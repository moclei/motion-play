#!/usr/bin/env python3
"""One-command DHO804 capture over the LAN (test-workflow-setup Phase 7; test-workflow-audit §5 item 1).

    python3 tools/lab/capture.py --test V7R-012 --arm A1 [--session lab/log/2026-11-04_s01.yaml]

What it does, in order (every command below is marked verified on fw 00.01.05 in
docs/initiatives/test-workflow-setup/PLAN.md "Verified instrument facts"):
  1. `*IDN?`; refuses any firmware other than 00.01.05 unless --any-firmware.
  2. Sets the scope clock from the Mac (`:SYSTem:DATE Y,M,D`, `:SYSTem:TIME H,M,S`, comma form)
     and reads it back.
  3. `:STOP`, so the PNG, the RAW memory and the measurements come from one frozen acquisition.
     The scope is left stopped; press RUN when done.
  4. Reads the channel / timebase / acquisition / trigger / decode / threshold settings.
  5. Pulls RAW memory for every displayed channel (`:WAVeform:MODE RAW`, `FORMat ASCii`,
     `STARt 1`, `STOP <memory depth>`). A single read is verified only at 10 kpts: deeper memory
     is refused unless --chunked (10 000-point windows; NOT verified on the bench).
  6. `:DISPlay:DATA? PNG` (TMC header stripped) and the `:SYSTem:SETup?` binary blob.
  7. `:MEASure:ITEM? <item>,CHANnel<n>` for each item and displayed channel. ~9.9E37 is recorded
     as `valid: false`, never as a number.
  8. Writes lab/captures/<ID>/YYYY-MM-DD_<ID>_<arm>_<nn>.{png,csv,setup.bin} (test-workflow-audit §4.4)
     and appends one measurement entry to the session log, with operator-only fields as TODO.

It never sends `:SAVE:SETup`, `:SAVE:MEMory:...` or `:SAVE:STATus?` (they fail silently on 00.01.05).
Nothing is written to disk until every query has succeeded.

Exit: 0 ok, 1 transport/scope error, 2 refused (precondition or bad arguments).
The socket layer is the vendored MIT ScpiClient in tools/lab/vendor/scpi.py.
"""
import argparse
import datetime
import decimal
import json
import logging
import math
import os
import re
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from vendor.scpi import ScpiClient, ScpiError  # noqa: E402

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

# The vendored client logs each failed connect to stderr and raises a message written for its
# MCP server ("server log", RIGOL_HOST). capture.py reports the address and cause itself.
logging.getLogger("vendor.scpi").setLevel(logging.CRITICAL)

DEFAULT_HOST = os.environ.get("DHO_HOST", "192.168.50.2")
LOCAL_NETWORK_HINT = ("macOS: allow your terminal app in System Settings → Privacy & Security → "
                      "Local Network; nc working does not prove Python can connect")


def connect_error(e, host, port):
    """Our text for the vendored client's connect failure, or None if e is another error."""
    cause = e.__cause__
    if not (isinstance(cause, OSError) and str(e).startswith("Could not connect")):
        return None
    return ("could not connect to the scope at %s:%s (%s). Check --host (or $DHO_HOST), the cable "
            "and that the scope's LAN is up. %s" % (host, port, cause, LOCAL_NETWORK_HINT))
VERIFIED_FW = "00.01.05"
SINGLE_READ_MAX = 10000          # RAW ASCii single read verified at 10 kpts only (PLAN, W4b S10)
DEFAULT_ITEMS = ["VTOP", "VBASe", "VAMP", "VPP"]   # items verified on 00.01.05 (W4 S4, S8c)
INVALID_MEAS = 9.0e37            # :MEASure:ITEM? answers ~9.9E37 when invalid (W4 S8b)
TEST_RE = re.compile(r"^V7R-\d{3,}$")
ARM_RE = re.compile(r"^[A-Za-z0-9]+(_[A-Za-z0-9]+)*$")   # A1, B, A2, S1, val_V5 (§4.4)
FORBIDDEN_RE = re.compile(r"^:?SAV(E)?:(SET|MEM|STAT)", re.IGNORECASE)
TODO = "TODO"


class Refused(Exception):
    """A precondition failed; nothing was written."""


# ---------------------------------------------------------------- SCPI wrapper

class Scope:
    """Thin wrapper over the vendored ScpiClient: a transcript, a forbidden-command
    guard, error-queue draining and a resync after binary reads."""

    def __init__(self, client):
        self.c = client
        self.transcript = []     # (command, reply or None)
        self.errors = []         # non-zero :SYSTem:ERRor? entries, with the command that preceded them

    def _guard(self, cmd):
        if FORBIDDEN_RE.match(cmd.strip()):
            raise Refused("refusing to send %r: :SAVE:SETup / :SAVE:MEMory / :SAVE:STATus? are "
                          "unusable on 00.01.05 (PLAN Verified instrument facts)" % cmd)

    def w(self, cmd):
        self._guard(cmd)
        self.c.write(cmd)
        self.transcript.append((cmd, None))

    def q(self, cmd):
        self._guard(cmd)
        r = self.c.query(cmd)
        self.transcript.append((cmd, r if len(r) < 200 else "<%d chars>" % len(r)))
        return r

    def safe_q(self, cmd):
        """A query whose failure must not stop the capture (settings not needed for the files).
        Returns None on timeout or transport error; the client reconnects on the next call."""
        try:
            return self.q(cmd)
        except ScpiError as e:
            self.transcript.append((cmd, "ERROR: %s" % e))
            self.errors.append({"after": cmd, "error": "no reply: %s" % e})
            return None

    def qbin(self, cmd):
        self._guard(cmd)
        data = self.c.query_binary(cmd)
        self.transcript.append((cmd, "<%d-byte block>" % len(data)))
        self.resync()
        return data

    def resync(self):
        """The vendored client drops the block's trailing newline with a 0.5 s recv. If that
        newline arrives late, it would be read as an empty reply to the next query and shift
        every later reply by one. `*IDN?` (verified) re-aligns: read lines until the IDN line."""
        self.c.write("*IDN?")
        for _ in range(3):
            line = self.c._read_line().decode("ascii", errors="replace").strip()
            if line.startswith("RIGOL"):
                return
        raise ScpiError("lost sync with the scope after a binary read")

    def drain_errors(self, after):
        for _ in range(20):
            r = self.safe_q(":SYSTem:ERRor?")
            if r is None or r.startswith("0,") or r.startswith("+0,"):
                return
            self.errors.append({"after": after, "error": r})


# ---------------------------------------------------------------- parsing helpers

def num(s):
    """Scientific-notation reply -> float, or None."""
    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def dec_scaled(raw, power):
    """raw * 10**power without binary float noise (3.0037E+00 V -> 3003.7 mV)."""
    return float(decimal.Decimal(raw.strip()).scaleb(power))


def strip_tmc(text):
    """ASCii waveform replies carry no TMC header on 00.01.05; strip one defensively if present."""
    if text.startswith("#") and len(text) > 2 and text[1].isdigit():
        n = int(text[1])
        return text[2 + n:]
    return text


def parse_preamble(s):
    f = [x.strip() for x in s.split(",")]
    if len(f) != 10:
        raise ScpiError("PREamble has %d fields, expected 10: %r" % (len(f), s))
    keys = ["format", "type", "points", "count", "xinc", "xorg", "xref", "yinc", "yorg", "yref"]
    out = {}
    for k, v in zip(keys, f):
        x = num(v)
        out[k] = int(x) if k in ("format", "type", "points", "count") and x is not None else x
    out["raw"] = s
    return out


def meas_entry(name, ch, raw):
    e = {"name": name, "ch": ch}
    x = num(raw)
    if raw is None:
        e.update(valid=False, raw=None, note="no reply")
    elif x is None:
        e.update(valid=False, raw=raw)
    elif not math.isfinite(x) or abs(x) >= INVALID_MEAS:
        e.update(valid=False, raw=raw)          # 9.9E37 = invalid, never a number
    else:
        up = name.upper()
        if up.startswith("V"):
            e["value_mV"] = dec_scaled(raw, 3)
        elif up.startswith(("RTIM", "FTIM", "PWID", "NWID", "PER")):
            e["value_ns"] = dec_scaled(raw, 9)
        elif up.startswith("FREQ"):
            e["value_Hz"] = dec_scaled(raw, 0)
        else:
            e["value"] = x                    # unit unknown to the tool; raw kept below
        e["raw"] = raw
    return e


def ratio_str(raw):
    x = num(raw)
    if x is None:
        return raw
    return ("%gx" % x)


def bw_str(raw):
    return "20MHz" if raw and raw.upper().startswith("20M") else raw


# ---------------------------------------------------------------- YAML emitter (stdlib; PyYAML reads it)

def _scalar(v):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, float):
        if math.isnan(v):
            return ".nan"
        if math.isinf(v):
            return ".inf" if v > 0 else "-.inf"
        r = repr(v)
        if "e" in r or "E" in r:              # PyYAML (YAML 1.1) needs a dot and a signed exponent
            mant, exp = r.lower().split("e")
            if "." not in mant:
                mant += ".0"
            if exp[0] not in "+-":
                exp = "+" + exp
            r = mant + "e" + exp
        return r
    return json.dumps(str(v))                 # a JSON string is a valid YAML double-quoted scalar


def _is_leaf_map(d):
    return isinstance(d, dict) and all(not isinstance(v, (dict, list)) for v in d.values())


def _flow(v):
    if isinstance(v, dict):
        return "{" + ", ".join("%s: %s" % (k, _scalar(x)) for k, x in v.items()) + "}"
    if isinstance(v, list):
        return "[" + ", ".join(_scalar(x) for x in v) + "]"
    return _scalar(v)


def dump_yaml(obj, indent=0):
    """Block YAML for dicts/lists; leaf maps and scalar lists in flow style."""
    pad = " " * indent
    lines = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if isinstance(v, dict) and v and not _is_leaf_map(v):
                lines.append("%s%s:" % (pad, k))
                lines.append(dump_yaml(v, indent + 2))
            elif isinstance(v, list) and v and any(isinstance(x, (dict, list)) for x in v):
                lines.append("%s%s:" % (pad, k))
                lines.append(dump_yaml(v, indent + 2))
            else:
                lines.append("%s%s: %s" % (pad, k, _flow(v)))
    elif isinstance(obj, list):
        for item in obj:
            if isinstance(item, dict) and not _is_leaf_map(item):
                body = dump_yaml(item, indent + 2).splitlines()
                lines.append(pad + "- " + body[0].lstrip())
                lines.extend(body[1:])
            else:
                lines.append(pad + "- " + _flow(item))
    return "\n".join(lines)


# ---------------------------------------------------------------- capture

def set_clock(sc, now):
    sc.w(":SYSTem:DATE %d,%d,%d" % (now.year, now.month, now.day))
    sc.w(":SYSTem:TIME %d,%d,%d" % (now.hour, now.minute, now.second))
    sc.drain_errors("clock set")
    d, t = sc.safe_q(":SYSTem:DATE?"), sc.safe_q(":SYSTem:TIME?")
    ok, delta = False, None
    try:
        back = datetime.datetime.strptime("%s %s" % (d, t), "%Y-%m-%d %H:%M:%S")
        delta = abs((back - now).total_seconds())
        ok = delta <= 10
    except (TypeError, ValueError):
        pass
    return {"set_to": now.strftime("%Y-%m-%dT%H:%M:%S"), "read_back": "%s %s" % (d, t),
            "ok": ok, "delta_s": delta}


def read_settings(sc):
    s = {"channels": {}, "displayed": []}
    for n in range(1, 5):
        disp = sc.q(":CHANnel%d:DISPlay?" % n)
        if disp.strip() not in ("1", "ON"):
            continue
        s["displayed"].append(n)
        ch = {}
        for key, cmd in (("probe", "PROBe"), ("bw_limit", "BWLimit"), ("scale", "SCALe"),
                         ("offset", "OFFSet"), ("coupling", "COUPling"), ("invert", "INVert"),
                         ("units", "UNITs")):
            ch[key] = sc.q(":CHANnel%d:%s?" % (n, cmd))
        s["channels"]["CH%d" % n] = ch
    s["timebase"] = {k: sc.q(c) for k, c in (("scale", ":TIMebase:MAIN:SCALe?"),
                                              ("offset", ":TIMebase:MAIN:OFFSet?"),
                                              ("mode", ":TIMebase:MODE?"))}
    s["acquire"] = {k: sc.q(c) for k, c in (("srate", ":ACQuire:SRATe?"),
                                             ("mdepth", ":ACQuire:MDEPth?"),
                                             ("type", ":ACQuire:TYPE?"))}
    trig = {k: sc.q(c) for k, c in (("mode", ":TRIGger:MODE?"), ("sweep", ":TRIGger:SWEep?"))}
    mode = trig["mode"].upper()
    if mode.startswith("EDGE"):
        for k, c in (("source", "SOURce"), ("slope", "SLOPe"), ("level", "LEVel")):
            trig[k] = sc.q(":TRIGger:EDGE:%s?" % c)
    elif mode.startswith("IIC"):
        # WHEN?/CLEVel? verified; the rest answer per [PG] but are untested -> tolerated
        trig["when"] = sc.q(":TRIGger:IIC:WHEN?")
        trig["clevel"] = sc.q(":TRIGger:IIC:CLEVel?")
        for k, c in (("scl", "SCL"), ("sda", "SDA"), ("dlevel", "DLEVel"), ("awidth", "AWIDth"),
                     ("address", "ADDRess"), ("direction", "DIRection")):
            trig[k] = sc.safe_q(":TRIGger:IIC:%s?" % c)
    s["trigger"] = trig
    bus = {"mode": sc.q(":BUS1:MODE?")}
    if bus["mode"].upper().startswith("IIC"):
        for k, c in (("scl_source", ":BUS1:IIC:SCLK:SOURce?"), ("sda_source", ":BUS1:IIC:SDA:SOURce?"),
                     ("address", ":BUS1:IIC:ADDRess?"), ("threshold_sda", ":BUS1:THReshold? SDA"),
                     ("threshold_scl", ":BUS1:THReshold? SCL")):
            bus[k] = sc.safe_q(c)
    s["bus1"] = bus
    s["measure"] = {k: sc.q(c) for k, c in (("threshold_type", ":MEASure:THReshold:TYPE?"),
                                             ("max_pct", ":MEASure:SETup:MAX?"),
                                             ("mid_pct", ":MEASure:SETup:MID?"),
                                             ("min_pct", ":MEASure:SETup:MIN?"),
                                             ("amsource", ":MEASure:AMSource?"))}
    return s


def read_waveform(sc, n, mdepth, chunked):
    sc.w(":WAVeform:SOURce CHANnel%d" % n)
    sc.w(":WAVeform:MODE RAW")
    sc.w(":WAVeform:FORMat ASCii")
    values = []
    step = mdepth if mdepth <= SINGLE_READ_MAX else SINGLE_READ_MAX
    start = 1
    while start <= mdepth:
        stop = min(start + step - 1, mdepth)
        sc.w(":WAVeform:STARt %d" % start)
        sc.w(":WAVeform:STOP %d" % stop)
        text = strip_tmc(sc.q(":WAVeform:DATA?"))
        part = [v.strip() for v in text.split(",") if v.strip()]
        if len(part) != stop - start + 1:
            raise ScpiError("CH%d RAW read %d..%d returned %d values" % (n, start, stop, len(part)))
        values.extend(part)
        start = stop + 1
    pre = parse_preamble(sc.q(":WAVeform:PREamble?"))
    if pre["points"] != mdepth:
        raise ScpiError("CH%d PREamble points %s != memory depth %d" % (n, pre["points"], mdepth))
    return values, pre


def capture(sc, args, now):
    """All scope I/O. Returns a dict of everything to write; writes nothing itself."""
    sc.drain_errors("connect")
    idn = sc.q("*IDN?")
    parts = [p.strip() for p in idn.split(",")]
    if len(parts) < 4 or not parts[0].startswith("RIGOL"):
        raise Refused("unexpected *IDN? reply: %r" % idn)
    model, serial, fw = parts[1], parts[2], parts[3]
    if fw != VERIFIED_FW and not args.any_firmware:
        raise Refused("scope firmware %s: the tool's commands are verified on %s only "
                      "(pass --any-firmware to override)" % (fw, VERIFIED_FW))

    clock = set_clock(sc, now)
    status_before = sc.q(":TRIGger:STATus?")
    sc.w(":STOP")
    status_after = None
    for _ in range(10):
        status_after = sc.q(":TRIGger:STATus?")
        if status_after.upper().startswith("STOP"):
            break
        time.sleep(0.2)
    settings = read_settings(sc)
    if not settings["displayed"]:
        raise Refused("no channel is displayed; nothing to capture")

    md = num(settings["acquire"]["mdepth"])
    if md is None or md <= 0 or md != int(md):
        raise Refused("memory depth reply %r is not a point count" % settings["acquire"]["mdepth"])
    mdepth = int(md)
    if mdepth > SINGLE_READ_MAX and not args.chunked:
        raise Refused("memory depth is %d points. A single RAW read is verified only at %d points "
                      "on 00.01.05. Set the memory depth to 10k on the scope, or pass --chunked "
                      "(10k-point windows, not verified on the bench)" % (mdepth, SINGLE_READ_MAX))

    png = sc.qbin(":DISPlay:DATA? PNG")
    if not png.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ScpiError(":DISPlay:DATA? PNG did not return a PNG (%r...)" % png[:8])

    waves = {}
    for n in settings["displayed"]:
        waves[n] = read_waveform(sc, n, mdepth, args.chunked)

    setup = sc.qbin(":SYSTem:SETup?")
    if not setup:
        raise ScpiError(":SYSTem:SETup? returned an empty block")

    values = []
    for n in settings["displayed"]:
        for item in args.items:
            values.append(meas_entry(item, "CH%d" % n, sc.safe_q(":MEASure:ITEM? %s,CHANnel%d" % (item, n))))
    sc.drain_errors("capture")

    return {"model": model, "serial": serial, "firmware": fw, "idn": idn, "clock": clock,
            "status_before": status_before, "status_after": status_after, "settings": settings,
            "mdepth": mdepth, "png": png, "waves": waves, "setup": setup, "values": values,
            "errors": list(sc.errors)}


# ---------------------------------------------------------------- files and log

def next_seq(cap_dir, prefix):
    pat = re.compile(re.escape(prefix) + r"_(\d{2,})\.")
    used = [int(m.group(1)) for p in cap_dir.glob(prefix + "_*") for m in [pat.match(p.name)] if m]
    return max(used, default=0) + 1


def csv_text(waves):
    chans = sorted(waves)
    first = waves[chans[0]][1]
    for n in chans[1:]:
        p = waves[n][1]
        if (p["xinc"], p["xorg"], p["points"]) != (first["xinc"], first["xorg"], first["points"]):
            raise ScpiError("channels have different time axes; refusing to merge into one CSV")
    xinc = decimal.Decimal(first["raw"].split(",")[4].strip())
    xorg = decimal.Decimal(first["raw"].split(",")[5].strip())
    out = ["Time(s)," + ",".join("CH%dV" % n for n in chans)]
    cols = [waves[n][0] for n in chans]
    for i in range(first["points"]):
        t = xorg + xinc * i
        out.append("%.9e," % t + ",".join(c[i] for c in cols))
    return "\n".join(out) + "\n"


def channels_block(settings):
    out = {}
    for name, ch in settings["channels"].items():
        out[name] = {"probe": TODO, "ratio": ratio_str(ch["probe"]), "signal": TODO, "point": TODO,
                     "bw_limit": bw_str(ch["bw_limit"]), "v_div_V": num(ch["scale"]),
                     "offset_V": num(ch["offset"]), "coupling": ch["coupling"]}
    return out


def trigger_block(trig):
    t = {"type": trig.get("mode"), "sweep": trig.get("sweep")}
    for k in ("source", "slope", "when", "scl", "sda", "address", "direction", "awidth"):
        if trig.get(k) is not None:
            t[k] = trig[k]
    for k in ("level", "clevel", "dlevel"):
        if trig.get(k) is not None:
            t[k + "_V"] = num(trig[k])
    return t


def new_session(stem, cap, setup_name):
    return {
        "session_id": stem,
        "kind": "scope",
        "operator": "user",
        "ai_session": TODO,
        "dut": {"board_id": TODO, "firmware_commit": TODO, "firmware_env": TODO, "declared_baseline": TODO},
        "scope": {"model": "Rigol " + cap["model"], "serial": cap["serial"], "firmware": cap["firmware"],
                  "setup_file": setup_name},
        "validation": {
            "passed": TODO,
            "V2_probe_ratio": {n: "%s/TODO" % ratio_str(c["probe"]) for n, c in cap["settings"]["channels"].items()},
            "V3_comp_png": TODO,
            "V5_noise_floor_mVpp": TODO,
            "V6_ground": {"method": TODO, "point": TODO, "length_mm": TODO},
            "V7_idle_high_V": {n: TODO for n in cap["settings"]["channels"]},
            "V8_decode_ok": TODO,
            "notes": "",
        },
        "channels": channels_block(cap["settings"]),
    }


def measurement_entry(args, cap, names, session_channels, now):
    s = cap["settings"]
    tb = num(s["timebase"]["scale"])
    entry = {
        "test_id": args.test,
        "arm": args.arm,
        "time": now.strftime("%Y-%m-%dT%H:%M:%S"),
        "trigger": trigger_block(s["trigger"]),
        "timebase_s_div": tb,
        "method": "auto",
        "feature": TODO,
        "values": cap["values"],
        "captures": names,
        "raw_observation": TODO,
        "source": "tools/lab/capture.py",
        "scope_settings": {
            "channels": s["channels"],
            "timebase": s["timebase"],
            "acquire": s["acquire"],
            "trigger": s["trigger"],
            "bus1": s["bus1"],
            "measure": s["measure"],
            "trigger_status": {"before": cap["status_before"], "after_stop": cap["status_after"]},
        },
        "waveform": {"mode": "RAW", "format": "ASCii", "points": cap["mdepth"],
                     "read": "single" if cap["mdepth"] <= SINGLE_READ_MAX else "chunked (unverified on 00.01.05)",
                     "preamble": {"CH%d" % n: w[1]["raw"] for n, w in sorted(cap["waves"].items())}},
        "scope_clock": cap["clock"],
        "scpi_errors": cap["errors"],
    }
    drift = []
    if session_channels:
        for name, cur in channels_block(s).items():
            old = session_channels.get(name)
            if not isinstance(old, dict):
                drift.append("%s not in the session channels block" % name)
                continue
            for k in ("ratio", "bw_limit", "v_div_V", "offset_V", "coupling"):
                if k in old and str(old[k]) != str(cur[k]):
                    drift.append("%s.%s: session %s, scope %s" % (name, k, old[k], cur[k]))
    if drift:
        entry["channel_drift"] = drift
    return entry


def append_measurement(path, entry):
    """Append `entry` under the top-level `measurements:` key, keeping the file's comments.
    The key must be the file's last top-level key. The result is re-parsed and the file is
    restored if it does not read back with exactly one more measurement."""
    text = path.read_text(encoding="utf-8")
    before = yaml.safe_load(text) if yaml else None
    n_before = len((before or {}).get("measurements") or [])
    lines = text.rstrip("\n").splitlines()
    top = [i for i, l in enumerate(lines) if re.match(r"^[A-Za-z_][\w-]*:", l)]
    if not top or not lines[top[-1]].startswith("measurements:"):
        raise Refused("%s: `measurements:` must be the last top-level key so the entry can be "
                      "appended without rewriting the file" % path)
    if lines[top[-1]].strip() in ("measurements: []", "measurements:"):
        lines[top[-1]] = "measurements:"
    new = "\n".join(lines) + "\n" + dump_yaml([entry], 2) + "\n"
    path.write_text(new, encoding="utf-8")
    if yaml:
        try:
            after = yaml.safe_load(new)
            ok = len(after.get("measurements") or []) == n_before + 1
        except Exception:
            ok = False
        if not ok:
            path.write_text(text, encoding="utf-8")
            raise Refused("%s: appended entry did not read back; file restored" % path)


def pick_session(root, arg, now):
    if arg:
        p = Path(arg)
        return p if p.is_absolute() else (root / p)
    logdir = root / "lab" / "log"
    today = sorted(logdir.glob(now.strftime("%Y-%m-%d") + "_s*.yaml"))
    return today[-1] if today else logdir / (now.strftime("%Y-%m-%d") + "_s01.yaml")


def write_outputs(root, args, cap, now):
    cap_dir = root / "lab" / "captures" / args.test
    cap_dir.mkdir(parents=True, exist_ok=True)
    prefix = "%s_%s_%s" % (now.strftime("%Y-%m-%d"), args.test, args.arm)
    stem = "%s_%02d" % (prefix, next_seq(cap_dir, prefix))
    files = {stem + ".png": cap["png"], stem + ".csv": csv_text(cap["waves"]).encode("ascii"),
             stem + ".setup.bin": cap["setup"]}
    for name in files:
        if (cap_dir / name).exists():
            raise Refused("%s already exists" % (cap_dir / name))

    session = pick_session(root, args.session, now)
    if session.exists() and yaml:
        sdata = yaml.safe_load(session.read_text(encoding="utf-8")) or {}
        if sdata.get("kind") == "log-only":
            raise Refused("%s is a log-only session; captures need kind: scope" % session)
        sess_channels = sdata.get("channels") or {}
    else:
        sess_channels = None

    for name, data in files.items():
        (cap_dir / name).write_bytes(data)
    names = list(files)
    entry = measurement_entry(args, cap, names, sess_channels, now)
    if session.exists():
        append_measurement(session, entry)
    else:
        session.parent.mkdir(parents=True, exist_ok=True)
        head = ("# %s — session log written by tools/lab/capture.py. Fill every TODO "
                "(template: lab/templates/log.yaml).\n" % session.name)
        body = dict(new_session(session.stem, cap, stem + ".setup.bin"))
        body["measurements"] = [entry]
        session.write_text(head + dump_yaml(body) + "\n", encoding="utf-8")
    return cap_dir, names, session, entry


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--test", required=True, help="card ID, V7R-NNN")
    ap.add_argument("--arm", required=True, help="A1 | B | A2 | S1… | val_V5 (§4.4)")
    ap.add_argument("--session", help="lab/log/<YYYY-MM-DD_sNN>.yaml (default: today's latest, else _s01)")
    ap.add_argument("--host", default=DEFAULT_HOST, help="scope IP (default %(default)s, or $DHO_HOST)")
    ap.add_argument("--port", type=int, default=5555)
    ap.add_argument("--timeout", type=float, default=10.0)
    ap.add_argument("--items", default=",".join(DEFAULT_ITEMS),
                    help="comma-separated :MEASure:ITEM? names per displayed channel (default %(default)s)")
    ap.add_argument("--chunked", action="store_true",
                    help="allow memory deeper than 10k points, read in 10k windows (NOT bench-verified)")
    ap.add_argument("--any-firmware", action="store_true", help="allow firmware other than 00.01.05")
    ap.add_argument("--root", default=str(HERE.parents[1]), help=argparse.SUPPRESS)
    ap.add_argument("--now", help=argparse.SUPPRESS)   # tests: fixed local time, ISO format
    args = ap.parse_args(argv)
    args.items = [i.strip() for i in args.items.split(",") if i.strip()]

    if not TEST_RE.match(args.test):
        print("capture: --test must look like V7R-012", file=sys.stderr)
        return 2
    if not ARM_RE.match(args.arm):
        print("capture: --arm must be letters/digits/underscores, e.g. A1, B, S2, val_V5", file=sys.stderr)
        return 2
    now = datetime.datetime.fromisoformat(args.now) if args.now else datetime.datetime.now().replace(microsecond=0)
    root = Path(args.root)

    client = ScpiClient(args.host, args.port, args.timeout)
    sc = Scope(client)
    try:
        cap = capture(sc, args, now)
    except Refused as e:
        print("capture: REFUSED: %s. Nothing was written." % e, file=sys.stderr)
        return 2
    except (ScpiError, OSError) as e:
        msg = connect_error(e, args.host, args.port) if isinstance(e, ScpiError) else None
        print("capture: scope error: %s. Nothing was written." % (msg or e), file=sys.stderr)
        return 1
    finally:
        client.close()

    try:
        cap_dir, names, session, entry = write_outputs(root, args, cap, now)
    except Refused as e:
        print("capture: REFUSED: %s" % e, file=sys.stderr)
        return 2

    print("capture: %s %s, %s, fw %s, memory %d pts, channels %s" % (
        args.test, args.arm, cap["model"], cap["firmware"], cap["mdepth"],
        ",".join("CH%d" % n for n in cap["settings"]["displayed"])))
    for n in names:
        print("  wrote %s" % (cap_dir / n))
    print("  log   %s (measurement appended; fill feature, raw_observation and any other TODO)" % session)
    if not cap["clock"]["ok"]:
        print("  WARNING: scope clock read-back %r does not match %s" % (cap["clock"]["read_back"], cap["clock"]["set_to"]))
    if not str(cap["status_after"]).upper().startswith("STOP"):
        print("  WARNING: trigger status after :STOP is %r, not STOP" % cap["status_after"])
    bad = [v for v in entry["values"] if v.get("valid") is False]
    if bad:
        print("  NOTE: %d measurement(s) invalid (9.9E37 or no reply): %s" % (
            len(bad), ", ".join("%s %s" % (v["name"], v["ch"]) for v in bad)))
    if cap["errors"]:
        print("  NOTE: SCPI errors recorded in the entry: %s" % cap["errors"])
    if entry.get("channel_drift"):
        print("  NOTE: channel settings differ from the session block: %s" % "; ".join(entry["channel_drift"]))
    print("  The scope is left STOPPED.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Tests for capture.py, validate_log.py (+ its pre-commit rule), ingest_usb.py and
backup_captures.sh.

Called from run_tests.py. capture.py runs against fake_scope.FakeScope, which replays the
Phase 6 bench recordings in scope_fixtures/. No real scope is needed.
"""
import datetime
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
LAB = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(LAB))

import capture  # noqa: E402
import validate_log  # noqa: E402
from fake_scope import FakeScope, FIX  # noqa: E402

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

NOW = "2026-11-04T10:42:05"
_results = []


def check(name, ok, detail=""):
    _results.append(ok)
    print("%s %s%s" % ("PASS" if ok else "FAIL", name, "" if ok else "\n  " + str(detail)))


def run(cmd, cwd=None):
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                       universal_newlines=True, cwd=cwd)
    return p.returncode, p.stdout


def run_capture(root, fake, *extra):
    return run([sys.executable, str(LAB / "capture.py"), "--test", "V7R-012", "--arm", "A1",
                "--host", "127.0.0.1", "--port", str(fake.port), "--root", str(root),
                "--now", NOW] + list(extra))


def payload(tmc):
    n = int(tmc[1:2])
    return tmc[2 + n:2 + n + int(tmc[2:2 + n])]


# ---------------------------------------------------------------- capture.py

def capture_tests(tmp):
    raw = (FIX / "lan_raw_ascii.txt").read_text().strip().split(",")

    # 1. basic capture, with an invalid measurement
    root = tmp / "c1"
    (root / "lab" / "log").mkdir(parents=True)
    f = FakeScope(meas={"VAMP,CHANNEL1": "9.9000E+37"})
    rc, out = run_capture(root, f)
    f.close()
    cap = root / "lab" / "captures" / "V7R-012"
    stem = "2026-11-04_V7R-012_A1_01"
    names = sorted(p.name for p in cap.iterdir()) if cap.is_dir() else []
    check("capture: exit 0 and §4.4 names", rc == 0 and names == sorted(
        [stem + ".png", stem + ".csv", stem + ".setup.bin"]), out + str(names))
    if rc != 0:
        return
    check("capture: PNG = :DISPlay:DATA? payload, TMC header stripped",
          (cap / (stem + ".png")).read_bytes() == payload((FIX / "lan_shot.tmc").read_bytes()))
    check("capture: setup file = :SYSTem:SETup? payload",
          (cap / (stem + ".setup.bin")).read_bytes() == payload((FIX / "lan_setup.tmc").read_bytes()))
    rows = (cap / (stem + ".csv")).read_text().splitlines()
    vals = [r.split(",")[1] for r in rows[1:]]
    check("capture: CSV holds the 10 000 RAW values verbatim", rows[0] == "Time(s),CH1V" and vals == raw,
          "%s / %d values" % (rows[0], len(vals)))
    t0, t1 = float(rows[1].split(",")[0]), float(rows[2].split(",")[0])
    check("capture: CSV time axis = PREamble xorg + i*xinc", abs(t0 + 2e-3) < 1e-12 and abs((t1 - t0) - 4e-7) < 1e-12,
          rows[1:3])

    cmds = [c.upper() for c in f.commands]
    check("capture: never sends :SAVE:SETup / :SAVE:MEMory / :SAVE:STATus?",
          not any(c.startswith((":SAVE:SET", ":SAVE:MEM", ":SAVE:STAT")) for c in cmds))
    check("capture: :STOP before the RAW read; STARt 1 / STOP 10000",
          ":STOP" in cmds and cmds.index(":STOP") < cmds.index(":WAVEFORM:MODE RAW")
          and ":WAVEFORM:START 1" in cmds and ":WAVEFORM:STOP 10000" in cmds)
    check("capture: clock set in comma form from the Mac time",
          ":SYSTEM:DATE 2026,11,4" in cmds and ":SYSTEM:TIME 10,42,5" in cmds)

    log = root / "lab" / "log" / "2026-11-04_s01.yaml"
    data = yaml.safe_load(log.read_text())
    m = data["measurements"][0]
    vamp = [v for v in m["values"] if v["name"] == "VAMP"][0]
    vtop = [v for v in m["values"] if v["name"] == "VTOP"][0]
    check("capture: 9.9E37 recorded as valid: false, no number",
          vamp.get("valid") is False and not any(k.startswith("value") for k in vamp), vamp)
    check("capture: valid measurement in mV with the raw reply", vtop.get("value_mV") == 2977.5 and vtop["raw"] == "2.9775E+00", vtop)
    check("capture: channels filled from the scope (ratio, bw_limit), operator fields TODO",
          data["channels"]["CH1"]["ratio"] == "10x" and data["channels"]["CH1"]["bw_limit"] == "OFF"
          and data["channels"]["CH1"]["signal"] == "TODO" and m["feature"] == "TODO" and m["raw_observation"] == "TODO",
          data["channels"])
    rep = validate_log.validate_text(log.read_text(), log.stem)
    check("capture: generated log has no validator errors, only TODOs (exit 3)",
          not rep.errors and rep.todos and rep.exit_code() == 3, rep.errors)
    check("capture: clock read back ok", m["scope_clock"]["ok"] is True, m["scope_clock"])

    # 2. second capture into the same session: nn = 02, comments kept, entry appended
    log.write_text("# operator comment kept\n" + log.read_text())
    f = FakeScope()
    rc, out = run_capture(root, f)
    f.close()
    data = yaml.safe_load(log.read_text())
    check("capture: second capture -> _02, appended to the same log, comments kept",
          rc == 0 and (cap / "2026-11-04_V7R-012_A1_02.png").exists() and len(data["measurements"]) == 2
          and log.read_text().startswith("# operator comment kept"), out)

    # 2a. channel drift is checked per arm: against the last entry with the same --arm only
    root = tmp / "c_drift"
    (root / "lab" / "log").mkdir(parents=True)

    def at_vdiv(arm, vdiv):
        f = FakeScope()
        f.table[":CHANNEL1:SCALE?"] = vdiv
        rc, out = run_capture(root, f, "--arm", arm)
        f.close()
        return rc, out
    rc1, out1 = at_vdiv("val_V3", "1.000000E+00")
    rc2, out2 = at_vdiv("val_V5", "5.000000E-01")
    check("capture: two arms at different V/div -> no drift NOTE",
          rc1 == 0 and rc2 == 0 and "NOTE: channel settings" not in out1 + out2, out1 + out2)
    rc3, out3 = at_vdiv("val_V5", "2.000000E-01")
    check("capture: same arm with a changed V/div -> drift NOTE naming v_div_V",
          rc3 == 0 and "NOTE: channel settings differ from the last val_V5 entry" in out3
          and "CH1.v_div_V" in out3 and "0.5" in out3 and "0.2" in out3, out3)
    d = yaml.safe_load((root / "lab" / "log" / "2026-11-04_s01.yaml").read_text())
    ms = d["measurements"]
    check("capture: channel_drift recorded only on the changed same-arm entry",
          [("channel_drift" in m) for m in ms] == [False, False, True], [m.get("channel_drift") for m in ms])
    v5 = d["validation"].get("V5")
    check("capture: validation skeleton writes the V5 block as per-channel TODOs, no legacy key",
          v5 == {k: {"CH1": "TODO"} for k in ("ctl_sd_mV", "dut_sd_mV", "excess_rms_mV", "offset_mV")}
          and "V5_noise_floor_mVpp" not in d["validation"], d["validation"])
    rep = validate_log.validate_text((root / "lab" / "log" / "2026-11-04_s01.yaml").read_text(), "2026-11-04_s01")
    check("capture: skeleton V5 TODOs are pending in the validator, no error or legacy warning",
          not rep.errors and "validation.V5.excess_rms_mV.CH1" in rep.todos
          and not any("legacy" in w for w in rep.warnings), rep.errors + rep.warnings)

    # 2b. connect failure: our message (--host/$DHO_HOST, Local Network hint), not the vendored one
    import socket
    s = socket.socket()
    s.bind(("127.0.0.1", 0))
    dead = s.getsockname()[1]
    s.close()
    root = tmp / "c_conn"
    rc, out = run([sys.executable, str(LAB / "capture.py"), "--test", "V7R-012", "--arm", "A1",
                   "--host", "127.0.0.1", "--port", str(dead), "--root", str(root), "--now", NOW])
    check("capture: connect failure names --host/$DHO_HOST and the Local Network hint, exit 1",
          rc == 1 and "--host" in out and "$DHO_HOST" in out and "Local Network" in out
          and "127.0.0.1:%d" % dead in out and "RIGOL_HOST" not in out and "server log" not in out
          and "Nothing was written" in out and not root.exists(), out)

    # 3. deeper memory is refused, nothing written
    root3 = tmp / "c3"
    f = FakeScope(mdepth=100000)
    rc, out = run_capture(root3, f)
    f.close()
    check("capture: memory depth > 10k refused (exit 2), nothing written",
          rc == 2 and "10k" in out and not (root3 / "lab").exists(), out)

    # 4. --chunked reads 10k windows
    root4 = tmp / "c4"
    f = FakeScope(mdepth=20000)
    rc, out = run_capture(root4, f, "--chunked")
    f.close()
    csvf = root4 / "lab" / "captures" / "V7R-012" / (stem + ".csv")
    nrows = len(csvf.read_text().splitlines()) - 1 if csvf.exists() else -1
    reads = [c.upper() for c in f.commands].count(":WAVEFORM:DATA?")
    d4 = yaml.safe_load((root4 / "lab" / "log" / "2026-11-04_s01.yaml").read_text()) if rc == 0 else {}
    check("capture: --chunked 20k = 2 reads, 20 000 rows, marked unverified",
          rc == 0 and nrows == 20000 and reads == 2
          and "unverified" in d4["measurements"][0]["waveform"]["read"], out)

    # 5. late TMC terminator: resync keeps later replies aligned
    root5 = tmp / "c5"
    f = FakeScope(late_terminator=True)
    rc, out = run_capture(root5, f)
    f.close()
    d5 = yaml.safe_load((root5 / "lab" / "log" / "2026-11-04_s01.yaml").read_text()) if rc == 0 else {}
    ok = rc == 0 and d5["measurements"][0]["values"][0]["raw"] == "2.9775E+00"
    check("capture: late block terminator -> resync, replies stay aligned", ok, out)

    # 6. other firmware refused
    f = FakeScope(idn="RIGOL TECHNOLOGIES,DHO804,X,00.01.06")
    rc, out = run_capture(tmp / "c6", f)
    f.close()
    check("capture: firmware other than 00.01.05 refused", rc == 2 and "00.01.06" in out, out)

    # 7. two channels -> one CSV, two columns
    root7 = tmp / "c7"
    f = FakeScope(displayed=(1, 2))
    rc, out = run_capture(root7, f)
    f.close()
    csvf = root7 / "lab" / "captures" / "V7R-012" / (stem + ".csv")
    head = csvf.read_text().splitlines()[0] if csvf.exists() else ""
    check("capture: two displayed channels -> Time(s),CH1V,CH2V", rc == 0 and head == "Time(s),CH1V,CH2V", out)

    # 8. a query with no reply (timeout) is recorded, capture continues
    root8 = tmp / "c8"
    f = FakeScope(drop_queries=[":MEASure:ITEM? VPP,CHANnel1"])
    rc, out = run_capture(root8, f, "--timeout", "1")
    f.close()
    d8 = yaml.safe_load((root8 / "lab" / "log" / "2026-11-04_s01.yaml").read_text()) if rc == 0 else {}
    vpp = [v for v in d8["measurements"][0]["values"] if v["name"] == "VPP"][0] if d8 else {}
    check("capture: unanswered measurement -> valid: false, capture still completes",
          rc == 0 and vpp.get("valid") is False and d8["measurements"][0]["scpi_errors"], out)

    # 9. the forbidden-command guard
    sc = capture.Scope(client=None)
    try:
        sc.w(":SAVE:SETup D:/x.stp")
        check("capture: guard refuses :SAVE:SETup", False)
    except capture.Refused:
        check("capture: guard refuses :SAVE:SETup", True)

    # 10. the YAML emitter round-trips awkward values through PyYAML
    obj = {"a": 1e-06, "b": "OFF", "c": "0x6B", "d": None, "e": True, "f": "x #y", "g": -2.994604,
           "h": [{"k": 9.9e37, "l": "yes"}], "i": {"j": {"k": 2e-4}}, "m": []}
    back = yaml.safe_load(capture.dump_yaml(obj))
    check("capture: YAML emitter round-trips through PyYAML", back == obj, capture.dump_yaml(obj))


# ---------------------------------------------------------------- validate_log.py + hook

def validator_tests(tmp):
    lf = HERE / "log_fixtures"
    for p in sorted((lf / "pass").glob("*.yaml")):
        rc, out = run([sys.executable, str(LAB / "validate_log.py"), str(p)])
        check("validate_log: pass/%s -> exit 0" % p.name, rc == 0, out)
    for p in sorted((lf / "fail").glob("*.yaml")):
        rep = validate_log.validate_text(p.read_text(), p.stem)
        expected = p.read_text().count("# FAIL")
        check("validate_log: fail/%s -> one error per FAIL marker (%d)" % (p.name, expected),
              len(rep.errors) == expected and rep.exit_code() == 1, "\n  ".join(rep.errors))
    legacy = "only the legacy V5_noise_floor_mVpp"
    p = lf / "pass" / "2026-11-04_s01.yaml"
    rep = validate_log.validate_text(p.read_text(), p.stem)
    check("validate_log: new validation.V5 block -> valid, no warning", not rep.errors and not rep.warnings,
          rep.errors + rep.warnings)
    p = lf / "warn" / "2026-11-06_s01.yaml"
    rep = validate_log.validate_text(p.read_text(), p.stem)
    check("validate_log: legacy V5_noise_floor_mVpp only -> valid, one legacy warning",
          not rep.errors and rep.exit_code() == 0 and [w for w in rep.warnings if legacy in w] == rep.warnings
          and len(rep.warnings) == 1, rep.errors + rep.warnings)
    p = lf / "pass" / "2026-11-07_s01.yaml"
    rep = validate_log.validate_text(p.read_text(), p.stem)
    check("validate_log: not_run with passed: false -> valid, not a TODO",
          not rep.errors and not rep.todos and rep.exit_code() == 0, rep.errors + rep.todos)
    s01 = LAB.parents[1] / "lab" / "log" / "2026-10-20_s01.yaml"
    if s01.exists():
        rep = validate_log.validate_text(s01.read_text(), s01.stem)
        check("validate_log: lab/log/2026-10-20_s01.yaml (V7R-001) -> no errors, legacy warning, V7 TODOs",
              not rep.errors and any(legacy in w for w in rep.warnings)
              and rep.todos == ["validation.V7_idle_high_V.CH1", "validation.V7_idle_high_V.CH2"],
              rep.errors + rep.todos + rep.warnings)
    tpl = LAB.parents[1] / "lab" / "templates" / "log.yaml"
    rep = validate_log.validate_text(tpl.read_text(), "2026-11-04_s01")
    check("validate_log: lab/templates/log.yaml is valid", not rep.errors, rep.errors)

    # pre-commit rule 4, in a scratch repo
    fail = lf / "fail" / "2026-11-04_s02.yaml"
    repo = tmp / "hookrepo"
    (repo / "lab" / "log").mkdir(parents=True)
    run(["git", "init", "-q"], cwd=str(repo))
    run(["git", "config", "user.email", "t@t"], cwd=str(repo))
    run(["git", "config", "user.name", "t"], cwd=str(repo))
    hook = [sys.executable, str(LAB / "precommit.py")]
    shutil.copy(str(fail), str(repo / "lab" / "log" / fail.name))
    run(["git", "add", "-A"], cwd=str(repo))
    rc, out = run(hook, cwd=str(repo))
    check("precommit: staged invalid log rejected", rc == 1 and "validation.passed" in out, out)
    run(["git", "rm", "-q", "--cached", "lab/log/" + fail.name], cwd=str(repo))
    os.remove(str(repo / "lab" / "log" / fail.name))
    good = lf / "pass" / "2026-11-04_s01.yaml"
    shutil.copy(str(good), str(repo / "lab" / "log" / good.name))
    run(["git", "add", "-A"], cwd=str(repo))
    rc, out = run(hook, cwd=str(repo))
    check("precommit: staged valid log accepted", rc == 0, out)
    p = repo / "lab" / "log" / good.name
    p.write_text(p.read_text().replace('feature: "SDA, master-driven 0-bit, flat region"', 'feature: "TODO"'))
    run(["git", "add", "-A"], cwd=str(repo))
    rc, out = run(hook, cwd=str(repo))
    check("precommit: TODO fields warn but do not reject", rc == 0 and "TODO" in out, out)


# ---------------------------------------------------------------- noise_floor.py

def noise_floor_tests(tmp):
    ev = LAB.parents[1] / "lab" / "evidence" / "V7R-001"
    ctl, dut = ev / "2026-10-20_V7R-001_val_V5_03.csv", ev / "2026-10-20_V7R-001_val_V5_01.csv"
    nf = [sys.executable, str(LAB / "noise_floor.py"), "--ctl", str(ctl)]
    rc, out = run(nf + ["--dut", str(dut)])
    check("noise_floor: V7R-001 S1 vs control -> sd 4.97/5.17, 4.77/4.72, excess 1.44/0, PASS",
          rc == 0 and "ctl_sd_mV: {CH1: 4.97, CH2: 4.77}" in out and "dut_sd_mV: {CH1: 5.17, CH2: 4.72}" in out
          and "excess_rms_mV: {CH1: 1.44, CH2: 0.0}" in out and "V5 PASS" in out, out)
    snip = out[out.index("  V5:"):]
    v5 = yaml.safe_load(snip)["V5"]
    rep = validate_log.Report()
    validate_log.check_v5(v5, rep)
    check("noise_floor: snippet parses and passes the validator's V5 check", not rep.errors, rep.errors)
    rows = dut.read_text().splitlines()
    x2 = tmp / "x2.csv"
    x2.write_text("\n".join([rows[0]] + [r.split(",")[0] + "," + ",".join(
        "%.6e" % (float(v) * 2) for v in r.split(",")[1:]) for r in rows[1:]]) + "\n")
    rc, out = run(nf + ["--dut", str(x2)])
    check("noise_floor: doubled noise -> FAIL (exit 1) and a level-step warning",
          rc == 1 and "FAIL" in out and "smallest level step differs" in out, out)
    short = tmp / "short.csv"
    short.write_text("\n".join(rows[:5001]) + "\n")
    rc, out = run(nf + ["--dut", str(short)])
    check("noise_floor: point count differs -> refused (exit 2)", rc == 2 and "point count" in out, out)
    rc, out = run(nf + ["--dut", str(ev / "2026-10-20_V7R-001_val_V3_01.csv")])
    check("noise_floor: sample interval differs -> refused (exit 2)", rc == 2 and "sample interval" in out, out)


# ---------------------------------------------------------------- i2c_frame.py

DT, T0, NPTS = 16e-9, -80e-6, 10000          # 10 us/div, 10 kpts: the V9 record
SDA_HI, SCL_HI, SDA_LO, ACK_LO, SCL_LO = 3.300, 3.290, 0.060, 0.120, 0.080
SDA_RAMP, SCL_RAMP, FALL = 200e-9, 150e-9, 20e-9


def wave(start, steps, rise):
    """steps: [(t, level)]; each step is a linear ramp from the previous level, `rise` long when
    going up, FALL when going down."""
    out = []
    for i in range(NPTS):
        t = T0 + i * DT
        v = start
        for tc, lv in steps:
            if t <= tc:
                break
            d = rise if lv > v else FALL
            v = v + (lv - v) * min(1.0, (t - tc) / d)
        out.append(v)
    return out


def frame(byte, ack=True, start_in_record=True, stop_us=30):
    """SDA/SCL steps for one address byte + 9th bit + STOP at 100 kHz. Bit k: SDA set at
    -73 + 10k us, SCL high -70 + 10k .. -65 + 10k us. STOP: SDA low at +17, SCL up at +23,
    SDA up at +stop_us (default +30) us. Master-driven lows at SDA_LO, the ACK low at ACK_LO."""
    sda = [((-78e-6 if start_in_record else -85e-6), SDA_LO)]
    scl = [(-75e-6, SCL_LO)]
    bits = [(byte >> (7 - k)) & 1 for k in range(8)] + [0 if ack else 1]
    for k, b in enumerate(bits):
        lo = ACK_LO if k == 8 else SDA_LO
        sda.append(((-73 + 10 * k) * 1e-6, SDA_HI if b else lo))
        scl += [((-70 + 10 * k) * 1e-6, SCL_HI), ((-65 + 10 * k) * 1e-6, SCL_LO)]
    sda += [(17e-6, SDA_LO), (stop_us * 1e-6, SDA_HI)]
    scl += [(23e-6, SCL_HI)]
    s = wave(SDA_HI, sda, SDA_RAMP)
    c = wave(SCL_HI, scl, SCL_RAMP)
    return {"CH1": s, "CH2": c}


def write_csv(path, cols):
    names = list(cols)
    lines = ["Time(s)," + ",".join(n + "V" for n in names)]
    for i in range(NPTS):
        lines.append("%.9e," % (T0 + i * DT) + ",".join("%+.6e" % cols[n][i] for n in names))
    path.write_text("\n".join(lines) + "\n")
    return path


def values_csv(out):
    return yaml.safe_load(out[out.index("    values_csv:"):])["values_csv"]


def i2c_frame_tests(tmp):
    tool = [sys.executable, str(LAB / "i2c_frame.py")]
    near = lambda a, b, tol: abs(a - b) <= tol  # noqa: E731
    # Expected from the ramps: the 0.99 -> 2.31 V time of a linear ramp, and the 1.65 V crossing.
    sda_rise = 1.32 / (SDA_HI - SDA_LO) * SDA_RAMP * 1e9          # 81.48 ns
    scl_rise = 1.32 / (SCL_HI - SCL_LO) * SCL_RAMP * 1e9          # 61.68 ns
    scl_mid_us = (1.65 - SCL_LO) / (SCL_HI - SCL_LO) * SCL_RAMP * 1e6
    sda_mid_us = (1.65 - SDA_LO) / (SDA_HI - SDA_LO) * SDA_RAMP * 1e6

    f = write_csv(tmp / "d6.csv", frame(0xD6))
    rc, out = run(tool + [str(f), "--expect", "D6"])
    try:
        v = values_csv(out)
        by = {}
        for e in v:
            by.setdefault(e["name"], []).append(e)
        vol = by["V_OL"]
        rise = {e["ch"]: e for e in by["rise_30_70"]}
        r1 = [float(x) for x in rise["CH1"]["value"].replace(" ns", "").split(",")]
        r2 = [float(x) for x in rise["CH2"]["value"].replace(" ns", "").split(",")]
        scl_t = [float(x) for x in rise["CH2"]["gate"].split("(")[1].split(" us")[0].split(",")]
        sda_t = [float(x) for x in rise["CH1"]["gate"].split("(")[1].split(" us")[0].split(",")]
        idle = {e["ch"]: e["value_mV"] for e in by["idle_high"]}
        idle_g = by["idle_high"][0]["gate"]
        idle_t0 = float(idle_g.split("t=")[1].split("..")[0])
        ok = (rc == 0 and "START at -77.99 us" in out and "-> D6, 9th bit low (ACK)" in out
              and "frame PASS" in out
              and by["SCL_period"][0]["value_us"] == 10.0
              # rise times within 0.2 ns of the ramp's; 10 SCL edges (9 bits + STOP), 4 SDA edges
              and len(r2) == 10 and all(near(x, scl_rise, 0.2) for x in r2)
              and len(r1) == 4 and all(near(x, sda_rise, 0.2) for x in r1)
              # edge times (1.65 V) within 0.02 us
              and all(near(a, -70 + 10 * k + scl_mid_us, 0.02) for k, a in enumerate(scl_t[:9]))
              and near(scl_t[9], 23 + scl_mid_us, 0.02)
              and len(sda_t) == 4 and all(near(a, b + sda_mid_us, 0.02) for a, b in zip(sda_t, [-73, -43, -23, 30]))
              # V_OL: bits 5, 3, R/W 0 at 60.0 mV (the 120 mV ACK excluded), n ~ 0.8 x 5 us / 16 ns
              and [e["gate"].split(",")[0] for e in vol] == ["address bit 5", "address bit 3", "R/W bit 0"]
              and all(e["value_mV"] == 60.0 and "sd 0.0 mV" in e["gate"] for e in vol)
              and all(240 <= int(e["gate"].split("n=")[1].split(",")[0]) <= 252 for e in vol)
              # idle from 5 us after the last edge (the STOP's SDA 1.65 V crossing): the window
              # starts at +30 + sda_mid + 5 us (+-0.02), past the ramp, so the levels are exact
              and idle_g.startswith("from 5 us after the last edge, t=")
              and near(idle_t0, 35 + sda_mid_us, 0.02)
              and "PASS  Idle high     CH1  3.3000 V (from 5 us after the last edge)" in out
              and near(idle["CH1"], 3300.0, 0.05) and near(idle["CH2"], 3290.0, 0.05))
    except (ValueError, KeyError, IndexError, TypeError) as e:
        ok, out = False, "%r\n%s" % (e, out)
    check("i2c_frame: synthetic D6+ACK frame -> byte, ACK, period 10 us, rise %.1f/%.1f ns (+-0.2), "
          "edge times (+-0.02 us), V_OL 60.0 mV x3 (ACK excluded), idle from 5 us after the last edge "
          "(start +-0.02 us) 3300.0/3290.0 mV, exit 0"
          % (sda_rise, scl_rise), ok, out)
    v = values_csv(out) if "values_csv" in out else []
    check("i2c_frame: frame snippet entries all carry a gate",
          bool(v) and all("gate" in e for e in v), out)

    # STOP's SDA rise at +72 us: 8 us of record after the last edge, but < 5 us after the margin
    f = write_csv(tmp / "late_stop.csv", frame(0xD6, stop_us=72))
    rc, out = run(tool + [str(f), "--expect", "D6"])
    check("i2c_frame: last edge at +72 us (< 5 us left after the 5 us margin) -> idle high n/a, exit 0",
          rc == 0 and "n/a   Idle high     -    not reported (< 5 us of samples from 5 us after the last edge)" in out
          and "idle high: not reported (last edge at +72.1" in out and "idle_high" not in out
          and "frame PASS" in out, out)

    f = write_csv(tmp / "idle.csv", {"CH1": [SDA_HI + (0.002 if i % 2 else -0.002) for i in range(NPTS)],
                                     "CH2": [SCL_HI] * NPTS})
    rc, out = run(tool + [str(f)])
    check("i2c_frame: flat idle record -> idle mode, V7_idle_high_V {CH1: 3.300, CH2: 3.290}, sd 2.00/0.00 mV, exit 0",
          rc == 0 and "mode: idle" in out and "V7_idle_high_V: {CH1: 3.300, CH2: 3.290}" in out
          and "{name: sd, ch: CH1, value_mV: 2.00}" in out and "V7 PASS" in out, out)
    f = write_csv(tmp / "idle_low.csv", {"CH1": [3.0] * NPTS, "CH2": [SCL_HI] * NPTS})
    rc, out = run(tool + [str(f)])
    check("i2c_frame: idle record at 3.0 V -> idle high FAIL, exit 1",
          rc == 1 and "FAIL  Idle high     CH1" in out and "V7 FAIL" in out, out)

    f = write_csv(tmp / "nack.csv", frame(0xD6, ack=False, start_in_record=False))
    rc, out = run(tool + [str(f), "--expect", "D6"])
    check("i2c_frame: NACK frame, START before the record -> anchored on the STOP, D6 NACK, decode FAIL, exit 1",
          rc == 1 and "no START in record; 9 bits before the STOP" in out
          and "-> D6, 9th bit high (NACK)" in out and "FAIL  Decode        CH1  D6 NACK" in out, out)

    f = write_csv(tmp / "d4.csv", frame(0xD4))
    rc, out = run(tool + [str(f), "--expect", "D6"])
    try:
        vol = [e for e in values_csv(out) if e["name"] == "V_OL"]
        ok = (rc == 1 and "-> D4, 9th bit low (ACK)" in out and "FAIL  Decode        CH1  D4 ACK  (limit D6 then ACK)" in out
              and [e["gate"].split(",")[0] for e in vol] == ["address bit 5", "address bit 3", "address bit 1", "R/W bit 0"]
              and "PASS  Rise" in out)
    except (ValueError, KeyError) as e:
        ok, out = False, "%r\n%s" % (e, out)
    check("i2c_frame: byte D4 with --expect D6 -> decode FAIL, other rows PASS, V_OL on 4 zero bits, exit 1", ok, out)

    f = write_csv(tmp / "one.csv", {"CH1": frame(0xD6)["CH1"]})
    rc, out = run(tool + [str(f), "--expect", "D6"])
    check("i2c_frame: single-channel record -> refused (no CH2 column), exit 2",
          rc == 2 and "no such column" in out and "--scl CH2" in out, out)

    uart = {"CH1": frame(0xD6)["CH1"], "CH2": [SCL_HI] * NPTS}
    f = write_csv(tmp / "uart.csv", uart)
    rc, out = run(tool + [str(f)])
    check("i2c_frame: SDA toggling with SCL flat (boot UART) -> no frame, exit 2",
          rc == 2 and "NO FRAME" in out, out)
    rc, out = run(tool + [str(tmp / "d6.csv"), "--expect", "G1"])
    check("i2c_frame: bad --expect -> exit 2", rc == 2, out)


# ---------------------------------------------------------------- ingest_usb.py

def ingest_tests(tmp):
    stick = tmp / "stick"
    stick.mkdir()
    (stick / ".Spotlight-V100").mkdir()
    (stick / "._p6img0.png").write_bytes(b"appledouble")
    at = datetime.datetime(2026, 11, 4, 10, 42)
    files = {  # name -> stick mtime (stick runs ~1 h ahead of the Mac)
        "p6img0.png": at + datetime.timedelta(minutes=60, seconds=20),
        "p6wav0.csv": at + datetime.timedelta(minutes=60, seconds=40),
        "old0.png": datetime.datetime(2013, 1, 18, 9, 52),
    }
    for n, t in files.items():
        (stick / n).write_bytes(n.encode())
        ts = t.timestamp()
        os.utime(str(stick / n), (ts, ts))
    before = sorted((p.name, p.stat().st_mtime) for p in stick.iterdir())

    root = tmp / "i1"
    ing = [sys.executable, str(LAB / "ingest_usb.py"), "--src", str(stick), "--test", "V7R-012",
           "--arm", "A1", "--root", str(root), "--now", "2026-11-04T12:00:00"]
    rc, out = run(ing + ["--at", "2026-11-04T10:42"])
    cap = root / "lab" / "captures" / "V7R-012"
    got = sorted(p.name for p in cap.glob("2026-*")) if cap.is_dir() else []
    check("ingest: time match with the +60 min stick offset, §4.4 names",
          rc == 0 and got == ["2026-11-04_V7R-012_A1_01.csv", "2026-11-04_V7R-012_A1_01.png"], out)
    inbox = list((root / "lab" / "inbox").glob("usb-*/*"))
    check("ingest: whole stick copied to inbox, hidden files skipped",
          sorted(p.name for p in inbox) == sorted(files), [p.name for p in inbox])
    check("ingest: content kept", (cap / "2026-11-04_V7R-012_A1_01.png").read_bytes() == b"p6img0.png")
    check("ingest: INGEST.tsv records the mapping", (cap / "INGEST.tsv").exists()
          and "p6img0.png" in (cap / "INGEST.tsv").read_text())

    # reported name without its index digit, second ingest -> _02, inbox not re-copied
    rc, out = run(ing + ["--at", "2026-11-04T10:42", "--files", "p6img.png"])
    check("ingest: reported name without the index digit matches; next nn = 02; no re-copy",
          rc == 0 and (cap / "2026-11-04_V7R-012_A1_02.png").exists() and "0 new" in out, out)

    # ambiguity: two PNGs near the time -> nothing renamed
    (stick / "p6img1.png").write_bytes(b"second")
    ts = (at + datetime.timedelta(minutes=61)).timestamp()
    os.utime(str(stick / "p6img1.png"), (ts, ts))
    n_before = len(list(cap.glob("2026-*")))
    rc, out = run(ing + ["--at", "2026-11-04T10:42"])
    check("ingest: two PNGs in the window -> ambiguous, exit 1, nothing renamed",
          rc == 1 and "ambiguous" in out and len(list(cap.glob("2026-*"))) == n_before, out)
    rc, out = run(ing + ["--at", "2026-11-04T10:42", "--files", "p6img.png"])
    check("ingest: --files p6img.png with p6img0 and p6img1 both near --at -> ambiguous",
          rc == 1 and "ambiguous" in out, out)
    rc, out = run(ing + ["--at", "2026-11-04T10:42", "--files", "p6img1.png", "--dry-run"])
    check("ingest: exact name resolves it (dry run writes nothing)",
          rc == 0 and "would write" in out and len(list(cap.glob("2026-*"))) == n_before, out)

    rc, out = run(ing + ["--at", "2026-11-05T09:00"])
    check("ingest: no file near --at -> exit 1", rc == 1 and "no scope file" in out, out)

    os.remove(str(stick / "p6img1.png"))
    after = sorted((p.name, p.stat().st_mtime) for p in stick.iterdir())
    check("ingest: stick untouched (names and mtimes)", before == after, (before, after))


# ---------------------------------------------------------------- backup_captures.sh

def backup_tests(tmp):
    sh = str(LAB / "backup_captures.sh")
    repo = tmp / "b_repo"
    (repo / "lab" / "captures" / "V7R-012").mkdir(parents=True)
    (repo / "lab" / "inbox" / "usb-x").mkdir(parents=True)
    (repo / "lab" / "captures" / "V7R-012" / "a.csv").write_text("1")
    (repo / "lab" / "inbox" / "usb-x" / "b.png").write_text("2")
    home = tmp / "b_home"
    icloud = home / "Library" / "Mobile Documents" / "com~apple~CloudDocs"

    def bk(*args, **env):
        e = dict(os.environ, HOME=str(home), LAB_REPO=str(repo))
        e.pop("LAB_BACKUP_DIR", None)
        e.update(env)
        p = subprocess.run(["/bin/sh", sh] + list(args), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, universal_newlines=True, env=e)
        return p.returncode, p.stdout

    home.mkdir()
    rc, out = bk()
    check("backup: missing iCloud root -> exit 1, clear message",
          rc == 1 and "iCloud Drive root not found" in out and not (home / "Library").exists(), out)
    icloud.mkdir(parents=True)
    dst = icloud / "motion-play-lab"
    rc, out = bk("--dry-run")
    check("backup: --dry-run copies nothing", rc == 0 and not dst.exists(), out)
    rc, out = bk()
    check("backup: copies captures/ and inbox/ to the default folder",
          rc == 0 and (dst / "captures" / "V7R-012" / "a.csv").read_text() == "1"
          and (dst / "inbox" / "usb-x" / "b.png").read_text() == "2", out)
    os.remove(str(repo / "lab" / "captures" / "V7R-012" / "a.csv"))
    rc, out = bk()
    check("backup: a file deleted locally is kept in the backup (no --delete)",
          rc == 0 and (dst / "captures" / "V7R-012" / "a.csv").exists(), out)
    alt = tmp / "b_alt"
    alt.mkdir()
    rc, out = bk(LAB_BACKUP_DIR=str(alt / "lab"))
    check("backup: $LAB_BACKUP_DIR overrides the destination",
          rc == 0 and (alt / "lab" / "inbox" / "usb-x" / "b.png").exists(), out)
    rc, out = bk("--delete")
    check("backup: unknown argument -> exit 2", rc == 2, out)


def main():
    if yaml is None:
        print("FAIL tool tests need PyYAML")
        return 1
    tmp = Path(tempfile.mkdtemp(prefix="labtools-"))
    try:
        capture_tests(tmp)
        validator_tests(tmp)
        noise_floor_tests(tmp)
        i2c_frame_tests(tmp)
        ingest_tests(tmp)
        backup_tests(tmp)
    finally:
        shutil.rmtree(str(tmp), ignore_errors=True)
    return sum(1 for r in _results if not r)


if __name__ == "__main__":
    n = main()
    print("\n%s: %d failure(s)" % ("OK" if not n else "FAILED", n))
    sys.exit(1 if n else 0)

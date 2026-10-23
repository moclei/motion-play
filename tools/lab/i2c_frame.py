#!/usr/bin/env python3
"""I2C frame numbers from a capture.py CSV, for V7 (idle high) and V9 (reference frame)
(PLAN "After V7R-002 S1" §3, §4, §6; lab/procedures/known-good-reference.md, pass table).

    python3 tools/lab/i2c_frame.py <csv> [--sda CH1] [--scl CH2] [--vdd 3.3] [--expect D6]

Thresholds are fractions of the nominal V_DD (UM10204): V_IL 0.3 V_DD, mid 0.5 V_DD,
V_IH 0.7 V_DD (0.99 / 1.65 / 2.31 V at 3.3 V). An edge is a move from below 0.3 V_DD to
above 0.7 V_DD (rising) or back (falling); its time is the 0.5 V_DD crossing.

Idle mode (no channel crosses 0.5 V_DD): per channel mean, sd, min, max of all samples, and
a `validation.V7_idle_high_V` snippet.

Frame mode (otherwise):
  - bits: one per SCL high interval with no SDA edge inside it, SDA read at the SCL rising
    edge. An SDA fall while SCL is high is a START, a rise a STOP. The frame starts after
    the first START; with no START in the record (the 0x6B address trigger at 10 us/div puts
    it just before the record) the bits before the first STOP / repeated START are used
    when they are a whole number of 9-bit groups. The first group is the address byte and
    its 9th bit (ACK when low).
  - SCL period: mean spacing of the address byte's 9 SCL rising edges.
  - rise time: every complete SDA and SCL rising edge in the record, the time from the
    0.3 V_DD crossing to the 0.7 V_DD crossing, linear interpolation between samples (§4).
  - V_OL: SDA mean on each master-driven 0-bit of the address byte (the ACK excluded),
    gated on that bit's SCL-high interval shrunk by 10 % at each end; n and sd (n - 1) in
    the gate.
  - idle high: per channel mean of the samples from 5 us after the last edge (its 0.5 V_DD
    crossing, on either channel) to the record end, when at least 5 us of samples remain
    after that margin; else not reported (and that row not evaluated). PLAN §6: 5 us is
    UM10204's t_BUF (4.7 us, Standard mode) rounded up.
  - a `values_csv` snippet with gates, in the style of lab/log/2026-10-21_s01.yaml.

Pass/fail per row of the known-good-reference.md pass table (limits copied below; that file
is the source): V_OL <= 0.4 V; idle high 3.135-3.465 V; rise 30->70 % <= 300 ns (the limit
V7R-002 registered, PLAN "After V7R-002 S1" §2); decode = --expect then ACK.
The scope panel RTIMe is recorded beside the CSV rise time by hand; it has no pass role.

Exit: 0 all evaluated rows PASS; 1 any FAIL; 2 bad input or no frame found. Stdlib only;
runs on Python 3.7.
"""
import argparse
import math
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from noise_floor import Refused, load  # noqa: E402  (the capture.py CSV loader)

REF = "lab/procedures/known-good-reference.md"
# Limits from REF's pass table (UM10204, V_DD = 3.3 V). REF is the source; keep these in step.
VOL_MAX_V = 0.4
VOL_INVESTIGATE_V = 0.2          # REF: "> 0.2 V on a working bus = investigate the setup [own heuristic]"
IDLE_LO_V, IDLE_HI_V = 3.135, 3.465
RISE_MAX_NS = 300.0              # Fast mode; kept for the 100 kHz reference frame (PLAN "After V7R-002 S1" §2)
IDLE_MIN_S = 5e-6
IDLE_MARGIN_S = 5e-6           # settle margin after the last edge (PLAN "After V7R-002 S1" §6)
GATE_SHRINK = 0.10


class NoFrame(Exception):
    pass


def first_time(path):
    with open(path, encoding="ascii") as f:
        f.readline()
        return float(f.readline().split(",")[0])


def cross(t, v, a, b, thr):
    """Time where the segment between samples a and b crosses thr (linear interpolation)."""
    if v[b] == v[a]:
        return t[a]
    return t[a] + (thr - v[a]) / (v[b] - v[a]) * (t[b] - t[a])


def find_edges(t, v, lo, mid, hi):
    """Complete edges: [{'kind': 'R'|'F', 't': mid crossing, 'end': t of the sample past the far
    threshold, 'rise_ns': for 'R'}]. A record that starts mid-edge gives no edge for it."""
    edges = []
    state = None
    last_lo = last_hi = None
    for j, x in enumerate(v):
        if x < lo:
            if state == "H":
                k = max(i for i in range(last_hi, j) if v[i] > mid)
                edges.append({"kind": "F", "t": cross(t, v, k, k + 1, mid), "end": t[j]})
            state, last_lo = "L", j
        elif x > hi:
            if state == "L":
                i = last_lo
                k = max(m for m in range(i, j) if v[m] < mid)
                edges.append({"kind": "R", "t": cross(t, v, k, k + 1, mid), "end": t[j],
                              "rise_ns": (cross(t, v, j - 1, j, hi) - cross(t, v, i, i + 1, lo)) * 1e9})
            state, last_hi = "H", j
    return edges


def stats(x):
    n = len(x)
    mean = sum(x) / n
    sd = math.sqrt(sum((a - mean) ** 2 for a in x) / (n - 1)) if n > 1 else 0.0
    return {"n": n, "mean": mean, "sd": sd, "min": min(x), "max": max(x)}


def us(x):
    return "%+.2f" % (x * 1e6)


def sample_at(t, v, when):
    dt = t[1] - t[0]
    i = int(round((when - t[0]) / dt))
    return v[min(max(i, 0), len(v) - 1)]


def decode(t, sda, scl_name, e_sda, e_scl, mid):
    """-> (bits, events). bits: [{'bit', 't_rise', 't_fall'}] of the frame's first 9-bit group
    onward, events: list of 'S'/'P' with times (for the report)."""
    if not e_scl:
        raise NoFrame("SCL (%s) has no complete edge" % scl_name)
    highs = []                                  # (t_rise or None, t_fall or None)
    if e_scl[0]["kind"] == "F":
        highs.append((None, e_scl[0]["t"]))
    for a, e in enumerate(e_scl):
        if e["kind"] == "R":
            nxt = e_scl[a + 1]["t"] if a + 1 < len(e_scl) else None
            highs.append((e["t"], nxt))
    seq = []
    for r, f in highs:
        lo_t = r if r is not None else t[0]
        hi_t = f if f is not None else t[-1]
        inside = [e for e in e_sda if lo_t < e["t"] < hi_t]
        if inside:
            seq.append(("S" if inside[0]["kind"] == "F" else "P", inside[0]["t"]))
        elif r is not None:
            seq.append(("B", 1 if sample_at(t, sda, r) > mid else 0, r, f))
    events = [(s[0], s[1]) for s in seq if s[0] != "B"]
    if seq and any(s[0] == "S" for s in seq):
        k = next(i for i, s in enumerate(seq) if s[0] == "S")
        run = []
        for s in seq[k + 1:]:
            if s[0] != "B":
                break
            run.append(s)
        anchored = "START at %s us" % us(seq[k][1])
        if len(run) < 9:
            raise NoFrame("%d bit(s) after the %s, fewer than 9" % (len(run), anchored))
    else:
        run = []
        end = None
        for s in seq:
            if s[0] != "B":
                end = s
                break
            run.append(s)
        if end is None or not run or len(run) % 9:
            raise NoFrame("no START in the record and %d bit(s) %s; the byte boundary cannot be "
                          "placed" % (len(run), "before the first STOP / START" if end else
                                      "with no STOP after them"))
        anchored = "no START in record; %d bits before the %s at %s us" % (
            len(run), "STOP" if end[0] == "P" else "START", us(end[1]))
    bits = [{"bit": s[1], "t_rise": s[2], "t_fall": s[3]} for s in run]
    return bits, events, anchored


def analyse(path, args):
    dt, cols = load(path)
    for role, ch in (("--sda", args.sda), ("--scl", args.scl)):
        if ch not in cols:
            raise Refused("%s %s: no such column in %s (has %s)" % (role, ch, path, ", ".join(cols)))
    t0, dt = first_time(path), float(dt)
    n = len(cols[args.sda])
    t = [t0 + i * dt for i in range(n)]
    sda = [float(x) for x in cols[args.sda]]
    scl = [float(x) for x in cols[args.scl]]
    lo, mid, hi = 0.3 * args.vdd, 0.5 * args.vdd, 0.7 * args.vdd
    res = {"path": path, "n": n, "dt": dt, "t": t, "sda": sda, "scl": scl,
           "lo": lo, "mid": mid, "hi": hi, "rows": []}
    crosses = [ch for ch, v in ((args.sda, sda), (args.scl, scl)) if min(v) < mid < max(v)]
    if not crosses:
        res["mode"] = "idle"
        res["idle"] = [(ch, stats(v)) for ch, v in ((args.sda, sda), (args.scl, scl))]
        for ch, s in res["idle"]:
            res["rows"].append(("Idle high", ch, "%.4f V (mean of all %d samples)" % (s["mean"], s["n"]),
                                "%.3f-%.3f V" % (IDLE_LO_V, IDLE_HI_V), IDLE_LO_V <= s["mean"] <= IDLE_HI_V))
        return res
    res["mode"] = "frame"
    e_sda, e_scl = find_edges(t, sda, lo, mid, hi), find_edges(t, scl, lo, mid, hi)
    res["e_sda"], res["e_scl"] = e_sda, e_scl
    bits, events, anchored = decode(t, sda, args.scl, e_sda, e_scl, mid)
    res["bits"], res["events"], res["anchored"] = bits, events, anchored
    b9 = bits[:9]
    byte = 0
    for b in b9[:8]:
        byte = (byte << 1) | b["bit"]
    res["byte"], res["ack"] = byte, b9[8]["bit"] == 0
    rises = [b["t_rise"] for b in b9]
    res["period_us"] = (rises[-1] - rises[0]) / 8 * 1e6
    res["period_minmax_us"] = (min(b - a for a, b in zip(rises, rises[1:])) * 1e6,
                               max(b - a for a, b in zip(rises, rises[1:])) * 1e6)
    res["rise"] = {args.sda: [e for e in e_sda if e["kind"] == "R"],
                   args.scl: [e for e in e_scl if e["kind"] == "R"]}
    vol = []
    for p, b in enumerate(b9[:8]):
        if b["bit"]:
            continue
        name = "R/W bit 0" if p == 7 else "address bit %d" % (7 - p)
        if b["t_fall"] is None:
            vol.append({"name": name, "skip": "SCL high runs to the record end"})
            continue
        h = b["t_fall"] - b["t_rise"]
        g0, g1 = b["t_rise"] + GATE_SHRINK * h, b["t_fall"] - GATE_SHRINK * h
        xs = [v for tt, v in zip(t, sda) if g0 <= tt <= g1]
        if not xs:
            vol.append({"name": name, "skip": "no sample in the gate"})
            continue
        vol.append(dict(stats(xs), name=name, g0=g0, g1=g1))
    res["vol"] = vol
    last = max(e["t"] for e in e_sda + e_scl)
    after = [i for i, tt in enumerate(t) if tt >= last + IDLE_MARGIN_S]
    res["idle_after"] = None
    if after and t[-1] - t[after[0]] >= IDLE_MIN_S:
        res["idle_after"] = {"g0": t[after[0]], "g1": t[-1], "ch": [
            (args.sda, stats([sda[i] for i in after])), (args.scl, stats([scl[i] for i in after]))]}
    res["last_edge"] = last

    rows = res["rows"]
    for v in vol:
        if "skip" in v:
            rows.append(("V_OL", args.sda, "%s: not measured (%s)" % (v["name"], v["skip"]), "<= 0.4 V", None))
        else:
            rows.append(("V_OL", args.sda, "%s: %.1f mV" % (v["name"], v["mean"] * 1e3),
                         "<= %.1f V" % VOL_MAX_V, v["mean"] <= VOL_MAX_V))
    if res["idle_after"]:
        for ch, s in res["idle_after"]["ch"]:
            rows.append(("Idle high", ch, "%.4f V (from 5 us after the last edge)" % s["mean"],
                         "%.3f-%.3f V" % (IDLE_LO_V, IDLE_HI_V), IDLE_LO_V <= s["mean"] <= IDLE_HI_V))
    else:
        rows.append(("Idle high", "-", "not reported (< 5 us of samples from 5 us after the last edge)",
                     "%.3f-%.3f V" % (IDLE_LO_V, IDLE_HI_V), None))
    for ch, es in res["rise"].items():
        if es:
            m = max(e["rise_ns"] for e in es)
            rows.append(("Rise 30->70 %", ch, "max %.1f ns of %d edges" % (m, len(es)),
                         "<= %g ns" % RISE_MAX_NS, m <= RISE_MAX_NS))
        else:
            rows.append(("Rise 30->70 %", ch, "no complete rising edge", "<= %g ns" % RISE_MAX_NS, None))
    exp = args.expect
    want = ("%02X then ACK" % exp) if exp is not None else "ACK (no --expect)"
    got = "%02X %s" % (byte, "ACK" if res["ack"] else "NACK")
    rows.append(("Decode", args.sda, got, want, res["ack"] and (exp is None or byte == exp)))
    return res


def report(res, args):
    p = print
    p("i2c_frame: %s" % res["path"])
    p("  %d points at %g s per sample, %s..%s us; SDA %s, SCL %s; V_DD %g V -> %.3f / %.3f / %.3f V"
      % (res["n"], res["dt"], us(res["t"][0]), us(res["t"][-1]), args.sda, args.scl, args.vdd,
         res["lo"], res["mid"], res["hi"]))
    p("")
    if res["mode"] == "idle":
        p("  mode: idle (no channel crosses %.3f V)" % res["mid"])
        p("  %-4s %10s %8s %10s %10s" % ("ch", "mean_V", "sd_mV", "min_V", "max_V"))
        for ch, s in res["idle"]:
            p("  %-4s %10.4f %8.2f %10.4f %10.4f" % (ch, s["mean"], s["sd"] * 1e3, s["min"], s["max"]))
    else:
        p("  mode: frame (%s)" % res["anchored"])
        for k, ev in res["events"]:
            p("  %s at %s us" % ("START" if k == "S" else "STOP", us(ev)))
        b9 = res["bits"][:9]
        p("  SDA at SCL rising: %s | %d  -> %02X, 9th bit %s"
          % (" ".join(str(b["bit"]) for b in b9[:8]), b9[8]["bit"], res["byte"],
             "low (ACK)" if res["ack"] else "high (NACK)"))
        p("  SCL rising edges of the address byte: %s us" % ", ".join(us(b["t_rise"]) for b in b9))
        if len(res["bits"]) > 9:
            p("  (%d further bit(s) after the address byte, not decoded)" % (len(res["bits"]) - 9))
        p("  SCL period %.3f us (min %.3f, max %.3f)" % ((res["period_us"],) + res["period_minmax_us"]))
        for ch, es in res["rise"].items():
            p("  rise 30->70 %% %s: %s" % (ch, ", ".join("%.1f ns @ %s us" % (e["rise_ns"], us(e["t"])) for e in es) or "none"))
        for v in res["vol"]:
            if "skip" in v:
                p("  V_OL %s: not measured (%s)" % (v["name"], v["skip"]))
            else:
                p("  V_OL %s: %.1f mV, t=%s..%s us, n=%d, sd %.1f mV" % (
                    v["name"], v["mean"] * 1e3, us(v["g0"]), us(v["g1"]), v["n"], v["sd"] * 1e3))
                if v["mean"] > VOL_INVESTIGATE_V:
                    p("    FLAG > %.1f V on a working bus: investigate the setup (%s)" % (VOL_INVESTIGATE_V, REF))
        ia = res["idle_after"]
        if ia:
            for ch, s in ia["ch"]:
                p("  idle high %s: %.1f mV, t=%s..%s us, n=%d, sd %.2f mV" % (
                    ch, s["mean"] * 1e3, us(ia["g0"]), us(ia["g1"]), s["n"], s["sd"] * 1e3))
        else:
            p("  idle high: not reported (last edge at %s us; fewer than 5 us of samples from 5 us after it)" % us(res["last_edge"]))
    p("")
    p("  pass table (%s; limits copied from it):" % REF)
    fail = False
    for q, ch, val, lim, ok in res["rows"]:
        tag = "n/a " if ok is None else ("PASS" if ok else "FAIL")
        fail = fail or ok is False
        p("  %s  %-13s %-4s %s  (limit %s)" % (tag, q, ch, val, lim))
    if res["mode"] == "frame":
        p("  note: record the scope panel RTIMe beside the CSV rise time; it has no pass role.")
    p("")
    p("  %s %s" % ("V7" if res["mode"] == "idle" else "frame", "FAIL" if fail else "PASS"))
    p("")
    snippet(res, args)
    return 1 if fail else 0


def snippet(res, args):
    p = print
    name = os.path.basename(res["path"])
    span = "%s..%s us" % ("%+g" % round(res["t"][0] * 1e6, 2), "%+g" % round(res["t"][-1] * 1e6, 2))
    if res["mode"] == "idle":
        p("# validation snippet (paste under validation:)")
        p("  V7_idle_high_V: {%s}   # CSV mean of all %d samples of %s (i2c_frame.py, bus idle)" % (
            ", ".join("%s: %.3f" % (ch, s["mean"]) for ch, s in res["idle"]), res["n"],
            name.replace(".csv", "")))
        p("# values_csv entries (paste under the capture's log entry)")
        p("    values_csv:")
        for ch, s in res["idle"]:
            p('      - {name: mean, ch: %s, value_mV: %.1f, gate: "all %d samples, %s, no channel crosses %.2f V"}'
              % (ch, s["mean"] * 1e3, s["n"], span, res["mid"]))
        for ch, s in res["idle"]:
            p("      - {name: sd, ch: %s, value_mV: %.2f}" % (ch, s["sd"] * 1e3))
        return
    sda, scl = args.sda, args.scl
    b9 = res["bits"][:9]
    p("# values_csv entries (paste under the capture's log entry; offset_mV is validation.V5.offset_mV of %s)" % sda)
    p("    values_csv:")
    for v in res["vol"]:
        if "skip" in v:
            continue
        p('      - {name: V_OL, ch: %s, value_mV: %.1f, gate: "%s, t=%s..%s us (n=%d, sd %.1f mV)", offset_mV: TODO}'
          % (sda, v["mean"] * 1e3, v["name"], us(v["g0"]), us(v["g1"]), v["n"], v["sd"] * 1e3))
    ia = res["idle_after"]
    if ia:
        for ch, s in ia["ch"]:
            p('      - {name: idle_high, ch: %s, value_mV: %.1f, gate: "from 5 us after the last edge, t=%s..%s us (n=%d)"}'
              % (ch, s["mean"] * 1e3, us(ia["g0"]), us(ia["g1"]), s["n"]))
    for ch, role in ((sda, "SDA"), (scl, "SCL")):
        es = res["rise"][ch]
        if not es:
            continue
        p('      - {name: rise_30_70, ch: %s, value: "%s ns", max_ns: %.1f, gate: "every %s rising edge in the record (%s us); %.2f->%.2f V, linear interpolation"}'
          % (ch, ", ".join("%.1f" % e["rise_ns"] for e in es), max(e["rise_ns"] for e in es), role,
             ", ".join(us(e["t"]) for e in es), res["lo"], res["hi"]))
    p('      - {name: decode_bits, ch: %s, value: "SDA at SCL rising: %s | %d (%02X, 9th clock %s)", gate: "SCL rising %s ... %s us"}'
      % (sda, " ".join(str(b["bit"]) for b in b9[:8]), b9[8]["bit"], res["byte"],
         "low = ACK" if res["ack"] else "high = NACK", us(b9[0]["t_rise"]), us(b9[8]["t_rise"])))
    p('      - {name: SCL_period, ch: %s, value_us: %.2f, gate: "rising edges %s ... %s us"}'
      % (scl, res["period_us"], us(b9[0]["t_rise"]), us(b9[8]["t_rise"])))


def hexbyte(s):
    try:
        v = int(s, 16)
    except ValueError:
        raise argparse.ArgumentTypeError("not a hex byte: %r" % s)
    if not 0 <= v <= 0xFF:
        raise argparse.ArgumentTypeError("not a byte: %r" % s)
    return v


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("csv", help="capture.py CSV (Time(s),CH1V,CH2V,...)")
    ap.add_argument("--sda", default="CH1", help="SDA channel (default %(default)s)")
    ap.add_argument("--scl", default="CH2", help="SCL channel (default %(default)s)")
    ap.add_argument("--vdd", type=float, default=3.3, help="nominal V_DD for the 0.3/0.5/0.7 thresholds (default %(default)g)")
    ap.add_argument("--expect", type=hexbyte, help="expected address byte, hex (e.g. D6)")
    try:
        args = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    try:
        res = analyse(args.csv, args)
    except Refused as e:
        print("i2c_frame: REFUSED: %s" % e, file=sys.stderr)
        return 2
    except NoFrame as e:
        print("i2c_frame: NO FRAME: %s" % e, file=sys.stderr)
        return 2
    return report(res, args)


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""V5 noise check: the noise the board and ground path add over a no-board control
(PLAN "After V7R-001" §1; lab/procedures/dho804-setup-validation.md V5).

    python3 tools/lab/noise_floor.py --ctl <control.csv> --dut <dut.csv> [--limit-mV 5]

Both files are capture.py CSVs (`Time(s),CH1V,CH2V,...`, volts). Per channel common to both it
prints mean, sd, max - min (mV) for each file and

    excess = sqrt(max(0, sd_dut^2 - sd_ctl^2))      (mV rms; independent sources add in quadrature)

PASS when excess <= --limit-mV on every channel. The control sd is checked against the sanity
band 2.5-10 mV; outside it is FLAGGED, not failed, and the band holds only at the V7R-001
reference settings (0.5 V/div, -1.65 V offset, BW OFF, 10 us/div, 10 kpts, 2 channels).

Refuses when the sample interval or the point count differ (not the same acquisition settings).
Warns when the smallest level step differs (a sign of a different V/div). Ends with a
`validation.V5` YAML snippet for the session log (offset_mV is the control mean).

Exit: 0 all PASS; 1 any FAIL; 2 refused or bad input. Stdlib only; runs on Python 3.7.
"""
import argparse
import csv
import decimal
import math
import sys

SANITY_LO_MV, SANITY_HI_MV = 2.5, 10.0
REL_TOL = 1e-6


class Refused(Exception):
    pass


def load(path):
    """-> (dt_s as Decimal, {channel: [volts]}) from a capture.py CSV."""
    try:
        f = open(path, newline="", encoding="ascii")
    except OSError as e:
        raise Refused("cannot open %s: %s" % (path, e))
    with f:
        rows = list(csv.reader(f))
    if len(rows) < 3 or not rows[0] or not rows[0][0].startswith("Time"):
        raise Refused("%s: not a capture.py CSV (header %r)" % (path, rows[0] if rows else None))
    names = [h[:-1] if h.endswith("V") else h for h in rows[0][1:]]
    if not names:
        raise Refused("%s: no channel columns" % path)
    cols = {n: [] for n in names}
    times = []
    for i, r in enumerate(rows[1:], 2):
        if not r:
            continue
        if len(r) != len(names) + 1:
            raise Refused("%s line %d: %d fields, expected %d" % (path, i, len(r), len(names) + 1))
        try:
            times.append(decimal.Decimal(r[0]))
            for n, v in zip(names, r[1:]):
                cols[n].append(decimal.Decimal(v))
        except decimal.InvalidOperation:
            raise Refused("%s line %d: not a number: %r" % (path, i, r))
    return times[1] - times[0], cols


def step(values):
    """Smallest non-zero difference between distinct levels (the ADC step at this V/div)."""
    lv = sorted(set(values))
    diffs = [b - a for a, b in zip(lv, lv[1:])]
    return min(diffs) if diffs else None


def stats_mV(values):
    x = [float(v) * 1000.0 for v in values]
    n = len(x)
    mean = sum(x) / n
    sd = math.sqrt(sum((v - mean) ** 2 for v in x) / (n - 1)) if n > 1 else 0.0
    return {"mean": mean, "sd": sd, "pp": max(x) - min(x)}


def close(a, b, rel=REL_TOL):
    return abs(a - b) <= rel * max(abs(a), abs(b))


def analyse(ctl, dut, limit):
    dt_c, cols_c = ctl
    dt_d, cols_d = dut
    if not close(float(dt_c), float(dt_d)):
        raise Refused("sample interval differs: ctl %s s, dut %s s (not the same timebase / "
                      "memory settings)" % (dt_c, dt_d))
    n_c, n_d = len(next(iter(cols_c.values()))), len(next(iter(cols_d.values())))
    if n_c != n_d:
        raise Refused("point count differs: ctl %d, dut %d" % (n_c, n_d))
    chans = [c for c in cols_c if c in cols_d]
    if not chans:
        raise Refused("no channel in common (ctl %s, dut %s)" % (list(cols_c), list(cols_d)))
    warnings = []
    for c in [c for c in cols_c if c not in cols_d] + [c for c in cols_d if c not in cols_c]:
        warnings.append("%s is only in %s; not compared" % (c, "ctl" if c in cols_c else "dut"))
    out = []
    for c in chans:
        s_c, s_d = step(cols_c[c]), step(cols_d[c])
        if s_c is not None and s_d is not None and not close(float(s_c), float(s_d), 1e-3):
            warnings.append("%s smallest level step differs: ctl %.4g mV, dut %.4g mV (different "
                            "V/div?)" % (c, float(s_c) * 1e3, float(s_d) * 1e3))
        a, b = stats_mV(cols_c[c]), stats_mV(cols_d[c])
        excess = math.sqrt(max(0.0, b["sd"] ** 2 - a["sd"] ** 2))
        out.append({"ch": c, "ctl": a, "dut": b, "excess": excess, "pass": excess <= limit,
                    "sane": SANITY_LO_MV <= a["sd"] <= SANITY_HI_MV,
                    "step_mV": float(s_c) * 1e3 if s_c is not None else None})
    return {"dt": dt_c, "points": n_c, "channels": out, "warnings": warnings}


def r2(x):
    return round(x, 2)


def report(res, args):
    p = print
    p("noise_floor: V5 excess noise over a no-board control")
    p("  ctl  %s" % args.ctl)
    p("  dut  %s" % args.dut)
    p("  %d points at %g s per sample; limit excess <= %g mV rms" % (res["points"], float(res["dt"]), args.limit_mV))
    p("")
    p("  %-4s %-4s %9s %7s %8s" % ("ch", "file", "mean_mV", "sd_mV", "max-min"))
    for c in res["channels"]:
        for k in ("ctl", "dut"):
            s = c[k]
            p("  %-4s %-4s %9.2f %7.2f %8.2f" % (c["ch"], k, s["mean"], s["sd"], s["pp"]))
    p("")
    for c in res["channels"]:
        p("  %s excess %.2f mV rms -> %s" % (c["ch"], c["excess"], "PASS" if c["pass"] else "FAIL"))
    for c in res["channels"]:
        if not c["sane"]:
            p("  FLAG %s control sd %.2f mV is outside the sanity band %g-%g mV. At the V7R-001 "
              "reference settings this means stop and check the scope and probes; at other "
              "settings the band does not apply (record only)." % (c["ch"], c["ctl"]["sd"], SANITY_LO_MV, SANITY_HI_MV))
    p("  note: the control-sd sanity band %g-%g mV holds only at the V7R-001 reference settings "
      "(0.5 V/div, -1.65 V offset, BW OFF, 10 us/div, 10 kpts, 2 channels)." % (SANITY_LO_MV, SANITY_HI_MV))
    for w in res["warnings"]:
        p("  WARNING %s" % w)
    ok = all(c["pass"] for c in res["channels"])
    p("")
    p("  V5 %s" % ("PASS" if ok else "FAIL"))
    p("")
    p("# validation.V5 snippet (paste under validation:)")

    def m(key):
        return "{" + ", ".join("%s: %s" % (c["ch"], r2(key(c))) for c in res["channels"]) + "}"
    p("  V5:")
    p("    ctl_sd_mV: %s" % m(lambda c: c["ctl"]["sd"]))
    p("    dut_sd_mV: %s" % m(lambda c: c["dut"]["sd"]))
    p("    excess_rms_mV: %s" % m(lambda c: c["excess"]))
    p("    offset_mV: %s" % m(lambda c: c["ctl"]["mean"]))
    p("    # vpp_panel_mV: {%s}   # optional: the scope panel Vpp of the DUT capture" %
      ", ".join("%s: TODO" % c["ch"] for c in res["channels"]))
    return 0 if ok else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--ctl", required=True, help="control CSV (probes on the scope's Cal ground, no board)")
    ap.add_argument("--dut", required=True, help="DUT CSV (arm ground point, board powered)")
    ap.add_argument("--limit-mV", dest="limit_mV", type=float, default=5.0,
                    help="pass limit on the excess, mV rms (default %(default)g)")
    args = ap.parse_args(argv)
    try:
        res = analyse(load(args.ctl), load(args.dut), args.limit_mV)
    except Refused as e:
        print("noise_floor: REFUSED: %s" % e, file=sys.stderr)
        return 2
    return report(res, args)


if __name__ == "__main__":
    sys.exit(main())

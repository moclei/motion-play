#!/usr/bin/env python3
"""Validate lab/log/*.yaml session logs against the §4.6 required fields (test-workflow-audit §4.6;
markers in lab/templates/log.yaml). Branches on `kind`:

  both kinds   session_id (YYYY-MM-DD_sNN, equal to the file stem), kind, every dut.* field
               (declared_baseline is v7-clean | v6-ref | other), at least one measurement, and per
               measurement test_id (V7R-NNN), feature, raw_observation.
  kind: scope  also scope.model/firmware; validation.passed (bool) + V2_probe_ratio, V5_noise_floor_mVpp
               (number), V6_ground {method, point, length_mm}, V7_idle_high_V; every channel's
               ratio/bw_limit/signal/point; per measurement method (auto|cursor|both), values (each
               with name, ch and a value_<unit> key, or valid: false) and captures (§4.4 names
               carrying the measurement's test_id).

A string containing TODO (what capture.py leaves for the operator) is reported as pending, not as
missing. Warnings never fail: validation.passed false, and a PNG capture with no ai_read entry.

    python3 tools/lab/validate_log.py lab/log/2026-11-04_s01.yaml [...] [--allow-todo]

Exit: 0 valid; 1 errors; 3 no errors but TODOs remain (0 with --allow-todo); 2 usage/PyYAML missing.
The pre-commit hook (precommit.py) rejects staged logs with errors and only warns on TODOs.
Requires PyYAML (session logs use lists, which the lablib fallback parser does not handle).
"""
import re
import sys
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover
    yaml = None

SESSION_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_s\d{2,}$")
TEST_RE = re.compile(r"^V7R-\d{3,}$")
CAPTURE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}_(V7R-\d{3,})_[A-Za-z0-9]+(?:_[A-Za-z0-9]+)*_\d{2,}\.[A-Za-z0-9.]+$")
KINDS = ("log-only", "scope")
BASELINES = ("v7-clean", "v6-ref", "other")
METHODS = ("auto", "cursor", "both")
TODO_RE = re.compile(r"\bTODO\b")


class Report:
    def __init__(self):
        self.errors, self.todos, self.warnings = [], [], []

    def exit_code(self, allow_todo=False):
        if self.errors:
            return 1
        if self.todos and not allow_todo:
            return 3
        return 0


def _is_todo(v):
    return isinstance(v, str) and bool(TODO_RE.search(v))


def _empty(v):
    return v is None or (isinstance(v, (str, list, dict)) and len(v) == 0)


def _walk_todos(obj, path, out):
    if isinstance(obj, dict):
        for k, v in obj.items():
            _walk_todos(v, "%s.%s" % (path, k) if path else str(k), out)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            _walk_todos(v, "%s[%d]" % (path, i), out)
    elif _is_todo(obj):
        out.append(path)


def _is_num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def validate(data, stem=None):
    r = Report()
    if not isinstance(data, dict):
        r.errors.append("top level is not a mapping")
        return r

    def need(path, v):
        """True if v is present and not a TODO (so type checks may run)."""
        if _empty(v):
            r.errors.append("%s: required, missing or empty" % path)
            return False
        if isinstance(v, (dict, list)):
            return True
        return not _is_todo(v)

    sid = data.get("session_id")
    if need("session_id", sid):
        if not SESSION_RE.match(str(sid)):
            r.errors.append("session_id: %r is not YYYY-MM-DD_sNN" % sid)
        elif stem and str(sid) != stem:
            r.errors.append("session_id: %r does not match the file name %r" % (sid, stem))
    kind = data.get("kind")
    if need("kind", kind) and kind not in KINDS:
        r.errors.append("kind: %r is not one of %s" % (kind, " | ".join(KINDS)))
    scope = kind == "scope"

    dut = data.get("dut")
    if not isinstance(dut, dict):
        r.errors.append("dut: required mapping missing")
        dut = {}
    for k in ("board_id", "firmware_commit", "firmware_env", "declared_baseline"):
        v = dut.get(k)
        if need("dut." + k, v) and k == "declared_baseline" and v not in BASELINES:
            r.errors.append("dut.declared_baseline: %r is not one of %s" % (v, " | ".join(BASELINES)))

    if scope:
        sc = data.get("scope")
        if not isinstance(sc, dict):
            r.errors.append("scope: required mapping missing (kind: scope)")
        else:
            for k in ("model", "firmware"):
                need("scope." + k, sc.get(k))

        val = data.get("validation")
        if not isinstance(val, dict):
            r.errors.append("validation: required mapping missing (kind: scope)")
            val = {}
        p = val.get("passed")
        if p is None:
            r.errors.append("validation.passed: required, missing")
        elif not _is_todo(p):
            if not isinstance(p, bool):
                r.errors.append("validation.passed: must be true or false, got %r" % p)
            elif p is False:
                r.warnings.append("validation.passed is false: no measurement in this log is trusted")
        if need("validation.V2_probe_ratio", val.get("V2_probe_ratio")) and not isinstance(val["V2_probe_ratio"], dict):
            r.errors.append("validation.V2_probe_ratio: must map channels to ratios")
        v5 = val.get("V5_noise_floor_mVpp")
        if need("validation.V5_noise_floor_mVpp", v5) and not _is_num(v5):
            r.errors.append("validation.V5_noise_floor_mVpp: must be a number (mVpp), got %r" % v5)
        g = val.get("V6_ground")
        if need("validation.V6_ground", g):
            if not isinstance(g, dict):
                r.errors.append("validation.V6_ground: must be {method, point, length_mm}")
            else:
                for k in ("method", "point", "length_mm"):
                    if need("validation.V6_ground." + k, g.get(k)) and k == "length_mm" and not _is_num(g[k]):
                        r.errors.append("validation.V6_ground.length_mm: must be a number, got %r" % g[k])
        v7 = val.get("V7_idle_high_V")
        if need("validation.V7_idle_high_V", v7):
            if not isinstance(v7, dict):
                r.errors.append("validation.V7_idle_high_V: must map channels to volts")
            else:
                for ch, x in v7.items():
                    if not _is_todo(x) and not _is_num(x):
                        r.errors.append("validation.V7_idle_high_V.%s: must be a number (V), got %r" % (ch, x))

        chans = data.get("channels")
        if not isinstance(chans, dict) or not chans:
            r.errors.append("channels: required mapping missing or empty (kind: scope)")
        else:
            for ch, c in chans.items():
                if not isinstance(c, dict):
                    r.errors.append("channels.%s: must be a mapping" % ch)
                    continue
                for k in ("ratio", "bw_limit", "signal", "point"):
                    need("channels.%s.%s" % (ch, k), c.get(k))

    ms = data.get("measurements")
    if not isinstance(ms, list) or not ms:
        r.errors.append("measurements: required, at least one entry")
        ms = []
    for i, m in enumerate(ms):
        at = "measurements[%d]" % i
        if not isinstance(m, dict):
            r.errors.append("%s: must be a mapping" % at)
            continue
        tid = m.get("test_id")
        if need(at + ".test_id", tid) and not TEST_RE.match(str(tid)):
            r.errors.append("%s.test_id: %r is not V7R-NNN" % (at, tid))
        need(at + ".feature", m.get("feature"))
        need(at + ".raw_observation", m.get("raw_observation"))
        if not scope:
            continue
        meth = m.get("method")
        if need(at + ".method", meth) and meth not in METHODS:
            r.errors.append("%s.method: %r is not one of %s" % (at, meth, " | ".join(METHODS)))
        vals = m.get("values")
        if need(at + ".values", vals):
            if not isinstance(vals, list):
                r.errors.append("%s.values: must be a list" % at)
            else:
                for j, v in enumerate(vals):
                    vat = "%s.values[%d]" % (at, j)
                    if not isinstance(v, dict):
                        r.errors.append("%s: must be a mapping" % vat)
                        continue
                    for k in ("name", "ch"):
                        need("%s.%s" % (vat, k), v.get(k))
                    vkeys = [k for k in v if str(k).startswith("value_") or k == "value"]
                    for k in vkeys:
                        if not _is_num(v[k]) and not _is_todo(v[k]):
                            r.errors.append("%s.%s: must be a number, got %r" % (vat, k, v[k]))
                    if not vkeys and v.get("valid") is not False:
                        r.errors.append("%s: needs a value_<unit> key (e.g. value_mV), or valid: false" % vat)
        caps = m.get("captures")
        if need(at + ".captures", caps):
            if not isinstance(caps, list):
                r.errors.append("%s.captures: must be a list of file names" % at)
            else:
                read = {a.get("capture") for a in (m.get("ai_read") or []) if isinstance(a, dict)}
                for c in caps:
                    mm = CAPTURE_RE.match(str(c))
                    if not mm:
                        r.errors.append("%s.captures: %r is not YYYY-MM-DD_<test-id>_<arm>_<nn>.<ext> (§4.4)" % (at, c))
                    elif TEST_RE.match(str(tid or "")) and mm.group(1) != tid:
                        r.errors.append("%s.captures: %r is not for %s" % (at, c, tid))
                    if str(c).lower().endswith(".png") and c not in read:
                        r.warnings.append("%s: no ai_read entry for %s yet" % (at, c))

    _walk_todos(data, "", r.todos)
    return r


def validate_text(text, stem=None):
    if yaml is None:
        r = Report()
        r.errors.append("PyYAML is not installed; cannot validate session logs")
        return r
    try:
        data = yaml.safe_load(text)
    except yaml.YAMLError as e:
        r = Report()
        r.errors.append("YAML does not parse: %s" % str(e).replace("\n", " "))
        return r
    return validate(data, stem)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    allow = "--allow-todo" in argv
    files = [a for a in argv if a != "--allow-todo"]
    if not files or any(a.startswith("-") for a in files):
        print("usage: validate_log.py <log.yaml> [...] [--allow-todo]", file=sys.stderr)
        return 2
    if yaml is None:
        print("validate_log: PyYAML is required (pip install pyyaml)", file=sys.stderr)
        return 2
    worst = 0
    for f in files:
        p = Path(f)
        r = validate_text(p.read_text(encoding="utf-8"), p.stem)
        code = r.exit_code(allow)
        label = {0: "OK", 1: "INVALID", 3: "PENDING (TODOs)"}[code]
        print("%s: %s" % (p, label))
        for e in r.errors:
            print("  ERROR   " + e)
        for t in r.todos:
            print("  TODO    " + t)
        for w in r.warnings:
            print("  warning " + w)
        worst = 1 if 1 in (worst, code) else max(worst, code)
    return worst


if __name__ == "__main__":
    sys.exit(main())

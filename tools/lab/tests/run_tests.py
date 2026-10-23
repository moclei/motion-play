#!/usr/bin/env python3
"""Tests for tools/lab/: check_state.py fixtures here, then capture.py, validate_log.py
(+ the pre-commit log rule) and ingest_usb.py via tool_tests.py.

Each fixture under fixtures/<name>/ holds a lab/ tree and a memory/ dir and is
built to trigger exactly one checker condition. The runner asserts that the
expected tag fires exactly once and that no other tag fires at all. `clean`
must produce no findings.

Run: python3 tools/lab/tests/run_tests.py
"""
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
CHECK = HERE.parent / "check_state.py"
FIX = HERE / "fixtures"
NOW = "2026-11-20"

# fixture -> (expected tag or None, expected exit code, --now)
CASES = {
    "clean":          (None,             0, NOW),
    "stale":          ("STALE",          1, NOW),
    "open_cards":     ("OPEN-CARDS",     0, NOW),
    "lost_result":    ("LOST-RESULT",    0, "2099-01-01"),
    "checkpoint_due": ("CHECKPOINT-DUE", 0, NOW),   # >= 3 recorded since last_checkpoint
    "checkpoint_gap": ("CHECKPOINT-DUE", 0, NOW),   # > 14 days since the last notebook entry
    "cap":            ("CAP",            0, NOW),
    "stale_hash":     ("STALE-HASH",     0, NOW),
    "memory":         ("MEMORY",         0, NOW),
}

# --fresh cases: (path under fixtures/, expected exit)
FRESH = [
    ("stale_hash/gen/board-context.json", 1),  # JSON _provenance, source changed
    ("stale_hash/gen/net-narrative.md", 0),    # Markdown front matter, fresh
    ("stale_hash/gen/net.png", 0),             # image + .meta.json sidecar, fresh
    ("clean/lab/STATE.md", 2),                 # hand-written: no provenance
]


def run(args):
    p = subprocess.run([sys.executable, str(CHECK)] + args, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, universal_newlines=True)
    return p.returncode, p.stdout


def tags(output):
    out = []
    for line in output.splitlines():
        if line.startswith("[") and "]" in line:
            out.append(line[1:line.index("]")])
    return out


def main():
    failures = 0
    seen = set(p.name for p in FIX.iterdir() if p.is_dir())
    missing = seen.symmetric_difference(CASES)
    if missing:
        print("FAIL fixtures/cases out of sync: %s" % sorted(missing))
        failures += 1

    for name, (tag, code, now) in CASES.items():
        d = FIX / name
        rc, out = run(["--root", str(d / "lab"), "--memory-dir", str(d / "memory"), "--now", now])
        found = tags(out)
        ok = rc == code and (found == [tag] if tag else found == [])
        failures += not ok
        print("%s %-15s expect %-15s got %s (exit %d)" % (
            "PASS" if ok else "FAIL", name, tag or "nothing", found or "nothing", rc))
        if not ok:
            print("  " + out.replace("\n", "\n  "))

    for rel, code in FRESH:
        rc, out = run(["--root", str(FIX / rel.split("/")[0] / "lab"), "--fresh", str(FIX / rel)])
        ok = rc == code
        failures += not ok
        print("%s --fresh %-34s expect exit %d got %d" % ("PASS" if ok else "FAIL", rel, code, rc))
        if not ok:
            print("  " + out)

    # The fallback parser must agree with PyYAML on the card template.
    sys.path.insert(0, str(HERE.parent))
    import lablib
    tpl = (HERE.parents[2] / "lab" / "templates" / "card.md").read_text(encoding="utf-8")
    fm, _ = lablib.split_front_matter(tpl)
    mini = lablib._mini_yaml(fm)
    if lablib.yaml is not None:
        ok = mini == lablib.yaml.safe_load(fm)
        print("%s mini-parser == PyYAML on lab/templates/card.md" % ("PASS" if ok else "FAIL"))
        failures += not ok

    import tool_tests
    failures += tool_tests.main()

    print("\n%s: %d failure(s)" % ("OK" if not failures else "FAILED", failures))
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())

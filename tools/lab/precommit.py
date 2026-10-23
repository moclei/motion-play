#!/usr/bin/env python3
"""Pre-commit rules for lab/ (context-strategy.md §4.2). Called by .githooks/pre-commit.

Reads the staged index (not the working tree) and rejects the commit when:
  1. a staged card's front matter moves to `status: recorded|abandoned` and
     lab/STATE.md is not staged with `as_of` = the highest such card ID;
  2. a card staged as `recorded` has an empty (or still `<hash>`) Result commit,
     or no `lab/evidence/<ID>/` reference in its `## Conclusion`;
  3. a staged card's V7R-NNN number is used by another card file;
  4. a staged session log lab/log/*.yaml fails validate_log.py (missing or malformed
     §4.6 required fields). TODO placeholders left by capture.py only warn.

`Result commit: self` is valid (the recording commit can't hold its own hash;
see the self-reference note in lab/templates/card.md).
Exit 0 = allow, 1 = reject. Bypass (don't): git commit --no-verify.
"""
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lablib  # noqa: E402
import validate_log  # noqa: E402

CARD_PATH_RE = re.compile(r"^lab/cards/(V7R-(\d{3,})-.+\.md)$")
LOG_PATH_RE = re.compile(r"^lab/log/([^/]+)\.yaml$")
STATE = "lab/STATE.md"


def git(*args, check=False):
    p = subprocess.run(["git"] + list(args), stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                       universal_newlines=True)
    if check and p.returncode != 0:
        raise RuntimeError(p.stderr.strip())
    return p.returncode, p.stdout


def blob(spec):
    rc, out = git("show", spec)
    return out if rc == 0 else None


def main():
    rc, out = git("diff", "--cached", "--name-only", "--diff-filter=ACMR")
    if rc != 0:
        print("lab pre-commit: could not read the staged diff", file=sys.stderr)
        return 1
    staged = out.split()
    has_head = git("rev-parse", "--verify", "-q", "HEAD")[0] == 0

    errors, warnings, transitions = [], [], []
    staged_cards = []
    for path in staged:
        m = CARD_PATH_RE.match(path)
        if not m:
            continue
        num = int(m.group(2))
        cid = lablib.fmt_id(num)
        new_text = blob(":" + path) or ""
        new_fm = lablib.front_matter(new_text)
        old_text = blob("HEAD:" + path) if has_head else None
        old_status = str(lablib.front_matter(old_text).get("status") or "").strip() if old_text else ""
        status = str(new_fm.get("status") or "").strip()
        staged_cards.append((path, num, cid))

        if not new_fm:
            errors.append("%s: front matter missing or unparseable" % path)
            continue
        if str(new_fm.get("test_id", "")).strip() != cid:
            warnings.append("%s: test_id %r does not match the filename" % (path, new_fm.get("test_id")))

        # Rule 1 input: a move into recorded|abandoned
        if status in lablib.RECORDED and status != old_status:
            transitions.append((num, cid, path, status))

        # Rule 2: a recorded card needs a Result commit and an evidence citation
        if status == "recorded":
            rcv = lablib.result_commit_value(new_text)
            if rcv is None:
                errors.append("%s: recorded, but has no 'Result commit:' line" % path)
            elif rcv in ("", "<hash>"):
                errors.append("%s: recorded, but 'Result commit:' is empty (write `self`)" % path)
            _, body = lablib.split_front_matter(new_text)
            concl = lablib.section(body, "Conclusion")
            if ("lab/evidence/%s/" % cid) not in concl:
                errors.append("%s: recorded, but its ## Conclusion cites no lab/evidence/%s/ file" % (path, cid))
            elif not git("ls-files", "lab/evidence/%s/" % cid)[1].strip():
                warnings.append("%s: lab/evidence/%s/ has no files in the index" % (path, cid))

    # Rule 4: staged session logs pass validate_log.py (TODOs warn only)
    for path in staged:
        m = LOG_PATH_RE.match(path)
        if not m:
            continue
        rep = validate_log.validate_text(blob(":" + path) or "", m.group(1))
        errors.extend("%s: %s" % (path, e) for e in rep.errors)
        if rep.todos:
            warnings.append("%s: %d TODO field(s) still to fill (%s%s)" % (
                path, len(rep.todos), ", ".join(rep.todos[:4]), ", ..." if len(rep.todos) > 4 else ""))
        warnings.extend("%s: %s" % (path, w) for w in rep.warnings)

    # Rule 1: STATE.md staged with as_of = highest transitioned ID
    if transitions:
        top = max(transitions)
        names = ", ".join("%s (%s)" % (p, s) for _, _, p, s in sorted(transitions))
        if STATE not in staged:
            errors.append("%s moves to recorded|abandoned, but %s is not staged. "
                          "Update STATE.md (as_of: %s, map cells, open_cards) in the same commit."
                          % (names, STATE, top[1]))
        else:
            as_of = lablib.front_matter(blob(":" + STATE) or "").get("as_of")
            if str(as_of).strip() != top[1]:
                errors.append("%s moves to recorded|abandoned, but staged %s has as_of: %s (expected %s)"
                              % (names, STATE, as_of, top[1]))

    # Rule 3: duplicate V7R-NNN among card files in the index
    if staged_cards:
        _, idx = git("ls-files", "lab/cards/")
        by_num = {}
        for p in idx.split():
            m = CARD_PATH_RE.match(p)
            if m:
                by_num.setdefault(int(m.group(2)), []).append(p)
        for path, num, cid in staged_cards:
            others = [p for p in by_num.get(num, []) if p != path]
            if others:
                errors.append("%s: duplicate ID %s, also used by %s (next free ID = highest + 1)"
                              % (path, cid, ", ".join(others)))
        # de-duplicate the symmetric message when both files are staged
        errors = list(dict.fromkeys(errors))

    for w in warnings:
        print("lab pre-commit: warning: " + w, file=sys.stderr)
    if errors:
        print("lab pre-commit: REJECTED", file=sys.stderr)
        for e in errors:
            print("  - " + e, file=sys.stderr)
        print("  (rules: docs/research/v7-retry/context-strategy.md §4.2; card template: lab/templates/card.md;"
              " log fields: lab/templates/log.yaml, tools/lab/validate_log.py)",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Session-start check for lab/ (context-strategy.md §4.2, §8.2).

Usage:
  python3 tools/lab/check_state.py                 # check the real lab/
  python3 tools/lab/check_state.py --load          # check, then print the default L1 load (§6.3)
  python3 tools/lab/check_state.py --fresh <file>  # provenance check on one generated file (§8.2)
  python3 tools/lab/check_state.py --root <dir>/lab --memory-dir <dir> --now YYYY-MM-DD  # fixtures

Findings are printed one per line as `[TAG] message`. Tags:
  STALE           STATE.md as_of is behind the highest recorded|abandoned card. HARD FAILURE (exit 1).
  OPEN-CARDS      open_cards does not match the cards whose status is pre-registered|run.
  LOST-RESULT     a card in `run` with no commit (card or its evidence) in the last 7 days.
  CHECKPOINT-DUE  >= 3 recorded cards since last_checkpoint, or > 14 days since the last notebook entry.
  CAP             a STATE.md section (or the whole file) is over its cap.
  STALE-HASH      a generated file cited in Lookups has a source hash that no longer matches.
  MEMORY          the auto-memory directory mentions v7 (it must not hold v7 state, §2.5).
  CARD / AS-OF    housekeeping: unparseable card, test_id/filename mismatch, as_of ahead of the cards.
Everything except STALE is a warning (exit 0).

Cap counting rule: a section's count excludes its heading, its one-line field
definition (the first non-blank, non-table line under the heading), the table
header row and separator row, and blank lines. `rows` caps count table data
rows (or content lines if the section has no table); `lines` caps count all
remaining non-blank lines. The whole file warns past 150 lines.
"""
import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lablib  # noqa: E402

FILE_CAP = 150
LOST_DAYS = 7
CHECKPOINT_EVERY = 3
GAP_DAYS = 14
MEMORY_RE = re.compile(r"v7|V7R-|BQ.*NACK", re.IGNORECASE)
CAP_RE = re.compile(r"≤\s*(\d+)\s*(lines|rows)")
SEP_RE = re.compile(r"^\|[\s:|-]+\|?$")
IMAGE_EXT = {".png", ".jpg", ".jpeg", ".svg", ".gif", ".webp"}


# ---------------------------------------------------------------- git helpers

def git(base, *args):
    try:
        out = subprocess.run(["git", "-C", str(base)] + list(args),
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                             universal_newlines=True, check=False)
    except OSError:
        return ""
    return out.stdout.strip() if out.returncode == 0 else ""


def last_touch(base, paths):
    """Latest commit time (epoch) touching any of paths; falls back to the
    newest mtime when nothing is committed."""
    best = 0.0
    for p in paths:
        t = git(base, "log", "-1", "--format=%ct", "--", str(p))
        if t:
            best = max(best, float(t))
    if best:
        return best
    for p in paths:
        if p.exists():
            for f in ([p] if p.is_file() else p.rglob("*")):
                if f.is_file():
                    best = max(best, f.stat().st_mtime)
    return best or None


def resolve_self(base, path, which):
    if which == "prereg":
        out = git(base, "log", "--diff-filter=A", "--format=%h", "--", str(path))
        return out.splitlines()[-1] if out else "(uncommitted)"
    out = git(base, "log", "-1", "-G^status: recorded", "--format=%h", "--", str(path))
    return out or "(uncommitted)"


# ---------------------------------------------------------------- lab model

class Card:
    def __init__(self, path, num):
        self.path = path
        self.num = num
        self.id = lablib.fmt_id(num)
        self.text = path.read_text(encoding="utf-8")
        self.fm = lablib.front_matter(self.text)
        self.status = str(self.fm.get("status") or "").strip()


def load_cards(root, findings):
    cards = []
    cdir = root / "cards"
    if not cdir.is_dir():
        return cards
    for p in sorted(cdir.iterdir()):
        m = lablib.CARD_RE.match(p.name)
        if not m:
            continue  # .gitkeep and anything that isn't V7R-NNN-*.md
        c = Card(p, int(m.group(1)))
        if not c.fm:
            findings.append(("CARD", "%s: front matter missing or unparseable" % p.name))
        elif str(c.fm.get("test_id", "")).strip() != c.id:
            findings.append(("CARD", "%s: test_id %r does not match filename" % (p.name, c.fm.get("test_id"))))
        cards.append(c)
    return sorted(cards, key=lambda c: c.num)


def state_sections(body):
    """Yield (heading_line, [lines]) for each `## ` section."""
    cur, lines = None, []
    for line in body.splitlines():
        if line.startswith("## "):
            if cur is not None:
                yield cur, lines
            cur, lines = line, []
        elif cur is not None:
            lines.append(line)
    if cur is not None:
        yield cur, lines


def count_section(lines, unit):
    content = [l for l in lines if l.strip()]
    if content and not content[0].lstrip().startswith("|"):
        content = content[1:]  # the one-line field definition
    table = [l for l in content if l.lstrip().startswith("|")]
    rest = [l for l in content if not l.lstrip().startswith("|")]
    data_rows = table[1:] if table else []
    data_rows = [r for r in data_rows if not SEP_RE.match(r.strip())]
    if unit == "rows":
        return len(data_rows) if table else len(rest)
    return len(rest) + len(data_rows)


# ---------------------------------------------------------------- provenance (§8.2)

def provenance(path):
    """Return the provenance dict for a generated file, or None if it has none."""
    try:
        if path.suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            prov = data.get("_provenance") if isinstance(data, dict) else None
        elif path.suffix == ".md":
            fm = lablib.front_matter(path.read_text(encoding="utf-8"))
            prov = fm.get("_provenance", fm) if isinstance(fm, dict) else None
        elif path.suffix.lower() in IMAGE_EXT:
            prov = None
            for side in (path.with_name(path.name + ".meta.json"), path.with_suffix(".meta.json")):
                if side.is_file():
                    data = json.loads(side.read_text(encoding="utf-8"))
                    prov = data.get("_provenance", data) if isinstance(data, dict) else None
                    break
        else:
            prov = None
    except (ValueError, OSError, UnicodeDecodeError):
        return None
    if isinstance(prov, dict) and prov.get("source") and prov.get("source_sha256"):
        return prov
    return None


def check_fresh(path, base):
    """Return (status, message): status in FRESH | STALE | NONE."""
    prov = provenance(path)
    if prov is None:
        return "NONE", "%s: no provenance (not a generated file, or missing _provenance)" % path
    src = Path(prov["source"])
    src = src if src.is_absolute() else base / src
    if not src.is_file():
        return "STALE", "%s: source %s is missing" % (path, prov["source"])
    actual = hashlib.sha256(src.read_bytes()).hexdigest()
    if actual != str(prov["source_sha256"]).strip().lower():
        return "STALE", "%s: source %s hash %s.. != recorded %s.." % (
            path, prov["source"], actual[:12], str(prov["source_sha256"])[:12])
    return "FRESH", "%s: source %s matches" % (path, prov["source"])


def lookup_paths(lines):
    rows = [l for l in lines if l.lstrip().startswith("|")]
    for r in rows[1:]:
        if SEP_RE.match(r.strip()):
            continue
        cols = [c.strip() for c in r.strip().strip("|").split("|")]
        if len(cols) < 2:
            continue
        for tok in re.split(r"[\s,;]+", cols[1].replace("`", "")):
            if "/" in tok or "." in tok:
                yield tok


# ---------------------------------------------------------------- checks

def run_checks(root, base, memory_dir, today):
    findings = []
    state_path = root / "STATE.md"
    if not state_path.is_file():
        print("ERROR: %s not found" % state_path)
        sys.exit(2)
    state_text = state_path.read_text(encoding="utf-8")
    fm_text, body = lablib.split_front_matter(state_text)
    sfm = lablib.parse_yaml(fm_text) if fm_text else {}
    as_of = lablib.id_num(sfm.get("as_of"))
    last_cp = lablib.id_num(sfm.get("last_checkpoint"))
    open_listed = sfm.get("open_cards") or []
    if as_of is None:
        findings.append(("STALE", "STATE.md as_of %r is not a V7R-NNN ID" % sfm.get("as_of")))
        as_of = -1
    if last_cp is None:
        last_cp = 0

    cards = load_cards(root, findings)

    # 1. as_of vs highest recorded|abandoned -> STALE (hard)
    done = [c for c in cards if c.status in lablib.RECORDED]
    if done:
        top = done[-1]
        if as_of < top.num:
            behind = [c.id for c in done if c.num > as_of]
            findings.append(("STALE", "as_of %s is behind %s (%s %s); reconcile STATE from: %s" % (
                sfm.get("as_of"), top.id, top.path.name, top.status, ", ".join(behind))))
        elif as_of > top.num:
            findings.append(("AS-OF", "as_of %s is ahead of the highest recorded|abandoned card %s" % (
                sfm.get("as_of"), top.id)))
    elif as_of > 0:
        findings.append(("AS-OF", "as_of %s but no card is recorded|abandoned" % sfm.get("as_of")))

    # 2. open_cards vs cards in pre-registered|run
    actual_open = {c.id for c in cards if c.status in lablib.OPEN}
    listed = {str(x).strip() for x in open_listed if x is not None}
    if actual_open != listed:
        parts = []
        if actual_open - listed:
            parts.append("open but not listed: " + ", ".join(sorted(actual_open - listed)))
        if listed - actual_open:
            parts.append("listed but not open: " + ", ".join(sorted(listed - actual_open)))
        findings.append(("OPEN-CARDS", "; ".join(parts)))

    # 3. card in `run` with no commit for 7 days -> possibly lost result
    now_epoch = dt.datetime.combine(today, dt.time(12)).timestamp()
    for c in cards:
        if c.status == "run":
            t = last_touch(base, [c.path, root / "evidence" / c.id])
            age = (now_epoch - t) / 86400 if t else None
            if age is None or age > LOST_DAYS:
                findings.append(("LOST-RESULT", "%s is in `run` with no commit for %s days: possibly lost result" % (
                    c.id, "?" if age is None else int(age))))

    # 4. checkpoint due
    since = [c for c in cards if c.status == "recorded" and c.num > last_cp]
    reasons = []
    if len(since) >= CHECKPOINT_EVERY:
        reasons.append("%d recorded since last_checkpoint %s (%s)" % (
            len(since), sfm.get("last_checkpoint"), ", ".join(c.id for c in since)))
    nb = root / "NOTEBOOK.md"
    if as_of > 0 and nb.is_file():
        dates = re.findall(r"^## (\d{4}-\d{2}-\d{2})", nb.read_text(encoding="utf-8"), re.MULTILINE)
        if dates:
            last = max(dt.date.fromisoformat(d) for d in dates)
            gap = (today - last).days
            if gap > GAP_DAYS:
                reasons.append("%d days since the last notebook entry (%s)" % (gap, last))
    if reasons:
        findings.append(("CHECKPOINT-DUE", "; ".join(reasons) + ". No new pre-registration until it runs (§4.3)"))

    # 5. caps
    total = len(state_text.splitlines())
    if total > FILE_CAP:
        findings.append(("CAP", "STATE.md is %d lines (cap ~%d)" % (total, FILE_CAP)))
    lookups = []
    for heading, lines in state_sections(body):
        if heading[3:].strip().startswith("9."):
            lookups = lines
        m = CAP_RE.search(heading)
        if not m:
            continue
        cap, unit = int(m.group(1)), m.group(2)
        n = count_section(lines, unit)
        if n > cap:
            name = re.sub(r"\s*\(.*$", "", heading[3:]).strip()
            findings.append(("CAP", "section '%s' has %d %s (cap %d)" % (name, n, unit, cap)))

    # 6. stale hashes of generated files cited in Lookups
    for tok in lookup_paths(lookups):
        p = base / tok
        if p.is_file():
            status, msg = check_fresh(p, base)
            if status == "STALE":
                findings.append(("STALE-HASH", msg))

    # 7. memory directory mentions v7
    info = []
    if memory_dir.is_dir():
        for f in sorted(memory_dir.glob("*.md")):
            hits = [str(i + 1) for i, l in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines())
                    if MEMORY_RE.search(l)]
            if hits:
                findings.append(("MEMORY", "%s mentions v7 (lines %s); v7 state belongs in lab/, not memory" % (
                    f.name, ",".join(hits))))
    else:
        info.append("memory dir %s not found; memory check skipped" % memory_dir)

    return sfm, cards, findings, info


# ---------------------------------------------------------------- --load (§6.3)

def print_load(root, base, cards, today):
    def resolved(c):
        notes = []
        if str(c.fm.get("prereg_commit") or "").strip() == "self":
            notes.append("prereg_commit self = %s" % resolve_self(base, c.path, "prereg"))
        rc = lablib.result_commit_value(c.text)
        if rc == "self" and c.status == "recorded":
            notes.append("Result commit self = %s" % resolve_self(base, c.path, "result"))
        return ("  [" + "; ".join(notes) + "]") if notes else ""

    print("\n=== LOAD: open cards (full) ===")
    opened = [c for c in cards if c.status in lablib.OPEN]
    if not opened:
        print("(none)")
    for c in opened:
        print("\n----- %s (%s)%s -----" % (c.path.relative_to(base), c.status, resolved(c)))
        print(c.text.rstrip())

    print("\n=== LOAD: last two recorded cards (front matter + Conclusion) ===")
    rec = [c for c in cards if c.status == "recorded"][-2:]
    if not rec:
        print("(none)")
    for c in rec:
        fm, body = lablib.split_front_matter(c.text)
        print("\n----- %s%s -----" % (c.path.relative_to(base), resolved(c)))
        print("---\n" + (fm or "").rstrip() + "\n---")
        print(lablib.section(body, "Conclusion").rstrip() or "(no ## Conclusion)")

    print("\n=== LOAD: today's log ===")
    logs = sorted((root / "log").glob(today.isoformat() + "_*.yaml")) if (root / "log").is_dir() else []
    if not logs:
        print("(none for %s)" % today)
    for p in logs:
        print("\n----- %s -----" % p.relative_to(base))
        print(p.read_text(encoding="utf-8").rstrip())


# ---------------------------------------------------------------- main

def default_memory_dir(base):
    slug = str(base.resolve()).replace("/", "-")
    return Path.home() / ".claude" / "projects" / slug / "memory"


def main(argv=None):
    here = Path(__file__).resolve()
    repo = here.parents[2]
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--root", type=Path, default=repo / "lab", help="lab/ directory to check (default: repo lab/)")
    ap.add_argument("--memory-dir", type=Path, default=None,
                    help="auto-memory dir to grep (default: $LAB_MEMORY_DIR or ~/.claude/projects/<repo-slug>/memory)")
    ap.add_argument("--now", default=None, help="override today's date (YYYY-MM-DD), for fixtures")
    ap.add_argument("--load", action="store_true", help="after the check, print the default L1 load (§6.3)")
    ap.add_argument("--fresh", type=Path, metavar="FILE", help="provenance check on one generated file and exit")
    a = ap.parse_args(argv)

    root = a.root.resolve()
    base = root.parent  # paths in Lookups and _provenance.source are relative to the repo root

    if a.fresh:
        f = a.fresh.resolve()
        if not f.is_file():
            print("ERROR: %s not found" % a.fresh)
            return 2
        status, msg = check_fresh(f, base)
        print("%s: %s" % ("NO PROVENANCE" if status == "NONE" else status, msg))
        return {"FRESH": 0, "STALE": 1, "NONE": 2}[status]

    today = dt.date.fromisoformat(a.now) if a.now else dt.date.today()
    mem = a.memory_dir or (Path(os.environ["LAB_MEMORY_DIR"]) if os.environ.get("LAB_MEMORY_DIR")
                           else default_memory_dir(base))

    sfm, cards, findings, info = run_checks(root, base, mem.expanduser(), today)
    print("check_state: %s  as_of=%s  last_checkpoint=%s  cards=%d  date=%s" % (
        root, sfm.get("as_of"), sfm.get("last_checkpoint"), len(cards), today))
    for tag, msg in findings:
        print("[%s] %s" % (tag, msg))
    for line in info:
        print("info: " + line)
    stale = any(t == "STALE" for t, _ in findings)
    warns = sum(1 for t, _ in findings if t != "STALE")
    if stale:
        print("RESULT: STALE. Blocks new work: reconcile STATE.md from the cards above, commit, then proceed.")
    else:
        print("RESULT: OK (%d warning%s)" % (warns, "" if warns == 1 else "s"))

    if a.load:
        print_load(root, base, cards, today)
    return 1 if stale else 0


if __name__ == "__main__":
    sys.exit(main())

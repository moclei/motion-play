#!/usr/bin/env python3
"""USB-stick ingest, the fallback to capture.py (test-workflow-audit §4.5, §4.9, §5 item 5).

    python3 tools/lab/ingest_usb.py --src /Volumes/<STICK> --test V7R-012 --arm A1 \\
        --at 2026-11-04T10:42 [--files p6img.png p6wav.csv] [--dry-run]

--at is required: it is the time match and it dates the §4.4 names.

1. Copies every file on the stick that is not already in the inbox into
   lab/inbox/usb-<YYYYMMDD-HHMMSS>/ (names and mtimes kept). Never writes to or deletes from the stick.
2. Picks the files for one capture:
   --files   the names the operator reported (REPORT field 3). The scope appends an index digit
             (`p6img.png` -> `p6img0.png`), so a name without its digit matches `<stem><digits>.<ext>`.
   --at      the Mac local time of the save. Stick timestamps have run about 1 h ahead of Mac time
             after a clock set (cause unknown), so a file matches if its mtime is within --window-s
             of --at shifted by any of --offset-min (default 0 and +60 minutes).
   With --files, --at only breaks ties between candidates of the same name. Without --files, every
   file whose time matches is taken.
3. Stops without renaming anything when the match is ambiguous: two candidates for one reported
   name, two files of one extension, or files that match only under different offsets. It prints
   the candidates with their times; rerun with a narrower --files/--at/--offset-min.
4. Copies the chosen files into lab/captures/<ID>/YYYY-MM-DD_<ID>_<arm>_<nn>.<ext> (§4.4), one
   shared <nn>, and appends the mapping to lab/captures/<ID>/INGEST.tsv. The date is the --at date.

The inbox copy stays as the verbatim record (gitignored, backed up). Add the printed names to the
session log's `captures` list. Exit: 0 ingested (or dry run), 1 nothing matched / ambiguous, 2 usage.
"""
import argparse
import datetime
import os
import re
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TEST_RE = re.compile(r"^V7R-\d{3,}$")
ARM_RE = re.compile(r"^[A-Za-z0-9]+(_[A-Za-z0-9]+)*$")
SCOPE_EXT = {".png", ".bmp", ".jpg", ".csv", ".bin", ".wfm", ".stp"}
SKIP_NAMES = {".Spotlight-V100", ".Trashes", ".fseventsd", "System Volume Information", ".TemporaryItems"}


def stick_files(src):
    out = []
    for dirpath, dirnames, filenames in os.walk(str(src)):
        dirnames[:] = [d for d in dirnames if d not in SKIP_NAMES and not d.startswith(".")]
        for f in filenames:
            if f.startswith("._") or f.startswith(".") or f in SKIP_NAMES:
                continue
            out.append(Path(dirpath) / f)
    return sorted(out)


def already_in_inbox(inbox, rel, st):
    for d in inbox.glob("usb-*"):
        p = d / rel
        if p.is_file():
            s = p.stat()
            if s.st_size == st.st_size and int(s.st_mtime) == int(st.st_mtime):
                return p
    return None


def copy_to_inbox(src, inbox, stamp, dry):
    """Returns {relative path on stick: inbox path} for every stick file."""
    dest = inbox / ("usb-" + stamp)
    mapping, copied = {}, 0
    for f in stick_files(src):
        rel = f.relative_to(src)
        st = f.stat()
        prev = already_in_inbox(inbox, rel, st)
        if prev:
            mapping[rel] = prev
            continue
        target = dest / rel
        if not dry:
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(str(f), str(target))
        mapping[rel] = target
        copied += 1
    return mapping, copied, dest


def name_matches(reported, actual):
    """`p6img.png` matches `p6img.png` and `p6img<digits>.png`, case-insensitively."""
    r, a = Path(reported.lower()), Path(actual.lower())
    if r.suffix != a.suffix:
        return False
    if r.stem == a.stem:
        return True
    return a.stem.startswith(r.stem) and a.stem[len(r.stem):].isdigit()


def time_offsets(mtime, at, offsets_min, window_s):
    """The offsets (minutes) under which a file's stick time matches --at."""
    hits = []
    for off in offsets_min:
        if abs((mtime - datetime.timedelta(minutes=off) - at).total_seconds()) <= window_s:
            hits.append(off)
    return hits


def choose(cands, args, at):
    """cands: [(rel, mtime)]. Returns (chosen [(rel, mtime, offsets)], problems [str])."""
    problems, chosen = [], []
    if args.files:
        for rep in args.files:
            m = [(rel, mt) for rel, mt in cands if name_matches(rep, rel.name)]
            if at is not None:
                timed = [(rel, mt, time_offsets(mt, at, args.offset_min, args.window_s)) for rel, mt in m]
                near = [x for x in timed if x[2]]
                if len(near) == 1:
                    chosen.append(near[0])
                    continue
                if not near and len(m) == 1:
                    chosen.append((m[0][0], m[0][1], []))
                    problems.append("warning: %s matched %s, but its stick time %s is not near --at under "
                                    "any offset" % (rep, m[0][0], m[0][1]))
                    continue
                m = [(x[0], x[1]) for x in (near or timed)]
            if len(m) == 1:
                chosen.append((m[0][0], m[0][1], []))
            elif not m:
                problems.append("no file on the stick matches %r" % rep)
            else:
                problems.append("ambiguous: %r matches %s" % (rep, ", ".join("%s (%s)" % (r, t) for r, t in m)))
    else:
        for rel, mt in cands:
            offs = time_offsets(mt, at, args.offset_min, args.window_s)
            if offs:
                chosen.append((rel, mt, offs))
        if not chosen:
            problems.append("no scope file on the stick has a time near %s (offsets %s min, window %d s)"
                            % (at, args.offset_min, args.window_s))
    offsets = {tuple(o) for _, _, o in chosen if o}
    if len(offsets) > 1:
        msg = "files match only under different clock offsets: %s" % ", ".join(
            "%s (%s, %s min)" % (r, t, o) for r, t, o in chosen)
        # reported names are authoritative, so with --files this only warns
        problems.append(("warning: " if args.files else "ambiguous: ") + msg)
    exts = {}
    for rel, _, _ in chosen:
        exts.setdefault(rel.suffix.lower(), []).append(str(rel))
    for ext, names in exts.items():
        if len(names) > 1:
            problems.append("ambiguous: %d %s files picked (%s); one capture has one file per type"
                            % (len(names), ext, ", ".join(names)))
    return chosen, problems


def next_seq(cap_dir, prefix):
    pat = re.compile(re.escape(prefix) + r"_(\d{2,})\.")
    used = [int(m.group(1)) for p in cap_dir.glob(prefix + "_*") for m in [pat.match(p.name)] if m]
    return max(used, default=0) + 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--src", required=True, help="mounted stick, e.g. /Volumes/HANTEK")
    ap.add_argument("--test", required=True, help="card ID, V7R-NNN")
    ap.add_argument("--arm", required=True, help="A1 | B | A2 | S1… | val_V5 (§4.4)")
    ap.add_argument("--at", required=True, help="Mac local time of the save, YYYY-MM-DDTHH:MM[:SS]; "
                    "also dates the §4.4 names (the stick clock is not trusted)")
    ap.add_argument("--files", nargs="+", help="file names the scope showed (REPORT field 3)")
    ap.add_argument("--offset-min", default="0,60",
                    help="stick-minus-Mac clock offsets to try, minutes (default %(default)s)")
    ap.add_argument("--window-s", type=int, default=300, help="time match window, seconds (default %(default)s)")
    ap.add_argument("--dry-run", action="store_true", help="show what would happen; copy nothing")
    ap.add_argument("--root", default=str(HERE.parents[1]), help=argparse.SUPPRESS)
    ap.add_argument("--now", help=argparse.SUPPRESS)   # tests: fixed inbox stamp
    args = ap.parse_args(argv)

    if not TEST_RE.match(args.test) or not ARM_RE.match(args.arm):
        print("ingest: --test must be V7R-NNN and --arm letters/digits/underscores", file=sys.stderr)
        return 2
    try:
        args.offset_min = [int(x) for x in args.offset_min.split(",") if x.strip()]
        at = datetime.datetime.fromisoformat(args.at)
    except ValueError as e:
        print("ingest: %s" % e, file=sys.stderr)
        return 2
    src = Path(args.src)
    if not src.is_dir():
        print("ingest: %s is not a directory (is the stick mounted?)" % src, file=sys.stderr)
        return 2
    root = Path(args.root)
    now = datetime.datetime.fromisoformat(args.now) if args.now else datetime.datetime.now()
    inbox = root / "lab" / "inbox"

    mapping, copied, dest = copy_to_inbox(src, inbox, now.strftime("%Y%m%d-%H%M%S"), args.dry_run)
    print("ingest: %d stick file(s), %d new %s %s" % (
        len(mapping), copied, "would be copied to" if args.dry_run else "copied to", dest))

    cands = []
    for rel in mapping:
        if rel.suffix.lower() in SCOPE_EXT:
            mt = datetime.datetime.fromtimestamp((src / rel).stat().st_mtime)
            cands.append((rel, mt))
    chosen, problems = choose(cands, args, at)
    hard = [p for p in problems if not p.startswith("warning:")]
    for p in problems:
        print("  " + p, file=sys.stderr if p in hard else sys.stdout)
    if hard or not chosen:
        print("ingest: nothing renamed. Candidates on the stick:", file=sys.stderr)
        for rel, mt in cands:
            print("    %-30s %s" % (rel, mt.strftime("%Y-%m-%d %H:%M:%S")), file=sys.stderr)
        return 1

    cap_dir = root / "lab" / "captures" / args.test
    prefix = "%s_%s_%s" % (at.strftime("%Y-%m-%d"), args.test, args.arm)
    seq = next_seq(cap_dir, prefix) if cap_dir.is_dir() else 1
    stem = "%s_%02d" % (prefix, seq)
    rows, names = [], []
    for rel, mt, offs in chosen:
        ext = rel.suffix.lower()
        name = stem + ext
        target = cap_dir / name
        if target.exists():
            print("ingest: %s exists; nothing renamed" % target, file=sys.stderr)
            return 1
        names.append(name)
        rows.append((name, str(mapping[rel]), str(rel), mt.strftime("%Y-%m-%dT%H:%M:%S"),
                     ",".join("+%d" % o for o in offs) or "none"))
    if not args.dry_run:
        cap_dir.mkdir(parents=True, exist_ok=True)
        for name, inbox_path, *_ in rows:
            shutil.copy2(inbox_path, str(cap_dir / name))
        log = cap_dir / "INGEST.tsv"
        new = not log.exists()
        with log.open("a", encoding="utf-8") as fh:
            if new:
                fh.write("capture\tinbox_path\tstick_name\tstick_mtime\tmatched_offset_min\tingested_at\n")
            for row in rows:
                fh.write("\t".join(row + (now.strftime("%Y-%m-%dT%H:%M:%S"),)) + "\n")
    for name, _, rel, mt, offs in rows:
        print("  %s %s <- %s (stick %s, offset %s min)" % (
            "would write" if args.dry_run else "wrote", cap_dir / name, rel, mt, offs))
    print("  captures: [%s]" % ", ".join(names))
    return 0


if __name__ == "__main__":
    sys.exit(main())

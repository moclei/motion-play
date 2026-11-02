#!/usr/bin/env python3
"""Scaffold a new lab investigation from lab/templates/STATE.md and NOTEBOOK.md.

    python3 tools/lab/new_investigation.py --name power --prefix PWR --title "Battery and power path"

Creates lab/investigations/<name>/STATE.md and NOTEBOOK.md. The STATE front matter is the
sentinel state: as_of and last_checkpoint <PREFIX>-000, open_cards [], status open, and the
given prefix and title. Its cards are then lab/cards/<PREFIX>-NNN-<slug>.md, numbered from 001.

Refuses (exit 2, nothing written):
  - a name that is not lowercase letters/digits/hyphens, or a folder that already exists;
  - a prefix that is not 2-6 characters [A-Z][A-Z0-9]+, or that is already in use: declared by
    an investigation's STATE, or the prefix of any card file in lab/cards/;
  - any existing investigation whose STATE declares no `prefix` (adding a second investigation
    would leave it unidentifiable; add `prefix:` to its front matter first).

It writes files only; it never commits. Check with `python3 tools/lab/check_state.py --inv <name>`,
then commit both files. Exit: 0 created, 2 refused/usage.
"""
import argparse
import datetime
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import lablib  # noqa: E402

NAME_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
TEMPLATES = ("STATE.md", "NOTEBOOK.md")
FILLED = ("<PREFIX>", "<TITLE>", "<NAME>", "<YYYY-MM-DD>")


def card_prefixes(root):
    cdir = Path(root) / "cards"
    out = set()
    if cdir.is_dir():
        for p in cdir.iterdir():
            m = lablib.CARD_RE.match(p.name)
            if m:
                out.add(m.group("prefix"))
    return out


def refusals(root, name, prefix, title):
    """Every reason not to scaffold (empty list = go)."""
    why = []
    if not NAME_RE.match(name):
        why.append("--name %r: use lowercase letters, digits and hyphens (it is the folder name)" % name)
    if not lablib.PREFIX_RE.match(prefix):
        why.append("--prefix %r: must be 2-6 characters, an uppercase letter then uppercase letters/digits" % prefix)
    if not title.strip() or any(c in title for c in '"\\\n'):
        why.append("--title must be non-empty, one line, without '\"' or '\\'")
    invs = lablib.investigations(root)
    if (Path(root) / lablib.INVESTIGATIONS_DIR / name).exists():
        why.append("lab/%s/%s/ already exists" % (lablib.INVESTIGATIONS_DIR, name))
    used = lablib.prefixes(invs)
    if prefix in used:
        why.append("prefix %s is already declared by %s" % (
            prefix, ", ".join("lab/%s/%s/STATE.md" % (lablib.INVESTIGATIONS_DIR, i.name) for i in used[prefix])))
    elif prefix in card_prefixes(root):
        why.append("prefix %s is already used by card files in lab/cards/ (%s-NNN-*.md)" % (prefix, prefix))
    for inv in invs:
        if inv.prefix is None:
            why.append("lab/%s/%s/STATE.md declares no `prefix`; add it to its front matter first, or that "
                       "investigation can't be told apart once a second one exists" % (lablib.INVESTIGATIONS_DIR, inv.name))
    return why


def render(text, name, prefix, title, today):
    # front matter `title:` is quoted so a title with ': ' or ' #' stays one YAML string
    text = re.sub(r"(?m)^title: <TITLE>\s*$", 'title: "%s"' % title, text, count=1)
    for k, v in (("<PREFIX>", prefix), ("<TITLE>", title), ("<NAME>", name), ("<YYYY-MM-DD>", today)):
        text = text.replace(k, v)
    return text


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--name", required=True, help="folder name under lab/investigations/, e.g. power")
    ap.add_argument("--prefix", required=True, help="card ID prefix, e.g. PWR (cards PWR-001, PWR-002, ...)")
    ap.add_argument("--title", required=True, help='one-line title, e.g. "Battery and power path"')
    ap.add_argument("--root", type=Path, default=HERE.parents[1] / "lab", help="lab/ directory (default: repo lab/)")
    ap.add_argument("--templates", type=Path, default=HERE.parents[1] / "lab" / "templates",
                    help="templates directory (default: repo lab/templates/)")
    ap.add_argument("--now", help=argparse.SUPPRESS)  # tests: fixed date, YYYY-MM-DD
    a = ap.parse_args(argv)

    root = a.root.resolve()
    title = a.title.strip()
    why = refusals(root, a.name, a.prefix, a.title)
    missing = [t for t in TEMPLATES if not (a.templates / t).is_file()]
    if missing:
        why.append("template(s) missing in %s: %s" % (a.templates, ", ".join(missing)))
    if why:
        print("new_investigation: REFUSED, nothing written:", file=sys.stderr)
        for w in why:
            print("  - " + w, file=sys.stderr)
        return 2

    today = a.now or datetime.date.today().isoformat()
    out = {}
    for t in TEMPLATES:
        text = render((a.templates / t).read_text(encoding="utf-8"), a.name, a.prefix, title, today)
        left = [k for k in FILLED if k in text]
        if left:
            print("new_investigation: template %s left %s unfilled; nothing written" % (t, ", ".join(left)),
                  file=sys.stderr)
            return 2
        out[t] = text
    fm = lablib.front_matter(out["STATE.md"])
    if fm.get("prefix") != a.prefix or fm.get("title") != title or fm.get("as_of") != lablib.fmt_id(0, a.prefix):
        print("new_investigation: rendered STATE front matter does not parse back (%r); nothing written" % fm,
              file=sys.stderr)
        return 2

    d = root / lablib.INVESTIGATIONS_DIR / a.name
    d.mkdir(parents=True)
    for t, text in out.items():
        (d / t).write_text(text, encoding="utf-8")
        print("  wrote %s" % (d / t))
    print("new_investigation: %s (%s, %s) created; first card is %s." % (
        a.name, a.prefix, title, lablib.next_id(root, a.prefix)))
    print("  Next: python3 tools/lab/check_state.py --inv %s, then commit both files." % a.name)
    return 0


if __name__ == "__main__":
    sys.exit(main())

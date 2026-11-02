"""Shared helpers for the lab/ tooling (check_state.py, precommit.py).

IDs are `<PREFIX>-NNN`. Each investigation is a folder lab/investigations/<name>/
whose STATE.md front matter declares its `prefix`, `title` and `status`
(open|closed); the folders are the registry (`investigations(root)`).

Stdlib only. PyYAML is used when importable; otherwise a minimal parser
handles the subset our front matter uses (scalars, comments, nested maps,
flow lists like `[]` or `[V7R-001, V7R-002]`).
"""
import datetime
import re
from pathlib import Path

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - exercised only without PyYAML
    yaml = None

PREFIX_PAT = r"[A-Z][A-Z0-9]{1,5}"
ID_PAT = r"(?P<prefix>%s)-(?P<num>\d{3,})" % PREFIX_PAT
CARD_RE = re.compile(r"^%s-.+\.md$" % ID_PAT)   # card filename: groups prefix, num
ID_RE = re.compile(r"^%s$" % ID_PAT)            # bare ID: groups prefix, num
PREFIX_RE = re.compile(r"^%s$" % PREFIX_PAT)
INVESTIGATIONS_DIR = "investigations"        # relative to the lab root
# Phase 1 fallback (lab-multi-investigation): while the real v7 STATE has no
# `prefix`, a lone investigation without one is treated as V7R. Removed in Phase 3.
LEGACY_PREFIX = "V7R"
RECORDED = ("recorded", "abandoned")
OPEN = ("pre-registered", "run")


def split_front_matter(text):
    """Return (front_matter_text, body) split on the first two `---` lines.

    Splits on whole lines only, so `--- RUN ---` in a card body is never
    mistaken for a delimiter. Returns (None, text) if there is no front matter.
    """
    lines = text.splitlines(True)
    if not lines or lines[0].strip() != "---":
        return None, text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[1:i]), "".join(lines[i + 1:])
    return None, text


def _strip_comment(value):
    # A ` #` outside quotes starts a comment (YAML rule).
    out, quote = [], None
    for i, ch in enumerate(value):
        if quote:
            if ch == quote:
                quote = None
        elif ch in "\"'":
            quote = ch
        elif ch == "#" and (i == 0 or value[i - 1] in " \t"):
            break
        out.append(ch)
    return "".join(out).strip()


def _scalar(v):
    if v == "" or v == "~" or v == "null":
        return None
    if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
        return v[1:-1]
    if v.startswith("[") and v.endswith("]"):
        inner = v[1:-1].strip()
        return [_scalar(x.strip()) for x in inner.split(",")] if inner else []
    if re.fullmatch(r"-?\d+", v):
        return int(v)
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", v):
        return datetime.date(*map(int, v.split("-")))
    return v


def _mini_yaml(text):
    root = {}
    stack = [(-1, root)]
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        line = raw.strip()
        if ":" not in line:
            continue
        key, _, rest = line.partition(":")
        rest = _strip_comment(rest)
        while stack and stack[-1][0] >= indent:
            stack.pop()
        parent = stack[-1][1]
        if rest == "":
            child = {}
            parent[key.strip()] = child
            stack.append((indent, child))
        else:
            parent[key.strip()] = _scalar(rest)
    # Empty nested maps with no children were really null values.
    def fix(d):
        for k, v in list(d.items()):
            if isinstance(v, dict):
                if not v:
                    d[k] = None
                else:
                    fix(v)
    fix(root)
    return root


def parse_yaml(text):
    if yaml is not None:
        data = yaml.safe_load(text)
        return data if isinstance(data, dict) else {}
    return _mini_yaml(text)


def front_matter(text):
    fm, _ = split_front_matter(text)
    if fm is None:
        return {}
    try:
        return parse_yaml(fm)
    except Exception:
        return {}


def parse_id(card_id):
    """'PWR-012' -> ('PWR', 12); anything else -> None."""
    m = ID_RE.match(str(card_id).strip()) if card_id is not None else None
    return (m.group("prefix"), int(m.group("num"))) if m else None


def id_num(card_id, prefix=LEGACY_PREFIX):
    """'V7R-012' -> 12. The ID's prefix must equal `prefix` (None = any);
    anything else -> None."""
    p = parse_id(card_id)
    if p is None or (prefix is not None and p[0] != prefix):
        return None
    return p[1]


def fmt_id(n, prefix=LEGACY_PREFIX):
    return "%s-%03d" % (prefix, n)


# ---------------------------------------------------------------- registry

class Investigation:
    """One lab/investigations/<name>/ folder, from its STATE front matter."""

    def __init__(self, name, fm, state_path=None, notebook_path=None, text=None):
        fm = fm if isinstance(fm, dict) else {}
        self.name = name
        self.fm = fm
        self.text = text
        raw = fm.get("prefix")
        self.prefix = str(raw).strip() if raw is not None and str(raw).strip() else None
        self.prefix_fallback = False
        self.title = str(fm.get("title") or name).strip()
        self.status = str(fm.get("status") or "open").strip().lower()
        self.state_path = state_path
        self.notebook_path = notebook_path

    @property
    def is_open(self):
        return self.status != "closed"

    def __repr__(self):
        return "Investigation(%s, %s, %s)" % (self.name, self.prefix, self.status)


def build_registry(entries):
    """entries: [(name, state_text, state_path, notebook_path)] -> [Investigation],
    sorted by name, with the Phase 1 V7R fallback applied."""
    invs = []
    for name, text, sp, nb in sorted(entries, key=lambda e: e[0]):
        invs.append(Investigation(name, front_matter(text or ""), sp, nb, text))
    if len(invs) == 1 and invs[0].prefix is None:  # Phase 1 fallback, removed in Phase 3
        invs[0].prefix = LEGACY_PREFIX
        invs[0].prefix_fallback = True
    return invs


def investigations(root):
    """Discover lab/investigations/*/STATE.md under the lab root `root`."""
    d = Path(root) / INVESTIGATIONS_DIR
    entries = []
    if d.is_dir():
        for sub in sorted(d.iterdir()):
            sp = sub / "STATE.md"
            if sub.is_dir() and sp.is_file():
                entries.append((sub.name, sp.read_text(encoding="utf-8"), sp, sub / "NOTEBOOK.md"))
    return build_registry(entries)


def prefixes(invs):
    """{prefix: [Investigation]} for investigations that have a prefix."""
    out = {}
    for inv in invs:
        if inv.prefix:
            out.setdefault(inv.prefix, []).append(inv)
    return out


def next_id(root, prefix):
    """Next free `<prefix>-NNN`: highest such card filename in lab/cards/ + 1."""
    top = 0
    cdir = Path(root) / "cards"
    if cdir.is_dir():
        for p in cdir.iterdir():
            m = CARD_RE.match(p.name)
            if m and m.group("prefix") == prefix:
                top = max(top, int(m.group("num")))
    return fmt_id(top + 1, prefix)


def section(body, heading_prefix):
    """Return the text of the `## <heading_prefix>...` section (up to the next
    `## ` heading, or end of file), or '' if absent."""
    out, inside = [], False
    for line in body.splitlines():
        if line.startswith("## "):
            if inside:
                break
            inside = line[3:].strip().startswith(heading_prefix)
            if inside:
                out.append(line)
            continue
        if inside:
            out.append(line)
    return "\n".join(out)


RESULT_COMMIT_RE = re.compile(r"Result commit:\s*(.*)$", re.MULTILINE)


def result_commit_value(text):
    """The Result commit value with any trailing HTML comment removed,
    or None if the line is missing."""
    m = RESULT_COMMIT_RE.search(text)
    if not m:
        return None
    v = re.sub(r"<!--.*?(-->|$)", "", m.group(1)).strip()
    return v

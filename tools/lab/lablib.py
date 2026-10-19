"""Shared helpers for the lab/ tooling (check_state.py, precommit.py).

Stdlib only. PyYAML is used when importable; otherwise a minimal parser
handles the subset our front matter uses (scalars, comments, nested maps,
flow lists like `[]` or `[V7R-001, V7R-002]`).
"""
import re

try:
    import yaml  # type: ignore
except ImportError:  # pragma: no cover - exercised only without PyYAML
    yaml = None

CARD_RE = re.compile(r"^V7R-(\d{3,})-.+\.md$")
ID_RE = re.compile(r"^V7R-(\d{3,})$")
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


def id_num(card_id):
    """'V7R-012' -> 12; anything else -> None."""
    m = ID_RE.match(str(card_id).strip()) if card_id is not None else None
    return int(m.group(1)) if m else None


def fmt_id(n):
    return "V7R-%03d" % n


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

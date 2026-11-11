#!/usr/bin/env python3
"""
kicad_io.py - the one place the KiCad tools load and save KiCad files (kicad10-tooling PLAN
"One I/O module").

It wraps kicad-tools' raw s-expression layer (``kicad_tools.sexp.SExp`` trees). Writers and board
readers work on the raw tree with the helpers below; kicad-tools' typed views (``schema.Schematic``
and friends) may wrap a ``Doc``'s tree for reads only, never to write (PLAN "Which layer").

Guards
- Pin check, at import: the installed kicad-tools must be ``PIN``, or ``KiCadIOVersionError``.
- Format check, at load: each file kind accepts only the format versions in ``FORMATS`` (the ones
  the regression harness has load/save-tested), or ``KiCadIOFormatError``. A newer file (KiCad 11,
  say) is refused rather than edited blind.
- Lock guard, at save: ``KiCadOpenError`` while any ``~*.kicad_sch.lck`` / ``~*.kicad_pcb.lck``
  is in the target's folder (KiCad has the project open).
- Version-unchanged check, at save: the tree's ``(version N)`` must be the one loaded, so a KiCad 9
  file can't leave as KiCad 10.

Splice save (PLAN OQ-7). kicad-tools records each top-level item's source span at parse. At save,
a top-level item whose serialization is unchanged is written as its original text, with the
whitespace that preceded it; a changed or new item is serialized by kicad-tools at depth 1. The
result is tree-identical to a plain kicad-tools save, an unedited save is byte-identical to the
input, and an edit's diff stays inside the edited items. After a save to the Doc's own path, the
Doc's baseline is the file just written.

Raw-tree traps (PLAN "Raw-layer traps"):
- An atom built as ``SExp(value=<float>)`` is written with 6 significant digits. Set numbers with
  ``set_num`` (exact text) or build nodes from text with ``node()``.
- A property's hide flag has three forms: ``(hide yes)`` inside ``effects`` (KiCad 8/9), a bare
  ``hide`` inside ``effects`` (KiCad 6/7 and files last saved by kiutils), and on KiCad 10
  schematics/libraries ``(hide yes)`` on the property itself. ``is_hidden`` reads all three;
  ``hide``/``make_property`` write the Doc's own form and never add a second flag.

Usage from another tools/ folder (run with tools/.venv/bin/python)::

    sys.path.insert(0, str(<repo>/"tools/kicad-io"))
    import kicad_io as kio
    doc = kio.load_schematic(path)
    ...edit doc.tree with the helpers...
    kio.save(doc)
"""

from __future__ import annotations

import importlib.metadata
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple, Union

PIN = "0.29.0"
REQUIREMENTS = "tools/requirements.txt"


class KiCadIOError(RuntimeError):
    """Base class of the I/O module's refusals."""


class KiCadIOVersionError(KiCadIOError):
    """The installed kicad-tools is not the pinned version."""


class KiCadIOFormatError(KiCadIOError):
    """A file's format version is not one the harness has tested, or a save would change it."""


class KiCadOpenError(KiCadIOError):
    """KiCad has the project open (a lock file exists in its folder)."""


def check_pin(installed: Optional[str] = None) -> str:
    """Raise KiCadIOVersionError unless kicad-tools (or ``installed``, for tests) is ``PIN``."""
    if installed is None:
        try:
            installed = importlib.metadata.version("kicad-tools")
        except importlib.metadata.PackageNotFoundError:
            installed = None
    if installed != PIN:
        raise KiCadIOVersionError(
            "kicad-tools {} is installed; kicad_io is pinned to {}. Build the venv from {} "
            "(kicad10-tooling PLAN \"Pin and upgrades\" for an upgrade)".format(installed, PIN, REQUIREMENTS))
    return installed


check_pin()

from kicad_tools.core.atomic_write import atomic_write_text  # noqa: E402
from kicad_tools.sexp import SExp, escape_string, parse_string, read_text_exact, source_span  # noqa: E402

# ---------------------------------------------------------------------------
# Formats
# ---------------------------------------------------------------------------

SCH, SYM, PCB = "schematic", "symbol_lib", "board"
ROOT_TAG = {SCH: "kicad_sch", SYM: "kicad_symbol_lib", PCB: "kicad_pcb"}

# Format versions the regression harness has load/save-tested, per kind (tools/kicad-regress
# test_kicad_io.py). KiCad 8 (power-supply project, stock-era libraries), 9 (v7, v8, sensor boards,
# KiCad 9.0.4 stock symbols), 10 (scratch conversions by kicad-cli 10.0.8, its stock symbols);
# 20211014 is the KiCad 6 symbol-library format of the easyeda2kicad parts under resources/.
FORMATS = {
    SCH: {20231120: 8, 20250114: 9, 20260306: 10},
    PCB: {20240108: 8, 20241229: 9, 20260206: 10},
    SYM: {20211014: 6, 20231120: 8, 20241209: 9, 20251024: 10},
}


def check_format(kind: str, version: Optional[int], path: Union[str, Path] = "") -> int:
    """The KiCad major version for ``version``, or KiCadIOFormatError."""
    known = FORMATS[kind]
    if version not in known:
        raise KiCadIOFormatError(
            "{}: {} format version {} is not one kicad_io has tested ({}). Test it with the "
            "regression harness before adding it to kicad_io.FORMATS".format(
                path, kind, version, ", ".join(str(v) for v in sorted(known))))
    return known[version]


# ---------------------------------------------------------------------------
# Doc, load
# ---------------------------------------------------------------------------

@dataclass
class _Item:
    node: SExp      # the top-level node as loaded (held, so its id() stays unique)
    compact: str    # its compact serialization when loaded
    lead: str       # the text between the previous item (or the root tag) and this item
    text: str       # this item's text, "(" to ")"


@dataclass
class Doc:
    """A loaded KiCad file: its raw tree plus what the splice save needs."""
    path: Path
    kind: str
    tree: SExp
    text: str                       # the file text the spans refer to (the baseline)
    version: int                    # the format version loaded; save refuses any other
    major: int                      # KiCad major version of that format (8, 9, 10)
    head: str = ""                  # text up to and including the root tag, e.g. "(kicad_sch"
    tail: str = ""                  # text after the last item, e.g. "\n)\n"
    spans: List[Tuple[int, int]] = field(default_factory=list)  # per top-level item, in text
    _by_id: Dict[int, _Item] = field(default_factory=dict, repr=False)      # loaded node -> item
    _by_text: Dict[str, _Item] = field(default_factory=dict, repr=False)    # compact -> first item

    @property
    def is_k10(self) -> bool:
        return self.major >= 10


_ROOT_RE = re.compile(r"\s*\(\s*([A-Za-z_]+)")


def _baseline(doc: Doc, text: str, children: Sequence[SExp], spans: Sequence[Tuple[int, int]]) -> None:
    m = _ROOT_RE.match(text)
    head_end = m.end() if m else 0
    doc.text = text
    doc.spans = list(spans)
    doc.head = text[:head_end]
    doc.tail = text[spans[-1][1]:] if spans else text[head_end:]
    doc._by_id, doc._by_text = {}, {}
    prev = head_end
    for c, (s, e) in zip(children, spans):
        it = _Item(c, c.to_string(compact=True), text[prev:s], text[s:e])
        doc._by_id[id(c)] = it
        doc._by_text.setdefault(it.compact, it)
        prev = e


def tree_version(tree: SExp) -> Optional[int]:
    v = child(tree, "version")
    a = atom(v) if v is not None else None
    try:
        return int(a) if a is not None else None
    except (TypeError, ValueError):
        return None


def _load(path: Union[str, Path], kind: str) -> Doc:
    path = Path(path)
    text = read_text_exact(path)
    tree = parse_string(text)
    if tree.name != ROOT_TAG[kind]:
        raise KiCadIOFormatError("{}: not a {} (root is ({} ...))".format(path, kind, tree.name))
    version = tree_version(tree)
    major = check_format(kind, version, path)
    spans = [source_span(c) for c in tree.children]
    if any(s is None for s in spans):
        raise KiCadIOError("{}: kicad-tools recorded no source span for a top-level item".format(path))
    doc = Doc(path=path, kind=kind, tree=tree, text=text, version=version, major=major)
    _baseline(doc, text, tree.children, spans)
    return doc


def load_schematic(path: Union[str, Path]) -> Doc:
    return _load(path, SCH)


def load_symbol_lib(path: Union[str, Path]) -> Doc:
    return _load(path, SYM)


def load_board(path: Union[str, Path]) -> Doc:
    return _load(path, PCB)


def load(path: Union[str, Path]) -> Doc:
    """Load by extension (.kicad_sch, .kicad_sym, .kicad_pcb)."""
    kind = {".kicad_sch": SCH, ".kicad_sym": SYM, ".kicad_pcb": PCB}.get(Path(path).suffix)
    if kind is None:
        raise KiCadIOFormatError("{}: not a .kicad_sch, .kicad_sym or .kicad_pcb".format(path))
    return _load(path, kind)


# ---------------------------------------------------------------------------
# Lock guard, save
# ---------------------------------------------------------------------------

LOCK_GLOBS = ("~*.kicad_sch.lck", "~*.kicad_pcb.lck")


def lock_files(path: Union[str, Path]) -> List[Path]:
    """KiCad lock files in the project folder of ``path`` (a file or a folder)."""
    p = Path(path).resolve()
    folder = p if p.is_dir() else p.parent
    return sorted(f for g in LOCK_GLOBS for f in folder.glob(g))


def assert_not_open(path: Union[str, Path]) -> None:
    locks = lock_files(path)
    if locks:
        raise KiCadOpenError("KiCad has this project open ({}); close it and try again".format(
            ", ".join(p.name for p in locks)))


def _check_version(doc: Doc) -> None:
    v = tree_version(doc.tree)
    if v != doc.version:
        raise KiCadIOFormatError("{}: the tree's format version is {}, but {} was loaded; kicad_io "
                                 "does not change a file's format".format(doc.path, v, doc.version))
    if doc.tree.name != ROOT_TAG[doc.kind]:
        raise KiCadIOFormatError("{}: root is ({} ...), not {}".format(doc.path, doc.tree.name, ROOT_TAG[doc.kind]))


def render(doc: Doc) -> Tuple[str, List[Tuple[int, int]]]:
    """The splice-save text of ``doc`` and each top-level item's span in it."""
    preserve = doc.kind == PCB          # as kicad-tools' save_pcb (untouched copper arcs)
    parts = [doc.head]
    pos = len(doc.head)
    spans = []
    for c in doc.tree.children:
        compact = c.to_string(compact=True)
        hit = doc._by_id.get(id(c))
        if hit is None or hit.compact != compact:
            hit = doc._by_text.get(compact)     # unchanged text, but a new or moved node
        if hit is not None:
            lead, body = hit.lead, hit.text
        else:
            lead = "\n\t"
            body = c.to_string(compact=True) if c._should_inline() else \
                c.to_string(indent=1, preserve_source=preserve).lstrip("\t")
        parts.append(lead)
        pos += len(lead)
        spans.append((pos, pos + len(body)))
        parts.append(body)
        pos += len(body)
    parts.append(doc.tail if doc.tree.children else "\n)\n")
    text = "".join(parts)
    if not text.endswith("\n"):
        text += "\n"
    return text, spans


def plain_text(doc: Doc) -> str:
    """kicad-tools' own serialization of the tree (what its save_* would write), for comparisons."""
    return doc.tree.to_string(preserve_source=doc.kind == PCB)


def _write(doc: Doc, target: Path) -> None:
    text, spans = render(doc)
    atomic_write_text(target, text, encoding="utf-8", newline="")
    if target.resolve() == doc.path.resolve():
        _baseline(doc, text, doc.tree.children, spans)


def save(doc: Doc, path: Union[str, Path, None] = None) -> Path:
    """Splice-save ``doc`` to ``path`` (default: where it was loaded from)."""
    target = Path(path) if path is not None else doc.path
    assert_not_open(target)
    _check_version(doc)
    _write(doc, target)
    return target


def save_project(docs: Iterable[Doc]) -> List[Path]:
    """Save several docs (each to its own path) after one guard and version check over all of them,
    so a refusal writes nothing."""
    docs = list(docs)
    for folder in sorted({d.path.resolve().parent for d in docs}):
        assert_not_open(folder)
    for d in docs:
        _check_version(d)
    seen, out = set(), []
    for d in docs:
        key = str(d.path.resolve())
        if key in seen:
            continue
        seen.add(key)
        _write(d, d.path)
        out.append(d.path)
    return out


# ---------------------------------------------------------------------------
# Raw-tree helpers: find
# ---------------------------------------------------------------------------

def kids(n: SExp, name: str) -> List[SExp]:
    return [c for c in n.children if c.name == name]


def child(n: SExp, name: str) -> Optional[SExp]:
    for c in n.children:
        if c.name == name:
            return c
    return None


def atoms(n: SExp) -> List[SExp]:
    return [c for c in n.children if c.is_atom]


def atom(n: SExp, i: int = 0):
    """The i-th atom child's value (str, int or float), or None."""
    a = atoms(n)
    return a[i].value if i < len(a) else None


def atom_text(n: SExp, i: int = 0) -> Optional[str]:
    """The i-th atom child as written in the file (numbers keep their original text)."""
    a = atoms(n)
    if i >= len(a):
        return None
    x = a[i]
    if x._original_str is not None:
        return x._original_str
    return x.value if isinstance(x.value, str) else num(x.value)


def at_xy(n: SExp) -> Tuple[float, float, float]:
    """(x, y, angle) of n's ``(at x y [angle])``."""
    a = child(n, "at")
    vals = [float(c.value) for c in atoms(a)]
    return vals[0], vals[1], (vals[2] if len(vals) > 2 else 0.0)


# ---------------------------------------------------------------------------
# Raw-tree helpers: set atoms, build nodes
# ---------------------------------------------------------------------------

def num(x: Union[int, float, str]) -> str:
    """Number text that keeps every digit of ``x`` (no exponent; integral floats without '.0').
    A str is taken as exact number text and only checked."""
    if isinstance(x, str):
        float(x)
        return x
    if isinstance(x, bool):
        raise TypeError("num() of a bool")
    if isinstance(x, int):
        return str(x)
    x = float(x)
    if x != x or x in (float("inf"), float("-inf")):
        raise ValueError("num() of {}".format(x))
    t = repr(x)
    if "e" in t or "E" in t:
        t = ("%.17f" % x).rstrip("0")
    if t.endswith(".0"):
        t = t[:-2]
    t = t.rstrip(".")
    return "0" if t in ("-0", "") else t


def q(s: str) -> str:
    """A KiCad quoted string."""
    return '"' + escape_string(str(s)) + '"'


def _atom_index(n: SExp, i: int) -> int:
    idx = [k for k, c in enumerate(n.children) if c.is_atom]
    if i >= len(idx):
        raise IndexError("({} ...) has no atom {}".format(n.name, i))
    return idx[i]


def set_str(n: SExp, i: int, value: str) -> None:
    """Replace the i-th atom child of n with a quoted string."""
    n.children[_atom_index(n, i)] = SExp(value=str(value), _originally_quoted=True)


def set_bare(n: SExp, i: int, value: str) -> None:
    """Replace the i-th atom child of n with a bare symbol (yes, no, input, ...)."""
    n.children[_atom_index(n, i)] = SExp(value=str(value), _originally_bare=True)


def set_num(n: SExp, i: int, value: Union[int, float, str]) -> None:
    """Replace the i-th atom child of n with a number written as ``num(value)`` (exact text)."""
    text = num(value)
    v = float(text) if any(ch in text for ch in ".eE") else int(text)
    n.children[_atom_index(n, i)] = SExp(value=v, _original_str=text)


def node(text: str) -> SExp:
    """Build an item from KiCad-form text; number atoms keep the text given."""
    return parse_string(text)


# KiCad's top-level item order (eeschema / pcbnew writers): items of one kind stay together.
SCH_ORDER = ["version", "generator", "generator_version", "uuid", "paper", "title_block", "lib_symbols",
             "junction", "no_connect", "bus_entry", "wire", "bus", "image", "polyline", "text", "text_box",
             "label", "global_label", "hierarchical_label", "netclass_flag", "rule_area", "symbol", "sheet",
             "sheet_instances", "symbol_instances", "embedded_fonts", "embedded_files"]
PCB_ORDER = ["version", "generator", "generator_version", "general", "paper", "title_block", "layers",
             "setup", "property", "net", "footprint", "gr_line", "gr_arc", "gr_circle", "gr_rect", "gr_poly",
             "gr_curve", "gr_text", "gr_text_box", "image", "dimension", "segment", "arc", "via", "zone",
             "group", "generated", "embedded_fonts", "embedded_files"]


def insert_item(root: SExp, item: SExp) -> None:
    """Insert a top-level item after the last sibling of its kind, else at its place in KiCad's
    order (schematic or board, from the root tag)."""
    last = None
    for i, c in enumerate(root.children):
        if c.name == item.name:
            last = i
    if last is not None:
        root.children.insert(last + 1, item)
        return
    order = PCB_ORDER if root.name == "kicad_pcb" else SCH_ORDER
    rank = order.index(item.name) if item.name in order else len(order)
    for i, c in enumerate(root.children):
        if c.name in order and order.index(c.name) > rank:
            root.children.insert(i, item)
            return
    root.children.append(item)


def remove_items(root: SExp, items: Iterable[SExp]) -> int:
    """Remove these child nodes (by identity); returns how many were removed."""
    ids = {id(x) for x in items}
    before = len(root.children)
    root.children = [c for c in root.children if id(c) not in ids]
    return before - len(root.children)


# ---------------------------------------------------------------------------
# Raw-tree helpers: hide flags (three forms) and properties
# ---------------------------------------------------------------------------

def _is_bare_hide(c: SExp) -> bool:
    return c.is_atom and c.value == "hide" and not c._originally_quoted


def _flag_yes(n: Optional[SExp]) -> bool:
    return n is not None and atom(n) == "yes"


def is_hidden(n: SExp) -> bool:
    """A property, ``pin_numbers``, ``pin_names`` or ``effects`` node is hidden, in any of the three
    forms: ``(hide yes)`` on the node, ``(hide yes)`` in its ``effects``, a bare ``hide`` in either."""
    if _flag_yes(child(n, "hide")) or any(_is_bare_hide(c) for c in n.children):
        return True
    eff = child(n, "effects")
    return eff is not None and is_hidden(eff)


def _property_level_hide(doc: Doc) -> bool:
    return doc.kind == PCB or doc.is_k10


def _bare_hide(doc: Doc) -> bool:
    return doc.kind in (SCH, SYM) and doc.major < 8


def hide(doc: Doc, n: SExp) -> bool:
    """Hide a property (or ``pin_numbers`` / ``pin_names``) in ``doc``'s own form. Returns True if
    the tree changed. Never adds a flag beside an existing one: an existing ``(hide no)`` is set to
    yes where it is; an already-hidden node is left alone."""
    if is_hidden(n):
        return False
    for holder in (n, child(n, "effects")):
        h = child(holder, "hide") if holder is not None else None
        if h is not None:
            set_bare(h, 0, "yes")
            return True
    if n.name != "property":                       # pin_numbers, pin_names: the flag is on the node
        n.children.append(SExp(value="hide", _originally_bare=True) if _bare_hide(doc) else node("(hide yes)"))
        return True
    if _property_level_hide(doc):
        # KiCad 10 schematic symbols and boards: (at ...) [(layer ...)] (hide yes) (show_name no) ...
        idx = 0
        for i, c in enumerate(n.children):
            if c.name in ("at", "layer"):
                idx = i + 1
        n.children.insert(idx, node("(hide yes)"))
        return True
    eff = child(n, "effects")
    if eff is None:
        eff = node(effects_text())
        n.children.append(eff)
    eff.children.append(SExp(value="hide", _originally_bare=True) if _bare_hide(doc) else node("(hide yes)"))
    return True


_hide = hide
FONT_SIZE = 1.27


def effects_text(hide: bool = False, justify: Optional[str] = None, size: float = FONT_SIZE) -> str:
    """``(effects (font (size s s)) [(justify ...)] [(hide yes)])`` (the KiCad 8/9 form)."""
    j = " (justify {})".format(justify) if justify else ""
    h = " (hide yes)" if hide else ""
    return "(effects (font (size {0} {0})){1}{2})".format(num(size), j, h)


def make_property(doc: Doc, key: str, value: str, x: Union[float, str], y: Union[float, str],
                  angle: Union[float, str] = 0, hide: bool = False, effects: Optional[str] = None) -> SExp:
    """A schematic property node in ``doc``'s form. ``effects`` is optional effects text without a
    hide flag (default: the 1.27 mm font)."""
    if doc.kind == PCB:
        raise KiCadIOError("make_property builds schematic/library properties; boards are Phase 10's")
    eff = effects if effects is not None else effects_text()
    at = "(at {} {} {})".format(num(x), num(y), num(angle))
    if doc.is_k10:
        flags = "(hide yes) " if hide else ""
        return node("(property {} {} {} {}(show_name no) (do_not_autoplace no) {})".format(
            q(key), q(value), at, flags, eff))
    p = node("(property {} {} {} {})".format(q(key), q(value), at, eff))
    if hide:
        _hide(doc, p)
    return p


# ---------------------------------------------------------------------------
# Nested lists (kiutils parse_sexp's shape), for layout_check
# ---------------------------------------------------------------------------

_KIUTILS_NUM = re.compile(r"[+-]?\d+\.\d+|-?\d+")


def _list_atom(text: str):
    if _KIUTILS_NUM.fullmatch(text):
        v = float(text)
        return int(v) if v.is_integer() else v
    return text


def to_lists(n: SExp):
    """The tree as nested Python lists, the shape kiutils' ``parse_sexp`` gave: a list is
    ``[name, *children]``; numbers are int/float (integral floats as int); strings are str (quoted
    ones with kiutils' unescaping: only ``\\\"``). kiutils treated a number followed by a newline or
    tab as a string; KiCad writes numbers inside one-line lists, so that case does not arise."""
    if n.is_atom:
        v = n.value
        if isinstance(v, str):
            if n._originally_quoted or (not n._originally_bare and SExp._must_quote(v)):
                return escape_string(v).replace('\\"', '"')
            return _list_atom(v)
        return _list_atom(n._original_str if n._original_str is not None else num(v))
    out = [_list_atom(n.name)] if n.name else []
    out.extend(to_lists(c) for c in n.children)
    return out

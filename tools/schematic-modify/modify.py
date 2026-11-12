#!/usr/bin/env python3
"""
modify.py - Helpers for in-place KiCad schematic edits.

This toolkit focuses on appending/removing items on existing sheets.
It intentionally delegates ai_* annotation writes to:
  tools/schematic-context/annotate.py

Files are loaded and saved through tools/kicad-io/kicad_io.py (kicad-tools' raw s-expression layer;
kicad10-tooling PLAN "Which layer"). A SheetDoc holds the loaded kicad_io Doc; ``sheet_doc.schematic``
is its raw tree (a ``kicad_tools.sexp.SExp`` rooted at ``kicad_sch``), and every helper here reads
and edits that tree. Items returned by the find helpers (find_component, get_lib_symbol_for,
find_sheet_ref, extract_lib_symbol) are raw SExp nodes. Run with tools/.venv/bin/python.

Numbers are written with kicad_io.num (exact text). The port does no rounding beyond the round(.., 2)
calls modify.py always made, so every coordinate is the same float kiutils wrote (kiutils wrote
str(float); num drops a trailing ".0").

Differences from kicad10-preport: add_sheet_reference writes the root schematic's stem as the instance
project and the keys Sheetname/Sheetfile (PLAN "Accepted differences from preport", E2). Preport parity
kept on purpose (PLAN "Raw-layer traps"): a placed symbol gets one (pin ...) entry per pin number (a repeated number keeps its first
position and its last uuid, as kiutils' pin dict did).
"""

from __future__ import annotations

import copy
import math
import os
import shutil
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "kicad-io"))
import kicad_io as kio  # noqa: E402
from kicad_io import at_xy, atom, atom_text, child, kids, node, num, q  # noqa: E402

# KiCad install: one place. KICAD_CLI (env) picks the kicad-cli binary, falling back to 9.0.4.
# The stock symbol libraries are read from the same install (<app>/Contents/SharedSupport/symbols).
KICAD_CLI_DEFAULT = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
KICAD_CLI = os.environ.get("KICAD_CLI") or KICAD_CLI_DEFAULT
STOCK_SYMBOLS = Path(shutil.which(KICAD_CLI) or KICAD_CLI).resolve().parents[1] / "SharedSupport" / "symbols"

ANNOTATE_SCRIPT = Path(__file__).resolve().parents[1] / "schematic-context" / "annotate.py"

FONT_SIZE = 1.27
# Pin -> label stub. 5.08 mm (Phase 11b; was 2.54) leaves room for a label beside the part's own
# fields. Per call: add_component(stub_len=...), set_pin_net(stub_len=...).
WIRE_STUB_LEN = 5.08


def new_uuid() -> str:
    return str(uuid.uuid4())


def _effects(justify: Optional[str] = None) -> str:
    return kio.effects_text(justify=justify, size=FONT_SIZE)


@dataclass
class SheetDoc:
    path: Path
    doc: kio.Doc
    instance_path: str

    @property
    def schematic(self):
        """The sheet's raw tree (kicad_sch root SExp)."""
        return self.doc.tree


@dataclass
class ProjectDocs:
    root_path: Path
    root_uuid: str
    project_name: str
    by_key: Dict[str, SheetDoc] = field(default_factory=dict)

    def sheet(self, key: str) -> SheetDoc:
        if key in self.by_key:
            return self.by_key[key]
        raise KeyError("Unknown sheet key: {}".format(key))

    def save_all(self) -> None:
        """Save every sheet (once per file) through kicad_io: lock guard and version check first,
        then a splice save of each."""
        kio.assert_not_open(self.root_path)
        kio.save_project(d.doc for d in self.by_key.values())


# ---------------------------------------------------------------------------
# Raw-tree accessors
# ---------------------------------------------------------------------------

def _uuid_of(n) -> str:
    u = child(n, "uuid")
    return str(atom(u)) if u is not None else ""


def _lib_id(sym) -> str:
    return str(atom(child(sym, "lib_id")))


def _symbols(sch) -> list:
    return kids(sch, "symbol")


def _props(n) -> list:
    return kids(n, "property")


def _prop(n, key: str):
    for p in _props(n):
        if atom(p, 0) == key:
            return p
    return None


def _xy(n) -> Tuple[float, float]:
    x, y, _ = at_xy(n)
    return x, y


def _wire_pts(w) -> List[Tuple[float, float]]:
    pts = child(w, "pts")
    return [(float(atom(xy, 0)), float(atom(xy, 1))) for xy in kids(pts, "xy")] if pts is not None else []


def _wires(sch) -> list:
    return kids(sch, "wire")


def _labels(sch) -> list:
    return kids(sch, "label")


# KiCad 7+ writes Sheetname/Sheetfile; KiCad 6 (and kiutils) Sheet name/Sheet file. Both are read.
SHEET_NAME_KEYS = ("Sheetname", "Sheet name")
SHEET_FILE_KEYS = ("Sheetfile", "Sheet file")


def _sheet_prop(sheet, keys):
    for p in _props(sheet):
        if atom(p, 0) in keys:
            return p
    return None


def sheet_file_name(sheet) -> str:
    """The file name a sheet reference points to ('' if it has none)."""
    p = _sheet_prop(sheet, SHEET_FILE_KEYS)
    return str(atom(p, 1)) if p is not None else ""


def _symbol_ref(symbol) -> str:
    for prop in _props(symbol):
        if atom(prop, 0) == "Reference":
            return str(atom(prop, 1))
    return ""


def _symbol_has_ref(sch, ref: str) -> bool:
    for sym in _symbols(sch):
        if _symbol_ref(sym) == ref:
            return True
    return False


def _all_ref_set(sch) -> set:
    refs = set()
    for sym in _symbols(sch):
        value = _symbol_ref(sym)
        if value:
            refs.add(value)
    return refs


def load_project(root_schematic: Path) -> ProjectDocs:
    root_path = root_schematic.resolve()
    if not root_path.exists():
        raise FileNotFoundError("Root schematic not found: {}".format(root_path))

    root_doc = kio.load_schematic(root_path)
    root = root_doc.tree
    root_uuid = _uuid_of(root)
    project_name = root_path.stem
    sheets = kids(root, "sheet")
    if sheets:
        inst = child(sheets[0], "instances")
        proj = kids(inst, "project") if inst is not None else []
        if proj and atom(proj[0], 0):
            project_name = str(atom(proj[0], 0))

    docs = ProjectDocs(
        root_path=root_path,
        root_uuid=root_uuid,
        project_name=project_name,
    )

    docs.by_key["root"] = SheetDoc(
        path=root_path,
        doc=root_doc,
        instance_path="/{}".format(root_uuid),
    )

    for sheet in sheets:
        fname = sheet_file_name(sheet)
        child_path = (root_path.parent / fname).resolve()
        if not child_path.exists():
            continue
        docs.by_key[fname] = SheetDoc(
            path=child_path,
            doc=kio.load_schematic(child_path),
            instance_path="/{}/{}".format(root_uuid, _uuid_of(sheet)),
        )

    return docs


# ---------------------------------------------------------------------------
# Library symbols
# ---------------------------------------------------------------------------

def extract_lib_symbol(lib_id: str, source_path: Path):
    """A deep copy of a library symbol's raw node, from a sheet's lib_symbols (.kicad_sch) or from a
    symbol library (.kicad_sym, renamed to lib_id; its units keep their own names, as KiCad embeds
    them)."""
    source = source_path.resolve()
    if source.suffix == ".kicad_sch":
        ls = child(kio.load_schematic(source).tree, "lib_symbols")
        for symbol in (kids(ls, "symbol") if ls is not None else []):
            if atom(symbol, 0) == lib_id:
                return copy.deepcopy(symbol)
        raise ValueError("lib_id {} not found in {}".format(lib_id, source.name))

    if source.suffix == ".kicad_sym":
        sym_name = lib_id.split(":")[1] if ":" in lib_id else lib_id
        for symbol in kids(kio.load_symbol_lib(source).tree, "symbol"):
            if atom(symbol, 0) == sym_name:
                result = copy.deepcopy(symbol)
                kio.set_str(result, 0, lib_id)
                return result
        raise ValueError("symbol {} not found in {}".format(sym_name, source.name))

    raise ValueError("Unsupported symbol source: {}".format(source))


def _lib_symbols_node(sch):
    ls = child(sch, "lib_symbols")
    if ls is None:
        ls = node("(lib_symbols)")
        kio.insert_item(sch, ls)
    return ls


def ensure_lib_symbol(sheet_doc: SheetDoc, lib_symbol) -> None:
    # A symbol from a newer KiCad's library can't go into this sheet (kicad_io refuses at save too).
    kio.check_embed(sheet_doc.doc, lib_symbol)
    ls = _lib_symbols_node(sheet_doc.schematic)
    for existing in kids(ls, "symbol"):
        if atom(existing, 0) == atom(lib_symbol, 0):
            return
    ls.children.append(copy.deepcopy(lib_symbol))


def make_property(sheet_doc: SheetDoc, key: str, value: str, x: float, y: float, angle: float = 0,
                  hide: bool = False, effects: Optional[str] = None):
    """A property node in the sheet's own format (kicad_io.make_property; 1.27 mm font)."""
    return kio.make_property(sheet_doc.doc, key, value, x, y, angle, hide=hide,
                             effects=effects if effects is not None else _effects())


def _pin_records(lib_symbol) -> List[Tuple[str, float, float, float]]:
    """(number, x, y, angle) of every pin in the symbol's units, in file order."""
    records = []
    for unit in kids(lib_symbol, "symbol"):
        for pin in kids(unit, "pin"):
            x, y, a = at_xy(pin)
            records.append((str(atom_text(child(pin, "number"), 0)), float(x), float(y), float(a or 0)))
    return records


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def _compute_pin_position(
    sym_x: float,
    sym_y: float,
    sym_angle: float,
    pin_lib_x: float,
    pin_lib_y: float,
) -> Tuple[float, float]:
    angle_rad = math.radians(sym_angle)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    # Library Y is up, sheet Y is down; KiCad rotates counter-clockwise on screen.
    # (Before 2026-11-03 the X term used +pin_lib_y*sin_a, which put pins of 90/270-degree
    # symbols at the wrong end; 0/180-degree symbols were unaffected.)
    sch_x = sym_x + pin_lib_x * cos_a - pin_lib_y * sin_a
    sch_y = sym_y - pin_lib_x * sin_a - pin_lib_y * cos_a
    return round(sch_x, 2), round(sch_y, 2)


def _compute_stub_endpoint(
    pin_sch_x: float,
    pin_sch_y: float,
    pin_lib_angle: float,
    sym_angle: float,
    stub_len: Optional[float] = None,
) -> Tuple[float, float]:
    length = WIRE_STUB_LEN if stub_len is None else float(stub_len)
    away_angle = (pin_lib_angle + sym_angle + 180) % 360
    angle_rad = math.radians(away_angle)
    dx = round(length * math.cos(angle_rad), 2)
    dy = round(-length * math.sin(angle_rad), 2)
    return round(pin_sch_x + dx, 2), round(pin_sch_y + dy, 2)


def _label_angle(pin_sch: Tuple[float, float], stub_end: Tuple[float, float],
                 sym_xy: Optional[Tuple[float, float]] = None) -> float:
    """Label angle at a stub end: always horizontal (Phase 11b; vertical labels in rows of test
    points were most of the power sheet's overlaps). A horizontal stub reads outward along the
    stub. On a vertical stub the text runs away from the part: right of the wire unless the pin
    is left of the symbol's origin (sym_xy)."""
    dx = stub_end[0] - pin_sch[0]
    dy = stub_end[1] - pin_sch[1]
    if abs(dx) > abs(dy):
        return 0 if dx > 0 else 180
    if sym_xy is not None and pin_sch[0] < sym_xy[0] - 0.01:
        return 180
    return 0


# ---------------------------------------------------------------------------
# Item builders (raw nodes, KiCad 8/9/10 form: no property-bearing items here)
# ---------------------------------------------------------------------------

def _make_wire(start: Tuple[float, float], end: Tuple[float, float]):
    return node("(wire (pts (xy {} {}) (xy {} {})) (stroke (width 0) (type default)) (uuid {}))".format(
        num(start[0]), num(start[1]), num(end[0]), num(end[1]), q(new_uuid())))


def _make_local_label(text: str, x: float, y: float, angle: float = 0):
    """A local label with KiCad's own justification (0/90: left bottom, 180/270: right bottom).
    Without a justify KiCad draws the text centred on the anchor, across the wire end (checked
    on kicad-cli 9.0.4 SVG plots, Phase 11b), so every label written here carries one."""
    horiz = "right" if int(round(angle)) % 360 in (180, 270) else "left"
    return node("(label {} (at {} {} {}) {} (uuid {}))".format(
        q(text), num(x), num(y), num(angle), _effects(horiz + " bottom"), q(new_uuid())))


def _lib_field(sheet_doc: SheetDoc, key: str, value: str, lib_symbol, x: float, y: float, angle: float):
    """A visible Reference/Value at the library symbol's own offset for that field, turned with
    the symbol. The field keeps the library's angle and justification: KiCad stores a symbol
    field's angle in the symbol's frame and turns it with the symbol when drawing. Falls back to
    the symbol origin if the library symbol has no such field."""
    lib_prop = _prop(lib_symbol, key)
    if lib_prop is None or child(lib_prop, "at") is None:
        return make_property(sheet_doc, key, value, x, y, 0)
    lx, ly, la = at_xy(lib_prop)
    fx, fy = _compute_pin_position(x, y, angle, float(lx), float(ly))
    parts = []
    lib_eff = child(lib_prop, "effects")
    font = child(lib_eff, "font") if lib_eff is not None else None
    size = child(font, "size") if font is not None else None
    if size is not None and atom(size, 0):
        parts.append(font.to_string(compact=True))
    else:
        parts.append("(font (size {0} {0}))".format(num(FONT_SIZE)))
    if lib_eff is not None and child(lib_eff, "justify") is not None:
        parts.append(child(lib_eff, "justify").to_string(compact=True))
    return make_property(sheet_doc, key, value, fx, fy, float(la or 0),
                         effects="(effects {})".format(" ".join(parts)))


def _append_prop(sym, prop) -> None:
    """After the symbol's last property (properties come before pins and instances)."""
    idx = max((i for i, c in enumerate(sym.children) if c.name == "property"), default=None)
    if idx is None:
        idx = max(i for i, c in enumerate(sym.children) if c.name in ("uuid", "at", "lib_id"))
    sym.children.insert(idx + 1, prop)


def add_component(
    sheet_doc: SheetDoc,
    *,
    lib_symbol,
    lib_id: str,
    ref: str,
    value: str,
    footprint: str,
    lcsc_part: str,
    position: Tuple[float, float],
    angle: float = 0,
    pin_nets: Optional[Dict[str, str]] = None,
    project_name: str = "motion-play-main",
    stub_len: Optional[float] = None,
) -> None:
    """Place a symbol and give each pin in pin_nets a wire stub (stub_len, default
    WIRE_STUB_LEN) and a horizontal local label (see _label_angle).

    Reference and Value go where the library symbol puts them (its own field offsets, angle and
    justification, turned with the symbol), as KiCad does on placement, and the symbol is marked
    (fields_autoplaced yes) so KiCad re-autoplaces them when the part moves. Footprint, Datasheet
    and LCSC Part are hidden at the symbol's origin."""
    sch = sheet_doc.schematic
    if _symbol_has_ref(sch, ref):
        raise ValueError("Reference already exists on sheet {}: {}".format(sheet_doc.path.name, ref))

    ensure_lib_symbol(sheet_doc, lib_symbol)
    pin_nets = pin_nets or {}

    x, y = float(position[0]), float(position[1])
    sym_uuid = new_uuid()
    props = [
        _lib_field(sheet_doc, "Reference", ref, lib_symbol, x, y, angle),
        _lib_field(sheet_doc, "Value", value, lib_symbol, x, y, angle),
        make_property(sheet_doc, "Footprint", footprint, x, y, 0, hide=True),
        make_property(sheet_doc, "Datasheet", "~", x, y, 0, hide=True),
    ]
    if lcsc_part:
        props.append(make_property(sheet_doc, "LCSC Part", lcsc_part, x, y, 0, hide=True))

    # One (pin ...) per pin number, as kiutils' pin dict kept them: a repeated number keeps its
    # first position and its last uuid (every record still mints a uuid).
    pin_uuid: Dict[str, str] = {}
    for pin_num, _, _, _ in _pin_records(lib_symbol):
        pin_uuid[pin_num] = new_uuid()

    symbol = node(
        "(symbol (lib_id {}) (at {} {} {}) (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes) "
        "(dnp no) (fields_autoplaced yes) (uuid {}) {} (instances (project {} (path {} (reference {}) "
        "(unit 1)))))".format(
            q(lib_id), num(x), num(y), num(angle), q(sym_uuid),
            " ".join("(pin {} (uuid {}))".format(q(n), q(u)) for n, u in pin_uuid.items()),
            q(project_name), q(sheet_doc.instance_path), q(ref)))
    idx = next(i for i, c in enumerate(symbol.children) if c.name == "uuid")
    symbol.children[idx + 1:idx + 1] = props
    kio.insert_item(sch, symbol)

    for pin_num, pin_x, pin_y, pin_angle in _pin_records(lib_symbol):
        if pin_num not in pin_nets:
            continue
        pin_sch = _compute_pin_position(x, y, angle, pin_x, pin_y)
        stub_end = _compute_stub_endpoint(pin_sch[0], pin_sch[1], pin_angle, angle, stub_len)
        kio.insert_item(sch, _make_wire(pin_sch, stub_end))
        kio.insert_item(sch, _make_local_label(pin_nets[pin_num], stub_end[0], stub_end[1],
                                               _label_angle(pin_sch, stub_end, (x, y))))


def remove_component(sheet_doc: SheetDoc, ref: str) -> bool:
    gone = [s for s in _symbols(sheet_doc.schematic) if _symbol_ref(s) == ref]
    kio.remove_items(sheet_doc.schematic, gone)
    return bool(gone)


def add_hierarchical_label(
    sheet_doc: SheetDoc,
    *,
    name: str,
    shape: str,
    net: str,
    position: Tuple[float, float],
    angle: float = 180,
) -> None:
    sch = sheet_doc.schematic
    x, y = float(position[0]), float(position[1])
    kio.insert_item(sch, node("(hierarchical_label {} (shape {}) (at {} {} {}) {} (uuid {}))".format(
        q(name), shape, num(x), num(y), num(angle), _effects(), q(new_uuid()))))

    if angle == 180:
        stub_end = (round(x + WIRE_STUB_LEN, 2), y)
        net_angle = 0
    elif angle == 0:
        stub_end = (round(x - WIRE_STUB_LEN, 2), y)
        net_angle = 180
    else:
        stub_end = (round(x + WIRE_STUB_LEN, 2), y)
        net_angle = 0

    kio.insert_item(sch, _make_wire((x, y), stub_end))
    kio.insert_item(sch, _make_local_label(net, stub_end[0], stub_end[1], net_angle))


def _sheet_pin(name: str, direction: str, x: float, y: float):
    return node("(pin {} {} (at {} {} 0) (uuid {}) {})".format(
        q(name), direction, num(x), num(y), q(new_uuid()), _effects()))


def add_sheet_reference(
    root_doc: SheetDoc,
    *,
    sheet_name: str,
    file_name: str,
    position: Tuple[float, float],
    size: Tuple[float, float],
    pins: List[Dict[str, str]],
    page: Optional[int] = None,
) -> str:
    sch = root_doc.schematic
    existing_files = [sheet_file_name(s) for s in kids(sch, "sheet")]
    if file_name in existing_files:
        raise ValueError("Sheet already exists in root schematic: {}".format(file_name))

    sheet_uuid = new_uuid()
    x, y = float(position[0]), float(position[1])
    width, height = float(size[0]), float(size[1])

    if page is None:
        pages = [1]
        for sheet in kids(sch, "sheet"):
            for inst in kids(sheet, "instances"):
                for proj in kids(inst, "project"):
                    for path in kids(proj, "path"):
                        pg = child(path, "page")
                        try:
                            pages.append(int(atom(pg, 0)))
                        except (TypeError, ValueError):
                            pass
        page = max(pages) + 1

    # The instance's project is the root schematic's stem (the .kicad_pro stem); the keys are the
    # KiCad 7+ Sheetname/Sheetfile. (kicad10-preport hard-coded "motion-play-main" and wrote the
    # KiCad 6 keys: kicad10-tooling PLAN E2.)
    sheet = node("(sheet (at {} {}) (size {} {}) (stroke (width 0)) (fill (color 0 0 0 0)) (uuid {}) "
                 "(instances (project {} (path {} (page {})))))".format(
                     num(x), num(y), num(width), num(height), q(sheet_uuid),
                     q(root_doc.path.stem), q("/" + _uuid_of(sch)), q(str(page))))
    props = [make_property(root_doc, "Sheetname", sheet_name, x, round(y - 2.54, 2), 0),
             make_property(root_doc, "Sheetfile", file_name, x, round(y + height + 2.54, 2), 0)]

    pin_step = 5.08
    left_x = x
    right_x = x + width
    left_y = y + pin_step
    right_y = y + pin_step

    pin_nodes = []
    for pin in pins:
        direction = pin.get("direction", "bidirectional")
        pname = pin["name"]
        if direction in ("input", "bidirectional"):
            pin_x = left_x
            pin_y = left_y
            left_y += pin_step
        else:
            pin_x = right_x
            pin_y = right_y
            right_y += pin_step
        pin_nodes.append(_sheet_pin(pname, direction, pin_x, pin_y))

    idx = next(i for i, c in enumerate(sheet.children) if c.name == "uuid")
    sheet.children[idx + 1:idx + 1] = props + pin_nodes
    kio.insert_item(sch, sheet)
    return sheet_uuid


def annotate_components(
    root_schematic: Path,
    references: List[str],
    annotations: Dict[str, str],
    annotate_script: Optional[Path] = None,
) -> None:
    if not references or not annotations:
        return

    root = root_schematic.resolve()
    if annotate_script is None:
        annotate_script = ANNOTATE_SCRIPT
    annotate_path = annotate_script.resolve()
    if not annotate_path.exists():
        raise FileNotFoundError("annotate.py not found: {}".format(annotate_path))

    cmd = [sys.executable, str(annotate_path), str(root)]
    cmd.extend(references)
    cmd.append("--")
    for key, value in sorted(annotations.items()):
        cmd.append("{}={}".format(key, value))

    result = subprocess.run(cmd, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(
            "annotate.py failed:\n{}\n{}".format(result.stdout.strip(), result.stderr.strip())
        )


# ---------------------------------------------------------------------------
# Sheet reference helpers
# ---------------------------------------------------------------------------

def find_sheet_ref(root_doc: SheetDoc, file_name: str):
    for sheet in kids(root_doc.schematic, "sheet"):
        if sheet_file_name(sheet) == file_name:
            return sheet
    raise ValueError("Sheet reference not found: {}".format(file_name))


def add_pin_to_sheet_ref(
    root_doc: SheetDoc,
    file_name: str,
    pin_name: str,
    direction: str,
) -> None:
    sheet = find_sheet_ref(root_doc, file_name)
    pins = kids(sheet, "pin")

    for pin in pins:
        if atom(pin, 0) == pin_name:
            raise ValueError("Pin '{}' already exists on {}".format(pin_name, file_name))

    pin_step = 5.08
    sx, sy = _xy(sheet)
    size = child(sheet, "size")
    width, height = float(atom(size, 0)), float(atom(size, 1))
    left_x = sx
    right_x = round(sx + width, 2)

    is_left = direction in ("input", "bidirectional")
    target_x = left_x if is_left else right_x

    max_y = sy
    for existing_pin in pins:
        px, py = _xy(existing_pin)
        if abs(px - target_x) < 1.0:
            if py > max_y:
                max_y = py

    if max_y <= sy:
        new_y = round(sy + pin_step, 2)
    else:
        new_y = round(max_y + pin_step, 2)

    sheet_bottom = round(sy + height, 2)
    if new_y + 2.0 > sheet_bottom:
        height = round(new_y - sy + pin_step, 2)
        kio.set_num(size, 1, height)
        fp = _sheet_prop(sheet, SHEET_FILE_KEYS)
        kio.set_num(child(fp, "at"), 1, round(sy + height + 2.54, 2))

    idx = max(i for i, c in enumerate(sheet.children) if c.name in ("pin", "property"))
    sheet.children.insert(idx + 1, _sheet_pin(pin_name, direction, target_x, new_y))


def change_sheet_pin_direction(
    root_doc: SheetDoc,
    file_name: str,
    pin_name: str,
    new_direction: str,
) -> bool:
    sheet = find_sheet_ref(root_doc, file_name)
    for pin in kids(sheet, "pin"):
        if atom(pin, 0) == pin_name:
            kio.set_bare(pin, 1, new_direction)
            return True
    return False


# ---------------------------------------------------------------------------
# Hierarchical label helpers
# ---------------------------------------------------------------------------

def change_hlabel_shape(
    sheet_doc: SheetDoc,
    label_name: str,
    new_shape: str,
) -> bool:
    for hlabel in kids(sheet_doc.schematic, "hierarchical_label"):
        if atom(hlabel, 0) == label_name:
            kio.set_bare(child(hlabel, "shape"), 0, new_shape)
            return True
    return False


# ---------------------------------------------------------------------------
# Label / wire / no-connect surgery
# ---------------------------------------------------------------------------

def find_component(sheet_doc: SheetDoc, ref: str):
    for sym in _symbols(sheet_doc.schematic):
        if _symbol_ref(sym) == ref:
            return sym
    return None


def get_lib_symbol_for(sheet_doc: SheetDoc, lib_id: str):
    ls = child(sheet_doc.schematic, "lib_symbols")
    for s in (kids(ls, "symbol") if ls is not None else []):
        if atom(s, 0) == lib_id:
            return s
    return None


def remove_local_label_near(
    sheet_doc: SheetDoc,
    text: str,
    position: Tuple[float, float],
    tolerance: float = 0.5,
) -> bool:
    x, y = position
    gone = []
    for label in _labels(sheet_doc.schematic):
        lx, ly = _xy(label)
        if atom(label, 0) == text and abs(lx - x) < tolerance and abs(ly - y) < tolerance:
            gone.append(label)
    kio.remove_items(sheet_doc.schematic, gone)
    return bool(gone)


def remove_wire_between(
    sheet_doc: SheetDoc,
    pos_a: Tuple[float, float],
    pos_b: Tuple[float, float],
    tolerance: float = 0.5,
) -> bool:
    def near(p, r):
        return abs(p[0] - r[0]) < tolerance and abs(p[1] - r[1]) < tolerance

    gone = []
    for w in _wires(sheet_doc.schematic):
        pts = _wire_pts(w)
        if len(pts) == 2:
            p0, p1 = pts
            if (near(p0, pos_a) and near(p1, pos_b)) or (near(p0, pos_b) and near(p1, pos_a)):
                gone.append(w)
    kio.remove_items(sheet_doc.schematic, gone)
    return bool(gone)


def _remove_at(sheet_doc: SheetDoc, kind: str, position: Tuple[float, float], tolerance: float) -> bool:
    x, y = position
    gone = [n for n in kids(sheet_doc.schematic, kind)
            if abs(_xy(n)[0] - x) < tolerance and abs(_xy(n)[1] - y) < tolerance]
    kio.remove_items(sheet_doc.schematic, gone)
    return bool(gone)


def remove_junction_at(
    sheet_doc: SheetDoc,
    position: Tuple[float, float],
    tolerance: float = 0.05,
) -> bool:
    return _remove_at(sheet_doc, "junction", position, tolerance)


def add_local_label(sheet_doc: SheetDoc, text: str, position: Tuple[float, float], angle: float = 0) -> None:
    """Place a local label at a point. The caller makes sure the point is on a wire end,
    a wire or a pin of the net it should join (a label touching nothing is dangling)."""
    kio.insert_item(sheet_doc.schematic,
                    _make_local_label(text, float(position[0]), float(position[1]), angle))


def add_wire(sheet_doc: SheetDoc, start: Tuple[float, float], end: Tuple[float, float]) -> None:
    kio.insert_item(sheet_doc.schematic, _make_wire(start, end))


def rename_hlabel(sheet_doc: SheetDoc, old: str, new: str) -> int:
    """Rename every hierarchical label `old` on a sheet; returns how many were renamed.
    The parent's sheet pin must be renamed to match (rename_sheet_pin)."""
    n = 0
    for hl in kids(sheet_doc.schematic, "hierarchical_label"):
        if atom(hl, 0) == old:
            kio.set_str(hl, 0, new)
            n += 1
    return n


def rename_sheet_pin(root_doc: SheetDoc, file_name: str, old: str, new: str) -> bool:
    sheet = find_sheet_ref(root_doc, file_name)
    for pin in kids(sheet, "pin"):
        if atom(pin, 0) == old:
            kio.set_str(pin, 0, new)
            return True
    return False


def add_no_connect(sheet_doc: SheetDoc, position: Tuple[float, float]) -> None:
    kio.insert_item(sheet_doc.schematic, node("(no_connect (at {} {}) (uuid {}))".format(
        num(float(position[0])), num(float(position[1])), q(new_uuid()))))


def remove_no_connect_at(
    sheet_doc: SheetDoc,
    position: Tuple[float, float],
    tolerance: float = 0.05,
) -> bool:
    return _remove_at(sheet_doc, "no_connect", position, tolerance)


# ---------------------------------------------------------------------------
# Pin-level net surgery
# ---------------------------------------------------------------------------

def pin_position(sheet_doc: SheetDoc, ref: str, pin_number: str) -> Tuple[Tuple[float, float], float, float]:
    """Return ((x, y), pin_lib_angle, symbol_angle) of a placed symbol's pin.

    Mirrored symbols are not supported (raises)."""
    sym = find_component(sheet_doc, ref)
    if sym is None:
        raise ValueError("{} not found on {}".format(ref, sheet_doc.path.name))
    if child(sym, "mirror") is not None:
        raise ValueError("{} is mirrored; pin_position does not handle mirroring".format(ref))
    lib = get_lib_symbol_for(sheet_doc, _lib_id(sym))
    if lib is None:
        raise ValueError("lib symbol {} not cached on {}".format(_lib_id(sym), sheet_doc.path.name))
    sx, sy, angle = at_xy(sym)
    angle = float(angle or 0)
    for pnum, px, py, pa in _pin_records(lib):
        if pnum == str(pin_number):
            return _compute_pin_position(sx, sy, angle, px, py), pa, angle
    raise ValueError("{} has no pin {}".format(ref, pin_number))


def _same_point(a: Tuple[float, float], b: Tuple[float, float], tol: float = 0.05) -> bool:
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def set_pin_net(sheet_doc: SheetDoc, ref: str, pin_number: str, net: str,
                stub_len: Optional[float] = None) -> str:
    """Put a symbol pin on a named local-label net, for pins wired label-style.

    Handles the three shapes a label-wired sheet uses:
      - pin -> one wire stub -> local label(s) at the stub end: the label is renamed;
      - pin -> one wire stub -> no-connect at the stub end: the flag is replaced by a label;
      - no-connect (or nothing) on the pin itself: the flag is removed, a stub + label added.
    Anything else (pin wired into a network, labels on the pin) raises, because a
    rename there would move other members too. Returns a short description of the change.
    """
    pin_xy, pin_angle, sym_angle = pin_position(sheet_doc, ref, pin_number)
    sch = sheet_doc.schematic
    stubs = []
    for w in _wires(sch):
        pts = _wire_pts(w)
        if len(pts) == 2:
            if _same_point(pts[0], pin_xy):
                stubs.append(pts[1])
            elif _same_point(pts[1], pin_xy):
                stubs.append(pts[0])
    if len(stubs) > 1:
        raise ValueError("{}.{}: {} wires on the pin; not a label stub".format(ref, pin_number, len(stubs)))
    if stubs:
        end = stubs[0]
        others = [w for w in _wires(sch)
                  if len(_wire_pts(w)) == 2 and any(_same_point(p, end) for p in _wire_pts(w))]
        if len(others) != 1:
            raise ValueError("{}.{}: stub end {} joins other wires".format(ref, pin_number, end))
        labels = [l for l in _labels(sch) if _same_point(_xy(l), end)]
        if labels:
            old = sorted({str(atom(l, 0)) for l in labels})
            for l in labels:
                kio.set_str(l, 0, net)
            return "{}.{}: label {} -> {}".format(ref, pin_number, "/".join(old), net)
        if remove_no_connect_at(sheet_doc, end):
            sym = find_component(sheet_doc, ref)
            kio.insert_item(sch, _make_local_label(net, end[0], end[1], _label_angle(pin_xy, end, _xy(sym))))
            return "{}.{}: no-connect at stub end -> label {}".format(ref, pin_number, net)
        raise ValueError("{}.{}: stub end {} has neither label nor no-connect".format(ref, pin_number, end))
    if any(_same_point(_xy(l), pin_xy) for l in _labels(sch)):
        raise ValueError("{}.{}: label directly on the pin; rename it by hand".format(ref, pin_number))
    had_nc = remove_no_connect_at(sheet_doc, pin_xy)
    end = _compute_stub_endpoint(pin_xy[0], pin_xy[1], pin_angle, sym_angle, stub_len)
    sym = find_component(sheet_doc, ref)
    kio.insert_item(sch, _make_wire(pin_xy, end))
    kio.insert_item(sch, _make_local_label(net, end[0], end[1], _label_angle(pin_xy, end, _xy(sym))))
    return "{}.{}: {}stub + label {}".format(ref, pin_number, "no-connect removed, " if had_nc else "", net)


# ---------------------------------------------------------------------------
# Added 2026-11-03 (v8-debug-board Phase 10)
# ---------------------------------------------------------------------------

def remove_component_with_stubs(sheet_doc: SheetDoc, ref: str) -> List[str]:
    """Remove a label-wired symbol together with each pin's wire stub and the labels or
    no-connects at the stub end (only when nothing else joins that end). Pins wired into a
    network raise, as set_pin_net does. Returns the removed labels' texts."""
    sym = find_component(sheet_doc, ref)
    if sym is None:
        raise ValueError("{} not found on {}".format(ref, sheet_doc.path.name))
    lib_id = _lib_id(sym)
    lib = get_lib_symbol_for(sheet_doc, lib_id)
    sch = sheet_doc.schematic
    removed = []
    for pnum, _, _, _ in _pin_records(lib):
        pin_xy, _, _ = pin_position(sheet_doc, ref, pnum)
        stubs = [w for w in _wires(sch)
                 if len(_wire_pts(w)) == 2 and any(_same_point(p, pin_xy) for p in _wire_pts(w))]
        remove_no_connect_at(sheet_doc, pin_xy)
        if not stubs:
            continue
        if len(stubs) > 1:
            raise ValueError("{}.{}: {} wires on the pin".format(ref, pnum, len(stubs)))
        w = stubs[0]
        end = [p for p in _wire_pts(w) if not _same_point(p, pin_xy)][0]
        others = [x for x in _wires(sch)
                  if x is not w and any(_same_point(p, end) for p in _wire_pts(x))]
        if others:
            raise ValueError("{}.{}: stub end {} joins other wires".format(ref, pnum, end))
        kio.remove_items(sch, [w])
        labels = [l for l in _labels(sch) if _same_point(_xy(l), end)]
        removed.extend(str(atom(l, 0)) for l in labels)
        kio.remove_items(sch, labels)
        remove_no_connect_at(sheet_doc, end)
    remove_component(sheet_doc, ref)
    if not any(_lib_id(s) == lib_id for s in _symbols(sch)):
        ls = child(sch, "lib_symbols")
        if ls is not None:
            kio.remove_items(ls, [s for s in kids(ls, "symbol") if atom(s, 0) == lib_id])
    return removed


def set_property(sheet_doc: SheetDoc, ref: str, key: str, value: str) -> str:
    """Set (or add, hidden) a property on a placed symbol. Returns 'old -> new'."""
    sym = find_component(sheet_doc, ref)
    if sym is None:
        raise ValueError("{} not found on {}".format(ref, sheet_doc.path.name))
    p = _prop(sym, key)
    if p is not None:
        old = str(atom(p, 1))
        kio.set_str(p, 1, value)
        return "{} {}: {} -> {}".format(ref, key, old, value)
    sx, sy = _xy(sym)
    _append_prop(sym, make_property(sheet_doc, key, value, sx, sy, 0, hide=True))
    return "{} {}: (new) {}".format(ref, key, value)


def add_power_symbol(sheet_doc: SheetDoc, lib_symbol, lib_id: str, ref: str, value: str,
                     position: Tuple[float, float], project_name: str) -> None:
    """Place a power symbol (or PWR_FLAG) with its pin exactly on `position` (no stub), so it
    joins whatever label, wire end or pin sits there. For power symbols the Value names the
    global net (KiCad 9: checked on this project, Phase 10)."""
    add_component(sheet_doc, lib_symbol=lib_symbol, lib_id=lib_id, ref=ref, value=value, footprint="",
                  lcsc_part="", position=position, pin_nets={}, project_name=project_name)
    sym = find_component(sheet_doc, ref)
    kio.set_bare(child(sym, "in_bom"), 0, "no")
    kio.set_bare(child(sym, "on_board"), 0, "no")
    kio.hide(sheet_doc.doc, _prop(sym, "Reference"))

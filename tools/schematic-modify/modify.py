#!/usr/bin/env python3
"""
modify.py - Helpers for in-place KiCad schematic edits.

This toolkit focuses on appending/removing items on existing sheets.
It intentionally delegates ai_* annotation writes to:
  tools/schematic-context/annotate.py
"""

from __future__ import annotations

import copy
import subprocess
import sys
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kiutils_k9  # noqa: E402  (KiCad 8/9 '(hide yes)' shim; must precede any load)

from kiutils.items.common import Effects, Font, Justify, Position, Property, Stroke  # noqa: E402
from kiutils.items.schitems import (
    Connection,
    HierarchicalLabel,
    HierarchicalPin,
    HierarchicalSheet,
    HierarchicalSheetProjectInstance,
    HierarchicalSheetProjectPath,
    LocalLabel,
    NoConnect,
    SchematicSymbol,
    SymbolProjectInstance,
    SymbolProjectPath,
)
from kiutils.schematic import Schematic
from kiutils.symbol import SymbolLib

FONT_SIZE = 1.27
# Pin -> label stub. 5.08 mm (Phase 11b; was 2.54) leaves room for a label beside the part's own
# fields. Per call: add_component(stub_len=...), set_pin_net(stub_len=...).
WIRE_STUB_LEN = 5.08


def new_uuid() -> str:
    return str(uuid.uuid4())


@dataclass
class SheetDoc:
    path: Path
    schematic: Schematic
    instance_path: str


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
        kiutils_k9.assert_not_open(self.root_path)
        saved = set()
        for doc in self.by_key.values():
            if str(doc.path) in saved:
                continue
            kiutils_k9.save_schematic(doc.schematic, doc.path)
            saved.add(str(doc.path))


def _symbol_ref(symbol: object) -> str:
    for prop in symbol.properties:
        if prop.key == "Reference":
            return prop.value
    return ""


def _symbol_has_ref(sch: Schematic, ref: str) -> bool:
    for sym in sch.schematicSymbols:
        if _symbol_ref(sym) == ref:
            return True
    return False


def _all_ref_set(sch: Schematic) -> set:
    refs = set()
    for sym in sch.schematicSymbols:
        value = _symbol_ref(sym)
        if value:
            refs.add(value)
    return refs


def load_project(root_schematic: Path) -> ProjectDocs:
    root_path = root_schematic.resolve()
    if not root_path.exists():
        raise FileNotFoundError("Root schematic not found: {}".format(root_path))

    root = Schematic.from_file(str(root_path))
    project_name = root_path.stem
    if root.sheets and root.sheets[0].instances:
        project_name = root.sheets[0].instances[0].name or project_name

    docs = ProjectDocs(
        root_path=root_path,
        root_uuid=root.uuid,
        project_name=project_name,
    )

    docs.by_key["root"] = SheetDoc(
        path=root_path,
        schematic=root,
        instance_path="/{}".format(root.uuid),
    )

    for sheet in root.sheets:
        child_path = (root_path.parent / sheet.fileName.value).resolve()
        if not child_path.exists():
            continue
        child = Schematic.from_file(str(child_path))
        docs.by_key[sheet.fileName.value] = SheetDoc(
            path=child_path,
            schematic=child,
            instance_path="/{}/{}".format(root.uuid, sheet.uuid),
        )

    return docs


def extract_lib_symbol(lib_id: str, source_path: Path) -> object:
    source = source_path.resolve()
    if source.suffix == ".kicad_sch":
        sch = Schematic.from_file(str(source))
        for symbol in sch.libSymbols:
            if symbol.libId == lib_id:
                return copy.deepcopy(symbol)
        raise ValueError("lib_id {} not found in {}".format(lib_id, source.name))

    if source.suffix == ".kicad_sym":
        sym_name = lib_id.split(":")[1] if ":" in lib_id else lib_id
        lib = SymbolLib.from_file(str(source))
        for symbol in lib.symbols:
            if symbol.libId == sym_name:
                result = copy.deepcopy(symbol)
                result.libId = lib_id
                return result
        raise ValueError("symbol {} not found in {}".format(sym_name, source.name))

    raise ValueError("Unsupported symbol source: {}".format(source))


def ensure_lib_symbol(sheet_doc: SheetDoc, lib_symbol: object) -> None:
    for existing in sheet_doc.schematic.libSymbols:
        if existing.libId == lib_symbol.libId:
            return
    sheet_doc.schematic.libSymbols.append(copy.deepcopy(lib_symbol))


def make_property(key: str, value: str, pos: Position, hide: bool, prop_id: int) -> Property:
    return Property(
        key=key,
        value=value,
        id=prop_id,
        position=pos,
        effects=Effects(font=Font(height=FONT_SIZE, width=FONT_SIZE), hide=hide),
    )


def _pin_records(lib_symbol: object) -> List[Tuple[str, float, float, float]]:
    records = []
    for unit in lib_symbol.units:
        for pin in unit.pins:
            records.append(
                (
                    str(pin.number),
                    float(pin.position.X),
                    float(pin.position.Y),
                    float(pin.position.angle or 0),
                )
            )
    return records


def _compute_pin_position(
    sym_x: float,
    sym_y: float,
    sym_angle: float,
    pin_lib_x: float,
    pin_lib_y: float,
) -> Tuple[float, float]:
    import math

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
    import math

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


def _make_wire(start: Tuple[float, float], end: Tuple[float, float]) -> Connection:
    return Connection(
        type="wire",
        points=[Position(X=start[0], Y=start[1]), Position(X=end[0], Y=end[1])],
        stroke=Stroke(width=0, type="default"),
        uuid=new_uuid(),
    )


def _make_local_label(text: str, x: float, y: float, angle: float = 0) -> LocalLabel:
    """A local label with KiCad's own justification (0/90: left bottom, 180/270: right bottom).
    Without a justify KiCad draws the text centred on the anchor, across the wire end (checked
    on kicad-cli 9.0.4 SVG plots, Phase 11b), so every label written here carries one."""
    label = LocalLabel()
    label.text = text
    label.position = Position(X=x, Y=y, angle=angle)
    horiz = "right" if int(round(angle)) % 360 in (180, 270) else "left"
    label.effects = Effects(font=Font(height=FONT_SIZE, width=FONT_SIZE),
                            justify=Justify(horizontally=horiz, vertically="bottom"))
    label.uuid = new_uuid()
    return label


def _lib_field(key: str, value: str, lib_symbol: object, x: float, y: float, angle: float,
               prop_id: int) -> Property:
    """A visible Reference/Value at the library symbol's own offset for that field, turned with
    the symbol. The field keeps the library's angle and justification: KiCad stores a symbol
    field's angle in the symbol's frame and turns it with the symbol when drawing. Falls back to
    the symbol origin if the library symbol has no such field."""
    lib_prop = next((p for p in getattr(lib_symbol, "properties", []) if p.key == key), None)
    if lib_prop is None or lib_prop.position is None:
        return make_property(key, value, Position(X=x, Y=y, angle=0), False, prop_id)
    fx, fy = _compute_pin_position(x, y, angle, float(lib_prop.position.X), float(lib_prop.position.Y))
    prop = make_property(key, value, Position(X=fx, Y=fy, angle=float(lib_prop.position.angle or 0)),
                         False, prop_id)
    lib_eff = lib_prop.effects
    if lib_eff is not None:
        if lib_eff.font is not None and lib_eff.font.height:
            prop.effects.font = copy.deepcopy(lib_eff.font)
        if lib_eff.justify is not None:
            prop.effects.justify = copy.deepcopy(lib_eff.justify)
    return prop


def add_component(
    sheet_doc: SheetDoc,
    *,
    lib_symbol: object,
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
    if _symbol_has_ref(sheet_doc.schematic, ref):
        raise ValueError("Reference already exists on sheet {}: {}".format(sheet_doc.path.name, ref))

    ensure_lib_symbol(sheet_doc, lib_symbol)
    pin_nets = pin_nets or {}

    x, y = float(position[0]), float(position[1])
    symbol = SchematicSymbol()
    symbol.libId = lib_id
    symbol.position = Position(X=x, Y=y, angle=angle)
    symbol.unit = 1
    symbol.inBom = True
    symbol.onBoard = True
    symbol.dnp = False
    symbol.uuid = new_uuid()
    symbol.fieldsAutoplaced = True
    symbol.properties = [
        _lib_field("Reference", ref, lib_symbol, x, y, angle, 0),
        _lib_field("Value", value, lib_symbol, x, y, angle, 1),
        make_property("Footprint", footprint, Position(X=x, Y=y, angle=0), True, 2),
        make_property("Datasheet", "~", Position(X=x, Y=y, angle=0), True, 3),
    ]
    if lcsc_part:
        symbol.properties.append(
            make_property("LCSC Part", lcsc_part, Position(X=x, Y=y, angle=0), True, 4)
        )

    symbol.pins = {}
    for pin_num, _, _, _ in _pin_records(lib_symbol):
        symbol.pins[pin_num] = new_uuid()

    symbol.instances = [
        SymbolProjectInstance(
            name=project_name,
            paths=[
                SymbolProjectPath(
                    sheetInstancePath=sheet_doc.instance_path,
                    reference=ref,
                    unit=1,
                )
            ],
        )
    ]
    sheet_doc.schematic.schematicSymbols.append(symbol)

    for pin_num, pin_x, pin_y, pin_angle in _pin_records(lib_symbol):
        if pin_num not in pin_nets:
            continue
        pin_sch = _compute_pin_position(x, y, angle, pin_x, pin_y)
        stub_end = _compute_stub_endpoint(pin_sch[0], pin_sch[1], pin_angle, angle, stub_len)
        sheet_doc.schematic.graphicalItems.append(_make_wire(pin_sch, stub_end))
        sheet_doc.schematic.labels.append(
            _make_local_label(pin_nets[pin_num], stub_end[0], stub_end[1],
                              _label_angle(pin_sch, stub_end, (x, y)))
        )


def remove_component(sheet_doc: SheetDoc, ref: str) -> bool:
    removed = False
    keep = []
    for symbol in sheet_doc.schematic.schematicSymbols:
        if _symbol_ref(symbol) == ref:
            removed = True
            continue
        keep.append(symbol)
    sheet_doc.schematic.schematicSymbols = keep
    return removed


def add_hierarchical_label(
    sheet_doc: SheetDoc,
    *,
    name: str,
    shape: str,
    net: str,
    position: Tuple[float, float],
    angle: float = 180,
) -> None:
    x, y = float(position[0]), float(position[1])
    hlabel = HierarchicalLabel()
    hlabel.text = name
    hlabel.shape = shape
    hlabel.position = Position(X=x, Y=y, angle=angle)
    hlabel.effects = Effects(font=Font(height=FONT_SIZE, width=FONT_SIZE))
    hlabel.uuid = new_uuid()
    sheet_doc.schematic.hierarchicalLabels.append(hlabel)

    if angle == 180:
        stub_end = (round(x + WIRE_STUB_LEN, 2), y)
        net_angle = 0
    elif angle == 0:
        stub_end = (round(x - WIRE_STUB_LEN, 2), y)
        net_angle = 180
    else:
        stub_end = (round(x + WIRE_STUB_LEN, 2), y)
        net_angle = 0

    sheet_doc.schematic.graphicalItems.append(_make_wire((x, y), stub_end))
    sheet_doc.schematic.labels.append(_make_local_label(net, stub_end[0], stub_end[1], net_angle))


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
    existing_files = [s.fileName.value for s in root_doc.schematic.sheets]
    if file_name in existing_files:
        raise ValueError("Sheet already exists in root schematic: {}".format(file_name))

    sheet_uuid = new_uuid()
    x, y = float(position[0]), float(position[1])
    width, height = float(size[0]), float(size[1])

    if page is None:
        pages = [1]
        for sheet in root_doc.schematic.sheets:
            for inst in sheet.instances:
                for path in inst.paths:
                    try:
                        pages.append(int(path.page))
                    except (TypeError, ValueError):
                        pass
        page = max(pages) + 1

    sheet = HierarchicalSheet(
        position=Position(X=x, Y=y, angle=0),
        width=width,
        height=height,
        uuid=sheet_uuid,
        sheetName=Property(
            key="Sheet name",
            value=sheet_name,
            id=0,
            position=Position(X=x, Y=round(y - 2.54, 2), angle=0),
            effects=Effects(font=Font(height=FONT_SIZE, width=FONT_SIZE)),
        ),
        fileName=Property(
            key="Sheet file",
            value=file_name,
            id=1,
            position=Position(X=x, Y=round(y + height + 2.54, 2), angle=0),
            effects=Effects(font=Font(height=FONT_SIZE, width=FONT_SIZE)),
        ),
        instances=[
            HierarchicalSheetProjectInstance(
                name="motion-play-main",
                paths=[
                    HierarchicalSheetProjectPath(
                        sheetInstancePath="/{}".format(root_doc.schematic.uuid),
                        page=str(page),
                    )
                ],
            )
        ],
    )

    pin_step = 5.08
    left_x = x
    right_x = x + width
    left_y = y + pin_step
    right_y = y + pin_step

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
        sheet.pins.append(
            HierarchicalPin(
                name=pname,
                connectionType=direction,
                position=Position(X=pin_x, Y=pin_y, angle=0),
                effects=Effects(font=Font(height=FONT_SIZE, width=FONT_SIZE)),
                uuid=new_uuid(),
            )
        )

    root_doc.schematic.sheets.append(sheet)
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
        annotate_script = root.parents[3] / "tools/schematic-context/annotate.py"
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

def find_sheet_ref(root_doc: SheetDoc, file_name: str) -> HierarchicalSheet:
    for sheet in root_doc.schematic.sheets:
        if sheet.fileName.value == file_name:
            return sheet
    raise ValueError("Sheet reference not found: {}".format(file_name))


def add_pin_to_sheet_ref(
    root_doc: SheetDoc,
    file_name: str,
    pin_name: str,
    direction: str,
) -> None:
    sheet = find_sheet_ref(root_doc, file_name)

    for pin in sheet.pins:
        if pin.name == pin_name:
            raise ValueError("Pin '{}' already exists on {}".format(pin_name, file_name))

    pin_step = 5.08
    left_x = sheet.position.X
    right_x = round(sheet.position.X + sheet.width, 2)

    is_left = direction in ("input", "bidirectional")
    target_x = left_x if is_left else right_x

    max_y = sheet.position.Y
    for existing_pin in sheet.pins:
        if abs(existing_pin.position.X - target_x) < 1.0:
            if existing_pin.position.Y > max_y:
                max_y = existing_pin.position.Y

    if max_y <= sheet.position.Y:
        new_y = round(sheet.position.Y + pin_step, 2)
    else:
        new_y = round(max_y + pin_step, 2)

    sheet_bottom = round(sheet.position.Y + sheet.height, 2)
    if new_y + 2.0 > sheet_bottom:
        sheet.height = round(new_y - sheet.position.Y + pin_step, 2)
        sheet.fileName.position.Y = round(sheet.position.Y + sheet.height + 2.54, 2)

    sheet.pins.append(
        HierarchicalPin(
            name=pin_name,
            connectionType=direction,
            position=Position(X=target_x, Y=new_y, angle=0),
            effects=Effects(font=Font(height=FONT_SIZE, width=FONT_SIZE)),
            uuid=new_uuid(),
        )
    )


def change_sheet_pin_direction(
    root_doc: SheetDoc,
    file_name: str,
    pin_name: str,
    new_direction: str,
) -> bool:
    sheet = find_sheet_ref(root_doc, file_name)
    for pin in sheet.pins:
        if pin.name == pin_name:
            pin.connectionType = new_direction
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
    for hlabel in sheet_doc.schematic.hierarchicalLabels:
        if hlabel.text == label_name:
            hlabel.shape = new_shape
            return True
    return False


# ---------------------------------------------------------------------------
# Label / wire / no-connect surgery
# ---------------------------------------------------------------------------

def find_component(sheet_doc: SheetDoc, ref: str) -> Optional[SchematicSymbol]:
    for sym in sheet_doc.schematic.schematicSymbols:
        if _symbol_ref(sym) == ref:
            return sym
    return None


def get_lib_symbol_for(sheet_doc: SheetDoc, lib_id: str):
    for ls in sheet_doc.schematic.libSymbols:
        if ls.libId == lib_id:
            return ls
    return None


def remove_local_label_near(
    sheet_doc: SheetDoc,
    text: str,
    position: Tuple[float, float],
    tolerance: float = 0.5,
) -> bool:
    x, y = position
    keep = []
    removed = False
    for label in sheet_doc.schematic.labels:
        if (
            label.text == text
            and abs(label.position.X - x) < tolerance
            and abs(label.position.Y - y) < tolerance
        ):
            removed = True
            continue
        keep.append(label)
    sheet_doc.schematic.labels = keep
    return removed


def remove_wire_between(
    sheet_doc: SheetDoc,
    pos_a: Tuple[float, float],
    pos_b: Tuple[float, float],
    tolerance: float = 0.5,
) -> bool:
    keep = []
    removed = False
    for item in sheet_doc.schematic.graphicalItems:
        if hasattr(item, "type") and item.type == "wire" and len(item.points) == 2:
            p0, p1 = item.points
            fwd = (
                abs(p0.X - pos_a[0]) < tolerance
                and abs(p0.Y - pos_a[1]) < tolerance
                and abs(p1.X - pos_b[0]) < tolerance
                and abs(p1.Y - pos_b[1]) < tolerance
            )
            rev = (
                abs(p0.X - pos_b[0]) < tolerance
                and abs(p0.Y - pos_b[1]) < tolerance
                and abs(p1.X - pos_a[0]) < tolerance
                and abs(p1.Y - pos_a[1]) < tolerance
            )
            if fwd or rev:
                removed = True
                continue
        keep.append(item)
    sheet_doc.schematic.graphicalItems = keep
    return removed


def remove_junction_at(
    sheet_doc: SheetDoc,
    position: Tuple[float, float],
    tolerance: float = 0.05,
) -> bool:
    x, y = position
    keep = []
    removed = False
    for j in sheet_doc.schematic.junctions:
        if abs(j.position.X - x) < tolerance and abs(j.position.Y - y) < tolerance:
            removed = True
            continue
        keep.append(j)
    sheet_doc.schematic.junctions = keep
    return removed


def add_local_label(sheet_doc: SheetDoc, text: str, position: Tuple[float, float], angle: float = 0) -> None:
    """Place a local label at a point. The caller makes sure the point is on a wire end,
    a wire or a pin of the net it should join (a label touching nothing is dangling)."""
    sheet_doc.schematic.labels.append(_make_local_label(text, float(position[0]), float(position[1]), angle))


def add_wire(sheet_doc: SheetDoc, start: Tuple[float, float], end: Tuple[float, float]) -> None:
    sheet_doc.schematic.graphicalItems.append(_make_wire(start, end))


def rename_hlabel(sheet_doc: SheetDoc, old: str, new: str) -> int:
    """Rename every hierarchical label `old` on a sheet; returns how many were renamed.
    The parent's sheet pin must be renamed to match (rename_sheet_pin)."""
    n = 0
    for hl in sheet_doc.schematic.hierarchicalLabels:
        if hl.text == old:
            hl.text = new
            n += 1
    return n


def rename_sheet_pin(root_doc: SheetDoc, file_name: str, old: str, new: str) -> bool:
    sheet = find_sheet_ref(root_doc, file_name)
    for pin in sheet.pins:
        if pin.name == old:
            pin.name = new
            return True
    return False


def add_no_connect(sheet_doc: SheetDoc, position: Tuple[float, float]) -> None:
    nc = NoConnect()
    nc.position = Position(X=float(position[0]), Y=float(position[1]))
    nc.uuid = new_uuid()
    sheet_doc.schematic.noConnects.append(nc)


def remove_no_connect_at(
    sheet_doc: SheetDoc,
    position: Tuple[float, float],
    tolerance: float = 0.05,
) -> bool:
    x, y = position
    keep = []
    removed = False
    for nc in sheet_doc.schematic.noConnects:
        if abs(nc.position.X - x) < tolerance and abs(nc.position.Y - y) < tolerance:
            removed = True
            continue
        keep.append(nc)
    sheet_doc.schematic.noConnects = keep
    return removed


# ---------------------------------------------------------------------------
# Pin-level net surgery
# ---------------------------------------------------------------------------

def pin_position(sheet_doc: SheetDoc, ref: str, pin_number: str) -> Tuple[Tuple[float, float], float, float]:
    """Return ((x, y), pin_lib_angle, symbol_angle) of a placed symbol's pin.

    Mirrored symbols are not supported (raises)."""
    sym = find_component(sheet_doc, ref)
    if sym is None:
        raise ValueError("{} not found on {}".format(ref, sheet_doc.path.name))
    if getattr(sym, "mirror", None):
        raise ValueError("{} is mirrored; pin_position does not handle mirroring".format(ref))
    lib = get_lib_symbol_for(sheet_doc, sym.libId)
    if lib is None:
        raise ValueError("lib symbol {} not cached on {}".format(sym.libId, sheet_doc.path.name))
    angle = float(sym.position.angle or 0)
    for num, px, py, pa in _pin_records(lib):
        if num == str(pin_number):
            return _compute_pin_position(sym.position.X, sym.position.Y, angle, px, py), pa, angle
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
    for item in sch.graphicalItems:
        if getattr(item, "type", None) == "wire" and len(item.points) == 2:
            p0 = (item.points[0].X, item.points[0].Y)
            p1 = (item.points[1].X, item.points[1].Y)
            if _same_point(p0, pin_xy):
                stubs.append(p1)
            elif _same_point(p1, pin_xy):
                stubs.append(p0)
    if len(stubs) > 1:
        raise ValueError("{}.{}: {} wires on the pin; not a label stub".format(ref, pin_number, len(stubs)))
    if stubs:
        end = stubs[0]
        others = [w for w in sch.graphicalItems
                  if getattr(w, "type", None) == "wire" and len(w.points) == 2
                  and any(_same_point((q.X, q.Y), end) for q in w.points)]
        if len(others) != 1:
            raise ValueError("{}.{}: stub end {} joins other wires".format(ref, pin_number, end))
        labels = [l for l in sch.labels if _same_point((l.position.X, l.position.Y), end)]
        if labels:
            old = sorted({l.text for l in labels})
            for l in labels:
                l.text = net
            return "{}.{}: label {} -> {}".format(ref, pin_number, "/".join(old), net)
        if remove_no_connect_at(sheet_doc, end):
            sym = find_component(sheet_doc, ref)
            sch.labels.append(_make_local_label(net, end[0], end[1],
                                                _label_angle(pin_xy, end, (sym.position.X, sym.position.Y))))
            return "{}.{}: no-connect at stub end -> label {}".format(ref, pin_number, net)
        raise ValueError("{}.{}: stub end {} has neither label nor no-connect".format(ref, pin_number, end))
    if any(_same_point((l.position.X, l.position.Y), pin_xy) for l in sch.labels):
        raise ValueError("{}.{}: label directly on the pin; rename it by hand".format(ref, pin_number))
    had_nc = remove_no_connect_at(sheet_doc, pin_xy)
    end = _compute_stub_endpoint(pin_xy[0], pin_xy[1], pin_angle, sym_angle, stub_len)
    sym = find_component(sheet_doc, ref)
    sch.graphicalItems.append(_make_wire(pin_xy, end))
    sch.labels.append(_make_local_label(net, end[0], end[1],
                                        _label_angle(pin_xy, end, (sym.position.X, sym.position.Y))))
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
    lib = get_lib_symbol_for(sheet_doc, sym.libId)
    sch = sheet_doc.schematic
    removed = []
    for num, _, _, _ in _pin_records(lib):
        pin_xy, _, _ = pin_position(sheet_doc, ref, num)
        stubs = [w for w in sch.graphicalItems
                 if getattr(w, "type", None) == "wire" and len(w.points) == 2
                 and any(_same_point((q.X, q.Y), pin_xy) for q in w.points)]
        remove_no_connect_at(sheet_doc, pin_xy)
        if not stubs:
            continue
        if len(stubs) > 1:
            raise ValueError("{}.{}: {} wires on the pin".format(ref, num, len(stubs)))
        w = stubs[0]
        end = [(q.X, q.Y) for q in w.points if not _same_point((q.X, q.Y), pin_xy)][0]
        others = [x for x in sch.graphicalItems
                  if x is not w and getattr(x, "type", None) == "wire"
                  and any(_same_point((q.X, q.Y), end) for q in x.points)]
        if others:
            raise ValueError("{}.{}: stub end {} joins other wires".format(ref, num, end))
        sch.graphicalItems = [x for x in sch.graphicalItems if x is not w]
        for l in [l for l in sch.labels if _same_point((l.position.X, l.position.Y), end)]:
            removed.append(l.text)
            sch.labels.remove(l)
        remove_no_connect_at(sheet_doc, end)
    remove_component(sheet_doc, ref)
    if not any(s.libId == sym.libId for s in sch.schematicSymbols):
        sch.libSymbols = [l for l in sch.libSymbols if l.libId != sym.libId]
    return removed


def set_property(sheet_doc: SheetDoc, ref: str, key: str, value: str) -> str:
    """Set (or add, hidden) a property on a placed symbol. Returns 'old -> new'."""
    sym = find_component(sheet_doc, ref)
    if sym is None:
        raise ValueError("{} not found on {}".format(ref, sheet_doc.path.name))
    for p in sym.properties:
        if p.key == key:
            old, p.value = p.value, value
            return "{} {}: {} -> {}".format(ref, key, old, value)
    sym.properties.append(make_property(key, value, Position(X=sym.position.X, Y=sym.position.Y, angle=0),
                                        True, len(sym.properties)))
    return "{} {}: (new) {}".format(ref, key, value)


def add_power_symbol(sheet_doc: SheetDoc, lib_symbol: object, lib_id: str, ref: str, value: str,
                     position: Tuple[float, float], project_name: str) -> None:
    """Place a power symbol (or PWR_FLAG) with its pin exactly on `position` (no stub), so it
    joins whatever label, wire end or pin sits there. For power symbols the Value names the
    global net (KiCad 9: checked on this project, Phase 10)."""
    add_component(sheet_doc, lib_symbol=lib_symbol, lib_id=lib_id, ref=ref, value=value, footprint="",
                  lcsc_part="", position=position, pin_nets={}, project_name=project_name)
    sym = find_component(sheet_doc, ref)
    sym.inBom = False
    sym.onBoard = False
    for p in sym.properties:
        if p.key == "Reference":
            p.effects.hide = True

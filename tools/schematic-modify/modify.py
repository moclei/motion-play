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

from kiutils.items.common import Effects, Font, Position, Property, Stroke
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
WIRE_STUB_LEN = 2.54


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
        saved = set()
        for doc in self.by_key.values():
            if str(doc.path) in saved:
                continue
            doc.schematic.to_file(str(doc.path))
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

    sch_x = sym_x + pin_lib_x * cos_a + pin_lib_y * sin_a
    sch_y = sym_y - pin_lib_x * sin_a + pin_lib_y * (-cos_a)
    return round(sch_x, 2), round(sch_y, 2)


def _compute_stub_endpoint(
    pin_sch_x: float,
    pin_sch_y: float,
    pin_lib_angle: float,
    sym_angle: float,
) -> Tuple[float, float]:
    import math

    away_angle = (pin_lib_angle + sym_angle + 180) % 360
    angle_rad = math.radians(away_angle)
    dx = round(WIRE_STUB_LEN * math.cos(angle_rad), 2)
    dy = round(-WIRE_STUB_LEN * math.sin(angle_rad), 2)
    return round(pin_sch_x + dx, 2), round(pin_sch_y + dy, 2)


def _label_angle(pin_sch: Tuple[float, float], stub_end: Tuple[float, float]) -> float:
    dx = stub_end[0] - pin_sch[0]
    dy = stub_end[1] - pin_sch[1]
    if abs(dx) > abs(dy):
        return 0 if dx > 0 else 180
    return 90 if dy > 0 else 270


def _make_wire(start: Tuple[float, float], end: Tuple[float, float]) -> Connection:
    return Connection(
        type="wire",
        points=[Position(X=start[0], Y=start[1]), Position(X=end[0], Y=end[1])],
        stroke=Stroke(width=0, type="default"),
        uuid=new_uuid(),
    )


def _make_local_label(text: str, x: float, y: float, angle: float = 0) -> LocalLabel:
    label = LocalLabel()
    label.text = text
    label.position = Position(X=x, Y=y, angle=angle)
    label.effects = Effects(font=Font(height=FONT_SIZE, width=FONT_SIZE))
    label.uuid = new_uuid()
    return label


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
) -> None:
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
    symbol.properties = [
        make_property("Reference", ref, Position(X=round(x + 2.54, 2), Y=round(y - 1.27, 2), angle=angle), False, 0),
        make_property("Value", value, Position(X=x, Y=round(y + 2.54, 2), angle=angle), False, 1),
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
            name="motion-play-main",
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
        stub_end = _compute_stub_endpoint(pin_sch[0], pin_sch[1], pin_angle, angle)
        sheet_doc.schematic.graphicalItems.append(_make_wire(pin_sch, stub_end))
        sheet_doc.schematic.labels.append(
            _make_local_label(pin_nets[pin_num], stub_end[0], stub_end[1], _label_angle(pin_sch, stub_end))
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


def add_no_connect(sheet_doc: SheetDoc, position: Tuple[float, float]) -> None:
    nc = NoConnect()
    nc.position = Position(X=float(position[0]), Y=float(position[1]))
    nc.uuid = new_uuid()
    sheet_doc.schematic.noConnects.append(nc)

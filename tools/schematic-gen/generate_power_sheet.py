#!/usr/bin/env python3
"""
generate_power_sheet.py — Generate power_management.kicad_sch from spec.json.

Reads the structured specification and produces a KiCad 9 schematic with:
- All 51 components placed by block
- Net labels on wire stubs at every connected pin
- No-connect flags on specified pins
- Hierarchical sheet labels for interface signals
- Power symbols for +5V, +3.3V, GND

Usage:
    python generate_power_sheet.py [--output path/to/output.kicad_sch]

Default output: hardware/pcb-main/kicad/power_management.kicad_sch
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import sys
import uuid
from pathlib import Path

from kiutils.schematic import Schematic
from kiutils.symbol import SymbolLib
from kiutils.items.schitems import (
    Connection,
    HierarchicalLabel,
    LocalLabel,
    NoConnect,
    SchematicSymbol,
    SymbolProjectInstance,
    SymbolProjectPath,
)
from kiutils.items.common import Effects, Font, Position, Property, Stroke


KICAD9_VERSION = "20250114"
PROJECT_NAME = "motion-play-main"
WIRE_STUB_LEN = 2.54

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_PATH = Path(__file__).resolve().parent / "spec.json"
DEFAULT_OUTPUT = REPO_ROOT / "hardware/pcb-main/kicad/power_management.kicad_sch"


def new_uuid() -> str:
    return str(uuid.uuid4())


def load_spec() -> dict:
    with open(SPEC_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------

def extract_lib_symbol_from_sch(source_path: Path, lib_id: str):
    sch = Schematic.from_file(str(source_path))
    for sym in sch.libSymbols:
        if sym.libId == lib_id:
            return copy.deepcopy(sym)
    raise ValueError(f"lib_symbol {lib_id!r} not found in {source_path.name}")


def extract_lib_symbol_from_symlib(source_path: Path, lib_id: str):
    """Extract a symbol from a .kicad_sym library file.

    Sets the top-level libId to the full lib_id (e.g. 'INA219AIDCNR:INA219AIDCNR')
    so it matches the lib_id used in placed SchematicSymbol references.
    Sub-symbol entryNames keep the short name (e.g. 'INA219AIDCNR').
    """
    lib = SymbolLib.from_file(str(source_path))
    sym_name = lib_id.split(":")[1] if ":" in lib_id else lib_id
    for sym in lib.symbols:
        if sym.libId == sym_name:
            result = copy.deepcopy(sym)
            result.libId = lib_id
            return result
    raise ValueError(f"symbol {sym_name!r} not found in {source_path.name}")


def extract_all_lib_symbols(spec: dict) -> dict:
    """Return {lib_id: Symbol} for every unique lib_id in the spec."""
    sources = spec["symbol_sources"]
    needed = set()
    for comp in spec["components"]:
        if isinstance(comp, dict) and "lib_id" in comp:
            needed.add(comp["lib_id"])

    symbols = {}
    for lib_id in sorted(needed):
        src_key = lib_id
        if src_key not in sources:
            for k in sources:
                if k.startswith("_"):
                    continue
                if lib_id.endswith(":" + k) or k.endswith(":" + lib_id) or k == lib_id:
                    src_key = k
                    break
        if src_key not in sources or src_key.startswith("_"):
            raise ValueError(f"No symbol source for {lib_id}")

        info = sources[src_key]
        path = REPO_ROOT / info["extract_from"]
        source_type = info.get("source_type", "kicad_sch")

        if source_type == "kicad_sym":
            symbols[lib_id] = extract_lib_symbol_from_symlib(path, lib_id)
        else:
            symbols[lib_id] = extract_lib_symbol_from_sch(path, lib_id)

    return symbols


# ---------------------------------------------------------------------------
# Pin position computation
# ---------------------------------------------------------------------------

def get_pin_list(lib_symbol) -> list[tuple[str, float, float, float]]:
    """Return [(pin_number, lib_x, lib_y, angle_deg), ...] from a lib symbol.

    Preserves duplicate pin numbers (e.g. USB-C shield pins).
    """
    pins = []
    for unit in lib_symbol.units:
        for pin in unit.pins:
            pins.append((str(pin.number), pin.position.X, pin.position.Y, pin.position.angle or 0))
    return pins


def get_unique_pin_numbers(lib_symbol) -> set[str]:
    """Return set of all unique pin numbers."""
    nums = set()
    for unit in lib_symbol.units:
        for pin in unit.pins:
            nums.add(str(pin.number))
    return nums


def compute_pin_position(
    sym_x: float, sym_y: float, sym_angle: float,
    pin_lib_x: float, pin_lib_y: float,
    mirror_x: bool = False, mirror_y: bool = False,
) -> tuple[float, float]:
    """Convert lib-space pin coords to schematic coords.

    KiCad lib symbols use Y-up; schematics use Y-down.
    """
    px, py = pin_lib_x, pin_lib_y

    if mirror_x:
        px = -px
    if mirror_y:
        py = -py

    angle_rad = math.radians(sym_angle)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    sx = sym_x + px * cos_a + py * sin_a
    sy = sym_y - px * sin_a + py * (-cos_a)

    return (round(sx, 2), round(sy, 2))


def compute_stub_endpoint(
    pin_sch_x: float, pin_sch_y: float,
    pin_lib_angle: float, sym_angle: float,
    mirror_x: bool = False, mirror_y: bool = False,
) -> tuple[float, float]:
    """Compute wire stub endpoint extending outward from a pin.

    Pin angle points from tip toward the component body.
    The stub extends 180° opposite (away from body).
    """
    away_angle = pin_lib_angle + sym_angle + 180
    if mirror_x:
        if (away_angle % 360) == 0:
            away_angle = 180
        elif (away_angle % 360) == 180:
            away_angle = 0
    if mirror_y:
        if (away_angle % 360) == 90:
            away_angle = 270
        elif (away_angle % 360) == 270:
            away_angle = 90

    away_angle = away_angle % 360
    angle_rad = math.radians(away_angle)

    dx = round(WIRE_STUB_LEN * math.cos(angle_rad), 2)
    dy = round(-WIRE_STUB_LEN * math.sin(angle_rad), 2)

    return (round(pin_sch_x + dx, 2), round(pin_sch_y + dy, 2))


# ---------------------------------------------------------------------------
# Schematic object construction
# ---------------------------------------------------------------------------

def make_property(key: str, value: str, pos: Position, hide: bool = False, prop_id=None) -> Property:
    eff = Effects(
        font=Font(height=1.27, width=1.27),
        hide=hide,
    )
    return Property(key=key, value=value, position=pos, effects=eff, id=prop_id)


def make_symbol(
    comp: dict,
    lib_symbols: dict,
    sheet_uuid: str,
) -> SchematicSymbol:
    """Create a placed SchematicSymbol from a spec component entry."""
    sym = SchematicSymbol()
    sym.libId = comp["lib_id"]
    x, y = comp["position"]
    angle = comp.get("angle", 0)
    sym.position = Position(X=x, Y=y, angle=angle)
    sym.unit = 1
    sym.inBom = True
    sym.onBoard = True
    sym.dnp = False
    sym.uuid = new_uuid()

    ref = comp["ref"]
    value = comp["value"]
    footprint = comp["footprint"]
    lcsc = comp.get("lcsc") or ""

    sym.properties = [
        make_property("Reference", ref,
                       Position(X=round(x + 2.54, 2), Y=round(y - 1.27, 2), angle=angle)),
        make_property("Value", value,
                       Position(X=x, Y=round(y + 2.54, 2), angle=angle)),
        make_property("Footprint", footprint,
                       Position(X=x, Y=y, angle=0), hide=True),
        make_property("Datasheet", "~",
                       Position(X=x, Y=y, angle=0), hide=True),
    ]
    if lcsc:
        sym.properties.append(
            make_property("LCSC Part", lcsc,
                           Position(X=x, Y=y, angle=0), hide=True)
        )

    lib_sym = lib_symbols[comp["lib_id"]]
    pin_list = get_pin_list(lib_sym)
    sym.pins = {}
    for pin_num, _, _, _ in pin_list:
        sym.pins[str(pin_num)] = new_uuid()

    sym.instances = [
        SymbolProjectInstance(
            name=PROJECT_NAME,
            paths=[
                SymbolProjectPath(
                    sheetInstancePath=f"/{sheet_uuid}",
                    reference=ref,
                    unit=1,
                )
            ],
        )
    ]

    return sym


def make_wire(start: tuple[float, float], end: tuple[float, float]) -> Connection:
    return Connection(
        type="wire",
        points=[
            Position(X=start[0], Y=start[1]),
            Position(X=end[0], Y=end[1]),
        ],
        stroke=Stroke(width=0, type="default"),
        uuid=new_uuid(),
    )


def make_net_label(text: str, x: float, y: float, angle: float = 0) -> LocalLabel:
    label = LocalLabel()
    label.text = text
    label.position = Position(X=x, Y=y, angle=angle)
    label.uuid = new_uuid()
    label.effects = Effects(font=Font(height=1.27, width=1.27))
    return label


def make_no_connect(x: float, y: float) -> NoConnect:
    nc = NoConnect()
    nc.position = Position(X=x, Y=y)
    nc.uuid = new_uuid()
    return nc


def make_hierarchical_label(name: str, shape: str, x: float, y: float, angle: float = 0) -> HierarchicalLabel:
    label = HierarchicalLabel()
    label.text = name
    label.shape = shape
    label.position = Position(X=x, Y=y, angle=angle)
    label.uuid = new_uuid()
    label.effects = Effects(font=Font(height=1.27, width=1.27))
    return label


def label_angle_for_stub(pin_sch: tuple, stub_end: tuple) -> float:
    """Determine the angle for a net label based on stub direction.

    Labels should face outward from the component. In KiCad:
    - angle 0: label text extends to the right (stub goes right)
    - angle 180: label text extends to the left (stub goes left)
    - angle 90: label text extends downward
    - angle 270: label text extends upward
    """
    dx = stub_end[0] - pin_sch[0]
    dy = stub_end[1] - pin_sch[1]

    if abs(dx) > abs(dy):
        return 0 if dx > 0 else 180
    else:
        return 90 if dy > 0 else 270


# ---------------------------------------------------------------------------
# Main generation
# ---------------------------------------------------------------------------

def generate(output_path: Path) -> None:
    spec = load_spec()
    lib_symbols = extract_all_lib_symbols(spec)

    sch = Schematic.create_new()
    sch.version = KICAD9_VERSION
    sch.generator = "eeschema"
    sch.uuid = new_uuid()
    sheet_uuid = sch.uuid

    used_lib_ids = set()
    for comp in spec["components"]:
        if isinstance(comp, dict) and "lib_id" in comp:
            used_lib_ids.add(comp["lib_id"])

    sch.libSymbols = []
    for lib_id in sorted(used_lib_ids):
        sch.libSymbols.append(lib_symbols[lib_id])

    wire_count = 0
    label_count = 0
    nc_count = 0

    for comp in spec["components"]:
        if not isinstance(comp, dict) or "ref" not in comp:
            continue

        sym = make_symbol(comp, lib_symbols, sheet_uuid)
        sch.schematicSymbols.append(sym)

        lib_sym = lib_symbols[comp["lib_id"]]
        all_pins = get_pin_list(lib_sym)
        cx, cy = comp["position"]
        sym_angle = comp.get("angle", 0)
        mirror_x = comp.get("mirror_x", False)
        mirror_y = comp.get("mirror_y", False)

        pin_nets = comp.get("pins", {})
        no_connect_pins = set(comp.get("no_connect", []))

        for pin_num, plx, ply, pin_angle in all_pins:
            pin_sch = compute_pin_position(cx, cy, sym_angle, plx, ply, mirror_x, mirror_y)
            stub_end = compute_stub_endpoint(
                pin_sch[0], pin_sch[1], pin_angle, sym_angle, mirror_x, mirror_y
            )

            if pin_num in pin_nets:
                sch.graphicalItems.append(make_wire(pin_sch, stub_end))
                wire_count += 1

                net_name = pin_nets[pin_num]
                lbl_angle = label_angle_for_stub(pin_sch, stub_end)
                sch.labels.append(make_net_label(net_name, stub_end[0], stub_end[1], lbl_angle))
                label_count += 1

            elif str(pin_num) in no_connect_pins:
                sch.noConnects.append(make_no_connect(pin_sch[0], pin_sch[1]))
                nc_count += 1

    # Hierarchical sheet labels for interface pins
    hlabel_x = 25.4
    hlabel_y_start = 38.1
    hlabel_spacing = 5.08

    type_to_shape = {
        "output": "output",
        "input": "input",
        "bidirectional": "bidirectional",
    }

    for i, iface in enumerate(spec["interface_pins"]):
        y = hlabel_y_start + i * hlabel_spacing
        shape = type_to_shape.get(iface["type"], "bidirectional")
        hlabel = make_hierarchical_label(iface["name"], shape, hlabel_x, y, angle=180)
        sch.hierarchicalLabels.append(hlabel)

        stub_end_x = hlabel_x + WIRE_STUB_LEN
        sch.graphicalItems.append(make_wire((hlabel_x, y), (stub_end_x, y)))
        wire_count += 1
        sch.labels.append(make_net_label(iface["net"], stub_end_x, y, angle=0))
        label_count += 1

    sch.to_file(str(output_path))

    real_comps = [c for c in spec["components"] if isinstance(c, dict) and "ref" in c]
    print(f"Generated: {output_path}")
    print(f"  {len(real_comps)} components")
    print(f"  {wire_count} wire stubs")
    print(f"  {label_count} net labels")
    print(f"  {nc_count} no-connect flags")
    print(f"  {len(spec['interface_pins'])} hierarchical labels")
    print(f"  {len(sch.libSymbols)} unique lib symbols")
    print(f"  Version: {KICAD9_VERSION}")
    print(f"\nOpen in KiCad 9 to verify:")
    print(f"  {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Generate power_management.kicad_sch from spec.json")
    parser.add_argument(
        "--output", "-o",
        default=str(DEFAULT_OUTPUT),
        help=f"Output path (default: {DEFAULT_OUTPUT})",
    )
    args = parser.parse_args()
    output_path = Path(args.output).resolve()
    generate(output_path)


if __name__ == "__main__":
    main()

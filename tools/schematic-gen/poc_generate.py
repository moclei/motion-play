#!/usr/bin/env python3
"""
poc_generate.py — Proof-of-concept: generate a minimal .kicad_sch via kiutils.

Creates a schematic with one resistor (R99, 10kΩ, 0603) and one net label
(TEST_NET) connected to pin 1. Validates that kiutils can produce a file
KiCad 9 opens without errors.

Usage:
    python poc_generate.py [--output path/to/output.kicad_sch]

Default output: hardware/pcb-main/kicad/poc_test.kicad_sch
"""

from __future__ import annotations

import argparse
import copy
import sys
import uuid
from pathlib import Path

from kiutils.schematic import Schematic
from kiutils.items.schitems import (
    Connection,
    LocalLabel,
    SchematicSymbol,
    SymbolProjectInstance,
    SymbolProjectPath,
)
from kiutils.items.common import Effects, Font, Position, Property, Stroke


KICAD9_VERSION = "20250114"
PROJECT_NAME = "motion-play-main"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REFERENCE_SCHEMATIC = REPO_ROOT / "hardware/pcb-main/kicad/3v3_Power_Supply.kicad_sch"
DEFAULT_OUTPUT = REPO_ROOT / "hardware/pcb-main/kicad/poc_test.kicad_sch"


def new_uuid() -> str:
    return str(uuid.uuid4())


def extract_lib_symbol(source_path: Path, lib_id: str):
    """Extract a lib_symbol definition from an existing schematic."""
    sch = Schematic.from_file(str(source_path))
    for sym in sch.libSymbols:
        if sym.libId == lib_id:
            return copy.deepcopy(sym)
    raise ValueError(f"lib_symbol {lib_id!r} not found in {source_path.name}")


def compute_pin_position(symbol_pos: Position, pin_lib_x: float, pin_lib_y: float) -> tuple[float, float]:
    """Convert a pin's lib-coordinate position to schematic coordinates.

    KiCad lib symbols use Y-up; schematics use Y-down. For rotation angle 0:
      schematic_x = symbol_x + pin_lib_x
      schematic_y = symbol_y - pin_lib_y
    """
    import math
    angle_rad = math.radians(symbol_pos.angle or 0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    sx = symbol_pos.X + pin_lib_x * cos_a + pin_lib_y * sin_a
    sy = symbol_pos.Y - pin_lib_x * sin_a + pin_lib_y * (-cos_a)

    return (round(sx, 2), round(sy, 2))


def make_resistor_symbol(
    ref: str,
    value: str,
    footprint: str,
    lcsc: str,
    position: Position,
    sheet_uuid: str,
) -> SchematicSymbol:
    """Create a placed resistor SchematicSymbol."""
    sym = SchematicSymbol()
    sym.libId = "Device:R"
    sym.position = position
    sym.unit = 1
    sym.inBom = True
    sym.onBoard = True
    sym.dnp = False
    sym.uuid = new_uuid()

    def prop(key, val, at_pos=None, hide=False):
        at = at_pos or Position(X=position.X, Y=position.Y, angle=0)
        eff = Effects(
            font=Font(height=1.27, width=1.27),
            hide=hide,
        )
        return Property(key=key, value=val, position=at, effects=eff, id=None)

    angle = position.angle or 0
    sym.properties = [
        prop("Reference", ref,
             Position(X=round(position.X + 2.032, 2), Y=position.Y, angle=angle)),
        prop("Value", value,
             Position(X=position.X, Y=round(position.Y + 2.54, 2), angle=angle)),
        prop("Footprint", footprint, hide=True),
        prop("Datasheet", "~", hide=True),
        prop("Description", "Resistor", hide=True),
        prop("LCSC Part", lcsc, hide=True),
    ]

    sym.pins = {
        "1": new_uuid(),
        "2": new_uuid(),
    }

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


def make_net_label(text: str, position: Position) -> LocalLabel:
    """Create a net label at the given position."""
    label = LocalLabel()
    label.text = text
    label.position = position
    label.uuid = new_uuid()
    label.effects = Effects(
        font=Font(height=1.27, width=1.27),
    )
    return label


def make_wire(start: tuple[float, float], end: tuple[float, float]) -> Connection:
    """Create a wire segment between two points."""
    return Connection(
        type="wire",
        points=[
            Position(X=start[0], Y=start[1]),
            Position(X=end[0], Y=end[1]),
        ],
        stroke=Stroke(width=0, type="default"),
        uuid=new_uuid(),
    )


def generate(output_path: Path) -> None:
    """Generate the proof-of-concept schematic."""

    r_lib_symbol = extract_lib_symbol(REFERENCE_SCHEMATIC, "Device:R")

    sch = Schematic.create_new()
    sch.version = KICAD9_VERSION
    sch.generator = "eeschema"
    sch.uuid = new_uuid()

    sch.libSymbols = [r_lib_symbol]

    resistor_pos = Position(X=127.0, Y=88.9, angle=0)
    sheet_uuid = sch.uuid

    r1 = make_resistor_symbol(
        ref="R99",
        value="10kΩ",
        footprint="Resistor_SMD:R_0603_1608Metric",
        lcsc="C25804",
        position=resistor_pos,
        sheet_uuid=sheet_uuid,
    )
    sch.schematicSymbols.append(r1)

    # Second resistor — shares TEST_NET on pin 2 to prove net-label connectivity
    resistor2_pos = Position(X=152.4, Y=88.9, angle=0)
    r2 = make_resistor_symbol(
        ref="R100",
        value="4.7kΩ",
        footprint="Resistor_SMD:R_0603_1608Metric",
        lcsc="C23162",
        position=resistor2_pos,
        sheet_uuid=sheet_uuid,
    )
    sch.schematicSymbols.append(r2)

    # Wire stubs + labels for R99
    r1_pin1 = compute_pin_position(resistor_pos, 0, 3.81)
    r1_pin2 = compute_pin_position(resistor_pos, 0, -3.81)

    # Wire stubs + labels for R100
    r2_pin1 = compute_pin_position(resistor2_pos, 0, 3.81)
    r2_pin2 = compute_pin_position(resistor2_pos, 0, -3.81)

    wire_len = 2.54

    def stub_up(pin_pos):
        end = (pin_pos[0], round(pin_pos[1] - wire_len, 2))
        return pin_pos, end

    def stub_down(pin_pos):
        end = (pin_pos[0], round(pin_pos[1] + wire_len, 2))
        return pin_pos, end

    # R99: pin 1 → TEST_NET (up), pin 2 → GND (down)
    w1_start, w1_end = stub_up(r1_pin1)
    w2_start, w2_end = stub_down(r1_pin2)
    # R100: pin 1 → TEST_NET (up), pin 2 → OTHER_NET (down)
    w3_start, w3_end = stub_up(r2_pin1)
    w4_start, w4_end = stub_down(r2_pin2)

    for start, end in [(w1_start, w1_end), (w2_start, w2_end),
                       (w3_start, w3_end), (w4_start, w4_end)]:
        sch.graphicalItems.append(make_wire(start, end))

    # TEST_NET on R99 pin 1 and R100 pin 1 — proves two labels share a net
    sch.labels.append(make_net_label("TEST_NET", Position(X=w1_end[0], Y=w1_end[1], angle=0)))
    sch.labels.append(make_net_label("TEST_NET", Position(X=w3_end[0], Y=w3_end[1], angle=0)))
    # GND on both pin 2s
    sch.labels.append(make_net_label("GND", Position(X=w2_end[0], Y=w2_end[1], angle=0)))
    sch.labels.append(make_net_label("GND", Position(X=w4_end[0], Y=w4_end[1], angle=0)))

    sch.to_file(str(output_path))
    print(f"Generated: {output_path}")
    print(f"  2 resistors (R99 10kΩ, R100 4.7kΩ)")
    print(f"  4 wire stubs + 4 net labels (TEST_NET × 2, GND × 2)")
    print(f"  Version: {KICAD9_VERSION}, Generator: eeschema")
    print(f"\nOpen in KiCad 9 to verify:")
    print(f"  {output_path}")


def main():
    parser = argparse.ArgumentParser(description="PoC: generate minimal .kicad_sch")
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

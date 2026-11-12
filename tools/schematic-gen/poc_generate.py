#!/usr/bin/env python3
"""
poc_generate.py — Proof-of-concept: generate a minimal .kicad_sch (through kicad_io).

Creates a schematic with one resistor (R99, 10kΩ, 0603) and one net label
(TEST_NET) connected to pin 1. Validates that the tools can produce a file
KiCad 9 opens without errors.

Usage:
    python poc_generate.py [--output path/to/output.kicad_sch]

Default output: hardware/pcb-main/kicad/poc_test.kicad_sch

Built on kicad_io's raw s-expression layer (tools/kicad-io; run with tools/.venv/bin/python): the
empty sheet is SHEET_TEMPLATE parsed into a kicad_io Doc, items are raw nodes, kio.save writes it.
Library symbols come from modify.extract_lib_symbol. The --output default points into the v7 project
(hardware/pcb-main/kicad/), which is never re-saved: always pass --output.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from pathlib import Path

import sys as _sys
_sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "schematic-modify"))
import modify  # noqa: E402  (extract_lib_symbol: raw library-symbol nodes through kicad_io)
from modify import kio  # noqa: E402
from kicad_io import at_xy, atom_text, child, kids, node, num, q  # noqa: E402

KICAD9_VERSION = "20250114"
PROJECT_NAME = "motion-play-main"

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
REFERENCE_SCHEMATIC = REPO_ROOT / "hardware/pcb-main/kicad/3v3_Power_Supply.kicad_sch"
DEFAULT_OUTPUT = REPO_ROOT / "hardware/pcb-main/kicad/poc_test.kicad_sch"

# An empty KiCad 9 sheet (what kiutils' Schematic.create_new() gave: A4 paper, one sheet instance).
# The uuid is filled in; items are added to the parsed tree, and kicad_io saves it.
SHEET_TEMPLATE = """(kicad_sch
\t(version {version})
\t(generator "eeschema")
\t(uuid "{uuid}")
\t(paper "A4")
\t(lib_symbols)
\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
)
"""


def new_uuid() -> str:
    return str(uuid.uuid4())


def extract_lib_symbol(source_path: Path, lib_id: str):
    """Extract a lib_symbol definition (raw node) from an existing schematic."""
    return modify.extract_lib_symbol(lib_id, source_path)


def compute_pin_position(symbol_pos: tuple, pin_lib_x: float, pin_lib_y: float) -> tuple[float, float]:
    """Convert a pin's lib-coordinate position to schematic coordinates (symbol_pos: x, y, angle).

    KiCad lib symbols use Y-up; schematics use Y-down. For rotation angle 0:
      schematic_x = symbol_x + pin_lib_x
      schematic_y = symbol_y - pin_lib_y
    """
    import math
    sym_x, sym_y, sym_angle = symbol_pos
    angle_rad = math.radians(sym_angle or 0)
    cos_a = math.cos(angle_rad)
    sin_a = math.sin(angle_rad)

    # Library Y is up, sheet Y is down; KiCad rotates counter-clockwise on screen.
    # (Before 2026-11-03 the X term used +pin_lib_y*sin_a: wrong end for 90/270-degree symbols.)
    sx = sym_x + pin_lib_x * cos_a - pin_lib_y * sin_a
    sy = sym_y - pin_lib_x * sin_a + pin_lib_y * (-cos_a)

    return (round(sx, 2), round(sy, 2))


# ---------------------------------------------------------------------------
# Raw-node builders (kicad_io; KiCad 9 form). Numbers are written with kio.num (exact text).
# ---------------------------------------------------------------------------

FONT = "(effects (font (size 1.27 1.27)))"


def make_property(doc, key, value, x, y, angle=0, hide=False):
    return kio.make_property(doc, key, value, x, y, angle, hide=hide, effects=FONT)


def _append_props(sym, props) -> None:
    idx = sym.children.index(child(sym, "uuid"))
    for k, p in enumerate(props, 1):
        sym.children.insert(idx + k, p)


def symbol_node(doc, lib_id, x, y, angle, props, pin_numbers, sheet_path, ref):
    """A placed symbol: one (pin ...) per pin number (a repeated number keeps its first position and
    its last uuid; a uuid is minted per pin record, as kiutils' pin dict did)."""
    sym = node("(symbol (lib_id {}) (at {} {} {}) (unit 1) (exclude_from_sim no) (in_bom yes) "
               "(on_board yes) (dnp no) (uuid {}))".format(q(lib_id), num(x), num(y), num(angle),
                                                           q(new_uuid())))
    pins = {}
    for pin_num in pin_numbers:
        pins[str(pin_num)] = new_uuid()
    _append_props(sym, [make_property(doc, *p[:5], hide=p[5]) for p in props])
    for pn, u in pins.items():
        sym.children.append(node("(pin {} (uuid {}))".format(q(pn), q(u))))
    sym.children.append(node('(instances (project {} (path {} (reference {}) (unit 1))))'.format(
        q(PROJECT_NAME), q(sheet_path), q(ref))))
    return sym


def make_wire(start, end):
    return node("(wire (pts (xy {} {}) (xy {} {})) (stroke (width 0) (type default)) (uuid {}))".format(
        num(start[0]), num(start[1]), num(end[0]), num(end[1]), q(new_uuid())))


def make_net_label(text, x, y, angle=0):
    return node("(label {} (at {} {} {}) {} (uuid {}))".format(
        q(text), num(x), num(y), num(angle), FONT, q(new_uuid())))


def new_sheet(output_path: Path):
    """An empty sheet Doc from SHEET_TEMPLATE (its uuid minted first, as before)."""
    return kio.new_doc(output_path, SHEET_TEMPLATE.format(version=KICAD9_VERSION, uuid=new_uuid()))


def make_resistor_symbol(doc, ref, value, footprint, lcsc, position, sheet_uuid):
    """A placed resistor (raw node); position is (x, y, angle)."""
    x, y, angle = position
    props = [
        ("Reference", ref, round(x + 2.032, 2), y, angle, False),
        ("Value", value, x, round(y + 2.54, 2), angle, False),
        ("Footprint", footprint, x, y, 0, True),
        ("Datasheet", "~", x, y, 0, True),
        ("Description", "Resistor", x, y, 0, True),
        ("LCSC Part", lcsc, x, y, 0, True),
    ]
    return symbol_node(doc, "Device:R", x, y, angle, props, ["1", "2"], "/{}".format(sheet_uuid), ref)


def generate(output_path: Path) -> None:
    """Generate the proof-of-concept schematic."""

    r_lib_symbol = extract_lib_symbol(REFERENCE_SCHEMATIC, "Device:R")

    doc = new_sheet(output_path)
    sch = doc.tree

    child(sch, "lib_symbols").children.append(r_lib_symbol)

    resistor_pos = (127.0, 88.9, 0)
    sheet_uuid = str(kio.atom(child(sch, "uuid")))

    r1 = make_resistor_symbol(
        doc,
        ref="R99",
        value="10kΩ",
        footprint="Resistor_SMD:R_0603_1608Metric",
        lcsc="C25804",
        position=resistor_pos,
        sheet_uuid=sheet_uuid,
    )
    kio.insert_item(sch, r1)

    # Second resistor — shares TEST_NET on pin 2 to prove net-label connectivity
    resistor2_pos = (152.4, 88.9, 0)
    r2 = make_resistor_symbol(
        doc,
        ref="R100",
        value="4.7kΩ",
        footprint="Resistor_SMD:R_0603_1608Metric",
        lcsc="C23162",
        position=resistor2_pos,
        sheet_uuid=sheet_uuid,
    )
    kio.insert_item(sch, r2)

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
        kio.insert_item(sch, make_wire(start, end))

    # TEST_NET on R99 pin 1 and R100 pin 1 — proves two labels share a net
    kio.insert_item(sch, make_net_label("TEST_NET", w1_end[0], w1_end[1], 0))
    kio.insert_item(sch, make_net_label("TEST_NET", w3_end[0], w3_end[1], 0))
    # GND on both pin 2s
    kio.insert_item(sch, make_net_label("GND", w2_end[0], w2_end[1], 0))
    kio.insert_item(sch, make_net_label("GND", w4_end[0], w4_end[1], 0))

    kio.save(doc)
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

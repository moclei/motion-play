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

Built on kicad_io's raw s-expression layer (tools/kicad-io; run with tools/.venv/bin/python): the
empty sheet is SHEET_TEMPLATE parsed into a kicad_io Doc, items are raw nodes, kio.save writes it.
Library symbols come from modify.extract_lib_symbol. The --output default points into the v7 project
(hardware/pcb-main/kicad/), which is never re-saved: always pass --output.
"""

from __future__ import annotations

import argparse
import json
import math
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
WIRE_STUB_LEN = 2.54

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
SPEC_PATH = Path(__file__).resolve().parent / "spec.json"
DEFAULT_OUTPUT = REPO_ROOT / "hardware/pcb-main/kicad/power_management.kicad_sch"

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


def load_spec() -> dict:
    with open(SPEC_PATH) as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Symbol extraction
# ---------------------------------------------------------------------------

def extract_lib_symbol_from_sch(source_path: Path, lib_id: str):
    """A deep copy of the raw lib symbol node from a sheet's lib_symbols (modify.extract_lib_symbol)."""
    return modify.extract_lib_symbol(lib_id, source_path)


def extract_lib_symbol_from_symlib(source_path: Path, lib_id: str):
    """A symbol from a .kicad_sym library (raw node), renamed to the full lib_id (e.g.
    'INA219AIDCNR:INA219AIDCNR') so it matches the placed symbols' lib_id; its units keep their
    short names (modify.extract_lib_symbol)."""
    return modify.extract_lib_symbol(lib_id, source_path)


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

def get_unique_pin_numbers(lib_symbol) -> set:
    """Return set of all unique pin numbers."""
    return {p[0] for p in get_pin_list(lib_symbol)}


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

    # Library Y is up, sheet Y is down; KiCad rotates counter-clockwise on screen.
    # (Before 2026-11-03 the X term used +py*sin_a, which put pins of 90/270-degree symbols
    # at the wrong end; 0/180-degree symbols were unaffected. Same fix as modify.py.)
    sx = sym_x + px * cos_a - py * sin_a
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

# ---------------------------------------------------------------------------
# Raw-node builders (kicad_io; KiCad 9 form). Numbers are written with kio.num (exact text).
# ---------------------------------------------------------------------------

FONT = "(effects (font (size 1.27 1.27)))"


def get_pin_list(lib_symbol) -> list:
    """Return [(pin_number, lib_x, lib_y, angle_deg), ...] from a raw lib symbol node.

    Preserves duplicate pin numbers (e.g. USB-C shield pins).
    """
    pins = []
    for unit in kids(lib_symbol, "symbol"):
        for pin in kids(unit, "pin"):
            x, y, a = at_xy(pin)
            pins.append((str(atom_text(child(pin, "number"), 0)), x, y, a or 0))
    return pins


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


def make_no_connect(x, y):
    return node("(no_connect (at {} {}) (uuid {}))".format(num(x), num(y), q(new_uuid())))


def make_hierarchical_label(name, shape, x, y, angle=0):
    return node("(hierarchical_label {} (shape {}) (at {} {} {}) {} (uuid {}))".format(
        q(name), shape, num(x), num(y), num(angle), FONT, q(new_uuid())))


def new_sheet(output_path: Path):
    """An empty sheet Doc from SHEET_TEMPLATE (its uuid minted first, as before)."""
    return kio.new_doc(output_path, SHEET_TEMPLATE.format(version=KICAD9_VERSION, uuid=new_uuid()))


def make_symbol(doc, comp, lib_symbols, root_uuid, sheet_ref_uuid):
    """A placed symbol (raw node) from a spec component entry."""
    x, y = comp["position"]
    angle = comp.get("angle", 0)
    ref = comp["ref"]
    value = comp["value"]
    footprint = comp["footprint"]
    lcsc = comp.get("lcsc") or ""

    hide_ref = ref.startswith("#")
    props = [
        ("Reference", ref, round(x + 2.54, 2), round(y - 1.27, 2), angle, hide_ref),
        ("Value", value, x, round(y + 2.54, 2), angle, False),
        ("Footprint", footprint, x, y, 0, True),
        ("Datasheet", "~", x, y, 0, True),
    ]
    if lcsc:
        props.append(("LCSC Part", lcsc, x, y, 0, True))

    pin_numbers = [p[0] for p in get_pin_list(lib_symbols[comp["lib_id"]])]
    return symbol_node(doc, comp["lib_id"], x, y, angle, props, pin_numbers,
                       "/{}/{}".format(root_uuid, sheet_ref_uuid), ref)


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

    meta = spec["meta"]
    root_uuid = meta["root_sheet_uuid"]
    sheet_ref_uuid = meta["hierarchical_sheet_uuid"]

    doc = new_sheet(output_path)
    sch = doc.tree

    used_lib_ids = set()
    for comp in spec["components"]:
        if isinstance(comp, dict) and "lib_id" in comp:
            used_lib_ids.add(comp["lib_id"])

    lib_node = child(sch, "lib_symbols")
    for lib_id in sorted(used_lib_ids):
        lib_node.children.append(lib_symbols[lib_id])

    wire_count = 0
    label_count = 0
    nc_count = 0

    for comp in spec["components"]:
        if not isinstance(comp, dict) or "ref" not in comp:
            continue

        sym = make_symbol(doc, comp, lib_symbols, root_uuid, sheet_ref_uuid)
        kio.insert_item(sch, sym)

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
                kio.insert_item(sch, make_wire(pin_sch, stub_end))
                wire_count += 1

                net_name = pin_nets[pin_num]
                lbl_angle = label_angle_for_stub(pin_sch, stub_end)
                kio.insert_item(sch, make_net_label(net_name, stub_end[0], stub_end[1], lbl_angle))
                label_count += 1

            elif str(pin_num) in no_connect_pins:
                kio.insert_item(sch, make_no_connect(pin_sch[0], pin_sch[1]))
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
        kio.insert_item(sch, hlabel)

        stub_end_x = hlabel_x + WIRE_STUB_LEN
        kio.insert_item(sch, make_wire((hlabel_x, y), (stub_end_x, y)))
        wire_count += 1
        kio.insert_item(sch, make_net_label(iface["net"], stub_end_x, y, angle=0))
        label_count += 1

    kio.save(doc)

    real_comps = [c for c in spec["components"] if isinstance(c, dict) and "ref" in c]
    print(f"Generated: {output_path}")
    print(f"  {len(real_comps)} components")
    print(f"  {wire_count} wire stubs")
    print(f"  {label_count} net labels")
    print(f"  {nc_count} no-connect flags")
    print(f"  {len(spec['interface_pins'])} hierarchical labels")
    print(f"  {len(kids(lib_node, "symbol"))} unique lib symbols")
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

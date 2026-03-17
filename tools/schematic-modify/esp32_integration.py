#!/usr/bin/env python3
"""
esp32_integration.py - Phase 1 ESP32 schematic modifications.

Scope for this script:
- Remaining Phase 1a part/library decisions are captured in PART_CHOICES
- Phase 1b programmatic edits:
  - add ESP32 sheet reference on root sheet
  - remove deprecated root symbols (U2/AP2112K + old testpoints)
  - place new power-sheet components off to one side
  - write ai_* annotations through tools/schematic-context/annotate.py

This script intentionally does not generate esp32_s3.kicad_sch (Phase 1c).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from modify import (
    add_component,
    add_hierarchical_label,
    add_sheet_reference,
    annotate_components,
    extract_lib_symbol,
    load_project,
    remove_component,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_SCHEMATIC = REPO_ROOT / "hardware/pcb-main/kicad/motion-play-main.kicad_sch"
POWER_SHEET_KEY = "power_management.kicad_sch"


PART_CHOICES = {
    "ams1117_input_cap": {
        "lcsc": "C109314",
        "symbol": "JLC-MCP-Capacitors:CC0805MKX5R6BB226",
        "footprint": "JLC-MCP:C0805",
        "value": "22uF",
    },
    "ams1117_output_tantalum": {
        "lcsc": "C129288",
        "symbol": "JLC-MCP-Capacitors:CA45-A-6_3V-22UF-K",
        "footprint": "JLC-MCP:CASE-A_3216",
        "value": "22uF 6.3V Tant",
    },
    "usb_esd": {
        "lcsc": "C7519",
        "symbol": "JLC-MCP-Diodes:USBLC6-2SC6",
        "footprint": "JLC-MCP:SOT-23-6_L2.9-W1.6-P0.95-LS2.8-BL",
        "value": "USBLC6-2SC6",
    },
    "power_switch": {
        "lcsc": "C319012",
        "symbol": "JLC-MCP-Misc:SS-12D10L5",
        "footprint": "JLC-MCP:SW-TH_SS-12D10L5",
        "value": "SS-12D10L5",
    },
    "tactile_switch": {
        "lcsc": "C49234124",
        "symbol": "JLC-MCP-ICs:HX_3X4X2-2P-1_6N_TACTILE_SWITCH",
        "footprint": "JLC-MCP:KEY-SMD_L4.0-W3.0-LS4.9-1",
        "value": "TACTILE_SWITCH",
    },
    "status_led": {
        "lcsc": "C4154873",
        "symbol": "JLC-MCP-Inductors:WS2812B-MINI-X1",
        "footprint": "JLC-MCP:LED-SMD_4P-L3.5-W3.5-TL_WS2812B-1",
        "value": "WS2812B-MINI",
    },
}


def _jlc_symbols_dir() -> Path:
    return Path.home() / "Documents/KiCad/9.0/3rdparty/jlc_mcp/symbols"


def _symbol_library_path(lib_id: str) -> Path:
    lib_name = lib_id.split(":", 1)[0]
    return _jlc_symbols_dir() / "{}.kicad_sym".format(lib_name)


def apply_modifications(root_schematic: Path, do_write: bool) -> None:
    docs = load_project(root_schematic)
    root = docs.sheet("root")
    power = docs.sheet(POWER_SHEET_KEY)

    sheet_pins = [
        {"name": "I2C_SDA", "direction": "input"},
        {"name": "I2C_SCL", "direction": "input"},
        {"name": "TCA_RESET", "direction": "output"},
        {"name": "INT1", "direction": "input"},
        {"name": "INT2", "direction": "input"},
        {"name": "INT3", "direction": "input"},
        {"name": "LED_DATA", "direction": "output"},
        {"name": "CHRG_INT", "direction": "input"},
        {"name": "USB_DP", "direction": "bidirectional"},
        {"name": "USB_DN", "direction": "bidirectional"},
        {"name": "+3.3V", "direction": "input"},
        {"name": "GND", "direction": "input"},
    ]
    add_sheet_reference(
        root,
        sheet_name="ESP32_S3",
        file_name="esp32_s3.kicad_sch",
        position=(292.1, 38.1),
        size=(63.5, 55.88),
        pins=sheet_pins,
    )

    for ref in ["U2", "U1", "C1", "C2", "TPIO1", "TPIO2", "TPIO3", "TPIO17", "TPIO18"]:
        remove_component(root, ref)

    ams_lib_id = "JLC-MCP-Power:AMS1117-3_3"
    ams_sym = extract_lib_symbol(ams_lib_id, _symbol_library_path(ams_lib_id))
    add_component(
        power,
        lib_symbol=ams_sym,
        lib_id=ams_lib_id,
        ref="U8",
        value="AMS1117-3.3",
        footprint="JLC-MCP:SOT-223-3_L6.5-W3.4-P2.30-LS7.0-BR",
        lcsc_part="C6186",
        position=(304.8, 45.72),
        pin_nets={"1": "GND", "2": "+3.3V", "3": "+5V", "4": "+3.3V"},
    )

    cin_lib_id = PART_CHOICES["ams1117_input_cap"]["symbol"]
    cin_sym = extract_lib_symbol(cin_lib_id, _symbol_library_path(cin_lib_id))
    add_component(
        power,
        lib_symbol=cin_sym,
        lib_id=cin_lib_id,
        ref="C42",
        value=PART_CHOICES["ams1117_input_cap"]["value"],
        footprint=PART_CHOICES["ams1117_input_cap"]["footprint"],
        lcsc_part=PART_CHOICES["ams1117_input_cap"]["lcsc"],
        position=(317.5, 38.1),
        pin_nets={"1": "+5V", "2": "GND"},
    )

    cout_lib_id = PART_CHOICES["ams1117_output_tantalum"]["symbol"]
    cout_sym = extract_lib_symbol(cout_lib_id, _symbol_library_path(cout_lib_id))
    add_component(
        power,
        lib_symbol=cout_sym,
        lib_id=cout_lib_id,
        ref="C43",
        value=PART_CHOICES["ams1117_output_tantalum"]["value"],
        footprint=PART_CHOICES["ams1117_output_tantalum"]["footprint"],
        lcsc_part=PART_CHOICES["ams1117_output_tantalum"]["lcsc"],
        position=(317.5, 53.34),
        pin_nets={"1": "+3.3V", "2": "GND"},
    )

    esd_lib_id = PART_CHOICES["usb_esd"]["symbol"]
    esd_sym = extract_lib_symbol(esd_lib_id, _symbol_library_path(esd_lib_id))
    add_component(
        power,
        lib_symbol=esd_sym,
        lib_id=esd_lib_id,
        ref="U9",
        value=PART_CHOICES["usb_esd"]["value"],
        footprint=PART_CHOICES["usb_esd"]["footprint"],
        lcsc_part=PART_CHOICES["usb_esd"]["lcsc"],
        position=(330.2, 76.2),
        pin_nets={"1": "USB_DP", "2": "GND", "3": "USB_DN", "4": "USB_DN", "5": "GND", "6": "USB_DP"},
    )

    sw_lib_id = PART_CHOICES["power_switch"]["symbol"]
    sw_sym = extract_lib_symbol(sw_lib_id, _symbol_library_path(sw_lib_id))
    add_component(
        power,
        lib_symbol=sw_sym,
        lib_id=sw_lib_id,
        ref="SW1",
        value=PART_CHOICES["power_switch"]["value"],
        footprint=PART_CHOICES["power_switch"]["footprint"],
        lcsc_part=PART_CHOICES["power_switch"]["lcsc"],
        position=(304.8, 88.9),
        pin_nets={"1": "VSYS", "2": "VSYS_SW", "3": "VSYS"},
    )

    add_hierarchical_label(
        power,
        name="USB_DP",
        shape="bidirectional",
        net="USB_DP",
        position=(279.4, 78.74),
        angle=180,
    )
    add_hierarchical_label(
        power,
        name="USB_DN",
        shape="bidirectional",
        net="USB_DN",
        position=(279.4, 83.82),
        angle=180,
    )

    if do_write:
        docs.save_all()
        annotate_components(
            root_schematic,
            references=["U8", "C42", "C43", "U9", "SW1"],
            annotations={"block": "power", "role": "placed_by_schematic_modify"},
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Apply ESP32 integration schematic modifications.")
    parser.add_argument(
        "--root",
        default=str(ROOT_SCHEMATIC),
        help="Path to root .kicad_sch (default: pcb-main root)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to disk (default is dry-run parse/build only)",
    )
    args = parser.parse_args()

    root_path = Path(args.root).resolve()
    apply_modifications(root_path, do_write=args.apply)
    if args.apply:
        print("Applied modifications to {}".format(root_path))
    else:
        print("Dry-run complete (no files written). Use --apply to save changes.")


if __name__ == "__main__":
    main()

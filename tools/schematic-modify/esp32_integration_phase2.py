#!/usr/bin/env python3
"""
esp32_integration_phase2.py - Fix-up edits after initial Phase 1d placement.

Fixes applied:
1. SW1 pin 3: remove duplicate VSYS label + wire, add no-connect
   (was wired identically to pin 1, making the switch always-on)
2. Power management sheet ref: add USB_DP / USB_DN sheet pins on root
   (hlabels exist inside the sheet but had no matching pins on root)
3. ESP32_S3 sheet: add +5V hierarchical label + sheet pin on root
   (status LED D5 VDD was on a local-scope +5V net, disconnected from global)
4. +3.3V direction: change hlabel on power sheet from input to output,
   and matching sheet pin on root, since AMS1117 now produces +3.3V there
"""

from __future__ import annotations

import argparse
from pathlib import Path

from modify import (
    _compute_pin_position,
    _compute_stub_endpoint,
    _pin_records,
    add_hierarchical_label,
    add_no_connect,
    add_pin_to_sheet_ref,
    annotate_components,
    change_hlabel_shape,
    change_sheet_pin_direction,
    find_component,
    find_sheet_ref,
    get_lib_symbol_for,
    load_project,
    remove_local_label_near,
    remove_wire_between,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
ROOT_SCHEMATIC = REPO_ROOT / "hardware/pcb-main/kicad/motion-play-main.kicad_sch"
POWER_SHEET_KEY = "power_management.kicad_sch"
ESP32_SHEET_KEY = "esp32_s3.kicad_sch"


def fix_sw1_pin3(docs) -> None:
    """SW1 pins 1 and 3 were both wired to VSYS — the switch can never
    disconnect.  Pin 3 should be no-connect (unused SPDT terminal)."""
    power = docs.sheet(POWER_SHEET_KEY)
    sw1 = find_component(power, "SW1")
    if sw1 is None:
        raise ValueError("SW1 not found on power sheet")

    lib_sym = get_lib_symbol_for(power, sw1.libId)
    if lib_sym is None:
        raise ValueError("Lib symbol for SW1 ({}) not found".format(sw1.libId))

    sx = sw1.position.X
    sy = sw1.position.Y
    sa = sw1.position.angle or 0

    for pin_num, px, py, pa in _pin_records(lib_sym):
        if pin_num != "3":
            continue

        pin_sch = _compute_pin_position(sx, sy, sa, px, py)
        stub_end = _compute_stub_endpoint(pin_sch[0], pin_sch[1], pa, sa)

        label_ok = remove_local_label_near(power, "VSYS", stub_end)
        wire_ok = remove_wire_between(power, pin_sch, stub_end)
        add_no_connect(power, pin_sch)

        print("  SW1 pin 3: label removed={}, wire removed={}, NC added".format(
            label_ok, wire_ok))
        return

    raise ValueError("Pin 3 not found in SW1 lib symbol")


def add_usb_pins_to_power_ref(docs) -> None:
    """USB_DP and USB_DN hlabels exist inside power_management but the
    sheet reference on root had no matching pins — signals couldn't flow."""
    root = docs.sheet("root")
    add_pin_to_sheet_ref(root, POWER_SHEET_KEY, "USB_DP", "bidirectional")
    add_pin_to_sheet_ref(root, POWER_SHEET_KEY, "USB_DN", "bidirectional")
    print("  Added USB_DP + USB_DN pins to {} sheet ref".format(POWER_SHEET_KEY))


def add_5v_to_esp32_sheet(docs) -> None:
    """D5 (WS2812B status LED) VDD is on local-scope /ESP32_S3/+5V which
    is disconnected from global +5V.  Add a +5V hierarchical label inside
    the ESP32 sheet and a matching sheet pin on the root reference."""
    esp32 = docs.sheet(ESP32_SHEET_KEY)

    existing_names = {hl.text for hl in esp32.schematic.hierarchicalLabels}
    if "+5V" in existing_names:
        print("  +5V hlabel already exists on ESP32 sheet — skipping")
    else:
        hlabel_x = 25.4
        hlabel_y = 99.06
        add_hierarchical_label(
            esp32,
            name="+5V",
            shape="input",
            net="+5V",
            position=(hlabel_x, hlabel_y),
            angle=180,
        )
        print("  Added +5V hierarchical label inside {}".format(ESP32_SHEET_KEY))

    root = docs.sheet("root")
    sheet = find_sheet_ref(root, ESP32_SHEET_KEY)
    existing_pin_names = {p.name for p in sheet.pins}
    if "+5V" in existing_pin_names:
        print("  +5V sheet pin already exists on root ref — skipping")
    else:
        add_pin_to_sheet_ref(root, ESP32_SHEET_KEY, "+5V", "input")
        print("  Added +5V pin to {} sheet ref on root".format(ESP32_SHEET_KEY))


def fix_3v3_direction(docs) -> None:
    """AMS1117 on power sheet now produces +3.3V — the hierarchical label
    and sheet pin direction must change from input to output."""
    power = docs.sheet(POWER_SHEET_KEY)
    root = docs.sheet("root")

    hl_ok = change_hlabel_shape(power, "+3.3V", "output")
    pin_ok = change_sheet_pin_direction(root, POWER_SHEET_KEY, "+3.3V", "output")
    print("  +3.3V direction: hlabel changed={}, sheet pin changed={}".format(
        hl_ok, pin_ok))


def apply_all(root_schematic: Path, do_write: bool) -> None:
    docs = load_project(root_schematic)

    print("1. Fix SW1 pin 3 (NC instead of duplicate VSYS)")
    fix_sw1_pin3(docs)

    print("2. Add USB_DP/USB_DN pins to power_management sheet ref")
    add_usb_pins_to_power_ref(docs)

    print("3. Add +5V to ESP32_S3 sheet + root reference")
    add_5v_to_esp32_sheet(docs)

    print("4. Change +3.3V direction to output on power sheet")
    fix_3v3_direction(docs)

    if do_write:
        docs.save_all()
        print("\nSaved all sheets.  Run extract.py --previous to refresh context.")
    else:
        print("\nDry-run complete (no files written). Use --apply to save.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 2 ESP32 integration fixes (SW1, USB pins, +5V, +3.3V direction).")
    parser.add_argument(
        "--root",
        default=str(ROOT_SCHEMATIC),
        help="Path to root .kicad_sch (default: pcb-main root)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes to disk (default is dry-run)",
    )
    args = parser.parse_args()
    apply_all(Path(args.root).resolve(), do_write=args.apply)


if __name__ == "__main__":
    main()

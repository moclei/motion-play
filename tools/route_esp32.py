#!/usr/bin/env python3
"""
route_esp32.py — Programmatic routing for ESP32 integration priorities 2-5.

Adds tracks and vias to the PCB for:
  - Priority 2 remaining: +5V connections, GND vias
  - Priority 3: EN circuit, BOOT circuit, decoupling caps
  - Priority 4: I2C, TCA_RESET, LED_DATA, CHRG_INT to U3
  - Priority 5: U3 GND pad vias, U8 thermal vias

Board: 4-layer (F.Cu, In1.Cu, In2.Cu, B.Cu), 88mm × 40mm
  - In1.Cu: GND zone (full board)
  - In2.Cu: +5V zone (full board) + +3.3V zone (partial, right/bottom)

Usage:
    python route_esp32.py <pcb_file> [--dry-run]
"""

import argparse
import sys
import uuid
from pathlib import Path

from kiutils.board import Board
from kiutils.items.common import Position
from kiutils.items.brditems import Segment, Via


def make_tstamp():
    return str(uuid.uuid4())


def add_seg(board, net_num, layer, width, x1, y1, x2, y2):
    seg = Segment()
    seg.start = Position(X=x1, Y=y1)
    seg.end = Position(X=x2, Y=y2)
    seg.width = width
    seg.layer = layer
    seg.net = net_num
    seg.locked = False
    seg.tstamp = make_tstamp()
    board.traceItems.append(seg)
    return seg


def add_via(board, net_num, x, y, size=0.6, drill=0.3, layers=None):
    if layers is None:
        layers = ['F.Cu', 'B.Cu']
    v = Via()
    v.position = Position(X=x, Y=y)
    v.size = size
    v.drill = drill
    v.layers = layers
    v.net = net_num
    v.locked = False
    v.tstamp = make_tstamp()
    board.traceItems.append(v)
    return v


def build_net_map(board):
    name_to_num = {}
    for n in board.nets:
        name_to_num[n.name] = n.number
    return name_to_num


def route_priority2_remaining(board, nets, log):
    """
    +5V → U8 pin 3 (111.0, 105.8): via to In2.Cu +5V zone
    +5V → D5 pin 2 (150.1, 103.1): via to In2.Cu +5V zone
    GND vias for new ESP32 components
    """
    n5v = nets['+5V']
    ngnd = nets['GND']

    log.append("--- Priority 2 remaining ---")

    # +5V to U8 pin 3: short trace north then via
    add_seg(board, n5v, 'F.Cu', 0.5, 111.0, 105.8, 111.0, 104.8)
    add_via(board, n5v, 111.0, 104.8)
    log.append("+5V: U8 pin 3 (111.0,105.8) → via at (111.0,104.8)")

    # +5V to D5 pin 2: short trace then via
    add_seg(board, n5v, 'F.Cu', 0.25, 150.1, 103.1, 150.1, 102.3)
    add_via(board, n5v, 150.1, 102.3)
    log.append("+5V: D5 pin 2 (150.1,103.1) → via at (150.1,102.3)")

    # U8 pin 1 (GND) at (115.6, 105.8)
    add_seg(board, ngnd, 'F.Cu', 0.5, 115.6, 105.8, 116.3, 105.8)
    add_via(board, ngnd, 116.3, 105.8)
    log.append("GND: U8 pin 1 (115.6,105.8) → via at (116.3,105.8)")

    # D5 pin 4 (GND) at (148.4, 104.8)
    add_seg(board, ngnd, 'F.Cu', 0.25, 148.4, 104.8, 148.4, 105.6)
    add_via(board, ngnd, 148.4, 105.6)
    log.append("GND: D5 pin 4 (148.4,104.8) → via at (148.4,105.6)")


def route_priority3_en(board, nets, log):
    """
    EN circuit:
      R50 p2 (115.8, 114.8) ↔ C50 p1 (115.8, 116.4) — vertical trace
      R50 p2 (115.8, 114.8) → via → B.Cu → via → U3 p3 (122.4, 111.4)
      SW2 p1 (121.9, 130.4) → via → B.Cu → via → U3 p3 area
      C50 p2 (114.2, 116.4) → GND via
      SW2 p2 (126.2, 130.4) → GND via
    """
    n_en = nets['/ESP32_S3/EN']
    ngnd = nets['GND']

    log.append("--- Priority 3: EN circuit ---")

    # R50 p2 ↔ C50 p1: vertical on F.Cu
    add_seg(board, n_en, 'F.Cu', 0.2, 115.8, 114.8, 115.8, 116.4)
    log.append("EN: R50 p2 (115.8,114.8) → C50 p1 (115.8,116.4) on F.Cu")

    # R50 p2 → U3 p3 via B.Cu
    # Path: R50 p2 (115.8,114.8) → short trace → via → B.Cu diagonal → via → U3 p3
    add_seg(board, n_en, 'F.Cu', 0.2, 115.8, 114.8, 115.8, 113.5)
    add_via(board, n_en, 115.8, 113.5)
    # B.Cu: (115.8, 113.5) → diagonal to (120.5, 111.5) → (122.0, 111.5)
    add_seg(board, n_en, 'B.Cu', 0.2, 115.8, 113.5, 118.3, 111.5)
    add_seg(board, n_en, 'B.Cu', 0.2, 118.3, 111.5, 121.5, 111.5)
    add_via(board, n_en, 121.5, 111.5)
    add_seg(board, n_en, 'F.Cu', 0.2, 121.5, 111.5, 122.4, 111.4)
    log.append("EN: R50 p2 → via(115.8,113.5) → B.Cu → via(121.5,111.5) → U3 p3 (122.4,111.4)")

    # SW2 p1 → EN via B.Cu
    # Path: SW2 p1 (121.9, 130.4) → via → B.Cu north → connect to EN B.Cu trace
    add_via(board, n_en, 121.9, 130.4)
    # B.Cu: (121.9, 130.4) → north to (121.5, 111.5) — join the EN B.Cu trace
    add_seg(board, n_en, 'B.Cu', 0.2, 121.9, 130.4, 121.5, 130.0)
    add_seg(board, n_en, 'B.Cu', 0.2, 121.5, 130.0, 121.5, 111.5)
    log.append("EN: SW2 p1 (121.9,130.4) → via → B.Cu north → join at (121.5,111.5)")

    # C50 p2 (GND) at (114.2, 116.4)
    add_via(board, ngnd, 114.2, 116.4)
    log.append("GND: C50 p2 via at (114.2,116.4)")

    # SW2 p2 (GND) at (126.2, 130.4)
    add_via(board, ngnd, 126.2, 130.4)
    log.append("GND: SW2 p2 via at (126.2,130.4)")


def route_priority3_boot(board, nets, log):
    """
    BOOT circuit:
      R51 p2 (139.8, 128.5) → U3 p27 (139.9, 125.4) — nearly vertical
      SW3 p1 (133.2, 130.5) → east along y=129.5 → R51 p2
      R51 p1 (139.8, 130.1) → +3.3V via (In2.Cu zone covers this area)
      SW3 p2 (137.6, 130.5) → GND via
    """
    n_boot = nets['/ESP32_S3/GPIO0_BOOT']
    n33 = nets['+3.3V']
    ngnd = nets['GND']

    log.append("--- Priority 3: BOOT circuit ---")

    # R51 p2 → U3 p27: nearly vertical on F.Cu
    add_seg(board, n_boot, 'F.Cu', 0.2, 139.8, 128.5, 139.9, 125.4)
    log.append("BOOT: R51 p2 (139.8,128.5) → U3 p27 (139.9,125.4) on F.Cu")

    # SW3 p1 → R51 p2: route along y=129.5 to avoid bottom pins
    add_seg(board, n_boot, 'F.Cu', 0.2, 133.2, 130.5, 133.2, 129.5)
    add_seg(board, n_boot, 'F.Cu', 0.2, 133.2, 129.5, 139.0, 129.5)
    add_seg(board, n_boot, 'F.Cu', 0.2, 139.0, 129.5, 139.8, 128.5)
    log.append("BOOT: SW3 p1 (133.2,130.5) → y=129.5 → (139.8,128.5) on F.Cu")

    # R51 p1 (+3.3V): via to In2.Cu +3.3V zone
    add_seg(board, n33, 'F.Cu', 0.25, 139.8, 130.1, 140.5, 130.8)
    add_via(board, n33, 140.5, 130.8)
    log.append("+3.3V: R51 p1 (139.8,130.1) → via at (140.5,130.8)")

    # SW3 p2 (GND)
    add_via(board, ngnd, 137.6, 130.5)
    log.append("GND: SW3 p2 via at (137.6,130.5)")


def route_priority3_decoupling(board, nets, log):
    """
    Decoupling caps C51-C55: +3.3V bus from existing trace, GND vias.

    +3.3V bus: branch from existing +3.3V trace at (119.0, ~110.0) south
    along x=119.0 to connect all cap +3.3V pins.
    Individual GND vias for each cap's ground pin.

    R50 p1 (+3.3V at 114.2, 114.8): horizontal trace to +3.3V bus.
    """
    n33 = nets['+3.3V']
    ngnd = nets['GND']

    log.append("--- Priority 3: Decoupling caps ---")

    # +3.3V vertical bus from existing trace to caps
    # Existing +3.3V trace passes through (118.30, 109.90) → (120.35, 109.90)
    # Branch at (119.0, 109.90) south to (119.0, 121.5)
    # Use 0.4mm width (power trace, but short local bypass)
    add_seg(board, n33, 'F.Cu', 0.4, 119.0, 109.90, 119.0, 121.5)
    log.append("+3.3V bus: (119.0,109.9) → (119.0,121.5) on F.Cu at 0.4mm")

    # R50 p1 (+3.3V) at (114.2, 114.8): trace east to bus
    add_seg(board, n33, 'F.Cu', 0.25, 114.2, 114.8, 118.8, 114.8)
    log.append("+3.3V: R50 p1 (114.2,114.8) → bus at (118.8,114.8)")

    # GND vias for each cap's GND pin (pin 2)
    gnd_caps = [
        ('C51', 117.5, 114.7),
        ('C52', 117.5, 116.4),
        ('C53', 117.5, 118.1),
        ('C54', 117.5, 119.8),
        ('C55', 117.4, 121.5),
    ]
    for name, x, y in gnd_caps:
        add_via(board, ngnd, x, y)
        log.append(f"GND: {name} p2 via at ({x},{y})")


def route_priority4_i2c(board, nets, log):
    """
    I2C_SDA: extend from U4 pin 23 (149.07, 116.92) to U3 pin 37 (139.9, 112.7)
    I2C_SCL: extend from U4 pin 22 (149.07, 116.27) to U3 pin 36 (139.9, 113.9)

    Both route on F.Cu: west from U4 area, then diagonal to U3 right side.
    """
    n_sda = nets['/I2C_SDA']
    n_scl = nets['/I2C_SCL']

    log.append("--- Priority 4: I2C ---")

    # I2C_SDA: (149.07, 116.92) already has trace to U4
    # Extend west then diagonal to U3 pin 37
    # (149.07, 116.92) → west to (145.5, 116.92) → 45° diagonal → (141.3, 112.7) → (139.9, 112.7)
    add_seg(board, n_sda, 'F.Cu', 0.25, 149.07, 116.92, 145.5, 116.92)
    add_seg(board, n_sda, 'F.Cu', 0.25, 145.5, 116.92, 141.28, 112.70)
    add_seg(board, n_sda, 'F.Cu', 0.25, 141.28, 112.70, 139.9, 112.70)
    log.append("I2C_SDA: (149.07,116.92) → west → 45° → U3 p37 (139.9,112.7)")

    # I2C_SCL: (149.07, 116.27) already has trace to U4
    # Extend west then diagonal to U3 pin 36
    # (149.07, 116.27) → west to (146.5, 116.27) → 45° diagonal → (144.13, 113.9) → (139.9, 113.9)
    add_seg(board, n_scl, 'F.Cu', 0.25, 149.07, 116.27, 146.5, 116.27)
    add_seg(board, n_scl, 'F.Cu', 0.25, 146.5, 116.27, 144.13, 113.90)
    add_seg(board, n_scl, 'F.Cu', 0.25, 144.13, 113.90, 139.9, 113.90)
    log.append("I2C_SCL: (149.07,116.27) → west → 45° → U3 p36 (139.9,113.9)")


def route_priority4_tca_reset(board, nets, log):
    """
    TCA_RESET: extend from existing B.Cu dead end (153.31, 113.37) to U3 pin 18 (128.0, 126.7).

    Route on B.Cu: diagonal southwest from existing endpoint to near U3 pin 18,
    then via to F.Cu for the final connection.
    """
    n_tca = nets['/TCA_RESET']

    log.append("--- Priority 4: TCA_RESET ---")

    # U3 pin 18 at (128.0, 126.7) on F.Cu
    # Short trace south from pin, then via to B.Cu
    add_seg(board, n_tca, 'F.Cu', 0.25, 128.0, 126.7, 128.0, 127.5)
    add_via(board, n_tca, 128.0, 127.5)

    # B.Cu: from (128.0, 127.5) → east to (140.0, 127.5) → 45° diagonal NE → (153.31, 113.37)
    # Diagonal from (140.0, 127.5) to (153.31, 113.37): dx=13.31, dy=-14.13
    # Not exactly 45°. Split into 45° + horizontal:
    # (140.0, 127.5) → 45° → (154.13, 113.37) — overshoot on x. Adjust.
    # dy = 127.5 - 113.37 = 14.13. 45° segment: dx = 14.13.
    # Start of diagonal: x = 153.31 - 14.13 = 139.18
    # So: (128.0, 127.5) → (139.18, 127.5) → 45° → (153.31, 113.37)
    add_seg(board, n_tca, 'B.Cu', 0.25, 128.0, 127.5, 139.18, 127.5)
    add_seg(board, n_tca, 'B.Cu', 0.25, 139.18, 127.5, 153.31, 113.37)
    log.append("TCA_RESET: U3 p18 (128.0,126.7) → via(128.0,127.5) → B.Cu east → 45° → existing (153.31,113.37)")


def route_priority4_led_data(board, nets, log):
    """
    LED_DATA: U3 pin 9 (122.4, 119.0) → IC1 pin 2 area (144.46, 134.20).

    Route via B.Cu to avoid F.Cu congestion:
    F.Cu short → via → B.Cu diagonal → via → F.Cu to IC1.
    """
    n_led = nets['/LED_DATA']

    log.append("--- Priority 4: LED_DATA ---")

    # U3 pin 9 at (122.4, 119.0) → short trace west → via
    add_seg(board, n_led, 'F.Cu', 0.25, 122.4, 119.0, 121.5, 119.0)
    add_via(board, n_led, 121.5, 119.0)

    # B.Cu: (121.5, 119.0) → south to (121.5, 120.0) → 45° diagonal to (134.5, 133.0) → east to (143.0, 133.0)
    add_seg(board, n_led, 'B.Cu', 0.25, 121.5, 119.0, 121.5, 120.0)
    add_seg(board, n_led, 'B.Cu', 0.25, 121.5, 120.0, 134.5, 133.0)
    add_seg(board, n_led, 'B.Cu', 0.25, 134.5, 133.0, 143.0, 133.0)

    # Via back to F.Cu, then short trace to existing LED_DATA at (144.46, 134.20)
    add_via(board, n_led, 143.0, 133.0)
    add_seg(board, n_led, 'F.Cu', 0.25, 143.0, 133.0, 144.46, 134.20)
    log.append("LED_DATA: U3 p9 → via(121.5,119.0) → B.Cu diagonal → via(143.0,133.0) → IC1 (144.46,134.20)")


def route_priority4_chrg_int(board, nets, log):
    """
    CHRG_INT: U3 pin 23 (134.4, 126.7) → existing routing near R38 area.

    Existing CHRG_INT has a dead end at (98.94, 118.81) on F.Cu.
    Route via B.Cu: U3 p23 → via → B.Cu west → via → F.Cu to join existing trace.
    """
    n_chrg = nets['/CHRG_INT']

    log.append("--- Priority 4: CHRG_INT ---")

    # U3 pin 23 at (134.4, 126.7) → short trace south → via
    add_seg(board, n_chrg, 'F.Cu', 0.25, 134.4, 126.7, 134.4, 127.5)
    add_via(board, n_chrg, 134.4, 127.5)

    # B.Cu: west from (134.4, 127.5) → to near the existing F.Cu trace
    # Existing CHRG_INT on F.Cu runs vertically at x≈101.16-101.75, y=109-121
    # Route on B.Cu: (134.4, 127.5) → west to (105.0, 127.5) → north to (105.0, 120.0) → via to F.Cu
    # Adjust to avoid VSYS on B.Cu (x≈99-101, y=115-128 at 1.0mm width)
    # Route west, staying above (south of) VSYS_SENSE B.Cu trace at (109.1, 127.9)
    # Path: (134.4, 127.5) → (110.0, 127.5) → diagonal NW → (104.5, 121.5) → via to F.Cu
    # Then short F.Cu trace to connect to existing CHRG_INT at x≈101

    # Adjusted path avoiding VSYS_SENSE B.Cu at (109.1, 127.9):
    # (134.4, 127.5) → (112.0, 127.5) → 45° NW → (106.0, 121.5) → via
    add_seg(board, n_chrg, 'B.Cu', 0.25, 134.4, 127.5, 112.0, 127.5)
    add_seg(board, n_chrg, 'B.Cu', 0.25, 112.0, 127.5, 106.0, 121.5)
    add_via(board, n_chrg, 106.0, 121.5)

    # F.Cu: connect via to existing CHRG_INT routing
    # Existing dead end at (98.94, 118.81). Also trace at (101.16, 120.38).
    # From (106.0, 121.5) → diagonal to (101.16, 120.38)
    # Actually, easier to connect to the vertical run at (101.16, y) or (101.75, y)
    # (106.0, 121.5) → diagonal SW → (101.5, 121.5) — join near existing trace area
    add_seg(board, n_chrg, 'F.Cu', 0.25, 106.0, 121.5, 101.16, 121.5)
    # This should connect to the existing trace at (101.16, 120.38) via overlapping segment
    # Add a connecting segment:
    add_seg(board, n_chrg, 'F.Cu', 0.25, 101.16, 121.5, 101.16, 120.38)
    log.append("CHRG_INT: U3 p23 → via(134.4,127.5) → B.Cu west → via(106.0,121.5) → F.Cu → existing trace")


def route_priority5_gnd_vias(board, nets, log):
    """
    U3 GND pad: 9 vias in 3×3 grid (pin 41 sub-pads).
    Sub-pad centers at:
      (128.3, 115.2), (128.3, 116.6), (128.3, 118.0)
      (129.7, 115.2), (129.7, 116.6), (129.7, 118.0)
      (131.1, 115.2), (131.1, 116.6), (131.1, 118.0)

    U8 thermal vias: 4 vias in +3.3V pour under tab pad.
    U8 pin 4 (tab) at (113.3, 111.7), connect to +3.3V.
    """
    ngnd = nets['GND']
    n33 = nets['+3.3V']

    log.append("--- Priority 5: GND and thermal vias ---")

    # U3 GND pad 3×3 vias
    u3_gnd_positions = [
        (128.3, 115.2), (128.3, 116.6), (128.3, 118.0),
        (129.7, 115.2), (129.7, 116.6), (129.7, 118.0),
        (131.1, 115.2), (131.1, 116.6), (131.1, 118.0),
    ]
    for x, y in u3_gnd_positions:
        add_via(board, ngnd, x, y, size=0.5, drill=0.25)
    log.append(f"GND: U3 pad 41 — 9 vias in 3×3 grid (0.5/0.25mm)")

    # U8 thermal vias under tab (pin 4 at (113.3, 111.7), net +3.3V)
    # Place 4 vias in a 2×2 pattern centered on the tab
    u8_thermal = [
        (112.5, 110.8), (114.1, 110.8),
        (112.5, 112.6), (114.1, 112.6),
    ]
    for x, y in u8_thermal:
        add_via(board, n33, x, y, size=0.6, drill=0.3)
    log.append(f"+3.3V: U8 tab — 4 thermal vias in 2×2 (0.6/0.3mm)")


def main():
    parser = argparse.ArgumentParser(description='Route ESP32 integration priorities 2-5')
    parser.add_argument('pcb_file', help='Path to .kicad_pcb file')
    parser.add_argument('--dry-run', action='store_true', help='Print plan without modifying file')
    args = parser.parse_args()

    pcb_path = Path(args.pcb_file)
    if not pcb_path.exists():
        print(f"Error: {pcb_path} not found")
        sys.exit(1)

    board = Board.from_file(str(pcb_path))
    nets = build_net_map(board)

    # Verify required nets exist
    required = ['+5V', 'GND', '+3.3V', '/ESP32_S3/EN', '/ESP32_S3/GPIO0_BOOT',
                '/I2C_SDA', '/I2C_SCL', '/TCA_RESET', '/LED_DATA', '/CHRG_INT']
    missing = [n for n in required if n not in nets]
    if missing:
        print(f"Error: Missing nets: {missing}")
        sys.exit(1)

    initial_count = len(board.traceItems)
    log = []

    route_priority2_remaining(board, nets, log)
    route_priority3_en(board, nets, log)
    route_priority3_boot(board, nets, log)
    route_priority3_decoupling(board, nets, log)
    route_priority4_i2c(board, nets, log)
    route_priority4_tca_reset(board, nets, log)
    route_priority4_led_data(board, nets, log)
    route_priority4_chrg_int(board, nets, log)
    route_priority5_gnd_vias(board, nets, log)

    final_count = len(board.traceItems)
    added = final_count - initial_count

    print(f"\n{'DRY RUN — ' if args.dry_run else ''}Routing summary:")
    print(f"  Initial trace items: {initial_count}")
    print(f"  Added: {added} (segments + vias)")
    print(f"  Final trace items: {final_count}")
    print()
    for line in log:
        print(f"  {line}")
    print()

    if not args.dry_run:
        board.to_file(str(pcb_path))
        print(f"Saved to {pcb_path}")
        print("Open in KiCad and run DRC to verify. Refill zones (Edit → Fill All Zones).")
    else:
        print("Dry run — no changes saved.")


if __name__ == '__main__':
    main()

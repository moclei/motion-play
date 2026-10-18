"""
PCB Enclosure — Motion Play Main Board v7

Two-part box: base with front-side component cavity + removable lid
on the battery (back) side for 18650 cell swap.

v7 differences from v6:
  - 88.2 × 38.5 mm rectangular board (on-board ESP32-S3-WROOM,
    no T-Display overhang)
  - 18650 battery holder on PCB back (19 mm thick with cell)
  - USB-C on -X edge; slide switch + WS2812B on +Y edge; JST-PH
    (LED strip) + 3× JST-SH (sensors) on +X edge; -Y edge is free
  - Front-side components all ≤ 5.75 mm tall (J3 JST-PH is tallest)

Coordinate system:
  Origin  = center of PCB cavity (XY)
  Z = 0   = outside bottom of floor; +Z toward the lid (battery side)
  +X      = JST connector side (KiCad +X)
  +Y      = switch/LED side (KiCad +Y)
  The PCB's component face points -Z (down toward the floor); the
  battery holder protrudes +Z toward the lid.

KiCad board extents: (75.7, 101) – (163.9, 139.5)
  → center (119.8, 120.25), 88.2 × 38.5 mm

Print orientation:
  Base — open cavity facing up (print bed contacts the floor exterior)
  Lid  — top face down (rim points up)
Material: PLA for test fit, PETG for final.

See mechanical/FDM_DESIGN_RULES.md
See hardware/pcb-main/kicad/pcb-layout-context.json
"""

from build123d import *
from pathlib import Path

try:
    from ocp_vscode import show, set_port
    set_port(3939)
    HAS_VIEWER = True
except ImportError:
    HAS_VIEWER = False

OUTPUT_DIR = Path(__file__).parent

# ============================================================
# PCB dimensions and KiCad → enclosure mapping
# ============================================================

PCB_LENGTH = 88.2
PCB_WIDTH = 38.5
PCB_THICKNESS = 1.55

KICAD_CENTER_X = 119.8
KICAD_CENTER_Y = 120.25


def k2e_x(kx):
    return kx - KICAD_CENTER_X


def k2e_y(ky):
    return ky - KICAD_CENTER_Y


# ============================================================
# Component Z-heights — measured by user (2026-04-17)
# "Height above PCB" = from PCB front face outward; in enc coords
# front-side components extend DOWNWARD from PCB face toward -Z.
# ============================================================

H_USBC = 3.0             # J7 body, flush with board edge
H_JSTPH = 5.75           # J3 (tallest front-side)
H_JSTSH = 3.0            # J4 / J5 / J6
H_SW_HANDLE = 0.5        # SW1 actuator top (above PCB surface)
H_SW_BODY = 3.5          # assumed body thickness (not measured)
H_WS2812 = 1.5           # D5
H_ESP32 = 3.5            # U3
H_BATTERY = 19.0         # BT1 holder + 18650 on PCB back

FRONT_MAX = max(H_USBC, H_JSTPH, H_JSTSH, H_SW_BODY, H_ESP32)  # 5.75

# ============================================================
# FDM parameters (mechanical/FDM_DESIGN_RULES.md)
# ============================================================

CLEARANCE = 0.2          # per-side sliding fit for PCB in cavity
WALL = 2.5               # external wall thickness (non-corner)
FLOOR = 1.6              # floor thickness
CORNER_R = 2.0           # external corner radius

LID_PLATE = 3.0          # thick enough to leave ≥1.5 mm below M2 counterbore
LID_RIM_DEPTH = 3.0      # lid rim extends into cavity (tongue-in-groove)
LID_RIM_WALL = 1.2
LID_RIM_GAP = 0.15       # rim clearance to cavity

# ============================================================
# PCB cavity geometry
# ============================================================

# Rail clears JST-PH (5.75 mm) with ~1 mm margin
PCB_RAIL_Z = FRONT_MAX + 1.0                 # 6.75
BATTERY_CLEARANCE = 1.0                       # above battery top

CAVITY_X = PCB_LENGTH + 2 * CLEARANCE         # 88.6
CAVITY_Y = PCB_WIDTH  + 2 * CLEARANCE         # 38.9
CAVITY_Z = PCB_RAIL_Z + PCB_THICKNESS + H_BATTERY + BATTERY_CLEARANCE
# = 6.75 + 1.55 + 19 + 1 = 28.3

PCB_LEDGE_W = 1.0                             # rail protrusion into cavity

# PCB Z position (front face of PCB points -Z)
PCB_Z_BOT = FLOOR + PCB_RAIL_Z                # 8.35  (front face)
PCB_Z_TOP = PCB_Z_BOT + PCB_THICKNESS         # 9.90  (back face, battery side)

# ============================================================
# Screw bosses — M2 heat-set inserts, 4 corners OUTSIDE the PCB
# footprint. Boss placed diagonally outside the cavity corner at 45°
# which minimises the extra outer-shell area.
# ============================================================

M2_INSERT_D = 3.2        # heat-set drill (brass insert ~3 mm OD)
M2_BOSS_OD = 5.0
M2_CLEARANCE_D = 2.4
M2_HEAD_D = 4.2
M2_HEAD_DEPTH = 1.5
BOSS_WALL_AROUND = 0.5   # material outside boss to outer face

# 45° diagonal offset from cavity corner so boss just clears PCB corner
# Constraint: (bx - CAVITY_X/2)^2 + (by - CAVITY_Y/2)^2 >= (M2_BOSS_OD/2)^2
# Pick bx - CAVITY_X/2 = by - CAVITY_Y/2 = M2_BOSS_OD/(2·√2)
_diag = M2_BOSS_OD / (2 ** 0.5) / 2 + 0.1      # +0.1 mm safety
BOSS_X = CAVITY_X / 2 + _diag                  # ≈ 46.1
BOSS_Y = CAVITY_Y / 2 + _diag                  # ≈ 21.2

# Outer shell: main rounded rect at CAVITY + 2·WALL, with 4 corner
# "ears" (circles) at the boss positions. Walls are a flat 2.5 mm
# on the mid-sides; only the corners bump out to house the inserts.
MAIN_EXT_X = CAVITY_X + 2 * WALL               # 93.6
MAIN_EXT_Y = CAVITY_Y + 2 * WALL               # 43.9
BOSS_EAR_R = M2_BOSS_OD / 2 + BOSS_WALL_AROUND  # 3.0

BASE_Z = FLOOR + CAVITY_Z                      # ≈ 29.9

BOSS_LOCS = [(+BOSS_X, +BOSS_Y),
             (+BOSS_X, -BOSS_Y),
             (-BOSS_X, +BOSS_Y),
             (-BOSS_X, -BOSS_Y)]

# ============================================================
# Connector / switch / LED cutouts
# ============================================================

# Cut boxes are centered on the outer wall face, so depth must reach
# from past the outer face through to past the inner cavity face.
# The effective wall thickness here is (EXT - CAVITY)/2 ≈ 4.85 mm
# (set by the corner boss spacing, not the nominal WALL param).
WALL_CUT_DEPTH = 20.0

# --- J7 USB-C on -X wall ---
J7_Y = k2e_y(119.6)                             # ≈ -0.65
J7_CUT_W = 11.0                                 # along Y
J7_CUT_H = 5.0                                  # along Z
J7_Z_CENTER = PCB_Z_BOT - H_USBC / 2            # ≈ 6.85

# --- J3 JST-PH on +X wall ---
J3_Y = k2e_y(130.7)                             # ≈ +10.45
J3_CUT_W = 10.0
J3_CUT_H = 7.0
J3_Z_CENTER = PCB_Z_BOT - H_JSTPH / 2           # ≈ 5.48

# --- J4/J5/J6 JST-SH on +X wall ---
JSH_CUT_W = 7.0
JSH_CUT_H = 4.0
JSH_Z_CENTER = PCB_Z_BOT - H_JSTSH / 2          # ≈ 6.85
JSH_YS = [k2e_y(121.1), k2e_y(113.2), k2e_y(105.3)]  # +0.85, -7.05, -14.95

# --- SW1 slide switch slot on +Y wall ---
# Switch bbox in KiCad: center (120.5, 137.5), size 8.92 × 6.558
# Body extends in enc X = -3.76 … +5.16, Y = +13.97 … +20.53
# (Y reaches 1.08 mm past cavity edge at +19.45 — slot through-cut
# accommodates this.)
SW1_X = k2e_x(120.5)                            # ≈ +0.70
SW1_SLOT_W = 14.0                               # along X (body width + travel)
SW1_SLOT_H = 5.0                                # along Z
SW1_Z_CENTER = PCB_Z_BOT - (H_SW_BODY / 2) + 1.0
# Span roughly Z = 4.6 … 9.6 — covers body + handle region.

# Switch body also overlaps the +Y rail in this X range — rail is
# interrupted locally so the body sits past the cavity edge cleanly.
SW1_RAIL_CUT_W = 12.0

# --- D5 WS2812B LED light hole through floor ---
D5_X = k2e_x(136.458)                           # ≈ +16.66
D5_Y = k2e_y(136.162)                           # ≈ +15.91
LED_HOLE_D = 4.0

# ============================================================
# Build — Base tray
# ============================================================

with BuildPart() as base:

    # Outer shell: main rect + 4 corner ears for screw bosses
    with BuildSketch(Plane.XY):
        RectangleRounded(MAIN_EXT_X, MAIN_EXT_Y, radius=CORNER_R)
        with Locations(BOSS_LOCS):
            Circle(BOSS_EAR_R)
    extrude(amount=BASE_Z)

    # Hollow main cavity (open top, +Z)
    inner_r = max(CORNER_R - WALL, 0.4)
    with BuildSketch(Plane.XY.offset(FLOOR)):
        RectangleRounded(CAVITY_X, CAVITY_Y, radius=inner_r)
    extrude(amount=CAVITY_Z + 1, mode=Mode.SUBTRACT)

    # PCB support rails along ±Y cavity walls, top face at PCB_Z_BOT
    ledge_len = PCB_LENGTH - 4.0
    for y_sign in (+1, -1):
        ly = y_sign * (CAVITY_Y / 2 - PCB_LEDGE_W / 2)
        with BuildSketch(Plane.XY.offset(FLOOR)):
            with Locations([(0, ly)]):
                Rectangle(ledge_len, PCB_LEDGE_W)
        extrude(amount=PCB_RAIL_Z)

    # Notch the +Y rail under the switch so the overhanging switch
    # body can seat past the cavity edge
    with Locations([(SW1_X, CAVITY_Y / 2 - PCB_LEDGE_W / 2,
                     FLOOR + PCB_RAIL_Z / 2)]):
        Box(SW1_RAIL_CUT_W, PCB_LEDGE_W + 0.1, PCB_RAIL_Z + 0.2,
            mode=Mode.SUBTRACT)

    # Screw bosses (solid columns with self-tap / heat-set hole)
    for (bx, by) in BOSS_LOCS:
        with BuildSketch(Plane.XY.offset(FLOOR)):
            with Locations([(bx, by)]):
                Circle(M2_BOSS_OD / 2)
        extrude(amount=CAVITY_Z)
        # Pilot hole for M2 heat-set insert (through full boss height;
        # insert sinks ~4 mm, hole just needs to be ≥ insert depth)
        with BuildSketch(Plane.XY.offset(FLOOR)):
            with Locations([(bx, by)]):
                Circle(M2_INSERT_D / 2)
        extrude(amount=CAVITY_Z, mode=Mode.SUBTRACT)

    # --- J7 USB-C in -X wall ---
    with Locations([(-MAIN_EXT_X / 2, J7_Y, J7_Z_CENTER)]):
        Box(WALL_CUT_DEPTH, J7_CUT_W, J7_CUT_H, mode=Mode.SUBTRACT)

    # --- J3 JST-PH in +X wall ---
    with Locations([(+MAIN_EXT_X / 2, J3_Y, J3_Z_CENTER)]):
        Box(WALL_CUT_DEPTH, J3_CUT_W, J3_CUT_H, mode=Mode.SUBTRACT)

    # --- J4/J5/J6 JST-SH in +X wall ---
    for jy in JSH_YS:
        with Locations([(+MAIN_EXT_X / 2, jy, JSH_Z_CENTER)]):
            Box(WALL_CUT_DEPTH, JSH_CUT_W, JSH_CUT_H, mode=Mode.SUBTRACT)

    # --- SW1 slide switch slot in +Y wall ---
    with Locations([(SW1_X, +MAIN_EXT_Y / 2, SW1_Z_CENTER)]):
        Box(SW1_SLOT_W, WALL_CUT_DEPTH, SW1_SLOT_H, mode=Mode.SUBTRACT)

    # --- D5 WS2812B light hole through floor ---
    with BuildSketch(Plane.XY):
        with Locations([(D5_X, D5_Y)]):
            Circle(LED_HOLE_D / 2)
    extrude(amount=FLOOR + 0.1, mode=Mode.SUBTRACT)

# ============================================================
# Build — Lid
# ============================================================

with BuildPart() as lid:

    # Top plate (matches base outer outline: rect + corner ears)
    with BuildSketch(Plane.XY):
        RectangleRounded(MAIN_EXT_X, MAIN_EXT_Y, radius=CORNER_R)
        with Locations(BOSS_LOCS):
            Circle(BOSS_EAR_R)
    extrude(amount=LID_PLATE)

    # Nesting rim (extends downward into cavity, hollow ring)
    rim_outer_x = CAVITY_X - 2 * LID_RIM_GAP
    rim_outer_y = CAVITY_Y - 2 * LID_RIM_GAP
    rim_inner_x = rim_outer_x - 2 * LID_RIM_WALL
    rim_inner_y = rim_outer_y - 2 * LID_RIM_WALL
    rim_r_outer = max(inner_r - LID_RIM_GAP, 0.3)
    rim_r_inner = max(rim_r_outer - LID_RIM_WALL, 0.2)

    with BuildSketch(Plane.XY):
        RectangleRounded(rim_outer_x, rim_outer_y, radius=rim_r_outer)
        RectangleRounded(rim_inner_x, rim_inner_y, radius=rim_r_inner,
                         mode=Mode.SUBTRACT)
    extrude(amount=-LID_RIM_DEPTH)

    # Screw clearance holes + head counterbores (bosses are outside
    # the cavity, so no rim relief needed)
    for (bx, by) in BOSS_LOCS:
        with BuildSketch(Plane.XY.offset(LID_PLATE / 2)):
            with Locations([(bx, by)]):
                Circle(M2_CLEARANCE_D / 2)
        extrude(amount=LID_PLATE + 2, both=True, mode=Mode.SUBTRACT)

        with BuildSketch(Plane.XY.offset(LID_PLATE)):
            with Locations([(bx, by)]):
                Circle(M2_HEAD_D / 2)
        extrude(amount=-M2_HEAD_DEPTH, mode=Mode.SUBTRACT)

# ============================================================
# Export
# ============================================================

export_stl(base.part, str(OUTPUT_DIR / "enclosure_base.stl"))
export_step(base.part, str(OUTPUT_DIR / "enclosure_base.step"))
export_stl(lid.part,  str(OUTPUT_DIR / "enclosure_lid.stl"))
export_step(lid.part, str(OUTPUT_DIR / "enclosure_lid.step"))

# ============================================================
# Summary
# ============================================================

bb_base = base.part.bounding_box()
bb_lid = lid.part.bounding_box()

print("PCB Enclosure — Motion Play Main Board v7")
print(f"  Main body: {MAIN_EXT_X:.1f} × {MAIN_EXT_Y:.1f} mm (wall = {WALL} mm)")
print(f"  Corner ears at ±({BOSS_X:.1f}, {BOSS_Y:.1f}), ⌀{2*BOSS_EAR_R:.1f} mm")
print(f"  Overall bbox (incl. ears): {bb_base.size.X:.1f} × {bb_base.size.Y:.1f} × {bb_base.size.Z:.1f} mm")
print(f"  Lid bbox:                  {bb_lid.size.X:.1f} × {bb_lid.size.Y:.1f} × {bb_lid.size.Z:.1f} mm")
print(f"  Assembled height: {BASE_Z + LID_PLATE:.1f} mm")
print()
print(f"  Internal cavity: {CAVITY_X:.1f} × {CAVITY_Y:.1f} × {CAVITY_Z:.1f} mm")
print(f"  PCB rail:        Z = {FLOOR:.1f} … {PCB_Z_BOT:.2f} mm  (PCB bottom = {PCB_Z_BOT:.2f})")
print(f"  Battery top:     Z = {PCB_Z_TOP + H_BATTERY:.1f} mm (lid inner at {BASE_Z:.1f})")
print()
print("Cutouts (enc coords):")
print(f"  J7 USB-C  (-X):  Y={J7_Y:+.2f}, {J7_CUT_W}×{J7_CUT_H} mm, Zc={J7_Z_CENTER:.2f}")
print(f"  J3 JST-PH (+X):  Y={J3_Y:+.2f}, {J3_CUT_W}×{J3_CUT_H} mm, Zc={J3_Z_CENTER:.2f}")
for i, jy in enumerate(JSH_YS, start=4):
    print(f"  J{i} JST-SH (+X): Y={jy:+.2f}, {JSH_CUT_W}×{JSH_CUT_H} mm, Zc={JSH_Z_CENTER:.2f}")
print(f"  SW1 slot  (+Y):  X={SW1_X:+.2f}, {SW1_SLOT_W}×{SW1_SLOT_H} mm, Zc={SW1_Z_CENTER:.2f}")
print(f"  D5 LED hole:     (X={D5_X:+.2f}, Y={D5_Y:+.2f}), ⌀{LED_HOLE_D} mm through floor")
print()
print(f"Screw bosses: M2 heat-set at (±{BOSS_X:.1f}, ±{BOSS_Y:.1f})")
print(f"\nExported: STL + STEP for base and lid")

# ============================================================
# Viewer
# ============================================================

if HAS_VIEWER:
    lid_assembly = lid.part.moved(Location((0, 0, BASE_Z + 5)))
    show(base.part, lid_assembly, names=["base", "lid"])

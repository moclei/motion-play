"""
PCB Enclosure — Motion Play Main Board v6

Two-part box: base tray + press-fit lid with display window.
Base holds the 88×40mm PCB on support ledges with connector cutouts
on three walls. The enclosure extends 20mm past the right board edge
to cover the T-Display-S3 module overhang (25mm past board edge,
hand-soldered after JLCPCB assembly).

Coordinate system:
  Origin = center of internal cavity (XY), bottom of enclosure (Z)
  X = along PCB length (88mm), +X = display/right side
  Y = along PCB width (40mm),  +Y = USB-C/LED connector side (KiCad y=101)
  Z = up, Z=0 at enclosure bottom

PCB left edge at X = -56.5 (against -X cavity wall)
PCB right edge at X = +31.5
Display extension from X = +31.5 to X = +56.5

Print: base upside-down (open face on plate), lid face-down.
Material: PLA for test fit, PETG for final.

See: mechanical/FDM_DESIGN_RULES.md
See: mechanical/models/pcb-enclosure/v6-pcb-layout-context.json
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
# PCB and module dimensions
# ============================================================

PCB_LENGTH = 88.0       # X
PCB_WIDTH = 40.0        # Y
PCB_THICKNESS = 1.55

# T-Display-S3 is hand-soldered and overhangs 25mm past the right board edge
DISPLAY_OVERHANG = 25.0

# ============================================================
# FDM design rules (FDM_DESIGN_RULES.md)
# ============================================================

CLEARANCE = 0.2         # per side — snug/sliding fit
WALL = 2.5              # thick wall for rigidity
FLOOR = 1.6
CORNER_R = 2.0          # external corner radius

# ============================================================
# Enclosure geometry
# ============================================================

# Internal cavity
CAVITY_X = PCB_LENGTH + DISPLAY_OVERHANG + 2 * CLEARANCE  # 108.4
CAVITY_Y = PCB_WIDTH + 2 * CLEARANCE                       # 40.4

# PCB support ledges
PCB_RAIL_Z = 3.8        # height above floor — clears T-Display through-hole pins
PCB_LEDGE_W = 1.0       # ledge protrusion from wall into cavity

# Component clearance above PCB top surface
# T-Display-S3 on pin headers ≈ 11mm; 1mm margin
ABOVE_PCB = 12.0

CAVITY_Z = PCB_RAIL_Z + PCB_THICKNESS + ABOVE_PCB  # 16.1

# External dimensions
EXT_X = CAVITY_X + 2 * WALL    # 111.6
EXT_Y = CAVITY_Y + 2 * WALL    # 43.6
BASE_Z = FLOOR + CAVITY_Z       # 17.7

# Lid
LID_PLATE = 1.6
LID_RIM_DEPTH = 3.0            # nesting rim extends down into cavity
LID_RIM_WALL = 1.2             # rim wall thickness (3 perimeters)
LID_RIM_GAP = 0.15             # clearance between rim and cavity wall

# Lid attachment
M2_BOSS_OD = 6.0               # screw boss outer diameter
M2_PILOT_D = 1.7               # self-tapping pilot hole for M2
M2_CLEARANCE_D = 2.4           # through-hole in lid
M2_HEAD_D = 4.2                # pan-head counterbore diameter
M2_HEAD_DEPTH = 1.0            # counterbore depth in lid top
BOSS_INSET_X = 4.5             # boss center inset from right cavity wall
BOSS_INSET_Y = 4.5             # boss center inset from ±Y cavity walls
DETENT_PROTRUSION = 0.4        # snap bump protrusion from left wall
DETENT_WIDTH = 5.0             # bump width (Y direction)
DETENT_HEIGHT = 1.5            # bump height (Z direction)

# ============================================================
# PCB position in enclosure coordinates
# ============================================================

PCB_X_LEFT = -CAVITY_X / 2 + CLEARANCE     # -54.0
PCB_X_RIGHT = PCB_X_LEFT + PCB_LENGTH       # +34.0
PCB_X_CENTER = (PCB_X_LEFT + PCB_X_RIGHT) / 2

PCB_Z_BOT = FLOOR + PCB_RAIL_Z              # 4.1  (bottom of board)
PCB_Z_TOP = PCB_Z_BOT + PCB_THICKNESS       # 5.7  (top of board)

# ============================================================
# Coordinate conversion: KiCad → enclosure
# ============================================================
# Board outline in KiCad: min (76, 101) to max (164, 141)
# Board center in KiCad: (120, 121)
# KiCad Y increases downward; enclosure Y increases upward (+Y = top edge)

KICAD_BOARD_MIN_X = 76.0
KICAD_BOARD_CENTER_Y = 121.0


def kicad_to_enc_x(kx):
    """KiCad X → enclosure X (board-relative offset from left edge)."""
    return (kx - KICAD_BOARD_MIN_X) + PCB_X_LEFT


def kicad_to_enc_y(ky):
    """KiCad Y → enclosure Y (flip direction)."""
    return -(ky - KICAD_BOARD_CENTER_Y)


# ============================================================
# Connector positions and cutout dimensions
# ============================================================

# All cutouts start at PCB bottom level and extend up past the connector
WALL_CUT_DEPTH = WALL * 3  # generous to ensure clean through-cut

# --- J7: USB-C, top edge (+Y wall) ---
# KiCad center (94.256, 106.15), connector body ~3.2mm above PCB
J7_X = kicad_to_enc_x(94.256)              # -35.7
J7_CUTOUT_W = 10.0
J7_CUTOUT_Z_BOT = PCB_Z_TOP
J7_CUTOUT_Z_TOP = PCB_Z_TOP + 4.0          # 9.7

# --- J3: JST-PH 3-pin (LED strip), top edge (+Y wall) ---
# KiCad center (117.25, 105.5), horizontal connector ~6mm tall
J3_X = kicad_to_enc_x(117.25)              # -12.75
J3_CUTOUT_W = 12.0
J3_CUTOUT_Z_BOT = PCB_Z_TOP
J3_CUTOUT_Z_TOP = PCB_Z_TOP + 7.0          # 12.7

# --- J8: JST-PH 2-pin (battery), left edge (-X wall) ---
# KiCad center (80.5, 118.95), rotated -90° → faces left
J8_Y = kicad_to_enc_y(118.95)              # +2.05
J8_CUTOUT_W = 8.0                          # along Y direction
J8_CUTOUT_Z_BOT = PCB_Z_TOP
J8_CUTOUT_Z_TOP = PCB_Z_TOP + 7.0          # 12.7

# --- J4/J5/J6: JST-SH 5-pin × 3 (sensors), bottom edge (-Y wall) ---
# KiCad centers: J4 (116.3, 138.425), J5 (125.5, 138.4), J6 (134.7, 138.4)
# Horizontal connectors ~4mm tall; single wide slot for all three
J4_X = kicad_to_enc_x(116.3)               # -13.7
J6_X = kicad_to_enc_x(134.7)               #  +4.7
SENSOR_EACH_W = 10.0
SENSOR_SLOT_W = (J6_X + SENSOR_EACH_W / 2) - (J4_X - SENSOR_EACH_W / 2)  # 28.4
SENSOR_SLOT_X = (J4_X + J6_X) / 2          # -4.5
SENSOR_CUTOUT_Z_BOT = PCB_Z_TOP
SENSOR_CUTOUT_Z_TOP = PCB_Z_TOP + 5.0      # 10.7

# ============================================================
# Display window — T-Display-S3
# ============================================================

# The T-Display-S3 mounts via 2×12 pin headers spanning KiCad
# x = 134.2–162.2, y = 107.5 and 130.4.  The 1.9" display glass
# is on the right end of the module (toward +X / board right edge).
#
# Active display area ≈ 23mm × 43mm (170×320 px, 1.9" diagonal).
# The window is intentionally oversized for first-print refinement.
# Measure the physical module and adjust these values.
DISPLAY_WIN_X = 23.7       # enclosure X — positioned so 9mm of lid remains on right
DISPLAY_WIN_Y = 2.0        # enclosure Y (roughly centered on module)
DISPLAY_WIN_LEN = 53.0     # X direction — covers display + 25mm overhang
DISPLAY_WIN_WID = 26.0     # Y direction — covers ~23mm active area
DISPLAY_WIN_R = 1.5        # corner radius

# ============================================================
# Build — Base Tray
# ============================================================

with BuildPart() as base:

    # --- Outer shell with rounded corners ---
    with BuildSketch(Plane.XY):
        RectangleRounded(EXT_X, EXT_Y, radius=CORNER_R)
    extrude(amount=BASE_Z)

    # --- Hollow out cavity (open top) ---
    inner_r = max(CORNER_R - WALL, 0.4)
    with BuildSketch(Plane.XY.offset(FLOOR)):
        RectangleRounded(CAVITY_X, CAVITY_Y, radius=inner_r)
    extrude(amount=CAVITY_Z + 1, mode=Mode.SUBTRACT)

    # --- PCB support ledges along ±Y walls ---
    # Ledge spans most of PCB length, stops 2mm short of each end
    ledge_len = PCB_LENGTH - 4.0
    for y_sign in [+1, -1]:
        ly = y_sign * (CAVITY_Y / 2 - PCB_LEDGE_W / 2)
        with BuildSketch(Plane.XY.offset(FLOOR)):
            with Locations([(PCB_X_CENTER, ly)]):
                Rectangle(ledge_len, PCB_LEDGE_W)
        extrude(amount=PCB_RAIL_Z)

    # --- Connector cutouts (subtractive boxes through walls) ---

    # J7 USB-C — +Y wall
    h = J7_CUTOUT_Z_TOP - J7_CUTOUT_Z_BOT
    z_mid = (J7_CUTOUT_Z_BOT + J7_CUTOUT_Z_TOP) / 2
    with Locations([(J7_X, EXT_Y / 2, z_mid)]):
        Box(J7_CUTOUT_W, WALL_CUT_DEPTH, h, mode=Mode.SUBTRACT)

    # J3 LED JST — +Y wall
    h = J3_CUTOUT_Z_TOP - J3_CUTOUT_Z_BOT
    z_mid = (J3_CUTOUT_Z_BOT + J3_CUTOUT_Z_TOP) / 2
    with Locations([(J3_X, EXT_Y / 2, z_mid)]):
        Box(J3_CUTOUT_W, WALL_CUT_DEPTH, h, mode=Mode.SUBTRACT)

    # J8 Battery JST — -X wall
    h = J8_CUTOUT_Z_TOP - J8_CUTOUT_Z_BOT
    z_mid = (J8_CUTOUT_Z_BOT + J8_CUTOUT_Z_TOP) / 2
    with Locations([(-EXT_X / 2, J8_Y, z_mid)]):
        Box(WALL_CUT_DEPTH, J8_CUTOUT_W, h, mode=Mode.SUBTRACT)

    # J4/J5/J6 Sensors — -Y wall (single wide slot)
    h = SENSOR_CUTOUT_Z_TOP - SENSOR_CUTOUT_Z_BOT
    z_mid = (SENSOR_CUTOUT_Z_BOT + SENSOR_CUTOUT_Z_TOP) / 2
    with Locations([(SENSOR_SLOT_X, -EXT_Y / 2, z_mid)]):
        Box(SENSOR_SLOT_W, WALL_CUT_DEPTH, h, mode=Mode.SUBTRACT)

    # --- M2 screw bosses in display extension area (right side) ---
    boss_x = CAVITY_X / 2 - BOSS_INSET_X
    boss_y_pos = CAVITY_Y / 2 - BOSS_INSET_Y
    # Shift each boss an extra half-diameter toward its respective corner
    # to clear the T-Display-S3 module
    screw_boss_locs = [(boss_x, +boss_y_pos + M2_BOSS_OD / 2),
                       (boss_x, -boss_y_pos - M2_BOSS_OD / 2)]

    for (bx, by) in screw_boss_locs:
        # Solid boss from floor to wall top
        with BuildSketch(Plane.XY.offset(FLOOR)):
            with Locations([(bx, by)]):
                Circle(M2_BOSS_OD / 2)
        extrude(amount=CAVITY_Z)
        # Self-tap pilot hole
        with BuildSketch(Plane.XY.offset(FLOOR)):
            with Locations([(bx, by)]):
                Circle(M2_PILOT_D / 2)
        extrude(amount=CAVITY_Z, mode=Mode.SUBTRACT)

    # --- Snap detent bumps on left wall interior ---
    # Small protrusions near the top of the -X wall that the lid rim
    # clicks past.  The ramped lower face (wedge) eases insertion.
    detent_x = -CAVITY_X / 2 + DETENT_PROTRUSION / 2
    detent_z = FLOOR + CAVITY_Z - DETENT_HEIGHT - 0.3  # near wall top

    for dy in [+10.0, -10.0]:
        # Rectangular bump
        with Locations([(detent_x, dy,
                         detent_z + DETENT_HEIGHT / 2)]):
            Box(DETENT_PROTRUSION, DETENT_WIDTH, DETENT_HEIGHT)

# ============================================================
# Build — Lid
# ============================================================

with BuildPart() as lid:

    # --- Top plate ---
    with BuildSketch(Plane.XY):
        RectangleRounded(EXT_X, EXT_Y, radius=CORNER_R)
    extrude(amount=LID_PLATE)

    # --- Nesting rim (extends downward into base cavity) ---
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

    # --- Display window cutout (through plate + rim) ---
    with BuildSketch(Plane.XY.offset(LID_PLATE / 2)):
        with Locations([(DISPLAY_WIN_X, DISPLAY_WIN_Y)]):
            RectangleRounded(DISPLAY_WIN_LEN, DISPLAY_WIN_WID,
                             radius=DISPLAY_WIN_R)
    extrude(amount=LID_PLATE + LID_RIM_DEPTH + 2, both=True,
            mode=Mode.SUBTRACT)

    # --- M2 screw clearance holes + counterbores + rim relief ---
    rim_relief_d = M2_BOSS_OD + 2 * CLEARANCE  # clear the boss with margin
    for (bx, by) in screw_boss_locs:
        # Cut rim away around the boss so it doesn't clash
        with Locations([(bx, by, -LID_RIM_DEPTH / 2)]):
            Box(rim_relief_d, rim_relief_d, LID_RIM_DEPTH + 1,
                mode=Mode.SUBTRACT)
        # Clearance hole through plate
        with BuildSketch(Plane.XY.offset(LID_PLATE / 2)):
            with Locations([(bx, by)]):
                Circle(M2_CLEARANCE_D / 2)
        extrude(amount=LID_PLATE + 2, both=True,
                mode=Mode.SUBTRACT)
        # Counterbore on top face for screw head
        with BuildSketch(Plane.XY.offset(LID_PLATE)):
            with Locations([(bx, by)]):
                Circle(M2_HEAD_D / 2)
        extrude(amount=-M2_HEAD_DEPTH, mode=Mode.SUBTRACT)

# ============================================================
# Export
# ============================================================

export_stl(base.part, str(OUTPUT_DIR / "enclosure_base.stl"))
export_step(base.part, str(OUTPUT_DIR / "enclosure_base.step"))
export_stl(lid.part, str(OUTPUT_DIR / "enclosure_lid.stl"))
export_step(lid.part, str(OUTPUT_DIR / "enclosure_lid.step"))

# ============================================================
# Summary
# ============================================================

bb_base = base.part.bounding_box()
bb_lid = lid.part.bounding_box()

print("PCB Enclosure — Motion Play Main Board v6")
print(f"  Base:  {bb_base.size.X:.1f} × {bb_base.size.Y:.1f} × {bb_base.size.Z:.1f} mm")
print(f"  Lid:   {bb_lid.size.X:.1f} × {bb_lid.size.Y:.1f} × {bb_lid.size.Z:.1f} mm")
print(f"  Assembled height: {BASE_Z + LID_PLATE:.1f} mm")
print()
print(f"  Internal cavity: {CAVITY_X:.1f} × {CAVITY_Y:.1f} × {CAVITY_Z:.1f} mm")
print(f"  Wall: {WALL} mm  |  Floor: {FLOOR} mm")
print(f"  PCB rail height: {PCB_RAIL_Z} mm  |  PCB at Z = {PCB_Z_BOT:.1f}–{PCB_Z_TOP:.1f} mm")
print()
print("Connector cutouts:")
print(f"  J7 USB-C    (+Y wall): X={J7_X:+.1f}, {J7_CUTOUT_W}×{J7_CUTOUT_Z_TOP - J7_CUTOUT_Z_BOT:.1f} mm")
print(f"  J3 LED JST  (+Y wall): X={J3_X:+.1f}, {J3_CUTOUT_W}×{J3_CUTOUT_Z_TOP - J3_CUTOUT_Z_BOT:.1f} mm")
print(f"  J8 Bat JST  (-X wall): Y={J8_Y:+.1f}, {J8_CUTOUT_W}×{J8_CUTOUT_Z_TOP - J8_CUTOUT_Z_BOT:.1f} mm")
print(f"  J4-J6 Sensors (-Y wall): X={SENSOR_SLOT_X:+.1f}, {SENSOR_SLOT_W:.1f}×{SENSOR_CUTOUT_Z_TOP - SENSOR_CUTOUT_Z_BOT:.1f} mm")
print()
print(f"Display window: {DISPLAY_WIN_LEN}×{DISPLAY_WIN_WID} mm at ({DISPLAY_WIN_X}, {DISPLAY_WIN_Y})")
print(f"\nExported: STL + STEP for base and lid")

# ============================================================
# Viewer — assembly with PCB STEP model
# ============================================================

if HAS_VIEWER:
    parts = [base.part]
    names = ["base"]

    # Load PCB STEP model (kept outside repo — too large for git)
    PCB_STEP_PATH = Path.home() / "Downloads" / "motion-play-v6.step"
    if PCB_STEP_PATH.exists():
        pcb_import = import_step(str(PCB_STEP_PATH))
        bb_pcb = pcb_import.bounding_box()
        print(f"\nPCB STEP bounding box:")
        print(f"  X: {bb_pcb.min.X:.2f} → {bb_pcb.max.X:.2f}  ({bb_pcb.size.X:.1f} mm)")
        print(f"  Y: {bb_pcb.min.Y:.2f} → {bb_pcb.max.Y:.2f}  ({bb_pcb.size.Y:.1f} mm)")
        print(f"  Z: {bb_pcb.min.Z:.2f} → {bb_pcb.max.Z:.2f}  ({bb_pcb.size.Z:.1f} mm)")

        # KiCad STEP export: X preserved, Y negated, board bottom at Z≈0.
        # Board outline in KiCad: (76, 101)–(164, 141)
        # → STEP board center: (120, -121, ~0)
        # Target in enclosure coords: (PCB_X_CENTER, 0, PCB_Z_BOT)
        KICAD_CENTER_X = (76 + 164) / 2     # 120
        KICAD_CENTER_Y_STEP = -KICAD_BOARD_CENTER_Y  # -121 (Y flipped in STEP)

        dx = PCB_X_CENTER - KICAD_CENTER_X
        dy = 0 - KICAD_CENTER_Y_STEP
        dz = PCB_Z_BOT - bb_pcb.min.Z       # align board bottom to rail top

        pcb_positioned = pcb_import.moved(Location((dx, dy, dz)))
        parts.append(pcb_positioned)
        names.append("pcb")
        print(f"  Translated by ({dx:.1f}, {dy:.1f}, {dz:.1f})")
    else:
        print(f"\nPCB STEP not found at {PCB_STEP_PATH} — showing enclosure only")

    # Lid raised above base for visual clearance
    lid_assembly = lid.part.moved(Location((0, 0, BASE_Z + 5)))
    parts.append(lid_assembly)
    names.append("lid")

    show(*parts, names=names)

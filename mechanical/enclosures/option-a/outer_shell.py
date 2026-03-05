"""
Wrap-Around Tray — Motion Play Sensor Enclosure (Option A)

Outer shell of the two-piece enclosure. A C-shaped channel that slides
over the hoop bar, housing the rigid PCB on the outer face.

Upper section (+Z): PCB cavity with connector exit slots
Lower section (-Z): wrap-around walls on -X and +X edges extending
  past the bar's thin edges, with end walls closing -Y and +Y faces.
  Bar notches in the end walls allow the tray to seat over the hoop.

The -X wrap-around wall is thicker than +X to shield the flex PCB's
180° bend from impact. The FPC passthrough is sized so that the outer
portion of the thickened wall remains intact, forming a retained shell
over the bend zone while preserving internal routing space.

The inner shell screws into the tray from the inner face side.
3× M2.5 heat-set insert bosses in a triangular pattern. The -X boss
is offset in Y to clear the FPC passthrough channel.

Print orientation: UPSIDE DOWN — inner face opening on build plate.

Coordinate convention:
  X = across bar width, Y = along hoop, Z = +Z away from bar (outer face)
  Z = 0 at bar's outer-face contact surface
  Bar occupies Z = 0 to Z = -BAR_THICKNESS (-4mm)
  Inner face at Z = -BAR_THICKNESS

See: mechanical/specs/assembly-v0.1.yaml
See: mechanical/FDM_DESIGN_RULES.md
"""

from build123d import *
import math
from pathlib import Path

try:
    from ocp_vscode import show, set_port
    set_port(3939)
    HAS_VIEWER = True
except ImportError:
    HAS_VIEWER = False

OUTPUT_DIR = Path(__file__).parent

# ============================================================
# Spec dimensions
# ============================================================

BAR_WIDTH = 25.25
BAR_THICKNESS = 4.0

PCB_X = 22.6
PCB_Y = 28.5
PCB_THICKNESS = 1.6
PCB_TALLEST_COMPONENT = 3.25
PCB_TOTAL_HEIGHT = PCB_THICKNESS + PCB_TALLEST_COMPONENT

FLEX_PCB_WIDTH = 10.0

JST_HOUSING_W = 7.0
JST_HOUSING_H = 3.25
JST_CENTER_FROM_WEST = 15.5
JST_X_OFFSET = -PCB_X / 2 + JST_CENTER_FROM_WEST

FPC_HOUSING_W = 15.0
FPC_HOUSING_H = 2.75
FPC_CENTER_Y = PCB_Y / 2 - FPC_HOUSING_W / 2  # +6.75 mm

# ============================================================
# Design parameters
# ============================================================

BASE_THICKNESS = 2.0
SIDE_EXTENSION = 8.0       # mm past bar edge each side (accommodates wrap walls + bosses)

PCB_CLEARANCE_X = 0.25
PCB_CLEARANCE_Y = 0.5
HEADROOM = 1.5
LID_THICKNESS = 2.0
LID_FLANGE_X = 3.0         # mm — lid overhang past cavity on each X side (for screw holes)
LID_FLANGE_Y = 1.0         # mm — lid overhang past cavity on each Y side

# M2 lid screws — 2 diagonal fasteners on X cavity wall tops
LID_INSERT_DIAM = 3.2      # mm — M2 heat-set insert hole (per FDM_DESIGN_RULES)
LID_INSERT_DEPTH = 4.0     # mm — insert length + 0.5mm overflow
LID_CLEARANCE_DIAM = 2.4   # mm — M2 clearance hole through lid
LID_SCREW_OFFSET_X = 1.5   # mm — hole center distance from cavity inner edge

CABLE_SLOT_WIDTH = JST_HOUSING_W + 1.5
CABLE_SLOT_HEIGHT = JST_HOUSING_H + 1.0
FPC_SLOT_WIDTH = FLEX_PCB_WIDTH + 2.0
FPC_SLOT_HEIGHT = FPC_HOUSING_H + 1.0

# Wrap-around walls
WRAP_WALL = 2.0            # mm — wall thickness (X direction)
WRAP_DEPTH = BAR_THICKNESS + 2.5  # 6.5mm below Z=0 (bar + inner shell seat)
BEND_GUARD_EXTRA = 3.0     # mm — extra -X wall thickness to shield flex bend

# M2.5 screw bosses (see FDM_DESIGN_RULES.md for fastener specs)
BOSS_DIAM = 7.0            # mm — outer diameter of boss cylinder
BOSS_HEIGHT = 6.0          # mm — boss extends from wrap bottom
INSERT_DIAM = 3.6          # mm — M2.5 heat-set insert hole
INSERT_DEPTH = 4.5         # mm

# ============================================================
# Computed
# ============================================================

SHELL_WIDTH = BAR_WIDTH + 2 * SIDE_EXTENSION     # 41.25 mm
SHELL_LENGTH = 34.0

INTERIOR_X = PCB_X + 2 * PCB_CLEARANCE_X         # 23.1 mm
INTERIOR_Y = PCB_Y + 2 * PCB_CLEARANCE_Y         # 29.5 mm
WALL_X = (SHELL_WIDTH - INTERIOR_X) / 2          # 9.075 mm
WALL_Y = (SHELL_LENGTH - INTERIOR_Y) / 2         # 2.25 mm
CAVITY_DEPTH = PCB_TOTAL_HEIGHT + HEADROOM        # 6.35 mm

# Wrap wall centers
wrap_wall_z_size = BASE_THICKNESS + WRAP_DEPTH    # 8.5 mm total
wrap_wall_z_center = (BASE_THICKNESS - WRAP_DEPTH) / 2  # -2.25 mm

# -X wall is thicker to shield the flex bend from external impact.
# It extends from the cavity top to the wrap bottom (taller than +X),
# fully enclosing the FPC passthrough from the exterior. The passthrough
# cuts partway in but leaves a retained outer shell (~2.5mm).
NEG_X_WALL = WRAP_WALL + BEND_GUARD_EXTRA              # 5.0mm total
neg_x_wall_outer = -SHELL_WIDTH / 2 - BEND_GUARD_EXTRA # -23.625mm
neg_x_wall_z_top = BASE_THICKNESS + CAVITY_DEPTH       # +8.35mm (cavity top)
neg_x_wall_z_bot = -WRAP_DEPTH                         # -6.5mm (wrap bottom)
neg_x_wall_z_size = neg_x_wall_z_top - neg_x_wall_z_bot   # 14.85mm
neg_x_wall_z_center = (neg_x_wall_z_top + neg_x_wall_z_bot) / 2  # +0.925mm

# Boss X positions (inward from wrap wall, 0.5mm overlap for solid union)
boss_x_neg = -SHELL_WIDTH / 2 + WRAP_WALL + BOSS_DIAM / 2 - 0.5
boss_x_pos = SHELL_WIDTH / 2 - WRAP_WALL - BOSS_DIAM / 2 + 0.5
boss_z_center = -BAR_THICKNESS + BOSS_HEIGHT / 2

# 3× M2.5 triangular pattern — -X boss offset in Y to clear FPC channel
BOSS_POSITIONS = [
    (boss_x_pos, +10.0),    # +X wall, toward +Y
    (boss_x_pos, -10.0),    # +X wall, toward -Y
    (boss_x_neg,  -6.0),    # -X wall, clear of FPC passthrough
]

# ============================================================
# Build — Tray
# ============================================================

with BuildPart() as tray:

    # 1. Base plate
    with BuildSketch(Plane.XY):
        Rectangle(SHELL_WIDTH, SHELL_LENGTH)
    extrude(amount=BASE_THICKNESS)

    # 2. PCB cavity walls (above base plate, +Z direction)
    with BuildSketch(Plane.XY.offset(BASE_THICKNESS)):
        Rectangle(SHELL_WIDTH, SHELL_LENGTH)
        Rectangle(INTERIOR_X, INTERIOR_Y, mode=Mode.SUBTRACT)
    extrude(amount=CAVITY_DEPTH)

    # 3. Wrap-around walls (-X and +X, extending from base plate downward)
    #    -X wall is thicker to enclose the flex bend zone.
    neg_x_wall_x = neg_x_wall_outer + NEG_X_WALL / 2
    with Locations([(neg_x_wall_x, 0, neg_x_wall_z_center)]):
        Box(NEG_X_WALL, SHELL_LENGTH, neg_x_wall_z_size)
    with Locations([(SHELL_WIDTH / 2 - WRAP_WALL / 2, 0, wrap_wall_z_center)]):
        Box(WRAP_WALL, SHELL_LENGTH, wrap_wall_z_size)

    # 4. Screw bosses — 3× M2.5 in triangular pattern.
    #    Protrude inward from wrap walls. Accept heat-set inserts
    #    opening at the bottom face (-Z) for inner shell attachment.
    for (bx, by) in BOSS_POSITIONS:
        with Locations([(bx, by, boss_z_center)]):
            Cylinder(BOSS_DIAM / 2, BOSS_HEIGHT)

    # 5. Insert holes (subtracted from bosses)
    insert_hole_z = -BAR_THICKNESS + INSERT_DEPTH / 2 - 0.5
    for (bx, by) in BOSS_POSITIONS:
        with Locations([(bx, by, insert_hole_z)]):
            Cylinder(INSERT_DIAM / 2, INSERT_DEPTH + 1, mode=Mode.SUBTRACT)

    # 6. JST-SH cable slot (in -Y cavity wall, same position as before)
    cable_slot_z = BASE_THICKNESS + PCB_THICKNESS + CABLE_SLOT_HEIGHT / 2
    with Locations([(JST_X_OFFSET, -SHELL_LENGTH / 2, cable_slot_z)]):
        Box(CABLE_SLOT_WIDTH, WALL_Y * 2 + 1, CABLE_SLOT_HEIGHT, mode=Mode.SUBTRACT)

    # 7. FPC flex passthrough — continuous slot from PCB cavity through
    #    the base plate and into the bend channel below. The flex exits
    #    the FPC connector, drops through this slot, and curves around
    #    the bar's -X thin edge inside the wrap-around wall.
    fpc_pass_top = BASE_THICKNESS + FPC_SLOT_HEIGHT
    fpc_pass_bot = -WRAP_DEPTH - 1
    fpc_pass_height = fpc_pass_top - fpc_pass_bot
    fpc_pass_z = (fpc_pass_top + fpc_pass_bot) / 2
    fpc_pass_width = WALL_X + 1
    fpc_pass_x = -SHELL_WIDTH / 2 + fpc_pass_width / 2 - 0.5
    with Locations([(fpc_pass_x, FPC_CENTER_Y, fpc_pass_z)]):
        Box(fpc_pass_width, FPC_SLOT_WIDTH, fpc_pass_height, mode=Mode.SUBTRACT)

    # 8. Bar clearance — trim any boss material that protrudes into the
    #    bar zone. Creates a flat D-shaped face on each boss rather than
    #    moving the boss outward (which would thin the inner shell screw edge).
    bar_clear = 0.3
    with Locations([(0, 0, -BAR_THICKNESS / 2)]):
        Box(BAR_WIDTH + 2 * bar_clear, SHELL_LENGTH + 2, BAR_THICKNESS,
            mode=Mode.SUBTRACT)

    # 9. End walls — close -Y and +Y faces of the wrap section.
    #    Extended on -X side to close the thicker bend-guard wall.
    #    Terminate at Z = -BAR_THICKNESS (bar inner face) so they don't
    #    collide with the inner shell base plate below.
    #    Bar notches allow the tray to seat over the continuous hoop.
    end_wall_z_size = BASE_THICKNESS + BAR_THICKNESS
    end_wall_z_center = (BASE_THICKNESS - BAR_THICKNESS) / 2
    end_wall_x_size = SHELL_WIDTH + BEND_GUARD_EXTRA
    for y_sign in (-1, +1):
        wall_y = y_sign * (SHELL_LENGTH / 2 - WRAP_WALL / 2)
        with Locations([(-BEND_GUARD_EXTRA / 2, wall_y, end_wall_z_center)]):
            Box(end_wall_x_size, WRAP_WALL, end_wall_z_size)
        with Locations([(0, wall_y, -BAR_THICKNESS / 2)]):
            Box(BAR_WIDTH + 0.5, WRAP_WALL + 2, BAR_THICKNESS + 0.5,
                mode=Mode.SUBTRACT)

    # 10. M2 lid screw holes — 2 diagonal heat-set insert bores in X wall tops.
    #     Holes go down from the wall top into the thick X walls.
    #     Diagonal placement prevents rotation with only 2 fasteners.
    lid_screw_x = INTERIOR_X / 2 + LID_SCREW_OFFSET_X
    lid_screw_z_top = BASE_THICKNESS + CAVITY_DEPTH
    lid_screw_z_center = lid_screw_z_top - LID_INSERT_DEPTH / 2
    LID_SCREW_POSITIONS = [
        (+lid_screw_x, +12.0),   # +X wall, +Y corner
        (-lid_screw_x, -12.0),   # -X wall, -Y corner
    ]
    for (sx, sy) in LID_SCREW_POSITIONS:
        with Locations([(sx, sy, lid_screw_z_center)]):
            Cylinder(LID_INSERT_DIAM / 2, LID_INSERT_DEPTH, mode=Mode.SUBTRACT)

# ============================================================
# Build — Lid
# ============================================================
# Covers the cavity opening with a small flange to reach the screw holes
# on the X walls. Two diagonal M2 screws hold it down.
# Print orientation: flat (bottom face on build plate).

lid_plate_x = INTERIOR_X + 2 * LID_FLANGE_X
lid_plate_y = INTERIOR_Y + 2 * LID_FLANGE_Y

with BuildPart() as lid:
    with BuildSketch(Plane.XY):
        Rectangle(lid_plate_x, lid_plate_y)
    extrude(amount=LID_THICKNESS)

    for (sx, sy) in LID_SCREW_POSITIONS:
        with Locations([(sx, sy, LID_THICKNESS / 2)]):
            Cylinder(LID_CLEARANCE_DIAM / 2, LID_THICKNESS + 1, mode=Mode.SUBTRACT)

# ============================================================
# Reference bar (for visualization — not exported)
# ============================================================

with BuildPart() as ref_bar:
    with Locations([(0, 0, -BAR_THICKNESS / 2)]):
        Box(BAR_WIDTH, SHELL_LENGTH + 20, BAR_THICKNESS)

# ============================================================
# Export
# ============================================================

export_stl(tray.part, str(OUTPUT_DIR / "outer_tray.stl"))
export_step(tray.part, str(OUTPUT_DIR / "outer_tray.step"))
export_stl(lid.part, str(OUTPUT_DIR / "outer_lid.stl"))
export_step(lid.part, str(OUTPUT_DIR / "outer_lid.step"))

bb = tray.part.bounding_box()
print("Wrap-around tray built")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print(f"  Volume: {tray.part.volume:.1f} mm³")
print(f"  Shell: {SHELL_WIDTH:.1f} x {SHELL_LENGTH:.1f} mm (+{BEND_GUARD_EXTRA:.0f}mm on -X for bend guard)")
print(f"  Wrap depth: {WRAP_DEPTH:.1f} mm below base plate")
print(f"  Fasteners: 3× M2.5 (boss Ø{BOSS_DIAM:.0f}, insert Ø{INSERT_DIAM:.1f})")
for i, (bx, by) in enumerate(BOSS_POSITIONS):
    print(f"  Boss {i+1}: ({bx:+.1f}, {by:+.1f}) mm")
print(f"  FPC passthrough at Y = {FPC_CENTER_Y:+.1f} mm")
print(f"  Bend guard: -X wall {NEG_X_WALL:.0f}mm (vs {WRAP_WALL:.0f}mm on +X), {BEND_GUARD_EXTRA - 0.5:.1f}mm retained over bend")

lid_bb = lid.part.bounding_box()
print(f"\nLid built")
print(f"  Plate: {lid_plate_x:.1f} x {lid_plate_y:.1f} x {LID_THICKNESS:.0f} mm")
print(f"  Lid screws: 2× M2 diagonal (insert Ø{LID_INSERT_DIAM:.1f}, clearance Ø{LID_CLEARANCE_DIAM:.1f})")
for i, (sx, sy) in enumerate(LID_SCREW_POSITIONS):
    print(f"  Screw {i+1}: ({sx:+.1f}, {sy:+.1f}) mm")

if HAS_VIEWER:
    show(tray, ref_bar, names=["wrap_tray", "bar_reference"])

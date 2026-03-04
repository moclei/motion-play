"""
Wrap-Around Tray Concept — Motion Play Sensor Enclosure (Option A)

CONCEPT MODEL for visual evaluation. The outer shell evolves from a flat
tray into a C-shaped channel that wraps around the bar's thin edges.

Upper section (+Z): PCB cavity with connector exit slots (same as before)
Lower section (-Z): wrap-around walls on -X and +X edges that extend
  past the bar's thin edges to the inner face level.

The -X wrap-around wall forms the bend channel for the flex PCB.
The inner shell (unchanged) screws into the inner face opening.
M2 screw bosses on each wrap-around wall accept heat-set inserts.

Print orientation: UPSIDE DOWN — inner face opening on build plate.
The tray slides onto the hoop bar like a C-channel.

Coordinate convention:
  X = across bar width, Y = along hoop, Z = +Z away from bar (outer face)
  Z = 0 at bar's outer-face contact surface
  Bar occupies Z = 0 to Z = -BAR_THICKNESS (-4mm)
  Inner face at Z = -BAR_THICKNESS

See: docs/explorations/sensor-enclosure.md
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

CABLE_SLOT_WIDTH = JST_HOUSING_W + 1.5
CABLE_SLOT_HEIGHT = JST_HOUSING_H + 1.0
FPC_SLOT_WIDTH = FLEX_PCB_WIDTH + 2.0
FPC_SLOT_HEIGHT = FPC_HOUSING_H + 1.0

# Wrap-around walls
WRAP_WALL = 2.0            # mm — wall thickness (X direction)
WRAP_DEPTH = BAR_THICKNESS + 2.5  # 6.5mm below Z=0 (bar + inner shell seat)

# M2 screw bosses
BOSS_DIAM = 5.0            # mm — outer diameter of boss cylinder
BOSS_HEIGHT = 6.0          # mm — boss extends upward from wrap bottom
INSERT_DIAM = 3.2          # mm — M2 heat-set insert hole
INSERT_DEPTH = 4.0         # mm

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

# Boss positions: inward from wall, 0.5mm overlap for solid union
boss_x_neg = -SHELL_WIDTH / 2 + WRAP_WALL + BOSS_DIAM / 2 - 0.5
boss_x_pos = SHELL_WIDTH / 2 - WRAP_WALL - BOSS_DIAM / 2 + 0.5
boss_z_center = -WRAP_DEPTH + BOSS_HEIGHT / 2

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
    with Locations([(-SHELL_WIDTH / 2 + WRAP_WALL / 2, 0, wrap_wall_z_center)]):
        Box(WRAP_WALL, SHELL_LENGTH, wrap_wall_z_size)
    with Locations([(SHELL_WIDTH / 2 - WRAP_WALL / 2, 0, wrap_wall_z_center)]):
        Box(WRAP_WALL, SHELL_LENGTH, wrap_wall_z_size)

    # 4. Screw bosses — protrude inward from wrap walls near the bottom.
    #    These accept M2 heat-set inserts. The insert opens at the bottom
    #    face (-Z), aligned with the inner shell screw holes.
    with Locations([(boss_x_neg, 0, boss_z_center)]):
        Cylinder(BOSS_DIAM / 2, BOSS_HEIGHT)
    with Locations([(boss_x_pos, 0, boss_z_center)]):
        Cylinder(BOSS_DIAM / 2, BOSS_HEIGHT)

    # 5. Insert holes (subtracted from bosses)
    insert_hole_z = -WRAP_DEPTH + INSERT_DEPTH / 2 - 0.5
    with Locations([(boss_x_neg, 0, insert_hole_z)]):
        Cylinder(INSERT_DIAM / 2, INSERT_DEPTH + 1, mode=Mode.SUBTRACT)
    with Locations([(boss_x_pos, 0, insert_hole_z)]):
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

# ============================================================
# Build — Lid (unchanged)
# ============================================================

with BuildPart() as lid:
    with BuildSketch(Plane.XY):
        Rectangle(SHELL_WIDTH, SHELL_LENGTH)
    extrude(amount=LID_THICKNESS)

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
print("Wrap-around tray concept built")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print(f"  Volume: {tray.part.volume:.1f} mm³")
print(f"  Shell width: {SHELL_WIDTH:.1f} mm (bar + {SIDE_EXTENSION:.0f}mm each side)")
print(f"  Wrap depth: {WRAP_DEPTH:.1f} mm below base plate")
print(f"  Bend channel clearance: {SIDE_EXTENSION - WRAP_WALL:.0f} mm from bar edge to wall")
print(f"  Boss X: {boss_x_neg:.1f} / {boss_x_pos:+.1f} mm")
print(f"  Boss Z center: {boss_z_center:.1f} mm")
print(f"  FPC passthrough at Y = {FPC_CENTER_Y:+.1f} mm")

if HAS_VIEWER:
    show(tray, ref_bar, names=["wrap_tray", "bar_reference"])

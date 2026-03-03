"""
Outer Shell (tray + lid) — Motion Play Sensor Enclosure (Option A)

Sits on the outer face of the hoop bar, housing the rigid sensor PCB.
The tray holds the PCB; the lid covers it. Zip ties hold both shells
together and to the bar.

Two pieces exported:
  - outer_tray.stl/step — open-top box with PCB cavity and connector slots
  - outer_lid.stl/step  — flat plate that sits on the tray, held by zip ties

Print orientation: base plate flat on build plate for both pieces.
Material recommendation: PETG for impact toughness.

See: docs/explorations/sensor-enclosure.md
See: mechanical/specs/assembly-v0.1.yaml
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
# Spec dimensions (from assembly-v0.1.yaml)
# ============================================================

BAR_WIDTH = 25.25           # mm — flat face width
BAR_THICKNESS = 4.0         # mm — thin edge

# Rigid PCB — component-side-up, bare underside rests on base plate
# Looking from above: FPC on west (-X), JST-SH on south (-Y)
PCB_X = 22.6                # mm across bar — south edge length
PCB_Y = 28.5                # mm along hoop — west edge length
PCB_THICKNESS = 1.6         # mm
PCB_TALLEST_COMPONENT = 3.25 # mm — JST-SH right-angle connector housing
PCB_TOTAL_HEIGHT = PCB_THICKNESS + PCB_TALLEST_COMPONENT  # 4.85 mm

FLEX_PCB_WIDTH = 10.0       # mm

# JST-SH connector — on south edge (-Y wall), right-angle female
# 15.5mm from SW corner to center, ~6.5mm from center to SE corner
JST_HOUSING_W = 7.0         # mm wide (along south edge, X direction)
JST_HOUSING_H = 3.25        # mm tall (Z, above PCB surface)
JST_CENTER_FROM_WEST = 15.5 # mm from west end of south edge to connector center
JST_X_OFFSET = -PCB_X / 2 + JST_CENTER_FROM_WEST  # +4.2 mm from PCB center

# FPC connector — on west edge (-X wall), aligned with NW corner
# Housing: 15mm along west edge x 2.75mm tall
# Flex PCB (10mm) centered within the 15mm housing
FPC_HOUSING_W = 15.0        # mm along west edge (Y direction)
FPC_HOUSING_H = 2.75        # mm tall (Z, above PCB surface)
FPC_CENTER_Y = PCB_Y / 2 - FPC_HOUSING_W / 2  # +6.75 mm from PCB center

# ============================================================
# Design parameters
# ============================================================

BASE_THICKNESS = 2.0        # mm — flat plate against hoop bar
SIDE_EXTENSION = 3.0        # mm — extend beyond bar edge (match inner shell)

PCB_CLEARANCE_X = 0.25      # mm per side
PCB_CLEARANCE_Y = 0.5       # mm per side (slightly more for FDM tolerance)
HEADROOM = 1.5              # mm above tallest component

LID_THICKNESS = 2.0         # mm

# Connector exit slots — sized to the housing + clearance
CABLE_SLOT_WIDTH = JST_HOUSING_W + 1.5   # 8.5 mm (X) — housing + clearance
CABLE_SLOT_HEIGHT = JST_HOUSING_H + 1.0  # 4.25 mm (Z)
FPC_SLOT_WIDTH = FLEX_PCB_WIDTH + 2.0    # 12 mm (Y) — flex PCB + clearance
FPC_SLOT_HEIGHT = FPC_HOUSING_H + 1.0    # 3.75 mm (Z)

# ============================================================
# Computed
# ============================================================

SHELL_WIDTH = BAR_WIDTH + 2 * SIDE_EXTENSION     # 31.25 mm (X)
SHELL_LENGTH = 34.0                                # mm (Y) — matches inner shell

INTERIOR_X = PCB_X + 2 * PCB_CLEARANCE_X          # 23.1 mm
INTERIOR_Y = PCB_Y + 2 * PCB_CLEARANCE_Y          # 29.5 mm

WALL_X = (SHELL_WIDTH - INTERIOR_X) / 2           # 4.075 mm
WALL_Y = (SHELL_LENGTH - INTERIOR_Y) / 2          # 2.25 mm

CAVITY_DEPTH = PCB_TOTAL_HEIGHT + HEADROOM         # 6.35 mm
WALL_HEIGHT = CAVITY_DEPTH

TOTAL_HEIGHT = BASE_THICKNESS + WALL_HEIGHT + LID_THICKNESS  # 10.1 mm

# ============================================================
# Build — Tray
# ============================================================
# Coordinate convention (same as inner shell):
#   X = across bar width, Y = along hoop, Z = +Z away from bar
#   Origin at center of base plate, bar-contact surface at Z=0

with BuildPart() as tray:

    # 1. Base plate
    with BuildSketch(Plane.XY):
        Rectangle(SHELL_WIDTH, SHELL_LENGTH)
    extrude(amount=BASE_THICKNESS)

    # 2. Walls — extruded frame
    with BuildSketch(Plane.XY.offset(BASE_THICKNESS)):
        Rectangle(SHELL_WIDTH, SHELL_LENGTH)
        Rectangle(INTERIOR_X, INTERIOR_Y, mode=Mode.SUBTRACT)
    extrude(amount=WALL_HEIGHT)

    # 3. JST-SH cable exit slot — in the -Y wall, offset +4.2mm in X.
    #    Connector center is 15.5mm from the SW corner of the PCB.
    cable_slot_z = BASE_THICKNESS + PCB_THICKNESS + CABLE_SLOT_HEIGHT / 2
    with Locations([(JST_X_OFFSET, -SHELL_LENGTH / 2, cable_slot_z)]):
        Box(
            CABLE_SLOT_WIDTH,
            WALL_Y * 2 + 1,
            CABLE_SLOT_HEIGHT,
            mode=Mode.SUBTRACT,
        )

    # 4. FPC exit slot — in the -X wall, offset +6.75mm in Y.
    #    FPC housing aligned with NW corner; flex (10mm) exits centered
    #    within the 15mm housing. Slot sized for flex, not full housing.
    fpc_slot_z = BASE_THICKNESS + FPC_SLOT_HEIGHT / 2
    with Locations([(-SHELL_WIDTH / 2, FPC_CENTER_Y, fpc_slot_z)]):
        Box(
            WALL_X * 2 + 1,
            FPC_SLOT_WIDTH,
            FPC_SLOT_HEIGHT,
            mode=Mode.SUBTRACT,
        )

# ============================================================
# Build — Lid
# ============================================================
# Simple flat plate. Sits on top of tray walls, held down by zip ties.

with BuildPart() as lid:
    with BuildSketch(Plane.XY):
        Rectangle(SHELL_WIDTH, SHELL_LENGTH)
    extrude(amount=LID_THICKNESS)

# ============================================================
# Export
# ============================================================

export_stl(tray.part, str(OUTPUT_DIR / "outer_tray.stl"))
export_step(tray.part, str(OUTPUT_DIR / "outer_tray.step"))
export_stl(lid.part, str(OUTPUT_DIR / "outer_lid.stl"))
export_step(lid.part, str(OUTPUT_DIR / "outer_lid.step"))

bb_tray = tray.part.bounding_box()
bb_lid = lid.part.bounding_box()

print("Outer shell built successfully")
print(f"\nTray:")
print(f"  Bounding box: {bb_tray.size.X:.1f} x {bb_tray.size.Y:.1f} x {bb_tray.size.Z:.1f} mm")
print(f"  Volume: {tray.part.volume:.1f} mm³")
print(f"  Interior: {INTERIOR_X:.1f} x {INTERIOR_Y:.1f} x {CAVITY_DEPTH:.1f} mm")
print(f"  Walls: X={WALL_X:.1f} mm, Y={WALL_Y:.1f} mm")
print(f"\nLid:")
print(f"  Bounding box: {bb_lid.size.X:.1f} x {bb_lid.size.Y:.1f} x {bb_lid.size.Z:.1f} mm")
print(f"\nConnector slots:")
print(f"  JST-SH: X offset = {JST_X_OFFSET:+.1f} mm, slot {CABLE_SLOT_WIDTH:.1f} x {CABLE_SLOT_HEIGHT:.1f} mm in -Y wall")
print(f"  FPC:    Y offset = {FPC_CENTER_Y:+.1f} mm, slot {FPC_SLOT_WIDTH:.1f} x {FPC_SLOT_HEIGHT:.1f} mm in -X wall")
print(f"\nAssembled total height: {TOTAL_HEIGHT:.1f} mm")
print(f"Exported: outer_tray.stl/step, outer_lid.stl/step")

if HAS_VIEWER:
    show(tray, lid)

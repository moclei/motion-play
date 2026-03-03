"""
Inner Shell — Motion Play Sensor Enclosure (Option A)

Sits on the inner face (hoop-interior side) of the steel flat bar.
Provides a flat base against the bar, a ramped surround that deflects
ball impacts away from the sensors, and an open sensor window for the
VCNL4040 optical path.

Print orientation: base plate flat on build plate, ramps facing up.
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
# Spec dimensions (from mechanical/specs/assembly-v0.1.yaml)
# ============================================================

BAR_WIDTH = 25.25           # mm — flat face width of hoop bar
BAR_THICKNESS = 4.0         # mm — thin edge of hoop bar
FLEX_PCB_WIDTH = 10.0       # mm
FLEX_SEATING_LENGTH = 22.0  # mm — portion lying flat on inner face
SENSOR_HEIGHT = 1.4         # mm — VCNL4040 protrusion above flex surface
SENSOR_SPACING = 10.0       # mm — center-to-center between two sensors

# ============================================================
# Design parameters
# ============================================================

BASE_THICKNESS = 2.0    # mm — flat plate that contacts the bar
SIDE_EXTENSION = 3.0    # mm — shell extends beyond bar edge each side

RAMP_HEIGHT = 3.5       # mm above base top surface
RAMP_RUN = 4.0          # mm horizontal distance the ramp slopes inward

WINDOW_WIDTH = 12.0     # mm across bar (X) — both sensors + clearance
WINDOW_LENGTH = 16.0    # mm along hoop (Y) — sensor spacing + margin

FLEX_RECESS_DEPTH = 0.4     # mm — shallow channel to locate the flex PCB
FLEX_RECESS_CLEARANCE = 0.5 # mm total width clearance around flex

# ============================================================
# Computed
# ============================================================

SHELL_WIDTH = BAR_WIDTH + 2 * SIDE_EXTENSION        # 31.25 mm
SHELL_LENGTH = WINDOW_LENGTH + 2 * (RAMP_RUN + 5.0) # 34.0 mm
TOTAL_HEIGHT = BASE_THICKNESS + RAMP_HEIGHT          # 5.5 mm

TAPER_ANGLE = math.degrees(math.atan(RAMP_RUN / RAMP_HEIGHT))

RAMP_TOP_WIDTH = SHELL_WIDTH - 2 * RAMP_RUN   # 23.25 mm
RAMP_TOP_LENGTH = SHELL_LENGTH - 2 * RAMP_RUN # 26.0 mm

# Minimum wall thickness at ramp top (between window edge and ramp outer edge)
MIN_WALL_X = (RAMP_TOP_WIDTH - WINDOW_WIDTH) / 2   # 5.625 mm
MIN_WALL_Y = (RAMP_TOP_LENGTH - WINDOW_LENGTH) / 2 # 5.0 mm

# ============================================================
# Coordinate convention
# ============================================================
#   X = across bar width (25.25 mm direction)
#   Y = along hoop circumference
#   Z = radial; +Z = into hoop interior (away from bar)
#   Origin = center of base plate, bar-contact surface at Z=0

# ============================================================
# Build
# ============================================================

with BuildPart() as inner_shell:

    # 1. Base plate
    with BuildSketch(Plane.XY):
        Rectangle(SHELL_WIDTH, SHELL_LENGTH)
    extrude(amount=BASE_THICKNESS)

    # 2. Ramp surround — tapered extrusion creates sloped outer walls.
    #    Bottom = full shell footprint, top = inset by RAMP_RUN each side.
    with BuildSketch(Plane.XY.offset(BASE_THICKNESS)):
        Rectangle(SHELL_WIDTH, SHELL_LENGTH)
    extrude(amount=RAMP_HEIGHT, taper=TAPER_ANGLE)

    # 3. Sensor window — hollow out the center of the ramp so sensors
    #    sit in a recessed well, protected by the surrounding ramp walls.
    with Locations([(0, 0, BASE_THICKNESS + RAMP_HEIGHT / 2)]):
        Box(WINDOW_WIDTH, WINDOW_LENGTH, RAMP_HEIGHT + 1, mode=Mode.SUBTRACT)

    # 4. Flex entry — open the -X ramp wall so the flex PCB can enter
    #    from the thin edge after its 180-degree bend. Only as wide as
    #    the flex PCB (+ clearance), preserving ramp wall above and below.
    wall_thickness_at_base = (SHELL_WIDTH - WINDOW_WIDTH) / 2
    with Locations([
        (-(WINDOW_WIDTH / 2 + wall_thickness_at_base / 2), 0,
         BASE_THICKNESS + RAMP_HEIGHT / 2)
    ]):
        Box(
            wall_thickness_at_base + 1,
            FLEX_PCB_WIDTH + 1.0,
            RAMP_HEIGHT + 1,
            mode=Mode.SUBTRACT,
        )

    # 5. Flex PCB recess — shallow channel in base plate top surface
    #    to locate the flex strip and prevent lateral sliding.
    with Locations([(0, 0, BASE_THICKNESS - FLEX_RECESS_DEPTH / 2)]):
        Box(
            FLEX_PCB_WIDTH + FLEX_RECESS_CLEARANCE,
            FLEX_SEATING_LENGTH,
            FLEX_RECESS_DEPTH,
            mode=Mode.SUBTRACT,
        )

# ============================================================
# Export
# ============================================================

stl_path = OUTPUT_DIR / "inner_shell.stl"
step_path = OUTPUT_DIR / "inner_shell.step"

export_stl(inner_shell.part, str(stl_path))
export_step(inner_shell.part, str(step_path))

bb = inner_shell.part.bounding_box()
print(f"Inner shell built successfully")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print(f"  Volume: {inner_shell.part.volume:.1f} mm³")
print(f"  Taper angle: {TAPER_ANGLE:.1f}° from vertical ({90 - TAPER_ANGLE:.1f}° from horizontal)")
print(f"  Ramp top: {RAMP_TOP_WIDTH:.1f} x {RAMP_TOP_LENGTH:.1f} mm")
print(f"  Min wall at top: X={MIN_WALL_X:.1f} mm, Y={MIN_WALL_Y:.1f} mm")
print(f"  Exported: {stl_path.name}, {step_path.name}")

if HAS_VIEWER:
    show(inner_shell)

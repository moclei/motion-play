"""
Inner Shell — Motion Play Sensor Enclosure (Option A)

Sits on the inner face (hoop-interior side) of the steel flat bar.
Provides a flat base against the bar, a ramped surround that deflects
ball impacts, an open sensor window, and a V-ridge that angles the two
sensors at ±3° toward opposite hoop entrances for direction detection.

Print orientation: base plate flat on build plate, ramps facing up.
Material recommendation: PETG for impact toughness.

Coordinate convention:
  X = across bar width (25.25mm) — hoop axial direction
  Y = along hoop circumference
  Z = radial; +Z = into hoop interior (away from bar)
  Origin = center of base plate, bar-contact surface at Z=0

The flex PCB enters from the -X thin edge, extends across the bar in X.
Its 10mm width runs along Y, centered at Y = -FPC_CENTER_Y because the
inner shell is viewed from the opposite side of the bar compared to the
outer shell (Y mirrors when going from outer face to inner face).

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
# Spec dimensions
# ============================================================

BAR_WIDTH = 25.25           # mm — flat face width
BAR_THICKNESS = 4.0         # mm — thin edge
FLEX_PCB_WIDTH = 10.0       # mm — narrow dimension, runs along Y on inner face
FLEX_SEATING_LENGTH = 22.0  # mm — lies across bar width in X direction
SENSOR_HEIGHT = 1.4         # mm — VCNL4040 protrusion above flex

# Sensor positions (measured from the far end of the flex, the +X end)
SENSOR_1_FROM_END = 7.25    # mm — sensor farthest from FPC tail
SENSOR_2_FROM_END = 17.75   # mm — sensor nearest to FPC tail
SENSOR_SPACING = 10.5       # mm — center-to-center
SENSOR_MIDPOINT_FROM_END = (SENSOR_1_FROM_END + SENSOR_2_FROM_END) / 2  # 12.5 mm

# FPC connector is at Y=+6.75 on the outer shell. Viewed from the inner
# face (opposite side of bar), this maps to Y=-6.75.
FPC_CENTER_Y_OUTER = 6.75   # mm — on outer shell

SENSOR_ANGLE_DEG = 3.0      # degrees — tilt per sensor from horizontal

# ============================================================
# Design parameters
# ============================================================

BASE_THICKNESS = 2.0        # mm — flat plate against bar

RAMP_HEIGHT = 3.5           # mm above base top surface
RAMP_RUN = 4.0              # mm horizontal ramp slope distance

# ============================================================
# Tray interface — must match outer_shell.py wrap-tray dimensions
# ============================================================

TRAY_SIDE_EXT = 8.0         # mm — tray's side extension past bar edge
TRAY_WRAP_WALL = 2.0        # mm — tray wrap-around wall thickness
TRAY_BOSS_DIAM = 5.0        # mm — screw boss outer diameter
ASSEMBLY_CLEARANCE = 0.3    # mm per side

# Inner shell sized to fit inside the tray's wrap-around opening
TRAY_OPENING_HALF_X = BAR_WIDTH / 2 + TRAY_SIDE_EXT - TRAY_WRAP_WALL  # 18.625
SIDE_EXTENSION = TRAY_OPENING_HALF_X - ASSEMBLY_CLEARANCE - BAR_WIDTH / 2  # ~5.7 mm

# M2 screw clearance holes — positions must match tray boss centers
SCREW_HOLE_DIAM = 2.4       # mm — M2 clearance
SCREW_X = TRAY_OPENING_HALF_X - TRAY_BOSS_DIAM / 2 + 0.5  # 16.625 mm from center
SCREW_Y = 0.0               # centered in Y

# ============================================================
# Flex channel positioning
# ============================================================
# The flex extends across the bar in X. Position it so the sensor
# midpoint sits at bar center (X = 0). Y is mirrored from outer shell.

FLEX_FAR_X = SENSOR_MIDPOINT_FROM_END                        # +12.5 mm
FLEX_NEAR_X = FLEX_FAR_X - FLEX_SEATING_LENGTH                # -9.5 mm
FLEX_CENTER_X = (FLEX_FAR_X + FLEX_NEAR_X) / 2               # +1.5 mm
FLEX_CENTER_Y = -FPC_CENTER_Y_OUTER                           # -6.75 mm

SENSOR_1_X = FLEX_FAR_X - SENSOR_1_FROM_END                  # +5.25 mm
SENSOR_2_X = FLEX_FAR_X - SENSOR_2_FROM_END                  # -5.25 mm

# ============================================================
# Sensor well (window subtracted from ramp surround)
# ============================================================
# Must be wide enough for the full flex PCB to slide in from -X
# until the sensor midpoint reaches X = 0 (the V-ridge peak).
# -X edge: at sensor 2 minus 2mm margin (flex entry handles the rest)
# +X edge: at flex far end + 0.5mm insertion clearance

WELL_X_MIN = SENSOR_2_X - 2.0                # -7.25 mm
WELL_X_MAX = FLEX_FAR_X + 0.5                # +13.0 mm
WINDOW_X = WELL_X_MAX - WELL_X_MIN           # 20.25 mm
WINDOW_Y = FLEX_PCB_WIDTH + 2.0              # 12.0 mm
WINDOW_CENTER_X = (WELL_X_MIN + WELL_X_MAX) / 2  # +2.875 mm
WINDOW_CENTER_Y = FLEX_CENTER_Y              # -6.75 mm

# ============================================================
# V-ridge for sensor angling
# ============================================================
# Ridge on base plate top, peak at X=0, slopes at SENSOR_ANGLE_DEG
# on each side. Sensor 1 (+X) looks toward +X hoop entrance,
# sensor 2 (-X) looks toward -X hoop entrance.

RIDGE_HALF_X = max(abs(FLEX_FAR_X), abs(FLEX_NEAR_X))        # 12.5 mm
RIDGE_HEIGHT = RIDGE_HALF_X * math.tan(math.radians(SENSOR_ANGLE_DEG))  # ~0.655 mm
RIDGE_Y_LENGTH = FLEX_PCB_WIDTH + 1.0                         # 11.0 mm

# ============================================================
# Shell dimensions
# ============================================================

SHELL_WIDTH = BAR_WIDTH + 2 * SIDE_EXTENSION   # 31.25 mm (X)
SHELL_LENGTH = 38.0                             # mm (Y) — accommodates offset window

TOTAL_HEIGHT = BASE_THICKNESS + RAMP_HEIGHT     # 5.5 mm
TAPER_ANGLE = math.degrees(math.atan(RAMP_RUN / RAMP_HEIGHT))

RAMP_TOP_WIDTH = SHELL_WIDTH - 2 * RAMP_RUN    # 23.25 mm
RAMP_TOP_LENGTH = SHELL_LENGTH - 2 * RAMP_RUN  # 30.0 mm

# ============================================================
# Build
# ============================================================

with BuildPart() as inner_shell:

    # 1. Base plate
    with BuildSketch(Plane.XY):
        Rectangle(SHELL_WIDTH, SHELL_LENGTH)
    extrude(amount=BASE_THICKNESS)

    # 2. Ramp surround — tapered walls, centered on shell footprint
    with BuildSketch(Plane.XY.offset(BASE_THICKNESS)):
        Rectangle(SHELL_WIDTH, SHELL_LENGTH)
    extrude(amount=RAMP_HEIGHT, taper=TAPER_ANGLE)

    # 3. Sensor window — cut only ramp material, preserve base plate.
    #    Box bottom at Z = BASE_THICKNESS (not below) so the ridge can
    #    sit directly on the intact base plate surface.
    window_cut_h = RAMP_HEIGHT + 1
    window_cut_z = BASE_THICKNESS + window_cut_h / 2
    with Locations([(WINDOW_CENTER_X, WINDOW_CENTER_Y, window_cut_z)]):
        Box(WINDOW_X, WINDOW_Y, window_cut_h, mode=Mode.SUBTRACT)

    # 4. Flex entry — open from sensor window to -X shell edge.
    #    Same Z range as window cut (above base plate only).
    window_x_min = WINDOW_CENTER_X - WINDOW_X / 2     # -7.25
    shell_x_min = -SHELL_WIDTH / 2                     # -15.625
    entry_x_size = abs(window_x_min - shell_x_min) + 1
    entry_x_center = (window_x_min + shell_x_min) / 2
    with Locations([(entry_x_center, FLEX_CENTER_Y, window_cut_z)]):
        Box(
            entry_x_size,
            FLEX_PCB_WIDTH + 1.0,
            window_cut_h,
            mode=Mode.SUBTRACT,
        )

    # 5. M2 screw clearance holes — through the base plate overhang area.
    #    These align with the heat-set insert bosses in the wrap-around tray.
    screw_hole_depth = BASE_THICKNESS + RAMP_HEIGHT + 1
    screw_hole_z = screw_hole_depth / 2 - 0.5
    with Locations([(-SCREW_X, SCREW_Y, screw_hole_z)]):
        Cylinder(SCREW_HOLE_DIAM / 2, screw_hole_depth, mode=Mode.SUBTRACT)
    with Locations([(SCREW_X, SCREW_Y, screw_hole_z)]):
        Cylinder(SCREW_HOLE_DIAM / 2, screw_hole_depth, mode=Mode.SUBTRACT)

    # 6. V-ridge — lofted triangular prism on base plate surface.
    #    Bottom face: wide rectangle at Z just below BASE_THICKNESS (overlap
    #    ensures solid boolean union with the base plate).
    #    Top face: hair-thin rectangle at Z = BASE_THICKNESS + RIDGE_HEIGHT.
    #    Loft creates a prism with planar 3° slopes on each side.
    with BuildSketch(Plane.XY.offset(BASE_THICKNESS - 0.05)):
        with Locations([(0, FLEX_CENTER_Y)]):
            Rectangle(2 * RIDGE_HALF_X, RIDGE_Y_LENGTH)
    with BuildSketch(Plane.XY.offset(BASE_THICKNESS + RIDGE_HEIGHT)):
        with Locations([(0, FLEX_CENTER_Y)]):
            Rectangle(0.01, RIDGE_Y_LENGTH)
    loft()

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
print(f"  Shell: {SHELL_WIDTH:.1f} x {SHELL_LENGTH:.1f} mm")
print(f"  Sensor window: {WINDOW_X:.1f} x {WINDOW_Y:.1f} mm at ({WINDOW_CENTER_X:.1f}, {WINDOW_CENTER_Y:.1f})")
print(f"  Flex channel: X=[{FLEX_NEAR_X:.1f}, {FLEX_FAR_X:.1f}], Y center={FLEX_CENTER_Y:.1f}")
print(f"  Sensor 1 (far): X={SENSOR_1_X:+.2f},  Sensor 2 (near): X={SENSOR_2_X:+.2f}")
print(f"  V-ridge: {RIDGE_HEIGHT:.3f} mm peak, {SENSOR_ANGLE_DEG}° each side")
print(f"  Exported: {stl_path.name}, {step_path.name}")

if HAS_VIEWER:
    show(inner_shell)

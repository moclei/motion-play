"""
Interior Channel Segment — Motion Play

A curved U-channel that sits on the interior circumference of the hoop
between sensor assemblies, housing the WS2812B LED strip and protecting
it from ball impact. Six identical segments cover the full hoop interior
(two per arc section between the three sensor assemblies).

The cross-section has four zones:
  - Clip wings with lips: extend above the base, wrapping the 4mm bar
    edges. Continuous inward-facing lips (0.5mm overhang) provide snap
    retention along the full arc. A 45° entry ramp on each lip eases
    progressive push-on installation (start at one end, work along).
    Wing deflection during assembly: ~0.3mm at 3.4% strain (within PLA).
  - Base plate: spans the full bar width at the bar's inner face,
    connecting the clip wings to the inner channel walls.
  - Fender: angled exterior surface replacing the flat shelf between
    the wing base and the inner wall. Deflects ball impacts instead of
    presenting a 90° ledge that a ball could catch on.
  - LED channel: U-shaped cavity below the base, housing the WS2812B
    strip. Walls are tall enough that a soccer ball (~220mm dia) can't
    reach the strip through the 16mm opening.

The segment is swept along a ~245mm arc at the hoop's inner radius.

Print orientation: concave side up, base flat on build plate.
  Chord length (~235mm) runs along the 250mm plate axis.
Material: PLA for prototyping, PETG for final.

Coordinate convention (hoop-centric, differs from sensor enclosures):
  The hoop lies in the XY plane, centered at the origin.
  Z = hoop axial direction (across bar width, 25.25mm).
  Radial direction is in the XY plane; inner radius at r = 252.5mm.
  The segment arc starts at 0° (+X axis) and sweeps counterclockwise.

See: mechanical/specs/assembly-v0.1.yaml
See: mechanical/FDM_DESIGN_RULES.md
See: docs/explorations/interior-channel.md
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
# Hoop geometry (from assembly-v0.1.yaml)
# ============================================================

HOOP_INNER_RADIUS = 252.5       # mm — inner diameter 505mm
BAR_WIDTH = 25.25               # mm — flat face (hoop axial direction)
BAR_THICKNESS = 4.0             # mm — thin edge (radial direction)
BAR_CENTER_RADIUS = HOOP_INNER_RADIUS + BAR_THICKNESS / 2  # 254.5mm

# ============================================================
# Segment layout
# ============================================================

SENSOR_ASSEMBLY_COUNT = 3
SEGMENTS_PER_SECTION = 2
TOTAL_SEGMENTS = SENSOR_ASSEMBLY_COUNT * SEGMENTS_PER_SECTION  # 6

HOOP_CIRCUMFERENCE = 2 * math.pi * HOOP_INNER_RADIUS  # ~1586mm
SECTION_ARC = HOOP_CIRCUMFERENCE / SENSOR_ASSEMBLY_COUNT  # ~529mm
SENSOR_FOOTPRINT = 38.0         # mm — sensor assembly along circumference
AVAILABLE_ARC = SECTION_ARC - SENSOR_FOOTPRINT  # ~491mm
SEGMENT_ARC_LENGTH = AVAILABLE_ARC / SEGMENTS_PER_SECTION  # ~245mm

SEGMENT_ANGLE_RAD = SEGMENT_ARC_LENGTH / HOOP_INNER_RADIUS
SEGMENT_ANGLE_DEG = math.degrees(SEGMENT_ANGLE_RAD)  # ~55.6°

# ============================================================
# Channel cross-section (see FDM_DESIGN_RULES.md)
# ============================================================

WALL_THICKNESS = 1.6            # mm — 4 perimeters @ 0.4mm nozzle
BASE_THICKNESS = 1.6            # mm — 4 perimeters
WALL_HEIGHT = 8.0               # mm above base; sized so a soccer ball
                                #   (~220mm Ø) can't reach the LED strip
                                #   through the 16mm wide opening
CHANNEL_INNER_WIDTH = 16.0      # mm — fits WS2812B strip (~14mm w/ silicone)
CHANNEL_OUTER_WIDTH = CHANNEL_INNER_WIDTH + 2 * WALL_THICKNESS  # 19.2mm
CHANNEL_TOTAL_HEIGHT = BASE_THICKNESS + WALL_HEIGHT  # 9.6mm

# ============================================================
# Clip wing geometry (snug-fit bar edge retention)
# ============================================================

CLIP_CLEARANCE = 0.20           # mm per side — snug/sliding fit
WING_THICKNESS = 1.2            # mm — thin feature (FDM min 0.8)

LIP_DEPTH = 0.5                 # mm — inward overhang past wing inner face
LIP_THICKNESS = 0.6             # mm — hook face height at lip tip
LIP_RAMP = LIP_DEPTH            # mm — 45° entry ramp vertical extent

WING_HEIGHT = BAR_THICKNESS + LIP_THICKNESS + LIP_RAMP  # 5.1mm — extends past bar outer face
                                # so lip ramp starts exactly at bar outer face

# Derived positions (from profile center, along hoop axis)
HALF_BAR = BAR_WIDTH / 2                           # 12.625mm
HALF_CH_INNER = CHANNEL_INNER_WIDTH / 2            # 8.0mm
HALF_CH_OUTER = CHANNEL_OUTER_WIDTH / 2            # 9.6mm
WING_INNER_X = HALF_BAR + CLIP_CLEARANCE           # 12.825mm
WING_OUTER_X = WING_INNER_X + WING_THICKNESS       # 14.025mm
LIP_TIP_X = WING_INNER_X - LIP_DEPTH              # 12.325mm
OVERALL_WIDTH = 2 * WING_OUTER_X                    # 28.05mm

# Snap-fit strain check (cantilever: ε = 1.5·t·y / L²)
# Actual deflection = LIP_DEPTH - CLIP_CLEARANCE (clearance absorbs part)
LIP_DEFLECTION = LIP_DEPTH - CLIP_CLEARANCE        # 0.3mm
LIP_STRAIN = 1.5 * WING_THICKNESS * LIP_DEFLECTION / WING_HEIGHT**2
assert LIP_STRAIN < 0.04, f"Lip strain {LIP_STRAIN:.1%} exceeds 4% PLA limit"

# ============================================================
# Hoop reference (visualization only)
# ============================================================

HOOP_REF_EXTRA_DEG = 8.0        # extra arc beyond segment on each side

# ============================================================
# Build — Channel Segment
# ============================================================

# Profile outline (cross-section in profile plane local coords):
#   x_local = hoop axis (across bar width)
#   y_local = outward radial (+ = toward outer face, - = toward hoop center)
#   y = 0 is the bar inner face (base contact surface)
#
#   Cross-section schematic:
#
#         lip    bar slot    lip
#        ┌──┤               ├──┐   y = +WING_HEIGHT
#        │  /               \  │   (45° lip ramp)
#        │ │                 │ │
#   ─────┘ └─────────────────┘ └───  y = 0 (bar inner face)
#   ───────────────────────────────  y = -BASE_THICKNESS
#      \    ┌───────────────┐    /
#       \   │               │   /   (fender)
#        \  │   LED strip   │  /
#         \ │               │ /
#          └┘               └┘     y = -CHANNEL_TOTAL_HEIGHT

Y_BOTTOM = -CHANNEL_TOTAL_HEIGHT    # -9.6
Y_BASE = -BASE_THICKNESS            # -1.6
Y_LIP_RAMP = WING_HEIGHT - LIP_THICKNESS - LIP_RAMP  # 2.9

profile_pts = [
    # Left fender (diagonal replaces the flat shelf + 90° corners)
    (-HALF_CH_OUTER, Y_BOTTOM),
    (-WING_OUTER_X, Y_BASE),
    # Left wing outer face
    (-WING_OUTER_X, WING_HEIGHT),
    # Left lip (hook face + 45° entry ramp)
    (-LIP_TIP_X, WING_HEIGHT),
    (-LIP_TIP_X, WING_HEIGHT - LIP_THICKNESS),
    (-WING_INNER_X, Y_LIP_RAMP),
    # Left wing inner face down to bar surface
    (-WING_INNER_X, 0),
    # Bar contact surface between wings
    (+WING_INNER_X, 0),
    # Right wing inner face up to lip ramp
    (+WING_INNER_X, Y_LIP_RAMP),
    # Right lip (45° entry ramp + hook face)
    (+LIP_TIP_X, WING_HEIGHT - LIP_THICKNESS),
    (+LIP_TIP_X, WING_HEIGHT),
    # Right wing outer face
    (+WING_OUTER_X, WING_HEIGHT),
    (+WING_OUTER_X, Y_BASE),
    # Right fender (diagonal)
    (+HALF_CH_OUTER, Y_BOTTOM),
    # LED cavity opening (across bottom, up inner walls)
    (+HALF_CH_INNER, Y_BOTTOM),
    (+HALF_CH_INNER, Y_BASE),
    (-HALF_CH_INNER, Y_BASE),
    (-HALF_CH_INNER, Y_BOTTOM),
]

with BuildPart() as channel:
    with BuildLine(Plane.XY):
        CenterArc(
            (0, 0),
            HOOP_INNER_RADIUS,
            start_angle=0,
            arc_size=SEGMENT_ANGLE_DEG,
        )

    # Profile plane at arc start (angle = 0°):
    #   point = (R, 0, 0), tangent = (0, 1, 0)
    #   x_local → hoop axis (global Z)
    #   y_local → outward radial (global +X at 0°)
    profile_plane = Plane(
        origin=(HOOP_INNER_RADIUS, 0, 0),
        x_dir=(0, 0, 1),
        z_dir=(0, 1, 0),
    )

    with BuildSketch(profile_plane):
        with BuildLine():
            Polyline(*profile_pts, close=True)
        make_face()

    sweep()

# ============================================================
# Build — Hoop Bar Reference
# ============================================================

hoop_ref_start_deg = -HOOP_REF_EXTRA_DEG
hoop_ref_arc_deg = SEGMENT_ANGLE_DEG + 2 * HOOP_REF_EXTRA_DEG
hoop_ref_start_rad = math.radians(hoop_ref_start_deg)

with BuildPart() as hoop_ref:
    with BuildLine(Plane.XY):
        CenterArc(
            (0, 0),
            BAR_CENTER_RADIUS,
            start_angle=hoop_ref_start_deg,
            arc_size=hoop_ref_arc_deg,
        )

    hoop_start_pt = (
        BAR_CENTER_RADIUS * math.cos(hoop_ref_start_rad),
        BAR_CENTER_RADIUS * math.sin(hoop_ref_start_rad),
        0,
    )
    hoop_tangent = (
        -math.sin(hoop_ref_start_rad),
        math.cos(hoop_ref_start_rad),
        0,
    )

    hoop_profile_plane = Plane(
        origin=hoop_start_pt,
        x_dir=(0, 0, 1),
        z_dir=hoop_tangent,
    )

    with BuildSketch(hoop_profile_plane):
        Rectangle(BAR_WIDTH, BAR_THICKNESS)

    sweep()

# ============================================================
# Export
# ============================================================

stl_path = OUTPUT_DIR / "channel_segment.stl"
step_path = OUTPUT_DIR / "channel_segment.step"
hoop_step_path = OUTPUT_DIR / "hoop_reference.step"

export_stl(channel.part, str(stl_path))
export_step(channel.part, str(step_path))
export_step(hoop_ref.part, str(hoop_step_path))

bb = channel.part.bounding_box()
chord = 2 * HOOP_INNER_RADIUS * math.sin(SEGMENT_ANGLE_RAD / 2)
sagitta = HOOP_INNER_RADIUS * (1 - math.cos(SEGMENT_ANGLE_RAD / 2))

bar_slot = 2 * WING_INNER_X
lip_gap = 2 * LIP_TIP_X

print(f"Interior channel segment built successfully")
print(f"  Arc: {SEGMENT_ARC_LENGTH:.1f} mm, {SEGMENT_ANGLE_DEG:.1f}°")
print(f"  Chord: {chord:.1f} mm, Sagitta: {sagitta:.1f} mm")
print(f"  Overall width: {OVERALL_WIDTH:.1f} mm (wings {WING_THICKNESS:.1f} mm thick)")
print(f"  Bar slot: {bar_slot:.2f} mm (bar {BAR_WIDTH:.2f} mm + {CLIP_CLEARANCE:.2f} mm/side)")
print(f"  Lip gap: {lip_gap:.2f} mm (overhang {LIP_DEPTH:.1f} mm, deflection {LIP_DEFLECTION:.1f} mm, strain {LIP_STRAIN:.1%})")
print(f"  LED channel: {CHANNEL_INNER_WIDTH:.1f} wide x {WALL_HEIGHT:.1f} deep")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print(f"  Volume: {channel.part.volume:.1f} mm3")
print(f"  Segments needed: {TOTAL_SEGMENTS}")
print(f"  Exported: {stl_path.name}, {step_path.name}, {hoop_step_path.name}")

if HAS_VIEWER:
    show(channel, hoop_ref, names=["channel_segment", "hoop_reference"])

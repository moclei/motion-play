"""
Door Latch Spring — V5 Spiral Spring

Changes from V4:
  - Flex bars replaced with a flat Archimedean spiral spring.
  - The spiral coils in the XY plane at Z=12.5-15, sitting in the
    +Z space above the posts (below the cover plate).
  - Short rigid arms connect the spiral ends to the sleeve walls.
  - ~35mm of beam path in a compact footprint, estimated max strain
    ~1% at full deflection — much better than straight bars.

The spiral arms approach the sleeves tangentially rather than at
right angles, distributing attachment stress and avoiding the
sharp-corner failure that broke V4.

Print orientation: Z-up. The spiral prints flat in the XY plane
so bending stress runs along layer lines.

Coordinate system:
  Origin = center of main post at mechanism base (Z=0)
  X = across mechanism width
  Y = along mechanism (-Y toward minor post)
  Z = mechanism depth (upward from base plate)

See: mechanical/FDM_DESIGN_RULES.md
"""

from build123d import *
from pathlib import Path
import math

try:
    from ocp_vscode import show, set_port
    set_port(3939)
    HAS_VIEWER = True
except ImportError:
    HAS_VIEWER = False

OUTPUT_DIR = Path(__file__).parent

# ============================================================
# Measured dimensions (from mechanism)
# ============================================================

MAIN_POST_RECT_X = 4.95
MAIN_POST_RECT_Y = 3.50
MAIN_POST_CYL_DIAM = 4.9
MAIN_POST_Z = 12.0

MINOR_POST_X = 4.40
MINOR_POST_Y = 2.00
MINOR_POST_Z = 2.50
MINOR_BASE_Z = 11.0

MINOR_OFFSET_X = -3.3
MINOR_OFFSET_Y = -18.0

# ============================================================
# Design parameters
# ============================================================

CLEARANCE = 0.15

# Main sleeve (tube — open both ends, hybrid bore)
MAIN_WALL = 2.0
MAIN_WALL_THIN = 1.5
MAIN_SLEEVE_Z_BOT = 2.0
MAIN_SLEEVE_Z_TOP = 15.0
MAIN_RECT_HEIGHT = 2.0

# Minor sleeve (cup — open bottom, capped top)
MINOR_WALL = 2.0
MINOR_CAP = 1.5
MINOR_SLEEVE_Z_BOT = 9.5
MINOR_SLEEVE_Z_TOP = MINOR_BASE_Z + MINOR_POST_Z + MINOR_CAP
MINOR_WING_Z_BOT = MAIN_SLEEVE_Z_BOT

# Spiral spring
SPIRAL_CX = -1.65              # center X (midpoint between posts)
SPIRAL_CY = -10.0              # center Y (biased slightly toward minor post)
SPIRAL_Z_BOT = 12.5            # bottom Z of spiral strip
SPIRAL_STRIP_W = 2.5           # strip width in Z
SPIRAL_STRIP_T = 0.8           # strip thickness (radial — the flex dimension)
SPIRAL_R_INNER = 2.0           # inner coil radius
SPIRAL_R_OUTER = 5.5           # outer coil radius
SPIRAL_TURNS = 1.5
SPIRAL_N_PTS = 90              # polyline resolution

# Arms (rigid connectors from spiral ends to sleeve walls)
ARM_WIDTH = 2.5                # X width of arm bars
ARM_OVERLAP = 1.0              # overlap into spiral/sleeve for union

# ============================================================
# Computed
# ============================================================

SPIRAL_Z_TOP = SPIRAL_Z_BOT + SPIRAL_STRIP_W
SPIRAL_TOTAL_ANGLE = SPIRAL_TURNS * 2 * math.pi

# Main sleeve
main_rect_inner_x = MAIN_POST_RECT_X + 2 * CLEARANCE
main_rect_inner_y = MAIN_POST_RECT_Y + 2 * CLEARANCE
main_outer_x = main_rect_inner_x + 2 * MAIN_WALL
main_outer_y = main_rect_inner_y + MAIN_WALL + MAIN_WALL_THIN
main_center_y = -(MAIN_WALL - MAIN_WALL_THIN) / 2
main_height = MAIN_SLEEVE_Z_TOP - MAIN_SLEEVE_Z_BOT
main_cyl_bore = MAIN_POST_CYL_DIAM + 2 * CLEARANCE
main_neg_y = -(main_rect_inner_y / 2) - MAIN_WALL

# Minor sleeve
minor_inner_x = MINOR_POST_X + 2 * CLEARANCE
minor_inner_y = MINOR_POST_Y + 2 * CLEARANCE
minor_outer_x = minor_inner_x + 2 * MINOR_WALL
minor_outer_y = minor_inner_y + 2 * MINOR_WALL
minor_height = MINOR_SLEEVE_Z_TOP - MINOR_SLEEVE_Z_BOT
minor_pos_y = MINOR_OFFSET_Y + minor_outer_y / 2

# Minor +Y wing
wing_z_top = MINOR_SLEEVE_Z_BOT
wing_z_bot = MINOR_WING_Z_BOT
wing_height = wing_z_top - wing_z_bot
wing_z_ctr = (wing_z_top + wing_z_bot) / 2
wing_y_pos = minor_pos_y - MINOR_WALL / 2

# Spiral geometry — Archimedean spiral: r = R_INNER + (R_OUTER-R_INNER) * θ/total_θ
# Oriented so θ=0 points +Y from center (toward main sleeve),
# θ=total points -Y from center (toward minor sleeve).

def spiral_point(t):
    """Return (x, y) for parameter t in [0, 1]."""
    theta = t * SPIRAL_TOTAL_ANGLE
    r = SPIRAL_R_INNER + (SPIRAL_R_OUTER - SPIRAL_R_INNER) * t
    x = SPIRAL_CX - r * math.sin(theta)
    y = SPIRAL_CY + r * math.cos(theta)
    return (x, y)

def spiral_outline_points():
    """Generate the 2D outline of the spiral strip as a closed polygon."""
    outer_pts = []
    inner_pts = []
    for i in range(SPIRAL_N_PTS + 1):
        t = i / SPIRAL_N_PTS
        theta = t * SPIRAL_TOTAL_ANGLE
        r_center = SPIRAL_R_INNER + (SPIRAL_R_OUTER - SPIRAL_R_INNER) * t
        r_out = r_center + SPIRAL_STRIP_T / 2
        r_in = r_center - SPIRAL_STRIP_T / 2

        outer_pts.append(Vector(
            SPIRAL_CX - r_out * math.sin(theta),
            SPIRAL_CY + r_out * math.cos(theta),
        ))
        inner_pts.append(Vector(
            SPIRAL_CX - r_in * math.sin(theta),
            SPIRAL_CY + r_in * math.cos(theta),
        ))
    return outer_pts + list(reversed(inner_pts))

# Spiral endpoint positions (for arm placement)
spiral_inner_end = spiral_point(0)     # near main sleeve
spiral_outer_end = spiral_point(1)     # near minor sleeve

# Arm geometry — main arm
main_arm_y_top = main_neg_y + ARM_OVERLAP
main_arm_y_bot = spiral_inner_end[1] - ARM_OVERLAP
main_arm_y_span = abs(main_arm_y_top - main_arm_y_bot)
main_arm_y_ctr = (main_arm_y_top + main_arm_y_bot) / 2
main_arm_x = spiral_inner_end[0]

# Arm geometry — minor arm
minor_arm_y_bot = minor_pos_y - ARM_OVERLAP
minor_arm_y_top = spiral_outer_end[1] + ARM_OVERLAP
minor_arm_y_span = abs(minor_arm_y_top - minor_arm_y_bot)
minor_arm_y_ctr = (minor_arm_y_top + minor_arm_y_bot) / 2
minor_arm_x_left = MINOR_OFFSET_X - minor_outer_x / 2 + MINOR_WALL
minor_arm_x_right = spiral_outer_end[0] + ARM_WIDTH / 2
minor_arm_x_span = abs(minor_arm_x_right - minor_arm_x_left)
minor_arm_x_ctr = (minor_arm_x_left + minor_arm_x_right) / 2

spiral_z_ctr = SPIRAL_Z_BOT + SPIRAL_STRIP_W / 2

# Approximate beam path length for reporting
mean_r = (SPIRAL_R_INNER + SPIRAL_R_OUTER) / 2
path_length = 2 * math.pi * mean_r * SPIRAL_TURNS

# ============================================================
# Build
# ============================================================

with BuildPart() as part:

    # 1. Main sleeve — outer shell with hybrid bore
    main_z_ctr = (MAIN_SLEEVE_Z_BOT + MAIN_SLEEVE_Z_TOP) / 2
    with Locations([(0, main_center_y, main_z_ctr)]):
        Box(main_outer_x, main_outer_y, main_height)

    cyl_z_bot = MAIN_SLEEVE_Z_BOT - 1.0
    cyl_z_top = MAIN_SLEEVE_Z_TOP - MAIN_RECT_HEIGHT
    cyl_h = cyl_z_top - cyl_z_bot
    cyl_z_ctr = (cyl_z_bot + cyl_z_top) / 2
    with Locations([(0, 0, cyl_z_ctr)]):
        Cylinder(main_cyl_bore / 2, cyl_h, mode=Mode.SUBTRACT)

    rect_z_bot = MAIN_SLEEVE_Z_TOP - MAIN_RECT_HEIGHT
    rect_z_top = MAIN_SLEEVE_Z_TOP + 1.0
    rect_h = rect_z_top - rect_z_bot
    rect_z_ctr = (rect_z_bot + rect_z_top) / 2
    with Locations([(0, 0, rect_z_ctr)]):
        Box(main_rect_inner_x, main_rect_inner_y, rect_h, mode=Mode.SUBTRACT)

    # 2. Minor sleeve body
    minor_z_ctr = (MINOR_SLEEVE_Z_BOT + MINOR_SLEEVE_Z_TOP) / 2
    with Locations([(MINOR_OFFSET_X, MINOR_OFFSET_Y, minor_z_ctr)]):
        Box(minor_outer_x, minor_outer_y, minor_height)

    minor_pocket_top = MINOR_BASE_Z + MINOR_POST_Z
    minor_pocket_bot = MINOR_SLEEVE_Z_BOT - 1.0
    minor_pocket_h = minor_pocket_top - minor_pocket_bot
    minor_pocket_z = (minor_pocket_top + minor_pocket_bot) / 2
    with Locations([(MINOR_OFFSET_X, MINOR_OFFSET_Y, minor_pocket_z)]):
        Box(minor_inner_x, minor_inner_y, minor_pocket_h, mode=Mode.SUBTRACT)

    # 3. Minor sleeve +Y wing
    with Locations([(MINOR_OFFSET_X, wing_y_pos, wing_z_ctr)]):
        Box(minor_outer_x, MINOR_WALL, wing_height)

    # 4. Spiral spring — flat Archimedean spiral extruded in Z
    outline = spiral_outline_points()
    with BuildSketch(Plane.XY.offset(SPIRAL_Z_BOT)):
        with BuildLine():
            Polyline(*outline, close=True)
        make_face()
    extrude(amount=SPIRAL_STRIP_W)

    # 5. Main arm — connects spiral inner end to main sleeve -Y wall
    with Locations([(main_arm_x, main_arm_y_ctr, spiral_z_ctr)]):
        Box(ARM_WIDTH, main_arm_y_span, SPIRAL_STRIP_W)

    # 6. Minor arm — connects spiral outer end to minor sleeve +Y wall
    with Locations([(minor_arm_x_ctr, minor_arm_y_ctr, spiral_z_ctr)]):
        Box(minor_arm_x_span, minor_arm_y_span, SPIRAL_STRIP_W)

# ============================================================
# Reference posts (visualization only)
# ============================================================

with BuildPart() as ref_main:
    cyl_ref_h = MAIN_POST_Z - 2.0
    with Locations([(0, 0, cyl_ref_h / 2)]):
        Cylinder(MAIN_POST_CYL_DIAM / 2, cyl_ref_h)
    with Locations([(0, 0, MAIN_POST_Z - 1.0)]):
        Box(MAIN_POST_RECT_X, MAIN_POST_RECT_Y, 2.0)

with BuildPart() as ref_minor:
    rz = MINOR_BASE_Z + MINOR_POST_Z / 2
    with Locations([(MINOR_OFFSET_X, MINOR_OFFSET_Y, rz)]):
        Box(MINOR_POST_X, MINOR_POST_Y, MINOR_POST_Z)

# ============================================================
# Export
# ============================================================

export_stl(part.part, str(OUTPUT_DIR / "v5_spiral_spring.stl"))
export_step(part.part, str(OUTPUT_DIR / "v5_spiral_spring.step"))

bb = part.part.bounding_box()
print("V5 spiral spring built")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print(f"  Volume: {part.part.volume:.1f} mm³")
print(f"  Spiral: {SPIRAL_TURNS} turns, R={SPIRAL_R_INNER:.0f}–{SPIRAL_R_OUTER:.0f}mm")
print(f"    strip: {SPIRAL_STRIP_T:.1f}mm thick x {SPIRAL_STRIP_W:.1f}mm wide")
print(f"    path length: ~{path_length:.0f}mm")
print(f"    center: ({SPIRAL_CX:.1f}, {SPIRAL_CY:.1f}), Z={SPIRAL_Z_BOT:.1f}–{SPIRAL_Z_TOP:.1f}")
print(f"  Main arm: {ARM_WIDTH:.1f} x {main_arm_y_span:.1f} mm")
print(f"  Minor arm: {minor_arm_x_span:.1f} x {minor_arm_y_span:.1f} mm")

if HAS_VIEWER:
    show(part, ref_main, ref_minor,
         names=["v5_spiral", "main_post_ref", "minor_post_ref"])

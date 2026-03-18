"""
Door Latch Spring — V6 Spiral with Under-Arm Connection

Changes from V5:
  - Removed the main arm that cut horizontally through the spiral
    (which fused half the coil and concentrated all strain on the
    remaining free portion).
  - Inner radius widened (2→3mm) to make room for a center hub.
  - New connection path: hub inside innermost coil → vertical post
    dropping to Z=2.5 → horizontal arm underneath the spiral to
    the main sleeve. The entire spiral is now free to flex.
  - Minor arm unchanged (to be revisited separately).

Print orientation: Z-up. The spiral prints flat in the XY plane.

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
SPIRAL_CX = -1.65
SPIRAL_CY = -10.0
SPIRAL_Z_BOT = 12.5
SPIRAL_STRIP_W = 2.5           # strip width (Z)
SPIRAL_STRIP_T = 0.8           # strip thickness (radial, flex dimension)
SPIRAL_R_INNER = 3.0           # widened from V5 to fit center hub
SPIRAL_R_OUTER = 5.5
SPIRAL_TURNS = 1.5
SPIRAL_N_PTS = 90

# Center column (unified hub + post — single solid piece from bottom arm to spiral top)
COL_X = 2.5                    # column width (same as old hub)
COL_Y = 3.5                    # column depth (extends from spiral center toward spiral start)
COL_Z_BOT = 2.5                # column bottom Z

# Bottom arm (runs underneath the spiral to the main sleeve)
BOTTOM_ARM_WIDTH = 3.0          # X width
BOTTOM_ARM_DEPTH = 8.0          # Z depth — fills most of the gap below the spiral
BOTTOM_ARM_Z_BOT = 2.0

# Minor arm (spiral outer end to minor sleeve — unchanged from V5)
MINOR_ARM_WIDTH = 2.5
MINOR_ARM_OVERLAP = 1.0

# ============================================================
# Computed
# ============================================================

SPIRAL_Z_TOP = SPIRAL_Z_BOT + SPIRAL_STRIP_W
SPIRAL_TOTAL_ANGLE = SPIRAL_TURNS * 2 * math.pi
spiral_z_ctr = SPIRAL_Z_BOT + SPIRAL_STRIP_W / 2

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

# Center column (unified hub + post)
col_y_bot = SPIRAL_CY                         # aligned with spiral center
col_y_top = SPIRAL_CY + COL_Y                 # extends toward spiral start
col_y_ctr = (col_y_bot + col_y_top) / 2
col_z_top = SPIRAL_Z_TOP                      # runs all the way to spiral top
col_z_height = col_z_top - COL_Z_BOT
col_z_ctr = (COL_Z_BOT + col_z_top) / 2

# Bottom arm: from center column to main sleeve -Y wall, underneath the spiral
bottom_arm_z_top = BOTTOM_ARM_Z_BOT + BOTTOM_ARM_DEPTH
bottom_arm_z_ctr = (BOTTOM_ARM_Z_BOT + bottom_arm_z_top) / 2
bottom_arm_y_bot = col_y_bot - 0.5            # 0.5mm overlap into column
bottom_arm_y_top = main_neg_y + 1.0           # 1mm into main sleeve wall
bottom_arm_y_span = abs(bottom_arm_y_top - bottom_arm_y_bot)
bottom_arm_y_ctr = (bottom_arm_y_top + bottom_arm_y_bot) / 2
bottom_arm_x = (SPIRAL_CX + 0) / 2           # biased toward -X for solid wall overlap

# Spiral geometry
def spiral_point(t):
    theta = t * SPIRAL_TOTAL_ANGLE
    r = SPIRAL_R_INNER + (SPIRAL_R_OUTER - SPIRAL_R_INNER) * t
    x = SPIRAL_CX - r * math.sin(theta)
    y = SPIRAL_CY + r * math.cos(theta)
    return (x, y)

def spiral_outline_points():
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

# Minor arm (same approach as V5)
spiral_outer_end = spiral_point(1)
minor_arm_y_bot = minor_pos_y - MINOR_ARM_OVERLAP
minor_arm_y_top = spiral_outer_end[1] + MINOR_ARM_OVERLAP
minor_arm_y_span = abs(minor_arm_y_top - minor_arm_y_bot)
minor_arm_y_ctr = (minor_arm_y_top + minor_arm_y_bot) / 2
minor_arm_x_left = MINOR_OFFSET_X - minor_outer_x / 2 + MINOR_WALL
minor_arm_x_right = spiral_outer_end[0] + MINOR_ARM_WIDTH / 2
minor_arm_x_span = abs(minor_arm_x_right - minor_arm_x_left)
minor_arm_x_ctr = (minor_arm_x_left + minor_arm_x_right) / 2

# Approximate beam path length
mean_r = (SPIRAL_R_INNER + SPIRAL_R_OUTER) / 2
path_length = 2 * math.pi * mean_r * SPIRAL_TURNS

# ============================================================
# Build
# ============================================================

with BuildPart() as part:

    # 1. Main sleeve
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

    # 4. Spiral spring
    outline = spiral_outline_points()
    with BuildSketch(Plane.XY.offset(SPIRAL_Z_BOT)):
        with BuildLine():
            Polyline(*outline, close=True)
        make_face()
    extrude(amount=SPIRAL_STRIP_W)

    # 5. Center column — unified hub + post, from bottom arm level to spiral top
    with Locations([(SPIRAL_CX, col_y_ctr, col_z_ctr)]):
        Box(COL_X, COL_Y, col_z_height)

    # 7. Bottom arm — horizontal bar underneath the spiral, to main sleeve
    with Locations([(bottom_arm_x, bottom_arm_y_ctr, bottom_arm_z_ctr)]):
        Box(BOTTOM_ARM_WIDTH, bottom_arm_y_span, BOTTOM_ARM_DEPTH)

    # 8. Minor arm — connects spiral outer end to minor sleeve +Y wall
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

export_stl(part.part, str(OUTPUT_DIR / "v6_spiral_underarm.stl"))
export_step(part.part, str(OUTPUT_DIR / "v6_spiral_underarm.step"))

bb = part.part.bounding_box()
print("V6 spiral with under-arm built")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print(f"  Volume: {part.part.volume:.1f} mm³")
print(f"  Spiral: {SPIRAL_TURNS} turns, R={SPIRAL_R_INNER:.0f}–{SPIRAL_R_OUTER:.0f}mm")
print(f"    strip: {SPIRAL_STRIP_T:.1f}mm thick x {SPIRAL_STRIP_W:.1f}mm wide")
print(f"    path length: ~{path_length:.0f}mm")
print(f"    center: ({SPIRAL_CX:.1f}, {SPIRAL_CY:.1f}), Z={SPIRAL_Z_BOT:.1f}–{SPIRAL_Z_TOP:.1f}")
print(f"  Column: {COL_X:.1f} x {COL_Y:.1f} mm, Z={COL_Z_BOT:.1f}–{col_z_top:.1f}")
print(f"  Bottom arm: {BOTTOM_ARM_WIDTH:.0f} x {bottom_arm_y_span:.1f} x {BOTTOM_ARM_DEPTH:.0f} mm at Z={BOTTOM_ARM_Z_BOT:.0f}–{bottom_arm_z_top:.0f}")
print(f"  Minor arm: {minor_arm_x_span:.1f} x {minor_arm_y_span:.1f} mm (at spiral Z)")

if HAS_VIEWER:
    show(part, ref_main, ref_minor,
         names=["v6_spiral_underarm", "main_post_ref", "minor_post_ref"])

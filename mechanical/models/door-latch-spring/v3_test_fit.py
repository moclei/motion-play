"""
Door Latch Spring — V3 Test Fit

Changes from V2:
  - Main sleeve bore: cylindrical (Ø5.2mm) for lower 11mm to clear the
    widened cylindrical portion of the post. Rectangular pocket only at
    the top 2mm where the post narrows to its rectangular cross-section.
  - Minor sleeve X offset flipped to -X (was mirrored in V2).

Main sleeve: TUBE (open both ends), hybrid bore.
Minor sleeve: CUP (open bottom, capped top).
Connection bar: rigid link between -Y/+Y walls.

Print orientation: Z-up (flat on build plate).

Coordinate system:
  Origin = center of main post at mechanism base (Z=0)
  X = across mechanism width
  Y = along mechanism (-Y toward minor post)
  Z = mechanism depth (upward from base plate)

See: mechanical/FDM_DESIGN_RULES.md
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
# Measured dimensions (from mechanism)
# ============================================================

MAIN_POST_RECT_X = 4.95       # rectangular section at top of post
MAIN_POST_RECT_Y = 3.50
MAIN_POST_CYL_DIAM = 4.9      # cylindrical section for most of post
MAIN_POST_Z = 12.0

MINOR_POST_X = 4.40
MINOR_POST_Y = 2.00
MINOR_POST_Z = 2.50
MINOR_BASE_Z = 11.0

MINOR_OFFSET_X = -3.3         # -X direction (flipped from V2)
MINOR_OFFSET_Y = -18.0

# ============================================================
# Design parameters — adjust these between test prints
# ============================================================

CLEARANCE = 0.15              # per-side (snug/sliding fit)

# Main sleeve (tube — open both ends, hybrid bore)
MAIN_WALL = 2.0               # -X, +X, -Y wall thickness
MAIN_WALL_THIN = 1.5          # +Y wall (tight clearance in mechanism)
MAIN_SLEEVE_Z_BOT = 2.0       # bottom of tube
MAIN_SLEEVE_Z_TOP = 15.0      # top of tube
MAIN_RECT_HEIGHT = 2.0        # top portion with rectangular pocket

# Minor sleeve (cup — open bottom, capped top)
MINOR_WALL = 2.0
MINOR_CAP = 1.5
MINOR_SLEEVE_Z_BOT = 10.5
MINOR_SLEEVE_Z_TOP = MINOR_BASE_Z + MINOR_POST_Z + MINOR_CAP

# Connection bar
BAR_WIDTH = 3.0
BAR_DEPTH = 3.0

# ============================================================
# Computed
# ============================================================

# Main sleeve — outer shell sized for the rectangular section
main_rect_inner_x = MAIN_POST_RECT_X + 2 * CLEARANCE
main_rect_inner_y = MAIN_POST_RECT_Y + 2 * CLEARANCE
main_outer_x = main_rect_inner_x + 2 * MAIN_WALL
main_outer_y = main_rect_inner_y + MAIN_WALL + MAIN_WALL_THIN
main_center_y = -(MAIN_WALL - MAIN_WALL_THIN) / 2
main_height = MAIN_SLEEVE_Z_TOP - MAIN_SLEEVE_Z_BOT

main_cyl_bore = MAIN_POST_CYL_DIAM + 2 * CLEARANCE
main_cyl_height = main_height - MAIN_RECT_HEIGHT

main_neg_y = -(main_rect_inner_y / 2) - MAIN_WALL

# Minor sleeve
minor_inner_x = MINOR_POST_X + 2 * CLEARANCE
minor_inner_y = MINOR_POST_Y + 2 * CLEARANCE
minor_outer_x = minor_inner_x + 2 * MINOR_WALL
minor_outer_y = minor_inner_y + 2 * MINOR_WALL
minor_height = MINOR_SLEEVE_Z_TOP - MINOR_SLEEVE_Z_BOT
minor_pos_y = MINOR_OFFSET_Y + minor_outer_y / 2

# Connection bar
bar_x = (0 + MINOR_OFFSET_X) / 2
bar_y_top = main_neg_y
bar_y_bot = minor_pos_y
bar_y_span = abs(bar_y_top - bar_y_bot)
bar_y_ctr = (bar_y_top + bar_y_bot) / 2
bar_z_ctr = (MAIN_SLEEVE_Z_TOP + MINOR_SLEEVE_Z_BOT) / 2

# ============================================================
# Build
# ============================================================

with BuildPart() as part:

    # 1. Main sleeve — outer shell
    main_z_ctr = (MAIN_SLEEVE_Z_BOT + MAIN_SLEEVE_Z_TOP) / 2
    with Locations([(0, main_center_y, main_z_ctr)]):
        Box(main_outer_x, main_outer_y, main_height)

    # Cylindrical bore — lower portion (open bottom)
    cyl_z_bot = MAIN_SLEEVE_Z_BOT - 1.0
    cyl_z_top = MAIN_SLEEVE_Z_TOP - MAIN_RECT_HEIGHT
    cyl_h = cyl_z_top - cyl_z_bot
    cyl_z_ctr = (cyl_z_bot + cyl_z_top) / 2
    with Locations([(0, 0, cyl_z_ctr)]):
        Cylinder(main_cyl_bore / 2, cyl_h, mode=Mode.SUBTRACT)

    # Rectangular pocket — top portion (open top)
    rect_z_bot = MAIN_SLEEVE_Z_TOP - MAIN_RECT_HEIGHT
    rect_z_top = MAIN_SLEEVE_Z_TOP + 1.0
    rect_h = rect_z_top - rect_z_bot
    rect_z_ctr = (rect_z_bot + rect_z_top) / 2
    with Locations([(0, 0, rect_z_ctr)]):
        Box(main_rect_inner_x, main_rect_inner_y, rect_h, mode=Mode.SUBTRACT)

    # 2. Minor sleeve — cup (open bottom, capped top)
    minor_z_ctr = (MINOR_SLEEVE_Z_BOT + MINOR_SLEEVE_Z_TOP) / 2
    with Locations([(MINOR_OFFSET_X, MINOR_OFFSET_Y, minor_z_ctr)]):
        Box(minor_outer_x, minor_outer_y, minor_height)

    minor_pocket_top = MINOR_BASE_Z + MINOR_POST_Z
    minor_pocket_bot = MINOR_SLEEVE_Z_BOT - 1.0
    minor_pocket_h = minor_pocket_top - minor_pocket_bot
    minor_pocket_z = (minor_pocket_top + minor_pocket_bot) / 2
    with Locations([(MINOR_OFFSET_X, MINOR_OFFSET_Y, minor_pocket_z)]):
        Box(minor_inner_x, minor_inner_y, minor_pocket_h, mode=Mode.SUBTRACT)

    # 3. Connection bar
    with Locations([(bar_x, bar_y_ctr, bar_z_ctr)]):
        Box(BAR_WIDTH, bar_y_span, BAR_DEPTH)

# ============================================================
# Reference posts (visualization only)
# ============================================================

with BuildPart() as ref_main:
    cyl_ref_h = MAIN_POST_Z - 2.0
    with Locations([(0, 0, cyl_ref_h / 2)]):
        Cylinder(MAIN_POST_CYL_DIAM / 2, cyl_ref_h)
    rect_ref_z = MAIN_POST_Z - 1.0
    with Locations([(0, 0, rect_ref_z)]):
        Box(MAIN_POST_RECT_X, MAIN_POST_RECT_Y, 2.0)

with BuildPart() as ref_minor:
    rz = MINOR_BASE_Z + MINOR_POST_Z / 2
    with Locations([(MINOR_OFFSET_X, MINOR_OFFSET_Y, rz)]):
        Box(MINOR_POST_X, MINOR_POST_Y, MINOR_POST_Z)

# ============================================================
# Export
# ============================================================

export_stl(part.part, str(OUTPUT_DIR / "v3_test_fit.stl"))
export_step(part.part, str(OUTPUT_DIR / "v3_test_fit.step"))

bb = part.part.bounding_box()
print("V3 test fit built")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print(f"  Volume: {part.part.volume:.1f} mm³")
print(f"  Main sleeve: {main_outer_x:.1f} x {main_outer_y:.1f} x {main_height:.1f} mm")
print(f"    cylindrical bore: Ø{main_cyl_bore:.2f} mm, {main_cyl_height:.0f}mm tall")
print(f"    rectangular top:  {main_rect_inner_x:.2f} x {main_rect_inner_y:.2f} mm, {MAIN_RECT_HEIGHT:.0f}mm tall")
print(f"  Minor sleeve: {minor_outer_x:.1f} x {minor_outer_y:.1f} x {minor_height:.1f} mm")
print(f"    at X={MINOR_OFFSET_X:+.1f}, Y={MINOR_OFFSET_Y:.1f}")
print(f"  Bar: {BAR_WIDTH:.0f} x {bar_y_span:.1f} x {BAR_DEPTH:.0f} mm at Z={bar_z_ctr:.1f}")

if HAS_VIEWER:
    show(part, ref_main, ref_minor,
         names=["v3_test_fit", "main_post_ref", "minor_post_ref"])

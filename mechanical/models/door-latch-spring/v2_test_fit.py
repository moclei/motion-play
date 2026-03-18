"""
Door Latch Spring — V2 Test Fit

Sleeve-only test piece for validating post fit and inter-post spacing.
No spring/tension mechanism — just two sleeves connected by a simple
rigid bar. Print this, try it on the mechanism, and adjust dimensions
before adding the flexure in a later version.

Main sleeve: TUBE (open both ends) — slides over the fixed 12mm post.
Minor sleeve: CUP (open bottom, capped top) — caps onto the 2.5mm post.
Connection bar: rigid link on the -Y/+Y walls, does NOT cover the
  sleeve openings so both posts can be inserted.

Assembly: tilt/angle the part to get both posts into their sleeves.
The main sleeve is a tube so the post can enter from either end.

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

MAIN_POST_X = 4.95
MAIN_POST_Y = 3.50
MAIN_POST_Z = 12.0

MINOR_POST_X = 4.40
MINOR_POST_Y = 2.00
MINOR_POST_Z = 2.50
MINOR_BASE_Z = 11.0

MINOR_OFFSET_X = 3.3
MINOR_OFFSET_Y = -18.0

# ============================================================
# Design parameters — adjust these between test prints
# ============================================================

CLEARANCE = 0.15          # per-side (snug/sliding fit)

# Main sleeve (tube — open both ends)
MAIN_WALL = 2.0           # -X, +X, -Y wall thickness
MAIN_WALL_THIN = 1.5      # +Y wall (tight clearance in mechanism)
MAIN_SLEEVE_Z_BOT = 2.0   # bottom of tube
MAIN_SLEEVE_Z_TOP = 15.0  # top of tube — raised to align with minor sleeve top

# Minor sleeve (cup — open bottom, capped top)
MINOR_WALL = 2.0
MINOR_CAP = 1.5
MINOR_SLEEVE_Z_BOT = 10.5 # open bottom — post enters here
MINOR_SLEEVE_Z_TOP = MINOR_BASE_Z + MINOR_POST_Z + MINOR_CAP  # 15.0

# Connection bar
BAR_WIDTH = 3.0           # X dimension
BAR_DEPTH = 3.0           # Z dimension

# ============================================================
# Computed
# ============================================================

main_inner_x = MAIN_POST_X + 2 * CLEARANCE
main_inner_y = MAIN_POST_Y + 2 * CLEARANCE
main_outer_x = main_inner_x + 2 * MAIN_WALL
main_outer_y = main_inner_y + MAIN_WALL + MAIN_WALL_THIN
main_center_y = -(MAIN_WALL - MAIN_WALL_THIN) / 2
main_height = MAIN_SLEEVE_Z_TOP - MAIN_SLEEVE_Z_BOT

main_neg_y = -(main_inner_y / 2) - MAIN_WALL

minor_inner_x = MINOR_POST_X + 2 * CLEARANCE
minor_inner_y = MINOR_POST_Y + 2 * CLEARANCE
minor_outer_x = minor_inner_x + 2 * MINOR_WALL
minor_outer_y = minor_inner_y + 2 * MINOR_WALL
minor_height = MINOR_SLEEVE_Z_TOP - MINOR_SLEEVE_Z_BOT

minor_pos_y = MINOR_OFFSET_Y + minor_outer_y / 2

# Bar spans between the two sleeve walls in Y, centered in X
# between the two posts, at a Z level within both sleeves.
bar_x = (0 + MINOR_OFFSET_X) / 2
bar_y_top = main_neg_y          # meets main sleeve -Y outer wall
bar_y_bot = minor_pos_y         # meets minor sleeve +Y outer wall
bar_y_span = abs(bar_y_top - bar_y_bot)
bar_y_ctr = (bar_y_top + bar_y_bot) / 2

# Z: centered where both sleeves overlap (main top area / minor bottom area)
bar_z_ctr = (MAIN_SLEEVE_Z_TOP + MINOR_SLEEVE_Z_BOT) / 2

# ============================================================
# Build
# ============================================================

with BuildPart() as part:

    # 1. Main sleeve — tube (open top and bottom)
    main_z_ctr = (MAIN_SLEEVE_Z_BOT + MAIN_SLEEVE_Z_TOP) / 2
    with Locations([(0, main_center_y, main_z_ctr)]):
        Box(main_outer_x, main_outer_y, main_height)
    with Locations([(0, 0, main_z_ctr)]):
        Box(main_inner_x, main_inner_y, main_height + 2, mode=Mode.SUBTRACT)

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

    # 3. Connection bar — rigid link between sleeve walls
    #    Attaches to -Y wall of main sleeve and +Y wall of minor sleeve.
    #    Sits to the side of both openings, does not obstruct post entry.
    with Locations([(bar_x, bar_y_ctr, bar_z_ctr)]):
        Box(BAR_WIDTH, bar_y_span, BAR_DEPTH)

# ============================================================
# Reference posts (visualization only)
# ============================================================

with BuildPart() as ref_main:
    with Locations([(0, 0, MAIN_POST_Z / 2)]):
        Box(MAIN_POST_X, MAIN_POST_Y, MAIN_POST_Z)

with BuildPart() as ref_minor:
    rz = MINOR_BASE_Z + MINOR_POST_Z / 2
    with Locations([(MINOR_OFFSET_X, MINOR_OFFSET_Y, rz)]):
        Box(MINOR_POST_X, MINOR_POST_Y, MINOR_POST_Z)

# ============================================================
# Export
# ============================================================

export_stl(part.part, str(OUTPUT_DIR / "v2_test_fit.stl"))
export_step(part.part, str(OUTPUT_DIR / "v2_test_fit.step"))

bb = part.part.bounding_box()
print("V2 test fit built")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print(f"  Volume: {part.part.volume:.1f} mm³")
print(f"  Main sleeve (tube): {main_outer_x:.1f} x {main_outer_y:.1f} x {main_height:.1f} mm")
print(f"    pocket: {main_inner_x:.2f} x {main_inner_y:.2f} mm (open both ends)")
print(f"    Z: {MAIN_SLEEVE_Z_BOT:.0f}–{MAIN_SLEEVE_Z_TOP:.0f} mm")
print(f"  Minor sleeve (cup): {minor_outer_x:.1f} x {minor_outer_y:.1f} x {minor_height:.1f} mm")
print(f"    pocket: {minor_inner_x:.2f} x {minor_inner_y:.2f} mm (open bottom, cap top)")
print(f"    Z: {MINOR_SLEEVE_Z_BOT:.1f}–{MINOR_SLEEVE_Z_TOP:.1f} mm")
print(f"  Bar: {BAR_WIDTH:.0f} x {bar_y_span:.1f} x {BAR_DEPTH:.0f} mm at Z={bar_z_ctr:.1f}")

if HAS_VIEWER:
    show(part, ref_main, ref_minor,
         names=["v2_test_fit", "main_post_ref", "minor_post_ref"])

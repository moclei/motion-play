"""
Door Latch Spring — V4 Flex Bars Experiment

Changes from V3:
  - Minor sleeve body extended 1mm lower (Z_BOT 10.5 → 9.5).
  - Minor sleeve +Y wall extends all the way down to match the main
    sleeve (Z=2), creating a tall wing for bar attachment.
  - Single rigid bar replaced with 3 thin bars spaced vertically,
    as a first experiment toward a flexible spring connection.

NOTE on flex: straight bars spanning ~11mm will be quite stiff against
the full 9.9mm of knob travel. They may flex 1-3mm before hitting PLA
strain limits. This version tests the concept — if they're too rigid,
the next step is adding zigzag/serpentine segments to increase the
effective beam length.

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
MINOR_SLEEVE_Z_BOT = 9.5       # extended 1mm lower than V3
MINOR_SLEEVE_Z_TOP = MINOR_BASE_Z + MINOR_POST_Z + MINOR_CAP
MINOR_WING_Z_BOT = MAIN_SLEEVE_Z_BOT  # +Y wing extends down to match main sleeve

# Flex bars (3 thin bars connecting the sleeves)
N_BARS = 3
BAR_THICK = 1.0               # X dimension — flex direction
BAR_DEPTH = 2.5               # Z dimension per bar
BAR_Z_MARGIN = 1.5            # clearance from sleeve top/bottom edges

# ============================================================
# Computed
# ============================================================

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

# Wing: extends the +Y wall of the minor sleeve down to MINOR_WING_Z_BOT
wing_z_top = MINOR_SLEEVE_Z_BOT          # starts where the main body ends
wing_z_bot = MINOR_WING_Z_BOT            # goes down to match main sleeve
wing_height = wing_z_top - wing_z_bot
wing_z_ctr = (wing_z_top + wing_z_bot) / 2
wing_x = minor_outer_x                   # same width as minor sleeve
wing_y = MINOR_WALL                      # wall thickness
wing_y_pos = minor_pos_y - MINOR_WALL / 2  # centered on the +Y outer wall

# Bar geometry — spans from main sleeve -Y wall to minor sleeve +Y wing
bar_y_top = main_neg_y
bar_y_bot = minor_pos_y
bar_y_span = abs(bar_y_top - bar_y_bot)
bar_y_ctr = (bar_y_top + bar_y_bot) / 2
bar_x = (0 + MINOR_OFFSET_X) / 2         # centered between post centers

# Space bars evenly across the available Z range (wing + sleeve overlap)
bar_z_range_bot = MINOR_WING_Z_BOT + BAR_Z_MARGIN
bar_z_range_top = MAIN_SLEEVE_Z_TOP - BAR_Z_MARGIN
bar_z_spacing = (bar_z_range_top - bar_z_range_bot) / (N_BARS - 1)
bar_z_centers = [bar_z_range_bot + i * bar_z_spacing for i in range(N_BARS)]

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

    # 2. Minor sleeve body — cup (open bottom, capped top)
    minor_z_ctr = (MINOR_SLEEVE_Z_BOT + MINOR_SLEEVE_Z_TOP) / 2
    with Locations([(MINOR_OFFSET_X, MINOR_OFFSET_Y, minor_z_ctr)]):
        Box(minor_outer_x, minor_outer_y, minor_height)

    minor_pocket_top = MINOR_BASE_Z + MINOR_POST_Z
    minor_pocket_bot = MINOR_SLEEVE_Z_BOT - 1.0
    minor_pocket_h = minor_pocket_top - minor_pocket_bot
    minor_pocket_z = (minor_pocket_top + minor_pocket_bot) / 2
    with Locations([(MINOR_OFFSET_X, MINOR_OFFSET_Y, minor_pocket_z)]):
        Box(minor_inner_x, minor_inner_y, minor_pocket_h, mode=Mode.SUBTRACT)

    # 3. Minor sleeve +Y wing — tall wall extending down to match main sleeve
    with Locations([(MINOR_OFFSET_X, wing_y_pos, wing_z_ctr)]):
        Box(wing_x, wing_y, wing_height)

    # 4. Three flex bars — thin beams connecting the sleeves
    for z in bar_z_centers:
        with Locations([(bar_x, bar_y_ctr, z)]):
            Box(BAR_THICK, bar_y_span, BAR_DEPTH)

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

export_stl(part.part, str(OUTPUT_DIR / "v4_flex_bars.stl"))
export_step(part.part, str(OUTPUT_DIR / "v4_flex_bars.step"))

bb = part.part.bounding_box()
print("V4 flex bars built")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print(f"  Volume: {part.part.volume:.1f} mm³")
print(f"  Main sleeve: {main_outer_x:.1f} x {main_outer_y:.1f} x {main_height:.1f} mm")
print(f"  Minor sleeve body: {minor_outer_x:.1f} x {minor_outer_y:.1f} x {minor_height:.1f} mm")
print(f"    Z: {MINOR_SLEEVE_Z_BOT:.1f}–{MINOR_SLEEVE_Z_TOP:.1f}")
print(f"  Minor +Y wing: {wing_x:.1f} x {wing_y:.1f} x {wing_height:.1f} mm (Z={MINOR_WING_Z_BOT:.0f}–{wing_z_top:.1f})")
print(f"  Bars: {N_BARS}x {BAR_THICK:.1f} x {bar_y_span:.1f} x {BAR_DEPTH:.1f} mm")
print(f"    at Z = {', '.join(f'{z:.1f}' for z in bar_z_centers)}")

if HAS_VIEWER:
    show(part, ref_main, ref_minor,
         names=["v4_flex_bars", "main_post_ref", "minor_post_ref"])

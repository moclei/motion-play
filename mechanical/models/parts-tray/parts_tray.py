"""
Parts Tray — Bench Storage for Loose Workshop Parts

Open-top tray for keeping wire harnesses, M2 screws, small electronics
and other loose bits within reach while building. Sized to also accept
a couple of 18650 batteries in the largest compartment.

Layout (5 compartments):
  - Big (left half):              ~73 × 96 mm — fits 2× 18650 batteries
  - Medium (top-right):           ~73 × 38 mm — wire harnesses, larger parts
  - Three small (bottom-right):   ~23 × 58 mm each — screws, headers, SMD parts

Flourish:
  - Rounded outer corners (R5) — softens the brick silhouette.
  - Finger-scoop dip carved into every divider top — functional (sweep
    parts up with a finger) and gives the tray a sculpted profile.
  - Three-dot deboss on the floor of the big compartment, arranged at
    120° — a quiet nod to the Motion Play three-sensor module layout.

Print orientation:
  Floor down on the build plate, open top facing +Z. No supports needed
  (scoop overhangs are concave half-pipes, self-supporting). PETG for
  durability or PLA for a quick print — wall thicknesses suit either.

Coordinate system:
  Origin = center of the tray's outer footprint, on top of the build plate.
  X = long axis (150mm), Y = short axis (100mm), Z = up.

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
# Dimensions
# ============================================================

OUTER_X = 150.0
OUTER_Y = 100.0
HEIGHT  = 30.0

OUTER_WALL = 1.6                  # 4 perimeters @ 0.4mm nozzle
INNER_WALL = 1.2                  # 3 perimeters
FLOOR      = 1.6
CORNER_R   = 5.0                  # outer corner fillet

# Layout — splits, in absolute coords from -X/2..+X/2 reference
DIV_X = 75.0                      # vertical divider position (X from left edge)
DIV_Y = 60.0                      # horizontal divider position on right side (Y from bottom edge)
N_SMALL = 3                       # number of small compartments in bottom-right row

# Finger-scoop into divider tops — radius >> depth makes it a shallow swoop
SCOOP_R     = 8.0
SCOOP_DEPTH = 10.0

# Logo deboss on big compartment floor (3 dots arranged at 120°)
LOGO_RING_R    = 18.0
LOGO_DOT_R     = 3.5
LOGO_DOT_DEPTH = 0.8

# ============================================================
# Derived layout (centered coords: origin at part center)
# ============================================================

inner_x = OUTER_X - 2 * OUTER_WALL
inner_y = OUTER_Y - 2 * OUTER_WALL
inner_r = max(CORNER_R - OUTER_WALL, 0.5)

div_x_pos    = DIV_X - OUTER_X / 2          # vertical divider center X
div_y_pos_h  = DIV_Y - OUTER_Y / 2          # horizontal divider center Y

div_z_height = HEIGHT - FLOOR
div_z_ctr    = FLOOR + div_z_height / 2

# Right-side region (between vertical divider and right outer wall)
right_x_min = div_x_pos + INNER_WALL / 2
right_x_max = OUTER_X / 2 - OUTER_WALL
right_x_span = right_x_max - right_x_min
right_x_ctr  = (right_x_min + right_x_max) / 2

# Top-right (medium) compartment Y range
top_y_min = div_y_pos_h + INNER_WALL / 2
top_y_max = OUTER_Y / 2 - OUTER_WALL
top_y_span = top_y_max - top_y_min

# Bottom-right row Y range (holds the 3 small compartments)
bot_y_min = -(OUTER_Y / 2 - OUTER_WALL)
bot_y_max = div_y_pos_h - INNER_WALL / 2
bot_y_span = bot_y_max - bot_y_min
bot_y_ctr  = (bot_y_min + bot_y_max) / 2

# Each small compartment width (after subtracting N-1 internal walls)
cell_x_width = (right_x_span - (N_SMALL - 1) * INNER_WALL) / N_SMALL

# Big compartment center (for logo placement)
big_x_min = -OUTER_X / 2 + OUTER_WALL
big_x_max = div_x_pos - INNER_WALL / 2
big_ctr_x = (big_x_min + big_x_max) / 2
big_ctr_y = 0.0
big_x_span = big_x_max - big_x_min
big_y_span = inner_y

# Scoop Z center — bottom of cylinder sits SCOOP_DEPTH below the rim,
# top extends past the rim so it cuts cleanly through.
scoop_z = HEIGHT - SCOOP_DEPTH + SCOOP_R

# ============================================================
# Build
# ============================================================

with BuildPart() as tray:

    # 1. Outer rounded box
    with BuildSketch(Plane.XY):
        RectangleRounded(OUTER_X, OUTER_Y, radius=CORNER_R)
    extrude(amount=HEIGHT)

    # 2. Hollow out the interior — leaves outer walls + floor
    with BuildSketch(Plane.XY.offset(FLOOR)):
        RectangleRounded(inner_x, inner_y, radius=inner_r)
    extrude(amount=HEIGHT, mode=Mode.SUBTRACT)

    # 3. Vertical divider — full inner Y, splits big compartment from right side
    with Locations([(div_x_pos, 0, div_z_ctr)]):
        Box(INNER_WALL, inner_y, div_z_height)

    # 4. Horizontal divider — only on right side, splits top-row from bottom-row
    with Locations([(right_x_ctr, div_y_pos_h, div_z_ctr)]):
        Box(right_x_span, INNER_WALL, div_z_height)

    # 5. Two short vertical dividers within the bottom-right row
    for i in range(1, N_SMALL):
        x_pos = right_x_min + i * cell_x_width + (i - 0.5) * INNER_WALL - INNER_WALL / 2
        with Locations([(x_pos, bot_y_ctr, div_z_ctr)]):
            Box(INNER_WALL, bot_y_span, div_z_height)

    # 6. Finger scoops — half-pipe cuts into the top of every divider.
    # Each cylinder lies horizontal along its divider's long axis.

    # Vertical divider scoop (axis along Y)
    with Locations([(div_x_pos, 0, scoop_z)]):
        Cylinder(SCOOP_R, inner_y,
                 rotation=(90, 0, 0), mode=Mode.SUBTRACT)

    # Horizontal divider scoop (axis along X)
    with Locations([(right_x_ctr, div_y_pos_h, scoop_z)]):
        Cylinder(SCOOP_R, right_x_span,
                 rotation=(0, 90, 0), mode=Mode.SUBTRACT)

    # Small divider scoops (axis along Y, only span bottom row)
    for i in range(1, N_SMALL):
        x_pos = right_x_min + i * cell_x_width + (i - 0.5) * INNER_WALL - INNER_WALL / 2
        with Locations([(x_pos, bot_y_ctr, scoop_z)]):
            Cylinder(SCOOP_R, bot_y_span,
                     rotation=(90, 0, 0), mode=Mode.SUBTRACT)

    # 7. Logo deboss — 3 dots at 120° on the big compartment floor.
    # Sketch sits at (FLOOR - depth) and extrudes UP by depth in subtract mode,
    # so the cut runs from the floor surface down to the indent base.
    with BuildSketch(Plane.XY.offset(FLOOR - LOGO_DOT_DEPTH)):
        for k in range(3):
            ang = math.radians(90 + k * 120)
            dx = LOGO_RING_R * math.cos(ang)
            dy = LOGO_RING_R * math.sin(ang)
            with Locations([(big_ctr_x + dx, big_ctr_y + dy)]):
                Circle(LOGO_DOT_R)
    extrude(amount=LOGO_DOT_DEPTH, mode=Mode.SUBTRACT)

# ============================================================
# Export
# ============================================================

export_stl(tray.part,  str(OUTPUT_DIR / "parts_tray.stl"))
export_step(tray.part, str(OUTPUT_DIR / "parts_tray.step"))

bb = tray.part.bounding_box()
print("Parts Tray")
print(f"  Outer:        {bb.size.X:.1f} × {bb.size.Y:.1f} × {bb.size.Z:.1f} mm")
print(f"  Walls:        outer={OUTER_WALL}mm, inner={INNER_WALL}mm, floor={FLOOR}mm")
print(f"  Big compt:    {big_x_span:.1f} × {big_y_span:.1f} mm  (fits 2× 18650)")
print(f"  Medium top-R: {right_x_span:.1f} × {top_y_span:.1f} mm")
print(f"  Small (×{N_SMALL}):   {cell_x_width:.1f} × {bot_y_span:.1f} mm each")
print(f"  Scoop:        r={SCOOP_R}mm, depth={SCOOP_DEPTH}mm into divider tops")
print(f"  Volume:       {tray.part.volume / 1000:.1f} cm³")
print(f"\nExported: STL, STEP")

if HAS_VIEWER:
    show(tray, names=["parts_tray"])

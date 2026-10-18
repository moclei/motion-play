"""
Drawer Storage Bins — Parametric Family for 12.25" × 12.25" Drawers

Open-top bins for organizing loose electronics (connectors, wires, components,
small baggies) inside plastic bench drawers. All tiles share a 25mm sub-grid,
so they tetris into a 300 × 300 mm footprint inside a 311 × 311 mm drawer
interior (12.25"). Roughly 11mm per side is left for filler to take up slack
and stop bins from sliding when the drawer opens.

Tile sizes (all 55mm tall):
  - 150 × 150  — big square (bulkier parts, coiled wires)
  - 150 × 100  — medium (harnesses, modules)
  - 150 × 75   — long-thin (connector strips, tape reels)
  - 150 × 50   — narrow strip (pin headers, DIP chips)
  - 100 × 100  — small square (tiny components, standoffs)

Example tilings of the 300 × 300 area:
  - Four 150×150                                      (4 bins)
  - Row 1: 2× 150×150, Row 2: 2× 150×100, Row 3: 2× 150×50   (6 bins)
  - Mixed with 100×100 filling remaining 100-wide strips      (7+ bins)

Flourish:
  - R4 rounded outer corners.
  - Semi-circular finger notch cut into one long side — hook a finger over
    the rim to lift the bin out of the drawer.
  - Debossed size label (e.g. "150x100") centered on the inside floor,
    legible from above.

Print orientation:
  Floor down on the build plate, open top facing +Z. No supports needed —
  the notch cylinder is a concave half-pipe (self-supporting under ~45°
  overhang in its lower half). PETG recommended for stiffness; PLA works.

Coordinate system (per bin):
  Origin = center of the outer footprint, on the build plate.
  X = bin width, Y = bin depth, Z = up. Notch is on the +Y wall.

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
# Shared parameters
# ============================================================

HEIGHT     = 55.0                 # was 60 previously — 55 clears drawer lip
WALL       = 2.4                  # 6 perimeters @ 0.4mm nozzle
FLOOR      = 1.6
CORNER_R   = 4.0                  # outer corner fillet

# Finger notch on +Y wall
NOTCH_R     = 12.0                # radius of the half-pipe cut
NOTCH_DEPTH = 12.0                # how far the notch dips from the top rim

# Size label deboss on floor
LABEL_DEPTH = 0.8                 # 2 layers at 0.4mm — clean emboss
LABEL_SIZE  = 9.0                 # text height in mm

# ============================================================
# Bin family — all share 25mm sub-grid for tetris-ability
# ============================================================

BINS = [
    (150, 150),
    (150, 100),
    (150, 75),
    (150, 50),
    (100, 100),
]

# Drawer interior for reference (12.25" square, curved front expands to 13")
DRAWER_INTERIOR = 311.15          # 12.25" in mm
TILE_AREA       = 300.0           # what we tile cleanly; leftover is filler

# ============================================================
# Builder
# ============================================================

def make_bin(w: float, d: float):
    """Build a single bin with given outer width (X) and depth (Y)."""

    inner_w = w - 2 * WALL
    inner_d = d - 2 * WALL
    inner_r = max(CORNER_R - WALL, 0.5)

    # Notch cylinder geometry: axis along Y, sits at the top of the +Y wall.
    # Cylinder center Z is chosen so the cylinder cuts exactly NOTCH_DEPTH
    # below the rim — bottom of the cylinder = HEIGHT - NOTCH_DEPTH.
    notch_z     = HEIGHT - NOTCH_DEPTH + NOTCH_R
    notch_y_ctr = d / 2 - WALL / 2          # centered in the wall thickness
    notch_len   = 3 * WALL                  # cuts cleanly through the wall

    label = f"{int(w)}x{int(d)}"

    with BuildPart() as bin_part:

        # 1. Outer rounded box
        with BuildSketch(Plane.XY):
            RectangleRounded(w, d, radius=CORNER_R)
        extrude(amount=HEIGHT)

        # 2. Hollow the interior
        with BuildSketch(Plane.XY.offset(FLOOR)):
            RectangleRounded(inner_w, inner_d, radius=inner_r)
        extrude(amount=HEIGHT, mode=Mode.SUBTRACT)

        # 3. Finger notch — half-pipe cut into top of +Y wall
        with Locations([(0, notch_y_ctr, notch_z)]):
            Cylinder(NOTCH_R, notch_len,
                     rotation=(90, 0, 0), mode=Mode.SUBTRACT)

        # 4. Size label debossed into the floor (visible from above)
        with BuildSketch(Plane.XY.offset(FLOOR - LABEL_DEPTH)):
            Text(label, font_size=LABEL_SIZE,
                 align=(Align.CENTER, Align.CENTER))
        extrude(amount=LABEL_DEPTH, mode=Mode.SUBTRACT)

    return bin_part.part


# ============================================================
# Build + export every size
# ============================================================

bin_cache = {}

def get_bin(w, d):
    key = (w, d)
    if key not in bin_cache:
        bin_cache[key] = make_bin(w, d)
    return bin_cache[key]


print("Drawer Storage Bins")
print(f"  Drawer interior: {DRAWER_INTERIOR:.1f} × {DRAWER_INTERIOR:.1f} mm  (12.25\")")
print(f"  Tile footprint:  {TILE_AREA:.0f} × {TILE_AREA:.0f} mm  "
      f"(≈{DRAWER_INTERIOR - TILE_AREA:.0f}mm filler on two edges)")
print(f"  Height: {HEIGHT}mm  |  wall: {WALL}mm  |  floor: {FLOOR}mm")
print()

for w, d in BINS:
    part = get_bin(w, d)
    name = f"bin_{int(w)}x{int(d)}"
    export_stl(part,  str(OUTPUT_DIR / f"{name}.stl"))
    export_step(part, str(OUTPUT_DIR / f"{name}.step"))
    vol_cm3 = part.volume / 1000
    print(f"  {name:>14}   outer {w:.0f} × {d:.0f} mm   "
          f"inner {w - 2*WALL:.1f} × {d - 2*WALL:.1f}   "
          f"{vol_cm3:.1f} cm³")

print(f"\nExported {len(BINS)} × STL + STEP to {OUTPUT_DIR}")

# ============================================================
# Demo tiling — shows how 7 bins fill the 300×300 drawer area
# ============================================================
# Rows are stacked in Y. Within each row, bins sit side-by-side in X.
# Layout uses four of the five sizes so the variety is visible.
#
#   y = -150 … -100:  [150×50 ] [150×50 ]                 ← bottom strip row
#   y = -100 …   50:  [150×150] [100×100  ]              ← left big + right column
#                                [100×100  ]
#                                [100×100  ]... wait, reshape below
#
# Final layout (symmetric, all 5 sizes present):
#
#   Top row     (y  75… 150, h=75):  [150×75 ][150×75 ]            (two 150×75)
#   Upper row   (y -25…  75, h=100): [150×100][150×100]            (two 150×100)
#   Center row  (y-125… -25, h=100): [100×100][100×100][100×100]   (three 100×100)
#   Bottom row  (y-150…-125, h=25):  ... only 25mm left, doesn't fit — re-plan
#
# Re-plan (clean fit, 300 tall): 75 + 100 + 75 + 50 = 300
#   Top    (y  75… 150, h=75):  [150×75 ][150×75 ]
#   Upper  (y -25…  75, h=100): [150×100][100×100][100×100]  but 150+100+100=350 ≠ 300 — bad
#
# Simplest balanced showcase:
#   Row 1 (h=150): [150×150]            [150×75 ]            (left big, right slim top)
#                                        [150×75 ]            (right slim bottom, stacked)
#   Row 2 (h=100): [150×100]            [150×100]            (two medium)
#   Row 3 (h=50):  [150×50 ]            [150×50 ]            (two strip)
# Total Y: 150 + 100 + 50 = 300. Uses 4 of 5 sizes (no 100×100).

tiling = [
    # (w, d, center_x, center_y)  — centered on origin, area = 300×300
    (150, 150,  -75,   75),         # top-left big square
    (150,  75,   75,  112.5),        # top-right upper slim
    (150,  75,   75,   37.5),        # top-right lower slim
    (150, 100,  -75,  -50),          # mid-left medium
    (150, 100,   75,  -50),          # mid-right medium
    (150,  50,  -75, -125),          # bottom-left strip
    (150,  50,   75, -125),          # bottom-right strip
]

# Include a 100×100 off to the side so all 5 sizes appear in the viewer
aside = [
    (100, 100, 250, 100),
]

demo_parts = []
demo_names = []
for (w, d, cx, cy) in tiling + aside:
    p = get_bin(w, d).moved(Location((cx, cy, 0)))
    demo_parts.append(p)
    demo_names.append(f"bin_{int(w)}x{int(d)}_@_{cx:+.0f}_{cy:+.0f}")

if HAS_VIEWER:
    show(*demo_parts, names=demo_names)

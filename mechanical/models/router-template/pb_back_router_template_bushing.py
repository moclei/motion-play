"""
PB Back Panel — Router Bushing Template

Adapted from the original pb_back_router_template (SendCutSend laser-cut)
for use with a handheld router and guide bushings. Each template opening
is enlarged by the bushing offset so the routed result matches the original
target dimensions.

Two bushing/bit combos:
  Large rectangles:  3/4" OD bushing  +  3/8" bit  →  offset 4.763mm/side
  Small hole grid:   5/16" OD bushing +  3/16" bit →  offset 1.594mm/side

The small hole grid uses a checkerboard pattern: alternating holes are
enlarged for the bushing ("cutting" holes), while the others remain at
original size for indexing pins or visual reference ("registration" holes).
This keeps adequate wall thickness between adjacent template openings.

Template corners on all bushing holes are radiused to the bushing radius
so the bushing tracks smoothly without catching on sharp corners.

Coordinate system (matching original SVG):
  Origin = center of template plate
  X = width (horizontal)
  Y = height (vertical)
  Z = thickness (+Z = top, bushing entry side)

Output: STEP, STL, SVG
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
# Routing system parameters
# ============================================================

# --- Large rectangles: 3/4" bushing + 3/8" bit ---
LARGE_BUSHING_OD = 19.05           # 3/4" in mm
LARGE_BIT_DIAM = 9.525             # 3/8" in mm
LARGE_OFFSET = (LARGE_BUSHING_OD - LARGE_BIT_DIAM) / 2  # 4.7625mm

# --- Small hole grid: 5/16" bushing + 3/16" bit ---
SMALL_BUSHING_OD = 7.95            # 5/16" in mm (measured)
SMALL_BIT_DIAM = 4.7625            # 3/16" in mm
SMALL_OFFSET = (SMALL_BUSHING_OD - SMALL_BIT_DIAM) / 2  # 1.59375mm

# ============================================================
# Original template geometry (from SVG, all in mm)
# ============================================================

# Outer plate
TEMPLATE_WIDTH = 235.82
TEMPLATE_HEIGHT = 177.13
TEMPLATE_THICKNESS = 3.0            # metal template thickness (adjust for material)

# Red rectangle (left large cutout) — target routed size
RED_RECT_W = 30.801                 # original width
RED_RECT_H = 35.371                 # original height
RED_RECT_CX = -65.19               # center X relative to plate center
RED_RECT_CY = -17.96               # center Y relative to plate center

# Blue rectangle (right large cutout) — target routed size
BLUE_RECT_W = 19.729
BLUE_RECT_H = 137.106
BLUE_RECT_CX = 76.51
BLUE_RECT_CY = -12.50

# Small hole grid — target routed size per hole
SMALL_HOLE_W = 15.425              # original width
SMALL_HOLE_H = 5.273               # original height

# Grid layout: 3 columns × 12 rows
GRID_COLS = 3
GRID_ROWS = 12
COL_SPACING = 22.362               # center-to-center horizontal
ROW_SPACING = 11.995               # center-to-center vertical

# Grid origin (center of col=0, row=0 hole) relative to plate center
GRID_ORIGIN_X = -13.84
GRID_ORIGIN_Y = 52.71              # top row, positive Y = up

# ============================================================
# Bushing-adapted dimensions
# ============================================================

# Large rectangles: enlarge by LARGE_OFFSET on each side
# Corner radius = bushing radius (bushing tracks smoothly around corners)
LARGE_TEMPLATE_RED_W = RED_RECT_W + 2 * LARGE_OFFSET
LARGE_TEMPLATE_RED_H = RED_RECT_H + 2 * LARGE_OFFSET
LARGE_TEMPLATE_BLUE_W = BLUE_RECT_W + 2 * LARGE_OFFSET
LARGE_TEMPLATE_BLUE_H = BLUE_RECT_H + 2 * LARGE_OFFSET
LARGE_CORNER_R = LARGE_BUSHING_OD / 2  # 9.525mm

# Small holes — checkerboard: cutting holes enlarged, registration holes unchanged
SMALL_CUTTING_W = SMALL_HOLE_W + 2 * SMALL_OFFSET
SMALL_CUTTING_H = SMALL_HOLE_H + 2 * SMALL_OFFSET
SMALL_CORNER_R = SMALL_BUSHING_OD / 2  # 3.975mm
SMALL_REG_W = SMALL_HOLE_W          # unchanged
SMALL_REG_H = SMALL_HOLE_H          # unchanged

# ============================================================
# Clearance checks
# ============================================================

# Vertical gap between adjacent small holes (cutting ↔ registration)
vert_gap = ROW_SPACING - SMALL_CUTTING_H / 2 - SMALL_REG_H / 2
# Horizontal gap between adjacent columns (cutting ↔ registration)
horiz_gap = COL_SPACING - SMALL_CUTTING_W / 2 - SMALL_REG_W / 2

# ============================================================
# Classify grid positions — checkerboard
# ============================================================

cutting_holes = []    # enlarged for bushing
reg_holes = []        # original size, indexing only

for col in range(GRID_COLS):
    for row in range(GRID_ROWS):
        cx = GRID_ORIGIN_X + col * COL_SPACING
        cy = GRID_ORIGIN_Y - row * ROW_SPACING
        if (col + row) % 2 == 0:
            cutting_holes.append((cx, cy))
        else:
            reg_holes.append((cx, cy))

# ============================================================
# Build — Template plate with bushing-adapted holes
# ============================================================

with BuildPart() as template:

    # 1. Base plate
    with BuildSketch(Plane.XY):
        Rectangle(TEMPLATE_WIDTH, TEMPLATE_HEIGHT)
    extrude(amount=TEMPLATE_THICKNESS)

    # 2. Red rectangle (large, left) — enlarged with rounded corners
    with BuildSketch(Plane.XY.offset(TEMPLATE_THICKNESS / 2)):
        with Locations([(RED_RECT_CX, RED_RECT_CY)]):
            RectangleRounded(
                LARGE_TEMPLATE_RED_W,
                LARGE_TEMPLATE_RED_H,
                radius=LARGE_CORNER_R,
            )
    extrude(amount=TEMPLATE_THICKNESS + 2, both=True, mode=Mode.SUBTRACT)

    # 3. Blue rectangle (large, right) — enlarged with rounded corners
    with BuildSketch(Plane.XY.offset(TEMPLATE_THICKNESS / 2)):
        with Locations([(BLUE_RECT_CX, BLUE_RECT_CY)]):
            RectangleRounded(
                LARGE_TEMPLATE_BLUE_W,
                LARGE_TEMPLATE_BLUE_H,
                radius=LARGE_CORNER_R,
            )
    extrude(amount=TEMPLATE_THICKNESS + 2, both=True, mode=Mode.SUBTRACT)

    # 4. Small grid — cutting holes (enlarged, rounded corners)
    with BuildSketch(Plane.XY.offset(TEMPLATE_THICKNESS / 2)):
        for (hx, hy) in cutting_holes:
            with Locations([(hx, hy)]):
                RectangleRounded(
                    SMALL_CUTTING_W,
                    SMALL_CUTTING_H,
                    radius=SMALL_CORNER_R,
                )
    extrude(amount=TEMPLATE_THICKNESS + 2, both=True, mode=Mode.SUBTRACT)

    # 5. Small grid — registration holes (original size, sharp corners)
    with BuildSketch(Plane.XY.offset(TEMPLATE_THICKNESS / 2)):
        for (hx, hy) in reg_holes:
            with Locations([(hx, hy)]):
                Rectangle(SMALL_REG_W, SMALL_REG_H)
    extrude(amount=TEMPLATE_THICKNESS + 2, both=True, mode=Mode.SUBTRACT)

# ============================================================
# Export
# ============================================================

export_stl(template.part, str(OUTPUT_DIR / "pb_back_router_template_bushing.stl"))
export_step(template.part, str(OUTPUT_DIR / "pb_back_router_template_bushing.step"))

# ============================================================
# SVG export — 2D outline for SendCutSend / visual review
# ============================================================

def svg_rounded_rect(cx, cy, w, h, r, stroke="#009933"):
    """SVG path for a rounded rectangle centered at (cx, cy)."""
    # Clamp radius to half the smaller dimension
    r = min(r, w / 2, h / 2)
    x = cx - w / 2
    y = cy - h / 2
    return (
        f'<rect x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" '
        f'rx="{r:.4f}" ry="{r:.4f}" fill="none" stroke="{stroke}" stroke-width="0.5"/>'
    )

def svg_rect(cx, cy, w, h, stroke="#999999"):
    """SVG path for a sharp-cornered rectangle centered at (cx, cy)."""
    x = cx - w / 2
    y = cy - h / 2
    return (
        f'<rect x="{x:.4f}" y="{y:.4f}" width="{w:.4f}" height="{h:.4f}" '
        f'fill="none" stroke="{stroke}" stroke-width="0.5"/>'
    )

# SVG coordinate system: origin at top-left, Y increases downward
# Map from physical coords (origin=center, Y-up) to SVG
MARGIN = 10.0
svg_w = TEMPLATE_WIDTH + 2 * MARGIN
svg_h = TEMPLATE_HEIGHT + 2 * MARGIN

def to_svg(px, py):
    """Physical coords (center origin, Y-up) → SVG coords (top-left origin, Y-down)."""
    sx = px + TEMPLATE_WIDTH / 2 + MARGIN
    sy = -py + TEMPLATE_HEIGHT / 2 + MARGIN
    return sx, sy

lines = []
lines.append(f'<?xml version="1.0" encoding="UTF-8"?>')
lines.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{svg_w:.2f}mm" height="{svg_h:.2f}mm" '
    f'viewBox="0 0 {svg_w:.2f} {svg_h:.2f}">'
)

# Outer plate
ox, oy = to_svg(0, 0)
lines.append(svg_rect(ox, oy, TEMPLATE_WIDTH, TEMPLATE_HEIGHT, "#333333"))

# Red rectangle — enlarged
rx, ry = to_svg(RED_RECT_CX, RED_RECT_CY)
lines.append(svg_rounded_rect(rx, ry, LARGE_TEMPLATE_RED_W, LARGE_TEMPLATE_RED_H,
                                LARGE_CORNER_R, "#cc0000"))

# Blue rectangle — enlarged
bx, by = to_svg(BLUE_RECT_CX, BLUE_RECT_CY)
lines.append(svg_rounded_rect(bx, by, LARGE_TEMPLATE_BLUE_W, LARGE_TEMPLATE_BLUE_H,
                                LARGE_CORNER_R, "#0066cc"))

# Small grid — cutting holes (enlarged, green)
for (hx, hy) in cutting_holes:
    sx, sy = to_svg(hx, hy)
    lines.append(svg_rounded_rect(sx, sy, SMALL_CUTTING_W, SMALL_CUTTING_H,
                                   SMALL_CORNER_R, "#009933"))

# Small grid — registration holes (original size, gray)
for (hx, hy) in reg_holes:
    sx, sy = to_svg(hx, hy)
    lines.append(svg_rect(sx, sy, SMALL_REG_W, SMALL_REG_H, "#999999"))

# Legend
lines.append(
    f'<text x="{MARGIN}" y="{svg_h - 2}" font-size="4" font-family="monospace" fill="#666">'
    f'GREEN = cutting (bushing) | GRAY = registration (index) | '
    f'RED/BLUE = large cutouts (3/4" bushing)'
    f'</text>'
)

lines.append('</svg>')

svg_path = OUTPUT_DIR / "pb_back_router_template_bushing.svg"
svg_path.write_text("\n".join(lines))

# ============================================================
# Summary
# ============================================================

bb = template.part.bounding_box()
print("PB Back Panel — Router Bushing Template")
print(f"  Template: {TEMPLATE_WIDTH:.1f} x {TEMPLATE_HEIGHT:.1f} x {TEMPLATE_THICKNESS:.1f} mm")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print()
print("Large rectangles (3/4\" bushing + 3/8\" bit):")
print(f"  Offset per side: {LARGE_OFFSET:.3f} mm")
print(f"  Corner radius: {LARGE_CORNER_R:.3f} mm")
print(f"  Red:  {RED_RECT_W:.1f}x{RED_RECT_H:.1f} target → "
      f"{LARGE_TEMPLATE_RED_W:.1f}x{LARGE_TEMPLATE_RED_H:.1f} template")
print(f"  Blue: {BLUE_RECT_W:.1f}x{BLUE_RECT_H:.1f} target → "
      f"{LARGE_TEMPLATE_BLUE_W:.1f}x{LARGE_TEMPLATE_BLUE_H:.1f} template")
print()
print("Small hole grid (5/16\" bushing + 3/16\" bit, checkerboard):")
print(f"  Offset per side: {SMALL_OFFSET:.3f} mm")
print(f"  Corner radius: {SMALL_CORNER_R:.3f} mm")
print(f"  Target hole: {SMALL_HOLE_W:.1f}x{SMALL_HOLE_H:.1f} mm")
print(f"  Cutting hole (template): {SMALL_CUTTING_W:.1f}x{SMALL_CUTTING_H:.1f} mm")
print(f"  Registration hole: {SMALL_REG_W:.1f}x{SMALL_REG_H:.1f} mm (unchanged)")
print(f"  Grid: {GRID_COLS} cols x {GRID_ROWS} rows = {GRID_COLS * GRID_ROWS} positions")
print(f"  Cutting holes: {len(cutting_holes)}  |  Registration holes: {len(reg_holes)}")
print(f"  Vertical gap (cutting↔reg): {vert_gap:.2f} mm")
print(f"  Horizontal gap (cutting↔reg): {horiz_gap:.2f} mm")
print()
print("Routed corner radii in workpiece:")
print(f"  Large rects: {LARGE_BIT_DIAM / 2:.2f} mm (= bit radius)")
print(f"  Small holes: {SMALL_BIT_DIAM / 2:.2f} mm (= bit radius)")
print()
print("Checkerboard usage:")
print("  GREEN holes: insert bushing, rout through")
print("  GRAY holes:  insert 5mm indexing pins into previously routed holes")
print("               (or skip — they serve as visual reference)")
print(f"\nExported: STEP, STL, SVG")

if HAS_VIEWER:
    show(template, names=["bushing_template"])

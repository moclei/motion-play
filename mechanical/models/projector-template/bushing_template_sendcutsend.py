"""
Generate SendCutSend-ready SVG from the bushing template geometry.

Extracts the 2D cut profile (outer boundary + all holes) from
bushing_template.py parameters and writes a clean SVG.

Run: python bushing_template_sendcutsend.py
Output: bushing_template_sendcutsend.svg
"""

from pathlib import Path

OUTPUT_DIR = Path(__file__).parent

# ============================================================
# Parameters (mirrored from bushing_template.py)
# ============================================================

TARGET_HOLE_DIAM = 5.0
ROUTER_BIT_DIAM = 4.75
BUSHING_OD = 7.9
TEMPLATE_HOLE_DIAM = TARGET_HOLE_DIAM + (BUSHING_OD - ROUTER_BIT_DIAM)  # 8.15mm

COLUMNS = 12
ROWS = 10
HOLE_SPACING = 10.0

GRID_SPAN_X = (COLUMNS - 1) * HOLE_SPACING   # 110mm
GRID_SPAN_Y = (ROWS - 1) * HOLE_SPACING      # 90mm

BORDER = 15.0
TEMPLATE_WIDTH = GRID_SPAN_X + 2 * BORDER     # 140mm
TEMPLATE_HEIGHT = GRID_SPAN_Y + 2 * BORDER    # 120mm

REG_PIN_DIAM = 5.0
CHAMFER_SIZE = 8.0

# ============================================================
# Compute hole positions (checkerboard)
# ============================================================

# Hole centers relative to template center
first_hole_x = -GRID_SPAN_X / 2
first_hole_y = +GRID_SPAN_Y / 2

cutting_holes = []   # 8.15mm
reg_holes = []       # 5.0mm

for col in range(COLUMNS):
    for row in range(ROWS):
        hx = first_hole_x + col * HOLE_SPACING
        hy = first_hole_y - row * HOLE_SPACING
        if (col + row) % 2 == 0:
            cutting_holes.append((hx, hy))
        else:
            reg_holes.append((hx, hy))

# ============================================================
# Generate SVG
# ============================================================

MARGIN = 5.0
svg_w = TEMPLATE_WIDTH + 2 * MARGIN
svg_h = TEMPLATE_HEIGHT + 2 * MARGIN


def to_svg(px, py):
    """Physical coords (center origin, Y-up) → SVG coords (top-left origin, Y-down)."""
    sx = px + TEMPLATE_WIDTH / 2 + MARGIN
    sy = -py + TEMPLATE_HEIGHT / 2 + MARGIN
    return sx, sy


lines = []
lines.append('<?xml version="1.0" encoding="UTF-8"?>')
lines.append(
    f'<svg xmlns="http://www.w3.org/2000/svg" '
    f'width="{svg_w:.2f}mm" height="{svg_h:.2f}mm" '
    f'viewBox="0 0 {svg_w:.2f} {svg_h:.2f}">'
)

# Outer boundary with chamfer notch at top-left corner
# Template rect from (MARGIN, MARGIN) to (MARGIN+W, MARGIN+H)
# Chamfer cuts a triangle from the top-left: 8mm along top edge, 8mm down left edge
x0 = MARGIN
y0 = MARGIN
x1 = MARGIN + TEMPLATE_WIDTH
y1 = MARGIN + TEMPLATE_HEIGHT
cx = x0 + CHAMFER_SIZE  # chamfer end along top edge
cy = y0 + CHAMFER_SIZE  # chamfer end down left edge

lines.append(
    f'<polygon points="'
    f'{cx:.4f},{y0:.4f} {x1:.4f},{y0:.4f} {x1:.4f},{y1:.4f} '
    f'{x0:.4f},{y1:.4f} {x0:.4f},{cy:.4f}" '
    f'fill="none" stroke="black" stroke-width="0.1"/>'
)

# Cutting holes (8.15mm diameter) — blue for visibility
for (hx, hy) in cutting_holes:
    sx, sy = to_svg(hx, hy)
    r = TEMPLATE_HOLE_DIAM / 2
    lines.append(
        f'<circle cx="{sx:.4f}" cy="{sy:.4f}" r="{r:.4f}" '
        f'fill="none" stroke="blue" stroke-width="0.1"/>'
    )

# Registration holes (5mm diameter) — red for visibility
for (hx, hy) in reg_holes:
    sx, sy = to_svg(hx, hy)
    r = REG_PIN_DIAM / 2
    lines.append(
        f'<circle cx="{sx:.4f}" cy="{sy:.4f}" r="{r:.4f}" '
        f'fill="none" stroke="red" stroke-width="0.1"/>'
    )

lines.append('</svg>')

svg_path = OUTPUT_DIR / "bushing_template_sendcutsend.svg"
svg_path.write_text("\n".join(lines))

# ============================================================
# Summary
# ============================================================

min_wall = HOLE_SPACING - TEMPLATE_HOLE_DIAM / 2 - REG_PIN_DIAM / 2
print("Bushing Template — SendCutSend SVG")
print(f"  Outer: {TEMPLATE_WIDTH:.0f} x {TEMPLATE_HEIGHT:.0f} mm (with {CHAMFER_SIZE:.0f}mm chamfer)")
print(f"  Cutting holes: {len(cutting_holes)} x {TEMPLATE_HOLE_DIAM:.2f}mm dia")
print(f"  Registration holes: {len(reg_holes)} x {REG_PIN_DIAM:.1f}mm dia")
print(f"  Min wall: {min_wall:.3f} mm")
print(f"  Grid: {COLUMNS} x {ROWS} = {COLUMNS * ROWS} holes, {HOLE_SPACING:.0f}mm spacing")
print(f"\nOutput: {svg_path}")

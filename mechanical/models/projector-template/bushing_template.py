"""
White Oak Hole Grid — Router Bushing Template (Checkerboard Quadrant)

3D-printed template for routing a 5mm hole array into 3/8" white oak
using a 4.75mm router bit inside a 7.9mm OD guide bushing. The bushing
rides in 8.15mm template holes, producing 5mm holes in the workpiece.

The full grid is 24 columns × 20 rows (480 holes) on 10mm spacing.
This template covers one quadrant: 12 columns × 10 rows (120 positions).
Reposition to four quadrant locations to complete the full grid.

Checkerboard pattern:
  Every grid position has a hole, but sizes alternate in a checkerboard.
  - Even+even and odd+odd indices (col+row even): 8.15mm cutting holes
    for the router bushing.
  - Even+odd and odd+even indices (col+row odd): 5mm registration holes
    for indexing pins into previously routed workpiece holes.

  This gives 60 cutting holes + 60 registration holes per quadrant.
  Adjacent holes are always different sizes, so the minimum wall is:
    10 - 8.15/2 - 5/2 = 3.425mm (vs 1.85mm with uniform cutting holes).

  CRITICAL: orientation matters. Rotating 180° swaps cutting/registration
  holes — the bushing won't fit 5mm holes and pins won't grip 8.15mm
  holes. The origin chamfer must be checked before every placement.

Quadrant sequence:
  1. TL — registered with workpiece corner fence/stop
  2. TR — 5mm pins into routed TL holes
  3. BL — 5mm pins into routed TL holes
  4. BR — 5mm pins into routed TR or BL holes

Print orientation: flat face down (Z-up)
Material: PLA or PETG, high infill (80%+), 4+ perimeters
Suggested layer height: 0.2mm

Coordinate system:
  Origin = center of template plate
  X = template width (columns direction)
  Y = template height (rows direction)
  Z = template thickness (+Z = top face, bushing entry side)

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
# Routing system parameters
# ============================================================

TARGET_HOLE_DIAM = 5.0          # desired hole in workpiece
ROUTER_BIT_DIAM = 4.75          # spiral upcut bit
BUSHING_OD = 7.9                # guide bushing outer diameter
# Template hole = target + (bushing OD - bit diameter)
TEMPLATE_HOLE_DIAM = TARGET_HOLE_DIAM + (BUSHING_OD - ROUTER_BIT_DIAM)
# = 8.15mm; bushing clearance = 0.125mm/side

# ============================================================
# Template geometry
# ============================================================

# Hole grid within this quadrant template
COLUMNS = 12
ROWS = 10
HOLE_SPACING = 10.0             # center-to-center

# Grid span (center-to-center of outermost holes)
GRID_SPAN_X = (COLUMNS - 1) * HOLE_SPACING   # 110mm
GRID_SPAN_Y = (ROWS - 1) * HOLE_SPACING      # 90mm

# Border around hole array to template edge
BORDER = 15.0

# Outer dimensions
TEMPLATE_WIDTH = GRID_SPAN_X + 2 * BORDER    # 140mm
TEMPLATE_HEIGHT = GRID_SPAN_Y + 2 * BORDER   # 120mm
TEMPLATE_THICKNESS = 9.0                       # 8-10mm acceptable

# First hole center relative to template top-left corner
FIRST_HOLE_FROM_LEFT = BORDER    # 15mm
FIRST_HOLE_FROM_TOP = BORDER     # 15mm

# Registration pin holes (5mm pins into previously drilled workpiece holes)
REG_PIN_DIAM = 5.0

# Origin corner chamfer (top-left orientation mark)
CHAMFER_SIZE = 8.0               # 45° chamfer leg length

# ============================================================
# Workpiece reference (for visualization / documentation)
# ============================================================

WORKPIECE_WIDTH = 277.80         # mm (10.93")
WORKPIECE_HEIGHT = 226.29        # mm (8.91")
WORKPIECE_THICKNESS = 9.525      # mm (3/8")

# First hole center on workpiece (from top-left corner)
WP_FIRST_HOLE_X = 22.49
WP_FIRST_HOLE_Y = 16.22

# Full grid
TOTAL_COLUMNS = 24
TOTAL_ROWS = 20

# ============================================================
# Computed positions — checkerboard hole pattern
# ============================================================

# Hole centers relative to template center (origin)
# First hole (col=0, row=0) is at (-GRID_SPAN_X/2, +GRID_SPAN_Y/2) — top-left
first_hole_x = -GRID_SPAN_X / 2
first_hole_y = +GRID_SPAN_Y / 2

# Classify each position: (col+row) even → cutting hole, odd → registration hole
cutting_holes = []     # 8.15mm — bushing guide holes
reg_holes = []         # 5.0mm  — indexing pin holes

for col in range(COLUMNS):
    for row in range(ROWS):
        hx = first_hole_x + col * HOLE_SPACING
        hy = first_hole_y - row * HOLE_SPACING
        if (col + row) % 2 == 0:
            cutting_holes.append((hx, hy))
        else:
            reg_holes.append((hx, hy))

# Wall between adjacent holes (cutting ↔ registration, always different types)
MIN_WALL = HOLE_SPACING - TEMPLATE_HOLE_DIAM / 2 - REG_PIN_DIAM / 2  # 3.425mm

# ============================================================
# Build — Template plate
# ============================================================

with BuildPart() as template:

    # 1. Base plate
    with BuildSketch(Plane.XY):
        Rectangle(TEMPLATE_WIDTH, TEMPLATE_HEIGHT)
    extrude(amount=TEMPLATE_THICKNESS)

    # 2. Orientation chamfer — triangular notch at top-left corner
    #    CRITICAL with checkerboard: rotating 180° swaps hole types.
    #    Removes a right triangle (CHAMFER_SIZE × CHAMFER_SIZE) from
    #    the corner, full thickness, making orientation unambiguous.
    tl_x = -TEMPLATE_WIDTH / 2
    tl_y = +TEMPLATE_HEIGHT / 2
    with BuildSketch(Plane.XY.offset(TEMPLATE_THICKNESS / 2)):
        with BuildLine():
            Line((tl_x, tl_y), (tl_x + CHAMFER_SIZE, tl_y))
            Line((tl_x + CHAMFER_SIZE, tl_y), (tl_x, tl_y - CHAMFER_SIZE))
            Line((tl_x, tl_y - CHAMFER_SIZE), (tl_x, tl_y))
        make_face()
    extrude(amount=TEMPLATE_THICKNESS + 2, both=True, mode=Mode.SUBTRACT)

    # 3. Cutting holes — 8.15mm bushing guide holes (checkerboard "even" positions)
    with BuildSketch(Plane.XY.offset(TEMPLATE_THICKNESS / 2)):
        for (hx, hy) in cutting_holes:
            with Locations([(hx, hy)]):
                Circle(TEMPLATE_HOLE_DIAM / 2)
    extrude(amount=TEMPLATE_THICKNESS + 2, both=True, mode=Mode.SUBTRACT)

    # 4. Registration holes — 5mm pin holes (checkerboard "odd" positions)
    with BuildSketch(Plane.XY.offset(TEMPLATE_THICKNESS / 2)):
        for (hx, hy) in reg_holes:
            with Locations([(hx, hy)]):
                Circle(REG_PIN_DIAM / 2)
    extrude(amount=TEMPLATE_THICKNESS + 2, both=True, mode=Mode.SUBTRACT)

# ============================================================
# Build — Calibration coupon (print this first to verify hole size)
# ============================================================

COUPON_ROWS = 3
COUPON_COLS = 4
COUPON_BORDER = 10.0
coupon_w = (COUPON_COLS - 1) * HOLE_SPACING + 2 * COUPON_BORDER   # 50mm
coupon_h = (COUPON_ROWS - 1) * HOLE_SPACING + 2 * COUPON_BORDER   # 40mm

with BuildPart() as coupon:
    with BuildSketch(Plane.XY):
        Rectangle(coupon_w, coupon_h)
    extrude(amount=TEMPLATE_THICKNESS)

    coupon_first_x = -(COUPON_COLS - 1) * HOLE_SPACING / 2
    coupon_first_y = +(COUPON_ROWS - 1) * HOLE_SPACING / 2

    # Checkerboard on coupon too — verify both hole sizes
    coupon_cutting = []
    coupon_reg = []
    for col in range(COUPON_COLS):
        for row in range(COUPON_ROWS):
            cx = coupon_first_x + col * HOLE_SPACING
            cy = coupon_first_y - row * HOLE_SPACING
            if (col + row) % 2 == 0:
                coupon_cutting.append((cx, cy))
            else:
                coupon_reg.append((cx, cy))

    with BuildSketch(Plane.XY.offset(TEMPLATE_THICKNESS / 2)):
        for (cx, cy) in coupon_cutting:
            with Locations([(cx, cy)]):
                Circle(TEMPLATE_HOLE_DIAM / 2)
    extrude(amount=TEMPLATE_THICKNESS + 2, both=True, mode=Mode.SUBTRACT)

    with BuildSketch(Plane.XY.offset(TEMPLATE_THICKNESS / 2)):
        for (cx, cy) in coupon_reg:
            with Locations([(cx, cy)]):
                Circle(REG_PIN_DIAM / 2)
    extrude(amount=TEMPLATE_THICKNESS + 2, both=True, mode=Mode.SUBTRACT)

# ============================================================
# Build — Workpiece reference (visualization only)
# ============================================================

with BuildPart() as workpiece_ref:
    with BuildSketch(Plane.XY):
        Rectangle(WORKPIECE_WIDTH, WORKPIECE_HEIGHT)
    extrude(amount=-WORKPIECE_THICKNESS)

# ============================================================
# Export
# ============================================================

export_stl(template.part, str(OUTPUT_DIR / "bushing_template.stl"))
export_step(template.part, str(OUTPUT_DIR / "bushing_template.step"))
export_stl(coupon.part, str(OUTPUT_DIR / "calibration_coupon.stl"))
export_step(coupon.part, str(OUTPUT_DIR / "calibration_coupon.step"))

# ============================================================
# Summary
# ============================================================

bb = template.part.bounding_box()
bushing_clearance = (TEMPLATE_HOLE_DIAM - BUSHING_OD) / 2

print("White Oak Hole Grid — Checkerboard Router Bushing Template")
print(f"  Template: {TEMPLATE_WIDTH:.0f} x {TEMPLATE_HEIGHT:.0f} x {TEMPLATE_THICKNESS:.0f} mm")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print(f"  Volume: {template.part.volume:.0f} mm³")
print()
print("Checkerboard pattern (per quadrant):")
print(f"  Grid: {COLUMNS} cols × {ROWS} rows = {COLUMNS * ROWS} positions")
print(f"  Cutting holes (8.15mm): {len(cutting_holes)} — (col+row) even")
print(f"  Registration holes (5mm): {len(reg_holes)} — (col+row) odd")
print(f"  Min wall (cutting ↔ reg): {MIN_WALL:.3f} mm")
print(f"  Hole spacing: {HOLE_SPACING:.1f} mm c-c")
print(f"  Grid span: {GRID_SPAN_X:.0f} x {GRID_SPAN_Y:.0f} mm")
print(f"  Border: {BORDER:.0f} mm")
print()
print("Routing system:")
print(f"  Target hole: {TARGET_HOLE_DIAM:.1f} mm")
print(f"  Router bit: {ROUTER_BIT_DIAM:.2f} mm")
print(f"  Bushing OD: {BUSHING_OD:.1f} mm")
print(f"  Template cutting hole: {TEMPLATE_HOLE_DIAM:.2f} mm")
print(f"  Bushing clearance: {bushing_clearance:.3f} mm/side")
print(f"  Registration pin: {REG_PIN_DIAM:.1f} mm (slip fit into routed {TARGET_HOLE_DIAM:.0f}mm holes)")
print()
print(f"  Orientation: chamfer at top-left corner ({CHAMFER_SIZE:.0f}mm) — CHECK BEFORE EVERY PLACEMENT")
print()
print("Quadrant usage (4 placements for 480 total holes):")
print(f"  TL: cols 0-11, rows 0-9   — fence to workpiece corner")
print(f"  TR: cols 12-23, rows 0-9  — pins into TL holes")
print(f"  BL: cols 0-11, rows 10-19 — pins into TL holes")
print(f"  BR: cols 12-23, rows 10-19 — pins into TR/BL holes")
print()
print("Full workpiece grid:")
print(f"  {TOTAL_COLUMNS} cols × {TOTAL_ROWS} rows = {TOTAL_COLUMNS * TOTAL_ROWS} holes")
print(f"  First hole center: ({WP_FIRST_HOLE_X:.2f}, {WP_FIRST_HOLE_Y:.2f}) mm from TL corner")
print(f"  Workpiece: {WORKPIECE_WIDTH:.1f} x {WORKPIECE_HEIGHT:.1f} mm ({WORKPIECE_THICKNESS:.3f}mm thick)")

cb = coupon.part.bounding_box()
print(f"\nCalibration coupon: {coupon_w:.0f} x {coupon_h:.0f} x {TEMPLATE_THICKNESS:.0f} mm")
print(f"  Checkerboard: {len(coupon_cutting)} cutting + {len(coupon_reg)} registration = {COUPON_COLS * COUPON_ROWS} holes")
print(f"  Print this first — measure both hole sizes with bushing and pins")
print(f"  FDM holes typically print undersized; adjust +0.1–0.3mm if needed")

if HAS_VIEWER:
    show(template, coupon,
         names=["bushing_template", "calibration_coupon"])

"""
Indexing Pin (Registration variant) — PB Back Router Bushing Template.

Companion to indexing_pin.py. Same body concept, different head profile:
the head fits the template's NON-rounded (registration) rectangle slots,
while the original pin fits the rounded (cutting) rectangle slots.

Two stacked rectangles:
  - Head: sharp-cornered, 15.425 × 5.273 — matches the template's small
    registration rectangles (SMALL_REG_W × SMALL_REG_H). Height is
    template thickness minus HEAD_RECESS so the head sits flush-or-below
    the template top face.
  - Body: rounded-corner, 15.425 × 5.273 with r≈2.38 — matches a routed
    workpiece pocket from the cutting rectangles. Length equals full
    workpiece thickness.

Usage note:
  Head and body share the same W×H; only the corners differ. That means
  the pin can drop through a sharp-cornered template slot (the head
  seats there) while the rounded body extends into a previously-routed
  cutting pocket below — useful when the template has been shifted so
  registration slots now overlap earlier routed pockets.

Print orientation:
  Head face-down on the build plate. Layer lines perpendicular to pin
  axis. The sharp-cornered first layer prints cleanly.

See: pb_back_router_template_bushing.py and indexing_pin.py.
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
# Dimensions — mirrored from pb_back_router_template_bushing.py
# ============================================================

# Head — fills the template's sharp-cornered registration rectangle
HEAD_W = 15.425               # SMALL_REG_W = SMALL_HOLE_W
HEAD_H = 5.273                # SMALL_REG_H = SMALL_HOLE_H
# (no head corner radius — registration rects are sharp)

# Body — fits a routed workpiece pocket (target dims + bit-radius corners)
BODY_W = 15.425               # SMALL_HOLE_W
BODY_H = 5.273                # SMALL_HOLE_H
BODY_CORNER_R = 2.38125       # SMALL_BIT_DIAM / 2 (3/16" bit radius)

TEMPLATE_THICKNESS = 6.4
WORKPIECE_THICKNESS = 15.0

HEAD_RECESS = 0.2
CLEARANCE = 0.1               # per-side slip-fit allowance

head_w = HEAD_W - 2 * CLEARANCE
head_h = HEAD_H - 2 * CLEARANCE
body_w = BODY_W - 2 * CLEARANCE
body_h = BODY_H - 2 * CLEARANCE
body_r = max(BODY_CORNER_R - CLEARANCE, 0.1)

head_height = TEMPLATE_THICKNESS - HEAD_RECESS
body_height = WORKPIECE_THICKNESS

# ============================================================
# Build
# ============================================================

with BuildPart() as pin:
    # Sharp-cornered head (face-down on build plate)
    with BuildSketch(Plane.XY):
        Rectangle(head_w, head_h)
    extrude(amount=head_height)

    # Rounded-corner body (stacks on head)
    with BuildSketch(Plane.XY.offset(head_height)):
        RectangleRounded(body_w, body_h, radius=body_r)
    extrude(amount=body_height)

# ============================================================
# Export
# ============================================================

export_stl(pin.part, str(OUTPUT_DIR / "indexing_pin_reg.stl"))
export_step(pin.part, str(OUTPUT_DIR / "indexing_pin_reg.step"))

# ============================================================
# Summary
# ============================================================

bb = pin.part.bounding_box()
print("Router Bushing Template — Indexing Pin (Registration variant)")
print(f"  Head:  {head_w:.2f} x {head_h:.2f} x {head_height:.2f} mm  "
      f"(sharp corners, fits template registration slot)")
print(f"  Body:  {body_w:.2f} x {body_h:.2f} x {body_height:.2f} mm  "
      f"(r={body_r:.2f}, fits routed workpiece pocket)")
print(f"  Total height: {head_height + body_height:.2f} mm")
print(f"  Clearance: {CLEARANCE:.2f} mm/side")
print(f"  Head recess: {HEAD_RECESS:.2f} mm below template top")
print(f"  Bounding box: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")
print(f"\nExported: STL, STEP")

if HAS_VIEWER:
    show(pin, names=["indexing_pin_reg"])

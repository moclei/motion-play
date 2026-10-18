"""
Indexing Pin — PB Back Router Bushing Template.

Stepped 3D-printed pin used to lock the router template against the
workpiece after a few small pockets have been routed. Frees up clamp
positions so the router can reach every cutout.

Two stacked rounded rectangles (cross-sections match the template's
small-grid holes):
  - Head: fits the template cutting rectangle (18.613 × 8.461, r3.975).
    Height is template thickness minus HEAD_RECESS so the head sits
    just below the template's top face.
  - Body: fits the routed workpiece pocket (15.425 × 5.273 target size
    with r2.38 corners from the 3/16" bit). Length equals full workpiece
    thickness for maximum engagement.

Note on body corners:
  The user spec said "dimensions of the smaller rectangles" — those
  template registration rectangles are sharp-cornered. But the pin body
  actually has to fit a *routed* pocket, which inherits the bit radius
  at every corner. A sharp-cornered body would jam on those radii, so
  the body corners are rounded to the bit radius (minus clearance).
  Overall W×H dimensions are preserved.

Workflow:
  1. Clamp template to workpiece. Rout a few small cutting pockets.
  2. Drop indexing pins through: body enters the routed pocket, head
     seats into the template cutting rectangle.
  3. Remove the clamps — pins now constrain the template in XY.
  4. Rout the remaining cutouts.

Print orientation:
  Head face-down on the build plate. Layer lines perpendicular to the
  pin axis so the head-to-body step is a clean horizontal transition.

See: pb_back_router_template_bushing.py (source of template geometry)
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

# Head — fills the template cutting rectangle (small-grid bushing hole)
HEAD_W = 18.613               # SMALL_CUTTING_W  = 15.425 + 2 * 1.59375
HEAD_H = 8.461                # SMALL_CUTTING_H  = 5.273  + 2 * 1.59375
HEAD_CORNER_R = 3.975         # SMALL_BUSHING_OD / 2

# Body — fits the routed workpiece pocket (target dims + bit-radius corners)
BODY_W = 15.425               # SMALL_HOLE_W (target routed size)
BODY_H = 5.273                # SMALL_HOLE_H
BODY_CORNER_R = 2.38125       # SMALL_BIT_DIAM / 2 (3/16" bit radius)

TEMPLATE_THICKNESS = 6.4      # user-specified
WORKPIECE_THICKNESS = 15.0    # user-specified

HEAD_RECESS = 0.2             # head seats this much below template top face
CLEARANCE = 0.1               # per-side slip-fit allowance (FDM prints oversize)

# Shrink features by clearance on every side
head_w = HEAD_W - 2 * CLEARANCE
head_h = HEAD_H - 2 * CLEARANCE
head_r = max(HEAD_CORNER_R - CLEARANCE, 0.1)
body_w = BODY_W - 2 * CLEARANCE
body_h = BODY_H - 2 * CLEARANCE
body_r = max(BODY_CORNER_R - CLEARANCE, 0.1)

head_height = TEMPLATE_THICKNESS - HEAD_RECESS
body_height = WORKPIECE_THICKNESS

# ============================================================
# Build
# ============================================================

with BuildPart() as pin:
    # Head (face-down on build plate)
    with BuildSketch(Plane.XY):
        RectangleRounded(head_w, head_h, radius=head_r)
    extrude(amount=head_height)

    # Body (stacked on top; projects down into workpiece in use)
    with BuildSketch(Plane.XY.offset(head_height)):
        RectangleRounded(body_w, body_h, radius=body_r)
    extrude(amount=body_height)

# ============================================================
# Export
# ============================================================

export_stl(pin.part, str(OUTPUT_DIR / "indexing_pin.stl"))
export_step(pin.part, str(OUTPUT_DIR / "indexing_pin.step"))

# ============================================================
# Summary
# ============================================================

bb = pin.part.bounding_box()
print("Router Bushing Template — Indexing Pin")
print(f"  Head:  {head_w:.2f} x {head_h:.2f} x {head_height:.2f} mm  "
      f"(r={head_r:.2f}, fits template cutting rect)")
print(f"  Body:  {body_w:.2f} x {body_h:.2f} x {body_height:.2f} mm  "
      f"(r={body_r:.2f}, fits routed workpiece pocket)")
print(f"  Total height: {head_height + body_height:.2f} mm")
print(f"  Clearance: {CLEARANCE:.2f} mm/side (bump up if pins are tight)")
print(f"  Head recess: {HEAD_RECESS:.2f} mm below template top")
print(f"  Bounding box: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")
print(f"\nExported: STL, STEP")

if HAS_VIEWER:
    show(pin, names=["indexing_pin"])

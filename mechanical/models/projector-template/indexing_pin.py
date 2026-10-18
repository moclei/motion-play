"""
Indexing Pin — Projector Bushing Template (SendCutSend).

Stepped 3D-printed pin used to lock the bushing template against the
workpiece after a few cutting holes have been routed. Lets you remove
the clamps that would otherwise block the router from reaching the
remaining holes.

Two stacked cylinders:
  - Head: fits the 8.15mm template cutting hole. Height is template
    thickness minus HEAD_RECESS so the pin head sits just below the
    template's top face (nothing proud to catch the router base).
  - Body: passes through the 5mm routed workpiece hole. Length equals
    the full workpiece thickness so the pin has full engagement.

Workflow:
  1. Clamp template to workpiece. Rout a few cutting holes.
  2. Drop indexing pins through: body enters the routed 5mm workpiece
     hole, head seats into the 8.15mm template hole.
  3. Remove the clamps — pins now constrain the template in XY.
  4. Rout the remaining holes.

Print orientation:
  Head face-down on the build plate. Layer lines run perpendicular to
  the pin axis so the head-to-body step is a clean horizontal transition.

See: bushing_template_sendcutsend.py (source of template geometry)
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
# Dimensions — mirrored from bushing_template_sendcutsend.py
# ============================================================

TEMPLATE_HOLE_DIAM = 8.15     # cutting hole in template — head seats here
REG_PIN_DIAM = 5.0            # registration hole / target routed hole — body passes through
TEMPLATE_THICKNESS = 5.0      # SendCutSend plate thickness (thinner than the router template)
WORKPIECE_THICKNESS = 15.0    # oak workpiece

HEAD_RECESS = 0.2             # head sits this much below template top face
CLEARANCE = 0.1               # per-side slip-fit allowance (FDM prints oversize)

HEAD_DIAM = TEMPLATE_HOLE_DIAM - 2 * CLEARANCE
HEAD_HEIGHT = TEMPLATE_THICKNESS - HEAD_RECESS
BODY_DIAM = REG_PIN_DIAM - 2 * CLEARANCE
BODY_HEIGHT = WORKPIECE_THICKNESS

# ============================================================
# Build
# ============================================================

with BuildPart() as pin:
    # Head cylinder (goes face-down on the build plate)
    with BuildSketch(Plane.XY):
        Circle(HEAD_DIAM / 2)
    extrude(amount=HEAD_HEIGHT)

    # Body cylinder (stacks on top of head; projects down into workpiece in use)
    with BuildSketch(Plane.XY.offset(HEAD_HEIGHT)):
        Circle(BODY_DIAM / 2)
    extrude(amount=BODY_HEIGHT)

# ============================================================
# Export
# ============================================================

export_stl(pin.part, str(OUTPUT_DIR / "indexing_pin.stl"))
export_step(pin.part, str(OUTPUT_DIR / "indexing_pin.step"))

# ============================================================
# Summary
# ============================================================

bb = pin.part.bounding_box()
print("Projector Bushing Template — Indexing Pin")
print(f"  Head:  Ø{HEAD_DIAM:.2f} x {HEAD_HEIGHT:.2f} mm  "
      f"(fits Ø{TEMPLATE_HOLE_DIAM:.2f} template hole, recess {HEAD_RECESS:.1f}mm)")
print(f"  Body:  Ø{BODY_DIAM:.2f} x {BODY_HEIGHT:.2f} mm  "
      f"(fits Ø{REG_PIN_DIAM:.1f} routed workpiece hole)")
print(f"  Total height: {HEAD_HEIGHT + BODY_HEIGHT:.2f} mm")
print(f"  Clearance: {CLEARANCE:.2f} mm/side (bump up if pins are tight)")
print(f"  Bounding box: {bb.size.X:.2f} x {bb.size.Y:.2f} x {bb.size.Z:.2f} mm")
print(f"\nExported: STL, STEP")

if HAS_VIEWER:
    show(pin, names=["indexing_pin"])

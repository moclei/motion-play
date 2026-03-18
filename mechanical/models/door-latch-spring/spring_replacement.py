"""
Door Latch Spring Replacement — 3D Printed Serpentine Flexure

Replaces a broken torsion spring in a vintage mortise latch mechanism.
Two sleeves fit onto internal posts, connected by a 5-arm serpentine
flexure that provides return force to keep the latch bolt extended.

Components:
  - Main sleeve: fits the fixed chassis post (12mm tall), open top
  - Minor sleeve: fits the moving latch post (2.5mm tall), capped top
  - Mount blocks: solid transition zones between sleeves and flexure
  - Serpentine bridge: 5 thin arms zigzagging between mount blocks

The serpentine arms flex in X when the doorknob is turned (minor post
travels +9.9mm in X). Each arm bends a fraction of the total travel.
With 5 arms of 1.2mm thickness, max strain is ~1.1% — viable for
hundreds of cycles in PLA.

Assembly: lower the entire part onto the mechanism from above (+Z).
The minor post enters its sleeve first (higher up), then the main post.

Print orientation: Z-up (flat on build plate). Arms print in the XY
plane so bending stress runs along layer lines (strong direction).

Coordinate system:
  Origin = center of main post at mechanism base (Z=0)
  X = across mechanism width
  Y = along mechanism (-Y toward minor post)
  Z = mechanism depth (perpendicular to base plate, upward)

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

MAIN_POST_X = 4.95       # slightly curved X faces; measured at widest
MAIN_POST_Y = 3.50       # flat Y faces
MAIN_POST_Z = 12.0       # protrudes from base (Z=0 upward)

MINOR_POST_X = 4.40
MINOR_POST_Y = 2.00
MINOR_POST_Z = 2.50      # protrudes from latch assembly
MINOR_BASE_Z = 11.0      # Z where minor post begins

MINOR_OFFSET_X = 3.3     # minor post position relative to main (+X)
MINOR_OFFSET_Y = -18.0   # minor post position relative to main (-Y)

KNOB_TRAVEL_X = 9.9      # minor post +X travel when knob turned

# ============================================================
# Design parameters (tune these between prints)
# ============================================================

CLEARANCE = 0.15          # per-side sleeve clearance (snug/sliding fit)

# Main sleeve
MAIN_WALL = 2.0           # wall thickness: -X, +X, -Y sides
MAIN_WALL_THIN = 1.5      # +Y wall (limited clearance in mechanism)
MAIN_FLOOR = 1.5          # floor at Z=0
MAIN_HEIGHT = 11.0        # Z=0 to Z=11

# Minor sleeve
MINOR_WALL = 2.0          # all sides
MINOR_CAP = 1.5           # solid cap at top
MINOR_Z_BOT = 9.0         # sleeve bottom (extended below post for bridge)

# Serpentine flexure
BRIDGE_Z_BOT = 7.0        # bridge bottom Z
BRIDGE_Z_TOP = 14.0       # bridge top Z
ARM_THICK = 1.2           # arm width in X — the flex dimension
ARM_GAP = 1.0             # gap between adjacent arms
N_ARMS = 5
ARM_Y_TOP = 2.0           # top turn Y (past main sleeve in +Y)
ARM_Y_BOT = -20.0         # bottom turn Y (past minor sleeve in -Y)

# Mount blocks (sleeve-to-flexure transitions)
MOUNT_WIDTH = 4.0         # X width of mount blocks
MOUNT_EXT = 3.0           # how far mount extends from sleeve wall
MOUNT_OVERLAP = 1.0       # overlap into sleeve wall for solid union

# ============================================================
# Computed dimensions
# ============================================================

BRIDGE_DEPTH = BRIDGE_Z_TOP - BRIDGE_Z_BOT
ARM_PITCH = ARM_THICK + ARM_GAP

# Main sleeve pocket
main_inner_x = MAIN_POST_X + 2 * CLEARANCE
main_inner_y = MAIN_POST_Y + 2 * CLEARANCE
main_outer_x = main_inner_x + 2 * MAIN_WALL
main_outer_y = main_inner_y + MAIN_WALL + MAIN_WALL_THIN
main_center_y = -(MAIN_WALL - MAIN_WALL_THIN) / 2

# Main sleeve edge Y coordinates
main_neg_y = -(main_inner_y / 2) - MAIN_WALL
main_pos_y = (main_inner_y / 2) + MAIN_WALL_THIN

# Minor sleeve pocket
minor_inner_x = MINOR_POST_X + 2 * CLEARANCE
minor_inner_y = MINOR_POST_Y + 2 * CLEARANCE
minor_outer_x = minor_inner_x + 2 * MINOR_WALL
minor_outer_y = minor_inner_y + 2 * MINOR_WALL
MINOR_Z_TOP = MINOR_BASE_Z + MINOR_POST_Z + MINOR_CAP
minor_height = MINOR_Z_TOP - MINOR_Z_BOT

# Minor sleeve edge Y coordinates
minor_pos_y = MINOR_OFFSET_Y + minor_outer_y / 2
minor_neg_y = MINOR_OFFSET_Y - minor_outer_y / 2

# Serpentine arm X positions
arm_x = [(-2.0 + i * ARM_PITCH) for i in range(N_ARMS)]

# Bridge Z center
bridge_z_ctr = (BRIDGE_Z_BOT + BRIDGE_Z_TOP) / 2

# Mount block geometry — main side
main_mount_y_inner = main_neg_y + MOUNT_OVERLAP
main_mount_y_outer = main_neg_y - MOUNT_EXT
main_mount_y_ctr = (main_mount_y_inner + main_mount_y_outer) / 2
main_mount_y_size = abs(main_mount_y_inner - main_mount_y_outer)

# Mount block geometry — minor side
minor_mount_y_inner = minor_pos_y - MOUNT_OVERLAP
minor_mount_y_outer = minor_pos_y + MOUNT_EXT
minor_mount_y_ctr = (minor_mount_y_inner + minor_mount_y_outer) / 2
minor_mount_y_size = abs(minor_mount_y_inner - minor_mount_y_outer)

# Arm Y extents (first/last arm start inside their mount block)
arm0_y_start = main_mount_y_outer + MOUNT_OVERLAP
arm_last_y_end = minor_mount_y_outer - MOUNT_OVERLAP

# ============================================================
# Build — spring replacement part
# ============================================================

with BuildPart() as spring:

    # 1. Main sleeve — rectangular tube, floor at Z=0, open top
    main_z_ctr = MAIN_HEIGHT / 2
    with Locations([(0, main_center_y, main_z_ctr)]):
        Box(main_outer_x, main_outer_y, MAIN_HEIGHT)

    pocket_h = MAIN_HEIGHT - MAIN_FLOOR
    pocket_z_ctr = MAIN_FLOOR + pocket_h / 2 + 0.5
    with Locations([(0, 0, pocket_z_ctr)]):
        Box(main_inner_x, main_inner_y, pocket_h + 1.0, mode=Mode.SUBTRACT)

    # 2. Minor sleeve — rectangular cup, open bottom, capped top
    minor_z_ctr = (MINOR_Z_BOT + MINOR_Z_TOP) / 2
    with Locations([(MINOR_OFFSET_X, MINOR_OFFSET_Y, minor_z_ctr)]):
        Box(minor_outer_x, minor_outer_y, minor_height)

    minor_pocket_top = MINOR_BASE_Z + MINOR_POST_Z
    minor_pocket_bot = MINOR_Z_BOT - 1.0
    minor_pocket_h = minor_pocket_top - minor_pocket_bot
    minor_pocket_z = (minor_pocket_top + minor_pocket_bot) / 2
    with Locations([(MINOR_OFFSET_X, MINOR_OFFSET_Y, minor_pocket_z)]):
        Box(minor_inner_x, minor_inner_y, minor_pocket_h, mode=Mode.SUBTRACT)

    # 3. Mount blocks — solid transition zones at bridge Z level
    with Locations([(arm_x[0], main_mount_y_ctr, bridge_z_ctr)]):
        Box(MOUNT_WIDTH, main_mount_y_size, BRIDGE_DEPTH)

    with Locations([(arm_x[-1], minor_mount_y_ctr, bridge_z_ctr)]):
        Box(MOUNT_WIDTH, minor_mount_y_size, BRIDGE_DEPTH)

    # 4. Serpentine arms — thin vertical-plane beams running in Y
    for i in range(N_ARMS):
        x = arm_x[i]
        if i == 0:
            y_top = arm0_y_start
            y_bot = ARM_Y_BOT
        elif i == N_ARMS - 1:
            y_top = ARM_Y_TOP
            y_bot = arm_last_y_end
        else:
            y_top = ARM_Y_TOP
            y_bot = ARM_Y_BOT

        arm_len = y_top - y_bot
        arm_y = (y_top + y_bot) / 2
        with Locations([(x, arm_y, bridge_z_ctr)]):
            Box(ARM_THICK, arm_len, BRIDGE_DEPTH)

    # 5. Serpentine turns — connect adjacent arms at alternating ends
    for i in range(N_ARMS - 1):
        if i % 2 == 0:
            turn_y = ARM_Y_BOT - ARM_THICK / 2
        else:
            turn_y = ARM_Y_TOP + ARM_THICK / 2

        turn_x = (arm_x[i] + arm_x[i + 1]) / 2
        turn_w = ARM_PITCH + ARM_THICK
        with Locations([(turn_x, turn_y, bridge_z_ctr)]):
            Box(turn_w, ARM_THICK, BRIDGE_DEPTH)

# ============================================================
# Reference posts (visualization only — not exported)
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

export_stl(spring.part, str(OUTPUT_DIR / "spring_replacement.stl"))
export_step(spring.part, str(OUTPUT_DIR / "spring_replacement.step"))

bb = spring.part.bounding_box()
print("Door latch spring replacement built")
print(f"  Bounding box: {bb.size.X:.1f} x {bb.size.Y:.1f} x {bb.size.Z:.1f} mm")
print(f"  Volume: {spring.part.volume:.1f} mm³")
print(f"  Main sleeve: {main_outer_x:.1f} x {main_outer_y:.1f} x {MAIN_HEIGHT:.1f} mm")
print(f"    pocket: {main_inner_x:.2f} x {main_inner_y:.2f} mm, {pocket_h:.1f}mm deep")
print(f"  Minor sleeve: {minor_outer_x:.1f} x {minor_outer_y:.1f} x {minor_height:.1f} mm")
print(f"    pocket: {minor_inner_x:.2f} x {minor_inner_y:.2f} mm, {MINOR_POST_Z:.1f}mm deep")
print(f"  Serpentine: {N_ARMS} arms @ {ARM_THICK:.1f}mm thick, {ARM_GAP:.1f}mm gap")
print(f"  Bridge Z: {BRIDGE_Z_BOT:.0f}–{BRIDGE_Z_TOP:.0f} mm ({BRIDGE_DEPTH:.0f}mm deep)")

if HAS_VIEWER:
    show(spring, ref_main, ref_minor,
         names=["spring_replacement", "main_post_ref", "minor_post_ref"])

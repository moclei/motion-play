"""
Assembly View — Shows tray + lid + inner shell + bar in assembled position.
For visual evaluation only — no exports.
"""

from build123d import *
from pathlib import Path

try:
    from ocp_vscode import show, set_port
    set_port(3939)
except ImportError:
    print("OCP viewer not available")
    exit(1)

HERE = Path(__file__).parent
BAR_WIDTH = 25.25
BAR_THICKNESS = 4.0
BASE_THICKNESS = 2.0
CAVITY_DEPTH = 6.35

tray_part = import_step(str(HERE / "outer_tray.step"))
lid_part = import_step(str(HERE / "outer_lid.step"))
inner_part = import_step(str(HERE / "inner_shell.step"))

# Lid sits on the cavity wall tops, pressed onto the retention posts.
# Lid Z=0 is its bottom face; translate up to the cavity top.
# Posts extend above, so offset by post height for the lid to sit on the wall tops.
lid_positioned = lid_part.move(Location((0, 0, BASE_THICKNESS + CAVITY_DEPTH)))

# Inner shell is built with Z=0 at bar contact, +Z into hoop.
# Rotate 180 deg around X to flip both Y and Z, then translate down.
inner_positioned = inner_part.rotate(Axis.X, 180)
inner_positioned = inner_positioned.move(Location((0, 0, -BAR_THICKNESS)))

# Reference bar
with BuildPart() as bar:
    with Locations([(0, 0, -BAR_THICKNESS / 2)]):
        Box(BAR_WIDTH, 54, BAR_THICKNESS)

show(
    tray_part,
    lid_positioned,
    inner_positioned,
    bar.part,
    names=["wrap_tray", "lid", "inner_shell", "bar"],
)

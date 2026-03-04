"""
Assembly View — Shows tray + inner shell + bar in assembled position.
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

tray_part = import_step(str(HERE / "outer_tray.step"))
inner_part = import_step(str(HERE / "inner_shell.step"))

# Inner shell is built with Z=0 at bar contact, +Z into hoop.
# In the outer shell's frame, the inner face is at Z = -BAR_THICKNESS.
# Rotate 180 deg around X to flip both Y and Z (maps the inner shell's
# coordinate system into the outer shell's frame), then translate down.
inner_positioned = inner_part.rotate(Axis.X, 180)
inner_positioned = inner_positioned.move(Location((0, 0, -BAR_THICKNESS)))

# Reference bar
with BuildPart() as bar:
    with Locations([(0, 0, -BAR_THICKNESS / 2)]):
        Box(BAR_WIDTH, 54, BAR_THICKNESS)

show(
    tray_part,
    inner_positioned,
    bar.part,
    names=["wrap_tray", "inner_shell", "bar"],
)

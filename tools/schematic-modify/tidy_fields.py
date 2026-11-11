#!/usr/bin/env python3
"""
tidy_fields.py - Netlist-neutral field tidy for a KiCad schematic project.

Undoes the damage from kiutils round trips made before the KiCad 8/9 shim
(kiutils_k9.py) existed (docs/research/kicad-ai-tooling-2026-11/
schematic-readability.md section 3.1 steps 2-4):

  1. Hide every placed-symbol field except Reference and Value.
  2. Restore pin_numbers / pin_names hiding on embedded library symbols:
     from the reference project (v7 at c2acffc by default) for the same
     lib_id, else from the source symbol library.
  3. Move every ai_* field to its symbol's position.

It only sets hide flags and moves hidden fields: no symbol, pin, wire or
label changes, so the netlist is unchanged.

Usage:
  python3 tools/schematic-modify/tidy_fields.py --check   # per-sheet counts, writes nothing
  python3 tools/schematic-modify/tidy_fields.py --apply   # write (refuses while KiCad is open)

Options:
  --root PATH        root .kicad_sch (default: the v8 main board)
  --ref-commit SHA   git commit of the reference project (default c2acffc)
  --ref-dir PATH     repo-relative folder of the reference project
                     (default hardware/pcb-main/kicad)
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kiutils_k9  # noqa: E402,F401  (KiCad 8/9 '(hide yes)' shim; must precede any load)
import modify  # noqa: E402
from kiutils.items.common import Position  # noqa: E402
from kiutils.schematic import Schematic  # noqa: E402
from kiutils.symbol import SymbolLib  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO / "hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_sch"
DEFAULT_REF_COMMIT = "c2acffc"
DEFAULT_REF_DIR = "hardware/pcb-main/kicad"
STOCK_SYMBOLS = modify.STOCK_SYMBOLS  # follows KICAD_CLI
KEEP_VISIBLE = {"Reference", "Value"}
AI_PREFIX = "ai_"
PAPER = {"A4": (297.0, 210.0), "A3": (420.0, 297.0), "A2": (594.0, 420.0), "A1": (841.0, 594.0)}

PinFlags = Tuple[bool, bool]  # (hidePinNumbers, pinNamesHide)


def reference_pin_flags(commit: str, ref_dir: str) -> Dict[str, PinFlags]:
    """lib_id -> pin flags from every sheet of the reference project at ``commit``."""
    names = subprocess.run(
        ["git", "-C", str(REPO), "ls-tree", "--name-only", commit, ref_dir + "/"],
        check=True, capture_output=True, text=True,
    ).stdout.split()
    flags = {}  # type: Dict[str, PinFlags]
    with tempfile.TemporaryDirectory() as tmp:
        for name in names:
            if not name.endswith(".kicad_sch"):
                continue
            text = subprocess.run(
                ["git", "-C", str(REPO), "show", "{}:{}".format(commit, name)],
                check=True, capture_output=True, text=True,
            ).stdout
            path = Path(tmp) / Path(name).name
            path.write_text(text)
            for sym in Schematic.from_file(str(path)).libSymbols:
                old = flags.get(sym.libId, (False, False))
                flags[sym.libId] = (old[0] or sym.hidePinNumbers, old[1] or sym.pinNamesHide)
    return flags


def _lib_table(project_dir: Path) -> Dict[str, Path]:
    table = project_dir / "sym-lib-table"
    out = {}  # type: Dict[str, Path]
    if table.exists():
        for name, uri in re.findall(r'\(name "([^"]+)"\).*?\(uri "([^"]+)"\)', table.read_text()):
            out[name] = Path(uri.replace("${KIPRJMOD}", str(project_dir))).resolve()
    return out


class SourceLibraries:
    """Pin flags from the source symbol library (project table, then KiCad stock)."""

    def __init__(self, project_dir: Path):
        self.table = _lib_table(project_dir)
        self.cache = {}  # type: Dict[Path, Optional[SymbolLib]]

    def flags(self, lib_id: str) -> Optional[PinFlags]:
        if ":" not in lib_id:
            return None
        nick, name = lib_id.split(":", 1)
        path = self.table.get(nick, STOCK_SYMBOLS / (nick + ".kicad_sym"))
        if path not in self.cache:
            self.cache[path] = SymbolLib.from_file(str(path)) if path.exists() else None
        lib = self.cache[path]
        if lib is None:
            return None
        for sym in lib.symbols:
            if sym.libId == name:
                return (sym.hidePinNumbers, sym.pinNamesHide)
        return None


def _off_paper(x: float, y: float, size: Tuple[float, float]) -> bool:
    return x < 0 or y < 0 or x > size[0] or y > size[1]


def tidy_sheet(sch: Schematic, ref_flags: Dict[str, PinFlags], src: SourceLibraries,
               notes: list) -> Dict[str, int]:
    counts = {"fields_hidden": 0, "pin_numbers": 0, "pin_names": 0, "ai_moved": 0, "off_sheet_left": 0}

    for sym in sch.schematicSymbols:
        for prop in sym.properties:
            # An empty field draws nothing: KiCad 9's save adds an empty, unhidden Description to
            # placed symbols (Phase 11c GUI pass), so empty values are left alone.
            if prop.key not in KEEP_VISIBLE and not prop.effects.hide and prop.value not in ("", "~"):
                prop.effects.hide = True
                counts["fields_hidden"] += 1
            if prop.key.startswith(AI_PREFIX):
                if prop.position.X != sym.position.X or prop.position.Y != sym.position.Y:
                    prop.position = Position(X=sym.position.X, Y=sym.position.Y, angle=0)
                    counts["ai_moved"] += 1

    for lib in sch.libSymbols:
        want = ref_flags.get(lib.libId)
        origin = "ref"
        if want is None:
            want = src.flags(lib.libId)
            origin = "library"
        if want is None:
            notes.append("no reference or library copy for {}".format(lib.libId))
            continue
        if want[0] and not lib.hidePinNumbers:
            lib.hidePinNumbers = True
            counts["pin_numbers"] += 1
            notes.append("pin_numbers hidden on {} (from {})".format(lib.libId, origin))
        if want[1] and not lib.pinNamesHide:
            lib.pinNames = True
            lib.pinNamesHide = True
            counts["pin_names"] += 1
            notes.append("pin_names hidden on {} (from {})".format(lib.libId, origin))

    size = PAPER.get(sch.paper.paperSize) if sch.paper is not None else None
    if size is not None:
        for sym in sch.schematicSymbols:
            for prop in sym.properties:
                if not prop.effects.hide and prop.value not in ("", "~") and \
                        _off_paper(prop.position.X, prop.position.Y, size):
                    counts["off_sheet_left"] += 1
        for group in (sch.labels, sch.globalLabels, sch.hierarchicalLabels, sch.texts):
            for item in group:
                if _off_paper(item.position.X, item.position.Y, size):
                    counts["off_sheet_left"] += 1
    return counts


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="print per-sheet counts; write nothing")
    mode.add_argument("--apply", action="store_true", help="write the tidy (refuses while KiCad is open)")
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("--ref-commit", default=DEFAULT_REF_COMMIT)
    ap.add_argument("--ref-dir", default=DEFAULT_REF_DIR)
    ap.add_argument("-v", "--verbose", action="store_true", help="list each pin-flag restore")
    args = ap.parse_args()

    if args.apply:
        kiutils_k9.assert_not_open(args.root)
    docs = modify.load_project(args.root)
    ref_flags = reference_pin_flags(args.ref_commit, args.ref_dir)
    src = SourceLibraries(args.root.resolve().parent)

    cols = ("fields_hidden", "pin_numbers", "pin_names", "ai_moved", "off_sheet_left")
    print("{:32s} {:>13s} {:>11s} {:>9s} {:>8s} {:>14s}".format("sheet", *cols))
    total = dict.fromkeys(cols, 0)
    changed = 0
    for key, doc in docs.by_key.items():
        notes = []  # type: list
        c = tidy_sheet(doc.schematic, ref_flags, src, notes)
        print("{:32s} {:13d} {:11d} {:9d} {:8d} {:14d}".format(doc.path.name, *(c[k] for k in cols)))
        for k in cols:
            total[k] += c[k]
        changed += sum(c[k] for k in cols[:4])
        for n in notes:
            if args.verbose or n.startswith("no reference"):
                print("    " + n)
    print("{:32s} {:13d} {:11d} {:9d} {:8d} {:14d}".format("TOTAL", *(total[k] for k in cols)))

    if args.check:
        print("check only: nothing written")
        return 0
    if changed:
        docs.save_all()
        print("written")
    else:
        print("nothing to change")
    return 0


if __name__ == "__main__":
    sys.exit(main())

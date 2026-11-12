#!/usr/bin/env python3
"""
tidy_fields.py - Netlist-neutral field tidy for a KiCad schematic project.

Undoes the damage from kiutils round trips made before the KiCad 8/9 shim
(kiutils_k9.py, since removed) existed (docs/research/kicad-ai-tooling-2026-11/
schematic-readability.md section 3.1 steps 2-4):

  1. Hide every placed-symbol field except Reference and Value.
  2. Restore pin_numbers / pin_names hiding on embedded library symbols:
     from the reference project (v7 at c2acffc by default) for the same
     lib_id, else from the source symbol library.
  3. Move every ai_* field to its symbol's position.

It only sets hide flags and moves hidden fields: no symbol, pin, wire or
label changes, so the netlist is unchanged. Files are read and written through
tools/kicad-io/kicad_io.py (raw s-expression layer, splice save); hide flags are
written in each file's own form (KiCad 8/9 in effects, KiCad 10 on the property).

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
import modify  # noqa: E402
from modify import kio  # noqa: E402
from kicad_io import atom, atom_text, child, kids, node  # noqa: E402

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
            ls = child(kio.load_schematic(path).tree, "lib_symbols")
            for sym in (kids(ls, "symbol") if ls is not None else []):
                lib_id = str(atom(sym, 0))
                old = flags.get(lib_id, (False, False))
                new = pin_flags(sym)
                flags[lib_id] = (old[0] or new[0], old[1] or new[1])
    return flags


def pin_flags(sym) -> PinFlags:
    """(pin numbers hidden, pin names hidden) of a library symbol node."""
    pn, pm = child(sym, "pin_numbers"), child(sym, "pin_names")
    return (pn is not None and kio.is_hidden(pn), pm is not None and kio.is_hidden(pm))


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
        self.cache = {}  # type: Dict[Path, Optional[kio.Doc]]

    def flags(self, lib_id: str) -> Optional[PinFlags]:
        if ":" not in lib_id:
            return None
        nick, name = lib_id.split(":", 1)
        path = self.table.get(nick, STOCK_SYMBOLS / (nick + ".kicad_sym"))
        if path not in self.cache:
            self.cache[path] = kio.load_symbol_lib(path) if path.exists() else None
        lib = self.cache[path]
        if lib is None:
            return None
        for sym in kids(lib.tree, "symbol"):
            if atom(sym, 0) == name:
                return pin_flags(sym)
        return None


def _off_paper(x: float, y: float, size: Tuple[float, float]) -> bool:
    return x < 0 or y < 0 or x > size[0] or y > size[1]


def _value(prop) -> str:
    v = atom(prop, 1)
    return "" if v is None else str(v)


# Where a new pin_numbers / pin_names node goes in a library symbol: after these heads (KiCad's
# order: name, extends, power, pin_numbers, pin_names, exclude_from_sim, in_bom, on_board, ...).
_PIN_FLAG_AFTER = {"pin_numbers": ("extends", "power"), "pin_names": ("extends", "power", "pin_numbers")}


def _set_pin_flag(doc, lib, name: str) -> None:
    """Hide pin_numbers / pin_names on a library symbol, in the doc's own form."""
    n = child(lib, name)
    if n is None:
        n = node("({})".format(name))
        idx = 0
        for i, c in enumerate(lib.children):
            if c.is_atom or c.name in _PIN_FLAG_AFTER[name]:
                idx = i + 1
        lib.children.insert(idx, n)
    kio.hide(doc, n)


def tidy_sheet(doc, ref_flags: Dict[str, PinFlags], src: SourceLibraries,
               notes: list) -> Dict[str, int]:
    """doc is a kicad_io.Doc; its tree is edited in place."""
    sch = doc.tree
    counts = {"fields_hidden": 0, "pin_numbers": 0, "pin_names": 0, "ai_moved": 0, "off_sheet_left": 0}

    for sym in kids(sch, "symbol"):
        sx, sy, _ = kio.at_xy(sym)
        for prop in kids(sym, "property"):
            key = str(atom(prop, 0))
            # An empty field draws nothing: KiCad 9's save adds an empty, unhidden Description to
            # placed symbols (Phase 11c GUI pass), so empty values are left alone.
            if key not in KEEP_VISIBLE and not kio.is_hidden(prop) and _value(prop) not in ("", "~"):
                kio.hide(doc, prop)
                counts["fields_hidden"] += 1
            if key.startswith(AI_PREFIX):
                px, py, _ = kio.at_xy(prop)
                if px != sx or py != sy:
                    at = child(sym, "at")
                    prop.children[prop.children.index(child(prop, "at"))] = node("(at {} {} 0)".format(
                        atom_text(at, 0), atom_text(at, 1)))
                    counts["ai_moved"] += 1

    ls = child(sch, "lib_symbols")
    for lib in (kids(ls, "symbol") if ls is not None else []):
        lib_id = str(atom(lib, 0))
        want = ref_flags.get(lib_id)
        origin = "ref"
        if want is None:
            want = src.flags(lib_id)
            origin = "library"
        if want is None:
            notes.append("no reference or library copy for {}".format(lib_id))
            continue
        have = pin_flags(lib)
        if want[0] and not have[0]:
            _set_pin_flag(doc, lib, "pin_numbers")
            counts["pin_numbers"] += 1
            notes.append("pin_numbers hidden on {} (from {})".format(lib_id, origin))
        if want[1] and not have[1]:
            _set_pin_flag(doc, lib, "pin_names")
            counts["pin_names"] += 1
            notes.append("pin_names hidden on {} (from {})".format(lib_id, origin))

    paper = child(sch, "paper")
    size = PAPER.get(str(atom(paper, 0))) if paper is not None else None
    if size is not None:
        for sym in kids(sch, "symbol"):
            for prop in kids(sym, "property"):
                px, py, _ = kio.at_xy(prop)
                if not kio.is_hidden(prop) and _value(prop) not in ("", "~") and _off_paper(px, py, size):
                    counts["off_sheet_left"] += 1
        for tag in ("label", "global_label", "hierarchical_label", "text"):
            for item in kids(sch, tag):
                x, y, _ = kio.at_xy(item)
                if _off_paper(x, y, size):
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
        kio.assert_not_open(args.root)
    docs = modify.load_project(args.root)
    ref_flags = reference_pin_flags(args.ref_commit, args.ref_dir)
    src = SourceLibraries(args.root.resolve().parent)

    cols = ("fields_hidden", "pin_numbers", "pin_names", "ai_moved", "off_sheet_left")
    print("{:32s} {:>13s} {:>11s} {:>9s} {:>8s} {:>14s}".format("sheet", *cols))
    total = dict.fromkeys(cols, 0)
    changed = 0
    for key, doc in docs.by_key.items():
        notes = []  # type: list
        c = tidy_sheet(doc.doc, ref_flags, src, notes)
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

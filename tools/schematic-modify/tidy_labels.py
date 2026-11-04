#!/usr/bin/env python3
"""
tidy_labels.py - Netlist-neutral label justify pass for a KiCad schematic project.

Labels written by kiutils scripts before Phase 11b carry no `justify`, so KiCad draws them
centred on their anchor, across the wire end (Worker #13 Notes, v8-debug-board SESSION.md).
GUI autoplace moves fields, not labels. This pass gives every local, hierarchical or global
label with no justify the placement rule of modify.py (_label_angle, _make_local_label):

  - Find the wires that end at the label's anchor (a wire passing through the anchor counts as
    leaving it on both sides).
  - One wire, horizontal: the label is horizontal, its text running away from the wire
    (wire to the right -> 180, wire to the left -> 0).
  - One wire, vertical: the label is turned horizontal, away from the part per
    modify._label_angle (right of the wire unless the pin at the wire's far end is left of its
    symbol's origin).
  - Wires on more than one side, or none ending there: the angle is kept.
  - Then KiCad's own justify for the angle: local labels 0/90 "left bottom", 180/270 "right
    bottom"; hierarchical and global labels 0/90 "left", 180/270 "right".

Positions, text and kind never change, so the netlist can't change. It also removes stacked
duplicates: labels of the same kind and text at the same position and angle (one is kept).

Overlap gate: the pass is first written to a scratch copy and measured with layout_check.py. If
a sheet's overlap count would go up, every changed label in a new pair is flipped to the other
side (0 <-> 180, 90 <-> 270) and measured again. If the count still goes up, nothing is written
and the new pairs are listed.

Usage:
  python3 tools/schematic-modify/tidy_labels.py --check   # per-sheet counts, writes nothing
  python3 tools/schematic-modify/tidy_labels.py --apply   # write (refuses while KiCad is open)
  options: --root PATH (default: the v8 main board), -v (list each changed label)
"""

from __future__ import annotations

import argparse
import collections
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))
import kiutils_k9  # noqa: E402,F401  (KiCad 8/9 '(hide yes)' shim; must precede any load)
import layout_check  # noqa: E402
import modify  # noqa: E402
from kiutils.items.common import Justify  # noqa: E402

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO / "hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_sch"
TOL = 0.01
KINDS = (("label", "labels", "label"), ("hier label", "hierarchicalLabels", "shaped"),
         ("global label", "globalLabels", "shaped"))

Pt = Tuple[float, float]


def _same(a: Pt, b: Pt) -> bool:
    return abs(a[0] - b[0]) < TOL and abs(a[1] - b[1]) < TOL


def _angle(label) -> int:
    return int(round(float(label.position.angle or 0))) % 360


def _justify(angle: int, kind: str) -> Justify:
    horiz = "right" if angle in (180, 270) else "left"
    return Justify(horizontally=horiz, vertically="bottom" if kind == "label" else None)


def _just_list(angle: int, kind: str) -> List[str]:
    j = _justify(angle, kind)
    return [x for x in (j.horizontally, j.vertically) if x]


def _has_justify(label) -> bool:
    j = getattr(label.effects, "justify", None) if label.effects is not None else None
    return j is not None and bool(j.horizontally or j.vertically)


def _wires(sch) -> List[Tuple[Pt, Pt]]:
    out = []
    for w in sch.graphicalItems:
        if getattr(w, "type", None) == "wire" and len(w.points) == 2:
            out.append(((w.points[0].X, w.points[0].Y), (w.points[1].X, w.points[1].Y)))
    return out


def _pins(doc) -> Dict[Tuple[float, float], Pt]:
    """Pin end (rounded) -> its symbol's origin, for every placed symbol on the sheet."""
    out = {}
    for sym in doc.schematic.schematicSymbols:
        lib = modify.get_lib_symbol_for(doc, sym.libId)
        if lib is None or getattr(sym, "mirror", None):
            continue
        ang = float(sym.position.angle or 0)
        for _, px, py, _ in modify._pin_records(lib):
            x, y = modify._compute_pin_position(sym.position.X, sym.position.Y, ang, px, py)
            out[(round(x, 2), round(y, 2))] = (sym.position.X, sym.position.Y)
    return out


def _directions(p: Pt, wires) -> Tuple[set, Dict[str, Pt]]:
    """Directions (R, L, U, D) in which wires leave p, and the far end per direction."""
    dirs, far = set(), {}

    def d_of(a: Pt, b: Pt) -> Optional[str]:
        dx, dy = b[0] - a[0], b[1] - a[1]
        if abs(dx) < TOL and abs(dy) < TOL:
            return None
        if abs(dx) >= abs(dy):
            return "R" if dx > 0 else "L"
        return "D" if dy > 0 else "U"

    for a, b in wires:
        if _same(p, a) or _same(p, b):
            other = b if _same(p, a) else a
            d = d_of(p, other)
            if d:
                dirs.add(d)
                far[d] = other
        else:   # through the anchor: both sides
            minx, maxx = min(a[0], b[0]) - TOL, max(a[0], b[0]) + TOL
            miny, maxy = min(a[1], b[1]) - TOL, max(a[1], b[1]) + TOL
            if minx <= p[0] <= maxx and miny <= p[1] <= maxy:
                cross = (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
                if abs(cross) < TOL:
                    d1, d2 = d_of(p, a), d_of(p, b)
                    dirs.update(x for x in (d1, d2) if x)
    return dirs, far


def plan_sheet(doc) -> Tuple[List[dict], List[tuple], Dict[str, int]]:
    """Changes for one sheet: (label changes, duplicate labels to delete, counts)."""
    sch = doc.schematic
    wires = _wires(sch)
    pins = _pins(doc)
    counts = collections.Counter()
    changes = []
    dupes = []
    for kind, attr, lc_kind in KINDS:
        seen = {}
        for lab in getattr(sch, attr):
            key = (lab.text, round(lab.position.X, 2), round(lab.position.Y, 2), _angle(lab))
            if key in seen:
                dupes.append((attr, lab, kind))
                counts["deduped"] += 1
                continue
            seen[key] = lab
        for lab in getattr(sch, attr):
            if any(lab is d[1] for d in dupes) or _has_justify(lab):
                continue
            p = (lab.position.X, lab.position.Y)
            old = _angle(lab)
            dirs, far = _directions(p, wires)
            new = old
            if len(dirs) == 1:
                d = next(iter(dirs))
                if d in ("R", "L"):
                    new = 180 if d == "R" else 0
                else:
                    end = far[d]
                    sym_xy = pins.get((round(end[0], 2), round(end[1], 2)))
                    new = int(modify._label_angle(end, p, sym_xy))
            elif not dirs:
                counts["no_wire"] += 1
            else:
                counts["both_sides"] += 1
            if old in (90, 270) and new in (0, 180):
                counts["turned_horizontal"] += 1
            elif new != old:
                counts["flipped"] += 1
            counts["justified"] += 1
            changes.append(dict(label=lab, kind=kind, lc_kind=lc_kind, old=old, new=new))
    return changes, dupes, counts


def apply_changes(doc, changes, dupes) -> None:
    sch = doc.schematic
    for attr, lab, _ in dupes:
        getattr(sch, attr).remove(lab)
    for c in changes:
        lab = c["label"]
        lab.position.angle = c["new"]
        lab.effects.justify = _justify(c["new"], c["lc_kind"])


def _box(c) -> tuple:
    lab = c["label"]
    h = float(lab.effects.font.height or 1.27) if lab.effects.font else 1.27
    return layout_check.label_box(lab.position.X, lab.position.Y, c["new"], lab.text, h,
                                  _just_list(c["new"], c["lc_kind"]), c["lc_kind"])


def _pair_keys(pairs) -> collections.Counter:
    return collections.Counter(tuple(sorted(((a.name(), a.text), (b.name(), b.text)))) for _, a, b in pairs)


def measure(doc, tmp: Path) -> dict:
    out = tmp / doc.path.name
    kiutils_k9.save_schematic(doc.schematic, out)
    return layout_check.analyse(out)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true", help="print per-sheet counts; write nothing")
    mode.add_argument("--apply", action="store_true", help="write the pass (refuses while KiCad is open)")
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    ap.add_argument("-v", "--verbose", action="store_true", help="list each changed label")
    args = ap.parse_args()

    if args.apply:
        kiutils_k9.assert_not_open(args.root)
    docs = modify.load_project(args.root)
    cols = ("justified", "turned_horizontal", "flipped", "no_wire", "both_sides", "deduped", "gate_flips")
    print("{:30s} {:>9s} {:>10s} {:>7s} {:>7s} {:>10s} {:>7s} {:>10s}  overlaps before -> after".format(
        "sheet", *cols))
    total = collections.Counter()
    blocked = []
    changed = 0
    with tempfile.TemporaryDirectory() as td:
        tmp = Path(td)
        for key, doc in docs.by_key.items():
            before = layout_check.analyse(doc.path)
            changes, dupes, counts = plan_sheet(doc)
            apply_changes(doc, changes, dupes)
            after = measure(doc, tmp)
            n_before, n_after = len(before["pairs"]), len(after["pairs"])
            if n_after > n_before:
                # Flip every changed label that sits in a new pair, then measure again.
                new_pairs = _pair_keys(after["pairs"]) - _pair_keys(before["pairs"])
                in_new = [(a, b) for _, a, b in after["pairs"]
                          if tuple(sorted(((a.name(), a.text), (b.name(), b.text)))) in new_pairs]
                boxes = {t.box for pair in in_new for t in pair}
                for c in changes:
                    if _box(c) in boxes:
                        c["new"] = (c["new"] + 180) % 360
                        counts["gate_flips"] += 1
                apply_changes(doc, changes, [])
                after = measure(doc, tmp)
                n_after = len(after["pairs"])
                if n_after > n_before:
                    still = _pair_keys(after["pairs"]) - _pair_keys(before["pairs"])
                    blocked.append((doc.path.name, n_before, n_after, sorted(still.elements())))
            print("{:30s} {:9d} {:10d} {:7d} {:7d} {:10d} {:7d} {:10d}  {:3d} -> {:3d}".format(
                doc.path.name, *(counts[k] for k in cols), n_before, n_after))
            total.update(counts)
            changed += counts["justified"] + counts["deduped"]
            if args.verbose:
                for c in changes:
                    lab = c["label"]
                    print("    {:10s} {:22s} ({}, {}) {:3d} -> {:3d}".format(
                        c["kind"], lab.text, lab.position.X, lab.position.Y, c["old"], c["new"]))
                for _, lab, kind in dupes:
                    print("    removed duplicate {} '{}' at ({}, {})".format(kind, lab.text, lab.position.X,
                                                                         lab.position.Y))
    print("{:30s} {:9d} {:10d} {:7d} {:7d} {:10d} {:7d} {:10d}".format("TOTAL", *(total[k] for k in cols)))
    if blocked:
        print("BLOCKED: overlap count would go up even after flipping; nothing written")
        for name, b, a, pairs in blocked:
            print("  {}: {} -> {}".format(name, b, a))
            for p in pairs:
                print("    {} '{}' / {} '{}'".format(p[0][0], p[0][1], p[1][0], p[1][1]))
        return 1
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

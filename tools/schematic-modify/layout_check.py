#!/usr/bin/env python3
"""
layout_check.py - Readability check for a KiCad schematic project (read-only).

Method: docs/research/kicad-ai-tooling-2026-11/schematic-readability.md section 1.1 (prototype
prototypes/probe.py), with the field geometry KiCad uses (a field's angle and justification are
in its symbol's frame, then turned with the symbol) and sheet-pin / sheet-field text on the root.

Per sheet, it fails on:
  1. a visible field other than Reference/Value on a non-power symbol;
  2. any text or symbol outside the paper (symbol bodies, visible text boxes, and the anchors of
     hidden fields, which still count for KiCad's zoom-to-fit);
  3. text-overlap pairs above the sheet's committed baseline (two visible text boxes overlapping
     by more than 25 % of the smaller one: Reference/Value, labels, sheet pins, text items);
  4. identical labels stacked on one point (same kind, text and position; counted as the labels
     in such stacks), above the baseline;
  5. a local, global or hierarchical label with no justify (KiCad draws it centred across its
     wire end; Phase 11c, tidy_labels.py). No baseline: none is allowed;
  6. a T-touch: a wire end or pin end on the interior of a wire, with no junction there.
     kicad-cli and the KiCad editor can disagree on whether it connects (Phase 11c: the editor
     joined a TCA SCL wire end to a pull-up stub that kicad-cli kept separate). No baseline: none
     is allowed. End the wire at the point, or add a junction. A label anchor on a wire's
     interior is not a T-touch: both tools connect it, and KiCad's own save produces it when it
     merges collinear wire segments (Phase 11c GUI pass). It is listed with -v only.

The baseline (layout_baseline.json beside this script) is keyed by "<project>/<sheet>": the root
sheet's file stem, then the sheet's path relative to the root sheet's folder. So a scratch copy of
a project (--root <copy>/X.kicad_sch) is checked against the same baseline as the working tree.
It only ratchets down. A count below it is reported, and --update-baseline records it.
--update-baseline never raises a baseline; a sheet with no baseline yet is recorded as it stands.
It refuses a root outside this repository, so a scratch copy never writes the committed baseline.
To accept more overlaps on purpose, edit the JSON by hand in a commit that says why.

The worst spots are printed by sheet grid zone (KiCad's default frame: columns 1.. every 50 mm
from the 10 mm margin, rows A.. every 50 mm), e.g. "C3".

Text boxes are approximate (0.72 x height per character, 1.1 x height tall), so overlap counts
are indicators. It parses the files as raw s-expressions and writes nothing but the baseline.

Usage:
  python3 tools/schematic-modify/layout_check.py                     # v8 main board
  python3 tools/schematic-modify/layout_check.py --root X.kicad_sch  # another project
  python3 tools/schematic-modify/layout_check.py --update-baseline   # record lower counts
  python3 tools/schematic-modify/layout_check.py -v                  # list every overlap pair
Exit status: 0 pass, 1 fail.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from kiutils.utils.sexpr import parse_sexp

REPO = Path(__file__).resolve().parents[2]
DEFAULT_ROOT = REPO / "hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_sch"
BASELINE = Path(__file__).resolve().parent / "layout_baseline.json"

PAPER = {"A5": (210, 148), "A4": (297, 210), "A3": (420, 297), "A2": (594, 420), "A1": (841, 594),
         "A0": (1189, 841), "A": (279.4, 215.9), "B": (431.8, 279.4), "C": (558.8, 431.8),
         "D": (863.6, 558.8), "E": (1117.6, 863.6), "USLetter": (279.4, 215.9),
         "USLegal": (355.6, 215.9), "USLedger": (431.8, 279.4)}
KEEP_VISIBLE = {"Reference", "Value"}
OVERLAP_FRACTION = 0.25
CHAR_W = 0.85        # character advance / text height (median of kicad-cli SVG plots)
LINE_H = 1.1         # box height / text height
SHAPE_GAP = 1.5     # global/hierarchical label: anchor to text start / text height
PIN_GAP = 1.1       # sheet pin: anchor to text start / text height
NOJUST_SHIFT = 1.2  # shaped label or sheet pin without a justify: text centre past the anchor
MARGIN = 10.0        # default drawing-sheet frame margin (mm)
ZONE = 50.0          # default drawing-sheet zone pitch (mm)

Box = Tuple[float, float, float, float]


# ---------------------------------------------------------------------------
# s-expression helpers
# ---------------------------------------------------------------------------

def kids(e, name):
    return [x for x in e if isinstance(x, list) and x and x[0] == name]


def kid(e, name):
    k = kids(e, name)
    return k[0] if k else None


def at_of(e) -> Tuple[float, float, float]:
    a = kid(e, "at")
    return float(a[1]), float(a[2]), float(a[3]) if len(a) > 3 else 0.0


def is_hidden(prop) -> bool:
    h = kid(prop, "hide")
    if h is not None and h[1:2] == ["yes"]:
        return True
    eff = kid(prop, "effects")
    if eff is None:
        return False
    if "hide" in eff:
        return True
    h = kid(eff, "hide")
    return bool(h is not None and (len(h) == 1 or h[1] == "yes"))


def font_h(e) -> float:
    eff = kid(e, "effects")
    if eff is not None:
        f = kid(eff, "font")
        if f is not None and kid(f, "size") is not None:
            return float(kid(f, "size")[1])
    return 1.27


def justify(e) -> List[str]:
    eff = kid(e, "effects")
    j = kid(eff, "justify") if eff is not None else None
    return [str(x) for x in j[1:]] if j else []


def paper_size(t) -> Tuple[float, float]:
    p = kid(t, "paper")
    if p is None:
        return PAPER["A4"]
    if p[1] == "User":
        w, h = float(p[2]), float(p[3])
    else:
        w, h = PAPER.get(p[1], PAPER["A4"])
    if "portrait" in p[2:]:
        w, h = min(w, h), max(w, h)
    return float(w), float(h)


# ---------------------------------------------------------------------------
# Geometry
# ---------------------------------------------------------------------------

def sym_matrix(angle: float, mirror: Optional[str]):
    """Screen-frame (y down) transform of a placed symbol: rotate CCW on screen, then mirror."""
    a = math.radians(angle)
    c, s = round(math.cos(a), 6), round(math.sin(a), 6)
    m = [[c, s], [-s, c]]
    if mirror == "x":      # flip about the horizontal axis
        m = [[m[0][0], m[0][1]], [-m[1][0], -m[1][1]]]
    elif mirror == "y":    # flip about the vertical axis
        m = [[-m[0][0], -m[0][1]], [m[1][0], m[1][1]]]
    return m


def apply(m, v):
    return m[0][0] * v[0] + m[0][1] * v[1], m[1][0] * v[0] + m[1][1] * v[1]


def text_extent(text: str, h: float) -> Tuple[float, float]:
    lines = str(text).split("\\n") if "\\n" in str(text) else str(text).split("\n")
    w = max(1, max(len(l) for l in lines)) * h * CHAR_W
    return w, h * LINE_H * len(lines) + h * 0.6 * (len(lines) - 1)


def field_box(x, y, fang, text, h, just, m) -> Box:
    """KiCad's field bbox: text box in the symbol's frame (field angle and justification),
    then turned with the symbol about the field's own position."""
    w, hh = text_extent(text, h)
    if "left" in just:
        u0, u1 = 0.0, w
    elif "right" in just:
        u0, u1 = -w, 0.0
    else:
        u0, u1 = -w / 2, w / 2
    if "top" in just:
        v0, v1 = 0.0, hh
    elif "bottom" in just:
        v0, v1 = -hh, 0.0
    else:
        v0, v1 = -hh / 2, hh / 2
    a = math.radians(fang)
    d = (round(math.cos(a), 6), -round(math.sin(a), 6))       # along the text (screen, y down)
    n = (-d[1], d[0])                                           # down the text
    pts = []
    for u in (u0, u1):
        for v in (v0, v1):
            p = apply(m, (u * d[0] + v * n[0], u * d[1] + v * n[1]))
            pts.append((x + p[0], y + p[1]))
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    return min(xs), min(ys), max(xs), max(ys)


def free_text_box(x, y, ang, text, h, just) -> Box:
    """A text item or label-like text without a symbol: angle and justification on screen."""
    return field_box(x, y, ang, text, h, just, [[1, 0], [0, 1]])


def label_box(x, y, ang, text, h, just, kind) -> Box:
    """A label's text box. KiCad draws a label's text at 0 deg for a 0/180 label and at 90 deg for
    a 90/270 one, with the file's justification on screen. KiCad itself always writes a justify
    (left bottom / right bottom); a local label written without one (older kiutils scripts) is
    drawn centred on its anchor, across the wire end. kind is "label" (local), "shaped" (global
    or hierarchical) or "pin" (sheet pin). Offsets measured on kicad-cli 9.0.4 SVG plots."""
    a = int(round(ang)) % 360
    tang = 90 if a in (90, 270) else 0
    ident = [[1, 0], [0, 1]]
    if kind == "label":
        return field_box(x, y, tang, text, h, just, ident)
    lr = [j for j in just if j in ("left", "right")]
    if lr:   # the text starts after the flag
        shift = h * (SHAPE_GAP if kind == "shaped" else PIN_GAP) * (1 if lr[0] == "left" else -1)
    else:    # no justify: centred a little past the anchor
        shift = h * NOJUST_SHIFT
    dx, dy = (0.0, -shift) if tang == 90 else (shift, 0.0)
    return field_box(x + dx, y + dy, tang, text, h, lr, ident)


def overlap(a: Box, b: Box) -> float:
    ix = min(a[2], b[2]) - max(a[0], b[0])
    iy = min(a[3], b[3]) - max(a[1], b[1])
    if ix <= 0 or iy <= 0:
        return 0.0
    sa = (a[2] - a[0]) * (a[3] - a[1])
    sb = (b[2] - b[0]) * (b[3] - b[1])
    return ix * iy / max(1e-9, min(sa, sb))


def lib_points(lib, unit: int, convert: int) -> List[Tuple[float, float]]:
    """Body points of one unit (lib coords, y up): unit 0 is shared by all units."""
    pts = []

    def walk(e, ok):
        for x in e:
            if not isinstance(x, list) or not x:
                continue
            if x[0] == "symbol":
                parts = str(x[1]).rsplit("_", 2)
                sub_ok = ok
                if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                    u, c = int(parts[1]), int(parts[2])
                    sub_ok = (u in (0, unit)) and (c in (0, convert))
                if sub_ok:
                    walk(x, True)
            elif not ok:
                continue
            elif x[0] == "rectangle":
                for k in ("start", "end"):
                    p = kid(x, k)
                    pts.append((float(p[1]), float(p[2])))
            elif x[0] == "pin":
                px, py, pa = at_of(x)
                ln = float(kid(x, "length")[1]) if kid(x, "length") else 0.0
                pts.append((px, py))
                pts.append((px + ln * math.cos(math.radians(pa)), py + ln * math.sin(math.radians(pa))))
            elif x[0] in ("polyline", "bezier"):
                for p in kids(kid(x, "pts") or [], "xy"):
                    pts.append((float(p[1]), float(p[2])))
            elif x[0] == "circle":
                c = kid(x, "center")
                r = float(kid(x, "radius")[1])
                pts.extend([(float(c[1]) - r, float(c[2]) - r), (float(c[1]) + r, float(c[2]) + r)])
            elif x[0] == "arc":
                for k in ("start", "mid", "end"):
                    p = kid(x, k)
                    if p is not None:
                        pts.append((float(p[1]), float(p[2])))

    walk(lib, True)
    return pts


def lib_pins(lib, unit: int, convert: int) -> List[Tuple[float, float]]:
    """Pin connection points of one unit (lib coords, y up); unit 0 is shared by all units."""
    pts = []

    def walk(e, ok):
        for x in e:
            if not isinstance(x, list) or not x:
                continue
            if x[0] == "symbol":
                parts = str(x[1]).rsplit("_", 2)
                sub_ok = ok
                if len(parts) == 3 and parts[1].isdigit() and parts[2].isdigit():
                    u, c = int(parts[1]), int(parts[2])
                    sub_ok = (u in (0, unit)) and (c in (0, convert))
                if sub_ok:
                    walk(x, True)
            elif ok and x[0] == "pin":
                px, py, _ = at_of(x)
                pts.append((px, py))

    walk(lib, True)
    return pts


def _on_interior(p, a, b, tol: float = 0.01) -> bool:
    if (abs(p[0] - a[0]) < tol and abs(p[1] - a[1]) < tol) or (abs(p[0] - b[0]) < tol and abs(p[1] - b[1]) < tol):
        return False
    if not (min(a[0], b[0]) - tol <= p[0] <= max(a[0], b[0]) + tol and
            min(a[1], b[1]) - tol <= p[1] <= max(a[1], b[1]) + tol):
        return False
    return abs((b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])) < tol


def t_touches(t, libs) -> List[str]:
    """Wire ends and pin ends on the interior of a wire, with no junction there (fail), and label
    anchors on a wire's interior (listed, not failed: both tools connect them)."""
    wires = []
    for w in kids(t, "wire"):
        xy = kids(kid(w, "pts") or [], "xy")
        if len(xy) == 2:
            wires.append(((float(xy[0][1]), float(xy[0][2])), (float(xy[1][1]), float(xy[1][2]))))
    junctions = [at_of(j)[:2] for j in kids(t, "junction")]
    points = []
    for a, b in wires:
        points += [("wire end", a), ("wire end", b)]
    for s in kids(t, "symbol"):
        lid = kid(s, "lib_id")[1]
        if lid not in libs:
            continue
        sx, sy, sa = at_of(s)
        mir = kid(s, "mirror")
        m = sym_matrix(sa, mir[1] if mir else None)
        unit = int(kid(s, "unit")[1]) if kid(s, "unit") else 1
        conv = int(kid(s, "convert")[1]) if kid(s, "convert") else 1
        ref = next((p[2] for p in kids(s, "property") if p[1] == "Reference"), "?")
        for px, py in lib_pins(libs[lid], unit, conv):
            dx, dy = apply(m, (px, -py))
            points.append(("pin of " + ref, (round(sx + dx, 4), round(sy + dy, 4))))
    for kind, tag in (("label", "label"), ("global label", "global_label"), ("hier label", "hierarchical_label")):
        for l in kids(t, tag):
            x, y, _ = at_of(l)
            points.append(("{} '{}'".format(kind, l[1]), (x, y)))
    out, labels = [], []
    for what, p in points:
        if any(abs(p[0] - j[0]) < 0.01 and abs(p[1] - j[1]) < 0.01 for j in junctions):
            continue
        for a, b in wires:
            if _on_interior(p, a, b):
                (labels if "label" in what else out).append("{} at ({:.2f}, {:.2f}) on wire ({:.2f}, {:.2f})-({:.2f}, {:.2f})".format(
                    what, p[0], p[1], a[0], a[1], b[0], b[1]))
    return out, labels


def zone(x: float, y: float, pw: float, ph: float) -> str:
    cols = max(1, int((pw - 2 * MARGIN) // ZONE))
    rows = max(1, int((ph - 2 * MARGIN) // ZONE))
    c = min(cols, max(1, int((x - MARGIN) // ZONE) + 1))
    r = min(rows, max(1, int((y - MARGIN) // ZONE) + 1))
    return "{}{}".format(chr(ord("A") + r - 1), c)


# ---------------------------------------------------------------------------
# Analysis
# ---------------------------------------------------------------------------

class Text:
    __slots__ = ("kind", "owner", "text", "box")

    def __init__(self, kind, owner, text, box):
        self.kind, self.owner, self.text, self.box = kind, owner, text, box

    def name(self) -> str:
        return "{} {}".format(self.owner, self.kind) if self.owner else "{} '{}'".format(self.kind, self.text)


def analyse(path: Path) -> dict:
    t = parse_sexp(path.read_text())
    pw, ph = paper_size(t)

    def outside(b: Box) -> bool:
        return b[0] < 0 or b[1] < 0 or b[2] > pw or b[3] > ph

    libs = {l[1]: l for l in kids(kid(t, "lib_symbols") or [], "symbol")}
    texts: List[Text] = []
    extra_visible: List[str] = []
    off_paper: List[str] = []

    for s in kids(t, "symbol"):
        lid = kid(s, "lib_id")[1]
        sx, sy, sa = at_of(s)
        mir = kid(s, "mirror")
        m = sym_matrix(sa, mir[1] if mir else None)
        unit = int(kid(s, "unit")[1]) if kid(s, "unit") else 1
        conv = int(kid(s, "convert")[1]) if kid(s, "convert") else 1
        props = kids(s, "property")
        ref = next((p[2] for p in props if p[1] == "Reference"), "?")
        power = ref.startswith("#")
        pts = lib_points(libs[lid], unit, conv) if lid in libs else []
        if pts:
            tp = [apply(m, (px, -py)) for px, py in pts]
            body = (sx + min(p[0] for p in tp), sy + min(p[1] for p in tp),
                    sx + max(p[0] for p in tp), sy + max(p[1] for p in tp))
        else:
            body = (sx, sy, sx, sy)
        if outside(body):
            off_paper.append("symbol {} at ({:.1f}, {:.1f})".format(ref, sx, sy))
        for p in props:
            key, val = p[1], p[2]
            px, py, pa = at_of(p)
            hidden = is_hidden(p) or val in ("", "~") or (power and key == "Reference")
            if hidden:
                if not (0 <= px <= pw and 0 <= py <= ph):
                    off_paper.append("hidden field {} {} at ({:.1f}, {:.1f})".format(ref, key, px, py))
                continue
            if key not in KEEP_VISIBLE and not power:
                extra_visible.append("{} {}={}".format(ref, key, val))
            b = field_box(px, py, pa, val, font_h(p), justify(p), m)
            if outside(b):
                off_paper.append("field {} {} '{}'".format(ref, key, val))
            texts.append(Text(key, ref, val, b))

    stacks = collections.Counter()
    unjustified: List[str] = []
    for kind, tag in (("label", "label"), ("global label", "global_label"), ("hier label", "hierarchical_label")):
        for l in kids(t, tag):
            x, y, a = at_of(l)
            if not justify(l):
                unjustified.append("{} '{}' at ({:.2f}, {:.2f})".format(kind, l[1], x, y))
            b = label_box(x, y, a, l[1], font_h(l), justify(l), "label" if tag == "label" else "shaped")
            if outside(b):
                off_paper.append("{} '{}' at ({:.1f}, {:.1f})".format(kind, l[1], x, y))
            texts.append(Text(kind, "", l[1], b))
            stacks[(kind, l[1], round(x, 2), round(y, 2))] += 1
    for tx in kids(t, "text"):
        x, y, a = at_of(tx)
        b = free_text_box(x, y, a, tx[1], font_h(tx), justify(tx))
        if outside(b):
            off_paper.append("text '{}'".format(str(tx[1])[:30]))
        texts.append(Text("text", "", str(tx[1]).split("\n")[0][:30], b))
    for sh in kids(t, "sheet"):
        x, y, _ = at_of(sh)
        size = kid(sh, "size")
        body = (x, y, x + float(size[1]), y + float(size[2]))
        name = next((p[2] for p in kids(sh, "property") if p[1] in ("Sheetname", "Sheet name")), "?")
        if outside(body):
            off_paper.append("sheet {}".format(name))
        for p in kids(sh, "property"):
            if is_hidden(p) or p[2] in ("", "~"):
                continue
            px, py, pa = at_of(p)
            texts.append(Text(p[1], "sheet " + name, p[2], free_text_box(px, py, pa, p[2], font_h(p), justify(p))))
        for pin in kids(sh, "pin"):
            px, py, pa = at_of(pin)
            b = label_box(px, py, pa, pin[1], font_h(pin), justify(pin), "pin")
            texts.append(Text("sheet pin", "", pin[1], b))

    pairs = []
    n = len(texts)
    for i in range(n):
        bi = texts[i].box
        for j in range(i + 1, n):
            if overlap(bi, texts[j].box) > OVERLAP_FRACTION:
                bj = texts[j].box
                cx = (max(bi[0], bj[0]) + min(bi[2], bj[2])) / 2
                cy = (max(bi[1], bj[1]) + min(bi[3], bj[3])) / 2
                pairs.append((zone(cx, cy, pw, ph), texts[i], texts[j]))
    stacked = [(k, c) for k, c in stacks.items() if c > 1]
    return dict(paper=(pw, ph), texts=len(texts), extra_visible=extra_visible, off_paper=off_paper,
                unjustified=unjustified, **dict(zip(("t_touches", "mid_wire_labels"), t_touches(t, libs))),
                pairs=pairs, stacked=stacked, stacked_count=sum(c for _, c in stacked))


# ---------------------------------------------------------------------------
# Project, baseline, report
# ---------------------------------------------------------------------------

def project_sheets(root: Path) -> List[Path]:
    """Root first, then every sub-sheet file once, depth first."""
    out, seen = [], set()

    def visit(p: Path):
        p = p.resolve()
        if p in seen or not p.exists():
            return
        seen.add(p)
        out.append(p)
        t = parse_sexp(p.read_text())
        for sh in kids(t, "sheet"):
            f = next((q[2] for q in kids(sh, "property") if q[1] in ("Sheetfile", "Sheet file")), None)
            if f:
                visit(p.parent / f)

    visit(root)
    return out


def rel(p: Path) -> str:
    try:
        return str(p.resolve().relative_to(REPO))
    except ValueError:
        return str(p.resolve())


def baseline_key(sheet: Path, root: Path) -> str:
    """'<root sheet stem>/<sheet path relative to the root sheet's folder>'."""
    root = root.resolve()
    try:
        r = sheet.resolve().relative_to(root.parent).as_posix()
    except ValueError:
        r = sheet.resolve().as_posix()
    return "{}/{}".format(root.stem, r)


def load_baseline() -> Dict[str, dict]:
    if BASELINE.exists():
        return json.loads(BASELINE.read_text()).get("sheets", {})
    return {}


def save_baseline(sheets: Dict[str, dict]) -> None:
    doc = {"_about": "layout_check.py per-sheet baseline: overlap_pairs and stacked_labels only ratchet "
                     "down (--update-baseline). Raise one only by hand, in a commit that says why.",
           "sheets": {k: sheets[k] for k in sorted(sheets)}}
    BASELINE.write_text(json.dumps(doc, indent=2) + "\n")


def run(root: Path = DEFAULT_ROOT, update_baseline: bool = False, verbose: bool = False,
        worst: int = 3) -> int:
    """Check every sheet of the project; print a report. Returns the number of failures."""
    if update_baseline and rel(root) == str(root.resolve()):
        print("Refusing --update-baseline: {} is outside the repository (a scratch copy)".format(root))
        return 1
    base = load_baseline()
    new_base = dict(base)
    fails = 0
    changed = []
    print("=== Layout check ({}) ===".format(rel(root)))
    for sheet in project_sheets(root):
        key = baseline_key(sheet, root)
        r = analyse(sheet)
        b = base.get(key)
        n_ov, n_st = len(r["pairs"]), r["stacked_count"]
        b_ov = b["overlap_pairs"] if b else 0
        b_st = b["stacked_labels"] if b else 0
        if update_baseline and b is None:   # a sheet's first baseline is what it is now
            b_ov, b_st = n_ov, n_st
        bad = []
        if r["extra_visible"]:
            bad.append("{} visible fields other than Reference/Value".format(len(r["extra_visible"])))
        if r["off_paper"]:
            bad.append("{} items outside the paper".format(len(r["off_paper"])))
        if r["t_touches"]:
            bad.append("{} T-touches with no junction".format(len(r["t_touches"])))
        if r["unjustified"]:
            bad.append("{} labels with no justify (tidy_labels.py)".format(len(r["unjustified"])))
        if n_ov > b_ov:
            bad.append("overlaps {} > baseline {}".format(n_ov, b_ov))
        if n_st > b_st:
            bad.append("stacked labels {} > baseline {}".format(n_st, b_st))
        notes = []
        if b is None:
            notes.append("baseline recorded" if update_baseline else "no baseline")
        else:
            if n_ov < b_ov:
                notes.append("overlaps below baseline {}".format(b_ov))
            if n_st < b_st:
                notes.append("stacked labels below baseline {}".format(b_st))
        fails += len(bad)
        print("  {} {:28s} overlaps {:3d}  stacked labels {:2d}{}{}".format(
            "BAD" if bad else "ok ", sheet.name, n_ov, n_st,
            "  [" + "; ".join(bad) + "]" if bad else "", "  (" + "; ".join(notes) + ")" if notes else ""))
        for item in r["extra_visible"][: 10 if not verbose else None]:
            print("      visible: " + item)
        for item in r["off_paper"][: 10 if not verbose else None]:
            print("      off paper: " + item)
        for item in r["t_touches"]:
            print("      T-touch: " + item)
        if verbose:
            for item in r["mid_wire_labels"]:
                print("      label on a wire's interior (connects in both tools): " + item)
        for item in r["unjustified"][: 10 if not verbose else None]:
            print("      no justify: " + item)
        if r["pairs"] and (worst or verbose):
            zc = collections.Counter(z for z, _, _ in r["pairs"])
            spots = []
            for z, c in zc.most_common(worst):
                ex = next((a, bb) for zz, a, bb in r["pairs"] if zz == z)
                spots.append("{} {} (e.g. {} / {})".format(z, c, ex[0].name(), ex[1].name()))
            print("      worst zones: " + "; ".join(spots))
        if verbose:
            for z, a, bb in r["pairs"]:
                print("      {:4s} {} '{}' / {} '{}'".format(z, a.name(), a.text, bb.name(), bb.text))
            for (kind, text, x, y), c in r["stacked"]:
                print("      stacked x{} {} '{}' at ({}, {}) {}".format(c, kind, text, x, y, zone(x, y, *r["paper"])))
        if update_baseline:
            nb = {"overlap_pairs": n_ov if b is None else min(n_ov, b_ov),
                  "stacked_labels": n_st if b is None else min(n_st, b_st)}
            if nb != b:
                new_base[key] = nb
                changed.append("{}: {} -> {}".format(sheet.name, b, nb))
            if b is not None and (n_ov > b_ov or n_st > b_st):
                print("      (baseline not raised: it only ratchets down)")
    if update_baseline:
        if changed:
            save_baseline(new_base)
            print("Baseline updated ({}): {}".format(rel(BASELINE), "; ".join(changed)))
        else:
            print("Baseline unchanged.")
    print("LAYOUT CHECK {}".format("PASSED" if fails == 0 else "FAILED ({} problems)".format(fails)))
    return fails


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--root", type=Path, default=DEFAULT_ROOT, help="root .kicad_sch (default: v8 main board)")
    ap.add_argument("--update-baseline", action="store_true", help="record lower counts (never raises one)")
    ap.add_argument("--worst", type=int, default=3, help="worst zones to print per sheet (default 3)")
    ap.add_argument("-v", "--verbose", action="store_true", help="list every overlap pair and stack")
    args = ap.parse_args()
    return 1 if run(args.root, args.update_baseline, args.verbose, args.worst) else 0


if __name__ == "__main__":
    sys.exit(main())

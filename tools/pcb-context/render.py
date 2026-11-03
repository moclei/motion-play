#!/usr/bin/env python3
"""
render.py: PNGs from a board model (board_model.py), one per critical net and
one per plane layer, each with a `<name>.png.meta.json` provenance sidecar
(tools/CONTEXT.md Source-Hash Rule).

Spec: docs/research/v7-retry/kicad-extraction-audit.md §5.4 (3).
  Net image:   board outline, footprint bodies and pads faded, other copper
               faint, the target net coloured by layer, its pads and vias
               labelled (leader line to the pad/via centre, dot on the centre),
               neighbours within the radius (report_lib.neighbours) highlighted
               by class and labelled, unreferenced stretches (antipads
               excluded) dashed.
  Plane image: zone fills by net, voids and split gaps hatched, keepouts
               dashed, the critical nets' tracks on the adjacent layer(s),
               GND vias as dots.
The meta file records the view (mm), the image size, the axes pixel box and
every label's anchor in mm and px, so a reader can map pixels to board mm.

Usage:
    python render.py <board-model.json> [-o OUTDIR] [--net NET ...] [--layer LAYER ...]
Default OUTDIR: <model folder>/img. Default nets: the config's critical_nets;
default layers: every copper layer with a zone fill.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

import matplotlib  # noqa: E402
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch, PathPatch  # noqa: E402
from matplotlib.path import Path as MPath  # noqa: E402
from shapely.geometry import Point, box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from board_model import BoardModel, poly_from_json  # noqa: E402
from report_lib import (Geo, derived_provenance, neighbours,  # noqa: E402
                        reference_for_line, safe_name, short, write_json)

GENERATOR = "tools/pcb-context/render.py"

LAYER_COLOURS = {"F.Cu": "#c62828", "B.Cu": "#1565c0", "In1.Cu": "#2e7d32", "In2.Cu": "#ef6c00"}
CLASS_COLOURS = {"signal": "#ff9800", "high_current": "#8e24aa", "high_dvdt": "#d81b60"}
NET_PALETTE = ["#9e9e9e", "#ffb74d", "#e57373", "#81c784", "#64b5f6", "#ba68c8", "#4db6ac", "#f06292"]
DPI = 160


# ---------------------------------------------------------------------------
# Drawing helpers
# ---------------------------------------------------------------------------

def _ring_codes(coords) -> Tuple[List, List]:
    pts = list(coords)
    return pts, [MPath.MOVETO] + [MPath.LINETO] * (len(pts) - 2) + [MPath.CLOSEPOLY]


def add_poly(ax, geom, **kw):
    if geom is None or geom.is_empty:
        return
    polys = []
    if geom.geom_type == "Polygon":
        polys = [geom]
    elif hasattr(geom, "geoms"):
        for g in geom.geoms:
            if g.geom_type == "Polygon":
                polys.append(g)
            elif hasattr(g, "geoms"):
                polys += [h for h in g.geoms if h.geom_type == "Polygon"]
    verts, codes = [], []
    for p in polys:
        for ring in [p.exterior] + list(p.interiors):
            v, c = _ring_codes(ring.coords)
            if len(v) < 3:
                continue
            verts += v
            codes += c
    if verts:
        ax.add_patch(PathPatch(MPath(verts, codes), **kw))


def add_line(ax, geom, **kw):
    if geom is None or geom.is_empty:
        return
    parts = [geom] if geom.geom_type == "LineString" else [g for g in getattr(geom, "geoms", [])
                                                         if g.geom_type == "LineString"]
    for ln in parts:
        xs, ys = zip(*ln.coords)
        ax.plot(xs, ys, **kw)


class Labeller:
    """Greedy label placement: text off to one side with a leader to the anchor."""

    def __init__(self, ax, fig, view, fontsize=7):
        self.ax, self.fig, self.fs = ax, fig, fontsize
        x0, y0, x1, y1 = view
        ax.apply_aspect()
        w_in = fig.get_size_inches()[0] * ax.get_position().width
        self.mm_per_pt = (x1 - x0) / (w_in * 72.0)
        self.boxes: List[Any] = []
        self.placed: List[Dict[str, Any]] = []
        self.view = view

    def _box(self, x, y, text, ha, va):
        w = len(text) * self.fs * 0.6 * self.mm_per_pt
        h = self.fs * 1.3 * self.mm_per_pt
        x0 = x if ha == "left" else (x - w if ha == "right" else x - w / 2)
        y0 = y if va == "top" else (y - h if va == "bottom" else y - h / 2)   # Y axis is inverted
        return box(x0, y0, x0 + w, y0 + h)

    def add(self, x, y, text, colour="#000", avoid: Optional[List[Any]] = None, kind="pad"):
        d = 2.2 * self.fs * self.mm_per_pt
        cands = []
        for k in (1.0, 1.8, 2.8, 4.0):
            for dx, dy in ((1, -1), (1, 1), (-1, -1), (-1, 1), (0, -1.3), (0, 1.3), (1.4, 0), (-1.4, 0)):
                cands.append((x + dx * d * k, y + dy * d * k, dx, dy))
        best = None
        for (tx, ty, dx, dy) in cands:
            ha = "left" if dx > 0 else ("right" if dx < 0 else "center")
            va = "bottom" if dy < 0 else ("top" if dy > 0 else "center")
            b = self._box(tx, ty, text, ha, va)
            vx0, vy0, vx1, vy1 = self.view
            if not box(vx0, vy0, vx1, vy1).contains(b):
                continue
            hit = sum(1 for o in self.boxes if o.intersects(b)) * 10 + \
                sum(1 for o in (avoid or []) if o.intersects(b))
            if best is None or hit < best[0]:
                best = (hit, tx, ty, ha, va, b)
            if hit == 0:
                break
        if best is None:
            best = (0, x, y, "left", "bottom", self._box(x, y, text, "left", "bottom"))
        _, tx, ty, ha, va, b = best
        self.boxes.append(b)
        self.ax.annotate(text, xy=(x, y), xytext=(tx, ty), fontsize=self.fs, color=colour, ha=ha, va=va,
                         arrowprops=dict(arrowstyle="-", color=colour, lw=0.6, shrinkA=0, shrinkB=0),
                         bbox=dict(boxstyle="round,pad=0.15", fc="white", ec=colour, lw=0.4, alpha=0.85),
                         zorder=20)
        self.ax.plot([x], [y], "o", ms=2.2, color=colour, zorder=21)
        self.placed.append({"label": text, "kind": kind, "anchor_mm": [round(x, 4), round(y, 4)],
                            "text_mm": [round(tx, 3), round(ty, 3)]})


def base_axes(view, title: str):
    x0, y0, x1, y1 = view
    w = 12.0
    h = max(4.0, min(14.0, w * (y1 - y0) / (x1 - x0) + 0.9))
    fig = plt.figure(figsize=(w, h), dpi=DPI)
    ax = fig.add_axes([0.05, 0.06, 0.78, 0.86])
    ax.set_xlim(x0, x1)
    ax.set_ylim(y1, y0)        # KiCad Y down
    ax.set_aspect("equal", adjustable="box")
    ax.set_title(title, fontsize=9, loc="left")
    ax.tick_params(labelsize=7)
    ax.set_xlabel("x (mm)", fontsize=7)
    ax.set_ylabel("y (mm, down)", fontsize=7)
    ax.grid(True, lw=0.3, color="#eeeeee", zorder=0)
    return fig, ax


def draw_context(ax, m: BoardModel, geo: Geo, view_box, skip_net: Optional[str] = None, faint_copper=True):
    add_poly(ax, m.outline, fc="none", ec="#000000", lw=1.0, zorder=1)
    for ref, fp in m.footprints.items():
        b = m.body(ref)
        if b.is_empty or not b.intersects(view_box):
            continue
        add_poly(ax, b, fc="none", ec="#bdbdbd", lw=0.5, ls="-", zorder=2)
        c = b.centroid
        if view_box.contains(c):
            ax.text(c.x, c.y, ref, fontsize=5, color="#9e9e9e", ha="center", va="center", zorder=2)
    for pid, p in m.pads.items():
        if p["net"] == skip_net:
            continue
        g = m.pad_geom(pid)
        if g.intersects(view_box):
            add_poly(ax, g, fc="#eeeeee", ec="#bdbdbd", lw=0.3, zorder=3)
    if faint_copper:
        for sid, s in m.segments.items():
            if s["net"] == skip_net:
                continue
            ln = m.segment_line(sid)
            if ln.intersects(view_box):
                add_line(ax, ln, color="#e0e0e0", lw=0.8, solid_capstyle="round", zorder=3)


# ---------------------------------------------------------------------------
# Net image
# ---------------------------------------------------------------------------

def render_net(m: BoardModel, geo: Geo, net: str, radii: Dict[str, float], prov: Dict[str, Any],
               out: Path) -> Dict[str, Any]:
    n = m.nets[net]
    cu = geo.cu
    tgt = unary_union([geo.copper(net, l) for l in cu])
    nb = neighbours(geo, net, radii)
    margin = max(4.0, max([e["radius_mm"] for e in nb] or [1.0]) + 1.5)
    x0, y0, x1, y1 = tgt.bounds
    ox0, oy0, ox1, oy1 = m.outline.bounds
    view = (max(x0 - margin, ox0 - 1), max(y0 - margin, oy0 - 1), min(x1 + margin, ox1 + 1), min(y1 + margin, oy1 + 1))
    vb = box(*view)
    src = prov.get("source_ref") or prov["source_sha256"][:8]
    fig, ax = base_axes(view, "%s  —  %s @ %s (sha %s), board model" % (
        net, Path(prov["source"]).name, src, prov["source_sha256"][:8]))
    draw_context(ax, m, geo, vb, skip_net=net)
    # Neighbours (their copper near the target).
    near_zone = tgt.buffer(max(e["radius_mm"] for e in nb) + 0.5) if nb else None
    nb_label_pts = []
    for e in nb:
        col = CLASS_COLOURS["high_dvdt"] if "high_dvdt" in e["classes"] else (
            CLASS_COLOURS["high_current"] if "high_current" in e["classes"] else CLASS_COLOURS["signal"])
        zone_r = tgt.buffer(e["radius_mm"] + 0.3)
        best = None
        for l in cu:
            g = geo.copper(e["net"], l).intersection(zone_r)
            if g.is_empty:
                continue
            add_poly(ax, g, fc=col, ec="none", alpha=0.35, zorder=5)
            d = g.distance(tgt)
            if best is None or d < best[0]:
                best = (d, g)
        if best is not None:
            # Anchor on the neighbour copper point closest to the target.
            from shapely.ops import nearest_points
            p = nearest_points(best[1], tgt)[0]
            nb_label_pts.append((p.x, p.y, short(e["net"]), col))
    # Target copper by layer (bottom layers first).
    for l in reversed(cu):
        for sid in n["segments"]:
            s = m.segments[sid]
            if s["layer"] == l:
                add_poly(ax, m.segment_geom(sid), fc=LAYER_COLOURS.get(l, "#555"), ec="none", alpha=0.85, zorder=8)
    for pid in n["pads"]:
        add_poly(ax, m.pad_geom(pid), fc="#424242", ec="#000", lw=0.4, alpha=0.9, zorder=9)
    for vid in n["vias"]:
        v = m.vias[vid]
        add_poly(ax, m.via_geom(vid), fc="#ffffff", ec="#000", lw=0.8, zorder=10)
        add_poly(ax, Point(v["position"]).buffer(v["drill"] / 2.0, 12), fc="#000", ec="none", zorder=10)
    # Unreferenced stretches (antipads excluded).
    unref_total = 0.0
    for sid in n["segments"]:
        s = m.segments[sid]
        for r in reference_for_line(geo, m.segment_line(sid), s["layer"]):
            for p in r["voids"]:
                unref_total += p.length
                add_line(ax, p, color="#000000", lw=1.6, ls=(0, (2, 1.5)), zorder=11)
    # Labels: pads and vias of the target, then neighbours.
    lab = Labeller(ax, fig, view)
    avoid = [tgt]
    for pid in sorted(n["pads"]):
        p = m.pads[pid]
        lab.add(p["center"][0], p["center"][1], pid, colour="#000000", avoid=avoid, kind="pad")
    for vid in n["vias"]:
        v = m.vias[vid]
        lab.add(v["position"][0], v["position"][1], vid, colour="#37474f", avoid=avoid, kind="via")
    unlabelled = [t for (_, _, t, _) in nb_label_pts if t.startswith("unconnected-")]
    for (x, y, text, col) in nb_label_pts:
        if not text.startswith("unconnected-"):
            lab.add(x, y, text, colour=col, avoid=avoid, kind="neighbour")
    handles = [Patch(fc=LAYER_COLOURS[l], label="%s (target)" % l) for l in cu if
               any(m.segments[s]["layer"] == l for s in n["segments"])]
    handles += [Patch(fc=c, alpha=0.35, label="neighbour: %s" % k) for k, c in CLASS_COLOURS.items()]
    handles += [Line2D([0], [0], color="#000", lw=1.6, ls=(0, (2, 1.5)),
                       label="no ref. plane (%.1f mm)" % unref_total),
                Patch(fc="#eeeeee", ec="#bdbdbd", label="other pads / bodies")]
    ax.legend(handles=handles, fontsize=6, loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
    fig.text(0.05, 0.012, "Neighbour radii (mm): %s. Labels point at pad/via centres (dot). No-ref dashes: antipads "
            "excluded. Highlighted but not labelled: %d no-connect pad net(s)." % (
                ", ".join("%s %g" % kv for kv in radii.items()), len(unlabelled)),
            fontsize=6, color="#616161")
    name = "net-%s.png" % safe_name(net)
    return finish(fig, ax, out / name, view, prov, lab, {"kind": "net", "net": net,
                                                        "neighbours": [e["net"] for e in nb],
                                                        "unreferenced_antipads_excl_mm": round(unref_total, 3)})


# ---------------------------------------------------------------------------
# Plane image
# ---------------------------------------------------------------------------

def render_plane(m: BoardModel, geo: Geo, layer: str, prov: Dict[str, Any], out: Path,
                 critical: List[str]) -> Dict[str, Any]:
    ol = m.outline
    x0, y0, x1, y1 = ol.bounds
    view = (x0 - 2, y0 - 2, x1 + 2, y1 + 2)
    vb = box(*view)
    src = prov.get("source_ref") or prov["source_sha256"][:8]
    fig, ax = base_axes(view, "%s planes  —  %s @ %s (sha %s), board model" % (
        layer, Path(prov["source"]).name, src, prov["source_sha256"][:8]))
    add_poly(ax, ol, fc="none", ec="#000", lw=1.0, zorder=1)
    for ref in m.footprints:
        b = m.body(ref)
        if not b.is_empty:
            add_poly(ax, b, fc="none", ec="#e0e0e0", lw=0.4, zorder=2)
    nets = geo.fill_nets(layer)
    colour = {}
    handles = []
    for i, net in enumerate(nets):
        c = "#9e9e9e" if net == "GND" else NET_PALETTE[1 + (i % (len(NET_PALETTE) - 1))]
        colour[net] = c
        f = geo.fill(layer, net)
        add_poly(ax, f, fc=c, ec="#616161", lw=0.3, alpha=0.75, zorder=3)
        handles.append(Patch(fc=c, alpha=0.75, label="%s fill (%.0f mm²)" % (net, f.area)))
    # Other copper on this layer (tracks, pads, vias of every net), thin.
    for sid, s in m.segments.items():
        if s["layer"] == layer:
            add_poly(ax, m.segment_geom(sid), fc="#424242", ec="none", alpha=0.6, zorder=4)
    # Voids / split gaps (as in plane_report: outline less 1 mm, less all copper, >= 1 mm²).
    cu_all = unary_union([geo.copper(n, layer, zones=True) for n in set(geo.nets_on(layer)) | set(nets)])
    empty = ol.buffer(-1.0, 8).difference(cu_all)
    holes = unary_union([h for (_, h, _) in geo.antipad_holes(layer)]) if nets else None
    voids = []
    share = unary_union([geo.fill(layer, n) for n in nets]).area / ol.area if nets and ol.area else 0.0
    is_plane = share >= 0.25   # as plane_report.py: voids only mean something on a plane layer
    for p in ((list(empty.geoms) if hasattr(empty, "geoms") else [empty]) if is_plane else []):
        if p.is_empty or p.area < 1.0:
            continue
        if holes is not None and not holes.is_empty and p.difference(holes).area < 0.05 * p.area:
            continue
        voids.append(p)
        add_poly(ax, p, fc="none", ec="#d50000", lw=0.6, hatch="////", zorder=5)
    if voids:
        handles.append(Patch(fc="none", ec="#d50000", hatch="////", label="no copper (void / split gap)"))
    for z in m.zones.values():
        if z["keepout"] is not None and layer in z["layers"]:
            add_poly(ax, poly_from_json(z["outline"]), fc="none", ec="#6a1b9a", lw=0.9, ls="--", zorder=6)
            handles.append(Line2D([0], [0], color="#6a1b9a", ls="--", label="keepout %s" % z["id"]))
    # Critical nets' tracks on the adjacent layer(s).
    adj = [a for a, _ in geo.adjacent(layer)]
    shown = []
    lab = Labeller(ax, fig, view, fontsize=6)
    for net in critical:
        for sid in m.nets.get(net, {}).get("segments", []):
            s = m.segments[sid]
            if s["layer"] in adj:
                add_line(ax, m.segment_line(sid), color=LAYER_COLOURS.get(s["layer"], "#000"), lw=1.1, zorder=7)
                if net not in shown:
                    shown.append(net)
    for net in shown:
        segs = [m.segments[s] for s in m.nets[net]["segments"] if m.segments[s]["layer"] in adj]
        longest = max(segs, key=lambda s: s["length_mm"])
        mid = m.segment_line(longest["id"]).interpolate(0.5, normalized=True)
        lab.add(mid.x, mid.y, short(net), colour=LAYER_COLOURS.get(longest["layer"], "#000"), kind="track")
    for l in adj:
        if any(m.segments[s]["layer"] == l for n in shown for s in m.nets[n]["segments"]):
            handles.append(Line2D([0], [0], color=LAYER_COLOURS.get(l, "#000"), lw=1.1,
                                  label="critical nets on %s (adjacent)" % l))
    gv = [v for v in m.vias.values() if v["net"] == "GND"]
    if gv:
        ax.plot([v["position"][0] for v in gv], [v["position"][1] for v in gv], ".", ms=2.5, color="#000",
                zorder=8)
        handles.append(Line2D([0], [0], marker=".", ls="none", color="#000", label="GND via (%d)" % len(gv)))
    for net in nets:
        f = geo.fill(layer, net)
        parts = sorted(list(f.geoms) if hasattr(f, "geoms") else [f], key=lambda p: -p.area)
        if parts and not parts[0].is_empty:
            c = parts[0].representative_point()
            lab.add(c.x, c.y, "%s" % net, colour="#212121", kind="zone")
    for p in sorted(voids, key=lambda p: -p.area)[:6]:
        c = p.representative_point()
        lab.add(c.x, c.y, "no Cu %.0f mm²" % p.area, colour="#d50000", kind="void")
    ax.legend(handles=handles, fontsize=6, loc="upper left", bbox_to_anchor=(1.0, 1.0), frameon=False)
    return finish(fig, ax, out / ("plane-%s.png" % layer.replace(".", "_")), view, prov, lab,
                  {"kind": "plane", "layer": layer, "fill_nets": nets, "adjacent_layers": adj,
                   "critical_nets_overlaid": shown, "is_plane_layer": is_plane,
                   "fill_share_of_outline": round(share, 4)})


# ---------------------------------------------------------------------------

def finish(fig, ax, path: Path, view, prov, lab: Labeller, extra: Dict[str, Any]) -> Dict[str, Any]:
    fig.savefig(str(path), dpi=DPI)
    fig.canvas.draw()
    W, H = fig.canvas.get_width_height()
    bb = ax.get_window_extent()
    x0, y0, x1, y1 = view

    def to_px(x, y):
        # Axes box in display coords (origin bottom-left) → image px (origin top-left); y axis inverted.
        px = bb.x0 + (x - x0) / (x1 - x0) * bb.width
        py_disp = bb.y1 - (y - y0) / (y1 - y0) * bb.height
        return [round(px, 1), round(H - py_disp, 1)]

    for p in lab.placed:
        p["anchor_px"] = to_px(*p["anchor_mm"])
    meta = {"_provenance": prov, **extra,
            "image": {"file": path.name, "width_px": W, "height_px": H, "dpi": DPI},
            "view_mm": [round(v, 3) for v in view], "y_axis": "down (KiCad)",
            "axes_px": {"left": round(bb.x0, 1), "top": round(H - bb.y1, 1), "right": round(bb.x1, 1),
                        "bottom": round(H - bb.y0, 1)},
            "labels": lab.placed}
    plt.close(fig)
    write_json(path.with_name(path.name + ".meta.json"), meta)
    return meta


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("model", help="board-model.json from board_model.py")
    ap.add_argument("-o", "--outdir", help="output folder (default: <model folder>/img)")
    ap.add_argument("--net", action="append", default=[], help="net to render (repeatable; default critical_nets)")
    ap.add_argument("--layer", action="append", default=[], help="plane layer to render (repeatable)")
    a = ap.parse_args()
    mp = Path(a.model)
    out = Path(a.outdir) if a.outdir else mp.parent / "img"
    out.mkdir(parents=True, exist_ok=True)
    m = BoardModel.load(mp)
    geo = Geo(m)
    prov = derived_provenance(m, mp, GENERATOR)
    radii = m.data.get("definitions", {}).get("neighbour_radii_mm") or {"signal": 1.0, "high_current": 3.0,
                                                                         "high_dvdt": 5.0}
    nets = a.net or m.data.get("critical_nets", [])
    layers = a.layer or [l for l in geo.cu if geo.fill_nets(l)]
    for net in nets:
        meta = render_net(m, geo, net, radii, prov, out)
        print("wrote %s (%d labels)" % (out / meta["image"]["file"], len(meta["labels"])))
    for l in layers:
        meta = render_plane(m, geo, l, prov, out, m.data.get("critical_nets", []))
        print("wrote %s (%d labels)" % (out / meta["image"]["file"], len(meta["labels"])))


if __name__ == "__main__":
    main()

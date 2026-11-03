#!/usr/bin/env python3
"""
plane_report.py: planes and regions report from a board model (board_model.py).

Spec: docs/research/v7-retry/kicad-extraction-audit.md §5.4 (2). Per copper
layer:
  - copper ownership: area per net (zone fills, and all copper), share of
    the board outline; a layer whose fills cover >= 25 % of the outline is
    a plane layer
  - zones on the layer (net, priority, fill area, holes)
  - splits: every pair of different-net fills on the layer that come within
    split_gap_max_mm: shared boundary length, min gap, bbox, and every track
    on an adjacent layer that crosses the gap
  - voids (plane layers): areas inside the outline (less edge_margin_mm)
    with no copper at all, >= min_void_mm2; antipad holes counted apart
Then:
  - mm unreferenced per signal segment (track centreline over the adjacent
    plane layer's fills; raw and antipads excluded), per net and per segment
  - GND stitching: GND vias per grid cell, density, empty cells, and the
    nearest GND via to every signal via (centre to centre)

Usage:
    python plane_report.py <board-model.json> [-o OUTDIR]
Writes OUTDIR/plane-report.md and OUTDIR/plane-report.json (default OUTDIR:
the model's folder), with provenance (tools/CONTEXT.md Source-Hash Rule).
Optional board-config key `plane_report` overrides the defaults below.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from shapely.geometry import Point, box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

from board_model import BoardModel, poly_from_json  # noqa: E402
from report_lib import (Geo, _pieces, derived_provenance, md_front_matter,  # noqa: E402
                        r1, reference_for_line, write_json)

GENERATOR = "tools/pcb-context/plane_report.py"

DEFAULTS = {
    "plane_fill_share": 0.25,     # a layer is a plane layer if its fills cover this share of the outline
    "split_gap_max_mm": 1.5,      # different-net fills closer than this form a split
    "edge_margin_mm": 1.0,        # voids are looked for inside the outline less this margin
    "min_void_mm2": 1.0,
    "antipad_cluster_mm2": 3.0,   # antipad holes this big are listed (merged antipads)
    "grid_mm": 10.0,
    "ground_net": "GND",
}

METHODS = {
    "ownership": "area of the union of a net's copper on the layer (zone fills; and all copper = fills + tracks + "
                 "pads + via annular rings)",
    "split": "boundary of fill A lying within split_gap_max_mm of fill B (length), the min edge-to-edge gap, and "
             "tracks on an adjacent copper layer whose centreline crosses the gap between them",
    "void_width": "mean width = 2 × area / perimeter (a long thin void along a split reads as its width)",
    "void": "outline shrunk by edge_margin_mm, less all copper on the layer; pieces >= min_void_mm2. A piece touching fills of two or more nets is a split gap, otherwise a void. Holes in a "
            "fill that contain a drilled hole are antipads and are counted separately",
    "unreferenced_raw": "track centreline over no fill on the adjacent copper layer (stackup); fill holes count as no copper",
    "unreferenced_antipads_excl": "as raw, but fill holes that contain a drilled hole (via, PTH, NPTH) count as copper",
    "stitching": "GND vias (centres) per grid cell; cells at least half inside the outline; nearest GND via to a "
                 "signal via is centre to centre",
}


def _area_net(geo: Geo, net: str, layer: str) -> float:
    return geo.copper(net, layer, zones=True).area


def layer_section(geo: Geo, m: BoardModel, layer: str, outline, P: Dict[str, Any]) -> Dict[str, Any]:
    oa = outline.area
    fill_nets = geo.fill_nets(layer)
    fills = {n: geo.fill(layer, n) for n in fill_nets}
    total_fill = unary_union(list(fills.values())) if fills else None
    fill_share = (total_fill.area / oa) if total_fill is not None and oa else 0.0
    is_plane = fill_share >= P["plane_fill_share"]
    owners = []
    for n in sorted(set(geo.nets_on(layer)) | set(fill_nets)):
        a_all = _area_net(geo, n, layer)
        a_fill = fills[n].area if n in fills else 0.0
        if a_all < 1e-3:
            continue
        owners.append({"net": n, "fill_mm2": r1(a_fill), "all_copper_mm2": r1(a_all),
                       "share_of_outline": round(a_all / oa, 4) if oa else None})
    owners.sort(key=lambda o: -o["all_copper_mm2"])
    zones = []
    for z in m.zones.values():
        if layer not in z["layers"]:
            continue
        g = m.zone_fill(z["id"], layer)
        zones.append({"id": z["id"], "net": z["net"] or None, "priority": z["priority"],
                      "keepout": z["keepout"], "fill_mm2": z["fill_area_mm2"].get(layer, 0.0),
                      "holes": z["fill_holes"].get(layer, 0),
                      "bbox": [r1(v) for v in g.bounds] if not g.is_empty else None})
    # Splits.
    splits = []
    adj_layers = [a for a, _ in geo.adjacent(layer)]
    for i, a in enumerate(fill_nets):
        for b in fill_nets[i + 1:]:
            A, B = fills[a], fills[b]
            gap = A.distance(B)
            if gap > P["split_gap_max_mm"]:
                continue
            g = P["split_gap_max_mm"]
            boundary = A.boundary.intersection(B.buffer(g, 8))
            channel = A.buffer(g, 8).intersection(B.buffer(g, 8)).difference(A).difference(B)
            crossings = []
            for al in adj_layers:
                for sid, s in m.segments.items():
                    if s["layer"] != al:
                        continue
                    ln = m.segment_line(sid)
                    if not ln.intersects(channel):
                        continue
                    pts = ln.intersection(channel)
                    c = pts.centroid
                    crossings.append({"net": s["net"], "segment": sid, "layer": al,
                                      "classes": m.nets.get(s["net"], {}).get("classes"),
                                      "at": [r1(c.x), r1(c.y)], "mm_in_gap": r1(pts.length)})
            crossings.sort(key=lambda c: (c["net"], c["segment"]))
            splits.append({"nets": [a, b], "min_gap_mm": r1(gap), "boundary_mm": r1(boundary.length),
                           "bbox": [r1(v) for v in channel.bounds] if not channel.is_empty else None,
                           "adjacent_track_crossings": crossings})
    # Voids and antipads.
    voids, antipads = [], {}
    if is_plane:
        inner = outline.buffer(-P["edge_margin_mm"], 8)
        cu_all = unary_union([geo.copper(n, layer, zones=True) for n in set(geo.nets_on(layer)) | set(fill_nets)])
        holes = geo.antipad_holes(layer)
        ap_union = unary_union([h for (_, h, _) in holes]) if holes else None
        empty = inner.difference(cu_all)
        ko = [poly for poly in (poly_from_json(z["outline"]) for z in m.zones.values()
                                if z["keepout"] is not None and layer in z["layers"]) if not poly.is_empty]
        for p in (list(empty.geoms) if hasattr(empty, "geoms") else [empty]):
            if p.is_empty or p.area < P["min_void_mm2"]:
                continue
            if ap_union is not None and p.difference(ap_union).area < 0.05 * p.area:
                continue   # an antipad (or merged antipads), listed below
            c = p.representative_point()
            near = sorted({s["net"] for sid, s in m.segments.items() if s["layer"] in adj_layers
                           and m.segment_line(sid).intersects(p)})
            touches = [n for n in fill_nets if fills[n].distance(p) < 0.05]
            voids.append({"kind": "split gap" if len(touches) >= 2 else "void", "fills_touched": touches,
                          "area_mm2": r1(p.area), "mean_width_mm": r1(2 * p.area / p.length), "bbox": [r1(v) for v in p.bounds], "at": [r1(c.x), r1(c.y)],
                          "in_keepout": any(k.intersects(p) and k.intersection(p).area > 0.5 * p.area for k in ko),
                          "nets_crossing_on_adjacent_layers": near})
        voids.sort(key=lambda v: -v["area_mm2"])
        big = [h for h in holes if h[1].area >= P["antipad_cluster_mm2"]]
        antipads = {"count": len(holes), "area_mm2": r1(sum(h[1].area for h in holes)),
                    "clusters": [{"net": n, "area_mm2": r1(h.area), "drills": k,
                                  "bbox": [r1(v) for v in h.bounds]} for (n, h, k) in
                                 sorted(big, key=lambda t: -t[1].area)]}
    return {"layer": layer, "is_plane": is_plane, "fill_share_of_outline": round(fill_share, 4),
            "adjacent_layers": geo.adjacent(layer), "owners": owners, "zones": zones,
            "splits": splits, "voids": voids, "antipads": antipads}


def unreferenced(geo: Geo, m: BoardModel) -> Dict[str, Any]:
    per_net = {}
    per_seg = []
    for net, n in sorted(m.nets.items()):
        if "signal" not in n["classes"] and "high_dvdt" not in n["classes"]:
            continue
        if "high_current" in n["classes"]:
            continue
        agg = None
        for sid in n["segments"]:
            s = m.segments[sid]
            ln = m.segment_line(sid)
            for r in reference_for_line(geo, ln, s["layer"]):
                if not geo.fill_nets(r["plane_layer"]):
                    continue
                agg = agg or {"track_mm": 0.0, "none_raw": 0.0, "none_excl": 0.0, "over": defaultdict(float)}
                agg["track_mm"] += ln.length
                agg["none_raw"] += r["none_raw"]
                agg["none_excl"] += r["none_antipads_excl"]
                for k, v in r["over"].items():
                    agg["over"][k] += v
                if r["none_raw"] > 1e-3:
                    per_seg.append({"net": net, "segment": sid, "layer": s["layer"], "plane_layer": r["plane_layer"],
                                    "length_mm": r1(ln.length), "none_raw_mm": r1(r["none_raw"]),
                                    "none_antipads_excl_mm": r1(r["none_antipads_excl"]),
                                    "over": {k: r1(v) for k, v in r["over"].items()}})
        if agg:
            per_net[net] = {"classes": n["classes"], "track_mm": r1(agg["track_mm"]),
                            "over_raw": {k: r1(v) for k, v in sorted(agg["over"].items(), key=lambda kv: -kv[1])},
                            "none_raw_mm": r1(agg["none_raw"]), "none_antipads_excl_mm": r1(agg["none_excl"])}
    per_seg.sort(key=lambda s: -s["none_antipads_excl_mm"])
    return {"per_net": per_net, "per_segment": per_seg}


def stitching(geo: Geo, m: BoardModel, outline, P: Dict[str, Any]) -> Dict[str, Any]:
    gnd = P["ground_net"]
    gv = [v for v in m.vias.values() if v["net"] == gnd]
    pts = [Point(v["position"]) for v in gv]
    x0, y0, x1, y1 = outline.bounds
    G = P["grid_mm"]
    cells = []
    nx, ny = int(math.ceil((x1 - x0) / G)), int(math.ceil((y1 - y0) / G))
    for j in range(ny):
        for i in range(nx):
            c = box(x0 + i * G, y0 + j * G, min(x1, x0 + (i + 1) * G), min(y1, y0 + (j + 1) * G))
            inside = c.intersection(outline).area
            if inside < 0.5 * c.area:
                continue
            k = sum(1 for p in pts if c.covers(p))
            cells.append({"cell": [i, j], "bbox": [r1(v) for v in c.bounds], "gnd_vias": k,
                          "per_cm2": r1(k / (inside / 100.0)) if inside else 0.0})
    counts = defaultdict(int)
    for c in cells:
        counts[min(c["gnd_vias"], 5)] += 1
    sig = []
    for v in m.vias.values():
        n = m.nets.get(v["net"], {})
        if "high_current" in n.get("classes", []) or v["net"] == gnd:
            continue
        P0 = Point(v["position"])
        ds = sorted((P0.distance(p), g["id"]) for p, g in zip(pts, gv))
        sig.append({"via": v["id"], "net": v["net"], "position": v["position"],
                    "nearest_gnd_via": ds[0][1] if ds else None,
                    "centre_to_centre_mm": r1(ds[0][0]) if ds else None})
    sig.sort(key=lambda s: -(s["centre_to_centre_mm"] or 0))
    return {"ground_net": gnd, "gnd_vias": len(gv), "outline_mm2": r1(outline.area),
            "per_cm2_board": r1(len(gv) / (outline.area / 100.0)) if outline.area else None,
            "grid_mm": G, "cells": cells,
            "histogram_vias_per_cell": {("5+" if k == 5 else str(k)): v for k, v in sorted(counts.items())},
            "empty_cells": [c["bbox"] for c in cells if c["gnd_vias"] == 0],
            "signal_vias_nearest_gnd": sig}


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def _lay(l: str) -> str:
    return l.replace(".Cu", "")


def md_report(rep: Dict[str, Any]) -> str:
    L = [md_front_matter(rep["_provenance"])]
    L.append("# Plane report — %s" % rep["board"])
    L.append("")
    L.append("Generated from the board model by `%s`. Check freshness before citing: "
             "`python3 tools/lab/check_state.py --fresh <this file>`. Coordinates are KiCad board mm, Y down."
             % GENERATOR)
    L.append("")
    L.append("**Measuring methods:**")
    L.append("")
    for k, v in rep["methods"].items():
        L.append("- *%s*: %s" % (k.replace("_", " "), v))
    L.append("")
    L.append("Parameters: %s. Outline %.1f mm².  Stackup: %s." % (
        ", ".join("%s %s" % kv for kv in rep["parameters"].items()), rep["outline_mm2"],
        "; ".join("%s↔%s %.3g mm" % (_lay(a), _lay(b), d) for a, b, d in rep["stackup_pairs"])))
    L.append("")
    for s in rep["layers"]:
        L.append("## %s%s" % (s["layer"], " (plane layer)" if s["is_plane"] else ""))
        L.append("")
        L.append("Fills cover %.1f %% of the outline. Adjacent: %s." % (
            100 * s["fill_share_of_outline"], ", ".join("%s (%.3g mm)" % (a, d) for a, d in s["adjacent_layers"])))
        L.append("")
        if s["zones"]:
            L.append("| Zone | Net | Priority | Fill mm² | Holes | Bbox |")
            L.append("|---|---|---|---|---|---|")
            for z in s["zones"]:
                L.append("| %s | %s | %s | %.1f | %d | %s |" % (
                    z["id"], z["net"] or ("keepout" if z["keepout"] else "—"), z["priority"], z["fill_mm2"],
                    z["holes"], z["bbox"] or "—"))
            L.append("")
        top = s["owners"][:8]
        L.append("Copper ownership (top %d of %d nets): " % (len(top), len(s["owners"])) + "; ".join(
            "%s %.1f mm² (fill %.1f, %.1f %%)" % (o["net"], o["all_copper_mm2"], o["fill_mm2"],
                                                 100 * (o["share_of_outline"] or 0)) for o in top))
        L.append("")
        for sp in s["splits"]:
            L.append("**Split %s | %s**: min gap %.2f mm, shared boundary %.1f mm, bbox %s." % (
                sp["nets"][0], sp["nets"][1], sp["min_gap_mm"], sp["boundary_mm"], sp["bbox"]))
            cr = sp["adjacent_track_crossings"]
            if cr:
                byn = defaultdict(list)
                for c in cr:
                    byn[(c["net"], c["layer"])].append(c)
                L.append("Tracks on adjacent layers crossing the gap: " + "; ".join(
                    "%s (%s) %s" % (n, _lay(l), ", ".join("%s %.2f mm in the gap at (%.1f, %.1f)" % (c["segment"], c["mm_in_gap"], *c["at"]) for c in cs))
                    for (n, l), cs in sorted(byn.items())))
            L.append("")
        if s["is_plane"]:
            ap = s["antipads"]
            L.append("Antipads: %d holes with a drill, %.1f mm² in all. Merged clusters ≥ %.0f mm²: %s." % (
                ap["count"], ap["area_mm2"], rep["parameters"]["antipad_cluster_mm2"],
                "; ".join("%s %.1f mm² (%d drills) %s" % (c["net"], c["area_mm2"], c["drills"], c["bbox"])
                          for c in ap["clusters"]) or "none"))
            L.append("")
            if s["voids"]:
                L.append("| Kind | mm² | Mean width mm | At | Bbox | Fills touched | In keepout | Nets crossing on adjacent layers |")
                L.append("|---|---|---|---|---|---|---|---|")
                for v in s["voids"]:
                    L.append("| %s | %.1f | %.2f | (%.1f, %.1f) | %s | %s | %s | %s |" % (
                        v["kind"], v["area_mm2"], v["mean_width_mm"], v["at"][0], v["at"][1], v["bbox"],
                        ", ".join(v["fills_touched"]) or "—", "yes" if v["in_keepout"] else "",
                        ", ".join(v["nets_crossing_on_adjacent_layers"]) or "—"))
            else:
                L.append("No voids ≥ %g mm²." % rep["parameters"]["min_void_mm2"])
            L.append("")
    u = rep["unreferenced"]
    L.append("## Unreferenced signal track (adjacent plane)")
    L.append("")
    L.append("Signal and high dv/dt nets that are not high-current. Nets with no unreferenced length are omitted.")
    L.append("")
    L.append("| Net | Track mm (over a plane layer) | Over (raw) | None, raw | None, antipads excl. |")
    L.append("|---|---|---|---|---|")
    for n, e in sorted(u["per_net"].items(), key=lambda kv: -kv[1]["none_antipads_excl_mm"]):
        if e["none_raw_mm"] <= 0.005:
            continue
        L.append("| %s | %.2f | %s | %.2f | **%.2f** |" % (n, e["track_mm"], ", ".join(
            "%s %.2f" % kv for kv in e["over_raw"].items()) or "—", e["none_raw_mm"], e["none_antipads_excl_mm"]))
    clean = [n for n, e in u["per_net"].items() if e["none_raw_mm"] <= 0.005]
    L.append("")
    L.append("Fully referenced (raw): %s." % (", ".join(sorted(clean)) or "none"))
    L.append("")
    L.append("Segments with any unreferenced length, antipads excluded (top 25; all in the JSON):")
    L.append("")
    L.append("| Net | Segment | Layer → plane | Seg mm | None, raw | None, antipads excl. |")
    L.append("|---|---|---|---|---|---|")
    for s in [s for s in u["per_segment"] if s["none_antipads_excl_mm"] > 0][:25]:
        L.append("| %s | %s | %s → %s | %.2f | %.2f | %.2f |" % (s["net"], s["segment"], _lay(s["layer"]),
                                                              _lay(s["plane_layer"]), s["length_mm"],
                                                              s["none_raw_mm"], s["none_antipads_excl_mm"]))
    L.append("")
    st = rep["stitching"]
    L.append("## %s stitching" % st["ground_net"])
    L.append("")
    L.append("%d %s vias over %.0f mm² of board: %.2f per cm². Grid %g mm, %d cells: vias per cell %s." % (
        st["gnd_vias"], st["ground_net"], st["outline_mm2"], st["per_cm2_board"], st["grid_mm"], len(st["cells"]),
        ", ".join("%s → %d cells" % kv for kv in st["histogram_vias_per_cell"].items())))
    L.append("")
    L.append("Cells with no %s via: %s." % (st["ground_net"], "; ".join(str(b) for b in st["empty_cells"]) or "none"))
    L.append("")
    L.append("Signal vias farthest from a %s via (top 15, centre to centre): " % st["ground_net"] + "; ".join(
        "%s %s %.2f mm (%s)" % (s["via"], s["net"], s["centre_to_centre_mm"], s["nearest_gnd_via"])
        for s in st["signal_vias_nearest_gnd"][:15]))
    L.append("")
    return "\n".join(L)


def build(model_path: Path) -> Dict[str, Any]:
    m = BoardModel.load(model_path)
    geo = Geo(m)
    P = dict(DEFAULTS)
    P.update(m.data.get("definitions", {}).get("plane_report", {}) or {})
    outline = m.outline
    cu = geo.cu
    pairs = [(a, b, geo.separation(a, b)) for a, b in zip(cu, cu[1:])]
    return {
        "_provenance": derived_provenance(m, model_path, GENERATOR),
        "board": "%s @ %s" % (m.data["_provenance"]["source"], m.data["_provenance"].get("source_ref") or "working tree"),
        "methods": METHODS, "parameters": P, "outline_mm2": r1(outline.area),
        "stackup_pairs": pairs,
        "layers": [layer_section(geo, m, l, outline, P) for l in cu],
        "unreferenced": unreferenced(geo, m),
        "stitching": stitching(geo, m, outline, P),
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("model", help="board-model.json from board_model.py")
    ap.add_argument("-o", "--outdir", help="output folder (default: the model's folder)")
    a = ap.parse_args()
    mp = Path(a.model)
    out = Path(a.outdir) if a.outdir else mp.parent
    out.mkdir(parents=True, exist_ok=True)
    rep = build(mp)
    write_json(out / "plane-report.json", rep)
    (out / "plane-report.md").write_text(md_report(rep), encoding="utf-8")
    print("wrote %s and %s" % (out / "plane-report.md", out / "plane-report.json"))


if __name__ == "__main__":
    main()

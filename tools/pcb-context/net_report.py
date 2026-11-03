#!/usr/bin/env python3
"""
net_report.py: net-centric report from a board model (board_model.py).

Spec: docs/research/v7-retry/kicad-extraction-audit.md §5.4 (1) and the
net-centric sketch. For each critical net (board config `critical_nets`,
or --net) a full block:
  - route narrative from the topology (tree from the driver; per chain the
    layer, length, width and its straight legs)
  - endpoints with branch length, vias and per-layer length from the driver
  - reference plane per segment (nearest copper layer above/below from the
    stackup; raw and antipads-excluded), and every unreferenced stretch
  - bodies the net passes under or over (plan view)
  - neighbours within the radii, across layers, unprompted: same-layer
    gap (track to track and all copper), plan-view gap with layer
    separation, coupled length, crossings, the closest item pair
  - per via: the layer change, the planes on each side, and the nearest
    via of each plane net (return-current path)
Every other net gets one summary row.

Usage:
    python net_report.py <board-model.json> [-o OUTDIR] [--net NET ...]
Writes OUTDIR/net-report.md and OUTDIR/net-report.json (default OUTDIR:
the model's folder). Both carry provenance (tools/CONTEXT.md Source-Hash Rule).
"""

from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

from shapely.geometry import Point  # noqa: E402

from board_model import BoardModel  # noqa: E402
from report_lib import (NONE, Geo, body_overlaps, derived_provenance,  # noqa: E402
                        md_front_matter, neighbours, r1, reference_for_line,
                        route_tree, write_json)

GENERATOR = "tools/pcb-context/net_report.py"

METHODS = {
    "track_to_track": "target track copper (centreline buffered by width/2) to neighbour track copper, same layer",
    "track_to_copper": "target track copper to all of the neighbour's same-layer copper (tracks, pads, vias, fills)",
    "all_copper": "tracks + pads + via annular rings (+ the neighbour's same-layer zone fills), same layer, edge to edge",
    "plan_view": "target copper on one layer to neighbour copper on another layer, edge to edge in plan view; "
                 "zone fills on other layers are reference planes, not neighbours; separation = dielectric between",
    "coupled": "mm of the target's track centrelines within the radius (edge to edge) of the neighbour's same-layer copper",
    "radius": "max of the target's and the neighbour's class radius (board config neighbour_radii_mm)",
    "reference_raw": "track centreline over the zone fills of the adjacent copper layer; fill holes count as no copper",
    "reference_antipads_excl": "as raw, but fill holes that contain a drilled hole (via, PTH, NPTH) count as copper",
    "bodies": "track centreline inside a footprint body polygon (courtyard, else fab, else pads), plan view",
}


# ---------------------------------------------------------------------------

def reference_planes(geo: Geo, m: BoardModel, net: str) -> Dict[str, Any]:
    per_seg, agg = [], {}
    stretches = []
    for sid in m.nets[net]["segments"]:
        s = m.segments[sid]
        ln = m.segment_line(sid)
        for r in reference_for_line(geo, ln, s["layer"]):
            key = (s["layer"], r["plane_layer"])
            a = agg.setdefault(key, {"layer": s["layer"], "plane_layer": r["plane_layer"],
                                     "dielectric_mm": r["dielectric_mm"], "track_mm": 0.0,
                                     "over": defaultdict(float), "over_antipads_excl": defaultdict(float),
                                     "none_raw": 0.0, "none_antipads_excl": 0.0})
            a["track_mm"] += ln.length
            for k, v in r["over"].items():
                a["over"][k] += v
            for k, v in r["over_antipads_excl"].items():
                a["over_antipads_excl"][k] += v
            a["none_raw"] += r["none_raw"]
            a["none_antipads_excl"] += r["none_antipads_excl"]
            per_seg.append({"segment": sid, "layer": s["layer"], "plane_layer": r["plane_layer"],
                            "length_mm": r1(ln.length), "over": {k: r1(v) for k, v in r["over"].items()},
                            "none_raw_mm": r1(r["none_raw"]), "none_antipads_excl_mm": r1(r["none_antipads_excl"])})
            for p in r["voids"]:
                (x0, y0), (x1, y1) = p.coords[0], p.coords[-1]
                stretches.append({"segment": sid, "layer": s["layer"], "plane_layer": r["plane_layer"],
                                  "length_mm": r1(p.length), "from": [r1(x0), r1(y0)], "to": [r1(x1), r1(y1)]})
    runs = []
    for a in agg.values():
        runs.append({"layer": a["layer"], "plane_layer": a["plane_layer"], "dielectric_mm": a["dielectric_mm"],
                     "track_mm": r1(a["track_mm"]),
                     "over_raw": dict(sorted(((k, r1(v)) for k, v in a["over"].items()), key=lambda kv: -kv[1])),
                     "none_raw_mm": r1(a["none_raw"]),
                     "over_antipads_excl": dict(sorted(((k, r1(v)) for k, v in a["over_antipads_excl"].items()),
                                                       key=lambda kv: -kv[1])),
                     "none_antipads_excl_mm": r1(a["none_antipads_excl"])})
    runs.sort(key=lambda r: (r["layer"], r["plane_layer"]))
    stretches.sort(key=lambda s: -s["length_mm"])
    return {"runs": runs, "unreferenced_stretches_antipads_excl": stretches, "per_segment": per_seg}


def via_details(geo: Geo, m: BoardModel, net: str, topo: Dict[str, Any]) -> List[Dict[str, Any]]:
    chains = topo.get("chains", [])
    out = []
    for vid in m.nets[net]["vias"]:
        v = m.vias[vid]
        P = Point(v["position"])
        layers = sorted({c["layer"] for c in chains if vid in (c["a"], c["b"]) and isinstance(c["layer"], str)},
                        key=lambda l: geo.cu.index(l) if l in geo.cu else 99)
        planes = {}
        for l in layers:
            for adj, _ in geo.adjacent(l):
                owners = [n for n in geo.fill_nets(adj) if geo.fill(adj, n, closed=True).distance(P) < 1.0]
                planes.setdefault(l, []).append({"plane_layer": adj, "nets_within_1mm": owners})
        plane_nets = sorted({n for ps in planes.values() for p in ps for n in p["nets_within_1mm"]})
        nearest = {}
        for pn in plane_nets:
            ds = [(P.distance(Point(o["position"])), o["id"]) for o in m.vias.values() if o["net"] == pn]
            if ds:
                d, oid = min(ds)
                nearest[pn] = {"via": oid, "centre_to_centre_mm": r1(d)}
        out.append({"via": vid, "position": v["position"], "size_mm": v["size"], "drill_mm": v["drill"],
                    "connects_layers": layers, "reference_planes": planes,
                    "nearest_plane_net_via": nearest})
    return out


def full_block(geo: Geo, m: BoardModel, net: str, radii: Dict[str, float]) -> Dict[str, Any]:
    n = m.nets[net]
    topo = n.get("topology") or {}
    rt = route_tree(m, net)
    branches = {b["to"]: b for b in topo.get("branches", [])}
    endpoints = []
    for pid in n["pads"]:
        p = m.pads[pid]
        fp = m.footprints[p["ref"]]
        b = branches.get(pid, {})
        endpoints.append({"pad": pid, "ref": p["ref"], "pin": p["number"], "pin_function": p.get("pin_function"),
                          "part": fp["value"], "footprint": fp["footprint"], "side": fp["side"],
                          "role": "root" if pid == topo.get("root") else None,
                          "from_root_mm": b.get("length_mm"), "vias_from_root": b.get("vias"),
                          "from_root_by_layer": b.get("by_layer")})
    endpoints.sort(key=lambda e: (e["role"] != "root", e["from_root_mm"] or 0))
    nb = neighbours(geo, net, radii)
    hc = [e for e in nb if "high_current" in e["classes"]]
    dv = [e for e in nb if "high_dvdt" in e["classes"]]
    reach = [b for b in topo.get("branches", []) if b.get("reachable")]
    return {
        "net": net, "classes": n["classes"],
        "endpoints": endpoints,
        "length_mm": n["length_mm"], "length_by_layer": n["length_by_layer"],
        "widths_mm": n["widths"], "vias": n["via_count"],
        "root": topo.get("root"), "root_source": topo.get("root_source"),
        "longest_branch_from_root_mm": max((b["length_mm"] for b in reach), default=None),
        "route_text": rt["text"], "chains": rt["chains"],
        "connected": topo.get("connected"), "islands": topo.get("islands"), "stubs": topo.get("stubs"),
        "reference_planes": reference_planes(geo, m, net),
        "passes_under_or_over": body_overlaps(m, net),
        "neighbours": nb,
        "nearby_high_current": [e["net"] for e in hc],
        "nearby_high_dvdt": [e["net"] for e in dv],
        "high_dvdt_pads_nearby": high_dvdt_pads_near(geo, m, net, radii),
        "via_details": via_details(geo, m, net, topo),
    }


def high_dvdt_pads_near(geo: Geo, m: BoardModel, net: str, radii: Dict[str, float]) -> List[Dict[str, Any]]:
    pads = m.data.get("definitions", {}).get("high_dvdt", {}).get("pads", [])
    r = radii.get("high_dvdt", 5.0)
    out = []
    for p in pads:
        pid = "%s.%s" % (p["ref"], p["pad"])
        if pid not in m.pads or m.pads[pid]["net"] == net:
            continue
        g = m.pad_geom(pid)
        best = None
        for l in m.pads[pid]["layers"]:
            for lt in geo.cu:
                T = geo.copper(net, lt)
                if T.is_empty:
                    continue
                d = T.distance(g)
                if d <= r and (best is None or d < best[0]):
                    best = (d, lt, l)
        if best:
            out.append({"pad": pid, "net": m.pads[pid]["net"], "gap_mm": r1(best[0]), "target_layer": best[1],
                        "pad_layer": best[2], "method": "all copper" if best[1] == best[2] else "plan view"})
    return out


def summary_row(m: BoardModel, net: str) -> Dict[str, Any]:
    n = m.nets[net]
    t = n.get("topology") or {}
    return {"net": net, "classes": n["classes"], "pads": len(n["pads"]), "length_mm": n["length_mm"],
            "length_by_layer": n["length_by_layer"], "widths_mm": n["widths"], "vias": n["via_count"],
            "zones": n["zones"], "root": t.get("root"),
            "connected": t.get("connected"),
            "islands_with_pads": sum(1 for i in t.get("islands", []) if i.get("pads")),
            "stubs": len(t.get("stubs", []) or [])}


# ---------------------------------------------------------------------------
# Markdown
# ---------------------------------------------------------------------------

def _fmt_over(d: Dict[str, float]) -> str:
    return ", ".join("%s %.2f" % (k, v) for k, v in d.items()) or "—"


def _lay(l: str) -> str:
    return l.replace(".Cu", "")


def md_block(b: Dict[str, Any]) -> str:
    L = []
    L.append("## %s" % b["net"])
    L.append("")
    lbl = ", ".join("%s %.2f" % (_lay(k), v) for k, v in b["length_by_layer"].items())
    L.append("Class: %s. %d pads, %d vias, track %.2f mm (%s), widths %s mm. Root: %s (%s). "
             "Longest branch from root: %.1f mm. Connected: %s."
             % ("/".join(b["classes"]), len(b["endpoints"]), b["vias"], b["length_mm"], lbl,
                ", ".join("%g" % w for w in b["widths_mm"]), b["root"], b["root_source"],
                b["longest_branch_from_root_mm"] or 0.0, b["connected"]))
    L.append("")
    L.append("### Route")
    L.append("")
    L.append("```")
    L.append(b["route_text"])
    L.append("```")
    L.append("")
    L.append("| Pad | Part | Side | From root (mm) | Vias | By layer |")
    L.append("|---|---|---|---|---|---|")
    for e in b["endpoints"]:
        bl = ", ".join("%s %.1f" % (_lay(k), v) for k, v in (e["from_root_by_layer"] or {}).items())
        L.append("| %s%s | %s | %s | %s | %s | %s |" % (
            e["pad"], " " + e["pin_function"] if e["pin_function"] and e["pin_function"] != e["pin"] else "", e["part"], e["side"],
            "root" if e["role"] == "root" else ("%.1f" % e["from_root_mm"] if e["from_root_mm"] is not None else "—"),
            "" if e["role"] == "root" else e["vias_from_root"], bl))
    if b["stubs"]:
        L.append("")
        L.append("Stubs: " + "; ".join("%s %s" % (s["kind"], s.get("chain") or s.get("via")) for s in b["stubs"]))
    L.append("")
    L.append("### Reference planes")
    L.append("")
    L.append("| Track layer | Plane layer (dielectric) | Track mm | Over (raw) | None, raw | None, antipads excl. |")
    L.append("|---|---|---|---|---|---|")
    rp = b["reference_planes"]
    for r in rp["runs"]:
        L.append("| %s | %s (%.3g mm) | %.2f | %s | **%.2f** | **%.2f** |" % (
            r["layer"], r["plane_layer"], r["dielectric_mm"], r["track_mm"], _fmt_over(r["over_raw"]),
            r["none_raw_mm"], r["none_antipads_excl_mm"]))
    st = [s for s in rp["unreferenced_stretches_antipads_excl"] if s["length_mm"] >= 0.05]
    if st:
        L.append("")
        L.append("Unreferenced stretches (antipads excluded): " + "; ".join(
            "%s %s %.2f mm (%.2f, %.2f)→(%.2f, %.2f) over no %s copper" % (
                s["segment"], _lay(s["layer"]), s["length_mm"], s["from"][0], s["from"][1], s["to"][0], s["to"][1],
                s["plane_layer"]) for s in st))
    if b["via_details"]:
        L.append("")
        L.append("| Via | Position | Layers joined | Planes beside it (within 1 mm) | Nearest via of each plane net (centre to centre) |")
        L.append("|---|---|---|---|---|")
        for v in b["via_details"]:
            planes = "; ".join("%s: %s" % (_lay(l), ", ".join("%s %s" % (_lay(p["plane_layer"]),
                                                                       "/".join(p["nets_within_1mm"]) or NONE)
                                                             for p in ps))
                               for l, ps in v["reference_planes"].items())
            near = ", ".join("%s %s %.2f mm" % (k, x["via"], x["centre_to_centre_mm"])
                             for k, x in v["nearest_plane_net_via"].items()) or "—"
            L.append("| %s | (%.2f, %.2f) | %s | %s | %s |" % (
                v["via"], v["position"][0], v["position"][1], " ↔ ".join(_lay(l) for l in v["connects_layers"]),
                planes, near))
    L.append("")
    L.append("### Passes under / over (plan view)")
    L.append("")
    po = [p for p in b["passes_under_or_over"] if not p["member"]]
    mem = [p for p in b["passes_under_or_over"] if p["member"]]
    if po:
        L.append("| Ref | Value | Side | mm by track layer | Body from |")
        L.append("|---|---|---|---|---|")
        for p in po:
            L.append("| %s | %s | %s | %s | %s |" % (p["ref"], p["value"], p["side"],
                                                    ", ".join("%s %.2f" % (_lay(k), v) for k, v in p["mm_by_layer"].items()),
                                                    p["body_source"]))
    else:
        L.append("None (non-member footprints).")
    if mem:
        L.append("")
        L.append("Inside the bodies of its own parts: " + ", ".join(
            "%s %s" % (p["ref"], ", ".join("%s %.2f" % (_lay(k), v) for k, v in p["mm_by_layer"].items())) for p in mem))
    L.append("")
    L.append("### Neighbours (unprompted, within the radius, ranked by coupled length)")
    L.append("")
    L.append("| Net | Class | Radius | Same layer: all copper (closest) | Track to copper (closest) | Track to track (closest) | "
             "Coupled mm by layer | Plan view: gap, layers, separation (closest) | Crossings |")
    L.append("|---|---|---|---|---|---|---|---|---|")
    for e in b["neighbours"]:
        sl, pv = e.get("same_layer"), e.get("plan_view")
        a = "%.2f %s (%s↔%s)" % (sl["all_copper_mm"], _lay(sl["layer"]), *sl["closest"]) if sl else "—"
        t = ("%.2f (%s↔%s)" % (sl["track_to_track_mm"], *sl["track_to_track_closest"])
             if sl and sl["track_to_track_mm"] is not None else "—")
        tcp = ("%.2f (%s↔%s)" % (sl["track_to_copper_mm"], *sl["track_to_copper_closest"])
               if sl and sl["track_to_copper_mm"] is not None else "—")
        c = ", ".join("%s %.1f" % (_lay(k), v) for k, v in (e.get("coupled_mm") or {}).items()) or "—"
        p = ("%.2f %s/%s %.2f mm (%s↔%s)" % (pv["all_copper_mm"], _lay(pv["target_layer"]), _lay(pv["neighbour_layer"]),
                                            pv["separation_mm"] or 0, *pv["closest"]) if pv else "—")
        x = str(pv["track_crossings"]) if pv else "—"
        L.append("| %s | %s | %g | %s | %s | %s | %s | %s | %s |" % (e["net"], "/".join(e["classes"]), e["radius_mm"],
                                                                   a, tcp, t, c, p, x))
    if b["high_dvdt_pads_nearby"]:
        L.append("")
        L.append("High dv/dt pads nearby: " + "; ".join("%s (%s) %.2f mm %s" % (p["pad"], p["net"], p["gap_mm"], p["method"])
                                                      for p in b["high_dvdt_pads_nearby"]))
    L.append("")
    return "\n".join(L)


def md_report(rep: Dict[str, Any]) -> str:
    L = [md_front_matter(rep["_provenance"])]
    L.append("# Net report — %s" % rep["board"])
    L.append("")
    L.append("Generated from the board model by `%s`. Check freshness before citing: "
             "`python3 tools/lab/check_state.py --fresh <this file>`. Coordinates are KiCad board mm, Y down." % GENERATOR)
    L.append("")
    L.append("**Measuring methods** (every number below names one):")
    L.append("")
    for k, v in rep["methods"].items():
        L.append("- *%s*: %s" % (k.replace("_", " "), v))
    L.append("")
    L.append("Neighbour radii (mm): %s." % ", ".join("%s %g" % kv for kv in rep["radii"].items()))
    L.append("")
    for b in rep["critical"]:
        L.append(md_block(b))
    L.append("## All nets")
    L.append("")
    L.append("| Net | Class | Pads | Track mm | By layer | Widths | Vias | Zones | Connected | Stubs |")
    L.append("|---|---|---|---|---|---|---|---|---|---|")
    for s in rep["all_nets"]:
        L.append("| %s | %s | %d | %.2f | %s | %s | %d | %s | %s | %d |" % (
            s["net"], "/".join(s["classes"]), s["pads"], s["length_mm"],
            ", ".join("%s %.1f" % (_lay(k), v) for k, v in s["length_by_layer"].items()) or "—",
            "/".join("%g" % w for w in s["widths_mm"]) or "—", s["vias"], ",".join(s["zones"]) or "—",
            {True: "yes", False: "**no**", None: "—"}[s["connected"]], s["stubs"]))
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------

def build(model_path: Path, nets: List[str]) -> Dict[str, Any]:
    m = BoardModel.load(model_path)
    geo = Geo(m)
    radii = m.data.get("definitions", {}).get("neighbour_radii_mm") or {"signal": 1.0, "high_current": 3.0,
                                                                         "high_dvdt": 5.0}
    targets = nets or m.data.get("critical_nets", [])
    missing = [n for n in targets if n not in m.nets]
    if missing:
        raise SystemExit("not on this board: %s" % ", ".join(missing))
    return {
        "_provenance": derived_provenance(m, model_path, GENERATOR),
        "board": "%s @ %s" % (m.data["_provenance"]["source"], m.data["_provenance"].get("source_ref") or "working tree"),
        "methods": METHODS, "radii": radii,
        "critical": [full_block(geo, m, n, radii) for n in targets],
        "all_nets": [summary_row(m, n) for n in sorted(m.nets)],
    }


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("model", help="board-model.json from board_model.py")
    ap.add_argument("-o", "--outdir", help="output folder (default: the model's folder)")
    ap.add_argument("--net", action="append", default=[], help="net for a full block (repeatable; "
                    "default: the config's critical_nets)")
    a = ap.parse_args()
    mp = Path(a.model)
    out = Path(a.outdir) if a.outdir else mp.parent
    out.mkdir(parents=True, exist_ok=True)
    rep = build(mp, a.net)
    write_json(out / "net-report.json", rep)
    (out / "net-report.md").write_text(md_report(rep), encoding="utf-8")
    print("wrote %s and %s: %d full blocks, %d nets" % (out / "net-report.md", out / "net-report.json",
                                                         len(rep["critical"]), len(rep["all_nets"])))


if __name__ == "__main__":
    main()

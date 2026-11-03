"""
report_lib.py: shared geometry and provenance for the board-model reports
(net_report.py, plane_report.py, render.py).

Everything here reads a BoardModel (board_model.py) and nothing else.

Measuring methods (named in every report, because the numbers differ):
  - track to track: target track copper (buffered by width/2) to neighbour
    track copper, same layer
  - all copper: tracks + pads + via annular rings (+ same-layer zone fills
    of the neighbour), same layer
  - plan view: target copper on one layer to neighbour copper on another
    layer (zone fills on other layers are reference planes, not neighbours),
    with the dielectric separation between the two layers
  - reference plane: the track centreline over the zone fills of the nearest
    copper layer above / below (stackup), reported two ways:
      raw            fill holes count as "no copper"
      antipads excl. fill holes that contain a drilled hole (via, PTH, NPTH)
                     count as copper, i.e. via and pad antipads are ignored
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shapely.geometry import LineString, MultiPolygon, Point, Polygon
from shapely.ops import unary_union

from board_model import BoardModel, poly_from_json, repo_root, _git

NONE = "<none>"


def r1(v: float) -> float:
    return round(float(v), 2)


# ---------------------------------------------------------------------------
# Provenance for derived outputs
# ---------------------------------------------------------------------------

def derived_provenance(m: BoardModel, model_path: Path, generator: str) -> Dict[str, Any]:
    """Provenance of a report: the PCB's source/hash (so check_state.py --fresh
    checks the report against the .kicad_pcb), plus the model it came from."""
    src = dict(m.data["_provenance"])
    here = Path(__file__).resolve().parent
    commit = _git("rev-parse", "HEAD") or "unknown"
    if _git("status", "--porcelain", "--", str(here / Path(generator).name), str(here / "report_lib.py")):
        commit += "-dirty"
    try:
        mp = str(model_path.resolve().relative_to(repo_root().resolve()))
    except ValueError:
        mp = str(model_path.resolve())
    return {
        "source": src["source"],
        "source_sha256": src["source_sha256"],
        "source_ref": src.get("source_ref"),
        "generator": generator,
        "generator_commit": commit,
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "model": mp,
        "model_sha256": hashlib.sha256(model_path.read_bytes()).hexdigest(),
        "model_generator_commit": src.get("generator_commit"),
    }


def md_front_matter(prov: Dict[str, Any]) -> str:
    lines = ["---"]
    for k, v in prov.items():
        lines.append('%s: "%s"' % (k, "" if v is None else str(v).replace('"', "'")))
    lines.append("---")
    return "\n".join(lines) + "\n"


def write_json(path: Path, obj: Any) -> None:
    path.write_text(json.dumps(obj, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")


def short(net: str) -> str:
    """Net name without its sheet path (for labels): '/Power Management/VSYS' → 'VSYS'."""
    return net.rstrip("/").split("/")[-1] or net


def safe_name(net: str) -> str:
    s = net.strip("/").replace("/", "__").replace(" ", "_").replace("+", "P")
    return "".join(ch for ch in s if ch.isalnum() or ch in "._-") or "net"


# ---------------------------------------------------------------------------
# Geometry index
# ---------------------------------------------------------------------------

class Geo:
    """Per-net, per-layer copper items and per-layer plane fills, cached."""

    def __init__(self, m: BoardModel):
        self.m = m
        self.cu: List[str] = m.data["meta"]["copper_layers"]
        self.items: Dict[str, Dict[str, List[Tuple[str, str, Any]]]] = defaultdict(lambda: defaultdict(list))
        for sid, s in m.segments.items():
            self.items[s["net"]][s["layer"]].append((sid, "track", m.segment_geom(sid)))
        for vid, v in m.vias.items():
            g = m.via_geom(vid)
            for l in v["layers"]:
                self.items[v["net"]][l].append((vid, "via", g))
        for pid, p in m.pads.items():
            if not p["net"]:
                continue
            g = m.pad_geom(pid)
            for l in p["layers"]:
                self.items[p["net"]][l].append((pid, "pad", g))
        # Zone fills per layer per net (keepouts have no fill).
        self.fill_items: Dict[str, Dict[str, List[Tuple[str, Any]]]] = defaultdict(lambda: defaultdict(list))
        for zid, z in m.zones.items():
            if z["keepout"] is not None:
                continue
            for l, f in z["fills"].items():
                self.fill_items[l][z["net"]].append((zid, poly_from_json(f)))
        self.drills = [Point(v["position"]) for v in m.vias.values()] + \
                      [Point(p["center"]) for p in m.pads.values() if p.get("drill")]
        self._union: Dict[Tuple, Any] = {}
        self._fill: Dict[Tuple, Any] = {}
        self.z_mid = self._z_mid()

    # -- copper -----------------------------------------------------------
    def copper(self, net: str, layer: str, kinds=("track", "via", "pad"), zones: bool = False):
        key = (net, layer, tuple(kinds), zones)
        if key not in self._union:
            parts = [g for (_, k, g) in self.items.get(net, {}).get(layer, []) if k in kinds]
            if zones:
                parts += [g for (_, g) in self.fill_items.get(layer, {}).get(net, [])]
            self._union[key] = unary_union(parts) if parts else Polygon()
        return self._union[key]

    def nets_on(self, layer: str) -> List[str]:
        return [n for n, by in self.items.items() if by.get(layer)]

    # -- planes -----------------------------------------------------------
    def fill(self, layer: str, net: Optional[str] = None, closed: bool = False):
        """Zone fill on a layer (one net, or all). closed=True fills the holes
        that contain a drilled hole (antipads), leaving real voids open."""
        key = (layer, net, closed)
        if key not in self._fill:
            nets = [net] if net is not None else list(self.fill_items.get(layer, {}))
            parts = []
            for n in nets:
                for (_, g) in self.fill_items.get(layer, {}).get(n, []):
                    parts.append(self._close(g) if closed else g)
            self._fill[key] = unary_union(parts) if parts else Polygon()
        return self._fill[key]

    def fill_nets(self, layer: str) -> List[str]:
        return sorted(self.fill_items.get(layer, {}))

    def _close(self, g):
        polys = list(g.geoms) if hasattr(g, "geoms") else [g]
        out = []
        for p in polys:
            keep = [h for h in p.interiors if not self._has_drill(Polygon(h))]
            out.append(Polygon(p.exterior, keep))
        return unary_union(out)

    def antipad_holes(self, layer: str) -> List[Tuple[str, Polygon, int]]:
        """(net, hole polygon, drills inside) for every fill hole with a drill in it."""
        out = []
        for net in self.fill_nets(layer):
            g = self.fill(layer, net)
            for p in (list(g.geoms) if hasattr(g, "geoms") else [g]):
                for h in p.interiors:
                    hp = Polygon(h)
                    n = self._has_drill(hp)
                    if n:
                        out.append((net, hp, n))
        return out

    def _has_drill(self, hp: Polygon) -> int:
        x0, y0, x1, y1 = hp.bounds
        return sum(1 for d in self.drills
                   if x0 <= d.x <= x1 and y0 <= d.y <= y1 and hp.contains(d))

    # -- stackup ----------------------------------------------------------
    def _z_mid(self) -> Dict[str, float]:
        z = {}
        for L in self.m.data["stackup"].get("layers", []):
            if L["type"] == "copper":
                z[L["name"]] = L["z_top_mm"] + L["thickness_mm"] / 2.0
        return z

    def separation(self, la: str, lb: str) -> Optional[float]:
        """Dielectric between two copper layers (sum of non-copper thicknesses)."""
        if la == lb:
            return 0.0
        layers = self.m.data["stackup"].get("layers", [])
        names = [L["name"] for L in layers]
        if la not in names or lb not in names:
            return None
        i, j = sorted((names.index(la), names.index(lb)))
        return round(sum(L["thickness_mm"] for L in layers[i + 1:j] if L["type"] != "copper"), 4)

    def adjacent(self, layer: str) -> List[Tuple[str, float]]:
        adj = self.m.data["stackup"].get("adjacency", {}).get(layer, {})
        out = []
        for side in ("above", "below"):
            a = adj.get(side)
            if a:
                out.append((a["layer"], a["dielectric_mm"]))
        return out


# ---------------------------------------------------------------------------
# Reference plane
# ---------------------------------------------------------------------------

def _pieces(geom) -> List[LineString]:
    if geom.is_empty:
        return []
    if geom.geom_type == "LineString":
        return [geom]
    if hasattr(geom, "geoms"):
        out = []
        for g in geom.geoms:
            out.extend(_pieces(g))
        return out
    return []


def reference_for_line(geo: Geo, line: LineString, layer: str) -> List[Dict[str, Any]]:
    """For each adjacent copper layer: mm of the centreline over each fill net,
    and mm over nothing (raw, and with antipads excluded), plus the void pieces."""
    out = []
    for adj, diel in geo.adjacent(layer):
        over, over_c = {}, {}
        for net in geo.fill_nets(adj):
            l_raw = line.intersection(geo.fill(adj, net)).length
            l_c = line.intersection(geo.fill(adj, net, closed=True)).length
            if l_raw > 1e-6:
                over[net] = l_raw
            if l_c > 1e-6:
                over_c[net] = l_c
        none_raw = max(0.0, line.length - sum(over.values()))
        none_c = max(0.0, line.length - sum(over_c.values()))
        voids = [p for p in _pieces(line.difference(geo.fill(adj, closed=True))) if p.length > 1e-3]
        out.append({"plane_layer": adj, "dielectric_mm": diel, "over": over, "over_antipads_excl": over_c,
                    "none_raw": none_raw, "none_antipads_excl": none_c, "voids": voids})
    return out


# ---------------------------------------------------------------------------
# Neighbours
# ---------------------------------------------------------------------------

def radius_for(classes: List[str], radii: Dict[str, float]) -> float:
    return max(radii.get(c, radii.get("signal", 1.0)) for c in (classes or ["signal"]))


def _closest(a_items, b_items) -> Tuple[float, Optional[str], Optional[str]]:
    best = (1e9, None, None)
    for (ia, _, ga) in a_items:
        for (ib, _, gb) in b_items:
            d = ga.distance(gb)
            if d < best[0]:
                best = (d, ia, ib)
    return best


def neighbours(geo: Geo, target: str, radii: Dict[str, float]) -> List[Dict[str, Any]]:
    """Every other net with copper within the radius of the target's copper:
    same layer (track to track, all copper) and plan view across layers."""
    m = geo.m
    tclasses = m.nets.get(target, {}).get("classes", ["signal"])
    t_layers = [l for l in geo.cu if geo.items.get(target, {}).get(l)]
    tracks_by_layer = defaultdict(list)
    for sid in m.nets.get(target, {}).get("segments", []):
        s = m.segments[sid]
        tracks_by_layer[s["layer"]].append(s)
    out = []
    for net in sorted(set(geo.items) | {n for l in geo.cu for n in geo.fill_nets(l)}):
        if net == target or not net:
            continue
        nclasses = m.nets.get(net, {}).get("classes", ["signal"])
        r = max(radius_for(nclasses, radii), radius_for(tclasses, radii))
        best_same, best_plan = None, None
        per_layer = {}
        for lt in t_layers:
            T = geo.copper(target, lt, zones=True)
            if T.is_empty:
                continue
            for ln in geo.cu:
                if ln == lt:
                    N = geo.copper(net, ln, zones=True)
                else:
                    N = geo.copper(net, ln)   # other-layer fills are planes, not neighbours
                if N.is_empty:
                    continue
                d = T.distance(N)
                if d > r:
                    continue
                if ln == lt:
                    if best_same is None or d < best_same[0]:
                        best_same = (d, lt)
                    per_layer[lt] = d
                else:
                    if best_plan is None or d < best_plan[0]:
                        best_plan = (d, lt, ln)
        if best_same is None and best_plan is None:
            continue
        entry: Dict[str, Any] = {"net": net, "classes": nclasses, "radius_mm": r}
        if best_same is not None:
            d, lt = best_same
            t_items = geo.items[target][lt]
            n_items = geo.items.get(net, {}).get(lt, []) + \
                [(zid, "zone", g) for (zid, g) in geo.fill_items.get(lt, {}).get(net, [])]
            dd, ia, ib = _closest(t_items, n_items)
            t_tracks = [i for i in t_items if i[1] == "track"]
            tt = _closest(t_tracks, [i for i in n_items if i[1] == "track"])
            tc = _closest(t_tracks, n_items)
            entry["same_layer"] = {
                "all_copper_mm": r1(d), "layer": lt, "closest": [ia, ib],
                "track_to_track_mm": r1(tt[0]) if tt[1] else None,
                "track_to_track_closest": [tt[1], tt[2]] if tt[1] else None,
                "track_to_copper_mm": r1(tc[0]) if tc[1] else None,
                "track_to_copper_closest": [tc[1], tc[2]] if tc[1] else None,
                "by_layer_all_copper_mm": {k: r1(v) for k, v in sorted(per_layer.items())},
                "by_layer_track_to_track_mm": {
                    l: r1(d2) for l in sorted(per_layer) for (d2, a2, _) in [_closest(
                        [i for i in geo.items[target][l] if i[1] == "track"],
                        [i for i in geo.items.get(net, {}).get(l, []) if i[1] == "track"])] if a2},
            }
            # Coupled length: target centreline within r (edge to edge) of the
            # neighbour's same-layer copper.
            coupled = {}
            for l, ss in tracks_by_layer.items():
                N = geo.copper(net, l, zones=True)
                if N.is_empty or N.distance(geo.copper(target, l, zones=True)) > r:
                    continue
                tot = 0.0
                for s in ss:
                    tot += m.segment_line(s["id"]).intersection(N.buffer(r + s["width"] / 2.0, 8)).length
                if tot > 1e-3:
                    coupled[l] = r1(tot)
            entry["coupled_mm"] = coupled
        if best_plan is not None:
            d, lt, ln = best_plan
            dd, ia, ib = _closest(geo.items[target][lt], geo.items.get(net, {}).get(ln, []))
            crossings = 0
            nsegs = [m.segments[x] for x in m.nets.get(net, {}).get("segments", [])]
            for l, ss in tracks_by_layer.items():
                for ns in nsegs:
                    if ns["layer"] == l:
                        continue
                    nl = m.segment_line(ns["id"])
                    crossings += sum(1 for s in ss if m.segment_line(s["id"]).intersects(nl))
            entry["plan_view"] = {"all_copper_mm": r1(d), "target_layer": lt, "neighbour_layer": ln,
                                  "separation_mm": geo.separation(lt, ln), "closest": [ia, ib],
                                  "track_crossings": crossings}
        out.append(entry)

    def rank(e):
        c = sum(e.get("coupled_mm", {}).values())
        gaps = [e[k]["all_copper_mm"] for k in ("same_layer", "plan_view") if k in e]
        return (-c, min(gaps))
    out.sort(key=rank)
    return out


# ---------------------------------------------------------------------------
# Bodies the net passes under / over
# ---------------------------------------------------------------------------

def body_overlaps(m: BoardModel, net: str, min_mm: float = 0.05) -> List[Dict[str, Any]]:
    n = m.nets.get(net, {})
    members = {m.pads[p]["ref"] for p in n.get("pads", [])}
    out = []
    lines = [(m.segments[s]["layer"], m.segment_line(s)) for s in n.get("segments", [])]
    for ref, fp in m.footprints.items():
        if not fp["body"]:
            continue
        b = m.body(ref)
        if b.is_empty:
            continue
        by_layer = defaultdict(float)
        for layer, ln in lines:
            if ln.intersects(b):
                by_layer[layer] += ln.intersection(b).length
        tot = sum(by_layer.values())
        if tot >= min_mm:
            out.append({"ref": ref, "value": fp["value"], "side": fp["side"], "body_source": fp["body_source"],
                        "member": ref in members, "mm_by_layer": {k: r1(v) for k, v in sorted(by_layer.items())},
                        "mm": r1(tot)})
    out.sort(key=lambda e: -e["mm"])
    return out


# ---------------------------------------------------------------------------
# Route narrative
# ---------------------------------------------------------------------------

def _legs(points: List[List[float]]) -> List[Dict[str, Any]]:
    legs = []
    for a, b in zip(points, points[1:]):
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy)
        if L < 1e-6:
            continue
        if legs:
            pa, pb = legs[-1]["from"], legs[-1]["to"]
            ex, ey = pb[0] - pa[0], pb[1] - pa[1]
            el = math.hypot(ex, ey)
            if el > 0 and abs(ex * dy - ey * dx) / (el * L) < 0.01 and ex * dx + ey * dy > 0:
                legs[-1]["to"] = b
                legs[-1]["length_mm"] += L
                continue
        legs.append({"from": a, "to": b, "length_mm": L})
    for g in legs:
        (x0, y0), (x1, y1) = g["from"], g["to"]
        if abs(y1 - y0) < 0.02:
            g["dir"] = "along y=%.2f (x %.1f→%.1f)" % (y0, x0, x1)
        elif abs(x1 - x0) < 0.02:
            g["dir"] = "along x=%.2f (y %.1f→%.1f)" % (x0, y0, y1)
        else:
            g["dir"] = "diagonal (%.1f,%.1f)→(%.1f,%.1f)" % (x0, y0, x1, y1)
        g["length_mm"] = r1(g["length_mm"])
    return legs


def node_label(m: BoardModel, nid: str, nodes: Dict[str, Dict]) -> str:
    n = nodes.get(nid, {})
    k = n.get("kind")
    if k == "pad":
        p = m.pads[nid]
        fp = m.footprints[p["ref"]]
        fn = (" " + p["pin_function"]) if p.get("pin_function") and p["pin_function"] != p["number"] else ""
        return "%s%s (%s)" % (nid, fn, fp["value"])
    if k == "via":
        v = m.vias[nid]
        return "via %s (%.2f, %.2f)" % (nid, v["position"][0], v["position"][1])
    if k == "zone":
        return "zone fill %s" % nid
    pos = n.get("pos") or [0, 0]
    return "%s (%.2f, %.2f)" % (k or "node", pos[0], pos[1])


def route_tree(m: BoardModel, net: str, min_leg_mm: float = 1.0) -> Dict[str, Any]:
    """The route as a tree from the root along the shortest copper paths."""
    t = m.nets[net].get("topology") or {}
    root = t.get("root")
    nodes = {n["id"]: n for n in t.get("nodes", [])}
    chains = {c["id"]: c for c in t.get("chains", [])}
    branch_len = {b["to"]: b for b in t.get("branches", []) if b.get("reachable")}
    children = defaultdict(list)
    in_tree = set()
    for b in t.get("branches", []):
        if not b.get("reachable"):
            continue
        path, cids = b["path"], b["chains"]
        for u, v, cid in zip(path, path[1:], cids):
            if (v, cid) not in children[u]:
                children[u].append((v, cid))
            in_tree.add(cid)
    lines: List[str] = []

    def chain_text(cid: str) -> str:
        c = chains[cid]
        lay = c["layer"] if isinstance(c["layer"], str) else "/".join(c["layer"] or ["?"])
        legs = [g for g in _legs(c["points"]) if g["length_mm"] >= min_leg_mm]
        detail = ""
        if len(legs) > 1 or (legs and legs[0]["length_mm"] >= 3):
            detail = " [" + "; ".join("%.1f %s" % (g["length_mm"], g["dir"]) for g in legs) + "]"
        w = "/".join("%g" % x for x in c["widths"])
        return "%s %.1f mm%s%s" % (lay, c["length_mm"], (" w" + w) if w else "", detail)

    def walk(u: str, prefix: str):
        kids = sorted(children.get(u, []), key=lambda vc: branch_len.get(vc[0], {}).get("length_mm", 0)
                      if vc[0] in branch_len else 0)
        for i, (v, cid) in enumerate(kids):
            last = i == len(kids) - 1
            tag = ""
            if v in branch_len:
                b = branch_len[v]
                tag = "   ⟨%.1f mm from root, %d via%s; %s⟩" % (
                    b["length_mm"], b["vias"], "" if b["vias"] == 1 else "s",
                    ", ".join("%s %.1f" % (k.split(".")[0], x) for k, x in b["by_layer"].items()))
            lines.append("%s%s─ %s → %s%s" % (prefix, "└" if last else "├", chain_text(cid),
                                             node_label(m, v, nodes), tag))
            walk(v, prefix + ("   " if last else "│  "))

    if root:
        lines.append("%s  — root (%s)" % (node_label(m, root, nodes), t.get("root_source")))
        walk(root, "")
    extra = [chains[c] for c in chains if c not in in_tree]
    for c in extra:
        lines.append("  (off-tree) %s ↔ %s: %s" % (node_label(m, c["a"], nodes), node_label(m, c["b"], nodes),
                                                  chain_text(c["id"])))
    legs = {cid: _legs(c["points"]) for cid, c in chains.items()}
    return {"root": root, "root_source": t.get("root_source"), "text": "\n".join(lines),
            "chains": [{"id": c["id"], "a": c["a"], "b": c["b"], "layer": c["layer"],
                        "length_mm": c["length_mm"], "widths": c["widths"], "segments": c["segments"],
                        "in_tree": c["id"] in in_tree,
                        "legs": [{"length_mm": g["length_mm"], "dir": g["dir"]} for g in legs[c["id"]]]}
                       for c in chains.values()]}

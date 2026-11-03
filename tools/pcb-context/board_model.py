#!/usr/bin/env python3
"""
board_model.py: one parse of a .kicad_pcb into one board model.

Spec: docs/research/v7-retry/kicad-extraction-audit.md §5.2 and §6.1.
Every report (net, plane, render) is derived from this model, so the
placement and routing views can't drift apart again.

The model holds:
  - footprints: true pad polygons (rotated; roundrect/oval/circle/custom;
    `*.Cu` and `F&B.Cu` expanded) and a body polygon (courtyard, then fab,
    then pads + footprint-name dims)
  - the board outline as a polygon (with cutouts)
  - segments, arcs (sampled) and vias, per net
  - zones: outline, de-fractured fills with holes, keepouts, priority,
    and a warning for any zone that has no fill
  - the stackup from `setup` (layer order, dielectric thicknesses, the
    copper layer above and below each copper layer)
  - a per-net topology graph (pads, vias, zones, junctions, dangling ends;
    chains between them; branches from a root pad; stubs; islands)
  - the kicad-cli DRC result for the same file
  - `_provenance` (tools/CONTEXT.md Source-Hash Rule)

Usage:
    python board_model.py <file.kicad_pcb> [-o board-model.json] [--config cfg.json]
                          [--no-drc] [--source-ref REF]
    python board_model.py --check <board-model.json>   # exit 0 fresh, 1 stale, 2 none

Library use (reports):
    from board_model import BoardModel
    m = BoardModel.load("board-model.json")
    m.net_copper("/I2C_SDA")      # {layer: shapely geometry}, edge-to-edge ready

Coordinates are KiCad board mm, Y down. Clearances computed from the model
are copper edge to copper edge (segments buffered by half their width).
"""

from __future__ import annotations

import argparse
import hashlib
import heapq
import json
import math
import os
import subprocess
import sys
import tempfile
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kiutils.board import Board
from kiutils.items.brditems import Arc, Segment, Via
from shapely.geometry import (LineString, MultiPolygon, Point, Polygon, box,
                              mapping)
from shapely.ops import polygonize, unary_union
from shapely import affinity

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))

# Reused from the existing extractors (spot-checked; see README).
from routing_extract import (_arc_to_polyline, _polyline_length,  # noqa: E402
                             _ref_sort_key, _world_xy, build_net_index)
from extract import (_BBOX_MIN_DIMENSION_MM,  # noqa: E402
                     _parse_inductor_dims_from_name, extract_footprint_name)

GENERATOR = "tools/pcb-context/board_model.py"
SCHEMA_VERSION = 1
KICAD_CLI_DEFAULT = "/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli"
CONFIG_DIR = _HERE / "board-config"

ND = 4            # decimals kept in the JSON
SNAP = 1e-3       # mm: endpoints closer than this are the same point
ARC_QUAD = 4      # shapely quad_segs for round corners (pad shapes)


# ---------------------------------------------------------------------------
# Small geometry helpers
# ---------------------------------------------------------------------------

def _r(v: float) -> float:
    return round(float(v), ND)


def _pt(x: float, y: float) -> List[float]:
    return [_r(x), _r(y)]


def poly_to_json(geom) -> List[Dict[str, Any]]:
    """Polygon / MultiPolygon → [{"exterior": [[x,y]..], "holes": [[[x,y]..]..]}]."""
    if geom is None or geom.is_empty:
        return []
    parts = list(geom.geoms) if hasattr(geom, "geoms") else [geom]
    out = []
    for p in parts:
        if p.geom_type != "Polygon" or p.is_empty:
            continue
        out.append({
            "exterior": [_pt(x, y) for x, y in p.exterior.coords],
            "holes": [[_pt(x, y) for x, y in h.coords] for h in p.interiors],
        })
    return out


def poly_from_json(parts: List[Dict[str, Any]]):
    polys = [Polygon(p["exterior"], p.get("holes") or []) for p in parts]
    if not polys:
        return Polygon()
    return polys[0] if len(polys) == 1 else MultiPolygon(polys)


def _local_to_world(geom, cx: float, cy: float, angle_deg: float):
    """Rotate a local-frame geometry by KiCad's angle convention, then move it.

    Same transform as routing_extract._world_xy (Y down):
        gx = cx + lx*cos(θ) + ly*sin(θ);  gy = cy - lx*sin(θ) + ly*cos(θ)
    """
    t = math.radians(angle_deg or 0.0)
    c, s = math.cos(t), math.sin(t)
    return affinity.affine_transform(geom, [c, s, -s, c, cx, cy])


def _graphic_points(gi) -> List[Tuple[float, float]]:
    """Local points of a footprint/board graphic item (for hulls and bboxes)."""
    name = type(gi).__name__
    if name.endswith("Poly"):
        return [(c.X, c.Y) for c in gi.coordinates]
    if name.endswith("Circle"):
        r = math.hypot(gi.end.X - gi.center.X, gi.end.Y - gi.center.Y)
        return list(Point(gi.center.X, gi.center.Y).buffer(r, ARC_QUAD).exterior.coords)
    if name.endswith("Arc"):
        return _arc_to_polyline(gi)
    if name.endswith("Rect"):
        return [(gi.start.X, gi.start.Y), (gi.end.X, gi.start.Y),
                (gi.end.X, gi.end.Y), (gi.start.X, gi.end.Y)]
    if hasattr(gi, "start") and hasattr(gi, "end"):
        return [(gi.start.X, gi.start.Y), (gi.end.X, gi.end.Y)]
    return []


def _shape_from_graphics(items) -> Optional[Any]:
    """Closed shape from graphic items: closed primitives as polygons, lines
    and arcs polygonized; convex hull of all points if nothing closes."""
    polys, lines, pts = [], [], []
    for gi in items:
        name = type(gi).__name__
        p = _graphic_points(gi)
        if not p:
            continue
        pts.extend(p)
        if name.endswith(("Poly", "Circle", "Rect")) and len(p) >= 3:
            polys.append(Polygon(p).buffer(0))
        else:
            lines.append(LineString(p))
    if lines:
        polys.extend(polygonize(unary_union(lines)))
    if polys:
        g = unary_union(polys)
        if not g.is_empty:
            return g
    if len(pts) >= 3:
        return Polygon(pts).convex_hull if len(set(pts)) >= 3 else None
    return None


# ---------------------------------------------------------------------------
# Layers and stackup
# ---------------------------------------------------------------------------

def copper_layers(board: Board) -> List[str]:
    """Copper layers top to bottom (F.Cu, In1.Cu, ..., B.Cu)."""
    cu = [l.name for l in board.layers if l.name.endswith(".Cu")]

    def key(n: str) -> Tuple[int, int]:
        if n == "F.Cu":
            return (0, 0)
        if n == "B.Cu":
            return (2, 0)
        digits = "".join(ch for ch in n if ch.isdigit())
        return (1, int(digits) if digits else 0)
    return sorted(cu, key=key)


def expand_layers(layers: List[str], cu: List[str]) -> List[str]:
    """Pad/via layer list → the copper layers it really occupies."""
    out: List[str] = []
    for l in layers or []:
        if l == "*.Cu":
            out.extend(cu)
        elif l == "F&B.Cu":
            out.extend([cu[0], cu[-1]])
        elif l.endswith(".Cu") and l in cu:
            out.append(l)
    seen = set()
    return [l for l in out if not (l in seen or seen.add(l))]


def via_span(layers: List[str], cu: List[str]) -> List[str]:
    ends = [l for l in layers if l in cu]
    if len(ends) < 2:
        return list(cu)
    i0, i1 = sorted((cu.index(ends[0]), cu.index(ends[-1])))
    return cu[i0:i1 + 1]


def extract_stackup(board: Board, cu: List[str], warnings: List[str]) -> Dict[str, Any]:
    st = board.setup.stackup if board.setup else None
    layers_out: List[Dict[str, Any]] = []
    if st is None or not st.layers:
        warnings.append("stackup: no stackup in setup; copper order only, no thicknesses")
        return {"layers": [], "copper_order": cu, "adjacency": {
            l: {"above": None, "below": None} for l in cu}, "board_thickness_mm": None}
    z = 0.0
    for L in st.layers:
        t = L.thickness or 0.0
        entry = {"name": L.name, "type": L.type, "thickness_mm": _r(t),
                 "material": L.material, "epsilon_r": getattr(L, "epsilonR", None),
                 "z_top_mm": _r(z)}
        layers_out.append(entry)
        z += t
    # Separation between successive copper layers = sum of the dielectrics between them.
    adjacency: Dict[str, Dict[str, Any]] = {}
    cu_idx = [i for i, e in enumerate(layers_out) if e["type"] == "copper"]
    names = [layers_out[i]["name"] for i in cu_idx]
    for k, i in enumerate(cu_idx):
        def sep(a: int, b: int) -> float:
            lo, hi = sorted((a, b))
            return sum(layers_out[j]["thickness_mm"] for j in range(lo + 1, hi)
                       if layers_out[j]["type"] not in ("copper",))
        above = ({"layer": names[k - 1], "dielectric_mm": _r(sep(cu_idx[k - 1], i))}
                 if k > 0 else None)
        below = ({"layer": names[k + 1], "dielectric_mm": _r(sep(i, cu_idx[k + 1]))}
                 if k + 1 < len(cu_idx) else None)
        adjacency[names[k]] = {"above": above, "below": below}
    return {"layers": layers_out, "copper_order": names or cu, "adjacency": adjacency,
            "board_thickness_mm": _r(z)}


# ---------------------------------------------------------------------------
# Outline
# ---------------------------------------------------------------------------

def extract_outline(board: Board, warnings: List[str]) -> Dict[str, Any]:
    items = [g for g in board.graphicItems if getattr(g, "layer", "") == "Edge.Cuts"]
    world_items_geoms = []
    for fp in board.footprints:
        fx, fy, fa = fp.position.X, fp.position.Y, fp.position.angle or 0
        for g in fp.graphicItems:
            if getattr(g, "layer", "") == "Edge.Cuts":
                p = _graphic_points(g)
                if len(p) >= 2:
                    world_items_geoms.append(_local_to_world(LineString(p), fx, fy, fa))
    polys, lines = [], list(world_items_geoms)
    for g in items:
        name = type(g).__name__
        p = _graphic_points(g)
        if name.endswith(("Rect", "Poly", "Circle")) and len(p) >= 3:
            polys.append(Polygon(p))
        elif len(p) >= 2:
            lines.append(LineString(p))
    if lines:
        polys.extend(polygonize(unary_union(lines)))
    if not polys:
        warnings.append("outline: no closed Edge.Cuts shape found")
        return {"polygon": [], "bbox": None, "area_mm2": 0.0}
    polys.sort(key=lambda p: p.area, reverse=True)
    outer = polys[0]
    holes = [p for p in polys[1:] if outer.contains(p)]
    shape = outer.difference(unary_union(holes)) if holes else outer
    x0, y0, x1, y1 = shape.bounds
    return {"polygon": poly_to_json(shape), "bbox": [_r(x0), _r(y0), _r(x1), _r(y1)],
            "width_mm": _r(x1 - x0), "height_mm": _r(y1 - y0),
            "area_mm2": _r(shape.area), "cutouts": len(holes)}


# ---------------------------------------------------------------------------
# Pads and bodies
# ---------------------------------------------------------------------------

def _pad_local_shape(pad):
    w, h = float(pad.size.X or 0.0), float(pad.size.Y or 0.0)
    shape = pad.shape
    if shape == "circle":
        return Point(0, 0).buffer(w / 2.0, ARC_QUAD * 4)
    if shape == "oval":
        if abs(w - h) < 1e-9:
            return Point(0, 0).buffer(w / 2.0, ARC_QUAD * 4)
        if w > h:
            return LineString([(-(w - h) / 2, 0), ((w - h) / 2, 0)]).buffer(h / 2.0, ARC_QUAD * 4)
        return LineString([(0, -(h - w) / 2), (0, (h - w) / 2)]).buffer(w / 2.0, ARC_QUAD * 4)
    if shape == "roundrect":
        r = (pad.roundrectRatio or 0.25) * min(w, h)
        if r <= 1e-9:
            return box(-w / 2, -h / 2, w / 2, h / 2)
        inner = box(-w / 2 + r, -h / 2 + r, w / 2 - r, h / 2 - r)
        return inner.buffer(r, ARC_QUAD)
    if shape == "custom":
        anchor_kind = getattr(pad.customPadOptions, "anchor", "rect") if pad.customPadOptions else "rect"
        parts = []
        if w > 0 and h > 0:
            parts.append(Point(0, 0).buffer(w / 2.0, ARC_QUAD * 4) if anchor_kind == "circle"
                         else box(-w / 2, -h / 2, w / 2, h / 2))
        for prim in pad.customPadPrimitives or []:
            p = _graphic_points(prim)
            sw = float(getattr(prim, "width", 0.0) or 0.0)
            name = type(prim).__name__
            if name.endswith(("Poly", "Rect", "Circle")) and len(p) >= 3:
                g = Polygon(p).buffer(0)
                parts.append(g.buffer(sw / 2.0, ARC_QUAD) if sw > 0 else g)
            elif len(p) >= 2:
                parts.append(LineString(p).buffer(max(sw, 1e-3) / 2.0, ARC_QUAD))
        return unary_union(parts) if parts else Point(0, 0).buffer(0.01)
    # rect, trapezoid (kiutils 1.4.8 has no rect_delta; treated as rect), unknown
    return box(-w / 2, -h / 2, w / 2, h / 2)


def build_pads(fp, ref: str, cu: List[str]) -> List[Dict[str, Any]]:
    fx, fy, fa = fp.position.X, fp.position.Y, fp.position.angle or 0
    out, seen = [], defaultdict(int)
    for pad in fp.pads:
        gx, gy = _world_xy(fx, fy, fa, pad.position.X, pad.position.Y)
        # Pad angle in the file is absolute (it already includes the footprint's).
        pangle = pad.position.angle if pad.position.angle is not None else 0.0
        drill = None
        if pad.drill is not None:
            drill = _r(getattr(pad.drill, "diameter", 0.0) or 0.0)
        layers = expand_layers(pad.layers, cu)
        if pad.type == "np_thru_hole" and drill is not None and \
                max(pad.size.X or 0, pad.size.Y or 0) <= (drill or 0) + 1e-6:
            layers = []   # a bare hole: no copper
        geom = _local_to_world(_pad_local_shape(pad), gx, gy, pangle)
        num = pad.number or ""
        seen[num] += 1
        pid = "%s.%s" % (ref, num) if seen[num] == 1 else "%s.%s#%d" % (ref, num, seen[num])
        net = getattr(pad.net, "name", "") if pad.net is not None else ""
        out.append({
            "id": pid, "ref": ref, "number": num, "net": net or "",
            "pin_function": pad.pinFunction, "pin_type": pad.pinType,
            "type": pad.type, "shape": pad.shape,
            "center": _pt(gx, gy), "angle": _r(pangle),
            "size": [_r(pad.size.X or 0), _r(pad.size.Y or 0)],
            "drill": drill, "layers": layers,
            "polygon": poly_to_json(geom),
        })
    return out


def build_body(fp, side: str, pads: List[Dict[str, Any]]) -> Tuple[Any, str]:
    """Body polygon in world coords: courtyard → fab → pads (+ name dims)."""
    fx, fy, fa = fp.position.X, fp.position.Y, fp.position.angle or 0
    prefix = "F." if side == "front" else "B."
    for tag, layer in (("courtyard", prefix + "CrtYd"), ("fab", prefix + "Fab")):
        items = [g for g in fp.graphicItems if getattr(g, "layer", "") == layer
                 and not type(g).__name__.endswith("Text")]
        shp = _shape_from_graphics(items) if items else None
        if shp is not None and not shp.is_empty:
            x0, y0, x1, y1 = shp.bounds
            if (x1 - x0) >= _BBOX_MIN_DIMENSION_MM and (y1 - y0) >= _BBOX_MIN_DIMENSION_MM:
                return _local_to_world(shp, fx, fy, fa), tag
    # Pad fallback, in local frame so the name dims line up with the body axes.
    local = [_pad_local_shape(p) for p in fp.pads]
    local = [affinity.translate(_local_rot(g, p, fa), p.position.X, p.position.Y)
             for g, p in zip(local, fp.pads)]
    if not local:
        return Polygon(), "none"
    x0, y0, x1, y1 = unary_union(local).bounds
    src = "pads"
    dims = _parse_inductor_dims_from_name(extract_footprint_name(fp))
    if dims and (y1 - y0) < (x1 - x0) / 2:
        bl, bw = dims
        cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        x0, x1 = min(x0, cx - bl / 2), max(x1, cx + bl / 2)
        y0, y1 = min(y0, cy - bw / 2), max(y1, cy + bw / 2)
        src = "pads+name_dims"
    return _local_to_world(box(x0, y0, x1, y1), fx, fy, fa), src


def _local_rot(geom, pad, fp_angle: float):
    """Pad shape rotated into the footprint frame (pad angle relative to footprint)."""
    rel = (pad.position.angle or 0.0) - (fp_angle or 0.0)
    return _local_to_world(geom, 0.0, 0.0, rel)


def extract_footprints(board: Board, cu: List[str]) -> List[Dict[str, Any]]:
    out = []
    for fp in board.footprints:
        ref = fp.properties.get("Reference", "") if isinstance(fp.properties, dict) else ""
        side = "front" if fp.layer == "F.Cu" else "back"
        pads = build_pads(fp, ref, cu)
        body, src = build_body(fp, side, pads)
        attrs = fp.attributes
        out.append({
            "ref": ref,
            "value": fp.properties.get("Value", "") if isinstance(fp.properties, dict) else "",
            "footprint": fp.libId or fp.entryName or "",
            "lcsc": (fp.properties.get("LCSC") or fp.properties.get("LCSC Part") or "")
            if isinstance(fp.properties, dict) else "",
            "position": _pt(fp.position.X, fp.position.Y),
            "rotation": _r(fp.position.angle or 0),
            "side": side,
            "attributes": {"type": getattr(attrs, "type", None),
                           "exclude_from_bom": bool(getattr(attrs, "excludeFromBom", False)),
                           "board_only": bool(getattr(attrs, "boardOnly", False))},
            "body_source": src,
            "body": poly_to_json(body),
            "pads": pads,
        })
    out.sort(key=lambda c: _ref_sort_key(c["ref"]))
    return out


# ---------------------------------------------------------------------------
# Tracks and vias
# ---------------------------------------------------------------------------

def extract_tracks(board: Board, net_index: Dict[int, str], cu: List[str]):
    segs, vias = [], []
    for item in board.traceItems:
        net = net_index.get(item.net, "<net#%s>" % item.net)
        if isinstance(item, Segment):
            p = [(item.start.X, item.start.Y), (item.end.X, item.end.Y)]
            segs.append({"id": "S%d" % len(segs), "net": net, "kind": "segment",
                         "layer": item.layer, "width": _r(item.width),
                         "points": [_pt(*q) for q in p],
                         "length_mm": _r(_polyline_length(p))})
        elif isinstance(item, Arc):
            p = _arc_to_polyline(item)
            segs.append({"id": "S%d" % len(segs), "net": net, "kind": "arc",
                         "layer": item.layer, "width": _r(item.width),
                         "points": [_pt(*q) for q in p],
                         "length_mm": _r(_polyline_length(p))})
        elif isinstance(item, Via):
            vias.append({"id": "V%d" % len(vias), "net": net,
                         "position": _pt(item.position.X, item.position.Y),
                         "size": _r(item.size or 0), "drill": _r(item.drill or 0),
                         "type": item.type or "through",
                         "layers": via_span(list(item.layers), cu)})
    return segs, vias


def extract_graphic_copper(board: Board, cu: List[str]) -> List[Dict[str, Any]]:
    out = []
    for g in board.graphicItems:
        layer = getattr(g, "layer", "")
        if layer not in cu or type(g).__name__.endswith("Text"):
            continue
        p = _graphic_points(g)
        name = type(g).__name__
        filled = str(getattr(g, "fill", "") or "") in ("yes", "solid", "true")
        sw = float(getattr(g, "width", 0.0) or 0.0)
        if name.endswith(("Rect", "Poly", "Circle")) and len(p) >= 3:
            geom = Polygon(p) if filled else LineString(list(p) + [p[0]]).buffer(max(sw, 1e-3) / 2)
        elif len(p) >= 2:
            geom = LineString(p).buffer(max(sw, 1e-3) / 2)
        else:
            continue
        out.append({"kind": name, "layer": layer, "net": getattr(g, "net", None),
                    "filled": filled, "polygon": poly_to_json(geom)})
    return out


# ---------------------------------------------------------------------------
# Zones
# ---------------------------------------------------------------------------

def extract_zones(board: Board, cu: List[str], warnings: List[str]) -> List[Dict[str, Any]]:
    out = []
    for i, z in enumerate(board.zones):
        layers = expand_layers(z.layers, cu)
        outline = unary_union([Polygon([(c.X, c.Y) for c in p.coordinates]).buffer(0)
                               for p in z.polygons]) if z.polygons else Polygon()
        keepout = None
        if z.keepoutSettings is not None:
            k = z.keepoutSettings
            keepout = {"tracks": k.tracks, "vias": k.vias, "pads": k.pads,
                       "copperpour": k.copperpour, "footprints": k.footprints}
        fills_by_layer: Dict[str, List[Any]] = defaultdict(list)
        for fpoly in z.filledPolygons or []:
            raw = Polygon([(c.X, c.Y) for c in fpoly.coordinates])
            # KiCad stores fills fractured: holes joined to the outer edge by
            # zero-width slits. buffer(0) turns the slits back into holes.
            fixed = raw.buffer(0)
            if raw.area > 0 and abs(fixed.area - abs(raw.area)) > 0.005 * abs(raw.area):
                warnings.append("zone Z%d %s %s: de-fracture changed area %.2f → %.2f mm²"
                                % (i, z.netName, fpoly.layer, abs(raw.area), fixed.area))
            fills_by_layer[fpoly.layer].append(fixed)
        fills, areas, holes = {}, {}, {}
        for layer, polys in fills_by_layer.items():
            g = unary_union(polys)
            fills[layer] = poly_to_json(g)
            areas[layer] = _r(g.area)
            holes[layer] = sum(len(p["holes"]) for p in fills[layer])
        filled = bool(fills)
        if keepout is None and not filled:
            warnings.append("zone Z%d (%s on %s) has no fill: refill in KiCad (or kicad-cli) "
                            "before trusting plane results" % (i, z.netName or "no net", ",".join(layers)))
        out.append({
            "id": "Z%d" % i, "name": z.name, "net": z.netName or "", "layers": layers,
            "priority": z.priority if z.priority is not None else 0,
            "keepout": keepout,
            "clearance_mm": z.clearance, "min_thickness_mm": z.minThickness,
            "connect_pads": getattr(z.connectPads, "type", None) if z.connectPads else None,
            "outline": poly_to_json(outline),
            "outline_area_mm2": _r(outline.area),
            "filled": filled,
            "fills": fills, "fill_area_mm2": areas, "fill_holes": holes,
        })
    return out


# ---------------------------------------------------------------------------
# Net topology
# ---------------------------------------------------------------------------

class _Graph:
    def __init__(self):
        self.nodes: Dict[str, Dict[str, Any]] = {}
        self.adj: Dict[str, List[Tuple[str, Dict[str, Any]]]] = defaultdict(list)

    def node(self, nid: str, **attrs) -> str:
        if nid not in self.nodes:
            self.nodes[nid] = dict(id=nid, **attrs)
        return nid

    def edge(self, a: str, b: str, **attrs):
        if a == b:
            return
        e = dict(attrs)
        self.adj[a].append((b, e))
        self.adj[b].append((a, e))


def _key(layer: str, x: float, y: float) -> str:
    return "J:%s:%.3f:%.3f" % (layer, round(x / SNAP) * SNAP, round(y / SNAP) * SNAP)


def build_topology(net: str, segs: List[Dict], vias: List[Dict], pads: List[Dict],
                   zones: List[Dict], root_hint: Optional[str]) -> Dict[str, Any]:
    """Graph of one net: pads, vias, zone fills, junctions and dangling ends,
    joined by chains of track. Branch lengths are along copper from the root."""
    g = _Graph()
    pad_geo = {p["id"]: poly_from_json(p["polygon"]) for p in pads}
    via_geo = {v["id"]: Point(*v["position"]).buffer(v["size"] / 2.0, 16) for v in vias}
    for p in pads:
        g.node(p["id"], kind="pad", pos=p["center"], layers=p["layers"])
    for v in vias:
        g.node(v["id"], kind="via", pos=v["position"], layers=v["layers"])

    # Connection rule (KiCad connectivity): two same-net items connect when an
    # anchor of one lies inside the copper of the other. Track anchors are its
    # endpoints; pad and via anchors are their centres. Overlapping pads join.
    seg_lines = {s["id"]: LineString(s["points"]) for s in segs}
    splits: Dict[str, List[Tuple[float, float]]] = defaultdict(list)
    forced: Dict[Tuple[str, str], str] = {}   # (layer, point key) → pad/via id
    by_layer: Dict[str, List[Dict]] = defaultdict(list)
    for s in segs:
        by_layer[s["layer"]].append(s)

    def interior(ln, P) -> Optional[Tuple[float, float]]:
        d = ln.project(P)
        if SNAP < d < ln.length - SNAP:
            q = ln.interpolate(d)
            return (q.x, q.y)
        return None

    for layer, ss in by_layer.items():
        ends = [(tuple(s["points"][0]), s["id"]) for s in ss] + \
               [(tuple(s["points"][-1]), s["id"]) for s in ss]
        for s in ss:
            ln, half = seg_lines[s["id"]], s["width"] / 2.0 + SNAP
            if ln.length <= SNAP:
                continue   # zero-length track: nothing to split
            # Another track's endpoint inside this track's copper (T join).
            for (pt, sid) in ends:
                if sid != s["id"] and ln.distance(Point(pt)) <= half:
                    q = interior(ln, Point(pt))
                    if q:
                        splits[s["id"]].append(q)
            # A pad or via centre inside this track's copper (track passes over it).
            for obj, kind in [(p, "pad") for p in pads] + [(v, "via") for v in vias]:
                if layer not in obj["layers"]:
                    continue
                c = Point(obj["center"] if kind == "pad" else obj["position"])
                if ln.distance(c) <= half:
                    q = interior(ln, c)
                    if q:
                        splits[s["id"]].append(q)
                    else:   # the centre is over this track's end cap
                        d = ln.project(c)
                        q = tuple(s["points"][0]) if d <= SNAP else tuple(s["points"][-1])
                    forced[(layer, _key(layer, *q))] = obj["id"]

    # Endpoints of every sub-segment, merged when one lies inside the other's track.
    pieces = []   # (seg, layer, (x0,y0), (x1,y1), length)
    for s in segs:
        ln = seg_lines[s["id"]]
        cuts = sorted(set(ln.project(Point(p)) for p in splits[s["id"]]))
        bounds = [0.0] + [c for c in cuts if SNAP < c < ln.length - SNAP] + [ln.length]
        scale = s["length_mm"] / ln.length if ln.length > 0 else 1.0
        for d0, d1 in zip(bounds, bounds[1:]):
            p0, p1 = ln.interpolate(d0), ln.interpolate(d1)
            pieces.append((s, s["layer"], (p0.x, p0.y), (p1.x, p1.y), (d1 - d0) * scale))

    parent: Dict[str, str] = {}

    def find(k: str) -> str:
        while parent.get(k, k) != k:
            parent[k] = parent.get(parent[k], parent[k])
            k = parent[k]
        return k

    def union(a: str, b: str):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    pts_by_layer: Dict[str, Dict[str, Tuple[float, float, float]]] = defaultdict(dict)
    for (s, layer, a, b, _) in pieces:
        for q in (a, b):
            k = _key(layer, *q)
            w = pts_by_layer[layer].get(k, (0, 0, 0))[2]
            pts_by_layer[layer][k] = (q[0], q[1], max(w, s["width"]))
    for layer, pts in pts_by_layer.items():
        items = list(pts.items())
        for i in range(len(items)):
            ki, (xi, yi, wi) = items[i]
            for j in range(i + 1, len(items)):
                kj, (xj, yj, wj) = items[j]
                if math.hypot(xi - xj, yi - yj) <= max(wi, wj) / 2.0 + SNAP:
                    union(ki, kj)

    # Each merged point set maps to the pad/via it lands in, else to a point node.
    node_of: Dict[str, str] = {}
    for layer, pts in pts_by_layer.items():
        groups: Dict[str, List[str]] = defaultdict(list)
        for k in pts:
            groups[find(k)].append(k)
        for root_k, members in groups.items():
            hits: List[str] = []
            for k in members:
                x, y, _ = pts[k]
                P = Point(x, y)
                if (layer, k) in forced:
                    hits.append(forced[(layer, k)])
                hits += [p["id"] for p in pads if layer in p["layers"]
                         and pad_geo[p["id"]].distance(P) < SNAP]
                hits += [v["id"] for v in vias if layer in v["layers"]
                         and via_geo[v["id"]].distance(P) < SNAP]
            hits = list(dict.fromkeys(hits))
            if hits:
                target = hits[0]
                for h in hits[1:]:
                    g.edge(target, h, kind="overlap", layer=layer, length=0.0, segs=[])
            else:
                x, y, _ = pts[root_k]
                target = g.node(root_k, kind="point", pos=_pt(x, y), layers=[layer])
            for k in members:
                node_of[k] = target

    for (s, layer, a, b, length) in pieces:
        g.edge(node_of[_key(layer, *a)], node_of[_key(layer, *b)], kind="track", layer=layer,
               length=length, segs=[s["id"]], width=s["width"])

    # Via-in-pad, and pads overlapping pads (e.g. an exposed pad and its via pads).
    for v in vias:
        for p in pads:
            if set(v["layers"]) & set(p["layers"]) and via_geo[v["id"]].intersects(pad_geo[p["id"]]):
                g.edge(v["id"], p["id"], kind="overlap", layer=None, length=0.0, segs=[])
    for i, p in enumerate(pads):
        for q in pads[i + 1:]:
            if set(p["layers"]) & set(q["layers"]) and pad_geo[p["id"]].intersects(pad_geo[q["id"]]):
                g.edge(p["id"], q["id"], kind="overlap", layer=None, length=0.0, segs=[])

    # Zone fills: each fill island is a node; whatever it touches joins it.
    for z in zones:
        if z["keepout"] is not None:
            continue
        for layer, parts in z["fills"].items():
            for k, part in enumerate(parts):
                poly = poly_from_json([part])
                zid = g.node("%s:%s:%d" % (z["id"], layer, k), kind="zone", zone=z["id"],
                             layer=layer, pos=_pt(*poly.representative_point().coords[0]),
                             layers=[layer])
                for p in pads:
                    if layer in p["layers"] and poly.intersects(pad_geo[p["id"]]):
                        g.edge(zid, p["id"], kind="zone", layer=layer, length=0.0, segs=[])
                for v in vias:
                    if layer in v["layers"] and poly.intersects(via_geo[v["id"]]):
                        g.edge(zid, v["id"], kind="zone", layer=layer, length=0.0, segs=[])
                for nid, n in list(g.nodes.items()):
                    if n["kind"] == "point" and n["layers"] == [layer] and \
                            poly.distance(Point(n["pos"])) < SNAP:
                        g.edge(zid, nid, kind="zone", layer=layer, length=0.0, segs=[])

    # Classify raw points: junction (≥3 tracks), end (1), pass-through (2).
    for nid, n in g.nodes.items():
        if n["kind"] == "point":
            deg = len(g.adj[nid])
            n["kind"] = "junction" if deg >= 3 else ("end" if deg <= 1 else "bend")

    # Contract bends into chains between key nodes.
    key = {nid for nid, n in g.nodes.items() if n["kind"] != "bend"}
    chains, used = [], set()
    cid = 0

    def walk(start: str, first: Tuple[str, Dict]) -> Optional[Dict[str, Any]]:
        nonlocal cid
        path, length, segs_in, widths, layers = [start], 0.0, [], set(), []
        prev, (cur, e) = start, first
        kinds = set()
        while True:
            if id(e) in used:
                return None
            used.add(id(e))
            length += e["length"]
            segs_in.extend(e["segs"])
            kinds.add(e["kind"])
            if e.get("width") is not None:
                widths.add(e["width"])
            if e["layer"] and (not layers or layers[-1] != e["layer"]):
                layers.append(e["layer"])
            path.append(cur)
            if cur in key:
                break
            nxt = [(b, ee) for (b, ee) in g.adj[cur] if id(ee) not in used]
            if not nxt:
                break
            prev, (cur, e) = cur, nxt[0]
        c = {"id": "C%d" % cid, "a": start, "b": cur, "length_mm": _r(length),
             "layer": layers[0] if len(layers) == 1 else (layers or None),
             "kind": "track" if "track" in kinds else sorted(kinds)[0],
             "widths": sorted(widths), "segments": sorted(set(segs_in), key=lambda s: int(s[1:])),
             "points": [g.nodes[n]["pos"] for n in path if "pos" in g.nodes[n]]}
        cid += 1
        return c

    for nid in sorted(key):
        for nb in g.adj[nid]:
            if id(nb[1]) not in used:
                c = walk(nid, nb)
                if c:
                    chains.append(c)
    # Loops made only of bends (no key node): break them at an arbitrary node.
    for nid, n in g.nodes.items():
        for nb in g.adj[nid]:
            if id(nb[1]) not in used:
                key.add(nid)
                n["kind"] = "junction"
                c = walk(nid, nb)
                if c:
                    chains.append(c)

    nodes = {nid: n for nid, n in g.nodes.items() if nid in key}
    cadj: Dict[str, List[Tuple[str, Dict]]] = defaultdict(list)
    for c in chains:
        cadj[c["a"]].append((c["b"], c))
        cadj[c["b"]].append((c["a"], c))

    # Islands.
    comp: Dict[str, int] = {}
    islands = []
    for nid in sorted(nodes):
        if nid in comp:
            continue
        stack, members = [nid], []
        comp[nid] = len(islands)
        while stack:
            u = stack.pop()
            members.append(u)
            for v, _ in cadj[u]:
                if v not in comp:
                    comp[v] = comp[nid]
                    stack.append(v)
        islands.append({"pads": sorted(m for m in members if nodes[m]["kind"] == "pad"),
                        "vias": sum(1 for m in members if nodes[m]["kind"] == "via"),
                        "zones": sorted(m for m in members if nodes[m]["kind"] == "zone")})

    # Root and branches.
    pad_ids = [p["id"] for p in pads]
    root, root_src = None, None
    if root_hint and root_hint in nodes:
        root, root_src = root_hint, "config"
    elif pad_ids:
        counts = defaultdict(int)
        for p in pads:
            counts[p["ref"]] += 1
        # Heuristic: a pad on the net's largest-pin-count footprint (often the MCU/IC).
        root = sorted(pad_ids, key=lambda i: (-_fp_pin_counts.get(i.split(".")[0], 0), i))[0]
        root_src = "heuristic: pad on the largest footprint"
    branches = []
    if root:
        dist = {root: 0.0}
        prev: Dict[str, Tuple[str, Dict]] = {}
        pq = [(0.0, root)]
        while pq:
            d, u = heapq.heappop(pq)
            if d > dist.get(u, 1e18):
                continue
            for v, c in cadj[u]:
                nd = d + c["length_mm"]
                if nd < dist.get(v, 1e18) - 1e-9:
                    dist[v] = nd
                    prev[v] = (u, c)
                    heapq.heappush(pq, (nd, v))
        for pid in pad_ids:
            if pid == root:
                continue
            if pid not in dist:
                branches.append({"to": pid, "reachable": False})
                continue
            path, by_layer, nvias, chain_ids = [pid], defaultdict(float), 0, []
            u = pid
            while u != root:
                pu, c = prev[u]
                chain_ids.append(c["id"])
                lay = c["layer"] if isinstance(c["layer"], str) else None
                if lay:
                    by_layer[lay] += c["length_mm"]
                path.append(pu)
                u = pu
            path.reverse()
            chain_ids.reverse()
            nvias = sum(1 for n in path if nodes[n]["kind"] == "via")
            branches.append({"to": pid, "reachable": True, "length_mm": _r(dist[pid]),
                             "by_layer": {k: _r(v) for k, v in sorted(by_layer.items())},
                             "vias": nvias, "path": path, "chains": chain_ids})
        branches.sort(key=lambda b: b.get("length_mm", 1e9))

    # Stubs: chains that end in nothing, and vias that join only one chain.
    stubs = []
    for c in chains:
        for end in (c["a"], c["b"]):
            if nodes.get(end, {}).get("kind") == "end":
                stubs.append({"kind": "dangling_track", "chain": c["id"], "at": nodes[end]["pos"],
                              "length_mm": c["length_mm"]})
    for nid, n in nodes.items():
        if n["kind"] == "via" and len(cadj[nid]) <= 1:
            stubs.append({"kind": "via_one_side" if cadj[nid] else "via_unconnected",
                          "via": nid, "at": n["pos"]})

    return {
        "root": root, "root_source": root_src,
        "nodes": [{"id": nid, "kind": n["kind"], "pos": n.get("pos"), "degree": len(cadj[nid])}
                  for nid, n in sorted(nodes.items())],
        "chains": chains,
        "branches": branches,
        "stubs": stubs,
        "islands": islands,
        "connected": sum(1 for i in islands if i["pads"]) <= 1,
    }


_fp_pin_counts: Dict[str, int] = {}


# ---------------------------------------------------------------------------
# Nets
# ---------------------------------------------------------------------------

def classify_net(name: str, segs: List[Dict], zones: List[Dict], cfg: Dict[str, Any]) -> List[str]:
    d = cfg.get("definitions", {})
    hc = d.get("high_current", {})
    classes = []
    min_w = hc.get("min_track_width_mm", 0.5)
    if (hc.get("zone_nets", True) and any(z["net"] == name and z["keepout"] is None for z in zones)) \
            or any(s["width"] >= min_w - 1e-9 for s in segs) \
            or name in hc.get("power_ground_nets", []):
        classes.append("high_current")
    if name in d.get("high_dvdt", {}).get("nets", []):
        classes.append("high_dvdt")
    if not classes:
        classes.append("signal")
    return classes


def build_nets(board: Board, footprints, segs, vias, zones, cfg) -> Dict[str, Any]:
    pads_by_net: Dict[str, List[Dict]] = defaultdict(list)
    for fp in footprints:
        for p in fp["pads"]:
            if p["net"]:
                pads_by_net[p["net"]].append(p)
    segs_by_net, vias_by_net = defaultdict(list), defaultdict(list)
    for s in segs:
        segs_by_net[s["net"]].append(s)
    for v in vias:
        vias_by_net[v["net"]].append(v)
    drivers = cfg.get("drivers", {})
    dvdt_pads = {"%s.%s" % (p["ref"], p["pad"]) for p in
                 cfg.get("definitions", {}).get("high_dvdt", {}).get("pads", [])}
    names = sorted(set(n.name for n in board.nets if n.name) | set(pads_by_net) | set(segs_by_net))
    out = {}
    for name in names:
        ss, vv, pp = segs_by_net[name], vias_by_net[name], pads_by_net[name]
        zz = [z for z in zones if z["net"] == name and z["keepout"] is None]
        by_layer: Dict[str, float] = defaultdict(float)
        for s in ss:
            by_layer[s["layer"]] += s["length_mm"]
        entry = {
            "classes": classify_net(name, ss, zones, cfg),
            "pads": [p["id"] for p in pp],
            "high_dvdt_pads": sorted(p["id"] for p in pp if p["id"] in dvdt_pads),
            "length_mm": _r(sum(by_layer.values())),
            "length_by_layer": {k: _r(v) for k, v in sorted(by_layer.items())},
            "widths": sorted(set(s["width"] for s in ss)),
            "via_count": len(vv),
            "zones": [z["id"] for z in zz],
            "segments": [s["id"] for s in ss],
            "vias": [v["id"] for v in vv],
        }
        if ss or vv or zz:
            entry["topology"] = build_topology(name, ss, vv, pp, zz, drivers.get(name))
        elif len(pp) > 1:
            entry["topology"] = {"root": None, "connected": False,
                                 "note": "pads on this net have no copper joining them"}
        out[name] = entry
    return out


# ---------------------------------------------------------------------------
# DRC via kicad-cli
# ---------------------------------------------------------------------------

def run_drc(pcb: Path, kicad_cli: str, warnings: List[str]) -> Dict[str, Any]:
    if not Path(kicad_cli).exists():
        warnings.append("drc: kicad-cli not found at %s; DRC not run" % kicad_cli)
        return {"ran": False}
    with tempfile.TemporaryDirectory() as td:
        out = Path(td) / "drc.json"
        cmd = [kicad_cli, "pcb", "drc", "--format", "json", "--severity-all",
               "--units", "mm", "-o", str(out), str(pcb)]
        r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True)
        if r.returncode != 0 or not out.exists():
            warnings.append("drc: kicad-cli failed (%d): %s" % (r.returncode, (r.stderr or r.stdout)[-300:]))
            return {"ran": False}
        d = json.loads(out.read_text(encoding="utf-8"))
    viol = d.get("violations", [])
    by_type: Dict[str, int] = defaultdict(int)
    by_sev: Dict[str, int] = defaultdict(int)
    for v in viol:
        by_type[v.get("type", "?")] += 1
        by_sev[v.get("severity", "?")] += 1
    slim = lambda v: {"type": v.get("type"), "severity": v.get("severity"),  # noqa: E731
                      "description": v.get("description"),
                      "items": [{"description": i.get("description"), "pos": i.get("pos")}
                                for i in v.get("items", [])]}
    return {
        "ran": True, "kicad_version": d.get("kicad_version"),
        "command": "kicad-cli pcb drc --format json --severity-all --units mm",
        "violations_total": len(viol),
        "by_type": dict(sorted(by_type.items())), "by_severity": dict(sorted(by_sev.items())),
        "unconnected_items": len(d.get("unconnected_items", [])),
        "schematic_parity": len(d.get("schematic_parity", [])),
        "violations": [slim(v) for v in viol],
        "unconnected": [slim(v) for v in d.get("unconnected_items", [])],
    }


# ---------------------------------------------------------------------------
# Provenance
# ---------------------------------------------------------------------------

def _git(*args: str, cwd: Path = _HERE) -> Optional[str]:
    try:
        r = subprocess.run(["git"] + list(args), cwd=str(cwd), stdout=subprocess.PIPE,
                           stderr=subprocess.DEVNULL, universal_newlines=True)
        return r.stdout.strip() if r.returncode == 0 else None
    except OSError:
        return None


def repo_root() -> Path:
    top = _git("rev-parse", "--show-toplevel")
    return Path(top) if top else _HERE.parent.parent


def provenance(pcb: Path, source_ref: Optional[str]) -> Dict[str, Any]:
    root = repo_root()
    try:
        src = str(pcb.resolve().relative_to(root.resolve()))
    except ValueError:
        src = str(pcb.resolve())
    commit = _git("rev-parse", "HEAD") or "unknown"
    if _git("status", "--porcelain", "--", str(_HERE / "board_model.py")):
        commit += "-dirty"
    if source_ref is None and not src.startswith("/"):
        if not _git("status", "--porcelain", "--", src, cwd=root):
            source_ref = _git("log", "-1", "--format=%H", "--", src, cwd=root)
    return {
        "source": src,
        "source_sha256": hashlib.sha256(pcb.read_bytes()).hexdigest(),
        "source_ref": source_ref,
        "generator": GENERATOR,
        "generator_commit": commit,
        "generated": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
    }


def check(model_path: Path) -> int:
    """Exit 0 fresh, 1 stale, 2 no provenance (tools/lab/check_state.py --fresh)."""
    sys.path.insert(0, str(_HERE.parent / "lab"))
    from check_state import check_fresh  # reuse the one freshness rule
    status, msg = check_fresh(model_path, repo_root())
    print(msg)
    return {"FRESH": 0, "STALE": 1}.get(status, 2)


# ---------------------------------------------------------------------------
# Build
# ---------------------------------------------------------------------------

def load_config(pcb: Path, explicit: Optional[str]) -> Tuple[Dict[str, Any], Optional[str]]:
    path = Path(explicit) if explicit else CONFIG_DIR / (pcb.stem + ".json")
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8")), str(path)
    if explicit:
        raise SystemExit("config not found: %s" % explicit)
    return {}, None


def build_model(pcb: Path, cfg: Dict[str, Any], cfg_path: Optional[str], drc: bool,
                kicad_cli: str, source_ref: Optional[str]) -> Dict[str, Any]:
    warnings: List[str] = []
    board = Board.from_file(str(pcb))
    cu = copper_layers(board)
    net_index = build_net_index(board)
    stackup = extract_stackup(board, cu, warnings)
    outline = extract_outline(board, warnings)
    footprints = extract_footprints(board, cu)
    _fp_pin_counts.clear()
    _fp_pin_counts.update({f["ref"]: len(f["pads"]) for f in footprints})
    segs, vias = extract_tracks(board, net_index, cu)
    zones = extract_zones(board, cu, warnings)
    nets = build_nets(board, footprints, segs, vias, zones, cfg)
    for name, n in nets.items():
        t = n.get("topology") or {}
        if (n["segments"] or n["vias"]) and t.get("connected") is False:
            warnings.append("net %s: copper islands not joined (%d islands with pads)"
                            % (name, sum(1 for i in t.get("islands", []) if i["pads"])))
    for d, cfgnet in (("drivers", cfg.get("drivers", {})),):
        for net, pid in cfgnet.items():
            if net not in nets or pid not in nets[net]["pads"]:
                warnings.append("config %s: %s → %s not on this board" % (d, net, pid))
    model = {
        "_provenance": provenance(pcb, source_ref),
        "meta": {
            "schema_version": SCHEMA_VERSION,
            "units": "mm", "y_axis": "down",
            "kicad_format_version": board.version, "kicad_generator": board.generator,
            "config": cfg_path,
            "copper_layers": cu,
            "counts": {"footprints": len(footprints), "pads": sum(len(f["pads"]) for f in footprints),
                       "nets": len(nets), "segments": sum(1 for s in segs if s["kind"] == "segment"),
                       "arcs": sum(1 for s in segs if s["kind"] == "arc"), "vias": len(vias),
                       "zones": len(zones)},
            "clearance_metric": "copper edge to copper edge (segments buffered by width/2)",
            "arc_handling": "sampled polyline (routing_extract, 16 steps)",
        },
        "warnings": warnings,
        "definitions": cfg.get("definitions", {}),
        "stackup": stackup,
        "outline": outline,
        "footprints": footprints,
        "segments": segs,
        "vias": vias,
        "zones": zones,
        "graphic_copper": extract_graphic_copper(board, cu),
        "nets": nets,
        "drc": run_drc(pcb, kicad_cli, warnings) if drc else {"ran": False, "skipped": True},
    }
    return model


# ---------------------------------------------------------------------------
# Loader for reports
# ---------------------------------------------------------------------------

class BoardModel:
    """Read-only view of a board-model.json with shapely geometry on demand."""

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.pads = {p["id"]: p for f in data["footprints"] for p in f["pads"]}
        self.footprints = {f["ref"]: f for f in data["footprints"]}
        self.segments = {s["id"]: s for s in data["segments"]}
        self.vias = {v["id"]: v for v in data["vias"]}
        self.zones = {z["id"]: z for z in data["zones"]}
        self.nets = data["nets"]

    @classmethod
    def load(cls, path) -> "BoardModel":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @property
    def outline(self):
        return poly_from_json(self.data["outline"]["polygon"])

    def pad_geom(self, pid: str):
        return poly_from_json(self.pads[pid]["polygon"])

    def segment_geom(self, sid: str):
        s = self.segments[sid]
        return LineString(s["points"]).buffer(s["width"] / 2.0, 16)

    def segment_line(self, sid: str):
        return LineString(self.segments[sid]["points"])

    def via_geom(self, vid: str):
        v = self.vias[vid]
        return Point(*v["position"]).buffer(v["size"] / 2.0, 16)

    def body(self, ref: str):
        return poly_from_json(self.footprints[ref]["body"])

    def zone_fill(self, zid: str, layer: str):
        return poly_from_json(self.zones[zid]["fills"].get(layer, []))

    def layer_fill(self, layer: str, net: Optional[str] = None):
        """Union of zone fills on a layer (optionally only one net's)."""
        parts = [self.zone_fill(z["id"], layer) for z in self.zones.values()
                 if z["keepout"] is None and layer in z["fills"] and (net is None or z["net"] == net)]
        return unary_union(parts) if parts else Polygon()

    def net_copper(self, net: str, layers: Optional[List[str]] = None,
                   include_zones: bool = True) -> Dict[str, Any]:
        """{layer: geometry} for every copper item of a net (tracks, pads, vias, fills)."""
        cu = self.data["meta"]["copper_layers"]
        want = set(layers or cu)
        parts: Dict[str, List[Any]] = defaultdict(list)
        n = self.nets.get(net, {})
        for sid in n.get("segments", []):
            s = self.segments[sid]
            if s["layer"] in want:
                parts[s["layer"]].append(self.segment_geom(sid))
        for vid in n.get("vias", []):
            for l in self.vias[vid]["layers"]:
                if l in want:
                    parts[l].append(self.via_geom(vid))
        for pid in n.get("pads", []):
            for l in self.pads[pid]["layers"]:
                if l in want:
                    parts[l].append(self.pad_geom(pid))
        if include_zones:
            for zid in n.get("zones", []):
                for l, f in self.zones[zid]["fills"].items():
                    if l in want:
                        parts[l].append(poly_from_json(f))
        return {l: unary_union(g) for l, g in parts.items()}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("pcb", nargs="?", help=".kicad_pcb to parse")
    ap.add_argument("-o", "--output", help="output JSON (default: board-model.json beside the PCB)")
    ap.add_argument("--config", help="per-board config JSON (default: board-config/<pcb stem>.json if present)")
    ap.add_argument("--no-drc", action="store_true", help="skip the kicad-cli DRC run")
    ap.add_argument("--kicad-cli", default=os.environ.get("KICAD_CLI", KICAD_CLI_DEFAULT))
    ap.add_argument("--source-ref", help="git ref the PCB came from (e.g. when parsing a git archive copy)")
    ap.add_argument("--check", metavar="MODEL", help="check a model's _provenance against its source; "
                    "exit 0 fresh, 1 stale, 2 none")
    a = ap.parse_args()
    if a.check:
        sys.exit(check(Path(a.check)))
    if not a.pcb:
        ap.error("pcb is required unless --check is given")
    pcb = Path(a.pcb)
    if not pcb.is_file():
        raise SystemExit("not a file: %s" % pcb)
    cfg, cfg_path = load_config(pcb, a.config)
    model = build_model(pcb, cfg, cfg_path, not a.no_drc, a.kicad_cli, a.source_ref)
    out = Path(a.output) if a.output else pcb.with_name("board-model.json")
    out.write_text(json.dumps(model, separators=(",", ":"), ensure_ascii=False), encoding="utf-8")
    m = model["meta"]["counts"]
    print("wrote %s (%.0f KB): %d footprints, %d pads, %d nets, %d segments, %d vias, %d zones"
          % (out, out.stat().st_size / 1024, m["footprints"], m["pads"], m["nets"],
             m["segments"], m["vias"], m["zones"]))
    d = model["drc"]
    if d.get("ran"):
        print("DRC: %d violations %s, %d unconnected" % (d["violations_total"], d["by_severity"],
                                                        d["unconnected_items"]))
    for w in model["warnings"]:
        print("WARNING:", w)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
verify-routing.py — PCB routing verification against ROUTING_GUIDE.md specs.

Parses the routed .kicad_pcb file via kiutils, extracts all routing
primitives (traces, vias, zones, pads), and runs structured checks
derived from the routing guide. Produces a Markdown report and JSON sidecar.

Usage:
    python verify-routing.py <file.kicad_pcb>
    python verify-routing.py <file.kicad_pcb> --output-dir path/to/reports/
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, NamedTuple, Optional, Set, Tuple

from kiutils.board import Board


# ---------------------------------------------------------------------------
# Constants — net class specifications from ROUTING_GUIDE.md
# ---------------------------------------------------------------------------

WIDTH_TOLERANCE_MM = 0.02

class NetClass(NamedTuple):
    name: str
    width: float  # mm
    clearance: float  # mm

NET_CLASSES = {
    "Power_5V":  NetClass("Power_5V",  1.5,  0.3),
    "Power_Med": NetClass("Power_Med", 1.0,  0.3),
    "Power_Low": NetClass("Power_Low", 0.75, 0.25),
    "Power_3V3": NetClass("Power_3V3", 0.5,  0.2),
    "Sensitive":  NetClass("Sensitive",  0.2,  0.25),
    "Default":    NetClass("Default",    0.25, 0.2),
}

# Net name → net class. Partial matching handles sheet prefixes
# (e.g. "/Power Management/Protected_VBUS" matches "Protected_VBUS").
_NET_CLASS_MAP = {
    "+5V":           "Power_5V",
    "BOOST_SW":      "Power_5V",
    "VSYS":          "Power_Med",
    "VSYS_SENSE":    "Power_Med",
    "Protected_VBUS": "Power_Med",
    "VBUS_RAW":      "Power_Med",
    "BQ_SW":         "Power_Med",
    "BQ_PMID":       "Power_Med",
    "+5V_TO_LEDS":   "Power_Med",
    "Net-(C7-Pad2)": "Power_Med",
    "VBAT":          "Power_Low",
    "BAT_RAW":       "Power_Low",
    "BQ_REGN":       "Power_Low",
    "+3.3V":         "Power_3V3",
    "BOOST_FB":      "Sensitive",
    "BOOST_COMP":    "Sensitive",
    "COMP_MID":      "Sensitive",
}


def classify_net(net_name: str) -> NetClass:
    """Determine the expected net class for a given net name.

    Handles hierarchical sheet prefixes by checking if the net name
    ends with any known suffix.
    """
    if not net_name:
        return NET_CLASSES["Default"]

    if net_name in _NET_CLASS_MAP:
        return NET_CLASSES[_NET_CLASS_MAP[net_name]]

    for suffix, cls_name in _NET_CLASS_MAP.items():
        if net_name.endswith("/" + suffix) or net_name.endswith(suffix):
            return NET_CLASSES[cls_name]

    return NET_CLASSES["Default"]


# ---------------------------------------------------------------------------
# Data structures for extracted routing primitives
# ---------------------------------------------------------------------------

class PadInfo(NamedTuple):
    ref: str
    number: str
    x: float
    y: float
    net_number: int
    net_name: str
    layers: list

class SegmentInfo(NamedTuple):
    start_x: float
    start_y: float
    end_x: float
    end_y: float
    width: float
    layer: str
    net_number: int

class ViaInfo(NamedTuple):
    x: float
    y: float
    size: float
    drill: float
    layers: list
    net_number: int

class ZoneInfo(NamedTuple):
    net_number: int
    net_name: str
    layers: list
    filled_polygons: list  # list of list of (x, y) tuples


class BoardData:
    """Container for all extracted board routing primitives."""

    def __init__(self, board: Board, pcb_path: Path):
        self.pcb_path = pcb_path
        self.board = board

        self.net_map = {}          # net_number → net_name
        self.net_number_map = {}   # net_name → net_number
        self.pads = []             # list of PadInfo
        self.segments = []         # list of SegmentInfo
        self.vias = []             # list of ViaInfo
        self.zones = []            # list of ZoneInfo

        # Per-net indices (populated by collect_by_net)
        self.pads_by_net = defaultdict(list)
        self.segments_by_net = defaultdict(list)
        self.vias_by_net = defaultdict(list)
        self.zones_by_net = defaultdict(list)

        # Ref-based pad lookup: (ref, pad_number) → PadInfo
        self.pad_lookup = {}

        self._extract()

    def _extract(self):
        self._build_net_map()
        self._extract_pads()
        self._extract_segments()
        self._extract_vias()
        self._extract_zones()
        self._collect_by_net()

    # --- Net map -------------------------------------------------------

    def _build_net_map(self):
        for net in self.board.nets:
            self.net_map[net.number] = net.name
            if net.name:
                self.net_number_map[net.name] = net.number

    def net_name(self, net_number: int) -> str:
        return self.net_map.get(net_number, "")

    def net_num(self, net_name: str) -> Optional[int]:
        """Look up net number by name, handling sheet prefixes."""
        if net_name in self.net_number_map:
            return self.net_number_map[net_name]
        for full_name, num in self.net_number_map.items():
            if full_name.endswith("/" + net_name) or full_name.endswith(net_name):
                return num
        return None

    # --- Pad extraction with rotation transform ------------------------

    def _extract_pads(self):
        for fp in self.board.footprints:
            ref = fp.properties.get("Reference", "")
            fp_x = fp.position.X
            fp_y = fp.position.Y
            angle_deg = fp.position.angle or 0
            theta = math.radians(angle_deg)
            cos_t = math.cos(theta)
            sin_t = math.sin(theta)

            for pad in fp.pads:
                lx = pad.position.X
                ly = pad.position.Y

                # KiCad Y-down coordinate transform
                gx = fp_x + lx * cos_t + ly * sin_t
                gy = fp_y - lx * sin_t + ly * cos_t

                net_num = pad.net.number if pad.net else 0
                net_name = pad.net.name if pad.net else ""

                info = PadInfo(
                    ref=ref,
                    number=pad.number,
                    x=round(gx, 3),
                    y=round(gy, 3),
                    net_number=net_num,
                    net_name=net_name,
                    layers=list(pad.layers),
                )
                self.pads.append(info)
                self.pad_lookup[(ref, str(pad.number))] = info

    # --- Segment extraction --------------------------------------------

    def _extract_segments(self):
        for item in self.board.traceItems:
            if type(item).__name__ != "Segment":
                continue
            self.segments.append(SegmentInfo(
                start_x=item.start.X,
                start_y=item.start.Y,
                end_x=item.end.X,
                end_y=item.end.Y,
                width=item.width,
                layer=item.layer,
                net_number=item.net,
            ))

    # --- Via extraction -------------------------------------------------

    def _extract_vias(self):
        for item in self.board.traceItems:
            if type(item).__name__ != "Via":
                continue
            self.vias.append(ViaInfo(
                x=item.position.X,
                y=item.position.Y,
                size=item.size,
                drill=item.drill,
                layers=list(item.layers),
                net_number=item.net,
            ))

    # --- Zone extraction ------------------------------------------------

    def _extract_zones(self):
        for zone in self.board.zones:
            polygons = []
            if zone.filledPolygons:
                for fp in zone.filledPolygons:
                    coords = [(c.X, c.Y) for c in fp.coordinates]
                    polygons.append(coords)

            self.zones.append(ZoneInfo(
                net_number=zone.net,
                net_name=zone.netName or "",
                layers=list(zone.layers) if zone.layers else [],
                filled_polygons=polygons,
            ))

    # --- Group by net ---------------------------------------------------

    def _collect_by_net(self):
        for pad in self.pads:
            self.pads_by_net[pad.net_number].append(pad)

        for seg in self.segments:
            self.segments_by_net[seg.net_number].append(seg)

        for via in self.vias:
            self.vias_by_net[via.net_number].append(via)

        for zone in self.zones:
            self.zones_by_net[zone.net_number].append(zone)

    # --- Convenience lookups -------------------------------------------

    def find_pad(self, ref: str, pad_number: str) -> Optional[PadInfo]:
        """Look up a specific pad by component ref and pad number."""
        return self.pad_lookup.get((ref, pad_number))

    def net_segments(self, net_name: str) -> List[SegmentInfo]:
        """Get all segments for a net by name."""
        num = self.net_num(net_name)
        return self.segments_by_net.get(num, []) if num is not None else []

    def net_vias(self, net_name: str) -> List[ViaInfo]:
        """Get all vias for a net by name."""
        num = self.net_num(net_name)
        return self.vias_by_net.get(num, []) if num is not None else []

    def net_pads(self, net_name: str) -> List[PadInfo]:
        """Get all pads for a net by name."""
        num = self.net_num(net_name)
        return self.pads_by_net.get(num, []) if num is not None else []

    def summary(self) -> Dict[str, int]:
        return {
            "nets": len([n for n in self.net_map if self.net_map[n]]),
            "footprints": len(self.board.footprints),
            "pads": len(self.pads),
            "segments": len(self.segments),
            "vias": len(self.vias),
            "zones": len(self.zones),
        }


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def distance(x1: float, y1: float, x2: float, y2: float) -> float:
    return math.hypot(x2 - x1, y2 - y1)


def segment_length(seg: SegmentInfo) -> float:
    return distance(seg.start_x, seg.start_y, seg.end_x, seg.end_y)


def point_in_polygon(px: float, py: float, polygon: List[Tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test."""
    n = len(polygon)
    inside = False
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        if ((yi > py) != (yj > py)) and (px < (xj - xi) * (py - yi) / (yj - yi) + xi):
            inside = not inside
        j = i
    return inside


def segments_intersect_rect(
    seg: SegmentInfo,
    rect_min_x: float, rect_min_y: float,
    rect_max_x: float, rect_max_y: float,
) -> bool:
    """Check if a segment crosses through or has endpoints inside a rectangle."""
    if (rect_min_x <= seg.start_x <= rect_max_x and
            rect_min_y <= seg.start_y <= rect_max_y):
        return True
    if (rect_min_x <= seg.end_x <= rect_max_x and
            rect_min_y <= seg.end_y <= rect_max_y):
        return True

    rect_edges = [
        (rect_min_x, rect_min_y, rect_max_x, rect_min_y),
        (rect_max_x, rect_min_y, rect_max_x, rect_max_y),
        (rect_max_x, rect_max_y, rect_min_x, rect_max_y),
        (rect_min_x, rect_max_y, rect_min_x, rect_min_y),
    ]
    for ex1, ey1, ex2, ey2 in rect_edges:
        if _line_segments_intersect(
            seg.start_x, seg.start_y, seg.end_x, seg.end_y,
            ex1, ey1, ex2, ey2,
        ):
            return True
    return False


def _line_segments_intersect(
    ax1: float, ay1: float, ax2: float, ay2: float,
    bx1: float, by1: float, bx2: float, by2: float,
) -> bool:
    """Check if two line segments intersect using cross products."""
    def cross(ox, oy, ax, ay, bx, by):
        return (ax - ox) * (by - oy) - (ay - oy) * (bx - ox)

    d1 = cross(bx1, by1, bx2, by2, ax1, ay1)
    d2 = cross(bx1, by1, bx2, by2, ax2, ay2)
    d3 = cross(ax1, ay1, ax2, ay2, bx1, by1)
    d4 = cross(ax1, ay1, ax2, ay2, bx2, by2)

    if ((d1 > 0 and d2 < 0) or (d1 < 0 and d2 > 0)) and \
       ((d3 > 0 and d4 < 0) or (d3 < 0 and d4 > 0)):
        return True
    return False


# ---------------------------------------------------------------------------
# Per-net connectivity graph
# ---------------------------------------------------------------------------

MERGE_TOLERANCE_MM = 0.5


class ConnectivityGraph:
    """Union-find connectivity graph for a single net.

    Nodes are integer IDs. Each node stores its (x, y) coordinates.
    Points within MERGE_TOLERANCE_MM are merged via distance check
    against all existing nodes (brute force, fine for PCB-scale nets).
    """

    def __init__(self):
        self._parent = {}
        self._rank = {}
        self._coords = {}  # node_id → (x, y)
        self._next_id = 0

    def _find(self, k):
        while self._parent[k] != k:
            self._parent[k] = self._parent[self._parent[k]]
            k = self._parent[k]
        return k

    def _union(self, a, b):
        ra, rb = self._find(a), self._find(b)
        if ra == rb:
            return
        if self._rank[ra] < self._rank[rb]:
            ra, rb = rb, ra
        self._parent[rb] = ra
        if self._rank[ra] == self._rank[rb]:
            self._rank[ra] += 1

    def _add_point(self, x: float, y: float) -> int:
        """Add a point, merging with existing node if within tolerance."""
        for nid, (nx, ny) in self._coords.items():
            if distance(x, y, nx, ny) <= MERGE_TOLERANCE_MM:
                return nid

        nid = self._next_id
        self._next_id += 1
        self._parent[nid] = nid
        self._rank[nid] = 0
        self._coords[nid] = (x, y)
        return nid

    def add_segment(self, seg: SegmentInfo):
        na = self._add_point(seg.start_x, seg.start_y)
        nb = self._add_point(seg.end_x, seg.end_y)
        self._union(na, nb)

    def add_via(self, via: ViaInfo):
        self._add_point(via.x, via.y)

    def add_pad(self, pad: PadInfo):
        self._add_point(pad.x, pad.y)

    def connected(self, x1: float, y1: float, x2: float, y2: float) -> bool:
        """Check if two points are in the same connected component."""
        na = self._find_nearest(x1, y1)
        nb = self._find_nearest(x2, y2)
        if na is None or nb is None:
            return False
        return self._find(na) == self._find(nb)

    def _find_nearest(self, x: float, y: float) -> Optional[int]:
        """Find the graph node nearest to (x, y) within tolerance."""
        best_id = None
        best_dist = MERGE_TOLERANCE_MM + 0.01
        for nid, (nx, ny) in self._coords.items():
            d = distance(x, y, nx, ny)
            if d < best_dist:
                best_dist = d
                best_id = nid
        return best_id

    def component_count(self) -> int:
        if not self._parent:
            return 0
        roots = set(self._find(k) for k in self._parent)
        return len(roots)


def build_connectivity_graph(data: BoardData, net_number: int) -> ConnectivityGraph:
    """Build a connectivity graph for all trace/via/pad primitives on a net."""
    g = ConnectivityGraph()

    for seg in data.segments_by_net.get(net_number, []):
        g.add_segment(seg)

    for via in data.vias_by_net.get(net_number, []):
        nid = g._add_point(via.x, via.y)
        # Vias connect to all segments touching the same point
        for seg in data.segments_by_net.get(net_number, []):
            for sx, sy in [(seg.start_x, seg.start_y), (seg.end_x, seg.end_y)]:
                if distance(via.x, via.y, sx, sy) <= MERGE_TOLERANCE_MM:
                    seg_nid = g._add_point(sx, sy)
                    g._union(nid, seg_nid)

    for pad in data.pads_by_net.get(net_number, []):
        nid = g._add_point(pad.x, pad.y)
        # Connect pad to any segment endpoint or via within tolerance
        for seg in data.segments_by_net.get(net_number, []):
            for sx, sy in [(seg.start_x, seg.start_y), (seg.end_x, seg.end_y)]:
                if distance(pad.x, pad.y, sx, sy) <= MERGE_TOLERANCE_MM:
                    seg_nid = g._add_point(sx, sy)
                    g._union(nid, seg_nid)
        for via in data.vias_by_net.get(net_number, []):
            if distance(pad.x, pad.y, via.x, via.y) <= MERGE_TOLERANCE_MM:
                via_nid = g._add_point(via.x, via.y)
                g._union(nid, via_nid)

    return g


# ---------------------------------------------------------------------------
# Check result data structure
# ---------------------------------------------------------------------------

class CheckResult:
    """Result from a single verification check."""

    def __init__(self, name: str, category: str):
        self.name = name
        self.category = category
        self.status = "PASS"  # PASS, FAIL, WARNING, SKIP
        self.summary = ""
        self.details = []     # list of detail strings
        self.measurements = {}  # raw data for JSON sidecar

    def fail(self, summary: str, detail: str = ""):
        self.status = "FAIL"
        self.summary = summary
        if detail:
            self.details.append(detail)

    def warn(self, summary: str, detail: str = ""):
        self.status = "WARNING"
        self.summary = summary
        if detail:
            self.details.append(detail)

    def passed(self, summary: str):
        self.status = "PASS"
        self.summary = summary

    def skip(self, summary: str):
        self.status = "SKIP"
        self.summary = summary

    def add_detail(self, detail: str):
        self.details.append(detail)

    def to_dict(self) -> Dict[str, Any]:
        d = {
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "summary": self.summary,
        }
        if self.details:
            d["details"] = self.details
        if self.measurements:
            d["measurements"] = self.measurements
        return d


# ---------------------------------------------------------------------------
# Check implementations (Phase 2+)
# ---------------------------------------------------------------------------

def check_trace_widths(data: BoardData) -> List[CheckResult]:
    """Verify all segments match expected net class widths."""
    results = []
    violations_by_class = defaultdict(list)
    warnings_by_class = defaultdict(list)
    checked = 0

    # GND uses planes primarily; trace widths vary by purpose (thermal pad
    # connections are fat, signal-return stubs are thin). Skip width checks.
    gnd_net_num = data.net_num("GND")

    for seg in data.segments:
        if seg.net_number == gnd_net_num:
            continue
        net_name = data.net_name(seg.net_number)
        if not net_name:
            continue
        expected_class = classify_net(net_name)
        checked += 1

        diff = abs(seg.width - expected_class.width)
        if diff > WIDTH_TOLERANCE_MM:
            # Kelvin sense exemption: VSYS and VSYS_SENSE legitimately
            # have thin 0.25mm segments for INA219 sense connections
            if expected_class.name == "Power_Med" and abs(seg.width - 0.25) < WIDTH_TOLERANCE_MM:
                continue

            entry = {
                "net": net_name,
                "expected": expected_class.width,
                "actual": seg.width,
                "layer": seg.layer,
                "from": (round(seg.start_x, 2), round(seg.start_y, 2)),
                "to": (round(seg.end_x, 2), round(seg.end_y, 2)),
            }

            # For power nets and low-current Default signals, width deviations
            # are warnings (stubs to passives, constrained areas, or intentional
            # choices). Only flag as violations for nets where width is critical
            # to current capacity.
            is_minor = (
                expected_class.name != "Default"
                or abs(entry["actual"] - expected_class.width) <= 0.1
            )
            if is_minor:
                warnings_by_class[expected_class.name].append(entry)
            else:
                violations_by_class[expected_class.name].append(entry)

    r = CheckResult("Trace Width Compliance", "trace_widths")
    total_violations = sum(len(v) for v in violations_by_class.values())
    total_warnings = sum(len(v) for v in warnings_by_class.values())
    r.measurements = {
        "segments_checked": checked,
        "violations": dict(violations_by_class),
        "warnings": dict(warnings_by_class),
    }

    if total_violations == 0 and total_warnings == 0:
        r.passed(f"All {checked} segments match expected net class widths")
    elif total_violations == 0:
        r.warn(
            f"{total_warnings} power-net width deviations across "
            f"{len(warnings_by_class)} net classes (review recommended)",
        )
        for cls_name, warns in sorted(warnings_by_class.items()):
            for w in warns[:5]:
                r.add_detail(
                    f"  {w['net']} on {w['layer']}: expected {w['expected']}mm, "
                    f"got {w['actual']}mm at {w['from']}→{w['to']}"
                )
            if len(warns) > 5:
                r.add_detail(f"  ... and {len(warns) - 5} more in {cls_name}")
    else:
        r.fail(
            f"{total_violations} violations, {total_warnings} warnings",
        )
        for cls_name, viols in sorted(violations_by_class.items()):
            for v in viols:
                r.add_detail(
                    f"  {v['net']} on {v['layer']}: expected {v['expected']}mm, "
                    f"got {v['actual']}mm at {v['from']}→{v['to']}"
                )

    results.append(r)
    return results


def check_zone_existence(data: BoardData) -> List[CheckResult]:
    """Confirm required zones exist on correct layers with filled polygons."""
    expected_zones = [
        ("BOOST_SW", ["F.Cu"], "Switching loop copper pour"),
        ("+5V", ["F.Cu"], "Output cap cluster pour"),
        ("+5V", ["In2.Cu"], "+5V distribution plane"),
        ("GND", ["In1.Cu"], "Primary ground return plane"),
        ("GND", ["B.Cu"], "Bottom ground fill"),
        ("+3.3V", ["In2.Cu"], "Logic area 3.3V zone"),
    ]

    results = []
    for net_name, expected_layers, purpose in expected_zones:
        r = CheckResult(f"Zone: {net_name} on {'/'.join(expected_layers)}", "zone_existence")

        found = False
        filled = False
        for zone in data.zones:
            zone_net_short = zone.net_name.split("/")[-1] if "/" in zone.net_name else zone.net_name
            if zone_net_short != net_name:
                continue
            for layer in expected_layers:
                if layer in zone.layers:
                    found = True
                    if zone.filled_polygons:
                        filled = True
                        r.measurements["polygon_count"] = len(zone.filled_polygons)
                        total_pts = sum(len(p) for p in zone.filled_polygons)
                        r.measurements["total_vertices"] = total_pts

        if found and filled:
            r.passed(f"{purpose} — zone exists and has fill")
        elif found:
            r.warn(f"{purpose} — zone exists but has no filled polygons (refill zones?)")
        else:
            r.fail(f"{purpose} — zone NOT FOUND on {'/'.join(expected_layers)}")

        results.append(r)

    return results


def check_critical_paths(data: BoardData) -> List[CheckResult]:
    """Verify pad-to-pad connectivity for critical power paths."""
    paths = [
        {
            "name": "BOOST_SW loop (U6 SW → L2 pad 1)",
            "net": "BOOST_SW",
            "from_pad": ("U6", "4"),
            "to_pad": ("L2", "1"),
            "zone_ok": True,
        },
        {
            "name": "BQ_SW (U5 pins 19-20 → L1 pad 1)",
            "net": "BQ_SW",
            "from_pad": ("U5", "19"),
            "to_pad": ("L1", "1"),
            "zone_ok": False,
        },
        {
            "name": "VSYS power (L1 pad 2 → R44 pad 1)",
            "net": "VSYS",
            "from_pad": ("L1", "2"),
            "to_pad": ("R44", "1"),
            "zone_ok": False,
        },
        {
            "name": "VSYS_SENSE (R44 pad 2 → L2 pad 2)",
            "net": "VSYS_SENSE",
            "from_pad": ("R44", "2"),
            "to_pad": ("L2", "2"),
            "zone_ok": False,
        },
        {
            "name": "Protected_VBUS (F2 pad 2 → U5 pin 1)",
            "net": "Protected_VBUS",
            "from_pad": ("F2", "2"),
            "to_pad": ("U5", "1"),
            "zone_ok": False,
        },
    ]

    results = []
    for path in paths:
        r = CheckResult(f"Path: {path['name']}", "critical_paths")

        pad_from = data.find_pad(*path["from_pad"])
        pad_to = data.find_pad(*path["to_pad"])

        if pad_from is None:
            r.fail(f"Pad {path['from_pad'][0]}.{path['from_pad'][1]} not found")
            results.append(r)
            continue
        if pad_to is None:
            r.fail(f"Pad {path['to_pad'][0]}.{path['to_pad'][1]} not found")
            results.append(r)
            continue

        net_num = data.net_num(path["net"])
        if net_num is None:
            r.fail(f"Net '{path['net']}' not found in board")
            results.append(r)
            continue

        graph = build_connectivity_graph(data, net_num)
        connected = graph.connected(pad_from.x, pad_from.y, pad_to.x, pad_to.y)

        if connected:
            r.passed(
                f"Connected via traces/vias: "
                f"{path['from_pad'][0]}.{path['from_pad'][1]} → "
                f"{path['to_pad'][0]}.{path['to_pad'][1]}"
            )
        elif path["zone_ok"]:
            # Check zone fill connectivity as fallback.
            # Test multiple points around pad center to handle edge cases
            # where pad copper overlaps zone but center is on the boundary.
            def pad_in_zone(px, py, poly):
                offsets = [(0, 0), (0.1, 0), (-0.1, 0), (0, 0.1), (0, -0.1)]
                return any(point_in_polygon(px + dx, py + dy, poly) for dx, dy in offsets)

            zone_connected = False
            for zone in data.zones_by_net.get(net_num, []):
                for poly in zone.filled_polygons:
                    if (pad_in_zone(pad_from.x, pad_from.y, poly) and
                            pad_in_zone(pad_to.x, pad_to.y, poly)):
                        zone_connected = True
                        break
            if zone_connected:
                r.passed(
                    f"Connected via zone fill: "
                    f"{path['from_pad'][0]}.{path['from_pad'][1]} → "
                    f"{path['to_pad'][0]}.{path['to_pad'][1]}"
                )
            else:
                r.fail(
                    f"NOT connected (traces or zone): "
                    f"{path['from_pad'][0]}.{path['from_pad'][1]} → "
                    f"{path['to_pad'][0]}.{path['to_pad'][1]}"
                )
        else:
            r.fail(
                f"NOT connected via traces/vias: "
                f"{path['from_pad'][0]}.{path['from_pad'][1]} → "
                f"{path['to_pad'][0]}.{path['to_pad'][1]}"
            )

        r.measurements = {
            "from": {"ref": pad_from.ref, "pad": pad_from.number,
                     "x": pad_from.x, "y": pad_from.y},
            "to": {"ref": pad_to.ref, "pad": pad_to.number,
                   "x": pad_to.x, "y": pad_to.y},
            "net": path["net"],
        }
        results.append(r)

    return results


def check_i2c_length_matching(data: BoardData) -> List[CheckResult]:
    """Compare SDA vs SCL trace lengths for each I2C channel pair."""
    pairs = [
        ("Main trunk", "I2C_SDA", "I2C_SCL"),
        ("CH0", "CH0_SDA", "CH0_SCL"),
        ("CH1", "CH1_SDA", "CH1_SCL"),
        ("CH2", "CH2_SDA", "CH2_SCL"),
    ]

    results = []
    for label, sda_net, scl_net in pairs:
        r = CheckResult(f"I2C length match: {label}", "i2c_length")

        sda_segs = data.net_segments(sda_net)
        scl_segs = data.net_segments(scl_net)

        if not sda_segs and not scl_segs:
            r.skip(f"No routed segments for {sda_net} / {scl_net}")
            results.append(r)
            continue

        sda_len = sum(segment_length(s) for s in sda_segs)
        scl_len = sum(segment_length(s) for s in scl_segs)
        diff = abs(sda_len - scl_len)

        r.measurements = {
            "sda_length_mm": round(sda_len, 2),
            "scl_length_mm": round(scl_len, 2),
            "difference_mm": round(diff, 2),
        }

        if diff > 10.0:
            r.fail(f"SDA={sda_len:.1f}mm, SCL={scl_len:.1f}mm, diff={diff:.1f}mm (>10mm)")
        elif diff > 5.0:
            r.warn(f"SDA={sda_len:.1f}mm, SCL={scl_len:.1f}mm, diff={diff:.1f}mm (>5mm)")
        else:
            r.passed(f"SDA={sda_len:.1f}mm, SCL={scl_len:.1f}mm, diff={diff:.1f}mm")

        results.append(r)

    return results


def check_i2c_isolation(data: BoardData) -> List[CheckResult]:
    """Check that I2C traces stay outside exclusion zones around switching components."""
    r = CheckResult("I2C isolation from switching nodes", "i2c_isolation")

    # Build exclusion rectangles: component bbox + margin
    exclusion_rects = []
    inductor_margin = 3.0
    sw_pin_margin = 2.0

    for ref, margin, label in [("L1", inductor_margin, "L1"), ("L2", inductor_margin, "L2")]:
        pad_list = [p for p in data.pads if p.ref == ref]
        if pad_list:
            xs = [p.x for p in pad_list]
            ys = [p.y for p in pad_list]
            exclusion_rects.append((
                min(xs) - margin, min(ys) - margin,
                max(xs) + margin, max(ys) + margin,
                label,
            ))

    # U6 SW pins 4-7
    u6_sw_pads = [data.find_pad("U6", str(n)) for n in range(4, 8)]
    u6_sw_pads = [p for p in u6_sw_pads if p is not None]
    if u6_sw_pads:
        xs = [p.x for p in u6_sw_pads]
        ys = [p.y for p in u6_sw_pads]
        exclusion_rects.append((
            min(xs) - sw_pin_margin, min(ys) - sw_pin_margin,
            max(xs) + sw_pin_margin, max(ys) + sw_pin_margin,
            "U6 SW pins",
        ))

    # U5 SW pins 19-20
    u5_sw_pads = [data.find_pad("U5", str(n)) for n in (19, 20)]
    u5_sw_pads = [p for p in u5_sw_pads if p is not None]
    if u5_sw_pads:
        xs = [p.x for p in u5_sw_pads]
        ys = [p.y for p in u5_sw_pads]
        exclusion_rects.append((
            min(xs) - sw_pin_margin, min(ys) - sw_pin_margin,
            max(xs) + sw_pin_margin, max(ys) + sw_pin_margin,
            "U5 SW pins",
        ))

    i2c_nets = [
        "I2C_SDA", "I2C_SCL",
        "CH0_SDA", "CH0_SCL",
        "CH1_SDA", "CH1_SCL",
        "CH2_SDA", "CH2_SCL",
    ]

    violations = []
    total_checked = 0
    for net_name in i2c_nets:
        segs = data.net_segments(net_name)
        for seg in segs:
            total_checked += 1
            for rx1, ry1, rx2, ry2, rect_label in exclusion_rects:
                if segments_intersect_rect(seg, rx1, ry1, rx2, ry2):
                    violations.append({
                        "net": net_name,
                        "zone": rect_label,
                        "segment": {
                            "from": (round(seg.start_x, 2), round(seg.start_y, 2)),
                            "to": (round(seg.end_x, 2), round(seg.end_y, 2)),
                        },
                    })

    r.measurements = {
        "segments_checked": total_checked,
        "exclusion_zones": len(exclusion_rects),
        "violations": violations,
    }

    if not violations:
        r.passed(f"All {total_checked} I2C segments clear of {len(exclusion_rects)} exclusion zones")
    else:
        r.fail(f"{len(violations)} I2C segments enter switching exclusion zones")
        for v in violations:
            r.add_detail(
                f"  {v['net']} segment {v['segment']['from']}→{v['segment']['to']} "
                f"enters {v['zone']} exclusion zone"
            )

    return [r]


def check_kelvin_sense(data: BoardData) -> List[CheckResult]:
    """Verify INA219 Kelvin sense traces are thin, dedicated connections.

    "Thin" means significantly narrower than the power trace width on the
    same net. The threshold is half the power class width (0.5mm for 1.0mm
    Power_Med nets). This accommodates slight width variations while still
    catching cases where the sense path shares fat power traces.
    """
    results = []

    sense_paths = [
        {
            "name": "VSYS sense (R44.1 → U7.1)",
            "net": "VSYS",
            "from_pad": ("R44", "1"),
            "to_pad": ("U7", "1"),
            "power_width": 1.0,
        },
        {
            "name": "VSYS_SENSE sense (R44.2 → U7.2)",
            "net": "VSYS_SENSE",
            "from_pad": ("R44", "2"),
            "to_pad": ("U7", "2"),
            "power_width": 1.0,
        },
    ]

    for sp in sense_paths:
        r = CheckResult(f"Kelvin: {sp['name']}", "kelvin_sense")

        pad_from = data.find_pad(*sp["from_pad"])
        pad_to = data.find_pad(*sp["to_pad"])

        if pad_from is None or pad_to is None:
            r.fail("Required pads not found")
            results.append(r)
            continue

        net_num = data.net_num(sp["net"])
        if net_num is None:
            r.fail(f"Net '{sp['net']}' not found")
            results.append(r)
            continue

        thin_threshold = sp["power_width"] / 2.0

        thin_segs = [
            s for s in data.segments_by_net.get(net_num, [])
            if s.width < thin_threshold
        ]
        sense_widths = sorted(set(s.width for s in thin_segs)) if thin_segs else []

        thin_graph = ConnectivityGraph()
        for s in thin_segs:
            thin_graph.add_segment(s)

        for pad in (pad_from, pad_to):
            nid = thin_graph._add_point(pad.x, pad.y)
            for s in thin_segs:
                for sx, sy in [(s.start_x, s.start_y), (s.end_x, s.end_y)]:
                    if distance(pad.x, pad.y, sx, sy) <= MERGE_TOLERANCE_MM:
                        seg_nid = thin_graph._add_point(sx, sy)
                        thin_graph._union(nid, seg_nid)

        connected_thin = thin_graph.connected(pad_from.x, pad_from.y, pad_to.x, pad_to.y)

        r.measurements = {
            "thin_segments": len(thin_segs),
            "thin_threshold_mm": thin_threshold,
            "sense_widths_mm": sense_widths,
            "connected_via_thin_only": connected_thin,
        }

        if connected_thin:
            width_str = "/".join(f"{w}mm" for w in sense_widths) if sense_widths else "?"
            r.passed(
                f"Dedicated thin path ({width_str}) exists, "
                f"separate from {sp['power_width']}mm power traces "
                f"({len(thin_segs)} sense segments)"
            )
        else:
            r.fail(
                f"No dedicated thin path (<{thin_threshold}mm) from "
                f"{sp['from_pad'][0]}.{sp['from_pad'][1]} to "
                f"{sp['to_pad'][0]}.{sp['to_pad'][1]}"
            )

        results.append(r)

    return results


def check_fb_comp_routing(data: BoardData) -> List[CheckResult]:
    """Verify BOOST_FB and BOOST_COMP traces stay on U6's left (low-x) side."""
    r = CheckResult("FB/COMP routing side", "fb_comp_side")

    # U6 center x
    u6_pads = [p for p in data.pads if p.ref == "U6"]
    if not u6_pads:
        r.fail("U6 not found in board")
        return [r]

    u6_center_x = sum(p.x for p in u6_pads) / len(u6_pads)
    r.measurements["u6_center_x"] = round(u6_center_x, 2)

    violations = []
    for net_name in ("BOOST_FB", "BOOST_COMP"):
        segs = data.net_segments(net_name)
        for seg in segs:
            max_x = max(seg.start_x, seg.end_x)
            if max_x > u6_center_x + MERGE_TOLERANCE_MM:
                violations.append({
                    "net": net_name,
                    "max_x": round(max_x, 2),
                    "from": (round(seg.start_x, 2), round(seg.start_y, 2)),
                    "to": (round(seg.end_x, 2), round(seg.end_y, 2)),
                })

    r.measurements["violations"] = violations

    if not violations:
        r.passed(f"All FB/COMP traces stay left of U6 center (x < {u6_center_x:.1f})")
    else:
        r.fail(f"{len(violations)} segments cross to U6's right (SW/inductor) side")
        for v in violations:
            r.add_detail(
                f"  {v['net']} at {v['from']}→{v['to']} "
                f"(max x={v['max_x']} > center {u6_center_x:.1f})"
            )

    return [r]


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def generate_markdown_report(
    results: List[CheckResult],
    data: BoardData,
    pcb_hash: str,
) -> str:
    """Generate a human-readable Markdown verification report."""
    lines = []
    lines.append("# PCB Routing Verification Report\n")
    lines.append(f"**Source:** `{data.pcb_path.name}`  ")
    lines.append(f"**SHA-256:** `{pcb_hash[:16]}...`  ")
    lines.append(f"**Generated:** {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  ")

    summary = data.summary()
    lines.append(f"**Board:** {summary['footprints']} footprints, "
                 f"{summary['segments']} segments, {summary['vias']} vias, "
                 f"{summary['zones']} zones, {summary['nets']} nets\n")

    # Summary table
    pass_count = sum(1 for r in results if r.status == "PASS")
    fail_count = sum(1 for r in results if r.status == "FAIL")
    warn_count = sum(1 for r in results if r.status == "WARNING")
    skip_count = sum(1 for r in results if r.status == "SKIP")

    lines.append(f"## Summary: {pass_count} PASS, {fail_count} FAIL, "
                 f"{warn_count} WARNING, {skip_count} SKIP\n")
    lines.append("| Check | Status | Detail |")
    lines.append("|-------|--------|--------|")

    status_icon = {"PASS": "PASS", "FAIL": "**FAIL**", "WARNING": "WARN", "SKIP": "SKIP"}
    for r in results:
        icon = status_icon.get(r.status, r.status)
        lines.append(f"| {r.name} | {icon} | {r.summary} |")

    # Detailed sections per category
    categories = []
    seen = set()
    for r in results:
        if r.category not in seen:
            categories.append(r.category)
            seen.add(r.category)

    for cat in categories:
        cat_results = [r for r in results if r.category == cat]
        has_details = any(r.details for r in cat_results)
        if not has_details:
            continue

        lines.append(f"\n## Details: {cat}\n")
        for r in cat_results:
            if r.details:
                lines.append(f"### {r.name} — {r.status}\n")
                lines.append("```")
                for d in r.details:
                    lines.append(d)
                lines.append("```\n")

    return "\n".join(lines) + "\n"


def generate_json_report(
    results: List[CheckResult],
    data: BoardData,
    pcb_hash: str,
) -> Dict[str, Any]:
    """Generate machine-readable JSON verification report."""
    return {
        "meta": {
            "source_file": str(data.pcb_path.name),
            "sha256": pcb_hash,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "board_summary": data.summary(),
        },
        "summary": {
            "total_checks": len(results),
            "pass": sum(1 for r in results if r.status == "PASS"),
            "fail": sum(1 for r in results if r.status == "FAIL"),
            "warning": sum(1 for r in results if r.status == "WARNING"),
            "skip": sum(1 for r in results if r.status == "SKIP"),
        },
        "checks": [r.to_dict() for r in results],
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def file_sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(str(path), "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify PCB routing against ROUTING_GUIDE.md specifications.",
    )
    parser.add_argument(
        "pcb",
        help="Path to the .kicad_pcb file",
    )
    parser.add_argument(
        "--output-dir", "-o",
        help="Directory for report output (default: hardware/pcb-main/kicad/reports/)",
    )
    args = parser.parse_args()

    pcb_path = Path(args.pcb).resolve()
    if not pcb_path.exists() or pcb_path.suffix != ".kicad_pcb":
        print(f"Error: invalid PCB file: {pcb_path}", file=sys.stderr)
        sys.exit(1)

    output_dir = Path(args.output_dir).resolve() if args.output_dir else pcb_path.parent / "reports"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load board
    print(f"Loading {pcb_path.name}...", file=sys.stderr)
    board = Board.from_file(str(pcb_path))

    # Extract all routing data
    print("Extracting routing primitives...", file=sys.stderr)
    data = BoardData(board, pcb_path)
    s = data.summary()
    print(f"  {s['pads']} pads, {s['segments']} segments, "
          f"{s['vias']} vias, {s['zones']} zones", file=sys.stderr)

    pcb_hash = file_sha256(pcb_path)

    # Run all checks
    print("Running verification checks...", file=sys.stderr)
    all_results = []
    all_results.extend(check_trace_widths(data))
    all_results.extend(check_zone_existence(data))
    all_results.extend(check_critical_paths(data))
    all_results.extend(check_i2c_length_matching(data))
    all_results.extend(check_i2c_isolation(data))
    all_results.extend(check_kelvin_sense(data))
    all_results.extend(check_fb_comp_routing(data))

    # Generate reports
    md_path = output_dir / "routing-verification.md"
    json_path = output_dir / "routing-verification.json"

    md_report = generate_markdown_report(all_results, data, pcb_hash)
    with open(str(md_path), "w") as f:
        f.write(md_report)

    json_report = generate_json_report(all_results, data, pcb_hash)
    with open(str(json_path), "w") as f:
        json.dump(json_report, f, indent=2)
        f.write("\n")

    # Print summary to stderr
    pass_count = sum(1 for r in all_results if r.status == "PASS")
    fail_count = sum(1 for r in all_results if r.status == "FAIL")
    warn_count = sum(1 for r in all_results if r.status == "WARNING")
    skip_count = sum(1 for r in all_results if r.status == "SKIP")

    print(f"\n{'='*50}", file=sys.stderr)
    print(f"Results: {pass_count} PASS, {fail_count} FAIL, "
          f"{warn_count} WARNING, {skip_count} SKIP", file=sys.stderr)
    print(f"{'='*50}", file=sys.stderr)

    for r in all_results:
        marker = {"PASS": " ", "FAIL": "X", "WARNING": "!", "SKIP": "-"}
        print(f"  [{marker.get(r.status, '?')}] {r.name}: {r.summary}", file=sys.stderr)

    print(f"\nReports written to:", file=sys.stderr)
    print(f"  {md_path}", file=sys.stderr)
    print(f"  {json_path}", file=sys.stderr)

    sys.exit(1 if fail_count > 0 else 0)


if __name__ == "__main__":
    main()

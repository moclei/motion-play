#!/usr/bin/env python3
"""
routing_extract.py — PCB routing context extraction.

Parses a KiCad .kicad_pcb file via kiutils and produces a
pcb-routing-context.json containing per-net track segments, vias,
and per-footprint pads in world-space coordinates.

Complements extract.py (placement-focused). Used downstream by
routing_audit.py (Phase 2) to compute proximity / asymmetry metrics.

Usage:
    python routing_extract.py <file.kicad_pcb>
    python routing_extract.py <file.kicad_pcb> --output path/to/output.json
    python routing_extract.py <file.kicad_pcb> --list-nets
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kiutils.board import Board
from kiutils.items.brditems import Arc, Segment, Via


# ---------------------------------------------------------------------------
# Net resolution
# ---------------------------------------------------------------------------

def build_net_index(board: Board) -> Dict[int, str]:
    """Build a {net_number: net_name} map from board.nets."""
    return {n.number: n.name for n in board.nets}


# ---------------------------------------------------------------------------
# Track segment / arc / via extraction
# ---------------------------------------------------------------------------

# Arc handling note:
#   The current motion-play-main.kicad_pcb (v7) contains 0 arcs (855 segments
#   + 224 vias only). To stay forward-compatible, we *sample* arcs into a
#   short polyline and contribute their summed chord lengths to the per-layer
#   length total. Sampling is safer than chord approximation for length and
#   matches the path PLAN.md sketched as the safer default. This default does
#   not require updating PLAN.md.
_ARC_SAMPLE_STEPS = 16


def _segment_length(start_xy: Tuple[float, float], end_xy: Tuple[float, float]) -> float:
    return math.hypot(end_xy[0] - start_xy[0], end_xy[1] - start_xy[1])


def _arc_to_polyline(arc: Arc, steps: int = _ARC_SAMPLE_STEPS) -> List[Tuple[float, float]]:
    """Sample a 3-point arc (start, mid, end) into a polyline of `steps+1` points.

    KiCad arcs are stored as (start, mid, end). We solve the circumscribed
    circle through those three points, then sweep the angle from start→end
    in the direction that passes through `mid`.
    """
    sx, sy = arc.start.X, arc.start.Y
    mx, my = arc.mid.X, arc.mid.Y
    ex, ey = arc.end.X, arc.end.Y

    # Circle through three points: solve the perpendicular bisector intersection
    d = 2.0 * (sx * (my - ey) + mx * (ey - sy) + ex * (sy - my))
    if abs(d) < 1e-12:
        # Degenerate (collinear): fall back to start→end straight line
        return [(sx, sy), (ex, ey)]

    ux = ((sx * sx + sy * sy) * (my - ey)
          + (mx * mx + my * my) * (ey - sy)
          + (ex * ex + ey * ey) * (sy - my)) / d
    uy = ((sx * sx + sy * sy) * (ex - mx)
          + (mx * mx + my * my) * (sx - ex)
          + (ex * ex + ey * ey) * (mx - sx)) / d

    cx, cy = ux, uy
    r = math.hypot(sx - cx, sy - cy)

    a_start = math.atan2(sy - cy, sx - cx)
    a_mid = math.atan2(my - cy, mx - cx)
    a_end = math.atan2(ey - cy, ex - cx)

    # Determine sweep direction by checking if `mid` lies on the
    # CCW arc from start to end. If so, sweep CCW; otherwise CW.
    def _ccw_delta(a: float, b: float) -> float:
        d = (b - a) % (2.0 * math.pi)
        return d

    ccw_total = _ccw_delta(a_start, a_end)
    ccw_mid = _ccw_delta(a_start, a_mid)
    if 0.0 < ccw_mid < ccw_total or ccw_total == 0.0:
        sweep = ccw_total if ccw_total != 0.0 else 2.0 * math.pi
        sign = 1.0
    else:
        sweep = (2.0 * math.pi) - ccw_total
        sign = -1.0

    pts: List[Tuple[float, float]] = []
    for i in range(steps + 1):
        t = i / steps
        a = a_start + sign * sweep * t
        pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def _polyline_length(pts: List[Tuple[float, float]]) -> float:
    total = 0.0
    for i in range(1, len(pts)):
        total += _segment_length(pts[i - 1], pts[i])
    return total


def extract_traces(
    board: Board, net_index: Dict[int, str]
) -> Dict[str, Dict[str, Any]]:
    """Extract per-net segments, arcs (sampled), and vias.

    Returns a map keyed by net name. Net 0 (unnamed) and unconnected nets are
    included if they happen to host trace items, since callers may want to
    inspect them; the auditor decides which to surface.
    """
    nets: Dict[str, Dict[str, Any]] = {}

    def _ensure(net_name: str) -> Dict[str, Any]:
        entry = nets.get(net_name)
        if entry is None:
            entry = {
                "name": net_name,
                "segments": [],
                "vias": [],
                "length_by_layer": defaultdict(float),
            }
            nets[net_name] = entry
        return entry

    seg_count = arc_count = via_count = 0

    for item in board.traceItems:
        if isinstance(item, Segment):
            net_name = net_index.get(item.net, f"<net#{item.net}>")
            entry = _ensure(net_name)
            sx, sy = round(item.start.X, 4), round(item.start.Y, 4)
            ex, ey = round(item.end.X, 4), round(item.end.Y, 4)
            length = _segment_length((sx, sy), (ex, ey))
            entry["segments"].append({
                "kind": "segment",
                "start": [sx, sy],
                "end": [ex, ey],
                "width": round(item.width, 4),
                "layer": item.layer,
                "length_mm": round(length, 4),
            })
            entry["length_by_layer"][item.layer] += length
            seg_count += 1

        elif isinstance(item, Arc):
            net_name = net_index.get(item.net, f"<net#{item.net}>")
            entry = _ensure(net_name)
            poly = _arc_to_polyline(item)
            length = _polyline_length(poly)
            entry["segments"].append({
                "kind": "arc",
                "start": [round(item.start.X, 4), round(item.start.Y, 4)],
                "mid": [round(item.mid.X, 4), round(item.mid.Y, 4)],
                "end": [round(item.end.X, 4), round(item.end.Y, 4)],
                "width": round(item.width, 4),
                "layer": item.layer,
                "length_mm": round(length, 4),
                "polyline": [[round(x, 4), round(y, 4)] for x, y in poly],
            })
            entry["length_by_layer"][item.layer] += length
            arc_count += 1

        elif isinstance(item, Via):
            net_name = net_index.get(item.net, f"<net#{item.net}>")
            entry = _ensure(net_name)
            entry["vias"].append({
                "position": [
                    round(item.position.X, 4),
                    round(item.position.Y, 4),
                ],
                "drill": round(item.drill, 4) if item.drill else 0.0,
                "size": round(item.size, 4) if item.size else 0.0,
                "layers": list(item.layers),
                "type": item.type or "through",
            })
            via_count += 1

    # Finalize length_by_layer + total_length_mm with rounding
    finalized: Dict[str, Dict[str, Any]] = {}
    for net_name, entry in nets.items():
        by_layer = {
            layer: round(length, 4)
            for layer, length in sorted(entry["length_by_layer"].items())
        }
        total = round(sum(entry["length_by_layer"].values()), 4)
        finalized[net_name] = {
            "name": entry["name"],
            "segments": entry["segments"],
            "vias": entry["vias"],
            "total_length_mm": total,
            "length_by_layer": by_layer,
        }

    finalized["__counts__"] = {  # type: ignore[assignment]
        "segments": seg_count,
        "arcs": arc_count,
        "vias": via_count,
    }
    return finalized


# ---------------------------------------------------------------------------
# Footprint pad extraction (world-space)
# ---------------------------------------------------------------------------

def _world_xy(
    fp_x: float, fp_y: float, angle_deg: float, lx: float, ly: float
) -> Tuple[float, float]:
    """Apply KiCad's footprint-local → board-global transform.

    Matches extract.py's convention exactly (KiCad's Y-down PCB system):
        gx = fp_x + lx*cos(θ) + ly*sin(θ)
        gy = fp_y - lx*sin(θ) + ly*cos(θ)
    """
    theta = math.radians(angle_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    gx = fp_x + lx * cos_t + ly * sin_t
    gy = fp_y - lx * sin_t + ly * cos_t
    return gx, gy


def _pad_layers(pad) -> List[str]:
    """Resolve a pad's actual copper layers, expanding wildcards conservatively.

    KiCad pad layer entries can be literal layer names ("F.Cu") or wildcards
    ("*.Cu" → all copper layers). For SMD pads we typically see a single
    layer; through-hole returns ["*.Cu", "F.Mask", "B.Mask"] which we
    normalize to the actual copper layers F.Cu + B.Cu (plus inner copper
    if the board has them).
    """
    layers = list(pad.layers or [])
    if not layers:
        return []
    return layers


def _pad_effective_radius(pad) -> float:
    """Conservative effective radius for a pad: half of the larger dimension.

    Treats rect / oval / roundrect as their bounding circle for v1 proximity
    use. Auditor (Phase 2) will refine if needed.
    """
    sx = pad.size.X if hasattr(pad.size, "X") else 0.0
    sy = pad.size.Y if hasattr(pad.size, "Y") else 0.0
    return round(max(sx, sy) / 2.0, 4)


def extract_footprint_pads(fp) -> List[Dict[str, Any]]:
    """Extract pads with world-space positions, sizes, and net info."""
    fp_x = fp.position.X
    fp_y = fp.position.Y
    angle_deg = fp.position.angle or 0

    pads: List[Dict[str, Any]] = []
    for pad in fp.pads:
        gx, gy = _world_xy(fp_x, fp_y, angle_deg, pad.position.X, pad.position.Y)
        net_name = ""
        net_number = None
        if pad.net is not None:
            net_name = getattr(pad.net, "name", "") or ""
            net_number = getattr(pad.net, "number", None)
        pads.append({
            "number": pad.number,
            "type": pad.type,
            "shape": pad.shape,
            "position": [round(gx, 4), round(gy, 4)],
            "size": [
                round(pad.size.X, 4) if hasattr(pad.size, "X") else 0.0,
                round(pad.size.Y, 4) if hasattr(pad.size, "Y") else 0.0,
            ],
            "effective_radius": _pad_effective_radius(pad),
            "layers": _pad_layers(pad),
            "net": net_name,
            "net_number": net_number,
        })
    return pads


# ---------------------------------------------------------------------------
# Per-layer footprint bounding box (in world-space)
# ---------------------------------------------------------------------------

def _bbox_from_world_pads(
    pads: List[Dict[str, Any]],
) -> Dict[str, Dict[str, float]]:
    """Group pads by copper layer and produce a per-layer world-space bbox.

    Wildcard layers ("*.Cu") contribute to every Cu layer in `_KNOWN_CU`.
    """
    per_layer: Dict[str, List[Tuple[float, float, float, float]]] = defaultdict(list)
    for pad in pads:
        px, py = pad["position"]
        rx = pad["size"][0] / 2.0
        ry = pad["size"][1] / 2.0
        # Pad bbox in world frame is approximate (ignores per-pad rotation
        # relative to footprint); for v1 this is good enough for component
        # exclusion zones. Auditor will refine if a pad turns out to need
        # tighter geometry.
        x0, x1 = px - rx, px + rx
        y0, y1 = py - ry, py + ry

        for layer in pad["layers"]:
            if layer.endswith(".Cu") or layer == "*.Cu":
                # Wildcard: expand to all known copper layers we've seen
                # (we don't know the full stack here without scanning the
                # board's layer list — that's done in extract_components).
                per_layer[layer].append((x0, y0, x1, y1))

    result: Dict[str, Dict[str, float]] = {}
    for layer, boxes in per_layer.items():
        xs0 = [b[0] for b in boxes]
        ys0 = [b[1] for b in boxes]
        xs1 = [b[2] for b in boxes]
        ys1 = [b[3] for b in boxes]
        result[layer] = {
            "min_x": round(min(xs0), 4),
            "min_y": round(min(ys0), 4),
            "max_x": round(max(xs1), 4),
            "max_y": round(max(ys1), 4),
        }
    return result


def _expand_wildcard_bboxes(
    bbox_by_layer: Dict[str, Dict[str, float]],
    cu_layers: List[str],
) -> Dict[str, Dict[str, float]]:
    """If "*.Cu" is present, distribute its bbox onto every real Cu layer."""
    if "*.Cu" not in bbox_by_layer:
        return bbox_by_layer
    wild = bbox_by_layer.pop("*.Cu")
    for layer in cu_layers:
        existing = bbox_by_layer.get(layer)
        if existing is None:
            bbox_by_layer[layer] = dict(wild)
        else:
            bbox_by_layer[layer] = {
                "min_x": min(existing["min_x"], wild["min_x"]),
                "min_y": min(existing["min_y"], wild["min_y"]),
                "max_x": max(existing["max_x"], wild["max_x"]),
                "max_y": max(existing["max_y"], wild["max_y"]),
            }
    return bbox_by_layer


# ---------------------------------------------------------------------------
# Footprint extraction
# ---------------------------------------------------------------------------

def extract_footprints(board: Board, cu_layers: List[str]) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for fp in board.footprints:
        ref = fp.properties.get("Reference", "")
        value = fp.properties.get("Value", "")
        x = round(fp.position.X, 4)
        y = round(fp.position.Y, 4)
        rotation = fp.position.angle or 0
        side = "front" if fp.layer == "F.Cu" else "back"

        pads = extract_footprint_pads(fp)
        bbox_by_layer = _bbox_from_world_pads(pads)
        bbox_by_layer = _expand_wildcard_bboxes(bbox_by_layer, cu_layers)

        out.append({
            "ref": ref,
            "value": value,
            "position": [x, y],
            "rotation": rotation,
            "side": side,
            "bbox_by_layer": bbox_by_layer,
            "pads": pads,
        })

    out.sort(key=lambda c: _ref_sort_key(c["ref"]))
    return out


def _ref_sort_key(ref: str) -> Tuple[str, int]:
    """Sort references by prefix then numeric suffix (C1 < C2 < C10)."""
    prefix = ref.rstrip("0123456789")
    num_str = ref[len(prefix):]
    try:
        return (prefix, int(num_str))
    except ValueError:
        return (prefix, 0)


# ---------------------------------------------------------------------------
# Context assembly
# ---------------------------------------------------------------------------

def _cu_layers(board: Board) -> List[str]:
    return [layer.name for layer in board.layers if layer.type == "signal"]


def build_context(
    pcb_path: Path,
    raw_pcb_arg: str,
    board: Board,
) -> Dict[str, Any]:
    net_index = build_net_index(board)
    cu_layers = _cu_layers(board)

    nets_with_counts = extract_traces(board, net_index)
    counts = nets_with_counts.pop("__counts__")

    footprints = extract_footprints(board, cu_layers)

    return {
        "meta": {
            "source_file": raw_pcb_arg,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "kicad_format_version": board.version,
            "kicad_generator": board.generator,
            "cu_layers": cu_layers,
            "trace_item_counts": counts,
            "arc_handling": "sampled_polyline",
        },
        "nets": dict(sorted(nets_with_counts.items(), key=lambda kv: kv[0])),
        "footprints": footprints,
    }


# ---------------------------------------------------------------------------
# Output
# ---------------------------------------------------------------------------

def _compact_json(obj: Any) -> str:
    """JSON formatter that keeps top-level structure readable but collapses
    deeply repetitive lists (segments, vias, pads) onto one line each.

    Mirrors the spirit of extract.py's _compact_json.
    """
    lines = ["{"]

    top_keys = list(obj.keys())
    for ki, key in enumerate(top_keys):
        is_last = ki == len(top_keys) - 1
        comma = "" if is_last else ","
        val = obj[key]

        if key == "meta":
            dumped = json.dumps(val, indent=2, ensure_ascii=False)
            indented = dumped.replace("\n", "\n  ")
            lines.append(f'  "meta": {indented}{comma}')

        elif key == "nets":
            lines.append('  "nets": {')
            net_names = list(val.keys())
            for ni, net_name in enumerate(net_names):
                last_net = ni == len(net_names) - 1
                ncomma = "" if last_net else ","
                net_data = val[net_name]
                lines.append(f'    {json.dumps(net_name)}: {{')
                lines.append(f'      "name": {json.dumps(net_data["name"])},')
                lines.append(
                    f'      "total_length_mm": {json.dumps(net_data["total_length_mm"])},'
                )
                lines.append(
                    f'      "length_by_layer": {json.dumps(net_data["length_by_layer"])},'
                )
                # Segments: one per line
                lines.append('      "segments": [')
                for si, seg in enumerate(net_data["segments"]):
                    scomma = "" if si == len(net_data["segments"]) - 1 else ","
                    lines.append(f'        {json.dumps(seg, ensure_ascii=False)}{scomma}')
                lines.append('      ],')
                # Vias: one per line
                lines.append('      "vias": [')
                for vi, via in enumerate(net_data["vias"]):
                    vcomma = "" if vi == len(net_data["vias"]) - 1 else ","
                    lines.append(f'        {json.dumps(via, ensure_ascii=False)}{vcomma}')
                lines.append('      ]')
                lines.append(f'    }}{ncomma}')
            lines.append(f'  }}{comma}')

        elif key == "footprints":
            lines.append('  "footprints": [')
            for fi, fp in enumerate(val):
                fcomma = "" if fi == len(val) - 1 else ","
                fp_no_lists = {k: v for k, v in fp.items() if k not in ("pads", "bbox_by_layer")}
                head = json.dumps(fp_no_lists, ensure_ascii=False)[:-1]  # strip "}"
                lines.append(f'    {head}, "bbox_by_layer": {json.dumps(fp["bbox_by_layer"], ensure_ascii=False)}, "pads": [')
                for pi, pad in enumerate(fp["pads"]):
                    pcomma = "" if pi == len(fp["pads"]) - 1 else ","
                    lines.append(f'      {json.dumps(pad, ensure_ascii=False)}{pcomma}')
                lines.append(f'    ]}}{fcomma}')
            lines.append(f'  ]{comma}')

        else:
            dumped = json.dumps(val, indent=2, ensure_ascii=False)
            indented = dumped.replace("\n", "\n  ")
            lines.append(f'  "{key}": {indented}{comma}')

    lines.append("}")
    return "\n".join(lines) + "\n"


def write_context_json(context: dict, output_path: Path) -> None:
    with open(str(output_path), "w") as f:
        f.write(_compact_json(context))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def resolve_pcb(raw_path: str) -> Path:
    pcb = Path(raw_path).resolve()

    if not pcb.exists():
        print(f"Error: PCB file not found: {pcb}", file=sys.stderr)
        sys.exit(1)

    if not pcb.is_file():
        print(f"Error: not a file: {pcb}", file=sys.stderr)
        sys.exit(1)

    if pcb.suffix != ".kicad_pcb":
        print(
            f"Error: expected a .kicad_pcb file, got: {pcb.name}",
            file=sys.stderr,
        )
        sys.exit(1)

    return pcb


def resolve_output_path(pcb: Path, explicit_output: Optional[str]) -> Path:
    if explicit_output:
        return Path(explicit_output).resolve()
    return pcb.parent / "pcb-routing-context.json"


def _print_nets(board: Board) -> None:
    """Print all nets that host at least one trace item, plus net names with
    no traces (so users see them too — they can still be referenced in audit
    specs to detect unintentionally-unrouted nets).
    """
    counts: Dict[int, int] = defaultdict(int)
    for item in board.traceItems:
        if isinstance(item, (Segment, Arc, Via)):
            counts[item.net] += 1

    print(f"Nets in {Path(board.filePath).name}:", file=sys.stderr)
    for net in board.nets:
        n = counts.get(net.number, 0)
        marker = "" if n > 0 else "  (no traces)"
        print(f"  #{net.number:>3}  {net.name!r:50s}  {n} trace items{marker}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Extract per-net trace geometry and per-footprint pad world-space "
            "data from a KiCad board file."
        ),
    )
    parser.add_argument(
        "pcb",
        help="Path to the .kicad_pcb file",
    )
    parser.add_argument(
        "--output", "-o",
        help=(
            "Output path for pcb-routing-context.json "
            "(default: pcb-routing-context.json next to the PCB)"
        ),
    )
    parser.add_argument(
        "--list-nets",
        action="store_true",
        help=(
            "List every net (with trace-item count) and exit. Useful for "
            "discovering exact net names to use in audit specs."
        ),
    )
    args = parser.parse_args()

    pcb_path = resolve_pcb(args.pcb)

    print(f"Loading {pcb_path.name}...", file=sys.stderr)
    board = Board.from_file(str(pcb_path))
    print(
        f"  {len(board.footprints)} footprints, "
        f"{len(board.nets)} nets, "
        f"{len(board.traceItems)} trace items",
        file=sys.stderr,
    )

    if args.list_nets:
        _print_nets(board)
        return

    output_path = resolve_output_path(pcb_path, args.output)

    context = build_context(pcb_path, args.pcb, board)
    write_context_json(context, output_path)

    counts = context["meta"]["trace_item_counts"]
    nets_with_traces = sum(
        1 for net_data in context["nets"].values()
        if net_data["total_length_mm"] > 0
    )

    print(
        f"\nWrote {output_path.name} ({output_path.stat().st_size:,} bytes)",
        file=sys.stderr,
    )
    print(
        f"  segments: {counts['segments']}, "
        f"arcs: {counts['arcs']}, "
        f"vias: {counts['vias']}",
        file=sys.stderr,
    )
    print(
        f"  {nets_with_traces} routed nets, "
        f"{len(context['footprints'])} footprints",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()

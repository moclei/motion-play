#!/usr/bin/env python3
"""
extract.py — PCB layout context extraction.

Parses a KiCad .kicad_pcb file via kiutils and produces a
pcb-layout-context.json for AI-assisted PCB layout sessions.

Extracts board outline, placed component positions/bounding boxes,
and identifies unplaced components by cross-referencing with
circuit-context.json (if available alongside the PCB).

Usage:
    python extract.py <file.kicad_pcb>
    python extract.py <file.kicad_pcb> --pads
    python extract.py <file.kicad_pcb> --output path/to/output.json
    python extract.py <file.kicad_pcb> --schematic-context path/to/circuit-context.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from kiutils.board import Board
from kiutils.items.common import Position


# ---------------------------------------------------------------------------
# Board outline extraction
# ---------------------------------------------------------------------------

def extract_board_outline(board: Board) -> Dict[str, Any]:
    """Extract the board outline from Edge.Cuts layer graphic items.

    Handles GrRect (common for simple boards) and falls back to
    computing a bounding polygon from GrLine/GrArc segments.
    """
    edge_cuts = [
        gi for gi in board.graphicItems
        if getattr(gi, "layer", None) == "Edge.Cuts"
    ]

    if not edge_cuts:
        return {"type": "none", "error": "No Edge.Cuts graphics found"}

    gi = edge_cuts[0]
    type_name = type(gi).__name__

    if type_name == "GrRect" and hasattr(gi, "start") and hasattr(gi, "end"):
        return _outline_from_rect(gi)

    return _outline_from_segments(edge_cuts)


def _outline_from_rect(rect) -> Dict[str, Any]:
    min_x = min(rect.start.X, rect.end.X)
    max_x = max(rect.start.X, rect.end.X)
    min_y = min(rect.start.Y, rect.end.Y)
    max_y = max(rect.start.Y, rect.end.Y)
    width = round(max_x - min_x, 3)
    height = round(max_y - min_y, 3)
    return {
        "type": "rectangle",
        "min_x": min_x,
        "min_y": min_y,
        "max_x": max_x,
        "max_y": max_y,
        "width": width,
        "height": height,
    }


def _outline_from_segments(items) -> Dict[str, Any]:
    """Compute bounding box from a collection of Edge.Cuts line/arc segments."""
    xs, ys = [], []
    for gi in items:
        if hasattr(gi, "start"):
            xs.append(gi.start.X)
            ys.append(gi.start.Y)
        if hasattr(gi, "end"):
            xs.append(gi.end.X)
            ys.append(gi.end.Y)
        if hasattr(gi, "center") and hasattr(gi, "end"):
            cx, cy = gi.center.X, gi.center.Y
            r = math.hypot(gi.end.X - cx, gi.end.Y - cy)
            xs.extend([cx - r, cx + r])
            ys.extend([cy - r, cy + r])

    if not xs:
        return {"type": "none", "error": "Could not parse Edge.Cuts geometry"}

    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    return {
        "type": "polygon_bbox",
        "min_x": round(min_x, 3),
        "min_y": round(min_y, 3),
        "max_x": round(max_x, 3),
        "max_y": round(max_y, 3),
        "width": round(max_x - min_x, 3),
        "height": round(max_y - min_y, 3),
        "segments": len(items),
    }


# ---------------------------------------------------------------------------
# Bounding box computation for footprints
# ---------------------------------------------------------------------------

_BBOX_MIN_DIMENSION_MM = 1.0

_INDUCTOR_DIM_RE = None  # lazy-compiled regex


def _parse_inductor_dims_from_name(name: str) -> Optional[Tuple[float, float]]:
    """Parse physical body dimensions from an inductor footprint name.

    Matches patterns like 'IND-SMD_L7.0-W6.6' → (7.0, 6.6).
    L = body length (along pad axis), W = body width (perpendicular).
    Returns (length, width) or None.
    """
    import re
    global _INDUCTOR_DIM_RE
    if _INDUCTOR_DIM_RE is None:
        _INDUCTOR_DIM_RE = re.compile(r'L(\d+(?:\.\d+)?)-W(\d+(?:\.\d+)?)')

    m = _INDUCTOR_DIM_RE.search(name)
    if m is None:
        return None
    return (float(m.group(1)), float(m.group(2)))


def compute_footprint_bbox(fp) -> Optional[Dict[str, float]]:
    """Compute a footprint's bounding box using courtyard → fab → pad fallback.

    Returns {"width": w, "height": h} in mm at rotation=0 (local coords),
    or None if no geometry is available.

    easyeda2kicad-imported footprints often have tiny courtyard layers
    (e.g. 0.06×0.06mm). If either dimension is below the sanity threshold,
    discard the layer-based bbox and fall through to pad-based calculation.

    For inductors with pads only on two sides (height < width/2), the
    pad-based bbox drastically underestimates the body height. If the
    footprint name contains "L{X}-W{Y}" dimensions, those are merged
    with the pad bbox using max() per axis.
    """
    for layer_pattern in ("CrtYd", "Fab"):
        bbox = _bbox_from_layer(fp.graphicItems, layer_pattern)
        if bbox:
            if bbox["width"] >= _BBOX_MIN_DIMENSION_MM and bbox["height"] >= _BBOX_MIN_DIMENSION_MM:
                return bbox

    bbox = _bbox_from_pads(fp.pads)
    if bbox is None:
        return None

    if bbox["height"] < bbox["width"] / 2:
        fp_name = extract_footprint_name(fp)
        dims = _parse_inductor_dims_from_name(fp_name)
        if dims is not None:
            body_l, body_w = dims
            bbox["width"] = round(max(bbox["width"], body_l), 3)
            bbox["height"] = round(max(bbox["height"], body_w), 3)

    return bbox


def _bbox_from_layer(
    graphic_items: list, layer_pattern: str
) -> Optional[Dict[str, float]]:
    """Compute bounding box from graphic items on a matching layer."""
    xs, ys = [], []
    for gi in graphic_items:
        layer = getattr(gi, "layer", "")
        if layer_pattern not in layer:
            continue
        if hasattr(gi, "start"):
            xs.append(gi.start.X)
            ys.append(gi.start.Y)
        if hasattr(gi, "end"):
            xs.append(gi.end.X)
            ys.append(gi.end.Y)
        if hasattr(gi, "center") and hasattr(gi, "end"):
            cx, cy = gi.center.X, gi.center.Y
            r = math.hypot(gi.end.X - cx, gi.end.Y - cy)
            xs.extend([cx - r, cx + r])
            ys.extend([cy - r, cy + r])

    if not xs:
        return None

    width = round(max(xs) - min(xs), 3)
    height = round(max(ys) - min(ys), 3)
    return {"width": width, "height": height}


def _bbox_from_pads(pads: list) -> Optional[Dict[str, float]]:
    """Compute bounding box from pad positions + pad sizes."""
    if not pads:
        return None

    xs_min, xs_max = [], []
    ys_min, ys_max = [], []
    for pad in pads:
        px = pad.position.X
        py = pad.position.Y
        sw = pad.size.X / 2.0 if hasattr(pad.size, "X") else 0
        sh = pad.size.Y / 2.0 if hasattr(pad.size, "Y") else 0
        xs_min.append(px - sw)
        xs_max.append(px + sw)
        ys_min.append(py - sh)
        ys_max.append(py + sh)

    width = round(max(xs_max) - min(xs_min), 3)
    height = round(max(ys_max) - min(ys_min), 3)
    return {"width": width, "height": height}


def rotated_bbox(
    bbox: Dict[str, float], angle_deg: Optional[float]
) -> Dict[str, float]:
    """Compute the axis-aligned bounding box after rotation.

    Takes a {"width", "height"} at rotation=0 and returns the
    axis-aligned bbox at the given rotation angle.
    """
    if not angle_deg or angle_deg % 180 == 0:
        return bbox

    w, h = bbox["width"], bbox["height"]
    rad = math.radians(angle_deg)
    cos_a = abs(math.cos(rad))
    sin_a = abs(math.sin(rad))
    return {
        "width": round(w * cos_a + h * sin_a, 3),
        "height": round(w * sin_a + h * cos_a, 3),
    }


# ---------------------------------------------------------------------------
# Component extraction
# ---------------------------------------------------------------------------

def extract_footprint_name(fp) -> str:
    """Extract a clean footprint name from the library ID."""
    lib_id = fp.libId or fp.entryName or ""
    if ":" in lib_id:
        return lib_id.split(":", 1)[1]
    return lib_id


def extract_pad_data(fp) -> List[Dict[str, Any]]:
    """Extract pad data with positions transformed to global (board) coordinates.

    KiCad stores pads in footprint-local coordinates. The transform for
    KiCad's Y-down coordinate system with positive rotation as stored:
        gx = fp_x + lx * cos(θ) + ly * sin(θ)
        gy = fp_y - lx * sin(θ) + ly * cos(θ)
    """
    fp_x = fp.position.X
    fp_y = fp.position.Y
    angle_deg = fp.position.angle or 0
    theta = math.radians(angle_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)

    pads = []
    for pad in fp.pads:
        lx = pad.position.X
        ly = pad.position.Y

        gx = fp_x + lx * cos_t + ly * sin_t
        gy = fp_y - lx * sin_t + ly * cos_t

        net_name = ""
        if hasattr(pad, "net") and pad.net is not None:
            net_name = getattr(pad.net, "name", "") or ""

        shape = getattr(pad, "shape", "unknown") or "unknown"

        pads.append({
            "number": pad.number,
            "x": round(gx, 3),
            "y": round(gy, 3),
            "size_x": round(pad.size.X, 3) if hasattr(pad.size, "X") else 0,
            "size_y": round(pad.size.Y, 3) if hasattr(pad.size, "Y") else 0,
            "net": net_name,
            "shape": shape,
        })

    return pads


def extract_components(
    board: Board, include_pads: bool = False,
) -> List[Dict[str, Any]]:
    """Extract all footprints from the board with position and bbox data."""
    components = []
    for fp in board.footprints:
        ref = fp.properties.get("Reference", "")
        value = fp.properties.get("Value", "")
        footprint_name = extract_footprint_name(fp)

        x = round(fp.position.X, 3)
        y = round(fp.position.Y, 3)
        rotation = fp.position.angle or 0

        side = "front" if fp.layer == "F.Cu" else "back"

        local_bbox = compute_footprint_bbox(fp)
        bbox = rotated_bbox(local_bbox, rotation) if local_bbox else None

        comp = {
            "ref": ref,
            "value": value,
            "footprint": footprint_name,
            "x": x,
            "y": y,
            "rotation": rotation,
            "side": side,
        }
        if bbox:
            comp["bbox"] = bbox
        if include_pads:
            comp["pads"] = extract_pad_data(fp)

        components.append(comp)

    components.sort(key=lambda c: _ref_sort_key(c["ref"]))
    return components


def _ref_sort_key(ref: str) -> Tuple[str, int]:
    """Sort references by prefix then numeric suffix (C1 < C2 < C10)."""
    prefix = ref.rstrip("0123456789")
    num_str = ref[len(prefix):]
    try:
        return (prefix, int(num_str))
    except ValueError:
        return (prefix, 0)


# ---------------------------------------------------------------------------
# Unplaced component detection via schematic cross-reference
# ---------------------------------------------------------------------------

def find_schematic_context(pcb_path: Path) -> Optional[Path]:
    """Auto-detect circuit-context.json alongside the PCB file."""
    candidate = pcb_path.parent / "circuit-context.json"
    return candidate if candidate.exists() else None


def load_schematic_refs(ctx_path: Path) -> Dict[str, Dict[str, str]]:
    """Load component ref/value/footprint from circuit-context.json."""
    with open(str(ctx_path)) as f:
        ctx = json.load(f)

    result = {}
    for ref, data in ctx.get("components", {}).items():
        fp_raw = data.get("footprint", "")
        fp_name = fp_raw.split(":", 1)[1] if ":" in fp_raw else fp_raw
        result[ref] = {
            "value": data.get("value", ""),
            "footprint": fp_name,
        }
    return result


def find_unplaced_components(
    pcb_refs: set,
    schematic_ctx_path: Optional[Path],
) -> List[Dict[str, str]]:
    """Identify components in the schematic but not yet in the PCB."""
    if schematic_ctx_path is None:
        return []

    schematic_refs = load_schematic_refs(schematic_ctx_path)
    unplaced_refs = sorted(
        schematic_refs.keys() - pcb_refs,
        key=_ref_sort_key,
    )

    return [
        {
            "ref": ref,
            "value": schematic_refs[ref]["value"],
            "footprint": schematic_refs[ref]["footprint"],
        }
        for ref in unplaced_refs
    ]


# ---------------------------------------------------------------------------
# Board utilization estimate
# ---------------------------------------------------------------------------

def estimate_utilization(
    board_outline: Dict[str, Any],
    components: List[Dict[str, Any]],
) -> Optional[float]:
    """Estimate board utilization as total component bbox area / board area."""
    board_area = board_outline.get("width", 0) * board_outline.get("height", 0)
    if board_area <= 0:
        return None

    component_area = sum(
        c["bbox"]["width"] * c["bbox"]["height"]
        for c in components
        if "bbox" in c
    )
    return round(100.0 * component_area / board_area, 1)


# ---------------------------------------------------------------------------
# Context assembly and output
# ---------------------------------------------------------------------------

def build_context(
    pcb_path: Path,
    raw_pcb_arg: str,
    board: Board,
    schematic_ctx_path: Optional[Path],
    include_pads: bool = False,
) -> Dict[str, Any]:
    """Build the complete pcb-layout-context.json structure."""
    board_outline = extract_board_outline(board)
    placed = extract_components(board, include_pads=include_pads)

    pcb_refs = {c["ref"] for c in placed}
    unplaced = find_unplaced_components(pcb_refs, schematic_ctx_path)

    board_area = board_outline.get("width", 0) * board_outline.get("height", 0)
    utilization = estimate_utilization(board_outline, placed)

    context = {
        "meta": {
            "source_file": raw_pcb_arg,
            "extracted_at": datetime.now(timezone.utc).isoformat(),
            "board_area_mm2": round(board_area, 1),
        },
        "board_outline": board_outline,
        "placed_components": placed,
        "unplaced_components": unplaced,
        "summary": {
            "total_components": len(placed) + len(unplaced),
            "placed": len(placed),
            "unplaced": len(unplaced),
        },
    }

    if utilization is not None:
        context["summary"]["board_utilization_pct"] = utilization

    if schematic_ctx_path:
        context["meta"]["schematic_context"] = str(schematic_ctx_path.name)

    return context


def _compact_json(obj: Any, indent: int = 2) -> str:
    """JSON serializer that puts component-level dicts on fewer lines.

    Top-level structure uses normal indentation. Component entries within
    placed_components and unplaced_components are collapsed to single lines
    for compactness. When pads are present, each component gets a multi-line
    block with pads on individual lines for readability.
    """
    lines = []

    def _dump_component(comp: dict, indent_str: str) -> str:
        if "pads" not in comp:
            return json.dumps(comp, ensure_ascii=False)

        comp_no_pads = {k: v for k, v in comp.items() if k != "pads"}
        base = json.dumps(comp_no_pads, ensure_ascii=False)
        base = base[:-1]  # strip trailing }

        pad_lines = []
        for pad in comp["pads"]:
            pad_lines.append(f"{indent_str}      {json.dumps(pad, ensure_ascii=False)}")

        return (
            base
            + f', "pads": [\n'
            + ",\n".join(pad_lines)
            + f"\n{indent_str}    ]"
            + "}"
        )

    def _dump_component_list(key: str, components: list, indent_str: str) -> None:
        lines.append(f'{indent_str}"{key}": [')
        for i, comp in enumerate(components):
            compact = _dump_component(comp, indent_str)
            comma = "," if i < len(components) - 1 else ""
            lines.append(f"{indent_str}  {compact}{comma}")
        lines.append(f"{indent_str}]")

    lines.append("{")
    top_keys = list(obj.keys())
    for ki, key in enumerate(top_keys):
        is_last = ki == len(top_keys) - 1
        val = obj[key]

        if key in ("placed_components", "unplaced_components"):
            _dump_component_list(key, val, "  ")
            if not is_last:
                lines[-1] += ","
        else:
            dumped = json.dumps(val, indent=indent, ensure_ascii=False)
            if "\n" in dumped:
                indented = dumped.replace("\n", "\n  ")
                entry = f'  "{key}": {indented}'
            else:
                entry = f'  "{key}": {dumped}'
            if not is_last:
                entry += ","
            lines.append(entry)

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
    return pcb.parent / "pcb-layout-context.json"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract PCB layout context from a KiCad board file.",
    )
    parser.add_argument(
        "pcb",
        help="Path to the .kicad_pcb file",
    )
    parser.add_argument(
        "--output", "-o",
        help=(
            "Output path for pcb-layout-context.json "
            "(default: pcb-layout-context.json next to the PCB)"
        ),
    )
    parser.add_argument(
        "--schematic-context",
        help=(
            "Path to circuit-context.json for cross-referencing unplaced "
            "components (auto-detected if present alongside the PCB)"
        ),
    )
    parser.add_argument(
        "--pads",
        action="store_true",
        help="Include per-component pad data (number, global x/y, size, net, shape)",
    )
    args = parser.parse_args()

    pcb_path = resolve_pcb(args.pcb)
    output_path = resolve_output_path(pcb_path, args.output)

    # Load PCB
    print(f"Loading {pcb_path.name}...", file=sys.stderr)
    board = Board.from_file(str(pcb_path))
    print(f"  {len(board.footprints)} footprints loaded", file=sys.stderr)

    # Resolve schematic context for cross-referencing
    schematic_ctx_path = None  # type: Optional[Path]
    if args.schematic_context:
        schematic_ctx_path = Path(args.schematic_context).resolve()
        if not schematic_ctx_path.exists():
            print(
                f"Warning: schematic context not found: {schematic_ctx_path}",
                file=sys.stderr,
            )
            schematic_ctx_path = None
    else:
        schematic_ctx_path = find_schematic_context(pcb_path)

    if schematic_ctx_path:
        print(
            f"  Cross-referencing with {schematic_ctx_path.name}",
            file=sys.stderr,
        )

    # Build and write context
    context = build_context(
        pcb_path, args.pcb, board, schematic_ctx_path,
        include_pads=args.pads,
    )

    write_context_json(context, output_path)

    summary = context["summary"]
    print(
        f"\nWrote {output_path.name} ({output_path.stat().st_size:,} bytes)",
        file=sys.stderr,
    )
    print(
        f"  {summary['placed']} placed, {summary['unplaced']} unplaced, "
        f"{summary['total_components']} total",
        file=sys.stderr,
    )
    if "board_utilization_pct" in summary:
        print(
            f"  Board utilization: {summary['board_utilization_pct']}%",
            file=sys.stderr,
        )


if __name__ == "__main__":
    main()

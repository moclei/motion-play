#!/usr/bin/env python3
"""
routing_audit.py — PCB routing audit (Phase 2 of pcb-routing-audit-tool).

Consumes:
  - pcb-routing-context.json produced by routing_extract.py
  - an audit spec JSON (target_nets, noisy_components, noisy_pads,
    noisy_nets, compare_pair)

Produces:
  - audit report JSON (per-net length + per-noisy-thing min-distance,
    plus an asymmetry diff for the compare_pair)
  - audit report Markdown (rounded to 0.1 mm, table-formatted)

Layer-aware: distance is only computed between geometry on the same
copper layer. The minimum across shared layers wins; the layer is
surfaced in the report.

Out of scope (per BRIEF.md):
  - Pad-to-pad path-distance via segment graph traversal
  - Trace impedance / SI / EM coupling math
  - Cross-PCB diff
  - Editing the .kicad_pcb (this tool is read-only — and reads only
    the extractor's JSON, never the .kicad_pcb directly)

Usage:
    python routing_audit.py --spec audit-specs/v7-main-i2c.json
    python routing_audit.py --spec <spec> --routing-json <path>
    python routing_audit.py --spec <spec> --out-json <path> --out-md <path>
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

from shapely.geometry import (
    LineString,
    MultiLineString,
    Point,
    Polygon,
)


# ---------------------------------------------------------------------------
# Geometry construction
# ---------------------------------------------------------------------------

def build_net_lines_by_layer(
    net_data: Dict[str, Any],
) -> Dict[str, MultiLineString]:
    """Build {layer: MultiLineString} for a single net.

    For 'segment' kinds we use start/end. For 'arc' kinds we use the sampled
    polyline that the extractor stored under 'polyline'. Vias are NOT included
    here — for v1 they're treated as zero-length endpoints (PLAN.md note).
    """
    by_layer: Dict[str, List[LineString]] = defaultdict(list)
    for seg in net_data.get("segments", []):
        layer = seg.get("layer")
        if not layer:
            continue
        kind = seg.get("kind", "segment")
        if kind == "segment":
            sx, sy = seg["start"]
            ex, ey = seg["end"]
            if (sx, sy) == (ex, ey):
                continue  # zero-length segment, skip
            by_layer[layer].append(LineString([(sx, sy), (ex, ey)]))
        elif kind == "arc":
            poly = seg.get("polyline") or [seg["start"], seg["mid"], seg["end"]]
            if len(poly) >= 2:
                by_layer[layer].append(LineString(poly))

    return {
        layer: MultiLineString(lines) if len(lines) > 1 else MultiLineString([lines[0]])
        for layer, lines in by_layer.items()
        if lines
    }


def bbox_dict_to_polygon(bbox: Dict[str, float]) -> Polygon:
    """Convert {min_x, min_y, max_x, max_y} → shapely Polygon."""
    x0, y0 = bbox["min_x"], bbox["min_y"]
    x1, y1 = bbox["max_x"], bbox["max_y"]
    return Polygon([(x0, y0), (x1, y0), (x1, y1), (x0, y1)])


def pad_disk(pad: Dict[str, Any]) -> Point:
    """Return the buffered (Point→disk) representation of a pad on each Cu layer.

    Caller filters layers to copper before computing distance.
    """
    px, py = pad["position"]
    return Point(px, py)


# ---------------------------------------------------------------------------
# Min-distance helpers
# ---------------------------------------------------------------------------

CU_LAYER_SUFFIX = ".Cu"


def _is_cu_layer(layer: str) -> bool:
    return layer.endswith(CU_LAYER_SUFFIX) and layer != "*.Cu"


def _shared_cu_layers(a_layers: List[str], b_layers: List[str]) -> List[str]:
    return [l for l in a_layers if l in b_layers and _is_cu_layer(l)]


def min_distance_net_to_polygon_per_layer(
    net_lines: Dict[str, MultiLineString],
    polygons_by_layer: Dict[str, Polygon],
) -> Optional[Dict[str, Any]]:
    """Min distance from a net's per-layer geometry to a polygon on each shared
    layer. Returns the minimum across layers (with layer name) or None if no
    shared layer exists.
    """
    candidates: List[Tuple[float, str]] = []
    for layer, lines in net_lines.items():
        if not _is_cu_layer(layer):
            continue
        poly = polygons_by_layer.get(layer)
        if poly is None:
            continue
        d = lines.distance(poly)
        candidates.append((d, layer))
    if not candidates:
        return None
    candidates.sort()
    best_d, best_layer = candidates[0]
    return {
        "min_distance_mm": best_d,
        "layer": best_layer,
        "per_layer_mm": {layer: d for d, layer in candidates},
    }


def min_distance_net_to_pad_per_layer(
    net_lines: Dict[str, MultiLineString],
    pad: Dict[str, Any],
) -> Optional[Dict[str, Any]]:
    """Net → pad disk distance per shared Cu layer.

    Pad is represented as Point.buffer(effective_radius). For a pad spanning
    multiple Cu layers (through-hole), the same disk is checked on each
    shared layer.
    """
    pad_layers = [l for l in pad.get("layers", []) if _is_cu_layer(l) or l == "*.Cu"]
    # Expand wildcard
    if "*.Cu" in pad_layers:
        # Use whatever Cu layers the net actually routes on as the candidate set
        pad_layers = [l for l in net_lines.keys() if _is_cu_layer(l)]

    if not pad_layers:
        return None

    eff_r = float(pad.get("effective_radius") or 0.0)
    px, py = pad["position"]
    disk = Point(px, py).buffer(eff_r) if eff_r > 0 else Point(px, py)

    candidates: List[Tuple[float, str]] = []
    for layer in pad_layers:
        lines = net_lines.get(layer)
        if lines is None:
            continue
        d = lines.distance(disk)
        candidates.append((d, layer))

    if not candidates:
        return None
    candidates.sort()
    best_d, best_layer = candidates[0]
    return {
        "min_distance_mm": best_d,
        "layer": best_layer,
        "pad_position": [px, py],
        "effective_radius_mm": eff_r,
        "per_layer_mm": {layer: d for d, layer in candidates},
    }


def min_distance_net_to_net_per_layer(
    a_lines: Dict[str, MultiLineString],
    b_lines: Dict[str, MultiLineString],
) -> Optional[Dict[str, Any]]:
    """Net → net distance per shared Cu layer."""
    candidates: List[Tuple[float, str]] = []
    for layer, a_geom in a_lines.items():
        if not _is_cu_layer(layer):
            continue
        b_geom = b_lines.get(layer)
        if b_geom is None:
            continue
        d = a_geom.distance(b_geom)
        candidates.append((d, layer))
    if not candidates:
        return None
    candidates.sort()
    best_d, best_layer = candidates[0]
    return {
        "min_distance_mm": best_d,
        "layer": best_layer,
        "per_layer_mm": {layer: d for d, layer in candidates},
    }


# ---------------------------------------------------------------------------
# Per-net summary
# ---------------------------------------------------------------------------

def _lookup_footprint(
    footprints: List[Dict[str, Any]], ref: str
) -> Optional[Dict[str, Any]]:
    for fp in footprints:
        if fp.get("ref") == ref:
            return fp
    return None


def _lookup_pad(
    fp: Dict[str, Any], pad_number: str
) -> Optional[Dict[str, Any]]:
    for pad in fp.get("pads", []):
        if str(pad.get("number")) == str(pad_number):
            return pad
    return None


def summarize_net(
    net_name: str,
    routing: Dict[str, Any],
    spec: Dict[str, Any],
    warnings: List[str],
) -> Optional[Dict[str, Any]]:
    """Build the per-net summary block."""
    net_data = routing["nets"].get(net_name)
    if net_data is None:
        warnings.append(f"target net not found in routing JSON: {net_name!r}")
        return None

    net_lines = build_net_lines_by_layer(net_data)

    # Edge case: net has zero segments → no proximities computable
    if not net_lines:
        warnings.append(
            f"net {net_name!r} has zero copper-layer geometry; "
            f"proximities will be empty."
        )

    proximities: Dict[str, Dict[str, Any]] = {}

    footprints = routing.get("footprints", [])

    # Component bbox proximity
    for comp_ref in spec.get("noisy_components", []):
        fp = _lookup_footprint(footprints, comp_ref)
        if fp is None:
            warnings.append(f"noisy_component not found on board: {comp_ref!r}")
            continue
        bbox_by_layer = fp.get("bbox_by_layer") or {}
        if not bbox_by_layer:
            warnings.append(
                f"noisy_component {comp_ref!r} has no per-layer bbox; skipping"
            )
            continue
        polygons = {
            layer: bbox_dict_to_polygon(bbox)
            for layer, bbox in bbox_by_layer.items()
            if _is_cu_layer(layer)
        }
        if not net_lines:
            proximities[comp_ref] = {"note": "net has no copper geometry"}
            continue
        result = min_distance_net_to_polygon_per_layer(net_lines, polygons)
        if result is None:
            proximities[comp_ref] = {
                "note": "no shared Cu layer between net and component bbox"
            }
        else:
            proximities[comp_ref] = result

    # Named pad proximity
    for pad_spec in spec.get("noisy_pads", []):
        ref = pad_spec.get("ref")
        pad_num = pad_spec.get("pad")
        label = pad_spec.get("label") or f"{ref}.pad.{pad_num}"
        key = f"{ref}.pad.{pad_num}"

        fp = _lookup_footprint(footprints, ref)
        if fp is None:
            warnings.append(f"noisy_pad ref not found on board: {ref!r}")
            continue
        pad = _lookup_pad(fp, pad_num)
        if pad is None:
            warnings.append(
                f"noisy_pad {ref}.{pad_num} not found in footprint pads"
            )
            continue
        if not net_lines:
            proximities[key] = {"label": label, "note": "net has no copper geometry"}
            continue
        result = min_distance_net_to_pad_per_layer(net_lines, pad)
        if result is None:
            proximities[key] = {
                "label": label,
                "note": "no shared Cu layer between net and pad",
            }
        else:
            result["label"] = label
            proximities[key] = result

    # Net proximity
    for other_net in spec.get("noisy_nets", []):
        if other_net == net_name:
            continue  # don't compare a net to itself
        other_data = routing["nets"].get(other_net)
        if other_data is None:
            warnings.append(f"noisy_net not found in routing JSON: {other_net!r}")
            continue
        other_lines = build_net_lines_by_layer(other_data)
        if not other_lines:
            proximities[other_net] = {"note": "other net has no copper geometry"}
            continue
        if not net_lines:
            proximities[other_net] = {"note": "net has no copper geometry"}
            continue
        result = min_distance_net_to_net_per_layer(net_lines, other_lines)
        if result is None:
            proximities[other_net] = {
                "note": "no shared Cu layer between nets"
            }
        else:
            proximities[other_net] = result

    return {
        "name": net_name,
        "total_length_mm": net_data.get("total_length_mm", 0.0),
        "length_by_layer": net_data.get("length_by_layer", {}),
        "segment_count": len(net_data.get("segments", [])),
        "via_count": len(net_data.get("vias", [])),
        "proximities": proximities,
    }


# ---------------------------------------------------------------------------
# Asymmetry diff
# ---------------------------------------------------------------------------

def build_asymmetry(
    net_summaries: Dict[str, Dict[str, Any]],
    pair: List[str],
) -> Optional[Dict[str, Any]]:
    """Diff length + every proximity row between the two named nets.

    Returns None if either net wasn't summarized.
    """
    if len(pair) != 2:
        return None
    a_name, b_name = pair
    a = net_summaries.get(a_name)
    b = net_summaries.get(b_name)
    if a is None or b is None:
        return None

    diffs: List[Dict[str, Any]] = []

    # Total length
    a_len = a["total_length_mm"]
    b_len = b["total_length_mm"]
    diffs.append({
        "metric": "total_length_mm",
        "a": a_len,
        "b": b_len,
        "delta_a_minus_b": round(a_len - b_len, 4),
    })

    # Per-proximity-key min distance
    keys = sorted(set(a["proximities"]) | set(b["proximities"]))
    for key in keys:
        a_prox = a["proximities"].get(key, {})
        b_prox = b["proximities"].get(key, {})
        a_d = a_prox.get("min_distance_mm")
        b_d = b_prox.get("min_distance_mm")
        delta: Optional[float] = None
        if a_d is not None and b_d is not None:
            delta = round(a_d - b_d, 4)
        diffs.append({
            "metric": f"min_distance_to_{key}_mm",
            "a": a_d,
            "a_layer": a_prox.get("layer"),
            "b": b_d,
            "b_layer": b_prox.get("layer"),
            "delta_a_minus_b": delta,
            "label": a_prox.get("label") or b_prox.get("label"),
        })

    return {
        "pair": [a_name, b_name],
        "diffs": diffs,
    }


# ---------------------------------------------------------------------------
# Markdown formatter
# ---------------------------------------------------------------------------

def _r1(value: Optional[float]) -> str:
    """Round to 0.1 mm for Markdown; return em-dash if None."""
    if value is None:
        return "—"
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return "—"


def _length_by_layer_str(lbl: Dict[str, float]) -> str:
    if not lbl:
        return "—"
    return ", ".join(f"{layer} {_r1(v)}" for layer, v in sorted(lbl.items()))


def render_markdown(
    report: Dict[str, Any],
    spec: Dict[str, Any],
) -> str:
    out: List[str] = []
    pcb_label = spec.get("pcb") or report["meta"].get("pcb") or "(unknown PCB)"
    out.append(f"## Routing audit — {pcb_label}")
    out.append("")
    out.append(f"_Generated_: {report['meta']['generated_at']}")
    out.append(f"_Spec_: `{report['meta']['spec']}`")
    out.append(f"_Routing context_: `{report['meta']['routing_context']}`")
    out.append("")

    # Per-net sections
    nets = report["nets"]
    for net_name in spec.get("target_nets", []):
        net = nets.get(net_name)
        if net is None:
            out.append(f"### Net `{net_name}`")
            out.append("")
            out.append("_Not present in routing JSON — see warnings._")
            out.append("")
            continue

        out.append(f"### Net `{net_name}`")
        out.append("")
        out.append(
            f"- Total length: **{_r1(net['total_length_mm'])} mm** "
            f"({_length_by_layer_str(net['length_by_layer'])})"
        )
        out.append(
            f"- Segments: {net['segment_count']}, vias: {net['via_count']}"
        )

        if not net["proximities"]:
            out.append("- _No proximities computed (empty noisy lists or no copper geometry)._")
            out.append("")
            continue

        # Render proximities in spec order: components, pads, nets
        rendered_keys: set = set()

        for comp_ref in spec.get("noisy_components", []):
            if comp_ref not in net["proximities"]:
                continue
            rendered_keys.add(comp_ref)
            prox = net["proximities"][comp_ref]
            if "min_distance_mm" in prox:
                out.append(
                    f"- Min clearance to component `{comp_ref}`: "
                    f"**{_r1(prox['min_distance_mm'])} mm** ({prox['layer']})"
                )
            else:
                out.append(
                    f"- Min clearance to component `{comp_ref}`: "
                    f"_{prox.get('note', 'n/a')}_"
                )

        for pad_spec in spec.get("noisy_pads", []):
            key = f"{pad_spec['ref']}.pad.{pad_spec['pad']}"
            if key not in net["proximities"]:
                continue
            rendered_keys.add(key)
            prox = net["proximities"][key]
            label = prox.get("label") or key
            if "min_distance_mm" in prox:
                out.append(
                    f"- Min clearance to {label}: "
                    f"**{_r1(prox['min_distance_mm'])} mm** ({prox['layer']})"
                )
            else:
                out.append(
                    f"- Min clearance to {label}: _{prox.get('note', 'n/a')}_"
                )

        for other_net in spec.get("noisy_nets", []):
            if other_net not in net["proximities"]:
                continue
            rendered_keys.add(other_net)
            prox = net["proximities"][other_net]
            if "min_distance_mm" in prox:
                out.append(
                    f"- Min clearance to net `{other_net}`: "
                    f"**{_r1(prox['min_distance_mm'])} mm** ({prox['layer']})"
                )
            else:
                out.append(
                    f"- Min clearance to net `{other_net}`: "
                    f"_{prox.get('note', 'n/a')}_"
                )

        # Anything else (defensive)
        for key, prox in net["proximities"].items():
            if key in rendered_keys:
                continue
            if "min_distance_mm" in prox:
                out.append(
                    f"- Min clearance to `{key}`: "
                    f"**{_r1(prox['min_distance_mm'])} mm** ({prox['layer']})"
                )
            else:
                out.append(
                    f"- Min clearance to `{key}`: _{prox.get('note', 'n/a')}_"
                )

        out.append("")

    # Asymmetry table
    asymmetry = report.get("asymmetry")
    if asymmetry:
        a_name, b_name = asymmetry["pair"]
        out.append(f"### Asymmetry (`{a_name}` vs `{b_name}`)")
        out.append("")
        out.append(
            "| Metric | "
            f"{a_name} | {b_name} | Δ (a − b) |"
        )
        out.append("|---|---:|---:|---:|")
        for row in asymmetry["diffs"]:
            metric = row["metric"]
            label = row.get("label")
            display_metric = metric
            if label and metric.startswith("min_distance_to_"):
                display_metric = f"Min dist to {label} (mm)"
            elif metric.startswith("min_distance_to_"):
                key = metric[len("min_distance_to_"):-len("_mm")]
                display_metric = f"Min dist to {key} (mm)"
            elif metric == "total_length_mm":
                display_metric = "Total length (mm)"

            a_layer = row.get("a_layer")
            b_layer = row.get("b_layer")
            a_val = _r1(row.get("a"))
            b_val = _r1(row.get("b"))
            if a_layer:
                a_val = f"{a_val} ({a_layer})"
            if b_layer:
                b_val = f"{b_val} ({b_layer})"
            delta = row.get("delta_a_minus_b")
            delta_str = _r1(delta) if delta is not None else "—"
            if delta is not None and delta > 0:
                delta_str = f"+{delta_str}"
            out.append(f"| {display_metric} | {a_val} | {b_val} | {delta_str} |")
        out.append("")

    # Warnings
    warnings = report.get("warnings") or []
    if warnings:
        out.append("### Warnings")
        out.append("")
        for w in warnings:
            out.append(f"- {w}")
        out.append("")

    return "\n".join(out) + "\n"


# ---------------------------------------------------------------------------
# Driver
# ---------------------------------------------------------------------------

def load_json(path: Path) -> Dict[str, Any]:
    with open(str(path)) as f:
        return json.load(f)


def resolve_routing_json(spec: Dict[str, Any], spec_path: Path,
                        explicit: Optional[str], repo_root: Path) -> Path:
    if explicit:
        return Path(explicit).resolve()
    rel = spec.get("routing_context")
    if rel:
        # Try interpreted as repo-rooted, then as cwd-relative, then as spec-relative
        for candidate in [
            repo_root / rel,
            Path(rel),
            spec_path.parent / rel,
        ]:
            p = Path(candidate).resolve()
            if p.exists():
                return p
    # Fallback: alongside the .kicad_pcb mentioned in spec
    pcb_rel = spec.get("pcb")
    if pcb_rel:
        candidate = (repo_root / pcb_rel).with_name("pcb-routing-context.json")
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate pcb-routing-context.json. "
        "Pass --routing-json explicitly, or set 'routing_context' in the spec."
    )


def find_repo_root(start: Path) -> Path:
    """Walk up until we find .git or hit the filesystem root."""
    p = start.resolve()
    for _ in range(8):
        if (p / ".git").exists():
            return p
        if p.parent == p:
            break
        p = p.parent
    # Fallback: assume the script is in tools/pcb-context/, repo is two up
    return start.resolve().parents[2] if len(start.resolve().parents) >= 3 else start.resolve()


def run_audit(
    spec_path: Path,
    routing_json: Optional[str],
    out_json: Optional[str],
    out_md: Optional[str],
) -> Tuple[Path, Path]:
    spec = load_json(spec_path)
    repo_root = find_repo_root(Path(__file__).parent)
    routing_path = resolve_routing_json(spec, spec_path, routing_json, repo_root)

    print(f"Spec:    {spec_path}", file=sys.stderr)
    print(f"Routing: {routing_path}", file=sys.stderr)

    routing = load_json(routing_path)

    warnings: List[str] = []

    net_summaries: Dict[str, Dict[str, Any]] = {}
    for net_name in spec.get("target_nets", []):
        summary = summarize_net(net_name, routing, spec, warnings)
        if summary is not None:
            net_summaries[net_name] = summary

    asymmetry = build_asymmetry(net_summaries, spec.get("compare_pair", []))

    report = {
        "meta": {
            "spec": str(spec_path.name),
            "spec_full_path": str(spec_path),
            "pcb": spec.get("pcb"),
            "routing_context": str(routing_path),
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schema_version": 1,
        },
        "nets": net_summaries,
        "asymmetry": asymmetry,
        "warnings": warnings,
    }

    # Default output paths: alongside the spec, with the spec stem as prefix
    if out_json:
        out_json_path = Path(out_json).resolve()
    else:
        out_json_path = spec_path.parent / f"{spec_path.stem}.audit.json"
    if out_md:
        out_md_path = Path(out_md).resolve()
    else:
        out_md_path = spec_path.parent / f"{spec_path.stem}.audit.md"

    with open(str(out_json_path), "w") as f:
        json.dump(report, f, indent=2)
        f.write("\n")
    md = render_markdown(report, spec)
    with open(str(out_md_path), "w") as f:
        f.write(md)

    print(f"\nWrote {out_json_path}", file=sys.stderr)
    print(f"      {out_md_path}", file=sys.stderr)

    if warnings:
        print(f"\n{len(warnings)} warning(s):", file=sys.stderr)
        for w in warnings:
            print(f"  - {w}", file=sys.stderr)

    return out_json_path, out_md_path


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Audit PCB routing against an audit spec. Reads the JSON produced "
            "by routing_extract.py (never the .kicad_pcb directly). Writes a "
            "machine-readable JSON report and a human-readable Markdown report."
        ),
    )
    parser.add_argument(
        "--spec",
        required=True,
        help="Path to the audit spec JSON (e.g. audit-specs/v7-main-i2c.json)",
    )
    parser.add_argument(
        "--routing-json",
        help=(
            "Path to pcb-routing-context.json. If omitted, resolved from the "
            "spec's 'routing_context' field, then from the spec's 'pcb' "
            "sibling."
        ),
    )
    parser.add_argument(
        "--out-json",
        help=(
            "Output path for the audit JSON report. "
            "Default: <spec_dir>/<spec_stem>.audit.json"
        ),
    )
    parser.add_argument(
        "--out-md",
        help=(
            "Output path for the audit Markdown report. "
            "Default: <spec_dir>/<spec_stem>.audit.md"
        ),
    )
    args = parser.parse_args()

    spec_path = Path(args.spec).resolve()
    if not spec_path.exists():
        print(f"Error: audit spec not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    run_audit(spec_path, args.routing_json, args.out_json, args.out_md)


if __name__ == "__main__":
    main()

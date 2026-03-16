#!/usr/bin/env python3
"""
place_power.py — Automated power section component placement.

Reads enriched pcb-layout-context.json (with --pads data) and spec.json,
computes optimal positions for ~39 power support components relative to
manually-placed anchor ICs, and writes results to the .kicad_pcb file
via kiutils.

Prerequisites:
    python extract.py <pcb> --pads    (generates enriched context)

Usage:
    python place_power.py <file.kicad_pcb>
    python place_power.py <file.kicad_pcb> --dry-run
    python place_power.py <file.kicad_pcb> --context path/to/context.json
    python place_power.py <file.kicad_pcb> --spec path/to/spec.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ANCHOR_REFS = frozenset({"U5", "U6", "J7", "J8", "L1", "L2", "R44"})

BOARD_MIN_X, BOARD_MIN_Y = 62.6, 101.0
BOARD_MAX_X, BOARD_MAX_Y = 164.0, 141.0
POWER_MAX_X = 105.0
CLEARANCE = 0.3  # mm minimum gap between component bboxes

# Tier assignments: ref → (tier, max_distance_mm, anchor_ref, target_nets)
# target_nets are spec.json net names used to locate the specific anchor pad(s)
TIER_MAP: Dict[str, Tuple[int, float, str, List[str]]] = {
    # Tier 1 — Critical: switching loop area minimization
    "C23": (1, 3.0, "U5", ["BQ_BTST"]),
    "C32": (1, 3.0, "U6", ["BOOST_BOOT"]),

    # Tier 2 — Important: bulk decoupling effectiveness
    "C20": (2, 5.0, "U5", ["Protected_VBUS"]),
    "C21": (2, 5.0, "U5", ["Protected_VBUS"]),
    "C25": (2, 5.0, "U5", ["BQ_PMID"]),
    "C26": (2, 5.0, "U5", ["BQ_PMID"]),
    "C34": (2, 6.0, "U6", ["+5V"]),
    "C35": (2, 6.0, "U6", ["+5V"]),
    "C36": (2, 6.0, "U6", ["+5V"]),
    "C41": (2, 5.0, "U6", ["VSYS_SENSE"]),
    "C31": (2, 5.0, "U6", ["VSYS_SENSE"]),

    # Tier 3 — Moderate: signal integrity, not switching-critical
    "R39": (3, 10.0, "U6", ["BOOST_FB"]),
    "R40": (3, 10.0, "U6", ["BOOST_FB"]),
    "R43": (3, 10.0, "U6", ["BOOST_COMP"]),
    "C38": (3, 10.0, "U6", ["BOOST_COMP"]),
    "C39": (3, 10.0, "U6", ["BOOST_COMP"]),
    "C24": (3, 10.0, "U5", ["BQ_REGN"]),
    "C27": (3, 10.0, "U5", ["VSYS"]),
    "C28": (3, 10.0, "U5", ["VSYS"]),
    "R32": (3, 10.0, "U5", ["BQ_ILIM"]),
    "C33": (3, 10.0, "U6", ["BOOST_VCC"]),
    "C37": (3, 10.0, "U6", ["BOOST_SS"]),
    "R41": (3, 10.0, "U6", ["BOOST_FSW"]),
    "R42": (3, 10.0, "U6", ["BOOST_ILIM"]),
    "F2":  (3, 10.0, "J7", ["VBUS_RAW"]),
    "R30": (3, 10.0, "J7", ["CC1"]),
    "R31": (3, 10.0, "J7", ["CC2"]),
    "Q2":  (3, 10.0, "J8", ["BAT_RAW"]),
    "U7":  (3, 10.0, "R44", ["VSYS_SENSE"]),

    # Tier 4 — Flexible: large passives, bias networks, misc
    "C29": (4, 20.0, "U5", ["VSYS"]),
    "C22": (4, 20.0, "J7", ["VBUS_RAW"]),
    "C30": (4, 15.0, "J8", ["BAT_RAW"]),
    "R33": (4, 15.0, "U5", ["VBAT"]),
    "R34": (4, 15.0, "J8", ["BAT_RAW"]),
    "R35": (4, 15.0, "U5", ["OTG_BIAS"]),
    "R38": (4, 15.0, "U5", ["CHRG_INT"]),
    "TH1": (4, 15.0, "U5", ["BQ_TS"]),
    "R36": (4, 15.0, "U5", ["BQ_TS"]),
    "R37": (4, 15.0, "U5", ["BQ_TS"]),
    "C40": (4, 15.0, "R44", ["VSYS"]),
}

TEST_POINT_REFS = ["TP1", "TP2", "TP3", "TP4"]


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class Rect:
    """Axis-aligned bounding box centered at (cx, cy)."""
    cx: float
    cy: float
    w: float
    h: float

    @property
    def left(self) -> float:
        return self.cx - self.w / 2

    @property
    def right(self) -> float:
        return self.cx + self.w / 2

    @property
    def top(self) -> float:
        return self.cy - self.h / 2

    @property
    def bottom(self) -> float:
        return self.cy + self.h / 2

    def overlaps(self, other: Rect, margin: float = 0) -> bool:
        """True if rects overlap or the gap between them is less than margin."""
        return (self.left - margin < other.right and
                self.right + margin > other.left and
                self.top - margin < other.bottom and
                self.bottom + margin > other.top)

    def within_bounds(self, min_x: float, min_y: float,
                      max_x: float, max_y: float) -> bool:
        return (self.left >= min_x and self.right <= max_x and
                self.top >= min_y and self.bottom <= max_y)


@dataclass
class PadInfo:
    number: str
    x: float
    y: float
    net: str


@dataclass
class CompInfo:
    ref: str
    value: str
    x: float
    y: float
    rotation: float
    bbox_w: float
    bbox_h: float
    pads: List[PadInfo] = field(default_factory=list)

    def rect(self) -> Rect:
        return Rect(self.x, self.y, self.bbox_w, self.bbox_h)


@dataclass
class Placement:
    ref: str
    x: float
    y: float
    rotation: float
    old_x: float
    old_y: float
    old_rotation: float
    tier: int
    note: str


# ---------------------------------------------------------------------------
# Net name normalization
# ---------------------------------------------------------------------------

def normalize_net(net: str) -> str:
    """Strip hierarchical path prefix from PCB net names.

    '/Power Management/BOOST_SW' → 'BOOST_SW'
    'GND' → 'GND', '+5V' → '+5V'
    """
    if not net:
        return ""
    parts = net.rsplit("/", 1)
    return parts[-1] if len(parts) > 1 else net


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_pcb_context(path: Path) -> Dict[str, Any]:
    with open(str(path)) as f:
        data = json.load(f)

    if "placed_components" not in data:
        print("Error: PCB context missing 'placed_components'", file=sys.stderr)
        print("  Run: python extract.py <pcb> --pads", file=sys.stderr)
        sys.exit(1)

    has_pads = any("pads" in c for c in data["placed_components"])
    if not has_pads:
        print("Error: PCB context missing pad data", file=sys.stderr)
        print("  Run: python extract.py <pcb> --pads", file=sys.stderr)
        sys.exit(1)

    return data


def load_spec(path: Path) -> Dict[str, Any]:
    with open(str(path)) as f:
        return json.load(f)


def build_comp_index(pcb_ctx: Dict[str, Any]) -> Dict[str, CompInfo]:
    """Build a ref → CompInfo index from PCB context data."""
    index: Dict[str, CompInfo] = {}
    for c in pcb_ctx["placed_components"]:
        pads = []
        for p in c.get("pads", []):
            if p.get("number"):
                pads.append(PadInfo(
                    number=p["number"],
                    x=p["x"],
                    y=p["y"],
                    net=normalize_net(p.get("net", "")),
                ))
        bbox = c.get("bbox", {})
        index[c["ref"]] = CompInfo(
            ref=c["ref"],
            value=c.get("value", ""),
            x=c["x"],
            y=c["y"],
            rotation=c.get("rotation", 0),
            bbox_w=bbox.get("width", 2.0),
            bbox_h=bbox.get("height", 2.0),
            pads=pads,
        )
    return index


def get_power_refs(spec: Dict[str, Any]) -> set:
    """Get component refs from spec.json (power section)."""
    refs = set()
    for entry in spec.get("components", []):
        ref = entry.get("ref", "")
        if ref and not ref.startswith("#"):
            refs.add(ref)
    return refs


# ---------------------------------------------------------------------------
# U6 rotation fix
# ---------------------------------------------------------------------------

def fix_u6_rotation(comp_index: Dict[str, CompInfo]) -> bool:
    """Rotate U6 from -90° to +90° by mirroring pad positions around center.

    Going from -90° to +90° is a 180° rotation of pad positions around
    the IC center, which flips SW pins from the left (board edge) to the
    right (board interior), making room for L2.

    Returns True if the fix was applied.
    """
    u6 = comp_index.get("U6")
    if u6 is None or u6.rotation != -90:
        return False

    cx, cy = u6.x, u6.y
    for pad in u6.pads:
        pad.x = round(2 * cx - pad.x, 3)
        pad.y = round(2 * cy - pad.y, 3)
    u6.rotation = 90
    return True


# ---------------------------------------------------------------------------
# Net-to-pad resolver
# ---------------------------------------------------------------------------

def find_anchor_pads(anchor: CompInfo, target_nets: List[str],
                     ) -> Optional[Tuple[float, float]]:
    """Find the centroid of anchor pads matching any target net.

    Returns (x, y) or None if no matching pads found.
    """
    matches = [(p.x, p.y) for p in anchor.pads if p.net in target_nets]
    if not matches:
        return None
    avg_x = sum(x for x, _ in matches) / len(matches)
    avg_y = sum(y for _, y in matches) / len(matches)
    return (avg_x, avg_y)


# ---------------------------------------------------------------------------
# Collision detection and position search
# ---------------------------------------------------------------------------

def is_valid_position(cx: float, cy: float, w: float, h: float,
                      occupied: List[Rect], x_max: float) -> bool:
    """Check if a component at (cx, cy) with bbox (w, h) is validly placed."""
    candidate = Rect(cx, cy, w, h)

    if not candidate.within_bounds(BOARD_MIN_X, BOARD_MIN_Y,
                                   BOARD_MAX_X, BOARD_MAX_Y):
        return False

    if candidate.right > x_max:
        return False

    for occ in occupied:
        if candidate.overlaps(occ, CLEARANCE):
            return False

    return True


def find_position(target_x: float, target_y: float,
                  anchor_x: float, anchor_y: float,
                  comp_w: float, comp_h: float,
                  max_dist: float, occupied: List[Rect],
                  x_max: float = POWER_MAX_X,
                  step: float = 0.5) -> Optional[Tuple[float, float]]:
    """Find a collision-free position near (target_x, target_y).

    Searches in expanding rings around the target, preferring the
    direction away from the anchor IC center. Returns (x, y) or None.
    """
    if is_valid_position(target_x, target_y, comp_w, comp_h, occupied, x_max):
        return (target_x, target_y)

    dx = target_x - anchor_x
    dy = target_y - anchor_y
    mag = math.hypot(dx, dy) or 1.0
    ux, uy = dx / mag, dy / mag

    r = step
    while r <= max_dist:
        n_angles = max(12, int(2 * math.pi * r / step))
        best = None
        best_score = float("inf")

        for i in range(n_angles):
            angle = 2 * math.pi * i / n_angles
            ox = r * math.cos(angle)
            oy = r * math.sin(angle)
            cx = target_x + ox
            cy = target_y + oy

            if not is_valid_position(cx, cy, comp_w, comp_h, occupied, x_max):
                continue

            dot = (ox * ux + oy * uy) / r if r > 0 else 0
            score = r * (1.0 - 0.4 * dot)

            if score < best_score:
                best = (cx, cy)
                best_score = score

        if best is not None:
            return best
        r += step

    return None


# ---------------------------------------------------------------------------
# Test point placement
# ---------------------------------------------------------------------------

def place_test_points(tp_refs: List[str], comp_index: Dict[str, CompInfo],
                      occupied: List[Rect]) -> List[Placement]:
    """Place test points along the bottom edge for probe access."""
    placements = []
    x_start = 67.0
    x_step = 4.0
    y_target = 139.5

    for i, ref in enumerate(tp_refs):
        comp = comp_index.get(ref)
        if comp is None:
            continue

        target_x = x_start + i * x_step
        pos = find_position(
            target_x, y_target, target_x, BOARD_MIN_Y,
            comp.bbox_w, comp.bbox_h, 15.0, occupied,
            x_max=POWER_MAX_X, step=0.5,
        )

        if pos is None:
            print(f"  WARNING: no valid position for {ref}", file=sys.stderr)
            continue

        placements.append(Placement(
            ref=ref, x=round(pos[0], 3), y=round(pos[1], 3),
            rotation=comp.rotation,
            old_x=comp.x, old_y=comp.y, old_rotation=comp.rotation,
            tier=5, note="test point, bottom edge",
        ))
        occupied.append(Rect(pos[0], pos[1], comp.bbox_w, comp.bbox_h))

    return placements


# ---------------------------------------------------------------------------
# Main placement engine
# ---------------------------------------------------------------------------

def run_placement(comp_index: Dict[str, CompInfo],
                  power_refs: set) -> Tuple[List[Placement], List[str]]:
    """Execute the tiered placement algorithm.

    Returns (placements, warnings).
    """
    placements: List[Placement] = []
    warnings: List[str] = []

    # Initialize occupied set with all anchors + all non-power components
    occupied: List[Rect] = []
    for ref, comp in comp_index.items():
        if ref in ANCHOR_REFS or ref not in power_refs:
            occupied.append(comp.rect())

    # Apply U6 rotation fix before computing placements
    if fix_u6_rotation(comp_index):
        u6 = comp_index["U6"]
        placements.append(Placement(
            ref="U6", x=u6.x, y=u6.y, rotation=90,
            old_x=u6.x, old_y=u6.y, old_rotation=-90,
            tier=0, note="rotation fix: -90° → +90° (SW pins face board interior)",
        ))
        print(f"  U6: rotation -90° → +90°", file=sys.stderr)

    # Build tier-ordered work list
    tier_items: List[Tuple[int, str, float, str, List[str]]] = []
    for ref, (tier, max_dist, anchor_ref, nets) in TIER_MAP.items():
        if ref in comp_index:
            tier_items.append((tier, ref, max_dist, anchor_ref, nets))
    tier_items.sort(key=lambda t: (t[0], t[1]))

    # Place each component in tier order
    for tier, ref, max_dist, anchor_ref, target_nets in tier_items:
        comp = comp_index[ref]
        anchor = comp_index.get(anchor_ref)

        if anchor is None:
            msg = f"{ref}: anchor {anchor_ref} not found in PCB"
            warnings.append(msg)
            print(f"  WARNING: {msg}", file=sys.stderr)
            continue

        pad_pos = find_anchor_pads(anchor, target_nets)
        if pad_pos is None:
            pad_pos = (anchor.x, anchor.y)
            msg = f"{ref}: no pads matching {target_nets} on {anchor_ref}, using center"
            warnings.append(msg)
            print(f"  note: {msg}", file=sys.stderr)

        target_x, target_y = pad_pos

        # Try placement within power zone
        pos = find_position(
            target_x, target_y, anchor.x, anchor.y,
            comp.bbox_w, comp.bbox_h, max_dist, occupied,
            x_max=POWER_MAX_X,
        )

        # Relaxation: double distance, remove power zone constraint
        if pos is None:
            pos = find_position(
                target_x, target_y, anchor.x, anchor.y,
                comp.bbox_w, comp.bbox_h, max_dist * 2, occupied,
                x_max=BOARD_MAX_X,
            )
            if pos is not None:
                msg = f"{ref}: relaxed to {max_dist * 2:.0f}mm / full board"
                warnings.append(msg)
                print(f"  WARNING: {msg}", file=sys.stderr)

        if pos is None:
            msg = f"{ref}: FAILED to place (tier {tier}, anchor {anchor_ref})"
            warnings.append(msg)
            print(f"  ERROR: {msg}", file=sys.stderr)
            continue

        dist = math.hypot(pos[0] - target_x, pos[1] - target_y)
        placements.append(Placement(
            ref=ref,
            x=round(pos[0], 3),
            y=round(pos[1], 3),
            rotation=comp.rotation,
            old_x=comp.x, old_y=comp.y, old_rotation=comp.rotation,
            tier=tier,
            note=f"near {anchor_ref} {'/'.join(target_nets)}, {dist:.1f}mm",
        ))
        occupied.append(Rect(pos[0], pos[1], comp.bbox_w, comp.bbox_h))
        print(
            f"  {ref}: ({pos[0]:.1f}, {pos[1]:.1f}) tier {tier}, "
            f"{dist:.1f}mm from {anchor_ref} pad",
            file=sys.stderr,
        )

    # Place test points last (lowest priority)
    tp_placements = place_test_points(TEST_POINT_REFS, comp_index, occupied)
    placements.extend(tp_placements)
    for tp in tp_placements:
        print(f"  {tp.ref}: ({tp.x:.1f}, {tp.y:.1f}) {tp.note}", file=sys.stderr)

    return placements, warnings


# ---------------------------------------------------------------------------
# PCB write via kiutils
# ---------------------------------------------------------------------------

def write_placements_to_pcb(pcb_path: Path,
                            placements: List[Placement]) -> None:
    """Update component positions/rotations in the .kicad_pcb file.

    Uses text-based replacement to preserve KiCad 9 file formatting.
    kiutils v1.4.8 rewrites uuid→tstamp and reformats the whole file,
    so we avoid its write path entirely.
    """
    import re

    text = pcb_path.read_text()
    placement_map = {p.ref: p for p in placements}
    updated = 0

    for ref, p in placement_map.items():
        pattern = re.compile(
            r'(\(property\s+"Reference"\s+"' + re.escape(ref) + r'")'
        )
        match = pattern.search(text)
        if match is None:
            print(f"  WARNING: {ref} not found in PCB file", file=sys.stderr)
            continue

        ref_pos = match.start()
        block_start = text.rfind("(footprint", 0, ref_pos)
        if block_start == -1:
            print(f"  WARNING: no footprint block for {ref}", file=sys.stderr)
            continue

        at_pattern = re.compile(r'\(at\s+[\d.\-]+\s+[\d.\-]+(?:\s+[\d.\-]+)?\)')
        at_match = at_pattern.search(text, block_start, ref_pos)
        if at_match is None:
            print(f"  WARNING: no (at ...) for {ref}", file=sys.stderr)
            continue

        if p.rotation == 0:
            new_at = f"(at {p.x} {p.y})"
        else:
            new_at = f"(at {p.x} {p.y} {p.rotation})"

        text = text[:at_match.start()] + new_at + text[at_match.end():]
        updated += 1

    pcb_path.write_text(text)
    print(f"\nWrote {updated} component positions to {pcb_path.name}",
          file=sys.stderr)


# ---------------------------------------------------------------------------
# Output formatting
# ---------------------------------------------------------------------------

def build_report(placements: List[Placement],
                 warnings: List[str]) -> Dict[str, Any]:
    """Build a JSON-serializable placement report."""
    return {
        "placements": [
            {
                "ref": p.ref,
                "x": p.x, "y": p.y, "rotation": p.rotation,
                "old_x": p.old_x, "old_y": p.old_y,
                "old_rotation": p.old_rotation,
                "tier": p.tier,
                "note": p.note,
            }
            for p in placements
        ],
        "warnings": warnings,
        "summary": {
            "placed": len(placements),
            "failed": sum(1 for w in warnings if "FAILED" in w),
            "relaxed": sum(1 for w in warnings if "relaxed" in w),
        },
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Place power section components on the PCB.",
    )
    parser.add_argument("pcb", help="Path to the .kicad_pcb file")
    parser.add_argument(
        "--context",
        help="Path to pcb-layout-context.json (default: alongside PCB)",
    )
    parser.add_argument(
        "--spec",
        help="Path to spec.json (default: tools/schematic-gen/spec.json)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Output proposed positions as JSON without writing to PCB",
    )
    args = parser.parse_args()

    pcb_path = Path(args.pcb).resolve()
    if not pcb_path.exists():
        print(f"Error: PCB file not found: {pcb_path}", file=sys.stderr)
        sys.exit(1)

    # Resolve context JSON
    if args.context:
        ctx_path = Path(args.context).resolve()
    else:
        ctx_path = pcb_path.parent / "pcb-layout-context.json"
    if not ctx_path.exists():
        print(f"Error: PCB context not found: {ctx_path}", file=sys.stderr)
        print("  Run: python extract.py <pcb> --pads", file=sys.stderr)
        sys.exit(1)

    # Resolve spec.json
    if args.spec:
        spec_path = Path(args.spec).resolve()
    else:
        spec_path = Path(__file__).resolve().parent.parent / "schematic-gen" / "spec.json"
    if not spec_path.exists():
        print(f"Error: spec.json not found: {spec_path}", file=sys.stderr)
        sys.exit(1)

    # Load data
    print(f"Loading PCB context: {ctx_path.name}", file=sys.stderr)
    pcb_ctx = load_pcb_context(ctx_path)

    print(f"Loading spec: {spec_path.name}", file=sys.stderr)
    spec = load_spec(spec_path)

    comp_index = build_comp_index(pcb_ctx)
    power_refs = get_power_refs(spec)

    n_anchors = len(ANCHOR_REFS & set(comp_index.keys()))
    to_place = power_refs - ANCHOR_REFS - set(TEST_POINT_REFS)
    to_place_present = to_place & set(comp_index.keys())
    assigned = to_place_present & set(TIER_MAP.keys())

    print(f"  {len(comp_index)} components in PCB, "
          f"{len(power_refs)} in power section", file=sys.stderr)
    print(f"  {n_anchors} anchors locked, "
          f"{len(to_place_present)} to place "
          f"({len(assigned)} with tier assignments)", file=sys.stderr)

    unassigned = to_place_present - set(TIER_MAP.keys())
    if unassigned:
        print(f"  WARNING: no tier assignment for: "
              f"{', '.join(sorted(unassigned))}", file=sys.stderr)

    # Run placement
    print("\nPlacing components...", file=sys.stderr)
    placements, warnings = run_placement(comp_index, power_refs)

    report = build_report(placements, warnings)

    if args.dry_run:
        print(json.dumps(report, indent=2))
        print(f"\nDry run: {len(placements)} placements proposed",
              file=sys.stderr)
    else:
        write_placements_to_pcb(pcb_path, placements)
        report_path = pcb_path.parent / "placement-report.json"
        with open(str(report_path), "w") as f:
            json.dump(report, f, indent=2)
        print(f"Wrote placement report to {report_path.name}",
              file=sys.stderr)

    if warnings:
        print(f"\n{len(warnings)} warning(s):", file=sys.stderr)
        for w in warnings:
            print(f"  • {w}", file=sys.stderr)


if __name__ == "__main__":
    main()

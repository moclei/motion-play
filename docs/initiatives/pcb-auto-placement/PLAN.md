# PCB Auto-Placement Tooling — Plan

## Approach

Two tools, built sequentially (the placement script depends on the enriched extract):

1. **Enhance `tools/pcb-context/extract.py`** — add a `--pads` flag that includes per-component pad data in the extracted JSON, and fix the bounding box calculation for imported footprints.
2. **Create `tools/pcb-context/place_power.py`** — reads the enriched extract and `spec.json`, computes optimal positions for power support components, writes them to the `.kicad_pcb` file via kiutils.

### Workflow in Practice

```
User positions anchor components in KiCad, saves
    ↓
python extract.py <pcb> --pads       → enriched pcb-layout-context.json
    ↓
python place_power.py                → reads JSON + spec.json, writes .kicad_pcb
    ↓
User opens KiCad, reviews placement, runs DRC
    ↓
Iterate if needed (adjust anchors, re-extract, re-place)
```

## Technical Notes

### Extract Enhancement: Pad Data

The `--pads` flag adds a `pads` array to each component in `placed_components`:

```json
{
  "ref": "U5",
  "value": "BQ24195RGER",
  "footprint": "VQFN-24_L4.0-W4.0-P0.50-TL-EP2.8",
  "x": 81.26, "y": 120.65,
  "rotation": 0, "side": "front",
  "bbox": {"width": 4.6, "height": 4.6},
  "pads": [
    {"number": "1", "x": 80.01, "y": 122.15, "size_x": 0.3, "size_y": 0.7, "net": "Protected_VBUS", "shape": "roundrect"},
    {"number": "25", "x": 81.26, "y": 120.65, "size_x": 2.8, "size_y": 2.8, "net": "GND", "shape": "rect"}
  ]
}
```

**Global pad position transform.** KiCad stores pad positions in footprint-local coordinates. The correct transform for KiCad's coordinate system (Y-down, positive rotation stored in file):

```
gx = fp_x + lx * cos(θ) + ly * sin(θ)
gy = fp_y - lx * sin(θ) + ly * cos(θ)
```

where `θ` is the footprint rotation in radians, `(fp_x, fp_y)` is the footprint center, and `(lx, ly)` is the pad's local position. This was verified against known pin orientations for U5 (BQ24195) and U6 (TPS61088).

**Data source:** `kiutils Board.footprints[].pads[]` already has local positions (`.position.X`, `.position.Y`), sizes (`.size.X`, `.size.Y`), shapes (`.shape`), and net assignments (`.net.name`). This is a data extraction + transform task.

### Extract Enhancement: Bbox Fix

Five easyeda2kicad-imported footprints (U5, U6, U7, J7, L2) have tiny or absent courtyard layers, causing the courtyard-based bbox to return 0.06×0.06mm. The pad data itself is correct — only the bbox path is broken.

**Fix:** Add a sanity threshold after the courtyard/fab bbox calculation. If either dimension is under ~1mm, discard the result and fall through to the pad-based bbox calculation (which already exists as `_bbox_from_pads` and works correctly).

### Placement Script: Anchor-Based Design

**Inputs:**
- `pcb-layout-context.json` (with `--pads` data) — component positions, pad positions, bounding boxes, board outline
- `tools/schematic-gen/spec.json` — net topology, functional block assignments, pin-to-net mappings

**Anchor components** keep their current positions (user places these manually in KiCad):
- U5 (BQ24195, 4×4mm VQFN-24) — battery management IC
- U6 (TPS61088, 4.6×3.6mm VQFN-20) — boost converter IC
- J7 (USB-C connector) — board-edge-mounted
- J8 (JST PH battery connector) — board-edge-mounted
- L1 (2.2µH inductor, 6×6mm) — BQ24195 switching inductor
- R44 (10mΩ 2512 shunt) — in-line on VSYS path

**Placed components** (~39 total): everything else in the power section — support passives (C20-C41, R30-R43), small ICs (U7), thermistor (TH1), PMOS (Q2), fuse (F2), test points (TP1-TP4).

**U6 rotation adjustment:** U6 is currently at -90° with SW pins (4-7) facing left toward the board edge, leaving only ~5mm before the edge — not enough for L2. The script rotates U6 to +90° so SW pins face right toward the board interior, allowing L2 to be placed adjacent. This is part of the placement logic, not a manual step.

### Placement Script: Tiered Priority System

Components are placed based on their electrical relationship to anchor pins, with distance constraints reflecting layout sensitivity:

| Tier | Constraint | Components | Rationale |
|------|-----------|------------|-----------|
| **1 — Critical** | <2mm from pins | L2→U6 SW, C23 bridging BTST↔SW, C32 bridging BOOT↔SW | Switching loop area minimization |
| **2 — Important** | <5mm from pins | C20/C21 to U5 IN, C34-C36 to U6 output, C25/C26 to U5 PMID, C41/C31 to U6 VIN | Bulk decoupling effectiveness |
| **3 — Moderate** | <10mm from pins | R39/R40 to U6 FB, R43/C38/C39 to U6 COMP, C24 to U5 REGN, C27/C28 to U5 VSYS | Signal integrity, not switching-critical |
| **4 — Flexible** | <15-20mm | C29 (220µF electrolytic), C22/C30 (47µF electrolytics), R35/R38 (pull-ups), R33/R34 (gate bias), TH1/R36/R37 (NTC network), TP1-TP4 | Large passives, bias networks, test access |

### Placement Script: Collision Avoidance

The script must ensure:
1. **No component overlap** — placed components' bounding boxes (with margin) must not intersect any existing component's bbox
2. **Board boundary** — all components must be fully within the board outline (62.6–164, 101–141)
3. **Power section boundary** — placed components stay within the left ~40mm power zone (roughly x < 105), not encroaching on existing right-side components
4. **Clearance margin** — minimum 0.3mm gap between component bboxes (KiCad default clearance)

### Placement Script: Algorithm Sketch

For each component to place, in tier order:
1. Identify the target anchor pin(s) from `spec.json` net mappings and the enriched pad data
2. Compute candidate position: offset from the target pin in a preferred direction (away from IC center, toward available space)
3. Check for collisions against all already-placed components
4. If collision, try alternate positions (rotate candidate, shift along preferred axis)
5. If no valid position found within tier distance, log a warning and relax the constraint
6. Record the final position

After all components are placed:
1. Open the `.kicad_pcb` via kiutils
2. For each placed component, find the matching footprint by reference designator
3. Set `position.X`, `position.Y`, and `position.angle`
4. Save the file

### Board Geometry Context

```
Board: 101.4mm × 40mm
Outline: (62.6, 101) to (164, 141)       ← KiCad coordinates (Y-down)

┌─── 62.6 ──────────── ~103 ──────────────── 164 ───┐
│                        │                            │ 101
│   POWER SECTION        │    EXISTING COMPONENTS     │
│   (~40mm wide)         │    (T-Display-S3, etc.)    │
│                        │                            │
│   U5, U6, J7, J8      │    U1, U2, U4, IC1        │
│   L1, L2, R44          │    J3-J6, etc.            │
│   + ~39 support        │                            │
│                        │                            │ 141
└────────────────────────┴────────────────────────────┘
```

U5 (BQ24195) at ~(83, 122) — SW pins 19-20 on top edge. L1 (83, 114) 2mm above with 2.1mm gap for C23.
U6 (TPS61088) at ~(70, 136) — needs rotation to +90° so SW pins face right.
J7 (USB-C) at ~(81, 106) — top-left area, board edge.
J8 (battery) at ~(67, 119) — left edge.

### Reference Files

| File | Purpose |
|------|---------|
| `tools/pcb-context/extract.py` | Script to enhance (pad data + bbox fix) |
| `tools/schematic-gen/spec.json` | Net topology, pin-to-net mappings, block assignments |
| `hardware/pcb-main/kicad/pcb-layout-context.json` | Current extraction output (input for placement) |
| `hardware/pcb-main/kicad/motion-play-main.kicad_pcb` | Target PCB file (placement writes here) |
| `docs/initiatives/integrated-power/LAYOUT_GUIDE.md` | Placement rules, trace widths, thermal requirements |

## Open Questions

All resolved during implementation:

- ~~`--dry-run` mode~~ — Implemented. Outputs full placement report as JSON.
- ~~Test points~~ — Implemented. TP1-TP4 placed along bottom edge with dedicated logic.
- ~~Side preference~~ — Uses direction-away-from-anchor-center preference. Works well in practice; bypass caps cluster on the appropriate sides.

## Resolved During Validation

- **kiutils KiCad 9 incompatibility:** kiutils v1.4.8 rewrites the entire file, converting `uuid` → `tstamp` (KiCad 7/8 format) and reformatting all s-expressions. The `group` element's `uuid` field becomes an empty `(id )` causing parse failures on re-read. **Fix:** `write_placements_to_pcb` now uses text-based regex replacement instead of kiutils Board.to_file, preserving KiCad 9 formatting.
- **C23 BTST bridging cap:** L1 shifted up 2mm (y 116.35→114.35) to open a 2.1mm gap between L1 bottom and U5 top. C23 now places at 3.0mm from BTST — within Tier 1 constraint, no relaxation needed. Previous position was 4.5mm (relaxed) when L1 sat 0.1mm above U5.

# PCB Context Tools

Scripts for extracting structured data from KiCad PCB files and automating component placement. The readers (`board_model.py`, `extract.py`, `routing_extract.py`, and `tools/verify-routing.py`) load the `.kicad_pcb` through `tools/kicad-io/kicad_io.py` and read the raw tree with the views in `pcb_raw.py` (not kicad-tools' typed `PCB`). `place_power.py` writes positions by text replacement.

## Historical outputs (v7 main board) — do not cite

These committed files in `hardware/pcb-main/kicad/` are kept because the v7 debug track cites `c2acffc` paths, but they do **not** describe the v7 board as built. Use `board_model.py` output instead (regenerate it; it carries `_provenance`).

| File | Why it is historical |
|---|---|
| `pcb-layout-context.json` | Extracted 2026-04-07, before the final layout (2026-04-13): 7 parts are at the wrong position, including U7 (INA219, on the I²C bus) by ~4.9 mm. Bounding boxes only; no pads, nets or copper. No source hash. |
| `drc-report.json` | Hand-run 2026-03-12, before routing: 137 unconnected, 84 violations. The routed board has 0 unconnected (kicad-cli 9.0.4, `board_model.py` DRC, 2026-11-02). |
| `placement-report.json` | Output of a `place_power.py` run (2026-03-16) whose placement was later redone by hand. |

Source: `docs/research/v7-retry/kicad-extraction-audit.md` §2.

## board_model.py

One parse of a `.kicad_pcb` into one model (`board-model.json`): true rotated pad polygons, footprint bodies, outline, tracks/vias, zones with de-fractured fills, stackup, per-net topology (branches, stubs, islands), kicad-cli DRC, and `_provenance`. Reports are derived from it. Spec: the extraction audit §5.2 / §6.1. Validated on v7 `c2acffc` (`docs/initiatives/v8-debug-board/SESSION.md`, Worker #5).

```bash
tools/.venv/bin/python tools/pcb-context/board_model.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb [-o out.json] [--config cfg.json] [--no-drc] [--source-ref REF]
tools/.venv/bin/python tools/pcb-context/board_model.py --check out.json     # 0 fresh, 1 stale, 2 no provenance
```

Per-board definitions (high-current, high dv/dt, neighbour radii, clearance metric, driver pads, critical nets) live in `board-config/<pcb stem>.json`, picked up automatically. Python use: `from board_model import BoardModel; m = BoardModel.load(path); m.net_copper("/I2C_SDA")`.

## Reports from the model: net_report.py, plane_report.py, render.py

All three read a `board-model.json` and nothing else. Shared geometry and the measuring methods live in `report_lib.py`.

```bash
D=hardware/pcb-main/kicad/board-model
tools/.venv/bin/python tools/pcb-context/board_model.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb -o $D/board-model.json --source-ref c2acffc
tools/.venv/bin/python tools/pcb-context/net_report.py   $D/board-model.json [--net NET ...]      # → $D/net-report.md, net-report.json
tools/.venv/bin/python tools/pcb-context/plane_report.py $D/board-model.json                       # → $D/plane-report.md, plane-report.json
tools/.venv/bin/python tools/pcb-context/render.py       $D/board-model.json [--net NET] [--layer L]  # → $D/img/*.png + *.png.meta.json
```

- **net_report.py**: one full block per critical net (board config `critical_nets`, or `--net`): route tree from the driver with each chain's layer, length, width and straight legs; endpoints with length/vias/layers from the driver; reference plane per segment and each unreferenced stretch; footprint bodies the net passes under or over; every neighbour within the radius on any layer (same-layer gaps, plan-view gap with dielectric separation, coupled length, crossings, the closest item pair); per via, the planes on each side and the nearest via of each plane net. A summary row for every other net.
- **plane_report.py**: per copper layer, area per net, zones, splits between different-net fills (min gap, shared boundary, tracks on adjacent layers crossing the gap, with mm in the gap), voids and split gaps (plane layers only: fills ≥ 25 % of the outline), antipad holes and merged clusters; mm unreferenced per signal segment and net; GND vias per 10 mm cell, empty cells, signal vias farthest from a GND via. Defaults can be overridden by a `plane_report` key in the board config's `definitions`.
- **render.py**: per critical net, a PNG cropped to the net (outline, faded bodies and pads, the net coloured by layer, its pads and vias labelled with a leader to the centre dot, neighbours shaded by class and labelled, no-reference stretches dashed); per layer with fills, a full-board PNG (fills by net, voids and split gaps hatched on plane layers, keepouts, critical-net tracks on the adjacent layer, GND vias). Each `.png.meta.json` holds the provenance, the view in mm, the axes box in px and every label's anchor in mm and px. After rendering, look at each image and check the labels sit on their pads.

**Measuring methods** (each report lists them; always cite the method with the number):

| Name | Meaning |
|---|---|
| track to track | target track copper (centreline buffered by width/2) to neighbour track copper, same layer |
| track to copper | target tracks to all neighbour copper on the layer (tracks, pads, vias, fills) |
| all copper | target tracks, pads and via rings to all neighbour copper, same layer |
| plan view | across layers, edge to edge in plan; zone fills on other layers are reference planes, not neighbours |
| coupled | mm of target track centreline within the radius of the neighbour's same-layer copper |
| reference raw / antipads excl. | centreline over the adjacent layer's fills; "antipads excl." counts fill holes that contain a drill (via, PTH, NPTH) as copper |

On v7 these differ by up to 0.3 mm (SCL to BOOST_SW: 0.94 track to track, 0.66 all copper via V200).

### Where committed outputs go

Generated outputs are committed beside the PCB they describe, in `<kicad folder>/board-model/` (v7: `hardware/pcb-main/kicad/board-model/`): `board-model.json`, `net-report.*`, `plane-report.*`, `img/`. Generate from the repo path (not a scratch copy), so `_provenance.source` is a repo-relative path that `python3 tools/lab/check_state.py --fresh <file>` can re-hash; pass `--source-ref` with the commit the PCB matches. Markdown carries the provenance as front matter, JSON as `_provenance`, PNGs in the sidecar. Regenerate all of them whenever the PCB changes, and commit the tool change first so `generator_commit` is not `-dirty`.

## Workflow (placement, older tools)

```
User positions anchor components in KiCad, saves
    ↓
tools/.venv/bin/python tools/pcb-context/extract.py <pcb> --pads       → pcb-layout-context.json (enriched)
    ↓
tools/.venv/bin/python tools/pcb-context/place_power.py <pcb> --dry-run → review proposed positions
    ↓
tools/.venv/bin/python tools/pcb-context/place_power.py <pcb>           → writes positions to .kicad_pcb
    ↓
User opens KiCad, reviews placement, runs DRC
```

KiCad must be closed before running `place_power.py` without `--dry-run` — both tools write to the same `.kicad_pcb` file.

## extract.py

Parses a `.kicad_pcb` file and produces `pcb-layout-context.json` — a structured snapshot of board outline, component positions, bounding boxes, and optionally per-component pad data. Used by `place_power.py` and by AI-assisted layout sessions.

```
tools/.venv/bin/python tools/pcb-context/extract.py <file.kicad_pcb> [options]
```

| Flag | Description |
|------|-------------|
| `--pads` | Include per-component pad data: pad number, global x/y, size, net name, shape. Required before running `place_power.py`. |
| `--output PATH`, `-o` | Output path for the JSON file. Default: `pcb-layout-context.json` alongside the PCB. |
| `--schematic-context PATH` | Path to `circuit-context.json` for cross-referencing unplaced components. Auto-detected if present alongside the PCB. |

### Examples

```bash
# Basic extraction
tools/.venv/bin/python tools/pcb-context/extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb

# With pad data (needed for placement)
tools/.venv/bin/python tools/pcb-context/extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb --pads

# Custom output path
tools/.venv/bin/python tools/pcb-context/extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb --pads -o /tmp/context.json
```

### Output format

The JSON includes `board_outline`, `placed_components` (with optional `pads` array), `unplaced_components`, and a `summary` with component counts and board utilization percentage.

## place_power.py

Reads the enriched `pcb-layout-context.json` and `tools/schematic-gen/spec.json`, then computes collision-free positions for power section support components relative to manually-placed anchor ICs (U5, U6, J7, J8, L1, R44).

```
tools/.venv/bin/python tools/pcb-context/place_power.py <file.kicad_pcb> [options]
```

| Flag | Description |
|------|-------------|
| `--dry-run` | Output proposed positions as JSON to stdout without modifying the PCB. Always run this first to review. |
| `--context PATH` | Path to `pcb-layout-context.json`. Default: alongside the PCB file. |
| `--spec PATH` | Path to `spec.json`. Default: `tools/schematic-gen/spec.json`. |

### Examples

```bash
# Preview placement without writing
tools/.venv/bin/python tools/pcb-context/place_power.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb --dry-run

# Apply placement (KiCad must be closed)
tools/.venv/bin/python tools/pcb-context/place_power.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb

# Custom input paths
tools/.venv/bin/python tools/pcb-context/place_power.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb \
    --context /tmp/context.json \
    --spec path/to/spec.json \
    --dry-run
```

### How placement works

**Anchors** (U5, U6, J7, J8, L1, R44) keep their manually-set positions. Everything else in the power section is repositioned.

Components are placed in four tiers based on electrical proximity requirements:

| Tier | Constraint | Purpose | Example components |
|------|-----------|---------|-------------------|
| 1 — Critical | <3mm from pins | Switching loop minimization | L2, C23, C32 |
| 2 — Important | <5–6mm from pins | Bulk decoupling | C20, C21, C34–C36, C25, C26 |
| 3 — Moderate | <10mm from pins | Signal integrity | R39, R40, R43, C24, C27, F2, U7 |
| 4 — Flexible | <15–20mm | Large passives, bias networks | C29, C22, R33, TH1, TP1–TP4 |

For each component, the script finds the target anchor pad via net name matching against `spec.json`, then searches in expanding rings for the closest collision-free position, preferring the direction away from the anchor IC center.

**U6 rotation fix:** U6 is rotated from -90° to +90° so its SW pins face the board interior, making room for L2.

**Test points** (TP1–TP4) are placed along the bottom board edge for probe access.

If a component can't be placed within its tier distance, the constraint is relaxed (doubled distance, full board width). Failures and relaxations are reported as warnings.

### Output

- **`--dry-run`**: prints a JSON report to stdout with `placements` (new and old positions), `warnings`, and `summary`.
- **Normal mode**: writes positions to the `.kicad_pcb` file and saves a `placement-report.json` alongside the PCB.

## routing_extract.py

> Superseded by `board_model.py` (which reuses its parsing core). Kept as a compatibility shim for `routing_audit.py`.

Parses a `.kicad_pcb` file and produces `pcb-routing-context.json` — a structured snapshot of per-net trace segments and vias, per-footprint pads in world-space coordinates, and per-layer footprint bounding boxes. Complements `extract.py`: where `pcb-layout-context.json` captures placement, `pcb-routing-context.json` captures routing. The two files live side-by-side in the PCB's `kicad/` folder.

```
tools/.venv/bin/python tools/pcb-context/routing_extract.py <file.kicad_pcb> [options]
```

| Flag | Description |
|------|-------------|
| `--list-nets` | Print all net names from the PCB to stdout and exit. Useful for discovering the exact strings to put in an audit spec — net names are sometimes hierarchical (e.g. `/Power Management/VSYS`, not `/VSYS`). |
| `--output PATH`, `-o` | Output path for the JSON file. Default: `pcb-routing-context.json` alongside the PCB. |

### Examples

```bash
# Extract routing context (writes pcb-routing-context.json next to the PCB)
tools/.venv/bin/python tools/pcb-context/routing_extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb

# Discover net names before authoring an audit spec
tools/.venv/bin/python tools/pcb-context/routing_extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb --list-nets

# Custom output path
tools/.venv/bin/python tools/pcb-context/routing_extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb -o /tmp/routing.json
```

### Output format

The JSON includes a `meta` block (source path, timestamp), a `nets` map keyed by net name (each entry has `segments`, `vias`, `total_length_mm`, and `length_by_layer`), and a `footprints` array (each entry has `ref`, `value`, `position`, `rotation`, `side`, `bbox_by_layer`, and a `pads` array with world-space pad positions, sizes, shapes, and net names).

## routing_audit.py

> **Superseded** by `board_model.py` + `net_report.py`. Its distances are centreline, not edge to edge, and it sees only what a spec names, on the same layer (extraction audit §2). Kept because the v7 debug track cites its spec and outputs.

Reads a `pcb-routing-context.json` plus a small audit spec (declarative JSON listing target nets, noisy components, noisy pads, noisy nets, and a compare pair) and writes a JSON report and a Markdown report. Computes per-net length, per-layer length, and minimum clearance from each target net to each item in the spec, all layer-aware. Used to produce hard numbers for design audits and debugging investigations (see `docs/debugging/v7-i2c-investigation.md` Phase 16 for an applied example).

```
tools/.venv/bin/python tools/pcb-context/routing_audit.py <audit-spec.json> [options]
```

| Flag | Description |
|------|-------------|
| `--output-json PATH` | Output path for the audit JSON report. Default: `<spec>.audit.json` alongside the spec. |
| `--output-md PATH` | Output path for the audit Markdown report. Default: `<spec>.audit.md` alongside the spec. |

### Examples

```bash
# Run an audit using the v7 main-PCB I2C spec
tools/.venv/bin/python tools/pcb-context/routing_audit.py tools/pcb-context/audit-specs/v7-main-i2c.json

# Custom output paths
tools/.venv/bin/python tools/pcb-context/routing_audit.py tools/pcb-context/audit-specs/v7-main-i2c.json \
    --output-json /tmp/audit.json \
    --output-md /tmp/audit.md
```

### Authoring an audit spec

An audit spec is a small JSON file living in `audit-specs/`. The v7 spec at `audit-specs/v7-main-i2c.json` is a worked example; copy and adapt it for new audits. Spec keys:

| Key | Description |
|-----|-------------|
| `pcb` | Path to the `.kicad_pcb` (informational; the auditor reads from `routing_context`, not directly from the PCB). |
| `routing_context` | Path to a `pcb-routing-context.json` produced by `routing_extract.py`. Relative to the spec file or absolute. |
| `target_nets` | Array of net names to report on. Each gets a per-net summary block with length and proximities. |
| `noisy_components` | Array of footprint references (e.g. `"L1"`, `"U5"`). For each target net, the auditor reports min clearance to that footprint's per-layer bounding box. |
| `noisy_pads` | Array of `{"ref", "pad", "label"}` objects naming specific pads. Min clearance is computed against `Point.buffer(effective_radius)` where the radius comes from the pad's size. Used to target individual pins on a multi-pin part (e.g. just the SW pins of a buck converter, not the whole IC). |
| `noisy_nets` | Array of net names. For each target net, min clearance is computed against the geometry of each named net (LineString to LineString, layer-aware). |
| `compare_pair` | Optional `[net_a, net_b]` two-element array. If present, the auditor emits an asymmetry table comparing the two nets across every metric in the per-net blocks. |

Two practical notes when authoring a spec:

1. **Hierarchical nets are sheet-prefixed.** On boards with hierarchical schematic sheets, KiCad prefixes net names with the sheet path. For example, `motion-play-main.kicad_pcb` exposes `/Power Management/VBAT` as the full net name, not `/VBAT`. Use `routing_extract.py --list-nets` to print the exact strings before pasting them into a spec — guessing at the prefix wastes a debug cycle.

2. **Pad numbers are footprint-specific, not schematic-symbol-specific.** The BQ24195's SW pin in the schematic might be labeled "SW" or "pin 7", but its physical footprint (`BQ24195RGER`) splits SW across pads 19 and 20. Open the footprint in KiCad's footprint editor (or check the datasheet's pinout) to find the actual pad numbers. A spec that names `{"ref": "U5", "pad": "7"}` for the BQ24195 will silently report the wrong (or missing) pad.

## Dependencies

Run every script with `tools/.venv/bin/python` from the repository root (Python 3.13; build the venv from `tools/requirements.txt`, see `tools/CONTEXT.md` "Dependencies"). That file pins:
- kicad-tools 0.29.0, used only through `tools/kicad-io/kicad_io.py` (the readers' raw views are `pcb_raw.py`)
- shapely 2.0.7 — required by `routing_extract.py`, `routing_audit.py` and `board_model.py` for 2D geometry math
- matplotlib 3.11.2 for rendering

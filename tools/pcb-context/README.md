# PCB Context Tools

Scripts for extracting structured data from KiCad PCB files and automating component placement. Both tools use [kiutils](https://pypi.org/project/kiutils/) (v1.4.8+) to parse and write `.kicad_pcb` files.

## Workflow

```
User positions anchor components in KiCad, saves
    ↓
python extract.py <pcb> --pads       → pcb-layout-context.json (enriched)
    ↓
python place_power.py <pcb> --dry-run → review proposed positions
    ↓
python place_power.py <pcb>           → writes positions to .kicad_pcb
    ↓
User opens KiCad, reviews placement, runs DRC
```

KiCad must be closed before running `place_power.py` without `--dry-run` — both tools write to the same `.kicad_pcb` file.

## extract.py

Parses a `.kicad_pcb` file and produces `pcb-layout-context.json` — a structured snapshot of board outline, component positions, bounding boxes, and optionally per-component pad data. Used by `place_power.py` and by AI-assisted layout sessions.

```
python extract.py <file.kicad_pcb> [options]
```

| Flag | Description |
|------|-------------|
| `--pads` | Include per-component pad data: pad number, global x/y, size, net name, shape. Required before running `place_power.py`. |
| `--output PATH`, `-o` | Output path for the JSON file. Default: `pcb-layout-context.json` alongside the PCB. |
| `--schematic-context PATH` | Path to `circuit-context.json` for cross-referencing unplaced components. Auto-detected if present alongside the PCB. |

### Examples

```bash
# Basic extraction
python extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb

# With pad data (needed for placement)
python extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb --pads

# Custom output path
python extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb --pads -o /tmp/context.json
```

### Output format

The JSON includes `board_outline`, `placed_components` (with optional `pads` array), `unplaced_components`, and a `summary` with component counts and board utilization percentage.

## place_power.py

Reads the enriched `pcb-layout-context.json` and `tools/schematic-gen/spec.json`, then computes collision-free positions for power section support components relative to manually-placed anchor ICs (U5, U6, J7, J8, L1, R44).

```
python place_power.py <file.kicad_pcb> [options]
```

| Flag | Description |
|------|-------------|
| `--dry-run` | Output proposed positions as JSON to stdout without modifying the PCB. Always run this first to review. |
| `--context PATH` | Path to `pcb-layout-context.json`. Default: alongside the PCB file. |
| `--spec PATH` | Path to `spec.json`. Default: `tools/schematic-gen/spec.json`. |

### Examples

```bash
# Preview placement without writing
python place_power.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb --dry-run

# Apply placement (KiCad must be closed)
python place_power.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb

# Custom input paths
python place_power.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb \
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

Parses a `.kicad_pcb` file and produces `pcb-routing-context.json` — a structured snapshot of per-net trace segments and vias, per-footprint pads in world-space coordinates, and per-layer footprint bounding boxes. Complements `extract.py`: where `pcb-layout-context.json` captures placement, `pcb-routing-context.json` captures routing. The two files live side-by-side in the PCB's `kicad/` folder.

```
python routing_extract.py <file.kicad_pcb> [options]
```

| Flag | Description |
|------|-------------|
| `--list-nets` | Print all net names from the PCB to stdout and exit. Useful for discovering the exact strings to put in an audit spec — net names are sometimes hierarchical (e.g. `/Power Management/VSYS`, not `/VSYS`). |
| `--output PATH`, `-o` | Output path for the JSON file. Default: `pcb-routing-context.json` alongside the PCB. |

### Examples

```bash
# Extract routing context (writes pcb-routing-context.json next to the PCB)
python routing_extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb

# Discover net names before authoring an audit spec
python routing_extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb --list-nets

# Custom output path
python routing_extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb -o /tmp/routing.json
```

### Output format

The JSON includes a `meta` block (source path, timestamp), a `nets` map keyed by net name (each entry has `segments`, `vias`, `total_length_mm`, and `length_by_layer`), and a `footprints` array (each entry has `ref`, `value`, `position`, `rotation`, `side`, `bbox_by_layer`, and a `pads` array with world-space pad positions, sizes, shapes, and net names).

## routing_audit.py

Reads a `pcb-routing-context.json` plus a small audit spec (declarative JSON listing target nets, noisy components, noisy pads, noisy nets, and a compare pair) and writes a JSON report and a Markdown report. Computes per-net length, per-layer length, and minimum clearance from each target net to each item in the spec, all layer-aware. Used to produce hard numbers for design audits and debugging investigations (see `docs/debugging/v7-i2c-investigation.md` Phase 16 for an applied example).

```
python routing_audit.py <audit-spec.json> [options]
```

| Flag | Description |
|------|-------------|
| `--output-json PATH` | Output path for the audit JSON report. Default: `<spec>.audit.json` alongside the spec. |
| `--output-md PATH` | Output path for the audit Markdown report. Default: `<spec>.audit.md` alongside the spec. |

### Examples

```bash
# Run an audit using the v7 main-PCB I2C spec
python routing_audit.py audit-specs/v7-main-i2c.json

# Custom output paths
python routing_audit.py audit-specs/v7-main-i2c.json \
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

- Python 3.7+
- kiutils ≥ 1.4.8 (`pip install kiutils`)
- shapely ≥ 2.0 (`pip install shapely`) — required by `routing_extract.py` and `routing_audit.py` for 2D geometry math

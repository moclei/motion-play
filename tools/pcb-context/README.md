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

## Dependencies

- Python 3.7+
- kiutils ≥ 1.4.8 (`pip install kiutils`)

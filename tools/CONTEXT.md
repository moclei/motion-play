# Tools — AI Context

## Critical Rule

**DO NOT read or edit `.kicad_sch` or `.kicad_pcb` files directly.** These files are large, verbose S-expression formats that waste context window budget and produce unreliable edits. Instead, use the tools described below — they extract compact JSON context files and perform programmatic CRUD through kiutils.

## KiCad Schematic Tools

These three toolkits form a pipeline: **gen** creates sheets, **modify** surgically edits existing sheets, **context** extracts/annotates for AI consumption.

### schematic-context/

Extracts circuit data from `.kicad_sch` files into compact `circuit-context.json` files optimized for AI analysis. Also writes `ai_`-prefixed annotations back into schematic symbols.

| Script | Purpose |
|--------|---------|
| `extract.py` | Combines `kicad-cli` netlist export + kiutils parsing → `circuit-context.json`. Use `--previous` to preserve net/block annotations across re-extractions. |
| `annotate.py` | Writes hidden `ai_function`, `ai_block`, `ai_role`, `ai_critical_specs` properties to component symbols in `.kicad_sch`. |
| `show.py` | Displays annotation coverage; `--unannotated` shows what still needs labeling. |

See `tools/schematic-context/README.md` for full usage.

### schematic-gen/

Generates complete `.kicad_sch` sheet files from structured JSON specs. Components get symbols, footprints, LCSC part numbers, net labels, no-connect flags, and hierarchical labels — all programmatically. Uses the `@jlcpcb/mcp` MCP server to search LCSC parts, check stock, and download symbols/footprints.

| File | Purpose |
|------|---------|
| `spec.json` | Structured spec for the power management sheet (components, nets, blocks). |
| `esp32_spec.json` | Structured spec for the ESP32-S3 sheet. |
| `generate_power_sheet.py` | Generates `power_management.kicad_sch` from `spec.json`. |
| `generate_esp32_sheet.py` | Generates `esp32_s3.kicad_sch` from `esp32_spec.json`. |
| `poc_generate.py` | Proof-of-concept: generates a minimal schematic with one resistor. |

### schematic-modify/

Surgical in-place edits on existing `.kicad_sch` files — adding/removing components, sheet references, hierarchical labels. Sits between gen (full sheet creation) and context (read-only extraction).

| File | Purpose |
|------|---------|
| `modify.py` | Reusable helpers: `add_component`, `remove_component`, `add_hierarchical_label`, `add_sheet_reference`, `annotate_components`. |
| `esp32_integration.py` | Initiative-specific script that used `modify.py` to integrate the ESP32-S3 into the main schematic. |

See `tools/schematic-modify/CONTEXT.md` for relationship details and typical workflow.

## KiCad PCB Tools

### pcb-context/

Extracts structured layout data from `.kicad_pcb` files into `pcb-layout-context.json`, and automates component placement.

| Script | Purpose |
|--------|---------|
| `extract.py` | Parses board outline, component positions, bounding boxes, optional pad data → `pcb-layout-context.json`. |
| `place_power.py` | Computes collision-free placements for power section components relative to anchor ICs. Supports `--dry-run`. |

See `tools/pcb-context/README.md` for full usage.

### verify-routing.py

Verifies PCB routing against spec constraints (trace widths, clearances, net classes). Currently hardcoded to a specific board revision — needs genericization to accept an input spec file.

## Firmware & Data Tools

| Tool | Type | Purpose |
|------|------|---------|
| `diagnose-session.sh` | Shell | Queries CloudWatch Logs for Lambda invocations related to a session. Shows invocation count, errors, durations. |
| `download-session.sh` | Shell | Downloads session data (metadata + readings) from API Gateway for offline analysis. Supports `--summary` and `--check-keys`. |
| `transit-calculator.py` | Python | Calculates sensor samples per ball transit for different hoop/ball/speed combinations. Design tool for sensor rate requirements. |

## ML Training

### ml-training/

Full pipeline: download labeled sessions → preprocess into (300, 6) tensors → train 1D CNN → quantize to int8 → export as C header for ESP32-S3 firmware. See `tools/ml-training/README.md`.

## Serial Studio

### serial-studio/

JSON dashboard definition files for Serial Studio (advanced serial monitor). Multiple versioned files exist from iterative development — the latest version is the active one. These are loaded into Serial Studio to visualize real-time sensor data from the device.

## Dependencies

All Python tools in this folder use **kiutils ≥ 1.4.8** for KiCad file parsing. Install via `pip install kiutils`. Shell scripts require AWS CLI + jq.

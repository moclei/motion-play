# Schematic Modify Toolkit Context

Programmatic helpers for editing existing KiCad schematics in place.

## Purpose

`schematic-modify` fills the gap between:

- `tools/schematic-gen/` (generates full new sheets from a structured spec)
- `tools/schematic-context/` (extracts + annotates context data from schematic files)

Use `schematic-modify` when you need to append/remove components or sheet links in an existing `.kicad_sch` without rewriting the whole file.

## Relationship to Other Tools

- **`schematic-gen`** is source-of-truth for generated sheets.
- **`schematic-modify`** performs surgical updates on existing sheets.
- **`schematic-context/annotate.py`** remains the single place that writes `ai_*` properties.

Design rule: this toolkit sets electrical properties (nets, footprint, LCSC fields) and delegates annotation to `annotate.py` after placement.

## Current Files

- `modify.py`: reusable helpers (`add_component`, `remove_component`, `add_hierarchical_label`, `add_sheet_reference`, `annotate_components`)
- `esp32_integration.py`: initiative-specific modifications for ESP32-S3 direct integration
- `v8_project_setup.py`: v8-debug-board initiative. Copies the v7 project (`c2acffc`) to `hardware/pcb-main-v8/kicad/` as `motion-play-main-v8`, renames instance project names via kiutils, writes an empty stackup-only `.kicad_pcb`, and verifies (ERC, netlist vs v7, DRC load). `--verify --no-v7-compare` re-runs the checks after edits

## Typical Workflow

1. Run `esp32_integration.py --apply` (or custom script using `modify.py`) to place components/sheet refs off to one side.
2. Script calls `tools/schematic-context/annotate.py` for `ai_*` properties.
3. Open KiCad and do manual placement/wiring cleanup.
4. Run `tools/schematic-context/extract.py --previous` to refresh `circuit-context.json`.

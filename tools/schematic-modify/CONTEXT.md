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

## Typical Workflow

1. Run `esp32_integration.py --apply` (or custom script using `modify.py`) to place components/sheet refs off to one side.
2. Script calls `tools/schematic-context/annotate.py` for `ai_*` properties.
3. Open KiCad and do manual placement/wiring cleanup.
4. Run `tools/schematic-context/extract.py --previous` to refresh `circuit-context.json`.

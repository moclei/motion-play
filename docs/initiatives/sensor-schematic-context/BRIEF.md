# Sensor PCB Schematic Context

## Intent

Run the existing schematic context extraction and annotation tooling on the two sensor PCBs (rigid base and flex strip) to produce `circuit-context.json` files, giving AI assistants the same quality of circuit understanding for sensor boards that already exists for the main PCB.

## Goals

- A complete `circuit-context.json` for the sensor rigid base (`hardware/sensor-rigid/circuit-context.json`) with all components annotated, nets described, and functional blocks defined
- A complete `circuit-context.json` for the flex sensor strip (`hardware/sensor-flex/circuit-context.json`) with the same coverage
- Updated `hardware/CONTEXT.md` status table reflecting the new context files
- Both schematics gain `ai_` custom properties on all components (persisting annotations in the `.kicad_sch` files)

## Scope

What's in:
- Running `extract.py` on both sensor schematics
- Full annotation pass for both boards (component ai_ properties, net annotations, block definitions)
- Documentation updates to reflect completed status

What's out:
- Changes to the extraction/annotation tooling itself (it's already built)
- Changes to the schematics beyond additive `ai_` metadata properties
- Verification quiz (these are simple single-sheet boards; visual inspection of the context files is sufficient)

## Constraints

- Python 3.7.3 — use `from __future__ import annotations` and `typing.Optional`/`typing.List`
- `kicad-cli` at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`
- Both schematics are single-sheet (no hierarchy), so `sheet_interfaces` will be empty
- Output goes next to the schematic file (not in a `kicad/` subdirectory — these projects don't use that structure)
- `hardware/CONTEXT.md` BOM tables are the reference for component functions and roles

## Reference

- **Parent initiative:** `docs/initiatives/schematic-context/` — built the tooling and completed the main PCB
- **Tooling docs:** `tools/schematic-context/README.md`
- **Hardware context:** `hardware/CONTEXT.md` — BOM tables for both boards

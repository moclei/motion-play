# Sensor PCB Schematic Context — Plan

## Approach

The tooling already exists in `tools/schematic-context/`. This initiative is purely about running it on two more boards and adding semantic annotations. Both schematics are single-sheet designs, so there's no hierarchy handling needed — `sheet_interfaces` will be empty and the extraction is straightforward.

For each board, the workflow is:
1. Run `extract.py` to produce an initial `circuit-context.json` (components + connectivity, no annotations)
2. Use `annotate.py` to write `ai_` properties to components in the `.kicad_sch` file
3. Manually add net annotations and block definitions to `circuit-context.json`
4. Re-extract with `--previous` to merge component annotations (from schematic) with net/block annotations (from JSON)

### Sensor Rigid Base

~16 components across 3-4 functional blocks:
- **i2c_mux** — PCA9546A (U1) with address jumpers (JP3, JP4) and reset pull-up (R3)
- **connectors** — JST-SH input (J1) and ZIF FPC output (FPC1)
- **pull_ups** — Main bus pull-ups (R1, R2), per-sensor pull-ups (R6-R9), address pull-ups (R12-R14)
- **power** — Bypass caps (C1, C2), power LED (D1, R4)
- **interrupts** — BAT54S diodes (D2, D3) for wired-OR interrupt combining, INT pull-up (R5)

### Sensor Flex Strip

~6 components, likely 1-2 blocks:
- **sensors** — 2× VCNL4040 (IC1, IC2) with bypass caps (C6, C7) and LED anode caps (C4, C8)

## Annotation Reference

Component annotations are informed by `hardware/CONTEXT.md` BOM tables, which already describe every component's function, value, and role. The AI proposes `ai_function`, `ai_block`, `ai_role`, and `ai_critical_specs` values; the human confirms before writing.

Net annotations follow the same schema as the main PCB context file:
- `type`: power | signal | clock
- `protocol`: I2C where applicable
- `direction`: input | output | bidirectional
- `description`: what the net carries

## Open Questions

- None — this is a straightforward application of existing tooling.

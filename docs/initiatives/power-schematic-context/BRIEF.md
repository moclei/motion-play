# Power Supply PCB — Schematic Context

## Intent

Generate `circuit-context.json` for the power supply PCB (`hardware/pcb-power-supply/`), using the existing schematic context tooling. This is a custom power management board designed to replace the DWEII USB-C power module on the main PCB, adding USB PD negotiation, Li-ion battery charging, and regulated output rails.

## Goals

- A complete, annotated `circuit-context.json` for the power supply PCB — components, nets, functional blocks, and sheet interfaces across all 5 sheets
- Annotations informed by the BOM, datasheets, and design intent (this is a prototype replacement for the DWEII module)
- An AI session given only the context file and `hardware/CONTEXT.md` can answer substantive questions about the power supply circuit

## Scope

What's in:
- Running extraction on the root schematic (motion-play-power.kicad_sch) which includes 4 child sheets (usb_pd, battery_mgmt, power_dist, connectors)
- Interactive annotation of all components, nets, and functional blocks
- Verification that the context file is sufficient for AI reasoning

What's out:
- Changes to the schematic design itself (annotations are additive metadata only)
- Tooling changes — the extraction/annotation scripts already exist and work
- Updating `hardware/CONTEXT.md` with power supply PCB details (separate task)

## Constraints

- Python 3.7.3 — use `from __future__ import annotations` and `typing.Optional`/`typing.List`
- kicad-cli at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`
- KiCad may be open during extraction (read-only), but must be closed or reloaded before/after annotation writes
- Output goes to `hardware/pcb-power-supply/kicad/circuit-context.json`

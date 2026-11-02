# v8 Main Board — Debug Board

## Intent
Design and order a large, probe-friendly v8 main board. It fixes the known v7 design faults, and it can be switched back to v7's configuration with jumpers, so any v8 result can be A/B/A'd against v7 (P11). The initiative also trials AI-driven placement and routing, and builds the board-reading tools for a partner design review. Opened by the user's checkpoint decision (notebook 2026-10-31). Not evidence about the v7 I²C mechanism.

## Goals
- Test points on every I²C net (both sides of the TCA), every rail and U3's spare GPIOs, each with a ground point beside it sized for a ground spring. Debug LEDs.
- Jumper-selectable v7 ↔ v8 configuration, at minimum: (a) SDA/SCL master pins, GPIO43/44 vs other pads; (b) protection on the cable-facing channel lines, fitted vs bypassed; (c) MCU 3.3 V and pull-up rail, shared vs separate; (d) on-board pull-up values.
- BQ24195 "needs an I²C command to work" root-caused in the design and fixed in hardware, not only in firmware.
- v8 power path designed after a methodical look at why battery connection cooked #0001/#0002 (and why #0004's boost doesn't run).
- AI places the board and the user reviews and corrects it. AI routes a tentative subset. Every correction is captured as reusable rules and scripts.
- Board-reading tools good enough for an AI partner review alongside the user's own review (zones, routes, reference planes, freshness).
- 5 assembled boards ordered from JLCPCB.

## Scope
In: power-path desk investigation and a bench relay to the Debugger; v8 design intent, parts (any part may be swapped), schematic, layout, review, fab outputs and order; board-model tooling (audit phases 1–2); AI placement/routing tooling and workflow; firmware env/pin config for v8.
Out: the v7 I²C debug track and anything in `lab/` (the Debugger runs the bench); v7 rework; product form factor, enclosure, compactness; v8 bring-up and A/B/A testing (relayed to the Debugger when boards arrive); board-model diff mode (Deferred).

## Constraints
- Jumpers default to the v8 (fixed) configuration; every suspected v7 → v8 difference has a v7 position.
- The power-path design waits on the bench findings from the battery investigation.
- `.kicad_sch` / `.kicad_pcb` are touched only through tools (tools/CONTEXT.md Critical Rule). Generated context carries provenance (Source-Hash Rule).
- Python 3.7 + kiutils + shapely 2.0.7; kicad-cli 9.0.4 at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` (not on PATH).
- BQ24195 (C90862) stock is chronically low: check stock before committing to any part.

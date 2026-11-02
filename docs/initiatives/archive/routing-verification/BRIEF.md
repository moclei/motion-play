# PCB Routing Verification

## Intent

Build a programmatic verification tool that extracts trace routing data from the completed `.kicad_pcb` file and checks it against the routing specifications in `ROUTING_GUIDE.md`. This is a pre-order quality gate — catching routing errors now costs nothing; catching them after fabrication costs a board spin.

## Goals

- Verify that all critical power and signal paths are routed with correct trace widths, on correct layers, and connecting the correct pads
- Confirm I2C bus integrity: length-matched SDA/SCL pairs per connector channel, adequate isolation from switching nodes
- Verify switching loop quality: BOOST_SW copper pour coverage, BQ_SW trace directness, no stray traces cutting through sensitive areas
- Verify INA219 Kelvin sense connections use dedicated thin traces separate from power paths
- Produce a human-readable Markdown report with PASS/FAIL per check and a JSON sidecar for structured data
- Regenerate stale `pcb-layout-context.json` as a prerequisite (current file is outdated vs. the routed PCB)

## Scope

What's in:
- Regeneration of `pcb-layout-context.json` from the current `.kicad_pcb`
- Python verification script using kiutils to parse segments, vias, zones, and footprints
- Trace width checks per net class
- Zone existence and coverage checks (BOOST_SW pour, +5V/GND/3.3V planes)
- End-to-end connectivity path checks for critical power nets
- I2C length matching and switching-node isolation analysis
- INA219 Kelvin sense path independence verification
- FB/COMP routing side verification (must not cross switching area)
- Markdown + JSON report output

What's out:
- Automated correction of routing errors (report-only, fixes are manual in KiCad)
- Silkscreen, courtyard, or mechanical layer verification
- Thermal analysis or current capacity simulation
- DRC re-run (KiCad's DRC already passes; this is higher-level design-intent verification)

## Constraints

- Must use kiutils v1.4.8 (already installed, confirmed working with KiCad 9 format)
- Python 3.7 (project's current pyenv version)
- The routing guide's absolute coordinates are stale — verification must extract actual positions from the `.kicad_pcb` file, not rely on `pcb-layout-context.json` positions for correctness. Net names and topological relationships remain valid.
- Script should be re-runnable after any PCB modification to verify changes

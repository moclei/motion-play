# PCB Auto-Placement Tooling

## Intent

Automate the PCB component placement workflow for the power section by enhancing the layout extraction tool with pad-level data and building a placement script that computes optimal positions for support components relative to manually-positioned anchors. This eliminates the slow manual cycle of placing components one-by-one in KiCad, extracting positions, getting AI feedback, and adjusting.

## Goals

- Enrich `pcb-layout-context.json` with per-component pad data (global positions, sizes, net names, shapes) so that scripts and AI agents can reason about exact pin locations
- Fix bounding box calculation for easyeda2kicad-imported footprints (U5, U6, U7, J7, L2) which currently report 0.06×0.06mm due to tiny/absent courtyard layers
- Build `place_power.py` — a script that reads the enriched extract and `spec.json`, computes collision-free positions for ~39 power support components relative to anchor ICs, and writes the result directly to the `.kicad_pcb` file
- Reduce the power section placement iteration cycle from hours of manual work to a minutes-long extract → place → review loop

## Scope

What's in:
- `--pads` flag on `extract.py` that adds a `pads` array per component (pad number, global x/y, size, net, shape)
- Bbox sanity threshold: if courtyard bbox < ~1mm in either dimension, fall through to pad-based calculation
- `place_power.py` with anchor-based placement, tiered distance priorities, collision avoidance, and board boundary enforcement
- U6 (TPS61088) rotation from -90° to +90° as part of placement logic (SW pins facing board interior for L2 clearance)
- Direct `.kicad_pcb` write via kiutils (user must close KiCad before running)

What's out:
- Trace routing automation (placement only, routing is manual)
- Non-power-section component placement (existing right-side components are never moved)
- DRC automation (user runs DRC manually in KiCad after reviewing placement)
- Thermal via or copper pour placement
- General-purpose auto-placer for arbitrary boards (this is purpose-built for the power section)

## Constraints

- Must use kiutils (already installed, v1.4.8)
- Placement script writes directly to `.kicad_pcb` — KiCad must be closed when running
- Depends on `pcb-layout-context.json` (with `--pads`) and `tools/schematic-gen/spec.json` as inputs
- Board: 101.4×40mm, outline from (62.6, 101) to (164, 141) in KiCad coordinates
- Power section occupies the left ~40mm; existing components (T-Display-S3, TCA9548A, level shifter, sensor connectors, AP2112K) on the right side must not be moved
- Parent initiative: `docs/initiatives/integrated-power/` (Phase 5 — PCB layout)
- Predecessor: `docs/initiatives/pcb-layout-context/` (built the base extraction tool)

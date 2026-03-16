# PCB Layout Context Extraction — Tasks

## Phase 1: Build Extraction Script ✅

- [x] Review kiutils PCB parsing API — understand `Board`, `Footprint`, `GraphicItem` classes for accessing outline, component positions, and courtyard/fab layers
- [x] Create `tools/pcb-context/extract.py` — argument parsing, load `.kicad_pcb` via kiutils
- [x] Extract board outline from `Edge.Cuts` layer graphic items (GrRect or line/arc segments → bounding rectangle)
- [x] Extract placed components: ref, value, footprint lib name, position, rotation, side (front/back)
- [x] Compute bounding boxes from courtyard → fab → pad fallback chain
- [x] Handle axis-aligned bbox for rotated components
- [x] Extract unplaced components via cross-reference with `circuit-context.json` (components in schematic but not yet in PCB)
- [x] Compute summary stats (total, placed, unplaced, board utilization estimate)
- [x] Write compact JSON output to `pcb-layout-context.json` alongside the input PCB file (115 lines)
- [x] Test on `hardware/pcb-main/kicad/motion-play-main.kicad_pcb` — 37 placed, 51 unplaced, 88 total, 64.6% utilization
- [ ] Commit

## Phase 2: Validate & Use in Layout Session

- [ ] Run extraction on the current main PCB (post-schematic sync, with unplaced power components)
- [ ] Load the output JSON into an AI layout session for the integrated power initiative
- [ ] Note any missing or misleading data — refine extraction if needed
- [ ] Commit any refinements

---

**Handoff prompt for Phase 1:**

> Read `docs/initiatives/pcb-layout-context/BRIEF.md`, `PLAN.md`, and `TASKS.md` for full context. Build the PCB layout context extraction tool. The existing schematic context tool at `tools/schematic-context/extract.py` is a good reference for patterns (CLI, kiutils parsing, JSON output). kiutils is already installed. Test against `hardware/pcb-main/kicad/motion-play-main.kicad_pcb` which currently has ~35 placed components and ~51 unplaced power management components. The board outline is on the Edge.Cuts layer. Output should go to `hardware/pcb-main/kicad/pcb-layout-context.json`.

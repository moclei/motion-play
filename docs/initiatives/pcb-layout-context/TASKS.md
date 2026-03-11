# PCB Layout Context Extraction — Tasks

## Phase 1: Build Extraction Script

- [ ] Review kiutils PCB parsing API — understand `Board`, `Footprint`, `GraphicItem` classes for accessing outline, component positions, and courtyard/fab layers
- [ ] Create `tools/pcb-context/extract.py` — argument parsing, load `.kicad_pcb` via kiutils
- [ ] Extract board outline from `Edge.Cuts` layer graphic items (lines/arcs → bounding rectangle or polygon vertices)
- [ ] Extract placed components: ref, value, footprint lib name, position, rotation, side (front/back)
- [ ] Compute bounding boxes from courtyard → fab → pad fallback chain
- [ ] Handle axis-aligned bbox for rotated components
- [ ] Extract unplaced components (position at origin or flagged as not-placed)
- [ ] Compute summary stats (total, placed, unplaced, board utilization estimate)
- [ ] Write JSON output to `pcb-layout-context.json` alongside the input PCB file
- [ ] Test on `hardware/pcb-main/kicad/motion-play-main.kicad_pcb` — verify output is accurate and compact
- [ ] Commit and update TASKS.md

## Phase 2: Validate & Use in Layout Session

- [ ] Run extraction on the current main PCB (post-schematic sync, with unplaced power components)
- [ ] Load the output JSON into an AI layout session for the integrated power initiative
- [ ] Note any missing or misleading data — refine extraction if needed
- [ ] Commit any refinements

---

**Handoff prompt for Phase 1:**

> Read `docs/initiatives/pcb-layout-context/BRIEF.md`, `PLAN.md`, and `TASKS.md` for full context. Build the PCB layout context extraction tool. The existing schematic context tool at `tools/schematic-context/extract.py` is a good reference for patterns (CLI, kiutils parsing, JSON output). kiutils is already installed. Test against `hardware/pcb-main/kicad/motion-play-main.kicad_pcb` which currently has ~35 placed components and ~51 unplaced power management components. The board outline is on the Edge.Cuts layer. Output should go to `hardware/pcb-main/kicad/pcb-layout-context.json`.

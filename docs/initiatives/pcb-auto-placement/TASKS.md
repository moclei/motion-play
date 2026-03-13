# PCB Auto-Placement Tooling — Tasks

## Phase 1: Extract Enhancement

- [x] Add `--pads` CLI flag to `extract.py` that includes a `pads` array per component
- [x] Implement global pad position transform: `gx = fp_x + lx*cos(θ) + ly*sin(θ)`, `gy = fp_y - lx*sin(θ) + ly*cos(θ)` (KiCad Y-down convention, verified for U5/U6)
- [x] Each pad entry: `number`, `x`, `y` (global), `size_x`, `size_y`, `net`, `shape`
- [x] Fix bbox sanity threshold: if courtyard-based bbox < ~1mm in either dimension, fall through to `_bbox_from_pads` (fixes U5, U6, U7, J7, L2 showing 0.06×0.06mm)
- [x] Run extraction with `--pads` on current PCB, verify pad positions for U5 and U6 against known pin locations — U5 pin 1 (Protected_VBUS) at (79.22, 119.4), U6 SW pins (4-7) at x=67.82
- [x] Verify fixed bboxes: U5 4.88×4.9mm, U6 4.16×5.06mm, U7 3.71×2.32mm, J7 9.86×6.49mm, L2 8.4×3.2mm — all pad-based, reasonable
- [x] Commit

## Phase 2: Placement Script

- [ ] Create `tools/pcb-context/place_power.py` — CLI that accepts PCB path, reads `pcb-layout-context.json` and `spec.json`
- [ ] Build anchor detection: identify anchor components (U5, U6, J7, J8, L1, R44) from the extract, lock their positions
- [ ] Build net-to-pad resolver: for a given net name + anchor ref, find the anchor's pad(s) on that net (using enriched pad data)
- [ ] Implement tiered placement engine: iterate components in tier order, compute position relative to target anchor pad, check constraints
- [ ] Implement collision detection: bbox intersection check with clearance margin against all placed components
- [ ] Implement board boundary enforcement: all placed component bboxes must fit within (62.6–164, 101–141)
- [ ] Handle U6 rotation: rotate from -90° to +90° (SW pins face right), recompute L2 position adjacent to new SW pin locations
- [ ] Place test points (TP1-TP4) along board edge (bottom or left) for probe access
- [ ] Implement `--dry-run` mode: output proposed positions as JSON without writing to PCB
- [ ] Implement PCB write: open `.kicad_pcb` via kiutils, set position/rotation for each placed component, save
- [ ] Commit

## Phase 3: Validation

- [ ] Run full workflow: extract `--pads` → `place_power.py` → open in KiCad
- [ ] Visual review in KiCad: verify no overlaps, reasonable grouping around ICs, switching loop components tight
- [ ] Run KiCad DRC, document any violations
- [ ] Iterate: adjust anchor positions or placement parameters if needed, re-run
- [ ] Verify critical distances: L2↔U6 SW <5mm, C23 bridging U5 BTST↔SW short, output caps within 5mm of U6 output pins
- [ ] Update `docs/initiatives/integrated-power/TASKS.md` to reflect tooling-assisted placement workflow
- [ ] Commit

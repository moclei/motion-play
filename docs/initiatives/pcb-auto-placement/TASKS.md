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

- [x] Create `tools/pcb-context/place_power.py` — CLI that accepts PCB path, reads `pcb-layout-context.json` and `spec.json`
- [x] Build anchor detection: identify anchor components (U5, U6, J7, J8, L1, R44) from the extract, lock their positions
- [x] Build net-to-pad resolver: for a given net name + anchor ref, find the anchor's pad(s) on that net (using enriched pad data) — net names normalized by stripping hierarchical path prefix
- [x] Implement tiered placement engine: 41 components across 4 tiers + 4 test points, all 46 placed successfully in dry-run
- [x] Implement collision detection: bbox intersection with 0.3mm clearance margin, expanding ring search with direction preference
- [x] Implement board boundary enforcement: board bounds (62.6–164, 101–141) + power section x<105 constraint with relaxation fallback
- [x] Handle U6 rotation: -90° → +90° via 180° pad mirror around IC center, SW pins now face board interior for L2 clearance
- [x] Place test points (TP1-TP4) along bottom edge for probe access
- [x] Implement `--dry-run` mode: outputs full placement report as JSON with old/new positions, tier info, and warnings
- [x] Implement PCB write: kiutils Board.from_file → set position.X/Y/angle per footprint → to_file — also writes placement-report.json
- [x] Commit

## Phase 3: Validation

- [x] Run full workflow: extract `--pads` → `place_power.py` → open in KiCad — 46 components placed, 0 failures, 4 relaxed
- [x] Fix kiutils KiCad 9 incompatibility: replaced kiutils Board.to_file (converts uuid→tstamp, reformats entire file) with text-based position replacement that preserves KiCad 9 formatting
- [x] Verify critical distances: L2 edge↔U6 SW 0.8mm (excellent), C32↔U6 BOOT 2.5mm, C34-C36↔U6 +5V 2.5-3.5mm
- [x] Shift L1 up 2mm (y 116.35→114.35) to open 2.1mm gap between L1 and U5 for C23 BTST bridging — re-extract and re-place improved C23 from 4.5mm (relaxed) to 3.0mm (within tier 1)
- [x] Update `docs/initiatives/integrated-power/TASKS.md` to reflect tooling-assisted placement workflow
- [x] Visual review in KiCad: 46 components placed, 0 overlaps, grouping reasonable, switching loop components tight around U5/U6
- [x] Run KiCad DRC: 84 violations, 137 unconnected (expected pre-routing). Breakdown: 56 from J7/U6 footprint imports (easyeda2kicad thermal vias, PTH clearances), 17 silkscreen overlaps (cosmetic), 9 dangling tracks (pre-existing), 2 R42 edge clearance (pad 0.35mm from board edge vs 0.5mm min — only placement-caused issue). F2/C22 placed relative to J7 center (VBUS/GND pads unassigned in footprint). No component-to-component overlap violations.
- [x] Commit

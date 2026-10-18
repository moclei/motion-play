# PCB Routing Audit Tool — Tasks

## Phase 1: Extractor (`routing_extract.py`)

- [x] Skeleton: argparse, `kiutils.Board` load, output path handling, mirror existing `extract.py` style
- [x] Add `shapely` to `tools/pcb-context/requirements.txt` (create if missing)
- [x] Extract per-net track segments (start, end, width, layer, net name)
- [x] Extract per-net vias (position, drill, size, layers spanned)
- [x] Decide arc handling — sampler implemented (16-step circumcircle); v7 board has 0 arcs but extractor stays forward-compatible
- [x] Extract footprint pads with world-space position (rotate pad offset by footprint rotation, add footprint position)
- [x] Extract per-layer footprint bbox
- [x] Compute total length per net + length by layer
- [x] Write `pcb-routing-context.json` next to existing `pcb-layout-context.json`
- [x] Add `--list-nets` flag for net discovery
- [x] **Verify:** spot-check 3 net lengths against KiCad's Net Inspector / Properties → Track Length. Tolerance ±0.05 mm. — user-confirmed (SDA 72.90, SCL 73.30, USB_DN 69.62 mm)
- [x] **Verify:** spot-check 3 pad coordinates (e.g., U5 pin 1, J6 pin 3, U4 pin 1) against KiCad's measure-from-origin. — user-confirmed
- [x] If verifications fail, do not proceed — fix root cause first.

## Phase 2: Auditor (`routing_audit.py`)

- [x] Skeleton: argparse, load routing JSON + audit spec
- [x] Min-distance computation: net (`MultiLineString`) → component bbox (`Polygon`), layer-aware
- [x] Min-distance computation: net → named pad (`Point.buffer(effective_radius)`), layer-aware
- [x] Min-distance computation: net → another net (LineString-to-LineString, layer-aware)
- [x] Per-net summary block (length, length-by-layer, proximities) → JSON
- [x] Asymmetry diff between named pair → JSON
- [x] Markdown formatter matching the structure in PLAN.md
- [x] Write audit spec `tools/pcb-context/audit-specs/v7-main-i2c.json`
- [x] **Verify:** for one proximity pair (e.g., `/I2C_SDA` → `L1`), measure manually in KiCad and compare. Tolerance ±0.05 mm. — user-confirmed (SDA→L1 6.05 mm, SCL→L1 5.55 mm)

## Phase 3: v7 first deliverable

- [x] Run extractor on `hardware/pcb-main/kicad/motion-play-main.kicad_pcb`
- [x] Run auditor with `v7-main-i2c.json` spec
- [x] Sanity-check the output — numbers consistent with known board layout (BQ at far end of bus, R28/R29 top-right, L1 near BQ)
- [x] Phase 16 section added to `docs/debugging/v7-i2c-investigation.md` — verdict: routing-asymmetry hypothesis **weakened**, not supported, by measured geometry
- [x] Updated `tools/pcb-context/README.md` with usage examples for both new scripts and audit-spec authoring guide

## Phase 4: Relay prompt for v2 (workflow override — see note below)

> **Note:** This phase exists by explicit user override of `.context/WORKFLOW.md`'s "no orphan documents" rule. The `RELAY_V2.md` file is a fourth document outside the BRIEF/PLAN/TASKS triad, and that's intentional for this initiative.

- [x] Created `docs/initiatives/pcb-routing-audit-tool/RELAY_V2.md` — what-v1-delivered, v1 artifacts list, deferred items with use cases, suggested v2 first deliverables (cross-PCB diff ranked highest given v8 on deck), self-contained planning prompt for a fresh v2 session
- [x] Added `## Tooling` section to `.context/IDEAS.md` with a single bullet pointing at `RELAY_V2.md`

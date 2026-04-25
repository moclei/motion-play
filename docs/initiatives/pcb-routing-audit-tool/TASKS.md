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

- [ ] Run extractor on `hardware/pcb-main/kicad/motion-play-main.kicad_pcb`
- [ ] Run auditor with `v7-main-i2c.json` spec
- [ ] Sanity-check the output: do numbers feel right given known board layout? (BQ at far end of bus, R28/R29 in top-right, L1 near BQ)
- [ ] Add a new section to `docs/debugging/v7-i2c-investigation.md` (e.g., "Phase 16 — routing-aware audit") with: the Markdown audit output verbatim, a 1–2 paragraph interpretation, and a verdict on whether the geometry supports or weakens the routing-asymmetry hypothesis.
- [ ] Update `tools/pcb-context/README.md` with usage examples for both new scripts and audit spec authoring guide.

## Phase 4: Relay prompt for v2 (workflow override — see note below)

> **Note:** This phase exists by explicit user override of `.context/WORKFLOW.md`'s "no orphan documents" rule. The `RELAY_V2.md` file is a fourth document outside the BRIEF/PLAN/TASKS triad, and that's intentional for this initiative.

- [ ] Create `docs/initiatives/pcb-routing-audit-tool/RELAY_V2.md` containing:
  - What v1 delivered (one paragraph, with file paths to the v1 code and the v7 audit output).
  - Deferred items list, each with a one-line rationale carried over from this initiative's BRIEF.md "What's out" section. At minimum: pad-to-pad path-distance via segment graph traversal; cross-PCB comparison (e.g., automated v7-vs-v8 routing diff).
  - Suggested first deliverables for v2 (which deferred items are highest-value to tackle first, and why).
  - Pointers to v1 artifacts: `docs/initiatives/pcb-routing-audit-tool/PLAN.md`, `tools/pcb-context/routing_extract.py`, `tools/pcb-context/routing_audit.py`, the v7 audit spec, the v7 audit Markdown output.
  - A self-contained planning prompt at the bottom — written so a fresh AI session can read just `RELAY_V2.md` and have everything it needs to produce a v2 initiative doc, in the same style as the prompt that produced this v1 initiative.
- [ ] Add a one-bullet entry to `.context/IDEAS.md` under a new "Tooling" section: a brief description of the deferred routing-audit-v2 work plus a pointer to `RELAY_V2.md` so it's discoverable from the project-level backlog after this initiative's folder becomes a historical record.

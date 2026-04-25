# PCB Routing Audit Tool — Relay to v2

> **Why this file exists:** v1 of the routing audit tool is shipped and applied. This document is a deliberate workflow override of `.context/WORKFLOW.md`'s "no orphan documents" rule (BRIEF / PLAN / TASKS only) — it lives here as a fourth file so a future session can spin up v2 without having to spelunk through this initiative's history. Once v2 has its own initiative folder, this file becomes a static pointer and the v1 folder can settle into being a historical record.

## What v1 delivered

A two-stage, read-only routing audit pipeline for the project's KiCad PCBs, sitting alongside the existing `tools/pcb-context/extract.py` (placement-only) extractor. `tools/pcb-context/routing_extract.py` reads a `.kicad_pcb` via `kiutils` and produces a `pcb-routing-context.json` artifact (per-net segments + vias, per-footprint pads in world-space, per-layer footprint bboxes, total length per net, length-by-layer). `tools/pcb-context/routing_audit.py` then consumes that JSON plus a small declarative audit spec (target nets, noisy components, noisy pads, noisy nets, compare pair) and emits a JSON report plus a Markdown report covering per-net length, per-layer length, and minimum clearance from each target net to each noisy element — layer-aware throughout, using `Shapely` for the 2D geometry. The first applied audit (`tools/pcb-context/audit-specs/v7-main-i2c.json` → `tools/pcb-context/audit-specs/v7-main-i2c.audit.{json,md}`) was used to settle the long-running routing-asymmetry hypothesis in the v7 I2C investigation: `docs/debugging/v7-i2c-investigation.md` Phase 16 (line 564 onward) embeds the Markdown verbatim and concludes the hypothesis is **weakened, not supported** by the measured geometry, redirecting the investigation toward the receiver-side (BQ24195) story.

## v1 artifacts

- `docs/initiatives/pcb-routing-audit-tool/BRIEF.md` — original intent, goals, scope, and the canonical "What's out" list that this relay leans on
- `docs/initiatives/pcb-routing-audit-tool/PLAN.md` — design (kiutils + Shapely, two-stage pipeline, output schemas, verification approach)
- `docs/initiatives/pcb-routing-audit-tool/TASKS.md` — execution checklist for v1 (all phases checked off through Phase 3; Phase 4 is this relay)
- `tools/pcb-context/routing_extract.py` — `.kicad_pcb` → `pcb-routing-context.json` (segments, vias, world-space pads, per-layer bboxes, length aggregates; `--list-nets` for net discovery)
- `tools/pcb-context/routing_audit.py` — `pcb-routing-context.json` + audit spec → JSON + Markdown report (net-vs-component, net-vs-pad, net-vs-net min clearance, layer-aware; asymmetry diff for a named pair)
- `tools/pcb-context/audit-specs/v7-main-i2c.json` — the first audit spec; worked example of the spec format
- `tools/pcb-context/audit-specs/v7-main-i2c.audit.json` — machine-readable audit output for v7
- `tools/pcb-context/audit-specs/v7-main-i2c.audit.md` — human-readable audit output for v7 (also embedded in the v7 I2C debug doc)
- `tools/pcb-context/README.md` — usage examples for both scripts and audit-spec authoring guide
- `docs/debugging/v7-i2c-investigation.md` Phase 16 (line 564) — the v7 audit applied, interpreted, and the verdict on the routing-asymmetry hypothesis
- `hardware/pcb-main/kicad/pcb-routing-context.json` — the extracted context for the v7 main PCB (lives next to the existing `pcb-layout-context.json`)

## Deferred items

These are carried over from v1's BRIEF.md "What's out" list. Each item gets one line restating it and one line on a concrete v2 use case.

- **Pad-to-pad path-distance via segment graph traversal.** v1 reports total per-net length and per-layer length, not the routed distance from a specific pad to another specific pad along the actual trace. Use case for v2: answering "how far does the SDA signal travel from the ESP32 pad to the BQ24195 pad along the routed copper, broken down by layer and via count?", which v1 cannot answer because it can't decompose a multi-pad net into per-pad-pair routes.
- **Trace impedance, signal-integrity math, EM-coupling modeling, current density, via thermal analysis.** v1 is a geometry tool, not a SI tool. Use case for v2: take the geometry v1 already extracts, combine it with stackup data, and emit characteristic-impedance estimates per segment — enough to flag impedance discontinuities or compute approximate coupling between adjacent traces, without trying to be a full field solver.
- **Cross-PCB comparison (e.g., automated v7-vs-v8 routing diff).** v1 audits one PCB at a time; v7-vs-v8 comparison today is manual (run the audit twice, eyeball the deltas). Use case for v2: given two `pcb-routing-context.json` files and a shared audit spec, emit a side-by-side diff (length deltas, clearance deltas, layer-routing deltas) — directly relevant the moment a v8 main PCB enters layout, since the v7 I2C debug doc's Phase 15 conclusion already names "v8 design with an I2C buffer between the upstream bus and BQ" as independently justified.
- **Editing the `.kicad_pcb`.** v1 is read-only by design and v2 should stay that way unless a very strong use case appears. Mentioned for completeness; not a candidate for v2.

## Suggested v2 first deliverables

Ranked by what would actually help next on this project, given what's on deck (v8 main PCB design starting in parallel with the v7 scope investigation, per `docs/debugging/v7-i2c-investigation.md` Phase 15):

1. **Cross-PCB comparison (highest value).** A v8 main PCB is explicitly on the roadmap and the obvious failure mode is "we redesigned it but didn't actually improve the routing where it counts." A v7-vs-v8 routing diff against a shared audit spec would catch regressions in the same metrics v1 already measures, with no new physics — it's mostly a presentation and spec layer over what v1 already produces. Lowest-risk, highest-leverage starting point.
2. **Pad-to-pad path-distance.** Once a v8 layout exists, the next natural question is "where exactly does the SDA path differ between v7 and v8 on the BQ side?" Pad-to-pad path lengths along the actual routed copper (with via penalties) make that question precisely answerable. Builds on the same `pcb-routing-context.json` schema by adding a graph-traversal layer; doesn't require new extraction.
3. **Stretch: light SI estimates (impedance / adjacent-trace coupling).** Once geometry diffing and pad-to-pad routing are solid, a thin SI layer on top — characteristic-impedance estimates per segment given a stackup file, and a "which adjacent trace runs in parallel for how many mm at how close a spacing" computation — would graduate the tool from geometry into early-warning SI without trying to be HFSS. Realistic only if the first two land cleanly.

These are *suggestions, not commitments*. v2 should re-evaluate priorities against whatever the project state actually is when v2 kicks off — the BQ scope investigation may have changed the landscape by then.

---

## Planning prompt for a fresh v2 session

> **Instructions to the AI session reading this:** you are being asked to draft the v2 initiative documents for the PCB Routing Audit Tool. Everything you need is in this file plus the files it points at. Follow the steps below in order.

**Project context.** Motion Play is an ESP32-based motion-sensor system. The hardware lives in `hardware/pcb-main/kicad/` (current revision: v7, ordered April 2026 — see the `project_pcb_revision_apr2026` memory note). The v7 main PCB has an open I2C debug investigation tracked in `docs/debugging/v7-i2c-investigation.md`; that investigation is the original motivating use case for the routing audit tool. Project-level conventions live in `.context/PROJECT.md`, `.context/WORKFLOW.md`, and `.context/IDEAS.md`. Tools-folder conventions (especially "do not read `.kicad_pcb` directly outside this tool") live in `tools/CONTEXT.md`.

**Your goal.** Produce a v2 initiative folder at `docs/initiatives/pcb-routing-audit-tool-v2/` with three documents — `BRIEF.md`, `PLAN.md`, `TASKS.md` — written in the same style and structure as the v1 initiative. Do not start implementation. The output of this session is the planning docs; a separate session will execute them.

**Required reading (in this order).**

1. `.context/WORKFLOW.md` — how initiatives are structured. Pay attention to the BRIEF/PLAN/TASKS templates and the "no orphan documents" rule. (This relay file is a deliberate exception to that rule for the v1→v2 handoff; v2's own folder should follow the rule strictly.)
2. `.context/PROJECT.md` — project-level context.
3. `tools/CONTEXT.md` — rules for tools that touch hardware artifacts.
4. `docs/initiatives/pcb-routing-audit-tool/BRIEF.md` — v1 intent, scope, and the canonical "What's out" list.
5. `docs/initiatives/pcb-routing-audit-tool/PLAN.md` — v1 design. Especially the schemas for `pcb-routing-context.json` and the audit report; v2 will likely extend rather than replace these.
6. `docs/initiatives/pcb-routing-audit-tool/TASKS.md` — v1 execution log; useful for sizing v2 work realistically.
7. The four sections of *this* file above the prompt (`What v1 delivered`, `v1 artifacts`, `Deferred items`, `Suggested v2 first deliverables`).
8. Skim only: `tools/pcb-context/routing_extract.py`, `tools/pcb-context/routing_audit.py`, `tools/pcb-context/audit-specs/v7-main-i2c.json`, and the `audit-specs/v7-main-i2c.audit.md` output. You don't need to deeply understand the code — just the inputs, outputs, and where v2 features would plug in.
9. `docs/debugging/v7-i2c-investigation.md` Phase 16 (line 564) — to understand how v1 was actually used and what shape v2 outputs should fit into when embedded in a debug doc.

**What v2 should decide (without committing to a specific design — that's for PLAN.md to draft).**

- Which deferred items from the list above are in scope for v2 vs deferred again to v3. (The "Suggested v2 first deliverables" section above is a starting point, not a mandate. Re-evaluate against current project state.)
- Whether v2 extends the existing scripts (`routing_extract.py`, `routing_audit.py`) or adds new ones (e.g., `routing_diff.py` for cross-PCB comparison, `routing_path.py` for pad-to-pad). Prefer the option that keeps the schemas stable and reusable.
- Whether the `pcb-routing-context.json` schema needs new fields (most v2 features are likely *consumers* of the existing schema rather than producers — if you find yourself wanting to add fields, sanity-check that they aren't computable from what's already there).
- Audit-spec format evolution: backward-compatible additions only, or a versioned spec format? Lean toward additive for v2.

**Constraints to carry over from v1.**

- Read-only with respect to `.kicad_pcb`. Do not break this.
- `kiutils` for parsing, `Shapely` for geometry. No `pcbnew` Python API (KiCad's bundled interpreter is not portable). New dependencies need explicit justification.
- Honor the project rule that `.kicad_pcb` is read only via `tools/pcb-context/`. Other tools must consume the JSON artifacts.
- Verification: every new metric needs at least one spot-check against KiCad's built-in tools at ±0.05 mm tolerance before it counts as working. v1's verification methodology in `PLAN.md` is the template.

**Deliverables for this session.**

1. Create `docs/initiatives/pcb-routing-audit-tool-v2/`.
2. Write `BRIEF.md` (intent, goals, scope with explicit "What's in" / "What's out", constraints) — under half a page, plain language, no implementation details.
3. Write `PLAN.md` (approach, technical notes, open questions) — reference v1's schemas where v2 reuses them, sketch new schemas where v2 extends them.
4. Write `TASKS.md` (phases, concrete actionable tasks). Mirror v1's phase structure: extractor work (if any) first, auditor / new-tool work next, first applied deliverable last. Include verification tasks per phase.
5. Reference this relay file in v2's `BRIEF.md` so the handoff chain stays discoverable.
6. Do not modify v1's BRIEF/PLAN/TASKS or the routing scripts — v1 is closed.
7. Do not start implementation. Stop after the three docs are written.

**Style notes.** Match the tone of v1's initiative docs — concrete, verification-oriented, willing to defer aggressively to keep scope tight. v1 shipped in one focused session because it deferred everything that wasn't strictly needed for the v7 question; v2 should make the same kind of deliberate cut.

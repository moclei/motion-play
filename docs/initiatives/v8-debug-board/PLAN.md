# v8 Main Board — Debug Board — Plan

## Approach

Four strands, run in sequence in one initiative. They share one board model and one design-intent file.

1. **Power-path investigation (desk → bench → design).** Workers trace v7's battery and power path from the schematic and the datasheets. They root-cause the BQ24195 "needs I²C" fault and rank the mechanisms by which battery connection could cook a board. They then write a bench relay for the Debugger (`debugger/RELAY-power.md`). The Debugger runs the bench work on #0001, #0002 and #0004 as lab cards, outside this initiative. The v8 power design (Phase 7) is gated on those findings (wait **W1**).
2. **v8 design intent and schematic.** One design-intent file, `hardware/pcb-main-v8/CONTEXT.md`, holds every v8 decision: the GPIO allocation, the jumper matrix (with v7 and v8 positions), the test-point and ground-point list, debug LEDs, part choices, and inherited v7 faults with their fixes. The schematic is built from it with the schematic tools. Workers can't do some schematic steps (wiring and Update-PCB-from-schematic are GUI-only today), so those become user steps with exact instructions.
3. **Board model (audit phases 1–2).** `kicad-extraction-audit.md` §5–§6.1 is the spec: one parser and one model, with zones (de-fractured fills), stackup, true pad polygons, bodies, outline, net topology and provenance. Reports are derived from the model: net-centric, plane/region, and per-net PNGs. It is validated on v7 against the audit's fixture table. This model then feeds both the AI layout work and the partner review. It absorbs the queued `pcb-board-model` initiative (decisioning §3.2a row 2) and supersedes the never-run `routing-verification` initiative.
4. **AI layout, learning as we go.** Placement and routing are trialled in small, reviewed steps. Each step follows the same loop: Worker writes a placement or routing with a script, then the user reviews it and corrects it in KiCad. A Worker diffs the user's corrections against what it wrote (board model, before vs after) and turns each correction into a rule in `tools/pcb-context/` (rules config and CONTEXT). The next step runs with the updated rules. Placement goes block by block, then the whole board. Routing is tentative: AI routes the low-risk nets, and the user owns the nets in OQ-1.

Review before ordering = the user's review + an AI partner review answered from board-model output (no throwaway probes), with targeted questions fixed in advance (Technical Notes). DRC/ERC clean. Then fab outputs, preflight (stock, BOM/CPL), user places the order (**W-order**).

## Technical Notes

**Sources to load per task (cite, don't recall).** `lab/STATE.md` §1–§4 and §8 (read-only); notebook entries 2026-10-27 desk (e), 2026-10-31 (checkpoint + decision), 2026-11-02 (decision); cards V7R-018, V7R-019, V7R-020; `docs/research/v7-retry/v6-v7-changelist.md` (CL-IDs); `kicad-extraction-audit.md` §3–§6.1; `decisioning.md` §4.1–4.2; `docs/references/{bq24195,tps61088,ina219}/DATASHEET_REFERENCE.md`; `hardware/CONTEXT.md`; `tools/CONTEXT.md`; `firmware/src/main.cpp` `configureBQ24195()` (the workaround: D+/D− tied to GND → default IINLIM, plus the 40 s watchdog).

**Folders.** v7 stays untouched at `hardware/pcb-main/kicad/` (the debug track, its probe-points files and cards cite those paths at `c2acffc`). v8 lives in `hardware/pcb-main-v8/kicad/`, started from a copy of the v7 project: schematic carried over and edited, layout restarted on a new outline. `hardware/pcb-main-v8/CONTEXT.md` is the design-intent file (an aspect CONTEXT per PROJECT.md, not an initiative doc).

**Jumper matrix (candidates; Phase 3 fixes the final list with the user).** Each row records: v7 position, v8 position, v6 position where it differs, the map row / CL-ID it toggles, and the implementation (solder jumper, 0 Ω, or 2-pin header).
| # | Toggles | Source |
|---|---|---|
| a | SDA/SCL master pins: GPIO43/44 vs a free pad pair (GPIO43/44 then free as UART0 for the boot log) | relay §2a; V7R-019; CL-02 |
| b | Cable-facing channel SDA/SCL protection (TVS + series R): fitted vs bypassed | relay §2b; notebook 2026-10-31 candidate (1) |
| c | MCU 3.3 V and pull-up/bus rail: shared (v7) vs separate regulators (v6) | relay §2c; CL-03, CL-08 |
| d | On-board pull-up values selectable (upstream; downstream per channel optional) | relay §2d |
| e | Master isolation: break SDA/SCL at the module so an external master (header) can drive the bus | V7R-004 / F-12 method; candidate |
| f | BQ24195 I²C isolate (symptom identity: causal row, untested) | STATE §3; L-Ph8 |
| g | LED_DATA on its own GPIO (GPIO16 freed as a bus candidate) | desk (e) |
| h | Rail current-measure links (0 Ω / jumper per rail) | debug goal |

**Partner review: targeted questions (Phase 18).** (1) Every member of each SDA/SCL net, its route, neighbours within the audit radii, and reference plane, in each jumper position. (2) What protects each cable-facing line, and where. (3) Battery → charger → boost → LDO path vs the Phase 2/7 failure mechanisms. (4) For each jumper in its v7 position, the net topology matches v7's (schematic level; the copper is new by design). (5) Every test point has a ground point within spring reach. (6) Antenna keepout, USB pair, switching loops.

**Board-model decisions (audit §6.1).** Generated outputs are committed with `_provenance` (tools/CONTEXT.md Source-Hash Rule). The stale v7 `pcb-layout-context.json` / `drc-report.json` are marked historical, not deleted (the debug track cites `c2acffc` files). kiutils + kicad-cli are used; pcbnew Python is not (OQ-3). Definitions (high-current, high dv/dt, neighbour radii, edge-to-edge clearance) go in a per-board config file, seeded from audit §6.1.

**AI layout tooling.** It generalises `place_power.py`'s kiutils write path (KiCad must be closed while it writes). The rules config holds constraints that can be checked (keepouts, decoupling distance, test-point spacing, connector edges). Placement runs: board model in → placement → write → board-model check (overlaps, courtyards, rules) → render PNG → user review. The user's corrections are measured as a before/after model diff of positions only, so this needs no diff mode.

**Firmware.** A `motion-play-v8` env with the pin set chosen at build time to match jumper (a), plus a v8 diag image. No v7 env changes.

**User waits.**
- **W1:** the power bench findings have landed (Debugger card IDs cited).
- **W2:** the design intent is approved.
- **W3:** schematic review.
- **W4–W6:** placement and routing reviews.
- **W7:** pre-order review.
- **W-order:** the order is placed.

## Rejected Approaches
- Separate `pcb-board-model` initiative run first: folded in, because v8 layout and review are its only consumer now and the user wants one initiative at a time.
- Targeted review via throwaway kiutils probes only: user wants reusable scripts for partner review.
- Fixing the BQ fault in firmware only (current `configureBQ24195()`): the brief asks for a design root cause.

## Open Questions
- OQ-1 (by Phase 16): which nets AI may route. Default: the user routes switching power (BQ_SW, BOOST_SW loops), the USB pair and battery/high-current paths. AI routes test-point stubs, LEDs, jumpers and the I²C channels, and the user reviews them.
- OQ-2 (by Phase 3): add a second master footprint (e.g. DevKitC-1 headers, or a header for an external S3/SAMD21) behind jumper (e)? This gives an on-board module vs dev-board A/B.
- OQ-3 (by Phase 13): kiutils-only writes, or allow pcbnew Python / Freerouting for routing experiments and zone refill?
- OQ-4 (by Phase 3): board size ceiling. JLC pricing steps at 100 × 100 mm. Is 18650 on-board or on a cable?
- OQ-5 (by Phase 3): debug-track inputs still pending: card (j), pad-37 joint vs inside the module, bears on the U3 footprint/pad and on jumper (a).
- ~~OQ-6 (protocol): no initiative → Debugger relay row~~ Resolved 2026-11-02: row added to PROTOCOL.md; relays go in `debugger/`.
- OQ-8 (by Phase 2 end): Debugger home for non-v7 investigations. Design agreed 2026-11-02: each new investigation gets `lab/investigations/STATE-<PREFIX>.md` with its own card prefix (`lab/cards/<PREFIX>-NNN-<slug>.md`). The folder is the registry: card prefix and open/closed come from each STATE file's front matter (file names are free-form, e.g. `STATE-v7-I2C.md` for prefix `V7R`). NOTEBOOK, procedures, templates, log, evidence and relays stay shared. The v7 state moved to `lab/investigations/STATE-v7-I2C.md` on 2026-11-02 (branch `chore/lab-investigations-move`, paths only). `tools/lab/` (card regex, check_state, precommit) is generalised, and the debugger role draft gains an investigation choice at session start (the user edits the role). Still open: whether the build is a v8 phase before the power relay or a separate small initiative.
- ~~OQ-7 (housekeeping): retire/archive `routing-verification`~~ Resolved 2026-11-02: moved to `docs/initiatives/archive/` (with `pcb-layout-context`, `esp32-integration`, `integrated-power`). The `tools/CONTEXT.md` wording about "the board-model initiative" is fixed in Phase 6.

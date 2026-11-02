# v8 Main Board — Debug Board — Tasks

> Waits W1–W7 and W-order are defined in PLAN Technical Notes. A task marked **(user)** is done by the user. The Worker prepares exact instructions for it, then stops and reports. Never read or edit `.kicad_sch` / `.kicad_pcb` text directly (tools/CONTEXT.md). Nothing under `lab/` is edited by this initiative.

## Phase 1: Power path — v7 trace and BQ root cause (desk)

- [ ] Re-extract v7 `circuit-context.json` from `c2acffc` to scratch (`tools/schematic-context/extract.py`) and confirm it matches the committed copy. List every component and net on the battery → charger → boost → LDO path (BT1, Q2, R34, BAT_RAW, VBAT, PMID, VSYS, VSYS_SENSE, SW1/BOOST_EN, U5, U6, U8, TS network, ILIM R32, D+/D−), with pin → net. Cite CL-09, CL-11, CL-14
- [ ] Check Q2's symbol/footprint pin mapping against the part's datasheet pinout (v6 used a SPICE symbol, CL-09), and BT1's polarity marking against the footprint's +/− pads
- [ ] Root-cause "BQ needs an I²C command" from `docs/references/bq24195/DATASHEET_REFERENCE.md`: input source detection with D+/D− tied to GND, ILIM pin vs IINLIM register, watchdog expiry and register reset, HIZ/VINDPM. State the root cause, and list hardware fix options (keep BQ24195 with pin changes, or swap to a part that needs no I²C to run at the target current), each with trade-offs
- [ ] Create `hardware/pcb-main-v8/CONTEXT.md` with sections: Purpose, Inherited v7 faults, Power path, GPIO allocation, Jumper matrix, Test points, Parts, Layout rules pointer. Fill only Purpose and Inherited v7 faults → BQ (root cause + options, with citations)
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 2: Power path — battery failure mechanisms and bench relay (desk)

- [ ] Rank the mechanisms by which connecting a battery could cook a v7 board. Cover at least: reverse insertion in BT1, the Q2 orientation and gate drive, hot-plug inrush/ringing on BAT, abs-max on every BAT_RAW/VBAT/VSYS member, the TS network, the boost enabled into a load at plug-in, and BT1 body over B.Cu copper (CL-10, CL-20). Each gets the datasheet value, which board observation would confirm or refute it, and whether the test is reversible
- [ ] Explain #0004's state (V7R-020 card: +5 V ≈ 3.75 V, +3.3 V ≈ 2.69 V, no USB device) and #0005's brownout loop and missing BQ, against the same path. Mark everything argued
- [ ] Write `docs/initiatives/v8-debug-board/debugger/RELAY-power.md` (PROTOCOL relay template, role: Debugger). Include: the boards (#0001, #0002, #0004, user supplies), a non-destructive-first bench sequence (visual/thermal, per-rail resistance to GND, diode-mode on Q2/U5/U6/U8 pins, then powered from a current-limited supply on each input), what each result discriminates between, and an explicit "no change to the debug track's order unless the user says so"
- [ ] Fill `hardware/pcb-main-v8/CONTEXT.md` Inherited v7 faults → battery (ranked mechanisms, pointer to the relay)
- [ ] Tell the user the relay is ready (W1 opens), and check OQ-8 is settled
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 3: Design intent — GPIO, jumpers, test points (desk)

- [ ] Re-read the card V7R-019 conclusion, the notebook 2026-10-31 decision and 2026-11-02 entries, and STATE §8. Record which debug-track inputs have landed since this plan was written (card (j), etc., OQ-5)
- [ ] GPIO allocation table for U3 (WROOM-1-N16R8 pinout, strapping pins, USB, PSRAM-reserved pins): SDA/SCL default pair and alternate pair, UART0 freed for the boot log, LED_DATA, TCA_RESET, CHRG_INT, INT1–3, debug LEDs, spare GPIOs out to test points
- [ ] Jumper matrix: take PLAN rows a–h and add any others the changelist §3 supports. For each: v7/v8/v6 position, map row or CL-ID, implementation type, default. Present OQ-2 and OQ-4 to the user with options, and record the answers
- [ ] Test-point and ground-point list: every I²C net on both sides of the TCA (upstream + CH0–CH2 SDA/SCL), every rail (VBUS, PMID, VSYS, VBAT, BAT_RAW, +5V, each +3.3V), spare GPIOs, UART0; ground point within spring reach of each. Debug LEDs (which signals, which colours)
- [ ] Fill the matching `hardware/pcb-main-v8/CONTEXT.md` sections. **W2 (part 1):** user approves GPIO allocation, jumper matrix and test-point list
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 4: Design intent — parts (non-power)

- [ ] Cable-facing protection for CH0–CH2 SDA/SCL: TVS array (low capacitance, 3.3 V working voltage) and series R value. Justify against I²C rise time with 4.7 k (rigid) and on-board pull-ups. LCSC part + stock via the JLC MCP
- [ ] Footprints: solder jumpers (2- and 3-way), 0 Ω links, test-point pads sized for the Sensepeek/Rigol tips, ground-spring points. Prefer KiCad stock libraries, and record each footprint name
- [ ] Debug LEDs, pull-up option resistors, header(s) for an external master / UART0 (if OQ-2 says yes). Stock check
- [ ] Review the remaining v7 parts (TCA9548A, INA219, SN74AHCT125, WS2812B-MINI, USBLC6, connectors) for swap candidates. Note only those with a reason. Stock check for everything kept
- [ ] Fill `hardware/pcb-main-v8/CONTEXT.md` Parts. **W2 (part 2):** user approves the parts list
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 5: Board model — parse and validate (audit phase 1)

- [ ] Install matplotlib for Python 3.7 (check the wheel installs; if it doesn't, record it in PLAN Open Questions and stop). Confirm shapely 2.0.7 and kicad-cli 9.0.4 at the app path
- [ ] `tools/pcb-context/board_model.py`: one parse into one model, covering footprints (true pad polygons, rotated; `*.Cu` expanded), bodies (courtyard/fab fallback), outline polygon, segments/arcs/vias, zones (outline + de-fractured fills with holes, keepouts, priority, a warning on unfilled zones), stackup from `setup`, net topology graph (pads, vias, junctions; branches and stubs), `_provenance` + `--check`, kicad-cli DRC in the run
- [ ] Per-board config file with the audit §6.1 definitions (high-current, high dv/dt seed list, neighbour radii, edge-to-edge clearance)
- [ ] Validate on v7 `c2acffc`: every audit §6.1 fixture row (SDA 72.9 mm F 35.9 / B 37.0, 3 vias; branch lengths; gaps; the In2 reference split; BT1 body length; 8 zones). Record each value and its delta in SESSION.md
- [ ] Mark v7's stale `pcb-layout-context.json`, `drc-report.json` and `placement-report.json` as historical in `tools/pcb-context/README.md` (don't delete them)
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 6: Board model — reports and images (audit phase 2)

- [ ] `net_report.py`: the net-centric Markdown + JSON (route narrative from the topology, neighbours within the radii across layers, coupled length, reference plane per segment), with provenance front matter
- [ ] `plane_report.py`: per-layer copper ownership, splits, voids, mm unreferenced per signal segment, GND stitching density
- [ ] `render.py`: one PNG per critical net and per plane layer (outline, faded footprints, net by layer, labelled pads/vias, neighbours highlighted) + `.meta.json`
- [ ] Acceptance: answer the audit §3 SDA acid test from the outputs alone, and match the audit's numbers. Look at each PNG and check the labels sit on their pads
- [ ] Update `tools/CONTEXT.md` (the pcb-context section; the board model replaces the "board-model initiative" wording) and `tools/pcb-context/README.md`
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 7: Power path design

- [ ] **W1:** confirm with the user that the power bench findings have landed, and list the Debugger card IDs. If they haven't, stop and report `BLOCKED: W1`
- [ ] Choose the charger/power-path IC (BQ24195 with a hardware fix, or a swap), using the Phase 1 options and the bench findings. Battery connection: holder vs connector (OQ-4), reverse-polarity and inrush protection, where the fuse sits. Each decision cites the mechanism it addresses
- [ ] Boost and enable, LDO(s): jumper (c) needs a separate bus/pull-up regulator option. Choose parts with dropout margin from the actual +5 V. Add a current-measure link per rail (jumper h)
- [ ] Stock check every power part. Fill `hardware/pcb-main-v8/CONTEXT.md` Power path. Write the schematic-gen spec JSON for the power sheet under `tools/schematic-gen/` (v8-named)
- [ ] User approves the power path (closes W2)
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 8: Schematic — project setup and MCU sheet

- [ ] Copy the v7 KiCad project (`c2acffc`) to `hardware/pcb-main-v8/kicad/`, renamed to `motion-play-main-v8`. Start with a fresh, empty `.kicad_pcb` that has the stackup only. Check it opens and runs ERC with kicad-cli
- [ ] MCU sheet edits per GPIO allocation and jumpers (a), (e), (g): an initiative script under `tools/schematic-modify/` (v8-named) using `modify.py` helpers
- [ ] List any wiring the tools can't do as numbered **(user)** steps. User does them; Worker re-extracts and checks pin → net against the GPIO allocation table
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 9: Schematic — TCA, bus and channels

- [ ] Jumpers (b), (d), (f) and the cable-facing protection on CH0–CH2, the upstream/downstream pull-up options, BQ I²C isolate, and channel test points
- [ ] **(user)** steps for wiring the tools can't do. Worker re-extracts and checks each jumper's two positions give the expected net membership (v7 position = v7 netlist membership for that net)
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 10: Schematic — power sheet

- [ ] Generate or modify the power sheet from the Phase 7 spec. Jumpers (c), (h). Rail test points
- [ ] **(user)** steps where needed. Worker re-extracts and checks every power net's membership against `hardware/pcb-main-v8/CONTEXT.md` Power path
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 11: Schematic — debug features, ERC, freeze

- [ ] Remaining test points, ground points, debug LEDs, UART0 header. Every part has an LCSC number and footprint (or is marked hand-fit)
- [ ] ERC clean (or each waived item listed with a reason). `circuit-context.json` extracted with `_provenance`; `annotate.py` for new parts
- [ ] Audit against `hardware/pcb-main-v8/CONTEXT.md`: every jumper, test point and LED is present; every v7 position reproduces v7 membership. Write the result in SESSION.md
- [ ] **W3:** user reviews the schematic in KiCad. Apply the fixes, re-run ERC, and tag the commit as the schematic freeze
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 12: Firmware — v8 env

- [ ] Add a `motion-play-v8` env and a v8 pin config selected at build time to match jumper (a) (default pair and alternate pair), with UART0 boot log available when the bus is off GPIO43/44. Add a v8 diag env. No change to v7 envs
- [ ] Hardware BQ fix reflected: `configureBQ24195()` (or its replacement) is kept or dropped per the Phase 7 part choice, with the reason in a code comment
- [ ] Build every v8 env and every existing v7 env (no regressions)
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 13: AI placement — tooling (dry run on v7)

- [ ] Present OQ-3 to the user and record the answer
- [ ] `tools/pcb-context/place.py`: generalises `place_power.py`. It reads the board model and a rules config, and writes footprint positions/rotations/sides via kiutils (refuses if a KiCad lock file exists). `--dry-run` renders a PNG
- [ ] Rules config (`tools/pcb-context/rules/<board>.yaml` or JSON): keepouts, edge connectors, decoupling-to-pin max distance, test-point spacing and ground-point pairing, courtyard clearance, groups (block membership from `ai_block` annotations)
- [ ] `place_check.py`: overlaps, courtyard and outline violations, rule violations, from the board model. Dry run: re-place one v7 block (e.g. TCA + pull-ups) in a scratch copy and check it. Record what the rules couldn't express
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 14: AI placement — v8 first blocks

- [ ] **(user)** in KiCad: Update PCB from Schematic into the empty v8 board. Worker defines the outline (OQ-4), mounting holes, the antenna keepout and the edge connectors via the tools
- [ ] Place the module, power path and connector blocks with `place.py`. `place_check.py` clean. Render
- [ ] **W4:** user reviews and corrects in KiCad. Worker diffs before/after positions from the board model and turns each correction into a rule (or a note of why it can't be one) in the rules config + `tools/pcb-context/CONTEXT.md`. Log the corrections in SESSION.md
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 15: AI placement — rest of board

- [ ] Place the TCA/bus, jumper, test-point, LED and remaining blocks with the updated rules. `place_check.py` clean. Render
- [ ] **W5:** user reviews and corrects. Worker diffs and updates the rules as in Phase 14
- [ ] Retrospective in SESSION.md: corrections per block, Phase 14 vs 15, and which rules made the difference. Propose workflow changes to the user, and update `tools/pcb-context/CONTEXT.md`
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 16: AI routing — tentative subset

- [ ] Present OQ-1 to the user and record the net split (AI-routed vs user-routed)
- [ ] Routing writer (kiutils segments/vias, or the OQ-3 choice) for the AI net set, honouring the board config's clearances and widths. Run DRC via kicad-cli
- [ ] **W6:** user reviews: keep, fix or rip up per net. Worker diffs and records the lessons in `tools/pcb-context/CONTEXT.md`
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 17: Routing completion and zones

- [ ] **(user)** routes the user-owned nets and pours the zones/planes. Worker supplies a per-net checklist from the board config (widths, loop areas, reference planes)
- [ ] Zones refilled (kicad-cli or user). DRC clean, with each waived item listed. Board model + net/plane reports + renders regenerated with provenance
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 18: Pre-order partner review

- [ ] Answer each targeted question in PLAN Technical Notes from the board-model outputs only. Cite the report file and its provenance hash for each finding
- [ ] Re-check the design intent end to end: jumpers, test/ground points, LEDs, BQ fix, power-path mechanisms covered
- [ ] **W7:** go through the findings with the user next to their own review. Apply the agreed fixes, then re-run DRC/ERC and the reports
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 19: Fabrication and order

- [ ] Fab outputs: gerbers, drill, BOM, CPL (Fabrication Toolkit or kicad-cli), 5 assembled. Cross-check CPL rotations against footprints
- [ ] Preflight: stock for every LCSC part (BQ-class parts first), substitutions recorded as built (CL-14 lesson), hand-fit parts listed
- [ ] **W-order (user):** user places the order. Record the order date and any checkout substitutions in `hardware/pcb-main-v8/CONTEXT.md`
- [ ] Write the bring-up relay for the Debugger (`debugger/RELAY-bringup.md`): power-on sequence, the v7-config jumper set, and the A/B/A cards the board enables. Update PROJECT.md status line
- [ ] 🔄 Handoff

## Deferred

[from: v8-debug-board] Board-model diff mode (audit phase 3), v6 ↔ v7 ↔ v8 relational diff.
[from: v8-debug-board] Board-model run on the sensor-rigid and sensor-flex boards (audit says it must run on all three; validation is main-only here).

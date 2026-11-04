# v8 Main Board — Debug Board — Tasks

> Waits W1–W7 and W-order are defined in PLAN Technical Notes. A task marked **(user)** is done by the user. The Worker prepares exact instructions for it, then stops and reports. Never read or edit `.kicad_sch` / `.kicad_pcb` text directly (tools/CONTEXT.md). Nothing under `lab/` is edited by this initiative.

## Phase 1: Power path — v7 trace and BQ root cause (desk)

- [x] Re-extract v7 `circuit-context.json` from `c2acffc` to scratch (`tools/schematic-context/extract.py`) and confirm it matches the committed copy. List every component and net on the battery → charger → boost → LDO path (BT1, Q2, R34, BAT_RAW, VBAT, PMID, VSYS, VSYS_SENSE, SW1/BOOST_EN, U5, U6, U8, TS network, ILIM R32, D+/D−), with pin → net. Cite CL-09, CL-11, CL-14
- [x] Check Q2's symbol/footprint pin mapping against the part's datasheet pinout (v6 used a SPICE symbol, CL-09), and BT1's polarity marking against the footprint's +/− pads
- [x] Root-cause "BQ needs an I²C command" from `docs/references/bq24195/DATASHEET_REFERENCE.md`: input source detection with D+/D− tied to GND, ILIM pin vs IINLIM register, watchdog expiry and register reset, HIZ/VINDPM. State the root cause, and list hardware fix options (keep BQ24195 with pin changes, or swap to a part that needs no I²C to run at the target current), each with trade-offs
- [x] Create `hardware/pcb-main-v8/CONTEXT.md` with sections: Purpose, Inherited v7 faults, Power path, GPIO allocation, Jumper matrix, Test points, Parts, Layout rules pointer. Fill only Purpose and Inherited v7 faults → BQ (root cause + options, with citations)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 2: Power path — battery failure mechanisms and bench relay (desk)

- [x] Rank the mechanisms by which connecting a battery could cook a v7 board. Cover at least: reverse insertion in BT1, the Q2 orientation and gate drive, hot-plug inrush/ringing on BAT, abs-max on every BAT_RAW/VBAT/VSYS member, the TS network, the boost enabled into a load at plug-in, and BT1 body over B.Cu copper (CL-10, CL-20). Each gets the datasheet value, which board observation would confirm or refute it, and whether the test is reversible
- [x] Explain #0004's state (V7R-020 card: +5 V ≈ 3.75 V, +3.3 V ≈ 2.69 V, no USB device) and #0005's brownout loop and missing BQ, against the same path. Mark everything argued
- [x] Write `docs/initiatives/v8-debug-board/debugger/RELAY-power.md` (PROTOCOL relay template, role: Debugger). Include: the boards (#0001, #0002, #0004, user supplies), a non-destructive-first bench sequence (visual/thermal, per-rail resistance to GND, diode-mode on Q2/U5/U6/U8 pins, then powered from a current-limited supply on each input), what each result discriminates between, and an explicit "no change to the debug track's order unless the user says so"
- [x] Fill `hardware/pcb-main-v8/CONTEXT.md` Inherited v7 faults → battery (ranked mechanisms, pointer to the relay)
- [x] Tell the user the relay is ready (W1 opens), and confirm `lab-multi-investigation` is merged (otherwise the relay waits)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 3: Design intent — GPIO, jumpers, test points (desk)

- [x] Re-read the card V7R-019 conclusion, the notebook 2026-10-31 decision and 2026-11-02 entries, and STATE §8. Record which debug-track inputs have landed since this plan was written (card (j), etc., OQ-5)
- [x] GPIO allocation table for U3 (WROOM-1-N16R8 pinout, strapping pins, USB, PSRAM-reserved pins): SDA/SCL default pair and alternate pair, UART0 freed for the boot log, LED_DATA, TCA_RESET, CHRG_INT, INT1–3, debug LEDs, spare GPIOs out to test points
- [x] Jumper matrix: take PLAN rows a–h and add any others the changelist §3 supports. For each: v7/v8/v6 position, map row or CL-ID, implementation type, default. Present OQ-2 and OQ-4 to the user with options, and record the answers
- [x] Test-point and ground-point list: every I²C net on both sides of the TCA (upstream + CH0–CH2 SDA/SCL), every rail (VBUS, PMID, VSYS, VBAT, BAT_RAW, +5V, each +3.3V), spare GPIOs, UART0; ground point within spring reach of each. Debug LEDs (which signals, which colours)
- [x] Fill the matching `hardware/pcb-main-v8/CONTEXT.md` sections. **W2 (part 1):** user approves GPIO allocation, jumper matrix and test-point list
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 4: Design intent — parts (non-power)

- [x] Cable-facing protection for CH0–CH2 SDA/SCL: TVS array (low capacitance, 3.3 V working voltage) and series R value. Justify against I²C rise time with 4.7 k (rigid) and on-board pull-ups. LCSC part + stock via the JLC MCP
- [x] Footprints: solder jumpers (2- and 3-way), 0 Ω links, test-point pads sized for the Sensepeek/Rigol tips, ground-spring points. Prefer KiCad stock libraries, and record each footprint name
- [x] Debug LEDs, pull-up option resistors, header(s) for an external master / UART0 (if OQ-2 says yes). Stock check
- [x] Review the remaining v7 parts (TCA9548A, INA219, SN74AHCT125, WS2812B-MINI, USBLC6, connectors) for swap candidates. Note only those with a reason. Stock check for everything kept
- [x] Fill `hardware/pcb-main-v8/CONTEXT.md` Parts. **W2 (part 2):** user approves the parts list
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 5: Board model — parse and validate (audit phase 1)

- [x] Install matplotlib for Python 3.7 (check the wheel installs; if it doesn't, record it in PLAN Open Questions and stop). Confirm shapely 2.0.7 and kicad-cli 9.0.4 at the app path
- [x] `tools/pcb-context/board_model.py`: one parse into one model, covering footprints (true pad polygons, rotated; `*.Cu` expanded), bodies (courtyard/fab fallback), outline polygon, segments/arcs/vias, zones (outline + de-fractured fills with holes, keepouts, priority, a warning on unfilled zones), stackup from `setup`, net topology graph (pads, vias, junctions; branches and stubs), `_provenance` + `--check`, kicad-cli DRC in the run
- [x] Per-board config file with the audit §6.1 definitions (high-current, high dv/dt seed list, neighbour radii, edge-to-edge clearance)
- [x] Validate on v7 `c2acffc`: every audit §6.1 fixture row (SDA 72.9 mm F 35.9 / B 37.0, 3 vias; branch lengths; gaps; the In2 reference split; BT1 body length; 8 zones). Record each value and its delta in SESSION.md
- [x] Mark v7's stale `pcb-layout-context.json`, `drc-report.json` and `placement-report.json` as historical in `tools/pcb-context/README.md` (don't delete them)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 6: Board model — reports and images (audit phase 2)

- [x] `net_report.py`: the net-centric Markdown + JSON (route narrative from the topology, neighbours within the radii across layers, coupled length, reference plane per segment), with provenance front matter
- [x] `plane_report.py`: per-layer copper ownership, splits, voids, mm unreferenced per signal segment, GND stitching density
- [x] `render.py`: one PNG per critical net and per plane layer (outline, faded footprints, net by layer, labelled pads/vias, neighbours highlighted) + `.meta.json`
- [x] Acceptance: answer the audit §3 SDA acid test from the outputs alone, and match the audit's numbers. Look at each PNG and check the labels sit on their pads
- [x] Update `tools/CONTEXT.md` (the pcb-context section; the board model replaces the "board-model initiative" wording) and `tools/pcb-context/README.md`
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 7: Power path design

- [x] **W1:** confirm with the user that the power bench findings have landed, and list the Debugger card IDs. If they haven't, stop and report `BLOCKED: W1`
- [x] Choose the charger/power-path IC (BQ24195 with a hardware fix, or a swap), using the Phase 1 options and the bench findings. Battery connection: holder vs connector (OQ-4), reverse-polarity and inrush protection, where the fuse sits. Each decision cites the mechanism it addresses
- [x] Boost and enable, LDO(s): jumper (c) needs a separate bus/pull-up regulator option. Choose parts with dropout margin from the actual +5 V. Add a current-measure link per rail (jumper h)
- [x] Stock check every power part. Fill `hardware/pcb-main-v8/CONTEXT.md` Power path. Write the schematic-gen spec JSON for the power sheet under `tools/schematic-gen/` (v8-named)
- [x] User approves the power path (closes W2)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 8: Schematic — project setup and MCU sheet

- [x] Copy the v7 KiCad project (`c2acffc`) to `hardware/pcb-main-v8/kicad/`, renamed to `motion-play-main-v8`. Start with a fresh, empty `.kicad_pcb` that has the stackup only. Check it opens and runs ERC with kicad-cli
- [x] MCU sheet edits per GPIO allocation and jumpers (a), (e), (g): an initiative script under `tools/schematic-modify/` (v8-named) using `modify.py` helpers
- [x] List any wiring the tools can't do as numbered **(user)** steps. User does them; Worker re-extracts and checks pin → net against the GPIO allocation table
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 9: Schematic — TCA, bus and channels

- [x] Jumpers (b), (d), (f) and the cable-facing protection on CH0–CH2, the upstream/downstream pull-up options, BQ I²C isolate, and channel test points
- [x] **(user)** steps for wiring the tools can't do. Worker re-extracts and checks each jumper's two positions give the expected net membership (v7 position = v7 netlist membership for that net)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 10: Schematic — power sheet

- [x] Generate or modify the power sheet from the Phase 7 spec. Jumpers (c), (h). Rail test points
- [x] **(user)** steps where needed. Worker re-extracts and checks every power net's membership against `hardware/pcb-main-v8/CONTEXT.md` Power path
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 11: Schematic — debug features, ERC, freeze

- [x] Remaining test points, ground points, debug LEDs, UART0 header. Every part has an LCSC number and footprint (or is marked hand-fit)
- [x] ERC clean (or each waived item listed with a reason). `circuit-context.json` extracted with `_provenance`; `annotate.py` for new parts
- [x] Audit against `hardware/pcb-main-v8/CONTEXT.md`: every jumper, test point and LED is present; every v7 position reproduces v7 membership. Write the result in SESSION.md
- [x] 🔄 Handoff (closed by the 2026-11-04 replan: Worker #11's notes and W3 guide are in SESSION.md, `2fb7e21`; W3 moved to Phase 11f)

> **Phases 11a–11f** were inserted by the 2026-11-04 replan, after the user opened the schematic for W3 and found it unreadable. Sources: `docs/research/kicad-ai-tooling-2026-11/schematic-readability.md` ("readability") and `landscape.md`, with prototypes in `prototypes/`. The user's decisions of 2026-11-04 are in PLAN Technical Notes → Schematic readability. KiCad must be closed (no `~*.lck` in `hardware/pcb-main-v8/kicad/`) whenever a script writes a schematic. The power/TCA re-layout is **not** a task: the user decides it at W3a (OQ-10).

# --- handoff point ---

## Phase 11a: Schematic tooling — kiutils KiCad 9 shim and field tidy

- [x] KiCad 8/9 shim for kiutils 1.4.8 (readability §3.1 step 1; prototype `prototypes/kiutils_k9_shim.py`): a module in `tools/schematic-modify/` that reads `(hide yes)` on effects and properties, and on `pin_numbers`/`pin_names`. Import it on every schematic load path: `modify.load_project`/`SheetDoc`, `tools/schematic-context/{annotate,extract,show}.py`, `v8_project_setup.py`, `v8_mcu_sheet.py`, and the `tools/schematic-gen/` generators (grep for `from_file`). `SheetDoc.save_all` (and any other schematic save, including annotate's) refuses while a `~*.kicad_sch.lck` exists in the project folder. Test in scratch: a load/save round trip of v7's three `c2acffc` sheets keeps every field's visibility and every pin_numbers/pin_names hide (readability §1.2: 496/99/49 flags). Report whether `fields_autoplaced` and `exclude_from_sim` are still dropped (readability §1.2, "Other things"); preserve `fields_autoplaced` if it is cheap. **Nothing else touches the v8 schematic before this lands.**
- [x] `annotate.write_ai_properties` (`annotate.py:134`): a new `ai_*` property takes its symbol's position and is hidden. Updating an existing `ai_*` also hides it and moves it to the symbol (readability §3.4)
- [x] `tools/schematic-modify/tidy_fields.py --check | --apply` (readability §3.1 steps 2–4; prototype `prototypes/hide_fields.py`): hide every placed-symbol field except Reference and Value; restore `pin_numbers`/`pin_names` hiding on embedded library symbols (from v7 `c2acffc` for the same `lib_id`, else from the source library); move every `ai_*` field to its symbol's position. `--check` prints per-sheet counts and writes nothing
- [x] Apply to v8. Gate, before vs after: `kicad-cli sch export netlist` identical (apart from library `uri` paths); `v8_debug_sheet.py --check` ends PHASE 11 CHECK PASSED; ERC 0 errors. Log per-sheet counts (fields hidden, pin flags restored, `ai_*` moved, off-sheet text left) in SESSION.md. Re-extract `circuit-context.json` (`extract.py --previous`) and confirm `check_state.py --fresh`
- [x] Check, don't fix: does a kiutils `Board` round trip of a KiCad 9 `.kicad_pcb` (scratch copies of v7 and v8) drop `(hide yes)` or other flags the same way? Record the answer under OQ-11 in PLAN (Phase 13's `place.py` writes boards with kiutils)
- [x] Write the rule in `tools/schematic-modify/CONTEXT.md` and `tools/CONTEXT.md`: every kiutils schematic load goes through the shim, and no write while KiCad has the project open. Point the `.context/HAZARDS.md` kiutils entry at the shim
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 11b: Schematic tooling — layout check and placement rules

- [x] `tools/schematic-modify/layout_check.py` (readability §1.1 method and §3.4; prototype `prototypes/probe.py`). Per sheet, it fails on: (1) a visible field other than Reference/Value on a non-power symbol; (2) any text or symbol outside the paper; (3) text-overlap pairs above a committed per-sheet baseline; (4) identical labels stacked on one point, above the baseline. The baseline only ratchets down: a lower count is reported, and `--update-baseline` records it. It prints the worst spots by sheet grid zone (e.g. "C3"). Record the baseline from the tidied v8 (readability expects about 111 overlap pairs by the prototype's count, 6 stacked labels on power)
- [x] Wire it into the end of `v8_debug_sheet.py --check`, so the whole v8 check chain (Phases 8–11) runs it. The chain passes
- [x] Placement rules in `modify.py` (readability §3.4 rows 2–3). `add_component` places Reference/Value at the library symbol's own field offsets, rotated with the symbol, and writes `(fields_autoplaced yes)`. `_make_local_label`/`_label_angle`: on a vertical stub, prefer a horizontal label justified away from the part. `WIRE_STUB_LEN` default 5.08 mm, with a per-call `stub_len`. Existing parts are not moved. Test on a scratch copy: a vertical two-pin part and a test point, each with labels, add 0 overlaps by `layout_check.py`
- [x] Record in `tools/schematic-modify/CONTEXT.md`: the placement rules, `layout_check.py` as part of every `--check`, and the grid rule for future generator scripts (row pitch from the longest label or value, about 0.75 × 1.27 mm per character + 2.54 mm; 1.27 mm grid snap; inside the frame with a margin from the title block). The already-run v8 phase scripts are not re-run
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 11c: BAT_CONN test point, GUI autoplace, readability look

- [ ] Add a test point on BAT_CONN (J8 pin 2, before F3) and its own GND point, per `hardware/pcb-main-v8/CONTEXT.md` Test points → Ground points and Parts → Footprints. Next free TP numbers. Placed with the 11b rules, in `v8_debug_sheet.py` (idempotent; its `--check` expects both; the v7-position comparison still gives 0 nets differ). `annotate` both parts. `layout_check.py` at or below baseline
- [ ] Update `hardware/pcb-main-v8/CONTEXT.md`: Test points (BAT_CONN added to the list and the "As built" paragraph), and the user's 2026-11-04 W3 decisions: keep R66 (10 mΩ, link h4), which answers the "Question for W3" under Power path; LED currents stay as designed. Re-extract `circuit-context.json`; `--fresh`
- [ ] Write the GUI steps for the user in SESSION.md, with checks inline in each step. Per sheet: Cmd+A, then `O` (Autoplace Fields); look before saving, and Undo on any hand-tuned v7 area that got worse. Then: Tools → Update Symbols from Library for Q20, Q21 and U10 only (clears the 3 `lib_symbol_mismatch` waivers); delete the 0.1 mm stray wire on SW1 pin 1 (power sheet, (222.25, 24.13)); optionally Preferences → Schematic Editor → Editing Options → automatically place fields; save; quit KiCad and confirm no `~*.lck` remains. Export the pre-GUI netlist to scratch first. Stop and report
- [ ] **(user)** Do the GUI pass (about 2 minutes per sheet)
- [ ] Verify the GUI pass: netlist identical to the pre-GUI export (pin → net checked for Q20, Q21, U10); `v8_debug_sheet.py --check` passes; ERC 0 errors with the 3 `lib_symbol_mismatch` gone; `layout_check.py` counts lowered and recorded with `--update-baseline`. Render each sheet to PNG (`kicad-cli sch export svg`, then convert) for the look, and list each sheet's remaining overlap spots by grid zone. Re-extract `circuit-context.json`; commit
- [ ] **W3a (user):** the readability look. The user reads each sheet (PNGs, then KiCad) and decides on the power/TCA re-layout (OQ-10), with the options in readability §3.3: none; hand layout in the GUI; scripted regroup; the battery block on its own sheet. Record the decision in SESSION.md. If any re-layout is chosen, stop: the Orchestrator sends a replan request to the Planner before Phase 11d
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 11d: Second-opinion review — kicad-happy (read-only)

- [ ] Clone kicad-happy at tag v3.0.0 (github.com/aklofas/kicad-happy, MIT; landscape §2 and §5 item 1) into its own scratchpad directory. Run its schematic analyzers on a scratch copy of `hardware/pcb-main-v8/kicad/` at HEAD, with output to the scratchpad. Run any of its Python with `-I` from outside its folder. Don't install it as a Claude Code plugin (that is a config change): if its analyzers can't run standalone, or need a Python we don't have, write the install as a **(user)** step and stop. Nothing it produces is written into the repo
- [ ] Classify each finding against the Phase 11 audit (SESSION.md, Worker #11) and `hardware/pcb-main-v8/CONTEXT.md`: new true issue; known or by design (cite the CONTEXT decision); or false positive. Spot-check its datasheet extraction for TCA9548A, BQ24195 and TPS61088 against `docs/references/*/DATASHEET_REFERENCE.md`
- [ ] Log the findings in SESSION.md as a table: finding, sheet/ref, class, evidence, proposed fix. **Nothing is applied**; each true issue goes to the user at W3 as a proposal. Give a recommendation for OQ-9 with the score (true new issues, false positives)
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 11e: Plain-language schematic tour

- [ ] Write `hardware/pcb-main-v8/REVIEW-GUIDE.md` for the user, who is not an EE. Start with a short primer: symbols, wires vs net labels, power symbols, hierarchical sheets, and how this board's jumpers, links and test points are drawn. Then go sheet by sheet, block by block: where it is (sheet, refs), what it does, why it is there (cite the CONTEXT decision, jumper row or CL-ID), and what an obvious mistake would look like on screen (e.g. a label spelt differently from its partner, an LED or diode backwards, a jumper's default position wrong, a test point without its GND point). End with the review checklist for W3: the open kicad-happy findings (11d) and Worker #11's W3 points that are still open. Ground it in `circuit-context.json` and CONTEXT.md, not memory: check with a script that every ref and net it names exists in the current `circuit-context.json`
- [ ] Add a one-line pointer to it in `hardware/pcb-main-v8/CONTEXT.md`
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 11f: Schematic review (W3) and freeze

- [ ] **W3:** the user reviews the schematic in KiCad against `hardware/pcb-main-v8/REVIEW-GUIDE.md` and the 11d findings. Apply the agreed fixes through the tools; re-run `v8_debug_sheet.py --check` (including `layout_check.py`) and ERC; re-extract `circuit-context.json` (`--fresh`); tag the commit as the schematic freeze
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
[from: v8-debug-board] `routing_audit.py` as a thin consumer of the board model (audit §6.1), or retired: marked superseded in the README in Phase 6; the v7 debug track still cites its spec and outputs.
[from: v8-debug-board] Board-model run on the sensor-rigid and sensor-flex boards (audit says it must run on all three; validation is main-only here).
[from: lab-multi-investigation] Once PR #89 is merged, the Phase 2 power relay (`debugger/RELAY-power.md`) runs as `PWR` cards: the Debugger scaffolds at intake with `python3 tools/lab/new_investigation.py --name power --prefix PWR --title "<title>"` and decides whether board #0004 also belongs to `power` in `lab/BENCH.md`.

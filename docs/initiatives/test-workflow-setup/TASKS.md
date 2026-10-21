# Test Workflow Setup — Tasks

> Track 1 (Phases 1–4) ends at the milestone merge that unblocks log-only debug cards. Track 2 (Phases 5–16) is the scope tooling. Waits W2–W8 are defined in PLAN.md (W1 was removed: the role install is deferred). Until the role is installed, a "debugger session" means an ad-hoc `claude` session opened with "Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session."
> ~~**User, at any time before Phase 9:** buy ground springs that fit the Sensepeek and Rigol probe tips (`test-workflow-audit.md` §4.1).~~ Closed: springs are on hand and fit both probes (W4 S8b).

## Phase 1: Firmware baselines

- [x] Read `test-workflow-audit.md` §2.5 and CL-25 in `v6-v7-changelist.md`. Diff the I²C init in `SensorManager.cpp` between `4da1c67` and HEAD, and list the five debug changes, with line numbers, in SESSION.md
- [x] Revert exactly those five changes and fix the boot-line text. Keep the diag paths and envs. Build every `motion-play-v7*` env
- [x] Commit (the message states the I²C init in one line). Create the annotated tag `v7-clean` with the init line, `STARTUP_I2C_SCAN` value and the envs that build. Do not flash
- [x] In a throwaway worktree on `4da1c67`, build the v6 env. Create the annotated tag `v6-ref` on `4da1c67` with its I²C init stated. If the build fails, record why in PLAN Open Questions and still tag (the tag is the source of truth, not the build cache)
- [x] Push both tags. Remove the worktree
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 2: lab/ containers and templates

- [x] Create the `lab/` tree per PLAN (cards/, log/, evidence/, procedures/, templates/ with `.gitkeep`). Add `lab/inbox/` and `lab/captures/` to `.gitignore`
- [x] Write the `lab/STATE.md` skeleton from `context-strategy.md` §4.1: front matter sentinels, the 9 section headings with cap annotations and one-line field definitions, no rows except true-now Lookups. No content in sections 1–8
- [x] Write `lab/NOTEBOOK.md`: the entry-format header (both formats from §5) and the volume-0 seed entry
- [x] Write `lab/templates/card.md` (§4.7, parseable YAML front matter) and `lab/templates/instruction.md` (§4.8 and its rules)
- [x] Write `lab/templates/log.yaml` (§4.6 + `ai_read` block + `kind: log-only | scope`), with required fields marked
- [x] Templates acceptance: create a dummy card `V7R-999-dummy.md` from the template, commit it as pre-registered, confirm the front matter parses (`python3 -c` yaml load), then delete it in a follow-up commit and note both hashes in SESSION.md
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 3: Checker and pre-commit hook

- [x] Settle the `Result commit` self-reference convention (PLAN Technical Notes). Update `lab/templates/card.md` to match
- [x] Write `tools/lab/check_state.py` with every §4.2 check (STALE is the only hard failure), plus `--root`, `--fresh <file>` and `--load`
- [x] Build fixtures under `tools/lab/tests/fixtures/`, one per condition (STALE, open-card mismatch, CHECKPOINT DUE, cap overrun, stale hash, memory hit), and a test runner asserting each fires exactly once. All pass
- [x] Write `.githooks/pre-commit` and its Python helper (card status → STATE `as_of` rule, recorded-card evidence/result rule, duplicate ID). Run `git config core.hooksPath .githooks`
- [x] Hook acceptance in a scratch clone: recording a dummy card without a STATE edit is rejected; with the edit, it passes. Log both outputs in SESSION.md
- [x] Add a `tools/lab/` section to `tools/CONTEXT.md` (what each script does, and the one-time hooksPath setup)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 4: Touch points, milestone

- [x] **W2:** present each touch point as a diff for approval and apply only the approved ones: PROTOCOL.md (§9 of context-strategy; the Debugger row is marked draft and points to the draft file and the ad-hoc invocation), the PROJECT.md pointer line, the `tools/CONTEXT.md` kiutils rule and source-hash rule (show the existing Phase 3 `tools/lab/` section alongside; don't add another), banners on the §2.4 items except the scope guide, auto-memory deletions and the C90862 stock tip moved to `hardware/CONTEXT.md`, and the user's choice for `project_bq24195_iinlim_fix.md` + its index line (reword/move, or keep as an accepted `[MEMORY]` warning). Record each outcome in SESSION.md
- [x] Budget check: measure the actual L0 (lines and bytes/4), with `docs/research/v7-retry/debugger-role-draft.md` standing in for `debugger.md`, and record it in SESSION.md. Pass: < 500 lines and ≤ ~12k tokens. If over, report which file and stop
- [x] Run `python3 tools/lab/check_state.py` on the real `lab/`. Expect no findings except `[MEMORY]` warnings the user accepted at W2 (sentinel state). Any other finding: report and stop
- [x] **W3:** open the milestone PR "test-workflow-setup: log-only ready". The user merges it with a merge commit. Tell the user the debug track can start as ad-hoc sessions off the draft (first debugger session transcribes `decisioning.md` §2). Re-cut the branch from main
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 5: Instrument facts (desk)

- [x] From Rigol's DHO800/DHO900 Programming Guide, record the exact SCPI syntax for every query listed in PLAN (screenshot, waveform data, setup save/load, per-channel ratio/BW/scale/offset, timebase, trigger, measurements), with source page numbers
- [x] Record the DHO804 Cal output spec, the setup-file extension, the CSV save path on fw 00.01.05, and Sensepeek SQ-500/SQ-10 bandwidth, attenuation and tip capacitance, each with its source. Mark each "desk-verified" or "needs bench"
- [x] Check the ESP32-S3 V_OL datasheet figure behind §2.1's "≈ 30–80 mV". Record whether it's supported (cite the `docs/references/` page) and what the procedure may claim
- [x] Evaluate the third-party DHO800 LAN/MCP project: licence, activity, coverage vs §5 item 1, effort to wrap. Write a short recommendation in PLAN
- [x] kiutils probe (scratch script, read-only): the closest GND-net pad to U5 pins 5/6 on v7 (edge-to-edge, `file@commit`), and the v6 names of the master SDA/SCL test points, BQ24195 pins 5/6 and the GND pad. Record them in PLAN
- [x] Draft the Phase 6 bench script as §4.8 blocks in SESSION.md (LAN connect, `*IDN?`, each query, USB save, LAN pull, third-party smoke test)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 6: Scope on the LAN (bench)

- [x] **W4:** the Orchestrator relays the Phase 5 bench blocks to the user one step at a time and records each REPORT in SESSION.md
- [x] Mark each [verify] item verified or corrected in PLAN "Verified instrument facts". Any item that fails goes to Open Questions, and the dependent tool or procedure work is blocked
- [x] LAN-vs-USB comparison: a scratch script compares the PNG and CSV from the same capture. Record the result (acceptance: LAN capture)
- [x] **W5:** present the build-vs-adopt evidence and get the user's decision. Record it in PLAN (strike through the question, add a Rejected Approaches line)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 7: Capture, ingest, validation, backup

- [x] Write the capture tool (or the wrapper around the adopted one) per PLAN: files named per §4.4, log entry with every required §4.6 field filled from scope queries, operator fields left as TODO
- [x] Write `tools/lab/validate_log.py` (branches on `kind`). Wire it into the pre-commit helper for staged `lab/log/*.yaml`. Add a passing and a failing fixture
- [x] Write `tools/lab/ingest_usb.py` (copy to inbox, timestamp-match, rename into captures)
- [x] Write `tools/lab/backup_captures.sh` (rsync captures/ + inbox/) to the iCloud Drive folder `~/Library/Mobile Documents/com~apple~CloudDocs/motion-play-lab/`, with the path as one config value (user, 2026-10-20: iCloud Drive replaces Google Drive)
- [x] **W6:** one bench capture with the tool. Keep the trace frozen and save a menu memory CSV (DATA SOURCE = MEMORY) and a PNG of the same capture to USB. Compare the tool's CSV against the memory CSV sample for sample and its PNG against the USB PNG, then run the validator on the generated entry (acceptance: capture tool). Update the `tools/CONTEXT.md` tools/lab section
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 8: Procedures and scope-guide retirement

- [x] Write `lab/procedures/dho804-setup-validation.md` (§4.2 V1–V9). Every number and menu path comes from PLAN "Verified instrument facts"; no remaining [verify] marks
- [x] Write `lab/procedures/known-good-reference.md` (§4.3), using the v6/v7 point names from Phase 5, the same-ground-length rule, and the pass table with the V_OL claim limited to what the datasheet check supports
- [x] Add the "scope setup → lab/procedures/" Lookups row (template; STATE.md too if the debug track has filled it, that row only)
- [x] Put a RETIRED banner on `docs/debugging/i2c-oscilloscope-debugging.md` pointing to `lab/procedures/` (body untouched)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 9: v6 dry run, first attempt (bench, as an ad-hoc debugger session)

- [x] Write the dry-run instructions for the user in SESSION.md: open an ad-hoc `claude` session with "Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session."; the session pre-registers the v6 validation card, flashes `v6-ref` to v6, runs setup validation then the known-good reference, captures with the tool, ingests, and records with STATE + notebook
- [x] **W7:** the user runs the dry run. Outcome: V7R-001 recorded void at V5 (`4736a4a`); V1–V4 pass, V5 fails on the scope's own floor, V7–V9 not run. Replanned: PLAN "After V7R-001". The fresh-session L0 test and the image-handoff report move to W8
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 10: Tool fixes after V7R-001 (desk)

> Does not depend on the two user questions in PLAN Open Questions. Source for every item: PLAN Technical Notes "After V7R-001" §1 and §5.

- [x] Write `tools/lab/noise_floor.py` (stdlib only; it must run on the repo's default `python3` 3.7). It takes `--ctl <csv> --dut <csv>` (capture.py CSVs) and `--limit-mV` (default 5). Per channel it prints mean, sd, max − min and excess = √(max(0, sd_dut² − sd_ctl²)), all in mV, with PASS/FAIL against the limit and the control-sd sanity band 2.5–10 mV (flagged, not failed, with a note that the band holds only at the V7R-001 reference settings). It refuses when the sample interval or point count differ, warns when the smallest level step differs, and prints a `validation.V5` YAML snippet. Check it on `lab/evidence/V7R-001/2026-10-20_V7R-001_val_V5_03.csv` (ctl) against `…_val_V5_01.csv` (dut). Expect sd ≈ 4.97 / 4.77 and 5.17 / 4.72 mV and excess ≈ 1.4 / 0 mV. Paste the output into SESSION.md
- [x] `validate_log.py` and `lab/templates/log.yaml`: add the `validation.V5` block (required per-channel maps `ctl_sd_mV`, `dut_sd_mV`, `excess_rms_mV`, `offset_mV`; optional `vpp_panel_mV`). A log with only the legacy `V5_noise_floor_mVpp` gets a WARNING. Accept `not_run: "<reason>"` for any `validation.V<n>` value only when `validation.passed` is false, and raise an ERROR when `passed` is true. Add fixtures: new V5 passes; legacy V5 warns; `not_run` with `passed: false` is valid; `not_run` with `passed: true` errors. Run the validator on `lab/log/2026-10-20_s01.yaml` without editing it, and record the output (expect the legacy warning, with the existing TODOs unchanged)
- [x] `capture.py`: check channel drift against the most recent earlier entry with the same `--arm` (no earlier entry for that arm means no check), and write the new V5 block as TODOs in the validation skeleton. Using `tests/fake_scope.py`, test that two arms at different V/div give no NOTE and that one arm with a changed V/div gives a NOTE
- [x] Run `tools/lab/tests/run_tests.py` and `tools/lab/tests/tool_tests.py`; all pass. Update the `tools/CONTEXT.md` tools/lab section: `noise_floor.py`, `not_run`, the per-arm drift rule, one log per arm
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 11: Procedure fixes and re-run relay (desk)

> **Gate:** both user questions in PLAN Open Questions (V5 rule change, S1 ground on v7) are answered and struck through. If an answer differs from the Planner's recommendation, the Planner updates PLAN "After V7R-001" before this phase starts.

- [x] `lab/procedures/dho804-setup-validation.md`: rewrite V5 per PLAN "After V7R-001" §1: V5a control at the Cal ground, then V5b on the arm's ground point, `noise_floor.py`, the 5 mV rms pass, the sanity band, the record fields, and an example command for each capture (`--arm val_V5ctl`, `--arm val_V5`). In V6, set the v6 master-end row to the soldered wire (§2) and the v7 master-end row per the user's answer. Redefine "unplug the board" per §4 everywhere it appears, and record whether the data cable is in. In "Closing the validation", add `not_run` and one log per arm (§5)
- [x] `lab/procedures/known-good-reference.md`: add a "v6 power and flash path" item to Prerequisites (§4), and say there that the reference runs with no sensor PCB (§3). In "Which transaction to capture" and step 5, the restart becomes unplug and replug of the main-board USB-C, and the RIGHT button is removed (§3). Update the S1 ground in the same-ground table and the Arms table (§2 and the user's answer). Step 7 V_OL cites the channel's V5 offset (§1). Recording uses one log per arm (§5). No pass-table limit changes
- [x] Write `RELAY-v6-dry-run-2.md` for W8, modelled on `RELAY-v6-dry-run.md` (which stays as run). It names the next free card ID (V7R-002 unless the debug track has taken it; the `lab/cards/` filenames are the counter), not a reopened V7R-001. Contents: re-flash `v6-ref` first (§4); V1–V4 once, then V5–V9 at S1 and at S2 on v6, one log per arm; the soldered wire stays on pad C; no sensor PCB; restart by replugging the main-board USB-C; the stop rules; run before the CHECKPOINT DUE date that `check_state.py` reports (2026-11-02 for W7), and stop and report if it fires. Afterwards, the fresh-session L0 test ("what is the bench state?") and the report list: L0 answer, image handoff, final commit, hand-set settings with button paths, pass or fail per V5–V9 row per arm
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 12: v6 re-run, S1 (bench)

- [x] **W8, part 1:** the user ran `RELAY-v6-dry-run-2.md` as an ad-hoc debugger session. Card V7R-002 is pre-registered and open; S1 ran V1–V9 and passed, with deviations (a) V7 from the CSV mean and (b) V8/V9 on an I²C address trigger, both decided on the card. S2, the card close and the L0 test moved to Phase 16. Interim return: `RELAY-v6-dry-run-2-return.md` (72329ef), SESSION.md "W8"
- [x] 🔄 Handoff (the interim return relay and SESSION.md "W8", ca5a1ab)

# --- handoff point ---

## Phase 13: Frame tool (desk)

> Source for this phase and the next two: PLAN "After V7R-002 S1" §1–§8. No pass limit and no card prediction changes anywhere.

- [x] Write `tools/lab/i2c_frame.py` per PLAN "After V7R-002 S1" §6, with the rise-time metric of §4 (0.99 V → 2.31 V, linear interpolation, every rising edge per channel). Args: `<csv>`, `--sda CH1`, `--scl CH2`, `--vdd 3.3`, `--expect <hex byte>`. Idle mode when no channel crosses V_DD/2; frame mode otherwise. Print the numbers, a YAML snippet for the log (`validation.V7_idle_high_V`, or `values` entries with `gate` strings in the S1 log's style), and pass/fail per `known-good-reference.md` pass-table row, citing that file for the limits. Stdlib only, Python 3.7. Reuse the CSV loader in `noise_floor.py` or `lablib.py` if it fits; don't refactor `noise_floor.py` otherwise. Exit 0 all pass, 1 any fail, 2 bad input or no frame found
- [x] Tests in `tools/lab/tests/tool_tests.py`, on synthetic CSVs that the test writes: a 100 kHz `D6`+ACK frame with known edge times, rise times and low levels; a flat idle record; a frame with NACK (9th bit high); a byte that differs from `--expect`; a record with a single channel. Each asserts the printed values within stated tolerances and the exit code. `tools/lab/tests/run_tests.py` passes
- [x] Acceptance on real data: run it on `lab/captures/V7R-002/2026-10-21_V7R-002_S1_01.csv` (`--expect D6`) and on `..._val_V7_01.csv`. Compare with the S1 log `lab/log/2026-10-21_s01.yaml` (the S1 entry's values; `V7_idle_high_V`). Record both outputs and every difference in SESSION.md. Pass: within 3 mV and 3 ns of the hand numbers, and the same byte and ACK. If not, report the difference and both gates, and don't tune the tool to match. If the captures are missing, stop and report (they are gitignored; the iCloud backup holds them). Do not edit the S1 log or the card — *run; not within 3 mV on V_OL (−6.9…−8.8 mV) and CH1 idle high (−5.8 mV), gate differences only, same verdicts; see SESSION Worker #16*
- [x] Add an `i2c_frame.py` row to the `tools/CONTEXT.md` tools/lab table, and the `tests/run_tests.py` row's list
- [x] 🔄 Handoff (Worker #16, 62ee15f)
- [x] Rework after Worker #16 (PLAN "After V7R-002 S1" §6, the gate bullets). V_OL: no change to the tool; the SCL-high gate shrunk by 10 % is the method. Idle high in frame mode: start the window 5 µs after the last edge (its 0.5 V_DD crossing, either channel), keep the ≥ 5 µs minimum after the margin, and change the gate string and the PASS line text to say "from 5 us after the last edge". Update the synthetic tests to match (idle window start, and a record where fewer than 5 µs remain after the margin gives "n/a"). `run_tests.py` passes
- [x] Re-run acceptance per PLAN §6 "Acceptance (revised after Worker #16)" on `S1_01.csv --expect D6`: byte, ACK, period and rise times as before; idle high within 3 mV of 3302.5 / 3292.9 mV; for V_OL, a one-off check script (in the scratchpad, not committed) computes the mean over the tool's printed gates (must match the tool within 0.1 mV) and over the hand gates (must give 72.4 / 70.2 / 75.4 within 0.1 mV). Record the tool output, the check output and every difference in SESSION.md. If any part is not met, report it with both gates; don't tune. Do not edit the S1 log or the card. Update the `tools/CONTEXT.md` `i2c_frame.py` row if its gate wording changed
- [x] 🔄 Handoff (Worker #17, b866747)

# --- handoff point ---

## Phase 14: Procedure revision (desk)

- [x] `lab/procedures/dho804-setup-validation.md`:
  - **Words / §0.4:** the screen rule from PLAN §7 (scope screen, board display, terminal), and the decode band defined as the row labelled B1 / I2C at the left edge of the scope screen.
  - **New decode-setup step before V8**, run in every scope session (PLAN §5): the menu path field by field, then the verified queries as the CHECK (`:BUS1:MODE?`, both sources, `:BUS1:THReshold? SDA` and `? SCL` reading about `1.65`). No SCPI set for Bus status, thresholds or R/W.
  - **V7** (PLAN §3): the panel item is VPP; the "VPP on the panel" check is its own step before the capture step; the value is the `i2c_frame.py` idle mean; limit unchanged.
  - **V8** (PLAN §1, §2): the address trigger (`WHEN ADDR`, `AWIDth 7`, `ADDRess 107`, `DIRection WRITe`, sweep SING), each set and read back; 20 µs/div for V8, then back to 10 µs/div and read back; replug; CHECK on the scope screen's decode band: `Write:d6` then `A:0`. Stop rule: no `d6` after 3 replugs. Remove the START trigger and sweep NORM.
  - **V4:** one line that identical panel digits on CH1 and CH2 were seen in V7R-002 and are not a fail (PLAN §4).
  - **Every step:** a CHECK that must happen before a later action ends its step, and the action becomes the next step (PLAN §7).
- [x] `lab/procedures/known-good-reference.md`:
  - **Prerequisites and "Which transaction to capture"** (PLAN §1, §2): the 0x6B frames at 100 kHz; sensor init at 400 kHz after them, so the bus is not quiet; the boot-ROM UART on SDA; hence the address trigger and SINGLE. Remove "the bus goes quiet" and the "if it shows another address" retry.
  - **Step 2:** correct the record to −80…+80 µs at 16 ns per sample at 10 µs/div, and say the START falls just outside it while the edges, the 0-bits, the ACK and the idle level after the STOP are inside.
  - **Step 3:** the address trigger in place of START. The MAX/MIN 70/30 set is now verified.
  - **Step 5:** CHECK the scope status reads STOP. An empty decode band at 10 µs/div is expected, because the decode comes from the CSV. Stop after 3 replugs with no trigger.
  - **Step 7:** run `i2c_frame.py --expect D6`. Name the gates as in PLAN §6: V_OL over the bit's SCL-high interval shrunk by 10 % at each end (replacing "the flat middle of a master-driven 0-bit"); idle high from 5 µs after the last edge (replacing "Vtop, or the mean of the samples before the START"). Rise time as in PLAN §4, with the panel RTIMe recorded beside it and no pass role. Decode from the CSV bits.
  - **Pass table:** the rise row reads ≤ 300 ns, with the note that the reference frame runs at 100 kHz and why the Fast-mode limit is kept (PLAN §2); ≤ 1000 ns stays only for the secondary reference. The Decode row's source is the CSV. Apply the step split rule from PLAN §7. No limit changes
- [x] `lab/templates/instruction.md`: add the CHECK-placement rule and the screen-naming rule (PLAN §7)
- [x] Read both procedures end to end for steps that contradict each other, and for any remaining "screen", START or "bus goes quiet" wording. List the result in SESSION.md
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 15: S2 relay (desk)

- [ ] Write `RELAY-v6-dry-run-2-s2.md` for the W8 continuation, modelled on `RELAY-v6-dry-run-2.md` (which stays as run). Contents:
  - It continues card **V7R-002** at S2. It is not a new card, and the card's predictions and limits stay as registered.
  - S2 runs on the procedures at the Phase 14 commit(s), and the card notes those commits. They write deviations (a) and (b) in as the method (PLAN §8).
  - Re-flash `v6-ref` first. This is a new scope session, so V1–V4 run again and go in the S2 log. The S2 log is named by its session date (`<date>_sNN.yaml`), and the card notes that the name differs from its Setup line.
  - Then decode setup, then S2: V2, V5–V9 at the BQ end. Pad F bridging warning. No sensor PCB. Restart by replugging the main-board USB-C.
  - Stop rules, including "no `d6` after 3 replugs".
  - Run before the CHECKPOINT DUE date that `check_state.py` reports, and stop and report if it fires.
  - Analysis with `i2c_frame.py`.
  - Then close the card: the recording commit touches STATE with `as_of`; a notebook entry; evidence for both arms, S1's captures included, promoted to `lab/evidence/V7R-002/`. Measured values: S1 cites its log as recorded (hand values), with the `i2c_frame.py` values for S1_01 beside them, labelled as PLAN §6 "The S1 record" says; S2 cites the tool values from its log; any S1-vs-S2 comparison uses the tool values for both. The S1 log is not edited.
  - Then the fresh-session L0 test ("what is the bench state?").
  - The report list: L0 answer, image handoff, final commit, hand-set settings with button paths, and pass or fail per V5–V9 row per arm.
- [ ] Check that every file path in the relay's paste text exists (`ls` each one) and record the list in SESSION.md (PLAN §7)
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 16: v6 re-run S2 and close (bench, then desk)

- [ ] **W8, part 2:** the user runs `RELAY-v6-dry-run-2-s2.md` as an ad-hoc debugger session (S2, close card V7R-002), then a second fresh ad-hoc debugger session asked only "what is the bench state?". The user reports whether the answer was correct and whether the image handoff was workable
- [ ] Verify from git, for V7R-002: the pre-registration commit comes before the raw-data commits; there are per-arm raw commits; the recording commit touches STATE with `as_of` set; the notebook entry exists; the evidence files for both arms are present; the card notes the procedure commits S2 ran on; the card's S1 Measured values cite the S1 log with the tool values beside them (PLAN §6 "The S1 record"); `check_state.py` is clean; `validate_log.py` passes both arm logs (`2026-10-21_s01` and the S2 log). If v6 is out of spec on a validated setup (V1–V8 pass for that arm), stop: the setup gets fixed before close (replan if needed). If V5 fails again, stop and replan; no limit is widened
- [ ] Tick both acceptance tables in PLAN. The Dry run rows cite V7R-002, with V7R-001 noted as the void first attempt. Open the final PR (merge commit)
- [ ] 🔄 Handoff

## Deferred

[from: test-workflow-setup] Install the debugger role: after the user's edit pass, copy `docs/research/v7-retry/debugger-role-draft.md` verbatim to `.claude/agents/debugger.md`, check every path it names exists, re-run the L0 budget check against it, and flip the PROTOCOL.md Debugger row from draft to installed.
[from: test-workflow-setup] Suggestions for the user's draft edit pass: tell sessions to run `git config core.hooksPath .githooks` when `git config core.hooksPath` is empty; decide whether the checkpoint section carries the `decisioning.md` §4.2 criteria table or a pointer. From W8: the draft's §4.8 relay rules could carry the CHECK-placement and screen-naming rules (test-workflow-setup PLAN "After V7R-002 S1" §7).
[from: test-workflow-setup] The ESP32-S3 datasheet (v1.7) is not in `docs/references/`; Phase 5 read it from `~/Downloads`. Add it (with a DATASHEET_REFERENCE.md like the BQ24195 one) so §4.3's V_OL citation points inside the repo.

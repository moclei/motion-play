# Test Workflow Setup — Tasks

> Track 1 (Phases 1–4) ends at the milestone merge that unblocks log-only debug cards. Track 2 (Phases 5–12) is the scope tooling. Waits W2–W8 are defined in PLAN.md (W1 was removed: the role install is deferred). Until the role is installed, a "debugger session" means an ad-hoc `claude` session opened with "Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session."
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
- [ ] Run `tools/lab/tests/run_tests.py` and `tools/lab/tests/tool_tests.py`; all pass. Update the `tools/CONTEXT.md` tools/lab section: `noise_floor.py`, `not_run`, the per-arm drift rule, one log per arm
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 11: Procedure fixes and re-run relay (desk)

> **Gate:** both user questions in PLAN Open Questions (V5 rule change, S1 ground on v7) are answered and struck through. If an answer differs from the Planner's recommendation, the Planner updates PLAN "After V7R-001" before this phase starts.

- [ ] `lab/procedures/dho804-setup-validation.md`: rewrite V5 per PLAN "After V7R-001" §1: V5a control at the Cal ground, then V5b on the arm's ground point, `noise_floor.py`, the 5 mV rms pass, the sanity band, the record fields, and an example command for each capture (`--arm val_V5ctl`, `--arm val_V5`). In V6, set the v6 master-end row to the soldered wire (§2) and the v7 master-end row per the user's answer. Redefine "unplug the board" per §4 everywhere it appears, and record whether the data cable is in. In "Closing the validation", add `not_run` and one log per arm (§5)
- [ ] `lab/procedures/known-good-reference.md`: add a "v6 power and flash path" item to Prerequisites (§4), and say there that the reference runs with no sensor PCB (§3). In "Which transaction to capture" and step 5, the restart becomes unplug and replug of the main-board USB-C, and the RIGHT button is removed (§3). Update the S1 ground in the same-ground table and the Arms table (§2 and the user's answer). Step 7 V_OL cites the channel's V5 offset (§1). Recording uses one log per arm (§5). No pass-table limit changes
- [ ] Write `RELAY-v6-dry-run-2.md` for W8, modelled on `RELAY-v6-dry-run.md` (which stays as run). It names the next free card ID (V7R-002 unless the debug track has taken it; the `lab/cards/` filenames are the counter), not a reopened V7R-001. Contents: re-flash `v6-ref` first (§4); V1–V4 once, then V5–V9 at S1 and at S2 on v6, one log per arm; the soldered wire stays on pad C; no sensor PCB; restart by replugging the main-board USB-C; the stop rules; run before the CHECKPOINT DUE date that `check_state.py` reports (2026-11-02 for W7), and stop and report if it fires. Afterwards, the fresh-session L0 test ("what is the bench state?") and the report list: L0 answer, image handoff, final commit, hand-set settings with button paths, pass or fail per V5–V9 row per arm
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 12: v6 re-run and close (bench, then desk)

- [ ] **W8:** the user runs `RELAY-v6-dry-run-2.md` as an ad-hoc debugger session, then a second fresh ad-hoc debugger session asked only "what is the bench state?". The user reports whether the answer was correct and whether the image handoff was workable
- [ ] Verify from git, for the new card: the pre-registration commit comes before the raw-data commits; there are per-arm raw commits; the recording commit touches STATE with `as_of` set; the notebook entry exists; the evidence files are present; `check_state.py` is clean; `validate_log.py` passes both arm logs. If v6 is out of spec on a validated setup (V1–V8 pass for that arm), stop: the setup gets fixed before close (replan if needed). If V5 fails again, stop and replan; no limit is widened
- [ ] Tick both acceptance tables in PLAN. The Dry run rows cite the new card, with V7R-001 noted as the void first attempt. Open the final PR (merge commit)
- [ ] 🔄 Handoff

## Deferred

[from: test-workflow-setup] Install the debugger role: after the user's edit pass, copy `docs/research/v7-retry/debugger-role-draft.md` verbatim to `.claude/agents/debugger.md`, check every path it names exists, re-run the L0 budget check against it, and flip the PROTOCOL.md Debugger row from draft to installed.
[from: test-workflow-setup] Suggestions for the user's draft edit pass: tell sessions to run `git config core.hooksPath .githooks` when `git config core.hooksPath` is empty; decide whether the checkpoint section carries the `decisioning.md` §4.2 criteria table or a pointer.
[from: test-workflow-setup] The ESP32-S3 datasheet (v1.7) is not in `docs/references/`; Phase 5 read it from `~/Downloads`. Add it (with a DATASHEET_REFERENCE.md like the BQ24195 one) so §4.3's V_OL citation points inside the repo.

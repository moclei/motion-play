# Test Workflow Setup — Tasks

> Track 1 (Phases 1–4) ends at the milestone merge that unblocks log-only debug cards. Track 2 (Phases 5–9) is the scope tooling. Waits W2–W7 are defined in PLAN.md (W1 was removed: the role install is deferred). Until the role is installed, a "debugger session" means an ad-hoc `claude` session opened with "Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session."
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
- [ ] **W5:** present the build-vs-adopt evidence and get the user's decision. Record it in PLAN (strike through the question, add a Rejected Approaches line)
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 7: Capture, ingest, validation, backup

- [ ] Write the capture tool (or the wrapper around the adopted one) per PLAN: files named per §4.4, log entry with every required §4.6 field filled from scope queries, operator fields left as TODO
- [ ] Write `tools/lab/validate_log.py` (branches on `kind`). Wire it into the pre-commit helper for staged `lab/log/*.yaml`. Add a passing and a failing fixture
- [ ] Write `tools/lab/ingest_usb.py` (copy to inbox, timestamp-match, rename into captures)
- [ ] Ask the user for the Google Drive for desktop folder path. Write `tools/lab/backup_captures.sh` (rsync captures/ + inbox/), with the path as one config value
- [ ] **W6:** one bench capture with the tool. Compare it with a USB save of the same screen, and run the validator on the generated entry (acceptance: capture tool). Update the `tools/CONTEXT.md` tools/lab section
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 8: Procedures and scope-guide retirement

- [ ] Write `lab/procedures/dho804-setup-validation.md` (§4.2 V1–V9). Every number and menu path comes from PLAN "Verified instrument facts"; no remaining [verify] marks
- [ ] Write `lab/procedures/known-good-reference.md` (§4.3), using the v6/v7 point names from Phase 5, the same-ground-length rule, and the pass table with the V_OL claim limited to what the datasheet check supports
- [ ] Add the "scope setup → lab/procedures/" Lookups row (template; STATE.md too if the debug track has filled it, that row only)
- [ ] Put a RETIRED banner on `docs/debugging/i2c-oscilloscope-debugging.md` pointing to `lab/procedures/` (body untouched)
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 9: v6 dry run (bench, as an ad-hoc debugger session)

- [ ] Write the dry-run instructions for the user in SESSION.md: open an ad-hoc `claude` session with "Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session."; the session pre-registers the v6 validation card, flashes `v6-ref` to v6, runs setup validation then the known-good reference, captures with the tool, ingests, and records with STATE + notebook
- [ ] **W7:** the user runs the dry run, then a second fresh ad-hoc debugger session (opened the same way) asked only "what is the bench state?". The user reports whether the answer was correct and whether the image handoff was workable
- [ ] Verify from git: pre-registration commit before the raw-data commits, per-arm raw commits, recording commit touching STATE with `as_of` set, notebook entry, evidence files present, `check_state.py` clean. If v6 is out of spec, stop: the setup gets fixed before close (replan if needed)
- [ ] Tick both acceptance tables in PLAN. Open the final PR (merge commit)
- [ ] 🔄 Handoff

## Deferred

[from: test-workflow-setup] Install the debugger role: after the user's edit pass, copy `docs/research/v7-retry/debugger-role-draft.md` verbatim to `.claude/agents/debugger.md`, check every path it names exists, re-run the L0 budget check against it, and flip the PROTOCOL.md Debugger row from draft to installed.
[from: test-workflow-setup] Suggestions for the user's draft edit pass: tell sessions to run `git config core.hooksPath .githooks` when `git config core.hooksPath` is empty; decide whether the checkpoint section carries the `decisioning.md` §4.2 criteria table or a pointer.
[from: test-workflow-setup] The ESP32-S3 datasheet (v1.7) is not in `docs/references/`; Phase 5 read it from `~/Downloads`. Add it (with a DATASHEET_REFERENCE.md like the BQ24195 one) so §4.3's V_OL citation points inside the repo.

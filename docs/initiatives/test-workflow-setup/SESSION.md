# Session Log — Test Workflow Setup

## 2026-10-18 — orchestration run 1

Entry conditions: planning PR #78 merged to main (`0ccf1f2`). Branch `feat/test-workflow-setup` cut from main. Started from `RELAY-orchestrator.md`. PLAN Open Questions are all scheduled for in-phase resolution (Phase 1, Phase 3, Phase 5, W1); none blocks Phase 1. Firmware builds at HEAD (stacked Phase 23–25 debug build).

---

### Worker #1 — Phase 1: Firmware baselines

**Dispatch:**
```
Initiative: Test Workflow Setup
Phase: 1 — Firmware baselines
Initiative path: docs/initiatives/test-workflow-setup/
Additional reading: docs/research/v7-retry/test-workflow-audit.md §2.5; CL-25 in v6-v7-changelist.md (as the task names). Phase notes: build-only — do NOT flash v7-clean or v6-ref onto any board. Tags are created only after the build passes (v6-ref is tagged regardless, per task 4). Work on branch feat/test-workflow-setup.

Tasks assigned (from TASKS.md Phase 1):
- [~] Read `test-workflow-audit.md` §2.5 and CL-25 in `v6-v7-changelist.md`. Diff the I²C init in `SensorManager.cpp` between `4da1c67` and HEAD, and list the five debug changes, with line numbers, in SESSION.md
- [ ] Revert exactly those five changes and fix the boot-line text. Keep the diag paths and envs. Build every `motion-play-v7*` env
- [ ] Commit (the message states the I²C init in one line). Create the annotated tag `v7-clean` with the init line, `STARTUP_I2C_SCAN` value and the envs that build. Do not flash
- [ ] In a throwaway worktree on `4da1c67`, build the v6 env. Create the annotated tag `v6-ref` on `4da1c67` with its I²C init stated. If the build fails, record why in PLAN Open Questions and still tag (the tag is the source of truth, not the build cache)
- [ ] Push both tags. Remove the worktree
- [ ] 🔄 Handoff
```

#### Notes

**Task 1: I²C-init diff, `4da1c67` → HEAD (`843e7c2`), `firmware/src/components/sensor/SensorManager.cpp`, `SensorManager::init()`.**

`4da1c67` L636–638: `Wire.begin(43, 44);` / `Wire.setClock(400000);` / `Serial.println("I2C clock set to 400 kHz");`. Nothing else touches drive, filters or pulls.

The five debug changes at HEAD (line numbers at `843e7c2`):

| # | Change | Code lines | Comment lines | Phase |
|---|---|---|---|---|
| 1 | `Wire.setClock(100000)` (was 400000) | L642 | L640–641 | 22–23 |
| 2 | `gpio_set_drive_capability(GPIO_NUM_43/44, GPIO_DRIVE_CAP_3)` | L648–649 | L643–647 | 23 |
| 3 | `i2c_filter_enable(I2C_NUM_0, 7)` | L658 | L650–657 | 24 Exp 1 |
| 4 | IO_MUX `FUN_FILTER_EN` (`#define` fallback + `REG_SET_BIT(GPIO_PIN_MUX_REG[43/44], …)`) | L668–672 | L660–667 | 25 Exp 2 |
| 5 | `gpio_pullup_dis` / `gpio_pulldown_dis` on 43/44 | L680–683 | L674–679 | 25 Exp 3 |

Supporting lines that exist only for these five: the includes `<driver/gpio.h>`, `<driver/i2c.h>`, `<soc/io_mux_reg.h>` (L3–5; nothing else in the file uses them), and the stale boot line at L685–686 (`"I2C: 100 kHz, drive CAP_3, filter(7), pad-filter, internal pulls dis [Phase 24 null + Phase 25 bundle]"`).

The rest of the `SensorManager.cpp` diff (`selectChannelVerify`, per-channel scan on a 0x60 NACK, diag paths) is outside the I²C init and is kept. The other `Wire.begin(43, 44)` callers (`main.cpp` `configureBQ24195()`, and `InterruptManager` via `MuxController::begin(..., 400000)`) are the same as in the v6 era and are not part of the five. The restored clock is 400 kHz, which matches `4da1c67`.

**Tasks 2–3: `v7-clean`.** Commit `90053af` replaces L639–686 with the `4da1c67` init (`Wire.begin(43, 44)` + `Wire.setClock(400000)`), a two-line comment and the boot line `"I2C: 400 kHz, default drive, no filters, default pulls [v7-clean]"`. It also drops the three includes listed above, since they only served the five changes. Judgement call: if a reviewer reads "exactly the five" strictly, the includes are inert either way. After this, `git diff 4da1c67 -- SensorManager.cpp` shows no I²C-init difference except the boot-line text and the comment. Every env built: `motion-play-v7`, `-diag`, `-busrec`, `-relbus`. `STARTUP_I2C_SCAN=true` is unchanged and inherited by all three derived envs. Annotated tag `v7-clean` points at `90053af`. Not flashed.

**Task 4: `v6-ref`.** In a detached worktree on `4da1c67`, the only env at that commit is `lilygo-t-display-s3` (`STARTUP_I2C_SCAN=false`). It built clean with today's PlatformIO and library cache and needed no fix. The PLAN Open Question is struck through. Annotated tag `v6-ref` points at `4da1c67`. Not flashed.

**Task 5.** Both tags are pushed to origin (`v7-clean` tag object `09dc82e`, `v6-ref` tag object `ce7e6e7`). The worktree is removed and pruned. `--force` was needed only because the untracked `.pio/` build output was there.

**For the next session.** The six detached Cursor worktrees under `~/.cursor/worktrees/motion-play/` are older and were not touched. Phase 2 has no dependency on firmware. Remember that PR merges must be merge commits so that `90053af` (the `v7-clean` target) stays reachable from main.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 1 | Phase 1: Firmware baselines | DONE | No — clean completion | c24f956 | 5 tasks; `v7-clean` → `90053af`, `v6-ref` → `4da1c67`, both pushed |

#### Verification
- Tags re-derived: `v7-clean^{}` = `90053af`, `v6-ref^{}` = `4da1c67`; both on origin (`git ls-remote`). Tag messages state I²C init, `STARTUP_I2C_SCAN` and envs. Throwaway worktree gone.
- `git diff 843e7c2 90053af`: only `SensorManager.cpp` firmware change; I²C init now byte-identical to `4da1c67` L636–637 apart from comment/boot-line text. `platformio.ini` untouched (`STARTUP_I2C_SCAN=true` at L93 for v7, `false` at L39 for v6 env), envs kept.
- Include removal (three headers used only by the five changes): accepted. Builds pass, and the I²C init behaviour is unchanged by it. Not a scope deviation.
- Builds were not re-run by the Orchestrator; build-pass rests on the Worker's report.
- PLAN.md: no date-stamped headings; Open Question struck through.
- Carry forward: the branch is not pushed yet (only tags). `90053af` is reachable on origin through the `v7-clean` tag. Push the branch when the milestone PR opens. Merge with a merge commit.

---

### Worker #2 — Phase 2: lab/ containers and templates

**Dispatch:**
```
Initiative: Test Workflow Setup
Phase: 2 — lab/ containers and templates
Initiative path: docs/initiatives/test-workflow-setup/
Additional reading: the source sections the tasks name — docs/research/v7-retry/context-strategy.md §4.1, §5, §6 (incl. §6.4); docs/research/v7-retry/test-workflow-audit.md §4.6, §4.7, §4.8. Phase notes: STATE.md is a skeleton only — no content in sections 1–8 (BRIEF scope: STATE content is out). Work on branch feat/test-workflow-setup.

Tasks assigned (from TASKS.md Phase 2):
- [~] Create the `lab/` tree per PLAN (cards/, log/, evidence/, procedures/, templates/ with `.gitkeep`). Add `lab/inbox/` and `lab/captures/` to `.gitignore`
- [ ] Write the `lab/STATE.md` skeleton from `context-strategy.md` §4.1: front matter sentinels, the 9 section headings with cap annotations and one-line field definitions, no rows except true-now Lookups. No content in sections 1–8
- [ ] Write `lab/NOTEBOOK.md`: the entry-format header (both formats from §5) and the volume-0 seed entry
- [ ] Write `lab/templates/card.md` (§4.7, parseable YAML front matter) and `lab/templates/instruction.md` (§4.8 and its rules)
- [ ] Write `lab/templates/log.yaml` (§4.6 + `ai_read` block + `kind: log-only | scope`), with required fields marked
- [ ] Templates acceptance: create a dummy card `V7R-999-dummy.md` from the template, commit it as pre-registered, confirm the front matter parses (`python3 -c` yaml load), then delete it in a follow-up commit and note both hashes in SESSION.md
- [ ] 🔄 Handoff
```

#### Notes

**Task 1 (`241c0e3`).** `lab/{cards,log,evidence,procedures,templates}/.gitkeep`. `.gitignore` gains `lab/inbox/` and `lab/captures/` (confirmed with `git check-ignore`). The two ignored dirs are not created; they appear on first ingest.

**Task 2 (`45860a7`).** `lab/STATE.md`: front matter `as_of: V7R-000`, `updated: 2026-10-19`, `last_checkpoint: V7R-000`, `open_cards: []` (parses with `yaml.safe_load`). The 9 headings keep the §4.1 cap annotations in the heading line, so the Phase 3 cap check can parse `(≤ N lines|rows)` from it. Sections 1–8 hold only the one-line field definition, plus the table header row where the section is a table (no data rows). Section 9 has three rows: changelist, legacy phase grep, decisioning.md §2 (until transcribed). The §4.1 mock-up's changelist cell said "§5; §3 by CL-ID"; the real file has §3 = changes table, §5 = observations, and the row says that.
- Judgement: section 6 (Baselines) is left empty even though `v7-clean`/`v6-ref` exist, per the "no content in sections 1–8" rule. The first debugger session fills it.
- Note for Phase 3: the cap check must decide whether the definition line and table header rows count toward a section's cap.

**Task 3 (`fcf1865`).** `lab/NOTEBOOK.md`: header (append-only rule, the "no result written twice" split), both §5 formats with placeholders, then the seed entry `2026-10-19 · s00`: volume 0 = `docs/debugging/v7-i2c-investigation.md` frozen; `L-PhNN`, `L-Ph24a` (Arduino-as-master), `L-Ph24b` (Exp 1 glitch filter).

**Task 4 (`5d6ac6d`).** `lab/templates/card.md` is the §4.7 block verbatim, with two changes: `firmware_commit` is quoted (an all-digit hash parses as an int), and the §4.7 rules are appended as an HTML comment at the end. `lab/templates/instruction.md` has the §4.8 block as a placeholder skeleton, the §4.8 example, and the three rules.

**Task 5 (`2344740`).** `lab/templates/log.yaml`: the §4.6 schema plus `kind: log-only | scope` and a per-measurement `ai_read` list (one entry per PNG: `capture`, `settings_seen`, `values_seen`, `mismatch`). Markers: `[REQ]` = both kinds (`session_id`, `kind`, `dut.*`, `measurements[].test_id/feature/raw_observation`); `[REQ scope]` = the rest of the §4.6 required list. `ai_read` is unmarked because it is written at ingest, after the capture; the Phase 7 validator decides whether to warn when it is missing. Two fixes so the §4.6 example parses: `probe: "SQ-500 #1"` (an unquoted ` #` starts a YAML comment and silently truncates the flow map) and `value: "0x6B"` (YAML 1.1 reads it as int 107). The filename follows PLAN (`YYYY-MM-DD_sNN.yaml`), not the §4.6 example's `_session-01`.

**Task 6 (templates acceptance).** `lab/cards/V7R-999-dummy.md` created from the template (test_id, title, created, H1 changed), committed as `status: pre-registered` in **`9bc9d0c`**. Front matter parsed from the committed blob with `yaml.safe_load` (lines between the first two `---`): `test_id: V7R-999`, `status: pre-registered`, all baseline keys present. Deleted in **`91b482f`**. No hook exists yet (Phase 3), so nothing guarded these commits.

**For Phase 3.**
- `prereg_commit:` in the card template ("filled by the commit") has the same self-reference problem as `Result commit`. Settle both with one convention.
- A front-matter parser must split on the first two `---` *lines*. A naive `split('---')` works on these files only because `--- RUN ---` comes after the front matter.
- `lab/cards/.gitkeep` sits beside the cards. The counter and the duplicate-ID check should match `V7R-NNN-*.md` only.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 2 | Phase 2: lab/ containers and templates | DONE | No — clean completion | d76f0d3 | 6 tasks; dummy card 9bc9d0c/91b482f |

#### Verification
- `lab/` tree matches PLAN; `lab/inbox/` and `lab/captures/` in `.gitignore` (L81–82).
- `lab/STATE.md` 52 lines, 9 sections; sections 1–8 carry only table header rows (no data rows); front matter sentinels `V7R-000`, `open_cards: []`; Lookups has the three true-now rows.
- Re-parsed with `yaml.safe_load`: card template front matter and `log.yaml` both load (`kind` present).
- `9bc9d0c` adds only `lab/cards/V7R-999-dummy.md`; `91b482f` removes it.
- PLAN.md untouched this phase; no date-stamped headings.
- Carry forward to Phase 3: the Worker #2 Notes' four carry-forwards (prereg_commit self-reference, front-matter split, `V7R-NNN-*.md`-only glob, cap counting rule).

---

### Worker #3 — Phase 3: Checker and pre-commit hook

**Dispatch:**
```
Initiative: Test Workflow Setup
Phase: 3 — Checker and pre-commit hook
Initiative path: docs/initiatives/test-workflow-setup/
Additional reading: SESSION.md "Worker #2" Notes block (carry-forwards for this phase: prereg_commit has the same self-reference problem as Result commit — settle both with one convention; front-matter split; V7R-NNN-*.md-only glob since cards/ holds .gitkeep; cap-count rule). docs/research/v7-retry/context-strategy.md §4.2, §8.2 as the tasks name. Phase notes: hook acceptance runs in a scratch clone (under your scratchpad), never by recording a card in the real lab/. Work on branch feat/test-workflow-setup.

Tasks assigned (from TASKS.md Phase 3):
- [~] Settle the `Result commit` self-reference convention (PLAN Technical Notes). Update `lab/templates/card.md` to match
- [ ] Write `tools/lab/check_state.py` with every §4.2 check (STALE is the only hard failure), plus `--root`, `--fresh <file>` and `--load`
- [ ] Build fixtures under `tools/lab/tests/fixtures/`, one per condition (STALE, open-card mismatch, CHECKPOINT DUE, cap overrun, stale hash, memory hit), and a test runner asserting each fires exactly once. All pass
- [ ] Write `.githooks/pre-commit` and its Python helper (card status → STATE `as_of` rule, recorded-card evidence/result rule, duplicate ID). Run `git config core.hooksPath .githooks`
- [ ] Hook acceptance in a scratch clone: recording a dummy card without a STATE edit is rejected; with the edit, it passes. Log both outputs in SESSION.md
- [ ] Add a `tools/lab/` section to `tools/CONTEXT.md` (what each script does, and the one-time hooksPath setup)
- [ ] 🔄 Handoff
```

#### Notes

**Task 5: hook acceptance (scratch clone, real `lab/` untouched).** The clone of `feat/test-workflow-setup` @ `4882bd7` is under the scratchpad, with `core.hooksPath .githooks`. `V7R-001-dummy.md` was made from the template and pre-registered (`58739ee`, STATE `open_cards: [V7R-001]`). Then status was set to `recorded`, `lab/evidence/V7R-001/A1_01.csv` was cited in the Conclusion and staged, and `Result commit: self` was kept.

Attempt 1, card + evidence staged, STATE not edited:
```
lab pre-commit: REJECTED
  - lab/cards/V7R-001-dummy.md (recorded) moves to recorded|abandoned, but lab/STATE.md is not staged. Update STATE.md (as_of: V7R-001, map cells, open_cards) in the same commit.
  (rules: docs/research/v7-retry/context-strategy.md §4.2; card template: lab/templates/card.md)
exit=1
```
Attempt 2, with STATE `as_of: V7R-001`, `open_cards: []` staged:
```
[feat/test-workflow-setup a38c80d] record V7R-001 + STATE as_of
 3 files changed, 5 insertions(+), 3 deletions(-)
 create mode 100644 lab/evidence/V7R-001/A1_01.csv
exit=0
```
Afterwards, `check_state.py --load` on the clone gave `RESULT: OK (0 warnings)` and resolved `prereg_commit self = 58739ee; Result commit self = a38c80d`, which are the right commits. Extra negative checks, all rejected (exit 1): a duplicate `V7R-001-other.md`; a recorded card with `Result commit: <hash>` and no evidence citation (two errors); a card moved to `abandoned` with STATE unchanged. A commit that stages nothing under `lab/` skips the hook (exit 0).

**Task 1 (`bf3e294`).** Convention: `prereg_commit` and `Result commit` are both written as the literal `self`, meaning "the commit that made this transition" (the commit that adds the file, and the commit that sets `status: recorded`). A real hash is also accepted. The resolution rule is the oldest `--diff-filter=A` commit for prereg and the latest `-G'^status: recorded'` commit for result. It is anchored at line start because the template's rules comment contains the literal text "status: recorded". The template and the PLAN Technical Note are updated, and the Open Question is struck through.

**Task 2 (`51205d2`).** `tools/lab/check_state.py` and `tools/lab/lablib.py` (shared parser). Findings print as `[TAG] msg`. The tags are STALE (exit 1), OPEN-CARDS, LOST-RESULT, CHECKPOINT-DUE, CAP, STALE-HASH and MEMORY, plus housekeeping tags CARD and AS-OF. Judgement calls:
- **Cap counting rule:** a section's count excludes the field-definition line, the table header and separator rows, and blank lines. `rows` caps count table data rows. The whole file warns past 150 lines.
- **CHECKPOINT DUE by gap:** "gap" is measured from the newest `## YYYY-MM-DD` notebook entry. It applies only once `as_of > V7R-000`, so the sentinel state doesn't nag.
- **LOST-RESULT:** this check uses the newest commit touching the card *or* `lab/evidence/<ID>/` (falling back to mtime if nothing is committed).
- **Path resolution:** Lookups paths and `_provenance.source` resolve against `--root`'s parent (the repo root for the real lab). Lookups files without provenance count as hand-written and are skipped.
- **Memory:** the default memory dir is derived from the repo path. The regex is case-insensitive.

**Task 3 (`5ad41a4`).** There are 9 fixtures: clean, stale, open_cards, lost_result, checkpoint_due, checkpoint_gap, cap, stale_hash, memory. The runner asserts the expected tag exactly once and *no other tag*, plus four `--fresh` exit-code cases (JSON stale, MD fresh, PNG+sidecar fresh, hand-written = none) and mini-parser parity with PyYAML on the card template. Result: 14/14 pass. The fixtures were generated from the real `lab/STATE.md` skeleton. If that skeleton changes, the cap fixture's section-1 lines still apply.

**Task 4 (`4882bd7`).** `.githooks/pre-commit` (POSIX sh) runs only when something under `lab/` is staged, then execs `tools/lab/precommit.py`, which reads the index, not the working tree. Rule 2 also *warns* (it does not reject) when the cited `lab/evidence/<ID>/` has no files in the index. `git config core.hooksPath .githooks` is set in the real repo. `.git/hooks` held only samples, so nothing was displaced.

**Task 6 (`065dcc2`).** `tools/CONTEXT.md` has a new "Lab Tools → lab/" section: the script table, the one-time hooksPath setup and the `self` convention. The Dependencies line now reads "All KiCad Python tools…", since the lab tools don't use kiutils.

**For Phase 4.**
- **Memory check on the real lab.** `check_state.py` currently returns `RESULT: OK (4 warnings)`, all of them MEMORY. Deleting the two planned memory files doesn't clear this: `project_bq24195_iinlim_fix.md` ("v6 + v7 main PCB need firmware…") and its MEMORY.md index line also match `v7`. The "expect a clean output" task will still see those two warnings unless the user rewords or moves that memory, or accepts them as known.
- **W2 and tools/CONTEXT.md.** W2 lists "a `tools/lab/` entry" for `tools/CONTEXT.md`. That entry has already landed here (task 6). W2 should show it to the user alongside the kiutils and source-hash rule diffs rather than add a second one.
- **Not enforced.** §4.3's "a new card can't be pre-registered while a checkpoint is due" is enforced by neither the hook nor the checker. The checker's CHECKPOINT-DUE message states the rule. Add a hook rule later if wanted.
- **Debugger role setup.** The debugger role should tell the session to run `git config core.hooksPath .githooks` if `git config core.hooksPath` is empty.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 3 | Phase 3: Checker and pre-commit hook | DONE | No — clean completion | 7925e52 | 6 tasks; 9 fixtures; hook acceptance in scratch clone |

#### Verification
- Re-ran `tools/lab/tests/run_tests.py`: 0 failures. `core.hooksPath` = `.githooks` in the real repo.
- Re-ran `check_state.py` on the real `lab/`: exit 0, `OK (4 warnings)`, all `[MEMORY]` (MEMORY.md, `project_bq24195_iinlim_fix.md`, `project_pcb_revision_apr2026.md`, `project_v7_i2c_bq_debug.md`). Phase 4 task "expect a clean output" depends on the W2 memory decision; even after the two planned deletions, the IINLIM memory and its index line still match.
- TASKS.md diff: only Phase 3 lines changed (the Worker's stray Handoff ticks in Phases 4–9 were reverted before commit; confirmed).
- PLAN.md: `Result commit` Open Question struck through; no date-stamped headings.
- Carry forward to Phase 4 (from Worker #3 Notes): the `tools/lab/` entry in `tools/CONTEXT.md` already exists, so W2 shows it rather than adding it again. The debugger role should tell sessions to set `core.hooksPath` if it is unset. The §4.3 "no pre-registration while a checkpoint is due" rule is stated, not enforced.

---

**W1 — loop paused before Phase 4.** Awaiting the user: is `docs/research/v7-retry/debugger-role-draft.md` final, and does its checkpoint section carry the `decisioning.md` §4.2 criteria table or a pointer?

**W1 outcome (user, 2026-10-19):** the debugger role draft is not final; the user wants more review time and does not want it to block. Decisions:
1. Installing the debugger role (`.claude/agents/debugger.md`) is deferred **out of this initiative**.
2. Until it is installed, debugger work runs as ad-hoc `claude` sessions that read `docs/research/v7-retry/debugger-role-draft.md` and act as that role.
3. The Phase 4 L0 budget check measures the current draft as a stand-in for `debugger.md`.
4. PROTOCOL.md touch points are applied at W2, with the Debugger row marked draft and pointing to the draft and its ad-hoc invocation.

`[ORCH] Spawning Planner — debugger role install deferred out of initiative; BRIEF goal, Phase 4 and Phase 9 need re-scoping`

`[ORCH] Planner → REPLANNED: ready to continue` — commit `4277e74`. Verified: no `claude --agent debugger` wording left in BRIEF/PLAN/TASKS; Phase 4 W1 task removed; budget check uses the draft; install + edit-pass suggestions in Deferred; PLAN has no date-stamped headings.

---

### Worker #4 — Phase 4: Touch points, milestone (W2 preparation)

**Dispatch:**
```
Initiative: Test Workflow Setup
Phase: 4 — Touch points, milestone
Initiative path: docs/initiatives/test-workflow-setup/
Additional reading: PLAN "Touch points (Phase 4)"; docs/research/v7-retry/context-strategy.md §2.4, §8.2, §8.3, §9 as the items name. Phase notes: W2 is a user-approval gate and Workers do not talk to the user. This dispatch is W2 preparation only: draft every touch-point edit as a proposed unified diff (or exact new text) in your SESSION.md Notes block, one numbered item each, with the target file. Do NOT apply any of them. The memory files live outside the repo (~/.claude/projects/-Users-marcocleirigh-Workspace-motion-play/memory/); for those, write the proposed deletions and edits as text and do not touch the files. For item (IINLIM memory), draft both options (reword/move to firmware/CONTEXT.md vs keep as accepted warning). Commit SESSION.md, leave the W2 task [~], and return PARTIAL: "W2 diffs ready". The Orchestrator presents them to the user and re-dispatches to apply the approved ones and finish the phase.

Tasks assigned (from TASKS.md Phase 4):
- [~] **W2:** present each touch point as a diff for approval and apply only the approved ones: PROTOCOL.md (§9 of context-strategy; the Debugger row is marked draft and points to the draft file and the ad-hoc invocation), the PROJECT.md pointer line, the `tools/CONTEXT.md` kiutils rule and source-hash rule (show the existing Phase 3 `tools/lab/` section alongside; don't add another), banners on the §2.4 items except the scope guide, auto-memory deletions and the C90862 stock tip moved to `hardware/CONTEXT.md`, and the user's choice for `project_bq24195_iinlim_fix.md` + its index line (reword/move, or keep as an accepted `[MEMORY]` warning). Record each outcome in SESSION.md
- [ ] Budget check … (not in this dispatch)
- [ ] Run `python3 tools/lab/check_state.py` … (not in this dispatch)
- [ ] **W3:** … (not in this dispatch)
- [ ] 🔄 Handoff
```

#### Notes

**W2 preparation only. Nothing below has been applied.** Every repo file named here is unchanged, and the memory directory was not touched. Each item is approved or declined on its own. Sub-items marked (a)/(b) can be split. Line numbers are at `f567168`.

Baseline: `python3 tools/lab/check_state.py` on the real `lab/` gives `RESULT: OK (4 warnings)`, all `[MEMORY]`: MEMORY.md L2,5,6; `project_bq24195_iinlim_fix.md` L2,3,7,11; `project_pcb_revision_apr2026.md`; `project_v7_i2c_bq_debug.md`. The grep is case-insensitive `v7|V7R-|BQ.*NACK`.

---

**Item 1: `.context/PROTOCOL.md` (context-strategy §9). Four hunks.**

(1a) Agent Roles: add a Debugger row marked draft, plus a draft/invocation note.
```diff
@@ -17,9 +17,12 @@
 | Bugfix       | —                | Diagnoses user-found issues; proposes fixes, applies only on approval |
 | Gardener     | GARDEN.md, HAZARDS.md | Clears accumulated cross-cutting refinements via orchestrated sub-agents |
+| Debugger *(draft)* | `lab/` (STATE, NOTEBOOK, cards, log) | Runs pre-registered bench experiments with the user and keeps state current |
 
 Each role's full definition lives in its own file under `.claude/agents/`; this document holds only the sections shared across roles. 
 
 **Invocation:** The user runs Planner, Orchestrator, Organizer, Bugfix, and Gardener as their own top-level sessions with `claude --agent <role>` — the active agent is fixed for a session's lifetime. The Worker is spawned by the Orchestrator via the Task tool (`subagent_type: worker`), never by the user or another role.
+
+**Debugger (draft):** not installed yet. Its definition is the user's draft at `docs/research/v7-retry/debugger-role-draft.md`, not a file under `.claude/agents/`. Until it is installed, the user runs it as an ad-hoc `claude` session opened with "Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session."
 
 ---
```

(1b) Non-Initiative Documents: add a `lab/` entry after HAZARDS.md.
```diff
@@ -146,6 +149,10 @@
 Rules: one trap per entry, a line or two, no history. Route here when the value is *knowing before you start*; route a scoped fix to GARDEN, a durable "always do X" rule to a CONTEXT.md, and a decision or feature to MASTER. If an item is both a warning and a fix, HAZARDS holds the warning and links the GARDEN item that owns the fix.
 
+**lab/:** Bench-debug state, owned by the Debugger, at the repo root. `lab/STATE.md` is the single live handoff document and is loaded at the start of every debugger session. It must be updated in the same commit that records or abandons a card: the pre-commit hook rejects the commit otherwise, and `tools/lab/check_state.py` reports a stale `as_of` at session start. `lab/NOTEBOOK.md` is append-only and is grepped by test ID or date, never loaded whole. Cards (`lab/cards/V7R-NNN-<slug>.md`), session logs (`lab/log/`) and evidence (`lab/evidence/`) are committed. `lab/captures/` and `lab/inbox/` are gitignored. Templates live in `lab/templates/`. `lab/` is not an initiative folder, so the "no orphan documents" rule does not apply to it.
+
 ---
 
 ## Session Management
```

(1c) Relays table: add a Debugger → Planner row.
```diff
@@ -168,6 +175,7 @@
 | Research / ideation session | `role:planner` | `RELAY-planner.md` | Enough explored to start an initiative |
 | Planner session | `role:orchestrator` | `RELAY-orchestrator.md` | Initiative docs complete, ready to build |
 | Orchestrator session | Bugfix / playtesting session | `RELAY-bugfix-<date>.md` | Build complete, testing needed |
+| Debugger session | `role:planner` | `RELAY-planner.md` (in the new initiative's folder) | A fix, a design change or a tool is needed |
```

(1d) Escalation Paths: add a Debugger entry after the Worker-blocker entry.
```diff
@@ -217,6 +225,11 @@
 → Document in `## Rejected Approaches` in PLAN.md → add to `## Open Questions`
 → Return `BLOCKED` → Orchestrator emits evaluation line, escalates to Planner
 
+**Debugger finds that build work is needed (a fix, a tool, a design change)**
+→ Do not implement it → propose a Planner relay
+→ Exception: a firmware change that *is* the experiment (a card's declared delta) is allowed with the user's approval and is reverted on a null result
+→ Anything that outlives the card goes to the Planner
+
 **Orchestrator sees repeated failure or drift**
 → Stop dispatching → send replan request to Planner with specifics
```
Not proposed: the Initiatives principle at L30 ("the only agent roles that directly interact with initiatives…"). The Debugger only suggests initiatives through a relay, which that principle already allows. When the Deferred install happens, (1a) becomes: drop "*(draft)*", delete the Debugger (draft) paragraph, and add Debugger to the `claude --agent` list.

---

**Item 2: `.context/PROJECT.md`, the pointer line (context-strategy §2.5 item 3).**
```diff
@@ -19,6 +19,7 @@
 ## Current Project Status
 
 **Hardware:** ✅ Custom PCBs operational with dual-MUX architecture (TCA→PCA→Sensors). AI-optimized `circuit-context.json` available for all three PCBs (main, sensor-rigid, sensor-flex).
+**v7 main PCB I²C fault:** open, see lab/STATE.md.
 **Firmware:** ✅ Full data collection pipeline (1000 Hz, PSRAM buffering, MQTT transmission)
```
The text is verbatim from PLAN. §2.5 rule: the line only ever says `open` or `closed`. Optional for the user: backtick the path (`` `lab/STATE.md` ``) to match the file's other path styling. The `*Last Updated*` footer is not touched.

---

**Item 3: `tools/CONTEXT.md`. Two hunks, shown with the existing Phase 3 section.**

(3a) Replace the Critical Rule (L5) with the §8.3 proposed text, verbatim.
```diff
@@ -3,6 +3,6 @@
 ## Critical Rule
 
-**DO NOT read or edit `.kicad_sch` or `.kicad_pcb` files directly.** These files are large, verbose S-expression formats that waste context window budget and produce unreliable edits. Instead, use the tools described below — they extract compact JSON context files and perform programmatic CRUD through kiutils.
+**Never read `.kicad_sch` or `.kicad_pcb` text into context, and never edit them directly.** Use the tools below. Exception: targeted read-only kiutils or `kicad-cli` probes are allowed when no tool output answers the question (e.g. zones, stackup). Run them from a scratch script, print only the numbers you need, and cite the probe and file commit.
 
 ## KiCad Schematic Tools
```
Option for the user: also keep the old rationale as a second sentence ("These files are large, verbose S-expression formats that waste context window budget and produce unreliable edits."). The §8.3 sunset rule (once board-model phase 1 lands, probes are only for its gaps) is left out of the line, as §8.3's own proposed text leaves it out.

(3b) Add the §8.2 source-hash rule as a standing section after the Critical Rule.
```diff
@@ -6,4 +6,15 @@
 **Never read `.kicad_sch` or `.kicad_pcb` text into context, and never edit them directly.** …
 
+## Source-Hash Rule
+
+**Every generated context file carries provenance, and every reader checks it.**
+
+- **JSON:** a top-level `_provenance` object: `source`, `source_sha256`, `generator`, `generator_commit`, `generated`.
+- **Markdown:** the same fields as a front-matter block.
+- **Images:** a sidecar `<name>.meta.json`, or the provenance block of the narrative that embeds them.
+- **Check:** `python3 tools/lab/check_state.py --fresh <file>` recomputes the source hash (exit 0 fresh, 1 stale, 2 no provenance). Run it before citing a generated file in a card or a design decision.
+- **Scope:** all generated context, including the existing `circuit-context.json` outputs. Those have no `_provenance` yet (the retrofit belongs to the board-model initiative), so `--fresh` reports them as having none (exit 2). Until the retrofit, judge their freshness from git.
+
 ## KiCad Schematic Tools
```
Checked: `--fresh hardware/pcb-main/kicad/circuit-context.json` gives `NO PROVENANCE`, exit 2, which matches the Scope bullet.

(3c) For reference only, no change: the existing Phase 3 section, `## Lab Tools` → `### lab/` (L83–98). It has the script table (`check_state.py`, `precommit.py`, `lablib.py`, `tests/run_tests.py`), the one-time setup `git config core.hooksPath .githooks`, and the `self` convention. The Dependencies line (L102) already says "All KiCad Python tools…" (Phase 3). No second `tools/lab/` entry is proposed.

---

**Item 4: banners on the §2.4 items (not the scope guide).** Each banner is a blockquote inserted as the first lines of the file (above any H1), followed by one blank line. The body is not touched (BRIEF scope).

(4a) `docs/debugging/v7-i2c-investigation.md`, frozen:
```
> **FROZEN 2026-10. Historical only. Current state: `lab/STATE.md`.** This is the legacy notebook (volume 0). Its summary sections (Fastest read, TL;DR, Current working theory, Candidate fixes, Firmware state, Revert list, Immediate next steps) and the status line below are not current. Look up a phase by heading (`grep -n "^### Phase"`) and cite it as `L-PhNN` (`L-Ph24a` = Arduino-as-master, `L-Ph24b` = Exp 1 glitch filter).
```
(4b) `docs/debugging/v7-i2c-session-resume.md`, retired (the file currently starts with a blank line; the banner goes above it):
```
> **RETIRED, superseded by `lab/STATE.md`; do not load.** Kept in place because other documents cite this path.
```
(4c) `docs/debugging/v7-i2c-fresh-perspective-prompt.md`, retired:
```
> **RETIRED, superseded by `lab/STATE.md`; do not load.** A future outside-review prompt is generated from `lab/STATE.md` (context-strategy §7.3), not maintained by hand.
```
(4d) `docs/explorations/esp32-s3-i2c-master-deep-dive.md` and (4e) `docs/explorations/bq_solder_sda-catmull.md`, the same banner on both:
```
> **Pre-retry interpretation: conclusions not authoritative; see `lab/STATE.md`.** Reference facts may be cited from this file; its conclusions may not.
```
(4f) `tools/pcb-context/audit-specs/v7-main-i2c.audit.md`, retired for numbers:
```
> **RETIRED for numbers.** Clearances here are centreline to centreline and overstate the real copper gap by roughly half the combined trace widths (`docs/research/v7-retry/kicad-extraction-audit.md`). Don't quote them. Use edge-to-edge figures from a read-only probe (tools/CONTEXT.md Critical Rule) until the board model lands.
```
**Caveat on 4f:** this file is generated. `tools/pcb-context/routing_audit.py` (L685) writes `<spec_stem>.audit.md` and would overwrite the banner on any re-run. The options are to accept that (re-runs are unlikely before the board model replaces it) or to also put a one-line comment in `audit-specs/v7-main-i2c.json`. The second option is a tool edit and is not drafted here.

(4g) `hardware/pcb-main/REVIEW-HANDOFF.md`, not debug context:
```
> **Not debug context.** This is the April 2026 pre-order review prompt for v7. Do not load it for the v7 I²C fault; see `lab/STATE.md`.
```

---

**Item 5: auto-memory deletions plus the C90862 tip (context-strategy §2.5 items 1–2).** The memory files are outside the repo. The user may do (5a)–(5c) by hand, or approve them for the next Worker.

(5a) Delete `~/.claude/projects/-Users-marcocleirigh-Workspace-motion-play/memory/project_v7_i2c_bq_debug.md` and remove its MEMORY.md index line:
```
- [V7 I2C BQ debug status](project_v7_i2c_bq_debug.md) — Paused at Ph25: S3 master implicated (Arduino master ACKs); retry via docs/research/v7-retry
```
Nothing is lost. Each durable fact in it already has a home in the repo: the bodge warning (decisioning/postmortem), Board 3 (test-workflow-audit), the v6 0-error reference and device-002 (v6-v7-changelist), the refuted "noise antenna" framing (postmortem), and the firmware baseline (`v6-ref` tag). The first debugger session's STATE fill carries them forward.

(5b) Delete `project_pcb_revision_apr2026.md` and remove its index line:
```
- [PCB revision Apr 2026](project_pcb_revision_apr2026.md) — Main PCB v7 ordered: ESP32 WROOM, custom power, 3 critical bugs fixed
```
The v6→v7 facts are covered by `v6-v7-changelist.md`, and the SPICE lesson by `feedback_spice_symbols.md`. **Question for the user:** its "Housekeeping still needed" list (re-extract context JSONs; update LCSC fields in the schematic for the C22/C30 → C72522 and C34–36/C42 → C45783 substitutions; update `preflight-review-v2.md`; 22 components unannotated). Per §2.5, any item that is still live moves to `docs/initiatives/GARDEN.md`. Which items, if any, are still live? The LCSC substitutions are the likeliest.

(5c) `hardware/CONTEXT.md`: move the stock tip in, as a new bullet at the end of the "### 1. Main PCB" list.
```diff
@@ -36,4 +36,5 @@
 - **SN74AHCT125** logic level shifter — Between MCU (3.3V) and WS2818B LED strip (5V). 72 LEDs, 1.2m strip.
 - **3× JST-SH 4-pin connectors** (SM04B-SRSS-TB) — One per sensor PCB (Pin 1 = 3.3V, Pin 2 = GND, Pin 3 = SDA, Pin 4 = SCL)
+- **Sourcing:** BQ24195 (LCSC C90862) stock is chronically low. Check it before every main PCB order.
 
 ### 2. Sensor Rigid Base (`hardware/sensor-rigid/`)
```
C90862 = `BQ24195RGER` confirmed in `hardware/pcb-main/kicad/circuit-context.json` (L2454–2456).

After (5a)+(5b), `[MEMORY]` warnings drop from 4 to 2: MEMORY.md (the IINLIM index line) and `project_bq24195_iinlim_fix.md`. Item 6 decides those two.

---

**Item 6: `project_bq24195_iinlim_fix.md` and its index line. The user picks one option.** The facts were checked against `firmware/src/main.cpp`: `configureBQ24195()` at L283, called at L128 before `display.init()` at L140; REG00 0x36 at L105; REG05 0x8A at L107; address 0x6B at L101.

**Option A: reword in place** (stays in memory, no `v7` string, so 0 `[MEMORY]` warnings). New file:
```
---
name: BQ24195 IINLIM firmware fix (main PCB, v6 onward)
description: Every main PCB revision since v6 ties BQ24195 D+/D- to GND, requiring firmware to lift IINLIM at boot or the ESP32 browns out
type: project
---

Every main PCB revision since v6 (the current one included) ties U5 (BQ24195) D+ and D− pins directly to GND. Without USB BC1.2 detection, the BQ defaults to ~500 mA IINLIM and clamps VSYS the moment the ESP32 + display draw more than that — VSYS thrashes 4.2 V → 2.6 V, +5 V/+3.3 V brown out, the MCU resets in a loop.

**Firmware fix (in `firmware/src/main.cpp`):** `configureBQ24195()` runs in `setup()` before `display.init()`. Writes BQ24195 REG00=0x36 (IINLIM=2 A, EN_HIZ=0) and REG05=0x8A (40 s I²C watchdog disabled). I²C addr 0x6B on the same bus as the TCA9548A (SDA=43, SCL=44). Probes for the chip first so bare T-Display test setups still boot cleanly.

**Why:** Without this the brownout is unrecoverable on USB-only power (no battery to fall back on). Confirmed on the v6 board on 2026-04-10: VSYS held steady, display booted normally after the firmware change. Later revisions have identical D+/D− wiring, so the same fix is mandatory on first flash of any of them.

**How to apply:** Do not delete `configureBQ24195()` or move it after `display.init()`. Hardware ILIM ceiling is ~1.6 A via R32=330 Ω (530/RILIM), so register IINLIM=2 A is effectively 1.6 A — that's the realistic max on this board until R32 is changed.

**v8 candidate fix (no firmware dependency):** short U5 D+ to U5 D− (instead of both to GND). BQ24195 then detects a DCP via built-in BC1.2 and sets IINLIM=1.5 A in hardware. Removes the firmware dependency entirely.
```
New index line:
```
- [BQ24195 IINLIM firmware fix](project_bq24195_iinlim_fix.md) — Main PCB (v6 onward) needs firmware to lift BQ24195 IINLIM or ESP32 browns out under load
```
Grep-checked: the proposed file and index line contain no match for `v7|V7R-|BQ.*NACK` (case-insensitive). The applying Worker re-runs the checker to confirm. Wording edits: "T-Display resets" → "the MCU resets" (v7 has no T-Display), and "v7 has identical wiring" → "Later revisions…".

**Option B: move to `firmware/CONTEXT.md`.** Delete the memory file and its index line, and add a subsection under `## Power Management` (after `### Power Flow`). In-repo text can name v7; the checker only greps memory. 0 `[MEMORY]` warnings.
```diff
@@ -94,6 +94,14 @@
 - +5V → T-Display via pin 12 (5V pin)
 
+### BQ24195 Input Current Limit (main PCB v6 and v7)
+
+Both boards tie U5 (BQ24195) D+ and D− to GND, so BC1.2 detection never runs and the BQ defaults to ~500 mA IINLIM. Above that it clamps VSYS (4.2 V → 2.6 V), +5 V/+3.3 V brown out and the MCU reset-loops. This is unrecoverable on USB-only power.
+
+- **Fix:** `configureBQ24195()` in `firmware/src/main.cpp` runs in `setup()` **before** `display.init()`. It probes 0x6B (on the TCA9548A bus, SDA=43/SCL=44; bare T-Display setups skip it), then writes REG00=0x36 (IINLIM=2 A, EN_HIZ=0) and REG05=0x8A (I²C watchdog disabled). Do not delete it or move it after `display.init()`. Confirmed on v6, 2026-04-10.
+- **Ceiling:** the hardware ILIM is ~1.6 A via R32=330 Ω (530/R_ILIM), so the register's 2 A is effectively 1.6 A until R32 changes.
+- **v8 candidate:** short D+ to D− instead of both to GND. The BQ then detects a DCP and sets 1.5 A in hardware, with no firmware dependency.
+
 ### Power Isolation Challenge
```
Note on B: the surrounding `### Power Flow` text (DWEII module, AP2112K, T-Display pin 12) describes the pre-v6 power path and is stale. This subsection would sit beside it. Fixing the stale text is not in this initiative's scope; it is an Organizer/GARDEN item.

**Option C: keep as is, as an accepted `[MEMORY]` warning.** No change. The Phase 4 checker task then expects exactly 2 `[MEMORY]` warnings (MEMORY.md L5 index line, and `project_bq24195_iinlim_fix.md`), and these count as accepted. The cost: every session-start check prints them, and the PLAN Retirement acceptance ("no v7 lines in the memory index, except a line the user kept as accepted at W2") is met only through its exception.

Worker recommendation, for the Orchestrator to pass on or drop: **B**. It is a durable firmware fact that a firmware session should find without memory, and it fits §2.5's "durable facts belong in the repo".

---

**Outcome table, for the applying Worker to fill:**

| # | Item | Target | Outcome |
|---|---|---|---|
| 1a–1d | PROTOCOL.md roles row / lab entry / relay row / escalation | `.context/PROTOCOL.md` | pending |
| 2 | Pointer line | `.context/PROJECT.md` | pending |
| 3a–3b | kiutils rule / source-hash rule (3c: shown only) | `tools/CONTEXT.md` | pending |
| 4a–4g | Banners | 7 files listed above | pending |
| 5a–5c | Memory deletions, stock tip | memory dir, `hardware/CONTEXT.md` | pending (+ housekeeping-list question) |
| 6 | IINLIM memory: A / B / C | memory dir (+ `firmware/CONTEXT.md` if B) | pending |

**For the next Worker.**
- Apply only the approved items, one commit per file group, and re-run `check_state.py` afterwards. Expected `[MEMORY]` counts: 0 if 5a+5b and 6A or 6B are applied; 2 if 6C.
- The memory edits sit outside git, so record them in SESSION.md, since there is no commit for them.
- The out-of-scope finding (stale `firmware/CONTEXT.md` Power Flow and stale `hardware/CONTEXT.md` Main PCB bullets, which still describe T-Display/DWEII/AP2112K) is noted here only. It belongs to the Organizer or GARDEN, not this initiative's Deferred list.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 4 | Phase 4: Touch points (W2 prep) | PARTIAL | Yes — planned stop at the W2 gate, resolvable: re-dispatch after approvals | d1e9de4 | Items 1–6 drafted, none applied |

#### Verification
- `git diff f567168 d1e9de4`: only SESSION.md changed. No touch point applied. The memory directory was not touched. W2 is still `[~]`.
- Drafts read in full and presented to the user as items 1–6, plus the housekeeping-list question from 5b.

**W2 decisions (user, 2026-10-19):**
- Approved: items 1a–1d (PROTOCOL.md), 2 (PROJECT.md pointer), 3a–3b (tools/CONTEXT.md), 4a–4g (banners, including the regeneration caveat on 4f), 5a, 5b, 5c, and 6 = **Option B** (move IINLIM to `firmware/CONTEXT.md`, delete the memory file and its index line).
- Memory edits are applied by the Worker; the user did not choose to do them by hand.
- The housekeeping-list question (5b) was left unanswered. Before deleting `project_pcb_revision_apr2026.md`, its "Housekeeping still needed" list is preserved verbatim in the applying Worker's Notes, and the question is put to the user again. Nothing goes to GARDEN.md until the user answers.

---

### Worker #5 — Phase 4: Touch points, milestone (apply + checks)

**Dispatch:**
```
Initiative: Test Workflow Setup
Phase: 4 — Touch points, milestone
Initiative path: docs/initiatives/test-workflow-setup/
Additional reading: SESSION.md "Worker #4" Notes block (the drafted items 1–6, applied exactly as drafted) and the "W2 decisions" block that follows Worker #4's Verification. Phase notes:
- Apply the approved items: 1a–1d, 2, 3a–3b, 4a–4g, 5a, 5b, 5c, and 6 Option B.
  - Use the drafted text verbatim; adjust line anchors only.
  - One commit per file group.
- Memory files live outside git (~/.claude/projects/-Users-marcocleirigh-Workspace-motion-play/memory/), so log each memory edit in your Notes.
- Before deleting project_pcb_revision_apr2026.md, copy its "Housekeeping still needed" list verbatim into your Notes. Do not write to GARDEN.md.
- Fill in Worker #4's outcome table by restating it in your own Notes. Don't edit Worker #4's block.
- Then do the budget check and the check_state.py task.
- Stop before W3. The Orchestrator opens the milestone PR. Leave W3 and Handoff unchecked, and return DONE with "ready for W3".

Tasks assigned (from TASKS.md Phase 4):
- [~] **W2:** present each touch point as a diff for approval and apply only the approved ones: … (approvals recorded in SESSION.md; apply them)
- [ ] Budget check: measure the actual L0 (lines and bytes/4), with `docs/research/v7-retry/debugger-role-draft.md` standing in for `debugger.md`, and record it in SESSION.md. Pass: < 500 lines and ≤ ~12k tokens. If over, report which file and stop
- [ ] Run `python3 tools/lab/check_state.py` on the real `lab/`. Expect no findings except `[MEMORY]` warnings the user accepted at W2 (sentinel state). Any other finding: report and stop
- [ ] **W3:** (Orchestrator)
- [ ] 🔄 Handoff
```

#### Notes

**W2 applied.** Every approved item went in with the drafted text verbatim. Only the line anchors moved. One commit per file group:

| # | Item | Target | Outcome |
|---|---|---|---|
| 1a–1d | PROTOCOL.md roles row / lab entry / relay row / escalation | `.context/PROTOCOL.md` | Approved, applied: `59d6ed5` |
| 2 | Pointer line | `.context/PROJECT.md` | Approved, applied (unbackticked path, as drafted): `89f2195` |
| 3a–3b | kiutils rule / source-hash rule (3c: shown only) | `tools/CONTEXT.md` | Approved, applied: `2e177f1`. 3a without the optional rationale sentence. 3c: no change, no second `tools/lab/` entry |
| 4a–4g | Banners | the 7 files in Worker #4's item 4 | Approved, applied: `07b7d59`. 4f caveat accepted: a `routing_audit.py` re-run would drop the banner. No tool edit |
| 5a–5c | Memory deletions, stock tip | memory dir, `hardware/CONTEXT.md` | Approved. 5a and 5b applied (memory, outside git, see below). 5c: `306438b`. Housekeeping-list question still open (below) |
| 6 | IINLIM memory | memory dir + `firmware/CONTEXT.md` | Option B. Subsection added under `## Power Management`: `7c41a96`. Memory file and its index line deleted (below) |

TASKS W2 ticked in `74693a4`.

**Memory edits** in `~/.claude/projects/-Users-marcocleirigh-Workspace-motion-play/memory/`. No commit covers these.
- Deleted `project_v7_i2c_bq_debug.md` (5a).
- Deleted `project_pcb_revision_apr2026.md` (5b).
- Deleted `project_bq24195_iinlim_fix.md` (6B). Its content now lives in `firmware/CONTEXT.md` (`7c41a96`).
- `MEMORY.md`: removed the three matching index lines. It now has 3 lines: user profile, enclosure feedback, SPICE feedback.
- None of the remaining memory files links to a deleted file (grep checked).
- Pre-deletion copies of all four files are in the session scratchpad (`/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/212d4cc0-97d5-46f4-abb7-0f1b4279e2c9/scratchpad/memory-backup/`). That folder is temporary, so don't count on it.

**Preserved from `project_pcb_revision_apr2026.md` before deletion**, verbatim:
```
**Housekeeping still needed:**
- Re-extract circuit-context.json and pcb-layout-context.json (stale, extracted mid-session)
- Update LCSC fields in schematic for substituted parts
- Update preflight-review-v2.md with resolved blockers
- Commit all changes
- 22 components still lack AI annotations
```
The "substituted parts" are listed in the same file's section just above it, also verbatim:
```
**LCSC substitutions at JLCPCB checkout (not yet updated in schematic):**
- C22, C30: C7469958 → C72522 (47µF 35V 6.3x5.4mm)
- C34, C35, C36, C42: C109314 → C45783 (22µF 25V 0805 Samsung)
```
**Still open for the user (Orchestrator to ask again):** which of these items are still live? Live items go to `docs/initiatives/GARDEN.md`. Nothing has been written to GARDEN.md.

**Budget check (L0, bytes ÷ 4, measured on this branch after W2):**

| L0 item | Lines | Bytes | Tokens |
|---|---|---|---|
| `CLAUDE.md` | 3 | 123 | ~31 |
| `.context/PROJECT.md` (with the pointer line) | 151 | 10,972 | ~2,743 |
| `MEMORY.md` index | 3 | 373 | ~93 |
| `docs/research/v7-retry/debugger-role-draft.md` (stand-in for `debugger.md`) | 75 | 5,052 | ~1,263 |
| PROTOCOL §Session Management (L155–162) + §Git (L246–257) | 20 | 1,137 | ~284 |
| `lab/STATE.md`, actual skeleton | 52 | 3,365 | ~841 |
| **Total, actual** | **304** | **21,022** | **~5.3k** |
| `lab/STATE.md` at cap instead (150 lines, ~4k tokens per context-strategy §11.2) | 150 | ~16,000 | ~4,000 |
| **Total, STATE at cap** | **402** | **~33,700** | **~8.4k** |

**PASS** on both measures (< 500 lines, ≤ ~12k tokens).
- Read strictly, "§Session Management" stops at `## Relays`. If Relays through the Relay template is counted too (L155–213), the total at cap is 441 lines and ~8.8k tokens, which still passes.
- PROJECT.md's bytes include multi-byte emoji, so its token figure runs slightly high. The error is in the safe direction.

**Checker:** `python3 tools/lab/check_state.py` on the real `lab/` gives `RESULT: OK (0 warnings)`, exit 0, `as_of=V7R-000`, `cards=0`.
- That matches the sentinel state. W2 accepted no `[MEMORY]` warning, and 5a, 5b and 6B cleared all four.
- `tools/lab/tests/run_tests.py` also passes (0 failures).
- `--fresh hardware/pcb-main/kicad/circuit-context.json` still gives NO PROVENANCE (exit 2), as the 3b Scope bullet says.

**For the Orchestrator / W3:**
- W3 and Handoff are left unchecked. The branch is ready for the milestone PR.
- Out-of-scope note, carried over from Worker #4: the existing `### Power Flow` text in `firmware/CONTEXT.md` and the Main PCB bullets in `hardware/CONTEXT.md` still describe the pre-v6 path (T-Display, DWEII, AP2112K). The new IINLIM subsection now sits beside that stale text. This is for the Organizer or GARDEN, and is not added to Deferred.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 5 | Phase 4: Touch points (apply + checks) | DONE | No — clean completion (stopped before W3 as dispatched) | 213b741 | W2 items applied; budget pass; checker 0 warnings |

#### Verification
- Re-ran `check_state.py` on the real `lab/`: `RESULT: OK (0 warnings)`.
- MEMORY.md now has 3 lines with no v7 entries. The memory directory holds only user_profile and the two feedback files.
- Spot-checked: PROJECT.md L22 pointer line; PROTOCOL.md Debugger (draft) row L19, invocation note L25, lab/ entry L151, relay row L176, escalation L226. Each of the 7 banner files has +2 lines, with the banner on line 1 and the body untouched.
- TASKS Phase 4: W2, budget check and checker ticked; W3 and Handoff open.
- Carry forward: the housekeeping list (preserved in the Worker #5 Notes) still needs the user's answer. The memory backups are in the session scratchpad and are temporary. Stale Power Flow / Main PCB text in firmware/ and hardware/ CONTEXT.md is an Organizer/GARDEN item, outside this initiative.

---

### W3 — milestone PR (Orchestrator)
Branch pushed, PR "test-workflow-setup: log-only ready" opened against main. Merge with a **merge commit** (keeps `90053af`/`v7-clean` reachable from main's history).
- PR #79 merged by the Orchestrator at the user's request, using a **merge commit** (`b412284`). `90053af` (`v7-clean`) is reachable from `origin/main`.
- Branch `feat/test-workflow-setup` re-cut from the new main. W3 and the Phase 4 Handoff are ticked. **Track 1 complete: the debug track can start as ad-hoc sessions off the draft.**

---

### Worker #6 — Phase 5: Instrument facts (desk)

**Dispatch:**
```
Initiative: Test Workflow Setup
Phase: 5 — Instrument facts (desk)
Initiative path: docs/initiatives/test-workflow-setup/
Additional reading: docs/research/v7-retry/test-workflow-audit.md §2.1, §4.2, §4.3, §4.8, §5 as the tasks name; tools/CONTEXT.md before any KiCad probe. Phase notes: desk only — nothing goes to the bench. Every fact gets a source; anything unconfirmable is marked "needs bench" and is not used as verified. kiutils probes are read-only scratch scripts in your scratchpad, citing file@commit. Branch freshly re-cut from main after the milestone merge (no rebase needed).

Tasks assigned (from TASKS.md Phase 5):
- [~] From Rigol's DHO800/DHO900 Programming Guide, record the exact SCPI syntax for every query listed in PLAN (screenshot, waveform data, setup save/load, per-channel ratio/BW/scale/offset, timebase, trigger, measurements), with source page numbers
- [ ] Record the DHO804 Cal output spec, the setup-file extension, the CSV save path on fw 00.01.05, and Sensepeek SQ-500/SQ-10 bandwidth, attenuation and tip capacitance, each with its source. Mark each "desk-verified" or "needs bench"
- [ ] Check the ESP32-S3 V_OL datasheet figure behind §2.1's "≈ 30–80 mV". Record whether it's supported (cite the `docs/references/` page) and what the procedure may claim
- [ ] Evaluate the third-party DHO800 LAN/MCP project: licence, activity, coverage vs §5 item 1, effort to wrap. Write a short recommendation in PLAN
- [ ] kiutils probe (scratch script, read-only): the closest GND-net pad to U5 pins 5/6 on v7 (edge-to-edge, `file@commit`), and the v6 names of the master SDA/SCL test points, BQ24195 pins 5/6 and the GND pad. Record them in PLAN
- [ ] Draft the Phase 6 bench script as §4.8 blocks in SESSION.md (LAN connect, `*IDN?`, each query, USB save, LAN pull, third-party smoke test)
- [ ] 🔄 Handoff
```

#### Phase 6 bench script (draft, §4.8 blocks)

The Orchestrator relays these blocks to the user **one at a time** and records each REPORT. Every command and menu path comes from PLAN "Verified instrument facts". Port 5555 and the firmware-00.01.05 behaviour are the **needs bench** items these steps settle. Files land in `lab/inbox/phase6/` (gitignored).

Shell helper for S2–S6. The user pastes it once into a Mac terminal at the repo root:
```
SCOPE=<ip from S1>; mkdir -p lab/inbox/phase6
q(){ printf '%s\n' "$1" | nc -w 3 "$SCOPE" 5555; }
```

```
STEP S1 of 9 — Phase 6 (scope on the LAN)
DO:      Connect the DHO804 to the router with an Ethernet cable. On the scope open Utility > IO.
         Turn DHCP on. Then, on the router, give the scope's MAC a DHCP reservation (or set a fixed IP on the scope).
         While in Utility, set the scope's date/time to the Mac's clock.
CHECK:   The IO page shows a non-zero IP address and a "connected"-type LAN status.
         The scope clock is within 1 min of the Mac.
CAPTURE: Nothing.
REPORT:  1. IP address: ___   (reserved on router? yes/no; or fixed IP: ___)
         2. MAC address: ___
         3. Firmware version shown on the scope (Utility > About or similar): ___
         4. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: no IP after 1 min, or the IO menu looks different from "Utility > IO" → report the menu names you see and wait.
```

```
STEP S2 of 9 — Phase 6 (*IDN? over LAN)
DO:      Paste the shell helper (above) with the S1 IP. Then run:  q '*IDN?'
CHECK:   The command returns within ~3 s.
CAPTURE: Nothing.
REPORT:  1. Output, verbatim: ___
         2. If nothing came back: open http://<ip> in a browser, go to "SCPI Panel Control", send *IDN?, and paste what it shows: ___
         3. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: no response by either route → report and wait (port 5555 is unconfirmed).
```

```
STEP S3 of 9 — Phase 6 (known signal on screen)
DO:      Rigol stock probe on CH1, probe switch at 10×, tip and ground clip on the Cal output terminal.
         Set CH1 1 V/div, timebase 200 µs/div, edge trigger on CH1. Open the measurement panel with Vamp, Vtop and Vbase on CH1.
         Close every other menu so only the waveform and the measurement panel show.
CHECK:   A stable square wave is on screen. The panel shows three numbers.
CAPTURE: Nothing yet.
REPORT:  1. CH1 Probe Ratio as the scope's channel menu shows it: ___
         2. Vamp = ___ V, Vtop = ___ V, Vbase = ___ V (from the panel)
         3. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: no stable trace → report and wait.
```

```
STEP S4 of 9 — Phase 6 (every settings query, live)
DO:      Do not touch the scope. Run:
         for c in ':CHANnel1:PROBe?' ':CHANnel1:BWLimit?' ':CHANnel1:SCALe?' ':CHANnel1:OFFSet?' ':CHANnel1:COUPling?' \
           ':CHANnel1:DISPlay?' ':CHANnel1:INVert?' ':CHANnel1:UNITs?' ':TIMebase:MAIN:SCALe?' ':TIMebase:MAIN:OFFSet?' \
           ':TIMebase:MODE?' ':ACQuire:SRATe?' ':ACQuire:MDEPth?' ':ACQuire:TYPE?' ':TRIGger:MODE?' ':TRIGger:SWEep?' \
           ':TRIGger:STATus?' ':TRIGger:EDGE:SOURce?' ':TRIGger:EDGE:SLOPe?' ':TRIGger:EDGE:LEVel?' \
           ':TRIGger:IIC:WHEN?' ':TRIGger:IIC:CLEVel?' ':BUS1:MODE?' ':BUS1:THReshold? SDA' ':MEASure:AMSource?' \
           ':MEASure:THReshold:TYPE?' ':MEASure:SETup:MAX?' ':MEASure:SETup:MID?' ':MEASure:SETup:MIN?' \
           ':MEASure:ITEM? VAMP,CHANnel1' ':MEASure:ITEM? VTOP,CHANnel1' ':MEASure:ITEM? VBASe,CHANnel1' \
           ':SAVE:IMAGe:HEADer?' ':LAN:IPADdress?' ':LAN:VISA?' ':SYSTem:VERSion?' ':SYSTem:ERRor?'; do printf '%-34s ' "$c"; q "$c"; done \
           | tee lab/inbox/phase6/s4_queries.txt
CHECK:   Every line has a value after the command. The waveform is still on screen.
CAPTURE: lab/inbox/phase6/s4_queries.txt (written by the command).
REPORT:  1. Paste the whole output verbatim: ___
         2. Lines with an empty value, or an error from :SYSTem:ERRor?: ___
         3. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: more than three empty lines → report and wait.
```

```
STEP S5 of 9 — Phase 6 (freeze, then pull over LAN)
DO:      Press STOP on the scope, then do not touch it until S6 is done. Run:
         printf ':DISPlay:DATA? PNG\n' | nc -w 8 "$SCOPE" 5555 > lab/inbox/phase6/lan_shot.tmc
         printf ':SYSTem:SETup?\n' | nc -w 5 "$SCOPE" 5555 > lab/inbox/phase6/lan_setup.tmc
         q ':WAVeform:SOURce CHANnel1'; q ':WAVeform:MODE NORMal'; q ':WAVeform:FORMat ASCii'
         q ':WAVeform:PREamble?' | tee lab/inbox/phase6/lan_preamble.txt; q ':WAVeform:DATA?' > lab/inbox/phase6/lan_wave_ascii.txt
         ls -l lab/inbox/phase6/; head -c 40 lab/inbox/phase6/lan_setup.tmc; echo
CHECK:   The scope still shows STOP and the same frozen trace.
CAPTURE: The four lan_* files (written by the commands).
REPORT:  1. Paste the ls -l output: ___
         2. Preamble line, verbatim: ___
         3. First 40 bytes of lan_setup.tmc, verbatim: ___
         4. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: lan_shot.tmc is under 10 KB or the trace changed → report and wait.
```

```
STEP S6 of 9 — Phase 6 (same frozen capture to USB: SCPI-driven, then by menu)
DO:      USB stick in the front USB port, scope still STOPPED. Run:
         q ':SAVE:IMAGe:FORMat PNG'; q ':SAVE:IMAGe D:/p6img.png'; sleep 3; q ':SAVE:STATus?'
         q ':SAVE:WAVeform D:/p6wav.csv'; sleep 3; q ':SAVE:STATus?'
         q ':SAVE:SETup D:/p6set.stp'; sleep 2; q ':SAVE:STATus?'
         Then, by hand on the scope: Storage > Save tab > Choose "Save Wave" > Data Source "Screen" > Format "*.csv"
         > File Name p6menu > File Path D: > Save. Then Choose "Save Setup" > File Name p6menu > Save.
CHECK:   Each :SAVE:STATus? prints 1. The menu names match the ones above.
CAPTURE: The files on the stick (p6img.png, p6wav.csv, p6set.stp, p6menu.csv, p6menu.stp).
REPORT:  1. The three :SAVE:STATus? outputs: ___
         2. Menu path as it actually appeared on 00.01.05, if any name differed: ___
         3. File names the scope showed for the two menu saves: ___
         4. Setup-file extension the scope used: ___
         5. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: the stick isn't detected (no D:) or a save errors → report and wait.
```

```
STEP S7 of 9 — Phase 6 (stick to Mac)
DO:      Press RUN on the scope. Move the stick to the Mac and copy its files into lab/inbox/phase6/usb/ :
         mkdir -p lab/inbox/phase6/usb && cp /Volumes/<stick>/p6* lab/inbox/phase6/usb/ && ls -l lab/inbox/phase6/usb/
CHECK:   Five p6* files listed.
CAPTURE: lab/inbox/phase6/usb/ (copied).
REPORT:  1. Paste the ls -l output: ___
         2. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: fewer than five files → report which are missing and wait.
```

```
STEP S8 of 9 — Phase 6 (probe facts on the bench)
DO:      Move the Rigol probe off CH2 if it's there. Connect the Sensepeek SQ500 to CH2, tip and ground on the Cal output.
         Do not change CH2's Probe Ratio by hand. Then run: q ':CHANnel2:PROBe?'
CHECK:   A square wave is on CH2.
CAPTURE: Nothing.
REPORT:  1. :CHANnel2:PROBe? output: ___   (did the scope change CH2's ratio by itself when the SQ500 was plugged in? yes/no)
         2. Any accessories in the stock-probe bags that look like ground springs: ___
         3. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: anything smells or gets hot → report and wait.
```

```
STEP S9 of 9 — Phase 6 (third-party tool smoke test)
DO:      Only if you are OK installing it: in a Python ≥ 3.10 venv outside the repo, run
         pip install "git+https://github.com/mattjax16/rigol-dho-mcp@f9ac7191869845ae46ca714de69a877c388b2530"
         cd lab/inbox/phase6 && RIGOL_HOST="$SCOPE" rigol-dho-cli '*IDN?' ':CHANnel1:SCALe?' ':DISPlay:DATA? PNG'
CHECK:   The install finishes. The CLI prints the IDN string.
CAPTURE: The capture_*.png the CLI writes in lab/inbox/phase6/.
REPORT:  1. CLI output, verbatim: ___
         2. Name and size of the PNG it saved: ___
         3. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: you'd rather not install third-party code → skip, and say so in REPORT 1.
```

After S9, the Phase 6 Worker does the following:
- Strips the TMC headers from `lan_shot.tmc` and `lan_setup.tmc`.
- Pixel-diffs `lan_shot` against `p6img.png`, and compares `lan_wave_ascii.txt` sample-for-sample with `p6wav.csv`.
- Diffs `lan_setup` against `p6set.stp`.
- Marks each needs-bench row in PLAN.

#### Notes
All Phase 5 work was done at the desk. Every fact is in PLAN → Technical Notes → "Verified instrument facts", with its source. Nothing is marked *verified*: rows are either desk-verified or needs bench.

**Findings that change later phases:**
- **Firmware gap:** Rigol's Programming Guide (PGA39106-1110) and User Guide (UGA36105-1110) both document software 00.01.03, and the scope runs 00.01.05. Every SCPI row needs one live check (bench script S4–S6).
- **No SCPI command reads a file back.** Over the LAN, the CSV has to be built from `:WAVeform:DATA?` + `PREamble?`. The setup can come over the LAN as ASCII through `:SYSTem:SETup?` ([PG] p.270–271), but whether that matches the `.stp` file needs bench.
  - Alternative for Phase 7: the scope can save native files into a Mac SMB share (`:SAVe:SMB:*`, drive `I:`).
- **No "list active measurements" query.** The capture tool has to query a named item list.
- **The CSV menu path is "Save Wave", not "Waveform/Trace".** Storage → Save → Choose "Save Wave" → Screen/Memory → `*.csv` ([UG] pp.210–213). The setup extension is `.stp`.
- **Filenames given over SCPI are capped at 16 characters,** so §4.4 names can only be applied at ingest.
- **The DHO804 Cal output is 1 kHz, 3 Vpp** ([DS] p.17), with no tolerance given. V4's ±3 % is our own tolerance.
- **Probes:**
  - SQ500: 10:1 fixed (no switch), 500 MHz, 9 pF.
  - SQ10: 1:1, > 10 MHz, capacitance not specified.
  - V2's "probe switch position" can't apply to the SQ500. Phase 8 should word V2 as "probe ratio (switch or fixed)".
- **V_OL is partly supported** (Open Question struck):
  - The CAP_3 typical I_OL gives ≈ 18 Ω, so ≈ 35 mV at 2 mA. The datasheet's V_OL max is a no-load figure.
  - Pass stays ≤ 0.4 V, and the expectation becomes a labelled estimate.
  - The topic-4 acceptance "Dry run" row in PLAN still says "*once the datasheet check confirms it*". The Planner or Phase 8 may want to reword it to "estimate only". I didn't change the acceptance table.
- **Nearest GND to U5 pins 5/6 on v7:** **C21.2** at 2.64 mm edge-to-edge (TP4 is 12.09 mm). It is the same 2.64 mm on v6, so it suits the same-ground-length rule.
  - C21.1 next to it is `Protected_VBUS`: there is a bridging risk.
  - v6 names: TPIO43/44 = SDA/SCL, U5.5 = SCL and U5.6 = SDA (same as v7), and TP4 + TP_GND1 for GND.
  - **CL-26's wording in `v6-v7-changelist.md` implies v6 lacked TP4; it didn't.** That research doc is outside my edit scope, so I'm flagging it for the Orchestrator.
- **W5 input:**
  - The audit doesn't name the third-party project. The best candidate is `mattjax16/rigol-dho-mcp` (MIT, active July–October 2026, untested on any stated firmware). It doesn't write files, pull the setup or configure I²C.
  - Recommendation: build our own `capture.py`, optionally vendoring its stdlib `ScpiClient`.

**Mechanics:**
- The scratch probes (`gnd_probe.py`, `gnd_probe2.py`, `tp_probe.py`) and the downloaded PDFs were in the session scratchpad and are temporary. PLAN gives the PDF URLs and their sha256 prefixes, and the commits the probes ran against (`c2acffc` v7, `fd632ef` v6, kiutils 1.4.8).
- New Deferred line: add the ESP32-S3 datasheet to `docs/references/` (it was read from `~/Downloads`, so the task's "cite the docs/references page" couldn't be met literally).
- The Phase 6 bench script (S1–S9) is above. S9 installs third-party code, and the user may skip it.
- PLAN grew by about 110 lines with the facts subsection. It is still the right home (the Planner specified it), but the Phase 8 procedures should cite rows rather than copy them.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 6 | Phase 5: Instrument facts (desk) | DONE | No — clean completion | (handoff commit) | All 6 tasks + handoff; needs-bench items listed for Phase 6 |

#### Verification
- 7 commits, one per task plus the handoff (`bf902e6`…`0277e00`). Phase 5 is fully ticked. The tree is clean.
- PLAN: a new "Verified instrument facts" subsection (L145). The V_OL Open Question is struck. No date-stamped headings.
- Process note: the Worker wrote the `#### Result` row itself. That row is Orchestrator-owned. It is accurate, so I left it in place; the commit is `0277e00`.
- Carry forward:
  - (a) Every SCPI row is desk-verified against fw 00.01.03. S2/S4 settle 00.01.05.
  - (b) The topic-4 "Dry run" acceptance row still says "once the datasheet check confirms it". The check came back *partly supported*, so Phase 8 limits the claim to ≤ 0.4 V plus a labelled estimate. Flag this at Phase 9 when the acceptance is ticked.
  - (c) The CL-26 TP4 error in `v6-v7-changelist.md` goes to the user. That research artefact is frozen.
  - (d) W5 recommendation: build our own `capture.py`.

**Housekeeping answer (user, 2026-10-19):** none of the `project_pcb_revision_apr2026.md` housekeeping items are still live. Nothing goes to GARDEN.md.

---

### W4 — Phase 6 bench relay (Orchestrator)
Branch is current with main (no rebase needed). Relaying Worker #6's S1–S9 one step at a time. Each REPORT is recorded below, verbatim.

**S1 REPORT (user, verbatim):**
> 1. IP: 192.168.50.2, fixed IP on the scope (DHCP and Auto IP off). The scope is on a direct Ethernet link to the Mac through a USB-C Ethernet adapter (Mac en7, fixed at 192.168.50.1/24, no router). The router isn't near the bench. The Mac's internet stays on Wi-Fi (192.168.86.x). The scope has no internet access and is only reachable while the adapter is plugged into the Mac.
> 2. 00:19:AF:A5:19:A7
> 3. Firmware version 00.01.05
> 4. I don't see a way to change the date or time on the device itself. Looking online I found nothing either. My best guess is that it's supposed to get it's date and time via the network

Orchestrator notes on S1:
- LAN is a direct point-to-point link, not a DHCP reservation. It meets the PLAN requirement of a fixed IP, recorded: `192.168.50.2`, with the Mac on `192.168.50.1/24`. Firmware 00.01.05 is confirmed.
- **The clock CHECK failed: there is no on-device date/time setting.** That rules out NTP, because the scope has no internet. This matters for Phase 7: `ingest_usb.py` matches files by timestamp, and the log's capture times come from the scope. Probe added to S4: `:SYSTem:DATE?` and `:SYSTem:TIME?` (not desk-verified, so the result is recorded as observed only). Phase 7 handles the offset or uses Mac-side time. This is not a STOP condition, so the relay continues.

**S2 REPORT (user, verbatim):**
> I ran the terminal command, nothing appeared after I entered the two commands.
> I opened the IP address in the browser and sent that command, it showed the following:
> `-> *IDN?` / `<- (Return Count:50)` / `RIGOL TECHNOLOGIES,DHO804,DHO8A282M00872,00.01.05` / `* Connected to: TCPIP::192.168.50.2::INSTR`

Orchestrator notes on S2:
- SCPI works over LAN through the web panel, which uses VXI-11 (`::INSTR`). The raw socket path (`nc` to port 5555) returned nothing. Fallback route succeeded, so STOP IF did not fire.
- The capture tool needs a scriptable route, so I'm inserting diagnostic step S2b before S3. Two likely causes: macOS `nc` closes the connection when stdin ends, before the scope replies; or port 5555 is closed or disabled. If the socket can't be made to work, VXI-11 (e.g. pyvisa-py) is the alternative and becomes an input to W5 and Phase 7.

**S2b REPORT (user, verbatim):**
> 1. Connection to 192.168.50.2 port 5555 [tcp/personal-agent] succeeded!
> 2. RIGOL TECHNOLOGIES,DHO804,DHO8A282M00872,00.01.05
> 3. Connection to 192.168.50.2 port 111 [tcp/sunrpc] succeeded!
> 4. I opened Utility/IO and did not see anything tagged with any of those words. The screen looks no different than it did before I ran the commands. (screenshot: IO page shows Network status CONNECTED, VISA address TCPIP::192.168.50.2::INSTR, Static IP 192.168.50.2/24, gateway 192.168.50.1, DNS 0.0.0.0, mDNS OFF, Host Name RIGOL_DHO8A282M00…; left menu IO/Setup/About/Other/Auto Config/SelfCal/Options/Quick/Self Check)
> 5. Didn't nothing anything like that

Orchestrator notes on S2b:
- **Raw socket on port 5555 is confirmed on 00.01.05** (fact "port 5555" → bench-verified). VXI-11 portmapper (111) is also open.
- Cause of the S2 silence: macOS `nc` half-closes on stdin EOF before the scope replies. Holding stdin open (`; sleep`) fixes it. For S3 onward the helper becomes `q(){ (printf '%s\n' "$1"; sleep "${2:-1}") | nc -G 3 "$SCOPE" 5555; }`. S5/S6 one-liners use the same pattern, with a longer hold for binary reads. Phase 7's tool must keep the socket open until it has read the full reply; it should not rely on EOF.
- The scope has no user-visible socket-port setting on the IO page.

**S3 (given to the user as a step-by-step menu walk-through, using AUTO first, then 1 V/div, 200 µs/div, an edge trigger on CH1, and the Vamp/Vtop/Vbase panel). REPORT (user, verbatim):**
> 1. Ch1 probe is 10x
> 2. Vamp = 3.0037V, Vtop = 2.9774V, Vbase = -26.266mV / 43.333mV alternating
> 3. It printed RIGOL TECHNOLOGIES,DHO804,DHO8A282M00872,00.01.05
> 4. Nothing

Orchestrator notes on S3:
- The Cal output is a ≈ 0 → 3 V square wave, so V4 should read **Vamp** (3.0037 V, +0.12 % vs the 3 Vpp nominal). This answers the PLAN fact "Base/top levels … needs bench".
- Vbase flickers between two values about 70 mV apart. This is recorded as observed and not interpreted; Phase 8 notes it when it sets V4.
- The revised `nc` helper is confirmed working.
- The menu walk-through was given in more detail than the drafted block; Phase 8's procedure needs that level of step detail.

**S4 REPORT (user):** "Read the txt file for the output" (the ledger is `lab/inbox/phase6/s4_queries.txt`, 1728 B, gitignored). The Orchestrator read the output and transcribed it verbatim:
```
:CHANnel1:PROBe? 10 | :CHANnel1:BWLimit? OFF | :CHANnel1:SCALe? 1.000000E+00 | :CHANnel1:OFFSet? -2.994604E+00
:CHANnel1:COUPling? DC | :CHANnel1:DISPlay? 1 | :CHANnel1:INVert? 0 | :CHANnel1:UNITs? VOLT
:TIMebase:MAIN:SCALe? 2.000000E-4 | :TIMebase:MAIN:OFFSet? 0.000000 | :TIMebase:MODE? MAIN
:ACQuire:SRATe? 2.500000E+6 | :ACQuire:MDEPth? 1.0000E+04 | :ACQuire:TYPE? NORM
:TRIGger:MODE? EDGE | :TRIGger:SWEep? AUTO | :TRIGger:STATus? TD | :TRIGger:EDGE:SOURce? CHAN1
:TRIGger:EDGE:SLOPe? POS | :TRIGger:EDGE:LEVel? 1.617302E0 | :TRIGger:IIC:WHEN? STAR | :TRIGger:IIC:CLEVel? 1.617302E0
:BUS1:MODE? PAR | :BUS1:THReshold? SDA 0.000000 | :MEASure:AMSource? OFF | :MEASure:THReshold:TYPE? PERC
:MEASure:SETup:MAX? 9.000000E+01 | :MEASure:SETup:MID? 5.000000E+01 | :MEASure:SETup:MIN? 1.000000E+01
:MEASure:ITEM? VAMP,CHANnel1 3.0037E+00 | VTOP 2.9775E+00 | VBASe -2.6267E-02
:SAVE:IMAGe:HEADer? 1 | :LAN:IPADdress? 192.168.50.2 | :LAN:VISA? TCPIP::192.168.50.2::INSTR
:SYSTem:VERSion? 3.0 | :SYSTem:DATE? 2013-01-18 | :SYSTem:TIME? 09:52:08 | :SYSTem:ERRor? 0,"No error"
```
(The file mtime on the Mac was 2026-10-19 23:17 local.)

Orchestrator notes on S4:
- **All 39 queries answered and no errors were raised.** Every PLAN SCPI query row in S4 is **bench-verified on 00.01.05**.
- The measurement values match the S3 panel.
- **Measurement thresholds default to 90/50/10 %.** §4.3's 30→70 % rise time therefore needs `:MEASure:SETup:MAX 70` / `MIN 30` set explicitly. This resolves a needs-bench item for Phase 8.
- **The scope clock reads 2013-01-18 09:52:08 against a Mac time of ≈ 2026-10-19 23:17, so it is wrong by ≈ 13.75 years.** Before S5 I'm adding an optional `:SYSTem:DATE`/`:SYSTem:TIME` set attempt. The syntax is not desk-verified, so this is a try-and-observe step. The Phase 7 tool must not trust scope timestamps unless the set works.
- The S5/S6 one-liners have been rewritten to the hold-open `nc` pattern from S2b.

**S4b REPORT (user, verbatim):** "For s4b, the first and second commands produced "2026-10-19", the third: `23:19:26` / `-109,"Missing parameter"`"

Orchestrator notes on S4b:
- **The scope clock can be set over SCPI.** `:SYSTem:DATE <Y>,<M>,<D>` and `:SYSTem:TIME <H>,<M>,<S>` both took effect: the date read back 2026-10-19 and the time read back 23:19:26, which matches the Mac.
- One of the three sets raised `-109 Missing parameter`. The most likely candidate is the dashed date form, but the error queue doesn't say which command caused it. Phase 7 uses the comma form and confirms it with a read-back.
- Still unknown: whether the setting survives a power cycle. Phase 7's tool should set the clock (or check it) at the start of each session.

**S5 REPORT (user, verbatim):** "I ran that and those files are there for you to examine". The Orchestrator examined `lab/inbox/phase6/`:
- `lan_shot.tmc` is 93 801 B. It is a TMC block (`#9000093789`) wrapping a valid **1024×600 PNG**. The PNG shows STOP, 200 µs/div, 2.50 MSa/s, 10 kpts, CH1 1.00 V/div with offset −2.99 V, trigger CH1 rising edge at 1.62 V, and the Result panel reading Vamp 3.0037 V, Vtop 2.9774 V, Vbase −26.266 mV. This is the same frozen trace as S3/S4.
- `lan_setup.tmc` is 2 879 B: a TMC block of 2 867 B. **Its contents are binary and zlib-compressed, not ASCII**, which contradicts [PG] "expressed in ASCII". S7 compares it byte-for-byte with the `.stp` file.
- Preamble is `2,0,1000,1,2.000000E-6,-1.000000E-3,0.000000,1.3333E-04,-22459,32768`: ASCII format, NORMal mode, **1000 points**, xinc 2 µs, xorg −1 ms.
- `lan_wave_ascii.txt` has **1000 comma-separated values with no TMC header**, ranging from −0.120 V to 3.078 V. That is consistent with the Cal square wave at the screen's 1 000-point resolution.

**S6 REPORT (user, verbatim):**
> 1. `1` / `1` / `1` / `0,"No error"`
> 2. Your step 9c didn't really make sense -- the Save tab didn't have a "Save setup" button or anything with that label
> 3. The file names were like p6menu0 and p6menu1, but like I said above I don't think I did step 9c right so p6menu1 might just be the same as the other one.

Orchestrator notes on S6:
- **All three SCPI saves to `D:` succeeded** (`:SAVE:STATus?` = 1 for each, and no error). `:SAVE:IMAGe`, `:SAVE:WAVeform` and `:SAVE:SETup` are bench-verified on 00.01.05.
- **The menu path "Choose > Save Setup" from [UG] p.214 does not appear as described on 00.01.05.** S7 lists what the "Choose" control actually offers. The SCPI `.stp` save is enough for the comparison, so the menu setup save is not repeated.
- The scope adds an index to menu-save file names (`p6menu0`, `p6menu1`). The extensions are still to be confirmed in S7. This matters for Phase 7 ingest naming.

**S7 REPORT (user, verbatim):**
> 1. "Save wave", "Save image" and "Save setup"
> 2. done. The stick's name is "HANTEK" btw

Orchestrator notes on S7 (`lab/inbox/phase6/usb/` and `/Volumes/HANTEK` checked by listing only):
- Files copied: `p6img0.png` (97 347 B, 1024×600 RGBA PNG), `p6wav0.csv`, `p6menu0.csv` and `p6menu1.csv` (26 985 B each). The CSV header is `Time(s),CH1V`.
- **The scope appends an index digit to every saved name**, SCPI saves included: `p6img.png` became `p6img0.png` and `p6wav.csv` became `p6wav0.csv`. This feeds Phase 7 ingest naming.
- **No `p6set.stp` on the stick**, even though `:SAVE:SETup D:/p6set.stp` returned `:SAVE:STATus?` = 1 and no error. The SCPI setup save is therefore *not* verified. The menu "Save setup" option exists in the "Choose" list (user item 1). Step c was ambiguously worded, which led to a second CSV save. An older `main-pcb/mainpcb_ack0.stp` exists on the stick, which suggests the menu save does write `.stp` files.
- The stick shows file dates of Oct 20 2026 for the new files, so the S4b clock set carried into file timestamps. The older `nack_bq_full0.png` is dated Jan 18 2013.
- Inserting S7b: put the stick back, retry the SCPI setup save and read back the error, then do the menu setup save with corrected wording. The trace is now RUN; the setup comparison concerns settings, not trace data.

**S7b REPORT (user, verbatim):**
> 1. printed `1` / `0,"No error"`
> 2. File is p6menu0.stp
> 3. done

Orchestrator notes on S7b:
- **The SCPI `:SAVE:SETup D:/p6set.stp` failed silently a second time.** It returned `:SAVE:STATus?` = 1 and no error, but no file appeared on the stick. → **`:SAVE:SETup` is not usable on 00.01.05**, and the setup-file row is corrected accordingly.
- The menu path **Storage > Save > Choose "Save setup" > File Name > Save** works and wrote `p6menu0.stp` (43 839 B). The user's `cp` did not land the file, so the Orchestrator copied it from `/Volumes/HANTEK` into `lab/inbox/phase6/usb/`.
- **The `.stp` file is XML** (`<?xml version="1.0" encoding="UTF-8"?>` …, Android-style). The LAN `:SYSTem:SETup?` block is 2 867 B of zlib-compressed binary. **They are different formats, not the same bytes.** Over LAN the setup can only be captured as the binary blob; the human-readable `.stp` file needs a USB menu save. The settings themselves are fully readable through the S4 queries, so the Phase 7 log entry does not depend on either file.

**S8 REPORT (user, verbatim):**
> 1. "1"
> 2. Not sure
> 3. Yes, a few of them

Orchestrator notes on S8:
- `:CHANnel2:PROBe?` returns `1` with the SQ500 on CH2. The user is not sure whether the ratio changed by itself, so **auto-detection is not verified**. Before this run CH2's ratio was never set by hand, so `1` is probably just the default value.
- What `1` means depends on the SQ500's actual attenuation, which has not been confirmed. Inserting S8b: read CH2 Vpp/Vamp on the 3 V Cal signal. About 3 V means a 1:1 probe and a correct ratio. About 0.3 V means a 10:1 probe that the scope does not detect, so the ratio must be set by hand in every procedure.
- **Ground springs: present** in the Rigol stock-probe bags. The "buy ground springs before Phase 9" item is closed, unless they turn out not to fit the probe barrel; Phase 8 to check the fit at first use.
- S9 has not been answered yet.

**S8b REPORT (user, verbatim):**
> 1. VAMP is 9.9000E+37, VPP is 9.9000E+37
> 2. Yes, I have a ground spring for both types of probes. The SQ500 one has the same kind of spring needle head as the main probe.

Orchestrator notes on S8b:
- `9.9E37` is the scope's "invalid measurement" value. The report doesn't say whether AUTO was pressed before re-running, so the ratio question is still open. Likely causes: CH2 not displayed, CH2 off-screen or clipped, or the trigger still on CH1. Inserting S8c, which turns CH2 on explicitly, sets the trigger source to CH2, presses AUTO and re-reads.
- **Ground springs: verified present and fitting both probes** (the Rigol stock probe and the SQ500). The ground-spring purchase is closed.

**S8c REPORT (user, verbatim):**
> 1. VAMP:2.9781E-01 , VPP:3.0744E-01 , CH2 SCALe: 5.000000E-02, ERRor: 0,"No error"
> 2. Square wave

Orchestrator notes on S8c:
- With the ratio at 1X, the 3 Vpp Cal signal reads 0.298 V VAMP and 0.307 V VPP, a factor of about 10 low. → **The SQ500 is 10:1, and the DHO804 does not detect it; CH2 stayed at 1X.** This matches the desk fact "SQ500: 10:1 fixed (no switch)". **Every procedure must set the channel's probe ratio to 10X by hand** (`:CHANnel<n>:PROBe 10`) and check it with `:CHANnel<n>:PROBe?` before measuring. V2 is worded as "probe ratio (switch or fixed)".
- The S8b `9.9E37` came from CH2 being off or not the trigger source. Procedures must turn the channel on and set the trigger source explicitly before running `:MEASure:ITEM?`.
- The bench is left with CH2 at 1X and the trigger source on CH2. The next session sets both explicitly.

**S9:** not run. The optional third-party smoke test was offered three times and the user didn't take it up. It doesn't block anything. W5 goes ahead on the desk evidence, and a later result can be appended here.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| W4 | Phase 6: bench relay | DONE | No — every STOP IF stayed clear; inserted S2b, S4b, S7b, S8b, S8c to resolve CHECK misses | 3d03458 (+ this commit) | S1–S8c recorded; S9 optional, not run |

#### Verification
Re-derived from the reports above. The Worker takes these to PLAN "Verified instrument facts":
- **Verified on 00.01.05:**
  - LAN is a fixed IP over a direct link, and port 5555 answers. macOS `nc` needs the hold-open form.
  - All 39 S4 queries answered.
  - `:SYSTem:DATE`/`:TIME` set works (persistence across a power cycle is unknown).
  - `:DISPlay:DATA? PNG` returns a TMC block with a 1024×600 PNG.
  - `:WAVeform:DATA?` ASCII has no TMC header.
  - SCPI image and wave saves to the USB stick work.
  - The menu setup save writes `.stp` XML.
  - Cal output measures 3.0 V Vamp on the 10X Rigol probe.
  - SQ500 is 10:1 and not auto-detected.
  - Ground springs are on hand for both probes.
- **Corrected:**
  - `:SAVE:SETup` silently writes nothing, so it is unusable.
  - `:SYSTem:SETup?` is zlib binary, not ASCII, and a different format from `.stp`.
  - The scope appends an index digit to every saved filename.
  - Measure thresholds default to 90/50/10, so rise-time procedures must set 70/30.
  - There is no front-panel clock setting. The clock is set over SCPI.
- **Open for the Worker:** the LAN-vs-USB data comparison. The LAN set (S5) and the USB set (S6/S7) may not come from the same acquisition: the first CSV values differ at index 1 (2.986 vs 2.7136).

---

### Worker #7 — Phase 6: Scope on the LAN (bench)

**Dispatch:**
```
Initiative: test-workflow-setup
Phase: 6 — Scope on the LAN (bench)
Initiative path: docs/initiatives/test-workflow-setup/
Additional reading: SESSION.md section "### W4 — Phase 6 bench relay (Orchestrator)", including its #### Verification list; PLAN.md → Technical Notes → "Verified instrument facts"; bench files in lab/inbox/phase6/ (LAN: lan_shot.tmc, lan_setup.tmc, lan_wave_ascii.txt, s4_queries.txt; USB: usb/p6img0.png, usb/p6wav0.csv, usb/p6menu0.csv, usb/p6menu1.csv, usb/p6menu0.stp)

Tasks assigned (from TASKS.md Phase 6):
- [x] **W4:** the Orchestrator relays the Phase 5 bench blocks to the user one step at a time and records each REPORT in SESSION.md
- [~] Mark each [verify] item verified or corrected in PLAN "Verified instrument facts". Any item that fails goes to Open Questions, and the dependent tool or procedure work is blocked
- [ ] LAN-vs-USB comparison: a scratch script compares the PNG and CSV from the same capture. Record the result (acceptance: LAN capture)
- [ ] **W5:** present the build-vs-adopt evidence and get the user's decision. Record it in PLAN (strike through the question, add a Rejected Approaches line)
- [ ] 🔄 Handoff

The first task is marked `[~]` because it was dispatched to you — it is not someone else's work in progress.

Scope for this dispatch: tasks 2 and 3 only. W5 needs the user's decision, which the Orchestrator is getting in parallel. Stop after task 3 with a planned PARTIAL. Don't touch W5 or the handoff.

Phase-specific notes:
- Bench evidence lives only in the W4 REPORTs and the Orchestrator notes. Cite them as the source for each row, e.g. "bench W4 S7b, 2026-10-20". Mark each row verified, corrected (with the corrected fact) or failed. The W4 #### Verification list summarises the outcomes, but check each one against the verbatim REPORTs.
- Phase 7 inputs to record as facts or notes:
  - The scope clock is set over SCPI at the start of every session; persistence across power cycles is unknown.
  - Don't rely on the socket reaching EOF.
  - The scope adds an index digit to every saved filename.
  - `:SAVE:SETup` is unusable on 00.01.05.
  - The SMB drop (`:SAVe:SMB:*`) is still an alternative that hasn't been tested.
- Phase 8 inputs to record:
  - The SQ500 is 10:1 and the scope doesn't detect it, so set `:CHANnel<n>:PROBe 10` and read it back.
  - Turn the channel on and set the trigger source before running `:MEASure:ITEM?`; otherwise it returns 9.9E37.
  - Measure thresholds default to 90/50/10, so set 70/30 for rise time.
  - Ground springs fit both probes.
  - The user needs menu steps spelled out button by button.
- Comparison:
  - Keep the script in the session scratchpad. Only the results go into PLAN or SESSION.
  - The LAN set (S5) and USB set (S6/S7) may not be the same acquisition, since the trace was in RUN at some points. Work out from the REPORTs which pairs are truly from the same capture, and say so.
  - If no clean pair exists, compare format, scaling, length and value range, and leave "identical data" unclaimed.
  - The setup formats differ: LAN is zlib binary, the file is `.stp` XML. Decompress the blob, report what it contains, and compare settings only where both sides expose them. Don't call the setup "verified identical".
  - If the acceptance cannot be met because no same-capture pair exists, record it as not met, with the reason. A short re-capture becomes a bench step the Orchestrator relays later. Do not fabricate a pass.
- The Rigol probe-bag ground-spring purchase item (if it appears in PLAN/BRIEF/Deferred) is resolved: springs are on hand and fit both probes.

You are not the Orchestrator. Do not create documents, work across phases, or replan.
Return DONE, PARTIAL, or BLOCKED with specifics.
```

#### Notes
This was a planned PARTIAL: tasks 2 and 3 are done, and W5 and the handoff are untouched. All results are in PLAN → "Verified instrument facts". It has a new Bench column in the SCPI table, updated scope/probe rows, a "LAN-vs-USB comparison" paragraph, and "Inputs for Phase 7" and "Inputs for Phase 8" lists. There are two new Open Questions.

**Task 2 (facts):**
- Every needs-bench row is now marked verified, corrected, failed or not tested, each with a W4 step cited. I checked each against the verbatim REPORTs and not only the W4 Verification list.
- Points where I differ from or add to the Verification list:
  - `:SAVE:STATus?` = 1 is **not** proof of a write (S7b). Recorded as a correction.
  - The `9.9E37` fix in S8c changed three things at once (CH2 on, trigger source, AUTO). Which one mattered was not isolated. The procedure rule (turn the channel on and set the trigger source) stands, but it is recorded as not isolated.
  - The S8c report doesn't say how the trigger source was set, so an SCPI trigger-source set is still not tested.
  - The ground springs are verified from S8b (not S8).
- The one **failed** item is `:SAVE:SETup` (silent no-write). It is in Open Questions, and Phase 7's "pull the setup file" bullet is blocked as written. The options are listed there; the choice is for W5 or the start of Phase 7.
- New observation: the files on the stick are dated about **1 h ahead** of Mac local time after the S4b clock set (stick 00:27–00:45 on 10-20; Mac commits 23:22–23:47 on 10-19, PDT). Phase 7 ingest needs this. I found it by listing `/Volumes/HANTEK` (listing only).
- The TASKS.md "buy ground springs" note is struck as closed.

**Task 3 (comparison):**
- **Same capture: yes.** The scope was STOPPED from S5 to S7. The two PNGs have 0 differing pixels across the graticule, trace and Result panel, and the three USB CSVs are byte-identical. This resolves the W4 "may not be the same acquisition" note.
- **PNG matches.** The only differences are the saved file's "DHO804" header overlay, the USB icon, and 63 pixels of ±2-level noise on the STOP badge.
- **CSV does not match sample for sample.** The format, time axis, steps, edge indices and levels all agree, but only 145 of 1 000 samples are equal. The difference is noise-sized (≤ 64 mV) away from the edges and up to 0.82 V within ±2 samples of an edge.
- **Acceptance "LAN capture" is recorded as NOT MET (CSV half).** I did not tick the acceptance table; Phase 9 does that.
- **Proposed bench step for the Orchestrator to relay:**
  1. With the trace frozen, set `:WAVeform:SOURce CHANnel1`, `:WAVeform:MODE RAW`, `:WAVeform:FORMat ASCii` (or BYTE plus PREamble), then pull `:WAVeform:DATA?`.
  2. Save `:SAVE:MEMory:WAVeform D:/p6mem.csv`.
  3. Copy the CSV off the stick, then compare sample for sample, and check whether both 1 000-point sets are subsets of the RAW data.
  - RAW reads may need `:WAVeform:STARt`/`STOP` chunking. That isn't tested; [PG] pp.406–413.
- **Setup:** the `:SYSTem:SETup?` blob is a 20 B header plus 29 records, each with a binary header and a zlib stream (6 745 B decoded). It holds packed LE integers and `$<len>` strings, with no field names. Its values agree with the `.stp` XML wherever both have them (214 of 215 distinctive integers). I recorded this as "consistent where comparable", not "identical".
- The scratch scripts (`compare.py`, `setup_cmp.py`) are in the session scratchpad (`p6cmp/`) and are temporary. Re-running needs only Python 3.7 stdlib: there is a pure-Python PNG decoder, because PIL is absent.

**For the Orchestrator / W5:**
- The S9 smoke test was never run, so the W5 recommendation's line "use the Phase 6 smoke test to validate the transport" has no result behind it. Port 5555 itself is verified (S2b).
- The `:SAVE:SETup` Open Question and the LAN CSV Open Question both bear on what `capture.py` writes. They are worth raising alongside W5.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 7 | Phase 6: Scope on the LAN (tasks 2–3) | PARTIAL (planned) | Yes — two new Open Questions; the LAN-capture acceptance is not met | c2bed11 | Facts marked; PNG matches; CSV does not match sample for sample; setup consistent where comparable |

#### Verification
- Commits `2e7161d` and `c2bed11`; the tree is clean. Tasks 2 and 3 are ticked; W5 and the handoff are `[ ]`. PLAN has no date-stamped headings. The two new Open Questions are in PLAN (`:SAVE:SETup`; LAN CSV ≠ USB CSV).
- [ORCH] Evaluating: resolvable without replanning? Partly.
  - The CSV question needs evidence first. The Orchestrator relays the re-capture bench step S10: RAW memory over the LAN vs `:SAVE:MEMory:WAVeform` CSV on one frozen trace.
  - The setup-file option is a user decision. If it changes the Phase 7 task wording, the Planner is engaged at that point.
- **W5 decision (user, verbatim, 2026-10-20):** "build + borrow the socket client". Our own `capture.py`, with a credited copy of the MIT `ScpiClient` from `mattjax16/rigol-dho-mcp` @ f9ac719. The next Phase 6 Worker records this in PLAN, along with the handoff.
- Carry forward: stick file timestamps run about 1 h ahead of Mac local time after the S4b clock set. This goes to Phase 7 ingest.

---

### W4b — Phase 6 bench relay, follow-up (Orchestrator)
This step answers the Worker #7 Open Question "LAN CSV ≠ USB CSV". The same rules as W4 apply.

**S10 REPORT (user, verbatim):**
> 1. Both error results were `0,"No error"`, the status result was "1"
> 2. You can check the size of those yourself. The USB stick did not have anything named p6mem...csv

Orchestrator notes on S10 (checked by listing and reading only):
- **The LAN RAW pull works:**
  - `lan_raw_ascii.txt` is 140 000 B and holds 10 000 comma-separated values, with no TMC header. It ends at +0.572 V, which is mid-edge.
  - Preamble `2,2,10000,1,4.000000E-7,-2.000000E-3,0.000000,1.3333E-04,0,32768`: format ASCII, mode RAW, 10 000 points, xinc 0.4 µs.
  - `:WAVeform:STARt 1`/`STOP 10000` worked in a single read at 10 kpts.
- **`:SAVE:MEMory:WAVeform D:/p6mem.csv` failed silently**, the same way `:SAVE:SETup` did: `:SAVE:STATus?` = 1, no error, no file. `/Volumes/HANTEK` lists no `p6mem*`. So the SCPI *memory* save is unusable on 00.01.05, while the SCPI *screen* wave save (S6) works.
- Inserting S10b: a menu save of memory data from the same frozen trace.

**S10b REPORT (user, verbatim):**
> 1. STOP
> 2. There's a field labelled "DATA SOURCE" which has the options "SCREEN" and  "MEMORY". I presumed that was what you were referring to and selected MEMORY. The menu has another field labeled "FORMAT" from which I selected "*.csv".
>
> The file from the USB stick is in place at `lab/inbox/phase6/usb/p6mem0.csv`

Orchestrator notes on S10b:
- The trace was still frozen, so S10 and S10b come from the same acquisition.
- The menu wording is **Storage → Save → Choose "Save wave" → DATA SOURCE = MEMORY → FORMAT = \*.csv → File Name → Save**. Phase 8 should use these exact labels.
- `p6mem0.csv` is 160 045 B with 10 001 lines. Its header is `CH1V,t0 =-2.000000e-03, tInc = 4.000000e-07,`, a different layout from the screen CSV's `Time(s),CH1V`. The first two values match the LAN RAW pull exactly (+1.223733, +1.679333), and t0/tInc match the RAW preamble. The full comparison is the Worker's job.

**Setup-file decision (user, verbatim, 2026-10-20):** "Let's go with option a". Each capture saves the `:SYSTem:SETup?` binary blob over the LAN, and the log entry records the readable settings from the S4 queries. No per-capture menu save. This keeps to the Phase 7 scope, so no Planner is needed.

**User clarification on PLAN edits (verbatim):** "Workers can update the plan of what they are actively working on, yes. They're not supposed to plan *new* initiatives, which is what I thought you meant. So you can forget about my comment."

---

### Worker #8 — Phase 6: Scope on the LAN (bench), W5 + handoff

**Dispatch:**
```
Initiative: test-workflow-setup
Phase: 6 — Scope on the LAN (bench)
Initiative path: docs/initiatives/test-workflow-setup/
Additional reading: SESSION.md sections "### Worker #7 — Phase 6" (its #### Notes, Result and Verification, including the W5 decision) and "### W4b — Phase 6 bench relay, follow-up"; PLAN.md Open Questions and "Verified instrument facts"; lab/inbox/phase6/lan_raw_preamble.txt, lan_raw_ascii.txt, usb/p6mem0.csv; Worker #7's scratch scripts in /private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/212d4cc0-97d5-46f4-abb7-0f1b4279e2c9/scratchpad/p6cmp/ (reuse them if useful)

Tasks assigned (from TASKS.md Phase 6):
- [x] **W4:** the Orchestrator relays the Phase 5 bench blocks to the user one step at a time and records each REPORT in SESSION.md
- [x] Mark each [verify] item verified or corrected in PLAN "Verified instrument facts". Any item that fails goes to Open Questions, and the dependent tool or procedure work is blocked
- [x] LAN-vs-USB comparison: a scratch script compares the PNG and CSV from the same capture. Record the result (acceptance: LAN capture)
- [~] **W5:** present the build-vs-adopt evidence and get the user's decision. Record it in PLAN (strike through the question, add a Rejected Approaches line)
- [ ] 🔄 Handoff

The first open task is marked `[~]` because it was dispatched to you — it is not someone else's work in progress.

Phase-specific notes:
- Follow-up to the completed comparison task, before W5: compare the S10 LAN RAW pull (`lan_raw_ascii.txt` with `lan_raw_preamble.txt`) sample by sample against the S10b menu memory CSV (`usb/p6mem0.csv`). Both come from one frozen acquisition (S10b TRIGger:STATus = STOP).
  - Report equal count, max abs diff, alignment offset if any, and whether t0/tInc match the preamble.
  - Check whether the S5 LAN screen ASCII and the S6/S7 screen CSV are subsets of this 10 k set. They aren't the same acquisition as S10, so this can only be a structural or decimation check unless you can show otherwise. Don't overclaim.
  - Update the comparison result and the LAN CSV Open Question in PLAN with the outcome. If the two memory sets match sample for sample, the acceptance is met on memory data: strike the Open Question and state that the capture tool writes RAW memory data and that W6 compares against a menu memory CSV. If they don't match, keep the Open Question open and return PARTIAL with the numbers.
- Bench facts from W4b to add to PLAN "Verified instrument facts":
  - `:WAVeform:MODE RAW` ASCII at 10 kpts reads in one go with STARt 1/STOP 10000; there's no TMC header. (bench W4b S10)
  - `:SAVE:MEMory:WAVeform` fails silently, like `:SAVE:SETup`. (S10)
  - The menu memory save path uses exact labels DATA SOURCE = MEMORY, FORMAT = *.csv. (S10b)
  - The memory CSV header is `CH1V,t0 =…, tInc = …,`, a different layout from the screen CSV.
- W5: the user's decision is recorded verbatim in SESSION (Worker #7 Verification): "build + borrow the socket client". Record it in PLAN as the task says. The decision is our own `capture.py` plus a credited, vendored copy of the MIT `ScpiClient` from `mattjax16/rigol-dho-mcp` @ f9ac7191869845ae46ca714de69a877c388b2530. The Rejected Approaches line covers adopting the tool as-is: untested on 00.01.05, writes no files, no setup pull, no I²C configuration, and the S9 smoke test was not run.
- Setup-file decision (user, verbatim in SESSION W4b): "Let's go with option a". Strike the `:SAVE:SETup` Open Question with this resolution: the capture tool saves the `:SYSTem:SETup?` binary blob over the LAN, and the log entry records the readable settings from the S4 queries; no per-capture menu save. Adjust the Phase 7 "pulls the … setup file" wording in PLAN and TASKS so it names the blob. This is within scope; don't change other Phase 7 tasks.
- Then do the 🔄 Handoff.

You are not the Orchestrator. Do not create documents, work across phases, or replan.
Return DONE, PARTIAL, or BLOCKED with specifics.
```

#### Notes
Phase 6 is complete: W5 and the handoff are ticked. All results are in PLAN → "Verified instrument facts" (SCPI table, CSV save path row, LAN-vs-USB comparison, Inputs for Phase 7), Technical Notes → Capture tooling, Rejected Approaches and Open Questions.

**RAW memory comparison (W4b S10 vs S10b, one frozen acquisition):**
- `lan_raw_ascii.txt` and `usb/p6mem0.csv` both have 10 000 values. **10 000 / 10 000 are equal**, as numbers and as text. Max abs difference is 0 and the alignment offset is 0. Shifts of ±1…5 samples match only 397–645 values, so the zero offset is not a coincidence.
- The memory CSV header gives `t0 = -2.000000e-03` and `tInc = 4.000000e-07`. Both equal the RAW preamble's xorg and xinc exactly.
- **Screen sets vs the 10 k memory:** this is a structural check only, because S5–S7 was a different acquisition. The screen window (xorg −1 ms, xinc 2 µs) corresponds to RAW indices 2 500–7 499 at stride 5. At that stride, its 1.5 V crossings fall at 1/251/501/751, the same as both screen sets, and all three sets have the same ≈ 2.5–2.7 mV value steps. But **no screen value occurs in the RAW value set** (the grids are offset; I didn't check why). So a value-level subset test isn't possible, and I don't claim one. Which memory samples each screen path takes is still a hypothesis.
- **Outcome:** the acceptance "LAN capture" is met on memory data (PNG match plus RAW = menu memory CSV). The LAN CSV Open Question is struck. PLAN now states that the capture tool writes RAW memory data and that W6 compares against a menu memory CSV.
- The scratch script is `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/212d4cc0-97d5-46f4-abb7-0f1b4279e2c9/scratchpad/p6raw/rawcmp.py`. It is temporary, stdlib only, and takes the `lab/inbox/phase6` path as its argument.

**W4b facts added to PLAN:** the RAW ASCii 10 kpt single read with STARt 1/STOP 10000 and no TMC header; `:SAVE:MEMory:WAVeform` failing silently; the menu memory path with the exact labels DATA SOURCE = MEMORY and FORMAT = \*.csv; and the memory CSV layout (`CH1V,t0 =…, tInc = …,` then `value,,` per line, with no time column).

**W5 and setup:**
- W5 is recorded: the Open Question is struck, the decision is quoted, there is a Rejected Approaches line for adopting `mattjax16/rigol-dho-mcp` as-is, and the Capture tooling heading names the vendored `ScpiClient` @ `f9ac7191869845ae46ca714de69a877c388b2530`.
- The `:SAVE:SETup` Open Question is struck with option (a). PLAN's Phase 7 bullet now reads "pulls the PNG, the RAW memory CSV and the `:SYSTem:SETup?` binary blob".

**For the Orchestrator:**
- TASKS.md Phase 7 has no "setup file" wording, so I made no TASKS change for the blob.
- The W6 task in TASKS still says "Compare it with a USB save of the same screen". By PLAN, the comparison is now against a menu **memory** CSV (DATA SOURCE = MEMORY) of the same frozen capture, plus a PNG. I left the task text alone, as instructed ("don't change other Phase 7 tasks"). You may want to reword it, or have the Phase 7 Worker read PLAN for it.
- RAW single-read is verified only at 10 kpts. Deeper memory may need `STARt`/`STOP` chunking, and that is noted in the Phase 7 inputs.
- Commit mechanics: the W5 and setup PLAN edits went into the comparison commit `39d6f88`. The W5 tick is in `f301ef2`.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 8 | Phase 6: Scope on the LAN (W5 + handoff) | DONE | No — clean completion | 935787e | RAW memory LAN vs menu memory CSV 10000/10000 equal; acceptance met on memory data; W5 and setup (a) recorded |

#### Verification
- Commits `39d6f88`, `f301ef2` and `935787e`; the tree is clean. Phase 6 is fully ticked. Every PLAN Open Question is struck. No date-stamped headings. origin/main has not moved, so no rebase is needed for Phase 7.
- Carry forward to Phase 7:
  - (a) The TASKS W6 wording "USB save of the same screen" is behind PLAN. Per PLAN, W6 compares against a **menu memory CSV** of the same frozen capture, plus the PNG. The Phase 7 Worker aligns the TASKS wording, since it is a Worker-owned doc and the change is within scope.
  - (b) A single RAW read is verified only at 10 kpts.
  - (c) Stick file timestamps run about 1 h ahead of Mac local time.
  - (d) Task 4 needs the user's Google Drive path. The Orchestrator asks the user in parallel with tasks 1–3.

---

### Worker #9 — Phase 7: Capture, ingest, validation, backup (tasks 1–3)

**Dispatch:**
```
Initiative: test-workflow-setup
Phase: 7 — Capture, ingest, validation, backup
Initiative path: docs/initiatives/test-workflow-setup/
Additional reading: SESSION.md "### Worker #8" (Notes + Verification carry-forward) and "### W4b"; PLAN.md "Verified instrument facts" with its "Inputs for Phase 7" list, and the Capture tooling section (W5 decision); tools/CONTEXT.md Lab Tools section; existing tools/lab/ (lablib.py, precommit.py, run_tests.py, fixtures); bench samples in lab/inbox/phase6/ (usable as test inputs)

Tasks assigned (from TASKS.md Phase 7):
- [~] Write the capture tool (or the wrapper around the adopted one) per PLAN: files named per §4.4, log entry with every required §4.6 field filled from scope queries, operator fields left as TODO
- [ ] Write `tools/lab/validate_log.py` (branches on `kind`). Wire it into the pre-commit helper for staged `lab/log/*.yaml`. Add a passing and a failing fixture
- [ ] Write `tools/lab/ingest_usb.py` (copy to inbox, timestamp-match, rename into captures)
- [ ] Ask the user for the Google Drive for desktop folder path. Write `tools/lab/backup_captures.sh` (rsync captures/ + inbox/), with the path as one config value
- [ ] **W6:** one bench capture with the tool. Compare it with a USB save of the same screen, and run the validator on the generated entry (acceptance: capture tool). Update the `tools/CONTEXT.md` tools/lab section
- [ ] 🔄 Handoff

The first task is marked `[~]` because it was dispatched to you — it is not someone else's work in progress.

Scope for this dispatch: tasks 1–3 only. Stop after task 3 with a planned PARTIAL. The Orchestrator is getting the Drive path (task 4) from the user, and W6 is a bench step the Orchestrator relays.

Phase-specific notes:
- W5 decision (PLAN): build our own `capture.py`, with a credited vendored copy of the MIT `ScpiClient` from `mattjax16/rigol-dho-mcp` @ f9ac7191869845ae46ca714de69a877c388b2530. Fetch the file at that exact commit. Keep the MIT licence text and attribution in the vendored file, and note its provenance (URL, commit, sha256) in tools/CONTEXT.md when you update it. Read the vendored code fully before using it.
- The capture tool works only against facts PLAN marks verified on 00.01.05. Key points:
  - Use the hold-open socket and don't rely on EOF.
  - Set the scope clock from the Mac at the start.
  - Waveform: RAW memory ASCii, STARt 1/STOP = memory depth. A single read is verified only at 10 kpts; for deeper memory, chunk or refuse with a clear message. Don't guess.
  - Write the PNG from `:DISPlay:DATA? PNG` with the TMC header stripped.
  - Setup: the `:SYSTem:SETup?` binary blob (option a), plus readable settings from the S4 queries in the log entry.
  - Never use `:SAVE:SETup`, `:SAVE:MEMory:WAVeform` or `:SAVE:STATus?` as proof of a save.
  - `:MEASure:ITEM?` returns 9.9E37 when invalid. Record it as invalid, not as a number.
- The tool can't be tested on the bench in this dispatch: the scope isn't attached for Workers. Test it against a local fake SCPI server or recorded responses, using the phase6 bench files. Add those tests to run_tests.py. W6 is the real bench check.
- The TASKS W6 wording "USB save of the same screen" is behind PLAN, which says to compare against a menu memory CSV (DATA SOURCE = MEMORY) of the same frozen capture, plus the PNG. Align the W6 wording in TASKS to PLAN. Don't change anything else in Phase 7's task list.
- ingest_usb.py: saved filenames get an appended index digit, and stick timestamps ran about 1 h ahead of Mac local time after the S4b clock set (Worker #7 note; cause unknown). Match tolerantly and report ambiguity rather than guessing. Never delete from the stick.
- Draft the W6 bench script for the Orchestrator to relay, in the same STEP/DO/CHECK/CAPTURE/REPORT/STOP IF format as the Phase 5 script. Put it in your #### Notes block. Menu steps must be spelled out button by button with the exact labels from PLAN. The operator must keep the trace frozen between the tool run and the menu memory save.

You are not the Orchestrator. Do not create documents, work across phases, or replan.
Return DONE, PARTIAL, or BLOCKED with specifics.
```

#### Notes
Tasks 1–3 are done and ticked. This is a planned PARTIAL: task 4 (the Drive path), W6 and the handoff are still open. Commits: `04a124d` (capture), `f0c781e` (validator + hook), `2d48cee` (ingest + tests). `python3 tools/lab/tests/run_tests.py` passes: the 9 checker fixtures plus 39 tool checks.

**What was built** (PLAN Technical Notes → Capture tooling → "As built" has the details):
- `tools/lab/capture.py --test V7R-NNN --arm A1 [--session …]` writes `<stem>.png`, `<stem>.csv` (`Time(s),CH1V…`, RAW values verbatim) and `<stem>.setup.bin` (the `:SYSTem:SETup?` blob, not named `.stp` because it is not the XML format). It appends one measurement entry to the session log, or creates the log. Every scope-sourced field is filled. `dut.*`, `validation.*`, `signal`/`point`/`probe`, `feature` and `raw_observation` are left as `TODO`. On a fresh capture the validator returns exit 3 (TODOs only, no errors).
- The vendored client is `tools/lab/vendor/scpi.py`: the MIT licence and provenance header, then the upstream file **unmodified**. Source: `https://github.com/mattjax16/rigol-dho-mcp/blob/f9ac7191869845ae46ca714de69a877c388b2530/rigol_dho_mcp/scpi.py`, upstream sha256 `9fface904495086784322b44cdfac4edaa35ea215f1c87ccdfe5b0d4004a5066`. The header gives the one-liner that rechecks the hash. I read it in full; it runs on the repo's Python 3.7. **Task 5 needs this provenance in `tools/CONTEXT.md`.** I did not touch CONTEXT.md, because that edit belongs to the W6 task.
- One hazard in the vendored client: after a binary block it reads the trailing `\n` with a 0.5 s timeout. A late `\n` would shift every later reply by one. capture.py resyncs with `*IDN?` after each block, and a test confirms that without the resync the capture fails.
- `validate_log.py` branches on `kind`. Exit codes: 0 valid, 1 errors, 3 TODOs only, 2 PyYAML missing. Pre-commit rule 4 rejects a staged `lab/log/*.yaml` with errors and only **warns** on TODOs, so mid-session per-arm commits aren't blocked. The Orchestrator may want to confirm that choice with the user. `lab/templates/log.yaml` itself validates clean.
- `ingest_usb.py` requires `--at` (the Mac time, which also dates the name) and takes `--files` as an option (the scope names; the index digit may be left off). It tries stick offsets of 0 and +60 min within ±300 s. When the match is ambiguous it lists the candidates and renames nothing. It never writes to the stick. The inbox copy is kept, and a mapping is appended to `captures/<ID>/INGEST.tsv`.
- Test inputs: five Phase 6 bench recordings, committed in `tools/lab/tests/scope_fixtures/` (≈ 240 KB), so the tests don't depend on the gitignored inbox. Log fixtures are in `tools/lab/tests/log_fixtures/{pass,fail}/`.

**Not bench-verified, and flagged in the tool:**
- `--chunked` (memory deeper than 10 kpts). Without it, deeper memory is refused with a message.
- The I²C trigger/decode queries other than WHEN/CLEVel. They are tolerated: a missing reply is recorded, not fatal.
- `:SYSTem:SETup?` and PNG over the vendored client. Phase 6 pulled them with `nc`/scratch code, so W6 is the first real run of the vendored client (the S9 smoke test was never run).

**For W6 comparison (the Worker after the bench):**
- Compare the CSV column `CH1V` as text against the `w6mem*.csv` value column (drop the trailing `,,`). The memory CSV's `t0`/`tInc` should equal the entry's PREamble xorg/xinc.
- Compare the PNG pixels over the graticule. The header overlay and the USB icon differ by design (Phase 6).

**W6 bench script (draft, §4.8 blocks; relay one at a time).** It uses the dummy ID `V7R-999` (the Phase 2 precedent) and puts the session log in the gitignored inbox, so nothing lands in `lab/log/`. Run every command in a Mac terminal at the repo root, with the scope on the direct link (`192.168.50.2`).

```
STEP S1 of 6 — W6 (known signal, scope running)
DO:      Insert the USB stick into the scope. Rigol stock probe on CH1, probe switch at 10×, tip and ground clip on the Cal output terminal.
         CH1 1 V/div, timebase 200 µs/div, edge trigger on CH1 (the Phase 6 S3 setup). Measurement panel showing Vamp, Vtop and Vbase on CH1.
         Press RUN/STOP until the scope is running. Close every other menu.
CHECK:   A stable square wave is on screen, the panel shows three numbers, and the stick icon is shown.
CAPTURE: Nothing.
REPORT:  1. Vamp / Vtop / Vbase CH1 from the panel: ___ / ___ / ___
         2. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: no stable wave, or the stick icon is missing → report and wait.
```

```
STEP S2 of 6 — W6 (capture tool; this freezes the trace)
DO:      Run:
           python3 tools/lab/capture.py --test V7R-999 --arm A1 --session lab/inbox/w6/$(date +%F)_s01.yaml
         From here until S4 is done, do not press any scope button and do not touch the probe.
CHECK:   The command ends with "The scope is left STOPPED." and the scope screen shows STOP.
CAPTURE: The tool writes the files itself.
REPORT:  1. The tool's full output, verbatim: ___
         2. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: the output starts "capture: REFUSED" or "capture: scope error" → paste it and wait (nothing was written). If it says memory depth > 10k, report the number and wait.
```

```
STEP S3 of 6 — W6 (PNG of the same frozen screen to USB, by SCPI)
DO:      Run (one line):
           python3 -c "import sys; sys.path.insert(0,'tools/lab'); from vendor.scpi import ScpiClient as C; c=C('192.168.50.2'); c.write(':SAVE:IMAGe:FORMat PNG'); c.write(':SAVE:IMAGe D:/w6img.png'); print(c.query(':SYSTem:ERRor?'))"; date +%FT%T
         Still do not press any scope button.
CHECK:   The screen still shows STOP and the same trace.
CAPTURE: The scope saves w6img<digit>.png to the stick.
REPORT:  1. Output, verbatim (an error line and a date/time): ___
         2. Anything the scope showed on screen while saving: ___
STOP IF: the error line is not 0,"No error", or the screen no longer shows STOP → report and wait.
```

```
STEP S4 of 6 — W6 (menu memory CSV of the same frozen trace)
DO:      Open Storage: the lower-left function navigation icon, or the toolbar Storage button.
         Select the Save tab. Under Choose, select "Save wave".
         Set DATA SOURCE to MEMORY. Set FORMAT to *.csv.
         Set File Name to w6mem. Press Save.
CHECK:   The screen still shows STOP before and after the save.
CAPTURE: The scope saves w6mem<digit>.csv to the stick.
REPORT:  1. The file name the scope shows after saving: ___
         2. Any label you saw that differs from the ones above (Storage, Save, Choose, "Save wave", DATA SOURCE, MEMORY, FORMAT, *.csv, File Name, Save): ___
         3. Anything you noticed that wasn't asked for, described as what you see, not why
STOP IF: the scope left STOP at any point (the trace changed) → report and wait; S2–S4 must be redone.
```

```
STEP S5 of 6 — W6 (USB ingest)
DO:      Press RUN/STOP so the scope runs again. Remove the stick and plug it into the Mac.
         Run, putting the date/time from S3 REPORT 1 after --at:
           python3 tools/lab/ingest_usb.py --src /Volumes/HANTEK --test V7R-999 --arm A1usb --at <S3 date/time> --files w6img.png w6mem.csv
         Leave the stick in the Mac.
CHECK:   The output ends with a "captures: [...]" line naming two files.
CAPTURE: The tool copies the stick to lab/inbox/ and renames the two files into lab/captures/V7R-999/.
REPORT:  1. The full output, verbatim: ___
STOP IF: the output says "ambiguous" or "nothing renamed" → paste it and wait. The stick is not modified either way.
```

```
STEP S6 of 6 — W6 (validator on the generated entry)
DO:      Run:
           python3 tools/lab/validate_log.py lab/inbox/w6/*_s01.yaml; echo "exit $?"
CHECK:   The command prints a result line and "exit <n>".
CAPTURE: Nothing.
REPORT:  1. The full output, verbatim: ___
STOP IF: nothing — report either way.
```

Expected for the Worker (not shown to the operator): S6 gives `PENDING (TODOs)`, exit 3, and no `ERROR` lines. The tool CSV should equal the `w6mem` values 10 000 / 10 000.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 9 | Phase 7: Capture, ingest, validation (tasks 1–3) | PARTIAL (planned) | Yes — planned stop; two user decisions open (backup destination, TODO-warn hook policy) | bbe6022 | capture.py + vendored ScpiClient, validate_log.py + hook rule 4, ingest_usb.py; 48 checks pass |

#### Verification
- Commits `04a124d`, `f0c781e`, `2d48cee` and `bbe6022`; the tree is clean. Tasks 1–3 are ticked, and the W6 wording in TASKS is aligned to PLAN. No date-stamped headings.
- Re-derived checks:
  - `run_tests.py` passes (`OK: 0 failure(s)`).
  - The vendored body hashes to `9fface90…5066`, matching upstream @ f9ac719. The MIT licence and attribution are present. PyYAML 6.0.1 is on python3 3.7.3. `capture.py --help` runs.
- Caveat on "the template validates clean": `validate_log.py lab/templates/log.yaml` exits **1** at the CLI because of the session_id/filename rule. A copy named `2026-11-04_s01.yaml` validates OK. The test checks errors other than the filename. This is harmless (the hook only checks `lab/log/*.yaml`), but the claim was overstated.
- [ORCH] Evaluating: resolvable without replanning? Yes, for W6, which is relayed now. Task 4 is waiting on the user's backup-destination answer. Anything other than Google Drive changes a BRIEF line, so the Planner is engaged when the answer arrives.
- The user is asked to confirm the pre-commit policy: errors block, TODOs only warn.
- W6 relay adjustments to the Worker's script:
  - S1 replaces the panel setup with AUTO, a CH1 probe-ratio readback, and CH2 turned off. CH2 was left displayed in S8c, and capture.py measures every displayed channel.

---

### W6 — Phase 7 bench relay (Orchestrator)
Relaying Worker #9's W6 script (S1 adjusted as noted above), one step at a time. REPORTs are verbatim.

**User decisions (verbatim, 2026-10-20):**
> 1. A - icloud folder
> 2. sounds good

- Backup destination: **iCloud Drive** (option A). `~/Library/Mobile Documents/com~apple~CloudDocs` exists on this Mac (Desktop and Documents already sync). The default subfolder is `motion-play-lab/`, kept as one config value. This changes the BRIEF line "Google Drive backup for gitignored captures" → Planner.
- Pre-commit policy confirmed: errors block, TODOs warn.

**S1 REPORT (user, verbatim):**
> 1. "10"
> 2. All yes

Orchestrator notes on S1: CH1 is at 10X, the scope is running, CH1 only, and the stick is present. All CHECKs pass.

**Planner (backup replan):** REPLANNED `30f5058`. BRIEF L15, PLAN (tree comments, backup bullet, Open Question history) and TASKS Phase 7 task 4 now name iCloud Drive at `~/Library/Mobile Documents/com~apple~CloudDocs/motion-play-lab/`; the `.gitignore` comment was updated too. RELAY-orchestrator.md and older SESSION entries are left as historical records. Verified with `git show --stat`; the tree is clean.

**S2 REPORT (user, verbatim):**
> The capture script failed, here's what the terminal showed:
> ```
> Could not connect to scope at 192.168.50.2:5555 — [Errno 65] No route to host
> Could not connect to scope at 192.168.50.2:5555 — [Errno 65] No route to host
> capture: scope error: Could not connect to the oscilloscope (address and underlying error are in the server log). Check that RIGOL_HOST is correct, the scope is on the network, and LAN control is enabled.. Nothing was written.
> ```

Orchestrator notes on S2 (diagnosed from the Orchestrator's shell; TCP connect only, no SCPI sent):
- The link is healthy: en7 is active at 192.168.50.1/24, the route to 192.168.50.2 is via en7, ping gets 2/2 at about 1.1 ms, `nc -z` to port 5555 succeeds, and a plain Python 3.7.3 (pyenv) `socket.create_connection` to :5555 succeeds **from the Orchestrator's shell**.
- From the user's terminal, `nc` worked in S1, but Python fails with EHOSTUNREACH. On macOS 26.6.2 this fits **Local Network privacy**. Apple system binaries such as `/usr/bin/nc` are exempt; a third-party binary (the pyenv python) launched from a terminal app is attributed to that app, and it is refused if the app lacks Local Network permission. This is the leading hypothesis and has not been confirmed.
- The tool behaved correctly: one retry, then "Nothing was written". Its error text comes from the vendored client and mentions "server log" and `RIGOL_HOST`, which don't apply to capture.py (it uses `--host`/`$DHO_HOST`). The next Worker should wrap that message. This is a cosmetic issue.
- Inserting S2a: check the Local Network toggle for the user's terminal app, then re-run S2 unchanged. The trace is still RUN, since nothing reached the scope.

**S2a REPORT (user, verbatim):**
> Ok I think it worked. I toggled "Cursor" off and on again
> The output was:
> ```
> capture: V7R-999 A1, DHO804, fw 00.01.05, memory 10000 pts, channels CH1
>   wrote /Users/marcocleirigh/Workspace/motion-play/lab/captures/V7R-999/2026-10-20_V7R-999_A1_01.png
>   wrote /Users/marcocleirigh/Workspace/motion-play/lab/captures/V7R-999/2026-10-20_V7R-999_A1_01.csv
>   wrote /Users/marcocleirigh/Workspace/motion-play/lab/captures/V7R-999/2026-10-20_V7R-999_A1_01.setup.bin
>   log   /Users/marcocleirigh/Workspace/motion-play/lab/inbox/w6/2026-10-20_s01.yaml (measurement appended; fill feature, raw_observation and any other TODO)
>   NOTE: 1 measurement(s) invalid (9.9E37 or no reply): VPP CH1
>   The scope is left STOPPED.
> ```

Orchestrator notes on S2a:
- **Cause confirmed: macOS Local Network privacy for Cursor.** Toggling Cursor off and on in Privacy & Security → Local Network fixed it. Phase 8 procedures need a one-time setup line: "allow your terminal app under Local Network; `nc` working does not prove Python will".
- Files, checked by listing: PNG 109 506 B, CSV 305 013 B, setup.bin 2 883 B, all in `lab/captures/V7R-999/`.
- The log has VAMP CH1 = 3003.7 mV, which matches S3's 3.0037 V. **VPP CH1 is recorded as `valid: false` (9.9E37)**, so the tool handled it correctly. VPP on CH2 was valid in S8c, though, so why VPP is invalid here is unknown. The next Worker should look at the frozen CSV: clipping at the top or bottom of the screen after AUTO is one possibility.
- The trace is frozen (STOPPED). Next is S3.

**S3 REPORT (user, verbatim):**
> 1. 0,"No error"
> 2026-10-20T11:43:04
>
> 2. It showed something like "Saving to D:/w6img.png"

Orchestrator notes on S3: no error, and the scope showed a save message. The Mac time is 2026-10-20T11:43:04, which is the `--at` value for S5. Whether the file was written gets checked in S5; `:SAVE:IMAGe` was bench-verified in S6/S7. Next is S4.

**S4 REPORT (user, verbatim):**
> 1. Yes, it showed w6mem0.csv
> 2. No

Orchestrator notes on S4: the trace stayed frozen from S2 through S4, so the tool files, `w6img*.png` and `w6mem0.csv` all come from one acquisition. Next is S5.

**S5 REPORT (user, verbatim):**
> ```
> ingest: 39 stick file(s), 39 new copied to /Users/marcocleirigh/Workspace/motion-play/lab/inbox/usb-20261020-115051
>   wrote /Users/marcocleirigh/Workspace/motion-play/lab/captures/V7R-999/2026-10-20_V7R-999_A1usb_01.png <- w6img0.png (stick 2026-10-20T11:43:04, offset +0 min)
>   wrote /Users/marcocleirigh/Workspace/motion-play/lab/captures/V7R-999/2026-10-20_V7R-999_A1usb_01.csv <- w6mem0.csv (stick 2026-10-20T11:45:56, offset +0 min)
>   captures: [2026-10-20_V7R-999_A1usb_01.png, 2026-10-20_V7R-999_A1usb_01.csv]
> ```

Orchestrator notes on S5:
- Ingest matched both files and renamed them per §4.4. **The stick timestamps matched the Mac at offset +0**: `w6img0.png` at 11:43:04 is exactly the S3 Mac time. Worker #7's "about 1 h ahead" observation is not reproduced. Its cause is unknown; one possibility is how the earlier listing rendered times. Ingest still tries +60, which does no harm. Phase 8 should not state an offset.
- All 39 stick files were copied into the inbox, including the old ones and system folders. That is acceptable, since the inbox is gitignored and backed up.
- Next is S6.

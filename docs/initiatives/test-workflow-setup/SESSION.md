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

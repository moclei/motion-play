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

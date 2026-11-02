# Session Log — Lab — Multiple Investigations

## 2026-11-02 — orchestration run 1

Entry: started from `RELAY-orchestrator.md`. Branch `feat/lab-multi-investigation` cut from `main` at `51afcf2`. PLAN Open Questions: none blocking. Relay states `run_tests.py` OK and `check_state.py` OK (0 warnings); Worker #1 records the actual baseline.

---

### Worker #1 — Phase 1: Registry, IDs, checker, hook

**Dispatch:** standard spawn prompt, Phase 1 task list. Additional reading: `tools/CONTEXT.md` § Lab Tools; `docs/research/v7-retry/context-strategy.md` §4.1, §4.2, §6 (section-scoped). Branch: `feat/lab-multi-investigation` (already cut; commit there).

**Baseline (before any Phase 1 change, HEAD `e67cb0c`, Python 3.7.3 with PyYAML):**
- `run_tests.py`: 86 PASS, 0 FAIL, `OK: 0 failure(s)`. The 9 checker fixtures each fire their one tag (`clean` nothing; `stale` exits 1).
- `check_state.py` (real lab): `as_of=V7R-020  last_checkpoint=V7R-019  cards=20`, `RESULT: OK (0 warnings)`, exit 0.
- `check_state.py --load`: same header, then open cards `(none)`; last two recorded `V7R-019` (prereg self = 8993678, result self = 4256a78) and `V7R-020` (prereg self = 3efc253, result self = 45240c9); today's log `(none for 2026-11-02)`. Exit 0.

**Fixtures (run_tests.py):** new `multi` (STALE, exit 1, grouped under `power` only), `closed` (CLOSED-OPEN), `dup_prefix` (DUP-PREFIX, exit 1), `no_prefix` (NO-PREFIX, exit 1), `orphan_card` (ORPHAN-CARD), plus `no_bench` (BENCH), not in the task list but the BENCH warning needed a fixture of its own. Each fires exactly its one tag. Extra checks on `multi`: `--inv v7-i2c` skips power (no findings, exit 0); `--load` without `--inv` exits 2; `--load --inv power` loads PWR-001; unknown `--inv` exits 2; `clean --load` needs no `--inv`. Every existing fixture got a `lab/BENCH.md` so the new warning does not fire there. Result: 98 PASS (86 baseline + 6 fixtures + 6 multi checks), `OK: 0 failure(s)`.

**Hook acceptance (throwaway clone of the branch, `core.hooksPath .githooks`, deleted afterwards):**
- A1 real lab, v7 STATE without prefix (fallback): V7R-021 recorded, STATE not staged → REJECTED ("lab/investigations/v7-i2c/STATE.md is not staged … as_of: V7R-021").
- A2 same, v7 STATE staged with as_of V7R-021 → ACCEPTED.
- B0 v7 STATE given `prefix: V7R` (as Phase 3 will), `power/STATE.md` with `prefix: PWR` added → ACCEPTED.
- B1 PWR-001 recorded, no STATE staged → REJECTED ("lab/investigations/power/STATE.md is not staged … as_of: PWR-001").
- B2 PWR-001 recorded with the *v7* STATE staged → REJECTED (same message: power STATE not staged).
- B3 PWR-001 recorded with power STATE as_of PWR-001 → ACCEPTED (also shows V7R-001 and PWR-001 coexist: rule 3 is per prefix).
- B4 a second PWR-001 card → REJECTED ("duplicate ID PWR-001, also used by lab/cards/PWR-001-accept.md").
- B5 ZZZ-001 recorded, no investigation declares ZZZ → REJECTED ("no investigation declares prefix ZZZ").
- Checker on the clone afterwards: two groups (power, v7-i2c), BENCH warning, and `[CAP] STATE is 153 lines (cap ~150)` for v7, caused by the 3 front-matter lines (see Notes).

**After Phase 1 (real lab):**
- `run_tests.py`: 98 PASS, `OK: 0 failure(s)`.
- `check_state.py`: exit 0, `RESULT: OK (1 warning)`. Differences from baseline: (1) the expected `[BENCH] lab/BENCH.md missing` warning; (2) the output format is now grouped: a registry header (`investigations: 1 open (v7-i2c V7R), 0 closed  cards=20`), then `== v7-i2c (V7R, open): v7-i2c  as_of=V7R-020  last_checkpoint=V7R-019  cards=20` with no findings (title shows the folder name until Phase 3 adds `title`); (3) an `info:` line naming the Phase 1 V7R fallback. No other finding.
- `check_state.py --load`: exit 0; after the header it prints `=== LOAD: investigation v7-i2c (V7R) ===` and then the load identical to baseline (diffed: open cards none, V7R-019 and V7R-020 with the same resolved `self` hashes, no log today).

#### Notes
- Commits: `3bc99a2` baseline, `145bacd` lablib, `d30259e` fixture keys, `6c70341` checker, `2c9eca0` hook, `f00fc23` fixtures + acceptance, then the handoff commit.
- **Phase 3 watch-out (CAP):** the real v7 STATE is exactly 150 lines. Adding `prefix`/`title`/`status` makes it 153 and the checker then warns `[CAP] STATE is 153 lines (cap ~150)` (seen in the acceptance clone). The §6 move to BENCH.md should take it back under; check before W1, since W1 expects baseline results.
- **Fallback scope:** the V7R fallback is in `lablib.build_registry` (search `LEGACY_PREFIX` / "Phase 1 fallback"), used by both checker and hook. It holds only while v7 is the only investigation; Phase 2's scaffold tests must use fixture roots, never the real lab, or v7 loses its prefix until Phase 3. Remove in Phase 3: the `build_registry` branch, the checker's `prefix_fallback` info line, the docstring line, and the default `prefix=LEGACY_PREFIX` on `id_num`/`fmt_id` once Phase 2 tools pass prefixes explicitly.
- Added a `no_bench` fixture beyond the task list so the BENCH warning has its own exactly-once test. Added `CLOSED-OPEN` as the closed-investigation tag (PLAN didn't name one); PLAN Technical Notes updated with the tags and hook behaviour.
- `capture.py`, `ingest_usb.py`, `validate_log.py` still have their own `V7R` regexes (Phase 2). They don't import the changed lablib names.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 1 | Phase 1: Registry, IDs, checker, hook | DONE | No — clean completion | 8f57774 | 6 tasks + handoff; 7 commits after baseline |

#### Verification
- Working tree clean; Phase 1 all `[x]`, Phases 2–3 untouched `[ ]`. PLAN.md: no date-stamped headings. No changes under `lab/`.
- Re-ran `run_tests.py`: `OK: 0 failure(s)`. Re-ran `check_state.py` on the real lab: exit 0, `RESULT: OK (1 warning)` — the warning is the expected `[BENCH]`; the fallback shows as an `info:` line, not a finding.
- Beyond the task list, accepted as within PLAN: `CLOSED-OPEN` emitted as a warning (PLAN left the level open); extra `no_bench` fixture; Worker added three as-built bullets to PLAN Technical Notes (no change of approach).
- Carries forward to Phase 3: adding the 3 front-matter keys to the 150-line v7 STATE trips `[CAP]` unless the §6 move lands in the same diff — check before W1. Fallback removal points: `lablib.build_registry` `LEGACY_PREFIX`, the checker's info line + docstring, the `V7R` default on `id_num`/`fmt_id`.
- Carries forward to Phase 2: scaffold tests must run in fixture roots, never the real lab (a second investigation there would turn v7 into `NO-PREFIX` while the fallback is live).

---

### Worker #2 — Phase 2: Other tools, templates, scaffold

**Dispatch:** standard spawn prompt, Phase 2 task list. Additional reading: `#### Notes` of Worker #1 above; `tools/CONTEXT.md` § Lab Tools; `docs/research/v7-retry/context-strategy.md` §4.1 (STATE skeleton for the template). Phase notes: tools should pass prefixes explicitly so the `V7R` default on `id_num`/`fmt_id` can go in Phase 3; scaffold tests in fixture roots only.

**Before (HEAD `c80bb24`):** `run_tests.py` 98 PASS, `OK: 0 failure(s)`. `check_state.py` (real lab) as at the end of Phase 1: exit 0, `RESULT: OK (1 warning)` (`[BENCH]`), fallback `info:` line.

**After Phase 2:** `run_tests.py` 123 PASS (98 + 25 new), `OK: 0 failure(s)`. `check_state.py` on the real lab: unchanged from before (exit 0, `RESULT: OK (1 warning)`, only `[BENCH]`, same `info:` line, `== v7-i2c (V7R, open) … as_of=V7R-020 last_checkpoint=V7R-019 cards=20`). `--load`: unchanged (open cards none, V7R-019/V7R-020 conclusions, no log today). `validate_log.py lab/log/*.yaml`: 2026-10-20_s01 PENDING (TODOs, as before), the rest OK. Nothing under `lab/` changed except `lab/templates/`.

#### Notes
- Commits: `f2cdd8f` tools (capture, ingest, validate_log, + rule 4), `1518b3b` templates, `b48ea8b` scaffold, `2e05970` CONTEXT, then the handoff commit.
- **ID check:** new `lablib.check_id(id, known)` + `lablib.registered_prefixes(lab_root)` + `lablib.ID_HELP`. `check_id` calls `id_num(card_id, prefix)` with the prefix explicitly, so no Phase 2 tool relies on the `V7R` default of `id_num`/`fmt_id`. The only `fmt_id`/`id_num` callers (`check_state.py`, `precommit.py`, `next_id`) already pass a prefix; Phase 3 can drop the `prefix=LEGACY_PREFIX` defaults.
- capture/ingest check `--test` against `<--root>/lab` before contacting the scope / copying anything (exit 2). They accept a prefix of a *closed* investigation too (PLAN says "registered"); flagging that is not done.
- **validate_log:** `validate(data, stem, prefixes=None)`; `None` = shape check only (used by direct callers that pass none, e.g. the template test). The CLI reads the registry from `--root <repo>` (default this repo). **precommit rule 4 now passes the staged registry's prefixes** (a small change to `precommit.py` beyond the three named tools, needed so the hook enforces the same rule); its docstring updated.
- Tool tests: `seed_registry()` writes a front-matter-only STATE in each temp root (capture/ingest/hook roots had no registry before; "nothing written" checks now ignore `lab/investigations/`).
- **Scaffold:** `--root` is the lab dir (as `check_state.py`), `--templates` defaults to the repo's `lab/templates/`. Title is written quoted in front matter (a `: ` in a title would otherwise break YAML). Beyond PLAN it also refuses: a prefix used only by card files, and any existing investigation with no `prefix` — this is the guard that keeps a scaffold on the real lab from turning v7 into `NO-PREFIX` while the fallback is live. It checks `inv.prefix is None or inv.prefix_fallback`; when Phase 3 removes the fallback, drop the `prefix_fallback` half.
- Templates: `lab/templates/STATE.md` substitutes `<PREFIX>`, `<TITLE>`, `<NAME>`, `<YYYY-MM-DD>`; other `<...>` stay as fill-in placeholders. Its §6 is baselines + the BENCH.md pointer; §9 has two generic rows. `card.md` fixed a wrong example log name (`2026-11-04_session-01.yaml` → `_s01`) and gained a rule-1 line. `log.yaml` got a comment on `test_id` only (values unchanged, still validates).
- `tools/CONTEXT.md` describes `lab/BENCH.md` as existing; it is created in Phase 3 (the checker warns until then). The fallback is not mentioned there, since it is transitional.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 2 | Phase 2: Other tools, templates, scaffold | DONE | No — clean completion | cf7e167 | 4 tasks + handoff |

#### Verification
- Worker #2 wrote the `#### Result` table itself (Orchestrator-owned); kept, with the commit filled in. Its Before/After lines sit above its Notes — left as written.
- Working tree clean; Phase 2 all `[x]`, Phase 3 untouched. PLAN.md: one as-built bullet, no date-stamped headings. Under `lab/`, only `lab/templates/` changed (in scope per BRIEF).
- Re-ran `run_tests.py`: `OK: 0 failure(s)`. Re-ran `check_state.py` on the real lab: exit 0, `RESULT: OK (1 warning)` (`[BENCH]`), fallback `info:` line — unchanged from Phase 1.
- Beyond the task list, accepted: hook rule 4 passes registered prefixes to `validate_log` (keeps hook and tool consistent); the scaffold's two extra refusals.
- Carries forward to Phase 3: fallback removal also covers the `prefix_fallback` half of `new_investigation.refusals()`. capture/ingest accept a closed investigation's prefix — noted, not in scope; surfaced to the user at closeout.
- Phase 3 dispatch shape: the Worker cannot reach the user, and removing the fallback before the v7 STATE has `prefix` makes the real lab `NO-PREFIX`. So Worker #3 merges `main`, checks `open_cards`, and prepares the W1 (STATE + BENCH.md + fallback removal), PROTOCOL and W2 diffs as patches without applying them, then returns. The Orchestrator puts them to the user; a later Worker applies what is approved, runs the end-to-end check and opens the PR.

---

### Worker #3 — Phase 3 (part 1): merge main, draft the approval diffs

**Dispatch:** Phase 3 tasks 1–2 plus drafting for W1, the PROTOCOL task and W2. Diffs are saved as patches in the session scratchpad, not applied to the branch (except the `main` merge). Additional reading: Worker #1 and #2 `#### Notes` and Verification; `lab/investigations/v7-i2c/STATE.md`; PROTOCOL § lab/; `docs/research/v7-retry/debugger-role-draft.md`.

**Task 1:** `git merge origin/main` → "Already up to date". No Debugger branch named, none merged. v7 STATE `open_cards: []`. Ticked, commit `35eedf7`.

#### Notes
- **Patches (not applied; each passes `git apply --check` on this branch tip; they touch disjoint files):**
  - `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/802b00cc-75aa-4bf6-a96c-438f5728422f/scratchpad/phase3/w1.patch` — W1 + task 2: new `lab/BENCH.md`; v7 STATE front matter (`prefix: V7R`, `title: "v7 I²C fault"`, `status: open`) and §6 reduced; fallback removal in `lablib.py` (`LEGACY_PREFIX`, the `build_registry` branch, `prefix_fallback` attribute, `V7R` default on `id_num`/`fmt_id`, now required), `check_state.py` (info line + docstring), `new_investigation.py` (`prefix_fallback` half of the refusal), and one stale test comment in `tool_tests.py`. No fixture changes needed.
  - `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/802b00cc-75aa-4bf6-a96c-438f5728422f/scratchpad/phase3/protocol.patch` — PROTOCOL § lab/ paragraph rewritten (folder per investigation, front-matter registry, scaffold command, one investigation per session via `--inv`, shared files, BENCH.md and its same-commit rule).
  - `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/802b00cc-75aa-4bf6-a96c-438f5728422f/scratchpad/phase3/w2.patch` — role draft: description and ownership generalised; start of session = checker lists open investigations → user picks → `--load --inv <name>` → read STATE + BENCH.md; new "New investigation (relay intake)" section (scaffold, fill §1–8, BENCH.md boards, one commit); `<PREFIX>-NNN` in lifecycle and commit messages; BENCH.md updated in the same commit as a card that changes boards/fixtures/flashing, and at the notebook stop; BENCH.md in the context-pressure handoff and outside-review prompts; auto-memory rule covers any investigation.
- **Scratch-copy results with w1.patch applied (detached worktree of `35eedf7`, removed afterwards):**
  - `run_tests.py`: 123 PASS, `OK: 0 failure(s)` (same count as end of Phase 2). Before the STATE edit, with only the code half applied, 3 `validate_log` pass-fixture tests failed ("no investigation declares prefix V7R"): they read the real-lab registry, so the code and STATE halves of w1 must land together.
  - `check_state.py --memory-dir <real memory dir>` on the real-lab copy: `investigations: 1 open (v7-i2c V7R), 0 closed  cards=20`, `== v7-i2c (V7R, open): v7 I²C fault  as_of=V7R-020  last_checkpoint=V7R-019  cards=20`, no findings, `RESULT: OK (0 warnings)`, exit 0. The `[BENCH]` warning and the fallback `info:` line are gone; no `[CAP]`. Matches the baseline (0 warnings).
  - `check_state.py --load`: exit 0; open cards none; V7R-019 (prereg 8993678, result 4256a78) and V7R-020 (prereg 3efc253, result 45240c9); no log today — same as baseline.
  - `validate_log.py lab/log/*.yaml`: 2026-10-20_s01 PENDING (TODOs, as before), the rest OK.
- **CAP:** the STATE is exactly 150 lines after w1 (cap warns at > 150). To get there, §6's field-definition line and the BENCH.md pointer are one line (template has them as two), so §6 is heading + definition/pointer + the Baselines bullet. Any future added line in the v7 STATE will trip `[CAP]`. No Lookups row for BENCH.md was added for the same reason.
- **BENCH.md shape:** boards as a table (ID | Condition | Mods | Role | Investigations), cells verbatim from the old §6 `Boards:` bullet split on its own ` | ` separators (trailing periods kept); the closing "#0004 could be B1, B2 or a spare." is a line under the table. Every board says `v7-i2c` (the only investigation). Fixtures: the fixtures half of the old first bullet (the Baselines half stays in §6), tagged `(v7-i2c)`. Flashed now and Bench at last stop: the old bullets verbatim.
- **For the user:** recorded cards V7R-019/020 cite "STATE §6" for board naming and the bench; those citations now resolve to BENCH.md (historical cards untouched, per BRIEF). Whether #0004 ("power-path case") belongs to the power investigation is the Debugger's call at intake; BENCH.md lists it as v7-i2c only.
- **Next Worker:** apply the approved patches (`git apply <patch>`), tick task 2 with W1, run `run_tests.py` and `check_state.py` again on the real lab, then the end-to-end clone check and the PR.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 3 | Phase 3 (part 1): merge main, draft approval diffs | PARTIAL | Yes — planned stop at W1; resolvable without replanning | 961bf45 | task 1 done; w1/protocol/w2 patches drafted, not applied |

#### Verification
- Working tree clean; only TASKS.md (task 1) and SESSION.md changed on the branch. `open_cards: []` confirmed by the Worker.
- All three patches pass `git apply --check` on 961bf45 and touch disjoint files. Read the `lab/` half of w1: §6 content appears in BENCH.md (boards split into table cells on the original ` | ` separators; fixtures, flashed-now and bench-at-last-stop lines unchanged); STATE gains the three keys; §6 keeps heading, cap and baselines. Read protocol.patch: one paragraph rewritten.
- Not re-run here (the Worker ran it in a scratch worktree): tests 123 PASS and real-lab checker `RESULT: OK (0 warnings)` with w1 applied. The next Worker re-runs both on the branch after applying.
- For the user: w1 must be applied whole (the code half alone fails 3 tests); the v7 STATE sits at exactly the 150-line cap; #0004 is tagged `v7-i2c` pending the power intake.

**User decisions (2026-11-02):** W1 approved as drafted (w1.patch). PROTOCOL § lab/ approved as drafted (protocol.patch). W2: user asked for w2.patch to be applied on the branch.

---

### Worker #4 — Phase 3 (part 2): apply approved patches, end-to-end check, PR

**Dispatch:** Phase 3 remaining tasks. Apply w1, protocol and w2 patches unchanged (all approved), re-verify on the branch, run the end-to-end check, open the PR (W3). Additional reading: Worker #3 `#### Notes` and the Verification under it.

**Patches applied (each `git apply --check` clean, applied unchanged):** w1 → `8de323e` (tasks 2 + W1 ticked), protocol → `03f3866`, w2 → `17ca761`.

**After W1, on the branch (real lab):** `run_tests.py` `OK: 0 failure(s)`. `check_state.py`: `investigations: 1 open (v7-i2c V7R), 0 closed  cards=20`, `== v7-i2c (V7R, open): v7 I²C fault  as_of=V7R-020  last_checkpoint=V7R-019  cards=20`, no findings, `RESULT: OK (0 warnings)`, exit 0. No `[CAP]`, no `[BENCH]`, no fallback `info:` line. v7 STATE is 150 lines. `--load`: exit 0; open cards none; V7R-019 (prereg 8993678, result 4256a78), V7R-020 (prereg 3efc253, result 45240c9); no log today. Same as baseline.

**End-to-end check (throwaway clone of `17ca761`, `core.hooksPath .githooks`, deleted afterwards):**
- E0 `new_investigation.py --name power --prefix PWR --title "Battery and power path"` → exit 0, wrote STATE + NOTEBOOK. A second scaffold with prefix PWR → REFUSED exit 2; name `power` again → REFUSED exit 2. Checker: `2 open (power PWR, v7-i2c V7R)`, power `as_of=PWR-000 cards=0`, `RESULT: OK (0 warnings)`. Commit ACCEPTED.
- E1 dummy `PWR-001` card from `lab/templates/card.md` (status pre-registered) + power STATE `open_cards: [PWR-001]` → ACCEPTED. Checker OK (0 warnings), power `cards=1`. `--load` without `--inv` → exit 2 ("--load needs --inv <name> when 2 investigations are open"). `--load --inv power` lists PWR-001 as open, prereg self resolved.
- E2 PWR-001 → `status: recorded` (Result commit self, Conclusion cites `lab/evidence/PWR-001/`): no STATE staged → REJECTED (power STATE not staged); only the *v7* STATE staged → REJECTED (same message); power STATE with `as_of: PWR-000` → REJECTED ("expected PWR-001"); power STATE `as_of: PWR-001`, `open_cards: []` → ACCEPTED (warning only: evidence dir has no files in the index). Checker: power `as_of=PWR-001`, `RESULT: OK (0 warnings)`; `--inv power` OK; `--load --inv power` shows PWR-001 recorded with both `self` hashes resolved.
- E3 a second `PWR-001` card → REJECTED ("duplicate ID PWR-001, also used by lab/cards/PWR-001-dummy.md"). `lablib.next_id(lab, 'PWR')` → PWR-002. V7R and PWR cards coexist (cards=21).
- The checker's default memory dir is derived from the clone path, so the MEMORY check was skipped there; re-run with `--memory-dir` set to the real memory dir: `RESULT: OK (0 warnings)`.

**W3:** branch pushed; PR https://github.com/moclei/motion-play/pull/89 opened to `main` (not merged; the user merges). `origin/main` had no new commits since the Phase 3 merge, so the PR has no conflicts.

#### Notes
- Commits: `8de323e` w1 (BENCH.md, v7 STATE, fallback removal; tasks 2 + W1), `03f3866` PROTOCOL § lab/, `17ca761` w2 role draft, `0b2fa60` e2e log, then this handoff commit. All three patches applied unchanged.
- Real lab on the branch after W1: `run_tests.py` OK (0 failures); `check_state.py` `RESULT: OK (0 warnings)`, no `[CAP]`; `--load` identical to baseline. The v7 STATE is at exactly 150 lines, so any added line will trigger `[CAP]`.
- End-to-end check passed (details above). Two things showed up only in the dummy run: (1) the hook prints a *warning* (not a rejection) when a recorded card cites `lab/evidence/<ID>/` but no evidence files are staged. This is expected. (2) The checker's default memory dir is derived from the repo path, so in a clone at another path the MEMORY check is skipped with an `info:` line. Pass `--memory-dir` there.
- The user still needs to hear that `v8-debug-board` Phase 2's power relay can now run as `PWR` cards. The Orchestrator relays this. The first Debugger session for it runs `tools/lab/new_investigation.py --name power --prefix PWR --title "..."` at intake.
- PR: https://github.com/moclei/motion-play/pull/89

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 4 | Phase 3 (part 2): apply approved patches, e2e, PR | DONE | No — clean completion | 1498ef9 | w1/protocol/w2 applied unchanged; e2e logged; PR #89 open |

#### Verification
- Working tree clean, branch in sync with origin. TASKS.md: no `[ ]` or `[~]` left. PLAN.md: no date-stamped headings.
- Re-ran on the branch: `run_tests.py` `OK: 0 failure(s)`; real-lab `check_state.py` `RESULT: OK (0 warnings)` — baseline result, `[BENCH]` and fallback line gone. v7 STATE is 150 lines (at cap). Only `v7-i2c` exists under `lab/investigations/` (the e2e ran in a deleted clone).
- PR #89: OPEN, `main` ← `feat/lab-multi-investigation`, MERGEABLE.

---

**Outcome:** Loop complete — 4 workers dispatched, 1 orchestration run, 0 unresolved blockers. Awaiting W3 (user merges PR #89).

Parked for a cross-initiative home (no `docs/initiatives/MASTER.md` exists; user asked where these go):
- To `v8-debug-board`: its Phase 2 power relay (`debugger/RELAY-power.md`) can run as `PWR` cards once PR #89 is merged. The Debugger scaffolds at intake: `python3 tools/lab/new_investigation.py --name power --prefix PWR --title "<title>"`, then decides whether board #0004 also belongs to `power` in `lab/BENCH.md`.
- Follow-ups (out of scope here): capture/ingest accept a closed investigation's prefix; v7 STATE sits at its 150-line cap; recorded cards V7R-019/020 cite "STATE §6" for content now in `lab/BENCH.md`; the hook does not enforce the BENCH.md same-commit rule (PLAN Open Question); the checker skips MEMORY from a clone at another path unless `--memory-dir` is given.

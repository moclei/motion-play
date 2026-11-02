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

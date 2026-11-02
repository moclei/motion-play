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

**Fixtures (run_tests.py):** new `multi` (STALE, exit 1, grouped under `power` only), `closed` (CLOSED-OPEN), `dup_prefix` (DUP-PREFIX, exit 1), `no_prefix` (NO-PREFIX, exit 1), `orphan_card` (ORPHAN-CARD), plus `no_bench` (BENCH), not in the task list but the BENCH warning needed a fixture of its own. Each fires exactly its one tag. Extra checks on `multi`: `--inv v7-i2c` skips power (no findings, exit 0); `--load` without `--inv` exits 2; `--load --inv power` loads PWR-001; unknown `--inv` exits 2; `clean --load` needs no `--inv`. Every existing fixture got a `lab/BENCH.md` so the new warning does not fire there. Result: 107 PASS, `OK: 0 failure(s)`.

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

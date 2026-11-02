# Session Log — v8-debug-board

## 2026-11-02 — orchestration run 1

Entry conditions: started from `RELAY-orchestrator.md`. `lab-multi-investigation` is merged (PR #89, `36ab0ad`). Branch `feat/v8-debug-board` was cut from `main` at `5acec69`. PLAN Open Questions OQ-1 to OQ-5 are still open, and each is assigned to a later phase (OQ-2/4/5 to Phase 3, OQ-3 to Phase 13, OQ-1 to Phase 16), so none gates Phase 1. Gate rule from the relay: Phases 1–6 run without a user gate except W2 (end of Phases 3–4). Phase 7 stops on W1 if the bench findings haven't landed.

---

### Worker #1 — Phase 1: Power path — v7 trace and BQ root cause (desk)

**Dispatch:** standard spawn prompt, plus:
- Additional reading: `tools/CONTEXT.md` (Critical Rule, Source-Hash Rule); PLAN Technical Notes "Sources to load per task" (the subset relevant to the power path: CL-IDs in `docs/research/v7-retry/v6-v7-changelist.md`, `docs/references/{bq24195,tps61088}/DATASHEET_REFERENCE.md`, `hardware/CONTEXT.md`, `firmware/src/main.cpp` `configureBQ24195()`).
- Scratch extraction output stays outside the repo. `lab/` is read-only.

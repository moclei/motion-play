# Relay-planner — orchestrator — 2026-11-02

role:orchestrator

## Context
`v8-debug-board` needs bench work on a second fault (battery/power), but `lab/` and `tools/lab/` assume a single investigation (`V7R-`). The user agreed a layout, `lab/investigations/<name>/{STATE.md,NOTEBOOK.md}`, and the v7 files have already moved there (`980caa0`, paths only). This initiative makes the tools handle many investigations, adds a scaffold, and moves boards and bench state into a shared `lab/BENCH.md` (the user's choice).

## Load these files
- .context/PROTOCOL.md
- docs/initiatives/lab-multi-investigation/ (BRIEF, PLAN, TASKS)
- tools/CONTEXT.md § Lab Tools
- docs/research/v7-retry/context-strategy.md §4.1, §4.2, §6 (section-scoped)

## State
Branch: the docs are on `plan/v8-debug-board`, which contains all of `debug/v7-track-4` (`980caa0`). Cut `feat/lab-multi-investigation` from `plan/v8-debug-board`. W3 merges it into `debug/v7-track-4`, which also carries the v8 planning commits and the PROTOCOL relay edits there. The user knows this.
Build: `run_tests.py` OK, `check_state.py` OK (0 warnings) at `980caa0`
TASKS.md current: yes

## What was done
- User decisions (2026-11-02): one folder per investigation; the folder is the registry (prefix in STATE front matter); a shared `lab/BENCH.md` for boards and bench state; a separate small initiative, not a v8 phase.
- 3 phases. Phases 1–2 are code and tests only. Phase 3 touches `lab/` and needs user approval (W1, W2), then the merge (W3).

## Your task
Run the initiative from Phase 1. It must finish before `v8-debug-board` Phase 2 hands over its power relay. If both initiatives are dispatched, finish this one first.

## Open questions
None blocking. See PLAN Open Questions.

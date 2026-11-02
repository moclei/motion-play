# Relay-planner — orchestrator — 2026-11-02

role:orchestrator

## Context
On 2026-10-31 the user opened a parallel respin track: a v8 main board built as a large, probe-friendly debug board, with v7's configuration jumper-selectable (notebook 2026-10-31 decision; relay `lab/relays/2026-10-31_RELAY-planner-v8-debug-board.md`). The Planner scoped it into this initiative. It also trials AI placement and routing, and builds the board-model tooling for an AI partner review.

## Load these files
- .context/PROTOCOL.md
- docs/initiatives/v8-debug-board/ (BRIEF, PLAN, TASKS)
- lab/relays/2026-10-31_RELAY-planner-v8-debug-board.md (the ask; read-only)
- tools/CONTEXT.md (Critical Rule, Source-Hash Rule)

## State
Branch: everything is on `debug/v7-track-4` (planning branches folded in 2026-11-02). Run `lab-multi-investigation` first; then cut `feat/v8-debug-board` from `debug/v7-track-4` after that initiative has merged back.
Build: n/a (no code yet)
TASKS.md current: yes

## What was done
- User decisions (2026-11-02):
  - Same design split as before, plus tentative AI placement/routing to build a workflow and scripts. The goal is AI placement, with the user reviewing and correcting.
  - Battery investigation: a desk phase here, bench work as Debugger cards.
  - Review: the user reviews, and the scripts are improved so the AI can partner-review.
  - 5 assembled boards.
  - Any part may be swapped.
- Board-model tooling (audit phases 1–2) folded in as Phases 5–6. This absorbs the queued `pcb-board-model` initiative and supersedes `routing-verification`.
- 19 phases. User waits W1 (power bench findings, before Phase 7), W2 (design intent), W3 (schematic), W4–W6 (placement/routing reviews), W7 (pre-order), W-order.

## Your task
Run the initiative from Phase 1. Phases 1–6 have no user gate except W2 at the end of Phases 3–4. Phases 5–6 can run while the Debugger does the Phase 2 bench relay. Phase 7 stops on W1 if the bench findings haven't landed: report it, don't skip ahead past Phase 7. Phases 8+ depend on Phase 7.

## Open questions
See PLAN Open Questions OQ-1 to OQ-8. Each names the phase that needs it.

# Relay — research/ideation → planner — 2026-10-17

role:planner

## Context

A research/ideation session discussed how to approach a retry of the "v7 main PCB" debugging work (previously stalled). The agreed first step, before any retry research or debugging, is to swap this project onto the newer workflow protocol that currently lives in `docs/scratch/`. The current protocol doc (`.context/WORKFLOW.md`) is an older version; `docs/scratch/PROTOCOL.md` plus the agent-role files are the replacements. This initiative is purely the swap — no v7 debugging work, no new content.

## Load these files

The target protocol is not yet installed at `.context/PROTOCOL.md` — read it from its staging location for now:

- `docs/scratch/PROTOCOL.md` — the new protocol, to be installed at `.context/PROTOCOL.md`
- `docs/scratch/planner.md`, `orchestrator.md`, `worker.md`, `bugfix.md`, `gardener.md`, `organizer.md` — role files, to be installed under `.claude/agents/`
- `docs/scratch/PROJECT.md` — **example from a different project; do NOT overwrite motion-play's PROJECT.md with it.** Read only to understand references to PROTOCOL/roles.
- `.context/WORKFLOW.md` — the file this initiative replaces
- `.context/PROJECT.md` — motion-play's real project doc; contains references to `WORKFLOW.md` that need updating (see "What was done")
- `.context/manifest.yaml`, `.context/IDEAS.md` — unclear whether the new protocol has a place for these; see Open Questions
- `.context/motion-play-main/`, `.context/motion-play-sensor/` — unknown; see Open Questions
- `docs/initiatives/` — contains existing BRIEF/PLAN/TASKS initiatives; the swap must not break their structure

This initiative folder (`docs/initiatives/adopt-protocol/`) currently contains only this relay.

## State

Branch: `feat/v7-board-firmware` (unrelated in-flight work; the Orchestrator will cut a fresh `feat/adopt-protocol` branch at run time per protocol)
Build: n/a — docs/config change, no code
TASKS.md current: no — not yet written; this relay exists to kick that off
Note: there are uncommitted changes on the current branch (firmware, mechanical, docs). The Planner should not touch them. The Orchestrator will branch from a clean point when it runs.

## What was done

- Research/ideation session established the overall v7-retry framework (not scoped into this initiative)
- Agreed that adopting the new protocol is a prerequisite and should ship as its own small initiative before any retry research begins
- Confirmed the new protocol/role files are staged in `docs/scratch/`
- Confirmed existing initiatives in `docs/initiatives/` already follow the BRIEF/PLAN/TASKS pattern — the swap should be compatible with them
- Identified concrete references to `WORKFLOW.md` that must be updated in `.context/PROJECT.md`: lines 3, 36, 46, 86
- Confirmed `/Users/marcocleirigh/Workspace/motion-play/CLAUDE.md` does **not** currently exist — the new protocol references a CLAUDE.md but this project doesn't have one; decide whether to create a minimal one or leave it absent
- `docs/scratch/PROJECT.md` is example content from an unrelated project — must not be used to overwrite motion-play's PROJECT.md

## Your task

Write BRIEF.md, PLAN.md, and TASKS.md for the `adopt-protocol` initiative in `docs/initiatives/adopt-protocol/`.

Scope the work to the file/doc swap and reconciliation only. Expected rough shape (subject to your planning):

- Install `docs/scratch/PROTOCOL.md` → `.context/PROTOCOL.md`
- Install the six role files → `.claude/agents/<role>.md`
- Delete `.context/WORKFLOW.md`
- Delete `docs/scratch/` (or its PROTOCOL + role files) after installation
- Update `WORKFLOW.md` references inside `.context/PROJECT.md` to point at `PROTOCOL.md`
- Decide and resolve the Open Questions below before Orchestrator dispatch — most are small, but a couple need user input

Keep the initiative session-sized. If it won't fit in one Worker session, split it into phases with a `🔄 Handoff` between.

Explicitly out of scope: anything v7-retry-specific, anything about kicad extraction scripts, oscilloscope workflows, or test cards. Those are future initiatives downstream of this one.

## Open questions

- **`.context/PROJECT.md` content reconciliation.** `docs/scratch/PROJECT.md` is from a different project and must not overwrite motion-play's. But does the motion-play PROJECT.md need any structural updates to match conventions implied by the new PROTOCOL (e.g., referencing CLAUDE.md, pointing at `.claude/agents/`)? Decide whether this initiative does light reconciliation or defers it.
- **CLAUDE.md.** The new protocol references a loaded CLAUDE.md. motion-play has none. Options: (a) create a minimal CLAUDE.md that points at PROJECT.md + PROTOCOL.md; (b) leave absent and treat as a known deviation; (c) defer to a later initiative. Surface to user if unclear.
- **`.context/manifest.yaml`.** Not referenced by the new protocol. Keep, migrate, or deprecate? Surface to user.
- **`.context/IDEAS.md`.** Backlog file. Not part of either protocol version. Keep as-is unless the user wants it folded into GARDEN.md.
- **`.context/motion-play-main/`, `.context/motion-play-sensor/`.** Unknown purpose from the research session. Investigate briefly and either leave untouched or flag for a cleanup pass.
- **Branch cut.** This relay was written on `feat/v7-board-firmware` with uncommitted work. Confirm with the user which branch base the Orchestrator should branch from (probably `main`).
- **Existing initiatives under `docs/initiatives/`.** Many pre-date the new protocol. Does `adopt-protocol` do anything to them (e.g., add a note that pre-protocol initiatives follow the old shape), or leave them untouched? Lean toward untouched.

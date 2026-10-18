# Relay — planner → orchestrator — 2026-10-17

role:orchestrator

## Context
The Planner wrote BRIEF/PLAN/TASKS for `adopt-protocol`. The initiative swaps motion-play from the old `.context/WORKFLOW.md` onto the new agent-role protocol staged in `docs/scratch/`. It is a single-phase docs/config change; all open questions were resolved with the user.

## Load these files
- `docs/scratch/PROTOCOL.md` — the protocol you run under. It is not yet installed at `.context/PROTOCOL.md`; this initiative installs it. Read it from the staging location.
- `docs/scratch/orchestrator.md` — your role definition, likewise staged and not yet under `.claude/agents/`
- `docs/initiatives/adopt-protocol/BRIEF.md`, `PLAN.md`, `TASKS.md`

## State
Branch: `feat/v7-board-firmware`, with the user's uncommitted firmware/mechanical/docs work. You cut `feat/adopt-protocol` from `main` per the prerequisite below.
Build: n/a — docs/config only
TASKS.md current: yes

## What was done
- BRIEF, PLAN and TASKS were written; all Open Questions in PLAN.md are resolved (struck through)
- User decisions: strip/adapt foreign-project content minimally; drop the Explorations convention; leave manifest.yaml and IDEAS.md untouched; the Orchestrator commits the v7 WIP and then branches from `main`
- Found that `.claude/` is gitignored. PLAN un-ignores `.claude/agents/` only.
- Decided to create a minimal root CLAUDE.md, because the gardener and organizer roles assume PROJECT.md is auto-loaded through it
- Nothing is committed yet. `docs/scratch/` and `docs/initiatives/adopt-protocol/` are untracked.

## Your task
1. **Run prerequisite (before anything else). See PLAN.md § Approach.**
   - On `feat/v7-board-firmware`, stage and commit all of the user's in-flight changes, tracked and untracked, as `WIP: v7 board firmware in-flight work (pre adopt-protocol)`. **Exclude `docs/scratch/` and `docs/initiatives/adopt-protocol/`.**
   - Run `git status` and confirm that only those two paths remain untracked.
2. `git checkout main && git checkout -b feat/adopt-protocol`. Confirm that both untracked paths are still present.
3. Commit the initiative docs (BRIEF, PLAN, TASKS, this relay, RELAY-planner) plus your new SESSION.md on `feat/adopt-protocol`.
4. Run the initiative: dispatch one Worker for Phase 1 and verify against PLAN.md's verification greps and `git ls-files .claude CLAUDE.md`. Report to the user.
   - The `worker` subagent type won't exist yet, because `.claude/agents/worker.md` is installed by this very phase. Spawn a general-purpose agent instead, and include in its prompt an instruction to read `docs/scratch/worker.md` as its role definition.
   - No playtest relay is needed; this is a docs-only change.
5. Stop before merging or opening a PR. The user decides when it lands on `main`.

## Open questions
None.

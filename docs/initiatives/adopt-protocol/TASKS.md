# Adopt Protocol — Tasks

## Phase 1: Install and reconcile

- [x] Update `.gitignore`: replace `.claude/` with `.claude/*` + `!.claude/agents/`; confirm `.claude/settings.local.json` is still ignored and `.claude/agents/*.md` is not
- [x] Copy `planner.md`, `orchestrator.md`, `worker.md`, `organizer.md` from `docs/scratch/` → `.claude/agents/` verbatim
- [x] Copy `gardener.md` and `bugfix.md` → `.claude/agents/` and apply the strip/adapt edits in PLAN.md Technical Notes
- [x] Copy `docs/scratch/PROTOCOL.md` → `.context/PROTOCOL.md` and apply the strip/adapt edits (Session Management principle, delete §UI Components)
- [ ] Create minimal root `CLAUDE.md` per PLAN.md (`@.context/PROJECT.md` import + one pointer line to PROTOCOL.md and `.claude/agents/`)
- [ ] Update `.context/PROJECT.md` lines 3, 36, 46 (+ tree entries), 86 per PLAN.md; touch nothing else
- [ ] Update `.cursor/rules/context-folder.mdc` WORKFLOW.md line → PROTOCOL.md
- [ ] Delete `.context/WORKFLOW.md` and the whole `docs/scratch/` folder
- [ ] Run the PLAN.md verification greps and `git ls-files .claude CLAUDE.md`; fix any residual hits
- [ ] 🔄 Handoff

## Deferred

[from: adopt-protocol] `.context/motion-play-main/` and `.context/motion-play-sensor/` hold stale v5 netlist JSON (Feb 2026), unreferenced and duplicated under `hardware/pcb-main/kicad/netlists/`. Candidate for GARDEN.md removal.
[from: adopt-protocol] `.context/manifest.yaml` was last updated 2026-01-30 and likely stale. Decide whether to refresh or retire it.
[from: adopt-protocol] `docs/initiatives/pcb-routing-audit-tool/RELAY_V2.md` and `TASKS.md` (on `feat/v7-board-firmware`) tell sessions to load `.context/WORKFLOW.md`, which will no longer exist once both branches merge. A v2 session should load PROTOCOL.md instead.
[from: adopt-protocol] `orchestrator.md` recommends a PreCompact hook on the Worker to make the context ceiling structural. No such hook is configured in this repo.

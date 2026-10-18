# Adopt Protocol

## Intent
Replace motion-play's old workflow doc (`.context/WORKFLOW.md`) with the newer agent-role protocol staged in `docs/scratch/`, so future initiatives — starting with the v7 main PCB retry — run under it. This is a swap only, no new process content.

## Goals
- `.context/PROTOCOL.md` and the six role files (`.claude/agents/{planner,orchestrator,worker,bugfix,gardener,organizer}.md`) are installed and committed to the repo
- The installed files contain nothing specific to the other project they came from (no Storybook, Prisma, next-intl, supabase, PRD/DOMAIN-MODEL rules)
- A minimal `CLAUDE.md` exists so that PROJECT.md is auto-loaded, as the roles assume
- `.context/WORKFLOW.md` and `docs/scratch/` are gone; no live doc still points at WORKFLOW.md
- `claude --agent <role>` works from a fresh checkout

## Scope
In:
- Installing PROTOCOL.md and role files, with minimal strip/adapt edits for foreign content
- Un-ignoring `.claude/agents/` in `.gitignore`
- Creating a minimal `CLAUDE.md`
- Updating WORKFLOW.md references in `.context/PROJECT.md` and `.cursor/rules/context-folder.mdc`, plus light structural notes (CLAUDE.md, `.claude/agents/`)
- Deleting `.context/WORKFLOW.md` and `docs/scratch/`

Out:
- Anything v7-retry-specific (kicad extraction, oscilloscope workflows, test cards)
- Rewriting or restructuring the protocol beyond stripping foreign content
- `.context/manifest.yaml`, `.context/IDEAS.md`, `.context/motion-play-{main,sensor}/` — left untouched
- Existing initiatives under `docs/initiatives/` — left untouched, including their historical WORKFLOW.md references
- Carrying the old "Explorations" convention forward (dropped by user decision; `docs/explorations/` files stay where they are)
- Creating GARDEN.md, HAZARDS.md, or MASTER.md (these are created on demand by their owning roles)

## Constraints
- Do not overwrite motion-play's `.context/PROJECT.md` with `docs/scratch/PROJECT.md` (that one is an example from another project)
- The in-flight work on `feat/v7-board-firmware` must be preserved. It is committed as WIP on that branch before `feat/adopt-protocol` is cut from `main`
- `.claude/settings.local.json` must stay gitignored

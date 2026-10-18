# Adopt Protocol — Plan

## Approach

A single-phase docs/config swap. Steps: copy the staged files into place, make a small set of targeted edits to remove the other project's content, wire in CLAUDE.md and `.gitignore`, repoint references, delete the old files, then verify with greps.

**Run prerequisite (Orchestrator, before cutting the branch):**
1. On `feat/v7-board-firmware`, commit all of the user's in-flight work as `WIP: v7 board firmware in-flight work (pre adopt-protocol)`. **Exclude** `docs/scratch/` and `docs/initiatives/adopt-protocol/`, which must stay untracked so they carry over to the new branch.
2. `git checkout main && git checkout -b feat/adopt-protocol`. Confirm that `docs/scratch/` and `docs/initiatives/adopt-protocol/` are present in the working tree.
3. Commit this initiative's docs (BRIEF/PLAN/TASKS/RELAY-*) and SESSION.md on `feat/adopt-protocol` before dispatching.

`main` and `feat/v7-board-firmware` have identical `.context/`, `.cursor/` and `.gitignore`, so branching from `main` causes no divergence for this work.

**Target file map:**

| Source | Destination | Treatment |
|---|---|---|
| `docs/scratch/PROTOCOL.md` | `.context/PROTOCOL.md` | Copy + strip/adapt (see below) |
| `docs/scratch/{planner,orchestrator,worker,organizer}.md` | `.claude/agents/` | Copy verbatim |
| `docs/scratch/gardener.md` | `.claude/agents/gardener.md` | Copy + adapt |
| `docs/scratch/bugfix.md` | `.claude/agents/bugfix.md` | Copy + adapt |
| `docs/scratch/PROJECT.md` | — | Not installed; deleted with `docs/scratch/` |
| — | `CLAUDE.md` (repo root) | New, minimal |
| `.context/WORKFLOW.md` | — | Deleted |

## Technical Notes

**Strip/adapt edits.** Keep them minimal: change only the listed lines and leave wording, typos and structure alone.

- `PROTOCOL.md`
  - §Session Management principle (the "Ground every task…" paragraph): replace the "PRD, DOMAIN-MODEL, and permission-string sections" / "never silently deviate from the PRD" wording with the motion-play source docs, i.e. `.context/PROJECT.md`, the relevant `CONTEXT.md`, and datasheets/references in `docs/references/`. Keep the rest of the sentence's meaning.
  - §UI Components: delete the whole section (heading through the "Title taxonomy" paragraph), along with its trailing `---` separator, so the separators stay balanced.
- `gardener.md`
  - Implementation sub-agent contract, the "Follow the project's Critical Rules…" sentence: replace the Prisma / next-intl / DB-authorization / ledger list with "Follow the project's conventions (PROJECT.md, already loaded, and the `CONTEXT.md` of any directory you touch)".
  - Step 4, "typecheck / lint / build; the `verify` skill where there's a runtime surface": replace with motion-play checks: `pio run` for firmware, `npm run build` / lint in `frontend/motion-play-ui/`, and hardware/runtime changes flagged *needs your eyes*.
- `bugfix.md`
  - The "what organization (provide the org slug) and user (provide the email address)…" sentence: replace with the hardware setup needed (which board/revision, sensors/cables, power source) and the steps to perform (on the bench, in the web UI with URLs if applicable, or via serial monitor).
  - The "integration test steps or psql commands… Docker container… supabase" sentence: replace with programmatic steps motion-play has, e.g. serial log checks, `pio run` / upload, or querying the AWS backend (DynamoDB/API). The agent performs these unless they need physical access to the hardware.
- `organizer.md` example paths (`tools/sprite-assigner/` etc.) are format illustrations and stay as they are.

**CLAUDE.md** (repo root). Minimal, a handful of lines:
- `@.context/PROJECT.md` import, so PROJECT.md is auto-loaded (the gardener and organizer roles assume this)
- One line: the initiative workflow and agent roles are in `.context/PROTOCOL.md` and `.claude/agents/`
- No other content. Project facts belong in PROJECT.md.

**`.gitignore`.** Replace the `.claude/` line with:
```
**/.claude/*
!.claude/agents/
```
(`**/` is needed: a bare `.claude/*` is root-anchored and stops ignoring nested dirs such as `hardware/libraries/.claude/settings.local.json`.) Verify that `git check-ignore .claude/settings.local.json` and `hardware/libraries/.claude/settings.local.json` still match and `git check-ignore .claude/agents/worker.md` does not.

**`.context/PROJECT.md` edits (light reconciliation):**
- Line 3 Quick Reference: `WORKFLOW.md` → `PROTOCOL.md` ("…for the initiative workflow and agent roles"). Keep the manifest and IDEAS links.
- Line 36: initiatives follow the structure defined in `PROTOCOL.md`; roles live in `.claude/agents/`.
- Line 46 tree comment: `(this file, manifest, protocol, ideas)`. Add tree entries for `.claude/agents/` (agent role definitions) and `CLAUDE.md` (auto-loads PROJECT.md).
- Line 86 `docs/` bullet: drop the Explorations clause (convention retired). It now reads "Initiatives follow BRIEF/PLAN/TASKS/SESSION per PROTOCOL.md". The `docs/explorations/` tree entry stays because it describes files that exist.
- Do not touch anything else (status, roadmap, terminology, "Last Updated").

**`.cursor/rules/context-folder.mdc`.** Line 9: `.context/WORKFLOW.md` → `.context/PROTOCOL.md` — Initiative workflow and agent roles.

**Verification greps** (live docs only):
- `grep -rn "WORKFLOW.md" . --exclude-dir={.git,node_modules,.pio}`. Allowed hits: `docs/initiatives/*` historical files (none exist on `main`, but some exist on `feat/v7-board-firmware`).
- `grep -n -i "storybook\|prisma\|next-intl\|supabase\|psql\|DOMAIN-MODEL\|PRD\|apps/web\|org slug" .context/PROTOCOL.md .claude/agents/*.md` should return nothing.
- `git ls-files .claude CLAUDE.md` should list exactly the 6 role files and CLAUDE.md.

**Things deliberately not created:** GARDEN.md, HAZARDS.md and MASTER.md are created on demand by their owners. SESSION.md is the Orchestrator's.

## Rejected Approaches
- Install staged files verbatim (with or without a GARDEN cleanup item). Rejected by user; agents would read Storybook/Prisma rules that don't apply.
- Carry the Explorations convention into PROTOCOL.md or PROJECT.md. User chose to drop it.
- Deprecate manifest.yaml or fold IDEAS.md into GARDEN.md. User chose to keep both untouched.
- Cut `feat/adopt-protocol` from `feat/v7-board-firmware` HEAD. Would drag the unmerged pcb-routing-audit commits along.
- Install role files under `.claude/agents/` without a `.gitignore` change. `.claude/` is ignored, so they'd never be committed.
- `.claude/*` (root-anchored) in `.gitignore`. Un-ignored the nested `hardware/libraries/.claude/`; replaced by `**/.claude/*`.

## Open Questions
- ~~PROJECT.md reconciliation~~ → light edits only (see Technical Notes)
- ~~CLAUDE.md~~ → create minimal, importing PROJECT.md (roles depend on it)
- ~~manifest.yaml / IDEAS.md~~ → untouched
- ~~`.context/motion-play-{main,sensor}/`~~ → stale v5 netlist JSON exports (Feb 2026), unreferenced, duplicated under `hardware/pcb-main/kicad/netlists/`; left untouched, logged in Deferred
- ~~Branch base~~ → Orchestrator commits v7 WIP on `feat/v7-board-firmware`, then branches from `main`
- ~~Existing initiatives~~ → untouched
- ~~Foreign-project content in staged files~~ → strip/adapt minimally
- ~~Explorations convention~~ → dropped

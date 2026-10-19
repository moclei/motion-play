# v7 Retry — Research Index

Stage A of the v7 PCB debugging retry. Each row below is one research session, producing one artifact.

See `RESEARCHER.md` for conventions. Kickoff relay drafts are in `relays/`.

## Topics

| # | Topic | Status | Artifact | Depends on |
|---|---|---|---|---|
| 1 | Post-mortem of prior debug attempt | complete | `postmortem.md` | — |
| 2 | v6 → v7 changelist | complete | `v6-v7-changelist.md` | — |
| 3 | KiCad extraction audit | complete | `kicad-extraction-audit.md` | — |
| 4 | Testing / scope workflow audit | complete | `test-workflow-audit.md` | — |
| 5 | Expert approaches to PCB bring-up debug | complete | `expert-approaches.md` | — |
| 6 | Context strategy for v7-retry sessions | complete | `context-strategy.md` | all of 1–5 |

**Status values:** `not started` · `in progress` · `complete` · `blocked`

**Recommended order:** 1 and 2 first (highest leverage, independent). 3, 4, 5 next (any order). 6 last — it synthesizes patterns from the others.

## Stage transition

When topics 1–6 are complete, a synthesis session reads the whole folder and produces `decisioning.md` + `RELAY-planner.md` for the first implementation initiative. See `RESEARCHER.md` for details.

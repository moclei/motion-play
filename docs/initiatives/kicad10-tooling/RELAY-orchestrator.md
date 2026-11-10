# Relay-Planner — Orchestrator — 2026-11-10

role:orchestrator

## Context
On 2026-11-07 the user decided to move from KiCad 9.0.4 to KiCad 10 and to modernise the KiCad tooling before any v8 layout exists. The Planner recommended a new initiative rather than a replan inside v8-debug-board, and the user chose it. v8-debug-board is paused before its Phase 13 until this initiative closes.

## Load these files
- .context/PROTOCOL.md
- docs/initiatives/kicad10-tooling/BRIEF.md, PLAN.md, TASKS.md
- .context/HAZARDS.md (the kiutils entry)
- tools/CONTEXT.md (Critical, kiutils and Source-Hash rules)
- docs/research/kicad-ai-tooling-2026-11/landscape.md and schematic-readability.md: cite them in dispatches as needed; don't load them whole
- docs/initiatives/v8-debug-board/SESSION.md: grep only (it is long). Worker #12 Notes give the round-trip counting method and the KiCad 9 counts; Worker #19 Notes cover the sheet-pin check

## State
Branch: none cut yet. Cut `feat/kicad10-tooling` from the head of `feat/v8-debug-board` (PLAN Technical Notes "Branch"), **not** from `main`: v8's tooling (Phases 11a–12a) isn't on `main` yet.
Build: passing on KiCad 9.0.4. All 8 firmware envs build, and the `v8_debug_sheet.py --check` chain passes (ERC 0 errors).
TASKS.md current: yes. Phases 1–9, all `[ ]`.

## What was done
- BRIEF, PLAN and TASKS written and committed (`2130a66`, on `feat/v8-debug-board`).
- v8 PLAN OQ-3 (the board write path) is marked as deferred to kicad10-tooling Phase 5.
- KiCad 10.0.8 was checked on 2026-11-08: released (kicad.org blog dates it 30 Oct; the GitHub tag says 6 Nov). Phase 1 re-checks it before G1.
- On this machine: kicad-cli 9.0.4 at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli` (not on PATH); pyenv `python3` 3.7.3 with kiutils 1.4.8, shapely 2.0.7 and numpy 1.21.6; `/usr/local/bin/python3.13` (3.13.3) exists; the lab pre-commit hook runs on PATH `python3` (`.githooks/pre-commit`).
- kicad-cli 9.0.4 has no `sch upgrade` or `pcb upgrade` command. Whether 10 has one is a Phase 1 task.

## Your task
Run the kicad10-tooling initiative from Phase 1.

Rules to enforce in every dispatch:
- v7 files at `hardware/pcb-main/kicad/` are never opened or saved by KiCad 10. Scratch copies are made with `git archive c2acffc …`.
- `lab/` is read-only.
- Trials and probes run on scratch copies only. Nothing under `hardware/pcb-main-v8/` changes before Phase 6 and G3.
- At every handoff, `git status` must show no change under `hardware/pcb-main/`, the other boards or `lab/`.

User gates:
- **G1** (Phase 1): the user installs KiCad 10.
- **G2** (end of Phase 3): the Python runtime and shim-or-replace. A "replace" answer goes back to the Planner before Phase 4.
- **G3** (start of Phase 6): approve the v8 migration and the freeze tag.
- **G4** (Phase 7): keep or drop IPC.
- **G5** (Phase 8): keep or drop the MCP server. OQ-5 (which server) is asked at the start of Phase 8.

Phases 1, 6 and 7 have user steps (install, convert or open in the GUI, enable the API server). Ask the user before dispatching any Worker task that needs them.

## Open questions
- OQ-1 to OQ-5 are in PLAN, each with the phase or gate that answers it. OQ-6 (uninstalling KiCad 9) is Deferred.
- If KiCad 10's kicad-cli has no format-upgrade command, each conversion in Phases 3, 5 and 6 is a user GUI step. The Phase 1 Worker writes the exact steps.
- At close, Phase 9 merges back into `feat/v8-debug-board` and leaves a v8 resume note. v8 then needs a Planner replan (BRIEF toolchain line, OQ-3, Phases 13 and 16) before its loop resumes.

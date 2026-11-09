# KiCad 10 Tooling

## Intent
Move the project from KiCad 9.0.4 to KiCad 10, and bring the KiCad tools up to date, before any v8 layout exists. Two things prompted it: kiutils is unmaintained and damages KiCad 9 files, and the current tool options (live IPC, MCP servers, Freerouting over IPC) need KiCad 10. v8-debug-board is paused before Phase 13 while this runs, and resumes afterwards on KiCad 10. Research input: `docs/research/kicad-ai-tooling-2026-11/`.

## Goals
- KiCad 10.0.8 installed alongside 9.0.4, with a rollback path that has been tested.
- A decided Python runtime and dependency set for the KiCad tools.
- Every tool in `tools/schematic-*/`, `tools/pcb-context/` and `tools/lab/probe_points/`, and every `--check` chain, passes on KiCad 10 against a copy of v8. Netlists are identical before and after. kiutils is fixed with a shim where it fails on KiCad 10 files, or replaced by a maintained parser.
- OQ-3 (how scripts write boards) answered for KiCad 10 with probe evidence.
- v8's project migrated to KiCad 10: netlist identical, ERC and layout_check re-baselined, circuit-context re-extracted. The freeze tag decided.
- A bounded trial of live IPC (kipy) and of one MCP server, each ending in a keep or drop decision with evidence.
- Docs and hazards updated, so v8 resumes with a short replan.

## Scope
In: the KiCad 10 install and rollback; the Python runtime for the KiCad tools; parser compatibility; re-validating the tools on scratch copies; the board write path on 10; v8 project migration; the IPC and MCP trials on scratch copies; docs.
Out: v8 layout work (Phases 13+ stay in v8-debug-board); migrating v7, the sensor boards or the power-supply board (they stay in KiCad 9 format and the tools must still read them); Freerouting and OQ-1 (v8 Phase 16); kicad-happy (v8 OQ-9); uninstalling KiCad 9; KiCad 11.

## Constraints
- v7 files at `hardware/pcb-main/kicad/` are cited at `c2acffc` and are never re-saved by any tool or any KiCad version. `lab/` is read-only.
- `.kicad_sch` and `.kicad_pcb` are changed only through tools (tools/CONTEXT.md Critical Rule). Trials and probes run on scratch copies. The Source-Hash Rule applies.
- Files saved by KiCad 10 can't be opened by 9: only v8 is migrated, and only after the user approves it.
- The lab pre-commit hook runs on whatever `python3` is on PATH. The global Python doesn't change without the user's approval.
- One active initiative: v8-debug-board stays paused until this one closes.

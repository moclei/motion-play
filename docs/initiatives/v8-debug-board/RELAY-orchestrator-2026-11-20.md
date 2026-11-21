# Relay-Planner — Orchestrator — 2026-11-20

role:orchestrator

## Context
v8-debug-board paused before Phase 13 so the KiCad tooling could move to KiCad 10 (initiative `kicad10-tooling`, now complete). The Planner has replanned v8 from Phase 13 on for the new toolchain. Resume the loop at Phase 13.

## Load these files
- .context/PROTOCOL.md
- .context/HAZARDS.md (the KiCad 10 entries)
- docs/initiatives/v8-debug-board/BRIEF.md (Constraints: the new toolchain line), PLAN.md ("AI layout tooling", "KiCad 10", "Board-model decisions", OQ-1, OQ-3 struck), TASKS.md (Phases 13–19)
- tools/CONTEXT.md: KiCad Version Rule, I/O-module Rule, "Board write path", "Live board edits (IPC)"
- docs/initiatives/v8-debug-board/SESSION.md: grep only (last Outcome / last Worker number), don't load it whole

## State
Branch: `feat/v8-debug-board` (pushed). Tags `v8-schematic-freeze-k10` (`60e9d12`, the v8 reference), `v8-schematic-freeze` and `v8-schematic-freeze-k9` (`0d6255b`, KiCad 9 rollback) are now pushed.
Build: passing. All v8 `--check` chains pass on KiCad 10 with `KICAD_CLI` set to KiCad 10's kicad-cli.
TASKS.md current: yes. Phases 1–12a done; 13 onward replanned.

## What was done
- BRIEF Constraints: toolchain line rewritten for KiCad 10.0.8, `tools/.venv` (3.13, kicad-tools via `kicad_io`), `pcbnew` on KiCad 10's Python, kipy in `tools/.venv-kipy`.
- PLAN: OQ-3 struck. User confirmed `pcbnew` on KiCad 10 as the batch writer (`pcb_write.py`); options 2–5, kicad_io raw edits and kicad-mcp-pro are in Rejected Approaches. "AI layout tooling" rewritten around one op list with two consumers: `pcb_write.py` (batch) and `pcb_live.py` (kipy, for W4–W5). New "KiCad 10" note. kiutils references updated (OQ-11 moot).
- User decisions 2026-11-20: when `KICAD_CLI` is unset, tools pick kicad-cli by file format (Phase 13 task 1); push the three v8 tags (done); retire `place_power.py` once `place.py` covers it (Phase 13a). The generators' `--output` default stays in kicad10-tooling Deferred.
- TASKS: old Phase 13 split into 13 (kicad-cli selection + `pcb_write.py`), 13a (`place.py`, rules, `place_check.py`, retire `place_power.py`), 13b (`pcb_live.py` + a user-attended live smoke test). Phases 14–15 run W4/W5 live over kipy, with batch write + diff as fallback. Phase 16 adds a short kipy track read-back probe before W6 and uses no MCP server.

## Your task
Run v8-debug-board from Phase 13. Every dispatch must name: `tools/.venv`, kicad-cli under a scratch `KICAD_CONFIG_HOME` seeded with KiCad 10's default lib tables, and `KICAD_CLI` set to `/Applications/KiCad10/KiCad.app/Contents/MacOS/kicad-cli` until Phase 13 task 1 lands. v7 test boards are scratch copies of `c2acffc` converted with `kicad-cli 10 pcb upgrade`; nothing under `hardware/pcb-main/` or `lab/` changes. Phase 13b and W4–W6 need the user at KiCad 10. Take those to the user as user steps.

## Open questions
- OQ-1 (which nets the AI may route, plus the Freerouting experiment) is unchanged; due at Phase 16 task 1.
- kicad10-tooling OQ-6 (uninstall KiCad 9.0.4) becomes possible after Phase 14 places the first v8 block on 10. Not v8 work. Remind the user then, and keep v7/lab on 9 regardless. The app path matters: renaming `KiCad10.app` breaks the global lib tables (HAZARDS).
- KiCad 11 (around early 2027) removes `pcbnew`: keep `pcb_write.py` behind its op-list interface.

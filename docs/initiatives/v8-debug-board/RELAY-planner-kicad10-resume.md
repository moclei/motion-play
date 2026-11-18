# Relay-Orchestrator — Planner — 2026-11-18

role:planner

## Context
v8-debug-board was paused before Phase 13 so the KiCad tooling could be upgraded first (`RELAY-planner-tooling-upgrade.md`). That work ran as its own initiative, `kicad10-tooling`, which is now complete. v8 is on KiCad 10, kiutils is gone, the board write path (OQ-3) is answered, and the live-IPC and MCP trials are decided (keep kipy, drop MCP). v8 now needs a Planner replan so that it resumes at Phase 13 on the new toolchain.

## Load these files
- .context/PROTOCOL.md
- .context/HAZARDS.md: the seven KiCad 10 entries added by kicad10-tooling Phase 17
- docs/initiatives/v8-debug-board/BRIEF.md (Constraints, toolchain line), PLAN.md (OQ-3, OQ-1, OQ-11, "AI layout tooling", "Board-model decisions", Rejected Approaches), TASKS.md (Phases 13–19)
- docs/initiatives/kicad10-tooling/SESSION.md: grep, don't load it whole:
  - **"v8 resume note"** in the Worker #20 Notes. This is the primary input: it lists every v8 doc change, line by line.
  - "### G3 — user decision", "### G4 — user decision", "### G5 — user decision"
  - the "**Outcome:**" line at the end
- docs/initiatives/kicad10-tooling/PLAN.md: "Board write path" (OQ-3 on KiCad 10), Trials ("IPC outcome"), Rejected Approaches (kicad-mcp-pro), Deferred items in TASKS.md
- tools/CONTEXT.md: the KiCad Version Rule, the I/O-module Rule, "Board write path", "Live board edits (IPC)"
- hardware/CONTEXT.md "KiCad Versions"; hardware/pcb-main-v8/CONTEXT.md (design intent)

## State
Branch: `feat/v8-debug-board` at `0b43a5d` (fast-forwarded to the end of kicad10-tooling). It and `feat/kicad10-tooling` are both pushed; no PR is open. Tags `v8-schematic-freeze-k10` (`60e9d12`, the v8 reference from now on) and `v8-schematic-freeze` / `-k9` (`0d6255b`, the KiCad 9 rollback point) exist locally.
Build: passing. All the v8 `--check` chains pass on KiCad 10 with `KICAD_CLI` set to 10. The ERC baseline is in the resume note.
TASKS.md current: v8's TASKS is current up to Phase 12a and still describes Phase 13 onwards in the pre-upgrade terms. That's what this replan fixes.

## What was done
- KiCad 10.0.8 is installed at `/Applications/KiCad10` alongside 9.0.4. v8's schematic and board were migrated at `60e9d12`. The netlist is structurally identical to the KiCad 9 freeze; 19 `lib_symbol_mismatch` warnings were accepted at G3. v8 resolves its own libraries through project lib tables.
- The tools run in `tools/.venv` (Python 3.13). kicad-tools 0.29.0 is used only through `tools/kicad-io/kicad_io.py`, with the splice save, the lock guard and the format checks. kiutils is removed, so v8 OQ-11 is moot.
- OQ-3 is answered: pcbnew on KiCad 10's bundled Python, in one `pcb_write.py` with three guards (KiCad 10 format only, a lock check, and kicad-cli plus a board-model check afterwards). It isn't built yet; that's v8 Phase 13 work. The first save of a converted board regroups its tracks once.
- G4, keep: kipy over IPC (`tools/requirements-kipy.txt`, venv `tools/.venv-kipy`) is the live channel for the W4–W5 placement reviews. Each AI edit is one named undo step, and the user's corrections are read back. The API server is enabled in the user's KiCad 10 prefs.
- G5, drop: kicad-mcp-pro. Its reads lose rotation and anything below 0.01 mm, its edits aren't named undo steps, it costs about $0.2 per turn, and its write mode can't be limited to moves. No MCP server is used.
- The tools still default `KICAD_CLI` to 9.0.4 (`tools/schematic-modify/modify.py:44`, `tools/pcb-context/board_model.py:74`). v8 work must set it to KiCad 10's kicad-cli, and should use a scratch `KICAD_CONFIG_HOME`.

## Your task
1. Read the files above, starting with the v8 resume note.
2. Replan v8-debug-board from Phase 13 on:
   - BRIEF: the toolchain Constraints line (proposed wording is in the resume note).
   - PLAN: strike OQ-3 with its answer and move options 2–5 to Rejected Approaches; rewrite "AI layout tooling" for KiCad 10, kicad_io, pcbnew 10 and the G4 live channel; replace the kiutils references in "Board-model decisions".
   - TASKS: Phase 13 (`pcb_write.py` on KiCad 10 with the format guard, the restated empty-op-list test, the board-model check keyed by ref, and a possible `pcb_live.py` for W4–W5), Phases 14–15 (W4/W5 using kipy), and Phase 16 (no MCP; a short kipy track read-back probe before W6 relies on it).
3. Put these questions to the user, in plain terms with a recommendation each:
   - Should the tools' `KICAD_CLI` default switch to KiCad 10 now? This touches v7 workflows, which stay on 9.
   - Should the local tags be pushed?
   - Are any of kicad10-tooling's Deferred items to be pulled into v8 (`place_power.py` writing outside `kicad_io`; the generators' `--output` default)?
4. Once the user approves, write `RELAY-orchestrator-<date>.md` so v8 can resume. Don't overwrite the existing `RELAY-orchestrator.md`.

## Open questions
- v8 OQ-1 (which nets the AI may route, and the Freerouting experiment) is unchanged and still due by Phase 16.
- kicad10-tooling OQ-6, uninstalling KiCad 9, stays deferred until v8 has placed its first block on 10.
- KiCad 11 (around early 2027) removes pcbnew. `pcb_write.py` must stay one module behind a narrow interface so it can move to IPC or kicad_io raw edits.

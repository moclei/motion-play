# Relay-Orchestrator — Planner — 2026-11-07

role:planner

## Context
The v8-debug-board initiative has finished Phases 1–12a: the schematic is frozen at tag `v8-schematic-freeze`, the v8 firmware envs exist, and circuit-context.json is correct. Before Phase 13 (AI placement), the user decided to **upgrade KiCad (9.0.4 → 10.x) and modernise the KiCad tooling now**, before any v8 layout exists. Two things led there: the research in `docs/research/kicad-ai-tooling-2026-11/`, and the finding that kiutils (unmaintained since 2024-02) damages KiCad 9 files. The user wants the Planner's opinion on whether this work is **a new initiative** (v8 paused, resumed at Phase 13 on KiCad 10 afterwards) or **a replan inside v8-debug-board** (inserted phases before Phase 13). The user has generally preferred one initiative at a time. The user decides after reading your recommendation.

## Load these files
- .context/PROTOCOL.md
- .context/HAZARDS.md (kiutils entry)
- docs/initiatives/v8-debug-board/BRIEF.md, PLAN.md, TASKS.md (Phases 13–19 especially; PLAN OQ-1, OQ-3, OQ-9, "AI layout tooling", Rejected Approaches)
- docs/initiatives/v8-debug-board/SESSION.md: grep these sections, don't load the file whole (it is long):
  - "Replan — schematic readability"
  - Worker #12 Notes: kiutils shim, and OQ-11, where a board round trip fails to load
  - "Replan — board write path": the pcbnew probe, a byte-identical round trip
  - Worker #19 Notes
- docs/research/kicad-ai-tooling-2026-11/landscape.md and schematic-readability.md
- tools/CONTEXT.md, tools/schematic-modify/CONTEXT.md, tools/schematic-context/README.md, tools/pcb-context/ (CONTEXT/README)
- hardware/pcb-main-v8/CONTEXT.md (design intent; frozen schematic)

## State
Branch: feat/v8-debug-board (clean). v8-debug-board is paused before Phase 13. OQ-3 (the board write path) is unanswered, waiting on this decision.
Build: passing. All 8 firmware envs build. The `v8_debug_sheet.py --check` chain passes on KiCad 9.0.4: ERC 0 errors, plus layout_check.
TASKS.md current: yes.

## What was done
- Tooling built in Phases 11a–12a, all on KiCad 9.0.4 and Python 3.7 plus kiutils 1.4.8:
  - `kiutils_k9.py` shim: hide flags, and no save while KiCad has the file open
  - `tidy_fields.py`, `tidy_labels.py`
  - `layout_check.py`: a ratcheting baseline; no-justify and T-touch rules
  - `extract.py --check-sheet-pins`: a probe netlist
- A kiutils Board round trip breaks KiCad 9 boards: kicad-cli can't load the result. KiCad 9's bundled pcbnew round-trips v7 byte-identically, and moves, rotations and flips all load. The Planner recommended pcbnew as OQ-3 option 1.
- What the research says about KiCad 10:
  - The IPC API covers the PCB only, and needs the GUI open. Schematic support and headless use come in KiCad 11, around early 2027.
  - pcbnew still exists in 10 and is removed in 11.
  - kicad-mcp-pro requires 10. Freerouting 2.5 talks to 10 over IPC.
  - Files saved in 10 can't be opened in 9.
  - kiutils compatibility with 10 is unknown. Its possible replacements, kicad-sch-api and kicad-tools, need Python 3.10 or newer; /usr/local/bin/python3.13 exists on this machine.
- User decisions, 2026-11-07:
  - Upgrade now, before layout.
  - Wants better tooling, and asked whether MCP servers help.
  - The Orchestrator explained that MCP is a wrapper and doesn't avoid the save-path question. Live IPC ("Claude moves parts while you watch") might help the W4–W6 placement review loop.
- Constraints that stay:
  - v7 files at `hardware/pcb-main/kicad/` are cited at `c2acffc` and must never be re-saved, including by KiCad 10.
  - `lab/` is read-only.
  - `.kicad_sch` and `.kicad_pcb` are edited only through tools.
  - The Source-Hash Rule applies.

## Your task
1. Read the files above. Form a recommendation: **new initiative** vs **replan inside v8-debug-board**, with the reasons and the trade-offs. Consider scope, which tools outside v8 are affected, the BRIEF constraints, and how v8 resumes.
2. Present the recommendation to the user in plain terms (the user is an engineer but not an EE, and leans on recommendations). Wait for the user's choice. Don't write documents before it.
3. Whichever shape is chosen, the work should cover at least:
   - KiCad 10 installed alongside 9 at first, with a rollback path.
   - Which Python the tools run on, and the dependency set.
   - Every tool in `tools/schematic-*` and `tools/pcb-context/`, and every `--check` chain, re-validated on KiCad 10 against a copy of v8:
     - the netlist must stay identical;
     - fix kiutils, or replace it with a maintained parser where it fails.
   - v8's project migrated to KiCad 10, with re-baselined ERC/layout and a fresh circuit-context. Decide whether the `v8-schematic-freeze` tag is superseded by a KiCad-10 freeze tag.
   - The OQ-3 answer re-asked for KiCad 10: likely pcbnew, but verify it.
   - A bounded trial of live IPC (kipy), and of one MCP server, on scratch copies. Each ends in a keep or drop decision with evidence.
   - Docs updated: tools/CONTEXT.md, HAZARDS, and `hardware/CONTEXT.md` if the KiCad version is recorded there.
4. Then write the docs (a new initiative's BRIEF/PLAN/TASKS, or a v8 replan), including user gates. Write an orchestrator relay only if the user asks.

## Open questions
- New initiative vs replan: the user decides after your recommendation.
- KiCad 10.0.7 vs 10.0.8: 10.0.8 was unconfirmed on 2026-11-04. Check before pinning a version.
- OQ-9 (kicad-happy as a standing check) is still open in v8; the recommendation is no. It isn't part of this decision unless KiCad 10 changes it.
- If a new initiative is chosen: the folder name, and whether `docs/research/kicad-ai-tooling-2026-11/` becomes its research input.

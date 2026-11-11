# KiCad 10 Tooling — Tasks

## Phase 1: Install side by side, one kicad-cli path, KiCad 9 baselines

- [x] Confirm KiCad 10.0.8 is the current stable macOS release (kicad.org downloads). If a newer 10.0.x exists, pin that instead and record why
- [x] **G1 (user):** install KiCad 10 to `/Applications/KiCad10/KiCad.app`, leaving `/Applications/KiCad/KiCad.app` (9.0.4) in place. The Worker writes exact steps: download, drag, rename the folder, first launch, and no project opened. Confirm afterwards that both `kicad-cli version` commands work and that `~/Library/Preferences/kicad/9.0` hasn't changed (compare its listing before and after)
- [x] One kicad-cli path: grep `tools/` for hard-coded KiCad app paths and the `kicad-cli` lookup. Every tool reads `KICAD_CLI` (env), falling back to the 9.0.4 path for now. No behaviour change on 9: every `--check` chain still passes
- [x] Check KiCad 10's kicad-cli for a schematic/board upgrade command (`sch --help`, `pcb --help`). Record the answer in PLAN Technical Notes "Converting the format". If there isn't one, write the exact GUI open-and-save steps for scratch copies
- [x] KiCad 9 reference run, outputs to the scratchpad. Record hashes and counts in SESSION.md. For v8 at `v8-schematic-freeze`: netlist, ERC counts, `v8_debug_sheet.py --check`, `layout_check.py`, `extract.py --check-sheet-pins`, `tidy_fields.py --check`, `tidy_labels.py --check`. For v7 from `git archive c2acffc`: board model, net and plane reports, and the probe-points `pads` output
- [x] Rollback drill: with `KICAD_CLI` set to 10, run one read-only check (v8 netlist export), set it back to 9 and re-run. Record it
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 2: Python runtime parity (still KiCad 9)

- [x] `tools/requirements.txt` (merging `tools/pcb-context/requirements.txt`; the old file points to it or is removed) and a gitignored `tools/.venv` on `/usr/local/bin/python3.13`. Pin the versions that install. The global `python3` and `.githooks/pre-commit` don't change
- [ ] Re-run Phase 1's KiCad 9 reference set under the venv. Outputs must be byte-identical. For board-model floats, state a tolerance and list every value outside exact match. Fix any 3.13 incompatibility in the tools; they must keep running on 3.7 until G2
- [ ] Record the parity result in SESSION.md, with the evidence OQ-1 needs (PLAN OQ-1)
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 3: KiCad 10 file format and the kiutils round-trip survey

- [ ] Scratch copies (never a GUI open of the working tree): v8 at `v8-schematic-freeze`, and v7 via `git archive c2acffc`. Convert both to the KiCad 10 format (Phase 1's method). kicad-cli 10's netlist of each copy against kicad-cli 9's netlist of the original: identical apart from header lines. ERC/DRC counts listed side by side
- [ ] Round-trip survey (PLAN "Round-trip survey"): kiutils 1.4.8 with `kiutils_k9`, a load + save of every converted v8 sheet, v8's board and v7's board. Count every token kind before and after; compare the netlist and plotted strings per sheet. Also check whether the KiCad 9 tools still read the unconverted KiCad 9 files on kicad-cli 10 (the other boards stay on 9)
- [ ] Read-only parse test of the same files with kicad-sch-api and kicad-tools (in the 3.13 venv, not added to requirements): do they load the files, round-trip them, and keep the tokens kiutils drops?
- [ ] Loss table plus a recommendation for OQ-1 and OQ-2 in SESSION.md
- [ ] **G2 (user):** decide OQ-1 (Python) and OQ-2 (shim or replace). Record both in PLAN (strike them; the options not chosen go to Rejected Approaches). If OQ-2 is "replace", stop and return to the Planner before Phase 4
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 4: Schematic tools on KiCad 10

- [ ] Shim, version-aware: extend `kiutils_k9.py` to cover every KiCad 10 loss in the Phase 3 table. Rename it if needed; if it's renamed, update every import. Round trip of the converted v8 sheets: 0 tokens lost, stable on a second round trip, netlist identical. KiCad 9 sheets (v7 `c2acffc`) are still kept item by item
- [ ] Re-validate on the KiCad-10 scratch v8, with `KICAD_CLI` set to 10: `v8_debug_sheet.py --check` (and the other `v8_*.py --check`), `tidy_fields.py --check` and `tidy_labels.py --check` (0 to do), `layout_check.py`, `extract.py --check-sheet-pins` (0 offenders), `annotate.py` and `show.py`. layout_check's geometry is calibrated on kicad-cli 9 SVG plots: re-check the calibration on 10 plots and fix it if they differ
- [ ] `tools/schematic-gen/` generators: generate one sheet into scratch with each generator, convert it, and check ERC on 10. If a generator only targets a retired board, mark it as not re-validated in its README instead
- [ ] Switch to the decided Python runtime (G2) for the schematic tools. Update the run instructions in `tools/schematic-modify/CONTEXT.md` and `tools/schematic-context/README.md`
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 5: Board tools and the write path on KiCad 10

- [ ] `tools/pcb-context/` (board_model, net_report, plane_report, render, extract, routing_extract) on scratch v7 converted to 10, against the Phase 1 KiCad 9 reference: identical model and reports, or each difference explained by a format change. Fix the parsing where needed (Phase 4's shim, or the board part of it). `tools/lab/probe_points` `pads` and `render` on 10: markers are still on their pads (look at the PNG)
- [ ] OQ-3 probe (PLAN "Board write path"): KiCad 10's bundled Python and `pcbnew`. A load + save of the converted v7 is byte-identical; move, rotate and flip C9, then kicad-cli 10 loads it and runs DRC. Record the paths and the result in PLAN (strike OQ-3, stating the recommended path for v8 Phase 13)
- [ ] Switch the board tools to the decided Python runtime. Update `tools/pcb-context/README.md`
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 6: Migrate v8 to KiCad 10

- [ ] **G3 (user):** approve the migration and answer OQ-4 (freeze tag). Record both in PLAN
- [ ] KiCad is closed (no `~*.lck`). Tag `v8-schematic-freeze-k9` on the `v8-schematic-freeze` commit. Convert `hardware/pcb-main-v8/kicad/` (schematic, board, project) to KiCad 10 by Phase 1's method; only those files change (check `git status`; nothing under `hardware/pcb-main/`, other boards or `lab/`)
- [ ] Gate (PLAN "Migrating v8"): netlist identical to 9.0.4 at `v8-schematic-freeze`; ERC 0 errors, warnings listed against the 9.0.4 counts; every `v8_*.py --check` passes; `layout_check` re-baselined, with each change explained; `extract.py --previous` reports no structural changes; `--check-sheet-pins` 0 offenders; `check_state.py --fresh` FRESH. Commit, then cut the tag chosen at G3
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 7: Live IPC trial (kipy)

- [ ] kipy in its own venv (scratchpad, or gitignored under `tools/`). **(user)** enables the API server in KiCad 10 (Preferences → Plugins) and opens a scratch KiCad-10 copy of v7's board. Never the working tree
- [ ] Run the trial task (PLAN "Trials") while the user watches: list the footprints, move three named footprints, rotate one, read back. Then the user moves one part and the script reads that correction back. Record the time per call, any busy or timeout failures, and whether the board on disk matches after the user saves
- [ ] **G4 (user):** keep or drop, with the evidence. If kept: where it fits in v8 (W4–W6 and/or Phase 16) and a tools/CONTEXT.md line. If dropped: a line in PLAN Rejected Approaches
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 8: MCP server trial

- [ ] Ask OQ-5 (which server; PLAN recommends kicad-mcp-pro), then record the answer. Install it pinned to a release, configured project-local for the trial only, read-only profile first
- [ ] The same trial task as Phase 7, on a fresh scratch copy, with the same measurements. Also count the tool calls and tokens per task against Phase 7's script
- [ ] **G5 (user):** keep or drop, with the evidence side by side with Phase 7. If dropped, remove the server config and add a Rejected Approaches line. If kept, its config is committed and a tools/CONTEXT.md line says what it's for and what it may write
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 9: Docs and close

- [ ] `tools/CONTEXT.md`: kiutils rule (the shim's new name and scope), the KiCad version and `KICAD_CLI`, the Python runtime and venv, the board write path, and the trial outcomes. `tools/schematic-modify/CONTEXT.md` and `tools/pcb-context/README.md` checked against what Phases 4–5 changed
- [ ] `.context/HAZARDS.md`: update the kiutils entry; add "files saved by KiCad 10 can't be opened by 9; never open v7 (`hardware/pcb-main/kicad/`) in KiCad 10 and save"; add any trap found in Phases 1–8. `hardware/CONTEXT.md`: note which boards are in which KiCad format. `.context/PROJECT.md` Development Environment: the KiCad version
- [ ] v8 resume note in SESSION.md for the v8 Planner replan: v8 BRIEF Constraints line (toolchain), v8 PLAN OQ-3 answer and "AI layout tooling" path, Phase 13 and 16 changes from G4/G5, freeze-tag name. Merge `feat/kicad10-tooling` into `feat/v8-debug-board`
- [ ] 🔄 Handoff

## Deferred

[from: kicad10-tooling] Uninstall KiCad 9.0.4 once v8 has placed its first block on 10 (OQ-6).
[from: kicad10-tooling] Migrating the sensor-rigid, sensor-flex and power-supply projects to KiCad 10 when they next get design work. v7 is never migrated.
[from: kicad10-tooling] KiCad 11 (around early 2027): headless IPC and the schematic API, and `pcbnew` removed. Revisit the board writer and the kiutils dependency then.

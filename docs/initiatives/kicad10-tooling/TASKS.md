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
- [x] Re-run Phase 1's KiCad 9 reference set under the venv. Outputs must be byte-identical. For board-model floats, state a tolerance and list every value outside exact match. Fix any 3.13 incompatibility in the tools; they must keep running on 3.7 until G2
- [x] Record the parity result in SESSION.md, with the evidence OQ-1 needs (PLAN OQ-1)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 3: KiCad 10 file format and the kiutils round-trip survey

- [x] Scratch copies (never a GUI open of the working tree): v8 at `v8-schematic-freeze`, and v7 via `git archive c2acffc`. Convert both to the KiCad 10 format (Phase 1's method). kicad-cli 10's netlist of each copy against kicad-cli 9's netlist of the original: identical apart from header lines. ERC/DRC counts listed side by side
- [x] Round-trip survey (PLAN "Round-trip survey"): kiutils 1.4.8 with `kiutils_k9`, a load + save of every converted v8 sheet, v8's board and v7's board. Count every token kind before and after; compare the netlist and plotted strings per sheet. Also check whether the KiCad 9 tools still read the unconverted KiCad 9 files on kicad-cli 10 (the other boards stay on 9)
- [x] Read-only parse test of the same files with kicad-sch-api and kicad-tools (in the 3.13 venv, not added to requirements): do they load the files, round-trip them, and keep the tokens kiutils drops?
- [x] Loss table plus a recommendation for OQ-1 and OQ-2 in SESSION.md
- [x] **G2 (user):** decide OQ-1 (Python) and OQ-2 (shim or replace). Record both in PLAN (strike them; the options not chosen go to Rejected Approaches). If OQ-2 is "replace", stop and return to the Planner before Phase 4. Decided: the 3.13 venv, and replacing kiutils with kicad-tools. The Planner replanned Phases 4 onward
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 4: Port groundwork: harness, scratch-root checks, kicad-tools pinned (still kiutils, KiCad 9)

- [x] Regression harness under `tools/kicad-regress/` (PLAN "Regression harness"): fresh `git archive` copies with `hardware/pcb-main/resources`, fixed-length run roots, a choice of Python, `KICAD_CLI` and tools ref (working tree or a worktree at a git ref), and a compare mode. Add a short entry for it in `tools/CONTEXT.md`
- [x] Scratch roots for the checks (PLAN "Scratch roots for the checks"). `layout_check.py`'s baseline is keyed relative to the project root. `v8_*.py --check` and `v8_project_setup.py --verify` take `--root`. On the working tree, the output is byte-identical before and after (show both)
- [x] The harness, run on the current tools with KiCad 9, reproduces the Phase 1 reference hashes (SESSION Worker #1 Notes). Every `v8_*.py --check` also passes on a scratch root
- [x] Add `kicad-tools==0.29.0` to `tools/requirements.txt`, with every transitive package pinned; kiutils stays. Rebuild `tools/.venv` from the file; `pip check` must be clean. If kicad-tools forces new shapely, numpy or matplotlib versions, the harness must still match the reference (1e-9 mm). Any difference stops the phase. The global `python3` doesn't change
- [x] Tag `kicad10-preport` on the handoff commit: it's the oracle for Phases 6–11
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 5: kicad-tools API spike (scratch only; no tool is ported)

- [x] Coverage map: every kiutils class and function that the 23 files use (PLAN "Port scope"), mapped to kicad-tools' typed layer, its raw s-expression layer, or "gap". Table in SESSION.md
- [x] Editing prototypes on a scratch v8 (KiCad 9, `KICAD_CLI` on 9) for each public `modify.py` operation: add and remove a component (with the library symbol embedded), wires, junctions, local and hierarchical labels, sheet references and sheet pins, no-connects, power symbols, property edits, annotation. Compare each with the same edit by the `kicad10-preport` `modify.py` on the same input. Netlist, ERC counts and plotted strings must be identical, and the token census may show only the intended change. Repeat a representative subset on a converted KiCad 10 copy (`KICAD_CLI` on 10)
- [x] Board read prototype: every value `board_model.py` reads (footprints, pad geometry including custom shapes and rotation, tracks, arcs, vias, zones and fills, stackup, outline, nets), from v7 on KiCad 9 and converted to 10, through kicad-tools. Compare with kiutils' read of the KiCad 9 board: the values must match
- [x] Save format (OQ-7). Measure the git diff of a one-property edit saved by kicad-tools, and state the options. Check that a kicad-tools save of a KiCad 9 file keeps it in KiCad 9 format (version token unchanged, and kicad-cli 9 loads it)
- [x] Propose the I/O module: its name, its functions, the lock guard and the version check (PLAN "One I/O module"). Confirm the retire candidates (PLAN "Retire candidates"): check that nothing else calls them. Record both in SESSION.md
- [x] **G2a (user):** go or no-go on the full port, given the coverage map. The options: (a) proceed, using the typed API where it covers and the raw s-expression layer for the gaps; (b) proceed on the raw layer for `modify.py`, with our own helpers; (c) stop and reopen OQ-2 (back to the Planner). Also answer OQ-7 and the retire list. Record all three in PLAN. Decided: (b) for every writer and the board readers (typed views read-only), the splice save, and delete all three retire candidates. The Planner recorded them and the preport exceptions E1 and E2
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 6a: The I/O module (still KiCad 9; no tool is ported)

- [x] Build `tools/kicad-io/kicad_io.py` (PLAN "One I/O module"): the pin check, the format check, `load_schematic`/`load_symbol_lib`/`load_board` returning a `Doc`, `save`/`save_project` with the lock guard, the version-unchanged check and the splice save, and the raw-tree helpers (PLAN "Raw-layer traps": `set_num` writes exact number text; `make_property`/`is_hidden`/`hide` handle all three hide forms by the `Doc`'s version). Start from the Phase 5 prototype (`p5/scripts/ktmod.py` and `savefmt.py` in the session scratchpad) if it's still there. `kiutils_k9.py` and every tool stay as they are
- [x] A committed test under `tools/kicad-regress/` (and a `regress.py` subcommand to run it): (1) load + save through `kicad_io` of every `.kicad_sch` and `.kicad_pcb` that `regress.py roundtrip` covers (v8 at `v8-schematic-freeze`, v7 `c2acffc`, power-supply, sensor-rigid, sensor-flex at HEAD) is tree-identical and keeps the version token, and an unedited splice save is byte-identical to the input; (2) one property edit on a KiCad-format sheet, one on the kiutils-format LED sheet, and one footprint move on v7's board (a scratch copy): each splice save is tree-identical to a plain kicad-tools save of the same edit, and the git diff touches only the edited item (record the line counts); (3) the same on a converted KiCad 10 copy, where kicad-cli 10 loads the result; (4) the lock guard refuses with a `~*.lck` present, the format check refuses a made-up newer version, the pin check refuses a different version, and `save` refuses a tree whose version token was changed; (5) a float written through `set_num` keeps all its digits; a hide written on 9 and on 10 lands in that version's form, and hiding an already-hidden property adds no second flag
- [x] kicad-cli 9 loads every KiCad 9 file the test saved (netlist for schematics, DRC for v7's board), with counts equal to the unsaved input's
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 6b: Port `modify.py`

- [x] Port `modify.py` onto `kicad_io` and its helpers: every public operation, the same signatures where the callers allow, raw layer only (PLAN "Which layer"). Reproduce preport's `add_sheet_reference` (E2) and the one-entry-per-pin-number behaviour exactly. `annotate_components` finds `annotate.py` from `Path(__file__)`
- [x] A committed differential test under `tools/kicad-regress/` that drives every public `modify.py` operation on a scratch copy, with the ported tools and with `kicad10-preport` (PLAN "Oracle", write tools; Phase 5's 11 ops, `edits.py`/`cmp_edit.py`, are the model, with seeded UUIDs). All pass on KiCad 9, and the kicad-tools census shows only the intended edit. Also run it on a converted KiCad 10 copy (`KICAD_CLI` on 10) for the property-writing ops and the sheet ops: pass, census only the edit
- [x] E2 fix, as its own commit after the test passes (PLAN "Accepted differences from preport", E2): the project name from the root schematic's stem, keys `Sheetname`/`Sheetfile`. Update the test's `add_sheet_reference` case to the E2 rule and re-run. Record the commit and the tree differences in SESSION
- [x] Handoff note: list the scripts that can't run until Phases 7–8 (PLAN "Transient breakage")
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 7: Tidy tools, `layout_check`, `v8_project_setup`, `v8_mcu_sheet`

- [x] Extend `--root` to the write modes (`--apply`, `--erc-fixes`, `--fix-11c/f`, `--annotate`) of the v8 scripts and to `v8_project_setup.py --apply` (its `DEST.relative_to(REPO)` print must work outside the repo), so the replays below run on scratch roots. On the working tree, `--check` output is byte-identical before and after
- [x] Port `tidy_fields.py`, `tidy_labels.py` and `layout_check.py` (`layout_check` reads through `to_lists`). `--check` outputs are identical to `kicad10-preport` on scratch v8 and v7 (KiCad 9). `--apply` on a scratch copy with something to tidy: identical netlist, ERC and plotted strings to the preport `--apply`
- [x] Port `v8_project_setup.py` (its board strip through `load_board`/`save`) and `v8_mcu_sheet.py` (its one-level `extends` flatten on the raw node). `--check`/`--verify` are identical to preport on a scratch root. `--apply` replay: run `git archive` of the v8 project at the commit before that script's `--apply` landed (for `v8_project_setup`, from v7 `c2acffc`). Run the preport and the ported `--apply` on two copies; the netlist, ERC and plotted strings must be identical, and for `v8_project_setup` the board's DRC counts too
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 8: `v8_debug_sheet`, `v8_bus_sheet`, `v8_power_sheet`; delete the v7 schematic scripts

- [x] Port the three, by the same method as Phase 7 task 3: `--check` identical on a scratch root, and an `--apply` replay from the commit before each apply landed (including `v8_power_sheet`'s one-off ERC-fix mode)
- [x] Delete `tools/schematic-modify/esp32_integration.py` and `esp32_integration_phase2.py` (G2a). Remove the `tools/CONTEXT.md` row (line 57 at `5060d05`) and the `tools/schematic-modify/CONTEXT.md` line (52), and reword its Typical Workflow step 1 (61) to name a `v8_*.py` script. `git grep` finds neither name outside history (archive initiatives, research, SESSION files)
- [x] Every remaining script that imports `modify.py` runs again (the Phase 6b handoff list is empty)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 9: `schematic-context` and `schematic-gen`

- [x] Port `extract.py`, `annotate.py` and `show.py` (raw layer; typed `Schematic` views allowed for reads). On scratch v8 (at `v8-schematic-freeze`) and v7 (`c2acffc`), KiCad 9, compare with `kicad10-preport`: `circuit-context.json` is identical (with and without `--previous`), `--check-sheet-pins` is identical, and the `annotate.py` and `show.py` outputs are identical
- [x] Port the three generators (`Schematic.create_new` becomes a template parsed by `node()`). Generate into scratch with preport and with the ported version: the netlist and ERC must be identical. Outputs go to scratch, never to their default paths under `hardware/pcb-main/kicad/`
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 10: Board readers; delete `route_esp32.py`

- [x] Port `board_model.py` onto `load_board` with small raw accessors in `pcb-context` (no typed `PCB`; PLAN "Raw-layer traps"), including custom-pad anchor and primitives. On v7 `c2acffc` (KiCad 9), `board-model.json` matches `kicad10-preport` on every leaf (1e-9 mm) except the E1 leaves (PLAN "Accepted differences from preport"); list each E1 leaf in SESSION with old value, new value and the file token. The net and plane reports and probe-points `pads U5 C21 C9` are identical, with no exception. `hardware/pcb-main/kicad/board-model/` isn't regenerated
- [x] Port `pcb-context/extract.py`, `routing_extract.py` and `tools/verify-routing.py` on the same accessors. Their outputs on v7 `c2acffc` are identical to preport (an E1 field carried into one of them takes the E1 rule; list it)
- [x] Delete `tools/route_esp32.py` (G2a). Re-grep for doc lines that name it outside history and remove any found
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 11: Remove kiutils; KiCad 9 reads; the parser rule

- [x] Final run of the full harness, the Phase 6a I/O test and the Phase 6b differential test against `kicad10-preport`, on KiCad 9, before kiutils is removed: everything matches, apart from E1 and E2 as listed. Then delete `kiutils_k9.py`, take kiutils out of `tools/requirements.txt`, and rebuild the venv from the file. `pip check` must be clean, and grep must find no `kiutils` import under `tools/` (outside `.venv`)
- [x] KiCad 9 files are still read (they stay on 9). Use `git archive` copies of v7 (`c2acffc`) and of sensor-rigid, sensor-flex and power-supply at HEAD. An I/O-module load and save of every `.kicad_sch` and `.kicad_pcb` must be tree-identical, with the version token unchanged. `schematic-context/extract.py` must run on each schematic project into scratch. Nothing under `hardware/` changes
- [x] Rules and run instructions. `tools/CONTEXT.md`: the kiutils Rule becomes the I/O-module rule (load and save only through `kicad_io`, the raw layer for writes and board reads with typed views read-only, the splice save, the lock guard, the pinned version, and the upgrade procedure from PLAN "Pin and upgrades"); the "Dependencies" line; the kiutils_k9 row becomes a `kicad-io/` entry. `tools/schematic-modify/CONTEXT.md`, `tools/schematic-context/README.md` and `tools/pcb-context/README.md`: run with `tools/.venv/bin/python`. `.context/HAZARDS.md`: replace the kiutils entry, and add the 6-significant-digit float atom trap
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 12: Schematic tools on KiCad 10

- [x] `extract.py` and the kicad-cli 10 `pinfunction` suffix (PLAN "kicad-cli 10 differences"). With `KICAD_CLI` on 10, `circuit-context.json` from a converted scratch v8 must equal the KiCad 9 one, apart from the listed exporter differences
- [x] Re-validate on a converted KiCad 10 scratch v8, with `KICAD_CLI` on 10, through the harness `--root`. Run every `v8_*.py --check`; `tidy_fields.py --check` and `tidy_labels.py --check` (0 to do); `layout_check.py` (its geometry is calibrated on kicad-cli 9 SVG plots, so re-check the calibration on 10 plots and fix it if they differ); `extract.py --check-sheet-pins` (0 offenders); `annotate.py`; `show.py`. ERC is listed against the freeze counts (PLAN "Migrating v8"), with setup items separate
- [x] `STOCK_SYMBOLS` follows `KICAD_CLI`. Check whether KiCad 10's stock symbols change what `tidy_fields` or the generators produce, and explain each difference. Generate one sheet with each generator into scratch, convert it, and run ERC on 10 (evidence: SESSION Worker #13 Notes task 3; the KiCad 10-stock-into-KiCad 9 finding closed by the kicad_io embedded-symbol check, `a757e18`)
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 13: Board tools and the write path on KiCad 10

- [x] `board_model.py` and the reports on scratch v7 converted to 10, with `KICAD_CLI` on 10. Compare with the KiCad 9 model: identical, or each difference explained by the format (Phase 3: NPTH `*.Cu`, a keepout zone with no net, the DRC block, the R2 field-parity item). Probe-points `pads` and `render` on 10: the markers are still on their pads (look at the PNG)
- [x] OQ-3 probe (PLAN "Board write path"), both candidates: `pcbnew` from KiCad 10's bundled Python, and kicad-tools' board save through the I/O module. Record the paths and results in PLAN. Strike OQ-3, stating the recommended path for v8 Phase 13 and what changes at KiCad 11
- [x] 🔄 Handoff

# --- handoff point ---

## Phase 14: Migrate v8 to KiCad 10

- [x] Before G3: list the libraries v8 resolves only through KiCad 9's global tables, with the two ways KiCad 10 could resolve them (PLAN "Migrating v8")
- [x] **G3 (user):** approve the migration, and answer OQ-4 (freeze tag) and the library-table question. Record all three in PLAN
- [x] KiCad is closed (no `~*.lck`). Tag `v8-schematic-freeze-k9` on the `v8-schematic-freeze` commit. Convert `hardware/pcb-main-v8/kicad/` (schematic, board, project) to KiCad 10 by Phase 1's method, and apply the library-table answer. Only those files change (check `git status`; nothing under `hardware/pcb-main/`, other boards or `lab/`)
- [x] Gate (PLAN "Migrating v8"). The netlist is structurally identical to 9.0.4 at `v8-schematic-freeze`. ERC has 0 errors, and its warnings are listed against the freeze counts. Every `v8_*.py --check` passes. `layout_check` is re-baselined, with each change explained. `extract.py --previous` reports no structural changes. `--check-sheet-pins` has 0 offenders. `check_state.py --fresh` reports FRESH. Commit, then cut the tag chosen at G3
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 15: Live IPC trial (kipy)

- [ ] kipy in its own venv (scratchpad, or gitignored under `tools/`). **(user)** enables the API server in KiCad 10 (Preferences → Plugins) and opens a scratch KiCad-10 copy of v7's board. Never the working tree
- [ ] Run the trial task (PLAN "Trials") while the user watches: list the footprints, move three named footprints, rotate one, read back. Then the user moves one part and the script reads that correction back. Record the time per call, any busy or timeout failures, and whether the board on disk matches after the user saves
- [ ] **G4 (user):** keep or drop, with the evidence. If kept: where it fits in v8 (W4–W6 and/or v8 Phase 16) and a tools/CONTEXT.md line. If dropped: a line in PLAN Rejected Approaches
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 16: MCP server trial

- [ ] Ask OQ-5 (which server; PLAN recommends kicad-mcp-pro and lists kicad-tools' `kct mcp serve` as an option), then record the answer. Install it pinned to a release, configured project-local for the trial only, with the read-only profile first
- [ ] The same trial task as Phase 15, on a fresh scratch copy, with the same measurements. Also count the tool calls and tokens per task, against Phase 15's script
- [ ] **G5 (user):** keep or drop, with the evidence side by side with Phase 15. If dropped, remove the server config and add a Rejected Approaches line. If kept, its config is committed and a tools/CONTEXT.md line says what it's for and what it may write
- [ ] 🔄 Handoff

# --- handoff point ---

## Phase 17: Docs and close

- [ ] `tools/CONTEXT.md`: the KiCad version and `KICAD_CLI`, the board write path, and the trial outcomes. Check the parser rule (Phase 11) still holds. Check `tools/schematic-modify/CONTEXT.md` and `tools/pcb-context/README.md` against what Phases 12–13 changed
- [ ] `.context/HAZARDS.md`: add "files saved by KiCad 10 can't be opened by 9; never open v7 (`hardware/pcb-main/kicad/`) in KiCad 10 and save", and any trap found in Phases 4–16. `hardware/CONTEXT.md`: note which boards are in which KiCad format. `.context/PROJECT.md` Development Environment: the KiCad version
- [ ] v8 resume note in SESSION.md for the v8 Planner replan. It covers the v8 BRIEF Constraints line (toolchain), v8 PLAN OQ-3's answer and the "AI layout tooling" path, the parser change (kicad-tools via the I/O module), the changes to v8 Phases 13 and 16 from G4/G5, and the freeze-tag name. Merge `feat/kicad10-tooling` into `feat/v8-debug-board`
- [ ] 🔄 Handoff

## Deferred

[from: kicad10-tooling] Uninstall KiCad 9.0.4 once v8 has placed its first block on 10 (OQ-6).
[from: kicad10-tooling] Migrating the sensor-rigid, sensor-flex and power-supply projects to KiCad 10 when they next get design work. v7 is never migrated.
[from: kicad10-tooling] Regenerate v7's committed `hardware/pcb-main/kicad/board-model/` with the ported reader: it would change `connect_pads` on 5 zones and the F.Cu rectangle's copper polygon (PLAN E1). Only with the user's and the v7-i2c Debugger's agreement, since lab work cites it.
[from: kicad10-tooling] KiCad 11 (around early 2027): headless IPC and the schematic API, and `pcbnew` removed. Revisit the board writer then (OQ-3's kicad-tools candidate), and re-check the pinned kicad-tools against KiCad 11 files with the regression harness.
[from: kicad10-tooling] The three `tools/schematic-gen` generators default `--output` into v7's project folder (`hardware/pcb-main/kicad/`, never re-saved), and `spec.json`/`poc_generate.py` still name `3v3_Power_Supply.kicad_sch`, deleted in `fd632ef` (Phase 9 restored it into scratch from `fd632ef^`). Make `--output` required and refresh the sources, or retire the generators.
[from: kicad10-tooling] `tools/pcb-context/place_power.py` writes footprint positions into a `.kicad_pcb` by text replacement, outside `kicad_io` and its lock guard (tools/CONTEXT.md I/O-module Rule, exception). Port it onto `kicad_io` or retire it when v8 placement generalises it.

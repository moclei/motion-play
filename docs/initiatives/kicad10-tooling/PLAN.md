# KiCad 10 Tooling — Plan

## Approach

Change one thing at a time, and compare each step against a baseline taken before it.

1. **Install and baseline (KiCad 9 still the reference).** KiCad 10.0.8 goes in next to 9.0.4. Then the tools run on the current Python 3.7 against KiCad 9 to record reference outputs. They run again on the candidate Python, still against KiCad 9 files. That separates the Python change from the KiCad change.
2. **KiCad 10 file compatibility (Phase 3; Python parity is Phase 2).** Scratch copies of v8 and v7 are converted to the KiCad 10 format. KiCad 10's netlist is checked against KiCad 9's. kiutils (with the `kiutils_k9` shim) round-trips the KiCad 10 files, and every token it drops is counted, as Phase 11a of v8-debug-board did for KiCad 9. That evidence decides whether to extend the shim or replace kiutils (user gate G2).
3. **Re-validate the tools.** The schematic tools first, then `pcb-context` and the board write path (OQ-3). Every `--check` chain runs on the KiCad 10 scratch copy of v8. The gate is the same as v8 Phase 11a: an identical netlist (only the date, tool-version and file-format lines may change), ERC errors unchanged, and layout_check at or below its baseline.
4. **Migrate v8 (user gate G3).** Only after the tools pass on a scratch copy. The project files are converted on the branch, the checks are re-baselined, circuit-context is re-extracted, and a KiCad-10 freeze tag is cut.
5. **Trials (gates G4, G5).** Live IPC through kipy, then one MCP server. Both run on scratch copies and on the same small task, so they can be compared. Each ends in keep or drop.
6. **Close.** Docs, hazards, and a v8 resume note for the Planner.

## Technical Notes

**Sources (cite, don't recall).** `docs/research/kicad-ai-tooling-2026-11/landscape.md` (§2 tools table, §3 comparison, §4 risks, §5 shortlist) and `schematic-readability.md` (§1 the kiutils `(hide yes)` loss and its counting method; prototypes in `prototypes/`). `tools/CONTEXT.md` (Critical, kiutils and Source-Hash rules). `tools/schematic-modify/CONTEXT.md`, `tools/schematic-context/README.md`, `tools/pcb-context/README.md`. `.context/HAZARDS.md` kiutils entry. v8-debug-board PLAN: "AI layout tooling", OQ-3, OQ-11, Rejected Approaches. v8-debug-board SESSION: Worker #12 Notes (round-trip method and counts), "Replan — board write path" and Worker #19 Notes.

**Branch.** v8's tooling (Phases 11a–12a) isn't on `main` yet. So this initiative's branch, `feat/kicad10-tooling`, is cut from `feat/v8-debug-board` at its head. At close it's merged back into `feat/v8-debug-board` (fast-forward if v8 hasn't moved), and v8 resumes there.

**Install, side by side (G1, a user step).** KiCad 10.0.8 macOS dmg, installed to `/Applications/KiCad10/KiCad.app`. 9.0.4 stays at `/Applications/KiCad/KiCad.app`. KiCad keeps per-version settings folders (`~/Library/Preferences/kicad/9.0` and `/10.0`), so 9 keeps working unchanged. Phase 1 confirms this on the machine. The tools take the kicad-cli path from one place, `KICAD_CLI` (env var, falling back to a default). Tools that hard-code `/Applications/KiCad/KiCad.app/...` today are found by grep and changed to read it. Rollback means pointing `KICAD_CLI` back at 9.0.4 and checking out the pre-migration tag. Phase 1 tests that rollback once.

**Python (OQ-1).** Today: pyenv 3.7.3 (EOL), with kiutils 1.4.8, shapely 2.0.7, numpy 1.21.6, PyYAML, Pillow and matplotlib. Candidate: a venv for the KiCad tools only (`tools/.venv`, gitignored, built from a committed `tools/requirements.txt`) on `/usr/local/bin/python3.13`. The global `python3` and the lab pre-commit hook don't change. Parity test on KiCad 9 files: every `--check` chain, `extract.py`, the board model and its reports, and the probe-points `pads` output, under 3.7 and under 3.13. Outputs must be identical. Board-model numbers may differ only within the float tolerance that Phase 2 states and records. The pcbnew writer (OQ-3) runs on KiCad's bundled Python, whatever is chosen here. Replacing kiutils with kicad-sch-api or kicad-tools needs 3.10+, so 3.13 keeps that option open.

**Converting the format.** Phase 1 checks whether KiCad 10's kicad-cli has an upgrade command for schematics and boards. If it doesn't, conversion is a user step: open a scratch copy in KiCad 10 and save it, with exact instructions. Either way, scratch copies live in the session scratchpad and are never made from v7's working tree by a GUI open. Make them with `git archive c2acffc hardware/pcb-main/kicad | tar -x -C <scratch>`.

**Round-trip survey (Phase 3).** The same method as v8 Worker #12: count each token kind (hide, uuid, locked, free, fields_autoplaced, embedded_fonts, exclude_from_sim, and any token new in KiCad 10) before and after a load + save. Also compare the netlist and the plotted strings per sheet. Do this for v8's five sheets and for the board (v8 is outline-only, so also v7's populated board, converted in scratch). The result is a table in SESSION.md with a shim-or-replace recommendation.

**Board write path (OQ-3 on KiCad 10).** Repeat the v8 Planner probe with KiCad 10's bundled Python and `pcbnew` on scratch v7 converted to 10. A load + save must be byte-identical. Moving, rotating and flipping C9 must give a board that kicad-cli 10 loads and runs DRC on. `pcbnew` is still in 10 and removed in 11, so the writer stays one module behind a narrow interface, as the v8 PLAN describes. This phase answers the question but doesn't build `pcb_write.py`; that stays v8 Phase 13's job.

**Trials (bounded: one session each, scratch copies only).** The same task in both, so they can be compared. On a scratch KiCad-10 copy of v7's board open in the KiCad 10 GUI: read the footprint list, move three named footprints, rotate one, and read the result back, while the user watches. Measure: did it work, how long each call took, and how often a call failed with KiCad busy. Did the board on disk match after the user saved? Would it fit the W4–W6 review loop (AI proposes, user watches and corrects, AI reads the corrections back)?
- **IPC:** kipy (kicad-python) in its own venv, with the API server enabled in KiCad 10 (Preferences → Plugins).
- **MCP:** one server, configured project-local for the trial and removed if dropped (OQ-5).
- "Keep" means a named place in v8's workflow (W4–W6, Phase 16) and a line in tools/CONTEXT.md. "Drop" means a line in Rejected Approaches with the evidence.

**Migrating v8 (G3).** Gate: kicad-cli 10's netlist of the migrated v8 is identical to kicad-cli 9's netlist at `v8-schematic-freeze`, apart from the header lines. ERC: errors stay at 0, and every warning count is listed next to the 9.0.4 counts (81 pin_to_pin, 3 lib_symbol_mismatch, 2 lib_symbol_issues, 1 unconnected_wire_endpoint per v8 SESSION Worker #12). `layout_check.py` is re-baselined; any change to the baseline is explained. `extract.py --previous` must report no structural changes, and `--check-sheet-pins` 0 offenders. `check_state.py --fresh` must report FRESH. Tag `v8-schematic-freeze-k9` on the pre-migration commit (the same commit as `v8-schematic-freeze`) for rollback.

**User gates.**
- **G1:** KiCad 10.0.8 installed side by side (Phase 1).
- **G2:** parser and Python decision: extend the shim or replace kiutils, and 3.13 venv or stay on 3.7 (end of Phase 3). If the answer is "replace", come back to the Planner before Phase 4: a port of every tool needs its own phases.
- **G3:** approve the v8 migration and the freeze-tag answer (start of Phase 6).
- **G4:** IPC keep or drop (Phase 7).
- **G5:** MCP keep or drop (Phase 8).

## Rejected Approaches
- Replan inside v8-debug-board: the tooling serves every board, v8's BRIEF constraint line would have to change from inside v8, and its SESSION and TASKS are already long. The user chose a new initiative (2026-11-07).
- Upgrading KiCad in place (replacing 9.0.4): no rollback, and KiCad-9 baselines couldn't be re-made after the change.
- Migrating every board to KiCad 10 now: v7 can't be re-saved, and the sensor and power-supply boards have no active work. The tools must keep reading KiCad 9 files instead.
- Switching the global `python3` to 3.13: the lab pre-commit hook and lab tools run on it, so it would be an unrelated risk. Use a tools-only venv.

## Open Questions
- OQ-1 (G2): Python runtime for the KiCad tools. Recommended: a 3.13 venv, if Phase 2 parity holds.
- OQ-2 (G2): kiutils on KiCad 10 files: extend the shim (`kiutils_k9.py` → a version-aware shim), or replace it (kicad-sch-api for schematics, kicad-tools' round-trip parser)? Decided from the Phase 3 loss table. Shim if the losses are a handful of flags, as on 9. Replace if structure is lost or kiutils fails to parse.
- OQ-3 (Phase 5): the board write path on KiCad 10. Expected: KiCad 10's bundled `pcbnew`, if the probe repeats. The answer goes back to v8 PLAN OQ-3 when v8 resumes.
- OQ-4 (G3): freeze tag. Recommended: a new tag `v8-schematic-freeze-k10` on the migration commit becomes the reference for v8 work. `v8-schematic-freeze` stays as the KiCad-9 record (tags are history), with the alias `v8-schematic-freeze-k9` on the same commit.
- OQ-5 (Phase 8 start): which MCP server to trial. Recommended: kicad-mcp-pro. It needs KiCad 10, works through IPC, and is read-only by default with gated writes. That makes it a direct comparison with Phase 7: a wrapper against plain kipy scripts. The alternative is mixelpixx KiCAD-MCP-Server (more popular, mostly SWIG and file edits). Landscape §4 evidence: MCP wrappers can do worse than an agent writing scripts.
- OQ-6 (at close): when to uninstall KiCad 9. Not before v8 has placed its first block on 10 (Deferred).

# Session Log — kicad10-tooling

## 2026-11-10 — orchestration run 1

Entry conditions: started from `RELAY-orchestrator.md`. Branch `feat/kicad10-tooling` cut from `feat/v8-debug-board` at `e8e739e`. Build passing on KiCad 9.0.4 (per relay). TASKS.md Phases 1–9 all `[ ]`. PLAN OQ-1 to OQ-5 are each scheduled to a later phase or gate, and none blocks Phase 1, so the loop proceeds.

G1 was done by the user before the first dispatch. The Orchestrator checked it on the machine:
- `/Applications/KiCad10/KiCad.app/Contents/MacOS/kicad-cli version` → `10.0.8` (signed, TeamIdentifier 9FQDHNY6U2). `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli version` → `9.0.4`.
- `~/Library/Preferences/kicad/10.0` was created on 2026-11-10 at 16:13 and holds `kicad.json`, `kicad_common.json` and `colors/`. It has no lib tables yet, and its `file_history` is empty, so no project was opened.
- No file under `~/Library/Preferences/kicad/9.0` is newer than 2026-11-07 (latest is `kicad_common.json`, Nov 7 21:35). No before-listing was taken, so the mtimes stand in for one.
- `git status` was clean. The `~*.lck` files under `hardware/pcb-main/kicad/` and `hardware/pcb-power-supply/kicad/` date from 2025, are gitignored and are stale. No KiCad process was running.

---

### Worker #1 — Phase 1: Install side by side, one kicad-cli path, KiCad 9 baselines

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 1 — Install side by side, one kicad-cli path, KiCad 9 baselines
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: SESSION.md "orchestration run 1" entry conditions (G1 evidence). .context/HAZARDS.md kiutils entry. tools/CONTEXT.md (Critical, kiutils, Source-Hash rules). v8-debug-board SESSION.md: grep only; Worker #12 Notes (line ~814) for the KiCad 9 ERC counts and method, Worker #19 Notes (line ~1538) for the sheet-pin check.

Tasks assigned: Phase 1, all 7 tasks (see TASKS.md)

G1 note: the user already installed KiCad 10.0.8. The Orchestrator verified it (SESSION.md entry conditions). For the G1 task, record that evidence and check it off; don't write install steps. Task 1 (confirm 10.0.8 is the current stable release) still runs, and if a newer 10.0.x exists, report it and don't install anything.

Rules: v7 files at hardware/pcb-main/kicad/ are never opened or saved by KiCad 10; scratch copies come from `git archive c2acffc`. lab/ is read-only. Nothing under hardware/pcb-main-v8/ changes. Reference outputs go to the session scratchpad, not the repo. At handoff, git status shows no change under hardware/ or lab/.
```

#### Notes

**KiCad 9 reference run (task 5).** All outputs are in the session scratchpad, at `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/k9-ref/` (`v8/`, `v7/`, the sources in `v8src/` and `v7src/`, and `HASHES.txt`). The hash script is `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/scripts/refhash.py` (run it as `python3 -I refhash.py <scratch root> <files>`). Hashes are the first 16 hex characters of sha256 after normalizing: netlists drop the `source`, `date` and `tool` lines; JSON drops the top-level `_provenance`; Markdown drops the front matter; and the scratch root is replaced by `<ROOT>` in all of them. A second run of the board model and of the netlist gave the same hashes, so the reference is deterministic.

- **Sources.** v8: `git archive v8-schematic-freeze hardware/pcb-main-v8/kicad hardware/pcb-main/resources`. v7: `git archive c2acffc hardware/pcb-main/kicad hardware/pcb-main/resources`. **A scratch copy needs `hardware/pcb-main/resources` at the same relative path.** v8's and v7's lib tables point at `${KIPRJMOD}/../../pcb-main/resources/` (v7: `../resources/`). Without it, ERC on v8 gains 4 `footprint_link_issues` and 2 `lib_symbol_issues`, and v7's DRC gains 5 warnings.
- **v8 netlist** (kicad-cli 9.0.4): 296 components, 158 nets (the `(net` / `<net` count, which includes the unconnected-* stubs). Hashes: s-expression `4d12a57a8f5dedbf`, kicadxml `2002f89e22294468`.
- **v8 ERC** (`--severity-all`, counted per (severity, type) over every sheet, as in `v8_debug_sheet.erc_summary`): 0 errors; warnings 81 `pin_to_pin` and 2 `lib_symbol_issues` (J7's `USB-C_SMD-TYPE-C-31-M-12` and U5's `BQ24195RGET` aren't in the lib table). This matches the freeze record (v8 SESSION line ~1465). **PLAN "Migrating v8" quotes Worker #12's Phase 11a counts (81 / 3 lib_symbol_mismatch / 2 / 1 unconnected_wire_endpoint); the baseline at the freeze tag is 81 pin_to_pin + 2 lib_symbol_issues.** Phase 6 should gate against the freeze numbers.
- **v8 checks**, all exit 0: `v8_debug_sheet.py --check` PHASE 11 CHECK PASSED; `layout_check.py` LAYOUT CHECK PASSED with overlaps root 4, LED 3, MCU 13, power 19, TCA 6 (45), stacked labels 0; `extract.py --check-sheet-pins` 42 pins, 0 offenders; `tidy_fields.py --check` all zeros; `tidy_labels.py --check` all zeros (overlaps 4/3/13/19/6 before and after). `v8_debug_sheet.py --check` and `layout_check.py` ran on the working tree, because they're hard-wired to repo paths. The v8 `.kicad_*` files there are byte-identical to the tag (`git diff v8-schematic-freeze` covers only `circuit-context.json` and REVIEW-GUIDE). **`layout_check.py --root <scratch copy>` fails**: its baseline is keyed by the repo-relative sheet path, so a scratch copy has no baseline ("overlaps 4 > baseline 0"). Phase 3 needs a way to point the baseline at a scratch copy, or it has to compare the counts by hand.
- **v7 board model** (`board_model.py --source-ref c2acffc`, DRC by kicad-cli 9.0.4): 93 footprints, 362 pads, 102 nets, 855 segments, 224 vias, 8 zones, no warnings. DRC: 20 violations (16 clearance and 2 hole_clearance errors, 2 padstack warnings), 0 unconnected, schematic parity 0. Hash `cc6589ad872205a1`.
- **v7 reports**: `net_report.py` (8 full blocks, 102 nets) json `b5ae052ac509f98f`, md `3a4bed9e52025bda`; `plane_report.py` json `491f464b93d5f9df`, md `8b16a7bc9620600b`.
- **v7 probe-points** `pads --board <scratch v7> U5 C21 C9`: hash `3ce3e444257eb167`.
- **Source hashes** (sha256, first 16): v7 board `ff6857d0bf797fc7`; v8 sheets: root `d65c086f4f3cc546`, MCU `9d0381f41bada0a3`, LED `6b7e283afc65573b`, power `ea7569f3da49dff5`, TCA `27f8d853f994cc7d`.

**Rollback drill (task 6).** On the scratch v8 copy (`k9-ref/v8src`), with `KICAD_CLI=/Applications/KiCad10/KiCad.app/Contents/MacOS/kicad-cli` (reports 10.0.8): netlist export exit 0 (302 `(comp` lines and 158 nets in KiCad 10's tab-indented format, header `(version "E")`, `(tool "Eeschema 10.0.8")`); `modify.KICAD_CLI` resolved to the KiCad 10 path; `extract.py --check-sheet-pins` passed (42 pins, 0 offenders). Then `KICAD_CLI` set back to 9.0.4 (reports 9.0.4): netlist export exit 0, normalized hash `4d12a57a8f5dedbf`, the same as the task 5 reference, and `modify.KICAD_CLI` back on the 9.0.4 path. Outputs: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/rollback/`. The two netlists weren't compared to each other; that's Phase 3.
- **Trap found: kicad-cli 10 writes a `.kicad_prl`.** The drill left a new `motion-play-main-v8.kicad_prl` in the scratch copy. A separate probe (`scratchpad/prl-probe/`) isolated it: kicad-cli 10 `sch export netlist` creates the `.kicad_prl` when there's none and rewrites an existing one (sha1 `2fb4508c…` → `ef4a26ce…` for a copy of v8's working-tree prl), and kicad-cli 9 creates nothing. The file is gitignored, so `git status` doesn't show it. The working-tree prl files of v8 and v7 are untouched (mtimes Nov 4 and Apr 7). Added to `.context/HAZARDS.md`. The reference sources in `k9-ref/v8src` now include that prl, so Phase 2 should make fresh copies rather than reuse `k9-ref/v8src` (the `.kicad_sch` hashes are unchanged).

**Release check (task 1).** kicad.org/download/macos on 2026-11-10: "Current Version: 10.0.8". No newer 10.0.x, so 10.0.8 stays pinned. Nothing installed.

**G1 (task 2).** Cites the Orchestrator's evidence above. Re-run: `/Applications/KiCad10/KiCad.app/Contents/MacOS/kicad-cli version` → 10.0.8; `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli version` → 9.0.4. A listing of `~/Library/Preferences/kicad/9.0` taken at the start of this dispatch (`scratchpad/prefs9_listing_phase1.txt`) is identical at handoff, after every kicad-cli 10 run in this phase. kicad-cli 10 runs wrote `3d_viewer.json`, `cvpcb.json`, `eeschema.json`, `fpedit.json`, `pcbnew.json` and `symbol_editor.json` into `~/Library/Preferences/kicad/10.0` (16:17). That folder still has **no global `sym-lib-table` or `fp-lib-table`**, so kicad-cli 10 resolves only the project lib tables. Phase 3's ERC on 10 may report library issues that 9 doesn't for that reason alone. Check it before blaming the format.

**One kicad-cli path (task 3, `d18b5be`).** Hard-coded app paths were in `v8_project_setup.py`, `v8_mcu_sheet.py` (kicad-cli and stock symbols) and `tidy_fields.py` (stock symbols). `tools/schematic-modify/modify.py` now holds `KICAD_CLI` (`$KICAD_CLI`, else the 9.0.4 path) and `STOCK_SYMBOLS`, which is the same install's `Contents/SharedSupport/symbols`. So pointing `KICAD_CLI` at 10 also switches the stock symbol libraries that `tidy_fields` and `v8_mcu_sheet` read. That's intended (one install, one place), and Phase 4 should know it. `v8_debug_sheet.py` already used `v8_mcu_sheet.KICAD_CLI`. `extract.py`, `board_model.py` and `probe_points.py` already read `KICAD_CLI` with a 9.0.4 fallback and are unchanged. Proof of no behaviour change on 9: the six schematic `--check` outputs (`v8_debug_sheet`, `v8_power_sheet`, `v8_bus_sheet`, `v8_mcu_sheet`, `tidy_fields`, `tidy_labels`) are byte-identical before and after the edit (`scratchpad/pre-edit-k9/` vs `post-edit-k9/`), all exit 0, and `extract.py --check-sheet-pins` passes. The READMEs that name the 9.0.4 path (`tools/schematic-context/README.md`, `tools/lab/probe_points/README.md`) already mention `KICAD_CLI` and are left for Phase 9.

**Upgrade command (task 4, `9c76c80`).** kicad-cli 10 has `sch upgrade` and `pcb upgrade` (9.0.4 has neither). They work in place, and `sch upgrade` converts only the file it's given. Details are in PLAN "Converting the format". The probe copy is at `scratchpad/upgrade-probe/`. Its upgraded netlist is there too, but it wasn't compared to anything (that's Phase 3).

**For the next session.**
- Phase 6's ERC gate in PLAN "Migrating v8" quotes Phase 11a counts. The freeze baseline is 81 pin_to_pin + 2 lib_symbol_issues, 0 errors (task 5 above). That's for the Orchestrator or Planner to correct in PLAN; I didn't edit it.
- `layout_check.py` can't check a scratch copy against its baseline (the baseline is keyed by repo-relative path). Phase 3 needs a way around that.
- Scratch copies need `hardware/pcb-main/resources` (task 5 above).
- Make fresh scratch copies; don't reuse `k9-ref/v8src`, which picked up a kicad-cli-10 `.kicad_prl`.

**Handoff checks.** `git status` is clean. `git diff d7a299e HEAD -- hardware lab` is empty, and the working-tree `.kicad_prl` files are untouched. Global python3 and `.githooks/pre-commit` are unchanged. No new documents. HAZARDS gained one entry (kicad-cli 10 `.kicad_prl`). Nothing Deferred.

#### Result
| # | Phase | Result | Commit | Notes |
|---|-------|--------|--------|-------|
| 1 | Phase 1: install, one kicad-cli path, KiCad 9 baselines | DONE | see the handoff commit | 10.0.8 is current; KICAD_CLI in every tool; `sch/pcb upgrade` exist; reference run in the scratchpad; rollback drill OK; one new hazard |

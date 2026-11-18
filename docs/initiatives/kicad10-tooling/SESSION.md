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

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 1 | Phase 1: Install side by side, one kicad-cli path, KiCad 9 baselines | DONE | No — clean completion | 36c561b | 7 tasks; 10.0.8 is current; kicad-cli 10 has `sch/pcb upgrade` |

#### Verification
- 7 commits, `9eda0cc`..`36c561b`. Phase 1 is all `[x]` and Phases 2–9 are all `[ ]` (the Worker's slip on the later Handoff boxes was reverted in `36c561b`). PLAN has no date-stamped headings. Only "Converting the format" changed, and that edit was in scope for the task.
- `git diff d7a299e HEAD -- hardware lab` is empty. The Orchestrator re-ran `v8_debug_sheet.py --check` at HEAD with `KICAD_CLI` unset (9.0.4 fallback): LAYOUT CHECK PASSED, PHASE 11 CHECK PASSED, and the tree is clean afterwards.
- Read the tool diff. `modify.py` owns `KICAD_CLI` and `STOCK_SYMBOLS` (derived from the same install). `tidy_fields.py` and `v8_mcu_sheet.py` import them, and `v8_project_setup.py` reads the env var itself. The fallback is 9.0.4, as the task asked.
- Carry forward:
  - **PLAN "Migrating v8" quotes stale ERC warning counts** (81/3/2/1, from Phase 11a). At `v8-schematic-freeze` they are 0 errors, 81 pin_to_pin and 2 lib_symbol_issues. PLAN belongs to the Planner, so it isn't edited here. The Phase 6 dispatch will cite the freeze-record counts, and the next Planner touch corrects PLAN.
  - **`layout_check.py --root <scratch>` has no baseline**, because its baseline is keyed by the path inside the repo. The Phase 3 and 4 dispatches must say how a scratch copy is checked against the baseline.
  - **kicad-cli 10 writes `.kicad_prl` on read-only commands** (now in HAZARDS). Every scratch copy is fresh, and kicad-cli 10 never runs inside a KiCad 9 project folder.
  - **Scratch copies need `hardware/pcb-main/resources` placed beside them.** KiCad 10 also has no global library tables, so ERC/DRC on 10 can show library issues that come from the setup, not the files.
  - **`STOCK_SYMBOLS` follows `KICAD_CLI`.** Phase 4 must check whether the KiCad 10 stock symbols change what `tidy_fields` or the generators produce.
- Phase 2's reference set: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/k9-ref/` (`HASHES.txt`), hashed with `scratchpad/scripts/refhash.py`.

---

### Worker #2 — Phase 2: Python runtime parity (still KiCad 9)

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 2 — Python runtime parity (still KiCad 9)
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: SESSION.md, Worker #1 Notes and the Orchestrator's Verification under it. The .context/HAZARDS.md pip/matplotlib entry. tools/pcb-context/requirements.txt.

Tasks assigned: Phase 2, all 4 tasks (see TASKS.md)

Notes: the KiCad 9 reference set is in scratchpad/k9-ref/ (HASHES.txt), hashed with scratchpad/scripts/refhash.py. Re-run it from fresh scratch copies; don't reuse k9-ref/v8src, because the rollback drill left a kicad-cli-10 .kicad_prl in it. Leave KICAD_CLI unset (9.0.4) for this whole phase. The global python3, its site-packages and .githooks/pre-commit don't change. Install only into tools/.venv. Make sure tools/.venv is gitignored before creating it. If a tool must change to run on 3.13, it must still give identical output on 3.7: show both.
Rules: as for Phase 1. hardware/ and lab/ unchanged at handoff.
```

#### Notes

**Parity result (task 3): the Python 3.13 venv reproduces the KiCad 9 reference set exactly.** KiCad 9.0.4 throughout (`KICAD_CLI` unset). All 21 entries of `k9-ref/HASHES.txt` match under 3.13.3 (`tools/.venv`) and, in a parallel run, under the global 3.7.3, after one tool fix (below). Run folders: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p2-313/` (3.13) and `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p2-037/` (3.7), each with its own `HASHES.txt`. Runner: `scratchpad/scripts/run_refset.sh <python> <run root>` (fresh `git archive` copies of v8 at `v8-schematic-freeze` and v7 at `c2acffc`, each with `hardware/pcb-main/resources`; then every Phase 1 command). Compare: `scratchpad/scripts/cmp_ref.sh <run root>` (refhash + diff against k9-ref) and `scratchpad/scripts/rawcmp.py <root A> <root B>` (raw and JSON leaf-by-leaf).

| Output | 3.13 vs k9-ref | 3.13 vs 3.7 (raw) |
|---|---|---|
| v8 netlist (.net, kicadxml), ERC counts | match | identical apart from the `date` line (kicad-cli, not Python) |
| `extract.py --check-sheet-pins` (42 pins, 0 offenders) | match | identical |
| `layout_check.py` (PASSED, 4/3/13/19/6) and the scratch-root no-baseline run | match | identical |
| `tidy_fields.py --check`, `tidy_labels.py --check` (all 0) | match | identical |
| `v8_debug_sheet.py --check` (PHASE 11 CHECK PASSED) | match after the fix | identical; also identical to Phase 1 `post-edit-k9/` |
| `v8_power_sheet`, `v8_bus_sheet`, `v8_mcu_sheet --check` (extra, not in HASHES) | = Phase 1 `post-edit-k9/` | identical |
| v7 `board-model.json` (93 fp, 362 pads, 102 nets, DRC 18 err / 2 warn) | match | identical bytes apart from `_provenance.generated` |
| v7 net-report and plane-report (.json, .md) | match | identical apart from `generated` and `model_sha256` (the model's timestamp) |
| probe-points `pads U5 C21 C9` | match | identical |

- **Float tolerance.** Stated before comparing: 1e-9 mm on any board-model or report number. Observed: no value outside exact match. The board model has 60,348 float leaves and 965 int leaves, the net report 1,600 floats, the plane report 1,803; every one is equal, and the serialized JSON is byte-identical once the timestamp is removed. No value to list.
- **The one 3.13 incompatibility (`4e1f90c`).** `c.find("fields") or []` tests an ElementTree Element's truth value. From 3.12 that raises a DeprecationWarning, which went to stderr inside `v8_debug_sheet.py --check`'s output and changed its hash (the check itself passed). Fixed in `v8_debug_sheet.py` and the identical line in `v8_project_setup.py` (`... if c.find("fields") is not None else []`). Same behaviour on 3.7: `v8_debug_sheet --check` output is identical on 3.7 and 3.13 and to Phase 1, and `v8_project_setup.load_netlist` on the v8 netlist gives the same result before and after on both (296 components, 158 nets, 2,214 fields, digest `ba5c45da32428e0d`; `scratchpad/p2-fix/`). `v8_project_setup.py --verify` wasn't run (it's hard-wired to the working tree and runs DRC there).
- **Other 3.13 checks.** All 28 `.py` files under `tools/schematic-*`, `tools/pcb-context` and `tools/lab/probe_points` compile on 3.13 with warnings as errors (no invalid-escape SyntaxWarnings). No imports of stdlib modules removed in 3.12/3.13.
- **Trap for anyone repeating this: keep the run root's name the same length as `k9-ref`.** `extract.py` prints the XML netlist's byte count, and the netlist carries the source path three times. A first 3.13 run in `p2-py313/` (two characters longer) differed by 6 bytes on that line only. `p2-313` and `p2-037` are six characters, like `k9-ref`.

**Evidence for OQ-1 beyond the reference set.**
- **Rendered PNGs differ (matplotlib 3.5.3 vs 3.11.2).** `render.py` on the v7 model under each Python (11 PNGs, `p2-313/v7/img` vs `p2-037/v7/img`): same image sizes and same sidecar metadata apart from paths and timestamps, but 0.9–3.1 % of pixels differ. A diff mask (`scratchpad/p2-render/diffmask_I2C_SCL.png`, side by side in `side_I2C_SCL.png`) shows the differences are only text glyphs, label boxes and their leader lines; copper, pads and zones are the same. So images regenerated on 3.13 will not be byte-identical to the committed v7 `hardware/pcb-main/kicad/board-model/img/` PNGs. That's churn, not a content change, but a regeneration on the venv would rewrite every PNG. `render.py` wasn't in the Phase 1 reference set.
- **Package set.** shapely is the same version on both (2.0.7). numpy 1.21.6 → 2.5.4, matplotlib 3.5.3 → 3.11.2, Pillow 9.5.0 → 13.0.0, PyYAML 6.0.1 → 6.0.3; kiutils 1.4.8 on both. Everything installed from wheels with the venv's pip (26.3), with none of the 3.7 pip workaround (HAZARDS pip/matplotlib entry). A second venv built from `tools/requirements.txt` alone gives an identical `pip freeze`, and `pip check` is clean.
- **Not tested here:** `probe_points.py render` (needs Chrome), `annotate.py`, `show.py`, the `schematic-gen` generators and the `--apply` paths. Phase 4/5 re-validate those on KiCad 10.
- **Recommendation for G2:** the 3.13 venv is safe for the KiCad tools: every checked text and JSON output is identical, and only the render PNGs differ in text anti-aliasing and label placement.

**Task 1 (`4c30098`).** `tools/requirements.txt` holds the four direct dependencies plus their transitive dependencies, pinned to what installed on 3.13.3. Its header lists the global 3.7 set for reference. `tools/pcb-context/requirements.txt` and `tools/schematic-context/requirements.txt` (which had kiutils and pyyaml) are now `-r ../requirements.txt` pointers. Installing either pointer on 3.7 will fail on the pins (numpy 2.5.4 has no 3.7 build), and pip resolves the whole set before it installs anything, so the global site-packages can't be changed by mistake. `.gitignore` gained `tools/.venv/`, added and checked with `git check-ignore` before the venv was created. The run instructions in `tools/schematic-context/README.md` ("Python 3.7+", `pip install -r requirements.txt`) and `tools/pcb-context/README.md` aren't changed; the TASKS for Phases 4 and 5 own that.

**Handoff checks.** `git status` is clean after the handoff commit. `git diff 7894745 HEAD -- hardware lab` is empty. The working-tree `.kicad_prl` files are untouched (v8 Nov 4, v7 Apr 7). The global `python3` is still pyenv 3.7.3 with the same package versions, and `.githooks/pre-commit` is unchanged. The 3.13 runs left `cpython-313` `.pyc` files in the tools' `__pycache__/` folders, which are gitignored. No new documents and nothing Deferred.

#### Result
| # | Phase | Result | Commit | Notes |
|---|-------|--------|--------|-------|
| 2 | Phase 2: Python runtime parity (still KiCad 9) | DONE | see the handoff commit | 3.13 venv: 21/21 reference hashes match, board model exact; one fix (Element truthiness); render PNGs differ in text only |

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 2 | Phase 2: Python runtime parity (still KiCad 9) | DONE | No — clean completion | aea1201 | 4 tasks; 21/21 hashes match on 3.13.3; one DeprecationWarning fix |

#### Verification
- 4 commits, `4c30098`..`aea1201`. 11 boxes are `[x]` (Phases 1–2), and Phases 3–9 are untouched. PLAN is unchanged. `git diff 7894745 HEAD -- hardware lab .githooks` is empty.
- Read the diff. The two `find("fields") or []` fixes are behaviour-preserving (an explicit None test). Both old requirements files are `-r ../requirements.txt` pointers, and `tools/.venv/` is gitignored (confirmed with `git check-ignore`). The global `python3` is still pyenv 3.7.3.
- Orchestrator re-run with `KICAD_CLI` unset: `v8_debug_sheet.py --check` gives PHASE 11 CHECK PASSED under `tools/.venv/bin/python -W error::DeprecationWarning` and under the global 3.7.3. The tree is clean afterwards.
- Carry forward:
  - **G2 / OQ-1:** the evidence supports the 3.13 venv. One caveat for the user: `render.py` output on matplotlib 3.11.2 changes text glyph pixels, so regenerating the committed v7 `board-model/img/` PNGs would rewrite every file with no change in content.
  - **The reference-set runner is sensitive to the scratch path's length.** `extract.py` prints the netlist's byte count, so run roots must have names the same length as `k9-ref`.
  - Phase 2 didn't cover `annotate.py`, `show.py`, the generators, the `--apply` paths or `probe_points render`. Phases 4 and 5 re-validate them.

---

### Worker #3 — Phase 3: KiCad 10 file format and the kiutils round-trip survey

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 3 — KiCad 10 file format and the kiutils round-trip survey
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: SESSION.md, the Notes and Orchestrator Verification for Workers #1 and #2. PLAN "Converting the format" and "Round-trip survey". docs/research/kicad-ai-tooling-2026-11/schematic-readability.md §1 (counting method). v8-debug-board SESSION.md Worker #12 Notes (grep, around line 814), for the KiCad 9 round-trip counts. landscape.md §2 (kicad-sch-api, kicad-tools rows).

Tasks assigned: Phase 3, tasks 1–4. Stop before G2 (task 5): the Orchestrator takes the decision to the user. Return PARTIAL at G2; that stop is planned.

Notes: convert with `kicad-cli sch upgrade` (each sheet separately) and `kicad-cli pcb upgrade`, on fresh scratch copies only (HAZARDS: kicad-cli 10 writes .kicad_prl). Put hardware/pcb-main/resources beside each copy. KiCad 10 has no global library tables: separate setup-caused library ERC/DRC items from real ones. Use tools/.venv (3.13) for kiutils; parity is proven. Install kicad-sch-api and kicad-tools into a separate scratch venv, not tools/.venv and not requirements.txt. The ERC reference at v8-schematic-freeze: 0 errors, 81 pin_to_pin, 2 lib_symbol_issues (Phase 1). v7 DRC reference: 20 violations, 0 unconnected.
Rules: as for Phases 1–2. Nothing under hardware/ or lab/ changes. No PLAN edits besides recording facts in Technical Notes, if needed.
```

#### Notes

Scratch root for this phase: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p3/` (`v8k9`, `v7k9` unconverted and run only on kicad-cli 9; `v8k10`, `v7k10` converted; `v8k9x`, `v7k9x` unconverted copies run on kicad-cli 10; outputs in `out/`). Scripts: `scratchpad/scripts3/` (`sexp.py` raw s-expression reader, `netconn.py`, `netsem2.py`, `erc_split.py`, plus the round-trip scripts below). Every copy is a fresh `git archive` (v8 at `v8-schematic-freeze`, v7 at `c2acffc`) with `hardware/pcb-main/resources` beside it.

**Task 1: conversion, netlist, ERC/DRC.**
- **Conversion.** `kicad-cli sch upgrade` on each of the five sheets, then `pcb upgrade` on the board, in both projects (`out/convert.log`). Every sheet 20250114 → 20260306, both boards 20241229 → 20260206, exit 0; a second `sch upgrade` prints "Schematic file was not updated" for all ten sheets. `pcb upgrade` created a `.kicad_prl` and left the `.kicad_pro` untouched, as Phase 1 saw.
- **The conversion itself is netlist-neutral.** kicad-cli 10's netlist of the unconverted copy (`v8k9x`, `v7k9x`) and of the converted copy are byte-identical apart from the `source`, `date` and `tool` lines, in both formats (s-expression and kicadxml), for v8 and v7. ERC and DRC counts are also identical between unconverted and converted on kicad-cli 10. So every difference below comes from kicad-cli 10's exporter and checker, not from the file format.
- **kicad-cli 9 (original) vs kicad-cli 10 (converted): connectivity identical, the text isn't.** A raw diff isn't usable: 10 writes tab-indented, one token per line, and reorders sheets. A structural compare (`netconn.py`): v8 296 components, 158 nets; v7 93 components, 102 nets; 0 components differ (value, footprint, every field, libsource, sheetpath, tstamps, properties) and 0 nets differ (name and node set by ref, pin, pintype, pinfunction) once the items below are accounted for. Exporter differences, each counted (`netsem2.py`):
  - **Every `pinfunction` gets `_<pin number>` appended** (v8 471 of 471, v7 206): `IO48` → `IO48_25`, `Pin_1` → `Pin_1_1`. Also in the kicadxml export. **`tools/schematic-context/extract.py:332` reads `pinfunction` from the XML netlist, so circuit-context pin names will change on 10.** Phase 4 must handle it (strip the suffix or read pin names elsewhere).
  - Net `class`: 9 writes `Default` for all; 10 writes the pattern-assigned classes from the `.kicad_pro` (`Power_Med,Default` etc.): 14 nets in v8, 16 in v7.
  - Root-sheet components' `Sheetname` property: `""` on 9, the project name on 10 (v8 28 components, v7 18).
  - Sheet `number`s follow the sheets' page numbers on 10 (TCA becomes 2, LED 3, Power 4); names and tstamps unchanged.
  - Dropped on 10: `(datasheet "~")` (v8 295, v7 91), the `~` value of the `Datasheet` field (327 / 119) and libpart `(docs "~")`. Added on 10: `(units …)` per component and libpart, and empty `groups` and `variants` sections.
  - `libraries`: 9 lists 18 (v7 14) libraries with absolute URIs; 10 lists 2 (the project-table ones, as `${KIPRJMOD}` URIs), because 10 has no global table.

| ERC (`--severity-all`) | v8 on 9 | v8 on 10 | v7 on 9 | v7 on 10 |
|---|---|---|---|---|
| errors | 0 | 0 | 0 | 0 |
| pin_to_pin | 81 | 81 | 56 | 56 |
| lib_symbol_issues, real (J7 USB-C, U5 BQ24195RGET: in no table) | 2 | 2 | 2 | 2 |
| unconnected_wire_endpoint | 0 | 0 | 1 | 1 |
| same_local_global_label (new check in 10) | – | 5 | – | 3 |
| lib_symbol_issues, setup | 0 | 330 | 0 | 121 |
| footprint_link_issues, setup | 0 | 281 | 0 | 79 |

| DRC (`--severity-all --schematic-parity`) | v8 on 9 | v8 on 10 | v7 on 9 | v7 on 10 |
|---|---|---|---|---|
| clearance / hole_clearance (errors) | 0 / 0 | 0 / 0 | 16 / 2 | 16 / 2 |
| padstack (warning) | 0 | 0 | 2 | 2 |
| invalid_outline (error) | 1 | 1 | 0 | 0 |
| unconnected | 0 | 0 | 0 | 0 |
| schematic parity | 199 (outline-only board) | 199 | 2 | 3 |
| lib_footprint_issues, setup | 0 | 0 | 0 | 79 |

- "Setup" means the library is in KiCad 9's global `sym-lib-table`/`fp-lib-table` and not in the project table, so it resolves on 9 and not on 10 (10 has no global tables yet). Every setup item was checked by name (`erc_split.py`): the stock libraries (`Device`, `power`, `Connector`, `TestPoint`, `Resistor_SMD`, …), the JLC-MCP 3rd-party libraries and `motion-play-symbols`/`-footprints`. Real library items are the same 2 on both versions.
- **New on 10, not setup:** `same_local_global_label` flags a power symbol and a label with the same name on one sheet (v8: `+5V`, `+3.3V_MCU` on root, `+3.3V_BUS` on TCA, `GND` on LED, `+5V_CORE` on power; v7: the root and LED ones). The v7 DRC parity count rises 2 → 3 because 10 compares footprint fields with symbol fields: R2's `ai_block` is `battery_mgmt` in the schematic and empty on the board. Both are warnings that 9 didn't check for, not changes in the design.
- v8 ERC against the freeze baseline (0 errors, 81 pin_to_pin, 2 lib_symbol_issues): unchanged on 10, plus 5 `same_local_global_label` and the setup items. v7 DRC against the reference (20 violations, 0 unconnected): unchanged on 10, plus the setup items and the one field-parity item.

**Task 2: kiutils round-trip survey (kiutils 1.4.8 + `kiutils_k9`, `tools/.venv` 3.13).** Script `scratchpad/scripts3/rt_kiutils.py` (load + save, then a second load + save). Token census `scripts3/tokcount.py`, independent of kiutils: every list counted by head, every flag counted whether written `(x yes)` or bare `x`, `(x no)` counted separately. Then two checks of what KiCad 10 makes of the output: kicad-cli 10's netlist and SVG plot of a project built from the round-tripped sheets (`p3/v8rt`, `p3/v7rt`), and a `sch upgrade --force` re-save of them (`p3/v8up`, `p3/v7up`), whose census against the original shows only what KiCad 10 itself reads differently. Output: `p3/out/rt_tokens.txt`.
- **Load:** all ten converted sheets (v8 and v7) and v8's board load and save. **v7's board does not load:** `IndexError` in `kiutils.items.common.Net.from_sexpr`. KiCad 10 boards have no net table and write every net by name, `(net "/ESP32_S3/EN")`, where kiutils expects `(net 12 "/ESP32_S3/EN")`. Same failure for any populated KiCad 10 board, so `board_model.py` (which reads boards with kiutils) can't read one.
- **Second round trip:** stable for every file that loads (rt1 → rt2 census identical).
- **Schematic census, before → after** (v8, five sheets; v7 the same pattern). Kinds whose count changed:

| Token (KiCad 10 form) | v8 before → after | Matters? (KiCad 10 re-save of the output) |
|---|---|---|
| `(show_name no)` (new in 10, on every property) | 3,854 → 0; kiutils writes a bare `(show_name)` on 3,696 of them | **Yes. kiutils reads the token's presence as true and writes `(show_name)`, which KiCad 10 reads as `show_name yes`.** 3,696 v8 properties (v7: 1,652) come back with their field name shown; the other 158 are re-saved as `no` |
| `(hide yes)` | 2,383 → 0 as a list, written as bare `hide` | No: the hide-flag count is unchanged and KiCad 10 reads bare `hide` as hidden (re-save restores `(hide yes)` on exactly the same items) |
| `(fields_autoplaced yes)` | 334 → written as `(fields_autoplaced)` | No: re-save restores all 334 |
| `(do_not_autoplace no)` | 3,854 → 0 | No: default |
| `(in_pos_files yes)` (new in 10) | 437 → 0 | No: default, re-save restores it |
| `(body_style 1)` (new in 10) | 334 → 0 | No: re-save restores it |
| `(duplicate_pin_numbers_are_jumpers no)` (new in 10) | 103 → 0 | No: default |
| `(exclude_from_sim no)`, `(embedded_fonts no)` | 441, 103 → 0 | No: defaults (as on 9) |
| `(power global)` (new in 10) | 25 → `(power)` | No: re-save restores `global` on all 25 |
| root sheet: `in_bom`/`on_board`/`dnp` on the 4 sheet symbols | 4 each → 0 | No: re-save restores them |
| `generator_version` | 1 per sheet → 0 | No |
| power sheet: 7 `(pin … (uuid …))` entries on J7 (USB-C, duplicate pin numbers) | 481 → 474 | No: re-save re-creates them with new uuids; netlist unchanged (same as on 9) |

- **The KiCad 10 re-save of the round-tripped sheets differs from the original in one thing only: `show_name`** (v8 per sheet: MCU 617, LED 228, root 391, power 1,686, TCA 774; v7: 253 / 134 / 336 / 806 / 123). No other token count changes, and no uuid changes apart from the 7 J7 pin uuids.
- **Netlist:** kicad-cli 10's netlist of the round-tripped projects is byte-identical to the converted originals (apart from source/date/tool), v8 and v7.
- **Plotted strings per sheet** (`scripts3/svgstrings.py`, every `<desc>` text in kicad-cli 10's SVG): v8 root 269 → 280, MCU 537 → 676, LED 154 → 180, power 1,197 → 1,690, TCA 567 → 741 (v7: 162 → 252, 388 → 416, 101 → 161, 610 → 882, 247 → 263). Every visible field is now drawn as "Name: value" ("Reference: C55", "Value: 1µF"), empty visible fields appear as "Description: ", and pin numbers on passives and some pin names appear. **Setting `show_name` back to `no` in the re-saved copy (`p3/v8fix`) gives plotted strings identical to the original on all five sheets**, so `show_name` is the whole visible loss.
- **v8's board** (outline only) loads and saves. Lost: the board-level `tenting`/`covering`/`plugging`/`capping`/`filling` defaults in setup, `allow_soldermask_bridges_in_footprints no`, `legacy_teardrops no`, 15 plot parameters, `embedded_fonts`, `generator_version`. kicad-cli 10 loads the result, DRC is unchanged (1 invalid_outline, 199 parity, 0 unconnected), and a `pcb upgrade --force` re-save has the same census as the original: nothing KiCad 10 doesn't restore.
- **v7's board, after a scratch-only experiment** (`scripts3/rt_board_k10probe.py`, not a proposal): with `Net` patched to read and write `(net "name")`, the board loads (93 footprints, 362 pads, 1,079 track items, 8 zones), but kicad-cli 10 can't load the saved file ("Expecting … uuid … Got 'segment'", line 5104): kiutils writes `(tstamp )` for every track's `uuid`. That is the KiCad 9 board result (v8 Worker #12, OQ-11) again; a board write through kiutils is not viable on either version. **Read path only:** `scripts3/board_readcmp.py` compares what kiutils reads from the KiCad 9 board and from the converted one (with the net patch). Footprints (lib id, position, angle, layer, pad and graphic counts), all 1,079 tracks (geometry, layer, net name) and graphics are identical. Two differences: one NPTH pad's layers read `*.Cu` instead of `F&B.Cu`, and the no-net keepout zone has no `(net …)` token. So a read-only board shim needs: nets by name (no net table), `*.Cu`, and a zone with no net.
- **KiCad 9 files on kicad-cli 10** (the other boards stay on 9). `scratchpad/scripts3/run_k9files_on_k10.sh` runs the Phase 1 tool set on fresh unconverted copies with `KICAD_CLI` pointing at kicad-cli 10 (run root `scratchpad/k10on9/`, same name length as `k9-ref`). Every tool exits as on 9. Hash-identical to `k9-ref`: `tidy_fields --check`, `tidy_labels --check` (both all 0, though `STOCK_SYMBOLS` now points at KiCad 10's libraries), net report and plane report (json and md), probe-points `pads`, and the five source sheets and board (unchanged by the reads). `layout_check --root` (no baseline) differs only in the path line. Different, all from kicad-cli 10 itself: the netlist (task 1 exporter changes); `extract --check-sheet-pins` still 42 pins, 0 offenders, only the netlist byte count changes (536,367 → 571,868); ERC counts (the task 1 setup items and 5 `same_local_global_label`); `board-model.json` is identical apart from its `drc` block, which has the same 20 violations at the same locations plus the 79 setup `lib_footprint_issues` and `kicad_version` 10.0.8. `v8_debug_sheet.py --check` and the `layout_check` default run weren't run, because they're hard-wired to the working tree and kicad-cli 10 must not run there.

**Task 3: kicad-sch-api and kicad-tools, read-only parse test.** Separate scratch venv on 3.13: `scratchpad/venv-alt/` with kicad-sch-api 0.5.6 and kicad-tools 0.29.0 (both MIT, Python ≥ 3.10; landscape §2 saw kicad-tools at 0.27.0 on 2026-10-31, so two minor releases in ten days). Nothing added to `tools/.venv` or `tools/requirements.txt`. Script `scripts3/rt_alt.py`; inputs are the same converted v8 and v7 files, plus v7's unconverted KiCad 9 files. Outputs in `p3/alt/`.
- **kicad-tools: lossless on every file.** Both its raw s-expression layer (`core.sexp_file.load_/save_schematic`, `load_/save_pcb`) and its typed layer (`schema.Schematic`, `schema.PCB` `.load()`/`.save()`) load and save all ten converted sheets, both converted boards, and v7's five KiCad 9 sheets and KiCad 9 board. The output is tree-identical to the input (`scripts3/treeeq.py`: same tokens, same order, quoted vs bare kept) in every case; only whitespace differs (short lists on one line, no final newline), so the files aren't byte-identical and a git diff of a save would be noisy. kicad-cli 10 on projects built from its output (`p3/v8kt`, `p3/v7kt`): netlist byte-identical, plotted strings identical on all ten sheets, DRC identical. Its typed `PCB` reads both v7 boards the same way (93 footprints, 362 pads, 341 with a net, 855 segments, 224 vias, 103 nets), net names included: it builds the net table itself on KiCad 10. It keeps every token kiutils drops, `show_name` included. Weight: 73 packages in the venv (numpy, shapely, rtree, pydantic, rich, …).
- **kicad-sch-api: loads, but a save is destructive.** It loads all ten sheets (with "Library not found" messages for every library outside its search path), then rewrites the embedded library symbols on save. kicad-cli 10 on the saved v8 (`p3/v8ksa`): 296 → 283 components and 158 → 154 nets in the netlist, components re-pointed at renamed library symbols (`Device:C` → `C_1`), the root title-block comments gone, and pin numbers and names missing from the plots. v7: 93 → 79 components, 102 → 63 nets. It writes `show_name no` on only part of the properties (power sheet: 1,427 of 1,740). Rejected as a parser for our files. Side effect: it created an empty `~/.cache/kicad-sch-api/symbols/` folder (outside the repo, not removed).

**Task 4: loss table and recommendation.**

| File (KiCad 10 format) | kiutils 1.4.8 + `kiutils_k9` | kicad-tools 0.29.0 | kicad-sch-api 0.5.6 |
|---|---|---|---|
| v8 sheets ×5, v7 sheets ×5 | Load, save, stable. **One real loss: `(show_name no)` read as true** on every property (v8 3,696, v7 1,652), so field names plot ("Reference: C55"). Every other dropped token is a default or something KiCad 10 restores on re-save (table in task 2). Netlist identical | Tree-identical, whitespace only | Loads; save loses components, nets and library symbols |
| v8 board (outline only) | Load, save; drops setup defaults and plot settings, all restored by KiCad 10; DRC unchanged | Tree-identical | n/a |
| v7 board (populated) | **Doesn't load** (`(net "name")`, no net table). With a net patch it loads, but a save writes `(tstamp )` for track uuids and kicad-cli 10 can't load it (as on 9) | Tree-identical; typed read gives the same nets as on 9 | n/a |
| v7 KiCad 9 files (other boards stay on 9) | As before (Phase 2: shim keeps every flag) | Tree-identical | Same token losses on save as on the converted sheets |

- **Shim check (scratch only, `scripts3/rt_kiutils_showname.py`).** `kiutils_k9` plus one more patch, reading `(show_name no)` as false, closes the schematic loss: kicad-cli 10's netlist is byte-identical, the plotted strings are identical on all ten sheets, and a KiCad 10 re-save of the output has a token census identical to the original on all ten sheets (no kind differs at all).

**Recommendation for OQ-2: extend the shim (version-aware `kiutils_k9`), don't replace kiutils.** PLAN's rule says shim if the losses are a handful of flags and replace if structure is lost or kiutils fails to parse. For schematics it's one flag, and the check above shows one patch fixes it. For boards kiutils does fail to parse, which is the "replace" condition, but only on the read side and only for one token form: board writes through kiutils are already ruled out on 9 and 10 (OQ-11; OQ-3 points at `pcbnew`), and the read path needs three small patches (below), after which footprints, pads, tracks and graphics read the same as on 9. Replacing kiutils with kicad-tools would mean porting every tool that imports kiutils (21 files under `tools/`, the shim included), taking on a fast-moving dependency with 73 packages, and accepting saves that aren't formatted like KiCad's. kicad-tools is the right fallback: it's the only candidate that round-trips every file exactly, and the KiCad 11 revisit (Deferred) is the natural point to reconsider. kicad-sch-api is out. If the user prefers the letter of the rule for boards, the middle option is kicad-tools for board reading only (`pcb-context`), with kiutils plus the shim for schematics.

**What the shim has to cover.**
- Must (schematics): `(show_name no|yes)` on `property`. Without it, every save shows field names.
- Must (board reads, if `board_model.py` and the other `pcb-context` readers stay on kiutils): `(net "name")` on pads, segments, vias, arcs and zones, with no board net table (build one, so the tools' number-to-name lookups keep working); a zone with no `(net …)` (keepouts); NPTH pad layers `*.Cu` where 9 wrote `F&B.Cu`. Board saves stay off kiutils.
- Guard (not present in our files today, but kiutils would silently change them): `(power local)` would be written as `(power)`, which KiCad reads as global, changing connectivity; `(in_pos_files no)`, `(exclude_from_sim yes)`, `(do_not_autoplace yes)` and `(duplicate_pin_numbers_are_jumpers yes)` would be dropped; `(body_style 2)` would be lost (De Morgan bodies); `dnp`/`in_bom`/`on_board` on sheet symbols would revert to defaults. The shim should either carry these or make `save_schematic` refuse when one of them has a non-default value.
- Already fine: `(hide yes)` (bare `hide` is read as hidden on 10), `fields_autoplaced`, `embedded_fonts`, `generator_version`, J7's duplicate-number pin uuids (re-created by KiCad, as on 9).

**Recommendation for OQ-1: the 3.13 venv.** Phase 2 showed parity on KiCad 9 files, kiutils 1.4.8 runs unchanged on 3.13 against KiCad 10 files, and both replacement candidates need Python ≥ 3.10, so staying on 3.7 would also close off the fallback above. The only caveat is Phase 2's: `render.py` PNGs change in text pixels on matplotlib 3.11.

**Found for later phases (not this phase's work).**
- **Phase 4, `extract.py`:** kicad-cli 10 appends `_<pin number>` to every `pinfunction` in the netlist (`IO48` → `IO48_25`), in the s-expression and the kicadxml formats, on KiCad 9 and KiCad 10 files alike. `tools/schematic-context/extract.py:332` reads `pinfunction` from the kicadxml netlist, so circuit-context pin names would change once `KICAD_CLI` points at 10. `--check-sheet-pins` is unaffected (42 pins, 0 offenders on 10).
- **Phase 6 ERC gate:** kicad-cli 10 adds 5 `same_local_global_label` warnings on v8 (power symbol and same-named label on one sheet). They aren't caused by the conversion (same count on the unconverted copy). The gate should list them beside the 9.0.4 counts. The setup library items (330 + 281 on v8) will appear on any ERC run until KiCad 10 has global library tables or the project tables list the stock libraries.
- **Phase 5, DRC parity:** on 10, v7 has one more parity item (R2's `ai_block` field: schematic `battery_mgmt`, board empty). KiCad 10 compares footprint fields with symbol fields.
- **Net classes in the netlist:** 10 writes the pattern-assigned net classes from the `.kicad_pro`; 9 wrote `Default`. No tool reads the netlist class today (grep).

**For the next session.**
- G2 is next and is the user's: OQ-1 and OQ-2, with the evidence above. I didn't touch PLAN's Open Questions.
- If OQ-2 is "shim", Phase 4's first task should start from the "What the shim has to cover" list. `scripts3/rt_kiutils_showname.py` and `scripts3/rt_board_k10probe.py` are scratch experiments, not code to copy: the board probe only quotes net names to measure the rest of the loss.
- The scratch tree `p3/` has every intermediate project (`v8k10`, `v7k10` converted; `*rt` kiutils; `*up` KiCad re-save of the kiutils output; `*kt` kicad-tools; `*ksa` kicad-sch-api; `*sn` the show_name experiment). All are scratch; the scratchpad is temporary.

**Handoff checks.** `git status` shows no change under `hardware/` or `lab/` (`git diff 536954f HEAD -- hardware lab` is empty). kicad-cli 10 ran only on scratch copies; the working-tree `.kicad_prl` files of v8 and v7 are untouched. `tools/.venv` and `tools/requirements.txt` are unchanged; kicad-sch-api and kicad-tools are only in `scratchpad/venv-alt/`. No PLAN edits, no new documents, nothing Deferred. One side effect outside the repo: kicad-sch-api created an empty `~/.cache/kicad-sch-api/symbols/`.

#### Result
| # | Phase | Result | Commit | Notes |
|---|-------|--------|--------|-------|
| 3 | Phase 3: KiCad 10 file format and the kiutils round-trip survey | PARTIAL (stopped at G2 user gate, as planned) | see the last Phase 3 commit | Conversion netlist-neutral; kiutils loses only `show_name` on sheets and can't read populated KiCad 10 boards; kicad-tools lossless; kicad-sch-api destructive; recommend shim + 3.13 venv |

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 3 | Phase 3: KiCad 10 file format and the kiutils round-trip survey | PARTIAL | Yes — resolvable without replanning: the stop is the planned G2 user gate | 18fb84e | Tasks 1–4 done; G2 and Handoff wait on the user |

(The Worker also wrote a Result table inside its own block. The table above is the Orchestrator's record.)

#### Verification
- 5 commits, `cc142e5`..`18fb84e`. Only SESSION.md and TASKS.md changed: `git diff 536954f HEAD -- hardware lab tools` is empty. Tasks 1–4 are `[x]`, and G2 and the Handoff are `[ ]`. PLAN is unchanged.
- Re-derived from the Notes' ERC/DRC table: converting moves no reference count (v8 ERC 0/81/2, v7 DRC 20/0 unconnected). The only new items are ones KiCad 10 added (`same_local_global_label`, the footprint-vs-symbol field parity check) and library items caused by the setup.
- Carry forward:
  - **kicad-cli 10 netlists append `_<pin>` to every `pinfunction`.** `extract.py:332` reads that field, so this goes to Phase 4.
  - **Phase 5 can't run `board_model.py` on a KiCad 10 board** until the shim covers net-by-name, zones with no net and NPTH `*.Cu`.
  - kicad-sch-api left an empty folder outside the repo, `~/.cache/kicad-sch-api/symbols/`. The user is told about it.
- G2 is taken to the user next.

### G2 — user decision (2026-11-10)

- **OQ-1:** the 3.13 venv (`tools/.venv`, built from `tools/requirements.txt`). The user took the recommendation.
- **OQ-2:** full replace with kicad-tools. Before deciding, the user asked for a cost/benefit rundown. The Orchestrator gave one:
  - **For kicad-tools:**
    - It is lossless by design, against the shim's list of known losses, where any loss not yet found is silent.
    - It reads KiCad 10 boards natively.
    - A board save path exists for when `pcbnew` is removed in KiCad 11.
  - **Against:**
    - A port of 20 kiutils-importing files, with every check chain re-validated.
    - The library changes fast (0.27 → 0.29 in ten days, about 8.3k commits, one maintainer) and pulls in 73 packages.
    - Its editing API is untested; Phase 3 tested load and save only.
  - **The framing:** the shim's cost recurs with every KiCad release, and the next forcing point is KiCad 11 (about January 2027).
  - The recommendation was the shim now, with kicad-tools at KiCad 11. The user chose the full replace.
- Per PLAN G2 and TASKS Phase 3 task 5, a "replace" answer goes to the Planner before Phase 4. G2 and the Phase 3 Handoff stay `[ ]` until the Planner records the decisions in PLAN.

[ORCH] Spawning Planner — G2 chose OQ-2 "replace": the kiutils → kicad-tools port needs its own phases before Phase 4

### Planner — replan after G2

[ORCH] Planner → REPLANNED: ready to continue (`0d5b098`)

**Verification:**
- Only PLAN.md and TASKS.md changed. PLAN has no date-stamped headings, and OQ-1 and OQ-2 are struck. G2 and the Phase 3 Handoff are `[x]`.
- The old Phases 4–9 are now Phases 4–17. The port is Phases 4–11:
  - Phase 4: groundwork.
  - Phase 5: API spike, ending at the new gate **G2a** (go/no-go on the port, OQ-7 save formatting, which scripts to retire).
  - Phases 6–10: port by tool group.
  - Phase 11: remove kiutils.
- The KiCad 10 work moves to Phases 12–17: schematic tools, board tools with OQ-3, the v8 migration (**G3**, which now adds a library-table question), the IPC trial (**G4**), the MCP trial (**G5**) and the close.
- BRIEF is unchanged; the Planner confirmed "replace" is inside its goal.
- The stale ERC counts in PLAN "Migrating v8" are corrected.
- About 8 phases are added compared with the shim path. Before Phase 4 is dispatched, the user is shown the new shape.

User approved resuming the loop with the replanned shape ("Go — dispatch Phase 4").

---

### Worker #4 — Phase 4: Port groundwork: harness, scratch-root checks, kicad-tools pinned

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 4 — Port groundwork: harness, scratch-root checks, kicad-tools pinned (still kiutils, KiCad 9)
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN (read in full; it was replanned at 0d5b098), especially "Regression harness", "Scratch roots for the checks", "kicad-tools pin and upgrades". In SESSION.md: Worker #1–#3 Notes and the Orchestrator Verifications (reference hashes, path-length trap, .kicad_prl hazard).

Tasks assigned: Phase 4, all 6 tasks (see TASKS.md)

Notes: the scratchpad reference scripts (scratchpad/scripts/, scripts3/) and k9-ref/HASHES.txt are still present this session. KICAD_CLI stays on 9.0.4 for the whole phase. Cut the `kicad10-preport` tag yourself on the handoff commit (annotated, not pushed).
Rules: hardware/ and lab/ unchanged; the global python3 and .githooks unchanged; kicad-cli 10 never runs on the working tree.
```

#### Notes

Scratch for this phase: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p4/` (before/after outputs, probe venv) and the harness run roots `scratchpad/p4run1`, `p4run2`, `p4wt01`, `p4wt02`. `KICAD_CLI` unset (9.0.4) throughout; kicad-cli 10 never ran.

**Task 1, harness (`123e651`).** `tools/kicad-regress/`: `regress.py` (CLI), `kcompare.py` (ERC counts and setup/real split, structural netlist compare, plotted strings, token census, tree equality, JSON leaf compare), `sexp.py`, `reference-k9.txt`. Rebuilt from the Phase 1–3 scratch scripts, stdlib only (runs on the global 3.7 or the venv). `run <root>` makes fresh `git archive` copies (v8 at `v8-schematic-freeze`, v7 at `c2acffc`, each with `hardware/pcb-main/resources`), runs the Phase 1 set plus every `v8_*.py --check` and `v8_project_setup.py --verify --no-v7-compare` with `--root`, writes `run.json` (settings, exit codes) and `HASHES.txt`. `--python`, `--kicad-cli`, `--tools <ref>` (a detached worktree with only `tools/` and `hardware/pcb-main/resources` checked out, removed after the run). Refuses a run root inside the repo and a run-root name that isn't 6 characters. `compare A B [--tol]` checks exit codes and every output. `reference-k9.txt` holds the Phase 1 hashes; `hash --against` checks a run against it. Usage is in the docstring; a short entry is in `tools/CONTEXT.md`.
- Hash method = Phase 1's `refhash.py`, with two additions. (a) The check outputs Phase 1 recorded on the working tree (`layout_check.txt`, `v8_debug_sheet_check.txt`, the other v8 checks) have the scratch prefix `<ROOT>/v8src/` stripped, because on a scratch root `layout_check`'s header prints the absolute path; that's the only difference (shown below). (b) Task 3 below.
- `layout_check_scratchroot_nobaseline.txt` is left out of the reference on purpose: after task 2 a scratch root has a baseline, so that run now equals `layout_check.txt` (its hash `706766624be6692a` reproduces from a scratch root).
- **Path length still matters:** the reference reproduces only from a run root of 121 characters (`<scratchpad>/<6 chars>`), because `extract.py` prints the netlist byte count. Run-vs-run compares only need equal lengths; `compare` warns otherwise.

**Task 2, scratch roots (`8ff6a88`).**
- `layout_check.py`: the baseline key is `<root sheet stem>/<sheet path relative to the root sheet's folder>` (`motion-play-main-v8/esp32_s3.kicad_sch`). `layout_baseline.json` re-keyed (values unchanged). `--update-baseline` refuses a root outside the repo, so a scratch run can't ratchet the committed baseline.
- `v8_mcu_sheet.py` gains `set_root`/`add_root_arg`/`apply_root_arg`. `--root` sets `ROOT`, `KICAD` and `FP_DIR` in every loaded v8 module (including `__main__`). `v8_mcu_sheet`, `v8_bus_sheet`, `v8_power_sheet` and `v8_debug_sheet` take `--root` with `--check` only; `--apply`, `--erc-fixes`, `--fix-11c/f` and `--annotate` with `--root` exit 2. `v8_project_setup.py` takes `--root` with `--verify` only (sets `DEST`). Phase 7's `--apply` replays will need `--root` for the write modes; it's refused today so a scratch `--apply` can't write the footprint into the working tree (`v8_power_sheet.write_j7_footprint` writes under `KICAD`).
- **Working tree, before vs after:** `v8_mcu/bus/power/debug_sheet.py --check`, `layout_check.py` and `layout_check.py -v` (venv, 9.0.4) are byte-identical (`p4/before-wt/` vs `p4/after-wt/`; md5 `51d59021…` bus, `57f49034…` debug, `01b6f14d…` mcu, `a9971998…` power, `03326d44…` layout, `55bdccf8…` layout -v; the four v8 files also equal Phase 1 `post-edit-k9/`).
- **`v8_project_setup.py --verify`, before vs after (never on the working tree):** the old tool ran from a scratch worktree at `dff387a` (its hard-wired `DEST` was the worktree's copy), the new tool with `--root` on a fresh `git archive HEAD` copy. Output identical, with and without `--no-v7-compare` (`p4/before-wt/v8_project_setup_verify*_wt.txt` vs `p4/after-wt/*_root.txt`).
- **Proof `--root` reaches every kicad-cli call:** `v8_debug_sheet.py --check --root <copy>` with `KICAD_CLI` set to a logging wrapper around 9.0.4 (`p4/cliwrap/calls.log`): 5 calls on the scratch v8 root, 1 on the check's own temp v7 copy, none on the working tree. PHASE 11 CHECK PASSED; output differs from the working-tree run only in the layout_check header path.

**Task 3, harness reproduces the reference (`7fb9801`).** `regress.py run scratchpad/p4run1` (working-tree tools, venv 3.13.3, 9.0.4): every command exits 0; **24/24 reference hashes match** (20 Phase 1 + the 4 other v8 checks). Every `v8_*.py --check` passes on the scratch root (CHECK PASSED, PHASE 9/10/11 CHECK PASSED, LAYOUT CHECK PASSED; `v8_project_setup --verify` ERC 0 errors, 81 pin_to_pin, 2 lib_symbol_issues). The same from a worktree at HEAD (`p4wt01`): 24/24, and `compare p4run1 p4wt01` SAME.
- **Found: kicad-cli 9.0.4 DRC doesn't write violations in a stable order.** The first run's `board-model.json` missed the Phase 1 hash only because `drc.violations[4]` and `[5]` were swapped; four bare `kicad-cli pcb drc` runs on the same board gave the swapped order once. Phase 1's "deterministic" check was lucky. The harness now sorts the board model's `drc.violations`/`drc.unconnected` before hashing and comparing; Phase 1's own file re-hashes to `84df69225ee16b00` (as do the Phase 2 runs and this one); `reference-k9.txt` records both. `compare` also ignores an ERC report's `date` and item `uuid`s (KiCad re-creates J7's duplicate-number pin uuids on every load). `board_model.py` itself is unchanged; whether it should sort its DRC list is Phase 10's call.

**Task 4, kicad-tools pinned (`5f9a109`).** kicad-tools 0.29.0 needs numpy ≥1.24, pydantic ≥2, pyyaml ≥6, rich ≥13, rtree ≥1, shapely ≥2. **It forces no new shapely, numpy or matplotlib** (2.0.7 / 2.5.4 / 3.11.2 kept). Ten packages added, all pinned: annotated-types 0.8.0, markdown-it-py 4.3.0, mdurl 0.1.2, pydantic 2.14.3, pydantic_core 2.50.4, Pygments 2.21.0, rich 15.0.0, rtree 1.4.1, typing-inspection 0.4.5, typing_extensions 4.16.0. (Phase 3's 73 packages came mostly from kicad-sch-api.) kiutils 1.4.8 stays. `tools/.venv` rebuilt from the file (old one moved to `p4/venv-old`; pip 26.3, then `-r tools/requirements.txt`): 25 packages, `pip check` clean, freeze identical to a probe venv built the same way. Harness on the rebuilt venv (`p4run2`): 24/24, and `compare p4run1 p4run2 --tol 0` SAME (board model and reports exact). The global `python3` is still pyenv 3.7.3.
- Added `regress.py roundtrip <outdir>` (with `rt_kicad_tools.py`, run in the venv): kicad-tools load + save, raw and typed layers, of all 22 `.kicad_sch`/`.kicad_pcb` of v8 (freeze), v7 (`c2acffc`) and power-supply, sensor-rigid, sensor-flex (HEAD). **All 44 saves tree-identical**, 0 failures (`p4/rt1`). PLAN "Pin and upgrades" asks the harness for this round trip.

**Oracle check before the tag.** `regress.py run scratchpad/p4wt02 --tools HEAD` at `5f9a109`: 24/24, and `compare p4run2 p4wt02 --tol 0` SAME. So `--tools kicad10-preport` reproduces the reference.

**For the next session.**
- Oracle runs: `python3 tools/kicad-regress/regress.py run <scratch>/<6 chars> --tools kicad10-preport` against the same with the ported tools, then `compare`. Keep the two run roots the same length.
- `modify.annotate_components` finds `annotate.py` as `root.parents[3]/tools/...`, which fails on a scratch root (loud `FileNotFoundError`, `--apply`/`--annotate` paths only). Phase 6/7 should take it from `Path(__file__)`.
- `--root` on the v8 scripts covers `--check`/`--verify` only. Phase 7's `--apply` replays need it extended to the write modes (`set_root` already moves `KICAD` and `FP_DIR`; `v8_project_setup` `--apply` prints `DEST.relative_to(REPO)`, which fails outside the repo).
- `tools/CONTEXT.md` "Dependencies" still says kiutils (Phase 11 owns it).

**Handoff checks.** `git status` clean. `git diff dff387a HEAD -- hardware lab .githooks` empty; the working-tree `.kicad_prl` files are untouched (v8 Nov 4, v7 Apr 7). No harness worktree is left (`git worktree list`). My Phase 4 "before" worktree used `sparse-checkout`, which set `extensions.worktreeConfig` in `.git/config`; I removed the worktree and unset that key, so `.git/config` is as it was. The harness doesn't use sparse checkout. kicad-tools wrote nothing outside the venv and scratch that I found. No new documents, nothing Deferred, PLAN unchanged.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 4 | Phase 4: Port groundwork | DONE | No — clean completion | b71c272 | 6 tasks; harness 24/24; kicad-tools 0.29.0 pinned; tag `kicad10-preport` = b71c272 |

#### Verification
- 5 commits, `123e651`..`b71c272`. Phase 4 is all `[x]`. PLAN is untouched since the replan. `git diff dff387a HEAD -- hardware lab .githooks` is empty.
- `kicad10-preport` resolves to `b71c272`. `extensions.worktreeConfig` is unset. The only extra worktrees are the user's own Cursor worktrees, which existed before this phase.
- Orchestrator re-run on the working tree: `tools/.venv` `v8_debug_sheet.py --check` gives PHASE 11 CHECK PASSED, and `pip check` is clean.
- The `layout_baseline.json` re-key changes the keys but not the values. Byte-identical working-tree output was shown by the Worker.
- Carry forward:
  - `modify.annotate_components` resolves `annotate.py` through `root.parents[3]`, so it breaks on scratch roots. This matters for the Phase 5 annotation prototype and the Phase 7 `--apply` replays.
  - `--root` has to be extended to the write modes in Phase 7.
  - kicad-cli 9 DRC order is unstable. The harness sorts it, and `reference-k9.txt` records both hashes.

---

### Worker #5 — Phase 5: kicad-tools API spike

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 5 — kicad-tools API spike (scratch only; no tool is ported)
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN in full ("Port scope", "One I/O module", "Retire candidates", OQ-7). In SESSION.md: Worker #3 Notes (kicad-tools round-trip, loss table) and Worker #4 Notes (harness usage, annotate_components path caveat).

Tasks assigned: Phase 5, tasks 1–5. Stop before G2a (task 6): the Orchestrator takes it to the user. Return PARTIAL at G2a; that stop is planned.

Notes: use tools/kicad-regress (regress.py) for netlist, ERC, plot, tokens and treeeq comparisons. Prototypes live in the scratchpad, not the repo; no tool is ported. Prototype against `kicad10-preport` modify.py on identical inputs. KiCad 10 copies only via `kicad-cli sch/pcb upgrade` on fresh scratch copies. Give the G2a recommendation with the evidence: (a), (b) or (c), OQ-7 options, and the retire list.
Rules: hardware/ and lab/ unchanged; kicad-cli 10 never on the working tree; tools/.venv and requirements.txt unchanged.
```

#### Notes

Scratch for this phase: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p5/` (scripts in `p5/scripts/`). The preport worktree was `p5/wt-pre` (`kicad10-preport` = `b71c272`), removed at handoff. kicad-tools 0.29.0 and kiutils 1.4.8 from `tools/.venv`, unchanged.

**Task 1: coverage map.** Method: `p5/scripts/kiutils_usage.py` lists, for each of the 23 files, the kiutils names imported and every attribute access whose name is a kiutils dataclass field (output `p5/usage.json`), then each use site was read. kicad-tools was read from its source in the venv. "Typed" is `kicad_tools.schema` (`Schematic`, `PCB`, `SymbolLibrary`). "Raw" is `kicad_tools.sexp.SExp` with `core.sexp_file.load_/save_schematic`, `load_symbol_lib`, `load_/save_pcb`. Files: modify = `schematic-modify/modify.py`; gens = the three `schematic-gen` scripts; sc-extract = `schematic-context/extract.py`; pcb readers = `pcb-context/board_model.py`, `extract.py`, `routing_extract.py`, `tools/verify-routing.py`.

Schematics and symbol libraries:

| kiutils (what we use) | Used by | kicad-tools typed | Raw layer | Verdict |
|---|---|---|---|---|
| `Schematic.from_file` | modify, tidy_fields, v8_project_setup, sc-extract, annotate, show, gens; via modify: every `v8_*`, tidy_labels, esp32_integration* | `Schematic.load` (read views) | `load_schematic` | Covered |
| `to_file` through `kiutils_k9.save_schematic` | modify, tidy_*, v8_*, annotate, gens | `Schematic.save` | `save_schematic` (tree-identical) | Covered. Keep our lock guard: kicad-tools checks only `~<that file>.lck` and by default only warns. Formatting differs (task 4) |
| `Schematic.create_new` | gens | none | parse a template text | Raw, small |
| `kiutils_k9` hide patches | every schematic loader | not needed: kicad-tools keeps tokens as written | readers must accept `(hide yes)`, bare `hide` (kiutils-saved files) and, on KiCad 10, a property-level `(hide yes)` | Helper `is_hidden()` |
| `SymbolLib.from_file`, `.symbols`, `libId` | modify (`extract_lib_symbol`), tidy_fields, v8_mcu_sheet, gens | `SymbolLibrary.load` (model) | `load_symbol_lib` | Covered (raw for copying a symbol into a sheet) |
| `Symbol.units[*].pins` (`number`, `position`) | modify, gens, v8_mcu_sheet | `LibrarySymbol.pins` (`LibraryPin` number, position, rotation, unit) | `symbol/symbol/pin` nodes | Covered |
| `Symbol.extends`, `entryName` (flatten one `extends` level) | v8_mcu_sheet | `resolve_extends` / `resolve_base`, but on the model (see embed) | copy the parent's raw node and rename it | Raw, small |
| `hidePinNumbers`, `pinNamesHide` | tidy_fields | none | `(pin_numbers (hide yes))`, `(pin_names … (hide yes))` | Raw |
| `libSymbols`; `ensure_lib_symbol` appends a deep copy | modify, gens, tidy_fields, v8_debug_sheet | `lib_symbols` returns the raw node; `embed_lib_symbol(LibrarySymbol)` **rebuilds the symbol from the model** (property positions reset to stacked offsets, no `pin_names`/`pin_numbers` flags) | deep copy of the raw node (proved in task 2) | **Typed embed unusable**; raw covers |
| `schematicSymbols` / `SchematicSymbol` (`libId`, `position`, `unit`, `inBom`, `onBoard`, `dnp`, `fieldsAutoplaced`, `uuid`, `pins`, `instances`, `mirror`) | modify, every `v8_*`, tidy_*, sc-extract, annotate, show, gens | read: `symbols` (`SymbolInstance` snapshot, `_sexp` back-reference). Add: `add_symbol`/`add_power`, but Value at +2.54 instead of the library offset, no field justify or angle, no `fields_autoplaced`, only 4 properties, uuid5 ids. No remove, no edit (snapshots) | the symbol node | **Edit and remove: raw only.** Typed add is not equivalent to `modify.add_component` |
| `Property` (`key`, `value`, `id`, `position`, `effects`) | modify, annotate, tidy_fields, gens | `SymbolProperty` snapshot: name, value, position, visible; no effects; `to_sexp` writes a fixed font | `property` node | Raw. KiCad 10 moved `hide` to the property (`(hide yes) (show_name no) (do_not_autoplace no)` before `effects`) |
| `Effects`, `Font`, `Justify`, `Stroke`, `Position` | modify, gens, annotate, v8_mcu/debug/bus_sheet, tidy_labels, tidy_fields | none (fixed values inside `add_*`) | `effects`/`font`/`justify`/`stroke`/`at` nodes | Raw helpers |
| `graphicalItems` / `Connection` (wires: `type`, `points`) | modify, gens, tidy_labels, v8_*, sc-extract | read `wires` (`Wire` start/end); `add_wire` (uuid5) | `wire` node | Read/add typed; remove raw |
| `labels` / `LocalLabel` | modify, gens, tidy_*, v8_* | read `labels`; `add_label` always writes `justify left bottom` and `fields_autoplaced` (wrong for 180/270, where `modify` writes `right bottom`) | `label` node | Raw |
| `hierarchicalLabels` | modify, gens, tidy_fields, v8_bus_sheet, sc-extract, esp32_integration_phase2 | read; `add_hierarchical_label`; no shape change or rename | `hierarchical_label` node | Raw for edits |
| `globalLabels`, `texts` | tidy_fields, v8_bus_sheet | `global_labels` read; no texts | nodes | Raw for texts |
| `junctions` | modify | read; `add_junction`; no remove | `junction` node | Raw for remove |
| `noConnects` / `NoConnect` | modify, gens | read only (no `to_sexp`, no add) | `no_connect` node | Raw |
| `sheets` / `HierarchicalSheet` (`fileName`, `sheetName`, `position`, `width`, `height`, `pins`, `instances`/page) | modify, sc-extract, annotate, show, v8_project_setup | `sheets` (name, file, uuid, position, size; no pins, no page); `hierarchy.SheetPin` read | `sheet` node | Read typed or raw; add and edit raw |
| `HierarchicalPin` (`name`, `connectionType`, `position`) | modify, v8_mcu_sheet | read only (`SheetPin`) | `sheet/pin` node | Raw |
| `SymbolProjectInstance/Path`, `HierarchicalSheetProjectInstance/Path` | modify, gens | written only inside `add_symbol` | `instances` blocks | Raw |
| `paper.paperSize` | tidy_fields, v8_bus/debug/power_sheet | `paper` | — | Covered |
| `titleBlock` (`title`, `revision`, `date`), `uuid`, `version`, `generator` | v8_project_setup, gens | read (`title_block`, `uuid`, `version`, `generator`) | — | Read typed; write raw |
| `.to_sexpr()` (comparing two library symbols) | v8_debug_sheet | — | `serialize_sexp` or tree compare | Covered |
| `kiutils.utils.sexpr.parse_sexp` (nested lists) | layout_check | — | `parse_string` gives `SExp` nodes, not lists | Raw plus a 10-line to-list adapter |

Boards:

| kiutils (what we use) | Used by | kicad-tools typed | Raw layer | Verdict |
|---|---|---|---|---|
| `Board.from_file` | pcb readers, v8_project_setup, route_esp32 | `PCB.load` (builds the net table on KiCad 10) | `load_pcb` | Covered |
| `Board.to_file` | v8_project_setup (strips v7's board to v8's outline-only board), route_esp32 | `PCB.save` | `save_pcb` (tree-identical) | Raw for v8_project_setup's strip. A board write on KiCad 10 is OQ-3's question (Phase 13) |
| `footprints` (`libId`/`entryName`, `position`+angle, `layer`, `properties` dict, `attributes`, `pads`, `graphicItems`) | pcb readers | `Footprint` (name, position, rotation, layer, reference, value, properties, attr, exclude_from_bom, pads, graphics; `board_only` kept as an unmodelled token) | `_sexp_node` | Covered; `board_only` raw (task 3) |
| `pads` (`number`, `type`, `shape`, `position`+angle, `size`, `drill`, `layers`, `net`, `pinFunction`, `pinType`, `roundrectRatio`) | pcb readers | `Pad` | — | Covered (task 3) |
| `customPadOptions.anchor`, `customPadPrimitives` | board_model | **none** | `pad/options`, `pad/primitives` via `Pad._sexp_node` | Raw (task 3) |
| `traceItems`: `Segment`, `Arc`, `Via` | pcb readers, route_esp32 | `segments`, `arcs`, `vias` | — | Covered (task 3) |
| `zones` (`layers`, `polygons`, `filledPolygons` per layer, `keepoutSettings`, `netName`, `name`, `priority`, `clearance`, `minThickness`, `connectPads`) | board_model, verify-routing | `Zone` | — | Covered (task 3) |
| `setup.stackup.layers` (`name`, `type`, `thickness`, `material`, `epsilonR`), `general.thickness` | board_model, v8_project_setup | `setup.stackup` (`StackupLayer`) | — | Covered |
| `layers`, `nets`, `graphicItems` (lines, arcs, circles, rects, polys), `version`, `generator` | pcb readers | `layers`, `nets`, `graphics` (`BoardGraphic`) | — | Covered (task 3) |
| `Net(...)`, `Segment(...)`, `Via(...)` construction, `tstamp`, `locked` | v8_project_setup, route_esp32 | `segments`/`vias` setters | nodes | Raw; route_esp32 is a retire candidate |

**What kicad-tools can't do in its typed layer (the gaps), and their size.** (1) No in-place edit or removal of any schematic item: the typed objects are snapshots. (2) No sheet or sheet-pin add, no no-connect add, no control of effects, justify or property placement. (3) `embed_lib_symbol` and `SymbolProperty.to_sexp` rewrite what they write, so they lose information. (4) No custom-pad primitives. Every gap is covered by the raw layer, which is lossless (Phase 3 and 4 round trips). The cost is our own helper layer: the prototype (`p5/scripts/ktmod.py`, 814 lines with docstrings) is 169 lines of helpers and I/O (find, insert in KiCad's order, atom setters, text builders, the lock guard), then about 645 lines that re-implement `modify.py`'s public functions (`modify.py` itself is 919 lines). Two raw-layer traps the helpers must handle: **a float atom created as `SExp(value=x)` is written with 6 significant digits** (`181.6099` → `181.61`; the helpers build numbers with an explicit string), and **properties hide in three forms** (above).

**Task 2: editing prototypes.** `p5/scripts/ktmod.py` re-implements every public `modify.py` function on kicad-tools' raw layer, with the same signatures and semantics (it reproduces two preport quirks on purpose: `add_sheet_reference` writes the project name `motion-play-main` and the KiCad 6 keys `Sheet name`/`Sheet file`; a repeated pin number keeps one `(pin …)` entry, as kiutils' pin dict does). The typed layer is used for nothing that writes. Driver `p5/scripts/edits.py IMPL OP BASE OUT`: a fresh copy of the base tree, one edit through either `modify.py` from the `kicad10-preport` worktree (kiutils) or `ktmod.py`, then save. `uuid.uuid4` is seeded in the driver, so both sides mint the same UUIDs and the netlists can be compared with tstamps included. Compare: `p5/scripts/cmp_edit.py` (harness `kcompare`: structural netlist, ERC counts by type, plotted strings per sheet; then each kicad-tools sheet's token census against the unedited base). Base: `git archive v8-schematic-freeze` with `hardware/pcb-main/resources` (`p5/base`). Results: `p5/cmp9.txt`, `p5/cmp10.txt`.

| Op | What it does (TCA sheet unless noted) | KiCad 9 | KiCad 10 |
|---|---|---|---|
| add_comp | `add_component` ×3: C900 (Device:C embedded from the stock `.kicad_sym`, 2 pin nets), R900 at 90° with `stub_len` 2.54, R901 on the LED sheet at 180° with the symbol taken from a `.kicad_sch` | PASS | PASS |
| remove_comp | `remove_component` R92; `remove_component_with_stubs` TP99 (stub, GND label, and its lib symbol when unused) | PASS | PASS |
| wires | `add_wire`; `remove_wire_between`; `remove_junction_at` | PASS | – |
| labels | `add_local_label` at 0° and 180°; `remove_local_label_near` | PASS | – |
| nc | `remove_no_connect_at`; `add_no_connect` | PASS | – |
| hlabels | `add_hierarchical_label` + `add_pin_to_sheet_ref`; `change_hlabel_shape` + `change_sheet_pin_direction`; `rename_hlabel` + `rename_sheet_pin`; 12 more output pins so the sheet grows | PASS | PASS |
| sheet | `add_sheet_reference` with 2 pins, to a new child sheet | PASS | PASS |
| power | `add_power_symbol` GND and PWR_FLAG from the stock `power.kicad_sym` | PASS | PASS |
| props | `set_property` of an existing Value, a new hidden MPN, and LCSC Part on the LED sheet | PASS | PASS |
| pin_net | `set_pin_net` on R92.1 (renames the stub's label) and on U4.10 (no-connect on the pin → stub + label) | PASS | PASS |
| annotate | `annotate_components` R92, R105, TP99 (3 ai_ fields). Preport: `annotate.py` from the worktree, passed as `annotate_script` (works around `root.parents[3]`). kicad-tools: the same write in process | PASS | PASS |

- **PASS** means the netlist is structurally identical (components with every field and tstamp, nets by node set), the ERC counts are identical by type, and the plotted strings are identical on every sheet. In every op the census of the kicad-tools sheets against the base shows only the edit. Examples: props +1 `property` and 1 hide; wires −1 `junction`, and the wire add and remove cancel; sheet +1 `sheet`, +2 `pin`, +1 `instances`/`page`. Each edit also changed the netlist against the base as intended (for example add_comp 296 → 299 components, 158 → 162 nets).
- **KiCad 10 method:** a fresh copy converted by `kicad-cli 10 sch upgrade` on each sheet (`p5/base10`), with the kicad-tools edit run on it. The other side is the preport's KiCad 9 output, copied and upgraded the same way. Both are read by kicad-cli 10. Both embed symbols from the 9.0.4 stock library, so only the file format differs. ERC on 10 lists the setup library items (about 281 footprint and 332 symbol), identical on both sides.
- **Found and fixed in the prototype.** (1) On the kiutils-formatted LED sheet, hidden properties carry a bare `hide`. The first `_hide_prop` added `(hide yes)` beside it, doubling the flag (census F:hide +3; KiCad didn't mind). (2) **KiCad 10 puts a property's `(hide yes)` on the property, not in `effects`**, beside `(show_name no)` and `(do_not_autoplace no)`. A KiCad-9-style property in a KiCad 10 file still loads, plots and netlists the same, but the census showed a second `hide`. The helpers now write each format's own form (chosen from the file's `version`). After both fixes the 11 KiCad 9 ops were re-run (all PASS) and the four property-writing KiCad 10 ops were re-run (all PASS, census only the edit). The other four KiCad 10 ops write no properties.
- **What that means for the port.** Every public `modify.py` operation works on the raw layer with identical results on KiCad 9 and on KiCad 10. No operation needed anything kicad-tools lacks. The typed layer couldn't have done most of them (task 1). The I/O module needs the format version per document (the prototype uses a module global).

**Task 3: board read prototype.** `p5/scripts/board_values.py` collects every value `board_model.py` reads into one record: footprints (lib id, layer, position and angle, Value, LCSC, attributes including `board_only`, every graphic), pads (number, type, shape, position and angle, size, drill, layers, net, pin function and type, roundrect ratio, custom-pad anchor and primitives), segments, arcs, vias, zones (net, name, layers, priority, clearance, min thickness, connect_pads, keepout flags, outline, fills per layer), stackup, board graphics (outline), layers, nets, version, generator. Side `ki` reads as board_model does with kiutils. Side `kt` uses kicad-tools' typed `PCB`, plus the corrections a port would need, each counted. Inputs: v7 `git archive c2acffc` (`p5/v7k9`) and a copy converted with `kicad-cli 10 pcb upgrade` (`p5/v7k10`). Records are in `p5/bv/`.
- **Result: 51,367 values; kicad-tools on the KiCad 9 board equals kiutils on 51,354 of them, exactly (tolerance 0).** The counts are 93 footprints, 362 pads, 855 segments, 0 arcs, 224 vias, 8 zones, 102 nets, 13 stackup layers and 2 board graphics. The other 13 are not kicad-tools errors. In 10, **kiutils misreads the file**: it gives `connect_pads` None for all 8 zones (the file has `(connect_pads yes …)` on 5, i.e. solid, and none on 3, i.e. thermal reliefs), and a width of 0.12 for both board `gr_rect`s, whose `(stroke (width …))` is 0.05 (Edge.Cuts) and 0.2 (the F.Cu rectangle). So today's `board-model.json` has `connect_pads: null` everywhere and buffers that copper rectangle at 0.12 mm. In the other 3, an absent zone name reads as None in kiutils and `''` in kicad-tools.
- **KiCad 10 board through kicad-tools against the KiCad 9 board through kicad-tools:** 2 values differ, both expected from Phase 3: one NPTH pad's layers `F&B.Cu` → `*.Cu`, and the version token. The keepout zone with no net reads `''` on both.
- **Corrections the typed `PCB` needed** (one finding each; a port must make every one, or read raw):
  - **Coordinates rebased.** `PCB.load` moves footprint positions, segments, vias and zone outlines and fills onto the Edge.Cuts minimum corner (v7: 75.7, 101.0). Board graphics stay in file coordinates. Adding the origin back was exact on v7, but it isn't exact in general.
  - Absent tokens come back as defaults: a pad with no drill gives `drill 0.0` (345 pads), absent `pinfunction`/`pintype` give `''` (141), absent stackup `material`/`epsilon_r` give `''`/`0.0` (10 layers), an absent zone name gives `''`.
  - **Oval drills** read as `drill 0.0`, with the size in `drill_size` (J7, 4 pads).
  - **A zone clearance of 0 reads as 0.2** (the keepout zone, `(connect_pads (clearance 0))`): a default is substituted for zero.
  - Custom pads (5: U6.21 and four J7 pads) have no typed anchor or primitives; they're read from `Pad._sexp_node`.
  - Single-layer zones have `layer` and empty `layers` (7).
  - Zones have no back-reference to their raw node; they were matched to the raw `zone` nodes by order.
- **What that means for the port (Phase 10).** The typed `PCB` reads everything, but with six silent default or rebasing behaviours. Each changes `board-model.json` unless it's undone. Reading the raw tree (`load_pcb`) with our own small accessors avoids all six, and also reads the two values kiutils got wrong. The preport oracle has those two wrong, so Phase 10's leaf compare will show them as differences in any case: `connect_pads` (8 zones) and the F.Cu rectangle's buffer width (one entry in `graphic_copper`). The Planner or Phase 10 needs to accept them as listed fixes.

**Task 4: save format (OQ-7).** Script `p5/scripts/savefmt.py`: one edit (a symbol's Value through `set_property`) on two sheets, each saved several ways, measured with `git diff --no-index --numstat` against the unedited file. Outputs: `p5/sf9/`, `p5/sf10/`.
- **The v8 files aren't in one format today.** At `v8-schematic-freeze`, four sheets are in KiCad's own tab format (last saved by the KiCad GUI). `led_controller.kicad_sch` and `motion-play-main-v8.kicad_pcb` are in kiutils' two-space format (last saved by a tool).

| Lines changed by one Value edit (+added / −removed) | TCA sheet, KiCad format (13,447 lines) | LED sheet, kiutils format (1,574 lines) |
|---|---|---|
| Preport kiutils save (today's behaviour), KiCad 9 | +5,199 / −13,446 (whole file) | +3 / −3 |
| kicad-tools plain save, KiCad 9 | +548 / −1,467 | +3,547 / −1,574 (whole file, once) |
| kicad-tools plain save, KiCad 10 copy | +548 / −1,467 | +155 / −421 (the copy is in KiCad format after `sch upgrade`) |
| **Splice save** (prototype), KiCad 9 | **+4 / −8** | +97 / −41 (the edited symbol, now in KiCad's layout) |
| **Splice save**, KiCad 10 copy | **+4 / −8** | **+4 / −8** |
| Plain save, then a kicad-cli 10 `sch upgrade --force` re-save (KiCad 10 files only) | **+1 / −1** | **+1 / −1** |

- **No formatting option in kicad-tools 0.29.0.** `SExp.to_string`/`serialize_sexp` have no style settings (the `indent` argument is ignored). `preserve_source=True` keeps original text only for untouched copper arcs.
- **Splice save (prototype, about 15 lines in `savefmt.py`).** kicad-tools records each top-level item's source span at parse. At save, an item whose compact serialization is unchanged is written as its original text, with the original whitespace before it. A changed or new item is serialized by kicad-tools. The output is tree-identical to the plain save in all four cases (`kcompare.tree_equal`). It needs no kicad-cli and works on KiCad 9 and 10. The same mechanism applies to boards (spans are recorded there too); I didn't measure it on a board edit.
- **KiCad 9 format kept.** Every kicad-tools save of a KiCad 9 file keeps its version token: 9 sheet saves keep `(version 20250114)`, and v7's board keeps `(version 20241229)`. kicad-cli 9 loads them all. The task 2 netlists and ERC of the kicad-tools-saved v8 copies were all run by kicad-cli 9. For v7's board, kicad-cli 9 DRC on a kicad-tools load + save gives exactly the original's counts (16 clearance and 2 hole_clearance errors, 2 padstack warnings, 0 unconnected, 2 parity). That no-op board save alone is +360 / −4,595 lines of whitespace.
- **The options, with their costs:**
  - **(1) Accept the plain save.** No effort. Every tool save reformats the whole file: about 2,000 lines on a 13,000-line sheet, and a full rewrite of any file still in kiutils format, once. That's still less noise than today's kiutils saves of KiCad-format sheets (+5,199/−13,446).
  - **(2) kicad-cli 10 re-save.** The output is exactly KiCad's format (+1/−1). It works only for KiCad 10 files: there's no `upgrade` in kicad-cli 9, and kicad-cli 10 would convert a KiCad 9 file. Run it on a temporary copy outside the project folder, then copy the file back (the `.kicad_prl` hazard), so about one kicad-cli call per saved sheet. It ties the I/O module to the installed KiCad and can't apply before the v8 migration (Phase 14).
  - **(3) Splice save in the I/O module.** About 30–40 lines plus a test. The diff is only the touched items, on KiCad 9 and 10, with no kicad-cli. The touched item takes kicad-tools' layout (short lists on one line), until KiCad next saves the file.
  - **(4) Splice save, then the kicad-cli 10 re-save for KiCad 10 files only.** Exact KiCad format on 10 at option 2's cost; (3) alone on 9.

**Task 5: the I/O module, and the retire candidates.**

*Proposed I/O module: `tools/kicad-io/kicad_io.py`.* It sits in a folder of its own beside the other tool folders, because `schematic-*`, `pcb-context` and `kicad-regress` all use it. Tools put `tools/kicad-io` on `sys.path`, as they do for `kiutils_k9` today. It replaces `kiutils_k9.py`, and nothing else under `tools/` imports `kicad_tools` directly for file I/O.
- **Version check, at import.** `importlib.metadata.version("kicad-tools")` must equal `PIN = "0.29.0"`, otherwise it raises `KiCadIOVersionError` naming `tools/requirements.txt` (PLAN "Pin and upgrades").
- **Format check, at load.** Each file kind has the set of format versions the harness has tested (schematic 20250114 and 20260306; board 20241229 and 20260206; symbol libraries as found in the KiCad 9 and 10 stock libraries). A newer one, for example a KiCad 11 file, raises rather than being edited blind.
- **Load.** `load_schematic(path)`, `load_symbol_lib(path)` and `load_board(path)` each return a `Doc`: path, kind, the raw `SExp` tree, the original text, and the format version. They use kicad-tools' raw loaders (`core.sexp_file`). Read-only tools may also wrap a `Doc` in the typed views (`schema.Schematic(doc.tree)`), but the typed `PCB` only with the task 3 corrections, or not at all (G2a recommendation below).
- **Save.** `save(doc, path=None)`:
  - It runs the lock guard (below).
  - It refuses if the tree's format version differs from the one loaded, so a KiCad 9 file can't leave as 10 by accident.
  - It writes with the OQ-7 strategy chosen at G2a (the splice save is the proposal), atomically (`core.atomic_write.atomic_write_text`), with a final newline.
  - `save_project(docs)` saves several docs after one guard check, as `ProjectDocs.save_all` does today.
- **Lock guard.** `lock_files(path)` and `assert_not_open(path)` raise `KiCadOpenError` while `~*.kicad_sch.lck` or `~*.kicad_pcb.lck` exists in the project folder (today's rule, extended to boards). kicad-tools' own check (`check_kicad_lock`) only looks at the exact file's marker and only warns by default, so the module doesn't rely on it.
- **Raw-tree helpers** (the prototype's 169 lines, which every writer needs):
  - finding: `kids`, `child`, `atom`, `at_xy`;
  - safe atom setters: `set_str`, `set_bare`, `set_num` (exact number text, against the six-digit float trap);
  - `node(text)` for building items from KiCad-form text;
  - `insert_item` (keeps KiCad's top-level order) and `remove_items`;
  - version-aware properties: `make_property`, `is_hidden`, `hide` (property-level hide on 10, in `effects` on 9, and bare `hide`);
  - `to_lists(tree)` for `layout_check`.
  - Board accessors stay in `pcb-context` (Phase 10).
- **Phase 6 test.** It includes `kicad-regress/rt_kicad_tools.py`'s round trip through `kicad_io` (load + save tree-identical, version token unchanged, on every board and project), and the splice save's "tree-identical to a plain save" check.

*Retire candidates: confirmed.* `git grep` over the whole repo finds no import, subprocess, runpy or import_module call of `esp32_integration.py`, `esp32_integration_phase2.py` or `route_esp32.py`. Each appears only in its own docstring and in documentation:
- `tools/CONTEXT.md:57` (the `esp32_integration.py` row) and `tools/schematic-modify/CONTEXT.md:52` and `:61`. Line 61 is workflow step 1, which names `esp32_integration.py --apply` as the example script, so it needs rewording rather than deleting.
- History, which stays: `docs/initiatives/archive/esp32-integration/` PLAN and TASKS, `docs/research/v7-retry/kicad-extraction-audit.md:28`, and v8-debug-board SESSION:845.
- The `esp32_integration_phase_1c` strings in both `circuit-context.json` files are `ai_role` values, not calls.

The two schematic scripts hard-code v7's `hardware/pcb-main/kicad/motion-play-main.kicad_sch`, which is never re-saved. `route_esp32.py` writes the board through kiutils `to_file`, the path OQ-11 ruled out. All three were last changed in March 2026 (`cc5e603`). Retiring them saves porting about 3 scripts, and their Phase 8 and 10 replays.

**Handoff checks.** The `p5/wt-pre` worktree was removed (`git worktree list` shows only the user's Cursor worktrees). `git status` is clean after the last commit. Nothing under `hardware/` or `lab/` changed (`git diff 7ad78bc HEAD -- hardware lab .githooks` is empty). `tools/.venv` and `tools/requirements.txt` are unchanged. kicad-cli 10 ran only on scratch copies in `p5/` (`base10`, `v7k10`, the `k10/*/pre` upgrades and the `sf10` re-saves). The global `python3` is unchanged. No new documents, no PLAN edits. G2a and the Handoff stay `[ ]`.

**G2a recommendation.**
- **Port: option (b), raw layer with our own helpers. Not (c); (a) only for read-only views.**
  - Every public `modify.py` operation worked on kicad-tools' raw layer, with identical netlist, ERC counts and plotted strings: 11/11 on KiCad 9 and 8/8 on KiCad 10. The census showed only the intended edit (task 2). Nothing needed a capability kicad-tools lacks, so there's no case for (c).
  - (a) doesn't buy much. For `modify.py` the typed layer covers only reads: no edit or removal, no sheet, sheet-pin or no-connect add. Its `add_symbol`/`add_label` differ from `modify.py` (field placement, justify, ids). `embed_lib_symbol` and `SymbolProperty.to_sexp` rewrite what they write (task 1).
  - For boards, the typed `PCB` reads 51,354 of 51,367 values the same as kiutils, but only after six corrections. It rebases coordinates onto the outline corner, and substitutes defaults for absent tokens, for oval drills and for a zero zone clearance (task 3). Those are silent changes in `board-model.json` if missed. So I'd port `board_model.py` and the other board readers on the raw layer as well, with small accessors in `pcb-context`. The typed `Schematic`/`PCB` stay acceptable as read-only conveniences in read-only tools, behind the I/O module's `Doc`.
  - Effort, from the prototype: about 170 lines of shared helpers plus I/O, and a `modify.py` port of about 650 lines with the same signatures.
- **What kicad-tools can't do, and how big each gap is:**
  - No typed editing at all (large, covered by the raw layer: done in the prototype).
  - Lossy typed writers for library symbols and properties (avoid them: small).
  - No custom-pad model (5 pads on v7; raw: small).
  - Six silent typed-PCB defaults (avoid the typed `PCB`, or correct each one: medium).
  - Programmatic float atoms written with 6 significant digits (one helper: small).
  - No formatting control (OQ-7 below).
  - KiCad 10 moved property `hide` (version-aware helper: small).
- **OQ-7: recommend option (3), the splice save in the I/O module, for KiCad 9 and 10 alike.** About 30–40 lines plus a test. A one-property edit becomes a +4/−8 diff instead of +548/−1,467, with no kicad-cli dependency. Its cost: the touched item takes kicad-tools' layout until KiCad next saves the file, and a file still in kiutils format changes only where it's touched.
  - Option (1), accept the plain save: no effort, but about 2,000 lines of noise per saved 13,000-line sheet.
  - Option (2), the kicad-cli 10 re-save: exact KiCad format (+1/−1), but for KiCad 10 files only, and one kicad-cli call per saved file.
  - Option (4): (3) plus (2) for KiCad 10 files, if exact KiCad layout after a tool save matters more than speed.
  - In every option, KiCad 9 files stay in KiCad 9 format (checked).
- **Retire list: delete all three** (`esp32_integration.py`, `esp32_integration_phase2.py`, `route_esp32.py`). Nothing calls them, they can only edit v7, and v7 is never re-saved. Git history keeps them. Phase 8 removes the `tools/CONTEXT.md:57` row and the `schematic-modify/CONTEXT.md:52` line, and rewords `:61`.
- **For the port phases, found here:**
  - **Two preport board-model values are kiutils misreads.** `connect_pads` is null on all 8 v7 zones, and the F.Cu `gr_rect` is buffered at 0.12 instead of its 0.2 stroke. A correct port changes them, so Phase 10's "identical to preport" needs them accepted as listed fixes (a Planner call).
  - **`add_sheet_reference` hard-codes the project name `motion-play-main`** and writes the KiCad 6 keys `Sheet name`/`Sheet file`. The prototype reproduced it for the comparison. On v8 the project is `motion-play-main-v8`. The port could take the project name from `ProjectDocs`, but that changes the output against preport, so it needs the same acceptance.
  - Typed views are snapshots: after a raw edit, a typed `Schematic` over the same tree must be rebuilt (`invalidate_cache()`).

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 5 | Phase 5: kicad-tools API spike | PARTIAL | Yes — resolvable without replanning: the stop is the planned G2a user gate | 78c2059 | Tasks 1–5 done; G2a and Handoff wait on the user |

#### Verification
- 5 commits, `4d86d21`..`78c2059`. Only SESSION.md and TASKS.md changed. PLAN is untouched. No extra worktree is left.
- Re-derived from the scratch output: `p5/cmp9.txt` has 11/11 VERDICT PASS and `p5/cmp10.txt` 8/8 PASS, with no non-PASS verdicts.
- Carry forward to the G2a Planner touch:
  - **Two kiutils misreads in today's `board-model.json`:** `connect_pads` is null on all 8 zones, and 2 `gr_rect` widths read 0.12. Phase 10's "identical to preport" gate needs them listed as accepted fixes.
  - **Preport `add_sheet_reference` writes the wrong things:** it hard-codes `motion-play-main` and writes the KiCad 6 sheet keys. Fixing either changes output against preport, so it needs a listed exception, or the bug is kept until Phase 11.
  - **The v8 LED sheet and v8 board are still in kiutils' format.** A first splice-save will reformat them once.
- G2a is taken to the user next.

### G2a — user decision (2026-11-11)

- **Port:** option (b). The port goes on kicad-tools' raw s-expression layer with our own helpers; typed views are used only for reads.
- **OQ-7:** splice save in the I/O module, for KiCad 9 and 10.
- **Retire list:** delete `esp32_integration.py`, `esp32_integration_phase2.py` and `route_esp32.py`.
- The two gate exceptions the spike found change the definition of Phase 10's gate and of the `add_sheet_reference` comparison against preport: the kiutils board misreads, and `add_sheet_reference`'s hard-coded project name and KiCad 6 sheet keys. Gate definitions belong to the Planner, so the decisions go to the Planner to record in PLAN.

[ORCH] Spawning Planner — record the G2a decisions and the two preport-gate exceptions in PLAN/TASKS before Phase 6

### Planner — G2a recorded

[ORCH] Planner → REPLANNED: ready to continue (`d1174b7`)

**Verification:**
- Only PLAN.md and TASKS.md changed. PLAN has no date-stamped headings, and OQ-7 is struck.
- G2a and the Phase 5 Handoff are `[x]`.
- Phase 6 is split into 6a (the I/O module and its committed test) and 6b (the `modify.py` port and the E2 fix). Phase numbers cited earlier stay valid.
- PLAN "Accepted differences from preport" is a closed list: E1 (the kiutils board misreads, accepted as fixes in Phase 10) and E2 (the port reproduces the `add_sheet_reference` bug, then a separate commit fixes it). Any other difference stops the Worker.
- The retirements are definite, in Phases 8 and 10.
- Deferred gained one line: regenerating v7's committed `board-model/` needs the user's and the Debugger's agreement.

---

### Worker #6 — Phase 6a: The I/O module

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 6a — The I/O module (still KiCad 9; no tool is ported)
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN in full (replanned at d1174b7), especially "Which layer", "One I/O module", "Raw-layer traps", "Accepted differences from preport". SESSION.md Worker #5 Notes (coverage map, prototype method, save-format measurements) and Worker #4 Notes (harness usage).

Tasks assigned: Phase 6a, all 4 tasks (see TASKS.md)

Notes: Phase 5 prototypes are in scratchpad/p5/scripts/ (ktmod.py, savefmt.py, edits.py, cmp_edit.py). They are present now; build from them, but the committed module and test must not depend on the scratchpad. KICAD_CLI on 9 except for the KiCad 10 copy test.
Rules: hardware/ and lab/ unchanged; kicad-cli 10 only on scratch copies; tools/requirements.txt pin unchanged; no tool ported or switched to kicad_io in this phase.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p6a/` (smoke tests, `fpprobe/`, test runs `io1`–`io4`; `io4.log` is the passing run). `KICAD_CLI` unset (9.0.4); kicad-cli 10 ran only inside the test's `OUTDIR/k10src` copies.

**Task 1, `tools/kicad-io/kicad_io.py` (`12a45e2`, one fix in `abc0880`).** Built from the Phase 5 prototype (`ktmod.py` helpers, `savefmt.py` splice); nothing imports the scratchpad. API: `PIN`, `check_pin`; `FORMATS`, `check_format`; `load_schematic`/`load_symbol_lib`/`load_board`/`load` returning a `Doc` (path, kind, tree, text, version, major, per-item spans); `save(doc, path=None)`, `save_project(docs)` (all guards and version checks first, so a refusal writes nothing), `render(doc)`, `plain_text(doc)`; `lock_files`, `assert_not_open`; `KiCadIOError` and its subclasses `KiCadIOVersionError`, `KiCadIOFormatError`, `KiCadOpenError`; helpers `kids`, `child`, `atoms`, `atom`, `atom_text`, `at_xy`, `num`, `q`, `set_str`, `set_bare`, `set_num`, `node`, `insert_item` (schematic and board order), `remove_items`, `is_hidden`, `hide`, `effects_text`, `make_property`, `to_lists`.
- Splice save: an unchanged top-level item is matched by identity (then by compact text) and written as its original text with its original leading whitespace. A changed item is serialized by kicad-tools at depth 1, keeping the line breaks that preceded it (the kiutils-format LED sheet has a blank line between items; without this the diff spilled one line outside the item). After a save to the Doc's own path, the Doc's baseline is the written text, so a second save splices against it.
- **Final newline.** Save always ends the file with `\n`, as PLAN "Save" says. 24 project symbol libraries (the easyeda2kicad `.kicad_sym` files, format 20211014) have no final newline, so their round trip is byte-identical apart from that added newline (tree-identical). No `.kicad_sch`/`.kicad_pcb` in the set lacks one. The test allows exactly this difference and lists the files.
- **Format list widened (PLAN "Format check" edited, `12a45e2`).** The PLAN list would have refused files the task requires: the power-supply project is KiCad 8 (schematic 20231120, board 20240108), and the tools load project symbol libraries in 20211014 (v8's `sym-lib-table` names `TPS61088RHLR` and `INA219AIDCNR` in `resources/`) and 20231120. Accepted now: schematic 20231120/20250114/20260306, board 20240108/20241229/20260206, symbol library 20211014/20231120/20241209/20251024. The test loads and saves every one.
- Hide: `is_hidden` reads `(hide yes)` on the node, `(hide yes)` in `effects`, and a bare `hide` in either. `hide(doc, n)` does nothing if the node is already hidden in any form, sets an existing `(hide no)` to yes where it is, and otherwise writes the Doc's form: on KiCad 10 schematics and libraries and on boards, on the property after `at`/`layer` (KiCad 10 writes `at, hide, show_name, do_not_autoplace` on placed symbols; embedded library symbols put `hide` after `do_not_autoplace`, which is the same tree apart from order); `(hide yes)` in `effects` on KiCad 8/9; bare `hide` for format majors below 8. It also handles `pin_numbers`/`pin_names`, where the flag is on the node itself.
- `num(x)` gives the shortest exact text (repr; no exponent; `5.0` → `5`). The prototype's `fmt` rounded to 4 decimals, which would cut board coordinates (6 decimals). Phase 6b decides whether `modify.py`'s port rounds before calling `set_num`; kiutils wrote Python `repr`-style floats.
- `to_lists` matches kiutils `parse_sexp` exactly (values and types) on all 5 v8 sheets, in both KiCad 9 and converted KiCad 10 form (one-off check against kiutils in the venv; not in the committed test). That's what `layout_check` needs in Phase 7.

**Task 2, the test (`abc0880`).** `tools/kicad-regress/test_kicad_io.py`, run with `python3 tools/kicad-regress/regress.py iotest <outdir outside the repo>` (about 4 minutes; `--no-k10` skips the KiCad 10 parts). **107/107 PASS** (`p6a/io4.log`).
- (1) Round trip: all 22 `.kicad_sch`/`.kicad_pcb` of the roundtrip set are byte-identical, tree-identical and keep their version token. So are 36 project symbol libraries (24 with the final-newline note above), 225 KiCad 9.0.4 stock libraries and 223 KiCad 10.0.8 stock libraries. The 12 KiCad 10 conversions are byte-identical too.
- (2)/(3) Edits. Each splice save is tree-identical to a plain kicad-tools save of the same edit, and every changed diff line is inside the edited item:

| Edit | KiCad 9 splice | KiCad 9 plain | KiCad 10 splice | KiCad 10 plain |
|---|---|---|---|---|
| R92 Value, TCA sheet (KiCad format) | +4 / −8 | +548 / −1,467 | +4 / −8 | +548 / −1,467 |
| R105 Value, LED sheet (kiutils format on 9) | +97 / −40 (the whole symbol, now in kicad-tools layout) | +3,547 / −1,574 | +4 / −8 | +155 / −421 |
| TPIO44 +0.5 mm in x, v7 board | **+1 / −1** | +361 / −4,596 | **+1 / −1** | +814 / −5,959 |

  On the board the moved footprint's kicad-tools serialization matched KiCad's own layout except the `at` line, so the first board-edit measurement is +1/−1. kicad-cli 10 loads every KiCad 10 result: netlist component/net counts are equal and only the edited Value changes, and DRC counts by type are equal.
- The footprint is TPIO44, not C9: moving C9 by 0.5 mm adds 4 clearance, 1 courtyard and 3 solder-mask-bridge errors on both 9 and 10. That's a real design effect of the move, not an I/O difference, so I picked a footprint whose move changes no DRC count (probe in `p6a/fpprobe/`; TPIO16, BT1 and TP4 also work).
- (4) Refusals: the lock guard refuses `save` and `save_project` with `~*.kicad_sch.lck`, and a board save with `~*.kicad_pcb.lck`; the save goes through once the lock is gone. The format check refuses version 20990101; the pin check refuses 0.30.0 and passes 0.29.0; `save` refuses a schematic or board whose version token was changed, and `save_project` writes nothing when one of its docs has. Each refused file is unchanged.
- (5) `set_num(181.6099)` and `set_num(63.123456789)` land with every digit (the trap: `SExp(value=…)` writes `181.61` and `63.1235`). Hiding on 9 writes `effects:(hide yes)`, and on 10 writes a property-level `(hide yes)` in KiCad's position. `make_property` writes the same forms. Hiding an already-hidden property adds nothing, in each of the three forms (9 effects, kiutils bare, 10 property-level).

**Task 3, kicad-cli 9 reads every KiCad 9 file the test saved.** These checks are part of the test (stages 1b, 2 and 6):
- Netlists of every project root after the round trip are structurally identical to the input's: v8 296/158, v7 93/102, power-supply 50/55, sensor-flex 9/12, sensor-rigid 22/17 (components/nets).
- v7 DRC after the round trip and after the TPIO44 move is equal to the input's by type: 16 clearance and 2 hole_clearance errors, 2 padstack warnings, 0 unconnected, 2 parity.
- Netlists after the TCA and LED edits: 296/158, and only the edited Value changes.
- The v8 copies saved by the refusal and atom stages: 296/158.

**For Phase 6b.**
- Use `kio.num`/`set_num` for every number, and decide on rounding explicitly. The preport parity in Phase 5 relied on 4-decimal inputs.
- `make_property` takes effects text without a hide flag and adds the flag itself. Pass custom effects (justify, a different size) through `effects=`.
- `hide()` returns whether the tree changed. A property built for a KiCad 10 doc already carries `show_name`/`do_not_autoplace`.
- No `ProjectDocs` lives in kicad_io; `modify.py` keeps its own and calls `save_project`.

**Handoff checks.** No tool imports kicad_io yet. `kiutils_k9.py` and every tool are unchanged; `tools/requirements.txt` is unchanged. `git diff 5f162bb HEAD -- hardware lab .githooks` is empty. No lock file or edited KiCad file was ever in the working tree (every write went under `p6a/`). PLAN changed in one place (the format list, above). No new documents; nothing Deferred.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 6 | Phase 6a: The I/O module | DONE | Yes — work beyond the plan, resolvable: the PLAN format list was widened to formats the BRIEF requires the tools to read; the footprint used for the move changed | 3775502 | 4 tasks; `regress.py iotest` 107/107 |

#### Verification
- 3 commits, `12a45e2`..`3775502`. Phase 6a is all `[x]`. `git diff 5f162bb HEAD` on hardware/, lab/, .githooks, tools/requirements.txt and tools/schematic-modify is empty. Nothing outside kicad-io and kicad-regress imports `kicad_io`.
- The Orchestrator re-ran `tools/.venv/bin/python tools/kicad-regress/regress.py iotest` into scratchpad/orch6a: IOTEST PASSED, 107 passed, 0 failed. The tree is clean afterwards.
- **Deviation 1, PLAN edit.** It is limited to the "One I/O module" format-check line. It adds KiCad 8 formats (the power-supply project) and old symbol-library formats (the easyeda2kicad parts v8 uses). This serves BRIEF Scope: the other boards stay unconverted and the tools must still read them. Each added version is round-tripped by the test. Accepted.
- **Deviation 2, TPIO44 instead of C9.** The task names no footprint, and moving C9 changes DRC by design, so TPIO44 was used. Accepted.
- **The final-newline exception** applies to 24 easyeda2kicad `.kicad_sym` files and no `.kicad_sch` or `.kicad_pcb` file. Recorded; it is not an E1/E2 difference against preport, because the files are libraries.
- Carry forward to 6b: `num()` gives exact text, so the port must pick its rounding explicitly to match preport. `make_property(effects=...)` takes hide-free effects text.

---

### Worker #7 — Phase 6b: Port `modify.py`

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 6b — Port `modify.py`
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN in full ("Which layer", "Oracle", "Accepted differences from preport" E2, "Raw-layer traps", "Transient breakage"). SESSION.md Worker #5 Notes (prototype ops and method) and Worker #6 Notes (kicad_io API, num()/rounding, make_property).

Tasks assigned: Phase 6b, all 5 tasks (see TASKS.md)

Notes: Phase 5 prototypes are in scratchpad/p5/scripts/ (ktmod.py, edits.py, cmp_edit.py). The committed test must not depend on the scratchpad. Reference side: a worktree of `kicad10-preport` (remove it after). The only allowed difference from preport is E2, and only after its own commit; anything else, stop and report.
Rules: hardware/ and lab/ unchanged; kicad-cli 10 only on scratch copies; no other tool ported in this phase (callers of modify.py may break; list them for the handoff note).
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p6b/` (test runs `m1`–`m7`; `m5.log` is the passing run before E2, `m7.log` after; `tb/` the transient-breakage probe). My preport worktree `p6b/wt-pre` is removed; `regress.py modtest` makes and removes its own. `KICAD_CLI` unset (9.0.4) except inside the test's KiCad 10 stage; kicad-cli 10 ran only on copies under `p6b/`.

**Task 1, the port (`f17fdd5`).** `tools/schematic-modify/modify.py` loads and saves through `kicad_io` and edits the raw tree only; no kiutils import is left in it. Every public function keeps its name, and its parameters, except `make_property` (below). What changed for callers:
- `SheetDoc(path, doc, instance_path)`: `doc` is the `kicad_io.Doc`; `sheet_doc.schematic` is a property returning `doc.tree` (the raw `kicad_sch` SExp). `ProjectDocs.save_all` runs the lock guard on the root's folder, then `kio.save_project` (splice save, version check).
- Every find helper returns raw SExp nodes: `find_component`, `get_lib_symbol_for`, `find_sheet_ref`, `extract_lib_symbol` (a deep copy of the symbol node; a `.kicad_sym` symbol is renamed to the lib id, units keep their names, as kiutils did). `_symbol_ref`, `_all_ref_set`, `_pin_records`, `_compute_pin_position`, `_compute_stub_endpoint`, `_label_angle`, `_make_wire`, `_make_local_label`, `new_uuid`, `FONT_SIZE`, `WIRE_STUB_LEN`, `KICAD_CLI`, `STOCK_SYMBOLS` keep their names and arguments (the v8 scripts and `tidy_*` use them); the builders return raw nodes.
- **Signature change: `make_property(sheet_doc, key, value, x, y, angle=0, hide=False, effects=None)`** (was `(key, value, pos: Position, hide, prop_id)`, returning a kiutils `Property`). It needs the doc for the version's hide form. Callers: `git grep` finds none outside `modify.py`. `_lib_field` (private) gained the doc too; no outside caller.
- New: `sheet_file_name(sheet)` (reads `Sheetfile` and `Sheet file`), `ANNOTATE_SCRIPT`.
- `annotate_components` takes `annotate.py` from `Path(__file__).parents[1]/schematic-context/` (`ANNOTATE_SCRIPT`); `annotate_script=` still overrides. It still runs `annotate.py` as a subprocess, which is kiutils until Phase 9.
- **Rounding.** None beyond the `round(…, 2)` calls preport already made. Every number is written with `kio.num`, i.e. the same float kiutils wrote with `str(float)`, minus a trailing `.0` (`254.0` → `254`). Accumulated values such as `add_sheet_reference`'s `y + 5.08 + 5.08` stay unrounded, as in preport. So every coordinate is numerically identical to preport's.
- Preport parity kept: one `(pin …)` per pin number (first position, last uuid; a uuid is still minted per record so the seeded sequences match), and (until task 3) E2. New items are written in KiCad's own form: quoted uuids, `(exclude_from_sim no)`, `(fields_autoplaced yes)`, no property `(id N)`, properties via `kio.make_property` (so KiCad 10 docs get property-level `(hide yes)`, `show_name`, `do_not_autoplace`). An embedded library symbol is copied whole (kiutils dropped its `(embedded_fonts no)`; KiCad's own embedded symbols on v8 carry it). The sheet node keeps preport's content (no `in_bom`/`on_board`/`dnp`/`exclude_from_sim`, stroke without type, pins at angle 0 with no justify).

**Task 2, the differential test (`9277d79`).** `tools/kicad-regress/test_modify.py`, run with `python3 tools/kicad-regress/regress.py modtest <outdir outside the repo>` (about 6.5 minutes; `--no-k10`, `--ops a,b`, `--pre REF`). It archives v8 at `v8-schematic-freeze` with resources, makes a worktree of `kicad10-preport` at `<outdir>/wt-pre` and removes it afterwards. Each op runs in its own process per side, with `uuid.uuid4` seeded. Model: Phase 5's `edits.py`/`cmp_edit.py`, extended.
- **Ops (12).** `reads` (project name, root uuid, sheet keys, instance paths, every sheet's ref set, `pin_position` on 177 pins including every pin of every MCU-sheet symbol, the geometry helpers, `extract_lib_symbol` from a `.kicad_sym` and a `.kicad_sch`, `find_sheet_ref`), `add_comp` (4 parts: 0/90/180/270°, stock and sheet-sourced symbols, `stub_len`, default `project_name`, a refused duplicate ref), `remove_comp` (`remove_component`, a miss, `remove_component_with_stubs`), `wires`, `labels` (0/90/180/270), `nc`, `hlabels` (180° and 0° labels, sheet pins on both sides, shape/direction changes, renames, misses, 12 pins until the sheet grows, a refused duplicate pin), `sheet` (`add_sheet_reference` with input, output and default-direction pins; a refused duplicate), `power`, `props` (an existing Value, new hidden properties on a KiCad-format and a kiutils-format sheet, a key and value with a quote and backslash), `pin_net` (stub label rename, no-connect on the pin, `stub_len`, a refused pin), `annotate`.
- **Checks per op on kicad-cli 9:** netlist structurally identical with tstamps; ERC counts by type; plotted strings on every sheet; the ops' return values equal; census. The census check is stricter than Phase 5's eyeball: the census change of each port sheet against the unedited base must equal preport's change against preport's own no-op save (same load/save, no op), except kinds where kiutils writes the same token in another form (`CENSUS_KIUTILS` in the test, each explained: bare uuids, `(id N)`, bare `hide` vs `(hide yes)` with `F:hide` still compared, `(fields_autoplaced)`, dropped `exclude_from_sim` and `embedded_fonts`). `annotate` runs the same `annotate.py` on both sides, so it checks the sheets are byte-identical instead.
- **KiCad 10 stage** (`add_comp`, `remove_comp`, `hlabels`, `sheet`, `power`, `props`, `pin_net`): the port edits a `sch upgrade` copy of the base; preport's KiCad 9 output and no-op save are converted the same way; kicad-cli 10 reads both (netlist, ERC including the 281/332 setup items on both sides, plots, returns). The port's census change against the converted base is printed (only the edit). The census comparison has no exceptions: kicad-cli 10's conversion fills KiCad 10 defaults into preport's new items (`body_style`, `in_pos_files`, a Description property, a sheet's `in_bom`/`on_board`/`dnp`/`exclude_from_sim`), so the port's output is re-saved the same way (`sch upgrade --force` on a copy) before the two changes are compared.
- **Not run on KiCad 10: `annotate`.** On a KiCad 10 file `annotate.py` (kiutils) unhides every property-level-hidden field: the first full run showed plotted strings +26 on LED and +174 on TCA, and 2 of 5 sheets differing from preport's. That is `annotate.py`, not `modify.py` (which only builds the command line); Phase 9 ports it and Phase 12 validates it on 10. Until then, `annotate_components` must not be pointed at a KiCad 10 file.
- **Result before E2: 97/97 PASS** (`p6b/m5.log`): 12 ops on 9, 7 on 10.

**Task 3, E2 (`8e12435`).** `add_sheet_reference` writes `root_doc.path.stem` as the instance project and the keys `Sheetname`/`Sheetfile`. The test's sheet-node check (the new sheet node compared, port against preport, numbers as numbers, uuid quoting and child order ignored) lists the allowed differences per stage in `SHEET_E2_DIFFS`. **97/97 PASS after the fix** (`p6b/m7.log`). Netlist, ERC counts and plotted strings unchanged against preport on both 9 and 10. Tree differences in the new sheet node:
- KiCad 9: exactly three: `instances/project` `motion-play-main` → `motion-play-main-v8`, `Sheet file` → `Sheetfile`, `Sheet name` → `Sheetname`.
- KiCad 10: none. kicad-cli 10's conversion of preport's output already rewrites both the project name and the keys, so preport's converted node equals the port's re-saved node.
- Before the fix (`f17fdd5`) the KiCad 9 sheet node had 0 differences from preport, i.e. the port reproduced preport exactly.

**Task 4, transient breakage (PLAN "Transient breakage").** Checked on a scratch v8 copy (`p6b/tb`) with the ported `modify.py`:
- **Can't run until Phase 7:** `tidy_fields.py` and `tidy_labels.py`, both `--check` and `--apply` (AttributeError on `.schematicSymbols` / `.graphicalItems`: they walk `modify.load_project`'s docs as kiutils objects).
- **Write modes can't run until Phase 7 (`v8_mcu_sheet`) or 8 (`v8_bus_sheet`, `v8_power_sheet`, `v8_debug_sheet`):** `--apply`, `--erc-fixes`, `--fix-11c`, `--fix-11f`, `--annotate`. They pass kiutils objects to and from `modify.py` (7–11 kiutils attribute uses each).
- **Still run:** `v8_mcu_sheet`, `v8_bus_sheet`, `v8_power_sheet`, `v8_debug_sheet` `--check` (CHECK PASSED, PHASE 9/10/11 CHECK PASSED, LAYOUT CHECK PASSED on the scratch root): their checks read kicad-cli netlists, not `modify`'s objects. `layout_check.py` (doesn't import `modify`), `v8_project_setup.py` (doesn't import it), everything in `schematic-context`, `schematic-gen`, `pcb-context`.
- `esp32_integration.py` and `esp32_integration_phase2.py` break too; they are deleted in Phase 8.
- So the harness `regress.py run` will show non-zero exits for `tidy_fields`/`tidy_labels --check` until Phase 7.

**For Phase 7.**
- `tidy_labels` uses `modify._compute_pin_position`, `_label_angle`, `_pin_records`, `get_lib_symbol_for`: all keep their arguments; `_pin_records` and `get_lib_symbol_for` now take and return raw nodes.
- `v8_mcu_sheet` calls `modify._make_wire`/`_make_local_label` and appends to kiutils lists: insert the returned nodes with `kio.insert_item(sheet_doc.schematic, …)`.
- `regress.py modtest` is a model for the `--apply` replays (fresh process per side, seeded uuids, census change against preport's no-op save).

**Handoff checks.** `git status` clean after the last commit. `git diff 24fff46 HEAD -- hardware lab .githooks tools/requirements.txt` is empty. No `p6b` worktree is left (`git worktree list`). No tool other than `modify.py` was changed; `tools/CONTEXT.md` gained one sentence on `modtest` in the kicad-regress entry. PLAN unchanged. No new documents; nothing Deferred.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 7 | Phase 6b: Port `modify.py` | DONE | No — clean completion | 7538dcf | 5 tasks; `regress.py modtest` 97/97 before and after the E2 fix (`8e12435`) |

#### Verification
- 4 commits, `f17fdd5`..`7538dcf`. Phase 6b is all `[x]`. `git diff 24fff46 HEAD` on hardware/, lab/, .githooks, tools/requirements.txt and PLAN.md is empty. `modify.py` no longer imports kiutils.
- The Orchestrator re-ran `regress.py modtest` into scratchpad/orch6b: MODTEST PASSED, 97 passed, 0 failed. The tree is clean afterwards and no worktree is left.
- E2 is the only difference from preport: 3 tree differences on KiCad 9 (the project name and the two sheet keys), none on 10, and netlist, ERC and plot are unchanged. This is inside PLAN's closed list.
- Carry forward:
  - **Transient breakage until Phase 7:** `tidy_fields` and `tidy_labels` (`--check` and `--apply`) and the `v8_mcu_sheet` write modes. `regress.py run` will show non-zero exits for the tidy tools until Phase 7 lands. The `v8_bus`/`power`/`debug` write modes stay broken until Phase 8.
  - **`annotate_components` must not run on a KiCad 10 file until `annotate.py` is ported (Phase 9).** `annotate.py` is still kiutils and unhides fields on 10. No KiCad 10 file is in the working tree, so the risk is limited to scratch work.
  - The `make_property` signature changed. It has no callers outside `modify.py`.

---

### Worker #8 — Phase 7: Tidy tools, `layout_check`, `v8_project_setup`, `v8_mcu_sheet`

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 7 — Tidy tools, layout_check, v8_project_setup, v8_mcu_sheet
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN in full ("Which layer", "Oracle", "Accepted differences from preport", "Raw-layer traps", "Scratch roots for the checks"). SESSION.md Worker #4 Notes (harness, scratch roots), Worker #6 Notes (kicad_io API), Worker #7 Notes and Orchestrator Verification (modify.py API changes, test method, transient breakage).

Tasks assigned: Phase 7, all 4 tasks (see TASKS.md)

Notes: reference side is a `kicad10-preport` worktree (remove after). The only allowed differences from preport are E1/E2 (E2 already landed in modify.py: an --apply replay that adds a sheet reference may show E2's three tree differences, nothing else). Never run --apply against the working tree; replays run on git-archive scratch copies.
Rules: hardware/ and lab/ unchanged; kicad-cli 10 only on scratch copies; no tool outside Phase 7's list ported.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p7/` (`before-wt/`, `after-wt/`, `after2-wt/` working-tree check outputs; `chk/` the `--check` comparisons; `rp/<case>/REPORT.txt` the `--apply` replays; `replay.py` and `seedrun.py` the replay driver and the seeded-uuid runner). Harness run roots `scratchpad/p7rpo1` (ported) and `p7rpr1` (`--tools kicad10-preport`). Preport worktree `p7/wt-pre` (removed at handoff). `KICAD_CLI` unset (9.0.4) throughout; kicad-cli 10 never ran. No write mode ran on the working tree.

**Task 1, `--root` for the write modes (`ed67ed9`).** `v8_mcu_sheet.apply_root_arg` now accepts `--root` with every write mode (`--apply`, `--erc-fixes`, `--fix-11c/f`, `--annotate`) of the four v8 scripts, but refuses (exit 2) a root inside the repository: `--root` means a scratch copy; the working tree is written only without it. `set_root` already moved `ROOT`, `KICAD` and `FP_DIR` (so `v8_power_sheet.write_j7_footprint` and its `fp-lib-table` edit follow the root). `v8_project_setup.py --apply --root <scratch>/hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_sch` creates the project there (the file need not exist; refused inside the repo); the "Copying ..." line prints the absolute path outside the repo. The refusals were tested with in-repo paths that could not write even if the guard failed. Working tree, before vs after (venv, 9.0.4): `v8_mcu/bus/power/debug_sheet.py --check`, `layout_check.py` and `-v` byte-identical (md5 `01b6f14d…` mcu, `51d59021…` bus, `a9971998…` power, `57f49034…` debug, `03326d44…` layout, `55bdccf8…` layout -v, the Phase 4 values). `v8_project_setup --verify --no-v7-compare` on a scratch root: old and new identical.

**Task 2, `tidy_fields`, `tidy_labels`, `layout_check` (`6064f55`).** All three on `kicad_io` (no kiutils import left). `layout_check` reads `kio.to_lists(kio.load_schematic(p).tree)` (new `read_lists`). `tidy_fields` hides fields with `kio.hide` (the file's own form), reads/writes `pin_numbers`/`pin_names` hide flags with `kio.is_hidden`/`kio.hide` (a missing node is inserted after `extends`/`power`/`pin_numbers`, KiCad's order), re-homes `ai_*` fields with the symbol's own `at` text. `tidy_labels` edits label `at` angles with `set_num` and writes `(justify …)` after `font` in `effects`; positions are read as kiutils did (int if integral) so `-v` prints the same; `measure` saves through `kio.save(doc, tmp)`.
- `--check` (and `-v`) identical to preport on scratch v8 (`v8-schematic-freeze`) and v7 (`c2acffc`), for all three tools (exit codes too: v7 layout_check and tidy_labels exit 1 on both sides; v7 has no baseline and its tidy_labels gate blocks).
- `--apply` replays (fresh archive per side, kicad-cli 9 on the copies): `tidy_fields` on v8 @ `8001cc8` (the input of its real apply, `dec1e37`: 536 fields hidden, 34+62 pin flags, 1130 ai moved) and on v7 `c2acffc` (36/3/11/315); `tidy_labels` on v8 @ `8047357` (the input of `e81ab69`: 679 justified, 4 deduped). Each: netlist structurally identical (with tstamps), ERC counts identical, plotted strings identical, tool output identical. Trees: `tidy_labels` tree-equal to preport on all 5 sheets; `tidy_fields` differs only in hide-flag form (preport/kiutils writes bare `hide` on `pin_names`/`pin_numbers`, the port `(hide yes)`, the KiCad 9 form; the `F:hide` count is equal) and, on v7, kiutils' whole-file rewrite (bare uuids, dropped `generator_version` etc.).

**Task 3, `v8_project_setup`, `v8_mcu_sheet` (`f4a4e68`).**
- `v8_project_setup`: `rename_instances` sets each symbol and sheet `instances/project` atom and the title block (`title`, `rev`, `date`; a missing field is inserted in KiCad's order) and splice-saves. `fresh_board` loads the v7 board with `kio.load_board`, removes footprints, tracks/arcs/vias, zones, `gr_*`, groups, dimensions, targets, properties and every net but net 0, and saves with `kio.save(doc, out)`. `--verify` reads the board raw (stackup and item counts, numbers printed as kiutils did). Item counts checked against kiutils on v7's full board: 93 footprints, 1079 tracks, 8 zones, 21 graphics, 103 nets on both.
- `v8_mcu_sheet`: `stock_symbol` returns a raw node (one-level `extends` flatten: the parent's body, the child's properties at the parent's property position, symbol and unit names renamed); the root sheet pin is a raw `(pin … input (at x 55.88 180) (uuid …) (effects (font (size 1.27 1.27))))` inserted after the sheet's last pin (no justify, as preport); wires/labels through `kio.insert_item`; the old IC1 library symbol is removed from `lib_symbols` raw.
- `--verify`/`--check` identical to preport on a scratch root (`--verify` with and without `--no-v7-compare`, `PYTHONHASHSEED=0`: the v7-compare branch prints set-ordered diffs, so it is hash-seed dependent on both sides).
- `--apply` replays. Pre side: the preport scripts refuse `--root` for `--apply`, so the input was placed inside the preport worktree (`wt-pre/hardware/pcb-main-v8/kicad`, scratch) and copied out after; port side `--apply --root` on its own archive. Both sides run through `seedrun.py` (`uuid.uuid4` seeded as in `modtest`).
  - `v8_project_setup --apply` from v7 `c2acffc` (resources at `23c929f` = `1213d24^`, identical to preport's): netlist identical (93/102), ERC counts identical (pin_to_pin 56, lib_symbol_issues 2 real, unconnected_wire_endpoint 1), plotted strings identical, **board DRC counts identical** (invalid_outline 1, 0 unconnected, 0 parity). `.kicad_pro`, lib tables and `libraries/` identical. Sheet trees differ only by kiutils' whole-file rewrite on preport's side; the board keeps v7's `generator_version`, `embedded_fonts` and KiCad 9 `pcbplotparams`, which kiutils dropped or rewrote (99 vs 151 lines). Tool output differs only in the "Copying … ->" path.
  - `v8_mcu_sheet --apply` on v8 @ `1213d24` (= `282259b^`): netlist identical including tstamps (99/101), ERC counts identical, plotted strings identical, tool output identical (both end `CHECK FAILED (3 problems)`, exit 1: today's check expects the later phases' nets; same on both sides). Tree differences only kiutils' forms (bare uuids, bare `hide`, dropped `exclude_from_sim`) and the new sheet pin's child order (port writes KiCad's `uuid` before `effects`). No E2 case arises (no sheet reference is added).

**Other**
- No difference outside E1/E2 was found. E1/E2 did not arise in these replays.
- `v8_bus/power/debug_sheet` write modes still can't run (Phase 8); `mcu.stock_symbol` now returns a raw node, which is what their `add_component` calls will need.

**Harness, after the three ports (`regress.py run`, tools from the working tree at `f4a4e68`'s content).** `run scratchpad/p7rpo1`: every command exits 0, **including `v8/tidy_fields.txt` and `v8/tidy_labels.txt`** (non-zero since Phase 6b). `hash --against reference-k9.txt`: 24/24. `run scratchpad/p7rpr1 --tools kicad10-preport`: every exit 0; `compare p7rpr1 p7rpo1`: COMPARE SAME (every output, including all `v8_*` checks, `v8_project_setup --verify`, `layout_check`, `tidy_*`). Working tree after the ports: the four `v8_*.py --check`, `layout_check.py` and `-v` still byte-identical to the before-capture (`after2-wt/`); `tidy_fields.py --check` and `tidy_labels.py --check` exit 0 with 0 to do.

**Transient breakage now (for Phase 8).** Still can't run: the write modes of `v8_bus_sheet`, `v8_power_sheet` (`--apply`, `--erc-fixes`) and `v8_debug_sheet` (`--apply`, `--fix-11c/f`, `--annotate`); `esp32_integration.py`, `esp32_integration_phase2.py` (deleted in Phase 8). Everything Phase 6b listed for Phase 7 runs again. `annotate.py` is still kiutils: don't point `--annotate`/`annotate_components` at a KiCad 10 file.

**For Phase 8.** `p7/replay.py` (scratchpad) is the replay method: `--pre-in-wt` puts the input inside a preport worktree, because preport's v8 scripts refuse `--root` with write modes; the port side uses `--apply --root`. Both sides run under `seedrun.py` (seeded `uuid.uuid4`), so netlist tstamps compare. Use `PYTHONHASHSEED=0` where a script prints set-ordered output.

**Handoff checks.** `git diff bb4d3c8 HEAD -- hardware lab .githooks tools/requirements.txt` empty. The preport worktree is removed (`git worktree list` shows only the user's Cursor worktrees); `extensions.worktreeConfig` unset. No write mode ran on the working tree; no `.kicad_prl` or lock file appeared. PLAN unchanged. No new documents; nothing Deferred.


#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 8 | Phase 7: Tidy tools, layout_check, v8_project_setup, v8_mcu_sheet | DONE | No — clean completion | c6bcb1b | 4 tasks; 5 `--apply` replays match preport; harness 24/24, COMPARE SAME |

#### Verification
- 4 commits, `ed67ed9`..`c6bcb1b`. Phase 7 is all `[x]`. `git diff bb4d3c8 HEAD` on hardware/, lab/, .githooks, tools/requirements.txt and PLAN.md is empty. None of the five ported tools has a kiutils import line (only comments mention it). No extra worktree is left, and `extensions.worktreeConfig` is unset.
- Orchestrator re-run on the working tree with `tools/.venv` and KiCad 9: `tidy_fields --check` and `tidy_labels --check` exit 0 (the Phase 6b breakage is cleared), and `v8_debug_sheet --check` gives PHASE 11 CHECK PASSED. The tree is clean afterwards.
- The tree differences against preport are kiutils' own forms only (bare `hide` and child order), with equal counts. Netlist, ERC and plots are identical, and no E1 or E2 case arose. This is inside the oracle rule.
- Carry forward: the replay helpers for Phase 8 are at scratchpad/p7/replay.py and seedrun.py. Preport refuses `--root` with write modes, so use `--pre-in-wt`. The phase ran for about 4.3 hours wall-clock, so Phase 8's dispatch keeps the same shape.

---

### Worker #9 — Phase 8: v8_debug_sheet, v8_bus_sheet, v8_power_sheet; delete the v7 schematic scripts

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 8 — v8_debug_sheet, v8_bus_sheet, v8_power_sheet; delete the v7 schematic scripts
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN in full ("Oracle", "Accepted differences from preport", "Raw-layer traps", "Retired"). SESSION.md Worker #7 Notes (modify.py API) and Worker #8 Notes + Orchestrator Verification (replay method, raw stock_symbol node, --pre-in-wt).

Tasks assigned: Phase 8, all 4 tasks (see TASKS.md)

Notes: replay helpers scratchpad/p7/replay.py and seedrun.py. Only E1/E2 differences allowed; anything else, stop and report. Write modes never on the working tree.
Rules: hardware/ and lab/ unchanged; kicad-cli 10 only on scratch copies; no tool outside Phase 8's list ported.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p8/`. It holds `rp/<case>/REPORT.txt` and `pre/`/`port/` for each replay; `chk/out/` for the `--check` and dry-run comparisons; `sweep.log` and `sweep.sh` for task 3; and `mt.log` for modtest. The tools are `replay.py` (Phase 7's, plus `--src DIR` to replay from a built input instead of `git archive`), `normeq.py` (a tree compare with kiutils' forms folded: quoting, number text, bare `hide`, and dropped `exclude_from_sim`/`embedded_fonts`/property `id`/`fields_autoplaced`; it lists every remaining difference) and `noerc.py` (below). The preport worktree `p8/wt-pre` is removed. `KICAD_CLI` was unset (9.0.4) throughout, and kicad-cli 10 never ran. No write mode ran on the working tree.

**Task 1, the three ports (`c464817`).** None of them imports kiutils now.
- `v8_bus_sheet`: `_check_free` reads raw wires, labels and symbols. New helpers `set_paper(doc, size)` and `set_at(node, x, y, angle)` are also used by the other two scripts. The hlabel rename and move, the R28/R29 LCSC edit and the sheet pin's angle (`set_num` on the `at`) are raw.
- `v8_power_sheet`: the `#PWR` Value retargets go through `set_str`. New `rename_labels(doc, old, new)` serves the rail labels and the ERC-fix `I2C_PU_RAIL` rename. DNP parts get `(dnp yes)` and `(in_bom no)` through `set_bare`.
- `v8_debug_sheet`: `rename_ref` covers properties and the `instances/project/path/reference`. `fix_11c` works raw on the wire delete, the label move with `(justify right bottom)` after `font`, and the SW1 wire end. Its embedded-symbol refresh test compares `_norm` of both nodes. `_norm` folds what kiutils' `to_sexpr()` never saw (quoting, number text, bare `hide`, `exclude_from_sim`, `embedded_fonts`, property `id`). `fix_11f` saves only the LED sheet with `kio.save(led.doc)` after `assert_not_open`.
- **`annotate.py` is not ported (Phase 9).** `--annotate` and `--fix-11f` used `annotate.write_ai_properties`, which is kiutils. `v8_debug_sheet.write_ai_properties(sheet_doc, symbol, props)` does the same thing on the raw tree: an existing `ai_*` field is re-homed (effects added if missing, hidden in the file's form, at the symbol origin with angle 0) and its value updated; a new one is appended hidden at the origin. It returns the same action lines. When Phase 9 ports `annotate.py`, it can replace this function.
- **`--check`** (and the dry run), preport vs port on a scratch v8 at `v8-schematic-freeze` with `PYTHONHASHSEED=0`: identical for all three, every one PASSED. The dry runs differ only by the `--root ... (a replay)` docstring line that Phase 7 task 1 added. On the working tree, `v8_mcu/bus/power/debug_sheet.py --check` still hash `01b6f14d`/`51d59021`/`a9971998`/`57f49034` (Phase 4's values).
- **`--apply` replays** (preport with `--pre-in-wt`, port with `--root`, both under seeded uuids and kicad-cli 9). The netlist (with tstamps), the ERC counts, the plotted strings and every non-schematic file in the project (J7 footprint, `fp-lib-table`) are identical in all 8 cases. `normeq` is EQUAL on every sheet unless noted.
  - `v8_bus_sheet --apply` @ `282259b` (= `c5241b9^`). Root sheet: 8 differences, all the child order of the 4 new sheet pins (the port writes KiCad's `uuid` before `effects`), as in Phase 7.
  - `v8_power_sheet --apply` @ `c5241b9` (= `dae1935^`).
  - **`v8_power_sheet --erc-fixes`.** No commit holds its input (`--apply` and the fixes landed together in `dae1935`). So the input was built by running preport's `--apply` on `c5241b9` with `erc_fixes` stubbed (`noerc.py`, seeded), and both sides then ran `--erc-fixes` on copies of it (`replay.py --src`). It adds `#FLG102`/`#FLG103` and renames 11 labels, the same on both sides.
  - `v8_debug_sheet --apply` @ `dae1935` (= `80036ff^`, the full Phase 11).
  - `v8_debug_sheet --apply` @ `dec1e37` (= `8047357^`, the 11c-only path).
  - `v8_debug_sheet --annotate` @ `80036ff` (= `dbad731^`). Both sides exit 1 with the same "not found" list, because today's `annotations()` includes the 11c and 11f parts.
  - `v8_debug_sheet --fix-11c` @ `e81ab69` (= `e365da3^`). The same "done" lines on both sides, so the refresh decision matched.
  - `v8_debug_sheet --fix-11f` @ `29904f6` (= `654ede6^`). LED sheet: the only difference is `generator_version`, which preport's `kiutils_k9.save_schematic` drops and the port keeps from the input.
  - Tool output is identical, apart from replay artifacts. In 3 replays, both sides end in the same `KeyError: 'R105.2'` traceback in `check()` (today's check expects later parts; it runs after the save), and only the paths and line numbers differ. In 2, the layout-check header is repo-relative on the preport side because its input sat inside the worktree.
- No difference outside E1/E2 was found. Neither E1 nor E2 came up (no sheet reference is added).

**Task 2 (`55e7e19`).** `esp32_integration.py` and `esp32_integration_phase2.py` are deleted. The `tools/CONTEXT.md` table row is removed. In `tools/schematic-modify/CONTEXT.md` the Current Files line is removed and Typical Workflow step 1 now reads "Run an initiative's script built on `modify.py` (for example `v8_bus_sheet.py --apply`)". `git grep -E "esp32_integration(\.py|_phase2)"` finds them only in the archive initiative, `docs/research/`, the v8 SESSION and this initiative's PLAN/TASKS/SESSION. The `ai_role` value `esp32_integration_phase_1c` in `hardware/` files is design data, not the script name, and it stays.

**Task 3 (`ddfe68d`).** The remaining `modify.py` importers are `tidy_fields`, `tidy_labels`, `v8_mcu/bus/power/debug_sheet` and `kicad-regress/test_modify.py`. The sweep (`sweep.sh`) ran on a scratch v8 at HEAD: every dry run, `--check` and write mode of those scripts. The `--apply` and `--erc-fixes` modes that are already applied refuse. `v8_debug_sheet --apply`, `--fix-11c` and `--fix-11f` are idempotent and PASS. `--annotate` annotated 228 parts. The `tidy_*` `--check` and `--apply` runs exit 0. Afterwards the netlist is equal, and all 5 sheets are byte-identical to HEAD (the splice save rewrote nothing). `regress.py modtest --no-k10`: MODTEST PASSED, 60/60. The Phase 6b transient-breakage list is empty.

**For later phases.**
- `tools/schematic-modify/CONTEXT.md` still says the `v8_*.py` scripts "refuse [`--root`] with any mode that writes", which Phase 7 task 1 changed. It also still describes `kiutils_k9.py` and says `v8_project_setup` renames "via kiutils". These lines are outside this phase's task. They belong in the Phase 11 docs pass.
- Do not run `annotate.py` itself, or `modify.annotate_components`, on a KiCad 10 file until Phase 9. `v8_debug_sheet --annotate` no longer goes through it.

**Handoff checks.** `git diff 249fac3 HEAD -- hardware lab .githooks tools/requirements.txt docs/initiatives/kicad10-tooling/PLAN.md` is empty. No `p8` worktree is left, and `extensions.worktreeConfig` is unset. No new documents; nothing Deferred.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 9 | Phase 8: v8_debug/bus/power_sheet; delete the v7 schematic scripts | DONE | No — clean completion | 2b261ea | 4 tasks; 8 `--apply` replays match preport; both esp32_integration scripts deleted |

#### Verification
- 4 commits, `c464817`..`2b261ea`. Phases 1–8 (with 6a and 6b) have their Handoffs `[x]` and nothing later is ticked: the Worker's slip that ticked every Handoff was reverted before commit. `git diff 249fac3 HEAD` on hardware/, lab/, .githooks, tools/requirements.txt and PLAN.md is empty. No `v8_*.py` imports kiutils. Both esp32_integration scripts are gone. No extra worktree is left.
- Orchestrator re-run on the working tree: `v8_debug_sheet --check` gives PHASE 11 CHECK PASSED. The tree is clean afterwards.
- Carry forward:
  - **`v8_debug_sheet.py` has its own raw-tree `write_ai_properties`.** It is a stop-gap for `annotate.write_ai_properties`, which is still kiutils. Phase 9 should replace it with the ported `annotate.py` function so there is one copy.
  - **Stale doc lines for Phase 11/17's docs pass** in `tools/schematic-modify/CONTEXT.md`: "v8_*.py refuse --root with write modes" (Phase 7 changed this), the `kiutils_k9.py` description, and "v8_project_setup renames via kiutils".

---

### Worker #10 — Phase 9: schematic-context and schematic-gen

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 9 — schematic-context and schematic-gen
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN in full ("Which layer", "Oracle", "Accepted differences from preport", "Raw-layer traps"). SESSION.md Worker #6 Notes (kicad_io API), Worker #8/#9 Notes + Orchestrator Verifications (replay method, kiutils-form folding, write_ai_properties stop-gap). tools/schematic-context/README.md.

Tasks assigned: Phase 9, all 3 tasks (see TASKS.md)

Notes: after annotate.py is ported, point v8_debug_sheet's write_ai_properties at it (one copy) and show debug --annotate/--fix-11f replays still match. Generators write only to scratch. Only E1/E2 differences allowed.
Rules: hardware/ and lab/ unchanged; kicad-cli 10 only on scratch copies; board readers are Phase 10.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p9/`. Read-tool runs `rd/` (`rd.sh`, `rdcmp.py`, `rd/cmp.txt`); annotate CLI replays `an/` (`ann.sh`, `anncmp.py`, `an/cmp_gv.txt`); KiCad 10 hide check `k10h/` (`k10hide.sh`, `hidecensus.py`); debug replays `rp/` (`replay.py`, `dbg_all.sh`, `dbg.log`, copied from p8); generators `gen1/`, `gen2/` (`gen.sh`, `gencmp.py`); modtest `mt-ann2.log`; harness roots `scratchpad/p9rpo1` (ported) and `p9rpr2` (`--tools kicad10-preport`). My preport worktree `p9/wt-pre` is removed. `KICAD_CLI` unset (9.0.4); kicad-cli 10 ran only on copies under `p9/` (modtest's KiCad 10 stage and `k10h/`). No tool wrote to the working tree.

**Task 1 (`5de9a72`, log wording `df5b6de`).** `extract.py`, `annotate.py`, `show.py` read the raw tree through `kicad_io` (no typed views were needed); none imports kiutils.
- `extract.py`: `read_kiutils_properties` is now `read_schematic_properties` (no outside caller); sheets, sheet pins, wires and hierarchical labels are read raw (`Sheetfile`/`Sheet file`, `Sheetname`/`Sheet name`). Without kicad-tools (not the venv) it still falls back to the netlist-only path, as preport did without kiutils. The stderr line "Reading schematic properties via kiutils..." is kept word for word, with a comment: the harness reference hashes `extract_sheetpins.txt`, which captures stderr (a reworded line made it 23/24). Phase 11 can reword it and re-record that hash.
- `annotate.py`: `write_ai_properties(doc, symbol, props)` (a `kio.Doc` and a raw symbol node) is the one writer of `ai_*` fields. It hides with `kio.hide` (the file's own form), homes the field at the symbol's `at` text, adds new fields after the last property, and saves all edited sheets with one `kio.save_project` (lock check first). `clear_ai_properties` removes raw nodes.
- **One copy.** `v8_debug_sheet.py` imports `annotate.write_ai_properties` (passing `sheet_doc.doc`); its stop-gap is deleted.
- **Read-tool compare** (preport worktree vs working tree, fresh archives, KiCad 9): v8 @ `v8-schematic-freeze`, v7 `c2acffc`, plus sensor-rigid and sensor-flex at HEAD. `circuit-context.json` with and without `--previous` (v8, v7) and plain (all four): every leaf identical apart from `source/extracted_at` (timestamp) and `_provenance` (`generator_commit` gains `-dirty`, hence the 6-byte "Wrote … bytes" difference). `--check-sheet-pins` and `-v`: identical (v8 42 pins, v7 37, 0 unresolved). `show.py` plain, `--unannotated`, `--sheet led_controller`: identical on all four.
- **annotate CLI replay** (`ann.sh`, 8 commands per project on v8 and v7: update, multi-ref with `--`, new fields, a root-sheet part, `--clear`, a missing ref, a partial miss, a bad key). Every command's output and exit code identical. kicad-cli 9 netlist, ERC counts and plotted strings identical. Trees (`normeq_gv`): equal on every sheet except the root, where preport's kiutils save drops each sheet node's `(exclude_from_sim no) (in_bom yes) (on_board yes) (dnp no)`; the port's sheet nodes are the input's own (checked against the archive). That is a kiutils form, not an E1/E2 case. The splice save changes only the edited symbols' text.
- **modtest** (`test_modify.py`): the `annotate` op used to require byte-identical sheets (the same kiutils `annotate.py` ran on both sides). Now it runs the census path (a preport sheet `annotate.py` didn't save counts as unchanged), adds an `ai fields` check (every `ai_*` field's value, hidden flag and position, preport against port; the census counts kinds, so it can't see a value change), adds `critical_specs` to the op so the "added" path runs, and runs on KiCad 10 too (`K10_OPS`). `regress.py modtest --ops annotate`: 13/13 PASS (1142 ai fields equal on 9 and on 10).
- **KiCad 10 hide round trip** (`k10hide.sh`): v8 converted with kicad-cli 10 on a scratch copy, then 5 ported `annotate.py` commands. Every `ai_*` field (1140) carries exactly one flag, the property-level KiCad 10 form; no effects-level `hide` was added; property-level hides +2 (new fields) and −4 (`--clear`); kicad-cli 10 plotted strings before and after are identical. So the field-unhiding Worker #7 saw is fixed.
- **Debug replays after the switch** (`dbg_all.sh`): `--annotate` @ `80036ff` and `--fix-11f` @ `29904f6`: netlist, ERC counts and plotted strings identical to preport; `normeq_gv` EQUAL on all 5 sheets; other files the same. Tool output identical, apart from Phase 8's known artifact in `--fix-11f` (the layout-check header is repo-relative on the preport side because its input sat inside the worktree). The port's 5 sheets are byte-identical to Phase 8's port outputs (the stop-gap's) in both replays.

**Task 2 (`09b5e42`).** `generate_power_sheet.py`, `generate_esp32_sheet.py`, `poc_generate.py` on `kicad_io`; none imports kiutils.
- New in `kicad_io`: `new_doc(path, text)`, a Doc for a file that doesn't exist yet, from template text (same format check as a load; `_load` now goes through `_from_text`). `Schematic.create_new()` becomes `SHEET_TEMPLATE` (version, generator, uuid, A4 paper, empty `lib_symbols`, `sheet_instances` page 1), saved with `kio.save`. Library symbols come from `modify.extract_lib_symbol`; items are raw nodes in KiCad 9 form (quoted uuids, `(exclude_from_sim no)`, `(hide yes)` in effects), inserted with `kio.insert_item`. Preport parity kept: one `(pin …)` per pin number (first position, last uuid, a uuid per record), the same uuid order, and the generators' mirror handling (pins mirrored, symbol not).
- **Inputs.** `spec.json` and `poc_generate.py` name `hardware/pcb-main/kicad/3v3_Power_Supply.kicad_sch`, deleted in `fd632ef`, and every `--output` default points into v7's folder. So `gen.sh` builds a scratch "repo root" per side (a copy of the tools, HEAD's `hardware/pcb-main/kicad`, resources and `pcb-power-supply/kicad`, plus that file from `fd632ef^`), runs each generator from it with seeded uuids and an explicit `--output` under it. The esp32 spec also reads the JLC-MCP libraries under `~/Documents/KiCad/9.0/3rdparty` (read only). Added to Deferred.
- **Result** (`gen2/cmp.txt`, after the final edit): for all three, the kicad-cli 9 netlist (with tstamps; the `Sheetfile` path normalized) is identical, ERC counts are identical (power: 6 pin_not_connected and 1 pin_not_driven errors on both; esp32: 26 label_dangling, 37 pin_not_connected on both; these are the generators' own), plotted strings identical, tool output identical, `normeq_gv` EQUAL. Census differences are kiutils' forms only: `generator` quoted, bare `hide`, dropped `exclude_from_sim`/`embedded_fonts`.

**Harness.** `regress.py run scratchpad/p9rpo1` (working tree): no non-zero exits, `hash --against reference-k9.txt` 24/24. `run scratchpad/p9rpr2 --tools kicad10-preport` then `compare p9rpr2 p9rpo1`: COMPARE SAME. `regress.py iotest --no-k10` (after `new_doc`): 71/71 PASS. Note: `--python` must be an absolute path when `--tools` is given (a relative one fails inside the worktree), and a run root outside `scratchpad/` changes the netlist byte count `extract.py` prints, so `hash --against` needs a root of the reference's length (`scratchpad/<6 chars>`).

**For later phases.**
- Phase 11: `extract.py`'s "via kiutils" log line (above). `tools/schematic-context/README.md` already names the venv and `kicad_io` (I changed its three kiutils lines); the `tools/schematic-modify/CONTEXT.md` lines Worker #9 listed are still stale, plus its `annotate.py`/kiutils_k9 sentence.
- Phase 12: `annotate.py` and `modify.annotate_components` are now safe on KiCad 10 files.
- No E1 or E2 case arose. No difference outside the kiutils forms listed.

**Handoff checks.** `git diff 5f31380 HEAD -- hardware lab .githooks tools/requirements.txt docs/initiatives/kicad10-tooling/PLAN.md` is empty. `git worktree list` shows only the user's Cursor worktrees; `extensions.worktreeConfig` unset. PLAN unchanged. One Deferred line added (generators). No new documents.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 10 | Phase 9: schematic-context and schematic-gen | DONE | No — clean completion | 2641aac | 3 tasks; read tools identical to preport; annotate replays and 3 generators match; one `write_ai_properties` |

#### Verification
- 4 commits, `5de9a72`..`2641aac`. Phase 9 is all `[x]`. `git diff 5f31380 HEAD` on hardware/, lab/, .githooks, tools/requirements.txt and PLAN.md is empty. No extra worktree is left.
- Remaining kiutils importers: `pcb-context/board_model.py`, `extract.py`, `routing_extract.py`, `tools/route_esp32.py`, `tools/verify-routing.py` (all Phase 10), and `kiutils_k9.py` (Phase 11). That is exactly the plan.
- Orchestrator re-run: `regress.py modtest --ops annotate` gives 13/13 PASS, and the working-tree `v8_debug_sheet --check` gives PHASE 11 CHECK PASSED. The tree is clean afterwards.
- **Test change, accepted.** `test_modify.py`'s `annotate` op no longer requires byte-identical sheets, because preport and port now run different `annotate.py` code. It now uses the census check plus a field-level check of every `ai_*` field's value, hide flag and position, and it also runs on KiCad 10. The strictness moved to what matters. The replays against preport still compare netlist, ERC, plots and the folded tree.
- **API addition: `kicad_io.new_doc(path, text)`**, which builds a Doc from a template with the same format check as a load. iotest gives 71/71 (`--no-k10`) per the Worker.
- **The KiCad 10 annotate hazard (Worker #7) is cleared**: on a converted v8, every `ai_*` field has exactly one hide flag, in KiCad 10's form.
- Carry forward to Phase 11:
  - Reword `extract.py`'s "via kiutils" stderr line and re-record that harness hash.
  - Stale lines in `tools/schematic-modify/CONTEXT.md`.
  - A Deferred line was added: the generator defaults point into v7's folder, and the specs name a deleted file.

---

### Worker #11 — Phase 10: Board readers; delete route_esp32.py

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 10 — Board readers; delete route_esp32.py
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN in full ("Which layer", "Raw-layer traps", "Accepted differences from preport" E1). SESSION.md Worker #5 Notes (board-read prototype, the six typed-PCB corrections, the 13 kiutils misreads) and Worker #6 Notes (kicad_io). tools/pcb-context/README.md.

Tasks assigned: Phase 10, all 4 tasks (see TASKS.md)

Notes: Phase 5 board prototype at scratchpad/p5/scripts/board_values.py. E1 is the only allowed difference; list each E1 leaf (old, new, file token) in SESSION. hardware/pcb-main/kicad/board-model/ is not regenerated. KICAD_CLI on 9.
Rules: hardware/ and lab/ unchanged; kicad-cli 10 only on scratch copies; kiutils_k9.py and requirements stay (Phase 11).
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p10/` (`v7/` and `v7k10/` archives of `c2acffc`, `scripts/attrcmp.py`, `scripts/leafdiff.py`, `scripts/rd.sh`, reader outputs `rd/pre`, `rd/por`, KiCad 10 smoke outputs `k10-board-model.json`, `k10rd/`); harness roots `scratchpad/p10po1` (ported, task 1), `p10po2` (ported, HEAD `606d44f`), `p10pr1` (`--tools kicad10-preport`). My preport worktree `p10/wt-pre` is removed. `KICAD_CLI` unset (9.0.4); kicad-cli 10 ran once, `pcb upgrade` on the `p10/v7k10` copy. Nothing written under hardware/ or lab/.

**Task 1 (`1c20f31`).** New `tools/pcb-context/pcb_raw.py`: read-only views over `kicad_io.load_board`'s raw tree (no typed `PCB`). They keep kiutils 1.4.8's class names, attribute names and attribute sets (the readers test `type(g).__name__` and `hasattr`), and kiutils' reading of absent tokens (defaults listed per class: zone `netName` "unknown", clearance/min_thickness 0.254, segment width 0.1, arc 0.2, pad drill/net/pinfunction None, …). Numbers come through `kio.to_lists`, so they have kiutils' types. Custom pads: `customPadOptions.anchor` (default `rect`) and `customPadPrimitives` (Gr* views) are read raw. `board_model.py` loads with `pcb_raw.load` and reads `connect_pads` as `z.connectPads`; nothing else in it changed. `board_model.py` still doesn't sort its DRC list (Worker #4 left it to this phase): I left it, because sorting would change the output against preport; the harness sorts it.
- **Attribute check** (`attrcmp.py`, every attribute pcb_raw defines against kiutils, item by item, v7 `c2acffc`): 73,386 values; differences only in `width` of graphics: the 2 board `gr_rect`s (E1) and 1,188 footprint graphics, where kiutils sets `width` None when a `stroke` is present and pcb_raw reads the stroke width. No reader reads footprint graphic widths (the outputs below are identical).
- **Gate.** Harness `p10po1`/`p10po2` against `p10pr1`: every output IDENTICAL/EQUAL except `v7/board-model.json`, 144 differing leaves, all E1. `net-report.json/.md`, `plane-report.json/.md`, `net_report.txt`, `plane_report.txt`, `board_model.txt` and `pads_U5_C21_C9.txt` identical. `po1` vs `po2` (after tasks 2-3): SAME at tol 0. `hash --against reference-k9.txt`: 23/24; the miss is `v7/board-model.json` (E1).
- **E1 leaves** (old = preport, new = port, token = v7 `c2acffc` board file):

| Leaf | Old | New | File token |
|---|---|---|---|
| `zones[0]/connect_pads` (BOOST_SW, F.Cu) | null | `"yes"` | `(connect_pads yes (clearance 0.3))`, line 37847 |
| `zones[1]/connect_pads` (U6-5V, F.Cu) | null | `"yes"` | `(connect_pads yes (clearance 0.3))`, line 37887 |
| `zones[3]/connect_pads` (U8_3.3V_POUR, F.Cu) | null | `"yes"` | `(connect_pads yes (clearance 0.3))`, line 37996 |
| `zones[6]/connect_pads` (5V_PLANE, In2.Cu) | null | `"yes"` | `(connect_pads yes (clearance 0.3))`, line 39549 |
| `zones[7]/connect_pads` (3V_PLANE, In2.Cu) | null | `"yes"` | `(connect_pads yes (clearance 0.3))`, line 40979 |
| `graphic_copper[0]/polygon[0]` (the F.Cu `gr_rect` 78.4,116.5 to 79.9,118; 129 exterior + 10 hole leaves) | buffered at 0.12/2: exterior bbox 78.34,116.44 to 79.96,118.06; hole 78.46,116.56 to 79.84,117.94 | buffered at 0.2/2: exterior bbox 78.3,116.4 to 80.0,118.1; hole 78.5,116.6 to 79.8,117.9 | `(stroke (width 0.2) (type default))`, line 28918 |

  Zones 2, 4, 5 stay null: their `(connect_pads (clearance …))` has no type atom (lines 37929, 38037, 38069). The Edge.Cuts `gr_rect` (`(stroke (width 0.05)`, line 28929) feeds no leaf: `graphic_copper` takes copper layers only and the outline doesn't use width.
- **KiCad 10 smoke** (read-only, `board_model.py --no-drc` on `p10/v7k10`, made with kicad-cli 10 `pcb upgrade`; format 20260206): **loads**, 93 footprints, 362 pads, 102 nets, 855 segments, 224 vias, 8 zones. Against the KiCad 9 port model, apart from the skipped DRC block and `kicad_format_version`, one leaf differs: `zones[4]/net` (the antenna keepout) `''` → `"unknown"`. KiCad 10 writes that zone with no `net`/`net_name` at all, and pcb_raw keeps kiutils' absent default "unknown". For Phase 13 (PLAN lists "a keepout zone with no net"); decide there whether absent should read `''` on 10. pcb_raw handles KiCad 10's name-only nets: an item's `net` is the name, and `Board.nets` is synthesized from the names used.

**Task 2 (`39f0bbc`).** `pcb-context/extract.py`, `routing_extract.py` and `tools/verify-routing.py` load with `pcb_raw.load` (only the import and load lines changed; extract.py's unused `Position` import dropped). Run (`rd.sh`) on fresh `c2acffc` archives, preport worktree vs working tree, every output to scratch: `extract.py` plain, `--pads`, `--pads --schematic-context /nonexistent.json`; `routing_extract.py -o` and `--list-nets`; `verify-routing.py --output-dir` (exit 1 on both: 3 FAIL checks, the board's own). Every JSON, Markdown, stdout, stderr and exit code identical; the only differing lines are the 4 `extracted_at` and 1 `generated_at` timestamps. The source board's md5 unchanged. No E1 field reaches them (outputs identical). On the KiCad 10 copy all three run: extract `--pads` identical, verify-routing identical apart from the file sha256, routing_extract differs in `net_number` (names on 10) and the NPTH pad's `*.Cu` bbox key; Phase 13.
- Doc lines: `tools/pcb-context/README.md` intro (readers on kicad_io + pcb_raw) and `tools/CONTEXT.md` board-model paragraph's "(kiutils + kicad-cli)". Left for Phase 11: README "kiutils ≥ 1.4.8" dependency line (246), CONTEXT kiutils Rule, line 57 and line 156, and `place_power.py`'s docstring "via kiutils" (it writes by text replacement and imports no kiutils).

**Task 3 (`606d44f`).** `tools/route_esp32.py` deleted. `git grep route_esp32`: only this initiative's PLAN, SESSION and TASKS (history); no other doc line. Remaining kiutils importer under `tools/`: `schematic-modify/kiutils_k9.py` only (Phase 11).

**Handoff checks.** `git status` clean. `git diff 6498283 HEAD` on hardware/, lab/, .githooks, tools/requirements.txt, `kiutils_k9.py` and PLAN.md is empty. `git worktree list`: only the user's Cursor worktrees; `extensions.worktreeConfig` unset. No new documents (pcb_raw.py is code), nothing Deferred, PLAN unchanged.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 11 | Phase 10: Board readers; delete route_esp32.py | DONE | No — clean completion | 5efc551 | 4 tasks; new `pcb-context/pcb_raw.py` views; only E1 differs (144 leaves); route_esp32.py deleted |

#### Verification
- 4 commits, `1c20f31`..`5efc551`. `git diff 6498283 HEAD` on hardware/, lab/, .githooks, tools/requirements.txt, kiutils_k9.py and PLAN.md is empty. The only kiutils importer left is `tools/schematic-modify/kiutils_k9.py`. route_esp32.py is gone. No extra worktree is left.
- Orchestrator re-ran `regress.py run` (ported tools, venv, KiCad 9) into scratchpad/orc10a. No exit is non-zero. 23/24 reference hashes match; the miss is `v7/board-model.json`. `compare` against the Worker's preport run `p10pr1` shows one differing item, `v7/board-model.json`, with 144 leaves, all of them `graphic_copper` polygon points or zone `connect_pads`. That is exactly PLAN E1. The tree is clean afterwards.
- Carry forward:
  - **Phase 11:** `reference-k9.txt` still holds the preport board-model hash. Re-record it for the ported reader, and cite E1 and the SESSION leaf list in the file, so later harness runs report 24/24.
  - **Phase 13:** on KiCad 10, a zone with no net token reads "unknown" rather than `''` (kiutils' default for an absent token). Decide what it should read on 10. `routing_extract` shows net names instead of net numbers on 10.
  - **Phase 11 docs:** the "kiutils ≥ 1.4.8" line in the pcb-context README, the kiutils lines in `tools/CONTEXT.md`, the `place_power.py` "via kiutils" docstring, the `extract.py` stderr line (Worker #10), and the stale `tools/schematic-modify/CONTEXT.md` lines (Worker #9).

---

### Worker #12 — Phase 11: Remove kiutils; KiCad 9 reads; the parser rule

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 11 — Remove kiutils; KiCad 9 reads; the parser rule
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN in full ("Pin and upgrades", "One I/O module", "Which layer", "Raw-layer traps", "Accepted differences from preport"). SESSION.md Orchestrator Verifications for Workers #9, #10, #11 (the doc-line carry-forwards and the reference-k9 re-record). Worker #4 Notes (harness).

Tasks assigned: Phase 11, all 4 tasks (see TASKS.md)

Notes: also re-record reference-k9.txt's board-model hash for the ported reader (cite E1), reword extract.py's "via kiutils" stderr line and re-record that hash; both re-records only after the final preport compare. Old venv backup before rebuilding. Only E1/E2 differences allowed.
Rules: hardware/ and lab/ unchanged; kicad-cli 10 only on scratch copies; global python3 and .githooks unchanged.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p11/` (logs `*.log`, iotest/modtest outdirs `io1`, `io2`, `mt1`–`mt3`, KiCad 9 archive copies `k9src`, round-trip outputs `k9out` with script `k9reads.py`, extract outputs `ext` (port) and `extpre` (preport)); harness run roots `scratchpad/p11po1` (ported, old venv), `p11pr1` (`--tools kicad10-preport`, old venv), `p11po2` (after the extract.py reword), `p11po3` (rebuilt venv). **The pre-Phase-11 venv (with kiutils) is saved at `scratchpad/p11/venv-old`.** `KICAD_CLI` unset (9.0.4) throughout; kicad-cli 10 ran only inside iotest/modtest's own scratch copies. The global `python3` is still pyenv 3.7.3; `.githooks` untouched.

**Task 1 (`e80dedf`).** Final compare on the old venv, KiCad 9:
- Harness: `p11po1` and `p11pr1` both exit 0 on every command. `compare p11pr1 p11po1`: one item, `v7/board-model.json`, 144 leaves, classified by script: 139 under `graphic_copper[0]/polygon[0]` and `zones[0,1,3,6,7]/connect_pads` null → `"yes"`. That is exactly E1 and Worker #11's leaf list. `p11pr1` 24/24 against the old reference, `p11po1` 23/24 (the board model).
- `iotest`: IOTEST PASSED 107/107. `modtest`: MODTEST PASSED 105/105 (97 at Phase 6b plus the annotate checks added in Phase 9); the sheet node differs from preport in 3 places on KiCad 9 (E2) and 0 on KiCad 10.
- Re-records (after the compare): `extract.py`'s stderr line now reads "Reading schematic properties via kicad_io..." (the old comment pinning the wording is gone). `compare p11po1 p11po2 --tol 0`: only that line differs. `reference-k9.txt`: `v7/board-model.json` `84df69225ee16b00` → `6994b724e9f71528`, with a note citing E1 and Worker #11's leaf list; `v8/extract_sheetpins.txt` `d4d54268519deb64` → `804e174e87ed142b`, with a note. Both old hashes are kept in the comments.
- Removal: `tools/schematic-modify/kiutils_k9.py` deleted; `kiutils==1.4.8` dropped from `tools/requirements.txt` (the kicad-tools comment now names the I/O-module Rule). `tools/.venv` moved to the scratchpad, rebuilt with `/usr/local/bin/python3.13 -m venv`, pip 26.3, `-r tools/requirements.txt`: 24 packages, `pip check` clean, and the freeze differs from the old one only by `kiutils==1.4.8`. `git grep -E '^\s*(import kiutils|from kiutils)' -- tools ':!tools/.venv'` finds nothing. `tidy_fields.py`'s docstring says kiutils_k9 was removed; `regress.py` no longer calls the reference "kiutils".
- On the rebuilt venv: harness `p11po3` 24/24 against the updated reference and `compare p11po2 p11po3 --tol 0` SAME; iotest 107/107.
- **The preport oracle no longer runs on `tools/.venv`.** `modtest --ops reads` on the new venv fails on the preport side (`ModuleNotFoundError: No module named 'kiutils'`, `mt3.log`); `run --tools kicad10-preport` fails the same way. Both run with `--python` set to a venv built from the tag's own requirements file, which has kiutils and kicad-tools 0.29.0: `modtest --python scratchpad/p11/venv-old/bin/python` passed 105/105 (`mt2.log`). The recipe (`git show kicad10-preport:tools/requirements.txt`, then a venv from it) is in the `regress.py` docstring and the `tools/CONTEXT.md` harness entry. That file is the one `venv-old` was built from (`git diff kicad10-preport 11af873 -- tools/requirements.txt` is empty).

**Task 2 (`78209cf`).** `git archive` copies: v7 at `c2acffc`; sensor-rigid, sensor-flex and power-supply (kicad + resources) at HEAD. `kicad_io.load` + `save` to a separate tree on the rebuilt venv: all 16 `.kicad_sch`/`.kicad_pcb` files are tree-identical and byte-identical, and every version token is unchanged (v7 and sensors 20250114/20241229; power-supply KiCad 8, 20231120/20240108). `extract.py` on each schematic project into scratch: all four exit 0 (v7 93 components, power-supply 50, sensor-flex 9, sensor-rigid 22; 37/12/0/0 sheet pins, 0 unresolved). Cross-check: preport's `extract.py` (temporary worktree, old venv, removed afterwards) on the same copies gives JSON that differs only in `source/extracted_at` (`_provenance` not compared) and stderr that differs only in the reworded line and the written byte count (+6). `git status hardware lab` is empty.

**Task 3 (`f062e11`).**
- `tools/CONTEXT.md`: the "kiutils Rule" became the "I/O-module Rule": load and save only through `kicad_io`; the raw layer for writes and board reads (through `pcb_raw.py`); typed views read-only and never the typed `PCB`; numbers as text; the splice save; version kept; the lock guard; the pin; the upgrade procedure from PLAN "Pin and upgrades". It lists one exception: `place_power.py` writes by text replacement outside `kicad_io`. The Critical Rule's probe exception now says `kicad_io` instead of kiutils. There is a new "KiCad File I/O / kicad-io/" entry, and the `kiutils_k9.py` row is gone. The `extract.py` row and the Dependencies paragraph were rewritten (venv, build command, kicad-tools through kicad_io, lab tools on the global python3). The harness entry says how to run the oracle.
- `tools/schematic-modify/CONTEXT.md`: the rule section was rewritten for `kicad_io`, with a history line on kiutils_k9. The `kiutils_k9.py` file entry is removed. Fixed: the `--root` line (write modes now work with a scratch copy outside the repo), `v8_project_setup` "renames via kiutils" (it renames through `kicad_io`), and `tidy_labels` "through the shim". The annotate.py/kiutils_k9 save sentence is now the `kio.save`/`save_project` lock-guard sentence.
- `tools/schematic-context/README.md` (10) and `tools/pcb-context/README.md` (24): every command now runs as `tools/.venv/bin/python tools/<folder>/<script>.py` from the repo root. The pcb-context ones used bare script names before, so `audit-specs/` paths now carry the `tools/pcb-context/` prefix. pcb-context Dependencies: venv, kicad-tools through `kicad_io`, shapely and matplotlib at their pins. The Python 3.7/kiutils lines are gone.
- `.context/HAZARDS.md`: the kiutils entry was replaced with "never load or save a KiCad file with anything but kicad_io", and the 6-significant-digit float-atom trap was added.
- `place_power.py`: the docstring and section comment say it writes by text replacement, outside `kicad_io` and its lock guard.
- Remaining `kiutils` mentions under tools/ and .context/ are history or comparisons (pcb_raw's kiutils-compatible defaults, test census kinds, generator comments, requirements' note on the global 3.7 install). None of them is a present-tense instruction.

**For the next session.**
- Use `tools/.venv/bin/python` for every KiCad tool. The harness itself (`regress.py`) is stdlib and runs on the global `python3`.
- Oracle runs need the preport venv (above). `scratchpad/p11/venv-old` works while the scratchpad lasts.
- Deferred line added: `place_power.py` writes `.kicad_pcb` outside `kicad_io`.

**Handoff checks.** `git diff 11af873 HEAD` on hardware/, lab/, .githooks and PLAN.md is empty. `git worktree list` shows only the user's Cursor worktrees: my `p11/wt-pre` is removed and pruned, and the harness/modtest worktrees removed themselves. The global `python3` is pyenv 3.7.3. No new documents; PLAN unchanged.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 12 | Phase 11: Remove kiutils; KiCad 9 reads; the parser rule | DONE | No — clean completion | d91321f | 4 tasks; final compare shows only E1 (and E2 in modtest); kiutils removed; harness 24/24 on the rebuilt venv |

#### Verification
- 4 commits, `e80dedf`..`d91321f`. `git diff 11af873 HEAD` on hardware/, lab/, .githooks and PLAN.md is empty. `kiutils_k9.py` is deleted. No kiutils import is left under tools/ (outside .venv). `tools/requirements.txt` mentions kiutils only in history comments. `tools/.venv` can't import kiutils, and `pip check` is clean. No extra worktree is left.
- Orchestrator re-run on the working tree with the rebuilt venv: `v8_debug_sheet --check` gives PHASE 11 CHECK PASSED, `tidy_fields --check` and `tidy_labels --check` exit 0, and the tree is clean afterwards.
- **The port is complete (Phases 4–11).**
- **Reference re-records:** `reference-k9.txt` now holds the board-model hash for the ported reader and the reworded `extract.py` line, each with a note citing why.
- **The preport oracle now needs its own venv.** It is built from `git show kicad10-preport:tools/requirements.txt`, and the recipe is in the `regress.py` docstring and the `tools/CONTEXT.md` harness entry. The saved copy in scratchpad/p11/venv-old is temporary.
- Deferred gained one line: `place_power.py` writes `.kicad_pcb` outside `kicad_io` and its lock guard. It is listed as an exception in the I/O-module Rule.

---

### Worker #13 — Phase 12: Schematic tools on KiCad 10

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 12 — Schematic tools on KiCad 10
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN in full ("kicad-cli 10 differences", "Migrating v8" ERC counts, "Scratch roots for the checks"). SESSION.md Worker #3 Notes (KiCad 10 conversion, exporter differences, ERC setup items) and Worker #10 Notes (schematic-context port, generator inputs via gen.sh). tools/CONTEXT.md I/O-module Rule.

Tasks assigned: Phase 12, all 4 tasks (see TASKS.md)

Notes: converted copies only (kicad-cli 10 sch upgrade per sheet on fresh scratch copies). KICAD_CLI on 10 for this phase's runs, never against a working-tree path. layout_check calibration changes need before/after evidence on 9 and 10. KiCad 9 behaviour must not regress: harness 24/24 on 9 at handoff.
Rules: hardware/ and lab/ unchanged; global python3 and .githooks unchanged.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p12/` (scripts in `p12/scripts/`: `leafdiff.py`, `svgboxes.py`, `rd10.sh`, `aifields.py`, `gen10.sh`, `stockcmp.py`, `mixembed.py`); harness run roots `scratchpad/p12k09` (KiCad 9) and `p12k10` (v8 converted, kicad-cli 10). kicad-cli 10 ran only on scratch copies; `KICAD_CLI` was set per command. Every KiCad 10 copy is a fresh `git archive` of v8 at `v8-schematic-freeze` with `kicad-cli sch upgrade` run on each of the five sheets (all 20250114 → 20260306).

**Task 1 (`9874709`). `extract.py` and the `pinfunction` suffix.**
- On v8, kicad-cli 10 writes all 471 named pinfunctions as `<name>_<pin>`. Unnamed pins have no pinfunction on 9 or on 10. 110 of the KiCad 9 names already end in `_<their own pin number>` (`Pin_1` on pin 1, and so on), so a plain strip would be wrong on 9 output.
- The fix: `_parse_nets` strips `_<that pin's number>` only when the netlist's `<design><tool>` says KiCad 10 or later (`_netlist_kicad_major`, `_pin_name`). KiCad 9 netlists are never touched.
- On a converted v8 with kicad-cli 10, `circuit-context.json` equals the KiCad 9 one leaf for leaf, apart from `_provenance` and `extracted_at`. None of the exporter differences reach it. Without the fix, 445 pin-name leaves differed (`'1'` → `'1_1'`). v7's KiCad 9 sheets through kicad-cli 10 give the same result. The only change in stderr is the netlist byte count (536,367 → 571,868).

**Task 2 (`3a53b35`). Re-validation on a KiCad 10 v8.**
- The harness gained `run --upgrade-v8`: after archiving, it runs `sch upgrade` on every v8 sheet with `--kicad-cli`, which must be 10 or later. One line was added to the harness entry in `tools/CONTEXT.md`.
- Runs: `regress.py run p12k10 --kicad-cli <10> --upgrade-v8` and `regress.py run p12k09`. In p12k10 every command exits 0. p12k09 matches 24/24 against `reference-k9.txt`, after the task 1 change.
- `compare p12k09 p12k10`:
  - IDENTICAL on 10: `layout_check`, `tidy_fields --check`, `tidy_labels --check` (TOTAL 0 on every sheet), and `v8_mcu/bus/power_sheet --check` (CHECK PASSED, PHASE 9/10).
  - `v8_debug_sheet --check` passes (LAYOUT CHECK PASSED, PHASE 11 CHECK PASSED). Its output and `v8_project_setup --verify` differ from 9 only in their ERC lines.
  - `extract --check-sheet-pins`: 42 pins, 0 offenders. Only the byte count differs.
  - The netlist is structurally equal with the suffix stripped: 296 components, 158 nets. What remains are the PLAN exporter items: net classes on 14 nets, sheet numbering, `Sheetname`, `datasheet`.
  - The converted sheets are byte-identical after the run, so the checks wrote nothing.
- ERC on 10 against the freeze counts: errors 0, pin_to_pin 81, lib_symbol_issues real 2 (J7 USB-C, U5 BQ24195RGET), all unchanged. New in 10: 5 `same_local_global_label` on root `+5V` and `+3.3V_MCU`, TCA `+3.3V_BUS`, LED `GND` and power `+5V_CORE`. Setup items, listed separately: lib_symbol_issues 330 and footprint_link_issues 281, broken down by library in `regress.py erc`.
- `extract.py`, `show.py` and `annotate.py` (`rd10.sh`), run on a 9 copy and a converted 10 copy:
  - Outputs and exit codes are identical for extract (plain, `--previous`, `--check-sheet-pins`, `-v`), show (plain, `--unannotated`, `--sheet led_controller`, and after annotation), and the 8 annotate commands from Phase 9 (update, multiple refs, new fields, root part, `--clear`, missing ref, partial miss, bad key). stderr differs only in the byte count.
  - Every `circuit-context.json` (before, `--previous`, after annotation) is equal apart from `_provenance` and `extracted_at`.
  - After annotation: the netlist is structurally equal (suffix stripped), ERC is as above, and the plotted strings are equal apart from the title-block "KiCad E.D.A." version and TCA's page "Id: 4/5" → "2/5" (sheet numbers follow page numbers on 10).
  - The 1,140 `ai_*` fields have the same value, hidden flag and position. On 10 each has exactly one hide flag, the property-level KiCad 10 form.
- **layout_check calibration: no change needed.** `svgboxes.py` compares the box of every plotted string in kicad-cli 9 and kicad-cli 10 SVGs of the same v8 sheets. 2,696 strings were matched. 1,992 have identical boxes (within 0.005 mm). The other 704 are all pin texts, which layout_check doesn't model: pin numbers, USB-C pin numbers such as `A1B12` and `B6`, and three `A`/`B`/`C` pin names. Each one is moved 0.102 mm along its pin (KiCad 10 moved pin text). Every field, label, sheet pin and text item plots in the same box on 10, so the geometry calibrated on 9 holds. `layout_check -v` on the 9 and 10 copies gives identical output, and the baseline is unchanged.
- The harness also ran v7's KiCad 9 board through kicad-cli 10. That belongs to Phase 13 and wasn't assessed here: board-model and DRC gain 79 setup `lib_footprint_issues`, and the reports are identical.

**Task 3 (not checked off: stopped on a finding). `STOCK_SYMBOLS` follows `KICAD_CLI`.**
- **tidy_fields: no change.** It reads only the pin flags (`pin_numbers`/`pin_names` hidden) from the stock libraries. `stockcmp.py` checked all 25 stock lib_ids embedded in v8: the pin flags are the same in 9.0.4 and 10.0.8. `tidy_fields --check` on 10 is identical (above).
- **schematic-gen generators: no change.** None of them reads `STOCK_SYMBOLS`. Their symbols come from project sheets, `resources/` and the JLC-MCP libraries under `~/Documents/KiCad/9.0/3rdparty`, and they always write format 20250114. Run with `KICAD_CLI` on 9 and on 10 (`gen10.sh`, Phase 9's scratch repo root, seeded uuids), each output sheet (poc, power, esp32) is byte-identical and the tool output is identical.
- **Generator outputs converted and run on 10.**
  - The conversion is netlist-neutral: kicad-cli 10's netlist of the unconverted and of the converted output are equal, and so are the non-library ERC items.
  - Against kicad-cli 9: poc's netlist is equal. power has 8 and esp32 25 extra single-node `unconnected-(…)` nets on 10, each with one pin and nothing else changed. This is kicad-cli 9 behaviour, not a tool difference: kicad-cli 9 leaves those nets out when a child sheet is exported as a standalone root. v8's own `power_management.kicad_sch` exported alone gives 0 of them on 9 and 5 on 10, while the v8 project gives 26 on both. extract.py drops `unconnected-*` nets in any case.
  - ERC poc: 0 on 9. On 10, setup items only (2 + 2).
  - ERC power: pin_not_connected 6, pin_not_driven 1, pin_to_pin 28, real library items 4 + 5. Same items at the same positions on 9 and 10. 9's one `lib_symbol_mismatch` (TH1 `Device:Thermistor_NTC`) becomes a setup item on 10, because 10 can't find `Device` to compare against. 10 adds setup items 51 + 46.
  - ERC esp32: 9's 26 `label_dangling` errors are reported on 10 as 26 `isolated_pin_label` warnings, the same labels at the same positions (KiCad 10 renamed and downgraded the check). pin_not_connected 37 and pin_to_pin 14 are the same items. The 2 `multiple_net_names` are the same pairs of names, with a different label copy as the marker. 10 adds setup items 14 + 14.
  - These are the generators' own open pins and labels, as recorded in Phase 9.
- **What KiCad 10's stock symbols change.** All 25 v8 stock symbols differ at least in format: property-level `hide`, `show_name`, `do_not_autoplace`, `in_pos_files`, `duplicate_pin_numbers_are_jumpers`, and `(power global)`. After those are folded back to the 9 form, none is identical. Content changes: Datasheet `~` → `""` on most symbols. `Device:Thermistor_NTC` has new `ki_fp_filters`. `Jumper:SolderJumper_*` have 2 body arcs instead of 4. 74AHCT1G125, TPD2E2U06DRL, CSD25402Q3A, AP2112K-3.3, Conn_02x*, C, R, Fuse, C_Polarized_Small_US and SW_SPDT have different pin or body records (CSD25402Q3A's first pin changes type and position). So a part placed with `KICAD_CLI` on 10 gets KiCad 10's symbol, as placing it in the KiCad 10 GUI would. A `v8_*.py --apply` replay run on 10 would no longer reproduce its historical output.
- **FINDING (the reason for the stop): with `KICAD_CLI` on 10, a stock-symbol embed into a KiCad 9 sheet produces a sheet KiCad 9 can't read.**
  - The embed path is `v8_mcu_sheet.stock_symbol`, used by the `--apply` modes of `v8_mcu/bus/power/debug_sheet.py`, then `modify.add_component`, `ensure_lib_symbol` and `kio.save`. It copies the KiCad 10 library symbol (`show_name`, `do_not_autoplace`, `in_pos_files`, property-level `hide`) into a file whose version token stays 20250114. `kicad_io`'s save checks only that token, so it doesn't refuse.
  - Experiment (`mixembed.py`, scratch `p12/mix/`): add `Device:D_Schottky` as D900 to v8's LED sheet (KiCad 9 copy) with `KICAD_CLI` on 9 (`s9`) and on 10 (`s10`). With 9, kicad-cli 9 reads 297 components and 160 nets; ERC is the freeze counts plus 2 dangling labels for the test nets; the LED sheet plots 158 strings.
  - With 10, kicad-cli 9 still exits 0 on the project, but **silently drops the LED sheet's contents**: 282 components, 155 nets, 5 `hier_label_mismatch` errors, and 33 plotted strings on the LED sheet. Exported on its own, the sheet gives "Failed to load schematic", exit 3.
  - On a converted (KiCad 10) v8 copy (`t9`, `t10`), the 9-stock and 10-stock embeds are equivalent: the netlist differs only in D900's random uuid, the plotted strings are equal, and ERC is the same. So the problem is only `KICAD_CLI` on 10 combined with a KiCad 9 target.
  - Today it bites only the `--apply`/write modes. Once Phase 14 migrates v8 to KiCad 10, v8 is safe. The other boards stay on KiCad 9.
  - The generators would hit the same mix if their `.kicad_sym` sources were ever KiCad 10 libraries (for example JLC-MCP re-downloaded under a KiCad 10 setup), since they always write 20250114.
  - Options, not acted on, since it's a design choice:
    - (a) `modify.ensure_lib_symbol` or `kio.save` refuses a lib symbol from a library newer than the target sheet. `kio.load_symbol_lib` knows the library's version: 20241209 is 9.0.4 stock, 20251024 is 10.0.8.
    - (b) Choose the stock folder from the target sheet's version rather than from `KICAD_CLI`.
    - (c) A HAZARDS line only.
  - I didn't fix it or add a hazard. Task 3 and the Handoff are left `[ ]`.

**For the next session.**
- `--upgrade-v8` on the harness is ready for Phase 14's gate runs.
- The KiCad 9 harness is 24/24 on the current tools (`p12k09`).
- Fix the finding above (or have it decided), then check off task 3. Its other evidence is complete above.

**Handoff checks.** `git diff aa470dd HEAD` on hardware/, lab/, .githooks and PLAN.md is empty. The working-tree `.kicad_prl` files are untouched (v8 Nov 4, v7 Apr 7). The global `python3` is pyenv 3.7.3. No worktree was created. No new documents, nothing Deferred, PLAN unchanged.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 13 | Phase 12: Schematic tools on KiCad 10 | BLOCKED | Yes — resolvable without replanning: it's a guard gap in this initiative's own I/O module, and the fix extends PLAN's existing "a KiCad 9 file can't leave as 10" save rule | dabb7b4 | Tasks 1–2 done; task 3's evidence is done, but it found that KiCad 10 stock symbols get embedded into KiCad 9 sheets |

#### Verification
- 3 commits, `9874709`..`dabb7b4`. Tasks 1–2 are `[x]`; task 3 and the Handoff are `[ ]`. `git diff aa470dd HEAD` on hardware/, lab/, .githooks and PLAN.md is empty. The tree is clean.
- **The finding is a real silent-loss path.** It happens when `KICAD_CLI` points at 10 and a `v8_*.py` write mode runs on a KiCad 9 sheet. `stock_symbol` then reads the KiCad 10 stock library, `add_component` embeds that symbol, and `kio.save` passes, because the sheet's version token is unchanged. kicad-cli 9 then drops the sheet's contents and exits 0.
  - Exposure today: write modes only, and only with `KICAD_CLI` set to 10. v8 stays on 9 until Phase 14, and the other boards stay on 9 permanently.
- **Decision (Orchestrator, within PLAN):** option (a). The I/O module refuses to save a lib symbol taken from a library whose format is newer than the target file's KiCad version. This is the same rule as the existing version-unchanged check, carried down to embedded content, so it fails loudly.
  - Option (b), picking the stock folder from the sheet's version, would change which symbols the tools pick, which is a behaviour change. It isn't needed once (a) refuses.
  - Option (c), a HAZARDS line only, leaves the silent loss in place.
  - A HAZARDS line is added alongside (a).

[ORCH] Adjusting and re-dispatching

---

### Worker #14 — Phase 12 (continued): stock-symbol version guard, then task 3

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 12 — Schematic tools on KiCad 10 (continued from Worker #13)
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: SESSION.md Worker #13 Notes and the Orchestrator Result/Verification under them. PLAN "One I/O module" (Save, Format check). tools/kicad-io/kicad_io.py, tools/kicad-regress/test_kicad_io.py, test_modify.py.

Tasks assigned: Phase 12 task 3 and the Handoff (tasks 1–2 are done).

Adjustment: before checking off task 3, close the finding with option (a): the I/O module refuses to embed or save a lib symbol from a library whose format is newer than the target file's KiCad version (9.0.4 stock = 20241209, 10.0.8 stock = 20251024). Committed test cases: KiCad 10 stock into a KiCad 9 sheet refuses, and the file is unchanged; KiCad 9 stock into 9, and 9 or 10 stock into a KiCad 10 sheet, pass. Record the rule in PLAN "One I/O module" (one sentence) and in the tools/CONTEXT.md I/O-module Rule. Add a HAZARDS line. Then re-run iotest, modtest, and the KiCad 9 harness (24/24), and check off task 3 from Worker #13's evidence.
Rules: hardware/ and lab/ unchanged; kicad-cli 10 only on scratch copies.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/`. These are `p12w14-io` (iotest) and `p12w14-mt` (modtest), each with a `.log`, plus `w14k09` (harness run, KiCad 9) and `p12/mix2` (the mixed-embed re-run). The scripts are `p12/scripts/mixembed.py` and the new `mixembed_bypass.py`. kicad-cli 10 ran only on scratch copies. `KICAD_CLI` was set per command and was unset (9.0.4) for the harness run.

**Guard (`a757e18`).** `kicad_io` now refuses a library symbol loaded from a file of a newer KiCad version than the target file.
- **How provenance travels.** At load, every library symbol in a Doc gets its node's class swapped to a slot-less `SExp` subclass whose class attribute `kio_source` = (kind, format version, KiCad major). For a library these are the top-level `symbol` items; for a schematic, the `lib_symbols` entries. `SExp` uses `__slots__`, so an instance attribute or weakref isn't possible. A class with no slots of its own has the same layout, so the swap is allowed, and `copy.deepcopy` rebuilds the copy with the same class. As a result the source survives `extract_lib_symbol`, `stock_symbol`'s `extends` flattening, `ensure_lib_symbol`'s deepcopy, and copies of copies. Serialization and the splice save are unaffected (kicad-tools has no type checks on `SExp`; iotest round trips are still byte-identical).
- **Where it's checked.** In both places:
  - At save. `_check_version` (run by `save` and, for every doc before any write, by `save_project`) calls `check_embed` on each library symbol in the tree. Nothing reaches disk past it, whatever the edit path. `v8_debug_sheet`'s REFRESH_LIBS, for example, replaces `lib_symbols` children directly and never calls `ensure_lib_symbol`.
  - At embed. `modify.ensure_lib_symbol` calls `kio.check_embed` first, so an `--apply` fails before it makes any other edit.
  - The comparison is by KiCad major. Project libraries in 20211014 (6) and 20231120 (8) format embed into 9 and 10 sheets. A node built in code with `node()` has no source and isn't checked (documented in the module and in tools/CONTEXT.md).
- **The message.** `<sheet>: library symbol "Device:D_Schottky" comes from a symbol library in format 20251024 (KiCad 10), newer than this schematic's format 20250114 (KiCad 9), which KiCad 9 can't read. Embed it from a KiCad 9 library (stock symbols: KICAD_CLI on KiCad 9)`. The exception is `KiCadIOFormatError`.
- **Tests: iotest stage 4b.** 17 new checks; IOTEST PASSED 124/124, against 107 before.
  - KiCad 10 stock into a KiCad 9 sheet: `check_embed`, `save` and `save_project` each refuse; the file is byte-unchanged; the message names the symbol, 20251024 and 20250114.
  - That same tree, written past the guard with `render`, gives a sheet kicad-cli 9 reads as 224 components instead of 296. This is the loss the guard prevents.
  - Each of these saves passes, and kicad-cli of the sheet's version reads the result with the input's counts (296/158):
    - KiCad 9 stock into a KiCad 9 sheet and into a KiCad 10 sheet.
    - KiCad 10 stock into a KiCad 10 sheet.
    - The 20211014 project symbol `INA219AIDCNR` into both.
  - A copy of a copy keeps its source, and a `node()` symbol has none.
- **Mixed-embed re-run through the real write path.** `mixembed.py` adds D900 `Device:D_Schottky` to the LED sheet, going through `stock_symbol`, `add_component` and `save_all`. Fresh `git archive` copies of v8 at `v8-schematic-freeze` were used, two of them converted by `sch upgrade`:
  - KiCad 9 sheet, `KICAD_CLI` on 9: saved. kicad-cli 9 reads 297 components and 160 nets, as Worker #13's `s9`.
  - KiCad 9 sheet, `KICAD_CLI` on 10: **refused** at `ensure_lib_symbol`, exit 1, all five sheets byte-unchanged. This is Worker #13's `s10` case.
  - KiCad 9 sheet, `KICAD_CLI` on 10, `mixembed_bypass.py`: the bypass appends the stock symbol to `lib_symbols` directly. **Refused** at `save_project`, exit 1, sheets byte-unchanged.
  - KiCad 10 sheet, `KICAD_CLI` on 9 and on 10: both saved. kicad-cli 10's netlists of the two are the same size.
- **Re-runs.**
  - `regress.py iotest`: 124/124.
  - `regress.py modtest --python scratchpad/p11/venv-old/bin/python`: MODTEST PASSED 105/105, the same count as Phase 11. The guard changes nothing on the 9-stock-into-9 and 9-stock-into-10 paths modtest exercises.
  - Harness `run w14k09` + `hash --against reference-k9.txt`: 24 of 24.
- **Recorded in:** the PLAN "One I/O module" Save bullet (one clause), the tools/CONTEXT.md I/O-module Rule Save bullet, and a `.context/HAZARDS.md` line.

**Task 3 checked off.** The evidence is Worker #13's Notes task 3: tidy_fields and the generators are unchanged, the generator outputs were converted and run through ERC on 10, and KiCad 10's stock-symbol differences are explained. Its finding is closed by `a757e18`.

**For the next session.** Phase 13 (board tools) is untouched. `scratchpad/p11/venv-old` is still the preport venv that modtest needs. The guard doesn't cover footprints in boards, because no board write path embeds library footprints yet; if Phase 13's write path does, the same check applies.

**Handoff checks.** `git diff dabb7b4 HEAD` on hardware/, lab/ and .githooks is empty. The working-tree `.kicad_prl` files are untouched (v8 Nov 4, v7 Apr 7). The global `python3` is 3.7.3. No worktree was left: modtest's `wt-pre` removed itself, and `git worktree list` shows only the user's Cursor worktrees. No new documents and nothing Deferred. PLAN changed only by the one Save clause.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 14 | Phase 12 (cont.): stock-symbol guard, task 3 | DONE | No — clean completion | 04a9611 | Guard `a757e18`; iotest 124/124; modtest 105/105; KiCad 9 harness 24/24; mixed embed now refused |

#### Verification
- 2 commits, `a757e18` and `04a9611`. Phase 12 is all `[x]`. `git diff bf0a5ca HEAD` on hardware/, lab/ and .githooks is empty. The PLAN edit is one clause in the "One I/O module" Save bullet, and it records the rule this dispatch asked for. No extra worktree is left.
- Orchestrator re-ran `regress.py iotest` into scratchpad/orch12: 124 passed, 0 failed. The tree is clean afterwards.
- **How the guard works.** Library-symbol nodes are re-classed at load to an `SExp` subclass that carries their source version. The source survives deepcopy. The guard checks at embed time (`ensure_lib_symbol`) and again at save, so nothing gets past it. Serialization is unchanged. One known gap: a symbol built in code with `node()` has no source and isn't checked. This is documented.
- Carry forward to Phase 13:
  - The guard doesn't cover footprints. If a board write path copies library footprints, apply the same rule there.
  - Worker #11 found that a zone with no net reads "unknown" on KiCad 10, where KiCad 9 gives `''`. Decide what it should read.
  - `routing_extract` shows net names instead of net numbers on 10.

---

### Worker #15 — Phase 13: Board tools and the write path on KiCad 10

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 13 — Board tools and the write path on KiCad 10
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN in full ("Board write path", "Which layer", "One I/O module"). SESSION.md Worker #3 Notes (KiCad 10 board format: nets by name, NPTH *.Cu, keepout zone, DRC parity item), Worker #11 Notes + Orchestrator Verification (pcb_raw views, KiCad 10 smoke test, absent-net "unknown"), Worker #14 Verification (footprint guard). docs/initiatives/v8-debug-board/PLAN.md OQ-3 and "AI layout tooling" (grep), and the v8 SESSION "Replan — board write path" section (grep) for the KiCad 9 probe method.

Tasks assigned: Phase 13, all 3 tasks (see TASKS.md)

Notes: decide the absent-net zone value on 10 with evidence (match KiCad 9's '' or keep "unknown") and record why. pcbnew probe runs KiCad 10's bundled Python only, on scratch copies. If a write path copies library footprints, state whether the version guard must cover it.
Rules: hardware/ and lab/ unchanged; kicad-cli 10 and KiCad 10's Python only on scratch copies; harness 24/24 on KiCad 9 at handoff.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p13/`. `v7k9`, `v7k10`: `c2acffc` archives, the second converted with kicad-cli 10 `pcb upgrade`. `base10`: a read-only converted master, copied to `pn-*` (pcbnew) and `kt-*` (kicad_io) per edit (`kt-flip3`/`kt-all3` are the final kicad_io flip runs; `kt-flip2`/`kt-all2` had the double-flip bug). Outputs: `out9`/`out10` (before the zone fix), `outb9`/`outb10` (after it), `drc/`, `bm/`, `pp10/`. Scripts: `scripts/pn_edit.py`, `kt_edit.py`, `order.py`, `c9cmp.py`, `drcdiff.py`. KiCad 9 harness run: `scratchpad/p13k09`. kicad-cli 10 and KiCad 10's Python ran only on those copies. No worktree made.

**Task 1 (`ce8c7a1`).** `board_model.py`, `net_report.py`, `plane_report.py` and probe-points `pads` run on `v7k9` with kicad-cli 9 and on `v7k10` with kicad-cli 10; all exit 0.
- **board-model.json, KiCad 10 against 9** (leaf compare, `_provenance` excluded): `meta/kicad_format_version` 20241229 → 20260206; `zones[4]/net` `''` → `"unknown"` (fixed below); and the `drc` block: `kicad_version` 10.0.8, +79 setup `lib_footprint_issues` (79 footprints in libraries KiCad 10 has no global table for), and the same 20 violations (16 clearance, 2 hole_clearance, 2 padstack). They are equal as sets once each violation's two items are sorted; kicad-cli 10 lists some pairs in the other order. Everything else is identical: footprints, pad polygons (the NPTH pad's `*.Cu` expands to the same layers as 9's `F&B.Cu`), tracks, zones, nets, topology. The R2 field-parity item doesn't show: `board_model.py` runs DRC without `--schematic-parity`.
- **The keepout's net: decided `''` on KiCad 10.** KiCad 9 writes the antenna keepout as `(net 0) (net_name "")`; KiCad 10 writes no net token, because it omits net 0. Both mean "no net". `"unknown"` was kiutils' default for a missing token, and `plane_report` printed it: the Markdown zone tables said `unknown` where 9 says `keepout` (4 rows), and the JSON `net` was `"unknown"` where 9 has `null`. `pcb_raw.Zone` now reads an absent net as `''` on a board with no net table (KiCad 10). Boards with a net table keep "unknown", so KiCad 9 output can't change (`out9` vs `outb9`: identical model and reports). After the fix the KiCad 10 model differs from 9 only in the format version and the DRC block, and the net and plane reports are identical apart from the source path and hash.
- **probe-points.** `pads U5 C21 C9` is byte-identical on 9 and 10. `render` ran with kicad-cli 10 and Chrome (`pp10/v7-k10-probe-points.png`, 1600×3798, render 6384×4792, board bbox x 875–5507, y 1385–3406 px). I looked at it: A/B are on the SDA/SCL test pads, C on C9's upper pad, D/E on U5 pins 6/5, F and the two X on the ends of C21/C20. Every marker is on its pad.
- Not changed: `routing_extract.py` writes net names as `net_number` on 10 (Worker #11). That's the format: KiCad 10 has no net numbers. `routing_audit.py` reads `routing_extract`'s output but not `net_number` (grep), and `verify-routing.py` builds its own net map from the board.

**Task 2 (`1b5efa7`).** Results, numbers and the recommendation are in PLAN "Board write path"; OQ-3 is struck. In short:
- KiCad 10's interpreter: `/Applications/KiCad10/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3` → 3.9.13, `pcbnew` 10.0.8 from its own site-packages, with `-I`. Every run prints a harmless `wxApp` assert on stderr.
- pcbnew load + save of the converted board is **not** byte-identical: the same items, but every track is regrouped by net in a different order, +10,444 lines. It is a one-time reorder: a second pcbnew round trip, and `kicad-cli pcb upgrade --force` of pcbnew's output, are byte-identical. The KiCad 9 probe's "byte-identical" held because that board was last saved by KiCad 9 itself. Edit diffs are measured against the fixed point.
- pcbnew 10 also saved a KiCad 9 board (`pn-k9`) as 20260206 without warning. The writer must check the version.
- kicad_io: round trip byte-identical. Raw edits give C9 the same pads, graphics, layers and position as pcbnew, and the same DRC. Field and `fp_text` angles after a flip differ from KiCad's. I wrote the flip from first principles (angle → −angle) and didn't fit it to pcbnew's output, so that difference is the finding.
- DRC changes from moving C9: 3 mm right puts it on U4's pins 17–21, and its old tracks and via stay behind (shorts, mask bridges, a courtyard overlap, dangling tracks, unconnected pads). The breakdown per edit is in PLAN. One U6 clearance item swaps between pad 2 and pad 4 with track order (both are 0.15 mm from the via), on every pcbnew save including the round trip. It isn't a change.
- Footprints: neither path copied a library footprint. PLAN says what the guard must do if code ever inserts `.kicad_mod` text through kicad_io; a pcbnew writer is covered by a KiCad-10-only board check.

**For v8's replan (not done here):** v8 PLAN OQ-3 and "AI layout tooling" still name KiCad 9.0.4's Python 3.9 and its byte-identical round trip. They need the KiCad 10 path and the three writer guards from this PLAN. Also, a board-model before/after check keyed by segment ids fails after pcbnew's first save, because ids are positional.

**Handoff checks.** KiCad 9 harness `regress.py run …/p13k09 --against reference-k9.txt`: 24 of 24. `git diff 367eadf HEAD` on hardware/, lab/ and .githooks is empty; the global python3 wasn't touched. No worktree created. Nothing Deferred. No new documents.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 15 | Phase 13: Board tools and the write path on KiCad 10 | DONE | No — clean completion | cfbfc3d | 3 tasks; board tools on 10 match 9 apart from format items; keepout net reads `''`; OQ-3 answered: pcbnew (KiCad 10 Python) for v8 Phase 13 |

#### Verification
- 3 commits, `ce8c7a1`..`cfbfc3d`. Phase 13 is all `[x]`. `git diff 367eadf HEAD` on hardware/, lab/ and .githooks is empty. OQ-3 is struck in PLAN, and PLAN has no date-stamped headings.
- The Orchestrator looked at the KiCad 10 probe-points render (`scratchpad/p13/pp10/v7-k10-probe-points.png`). Markers A–F and both X sit on their pads: TPIO43/44, C9.1, U5 pins 5 and 6, and C21/C20.
- The `pcb_raw` keepout change applies only to boards with no net table (KiCad 10). The Worker showed KiCad 9 output unchanged and the harness at 24/24.
- **For the v8 replan (Phase 17 resume note):**
  - The v8 PLAN OQ-3 and "AI layout tooling" still cite KiCad 9's Python and a byte-identical round trip. On 10, pcbnew's first save of a kicad-cli-converted board regroups the tracks (+10k lines), and from then on it's stable.
  - pcbnew 10 silently saves a KiCad 9 board as 10, so `pcb_write.py` needs the three guards in PLAN "Board write path".
- The footprint guard isn't needed for either probed path. PLAN records what's needed if `.kicad_mod` text is ever inserted through kicad_io.
- Next: Phase 14 task 1 (the library list, before G3), then the loop pauses for G3.

---

### Worker #16 — Phase 14 (pre-G3): v8's library resolution on KiCad 10

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 14 — Migrate v8 to KiCad 10 (task 1 only; stop at G3)
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN "Migrating v8", OQ-4. SESSION.md Worker #3 Notes (setup lib items on 10) and Worker #13 Notes (ERC on 10 with setup items). hardware/pcb-main-v8/kicad/sym-lib-table and fp-lib-table (read only). ~/Library/Preferences/kicad/9.0/sym-lib-table and fp-lib-table (read only).

Tasks assigned: Phase 14 task 1. Stop before G3 and return PARTIAL; that stop is planned.

Notes: read-only on hardware/ and on both KiCad prefs folders. Trial either option only on scratch copies (a scratch project table; a scratch KICAD10 config dir via KICAD_CONFIG_HOME if that works for kicad-cli 10), never the real ~/Library/Preferences/kicad/10.0. For each option, show ERC on converted scratch v8 drops the setup items to 0. Give a recommendation.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p14/`. `base` is a `git archive v8-schematic-freeze` of `hardware/pcb-main-v8/kicad`, `hardware/pcb-main/resources` and `hardware/libraries`. (The five sheets are the same at HEAD.) `conv` is `base` with `kicad-cli sch upgrade` run on each sheet (all 20250114 → 20260306). Each trial is a copy of `conv` (`convA1`, `convA2`, `convB1`, `convB2`, `convB9`) with its own scratch config home (`cfg0`, `cfgA1`, `cfgA2`, `cfgB1`, `cfgB2`). Scripts are in `scripts/`: `libuse.py` (library use per sheet), `mktables.py` (the project-table entries), `erc.sh`, `ercitems.py` (compares the non-library ERC items) and `tools.sh` (the schematic checks). Every kicad-cli 10 run in this session had `KICAD_CONFIG_HOME` pointed at a scratch folder.

**How kicad-cli 10 finds its config (tested, not assumed).** kicad-cli 10 honours `KICAD_CONFIG_HOME`. With it set, it reads and writes `$KICAD_CONFIG_HOME/10.0/`: `kicad-cli version` alone created `kicad.json`, `kicad_common.json` and `colors/` there. Without it, a kicad-cli 10 run rewrites the real `~/Library/Preferences/kicad/10.0/kicad_common.json`. Its mtime was 22:39 today, before this session started, presumably from an earlier run. The listings (stat and shasum, `p14/prefs{9.0,10.0}_{before,after}.txt`) are identical before and after this session for both `~/Library/Preferences/kicad/9.0` and `/10.0`. Nothing under `~/Documents/KiCad/10.0` is newer than the before-listing either. The real 10.0 folder still has no lib tables. Phase 14 can use this: the gate runs can set `KICAD_CONFIG_HOME` to a scratch folder seeded with the agreed tables. Then the results don't depend on the machine's prefs, and the real ones are never written.

**Baseline, empty scratch config (`cfg0`, the state of the machine today).** ERC on `conv`: 0 errors, 81 pin_to_pin, 2 real lib_symbol_issues, 5 same_local_global_label, and the setup items 330 lib_symbol_issues and 281 footprint_link_issues. These are the Worker #3/#13 counts.

**What v8 uses that resolves only through KiCad 9's global tables** (`libuse.py`, the 334 placed symbols across the five sheets). The per-library counts add up to the setup items exactly: symbols 321 + 9 = 330, footprints 280 + 1 = 281.

- **Own libraries (not KiCad's), 9 symbols and 1 footprint.** KiCad 10 does not provide these.

| Library | Kind | Parts | In 9's global table as |
|---|---|---|---|
| `JLC-MCP-Capacitors` | symbol | 2 (C42, C43) | `${KICAD9_3RD_PARTY}/jlc_mcp/symbols/…` (`~/Documents/KiCad/9.0/3rdparty`, outside the repo) |
| `JLC-MCP-ICs` | symbol | 2 (SW2, SW3) | same |
| `JLC-MCP-Diodes` | symbol | 1 (U9) | same |
| `JLC-MCP-Inductors` | symbol | 1 (D5) | same |
| `JLC-MCP-MCUs` | symbol | 1 (U3) | same |
| `JLC-MCP-Power` | symbol | 1 (U8) | same |
| `motion-play-symbols` | symbol | 1 (U4 TCA9548APWR) | absolute path to the working tree, `…/motion-play/hardware/libraries/motion-play-symbols.kicad_sym` |
| `motion-play-footprints` | footprint | 1 (U4 `SOP65P640X120-24N`) | absolute path, `…/hardware/libraries/motion-play-footprints.pretty` |

- **KiCad stock libraries, 321 symbols and 280 footprints.** KiCad 10.0.8 ships all of these, and its default global table lists them.
  - Symbols: Connector 119, Device 108, power 38, Connector_Generic 29, Jumper 18, Power_Protection 3, Switch 2, Transistor_FET 2, 74xGxx 1, Regulator_Linear 1.
  - Footprints: TestPoint 119, Resistor_SMD 53, Capacitor_SMD 43, Connector_PinHeader_2.54mm 23, Jumper 18, LED_SMD 7, Connector_JST 5, Package_TO_SOT_SMD 5, Fuse 3, Package_SON 2, Connector_AMASS 1, Inductor_SMD 1.
- **Already resolved through v8's project tables, no change needed:** symbols `TPS61088RHLR` and `INA219AIDCNR`. Footprints `JLC-MCP` (10 parts), `motion-play-v8` (J7), `BQ24195RGET`, `FXL0630-2R2-M`, `INA219AIDCNR` and `TPS61088RHLR`.
- **The 2 real lib_symbol_issues** are the symbol libraries `BQ24195RGET` (U5) and `USB-C_SMD-TYPE-C-31-M-12` (J7). They are in no table, on 9 or on 10. No option changes them.

**New finding: 19 `lib_symbol_mismatch` warnings once the stock libraries resolve on 10.** In every trial that points the stock names at KiCad 10's stock libraries, ERC reports 19 new `lib_symbol_mismatch` warnings: TH1 `Device:Thermistor_NTC`, and 18 jumpers. Those are JP3, 4, 21–26 and 33 (`SolderJumper_2_Open`), JP40–43 (`SolderJumper_2_Bridged`) and JP5, 31, 32, 34, 35 (`SolderJumper_3_Bridged12`). They are the embedded symbols differing from KiCad 10's stock copies. Worker #13 found the same library changes: Thermistor_NTC has new `ki_fp_filters`, and the SolderJumpers have 2 body arcs instead of 4. They are not a design change. Control trial `B9`: the same project table pointed at KiCad 9.0.4's stock folders (`/Applications/KiCad/KiCad.app/Contents/SharedSupport/{symbols,footprints}`) gives 0 mismatches. On 9 these 19 were hidden because 9's stock matched; with no table on 10 they were hidden because nothing resolved. **So the PLAN gate's warning list (81 pin_to_pin, 2 lib_symbol_issues, 5 same_local_global_label) needs 19 lib_symbol_mismatch added at G3, whichever option is chosen.** The other way to clear them is "Update symbols from library" in KiCad 10. That changes the design's embedded symbols, so it isn't part of the migration. B9 is a control only: pointing at 9.0.4's install would break when 9 is uninstalled (OQ-6).

**The two options, each trialled on a converted scratch v8.** For each trial:

| Trial | Config (scratch) | Project tables | errors | pin_to_pin | lib_symbol_issues (real) | same_local_global_label | lib_symbol_mismatch | setup sym / fp |
|---|---|---|---|---|---|---|---|---|
| baseline `cfg0` | none | as committed | 0 | 81 | 2 | 5 | 0 | 330 / 281 |
| (a) `A1`: 9's two tables copied verbatim | 9's tables | as committed | 0 | 81 | 2 | 5 | 19 | **8** / 0 |
| (a) `A2`: as A1, plus the path `KICAD9_3RD_PARTY` set in `kicad_common.json` | 9's tables + path | as committed | 0 | 81 | 2 | 5 | 19 | 0 / 0 |
| (b) `B1`: own libraries in the project tables | KiCad 10's default tables (`SharedSupport/template/{sym,fp}-lib-table`) | +7 sym, +1 fp entries; 6 JLC-MCP files copied | 0 | 81 | 2 | 5 | 19 | 0 / 0 |
| (b) `B2`: own and stock libraries in the project tables | none | +17 sym, +13 fp entries; 6 JLC-MCP files copied | 0 | 81 | 2 | 5 | 19 | 0 / 0 |
| control `B9`: as B2 with stock pointed at 9.0.4's install | none | as B2 | 0 | 81 | 2 | 5 | 0 | 0 / 0 |

- **The non-library items are the same items.** `ercitems.py` compared them (type, sheet, description, item uuids and positions; 88 items including the 2 real library issues). A1env, A2, B2, B9 and two reruns of B1 are identical to the baseline. The first B1 run named the other one of J7's two stacked shell pins "0" (same position, 39.37/72.39) in one Power-sheet pin_to_pin. Reruns of B1 and of `cfg0` named the usual one, so kicad-cli picks between duplicate pins arbitrarily; it isn't caused by the table.
- **Netlist** (kicad-cli 10, `regress.py netlist`). `cfg0` against A2 and against B1: structurally equal. Only the `libraries` section changes, so `extract --check-sheet-pins` reports a different byte count.
- **The schematic checks** (`tools.sh`, `KICAD_CLI` on 10, `--root` on the scratch copy): `tidy_fields`, `tidy_labels`, `v8_power/mcu/bus/debug_sheet --check`, `v8_project_setup --verify --no-v7-compare`, `layout_check` and `extract --check-sheet-pins`. Every one exits 0 for `cfg0`, A2, B1 and B2. A2 and B1 match `cfg0` except in the ERC lines (the setup items are gone and the 19 mismatches appear) and in the netlist byte count. B2 matches B1 except for `tidy_fields`. Its `_lib_table` (`tidy_fields.py:90`) reads v8's project table literally, so `${KICAD10_SYMBOL_DIR}/…` doesn't resolve. It then reports "no reference or library copy" for 7 stock symbols instead of reading `STOCK_SYMBOLS`. `--check` still passes, but the tool has lost its source for those symbols. B1 adds JLC-MCP and `motion-play-symbols` to the table `tidy_fields` reads, and its output is unchanged.

**(a) KiCad 10 global tables, set up by the user.**
- Machine: `~/Library/Preferences/kicad/10.0/sym-lib-table` and `fp-lib-table`, plus one more step for JLC-MCP.
  - By import: KiCad 10's first-run "import settings from 9.0" copies 9's tables. The import itself is a GUI step and wasn't run; A1 is the tables copied by hand.
  - kicad-cli 10 resolves `${KICAD9_SYMBOL_DIR}`/`${KICAD9_FOOTPRINT_DIR}` to its own stock folders, which is where the 19 mismatches in A1 come from. It resolves `${KICAD9_3RD_PARTY}` to `~/Documents/KiCad/10.0/3rdparty`, which is empty: "library 'JLC-MCP-ICs' was not found at '/Users/marcocleirigh/Documents/KiCad/10.0/3rdparty//jlc_mcp/…'". So an import alone leaves 8 symbols unresolved (A1).
  - The fix is one of three: a `KICAD9_3RD_PARTY` path in Preferences → Configure Paths, which is stored in `kicad_common.json` `environment.vars` (A2 tested this, as did setting it in the process environment); absolute paths in the six entries; or copying or linking `jlc_mcp/` into `~/Documents/KiCad/10.0/3rdparty`.
  - By hand: start from KiCad 10's default tables and add the 8 own entries with absolute paths. That ends up as A2.
- Repo: no change.
- Other boards: none. They stay on 9 and 9 reads only `…/9.0/`. v8's project tables are unchanged.
- Costs:
  - v8 depends on machine state again: six libraries outside the repo, and absolute working-tree paths.
  - Each new machine or KiCad version repeats the setup.
  - The gate's ERC depends on the user's prefs, unless the gate seeds a scratch `KICAD_CONFIG_HOME`.
  - JLC-MCP parts added later through the MCP tool reach v8 with no copy step. That's a plus, but the libraries can drift under it.

**(b) The own libraries in v8's project tables (B1), with stock from KiCad 10's own default global table.**
- Repo, all under `hardware/pcb-main-v8/kicad/`:
  - `sym-lib-table` gains 7 entries: `motion-play-symbols` → `${KIPRJMOD}/../../libraries/motion-play-symbols.kicad_sym`, and the six `JLC-MCP-*` → `${KIPRJMOD}/libraries/symbols/JLC-MCP-*.kicad_sym`.
  - `fp-lib-table` gains 1: `motion-play-footprints` → `${KIPRJMOD}/../../libraries/motion-play-footprints.pretty`.
  - The six JLC-MCP `.kicad_sym` files (about 45 KB, KiCad 9 format 20241209, 3–6 symbols each) are copied from `~/Documents/KiCad/9.0/3rdparty/jlc_mcp/symbols/` into `libraries/symbols/`, beside the `JLC-MCP-Misc.kicad_sym` already there. kicad_io's FORMATS already accepts 20241209.
- Machine: KiCad 10's default global tables, for the stock libraries only. KiCad ships them as `SharedSupport/template/{sym,fp}-lib-table`, and KiCad 10 offers "copy default global table" the first time the GUI opens the symbol table. kicad-cli needs them in `~/Library/Preferences/kicad/10.0`, or in a seeded `KICAD_CONFIG_HOME`.
- Other boards: none. Only v8's tables and its own `libraries/` change. `hardware/libraries/` is referenced, not edited. v7 and the others stay on 9 with 9's tables.
- Costs:
  - The six files are a snapshot. A new JLC part for v8 has to be copied into the project, as `JLC-MCP-Misc` was.
  - The repo change goes beyond the format conversion, so the gate's "only those files change" check has to allow these files.
- Variant B2 (stock entries in the project table too): no global table needed at all. But it needs `tidy_fields._lib_table` to expand `${KICADn_SYMBOL_DIR}` to `STOCK_SYMBOLS`, and it puts 23 stock entries in v8's tables. Not recommended.

**Recommendation: (b), as B1.**
- v8 then resolves everything that isn't KiCad's from the repo, with project-relative paths and no environment variables.
- It no longer depends on `~/Documents/KiCad/9.0/3rdparty`, which an uninstall of 9 (OQ-6) could remove, or on an absolute working-tree path.
- The only machine step is KiCad 10's own default table.
- No tool changes. The checks are unchanged apart from the expected ERC lines.
- In both options, G3 also has to accept the 19 `lib_symbol_mismatch` into the gate's warning list.

**For the next session.**
- G3 is the user's: approve the migration, OQ-4 and the library table. Add "accept 19 lib_symbol_mismatch" to the same gate. PLAN is unchanged, and its Open Questions weren't touched.
- If (b): Phase 14 task 3 copies the six JLC-MCP files and adds the 8 entries by `mktables.py own`'s text (the descriptions can be adjusted). The machine needs KiCad 10's default global tables before the gate's kicad-cli runs. Alternatively, the gate seeds a scratch `KICAD_CONFIG_HOME` with them.
- If (a): the user sets up `~/Library/Preferences/kicad/10.0` and includes the JLC-MCP path, or ERC will show 8 setup items.

**Handoff checks.** `git status` was clean before the commits. The working-tree `.kicad_prl` of v8 is untouched (Nov 4). Nothing under hardware/ or lab/ changed. Both KiCad prefs folders match their before-listings. The global python3 and .githooks weren't touched. No PLAN edits, no new documents, nothing Deferred.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 16 | Phase 14 (pre-G3): v8 library resolution | PARTIAL | Yes — resolvable without replanning: the stop is the planned G3 user gate | 345fcbb | Task 1 done; recommends option (b) project tables; found 19 `lib_symbol_mismatch` from KiCad 10's changed stock symbols |

#### Verification
- 1 commit (`345fcbb`). Only SESSION.md and TASKS.md changed. The tree is clean.
- **Machine-side observation (Orchestrator):** both `~/Library/Preferences/kicad/9.0/kicad_common.json` (22:40) and `10.0/kicad_common.json` (22:39) have mtimes of 2026-11-11, each at its earlier byte size (2398 and 2691). At session start, 9.0's was Nov 7. The likeliest cause is a kicad-cli run without `KICAD_CONFIG_HOME` rewriting the common settings on exit; Worker #16 showed this for kicad-cli 10. Same size suggests the same content, but there's no before-copy to prove it. The user is told. For Phase 14 onward, every kicad-cli run uses a scratch `KICAD_CONFIG_HOME`, seeded with the agreed tables.
- G3 goes to the user with four items: the migration, OQ-4, the library table, and accepting the 19 `lib_symbol_mismatch` warnings into the gate's warning list.

### G3 — user decision (2026-11-11)

- **Migrate v8:** yes.
- **OQ-4:** a new tag `v8-schematic-freeze-k10` on the migration commit becomes the reference for v8 work. `v8-schematic-freeze` stays as the KiCad 9 record, with the alias `v8-schematic-freeze-k9` on the same commit.
- **Library tables:** option (b), project tables.
  - Copy the six JLC-MCP `.kicad_sym` files into `hardware/pcb-main-v8/kicad/libraries/symbols/`, and add project-relative entries to v8's `sym-lib-table` (7) and `fp-lib-table` (1).
  - The stock libraries come from KiCad 10's default global table.
- **Gate warnings:** accept the 19 `lib_symbol_mismatch` (TH1 and 18 solder jumpers, from KiCad 10's changed stock symbols) into the gate's warning list. The embedded symbols stay as frozen.
- **For the gate runs:** kicad-cli uses a scratch `KICAD_CONFIG_HOME`, seeded with KiCad 10's default global tables, so no machine prefs are touched.
- **The user's step, before any GUI use of v8 on 10 (Phase 15):** accept KiCad 10's default global library table on first launch.

---

### Worker #17 — Phase 14: Migrate v8 to KiCad 10

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 14 — Migrate v8 to KiCad 10 (G3 onward)
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN "Migrating v8", OQ-4. SESSION.md Worker #16 Notes and the "G3 — user decision" entry. Worker #13 Notes (ERC on 10). tools/CONTEXT.md I/O-module Rule. lab/ STATE rules for check_state.py --fresh (read only).

Tasks assigned: Phase 14 tasks 2–5 (G3 record, convert, gate, Handoff).

Notes: record the G3 decisions in PLAN (strike OQ-4; library-table and 19-warning decisions in "Migrating v8"). Every kicad-cli run uses a scratch KICAD_CONFIG_HOME seeded with KiCad 10's default global tables; never the real prefs. "Only those files change" includes the new libraries/symbols/ folder and the two lib tables. Tags annotated, not pushed. If any gate item fails, stop and report; do not commit the migration.
Rules: nothing under hardware/pcb-main/, other boards or lab/ changes.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p14w/`. `cfg/` is the scratch `KICAD_CONFIG_HOME`: `cfg/10.0/{sym,fp}-lib-table` are KiCad 10's default tables, copied from `KiCad10.app/Contents/SharedSupport/template/`. Every kicad-cli 9 and 10 run in this session used it, including the runs the tools make (they inherit the environment: the only `env=` in the KiCad tools is `regress.py`/`test_modify.py`, built from `os.environ`). kicad-cli 9 wrote its own `cfg/9.0/` with no tables. `ref/` is a `git archive v8-schematic-freeze` of v8, `pcb-main/resources` and `hardware/libraries`. Outputs are in `out/` and `tools_out/`; `scripts/tools.sh` is Worker #16's, pointed at a root sheet path. The real `~/Library/Preferences/kicad/9.0` and `/10.0` match their before-listing (`out/prefs_before.txt`, shasum of every file).

**Task 2 (`6bd9bc8`). G3 recorded in PLAN.** OQ-4 struck with the answer. "Migrating v8" gains the library-table decision (option b, the B1 entries) and the gate's warning list (0 errors; 81 pin_to_pin, 2 lib_symbol_issues, 5 same_local_global_label, 19 lib_symbol_mismatch; 0 setup items), with the 19 named and the embedded symbols left as frozen. G3 marked done under User gates. Three Rejected Approaches lines: option (a), variant B2, and updating the 19 symbols from the library.

**Task 3. Conversion.**
- Before: `pgrep -i kicad` found nothing. No `~*.lck` in v8's folder. The only lock files in `hardware/` are the old stale ones (v7 `~motion-play-v3.kicad_sch.lck`, Sep 2025; power-supply sch and pcb, Oct 2025).
- `v8-schematic-freeze-k9`: annotated, on `0d6255b` (the `v8-schematic-freeze` commit).
- kicad-cli 10.0.8 `sch upgrade` on each of the five sheets (20250114 → 20260306); a second run on each printed "Schematic file was not updated". `pcb upgrade` on the board (20241229 → 20260206). The `.kicad_pro` and `.kicad_dru` weren't touched (the upgrade commands don't write them).
- **`.kicad_prl`: `pcb upgrade` rewrote v8's `motion-play-main-v8.kicad_prl`** (2,501 → 2,666 bytes, Nov 4 → 23:32 today). It's gitignored. The original is saved at `p14w/out/prl.before`.
- Library tables: the six JLC-MCP `.kicad_sym` files copied from `~/Documents/KiCad/9.0/3rdparty/jlc_mcp/symbols/` (read only) into `libraries/symbols/`; the 7 + 1 entries added by Worker #16's `mktables.py own`. Both tables and all seven library files are byte-identical to Worker #16's B1 trial copy.
- `git status` showed only the five sheets, the board, the two tables and the six new library files, all under `hardware/pcb-main-v8/kicad/`. No file under `hardware/` or `lab/` outside v8's folder is newer than the start of the conversion. `kicad_io` loads all of them (sheets 20260306, board 20260206, libraries 20241209).

**Task 4 (`60e9d12`). Gate, all on the migrated working tree, `KICAD_CLI` on 10, `tools/.venv/bin/python`.**
- **Netlist.** kicad-cli 10's netlist of the migrated v8 against kicad-cli 9's of the `ref/` copy at the freeze (`regress.py netlist --strip-b`): 296/296 components, 158/158 nets, 0 components and 0 nets differing. The only differences are the 14 net-class strings, the PLAN exporter item. NETLISTS EQUAL.
- **ERC.** 107 violations, all warnings, 0 errors: 81 pin_to_pin, 2 lib_symbol_issues (J7 `USB-C_SMD-TYPE-C-31-M-12`, U5 `BQ24195RGET`), 5 same_local_global_label, 19 lib_symbol_mismatch. 0 setup items. Exactly the PLAN list. The 19 mismatches are the same items (sheet and symbol uuids) as in Worker #16's B1 trial: TH1 `Thermistor_NTC` and the 18 jumpers. Worker #16's `ercitems.py` finds the 88 non-setup items identical to B1 and to the `cfg0` baseline (description, uuids and positions).
- **Checks** (`tools.sh`): `tidy_fields --check` and `tidy_labels --check` (TOTAL 0, nothing written), `v8_power_sheet` (PHASE 10 CHECK PASSED), `v8_mcu_sheet` (CHECK PASSED), `v8_bus_sheet` (PHASE 9 CHECK PASSED), `v8_debug_sheet` (LAYOUT CHECK PASSED, PHASE 11 CHECK PASSED), `v8_project_setup --verify --no-v7-compare`, `layout_check`, `extract --check-sheet-pins`. All exit 0. Each output equals B1's, apart from two lines:
  - `v8_project_setup`: "board items … nets 1" → "nets 0". B1 converted only the sheets; here the board is converted too. The KiCad 9 board has one `(net 0 "")` declaration, and the KiCad 10 format declares no nets (name-only nets, PLAN "Board write path"). The empty board's DRC is unchanged: one `invalid_outline`.
  - `extract`: the netlist byte count (573,760 → 573,677), because the netlist carries the source path and the paths have different lengths.
- **`layout_check` re-baselined: no change.** `--update-baseline` printed "Baseline unchanged." and `tools/schematic-modify/layout_baseline.json` has no diff. `layout_check` and `layout_check -v` on the migrated v8 with kicad-cli 10 are identical to the same commands on `ref/` with kicad-cli 9 (paths normalised), and nothing is below baseline. Phase 12 showed why: every field, label, sheet pin and text item plots in the same box on 10.
- **`extract.py --previous`** (previous = the committed file, copied to scratch first): "No structural changes", 42 sheet pins, 0 unresolved. Against the previous file, the only differences are `_provenance` (the five new source hashes, `generator_commit` `6bd9bc8`, `generated`) and `source.extracted_at`. Its provenance keeps the root plus 4 `sources` form.
- **`--check-sheet-pins`:** 42 pins, 0 offenders.
- **`check_state.py --fresh hardware/pcb-main-v8/kicad/circuit-context.json`** (global python3): FRESH ("source … and 4 more match"), before and after the commit.
- Committed as `60e9d12` (5 sheets, board, two tables, six libraries, circuit-context.json, TASKS ticks). The lab pre-commit hook ran and accepted it. Then `v8-schematic-freeze-k10` (annotated) went on `60e9d12`. Neither tag was pushed.

**For the next session.**
- v8 is on KiCad 10 from `v8-schematic-freeze-k10`. Run kicad-cli on v8 only with `KICAD_CLI` on 10 and a `KICAD_CONFIG_HOME` that has KiCad 10's default tables. Without one, ERC shows the setup items, and kicad-cli 10 writes the real `~/Library/Preferences/kicad/10.0`.
- The harness's `run` still archives v8 at `v8-schematic-freeze` (KiCad 9) by default, and `reference-k9.txt` is unchanged. `--v8-ref v8-schematic-freeze-k10` runs it on the migrated v8.
- Before any GUI use of v8 on 10 (Phase 15), the user accepts KiCad 10's default global library table on first launch (G3).

**Handoff checks.** `git status` is clean. Nothing under `hardware/pcb-main/`, other boards, `lab/`, `.githooks` or `tools/` changed (`git diff 982efcc HEAD --stat`). The global `python3` is unchanged. No new documents, nothing Deferred.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 17 | Phase 14: Migrate v8 to KiCad 10 | DONE | No — clean completion | d0bcc1c | Migration `60e9d12`, tagged `v8-schematic-freeze-k10`; `-k9` alias on `0d6255b`; every gate item passed |

#### Verification
- 3 commits, `6bd9bc8`..`d0bcc1c`. Every changed file is under `hardware/pcb-main-v8/kicad/` or this initiative's folder. v8's sheets are at format 20260306 (generator_version 10.0), and the board at 20260206.
- Tags: `v8-schematic-freeze` and `v8-schematic-freeze-k9` both resolve to `0d6255b`. `v8-schematic-freeze-k10` is an annotated tag on `60e9d12`.
- **Orchestrator re-run** on the migrated working tree, with `KICAD_CLI` on 10 and a scratch `KICAD_CONFIG_HOME` seeded with KiCad 10's template tables:
  - `v8_debug_sheet --check`: PHASE 9/10/11 CHECK PASSED and LAYOUT CHECK PASSED.
  - ERC: 0 errors, 81 pin_to_pin, 2 lib_symbol_issues, 5 same_local_global_label, 19 lib_symbol_mismatch. This is exactly PLAN's gate list.
  - `check_state.py --fresh`: FRESH.
  - The tree is clean afterwards.
- **The harness still defaults to the KiCad 9 freeze.** Use `--v8-ref v8-schematic-freeze-k10` to run it on the migrated v8.
- v8's `.kicad_prl` was rewritten by `pcb upgrade`. It's gitignored, and the original is saved in scratchpad/p14w/out/prl.before.
- **Next: Phase 15 (live IPC trial)** has user steps. The user is asked before dispatch.

User chose to run Phase 15 now (2026-11-12). The Worker can't talk to the user, so the Orchestrator relays: the Worker stops at each user step and is continued with the user's report.

---

### Worker #18 — Phase 15: Live IPC trial (kipy)

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 15 — Live IPC trial (kipy)
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN "Trials", "Board write path". SESSION.md Worker #15 Notes (pcbnew/kicad_io board edits on v7, C9 DRC effects), Worker #16/#17 Notes (KICAD_CONFIG_HOME). landscape.md §2 kipy row.

Tasks assigned: Phase 15 tasks 1–2; stop before G4.

Notes: work in stages and return at each user step with exact numbered instructions (the Orchestrator relays and continues you). Stage A: kipy venv (scratchpad), scratch KiCad-10 copy of v7 board, the trial script, user steps to enable the API server and open the copy. Stage B: run the trial (list, move 3, rotate 1, read back) with timings; then ask the user to move one named part and save. Stage C: read the correction back, compare disk vs live. Choose footprints whose moves are harmless to DRC where possible.
Rules: never open or touch working-tree board files; hardware/ and lab/ unchanged; the user's real KiCad 10 prefs will change when the GUI enables the API server — record that.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p15/`.
- `venv`: python3.13 with `kicad-python==0.8.0`; the full freeze is in `requirements-kipy.txt`.
- `v7k10`: `git archive c2acffc` of the kicad and resources folders, converted with kicad-cli 10 `pcb upgrade`. The user opened this copy in the GUI.
- `orig`: the converted board before the GUI touched it (sha1 `8e6bfd4f`).
- `cfg`: the scratch `KICAD_CONFIG_HOME`, seeded with KiCad 10's template tables. Every kicad-cli and pcbnew run here used it.
- Scripts in `scripts/`:
  - `trial.py`: the IPC trial. Commands `probe`, `list`, `apply`, `read` and `dump`. Every call is timed, and busy replies are retried and counted.
  - `pn_plan.py`: the same edits through pcbnew.
  - `disk_fps.py`: footprints read from a file with pcbnew.
  - `bmdiff.py`: a board-model diff keyed by ref, with segments and vias compared as multisets.
  - `drcdiff.py`: the one from p13.
- Outputs:
  - `trial-log.jsonl`: every call.
  - `ipc-after-apply.json` and `ipc-after-save.json`: IPC dumps.
  - `disk-*.json`, `bm/`, `drc/`.
  - `saved/`: a snapshot of the GUI-saved project.
  - `prefs10_{before,after_stageB,after_stageC}.txt`.

**Setup (task 1).**
- **Version.** kipy 0.8.0 is the latest release, and it was built against API 10.0.6. Against KiCad 10.0.8 every call worked. kipy's own `check_version()` would raise `FutureVersionError` on the patch-level gap, so the script doesn't call it.
- **Connection.** The socket is `/tmp/kicad/api.sock`, and the sandbox let the script reach it.
- **User steps.** The user enabled the API (Preferences → Plugins, "Enable KiCad API", then restarted KiCad). They opened the scratch project through the project manager. `probe` confirmed the project path is the scratch `p15/v7k10/...`.

**The parts chosen, and why.** Every footprint on v7 is routed, so any move risks DRC. I used round test-point pads, each moved toward or along its single track by 0.5 mm. That keeps the track end inside the 1 mm pad radius.
- Moves: TPIO21 by −0.5 mm in x, TPIO16 by −0.5 mm in x, TPIO43 by +0.5 mm in y.
- Rotate: TP3 by +45°. It's a 1.5 mm circle, so the rotation changes the pad angle and fields but no copper.
- The same edits through pcbnew, DRC'd with kicad-cli 10, gave 25 items before and after. The only change was the U6 pad 2/4 item, which swaps with track order (Worker #15).

**Trial (task 2).**

*Timings.* 42 API calls across six runs. **0 busy, 0 timeouts, 0 errors.** Per call:

| Call | Time |
|---|---|
| ping, get_version, get_open_documents, get_board | 0.3–7.6 ms each |
| get_footprints (93 footprints) | 27–39 ms; 120 ms straight after the commits |
| update_items | 0.8–12.6 ms |
| push_commit | 10–15 ms |
| first begin_commit | 0.5 ms |
| begin_commit straight after a push | 98–163 ms (the GUI redrawing) |
| the whole `apply` run (connect, list, 4 commits, fresh read-back) | 620 ms |

*What the trial showed.*
- **Edits.** Each edit is one commit, so it shows in the GUI's Undo History as its own step ("Phase 15 trial: …"). The user saw the four steps there. They didn't see the 0.5 mm moves by eye on a busy board.
- **Read-back.** It matched the plan exactly: positions, pad positions and angles, and the reference text. Only those 4 of the 93 footprints changed.
- **The user's correction.** The user set TPIO21 back to (115.5, 126.5) in its Properties dialog and saved with Cmd-S, with no dialogs. IPC then read back TPIO21 at (115.5, 126.5) and the other three as the script had moved them.

*Disk against IPC.*
- **Footprints.** `disk_fps.py` read all 93 footprints from the saved file, and they match the IPC dump on every value: position, rotation, pads, and reference-text position and angle.
- **Changed against the original.** On disk only TPIO16, TPIO43 and TP3 differ from `orig`. TPIO21 is back exactly.

*KiCad's save normalisation.*
- **Size.** The saved file differs from the converted original by 10,422 lines (5,211 each way).
- **Cause.** This is the one-time track regrouping on a converted board's first KiCad 10 save, which Phase 13 recorded for pcbnew (+10,444).
- **Proof.** I made `pn-corr`, the same final state written by pcbnew from `orig`. The GUI's save and pcbnew's file differ by **only 2 lines**: TP3's reference and value field offsets are `-1.647999`/`1.749999` in the GUI save against pcbnew's `-1.648`/`1.75`. That's 1 nm of rounding. kipy's `orientation` setter rotates the field positions in the client (in nm), whereas pcbnew rotates them inside KiCad.

*Board model and DRC.*
- **Board model (`bmdiff.py`).** The board model of the saved file is identical to `pn-corr`'s, with 0 differing leaves. Against the original, segments and vias are equal as multisets, and only the three footprints change.
  - **Nets.** The `nets` leaves that differ are segment ids (positional, renumbered by the regrouping). The two changed pad positions show in the `/I2C_SDA` and `/LED_DATA` topologies. GND's chain and branch split follows traversal order, with the same nodes and connectivity.
- **DRC.** kicad-cli 10 on the saved file (scratch config home) gives 25 items, the same as the original. The only change is the same U6 pad 2/4 swap.

**Side effects to know about.**
- **KiCad 10 local history.** KiCad 10 created a `.history/` git repo (2.8 MB) in the opened project folder. It has commits "Autosave" and "PCB Save", plus a README; it can be turned off under Preferences → Common → Project Backup.
  - `git check-ignore` says `hardware/pcb-main-v8/kicad/.history/` is **not** ignored. The first GUI save of v8 on 10 will leave an untracked `.history/` with a nested `.git`. That's for Phase 17 HAZARDS/GARDEN; it's not fixed here.
- **The user's real `~/Library/Preferences/kicad/10.0`** (before and after listings in scratch).
  - **New global library tables.** `sym-lib-table`, `fp-lib-table` and `design-block-lib-table` are new. Each is one nested entry, `(name "KiCad") (type "Table") (uri "/Applications/KiCad10/KiCad.app/Contents/SharedSupport/template/…")`. That's what the "use KiCad libraries" first-run choice wrote. They aren't copies of the template tables, which is what Phase 14's scratch `KICAD_CONFIG_HOME` holds. The stock libraries resolve the same way, but these tables depend on the app's path.
  - **Changed.** `kicad_common.json` now has `api.enable_server: true`. `kicad.json` changed too.
  - **Other new files.** `gerbview.json`, `pl_editor.json`, `installed_packages.json`, `user.hotkeys`, `toolbars/kicad-toolbars.json`. Also `~/Documents/KiCad/10.0/scripting/plugins/` (an empty folder).
  - **Nothing changed between Stage B and Stage C.**
- **The API stays enabled** in the user's KiCad 10 until they untick it.

**Evidence for G4 and my recommendation: keep, in a narrow role.** IPC is the live channel for the W4–W6 placement reviews (AI proposes, the user watches and corrects in the open GUI, the AI reads the corrections back). It is not the board writer.

For keeping it:
- On this task it was exact, fast (tens of ms per edit) and never busy.
- Each AI edit is one named undo step the user can see and revert.
- Reading the user's correction back takes one call.
- After the user saves, the file on disk matches what IPC reported, and matches pcbnew's writer apart from a 1 nm field rounding. DRC was unchanged.

Its limits:
- The GUI must be running, with the API enabled in the user's prefs.
- It covers the board only.
- kipy trails KiCad (0.8.0 targets 10.0.6), so it needs a pin.
- Rotation runs in the client, which causes the 1 nm drift.
- What reaches disk depends on the user's save, so the file-level checks (kicad-cli DRC, the board-model diff keyed by ref) still run on the saved file afterwards.

Where it would fit in v8:
- **v8 Phase 13 (AI placement).** `pcb_write.py` (pcbnew) stays the batch writer.
- **W4 and W5 placement reviews.** A small `pcb_live.py` in the pinned kipy venv proposes moves into the open board, one commit per block, and reads the positions back into the placement report after the user's edits.
- **W6 and v8 Phase 16 (routing).** Read-back of the user's hand routing (`get_tracks`/`get_vias`) is plausible. It wasn't tested here, and this trial doesn't support live track writes.
- **A tools/CONTEXT.md line if kept.** Something like: "Live board edits and read-back use kipy (pinned) over IPC with KiCad 10 open on the board; edits are one commit each; after the user saves, verify on disk with kicad-cli DRC and board_model."

The case for dropping it: the same loop can run on files instead (the user saves, the AI reads with `kicad_io`), with no prefs change and no extra venv. That costs a save-and-reload on every turn, and the AI's moves stop being undo steps.

**Handoff checks.**
- `hardware/`, `lab/` and `.githooks` are unchanged, and no working-tree board was opened.
- The global python3 is untouched.
- kicad-cli ran only with the scratch config home.
- KiCad is still open on the scratch board, as the Orchestrator asked.
- No new documents. Nothing Deferred: the `.history` finding is for Phase 17.

**G4 close-out (after the user's decision).** Kept, in the narrow role. `tools/requirements-kipy.txt` pins kicad-python 0.8.0 and its 10 transitive packages (the trial venv's freeze), and its header says to skip `check_version()`. Its venv `tools/.venv-kipy/` is gitignored; `tools/requirements.txt` and `tools/.venv` are unchanged. tools/CONTEXT.md gains a "Live board edits (IPC)" paragraph under pcb-context and a line under Dependencies. PLAN Trials gains an "IPC outcome" bullet: W4–W5, `pcb_write.py` stays the writer, W6 / v8 Phase 16 untested, skip the version check. The G4 line is marked done. The `.history/` gitignore is left for Phase 17. `hardware/`, `lab/` and `.githooks` are unchanged.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 18 | Phase 15: Live IPC trial (kipy) | PARTIAL | Yes — resolvable: a planned stop at the G4 user gate (Stages A and B also stopped at planned user steps) | a2571a0 | Tasks 1–2 done; G4 open |

#### Verification
- `git diff 3f9ce36 a2571a0` touches only SESSION.md and TASKS.md. The tree is clean. TASKS Phase 15 tasks 1 and 2 are `[x]`; G4 and the Handoff are `[ ]`. PLAN has no date-stamped headings.
- trial-log.jsonl re-read: all 6 command `end` records show busy 0, timeouts 0, errors 0. kipy's API is 10.0.6 and KiCad is 10.0.8.
- disk-saved.json vs ipc-after-save.json re-compared for the four parts: TPIO21 (115.5, 126.5, 0°), TPIO16 (142.3, 129.1), TPIO43 (142.8, 110.4, 90°), TP3 (78.455, 104.0, 135°). They are identical, 93 footprints each.
- DRC JSONs recounted: pn-base, pn-plan and saved each have 22 violations, 0 unconnected and 3 parity items (25 in total), which matches the Worker.
- `git check-ignore` confirms that `hardware/pcb-main-v8/kicad/.history/` is not ignored.
- Carries to Phase 17: KiCad 10 `.history/` (gitignore it, or turn off Project Backup); the user's KiCad 10 global lib tables are nested app-path references rather than copies; api.enable_server stays true; kipy's version check fails against 10.0.8.

---

### G4 — user decision (2026-11-12)

- **Keep, in a narrow role.** Live IPC (kipy, pinned) is the channel for the v8 W4–W5 placement reviews: the AI proposes moves into the open board, one commit (undo step) per edit; the user corrects by hand; the AI reads the corrections back. `pcb_write.py` (pcbnew on 10) stays the batch writer. Hand-routing read-back (W6 / v8 Phase 16) is untested.
- **KiCad 10 `.history/`: gitignore it.** This is Phase 17 work (the .gitignore entry plus a HAZARDS line).

#### Result (continued after G4)
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 18 | Phase 15: Live IPC trial (kipy) | DONE | No — clean completion after G4 | adb185e | G4 closed (keep, narrow); Handoff checked |

#### Verification (continued)
- `git diff 162ca91 adb185e`: .gitignore (+`tools/.venv-kipy/` only), PLAN (IPC outcome bullet; G4 marked done), TASKS (Phase 15 all `[x]`), the Worker's own Notes block, tools/CONTEXT.md (Live board edits paragraph plus a Dependencies line), and the new tools/requirements-kipy.txt. Nothing under hardware/, lab/ or .githooks. PLAN has no date-stamped headings. The tree is clean.
- My G4 decision and Result blocks are untouched.

---

### Worker #19 — Phase 16: MCP server trial

**Dispatch:**
```
Initiative: kicad10-tooling
Phase: 16 — MCP server trial
Initiative path: docs/initiatives/kicad10-tooling/
Additional reading: PLAN "Trials" (incl. the IPC outcome bullet), OQ-5. SESSION.md Worker #18 Notes (trial method, timings, prefs effects, .history). Phase 15 artefacts in scratchpad/p15/ (trial.py, trial-log.jsonl, pn-plan).

Tasks assigned (from TASKS.md Phase 16): tasks 1–2; stop before G5.

OQ-5 answered by the user (2026-11-12): kicad-mcp-pro. Record it in PLAN (strike OQ-5) as part of task 1.

Notes: work in stages and return at each user step with exact numbered instructions (the Orchestrator relays and continues you). Pin kicad-mcp-pro to a release in its own venv (scratchpad, or gitignored under tools/); configure it project-local for the trial only, read-only profile first, then the gated write profile for the moves. Fresh scratch KiCad-10 copy of v7's board (git archive c2acffc, converted as in p15). The same task as Phase 15 (list, move TPIO21/TPIO16/TPIO43, rotate TP3, read back; the user corrects one part and saves; read back; disk compare, board_model diff, DRC with a scratch KICAD_CONFIG_HOME). Measurements as in Phase 15, plus tool calls and tokens per task against Phase 15's script. The MCP tools have to be driven by an agent: if a project-local MCP server can't be loaded into a running session, say so and propose how to run it (e.g. the user restarting Claude Code, or a sub-session) rather than improvising. KiCad 10 still has the API enabled from Phase 15.
Rules: never open or touch working-tree board files; hardware/ and lab/ unchanged; no change to global python3 or the lab hook; any MCP config added must be removable and named in your Notes; record any change to the user's KiCad or Claude config.
```

#### Notes

Scratch: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/1edf598d-7bc7-4919-a0bd-71f5981db13e/scratchpad/p16/`.

**Stage A (task 1, setup).**
- **OQ-5** recorded in PLAN (struck; kicad-mcp-pro). PLAN Trials "MCP" bullet now names the version and profile.
- **Install.** `venv/`: python3.13 venv with `kicad-mcp-pro==4.14.0` (latest; released 2026-11-12, the project ships near-daily). It pulls `kicad-python==0.8.0` (same as Phase 15), `kicad-sch-api 0.5.6`, `mcp 2.3.0`; 90 packages, frozen in `requirements-mcp-pro.txt`. Global python3 untouched.
- **Profiles.** The `default` profile (25 read-only tools) has no footprint list or move tool. `build` doesn't either. `pcb_only` does: `--mode readonly` = 44 tools (incl. `pcb_get_footprints`), `--mode write` = 107 tools (adds `pcb_move_footprint`, absolute x/y/rotation through kipy `update_items`, plus `pcb_save`, `pcb_begin_commit` and many others). Tool schemas cost about 11.5k tokens (readonly) and 35k tokens (write) of context, measured as JSON chars / 4.
- **Config (removable, nothing global).** Two MCP config files in the scratch folder, `mcp-readonly.json` and `mcp-write.json`, each a stdio server `kicad` with `--profile pcb_only`, `--project-dir` the scratch board, a JSON log in `logs/`, and env `HOME=p16/home` (so the server neither reads nor writes `~/.config/kicad-mcp-pro`), `KICAD_CONFIG_HOME=p16/cfg` (copy of p15's scratch config), `KICAD_MCP_KICAD_CLI` = KiCad 10's kicad-cli, telemetry off. No `.mcp.json` in the repo, no change to `~/.claude*` or any Claude Code settings so far.
- **Smoke test** (`scripts/smoke.py`, initialize + list_tools only): both configs start. Startup defers IPC, but `list_tools` probes it (ping, version, open board) and hides tools that need a live board (see the rebuild below for what that changes).
- **Scratch board.** `v7k10/`: `git archive c2acffc` of `hardware/pcb-main/{kicad,resources}`, `kicad-cli 10 pcb upgrade` with the scratch config. The converted board's sha1 is `8e6bfd4f`, identical to Phase 15's `orig`. Copy in `orig/`.
- **How the tools get driven.** A running Claude Code session loads MCP servers only at start, so neither this Worker nor the Orchestrator can call them. `claude` itself hangs in this Worker's sandbox, so I can't start a sub-session either. Proposed: the user runs `run.sh 1|2|3` in their own terminal. Each run is a headless `claude -p` sub-session with `--mcp-config <file> --strict-mcp-config`, only `mcp__kicad` tools allowed, built-in tools disallowed, transcript saved as `run-N.jsonl` (stream-json: every tool call and token usage). `scripts/usage.py` summarises it; per-call latency comes from the server log. Prompts: `prompt-1-read.txt`, `prompt-2-write.txt` (refuses to edit unless the four parts are at Phase 15's original positions; never calls `pcb_save`), `prompt-3-readback.txt`.

**Stage A rebuilt (2026-11-18).** About six days after the first return, macOS's periodic `/tmp` cleanup had emptied the scratchpad (p15 and p16: venv, configs, prompts, scripts and both scratch boards; only empty folders were left). Phase 15's numbers survive only in SESSION and PLAN.
- **`rebuild.sh`** (`p16/rebuild.sh`) rebuilds all of Stage A in one idempotent command: the 4.14.0 venv (reinstalled only if missing or a different version), `cfg/10.0` seeded with KiCad 10's template `{sym,fp}-lib-table`, the board from `git archive c2acffc` plus `kicad-cli 10 pcb upgrade` (only if missing, or with `--fresh-board`, so a rerun mid-trial keeps the user's edits), `orig/` and the sha1 check (`8e6bfd4f`, matched again), both MCP configs, the three prompts, `run.sh`, `scripts/smoke.py` and `scripts/usage.py`, then the smoke test. The script itself lives in `/tmp` too: if it's lost, its full text is in Worker #19's second return to the Orchestrator.
- **The tool list depends on KiCad's state when the client lists tools.** With KiCad running but no board open (as now): readonly 41 tools (~11.2k tokens), write 56 (~23.3k). `pcb_move_footprint`, `pcb_save` and the commit tools are absent. On 2026-11-12, with the p15 board open: 44 and 107 (~35k). Claude Code lists tools once when the session starts, so the board must be open in KiCad before each `run.sh`. For G5: an agent session started before the board is open can't edit, and the tool budget changes with KiCad's state.
- **HAZARD for Phase 17:** macOS's periodic cleanup deletes files under `/private/tmp` (this includes the Claude Code scratchpad) that haven't been touched for about three days. A multi-day initiative with user gates must not keep anything it needs for a later gate only in the scratchpad: keep a rebuild script, or keep it under a gitignored repo path.

**Task 1 closed.** The user ran `run.sh 1` with this setup. The server config reaches only the sub-sessions that `run.sh` starts (`--mcp-config` from the scratch folder, `--strict-mcp-config`). Nothing was added to the repo or to Claude Code's settings.

**Run 1 (read-only listing, 2026-11-18 14:36–14:37).** `run-1.jsonl` and `logs/server-readonly.log` in p16.
- **Agent.** claude-opus-5-5, 9 turns, 34.5 s wall (33.9 s of it model time). 8 tool calls, 0 errors:
  - Claude Code deferred the MCP schemas, so 2 of the calls were ToolSearch loading them;
  - the other 6 were `kicad_get_project_info`, `pcb_get_board_summary`, `pcb_get_footprints`, `pcb_get_live_edit_state`, `pcb_get_board_as_string` and `pcb_list_test_points`.
- **Tokens and cost.** Input 18, cache write 17,652, cache read 129,197, output 3,472; $0.237. Tool results were 10.7k chars. Phase 15's equivalent was one script run (`list` output 6.7k chars, about 1.7k tokens) after writing `trial.py` once (7.1k chars, about 1.8k tokens).
- **Server latency.** `kicad_get_project_info` 0.8 ms; `pcb_get_board_summary` 93 ms; `pcb_get_footprints` 35 ms for 93 footprints (Phase 15's `get_footprints` took 27–39 ms); `pcb_get_live_edit_state` 0.7 ms; `pcb_get_board_as_string` 77 ms; `pcb_list_test_points` 1.2 ms. No busy replies and no retries. Server start to first call took about 4.5 s.
- **Result.** 93 footprints, with the four parts at the expected positions and the open board confirmed. The agent stopped because nothing reported rotation. Nothing was edited, and the board on disk still has sha1 `8e6bfd4f`.
- **The rotation gap is real, not something the model missed.**
  - Read from the source: `pcb_get_footprints` formats reference, value, x/y at `:.2f`, layer and id, with no orientation. `pcb_get_pads` gives positions only. `pcb_get_board_as_string` is truncated at 50,000 chars of a 1.1 MB board.
  - No read tool in the full 342-tool catalog prints footprint orientation. The only live source is the reply from `pcb_move_footprint` ("verified rotation …"), which you get only by writing.
  - Positions come back rounded to 0.01 mm, so TP3's true x of 78.455 reads as 78.45. An agent that derives a relative move from the list moves off-grid parts by up to 5 µm.
  - Phase 15's kipy script read exact nm values and the orientation.
- **Changes for run 2 and run 3.**
  - Run 2 is limited to `kicad_get_project_info`, `pcb_get_board_summary`, `pcb_get_footprints` and `pcb_move_footprint`.
  - Run 2 checks only the start positions (within 0.01 mm), and refuses to edit if any is off.
  - Run 2 is given exact absolute targets (TPIO21 115.0/126.5; TPIO16 142.3/129.1; TPIO43 142.8/110.4; TP3 78.455/104.0 at 135°, from Phase 15's known start). It reports the rotation each move call returns. It still never saves.
  - Run 3 compares positions only.
  - The `run.sh` summary line now comes from the last `"type":"result"` record, parsed with python. The old sed version printed usage JSON.
  - All of this is in `rebuild.sh`. A rerun with the board open kept the board and lists 44 and 107 tools again.
- **Claude-side effect.** Each `run.sh` sub-session writes its transcript under `~/.claude/projects/-private-tmp-claude-501--Users-marcocleirigh-Workspace-motion-play-1edf598d-7bc7-4919-a0bd-71f5981db13e-scratchpad-p16/`. Run 1 also left one oversized tool result there (`pcb_get_board_as_string`). The folder is removable and isn't config.


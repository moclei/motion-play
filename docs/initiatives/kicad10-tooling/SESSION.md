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
| `(show_name no)` on every property | 3,696 → 0; written back as bare `(show_name)` | **Yes. kiutils reads the token's presence as true and writes `(show_name)`, which KiCad 10 reads as `show_name yes`.** All 3,696 v8 properties (v7: 1,652) come back with their field name shown |
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

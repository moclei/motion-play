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

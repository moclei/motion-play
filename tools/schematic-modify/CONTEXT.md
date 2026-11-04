# Schematic Modify Toolkit Context

Programmatic helpers for editing existing KiCad schematics in place.

## Purpose

`schematic-modify` fills the gap between:

- `tools/schematic-gen/` (generates full new sheets from a structured spec)
- `tools/schematic-context/` (extracts + annotates context data from schematic files)

Use `schematic-modify` when you need to append/remove components or sheet links in an existing `.kicad_sch` without rewriting the whole file.

## Rule: kiutils loads go through the shim; no write while KiCad is open

kiutils 1.4.8 (the last release, written for KiCad 7) does not read KiCad 8/9's `(hide yes)`. A bare kiutils load + save of a KiCad-saved sheet unhides every hidden field and drops `pin_numbers`/`pin_names` hiding (v8 lost 536 fields this way; `docs/research/kicad-ai-tooling-2026-11/schematic-readability.md` §1).

- **Every kiutils load of a `.kicad_sch` or `.kicad_sym` goes through `kiutils_k9.py`.** Importing it patches kiutils once per process (effects, properties, `pin_numbers`/`pin_names`, pins). `modify.py` imports it, so anything that imports `modify` is covered. A script outside this folder adds `tools/schematic-modify` to `sys.path` and does `import kiutils_k9` before its first `from_file` (see `tools/schematic-context/*.py`, `tools/schematic-gen/*.py`). A v7 `c2acffc` round trip through the shim keeps every hidden flag (496/99/49/77/194 per sheet); `(fields_autoplaced yes)` survives; `(exclude_from_sim no)` is dropped (harmless).
- **No schematic write while KiCad has the project open.** Save with `kiutils_k9.save_schematic(sch, path)` (or call `kiutils_k9.assert_not_open(path)` first); `ProjectDocs.save_all` and `annotate.py` already do. It raises `KiCadOpenError` while a `~*.kicad_sch.lck` exists in the project folder, because KiCad would overwrite the script's changes on its next save.
- The shim covers schematics only. A kiutils `Board` round trip of a KiCad 9 board is worse (footprint fields lose position/layer/hide, locks dropped, and kicad-cli can't load the result): see `docs/initiatives/v8-debug-board/PLAN.md` OQ-11.

## Rule: readable placement, checked by `layout_check.py`

New parts must come out readable without a GUI pass (`docs/research/kicad-ai-tooling-2026-11/schematic-readability.md` §3.4). Parts already on a sheet are not moved by any of this, and the already-run v8 phase scripts (`v8_*.py --apply`) are not re-run.

- **`layout_check.py` is part of every `--check`.** `v8_debug_sheet.py --check` ends with it, so the whole v8 chain (Phases 8–11) runs it; a new phase script's `--check` calls `layout_check.run(ROOT)` and adds its return to its failure count. Per sheet it fails on: a visible field other than Reference/Value on a non-power symbol; any symbol body, visible text box or hidden-field anchor outside the paper; text-overlap pairs or stacked identical labels above the sheet's baseline in `layout_baseline.json`; a local, global or hierarchical label with no `justify` (no baseline: none allowed, Phase 11c). The baseline only ratchets down: a lower count is reported, `--update-baseline` records it, and it never raises one (raise one only by hand, in a commit that says why). It prints the worst spots by sheet grid zone ("C3": rows A.. and columns 1.. every 50 mm from the 10 mm frame margin). v8 baseline at Phase 11b (after the 11a tidy): root 13, MCU 22, LED 5, power 51 (+ 6 stacked labels), TCA 50 overlap pairs; after the Phase 11c label pass: root 4, MCU 19, LED 5, power 39 (0 stacked), TCA 30.
- **Text geometry** (calibrated on kicad-cli 9.0.4 SVG plots of v8: 141 modelled vs 143 plotted pairs). Characters are about 0.85 × the text height wide. A symbol field's angle and justification are in the symbol's frame and turn with the symbol. A label's text is horizontal at 0/180 and vertical at 90/270, justified as written. **A local label written without a `justify` is drawn centred on its anchor, across the wire end**: most labels written by the older scripts are like this.
- **`add_component`** places Reference and Value at the library symbol's own field offsets (position turned with the symbol; the library's angle, justification and font kept), as KiCad does on placement, and writes `(fields_autoplaced yes)` so KiCad re-autoplaces them when the part moves. Footprint, Datasheet and LCSC Part stay hidden at the origin.
- **Labels** (`_make_local_label`, `_label_angle`, used by `add_component` and `set_pin_net`): always horizontal. A horizontal stub's label reads outward along the stub; a vertical stub's label runs right of the wire, or left when the pin is left of the symbol's origin. Every label is written with KiCad's own justification (0/90: left bottom; 180/270: right bottom).
- **Existing labels: `tidy_labels.py`** (Phase 11c) applies the same label rule to labels already on a sheet, netlist-neutrally: a label with no `justify` gets one; on a single horizontal wire it reads away from the wire; on a single vertical wire it is turned horizontal, away from the part (`_label_angle`, using the pin at the wire's far end); with wires on more than one side, or none, it keeps its angle. Hierarchical and global labels get `left`/`right` only. Positions, text and kind never change; identical stacked labels (kind, text, position, angle) are reduced to one. It measures the result with `layout_check.py` on a scratch copy and flips any changed label in a new overlap pair; if a sheet's count would still go up it writes nothing. GUI autoplace moves fields, not labels, so this pass comes before it.
- **Stubs:** `WIRE_STUB_LEN` is 5.08 mm (was 2.54, where a vertical part's Value met the stub's label); `add_component(stub_len=...)` and `set_pin_net(stub_len=...)` override it per call.
- **Grid rule for future generator scripts** (row and grid placement of new parts): row pitch from the longest label or value in the row, about 0.75–0.85 × 1.27 mm per character (0.85 measured) + 2.54 mm, not a fixed 5–8 mm; every coordinate snapped to the 1.27 mm grid; new parts inside the frame, with a margin from the title block. Run `layout_check.py` after placing.

## Relationship to Other Tools

- **`schematic-gen`** is source-of-truth for generated sheets.
- **`schematic-modify`** performs surgical updates on existing sheets.
- **`schematic-context/annotate.py`** remains the single place that writes `ai_*` properties.

Design rule: this toolkit sets electrical properties (nets, footprint, LCSC fields) and delegates annotation to `annotate.py` after placement.

## Current Files

- `kiutils_k9.py`: the KiCad 8/9 `(hide yes)` shim and the lock-file save guard (`save_schematic`, `assert_not_open`, `lock_files`). See the rule above
- `tidy_fields.py`: `--check | --apply`. Netlist-neutral field tidy for a whole project (default v8): hides every placed-symbol field except Reference and Value, restores `pin_numbers`/`pin_names` hiding on embedded library symbols (from v7 `c2acffc` for the same `lib_id`, else from the source library), and moves every `ai_*` field to its symbol's position. `--check` prints per-sheet counts (including visible text left off the paper) and writes nothing
- `tidy_labels.py`: `--check | --apply` (`-v` lists each label). Netlist-neutral label justify pass and stacked-label dedupe for a whole project (default v8); see the placement rule above. Through the shim, refuses while a `~*.lck` exists
- `layout_check.py`: read-only readability check for a whole project (default v8): visible extra fields, off-paper items, labels with no justify, overlap and stacked-label counts against `layout_baseline.json` (ratchets down; `--update-baseline`), worst grid zones; `-v` lists every pair. See the placement rule above
- `layout_baseline.json`: the committed per-sheet baseline (`overlap_pairs`, `stacked_labels`, keyed by repo-relative sheet path)
- `modify.py`: reusable helpers (`add_component` (with `project_name`), `remove_component`, `add_hierarchical_label`, `add_sheet_reference`, `annotate_components`, `pin_position`, `set_pin_net`, `remove_no_connect_at`, `remove_junction_at`, `add_local_label`, `add_wire`, `rename_hlabel`, `rename_sheet_pin`, and from Phase 10 `remove_component_with_stubs`, `set_property`, `add_power_symbol`). A power symbol's Value names its global net in KiCad 9 (checked on the v8 project), so `add_power_symbol` and a Value edit retarget a rail. `pin_position` handles 0/90/180/270-degree symbols (fixed 2026-11-03: 90/270 used to put pins at the wrong end; mirrored symbols still raise). `set_pin_net` moves a label-wired pin to another net (renames the stub's label, or replaces a no-connect with a label); it refuses pins wired into a network
- `esp32_integration.py`: initiative-specific modifications for ESP32-S3 direct integration
- `v8_project_setup.py`: v8-debug-board initiative. Copies the v7 project (`c2acffc`) to `hardware/pcb-main-v8/kicad/` as `motion-play-main-v8`, renames instance project names via kiutils, writes an empty stackup-only `.kicad_pcb`, and verifies (ERC, netlist vs v7, DRC load). `--verify --no-v7-compare` re-runs the checks after edits
- `v8_mcu_sheet.py`: v8-debug-board Phase 8. U3 pin moves and jumper rows a, e, g on `esp32_s3.kicad_sch` (JP1/JP2 1x4 headers, J10 + JP3/JP4 external master, JP5 SJ3), `+3.3V_BUS` sheet pin, IC1 swap to SN74AHCT1G125 on `led_controller.kicad_sch`. All label-style, so no GUI wiring. `--check` exports the netlist and checks pin -> net against the GPIO allocation and the all-v7 jumper positions against v7 @ `c2acffc` (it also applies later phases' jumpers by importing `v8_bus_sheet.py`)
- `v8_bus_sheet.py`: v8-debug-board Phase 9. TCA sheet (now A3): row b (47 Ω + bypass header per channel line, TPD2E2U06 + GND-leg header per connector, CHn_x / CHn_x_CONN split by renaming the channel hierarchical labels), row d (2x3 upstream selector headers, R28/R29 moved off the bus, 4.7 k/10 k options, downstream 4.7 k + open SJ2), row f (BQ_SDA/BQ_SCL headers; U5 relabelled on the power sheet; root sheet pins), channel test points + ground points. Wire-wired pins are freed by removing the wire/junction first, then labelled. `--check` = MCU check + pin -> net + each jumper's positions
- `v8_debug_sheet.py`: v8-debug-board Phase 11. Debug features (test points + ground points, debug LEDs, UART0 and spare-GPIO headers). `--check` = Phase 8–10 checks + Phase 11 pins, BOM audit, ERC summary, then `layout_check.py` (Phase 11b): the end of the whole v8 check chain
- `v8_power_sheet.py`: v8-debug-board Phase 10. Power sheet modified in place from `tools/schematic-gen/power_v8_spec.json` (paper A3, new parts gridded): battery block (J8 XT30, F3, Q20/Q21, gate network, SW4, J9) replacing BT1/Q2/R33/R34; rows c, h, i, j, k, l; STAT LED; PMID 6 x 22 uF; rail test points + GND points; J7 on a v8 shell-GND footprint (`libraries/footprints/motion-play-v8.pretty`). Rails: global +3.3V -> +3.3V_MCU; bus loads on the global +3.3V_BUS; D5 on +5V_CORE; link h4 on the LED sheet ahead of v7's R27. `--check` = Phase 8 + 9 checks + pin -> net for every power part + each power row's positions. The all-v7 comparison drops BT1/Q2/R33/R34 (v7) and the new battery parts (v8), both modelled conducting: battery protection has no v7 position (user decision 2026-11-03)

## Typical Workflow

1. Run `esp32_integration.py --apply` (or custom script using `modify.py`) to place components/sheet refs off to one side.
2. Script calls `tools/schematic-context/annotate.py` for `ai_*` properties.
3. Open KiCad and do manual placement/wiring cleanup.
4. Run `tools/schematic-context/extract.py --previous` to refresh `circuit-context.json`.

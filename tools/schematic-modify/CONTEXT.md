# Schematic Modify Toolkit Context

Programmatic helpers for editing existing KiCad schematics in place.

## Purpose

`schematic-modify` fills the gap between:

- `tools/schematic-gen/` (generates full new sheets from a structured spec)
- `tools/schematic-context/` (extracts + annotates context data from schematic files)

Use `schematic-modify` when you need to append/remove components or sheet links in an existing `.kicad_sch` without rewriting the whole file.

## Relationship to Other Tools

- **`schematic-gen`** is source-of-truth for generated sheets.
- **`schematic-modify`** performs surgical updates on existing sheets.
- **`schematic-context/annotate.py`** remains the single place that writes `ai_*` properties.

Design rule: this toolkit sets electrical properties (nets, footprint, LCSC fields) and delegates annotation to `annotate.py` after placement.

## Current Files

- `modify.py`: reusable helpers (`add_component` (with `project_name`), `remove_component`, `add_hierarchical_label`, `add_sheet_reference`, `annotate_components`, `pin_position`, `set_pin_net`, `remove_no_connect_at`, `remove_junction_at`, `add_local_label`, `add_wire`, `rename_hlabel`, `rename_sheet_pin`, and from Phase 10 `remove_component_with_stubs`, `set_property`, `add_power_symbol`). A power symbol's Value names its global net in KiCad 9 (checked on the v8 project), so `add_power_symbol` and a Value edit retarget a rail. `pin_position` handles 0/90/180/270-degree symbols (fixed 2026-11-03: 90/270 used to put pins at the wrong end; mirrored symbols still raise). `set_pin_net` moves a label-wired pin to another net (renames the stub's label, or replaces a no-connect with a label); it refuses pins wired into a network
- `esp32_integration.py`: initiative-specific modifications for ESP32-S3 direct integration
- `v8_project_setup.py`: v8-debug-board initiative. Copies the v7 project (`c2acffc`) to `hardware/pcb-main-v8/kicad/` as `motion-play-main-v8`, renames instance project names via kiutils, writes an empty stackup-only `.kicad_pcb`, and verifies (ERC, netlist vs v7, DRC load). `--verify --no-v7-compare` re-runs the checks after edits
- `v8_mcu_sheet.py`: v8-debug-board Phase 8. U3 pin moves and jumper rows a, e, g on `esp32_s3.kicad_sch` (JP1/JP2 1x4 headers, J10 + JP3/JP4 external master, JP5 SJ3), `+3.3V_BUS` sheet pin, IC1 swap to SN74AHCT1G125 on `led_controller.kicad_sch`. All label-style, so no GUI wiring. `--check` exports the netlist and checks pin -> net against the GPIO allocation and the all-v7 jumper positions against v7 @ `c2acffc` (it also applies later phases' jumpers by importing `v8_bus_sheet.py`)
- `v8_bus_sheet.py`: v8-debug-board Phase 9. TCA sheet (now A3): row b (47 Ω + bypass header per channel line, TPD2E2U06 + GND-leg header per connector, CHn_x / CHn_x_CONN split by renaming the channel hierarchical labels), row d (2x3 upstream selector headers, R28/R29 moved off the bus, 4.7 k/10 k options, downstream 4.7 k + open SJ2), row f (BQ_SDA/BQ_SCL headers; U5 relabelled on the power sheet; root sheet pins), channel test points + ground points. Wire-wired pins are freed by removing the wire/junction first, then labelled. `--check` = MCU check + pin -> net + each jumper's positions
- `v8_power_sheet.py`: v8-debug-board Phase 10. Power sheet modified in place from `tools/schematic-gen/power_v8_spec.json` (paper A3, new parts gridded): battery block (J8 XT30, F3, Q20/Q21, gate network, SW4, J9) replacing BT1/Q2/R33/R34; rows c, h, i, j, k, l; STAT LED; PMID 6 x 22 uF; rail test points + GND points; J7 on a v8 shell-GND footprint (`libraries/footprints/motion-play-v8.pretty`). Rails: global +3.3V -> +3.3V_MCU; bus loads on the global +3.3V_BUS; D5 on +5V_CORE; link h4 on the LED sheet ahead of v7's R27. `--check` = Phase 8 + 9 checks + pin -> net for every power part + each power row's positions. The all-v7 comparison drops BT1/Q2/R33/R34 (v7) and the new battery parts (v8), both modelled conducting: battery protection has no v7 position (user decision 2026-11-03)

## Typical Workflow

1. Run `esp32_integration.py --apply` (or custom script using `modify.py`) to place components/sheet refs off to one side.
2. Script calls `tools/schematic-context/annotate.py` for `ai_*` properties.
3. Open KiCad and do manual placement/wiring cleanup.
4. Run `tools/schematic-context/extract.py --previous` to refresh `circuit-context.json`.

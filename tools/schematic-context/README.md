# Schematic Context Tools

Python scripts that extract circuit data from KiCad schematics and produce AI-optimized `circuit-context.json` files. These replace the old JSON netlist + YAML annotation system.

## Prerequisites

- **Python:** `tools/.venv/bin/python` (Python 3.13, built from `tools/requirements.txt`; kicad-tools is pinned there). Schematic files are loaded and saved only through `tools/kicad-io/kicad_io.py`.
- **KiCad 9** — `kicad-cli` must be available (macOS default: `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`)

Override the kicad-cli path with the `KICAD_CLI` environment variable if needed.

## Scripts

### extract.py

Main extraction pipeline. Combines `kicad-cli` netlist export (for connectivity) with a read of the schematic files through `kicad_io` (for component properties and hierarchy) to produce `circuit-context.json`.

```bash
# Basic extraction — outputs circuit-context.json next to the schematic
tools/.venv/bin/python tools/schematic-context/extract.py hardware/pcb-main/kicad/motion-play-main.kicad_sch

# Custom output path
tools/.venv/bin/python tools/schematic-context/extract.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
  --output path/to/circuit-context.json

# Re-extract with annotation merge — carries forward net/block annotations from a previous run
tools/.venv/bin/python tools/schematic-context/extract.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
  --previous hardware/pcb-main/kicad/circuit-context.json
```

The `--previous` flag is important: component annotations live in the `.kicad_sch` files (as `ai_` properties) and come through automatically, but net annotations and block definitions only exist in `circuit-context.json`. The merge preserves them across re-extractions.

#### Sheet pins (`sheet_interfaces`) and `--check-sheet-pins`

Each hierarchical sheet pin in `sheet_interfaces` carries the net KiCad actually connects it to. `extract.py` copies the project folder to a temp directory, places a one-pin probe symbol on the root sheet exactly on each sheet pin's connection point, and exports a second netlist with kicad-cli. A probe's net holds everything KiCad joins to that pin on both sides (parent wires, labels and power symbols, and the child's hierarchical label). Its component-pin members are then looked up in the real netlist, so the name reported is the real net's (e.g. v8's TCA box pin `VCC_3V3` → `+3.3V_BUS`). The real sheets are only read. Until Phase 12a of v8-debug-board, pins were matched by name with a power-alias table (`VCC_3V3` → `+3.3V`), which gave an empty or wrong net when the board names its rails differently; that table is gone.

```bash
# Check only: exit 1 and list each sheet pin on no net or on a net with no component pins
tools/.venv/bin/python tools/schematic-context/extract.py hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_sch \
  --check-sheet-pins          # add -v to print every pin, its net and its members
```

`--check-sheet-pins` alone writes nothing; with `--output` it also writes the context file (and still exits 1 on offenders). Only sheets placed on the root are probed (nested sheets are not). Each probe round is one more kicad-cli export (a few seconds on v8). A probe is accepted only if its members are exactly one real net's full member set; if not (a probe dropped inside a wire splits it off, as on the power-supply board), the pin is probed again at the ends of the root wire through it, then at the child's hierarchical label, and reported as an offender if none works.

### annotate.py

Writes `ai_`-prefixed custom properties to component symbols in `.kicad_sch` files through `kicad_io` (raw s-expression layer, splice save: only the edited symbols' text changes). Properties are hidden in the schematic editor, in the file's own hide form (KiCad 9 or 10), and survive schematic edits. `write_ai_properties(doc, symbol, props)` is the one writer of `ai_*` fields; `v8_debug_sheet.py` imports it.

```bash
# Annotate a single component
tools/.venv/bin/python tools/schematic-context/annotate.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
  U1 function="3.3V LDO regulator" block=power role=voltage_regulator

# Annotate multiple components with the same properties (use -- separator)
tools/.venv/bin/python tools/schematic-context/annotate.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
  R28 R29 -- role=pull_up block=i2c_mux

# Clear all ai_ properties from a component
tools/.venv/bin/python tools/schematic-context/annotate.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
  C1 --clear
```

Valid annotation fields: `function`, `block`, `role`, `critical_specs`.

The script resolves which `.kicad_sch` file a component lives on (root or child sheet) automatically.

### show.py

Displays annotation coverage across all components. Useful during interactive annotation sessions to track progress.

```bash
# Show all components with annotation status
tools/.venv/bin/python tools/schematic-context/show.py hardware/pcb-main/kicad/motion-play-main.kicad_sch

# Show only unannotated components
tools/.venv/bin/python tools/schematic-context/show.py hardware/pcb-main/kicad/motion-play-main.kicad_sch --unannotated

# Filter to a specific sheet
tools/.venv/bin/python tools/schematic-context/show.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
  --sheet led_controller
```

## Typical Workflow

1. **Edit schematic** in KiCad
2. **Extract** — run `extract.py` with `--previous` to produce an updated `circuit-context.json`
3. **Check coverage** — run `show.py --unannotated` to find new components needing annotation
4. **Annotate** — interactive session: AI proposes annotations, human confirms, write via `annotate.py`
5. **Re-extract** — run `extract.py --previous` again to merge everything into the final context file

## Output Location

| PCB | Context File |
|-----|-------------|
| Main PCB | `hardware/pcb-main/kicad/circuit-context.json` |
| Sensor Rigid | `hardware/sensor-rigid/circuit-context.json` |
| Sensor Flex | `hardware/sensor-flex/circuit-context.json` |

## Design Details

See `docs/initiatives/schematic-context/PLAN.md` for the full design rationale, context file schema, and annotation storage decisions.

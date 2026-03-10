# Schematic Context Tools

Python scripts that extract circuit data from KiCad schematics and produce AI-optimized `circuit-context.json` files. These replace the old JSON netlist + YAML annotation system.

## Prerequisites

- **Python 3.7+** (tested on 3.7.3)
- **KiCad 9** — `kicad-cli` must be available (macOS default: `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`)
- **Dependencies:** `pip install -r requirements.txt` (kiutils >= 1.4.8)

Override the kicad-cli path with the `KICAD_CLI` environment variable if needed.

## Scripts

### extract.py

Main extraction pipeline. Combines `kicad-cli` netlist export (for connectivity) with `kiutils` schematic parsing (for component properties and hierarchy) to produce `circuit-context.json`.

```bash
# Basic extraction — outputs circuit-context.json next to the schematic
python tools/schematic-context/extract.py hardware/pcb-main/kicad/motion-play-main.kicad_sch

# Custom output path
python tools/schematic-context/extract.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
  --output path/to/circuit-context.json

# Re-extract with annotation merge — carries forward net/block annotations from a previous run
python tools/schematic-context/extract.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
  --previous hardware/pcb-main/kicad/circuit-context.json
```

The `--previous` flag is important: component annotations live in the `.kicad_sch` files (as `ai_` properties) and come through automatically, but net annotations and block definitions only exist in `circuit-context.json`. The merge preserves them across re-extractions.

### annotate.py

Writes `ai_`-prefixed custom properties to component symbols in `.kicad_sch` files via kiutils. Properties are hidden in the schematic editor and survive schematic edits.

```bash
# Annotate a single component
python tools/schematic-context/annotate.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
  U1 function="3.3V LDO regulator" block=power role=voltage_regulator

# Annotate multiple components with the same properties (use -- separator)
python tools/schematic-context/annotate.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
  R28 R29 -- role=pull_up block=i2c_mux

# Clear all ai_ properties from a component
python tools/schematic-context/annotate.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
  C1 --clear
```

Valid annotation fields: `function`, `block`, `role`, `critical_specs`.

The script resolves which `.kicad_sch` file a component lives on (root or child sheet) automatically.

### show.py

Displays annotation coverage across all components. Useful during interactive annotation sessions to track progress.

```bash
# Show all components with annotation status
python tools/schematic-context/show.py hardware/pcb-main/kicad/motion-play-main.kicad_sch

# Show only unannotated components
python tools/schematic-context/show.py hardware/pcb-main/kicad/motion-play-main.kicad_sch --unannotated

# Filter to a specific sheet
python tools/schematic-context/show.py hardware/pcb-main/kicad/motion-play-main.kicad_sch \
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
| Sensor Rigid (future) | `hardware/sensor-rigid/circuit-context.json` |
| Sensor Flex (future) | `hardware/sensor-flex/circuit-context.json` |

## Design Details

See `docs/initiatives/schematic-context/PLAN.md` for the full design rationale, context file schema, and annotation storage decisions.

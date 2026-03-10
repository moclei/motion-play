# Schematic Context System — Plan

## Approach

The system has three layers: **extraction** (reading schematic data), **annotation** (adding semantic context), and **export** (producing the AI-optimized context file). Two external tools provide the foundation — `kicad-cli` for connectivity data and `kiutils` for schematic property access.

### Extraction Pipeline

```
kicad-cli sch export netlist (XML)
    ↓ pin names, pin types, net assignments, cross-sheet nets
Python extraction script
    ↑ component properties, ai_ annotations, sheet hierarchy
kiutils reads .kicad_sch files
    ↓
Merge with previous circuit-context.json (preserves net/block annotations)
    ↓
circuit-context.json
```

The extraction script:
1. Runs `kicad-cli` to export a fresh XML netlist (handles all connectivity resolution including cross-sheet nets)
2. Parses the XML for components, pins, nets, and sheet structure
3. Uses `kiutils` to read each `.kicad_sch` file for component properties (including `ai_` custom properties) and label data
4. If a previous `circuit-context.json` exists, merges forward any net annotations and block definitions
5. Writes the combined output as `circuit-context.json`

### Annotation Storage

Two categories of annotation, stored differently:

| Annotation type | Storage | Rationale |
|----------------|---------|-----------|
| **Component annotations** (`ai_function`, `ai_block`, `ai_description`, `ai_critical_specs`) | Written into `.kicad_sch` as custom properties via kiutils | Survives schematic edits — properties travel with the component |
| **Net annotations** (`type`, `protocol`, `direction`, `description`) | Stored in `circuit-context.json` only | kiutils labels don't support custom properties; merge-on-extract preserves them |
| **Block definitions** (functional groupings) | Stored in `circuit-context.json` only | Blocks are an AI-layer concept with no KiCad equivalent |

### Annotation Workflow

The annotation pass is interactive:
1. Run extraction to produce initial `circuit-context.json` (components and connectivity, no semantic context yet)
2. AI reads the context file, proposes annotations in batches grouped by apparent functional block
3. Human confirms/corrects each batch
4. Component annotations → written to `.kicad_sch` via annotation script
5. Net/block annotations → written directly to `circuit-context.json`
6. Re-extract to produce the final context file with all annotations merged

Subsequent annotation sessions (after schematic edits) only need to address new/changed components and nets — existing annotations carry forward.

### Hierarchy Handling

The main PCB uses hierarchical schematics:
- Root: `motion-play-main.kicad_sch` (51 symbols, 10 labels, 2 sub-sheets)
- Child: `led_controller.kicad_sch` (10 symbols, 5 hierarchical labels)
- Child: `tca9548A_subsystem.kicad_sch` (9 symbols, 12 hierarchical labels)

`kicad-cli` resolves cross-sheet nets automatically in the XML export (e.g., `/TCA9548A_Subsystem/CH0_SCL`). The extraction script discovers child sheets via kiutils' `sch.sheets` objects (which expose `fileName`, `sheetName`, and pin interfaces) and parses each child for its `ai_` properties.

The context file represents sheets as a flat component/net list (matching the netlist's view) but includes a `sheet_interfaces` section that makes cross-sheet signal flow explicit.

## Context File Schema

```json
{
  "schema_version": "1.0",
  "project": "motion-play-main",
  "source": {
    "root": "motion-play-main.kicad_sch",
    "sheets": {
      "led_controller.kicad_sch": "LED Controller",
      "tca9548A_subsystem.kicad_sch": "TCA9548A_Subsystem"
    },
    "source_hash": "<md5 of component refs + net names>",
    "extracted_at": "<ISO timestamp>"
  },
  "description": "<human-confirmed overall circuit description>",

  "blocks": {
    "<block_id>": {
      "description": "<what this functional block does>",
      "sheet": "<which sheet, if block is on a child sheet>",
      "components": ["<ref>", ...],
      "notes": "<design intent, constraints, future plans>"
    }
  },

  "components": {
    "<ref>": {
      "part": "<library part name>",
      "value": "<component value>",
      "footprint": "<footprint>",
      "lcsc": "<LCSC part number if available>",
      "sheet": "<which sheet this component is on>",
      "block": "<block_id>",
      "function": "<what this component does in context>",
      "role": "<pull_up|decoupling|current_limit|bypass|etc. for passives>",
      "critical_specs": "<key specs that matter for design review>",
      "pins": [
        {
          "number": "<pin number>",
          "name": "<pin function name from library>",
          "type": "<electrical type: input|output|bidirectional|passive|power_in|power_out>",
          "net": "<net name>"
        }
      ]
    }
  },

  "nets": {
    "<net_name>": {
      "type": "<power|signal|analog|clock>",
      "protocol": "<I2C|SPI|UART|WS2812B|etc., if applicable>",
      "direction": "<input|output|bidirectional, if applicable>",
      "description": "<what this net carries>"
    }
  },

  "sheet_interfaces": {
    "<sheet_filename>": {
      "description": "<what this sub-sheet does>",
      "pins": [
        {
          "name": "<hierarchical pin name>",
          "direction": "<input|output|bidirectional>",
          "net": "<net it connects to on parent>"
        }
      ]
    }
  }
}
```

## Script Design

Scripts live in `tools/schematic-context/`:

| Script | Purpose |
|--------|---------|
| `extract.py` | Main pipeline: runs kicad-cli, parses XML + kiutils, merges previous context, outputs circuit-context.json |
| `annotate.py <ref> <key=value ...>` | Writes `ai_` properties to a component in the .kicad_sch file via kiutils |
| `show.py [--unannotated]` | Reads current state, shows components/nets with or without annotations. Diagnostic tool for annotation sessions. |

`extract.py` accepts the root `.kicad_sch` path and an optional `--previous` flag pointing to an existing context file for merge.

## File Locations

| File | Location |
|------|----------|
| Tool scripts | `tools/schematic-context/` |
| Main PCB context output | `hardware/pcb-main/circuit-context.json` |
| Future: sensor-rigid context | `hardware/sensor-rigid/circuit-context.json` |
| Future: sensor-flex context | `hardware/sensor-flex/circuit-context.json` |

## Verification Approach

The acceptance criterion for this initiative is: **an AI session given only `circuit-context.json` and `hardware/CONTEXT.md` can correctly answer substantive questions about the circuit** — questions like tracing signal paths, identifying component roles, and reasoning about what would need to change for a given modification.

Before the annotation pass (Phase 3a), we define 5-10 specific test questions. After the context file is complete (Phase 3c), we run those questions in a fresh session without schematic access. Failed questions indicate gaps in the context file that need addressing.

## Open Questions

- None currently — spike validated all key assumptions.

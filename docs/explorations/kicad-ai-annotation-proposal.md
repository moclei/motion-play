# Proposal: AI-Assisted Schematic Annotation for KiCad

**Decision: Decided** — Proceeding as initiative `docs/initiatives/schematic-context/`. Approach validated via spike test (kiutils 1.4.8 + kicad-cli). Key refinements from spike: kiutils handles property read/write but not connectivity; kicad-cli fills the gap with authoritative netlist export. Net annotations stored in output file (not schematic) since kiutils labels lack property support.

## Background

This project uses KiCad 9 for PCB design, JLCPCB for fabrication and assembly, and LCSC for component sourcing. An existing KiCad plugin exports a JSON netlist to provide AI assistants with schematic context.

The current export is limited — it captures topology (what connects to what) but loses semantic information (what things *mean*). This causes AI to miss things that are obvious when reading the schematic visually: signal direction, functional groupings, power topology, design intent.

## Problem Statement

AI-assisted schematic reasoning is only as good as the data it receives. Structured netlist data has several known blind spots:

- **Auto-named nets** (`Net-(U1-Pin7)`) are opaque — no signal type, protocol, or direction is implied
- **Pin names are dropped** — knowing U1 pin 7 is `GPIO21/SDA` is far more useful than just the pin number
- **Pin electrical types are lost** — whether a pin is input, output, bidirectional, or passive is key to reasoning about signal flow
- **Passive component roles are ambiguous** — a resistor between a signal and a power rail could be a pull-up, current limiter, or something else entirely
- **Functional groupings are absent** — nothing marks a cluster of components as "the power supply block" or "the I2C interface"
- **Design intent is invisible** — structured data can represent what a circuit *is*, but not what the designer *meant*

Schematic files can also be large (114kb+ observed), making it impractical to read the raw file into an AI context window directly.

## Proposed Solution

An interactive AI-assisted annotation workflow, run via Claude Code, that:

1. Uses a small set of Python tool scripts (built on `kiutils`) to read and write `.kicad_sch` files
2. Extracts a compact JSON summary of components, nets, and existing properties — not the raw schematic
3. Interviews the designer via natural language chat to capture semantic context
4. Writes annotations back into the schematic as KiCad custom properties, in-session
5. Produces richer AI context automatically on all subsequent exports, with no further manual input

The schematic file itself is the only state. No session persistence is needed — if a session is interrupted, the next session picks up from whatever has already been annotated.

## Key Design Principles

- **Propose, don't ask open questions** — Claude should offer candidate answers ("is this your 3.3V regulator?") rather than asking "what does this do?"
- **Batch related questions** — group questions by apparent functional block, not component-by-component
- **Light-touch inference** — use footprint data, existing values, and net name patterns to form candidate answers, but always ask for confirmation. No complex inference rules; the annotation session is a one-time effort and the overhead of just answering questions is low.
- **Non-destructive** — annotations are additive custom properties; no existing KiCad data is modified or removed
- **Git-friendly** — each annotation session produces a clean diff; the history is auditable

## Technical Approach

### Why Not the KiCad Python API?

KiCad has two Python surfaces. `pcbnew` (layout) can be imported as a standalone library. The schematic module (`eeschema`) cannot — it is only accessible from inside KiCad's scripting console. A command-line script cannot call it.

### `kiutils` as the Foundation

[`kiutils`](https://github.com/mvnmgrx/kiutils) is a pure Python library that parses and writes KiCad 6–9 file formats, including `.kicad_sch`, with no KiCad installation required. It provides a full object model for symbols, properties, pins, and net labels, and supports round-trip write-back.

```python
from kiutils.schematic import Schematic

sch = Schematic.from_file("project.kicad_sch")

for symbol in sch.schematicSymbols:
    print(symbol.libraryNickname, symbol.entryName)
    for prop in symbol.properties:
        print(f"  {prop.key}: {prop.value}")
    for pin in symbol.pins:
        print(f"  pin {pin.number} ({pin.name}) → net: {pin.netName}")
```

Writing a custom property back:

```python
from kiutils.items.common import Property

new_prop = Property(key="ai_function", value="power_supply")
symbol.properties.append(new_prop)
sch.to_file()
```

This solves the context window problem: the script extracts only what is needed (refs, values, footprints, pin names, net names, existing properties) and produces a compact JSON payload — typically a few kilobytes regardless of schematic size.

### Net Label Annotations

In KiCad 7+ (including KiCad 9), net labels support custom properties. `kiutils` exposes these. Net-level metadata (signal type, protocol, direction) can therefore be stored directly on net labels in the schematic — no sidecar file needed.

### Tool Scripts

The workflow is implemented as a small set of Python scripts that Claude Code calls as tools:

| Script | Purpose |
|---|---|
| `read_schematic.py` | Parses schematic, returns compact JSON summary of all components and nets |
| `get_component.py <ref>` | Returns full detail for a single component including all pins and existing properties |
| `list_unannotated.py` | Returns components and nets that have no `ai_` properties yet |
| `annotate_component.py <ref> <key=value ...>` | Writes one or more custom properties to a component in-file |
| `annotate_net.py <net_name> <key=value ...>` | Writes one or more custom properties to a net label in-file |

All scripts operate directly on the `.kicad_sch` file. The schematic is modified in place; KiCad will reformat on next open, which is expected and fine.

### Integration Model

The designer opens a Claude Code session and converses naturally. Claude calls the tool scripts to read context, reason about what it sees, ask batched confirmatory questions, and write annotations as answers are confirmed. No special invocation is needed beyond starting the session.

Example exchange:

```
You: Let's annotate the schematic

Claude: [calls list_unannotated, read_schematic]
        Found 14 components without annotations. Starting with what looks
        like a power block — U1 (AMS1117-3.3), C3 (100µF), C4 (100nF).

        Is U1 your 3.3V linear regulator? Proposing:
          U1 → ai_function=power_supply, ai_input_rail=5V, ai_output_rail=3V3
          C3, C4 → ai_function=decoupling, ai_block=power_supply

You: Yes, but use 3V3 as the rail name not 3V3_OUT

Claude: [calls annotate_component for U1, C3, C4]
        Done. I can also see Net-(U1-Pin2) and Net-(U1-Pin3) —
        proposing to rename those to 5V and 3V3 and tag them as power rails. OK?

You: Yes
...
```

## Annotation Schema

Custom properties written to components:

| Property | Example values |
|---|---|
| `ai_function` | `power_supply`, `decoupling`, `pull_up`, `current_limit`, `mcu`, `sensor`, `connector` |
| `ai_description` | Free text, designer-confirmed |
| `ai_block` | Functional group label, e.g. `power_supply`, `sensor_interface`, `usb` |
| `ai_input_rail` | e.g. `5V` — for power components |
| `ai_output_rail` | e.g. `3V3` — for power components |

Custom properties written to net labels:

| Property | Example values |
|---|---|
| `ai_signal_type` | `power`, `signal`, `analog` |
| `ai_protocol` | `I2C`, `SPI`, `UART`, `USB` |
| `ai_direction` | `input`, `output`, `bidirectional` |

The schema is intentionally minimal. New keys can be added ad hoc during annotation sessions — the export plugin reads all `ai_` prefixed properties dynamically.

## Export Plugin Update

The existing JSON export plugin is updated to include all `ai_` prefixed properties in its output for both components and nets. The plugin interface (how it's invoked, what files it produces) does not change — only the richness of the data it emits.

The annotation tooling and export plugin can be developed independently once the property schema is agreed.

## Open Questions

- [ ] **Hierarchical schematics** — if the project uses multiple `.kicad_sch` files (sheets), do the tool scripts need to handle cross-sheet net resolution, or is annotating each sheet independently sufficient?
- [ ] **Footprint-to-function inference** — agree on a short list of footprint/value patterns worth auto-detecting (e.g. C in decoupling position, R between signal and power net). Keep this list small and confirmed by testing.
- [ ] **Export plugin changes** — review the existing plugin to confirm it reads component properties from the parsed schematic (not a compiled netlist), so `ai_` properties will be picked up without further changes.

## Next Steps

- [ ] Install `kiutils`, confirm it reads a sample `.kicad_sch` cleanly and can write a custom property back without corrupting the file
- [ ] Write and test the five tool scripts against a real schematic
- [ ] Run a first annotation session end-to-end on a small schematic
- [ ] Update the export plugin to include `ai_` properties in its JSON output
- [ ] Document the schema in the repo for future reference

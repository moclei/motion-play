# Schematic Context System — Tasks

## Phase 1a: Extraction Pipeline — XML Parsing

- [x] Create `tools/schematic-context/` directory and `requirements.txt` (kiutils, pyyaml)
- [x] Write `extract.py` — kicad-cli invocation: call kicad-cli to export XML netlist from a given root `.kicad_sch`, handle path resolution and error cases
- [x] Write `extract.py` — XML netlist parsing: parse the exported XML into component, pin, and net data structures (ref, value, footprint, LCSC part, pin names, pin types, net assignments, sheet paths)
- [x] Write `extract.py` — basic context file output: produce a `circuit-context.json` with components, pins, and nets from the XML data alone (no kiutils yet, no annotations, no blocks)
- [x] Test on main PCB: run extraction, verify all components and nets from all sheets appear correctly in the output
- [x] Commit, update TASKS.md, generate handoff prompt for next session. Note any unexpected issues or implementation decisions.

## Phase 1b: Extraction Pipeline — kiutils Integration & Merge

- [x] Add kiutils integration to `extract.py`: read each `.kicad_sch` file (root + children discovered via kiutils `sch.sheets`), extract all component properties including `ai_` prefixed custom properties
- [x] Add sheet hierarchy to `extract.py`: build `sheet_interfaces` section from hierarchical sheet pins (name, direction) and match to hierarchical labels in child schematics
- [x] Add previous-context merge to `extract.py`: if a previous `circuit-context.json` exists, carry forward net annotations and block definitions, flag new/removed items
- [x] End-to-end test: run full extraction on main PCB, verify kiutils properties and sheet interfaces appear correctly alongside XML-derived connectivity
- [x] Commit, update TASKS.md, generate handoff prompt for next session. Note any unexpected issues or implementation decisions.

## Phase 2: Annotation Tooling

- [x] Write `annotate.py` — accepts component ref + key=value pairs, writes `ai_` properties to the correct `.kicad_sch` file via kiutils (must resolve which sheet a component lives on)
- [x] Write `show.py` — reads current schematic state via kiutils, displays components grouped by annotation status (annotated vs unannotated), useful for guiding annotation sessions
- [x] Test annotation round-trip: write a property via `annotate.py`, re-extract via `extract.py`, confirm property appears in `circuit-context.json`
- [x] Commit, update TASKS.md, generate handoff prompt for next session. Note any unexpected issues or implementation decisions.

## Phase 3a: Annotation Pass — Setup & First Blocks

- [x] Define 10 test questions about the main PCB schematic — saved in `docs/initiatives/schematic-context/TEST_QUESTIONS.md`
- [x] Run initial extraction on main PCB to produce baseline `circuit-context.json` (37 components, 26 nets, all empty)
- [x] Interactive annotation session: annotate power subsystem (J2, D1, U1, C1, C2, TP_5V1, TP_3V1, TP_GND1) — 8 components
- [x] Interactive annotation session: annotate MCU block (U2 + 14 test points), I2C mux block (U4, R6, R28, R29, C9, C10), and sensor connectors (J4, J5, J6) — 23 components
- [x] Re-extract to capture annotations — 31/37 components annotated (84%), remaining 6 are LED controller block (Phase 3b)
- [x] Commit, update TASKS.md, generate handoff prompt for next session. Note any unexpected issues or implementation decisions.

## Phase 3b: Annotation Pass — Remaining Blocks & Nets

- [ ] Interactive annotation session: annotate LED controller block (IC1 level shifter, F1 fuse, R27 sense resistor, C7, C8 caps, J3 LED strip connector) — 6 remaining components
- [ ] Add net annotations to `circuit-context.json` — type, protocol, direction, description for all non-trivial nets
- [ ] Define functional blocks in `circuit-context.json` with descriptions, component membership, and design intent notes
- [ ] Commit, update TASKS.md, generate handoff prompt for next session. Note any unexpected issues or implementation decisions.

## Phase 3c: Verification

- [ ] Final re-extraction to produce the complete, annotated `circuit-context.json`
- [ ] Run verification quiz: open a fresh session with only `circuit-context.json` and `hardware/CONTEXT.md`, ask the test questions defined in Phase 3a, compare answers against known-correct answers
- [ ] If gaps are found, identify what's missing from the context file, add the missing information, and re-run failed questions
- [ ] Commit, update TASKS.md, generate handoff prompt for next session. Note any unexpected issues or implementation decisions.

## Phase 4: Documentation & Cleanup

- [ ] Update `hardware/CONTEXT.md` — replace annotated netlist references with circuit-context.json guidance, remove YAML annotation workflow, add instructions for AI sessions to use the context file
- [ ] Update `.context/PROJECT.md` — mention schematic context system under hardware section
- [ ] Remove or mark as deprecated: existing netlist JSON files and annotation YAML files that are superseded
- [ ] Add a brief README in `tools/schematic-context/` documenting script usage for future sessions
- [ ] Commit, update TASKS.md, generate handoff prompt (or mark initiative complete).

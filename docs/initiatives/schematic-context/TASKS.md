# Schematic Context System — Tasks

## Phase 1a: Extraction Pipeline — XML Parsing

- [x] Create `tools/schematic-context/` directory and `requirements.txt` (kiutils, pyyaml)
- [x] Write `extract.py` — kicad-cli invocation: call kicad-cli to export XML netlist from a given root `.kicad_sch`, handle path resolution and error cases
- [x] Write `extract.py` — XML netlist parsing: parse the exported XML into component, pin, and net data structures (ref, value, footprint, LCSC part, pin names, pin types, net assignments, sheet paths)
- [x] Write `extract.py` — basic context file output: produce a `circuit-context.json` with components, pins, and nets from the XML data alone (no kiutils yet, no annotations, no blocks)
- [x] Test on main PCB: run extraction, verify all components and nets from all sheets appear correctly in the output
- [x] Commit, update TASKS.md, generate handoff prompt for next session. Note any unexpected issues or implementation decisions.

## Phase 1b: Extraction Pipeline — kiutils Integration & Merge

- [ ] Add kiutils integration to `extract.py`: read each `.kicad_sch` file (root + children discovered via kiutils `sch.sheets`), extract all component properties including `ai_` prefixed custom properties
- [ ] Add sheet hierarchy to `extract.py`: build `sheet_interfaces` section from hierarchical sheet pins (name, direction) and match to hierarchical labels in child schematics
- [ ] Add previous-context merge to `extract.py`: if a previous `circuit-context.json` exists, carry forward net annotations and block definitions, flag new/removed items
- [ ] End-to-end test: run full extraction on main PCB, verify kiutils properties and sheet interfaces appear correctly alongside XML-derived connectivity
- [ ] Commit, update TASKS.md, generate handoff prompt for next session. Note any unexpected issues or implementation decisions.

## Phase 2: Annotation Tooling

- [ ] Write `annotate.py` — accepts component ref + key=value pairs, writes `ai_` properties to the correct `.kicad_sch` file via kiutils (must resolve which sheet a component lives on)
- [ ] Write `show.py` — reads current schematic state via kiutils, displays components grouped by annotation status (annotated vs unannotated), useful for guiding annotation sessions
- [ ] Test annotation round-trip: write a property via `annotate.py`, re-extract via `extract.py`, confirm property appears in `circuit-context.json`
- [ ] Commit, update TASKS.md, generate handoff prompt for next session. Note any unexpected issues or implementation decisions.

## Phase 3a: Annotation Pass — Setup & First Blocks

- [ ] Define 5-10 test questions about the main PCB schematic that an AI should be able to answer from the context file alone (include questions that have previously gotten poor answers)
- [ ] Run initial extraction on main PCB to produce baseline `circuit-context.json`
- [ ] Interactive annotation session: annotate power subsystem components (DWEII module, voltage regulation, decoupling caps) — `ai_function`, `ai_block`, `ai_critical_specs`
- [ ] Interactive annotation session: annotate MCU block (T-Display-S3, GPIO assignments) and I2C mux block (TCA9548A, pull-ups)
- [ ] Re-extract to capture annotations written so far
- [ ] Commit, update TASKS.md, generate handoff prompt for next session. Note any unexpected issues or implementation decisions.

## Phase 3b: Annotation Pass — Remaining Blocks & Nets

- [ ] Interactive annotation session: annotate LED controller block (SN74AHCT125 level shifter, fuse, connectors)
- [ ] Interactive annotation session: annotate sensor connector block (JST-SH connectors, test points, remaining passives)
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

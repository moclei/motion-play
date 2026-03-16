# PCB Routing Verification — Tasks

## Phase 1: Foundations

- [ ] Regenerate `pcb-layout-context.json` from current `.kicad_pcb` (positions are stale)
- [ ] Scaffold `tools/verify-routing.py` — argument parsing, kiutils board loading, net map construction
- [ ] Build absolute pad position calculator (footprint origin + pad offset + rotation)
- [ ] Build per-net primitive collector (group segments, vias, zone polygons, and pads by net ID)

## Phase 2: Core Checks

- [ ] Trace width checks — verify all segments match expected net class widths
- [ ] Zone existence checks — confirm BOOST_SW, +5V, GND, 3.3V zones on correct layers
- [ ] Critical path connectivity — build per-net graph and verify pad-to-pad reachability for all power paths
- [ ] BOOST_SW zone coverage — verify U6 SW pins and L2 pad 1 fall within BOOST_SW filled polygon

## Phase 3: Signal Integrity Checks

- [ ] I2C length matching — sum segment lengths per SDA/SCL pair, flag mismatches >5mm
- [ ] I2C isolation — define exclusion zones around L1, L2, U6 SW, U5 SW; check no I2C trace enters them
- [ ] INA219 Kelvin sense — verify R44↔U7 sense traces are 0.25mm and independent from power path
- [ ] FB/COMP routing side — verify BOOST_FB and BOOST_COMP traces stay on U6's left (low-x) side

## Phase 4: Report and Validation

- [ ] Generate Markdown report with summary table and per-check details
- [ ] Generate JSON sidecar with raw measurements
- [ ] Run script end-to-end on the current board, review results
- [ ] Fix any real issues found, iterate if needed

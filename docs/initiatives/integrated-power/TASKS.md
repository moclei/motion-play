# Integrated Power Management — Tasks

## Phase 1: Component Selection, Datasheet Review + Validation ✅

- [x] Search LCSC for boost converter candidates (8-10A switch class, SOT/QFN preferred)
- [x] Evaluate candidates: output current, package size, LCSC stock/pricing, basic vs extended part, thermal resistance
- [x] Select boost converter and source datasheet — extract text-only reference to `docs/references/tps61088/DATASHEET_REFERENCE.md`
- [x] Source BQ24195 datasheet — verify ILIM resistor-to-current mapping, battery-absent VSYS behavior, power-on sequence, I2C register defaults. Saved to `docs/references/bq24195/DATASHEET_REFERENCE.md`
- [x] Source INA219 datasheet — determine shunt resistor value (10mΩ, PGA /2), confirm I2C address (0x40), verify max bus voltage (26V >> 4.5V). Saved to `docs/references/ina219/DATASHEET_REFERENCE.md`
- [x] Rough board area estimate: ~830mm² power block fits on 85×45mm board (tight). May need 90×50mm.
- [x] Thermal validation: TPS61088 ~1.5W + BQ24195 ~1-2W = ~3W typical. RθJA 29.7°C/W → Tj ~85°C at 40°C ambient. OK.
- [x] Confirm all passive values: ILIM changed to **330Ω** (from 2.7kΩ), feedback divider 180kΩ/56kΩ, inductor 2.2µH/10A Isat, shunt 10mΩ. Full BOM in `COMPONENT_SELECTION.md`.
- [x] Allocate GPIO for BQ24195 INT → **GPIO 21** (preserves GPIO 1-3 and 17-18 for future)
- [x] Validate battery-absent operation: BQ24195 confirms instant-on support. VSYS ~3.65V from VBUS. Viable with revised ILIM/OTG settings.
- [x] **CRITICAL FINDING:** Reference design 2.7kΩ ILIM gives only 100mA boot current — changed to 330Ω + OTG HIGH. See `COMPONENT_SELECTION.md`.

## Phase 2: Schematic Change Specification ✅

Full specification in `SCHEMATIC_SPEC.md` (51 components, 30+ nets, 4 functional blocks).

- [x] Root sheet changes: remove DWEII (J2), Schottky (D1); add Power Management hierarchical sheet with 6 interface pins (+5V, GND, +3.3V, I2C_SDA, I2C_SCL, CHRG_INT)
- [x] USB-C input block: J7 (TYPE-C-31-M-12), F2 (3A fuse), R30/R31 (5.1kΩ CC pull-downs), C20-C22 (decoupling)
- [x] Battery management block: U5 (BQ24195RGER), Q2 (PMOS), L1 (2.2µH), J8 (JST PH), TH1 (NTC), R32 (330Ω ILIM), R35 (OTG pull-up), R36/R37 (NTC biasing from REGN), all support caps
- [x] Boost converter block: U6 (TPS61088RHLR), L2 (2.2µH/10A), R39/R40 (180kΩ/56kΩ FB divider → 5.07V), R43/C38/C39 (22kΩ/4.7nF/100pF compensation from EVM scaling), C34-C36 (3×22µF output)
- [x] Power monitoring block: U7 (INA219AIDCNR), R44 (10mΩ 2512 shunt on VSYS), C40 (VS bypass)
- [x] Signal routing: BQ24195 I2C (0x6B) + INT→GPIO21 via R38 pull-up, INA219 I2C (0x40), 4 test points (VSYS, VBAT, PVBUS, PGND)
- [x] Consistency review: net names verified, no I2C address conflicts (0x40/0x6B/0x70), all pin assignments cross-checked against datasheets

**Phase 2 design decisions resolved:**
- CE pin: tied LOW (GND) — charging controlled via I2C
- NTC biasing: REGN → 5.6kΩ → TS → (10kΩ NTC ‖ 30kΩ) → GND
- Compensation network: 22kΩ / 4.7nF / 100pF (from TPS61088 EVM scaling, bench-tunable)
- PMID capacitance: 2× 10µF (20µF, meeting datasheet minimum)

## Phase 3: Scripted Schematic Generation

- [x] Proof-of-concept: generate a minimal `.kicad_sch` via kiutils, verify KiCad 9 opens it without errors. **Validated:** 2 resistors + net labels, zero ERC errors. Key learnings: wire stubs needed for label-pin connectivity, Y-negation transform correct, lib symbols extractable from existing schematics. Script: `tools/schematic-gen/poc_generate.py`
- [x] Convert `SCHEMATIC_SPEC.md` to `spec.json` — structured JSON with component definitions (ref, value, footprint, LCSC, symbol), pin-to-net mappings, and block layout positions. **Validated:** 51 components, 31 nets, 154 pin-to-net mappings, all cross-verified. Script: `tools/schematic-gen/spec.json`
- [x] Collect symbol definitions: extract from existing project schematics (BQ24195, passives, connectors), install TPS61088 and INA219 symbols via JLCPCB MCP `library_install`. Installed via `easyeda2kicad` into `hardware/pcb-main/resources/`, registered in `sym-lib-table` and `fp-lib-table`
- [x] Build `generate_power_sheet.py` — reads `spec.json`, places components in a grid by block, attaches net labels to pins, adds hierarchical sheet labels for interface signals. Key fixes during development: `lib_id` format must be `LibName:SymName` for KiCad 9, wire stubs must extend *away* from component body (pin angle + 180°), components need ≥15.24mm vertical spacing to avoid stub collisions
- [x] Generate `power_management.kicad_sch`, open in KiCad, run ERC, iterate on script until clean. Result: 51 components, 163 wire stubs + net labels, 8 no-connect flags, 6 hierarchical labels. Also hid `ai_*` and `Footprint` property labels across all existing schematic sheets for visual clarity
- [x] User: manually edit root sheet in KiCad (delete J2/D1, add hierarchical sheet reference, wire GPIO 21 to CHRG_INT). Deleted J2 (DWEII module) and D1 (Schottky), added hierarchical sheet reference, wired all 6 interface pins (+5V, GND, +3.3V, I2C_SDA, I2C_SCL, CHRG_INT), connected CHRG_INT to GPIO 21
- [x] Run full ERC on complete design (root + power management sheet), fix any remaining issues — Added 4 PWR_FLAG symbols (#FLG05–#FLG08) to resolve `power_pin_not_driven` errors on VBUS_RAW, Protected_VBUS, VBAT, and VSYS nets. Regenerated schematic: 55 components, 167 wire stubs + net labels, 14 unique lib symbols. Remaining: ~27 `pin_to_pin` type mismatch warnings from easyeda2kicad-generated symbols (cosmetic, fixable by editing `.kicad_sym` pin types but low priority)

## Phase 4: KiCad Review + Annotation ✅

- [x] User re-extracts `circuit-context.json` via `extract.py --previous` — 86 components, 50 nets, 4 sheets. 51 new power management components detected, D1/J2 correctly removed.
- [x] AI reviews extracted context against schematic spec — pin-by-pin verification of all 3 ICs (U5/U6/U7), all passives, all net connections. Zero discrepancies found. All 51 physical components + 4 PWR_FLAGs match spec.json and SCHEMATIC_SPEC.md.
- [x] Annotation session for new components — batch Python script wrote ai_function, ai_block, ai_role, ai_critical_specs for all 51 new components + updated TPIO21. 86/86 components annotated (100% coverage). Added 6 new block definitions (usb_c_input, battery_mgmt, boost_5v, power_monitor, power_test_points + updated power block). Annotated all 26 new nets. Updated stale descriptions (+5V net, power block, MCU block notes).

## Phase 5: Layout and Ordering

- [ ] PCB layout: boost converter + inductor + diode placed close together, thermal copper pours under BQ24195 and boost IC
- [ ] Power path trace widths sized for 3A+ (minimum 1mm for main 5V traces, wider preferred)
- [ ] Generate BOM, verify all parts available on LCSC
- [ ] Review JLCPCB assembly capability for selected components (package types, extended vs basic)
- [ ] Order PCB + assembly from JLCPCB

## Phase 6: Build and Test

- [ ] Bench test power path: USB → Protected_VBUS → BQ24195 → VSYS → boost → +5V → AP2112K → +3.3V
- [ ] Verify all rail voltages with multimeter on test points
- [ ] Battery charging test with Samsung 30Q (verify charge current, temperature monitoring, charge termination)
- [ ] Battery-absent operation test (USB only, verify VSYS and +5V stability under load)
- [ ] Load test at power budget levels (apply 2A+ resistive load on +5V, verify stability and thermal)
- [ ] INA219 readout test (verify voltage and current readings match multimeter)
- [ ] BQ24195 I2C test (read status registers, configure input current limit)
- [ ] Full integration test: sensor acquisition + LED patterns + WiFi on battery power
- [ ] Document results and update hardware/CONTEXT.md with integrated power design details

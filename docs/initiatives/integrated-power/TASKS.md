# Integrated Power Management — Tasks

## Phase 1: Component Selection, Datasheet Review + Validation

- [ ] Search LCSC for boost converter candidates (8-10A switch class, SOT/QFN preferred)
- [ ] Evaluate candidates: output current, package size, LCSC stock/pricing, basic vs extended part, thermal resistance
- [ ] Select boost converter and source datasheet — extract text-only reference to `docs/references/<part>/`
- [ ] Source BQ24195 datasheet — verify ILIM resistor-to-current mapping, battery-absent VSYS behavior, power-on sequence, I2C register defaults. Save to `docs/references/bq24195/`
- [ ] Source INA219 datasheet — determine shunt resistor value for VSYS current range (~0.5-6A), confirm I2C address config, verify max bus voltage. Save to `docs/references/ina219/`
- [ ] Rough board area estimate: sum component footprints for new power block, compare to available PCB area
- [ ] Thermal validation: check boost converter + BQ24195 dissipation (~4-5W) against thermal resistance specs and available copper pour
- [ ] Confirm all passive values: ILIM resistor, boost feedback divider, capacitors, inductors
- [ ] Allocate GPIO for BQ24195 INT (from unused: 1, 2, 3, 17, 18, 21)
- [ ] Validate battery-absent operation scenario against BQ24195 datasheet

## Phase 2: Schematic Change Specification

- [ ] Produce change spec for main PCB root sheet: remove DWEII (J2), remove Schottky (D1), add new hierarchical sheet pin connections
- [ ] Produce change spec for new power management hierarchical sheet: USB-C input block (connector, fuse, CC pull-downs, decoupling)
- [ ] Produce change spec for battery management block (BQ24195, PMOS, NTC, inductor, all support passives)
- [ ] Produce change spec for boost converter block (selected IC, feedback divider, inductor, Schottky diode, capacitors)
- [ ] Produce change spec for power monitoring block (INA219, shunt resistor)
- [ ] Produce change spec for signal routing: BQ24195 I2C + INT GPIO, INA219 I2C, test points
- [ ] Review complete spec for consistency — net names, pin assignments, address conflicts

## Phase 3: KiCad Implementation + Review

- [ ] User creates new hierarchical sheet for power management in KiCad
- [ ] User implements schematic per change spec
- [ ] User runs ERC (Electrical Rules Check)
- [ ] User re-extracts `circuit-context.json` via `extract.py --previous`
- [ ] AI reviews extracted context against change spec — verify all connections, flag discrepancies
- [ ] Annotation session for new components (ai_function, ai_block, ai_role, ai_critical_specs)

## Phase 4: Layout and Ordering

- [ ] PCB layout: boost converter + inductor + diode placed close together, thermal copper pours under BQ24195 and boost IC
- [ ] Power path trace widths sized for 3A+ (minimum 1mm for main 5V traces, wider preferred)
- [ ] Generate BOM, verify all parts available on LCSC
- [ ] Review JLCPCB assembly capability for selected components (package types, extended vs basic)
- [ ] Order PCB + assembly from JLCPCB

## Phase 5: Build and Test

- [ ] Bench test power path: USB → Protected_VBUS → BQ24195 → VSYS → boost → +5V → AP2112K → +3.3V
- [ ] Verify all rail voltages with multimeter on test points
- [ ] Battery charging test with Samsung 30Q (verify charge current, temperature monitoring, charge termination)
- [ ] Battery-absent operation test (USB only, verify VSYS and +5V stability under load)
- [ ] Load test at power budget levels (apply 2A+ resistive load on +5V, verify stability and thermal)
- [ ] INA219 readout test (verify voltage and current readings match multimeter)
- [ ] BQ24195 I2C test (read status registers, configure input current limit)
- [ ] Full integration test: sensor acquisition + LED patterns + WiFi on battery power
- [ ] Document results and update hardware/CONTEXT.md with integrated power design details

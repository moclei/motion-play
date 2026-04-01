# Dual-Bus I2C — Tasks

## Phase 1: Preparation & Part Selection
- [ ] Confirm GPIO11/GPIO12 for I2C1 — review against ESP32-S3 datasheet for any restrictions
- [ ] Find LCSC part number for 4-pin JST-SH connector (SM04B-SRSS-TB or equivalent horizontal SMD)
- [ ] Verify JLCPCB assembly availability for the 4-pin connector
- [ ] Confirm 2.2kΩ 0603 resistor (C114662) is available — same as R28/R29
- [ ] Confirm KiCad footprint exists for 4-pin JST-SH (`JST_SH_SM04B-SRSS-TB_1x04-1MP_P1.00mm_Horizontal`)
- [ ] Decide: keep GPIO10/GPIO13 as spare breakout pads or leave unconnected

## Phase 2: Schematic Changes
- [ ] Remove TCA9548A subsystem sheet contents (U4, C9, C10, R6) or delete the sheet entirely
- [ ] Move R28/R29 (I2C0 pull-ups) to root sheet — connect to `/I2C_SDA`, `/I2C_SCL`, +3.3V
- [ ] Change J4 to 4-pin: update symbol, connect pins to +3.3V, GND, `/I2C_SDA`, `/I2C_SCL`
- [ ] Change J5 to 4-pin: update symbol, connect pins to +3.3V, GND, `/I2C_SDA`, `/I2C_SCL`
- [ ] Create new global labels `/I2C1_SDA` and `/I2C1_SCL`
- [ ] Add R60 (2.2kΩ) from `/I2C1_SDA` to +3.3V
- [ ] Add R61 (2.2kΩ) from `/I2C1_SCL` to +3.3V
- [ ] Change J6 to 4-pin: update symbol, connect pins to +3.3V, GND, `/I2C1_SDA`, `/I2C1_SCL`
- [ ] On ESP32 sheet: change U3 pin 19 (IO11) net to `/I2C1_SDA`
- [ ] On ESP32 sheet: change U3 pin 20 (IO12) net to `/I2C1_SCL`
- [ ] On ESP32 sheet: disconnect U3 pin 21 (IO13) and pin 18 (IO10) from old nets
- [ ] Update ESP32 sub-sheet hierarchical pins: remove `TCA_RESET`, `INT1-3`; add `I2C1_SDA`, `I2C1_SCL`
- [ ] Update root sheet hierarchical pin connections to match
- [ ] Remove TPIO10 test point (was TCA_RESET)
- [ ] Add test points for I2C1: TPIO11 (`/I2C1_SDA`) and TPIO12 (`/I2C1_SCL`)

## Phase 3: Schematic Verification
- [ ] Run ERC in KiCad — resolve all new errors/warnings
- [ ] Re-extract circuit-context.json (`python3 tools/schematic-context/extract.py ...`)
- [ ] Review circuit-context.json: confirm TCA components gone, new nets present, connector pins correct
- [ ] Annotate any new components in circuit-context.json (R60, R61, new test points)

## Phase 4: PCB Layout
- [ ] Update PCB from Schematic (F8) — accept component additions/removals
- [ ] Delete TCA9548A footprint (U4) and associated passives (C9, C10, R6) from board
- [ ] Delete TPIO10 test point footprint
- [ ] Swap J4, J5, J6 footprints to 4-pin JST-SH
- [ ] Place R60/R61 near J6 (or near U3 — decide based on board space)
- [ ] Place TPIO11, TPIO12 test points near I2C1 traces
- [ ] Route I2C0: ESP32 pads → R28/R29 → fork to J4 and J5
- [ ] Route I2C1: ESP32 pins 19/20 → R60/R61 → J6
- [ ] Verify ground pour continuity under I2C traces
- [ ] Check clearances around removed TCA area — consider tightening board or using freed space

## Phase 5: PCB Verification
- [ ] Run DRC in KiCad — resolve all errors
- [ ] Re-extract pcb-layout-context.json
- [ ] Review pcb-layout-context.json: confirm component placement and net connectivity
- [ ] Visual inspection of 3D view for connector/component conflicts

## Phase 6: Production Files
- [ ] Export production files via JLCPCB Fabrication Toolkit
- [ ] Review BOM: confirm TCA + passives removed, new pull-ups and connectors present, all LCSC parts valid
- [ ] Review CPL (positions): confirm new component placements are correct
- [ ] Verify designators.csv has no orphaned references
- [ ] Final sanity check: component count, net count, board dimensions

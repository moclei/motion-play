# ESP32-S3 Direct Integration — Tasks

## Phase 1: Schematic Design

- [ ] Create git branch for ESP32 integration work
- [ ] Verify WROOM-1-N16R8 LCSC part number and JLCPCB assembly stock
- [ ] Find or create KiCad symbol and footprint for ESP32-S3-WROOM-1 (check official KiCad library, Espressif GitHub, or LCSC/EasyEDA import)
- [ ] Find or create KiCad symbol and footprint for AMS1117-3.3 (SOT-223)
- [ ] Create new schematic sheet for ESP32-S3 module and support circuitry (EN/reset, boot, auto-download, decoupling)
- [ ] Add USB D+/D- routing from J7 to ESP32 sheet (modify power_management.kicad_sch or root sheet)
- [ ] Replace U1 AP2112K with AMS1117-3.3 — update symbol, footprint, decoupling caps per datasheet
- [ ] Find or create KiCad symbol and footprint for power slide switch (SPDT, >= 3A rated, LCSC stocked)
- [ ] Add power switch to schematic in VSYS path between BQ24195 output and downstream regulators
- [ ] Remove U2 (T-Display-S3) symbol, footprint, and unused nets/test points (TPIO1, TPIO2, TPIO3, TPIO17, TPIO18)
- [ ] Remove +5V connection to old U2 pin 12 — WROOM-1 takes 3.3V from LDO
- [ ] Run ERC — resolve any new errors
- [ ] Update circuit-context.json via extract.py + annotate new components
- [ ] Peer review schematic against Espressif Hardware Design Guidelines checklist

## Phase 2: PCB Layout

- [ ] Place WROOM-1 module at board edge with antenna keepout zone
- [ ] Place AMS1117-3.3 with thermal copper pour
- [ ] Place power slide switch at board edge (accessible from enclosure)
- [ ] Place boot/reset buttons in accessible location
- [ ] Place auto-download transistors and USB series resistors near module
- [ ] Route all new connections
- [ ] Rework freed board area (clean up removed traces/vias from old U2)
- [ ] Evaluate board outline — shrink or keep current dimensions
- [ ] Run DRC — resolve violations
- [ ] Generate JLCPCB production files (BOM, CPL, gerbers) via Fabrication Toolkit
- [ ] Preflight manufacturing review (stock check, BOM validation, CPL cross-reference)

## Phase 3: Firmware Adaptation

- [ ] Update `platformio.ini` board definition and build flags (USB CDC, remove TFT_eSPI)
- [ ] Remove `firmware/include/User_Setup.h`
- [ ] Stub out or remove `DisplayManager` and update all call sites in `main.cpp`
- [ ] Clean up `pin_config.h` — remove display pin definitions
- [ ] Verify build compiles cleanly
- [ ] Test on v6 hardware with firmware changes (display calls become no-ops) before new boards arrive

## Phase 4: Fabrication and Validation

- [ ] Confirm v6 board validation is complete (gate for ordering)
- [ ] Order new revision from JLCPCB
- [ ] Bring-up: power rails, USB enumeration, serial output
- [ ] Validate I2C bus — all devices respond (TCA9548A, BQ24195, INA219)
- [ ] Validate sensor performance — compare 1000Hz polling against v6 baseline
- [ ] Validate WiFi + MQTT connectivity
- [ ] Validate LED strip operation
- [ ] Run a full field test session (debug mode data collection + upload)

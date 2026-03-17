# ESP32-S3 Direct Integration — Tasks

## Phase 1: Schematic Design

### 1a. Part Verification and Library Setup

- [x] Create git branch — `esp32-integration-schematic` from main
- [x] Verify WROOM-1-N16R8 LCSC part — **C2913202**, 31k stock, $5.71, extended
- [x] Verify AMS1117-3.3 LCSC part — **C6186** (Advanced Monolithic Systems), 1M+ stock, $0.22, **basic** part
- [x] Install KiCad symbol + footprint for WROOM-1 via JLC-MCP — `JLC-MCP-MCUs:ESP32-S3-WROOM-1_N16R8_`
- [x] Install KiCad symbol + footprint for AMS1117-3.3 via JLC-MCP — `JLC-MCP-Power:AMS1117-3_3`
- [ ] Verify AMS1117 capacitor LCSC parts — 22µF ceramic (input), 22µF tantalum (output, required for AMS1117 stability)
- [ ] Find or create KiCad symbol and footprint for power slide switch (SPDT, >= 3A rated, LCSC stocked)
- [ ] Find or create KiCad symbol and footprint for MMBT3904 NPN (auto-download circuit)
- [ ] Find or create KiCad symbol and footprint for tactile switches (boot + reset buttons)

### 1b. Tooling — `tools/schematic-modify/`

New toolkit for programmatic modification of existing KiCad schematics via kiutils. Separate from `schematic-gen` (creates new sheets) and `schematic-context` (reads/annotates existing).

- [ ] Create `tools/schematic-modify/CONTEXT.md` — purpose, usage, relationship to schematic-gen and schematic-context
- [ ] Create `tools/schematic-modify/modify.py` — core helpers: `add_component()`, `remove_component()`, `add_hierarchical_label()`, `add_sheet_reference()`, etc.
  - Components placed at specified offset (off to one side, user arranges in KiCad)
  - Net labels on wire stubs at every connected pin
  - Footprint, LCSC part, and all standard properties set
  - `ai_*` annotation handled by calling `tools/schematic-context/annotate.py` after placement (annotation logic lives in one place)
- [ ] Create `tools/schematic-modify/esp32_integration.py` — this initiative's specific modifications (uses modify.py helpers)

### 1c. New ESP32-S3 Schematic Sheet

Generate `hardware/pcb-main/kicad/esp32_s3.kicad_sch` using the `tools/schematic-gen/` spec.json + generator approach.

- [ ] Create `tools/schematic-gen/esp32_spec.json` — all components, positions, pin-to-net maps, hierarchical labels
- [ ] Create `tools/schematic-gen/generate_esp32_sheet.py` (or extend existing generator)
- [ ] Generate `esp32_s3.kicad_sch` and verify in KiCad
- [ ] Annotate new components via `annotate.py`

Components on this sheet: WROOM-1 module (U3), EN/reset circuit (10k pull-up + 1µF cap + tactile switch), boot circuit (10k pull-up + tactile switch), auto-download (2x MMBT3904 + 2x 10k), USB series resistors (2x 22Ω on D-/D+), decoupling (10µF bulk + 3x 100nF + 1µF).

Hierarchical labels: `I2C_SDA`, `I2C_SCL`, `TCA_RESET`, `INT1`, `INT2`, `INT3`, `LED_DATA`, `CHRG_INT`, `USB_DP`, `USB_DN`, `+3.3V`, `GND`.

### 1d. Modify Existing Schematics

Use `tools/schematic-modify/` to place new components on existing sheets (off to one side). User manually positions and wires in KiCad.

**Root sheet (`motion-play-main.kicad_sch`):**
- [ ] Add hierarchical sheet reference to `esp32_s3.kicad_sch` with all interface pins
- [ ] Remove U2 (T-Display-S3) symbol instance
- [ ] Remove unused test points (TPIO1, TPIO2, TPIO3, TPIO17, TPIO18)
- [ ] Remove U1 (AP2112K) and associated caps C1, C2 — LDO moves to power_management sheet
- [ ] Reconnect signal wires from old U2 to new ESP32 sheet pins (manual in KiCad)

**Power management sheet (`power_management.kicad_sch`):**
- [ ] Add AMS1117-3.3 with caps (22µF ceramic input, 22µF tantalum output) — replaces U1, now lives with other power components
- [ ] Change `+3.3V` hierarchical pin from input to output (power_management now produces +3.3V)
- [ ] Add USB D+/D- net labels on J7's data pads (currently no-connected)
- [ ] Add hierarchical labels `USB_DP`, `USB_DN` for routing to ESP32 sheet
- [ ] Add power slide switch in VSYS path between BQ24195 output and downstream regulators
- [ ] Annotate all new components via `annotate.py`

### 1e. Verification

- [ ] Run ERC — resolve any new errors
- [ ] Update circuit-context.json via `extract.py --previous`
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

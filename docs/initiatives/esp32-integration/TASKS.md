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
- [ ] Find or create KiCad symbol and footprint for tactile switches (boot + reset buttons)
- [ ] Find or create KiCad symbol and footprint for USBLC6-2SC6 (USB ESD protection, LCSC C7519)
- [ ] Select status LED — WS2812B-mini (addressable, shares GPIO16) or simple LED + resistor (dedicated GPIO). Find LCSC part.

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

Components on this sheet: WROOM-1 module (U3), EN/reset circuit (10k pull-up + 1µF cap + tactile switch), boot circuit (10k pull-up + tactile switch), USB series resistors (2x 22Ω on D-/D+), decoupling (10µF bulk + 3x 100nF + 1µF), status LED.

Hierarchical labels: `I2C_SDA`, `I2C_SCL`, `TCA_RESET`, `INT1`, `INT2`, `INT3`, `LED_DATA`, `CHRG_INT`, `USB_DP`, `USB_DN`, `+3.3V`, `GND`.

GPIO breakout header: unpopulated 2x5 0.1" pitch pads on root or ESP32 sheet. Suggested pins: GPIO5-9, GPIO14, GPIO15, +3.3V, GND ×2. Avoid strapping pins (GPIO3, GPIO46).

### 1d. Modify Existing Schematics

Use `tools/schematic-modify/` to place new components on existing sheets (off to one side). User manually positions and wires in KiCad.

**Root sheet (`motion-play-main.kicad_sch`):**
- [ ] Add hierarchical sheet reference to `esp32_s3.kicad_sch` with all interface pins
- [ ] Remove U2 (T-Display-S3) symbol instance
- [ ] Remove unused test points (TPIO1, TPIO2, TPIO3, TPIO17, TPIO18)
- [ ] Remove U1 (AP2112K) and associated caps C1, C2 — LDO moves to power_management sheet
- [ ] Reconnect signal wires from old U2 to new ESP32 sheet pins (manual in KiCad)

**Power management sheet (`power_management.kicad_sch`):**
- [ ] Add AMS1117-3.3 with caps (22µF ceramic input, 22µF tantalum output) — VIN from `+5V` (boost output), not VSYS
- [ ] Change `+3.3V` hierarchical pin from input to output (power_management now produces +3.3V)
- [ ] Add USB D+/D- net labels on J7's data pads — tie A-side and B-side D+/D- together for orientation independence
- [ ] Add USBLC6-2SC6 ESD protection between J7 D+/D- pads and series resistors
- [ ] Add hierarchical labels `USB_DP`, `USB_DN` for routing to ESP32 sheet
- [ ] Add power slide switch in VSYS path between BQ24195 output and TPS61088 boost input
- [ ] Annotate all new components via `annotate.py`

### 1e. Verification

- [ ] Verify strapping pins (GPIO3, GPIO46) are not inadvertently driven by main PCB nets or breakout header
- [ ] Run ERC — resolve any new errors
- [ ] Update circuit-context.json via `extract.py --previous`
- [ ] Peer review schematic against Espressif Hardware Design Guidelines checklist

## Phase 2: PCB Layout

- [ ] Place WROOM-1 module at board edge with antenna keepout zone
- [ ] Place AMS1117-3.3 with thermal copper pour
- [ ] Place power slide switch at board edge (accessible from enclosure)
- [ ] Place boot/reset buttons in accessible location
- [ ] Place USBLC6-2SC6 close to J7, USB series resistors near module
- [ ] Place status LED in visible location
- [ ] Place GPIO breakout header pads (unpopulated)
- [ ] Route USB D+/D- with 90 ohm differential impedance
- [ ] Route all other new connections
- [ ] Rework freed board area (clean up removed traces/vias from old U2)
- [ ] Evaluate board outline — shrink or keep current dimensions
- [ ] Run DRC — resolve violations
- [ ] Generate JLCPCB production files (BOM, CPL, gerbers) via Fabrication Toolkit
- [ ] Preflight manufacturing review (stock check, BOM validation, CPL cross-reference)

## Phase 3: Firmware Adaptation

- [ ] Update `platformio.ini` board definition and build flags (USB CDC, remove TFT_eSPI)
- [ ] Verify `board_build.arduino.memory_type = qio_opi` is preserved or explicitly set for octal PSRAM
- [ ] Verify `board_build.partitions = default_16MB.csv` still applies with the new board definition
- [ ] Remove `firmware/include/User_Setup.h`
- [ ] Stub out or remove `DisplayManager` and update all call sites in `main.cpp`
- [ ] Clean up `pin_config.h` — remove `PIN_LCD_*`, `PIN_POWER_ON`, `PIN_TOUCH_*`. Rename `PIN_TOUCH_RES` (GPIO21) to `PIN_CHRG_INT`.
- [ ] Verify build compiles cleanly
- [ ] Test on v6 hardware with firmware changes (display calls become no-ops) before new boards arrive

## Phase 4: Fabrication and Validation

- [ ] Confirm v6 board validation is complete (gate for ordering)
- [ ] Order new revision from JLCPCB
- [ ] First flash via boot+reset button sequence (document procedure)
- [ ] Bring-up: power rails, USB enumeration, serial output
- [ ] Flash firmware via USB from the single USB-C port (validate full programming workflow)
- [ ] Validate PSRAM — confirm `ESP.getPsramSize()` returns ~8MB, DataBuffer allocates successfully
- [ ] Validate I2C bus — all devices respond (TCA9548A, BQ24195, INA219)
- [ ] Validate sensor performance — compare 1000Hz polling against v6 baseline (cycle time jitter, missed reads)
- [ ] Validate WiFi + MQTT connectivity
- [ ] Validate LED strip operation
- [ ] Validate status LED functionality
- [ ] Validate power switch — system off kills all rails, BQ24195 still charges battery when off
- [ ] Run a full field test session (debug mode data collection + upload)

# ESP32-S3 Direct Integration — Plan

## Approach

The work is split into four phases: schematic design, PCB layout, firmware adaptation, and fabrication/validation. Phases 1-2 are hardware (KiCad), Phase 3 is firmware (PlatformIO), and Phase 4 is manufacturing and bring-up. Schematic work begins now on a git branch; fabrication is gated on v6 board validation.

The core principle is like-for-like: every signal that currently connects to U2 continues to connect to the WROOM-1 module on the same GPIO numbers. The I2C bus, sensor interrupts, LED data, and charge interrupt are all unchanged. What changes is the physical module, the power path (3.3V LDO upgrade + physical power switch), the USB routing (data lines added to J7), and the removal of the display.

## Technical Notes

### Module: ESP32-S3-WROOM-1-N16R8

- LCSC **C2913202**, installed as `JLC-MCP-MCUs:ESP32-S3-WROOM-1_N16R8_`
- 16MB flash, 8MB octal PSRAM, built-in PCB antenna
- 25.5mm x 18mm, 41 pins (40 edge + 1 ground pad)
- GPIO33-37 consumed by PSRAM bus — none of these are used in our design
- Reflow-solderable, JLCPCB assembly compatible

**Confirmed pin mapping (from installed JLC-MCP symbol):**

| Signal | GPIO | WROOM-1 Pin # | Symbol Pin Name |
|--------|------|---------------|-----------------|
| I2C SDA | 43 | 37 | TXD0 |
| I2C SCL | 44 | 36 | RXD0 |
| TCA_RESET | 10 | 18 | IO10 |
| INT1 | 13 | 21 | IO13 |
| INT2 | 12 | 20 | IO12 |
| INT3 | 11 | 19 | IO11 |
| LED_DATA | 16 | 9 | IO16 |
| CHRG_INT | 21 | 23 | IO21 |
| USB D- | 19 | 13 | IO19 |
| USB D+ | 20 | 14 | IO20 |
| BOOT | 0 | 27 | IO0 |
| EN/Reset | — | 3 | EN |
| 3V3 (power) | — | 2 | 3V3 |
| GND | — | 1, 40, 41 | GND |

### Schematic Changes

**New ESP32 sheet** (replaces U2 on root sheet):
- WROOM-1-N16R8 module with all pin connections
- EN/Reset: 10k pull-up + 1uF cap + tactile switch
- GPIO0/Boot: 10k pull-up + tactile switch
- Decoupling: 10uF bulk + 3x 0.1uF (CPU, RTC, SPI) + 1uF (VDD_SPI)
- USB: 2x 22 ohm series resistors on D-/D+ lines
- Status LED: single WS2812B-mini (or simple LED + resistor) for on-board visual feedback (power, WiFi, errors). Can share GPIO16 (LED_DATA) in series before the level shifter, or use a spare GPIO.
- No auto-download circuit — native USB CDC handles auto-reset (see resolved questions)

**J7 modification** (power_management.kicad_sch):
- Add D+/D- net connections from the TYPE-C-31-M-12 connector pads to the new ESP32 sheet
- J7 has separate D+ and D- pins for both cable orientations (A-side and B-side). For USB 2.0, tie both sides together: A6 and B6 → USB_DP net, A7 and B7 → USB_DN net. This ensures data works regardless of cable orientation.
- Add ESD protection on D+/D-: USBLC6-2SC6 (LCSC C7519, ~$0.10) placed close to J7, between the connector and the series resistors
- BQ24195 D+/D- remain tied to GND (unchanged)

**LDO replacement** (moved to power_management.kicad_sch — all power components in one sheet):
- AP2112K-3.3 (U1, SOT-23-5, 600mA) removed from root sheet → AMS1117-3.3 (SOT-223, 1A) added to power_management
- LCSC **C6186** (Advanced Monolithic Systems, basic part), installed as `JLC-MCP-Power:AMS1117-3_3`
- AMS1117 pin mapping: Pin 1=GND, Pin 2=VOUT, Pin 3=VIN, Pin 4=VOUT (tab/heatsink)
- Input cap: 22µF ceramic (replaces C1 1µF)
- Output cap: 22µF tantalum (replaces C2 2.2µF) — required for AMS1117 stability (narrow ESR window, pure MLCC can cause oscillation)
- The `+3.3V` hierarchical pin on power_management changes from input to output

**Power switch** (power_management.kicad_sch):
- SPDT slide switch rated >= 3A, placed in the VSYS power path between the BQ24195 output (VSYS) and the TPS61088 boost converter input
- Switch off → VSYS disconnected from boost → +5V rail dies → AMS1117 has no input → +3.3V dies → entire system off. No quiescent draw from any regulator or the ESP32.
- **Important:** The AMS1117 VIN is `+5V` (from TPS61088 boost output), not VSYS directly. The AMS1117 cannot regulate 3.3V from VSYS (dropout ~1.1V, VSYS can be as low as 3.0V on depleted battery). The switch kills VSYS→boost→+5V→AMS1117 transitively.
- When off, BQ24195 can still charge the battery from USB (VSYS remains powered from its output side for charging, the switch isolates the load side)
- Part selection: look for a compact through-hole or SMD slide switch (e.g., SS-12D00, MSS22D18, or similar LCSC-stocked, 3A+ rated, SPDT/DPDT)
- Needs to be accessible from outside the enclosure — place at board edge

**GPIO breakout header** (root sheet or ESP32 sheet):
- Unpopulated 2x5 0.1" pitch header pads bringing out spare GPIOs freed by display removal
- Suggested pins: GPIO5, GPIO6, GPIO7, GPIO8, GPIO9, GPIO14, GPIO15, +3.3V, GND (×2)
- Zero BOM cost (pads only, no component populated), minimal board space
- Provides debug and future expansion capability

**Removals:**
- U2 (T-Display-S3) symbol and footprint
- Associated test points that only connected to U2 unused pins (TPIO1, TPIO2, TPIO3, TPIO17, TPIO18)
- Display-related nets (Net-(U2-1), Net-(U2-2), Net-(U2-3), Net-(U2-17), Net-(U2-18))
- The +5V connection to U2 pin 12 (WROOM-1 takes 3.3V from LDO, not 5V)
- Auto-download circuit (2x MMBT3904 + 2x 10k) — not needed with native USB CDC

### PCB Layout Constraints

- WROOM-1 module placed at a board edge with antenna protruding beyond or flush with the edge
- ~10-15mm keepout zone past the antenna end: no copper pour, no components, no ground plane
- Per Espressif guidelines: no high-frequency traces near antenna, ground plane under module body (not under antenna)
- AMS1117 in SOT-223 needs adequate copper pour for thermal dissipation (it's a linear regulator — dissipates ~(5V-3.3V) x Iload as heat)
- Boot/reset buttons should be accessible (board edge or near enclosure opening)

### USB Data Sharing on J7

J7 (TYPE-C-31-M-12) currently uses: VBUS (A4B9, B4A9), CC1 (A5), CC2 (B5), GND, shield. The D+/D- pads exist on the connector but are unconnected. We add:
- D+ (A6 and B6 tied together) → USBLC6-2SC6 ESD protection → 22 ohm series resistor → GPIO20
- D- (A7 and B7 tied together) → USBLC6-2SC6 ESD protection → 22 ohm series resistor → GPIO19
- USB 2.0 D+/D- require 90 ohm differential impedance — controlled-impedance routing during PCB layout

The BQ24195's D+/D- (pins 2, 3) stay tied to GND. It uses these for USB adapter detection (SDP/CDP/DCP), but since we've grounded them it sees a non-standard adapter and relies on ILIM resistor + I2C register configuration for current limits. This behavior is unchanged.

### Programming and First-Flash

With native USB CDC (no UART bridge), the programming workflow is:

- **Normal operation:** esptool communicates over USB CDC and triggers auto-reset into bootloader via the CDC ACM protocol. This works the same as the T-Display-S3 — no auto-download transistors needed.
- **First flash (blank module):** Hold the boot button (GPIO0 low), press and release the reset button, then release boot. This enters the ROM bootloader which exposes a USB CDC interface for esptool. Only needed once per board.
- **Boot and reset buttons are required** and must be accessible on the board edge or through the enclosure.

### Firmware Changes

- `platformio.ini`: board definition from `lilygo-t-display-s3` to `esp32-s3-devkitc-1` (or custom board JSON)
- Remove `TFT_eSPI` from `lib_deps`, delete `firmware/include/User_Setup.h`
- `DisplayManager`: convert to no-op stub (all methods become empty). This preserves the API so call sites in `main.cpp` don't need deletion — they just do nothing. Alternatively, remove all display calls and the class entirely.
- `pin_config.h`: remove all `PIN_LCD_*`, `PIN_POWER_ON`, `PIN_TOUCH_*` definitions. Rename `PIN_TOUCH_RES` (GPIO21) to `PIN_CHRG_INT` — this pin is wired to BQ24195 CHRG_INT on the PCB, not to a touch controller. Active sensor/I2C pins unchanged.
- Build flags: remove `-DUSER_SETUP_LOADED` and `-include firmware/include/User_Setup.h`
- USB CDC configuration: may need explicit build flags for `USB CDC On Boot: Enabled` and `USB Mode: Hardware CDC and JTAG` (the T-Display-S3 board definition sets these automatically)
- Verify `board_build.arduino.memory_type = qio_opi` is preserved or explicitly set — the new board definition may reset the PSRAM memory type. WROOM-1-N16R8 uses octal PSRAM (same as T-Display-S3).
- Verify `board_build.partitions = default_16MB.csv` still applies — WROOM-1-N16R8 has 16MB flash (same as T-Display-S3) but the new board definition may default to a different partition scheme.

### Strapping Pins

The ESP32-S3 has strapping pins sampled at boot. For the WROOM-1 module:

| Pin | Function | Required State | Handling |
|-----|----------|---------------|----------|
| GPIO0 | Boot mode | HIGH = normal, LOW = download | 10k pull-up + boot button (explicit) |
| GPIO46 | SPI boot mode | LOW for SPI flash boot | Internal pull-down (default correct) |
| GPIO3 | JTAG signal source | LOW for internal JTAG | Internal pull-down (default correct) |
| GPIO45 | VDD_SPI voltage | Handled by WROOM-1 module internally | No action needed |

Verify during schematic review that nothing on the main PCB inadvertently drives GPIO3 or GPIO46. If the GPIO breakout header includes these pins, document that they must not be driven during boot.

### Reference Designs

Consult during schematic work:
- [Espressif Hardware Design Guidelines — ESP32-S3 Schematic Checklist](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html)
- [ESP32-S3-DevKitC-1 schematic](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide.html) — canonical auto-download circuit
- [Unexpected Maker ESP32-S3 KiCad designs](https://github.com/UnexpectedMaker/esp32s3) — compact layout reference
- [FrWA14 KiCad 8 WROOM-1 DevBoard](https://github.com/FrWA14/KiCad8_ESP32S3_DevModule_wroom-1_DevelopementBoard) — JLCPCB-oriented

## Tooling Approach

Schematic changes use three complementary tools in `tools/`:

| Tool | Purpose |
|------|---------|
| `schematic-gen/` | Create new sheets from spec.json (used for `esp32_s3.kicad_sch`) |
| `schematic-modify/` | Programmatically append/remove components on existing sheets via kiutils |
| `schematic-context/` | Extract circuit-context.json and annotate components with `ai_*` properties |

**Key principle:** `schematic-modify` places components with correct nets, footprints, and LCSC numbers, but delegates `ai_*` annotation to `schematic-context/annotate.py`. Annotation logic lives in one place.

**Workflow for modifying existing sheets:**
1. `schematic-modify/esp32_integration.py` places new components off to one side of the sheet
2. `schematic-context/annotate.py` adds `ai_*` properties to the new components
3. User opens in KiCad, moves components into position, connects wires
4. `schematic-context/extract.py --previous` produces updated circuit-context.json

## Resolved Questions

- **AMS1117-3.3 output cap:** Tantalum required. 22µF tantalum on output, 22µF ceramic on input. LCSC availability TBD.
- **WROOM-1-N16R8 LCSC:** Confirmed **C2913202**, 31k stock, $5.71, extended part.
- **LDO sheet placement:** Moved from root sheet to `power_management.kicad_sch` — groups all power components together.
- **AMS1117-3.3 VIN source:** Must be `+5V` (from TPS61088 boost output), not VSYS directly. VSYS can drop to 3.0V on depleted battery, which is below AMS1117's 3.3V + 1.1V dropout = 4.4V minimum VIN.
- **Auto-download circuit:** Dropped. The classic 2-transistor DTR/RTS circuit requires a UART bridge chip (CP2102, CH340) to provide DTR/RTS signals. With native USB CDC (GPIO19/20 directly to USB connector), there is no UART bridge — the ESP32-S3 itself is the USB device. The ESP32-S3 ROM and USB CDC stack support auto-reset into bootloader natively (same mechanism the T-Display-S3 uses). First flash on a blank module requires manual boot+reset button sequence. Saves 4 BOM items (2x MMBT3904, 2x 10k).
- **USB ESD protection:** USBLC6-2SC6 (LCSC C7519) added on D+/D- between J7 and series resistors.
- **USB-C D+/D- orientation:** A-side and B-side D+/D- pins tied together at J7. USB 2.0 doesn't use SuperSpeed lanes, so tying orientations is correct.

## Open Questions

- Board outline: keep current dimensions or shrink? Deferred to PCB layout phase.
- Whether to keep TPIO43/TPIO44 (I2C SDA/SCL test points) and TPIO10-13 (TCA_RESET, INT1-3 test points) or consolidate. These connect to active signals and are useful for debugging — likely keep.
- Status LED: use WS2812B-mini (addressable, richer feedback, shares GPIO16) vs. simple LED + resistor (dedicated spare GPIO, simpler). Decide during schematic work.
- GPIO breakout header: exact pin selection and header size (2x4 vs 2x5). Decide during schematic work, avoid strapping pins GPIO3/GPIO46.
- AMS1117 quiescent current (~5-10mA) is not ideal for battery-powered operation. Not a concern for current milestone, but a lower-Iq LDO (e.g., AP7361C-33E, ~55µA Iq, also 1A SOT-223) would be a future drop-in improvement if battery life becomes a priority.

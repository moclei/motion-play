# ESP32-S3 Direct Integration — Plan

## Approach

The work is split into four phases: schematic design, PCB layout, firmware adaptation, and fabrication/validation. Phases 1-2 are hardware (KiCad), Phase 3 is firmware (PlatformIO), and Phase 4 is manufacturing and bring-up. Schematic work begins now on a git branch; fabrication is gated on v6 board validation.

The core principle is like-for-like: every signal that currently connects to U2 continues to connect to the WROOM-1 module on the same GPIO numbers. The I2C bus, sensor interrupts, LED data, and charge interrupt are all unchanged. What changes is the physical module, the power path (3.3V LDO upgrade), the USB routing (data lines added to J7), and the removal of the display.

## Technical Notes

### Module: ESP32-S3-WROOM-1-N16R8

- 16MB flash, 8MB octal PSRAM, built-in PCB antenna
- 25.5mm x 18mm, 41 pins (40 edge + 1 ground pad)
- GPIO33-37 consumed by PSRAM bus — none of these are used in our design
- Reflow-solderable, JLCPCB assembly compatible

### Schematic Changes

**New ESP32 sheet** (replaces U2 on root sheet):
- WROOM-1-N16R8 module with all pin connections
- EN/Reset: 10k pull-up + 1uF cap + tactile switch
- GPIO0/Boot: 10k pull-up + tactile switch
- Auto-download: 2x MMBT3904 NPN + 2x 10k resistors (DTR→GPIO0, RTS→EN)
- Decoupling: 10uF bulk + 3x 0.1uF (CPU, RTC, SPI) + 1uF (VDD_SPI)
- USB: 2x 22 ohm series resistors on D-/D+ lines

**J7 modification** (power_management.kicad_sch):
- Add D+/D- net connections from the TYPE-C-31-M-12 connector pads to the new ESP32 sheet
- BQ24195 D+/D- remain tied to GND (unchanged)

**U1 replacement** (motion-play-main.kicad_sch):
- AP2112K-3.3 (SOT-23-5, 600mA) → AMS1117-3.3 (SOT-223, 1A)
- Different footprint — requires new symbol/footprint and updated land pattern
- Input/output caps may need adjustment per AMS1117 datasheet (typically 22uF tantalum or ceramic on output)

**Removals:**
- U2 (T-Display-S3) symbol and footprint
- Associated test points that only connected to U2 unused pins (TPIO1, TPIO2, TPIO3, TPIO17, TPIO18)
- Display-related nets (Net-(U2-1), Net-(U2-2), Net-(U2-3), Net-(U2-17), Net-(U2-18))
- The +5V connection to U2 pin 12 (WROOM-1 takes 3.3V from LDO, not 5V)

### PCB Layout Constraints

- WROOM-1 module placed at a board edge with antenna protruding beyond or flush with the edge
- ~10-15mm keepout zone past the antenna end: no copper pour, no components, no ground plane
- Per Espressif guidelines: no high-frequency traces near antenna, ground plane under module body (not under antenna)
- AMS1117 in SOT-223 needs adequate copper pour for thermal dissipation (it's a linear regulator — dissipates ~(5V-3.3V) x Iload as heat)
- Boot/reset buttons should be accessible (board edge or near enclosure opening)

### USB Data Sharing on J7

J7 (TYPE-C-31-M-12) currently uses: VBUS (A4B9, B4A9), CC1 (A5), CC2 (B5), GND, shield. The D+/D- pads exist on the connector but are unconnected. We add:
- D+ routed to GPIO20 via 22 ohm series resistor
- D- routed to GPIO19 via 22 ohm series resistor

The BQ24195's D+/D- (pins 2, 3) stay tied to GND. It uses these for USB adapter detection (SDP/CDP/DCP), but since we've grounded them it sees a non-standard adapter and relies on ILIM resistor + I2C register configuration for current limits. This behavior is unchanged.

### Firmware Changes

- `platformio.ini`: board definition from `lilygo-t-display-s3` to `esp32-s3-devkitc-1` (or custom board JSON)
- Remove `TFT_eSPI` from `lib_deps`, delete `firmware/include/User_Setup.h`
- `DisplayManager`: convert to no-op stub (all methods become empty). This preserves the API so call sites in `main.cpp` don't need deletion — they just do nothing. Alternatively, remove all display calls and the class entirely.
- `pin_config.h`: remove all `PIN_LCD_*`, `PIN_POWER_ON`, `PIN_TOUCH_*` definitions. Active pins unchanged.
- Build flags: remove `-DUSER_SETUP_LOADED` and `-include firmware/include/User_Setup.h`
- USB CDC configuration: may need explicit build flags for `USB CDC On Boot: Enabled` and `USB Mode: Hardware CDC and JTAG` (the T-Display-S3 board definition sets these automatically)

### Reference Designs

Consult during schematic work:
- [Espressif Hardware Design Guidelines — ESP32-S3 Schematic Checklist](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html)
- [ESP32-S3-DevKitC-1 schematic](https://docs.espressif.com/projects/esp-dev-kits/en/latest/esp32s3/esp32-s3-devkitc-1/user_guide.html) — canonical auto-download circuit
- [Unexpected Maker ESP32-S3 KiCad designs](https://github.com/UnexpectedMaker/esp32s3) — compact layout reference
- [FrWA14 KiCad 8 WROOM-1 DevBoard](https://github.com/FrWA14/KiCad8_ESP32S3_DevModule_wroom-1_DevelopementBoard) — JLCPCB-oriented

## Open Questions

- AMS1117-3.3 output capacitor requirements — datasheet specifies tantalum on output for stability. Verify if ceramic is acceptable (some AMS1117 variants are ceramic-stable). If tantalum required, confirm JLCPCB availability.
- WROOM-1-N16R8 LCSC part number and JLCPCB assembly stock — verify before schematic finalization.
- Board outline: keep current dimensions or shrink? Deferred to PCB layout phase.
- Whether to keep TPIO43/TPIO44 (I2C SDA/SCL test points) and TPIO10-13 (TCA_RESET, INT1-3 test points) or consolidate. These connect to active signals and are useful for debugging — likely keep.

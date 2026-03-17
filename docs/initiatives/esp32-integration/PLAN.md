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
- Auto-download: 2x MMBT3904 NPN + 2x 10k resistors (DTR→GPIO0, RTS→EN)
- Decoupling: 10uF bulk + 3x 0.1uF (CPU, RTC, SPI) + 1uF (VDD_SPI)
- USB: 2x 22 ohm series resistors on D-/D+ lines

**J7 modification** (power_management.kicad_sch):
- Add D+/D- net connections from the TYPE-C-31-M-12 connector pads to the new ESP32 sheet
- BQ24195 D+/D- remain tied to GND (unchanged)

**LDO replacement** (moved to power_management.kicad_sch — all power components in one sheet):
- AP2112K-3.3 (U1, SOT-23-5, 600mA) removed from root sheet → AMS1117-3.3 (SOT-223, 1A) added to power_management
- LCSC **C6186** (Advanced Monolithic Systems, basic part), installed as `JLC-MCP-Power:AMS1117-3_3`
- AMS1117 pin mapping: Pin 1=GND, Pin 2=VOUT, Pin 3=VIN, Pin 4=VOUT (tab/heatsink)
- Input cap: 22µF ceramic (replaces C1 1µF)
- Output cap: 22µF tantalum (replaces C2 2.2µF) — required for AMS1117 stability (narrow ESR window, pure MLCC can cause oscillation)
- The `+3.3V` hierarchical pin on power_management changes from input to output

**Power switch** (power_management.kicad_sch):
- SPDT slide switch rated >= 3A, placed in the VSYS power path between the BQ24195 output (VSYS) and the downstream regulators (TPS61088 boost, AMS1117 LDO)
- Switch cuts all power when off — no quiescent draw from any regulator or the ESP32
- When off, BQ24195 can still charge the battery from USB (VSYS remains powered from its output side for charging, the switch isolates the load side)
- Part selection: look for a compact through-hole or SMD slide switch (e.g., SS-12D00, MSS22D18, or similar LCSC-stocked, 3A+ rated, SPDT/DPDT)
- Needs to be accessible from outside the enclosure — place at board edge

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

## Open Questions

- Board outline: keep current dimensions or shrink? Deferred to PCB layout phase.
- Whether to keep TPIO43/TPIO44 (I2C SDA/SCL test points) and TPIO10-13 (TCA_RESET, INT1-3 test points) or consolidate. These connect to active signals and are useful for debugging — likely keep.
- Auto-download circuit: confirm DTR/RTS signals are available from USB CDC (native USB uses GPIO19/20 directly — the classic DTR/RTS auto-download may need adaptation for USB CDC vs UART bridge). Review Espressif DevKitC-1 reference.

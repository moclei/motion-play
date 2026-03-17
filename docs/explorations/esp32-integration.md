# ESP32-S3 Direct Integration — Exploration

## Problem

The main PCB (v6, 4-layer) uses a LilyGO T-Display-S3 dev board (U2) as a plug-in module. This works but has significant drawbacks:

- **Hand-soldering required.** U2 is the only hand-assembled component on the board. Every other part is machine-placed by JLCPCB. This is the manufacturing bottleneck.
- **Oversized footprint.** The T-Display-S3 is ~65mm x 25.4mm — the single largest component on the board. It consumes board area disproportionate to what we actually use.
- **Unused onboard peripherals.** The dev board includes a 1.9" TFT display (14 GPIOs consumed internally), a LiPo charger (TP4056/TP4065), a touch controller (CST816), and an SD card interface. We use none of these in the final design — the main PCB now has its own BQ24195 charger, and the display is not needed for field operation.
- **Two USB-C ports.** The T-Display has its own USB-C (for programming), separate from the main PCB's J7 (power-only). This is confusing and wastes a connector.
- **Cost.** The T-Display-S3 retails for $15-20, while the ESP32-S3 module inside it costs $5-7.

Replacing the T-Display with a directly-integrated ESP32-S3-WROOM-1 module would eliminate hand-assembly, shrink the board, reduce cost, and simplify the USB situation — all while maintaining identical electrical functionality.

## Current State

### What U2 connects to

From `hardware/pcb-main/kicad/circuit-context.json` and `firmware/include/pin_config.h`, these are the signals between U2 and the rest of the board:

| GPIO | Signal | Net | Connects To |
|------|--------|-----|-------------|
| 43 | I2C SDA | `/I2C_SDA` | TCA9548A (U4), BQ24195 (U5), INA219 (U7) |
| 44 | I2C SCL | `/I2C_SCL` | TCA9548A (U4), BQ24195 (U5), INA219 (U7) |
| 10 | TCA_RESET | `/TCA9548A_Subsystem/TCA_RESET` | TCA9548A reset (active low) |
| 13 | INT1 | `/INT1` | Sensor module 1 interrupt |
| 12 | INT2 | `/INT2` | Sensor module 2 interrupt |
| 11 | INT3 | `/INT3` | Sensor module 3 interrupt |
| 16 | LED_DATA | `/LED Controller/DATA_IN` | SN74AHCT125 level shifter (IC1) → WS2812B strip |
| 21 | CHRG_INT | `/Power Management/CHRG_INT` | BQ24195 interrupt (wired, not yet used in firmware) |
| — | +5V | `+5V` | Bidirectional 5V rail |
| — | GND | `GND` | 5 ground pins |

Additionally, 5 GPIOs (1, 2, 3, 17, 18) are routed to test point pads but are currently unused.

### What the T-Display-S3 provides internally

The T-Display-S3 uses a bare ESP32-S3R8 chip (not a WROOM module) with:

- 16MB external flash, 8MB in-package PSRAM
- PCB trace antenna for WiFi/BT
- ST7789V 1.9" TFT (8-bit parallel interface, 14 GPIOs)
- Native USB — no UART bridge chip. Programming and serial via USB CDC on GPIO19/20.
- TP4056/TP4065 LiPo charger
- ~500mA internal 3.3V LDO (powers only the ESP32, separate from main PCB's AP2112K)
- Boot button (GPIO0), reset button (EN), user button (GPIO14)
- Optional CST816 touch controller (disabled in our firmware — GPIO16 conflict with LED strip)

### T-Display-S3 feature audit

| Feature | Status | Notes |
|---------|--------|-------|
| ESP32-S3 dual-core 240MHz | **Used** — core MCU | Must replicate |
| 8MB PSRAM | **Used** — 30k+ sample buffering | Must replicate |
| 16MB flash | **Used** — firmware + TFLite model | Must replicate |
| Native USB (GPIO19/20) | **Used** — programming + serial | Must replicate, route to J7 |
| PCB antenna | **Used** — WiFi + BT | Must replicate |
| Boot/Reset buttons | **Used** — programming workflow | Must replicate + auto-download circuit |
| ST7789V TFT display | **Dropping** | Not needed for field operation. Serial + LED strip provide feedback. |
| Internal 3.3V LDO | **Replacing** | Main PCB LDO will power ESP32 directly |
| User button (GPIO14) | **Not replicating** | GPIO available if needed later |
| Battery charger (TP4056) | **Not needed** | BQ24195 on main PCB handles charging |
| LiPo connector | **Not needed** | J8 on main PCB |
| Touch controller (CST816) | **Not needed** | Was disabled for LED strip GPIO conflict |
| SD card interface | **Not needed** | GPIO conflicts with sensor interrupts |
| Battery voltage ADC (GPIO4) | **Not needed** | BQ24195 I2C + INA219 provide power monitoring |

### Power architecture

The v6 board power path is: USB-C (J7) → F2 fuse → BQ24195 (U5) → VSYS → TPS61088 boost (U6) → +5V. The +5V rail feeds the AP2112K (U1) which produces +3.3V for the TCA9548A, I2C pull-ups, and sensor board connectors. The T-Display-S3 takes +5V from pin 12 and has its own internal 3.3V LDO for the ESP32 chip.

When the T-Display is replaced, the ESP32 module needs 3.3V from the main PCB's LDO. This changes the 3.3V rail load from ~4.1mA (peripherals only) to ~410-500mA peak (peripherals + ESP32 WiFi/BT TX + TFLite inference).

### I2C bus architecture

The I2C bus (GPIO43 SDA, GPIO44 SCL, 2.2k pull-ups to 3.3V) is shared between:

- TCA9548A (0x70) — sensor mux, Core 0 at up to 1000Hz
- BQ24195 (0x6B) — battery charger, Core 1 occasional access
- INA219 (0x40) — power monitor, Core 1 occasional access

Speed is critical for the sensor path. Serial debugging uses native USB CDC (GPIO19/20), which is completely independent of the I2C bus. The default UART0 maps to GPIO43/44, but we use those for I2C — and since the T-Display (and the WROOM-1) uses native USB for serial, UART0 is never active. The ESP32-S3 ROM bootloader briefly outputs on GPIO43/44 during the first few ms of cold boot (before `Wire.begin()`), which is not a practical concern.

## Options

### Option A: Direct integration with ESP32-S3-WROOM-1-N16R8

Replace the T-Display-S3 with an ESP32-S3-WROOM-1-N16R8 module soldered directly to the main PCB. This is the recommended path.

**Module selection:** ESP32-S3-WROOM-1-N16R8

- 16MB flash (matches T-Display-S3's 16MB — no risk of flash constraints as firmware grows)
- 8MB octal PSRAM (matches T-Display-S3)
- Built-in PCB antenna (compatible with 3D-printed plastic enclosures)
- 25.5mm x 18mm (vs T-Display-S3's 65mm x 25.4mm)
- JLCPCB assembly compatible — eliminates the only hand-soldered component
- GPIO33-37 consumed by octal PSRAM bus (not needed by our design)

**Required support circuitry:**

1. **3.3V LDO upgrade** — Replace AP2112K-3.3 (U1, 600mA, SOT-23-5) with AMS1117-3.3 (1A, SOT-223) or equivalent. Supplies ESP32 module + all 3.3V peripherals. 1A provides headroom for simultaneous WiFi TX + BT + TFLite inference + sensors at max rate. Same +5V input, same output voltage, same function — just higher current capacity.

2. **EN/Reset circuit** — 10k pull-up to 3.3V + 1uF cap to GND on the EN (CHIP_PU) pin. Tactile reset button pulling EN low. The RC time constant ensures clean boot sequencing.

3. **Boot mode circuit** — 10k pull-up to 3.3V on GPIO0 (module also has internal 45k pull-up). Tactile boot button to GND.

4. **Auto-download circuit** — Classic 2-transistor DTR/RTS circuit: 2x NPN (e.g. MMBT3904) + 2x 10k resistors. Connects USB DTR → GPIO0 and RTS → EN for automatic bootloader entry from esptool/PlatformIO. Without this, boot and reset buttons must be manually pressed during flashing.

5. **USB data routing to J7** — Route GPIO19 (USB D-) and GPIO20 (USB D+) with 22 ohm series resistors to J7's D+/D- pads. The TYPE-C-31-M-12 connector already has these pads — they're just not connected in v6 (J7 is power-only). This unifies power and programming into a single USB-C port. The BQ24195 D+/D- pins remain tied to GND (they're used for USB source detection, not data).

6. **Module decoupling** — 10uF bulk capacitor at VDD pin + 0.1uF at each power domain (VDD3P3_CPU, VDD3P3_RTC, VDD_SPI) + 1uF at VDD_SPI. ~5 additional capacitors total.

7. **Antenna keepout** — The WROOM-1 module must be placed at a board edge with the antenna extending beyond or flush with the edge. A ~10-15mm keepout zone beyond the antenna (no copper pour, no components, no ground plane) is required for proper RF performance. This is a PCB layout constraint, not a BOM item.

**GPIO mapping (active signals — unchanged from v6):**

| GPIO | Function | WROOM-1 Pin |
|------|----------|-------------|
| 43 | I2C SDA | 37 (TXD0) |
| 44 | I2C SCL | 36 (RXD0) |
| 10 | TCA_RESET | 18 |
| 13 | INT1 | 21 |
| 12 | INT2 | 20 |
| 11 | INT3 | 19 |
| 16 | LED_DATA | 9 |
| 21 | CHRG_INT | 23 |
| 19 | USB D- | 13 |
| 20 | USB D+ | 14 |
| 0 | BOOT button | 27 |
| — | EN (reset) | 3 |

All active signals map directly. With the display removed, GPIOs 5-9, 14, 15, 38-42, 45-48 become available as spare pins for future expansion.

**Board size impact:**

- T-Display-S3: ~65mm x 25.4mm = ~1,651 mm^2
- WROOM-1 + support circuitry: ~25.5mm x 18mm + ~150 mm^2 = ~609 mm^2
- Antenna keepout: ~180-270 mm^2 (at board edge, may overlap with existing edge clearance)
- Net reduction: ~770-910 mm^2 (47-55% of current MCU area)

**BOM cost impact (per board):**

| Item | Cost Delta |
|------|------------|
| Remove T-Display-S3 | -$15 to -$20 |
| Add ESP32-S3-WROOM-1-N16R8 | +$5.50-7 |
| AMS1117-3.3 (replaces AP2112K, similar price) | +$0.10 |
| 2x MMBT3904 NPN + resistors + caps | +$0.50 |
| 2x tactile switches (boot + reset) | +$0.30 |
| **Net savings** | **~$8-14** |

The manufacturing improvement is more significant than the BOM savings: the WROOM-1 is reflow-solderable, making the board fully JLCPCB-assembled with zero hand-soldering.

**Firmware impact:**

- PlatformIO board definition changes from `lilygo-t-display-s3` to a generic ESP32-S3 board
- TFT_eSPI library dependency and `User_Setup.h` removed
- `DisplayManager` becomes a no-op stub or is removed (all call sites in `main.cpp` updated)
- Display pin definitions removed from `pin_config.h`; active GPIO numbers (10-13, 16, 21, 43, 44) unchanged
- `Serial` continues to work via USB CDC (GPIO19/20) — no change to debugging workflow
- All sensor, networking, detection, and ML code is unaffected

**Effort level:** Medium. New schematic sheet for ESP32 support circuitry, USB data routing added to J7, LDO swap, PCB relayout of MCU area. Firmware changes are mostly deletion (display code) and config (board definition). Existing sensor/networking/detection code is untouched.

### Option B: Keep T-Display-S3

Continue with the current plug-in module approach. No schematic or firmware changes.

**Trade-offs:** Retains hand-soldering dependency, larger board, higher BOM cost, two USB-C ports, unused display consuming GPIOs and power. Only advantage is zero engineering effort. This is the fallback if v6 validation reveals unexpected issues that make a board revision impractical in the near term.

## Reference Designs

These should be consulted during schematic design:

- **Espressif ESP32-S3-DevKitC-1** — Official reference schematic. Has the canonical auto-download circuit, EN/GPIO0 handling, and USB routing. [Hardware Design Guidelines](https://docs.espressif.com/projects/esp-hardware-design-guidelines/en/latest/esp32s3/schematic-checklist.html) is essential reading.
- **Unexpected Maker TinyS3/FeatherS3** — Open-source KiCad designs at [github.com/UnexpectedMaker/esp32s3](https://github.com/UnexpectedMaker/esp32s3). Compact layouts, good reference for minimal support circuitry.
- **FrWA14 KiCad 8 DevBoard** — JLCPCB-oriented WROOM-1 design at [github.com/FrWA14/KiCad8_ESP32S3_DevModule_wroom-1_DevelopementBoard](https://github.com/FrWA14/KiCad8_ESP32S3_DevModule_wroom-1_DevelopementBoard).

## Recommendation

Proceed with Option A (direct ESP32-S3-WROOM-1-N16R8 integration) as the next board revision after v6 boards arrive and are validated. The decision to drop the display, unify USB through J7, and upgrade the LDO to AMS1117-3.3 are confirmed. This change eliminates the last hand-assembly step, reduces board area by ~50%, saves ~$8-14 per board in BOM cost, and simplifies the system from two USB-C ports to one.

This should be scoped as an initiative (`docs/initiatives/esp32-integration/`) once v6 validation is complete and we're ready to begin schematic work.

## Decision

**Status: Decided**

Proceeding with Option A: direct ESP32-S3-WROOM-1-N16R8 integration. Schematic work begins now on a branch, in parallel with v6 board validation. Firmware changes (DisplayManager removal, board definition) are part of the same initiative, phased after hardware.

See initiative: `docs/initiatives/esp32-integration/`

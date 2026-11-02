# ESP32 Integration — Routing Priority Guide

Route in this order. Higher priority nets have stricter constraints.

## Priority 1 — USB Differential Pair

Route first — needs clear space and impedance control.

**Signal path:** J7 → U9 → R52/R53 → U3

| Segment | From | To | Net |
|---------|------|----|-----|
| 1a | J7 pad A6/B6 | U9 pin 1/6 | /USB_DP |
| 1b | J7 pad A7/B7 | U9 pin 3/4 | /USB_DN |
| 2a | U9 pin 6 | R53 pin 1 | /USB_DP |
| 2b | U9 pin 4 | R52 pin 1 | /USB_DN |
| 3a | R53 pin 2 | U3 pin 14 (122.0, 125.4) | /USB_DP_MCU |
| 3b | R52 pin 2 | U3 pin 13 (122.0, 124.1) | /USB_DN_MCU |

**Rules:**
- Route as a differential pair — maintain consistent spacing between the two traces
- 90Ω differential impedance target (check trace geometry against your stackup)
- Match trace lengths within 0.5mm (D+ and D- should be the same length)
- Avoid vias; if unavoidable, via both traces together at the same point
- Keep clear of boost converter area (U6/L2 switching noise)
- Segments 1a/1b route south through J7's footprint area to U9
- Segments 2a/2b route east across the board to R52/R53
- Segments 3a/3b are short, R52/R53 to U3 left side

## Priority 2 — Power Rails

Wide traces for current handling. Use 0.5mm minimum width, wider where space allows.

| From | To | Net | Notes |
|------|----|-----|-------|
| +5V rail (from TPS61088 output area) | U8 pin 3 (111.0, 105.8) | +5V | Short, direct |
| U8 pin 2/4 pour | U3 pin 2 (122.0, 110.2) | +3.3V | Via the +3.3V copper pour |
| U8 pin 2/4 pour | Existing +3.3V distribution | +3.3V | To caps, U4, sensors |
| VSYS source | SW1 pin 1 (101.4, 139.2) | VSYS | Carries full system current |
| SW1 pin 2 (96.7, 139.2) | R44, U7 | VSYS_SW | Wide trace or pour |
| +5V | D5 pin 2 (VDD) | +5V | 0.25mm OK |
| GND | All new component GND pins | GND | Via to ground plane |

## Priority 3 — ESP32 Support Circuits

Standard signal traces, 0.2–0.25mm width.

| From | To | Net | Notes |
|------|----|-----|-------|
| +3.3V | R50 pin 1 | +3.3V | Short, near U3 |
| R50 pin 2 | U3 pin 3 (EN) | /ESP32_S3/EN | Keep short |
| C50 pin 1 | U3 pin 3 (EN) | /ESP32_S3/EN | Keep short |
| C50 pin 2 | GND | GND | Via nearby |
| SW2 pin 1 | U3 pin 3 (EN) | /ESP32_S3/EN | 19mm trace OK (R50+C50 filter noise) |
| SW2 pin 2 | GND | GND | Via nearby |
| +3.3V | R51 pin 1 | +3.3V | Short, near U3 |
| R51 pin 2 | U3 pin 27 (GPIO0) | /ESP32_S3/GPIO0_BOOT | Keep short |
| SW3 pin 1 | U3 pin 27 (GPIO0) | /ESP32_S3/GPIO0_BOOT | Short |
| SW3 pin 2 | GND | GND | Via nearby |
| C51–C55 | Between +3.3V and GND | +3.3V / GND | As short as possible to pin 2 |

## Priority 4 — Board Signal Connections

Connect U3 to existing board circuitry. Standard trace width.

| From | To | Net | Notes |
|------|----|-----|-------|
| U3 pin 37 (139.5, 112.7) | U4 (TCA9548A) | /I2C_SDA | Route right from U3 |
| U3 pin 36 (139.5, 114.0) | U4 | /I2C_SCL | Keep near SDA |
| U3 pin 18 (127.6, 126.7) | U4 pin 3, R6 | /TCA_RESET | Bottom of U3 toward right |
| U3 pin 9 (122.0, 119.1) | D5 pin 1, IC1 | /LED_DATA | Left side of U3 |
| U3 pin 23 (133.9, 126.7) | R38, U5 pin 7 | /CHRG_INT | Bottom of U3 toward left |

## Priority 5 — Finishing

| Item | Notes |
|------|-------|
| TPIO21 | Connect to /CHRG_INT net |
| Other test points | Verify existing connections still valid |
| U3 GND pad | Place 9 vias in the 3×3 sub-pad grid |
| U8 thermal vias | Place 4–6 vias in the +3.3V pour |
| Ground pour | Fill on all open areas after routing complete |

## Copper Pour Summary

| Component | Net | Purpose | Minimum size |
|-----------|-----|---------|-------------|
| U8 heatsink tab | +3.3V | Thermal dissipation | Cover pins 2+4 area (~8×6mm) |
| U3 module body | GND | RF ground plane + thermal | Continuous under body, stop at antenna keepout |

## Trace Width Reference

| Category | Width | Where |
|----------|-------|-------|
| USB differential pair | Per impedance calc | J7 → U9 → R52/R53 → U3 |
| Power rails (+5V, +3.3V, VSYS) | 0.5mm+ | All power connections |
| Standard signals | 0.2–0.25mm | I2C, LED_DATA, EN, BOOT, CHRG_INT |
| GND connections | Via to plane | Don't route GND as traces; use vias to ground pour |

---

*Reference: pad positions from pcb-layout-context.json extracted at current board state.*

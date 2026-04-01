# Dual-Bus I2C — Main PCB Implementation

## Intent

Implement the dual-bus I2C architecture on the main PCB, removing the TCA9548A multiplexer and splitting sensor I2C traffic across both ESP32-S3 hardware I2C controllers. This reduces poll cycle time from ~2.8ms to ~1.2ms and improves timestamp precision for direction detection.

## Goals

- Remove TCA9548A (U4) and its passives (C9, C10, R6) from the main PCB schematic and layout
- Route I2C0 (GPIO43/44) directly to J4 (M1) and J5 (M2) connectors
- Route I2C1 (new GPIO pair) to J6 (M3) connector
- Add pull-ups and test points for the new I2C1 bus
- Reduce sensor connectors from 5-pin to 4-pin JST-SH (INT lines removed)
- Clean ERC/DRC, verified BOM/CPL, ready to order from JLCPCB

## Scope

What's in:
- Main PCB schematic changes (TCA removal, bus routing, connector changes, pull-ups, test points)
- Main PCB layout changes (component removal, placement, routing, copper pours)
- Context file re-extraction (circuit-context.json, pcb-layout-context.json)
- ERC and DRC verification
- Production file export and BOM/CPL review

What's out:
- Sensor rigid/flex board changes (they already have addressable PCA9546As with DIP switches)
- Firmware changes (separate initiative — dual Wire instances, PCA addressing, TCA driver removal)
- Cable fabrication (new 4-pin JST-SH cables needed, but that's a procurement task)

## Constraints

- Must be on branch `esp32-integration-schematic` (where the ESP32-S3 module integration lives)
- GPIO pair for I2C1 must avoid strapping pins (GPIO 0, 3, 45, 46) and already-used pins
- Bus 1 pull-ups must support 400kHz Fast Mode over 825mm cable (~100-120pF load)
- All parts must be JLCPCB-assemblable (LCSC stock)
- Origin exploration: `docs/explorations/multi-bus/multi-bus-architecture.md`

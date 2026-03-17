# ESP32-S3 Direct Integration

## Intent

Replace the T-Display-S3 dev board (U2) with an ESP32-S3-WROOM-1-N16R8 module soldered directly to the main PCB. This eliminates the only hand-assembled component, reduces board area and BOM cost, and unifies the two USB-C ports into one.

Exploration: `docs/explorations/esp32-integration.md`

## Goals

- Fully JLCPCB-assembled board — zero hand-soldering required
- Single USB-C port (J7) for both power and programming
- Same electrical functionality as v6 — all sensor, networking, detection, and ML capabilities preserved
- 3.3V LDO upgraded to handle ESP32 directly (AMS1117-3.3 or equivalent, 1A)
- Physical on/off power switch on the PCB (slide switch, previously blocked by space constraints in v6)
- Firmware builds and runs on the new hardware with no functional regression

## Scope

What's in:
- ESP32-S3-WROOM-1-N16R8 module integration with support circuitry (EN/reset, boot, auto-download, decoupling)
- USB D+/D- data routing added to J7
- AP2112K replaced with AMS1117-3.3 (or equivalent 1A LDO)
- T-Display-S3 footprint and associated nets/test points removed
- Physical slide switch for system on/off (in the power path, rated for system current)
- PCB relayout of the MCU area (module placement, antenna keepout)
- Firmware adaptation (board definition, DisplayManager removal, pin_config cleanup)
- JLCPCB manufacturing review (BOM, CPL, DRC, stock check)

What's out:
- New features, GPIO breakouts, or additional peripherals beyond the power switch — this is a like-for-like replacement
- Board outline resize (evaluate during layout but not a goal of this revision)
- Enclosure redesign (if the board shrinks, enclosure updates are a separate effort)
- Power management changes beyond the LDO swap (BQ24195, TPS61088, INA219 circuits are unchanged)

If a low-risk, compelling addition presents itself during layout, it can be considered — but the default is no scope creep.

## Constraints

- v6 board must validate successfully before this revision is sent to fabrication
- Schematic work can proceed now on a branch; fabrication is gated on v6 validation
- All existing I2C addresses and bus topology must be preserved (TCA9548A 0x70, BQ24195 0x6B, INA219 0x40)
- GPIO assignments for active signals (43, 44, 10-13, 16, 21) must not change — firmware compatibility with v6 sensor/networking code
- WROOM-1 antenna keepout zone (~10-15mm) must be respected at a board edge

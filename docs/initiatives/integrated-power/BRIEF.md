# Integrated Power Management

## Intent

Replace the DWEII USB-C power module with a custom power management system integrated directly onto the main PCB. This adds proper battery charging, power path management, a boost converter sized for the LED strip, and MCU-visible power monitoring — all without a separate power board or inter-board connectors.

See `docs/explorations/power-budget.md` for the analysis that informed this initiative.

## Goals

- The main PCB accepts USB-C power input and charges a single-cell Li-ion battery (Samsung 30Q 18650 or equivalent)
- +5V rail delivers 3A+ continuous from battery or USB, powering the LED strip, T-Display-S3, and level shifter
- MCU can read system voltage and current in real time via I2C (INA219 on VSYS)
- MCU can configure charge parameters and read charge status via I2C (BQ24195)
- No hand-soldered third-party modules — all power components are JLCPCB-assembled
- System operates from USB alone (no battery), from battery alone (no USB), or both simultaneously

## Scope

What's in:
- USB-C power input with 5.1k CC pull-downs (power only, no data, no PD negotiation)
- BQ24195 battery charger and power path management IC with full support circuitry
- High-current boost converter (8-10A switch class) from VSYS to +5V
- INA219 power monitor on VSYS rail
- PMOS battery reverse polarity protection
- NTC thermistor for battery temperature monitoring
- BQ24195 INT signal wired to a T-Display-S3 GPIO
- Test points on key voltage rails
- Removal of DWEII module footprint and Schottky diode from main PCB
- Datasheet sourcing for BQ24195, selected boost converter, and INA219

What's out:
- USB PD negotiation (STUSB4500 removed; basic USB-C 5V is sufficient for V1)
- USB data lines (D+/D-) — future initiative for bare ESP32-S3 + single USB-C
- Replacing the T-Display-S3 with a bare ESP32-S3 — separate future initiative
- Changes to the 3.3V regulator — existing AP2112K stays, fed from +5V post-boost
- Changes to sensor boards, LED controller, or TCA9548A subsystem
- Firmware for BQ24195/INA219 I2C communication (separate task after hardware is validated)
- Enclosure redesign (will be needed but is a separate mechanical effort)

## Constraints

- +5V rail: minimum 2.4A continuous, target 3A+
- +3.3V rail: existing AP2112K (600mA) fed from +5V post-boost. Not replaced.
- Li-ion single-cell: 3.0V-4.2V operating range (Samsung 30Q 18650 or equivalent)
- USB-C input: 5V, no PD. VBUS fuse rated at 3A.
- All components must be available on LCSC and JLCPCB-assembable (standard SMD)
- Thermal: boost converter + BQ24195 dissipation estimated at 4-5W worst case. Must be validated against copper pour area during component selection. No active cooling.
- Board area: adding ~25-30 components to the main PCB. If board grows beyond current 85mm x 45mm, flag early (enclosure will be redesigned).
- I2C bus shared with TCA9548A (0x70). BQ24195 at 0x6B, INA219 at 0x40. Pull-ups must be 3.3V (not 5V).
- BQ24195 ILIM resistor sets boot-time input current limit (~1-1.5A). Firmware must configure actual limit on boot.
- Design must not preclude future USB D+/D- passthrough for single-USB-C architecture.

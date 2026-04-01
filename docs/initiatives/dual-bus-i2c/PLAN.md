# Dual-Bus I2C — Plan

## Approach

All changes are on the main PCB (`hardware/pcb-main/kicad/`). The user makes schematic and layout edits manually in KiCad; AI provides step-by-step guidance, part selection, and verification after each phase. Context files are re-extracted after schematic and layout phases to confirm correctness.

## Architecture: Before and After

**Before (current):**
```
ESP32-S3 I2C0 (GPIO43 SDA, GPIO44 SCL)
  ├── BQ24195 (0x6B)
  ├── INA219 (0x40)
  └── TCA9548A (0x70)    ← being removed
       ├── Ch0 → J4 → PCA#1 (0x74) → M1 sensors
       ├── Ch1 → J5 → PCA#2 (0x75) → M2 sensors
       └── Ch2 → J6 → PCA#3 (0x76) → M3 sensors
```

**After:**
```
ESP32-S3 I2C0 (GPIO43 SDA, GPIO44 SCL)
  ├── BQ24195 (0x6B)
  ├── INA219 (0x40)
  ├── J4 → PCA#1 (0x74) → M1 sensors
  └── J5 → PCA#2 (0x75) → M2 sensors

ESP32-S3 I2C1 (GPIO11 SDA, GPIO12 SCL)   ← new bus
  └── J6 → PCA#3 (0x76) → M3 sensors
```

## GPIO Selection for I2C1

**GPIO11 (SDA1) and GPIO12 (SCL1).** Rationale:
- Both are freed by abandoning INT lines (INT3/INT2 were already marked no-connect on the ESP32 sheet)
- Not strapping pins (strapping is GPIO 0, 3, 45, 46 only)
- Adjacent pin numbers on the WROOM-1 module (pins 19 and 20) — convenient for PCB routing
- GPIO13 (INT1) stays available as a spare, and GPIO10 (former TCA_RESET) is also freed

## Parts Needed

| Ref | Part | Value | Footprint | LCSC | Purpose |
|-----|------|-------|-----------|------|---------|
| R60 | Resistor | 2.2kΩ | 0603 | C114662 | I2C1 SDA pull-up |
| R61 | Resistor | 2.2kΩ | 0603 | C114662 | I2C1 SCL pull-up |
| J4 | JST-SH 4-pin | SM04B-SRSS-TB | JST_SH_SM04B-SRSS-TB | TBD | Replace 5-pin (M1) |
| J5 | JST-SH 4-pin | SM04B-SRSS-TB | JST_SH_SM04B-SRSS-TB | TBD | Replace 5-pin (M2) |
| J6 | JST-SH 4-pin | SM04B-SRSS-TB | JST_SH_SM04B-SRSS-TB | TBD | Replace 5-pin (M3) |

R60/R61 use the same part as existing R28/R29. Connector LCSC part number and footprint availability need to be confirmed in Phase 1.

## Components Removed

| Ref | Part | Reason |
|-----|------|--------|
| U4 | TCA9548A (TSSOP-24) | No longer needed — PCAs addressed directly |
| C9 | 100nF decoupling | TCA bypass cap |
| C10 | 10µF decoupling | TCA bulk cap |
| R6 | 10kΩ pull-up | TCA ~RESET pull-up |
| TPIO10 | Test point | Was TCA_RESET signal — no longer exists |

## Net Changes

| Net | Action |
|-----|--------|
| `/TCA9548A_Subsystem/CH0_SDA`, `CH0_SCL` | Removed — J4 connects directly to `/I2C_SDA`, `/I2C_SCL` |
| `/TCA9548A_Subsystem/CH1_SDA`, `CH1_SCL` | Removed — J5 connects directly to `/I2C_SDA`, `/I2C_SCL` |
| `/TCA9548A_Subsystem/CH2_SDA`, `CH2_SCL` | Removed — replaced by `/I2C1_SDA`, `/I2C1_SCL` |
| `/TCA_RESET` | Removed — TCA no longer exists |
| `/I2C1_SDA` | **New** — Bus 1 data line |
| `/I2C1_SCL` | **New** — Bus 1 clock line |
| `/ESP32_S3/INT1`, `INT2`, `INT3` | Removed from ESP32 sheet (were already no-connect) |

## ESP32 Sheet Changes

On `esp32_s3.kicad_sch`, U3 pin changes:
- Pin 19 (IO11): change from `/ESP32_S3/INT3` → `/I2C1_SDA`
- Pin 20 (IO12): change from `/ESP32_S3/INT2` → `/I2C1_SCL`
- Pin 21 (IO13): change from `/ESP32_S3/INT1` → unconnected (or spare GPIO breakout)
- Pin 18 (IO10): change from `/TCA_RESET` → unconnected (or spare GPIO breakout)

The ESP32 sub-sheet's hierarchical pins need to be updated: remove `TCA_RESET`, `INT1`, `INT2`, `INT3`; add `I2C1_SDA`, `I2C1_SCL`.

## Pull-Up Strategy

**Bus 0 (I2C0):** R28 (2.2kΩ SDA) and R29 (2.2kΩ SCL) currently on the TCA subsystem sheet. These must be preserved — either moved to the root sheet or to a replacement section. They connect to `/I2C_SDA` and `/I2C_SCL` with the other end to +3.3V.

**Bus 1 (I2C1):** New R60 (2.2kΩ SDA) and R61 (2.2kΩ SCL) connecting `/I2C1_SDA` and `/I2C1_SCL` to +3.3V. Place near J6 on the PCB.

## PCB Routing Guidance

- I2C0 traces (SDA/SCL) from ESP32 U3 pads → R28/R29 pull-ups → split to J4 and J5. Keep traces short and matched length where practical.
- I2C1 traces from ESP32 U3 pins 19/20 → R60/R61 pull-ups → J6. These are the 825mm cable bus — clean routing from MCU to connector matters.
- Place R60/R61 close to J6 (or close to U3 — either is fine for 400kHz).
- Ground pour continuity under I2C traces for signal integrity.
- The removed TCA footprint frees board space — may simplify overall routing.

## Open Questions

- JST-SH SM04B-SRSS-TB LCSC part number and JLCPCB assembly availability — verify in Phase 1.
- Whether to keep GPIO10 and GPIO13 as spare breakout pads or leave fully unconnected.

# Power Budget — Exploration

## Problem

The Motion Play system has no consolidated power budget. The current design uses a DWEII USB-C module (hand-soldered, 5V @ ~2.4A with battery charging) and an AP2112K-3.3 LDO for 3.3V. This works for prototyping but has limitations: two USB-C ports (one on the DWEII, one on the T-Display-S3), limited current capacity, and no MCU visibility into power state.

Before designing a custom integrated power solution, we need accurate numbers for every consumer on both voltage rails, validated against datasheets, to correctly size the boost converter, verify battery life expectations, and establish thermal budgets.

## Current State

### System Architecture

The main PCB (`hardware/pcb-main/kicad/circuit-context.json`) hosts:
- T-Display-S3 (ESP32-S3 dev board) — MCU, WiFi, BT, LCD
- TCA9548A I2C multiplexer — routes to 3 sensor boards
- SN74AHCT125 level shifter — 3.3V to 5V for WS2812B LED data
- 3x JST-SH connectors to sensor modules (each with PCA9546A + 2x VCNL4040)
- JST-PH connector to LED strip (72 LEDs currently, upgrading to 90)
- DWEII USB-C power module → Schottky diode → +5V rail
- AP2112K-3.3 LDO → +3.3V rail

### Previous Power Estimates

Scattered across the codebase (no single source of truth):
- `docs/references/vcnl4040/CONFIGURATION_GUIDE.md`: 5mA avg per sensor at 200mA LED / 1/40 duty
- `docs/references/vcnl4040/DUTY_CYCLE_IMPLEMENTATION.md`: 30mA total for 6 sensors at 1/40 duty
- `hardware/archive/sensor-alt-pt/docs/hoop_detection_schematic_plan_final.md`: Old phototransistor-era budget (<350mA peak), not applicable to current VCNL4040 design

These earlier estimates used different assumptions and configurations. The numbers below supersede them.

## Power Budget Analysis

### 5V Rail Consumers

| Consumer | Typical | Peak | Source / Notes |
|----------|---------|------|----------------|
| WS2812B LED strip (90 LEDs @ 20mA max per LED) | varies by pattern | 1.80A | 90 LEDs = 1500mm @ 60/m. 20mA/LED is a design constraint, not full-white max (which is 60mA/LED). Actual patterns will vary. |
| T-Display-S3 (ESP32-S3 + LCD) | ~120mA | ~200mA | WiFi TX bursts dominate peak. LCD backlight ~20mA. BT adds ~30mA when active. |
| SN74AHCT125 level shifter | ~1mA | ~1mA | Only 1 of 4 buffers used. Quiescent + switching negligible. |
| AP2112K-3.3 quiescent + load | ~5mA | ~5mA | At ~5mA 3.3V output, input current ≈ output current × (3.3/5) / efficiency ≈ 5mA |
| **Total 5V** | **varies** | **~2.01A** | Design target: 3A+ continuous capability for LED headroom |

### 3.3V Rail Consumers

| Consumer | Typical | Peak | Source / Notes |
|----------|---------|------|----------------|
| 6x VCNL4040 proximity sensors | 1.8mA | 1.8mA | ~0.3mA avg each at 200mA IR LED, 1/40 duty, 2T integration, 8x multi-pulse. IR LED current is pulsed internally; average draw is low. |
| TCA9548A I2C mux | ~0.1mA | ~0.1mA | Quiescent current per datasheet |
| 3x PCA9546A I2C mux | ~0.3mA | ~0.3mA | ~0.1mA each, quiescent |
| I2C pull-ups (2.2k to 3.3V, x2 upstream + x2 per sensor board x3) | ~1.2mA | ~1.2mA | Worst case when lines held low: 3.3V / 2.2k = 1.5mA per pair. Duty cycle < 100%. |
| Sensor board pull-ups (4.7k reset, address, INT) | ~0.7mA | ~0.7mA | Various 4.7k-10k pull-ups across 3 sensor boards |
| **Total 3.3V** | **~4.1mA** | **~4.1mA** | Well within AP2112K's 600mA rating |

### Total System Power

| Condition | 5V Draw | 3.3V Draw | Total Power | Notes |
|-----------|---------|-----------|-------------|-------|
| Idle (LEDs off, WiFi sleep) | ~0.13A | ~4mA | ~0.67W | Baseline for battery life |
| Active sensing, LEDs moderate | ~1.0A | ~4mA | ~5.0W | Typical field use |
| Full load (all LEDs, WiFi TX) | ~2.0A | ~4mA | ~10.0W | Peak / worst case |

### Battery Life Estimates (Samsung 30Q, 3000mAh, 3.7V nominal)

Battery energy: 3.0Ah × 3.7V = 11.1Wh. Accounting for boost converter efficiency (~85%):

| Mode | System Power | Battery Drain | Estimated Runtime |
|------|-------------|---------------|-------------------|
| Idle | ~0.67W | ~0.79W from battery | ~14 hours |
| Active sensing, moderate LEDs | ~5.0W | ~5.9W from battery | ~1.9 hours |
| Full load | ~10.0W | ~11.8W from battery | ~56 minutes |

Active sensing with moderate LEDs is the most relevant scenario for field playtesting. ~2 hours of runtime is achievable with brightness management.

### Boost Converter Sizing

The boost converter steps VSYS (3.0V-4.2V on battery, ~4.5V on USB) up to 5V.

At 3A output / 3.0V input (worst case — nearly depleted battery):
- Required input current: 3A × 5V / (3.0V × 0.85) = **5.9A**
- Peak inductor current (with ripple): ~6.5-7A
- **Minimum switch rating: 8A, recommended 10A**

At 3A output / 3.7V input (typical battery):
- Required input current: 3A × 5V / (3.7V × 0.85) = **4.8A**

At 3A output / 4.5V input (USB-powered, VSYS ≈ VBUS - BQ24195 dropout):
- Required input current: 3A × 5V / (4.5V × 0.85) = **3.9A**

The MT3608 (2A switch) in the existing power supply PCB design can deliver at most ~1A output at worst-case battery. It is fundamentally inadequate and must be replaced with an 8-10A switch class converter.

### Thermal Budget

Worst-case dissipation:
- Boost converter: 5V × 3A / 0.85 efficiency = 17.6W input → **2.6W dissipated** in the converter
- BQ24195 during fast charging (2A charge from 5V USB): **~1-2W** (input power management + charge regulation losses)
- Total: up to **~4-5W** on the PCB

This requires adequate copper pour area under the boost converter and BQ24195. Specific thermal validation must happen during component selection (Phase 1) using the selected converter's junction-to-ambient thermal resistance specs.

## Derived Requirements

From the analysis above:

1. **+5V rail**: 3A continuous capability (2A peak measured + headroom for brighter LEDs)
2. **+3.3V rail**: ~5mA load; existing AP2112K (600mA, fed from +5V) is more than adequate
3. **Boost converter**: 8-10A switch class, VSYS (3.0-4.5V) to 5V, >3A output
4. **Battery**: Single-cell Li-ion 18650 (Samsung 30Q 3000mAh). ~2 hours active runtime.
5. **Charging**: BQ24195 at up to 2A charge rate. ~1.5-3 hours from USB-C depending on system load during charging.
6. **Thermal**: ~4-5W worst case dissipation, must be managed with copper pours (no active cooling, no heatsink)
7. **Monitoring**: INA219 on VSYS for MCU-readable voltage/current. BQ24195 I2C for charge status.

## Recommendation

Proceed with the integrated power management initiative: integrate USB-C input, BQ24195 battery management, a high-current boost converter, and INA219 power monitoring directly onto the main PCB. Drop the DWEII module, the separate power supply PCB concept, and the STUSB4500 USB PD controller. Feed the 3.3V LDO (existing AP2112K) from the +5V post-boost rail to avoid dropout at low battery voltages.

## Decision

**Status: Decided**

Proceeding with initiative: `docs/initiatives/integrated-power/`

# Hoop Detection System

## Schematic Design Plan

**Version 2.1 — December 2024**

**BOM Verified ✓**

---

## 1. Project Overview

This document outlines the schematic design plan for a soccer ball hoop detection system using IR beam-break technology. The system detects ball passage through a suspended hoop and determines direction of travel using paired sensors with precise timing.

### 1.1 System Requirements

| Parameter | Value |
|-----------|-------|
| Hoop diameter | 500mm |
| Ball diameter | 203mm (size 5 soccer ball) |
| Number of IR beams | 3 (asymmetric placement) |
| Ball speed range | 10–30 m/s |
| Sensor spacing | 25mm (for direction detection) |
| Power budget | <1A total, <100mA average |

### 1.2 Beam Geometry

- LED positions: 0°, 50°, 100° (one half of hoop)
- Sensor positions: 180°, 230°, 280° (opposite half)
- Each sensor position has 2 photodiodes spaced 25mm apart for direction sensing.

### 1.3 Timing Considerations

The ball's cross-section through the hoop plane is not constant during transit. As the ball enters, the effective diameter starts small (just the leading edge), grows to the full 203mm at center, then shrinks again as it exits. This affects beam-break duration at the detection threshold, particularly at high speeds.

For direction detection, we measure timing differences between paired sensors (25mm apart). At 30 m/s, the ball crosses this 25mm gap in ~833µs. To reliably distinguish "A then B" from "B then A," we target <10µs timing precision.

**Critical design principle:** Detection/capture must be fast (hardware-based, microsecond precision). Processing can be slow (software-based, milliseconds to seconds acceptable). The system timestamps beam breaks in real-time via interrupts, then analyzes the data afterward.

---

## 2. Component Selection

### 2.1 Microcontroller — LilyGO T-Display-S3

| Parameter | Value |
|-----------|-------|
| Module | LilyGO T-Display-S3 (ESP32-S3R8) |
| GPIO voltage | 3.3V logic |
| Display | 1.9" ST7789 (170×320) |
| Power input | USB-C with 18650 battery support |
| Available GPIOs | 14 on headers (see Section 4.3) |

### 2.2 Photodiode — VEMD2020X01

| Parameter | Value |
|-----------|-------|
| LCSC Part # | **C3210968** |
| Peak wavelength | 940nm |
| Half angle | ±15° |
| Spectral range | 750–1050nm (daylight filter) |
| Responsivity | 12µA @ 1mW/cm² (8.5 min, 17 max) |
| Response time | 100ns rise/fall |
| Dark current | 1nA typ, 10nA max |
| Package | SMD 2.3×2.3×2.8mm (Gullwing) |

### 2.3 IR LED — P2835P1VIRB8G025-940

| Parameter | Value |
|-----------|-------|
| LCSC Part # | **C22466183** |
| Wavelength | 940nm typ (932–948nm) |
| Viewing angle | 23–29° (half angle 11.5–14.5°) |
| Optical power | 120mW typ @ 120mA, 150mW max |
| Forward voltage | 2.0V typ (1.7–2.3V) |
| Forward current (max) | 180mA peak |
| Package | SMD 2835 (2.8×3.5mm) |

---

## 3. PCB Architecture

The system uses three separate PCBs connected via flexible PCB sections.

### 3.1 Main Board (Rigid)

- ESP32-S3 T-Display-S3 module mounting
- USB-C power input with battery management
- 18650 battery holder
- LED driver circuitry (3 channels with staggered pulse control)
- MCP4728 DACs for programmable sensor thresholds (2 ICs)
- Photodiode comparator circuits (6 channels)
- FPC connectors for flex PCB interfaces

### 3.2 LED Flex PCB

- Arc length: ~436mm (covering 100° of 500mm diameter hoop)
- 3 IR LEDs at 0°, 50°, 100° positions
- Power traces for LED current (sized for pulsed operation)
- 6-pin FPC connector to main board

### 3.3 Sensor Flex PCB

- Arc length: ~436mm (covering 100° of 500mm diameter hoop)
- 6 photodiodes: 2 per beam position at 180°, 230°, 280°
- 25mm spacing between paired sensors
- Signal traces back to main board
- 8-pin FPC connector to main board

---

## 4. Circuit Schematics

### 4.1 LED Driver Circuit

**Design approach:** Staggered pulsed operation with MOSFET switching. LEDs fire sequentially (not simultaneously) to reduce peak current draw.

#### Pulsed Operation

| Parameter | Value |
|-----------|-------|
| Peak current (per LED) | 167mA (with 18Ω resistor) |
| Pulse width | 50–100µs |
| Duty cycle | ~0.2% (50µs on / 25ms period) |
| Pulse rate | 40 Hz (40 samples per second) |
| Average current (3 LEDs) | ~1mA total |

#### Staggered Pulse Sequence

1. Fire LED1, wait ~5µs for light propagation, read comparators for Sensor Pair 1
2. Turn off LED1, fire LED2, read Sensor Pair 2
3. Turn off LED2, fire LED3, read Sensor Pair 3

**Result:** Peak current drops from ~500mA (simultaneous) to ~167mA (staggered). One complete scan of all 6 sensors takes <500µs.

#### Circuit Topology

- **Power supply:** 5V rail from USB-C/battery module
- **Current limiting resistor:** R = (5V - 2.0V) / 180mA = 16.7Ω → use 18Ω (yields ~167mA)
- **Resistor power:** P = I²R = 0.167² × 18 = 0.5W peak (use 2512 package, 1W rating)
- **Switching element:** AO3400-ED N-channel MOSFET
- **Gate drive:** Direct GPIO from ESP32 (3.3V logic)
- **Gate resistor:** 100Ω to limit inrush and reduce ringing
- **Decoupling:** 100µF electrolytic (bulk) + 100nF ceramic near each MOSFET

### 4.2 Photodiode Detection Circuit

**Design approach:** Reverse-biased photodiode with comparator, programmable threshold via I2C DAC.

#### Programmable Threshold Control

MCP4728 12-bit I2C DAC provides per-sensor threshold adjustment. Two ICs provide 8 channels (6 for sensors + 2 spare). 12-bit resolution gives 4096 threshold steps (~0.8mV per step at 3.3V reference).

#### Circuit Topology

- **Bias configuration:** Reverse-biased at 5V for fastest response
- **Load resistor:** 10kΩ converts photocurrent to voltage
- **Comparator:** LM339 (quad comparator, 300ns–1.3µs response)
- **Threshold source:** MCP4728 DAC output (0–3.3V, 12-bit)
- **Output:** Open-collector with 10kΩ pull-up to 3.3V, connected to ESP32 interrupt-capable GPIO

#### Signal Budget Analysis

At 500mm distance with 167mA pulsed LED operation:

| Parameter | Value |
|-----------|-------|
| Expected photocurrent | 22–34 µA |
| Voltage with 10kΩ load | 220–340 mV |
| Dark current noise floor | 10–100 µV |
| **Signal-to-noise ratio** | **>2000:1** |

#### Detection Latency Budget

| Stage | Latency |
|-------|---------|
| Photodiode response | 100ns |
| LM339 comparator | ~300ns (large signal) |
| ESP32-S3 GPIO interrupt | 1–2µs |
| **Total detection latency** | **~1.5–2.5µs** |

### 4.3 T-Display-S3 GPIO Assignment

| GPIO | Function | Notes |
|------|----------|-------|
| GPIO43 | LED1_DRIVE | Digital output, MOSFET gate |
| GPIO44 | LED2_DRIVE | Digital output, MOSFET gate |
| GPIO21 | LED3_DRIVE | Digital output, MOSFET gate |
| GPIO10 | SENSOR1 | Interrupt input from comparator |
| GPIO11 | SENSOR2 | Interrupt input from comparator |
| GPIO12 | SENSOR3 | Interrupt input from comparator |
| GPIO13 | SENSOR4 | Interrupt input from comparator |
| GPIO16 | SENSOR5 | Interrupt input from comparator |
| GPIO18 | SENSOR6 | Interrupt input from comparator |
| GPIO17 | I2C SDA | Shared bus for DACs |
| GPIO01 | I2C SCL | Shared bus for DACs |
| GPIO02, 03 | SPARE | Reserved for debug/expansion |

---

## 5. Verified Bill of Materials

All components verified from datasheets and selected from LCSC for single-source ordering with JLCPCB assembly.

### 5.1 Active Components

| Component | Part Number | LCSC # | Qty |
|-----------|-------------|--------|-----|
| Photodiode | VEMD2020X01 | **C3210968** | 6 |
| IR LED | P2835P1VIRB8G025-940 | **C22466183** | 3 |
| N-MOSFET | AO3400-ED | **C4748722** | 3 |
| Quad Comparator | LM339 | **C2829428** | 2 |
| 4-Ch 12-bit DAC | MCP4728 | **C108207** | 2 |

### 5.2 Connectors

| Component | Part Number | LCSC # | Qty |
|-----------|-------------|--------|-----|
| FPC 6P 1mm | 1.0K-ES-6PWB-RL | **C51901482** | 1 |
| FPC 8P 1mm | F-FPC1M08P-A310 | **C132510** | 1 |

*Note: Both FPC connectors are 1mm pitch, slide lock, top contact, 0.3mm FFC thickness.*

### 5.3 Passive Components

| Component | Value | Package | Qty | LCSC # |
|-----------|-------|---------|-----|--------|
| LED current limit | 18Ω 1W | 2512 | 3 | (standard) |
| MOSFET gate | 100Ω | 0603 | 3 | (standard) |
| Photodiode load | 10kΩ | 0603 | 6 | (standard) |
| Comparator pull-up | 10kΩ | 0603 | 6 | (standard) |
| Bulk decoupling | 100µF 16V | 6.3×5.4mm | 1 | **C2887276** |
| Local decoupling | 100nF | 0603 | 7 | (standard) |

---

## 6. System Power Budget

| Subsystem | Peak | Average |
|-----------|------|---------|
| IR LEDs (3×, staggered) | 167mA | ~1mA |
| Sensor circuit (comparators, DACs) | ~8mA | ~8mA |
| ESP32-S3 + display (estimate) | ~150mA | ~80mA |
| **Total** | **<350mA** | **<100mA** |

Well within the 1A budget. With an 18650 battery (2500–3000mAh typical), expect 25–30+ hours of continuous operation.

---

## 7. Next Steps

1. ~~Component selection complete~~ — All parts verified from datasheets
2. ~~BOM finalized~~ — LCSC part numbers confirmed
3. ~~GPIO assignment verified~~ — Based on T-Display-S3 actual pinout
4. **Create KiCad schematic** — Main board schematic with all subcircuits
5. **Design flex PCB layouts** — LED and sensor flex boards
6. **Prototype and test** — Validate detection at target distances and speeds

---

## 8. Open Questions

- ESD protection on sensor inputs? (TVS diodes or series resistors)
- I2C addresses for two MCP4728 ICs — verify address pin configuration
- Custom footprints needed for: T-Display-S3 module, VEMD2020X01, IR LED 2835, FPC connectors

---

## Appendix: EDA File Download Commands

```bash
# Install the conversion tool
pip install easyeda2kicad

# Download all components (symbols, footprints, 3D models)
easyeda2kicad --full --lcsc_id=C3210968 --output ~/Documents/KiCad/hoop_detection   # Photodiode
easyeda2kicad --full --lcsc_id=C22466183 --output ~/Documents/KiCad/hoop_detection  # IR LED
easyeda2kicad --full --lcsc_id=C4748722 --output ~/Documents/KiCad/hoop_detection   # MOSFET
easyeda2kicad --full --lcsc_id=C2829428 --output ~/Documents/KiCad/hoop_detection   # LM339
easyeda2kicad --full --lcsc_id=C108207 --output ~/Documents/KiCad/hoop_detection    # MCP4728
easyeda2kicad --full --lcsc_id=C51901482 --output ~/Documents/KiCad/hoop_detection  # FPC 6P
easyeda2kicad --full --lcsc_id=C132510 --output ~/Documents/KiCad/hoop_detection    # FPC 8P
easyeda2kicad --full --lcsc_id=C2887276 --output ~/Documents/KiCad/hoop_detection   # 100µF Cap
```

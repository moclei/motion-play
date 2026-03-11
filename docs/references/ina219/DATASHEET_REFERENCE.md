# INA219 Datasheet Reference

> Source: TI INA219 (SBOS448G, August 2008, Rev. December 2015)

## 1. Overview

**Part Number:** INA219 (A and B grades; B has tighter accuracy specs)

**Description:** Zero-drift, bidirectional current/power monitor with I2C/SMBus interface. Measures shunt voltage drop and bus supply voltage, computes current and power via internal calibration engine.

**Key Features:**
- High-side or low-side current sensing
- Bus voltage sensing: 0–26V
- I2C/SMBus interface, up to 2.56 MHz (high-speed mode)
- 16 programmable I2C addresses via A0/A1 pins
- Programmable PGA gain (±40mV to ±320mV shunt range)
- Direct current (A) and power (W) register readouts when calibrated
- Packages: SOT-23-8 (1.63×2.90mm) and SOIC-8 (3.91×4.90mm)

## 2. Absolute Maximum Ratings

| Parameter | Min | Max | Unit |
|-----------|-----|-----|------|
| VS supply voltage | — | 6 | V |
| Differential input (VIN+ − VIN−) | −26 | 26 | V |
| Common-mode (VIN+, VIN−) | −0.3 | 26 | V |
| SDA | GND − 0.3 | 6 | V |
| SCL | GND − 0.3 | VS + 0.3 | V |
| Input current into any pin | — | 5 | mA |
| Operating temperature | −40 | 125 | °C |

The input pins tolerate 0–26V regardless of whether VS is powered.

## 3. Key Electrical Characteristics

(At VS = 3.3V, TA = 25°C)

### Shunt Voltage (Current Sense Input)

| PGA Setting | Full-Scale Range | Resolution (LSB) |
|-------------|-----------------|-------------------|
| /1 | ±40 mV | 10 µV |
| /2 | ±80 mV | 10 µV |
| /4 | ±160 mV | 10 µV |
| /8 (default) | ±320 mV | 10 µV |

### Bus Voltage

| BRNG Setting | Full-Scale Range | Resolution (LSB) |
|--------------|-----------------|-------------------|
| 1 (default) | 0–32V | 4 mV |
| 0 | 0–16V | 4 mV |

### Accuracy

| Parameter | INA219A | INA219B |
|-----------|---------|---------|
| Current measurement error (25°C) | ±0.5% max | ±0.3% max |
| Current error over temp (−25 to 85°C) | ±1% | ±0.5% |
| Bus voltage error (25°C) | ±0.5% max | ±0.5% max |
| Shunt offset (PGA /1) | ±100 µV max | ±50 µV max |
| ADC basic resolution | 12 bits | 12 bits |

### Power Supply

| Parameter | Typ | Max | Unit |
|-----------|-----|-----|------|
| Operating range | 3–5.5 | — | V |
| Quiescent current | 0.7 | 1.0 | mA |
| Power-down current | 6 | 15 | µA |

## 4. Pin Configuration

SOT-23-8 (DCN package):

| Pin | Name | I/O | Function |
|-----|------|-----|----------|
| 1 | IN+ | Analog Input | Positive shunt voltage. Connect to supply side of shunt resistor. |
| 2 | IN− | Analog Input | Negative shunt voltage. Bus voltage is measured from this pin to GND. |
| 3 | GND | Power | Ground |
| 4 | VS | Power | Supply voltage, 3V to 5.5V |
| 5 | SCL | Digital Input | I2C clock |
| 6 | SDA | Digital I/O | I2C data (open-drain) |
| 7 | A0 | Digital Input | Address configuration pin |
| 8 | A1 | Digital Input | Address configuration pin |

SOIC-8 (D package) has reversed pin numbering: pin 1 = A1, pin 8 = IN+. Check package drawing.

## 5. I2C Address Configuration

A0 and A1 can each be connected to GND, VS+, SDA, or SCL, giving 16 possible addresses.

| A1 | A0 | 7-bit Address (binary) | Hex |
|----|----|-----------------------|-----|
| GND | GND | 1000000 | **0x40** |
| GND | VS+ | 1000001 | 0x41 |
| GND | SDA | 1000010 | 0x42 |
| GND | SCL | 1000011 | 0x43 |
| VS+ | GND | 1000100 | 0x44 |
| VS+ | VS+ | 1000101 | 0x45 |
| ... | ... | ... | ... |

**For our application: A0 = GND, A1 = GND → address 0x40.**

Address pins are sampled at the start of every I2C communication.

## 6. Shunt Resistor Selection (0–6A VSYS)

### Requirements
- Current range: ~0.5A to 6A (unidirectional, high-side)
- VSYS rail: 3.0–4.5V (battery powered — voltage drop matters)

### Trade-Off Analysis

| PGA | Range | Max R_shunt (6A) | P_dissipation (6A) | V_drop (6A) | Current Resolution |
|-----|-------|-------------------|--------------------|--------------|--------------------|
| /1 | ±40mV | 6.67 mΩ | 0.24W | 40mV | 1.5 mA/LSB |
| /2 | ±80mV | 13.3 mΩ | 1.07W | 80mV | 0.75 mA/LSB |
| /4 | ±160mV | 26.7 mΩ | 4.27W | 160mV | — (impractical) |
| /8 | ±320mV | 53.3 mΩ | 19.2W | 320mV | — (impractical) |

PGA /4 and /8 are ruled out — voltage drop and power dissipation are unacceptable at 6A on a 3–4.5V rail.

### Recommended Options (Standard Shunt Values)

**Option A: 10 mΩ shunt, PGA /2 (±80mV) — BEST RESOLUTION**
- Max measurable current: 80mV / 10mΩ = 8A (33% headroom)
- Power dissipation at 6A: I²R = 36 × 0.01 = **0.36W**
- Voltage drop at 6A: 60mV (2% of 3.0V min — acceptable)
- Current resolution: 10µV / 10mΩ = **1 mA/LSB**
- Package requirement: 2512 or 2010 rated ≥0.5W

**Option B: 5 mΩ shunt, PGA /1 (±40mV) — LOWEST LOSS**
- Max measurable current: 40mV / 5mΩ = 8A (33% headroom)
- Power dissipation at 6A: I²R = 36 × 0.005 = **0.18W**
- Voltage drop at 6A: 30mV (1% of 3.0V min — very good)
- Current resolution: 10µV / 5mΩ = **2 mA/LSB**
- Package requirement: 1206 rated ≥0.25W, or 2512 for margin

### Recommendation

**Use 10 mΩ with PGA /2** for the best measurement resolution (1 mA/LSB). The 0.36W dissipation and 60mV drop are acceptable for a battery monitoring application. If board space is tight or the 60mV drop is problematic at low battery (3.0V), fall back to 5 mΩ with PGA /1.

## 7. Bus Voltage Measurement

- Measured at the IN− pin with respect to GND (load-side voltage)
- BRNG = 1 (default): 0–32V range, 4 mV/LSB
- BRNG = 0: 0–16V range, 4 mV/LSB
- Bus Voltage register bits [15:3] contain the voltage data (must shift right by 3 bits)
- Bit 1 (CNVR): Conversion Ready flag
- Bit 0 (OVF): Math Overflow flag

For our 3.0–4.5V VSYS rail, use BRNG = 0 (16V) for a closer full-scale match, or leave at default 32V — both work fine. Resolution is 4 mV/LSB either way.

## 8. Register Map Summary

| Addr | Name | Type | Reset | Description |
|------|------|------|-------|-------------|
| 0x00 | Configuration | R/W | 0x399F | PGA gain, bus voltage range, ADC resolution/averaging, operating mode, reset |
| 0x01 | Shunt Voltage | R | — | Measured shunt voltage. LSB = 10 µV. Signed (2's complement). |
| 0x02 | Bus Voltage | R | — | Measured bus voltage. Bits [15:3] = voltage, LSB = 4 mV. Bits [1:0] = status. |
| 0x03 | Power | R | 0x0000 | Computed power. Only valid after calibration register is programmed. |
| 0x04 | Current | R | 0x0000 | Computed current. Only valid after calibration register is programmed. |
| 0x05 | Calibration | R/W | 0x0000 | Programs full-scale current range and LSB for current/power registers. |

### Configuration Register (0x00) Bit Fields

| Bits | Field | Default | Purpose |
|------|-------|---------|---------|
| 15 | RST | 0 | Write 1 to reset all registers (self-clearing) |
| 13 | BRNG | 1 | Bus voltage range: 0 = 16V, 1 = 32V |
| 12:11 | PG | 11 | PGA gain: 00 = /1 (±40mV), 01 = /2, 10 = /4, 11 = /8 (±320mV) |
| 10:7 | BADC | 0011 | Bus ADC resolution/averaging (12-bit default, 532 µs) |
| 6:3 | SADC | 0011 | Shunt ADC resolution/averaging (12-bit default, 532 µs) |
| 2:0 | MODE | 111 | Operating mode (continuous shunt + bus default) |

### ADC Resolution/Averaging Options

| Setting | Mode | Conversion Time |
|---------|------|-----------------|
| 9-bit | Single | 84 µs |
| 10-bit | Single | 148 µs |
| 11-bit | Single | 276 µs |
| 12-bit | Single | 532 µs |
| 2 samples | Averaging | 1.06 ms |
| 4 samples | Averaging | 2.13 ms |
| 128 samples | Averaging | 68.10 ms |

## 9. Calibration Register Programming

### Equations

```
Current_LSB = Max_Expected_Current / 2^15

Cal = trunc(0.04096 / (Current_LSB × R_SHUNT))

Power_LSB = 20 × Current_LSB
```

### Example: 10 mΩ Shunt, 8A Max

1. Current_LSB (min) = 8 / 32768 = 244 µA → round to **1 mA** for simplicity
2. Cal = trunc(0.04096 / (0.001 × 0.01)) = trunc(4096) = **4096 (0x1000)**
3. Power_LSB = 20 × 1 mA = **20 mW**

Reading current: `Current_A = Current_Register × 0.001`
Reading power: `Power_W = Power_Register × 0.020`

### Example: 5 mΩ Shunt, 8A Max

1. Current_LSB = round up to **0.5 mA**
2. Cal = trunc(0.04096 / (0.0005 × 0.005)) = trunc(16384) = **16384 (0x4000)**
3. Power_LSB = 20 × 0.5 mA = **10 mW**

### Register Computation (Internal)

```
Current_Register = (Shunt_Voltage_Register × Calibration_Register) / 4096
Power_Register = (Current_Register × Bus_Voltage_Register) / 5000
```

Current and Power registers remain 0 until the Calibration register is written.

## 10. Maximum Bus Voltage — VSYS Compatibility

VSYS range: 3.0–4.5V. INA219 bus voltage input range: 0–26V (absolute max at IN− pin).

**This is well within spec.** The INA219 operates with common-mode voltages from 0–26V on its inputs regardless of VS supply voltage. No concerns here.

The device VS supply (3–5.5V) can be powered from the same 3.3V logic rail used by the ESP32.

## 11. Connection Diagram — High-Side Current Sensing

```
VSYS (from battery/regulator)
    │
    ├──── R_SHUNT ────┐
    │                  │
    │  ┌───────────┐   │
    │  │  INA219   │   │
    └──┤ IN+   VS ├───┤── 3.3V (logic supply)
       │           │   │
    ┌──┤ IN−  GND ├───┤── GND
    │  │           │   │
    │  │  SCL  A0 ├───┤── GND (address = 0x40)
    │  │  SDA  A1 ├───┤── GND
    │  └───────────┘
    │
    └──── To load (ESP32, sensors, etc.)
```

- IN+ on the supply side of the shunt (higher voltage)
- IN− on the load side (bus voltage measured from here to GND)
- 0.1 µF bypass cap on VS to GND, as close to pins as possible
- Use Kelvin (4-wire) connection to the shunt resistor for accuracy
- Optional: 10Ω series resistors on IN+/IN− for ESD/dV/dt protection (no accuracy impact)
- I2C pull-ups (3.3kΩ typical) only needed if not already present on the bus

## Quick Reference for Our Application

| Parameter | Value |
|-----------|-------|
| I2C Address | **0x40** (A0=GND, A1=GND) |
| Shunt Resistor | **10 mΩ** (alt: 5 mΩ) |
| PGA Setting | **/2 (±80mV)** (alt: /1 for 5 mΩ) |
| BRNG Setting | 0 or 1 (16V or 32V — either works) |
| Max Measurable Current | 8A |
| Current Resolution | 1 mA/LSB |
| Power at 6A (shunt) | 0.36W |
| Voltage Drop at 6A | 60 mV |
| Calibration Register | 0x1000 (4096) |
| Power LSB | 20 mW |
| VS Supply | 3.3V (from ESP32 logic rail) |
| VSYS Range (3.0–4.5V) | Well within 26V max |

# BQ24195 Datasheet Reference

**Part Number:** BQ24195 (4.5A) / BQ24195L (2.5A)
**Datasheet:** SLUSB97A (October 2012, Revised December 2014)
**Package:** VQFN-24, 4.00 mm × 4.00 mm

## Overview

I2C-controlled single-cell Li-Ion/Li-polymer battery charge management and system power path management device. Integrates all power FETs: input reverse-blocking (RBFET Q1), high-side switching (HSFET Q2), low-side switching (LSFET Q3), and battery disconnect (BATFET Q4) with bootstrap diode. 1.5 MHz switching frequency. NVDC (Narrow VDC) power path architecture keeps system alive with no battery or deeply depleted battery. I2C address: **0x6B**.

Key features:
- Up to 4.5A fast charge (bq24195) or 2.5A (bq24195L)
- 5.1V boost mode output at 2.1A (bq24195) or 1A (bq24195L)
- USB BC1.2 D+/D- detection for automatic input current limit
- Autonomous charging with or without host management
- 92% charge efficiency at 2A, 90% at 4A

## Absolute Maximum Ratings

| Parameter | Min | Max | Unit |
|-----------|-----|-----|------|
| VBUS | -2 | 22 | V |
| PMID | -0.3 | 22 | V |
| BAT, SYS (not switching) | -0.3 | 6 | V |
| SDA, SCL, INT, OTG, ILIM, REGN, TS, CE, D+, D- | -0.3 | 7 | V |
| BTST | -0.3 | 26 | V |
| SW | -2 | 20 | V |
| Junction temperature | -40 | 150 | °C |
| Operating temperature (TA) | -40 | 85 | °C |

**Recommended operating input voltage:** 3.9V to 17V

## Key Electrical Characteristics

| Parameter | Min | Typ | Max | Unit |
|-----------|-----|-----|-----|------|
| Input current limit (I2C register) | 100 | — | 3000 | mA |
| Fast charge current range (bq24195) | 512 | — | 4544 | mA |
| VSYS regulation range | 3.5 | — | 4.35 | V |
| VSYS_MIN (programmable) | 3.0 | — | 3.7 | V |
| VSYS_MIN output (default 3.5V setting) | 3.55 | — | 3.65 | V |
| BATFET on-resistance (RON_BATFET) | — | 12 | 20 | mΩ |
| RBFET on-resistance (VBUS→PMID) | — | 23 | 38 | mΩ |
| HSFET on-resistance (PMID→SW) | — | 30 | 48 | mΩ |
| LSFET on-resistance (SW→PGND) | — | 35 | 51 | mΩ |
| Charge voltage accuracy | — | — | ±0.5 | % |
| Charge current accuracy (25°C) | — | — | ±4 | % |
| Input current regulation accuracy | — | — | ±7.5 | % |
| PWM switching frequency | 1300 | 1500 | 1700 | kHz |
| VBUS UVLO (for active I2C, no battery) | — | 3.6 | — | V |
| Battery depletion threshold | — | 2.4–2.6 | — | V |
| IBAT quiescent (no VBUS, BATFET on) | — | 32 | 55 | µA |
| IBAT quiescent (no VBUS, BATFET off) | — | 12 | 20 | µA |

## Pin Configuration (24-Pin VQFN)

| Pin | Number | Type | Description |
|-----|--------|------|-------------|
| VBUS | 1, 24 | P | Charger input. Internal RBFET source. Decouple with 1µF to PGND close to IC. |
| D+ | 2 | I | USB data positive. BC1.2 detection (DCD + primary detection). |
| D- | 3 | I | USB data negative. BC1.2 detection (DCD + primary detection). |
| STAT | 4 | O (OD) | Charge status. LOW=charging, HIGH=done/disabled, BLINK 1Hz=fault. Pull up via 10kΩ. |
| SCL | 5 | I | I2C clock. Pull up via 10kΩ. Supports up to 400 kHz. |
| SDA | 6 | I/O | I2C data. Pull up via 10kΩ. |
| INT | 7 | O (OD) | Interrupt output. Active-low 256µs pulse on status/fault events. Pull up via 10kΩ. |
| OTG | 8 | I | USB current select (buck) / boost enable (boost). HIGH in buck = 500mA USB limit. |
| CE | 9 | I | Active-low charge enable. Charging enabled when REG01[5:4]=01 AND CE=LOW. Must be pulled high or low. |
| ILIM | 10 | I | Input current limit set by resistor to GND. Regulates pin at 1V. |
| TS1 | 11 | I | NTC thermistor input #1. Biased from REGN via resistor divider. Must short TS1 to TS2. |
| TS2 | 12 | I | NTC thermistor input #2. Must short to TS1. |
| BAT | 13, 14 | P | Battery positive terminal. BATFET connects BAT↔SYS. Decouple with 10µF. |
| SYS | 15, 16 | P | System output. Regulated above VSYS_MIN when VBUS present. |
| PGND | 17, 18 | P | Power ground. Connect to input/output cap ground. |
| SW | 19, 20 | O | Switching node to inductor. Connect 47nF bootstrap cap from SW to BTST. |
| BTST | 21 | P | Bootstrap supply for high-side driver. 47nF cap from BTST to SW. |
| REGN | 22 | P | Internal LDO output (~6V from VBUS, ~4.8V from 5V VBUS). Decouple with 4.7µF 10V. Also biases TS pins. |
| PMID | 23 | P | Mid-rail node. Drain of RBFET and HSFET. Boost mode output. Min cap: 20µF (L) or 60µF. |
| Thermal Pad | — | P | Exposed pad. Must solder to board. Vias to PGND/ground plane. |

## ILIM Resistor — Input Current Limit

The ILIM pin regulates at 1V. A resistor from ILIM to GND sets the hardware maximum input current:

**Formula:** `I_INMAX = KILIM / R_ILIM`

where KILIM = 435 (min) / 485 (typ) / 530 (max) A×Ω.

The actual input current limit is the **lower** of the ILIM setting and the I2C register setting (REG00[2:0]).

| RILIM | Current (typ) | Current (max) |
|-------|---------------|---------------|
| 177Ω | 2.74A | 3.0A |
| 333Ω | 1.46A | 1.59A |
| 353Ω | 1.37A | 1.50A |
| 530Ω | 0.92A | 1.0A |
| 1060Ω | 0.46A | 0.50A |
| **2700Ω (2.7kΩ)** | **~180mA** | **~196mA** |

**Minimum ILIM current: 500mA.** The datasheet states the minimum input current programmable via ILIM pin is 500mA. With R_ILIM = 2.7kΩ, the formula yields ~180–196mA, which is below the 500mA floor. **A 2.7kΩ ILIM resistor effectively clamps input current at the 500mA internal minimum.** The I2C register can further limit below this. If ILIM pin is open (floating above 1V), current is limited to zero. If shorted, only the register controls the limit.

**Monitoring:** V_ILIM is proportional to actual input current: `I_IN = V_ILIM × KILIM / R_ILIM`. For example, V_ILIM = 0.6V with a 2A ILIM setting means actual current is 1.2A.

## Battery-Absent Operation

The BQ24195 is explicitly designed to operate without a battery ("Instant-on Works with No Battery or Deeply Discharged Battery").

**Key behaviors with no battery connected:**

1. **VSYS remains regulated from VBUS.** The NVDC power path regulates SYS above the minimum system voltage, even with battery completely depleted or removed.

2. **VSYS voltage:** Regulated at **VSYS_MIN + 150mV**. With default VSYS_MIN = 3.5V, this gives **~3.65V on SYS** (measured range: 3.55V–3.65V).

3. **When charge is disabled or terminated**, SYS is always regulated at 150mV above VSYS_MIN setting.

4. **Recommended configuration:** Set REG07[5] = 1 (BATFET_Disable) to turn off Q4 when no battery is attached. This disables charging and supplement mode, preventing the charger from trying to charge a non-existent battery.

5. **Load current** is limited by the input current limit (ILIM pin or I2C register, whichever is lower). The converter runs in PFM at light loads for efficiency. System current up to 4.5A (bq24195) or 2.5A (bq24195L) is supported per recommended operating conditions.

6. **During system startup (VSYS < 2.2V):** Input current is forced to 100mA regardless of register/ILIM settings. After SYS rises above 2.2V, the configured current limit applies.

7. **REG08[0] (VSYS_STAT)** goes high when the system is in minimum system voltage regulation.

## Power Path Management

**NVDC Architecture:** BATFET (Q4) separates SYS from BAT. The buck converter regulates SYS from VBUS through PMID.

- When BAT < VSYS_MIN: BATFET operates in LDO mode, SYS = VSYS_MIN + 150mV
- When BAT > VSYS_MIN: BATFET fully on, SYS = BAT + BATFET VDS (~12mΩ × I)

**Dynamic Power Management (DPM):** Monitors input current (IINDPM via REG00[2:0]) and input voltage (VINDPM via REG00[6:3]). When input source is overloaded, charge current is reduced first, then if system load still exceeds input capacity, BATFET turns on for **supplement mode** (system powered by both VBUS and battery).

**Supplement Mode:** BATFET VDS is regulated to minimum 30mV at low current to prevent oscillation. As discharge current increases, gate drive increases until full conduction. BATFET turns off to exit supplement mode when battery falls below depletion threshold.

**PMID:** Connects RBFET drain to HSFET drain. In buck mode, PMID ≈ VBUS - RBFET drop. In boost mode, PMID outputs 5.12V regulated.

## I2C Register Map Summary

**I2C Address:** 0x6B. REG00–REG07 are R/W. REG08–REG0A are read-only.

| Register | Name | Default | Controls |
|----------|------|---------|----------|
| REG00 | Input Source Control | 0x30 | EN_HIZ, VINDPM[3:0] (input voltage DPM, default 4.36V), IINLIM[2:0] (input current limit, default 100mA/500mA) |
| REG01 | Power-On Configuration | 0x1B | Register reset, watchdog reset, CHG_CONFIG[1:0] (charge/OTG mode, default charge), SYS_MIN[2:0] (min sys voltage, default 3.5V) |
| REG02 | Charge Current Control | 0x60 | ICHG[5:0] (fast charge current, default 2048mA), FORCE_20PCT |
| REG03 | Pre-Charge/Term Current | 0x11 | IPRECHG[3:0] (pre-charge, default 256mA), ITERM[3:0] (termination, default 256mA) |
| REG04 | Charge Voltage Control | 0xB2 | VREG[5:0] (charge voltage, default 4.208V), BATLOWV (pre→fast threshold, default 3.0V), VRECHG (recharge threshold, default 100mV) |
| REG05 | Charge Term/Timer | 0x9A | EN_TERM (default on), WATCHDOG[1:0] (default 40s), EN_TIMER (default on), CHG_TIMER[1:0] (default 8hr) |
| REG06 | Thermal Regulation | 0x03 | TREG[1:0] (thermal reg threshold, default 120°C, range 60–120°C) |
| REG07 | Misc Operation Control | 0x4B | DPDM_EN (force D+/D- detect), TMR2X_EN, BATFET_Disable, INT_MASK[1:0] |
| REG08 | System Status (RO) | — | VBUS_STAT[1:0], CHRG_STAT[1:0], DPM_STAT, PG_STAT, THERM_STAT, VSYS_STAT |
| REG09 | Fault (RO) | — | WATCHDOG_FAULT, CHRG_FAULT[1:0], BAT_FAULT, NTC_FAULT[2:0]. Read twice for current state. |
| REG0A | Vendor/Part/Rev (RO) | 0x23 | PN[2:0] = 100 (bq24195). TS_PROFILE, DEV_REG. |

## Boot Sequence and Default Values

1. **POR:** When VBUS or VBAT rises above UVLOZ (~3.6V for VBUS, ~2.3V for VBAT), I2C is active and all registers reset to defaults.
2. **Default mode** starts (REG09[7] = 1). Autonomous charging with defaults:
   - Charge voltage: 4.208V
   - Charge current: 2048mA
   - Pre-charge current: 256mA
   - Termination current: 256mA
   - Safety timer: 8 hours (but 5 hours in default mode)
   - Watchdog: 40 seconds
   - VSYS_MIN: 3.5V
   - VINDPM: 4.36V
   - Thermal regulation: 120°C
3. **Input current limit before I2C config:** Set by D+/D- detection result. USB host → 100mA (OTG LOW) or 500mA (OTG HIGH). Charging port → 1.5A. D+/D- timeout → 100mA.
4. **During startup (VSYS < 2.2V):** Forced to 100mA input current regardless.
5. **Entering host mode:** Any I2C write transitions from default to host mode. Watchdog must be periodically reset (write 1 to REG01[6]) or disabled (REG05[5:4] = 00) to stay in host mode. On watchdog expiry, all registers reset to defaults.

### Default Register Values at POR

| REG | Hex | Binary |
|-----|-----|--------|
| REG00 | 0x30 | 00110000 |
| REG01 | 0x1B | 00011011 |
| REG02 | 0x60 | 01100000 |
| REG03 | 0x11 | 00010001 |
| REG04 | 0xB2 | 10110010 |
| REG05 | 0x9A | 10011010 |
| REG06 | 0x03 | 00000011 |
| REG07 | 0x4B | 01001011 |

## D+/D- Pin Behavior

The BQ24195 uses D+/D- pins for USB BC1.2 source detection. Detection runs automatically at power-up (and can be forced via REG07[7]).

**Detection sequence:**
1. **DCD (Data Contact Detection):** IDP_SRC (7–14µA) on D+, RDM_DWN (14–25kΩ pulldown) on D- for 40ms. Waits for D+ to go LOW (up to 0.5s timeout).
2. **Primary Detection:** VDP_SRC (0.5–0.7V) on D+, IDM_SINK (50–150µA) on D-. If D- is LOW → USB host (SDP). If D- is HIGH → charging port (CDP/DCP).

**When D+ and D- are grounded (tied to GND):**
- DCD completes immediately (D+ is already LOW)
- Primary detection: VDP_SRC drives into ground on D+, D- is grounded (LOW)
- **Result: Detected as USB host (SDP)**, REG08[7:6] = 01
- Input current limit: **100mA** (OTG LOW) or **500mA** (OTG HIGH)
- Host must write REG00[2:0] after boot to set the desired input current limit

| Detection Result | OTG | Current Limit | REG08[7:6] |
|-----------------|-----|---------------|-------------|
| DCD timeout (D+/D- floating) | — | 100mA | 00 |
| USB host (SDP) — **D+/D- grounded** | LOW | 100mA | 01 |
| USB host (SDP) — **D+/D- grounded** | HIGH | 500mA | 01 |
| Charging port (CDP/DCP) | — | 1.5A | 10 |

**For designs without USB data lines:** After detection completes, the host must write the actual input current limit to REG00[2:0] via I2C. With D+/D- grounded and OTG LOW, the boot-time limit is only 100mA until I2C reconfigures it.

## Thermal Considerations

- **Thermal regulation threshold:** Programmable via REG06[1:0]. Default 120°C (options: 60°C, 80°C, 100°C, 120°C). When TJ exceeds this, charge current is reduced.
- **Thermal shutdown:** 160°C rising, 30°C hysteresis (resets at 130°C). Converter stops. Fault in REG09[5:4] = 10.
- **Thermal resistance:** θJA = 32.2°C/W, θJB = 9.1°C/W, θJC(bottom) = 2.2°C/W
- **Layout critical:** Solder exposed thermal pad. Use vias to PGND/ground plane. Place input caps close to PMID/PGND. Minimize SW trace copper area.

## Support Component Requirements

| Component | Value | Rating | Notes |
|-----------|-------|--------|-------|
| C_VBUS (VBUS→PGND) | 1µF | 25V+ | Ceramic X7R/X5R. Close to IC. |
| C_PMID (PMID→PGND) | 20µF min (L) / **60µF min** | 25V+ | Ceramic X7R/X5R. Main input filter. |
| C_BAT (BAT→GND) | 10µF | 6V+ | Close to BAT pins. |
| C_SYS (SYS→GND) | 10µF | 6V+ | Total output ~20µF recommended (with inductor 2.2µH). |
| C_BTST (BTST→SW) | 47nF (0.047µF) | — | Bootstrap capacitor. |
| C_REGN (REGN→GND) | 4.7µF | 10V | Close to IC. |
| L1 (inductor, SW→SYS) | 2.2µH | — | ISAT > ICHG + ½×IRIPPLE. 1.5MHz optimized. |

**Output LC resonance:** Target 15–25 kHz. With L=2.2µH, C_OUT≈20µF achieves this.

## NTC Temperature Monitoring

TS1 and TS2 pins **must be shorted together**. Connect a 103AT NTC thermistor (10kΩ at 25°C) with resistor divider from REGN.

**Divider network (for 0°C to 45°C window):**
- RTH = 10kΩ NTC (103AT on battery pack)
- RT1 = 5.52kΩ (REGN to TS junction)
- RT2 = 31.23kΩ (TS junction to GND)

**Thresholds (as percentage of VREGN):**
| Condition | Threshold | Action |
|-----------|-----------|--------|
| Cold (VLTF) | 73–74% | Suspend charge |
| Hot (VHTF) | 46.6–48.8% | Suspend charge initiation |
| Cut-off (VTCO) | 44.2–45.2% | Suspend during charge |

Deglitch time for out-of-range detection: 10ms. Faults reported in REG09[2:0] with INT pulse.

**If NTC is not used:** TS pins must still be biased within the valid window (between VTCO and VLTF thresholds) using a fixed resistor divider, or charging will be suspended.

## I2C Input Current Limit Register Values

Quick reference for REG00[2:0]:

| REG00[2:0] | Current Limit |
|------------|---------------|
| 000 | 100mA |
| 001 | 150mA |
| 010 | 500mA |
| 011 | 900mA |
| 100 | 1.2A |
| 101 | 1.5A |
| 110 | 2.0A |
| 111 | 3.0A |

## VSYS_MIN Register Values

Quick reference for REG01[3:1]:

| REG01[3:1] | VSYS_MIN |
|------------|----------|
| 000 | 3.0V |
| 001 | 3.1V |
| 010 | 3.2V |
| 011 | 3.3V |
| 100 | 3.4V |
| 101 | 3.5V (default) |
| 110 | 3.6V |
| 111 | 3.7V |

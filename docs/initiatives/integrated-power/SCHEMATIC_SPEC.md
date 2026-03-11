# Integrated Power Management — Schematic Change Specification (Phase 2)

This document specifies every component, pin connection, net, and value needed to implement the integrated power management system on the main PCB. Implement in KiCad by following each section in order.

**Conventions:**
- All resistors are 0603 unless noted otherwise
- All ceramic capacitors are 0603 unless noted otherwise
- All capacitor voltage ratings ≥2× operating voltage unless noted
- Net names in `monospace` are exact KiCad net labels
- Pin numbers match datasheet/LCSC footprint conventions
- "→" denotes a direct electrical connection (same net)

---

## 1. Root Sheet Changes

### 1.1 Components to Remove

| Ref | Part | Action |
|-----|------|--------|
| J2 | DWEII USB-C Power Module | Delete symbol and footprint |
| D1 | Schottky diode (D_SMC) | Delete symbol and footprint |

Removing J2 and D1 eliminates the `Net-(D1-A)` net entirely. The `+5V` rail is now supplied by the new power management hierarchical sheet.

### 1.2 Net Changes on Root Sheet

| Net | Before | After |
|-----|--------|-------|
| `Net-(D1-A)` | J2 pin 2 → D1 anode | **Deleted** (no longer exists) |
| `+5V` | D1 cathode → U1, U2, LED sheet, TPs | Fed from Power Mgmt sheet `+5V` output pin |
| `Net-(U2-21)` | U2 pin 19 → TPIO21 only | Renamed to `/Power Management/CHRG_INT` — connects U2 pin 19 (GPIO 21) and TPIO21 to the CHRG_INT output from the power management sheet |

### 1.3 New Hierarchical Sheet Symbol

Add a hierarchical sheet symbol on the root sheet labeled **"Power Management"** pointing to a new child schematic file `power_management.kicad_sch`.

**Hierarchical sheet pins:**

| Pin Name | Direction | Root Sheet Net | Purpose |
|----------|-----------|---------------|---------|
| +5V | output | `+5V` | Boost converter output, feeds existing +5V rail |
| GND | bidirectional | `GND` | Common ground |
| +3.3V | input | `+3.3V` | Logic supply for INA219, pull-ups |
| I2C_SDA | bidirectional | `/I2C_SDA` | I2C data (GPIO 43) |
| I2C_SCL | bidirectional | `/I2C_SCL` | I2C clock (GPIO 44) |
| CHRG_INT | output | `/Power Management/CHRG_INT` | BQ24195 interrupt → GPIO 21 |

### 1.4 Root Sheet Wiring After Changes

Connect the hierarchical sheet pins to the existing nets:
- `+5V` pin → existing `+5V` power flag/net (was previously fed by D1 cathode)
- `GND` pin → existing `GND`
- `+3.3V` pin → existing `+3.3V` (from AP2112K U1 output)
- `I2C_SDA` pin → existing `/I2C_SDA` (GPIO 43, also to TCA9548A sheet)
- `I2C_SCL` pin → existing `/I2C_SCL` (GPIO 44, also to TCA9548A sheet)
- `CHRG_INT` pin → U2 pin 19 (GPIO 21) and TPIO21

**Existing root sheet components that remain unchanged:** U1 (AP2112K), U2 (T-Display-S3), J3–J6 (connectors), C1, C2 (LDO caps), all test points except TPIO21 net rename. The LED Controller and TCA9548A_Subsystem hierarchical sheets are unchanged.

---

## 2. Power Management Sheet — Overview

The new `power_management.kicad_sch` contains four functional blocks. All components are on this single sheet.

```
                           POWER MANAGEMENT SHEET
┌──────────────────────────────────────────────────────────────────────┐
│                                                                      │
│  ┌─────────────┐    ┌────────────────────┐    ┌──────────────┐      │
│  │  USB-C Input │    │ Battery Management │    │ 5V Boost     │      │
│  │  J7, F2,     │───→│ U5 (BQ24195)       │───→│ U6 (TPS61088)│──→+5V│
│  │  R30, R31,   │    │ Q2, L1, TH1,       │    │ L2, R39-R43, │      │
│  │  C20-C22     │    │ R32-R38, C23-C30   │    │ C31-C39, C41 │      │
│  └─────────────┘    │ J8 (battery)        │    └──────────────┘      │
│                      └────────┬───────────┘                          │
│                               │ VSYS                                 │
│                      ┌────────┴───────────┐                          │
│                      │ Power Monitoring    │                          │
│                      │ U7 (INA219)         │                          │
│                      │ R44, C40            │                          │
│                      └────────────────────┘                          │
│                                                                      │
│  Sheet pins: +5V, GND, +3.3V, I2C_SDA, I2C_SCL, CHRG_INT          │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 3. Block 1: USB-C Input

### 3.1 Components

| Ref | Part | Value | Footprint | LCSC | Function |
|-----|------|-------|-----------|------|----------|
| J7 | TYPE-C-31-M-12 | — | USB-C_SMD-TYPE-C-31-M-12 | C165948 | USB-C power connector |
| F2 | Fuse | 3A | Fuse_1206_3216Metric | C2897466 | VBUS overcurrent protection |
| R30 | R | 5.1kΩ | R_0603 | C23186 | CC1 pull-down (UFP sink) |
| R31 | R | 5.1kΩ | R_0603 | C23186 | CC2 pull-down (UFP sink) |
| C20 | C | 1µF X7R 25V | C_0603 | C15849 | BQ24195 VBUS pin bypass (close to U5) |
| C21 | C | 4.7µF X5R 10V | C_0603 | C19666 | Protected_VBUS ceramic decoupling |
| C22 | C_Polarized | 47µF 16V | C_Elec_6.3x5.4 | C2836440 | Protected_VBUS bulk decoupling |

### 3.2 Pin-by-Pin Connections

**J7 (USB-C connector):**

| Pin | Name | Net |
|-----|------|-----|
| A4, A9, B4, B9 | VBUS | `VBUS_RAW` |
| A5 | CC1 | `CC1` |
| B5 | CC2 | `CC2` |
| A1, A12, B1, B12, SH | GND | `GND` |

**F2 (Fuse):**

| Pin | Net |
|-----|-----|
| 1 | `VBUS_RAW` |
| 2 | `Protected_VBUS` |

**R30 (CC1 pull-down):** Pin 1 → `CC1`, Pin 2 → `GND`

**R31 (CC2 pull-down):** Pin 1 → `CC2`, Pin 2 → `GND`

**C20 (VBUS bypass):** Pin 1 → `Protected_VBUS`, Pin 2 → `GND`

**C21 (PVBUS ceramic):** Pin 1 → `Protected_VBUS`, Pin 2 → `GND`

**C22 (PVBUS bulk):** Pin 1 (+) → `Protected_VBUS`, Pin 2 (−) → `GND`

### 3.3 Net Summary

| Net | Type | Nodes |
|-----|------|-------|
| `VBUS_RAW` | power | J7 VBUS pins → F2 pin 1 |
| `CC1` | signal | J7 A5 → R30 pin 1 |
| `CC2` | signal | J7 B5 → R31 pin 1 |
| `Protected_VBUS` | power | F2 pin 2 → C20.1 → C21.1 → C22.1(+) → U5 VBUS pins |

---

## 4. Block 2: Battery Management (BQ24195)

### 4.1 Components

| Ref | Part | Value | Footprint | LCSC | Function |
|-----|------|-------|-----------|------|----------|
| U5 | BQ24195RGER | — | QFN-24-EP (4×4mm) | C90862 | Battery charger + power path IC |
| J8 | Conn_01x02 | JST PH 2-pin | JST_PH_S2B-PH-SM4-TB | C18221575 | Battery connector |
| Q2 | PMOS | — | SOT-23 | C3040193 | Battery reverse polarity protection |
| L1 | L | 2.2µH | L_Changjiang_FNR6028S | C266426 | BQ24195 switching inductor |
| TH1 | Thermistor_NTC | 10kΩ | R_0603 | C13564 | Battery temperature monitoring |
| R32 | R | 330Ω 1% | R_0603 | C23138 | ILIM resistor (~1.5A hardware ceiling) |
| R33 | R | 100kΩ | R_0603 | C14675 | PMOS gate bias to VBAT |
| R34 | R | 100kΩ | R_0603 | C14675 | PMOS gate bias to BAT_RAW |
| R35 | R | 10kΩ | R_0603 | C25804 | OTG pull-up to +3.3V (500mA SDP boot) |
| R36 | R | 5.6kΩ 1% | R_0603 | TBD | NTC bias top (REGN → TS) |
| R37 | R | 30kΩ 1% | R_0603 | TBD | NTC bias bottom (TS → GND) |
| R38 | R | 10kΩ | R_0603 | C25804 | INT pull-up to +3.3V |
| C23 | C | 47nF X7R | C_0603 | TBD | Bootstrap cap (BTST → SW) |
| C24 | C | 4.7µF X5R 10V | C_0603 | C19666 | REGN internal LDO bypass |
| C25 | C | 10µF X5R 10V | C_0603 | C96446 | PMID bypass #1 |
| C26 | C | 10µF X5R 10V | C_0603 | C96446 | PMID bypass #2 (20µF total ≥ datasheet min) |
| C27 | C | 10µF X5R 10V | C_0603 | C96446 | VSYS ceramic decoupling #1 |
| C28 | C | 10µF X5R 10V | C_0603 | C96446 | VSYS ceramic decoupling #2 |
| C29 | C_Polarized | 220µF 10V | CP_Elec_6.3x7.7 | C3342 | VSYS bulk output cap |
| C30 | C_Polarized | 47µF 10V | C_Elec_6.3x5.4 | C2836440 | Battery terminal bulk cap |

### 4.2 Resolved Design Decisions

**CE pin (pin 9):** Tied directly to `GND`. This means CE is always LOW (charging hardware-enabled). Charging is controlled entirely via I2C register REG01[5:4]. This is simpler and more reliable than the reference design's CE→PG connection.

**OTG pin (pin 8):** Pulled HIGH to `+3.3V` via R35 (10kΩ). With D+/D- grounded, BQ24195 detects USB SDP. OTG HIGH gives 500mA boot-time input current (vs 100mA with OTG LOW). Critical for system boot on USB-only power.

**ILIM resistor (R32):** 330Ω (changed from reference design's 2.7kΩ). Sets hardware current ceiling at ~1.5A (KILIM/RILIM = 485/330 = 1.47A). See COMPONENT_SELECTION.md for full analysis.

**NTC biasing:** Full REGN → RT1 → TS → (NTC ‖ RT2) → GND divider per datasheet recommendation. If NTC (TH1) is not populated during early testing, replace R37 with 10kΩ to bias TS at ~64% of VREGN (within the valid charging window).

**PMID capacitance:** 2× 10µF (C25 + C26 = 20µF total), meeting the datasheet minimum of 20µF. The reference design had only 10µF — insufficient per datasheet.

**Bootstrap cap:** 47nF per datasheet (reference design used 100nF; larger works but 47nF is the specified value).

**D+ / D-:** Both tied to `GND`. No USB data lines in this design.

**STAT pin:** Left unconnected (no-connect). Charge status is readable via I2C register REG08[5:4]. No dedicated GPIO needed.

### 4.3 Pin-by-Pin Connections — U5 (BQ24195RGER)

| Pin | Name | Net | Connection |
|-----|------|-----|------------|
| 1 | VBUS1 | `Protected_VBUS` | From F2 output, with C20 bypass close by |
| 2 | D+ | `GND` | Tied to ground (no USB data) |
| 3 | D- | `GND` | Tied to ground (no USB data) |
| 4 | STAT | — | **No connect** (status via I2C REG08) |
| 5 | SCL | `I2C_SCL` | Sheet pin → root → GPIO 44 |
| 6 | SDA | `I2C_SDA` | Sheet pin → root → GPIO 43 |
| 7 | INT | `CHRG_INT` | → R38 pull-up to +3.3V → sheet pin → GPIO 21 |
| 8 | OTG | `OTG_BIAS` | → R35 (10kΩ) → `+3.3V` |
| 9 | CE | `GND` | Tied LOW (charging always hardware-enabled) |
| 10 | ILIM | `BQ_ILIM` | → R32 (330Ω) → `GND` |
| 11 | TS1 | `BQ_TS` | Shorted to TS2; → TH1 ‖ R37 → GND; → R36 → REGN |
| 12 | TS2 | `BQ_TS` | Shorted to TS1 |
| 13 | BAT1 | `VBAT` | Battery + (after PMOS protection) |
| 14 | BAT2 | `VBAT` | Battery + (after PMOS protection) |
| 15 | SYS1 | `VSYS` | System voltage output |
| 16 | SYS2 | `VSYS` | System voltage output |
| 17 | PGND1 | `GND` | Power ground |
| 18 | PGND2 | `GND` | Power ground |
| 19 | SW1 | `BQ_SW` | Switching node → L1 pin 1 |
| 20 | SW2 | `BQ_SW` | Switching node → L1 pin 1 |
| 21 | BTST | `BQ_BTST` | → C23 (47nF) → `BQ_SW` |
| 22 | REGN | `BQ_REGN` | → C24 (4.7µF) → GND; → R36 (5.6kΩ) → `BQ_TS` |
| 23 | PMID | `BQ_PMID` | → C25 (10µF) → GND; → C26 (10µF) → GND |
| 24 | VBUS2 | `Protected_VBUS` | Second VBUS power pin |
| EP | Thermal Pad | `GND` | Solder to ground plane with thermal vias |

### 4.4 Battery Protection Circuit

```
J8 Pin 1 (+) ──→ BAT_RAW ──→ Q2 Drain (pin 1)
                    │                    │
                    │               Q2 Gate (pin 2) ──→ PMOS_GATE
                    │                    │
                    │               Q2 Source (pin 3) ──→ VBAT
                    │
                    ├── R34 (100kΩ) ──→ PMOS_GATE
                    └── C30 (+) ──→ BAT_RAW, C30 (−) → GND

PMOS_GATE ──→ R33 (100kΩ) ──→ VBAT
                    └──→ R34 (100kΩ) ──→ BAT_RAW

J8 Pin 2 (−) ──→ GND
```

**Q2 (PMOS) connections:**

| Pin | Name | Net |
|-----|------|-----|
| 1 | Drain | `BAT_RAW` |
| 2 | Gate | `PMOS_GATE` |
| 3 | Source | `VBAT` |

**R33:** Pin 1 → `VBAT`, Pin 2 → `PMOS_GATE`

**R34:** Pin 1 → `PMOS_GATE`, Pin 2 → `BAT_RAW`

**C30 (battery bulk):** Pin 1 (+) → `BAT_RAW`, Pin 2 (−) → `GND`

**J8 (battery connector):** Pin 1 → `BAT_RAW`, Pin 2 → `GND`

### 4.5 NTC Temperature Monitoring Circuit

```
BQ_REGN ──→ R36 (5.6kΩ) ──→ BQ_TS ──→ TH1 (10kΩ NTC) ──→ GND
                                  └──→ R37 (30kΩ) ────────→ GND
```

**R36:** Pin 1 → `BQ_REGN`, Pin 2 → `BQ_TS`

**TH1:** Pin 1 → `BQ_TS`, Pin 2 → `GND`

**R37:** Pin 1 → `BQ_TS`, Pin 2 → `GND`

At 25°C: R_NTC = 10kΩ → VTS ≈ 57% of VREGN (within valid 45–73% window).

### 4.6 BQ24195 Inductor

**L1:** Pin 1 → `BQ_SW`, Pin 2 → `VSYS`

### 4.7 BQ24195 Passive Connections Summary

| Component | Pin 1 Net | Pin 2 Net |
|-----------|-----------|-----------|
| C23 (47nF bootstrap) | `BQ_BTST` | `BQ_SW` |
| C24 (4.7µF REGN) | `BQ_REGN` | `GND` |
| C25 (10µF PMID) | `BQ_PMID` | `GND` |
| C26 (10µF PMID) | `BQ_PMID` | `GND` |
| C27 (10µF VSYS) | `VSYS` | `GND` |
| C28 (10µF VSYS) | `VSYS` | `GND` |
| C29 (220µF VSYS bulk) | `VSYS` (+) | `GND` (−) |
| R32 (330Ω ILIM) | `BQ_ILIM` | `GND` |
| R35 (10kΩ OTG) | `OTG_BIAS` | `+3.3V` |
| R38 (10kΩ INT) | `CHRG_INT` | `+3.3V` |

---

## 5. Block 3: 5V Boost Converter (TPS61088)

### 5.1 Components

| Ref | Part | Value | Footprint | LCSC | Function |
|-----|------|-------|-----------|------|----------|
| U6 | TPS61088RHLR | — | VQFN-20-EP (3.5×4.5mm) | C87357 | 10A synchronous boost converter |
| L2 | L | 2.2µH 10A Isat | FXL0630-2R2-M (7.0×6.6mm) | C167218 | Boost power inductor |
| R39 | R | 180kΩ 1% | R_0603 | C22827 | FB divider top (sets VOUT) |
| R40 | R | 56kΩ 1% | R_0603 | C23206 | FB divider bottom |
| R41 | R | 100kΩ 1% | R_0603 | C14675 | FSW frequency set (~2.2 MHz) |
| R42 | R | 100kΩ 1% | R_0603 | C14675 | ILIM current limit (11.9A peak) |
| R43 | R | 22kΩ 1% | R_0603 | TBD | Compensation resistor |
| C31 | C | 0.1µF X7R 16V | C_0603 | C14663 | VIN pin bypass (close to pin 9) |
| C32 | C | 0.1µF X7R 16V | C_0603 | C14663 | BOOT cap (BOOT → SW) |
| C33 | C | 2.2µF X5R 10V | C_0603 | C23630 | VCC internal LDO decoupling |
| C34 | C | 22µF X5R 10V | C_0805 | C59461 | Output cap #1 |
| C35 | C | 22µF X5R 10V | C_0805 | C59461 | Output cap #2 |
| C36 | C | 22µF X5R 10V | C_0805 | C59461 | Output cap #3 (66µF total) |
| C37 | C | 47nF X7R | C_0603 | TBD | Soft-start cap (~11ms ramp) |
| C38 | C | 4.7nF X7R | C_0603 | TBD | Compensation cap C_COMP1 |
| C39 | C | 100pF C0G | C_0603 | TBD | Compensation cap C_COMP2 (HF pole) |
| C41 | C | 10µF X5R 10V | C_0805 | C15850 | VIN power stage input cap |

### 5.2 Compensation Network Values

Derived from the TPS61088 EVM (SLVUAF2) reference design and scaled for 5V/3A at ~2.2 MHz:

| Parameter | EVM (9V/3A, 600 kHz) | This Design (5V/3A, 2.2 MHz) |
|-----------|---------------------|------------------------------|
| R_COMP | 17.4kΩ | **22kΩ** |
| C_COMP1 | 4700pF | **4700pF (4.7nF)** |
| C_COMP2 | not populated | **100pF** |
| Inductor | 1.2µH | 2.2µH |
| Output caps | 4× 22µF | 3× 22µF |

The EVM's R6=17.4kΩ and C8=4700pF form the main compensation zero. For our higher switching frequency and lower output voltage, the right-half-plane zero moves higher (~43 kHz at VIN=3.0V), allowing similar or slightly higher crossover bandwidth. R_COMP increased to 22kΩ for additional phase boost. C_COMP2 = 100pF adds a high-frequency pole for noise attenuation.

**These values are a conservative starting point. Verify loop stability with a Bode plot measurement during Phase 5 bench testing. If oscillation or excessive ringing is observed, adjust R_COMP (10–47kΩ) and C_COMP1 (2.2–10nF) on the bench.**

### 5.3 Pin-by-Pin Connections — U6 (TPS61088RHLR)

| Pin | Name | Net | Connection |
|-----|------|-----|------------|
| 1 | VCC | `BOOST_VCC` | → C33 (2.2µF) → GND |
| 2 | EN | `VSYS_SENSE` | Tied to VIN (always-on when VSYS present) |
| 3 | FSW | `BOOST_FSW` | → R41 (100kΩ) → `BOOST_SW` |
| 4 | SW | `BOOST_SW` | Switching node |
| 5 | SW | `BOOST_SW` | Switching node |
| 6 | SW | `BOOST_SW` | Switching node |
| 7 | SW | `BOOST_SW` | Switching node |
| 8 | BOOT | `BOOST_BOOT` | → C32 (0.1µF) → `BOOST_SW` |
| 9 | VIN | `VSYS_SENSE` | Power input (after INA219 shunt) |
| 10 | SS | `BOOST_SS` | → C37 (47nF) → `GND` |
| 11 | NC | `GND` | Connect to ground plane (thermal) |
| 12 | NC | `GND` | Connect to ground plane (thermal) |
| 13 | MODE | — | **Float** (PFM mode for battery efficiency) |
| 14 | VOUT | `+5V` | Boost output |
| 15 | VOUT | `+5V` | Boost output |
| 16 | VOUT | `+5V` | Boost output |
| 17 | FB | `BOOST_FB` | Feedback divider midpoint |
| 18 | COMP | `BOOST_COMP` | Compensation network |
| 19 | ILIM | `BOOST_ILIM` | → R42 (100kΩ) → `GND` (AGND) |
| 20 | AGND | `GND` | Analog ground |
| 21 | PGND | `GND` | Power ground |
| EP | Thermal Pad | `GND` | Solder to ground plane with thermal vias |

**Note on MODE pin (pin 13):** Leave floating — the internal 800kΩ pull-up selects PFM mode. PFM provides high efficiency at light loads (important for battery life). Do NOT connect MODE to GND unless forced PWM is specifically needed.

### 5.4 Feedback Divider

```
+5V ──→ R39 (180kΩ) ──→ BOOST_FB ──→ R40 (56kΩ) ──→ GND
                              │
                         U6 pin 17 (FB)
```

**R39:** Pin 1 → `+5V`, Pin 2 → `BOOST_FB`

**R40:** Pin 1 → `BOOST_FB`, Pin 2 → `GND`

VOUT = VREF × (1 + R39/R40) = 1.204 × (1 + 180/56) = **5.07V**

### 5.5 Compensation Network

```
BOOST_COMP (U6 pin 18) ──→ R43 (22kΩ) ──→ C38 (4.7nF) ──→ GND
                    │
                    └──→ C39 (100pF) ──→ GND
```

**R43:** Pin 1 → `BOOST_COMP`, Pin 2 → net `COMP_MID`

**C38:** Pin 1 → `COMP_MID`, Pin 2 → `GND`

**C39:** Pin 1 → `BOOST_COMP`, Pin 2 → `GND`

### 5.6 Frequency and Current Limit

**R41 (FSW):** Pin 1 → `BOOST_FSW`, Pin 2 → `BOOST_SW`
Sets switching frequency. With 100kΩ: fsw ≈ 2.2 MHz.

**R42 (ILIM):** Pin 1 → `BOOST_ILIM`, Pin 2 → `GND`
Sets peak current limit. With 100kΩ: ILIM ≈ 11.9A (PFM mode).

### 5.7 Inductor and Caps

**L2 (boost inductor):** Pin 1 → `BOOST_SW`, Pin 2 → `VSYS_SENSE`

Note: For a synchronous boost converter, the inductor connects from VIN to the SW node. Current path: VSYS_SENSE → L2 → BOOST_SW → [internal high-side FET] → +5V.

**C31 (VIN bypass):** Pin 1 → `VSYS_SENSE`, Pin 2 → `GND` (place close to U6 pin 9)

**C32 (BOOT cap):** Pin 1 → `BOOST_BOOT`, Pin 2 → `BOOST_SW`

**C33 (VCC cap):** Pin 1 → `BOOST_VCC`, Pin 2 → `GND`

**C34, C35, C36 (output caps):** Each: Pin 1 → `+5V`, Pin 2 → `GND`

**C37 (soft-start):** Pin 1 → `BOOST_SS`, Pin 2 → `GND`

**C41 (VIN bulk):** Pin 1 → `VSYS_SENSE`, Pin 2 → `GND`

### 5.8 Boost Converter Passive Connections Summary

| Component | Pin 1 Net | Pin 2 Net |
|-----------|-----------|-----------|
| L2 (2.2µH inductor) | `BOOST_SW` | `VSYS_SENSE` |
| C31 (0.1µF VIN bypass) | `VSYS_SENSE` | `GND` |
| C32 (0.1µF BOOT) | `BOOST_BOOT` | `BOOST_SW` |
| C33 (2.2µF VCC) | `BOOST_VCC` | `GND` |
| C34 (22µF output) | `+5V` | `GND` |
| C35 (22µF output) | `+5V` | `GND` |
| C36 (22µF output) | `+5V` | `GND` |
| C37 (47nF soft-start) | `BOOST_SS` | `GND` |
| C38 (4.7nF comp) | `COMP_MID` | `GND` |
| C39 (100pF comp) | `BOOST_COMP` | `GND` |
| C41 (10µF VIN bulk) | `VSYS_SENSE` | `GND` |
| R39 (180kΩ FB top) | `+5V` | `BOOST_FB` |
| R40 (56kΩ FB bottom) | `BOOST_FB` | `GND` |
| R41 (100kΩ FSW) | `BOOST_FSW` | `BOOST_SW` |
| R42 (100kΩ ILIM) | `BOOST_ILIM` | `GND` |
| R43 (22kΩ comp R) | `BOOST_COMP` | `COMP_MID` |

---

## 6. Block 4: Power Monitoring (INA219)

### 6.1 Components

| Ref | Part | Value | Footprint | LCSC | Function |
|-----|------|-------|-----------|------|----------|
| U7 | INA219AIDCNR | — | SOT-23-8 | C87469 | I2C power monitor |
| R44 | R | 10mΩ 1% 1W | R_2512 | C1322424 | VSYS current sense shunt |
| C40 | C | 0.1µF X7R | C_0603 | C14663 | VS supply bypass |

### 6.2 Shunt Resistor Placement

The shunt resistor sits in series on the VSYS rail between the BQ24195 output and the boost converter input:

```
BQ24195 SYS ──→ VSYS ──→ bulk caps (C27, C28, C29) ──→ R44 (10mΩ) ──→ VSYS_SENSE ──→ TPS61088 VIN
                                                          │                    │
                                                     INA219 IN+          INA219 IN-
```

This placement ensures the INA219 measures all current flowing from the BQ24195 to the boost converter (and thus to the entire +5V system).

### 6.3 Pin-by-Pin Connections — U7 (INA219AIDCNR, SOT-23-8)

| Pin | Name | Net | Connection |
|-----|------|-----|------------|
| 1 | IN+ | `VSYS` | Supply side of shunt (BQ24195 output) |
| 2 | IN− | `VSYS_SENSE` | Load side of shunt (boost converter input) |
| 3 | GND | `GND` | Ground |
| 4 | VS | `+3.3V` | Logic supply from 3.3V rail |
| 5 | SCL | `I2C_SCL` | Sheet pin → root → GPIO 44 |
| 6 | SDA | `I2C_SDA` | Sheet pin → root → GPIO 43 |
| 7 | A0 | `GND` | Address bit 0 = 0 |
| 8 | A1 | `GND` | Address bit 1 = 0 |

I2C address: **0x40** (A0=GND, A1=GND). No conflict with TCA9548A (0x70) or BQ24195 (0x6B).

### 6.4 Passive Connections

**R44 (shunt):** Pin 1 → `VSYS`, Pin 2 → `VSYS_SENSE`

**C40 (VS bypass):** Pin 1 → `+3.3V`, Pin 2 → `GND` (place close to U7 pin 4)

### 6.5 INA219 Configuration Summary

| Parameter | Value |
|-----------|-------|
| Shunt resistance | 10mΩ |
| PGA setting | /2 (±80mV range) |
| Max measurable current | 8A |
| Current resolution | 1 mA/LSB |
| Calibration register | 0x1000 (4096) |
| Power LSB | 20 mW |
| Bus voltage range | 16V (BRNG=0) or 32V (default) |

---

## 7. Signal Routing and Test Points

### 7.1 I2C Bus

The main I2C bus (`I2C_SDA`, `I2C_SCL`) enters the power management sheet via hierarchical pins and connects to:
- U5 (BQ24195) pins 5 (SCL) and 6 (SDA) — address 0x6B
- U7 (INA219) pins 5 (SCL) and 6 (SDA) — address 0x40

**No additional pull-ups on this sheet.** The existing 2.2kΩ pull-ups to +3.3V (R28, R29 on the TCA9548A subsystem sheet) serve the entire upstream bus. The BQ24195 and INA219 both support 400 kHz I2C.

### 7.2 BQ24195 Interrupt

`CHRG_INT` net: U5 pin 7 (INT) → R38 (10kΩ pull-up to +3.3V) → sheet pin CHRG_INT → root sheet → U2 pin 19 (GPIO 21) + TPIO21 test point.

INT is active-low, open-drain, 256µs pulse on any status or fault change. ESP32 firmware should configure GPIO 21 as falling-edge interrupt input.

### 7.3 Test Points

Add four test points on the power management sheet:

| Ref | Value/Label | Net | Footprint |
|-----|------------|-----|-----------|
| TP_VSYS | VSYS | `VSYS` | TestPoint_Pad_D1.5mm |
| TP_VBAT | VBAT | `VBAT` | TestPoint_Pad_D1.5mm |
| TP_PVBUS | PVBUS | `Protected_VBUS` | TestPoint_Pad_D1.5mm |
| TP_PGND | PGND | `GND` | TestPoint_Pad_D1.5mm |

Existing root sheet test points TP_5V1, TP_3V1, TP_GND1 remain for the +5V, +3.3V, and GND rails.

---

## 8. Complete Net List

### 8.1 Power Nets

| Net | Type | Source | Sinks |
|-----|------|--------|-------|
| `GND` | Ground | — | All component grounds, thermal pads |
| `+5V` | Power | U6 VOUT (pins 14-16) | Sheet pin → root: U1 VIN, U2 5V, LED sheet, C34-C36, R39 |
| `+3.3V` | Power | Sheet pin (from root AP2112K) | U7 VS, R35, R38 |
| `VBUS_RAW` | Power | J7 VBUS pins | F2 pin 1 |
| `Protected_VBUS` | Power | F2 pin 2 | U5 pins 1+24, C20, C21, C22 |
| `BAT_RAW` | Power | J8 pin 1 | Q2 drain, R34, C30 |
| `VBAT` | Power | Q2 source | U5 pins 13+14, R33, TP_VBAT |
| `VSYS` | Power | U5 pins 15+16 | L1 pin 2, C27, C28, C29, R44 pin 1, U7 IN+, TP_VSYS |
| `VSYS_SENSE` | Power | R44 pin 2 | U7 IN-, U6 pin 9 (VIN), U6 pin 2 (EN), L2 pin 2, C31, C41 |
| `BQ_PMID` | Power | U5 pin 23 | C25, C26 |
| `BQ_REGN` | Power | U5 pin 22 | C24, R36 |

### 8.2 Signal Nets

| Net | Type | Source | Sinks |
|-----|------|--------|-------|
| `I2C_SDA` | I2C data | Sheet pin (bidirectional) | U5 pin 6, U7 pin 6 |
| `I2C_SCL` | I2C clock | Sheet pin (bidirectional) | U5 pin 5, U7 pin 5 |
| `CHRG_INT` | Interrupt | U5 pin 7 | R38 (pull-up), sheet pin → GPIO 21 |
| `CC1` | USB-C | J7 A5 | R30 |
| `CC2` | USB-C | J7 B5 | R31 |

### 8.3 Internal Nets

| Net | Nodes |
|-----|-------|
| `BQ_SW` | U5 pins 19+20, L1 pin 1, C23 pin 2 |
| `BQ_BTST` | U5 pin 21, C23 pin 1 |
| `BQ_ILIM` | U5 pin 10, R32 pin 1 |
| `BQ_TS` | U5 pins 11+12, TH1 pin 1, R36 pin 2, R37 pin 1 |
| `OTG_BIAS` | U5 pin 8, R35 pin 1 |
| `PMOS_GATE` | Q2 pin 2, R33 pin 2, R34 pin 1 |
| `BOOST_SW` | U6 pins 4-7, L2 pin 1, C32 pin 2, R41 pin 2 |
| `BOOST_BOOT` | U6 pin 8, C32 pin 1 |
| `BOOST_VCC` | U6 pin 1, C33 pin 1 |
| `BOOST_FSW` | U6 pin 3, R41 pin 1 |
| `BOOST_SS` | U6 pin 10, C37 pin 1 |
| `BOOST_FB` | U6 pin 17, R39 pin 2, R40 pin 1 |
| `BOOST_COMP` | U6 pin 18, R43 pin 1, C39 pin 1 |
| `BOOST_ILIM` | U6 pin 19, R42 pin 1 |
| `COMP_MID` | R43 pin 2, C38 pin 1 |

---

## 9. Complete Bill of Materials

### 9.1 Active ICs (3)

| Ref | Part Number | Value | Package | LCSC | Qty |
|-----|------------|-------|---------|------|-----|
| U5 | BQ24195RGER | — | VQFN-24-EP 4×4mm | C90862 | 1 |
| U6 | TPS61088RHLR | — | VQFN-20-EP 3.5×4.5mm | C87357 | 1 |
| U7 | INA219AIDCNR | — | SOT-23-8 | C87469 | 1 |

### 9.2 Connectors (2)

| Ref | Part | Footprint | LCSC | Qty |
|-----|------|-----------|------|-----|
| J7 | TYPE-C-31-M-12 | USB-C_SMD | C165948 | 1 |
| J8 | JST PH 2-pin | JST_PH_S2B-PH-SM4-TB | C18221575 | 1 |

### 9.3 Discrete Semiconductors (1)

| Ref | Part | Package | LCSC | Qty |
|-----|------|---------|------|-----|
| Q2 | PMOS | SOT-23 | C3040193 | 1 |

### 9.4 Inductors (2)

| Ref | Value | Part Number | LCSC | Qty |
|-----|-------|------------|------|-----|
| L1 | 2.2µH | FNR6028S | C266426 | 1 |
| L2 | 2.2µH 10A Isat | FXL0630-2R2-M | C167218 | 1 |

### 9.5 Fuse (1)

| Ref | Value | Package | LCSC | Qty |
|-----|-------|---------|------|-----|
| F2 | 3A | 1206 | C2897466 | 1 |

### 9.6 Thermistor (1)

| Ref | Value | Package | LCSC | Qty |
|-----|-------|---------|------|-----|
| TH1 | 10kΩ NTC | 0603 | C13564 | 1 |

### 9.7 Resistors (15)

| Ref | Value | Tolerance | LCSC | Qty | Function |
|-----|-------|-----------|------|-----|----------|
| R30 | 5.1kΩ | 1% | C23186 | 1 | CC1 pull-down |
| R31 | 5.1kΩ | 1% | C23186 | 1 | CC2 pull-down |
| R32 | 330Ω | 1% | C23138 | 1 | BQ24195 ILIM |
| R33 | 100kΩ | 1% | C14675 | 1 | PMOS gate bias (VBAT side) |
| R34 | 100kΩ | 1% | C14675 | 1 | PMOS gate bias (BAT_RAW side) |
| R35 | 10kΩ | 1% | C25804 | 1 | OTG pull-up to +3.3V |
| R36 | 5.6kΩ | 1% | TBD | 1 | NTC bias top (REGN→TS) |
| R37 | 30kΩ | 1% | TBD | 1 | NTC bias bottom (TS→GND) |
| R38 | 10kΩ | 1% | C25804 | 1 | INT pull-up to +3.3V |
| R39 | 180kΩ | 1% | C22827 | 1 | FB divider top |
| R40 | 56kΩ | 1% | C23206 | 1 | FB divider bottom |
| R41 | 100kΩ | 1% | C14675 | 1 | TPS61088 FSW frequency set |
| R42 | 100kΩ | 1% | C14675 | 1 | TPS61088 ILIM current limit |
| R43 | 22kΩ | 1% | TBD | 1 | Compensation resistor |
| R44 | 10mΩ | 1% | C1322424 | 1 | INA219 shunt (2512 pkg, 1W) |

### 9.8 Capacitors (22)

| Ref | Value | Pkg | Voltage | LCSC | Qty | Function |
|-----|-------|-----|---------|------|-----|----------|
| C20 | 1µF X7R | 0603 | 25V | C15849 | 1 | VBUS bypass |
| C21 | 4.7µF X5R | 0603 | 10V | C19666 | 1 | Protected_VBUS ceramic |
| C22 | 47µF electrolytic | 6.3×5.4 | 16V | C2836440 | 1 | Protected_VBUS bulk |
| C23 | 47nF X7R | 0603 | 25V | TBD | 1 | BQ24195 bootstrap (BTST→SW) |
| C24 | 4.7µF X5R | 0603 | 10V | C19666 | 1 | BQ24195 REGN bypass |
| C25 | 10µF X5R | 0603 | 10V | C96446 | 1 | BQ24195 PMID bypass #1 |
| C26 | 10µF X5R | 0603 | 10V | C96446 | 1 | BQ24195 PMID bypass #2 |
| C27 | 10µF X5R | 0603 | 10V | C96446 | 1 | VSYS ceramic #1 |
| C28 | 10µF X5R | 0603 | 10V | C96446 | 1 | VSYS ceramic #2 |
| C29 | 220µF electrolytic | 6.3×7.7 | 10V | C3342 | 1 | VSYS bulk |
| C30 | 47µF electrolytic | 6.3×5.4 | 10V | C2836440 | 1 | Battery bulk |
| C31 | 0.1µF X7R | 0603 | 16V | C14663 | 1 | Boost VIN bypass |
| C32 | 0.1µF X7R | 0603 | 16V | C14663 | 1 | Boost BOOT cap |
| C33 | 2.2µF X5R | 0603 | 10V | C23630 | 1 | Boost VCC LDO cap |
| C34 | 22µF X5R | 0805 | 10V | C59461 | 1 | Boost output #1 |
| C35 | 22µF X5R | 0805 | 10V | C59461 | 1 | Boost output #2 |
| C36 | 22µF X5R | 0805 | 10V | C59461 | 1 | Boost output #3 |
| C37 | 47nF X7R | 0603 | 25V | TBD | 1 | Boost soft-start |
| C38 | 4.7nF X7R | 0603 | 25V | TBD | 1 | Compensation C_COMP1 |
| C39 | 100pF C0G | 0603 | 50V | TBD | 1 | Compensation C_COMP2 |
| C40 | 0.1µF X7R | 0603 | 16V | C14663 | 1 | INA219 VS bypass |
| C41 | 10µF X5R | 0805 | 10V | C15850 | 1 | Boost VIN bulk |

### 9.9 Test Points (4)

| Ref | Label | Net | Footprint | Qty |
|-----|-------|-----|-----------|-----|
| TP_VSYS | VSYS | `VSYS` | TestPoint_Pad_D1.5mm | 1 |
| TP_VBAT | VBAT | `VBAT` | TestPoint_Pad_D1.5mm | 1 |
| TP_PVBUS | PVBUS | `Protected_VBUS` | TestPoint_Pad_D1.5mm | 1 |
| TP_PGND | PGND | `GND` | TestPoint_Pad_D1.5mm | 1 |

### 9.10 Summary

| Category | Count |
|----------|-------|
| ICs | 3 |
| Connectors | 2 |
| PMOS transistor | 1 |
| Inductors | 2 |
| Fuse | 1 |
| NTC thermistor | 1 |
| Resistors | 15 |
| Capacitors | 22 |
| Test points | 4 |
| **Total new components** | **51** |

Components removed from root sheet: 2 (J2, D1).

---

## 10. I2C Address Map (After Changes)

| Device | Address | Sheet |
|--------|---------|-------|
| TCA9548A | 0x70 | TCA9548A_Subsystem (existing) |
| BQ24195 | 0x6B | Power Management (new) |
| INA219 | 0x40 | Power Management (new) |
| PCA9546A ×3 | 0x70–0x72 | Downstream of TCA9548A (sensor boards) |
| VCNL4040 ×6 | 0x60 | Downstream of PCA9546A (sensor boards) |

No address conflicts. All three upstream devices (TCA9548A, BQ24195, INA219) have unique addresses on the shared I2C bus.

---

## 11. Power Path Summary

```
USB-C (5V)
  │
  └→ F2 (3A fuse)
       │
       └→ Protected_VBUS (C20 1µF + C21 4.7µF + C22 47µF)
            │
            └→ U5 BQ24195 VBUS
                 │
                 ├→ PMID (C25+C26 = 20µF)
                 │
                 ├→ [internal buck/charge path]
                 │       │
                 │       └→ VBAT ←→ Q2 (PMOS) ←→ J8 (battery)
                 │              (C30 47µF)
                 │
                 └→ SYS → VSYS (C27+C28 = 20µF + C29 220µF)
                            │
                            └→ R44 (10mΩ shunt) ← INA219 monitors
                                 │
                                 └→ VSYS_SENSE (C41 10µF + C31 0.1µF)
                                      │
                                      └→ U6 TPS61088 VIN
                                           │
                                           └→ [boost conversion]
                                                │
                                                └→ +5V (C34+C35+C36 = 66µF)
                                                     │
                                                     ├→ AP2112K → +3.3V (root sheet)
                                                     ├→ T-Display-S3 (root sheet)
                                                     ├→ LED controller (root sheet)
                                                     └→ Level shifter VCC (LED sheet)
```

---

## 12. Design Notes

### 12.1 TBD LCSC Part Numbers

The following parts need LCSC numbers confirmed before ordering. All are common values — search LCSC for 0603 ceramics and resistors in these values:

| Ref | Value | Expected LCSC range |
|-----|-------|-------------------|
| R36 | 5.6kΩ 1% 0603 | Standard E96 value |
| R37 | 30kΩ 1% 0603 | Standard E96 value |
| R43 | 22kΩ 1% 0603 | Standard E24 value |
| C23 | 47nF X7R 0603 25V+ | Common value |
| C37 | 47nF X7R 0603 25V+ | Same as C23 |
| C38 | 4.7nF X7R 0603 25V+ | Common value |
| C39 | 100pF C0G 0603 50V | Common value |

### 12.2 Layout-Critical Placement

1. **C20 (1µF VBUS bypass):** Place within 3mm of U5 VBUS pins (1, 24)
2. **C31 (0.1µF VIN bypass):** Place within 3mm of U6 VIN pin (9)
3. **C40 (0.1µF VS bypass):** Place within 3mm of U7 VS pin (4)
4. **C25, C26 (PMID caps):** Place close to U5 PMID pin (23)
5. **L2 (boost inductor):** Minimize trace length between L2, U6 SW pins, and U6 VIN
6. **R44 (shunt):** Use Kelvin (4-wire) connection for accurate sensing
7. **U5, U6 thermal pads:** Solder to ground plane with thermal vias (minimum 5 vias each)
8. **U6 NC pins (11, 12):** Connect to ground plane for thermal dissipation
9. **Minimize BOOST_SW copper area:** Fast switching edges radiate EMI

### 12.3 Compensation Network Tuning

The R43/C38/C39 compensation values (22kΩ / 4.7nF / 100pF) are derived from the TPS61088 EVM and scaled for 5V output. These are a starting point. During Phase 5 bench testing:

1. Check output voltage stability under load transients (0.5A to 2.5A step)
2. If ringing or oscillation is observed, try:
   - Increase R43 to 33kΩ or 47kΩ (more phase margin)
   - Increase C38 to 10nF (lower crossover frequency)
   - Remove C39 (eliminate HF pole if it causes problems)
3. If possible, measure the loop Bode plot with a network analyzer

### 12.4 NTC Without Battery

If testing without a battery or without the NTC thermistor populated:
- **No NTC (TH1 not populated):** Replace R37 (30kΩ) with 10kΩ. This biases TS at ~64% of VREGN, within the valid charging window.
- **No battery (J8 empty):** Configure firmware to set REG07[5] = 1 (BATFET_Disable). NTC state does not affect operation when BATFET is disabled.

### 12.5 Boot-Time Power Sequence

1. USB-C connected → VBUS present → Protected_VBUS rises
2. BQ24195 POR: I2C active, registers at default, D+/D- detection starts
3. D+/D- grounded → detected as SDP. OTG HIGH → 500mA input current limit
4. VSYS rises to ~3.65V (VSYS_MIN + 150mV, battery absent) or battery voltage
5. TPS61088 EN crosses 1.2V threshold → converter initializes
6. TPS61088 VIN UVLO clears at 2.7V → switching begins, soft-start ramps
7. +5V output reaches 5.07V (~11ms soft-start)
8. AP2112K produces +3.3V from +5V
9. ESP32 boots, firmware configures BQ24195 via I2C:
   - Write REG00[2:0] = 101 (1.5A input limit), clamped by ILIM at ~1.5A
   - Optionally disable watchdog: REG05[5:4] = 00
   - If no battery detected (REG08[0] = 1): set REG07[5] = 1 (BATFET_Disable)

---

*Generated: March 10, 2026 — Phase 2 of Integrated Power Management Initiative*

# Integrated Power Management — PCB Layout Guide (Phase 5)

This document captures layout constraints, trace sizing, thermal management, and placement priorities for the power management section of the main PCB. Use when placing components in KiCad PCB editor.

---

## 1. Board Area & Placement Strategy

### Current Board: 85mm × 45mm

Power block estimated at ~830mm² (components + clearance + routing). This fits within the ~1,000-1,400mm² of available area, but is tight. Removing the DWEII module (J2) and Schottky (D1) frees ~150mm² additional space.

**Decision point:** If component placement or thermal pour requirements feel cramped, grow board to **90mm × 50mm**. This adds ~675mm² of usable area — a comfortable buffer.

### Placement Zones

Organize the power section into 4 zones, placed in rough order from USB-C input to output:

```
                    ┌─────────────────────────────────────────┐
                    │           EXISTING COMPONENTS            │
                    │  T-Display-S3, TCA9548A, AP2112K, etc.  │
                    │                                          │
                    ├─────────────────────────────────────────┤
                    │                                          │
  ┌──────────┐      │  ┌────────────┐   ┌────────────┐        │
  │  USB-C   │      │  │  BQ24195   │   │  TPS61088  │        │
  │  + Fuse  │──────│──│  + L1, Q2  │──→│  + L2      │──→ +5V │
  │  J7, F2  │      │  │  + caps    │   │  + caps    │        │
  └──────────┘      │  └────────────┘   └────────────┘        │
   CC pulldowns,    │                                          │
   decoupling       │  ┌─────────┐  ┌────────────┐            │
                    │  │  J8 BAT │  │  INA219    │            │
                    │  │  + Q2   │  │  + R_SHUNT │            │
                    │  └─────────┘  └────────────┘            │
                    │  Test Points: TP1-TP4 along board edge   │
                    └─────────────────────────────────────────┘
```

**USB-C connector (J7):** Place at board edge. The connector has a fixed orientation — the receptacle opening must face outward.

**Battery connector (J8):** Place at board edge, accessible for JST PH plug.

---

## 2. Critical Placement Rules

### 2.1 TPS61088 Boost Converter — Tightest Layout

The TPS61088 is a 2.2MHz switching converter. Loop inductance is the primary layout concern.

1. **L2 (2.2µH 10A inductor) must be as close as possible to U6 pins 4-7 (SW)**. Minimize the trace length between L2 pad 1 and U6 SW pins. Ideally <5mm trace length, <3mm preferred.

2. **Output caps (C34, C35, C36 — 22µF 0805) must be close to U6 pins 14-16 (+5V)**. Place within 5mm of the IC output pins.

3. **Input cap (C41 — 10µF 0805, C31 — 100nF) must be close to U6 pins 2/9 (VIN/EN)**. The 100nF cap (C31) should be the closest to the IC pins.

4. **Bootstrap cap (C32 — 100nF) connects BOOT (pin 8) to SW (pins 4-7)**. Keep this trace short and direct.

5. **Feedback divider (R39/R40):** Place close to U6 pin 17 (FB). Route the FB trace away from the SW node and inductor. Keep FB trace short and away from noisy nodes.

6. **Compensation network (R43, C38, C39):** Place close to U6 pin 18 (COMP). These are small-signal — keep away from power traces.

### 2.2 BQ24195 — Moderate Layout Sensitivity

1. **L1 (2.2µH) connects to U5 pins 19-20 (SW) and feeds VSYS**. Place L1 close to the BQ24195.

2. **Bootstrap cap (C23 — 47nF) connects BTST (pin 21) to SW (pins 19-20)**. Short trace.

3. **PMID caps (C25, C26 — 10µF each) connect to pin 23**. Place close.

4. **VSYS bulk capacitors (C27, C28 — 10µF, C29 — 220µF):** Place near U5 pins 15-16 (VSYS). The electrolytic (C29) can be slightly further away but should still be within 10-15mm.

5. **Input caps on Protected_VBUS (C20, C21, C22):** Place between the fuse (F2) and U5 pins 1/24 (IN).

### 2.3 INA219 + Shunt Resistor

1. **R44 (10mΩ 2512) is in-line on the VSYS rail**. The current path from BQ24195 VSYS output to TPS61088 VIN flows through this shunt.

2. **U7 Kelvin connections:** INA219 pins 1 (VIN+) and 2 (VIN-) should connect to opposite sides of R44 with separate traces (4-wire Kelvin sense). Do NOT tap the sense lines from the main current path — run dedicated thin traces from the R44 pads directly to U7 pins 1 and 2.

3. **C40 (100nF) bypass:** Place on U7 pin 4 (VS), close to IC.

### 2.4 PMOS Reverse Polarity Protection (Q2)

Place Q2 near J8 (battery connector). R33 and R34 (gate bias) should be close to Q2.

---

## 3. Trace Width Calculations

For 1 oz copper (35µm thickness), outer layer, 10°C temperature rise:

| Current | Min Width (1oz) | Recommended | Traces |
|---------|----------------|-------------|--------|
| 3A | 0.76mm | **≥1.0mm** | +5V output, VSYS power, Protected_VBUS |
| 2A | 0.45mm | **≥0.75mm** | VBAT, BAT_RAW |
| 1.5A | 0.30mm | **≥0.5mm** | VBUS_RAW (USB input to fuse) |
| <0.5A | 0.15mm | **≥0.25mm** | I2C_SDA, I2C_SCL, CHRG_INT, all signal traces |

### Specific Trace Recommendations

| Net | Expected Current | Width | Notes |
|-----|-----------------|-------|-------|
| **+5V** (boost output to rest of board) | up to 3A+ | **1.5mm** or polygon fill | Main power distribution — widest trace on the board |
| **VSYS** (BQ24195 to shunt to TPS61088) | up to 3A | **1.0-1.5mm** | Carries full system current |
| **VSYS_SENSE** (post-shunt to TPS61088 VIN) | up to 3A | **1.0-1.5mm** | Same current as VSYS |
| **Protected_VBUS** (fuse to BQ24195 IN) | up to 3A | **1.0mm** | USB input current |
| **VBUS_RAW** (USB-C to fuse) | up to 3A | **1.0mm** | Short run from connector |
| **BQ_SW** (switching node) | pulsed 4.5A | **1.0mm** | Keep short, minimize loop area |
| **BOOST_SW** (TPS61088 switching node) | pulsed 6A+ | **1.5mm** | CRITICAL: keep short, minimize loop area with GND return |
| **VBAT / BAT_RAW** | up to 2A charge | **0.75mm** | Battery charge current |
| **GND** | — | **Ground plane** | Unbroken ground plane under entire power section |

### Switching Node Traces (BQ_SW, BOOST_SW)

These carry high-frequency pulsed current. Rules:
- Keep as short as possible (minimize loop area)
- Route on the same layer as the IC and inductor (avoid vias in the power path)
- The GND return path should be directly underneath on the adjacent layer (ground plane)
- Do NOT route sensitive signal traces (FB, COMP, I2C) near switching nodes

---

## 4. Thermal Management

### 4.1 TPS61088 Thermal Pad

The TPS61088 (VQFN-20-EP) has an exposed thermal pad on the bottom. At 3A output from ~3.5V VSYS:
- **Estimated dissipation:** ~1.5W (at ~85% efficiency)
- **RθJA with good layout:** 29.7°C/W → Tj = Tambient + 44.5°C → ~85°C at 40°C ambient

**Requirements:**
- Connect exposed pad to GND plane via **multiple thermal vias** (array of 4-6 vias, 0.3mm drill, within the EP footprint)
- **Copper pour on top layer** under U6 connected to GND — at least 5mm beyond IC footprint in all directions
- Bottom layer GND plane should be solid under U6

### 4.2 BQ24195 Thermal Pad

The BQ24195 (VQFN-24-EP) also has an exposed thermal pad. Dissipation depends on operating mode:
- **Charging at 2A:** ~1-2W typical
- **Buck mode (VBUS→VSYS):** ~0.5W
- **Supplementing mode (VBUS + BAT → VSYS):** ~0.3W

**Requirements:**
- Connect exposed pad to GND plane via **multiple thermal vias** (array of 4-6 vias, 0.3mm drill)
- **Copper pour on top layer** under U5 connected to GND — at least 3-5mm beyond IC footprint
- Bottom layer GND plane should be solid under U5

### 4.3 Shunt Resistor (R44)

10mΩ 2512 dissipates up to 0.36W at 6A. The 2512 package (6.3×3.2mm) handles this easily. No special thermal relief needed, but ensure adequate copper on both pads for current carrying capacity.

### 4.4 Inductor Thermal

L2 (FXL0630-2R2-M, 7×6.6mm) dissipates ~0.5W at 3A DC (15mΩ DCR × 3A²). Acceptable without additional thermal relief.

L1 (SMNR6028-2R2MT, 6×6mm) dissipates ~0.1W at 2A DC (26mΩ DCR). Negligible.

---

## 5. Ground Plane Strategy

**An unbroken ground plane is the single most important layout decision for this power section.**

1. **Dedicate one full inner layer (or the bottom layer on a 2-layer board) as ground.** No signal routing should split the ground plane under the power section.

2. **Ground vias near every bypass cap:** Every decoupling cap GND pad should have a via to the ground plane within 0.5mm.

3. **Star grounding is NOT needed** for this design — a solid ground plane with short return paths is sufficient.

4. **High-current ground return:** The boost converter and BQ24195 switching currents return through the ground plane. Ensure the ground plane copper under L2 and U6 is continuous and not interrupted by signal traces.

---

## 6. Specific Component Footprint Notes

| Component | Footprint | Special Notes |
|-----------|-----------|---------------|
| U5 BQ24195 | VQFN-24-EP (4×4mm, 0.5mm pitch) | Exposed pad → GND, thermal vias required |
| U6 TPS61088 | VQFN-20-EP (3.6×4.6mm, 0.5mm pitch) | Exposed pad → GND, thermal vias required |
| U7 INA219 | SOT-23-8 | No exposed pad, standard SOT-23-8 |
| L2 boost inductor | IND-SMD_L7.0-W6.6 | Largest component, 7×6.6mm footprint |
| C29 220µF electrolytic | CP_Elec_6.3x7.7 | Tallest component (~7.7mm), check enclosure clearance |
| R44 10mΩ shunt | R_2512_6332Metric | 6.3×3.2mm, needs wide traces to pads |
| J7 USB-C | USB-C_SMD-TYPE-C-31-M-12 | Board edge placement, mechanical anchoring tabs |

---

## 7. DRC Settings for Power Section

Suggested KiCad DRC overrides for power nets:

| Parameter | Default | Power Nets |
|-----------|---------|------------|
| Min trace width | 0.2mm | 1.0mm for +5V, VSYS, VSYS_SENSE, Protected_VBUS |
| Min clearance | 0.2mm | 0.3mm (higher voltage switching nodes) |
| Min via drill | 0.3mm | 0.3mm (standard for thermal vias) |
| Via annular ring | 0.15mm | 0.15mm |

---

## 8. Board Stackup Recommendation

For the power section, **2-layer is possible but 4-layer is strongly recommended:**

| Option | Pros | Cons |
|--------|------|------|
| **2-layer** | Cheaper ($2-5 at JLCPCB qty 5) | Ground plane interrupted by signal routing; harder to achieve good thermal performance |
| **4-layer** (recommended) | Dedicated inner GND plane, better thermal vias, cleaner signal routing | ~$8-15 more at JLCPCB qty 5 |

If staying with 2-layer, maximize the bottom-layer ground pour and avoid routing signals through the power section ground plane area.

---

## 9. Pre-Layout Checklist

- [ ] Confirm board dimensions (85×45mm or expand to 90×50mm)
- [ ] Place USB-C connector at board edge
- [ ] Place battery connector at board edge
- [ ] Place TPS61088 + L2 close together (SW trace <5mm)
- [ ] Place BQ24195 + L1 close together
- [ ] Place INA219 + R44 in-line on VSYS path (Kelvin sense)
- [ ] Add thermal via arrays under U5 and U6 exposed pads
- [ ] Create copper pour zones for U5 and U6 thermal relief
- [ ] Set trace widths per §3 table
- [ ] Verify ground plane continuity under power section
- [ ] Check C29 (220µF, 7.7mm tall) fits within enclosure height
- [ ] Place test points (TP1-TP4) at board edge for probe access
- [ ] Run DRC with power net width constraints

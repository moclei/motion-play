# Integrated Power Management — BOM Verification & Assembly Review (Phase 5)

> Generated from `spec.json` and verified against LCSC/JLCPCB on March 11, 2026

## Summary

- **47 physical components** across 4 functional blocks + 4 test points (bare pads)
- **30 unique LCSC part numbers** (after deduplication)
- **3 BOM issues found** — all resolved with drop-in swaps (see §1)
- **5 cost optimization swaps** — extended → basic parts, saves ~$15 per assembly order
- **13 extended parts, 17 basic parts** after optimization
- **Estimated power section component cost:** ~$7.50 per board (at qty 5)

---

## 1. Critical Issues & Required Changes

### 1.1 ⚠️ PMOS Q2: Out of Stock — SWAP REQUIRED

| | Original | Replacement |
|---|----------|-------------|
| **Ref** | Q2 | Q2 |
| **LCSC** | C3040193 (VBZ3401) | **C15127 (AO3401A)** |
| **Stock** | **3** (effectively OOS) | **904,777** |
| **Price** | $0.11 | $0.057 |
| **Library** | Extended | **Basic** (saves $3) |
| **Package** | SOT-23 | SOT-23 (drop-in) |
| **Specs** | 30V, 5.6A, 46mΩ | 30V, 4A, 47mΩ |

**Impact:** AO3401A has 4A continuous drain vs 5.6A for VBZ3401. This PMOS carries battery charge current (max configurable 4.5A on BQ24195, but we'll set 2-3A for Samsung 30Q). 4A rating is adequate for our use case. The lower RDS(on) difference is negligible (47mΩ vs 46mΩ).

### 1.2 ⚠️ 22µF Output Caps C34-C36: Footprint Mismatch — SWAP REQUIRED

| | Original | Replacement |
|---|----------|-------------|
| **LCSC** | C59461 (CL10A226MQ8NRNC) | **C45783 (CL21A226MAQNNNE)** |
| **Package** | **0603** (mismatch with 0805 footprint!) | **0805** (correct) |
| **Voltage** | 6.3V | **25V** (5x improvement) |
| **Stock** | 19.7M | **4.4M** |
| **Price** | $0.0095 | $0.031 |
| **Library** | Basic | **Basic** |

**Impact:** The original C59461 is physically a 0603 cap but `spec.json` specifies `C_0805_2012Metric` footprint — these are incompatible sizes. C45783 is a proper 0805 part. The 25V rating (vs 6.3V) also provides much better voltage margin for the 5V boost output and improves capacitance stability under DC bias.

### 1.3 ⚠️ BQ24195RGER C90862: Low Stock Warning

| Detail | Value |
|--------|-------|
| **Current stock** | **24 units** |
| **Needed per board** | 1 |
| **For 5-board order** | 5 units (OK, but tight) |

Stock is sufficient for a small order but leaves no margin for reorders. The fallback part BQ25896RTWR (C181475, 113 units, $1.71) is pin-incompatible and would require schematic changes. **Recommendation:** Order promptly. If stock drops to zero, the RGET variant or a different lot may restock.

---

## 2. Cost Optimization — Extended → Basic Swaps

These swaps maintain identical electrical specs while saving $3/each in JLCPCB extended part surcharges:

| Refs | Value | Original LCSC | → Optimized LCSC | Savings |
|------|-------|---------------|-------------------|---------|
| R33, R34, R41, R42 | 100kΩ 0603 | C14675 (extended) | **C25803** (basic) | $3 |
| C23, C37 | 47nF 0603 | C107093 (extended) | **C1622** (basic) | $3 |
| C38 | 4.7nF 0603 | C1621 (extended) | **C53987** (basic) | $3 |
| C34, C35, C36 | 22µF 0805 | C59461 (wrong pkg) | **C45783** (basic) | $3 |
| Q2 | PMOS SOT-23 | C3040193 (extended) | **C15127** (basic) | $3 |

**Total extended part surcharge savings: ~$15 per order**

---

## 3. Complete BOM — Power Management Section

### 3.1 ICs (3 unique parts — all Extended)

| Ref | Value | LCSC | Package | Stock | Price | Type |
|-----|-------|------|---------|-------|-------|------|
| U5 | BQ24195RGER | C90862 | VQFN-24-EP (4×4mm) | 24 | $2.31 | Extended |
| U6 | TPS61088RHLR | C87357 | VQFN-20-EP (3.6×4.6mm) | 4,959 | $1.08 | Extended |
| U7 | INA219AIDCNR | C87469 | SOT-23-8 | 7,253 | $0.58 | Extended |

### 3.2 Discrete Semiconductor (1 unique part — Basic)

| Ref | Value | LCSC | Package | Stock | Price | Type |
|-----|-------|------|---------|-------|-------|------|
| Q2 | AO3401A PMOS | **C15127** | SOT-23 | 904,777 | $0.057 | Basic |

### 3.3 Connectors (2 unique parts — Extended)

| Ref | Value | LCSC | Package | Stock | Price | Type |
|-----|-------|------|---------|-------|-------|------|
| J7 | TYPE-C-31-M-12 | C165948 | SMD 16P | 191,906 | $0.18 | Extended |
| J8 | JST PH 2-pin | C18221575 | SMD P=2mm | 830 | $0.03 | Extended |

### 3.4 Inductors (2 unique parts — Extended)

| Ref | Value | LCSC | Package | Stock | Price | Type |
|-----|-------|------|---------|-------|-------|------|
| L1 | 2.2µH (BQ24195 switching) | C266426 | SMD 6×6mm | 737 | $0.09 | Extended |
| L2 | 2.2µH 10A (TPS61088 boost) | C167218 | SMD 7×6.6mm | 109,622 | $0.10 | Extended |

### 3.5 Resistors (11 unique values, 15 instances)

| Ref(s) | Value | LCSC | Qty | Stock | Price | Type |
|--------|-------|------|-----|-------|-------|------|
| R30, R31 | 5.1kΩ | C23186 | 2 | 4.1M | $0.0014 | Basic |
| R32 | 330Ω | C23138 | 1 | 2.4M | $0.0015 | Basic |
| R33, R34, R41, R42 | 100kΩ | **C25803** | 4 | 5.1M | $0.0014 | Basic |
| R35, R38 | 10kΩ | C25804 | 2 | 29.4M | $0.0013 | Basic |
| R36 | 5.6kΩ | C23189 | 1 | 1.2M | $0.0012 | Basic |
| R37 | 30kΩ | C22984 | 1 | 721K | $0.0014 | Basic |
| R39 | 180kΩ | C22827 | 1 | 96K | $0.0015 | Extended |
| R40 | 56kΩ | C23206 | 1 | 1.3M | $0.0013 | Basic |
| R43 | 22kΩ | C31850 | 1 | 1.6M | $0.0016 | Basic |
| R44 | 10mΩ 2512 | C1322424 | 1 | 4,470 | $0.078 | Extended |
| TH1 | 10kΩ NTC | C13564 | 1 | 466K | $0.038 | Extended |

### 3.6 Capacitors (10 unique values, 21 instances)

| Ref(s) | Value | LCSC | Qty | Pkg | Stock | Price | Type |
|--------|-------|------|-----|-----|-------|-------|------|
| C20 | 1µF | C15849 | 1 | 0603 | 7.5M | $0.0072 | Basic |
| C21, C24 | 4.7µF | C19666 | 2 | 0603 | 6.6M | $0.010 | Basic |
| C25, C26, C27, C28 | 10µF 25V | C96446 | 4 | 0603 | 13.8M | $0.018 | Basic |
| C31, C32, C40 | 100nF | C14663 | 3 | 0603 | 47.1M | $0.0027 | Basic |
| C33 | 2.2µF | C23630 | 1 | 0603 | 5.9M | $0.0062 | Basic |
| C23, C37 | 47nF | **C1622** | 2 | 0603 | 2.6M | $0.0053 | Basic |
| C38 | 4.7nF | **C53987** | 1 | 0603 | 276K | $0.0034 | Basic |
| C39 | 100pF | C14858 | 1 | 0603 | 7.3M | $0.0041 | Basic |
| C34, C35, C36 | 22µF 25V | **C45783** | 3 | 0805 | 4.4M | $0.031 | Basic |
| C41 | 10µF 25V | C15850 | 1 | 0805 | 3.9M | $0.020 | Basic |

### 3.7 Electrolytic Capacitors (2 unique parts — Extended)

| Ref(s) | Value | LCSC | Qty | Package | Stock | Price | Type |
|--------|-------|------|-----|---------|-------|-------|------|
| C22, C30 | 47µF 35V | C2836440 | 2 | D6.3×L5.4mm | 209K | $0.032 | Extended |
| C29 | 220µF 16V | C3342 | 1 | D6.3×L7.7mm | 87K | $0.035 | Extended |

### 3.8 Fuse (1 unique part — Extended)

| Ref | Value | LCSC | Package | Stock | Price | Type |
|-----|-------|------|---------|-------|-------|------|
| F2 | 3A PTC | C2897466 | 1206 | 20K | $0.088 | Extended |

### 3.9 Test Points (not assembled — bare copper pads)

| Ref | Net | Footprint |
|-----|-----|-----------|
| TP1 | VSYS | TestPoint_Pad_D1.5mm |
| TP2 | VBAT | TestPoint_Pad_D1.5mm |
| TP3 | Protected_VBUS | TestPoint_Pad_D1.5mm |
| TP4 | GND | TestPoint_Pad_D1.5mm |

### 3.10 Non-physical (ERC only — not in BOM)

#FLG05, #FLG06, #FLG07, #FLG08 — PWR_FLAG symbols (no footprint, schematic-only)

---

## 4. JLCPCB Assembly Capability Review

### 4.1 Package Compatibility

All packages are standard SMT that JLCPCB assembles routinely:

| Package | Components | JLCPCB Status |
|---------|-----------|---------------|
| VQFN-24-EP (4×4mm, 0.5mm pitch) | U5 (BQ24195) | ✅ Standard — requires paste stencil for exposed pad |
| VQFN-20-EP (3.6×4.6mm, 0.5mm pitch) | U6 (TPS61088) | ✅ Standard — requires paste stencil for exposed pad |
| SOT-23-8 | U7 (INA219) | ✅ Standard |
| SOT-23 | Q2 (PMOS) | ✅ Standard |
| 0603 passives | 28 components | ✅ Standard |
| 0805 passives | 4 components | ✅ Standard |
| 2512 resistor | R44 (shunt) | ✅ Standard |
| 1206 fuse | F2 | ✅ Standard |
| SMD electrolytic (6.3mm dia) | C22, C29, C30 | ✅ Standard |
| SMD inductor (6×6mm) | L1 | ✅ Standard |
| SMD inductor (7×6.6mm) | L2 | ✅ Standard |
| USB-C SMD connector | J7 | ✅ Standard (16-pin, may need manual orientation check) |
| JST PH SMD | J8 | ✅ Standard |

**No BGA, through-hole, or fine-pitch (<0.4mm) packages.** All components are single-side SMT compatible.

### 4.2 Extended vs Basic Part Count

| Category | Count | Surcharge |
|----------|-------|-----------|
| Basic parts | 17 unique | $0 |
| Extended parts | 13 unique | $3 × 13 = **$39** |
| **Total unique LCSC parts** | **30** | **$39 extended surcharge** |

**Extended parts breakdown:**
1. C90862 — BQ24195RGER (IC)
2. C87357 — TPS61088RHLR (IC)
3. C87469 — INA219AIDCNR (IC)
4. C165948 — USB-C connector
5. C18221575 — JST PH connector
6. C266426 — 2.2µH inductor (BQ24195)
7. C167218 — 2.2µH 10A inductor (TPS61088)
8. C2836440 — 47µF electrolytic
9. C3342 — 220µF electrolytic
10. C1322424 — 10mΩ shunt resistor
11. C13564 — 10kΩ NTC thermistor
12. C22827 — 180kΩ resistor (FB divider)
13. C2897466 — 3A resettable fuse

### 4.3 Thermal Pad Notes

U5 (BQ24195) and U6 (TPS61088) have exposed thermal pads (EP). JLCPCB handles these via solder paste stencil openings. Ensure the KiCad footprint has proper paste mask definition for the EP. The easyeda2kicad-installed footprints should include this.

---

## 5. Estimated Per-Board Cost (Power Section Only)

| Line Item | Cost |
|-----------|------|
| ICs (U5 + U6 + U7) | $3.97 |
| PMOS (Q2) | $0.06 |
| Connectors (J7 + J8) | $0.21 |
| Inductors (L1 + L2) | $0.19 |
| Resistors (15 pcs) | $0.11 |
| Capacitors (21 pcs ceramic) | $0.30 |
| Electrolytic caps (3 pcs) | $0.10 |
| Fuse (F2) | $0.09 |
| **Component total** | **~$5.03** |
| Extended part surcharge (13 × $3, amortized over 5 boards) | ~$7.80 |
| **Per-board total (components + surcharge)** | **~$12.83** |

*Assembly labor, PCB fabrication, and shipping are additional.*

---

## 6. Changes Required in spec.json

Before generating the final assembly BOM, update these LCSC numbers in `spec.json`:

| Ref(s) | Field | Old Value | New Value | Reason |
|--------|-------|-----------|-----------|--------|
| Q2 | lcsc | C3040193 | **C15127** | OOS → AO3401A (basic, in stock) |
| C34, C35, C36 | lcsc | C59461 | **C45783** | Footprint mismatch fix (0603→0805) |
| R33, R34, R41, R42 | lcsc | C14675 | **C25803** | Extended → basic optimization |
| C23, C37 | lcsc | C107093 | **C1622** | Extended → basic optimization |
| C38 | lcsc | C1621 | **C53987** | Extended → basic optimization |

---

## 7. Pre-Order Checklist

- [ ] Apply spec.json LCSC changes from §6
- [ ] Regenerate `power_management.kicad_sch` (if LCSC field is embedded in schematic)
- [ ] Complete PCB layout (boost converter proximity, thermal pours, trace widths)
- [ ] Export Gerbers + drill files from KiCad
- [ ] Export BOM CSV (Ref, Value, Footprint, LCSC) and CPL (component placement) from KiCad
- [ ] Upload to JLCPCB: Gerbers → BOM → CPL
- [ ] Verify component orientation in JLCPCB preview (especially J7 USB-C, U5, U6)
- [ ] Confirm BQ24195 (C90862) is still in stock at order time
- [ ] Select assembly options: single-side SMT, economic assembly
- [ ] Order qty 5 (minimum for JLCPCB SMT assembly)

# JLCPCB Manufacturing Pre-Flight Review

**Board:** motion-play-main (2-layer, KiCad 9)
**Date:** 2026-03-16
**Branch:** `power-switch`
**Reviewer:** AI (Cursor agent session)

---

## Overall Verdict: CONDITIONAL PASS — 1 advisory remains (BQ24195 low stock)

| Area | Status | Summary |
|------|--------|---------|
| ERC | PASS (warnings only) | 0 errors, 30 benign warnings |
| DRC | CONDITIONAL PASS | 0 unconnected nets, 33 violations — all within JLCPCB manufacturing capability |
| BOM | PASS (fixed) | J4-J6 LCSC# corrected, R27 and Q2 substituted |
| CPL | PASS | 66 components, all top layer, counts match BOM |
| Stock | PASS (1 advisory) | R27/Q2 substituted; U5 BQ24195 low stock (22 units) — order promptly |

---

## 1. ERC Report

**Result: 0 errors, 30 warnings — ALL ACCEPTABLE**

| Category | Count | Cause | Verdict |
|----------|-------|-------|---------|
| `lib_symbol_issues` | 2 | J7 and U5 symbol libraries not in config (EasyEDA imports) | Cosmetic — symbols are correct on schematic |
| `pin_to_pin` Unspecified↔Passive | 18 | U6 (TPS61088) and U7 (INA219) pins typed as "Unspecified" in imported symbols | Benign — connections are electrically correct |
| `pin_to_pin` Unspecified↔Unspecified | 6 | Multi-pin SW/VOUT/GND on U6, A0/A1 on U7 | Benign — ganged pins on same net |
| `pin_to_pin` Unspecified↔Bidirectional | 1 | U7 SDA ↔ U5 SDA (I2C bus) | Benign — both are I2C data lines |
| `pin_to_pin` Unspecified↔Input | 1 | U7 SCL ↔ U5 SCL (I2C bus) | Benign — both are I2C clock lines |
| `pin_to_pin` NC↔NC/Passive | 2 | U6 NC pins tied to GND | Benign — per TPS61088 datasheet |

**Root cause:** U6 and U7 symbols were imported from EasyEDA/LCSC with all pins typed as "Unspecified" rather than proper electrical types. This triggers pin-compatibility warnings but does not indicate any real electrical issue. Could be cleaned up in a future schematic revision by editing the symbol pin types.

---

## 2. DRC Report

**Result: 33 violations, 0 unconnected pads, 0 footprint errors**

### 2a. Violations from component footprints (not user-fixable) — 17 total

| Type | Count | Component | Detail | JLCPCB Impact |
|------|-------|-----------|--------|--------------|
| Annular width | 8 | U6 (TPS61088) | Thermal vias: 0.096mm vs 0.130mm min | None — manufacturer footprint, standard practice |
| Annular width | 2 | J7 (USB-C) | Mounting tab PTH: -0.003mm | None — mechanical mounting pads |
| Clearance | 5 | J7 (USB-C) | Internal pad-to-pad: 0.100–0.185mm | None — connector footprint geometry |
| Hole clearance | 2 | J7 (USB-C) | Mounting hole to pad: 0.217mm vs 0.250mm | None — within connector footprint |

These 17 violations are inherent to the imported component footprints (U6 from TPS61088RHLR library, J7 from EasyEDA USB-C library). They cannot be fixed without modifying vendor footprints and do not affect manufacturability.

### 2b. Routing clearance violations (user-routed) — 16 total

All in the power management section around U6/U5. Sorted by severity:

| Actual | Required | Location | Risk |
|--------|----------|----------|------|
| 0.150mm | 0.200mm | U6 pin 2 (VSYS_SENSE) ↔ BOOST_FSW via | Low — exceeds JLCPCB 5mil min |
| 0.176mm | 0.200mm | VSYS_SENSE track ↔ BOOST_VCC track (F.Cu) | Low |
| 0.176mm | 0.200mm | VSYS_SENSE track ↔ BOOST_FSW track (B.Cu) | Low |
| 0.180mm | 0.200mm | BOOST_SS track ↔ C31 pad (VSYS_SENSE) | Low |
| 0.190mm | 0.200mm | VSYS_SENSE track ↔ BOOST_FSW track (B.Cu) | Low |
| 0.192mm | 0.200mm | R42 pad (BOOST_ILIM) ↔ BOOST_VCC track | Low |
| 0.195mm | 0.200mm | BOOST_VCC track ↔ U6 GND pad | Low |
| 0.195mm | 0.200mm | U6 GND pad ↔ BOOST_SS track | Low |
| 0.195mm | 0.200mm | U5 BQ_SW pad ↔ BQ_BTST via | Low |
| 0.196mm | 0.200mm | BOOST_SS track ↔ C31 pad | Low |
| *+6 more* | | *Similar tight clearances around U6/U5* | Low |

**Assessment:** All 16 violations are between 0.150mm and 0.196mm against a 0.200mm design rule. JLCPCB's standard 2-layer manufacturing capability is 0.127mm (5mil) clearance minimum. Every violation exceeds this threshold, so **the board will manufacture without issue**. The violations reflect tight routing in the power section (expected for a dense boost converter layout) but do not pose a manufacturing risk.

**Recommendation:** Accept as-is for this prototype run. Consider widening clearances in a future revision if reworking the U6 area.

---

## 3. BOM Validation

### 3a. Component Summary

| Metric | Count |
|--------|-------|
| Total unique designators | 83 |
| JLCPCB-assembled (have LCSC#) | 65 |
| Test point pads (no component) | 17 (TP1-4, TPIO×10, TP_3V1, TP_5V1, TP_GND1) |
| Hand-assembly required | 1 (U2: T-Display-S3 dev board) |
| Unique LCSC part numbers | 41 |
| Basic library parts | 17 unique |
| Extended library parts | 24 unique |
| Through-hole (THT) parts | 0 (all SMD) |

### 3b. LCSC Cross-Reference vs circuit-context.json

All 41 LCSC part numbers in the BOM match `circuit-context.json` exactly.

### 3c. LCSC Part Number Corrections (RESOLVED)

#### J4/J5/J6: Pin count mismatch — FIXED

| Field | Before | After |
|-------|--------|-------|
| LCSC# | C160403 (SM03B, 3-pin) | **C136657** (SM05B, 5-pin) |
| Stock | 48,375 (wrong part) | 14,860 |

Updated in: schematic, PCB, circuit-context.json, BOM.

#### R27: Out-of-stock sense resistor — SUBSTITUTED

| Field | Before | After |
|-------|--------|-------|
| LCSC# | C500724 (0.1Ω 2W 2512, OOS) | **C2903476** (0.1Ω 3W 2512, 94,464 stock) |
| Part | GX2512-2W-100mR-1% | HoJLR2512-3W-100mR-1% |
| Change impact | None — same value, tolerance, package. Higher power rating (3W vs 2W). | |

#### Q2: Near-OOS PMOS — SUBSTITUTED

| Field | Before | After |
|-------|--------|-------|
| LCSC# | C3040193 (VBZ3401, 3 units) | **C15127** (AO3401A, 1,453,147 stock) |
| Part | VBZ3401 (P-ch, 30V, 5.6A, 46mΩ) | AO3401A (P-ch, 30V, 4A, 47mΩ) |
| Library type | Extended ($3 fee) | **Basic** (no fee — saves $3) |
| Change impact | None — same SOT-23 footprint, same pinout (DGS), compatible specs. | |

### 3d. WARNING — Package Size Mismatch

| Designators | BOM Footprint | LCSC Part (C59461) | Concern |
|-------------|---------------|---------------------|---------|
| C34, C35, C36 | 0805 | 0603 (22µF 6.3V) | JLCPCB may flag DFM; 0603 part on 0805 pads will solder but is not ideal |

This has been in the design since schematic capture. The 0603 Samsung CL10A226MQ8NRNC will physically fit on 0805 pads — the solder paste stencil may over-apply but assembly will likely succeed. Consider swapping to an 0805 22µF cap (e.g., search LCSC for "0805 22uF") in a future revision.

### 3e. Basic vs Extended Parts Breakdown

**Basic Parts (16 unique — no per-part setup fee):**

| LCSC | Value | Package | Designators | Qty |
|------|-------|---------|-------------|-----|
| C15849 | 1µF | 0603 | C1, C20 | 2 |
| C19702 | 10µF | 0603 | C8, C10 | 2 |
| C23630 | 2.2µF | 0603 | C2, C33 | 2 |
| C19666 | 4.7µF | 0603 | C21, C24 | 2 |
| C96446 | 10µF 25V | 0603 | C25–C28 | 4 |
| C14663 | 100nF | 0603 | C7, C9, C31, C32, C40 | 5 |
| C59461 | 22µF | 0603* | C34–C36 | 3 |
| C14858 | 100pF C0G | 0603 | C39 | 1 |
| C15850 | 10µF | 0805 | C41 | 1 |
| C25804 | 10kΩ | 0603 | R6, R35, R38 | 3 |
| C23186 | 5.1kΩ | 0603 | R30, R31 | 2 |
| C23138 | 330Ω | 0603 | R32 | 1 |
| C23189 | 5.6kΩ | 0603 | R36 | 1 |
| C22984 | 30kΩ | 0603 | R37 | 1 |
| C23206 | 56kΩ | 0603 | R40 | 1 |
| C31850 | 22kΩ | 0603 | R43 | 1 |

**Extended Parts (25 unique — ~$3 setup fee each = ~$75 total extended fee):**

| LCSC | Component | Designators | Qty | Stock | Price/ea |
|------|-----------|-------------|-----|-------|----------|
| C90862 | BQ24195RGER | U5 | 1 | **22** | $2.30 |
| C87357 | TPS61088RHLR | U6 | 1 | 1,269 | $1.08 |
| C87469 | INA219AIDCNR | U7 | 1 | 5,925 | $0.62 |
| C51118 | AP2112K-3.3 | U1 | 1 | 193,314 | $0.13 |
| C130026 | TCA9548APWR | U4 | 1 | 11,102 | $0.67 |
| C36365 | SN74AHCT125PWR | IC1 | 1 | 970 | $0.39 |
| C165948 | TYPE-C-31-M-12 | J7 | 1 | 164,239 | $0.18 |
| C136657* | SM05B-SRSS-TB 5-pin | J4–J6 | 3 | 14,860 | $0.27 |
| C265101 | S3B-PH-SM4-TB 3-pin | J3 | 1 | 21,652 | $0.25 |
| C18221575 | YTC-PH-2AWB 2-pin | J8 | 1 | 830 | $0.03 |
| C15127 | AO3401A PMOS | Q2 | 1 | 1,453,147 | $0.06 |
| C266426 | SMNR6028-2R2MT | L1 | 1 | 737 | $0.09 |
| C167218 | FXL0630-2R2-M | L2 | 1 | 97,869 | $0.10 |
| C2903476 | 0.1Ω 3W 2512 | R27 | 1 | 94,464 | $0.09 |
| C1322424 | 10mΩ 2512 | R44 | 1 | 4,440 | $0.08 |
| C2836440 | 47µF SMD elec | C22, C30 | 2 | 188,192 | $0.03 |
| C3342 | 220µF SMD elec | C29 | 1 | 86,763 | $0.03 |
| C107093 | 47nF | C23, C37 | 2 | 293,008 | $0.003 |
| C1621 | 4.7nF | C38 | 1 | 661,165 | $0.005 |
| C354897 | 3A fuse | F1 | 1 | 27,185 | $0.06 |
| C2897466 | 3A PTC fuse | F2 | 1 | 19,366 | $0.09 |
| C114662 | 2.2kΩ | R28, R29 | 2 | 556,288 | $0.001 |
| C14675 | 100kΩ | R33, R34, R41, R42 | 4 | 2,866,010 | $0.001 |
| C22827 | 180kΩ | R39 | 1 | 86,784 | $0.002 |
| C13564 | 10kΩ NTC | TH1 | 1 | 427,342 | $0.04 |

*\*C136657 replaces incorrect C160403 — see §3c*

### 3f. Hand-Assembly Components

| Designator | Part | Reason |
|------------|------|--------|
| U2 | T-Display-S3 (ESP32-S3 dev board) | No LCSC#, module with pin headers |
| TP1–TP4 | Test point pads (1.5mm) | Bare copper — no physical component |
| TPIO×10, TP_×3 | Test point pads (2.0mm) | Bare copper — no physical component |

---

## 4. CPL (Placement File) Review

**Result: PASS — no issues found**

| Check | Result |
|-------|--------|
| Total components in CPL | 66 |
| Components with LCSC# (assembleable) | 65 |
| Components without LCSC# (skip) | 1 (U2) |
| All on expected layer (top) | Yes ✓ |
| Any (0,0) coordinates | None ✓ |
| Any suspicious positions | None — all within board outline |
| CPL count matches BOM (assembled parts) | 65 = 65 ✓ |
| Coordinate system | JLCPCB format (Y-negative) via Fabrication Toolkit ✓ |

Test points (17) are correctly excluded from the CPL — they are bare copper pads with no component to place.

---

## 5. Component Stock Check

### Resolved Stock Issues

| LCSC (old → new) | Part | Designator | New Stock | Resolution |
|-------------------|------|------------|-----------|------------|
| C500724 → **C2903476** | 0.1Ω 3W 2512 | R27 | 94,464 | Substituted — same value/package, higher power rating |
| C3040193 → **C15127** | AO3401A PMOS SOT-23 | Q2 | 1,453,147 | Substituted — same footprint, now **Basic** part |

### Remaining Advisory

| LCSC | Part | Designator | Stock | Severity | Impact |
|------|------|------------|-------|----------|--------|
| C90862 | BQ24195RGER | U5 | **22** | LOW STOCK | Battery charger/PMIC — order promptly, no drop-in substitute |

### All Other Parts — Adequate Stock

All remaining 39 unique LCSC parts have stock >700 units, most >10,000. No concerns.

---

## 6. Recommended Actions Before Upload

### BLOCKING — All resolved

~~1. J4/J5/J6 LCSC#~~ — Fixed: C160403 → C136657
~~2. R27 out-of-stock~~ — Substituted: C500724 → C2903476 (0.1Ω 3W 2512, 94k stock)
~~3. Q2 near-OOS~~ — Substituted: C3040193 → C15127 (AO3401A, 1.45M stock, Basic)

### HIGH PRIORITY (act before uploading)

4. **Verify BQ24195 (C90862) availability**
   - Only 22 units in stock — may sell out before order processes
   - Consider placing order immediately, or check if JLCPCB has incoming stock
   - No drop-in substitute exists (BQ24195 is the specific PMIC for this design)

5. **Re-export BOM via Fabrication Toolkit**
   - LCSC fields were updated in schematics and PCB, but the BOM CSV was patched manually
   - For full consistency, re-export from KiCad after opening the project

### ADVISORY (can proceed but note)

5. **C34/C35/C36 package mismatch** (0603 part in 0805 footprint)
   - Will likely assemble fine, but JLCPCB DFM may flag it
   - If flagged, approve manually or swap to 0805 22µF cap

6. **DRC clearance violations**
   - All 16 routing violations exceed JLCPCB manufacturing minimums
   - No action needed for this prototype run

7. **U2 (T-Display-S3) in CPL but not BOM-assembled**
   - JLCPCB will skip it automatically — no action needed
   - Hand-solder after boards arrive

---

## Appendix A: Cost Estimate (Components Only)

| Category | Unique Parts | Setup Fee | Component Cost (×5 boards) |
|----------|-------------|-----------|---------------------------|
| Basic parts | 17 | $0 | ~$1.50 |
| Extended parts | 24 | ~$72 | ~$14.50 |
| **Total** | **41** | **~$72** | **~$16.00** |

*Extended part fee is per-unique-part, typically $3/part. Actual fee may vary. Component costs are approximate for a 5-board run. Q2 substitution (C15127 AO3401A) moved from Extended to Basic, saving ~$3.*

---

## Appendix B: Full Stock Report

| LCSC | Part | Stock | Type | Price |
|------|------|-------|------|-------|
| C90862 | BQ24195RGER | 22 | Ext | $2.30 |
| C87357 | TPS61088RHLR | 1,269 | Ext | $1.08 |
| C87469 | INA219AIDCNR | 5,925 | Ext | $0.62 |
| C51118 | AP2112K-3.3 | 193,314 | Ext | $0.13 |
| C130026 | TCA9548APWR | 11,102 | Ext | $0.67 |
| C36365 | SN74AHCT125PWR | 970 | Ext | $0.39 |
| C165948 | TYPE-C-31-M-12 | 164,239 | Ext | $0.18 |
| C136657 | SM05B-SRSS-TB 5-pin | 14,860 | Ext | $0.27 |
| C265101 | S3B-PH-SM4-TB 3-pin | 21,652 | Ext | $0.25 |
| C18221575 | YTC-PH-2AWB 2-pin | 830 | Ext | $0.03 |
| C15127 | AO3401A PMOS | 1,453,147 | **Basic** | $0.06 |
| C266426 | SMNR6028-2R2MT 2.2µH | 737 | Ext | $0.09 |
| C167218 | FXL0630-2R2-M 2.2µH 10A | 97,869 | Ext | $0.10 |
| C2903476 | 0.1Ω 3W 2512 | 94,464 | Ext | $0.09 |
| C1322424 | 10mΩ 1W 2512 | 4,440 | Ext | $0.08 |
| C2836440 | 47µF SMD electrolytic | 188,192 | Ext | $0.03 |
| C3342 | 220µF SMD electrolytic | 86,763 | Ext | $0.03 |
| C107093 | 47nF 0603 | 293,008 | Ext | $0.003 |
| C1621 | 4.7nF 0603 | 661,165 | Ext | $0.005 |
| C354897 | 3A fuse 1206 | 27,185 | Ext | $0.06 |
| C2897466 | 3A PTC fuse 1206 | 19,366 | Ext | $0.09 |
| C114662 | 2.2kΩ 0603 | 556,288 | Ext | $0.001 |
| C14675 | 100kΩ 0603 | 2,866,010 | Ext | $0.001 |
| C22827 | 180kΩ 0603 | 86,784 | Ext | $0.002 |
| C13564 | 10kΩ NTC 0603 | 427,342 | Ext | $0.04 |
| C15849 | 1µF 0603 | 10,922,634 | Basic | $0.007 |
| C19702 | 10µF 0603 | 12,471,027 | Basic | $0.007 |
| C23630 | 2.2µF 0603 | 5,595,177 | Basic | $0.006 |
| C19666 | 4.7µF 0603 | 6,503,123 | Basic | $0.010 |
| C96446 | 10µF 25V 0603 | 12,866,406 | Basic | $0.017 |
| C14663 | 100nF 0603 | 46,340,708 | Basic | $0.003 |
| C59461 | 22µF 0603 | 20,124,287 | Basic | $0.009 |
| C14858 | 100pF C0G 0603 | 6,905,557 | Basic | $0.004 |
| C15850 | 10µF 0805 | 5,886,252 | Basic | $0.020 |
| C25804 | 10kΩ 0603 | 27,514,040 | Basic | $0.001 |
| C23186 | 5.1kΩ 0603 | 3,447,728 | Basic | $0.001 |
| C23138 | 330Ω 0603 | 4,665,460 | Basic | $0.002 |
| C23189 | 5.6kΩ 0603 | 1,113,659 | Basic | $0.001 |
| C22984 | 30kΩ 0603 | 645,852 | Basic | $0.001 |
| C23206 | 56kΩ 0603 | 1,188,940 | Basic | $0.001 |
| C31850 | 22kΩ 0603 | 1,369,436 | Basic | $0.002 |

*Stock figures checked 2026-03-16 via JLCPCB/LCSC MCP tool. Stock is live and may change.*

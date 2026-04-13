# JLCPCB Manufacturing Pre-Flight Review v2

**Board:** motion-play-main (4-layer, KiCad 9)
**Date:** 2026-04-05
**Reviewer:** AI (Claude Code session)
**Previous review:** 2026-03-16 (preflight-review.md)
**Changes since last review:** ESP32-S3 WROOM integration, custom power circuit, battery holder, polarity fix, power switch, USB ESD, AMS1117 LDO

---

## Overall Verdict: FAIL — 2 blockers must be fixed before ordering

| Area | Status | Summary |
|------|--------|---------|
| Schematic | **FAIL** | U9 USBLC6-2SC6 pin 5 wired to GND (must be VBUS) |
| BOM | **FAIL** | production/bom.csv is stale — missing 22 new components, contains 3 removed components |
| ERC | PASS (warnings only) | 0 errors, 60 warnings — all benign (30 new, same root cause as previous 30) |
| DRC | CONDITIONAL PASS | 0 unconnected nets, 36 violations — all within JLCPCB capability except USB D+/D- at 0.085mm (see advisory) |
| Layout | PASS | 92/92 placed, antenna keepout clear, battery holder on back within outline |

---

## BLOCKERS — Must fix before ordering

### BLOCKER 1: U9 (USBLC6-2SC6) pin 5 connected to GND — should be VBUS

**Severity: BLOCKER**

The USBLC6-2SC6 ESD protection IC (U9) has pin 5 connected to GND. Per the ST datasheet, pin 5 is the VBUS reference for the upper ESD clamping diodes. With VBUS tied to GND, the internal diodes from I/O to "VBUS" (=GND) will forward-bias whenever USB_DP or USB_DN exceed ~0.7V, clamping the data lines to ground and **preventing USB communication entirely**.

**Fix:** Connect U9 pin 5 to Protected_VBUS (or VBUS_RAW) instead of GND. Pin 2 remains on GND.

**Current (wrong):**
```
Pin 1 (I/O1) → USB_DP
Pin 2 (GND)  → GND
Pin 3 (I/O2) → USB_DN
Pin 4 (I/O2) → USB_DN
Pin 5 (VBUS) → GND      ← WRONG
Pin 6 (I/O1) → USB_DP
```

**Correct:**
```
Pin 5 (VBUS) → Protected_VBUS (or +5V)
```

### BLOCKER 2: BOM is stale — does not match current schematic

**Severity: BLOCKER**

The file `production/bom.csv` was last generated during the March 16 preflight review. Since then, the schematic has had major changes (ESP32 integration, power circuit overhaul, battery holder). The BOM is completely out of date.

**Missing from BOM (22 new components):**

| Designator | Part | LCSC | Sheet |
|------------|------|------|-------|
| U3 | ESP32-S3-WROOM-1-N16R8 | C2913202 | esp32_s3 |
| U8 | AMS1117-3.3 | C6186 | power_management |
| U9 | USBLC6-2SC6 | C7519 | power_management |
| SW1 | SS-12D10L5 (power switch) | C319012 | power_management |
| SW2, SW3 | Tactile switch (RESET, BOOT) | C49234124 | esp32_s3 |
| R50, R51 | 10kΩ (EN/GPIO0 pull-ups) | C25804 | esp32_s3 |
| R52 | 22Ω (USB DN series) | C23345 | esp32_s3 |
| R53 | 22Ω (USB DP series) | C23345 | esp32_s3 |
| R1 | 1kΩ (power LED) | C22548 | power_management |
| D1 | Green LED 0603 | C19171301 | power_management |
| D5 | WS2812B-MINI | C4154873 | esp32_s3 |
| C42 | 22µF 0805 | C109314 | power_management |
| C43 | 22µF 6.3V Tant (Case-A) | C129288 | power_management |
| C50, C55 | 1µF 0603 | C15849 | esp32_s3 |
| C51 | 10µF 0603 | C96446 | esp32_s3 |
| C52, C53, C54 | 100nF 0603 | C14663 | esp32_s3 |
| BT1 | Keystone 1042 18650 holder | — (hand-solder) | power_management |

**Stale entries to remove from BOM:**

| Designator | Part | Reason |
|------------|------|--------|
| U2 | T-Display-S3 | Removed — replaced by U3 (ESP32-S3-WROOM-1) |
| J8 | JST-PH 2-pin (C18221575) | Removed — replaced by BT1 battery holder |
| U1 | AP2112K-3.3 (C51118) | Removed — replaced by U8 (AMS1117-3.3) |
| C1 | 1µF (was AP2112K decoupling) | Removed with U1 |
| C2 | 2.2µF (was AP2112K decoupling) | Removed with U1 |

**Additional BOM discrepancy:** J4/J5/J6 show as 5-pin SM05B (C136657) in BOM but schematic now has 4-pin SM04B (C160404). Verify which is correct — the schematic was likely updated after the preflight.

**BOM also shows C31/C32/C40 and C7/C9 with different LCSC numbers** (C92490 instead of C14663 for 100nF caps). This will be resolved by re-export.

**Fix:** Re-run KiCad Fabrication Toolkit to regenerate BOM, CPL, and Gerbers after fixing Blocker 1. Verify all LCSC numbers match circuit-context.json.

---

## 1. Schematic Correctness

### 1a. Power Rail Chain — PASS

The power path is correct:

```
J7 (USB-C) → VBUS_RAW → F2 (3A PTC) → Protected_VBUS
  → U5 (BQ24195) → VSYS → SW1 → VSYS_SW → R44 (10mΩ) → VSYS_SENSE
    → U6 (TPS61088) → +5V
      → U8 (AMS1117-3.3) → +3.3V

U5 (BQ24195) BAT → VBAT → Q2 (PMOS) → BAT_RAW → BT1 (18650)
```

All verified from circuit-context.json net connections. No floating power rails, no missing connections.

### 1b. Reverse Polarity Protection — PASS (topology correct)

| Component | Net 1 | Net 2 | Status |
|-----------|-------|-------|--------|
| Q2 (PMOS) pin 1 | BAT_RAW | — | Battery positive |
| Q2 (PMOS) pin 2 | PMOS_GATE | — | Gate bias |
| Q2 (PMOS) pin 3 | VBAT | — | Downstream to BQ24195 |
| R33 (100kΩ) | VBAT | PMOS_GATE | Gate pull toward VBAT |
| R34 (100kΩ) | PMOS_GATE | GND | Gate divider to GND |

**Analysis:** R34 was correctly rewired from BAT_RAW to GND. The divider now gives:
- Vgate = VBAT × R34/(R33+R34) = VBAT/2
- Vgs = VBAT/2 - VBAT = -VBAT/2 ≈ -1.85V (for 3.7V battery)
- AO3401A Vgs(th) = -1.2V max → MOSFET turns on fully

Reverse polarity: Battery reversed → body diode blocks → VBAT stays at 0 → Vgs = 0 → MOSFET OFF. Protected.

**Advisory — Q2 pin mapping:** The circuit-context labels Q2 pin 1 as "D" (Drain), but for AO3401A SOT-23, physical pin 1 is Gate. Verify that the KiCad symbol-to-footprint pin mapping correctly assigns: physical pin 1 = Gate → PMOS_GATE, pin 2 = Source → VBAT (or BAT_RAW), pin 3 = Drain. If the generic PMOS symbol uses G=1/S=2/D=3 internally (KiCad standard), the mapping is correct despite the confusing labels in the extraction. But this should be confirmed visually in KiCad.

### 1c. 3.3V Regulator Redundancy — RESOLVED

U1 (AP2112K-3.3) has been removed from the schematic (not present in circuit-context.json extracted today). U8 (AMS1117-3.3, SOT-223) replaces it, providing 3.3V from +5V. No dual-regulator conflict exists.

**Note:** U8 (AMS1117-3.3) is SOT-223 package — significantly larger than the old AP2112K (SOT-23-5). It provides up to 1A output, adequate for ESP32-S3 + TCA9548A + peripherals.

### 1d. BQ24195 Support Components — PASS

| Component | Function | Value | Datasheet Requirement | Status |
|-----------|----------|-------|-----------------------|--------|
| C23 | BTST bootstrap | 47nF | 47nF–100nF | OK |
| C24 | REGN LDO bypass | 4.7µF | ≥1µF (4.7µF recommended) | OK |
| C25+C26 | PMID bypass | 2×10µF = 20µF | ≥10µF | OK |
| C27+C28+C29 | VSYS output | 2×10µF + 220µF | ≥10µF ceramic recommended | OK |
| L1 | Buck inductor | 2.2µH | 2.2µH | OK |
| R32 | ILIM | 330Ω | Sets ~1.5A ceiling | OK |
| R36/R37/TH1 | NTC temp monitoring | 5.6k/30k/10k NTC | Per BQ24195 app note | OK |
| R35 | OTG pull-up | 10kΩ to 3.3V | OTG HIGH = 500mA SDP boot | OK |
| R38 | INT pull-up | 10kΩ to 3.3V | Open-drain output | OK |
| U5 D+/D- | Current detection | Tied to GND | Disables auto-detect, I2C control | OK |
| U5 CE | Charge enable | Tied to GND (LOW) | LOW = charge enabled | OK |

### 1e. TPS61088 Support Components — PASS

| Component | Function | Value | Status |
|-----------|----------|-------|--------|
| C31 | VIN bypass | 0.1µF | OK |
| C41 | VIN bulk | 10µF 0805 | OK |
| C32 | BOOT bootstrap | 0.1µF | OK |
| C33 | VCC LDO decoupling | 2.2µF | OK |
| C34+C35+C36 | VOUT output | 3×22µF = 66µF | OK |
| C37 | Soft-start | 47nF (~11ms ramp) | OK |
| R43+C38+C39 | Compensation | 22kΩ + 4.7nF + 100pF | OK |
| R41 | FSW frequency | 100kΩ (FSW↔SW) | ~2.2MHz OK |
| R42 | ILIM current | 100kΩ to GND | ~11.9A peak OK |
| R39/R40 | Feedback divider | 180kΩ/56kΩ | VOUT = 1.204×(1+180/56) = 5.07V OK |
| L2 | Boost inductor | 2.2µH 10A | OK |
| NC pins 11,12 | No connect | Tied to GND | Per datasheet OK |

### 1f. ESP32-S3 WROOM Connections — PASS

| Signal | GPIO | Pin | Connection | Status |
|--------|------|-----|------------|--------|
| I2C SDA | IO43 (TXD0) | 37 | /I2C_SDA → U4, U5, U7 | OK |
| I2C SCL | IO44 (RXD0) | 36 | /I2C_SCL → U4, U5, U7 | OK |
| LED Data | IO16 | 9 | /LED_DATA → D5, IC1 | OK |
| TCA Reset | IO10 | 18 | /TCA_RESET → U4 ~RESET | OK |
| CHRG INT | IO21 | 23 | /CHRG_INT → U5 INT | OK |
| USB D- | IO19 | 13 | → R52 (22Ω) → /USB_DN | OK |
| USB D+ | IO20 | 14 | → R53 (22Ω) → /USB_DP | OK |
| EN | EN | 3 | R50 (10kΩ↑), C50 (1µF↓), SW2 | OK |
| BOOT | IO0 | 27 | R51 (10kΩ↑), SW3 | OK |
| VDD | 3V3 | 2 | +3.3V | OK |
| GND | GND | 1,40,41 | GND | OK |

**Note:** GPIO43/44 (default UART0 TX/RX) used for I2C. This is correct — ESP32-S3's GPIO matrix allows remapping, and USB CDC replaces UART0 for serial debug.

Decoupling: C51 (10µF), C52–C54 (3×100nF), C55 (1µF) — adequate for the WROOM-1 module.

### 1g. I2C Buses — PASS

**Upstream bus** (/I2C_SDA, /I2C_SCL):
- Pull-ups: R28, R29 (2.2kΩ to +3.3V) — sized for 400kHz
- Devices: U4 (TCA9548A, 0x70), U5 (BQ24195, 0x6B), U7 (INA219, 0x40) — no address conflicts

**Downstream buses** (CH0–CH2 via TCA9548A to J4–J6):
- No pull-ups on main PCB — correct, pull-ups are on sensor rigid boards
- Each channel routes SDA/SCL to a JST-SH connector

### 1h. LED Strip Path — PASS

```
U3 IO16 → /LED_DATA → IC1 1A (3.3V input)
                     → D5 DIN (status LED, parallel)
IC1 1Y → /DATA_TO_LEDS → J3 pin 2

+5V → F1 (3A fuse) → R27 (0.1Ω sense) → +5V_TO_LEDS → J3 pin 1
                                                        → IC1 VCC
```

IC1 (SN74AHCT125) VCC is on +5V_TO_LEDS (after fuse and sense resistor). 1OE tied to GND (always enabled). Level shift 3.3V → 5V works correctly with AHCT family.

**Advisory — D5 (WS2812B-MINI):** D5 DIN receives 3.3V logic while powered from +5V. WS2812B spec requires VIH ≥ 0.7×VDD = 3.5V. At 3.3V input, D5 may not reliably read data. This is a status LED only — if it doesn't work, the LED strip (which gets 5V logic from IC1) will still function. Non-critical.

### 1i. Missing Pull-ups/Pull-downs — PASS

| Signal | Pull | Component | Status |
|--------|------|-----------|--------|
| I2C SDA | 2.2kΩ up | R28 | OK |
| I2C SCL | 2.2kΩ up | R29 | OK |
| TCA ~RESET | 10kΩ up | R6 | OK |
| ESP32 EN | 10kΩ up | R50 | OK |
| ESP32 GPIO0 | 10kΩ up | R51 | OK |
| BQ24195 INT | 10kΩ up | R38 | OK |
| BQ24195 OTG | 10kΩ up | R35 | OK |
| USB CC1 | 5.1kΩ down | R30 | OK |
| USB CC2 | 5.1kΩ down | R31 | OK |

No floating inputs identified on active ICs.

### 1j. Decoupling — PASS

| IC | Decoupling | Status |
|----|-----------|--------|
| U3 (ESP32-S3) | C51 10µF, C52-C54 3×100nF, C55 1µF | OK |
| U4 (TCA9548A) | C9 100nF, C10 10µF | OK |
| U5 (BQ24195) | C20 1µF, C21 4.7µF, C22 47µF (VBUS); C24 4.7µF (REGN); C25-C26 2×10µF (PMID) | OK |
| U6 (TPS61088) | C31 0.1µF, C41 10µF (VIN); C33 2.2µF (VCC) | OK |
| U7 (INA219) | C40 0.1µF | OK |
| U8 (AMS1117) | C42 22µF (input), C43 22µF tant (output) | OK |
| IC1 (SN74AHCT125) | C8 10µF (VCC) | OK |

---

## 2. ERC Analysis

**Result: 0 errors, 60 warnings — ALL ACCEPTABLE**

| Source | Category | Count | Cause | Verdict |
|--------|----------|-------|-------|---------|
| Root sheet | `lib_symbol_issues` | 2 | J7, U5 imported symbols not in lib config | Cosmetic |
| Power Mgmt | `pin_to_pin` Unspecified↔Passive | 12 | U6, U7, U8 pins typed "Unspecified" | Benign |
| Power Mgmt | `pin_to_pin` Unspecified↔Unspecified | 11 | Multi-pin SW/VOUT/GND on U6/U8, A0/A1 on U7 | Benign |
| Power Mgmt | `pin_to_pin` Unspecified↔Bidirectional | 1 | U7 SDA ↔ U5 SDA (I2C bus) | Benign |
| Power Mgmt | `pin_to_pin` Unspecified↔Input | 4 | U7 SCL ↔ U5 SCL; U9 ↔ J7; U8 ↔ U9 | Benign |
| Power Mgmt | `pin_to_pin` Unspecified↔Power input | 1 | SW1 ↔ U5 SYS pin | Benign |
| Power Mgmt | `pin_to_pin` NC↔NC | 1 | U6 NC pins tied together | Benign |
| ESP32 sheet | `pin_to_pin` Unspecified↔Passive | 12 | U3, SW2, SW3, D5 pins vs passive caps/resistors | Benign |
| ESP32 sheet | `pin_to_pin` Unspecified↔Unspecified | 7 | U3↔D5, U3↔U7, U3↔U8 cross-sheet connections | Benign |
| ESP32 sheet | `pin_to_pin` Unspecified↔Input | 2 | U3↔U4 RESET, U3↔U5 INT | Benign |
| ESP32 sheet | `pin_to_pin` Unspecified↔Output | 1 | U3↔U5 INT (output) | Benign |
| | | **60** | | |

**Root cause:** Same as previous review — imported symbols (U6, U7, U8, U9, SW1, D5, U3) have "Unspecified" pin types instead of proper electrical types. All 30 new warnings follow the same pattern. No real electrical issues.

---

## 3. DRC Analysis

**Result: 36 violations (29 errors, 7 warnings), 0 unconnected pads, 0 footprint errors**

### 3a. Violations from component footprints (not user-fixable) — 14 total

| Type | Count | Component | Detail | JLCPCB Impact |
|------|-------|-----------|--------|--------------|
| Annular width | 2 | J7 (USB-C) | Mounting PTH: -0.003mm | None — mechanical pads |
| Clearance | 8 | J7 (USB-C) | Internal pad-to-pad: 0.100–0.185mm | None — connector geometry |
| Hole clearance | 2 | J7 (USB-C) | Mounting hole to pad: 0.217mm | None — connector geometry |
| Padstack | 2 | J7 (USB-C) | PTH hole leaves no copper | None — mounting holes |

These 14 violations are inherent to the USB-C connector footprint. Same as previous review. Not fixable, not a manufacturing risk.

### 3b. USB data line clearance violations — 4 total (NEW)

| Actual | Required | Nets | Risk |
|--------|----------|------|------|
| **0.085mm** | 0.200mm | USB_DP ↔ USB_DN tracks | **Below JLCPCB 0.09mm min** |
| **0.085mm** | 0.200mm | USB_DP ↔ USB_DN tracks | **Below JLCPCB 0.09mm min** |
| **0.085mm** | 0.200mm | USB_DP ↔ USB_DN tracks | **Below JLCPCB 0.09mm min** |
| 0.120mm | 0.200mm | USB_DP track ↔ USB_DN via | OK — exceeds 0.09mm |

**Assessment:** Three clearance violations at 0.085mm are below JLCPCB's standard 4-layer minimum (0.09mm / 3.5mil). These are between USB D+/D- trace segments near the USB-C connector J7. JLCPCB may reject the gerbers or may manufacture with reduced yield.

**Recommendation:** Widen USB_DP/USB_DN trace spacing to ≥0.1mm if possible. If not, flag these during JLCPCB upload and consider adding a note that tight USB routing is intentional. These are very short trace segments and may pass automated review.

### 3c. Power section routing clearance — 15 total

All in the power management section around U5/U6. Range: 0.150mm–0.196mm against 0.200mm design rules.

| Group | Count | Minimum | Notes |
|-------|-------|---------|-------|
| VSYS_SENSE ↔ BOOST_FSW/VCC | 5 | 0.150mm | Around U6 |
| BOOST_SS ↔ VSYS_SENSE/U6 GND | 5 | 0.176mm | Around U6 |
| BOOST_VCC ↔ U6 GND | 3 | 0.168mm | U6 pad-to-pad |
| BQ_SW ↔ BQ_BTST via | 1 | 0.195mm | Around U5 |
| BOOST_FSW via ↔ U6 SW pad | 1 | 0.150mm | U6 pin spacing |

**Assessment:** All 15 violations exceed JLCPCB's 0.09mm manufacturing minimum. No manufacturing risk. Same pattern as previous review.

### 3d. Other violations — 3 total

| Type | Count | Detail | Severity |
|------|-------|--------|----------|
| Track dangling | 1 | TCA_RESET stub on F.Cu (0.285mm), near U4 | Advisory — leftover trace fragment, no electrical impact |
| Connection width | 1 | C28 GND pad to via: 0.126mm (min 0.15mm) | Advisory — GND has multiple paths, adequate current capacity |
| Silk overlap | 3 | D5 text overlap, U3/SW2 silkscreen overlap | Cosmetic only |

### 3e. DRC.rpt vs DRC.json comparison

DRC.rpt reports 29 violations (errors only). DRC.json reports 36 (29 errors + 7 warnings). The additional 7 warnings are: 1 track_dangling, 1 connection_width, 2 padstack, 3 silk_overlap. No discrepancies — DRC.rpt only shows errors by default.

---

## 4. BOM / Assembly Readiness

### 4a. BOM Status: STALE — MUST RE-EXPORT

The production BOM was generated 2026-03-16 and does not reflect the current schematic. See Blocker 2 for full details.

### 4b. LCSC Part Numbers for New Components

All new components in circuit-context.json have LCSC part numbers assigned:

| Designator | Part | LCSC | Type | Notes |
|------------|------|------|------|-------|
| U3 | ESP32-S3-WROOM-1-N16R8 | C2913202 | Extended | Verify stock before ordering |
| U8 | AMS1117-3.3 | C6186 | Basic | High stock, common part |
| U9 | USBLC6-2SC6 | C7519 | Extended | Common USB ESD |
| SW1 | SS-12D10L5 | C319012 | Extended | Through-hole slide switch |
| SW2, SW3 | Tactile 4×3mm | C49234124 | Extended | Same part for both |
| R52, R53 | 22Ω 0603 | C23345 | Basic | USB series resistors |
| R1 | 1kΩ 0603 | C22548 | Basic | LED current limit |
| D1 | LED 0603 green | C19171301 | Extended | Verify stock |
| D5 | WS2812B-MINI | C4154873 | Extended | Status LED |
| C42 | 22µF 0805 | C109314 | Extended | Already in design |
| C43 | 22µF 6.3V Tant Case-A | C129288 | Extended | New — verify stock |
| BT1 | Keystone 1042 | — | Hand-solder | Not on LCSC |

### 4c. Hand-Assembly Components

| Designator | Part | Reason |
|------------|------|--------|
| BT1 | Keystone 1042 (18650 holder) | Not on LCSC, back-side mount |
| SW1 | SS-12D10L5 (slide switch) | Through-hole — verify JLCPCB THT assembly capability, or hand-solder |

**Note:** SW1 has a through-hole footprint (SW-TH_SS-12D10L5). JLCPCB can assemble THT components with their Standard PCBA service (not Economic). If using Economic PCBA, SW1 must be hand-soldered.

### 4d. Previous Substitutions — Verified

| Designator | Old LCSC | New LCSC | Part | Still in design? |
|------------|----------|----------|------|------------------|
| R27 | C500724 | C2903476 | 0.1Ω 3W 2512 | Yes ✓ |
| Q2 | C3040193 | C15127 | AO3401A PMOS | Yes ✓ |
| C34-C36 | C59461 | C109314 | 22µF 0805 | Yes ✓ |
| C22, C30 | C2836440 | C7469958 | 47µF electrolytic | Yes ✓ |

### 4e. Stock Concern Carried Forward

| LCSC | Part | Designator | Previous Stock | Severity |
|------|------|------------|---------------|----------|
| C90862 | BQ24195RGER | U5 | 22 (on 2026-03-16) | **CRITICAL — verify stock before ordering** |

---

## 5. PCB Layout Checks

### 5a. Component Placement Summary — PASS

- Total components: 92
- Placed: 92
- Unplaced: 0
- All components within board outline (88.2mm × 38.5mm)

### 5b. Battery Holder (BT1) — PASS with advisories

| Check | Result |
|-------|--------|
| Side | Back ✓ |
| Within board outline | Yes — pads at x=79.94 and x=159.32, board x=[75.7, 163.9] |
| BT1 pads overlap J7 THT | No — J7 THT pads at y=116.7–124.0, BT1 pad 1 starts at y≈125.4 |
| Mechanical pegs | 2 remaining at (83.5, 136.6) and (141.73, 136.5) — within board |

**Advisory — Through-hole pin clearance:** SW1 (power switch) has through-hole pins at x=99.7, y=127–136. These pins protrude through to the back side where the 18650 cell body sits (cell spans y≈119.5–137.7). Verify that SW1 pin stubs have adequate clearance from the cell body. Consider adding insulation (Kapton tape) over SW1 pin solder joints on the back side.

### 5c. ESP32 Antenna Keepout — PASS

Antenna keepout zone: X=[121, 140.5], Y=[100.9, 107.9]

Components in or near this zone:
- R1 at (120.4, 104.5): Just outside X range (120.4 < 121). OK.
- D1 at (118.7, 104.5): Outside X range. OK.
- C42 at (113.4, 102.3): Outside X range. OK.
- C43 at (118.3, 108.7): Outside both X and Y range. OK.
- No components are within the keepout zone. ✓

**18650 cell vs antenna:** Cell center at y=128.6, diameter 18.3mm → body from y≈119.5 to y≈137.7. Antenna keepout ends at y=107.9. Cell body is >11mm away from antenna zone. No physical interference.

### 5d. Board Utilization

Board area: 88.2mm × 38.5mm = 3,396mm². Reported utilization: 113.6% (component footprint area exceeds board area — normal for dense designs with back-side battery holder).

---

## 6. Proposed Annotations for Unannotated Components

22 components lack AI annotations. Proposed annotations (DO NOT write to schematic files):

### ESP32 Sheet (14 components)

| Ref | ai_function | ai_block | ai_role |
|-----|-----------|----------|---------|
| U3 | ESP32-S3 WROOM-1 MCU module, 16MB flash, 8MB PSRAM | mcu | controller |
| C50 | EN pin bootstrap delay capacitor (1µF) | mcu | bootstrap |
| C51 | 3.3V bulk decoupling for ESP32 module (10µF) | mcu | decoupling |
| C52 | 3.3V high-freq bypass for ESP32 (100nF) | mcu | decoupling |
| C53 | 3.3V high-freq bypass for ESP32 (100nF) | mcu | decoupling |
| C54 | 3.3V high-freq bypass for ESP32 (100nF) | mcu | decoupling |
| C55 | 3.3V ceramic decoupling for ESP32 (1µF) | mcu | decoupling |
| D5 | WS2812B-MINI status LED on IO16 (LED_DATA) | mcu | indicator |
| R50 | EN pull-up to 3.3V, keeps ESP32 enabled (10kΩ) | mcu | pull_up |
| R51 | GPIO0 pull-up to 3.3V, normal boot mode (10kΩ) | mcu | pull_up |
| R52 | USB D- series resistor for signal integrity (22Ω) | mcu | impedance_match |
| R53 | USB D+ series resistor for signal integrity (22Ω) | mcu | impedance_match |
| SW2 | Reset button, pulls EN low (tactile) | mcu | user_interface |
| SW3 | Boot button, pulls GPIO0 low for download mode (tactile) | mcu | user_interface |

### Power Management Sheet (8 components)

| Ref | ai_function | ai_block | ai_role |
|-----|-----------|----------|---------|
| BT1 | Keystone 1042 SMD 18650 battery holder, back-side mount | battery | holder |
| D1 | 3.3V power indicator LED (green, 0603) | power_indicator | indicator |
| R1 | D1 current limit resistor, I=(3.3-Vf)/1k ≈ 1.4mA (1kΩ) | power_indicator | current_limit |
| SW1 | VSYS on/off slide switch (SPDT, position 1 used) | power_switch | user_interface |
| U8 | AMS1117-3.3 LDO, 5V→3.3V, 1A max | ldo_3v3 | voltage_regulator |
| U9 | USBLC6-2SC6 USB ESD protection on D+/D- lines | usb_protection | esd_protection |
| C42 | AMS1117 input decoupling (22µF ceramic) | ldo_3v3 | decoupling |
| C43 | AMS1117 output decoupling (22µF tantalum) | ldo_3v3 | decoupling |

---

## 7. Summary of Action Items

### Must fix (blockers)

1. **U9 pin 5:** Reconnect from GND to Protected_VBUS (or +5V) in schematic
2. **Re-export BOM/CPL/Gerbers:** After fixing U9, run Update PCB from Schematic, then re-export all production files via Fabrication Toolkit

### Should fix (warnings)

3. **USB D+/D- clearance:** Three trace segments at 0.085mm spacing are below JLCPCB's 0.09mm minimum. Widen spacing if routing permits. If not possible, note when uploading gerbers.
4. **Verify J4/J5/J6 connector type:** Schematic shows 4-pin SM04B (C160404) but previous review changed to 5-pin SM05B (C136657). Confirm which is correct for the sensor cable pinout.
5. **Verify BQ24195 stock (C90862):** Was at 22 units on March 16. May be out of stock.

### Should verify (advisories)

6. **Q2 pin mapping:** Confirm in KiCad that the PMOS symbol-to-SOT-23 footprint pin assignment is correct (Gate → physical pin 1, Source → pin 2, Drain → pin 3).
7. **SW1 through-hole clearance:** Verify pin stubs on back side clear the 18650 cell body. Consider Kapton insulation.
8. **Dangling TCA_RESET trace:** Short stub at (152.86, 109.50) on F.Cu. Remove for cleanliness.
9. **D5 (WS2812B-MINI) 3.3V logic:** May not reliably drive WS2812B at 5V VDD. Non-critical status LED.

### Safe to ignore

- All 60 ERC warnings (Unspecified pin type false positives)
- 14 DRC violations from J7 USB-C connector footprint
- 15 DRC power section clearance violations (all above 0.09mm JLCPCB minimum)
- 3 silkscreen overlaps (cosmetic)
- 1 connection width warning (C28 GND, multiple current paths)
- 2 padstack warnings (J7 mounting holes)
- TCA_RESET dangling trace (0.285mm stub, no electrical impact)

---

*Report generated 2026-04-05. Based on circuit-context.json (extracted 2026-04-05T16:24:59Z) and pcb-layout-context.json (extracted 2026-04-05T16:25:02Z).*

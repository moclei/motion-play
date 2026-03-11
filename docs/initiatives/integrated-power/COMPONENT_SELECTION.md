# Integrated Power Management — Component Selection (Phase 1)

## Active ICs — Confirmed via JLCPCB MCP

| Component | Part Number | LCSC | Stock | Price | Package | Library |
|-----------|------------|------|-------|-------|---------|---------|
| Boost Converter | TPS61088RHLR | C87357 | 4,972 | $1.08 | VQFN-20-EP (3.6×4.6mm) | Extended |
| Battery Charger | BQ24195RGER | C90862 | 24 | $2.30 | VQFN-24-EP (4×4mm) | Extended |
| Power Monitor | INA219AIDCNR | C87469 | 7,586 | $0.58 | SOT-23-8 | Extended |

**Fallback charger:** BQ25896RTWR (C181475) — 113 units, $1.71, QFN-24-EP (4×4mm). Pin-incompatible with BQ24195 but similar I2C register set. Only needed if BQ24195RGER stock drops to zero.

**Note on BQ24195 variants:** The RGET variant (C2876710) used in the reference power PCB is out of stock (0 units). RGER is identical silicon, different packaging tape — no design changes needed.

## Critical Design Finding: Boot-Time Input Current Limit

The PLAN.md assumed ~1-1.5A boot-time input current from the 2.7kΩ ILIM resistor. **This is incorrect.** Datasheet analysis reveals:

1. **ILIM with 2.7kΩ:** Formula gives ~180mA, clamped at internal 500mA floor
2. **D+/D- grounded + OTG LOW:** Detects as USB SDP → I2C default = 100mA
3. **Effective boot limit = min(ILIM, I2C) = 100mA** — far too low for system boot

At 100mA from VBUS, available power at the +5V rail is ~400mW (after BQ24195 and boost losses). The ESP32-S3 alone needs ~600mW+ to boot. **The system cannot boot on USB-only with these settings.**

### Resolution

Change two components from the reference design:

| Change | Reference Design | New Design | Rationale |
|--------|-----------------|------------|-----------|
| **ILIM resistor** | 2.7kΩ (R6) | **330Ω** | Sets hardware ceiling at ~1.5A (KILIM/RILIM = 485/330 = 1.47A) |
| **OTG pin** | Tied to GND | **Tied to VCC (3.3V) via 10kΩ** | SDP detection with OTG HIGH → 500mA boot current |

Post-fix boot sequence:
- Boot: 500mA from VBUS (~2.1W at +5V rail) — sufficient for ESP32 + boost converter startup
- Firmware writes REG00[2:0] = 101 (1.5A) → clamped by ILIM hardware limit at 1.5A
- Full system operational on USB-only at 1.5A input (7.5W available at VBUS)

**Safety note:** OTG HIGH in default charge mode (CHG_CONFIG=01) only affects SDP current selection. It does NOT enable boost output — that requires CHG_CONFIG=10, which is never set in our firmware.

## Boost Converter: TPS61088 — Passive Values

### Feedback Divider (sets VOUT = 5.07V)

| Ref | Value | LCSC | Stock | Price | Part | Notes |
|-----|-------|------|-------|-------|------|-------|
| R_FB_TOP | 180kΩ 1% 0603 | C22827 | 114,474 | $0.002 | 0603WAF1803T5E | Extended |
| R_FB_BOT | 56kΩ 1% 0603 | C23206 | 1,263,866 | $0.001 | 0603WAF5602T5E | Basic |

Formula: VOUT = VREF × (1 + R_TOP/R_BOT) = 1.204 × (1 + 180/56) = 1.204 × 4.214 = **5.07V**

Acceptable — 1.4% above nominal 5.0V. Within WS2812B operating range (4.5-5.5V) and AP2112K input range.

### Inductor

| Ref | Value | LCSC | Stock | Price | Part | Package |
|-----|-------|------|-------|-------|------|---------|
| L_BOOST | 2.2µH, 10A Isat, 15mΩ DCR | C167218 | 110,139 | $0.10 | FXL0630-2R2-M | 7.0×6.6mm |

Peak inductor current at worst case (VIN=3.0V, VOUT=5V, IOUT=3A, η=85%): ~5.9A DC + ~0.25A ripple = **6.15A peak**. The 10A Isat provides 63% margin. The TPS61088 datasheet recommends ≥12A for the 9V/3A reference design, but for 5V/3A the input current is 40% lower — 10A Isat is adequate.

### Capacitors

| Ref | Value | LCSC | Notes |
|-----|-------|------|-------|
| C_VIN | 10µF ceramic 0805 X5R 10V | C15850 | Input power stage decoupling (from reference BQ24195 circuitry) |
| C_VIN_BYP | 0.1µF ceramic 0603 X7R | C14663 | VIN pin bypass, close to IC |
| C_BOOT | 0.1µF ceramic 0603 X7R | C14663 | BOOT to SW bootstrap |
| C_VCC | 2.2µF ceramic 0603 X5R | C23630 | Internal LDO decoupling |
| C_OUT (×3) | 22µF ceramic 0805 X5R 10V | C59461 | Output filtering (66µF total nominal) |
| C_SS | 47nF ceramic 0603 | — | Soft-start (~11ms ramp) |

### Other Passives

| Ref | Value | LCSC | Notes |
|-----|-------|------|-------|
| R_FREQ | 100kΩ 1% 0603 | C14675 | FSW→SW, sets ~2.2MHz switching frequency |
| R_ILIM_BOOST | 100kΩ 1% 0603 | C14675 | ILIM→AGND, sets 11.9A peak current limit |
| R_COMP | TBD | — | Loop compensation — value depends on load; use TPS61088 EVM values initially |
| C_COMP1 | TBD | — | Loop compensation |
| C_COMP2 | TBD | — | Loop compensation |

**Note:** Compensation network values (R_COMP, C_COMP1, C_COMP2) will be taken from the TPS61088 EVM reference design for 5V output during Phase 2 schematic spec. The TI WEBENCH tool can also calculate these.

## Battery Charger: BQ24195 — Passive Values

Carried forward from the reference power supply PCB (`hardware/pcb-power-supply/kicad/circuit-context.json`) with one change (ILIM resistor).

| Ref | Value | LCSC | Function | Changed? |
|-----|-------|------|----------|----------|
| C_BTST | 47nF (0.047µF) | — | Bootstrap cap, BTST→SW | Same (was 100nF in ref — datasheet says 47nF) |
| C_REGN | 4.7µF ceramic 0603 | C19666 | REGN internal LDO bypass | Same |
| C_PMID | 10µF ceramic 0603 | C96446 | PMID bypass (min 20µF recommended — may need 2×) | Review |
| C_VSYS (×2) | 10µF ceramic 0603 | C96446 | VSYS output decoupling | Same |
| C_VSYS_BULK | 220µF electrolytic | C3342 | VSYS bulk output | Same |
| C_VBUS | 1µF ceramic 0603 | C15849 | VBUS input bypass | Same |
| C_BAT | 47µF electrolytic | C2836440 | Battery terminal bulk | Same |
| L_BQ | 2.2µH (FNR6028S) | C266426 | BQ24195 switching inductor | Same |
| **R_ILIM** | **330Ω 1% 0603** | **C23138** | **ILIM resistor (~1.5A)** | **CHANGED from 2.7kΩ** |
| R_PMOS1 | 100kΩ 0603 | C14675 | PMOS gate bias (VBAT side) | Same |
| R_PMOS2 | 100kΩ 0603 | C14675 | PMOS gate bias (raw battery side) | Same |
| Q_PMOS | SOT-23 PMOS | C3040193 | Battery reverse polarity protection | Same |
| TH_NTC | 10kΩ NTC 0603 | C13564 | Battery temperature monitoring | Same |

### Bootstrap Cap Discrepancy

The reference design uses 100nF for C_BTST (C3 in circuit-context.json: "100nF"). The BQ24195 datasheet specifies **47nF**. The reference design value works (larger bootstrap cap is generally fine), but we should use the datasheet-recommended 47nF for the new design.

### PMID Capacitance

The reference design has only one 10µF on PMID (C4). The BQ24195 datasheet recommends **20µF minimum** (60µF for full load support). We should increase to 2× 10µF (20µF total) or add a 22µF ceramic.

## Power Monitor: INA219 — Passive Values

| Ref | Value | LCSC | Function |
|-----|-------|------|----------|
| R_SHUNT | 10mΩ 1% 2512 1W | C1322424 | Current sense resistor on VSYS rail |
| C_VS | 0.1µF ceramic 0603 | C14663 | VS power supply bypass |

**Shunt resistor selection:** FH MFJ12HR010FT (C1322424) — 10mΩ, 1W, ±1%, ±50ppm/°C, 2512 package. 6,477 in stock at $0.08.

- PGA setting: /2 (±80mV range)
- Max measurable current: 80mV / 10mΩ = 8A (33% headroom over 6A max)
- Power dissipation at 6A: 0.36W (within 1W rating)
- Voltage drop at 6A: 60mV (2% of 3.0V minimum VSYS)
- Current resolution: 1 mA/LSB
- Calibration register: 0x1000 (4096)
- I2C address: 0x40 (A0=GND, A1=GND — no conflicts with TCA9548A at 0x70 or BQ24195 at 0x6B)

## USB-C Input — Passive Values

Carried from reference design, minus STUSB4500 and USBLC6-2SC6.

| Ref | Value | LCSC | Function |
|-----|-------|------|----------|
| USBC1 | TYPE-C-31-M-12 | C165948 | USB-C connector |
| F_VBUS | 3A 1206 fuse | C2897466 | VBUS overcurrent protection |
| R_CC1 | 5.1kΩ 0603 | C23186 | CC1 pull-down (UFP sink) |
| R_CC2 | 5.1kΩ 0603 | C23186 | CC2 pull-down (UFP sink) |
| C_PVBUS_CERAMIC | 4.7µF ceramic 0603 | C19666 | Protected_VBUS decoupling |
| C_PVBUS_BULK | 47µF electrolytic 6.3×5.4 | C2836440 | Protected_VBUS bulk decoupling |

## Board Area Estimate

### New Components (not on current main PCB)

| Block | Components | Footprint Area | Notes |
|-------|-----------|---------------|-------|
| USB-C connector | 1 IC | ~9.0 × 7.3mm = 65mm² | TYPE-C-31-M-12 |
| BQ24195 + support | 1 IC + ~15 passives | ~4×4mm IC + ~25mm² passives = 41mm² | Includes inductor, caps, NTC, PMOS, resistors |
| BQ24195 inductor | L_BQ (FNR6028S) | 6.4 × 2.8mm = 18mm² | Separate from IC area |
| TPS61088 + support | 1 IC + ~12 passives | ~4.5×3.5mm IC + ~20mm² passives = 36mm² | Includes comp network |
| Boost inductor | L_BOOST (FXL0630) | 7.0 × 6.6mm = 46mm² | Largest single component |
| Boost output caps (×3) | 3× 22µF 0805 | 3 × 3.2mm² = 10mm² | |
| INA219 + shunt | 1 IC + 2 passives | SOT-23-8 + 2512 = 20mm² | |
| VSYS bulk cap | 220µF electrolytic | 6.3 × 7.7mm = 49mm² | Tallest component |
| Battery connector | JST PH 2-pin | ~7 × 5mm = 35mm² | |
| Test points (×4-6) | 1.5mm pads | ~12mm² | VSYS, VBAT, VBUS, GND |
| **Total new footprint area** | | **~332mm²** | |

### Clearance and Routing Overhead

Component-only area: ~332mm². With clearance, routing channels, and thermal copper pours, multiply by ~2.5×:

**Estimated power block area: ~830mm² ≈ 8.3cm²**

### Current Main PCB

Board size: 85mm × 45mm = 3,825mm² total. Usable area (after edge clearance): ~3,400mm². Current component density leaves approximately 30-40% open area for routing/expansion.

**Available area for power block: ~1,000-1,400mm²**

The estimated 830mm² power block fits within available area, but it will be tight — the power block consumes roughly 60-80% of the available expansion space. The DWEII module removal (~12×12mm = 144mm²) and Schottky D1 removal (~5mm²) free about 150mm² additional space.

**Verdict: The power block fits on the current 85mm × 45mm board**, but leaves minimal room for future expansion. If layout proves too cramped (especially for thermal copper pours under the boost converter and BQ24195), consider growing the board to **90mm × 50mm** (4,500mm²), which would provide comfortable margins. Flag this during Phase 3 layout.

## GPIO Allocation: BQ24195 INT

### Available GPIOs on T-Display-S3 (from main PCB circuit-context)

| GPIO | Current Assignment | Net Name | Test Point |
|------|-------------------|----------|------------|
| 1 | Unused breakout | Net-(U2-1) | TPIO1 |
| 2 | Unused breakout | Net-(U2-2) | TPIO2 |
| 3 | Unused breakout | Net-(U2-3) | TPIO3 |
| 17 | Unused breakout | Net-(U2-17) | TPIO17 |
| 18 | Unused breakout | Net-(U2-18) | TPIO18 |
| 21 | Unused breakout | Net-(U2-21) | TPIO21 |

### Selection Criteria

- BQ24195 INT is active-low, open-drain, 256µs pulse on status/fault events
- Needs internal pull-up or external pull-up to 3.3V
- Should support GPIO interrupt (falling edge) on ESP32-S3
- No conflict with existing signals
- Physical proximity on T-Display-S3 header to the power block area of the PCB

### Recommendation: **GPIO 21**

- Pin 19 on T-Display-S3 header (close to other I2C pins 43/44 at pins 15/16)
- No known ESP32-S3 special functions on GPIO 21 that would conflict
- All candidate GPIOs support edge interrupts, so any would work electrically
- GPIO 21 is at the end of the header, adjacent to GPIO 16 (LED data) — routing to the power block (near the USB-C end of the board) should be straightforward
- Preserves GPIO 1-3 as a contiguous group for future use (e.g., SPI, UART, or additional sensors)
- Preserves GPIO 17-18 as a pair for future use

**Allocated: GPIO 21 → BQ24195 INT (active-low, 10kΩ pull-up to 3.3V)**

## Battery-Absent Operation — Datasheet Validation

### BQ24195 Behavior Without Battery

The BQ24195 **explicitly supports battery-absent operation** ("Instant-on Works with No Battery or Deeply Discharged Battery"):

1. **VSYS regulation:** VSYS is regulated from VBUS at VSYS_MIN + 150mV. With default VSYS_MIN = 3.5V → **VSYS ≈ 3.65V** (range 3.55–3.65V).

2. **Load current capability:** Limited by the input current limit (min of ILIM hardware and I2C register). With our revised ILIM (330Ω → 1.5A) and OTG HIGH (500mA SDP boot), the system gets:
   - Boot: 500mA input → ~2.1W at +5V (after losses) → sufficient for ESP32 startup
   - Post-firmware: 1.5A input → ~6.3W at +5V → sufficient for full operation minus LEDs at high brightness

3. **Recommended firmware configuration:** Set REG07[5] = 1 (BATFET_Disable) when no battery is detected. This prevents the charger from trying to charge a non-existent battery.

4. **Startup sequence:** During initial startup (VSYS < 2.2V), input current is forced to 100mA regardless of ILIM/register settings. Once VSYS rises above 2.2V, the configured limit applies. This 100mA phase is brief (~ms) as VSYS capacitors charge.

5. **VSYS_STAT bit:** REG08[0] goes high when the system is in minimum system voltage regulation (battery-absent or deeply depleted) — firmware can detect this.

### Current Budget on USB-Only (Battery-Absent)

| Parameter | Value |
|-----------|-------|
| VBUS input | 5V |
| Input current limit (after firmware config) | 1.5A |
| Input power | 7.5W |
| BQ24195 efficiency (buck to VSYS) | ~92% |
| VSYS power | ~6.9W |
| Boost efficiency (VSYS → +5V) | ~90% |
| Available at +5V | ~6.2W = **1.24A at 5V** |

| Load | Current at 5V |
|------|--------------|
| ESP32-S3 + LCD (active WiFi) | ~200mA |
| 3.3V rail (sensors, muxes) | ~5mA |
| LEDs (moderate, 30% duty) | ~500mA |
| Level shifter | ~1mA |
| **Total** | **~706mA** |

**1.24A available > 706mA required → USB-only operation is viable** with moderate LED brightness. Full LED brightness (1.8A) would exceed the budget — firmware should limit LED duty when on USB-only power.

### Validation Result

**Battery-absent operation is confirmed viable.** The BQ24195 natively supports it, VSYS stays regulated, and our revised ILIM/OTG configuration provides sufficient input current for the system to boot and operate at moderate loads. Firmware must:
1. Detect battery-absent via REG08[0] (VSYS_STAT)
2. Set BATFET_Disable (REG07[5] = 1)
3. Limit LED brightness to stay within input current budget

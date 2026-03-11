# TPS61088 Datasheet Reference

> Texas Instruments TPS61088 — 10-A Fully-Integrated Synchronous Boost Converter
> Document: SLVSCM8D (May 2015, Rev. August 2021)

## Overview

The TPS61088 is a high-power-density synchronous boost converter with integrated 11-mΩ low-side and 13-mΩ high-side MOSFETs. It uses adaptive constant off-time peak current control.

- **Input voltage:** 2.7 V to 12 V
- **Output voltage:** 4.5 V to 12.6 V
- **Switch current:** 10 A
- **Efficiency:** Up to 91% (VIN = 3.3 V, VOUT = 9 V, IOUT = 3 A)
- **Switching frequency:** 200 kHz to 2.2 MHz (resistor-programmable)
- **Package:** 4.50 mm × 3.50 mm, 20-pin VQFN (RHL)
- **Light-load modes:** PFM (high efficiency) or forced PWM (no acoustic noise), selected via MODE pin
- **Quiescent current:** 1 µA typ from VIN (enabled, no load); 1 µA typ shutdown

## Absolute Maximum Ratings

| Parameter | Min | Max | Unit |
|-----------|-----|-----|------|
| VIN, SW, FSW, VOUT | −0.3 | 14.5 | V |
| EN, VCC, SS, COMP, MODE | −0.3 | 7 | V |
| ILIM, FB | −0.3 | 3.6 | V |
| BOOT | −0.3 | SW + 7 | V |
| Operating junction temp (TJ) | −40 | 150 | °C |
| Storage temperature | −65 | 150 | °C |

## Key Electrical Characteristics

Conditions: VIN = 2.7–5.5 V, TJ = −40 to 125°C. Typical at VIN = 3.6 V, TJ = 25°C.

**Power Supply:**
- VIN UVLO rising threshold: 2.7 V
- VIN UVLO falling threshold: 2.4–2.5 V (200 mV hysteresis)
- VCC UVLO falling threshold: 2.1 V
- VCC regulation: 5.8 V (at IVCC = 5 mA, VIN = 8 V)

**Reference & Output:**
- FB reference voltage (PWM): 1.186 / 1.204 / 1.222 V (min/typ/max)
- FB reference voltage (PFM): 1.212 V typ
- FB pin leakage: 100 nA

**Power Switches:**
- High-side RDS(on): 13 mΩ typ, 18 mΩ max (VCC = 6 V)
- Low-side RDS(on): 11 mΩ typ, 16.5 mΩ max (VCC = 6 V)

**Current Limit (RILIM = 100 kΩ):**
- PFM mode: 10.6 / 11.9 / 13.0 A (min/typ/max)
- FPWM mode: 9.0 / 10.3 / 11.4 A (min/typ/max)

**Switching Frequency:**
- 500 kHz typ at RFREQ = 301 kΩ (VIN = 3.6 V, VOUT = 12 V)
- Min on-time: 90–180 ns

**Protection:**
- OVP threshold: 12.7 / 13.2 / 13.6 V (with 0.25 V hysteresis)
- Thermal shutdown: 150°C rising, 20°C hysteresis

**EN Pin:**
- High threshold: 1.2 V
- Low threshold: 0.4 V
- Internal pull-down: 800 kΩ

## Pin Configuration (20-Pin VQFN + Thermal Pad)

| Pin | Name | I/O | Function |
|-----|------|-----|----------|
| 1 | VCC | O | Internal LDO output. Requires ≥1.0 µF ceramic cap to GND. |
| 2 | EN | I | Enable. High = on, Low = shutdown. Has 800 kΩ internal pull-down. |
| 3 | FSW | I | Switching frequency set by resistor between FSW and SW. |
| 4–7 | SW | — | Switching node (low-side drain, high-side source). |
| 8 | BOOT | O | High-side gate driver supply. Requires 0.1 µF cap between BOOT and SW. |
| 9 | VIN | I | Power supply input. |
| 10 | SS | O | Soft-start. External cap sets ramp rate (charged at 5 µA). |
| 11–12 | NC | — | No internal connection. Connect to ground plane for thermal dissipation. |
| 13 | MODE | I | Light-load mode: GND = forced PWM, floating = PFM. 800 kΩ internal pull-up. |
| 14–16 | VOUT | O | Boost converter output. |
| 17 | FB | I | Feedback input. Connect to resistor divider center tap. |
| 18 | COMP | O | Error amplifier output. Connect external compensation network here. |
| 19 | ILIM | O | Peak current limit set by resistor to AGND. |
| 20 | AGND | — | Signal ground. |
| 21 | PGND | — | Power ground (low-side MOSFET source). |
| Pad | Thermal | — | Exposed thermal pad. Must be soldered to ground plane. |

## Typical Application Circuit

Required external components (referencing Figure 8-1 in the datasheet, 3.3–4.2 V → 9 V/3 A design):

| Ref | Component | Value | Purpose |
|-----|-----------|-------|---------|
| L1 | Inductor | 1.2 µH | Power inductor (e.g. Sumida CDMC8D28NP-1R2MC) |
| C1 | Input cap (VIN) | 10 µF ceramic | Input decoupling, power stage |
| C2 | VIN bypass | 0.1 µF ceramic | Close to VIN pin |
| C3 | Boot cap | 0.1 µF ceramic | Between BOOT and SW |
| C4 | VCC cap | 2.2 µF ceramic | Internal LDO decoupling |
| C9 | Output caps | 3× 22 µF ceramic | Output filtering |
| C6 | Comp cap (C5 in network) | — | Loop compensation |
| C5, C8 | Comp network | — | Loop compensation (R5, C5, C8 form Type II) |
| R1 | FB upper resistor | 360 kΩ | Sets output voltage (with R2) |
| R2 | FB lower resistor | 56 kΩ | Sets output voltage (with R1) |
| R3 | Freq resistor | 255 kΩ | FSW to SW, sets switching frequency |
| R4 | Current limit resistor | 100 kΩ | ILIM to AGND, sets 11.9 A peak limit |
| R5 | Comp resistor | — | Loop compensation |
| C7 | Soft-start cap | 47 nF | SS pin to GND |

## Feedback Divider — Setting Output Voltage

The output voltage is programmed by an external resistor divider from VOUT to FB to GND.

**Formula:**

```
R1 = (VOUT − VREF) × R2 / VREF
```

Where:
- **VREF** = 1.204 V (typical FB reference voltage in PWM mode)
- **R2** = lower resistor (FB to GND), recommended starting point: **56 kΩ** (ensures ≥20 µA divider current for noise immunity)
- **R1** = upper resistor (VOUT to FB)

**For 5 V output:**

```
R1 = (5.0 − 1.204) × 56 kΩ / 1.204
     = 3.796 × 56k / 1.204
     = 176.6 kΩ
```

Use standard values: **R2 = 56 kΩ, R1 = 180 kΩ** (gives VOUT ≈ 5.07 V) or **R1 = 174 kΩ** (gives VOUT ≈ 4.94 V). A 1% 178 kΩ resistor gives VOUT ≈ 5.03 V if available; otherwise 180 kΩ is the practical choice.

Alternatively, with R2 = 100 kΩ: R1 = 315.4 kΩ → use 316 kΩ (1%) for VOUT ≈ 5.00 V. This trades slightly higher divider current for better accuracy with standard values.

## Inductor Selection

**Recommended value:** 0.47 µH to 10 µH. The datasheet defaults to **2.2 µH** for general use, but the typical application example uses **1.2 µH** for the high-power 9 V design.

**Key selection criteria:**
- Saturation current must exceed the programmed peak current limit
- Inductors can lose 20–35% of rated inductance near saturation — account for this
- Tolerance can be ±20% to ±30% — use worst-case (−30%) inductance for peak current calculations
- Lower DCR and ESR improve efficiency
- Shielded inductors recommended for EMI but typically have higher DCR

**For a 5 V/3 A design from 3.0 V input (worst case):**
- DC current ≈ VOUT × IOUT / (VIN × η) = 5 × 3 / (3.0 × 0.85) ≈ 5.9 A
- A 2.2 µH inductor reduces ripple vs 1.2 µH, easier thermal management
- Saturation current rating: ≥12 A recommended

**Recommended inductors from datasheet (2.2 µH):**
- Cyntec PIMB104T-2R2MS: 7 mΩ DCR, 18/12 A sat/heat, 11.2 × 10.3 × 4.0 mm
- Cyntec PIMB103T-2R2MS: 9 mΩ DCR, 16/13 A sat/heat, 11.2 × 10.3 × 3.0 mm
- Cyntec PIMB065T-2R2MS: 12.5 mΩ DCR, 12/10.5 A sat/heat, 7.4 × 6.8 × 5.0 mm

## Input/Output Capacitors

**Input capacitors:**
- 0.1 µF ceramic bypass close to VIN pin (mandatory)
- ≥10 µF ceramic for power stage input filtering (keep input ripple < 100 mV)
- Use low-ESR ceramics; account for DC bias derating (a 10 µF/10 V 0805 cap may drop below 5 µF at 5 V bias)
- If supply is far from converter, add 47 µF electrolytic/tantalum bulk cap

**Output capacitors:**
- 3× 22 µF ceramic typical (66 µF nominal, effective capacitance after derating matters)
- Recommended range: 6.8 µF to 1000 µF effective
- Higher values improve load transient response
- Must account for voltage derating — use caps rated well above VOUT

**VCC pin:** ≥1.0 µF ceramic (2.2 µF used in typical application)
**BOOT pin:** 0.1 µF ceramic between BOOT and SW

## Thermal Information

| Metric | Standard PCB | EVM | Unit |
|--------|-------------|-----|------|
| RθJA (junction-to-ambient) | 38.8 | 29.7 | °C/W |
| RθJC(top) | 39.8 | — | °C/W |
| RθJB (junction-to-board) | 15.5 | — | °C/W |
| RθJC(bottom) | 3.1 | — | °C/W |

**Max junction temperature:** 125°C under normal operation (150°C absolute max).

**Max power dissipation:**

```
PD(max) = (125°C − TA) / RθJA
```

At 40°C ambient with standard PCB: PD(max) = 85 / 38.8 = **2.19 W**
At 40°C ambient with good layout (EVM): PD(max) = 85 / 29.7 = **2.86 W**

The exposed thermal pad must be soldered to a large ground plane with thermal vias for adequate heat spreading.

## Soft-Start and Enable

**EN pin behavior:**
- Logic high (>1.2 V) enables the device
- Logic low (<0.4 V) puts device into shutdown (1 µA VIN current)
- Internal 800 kΩ pull-down ensures device stays off if EN is floating

**Soft-start:**
- Controlled by external capacitor on SS pin
- SS pin charged with 5 µA constant current source
- Voltage ramps up; the lower of SS voltage or internal 1.204 V reference is used as the error amplifier input
- Soft-start complete when SS voltage exceeds 1.204 V
- SS cap discharged to GND when EN goes low

**Soft-start time formula:**

```
tSS = VREF × CSS / ISS = 1.204 × CSS / 5µA
```

With 47 nF (typical): tSS ≈ 11.3 ms

## Protection Features

**Output Overvoltage Protection (OVP):**
- Threshold: 13.2 V typical (12.7–13.6 V range) at VOUT pin
- Converter stops switching when VOUT exceeds OVP threshold
- Resumes when VOUT drops 0.25 V below threshold
- This is a fixed threshold — not relative to the programmed output voltage

**Overcurrent Protection (OCP):**
- Cycle-by-cycle peak current limiting
- Low-side switch turned off immediately when inductor current hits the limit
- Limit is programmable via RILIM resistor (ILIM pin to AGND)
- With RILIM = 100 kΩ: 11.9 A (PFM) or 10.3 A (FPWM) typical
- Formula (PFM mode): RILIM = 1,190,000 / ILIM
- Worst-case current limit can be 1.3 A below calculated value

**Undervoltage Lockout (UVLO):**
- VIN UVLO: stops switching when VIN falls below 2.4–2.5 V; restarts at VIN rising above ~2.7 V (200 mV hysteresis)
- VCC UVLO: stops when VCC falls below 2.1 V

**Thermal Shutdown:**
- Triggers at TJ = 150°C
- Resumes when TJ falls below ~130°C (20°C hysteresis)

## PCB Layout Recommendations

1. **Minimize SW trace length and area** — fast switching edges radiate EMI. Keep traces to SW pins as short as possible.
2. **Ground plane under the converter** — required to minimize interplane coupling and provide return current path.
3. **Input capacitor close to VIN and GND pins** — reduces input ripple.
4. **Thermal pad soldered to large ground plane** — critical for heat dissipation. Use thermal vias underneath the pad.
5. **NC pins (11, 12) connected to ground plane** — improves thermal dissipation.
6. **Bottom layer large ground plane** — connected to PGND and AGND planes on top layer via vias.
7. **Thick PCB copper** — improves thermal performance.
8. **Use vias around IC** — connects top and bottom ground planes without solder mask for better thermal capability.
9. **Non-solder-mask-defined (NSMD) pads preferred** for the land pattern.

## Application Notes for 5 V/3 A from 3.0–4.5 V Input

This section summarizes design considerations specific to Motion Play's boost converter application.

**Feasibility:** Well within the TPS61088's capabilities. The device supports 2.7–12 V input and 4.5–12.6 V output. A 3.0–4.5 V → 5 V boost is a modest step-up ratio.

**Efficiency expectation:** At VIN = 3.6 V and VOUT = 5 V, efficiency should be high (the datasheet shows ~90%+ for 5 V output at moderate loads). Low step-up ratio is favorable for efficiency.

**Power budget:** POUT = 5 V × 3 A = 15 W. At ~90% efficiency, PIN ≈ 16.7 W. At VIN = 3.0 V, IIN ≈ 5.6 A — well within the 10 A switch current capability.

**Switching frequency:** For a 5 V output, higher switching frequency (e.g., 1 MHz) is feasible because the low VOUT/VIN ratio means lower RHPZ frequency is less of a constraint. Higher frequency allows smaller inductor and output caps.

**MODE pin:** For a battery-powered application, PFM mode (MODE floating) is recommended for good light-load efficiency. Use FPWM (MODE to GND) only if acoustic noise or fixed-frequency operation is required.

# ESP32 Integration — PCB Placement Guide

Component placement guide for the 20 new ESP32 integration components. Organized as a staged placement process — each stage is a logical group. Higher stages depend on lower ones being positioned first.

## Current Board Layout Reference

Board outline: 88mm × 40mm (x: 76–164, y: 101–141, Y-down)

Key anchors already positioned:
- **J7** (USB-C): (80.8, 119.6) rot -90° — left edge, data pads at x≈83.3
- **U5** (BQ24195): (96.9, 117.6) — power section
- **U4** (TCA9548A): (151.9, 114.0) — right half
- **J4/J5/J6** (sensor connectors): x≈161.3 — right edge
- **IC1** (level shifter): (148.8, 135.5)

## U3 Pin Map (at rotation 0°)

Understanding which pins are on which side is critical for support component placement.

```
                    ┌─────── ANTENNA (top, ~y=105) ───────┐
                    │         no pads, keepout zone        │
    LEFT (x≈120.8)  │                                      │  RIGHT (x≈138.3)
    ────────────────│──────────────────────────────────────│────────────────
    Pin 1   GND     │                                      │  Pin 40  GND
    Pin 2   +3.3V ★ │          GND pad (pin 41)            │  Pin 39  IO1
    Pin 3   EN ★    │          3×3 via array               │  Pin 38  IO2
    Pin 4   IO4     │          center of module             │  Pin 37  I2C_SDA ★
    Pin 5   IO5     │                                      │  Pin 36  I2C_SCL ★
    Pin 6   IO6     │                                      │  Pin 35  IO42
    Pin 7   IO7     │                                      │  Pin 34  IO41
    Pin 8   IO15    │                                      │  Pin 33  IO40
    Pin 9   LED_DATA★│                                      │  Pin 32  IO39
    Pin 10  IO17    │                                      │  Pin 31  IO38
    Pin 11  IO18    │                                      │  Pin 30  IO37
    Pin 12  IO8     │                                      │  Pin 29  IO36
    Pin 13  USB_DN ★│                                      │  Pin 28  IO35
    Pin 14  USB_DP ★│                                      │  Pin 27  GPIO0_BOOT ★
    ────────────────│──────────────────────────────────────│────────────────
                    │               BOTTOM (y≈127.4)       │
                    │  15  16  17  18  19  20  21  22  23  24  25  26
                    │  IO3 IO46 IO9 TCA INT3 INT2 INT1 IO14 CHRG IO47 IO48 IO45
                    │              RST★  (NC) (NC) (NC)     INT★
                    └──────────────────────────────────────┘
```

★ = active signal requiring a trace or support component nearby.

**Key takeaway:** Power/USB/LED signals exit the **left side**. I2C/boot exit the **right side**. TCA_RESET and CHRG_INT exit the **bottom**.

---

## Stage 1: U3 — WROOM-1 Module

**Priority: Highest — everything else positions relative to U3.**

### Constraints
1. **Antenna at board edge.** The antenna is the top of the module (at rot 0°). Position U3 so the antenna end is flush with or protruding past a board edge. The top edge (y=101) works well with the current rotation.
2. **Antenna keepout zone.** No copper pour, no traces, no ground plane, and no components in the antenna region. This covers the top ~5–8mm of the module body (roughly y < 110 at current position) plus 10–15mm past the antenna tip. If the antenna is at the board edge, the keepout extends into air — ideal.
3. **Ground plane under module body.** Solid unbroken ground plane under everything *except* the antenna section. Critical for RF performance.
4. **GND pad (pin 41) vias.** The center ground pad needs multiple vias (at least 9, matching the 3×3 sub-pad grid) connecting to the ground plane on the back layer. This is the primary thermal and electrical ground return.
5. **No high-frequency digital traces** routed under or near the antenna section.

### Position Recommendation

At the current position (129.6, 118.5) rot 0°, the antenna top is at approximately y≈105.2 — about 4mm inside the top edge. **Moving U3 up ~4mm** (to roughly y≈114.5) would put the antenna flush with the top edge, pushing the entire keepout zone off-board. This is the cleanest approach.

Alternatively, keep the current position and define an on-board keepout rectangle from x=120 to x=139, y=101 to y=110 (no fill, no traces).

### Orientation Check

At rot 0°:
- Left side → faces power section / J7 → good (USB, power, LED signals)
- Right side → faces U4 / sensor connectors → good (I2C, boot)
- Bottom → faces power switch area → acceptable (TCA_RESET, CHRG_INT)
- Top → antenna toward board edge → correct

This orientation routes signals toward their destinations with minimal crossing. No rotation change needed.

---

## Stage 2: U8 — AMS1117-3.3 + Caps

**Priority: High — thermal and power integrity.**

### Components
| Ref | Value | Net connections | Placement rule |
|-----|-------|----------------|----------------|
| U8 | AMS1117-3.3 | VIN=+5V, VOUT=+3.3V, GND | Needs thermal copper pour on tab |
| C42 | 22µF ceramic (0805) | +5V → GND | Within 3mm of U8 pin 3 (VIN) |
| C43 | 22µF tantalum (Case-A) | +3.3V → GND | Within 3mm of U8 pin 2/4 (VOUT) |

### U8 Pad Map (at rot 0°)
```
    Pin 4 (VOUT/tab)          Pin 3 (VIN, +5V)     ← x≈116.7, y≈103.0
    large heatsink pad        Pin 2 (VOUT, +3.3V)   ← y≈105.3
    at x≈110.8                Pin 1 (GND)            ← y≈107.6
```

### Constraints
1. **Heatsink tab (pin 4):** Connect to +3.3V copper pour — this is the primary heat dissipation path. The bigger the pour, the better. The AMS1117 dissipates ~(5V−3.3V) × I_load as heat. At 500mA that's 850mW.
2. **C42 (input cap):** Place between pin 3 (+5V) and pin 1 (GND). As close as possible — this cap provides the instantaneous current during load transients.
3. **C43 (output cap, tantalum):** Place between pin 2/4 (+3.3V) and pin 1 (GND). This cap is **critical for AMS1117 stability** — the AMS1117 requires output capacitance with ESR in a specific range. Tantalum provides this. Keep the loop area small.
4. **Thermal vias** under the tab pad connecting to inner/back copper ground or power pour.

### Position Note
Current position (113.8, 105.3) places U8 between the power section and U3. The +5V rail (from TPS61088 output) and +3.3V rail (to U3 and the rest of the board) both route through this area — good location.

---

## Stage 3: U9 — USBLC6-2SC6 (USB ESD)

**Priority: High — must be the first thing USB data hits after J7.**

### Constraints
1. **As close to J7 as possible.** ESD protection effectiveness degrades with distance from the connector. Target: within 5mm of J7's D+/D- pads.
2. **Signal path order:** J7 → U9 → R52/R53 → U3. Never put the series resistors between J7 and U9.
3. J7's D+/D- pads are at (83.3, 119–120). U9 should go at approximately (86–90, 119–120) — just to the right of J7.

### U9 Pad Map (SOT-23-6)
```
Pin 1 (USB_DP)   Pin 6 (USB_DP)
Pin 2 (GND)      Pin 5 (GND)  
Pin 3 (USB_DN)   Pin 4 (USB_DN)
```
Symmetric — D+ goes in one side, out the other. Same for D−. Place it inline with the USB data path from J7.

---

## Stage 4: R52 + R53 — USB Series Resistors

**Priority: High — USB signal integrity.**

| Ref | Value | Net (pin 1 → pin 2) |
|-----|-------|---------------------|
| R52 | 22Ω | /USB_DN → /ESP32_S3/USB_DN_MCU |
| R53 | 22Ω | /USB_DP → /ESP32_S3/USB_DP_MCU |

### Constraints
1. **Between U9 and U3** in the signal path. Closer to U3 is preferred per Espressif guidelines.
2. **Maintain differential pair spacing.** Keep R52 and R53 at the same distance from U3's USB pins (13, 14 on the left side at x≈120.8, y≈124–126).
3. These are small 0603 parts — easy to tuck near U3's left side.

---

## Stage 5: ESP32 Decoupling + Pull-ups

**Priority: Medium — close to U3 but exact position is flexible.**

### Left Side Group (near pins 2, 3)
| Ref | Value | Purpose | Target pin |
|-----|-------|---------|------------|
| C51 | 10µF | Bulk bypass | Pin 2 (+3.3V), x≈120.8, y≈110.8 |
| C52 | 100nF | CPU bypass | Pin 2 |
| C53 | 100nF | RTC bypass | Pin 2 |
| C54 | 100nF | SPI bypass | Pin 2 |
| C55 | 1µF | VDD_SPI bypass | Pin 2 |
| R50 | 10kΩ | EN pull-up | Pin 3 (EN), x≈120.8, y≈112.1 |
| C50 | 1µF | EN reset cap | Pin 3 (EN) |

**Placement:** Cluster these to the left of U3, just outside the pin row. All connect to +3.3V and GND, so they share power rails. Place C51 (largest value) closest to pin 2, then the 100nF caps in a row. R50 and C50 should be near pin 3 (EN).

### Right Side (near pin 27)
| Ref | Value | Purpose | Target pin |
|-----|-------|---------|------------|
| R51 | 10kΩ | BOOT pull-up | Pin 27 (GPIO0), x≈138.3, y≈126.1 |

**Placement:** To the right of U3, near pin 27. Connects between +3.3V and GPIO0.

### Constraint
All bypass caps: keep within 5mm of the 3V3 pin (pin 2). Shorter traces = lower inductance = better high-frequency decoupling.

---

## Stage 6: SW2 + SW3 — Reset and Boot Buttons

**Priority: Medium — functional requirement, position is flexible.**

| Ref | Function | Connects to | U3 pin side |
|-----|----------|-------------|-------------|
| SW2 | RESET | EN → GND | Left (pin 3) |
| SW3 | BOOT | GPIO0 → GND | Right (pin 27) |

### Constraints
1. **Accessible from board edge or enclosure.** These are user-facing buttons (first flash requires manual boot+reset sequence).
2. **Short traces to U3** — especially SW2 to EN, since long EN traces can pick up noise and cause resets.
3. SW2 naturally goes near the left/bottom of U3 (near pin 3). SW3 near the right/bottom (near pin 27).
4. Consider placing both along the same board edge for ergonomics.

---

## Stage 7: D5 — WS2812B Status LED

**Priority: Low — placement is flexible.**

| Net | Pin |
|-----|-----|
| LED_DATA (DIN) | Pin 1 |
| +5V (VDD) | Pin 2 |
| GND | Pin 4 |
| DOUT — NC | Pin 3 |

### Constraints
1. **Visible from outside the enclosure.** Top edge or near an enclosure opening.
2. Powered from +5V, data from LED_DATA (U3 pin 9, left side at x≈120.8, y≈119.7).
3. Keep the data line reasonably short (WS2812B protocol is timing-sensitive).
4. No strict electrical proximity requirement — it's a single addressable LED.

---

## Stage 8: SW1 — Power Slide Switch

**Priority: Low — already roughly positioned.**

Current position: (122.8, 133.4) near the bottom edge. Through-hole, 13.2mm wide.

### Constraints
1. **Board edge, accessible from enclosure.** Slider must protrude past the enclosure wall.
2. In the VSYS power path — connects VSYS to VSYS_SW. Trace width should handle system current (1A+). Use wide traces or copper pour.
3. No strict electrical proximity to other components — it's just a switch in a DC power path.

---

## Stage 9: TPIO21 — Test Point

**Priority: Lowest.** Place wherever convenient and accessible for probing. Connects to /CHRG_INT.

---

## USB D+/D- Routing Notes

After placement, the USB data path needs controlled-impedance routing:

1. **Differential impedance target: 90Ω.** Check your stackup — for standard JLCPCB 4-layer 1.6mm, typical differential pair geometry is ~0.2mm trace width with ~0.15mm gap on an outer layer over a ground plane.
2. **Route as a differential pair** from J7 → U9 → R52/R53 → U3 pins 13/14.
3. **Match trace lengths** within the pair — keep the length difference under 0.5mm.
4. **Avoid vias** in the USB data path if possible. If a via is unavoidable, use matched vias (both lines via together).
5. **Keep away from high-speed switching signals** (boost converter area, clock lines).
6. The series resistors (R52/R53) break the differential pair — route as a pair on both sides of the resistors.

## Antenna Keepout Zone

After U3 is in its final position, create a keepout zone in KiCad:

1. **Place → Keepout Area** (or draw a Rule Area on the copper layers).
2. Cover the antenna section of the module: the top ~8mm of the footprint body.
3. Extend the keepout 10–15mm past the antenna tip (if this is on-board; if antenna is at the board edge, it extends into air and no on-board keepout is needed past the edge).
4. The keepout should prohibit: copper fill, tracks, and vias.
5. Ground plane is fine *under the module body* but must stop before the antenna section begins.

---

*Generated from pcb-layout-context.json extracted on the current board state.*

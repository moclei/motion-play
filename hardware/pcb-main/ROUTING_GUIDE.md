# PCB Routing Guide — Power Section + Full Board

Ephemeral reference doc. Delete after use.

> **L2 bbox fix (re-placement run):** L2's bounding box was corrected from 8.4×3.2mm
> (pad-only) to 8.4×6.6mm (body size from footprint name). This pushed C32, R41,
> R42, R43, and TP4 out of L2's footprint. R41/R42/R43 are now 9-11mm from U6
> (were ~2-3mm). C32 moved above L2 to ~(72.6, 131.9). See `placement-report.json`
> for all current positions.

---

## Step 0: Before You Start Routing

1. **Fill all zones** (`B`). This shows GND planes on In1.Cu/B.Cu and +5V/3.3V zones on In2.Cu.
2. **Turn on ratsnest** — the thin lines are your to-do list.
3. **Lock anchor components.** Right-click U5, U6, J7, J8, L1, L2, R44 → Properties → "Locked". Prevents accidental nudging.

---

## Step 1: Thermal Via Arrays Under U5 and U6

### U5 (BQ24195) — exposed pad 25 at (82.75, 122.25), 2.8×2.8mm, GND

Place a 3×2 grid of vias (0.6mm dia / 0.3mm drill) centered on the pad:
- x = {81.85, 82.75, 83.65}
- y = {121.65, 122.85}

These connect the exposed pad to the In1.Cu GND plane for heat dissipation.

### U6 (TPS61088) — exposed pad at (69.77, 135.95), GND

The footprint has 8 built-in thermal vias (0.4mm circles, no net assigned). Options:
- If they already connect to GND on inner layers → you're set
- If not → add a small GND copper pour on F.Cu over the exposed pad area, which will connect through the existing vias
- Or place your own 0.6mm/0.3mm vias on GND net in the same area

**Verify:** refill zones (`B`), check ratsnest confirms U5 pad 25 and U6 pad 21 are connected to GND.

---

## Step 2: TPS61088 Boost Switching Loop (HIGHEST PRIORITY)

The most EMI-sensitive loop. Switching current at 2.2MHz flows:

```
VSYS_SENSE → L2 pad 2 → L2 pad 1 → BOOST_SW → U6 pins 4-7 → GND (plane return)
```

### 2a. BOOST_SW: U6 pins 4-7 → L2 pad 1

| From | To | Distance |
|------|----|----------|
| U6 pins 4-7 at x=71.5, y=135.2–136.7 | L2 pad 1 at (73.474, 136.456) | ~2mm |

**Use a copper pour, not a trace.** Draw a small filled zone on F.Cu assigned to BOOST_SW that covers U6 SW pins and extends to L2 pad 1. Keep it compact — only the area between U6 right side and L2 left pad. ~2-3mm wide.

### 2b. BOOST_BOOT: U6 pin 8 → C32

| From | To | Width |
|------|----|-------|
| U6 pin 8 at (71.5, 134.7) | C32 pad 1 (BOOST_BOOT) at ~(72.6, 131.9) | 0.25mm (Default) |

Low-current bootstrap charge. ~3mm trace from U6 pin 8 to C32 (moved above L2 due to bbox fix).

Then connect **C32 pad 2 (BOOST_SW)** to the BOOST_SW pour — extend the pour or run a short 1.0mm trace.

### 2c. VSYS_SENSE: L2 pad 2 → U6 pins 2/9

| From | To | Width |
|------|----|-------|
| L2 pad 2 at (79.474, 136.456) | U6 pin 2 at (71.5, 137.7) and pin 9 at (71.5, 134.2) | 1.0mm (Power_Med) |

Carries full boost input current (~3A). Route from L2 pad 2 leftward to U6 pin 2, then down to pin 9 along U6's right edge.

**Input caps C31 and C41** must tap off this trace close to U6 — not at the far end of a long stub.

### 2d. GND return

No explicit trace — In1.Cu GND plane handles this. **Verify** the plane is unbroken under U6 and L2 (no signal traces cutting through on In1.Cu).

---

## Step 3: BQ24195 Switching Loop (SECOND PRIORITY)

Switching path:

```
Protected_VBUS → U5 pins 1/24 → BQ_SW pins 19-20 → L1 pad 1 → (L1) → VSYS
                                       ↑
                         C23 bridges BTST (pin 21) to SW
```

### 3a. BQ_SW: U5 pins 19-20 → L1 pad 1

| From | To | Width |
|------|----|-------|
| U5 pins 19-20 at (83.5, 120.2) and (84.0, 120.2) | L1 pad 1 (BQ_SW) at (83.1, 116.6) | 1.0mm (Power_Med) |

~3.6mm vertical. Route straight up from pins 19-20 to L1 pad 1. Keep as short and direct as possible.

### 3b. BQ_BTST: U5 pin 21 → C23 → BQ_SW

| From | To | Width |
|------|----|-------|
| U5 pin 21 (BTST) at (83.0, 120.2) | C23 pad 1 (BTST) at ~(86.4, 118.7) | 0.25mm (Default) |
| C23 pad 2 (BQ_SW) at ~(84.8, 118.7) | BQ_SW trace above | 0.25mm (Default) |

Bootstrap charging current — not high power. Connect C23 pad 2 to the BQ_SW trace between U5 and L1.

### 3c. VSYS: L1 pad 2 → R44 pad 1

| From | To | Width |
|------|----|-------|
| L1 pad 2 (VSYS) at (83.1, 112.1) | R44 pad 1 (VSYS) at (78.775, 130.9) | 1.0mm (Power_Med) |

Main VSYS power path, ~3A, ~19mm route. Go from L1 pad 2 downward, around the left side of U5, then down to R44. Stay in the power section (x < 90).

**C27/C28/C29 (VSYS bulk caps)** should tap off this trace near U5 VSYS pins (15-16, at x=84.79) — not at the far end.

---

## Step 4: INA219 Kelvin Sense Traces

**Precision measurement — routing accuracy matters here.**

R44 at (81.737, 130.9):
- Pad 1 (VSYS) at (78.775, 130.9)
- Pad 2 (VSYS_SENSE) at (84.7, 130.9)

U7 (INA219) at (88.2, 130.9):
- Pin 1 (VIN+ = VSYS) at (86.97, 129.92)
- Pin 2 (VIN- = VSYS_SENSE) at (86.97, 130.57)

### Rules:
1. Run a **thin 0.25mm dedicated trace** from R44 pad 1 → U7 pin 1
2. Run a **thin 0.25mm dedicated trace** from R44 pad 2 → U7 pin 2
3. These traces **must NOT merge with or tap off the fat power traces**
4. They connect **directly and only** to R44 pads and U7 pins
5. The fat 1.0mm VSYS and VSYS_SENSE power traces also connect to R44 pads — but separately, carrying load current to the rest of the power path

---

## Step 5: Protected_VBUS Path (USB-C → BQ24195)

```
J7 (USB-C) → VBUS_RAW → F2 → Protected_VBUS → C20/C21/C22 → U5 pins 1/24
```

### 5a. VBUS_RAW: J7 → F2 pad 1

| Width | Notes |
|-------|-------|
| 1.0mm (Power_Med) | Short run from USB-C connector to fuse |

### 5b. Protected_VBUS: F2 pad 2 → U5 pins 1/24

| From | To | Width |
|------|----|-------|
| F2 pad 2 at (83.807, 110.859) | U5 pin 1 at (80.71, 121.0) and pin 24 at (81.5, 120.2) | 1.0mm (Power_Med) |

Route southward from F2 to U5. Connect C20 and C21 (input decoupling, near U5 at ~x=78) with short stubs off this trace. C22 (47µF at ~x=91-93) gets a longer stub — fine for bulk cap.

### 5c. CC1/CC2: J7 → R30/R31

0.25mm (Default). USB-C sink pull-downs to GND. Short, non-critical.

---

## Step 6: Battery Path

```
J8 pin 1 (BAT_RAW) → Q2 drain (pin 1) → Q2 source (pin 3, VBAT) → U5 pins 13-14
```

| Segment | Width |
|---------|-------|
| BAT_RAW (J8 → Q2) | 0.75mm (Power_Low) |
| VBAT (Q2 → U5 pins 13-14) | 0.75mm (Power_Low) |

Key positions:
- J8 pad 1 (BAT_RAW) at (70.0, 118.0)
- Q2 at (74.7, 114.3): pin 1 = BAT_RAW, pin 3 = VBAT
- U5 pins 13-14 (VBAT) at (84.79, 123.0/123.5)

R33 (VBAT → PMOS_GATE) and R34 (PMOS_GATE → BAT_RAW): 0.25mm signal traces, close to Q2.

C30 (47µF BAT_RAW bulk cap at ~68.7, 109.6): connects to BAT_RAW trace near J8.

---

## Step 7: +5V Output Distribution

U6 outputs +5V on pins 14-16 (left side, x=68.04, y=135.2–136.2).

### Output caps (C34/C35/C36)

Clustered at ~x=65. Connect with 1.5mm traces or a small +5V copper pour on F.Cu covering U6 output pins and the three caps.

**Each cap's GND pad needs a 0.6mm/0.3mm via to In1.Cu GND plane within 0.5mm of the pad.**

### +5V to the rest of the board

From the output cap cluster, reach:
- U1 (AP2112K) pins 1/3 (+5V) at ~(105, 124-126)
- F1 (LED fuse) pad 1 (+5V) at (105.55, 118.25)

**Use the In2.Cu +5V zone for long runs.** Drop a via from F.Cu to In2.Cu near U6's output, and a via from In2.Cu back to F.Cu near U1/F1. Avoids routing fat traces across the top layer.

---

## Step 8: VSYS_SENSE → U6 Input

| From | To | Width |
|------|----|-------|
| R44 pad 2 (VSYS_SENSE) at (84.7, 130.9) | L2 pad 2 at (79.474, 136.456) and U6 pins 2/9 | 1.0mm (Power_Med) |

Full boost input current (~3A). Route from R44 pad 2 leftward and downward toward L2/U6. C31 and C41 (input caps) should connect to this trace close to U6.

---

## Step 9: U5 Support Passives

All 0.25mm (Default) traces unless noted. Short connections from U5 pins to nearby 0603 components.

| Net | U5 Pin(s) | Pin Location | Connect To |
|-----|-----------|--------------|------------|
| BQ_REGN | 22 | (82.5, 120.2) | C24 |
| BQ_PMID | 23 | (82.0, 120.2) | C25, C26 |
| BQ_ILIM | 10 | (83.0, 124.3) | R32 |
| BQ_TS | 11-12 | (83.5–84.0, 124.3) | R36, R37, TH1 |
| CHRG_INT | 7 | (81.5, 124.3) | R38 (pull-up), also routes to sheet connector |
| OTG_BIAS | 8 | (82.0, 124.3) | R35 (pull-up to 3.3V) |
| I2C_SCL | 5 | (80.71, 123.0) | I2C bus — keep away from SW traces |
| I2C_SDA | 6 | (80.71, 123.5) | I2C bus — keep away from SW traces |

**Every cap's GND pad: drop a 0.6mm/0.3mm via to In1.Cu GND plane within 0.5mm of the pad.**

---

## Step 10: U6 Support Passives

| Net | U6 Pin | Pin Location | Connect To | Width |
|-----|--------|--------------|------------|-------|
| BOOST_VCC | 1 | (70.52, 138.13) | C33 | 0.25mm |
| BOOST_SS | 10 | (70.52, 133.77) | C37 | 0.25mm |
| BOOST_FSW | 3 | (71.5, 137.2) | R41 | 0.25mm |
| BOOST_ILIM | 19 | (68.04, 137.7) | R42 | 0.25mm |
| **BOOST_FB** | **17** | **(68.04, 136.7)** | **R39 → R40 divider** | **0.2mm (Sensitive)** |
| **BOOST_COMP** | **18** | **(68.04, 137.2)** | **R43 → C38/C39** | **0.2mm (Sensitive)** |

### CRITICAL: FB and COMP routing

- Route on U6's **LEFT** side (toward board edge)
- SW and L2 are on U6's **RIGHT** side
- **Never cross FB/COMP traces with SW traces or route them near the inductor**
- Keep FB and COMP traces short and direct

---

## Step 11: Right-Side Connections (Existing Board)

The sensor connectors (J3-J6), TCA9548A, level shifter, and T-Display-S3 had some traces deleted during board resize. Re-route:

| Connection | Width | Notes |
|------------|-------|-------|
| TCA I2C channels (CH0-CH2 SCL/SDA) → sensor connectors | 0.25mm | Signal traces |
| Main I2C bus (SCL/SDA): T-Display → TCA → U5 → U7 | 0.25mm | Keep away from power section SW nodes |
| LED data: DATA_IN → IC1 → DATA_TO_LEDS → J3 | 0.25mm | Signal |
| LED power: +5V → F1 → R27 → +5V_TO_LEDS | 1.0mm | Use Power_Med or +5V zone on In2.Cu for input side |
| INT lines (INT1-INT3) | 0.25mm | Signal |

---

## Step 12: Copper Pours and Zone Fills

After all traces are routed:

### 12a. Fill all zones (`B`) and verify:

- [ ] In1.Cu GND plane is continuous under U5, U6, L1, L2 (no trace cuts)
- [ ] In2.Cu +5V zone covers U6 output area through to U1/F1 area
- [ ] In2.Cu 3.3V zone covers right-side logic area
- [ ] B.Cu GND fill is solid

### 12b. Local GND pours on F.Cu

If there's unused space around U5 and U6, draw small copper zones on F.Cu assigned to GND extending ~5mm beyond each IC footprint. These improve thermal performance by connecting to GND plane through thermal vias.

### 12c. GND stitching vias

Place 0.6mm/0.3mm vias on GND every ~5-10mm:
- Around the board perimeter
- In any open areas between component clusters
- These tie top and bottom GND pours together and reduce EMI

---

## Step 13: Final DRC and Check

1. Run DRC (Inspect → Design Rules Check)
2. Target: zero clearance violations, zero unconnected items
3. **Expected remaining violations** (not routing issues):
   - J7 footprint-level: annular width, padstack, hole clearance (easyeda2kicad import)
   - Silkscreen overlaps (cosmetic)
4. Check 3D viewer (View → 3D Viewer) for physical sanity

---

## General Tips

- **`W` while routing** — cycle through pre-defined track widths
- **`V` while routing** — drop a via and switch layers
- **Route from the IC outward** to passives, not the other way around. Control the critical end of the trace.
- **Don't route signal traces under L1 or L2** on any layer. Inductor magnetic field couples into traces underneath.
- **When you hit a dead end** — note it, finish other traces, then revisit placement. This is normal.
- **Check ratsnest often** — hidden unconnected nets are easy to miss on a busy board.
- **Save frequently.** KiCad doesn't auto-save during routing.

---

## Quick Net Reference

| Net Class | Width | Clearance | Nets |
|-----------|-------|-----------|------|
| **Power_5V** | 1.5mm | 0.3mm | `+5V`, `BOOST_SW` |
| **Power_Med** | 1.0mm | 0.3mm | `VSYS`, `VSYS_SENSE`, `Protected_VBUS`, `VBUS_RAW`, `BQ_SW`, `BQ_PMID`, `+5V_TO_LEDS`, `Net-(C7-Pad2)` |
| **Power_Low** | 0.75mm | 0.25mm | `VBAT`, `BAT_RAW`, `BQ_REGN` |
| **Power_3V3** | 0.5mm | 0.2mm | `+3.3V` |
| **Sensitive** | 0.2mm | 0.25mm | `BOOST_FB`, `BOOST_COMP`, `COMP_MID` |
| **Default** | 0.25mm | 0.2mm | Everything else |

## Component Position Reference

| Ref | Part | Position (x, y) | Key Pins |
|-----|------|-----------------|----------|
| U5 | BQ24195 | (82.75, 122.25) | Top: SW/BTST/REGN/PMID/PVBUS. Left: PVBUS/GND/I2C. Bottom: INT/OTG/ILIM/TS. Right: VBAT/VSYS/GND |
| U6 | TPS61088 | (69.77, 135.95) rot 90° | Right: VSYS_SENSE/FSW/SW×4/BOOT/VSYS_SENSE. Left: GND/MODE/+5V×3/FB/COMP/ILIM. Top: VCC/GND. Bottom: SS/GND |
| L1 | 2.2µH | (83.1, 114.35) rot 90° | Pad 1 (BQ_SW) at y=116.6, Pad 2 (VSYS) at y=112.1 |
| L2 | 2.2µH 10A | (76.474, 136.456) | Pad 1 (BOOST_SW) at x=73.5, Pad 2 (VSYS_SENSE) at x=79.5 |
| R44 | 10mΩ | (81.737, 130.9) | Pad 1 (VSYS) at x=78.8, Pad 2 (VSYS_SENSE) at x=84.7 |
| U7 | INA219 | (88.2, 130.9) rot 180° | Pin 1 (VSYS) at (87.0, 129.9), Pin 2 (VSYS_SENSE) at (87.0, 130.6) |
| J7 | USB-C | (80.67, 106.17) | VBUS pads at y≈108-109 area |
| J8 | JST PH | (67.15, 119) rot -90° | Pad 1 (BAT_RAW) at (70, 118), Pad 2 (GND) at (70, 120) |
| U1 | AP2112K | (106.535, 125.55) | Pin 1/3 (+5V input), Pin 5 (+3.3V output) |
| F1 | 3A fuse | (106.95, 118.25) | Pad 1 (+5V), Pad 2 (to R27) |
| F2 | 3A fuse | (82.407, 110.859) | Pad 1 (VBUS_RAW), Pad 2 (Protected_VBUS) |

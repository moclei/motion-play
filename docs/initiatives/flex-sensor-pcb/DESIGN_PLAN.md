# Flex Sensor PCB Design Plan

> **Goal**: Angle the VCNL4040 sensors outward (~2°) to reduce detection overlap and improve direction discrimination for fast-moving objects.

## Problem Statement

- Current rigid PCB has both sensors facing straight "up" (perpendicular to PCB)
- Fast-moving objects sometimes trigger both sensors simultaneously
- Sample rate is near maximum; can't solve this in software alone
- Need physical separation of detection windows via sensor angling

## Proposed Solution: Hybrid Rigid + Flex

Split the sensor board into:
1. **Rigid "base" PCB** - Connector, mux, shared circuitry, solder finger interface
2. **Flex "sensor strip"** - Single strip with both VCNL4040s, bent into V-shape

```
                         RIGID BASE PCB
                    ┌─────────────────────┐
                    │  (PCA9546A, J1,     │
                    │   diodes, LED,      │
                    │   caps, resistors)  │
                    │                     │
                    │  [ZIF FPC Connector]│  ← C132510 (8-pin, 1.0mm pitch)
                    └──────────┬──────────┘
                               │ Flex tail inserts here
                    ┌──────────┴──────────┐
                    │   [Connector Tail]  │  ← Exposed pads (top layer)
                    │                     │
               ↙ 2° │   FLEX SENSOR STRIP │ 2° ↘
                    │                     │
              ┌─────┴─────┐         ┌─────┴─────┐
              │   IC1     │  ~10mm  │   IC2     │
              │ VCNL4040  │←───────→│ VCNL4040  │
              └───────────┘         └───────────┘
```

The flex strip bends at the center, creating a shallow V-shape. Each sensor faces slightly outward. Mounted on a 3D-printed backing with a V-groove.

---

## Component Split

### On Rigid Base PCB
| Component | Function | Why Rigid |
|-----------|----------|-----------|
| J1 | JST-SH 5-pin connector | Needs mechanical strength for plug/unplug |
| **FPC1** | **FPC ZIF connector (C132510)** | **Connection to flex sensor strip** |
| U1 | PCA9546A I2C mux | Central to both sensors, heat dissipation |
| JP3, JP4 | Address jumpers | Manual configuration access |
| R1, R2 | Main I2C pull-ups (4.7kΩ) | Shared between sensors |
| R3 | Reset pull-up (10kΩ) | Connected to mux |
| R5 | INT pull-up (8.2kΩ) | Shared interrupt line |
| **R6-R9** | **Per-sensor I2C pull-ups (4.7kΩ)** | **Shorter path to mux** |
| R10, R11 | 22Ω series resistors | I2C line conditioning |
| R12-R14 | 10kΩ pull-ups | Additional control signals |
| D2, D3 | BAT54S Schottky diodes | Interrupt combining |
| D1, R4 | Power LED + resistor | Visual indicator |
| C1, C2 | Main bypass caps | Bulk power filtering |
| TP1-TP5 | Test points | Debug access |

### On Flex Sensor Strip (×1)
| Component | Function | Why Flex |
|-----------|----------|----------|
| IC1, IC2 | Both VCNL4040 sensors | Need to be angled outward |
| C6, C7 | 0.1µF bypass caps (×2) | Must be close to each sensor |
| C4, C8 | 2.2µF LED anode caps (×2) | Must be close to each sensor |

**Flex strip dimensions**: ~25mm × 8mm (sensors 10mm apart center-to-center)

### Decision: I2C Pull-ups for Sensor Channels
The per-sensor I2C pull-ups (R6-R9, 4.7kΩ each) can go on either:
- **Rigid base** (recommended) - Fewer components on flex, easier routing
- **Flex wings** - Shorter I2C trace length to sensor

**Recommendation**: Put R6-R9 on rigid base. The trace length difference is minimal.

---

## Connection: Rigid to Flex

### Chosen: ZIF FPC Connector

**Rigid side**: FPC ZIF connector (physical component)
- **LCSC Part**: C132510
- **Manufacturer**: Ckmtw F-FPC1M08P-A310
- **Specs**: 8-pin + 2 mechanical, 1.0mm pitch, top contact, slide lock
- **FPC thickness**: 0.3mm
- **Height above board**: 2.5mm

**Flex side**: Exposed copper pads (connector tail)
- Just copper pads at board edge, no physical component
- Pads must be on **TOP layer** (top-contact connector)
- Pad pitch: 1.0mm to match connector
- Requires stiffener on connector tail area

### Pin Order (Optimized for Signal Integrity)

INT lines used as buffers between power/ground and I2C signals:

| Pin | Signal | Purpose |
|-----|--------|---------|
| 1 | 3.3V | Power |
| 2 | INT1 | Interrupt sensor 1 (buffer between power and I2C) |
| 3 | SDA1 | I2C data sensor 1 |
| 4 | SCL1 | I2C clock sensor 1 |
| 5 | GND | Ground (shield between sensor groups) |
| 6 | INT2 | Interrupt sensor 2 (buffer after GND) |
| 7 | SDA2 | I2C data sensor 2 |
| 8 | SCL2 | I2C clock sensor 2 |
| 9 | GND | Mechanical mounting (connect to GND) |
| 10 | GND | Mechanical mounting (connect to GND) |

```
Pin Layout:
┌─────────────────────────────────────────────────────────────┐
│ 3.3V │ INT1 │ SDA1 │ SCL1 │ GND │ INT2 │ SDA2 │ SCL2 │ GND │ GND │
│  1   │  2   │  3   │  4   │  5  │  6   │  7   │  8   │  9  │ 10  │
└─────────────────────────────────────────────────────────────┘
  Power  Buffer  ──I2C 1──  Shield  Buffer  ──I2C 2──   Mechanical
```

**Why this order:**
- INT1 shields 3.3V ripple from SDA1
- GND in middle separates sensor 1 from sensor 2
- INT2 provides additional shielding after GND
- I2C pairs (SDA+SCL) kept adjacent for matched routing
- INT lines are mostly quiet (good passive shields)

---

## Pitfalls & Considerations

### 🔴 Flex PCB Pitfalls

1. **Layer Count**: JLCPCB flex is typically 1-2 layers
   - Your current design is 4-layer
   - Flex wings only need routing for 5 signals, so 2 layers is fine
   - Rigid base can remain 4-layer

2. **Minimum Bend Radius**: Rule of thumb is 10× material thickness
   - 0.1mm flex → 1mm minimum bend radius
   - For 2° bend, this is not a concern (very gentle curve)
   
3. **Component Placement Near Bend**: 
   - Keep SMD components 1-2mm away from bend line
   - VCNL4040 and caps should be on the flat portion of the wing

4. **Trace Width at Bend**:
   - Widen traces where they cross bend zones
   - Use curved traces, not 90° angles
   - No vias in bend area

5. **Stiffener Requirement**:
   - Both sensor areas need polyimide stiffener (keep sensors flat)
   - Only the CENTER zone (~5mm) should be flexible (the bend point)
   - JLCPCB can add stiffeners during manufacturing
   - Stiffener layout: `[STIFF]---[FLEX]---[STIFF]`

6. **Copper Adhesion**:
   - Flex uses adhesive-based copper bonding
   - Small pads can lift under stress
   - Use adequate pad sizes for the VCNL4040 footprint

### 🟡 I2C on Flex Pitfalls

1. **Trace Impedance**:
   - Flex has different dielectric (polyimide vs FR4)
   - I2C at 400kHz is forgiving; this won't be an issue
   - Keep SDA/SCL traces similar length (within 5mm)

2. **Crosstalk**:
   - Route SDA and SCL with ground between them if possible
   - Or keep them 2× trace width apart

3. **Pull-up Location**:
   - Keep pull-ups on rigid base (shorter path to mux)
   - Avoids needing resistors on flex

4. **No Vias in Signal Path**:
   - On 2-layer flex, route I2C entirely on one layer if possible
   - Vias in flex are stress points

5. **Routing Across Bend Zone**:
   - All 8 signals must cross the center bend to reach IC2
   - Use wider traces (0.2mm → 0.3mm) in bend zone
   - Curve traces perpendicular to bend axis
   - No vias in bend zone

### 🟠 FPC Connector Pitfalls

1. **Connector Tail Design**:
   - Flex tail must match connector specs exactly
   - Pad pitch: 1.0mm (must be precise)
   - FPC thickness: 0.3mm (order flex with correct stackup)
   - Pads on TOP layer (C132510 is top-contact)

2. **Stiffener on Tail**:
   - Connector tail area MUST have stiffener
   - Without stiffener, flex is too floppy to insert
   - Stiffener provides rigidity for insertion/removal

3. **Insertion Depth**:
   - Ensure flex tail is long enough to fully engage connector
   - Typical insertion depth: 2-3mm
   - Add alignment marks on flex for consistent insertion

4. **Latch Mechanism**:
   - C132510 uses slide lock (ZIF)
   - Open latch → insert flex → close latch
   - Don't force flex in with latch closed

### 🟢 Mechanical Pitfalls

1. **Mounting Strategy**:
   - 3D print a backing with:
     - Flat pocket for rigid base
     - V-groove for flex strip (creates the bend angle)
     - Angle of V-groove determines sensor tilt (2° = 176° included angle)
   - Glue or double-sided tape to secure flex into groove

2. **Bend Location**:
   - The flex bends at the CENTER, between the two sensors
   - Sensors themselves sit on flat portions of the flex
   - Keep bend zone free of traces if possible, or use wider traces

3. **Sensor Window**:
   - Ensure 3D-printed mount doesn't block VCNL4040 field of view
   - The sensor needs clear line-of-sight
   - V-groove walls must be lower than sensor height

4. **Cable Strain**:
   - JST-SH connector is on rigid base (good)
   - No stress transferred to flex

---

## Implementation Phases

### Phase 1: Design (1-2 weeks)
- [x] Design rigid base PCB in KiCad (`hardware/sensor-rigid/`)
  - Reused existing schematic, removed IC1, IC2, C4, C6, C7, C8
  - Added FPC ZIF connector (C132510) with optimized pin order
  - Kept R6-R9 (I2C pull-ups) on rigid
- [ ] Design flex sensor strip PCB in KiCad (`hardware/sensor-flex/`)
  - 2× VCNL4040 + 4 caps + connector tail pads
  - 2-layer, polyimide, 0.3mm thickness
  - Stiffener on: sensor areas + connector tail
  - Bend zone in center (~5mm unstiffened)
  - All pads/traces on TOP layer (top-contact connector)
- [ ] Design 3D-printed mounting jig
  - Flat pocket for rigid base
  - V-groove for flex strip (adjustable angle)
  - Open top for sensor visibility

### Phase 2: Prototype Order (2-3 weeks)
- [ ] Order rigid base from JLCPCB (standard FR4 service)
- [ ] Order flex sensor strip from JLCPCB (flex PCB service)
  - Thickness: 0.3mm total (to match connector C132510)
  - Stiffener: polyimide on sensor areas + connector tail
  - Surface finish: ENIG on connector pads
  - Leave center ~5mm unstiffened for bend
- [ ] 3D print mounting jig (try multiple angles: 2°, 5°, 10°)

### Phase 3: Assembly & Test (1 week)
- [ ] Insert flex tail into ZIF connector on rigid base
- [ ] Mount assembled unit in V-groove jig
- [ ] Verify I2C communication to both sensors
- [ ] Test with existing firmware (no changes needed)
- [ ] Compare detection performance vs current flat design
- [ ] Test different V-groove angles with same flex strip

### Phase 4: Iterate
- [ ] Adjust angle if needed (reprint jig only)
- [ ] If successful, consider rigid-flex integrated design for production

---

## Cost Estimate (per sensor board)

| Item | Current Design | Hybrid Design |
|------|----------------|---------------|
| Rigid PCB | ~$2 | ~$1.50 (smaller) |
| Flex PCB | - | ~$4 (single strip) |
| Assembly | ~$5 | ~$4 (rigid) + ~$3 (flex) |
| **Total** | ~$7 | ~$12.50 |

**Note**: First prototype run will be more expensive due to setup fees. Cost decreases significantly at volume. Single flex strip is cheaper than two separate wings.

---

## Alternative: Pure Rigid-Flex PCB

If the hybrid approach proves successful, consider a **single rigid-flex PCB** for production:
- No solder finger connection
- Single manufacturing order
- More expensive per unit, but fewer assembly steps
- JLCPCB offers rigid-flex with PCBA

This would be Phase 5 if Phase 3-4 validate the angled sensor concept.

---

## Files Created / To Create

```
hardware/
├── sensor-rigid/              # ✅ Rigid base PCB project (DONE)
│   ├── sensor-rigid.kicad_sch
│   ├── sensor-rigid.kicad_pcb
│   └── ...
├── sensor-flex/               # 🔄 Flex sensor strip PCB project (IN PROGRESS)
│   ├── sensor-flex.kicad_sch
│   ├── sensor-flex.kicad_pcb
│   └── ...
├── libraries/
│   └── easyeda2kicad/         # ✅ FPC connector imported from LCSC
│       ├── easyeda2kicad.kicad_sym
│       ├── easyeda2kicad.pretty/
│       └── 3dshapes/
└── mounts/
    └── sensor-mount-v-groove.stl  # 📋 TODO: 3D-printed mounting jig
```

---

## Questions Resolved

1. ~~**Exact angle**: Start with 2°, but may need tuning (5°, 10°?)~~ → Determined by 3D-printed jig, can experiment
2. ~~**Flex wing dimensions**: How much space for routing + sensor + caps?~~ → ~25mm × 8mm
3. ~~**Stiffener material**: Polyimide vs FR4 stiffener on flex?~~ → Polyimide (standard for JLCPCB flex)
4. ~~**Connector orientation**: JST-SH pointing which direction relative to hoop?~~ → TBD during enclosure design
5. ~~**Connection method**: Solder fingers vs FPC connector~~ → **FPC ZIF connector (C132510)**
6. ~~**Pin order**: Power/signal arrangement~~ → **3.3V-INT1-SDA1-SCL1-GND-INT2-SDA2-SCL2-GND-GND**

## Remaining Questions - RESOLVED ✅

1. **Flex PCB stackup**: ✅ JLCPCB 2-layer flex is ~0.11mm. Add 0.2mm PI stiffener for 0.3mm total.
2. **Connector tail dimensions**: ✅ Custom footprint created: `FPC_Tail_10P_1.0mm_TopContact`
   - Signal pads: 0.5mm × 2.5mm at 1.0mm pitch
   - Mechanical pads: 1.5mm × 2.5mm at ±5.5mm from center
   - Pads on TOP layer for top-contact connector
3. **Stiffener zones**: ✅ Three zones defined:
   - Connector tail: 13mm × 4mm (0.2mm PI stiffener)
   - Sensor area 1: 8mm × 8mm (0.1mm PI stiffener)
   - Sensor area 2: 8mm × 8mm (0.1mm PI stiffener)
   - Bend zone: ~5mm center section (NO stiffener)

## Files Created

- **Footprint**: `hardware/libraries/motion-play-footprints.pretty/FPC_Tail_10P_1.0mm_TopContact.kicad_mod`
- **Symbol**: `FPC_Tail_10P` in `hardware/libraries/motion-play-symbols.kicad_sym`
- **Setup Guide**: `hardware/sensor-flex/FLEX_PCB_SETUP.md`

---

*Created: December 9, 2025*
*Updated: December 11, 2025*
*Status: Phase 1 - sensor-rigid complete, sensor-flex setup complete, ready for schematic/layout*


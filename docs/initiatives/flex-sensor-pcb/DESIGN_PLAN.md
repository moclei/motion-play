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
                    └──────────┬──────────┘
                               │ Solder Fingers
                    ┌──────────┴──────────┐
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
| U1 | PCA9546A I2C mux | Central to both sensors, heat dissipation |
| JP3, JP4 | Address jumpers | Manual configuration access |
| R1, R2 | Main I2C pull-ups (4.7kΩ) | Shared between sensors |
| R3 | Reset pull-up (10kΩ) | Connected to mux |
| R5 | INT pull-up (10kΩ) | Shared interrupt line |
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

### Option A: Solder Fingers (Recommended)
- Exposed copper pads on flex edge, soldered to matching pads on rigid
- User has experience with solder wicking
- No connector overhead
- Permanent but reliable connection

**Finger pitch**: 1.0mm (matches JST-SH, familiar)
**Finger count**: 8 signals needed:
  - 3.3V, GND (shared power)
  - SDA1, SCL1, INT1 (sensor 1 via mux channel 0)
  - SDA2, SCL2, INT2 (sensor 2 via mux channel 1)
**Finger width**: 0.5mm
**Finger length**: 2-3mm for solder overlap

*Note: Could reduce to 6 fingers if interrupt lines are combined on the flex strip before connecting to rigid base.*

### Option B: Castellated Holes
- Half-holes on flex edge that wrap around
- Allows soldering from the side
- More mechanically robust than flat fingers

### Option C: FPC Connector
- ZIF connector on rigid, mates with flex
- Adds cost, height, potential failure point
- Not recommended for this application

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

### 🟠 Rigid-to-Flex Connection Pitfalls

1. **Solder Joint Stress**:
   - The finger connection is a stress concentration point
   - Add strain relief: small curve in flex before rigid
   - Don't mount flex at 90° to rigid

2. **Thermal Mismatch**:
   - Flex and rigid expand at different rates
   - For your small board, this is negligible
   - Would matter more in automotive/industrial

3. **Alignment During Soldering**:
   - Create a soldering jig (3D printed)
   - Align flex fingers to rigid pads before applying heat
   - Use low-temp solder paste if hand soldering

4. **Inspection**:
   - Solder joints are hidden under flex
   - Consider adding a test point on each wing to verify connectivity

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
- [ ] Design rigid base PCB in KiCad
  - Reuse existing schematic
  - Add 8-pin solder finger footprint on one edge
  - Remove VCNL4040s and their local caps (C4, C6, C7, C8)
- [ ] Design flex sensor strip PCB in KiCad
  - New project (simpler)
  - 2× VCNL4040 + 4 caps + solder fingers
  - 2-layer, polyimide
  - Add stiffener on sensor areas, leave center bendable
  - Keep traces wide at bend zone
- [ ] Design 3D-printed mounting jig
  - Flat pocket for rigid base
  - V-groove for flex strip (adjustable angle)
  - Open top for sensor visibility

### Phase 2: Prototype Order (2-3 weeks)
- [ ] Order rigid base from JLCPCB (standard FR4 service)
- [ ] Order flex sensor strip from JLCPCB (flex PCB service)
  - Request stiffener on both sensor areas
  - Request gold fingers on connection edge
  - Leave center 5mm unstiffened for bend
- [ ] 3D print mounting jig (try multiple angles: 2°, 5°, 10°)

### Phase 3: Assembly & Test (1 week)
- [ ] Solder flex strip to rigid base using alignment jig
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

## Files to Create

```
hardware/
├── pcb-sensor-rigid-base/     # New rigid base PCB project
│   └── kicad/
├── pcb-sensor-flex-strip/     # New flex sensor strip PCB project  
│   └── kicad/
└── mounts/
    └── sensor-mount-v-groove.stl  # 3D-printed mounting jig with V-groove
```

---

## Questions to Resolve

1. **Exact angle**: Start with 2°, but may need tuning (5°, 10°?)
2. **Flex wing dimensions**: How much space for routing + sensor + caps?
3. **Stiffener material**: Polyimide vs FR4 stiffener on flex?
4. **Connector orientation**: JST-SH pointing which direction relative to hoop?

---

*Created: December 9, 2025*
*Status: Planning*


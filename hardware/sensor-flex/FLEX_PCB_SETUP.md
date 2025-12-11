# Flex PCB Setup Guide for sensor-flex

This guide covers setting up the sensor-flex PCB in KiCad for JLCPCB flex manufacturing.

## 1. Layer Stackup Configuration

### JLCPCB 2-Layer Flex PCB Standard Stackup

| Layer | Material | Thickness |
|-------|----------|-----------|
| Top Coverlay | Polyimide + Adhesive | 0.0275mm (12.5µm PI + 15µm adhesive) |
| F.Cu (Top Copper) | Copper | 0.012mm (12µm = 1/3 oz) |
| Adhesive | Acrylic | 0.015mm |
| Core | Polyimide | 0.025mm (25µm PI) |
| Adhesive | Acrylic | 0.015mm |
| B.Cu (Bottom Copper) | Copper | 0.012mm (12µm = 1/3 oz) |
| Bottom Coverlay | Polyimide + Adhesive | 0.0275mm |
| **Total Flex Thickness** | | **~0.11mm** |

### With Stiffener (for 0.3mm FPC connector)

The C132510 ZIF connector requires 0.3mm FPC thickness. JLCPCB adds polyimide stiffener to achieve this:

- Flex core: ~0.11mm
- PI Stiffener: ~0.19mm
- **Total with stiffener: 0.3mm**

### KiCad Board Setup (File → Board Setup → Board Stackup)

1. **Set Layer Count**: Click "Layer" on the left, set to **2 layers**
2. **Edit Stackup**: Click "Physical Stackup" and configure:

```
Layers:
- F.SilkS: Top Silk Screen
- F.Paste: Top Solder Paste  
- F.Mask: Top Solder Mask (thickness: 0)  ← No coverlay opening in KiCad, handled by manufacturer
- F.Cu: copper (thickness: 0.012mm)
- dielectric 1: core
    - Material: Polyimide
    - Thickness: 0.05mm (accounts for PI + adhesive layers)
    - Epsilon_r: 3.4
    - Loss tangent: 0.002
- B.Cu: copper (thickness: 0.012mm)
- B.Mask: Bottom Solder Mask (thickness: 0)
- B.Paste: Bottom Solder Paste
- B.SilkS: Bottom Silk Screen

Board thickness: 0.11mm (KiCad calculates automatically)
Copper finish: ENIG (recommended for connector pads)
```

**Important**: The "User.1" layer is already renamed to "Stiffener" - use this for stiffener outlines.

---

## 2. Design Rules for Flex PCB

### Minimum Specifications (JLCPCB Flex Capabilities)

| Parameter | Minimum | Recommended |
|-----------|---------|-------------|
| Trace width | 0.1mm | **0.15mm** (0.2mm in bend zone) |
| Trace spacing | 0.1mm | **0.15mm** |
| Via diameter | 0.3mm | **Avoid vias** (stress points) |
| Via drill | 0.15mm | **Avoid vias** |
| Annular ring | 0.1mm | 0.15mm |
| Pad size | 0.3mm min | Per component spec |
| SMD clearance | 0.1mm | 0.15mm |

### Bend Zone Rules (Critical!)

1. **Trace width in bend zone**: Increase to **0.2-0.3mm** (wider = more durable)
2. **Trace angles**: Use **curved traces** (no 90° angles in bend area)
3. **No vias in bend zone**: Vias are stress concentration points
4. **Trace orientation**: Route traces **perpendicular** to bend axis
5. **Component clearance**: Keep components **1.5mm minimum** from bend line

### KiCad Design Rules Setup

Go to **File → Board Setup → Design Rules**:

```
Constraints:
- Minimum clearance: 0.15mm
- Minimum track width: 0.15mm
- Minimum via diameter: 0.4mm (but avoid using vias)
- Minimum via drill: 0.2mm
- Minimum hole diameter: 0.2mm
- Minimum annular ring: 0.15mm

Pre-defined Sizes:
- Track widths: 0.15, 0.2, 0.25, 0.3mm
- Via size: 0.4/0.2mm (diameter/drill)

Net Classes:
- Default: 0.15mm track, 0.15mm clearance
- Power: 0.25mm track, 0.15mm clearance
- BendZone: 0.25mm track, 0.2mm clearance (custom class for bend area traces)
```

---

## 3. Stiffener Zones

### Purpose of Stiffeners

1. **Connector tail**: Makes flex rigid enough to insert into ZIF connector (required for 0.3mm thickness)
2. **Sensor areas**: Keeps VCNL4040 sensors flat and stable (component mounting)
3. **Leave center flexible**: The bend zone (~5mm) remains unstiffened

### Stiffener Layout

```
┌─────────────────────────────────────────────────────────────┐
│                        FLEX PCB TOP VIEW                     │
│                                                               │
│  ┌─────────┐    ┌──────────────────┐    ┌─────────┐         │
│  │ SENSOR  │    │                  │    │ SENSOR  │         │
│  │  AREA   │    │    BEND ZONE     │    │  AREA   │         │
│  │ (stiff) │    │  (NO STIFFENER)  │    │ (stiff) │         │
│  │         │    │      ~5mm        │    │         │         │
│  │  IC1    │    │                  │    │  IC2    │         │
│  │  C4,C6  │    │    ↑ traces ↓    │    │  C8,C7  │         │
│  └─────────┘    └──────────────────┘    └─────────┘         │
│                                                               │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              CONNECTOR TAIL AREA (stiff)               │  │
│  │   [10] [9] [8] [7] [6] [5] [4] [3] [2] [1]           │  │
│  │   GND GND SCL2 SDA2 INT2 GND SCL1 SDA1 INT1 3.3V     │  │
│  └───────────────────────────────────────────────────────┘  │
│                           ↓ BOARD EDGE                       │
└─────────────────────────────────────────────────────────────┘
```

### Drawing Stiffener Zones in KiCad

1. Select the **"Stiffener" (User.1)** layer
2. Use **Draw Rectangle** or **Draw Polygon** tools
3. Draw closed shapes around:
   - **Sensor area 1**: Around IC1 and its capacitors (C4, C6)
   - **Sensor area 2**: Around IC2 and its capacitors (C8, C7)
   - **Connector tail**: The entire FPC tail section (~4mm deep)

### Stiffener Dimensions

| Zone | Size | Thickness (JLCPCB) |
|------|------|-------------------|
| Connector tail | 13mm × 4mm | 0.2mm PI (total 0.3mm with flex) |
| Sensor area 1 | 8mm × 8mm | 0.1-0.2mm PI |
| Sensor area 2 | 8mm × 8mm | 0.1-0.2mm PI |
| Bend zone (center) | ~5mm wide | **NO STIFFENER** |

**Note**: When ordering, specify stiffener zones in the order notes or use a separate gerber layer.

---

## 4. Connector Tail Footprint

The custom footprint `FPC_Tail_10P_1.0mm_TopContact` is located at:
```
hardware/libraries/motion-play-footprints.pretty/FPC_Tail_10P_1.0mm_TopContact.kicad_mod
```

### Footprint Details

- **10 pads** (8 signal + 2 mechanical)
- **1.0mm pitch** for signal pads
- **Pads on TOP copper layer** (top-contact connector)
- **Signal pads**: 0.5mm × 2.5mm
- **Mechanical pads**: 1.5mm × 2.5mm
- **Board edge**: At Y=0 (pads extend from edge into board)
- **Stiffener zone indicator** on User.1 layer

### Pin Assignment

| Pin | Signal | Net Name |
|-----|--------|----------|
| 1 | 3.3V | +3.3V |
| 2 | INT1 | Net-(IC1-INT) |
| 3 | SDA1 | Net-(IC1-SDAT) |
| 4 | SCL1 | Net-(IC1-SCLK) |
| 5 | GND (shield) | GND |
| 6 | INT2 | Net-(IC2-INT) |
| 7 | SDA2 | Net-(IC2-SDAT) |
| 8 | SCL2 | Net-(IC2-SCLK) |
| 9 | GND (mechanical) | GND |
| 10 | GND (mechanical) | GND |

---

## 5. Routing Guidelines

### General Flex Routing

1. **Minimize layer changes**: Use single-layer routing where possible
2. **Curve all corners**: Use 45° or arc traces, never 90° angles
3. **Match I2C lengths**: Keep SDA and SCL traces within 2mm of each other
4. **Ground pour**: Add copper pour on unused areas (helps EMI and mechanical strength)

### Bend Zone Routing

```
GOOD (perpendicular to bend):        BAD (parallel to bend):
     
     ↓ bend axis                          ↓ bend axis
━━━━━━━━━━━━━━━━━━━━                 │ │ │ │ │ │ │ │
     │ │ │ │ │ │                     │ │ │ │ │ │ │ │
     │ │ │ │ │ │                     ↓ ↓ ↓ ↓ ↓ ↓ ↓ ↓
━━━━━━━━━━━━━━━━━━━━                 
```

### Trace Width Transitions

When transitioning from normal area to bend zone:
- Use **gradual taper** (45° angle)
- Don't create stress concentration points

```
Normal area → [taper] → Bend zone → [taper] → Normal area
   0.15mm      45°       0.25mm      45°       0.15mm
```

---

## 6. JLCPCB Ordering Specifications

### Flex PCB Order Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| **Base Material** | Polyimide (PI) | Yellow flex material |
| **Layers** | 2 | Single-sided also available |
| **Flex Thickness** | 0.11mm | Standard JLCPCB flex |
| **Copper Weight** | 1/3 oz (12µm) | Standard for flex |
| **Surface Finish** | ENIG | Required for connector pads (hard gold better but more expensive) |
| **Coverlay Color** | Yellow | Standard PI coverlay |
| **Silkscreen** | White | Optional for flex |
| **Stiffener** | PI (Polyimide) | Specify thickness per zone |
| **Stiffener Thickness** | 0.1-0.2mm | Match connector requirements |
| **Minimum Trace/Space** | 0.1/0.1mm | 0.15/0.15mm recommended |

### Order Notes to Include

When placing the order, add these notes:

```
FLEX PCB ORDER NOTES:
1. 2-layer polyimide flex PCB
2. Stiffener zones marked on User.1 layer (Stiffener layer in gerber)
3. Connector tail area requires 0.2mm PI stiffener (total 0.3mm for FPC connector)
4. Sensor areas require 0.1mm PI stiffener
5. Center bend zone (~5mm) - NO STIFFENER
6. ENIG finish on connector tail pads
7. FPC connector mating part: C132510 (1.0mm pitch, 8-pin, top contact)
```

### Gerber Files to Export

- F.Cu (Top copper)
- B.Cu (Bottom copper) - if used
- F.Mask (Top solder mask openings)
- B.Mask (Bottom solder mask openings)
- F.Paste (Top paste stencil)
- Edge.Cuts (Board outline)
- **User.1 / Stiffener** (Stiffener zones - export as separate layer)
- F.SilkS (Optional silkscreen)

### Cost Estimate

For a small flex PCB (~25mm × 15mm), qty 5:
- Base flex PCB: $15-25
- Stiffener: +$5-10
- ENIG: Included in flex pricing
- Setup fee (first order): ~$20

Total first prototype run: ~$40-60 for 5 pcs

---

## 7. Assembly Notes

### Component Placement

1. **VCNL4040 sensors** (IC1, IC2):
   - Place on stiffened areas only
   - Position at least 1.5mm from bend line
   - Ensure IR LED/sensor window faces outward (away from PCB center)

2. **Bypass capacitors** (C4, C6, C7, C8):
   - Place as close to sensor VDD pins as possible
   - All on stiffened areas
   - C4, C8: 2.2µF (LED anode capacitors)
   - C6, C7: 0.1µF (VDD bypass)

### Hand Assembly

Flex PCBs require careful handling:
1. Support the flex during soldering (use a flat surface)
2. Lower soldering iron temperature if possible (~300°C)
3. Avoid excessive force on components
4. Don't bend the PCB until fully assembled and inspected

### Testing Before Bending

1. Check continuity of all traces
2. Verify I2C communication with both sensors (flat configuration)
3. Check for shorts (especially on FPC connector pads)
4. Then carefully bend to final angle

---

## 8. Checklist Before Manufacturing

- [ ] Layer count set to 2
- [ ] Stackup configured for polyimide
- [ ] Board thickness ~0.11mm
- [ ] Design rules set for flex (0.15mm min trace/space)
- [ ] No vias in bend zone
- [ ] Wider traces (0.25mm) in bend zone
- [ ] Curved traces only (no 90° angles)
- [ ] Components placed on stiffened areas only
- [ ] Stiffener zones drawn on User.1 layer
- [ ] FPC tail footprint at board edge
- [ ] Pads on correct layer (TOP for top-contact connector)
- [ ] ENIG surface finish specified
- [ ] Ground pour added (optional but recommended)
- [ ] DRC passes with no errors

---

*Last updated: December 11, 2025*

# VCNL4040 Sensor Spacing, Covers, and Detection Geometry

**Purpose**: Document physical design considerations for optimal sensor performance.

## Detection Geometry

From the VCNL4040 datasheet and application note:

### IR Emitter Cone (Fig. 4, 10 in datasheet)
- **Half-intensity angle**: ±15° from vertical
- This is a relatively narrow beam
- Peak wavelength: 940nm

### Proximity Photodiode Sensitivity (Fig. 7 in application note)
- **Half-sensitivity angle**: ±55° from vertical
- Much wider acceptance angle than emitter
- Peak sensitivity: 940nm (matched to emitter)

### Visualized:
```
           ▲ (normal to sensor)
           │
      ╱    │    ╲
    ╱ 15°  │  15° ╲   ← IR Emitter cone (narrow)
  ╱        │        ╲
 ╱    55°  │  55°    ╲ ← Photodiode sensitivity (wide)
```

### Implications for Your Design
With sensors 10mm apart (on-center):
- At 50mm distance: emitter beams are ~13mm apart (minimal overlap)
- At 100mm distance: emitter beams are ~26mm apart
- The wide photodiode angle means each sensor can "see" reflections from the other's emitter somewhat

**Bottom Line**: 10mm spacing should be fine. The narrow emitter cone and the sensor's DC-rejection circuitry (which filters out constant ambient light, including neighboring IR) mean crosstalk should be minimal.

---

## Cover Window Design

### The Problem You're Experiencing
> "If I put a cover on the PCB it seems to raise the baseline proximity of a sensor, even though the cover has a 'window' above each sensor."

This is **expected behavior** documented in the application note (p. 4):
> "There is some reflection of the infrared emitted light off the surfaces of the components surrounding the VCNL4040. The distance to the cover, proximity of surrounding components, tolerances of the sensor... all contribute to this reflection. The result... is the production of an output current on the proximity sensing photodiode. This current is converted into a count called the **offset count**."

### Solution: Use PS_CANC Register

The VCNL4040 has a built-in cancellation feature:
1. Measure the baseline with cover installed (no object present)
2. Write this value to `PS_CANC` register (0x05)
3. Sensor now outputs: `actual_reading - offset`

**In your firmware**, you could add:
```cpp
void calibrateBaselineOffset(uint8_t sensorIndex) {
    // Measure average baseline over ~100 readings
    uint32_t sum = 0;
    for (int i = 0; i < 100; i++) {
        sum += sensors[sensorIndex].getProximity();
        delay(10);
    }
    uint16_t baseline = sum / 100;
    
    // Write to PS_CANC register
    // Note: This requires raw I2C access - Adafruit library doesn't expose this
    Wire.beginTransmission(0x60);
    Wire.write(0x05);  // PS_CANC register
    Wire.write(baseline & 0xFF);        // Low byte
    Wire.write((baseline >> 8) & 0xFF); // High byte
    Wire.endTransmission();
    
    Serial.printf("Sensor %d baseline set to %d\n", sensorIndex, baseline);
}
```

### Window Sizing Requirements

From the application note (p. 3):

**For a single window** (covers both emitter and detector):
| Distance to Cover | Minimum Window Diameter |
|-------------------|------------------------|
| 0.0 mm | 4.0 mm |
| 0.5 mm | 4.84 mm |
| 1.0 mm | 5.68 mm |
| 1.5 mm | 6.56 mm |
| 2.0 mm | 7.36 mm |
| 3.0 mm | 9.04 mm |

Formula: `d = 4.0mm + (0.84 × cover_distance_mm × 2)`

**For separate holes** (emitter and detector separate):
- Emitter hole: 1.2mm minimum, doesn't need to increase with distance
- Detector hole: Same sizing rules as above

### Window Material

**Can you use clear acrylic to protect the PCB?**

Yes, with caveats:
1. **IR Transmission**: Standard acrylic transmits IR reasonably well (940nm passes through)
2. **Thickness matters**: Thinner is better (reduces internal reflections)
3. **Surface finish**: Matte/anti-reflective coating reduces baseline offset
4. **Color**: Clear or slightly tinted OK; avoid heavily tinted

**Best Practices**:
- Use thin acrylic (0.5-1mm)
- Keep window as close to sensor as mechanically practical
- Apply anti-reflective coating if possible
- Measure and calibrate baseline offset with cover installed

### Window Coating Options
- Anti-reflective (AR) coating: Reduces baseline significantly
- Matte/frosted: Diffuses but increases baseline
- Clear gloss: Highest baseline but works fine with calibration

---

## Green Power LED Interference

Your concern about the green LED 4mm from sensor 1:

**Good news**: The VCNL4040's proximity detection is:
1. Tuned to 940nm (IR), green is ~520-560nm
2. Uses pulsed detection with DC-rejection
3. The green LED is constant (DC), so it's filtered out

**The green LED should NOT affect proximity readings.**

However, it WILL affect ambient light readings if you ever enable them. Solutions:
- Keep ambient light disabled (your current setting)
- OR add the LED enable jumper to your PCB design to disable during testing
- OR use IR-pass filter over window (blocks visible, passes IR)

---

## Recommended Cover Design for Your PCB

Based on your 10mm sensor spacing:

```
┌────────────────────────────────────┐
│           Sensor PCB               │
│                                    │
│   ┌─────┐        ┌─────┐          │
│   │  ◯  │  10mm  │  ◯  │          │
│   │ S1  │ ←────→ │ S2  │          │
│   └─────┘        └─────┘          │
│                                    │
│   Power LED (● green)              │
└────────────────────────────────────┘

Cover Window Design (top view):
┌────────────────────────────────────┐
│           Clear Acrylic            │
│                                    │
│   ┌─────┐        ┌─────┐          │
│   │     │        │     │          │ ← 6mm diameter windows
│   │ ○   │        │  ○  │          │   (for 1mm cover distance)
│   └─────┘        └─────┘          │
│                                    │
│   ● ← opaque area over LED        │
│     (optional, blocks visible      │
│      light if you enable ALS)      │
└────────────────────────────────────┘
```

### Key Dimensions (for 1mm cover distance)
- Window diameter: 6mm (conservative)
- Center-to-center: Match sensor spacing (10mm)
- Divider between windows: Optional, not required for crosstalk prevention

---

## Summary of Answers

| Question | Answer |
|----------|--------|
| Crosstalk between sensors 10mm apart? | Minimal - narrow emitter cone + DC rejection |
| Cover raises baseline? | Normal - use PS_CANC register to calibrate |
| Detection cone size? | Emitter: ±15°, Detector: ±55° |
| Clear acrylic OK? | Yes, thin (0.5-1mm), calibrate baseline |
| Green LED interference? | No effect on proximity (different wavelength + DC rejection) |
| Divider between sensors needed? | No - sensors already isolated by design |

---

*Last Updated: December 2024*


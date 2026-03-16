# PCB Routing Verification Report

**Source:** `motion-play-main.kicad_pcb`  
**SHA-256:** `6c893ac56a2de4c5...`  
**Generated:** 2026-03-16 02:34 UTC  
**Board:** 83 footprints, 641 segments, 156 vias, 6 zones, 85 nets

## Summary: 16 PASS, 4 FAIL, 0 WARNING, 0 SKIP

| Check | Status | Detail |
|-------|--------|--------|
| Trace Width Compliance | **FAIL** | 15 violations, 102 warnings |
| Zone: BOOST_SW on F.Cu | PASS | Switching loop copper pour — zone exists and has fill |
| Zone: +5V on F.Cu | PASS | Output cap cluster pour — zone exists and has fill |
| Zone: +5V on In2.Cu | PASS | +5V distribution plane — zone exists and has fill |
| Zone: GND on In1.Cu | PASS | Primary ground return plane — zone exists and has fill |
| Zone: GND on B.Cu | **FAIL** | Bottom ground fill — zone NOT FOUND on B.Cu |
| Zone: +3.3V on In2.Cu | PASS | Logic area 3.3V zone — zone exists and has fill |
| Path: BOOST_SW loop (U6 SW → L2 pad 1) | PASS | Connected via zone fill: U6.4 → L2.1 |
| Path: BQ_SW (U5 pins 19-20 → L1 pad 1) | PASS | Connected via traces/vias: U5.19 → L1.1 |
| Path: VSYS power (L1 pad 2 → R44 pad 1) | PASS | Connected via traces/vias: L1.2 → R44.1 |
| Path: VSYS_SENSE (R44 pad 2 → L2 pad 2) | PASS | Connected via traces/vias: R44.2 → L2.2 |
| Path: Protected_VBUS (F2 pad 2 → U5 pin 1) | PASS | Connected via traces/vias: F2.2 → U5.1 |
| I2C length match: Main trunk | **FAIL** | SDA=76.8mm, SCL=88.1mm, diff=11.3mm (>10mm) |
| I2C length match: CH0 | PASS | SDA=13.8mm, SCL=13.3mm, diff=0.5mm |
| I2C length match: CH1 | PASS | SDA=8.4mm, SCL=8.3mm, diff=0.1mm |
| I2C length match: CH2 | PASS | SDA=10.8mm, SCL=10.9mm, diff=0.1mm |
| I2C isolation from switching nodes | PASS | All 96 I2C segments clear of 4 exclusion zones |
| Kelvin: VSYS sense (R44.1 → U7.1) | **FAIL** | No dedicated 0.25mm path from R44.1 to U7.1 |
| Kelvin: VSYS_SENSE sense (R44.2 → U7.2) | PASS | Dedicated 0.25mm path exists (6 thin segments on net) |
| FB/COMP routing side | PASS | All FB/COMP traces stay left of U6 center (x < 83.6) |

## Details: trace_widths

### Trace Width Compliance — FAIL

```
  /Power Management/BOOST_VCC on F.Cu: expected 0.25mm, got 0.2mm at (84.35, 135.99)→(86.38, 138.02)
  /Power Management/BOOST_VCC on F.Cu: expected 0.25mm, got 0.2mm at (86.38, 138.02)→(86.38, 138.5)
  /Power Management/BOOST_VCC on F.Cu: expected 0.25mm, got 0.2mm at (84.35, 135.58)→(84.35, 135.99)
  /Power Management/BOOST_SS on F.Cu: expected 0.25mm, got 0.2mm at (81.85, 128.97)→(81.85, 128.2)
  /Power Management/BOOST_SS on F.Cu: expected 0.25mm, got 0.2mm at (84.35, 130.6)→(83.99, 130.24)
  /Power Management/BOOST_SS on F.Cu: expected 0.25mm, got 0.2mm at (83.99, 130.24)→(83.11, 130.24)
  /Power Management/BOOST_SS on F.Cu: expected 0.25mm, got 0.2mm at (84.35, 131.22)→(84.35, 130.6)
  /Power Management/BOOST_SS on F.Cu: expected 0.25mm, got 0.2mm at (83.11, 130.24)→(81.85, 128.97)
  /Power Management/CC2 on F.Cu: expected 0.25mm, got 0.15mm at (92.5, 108.61)→(92.51, 108.62)
  /Power Management/CC2 on F.Cu: expected 0.25mm, got 0.15mm at (92.5, 107.68)→(92.5, 108.61)
  /Power Management/BOOST_FSW on F.Cu: expected 0.25mm, got 0.15mm at (84.55, 128.7)→(84.55, 128.38)
  /Power Management/BOOST_FSW on F.Cu: expected 0.25mm, got 0.15mm at (84.55, 128.38)→(85.22, 127.7)
  /Power Management/BOOST_FSW on B.Cu: expected 0.25mm, got 0.15mm at (85.33, 134.65)→(85.33, 132.23)
  /Power Management/BOOST_FSW on B.Cu: expected 0.25mm, got 0.15mm at (84.55, 131.46)→(84.55, 128.7)
  /Power Management/BOOST_FSW on B.Cu: expected 0.25mm, got 0.15mm at (85.33, 132.23)→(84.55, 131.46)
```


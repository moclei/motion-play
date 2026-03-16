# PCB Routing Verification Report

**Source:** `motion-play-main.kicad_pcb`  
**SHA-256:** `94f079cce6bba778...`  
**Generated:** 2026-03-16 03:03 UTC  
**Board:** 83 footprints, 650 segments, 156 vias, 7 zones, 85 nets

## Summary: 19 PASS, 0 FAIL, 1 WARNING, 0 SKIP

| Check | Status | Detail |
|-------|--------|--------|
| Trace Width Compliance | WARN | 111 power-net width deviations across 5 net classes (review recommended) |
| Zone: BOOST_SW on F.Cu | PASS | Switching loop copper pour — zone exists and has fill |
| Zone: +5V on F.Cu | PASS | Output cap cluster pour — zone exists and has fill |
| Zone: +5V on In2.Cu | PASS | +5V distribution plane — zone exists and has fill |
| Zone: GND on In1.Cu | PASS | Primary ground return plane — zone exists and has fill |
| Zone: GND on B.Cu | PASS | Bottom ground fill — zone exists and has fill |
| Zone: +3.3V on In2.Cu | PASS | Logic area 3.3V zone — zone exists and has fill |
| Path: BOOST_SW loop (U6 SW → L2 pad 1) | PASS | Connected via zone fill: U6.4 → L2.1 |
| Path: BQ_SW (U5 pins 19-20 → L1 pad 1) | PASS | Connected via traces/vias: U5.19 → L1.1 |
| Path: VSYS power (L1 pad 2 → R44 pad 1) | PASS | Connected via traces/vias: L1.2 → R44.1 |
| Path: VSYS_SENSE (R44 pad 2 → L2 pad 2) | PASS | Connected via traces/vias: R44.2 → L2.2 |
| Path: Protected_VBUS (F2 pad 2 → U5 pin 1) | PASS | Connected via traces/vias: F2.2 → U5.1 |
| I2C length match: Main trunk | PASS | SDA=82.0mm, SCL=86.6mm, diff=4.5mm |
| I2C length match: CH0 | PASS | SDA=13.8mm, SCL=13.3mm, diff=0.5mm |
| I2C length match: CH1 | PASS | SDA=8.4mm, SCL=8.3mm, diff=0.1mm |
| I2C length match: CH2 | PASS | SDA=10.8mm, SCL=10.9mm, diff=0.1mm |
| I2C isolation from switching nodes | PASS | All 102 I2C segments clear of 4 exclusion zones |
| Kelvin: VSYS sense (R44.1 → U7.1) | PASS | Dedicated thin path (0.25mm/0.3mm) exists, separate from 1.0mm power traces (17 sense segments) |
| Kelvin: VSYS_SENSE sense (R44.2 → U7.2) | PASS | Dedicated thin path (0.25mm/0.3mm) exists, separate from 1.0mm power traces (11 sense segments) |
| FB/COMP routing side | PASS | All FB/COMP traces stay left of U6 center (x < 83.6) |

## Details: trace_widths

### Trace Width Compliance — WARNING

```
  /Power Management/CC2 on F.Cu: expected 0.25mm, got 0.15mm at (92.5, 108.61)→(92.51, 108.62)
  /Power Management/CC2 on F.Cu: expected 0.25mm, got 0.15mm at (92.5, 107.68)→(92.5, 108.61)
  /Power Management/BOOST_FSW on F.Cu: expected 0.25mm, got 0.15mm at (84.55, 128.7)→(84.55, 128.38)
  /Power Management/BOOST_FSW on F.Cu: expected 0.25mm, got 0.15mm at (84.55, 128.38)→(85.22, 127.7)
  /Power Management/BOOST_FSW on B.Cu: expected 0.25mm, got 0.2mm at (85.33, 134.65)→(85.33, 132.23)
  ... and 2 more in Default
  +3.3V on F.Cu: expected 0.5mm, got 0.25mm at (135.28, 122.78)→(135.3, 122.8)
  +3.3V on F.Cu: expected 0.5mm, got 0.25mm at (151.5, 134)→(151.5, 133.5)
  +3.3V on F.Cu: expected 0.5mm, got 0.25mm at (123.7, 123.4)→(123.7, 122.86)
  +3.3V on F.Cu: expected 0.5mm, got 0.25mm at (122.8, 124.1)→(123, 124.1)
  +3.3V on F.Cu: expected 0.5mm, got 0.25mm at (151.5, 134)→(153.1, 134)
  ... and 13 more in Power_3V3
  +5V on F.Cu: expected 1.5mm, got 0.75mm at (115.4, 124.2)→(114.8, 123.6)
  /Power Management/BQ_REGN on F.Cu: expected 0.75mm, got 0.25mm at (102.13, 118.78)→(102.62, 118.78)
  /Power Management/BQ_REGN on F.Cu: expected 0.75mm, got 0.25mm at (103.4, 118.0)→(103.4, 115.08)
  /Power Management/BQ_REGN on F.Cu: expected 0.75mm, got 0.25mm at (96.09, 119.19)→(96.09, 120.18)
  /Power Management/BQ_REGN on F.Cu: expected 0.75mm, got 0.25mm at (96.07, 119.17)→(96.09, 119.19)
  /Power Management/BQ_REGN on F.Cu: expected 0.75mm, got 0.25mm at (96.07, 118.8)→(96.07, 119.17)
  ... and 6 more in Power_Low
  /Power Management/Protected_VBUS on F.Cu: expected 1.0mm, got 0.75mm at (93.03, 121.34)→(94.2, 120.16)
  /Power Management/Protected_VBUS on F.Cu: expected 1.0mm, got 1.5mm at (103.76, 110.28)→(104.7, 109.34)
  /Power Management/Protected_VBUS on F.Cu: expected 1.0mm, got 1.5mm at (104.7, 109)→(109.9, 103.8)
  /Power Management/Protected_VBUS on F.Cu: expected 1.0mm, got 0.75mm at (99.17, 110.61)→(93.59, 110.61)
  /Power Management/Protected_VBUS on F.Cu: expected 1.0mm, got 0.75mm at (92.4, 119.78)→(93.82, 119.78)
  ... and 69 more in Power_Med
```


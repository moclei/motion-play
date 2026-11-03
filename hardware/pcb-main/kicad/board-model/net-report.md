---
source: "hardware/pcb-main/kicad/motion-play-main.kicad_pcb"
source_sha256: "ff6857d0bf797fc745a59a91123e752c4233ac3682e1ce38f2e270348b26e5b3"
source_ref: "c2acffc"
generator: "tools/pcb-context/net_report.py"
generator_commit: "aa34a874c67e901d93401d7155581a1cd40dcbc8"
generated: "2026-11-03T00:20:39+00:00"
model: "hardware/pcb-main/kicad/board-model/board-model.json"
model_sha256: "a20d1f83c165045be94d60a5a5ca88b88d6571620e245cdb9c91db96dde5ec40"
model_generator_commit: "aa34a874c67e901d93401d7155581a1cd40dcbc8"
---

# Net report — hardware/pcb-main/kicad/motion-play-main.kicad_pcb @ c2acffc

Generated from the board model by `tools/pcb-context/net_report.py`. Check freshness before citing: `python3 tools/lab/check_state.py --fresh <this file>`. Coordinates are KiCad board mm, Y down.

**Measuring methods** (every number below names one):

- *track to track*: target track copper (centreline buffered by width/2) to neighbour track copper, same layer
- *track to copper*: target track copper to all of the neighbour's same-layer copper (tracks, pads, vias, fills)
- *all copper*: tracks + pads + via annular rings (+ the neighbour's same-layer zone fills), same layer, edge to edge
- *plan view*: target copper on one layer to neighbour copper on another layer, edge to edge in plan view; zone fills on other layers are reference planes, not neighbours; separation = dielectric between
- *coupled*: mm of the target's track centrelines within the radius (edge to edge) of the neighbour's same-layer copper
- *radius*: max of the target's and the neighbour's class radius (board config neighbour_radii_mm)
- *reference raw*: track centreline over the zone fills of the adjacent copper layer; fill holes count as no copper
- *reference antipads excl*: as raw, but fill holes that contain a drilled hole (via, PTH, NPTH) count as copper
- *bodies*: track centreline inside a footprint body polygon (courtyard, else fab, else pads), plan view

Neighbour radii (mm): signal 1, high_current 3, high_dvdt 5.

## /I2C_SDA

Class: signal. 6 pads, 3 vias, track 72.90 mm (B 36.98, F 35.92), widths 0.25 mm. Root: U3.37 (config). Longest branch from root: 47.7 mm. Connected: True.

### Route

```
U3.37 TXD0 (ESP32-S3-WROOM-1-N16R8)  — root (config)
├─ F.Cu 3.9 mm w0.25 [1.5 diagonal (143.4,111.6)→(142.3,112.7); 2.4 along y=112.67 (x 142.3→139.9)] → junction (143.41, 111.60)
│  ├─ F.Cu 2.0 mm w0.25 → TPIO43.1 (TestPoint)   ⟨5.9 mm from root, 0 vias; F 5.9⟩
│  └─ F.Cu 5.5 mm w0.25 [2.2 along y=111.60 (x 143.4→145.6); 2.1 diagonal (145.6,111.6)→(147.0,110.1); 1.3 along y=110.14 (x 147.0→148.3)] → U4.23 SDA (TCA9548APWR)   ⟨9.4 mm from root, 0 vias; F 9.4⟩
│     └─ F.Cu 9.9 mm w0.25 [7.1 along x=150.73 (y 102.0→109.0); 1.6 diagonal (150.7,109.0)→(149.6,110.1); 1.3 along y=110.14 (x 149.6→148.3)] → R28.1 (2.2kΩ)   ⟨19.4 mm from root, 0 vias; F 19.4⟩
└─ F.Cu 1.5 mm w0.25 → via V196 (138.40, 112.65)
   └─ B.Cu 26.3 mm w0.25 [9.2 diagonal (138.4,112.7)→(131.9,119.2); 17.1 along y=119.17 (x 131.9→114.8)] → via V198 (114.77, 119.17)
      ├─ B.Cu 10.6 mm w0.25 [6.0 along y=122.19 (x 105.4→111.4); 4.2 diagonal (111.4,122.2)→(114.4,119.2)] → via V197 (105.37, 122.19)
      │  └─ F.Cu 9.2 mm w0.25 [3.2 diagonal (98.1,120.4)→(100.4,122.7); 3.3 along y=122.70 (x 100.4→103.7); 1.2 along y=122.19 (x 104.2→105.4)] → U5.6 SDA (BQ24195RGER)   ⟨47.7 mm from root, 3 vias; B 37.0, F 10.7⟩
      └─ F.Cu 3.8 mm w0.25 [3.8 along y=119.19 (x 110.9→114.8)] → U7.6 SDA (INA219AIDCNR)   ⟨31.7 mm from root, 2 vias; B 26.3, F 5.3⟩
```

| Pad | Part | Side | From root (mm) | Vias | By layer |
|---|---|---|---|---|---|
| U3.37 TXD0 | ESP32-S3-WROOM-1-N16R8 | front | root |  |  |
| TPIO43.1 | TestPoint | front | 5.9 | 0 | F 5.9 |
| U4.23 SDA | TCA9548APWR | front | 9.4 | 0 | F 9.4 |
| R28.1 | 2.2kΩ | front | 19.4 | 0 | F 19.4 |
| U7.6 SDA | INA219AIDCNR | front | 31.7 | 2 | B 26.3, F 5.3 |
| U5.6 SDA | BQ24195RGER | front | 47.7 | 3 | B 37.0, F 10.7 |

### Reference planes

| Track layer | Plane layer (dielectric) | Track mm | Over (raw) | None, raw | None, antipads excl. |
|---|---|---|---|---|---|
| B.Cu | In2.Cu (0.1 mm) | 36.98 | +3.3V 28.94 | **8.04** | **6.19** |
| F.Cu | In1.Cu (0.1 mm) | 35.92 | GND 30.71 | **5.21** | **0.00** |

Unreferenced stretches (antipads excluded): S541 B 6.01 mm (105.38, 122.17)→(111.40, 122.17) over no In2.Cu copper; S542 B 0.16 mm (111.40, 122.17)→(111.51, 122.06) over no In2.Cu copper

| Via | Position | Layers joined | Planes beside it (within 1 mm) | Nearest via of each plane net (centre to centre) |
|---|---|---|---|---|
| V196 | (138.40, 112.65) | F ↔ B | F: In1 GND; B: In2 +3.3V | +3.3V V165 8.36 mm, GND V104 3.97 mm |
| V197 | (105.37, 122.19) | F ↔ B | F: In1 GND; B: In2 +3.3V/+5V | +3.3V V167 2.99 mm, +5V V19 7.13 mm, GND V84 3.15 mm |
| V198 | (114.77, 119.17) | F ↔ B | F: In1 GND; B: In2 +3.3V | +3.3V V164 5.13 mm, GND V105 3.43 mm |

### Passes under / over (plan view)

| Ref | Value | Side | mm by track layer | Body from |
|---|---|---|---|---|
| BT1 | Battery_Cell | back | B 29.74, F 13.04 | courtyard |
| C53 | 100nF | front | B 2.96 | courtyard |

Inside the bodies of its own parts: U3 B 19.66, F 2.55, U4 F 9.88, TPIO43 F 1.57, R28 F 0.73, U7 F 0.62, U5 F 0.40

### Neighbours (unprompted, within the radius, ranked by coupled length)

| Net | Class | Radius | Same layer: all copper (closest) | Track to copper (closest) | Track to track (closest) | Coupled mm by layer | Plan view: gap, layers, separation (closest) | Crossings |
|---|---|---|---|---|---|---|---|---|
| GND | high_current | 3 | 0.20 B (S544↔V110) | 0.20 (S544↔V110) | 23.31 (S540↔S396) | F 27.6, B 24.9 | 0.00 B/F 1.44 mm (S544↔C53.2) | 0 |
| /I2C_SCL | signal | 1 | 0.20 F (V197↔S547) | 0.20 (S533↔S545) | 0.20 (S533↔S545) | F 32.1, B 20.3 | 0.00 F/B 1.44 mm (S523↔S575) | 2 |
| +3.3V | high_current | 3 | 0.20 B (S544↔V183) | 0.20 (S544↔V183) | — | F 22.5, B 13.3 | 0.00 B/F 1.44 mm (S544↔C53.1) | 0 |
| /CHRG_INT | high_dvdt | 5 | 0.20 F (S536↔V16) | 0.20 (S536↔V16) | 0.23 (S536↔S164) | F 9.2, B 10.1 | 0.00 F/B 1.44 mm (S521↔S174) | 1 |
| /Power Management/VSYS_SENSE | high_current | 3 | 0.57 F (V197↔R44.2) | 0.85 (S521↔R44.2) | 0.96 (S521↔S696) | F 6.0 | 0.00 B/F 1.44 mm (S541↔S702) | 1 |
| /Power Management/BOOST_SW | high_current/high_dvdt | 5 | 1.52 F (V197↔S723) | 1.79 (S521↔S723) | 1.79 (S521↔S723) | F 4.9 | 1.52 In1/F 0.10 mm (V197↔S723) | 0 |
| /Power Management/Protected_VBUS | high_current | 3 | 1.67 F (S533↔C21.1) | 1.67 (S533↔C21.1) | 1.69 (S533↔S72) | F 2.8 | — | — |
| unconnected-(U3-IO2-Pad38) | signal | 1 | 0.37 F (U3.37↔U3.38) | 0.68 (S538↔U3.38) | — | F 2.8 | 0.92 In1/F 0.10 mm (V196↔U3.38) | 0 |
| /Power Management/BQ_SW | high_current/high_dvdt | 5 | 3.55 F (U5.6↔U5.20) | 3.80 (S534↔U5.20) | 3.97 (S534↔S621) | F 1.4 | — | — |
| /Power Management/VSYS | high_current | 3 | 1.68 F (U7.6↔U7.1) | 2.09 (S528↔U7.1) | 2.53 (S528↔S659) | F 1.0 | — | — |
| unconnected-(U5-STAT-Pad4) | signal | 1 | 0.70 F (U5.6↔U5.4) | 0.73 (S534↔U5.4) | — | F 1.0 | — | — |
| /Power Management/BQ_PMID | high_current | 3 | 2.85 F (U5.6↔U5.23) | 2.99 (S534↔U5.23) | 3.29 (S534↔S637) | F 0.0 | — | — |
| /ESP32_S3/EN | signal | 1 | — | — | — | — | 0.00 B/F 1.44 mm (S544↔S8) | 1 |
| /LED_DATA | high_dvdt | 5 | — | — | — | — | 0.00 B/F 1.44 mm (S544↔S12) | 1 |
| /Power Management/VBAT | high_current | 3 | — | — | — | — | 0.00 F/B 1.44 mm (S533↔S793) | 1 |
| unconnected-(U3-IO17-Pad10) | signal | 1 | — | — | — | — | 0.54 B/F 1.44 mm (S544↔U3.10) | 0 |
| +5V | high_current | 3 | 0.56 In2 (V197↔Z6) | — | — | — | — | — |
| /Power Management/OTG_BIAS | signal | 1 | 0.78 F (U5.6↔U5.8) | 1.08 (S534↔U5.8) | 1.27 (S534↔S806) | — | — | — |
| unconnected-(U3-IO15-Pad8) | signal | 1 | — | — | — | — | 0.85 B/F 1.44 mm (S544↔U3.8) | 0 |
| /ESP32_S3/USB_DN_MCU | high_dvdt | 5 | — | — | — | — | 4.35 B/F 1.44 mm (S544↔U3.13) | 0 |
| /USB_DN | high_dvdt | 5 | — | — | — | — | 4.39 B/F 1.44 mm (S544↔R52.1) | 0 |

High dv/dt pads nearby: U5.19 (/Power Management/BQ_SW) 3.88 mm all copper; U5.20 (/Power Management/BQ_SW) 3.55 mm all copper

## /I2C_SCL

Class: signal. 6 pads, 5 vias, track 73.30 mm (B 39.64, F 33.66), widths 0.25 mm. Root: U3.36 (config). Longest branch from root: 48.0 mm. Connected: True.

### Route

```
U3.36 RXD0 (ESP32-S3-WROOM-1-N16R8)  — root (config)
├─ F.Cu 2.4 mm w0.25 → junction (142.36, 113.94)
│  ├─ F.Cu 2.3 mm w0.25 → via V201 (144.00, 112.30)
│  │  └─ B.Cu 3.6 mm w0.25 [3.6 diagonal (144.0,112.3)→(146.5,109.7)] → via V203 (146.54, 109.72)
│  │     └─ F.Cu 1.8 mm w0.25 → U4.22 SCL (TCA9548APWR)   ⟨10.2 mm from root, 2 vias; B 3.6, F 6.6⟩
│  │        └─ F.Cu 9.5 mm w0.25 [1.4 diagonal (149.2,102.0)→(150.2,102.9); 6.0 along x=150.18 (y 102.9→109.0); 1.3 along y=109.50 (x 149.6→148.3)] → R29.1 (2.2kΩ)   ⟨19.6 mm from root, 2 vias; B 3.6, F 16.1⟩
│  └─ F.Cu 2.1 mm w0.25 → TPIO44.1 (TestPoint)   ⟨4.6 mm from root, 0 vias; F 4.6⟩
└─ F.Cu 1.5 mm w0.25 → via V202 (138.40, 113.95)
   └─ B.Cu 27.4 mm w0.25 [17.1 along y=120.77 (x 113.8→130.9); 9.7 diagonal (130.9,120.8)→(137.8,114.0)] → via V199 (113.81, 120.77)
      ├─ B.Cu 8.6 mm w0.25 [3.0 diagonal (113.8,120.8)→(111.7,122.9); 5.6 along y=122.90 (x 111.7→106.1)] → via V200 (106.10, 122.91)
      │  └─ F.Cu 10.5 mm w0.25 [3.6 diagonal (97.7,120.6)→(100.2,123.2); 3.6 along y=123.15 (x 100.2→103.9); 2.0 along y=122.91 (x 104.1→106.1)] → U5.5 SCL (BQ24195RGER)   ⟨48.0 mm from root, 3 vias; B 36.0, F 12.1⟩
      └─ F.Cu 3.3 mm w0.25 [1.9 along y=119.85 (x 110.9→112.9); 1.3 diagonal (112.9,119.8)→(113.8,120.8)] → U7.5 SCL (INA219AIDCNR)   ⟨32.2 mm from root, 2 vias; B 27.4, F 4.8⟩
```

| Pad | Part | Side | From root (mm) | Vias | By layer |
|---|---|---|---|---|---|
| U3.36 RXD0 | ESP32-S3-WROOM-1-N16R8 | front | root |  |  |
| TPIO44.1 | TestPoint | front | 4.6 | 0 | F 4.6 |
| U4.22 SCL | TCA9548APWR | front | 10.2 | 2 | B 3.6, F 6.6 |
| R29.1 | 2.2kΩ | front | 19.6 | 2 | B 3.6, F 16.1 |
| U7.5 SCL | INA219AIDCNR | front | 32.2 | 2 | B 27.4, F 4.8 |
| U5.5 SCL | BQ24195RGER | front | 48.0 | 3 | B 36.0, F 12.1 |

### Reference planes

| Track layer | Plane layer (dielectric) | Track mm | Over (raw) | None, raw | None, antipads excl. |
|---|---|---|---|---|---|
| B.Cu | In2.Cu (0.1 mm) | 39.64 | +3.3V 29.85 | **9.79** | **6.78** |
| F.Cu | In1.Cu (0.1 mm) | 33.66 | GND 29.13 | **4.53** | **0.00** |

Unreferenced stretches (antipads excluded): S576 B 2.97 mm (106.10, 122.91)→(109.07, 122.91) over no In2.Cu copper; S570 B 2.60 mm (109.08, 122.90)→(111.69, 122.90) over no In2.Cu copper; S574 B 1.19 mm (111.69, 122.90)→(112.53, 122.06) over no In2.Cu copper

| Via | Position | Layers joined | Planes beside it (within 1 mm) | Nearest via of each plane net (centre to centre) |
|---|---|---|---|---|
| V199 | (113.81, 120.77) | F ↔ B | F: In1 GND; B: In2 +3.3V | +3.3V V169 4.56 mm, GND V105 3.42 mm |
| V200 | (106.10, 122.91) | F ↔ B | F: In1 GND; B: In2 +3.3V/+5V | +3.3V V167 3.94 mm, +5V V19 7.22 mm, GND V84 3.42 mm |
| V201 | (144.00, 112.30) | F ↔ B | F: In1 GND; B: In2 +3.3V | +3.3V V165 4.15 mm, GND V52 6.29 mm |
| V202 | (138.40, 113.95) | F ↔ B | F: In1 GND; B: In2 +3.3V | +3.3V V165 9.08 mm, GND V104 5.26 mm |
| V203 | (146.54, 109.72) | F ↔ B | F: In1 GND; B: In2 +3.3V | +3.3V V165 1.52 mm, GND V150 3.19 mm |

### Passes under / over (plan view)

| Ref | Value | Side | mm by track layer | Body from |
|---|---|---|---|---|
| BT1 | Battery_Cell | back | B 29.96, F 13.86 | courtyard |
| C54 | 100nF | front | B 2.96 | courtyard |

Inside the bodies of its own parts: U3 B 19.78, F 2.55, U4 F 9.04, TPIO44 F 1.50, R29 F 0.93, U7 F 0.62, U5 F 0.40

### Neighbours (unprompted, within the radius, ranked by coupled length)

| Net | Class | Radius | Same layer: all copper (closest) | Track to copper (closest) | Track to track (closest) | Coupled mm by layer | Plan view: gap, layers, separation (closest) | Crossings |
|---|---|---|---|---|---|---|---|---|
| /I2C_SDA | signal | 1 | 0.20 F (S547↔V197) | 0.20 (S547↔V197) | 0.20 (S545↔S533) | F 30.0, B 19.2 | 0.00 F/B 1.44 mm (S549↔S542) | 2 |
| /CHRG_INT | high_dvdt | 5 | 0.30 B (V200↔S175) | 0.58 (S576↔S173) | 0.58 (S576↔S173) | F 13.9, B 27.5 | 0.00 F/B 1.44 mm (S547↔S174) | 1 |
| GND | high_current | 3 | 0.20 F (S567↔V150) | 0.20 (S567↔V150) | 0.28 (S545↔S333) | F 23.5, B 16.7 | 0.00 B/F 1.44 mm (S571↔C54.2) | 0 |
| +3.3V | high_current | 3 | 0.20 B (S571↔V188) | 0.20 (S571↔V188) | — | F 18.3, B 12.3 | 0.00 B/F 1.44 mm (S571↔S427) | 0 |
| /Power Management/VSYS_SENSE | high_current | 3 | 1.22 F (V200↔S702) | 1.49 (S547↔S702) | 1.49 (S547↔S702) | F 6.1 | 0.00 B/F 1.44 mm (S569↔S702) | 1 |
| /LED_DATA | high_dvdt | 5 | 4.16 B (S571↔V1) | 4.16 (S571↔V1) | 4.34 (S571↔S28) | B 5.7 | 0.00 B/F 1.44 mm (S571↔S21) | 1 |
| /Power Management/BOOST_SW | high_current/high_dvdt | 5 | 0.66 F (V200↔S723) | 0.94 (S547↔S723) | 0.94 (S547↔S723) | F 5.7 | 0.66 In1/F 0.10 mm (V200↔S723) | 0 |
| /USB_DN | high_dvdt | 5 | 4.37 B (S571↔V4) | 4.37 (S571↔V4) | 4.45 (S571↔S57) | B 5.0 | 2.79 B/F 1.44 mm (S571↔R52.1) | 0 |
| /Power Management/Protected_VBUS | high_current | 3 | 1.18 F (S545↔C21.1) | 1.18 (S545↔C21.1) | 1.21 (S545↔S72) | F 3.6 | — | — |
| unconnected-(U4-SC7-Pad20) | signal | 1 | 0.89 F (U4.22↔U4.20) | 0.96 (S567↔U4.20) | — | F 2.9 | — | — |
| unconnected-(U3-IO42-Pad35) | signal | 1 | 0.37 F (U3.36↔U3.35) | 0.69 (S568↔U3.35) | — | F 2.8 | 0.93 In1/F 0.10 mm (V202↔U3.35) | 0 |
| /Power Management/BQ_SW | high_current/high_dvdt | 5 | 3.17 F (U5.5↔U5.20) | 3.44 (S554↔U5.20) | 3.62 (S554↔S621) | F 1.8 | — | — |
| unconnected-(U5-STAT-Pad4) | signal | 1 | 0.20 F (U5.5↔U5.4) | 0.23 (S554↔U5.4) | — | F 1.4 | — | — |
| unconnected-(U4-SC4-Pad14) | signal | 1 | 0.96 F (S567↔U4.14) | 0.96 (S567↔U4.14) | — | F 0.9 | — | — |
| unconnected-(U4-SC5-Pad16) | signal | 1 | 0.96 F (S567↔U4.16) | 0.96 (S567↔U4.16) | — | F 0.9 | — | — |
| unconnected-(U4-SC6-Pad18) | signal | 1 | 0.96 F (S567↔U4.18) | 0.96 (S567↔U4.18) | — | F 0.9 | — | — |
| unconnected-(U4-SD4-Pad13) | signal | 1 | 0.96 F (S567↔U4.13) | 0.96 (S567↔U4.13) | — | F 0.9 | — | — |
| unconnected-(U4-SD5-Pad15) | signal | 1 | 0.96 F (S567↔U4.15) | 0.96 (S567↔U4.15) | — | F 0.9 | — | — |
| unconnected-(U4-SD6-Pad17) | signal | 1 | 0.96 F (S567↔U4.17) | 0.96 (S567↔U4.17) | — | F 0.9 | — | — |
| unconnected-(U4-SD7-Pad19) | signal | 1 | 0.96 F (S567↔U4.19) | 0.96 (S567↔U4.19) | — | F 0.9 | — | — |
| /Power Management/BQ_PMID | high_current | 3 | 2.37 F (U5.5↔U5.23) | 2.53 (S554↔U5.23) | 2.83 (S554↔S637) | F 0.8 | — | — |
| /Power Management/VSYS | high_current | 3 | 2.15 F (U7.5↔U7.1) | 2.51 (S560↔U7.1) | 2.90 (S560↔S659) | F 0.7 | — | — |
| /ESP32_S3/EN | signal | 1 | — | — | — | — | 0.00 B/F 1.44 mm (S571↔S8) | 1 |
| /Power Management/VBAT | high_current | 3 | — | — | — | — | 0.00 F/B 1.44 mm (S545↔S793) | 1 |
| unconnected-(U3-IO17-Pad10) | signal | 1 | — | — | — | — | 0.00 B/F 1.44 mm (S571↔U3.10) | 0 |
| unconnected-(U3-IO18-Pad11) | signal | 1 | — | — | — | — | 0.21 B/F 1.44 mm (S571↔U3.11) | 0 |
| +5V | high_current | 3 | 0.30 In2 (V200↔Z6) | — | — | — | — | — |
| /TCA_RESET | signal | 1 | — | — | — | — | 0.58 F/B 1.44 mm (TPIO44.1↔S153) | 0 |
| /ESP32_S3/USB_DN_MCU | high_dvdt | 5 | — | — | — | — | 2.75 B/F 1.44 mm (S571↔U3.13) | 0 |
| /ESP32_S3/USB_DP_MCU | high_dvdt | 5 | — | — | — | — | 4.02 B/F 1.44 mm (S571↔U3.14) | 0 |

High dv/dt pads nearby: U5.19 (/Power Management/BQ_SW) 3.55 mm all copper; U5.20 (/Power Management/BQ_SW) 3.17 mm all copper

## /TCA9548A_Subsystem/CH0_SDA

Class: signal. 2 pads, 0 vias, track 14.62 mm (F 14.62), widths 0.25 mm. Root: U4.4 (heuristic: pad on the largest footprint). Longest branch from root: 14.2 mm. Connected: True.

### Route

```
U4.4 SD0 (TCA9548APWR)  — root (heuristic: pad on the largest footprint)
└─ F.Cu 14.2 mm w0.25 [3.0 diagonal (159.2,120.6)→(156.9,118.7); 7.9 along x=156.89 (y 118.7→110.8); 2.8 diagonal (156.9,110.8)→(154.9,108.8)] → J4.3 Pin_3 (Conn_01x04)   ⟨14.2 mm from root, 0 vias; F 14.2⟩
```

| Pad | Part | Side | From root (mm) | Vias | By layer |
|---|---|---|---|---|---|
| U4.4 SD0 | TCA9548APWR | front | root |  |  |
| J4.3 Pin_3 | Conn_01x04 | front | 14.2 | 0 | F 14.2 |

### Reference planes

| Track layer | Plane layer (dielectric) | Track mm | Over (raw) | None, raw | None, antipads excl. |
|---|---|---|---|---|---|
| F.Cu | In1.Cu (0.1 mm) | 14.62 | GND 14.62 | **0.00** | **0.00** |

### Passes under / over (plan view)

| Ref | Value | Side | mm by track layer | Body from |
|---|---|---|---|---|
| BT1 | Battery_Cell | back | F 3.43 | courtyard |

Inside the bodies of its own parts: J4 F 1.62, U4 F 1.12

### Neighbours (unprompted, within the radius, ranked by coupled length)

| Net | Class | Radius | Same layer: all copper (closest) | Track to copper (closest) | Track to track (closest) | Coupled mm by layer | Plan view: gap, layers, separation (closest) | Crossings |
|---|---|---|---|---|---|---|---|---|
| /TCA9548A_Subsystem/CH0_SCL | signal | 1 | 0.20 F (S602↔S589) | 0.20 (S602↔S589) | 0.20 (S602↔S589) | F 14.6 | — | — |
| GND | high_current | 3 | 0.20 F (S606↔V154) | 0.20 (S606↔V154) | 0.38 (S606↔S337) | F 14.6 | 0.20 F/In1 0.10 mm (S606↔V154) | 0 |
| +3.3V | high_current | 3 | 1.40 F (J4.3↔J4.1) | 1.43 (S602↔J5.1) | 1.62 (S603↔S423) | F 11.2 | 1.72 F/In1 0.10 mm (J4.3↔V170) | 0 |
| /TCA9548A_Subsystem/CH1_SDA | signal | 1 | 0.79 F (S602↔S595) | 0.79 (S602↔S595) | 0.79 (S602↔S595) | F 5.5 | — | — |
| Net-(C7-Pad2) | high_current | 3 | 2.32 F (S602↔S477) | 2.32 (S602↔S477) | 2.32 (S602↔S477) | F 4.4 | — | — |
| /TCA_RESET | signal | 1 | 0.24 F (U4.4↔U4.3) | 0.25 (S606↔U4.3) | 0.40 (S605↔S147) | F 2.3 | 0.69 F/In1 0.10 mm (U4.4↔V12) | 0 |

## /TCA9548A_Subsystem/CH0_SCL

Class: signal. 2 pads, 0 vias, track 14.90 mm (F 14.90), widths 0.25 mm. Root: U4.5 (heuristic: pad on the largest footprint). Longest branch from root: 14.1 mm. Connected: True.

### Route

```
U4.5 SC0 (TCA9548APWR)  — root (heuristic: pad on the largest footprint)
└─ F.Cu 0.8 mm w0.25 → junction (154.88, 108.19)
   └─ F.Cu 13.3 mm w0.25 [2.6 diagonal (159.2,119.6)→(157.3,117.7); 7.2 along x=157.34 (y 117.7→110.5); 3.3 diagonal (157.3,110.5)→(155.0,108.2)] → J4.4 Pin_4 (Conn_01x04)   ⟨14.1 mm from root, 0 vias; F 14.1⟩
  (off-tree) junction (154.88, 108.19) ↔ U4.5 SC0 (TCA9548APWR): F.Cu 0.8 mm w0.25
```

| Pad | Part | Side | From root (mm) | Vias | By layer |
|---|---|---|---|---|---|
| U4.5 SC0 | TCA9548APWR | front | root |  |  |
| J4.4 Pin_4 | Conn_01x04 | front | 14.1 | 0 | F 14.1 |

### Reference planes

| Track layer | Plane layer (dielectric) | Track mm | Over (raw) | None, raw | None, antipads excl. |
|---|---|---|---|---|---|
| F.Cu | In1.Cu (0.1 mm) | 14.90 | GND 14.90 | **0.00** | **0.00** |

### Passes under / over (plan view)

| Ref | Value | Side | mm by track layer | Body from |
|---|---|---|---|---|
| BT1 | Battery_Cell | back | F 1.76 | courtyard |

Inside the bodies of its own parts: U4 F 1.89, J4 F 1.13

### Neighbours (unprompted, within the radius, ranked by coupled length)

| Net | Class | Radius | Same layer: all copper (closest) | Track to copper (closest) | Track to track (closest) | Coupled mm by layer | Plan view: gap, layers, separation (closest) | Crossings |
|---|---|---|---|---|---|---|---|---|
| /TCA9548A_Subsystem/CH0_SDA | signal | 1 | 0.20 F (S589↔S602) | 0.20 (S589↔S602) | 0.20 (S589↔S602) | F 14.9 | — | — |
| GND | high_current | 3 | 0.52 F (S589↔V77) | 0.52 (S589↔V77) | 0.70 (S589↔S361) | F 14.9 | 0.52 F/In1 0.10 mm (S589↔V77) | 0 |
| /TCA9548A_Subsystem/CH1_SDA | signal | 1 | 0.24 F (S587↔S595) | 0.24 (S587↔S595) | 0.24 (S587↔S595) | F 8.0 | — | — |
| +3.3V | high_current | 3 | 0.97 F (S589↔J5.1) | 0.97 (S589↔J5.1) | 1.50 (S589↔S426) | F 7.5 | 2.27 F/In1 0.10 mm (S589↔V171) | 0 |
| /TCA9548A_Subsystem/CH1_SCL | signal | 1 | 0.69 F (S587↔S585) | 0.69 (S587↔S585) | 0.69 (S587↔S585) | F 6.3 | — | — |
| /TCA_RESET | signal | 1 | 0.80 F (S587↔U4.3) | 0.80 (S587↔U4.3) | 1.05 (S588↔S147) | F 3.1 | — | — |
| Net-(C7-Pad2) | high_current | 3 | 2.77 F (S589↔S477) | 2.77 (S589↔S477) | 2.77 (S589↔S477) | F 2.7 | — | — |

## /TCA9548A_Subsystem/CH1_SDA

Class: signal. 2 pads, 0 vias, track 8.36 mm (F 8.36), widths 0.25 mm. Root: U4.6 (heuristic: pad on the largest footprint). Longest branch from root: 7.6 mm. Connected: True.

### Route

```
U4.6 SD1 (TCA9548APWR)  — root (heuristic: pad on the largest footprint)
└─ F.Cu 7.6 mm w0.25 [1.1 diagonal (159.2,112.7)→(158.1,112.4); 1.8 along x=158.12 (y 112.4→110.6); 4.3 diagonal (158.1,110.6)→(155.1,107.5); 1.0 along y=107.55 (x 155.1→154.1)] → J5.3 Pin_3 (Conn_01x04)   ⟨7.6 mm from root, 0 vias; F 7.6⟩
```

| Pad | Part | Side | From root (mm) | Vias | By layer |
|---|---|---|---|---|---|
| U4.6 SD1 | TCA9548APWR | front | root |  |  |
| J5.3 Pin_3 | Conn_01x04 | front | 7.6 | 0 | F 7.6 |

### Reference planes

| Track layer | Plane layer (dielectric) | Track mm | Over (raw) | None, raw | None, antipads excl. |
|---|---|---|---|---|---|
| F.Cu | In1.Cu (0.1 mm) | 8.36 | GND 8.36 | **0.00** | **0.00** |

### Passes under / over (plan view)

None (non-member footprints).

Inside the bodies of its own parts: J5 F 2.71, U4 F 1.05

### Neighbours (unprompted, within the radius, ranked by coupled length)

| Net | Class | Radius | Same layer: all copper (closest) | Track to copper (closest) | Track to track (closest) | Coupled mm by layer | Plan view: gap, layers, separation (closest) | Crossings |
|---|---|---|---|---|---|---|---|---|
| /TCA9548A_Subsystem/CH1_SCL | signal | 1 | 0.20 F (S591↔S585) | 0.20 (S591↔S585) | 0.20 (S591↔S585) | F 8.4 | — | — |
| GND | high_current | 3 | 0.40 F (J5.3↔J5.2) | 0.58 (S593↔J5.2) | 0.75 (S593↔S361) | F 8.4 | 0.45 F/In1 0.10 mm (J5.3↔V77) | 0 |
| /TCA9548A_Subsystem/CH0_SCL | signal | 1 | 0.24 F (S595↔S587) | 0.24 (S595↔S587) | 0.24 (S595↔S587) | F 7.7 | — | — |
| /TCA9548A_Subsystem/CH0_SDA | signal | 1 | 0.79 F (S595↔S602) | 0.79 (S595↔S602) | 0.79 (S595↔S602) | F 7.1 | — | — |
| +3.3V | high_current | 3 | 1.40 F (J5.3↔J5.1) | 1.58 (S593↔J5.1) | 1.62 (S593↔S426) | F 5.2 | 1.84 F/In1 0.10 mm (J5.3↔V185) | 0 |
| /TCA9548A_Subsystem/CH2_SDA | signal | 1 | 0.89 F (U4.6↔U4.8) | 0.97 (S591↔U4.8) | 1.05 (S591↔S599) | F 1.0 | — | — |

## /TCA9548A_Subsystem/CH1_SCL

Class: signal. 2 pads, 0 vias, track 7.55 mm (F 7.55), widths 0.25 mm. Root: U4.7 (heuristic: pad on the largest footprint). Longest branch from root: 7.5 mm. Connected: True.

### Route

```
U4.7 SC1 (TCA9548APWR)  — root (heuristic: pad on the largest footprint)
└─ F.Cu 7.5 mm w0.25 [5.9 diagonal (159.2,111.1)→(155.1,106.9)] → J5.4 Pin_4 (Conn_01x04)   ⟨7.5 mm from root, 0 vias; F 7.5⟩
```

| Pad | Part | Side | From root (mm) | Vias | By layer |
|---|---|---|---|---|---|
| U4.7 SC1 | TCA9548APWR | front | root |  |  |
| J5.4 Pin_4 | Conn_01x04 | front | 7.5 | 0 | F 7.5 |

### Reference planes

| Track layer | Plane layer (dielectric) | Track mm | Over (raw) | None, raw | None, antipads excl. |
|---|---|---|---|---|---|
| F.Cu | In1.Cu (0.1 mm) | 7.55 | GND 7.55 | **0.00** | **0.00** |

### Passes under / over (plan view)

None (non-member footprints).

Inside the bodies of its own parts: U4 F 1.05, J5 F 0.92

### Neighbours (unprompted, within the radius, ranked by coupled length)

| Net | Class | Radius | Same layer: all copper (closest) | Track to copper (closest) | Track to track (closest) | Coupled mm by layer | Plan view: gap, layers, separation (closest) | Crossings |
|---|---|---|---|---|---|---|---|---|
| /TCA9548A_Subsystem/CH1_SDA | signal | 1 | 0.20 F (S585↔S591) | 0.20 (S585↔S591) | 0.20 (S585↔S591) | F 7.5 | — | — |
| GND | high_current | 3 | 1.40 F (J5.4↔J5.2) | 1.58 (S584↔J5.2) | 1.75 (S584↔S361) | F 7.5 | 1.43 F/In1 0.10 mm (J5.4↔V77) | 0 |
| /TCA9548A_Subsystem/CH0_SCL | signal | 1 | 0.69 F (S585↔S587) | 0.69 (S585↔S587) | 0.69 (S585↔S587) | F 6.0 | — | — |
| +3.3V | high_current | 3 | 2.19 F (S585↔J6.1) | 2.19 (S585↔J6.1) | 2.62 (S584↔S426) | F 4.7 | 2.82 F/In1 0.10 mm (J5.4↔V185) | 0 |
| /TCA9548A_Subsystem/CH2_SDA | signal | 1 | 0.24 F (U4.7↔U4.8) | 0.32 (S583↔U4.8) | 0.40 (S583↔S599) | F 1.8 | — | — |
| /TCA9548A_Subsystem/CH2_SCL | signal | 1 | 0.89 F (U4.7↔U4.9) | 0.97 (S583↔U4.9) | 1.05 (S583↔S597) | F 1.0 | — | — |

## /TCA9548A_Subsystem/CH2_SDA

Class: signal. 2 pads, 0 vias, track 5.75 mm (F 5.75), widths 0.25 mm. Root: U4.8 (heuristic: pad on the largest footprint). Longest branch from root: 5.3 mm. Connected: True.

### Route

```
U4.8 SD2 (TCA9548APWR)  — root (heuristic: pad on the largest footprint)
└─ F.Cu 5.3 mm w0.25 [2.4 diagonal (159.2,104.8)→(157.3,106.2); 3.2 along y=106.25 (x 157.3→154.1)] → J6.3 Pin_3 (Conn_01x04)   ⟨5.3 mm from root, 0 vias; F 5.3⟩
```

| Pad | Part | Side | From root (mm) | Vias | By layer |
|---|---|---|---|---|---|
| U4.8 SD2 | TCA9548APWR | front | root |  |  |
| J6.3 Pin_3 | Conn_01x04 | front | 5.3 | 0 | F 5.3 |

### Reference planes

| Track layer | Plane layer (dielectric) | Track mm | Over (raw) | None, raw | None, antipads excl. |
|---|---|---|---|---|---|
| F.Cu | In1.Cu (0.1 mm) | 5.75 | GND 5.75 | **0.00** | **0.00** |

### Passes under / over (plan view)

None (non-member footprints).

Inside the bodies of its own parts: J6 F 1.62, U4 F 1.03

### Neighbours (unprompted, within the radius, ranked by coupled length)

| Net | Class | Radius | Same layer: all copper (closest) | Track to copper (closest) | Track to track (closest) | Coupled mm by layer | Plan view: gap, layers, separation (closest) | Crossings |
|---|---|---|---|---|---|---|---|---|
| /TCA9548A_Subsystem/CH2_SCL | signal | 1 | 0.20 F (J6.3↔S598) | 0.32 (S599↔U4.9) | 0.40 (S599↔S597) | F 5.8 | — | — |
| GND | high_current | 3 | 0.20 F (S600↔J6.2) | 0.20 (S600↔J6.2) | 0.44 (S600↔S324) | F 5.8 | 0.27 F/In1 0.10 mm (S600↔V130) | 0 |
| +3.3V | high_current | 3 | 0.91 F (S600↔J6.1) | 0.91 (S600↔J6.1) | 1.36 (S600↔S473) | F 4.5 | 1.57 F/In1 0.10 mm (J6.3↔V176) | 0 |
| /TCA9548A_Subsystem/CH1_SCL | signal | 1 | 0.24 F (U4.8↔U4.7) | 0.32 (S599↔U4.7) | 0.40 (S599↔S583) | F 2.1 | — | — |
| /TCA9548A_Subsystem/CH1_SDA | signal | 1 | 0.89 F (U4.8↔U4.6) | 0.97 (S599↔U4.6) | 1.05 (S599↔S591) | F 1.0 | — | — |
| unconnected-(U4-SD3-Pad10) | signal | 1 | 0.89 F (U4.8↔U4.10) | 0.97 (S599↔U4.10) | — | F 1.0 | — | — |

## /TCA9548A_Subsystem/CH2_SCL

Class: signal. 2 pads, 0 vias, track 5.89 mm (F 5.89), widths 0.25 mm. Root: U4.9 (heuristic: pad on the largest footprint). Longest branch from root: 5.4 mm. Connected: True.

### Route

```
U4.9 SC2 (TCA9548APWR)  — root (heuristic: pad on the largest footprint)
└─ F.Cu 5.4 mm w0.25 [2.9 diagonal (159.2,103.8)→(156.9,105.6); 2.9 along y=105.59 (x 156.9→154.1)] → J6.4 Pin_4 (Conn_01x04)   ⟨5.4 mm from root, 0 vias; F 5.4⟩
```

| Pad | Part | Side | From root (mm) | Vias | By layer |
|---|---|---|---|---|---|
| U4.9 SC2 | TCA9548APWR | front | root |  |  |
| J6.4 Pin_4 | Conn_01x04 | front | 5.4 | 0 | F 5.4 |

### Reference planes

| Track layer | Plane layer (dielectric) | Track mm | Over (raw) | None, raw | None, antipads excl. |
|---|---|---|---|---|---|
| F.Cu | In1.Cu (0.1 mm) | 5.89 | GND 5.89 | **0.00** | **0.00** |

### Passes under / over (plan view)

None (non-member footprints).

Inside the bodies of its own parts: J6 F 1.62, U4 F 1.03

### Neighbours (unprompted, within the radius, ranked by coupled length)

| Net | Class | Radius | Same layer: all copper (closest) | Track to copper (closest) | Track to track (closest) | Coupled mm by layer | Plan view: gap, layers, separation (closest) | Crossings |
|---|---|---|---|---|---|---|---|---|
| /TCA9548A_Subsystem/CH2_SDA | signal | 1 | 0.20 F (S598↔J6.3) | 0.20 (S598↔J6.3) | 0.40 (S597↔S599) | F 5.9 | — | — |
| GND | high_current | 3 | 0.91 F (S598↔J6.2) | 0.91 (S598↔J6.2) | 1.15 (S598↔S324) | F 5.9 | 0.97 F/In1 0.10 mm (S598↔V130) | 0 |
| +3.3V | high_current | 3 | 1.62 F (S598↔J6.1) | 1.62 (S598↔J6.1) | 2.07 (S598↔S473) | F 4.5 | 2.53 F/In1 0.10 mm (J6.4↔V176) | 0 |
| unconnected-(U4-SD3-Pad10) | signal | 1 | 0.24 F (U4.9↔U4.10) | 0.32 (S597↔U4.10) | — | F 1.8 | — | — |
| /TCA9548A_Subsystem/CH1_SCL | signal | 1 | 0.89 F (U4.9↔U4.7) | 0.97 (S597↔U4.7) | 1.05 (S597↔S583) | F 1.0 | — | — |
| unconnected-(U4-SC3-Pad11) | signal | 1 | 0.89 F (U4.9↔U4.11) | 0.97 (S597↔U4.11) | — | F 1.0 | — | — |

## All nets

| Net | Class | Pads | Track mm | By layer | Widths | Vias | Zones | Connected | Stubs |
|---|---|---|---|---|---|---|---|---|---|
| +3.3V | high_current | 25 | 39.19 | F 39.2 | 0.25/0.5/0.75 | 31 | Z3,Z7 | yes | 0 |
| +5V | high_current | 11 | 15.96 | F 16.0 | 0.5/1.5 | 10 | Z1,Z6 | yes | 0 |
| /CHRG_INT | high_dvdt | 4 | 42.75 | B 31.8, F 11.0 | 0.25 | 3 | — | yes | 0 |
| /ESP32_S3/EN | signal | 4 | 24.21 | F 24.2 | 0.2/0.25 | 0 | — | yes | 0 |
| /ESP32_S3/GPIO0_BOOT | signal | 3 | 6.26 | F 6.3 | 0.25 | 0 | — | yes | 0 |
| /ESP32_S3/INT1 | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| /ESP32_S3/INT2 | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| /ESP32_S3/INT3 | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| /ESP32_S3/USB_DN_MCU | high_dvdt | 2 | 1.82 | F 1.8 | 0.3 | 0 | — | yes | 0 |
| /ESP32_S3/USB_DP_MCU | high_dvdt | 2 | 2.18 | F 2.2 | 0.3 | 0 | — | yes | 0 |
| /I2C_SCL | signal | 6 | 73.30 | B 39.6, F 33.7 | 0.25 | 5 | — | yes | 0 |
| /I2C_SDA | signal | 6 | 72.90 | B 37.0, F 35.9 | 0.25 | 3 | — | yes | 0 |
| /LED Controller/+5V_TO_LEDS | high_current | 4 | 14.65 | F 14.7 | 1 | 0 | — | yes | 0 |
| /LED Controller/DATA_TO_LEDS | high_dvdt | 2 | 11.83 | B 7.8, F 4.1 | 0.25 | 2 | — | yes | 0 |
| /LED_DATA | high_dvdt | 4 | 42.07 | B 18.3, F 23.7 | 0.25 | 2 | — | yes | 0 |
| /Power Management/BAT_RAW | high_current | 3 | 14.71 | B 8.3, F 6.4 | 0.75/2 | 1 | — | yes | 0 |
| /Power Management/BOOST_BOOT | signal | 2 | 3.57 | F 3.6 | 0.25 | 0 | — | yes | 0 |
| /Power Management/BOOST_COMP | signal | 3 | 5.89 | F 5.9 | 0.2 | 0 | — | yes | 0 |
| /Power Management/BOOST_EN | high_current | 3 | 20.89 | F 20.9 | 0.3/0.5 | 0 | — | yes | 0 |
| /Power Management/BOOST_FB | signal | 3 | 5.69 | F 5.7 | 0.2 | 0 | — | yes | 0 |
| /Power Management/BOOST_FSW | signal | 2 | 7.55 | B 6.3, F 1.3 | 0.15/0.2 | 2 | — | yes | 0 |
| /Power Management/BOOST_ILIM | signal | 2 | 4.38 | F 4.4 | 0.25 | 0 | — | yes | 0 |
| /Power Management/BOOST_SS | signal | 2 | 5.07 | F 5.1 | 0.25 | 0 | — | yes | 0 |
| /Power Management/BOOST_SW | high_current/high_dvdt | 7 | 6.53 | F 6.5 | 1.5 | 0 | Z0 | yes | 0 |
| /Power Management/BOOST_VCC | signal | 2 | 3.76 | F 3.8 | 0.25 | 0 | — | yes | 0 |
| /Power Management/BQ_BTST | signal | 2 | 4.71 | B 3.0, F 1.7 | 0.25 | 2 | — | yes | 0 |
| /Power Management/BQ_ILIM | signal | 2 | 1.92 | F 1.9 | 0.25 | 0 | — | yes | 0 |
| /Power Management/BQ_PMID | high_current | 3 | 15.98 | B 9.6, F 6.4 | 0.25 | 2 | — | yes | 0 |
| /Power Management/BQ_REGN | signal | 3 | 14.69 | B 6.9, F 7.8 | 0.25 | 2 | — | yes | 0 |
| /Power Management/BQ_SW | high_current/high_dvdt | 4 | 5.27 | F 5.3 | 0.75 | 0 | — | yes | 0 |
| /Power Management/BQ_TS | signal | 5 | 26.75 | B 11.4, F 15.4 | 0.25 | 2 | — | yes | 0 |
| /Power Management/CC1 | signal | 2 | 5.68 | F 5.7 | 0.2/0.25 | 0 | — | yes | 0 |
| /Power Management/CC2 | signal | 2 | 6.34 | F 6.3 | 0.15/0.2/0.25 | 0 | — | yes | 0 |
| /Power Management/COMP_MID | signal | 2 | 1.55 | F 1.5 | 0.2 | 0 | — | yes | 0 |
| /Power Management/OTG_BIAS | signal | 2 | 2.38 | F 2.4 | 0.25 | 0 | — | yes | 0 |
| /Power Management/PMOS_GATE | signal | 3 | 7.13 | F 7.1 | 0.2/0.25 | 0 | — | yes | 0 |
| /Power Management/Protected_VBUS | high_current | 8 | 57.70 | B 9.6, F 48.1 | 0.25/0.75/1/1.5 | 2 | — | yes | 0 |
| /Power Management/VBAT | high_current | 5 | 24.56 | B 17.3, F 7.2 | 0.75 | 3 | — | yes | 0 |
| /Power Management/VBUS_RAW | high_current | 3 | 14.28 | F 14.3 | 0.3/0.5/1 | 0 | — | yes | 0 |
| /Power Management/VSYS | high_current | 9 | 52.87 | B 3.9, F 48.9 | 0.25/0.5/1 | 4 | — | yes | 0 |
| /Power Management/VSYS_SENSE | high_current | 7 | 35.60 | B 4.7, F 30.9 | 0.2/0.25/0.5/0.75/1 | 2 | — | yes | 0 |
| /TCA9548A_Subsystem/CH0_SCL | signal | 2 | 14.90 | F 14.9 | 0.25 | 0 | — | yes | 0 |
| /TCA9548A_Subsystem/CH0_SDA | signal | 2 | 14.62 | F 14.6 | 0.25 | 0 | — | yes | 0 |
| /TCA9548A_Subsystem/CH1_SCL | signal | 2 | 7.55 | F 7.5 | 0.25 | 0 | — | yes | 0 |
| /TCA9548A_Subsystem/CH1_SDA | signal | 2 | 8.36 | F 8.4 | 0.25 | 0 | — | yes | 0 |
| /TCA9548A_Subsystem/CH2_SCL | signal | 2 | 5.89 | F 5.9 | 0.25 | 0 | — | yes | 0 |
| /TCA9548A_Subsystem/CH2_SDA | signal | 2 | 5.75 | F 5.7 | 0.25 | 0 | — | yes | 0 |
| /TCA_RESET | signal | 4 | 40.82 | B 22.5, F 18.3 | 0.25 | 3 | — | yes | 0 |
| /USB_DN | high_dvdt | 5 | 69.62 | B 51.6, F 18.0 | 0.2/0.25/0.3 | 5 | — | yes | 0 |
| /USB_DP | high_dvdt | 5 | 73.00 | B 44.0, F 29.0 | 0.2/0.25/0.3 | 2 | — | yes | 0 |
| GND | high_current | 94 | 134.04 | B 19.3, F 114.7 | 0.2/0.25/0.5/0.75/1/1.5 | 136 | Z2,Z5 | yes | 0 |
| Net-(C7-Pad2) | high_current | 3 | 7.87 | F 7.9 | 1 | 0 | — | yes | 0 |
| Net-(D1-A) | signal | 2 | 1.74 | F 1.7 | 0.25 | 0 | — | yes | 0 |
| unconnected-(D5-DOUT-Pad3) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(IC1-2A-Pad5) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(IC1-2Y-Pad6) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(IC1-2~{OE}-Pad4) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(IC1-3A-Pad9) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(IC1-3Y-Pad8) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(IC1-3~{OE}-Pad10) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(IC1-4A-Pad12) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(IC1-4Y-Pad11) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(IC1-4~{OE}-Pad13) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(J7-SBU1-PadA8) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(J7-SBU2-PadB8) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO1-Pad39) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO14-Pad22) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO15-Pad8) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO17-Pad10) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO18-Pad11) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO2-Pad38) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO3-Pad15) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO35-Pad28) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO36-Pad29) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO37-Pad30) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO38-Pad31) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO39-Pad32) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO4-Pad4) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO40-Pad33) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO41-Pad34) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO42-Pad35) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO45-Pad26) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO46-Pad16) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO47-Pad24) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO48-Pad25) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO5-Pad5) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO6-Pad6) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO7-Pad7) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO8-Pad12) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U3-IO9-Pad17) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U4-SC3-Pad11) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U4-SC4-Pad14) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U4-SC5-Pad16) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U4-SC6-Pad18) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U4-SC7-Pad20) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U4-SD3-Pad10) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U4-SD4-Pad13) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U4-SD5-Pad15) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U4-SD6-Pad17) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U4-SD7-Pad19) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U5-STAT-Pad4) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |
| unconnected-(U6-MODE-Pad13) | signal | 1 | 0.00 | — | — | 0 | — | — | 0 |

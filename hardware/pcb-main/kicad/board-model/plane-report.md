---
source: "hardware/pcb-main/kicad/motion-play-main.kicad_pcb"
source_sha256: "ff6857d0bf797fc745a59a91123e752c4233ac3682e1ce38f2e270348b26e5b3"
source_ref: "c2acffc"
generator: "tools/pcb-context/plane_report.py"
generator_commit: "aa34a874c67e901d93401d7155581a1cd40dcbc8"
generated: "2026-11-03T00:20:49+00:00"
model: "hardware/pcb-main/kicad/board-model/board-model.json"
model_sha256: "a20d1f83c165045be94d60a5a5ca88b88d6571620e245cdb9c91db96dde5ec40"
model_generator_commit: "aa34a874c67e901d93401d7155581a1cd40dcbc8"
---

# Plane report — hardware/pcb-main/kicad/motion-play-main.kicad_pcb @ c2acffc

Generated from the board model by `tools/pcb-context/plane_report.py`. Check freshness before citing: `python3 tools/lab/check_state.py --fresh <this file>`. Coordinates are KiCad board mm, Y down.

**Measuring methods:**

- *ownership*: area of the union of a net's copper on the layer (zone fills; and all copper = fills + tracks + pads + via annular rings)
- *split*: boundary of fill A lying within split_gap_max_mm of fill B (length), the min edge-to-edge gap, and tracks on an adjacent copper layer whose centreline crosses the gap between them
- *void width*: mean width = 2 × area / perimeter (a long thin void along a split reads as its width)
- *void*: outline shrunk by edge_margin_mm, less all copper on the layer; pieces >= min_void_mm2. A piece touching fills of two or more nets is a split gap, otherwise a void. Holes in a fill that contain a drilled hole are antipads and are counted separately
- *unreferenced raw*: track centreline over no fill on the adjacent copper layer (stackup); fill holes count as no copper
- *unreferenced antipads excl*: as raw, but fill holes that contain a drilled hole (via, PTH, NPTH) count as copper
- *stitching*: GND vias (centres) per grid cell; cells at least half inside the outline; nearest GND via to a signal via is centre to centre

Parameters: plane_fill_share 0.25, split_gap_max_mm 1.5, edge_margin_mm 1.0, min_void_mm2 1.0, antipad_cluster_mm2 3.0, grid_mm 10.0, ground_net GND. Outline 3395.7 mm².  Stackup: F↔In1 0.1 mm; In1↔In2 1.24 mm; In2↔B 0.1 mm.

## F.Cu

Fills cover 4.8 % of the outline. Adjacent: In1.Cu (0.1 mm).

| Zone | Net | Priority | Fill mm² | Holes | Bbox |
|---|---|---|---|---|---|
| Z0 | /Power Management/BOOST_SW | 4 | 5.3 | 0 | [104.31, 129.57, 107.47, 131.27] |
| Z1 | +5V | 5 | 10.5 | 0 | [98.49, 126.37, 101.56, 131.87] |
| Z2 | GND | 3 | 94.4 | 0 | [146.07, 116.95, 156.25, 128.76] |
| Z3 | +3.3V | 6 | 54.1 | 0 | [109.96, 104.35, 117.56, 113.85] |
| Z4 | keepout | 0 | 0.0 | 0 | — |

Copper ownership (top 8 of 102 nets): GND 244.0 mm² (fill 94.4, 7.2 %); +3.3V 83.6 mm² (fill 54.1, 2.5 %); /Power Management/VSYS 56.5 mm² (fill 0.0, 1.7 %); /Power Management/Protected_VBUS 47.8 mm² (fill 0.0, 1.4 %); +5V 39.2 mm² (fill 10.5, 1.2 %); /Power Management/VSYS_SENSE 29.7 mm² (fill 0.0, 0.9 %); /LED Controller/+5V_TO_LEDS 19.3 mm² (fill 0.0, 0.6 %); /Power Management/BOOST_SW 17.8 mm² (fill 5.3, 0.5 %)

## In1.Cu (plane layer)

Fills cover 88.1 % of the outline. Adjacent: F.Cu (0.1 mm), In2.Cu (1.24 mm).

| Zone | Net | Priority | Fill mm² | Holes | Bbox |
|---|---|---|---|---|---|
| Z4 | keepout | 0 | 0.0 | 0 | — |
| Z5 | GND | 0 | 2991.1 | 81 | [76.05, 101.3, 163.6, 139.2] |

Copper ownership (top 8 of 21 nets): GND 2992.0 mm² (fill 2991.1, 88.1 %); +3.3V 8.8 mm² (fill 0.0, 0.3 %); +5V 3.3 mm² (fill 0.0, 0.1 %); /Power Management/VSYS 2.0 mm² (fill 0.0, 0.1 %); /USB_DN 1.8 mm² (fill 0.0, 0.1 %); /I2C_SCL 1.6 mm² (fill 0.0, 0.1 %); /CHRG_INT 1.1 mm² (fill 0.0, 0.0 %); /I2C_SDA 1.1 mm² (fill 0.0, 0.0 %)

Antipads: 70 holes with a drill, 195.8 mm² in all. Merged clusters ≥ 3 mm²: GND 12.8 mm² (5 drills) [77.23, 121.15, 83.72, 125.47]; GND 10.3 mm² (5 drills) [119.7, 114.0, 121.4, 122.2]; GND 9.9 mm² (5 drills) [96.75, 112.4, 101.38, 116.38]; GND 7.3 mm² (4 drills) [112.46, 104.02, 115.36, 107.7]; GND 6.6 mm² (1 drills) [82.05, 135.15, 84.95, 138.05]; GND 6.1 mm² (3 drills) [99.47, 126.37, 101.07, 131.17]; GND 5.6 mm² (2 drills) [77.23, 112.66, 79.44, 116.11]; GND 5.0 mm² (2 drills) [79.72, 118.0, 81.52, 121.43]; GND 4.9 mm² (3 drills) [91.95, 116.41, 94.78, 119.4]; GND 4.6 mm² (2 drills) [81.31, 114.51, 83.72, 117.37]; GND 4.3 mm² (2 drills) [104.47, 121.29, 107.0, 123.81]; GND 4.1 mm² (2 drills) [111.11, 110.2, 112.91, 113.6]; GND 4.0 mm² (2 drills) [144.86, 107.69, 147.34, 110.53]; GND 3.9 mm² (2 drills) [137.6, 111.85, 139.2, 114.75]; GND 3.7 mm² (2 drills) [109.69, 103.93, 111.56, 106.65]; GND 3.6 mm² (2 drills) [101.75, 120.4, 104.0, 122.88]; GND 3.5 mm² (2 drills) [159.19, 121.87, 161.59, 124.03]; GND 3.4 mm² (2 drills) [147.86, 110.89, 150.36, 112.5]; GND 3.2 mm² (2 drills) [84.57, 129.04, 86.91, 131.33].

| Kind | mm² | Mean width mm | At | Bbox | Fills touched | In keepout | Nets crossing on adjacent layers |
|---|---|---|---|---|---|---|---|
| void | 109.8 | 4.05 | (130.8, 103.7) | [119.6, 102.0, 140.5, 107.6] | GND | yes | +3.3V |
| void | 2.1 | 0.49 | (112.2, 102.9) | [110.76, 102.0, 112.46, 103.85] | GND |  | +5V |

## In2.Cu (plane layer)

Fills cover 81.3 % of the outline. Adjacent: In1.Cu (1.24 mm), B.Cu (0.1 mm).

| Zone | Net | Priority | Fill mm² | Holes | Bbox |
|---|---|---|---|---|---|
| Z4 | keepout | 0 | 0.0 | 0 | — |
| Z6 | +5V | 7 | 1582.2 | 70 | [76.0, 101.3, 163.6, 139.2] |
| Z7 | +3.3V | 8 | 1177.9 | 36 | [102.1, 101.3, 163.6, 130.5] |

Copper ownership (top 8 of 21 nets): +5V 1582.2 mm² (fill 1582.2, 46.6 %); +3.3V 1177.9 mm² (fill 1177.9, 34.7 %); GND 43.0 mm² (fill 0.0, 1.3 %); /Power Management/VSYS 2.0 mm² (fill 0.0, 0.1 %); /USB_DN 1.8 mm² (fill 0.0, 0.1 %); /I2C_SCL 1.6 mm² (fill 0.0, 0.1 %); /CHRG_INT 1.1 mm² (fill 0.0, 0.0 %); /I2C_SDA 1.1 mm² (fill 0.0, 0.0 %)

**Split +3.3V | +5V**: min gap 0.90 mm, shared boundary 47.4 mm, bbox [100.6, 100.03, 164.95, 132.0].
Tracks on adjacent layers crossing the gap: /CHRG_INT (B) S174 1.52 mm in the gap at (104.6, 122.6), S176 0.60 mm in the gap at (117.2, 124.7), S179 0.88 mm in the gap at (103.6, 122.1); /I2C_SCL (B) S569 0.02 mm in the gap at (109.1, 122.9), S570 2.60 mm in the gap at (110.4, 122.9), S574 1.19 mm in the gap at (112.1, 122.5), S576 2.97 mm in the gap at (107.6, 122.9); /I2C_SDA (B) S539 0.02 mm in the gap at (105.4, 122.2), S541 6.01 mm in the gap at (108.4, 122.2), S542 0.16 mm in the gap at (111.5, 122.1); /LED_DATA (B) S25 1.10 mm in the gap at (130.4, 131.4); /Power Management/BQ_TS (B) S833 1.00 mm in the gap at (101.0, 110.9), S834 0.01 mm in the gap at (101.3, 111.2); /TCA_RESET (B) S151 0.70 mm in the gap at (141.9, 119.5); /USB_DN (B) S55 0.73 mm in the gap at (117.5, 131.2); /USB_DP (B) S140 1.20 mm in the gap at (118.1, 131.3); GND (B) S396 1.71 mm in the gap at (158.7, 127.4), S398 1.43 mm in the gap at (159.3, 127.8), S400 0.59 mm in the gap at (159.5, 126.9), S401 0.90 mm in the gap at (159.8, 128.2), S407 1.48 mm in the gap at (160.8, 127.8), S408 0.57 mm in the gap at (159.3, 128.2), S409 0.70 mm in the gap at (157.5, 128.1), S410 0.11 mm in the gap at (159.4, 127.9), S412 0.48 mm in the gap at (159.3, 128.3)

Antipads: 106 holes with a drill, 206.9 mm² in all. Merged clusters ≥ 3 mm²: +3.3V 13.7 mm² (9 drills) [127.69, 114.58, 131.7, 118.58]; +5V 8.4 mm² (10 drills) [101.34, 128.61, 105.19, 133.2]; +5V 6.6 mm² (1 drills) [82.05, 135.15, 84.95, 138.05]; +5V 6.5 mm² (4 drills) [81.31, 114.51, 84.99, 117.37]; +3.3V 5.7 mm² (5 drills) [114.96, 104.85, 118.2, 107.35]; +5V 5.5 mm² (3 drills) [81.31, 121.92, 84.43, 124.77]; +5V 5.4 mm² (3 drills) [77.23, 112.86, 79.65, 116.11]; +5V 3.5 mm² (3 drills) [136.79, 135.75, 138.99, 138.75]; +5V 3.3 mm² (3 drills) [153.49, 128.8, 155.88, 131.38]; +5V 3.2 mm² (3 drills) [92.15, 116.61, 94.58, 119.2]; +3.3V 3.2 mm² (3 drills) [154.66, 109.59, 155.96, 112.7]; +3.3V 3.1 mm² (3 drills) [153.16, 102.39, 155.86, 104.3]; +5V 3.1 mm² (3 drills) [143.99, 129.96, 146.09, 132.16]; +5V 3.1 mm² (3 drills) [93.6, 113.67, 96.58, 115.66]; +5V 3.1 mm² (2 drills) [79.92, 118.2, 81.32, 121.23]; +5V 3.1 mm² (3 drills) [84.39, 129.05, 86.71, 131.13]; +5V 3.0 mm² (2 drills) [122.16, 133.57, 124.56, 135.67].

| Kind | mm² | Mean width mm | At | Bbox | Fills touched | In keepout | Nets crossing on adjacent layers |
|---|---|---|---|---|---|---|---|
| split gap | 215.2 | 1.19 | (101.1, 117.5) | [96.95, 102.0, 162.9, 133.04] | +3.3V, +5V |  | /CHRG_INT, /I2C_SCL, /I2C_SDA, /LED_DATA, /Power Management/BQ_TS, /Power Management/VBAT, /Power Management/VSYS, /TCA_RESET, /USB_DN, /USB_DP, GND |
| void | 108.2 | 4.32 | (130.8, 104.5) | [121.0, 102.0, 140.5, 107.6] | +3.3V | yes | — |
| void | 1.2 | 0.32 | (116.4, 102.8) | [115.26, 102.0, 116.56, 103.55] | +3.3V |  | — |

## B.Cu

Fills cover 0.0 % of the outline. Adjacent: In2.Cu (0.1 mm).

| Zone | Net | Priority | Fill mm² | Holes | Bbox |
|---|---|---|---|---|---|
| Z4 | keepout | 0 | 0.0 | 0 | — |

Copper ownership (top 8 of 21 nets): GND 87.1 mm² (fill 0.0, 2.6 %); /Power Management/BAT_RAW 58.8 mm² (fill 0.0, 1.7 %); /USB_DN 16.7 mm² (fill 0.0, 0.5 %); /Power Management/VBAT 13.4 mm² (fill 0.0, 0.4 %); /USB_DP 13.4 mm² (fill 0.0, 0.4 %); /I2C_SCL 11.1 mm² (fill 0.0, 0.3 %); /I2C_SDA 10.0 mm² (fill 0.0, 0.3 %); +3.3V 8.8 mm² (fill 0.0, 0.3 %)

## Unreferenced signal track (adjacent plane)

Signal and high dv/dt nets that are not high-current. Nets with no unreferenced length are omitted.

| Net | Track mm (over a plane layer) | Over (raw) | None, raw | None, antipads excl. |
|---|---|---|---|---|
| /I2C_SCL | 73.30 | +3.3V 29.85, GND 29.13 | 14.32 | **6.78** |
| /I2C_SDA | 72.90 | GND 30.71, +3.3V 28.94 | 13.25 | **6.19** |
| /CHRG_INT | 42.75 | +3.3V 14.85, +5V 10.10, GND 8.36 | 9.44 | **4.80** |
| /TCA_RESET | 40.82 | +3.3V 14.98, GND 14.83, +5V 1.06 | 9.95 | **4.55** |
| /USB_DN | 69.62 | +5V 39.93, GND 13.68, +3.3V 4.50 | 11.50 | **3.52** |
| /USB_DP | 73.00 | +5V 38.37, GND 23.29, +3.3V 1.88 | 9.46 | **2.69** |
| /LED_DATA | 42.07 | GND 20.50, +5V 9.67, +3.3V 5.47 | 6.44 | **2.60** |
| /Power Management/BQ_TS | 26.75 | GND 11.16, +5V 9.08 | 6.52 | **1.71** |
| /ESP32_S3/EN | 24.21 | GND 23.26 | 0.95 | **0.00** |
| /LED Controller/DATA_TO_LEDS | 11.83 | +5V 6.52, GND 2.44 | 2.86 | **0.00** |
| /Power Management/BOOST_BOOT | 3.57 | GND 2.57 | 1.00 | **0.00** |
| /Power Management/BOOST_FSW | 7.55 | +5V 5.21, GND 0.49 | 1.85 | **0.00** |
| /Power Management/BQ_BTST | 4.71 | +5V 1.88, GND 0.17 | 2.67 | **0.00** |
| /Power Management/BQ_REGN | 14.69 | +5V 5.66, GND 5.32 | 3.70 | **0.00** |
| /Power Management/CC2 | 6.34 | GND 5.28 | 1.05 | **0.00** |

Fully referenced (raw): /ESP32_S3/GPIO0_BOOT, /ESP32_S3/USB_DN_MCU, /ESP32_S3/USB_DP_MCU, /Power Management/BOOST_COMP, /Power Management/BOOST_FB, /Power Management/BOOST_ILIM, /Power Management/BOOST_SS, /Power Management/BOOST_VCC, /Power Management/BQ_ILIM, /Power Management/CC1, /Power Management/COMP_MID, /Power Management/OTG_BIAS, /Power Management/PMOS_GATE, /TCA9548A_Subsystem/CH0_SCL, /TCA9548A_Subsystem/CH0_SDA, /TCA9548A_Subsystem/CH1_SCL, /TCA9548A_Subsystem/CH1_SDA, /TCA9548A_Subsystem/CH2_SCL, /TCA9548A_Subsystem/CH2_SDA, Net-(D1-A).

Segments with any unreferenced length, antipads excluded (top 25; all in the JSON):

| Net | Segment | Layer → plane | Seg mm | None, raw | None, antipads excl. |
|---|---|---|---|---|---|
| /I2C_SDA | S541 | B → In2 | 6.01 | 6.01 | 6.01 |
| /I2C_SCL | S576 | B → In2 | 2.97 | 2.97 | 2.97 |
| /USB_DN | S55 | B → In2 | 11.24 | 2.97 | 2.97 |
| /USB_DP | S140 | B → In2 | 11.77 | 2.69 | 2.69 |
| /I2C_SCL | S570 | B → In2 | 2.60 | 2.60 | 2.60 |
| /CHRG_INT | S176 | B → In2 | 18.38 | 3.10 | 2.40 |
| /TCA_RESET | S155 | B → In2 | 3.82 | 2.52 | 1.92 |
| /LED_DATA | S25 | B → In2 | 4.65 | 1.75 | 1.75 |
| /Power Management/BQ_TS | S833 | B → In2 | 1.89 | 1.70 | 1.70 |
| /CHRG_INT | S174 | B → In2 | 2.35 | 1.52 | 1.52 |
| /TCA_RESET | S151 | B → In2 | 2.02 | 1.50 | 1.50 |
| /I2C_SCL | S574 | B → In2 | 3.01 | 1.79 | 1.19 |
| /TCA_RESET | S153 | B → In2 | 9.58 | 1.13 | 1.13 |
| /CHRG_INT | S179 | B → In2 | 0.88 | 0.88 | 0.88 |
| /LED_DATA | S23 | B → In2 | 1.00 | 0.64 | 0.64 |
| /USB_DN | S67 | B → In2 | 4.20 | 0.48 | 0.48 |
| /LED_DATA | S27 | B → In2 | 0.92 | 0.21 | 0.21 |
| /I2C_SDA | S542 | B → In2 | 4.24 | 0.43 | 0.16 |
| /USB_DN | S57 | B → In2 | 0.07 | 0.07 | 0.07 |
| /I2C_SCL | S569 | B → In2 | 0.02 | 0.02 | 0.02 |
| /I2C_SDA | S539 | B → In2 | 0.02 | 0.02 | 0.02 |
| /Power Management/BQ_TS | S834 | B → In2 | 0.01 | 0.01 | 0.01 |

## GND stitching

136 GND vias over 3396 mm² of board: 4.01 per cm². Grid 10 mm, 36 cells: vias per cell 0 → 3 cells, 1 → 6 cells, 2 → 11 cells, 3 → 3 cells, 4 → 1 cells, 5+ → 12 cells.

Cells with no GND via: [125.7, 101.0, 135.7, 111.0]; [135.7, 111.0, 145.7, 121.0]; [75.7, 131.0, 85.7, 139.5].

Signal vias farthest from a GND via (top 15, centre to centre): V11 /TCA_RESET 7.11 mm (V101); V10 /USB_DP 6.79 mm (V72); V201 /I2C_SCL 6.29 mm (V52); V14 /CHRG_INT 5.82 mm (V120); V13 /TCA_RESET 5.80 mm (V136); V202 /I2C_SCL 5.26 mm (V104); V6 /USB_DN 4.47 mm (V112); V207 /Power Management/BQ_REGN 4.43 mm (V116); V1 /LED_DATA 4.33 mm (V46); V15 /CHRG_INT 4.33 mm (V88); V0 /LED_DATA 4.29 mm (V48); V2 /USB_DN 4.29 mm (V63); V4 /USB_DN 4.10 mm (V43); V196 /I2C_SDA 3.97 mm (V104); V5 /USB_DN 3.61 mm (V63)

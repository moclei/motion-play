# PCB Routing Verification — Plan

## Approach

A single Python script (`tools/verify-routing.py`) that parses the `.kicad_pcb` file using kiutils, extracts all routing primitives, and runs a series of structured checks derived from `ROUTING_GUIDE.md`. Outputs a Markdown report and a JSON sidecar.

Before verification, regenerate `pcb-layout-context.json` using the existing extraction tool so that context files are in sync with the routed board.

### Data Flow

```
motion-play-main.kicad_pcb
        │
        ▼
   kiutils.Board.from_file()
        │
        ├─► Footprints → absolute pad positions (ref, pad#, net, x, y, layers)
        ├─► Segments → (start, end, width, layer, net)
        ├─► Vias → (position, size, drill, layers, net)
        └─► Zones → (net, layers, polygons, filled_polygons)
        │
        ▼
   Per-net topology builder
        │
        ├─► Group all primitives (segments, vias, zone fills, pads) by net
        └─► Build connectivity graph per net (nodes = points, edges = segments/vias)
        │
        ▼
   Verification checks (each produces PASS/FAIL/WARNING + detail)
        │
        ▼
   Report generator → routing-report.md + routing-report.json
```

### Computing Absolute Pad Positions

Pad positions in kiutils are relative to the footprint origin. To get absolute board coordinates:

```
abs_x = fp.position.X + pad.X * cos(rot) - pad.Y * sin(rot)
abs_y = fp.position.Y + pad.X * sin(rot) + pad.Y * cos(rot)
```

Where `rot` is the footprint rotation in radians. This is validated against known DRC report coordinates.

### Per-Net Connectivity Graph

For each net:
1. Collect all segment endpoints and via positions as graph nodes
2. Collect all pad centers (from footprints on that net) as graph nodes
3. Add edges for each segment (start↔end) and each via (connects layers at same XY)
4. Two nodes merge if within 0.1mm tolerance (handles rounding between pad center and trace endpoint)
5. Connected components reveal whether all expected pads on a net are actually connected by copper

For zone connectivity, a pad is "zone-connected" if the pad center falls within a filled polygon of the correct zone/net. This requires a point-in-polygon test against `zone.filledPolygons`.

## Check Categories

### 1. Trace Width Checks

For each segment, verify width matches expected net class:

| Net Class | Expected Width | Nets |
|-----------|---------------|------|
| Power_5V | 1.5mm (or zone) | `+5V`, `BOOST_SW` |
| Power_Med | 1.0mm | `VSYS`, `VSYS_SENSE`, `Protected_VBUS`, `VBUS_RAW`, `BQ_SW`, `BQ_PMID`, `+5V_TO_LEDS`, `Net-(C7-Pad2)` |
| Power_Low | 0.75mm | `VBAT`, `BAT_RAW`, `BQ_REGN` |
| Power_3V3 | 0.5mm | `+3.3V` |
| Sensitive | 0.2mm | `BOOST_FB`, `BOOST_COMP`, `COMP_MID` |
| Default | 0.25mm | All others |

Allow a small tolerance (~0.02mm) for rounding. Flag any segment that deviates.

Exception: nets that share both power and sense paths (VSYS, VSYS_SENSE) legitimately have both fat and thin segments — the thin ones are INA219 Kelvin sense connections. These get a special exemption checked in the Kelvin verification.

### 2. Zone Existence Checks

| Zone | Expected Net | Expected Layer | Purpose |
|------|-------------|----------------|---------|
| BOOST_SW pour | BOOST_SW | F.Cu | Switching loop copper pour |
| +5V output | +5V | F.Cu (near U6) | Output cap cluster |
| +5V distribution | +5V | In2.Cu | Long run to U1/F1 |
| GND plane | GND | In1.Cu | Primary ground return |
| GND plane | GND | B.Cu | Bottom ground fill |
| 3.3V zone | +3.3V | In2.Cu | Logic area |

### 3. Critical Path Connectivity

Verify specific pad-to-pad paths exist as connected copper:

- **BOOST_SW loop:** U6 pins 4-7 → L2 pad 1 (via zone)
- **BQ_SW:** U5 pins 19-20 → L1 pad 1
- **VSYS power:** L1 pad 2 → U5 pins 15-16 → R44 pad 1
- **VSYS_SENSE:** R44 pad 2 → L2 pad 2 → U6 pins 2/9
- **Protected_VBUS:** F2 pad 2 → U5 pins 1/24 → C22 pad 1
- **VBAT:** J8 pad 1 → Q2 pin 1 (BAT_RAW), Q2 pin 3 → U5 pins 13-14
- **I2C main trunk:** U2 pins 15/16 → U4 pins 22/23 (via R28/R29 pull-ups on trunk)
- **I2C channels:** U4 CH0 pins → J4, U4 CH1 pins → J5, U4 CH2 pins → J6

### 4. I2C Length Matching

For each I2C channel pair:
- CH0: `CH0_SDA` vs `CH0_SCL` (U4 → J4)
- CH1: `CH1_SDA` vs `CH1_SCL` (U4 → J5)
- CH2: `CH2_SDA` vs `CH2_SCL` (U4 → J6)
- Main trunk: `I2C_SDA` vs `I2C_SCL` (U2 → U4)

Sum segment lengths per net. Report absolute difference and percentage. At 400kHz I2C, length matching matters less than for high-speed differential — flag if difference exceeds 5mm (warning) or 10mm (fail).

### 5. I2C Isolation from Switching Nodes

Define exclusion zones around switching components:
- L1 bounding box + 3mm margin on all sides
- L2 bounding box + 3mm margin on all sides
- U6 SW pins (4-7) area + 2mm margin
- U5 SW pins (19-20) area + 2mm margin

For every I2C segment (main trunk + all channels), check if either endpoint falls within any exclusion zone. Also check if any segment crosses through an exclusion zone (line-rectangle intersection).

### 6. INA219 Kelvin Sense Verification

On the VSYS net, identify segments connecting R44 pad 1 → U7 pin 1. On the VSYS_SENSE net, identify segments connecting R44 pad 2 → U7 pin 2. These must be:
- Width 0.25mm (not 1.0mm power width)
- A distinct sub-path that does not share segments with the main power path
- Direct connection (not going through other components first)

Approach: starting from U7 pin 1, walk the connectivity graph on the VSYS net following only 0.25mm segments. Verify R44 pad 1 is reachable. Same for pin 2 / VSYS_SENSE / R44 pad 2.

### 7. FB/COMP Routing Side Check

BOOST_FB and BOOST_COMP traces must route on U6's left side (lower x values relative to U6 center). No FB/COMP segment should have x-coordinates greater than U6's center x. These sensitive feedback traces must not cross the SW/inductor area on U6's right side.

## Report Format

**Markdown report** (`hardware/pcb-main/kicad/reports/routing-verification.md`):
- Summary table: check name, status (PASS/FAIL/WARNING), one-line detail
- Detailed sections per check category with specifics on any failures
- Timestamp and source file hash for reproducibility

**JSON sidecar** (`hardware/pcb-main/kicad/reports/routing-verification.json`):
- Machine-readable version of every check result
- Includes raw measurements (trace lengths, distances, widths) for each check
- Enables future CI integration or diff-against-previous-run

## Open Questions

- None currently — all trade-offs from planning session have been resolved.

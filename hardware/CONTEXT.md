# Hardware Context

Custom PCB designs for the Motion Play sensor system. Three PCB types make up the electronics: one main board and a two-part sensor assembly (rigid base + flex strip) replicated three times around the hoop.

## Physical Architecture

- **Hoop diameter:** 500mm (transparent polypropylene tubing, 19mm diameter)
- **Orientation:** Vertical plane (opening faces horizontally)
- **Main enclosure:** 85mm × 45mm × 15mm at 6 o'clock position

### Sensor Placement

3 sensor assemblies positioned at:
- Position 1 (M1): 6 o'clock (bottom, co-located with main enclosure)
- Position 2 (M2): 9 o'clock (left side)
- Position 3 (M3): 3 o'clock (right side)

Each assembly has dual sensors with ~2° angular offset:
- **Side A** (-2°): Faces the back of the hoop
- **Side B** (+2°): Faces the front of the hoop

The angle increases the detection time window for direction discrimination. Object passing through triggers sequential sensor activation — direction is determined by A→B vs B→A trigger sequence. 120° spacing provides full coverage.

See [`docs/detection-algorithm.md`](../docs/detection-algorithm.md) for the full algorithm design and transit scenario catalog.

## Custom PCBs

### 1. Main PCB (`hardware/pcb-main/`)

Houses the system controller and power management:

- **T-Display-S3** (ESP32-S3 development board) — The MCU with a built-in LCD screen. Long-term goal is to incorporate a bare ESP32-S3 directly into the main PCB.
- **TCA9548A** I2C multiplexer — Organizes I2C communication with sensor PCBs. 3 channels used. Speed is critical for high-frequency sensing.
- **AP2112K-3.3** voltage regulator — Provides 3.3V to sensors.
- **DWEII USB-C power module** — Development power module providing 5V @ ~2.4A with battery charging. Will be replaced with a custom solution eventually.
- **SN74AHCT125** logic level shifter — Between MCU (3.3V) and WS2818B LED strip (5V). 72 LEDs, 1.2m strip.
- **3× JST-SH 5-pin connectors** — One per sensor PCB (Pin 1 = 3.3V, Pin 2 = GND, Pin 3 = SDA, Pin 4 = SCL, Pin 5 = INT)

### 2. Sensor Rigid Base (`hardware/sensor-rigid/`)

The mounting board with local I2C multiplexing:

| Ref | Component | Function |
|-----|-----------|----------|
| U1 | PCA9546A | Local I2C mux (controls two sensors) |
| J1 | JST-SH 5-pin | Connector to main board |
| FPC1 | C132510 ZIF | Connection to flex sensor strip |
| R1, R2 | 4.7kΩ | Main I2C pull-ups |
| R6-R9 | 4.7kΩ | Per-sensor I2C pull-ups |
| R3, R12-R14 | 10kΩ | Reset and address pull-ups |
| R5 | 8.2kΩ | INT pull-up |
| D2, D3 | BAT54S | Interrupt combining (wired-OR) |
| D1, R4 | LED + 1kΩ | Power indicator |
| C1, C2 | 2.2µF, 0.1µF | Power bypass caps |
| JP3, JP4 | Solder jumpers | I2C address select (A0, A1) |

- **PCB Type**: Standard rigid FR4, 1.6mm thickness, HASL or ENIG finish.
- **I2C Addressing (PCA9546A):** Board 1: 0x70, Board 2: 0x71, Board 3: 0x72 (set via JP3/JP4).

### 3. Flex Sensor Strip (`hardware/sensor-flex/`)

Polyimide flex PCB that bends to angle sensors outward:

- **PCB Type**: 2-layer polyimide flex, ~0.11mm core + 0.2mm stiffener = 0.3mm total, ENIG finish
- ~25mm × 8mm, sensors 10mm apart center-to-center
- ~5mm center bend zone (unstiffened, flexible)
- Stiffened at sensor areas and connector tail

| Ref | Component | Function |
|-----|-----------|----------|
| IC1, IC2 | VCNL4040M3OE | Proximity sensors |
| C4, C8 | 2.2µF | LED anode capacitors |
| C6, C7 | 0.1µF | VDD bypass capacitors |

Connected to rigid base via ZIF FPC connector (C132510, 1.0mm pitch, top contact, slide lock, 0.3mm FPC):

**ZIF Connector Pinout:**

| Pin | Signal | Purpose |
|-----|--------|---------|
| 1 | 3.3V | Power |
| 2 | INT1 | Interrupt sensor 1 |
| 3 | SDA1 | I2C data sensor 1 |
| 4 | SCL1 | I2C clock sensor 1 |
| 5 | GND | Ground (shield between sensor groups) |
| 6 | INT2 | Interrupt sensor 2 |
| 7 | SDA2 | I2C data sensor 2 |
| 8 | SCL2 | I2C clock sensor 2 |
| 9 | GND | Mechanical mounting |
| 10 | GND | Mechanical mounting |

**Why the split design?** The flex PCB allows sensors to be angled ~2° away from each other, increasing the time window between sequential sensor triggers and improving direction discrimination.

### Flex PCB Design Notes
1. Center ~5mm bend zone is unstiffened
2. 0.25mm traces in bend zone (wider than normal), curved paths, no vias
3. Traces perpendicular to bend axis for durability
4. Components only on stiffened areas

See `docs/initiatives/flex-sensor-pcb/DESIGN_PLAN.md` for detailed design rationale.
See `hardware/sensor-flex/FLEX_PCB_SETUP.md` for flex PCB manufacturing notes.

## Component Nicknames

| Component | Part Number | Function | Shorthand |
|-----------|------------|----------|-----------|
| Main Controller | LilyGO T-Display-S3 | ESP32-S3 with built-in display | `tdisplay` |
| I2C Multiplexer | TCA9548A | 8-channel I2C switch (main board) | `tca` |
| Local I2C Multiplexer | PCA9546A | I2C switch (sensor board) | `pca` |
| Sensors | VCNL4040 | Proximity & ambient light sensing | `sensors` |
| Voltage Regulator | AP2112K-3.3 | 3.3V regulator | `apk` |
| Power Module | DWEII USB-C | USB-C power input | `dweii` or `power module` |

## Annotated Netlist Specification

Raw KiCad schematic files are difficult for AI assistants to interpret. The **annotated netlist** system provides machine-readable circuit data with human-written context.

**Always use annotated netlists** (`*.json` + `*.annotations.yaml`) instead of `.kicad_sch` files when understanding hardware designs.

### File Locations

| PCB | Netlist | Annotations |
|-----|---------|-------------|
| Main PCB | `hardware/pcb-main/kicad/netlists/*.json` | `hardware/pcb-main/kicad/netlists/*.annotations.yaml` |
| Sensor Rigid Base | `hardware/sensor-rigid/sensor-rigid.json` | `hardware/sensor-rigid/sensor-rigid.annotations.yaml` |
| Sensor Flex Strip | `hardware/sensor-flex/sensor-flex.json` | `hardware/sensor-flex/sensor-flex.annotations.yaml` |
| Sensor Legacy (deprecated) | `hardware/pcb-sensor/kicad/netlist/*.json` | N/A — use rigid+flex instead |

### Annotation File Format

```yaml
_meta:
  description: "Brief description of the PCB"
  version: "4.0"
  last_synced: "2025-12-15T14:30:00"
  netlist_hash: "abc123"

_status:
  missing_annotations: []
  archived_count: 0

components:
  IC1:
    nickname: "sensor1"
    purpose: "Front-facing proximity sensor"
  R5:
    purpose: "8.2kΩ pull-up for combined INT line"

nets:
  "Net-(D2-A)":
    nickname: "INT_COMBINED"
    purpose: "Combined interrupt line from both sensors via wired-OR diodes"
    connects_to: "Main PCB GPIO via J1 Pin 5"

_archived:
  # Components removed from schematic (kept for reference)
```

### Workflow

1. Edit schematic in KiCad
2. Export netlist via KiCad (runs `firmware/tools/convert_netlist_to_json.py`)
3. Plugin generates/updates `*.json` and `*.annotations.yaml` (preserves existing annotations)
4. Check `_status.missing_annotations` for new items needing description
5. Fill in annotations for new components/nets

## VCNL4040 Sensor Capabilities

- **Proximity Detection**: IR LED emission and reflection measurement
- **Ambient Light Sensing**: Human eye response approximation
- **Programmable**: Integration time, interrupt thresholds, LED current control
- **Communication**: I2C up to 400kHz
- **Reference docs**: `docs/references/vcnl4040/`

## I2C Multiplexing Architecture

```
T-Display-S3
    └── TCA9548A (Primary MUX, 0x70)
        ├── Channel 0 → PCA9546A (0x70) → 2× VCNL4040 (Module 1)
        ├── Channel 1 → PCA9546A (0x71) → 2× VCNL4040 (Module 2)
        └── Channel 2 → PCA9546A (0x72) → 2× VCNL4040 (Module 3)
```

All VCNL4040 sensors share address 0x60. The TCA→PCA dual-MUX chain provides individual addressability.

---

*Last Updated: March 4, 2026*

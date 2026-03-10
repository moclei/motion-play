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
| C4, C8 | 2.2µF | LED anode capa30Qtors |
| C6, C7 | 0.1µF | VDD bypass capacitors |
| R10, R11 | 22Ω | VDD series filter resistors (one per sensor) |
| FPC1 | FPC_Tail_10P | FPC tail connector (mates with ZIF on rigid base) |

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

## Schematic Context System

Raw KiCad schematic files are difficult for AI assistants to interpret. The **schematic context system** extracts circuit data and combines it with human-confirmed semantic annotations into a single `circuit-context.json` file per PCB project.

**Always use `circuit-context.json`** instead of `.kicad_sch` files when reasoning about hardware designs.

### File Locations

| PCB | Context File | Status |
|-----|-------------|--------|
| Main PCB | `hardware/pcb-main/kicad/circuit-context.json` | Complete — 37 components, 26 nets, 5 functional blocks |
| Sensor Rigid Base | `hardware/sensor-rigid/circuit-context.json` | Complete — 27 components, 16 nets, 6 functional blocks |
| Sensor Flex Strip | `hardware/sensor-flex/circuit-context.json` | Complete — 9 components, 12 nets, 4 functional blocks |
| Power Supply | `hardware/pcb-power-supply/kicad/circuit-context.json` | Complete — 50 components, 29 nets, 4 functional blocks |

### What's in circuit-context.json

- **Components** — every part with value, footprint, LCSC number, pin-level connectivity, and AI annotations (function, block membership, role, critical specs)
- **Nets** — all named nets with type (power/signal/clock), protocol, direction, and description
- **Functional blocks** — logical groupings (power, mcu, i2c_mux, sensor_connectors, led_controller) with descriptions and design intent notes
- **Sheet interfaces** — hierarchical pin mappings showing signal flow between parent and child schematics
- **Source metadata** — schema version, source hash, and extraction timestamp for staleness detection

### Tooling

Scripts live in `tools/schematic-context/` (see that folder's README for full usage):

| Script | Purpose |
|--------|---------|
| `extract.py` | Runs kicad-cli + kiutils to produce `circuit-context.json` from a root `.kicad_sch` |
| `annotate.py` | Writes `ai_` properties to components in `.kicad_sch` files via kiutils |
| `show.py` | Displays annotation coverage — useful during interactive annotation sessions |

### Workflow

1. Edit schematic in KiCad
2. Run `extract.py` on the root `.kicad_sch` — uses `--previous` to merge forward existing net/block annotations
3. If new components appeared, run an interactive annotation session with AI (propose annotations → confirm → write via `annotate.py`)
4. Re-extract to produce the final context file with all annotations merged

Component annotations (`ai_function`, `ai_block`, `ai_role`, `ai_critical_specs`) are stored as custom properties in the `.kicad_sch` file — they survive schematic edits. Net and block annotations are stored in `circuit-context.json` and carried forward via the `--previous` merge.

### Deprecated: Old Netlist + Annotation System

The previous system used `convert_netlist_to_json.py` to produce JSON netlists with separate YAML annotation files. This has been fully replaced by the schematic context system. Old files in `hardware/pcb-main/kicad/netlists/` and `hardware/pcb-sensor/kicad/netlist/` are retained for reference but should not be used.

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

*Last Updated: March 9, 2026*

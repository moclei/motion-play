# Motion Play Project Context

> **Quick Reference**: See [manifest.yaml](./manifest.yaml) for structured metadata. See [IDEAS.md](./IDEAS.md) for feature backlog. See [WORKFLOW.md](./WORKFLOW.md) for instructions on managing features and initiatives.

## Overview

Motion Play is an ESP32-based sensor system for detecting and tracking fast-moving objects through a detection plane. The system determines movement direction and provides visual feedback through LED lights. Multiple units can be networked via Bluetooth, and the system supports WiFi connectivity for mobile device integration. Designed for games and sports performance training applications.

## Current Project Status

**Hardware:** ✅ Custom PCBs operational with dual-MUX architecture (TCA→PCA→Sensors)  
**Firmware:** ✅ Full data collection pipeline (1000 Hz, PSRAM buffering, MQTT transmission)  
**Backend:** ✅ AWS IoT Core + Lambda + DynamoDB + API Gateway  
**Frontend:** ✅ React web interface with real-time visualization and device control  
**ML Detection:** 🔄 Initial proof-of-concept working — TFLite Micro 1D CNN running on-device, selectable via config. See `docs/initiatives/ml-direction-detection/`  
**Current Phase:** Phase 4 - Integration & Polish (77% complete overall)

## Hardware Architecture

### Custom PCBs

1. **Main PCB** - Houses:
   - T-Display-S3 (ESP32 development board) - The brains of the operation - an MCU devkit with an LCD screen to assist in debugging during the early stages of development. I am considering moving to another MCU like the ESP32-S3-DevKitC-3. Ultimately my goal would be to incorporate a bare ESP32-S3 into the main PCB to control things, with just the components necessary to achieve the purpose of this project, and move away from devkits like the T-Display-S3 or ESP32-S3-DevKitC-1. I will look to take that step when the project has reached a more mature position.
   - TCA9548A I2C multiplexer - Our project communicates over I2C with multiple VCNL4040 sensors to detect movement. The MCU has one I2C bus and communicates with this multiplexer to organize communications with the sensor PCBs. Speed is of the essence for this project, so all systems must be tuned to maximize I2C communication speed. 3 channels are used to connect to the sensor PCBs
   - AP2112K-3.3 3.3V voltage regulator, to provide 3.3v power, to the sensors mostly.
   - DWEII USB-C power module - This is a development module I buy online for cheap, it provides a USB-C port to plug in, and gives out 5v (usually around 5.2v) at approximately 2.4A. It has battery charging capabilities, and claims it can output 5.2v @ 2.4A from the battery, although I haven't tested this myself. I would ultimately like to replace this with a custom solution, built into the main PCB. Powering the board by battery is a later goal I have, but beyond the scope right now.
   - SN74AHCT125 - This is described as a "4-ch, 4.5-V to 5.5-V buffers with TTL-compatible CMOS inputs and 3-state outputs" and is used as a logic level shifter between the MCU and the LED strip controlled by it - a WS2818B individually aadressable RGB LED light strip, with 60 LEDs per meter, 1.2 meters long, powered from the DWEII power module
   - JST-SH 5-pin connectors, 3 of them, leading to 3 sensor PCBs, each with two VCNL4040s. Each sensor PCB has a local multiplexer to handle the multiplexing of it's two sensors.
   - Supporting components (resistors, diodes, connectors)
   - See the Netlist and BOM for more information (found in the .context/motion-play-main/netlist folder). They are in json format, let me know if you can't find them.

2. **Sensor PCBs** (Rigid + Flex hybrid design) - The sensor board is split into two PCBs that connect via ZIF FPC connector:

   **Rigid Base PCB** (`hardware/sensor-rigid/`):
   - PCA9546A for local I2C multiplexing (controls the two sensors)
   - JST-SH 5-pin connector to main board
   - ZIF FPC connector (C132510) for flex PCB connection
   - I2C pull-up resistors (R1-R2 for main bus, R6-R9 for sensor channels)
   - BAT54S Schottky diodes for interrupt combining
   - Power LED with enable jumper
   - Solder jumpers for I2C addressing (JP3, JP4)
   - Connector pinout: Pin 1 = 3.3V, Pin 2 = GND, Pin 3 = SDA, Pin 4 = SCL, Pin 5 = INT

   **Flex Sensor Strip** (`hardware/sensor-flex/`):
   - 2 VCNL4040 proximity/ambient light sensors
   - Bypass capacitors for each sensor (0.1µF + 2.2µF)
   - Polyimide flex PCB that bends in the center
   - Sensors are angled ~2° outward when bent, increasing detection time window
   - Stiffened zones at sensor areas and connector tail; center remains flexible
   - 10-pin FPC tail connects to rigid base via ZIF connector

   **Why the split design?**
   The flex PCB allows the sensors to be angled slightly away from each other. This physical separation of detection windows provides more time between sequential sensor triggers, improving direction detection accuracy for fast-moving objects.

   See `docs/initiatives/flex-sensor-pcb/DESIGN_PLAN.md` for detailed design rationale.
   See `hardware/sensor-flex/FLEX_PCB_SETUP.md` for flex PCB manufacturing notes.

### Components Nicknames

| Component | Part Number | Function | Shorthand |
|-----------|------------|----------|-----------|
| Main Controller | LilyGO T-Display-S3 | ESP32-S3 with built-in display | `tdisplay` |
| I2C Multiplexer | TCA9548A | 8-channel I2C switch | `tca` |
| Local I2C Multiplexer | PCA9546A | I2C switch | `pca` |
| Sensors | VCNL4040 | Proximity & ambient light sensing | `sensors` |
| Voltage Regulator | AP2112K-3.3 | 3.3V regulator | `apk` |
| Power Module | DWEII USB-C | USB-C power input | `dweii` or `power module` |

### Hardware Connections

**⚠️ AI Guidance**: For understanding PCB designs, always use the **annotated netlists** (`*.json` + `*.annotations.yaml`), never the raw KiCad schematic files (`.kicad_sch`). The annotation files are the source of truth for understanding circuit intent.

See the Annotated Netlist Specification below for file locations and format.

### Pin Configuration

**T-Display-S3 GPIO Assignments (Motion Play v4/v5):**

| GPIO | Function | Description | Notes |
|------|----------|-------------|-------|
| 43 | I2C SDA | I2C data line to TCA9548A | Custom PCB connection |
| 44 | I2C SCL | I2C clock line to TCA9548A | Custom PCB connection |
| 10 | TCA_RESET | TCA9548A reset control | Active low reset |
| 11 | SENSOR_INT_1 | Sensor board 1 interrupt | From PCA9546A via VCNL4040 |
| 12 | SENSOR_INT_2 | Sensor board 2 interrupt | From PCA9546A via VCNL4040 |
| 13 | SENSOR_INT_3 | Sensor board 3 interrupt | From PCA9546A via VCNL4040 |
| 16 | LED_STRIP_DATA | WS2818B LED strip control | 72 LEDs, 5V logic level |

**Built-in T-Display-S3 Pins:**
| GPIO | Function | Description |
|------|----------|-------------|
| 14 | BUTTON_1 | Built-in button 1 |
| 0 | BUTTON_2 | Built-in button 2 (BOOT) |
| 15 | POWER_ON | Display power control |
| 21 | TOUCH_RES | Touch screen reset |

**Display Interface (Parallel 8-bit):**
- Data: GPIO 39-42, 45-48 (D0-D7)
- Control: GPIO 5-9 (RES, CS, DC, WR, RD)
- Backlight: GPIO 38

**Pin Conflicts to Note:**
- GPIO 16: Used for LED strip (touch interrupt disabled)
- GPIO 10-13: Used for Motion Play hardware (SD card disabled)

## Software Stack

### Development Environment
- **Framework**: Arduino
- **Platform**: PlatformIO
- **Board**: ESP32-S3
- **Laptop**: Macbook Pro
- **Version Control**: Github
- **IDE**: Cursor (VSCode based)

### Dependencies
```ini
lib_deps =
    bodmer/TFT_eSPI@^2.5.31        ; Display driver (ST7789, 8-bit parallel)
    adafruit/Adafruit BusIO@^1.14.5
    adafruit/Adafruit VCNL4040@^1.1.4
    robtillaart/TCA9548@^0.3.0
    fastled/FastLED@^3.7.0
    knolleary/PubSubClient@^2.8
    bblanchon/ArduinoJson@^6.21.3
    spaziochirale/Chirale_TensorFLowLite@^2.0.0
```

### Configuration Parameters
```ini
monitor_speed = 115200
upload_speed = 921600
board_build.flash_mode = qio
board_build.f_cpu = 240000000L
board_build.f_flash = 80000000L
```

**Critical TFT_eSPI build flags** — The T-Display-S3 requires a custom `User_Setup.h` (in `firmware/include/`) to configure the ST7789 driver with 8-bit parallel interface and correct pin mappings. Two build flags in `platformio.ini` ensure the library always uses this custom config instead of its default:
```ini
-DUSER_SETUP_LOADED
-include firmware/include/User_Setup.h
```
Without these, TFT_eSPI falls back to its default ILI9341 SPI configuration, resulting in a black screen (backlight on, no display output).

## Power Management Architecture

### Power Flow Design
The system uses isolated power paths to prevent conflicts:

**Primary Power Path (Normal Operation):**
- DWEII USB-C module → +5V rail → Main PCB components
- +5V → AP2112K regulator → +3.3V rail → Sensors, TCA9548A
- +5V → LED strip (directly)
- +5V → T-Display via pin 12 (5V pin)

**Programming Power Path (Development):**
- MacBook USB-C → T-Display USB port → T-Display internal power
- T-Display 3.3V pins: **DISCONNECTED** from main PCB (prevents voltage regulator conflict)
- T-Display 5V pin: **CONNECTED** to main PCB +5V rail

### Power Isolation Challenge

**Issue:** The T-Display's 5V pin (pin 12) is bidirectional. When powered via USB for programming, it back-feeds 5V to the main PCB's +5V rail, partially powering components. This is problematic because:

1. USB power (500-900mA) is insufficient for LED strip (up to 4-5A)
2. May cause brown-outs or damage when code tries to activate LEDs
3. Creates unpredictable component behavior during development

**Note:** While the T-Display's 3.3V output pins are disconnected from the main PCB, the 5V connection remains necessary for normal operation, creating this development challenge.

## Building and Deployment

### Prerequisites
- Install PlatformIO (VS Code extension or CLI)
- Install CP210x USB drivers if needed
- Have both cables ready:
  - **Cable A**: USB-C to wall power (for DWEII module)
  - **Cable B**: USB-C to MacBook (for programming/serial monitor)
  - **Data-only adapter**: USB-C female-to-male with power pins disabled

### Development Workflow

**For Code Upload:**
1. Ensure Cable A (DWEII power) is **disconnected**
2. Connect Cable B (MacBook) directly to T-Display USB-C (no data-only adapter)
3. Upload code via PlatformIO
4. Device will reboot and start running code

**For Testing (after upload):**
1. Disconnect Cable B from T-Display
2. Install data-only adapter onto Cable B
3. Reconnect Cable B (with adapter) to T-Display - for serial monitoring only
4. Connect Cable A to DWEII module - provides main power
5. Open serial monitor

**For Re-uploading:**
1. Disconnect Cable A (DWEII power)
2. Remove data-only adapter from Cable B
3. Reconnect Cable B directly to T-Display
4. Upload new code
5. Repeat testing steps above

### Safety Considerations

**⚠️ Critical for LED Testing:**
- Always have DWEII power (Cable A) connected before LEDs initialize
- Code should include startup delay allowing time to switch power sources
- Never rely on USB power for LED strip operation

**Why the data-only adapter?**
- Prevents power conflicts between MacBook USB and DWEII module
- Allows serial monitoring while DWEII provides proper power
- Without it: potential for competing 5V sources through T-Display pin 12

**Power Source Indicator:**
- If main PCB components (LEDs, sensors) activate with only Cable B connected, power is back-feeding through T-Display 5V pin
- This is expected but insufficient for proper operation
- Always verify DWEII module is connected for component testing

### Ideal vs Current Setup

**Current Setup:**
- Requires cable swapping and adapter manipulation between upload and test
- Necessary due to 5V pin back-feeding when T-Display powered via USB

**Ideal (not yet reliable):**
- Leave Cable A always connected
- Leave Cable B with data-only adapter installed
- Upload and test without cable changes
- *Note: This doesn't work reliably yet - investigating*

### Debugging Tools

- **Built-in T-Display screen** for status messages and mode display
- **Serial monitor** via Cable B (with data-only adapter) — `pio device monitor`
- **DWEII power indicator LED** (when module powered)

#### Serial Studio (Real-Time Visualization)

Serial Studio is a standalone desktop app for real-time sensor visualization and detection algorithm debugging. It provides live plotting of all 6 sensor channels plus algorithm internals (smoothed signals, thresholds, wave states, detection results) without needing the full cloud pipeline.

**Installation:**
```bash
brew install --cask serial-studio
```

**Enabling Serial Studio output:**

1. In `platformio.ini`, change the build flag from `false` to `true`:
   ```
   -DSERIAL_STUDIO_DEFAULT=true
   ```
2. Build and flash: `pio run -t upload`
3. The firmware will now emit structured CSV frames (`/*...*/` delimited) alongside normal serial output.

**Connecting Serial Studio:**

1. **Close the PlatformIO serial monitor first** — only one application can hold the serial port at a time.
2. Open Serial Studio.
3. Load the project file: `tools/serial-studio/motion-play.json` (File → Open).
4. Select the serial port (same one PlatformIO uses) and set baud rate to **115200**.
5. Click Connect. The custom dashboard should populate with live sensor and algorithm data.

**Important notes:**
- When done with Serial Studio, disconnect it before reopening the PlatformIO serial monitor.
- Set `SERIAL_STUDIO_DEFAULT` back to `false` when not using Serial Studio, to keep normal serial output clean.
- The flag can also be overridden at runtime via cloud config (`serial_studio_enabled` key) if WiFi is connected.
- Serial Studio output works in all active modes (DEBUG, PLAY, LIVE_DEBUG). Algorithm telemetry fields are populated in PLAY and LIVE_DEBUG modes.

**Full technical details:** See `docs/initiatives/serial-studio/` (BRIEF, PLAN, TASKS).

## Project Structure

motion-play/
├── .context/               # AI documentation
├── .pio/               # Platformio configs
├── docs/            # Project documentation
├── firmware/            # root folder for all software for this project
│   ├── src/            # source code
│   ├── tools/            # various scripts and code, such as Kicad python extension scripts
├── tools/              # Diagnostic scripts (download-session.sh, diagnose-session.sh)
├── hardware/     # root folder for all hardware for this project
│   ├── components/   # contains folders for each hardware component used, with datasheets, symbols, footprints and more
│   ├── pcb-main/  # root folder for the main PCB project
│   │   ├── kicad/ # contains all Kicad files
│   │   ├── production/ # contains all output files necessary for uploading to JLCPCB for PCB manufacture and assembly
│   ├── sensor-rigid/     # Rigid base PCB with PCA9546A mux, connector, support circuitry
│   ├── sensor-flex/      # Flex PCB with VCNL4040 sensors (bends to angle sensors outward)
│   └── pcb-sensor/       # DEPRECATED - legacy single-board sensor design, replaced by sensor-rigid + sensor-flex
├── platformio.ini        # PlatformIO configuration

## Annotated Netlist Specification

### Purpose

Raw KiCad schematic files are difficult for AI assistants to interpret correctly. The **annotated netlist** system provides machine-readable circuit data with human-written context explaining the purpose of each component and net.

**Always use annotated netlists** (`*.json` + `*.annotations.yaml`) instead of `.kicad_sch` files when understanding hardware designs.

### File Locations

| PCB | Netlist | Annotations |
|-----|---------|-------------|
| Main PCB | `hardware/pcb-main/kicad/netlists/*.json` | `hardware/pcb-main/kicad/netlists/*.annotations.yaml` |
| Sensor Rigid Base | `hardware/sensor-rigid/sensor-rigid.json` | `hardware/sensor-rigid/sensor-rigid.annotations.yaml` |
| Sensor Flex Strip | `hardware/sensor-flex/sensor-flex.json` | `hardware/sensor-flex/sensor-flex.annotations.yaml` |
| Sensor Legacy (deprecated) | `hardware/pcb-sensor/kicad/netlist/*.json` | N/A - use rigid+flex instead |

### Annotation File Format

```yaml
# example.annotations.yaml
_meta:
  description: "Brief description of the PCB"
  version: "4.0"
  last_synced: "2025-12-15T14:30:00"
  netlist_hash: "abc123"

_status:
  missing_annotations: []   # Components/nets needing description
  archived_count: 0         # Removed items kept for reference

components:
  IC1:
    nickname: "sensor1"     # Short name for code/discussion
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

The plugin preserves all existing annotations when regenerating, only adding placeholders for new components.

## Technical Details

### I2C Multiplexing
The TCA9548A enables multiple VCNL4040 sensors (all with address 0x60) to coexist on the same I2C bus. Features:
- 8 independent I2C channels
- Voltage translation (1.65V to 5.5V)
- Active-low RESET for recovery
- Software-selectable channels via control register

### VCNL4040 Sensor Capabilities
- **Proximity Detection**: IR LED emission and reflection measurement
- **Ambient Light Sensing**: Human eye response approximation
- **Programmable Features**:
  - Integration time
  - Interrupt thresholds
  - LED current control
- **Communication**: I2C up to 400kHz

### Power Management
- USB-C input via DWEII module (5V)
- AP2112K regulates to 3.3V for logic
- Sensor PCBs use 3.3v
- LED power strip uses 5v

## Cloud Infrastructure & Data Collection System

### Overview

The Motion Play system includes a complete cloud-based data collection platform built on AWS. This enables remote control, high-frequency sensor data collection, storage, and visualization for ML training and algorithm development.

**Status**: ✅ Phase 1-3B Complete, Phase 4 in Progress (77% overall)

### AWS Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS Cloud                                 │
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │  IoT Core    │      │   Lambda     │      │  DynamoDB    │ │
│  │   (MQTT)     │─────▶│  Functions   │─────▶│   Tables     │ │
│  └──────┬───────┘      └──────────────┘      └──────────────┘ │
│         │                      ▲                                │
│         │                      │                                │
│         ▼                      │                                │
│  ┌──────────────┐      ┌──────┴───────┐                       │
│  │ IoT Rules    │      │ API Gateway  │                       │
│  │   Engine     │      │   (REST)     │                       │
│  └──────────────┘      └──────┬───────┘                       │
│                                │                                │
└────────────────────────────────┼────────────────────────────────┘
                                 │ HTTPS
                                 ▼
                    ┌────────────────────────┐
                    │   React Web Frontend   │
                    └────────────────────────┘
                                 ▲
         ┌───────────────────────┴────────────────────────┐
         │  WiFi/MQTT (TLS)                               │
         ▼                                                 │
┌────────────────────┐                                    │
│  ESP32-S3 Device   │                                    │
│  ─────────────────│                                    │
│  │ T-Display S3  │ │ Core 1: WiFi/MQTT/Display        │
│  │ VCNL4040 × 6  │ │ Core 0: Sensors (1000 Hz)        │
│  │ PSRAM Buffer  │ │────────────────────────────────────┘
└────────────────────┘
```

### Component Details

#### AWS IoT Core
- **Purpose**: Device connectivity and message routing
- **Authentication**: X.509 certificates (per device)
- **Protocol**: MQTT over TLS 1.2
- **Topics**:
  - `motionplay/{device_id}/commands` - Commands from cloud to device
  - `motionplay/{device_id}/data` - Sensor data from device to cloud
  - `motionplay/{device_id}/status` - Device status updates

#### Lambda Functions

| Function | Trigger | Purpose |
|----------|---------|---------|
| **processData** | IoT Rule (data topic) | Process and store sensor data in DynamoDB |
| **getSessionData** | API Gateway GET | Retrieve session metadata and readings |
| **getSessions** | API Gateway GET | List all sessions with filtering |
| **sendCommand** | API Gateway POST | Send commands to device via IoT Core |
| **updateSession** | API Gateway PATCH | Update session labels/notes |
| **deleteSession** | API Gateway DELETE | Delete session and associated data |
| **processStatus** | IoT Rule (status topic) | Process device status updates |

#### DynamoDB Tables

**MotionPlaySessions** - Session metadata
- Partition Key: `session_id` (String)
- GSI: `DeviceTimeIndex` (device_id, start_timestamp)
- Stores: session metadata, configuration, labels, notes

**MotionPlaySensorData** - Sensor readings
- Partition Key: `session_id` (String)
- Sort Key: `timestamp_offset` (Number) - **Composite timestamp**
- Stores: proximity, ambient light, position, timestamp

**Critical Implementation Detail - Composite Timestamp Key**:
```javascript
// Multiple sensors reading simultaneously need unique keys
timestamp_offset = (timestamp_ms * 10) + sensor_position

// Example: P1S1 at 100ms → (100 * 10) + 0 = 1000
// Example: P1S2 at 100ms → (100 * 10) + 1 = 1001

// Decoding:
actual_timestamp = Math.floor(timestamp_offset / 10)
sensor_position = timestamp_offset % 10
```

This prevents duplicate keys while maintaining sort order. See `infrastructure/DATABASE_SCHEMA.md` for full details.

**MotionPlayDevices** - Device registry
- Partition Key: `device_id` (String)
- Stores: device configuration, last seen, certificate info

#### API Gateway
- **Type**: REST API
- **CORS**: Enabled for local development
- **Endpoints**:
  - `GET /sessions` - List sessions
  - `GET /sessions/{session_id}` - Get session details
  - `GET /sessions/{session_id}/data` - Get sensor readings
  - `POST /command` - Send device command
  - `PATCH /sessions/{session_id}` - Update session
  - `DELETE /sessions/{session_id}` - Delete session

### Data Flow

**Starting a Collection Session**:
1. User clicks "Start Collection" in web interface
2. Frontend → API Gateway → `sendCommand` Lambda
3. Lambda publishes to `motionplay/{device_id}/commands`
4. ESP32 receives command, begins 1000 Hz data collection
5. Data buffered in PSRAM (30,000+ samples)

**Stopping and Uploading**:
1. User clicks "Stop Collection"
2. Same flow as above, but with stop command
3. ESP32 stops collection, publishes batched data
4. IoT Rule triggers `processData` Lambda
5. Lambda processes and stores in DynamoDB
6. Lambda returns session_id to device
7. Frontend polls for new session

**Viewing Data**:
1. Frontend → API Gateway → `getSessionData` Lambda
2. Lambda queries DynamoDB for session + readings
3. Data returned as JSON to frontend
4. Chart.js visualization renders data

### Firmware Architecture (Data Collection)

**Core 0 (High Priority - Time Critical)**:
- Sensor reading loop (1ms cycle time = 1000 Hz)
- I2C communication with VCNL4040 sensors
- Data buffering to PSRAM
- No network operations

**Core 1 (Standard Priority - Asynchronous)**:
- WiFi connection management
- MQTT client operations
- Command processing from cloud
- Display updates (T-Display)
- Batch data transmission

**Data Collection Process**:
1. `START_COLLECTION` command received
2. Core 0 begins tight sensor reading loop
3. Each reading stored in PSRAM circular buffer
4. Buffer capacity: 30,000+ samples (~30 seconds at 1000 Hz)
5. `STOP_COLLECTION` command received
6. Core 1 serializes buffer to JSON
7. Data transmitted in batches via MQTT
8. Buffer cleared, ready for next session

**Key Firmware Components**:
- `SensorManager` - Multi-sensor coordination, I2C multiplexing
- `DataCollectionManager` - High-speed buffering, PSRAM management
- `MQTTManager` - AWS IoT Core connectivity, message handling
- `NetworkManager` - WiFi, certificate management
- `SessionManager` - Session state, command processing
- `DisplayManager` - UI rendering, status display

### Frontend Architecture

**Technology Stack**:
- React 18 with TypeScript
- Vite for build tooling
- Tailwind CSS for styling
- Chart.js for visualization
- Recharts for advanced charting

**Key Components**:
- `SessionList` - Browse and filter sessions
- `SessionChart` - Visualize sensor data (line charts, multi-sensor)
- `SessionConfig` - Configure device and sensor settings
- `Header` - Navigation and status
- `SettingsModal` - Application settings

**Features**:
- Real-time session list updates
- Side-by-side session comparison
- Interactive data visualization (zoom, pan, hover)
- Session labeling and notes
- Data export (JSON, CSV)
- Configuration tracking for ML training
- Device mode control (Idle/Debug/Play)

### MQTT Message Formats

**Command Message** (Cloud → Device):
```json
{
  "command": "START_COLLECTION|STOP_COLLECTION|SET_MODE|CONFIGURE_SENSORS",
  "session_id": "device-001_123456",
  "parameters": {
    "mode": "debug|play|idle",
    "sample_rate": 1000,
    "vcnl4040_config": {
      "led_current": 200,
      "integration_time": 80
    }
  }
}
```

**Data Message** (Device → Cloud):
```json
{
  "device_id": "motionplay-device-001",
  "session_id": "device-001_123456",
  "start_timestamp": 1234567890,
  "sample_rate": 1000,
  "mode": "debug",
  "readings": [
    {
      "timestamp": 0,
      "position": 0,
      "sensor_id": "P1S1",
      "proximity": 551,
      "ambient": 23,
      "white": 15
    }
    // ... more readings
  ],
  "active_sensors": [
    {"position": 0, "sensor_id": "P1S1", "enabled": true}
  ],
  "vcnl4040_config": {
    "led_current": 200,
    "integration_time": 80
  }
}
```

**Status Message** (Device → Cloud):
```json
{
  "device_id": "motionplay-device-001",
  "status": "idle|collecting|uploading|error",
  "wifi_rssi": -45,
  "free_heap": 123456,
  "uptime_ms": 3600000
}
```

### Development & Deployment

**Infrastructure Setup**:
- AWS credentials configured locally
- IoT Core endpoint configured
- Device certificates generated and provisioned
- DynamoDB tables created
- Lambda functions deployed
- API Gateway configured

**Firmware Deployment**:
- Device certificates stored in `firmware/data/certs/`
- WiFi credentials in `firmware/data/config.json`
- Upload via PlatformIO
- Certificates automatically loaded at boot

**Frontend Deployment**:
- Local development: `npm run dev`
- API endpoint configured in environment
- CORS enabled for local testing

**Documentation**:
- Full setup: `infrastructure/aws-setup-guide.md`
- Lambda deployment: `infrastructure/lambda-deployment-guide.md`
- Database schema: `infrastructure/DATABASE_SCHEMA.md`
- Data collection docs: `docs/initiatives/data-collection/`
- Live Debug (curated event capture): `docs/initiatives/live-debug/`

## Terminology

Standard terms used across code, docs, and conversation. When in doubt, use these.

### Hardware

| Term | Definition | Code / Notation |
|------|-----------|-----------------|
| **Sensor Module** | The complete assembly: rigid base + flex strip + enclosure. Three per system, spaced 120° around the hoop. | Module 1 (M1) at 6 o'clock, M2 at 9 o'clock, M3 at 3 o'clock |
| **Rigid Base** | The rigid FR4 PCB with PCA9546A I2C mux and connectors. Mounts in the enclosure. | `hardware/sensor-rigid/` |
| **Flex Strip** | The polyimide flex PCB with both VCNL4040 sensors. Bends to angle sensors ~2° outward. | `hardware/sensor-flex/` |
| **Sensor** | An individual VCNL4040 proximity/ambient light sensor on a flex strip. | Identified by module + side: M1-A, M1-B, etc. In code: `position` (0–5), `pcb_id` (1–3), `side` (1–2) |
| **Side A / Side B** | The two sensors on a module. A (side 1) faces the back of the hoop (-2°). B (side 2) faces the front (+2°). | Notation: P1S1 = Module 1 Side A, P1S2 = Module 1 Side B |

### Data Pipeline

| Term | Definition | Code Reference |
|------|-----------|---------------|
| **Reading** | A single proximity + ambient value from one sensor at one timestamp. The atomic unit of sensor data. | `SensorReading` struct (`SensorManager.h`) |
| **Cycle** | One complete read of all active sensors at the same timestamp. At 500 Hz, one cycle occurs every ~2ms and produces 6 readings. | `SessionSummary.total_cycles` |
| **Wave** | A continuous period where a side's smoothed signal exceeds its adaptive threshold. The signal-level building block of detection. | `WaveTracker`, `WaveState` (`DirectionDetector.h`) |
| **Detection** | The algorithmic conclusion: both sides of a module showed waves within a valid time window, and a direction + confidence have been computed. | `DetectionResult` struct (`DirectionDetector.h`) |
| **Transit** | The physical event of an object passing through the hoop plane. One transit produces readings, which form waves, which yield a detection. | Not yet in code — conceptual term for the real-world event |

### Narrative Flow

A **transit** produces **readings** (grouped into **cycles**). After smoothing, readings form **waves** on each side of a **sensor module**. When both sides show waves within a valid time window, the algorithm produces a **detection** with a direction and confidence score.

---

## Structured System Description

### Physical Architecture

- **Form Factor:**

   - **Hoop diameter:** 500mm (transparent polypropylene tubing, 19mm diameter)
   - **Orientation:** Vertical plane (opening faces horizontally)
   - **Main enclosure:** 85mm × 45mm × 15mm at 6 o'clock position

- **Sensor Placement:**

   - 3 sensor assemblies (rigid+flex pairs) positioned at:
      - Position 1: 6 o'clock (bottom, co-located with main enclosure)
      - Position 2: 9 o'clock (left side)
      - Position 3: 3 o'clock (right side)

   - Rigid base mounts in enclosure; flex strip bends into V-groove
   - Dual sensors per assembly: ~2° angular offset from radial center (achieved via flex PCB bend)

   - "A" sensor: -2° (toward "back" of hoop)
   - "B" sensor: +2° (toward "front" of hoop)
   - Angle provides increased detection window for direction discrimination



- **Detection Principle:**

   Object passing through triggers sequential sensor activation
   Direction determined by A→B vs B→A trigger sequence
   120° spacing provides full coverage of hoop circumference

   See [`docs/detection-algorithm.md`](../docs/detection-algorithm.md) for the full algorithm design, transit scenario catalog, and architectural analysis.

# Sensor PCB Design Specification v5.0
## For Motion Play Detection System (Rigid + Flex Hybrid)

### Overview
The sensor board has been redesigned as a **hybrid rigid + flex** system to improve direction detection:
- **Rigid Base PCB** (`sensor-rigid/`): Contains PCA9546A mux, connector, support circuitry
- **Flex Sensor Strip** (`sensor-flex/`): Contains both VCNL4040 sensors, bends to angle them outward

This design allows the sensors to be angled ~2° away from each other, increasing the time window between sequential sensor triggers and improving direction discrimination for fast-moving objects.

- 3 sensor assemblies per system (addresses 0x70, 0x71, 0x72)
- Mounts in C-shaped enclosure around 19mm diameter tube
- Part of 500mm diameter hoop detection system

### Mechanical Specifications

**Rigid Base PCB:**
- **PCB Type**: Standard rigid FR4, 1.6mm thickness
- **Finish**: HASL or ENIG

**Flex Sensor Strip:**
- **PCB Type**: 2-layer polyimide flex, ~0.11mm core + 0.2mm stiffener = 0.3mm total
- **Dimensions**: ~25mm × 8mm (sensors 10mm apart center-to-center)
- **Bend Zone**: ~5mm center section (unstiffened, flexible)
- **Stiffener Zones**: Sensor areas + connector tail (polyimide stiffener)
- **Finish**: ENIG (required for FPC connector pads)

### Connection Between Rigid and Flex

**ZIF FPC Connector** (on rigid base):
- **LCSC Part**: C132510
- **Type**: 8-pin signal + 2 mechanical, 1.0mm pitch, top contact, slide lock
- **FPC thickness**: 0.3mm

**Pin Order** (optimized for signal integrity):
| Pin | Signal | Purpose |
|-----|--------|---------|
| 1 | 3.3V | Power |
| 2 | INT1 | Interrupt sensor 1 (buffer between power and I2C) |
| 3 | SDA1 | I2C data sensor 1 |
| 4 | SCL1 | I2C clock sensor 1 |
| 5 | GND | Ground (shield between sensor groups) |
| 6 | INT2 | Interrupt sensor 2 (buffer after GND) |
| 7 | SDA2 | I2C data sensor 2 |
| 8 | SCL2 | I2C clock sensor 2 |
| 9 | GND | Mechanical mounting |
| 10 | GND | Mechanical mounting |

### Component Split

**On Rigid Base PCB:**
| Ref | Component | Function |
|-----|-----------|----------|
| U1 | PCA9546APW | I2C mux (controls both sensors) |
| J1 | JST-SH 5-pin | Main connector to main PCB |
| FPC1 | C132510 ZIF | Connection to flex sensor strip |
| R1, R2 | 4.7kΩ | Main I2C pull-ups |
| R6-R9 | 4.7kΩ | Per-sensor I2C pull-ups |
| R3, R12-R14 | 10kΩ | Reset and address pull-ups |
| R5 | 8.2kΩ | INT pull-up |
| D2, D3 | BAT54S | Interrupt combining diodes |
| D1, R4 | LED + 1kΩ | Power indicator |
| C1, C2 | 2.2µF, 0.1µF | Power bypass caps |
| JP3, JP4 | Solder jumpers | Address select (A0, A1) |

**On Flex Sensor Strip:**
| Ref | Component | Function |
|-----|-----------|----------|
| IC1, IC2 | VCNL4040M3OE | Proximity sensors |
| C4, C8 | 2.2µF | LED anode capacitors |
| C6, C7 | 0.1µF | VDD bypass capacitors |

### I2C Addressing (PCA9546A)
Configure via solder jumpers JP3 (A1) and JP4 (A0):
- Board 1: A1=0, A0=0 → Address 0x70
- Board 2: A1=0, A0=1 → Address 0x71
- Board 3: A1=1, A0=0 → Address 0x72

### Interrupt Combining
- Both VCNL4040 INT pins → BAT54S Schottky diodes
- Diode anodes → R5 (8.2kΩ pull-up) → INT output (J1 Pin 5)
- Creates wired-OR configuration

### Flex PCB Design Notes
1. **Bend Zone**: Center ~5mm is unstiffened and bends to create V-shape
2. **Routing in Bend Zone**: Use 0.25mm traces (wider than normal), curved paths, no vias
3. **Traces perpendicular to bend axis** for durability
4. **Components only on stiffened areas** (sensor areas and connector tail)

### Documentation
- **Design rationale**: `docs/initiatives/flex-sensor-pcb/DESIGN_PLAN.md`
- **Flex PCB manufacturing**: `hardware/sensor-flex/FLEX_PCB_SETUP.md`
- **Rigid netlist**: `hardware/sensor-rigid/sensor-rigid.json`


## Development Roadmap

### Phase 0: Setup & Preparation ✅ COMPLETE
- ✅ AWS infrastructure (IoT Core, DynamoDB, Lambda, API Gateway)
- ✅ Development environments (ESP32, React, PlatformIO)
- ✅ Repository structure and documentation
- ✅ Custom PCB design and fabrication

### Phase 1: Basic Connectivity ✅ COMPLETE  
- ✅ Hardware validation (PCB functionality, sensor operation)
- ✅ WiFi connection with certificate management
- ✅ MQTT client with AWS IoT Core
- ✅ TLS communication with device certificates
- ✅ Command processing (ping/pong)
- ✅ Display integration (T-Display S3)

### Phase 2: Data Pipeline ✅ COMPLETE
- ✅ Sensor manager with dual-MUX architecture (TCA→PCA→VCNL4040)
- ✅ High-frequency data collection (1000 Hz)
- ✅ PSRAM buffering (30,000+ samples)
- ✅ Batch MQTT transmission with enhanced metadata
- ✅ Lambda data processing pipeline
- ✅ DynamoDB storage implementation

### Phase 3: Web Interface ✅ COMPLETE
- ✅ API Gateway REST API with CORS
- ✅ React frontend (TypeScript + Tailwind CSS + Vite)
- ✅ Session list and detail views
- ✅ Interactive data visualization (Chart.js)
- ✅ Device control (start/stop collection)
- ✅ Real-time session updates

### Phase 3-B: Enhancements ✅ COMPLETE
- ✅ Session labels and notes
- ✅ Data export (JSON/CSV for ML training)
- ✅ Mode selector (Idle/Debug/Play)
- ✅ Sensor configuration panel
- ✅ Configuration tracking (critical for ML)
- ✅ Advanced filtering and search
- ✅ Side-by-side session comparison

### Phase 4: Integration & Polish 🔄 IN PROGRESS (77% Complete)
- ✅ End-to-end testing
- ✅ Basic error handling and validation
- 🔄 Performance optimization (ongoing)
- 🔄 Security review
- 🔄 Monitoring and logging improvements
- 🔄 Documentation updates

### Phase 5: Detection Algorithms (Future)
- 📋 Sensor calibration and tuning
- 📋 Multi-sensor coordination refinement
- 📋 Movement detection algorithms
- 📋 Direction detection implementation
- 📋 Response time optimization
- 📋 LED feedback system integration

### Phase 6: Advanced Features (In Progress / Future)
- ✅ ML model training pipeline — Python pipeline in `tools/ml-training/` (download, preprocess, train 1D CNN, export TFLite)
- ✅ On-device AI inference — `MLDetector` component using TFLite Micro on ESP32-S3 (float32, ~140ms inference). Selectable via `detection_mode` config. See `docs/initiatives/ml-direction-detection/`
- 📋 Bluetooth mesh networking
- 📋 Multi-device coordination
- 📋 Mobile app development
- 📋 Game mode implementations
- 📋 Training program presets
- 📋 Performance analytics

## AI Development Context

### When Developing for This Project

1. **Component Shorthands** - Use these in code for clarity:
   - `tdisplay` for T-Display-S3
   - `tca` for TCA9548A (main board I2C multiplexer)
   - `pca` for PCA9546A (sensor board local multiplexer)
   - `sensor` for VCNL4040
   - `apk` for AP2112K voltage regulator
   - `dweii` or `power module` for DWEII USB-C module

2. **Critical Hardware Constraints**:
   - **I2C Speed**: Essential for high-frequency sensing (1000 Hz target)
   - **Core Assignment**: Core 0 for sensors (time-critical), Core 1 for networking
   - **PSRAM Required**: 30,000+ sample buffering needs external PSRAM
   - **3.3V Logic**: All I2C and sensor communication
   - **Power Isolation**: Development vs runtime power considerations
   - **Dual MUX Architecture**: TCA→PCA→Sensors requires proper channel selection

3. **Software Architecture**:
   - **Framework**: Arduino (for ESP32 compatibility and libraries)
   - **Build System**: PlatformIO (better dependency management)
   - **Component-Based**: Modular firmware structure in `firmware/src/components/`
   - **Async Communication**: MQTT and WiFi on separate core from sensors

4. **Cloud Integration**:
   - **Authentication**: X.509 certificates (stored in firmware/data/certs/)
   - **MQTT Topics**: Follow pattern `motionplay/{device_id}/{type}`
   - **Message Format**: JSON with specific schema (see Cloud Infrastructure section)
   - **Batch Transmission**: Send data in batches to reduce MQTT overhead
   - **Composite Keys**: DynamoDB uses composite timestamp for uniqueness

5. **Data Collection Best Practices**:
   - **Timestamps**: Use milliseconds since session start (not absolute time)
   - **Configuration Tracking**: Always include sensor config with data for ML training
   - **Session Metadata**: Label and annotate sessions for training datasets
   - **Buffer Management**: Monitor PSRAM usage, prevent overflows
   - **Synchronization**: Coordinate multi-sensor readings for timing accuracy

6. **Documentation Requirements**:
   - **Code Comments**: Explain hardware interactions and timing constraints
   - **Pin Usage**: Track and document GPIO assignments (conflicts with SD/touch)
   - **I2C Addresses**: Document all devices and multiplexer channel mappings
   - **Message Formats**: Keep MQTT schemas documented and versioned
   - **Configuration Changes**: Update both firmware and cloud when changing schemas

7. **Testing Considerations**:
   - **Hardware Testing**: Actual PCB testing required for timing validation
   - **Power Scenarios**: Test with both USB and DWEII power
   - **Network Failures**: Handle WiFi drops and MQTT reconnection
   - **Buffer Edge Cases**: Test at capacity limits (30,000 samples)
   - **Multi-Sensor Timing**: Verify simultaneous sensor reading accuracy

8. **Performance Priorities**:
   - **Sensor Loop**: Must maintain 1ms cycle time (1000 Hz)
   - **I2C Speed**: Optimize for 400kHz Fast Mode
   - **Display Updates**: Balance with sensor performance (don't block Core 0)
   - **MQTT Batching**: Larger batches = fewer transmissions = better efficiency
   - **Memory Management**: PSRAM for data, heap for program state

### Quick Reference

**Repository Structure** (see [manifest.yaml](./manifest.yaml) for full details):
- `firmware/` - ESP32-S3 firmware (C++/Arduino)
- `frontend/` - React web interface (TypeScript)
- `lambda/` - AWS Lambda functions (Node.js)
- `infrastructure/` - AWS setup and deployment docs
- `hardware/` - KiCad schematics and PCB designs
- `docs/references/` - Hardware datasheets and component documentation

**Key Files**:
- `firmware/src/main.cpp` - Main firmware entry point
- `firmware/data/config.json` - Device configuration (WiFi, API endpoint)
- `firmware/data/certs/` - AWS IoT certificates
- `infrastructure/DATABASE_SCHEMA.md` - DynamoDB schema details (composite key!)

**Key Architectural Decisions**:
- **Composite Timestamp Key**: `(timestamp_ms * 10) + sensor_position` - allows multiple sensors to write simultaneously without key collisions
- **Dual-Core Architecture**: Core 0 = sensors (1000 Hz, time-critical), Core 1 = networking (WiFi, MQTT, display)
- **Dual MUX**: TCA9548A (main) → PCA9546A (sensor board) → VCNL4040 - all sensors share address 0x60
- **Cloud Config Source of Truth**: Device fetches sensor config from cloud on boot, frontend is authoritative
- **Session Flow**: Start command → buffer in PSRAM → stop command → batch upload → Lambda processes → DynamoDB

----

*Last Updated: February 18, 2026*
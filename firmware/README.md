# Motion Play Firmware

ESP32-S3 firmware for high-frequency sensor data collection and cloud transmission.

## Architecture Overview

### Dual-Core Design
- **Core 0:** Sensor data collection (1000 Hz) and buffering
- **Core 1:** MQTT communication, display updates, command processing

### Component Structure
```
firmware/src/
├── main.cpp                          # Application entry point, setup, loop
└── components/
    ├── data/                         # Data collection & transmission
    │   ├── DataTransmitter.h/cpp    # Batch MQTT transmission
    │   └── DataBuffer.h/cpp         # PSRAM-based ring buffer
    ├── sensor/                       # Sensor management
    │   ├── SensorManager.h/cpp      # Multi-sensor coordination
    │   ├── SensorConfiguration.h    # Sensor config structure
    │   └── VCNL4040Sensor.h/cpp     # VCNL4040 driver
    ├── mqtt/                         # Cloud communication
    │   └── MQTTManager.h/cpp        # AWS IoT Core client
    └── display/                      # Visual feedback
        └── DisplayManager.h/cpp     # T-Display-S3 interface
```

## Core Components

### `main.cpp`
**Purpose:** Application initialization and coordination

**Key Responsibilities:**
- WiFi connection setup
- MQTT client initialization
- Sensor manager setup
- Command routing (start_collection, stop_collection, set_mode, configure_sensors)
- Display updates

**Global State:**
- `SensorConfiguration currentConfig` - Current sensor settings
- `DataTransmitter* dataTransmitter` - Transmission handler
- `MQTTManager* mqttManager` - MQTT client
- `SensorManager* sensorManager` - Sensor coordinator

### `SensorManager` (sensor/)
**Purpose:** Coordinate multiple VCNL4040 sensors via dual-MUX architecture

**Architecture:**
```
T-Display-S3
    └── TCA9548A (Primary MUX, 0x70)
        ├── Channel 0 → PCA9546A (Secondary MUX, 0x71)
        │   ├── Channel 0 → VCNL4040 (0x60) - PCB 0, Side 1
        │   ├── Channel 1 → VCNL4040 (0x60) - PCB 1, Side 1
        │   └── Channel 2 → VCNL4040 (0x60) - PCB 2, Side 1
        └── Channel 1 → PCA9546A (Secondary MUX, 0x72)
            ├── Channel 0 → VCNL4040 (0x60) - PCB 0, Side 2
            ├── Channel 1 → VCNL4040 (0x60) - PCB 1, Side 2
            └── Channel 2 → VCNL4040 (0x60) - PCB 2, Side 2
```

**Key Methods:**
- `begin()` - Initialize all sensors
- `readAllSensors()` - Read all active sensors
- `calibrateSensors()` - Run calibration routine

**Data Structure:**
```cpp
struct SensorMetadata {
    uint8_t position;      // Sensor index (0-5)
    uint8_t pcb_id;        // PCB number (0-2)
    uint8_t side;          // Side (1 or 2)
    String name;           // Human-readable name
    bool active;           // Sensor active/present
};
```

### `DataTransmitter` (data/)
**Purpose:** Batch sensor readings and transmit via MQTT

**Key Features:**
- Batch transmission (100 readings per message)
- Session metadata included in first batch
- Sensor configuration tracking
- 16KB MQTT buffer support

**Key Methods:**
- `transmitSession()` - Send complete session with metadata
- `transmitBatch()` - Send batch of readings

**JSON Structure:**
```json
{
  "device_id": "motionplay-device-001",
  "session_id": "device-001_12345",
  "start_timestamp": "2025-11-14T10:30:00Z",
  "mode": "debug",
  "sample_rate": 1000,
  "active_sensors": [...],
  "vcnl4040_config": {
    "sample_rate_hz": 1000,
    "led_current": "200mA",
    "integration_time": "1T",
    "high_resolution": true
  },
  "readings": [...]
}
```

### `DataBuffer` (data/)
**Purpose:** PSRAM-based circular buffer for sensor readings

**Capacity:** 30,000+ samples
**Location:** PSRAM (external RAM on ESP32-S3)

**Key Methods:**
- `addReading()` - Add sensor reading
- `getReadings()` - Retrieve batch of readings
- `clear()` - Reset buffer

### `MQTTManager` (mqtt/)
**Purpose:** AWS IoT Core communication with TLS

**Key Features:**
- Certificate-based authentication
- LittleFS certificate storage
- Automatic reconnection
- Command subscription

**Topics:**
- Publish: `motionplay/data/{device_id}`
- Subscribe: `motionplay/commands/{device_id}`

**Key Methods:**
- `connect()` - Connect to AWS IoT Core
- `publish()` - Send message
- `setCallback()` - Register command handler
- `loop()` - Maintain connection

### `SensorConfiguration` (sensor/)
**Purpose:** Track sensor settings for ML training

**Structure:**
```cpp
struct SensorConfiguration {
    uint16_t sample_rate_hz;      // 100-1000 Hz
    String led_current;           // "50mA", "100mA", "200mA"
    String integration_time;      // "1T", "2T", "4T", "8T"
    bool high_resolution;         // 12-bit vs 16-bit
};
```

**Why This Exists:**
Different sensor configurations produce different data characteristics. For ML training, you need to know which settings were used for each dataset to properly normalize and group training data.

### `DisplayManager` (display/)
**Purpose:** T-Display-S3 TFT screen management

**Key Features:**
- Status display (WiFi, MQTT, collection state)
- Real-time sensor readings
- Mode indication (Debug/Play/Idle)

**Key Methods:**
- `showStatus()` - Display connection status
- `showSensorData()` - Display live readings
- `showMessage()` - Show temporary message

## Data Collection Flow

### Session Lifecycle

1. **Idle State**
   - Device connected to AWS IoT Core
   - Listening for commands
   - Display shows "Ready"

2. **Start Collection**
   - Command received: `start_collection`
   - Generate session ID: `{device_id}_{timestamp}`
   - Clear data buffer
   - Start high-frequency sampling (Core 0)
   - Display shows "Collecting..."

3. **Active Collection**
   - Core 0: Read all sensors at 1000 Hz
   - Store readings in PSRAM buffer
   - Core 1: Update display periodically
   - Continue until buffer full or stop command

4. **Stop Collection**
   - Command received: `stop_collection`
   - Stop sampling
   - Transmit all buffered data in batches
   - Include session metadata + sensor config
   - Clear buffer
   - Return to idle

### Command Processing

Commands are received via MQTT on `motionplay/commands/{device_id}`:

**`start_collection`**
```json
{
  "command": "start_collection"
}
```

**`stop_collection`**
```json
{
  "command": "stop_collection"
}
```

**`set_mode`**
```json
{
  "command": "set_mode",
  "mode": "debug"  // or "play", "idle"
}
```

**`configure_sensors`**
```json
{
  "command": "configure_sensors",
  "sensor_config": {
    "sample_rate_hz": 1000,
    "led_current": "200mA",
    "integration_time": "1T",
    "high_resolution": true
  }
}
```

## Configuration

### PlatformIO Configuration (`platformio.ini`)

```ini
[env:lilygo-t-display-s3]
platform = espressif32
board = lilygo-t-display-s3
framework = arduino

monitor_speed = 115200
upload_speed = 921600

board_build.arduino.memory_type = qio_opi
board_build.partitions = default_16MB.csv

lib_deps = 
    knolleary/PubSubClient @ ^2.8
    bblanchon/ArduinoJson @ ^6.21.3
    adafruit/Adafruit VCNL4040 @ ^2.0.3
```

### WiFi & Certificates

Certificates stored in LittleFS:
- `/ca.crt` - AWS IoT Root CA
- `/cert.crt` - Device certificate
- `/private.key` - Private key

**Note:** Certificates must be obtained from AWS IoT Core and uploaded to the device.

## Development Workflow

### Build & Upload
```bash
cd firmware/
pio run -t upload
```

### Monitor Serial Output
```bash
pio device monitor
```

### Clean Build
```bash
pio run -t clean
pio run -t upload
```

## Memory Management

### PSRAM Usage
- **Data Buffer:** ~30,000 samples in PSRAM
- **Benefit:** Offloads large buffers from internal SRAM
- **Access:** Slightly slower than SRAM but sufficient for buffering

### Task Priorities
- **Sensor Task (Core 0):** Priority 1 (highest)
- **MQTT Task (Core 1):** Priority 0 (normal)

## Adding New Components

### 1. Create Component Files
```bash
firmware/src/components/your_component/
├── YourComponent.h
└── YourComponent.cpp
```

### 2. Add to Build
PlatformIO automatically includes all `.cpp` files in `src/`.

### 3. Include in main.cpp
```cpp
#include "components/your_component/YourComponent.h"
```

### 4. Initialize in setup()
```cpp
void setup() {
    // ... existing setup ...
    yourComponent = new YourComponent();
    yourComponent->begin();
}
```

## Debugging Tips

### Check Serial Output
Most components log to Serial at 115200 baud. Look for:
- `[WiFi]` - Connection status
- `[MQTT]` - Cloud communication
- `[Sensor]` - Sensor readings
- `[Data]` - Transmission status

### Common Issues

**Sensors Not Found:**
- Check I2C connections
- Verify MUX addresses (0x70, 0x71, 0x72)
- Run I2C scanner

**MQTT Not Connecting:**
- Verify WiFi connection
- Check certificates in LittleFS
- Confirm AWS IoT endpoint in code

**Data Not Transmitting:**
- Check MQTT buffer size (16KB)
- Verify topic permissions in AWS IoT policy
- Monitor AWS IoT Core test client

**High Frequency Sampling Issues:**
- Ensure sensors on Core 0
- Check task priorities
- Verify PSRAM availability

## Key Constants

```cpp
#define SAMPLE_RATE_HZ 1000
#define BUFFER_SIZE 30000
#define MQTT_BUFFER_SIZE 16384
#define BATCH_SIZE 100
```

## Device Modes

- **Idle:** Minimal operation, ready for commands
- **Debug:** Full logging, 1000 Hz collection, detailed display
- **Play:** Optimized for game use, minimal logging, LED feedback

## Further Reading

- **Project Context:** [.context/PROJECT.md](../.context/PROJECT.md)
- **AWS Setup:** `infrastructure/aws-setup-guide.md`
- **Sensor Datasheets:** `docs/references/vcnl4040/`

---

*Last Updated: December 5, 2025*


# Firmware Context

ESP32-S3 firmware for the Motion Play sensor system. Built with Arduino framework on PlatformIO.

> See `firmware/README.md` for component-level API documentation, data structures, and debugging tips.

## Dual-Core Architecture

- **Core 0 (High Priority):** Sensor data collection at up to 1000 Hz. I2C communication with VCNL4040 sensors via dual-MUX chain. Data buffering to PSRAM. No network operations on this core.
- **Core 1 (Standard Priority):** WiFi connection management, MQTT client operations, command processing from cloud, display updates (T-Display-S3), batch data transmission.

## Key Components

| Component | Location | Purpose |
|-----------|----------|---------|
| `SensorManager` | `components/sensor/` | Multi-sensor coordination, I2C multiplexing via TCA→PCA→VCNL4040 chain |
| `DataBuffer` | `components/data/` | PSRAM-based ring buffer (30,000+ samples) |
| `DataTransmitter` | `components/data/` | Batch MQTT transmission to AWS IoT Core |
| `MQTTManager` | `components/mqtt/` | AWS IoT Core connectivity (TLS, X.509 certs) |
| `NetworkManager` | `components/network/` | WiFi, certificate management |
| `SessionManager` | `components/session/` | Session state, command processing |
| `DisplayManager` | `components/display/` | T-Display-S3 UI rendering |
| `DirectionDetector` | `components/detection/` | Wave-based detection algorithm (adaptive thresholds, per-module tracking) |
| `MLDetector` | `components/detection/` | TFLite Micro 1D CNN for on-device direction inference |

## Software Stack

- **Framework**: Arduino
- **Platform**: PlatformIO
- **Board**: ESP32-S3 (LilyGO T-Display-S3)

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

### Build Configuration
```ini
monitor_speed = 115200
upload_speed = 921600
board_build.flash_mode = qio
board_build.f_cpu = 240000000L
board_build.f_flash = 80000000L
```

**Critical TFT_eSPI build flags** — The T-Display-S3 requires a custom `User_Setup.h` (in `firmware/include/`) to configure the ST7789 driver with 8-bit parallel interface and correct pin mappings:
```ini
-DUSER_SETUP_LOADED
-include firmware/include/User_Setup.h
```
Without these, TFT_eSPI falls back to its default ILI9341 SPI configuration, resulting in a black screen.

## Pin Configuration

**T-Display-S3 GPIO Assignments:**

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

**Display Interface (Parallel 8-bit):** Data: GPIO 39-42, 45-48 (D0-D7). Control: GPIO 5-9 (RES, CS, DC, WR, RD). Backlight: GPIO 38.

**Pin Conflicts:** GPIO 16 used for LED strip (touch interrupt disabled). GPIO 10-13 used for Motion Play hardware (SD card disabled).

## Power Management

### Power Flow
- DWEII USB-C module → +5V rail → Main PCB components
- +5V → AP2112K regulator → +3.3V rail → Sensors, TCA9548A
- +5V → LED strip (directly)
- +5V → T-Display via pin 12 (5V pin)

### Power Isolation Challenge

The T-Display's 5V pin (pin 12) is bidirectional. When powered via USB for programming, it back-feeds 5V to the main PCB's +5V rail. USB power (500-900mA) is insufficient for the LED strip (up to 4-5A), risking brown-outs or damage.

The T-Display's 3.3V output pins are disconnected from the main PCB, but the 5V connection remains necessary for normal operation.

### Development Cable Workflow

**For Code Upload:**
1. Disconnect Cable A (DWEII power)
2. Connect Cable B (MacBook) directly to T-Display USB-C
3. Upload via PlatformIO

**For Testing (after upload):**
1. Disconnect Cable B from T-Display
2. Install data-only adapter onto Cable B
3. Reconnect Cable B (with adapter) for serial monitoring only
4. Connect Cable A to DWEII module for main power
5. Open serial monitor

**Why the data-only adapter?** Prevents power conflicts between MacBook USB and DWEII module. Without it: competing 5V sources through T-Display pin 12.

**Safety:** Always have DWEII power connected before LEDs initialize. Never rely on USB power for LED strip operation.

## Serial Studio

Serial Studio is a standalone desktop app for real-time sensor visualization. It provides live plotting of all 6 sensor channels plus algorithm internals without needing the full cloud pipeline.

**Enabling:** Set `-DSERIAL_STUDIO_DEFAULT=true` in `platformio.ini`, build and flash. Can also be toggled at runtime via cloud config (`serial_studio_enabled`).

**Dashboard files:** `tools/serial-studio/`
- `motion-play-v10.json` — Main dashboard: per-module sensor graphs, detection summary, rates & config
- `motion-play-v9-sensors.json` — Sensor comparison dashboard: per-module plus overlay graphs

**Important notes:**
- Close PlatformIO serial monitor before connecting Serial Studio (only one app can hold the serial port)
- Set `SERIAL_STUDIO_DEFAULT` back to `false` when not using Serial Studio
- Dashboard files get overwritten by Serial Studio on disk — always create new versioned files when updating
- **Transit speed estimation:** Configure `ball_diameter_mm` (default: 190) and `hoop_inner_diameter_mm` (default: 450) via cloud config
- **Transit calculator:** `python3 tools/transit-calculator.py --help`
- **Dual rate display:** Sensor Rate (from IT × duty cycle) vs Poll Rate (measured I2C reads/sec). Sensor rate is always the bottleneck.

See `docs/initiatives/serial-studio/` for full technical details.

## Performance Constraints

- **Sensor Loop:** Must maintain ≤1ms cycle time (1000 Hz)
- **I2C Speed:** 400kHz Fast Mode, optimized for dual-MUX chain
- **PSRAM Required:** 30,000+ sample buffering needs external PSRAM
- **3.3V Logic:** All I2C and sensor communication
- **Display Updates:** Must not block Core 0
- **MQTT Batching:** Larger batches = fewer transmissions = better efficiency

## Data Conventions

- **Timestamps**: Use milliseconds since session start (not absolute time)
- **Configuration tracking**: Always include sensor config with data — critical for ML training
- **Buffer management**: Monitor PSRAM usage, prevent overflows

## Data Collection Flow

1. `START_COLLECTION` command received via MQTT
2. Core 0 begins tight sensor reading loop (1ms cycle)
3. Each reading stored in PSRAM circular buffer
4. Buffer capacity: 30,000+ samples (~30 seconds at 1000 Hz)
5. `STOP_COLLECTION` command received
6. Core 1 serializes buffer to JSON
7. Data transmitted in batches via MQTT
8. Buffer cleared, ready for next session

---

*Last Updated: March 4, 2026*

# Motion Play

A sensor-based system for detecting and tracking fast-moving objects through a plane, with LED feedback and wireless connectivity capabilities.

## Overview

Motion Play is an ESP32-based system that uses proximity sensors to detect and track fast-moving objects through a detection plane. The system can determine the direction of movement and provide visual feedback through LED lights. Multiple units can be networked together via Bluetooth, and the system can connect to WiFi networks or directly to a mobile device. This system is designed for games and sports performance training applications.

## Hardware Components

- **Main Controller**: LilyGO T-Display-S3
- **I2C Multiplexer**: TCA9548A
- **Sensors**: VCNL4040 Proximity and Ambient Light Sensors

### Hardware Setup

- T-Display-S3 SDA/SCL pins → TCA9548A
- TCA9548A Channels:
  - Channel 0: Sensor #1
  - Channel 1: Sensor #2
  - Channels 2-7: Available for expansion

## Software Requirements

- PlatformIO
- Arduino Framework
- ESP32 Board Support Package

## Dependencies

- TFT_eSPI (^2.5.31)
- Adafruit BusIO (^1.14.5)
- Adafruit ADS1X15 (^2.4.0)

## Building and Uploading

1. Install PlatformIO
2. Clone this repository
3. Open the project in your IDE
4. Build and upload to your device

## Configuration

The project uses the following configuration:
- Monitor speed: 115200 baud
- Upload speed: 921600 baud
- Flash mode: QIO
- CPU frequency: 240MHz
- Flash frequency: 80MHz

## Project Structure

- `.context/`: Project documentation and reference materials
  - `datasheets/`: Component datasheets
- `src/`: Source code directory
- `platformio.ini`: PlatformIO configuration file

## Future Development

- Mobile app interface
- Multi-device synchronization
- Game modes and training programs
- Additional sensor support

## License

[Add your license information here]

## Contributing

[Add contribution guidelines here]


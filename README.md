# Motion Play Project Documentation

## Overview

Motion Play is an ESP32-based sensor system for detecting and tracking fast-moving objects through a detection plane. The system determines movement direction and provides visual feedback through LED lights. Multiple units can be networked via Bluetooth, and the system supports WiFi connectivity for mobile device integration. Designed for games and sports performance training applications.

## Current Project Status

**Hardware:** Custom PCBs fabricated and assembled
**Software:** Basic test code uploaded, display showing sensor readings
**Testing Phase:** Verifying PCB functionality and sensor operation

## Hardware Architecture

### Custom PCBs

1. **Main PCB** - Houses:
   - T-Display-S3 (ESP32 development board)
   - TCA9548A I2C multiplexer
   - AMS1117 3.3V voltage regulator
   - DWEII USB-C power module
   - Supporting components (resistors, diodes, connectors)

2. **Sensor PCB** (Flexible) - Contains:
   - VCNL4040 proximity/ambient light sensor
   - Power connector (3.3V)
   - Signal connectors (SDA, SCL, INT)
   - Daisy-chain power connector (reduces wiring from main PCB)

The main PCB supports up to 6 sensor PCBs.

### Core Components

| Component | Part Number | Function | Shorthand |
|-----------|------------|----------|-----------|
| Main Controller | LilyGO T-Display-S3 | ESP32-S3 with built-in display | `tdisplay` |
| I2C Multiplexer | TCA9548A | 8-channel I2C switch | `tca` |
| Sensors | VCNL4040 | Proximity & ambient light sensing | `sensor` |
| Voltage Regulator | AMS1117-3.3 | 3.3V 1A LDO regulator | - |
| Power Module | DWEII USB-C | USB-C power input | - |

### Hardware Connections


T-Display-S3 (I2C Master)
    ├── SDA ───→ TCA9548A SDA
    └── SCL ───→ TCA9548A SCL
    
TCA9548A Channels:
    ├── Channel 0 (SC0/SD0) → Sensor #1 (VCNL4040)
    ├── Channel 1 (SC1/SD1) → Sensor #2 (VCNL4040)
    └── Channels 2-7 → Available for expansion


### Pin Configuration

- **T-Display-S3 I2C**: Default SDA/SCL pins
- **TCA9548A Address**: 0x70 (default, configurable via A0-A2)
- **VCNL4040 Address**: 0x60 (fixed)

## Software Stack

### Development Environment
- **Framework**: Arduino
- **Platform**: PlatformIO
- **Board**: ESP32-S3

### Dependencies
ini
lib_deps = 
    TFT_eSPI @ ^2.5.31
    Adafruit BusIO @ ^1.14.5
    Adafruit ADS1X15 @ ^2.4.0


### Configuration Parameters

monitor_speed = 115200
upload_speed = 921600
board_build.flash_mode = qio
board_build.f_cpu = 240000000L
board_build.f_flash = 80000000L

## Building and Deployment

1. **Prerequisites**
   - Install PlatformIO (VS Code extension or CLI)
   - Install CP210x USB drivers if needed

2. **Setup**
   ```bash
   git clone [repository]
   cd motion-play
   ```

3. **Build & Upload**
   ```bash
   pio run -t upload
   ```

4. **Monitor Serial Output**
   ```bash
   pio device monitor
   ```

## Project Structure

motion-play/
├── .context/               # Project documentation
│   ├── datasheets/        # Component datasheets
│   │   ├── TCA9548A.pdf
│   │   ├── VCNL4040.pdf
│   │   ├── AMS1117-3.3.pdf
│   │   ├── DWEII_Power_Module.pdf
│   │   └── T_Display_S3.pdf
│   └── schematics/        # PCB designs
│       ├── mpv3-main-schematic.pdf
│       ├── mpv3-main-pcb.pdf
│       ├── mpv3-sensor-schematic.pdf
│       └── mpv3-sensor-pcb.pdf
├── src/                   # Source code
│   └── main.cpp          # Main application
├── platformio.ini        # PlatformIO configuration
└── README.md            # This document

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
- AMS1117 regulates to 3.3V for logic
- Separate power distribution to sensor PCBs
- Daisy-chain capability reduces cable complexity

## Development Roadmap

### Phase 1: Hardware Validation ✓
- PCB fabrication and assembly
- Basic connectivity testing
- Display integration

### Phase 2: Core Functionality (Current)
- Sensor calibration
- Multi-sensor coordination
- Movement detection algorithms

### Phase 3: Enhanced Features
- LED feedback system
- Direction detection refinement
- Response time optimization

### Phase 4: Connectivity
- Bluetooth mesh networking
- WiFi configuration portal
- Mobile app development

### Phase 5: Applications
- Game mode implementations
- Training program presets
- Performance analytics
- Data logging and export

## Troubleshooting

### Common Issues

1. **TCA9548A Not Found**
   - Check I2C connections
   - Verify pull-up resistors (2.2kΩ)
   - Scan I2C bus for address conflicts

2. **VCNL4040 Not Responding**
   - Ensure TCA9548A channel selection
   - Check sensor PCB connections
   - Verify 3.3V power supply

3. **Display Issues**
   - Confirm TFT_eSPI configuration
   - Check display backlight pin
   - Verify SPI connections

## AI Development Context

When developing for this project:

1. **Use component shorthands** in code for clarity:
   - `tdisplay` for T-Display-S3
   - `tca` for TCA9548A
   - `sensor` for VCNL4040

2. **Consider hardware constraints**:
   - I2C multiplexing required for multiple sensors
   - 3.3V logic levels throughout
   - Display update rate vs sensor polling balance

3. **Maintain compatibility**:
   - Arduino framework conventions
   - PlatformIO project structure
   - Existing pin assignments

4. **Document changes**:
   - Update this file with new features
   - Comment code thoroughly
   - Track pin usage and I2C addresses

## Contributing

When contributing to this project:
- Follow existing code style
- Test on actual hardware when possible
- Update documentation for new features
- Consider power consumption impacts
- Maintain backward compatibility

## License

[Specify your license here]

## Support

For questions or issues:
- Check troubleshooting section
- Review component datasheets in `.context/datasheets/`
- Consult PCB schematics in `.context/schematics/`

---

*Last Updated: [Current Date]*
*Build Info: Accessible via `__DATE__` and `__TIME__` macros in code*
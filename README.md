# Motion Play Project Documentation

## Overview

Motion Play is an ESP32-based sensor system for detecting and tracking fast-moving objects through a detection plane. The system determines movement direction and provides visual feedback through LED lights. Multiple units can be networked via Bluetooth, and the system supports WiFi connectivity for mobile device integration. Designed for games and sports performance training applications.

## Current Project Status

**Hardware:** ✅ Custom PCBs operational with dual-MUX architecture (TCA→PCA→Sensors)
**Firmware:** ✅ Full data collection pipeline (1000 Hz, PSRAM buffering, MQTT transmission)
**Backend:** ✅ AWS IoT Core + Lambda + DynamoDB + API Gateway
**Frontend:** ✅ React web interface with real-time visualization and device control
**Current Phase:** Phase 4 - Integration & Polish (77% complete overall)

📊 **For detailed status:** See `docs/data collection/PROJECT_STATUS.md`

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

## System Architecture

### Data Collection System
The Motion Play system collects high-frequency sensor data for ML training:

1. **Device Layer** (ESP32)
   - 1000 Hz data collection from VCNL4040 sensors
   - PSRAM buffering (30,000+ samples)
   - Batch transmission via MQTT

2. **Cloud Layer** (AWS)
   - IoT Core: Device connectivity and command routing
   - Lambda: Data processing and API logic
   - DynamoDB: Session metadata and sensor readings
   - API Gateway: REST API for web interface

3. **Frontend Layer** (React)
   - Session management and visualization
   - Device control (start/stop, mode selection)
   - Data export for ML training
   - Configuration tracking

### Web Interface
Access at: `https://[api-gateway-url]/prod`

Features:
- Real-time session list with filtering
- Interactive charts (side-by-side comparison)
- Label and annotate sessions
- Export data (JSON/CSV)
- Configure sensors (sample rate, LED current, etc.)
- Track configuration for ML training

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
├── docs/                      # Project documentation
│   ├── data collection/      # Data collection system docs
│   │   ├── PROJECT_STATUS.md
│   │   ├── IMPLEMENTATION_GUIDE.md
│   │   ├── phase1-connectivity-guide.md
│   │   ├── phase2-data-pipeline-guide.md
│   │   ├── phase3-web-interface-guide.md
│   │   └── phase3-b-enhancements-guide.md
│   └── DEVELOPMENT_PLAN.md
├── firmware/                  # ESP32 firmware
│   ├── src/
│   │   ├── main.cpp
│   │   └── components/       # Modular firmware components
│   │       ├── data/         # Data collection & transmission
│   │       ├── mqtt/         # MQTT client
│   │       ├── sensor/       # Sensor management
│   │       └── display/      # TFT display
│   └── platformio.ini
├── frontend/                  # React web interface
│   └── motion-play-ui/
│       ├── src/
│       │   ├── components/   # React components
│       │   ├── services/     # API client
│       │   └── App.tsx
│       └── package.json
├── lambda/                    # AWS Lambda functions
│   ├── processData/          # Process sensor data
│   ├── getSessionData/       # Retrieve sessions
│   ├── sendCommand/          # Send device commands
│   └── updateSession/        # Update session metadata
├── infrastructure/            # AWS infrastructure
│   └── aws-setup-guide.md
├── .context/                  # Hardware documentation
│   ├── datasheets/           # Component datasheets
│   └── schematics/           # PCB designs
└── README.md                 # This document

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

### Phase 0: Setup & Preparation ✅ COMPLETE
- AWS infrastructure (IoT Core, DynamoDB, Lambda)
- Development environments (ESP32, React, PlatformIO)
- Repository structure and documentation

### Phase 1: Basic Connectivity ✅ COMPLETE
- WiFi connection with certificate management
- MQTT client with AWS IoT Core
- TLS communication with device certificates
- Command processing (ping/pong)

### Phase 2: Data Pipeline ✅ COMPLETE
- Sensor manager with dual-MUX architecture (TCA→PCA→VCNL4040)
- High-frequency data collection (1000 Hz)
- PSRAM buffering (30,000+ samples)
- Batch MQTT transmission with enhanced metadata
- Lambda processing to DynamoDB

### Phase 3: Web Interface ✅ COMPLETE
- API Gateway REST API with CORS
- React frontend (TypeScript + Tailwind CSS)
- Session list and detail views
- Interactive data visualization
- Device control (start/stop collection)

### Phase 3-B: Enhancements ✅ COMPLETE
- Session labels and notes
- Data export (JSON/CSV for ML training)
- Mode selector (Idle/Debug/Play)
- Sensor configuration panel
- Configuration tracking (critical for ML)
- Advanced filtering

### Phase 4: Integration & Polish (Current)
- End-to-end testing
- Error handling and validation
- Performance optimization
- Security review
- Monitoring and logging

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

## Documentation

### Getting Started
- `QUICK_START_GUIDE.md` - Quick setup reference
- `docs/data collection/IMPLEMENTATION_GUIDE.md` - Detailed walkthrough
- `docs/data collection/PROJECT_STATUS.md` - Current progress (77% complete)

### Phase Guides (Step-by-Step)
- `docs/data collection/phase1-connectivity-guide.md` - WiFi + MQTT
- `docs/data collection/phase2-data-pipeline-guide.md` - Sensors + Data
- `docs/data collection/phase3-web-interface-guide.md` - API + Frontend
- `docs/data collection/phase3-b-enhancements-guide.md` - Enhancements

### Planning & Design
- `docs/data collection/implementation_plan.md` - Full implementation plan
- `docs/data collection/technical_design_doc.md` - Design decisions
- `docs/data collection/tech_reqs.md` - Technical requirements

### Hardware Documentation
- `.context/datasheets/` - Component datasheets (TCA9548A, VCNL4040, etc.)
- `.context/schematics/` - PCB designs (Main PCB, Sensor PCB)

## Support

For questions or issues:
- Check troubleshooting section above
- Review phase guides for detailed implementation steps
- Consult `docs/data collection/PROJECT_STATUS.md` for current status
- Review component datasheets in `.context/datasheets/`
- Consult PCB schematics in `.context/schematics/`

---

*Last Updated: November 14, 2025*
*Build Info: Accessible via `__DATE__` and `__TIME__` macros in code*
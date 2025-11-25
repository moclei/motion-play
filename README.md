# Motion Play Project Documentation

## Overview

Motion Play is an ESP32-based sensor system for detecting and tracking fast-moving objects through a detection plane. The system determines movement direction and provides visual feedback through LED lights. Multiple units can be networked via Bluetooth, and the system supports WiFi connectivity for mobile device integration. Designed for games and sports performance training applications.

## Current Project Status

**Hardware:** ✅ Custom PCBs operational with dual-MUX architecture (TCA→PCA→Sensors)
**Firmware:** ✅ Full data collection pipeline (1000 Hz, PSRAM buffering, MQTT transmission)
**Backend:** ✅ AWS IoT Core + Lambda + DynamoDB + API Gateway
**Frontend:** ✅ React web interface with real-time visualization and device control
**Current Phase:** Phase 4 - Integration & Polish (77% complete overall)

### 📚 Documentation

- **Documentation Guide**: [DOCUMENTATION.md](DOCUMENTATION.md) - How documentation is organized
- **Documentation Index**: [docs/INDEX.md](docs/INDEX.md) - Master index of all documentation
- **Technical Reference**: [.context/PROJECT.md](.context/PROJECT.md) - Comprehensive technical details for AI assistants
- **Getting Started**: [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) - Quick setup guide

### 📍 Key Project Documents

- **Data Collection Initiative**: [docs/initiatives/data-collection/](docs/initiatives/data-collection/) - Full documentation for data collection system
- **Project Status**: [docs/initiatives/data-collection/PROJECT_STATUS.md](docs/initiatives/data-collection/PROJECT_STATUS.md) - Current implementation status
- **Database Schema**: [infrastructure/DATABASE_SCHEMA.md](infrastructure/DATABASE_SCHEMA.md) ⚠️ Read this for composite key details
- **Lambda Functions**: [lambda/README.md](lambda/README.md)
- **Deployment Guide**: [infrastructure/lambda-deployment-guide.md](infrastructure/lambda-deployment-guide.md)

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

The T-Display-S3 connects to multiple VCNL4040 sensors via the TCA9548A I2C multiplexer. The main PCB supports up to 6 sensor PCBs, each with dual sensors managed by a local PCA9546A multiplexer.

> **For detailed pin configurations, I2C addressing, and connection diagrams**, see [.context/PROJECT.md](.context/PROJECT.md)

## Software Stack

- **Framework**: Arduino
- **Platform**: PlatformIO
- **Board**: ESP32-S3
- **Key Libraries**: TFT_eSPI, Adafruit BusIO, AWS IoT SDK

> **For complete configuration details and dependencies**, see [firmware/README.md](firmware/README.md) and [.context/PROJECT.md](.context/PROJECT.md)

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

```
motion-play/                   # Monorepo root
├── docs/                      # Project documentation
│   ├── INDEX.md              # Master documentation index
│   ├── initiatives/          # Cross-cutting features
│   │   └── data-collection/  # Data collection system
│   │       ├── README.md     # Initiative overview
│   │       ├── guides/       # Implementation guides
│   │       └── work/         # Ephemeral working docs
│   ├── references/           # Hardware datasheets & vendor docs
│   │   ├── vcnl4040/        # Sensor documentation
│   │   └── i2c-multiplexer/ # Multiplexer docs
│   └── archive/             # Historical documentation
├── firmware/                 # ESP32-S3 firmware
│   ├── src/
│   │   ├── main.cpp
│   │   └── components/      # Modular components
│   │       ├── data/        # Data collection & transmission
│   │       ├── mqtt/        # MQTT client
│   │       ├── sensor/      # Sensor management
│   │       ├── network/     # WiFi & connectivity
│   │       ├── session/     # Session management
│   │       └── display/     # TFT display UI
│   └── README.md            # Firmware documentation
├── frontend/                # React web interface
│   └── motion-play-ui/
│       ├── src/
│       │   ├── components/  # React components
│       │   ├── services/    # API client
│       │   └── App.tsx
│       └── README.md        # Frontend documentation
├── lambda/                  # AWS Lambda functions
│   ├── processData/         # Process sensor data
│   ├── getSessionData/      # Retrieve sessions
│   ├── sendCommand/         # Send device commands
│   └── updateSession/       # Update session metadata
├── infrastructure/          # AWS infrastructure
│   ├── aws-setup-guide.md
│   ├── lambda-deployment-guide.md
│   └── DATABASE_SCHEMA.md
├── hardware/                # PCB designs & schematics
│   ├── pcb-main/           # Main controller board
│   ├── pcb-sensor/         # Sensor boards
│   └── components/         # Component libraries
├── .context/               # AI assistant context
│   └── PROJECT.md          # Comprehensive technical reference
├── DOCUMENTATION.md        # Documentation guide
├── README.md               # This document (project overview)
└── QUICK_START_GUIDE.md    # Quick setup guide
```

## Technical Highlights

- **I2C Multiplexing**: TCA9548A enables multiple sensors with the same address to coexist on one bus
- **Sensors**: VCNL4040 proximity/ambient light sensors with programmable detection thresholds
- **Power**: USB-C 5V input, regulated to 3.3V for logic and sensors
- **Data Rate**: 1000 Hz sensor sampling with PSRAM buffering

> **For complete technical specifications, pin configurations, and power management details**, see [.context/PROJECT.md](.context/PROJECT.md)

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

For common issues (I2C connection problems, sensor not responding, display issues), see:
- [.context/PROJECT.md](.context/PROJECT.md) - Comprehensive troubleshooting guide
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) - Setup and deployment issues
- [docs/INDEX.md](docs/INDEX.md) - Find specific technical documentation

## Contributing

When contributing to this project:
- Follow existing code style
- Test on actual hardware when possible
- Update documentation for new features
- Consider power consumption impacts
- Maintain backward compatibility

## License

[Specify your license here]

## Additional Documentation

### Getting Started
- [QUICK_START_GUIDE.md](QUICK_START_GUIDE.md) - Quick setup reference
- [DOCUMENTATION.md](DOCUMENTATION.md) - How documentation is organized
- [docs/INDEX.md](docs/INDEX.md) - Master documentation index

### Data Collection System
- [Initiative Overview](docs/initiatives/data-collection/README.md) - Data collection system overview
- [Project Status](docs/initiatives/data-collection/PROJECT_STATUS.md) - Current progress (77% complete)
- [Implementation Guides](docs/initiatives/data-collection/guides/) - Step-by-step phase guides

### Technical Reference
- [.context/PROJECT.md](.context/PROJECT.md) - Comprehensive technical reference for AI assistants
- [docs/references/](docs/references/) - Hardware component documentation and datasheets

## Support

For questions or issues:
- Check troubleshooting section above
- Review [DOCUMENTATION.md](DOCUMENTATION.md) to find relevant documentation
- Consult [docs/INDEX.md](docs/INDEX.md) for master documentation index
- Check [Data Collection Project Status](docs/initiatives/data-collection/PROJECT_STATUS.md)
- Review component datasheets in [docs/references/](docs/references/)
- See [.context/PROJECT.md](.context/PROJECT.md) for comprehensive technical reference

---

*Last Updated: November 21, 2025*
*Build Info: Accessible via `__DATE__` and `__TIME__` macros in code*
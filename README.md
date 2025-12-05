# Motion Play

ESP32-based sensor system for detecting and tracking fast-moving objects through a detection plane. Designed for games and sports performance training.

## Project Status

**Phase 4 - Integration & Polish** (77% complete)

- ✅ Custom PCBs with dual-MUX sensor architecture
- ✅ 1000 Hz data collection with PSRAM buffering
- ✅ AWS IoT Core + Lambda + DynamoDB backend
- ✅ React web interface with visualization and device control
- 🔄 Testing, optimization, documentation

## Repository Structure

```
motion-play/
├── .context/           # AI context documentation (start here)
│   ├── PROJECT.md      # Comprehensive project context
│   ├── manifest.yaml   # Structured metadata
│   └── IDEAS.md        # Feature backlog
├── firmware/           # ESP32-S3 firmware (PlatformIO/Arduino)
├── frontend/           # React web interface
├── lambda/             # AWS Lambda functions
├── infrastructure/     # AWS setup and deployment
├── hardware/           # KiCad PCB designs
└── docs/references/    # Hardware datasheets
```

## Quick Start

```bash
# Firmware
cd firmware && pio run -t upload

# Frontend
cd frontend/motion-play-ui && npm install && npm run dev
```

## Documentation

**For AI assistants and detailed context**: See [`.context/PROJECT.md`](.context/PROJECT.md)

**Hardware reference materials**: See [`docs/references/`](docs/references/)

## Hardware

- **MCU**: LilyGO T-Display-S3 (ESP32-S3)
- **Sensors**: 6× VCNL4040 proximity sensors (3 boards × 2 sensors)
- **Architecture**: TCA9548A → PCA9546A → VCNL4040 (dual I2C multiplexing)

## License

[TBD]

# Motion Play Development Plan v2.0
## Complete System Rebuild with Vetted Libraries

### Overview
This document outlines the step-by-step approach to rebuild the Motion Play firmware from scratch using established, vetted libraries. The goal is to create a robust, maintainable codebase that properly interfaces with all hardware components.

## Hardware Architecture Review

### Current PCB Design (v4/v5):
- **Main PCB**: T-Display-S3, TCA9548A (0x70), AP2112K-3.3V regulator, DWEII power module
- **Sensor PCBs**: 3 boards, each with PCA9546A + 2x VCNL4040 sensors
- **Addressing**: 
  - TCA9548A channels 0-2 → Sensor boards 1-3
  - Each sensor board: PCA9546A at 0x70/0x71/0x72
  - VCNL4040 sensors: always at 0x60 (multiplexed)

## Library Requirements & Status

### ✅ Already Configured (in platformio.ini):
```ini
lib_deps =
    bodmer/TFT_eSPI@^2.5.31           # T-Display-S3 screen
    adafruit/Adafruit BusIO@^1.14.5   # I2C foundation
    adafruit/Adafruit VCNL4040@^1.1.4 # Proximity sensors
```

### 🔄 Need to Add:
```ini
# Add these to lib_deps:
    adafruit/Adafruit TCA9548A@^1.0.1  # Main I2C multiplexer
```

### 📝 PCA9546A Handling:
- **No dedicated Adafruit library exists**
- **Solution**: Use basic I2C Wire commands (similar to TCA9548A protocol)
- **Alternative**: Create lightweight wrapper class

## Development Phases

### Phase 1: Foundation & Display ✅ **COMPLETED**
**Objective**: Verify basic hardware functionality  
**Completion Date**: October 4, 2025
- [x] Archive current main.cpp → `archive/main_old_v3.cpp`
- [x] Create minimal new main.cpp
- [x] Test T-Display-S3 initialization
- [x] Display build info and system status
- [x] Implement basic terminal/logging system
- [x] Test button navigation

**Success Criteria**: ✅ Display shows "Motion Play v2.0" with build timestamp

### Phase 2: I2C Bus & TCA9548A 🔌 **CURRENT PHASE**
**Objective**: Establish main I2C multiplexer communication  
**Status**: Ready to begin
- [x] Update platformio.ini with TCA9548A library (robtillaart/TCA9548)
- [x] Initialize I2C bus (GPIO 43/44 pins configured)
- [ ] Scan I2C bus for devices
- [ ] Initialize TCA9548 library
- [ ] Test channel switching (channels 0-2)
- [ ] Verify each channel can be selected/deselected

**Success Criteria**: Can detect TCA9548A at 0x70 and switch between channels

### Phase 3: PCA9546A Communication 🔀
**Objective**: Connect to sensor board multiplexers
- [ ] Create PCA9546A wrapper class (if needed)
- [ ] Test communication through TCA9548A → PCA9546A chain
- [ ] Verify addressing: TCA ch0→PCA@0x70, ch1→PCA@0x71, ch2→PCA@0x72
- [ ] Test PCA9546A channel switching (channels 0-1 for each board)

**Success Criteria**: Can access all 3 PCA9546A devices and switch their channels

### Phase 4: VCNL4040 Sensor Integration 📡
**Objective**: Read sensor data through multiplexer chain
- [ ] Initialize Adafruit VCNL4040 library
- [ ] Test single sensor access: TCA ch0 → PCA ch0 → VCNL4040
- [ ] Implement sensor reading routine
- [ ] Test all 6 sensors (3 boards × 2 sensors each)
- [ ] Display real-time sensor readings
- [ ] Implement basic proximity detection

**Success Criteria**: All 6 sensors provide proximity and ambient light readings

### Phase 5: System Integration & Optimization ⚡
**Objective**: Create production-ready sensor system
- [ ] Implement fast I2C switching routine
- [ ] Add sensor calibration (baseline + threshold)
- [ ] Create detection algorithm (direction sensing)
- [ ] Add LED feedback system integration
- [ ] Optimize I2C speed for maximum performance
- [ ] Add error handling and recovery

**Success Criteria**: System detects object movement and direction reliably

## Code Structure Plan

### File Organization:
```
firmware/src/
├── main.cpp                 # Main application loop
├── components/
│   ├── display/
│   │   ├── terminal.h/cpp   # Terminal display system
│   │   └── ui.h/cpp         # User interface
│   ├── multiplexers/
│   │   ├── tca9548a.h/cpp   # TCA9548A wrapper
│   │   └── pca9546a.h/cpp   # PCA9546A wrapper
│   ├── sensors/
│   │   └── vcnl4040_array.h/cpp # Multi-sensor management
│   └── detection/
│       └── motion_detector.h/cpp # Movement detection logic
└── pin_config.h             # Hardware pin definitions
```

### Key Classes to Implement:
1. **TerminalDisplay**: Logging and debug display
2. **TCA9548AManager**: Main multiplexer control
3. **PCA9546AManager**: Sensor board multiplexer control
4. **VCNL4040Array**: Multi-sensor management
5. **MotionDetector**: Direction detection algorithm

## Testing Strategy

### Unit Tests (per phase):
- **Display**: Show text, handle buttons, scroll logs
- **TCA9548A**: Channel switching, device detection
- **PCA9546A**: Communication through TCA chain
- **VCNL4040**: Sensor readings, calibration
- **Integration**: Full detection cycle timing

### Performance Targets:
- **I2C Speed**: 400kHz (fast mode)
- **Sensor Reading**: <10ms per sensor
- **Full Scan**: <100ms for all 6 sensors
- **Detection Latency**: <50ms object-to-LED response

## Implementation Notes

### GPIO Pin Assignments (Motion Play v4/v5):
```
T-Display-S3 Custom Connections:
├── GPIO 43: I2C SDA → TCA9548A
├── GPIO 44: I2C SCL → TCA9548A  
├── GPIO 10: TCA_RESET → TCA9548A reset (active low)
├── GPIO 11: SENSOR_INT_1 → Sensor board 1 interrupt
├── GPIO 12: SENSOR_INT_2 → Sensor board 2 interrupt
├── GPIO 13: SENSOR_INT_3 → Sensor board 3 interrupt
└── GPIO 16: LED_STRIP_DATA → WS2818B (72 LEDs)

Built-in T-Display-S3:
├── GPIO 14: BUTTON_1 (user button)
├── GPIO 0:  BUTTON_2 (boot button)
└── GPIO 15: POWER_ON (display power)
```

### I2C Addressing Map:
```
Main I2C Bus (GPIO 43/44):
├── 0x70: TCA9548A (main multiplexer)
│   ├── Channel 0 → Sensor Board 1
│   │   └── 0x70: PCA9546A
│   │       ├── Channel 0 → VCNL4040 #1 (0x60)
│   │       └── Channel 1 → VCNL4040 #2 (0x60)
│   ├── Channel 1 → Sensor Board 2
│   │   └── 0x71: PCA9546A
│   │       ├── Channel 0 → VCNL4040 #3 (0x60)
│   │       └── Channel 1 → VCNL4040 #4 (0x60)
│   └── Channel 2 → Sensor Board 3
│       └── 0x72: PCA9546A
│           ├── Channel 0 → VCNL4040 #5 (0x60)
│           └── Channel 1 → VCNL4040 #6 (0x60)
```

### Critical Success Factors:
1. **Library Compatibility**: Use only well-maintained libraries
2. **Error Handling**: Robust I2C communication with recovery
3. **Performance**: Optimize for speed without sacrificing reliability
4. **Maintainability**: Clean, documented code structure
5. **Testability**: Each component independently verifiable

## Next Steps

1. **Immediate**: Update platformio.ini with TCA9548A library
2. **Phase 1 Start**: Create new main.cpp with basic display test
3. **Documentation**: Update this plan as implementation progresses
4. **Testing**: Validate each phase before proceeding to next

---

**Document Version**: 2.0  
**Created**: October 2025  
**Last Updated**: [Auto-updated with each commit]  
**Status**: Ready for implementation

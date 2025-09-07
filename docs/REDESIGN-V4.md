## Motion Play PCB Redesign Plan - Summary Document

### Project Overview
Redesigning the Motion Play sensor system to address current limitations and improve functionality. The system will maintain 6 proximity sensors total, but reorganized as 3 sensor boards with 2 sensors each, connected to a main control board.

### Sensor Spacing Calculation
For a 19mm diameter circle with sensors positioned to achieve a 10-degree angular separation:
- Circle circumference: π × 19mm = 59.7mm
- 10 degrees of 360 degrees = 10/360 = 2.78% of circumference
- **Required spacing: 59.7mm × 0.0278 = 1.66mm**
- **Recommended: 2mm spacing** (accounts for sensor package width and provides slight margin)

This close spacing means the sensors will be nearly adjacent on the flex PCB, which is actually good for detecting fine motion differences across the curved surface.

---

## SENSOR BOARD REDESIGN SPECIFICATIONS

### Key Changes from Current Design
1. **Consolidation**: Two VCNL4040 sensors per board (previously one)
2. **Local Multiplexing**: PCA9546A on each sensor board
3. **Improved Power**: Direct connection from main board (no daisy-chaining)
4. **Debug Features**: Power LED with enable jumper
5. **Flexible Configuration**: Solder jumpers for I2C addressing

### Component Selection
| Component | Part Number | Quantity | Purpose |
|-----------|------------|----------|---------|
| I2C Switch | PCA9546A | 1 | Local multiplexing of 2 sensors |
| Proximity Sensor | VCNL4040 | 2 | Object detection (2mm apart) |
| LED | Green 0603 | 1 | Power indicator |
| Resistor | 330Ω 0603 | 1 | LED current limiting |
| Resistor | 10kΩ 0603 | 3 | Pull-ups (1 for RESET, 2 optional for I2C) |
| Capacitor | 10µF 0603 | 1 | Bulk power filtering |
| Capacitor | 0.1µF 0603 | 3 | Local decoupling (1 per IC) |
| Connector | JST-SH 5-pin | 1 | Main board interface |

### Connector Pinout (JST-SH 5-pin)
| Pin | Signal | Direction | Description |
|-----|--------|-----------|-------------|
| 1 | 3.3V | Power In | Regulated power from main board |
| 2 | GND | Power | Ground reference |
| 3 | SDA | Bidirectional | I2C data from TCA9548A channel |
| 4 | SCL | Input | I2C clock from TCA9548A channel |
| 5 | INT | Output | Combined interrupt from both sensors |

### PCA9546A Pin Assignments
| Pin | Name | Connection | Notes |
|-----|------|------------|-------|
| 1 | SDA | To JST Pin 3 | Main I2C data |
| 2 | SCL | To JST Pin 4 | Main I2C clock |
| 3 | SD0 | To VCNL4040 #1 SDA | Channel 0 data |
| 4 | SC0 | To VCNL4040 #1 SCL | Channel 0 clock |
| 5 | SD1 | To VCNL4040 #2 SDA | Channel 1 data |
| 6 | SC1 | To VCNL4040 #2 SCL | Channel 1 clock |
| 7 | SD2 | No Connect | Unused channel |
| 8 | GND | Ground | |
| 9 | SC2 | No Connect | Unused channel |
| 10 | SD3 | No Connect | Unused channel |
| 11 | SC3 | No Connect | Unused channel |
| 12 | A2 | Solder Jumper SJ3 | Address bit 2 |
| 13 | A1 | Solder Jumper SJ2 | Address bit 1 |
| 14 | A0 | Solder Jumper SJ1 | Address bit 0 |
| 15 | RESET | 10kΩ to 3.3V | Active low reset |
| 16 | VDD | 3.3V | Power supply |

### I2C Address Configuration
Using 3-pad solder jumpers for each address bit:

| Board # | A2 | A1 | A0 | I2C Address |
|---------|----|----|-----|-------------|
| Board 1 | Float | Float | GND | 0x71 |
| Board 2 | Float | GND | Float | 0x72 |
| Board 3 | Float | GND | GND | 0x73 |

### Design Features
1. **Cuttable I2C Pull-ups**: 10kΩ resistors with cuttable traces (normally disconnected)
2. **Power LED Jumper**: Allows disabling LED to save power
3. **Test Points**: 8 test points for debugging all I2C channels
4. **Interrupt Combining**: Both VCNL4040 INT pins wire-OR'd to single output
5. **Flex PCB Stiffeners**: Under connector, PCA9546A, and both sensors

---

## MAIN BOARD REDESIGN SPECIFICATIONS

### Key Changes from Current Design
1. **Power Upgrade**: Replace AMS1117-3.3 with MP2315 (3A switching regulator)
2. **Remove Daisy-Chain**: Eliminate pass-through power connectors
3. **Add Debug LEDs**: Power indicator for 3.3V rail
4. **Maintain TCA9548A**: Keep 8-channel mux for future expansion

### Power System Redesign

#### Current (Inadequate) System:
- AMS1117-3.3: 1A max output
- Required: ~1.5A peak for 6 sensors + logic

#### New Power Architecture:
```
USB-C (5.2V/2.4A) 
    ├── Direct to LED strip (5V)
    ├── Direct to T-Display-S3 VIN (5V)
    └── MP2315 Switching Regulator
        └── 3.3V/3A output
            ├── To TCA9548A
            ├── To all sensor boards
            └── Power indicator LED
```

### MP2315 Circuit Requirements
- Input capacitors: 10µF + 10µF ceramic
- Output capacitors: 22µF + 22µF ceramic  
- Inductor: 4.7µH, >3A rating
- Feedback resistors for 3.3V output
- Enable pin tied to VIN

### Main Board Connector Changes
- Change from 6 individual sensor connectors to 3 connectors (one per sensor board)
- Each connector: JST-SH 5-pin matching sensor board pinout
- Power wiring: Star topology with external wire splicing

### Pull-up Resistor Configuration
- Main I2C bus (MCU to TCA9548A): 2.2kΩ pull-ups
- Each TCA9548A channel: 2.2kΩ pull-ups
- Total resistance with sensor boards: ~2.2kΩ (sensor pull-ups disconnected by default)

---

## IMPLEMENTATION PLAN

### Phase 1: Prototype Design
1. Create KiCad schematic for new sensor board
2. Update main board schematic with MP2315
3. Design flex PCB layout with 2mm sensor spacing
4. Verify I2C addressing scheme

### Phase 2: Testing Strategy
1. Build one sensor board first
2. Test with current main board (using external 3.3V supply)
3. Verify PCA9546A switching and dual sensor operation
4. Test interrupt combining functionality

### Phase 3: Full Implementation
1. Fabricate all 3 sensor boards
2. Update main board with new power system
3. Test complete system with short cables first
4. Gradually extend cable length to 800mm target

### Critical Design Validations
1. **Power Budget**: Verify MP2315 handles 1.5A load with margin
2. **I2C Timing**: Confirm 400kHz operation with 2.2kΩ pull-ups
3. **Flex PCB Durability**: Test connector strain relief
4. **Sensor Spacing**: Validate 2mm spacing provides desired angular resolution

---

## OPEN ITEMS & CONSIDERATIONS

### Resolved Decisions
- ✅ Use MP2315 switching regulator
- ✅ Solder jumpers for address selection
- ✅ Skip I2C buffers initially
- ✅ Combine interrupts per sensor board
- ✅ 2mm spacing between sensors

### Future Considerations
1. Add I2C buffers if cable length issues arise
2. Consider conformal coating on flex PCB for durability
3. Potential for 4-sensor boards using all PCA9546A channels
4. Software interrupt handling for identifying which sensor triggered

### Risk Mitigation
1. **I2C Signal Integrity**: Include footprints for optional I2C buffers
2. **Power Stability**: Add test points for voltage monitoring
3. **Mechanical Stress**: Use strain relief and cable management
4. **Assembly Errors**: Clear silkscreen marking for solder jumper configuration

---

This document serves as the foundation for both PCB redesigns. The sensor board is the priority, as it represents the most significant change and will inform final main board modifications.

Motion Play PCB Redesign Plan - Summary Document
Project Overview
Redesigning the Motion Play sensor system to address current limitations and improve functionality. The system will maintain 6 proximity sensors total, reorganized as 3 sensor boards with 2 sensors each, connected to a main control board via individual cables in a star topology.
Sensor Spacing Calculation
For a 19mm diameter circle with sensors positioned to achieve a 10-degree angular separation:

Circle circumference: π × 19mm = 59.7mm
10 degrees of 360 degrees = 10/360 = 2.78% of circumference
Required spacing: 59.7mm × 0.0278 = 1.66mm
Recommended: 2mm spacing (accounts for sensor package width and provides slight margin)

This close spacing means the sensors will be nearly adjacent on the flex PCB, which is actually good for detecting fine motion differences across the curved surface.

SENSOR BOARD REDESIGN SPECIFICATIONS
Key Changes from Current Design

Consolidation: Two VCNL4040 sensors per board (previously one)
Local Multiplexing: PCA9546A on each sensor board
Improved Power: Direct connection from main board via 5-pin connector
Debug Features: Power LED with enable jumper
Flexible Configuration: Solder jumpers for I2C addressing and pull-up resistors

Component Selection
ComponentPart NumberQuantityPurposeI2C SwitchPCA9546A1Local multiplexing of 2 sensorsProximity SensorVCNL40402Object detection (2mm apart)LEDGreen 06031Power indicatorResistor330Ω 06031LED current limitingResistor10kΩ 06031Pull-up for RESETResistor4.7kΩ 06032I2C pull-ups (with disconnect option)Capacitor10µF 06031Bulk power filteringCapacitor0.1µF 06033Local decoupling (1 per IC)ConnectorJST-SH 5-pin1Main board interface
Connector Pinout (JST-SH 5-pin)
PinSignalDirectionDescription13.3VPower InRegulated power from main board2GNDPowerGround reference3SDABidirectionalI2C data from TCA9548A channel4SCLInputI2C clock from TCA9548A channel5INTOutputCombined interrupt from both sensors
PCA9546A Pin Assignments
PinNameConnectionNotes1SDATo JST Pin 3Main I2C data2SCLTo JST Pin 4Main I2C clock3SD0To VCNL4040 #1 SDAChannel 0 data4SC0To VCNL4040 #1 SCLChannel 0 clock5SD1To VCNL4040 #2 SDAChannel 1 data6SC1To VCNL4040 #2 SCLChannel 1 clock7SD2No ConnectUnused channel8GNDGround9SC2No ConnectUnused channel10SD3No ConnectUnused channel11SC3No ConnectUnused channel12A2Solder Jumper SJ3Address bit 213A1Solder Jumper SJ2Address bit 114A0Solder Jumper SJ1Address bit 015RESET10kΩ to 3.3VActive low reset16VDD3.3VPower supply
I2C Address Configuration
Using 3-pad solder jumpers for each address bit:
Board #A2A1A0I2C AddressBoard 1FloatFloatGND0x71Board 2FloatGNDFloat0x72Board 3FloatGNDGND0x73
Pull-up Resistor Configuration

Main I2C input: 4.7kΩ pull-ups on SDA/SCL with cuttable traces
PCA9546A to sensors: No pull-ups (short traces, low capacitance)
Design feature: Solder jumpers to disconnect pull-ups if needed

Design Features

Configurable I2C Pull-ups: 4.7kΩ resistors with cuttable traces/solder jumpers
Power LED Jumper: Allows disabling LED to save power
Test Points: 8 test points for debugging all I2C channels
Interrupt Combining: Both VCNL4040 INT pins wire-OR'd to single output
Flex PCB Stiffeners: Under connector, PCA9546A, and both sensors


MAIN BOARD REDESIGN SPECIFICATIONS
Key Changes from Current Design

Power Upgrade: Replace AMS1117-3.3 with MP2393 (3A switching regulator)
Connector Reduction: From 6 individual to 3 sensor board connectors
Power Distribution: Star topology with individual cables (no daisy-chain)
Add Power Monitoring: Utilize MP2393's Power Good pin
Maintain TCA9548A: Keep 8-channel mux, use 3 channels

Power System Redesign
Current (Inadequate) System:

AMS1117-3.3: 1A max output
Required: ~1.5A peak for 6 sensors + logic

New Power Architecture:
USB-C (5.2V/2.4A) 
    ├── Direct to LED strip (5V)
    ├── Direct to T-Display-S3 VIN (5V)
    └── MP2393 Switching Regulator
        └── 3.3V/3A output
            ├── To TCA9548A
            ├── To all sensor boards (via star topology)
            ├── Power indicator LED
            └── Power Good → GPIO1
MP2393 Circuit Requirements

Input capacitors: 10µF + 10µF ceramic
Output capacitors: 22µF + 22µF ceramic
Inductor: 4.7µH, >3A rating
Feedback resistors for 3.3V output
Enable pin tied to VIN
Power Good pin to T-Display-S3 GPIO1

Main Board Connector Configuration

Quantity: 3x JST-SH 5-pin connectors
Cable type: 5-conductor, up to 800mm length
Topology: Star configuration - individual cable from main board to each sensor board
Current per connector: ~250mA max (2 sensors + PCA9546A)

Pull-up Resistor Strategy

Main I2C bus (MCU to TCA9548A): 2.2kΩ pull-ups on SDA/SCL
TCA9548A output channels: NO pull-ups (handled by sensor boards)
Total bus resistance: Effectively 4.7kΩ per active segment
I2C Speed: 400kHz supported with this configuration

T-Display-S3 GPIO Assignments
GPIOFunctionNotes43I2C SDAMain I2C bus44I2C SCLMain I2C bus10TCA9548A RESETActive low reset control11Sensor INT 1Interrupt from sensor board 112Sensor INT 2Interrupt from sensor board 213Sensor INT 3Interrupt from sensor board 316LED DataWS2812B control signal3ADC Current SenseMonitor LED strip current1Power GoodMP2393 power status

IMPLEMENTATION PLAN
Phase 1: Prototype Design

Create KiCad schematic for new sensor board with PCA9546A
Update main board schematic with MP2393 and reduced connectors
Design flex PCB layout with 2mm sensor spacing
Implement hierarchical schematic for TCA9548A subsystem

Phase 2: Testing Strategy

Build one sensor board first
Test with current main board (using external 3.3V supply)
Verify PCA9546A switching and dual sensor operation
Test interrupt combining functionality
Validate pull-up resistor configuration at 400kHz

Phase 3: Full Implementation

Fabricate all 3 sensor boards
Update main board with MP2393 power system
Test complete system with short cables first
Gradually extend cable length to 800mm target
Verify Power Good signal operation

Critical Design Validations

Power Budget: Verify MP2393 handles 1.5A load with margin
I2C Signal Integrity: Confirm 400kHz operation with 800mm cables
Pull-up Optimization: Test with/without sensor board pull-ups
Flex PCB Durability: Test connector strain relief
Sensor Spacing: Validate 2mm spacing provides desired angular resolution


DESIGN DECISIONS SUMMARY
Finalized Decisions

✅ Use MP2393 switching regulator with Power Good monitoring
✅ Single 5-pin JST-SH connector per sensor board
✅ Star topology power distribution (no daisy-chain)
✅ 2.2kΩ pull-ups on main bus, 4.7kΩ on sensor boards
✅ Solder jumpers for address selection
✅ Combine interrupts per sensor board
✅ 2mm spacing between sensors on each board
✅ Skip per-channel debug LEDs (only power indicator)

Risk Mitigation

I2C Signal Integrity: Configurable pull-ups via solder jumpers
Power Stability: Power Good signal for system reliability
Cable Management: Star topology simplifies troubleshooting
Assembly Flexibility: Clear silkscreen for jumper configuration
Future Expansion: 5 unused TCA9548A channels available

Future Considerations

Add I2C buffers if longer cable requirements arise
Consider conformal coating on flex PCB for durability
Potential for custom cable assemblies to reduce cost
Software interrupt handler optimization for multi-sensor triggers


This document serves as the complete specification for both PCB redesigns. The modular approach with PCA9546A on sensor boards provides maximum flexibility while the MP2393-based main board ensures adequate power delivery for the complete system.



Update 09/07/2025:

Implementation Updates from Original Plan
Connector Pin Assignments Finalized
During implementation, the 5-pin JST-SH connector pinout for sensor boards was finalized as:

Pin 1: 3.3V
Pin 2: GND
Pin 3: SDA
Pin 4: SCL
Pin 5: INT

This order was chosen to keep power and ground together, reducing the chance of noise coupling into the I2C signals.
GPIO Pin Assignments Confirmed
The T-Display-S3 GPIO allocation has been finalized based on available pins:

GPIO 43, 44: I2C bus (SDA/SCL)
GPIO 10: TCA9548A RESET control
GPIO 11, 12, 13: Interrupt inputs from sensor boards 1, 2, 3
GPIO 16: WS2812B LED data (moved from GPIO 2 for cleaner operation)
GPIO 3: ADC current sensing for LED strip monitoring
GPIO 1: Power Good signal from MP2393

LED Strip Connector Updated
Replaced the incorrect JST PH 2.0mm connector (C265101) with a proper JST XH-compatible 2.5mm pitch connector (LCSC: C7429672) to match standard WS2812B LED strips. The connector is a 3-pin SMD right-angle type with pinout matching the standard +5V/Data/GND configuration.
Hierarchical Schematic Organization
The TCA9548A multiplexer and its support components have been organized into a hierarchical sheet for better schematic clarity. The main sheet retains the MCU, power system, and all connectors for easier PCB layout planning.


Next Steps:

* Complete Design Rule Check (DRC) and Electrical Rules Check (ERC) on main schematic
* Begin sensor board schematic with PCA9546A implementation
* Create PCB layout for main board with attention to:

* Power plane design for MP2393
* I2C trace routing and length matching
* Connector placement for cable management


* Design flex PCB layout for sensor boards with 2mm sensor spacing

Open Items:

* Verify MP2393 inductor selection for optimal efficiency
* Confirm pull-up resistor values after prototype testing
* Determine optimal flex PCB stiffener placement
* Select specific cable assemblies or specify build requirements
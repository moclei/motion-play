# Testing Guide

This project now includes two test programs:

## 1. Full System Test (`main.cpp`)
Tests the complete system with TCA9548A multiplexer and sensor PCBs.

**To build and upload:**
```bash
pio run -e lilygo-t-display-s3 -t upload
```

## 2. Direct Sensor Test (`sensor_direct_test.cpp`)
Tests a single sensor PCB directly connected to T-Display-S3, bypassing the multiplexer.

**To build and upload:**
```bash
pio run -e sensor-direct-test -t upload
```

## Direct Sensor Test Wiring

Connect your T-Display-S3 to the sensor PCB using jumper wires:

| T-Display-S3 Pin | Sensor PCB Connector | Signal |
|------------------|---------------------|---------|
| Pin 43 (SDA)     | J3 Pin 2           | SDA     |
| Pin 44 (SCL)     | J3 Pin 1           | SCL     |
| 3.3V             | J1 Pin 1           | 3.3V    |
| GND              | J1 Pin 2           | GND     |

**Notes:**
- J1 is the power connector (3.3V + GND)
- J3 is the communication connector (SDA + SCL + INT)
- INT pin is not needed for this test
- Use a breadboard to make connections easier

## What the Direct Test Does

1. **I2C Bus Test**: Scans for devices at different speeds (100kHz, 400kHz)
2. **Communication Test**: Verifies the sensor responds at address 0x60
3. **Device ID Check**: Reads the VCNL4040 device ID register (should be 0x0186)
4. **Register Configuration**: Sets up proximity and ambient light sensors
5. **Register Dump**: Shows all register values for debugging
6. **Live Readings**: Displays real-time sensor data

## Controls

- **Button 1 (UP)**: Short press = scroll up one line, Long press = jump to top
- **Button 2 (DOWN)**: Short press = scroll down one line, Long press = jump to bottom  
- **Both Buttons**: Hold for 2 seconds to reset device

## Troubleshooting

If the direct test fails:

1. **Check Power**: Verify 3.3V and GND connections with multimeter
2. **Check Data Lines**: Verify SDA/SCL continuity
3. **Check Soldering**: Ensure sensor PCB connections are solid
4. **Try Different Speeds**: The test tries both 100kHz and 400kHz I2C
5. **Check Pull-ups**: Ensure I2C pull-up resistors are present

## Expected Results

**Working sensor should show:**
- Device found at 0x60 in I2C scan
- Communication test: OK
- Device ID: 0x0186
- All register writes: OK
- Live readings with changing proximity values

**Common failures:**
- No device at 0x60 = power or connection issue
- Device ID 0x0000 or 0xFFFF = power or timing issue
- Communication test failed = wiring or I2C issue

## Switching Between Tests

The project is set up so you can easily switch between the full system test and direct sensor test without losing either version of the code.

- Use `pio run -e lilygo-t-display-s3 -t upload` for full system
- Use `pio run -e sensor-direct-test -t upload` for direct sensor test

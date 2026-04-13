#include "PowerMonitor.h"

bool PowerMonitor::init()
{
    // Probe for INA219
    Wire.beginTransmission(INA219_ADDR);
    if (Wire.endTransmission() != 0)
    {
        Serial.println("[PowerMonitor] INA219 not found at 0x40 - skipping");
        available = false;
        return false;
    }

    // Reset the INA219
    writeRegister(INA219_REG_CONFIG, 0x8000);
    delay(1);

    // Config register:
    //   BRNG = 0 (16V bus range, sufficient for VSYS 3.0-4.5V)
    //   PGA  = /2 (01) → +/-80mV shunt range → 8A max with 10mΩ
    //   BADC = 1101 (12-bit, 128 samples avg, ~68ms) — smooth readings
    //   SADC = 1101 (12-bit, 128 samples avg, ~68ms)
    //   MODE = 111 (shunt + bus, continuous)
    //
    // Bit layout: 0 | BRNG(1) | PG1 PG0(2) | BADC4..1(4) | SADC4..1(4) | MODE3..1(3)
    //             0    0         0  1          1  1  0  1     1  1  0  1     1  1  1
    // = 0x1EF7 — but let's use 32-sample avg (~17ms) for faster updates:
    //   BADC = 1100 (32 samples, ~17ms)
    //   SADC = 1100 (32 samples, ~17ms)
    // = 0x1CE7 — still smooth, but more responsive
    //
    // Actually for debugging power issues, let's use 16-sample avg (~8.5ms):
    //   BADC = 1011 (16 samples)
    //   SADC = 1011 (16 samples)
    // = 0x1ADF — not right, let me lay it out properly:
    //
    // Bits 15-13: RST(1) + unused(2) = 0b000
    // Bit 13: BRNG = 0 (16V)
    // Bits 12-11: PGA = 01 (/2)
    // Bits 10-7: BADC = 1100 (12-bit, 32 avg)
    // Bits 6-3: SADC = 1100 (12-bit, 32 avg)
    // Bits 2-0: MODE = 111 (continuous shunt+bus)
    //
    // = 0b0_0_01_1100_1100_111 = 0x1E67
    uint16_t config = 0x1E67;
    writeRegister(INA219_REG_CONFIG, config);

    // Calibration register:
    // Cal = trunc(0.04096 / (Current_LSB * R_shunt))
    // Current_LSB = 1mA = 0.001A, R_shunt = 0.01Ω
    // Cal = trunc(0.04096 / (0.001 * 0.01)) = trunc(4096) = 4096 = 0x1000
    writeRegister(INA219_REG_CALIBRATION, 4096);

    available = true;
    Serial.println("[PowerMonitor] INA219 configured: 10mR shunt, 1mA/LSB, 8A max");
    return true;
}

void PowerMonitor::update()
{
    if (!available)
        return;

    // Read bus voltage register
    int16_t rawBus = readRegister(INA219_REG_BUS_V);
    // Bus voltage: bits 15-3 contain the voltage, LSB = 4mV
    // Bit 1 = CNVR (conversion ready), Bit 0 = OVF (overflow)
    busVoltage = (rawBus >> 3) * 0.004f;

    // Read current register (uses calibration)
    int16_t rawCurrent = readRegister(INA219_REG_CURRENT);
    // Current LSB = 1mA (per our calibration)
    currentMA = (float)rawCurrent;

    // Read shunt voltage for diagnostics
    int16_t rawShunt = readRegister(INA219_REG_SHUNT_V);
    // Shunt voltage LSB = 10µV
    shuntVoltage = rawShunt * 0.01f; // in mV
}

int16_t PowerMonitor::readRegister(uint8_t reg)
{
    Wire.beginTransmission(INA219_ADDR);
    Wire.write(reg);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)INA219_ADDR, (uint8_t)2);
    if (Wire.available() < 2)
        return 0;
    uint8_t msb = Wire.read();
    uint8_t lsb = Wire.read();
    return (int16_t)((msb << 8) | lsb);
}

void PowerMonitor::writeRegister(uint8_t reg, uint16_t value)
{
    Wire.beginTransmission(INA219_ADDR);
    Wire.write(reg);
    Wire.write((uint8_t)(value >> 8));
    Wire.write((uint8_t)(value & 0xFF));
    Wire.endTransmission();
}

#include "VCNL4040.h"

// Register addresses
#define VCNL4040_ALS_CONF 0x00
#define VCNL4040_ALS_THDH 0x01
#define VCNL4040_ALS_THDL 0x02
#define VCNL4040_PS_CONF1 0x03
#define VCNL4040_PS_CONF2 0x04
#define VCNL4040_PS_CONF3 0x05
#define VCNL4040_PS_MS 0x06
#define VCNL4040_PS_THDL 0x07
#define VCNL4040_PS_THDH 0x08
#define VCNL4040_PS_DATA 0x08
#define VCNL4040_ALS_DATA 0x09
#define VCNL4040_WHITE_DATA 0x0A
#define VCNL4040_INT_FLAG 0x0B
#define VCNL4040_ID 0x0C

VCNL4040::VCNL4040(uint8_t address) : _address(address) {}

bool VCNL4040::begin()
{
    // Check if device is present
    Wire.beginTransmission(_address);
    if (Wire.endTransmission() != 0)
    {
        return false;
    }

    // Verify device ID
    uint16_t deviceID = readRegister(VCNL4040_ID);

    if (deviceID != 0x0186)
    {
        return false;
    }

    // Configure proximity sensor
    writeRegister(VCNL4040_PS_CONF1, 0x0000); // Default settings
    writeRegister(VCNL4040_PS_CONF2, 0x0000); // Default settings
    writeRegister(VCNL4040_PS_CONF3, 0x0000); // Default settings

    // Configure ambient light sensor
    writeRegister(VCNL4040_ALS_CONF, 0x0000); // Default settings
    return true;
}

uint16_t VCNL4040::readProximity()
{
    return readRegister(VCNL4040_PS_DATA);
}

uint16_t VCNL4040::readAmbientLight()
{
    return readRegister(VCNL4040_ALS_DATA);
}

bool VCNL4040::writeRegister(uint8_t reg, uint16_t value)
{
    Wire.beginTransmission(_address);
    Wire.write(reg);
    Wire.write(value & 0xFF);
    Wire.write((value >> 8) & 0xFF);
    return Wire.endTransmission() == 0;
}

uint16_t VCNL4040::readRegister(uint8_t reg)
{
    Wire.beginTransmission(_address);
    Wire.write(reg);
    Wire.endTransmission(false);

    Wire.requestFrom((uint8_t)_address, (uint8_t)2);
    if (Wire.available() >= 2)
    {
        uint8_t lsb = Wire.read();
        uint8_t msb = Wire.read();
        return (msb << 8) | lsb;
    }
    return 0;
}
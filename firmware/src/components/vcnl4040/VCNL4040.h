#pragma once

#include <Arduino.h>
#include <Wire.h>

class VCNL4040
{
public:
    VCNL4040(uint8_t address = 0x60);
    bool begin();
    uint16_t readProximity();
    uint16_t readAmbientLight();

private:
    uint8_t _address;
    bool writeRegister(uint8_t reg, uint16_t value);
    uint16_t readRegister(uint8_t reg);
};
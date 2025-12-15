/**
 * VCNL4040 Enhanced Library - Implementation
 * 
 * See VCNL4040.h for documentation and register map details.
 */

#include "VCNL4040.h"

// =============================================================================
// Constructor
// =============================================================================

VCNL4040::VCNL4040(uint8_t address) : _address(address), _i2cPort(nullptr) {}

// =============================================================================
// Initialization
// =============================================================================

bool VCNL4040::begin(TwoWire &wirePort)
{
    _i2cPort = &wirePort;
    
    // Check if device is responding
    if (!isConnected()) {
        return false;
    }

    // Verify device ID
    uint16_t deviceID = getID();
    if (deviceID != VCNL4040_ID_VALUE) {
        return false;
    }

    // Initialize with sensible defaults:
    // - PS and ALS powered off initially (user must enable)
    // - 16-bit resolution for proximity
    // - 200mA LED current
    // - PS interrupt disabled
    
    // ALS_CONF: ALS off, 80ms integration, no interrupt
    writeRegister(VCNL4040_ALS_CONF, 0x0001);
    
    // PS_CONF1/2: PS off, 1/40 duty, 1T integration, 16-bit, interrupt disabled
    writeRegister(VCNL4040_PS_CONF1_2, 0x0801);  // PS_HD=1 (16-bit), PS_SD=1 (off)

    // PS_CONF3/MS: No multi-pulse, 200mA LED current, normal mode
    writeRegister(VCNL4040_PS_CONF3_MS, 0x0700);  // LED_I = 200mA
    
    return true;
}

bool VCNL4040::isConnected()
{
    if (_i2cPort == nullptr) return false;
    
    _i2cPort->beginTransmission(_address);
    return (_i2cPort->endTransmission() == 0);
}

uint16_t VCNL4040::getID()
{
    return readRegister(VCNL4040_ID);
}

// =============================================================================
// Proximity Sensor - Basic Reading
// =============================================================================

uint16_t VCNL4040::readProximity()
{
    return readRegister(VCNL4040_PS_DATA);
}

void VCNL4040::powerOnProximity(bool on)
{
    if (on) {
        bitMask(VCNL4040_PS_CONF1_2, false, VCNL4040_PS_SD_MASK, VCNL4040_PS_SD_ON);
    } else {
        bitMask(VCNL4040_PS_CONF1_2, false, VCNL4040_PS_SD_MASK, VCNL4040_PS_SD_OFF);
    }
}

// =============================================================================
// Proximity Sensor - Interrupt Configuration
// =============================================================================

void VCNL4040::setProxInterruptType(VCNL4040_PSInterrupt type)
{
    bitMask(VCNL4040_PS_CONF1_2, true, VCNL4040_PS_INT_MASK, static_cast<uint8_t>(type));
}

void VCNL4040::setProxHighThreshold(uint16_t threshold)
{
    writeRegister(VCNL4040_PS_THDH, threshold);
}

void VCNL4040::setProxLowThreshold(uint16_t threshold)
{
    writeRegister(VCNL4040_PS_THDL, threshold);
}

void VCNL4040::setProxPersistence(uint8_t hits)
{
    uint8_t value;
    switch (hits) {
        case 1:  value = VCNL4040_PS_PERS_1; break;
        case 2:  value = VCNL4040_PS_PERS_2; break;
        case 3:  value = VCNL4040_PS_PERS_3; break;
        case 4:  value = VCNL4040_PS_PERS_4; break;
        default: value = VCNL4040_PS_PERS_1; break;
    }
    bitMask(VCNL4040_PS_CONF1_2, false, VCNL4040_PS_PERS_MASK, value);
}

void VCNL4040::enableSmartPersistence(bool enable)
{
    uint8_t value = enable ? VCNL4040_PS_SMART_PERS_ENABLE : VCNL4040_PS_SMART_PERS_DISABLE;
    bitMask(VCNL4040_PS_CONF3_MS, false, VCNL4040_PS_SMART_PERS_MASK, value);
}

void VCNL4040::enableProxLogicMode(bool enable)
{
    uint8_t value = enable ? VCNL4040_PS_MS_LOGIC : VCNL4040_PS_MS_NORMAL;
    bitMask(VCNL4040_PS_CONF3_MS, true, VCNL4040_PS_MS_MASK, value);
}

// =============================================================================
// Proximity Sensor - Configuration
// =============================================================================

void VCNL4040::setLEDCurrent(uint16_t currentMA)
{
    uint8_t value;
    switch (currentMA) {
        case 50:  value = VCNL4040_LED_I_50MA; break;
        case 75:  value = VCNL4040_LED_I_75MA; break;
        case 100: value = VCNL4040_LED_I_100MA; break;
        case 120: value = VCNL4040_LED_I_120MA; break;
        case 140: value = VCNL4040_LED_I_140MA; break;
        case 160: value = VCNL4040_LED_I_160MA; break;
        case 180: value = VCNL4040_LED_I_180MA; break;
        case 200: value = VCNL4040_LED_I_200MA; break;
        default:  value = VCNL4040_LED_I_200MA; break;
    }
    bitMask(VCNL4040_PS_CONF3_MS, true, VCNL4040_LED_I_MASK, value);
}

void VCNL4040::setIRDutyCycle(uint16_t dutyValue)
{
    uint8_t value;
    switch (dutyValue) {
        case 40:  value = VCNL4040_PS_DUTY_40; break;
        case 80:  value = VCNL4040_PS_DUTY_80; break;
        case 160: value = VCNL4040_PS_DUTY_160; break;
        case 320: value = VCNL4040_PS_DUTY_320; break;
        default:  value = VCNL4040_PS_DUTY_40; break;
    }
    bitMask(VCNL4040_PS_CONF1_2, false, VCNL4040_PS_DUTY_MASK, value);
}

void VCNL4040::setProxIntegrationTime(uint8_t timeValue)
{
    uint8_t value;
    switch (timeValue) {
        case 1:  value = VCNL4040_PS_IT_1T; break;
        case 2:  value = VCNL4040_PS_IT_2T; break;
        case 3:  value = VCNL4040_PS_IT_3T; break;
        case 4:  value = VCNL4040_PS_IT_4T; break;
        case 8:  value = VCNL4040_PS_IT_8T; break;
        default: value = VCNL4040_PS_IT_1T; break;
    }
    bitMask(VCNL4040_PS_CONF1_2, false, VCNL4040_PS_IT_MASK, value);
}

void VCNL4040::setProxResolution(uint8_t bits)
{
    uint8_t value = (bits == 16) ? VCNL4040_PS_HD_16BIT : VCNL4040_PS_HD_12BIT;
    bitMask(VCNL4040_PS_CONF1_2, true, VCNL4040_PS_HD_MASK, value);
}

void VCNL4040::setMultiPulse(uint8_t pulses)
{
    uint8_t value;
    switch (pulses) {
        case 1: value = VCNL4040_PS_MPS_1; break;
        case 2: value = VCNL4040_PS_MPS_2; break;
        case 4: value = VCNL4040_PS_MPS_4; break;
        case 8: value = VCNL4040_PS_MPS_8; break;
        default: value = VCNL4040_PS_MPS_1; break;
    }
    bitMask(VCNL4040_PS_CONF3_MS, false, VCNL4040_PS_MPS_MASK, value);
}

void VCNL4040::setProxCancellation(uint16_t cancelValue)
{
    writeRegister(VCNL4040_PS_CANC, cancelValue);
}

void VCNL4040::enableSunlightCancellation(bool enable)
{
    uint8_t value = enable ? VCNL4040_PS_SC_ENABLE : VCNL4040_PS_SC_DISABLE;
    bitMask(VCNL4040_PS_CONF3_MS, false, VCNL4040_PS_SC_MASK, value);
}

// =============================================================================
// Ambient Light Sensor
// =============================================================================

uint16_t VCNL4040::readAmbientLight()
{
    return readRegister(VCNL4040_ALS_DATA);
}

uint16_t VCNL4040::readWhite()
{
    return readRegister(VCNL4040_WHITE_DATA);
}

void VCNL4040::powerOnAmbient(bool on)
{
    if (on) {
        bitMask(VCNL4040_ALS_CONF, false, VCNL4040_ALS_SD_MASK, VCNL4040_ALS_SD_ON);
    } else {
        bitMask(VCNL4040_ALS_CONF, false, VCNL4040_ALS_SD_MASK, VCNL4040_ALS_SD_OFF);
    }
}

void VCNL4040::enableWhiteChannel(bool enable)
{
    // Note: The bit logic is inverted - 0 = enabled, 1 = disabled
    uint8_t value = enable ? VCNL4040_WHITE_ENABLE : VCNL4040_WHITE_DISABLE;
    bitMask(VCNL4040_PS_CONF3_MS, true, VCNL4040_WHITE_EN_MASK, value);
}

void VCNL4040::setALSIntegrationTime(uint16_t timeMS)
{
    uint8_t value;
    switch (timeMS) {
        case 80:  value = VCNL4040_ALS_IT_80MS; break;
        case 160: value = VCNL4040_ALS_IT_160MS; break;
        case 320: value = VCNL4040_ALS_IT_320MS; break;
        case 640: value = VCNL4040_ALS_IT_640MS; break;
        default:  value = VCNL4040_ALS_IT_80MS; break;
    }
    bitMask(VCNL4040_ALS_CONF, false, VCNL4040_ALS_IT_MASK, value);
}

void VCNL4040::enableALSInterrupts(bool enable)
{
    uint8_t value = enable ? VCNL4040_ALS_INT_ENABLE : VCNL4040_ALS_INT_DISABLE;
    bitMask(VCNL4040_ALS_CONF, false, VCNL4040_ALS_INT_MASK, value);
}

void VCNL4040::setALSHighThreshold(uint16_t threshold)
{
    writeRegister(VCNL4040_ALS_THDH, threshold);
}

void VCNL4040::setALSLowThreshold(uint16_t threshold)
{
    writeRegister(VCNL4040_ALS_THDL, threshold);
}

void VCNL4040::setALSPersistence(uint8_t hits)
{
    uint8_t value;
    switch (hits) {
        case 1: value = VCNL4040_ALS_PERS_1; break;
        case 2: value = VCNL4040_ALS_PERS_2; break;
        case 4: value = VCNL4040_ALS_PERS_4; break;
        case 8: value = VCNL4040_ALS_PERS_8; break;
        default: value = VCNL4040_ALS_PERS_1; break;
    }
    bitMask(VCNL4040_ALS_CONF, false, VCNL4040_ALS_PERS_MASK, value);
}

// =============================================================================
// Interrupt Handling
// =============================================================================

VCNL4040_InterruptFlags VCNL4040::readInterruptFlags()
{
    VCNL4040_InterruptFlags flags;
    
    // Reading the INT_FLAG register clears all flags and resets INT pin
    uint8_t flagByte = readRegisterHigh(VCNL4040_INT_FLAG);
    
    flags.raw = flagByte;
    flags.psClose = (flagByte & VCNL4040_INT_FLAG_PS_IF_CLOSE) != 0;
    flags.psAway = (flagByte & VCNL4040_INT_FLAG_PS_IF_AWAY) != 0;
    flags.alsHigh = (flagByte & VCNL4040_INT_FLAG_ALS_IF_H) != 0;
    flags.alsLow = (flagByte & VCNL4040_INT_FLAG_ALS_IF_L) != 0;
    flags.psProtection = (flagByte & VCNL4040_INT_FLAG_PS_SPFLAG) != 0;
    
    return flags;
}

bool VCNL4040::isClose()
{
    VCNL4040_InterruptFlags flags = readInterruptFlags();
    return flags.psClose;
}

bool VCNL4040::isAway()
{
    VCNL4040_InterruptFlags flags = readInterruptFlags();
    return flags.psAway;
}

bool VCNL4040::isLight()
{
    VCNL4040_InterruptFlags flags = readInterruptFlags();
    return flags.alsHigh;
}

bool VCNL4040::isDark()
{
    VCNL4040_InterruptFlags flags = readInterruptFlags();
    return flags.alsLow;
}

// =============================================================================
// Active Force Mode
// =============================================================================

void VCNL4040::enableActiveForceMode(bool enable)
{
    uint8_t value = enable ? VCNL4040_PS_AF_ENABLE : VCNL4040_PS_AF_DISABLE;
    bitMask(VCNL4040_PS_CONF3_MS, false, VCNL4040_PS_AF_MASK, value);
}

void VCNL4040::triggerProxMeasurement()
{
    // Set PS_TRIG bit (auto-clears after measurement)
    bitMask(VCNL4040_PS_CONF3_MS, false, VCNL4040_PS_TRIG_MASK, VCNL4040_PS_TRIG);
}

// =============================================================================
// Low-Level Register Access
// =============================================================================

uint16_t VCNL4040::readRegister(uint8_t commandCode)
{
    _i2cPort->beginTransmission(_address);
    _i2cPort->write(commandCode);
    _i2cPort->endTransmission(false);  // Repeated start
    
    _i2cPort->requestFrom(_address, (uint8_t)2);
    
    if (_i2cPort->available() >= 2) {
        uint8_t lsb = _i2cPort->read();
        uint8_t msb = _i2cPort->read();
        return ((uint16_t)msb << 8) | lsb;
    }
    
    return 0;
}

bool VCNL4040::writeRegister(uint8_t commandCode, uint16_t value)
{
    _i2cPort->beginTransmission(_address);
    _i2cPort->write(commandCode);
    _i2cPort->write(value & 0xFF);        // Low byte first
    _i2cPort->write((value >> 8) & 0xFF); // High byte second
    return (_i2cPort->endTransmission() == 0);
}

uint8_t VCNL4040::readRegisterLow(uint8_t commandCode)
{
    uint16_t reg = readRegister(commandCode);
    return (uint8_t)(reg & 0xFF);
}

uint8_t VCNL4040::readRegisterHigh(uint8_t commandCode)
{
    uint16_t reg = readRegister(commandCode);
    return (uint8_t)((reg >> 8) & 0xFF);
}

bool VCNL4040::writeRegisterLow(uint8_t commandCode, uint8_t value)
{
    // Read current value, preserve high byte
    uint16_t current = readRegister(commandCode);
    uint16_t newValue = (current & 0xFF00) | value;
    return writeRegister(commandCode, newValue);
}

bool VCNL4040::writeRegisterHigh(uint8_t commandCode, uint8_t value)
{
    // Read current value, preserve low byte
    uint16_t current = readRegister(commandCode);
    uint16_t newValue = (current & 0x00FF) | ((uint16_t)value << 8);
    return writeRegister(commandCode, newValue);
}

// =============================================================================
// Private Helpers
// =============================================================================

void VCNL4040::bitMask(uint8_t commandCode, bool isHighByte, uint8_t mask, uint8_t value)
{
    // Read current register value
    uint16_t reg = readRegister(commandCode);
    
    uint8_t currentByte;
    if (isHighByte) {
        currentByte = (reg >> 8) & 0xFF;
    } else {
        currentByte = reg & 0xFF;
    }
    
    // Apply mask and set new bits
    currentByte = (currentByte & mask) | value;
    
    // Write back
    if (isHighByte) {
        reg = (reg & 0x00FF) | ((uint16_t)currentByte << 8);
    } else {
        reg = (reg & 0xFF00) | currentByte;
    }
    
    writeRegister(commandCode, reg);
}

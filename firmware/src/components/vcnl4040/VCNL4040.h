/**
 * VCNL4040 Enhanced Library
 * 
 * Complete driver for the Vishay VCNL4040 proximity and ambient light sensor.
 * Supports all sensor features including interrupt configuration.
 * 
 * Based on:
 * - Vishay VCNL4040 Datasheet (Document 84274)
 * - Vishay Application Note "Designing the VCNL4040 Into an Application"
 * - SparkFun VCNL4040 Arduino Library (reference implementation)
 * 
 * Register Map (16-bit registers, little-endian):
 *   0x00: ALS_CONF (L) + Reserved (H)
 *   0x01: ALS_THDH - ALS high threshold
 *   0x02: ALS_THDL - ALS low threshold
 *   0x03: PS_CONF1 (L) + PS_CONF2 (H)
 *   0x04: PS_CONF3 (L) + PS_MS (H)
 *   0x05: PS_CANC - Cancellation level
 *   0x06: PS_THDL - PS low threshold
 *   0x07: PS_THDH - PS high threshold
 *   0x08: PS_DATA - Proximity data
 *   0x09: ALS_DATA - Ambient light data
 *   0x0A: WHITE_DATA - White channel data
 *   0x0B: Reserved (L) + INT_Flag (H)
 *   0x0C: ID - Device ID (should read 0x0186)
 */

#pragma once

#include <Arduino.h>
#include <Wire.h>

// =============================================================================
// Register Command Codes (each addresses a 16-bit register)
// =============================================================================
#define VCNL4040_ALS_CONF       0x00
#define VCNL4040_ALS_THDH       0x01
#define VCNL4040_ALS_THDL       0x02
#define VCNL4040_PS_CONF1_2     0x03  // PS_CONF1 (low byte) + PS_CONF2 (high byte)
#define VCNL4040_PS_CONF3_MS    0x04  // PS_CONF3 (low byte) + PS_MS (high byte)
#define VCNL4040_PS_CANC        0x05
#define VCNL4040_PS_THDL        0x06
#define VCNL4040_PS_THDH        0x07
#define VCNL4040_PS_DATA        0x08
#define VCNL4040_ALS_DATA       0x09
#define VCNL4040_WHITE_DATA     0x0A
#define VCNL4040_INT_FLAG       0x0B
#define VCNL4040_ID             0x0C

// =============================================================================
// PS_CONF1 (0x03 Low Byte) Bit Definitions
// =============================================================================

// PS_Duty - IRED duty ratio (bits 7:6)
#define VCNL4040_PS_DUTY_MASK   0x3F  // Mask to clear bits 7:6
#define VCNL4040_PS_DUTY_40     0x00  // 1/40 duty cycle (~200 Hz)
#define VCNL4040_PS_DUTY_80     0x40  // 1/80 duty cycle (~100 Hz)
#define VCNL4040_PS_DUTY_160    0x80  // 1/160 duty cycle (~50 Hz)
#define VCNL4040_PS_DUTY_320    0xC0  // 1/320 duty cycle (~25 Hz)

// PS_PERS - Interrupt persistence (bits 5:4)
#define VCNL4040_PS_PERS_MASK   0xCF  // Mask to clear bits 5:4
#define VCNL4040_PS_PERS_1      0x00  // 1 consecutive hit
#define VCNL4040_PS_PERS_2      0x10  // 2 consecutive hits
#define VCNL4040_PS_PERS_3      0x20  // 3 consecutive hits
#define VCNL4040_PS_PERS_4      0x30  // 4 consecutive hits

// PS_IT - Integration time (bits 3:1)
#define VCNL4040_PS_IT_MASK     0xF1  // Mask to clear bits 3:1
#define VCNL4040_PS_IT_1T       0x00  // 1T
#define VCNL4040_PS_IT_1_5T     0x02  // 1.5T
#define VCNL4040_PS_IT_2T       0x04  // 2T
#define VCNL4040_PS_IT_2_5T     0x06  // 2.5T
#define VCNL4040_PS_IT_3T       0x08  // 3T
#define VCNL4040_PS_IT_3_5T     0x0A  // 3.5T
#define VCNL4040_PS_IT_4T       0x0C  // 4T
#define VCNL4040_PS_IT_8T       0x0E  // 8T

// PS_SD - Shutdown (bit 0)
#define VCNL4040_PS_SD_MASK     0xFE  // Mask to clear bit 0
#define VCNL4040_PS_SD_ON       0x00  // Power on
#define VCNL4040_PS_SD_OFF      0x01  // Shut down

// =============================================================================
// PS_CONF2 (0x03 High Byte) Bit Definitions
// =============================================================================

// PS_HD - Resolution (bit 3)
#define VCNL4040_PS_HD_MASK     0xF7  // Mask to clear bit 3
#define VCNL4040_PS_HD_12BIT    0x00  // 12-bit resolution
#define VCNL4040_PS_HD_16BIT    0x08  // 16-bit resolution

// PS_INT - Interrupt configuration (bits 1:0)
#define VCNL4040_PS_INT_MASK    0xFC  // Mask to clear bits 1:0
#define VCNL4040_PS_INT_DISABLE 0x00  // Interrupt disabled
#define VCNL4040_PS_INT_CLOSE   0x01  // Trigger when close (above high threshold)
#define VCNL4040_PS_INT_AWAY    0x02  // Trigger when away (below low threshold)
#define VCNL4040_PS_INT_BOTH    0x03  // Trigger on both close and away

// =============================================================================
// PS_CONF3 (0x04 Low Byte) Bit Definitions
// =============================================================================

// PS_MPS - Multi-pulse setting (bits 6:5)
#define VCNL4040_PS_MPS_MASK    0x9F  // Mask to clear bits 6:5
#define VCNL4040_PS_MPS_1       0x00  // 1 pulse
#define VCNL4040_PS_MPS_2       0x20  // 2 pulses
#define VCNL4040_PS_MPS_4       0x40  // 4 pulses
#define VCNL4040_PS_MPS_8       0x60  // 8 pulses

// PS_SMART_PERS - Smart persistence (bit 4)
#define VCNL4040_PS_SMART_PERS_MASK     0xEF  // Mask to clear bit 4
#define VCNL4040_PS_SMART_PERS_DISABLE  0x00
#define VCNL4040_PS_SMART_PERS_ENABLE   0x10

// PS_AF - Active force mode (bit 3)
#define VCNL4040_PS_AF_MASK     0xF7  // Mask to clear bit 3
#define VCNL4040_PS_AF_DISABLE  0x00
#define VCNL4040_PS_AF_ENABLE   0x08

// PS_TRIG - Active force trigger (bit 2)
#define VCNL4040_PS_TRIG_MASK   0xFB  // Mask to clear bit 2
#define VCNL4040_PS_TRIG        0x04  // Trigger one measurement

// PS_SC_EN - Sunlight cancellation (bit 0)
#define VCNL4040_PS_SC_MASK     0xFE  // Mask to clear bit 0
#define VCNL4040_PS_SC_DISABLE  0x00
#define VCNL4040_PS_SC_ENABLE   0x01

// =============================================================================
// PS_MS (0x04 High Byte) Bit Definitions
// =============================================================================

// WHITE_EN - White channel enable (bit 7) - NOTE: 0 = enabled, 1 = disabled
#define VCNL4040_WHITE_EN_MASK      0x7F  // Mask to clear bit 7
#define VCNL4040_WHITE_ENABLE       0x00  // White channel enabled
#define VCNL4040_WHITE_DISABLE      0x80  // White channel disabled

// PS_MS - Proximity mode selection (bit 6)
#define VCNL4040_PS_MS_MASK         0xBF  // Mask to clear bit 6
#define VCNL4040_PS_MS_NORMAL       0x00  // Normal interrupt mode
#define VCNL4040_PS_MS_LOGIC        0x40  // Logic output mode (INT stays low while close)

// LED_I - LED current (bits 2:0)
#define VCNL4040_LED_I_MASK         0xF8  // Mask to clear bits 2:0
#define VCNL4040_LED_I_50MA         0x00
#define VCNL4040_LED_I_75MA         0x01
#define VCNL4040_LED_I_100MA        0x02
#define VCNL4040_LED_I_120MA        0x03
#define VCNL4040_LED_I_140MA        0x04
#define VCNL4040_LED_I_160MA        0x05
#define VCNL4040_LED_I_180MA        0x06
#define VCNL4040_LED_I_200MA        0x07

// =============================================================================
// ALS_CONF (0x00 Low Byte) Bit Definitions
// =============================================================================

// ALS_IT - Integration time (bits 7:6)
#define VCNL4040_ALS_IT_MASK        0x3F  // Mask to clear bits 7:6
#define VCNL4040_ALS_IT_80MS        0x00
#define VCNL4040_ALS_IT_160MS       0x40
#define VCNL4040_ALS_IT_320MS       0x80
#define VCNL4040_ALS_IT_640MS       0xC0

// ALS_PERS - Persistence (bits 3:2)
#define VCNL4040_ALS_PERS_MASK      0xF3  // Mask to clear bits 3:2
#define VCNL4040_ALS_PERS_1         0x00
#define VCNL4040_ALS_PERS_2         0x04
#define VCNL4040_ALS_PERS_4         0x08
#define VCNL4040_ALS_PERS_8         0x0C

// ALS_INT_EN - Interrupt enable (bit 1)
#define VCNL4040_ALS_INT_MASK       0xFD  // Mask to clear bit 1
#define VCNL4040_ALS_INT_DISABLE    0x00
#define VCNL4040_ALS_INT_ENABLE     0x02

// ALS_SD - Shutdown (bit 0)
#define VCNL4040_ALS_SD_MASK        0xFE  // Mask to clear bit 0
#define VCNL4040_ALS_SD_ON          0x00
#define VCNL4040_ALS_SD_OFF         0x01

// =============================================================================
// INT_FLAG (0x0B High Byte) Bit Definitions
// =============================================================================
#define VCNL4040_INT_FLAG_PS_SPFLAG     0x40  // PS entering protection mode (bit 6)
#define VCNL4040_INT_FLAG_ALS_IF_L      0x20  // ALS crossed low threshold (bit 5)
#define VCNL4040_INT_FLAG_ALS_IF_H      0x10  // ALS crossed high threshold (bit 4)
#define VCNL4040_INT_FLAG_PS_IF_CLOSE   0x02  // PS crossed high threshold - close (bit 1)
#define VCNL4040_INT_FLAG_PS_IF_AWAY    0x01  // PS crossed low threshold - away (bit 0)

// =============================================================================
// Device Constants
// =============================================================================
// Note: Using VCNL4040_ID_VALUE to avoid conflict with Adafruit library's VCNL4040_DEVICE_ID
#define VCNL4040_ID_VALUE       0x0186
#define VCNL4040_DEFAULT_ADDR   0x60

// =============================================================================
// Enums for cleaner API
// =============================================================================

enum class VCNL4040_PSInterrupt : uint8_t {
    DISABLE = VCNL4040_PS_INT_DISABLE,
    CLOSE   = VCNL4040_PS_INT_CLOSE,
    AWAY    = VCNL4040_PS_INT_AWAY,
    BOTH    = VCNL4040_PS_INT_BOTH
};

enum class VCNL4040_PSPersistence : uint8_t {
    PERS_1 = 1,
    PERS_2 = 2,
    PERS_3 = 3,
    PERS_4 = 4
};

// Structure to hold interrupt flags after reading
struct VCNL4040_InterruptFlags {
    bool psClose;       // PS value exceeded high threshold
    bool psAway;        // PS value fell below low threshold
    bool alsHigh;       // ALS value exceeded high threshold
    bool alsLow;        // ALS value fell below low threshold
    bool psProtection;  // PS entered protection mode
    uint8_t raw;        // Raw flag byte for debugging
};

// =============================================================================
// VCNL4040 Class
// =============================================================================

class VCNL4040
{
public:
    /**
     * Constructor
     * @param address I2C address (default 0x60)
     */
    VCNL4040(uint8_t address = VCNL4040_DEFAULT_ADDR);

    /**
     * Initialize the sensor
     * @param wirePort Reference to TwoWire instance (default Wire)
     * @return true if successful, false if sensor not found
     */
    bool begin(TwoWire &wirePort = Wire);

    /**
     * Check if sensor is connected and responding
     * @return true if device responds at expected address
     */
    bool isConnected();

    /**
     * Get the device ID (should be 0x0186)
     * @return 16-bit device ID
     */
    uint16_t getID();

    // =========================================================================
    // Proximity Sensor - Basic Reading
    // =========================================================================
    
    /**
     * Read the proximity value
     * @return 12-bit or 16-bit proximity value (depending on PS_HD setting)
     */
    uint16_t readProximity();

    /**
     * Power on/off the proximity sensor
     * @param on true to enable, false to disable
     */
    void powerOnProximity(bool on = true);

    // =========================================================================
    // Proximity Sensor - Interrupt Configuration
    // =========================================================================

    /**
     * Set proximity interrupt type
     * @param type DISABLE, CLOSE, AWAY, or BOTH
     */
    void setProxInterruptType(VCNL4040_PSInterrupt type);

    /**
     * Set proximity high threshold (triggers "close" interrupt)
     * @param threshold 16-bit threshold value
     */
    void setProxHighThreshold(uint16_t threshold);

    /**
     * Set proximity low threshold (triggers "away" interrupt)
     * @param threshold 16-bit threshold value
     */
    void setProxLowThreshold(uint16_t threshold);

    /**
     * Set proximity interrupt persistence (consecutive hits before interrupt)
     * @param hits Number of consecutive hits (1-4)
     */
    void setProxPersistence(uint8_t hits);

    /**
     * Enable/disable smart persistence
     * Accelerates response time by taking 4 quick measurements when threshold crossed
     * @param enable true to enable
     */
    void enableSmartPersistence(bool enable);

    /**
     * Enable/disable proximity logic output mode
     * In this mode, INT stays LOW while object is close, goes HIGH when away
     * @param enable true to enable logic mode
     */
    void enableProxLogicMode(bool enable);

    // =========================================================================
    // Proximity Sensor - Configuration
    // =========================================================================

    /**
     * Set LED current
     * @param currentMA Current in mA: 50, 75, 100, 120, 140, 160, 180, or 200
     */
    void setLEDCurrent(uint16_t currentMA);

    /**
     * Set IR duty cycle (affects response time and power consumption)
     * @param dutyValue 40, 80, 160, or 320 (represents 1/x duty cycle)
     */
    void setIRDutyCycle(uint16_t dutyValue);

    /**
     * Set proximity integration time
     * @param timeValue 1, 2, 3, 4, or 8 (represents xT integration time)
     */
    void setProxIntegrationTime(uint8_t timeValue);

    /**
     * Set proximity resolution
     * @param bits 12 or 16 bit resolution
     */
    void setProxResolution(uint8_t bits);

    /**
     * Set multi-pulse count
     * @param pulses 1, 2, 4, or 8 pulses
     */
    void setMultiPulse(uint8_t pulses);

    /**
     * Set cancellation level (subtracted from proximity readings)
     * @param cancelValue 16-bit cancellation value
     */
    void setProxCancellation(uint16_t cancelValue);

    /**
     * Enable/disable sunlight cancellation
     * @param enable true to enable
     */
    void enableSunlightCancellation(bool enable);

    // =========================================================================
    // Ambient Light Sensor
    // =========================================================================

    /**
     * Read the ambient light value
     * @return 16-bit ALS value
     */
    uint16_t readAmbientLight();

    /**
     * Read the white channel value
     * @return 16-bit white channel value
     */
    uint16_t readWhite();

    /**
     * Power on/off the ambient light sensor
     * @param on true to enable, false to disable
     */
    void powerOnAmbient(bool on = true);

    /**
     * Enable/disable the white channel
     * @param enable true to enable
     */
    void enableWhiteChannel(bool enable);

    /**
     * Set ALS integration time
     * @param timeMS 80, 160, 320, or 640 milliseconds
     */
    void setALSIntegrationTime(uint16_t timeMS);

    /**
     * Enable/disable ALS interrupts
     * @param enable true to enable
     */
    void enableALSInterrupts(bool enable);

    /**
     * Set ALS high threshold
     * @param threshold 16-bit threshold value
     */
    void setALSHighThreshold(uint16_t threshold);

    /**
     * Set ALS low threshold
     * @param threshold 16-bit threshold value
     */
    void setALSLowThreshold(uint16_t threshold);

    /**
     * Set ALS interrupt persistence
     * @param hits 1, 2, 4, or 8 consecutive hits
     */
    void setALSPersistence(uint8_t hits);

    // =========================================================================
    // Interrupt Handling
    // =========================================================================

    /**
     * Read and clear interrupt flags
     * NOTE: Reading the INT_Flag register automatically clears all flags
     * and resets the INT pin to HIGH
     * @return Structure containing all interrupt flags
     */
    VCNL4040_InterruptFlags readInterruptFlags();

    /**
     * Check if a "close" interrupt occurred (PS above high threshold)
     * NOTE: This reads and clears all interrupt flags
     * @return true if close interrupt was triggered
     */
    bool isClose();

    /**
     * Check if an "away" interrupt occurred (PS below low threshold)
     * NOTE: This reads and clears all interrupt flags
     * @return true if away interrupt was triggered
     */
    bool isAway();

    /**
     * Check if ALS high interrupt occurred
     * NOTE: This reads and clears all interrupt flags
     * @return true if ALS high interrupt was triggered
     */
    bool isLight();

    /**
     * Check if ALS low interrupt occurred
     * NOTE: This reads and clears all interrupt flags
     * @return true if ALS low interrupt was triggered
     */
    bool isDark();

    // =========================================================================
    // Active Force Mode (Single-Shot Measurement)
    // =========================================================================

    /**
     * Enable/disable active force mode
     * In this mode, the sensor stays in standby until triggered
     * @param enable true to enable
     */
    void enableActiveForceMode(bool enable);

    /**
     * Trigger a single proximity measurement (requires active force mode)
     * After measurement, read with readProximity()
     */
    void triggerProxMeasurement();

    // =========================================================================
    // Low-Level Register Access (for advanced use)
    // =========================================================================

    /**
     * Read a 16-bit register
     * @param commandCode Register address
     * @return 16-bit register value
     */
    uint16_t readRegister(uint8_t commandCode);

    /**
     * Write a 16-bit register
     * @param commandCode Register address
     * @param value 16-bit value to write
     * @return true if successful
     */
    bool writeRegister(uint8_t commandCode, uint16_t value);

    /**
     * Read only the low byte of a register
     * @param commandCode Register address
     * @return Low byte value
     */
    uint8_t readRegisterLow(uint8_t commandCode);

    /**
     * Read only the high byte of a register
     * @param commandCode Register address
     * @return High byte value
     */
    uint8_t readRegisterHigh(uint8_t commandCode);

    /**
     * Write only the low byte of a register (preserves high byte)
     * @param commandCode Register address
     * @param value Byte value to write
     * @return true if successful
     */
    bool writeRegisterLow(uint8_t commandCode, uint8_t value);

    /**
     * Write only the high byte of a register (preserves low byte)
     * @param commandCode Register address
     * @param value Byte value to write
     * @return true if successful
     */
    bool writeRegisterHigh(uint8_t commandCode, uint8_t value);

private:
    TwoWire *_i2cPort;
    uint8_t _address;

    /**
     * Helper to modify specific bits in a register byte
     * @param commandCode Register address
     * @param isHighByte true for high byte, false for low byte
     * @param mask Bits to preserve (1 = keep, 0 = modify)
     * @param value New value for the masked bits
     */
    void bitMask(uint8_t commandCode, bool isHighByte, uint8_t mask, uint8_t value);
};

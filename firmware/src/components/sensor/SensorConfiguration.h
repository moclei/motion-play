#ifndef SENSOR_CONFIGURATION_H
#define SENSOR_CONFIGURATION_H

#include <Arduino.h>

// Sensor configuration structure
// Tracks current VCNL4040 sensor settings
struct SensorConfiguration
{
    uint16_t sample_rate_hz = 1000;
    String led_current = "200mA";
    String integration_time = "1T";
    bool high_resolution = true;
    bool read_ambient = true; // If false, only proximity is read (faster)
    uint32_t i2c_clock_khz = 400; // I2C clock speed in kHz (400 or 1000)
    uint16_t actual_sample_rate_hz = 0; // Measured actual sample rate (populated during session)

    // Note: Configuration is applied during sensor initialization.
    // Dynamic reconfiguration requires sensor reinitialization.
};

#endif


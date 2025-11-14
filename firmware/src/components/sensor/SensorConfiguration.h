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

    // Note: String/enum conversion functions will be added in Phase 3-B
    // when implementing dynamic sensor reconfiguration.
    // For now, configuration is stored as strings and applied on device restart.
};

#endif


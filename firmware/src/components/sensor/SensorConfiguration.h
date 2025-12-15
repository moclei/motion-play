#ifndef SENSOR_CONFIGURATION_H
#define SENSOR_CONFIGURATION_H

#include <Arduino.h>

// Sensor mode determines how we read sensors
enum class SensorMode
{
    POLLING_MODE,  // Traditional high-frequency polling (read sensors at sample_rate_hz)
    INTERRUPT_MODE // Interrupt-based detection (sensors signal when thresholds crossed)
};

// Sensor configuration structure
// Tracks current VCNL4040 sensor settings
struct SensorConfiguration
{
    // === Primary Mode Selection ===
    SensorMode sensor_mode = SensorMode::POLLING_MODE; // How to read sensors

    // === Proximity Polling Mode Settings ===
    uint16_t sample_rate_hz = 1000;
    String led_current = "200mA";
    String integration_time = "1T";
    String duty_cycle = "1/40"; // Controls measurement frequency: 1/40 (~200Hz), 1/80 (~100Hz), 1/160 (~50Hz), 1/320 (~25Hz)
    String multi_pulse = "1";   // Multi-pulse mode: "1", "2", "4", "8" pulses per measurement (more = stronger signal)
    bool high_resolution = true;
    bool read_ambient = true;           // If false, only proximity is read (faster)
    uint32_t i2c_clock_khz = 400;       // I2C clock speed in kHz (400 or 1000)
    uint16_t actual_sample_rate_hz = 0; // Measured actual sample rate (populated during session)

    // === Interrupt Mode Settings ===
    // Note: Uses calibration-based approach - thresholds are relative to baseline (set via PS_CANC)
    uint16_t interrupt_threshold_margin = 10; // Trigger when prox exceeds baseline + margin
    uint16_t interrupt_hysteresis = 5;        // Gap between high and low thresholds
    uint8_t interrupt_integration_time = 8;   // Integration time for interrupt mode (1-8 for 1T-8T)
    uint8_t interrupt_multi_pulse = 8;        // Multi-pulse count (1, 2, 4, 8)
    uint8_t interrupt_persistence = 1;        // Consecutive hits before interrupt (1-4)
    bool interrupt_smart_persistence = true;  // Enable fast response mode
    String interrupt_mode = "normal";         // "normal" or "logic" (logic = INT stays LOW while close)

    // Note: Configuration is applied during sensor initialization.
    // Dynamic reconfiguration requires sensor reinitialization.
};

#endif

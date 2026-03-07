#pragma once

#include <Arduino.h>
#include <atomic>
#include <vector>
#include <Adafruit_VCNL4040.h>
#include "../mux/MuxController.h"
#include "SensorConfiguration.h"
#include "sensor_types.h"

// Forward declaration for session confirmation counters
struct SessionSummary;

class SensorManager
{
private:
    MuxController muxController;

    bool initialized = false;
    TaskHandle_t sensorTask = NULL;
    TaskHandle_t stopRequestorTask = NULL;
    QueueHandle_t dataQueue = NULL;
    SensorConfiguration *activeConfig = nullptr; // Reference to active configuration

    // Baseline cancellation values per sensor (for PS_CANC register)
    // These values are subtracted by the sensor hardware to compensate for
    // cover window reflections and other constant offsets
    uint16_t baselineValues[NUM_SENSORS] = {0};

    // Graceful shutdown flag — set on Core 1, read on Core 0
    std::atomic<bool> stopRequested{false};

    // Session Confirmation: pointer to active session summary for counter updates
    // Set when collection starts, cleared when collection stops.
    // Written only from Core 0 sensor task — no synchronization needed.
    struct SessionSummary *activeSummary = nullptr;

    void debugI2CScan();  // Debug: scan I2C bus on each TCA channel
    static void sensorTaskFunction(void *parameter);
    bool calibrateSensorBaseline(uint8_t sensorIndex); // Calibrate single sensor PS_CANC

    // Configuration helpers
    VCNL4040_LEDCurrent parseLEDCurrent(const String &current);
    VCNL4040_ProximityIntegration parseIntegrationTime(const String &time);
    VCNL4040_LEDDutyCycle parseDutyCycle(const String &duty);
    uint8_t parseMultiPulse(const String &mp); // Multi-pulse mode: 1, 2, 4, or 8 pulses
    bool applySensorConfig(uint8_t sensorIndex);

public:
    SensorManager();
    bool init(SensorConfiguration *config = nullptr);
    bool startCollection(QueueHandle_t queue, SessionSummary *summary = nullptr);
    void stopCollection();
    bool isCollecting();
    bool readSensor(uint8_t sensorIndex, SensorReading &reading);
    std::vector<SensorMetadata> getSensorMetadata();
    bool reinitialize(SensorConfiguration *config);
    void dumpSensorConfiguration();                 // Diagnostic: print all sensor configs to serial
    bool calibrateProximityCancellation();          // Calibrate PS_CANC for all sensors (cover offset)
    uint16_t getBaselineValue(uint8_t sensorIndex); // Get stored baseline for a sensor
};
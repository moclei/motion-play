#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include <Arduino.h>
#include <vector>
#include "../tca9548a/TCA9548A.h"
#include <Adafruit_VCNL4040.h>
#include "SensorConfiguration.h"

// Forward declaration for session confirmation counters
struct SessionSummary;

// Sensor configuration
#define NUM_SENSORS 6
#define SAMPLE_RATE_HZ 1000
#define SAMPLE_INTERVAL_US (1000000 / SAMPLE_RATE_HZ)

// Simple PCA9546A wrapper class (for local multiplexing on each sensor board)
class PCA9546A
{
private:
    uint8_t address;

public:
    PCA9546A(uint8_t addr = 0x70) : address(addr) {}

    bool begin()
    {
        Wire.beginTransmission(address);
        return (Wire.endTransmission() == 0);
    }

    bool selectChannel(uint8_t channel)
    {
        if (channel > 3)
            return false;
        Wire.beginTransmission(address);
        Wire.write(1 << channel);
        return (Wire.endTransmission() == 0);
    }

    bool disableAllChannels()
    {
        Wire.beginTransmission(address);
        Wire.write(0x00);
        return (Wire.endTransmission() == 0);
    }
};

// Sensor reading structure
struct SensorReading
{
    uint32_t timestamp_us; // Microsecond timestamp (was timestamp_ms prior to microsecond-timestamps initiative)
    uint8_t position;      // 0-5 (sensor array index)
    uint8_t pcb_id;        // 1-3 (which sensor board: P1, P2, P3)
    uint8_t side;          // 1-2 (which sensor on board: S1, S2)
    uint16_t proximity;
    uint16_t ambient;
};

// Sensor metadata structure
struct SensorMetadata
{
    uint8_t position;
    uint8_t pcb_id;
    uint8_t side;
    bool active;
    String name; // "P1S1", "P2S2", etc.
};

class SensorManager
{
private:
    TCA9548A mux;
    Adafruit_VCNL4040 sensors[NUM_SENSORS];

    // PCA9546A multiplexers (one per sensor board, up to 3 boards)
    PCA9546A pca_instances[3] = {PCA9546A(0x74), PCA9546A(0x75), PCA9546A(0x76)};
    uint8_t pca_addresses[3] = {0, 0, 0}; // Detected addresses (0 = not found)

    // Sensor mapping structure
    struct SensorMap
    {
        uint8_t tca_channel; // 0-2 (which sensor board on TCA)
        uint8_t pca_channel; // 0-1 (which sensor on board: S1/S2)
    };

    const SensorMap sensorMapping[NUM_SENSORS] = {
        {0, 0}, // Sensor 0: P1S1 (TCA0, PCA0)
        {0, 1}, // Sensor 1: P1S2 (TCA0, PCA1)
        {1, 0}, // Sensor 2: P2S1 (TCA1, PCA0)
        {1, 1}, // Sensor 3: P2S2 (TCA1, PCA1)
        {2, 0}, // Sensor 4: P3S1 (TCA2, PCA0)
        {2, 1}  // Sensor 5: P3S2 (TCA2, PCA1)
    };

    bool initialized = false;
    bool sensorsActive[NUM_SENSORS] = {false}; // Track which sensors initialized
    TaskHandle_t sensorTask = NULL;
    QueueHandle_t dataQueue = NULL;
    SensorConfiguration *activeConfig = nullptr; // Reference to active configuration

    // Baseline cancellation values per sensor (for PS_CANC register)
    // These values are subtracted by the sensor hardware to compensate for
    // cover window reflections and other constant offsets
    uint16_t baselineValues[NUM_SENSORS] = {0};

    // Graceful shutdown flag - volatile because accessed from multiple cores
    volatile bool stopRequested = false;

    // Session Confirmation: pointer to active session summary for counter updates
    // Set when collection starts, cleared when collection stops.
    // Written only from Core 0 sensor task — no synchronization needed.
    struct SessionSummary *activeSummary = nullptr;

    bool initializePCA();
    void cleanupI2CBus(); // Clean up I2C bus state
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

#endif
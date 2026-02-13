#ifndef SESSION_MANAGER_H
#define SESSION_MANAGER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <vector>
#include "../sensor/SensorManager.h"
#include "../interrupt/InterruptManager.h"
#include "../memory/PSRAMAllocator.h"

enum SessionState
{
    IDLE,
    COLLECTING,
    UPLOADING
};

// Session Confirmation: tracks pipeline integrity counters during a session.
// Populated by SensorManager (collection), SessionManager (buffering),
// and DataTransmitter (transmission). Sent as a separate MQTT message
// after all data batches to verify end-to-end data delivery.
struct SessionSummary
{
    uint32_t total_cycles = 0;                      // Sensor loop iterations
    uint32_t readings_collected[NUM_SENSORS] = {0}; // Successful reads per sensor position
    uint32_t i2c_errors[NUM_SENSORS] = {0};         // Failed reads per sensor position
    uint32_t queue_drops = 0;                       // Readings lost due to full queue
    uint32_t buffer_drops = 0;                      // Readings lost due to full buffer
    uint32_t total_readings_transmitted = 0;        // Sum of readings across all MQTT batches
    uint32_t total_batches_transmitted = 0;         // Number of MQTT batches sent
    uint16_t measured_cycle_rate_hz = 0;            // total_cycles / (duration_ms / 1000)
    uint32_t duration_ms = 0;                       // Actual session duration
    uint32_t theoretical_max_readings = 0;          // sample_rate_hz * (duration_ms/1000) * active_sensors
    uint8_t num_active_sensors = 0;                 // How many sensors were active

    void reset()
    {
        total_cycles = 0;
        memset(readings_collected, 0, sizeof(readings_collected));
        memset(i2c_errors, 0, sizeof(i2c_errors));
        queue_drops = 0;
        buffer_drops = 0;
        total_readings_transmitted = 0;
        total_batches_transmitted = 0;
        measured_cycle_rate_hz = 0;
        duration_ms = 0;
        theoretical_max_readings = 0;
        num_active_sensors = 0;
    }
};

// Session type - determines data structure and transmission format
// Note: Using SESSION_* prefix to avoid conflict with ESP32 SDK macros
enum class SessionType
{
    PROXIMITY,      // Traditional polling mode - SensorReading data
    INTERRUPT_BASED // Interrupt-based mode - InterruptEvent data
};

class SessionManager
{
private:
    SessionState state = IDLE;
    SessionType sessionType = SessionType::PROXIMITY;
    QueueHandle_t dataQueue = NULL;

    String sessionId;
    String deviceIdPrefix; // Short prefix for session IDs (e.g. "device-002")
    unsigned long sessionStartTime = 0;
    unsigned long sessionDuration = 0;

    // CRITICAL: Use PSRAM allocator to prevent heap exhaustion
    // 30,000 samples × 12 bytes = 360KB would exhaust the 400KB heap
    // PSRAM has 8MB available
    std::vector<SensorReading, PSRAMAllocator<SensorReading>> dataBuffer;
    std::vector<SensorMetadata> activeSensors;

    // Interrupt session buffer (much smaller - typically <1000 events)
    std::vector<InterruptEvent> interruptBuffer;

    static const size_t MAX_BUFFER_SIZE = 30000;      // 30 seconds * 1000 Hz (proximity)
    static const size_t MAX_INTERRUPT_BUFFER = 10000; // Max interrupt events

    // Session Confirmation: pipeline integrity counters
    SessionSummary sessionSummary;

    void generateSessionId();

public:
    SessionManager();

    // Device ID for session ID generation
    void setDeviceId(const String &fullDeviceId);

    // Session control
    bool startSession();
    bool stopSession();
    void processQueue();
    void clearBuffer();

    // Session type
    void setSessionType(SessionType type) { sessionType = type; }
    SessionType getSessionType() const { return sessionType; }

    // State and metadata
    bool hasData();
    size_t getDataCount();
    SessionState getState();
    String getSessionId();
    unsigned long getDuration();
    unsigned long getStartTime();
    QueueHandle_t getQueue();

    // Proximity mode data
    std::vector<SensorReading, PSRAMAllocator<SensorReading>> &getDataBuffer();
    void setSensorMetadata(const std::vector<SensorMetadata> &metadata);
    const std::vector<SensorMetadata> &getSensorMetadata();

    // Interrupt mode data
    std::vector<InterruptEvent> &getInterruptBuffer() { return interruptBuffer; }
    const std::vector<InterruptEvent> &getInterruptBuffer() const { return interruptBuffer; }
    size_t getInterruptEventCount() const { return interruptBuffer.size(); }

    // Add interrupt event to buffer
    bool addInterruptEvent(const InterruptEvent &event);

    // Session Confirmation: pipeline integrity
    SessionSummary &getSessionSummary() { return sessionSummary; }
    const SessionSummary &getSessionSummary() const { return sessionSummary; }
    void finalizeSessionSummary(const SensorConfiguration *config, uint8_t numActiveSensors);
};

#endif
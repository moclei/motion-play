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
};

#endif
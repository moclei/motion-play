#ifndef SESSION_MANAGER_H
#define SESSION_MANAGER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <vector>
#include "../sensor/SensorManager.h"
#include "../memory/PSRAMAllocator.h"

enum SessionState
{
    IDLE,
    COLLECTING,
    UPLOADING
};

class SessionManager
{
private:
    SessionState state = IDLE;
    QueueHandle_t dataQueue = NULL;

    String sessionId;
    unsigned long sessionStartTime = 0;
    unsigned long sessionDuration = 0;
    // CRITICAL: Use PSRAM allocator to prevent heap exhaustion
    // 30,000 samples × 12 bytes = 360KB would exhaust the 400KB heap
    // PSRAM has 8MB available
    std::vector<SensorReading, PSRAMAllocator<SensorReading>> dataBuffer;
    std::vector<SensorMetadata> activeSensors;

    static const size_t MAX_BUFFER_SIZE = 30000; // 30 seconds * 1000 Hz

    void generateSessionId();

public:
    SessionManager();
    bool startSession();
    bool stopSession();
    void processQueue();
    bool hasData();
    size_t getDataCount();
    SessionState getState();
    String getSessionId();
    unsigned long getDuration();
    unsigned long getStartTime();  // Actual session start time (millis at start)
    std::vector<SensorReading, PSRAMAllocator<SensorReading>> &getDataBuffer();
    void setSensorMetadata(const std::vector<SensorMetadata> &metadata);
    const std::vector<SensorMetadata> &getSensorMetadata();
    void clearBuffer();
    QueueHandle_t getQueue();
};

#endif
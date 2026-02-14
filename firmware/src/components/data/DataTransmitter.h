#ifndef DATA_TRANSMITTER_H
#define DATA_TRANSMITTER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include "../mqtt/MQTTManager.h"
#include "../session/SessionManager.h"
#include "../sensor/SensorConfiguration.h"
#include "../memory/PSRAMAllocator.h"

class DataTransmitter
{
private:
    MQTTManager *mqttManager;
    static const size_t BATCH_SIZE = 25;                    // Proximity: 25 samples per batch
    static const size_t INT_BATCH_SIZE = 100;               // Interrupt: 100 events per batch
    static const size_t LIVE_DEBUG_BATCH_SIZE = 200;        // Live Debug: larger batches for speed
    static const unsigned long LIVE_DEBUG_BATCH_DELAY = 20; // ms between Live Debug batches

    // Session Confirmation: pointer to active session summary for transmission counters
    SessionSummary *activeSummary = nullptr;

public:
    DataTransmitter(MQTTManager *mqtt);

    // Session Confirmation: set summary pointer for transmission counting
    void setSessionSummary(SessionSummary *summary) { activeSummary = summary; }

    // Transmit session based on its type
    bool transmitSession(SessionManager &session, const SensorConfiguration *config = nullptr);

    // Proximity mode transmission
    bool transmitProximitySession(SessionManager &session, const SensorConfiguration *config = nullptr);
    bool transmitBatch(const String &sessionId,
                       const String &deviceId,
                       unsigned long startTime,
                       unsigned long duration,
                       std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings,
                       size_t offset,
                       size_t count,
                       const std::vector<SensorMetadata> *sensorMetadata,
                       const SensorConfiguration *config = nullptr);

    // Interrupt mode transmission
    bool transmitInterruptSession(SessionManager &session, const SensorConfiguration *config = nullptr);
    bool transmitInterruptBatch(const String &sessionId,
                                const String &deviceId,
                                unsigned long startTime,
                                unsigned long duration,
                                const std::vector<InterruptEvent> &events,
                                size_t offset,
                                size_t count,
                                bool isFirstBatch,
                                const SensorConfiguration *config = nullptr);

    // Live Debug capture transmission
    // Returns the generated session_id on success, or empty String on failure
    String transmitLiveDebugCapture(
        std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings,
        size_t startIdx,
        size_t count,
        const char *captureReason,
        const char *detectionDirection,
        float detectionConfidence,
        const SensorConfiguration *config = nullptr);

    // Session Confirmation: transmit pipeline integrity summary as separate MQTT message
    bool transmitSessionSummary(const SessionSummary &summary,
                                const String &sessionId,
                                const String &deviceId);
};

#endif
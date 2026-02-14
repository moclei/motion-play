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
    static const size_t BATCH_SIZE = 25;      // Proximity: 25 samples per batch
    static const size_t INT_BATCH_SIZE = 100; // Interrupt: 100 events per batch

    // Live Debug: larger batches + shorter delays for fast capture transmission
    static const size_t LIVE_DEBUG_BATCH_SIZE = 200;
    static const unsigned long LIVE_DEBUG_BATCH_DELAY = 20; // ms between batches

public:
    DataTransmitter(MQTTManager *mqtt);

    // Transmit session based on its type
    bool transmitSession(SessionManager &session, const SensorConfiguration *config = nullptr);

    // Proximity mode transmission (existing)
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

    // Interrupt mode transmission (new)
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

    // Live Debug: transmit a capture window (bypasses SessionManager)
    bool transmitLiveDebugCapture(
        std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings,
        size_t startIdx,
        size_t count,
        const char *captureReason,      // "detection" or "missed_event"
        const char *detectionDirection, // "a_to_b", "b_to_a", or nullptr
        float detectionConfidence,      // confidence score, or 0.0 for missed
        const SensorConfiguration *config = nullptr);
};

#endif
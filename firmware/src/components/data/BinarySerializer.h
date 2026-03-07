#pragma once

#include <Arduino.h>
#include <vector>
#include "sensor_types.h"
#include "../session/SessionManager.h"
#include "../memory/PSRAMAllocator.h"

class MQTTManager;
class SensorConfiguration;

class BinarySerializer
{
private:
    MQTTManager *mqttManager;

public:
    BinarySerializer(MQTTManager *mqtt);

    // Packs all readings as 9-byte structs, base64-encodes, and merges data + summary
    // into a single MQTT message. No separate summary message needed.
    String transmitLiveDebugCaptureBinary(
        std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings,
        size_t startIdx,
        size_t count,
        const char *captureReason,
        const char *detectionDirection,
        float detectionConfidence,
        const SessionSummary &summary,
        const SensorConfiguration *config = nullptr);
};

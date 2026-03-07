#include "BinarySerializer.h"
#include "SerializationHelpers.h"
#include "../mqtt/MQTTManager.h"
#include "mbedtls/base64.h"

BinarySerializer::BinarySerializer(MQTTManager *mqtt) : mqttManager(mqtt) {}

String BinarySerializer::transmitLiveDebugCaptureBinary(
    std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings,
    size_t startIdx,
    size_t count,
    const char *captureReason,
    const char *detectionDirection,
    float detectionConfidence,
    const SessionSummary &summary,
    const SensorConfiguration *config)
{
    if (count == 0)
    {
        Serial.println("Live Debug Binary: No readings to transmit");
        return "";
    }

    // Generate session ID
    String deviceId = mqttManager->getDeviceId();
    String deviceSuffix = deviceId;
    int lastDash = deviceId.lastIndexOf('-');
    int secondLastDash = deviceId.lastIndexOf('-', lastDash - 1);
    if (secondLastDash >= 0)
    {
        deviceSuffix = deviceId.substring(secondLastDash + 1);
    }
    String sessionId = deviceSuffix + "_" + String(millis());

    // Calculate timing from the readings themselves (timestamps are in microseconds)
    unsigned long startTime = readings[startIdx].timestamp_us;
    unsigned long endTime = readings[startIdx + count - 1].timestamp_us;
    unsigned long durationUs = endTime - startTime;
    unsigned long durationMs = durationUs / 1000;

    Serial.printf("Live Debug Binary: reason=%s, readings=%d, duration=%lums\n",
                  captureReason, count, durationMs);

    // 1. Pack readings into binary buffer (9 bytes per reading, little-endian)
    size_t binarySize = count * 9;
    uint8_t *binaryBuf = (uint8_t *)ps_malloc(binarySize);
    if (!binaryBuf)
    {
        Serial.printf("ERROR: Failed to allocate %d bytes in PSRAM for binary buffer\n", binarySize);
        return "";
    }

    for (size_t i = 0; i < count; i++)
    {
        SensorReading &r = readings[startIdx + i];
        size_t off = i * 9;
        memcpy(binaryBuf + off, &r.timestamp_us, 4);
        binaryBuf[off + 4] = r.position;
        memcpy(binaryBuf + off + 5, &r.proximity, 2);
        memcpy(binaryBuf + off + 7, &r.ambient, 2);
    }

    // 2. Base64-encode
    size_t base64Len = 0;
    mbedtls_base64_encode(NULL, 0, &base64Len, binaryBuf, binarySize);

    unsigned char *base64Buf = (unsigned char *)ps_malloc(base64Len + 1);
    if (!base64Buf)
    {
        Serial.printf("ERROR: Failed to allocate %d bytes in PSRAM for base64 buffer\n", base64Len + 1);
        free(binaryBuf);
        return "";
    }

    size_t written = 0;
    mbedtls_base64_encode(base64Buf, base64Len + 1, &written, binaryBuf, binarySize);
    base64Buf[written] = '\0';
    free(binaryBuf);

    Serial.printf("Live Debug Binary: packed %d bytes -> %d bytes base64\n", binarySize, written);

    // 3. Build JSON document
    // ArduinoJson stores char* by reference (zero-copy), so the doc only needs
    // memory for the JSON structure itself, not the base64 string content.
    DynamicJsonDocument doc(8192);

    // Session metadata
    doc["session_id"] = sessionId;
    doc["device_id"] = deviceId;
    doc["session_type"] = "proximity";
    doc["mode"] = "live_debug";
    doc["start_timestamp"] = startTime;
    doc["duration_ms"] = durationMs;
    doc["timestamp_unit"] = "us";
    doc["sample_rate"] = (config != nullptr && config->actual_sample_rate_hz > 0)
                             ? config->actual_sample_rate_hz
                             : SAMPLE_RATE_HZ;

    // Capture metadata
    doc["capture_reason"] = captureReason;
    if (detectionDirection != nullptr)
    {
        doc["detection_direction"] = detectionDirection;
        doc["detection_confidence"] = detectionConfidence;
    }

    // Binary reading payload
    doc["reading_format"] = "bin9";
    doc["reading_count"] = count;
    doc["readings_b64"] = (const char *)base64Buf;

    serialization::serializeConfig(doc, config);
    serialization::serializeCalibration(doc);

    // Inline session summary — Lambda processes everything in one shot
    doc["type"] = "session_summary";
    JsonObject summaryObj = doc.createNestedObject("summary");
    serialization::serializeSummary(summaryObj, summary);
    summaryObj["total_readings_transmitted"] = count;
    summaryObj["total_batches_transmitted"] = 1;

    if (doc.overflowed())
    {
        Serial.printf("ERROR: JSON doc overflow! (usage=%d/8192 bytes)\n", doc.memoryUsage());
        free(base64Buf);
        return "";
    }

    // 4. Publish via streaming API (payload exceeds the 32KB PubSubClient buffer)
    bool success = mqttManager->publishDataStreaming(doc);
    free(base64Buf);

    if (!success)
    {
        Serial.println("ERROR: Live Debug Binary MQTT streaming publish failed!");
        return "";
    }

    Serial.printf("Live Debug Binary: session=%s, %d readings in 1 message\n",
                  sessionId.c_str(), count);
    return sessionId;
}

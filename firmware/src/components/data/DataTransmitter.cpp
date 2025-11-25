#include "DataTransmitter.h"

DataTransmitter::DataTransmitter(MQTTManager *mqtt) : mqttManager(mqtt)
{
    // Constructor
}

bool DataTransmitter::transmitBatch(const String &sessionId,
                                    const String &deviceId,
                                    unsigned long startTime,
                                    unsigned long duration,
                                    std::vector<SensorReading> &readings,
                                    size_t offset,
                                    size_t count,
                                    const std::vector<SensorMetadata> *sensorMetadata,
                                    const SensorConfiguration *config)
{
    // Create JSON document
    DynamicJsonDocument doc(8192); // 8KB for batch

    doc["session_id"] = sessionId;
    doc["device_id"] = deviceId;
    doc["start_timestamp"] = startTime;
    doc["duration_ms"] = duration;
    doc["sample_rate"] = SAMPLE_RATE_HZ;
    doc["batch_offset"] = offset;
    doc["batch_size"] = count;

    // Add sensor metadata AND configuration (only in first batch)
    if (offset == 0 && sensorMetadata != nullptr)
    {
        // Add active sensor list
        JsonArray sensorArray = doc.createNestedArray("active_sensors");

        for (const auto &sensor : *sensorMetadata)
        {
            JsonObject sensorObj = sensorArray.createNestedObject();
            sensorObj["pos"] = sensor.position;
            sensorObj["pcb"] = sensor.pcb_id;
            sensorObj["side"] = sensor.side;
            sensorObj["name"] = sensor.name;
            sensorObj["active"] = sensor.active;
        }

        // Add VCNL4040 configuration parameters
        if (config != nullptr)
        {
            JsonObject configObj = doc.createNestedObject("vcnl4040_config");
            configObj["sample_rate_hz"] = config->sample_rate_hz;
            configObj["led_current"] = config->led_current;
            configObj["integration_time"] = config->integration_time;
            configObj["high_resolution"] = config->high_resolution;
            configObj["read_ambient"] = config->read_ambient;
            configObj["i2c_clock_khz"] = config->i2c_clock_khz;
            configObj["actual_sample_rate_hz"] = config->actual_sample_rate_hz;
        }
    }

    // Add readings array
    JsonArray readingsArray = doc.createNestedArray("readings");

    for (size_t i = 0; i < count; i++)
    {
        SensorReading &reading = readings[offset + i];

        JsonObject readingObj = readingsArray.createNestedObject();
        readingObj["ts"] = reading.timestamp_ms;
        readingObj["pos"] = reading.position;
        readingObj["pcb"] = reading.pcb_id;
        readingObj["side"] = reading.side;
        readingObj["prox"] = reading.proximity;
        readingObj["amb"] = reading.ambient;
    }

    // Serialize to string
    String payload;
    size_t payloadSize = serializeJson(doc, payload);

    // Publish via MQTT
    Serial.print("Transmitting batch ");
    Serial.print(offset / BATCH_SIZE);
    Serial.print(" (");
    Serial.print(count);
    Serial.print(" samples, ");
    Serial.print(payloadSize);
    Serial.println(" bytes)");

    bool success = mqttManager->publishData(doc);

    if (!success)
    {
        Serial.println("ERROR: MQTT publish failed!");
        Serial.print("  Payload size: ");
        Serial.print(payloadSize);
        Serial.println(" bytes");
        Serial.print("  First 200 chars: ");
        Serial.println(payload.substring(0, 200));
    }

    return success;
}

bool DataTransmitter::transmitSession(SessionManager &session, const SensorConfiguration *config)
{
    if (!session.hasData())
    {
        Serial.println("No data to transmit");
        return false;
    }

    String sessionId = session.getSessionId();
    String deviceId = "motionplay-device-001"; // TODO: Get from config
    unsigned long startTime = millis() - session.getDuration();
    unsigned long duration = session.getDuration();

    std::vector<SensorReading> &readings = session.getDataBuffer();
    const std::vector<SensorMetadata> &sensorMetadata = session.getSensorMetadata();
    size_t totalReadings = readings.size();

    Serial.print("Transmitting session ");
    Serial.print(sessionId);
    Serial.print(" (");
    Serial.print(totalReadings);
    Serial.println(" readings)");

    // Send in batches
    size_t offset = 0;
    while (offset < totalReadings)
    {
        size_t remaining = totalReadings - offset;
        size_t batchCount = (remaining > BATCH_SIZE) ? BATCH_SIZE : remaining;

        // Pass sensor metadata and config only for first batch
        const std::vector<SensorMetadata> *metadataPtr = (offset == 0) ? &sensorMetadata : nullptr;
        const SensorConfiguration *configPtr = (offset == 0) ? config : nullptr;

        if (!transmitBatch(sessionId, deviceId, startTime, duration,
                           readings, offset, batchCount, metadataPtr, configPtr))
        {
            Serial.println("ERROR: Failed to transmit batch");
            return false;
        }

        offset += batchCount;

        // Small delay between batches to avoid overwhelming MQTT
        delay(100);
    }

    Serial.println("Session transmission complete!");
    return true;
}
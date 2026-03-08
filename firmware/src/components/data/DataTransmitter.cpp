#include "DataTransmitter.h"
#include "SerializationHelpers.h"
#include "../mqtt/MQTTManager.h"
#include "../memory/PSRAMAllocator.h"

DataTransmitter::DataTransmitter(MQTTManager *mqtt) : mqttManager(mqtt) {}

// ============================================================================
// Cooperative Transmission API
// ============================================================================

bool DataTransmitter::beginTransmission(SessionManager &session, const SensorConfiguration *config,
                                        const UploadContext &context)
{
    txContext_ = context;

    if (txState_ == TransmitState::TRANSMITTING)
    {
        Serial.println("ERROR: Transmission already in progress");
        txState_ = TransmitState::FAILED;
        return false;
    }

    if (!session.hasData())
    {
        Serial.println("No data to transmit");
        txState_ = TransmitState::FAILED;
        return false;
    }

    txSessionId_ = session.getSessionId();
    txDeviceId_ = mqttManager->getDeviceId();
    txStartTime_ = session.getStartTime();
    txDuration_ = session.getDuration();
    txConfig_ = config;
    txOffset_ = 0;
    txLastBatchTime_ = 0;
    txSessionType_ = session.getSessionType();

    if (txSessionType_ == SessionType::INTERRUPT_BASED)
    {
        txEvents_ = &session.getInterruptBuffer();
        txTotalItems_ = txEvents_->size();
        txBatchDelay_ = INT_BATCH_DELAY_MS;
        txReadings_ = nullptr;
        txSensorMetadata_ = nullptr;

        Serial.printf("Transmitting interrupt session %s (%d events)\n",
                      txSessionId_.c_str(), txTotalItems_);
    }
    else
    {
        txReadings_ = &session.getDataBuffer();
        txSensorMetadata_ = &session.getSensorMetadata();
        txTotalItems_ = txReadings_->size();
        txBatchDelay_ = BATCH_DELAY_MS;
        txEvents_ = nullptr;

        Serial.printf("Transmitting proximity session %s (%d readings)\n",
                      txSessionId_.c_str(), txTotalItems_);
    }

    txState_ = TransmitState::TRANSMITTING;
    return true;
}

TransmitState DataTransmitter::tick()
{
    if (txState_ != TransmitState::TRANSMITTING)
        return txState_;

    if (txLastBatchTime_ > 0 && (millis() - txLastBatchTime_) < txBatchDelay_)
        return txState_;

    bool success;
    size_t remaining = txTotalItems_ - txOffset_;
    size_t batchCount;

    if (txSessionType_ == SessionType::INTERRUPT_BASED)
    {
        batchCount = (remaining > INT_BATCH_SIZE) ? INT_BATCH_SIZE : remaining;
        bool isFirst = (txOffset_ == 0);
        success = transmitInterruptBatch(txSessionId_, txDeviceId_, txStartTime_, txDuration_,
                                         *txEvents_, txOffset_, batchCount, isFirst, txConfig_);
    }
    else
    {
        batchCount = (remaining > BATCH_SIZE) ? BATCH_SIZE : remaining;
        const std::vector<SensorMetadata> *metaPtr = (txOffset_ == 0) ? txSensorMetadata_ : nullptr;
        success = transmitBatch(txSessionId_, txDeviceId_, txStartTime_, txDuration_,
                                *txReadings_, txOffset_, batchCount, metaPtr, txConfig_);
    }

    if (!success)
    {
        Serial.println("ERROR: Failed to transmit batch");
        txState_ = TransmitState::FAILED;
        return txState_;
    }

    txOffset_ += batchCount;
    txLastBatchTime_ = millis();

    if (txOffset_ >= txTotalItems_)
    {
        Serial.printf("%s session transmission complete!\n",
                      txSessionType_ == SessionType::INTERRUPT_BASED ? "Interrupt" : "Proximity");
        txState_ = TransmitState::SUCCEEDED;
    }

    return txState_;
}

void DataTransmitter::resetTransmission()
{
    txState_ = TransmitState::IDLE;
    txReadings_ = nullptr;
    txSensorMetadata_ = nullptr;
    txEvents_ = nullptr;
    txTotalItems_ = 0;
    txOffset_ = 0;
    txConfig_ = nullptr;
    txLastBatchTime_ = 0;
    txBatchDelay_ = 0;
    txContext_ = UploadContext{};
}

// ============================================================================
// Proximity Batch Transmission (single batch)
// ============================================================================

bool DataTransmitter::transmitBatch(const String &sessionId,
                                    const String &deviceId,
                                    unsigned long startTime,
                                    unsigned long duration,
                                    std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings,
                                    size_t offset,
                                    size_t count,
                                    const std::vector<SensorMetadata> *sensorMetadata,
                                    const SensorConfiguration *config)
{
    // Create JSON document
    DynamicJsonDocument doc(8192); // 8KB for batch

    doc["session_id"] = sessionId;
    doc["device_id"] = deviceId;
    doc["session_type"] = "proximity";           // Explicit session type
    doc["start_timestamp"] = startTime * 1000UL; // Convert session start from ms to us (consistent with reading timestamps)
    doc["duration_ms"] = duration;
    doc["sample_rate"] = (config != nullptr && config->actual_sample_rate_hz > 0)
                             ? config->actual_sample_rate_hz
                             : SAMPLE_RATE_HZ;
    doc["batch_offset"] = offset;
    doc["batch_size"] = count;
    doc["timestamp_unit"] = "us"; // Signal to Lambda that timestamps are in microseconds

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

        serialization::serializeConfig(doc, config);
        serialization::serializeCalibration(doc);
    }

    // Add readings array
    JsonArray readingsArray = doc.createNestedArray("readings");
    serialization::serializeReadingsArray(readingsArray, readings, offset, count);

    if (doc.overflowed())
    {
        Serial.printf("WARNING: ArduinoJson overflow in transmitBatch! (doc: %d/8192 bytes, readings: %d)\n",
                      doc.memoryUsage(), count);
    }

    // Serialize to string
    String payload;
    size_t payloadSize = serializeJson(doc, payload);

    // Publish via MQTT (silent on success, only log errors)
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
    else if (activeSummary)
    {
        // Session Confirmation: count transmitted readings and batches
        activeSummary->total_readings_transmitted += count;
        activeSummary->total_batches_transmitted++;
    }

    return success;
}

// ============================================================================
// Interrupt Batch Transmission (single batch)
// ============================================================================

bool DataTransmitter::transmitInterruptBatch(const String &sessionId,
                                             const String &deviceId,
                                             unsigned long startTime,
                                             unsigned long duration,
                                             const std::vector<InterruptEvent> &events,
                                             size_t offset,
                                             size_t count,
                                             bool isFirstBatch,
                                             const SensorConfiguration *config)
{
    // Create JSON document
    DynamicJsonDocument doc(8192);

    doc["session_id"] = sessionId;
    doc["device_id"] = deviceId;
    doc["session_type"] = "interrupt"; // Explicit session type
    doc["start_timestamp"] = startTime;
    doc["duration_ms"] = duration;
    doc["batch_offset"] = offset;
    doc["batch_size"] = count;

    // Add interrupt configuration (only in first batch)
    // Uses calibration-based approach - thresholds are relative to auto-calibrated baseline
    if (isFirstBatch && config != nullptr)
    {
        JsonObject intConfig = doc.createNestedObject("interrupt_config");
        intConfig["threshold_margin"] = config->interrupt_threshold_margin;
        intConfig["hysteresis"] = config->interrupt_hysteresis;
        intConfig["integration_time"] = config->interrupt_integration_time;
        intConfig["multi_pulse"] = config->interrupt_multi_pulse;
        intConfig["persistence"] = config->interrupt_persistence;
        intConfig["smart_persistence"] = config->interrupt_smart_persistence;
        intConfig["mode"] = config->interrupt_mode;
        intConfig["led_current"] = config->led_current;

        serialization::serializeCalibration(doc);
    }

    // Add events array
    JsonArray eventsArray = doc.createNestedArray("events");

    for (size_t i = 0; i < count; i++)
    {
        const InterruptEvent &evt = events[offset + i];

        JsonObject evtObj = eventsArray.createNestedObject();
        evtObj["ts"] = evt.timestamp_us;
        evtObj["board"] = evt.boardId;
        evtObj["sensor"] = evt.sensorId;

        // Convert event type to string
        switch (evt.type)
        {
        case InterruptEventType::CLOSE:
            evtObj["type"] = "close";
            break;
        case InterruptEventType::AWAY:
            evtObj["type"] = "away";
            break;
        default:
            evtObj["type"] = "unknown";
            break;
        }

        evtObj["flags"] = evt.rawFlags;
    }

    if (doc.overflowed())
    {
        Serial.printf("WARNING: ArduinoJson overflow in transmitInterruptBatch! (doc: %d/8192 bytes, events: %d)\n",
                      doc.memoryUsage(), count);
    }

    // Serialize to string for debugging
    String payload;
    size_t payloadSize = serializeJson(doc, payload);

    // Publish via MQTT
    bool success = mqttManager->publishData(doc);

    if (!success)
    {
        Serial.println("ERROR: MQTT publish failed for interrupt batch!");
        Serial.print("  Payload size: ");
        Serial.print(payloadSize);
        Serial.println(" bytes");
    }
    else
    {
        Serial.printf("  Sent interrupt batch: offset=%d, count=%d\n", offset, count);
    }

    return success;
}

// ============================================================================
// Live Debug Capture Transmission (legacy synchronous path)
// ============================================================================

String DataTransmitter::transmitLiveDebugCapture(
    std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings,
    size_t startIdx,
    size_t count,
    const char *captureReason,
    const char *detectionDirection,
    float detectionConfidence,
    const SensorConfiguration *config)
{
    if (count == 0)
    {
        Serial.println("Live Debug: No readings to transmit");
        return "";
    }

    // Generate a unique session ID for this capture
    String deviceId = mqttManager->getDeviceId();
    // Extract short device suffix for session ID (e.g. "motionplay-device-002" -> "device-002")
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

    Serial.printf("Live Debug capture: reason=%s, readings=%d, duration=%lums\n",
                  captureReason, count, durationMs);

    // Send in batches using Live Debug batch settings
    size_t offset = 0;
    while (offset < count)
    {
        size_t remaining = count - offset;
        size_t batchCount = (remaining > LIVE_DEBUG_BATCH_SIZE) ? LIVE_DEBUG_BATCH_SIZE : remaining;

        // Create JSON document — 32KB to comfortably fit 200 readings
        // At ~80 bytes per reading in ArduinoJson memory, 200 readings needs ~16KB+
        // Previous 16KB buffer silently truncated readings via ArduinoJson overflow
        DynamicJsonDocument doc(32768);

        doc["session_id"] = sessionId;
        doc["device_id"] = deviceId;
        doc["session_type"] = "proximity";
        doc["mode"] = "live_debug";
        doc["start_timestamp"] = startTime; // Microseconds (first reading timestamp)
        doc["duration_ms"] = durationMs;
        doc["timestamp_unit"] = "us"; // Signal to Lambda that timestamps are in microseconds
        doc["sample_rate"] = (config != nullptr && config->actual_sample_rate_hz > 0)
                                 ? config->actual_sample_rate_hz
                                 : SAMPLE_RATE_HZ;
        doc["batch_offset"] = offset;
        doc["batch_size"] = batchCount;

        // First batch: include capture metadata and config
        if (offset == 0)
        {
            // Live Debug capture metadata
            doc["capture_reason"] = captureReason;
            if (detectionDirection != nullptr)
            {
                doc["detection_direction"] = detectionDirection;
                doc["detection_confidence"] = detectionConfidence;
            }

            serialization::serializeConfig(doc, config);
            serialization::serializeCalibration(doc);
        }

        // Add readings array
        JsonArray readingsArray = doc.createNestedArray("readings");
        serialization::serializeReadingsArray(readingsArray, readings, startIdx + offset, batchCount);

        // Check for ArduinoJson buffer overflow (silent data truncation)
        size_t actualReadingsInDoc = readingsArray.size();
        if (doc.overflowed())
        {
            Serial.printf("WARNING: ArduinoJson overflow! Wanted %d readings, only %d fit (doc: %d/%d bytes)\n",
                          batchCount, actualReadingsInDoc, doc.memoryUsage(), 32768);
        }

        // Publish via MQTT
        bool success = mqttManager->publishData(doc);
        if (!success)
        {
            String payload;
            size_t payloadSize = serializeJson(doc, payload);
            Serial.printf("ERROR: Live Debug MQTT publish failed! Size: %d bytes\n", payloadSize);
            return "";
        }

        // Session Confirmation: count only readings that actually made it into the JSON
        if (activeSummary)
        {
            activeSummary->total_readings_transmitted += actualReadingsInDoc;
            activeSummary->total_batches_transmitted++;
        }

        offset += batchCount;

        // Short delay between batches
        if (offset < count)
        {
            delay(LIVE_DEBUG_BATCH_DELAY);
        }
    }

    uint32_t actualTransmitted = activeSummary ? activeSummary->total_readings_transmitted : count;
    Serial.printf("Live Debug capture transmitted: session=%s, %d/%d readings in %d batches\n",
                  sessionId.c_str(), actualTransmitted, count,
                  activeSummary ? activeSummary->total_batches_transmitted : 0);
    return sessionId;
}

// ============================================================================
// Session Confirmation: Transmit pipeline integrity summary
// ============================================================================

bool DataTransmitter::transmitSessionSummary(const SessionSummary &summary,
                                             const String &sessionId,
                                             const String &deviceId)
{
    DynamicJsonDocument doc(4096);

    doc["type"] = "session_summary";
    doc["session_id"] = sessionId;
    doc["device_id"] = deviceId;

    JsonObject summaryObj = doc.createNestedObject("summary");
    serialization::serializeSummary(summaryObj, summary);

    // Retry up to 3 times
    for (int attempt = 0; attempt < 3; attempt++)
    {
        if (mqttManager->publishData(doc))
        {
            Serial.printf("Session summary transmitted (attempt %d)\n", attempt + 1);
            return true;
        }
        Serial.printf("WARNING: Session summary publish failed (attempt %d/3)\n", attempt + 1);
        delay(500);
    }

    Serial.println("ERROR: Failed to transmit session summary after 3 attempts");
    return false;
}
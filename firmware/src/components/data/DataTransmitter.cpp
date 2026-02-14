#include "DataTransmitter.h"
#include "../memory/PSRAMAllocator.h"
#include "../calibration/CalibrationData.h"

DataTransmitter::DataTransmitter(MQTTManager *mqtt) : mqttManager(mqtt)
{
    // Constructor
}

// ============================================================================
// Main entry point - routes to correct transmission method
// ============================================================================

bool DataTransmitter::transmitSession(SessionManager &session, const SensorConfiguration *config)
{
    if (session.getSessionType() == SessionType::INTERRUPT_BASED)
    {
        return transmitInterruptSession(session, config);
    }
    else
    {
        return transmitProximitySession(session, config);
    }
}

// ============================================================================
// Proximity Mode Transmission (existing implementation)
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
    doc["session_type"] = "proximity"; // Explicit session type
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

        // Add calibration metadata if available
        if (deviceCalibration.isValid())
        {
            JsonObject calObj = doc.createNestedObject("calibration");
            calObj["valid"] = true;
            calObj["timestamp"] = deviceCalibration.timestamp;
            calObj["multi_pulse"] = deviceCalibration.multi_pulse;
            calObj["integration_time"] = deviceCalibration.integration_time;

            JsonArray thresholds = calObj.createNestedArray("thresholds");
            for (int i = 0; i < CALIBRATION_NUM_PCBS; i++)
            {
                JsonObject pcbCal = thresholds.createNestedObject();
                pcbCal["pcb"] = i + 1;
                pcbCal["baseline_max"] = deviceCalibration.pcbs[i].baseline_max;
                pcbCal["signal_min"] = deviceCalibration.pcbs[i].signal_min;
                pcbCal["signal_max"] = deviceCalibration.pcbs[i].signal_max;
                pcbCal["threshold"] = deviceCalibration.pcbs[i].threshold;
            }
        }
        else
        {
            JsonObject calObj = doc.createNestedObject("calibration");
            calObj["valid"] = false;
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

bool DataTransmitter::transmitProximitySession(SessionManager &session, const SensorConfiguration *config)
{
    if (!session.hasData())
    {
        Serial.println("No data to transmit");
        return false;
    }

    String sessionId = session.getSessionId();
    String deviceId = mqttManager->getDeviceId();
    unsigned long startTime = session.getStartTime();
    unsigned long duration = session.getDuration();

    std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings = session.getDataBuffer();
    const std::vector<SensorMetadata> &sensorMetadata = session.getSensorMetadata();
    size_t totalReadings = readings.size();

    Serial.print("Transmitting proximity session ");
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

    Serial.println("Proximity session transmission complete!");
    return true;
}

// ============================================================================
// Interrupt Mode Transmission (new implementation)
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

        // Add calibration metadata if available
        if (deviceCalibration.isValid())
        {
            JsonObject calObj = doc.createNestedObject("calibration");
            calObj["valid"] = true;
            calObj["timestamp"] = deviceCalibration.timestamp;
            calObj["multi_pulse"] = deviceCalibration.multi_pulse;
            calObj["integration_time"] = deviceCalibration.integration_time;

            JsonArray thresholds = calObj.createNestedArray("thresholds");
            for (int i = 0; i < CALIBRATION_NUM_PCBS; i++)
            {
                JsonObject pcbCal = thresholds.createNestedObject();
                pcbCal["pcb"] = i + 1;
                pcbCal["baseline_max"] = deviceCalibration.pcbs[i].baseline_max;
                pcbCal["signal_min"] = deviceCalibration.pcbs[i].signal_min;
                pcbCal["signal_max"] = deviceCalibration.pcbs[i].signal_max;
                pcbCal["threshold"] = deviceCalibration.pcbs[i].threshold;
            }
        }
        else
        {
            JsonObject calObj = doc.createNestedObject("calibration");
            calObj["valid"] = false;
        }
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

bool DataTransmitter::transmitInterruptSession(SessionManager &session, const SensorConfiguration *config)
{
    if (!session.hasData())
    {
        Serial.println("No interrupt events to transmit");
        return false;
    }

    String sessionId = session.getSessionId();
    String deviceId = mqttManager->getDeviceId();
    unsigned long startTime = session.getStartTime();
    unsigned long duration = session.getDuration();

    const std::vector<InterruptEvent> &events = session.getInterruptBuffer();
    size_t totalEvents = events.size();

    Serial.print("Transmitting interrupt session ");
    Serial.print(sessionId);
    Serial.print(" (");
    Serial.print(totalEvents);
    Serial.println(" events)");

    // Send in batches (interrupt events are smaller, can send more per batch)
    size_t offset = 0;
    while (offset < totalEvents)
    {
        size_t remaining = totalEvents - offset;
        size_t batchCount = (remaining > INT_BATCH_SIZE) ? INT_BATCH_SIZE : remaining;

        bool isFirstBatch = (offset == 0);

        if (!transmitInterruptBatch(sessionId, deviceId, startTime, duration,
                                    events, offset, batchCount, isFirstBatch, config))
        {
            Serial.println("ERROR: Failed to transmit interrupt batch");
            return false;
        }

        offset += batchCount;

        // Small delay between batches
        delay(50);
    }

    Serial.println("Interrupt session transmission complete!");
    return true;
}

// ============================================================================
// Live Debug Capture Transmission
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

    // Calculate timing from the readings themselves
    unsigned long startTime = readings[startIdx].timestamp_ms;
    unsigned long endTime = readings[startIdx + count - 1].timestamp_ms;
    unsigned long duration = endTime - startTime;

    Serial.printf("Live Debug capture: reason=%s, readings=%d, duration=%lums\n",
                  captureReason, count, duration);

    // Send in batches using Live Debug batch settings
    size_t offset = 0;
    while (offset < count)
    {
        size_t remaining = count - offset;
        size_t batchCount = (remaining > LIVE_DEBUG_BATCH_SIZE) ? LIVE_DEBUG_BATCH_SIZE : remaining;

        // Create JSON document
        DynamicJsonDocument doc(16384); // 16KB for larger batches

        doc["session_id"] = sessionId;
        doc["device_id"] = deviceId;
        doc["session_type"] = "proximity";
        doc["mode"] = "live_debug";
        doc["start_timestamp"] = startTime;
        doc["duration_ms"] = duration;
        doc["sample_rate"] = SAMPLE_RATE_HZ;
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

            // Sensor configuration
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

            // Calibration metadata
            if (deviceCalibration.isValid())
            {
                JsonObject calObj = doc.createNestedObject("calibration");
                calObj["valid"] = true;
                calObj["timestamp"] = deviceCalibration.timestamp;
                calObj["multi_pulse"] = deviceCalibration.multi_pulse;
                calObj["integration_time"] = deviceCalibration.integration_time;

                JsonArray thresholds = calObj.createNestedArray("thresholds");
                for (int i = 0; i < CALIBRATION_NUM_PCBS; i++)
                {
                    JsonObject pcbCal = thresholds.createNestedObject();
                    pcbCal["pcb"] = i + 1;
                    pcbCal["baseline_max"] = deviceCalibration.pcbs[i].baseline_max;
                    pcbCal["signal_min"] = deviceCalibration.pcbs[i].signal_min;
                    pcbCal["signal_max"] = deviceCalibration.pcbs[i].signal_max;
                    pcbCal["threshold"] = deviceCalibration.pcbs[i].threshold;
                }
            }
        }

        // Add readings array
        JsonArray readingsArray = doc.createNestedArray("readings");
        for (size_t i = 0; i < batchCount; i++)
        {
            SensorReading &reading = readings[startIdx + offset + i];

            JsonObject readingObj = readingsArray.createNestedObject();
            readingObj["ts"] = reading.timestamp_ms;
            readingObj["pos"] = reading.position;
            readingObj["pcb"] = reading.pcb_id;
            readingObj["side"] = reading.side;
            readingObj["prox"] = reading.proximity;
            readingObj["amb"] = reading.ambient;
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

        // Session Confirmation: count transmitted readings and batches
        if (activeSummary)
        {
            activeSummary->total_readings_transmitted += batchCount;
            activeSummary->total_batches_transmitted++;
        }

        offset += batchCount;

        // Short delay between batches
        if (offset < count)
        {
            delay(LIVE_DEBUG_BATCH_DELAY);
        }
    }

    Serial.printf("Live Debug capture transmitted: session=%s, %d readings\n",
                  sessionId.c_str(), count);
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
    summaryObj["total_cycles"] = summary.total_cycles;
    summaryObj["queue_drops"] = summary.queue_drops;
    summaryObj["buffer_drops"] = summary.buffer_drops;
    summaryObj["total_readings_transmitted"] = summary.total_readings_transmitted;
    summaryObj["total_batches_transmitted"] = summary.total_batches_transmitted;
    summaryObj["measured_cycle_rate_hz"] = summary.measured_cycle_rate_hz;
    summaryObj["duration_ms"] = summary.duration_ms;
    summaryObj["theoretical_max_readings"] = summary.theoretical_max_readings;
    summaryObj["num_active_sensors"] = summary.num_active_sensors;

    // Per-sensor arrays
    JsonArray collectedArr = summaryObj.createNestedArray("readings_collected");
    JsonArray errorsArr = summaryObj.createNestedArray("i2c_errors");
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        collectedArr.add(summary.readings_collected[i]);
        errorsArr.add(summary.i2c_errors[i]);
    }

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
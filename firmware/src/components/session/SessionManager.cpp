#include "SessionManager.h"

SessionManager::SessionManager()
{
    // Create queue for sensor data (6 sensors * 1000Hz = 6000 items/sec)
    dataQueue = xQueueCreate(1000, sizeof(SensorReading));

    if (dataQueue == NULL)
    {
        Serial.println("ERROR: Failed to create data queue");
    }
}

void SessionManager::setDeviceId(const String &fullDeviceId)
{
    // Extract short suffix for session IDs (e.g. "motionplay-device-002" -> "device-002")
    int lastDash = fullDeviceId.lastIndexOf('-');
    int secondLastDash = fullDeviceId.lastIndexOf('-', lastDash - 1);
    if (secondLastDash >= 0)
    {
        deviceIdPrefix = fullDeviceId.substring(secondLastDash + 1);
    }
    else
    {
        deviceIdPrefix = fullDeviceId;
    }
    Serial.printf("Session ID prefix set to: %s\n", deviceIdPrefix.c_str());
}

void SessionManager::generateSessionId()
{
    // Generate unique session ID: device-NNN_timestamp
    String prefix = deviceIdPrefix.isEmpty() ? "device-001" : deviceIdPrefix;
    sessionId = prefix + "_" + String(millis());
}

bool SessionManager::startSession()
{
    if (state != IDLE)
    {
        Serial.println("ERROR: Session already active");
        return false;
    }

    Serial.println("Starting new session...");
    Serial.printf("  Session type: %s\n",
                  sessionType == SessionType::INTERRUPT_BASED ? "INTERRUPT" : "PROXIMITY");

    // Reset session confirmation counters
    sessionSummary.reset();

    // Clear any old data based on session type
    if (sessionType == SessionType::INTERRUPT_BASED)
    {
        interruptBuffer.clear();
        interruptBuffer.reserve(MAX_INTERRUPT_BUFFER);
    }
    else
    {
        dataBuffer.clear();
        dataBuffer.reserve(MAX_BUFFER_SIZE);
    }

    // Generate new session ID
    generateSessionId();
    sessionStartTime = millis();

    state = COLLECTING;

    Serial.print("Session started: ");
    Serial.println(sessionId);

    return true;
}

bool SessionManager::stopSession()
{
    if (state != COLLECTING)
    {
        Serial.println("ERROR: No active session");
        return false;
    }

    Serial.println("Stopping session...");

    sessionDuration = millis() - sessionStartTime;
    state = UPLOADING;

    // Process any remaining items in queue (only for proximity mode)
    if (sessionType == SessionType::PROXIMITY)
    {
        processQueue();
    }

    Serial.print("Session stopped. Duration: ");
    Serial.print(sessionDuration);
    Serial.print("ms, ");

    if (sessionType == SessionType::INTERRUPT_BASED)
    {
        Serial.print("Events: ");
        Serial.println(interruptBuffer.size());
    }
    else
    {
        Serial.print("Samples: ");
        Serial.println(dataBuffer.size());
    }

    return true;
}

void SessionManager::processQueue()
{
    if (state != COLLECTING)
        return;

    // Only process queue for proximity mode
    if (sessionType != SessionType::PROXIMITY)
        return;

    SensorReading reading;
    int processed = 0;

    // Process all available readings
    while (xQueueReceive(dataQueue, &reading, 0) == pdTRUE)
    {
        if (dataBuffer.size() < MAX_BUFFER_SIZE)
        {
            dataBuffer.push_back(reading);
            processed++;
        }
        else
        {
            // Count remaining items in queue that will be dropped
            uint32_t dropped = 1; // This one
            SensorReading discardReading;
            while (xQueueReceive(dataQueue, &discardReading, 0) == pdTRUE)
            {
                dropped++;
            }
            sessionSummary.buffer_drops += dropped;
            Serial.printf("WARNING: Buffer full, dropped %lu samples\n", (unsigned long)dropped);
            break;
        }
    }

    if (processed > 0)
    {
        // Periodic status update (every 1000 samples)
        if (dataBuffer.size() % 1000 == 0)
        {
            Serial.print("Buffered: ");
            Serial.print(dataBuffer.size());
            Serial.println(" samples");
        }
    }
}

bool SessionManager::hasData()
{
    if (sessionType == SessionType::INTERRUPT_BASED)
    {
        return !interruptBuffer.empty();
    }
    return !dataBuffer.empty();
}

size_t SessionManager::getDataCount()
{
    if (sessionType == SessionType::INTERRUPT_BASED)
    {
        return interruptBuffer.size();
    }
    return dataBuffer.size();
}

SessionState SessionManager::getState()
{
    return state;
}

String SessionManager::getSessionId()
{
    return sessionId;
}

unsigned long SessionManager::getDuration()
{
    if (state == COLLECTING)
    {
        return millis() - sessionStartTime;
    }
    return sessionDuration;
}

unsigned long SessionManager::getStartTime()
{
    return sessionStartTime;
}

std::vector<SensorReading, PSRAMAllocator<SensorReading>> &SessionManager::getDataBuffer()
{
    return dataBuffer;
}

void SessionManager::clearBuffer()
{
    dataBuffer.clear();
    interruptBuffer.clear();
    state = IDLE;
    sessionType = SessionType::PROXIMITY; // Reset to default
    Serial.println("Buffer cleared, session reset to IDLE");
}

void SessionManager::setSensorMetadata(const std::vector<SensorMetadata> &metadata)
{
    activeSensors = metadata;
}

const std::vector<SensorMetadata> &SessionManager::getSensorMetadata()
{
    return activeSensors;
}

QueueHandle_t SessionManager::getQueue()
{
    return dataQueue;
}

bool SessionManager::addInterruptEvent(const InterruptEvent &event)
{
    if (state != COLLECTING || sessionType != SessionType::INTERRUPT_BASED)
    {
        return false;
    }

    if (interruptBuffer.size() >= MAX_INTERRUPT_BUFFER)
    {
        Serial.println("WARNING: Interrupt buffer full, dropping event");
        return false;
    }

    interruptBuffer.push_back(event);
    return true;
}

void SessionManager::finalizeSessionSummary(const SensorConfiguration *config, uint8_t numActiveSensors)
{
    // Use caller-provided duration_ms if already set (Live Debug sets capture window duration),
    // otherwise fall back to the full session duration
    if (sessionSummary.duration_ms == 0)
    {
        sessionSummary.duration_ms = sessionDuration;
    }
    sessionSummary.num_active_sensors = numActiveSensors;

    // Compute measured cycle rate
    if (sessionSummary.duration_ms > 0)
    {
        sessionSummary.measured_cycle_rate_hz =
            (uint16_t)((uint32_t)sessionSummary.total_cycles * 1000 / sessionSummary.duration_ms);
    }

    // Compute theoretical max from config
    if (config != nullptr && sessionSummary.duration_ms > 0)
    {
        // theoretical = sample_rate * (duration_seconds) * active_sensors
        sessionSummary.theoretical_max_readings =
            (uint32_t)((float)config->sample_rate_hz * (sessionSummary.duration_ms / 1000.0f) * numActiveSensors);

        // Also populate actual_sample_rate_hz on the config (mutable cast — config is owned by main.cpp)
        const_cast<SensorConfiguration *>(config)->actual_sample_rate_hz = sessionSummary.measured_cycle_rate_hz;
    }

    // Log summary
    uint32_t totalCollected = 0;
    uint32_t totalErrors = 0;
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        totalCollected += sessionSummary.readings_collected[i];
        totalErrors += sessionSummary.i2c_errors[i];
    }

    Serial.println("\n=== Session Summary ===");
    Serial.printf("  Duration: %lu ms\n", (unsigned long)sessionSummary.duration_ms);
    Serial.printf("  Cycles: %lu, Rate: %u Hz\n",
                  (unsigned long)sessionSummary.total_cycles, sessionSummary.measured_cycle_rate_hz);
    Serial.printf("  Readings collected: %lu\n", (unsigned long)totalCollected);
    Serial.printf("  I2C errors: %lu\n", (unsigned long)totalErrors);
    Serial.printf("  Queue drops: %lu\n", (unsigned long)sessionSummary.queue_drops);
    Serial.printf("  Buffer drops: %lu\n", (unsigned long)sessionSummary.buffer_drops);
    Serial.printf("  Theoretical max: %lu\n", (unsigned long)sessionSummary.theoretical_max_readings);
    Serial.printf("  Active sensors: %u\n", sessionSummary.num_active_sensors);
    Serial.println("=======================\n");
}
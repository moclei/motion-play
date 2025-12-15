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

void SessionManager::generateSessionId()
{
    // Generate unique session ID: device-001_timestamp
    sessionId = "device-001_" + String(millis());
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
            Serial.println("WARNING: Buffer full, dropping samples");
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
    sessionType = SessionType::PROXIMITY;  // Reset to default
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

bool SessionManager::addInterruptEvent(const InterruptEvent& event)
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
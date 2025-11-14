# Phase 2: Data Pipeline Implementation Guide

This guide walks you through implementing sensor data collection, buffering, and transmission to AWS IoT Core.

## Phase 2 Overview

**Goal:** Collect high-frequency sensor data from VCNL4040 sensors and transmit it to AWS for storage in DynamoDB.

**Deliverables:**

1. Sensor data collection running on Core 0 at 1000 Hz
2. Session management (start/stop commands)
3. Data buffering in PSRAM
4. JSON serialization and MQTT transmission
5. End-to-end data flow to DynamoDB

## Prerequisites

- ✅ Phase 1 complete (WiFi + MQTT working)
- ✅ Existing VCNL4040 sensor code in `src/archive/`
- ✅ T-Display S3 with 6 sensors connected
- ✅ AWS Lambda functions deployed

---

## Architecture Overview

### Dual-Core Design

**Core 0 (Protocol CPU):**
- High-frequency sensor reading loop (1000 Hz)
- Minimal processing
- Write to FreeRTOS queue

**Core 1 (Application CPU):**
- MQTT/WiFi handling
- Command processing
- Data buffering and transmission
- Display updates

### Data Flow

```
Sensors → Core 0 → Queue → Core 1 → Buffer → MQTT → IoT Core → Lambda → DynamoDB
```

---

## Step 1: Create Sensor Manager Component

### 1.1 Create SensorManager.h

Create `firmware/src/components/sensor/SensorManager.h`:

```cpp
#ifndef SENSOR_MANAGER_H
#define SENSOR_MANAGER_H

#include <Arduino.h>
#include "../tca9548a/TCA9548A.h"
#include "../vcnl4040/VCNL4040.h"

// Sensor configuration
#define NUM_SENSORS 6
#define SAMPLE_RATE_HZ 1000
#define SAMPLE_INTERVAL_US (1000000 / SAMPLE_RATE_HZ)

// Sensor reading structure
struct SensorReading {
    uint32_t timestamp_ms;
    uint8_t position;       // 0=thumb, 1=index, 2=middle, 3=ring, 4=pinky, 5=palm
    uint16_t proximity;
    uint16_t ambient;
};

class SensorManager {
private:
    TCA9548A mux;
    VCNL4040 sensors[NUM_SENSORS];
    
    // Sensor positions mapping
    const uint8_t sensorChannels[NUM_SENSORS] = {0, 1, 2, 3, 4, 5};
    const char* sensorNames[NUM_SENSORS] = {
        "Thumb", "Index", "Middle", "Ring", "Pinky", "Palm"
    };
    
    bool initialized = false;
    TaskHandle_t sensorTask = NULL;
    QueueHandle_t dataQueue = NULL;
    
    static void sensorTaskFunction(void* parameter);
    
public:
    SensorManager();
    bool init();
    bool startCollection(QueueHandle_t queue);
    void stopCollection();
    bool isCollecting();
    bool readSensor(uint8_t sensorIndex, SensorReading& reading);
};

#endif
```

### 1.2 Create SensorManager.cpp

Create `firmware/src/components/sensor/SensorManager.cpp`:

```cpp
#include "SensorManager.h"

SensorManager::SensorManager() : mux(0x70) {
    // Constructor
}

bool SensorManager::init() {
    Serial.println("Initializing Sensor Manager...");
    
    // Initialize I2C
    Wire.begin(43, 44); // SDA=43, SCL=44 for T-Display S3
    Wire.setClock(400000); // 400kHz I2C
    
    // Initialize TCA9548A multiplexer
    if (!mux.begin()) {
        Serial.println("ERROR: Failed to initialize TCA9548A");
        return false;
    }
    Serial.println("TCA9548A initialized");
    
    // Initialize all VCNL4040 sensors
    for (int i = 0; i < NUM_SENSORS; i++) {
        mux.selectChannel(sensorChannels[i]);
        
        if (!sensors[i].begin()) {
            Serial.print("ERROR: Failed to initialize sensor ");
            Serial.print(sensorNames[i]);
            Serial.print(" on channel ");
            Serial.println(sensorChannels[i]);
            return false;
        }
        
        // Configure sensor
        sensors[i].setProxIntegrationTime(VCNL4040_PROX_IT_1T);
        sensors[i].setProxResolution(VCNL4040_PROX_RES_16BIT);
        sensors[i].setAmbientIntegrationTime(VCNL4040_ALS_IT_80MS);
        
        Serial.print("Sensor ");
        Serial.print(sensorNames[i]);
        Serial.println(" initialized");
    }
    
    initialized = true;
    Serial.println("All sensors initialized successfully!");
    return true;
}

bool SensorManager::readSensor(uint8_t sensorIndex, SensorReading& reading) {
    if (sensorIndex >= NUM_SENSORS) return false;
    
    mux.selectChannel(sensorChannels[sensorIndex]);
    
    reading.timestamp_ms = millis();
    reading.position = sensorIndex;
    reading.proximity = sensors[sensorIndex].getProximity();
    reading.ambient = sensors[sensorIndex].getAmbient();
    
    return true;
}

void SensorManager::sensorTaskFunction(void* parameter) {
    SensorManager* manager = (SensorManager*)parameter;
    
    Serial.println("Sensor task started on Core 0");
    
    unsigned long lastSampleTime = micros();
    SensorReading reading;
    
    while (true) {
        unsigned long currentTime = micros();
        
        // Check if it's time for next sample
        if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_US) {
            lastSampleTime = currentTime;
            
            // Read all sensors
            for (int i = 0; i < NUM_SENSORS; i++) {
                if (manager->readSensor(i, reading)) {
                    // Send to queue (non-blocking)
                    if (xQueueSend(manager->dataQueue, &reading, 0) != pdTRUE) {
                        // Queue full - data lost
                        // Could increment a dropped sample counter here
                    }
                }
            }
        }
        
        // Small yield to prevent watchdog
        vTaskDelay(1);
    }
}

bool SensorManager::startCollection(QueueHandle_t queue) {
    if (!initialized) {
        Serial.println("ERROR: Sensors not initialized");
        return false;
    }
    
    if (sensorTask != NULL) {
        Serial.println("Collection already running");
        return false;
    }
    
    dataQueue = queue;
    
    // Create sensor task on Core 0
    xTaskCreatePinnedToCore(
        sensorTaskFunction,
        "SensorTask",
        4096,           // Stack size
        this,           // Parameter
        2,              // Priority
        &sensorTask,
        0               // Core 0
    );
    
    Serial.println("Sensor collection started");
    return true;
}

void SensorManager::stopCollection() {
    if (sensorTask != NULL) {
        vTaskDelete(sensorTask);
        sensorTask = NULL;
        Serial.println("Sensor collection stopped");
    }
}

bool SensorManager::isCollecting() {
    return sensorTask != NULL;
}
```

---

## Step 2: Create Session Manager Component

### 2.1 Create SessionManager.h

Create `firmware/src/components/session/SessionManager.h`:

```cpp
#ifndef SESSION_MANAGER_H
#define SESSION_MANAGER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include <vector>
#include "../sensor/SensorManager.h"

enum SessionState {
    IDLE,
    COLLECTING,
    UPLOADING
};

class SessionManager {
private:
    SessionState state = IDLE;
    QueueHandle_t dataQueue = NULL;
    
    String sessionId;
    unsigned long sessionStartTime = 0;
    unsigned long sessionDuration = 0;
    std::vector<SensorReading> dataBuffer;
    
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
    std::vector<SensorReading>& getDataBuffer();
    void clearBuffer();
};

#endif
```

### 2.2 Create SessionManager.cpp

Create `firmware/src/components/session/SessionManager.cpp`:

```cpp
#include "SessionManager.h"

SessionManager::SessionManager() {
    // Create queue for sensor data (6 sensors * 1000Hz = 6000 items/sec)
    dataQueue = xQueueCreate(1000, sizeof(SensorReading));
    
    if (dataQueue == NULL) {
        Serial.println("ERROR: Failed to create data queue");
    }
}

void SessionManager::generateSessionId() {
    // Generate unique session ID: device-001_timestamp
    sessionId = "device-001_" + String(millis());
}

bool SessionManager::startSession() {
    if (state != IDLE) {
        Serial.println("ERROR: Session already active");
        return false;
    }
    
    Serial.println("Starting new session...");
    
    // Clear any old data
    dataBuffer.clear();
    dataBuffer.reserve(MAX_BUFFER_SIZE);
    
    // Generate new session ID
    generateSessionId();
    sessionStartTime = millis();
    
    state = COLLECTING;
    
    Serial.print("Session started: ");
    Serial.println(sessionId);
    
    return true;
}

bool SessionManager::stopSession() {
    if (state != COLLECTING) {
        Serial.println("ERROR: No active session");
        return false;
    }
    
    Serial.println("Stopping session...");
    
    sessionDuration = millis() - sessionStartTime;
    state = UPLOADING;
    
    // Process any remaining items in queue
    processQueue();
    
    Serial.print("Session stopped. Duration: ");
    Serial.print(sessionDuration);
    Serial.print("ms, Samples: ");
    Serial.println(dataBuffer.size());
    
    return true;
}

void SessionManager::processQueue() {
    if (state != COLLECTING) return;
    
    SensorReading reading;
    int processed = 0;
    
    // Process all available readings
    while (xQueueReceive(dataQueue, &reading, 0) == pdTRUE) {
        if (dataBuffer.size() < MAX_BUFFER_SIZE) {
            dataBuffer.push_back(reading);
            processed++;
        } else {
            Serial.println("WARNING: Buffer full, dropping samples");
            break;
        }
    }
    
    if (processed > 0) {
        // Periodic status update (every 1000 samples)
        if (dataBuffer.size() % 1000 == 0) {
            Serial.print("Buffered: ");
            Serial.print(dataBuffer.size());
            Serial.println(" samples");
        }
    }
}

bool SessionManager::hasData() {
    return !dataBuffer.empty();
}

size_t SessionManager::getDataCount() {
    return dataBuffer.size();
}

SessionState SessionManager::getState() {
    return state;
}

String SessionManager::getSessionId() {
    return sessionId;
}

unsigned long SessionManager::getDuration() {
    if (state == COLLECTING) {
        return millis() - sessionStartTime;
    }
    return sessionDuration;
}

std::vector<SensorReading>& SessionManager::getDataBuffer() {
    return dataBuffer;
}

void SessionManager::clearBuffer() {
    dataBuffer.clear();
    state = IDLE;
    Serial.println("Buffer cleared, session reset to IDLE");
}

QueueHandle_t SessionManager::getQueue() {
    return dataQueue;
}
```

### 2.3 Add getQueue() to header

Add this to SessionManager.h public methods:

```cpp
QueueHandle_t getQueue();
```

---

## Step 3: Create Data Transmitter Component

### 3.1 Create DataTransmitter.h

Create `firmware/src/components/data/DataTransmitter.h`:

```cpp
#ifndef DATA_TRANSMITTER_H
#define DATA_TRANSMITTER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include "../mqtt/MQTTManager.h"
#include "../session/SessionManager.h"

class DataTransmitter {
private:
    MQTTManager* mqttManager;
    static const size_t BATCH_SIZE = 100; // Send 100 readings at a time
    
public:
    DataTransmitter(MQTTManager* mqtt);
    bool transmitSession(SessionManager& session);
    bool transmitBatch(const String& sessionId, 
                      const String& deviceId,
                      unsigned long startTime,
                      unsigned long duration,
                      std::vector<SensorReading>& readings,
                      size_t offset,
                      size_t count);
};

#endif
```

### 3.2 Create DataTransmitter.cpp

Create `firmware/src/components/data/DataTransmitter.cpp`:

```cpp
#include "DataTransmitter.h"

DataTransmitter::DataTransmitter(MQTTManager* mqtt) : mqttManager(mqtt) {
    // Constructor
}

bool DataTransmitter::transmitBatch(const String& sessionId,
                                   const String& deviceId,
                                   unsigned long startTime,
                                   unsigned long duration,
                                   std::vector<SensorReading>& readings,
                                   size_t offset,
                                   size_t count) {
    // Create JSON document
    DynamicJsonDocument doc(8192); // 8KB for batch
    
    doc["session_id"] = sessionId;
    doc["device_id"] = deviceId;
    doc["start_timestamp"] = startTime;
    doc["duration_ms"] = duration;
    doc["sample_rate"] = SAMPLE_RATE_HZ;
    doc["batch_offset"] = offset;
    doc["batch_size"] = count;
    
    // Add readings array
    JsonArray readingsArray = doc.createNestedArray("readings");
    
    for (size_t i = 0; i < count; i++) {
        SensorReading& reading = readings[offset + i];
        
        JsonObject readingObj = readingsArray.createNestedObject();
        readingObj["ts"] = reading.timestamp_ms;
        readingObj["pos"] = reading.position;
        readingObj["prox"] = reading.proximity;
        readingObj["amb"] = reading.ambient;
    }
    
    // Serialize to string
    String payload;
    serializeJson(doc, payload);
    
    // Publish via MQTT
    Serial.print("Transmitting batch ");
    Serial.print(offset / BATCH_SIZE);
    Serial.print(" (");
    Serial.print(count);
    Serial.println(" samples)");
    
    return mqttManager->publishData(doc);
}

bool DataTransmitter::transmitSession(SessionManager& session) {
    if (!session.hasData()) {
        Serial.println("No data to transmit");
        return false;
    }
    
    String sessionId = session.getSessionId();
    String deviceId = "motionplay-device-001"; // TODO: Get from config
    unsigned long startTime = millis() - session.getDuration();
    unsigned long duration = session.getDuration();
    
    std::vector<SensorReading>& readings = session.getDataBuffer();
    size_t totalReadings = readings.size();
    
    Serial.print("Transmitting session ");
    Serial.print(sessionId);
    Serial.print(" (");
    Serial.print(totalReadings);
    Serial.println(" readings)");
    
    // Send in batches
    size_t offset = 0;
    while (offset < totalReadings) {
        size_t remaining = totalReadings - offset;
        size_t batchCount = (remaining > BATCH_SIZE) ? BATCH_SIZE : remaining;
        
        if (!transmitBatch(sessionId, deviceId, startTime, duration, 
                          readings, offset, batchCount)) {
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
```

---

## Step 4: Integrate into Main

### 4.1 Update main.cpp

Update your `firmware/src/main.cpp` to include the new components:

```cpp
#include <Arduino.h>
#include "components/network/NetworkManager.h"
#include "components/mqtt/MQTTManager.h"
#include "components/display/DisplayManager.h"
#include "components/sensor/SensorManager.h"
#include "components/session/SessionManager.h"
#include "components/data/DataTransmitter.h"

// Button pins for T-Display-S3
#define BUTTON_1 0   // Left button (BOOT)
#define BUTTON_2 14  // Right button

// Managers
NetworkManager networkManager;
MQTTManager* mqttManager;
DisplayManager display;
SensorManager sensorManager;
SessionManager sessionManager;
DataTransmitter* dataTransmitter;

// Timing
unsigned long lastStatusUpdate = 0;
const unsigned long STATUS_UPDATE_INTERVAL = 30000; // 30 seconds

bool systemInitialized = false;

// Forward declarations
void handleCommand(const String& command);

void setup() {
    Serial.begin(115200);
    delay(2000);

    Serial.println("\n\n\n=================================");
    Serial.println("Motion Play Device - BOOT");
    Serial.println("=================================");
    Serial.println("Serial is working!");
    Serial.println("Waiting for button press to initialize...");
    Serial.println("Press LEFT button (BOOT/GPIO 0) to start");
    Serial.println("Press RIGHT button (GPIO 14) to restart");
    Serial.println("=================================\n");

    // Initialize buttons
    pinMode(BUTTON_1, INPUT_PULLUP);
    pinMode(BUTTON_2, INPUT_PULLUP);
    Serial.println("Buttons initialized");

    // Initialize display
    display.init();
    display.showBootScreen();
    display.updateStatus("Waiting for button...", TFT_CYAN);
    Serial.println("Display initialized");

    Serial.println("\n=== Setup Complete - Entering Loop ===\n");
}

void initializeSystem() {
    Serial.println("\n=== Button pressed! Starting initialization ===\n");
    display.updateStatus("Initializing...", TFT_YELLOW);

    // Initialize sensors first
    Serial.println("Initializing sensors...");
    display.updateStatus("Init sensors...");
    if (!sensorManager.init()) {
        Serial.println("ERROR: Sensor initialization failed!");
        display.updateStatus("Sensor init failed!", TFT_RED);
        while (1) delay(1000);
    }
    Serial.println("Sensors initialized successfully");
    display.updateStatus("Sensors OK", TFT_GREEN);

    // Load network configuration
    Serial.println("Loading config...");
    display.updateStatus("Loading config...");
    if (!networkManager.loadConfig()) {
        Serial.println("ERROR: Config failed!");
        display.updateStatus("Config failed!", TFT_RED);
        while (1) delay(1000);
    }
    Serial.println("Config loaded successfully");
    display.updateStatus("Config loaded", TFT_GREEN);

    // Connect to WiFi
    Serial.println("Connecting to WiFi...");
    display.updateStatus("Connecting WiFi...");
    if (!networkManager.connectWiFi()) {
        Serial.println("ERROR: WiFi failed!");
        display.updateStatus("WiFi failed!", TFT_RED);
        while (1) delay(1000);
    }
    Serial.println("WiFi connected!");
    display.updateStatus("WiFi connected", TFT_GREEN);

    // Initialize MQTT
    mqttManager = new MQTTManager(&networkManager);

    Serial.println("Loading MQTT config...");
    display.updateStatus("Loading MQTT config...");
    if (!mqttManager->loadConfig()) {
        Serial.println("ERROR: MQTT config failed!");
        display.updateStatus("MQTT config failed!", TFT_RED);
        while (1) delay(1000);
    }
    Serial.println("MQTT config loaded");

    // Connect to MQTT
    Serial.println("Connecting to MQTT...");
    display.updateStatus("Connecting MQTT...");
    if (!mqttManager->connect()) {
        Serial.println("WARNING: MQTT connection failed");
        display.updateStatus("MQTT failed!", TFT_RED);
    } else {
        Serial.println("MQTT connected!");
        display.updateStatus("MQTT connected", TFT_GREEN);
    }

    // Initialize data transmitter
    dataTransmitter = new DataTransmitter(mqttManager);

    // Set up command handler
    mqttManager->setCallback([](char* topic, byte* payload, unsigned int length) {
        char message[length + 1];
        memcpy(message, payload, length);
        message[length] = '\0';

        DynamicJsonDocument doc(256);
        DeserializationError error = deserializeJson(doc, message);

        if (!error) {
            String command = doc["command"].as<String>();
            handleCommand(command);
        }
    });

    Serial.println("\n=== System Initialization Complete ===\n");
    systemInitialized = true;
}

void handleCommand(const String& command) {
    Serial.print("Received command: ");
    Serial.println(command);

    if (command == "ping") {
        mqttManager->publishStatus("pong");
        display.updateStatus("Ping received", TFT_YELLOW);
    }
    else if (command == "start_collection") {
        Serial.println("Starting data collection...");
        display.updateStatus("Starting collection", TFT_CYAN);
        
        if (sessionManager.startSession()) {
            sensorManager.startCollection(sessionManager.getQueue());
            mqttManager->publishStatus("collection_started");
            display.updateStatus("Collecting...", TFT_GREEN);
        } else {
            mqttManager->publishStatus("collection_failed");
        }
    }
    else if (command == "stop_collection") {
        Serial.println("Stopping data collection...");
        display.updateStatus("Stopping...", TFT_YELLOW);
        
        sensorManager.stopCollection();
        sessionManager.stopSession();
        
        // Transmit data
        display.updateStatus("Uploading data...", TFT_YELLOW);
        if (dataTransmitter->transmitSession(sessionManager)) {
            mqttManager->publishStatus("upload_complete");
            display.updateStatus("Upload complete!", TFT_GREEN);
        } else {
            mqttManager->publishStatus("upload_failed");
            display.updateStatus("Upload failed!", TFT_RED);
        }
        
        // Clear buffer
        sessionManager.clearBuffer();
        display.updateStatus("Ready", TFT_CYAN);
    }
    else if (command == "reboot") {
        display.updateStatus("Rebooting...", TFT_YELLOW);
        delay(1000);
        ESP.restart();
    }
}

void loop() {
    static unsigned long lastHeartbeat = 0;
    static int buttonState1 = HIGH;
    static int buttonState2 = HIGH;
    
    int currentButton1 = digitalRead(BUTTON_1);
    int currentButton2 = digitalRead(BUTTON_2);

    if (!systemInitialized) {
        // Print heartbeat while waiting
        if (millis() - lastHeartbeat > 2000) {
            lastHeartbeat = millis();
            Serial.print(". Waiting for button... (uptime: ");
            Serial.print(millis() / 1000);
            Serial.println("s)");
        }

        // Check for LEFT button press to initialize
        if (currentButton1 == LOW && buttonState1 == HIGH) {
            Serial.println("\n*** LEFT BUTTON PRESSED! ***");
            delay(200);
            initializeSystem();
        }
        buttonState1 = currentButton1;

        // Check for RIGHT button press to restart
        if (currentButton2 == LOW && buttonState2 == HIGH) {
            Serial.println("\n*** RIGHT BUTTON PRESSED - RESTARTING ***");
            ESP.restart();
        }
        buttonState2 = currentButton2;

        delay(50);
        return;
    }

    // System is initialized - normal operation
    
    // Check for button press to restart
    if (currentButton2 == LOW && buttonState2 == HIGH) {
        Serial.println("RIGHT BUTTON - Restarting...");
        ESP.restart();
    }
    buttonState2 = currentButton2;

    // Check network connection
    networkManager.checkConnection();

    // Handle MQTT
    mqttManager->loop();

    // Process sensor data queue if collecting
    if (sessionManager.getState() == COLLECTING) {
        sessionManager.processQueue();
    }

    // Send periodic status updates
    if (millis() - lastStatusUpdate > STATUS_UPDATE_INTERVAL) {
        lastStatusUpdate = millis();

        if (mqttManager->isConnected()) {
            mqttManager->publishStatus("online");
            Serial.print("Status update sent. Session state: ");
            
            switch(sessionManager.getState()) {
                case IDLE: Serial.println("IDLE"); break;
                case COLLECTING: 
                    Serial.print("COLLECTING (");
                    Serial.print(sessionManager.getDataCount());
                    Serial.println(" samples)");
                    break;
                case UPLOADING: Serial.println("UPLOADING"); break;
            }
        }
    }

    delay(10);
}
```

---

## Step 5: Update platformio.ini

Make sure your `platformio.ini` has these settings:

```ini
build_flags = 
    -DBOARD_HAS_PSRAM
    -DARDUINO_USB_MODE=1
    -DARDUINO_USB_CDC_ON_BOOT=1
    -DCORE_DEBUG_LEVEL=3
    -Ifirmware/include
```

---

## Step 6: Build and Upload

### 6.1 Build the project

```bash
pio run
```

Fix any compilation errors before proceeding.

### 6.2 Upload to device

```bash
pio run --target upload && pio device monitor
```

### 6.3 Press LEFT button to initialize

You should see all systems initialize including sensors.

---

## Step 7: Test Data Collection

### 7.1 Start a collection session

In AWS IoT Core MQTT Test Client:

**Publish to:** `motionplay/motionplay-device-001/commands`

```json
{
  "command": "start_collection",
  "timestamp": 1234567890
}
```

**Expected:** Device starts collecting sensor data

### 7.2 Wave hand in front of sensors

Move your hand over the sensors for 5-10 seconds to generate data.

### 7.3 Stop collection

**Publish to:** `motionplay/motionplay-device-001/commands`

```json
{
  "command": "stop_collection",
  "timestamp": 1234567891
}
```

**Expected:** 
- Device stops collecting
- Data is uploaded in batches to AWS
- Status messages show progress

### 7.4 Verify data in AWS

Check your serial monitor for:
```
Session started: device-001_xxxxx
Buffered: 1000 samples
Buffered: 2000 samples
...
Stopping session...
Session stopped. Duration: 5234ms, Samples: 5234
Transmitting session device-001_xxxxx (5234 readings)
Transmitting batch 0 (100 samples)
Transmitting batch 1 (100 samples)
...
Session transmission complete!
```

---

## Step 8: Verify Data in DynamoDB

### 8.1 Check Lambda logs

```bash
aws logs tail /aws/lambda/motionplay-processData --follow
```

You should see logs showing data being processed.

### 8.2 Query DynamoDB

```bash
# Check sessions table
aws dynamodb scan --table-name MotionPlaySessions --max-items 5

# Check sensor data table (use your session_id from logs)
aws dynamodb query \
    --table-name MotionPlaySensorData \
    --key-condition-expression "session_id = :sid" \
    --expression-attribute-values '{":sid":{"S":"device-001_xxxxx"}}'
```

---

## Troubleshooting

### Issue: Sensors fail to initialize

**Symptoms:** "Failed to initialize sensor X" errors

**Solutions:**
- Check I2C connections (SDA=43, SCL=44)
- Verify TCA9548A multiplexer is connected
- Check sensor power (3.3V)
- Try reducing I2C clock speed: `Wire.setClock(100000)`

### Issue: Buffer full / samples dropped

**Symptoms:** "Buffer full, dropping samples" warnings

**Solutions:**
- Reduce collection time
- Increase `MAX_BUFFER_SIZE` in SessionManager.h
- Increase queue size in SessionManager constructor

### Issue: MQTT publish fails during upload

**Symptoms:** "Failed to transmit batch" errors

**Solutions:**
- Check MQTT connection is still active
- Reduce `BATCH_SIZE` in DataTransmitter.h
- Increase delay between batches
- Check AWS IoT Core message size limits (128KB)

### Issue: Core 0 watchdog timeout

**Symptoms:** ESP32 restarts with "Task watchdog" error

**Solutions:**
- Add `vTaskDelay(1)` in sensor loop
- Reduce sampling rate
- Optimize sensor reading code

### Issue: Memory allocation fails

**Symptoms:** "Failed to allocate buffer" or crashes

**Solutions:**
- Ensure PSRAM is enabled in platformio.ini
- Reduce `MAX_BUFFER_SIZE`
- Check available heap: `Serial.println(ESP.getFreeHeap())`

---

## Success Criteria

Phase 2 is complete when:

- ✅ Sensors initialize successfully (all 6)
- ✅ Can start collection via MQTT command
- ✅ Data buffered at ~1000 Hz for 30 seconds
- ✅ Can stop collection via MQTT command
- ✅ Data transmitted to AWS in batches
- ✅ Data appears in DynamoDB tables
- ✅ No memory leaks or crashes
- ✅ Display shows collection status

---

## Next Steps

Once Phase 2 is working:

**Phase 3: Web Interface**
- Set up API Gateway
- Build React frontend
- Display session data
- Visualize sensor readings

---

## Useful Commands

```bash
# Build and upload
pio run --target upload && pio device monitor

# Monitor only
pio device monitor

# Clean build
pio run --target clean && pio run

# Check Lambda logs
aws logs tail /aws/lambda/motionplay-processData --follow

# Query recent sessions
aws dynamodb scan --table-name MotionPlaySessions \
    --filter-expression "device_id = :did" \
    --expression-attribute-values '{":did":{"S":"motionplay-device-001"}}' \
    --max-items 10
```

---

**Ready to start Phase 2!** Follow the steps above and let me know if you encounter any issues.


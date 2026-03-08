#include <Arduino.h>
#include <Adafruit_VCNL4040.h>
#include <ArduinoJson.h>
#include "components/config/ConfigLoader.h"
#include "components/network/NetworkManager.h"
#include "components/mqtt/MQTTManager.h"
#include "components/display/DisplayManager.h"
#include "components/sensor/SensorManager.h"
#include "components/sensor/SensorConfiguration.h"
#include "components/session/SessionManager.h"
#include "components/data/DataTransmitter.h"
#include "components/data/BinarySerializer.h"
#include "components/diagnostics/MemoryMonitor.h"
#include "components/detection/DirectionDetector.h"
#include "components/detection/MLDetector.h"
#include "components/detection/DetectionController.h"
#include "components/led/LEDController.h"
#include "components/interrupt/InterruptManager.h"
#include "components/calibration/CalibrationManager.h"
#include "components/display/CalibrationScreen.h"
#include "components/command/CommandHandler.h"
#include "components/cloud/CloudConfig.h"
#include "components/serialstudio/SerialStudioOutput.h"
#include "constants.h"
#include "debug_log.h"

// Button pins for T-Display-S3
#define BUTTON_1 0  // Left button (BOOT)
#define BUTTON_2 14 // Right button

// Managers
NetworkManager networkManager;
MQTTManager *mqttManager;
DisplayManager display;
CalibrationScreen calibrationScreen(display.getTft());
SensorManager sensorManager;
SessionManager sessionManager;
DataTransmitter *dataTransmitter;
BinarySerializer *binarySerializer;
DirectionDetector directionDetector;
MLDetector mlDetector;
LEDController ledController;
SerialStudioOutput serialStudioOutput;

// Detection mode: false = heuristic (DirectionDetector), true = ML (MLDetector)
bool useMLDetection = false;

// Detection algorithm config (runtime-configurable via cloud config)
DetectorConfig detectorConfig;

// Serial Studio output: compile-time default from build flags, overridable via cloud config
bool serialStudioEnabled = SERIAL_STUDIO_DEFAULT;
InterruptManager interruptManager;
CommandHandler *commandHandler = nullptr;

// Current device mode
DeviceMode currentMode = DeviceMode::DEBUG; // Default to debug for backwards compatibility

// Play mode state
bool playModeActive = false;
unsigned long lastDetectionTime = 0;
const unsigned long DETECTION_COOLDOWN = 500; // 500ms - prevents double-trigger, allows quick successive throws

DetectionController detectionController(
    directionDetector, mlDetector,
    ledController, display,
    serialStudioOutput, sessionManager,
    useMLDetection, lastDetectionTime, DETECTION_COOLDOWN);

// Live Debug mode state
bool liveDebugActive = false;

// Timing
unsigned long lastStatusUpdate = 0;
const unsigned long STATUS_UPDATE_INTERVAL = 30000; // 30 seconds

// Global sensor configuration instance
SensorConfiguration currentConfig;

// Forward declarations
void initializeSystem();

void setup()
{
    Serial.begin(115200);
    delay(500);

    Serial.println("\n\n=================================");
    Serial.println("Motion Play Device - BOOT");
    Serial.println("=================================");
    Serial.println("Press RIGHT button (GPIO 14) to restart anytime");
    Serial.println("=================================\n");

    pinMode(BUTTON_1, INPUT_PULLUP);
    pinMode(BUTTON_2, INPUT_PULLUP);

    if (!display.init())
    {
        Serial.println("ERROR: Display initialization failed!");
        while (1)
            delay(1000);
    }
    display.showInitScreen();
    Serial.println("Display initialized");

    initializeSystem();

    Serial.println("\n=== Setup Complete - Entering Loop ===\n");
}

void initializeSystem()
{
    Serial.println("\n=== Starting System Initialization ===\n");

    display.updateInitStage(INIT_BOOT, "Booting up...");

    // --- Phase 1: Network (WiFi → MQTT → cloud config) ---
    // Done first so we have the real sensor config before initializing hardware.

    Serial.println("Loading device config...");
    ConfigLoader configLoader;
    if (!configLoader.load())
    {
        Serial.println("ERROR: Config failed!");
        display.setInitError("Config load failed!");
        while (1)
            delay(1000);
    }
    networkManager.applyConfig(configLoader.getConfig());
    Serial.println("Config loaded successfully");

    Serial.println("Connecting to WiFi...");
    display.updateInitStage(INIT_WIFI_CONNECTING, "Connecting to WiFi...");
    if (!networkManager.connectWiFi())
    {
        Serial.println("ERROR: WiFi failed!");
        display.setInitError("WiFi connection failed!");
        while (1)
            delay(1000);
    }
    Serial.println("WiFi connected!");
    display.updateInitStage(INIT_WIFI_CONNECTED, "WiFi connected");

    mqttManager = new MQTTManager(&networkManager);

    Serial.println("Loading MQTT config...");
    if (!mqttManager->applyConfig(configLoader.getConfig()))
    {
        Serial.println("ERROR: MQTT config failed!");
        display.setInitError("MQTT config failed!");
        while (1)
            delay(1000);
    }
    Serial.println("MQTT config loaded");

    Serial.println("Connecting to MQTT...");
    display.updateInitStage(INIT_MQTT_CONNECTING, "Connecting to AWS IoT...");
    if (!mqttManager->connect())
    {
        Serial.println("WARNING: MQTT connection failed");
        display.setInitError("MQTT connection failed!");
        delay(3000);
    }
    else
    {
        Serial.println("MQTT connected!");
        display.updateInitStage(INIT_MQTT_CONNECTED, "AWS IoT connected");
    }

    dataTransmitter = new DataTransmitter(mqttManager);
    binarySerializer = new BinarySerializer(mqttManager);
    sessionManager.setDeviceId(networkManager.getDeviceId());

    commandHandler = new CommandHandler(
        mqttManager, display, sensorManager, sessionManager,
        dataTransmitter, binarySerializer, directionDetector, mlDetector,
        ledController, interruptManager, serialStudioOutput, detectionController,
        currentConfig, currentMode, useMLDetection, detectorConfig,
        playModeActive, liveDebugActive, lastDetectionTime);

    mqttManager->setCallback([](char *topic, byte *payload, unsigned int length)
                             {
        if (length > MQTT_MAX_INCOMING_MSG) {
            Serial.printf("MQTT message too large (%u bytes, max %u) — dropped\n",
                          length, (unsigned)MQTT_MAX_INCOMING_MSG);
            return;
        }

        char message[MQTT_MAX_INCOMING_MSG + 1];
        memcpy(message, payload, length);
        message[length] = '\0';

        DynamicJsonDocument doc(1024);
        DeserializationError error = deserializeJson(doc, message);

        if (!error) {
            String command = doc["command"].as<String>();
            Serial.print("Received command: ");
            Serial.println(command);
            commandHandler->handleCommand(command, &doc);
        } });

    // Fetch cloud config so sensors get initialized with the right settings
    Serial.println("Fetching sensor config from cloud...");
    display.updateInitStage(INIT_COMPLETE, "Loading config...");
    CloudConfig cloudConfig(networkManager);
    bool cloudConfigLoaded = cloudConfig.fetch(currentConfig, useMLDetection,
                                               detectorConfig, serialStudioEnabled);
    if (cloudConfigLoaded)
    {
        serialStudioOutput.setEnabled(serialStudioEnabled);
        directionDetector.setConfig(detectorConfig);
        Serial.println("Cloud config loaded — sensors will init with cloud settings");
    }
    else
    {
        Serial.println("WARNING: Cloud config unavailable, sensors will use defaults");
    }

    Serial.printf("\n[Config] Detection mode: %s (useMLDetection=%d)\n",
                  useMLDetection ? "ML" : "heuristic", useMLDetection);

    // --- Phase 2: Sensors (one-shot init with final config) ---

    Serial.println("Initializing sensors...");
    display.updateInitStage(INIT_SENSORS, "Initializing sensors...");
    if (!sensorManager.init(&currentConfig))
    {
        Serial.println("ERROR: Sensor initialization failed!");
        display.setInitError("Sensor init failed!");
        while (1)
            delay(1000);
    }
    Serial.println("Sensors initialized successfully");

    // CalibrationManager (just GPIO setup, no delay)
    Serial.println("Initializing CalibrationManager...");
    if (!calibrationManager.begin(&sensorManager, &calibrationScreen))
    {
        Serial.println("WARNING: CalibrationManager init failed");
    }
    else
    {
        Serial.println("CalibrationManager initialized");
    }

    // --- Phase 3: Detection & output ---

    if (useMLDetection)
    {
        Serial.println("\n=== Initializing ML Detector ===");
        if (!mlDetector.init())
        {
            Serial.println("WARNING: ML detector initialization failed, falling back to heuristic");
            useMLDetection = false;
        }
        else
        {
            Serial.println("ML detector initialized successfully");
        }
    }

    serialStudioOutput.begin(&sessionManager.getDataBuffer(), &directionDetector);
    serialStudioOutput.setConfig(&currentConfig);
    serialStudioOutput.setEnabled(serialStudioEnabled);
    Serial.printf("Serial Studio output: %s\n", serialStudioEnabled ? "enabled" : "disabled");

    // --- Done ---

    Serial.println("\n=== System Initialization Complete ===\n");
    MemoryMonitor::printMemoryStats();

    display.updateInitStage(INIT_COMPLETE, "System ready!");
    delay(500);

    display.setSensorConfig(&currentConfig);
    display.setDetectionConfig(detectorConfig.peakMultiplier, detectorConfig.minRise,
                               detectorConfig.minWaveDurationMs, detectorConfig.smoothingWindow);
    display.showSessionScreen();
}

void loop()
{
    static int buttonState2 = HIGH;
    static unsigned long lastSampleUpdate = 0;
    static unsigned long button1HoldStart = 0;
    static bool button1WasPressed = false;

    int currentButton1 = digitalRead(BUTTON_1);
    int currentButton2 = digitalRead(BUTTON_2);

    // If calibration is active, handle it exclusively
    if (calibrationManager.isActive())
    {
        calibrationManager.update();

        // After calibration completes, restore normal display
        if (!calibrationManager.isActive())
        {
            display.showSessionScreen();
            display.setSensorConfig(&currentConfig);

            // Set sensor config in calibration manager for next time
            uint8_t mp = currentConfig.multi_pulse.toInt();
            if (mp == 0)
                mp = 1;
            uint8_t it = currentConfig.integration_time.substring(0, 1).toInt();
            if (it == 0)
                it = 1;
            uint8_t led = currentConfig.led_current.toInt();
            if (led == 0)
                led = 200;
            calibrationManager.setSensorConfig(mp, it, led);
        }

        delay(10);
        return; // Skip normal loop during calibration
    }

    // Check for LEFT button (BOOT) long-press to start calibration
    if (currentButton1 == LOW)
    {
        if (!button1WasPressed)
        {
            button1WasPressed = true;
            button1HoldStart = millis();
        }
        else if (millis() - button1HoldStart >= 3000)
        {
            // 3 second hold - trigger calibration
            Serial.println("Button 1 held 3s - Starting calibration...");

            // Only start if not collecting
            if (sessionManager.getState() == IDLE)
            {
                // Set sensor config before starting
                uint8_t mp = currentConfig.multi_pulse.toInt();
                if (mp == 0)
                    mp = 1;
                uint8_t it = currentConfig.integration_time.substring(0, 1).toInt();
                if (it == 0)
                    it = 1;
                uint8_t led = currentConfig.led_current.toInt();
                if (led == 0)
                    led = 200;
                calibrationManager.setSensorConfig(mp, it, led);

                calibrationManager.startCalibration();
            }
            else
            {
                display.showMessage("Stop collection first!", TFT_RED);
                delay(1500);
                display.setDisplayState(DISPLAY_IDLE);
            }

            button1WasPressed = false; // Reset to prevent re-trigger
            button1HoldStart = 0;
        }
    }
    else
    {
        button1WasPressed = false;
        button1HoldStart = 0;
    }

    // Check for RIGHT button press to restart anytime
    if (currentButton2 == LOW && buttonState2 == HIGH)
    {
        Serial.println("RIGHT BUTTON - Restarting...");
        display.showMessage("Restarting...", TFT_YELLOW);
        delay(500);
        ESP.restart();
    }
    buttonState2 = currentButton2;

    // Check network connection
    networkManager.checkConnection();

    // Handle MQTT
    mqttManager->loop();

    // Process sensor data queue if collecting
    if (sessionManager.getState() == COLLECTING)
    {
        // Check session type to determine processing method
        bool isInterruptSession = (sessionManager.getSessionType() == SessionType::INTERRUPT_BASED);

        if (isInterruptSession)
        {
            // INTERRUPT MODE: Drain events from InterruptManager
            while (interruptManager.hasEvents())
            {
                InterruptEvent evt;
                if (interruptManager.getNextEvent(evt))
                {
                    sessionManager.addInterruptEvent(evt);
                }
            }

            // Update display periodically
            static unsigned long lastIntUpdate = 0;
            if (millis() - lastIntUpdate > 500)
            {
                lastIntUpdate = millis();
                size_t eventCount = sessionManager.getInterruptEventCount();

                // Log event count
                Serial.printf("[INT] Events: %d\n", eventCount);
            }

            // Check for maximum session duration (30 seconds for interrupt too)
            if (sessionManager.getDuration() >= 30000)
            {
                Serial.println("WARNING: Maximum interrupt session duration reached (30s), auto-stopping...");
                display.showMessage("Max duration!", TFT_ORANGE);
                delay(1000);

                // Auto-stop
                interruptManager.stopMonitoring();
                sessionManager.stopSession();
                display.setDisplayState(DISPLAY_UPLOADING);

                if (dataTransmitter->transmitSession(sessionManager, &currentConfig))
                {
                    mqttManager->publishStatus("upload_complete_auto_stopped");
                    display.setDisplayState(DISPLAY_SUCCESS);
                    delay(2000);
                    sessionManager.clearBuffer();
                    display.setDisplayState(DISPLAY_IDLE);
                }
                else
                {
                    mqttManager->publishStatus("upload_failed");
                    display.setDisplayState(DISPLAY_ERROR);
                    delay(2000);
                    sessionManager.clearBuffer();
                    display.setDisplayState(DISPLAY_IDLE);
                }
            }
        }
        else
        {
            // POLLING MODE: Regular proximity processing
            sessionManager.processQueue();

            // Serial Studio: emit CSV frames for new readings
            serialStudioOutput.update();
        }

        if ((playModeActive && currentMode == DeviceMode::PLAY) ||
            (liveDebugActive && currentMode == DeviceMode::LIVE_DEBUG))
        {
            detectionController.update();
        }
        else
        {
            // DEBUG MODE: Standard collection behavior

            // Check for maximum session duration (30 seconds safety limit)
            if (sessionManager.getDuration() >= 30000) // 30 seconds in milliseconds
            {
                Serial.println("WARNING: Maximum session duration reached (30s), auto-stopping...");
                display.showMessage("Max duration reached!", TFT_ORANGE);
                delay(1000);

                // Auto-stop collection
                sensorManager.stopCollection();
                sessionManager.stopSession();
                display.setDisplayState(DISPLAY_UPLOADING);

                // Session Confirmation: finalize summary
                {
                    uint8_t activeCnt = 0;
                    for (const auto &m : sessionManager.getSensorMetadata())
                    {
                        if (m.active)
                            activeCnt++;
                    }
                    sessionManager.finalizeSessionSummary(&currentConfig, activeCnt);
                    dataTransmitter->setSessionSummary(&sessionManager.getSessionSummary());
                }

                // Transmit data
                if (dataTransmitter->transmitSession(sessionManager, &currentConfig))
                {
                    // Session Confirmation: send summary
                    dataTransmitter->transmitSessionSummary(
                        sessionManager.getSessionSummary(),
                        sessionManager.getSessionId(),
                        mqttManager->getDeviceId());

                    mqttManager->publishStatus("upload_complete_auto_stopped");
                    display.setDisplayState(DISPLAY_SUCCESS);
                    delay(2000);
                    dataTransmitter->setSessionSummary(nullptr);
                    sessionManager.clearBuffer();
                    display.setDisplayState(DISPLAY_IDLE);
                }
                else
                {
                    Serial.println("ERROR: Auto-stop session transmission failed!");
                    mqttManager->publishStatus("upload_failed");
                    display.setDisplayState(DISPLAY_ERROR);
                    display.showMessage("Upload failed - Restarting...", TFT_RED);
                    delay(3000);
                    dataTransmitter->setSessionSummary(nullptr);
                    sessionManager.clearBuffer();

                    // Restart device to recover from potential I2C/sensor issues
                    Serial.println("Restarting device to recover from upload failure...");
                    ESP.restart();
                }
            }

            // Update sample count on display every second
            if (millis() - lastSampleUpdate > 1000)
            {
                lastSampleUpdate = millis();
                int sampleCount = sessionManager.getDataCount();
                display.updateSampleCount(sampleCount);

                if (debugPrintEnabled())
                {
                    Serial.printf("Samples: %d | ", sampleCount);
                    MemoryMonitor::printCompactStatus();
                }

                if (!MemoryMonitor::isMemoryHealthy())
                {
                    DEBUG_LOG("WARNING: Memory getting low during collection!\n");
                }
            }
        }
    }

    // Send periodic status updates
    if (millis() - lastStatusUpdate > STATUS_UPDATE_INTERVAL)
    {
        lastStatusUpdate = millis();

        if (mqttManager->isConnected())
        {
            mqttManager->publishStatus("online");
            if (debugPrintEnabled())
            {
                Serial.print("Status update sent. Session state: ");
                switch (sessionManager.getState())
                {
                case IDLE:
                    Serial.println("IDLE");
                    break;
                case COLLECTING:
                    Serial.print("COLLECTING (");
                    Serial.print(sessionManager.getDataCount());
                    Serial.println(" samples)");
                    break;
                case UPLOADING:
                    Serial.println("UPLOADING");
                    break;
                }
            }
        }
    }

    delay(10);
}
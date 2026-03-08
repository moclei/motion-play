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
#include "components/collection/CollectionController.h"
#include "components/cloud/CloudConfig.h"
#include "components/button/ButtonHandler.h"
#include "components/serialstudio/SerialStudioOutput.h"
#include "pin_config.h"
#include "constants.h"
#include "debug_log.h"

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
ButtonHandler buttonHandler(PIN_BUTTON_2, PIN_BUTTON_1); // left=BOOT(GPIO0), right=GPIO14
CommandHandler *commandHandler = nullptr;
CollectionController *collectionController = nullptr;

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

    buttonHandler.init();

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

    collectionController = new CollectionController(
        interruptManager, sessionManager, sensorManager,
        serialStudioOutput, display, dataTransmitter, mqttManager,
        detectionController, currentConfig, currentMode,
        playModeActive, liveDebugActive);

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

    ButtonEvent buttonEvent = buttonHandler.update();

    if (buttonEvent == ButtonEvent::LEFT_LONG_PRESS)
    {
        Serial.println("Button 1 held 3s - Starting calibration...");

        if (sessionManager.getState() == IDLE)
        {
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
    }
    else if (buttonEvent == ButtonEvent::RIGHT_PRESS)
    {
        Serial.println("RIGHT BUTTON - Restarting...");
        display.showMessage("Restarting...", TFT_YELLOW);
        delay(500);
        ESP.restart();
    }

    // Check network connection
    networkManager.checkConnection();

    // Handle MQTT
    mqttManager->loop();

    if (sessionManager.getState() == COLLECTING)
    {
        collectionController->update();
    }
    else if (sessionManager.getState() == UPLOADING)
    {
        TransmitState txState = dataTransmitter->tick();

        if (txState == TransmitState::SUCCEEDED)
        {
            const UploadContext &ctx = dataTransmitter->getUploadContext();

            if (ctx.sendSummary)
            {
                dataTransmitter->transmitSessionSummary(
                    sessionManager.getSessionSummary(),
                    sessionManager.getSessionId(),
                    mqttManager->getDeviceId());
            }

            mqttManager->publishStatus(ctx.successStatus);
            display.setDisplayState(DISPLAY_SUCCESS);
            delay(ctx.displayDelayMs);
            dataTransmitter->setSessionSummary(nullptr);
            dataTransmitter->resetTransmission();
            sessionManager.clearBuffer();
            display.setDisplayState(DISPLAY_IDLE);
        }
        else if (txState == TransmitState::FAILED)
        {
            const UploadContext &ctx = dataTransmitter->getUploadContext();

            Serial.println("ERROR: Session transmission failed!");
            mqttManager->publishStatus("upload_failed");
            display.setDisplayState(DISPLAY_ERROR);
            display.showMessage(ctx.restartOnFailure
                                    ? "Upload failed - Restarting..."
                                    : "Upload failed!",
                                TFT_RED);
            delay(ctx.restartOnFailure ? 3000 : ctx.displayDelayMs);
            dataTransmitter->setSessionSummary(nullptr);
            dataTransmitter->resetTransmission();
            sessionManager.clearBuffer();

            if (ctx.restartOnFailure)
            {
                ESP.restart();
            }
            display.setDisplayState(DISPLAY_IDLE);
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
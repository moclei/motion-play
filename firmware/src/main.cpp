#include <Arduino.h>
#include <Adafruit_VCNL4040.h>
#include <HTTPClient.h>
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
#include "components/led/LEDController.h"
#include "components/interrupt/InterruptManager.h"
#include "components/calibration/CalibrationManager.h"
#include "components/display/CalibrationScreen.h"
#include "components/command/CommandHandler.h"
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

// Live Debug mode state
bool liveDebugActive = false;

// Live Debug capture window constants
const size_t LIVE_DEBUG_BUFFER_CAP = 18000;        // ~3 seconds buffer cap
const unsigned long DETECTION_WINDOW_MS = 500;     // 0.5s of pre-detection data to capture
const unsigned long POST_DETECTION_DELAY_MS = 250; // 0.25s of post-detection data (sensor task keeps collecting)

// Timing
unsigned long lastStatusUpdate = 0;
const unsigned long STATUS_UPDATE_INTERVAL = 30000; // 30 seconds

// Global sensor configuration instance
SensorConfiguration currentConfig;

// Forward declarations
void initializeSystem();
bool fetchConfigFromCloud();

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

bool fetchConfigFromCloud()
{
    Serial.println("\n=== Fetching Config from Cloud ===");

    // Get device ID and API endpoint from NetworkManager
    String deviceId = networkManager.getDeviceId();
    String apiEndpoint = networkManager.getApiEndpoint();

    if (apiEndpoint.isEmpty())
    {
        Serial.println("WARNING: No API endpoint configured, using defaults");
        return false;
    }

    // Construct URL
    String url = apiEndpoint + "/device/" + deviceId + "/config";
    Serial.printf("Fetching config from: %s\n", url.c_str());

    HTTPClient http;
    http.begin(url);
    http.setTimeout(5000);

    int httpCode = http.GET();

    if (httpCode == HTTP_CODE_OK)
    {
        String payload = http.getString();
        Serial.println("Config received:");
        Serial.println(payload);

        // Parse JSON response
        DynamicJsonDocument doc(2048);
        DeserializationError error = deserializeJson(doc, payload);

        if (error)
        {
            Serial.print("JSON parse error: ");
            Serial.println(error.c_str());
            http.end();
            return false;
        }

        // Extract sensor_config
        if (doc.containsKey("sensor_config"))
        {
            JsonObject config = doc["sensor_config"];

            // Update current configuration
            // Handle both sample_rate and sample_rate_hz for compatibility
            if (config.containsKey("sample_rate_hz"))
            {
                currentConfig.sample_rate_hz = config["sample_rate_hz"];
            }
            else if (config.containsKey("sample_rate"))
            {
                currentConfig.sample_rate_hz = config["sample_rate"];
            }

            currentConfig.led_current = config["led_current"] | "200mA";
            currentConfig.integration_time = config["integration_time"] | "1T";
            currentConfig.high_resolution = config["high_resolution"] | true;
            currentConfig.read_ambient = config["read_ambient"] | true;

            // New field: I2C clock speed
            if (config.containsKey("i2c_clock_khz"))
            {
                currentConfig.i2c_clock_khz = config["i2c_clock_khz"];
            }

            // New field: Multi-pulse mode
            if (config.containsKey("multi_pulse"))
            {
                currentConfig.multi_pulse = config["multi_pulse"].as<String>();
            }
            else
            {
                currentConfig.multi_pulse = "1"; // Default: 1 pulse
            }

            // Physical geometry for transit speed estimation
            if (config.containsKey("ball_diameter_mm"))
                currentConfig.ball_diameter_mm = config["ball_diameter_mm"];
            if (config.containsKey("hoop_inner_diameter_mm"))
                currentConfig.hoop_inner_diameter_mm = config["hoop_inner_diameter_mm"];

            // Sensor mode (polling vs interrupt)
            if (config.containsKey("sensor_mode"))
            {
                String modeStr = config["sensor_mode"].as<String>();
                currentConfig.sensor_mode = (modeStr == "interrupt")
                                                ? SensorMode::INTERRUPT_MODE
                                                : SensorMode::POLLING_MODE;
            }

            // Interrupt settings (calibration-based approach)
            if (config.containsKey("interrupt_threshold_margin"))
            {
                currentConfig.interrupt_threshold_margin = config["interrupt_threshold_margin"];
            }
            if (config.containsKey("interrupt_hysteresis"))
            {
                currentConfig.interrupt_hysteresis = config["interrupt_hysteresis"];
            }
            if (config.containsKey("interrupt_integration_time"))
            {
                currentConfig.interrupt_integration_time = config["interrupt_integration_time"];
            }
            if (config.containsKey("interrupt_multi_pulse"))
            {
                currentConfig.interrupt_multi_pulse = config["interrupt_multi_pulse"];
            }
            if (config.containsKey("interrupt_persistence"))
            {
                currentConfig.interrupt_persistence = config["interrupt_persistence"];
            }
            if (config.containsKey("interrupt_smart_persistence"))
            {
                currentConfig.interrupt_smart_persistence = config["interrupt_smart_persistence"];
            }
            if (config.containsKey("interrupt_mode"))
            {
                currentConfig.interrupt_mode = config["interrupt_mode"].as<String>();
            }

            Serial.println("\nConfig loaded from cloud:");
            Serial.printf("  Sensor Mode: %s\n", currentConfig.sensor_mode == SensorMode::INTERRUPT_MODE ? "INTERRUPT" : "POLLING");
            Serial.printf("  Sample Rate: %d Hz\n", currentConfig.sample_rate_hz);
            Serial.printf("  LED Current: %s\n", currentConfig.led_current.c_str());
            Serial.printf("  Integration Time: %s\n", currentConfig.integration_time.c_str());
            Serial.printf("  Multi-Pulse: %s pulses\n", currentConfig.multi_pulse.c_str());
            Serial.printf("  High Resolution: %s\n", currentConfig.high_resolution ? "enabled" : "disabled");
            Serial.printf("  Read Ambient: %s\n", currentConfig.read_ambient ? "enabled" : "disabled");
            Serial.printf("  I2C Clock: %d kHz\n", currentConfig.i2c_clock_khz);
            if (currentConfig.sensor_mode == SensorMode::INTERRUPT_MODE)
            {
                Serial.printf("  INT Threshold Margin: %d\n", currentConfig.interrupt_threshold_margin);
                Serial.printf("  INT Hysteresis: %d\n", currentConfig.interrupt_hysteresis);
                Serial.printf("  INT Integration Time: %dT\n", currentConfig.interrupt_integration_time);
                Serial.printf("  INT Multi-Pulse: %d\n", currentConfig.interrupt_multi_pulse);
            }

            // Check for detection_mode in sensor config
            if (config.containsKey("detection_mode"))
            {
                String detMode = config["detection_mode"].as<String>();
                useMLDetection = (detMode == "ml");
                Serial.printf("  Detection Mode: %s (raw value: '%s')\n", useMLDetection ? "ML" : "heuristic", detMode.c_str());
            }
            else
            {
                Serial.println("  Detection Mode: not present in cloud config (defaulting to heuristic)");
            }

            if (config.containsKey("serial_studio_enabled"))
            {
                serialStudioEnabled = config["serial_studio_enabled"].as<bool>();
                serialStudioOutput.setEnabled(serialStudioEnabled);
                Serial.printf("  Serial Studio: %s\n", serialStudioEnabled ? "enabled" : "disabled");
            }

            // Detection algorithm parameters
            if (config.containsKey("peak_multiplier"))
                detectorConfig.peakMultiplier = config["peak_multiplier"].as<float>();
            if (config.containsKey("min_rise"))
                detectorConfig.minRise = config["min_rise"];
            if (config.containsKey("min_wave_duration_ms"))
                detectorConfig.minWaveDurationMs = config["min_wave_duration_ms"];
            if (config.containsKey("smoothing_window"))
                detectorConfig.smoothingWindow = config["smoothing_window"];

            directionDetector.setConfig(detectorConfig);
            Serial.printf("  Detection Config: peak=%.1fx, rise=%d, wave=%dms, smooth=%d\n",
                          detectorConfig.peakMultiplier, detectorConfig.minRise,
                          detectorConfig.minWaveDurationMs, detectorConfig.smoothingWindow);

            http.end();
            return true;
        }
        else
        {
            Serial.println("WARNING: No sensor_config in response");
            http.end();
            return false;
        }
    }
    else
    {
        Serial.printf("HTTP GET failed, error: %s (code: %d)\n", http.errorToString(httpCode).c_str(), httpCode);
        http.end();
        return false;
    }
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
        ledController, interruptManager, serialStudioOutput, currentConfig,
        currentMode, useMLDetection, detectorConfig,
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
    bool cloudConfigLoaded = fetchConfigFromCloud();
    if (cloudConfigLoaded)
    {
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

        // PLAY MODE: Run direction detection on collected data
        if (playModeActive && currentMode == DeviceMode::PLAY)
        {
            // Update LED animation (handles fade-out after detection)
            bool animating = ledController.update();

            static unsigned long lastPlayDebug = 0;
            if (debugPrintEnabled() && millis() - lastPlayDebug > 2000)
            {
                lastPlayDebug = millis();
                bool detectorReady = useMLDetection ? mlDetector.isReady() : directionDetector.isReady();
                Serial.printf("[PLAY] Buffer: %d samples, Detector(%s): %s\n",
                              sessionManager.getDataCount(),
                              useMLDetection ? "ML" : "heuristic",
                              detectorReady ? "READY" : "establishing baseline...");
            }

            // Check cooldown between detections
            unsigned long now = millis();
            bool inCooldown = (lastDetectionTime > 0) && (now - lastDetectionTime < DETECTION_COOLDOWN);

            if (!inCooldown)
            {
                // Feed new readings to the detector
                auto &buffer = sessionManager.getDataBuffer();
                static size_t lastProcessedIndex = 0;

                // Add new readings since last check
                size_t bufferSize = buffer.size();
                for (size_t i = lastProcessedIndex; i < bufferSize; i++)
                {
                    if (useMLDetection)
                        mlDetector.addReading(buffer[i]);
                    else
                        directionDetector.addReading(buffer[i]);
                }
                // Flush the last reading to ensure it's processed
                if (useMLDetection)
                    mlDetector.flushReading();
                else
                    directionDetector.flushReading();
                lastProcessedIndex = bufferSize;

                // Check for detection
                bool detected = useMLDetection ? mlDetector.hasDetection() : directionDetector.hasDetection();
                if (detected)
                {
                    DetectionResult result = useMLDetection ? mlDetector.getResult() : directionDetector.getResult();
                    serialStudioOutput.cacheDetection(result);

                    // Detection successful!
                    DEBUG_LOG("DETECTION [%s]: %s (confidence: %.2f)\n",
                             useMLDetection ? "ML" : "heuristic",
                             directionToString(result.direction),
                             result.confidence);

                    // Show on LEDs
                    ledController.showDirection(result.direction, 3000);

                    // Show on display
                    if (result.direction == Direction::A_TO_B)
                        display.showMessage("A -> B", TFT_BLUE);
                    else if (result.direction == Direction::B_TO_A)
                        display.showMessage("B -> A", TFT_ORANGE);
                    else
                        display.showMessage("Unknown", TFT_RED);

                    // Publish detection result
                    String statusMsg = "detection_" + String(directionToString(result.direction));
                    mqttManager->publishStatus(statusMsg.c_str());

                    // Reset for next detection (clear buffer without changing state)
                    lastDetectionTime = now;
                    if (useMLDetection)
                        mlDetector.reset();
                    else
                        directionDetector.reset();
                    lastProcessedIndex = 0;
                    buffer.clear();
                    serialStudioOutput.resetIndex();
                    DEBUG_LOG("Detection complete, buffer cleared for next event\n");
                }

                // Limit buffer size to prevent memory issues in play mode.
                // Only clear the session buffer — detectors maintain their own
                // internal state (ring buffer for ML, wave state for heuristic)
                // and must NOT be reset here or they lose accumulated data.
                if (bufferSize > 500)
                {
                    DEBUG_LOG("Buffer overflow prevention: clearing %d samples\n", bufferSize);
                    if (!useMLDetection)
                        directionDetector.reset();
                    lastProcessedIndex = 0;
                    buffer.clear();
                    serialStudioOutput.resetIndex();
                }
            }
            else if (!ledController.isAnimating() &&
                     (useMLDetection ? mlDetector.isReady() : directionDetector.isReady()))
            {
                ledController.showReady();
            }

            // No timeout in play mode - it runs until stopped
        }
        else if (liveDebugActive && currentMode == DeviceMode::LIVE_DEBUG)
        {
            // LIVE DEBUG MODE: Detection with event capture

            // Update LED animation (handles fade-out after detection)
            ledController.update();

            static unsigned long lastLiveDebugLog = 0;
            if (debugPrintEnabled() && millis() - lastLiveDebugLog > 2000)
            {
                lastLiveDebugLog = millis();
                bool detectorReady = useMLDetection ? mlDetector.isReady() : directionDetector.isReady();
                Serial.printf("[LIVE_DEBUG] Buffer: %d samples, Detector(%s): %s\n",
                              sessionManager.getDataCount(),
                              useMLDetection ? "ML" : "heuristic",
                              detectorReady ? "READY" : "establishing baseline...");
            }

            // Check cooldown between detections
            unsigned long now = millis();
            bool inCooldown = (lastDetectionTime > 0) && (now - lastDetectionTime < DETECTION_COOLDOWN);

            if (!inCooldown)
            {
                // Feed new readings to the detector
                auto &buffer = sessionManager.getDataBuffer();
                static size_t lastLiveDebugIndex = 0;

                // Add new readings since last check
                size_t bufferSize = buffer.size();
                for (size_t i = lastLiveDebugIndex; i < bufferSize; i++)
                {
                    if (useMLDetection)
                        mlDetector.addReading(buffer[i]);
                    else
                        directionDetector.addReading(buffer[i]);
                }
                if (useMLDetection)
                    mlDetector.flushReading();
                else
                    directionDetector.flushReading();
                lastLiveDebugIndex = bufferSize;

                // Check for detection
                bool detected = useMLDetection ? mlDetector.hasDetection() : directionDetector.hasDetection();
                if (detected)
                {
                    DetectionResult result = useMLDetection ? mlDetector.getResult() : directionDetector.getResult();
                    serialStudioOutput.cacheDetection(result);

                    DEBUG_LOG("[LIVE_DEBUG] DETECTION [%s]: %s (confidence: %.2f)\n",
                             useMLDetection ? "ML" : "heuristic",
                             directionToString(result.direction),
                             result.confidence);

                    // LED feedback (same as Play)
                    ledController.showDirection(result.direction, 3000);

                    // Display feedback
                    if (result.direction == Direction::A_TO_B)
                        display.showMessage("A -> B", TFT_BLUE);
                    else if (result.direction == Direction::B_TO_A)
                        display.showMessage("B -> A", TFT_ORANGE);
                    else
                        display.showMessage("Unknown", TFT_RED);

                    // === CAPTURE FLOW: Delay → Pause → Extract → Transmit → Resume ===

                    // 1. Post-detection delay: keep collecting so we capture the trailing edge
                    //    Sensor task runs on Core 0, so delay() on Core 1 lets it continue
                    DEBUG_LOG("[LIVE_DEBUG] Post-detection delay: %lums\n", POST_DETECTION_DELAY_MS);
                    delay(POST_DETECTION_DELAY_MS);

                    // 2. Stop sensor polling
                    sensorManager.stopCollection();
                    delay(50); // Let queue drain

                    // Process any remaining queued readings
                    sessionManager.processQueue();

                    // 3. Show transmitting status
                    display.showMessage("Transmitting...", TFT_MAGENTA);

                    // 4. Calculate window using actual timestamps in the buffer
                    //    Capture from (detectionTime - DETECTION_WINDOW_MS) to end of buffer
                    size_t actualBufferSize = buffer.size();
                    size_t startIdx = 0;

                    if (actualBufferSize > 0)
                    {
                        unsigned long latestTs = buffer[actualBufferSize - 1].timestamp_us;
                        unsigned long totalWindowUs = (DETECTION_WINDOW_MS + POST_DETECTION_DELAY_MS) * 1000UL; // Convert ms to us
                        unsigned long cutoffTs = (latestTs > totalWindowUs) ? latestTs - totalWindowUs : 0;

                        // Binary search for the first reading at or after cutoffTs
                        size_t lo = 0, hi = actualBufferSize;
                        while (lo < hi)
                        {
                            size_t mid = lo + (hi - lo) / 2;
                            if (buffer[mid].timestamp_us < cutoffTs)
                                lo = mid + 1;
                            else
                                hi = mid;
                        }
                        startIdx = lo;
                    }

                    size_t captureCount = actualBufferSize - startIdx;
                    DEBUG_LOG("[LIVE_DEBUG] Capture: %d readings from idx %d (buffer has %d)\n",
                             captureCount, startIdx, actualBufferSize);

                    // 5. Session Confirmation: finalize summary for this capture
                    {
                        uint8_t activeCnt = 0;
                        for (const auto &m : sessionManager.getSensorMetadata())
                        {
                            if (m.active)
                                activeCnt++;
                        }
                        // Use capture duration for summary, not full session duration
                        unsigned long capDur = (captureCount > 0)
                                                   ? (buffer[actualBufferSize - 1].timestamp_us - buffer[startIdx].timestamp_us) / 1000
                                                   : 0;
                        sessionManager.getSessionSummary().duration_ms = capDur;
                        sessionManager.finalizeSessionSummary(&currentConfig, activeCnt);
                    }

                    // 6. Transmit the capture (binary-packed single message — data + summary)
                    const char *dirStr;
                    if (result.direction == Direction::A_TO_B)
                        dirStr = "a_to_b";
                    else if (result.direction == Direction::B_TO_A)
                        dirStr = "b_to_a";
                    else
                        dirStr = "unknown";
                    String captureSessionId = binarySerializer->transmitLiveDebugCaptureBinary(
                        buffer, startIdx, captureCount,
                        "detection", dirStr, result.confidence,
                        sessionManager.getSessionSummary(),
                        &currentConfig);

                    if (captureSessionId.length() > 0)
                    {
                        DEBUG_LOG("[LIVE_DEBUG] Detection capture transmitted successfully\n");
                        mqttManager->publishStatus("live_debug_detection_captured");
                    }
                    else
                    {
                        DEBUG_LOG("[LIVE_DEBUG] ERROR: Detection capture transmission failed!\n");
                        mqttManager->publishStatus("live_debug_capture_failed");
                    }

                    // 7. Clear buffer and reset detector
                    lastDetectionTime = millis();
                    if (useMLDetection)
                        mlDetector.reset();
                    else
                        directionDetector.reset();
                    lastLiveDebugIndex = 0;
                    buffer.clear();
                    serialStudioOutput.resetIndex();

                    // 8. Reset summary for next capture and resume sensor polling
                    sessionManager.getSessionSummary().reset();
                    sensorManager.startCollection(sessionManager.getQueue(), &sessionManager.getSessionSummary());
                    display.showMessage("Ready", TFT_MAGENTA);
                    DEBUG_LOG("[LIVE_DEBUG] Resumed — waiting for next event\n");
                }

                // Buffer overflow prevention (higher cap than Play)
                if (bufferSize > LIVE_DEBUG_BUFFER_CAP)
                {
                    DEBUG_LOG("[LIVE_DEBUG] Buffer overflow prevention: clearing %d samples\n", bufferSize);
                    if (useMLDetection)
                        mlDetector.reset();
                    else
                        directionDetector.reset();
                    lastLiveDebugIndex = 0;
                    buffer.clear();
                    serialStudioOutput.resetIndex();
                }
            }
            else if (!ledController.isAnimating() &&
                     (useMLDetection ? mlDetector.isReady() : directionDetector.isReady()))
            {
                ledController.showReady();
            }

            // No timeout in live debug mode - runs until stopped
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
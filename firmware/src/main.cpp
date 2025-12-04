#include <Arduino.h>
#include <Adafruit_VCNL4040.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "components/network/NetworkManager.h"
#include "components/mqtt/MQTTManager.h"
#include "components/display/DisplayManager.h"
#include "components/sensor/SensorManager.h"
#include "components/sensor/SensorConfiguration.h"
#include "components/session/SessionManager.h"
#include "components/data/DataTransmitter.h"
#include "components/diagnostics/MemoryMonitor.h"
#include "components/detection/DirectionDetector.h"
#include "components/led/LEDController.h"

// Button pins for T-Display-S3
#define BUTTON_1 0  // Left button (BOOT)
#define BUTTON_2 14 // Right button

// Device modes
enum class DeviceMode {
    IDLE,   // Standby mode
    DEBUG,  // Data collection for algorithm development
    PLAY    // Active game mode with direction detection
};

// Managers
NetworkManager networkManager;
MQTTManager *mqttManager;
DisplayManager display;
SensorManager sensorManager;
SessionManager sessionManager;
DataTransmitter *dataTransmitter;
DirectionDetector directionDetector;
LEDController ledController;

// Current device mode
DeviceMode currentMode = DeviceMode::DEBUG;  // Default to debug for backwards compatibility

// Play mode state
bool playModeActive = false;
unsigned long lastDetectionTime = 0;
const unsigned long DETECTION_COOLDOWN = 3000; // 3 seconds between detections

// Timing
unsigned long lastStatusUpdate = 0;
const unsigned long STATUS_UPDATE_INTERVAL = 30000; // 30 seconds

bool systemInitialized = false;

// Global sensor configuration instance
SensorConfiguration currentConfig;

// Forward declarations
void initializeSystem();
void handleCommand(const String &command, JsonDocument *doc = nullptr);
bool fetchConfigFromCloud();

void setup()
{
    Serial.begin(115200);
    delay(1500); // Initial stabilization delay

    Serial.println("\n\n\n=================================");
    Serial.println("Motion Play Device - BOOT");
    Serial.println("=================================");
    Serial.println("Serial is working!");
    Serial.println("Auto-initializing in 3 seconds...");
    Serial.println("Press RIGHT button (GPIO 14) to restart anytime");
    Serial.println("=================================\n");

    // Initialize buttons
    pinMode(BUTTON_1, INPUT_PULLUP);
    pinMode(BUTTON_2, INPUT_PULLUP);
    Serial.println("Buttons initialized");

    // Initialize display
    display.init();
    display.showInitScreen();
    Serial.println("Display initialized");

    // Longer delay for WiFi hardware stabilization (ESP32 needs 3-5 seconds)
    Serial.println("Waiting for hardware to stabilize...");
    delay(3000);

    // Auto-initialize system
    Serial.println("\n=== Starting Auto-Initialization ===\n");
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
    http.setTimeout(10000); // 10 second timeout

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
                currentConfig.multi_pulse = "1";  // Default: 1 pulse
            }

            Serial.println("\nConfig loaded from cloud:");
            Serial.printf("  Sample Rate: %d Hz\n", currentConfig.sample_rate_hz);
            Serial.printf("  LED Current: %s\n", currentConfig.led_current.c_str());
            Serial.printf("  Integration Time: %s\n", currentConfig.integration_time.c_str());
            Serial.printf("  Multi-Pulse: %s pulses\n", currentConfig.multi_pulse.c_str());
            Serial.printf("  High Resolution: %s\n", currentConfig.high_resolution ? "enabled" : "disabled");
            Serial.printf("  Read Ambient: %s\n", currentConfig.read_ambient ? "enabled" : "disabled");
            Serial.printf("  I2C Clock: %d kHz\n", currentConfig.i2c_clock_khz);

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
    delay(500);

    // Initialize sensors first (with current configuration)
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
    delay(500);

    // Load network configuration
    Serial.println("Loading WiFi config...");
    if (!networkManager.loadConfig())
    {
        Serial.println("ERROR: Config failed!");
        display.setInitError("Config load failed!");
        while (1)
            delay(1000);
    }
    Serial.println("Config loaded successfully");
    delay(500); // Give WiFi stack time to initialize

    // Connect to WiFi
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
    delay(500);

    // Initialize MQTT
    mqttManager = new MQTTManager(&networkManager);

    Serial.println("Loading MQTT config...");
    if (!mqttManager->loadConfig())
    {
        Serial.println("ERROR: MQTT config failed!");
        display.setInitError("MQTT config failed!");
        while (1)
            delay(1000);
    }
    Serial.println("MQTT config loaded");

    // Connect to MQTT
    Serial.println("Connecting to MQTT...");
    display.updateInitStage(INIT_MQTT_CONNECTING, "Connecting to AWS IoT...");
    if (!mqttManager->connect())
    {
        Serial.println("WARNING: MQTT connection failed");
        display.setInitError("MQTT connection failed!");
        delay(3000); // Show error, but continue (can retry later)
    }
    else
    {
        Serial.println("MQTT connected!");
        display.updateInitStage(INIT_MQTT_CONNECTED, "AWS IoT connected");
    }
    delay(500);

    // Initialize data transmitter
    dataTransmitter = new DataTransmitter(mqttManager);

    // Set up command handler
    mqttManager->setCallback([](char *topic, byte *payload, unsigned int length)
                             {
        char message[length + 1];
        memcpy(message, payload, length);
        message[length] = '\0';

        DynamicJsonDocument doc(1024);  // Increased size for sensor config
        DeserializationError error = deserializeJson(doc, message);

        if (!error) {
            String command = doc["command"].as<String>();
            handleCommand(command, &doc);
        } });

    // Fetch configuration from cloud
    Serial.println("Fetching sensor config from cloud...");
    display.updateInitStage(INIT_COMPLETE, "Loading config...");
    if (fetchConfigFromCloud())
    {
        Serial.println("Config fetched successfully, applying to sensors...");

        // Apply config to sensors
        if (sensorManager.reinitialize(&currentConfig))
        {
            Serial.println("Config applied to sensors successfully!");
        }
        else
        {
            Serial.println("WARNING: Failed to apply config to sensors, using defaults");
        }
    }
    else
    {
        Serial.println("WARNING: Failed to fetch config from cloud, using defaults");
    }

    // Initialization complete!
    Serial.println("\n=== System Initialization Complete ===\n");

    // Print memory statistics after initialization
    MemoryMonitor::printMemoryStats();

    display.updateInitStage(INIT_COMPLETE, "System ready!");
    delay(1500);

    // Switch to session screen and show current config
    display.setSensorConfig(&currentConfig);
    display.showSessionScreen();
    systemInitialized = true;
}

void handleCommand(const String &command, JsonDocument *doc)
{
    Serial.print("Received command: ");
    Serial.println(command);

    if (command == "ping")
    {
        mqttManager->publishStatus("pong");
        display.showMessage("Ping received", TFT_YELLOW);
        delay(1000);
        display.setDisplayState(DISPLAY_IDLE);
    }
    else if (command == "start_collection")
    {
        if (currentMode == DeviceMode::PLAY)
        {
            // PLAY MODE: Start direction detection
            Serial.println("Starting PLAY mode - Direction detection active");
            
            // Initialize LED controller if not already done
            if (!ledController.init())
            {
                Serial.println("WARNING: LED controller init failed");
            }
            
            // Reset the detector
            directionDetector.reset();
            
            // Start sensor collection with internal queue for detection
            if (sessionManager.startSession())
            {
                sensorManager.startCollection(sessionManager.getQueue());
                playModeActive = true;
                lastDetectionTime = 0;
                
                mqttManager->publishStatus("play_started");
                display.showMessage("PLAY MODE ACTIVE", TFT_GREEN);
                display.setDisplayState(DISPLAY_RECORDING);
                
                // Show ready state on LEDs
                ledController.showReady();
            }
            else
            {
                mqttManager->publishStatus("play_failed");
                display.setDisplayState(DISPLAY_ERROR);
            }
        }
        else
        {
            // DEBUG MODE: Standard data collection
            Serial.println("Starting data collection (DEBUG mode)...");

            // Check memory health before starting collection
            MemoryMonitor::printMemoryStats();
            if (!MemoryMonitor::isMemoryHealthy())
            {
                Serial.println("ERROR: Insufficient memory to start collection!");
                mqttManager->publishStatus("collection_failed_low_memory");
                display.showMessage("Low memory!", TFT_RED);
                delay(2000);
                display.setDisplayState(DISPLAY_ERROR);
                return;
            }

            if (sessionManager.startSession())
            {
                // Set sensor metadata for this session
                std::vector<SensorMetadata> metadata = sensorManager.getSensorMetadata();
                sessionManager.setSensorMetadata(metadata);

                sensorManager.startCollection(sessionManager.getQueue());
                mqttManager->publishStatus("collection_started");

                // Update display to recording state (config panel already shows settings)
                display.setDisplayState(DISPLAY_RECORDING);
            }
            else
            {
                mqttManager->publishStatus("collection_failed");
                display.setDisplayState(DISPLAY_ERROR);
            }
        }
    }
    else if (command == "stop_collection")
    {
        if (playModeActive && currentMode == DeviceMode::PLAY)
        {
            // PLAY MODE: Just stop detection, no upload needed
            Serial.println("Stopping PLAY mode...");
            
            sensorManager.stopCollection();
            sessionManager.stopSession();
            sessionManager.clearBuffer();
            
            playModeActive = false;
            directionDetector.reset();
            ledController.off();
            
            mqttManager->publishStatus("play_stopped");
            display.showMessage("Play mode stopped", TFT_YELLOW);
            delay(1500);
            display.setDisplayState(DISPLAY_IDLE);
        }
        else
        {
            // DEBUG MODE: Stop collection and upload data
            Serial.println("Stopping data collection...");

            sensorManager.stopCollection();
            sessionManager.stopSession();

            // Print memory stats after collection
            Serial.printf("Collected %d samples\n", sessionManager.getDataCount());
            MemoryMonitor::printMemoryStats();

            // Update display to uploading state
            display.setDisplayState(DISPLAY_UPLOADING);

            // Transmit data (include current sensor configuration)
            if (dataTransmitter->transmitSession(sessionManager, &currentConfig))
            {
                mqttManager->publishStatus("upload_complete");
                display.setDisplayState(DISPLAY_SUCCESS);

                // Return to idle after showing success
                delay(3000);
                sessionManager.clearBuffer();
                display.setDisplayState(DISPLAY_IDLE);
            }
            else
            {
                Serial.println("ERROR: Session transmission failed!");
                mqttManager->publishStatus("upload_failed");
                display.setDisplayState(DISPLAY_ERROR);
                display.showMessage("Upload failed - Restarting...", TFT_RED);

                // Return to idle after showing error
                delay(3000);
                sessionManager.clearBuffer();

                // Restart device to recover from potential I2C/sensor issues
                Serial.println("Restarting device to recover from upload failure...");
                ESP.restart();
            }
        }
    }
    else if (command == "configure_sensors")
    {
        Serial.println("Configuring sensors...");
        display.showMessage("Configuring sensors...", TFT_CYAN);

        if (doc != nullptr && doc->containsKey("sensor_config"))
        {
            JsonObject config = (*doc)["sensor_config"];

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
            else
            {
                currentConfig.sample_rate_hz = 1000; // Default
            }

            currentConfig.led_current = config["led_current"] | "200mA";
            currentConfig.integration_time = config["integration_time"] | "1T";
            currentConfig.duty_cycle = config["duty_cycle"] | "1/40";  // CRITICAL: Was missing!
            currentConfig.high_resolution = config["high_resolution"] | true;
            currentConfig.read_ambient = config["read_ambient"] | true;

            // Handle I2C clock speed if provided
            if (config.containsKey("i2c_clock_khz"))
            {
                currentConfig.i2c_clock_khz = config["i2c_clock_khz"];
            }

            // Handle multi-pulse mode if provided
            if (config.containsKey("multi_pulse"))
            {
                currentConfig.multi_pulse = config["multi_pulse"].as<String>();
            }
            else
            {
                currentConfig.multi_pulse = "1";  // Default: 1 pulse
            }

            Serial.println("Configuration updated:");
            Serial.printf("  Sample Rate: %d Hz\n", currentConfig.sample_rate_hz);
            Serial.printf("  LED Current: %s\n", currentConfig.led_current.c_str());
            Serial.printf("  Integration Time: %s\n", currentConfig.integration_time.c_str());
            Serial.printf("  Duty Cycle: %s\n", currentConfig.duty_cycle.c_str());
            Serial.printf("  Multi-Pulse: %s pulses\n", currentConfig.multi_pulse.c_str());
            Serial.printf("  High Resolution: %s\n", currentConfig.high_resolution ? "enabled" : "disabled");
            Serial.printf("  Read Ambient: %s\n", currentConfig.read_ambient ? "enabled" : "disabled");
            Serial.printf("  I2C Clock: %d kHz\n", currentConfig.i2c_clock_khz);

            // Apply configuration to sensors immediately
            if (sensorManager.reinitialize(&currentConfig))
            {
                // Update display with new config
                display.setSensorConfig(&currentConfig);
                display.showMessage("Config applied successfully!", TFT_GREEN);
                mqttManager->publishStatus("config_applied");
            }
            else
            {
                display.showMessage("Config apply failed", TFT_RED);
                mqttManager->publishStatus("config_failed");
            }
        }
        else
        {
            Serial.println("No sensor_config in command payload");
            display.showMessage("Config data missing", TFT_RED);
        }

        delay(2000);
        display.setDisplayState(DISPLAY_IDLE);
    }
    else if (command == "set_mode")
    {
        if (doc != nullptr && doc->containsKey("mode"))
        {
            String modeStr = (*doc)["mode"].as<String>();
            
            if (modeStr == "idle")
            {
                currentMode = DeviceMode::IDLE;
                playModeActive = false;
                ledController.off();
                display.setMode(MODE_IDLE);
                display.showMessage("Mode: IDLE", TFT_DARKGREY);
                mqttManager->publishStatus("mode_idle");
            }
            else if (modeStr == "debug")
            {
                currentMode = DeviceMode::DEBUG;
                playModeActive = false;
                ledController.off();
                display.setMode(MODE_DEBUG);
                display.showMessage("Mode: DEBUG", TFT_BLUE);
                mqttManager->publishStatus("mode_debug");
            }
            else if (modeStr == "play")
            {
                currentMode = DeviceMode::PLAY;
                display.setMode(MODE_PLAY);
                display.showMessage("Mode: PLAY", TFT_GREEN);
                mqttManager->publishStatus("mode_play");
                // LED controller will be initialized when play starts
            }
            else
            {
                display.showMessage("Unknown mode", TFT_RED);
                mqttManager->publishStatus("mode_invalid");
            }
            
            Serial.printf("Device mode set to: %s\n", modeStr.c_str());
            delay(1500);
            display.setDisplayState(DISPLAY_IDLE);
        }
    }
    else if (command == "reboot")
    {
        display.showMessage("Rebooting...", TFT_YELLOW);
        delay(1000);
        ESP.restart();
    }
}

void loop()
{
    static int buttonState2 = HIGH;
    static unsigned long lastSampleUpdate = 0;

    int currentButton2 = digitalRead(BUTTON_2);

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
        sessionManager.processQueue();

        // PLAY MODE: Run direction detection on collected data
        if (playModeActive && currentMode == DeviceMode::PLAY)
        {
            // Update LED animation (handles fade-out after detection)
            bool animating = ledController.update();
            
            // Debug: log buffer status periodically
            static unsigned long lastPlayDebug = 0;
            if (millis() - lastPlayDebug > 2000)
            {
                lastPlayDebug = millis();
                Serial.printf("[PLAY] Buffer: %d samples, Detector ready: %s\n", 
                    sessionManager.getDataCount(),
                    directionDetector.hasEnoughData() ? "YES" : "no");
            }
            
            // Check cooldown between detections
            unsigned long now = millis();
            bool inCooldown = (lastDetectionTime > 0) && (now - lastDetectionTime < DETECTION_COOLDOWN);
            
            if (!inCooldown)
            {
                // Feed new readings to the detector
                auto& buffer = sessionManager.getDataBuffer();
                static size_t lastProcessedIndex = 0;
                
                // Add new readings since last check
                size_t bufferSize = buffer.size();
                for (size_t i = lastProcessedIndex; i < bufferSize; i++)
                {
                    directionDetector.addReading(buffer[i]);
                }
                lastProcessedIndex = bufferSize;
                
                // Try to detect direction
                if (directionDetector.hasEnoughData())
                {
                    DetectionResult result = directionDetector.analyze();
                    
                    if (result.direction != Direction::UNKNOWN)
                    {
                        // Detection successful!
                        Serial.printf("DETECTION: %s (confidence: %.2f, gap: %dms)\n",
                            DirectionDetector::directionToString(result.direction),
                            result.confidence,
                            result.gapMs);
                        
                        // Show on LEDs
                        ledController.showDirection(result.direction, 3000);
                        
                        // Show on display
                        if (result.direction == Direction::A_TO_B)
                        {
                            display.showMessage("A -> B", TFT_BLUE);
                        }
                        else
                        {
                            display.showMessage("B -> A", TFT_ORANGE);
                        }
                        
                        // Publish detection result
                        String statusMsg = "detection_" + String(DirectionDetector::directionToString(result.direction));
                        mqttManager->publishStatus(statusMsg.c_str());
                        
                        // Reset for next detection (clear buffer without changing state)
                        lastDetectionTime = now;
                        directionDetector.reset();
                        lastProcessedIndex = 0;
                        buffer.clear();  // Clear buffer directly, don't reset session state
                        Serial.println("Detection complete, buffer cleared for next event");
                    }
                }
                
                // Limit buffer size to prevent memory issues in play mode
                if (bufferSize > 500)
                {
                    // Keep only recent data, reset detector
                    Serial.printf("Buffer overflow prevention: clearing %d samples\n", bufferSize);
                    directionDetector.reset();
                    lastProcessedIndex = 0;
                    buffer.clear();  // Clear buffer directly, don't reset session state
                }
            }
            else if (!ledController.isAnimating())
            {
                // Show ready pulse while in cooldown (but not animating a detection)
                ledController.showReady();
            }
            
            // No timeout in play mode - it runs until stopped
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

                // Transmit data
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
                    Serial.println("ERROR: Auto-stop session transmission failed!");
                    mqttManager->publishStatus("upload_failed");
                    display.setDisplayState(DISPLAY_ERROR);
                    display.showMessage("Upload failed - Restarting...", TFT_RED);
                    delay(3000);
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

                // Log to serial with memory status
                Serial.printf("Samples: %d | ", sampleCount);
                MemoryMonitor::printCompactStatus();

                // Check memory health during collection
                if (!MemoryMonitor::isMemoryHealthy())
                {
                    Serial.println("WARNING: Memory getting low during collection!");
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

    delay(10);
}
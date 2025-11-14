#include <Arduino.h>
#include <Adafruit_VCNL4040.h>
#include "components/network/NetworkManager.h"
#include "components/mqtt/MQTTManager.h"
#include "components/display/DisplayManager.h"
#include "components/sensor/SensorManager.h"
#include "components/sensor/SensorConfiguration.h"
#include "components/session/SessionManager.h"
#include "components/data/DataTransmitter.h"

// Button pins for T-Display-S3
#define BUTTON_1 0  // Left button (BOOT)
#define BUTTON_2 14 // Right button

// Managers
NetworkManager networkManager;
MQTTManager *mqttManager;
DisplayManager display;
SensorManager sensorManager;
SessionManager sessionManager;
DataTransmitter *dataTransmitter;

// Timing
unsigned long lastStatusUpdate = 0;
const unsigned long STATUS_UPDATE_INTERVAL = 30000; // 30 seconds

bool systemInitialized = false;

// Global sensor configuration instance
SensorConfiguration currentConfig;

// Forward declarations
void handleCommand(const String &command, JsonDocument *doc = nullptr);

void setup()
{
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

void initializeSystem()
{
    Serial.println("\n=== Button pressed! Starting initialization ===\n");
    display.updateStatus("Initializing...", TFT_YELLOW);

    // Initialize sensors first
    Serial.println("Initializing sensors...");
    display.updateStatus("Init sensors...");
    if (!sensorManager.init())
    {
        Serial.println("ERROR: Sensor initialization failed!");
        display.updateStatus("Sensor init failed!", TFT_RED);
        while (1)
            delay(1000);
    }
    Serial.println("Sensors initialized successfully");
    display.updateStatus("Sensors OK", TFT_GREEN);

    // Load network configuration
    Serial.println("Loading config...");
    display.updateStatus("Loading config...");
    if (!networkManager.loadConfig())
    {
        Serial.println("ERROR: Config failed!");
        display.updateStatus("Config failed!", TFT_RED);
        while (1)
            delay(1000);
    }
    Serial.println("Config loaded successfully");
    display.updateStatus("Config loaded", TFT_GREEN);

    // Connect to WiFi
    Serial.println("Connecting to WiFi...");
    display.updateStatus("Connecting WiFi...");
    if (!networkManager.connectWiFi())
    {
        Serial.println("ERROR: WiFi failed!");
        display.updateStatus("WiFi failed!", TFT_RED);
        while (1)
            delay(1000);
    }
    Serial.println("WiFi connected!");
    display.updateStatus("WiFi connected", TFT_GREEN);

    // Initialize MQTT
    mqttManager = new MQTTManager(&networkManager);

    Serial.println("Loading MQTT config...");
    display.updateStatus("Loading MQTT config...");
    if (!mqttManager->loadConfig())
    {
        Serial.println("ERROR: MQTT config failed!");
        display.updateStatus("MQTT config failed!", TFT_RED);
        while (1)
            delay(1000);
    }
    Serial.println("MQTT config loaded");

    // Connect to MQTT
    Serial.println("Connecting to MQTT...");
    display.updateStatus("Connecting MQTT...");
    if (!mqttManager->connect())
    {
        Serial.println("WARNING: MQTT connection failed");
        display.updateStatus("MQTT failed!", TFT_RED);
    }
    else
    {
        Serial.println("MQTT connected!");
        display.updateStatus("MQTT connected", TFT_GREEN);
    }

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

    Serial.println("\n=== System Initialization Complete ===\n");
    systemInitialized = true;
}

void handleCommand(const String &command, JsonDocument *doc)
{
    Serial.print("Received command: ");
    Serial.println(command);

    if (command == "ping")
    {
        mqttManager->publishStatus("pong");
        display.updateStatus("Ping received", TFT_YELLOW);
    }
    else if (command == "start_collection")
    {
        Serial.println("Starting data collection...");
        display.updateStatus("Starting collection", TFT_CYAN);

        if (sessionManager.startSession())
        {
            // Set sensor metadata for this session
            std::vector<SensorMetadata> metadata = sensorManager.getSensorMetadata();
            sessionManager.setSensorMetadata(metadata);

            sensorManager.startCollection(sessionManager.getQueue());
            mqttManager->publishStatus("collection_started");
            display.updateStatus("Collecting...", TFT_GREEN);
        }
        else
        {
            mqttManager->publishStatus("collection_failed");
        }
    }
    else if (command == "stop_collection")
    {
        Serial.println("Stopping data collection...");
        display.updateStatus("Stopping...", TFT_YELLOW);

        sensorManager.stopCollection();
        sessionManager.stopSession();

        // Transmit data (include current sensor configuration)
        display.updateStatus("Uploading data...", TFT_YELLOW);
        if (dataTransmitter->transmitSession(sessionManager, &currentConfig))
        {
            mqttManager->publishStatus("upload_complete");
            display.updateStatus("Upload complete!", TFT_GREEN);
        }
        else
        {
            mqttManager->publishStatus("upload_failed");
            display.updateStatus("Upload failed!", TFT_RED);
        }

        // Clear buffer
        sessionManager.clearBuffer();
        display.updateStatus("Ready", TFT_CYAN);
    }
    else if (command == "configure_sensors")
    {
        Serial.println("Configuring sensors...");
        display.updateStatus("Configuring sensors", TFT_CYAN);

        if (doc != nullptr && doc->containsKey("sensor_config"))
        {
            JsonObject config = (*doc)["sensor_config"];

            // Update current configuration
            currentConfig.sample_rate_hz = config["sample_rate"] | 1000;
            currentConfig.led_current = config["led_current"] | "200mA";
            currentConfig.integration_time = config["integration_time"] | "1T";
            currentConfig.high_resolution = config["high_resolution"] | true;

            Serial.println("Configuration updated:");
            Serial.printf("  Sample Rate: %d Hz\n", currentConfig.sample_rate_hz);
            Serial.printf("  LED Current: %s\n", currentConfig.led_current.c_str());
            Serial.printf("  Integration Time: %s\n", currentConfig.integration_time.c_str());
            Serial.printf("  High Resolution: %s\n", currentConfig.high_resolution ? "enabled" : "disabled");

            display.updateStatus("Config updated", TFT_GREEN);
            display.updateStatus("Restart for changes", TFT_YELLOW);
        }
        else
        {
            Serial.println("No sensor_config in command payload");
            display.updateStatus("Config missing", TFT_RED);
        }
    }
    else if (command == "reboot")
    {
        display.updateStatus("Rebooting...", TFT_YELLOW);
        delay(1000);
        ESP.restart();
    }
}

void loop()
{
    static unsigned long lastHeartbeat = 0;
    static int buttonState1 = HIGH;
    static int buttonState2 = HIGH;

    int currentButton1 = digitalRead(BUTTON_1);
    int currentButton2 = digitalRead(BUTTON_2);

    if (!systemInitialized)
    {
        // Print heartbeat while waiting
        if (millis() - lastHeartbeat > 2000)
        {
            lastHeartbeat = millis();
            Serial.print(". Waiting for button... (uptime: ");
            Serial.print(millis() / 1000);
            Serial.println("s)");
        }

        // Check for LEFT button press to initialize
        if (currentButton1 == LOW && buttonState1 == HIGH)
        {
            Serial.println("\n*** LEFT BUTTON PRESSED! ***");
            delay(200);
            initializeSystem();
        }
        buttonState1 = currentButton1;

        // Check for RIGHT button press to restart
        if (currentButton2 == LOW && buttonState2 == HIGH)
        {
            Serial.println("\n*** RIGHT BUTTON PRESSED - RESTARTING ***");
            ESP.restart();
        }
        buttonState2 = currentButton2;

        delay(50);
        return;
    }

    // System is initialized - normal operation

    // Check for button press to restart
    if (currentButton2 == LOW && buttonState2 == HIGH)
    {
        Serial.println("RIGHT BUTTON - Restarting...");
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
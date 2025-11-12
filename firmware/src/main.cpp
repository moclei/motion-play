#include <Arduino.h>
#include "components/network/NetworkManager.h"
#include "components/mqtt/MQTTManager.h"
#include "components/display/DisplayManager.h"

// Managers
NetworkManager networkManager;
MQTTManager* mqttManager;
DisplayManager display;

// Timing
unsigned long lastStatusUpdate = 0;
const unsigned long STATUS_UPDATE_INTERVAL = 30000; // 30 seconds

void setup() {
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n=== Motion Play Device Starting ===");

    // Initialize display
    display.init();
    display.showBootScreen();

    // Load network configuration
    display.updateStatus("Loading config...");
    if (!networkManager.loadConfig()) {
        display.updateStatus("Config failed!", TFT_RED);
        while (1) delay(1000);
    }
    display.updateStatus("Config loaded", TFT_GREEN);

    // Connect to WiFi
    display.updateStatus("Connecting WiFi...");
    if (!networkManager.connectWiFi()) {
        display.updateStatus("WiFi failed!", TFT_RED);
        while (1) delay(1000);
    }
    display.updateStatus("WiFi connected", TFT_GREEN);
    display.showNetworkInfo(WiFi.localIP().toString(), WiFi.RSSI());

    // Initialize MQTT
    mqttManager = new MQTTManager(&networkManager);

    display.updateStatus("Loading MQTT config...");
    if (!mqttManager->loadConfig()) {
        display.updateStatus("MQTT config failed!", TFT_RED);
        while (1) delay(1000);
    }

    // Connect to MQTT
    display.updateStatus("Connecting MQTT...");
    if (!mqttManager->connect()) {
        display.updateStatus("MQTT failed!", TFT_RED);
    } else {
        display.updateStatus("MQTT connected", TFT_GREEN);
    }

    display.showMQTTStatus(mqttManager->isConnected());

    // Set up custom command handler
    mqttManager->setCallback([](char* topic, byte* payload, unsigned int length) {
        // Handle incoming commands
        char message[length + 1];
        memcpy(message, payload, length);
        message[length] = '\0';

        DynamicJsonDocument doc(256);
        DeserializationError error = deserializeJson(doc, message);

        if (!error) {
            String command = doc["command"].as<String>();

            if (command == "ping") {
                mqttManager->publishStatus("pong");
                display.updateStatus("Ping received", TFT_YELLOW);
            } else if (command == "reboot") {
                display.updateStatus("Rebooting...", TFT_YELLOW);
                delay(1000);
                ESP.restart();
            }
        }
    });

    Serial.println("=== Setup Complete ===");
}

void loop() {
    // Check network connection
    networkManager.checkConnection();

    // Handle MQTT
    mqttManager->loop();

    // Update display status
    display.showMQTTStatus(mqttManager->isConnected());

    // Send periodic status updates
    if (millis() - lastStatusUpdate > STATUS_UPDATE_INTERVAL) {
        lastStatusUpdate = millis();

        if (mqttManager->isConnected()) {
            mqttManager->publishStatus("online");
            Serial.println("Status update sent");
        }
    }

    // Small delay to prevent watchdog issues
    delay(10);
}
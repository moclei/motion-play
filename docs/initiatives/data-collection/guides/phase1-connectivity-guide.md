# Phase 1: ESP32 Basic Connectivity Implementation Guide

This guide walks you through implementing WiFi and MQTT connectivity on the ESP32, establishing communication with AWS IoT Core.

## Phase 1 Overview

**Goal:** Get the ESP32 connected to AWS IoT Core and verify bidirectional communication.

**Deliverables:**

1. WiFi connection with auto-reconnect
2. Secure MQTT connection to AWS IoT Core
3. Publishing device status on boot
4. Subscribing to command topic
5. Status display on T-Display screen

## Prerequisites

- ✅ AWS IoT Core configured (Phase 0)
- ✅ Certificates in `firmware/data/certs/`
- ✅ Config file updated with WiFi credentials and IoT endpoint
- ✅ PlatformIO environment ready

## Step 1: Update Configuration

First, ensure your `firmware/data/config.json` is properly configured:

```json
{
  "device_id": "motionplay-device-001",
  "wifi": {
    "ssid": "YOUR_WIFI_SSID",
    "password": "YOUR_WIFI_PASSWORD"
  },
  "mqtt": {
    "broker": "YOUR_IOT_ENDPOINT.iot.us-west-2.amazonaws.com",
    "port": 8883,
    "client_id": "motionplay-device-001"
  },
  "sampling": {
    "rate_hz": 1000,
    "max_duration_seconds": 30
  }
}
```

## Step 2: Create Core Components

### 2.1 Create Network Manager

Create `firmware/src/components/network/NetworkManager.h`:

```cpp
#ifndef NETWORK_MANAGER_H
#define NETWORK_MANAGER_H

#include <WiFi.h>
#include <WiFiClientSecure.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>

class NetworkManager {
private:
    String ssid;
    String password;
    WiFiClientSecure wifiClient;
    bool connected = false;

public:
    NetworkManager();
    bool loadConfig();
    bool connectWiFi();
    void disconnect();
    bool isConnected();
    WiFiClientSecure& getClient();
    void checkConnection();
};

#endif
```

Create `firmware/src/components/network/NetworkManager.cpp`:

```cpp
#include "NetworkManager.h"

NetworkManager::NetworkManager() {
    // Constructor
}

bool NetworkManager::loadConfig() {
    if (!SPIFFS.begin(true)) {
        Serial.println("Failed to mount SPIFFS");
        return false;
    }

    File configFile = SPIFFS.open("/config.json", "r");
    if (!configFile) {
        Serial.println("Failed to open config file");
        return false;
    }

    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, configFile);
    configFile.close();

    if (error) {
        Serial.print("Failed to parse config: ");
        Serial.println(error.c_str());
        return false;
    }

    ssid = doc["wifi"]["ssid"].as<String>();
    password = doc["wifi"]["password"].as<String>();

    return true;
}

bool NetworkManager::connectWiFi() {
    Serial.print("Connecting to WiFi: ");
    Serial.println(ssid);

    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid.c_str(), password.c_str());

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < 30) {
        delay(1000);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        connected = true;
        Serial.println("\nWiFi connected!");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
        return true;
    }

    Serial.println("\nWiFi connection failed!");
    return false;
}

void NetworkManager::disconnect() {
    WiFi.disconnect(true);
    connected = false;
}

bool NetworkManager::isConnected() {
    return WiFi.status() == WL_CONNECTED;
}

WiFiClientSecure& NetworkManager::getClient() {
    return wifiClient;
}

void NetworkManager::checkConnection() {
    if (!isConnected() && connected) {
        Serial.println("WiFi connection lost, reconnecting...");
        connectWiFi();
    }
}
```

### 2.2 Create MQTT Manager

Create `firmware/src/components/mqtt/MQTTManager.h`:

```cpp
#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>
#include "NetworkManager.h"

class MQTTManager {
private:
    PubSubClient mqttClient;
    NetworkManager* networkManager;
    String broker;
    int port;
    String clientId;
    String deviceId;

    // Topics
    String statusTopic;
    String dataTopic;
    String commandTopic;

    // Certificates
    String caCert;
    String clientCert;
    String privateKey;

    bool loadCertificates();
    static void messageCallback(char* topic, byte* payload, unsigned int length);

public:
    MQTTManager(NetworkManager* netManager);
    bool loadConfig();
    bool connect();
    void disconnect();
    bool isConnected();
    void loop();
    bool publishStatus(const char* status);
    bool publishData(const JsonDocument& data);
    void setCallback(std::function<void(char*, byte*, unsigned int)> callback);
};

#endif
```

Create `firmware/src/components/mqtt/MQTTManager.cpp`:

```cpp
#include "MQTTManager.h"

MQTTManager::MQTTManager(NetworkManager* netManager) : networkManager(netManager) {
    mqttClient.setClient(networkManager->getClient());
}

bool MQTTManager::loadConfig() {
    File configFile = SPIFFS.open("/config.json", "r");
    if (!configFile) return false;

    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, configFile);
    configFile.close();

    if (error) return false;

    broker = doc["mqtt"]["broker"].as<String>();
    port = doc["mqtt"]["port"];
    clientId = doc["mqtt"]["client_id"].as<String>();
    deviceId = doc["device_id"].as<String>();

    // Set up topics
    statusTopic = "motionplay/" + deviceId + "/status";
    dataTopic = "motionplay/" + deviceId + "/data";
    commandTopic = "motionplay/" + deviceId + "/commands";

    // Load certificates
    if (!loadCertificates()) {
        Serial.println("Failed to load certificates");
        return false;
    }

    mqttClient.setServer(broker.c_str(), port);
    mqttClient.setCallback(messageCallback);

    return true;
}

bool MQTTManager::loadCertificates() {
    // Load CA certificate
    File ca = SPIFFS.open("/certs/root-ca.pem", "r");
    if (!ca) {
        Serial.println("Failed to open CA certificate");
        return false;
    }
    caCert = ca.readString();
    ca.close();

    // Load client certificate
    File cert = SPIFFS.open("/certs/device-cert.pem", "r");
    if (!cert) {
        Serial.println("Failed to open device certificate");
        return false;
    }
    clientCert = cert.readString();
    cert.close();

    // Load private key
    File key = SPIFFS.open("/certs/private-key.pem", "r");
    if (!key) {
        Serial.println("Failed to open private key");
        return false;
    }
    privateKey = key.readString();
    key.close();

    // Configure secure client
    networkManager->getClient().setCACert(caCert.c_str());
    networkManager->getClient().setCertificate(clientCert.c_str());
    networkManager->getClient().setPrivateKey(privateKey.c_str());

    return true;
}

bool MQTTManager::connect() {
    if (!networkManager->isConnected()) {
        Serial.println("No WiFi connection");
        return false;
    }

    Serial.print("Connecting to MQTT broker: ");
    Serial.println(broker);

    int attempts = 0;
    while (!mqttClient.connected() && attempts < 5) {
        if (mqttClient.connect(clientId.c_str())) {
            Serial.println("MQTT connected!");

            // Subscribe to command topic
            if (mqttClient.subscribe(commandTopic.c_str())) {
                Serial.print("Subscribed to: ");
                Serial.println(commandTopic);
            }

            // Publish initial status
            publishStatus("online");

            return true;
        }

        Serial.print("MQTT connection failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" retrying in 5 seconds");

        attempts++;
        delay(5000);
    }

    return false;
}

void MQTTManager::disconnect() {
    mqttClient.disconnect();
}

bool MQTTManager::isConnected() {
    return mqttClient.connected();
}

void MQTTManager::loop() {
    if (!mqttClient.connected()) {
        connect();
    }
    mqttClient.loop();
}

bool MQTTManager::publishStatus(const char* status) {
    DynamicJsonDocument doc(256);
    doc["device_id"] = deviceId;
    doc["status"] = status;
    doc["timestamp"] = millis();
    doc["wifi_rssi"] = WiFi.RSSI();
    doc["free_heap"] = ESP.getFreeHeap();
    doc["uptime_ms"] = millis();

    String payload;
    serializeJson(doc, payload);

    return mqttClient.publish(statusTopic.c_str(), payload.c_str());
}

bool MQTTManager::publishData(const JsonDocument& data) {
    String payload;
    serializeJson(data, payload);

    return mqttClient.publish(dataTopic.c_str(), payload.c_str());
}

void MQTTManager::messageCallback(char* topic, byte* payload, unsigned int length) {
    Serial.print("Message received on topic: ");
    Serial.println(topic);

    char message[length + 1];
    memcpy(message, payload, length);
    message[length] = '\0';

    Serial.print("Payload: ");
    Serial.println(message);

    // Parse command
    DynamicJsonDocument doc(256);
    DeserializationError error = deserializeJson(doc, message);

    if (!error) {
        String command = doc["command"].as<String>();
        Serial.print("Command: ");
        Serial.println(command);

        // Handle commands here
        if (command == "ping") {
            // Respond to ping
            Serial.println("Received ping command");
        }
    }
}

void MQTTManager::setCallback(std::function<void(char*, byte*, unsigned int)> callback) {
    mqttClient.setCallback(callback);
}
```

### 2.3 Create Display Manager

Create `firmware/src/components/display/DisplayManager.h`:

```cpp
#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include <TFT_eSPI.h>

class DisplayManager {
private:
    TFT_eSPI tft = TFT_eSPI();
    int statusY = 0;

public:
    void init();
    void showBootScreen();
    void updateStatus(const String& status, uint16_t color = TFT_WHITE);
    void showNetworkInfo(const String& ip, int rssi);
    void showMQTTStatus(bool connected);
    void clear();
};

#endif
```

Create `firmware/src/components/display/DisplayManager.cpp`:

```cpp
#include "DisplayManager.h"

void DisplayManager::init() {
    tft.init();
    tft.setRotation(1); // Landscape
    tft.fillScreen(TFT_BLACK);
    tft.setTextSize(2);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
}

void DisplayManager::showBootScreen() {
    clear();
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.drawString("Motion Play", 10, 10);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString("Initializing...", 10, 40);
    statusY = 70;
}

void DisplayManager::updateStatus(const String& status, uint16_t color) {
    tft.setTextColor(color, TFT_BLACK);
    tft.fillRect(10, statusY, 220, 20, TFT_BLACK);
    tft.drawString(status, 10, statusY);
    statusY += 25;
    if (statusY > 160) statusY = 70; // Wrap around
}

void DisplayManager::showNetworkInfo(const String& ip, int rssi) {
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString("WiFi: " + ip, 10, 100);
    tft.drawString("RSSI: " + String(rssi) + " dBm", 10, 125);
}

void DisplayManager::showMQTTStatus(bool connected) {
    tft.setTextColor(connected ? TFT_GREEN : TFT_RED, TFT_BLACK);
    tft.fillRect(10, 150, 220, 20, TFT_BLACK);
    tft.drawString("MQTT: " + String(connected ? "Connected" : "Disconnected"), 10, 150);
}

void DisplayManager::clear() {
    tft.fillScreen(TFT_BLACK);
}
```

## Step 3: Update Main Program

Replace `firmware/src/main.cpp` with the Phase 1 implementation:

```cpp
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
```

## Step 4: Upload Filesystem

Before uploading the code, ensure your data files are in place:

1. **Upload the SPIFFS filesystem:**

```bash
cd firmware
pio run --target uploadfs
```

This uploads:

- `/data/config.json` (with your WiFi and IoT settings)
- `/data/certs/root-ca.pem`
- `/data/certs/device-cert.pem`
- `/data/certs/private-key.pem`

## Step 5: Build and Upload

1. **Build the project:**

```bash
pio run
```

2. **Upload to ESP32:**

```bash
pio run --target upload
```

3. **Monitor serial output:**

```bash
pio device monitor
```

## Step 6: Test Communication

### 6.1 Monitor MQTT Messages

In AWS Console, go to IoT Core → Test → Subscribe to topic:

- Subscribe to: `motionplay/+/status`
- You should see status messages every 30 seconds

### 6.2 Send Test Command

In AWS Console IoT Test client:

1. Publish to topic: `motionplay/motionplay-device-001/commands`
2. Message:

```json
{
  "command": "ping",
  "timestamp": 1234567890
}
```

You should see:

- "Ping received" on the display
- A "pong" status message published

### 6.3 Check DynamoDB

The status messages should trigger the Lambda function and store device status:

```bash
aws dynamodb scan --table-name MotionPlayDevices
```

## Troubleshooting

### WiFi Connection Issues

- Double-check SSID and password in config.json
- Ensure 2.4GHz network (ESP32 doesn't support 5GHz)
- Check serial monitor for error messages

### MQTT Connection Issues

- Verify IoT endpoint is correct (no extra .amazonaws.com)
- Check all 3 certificate files are present and valid
- Ensure IoT Policy is attached to certificate
- Check CloudWatch logs for Lambda errors

### Certificate Issues

- Ensure line endings are preserved (LF, not CRLF)
- Files should start with `-----BEGIN CERTIFICATE-----`
- No extra spaces or characters

### Display Issues

- Check User_Setup.h matches your T-Display S3 configuration
- Verify TFT_eSPI library is properly configured

## Success Criteria

Phase 1 is complete when:

- ✅ ESP32 connects to WiFi automatically
- ✅ ESP32 connects to AWS IoT Core over MQTT
- ✅ Status messages appear in AWS IoT Test console
- ✅ Device responds to ping command
- ✅ Display shows connection status
- ✅ Device status stored in DynamoDB

## Next Steps

Once Phase 1 is working:

1. Phase 2: Implement sensor data collection and transmission
2. Phase 3: Build web interface for monitoring
3. Phase 4: Add advanced features and polish

## Useful Commands

```bash
# Monitor serial output
pio device monitor

# Clean and rebuild
pio run --target clean
pio run

# Check device filesystem
pio run --target uploadfs

# View Lambda logs
aws logs tail /aws/lambda/motionplay-processStatus --follow
```

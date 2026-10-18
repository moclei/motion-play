#include "NetworkManager.h"
#include <esp_system.h>

NetworkManager::NetworkManager() {
    // Constructor
}

bool NetworkManager::loadConfig() {
    Serial.println("Attempting to mount LittleFS...");
    if (!LittleFS.begin(true)) {
        Serial.println("ERROR: Failed to mount LittleFS");
        return false;
    }
    Serial.println("LittleFS mounted successfully!");

    // List files in root directory
    Serial.println("Listing files in LittleFS root:");
    File root = LittleFS.open("/");
    if (!root) {
        Serial.println("Failed to open root directory");
    } else {
        File file = root.openNextFile();
        while (file) {
            Serial.print("  Found file: ");
            Serial.print(file.name());
            Serial.print(" (");
            Serial.print(file.size());
            Serial.println(" bytes)");
            file = root.openNextFile();
        }
    }

    Serial.println("Attempting to open /config.json...");
    File configFile = LittleFS.open("/config.json", "r");
    if (!configFile) {
        Serial.println("ERROR: Failed to open config file");
        Serial.println("Trying alternate path /data/config.json...");
        configFile = LittleFS.open("/data/config.json", "r");
        if (!configFile) {
            Serial.println("ERROR: Config file not found in either location");
            return false;
        }
    }
    Serial.println("Config file opened successfully!");
    Serial.flush();
    Serial.println("[DBG] A: after file open");
    Serial.flush();
    Serial.printf("[DBG] B: reset_reason=%d\n", (int)esp_reset_reason());
    Serial.flush();
    Serial.printf("[DBG] C: free_heap=%u\n", (unsigned)ESP.getFreeHeap());
    Serial.flush();
    Serial.printf("[DBG] D: free_psram=%u\n", (unsigned)ESP.getFreePsram());
    Serial.flush();

    Serial.println("[DBG] Allocating DynamicJsonDocument(1024)...");
    Serial.flush();
    DynamicJsonDocument doc(1024);
    Serial.println("[DBG] Doc allocated. Parsing...");
    Serial.flush();
    DeserializationError error = deserializeJson(doc, configFile);
    Serial.println("[DBG] Parse returned. Closing file...");
    Serial.flush();
    configFile.close();
    Serial.println("[DBG] File closed.");
    Serial.flush();

    if (error) {
        Serial.print("Failed to parse config: ");
        Serial.println(error.c_str());
        return false;
    }

    Serial.println("[DBG] Extracting ssid...");
    Serial.flush();
    ssid = doc["wifi"]["ssid"].as<String>();
    Serial.println("[DBG] Extracting password...");
    Serial.flush();
    password = doc["wifi"]["password"].as<String>();
    Serial.println("[DBG] Extracting deviceId...");
    Serial.flush();
    deviceId = doc["device_id"].as<String>();

    Serial.printf("[DBG] ssid='%s' deviceId='%s'\n", ssid.c_str(), deviceId.c_str());
    Serial.flush();

    // Load API endpoint if available
    if (doc.containsKey("api") && doc["api"].containsKey("endpoint"))
    {
        apiEndpoint = doc["api"]["endpoint"].as<String>();
        Serial.print("API Endpoint: ");
        Serial.println(apiEndpoint);
    }

    Serial.println("[DBG] loadConfig complete.");
    Serial.flush();
    return true;
}

bool NetworkManager::connectWiFi() {
    Serial.print("Connecting to WiFi: ");
    Serial.println(ssid);

    WiFi.mode(WIFI_STA);
    delay(100); // Give WiFi mode change time to take effect
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

String NetworkManager::getDeviceId() {
    return deviceId;
}

String NetworkManager::getApiEndpoint() {
    return apiEndpoint;
}
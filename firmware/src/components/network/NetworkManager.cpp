#include "NetworkManager.h"

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
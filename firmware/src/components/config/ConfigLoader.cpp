#include "ConfigLoader.h"
#include <LittleFS.h>
#include <ArduinoJson.h>
#include "constants.h"

bool ConfigLoader::load() {
    if (!mountFilesystem()) return false;
    if (!parseConfigFile()) return false;
    return true;
}

bool ConfigLoader::mountFilesystem() {
    Serial.println("Attempting to mount LittleFS...");
    if (!LittleFS.begin(true)) {
        Serial.println("ERROR: Failed to mount LittleFS");
        return false;
    }
    Serial.println("LittleFS mounted successfully!");

#ifdef DEBUG_FILESYSTEM
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
#endif

    return true;
}

bool ConfigLoader::parseConfigFile() {
    Serial.println("Attempting to open /config.json...");
    File configFile = LittleFS.open(CONFIG_FILE_PATH, "r");
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

    DynamicJsonDocument doc(CONFIG_JSON_CAPACITY);
    DeserializationError error = deserializeJson(doc, configFile);
    configFile.close();

    if (error) {
        Serial.print("Failed to parse config: ");
        Serial.println(error.c_str());
        return false;
    }

    config_.wifiSsid = doc["wifi"]["ssid"].as<String>();
    config_.wifiPassword = doc["wifi"]["password"].as<String>();
    config_.deviceId = doc["device_id"].as<String>();

    if (doc.containsKey("api") && doc["api"].containsKey("endpoint")) {
        config_.apiEndpoint = doc["api"]["endpoint"].as<String>();
        Serial.print("API Endpoint: ");
        Serial.println(config_.apiEndpoint);
    }

    config_.mqttBroker = doc["mqtt"]["broker"].as<String>();
    config_.mqttPort = doc["mqtt"]["port"];
    config_.mqttClientId = doc["mqtt"]["client_id"].as<String>();

    return true;
}

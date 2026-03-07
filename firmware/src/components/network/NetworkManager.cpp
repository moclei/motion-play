#include "NetworkManager.h"
#include "../config/ConfigLoader.h"

NetworkManager::NetworkManager() {
    // Constructor
}

void NetworkManager::applyConfig(const DeviceConfig& config) {
    ssid = config.wifiSsid;
    password = config.wifiPassword;
    deviceId = config.deviceId;
    apiEndpoint = config.apiEndpoint;
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

const String& NetworkManager::getDeviceId() const {
    return deviceId;
}

const String& NetworkManager::getApiEndpoint() const {
    return apiEndpoint;
}
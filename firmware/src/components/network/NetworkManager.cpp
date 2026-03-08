#include "NetworkManager.h"
#include "../config/ConfigLoader.h"

NetworkManager::NetworkManager() {
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
    delay(WIFI_MODE_SETTLE_MS);
    WiFi.begin(ssid.c_str(), password.c_str());

    int attempts = 0;
    while (WiFi.status() != WL_CONNECTED && attempts < WIFI_MAX_BOOT_ATTEMPTS) {
        delay(1000);
        Serial.print(".");
        attempts++;
    }

    if (WiFi.status() == WL_CONNECTED) {
        wifiState = WiFiState::CONNECTED;
        reconnectAttemptCount = 0;
        Serial.println("\nWiFi connected!");
        Serial.print("IP address: ");
        Serial.println(WiFi.localIP());
        return true;
    }

    wifiState = WiFiState::DISCONNECTED;
    Serial.println("\nWiFi connection failed!");
    return false;
}

void NetworkManager::disconnect() {
    WiFi.disconnect(true);
    wifiState = WiFiState::DISCONNECTED;
}

bool NetworkManager::isConnected() {
    return WiFi.status() == WL_CONNECTED;
}

WiFiClientSecure& NetworkManager::getClient() {
    return wifiClient;
}

void NetworkManager::checkConnection() {
    bool wifiUp = (WiFi.status() == WL_CONNECTED);

    switch (wifiState) {
    case WiFiState::CONNECTED:
        if (!wifiUp) {
            Serial.println("WiFi connection lost");
            wifiState = WiFiState::DISCONNECTED;
            reconnectAttemptCount = 0;
            lastReconnectAttemptMs = millis();
        }
        break;

    case WiFiState::DISCONNECTED: {
        uint32_t backoff = getReconnectBackoffMs();
        if (millis() - lastReconnectAttemptMs < backoff) break;

        Serial.printf("WiFi reconnecting (attempt %u, backoff %ums)...\n",
                       reconnectAttemptCount + 1, backoff);
        WiFi.begin(ssid.c_str(), password.c_str());
        lastReconnectAttemptMs = millis();
        wifiState = WiFiState::CONNECTING;
        break;
    }

    case WiFiState::CONNECTING:
        if (wifiUp) {
            Serial.println("WiFi reconnected!");
            Serial.print("IP: ");
            Serial.println(WiFi.localIP());
            wifiState = WiFiState::CONNECTED;
            reconnectAttemptCount = 0;
        } else if (millis() - lastReconnectAttemptMs > WIFI_CONNECT_TIMEOUT_MS) {
            reconnectAttemptCount++;
            Serial.printf("WiFi reconnect timed out (next backoff %ums)\n",
                           getReconnectBackoffMs());
            wifiState = WiFiState::DISCONNECTED;
            lastReconnectAttemptMs = millis();
        }
        break;
    }
}

uint32_t NetworkManager::getReconnectBackoffMs() const {
    uint32_t backoff = WIFI_RECONNECT_BASE_MS;
    for (uint8_t i = 0; i < reconnectAttemptCount && backoff < WIFI_RECONNECT_MAX_MS; i++) {
        backoff *= 2;
    }
    return (backoff < WIFI_RECONNECT_MAX_MS) ? backoff : WIFI_RECONNECT_MAX_MS;
}

const String& NetworkManager::getDeviceId() const {
    return deviceId;
}

const String& NetworkManager::getApiEndpoint() const {
    return apiEndpoint;
}

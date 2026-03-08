#pragma once

#include <WiFi.h>
#include <WiFiClientSecure.h>

struct DeviceConfig;

class NetworkManager {
private:
    String ssid;
    String password;
    String deviceId;
    String apiEndpoint;
    WiFiClientSecure wifiClient;

    enum class WiFiState { DISCONNECTED, CONNECTING, CONNECTED };
    WiFiState wifiState = WiFiState::DISCONNECTED;
    uint32_t lastReconnectAttemptMs = 0;
    uint8_t reconnectAttemptCount = 0;

    static constexpr uint32_t WIFI_RECONNECT_BASE_MS = 1000;
    static constexpr uint32_t WIFI_RECONNECT_MAX_MS  = 60000;
    static constexpr uint32_t WIFI_CONNECT_TIMEOUT_MS = 15000;
    static constexpr uint8_t  WIFI_MAX_BOOT_ATTEMPTS = 30;
    static constexpr uint32_t WIFI_MODE_SETTLE_MS = 100;

    uint32_t getReconnectBackoffMs() const;

public:
    NetworkManager();
    void applyConfig(const DeviceConfig& config);
    bool connectWiFi();
    void disconnect();
    bool isConnected();
    WiFiClientSecure& getClient();
    void checkConnection();
    const String& getDeviceId() const;
    const String& getApiEndpoint() const;
};

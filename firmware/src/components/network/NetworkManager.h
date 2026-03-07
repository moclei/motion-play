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
    bool connected = false;

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
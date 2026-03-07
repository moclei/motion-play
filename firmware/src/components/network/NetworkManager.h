#pragma once

#include <WiFi.h>
#include <WiFiClientSecure.h>

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
    bool loadConfig();
    bool connectWiFi();
    void disconnect();
    bool isConnected();
    WiFiClientSecure& getClient();
    void checkConnection();
    const String& getDeviceId() const;
    const String& getApiEndpoint() const;
};
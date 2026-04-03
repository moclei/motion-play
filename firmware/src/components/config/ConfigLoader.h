#pragma once

#include <Arduino.h>

struct DeviceConfig {
    // WiFi
    String wifiSsid;
    String wifiPassword;

    // Device identity
    String deviceId;
    String apiEndpoint;

    // MQTT
    String mqttBroker;
    int mqttPort = 0;
    String mqttClientId;
};

class ConfigLoader {
public:
    bool load();
    const DeviceConfig& getConfig() const { return config_; }

private:
    DeviceConfig config_;

    bool mountFilesystem();
    bool parseConfigFile();
};

#pragma once

#include <PubSubClient.h>
#include <ArduinoJson.h>

class NetworkManager;
struct DeviceConfig;

class MQTTManager
{
private:
    PubSubClient mqttClient;
    NetworkManager *networkManager;
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

    // Non-blocking reconnection state
    uint32_t lastReconnectAttemptMs = 0;
    uint8_t reconnectAttemptCount = 0;

    static constexpr uint32_t MQTT_RECONNECT_BASE_MS = 1000;
    static constexpr uint32_t MQTT_RECONNECT_MAX_MS  = 60000;

    bool loadCertificates();
    uint32_t getReconnectBackoffMs() const;

public:
    MQTTManager(NetworkManager *netManager);
    bool applyConfig(const DeviceConfig& config);
    bool connect();
    void disconnect();
    bool isConnected();
    void loop();
    const String &getDeviceId() const { return deviceId; }
    bool publishStatus(const char *status);
    bool publishData(const JsonDocument &data);
    bool publishDataStreaming(const JsonDocument &data);
    void setCallback(std::function<void(char *, byte *, unsigned int)> callback);
};

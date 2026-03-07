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

    bool loadCertificates();

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
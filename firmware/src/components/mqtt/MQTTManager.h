#ifndef MQTT_MANAGER_H
#define MQTT_MANAGER_H

#include <PubSubClient.h>
#include <ArduinoJson.h>
#include <SPIFFS.h>
#include "NetworkManager.h"

class MQTTManager {
private:
    PubSubClient mqttClient;
    NetworkManager* networkManager;
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
    static void messageCallback(char* topic, byte* payload, unsigned int length);

public:
    MQTTManager(NetworkManager* netManager);
    bool loadConfig();
    bool connect();
    void disconnect();
    bool isConnected();
    void loop();
    bool publishStatus(const char* status);
    bool publishData(const JsonDocument& data);
    void setCallback(std::function<void(char*, byte*, unsigned int)> callback);
};

#endif
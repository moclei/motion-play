#include "MQTTManager.h"

MQTTManager::MQTTManager(NetworkManager *netManager) : networkManager(netManager)
{
    mqttClient.setClient(networkManager->getClient());
}

bool MQTTManager::loadConfig()
{
    File configFile = LittleFS.open("/config.json", "r");
    if (!configFile)
        return false;

    DynamicJsonDocument doc(1024);
    DeserializationError error = deserializeJson(doc, configFile);
    configFile.close();

    if (error)
        return false;

    broker = doc["mqtt"]["broker"].as<String>();
    port = doc["mqtt"]["port"];
    clientId = doc["mqtt"]["client_id"].as<String>();
    deviceId = doc["device_id"].as<String>();

    // Set up topics
    statusTopic = "motionplay/" + deviceId + "/status";
    dataTopic = "motionplay/" + deviceId + "/data";
    commandTopic = "motionplay/" + deviceId + "/commands";

    // Load certificates
    if (!loadCertificates())
    {
        Serial.println("Failed to load certificates");
        return false;
    }

    mqttClient.setServer(broker.c_str(), port);
    mqttClient.setCallback(messageCallback);

    // Set buffer size for large data payloads (default is 256 bytes)
    // AWS IoT Core max is 128KB, we set to 32KB for Live Debug batch data
    mqttClient.setBufferSize(32768);
    Serial.println("MQTT buffer size set to 32KB");

    return true;
}

bool MQTTManager::loadCertificates()
{
    // Load CA certificate
    File ca = LittleFS.open("/certs/root-ca.pem", "r");
    if (!ca)
    {
        Serial.println("Failed to open CA certificate");
        return false;
    }
    caCert = ca.readString();
    ca.close();

    // Load client certificate
    File cert = LittleFS.open("/certs/device-cert.pem", "r");
    if (!cert)
    {
        Serial.println("Failed to open device certificate");
        return false;
    }
    clientCert = cert.readString();
    cert.close();

    // Load private key
    File key = LittleFS.open("/certs/private-key.pem", "r");
    if (!key)
    {
        Serial.println("Failed to open private key");
        return false;
    }
    privateKey = key.readString();
    key.close();

    // Configure secure client
    networkManager->getClient().setCACert(caCert.c_str());
    networkManager->getClient().setCertificate(clientCert.c_str());
    networkManager->getClient().setPrivateKey(privateKey.c_str());

    return true;
}

bool MQTTManager::connect()
{
    if (!networkManager->isConnected())
    {
        Serial.println("No WiFi connection");
        return false;
    }

    Serial.print("Connecting to MQTT broker: ");
    Serial.println(broker);

    int attempts = 0;
    while (!mqttClient.connected() && attempts < 5)
    {
        if (mqttClient.connect(clientId.c_str()))
        {
            Serial.println("MQTT connected!");

            // Subscribe to command topic
            if (mqttClient.subscribe(commandTopic.c_str()))
            {
                Serial.print("Subscribed to: ");
                Serial.println(commandTopic);
            }

            // Publish initial status
            publishStatus("online");

            return true;
        }

        Serial.print("MQTT connection failed, rc=");
        Serial.print(mqttClient.state());
        Serial.println(" retrying in 5 seconds");

        attempts++;
        delay(5000);
    }

    return false;
}

void MQTTManager::disconnect()
{
    mqttClient.disconnect();
}

bool MQTTManager::isConnected()
{
    return mqttClient.connected();
}

void MQTTManager::loop()
{
    if (!mqttClient.connected())
    {
        connect();
    }
    mqttClient.loop();
}

bool MQTTManager::publishStatus(const char *status)
{
    DynamicJsonDocument doc(256);
    doc["device_id"] = deviceId;
    doc["status"] = status;
    doc["timestamp"] = millis();
    doc["wifi_rssi"] = WiFi.RSSI();
    doc["free_heap"] = ESP.getFreeHeap();
    doc["uptime_ms"] = millis();

    String payload;
    serializeJson(doc, payload);

    return mqttClient.publish(statusTopic.c_str(), payload.c_str());
}

bool MQTTManager::publishData(const JsonDocument &data)
{
    String payload;
    size_t payloadSize = serializeJson(data, payload);

    // Warn if payload approaches MQTT buffer limit
    if (payloadSize > 24576)
    {
        Serial.printf("WARNING: Large MQTT payload: %d bytes (buffer: 32KB)\n", payloadSize);
    }

    bool success = mqttClient.publish(dataTopic.c_str(), payload.c_str());

    if (!success)
    {
        Serial.println("ERROR: mqttClient.publish() failed!");
        Serial.printf("  MQTT state: %d, connected: %s, payload: %d bytes\n",
                      mqttClient.state(),
                      mqttClient.connected() ? "YES" : "NO",
                      payloadSize);
    }

    return success;
}

void MQTTManager::messageCallback(char *topic, byte *payload, unsigned int length)
{
    Serial.print("Message received on topic: ");
    Serial.println(topic);

    char message[length + 1];
    memcpy(message, payload, length);
    message[length] = '\0';

    Serial.print("Payload: ");
    Serial.println(message);

    // Parse command
    DynamicJsonDocument doc(256);
    DeserializationError error = deserializeJson(doc, message);

    if (!error)
    {
        String command = doc["command"].as<String>();
        Serial.print("Command: ");
        Serial.println(command);

        // Handle commands here
        if (command == "ping")
        {
            // Respond to ping
            Serial.println("Received ping command");
        }
    }
}

void MQTTManager::setCallback(std::function<void(char *, byte *, unsigned int)> callback)
{
    mqttClient.setCallback(callback);
}
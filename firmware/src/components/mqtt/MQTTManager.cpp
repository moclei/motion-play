#include "MQTTManager.h"
#include "../network/NetworkManager.h"
#include <LittleFS.h>
#include "constants.h"

MQTTManager::MQTTManager(NetworkManager *netManager) : networkManager(netManager)
{
    mqttClient.setClient(networkManager->getClient());
}

bool MQTTManager::loadConfig()
{
    File configFile = LittleFS.open(CONFIG_FILE_PATH, "r");
    if (!configFile)
        return false;

    DynamicJsonDocument doc(CONFIG_JSON_CAPACITY);
    DeserializationError error = deserializeJson(doc, configFile);
    configFile.close();

    if (error)
        return false;

    broker = doc["mqtt"]["broker"].as<String>();
    port = doc["mqtt"]["port"];
    clientId = doc["mqtt"]["client_id"].as<String>();
    deviceId = doc["device_id"].as<String>();

    // Set up topics
    statusTopic = String(MQTT_TOPIC_PREFIX) + deviceId + "/status";
    dataTopic = String(MQTT_TOPIC_PREFIX) + deviceId + "/data";
    commandTopic = String(MQTT_TOPIC_PREFIX) + deviceId + "/commands";

    // Load certificates
    if (!loadCertificates())
    {
        Serial.println("Failed to load certificates");
        return false;
    }

    mqttClient.setServer(broker.c_str(), port);
    mqttClient.setCallback(messageCallback);

    // Set buffer size for data payloads (default is 256 bytes)
    // 32KB covers the largest JSON batch (200 readings at ~80 bytes each).
    // Binary-packed captures (~56KB) use the streaming publishData overload instead.
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

bool MQTTManager::publishDataStreaming(const JsonDocument &data)
{
    size_t payloadSize = measureJson(data);

    Serial.printf("MQTT streaming publish: %d bytes\n", payloadSize);

    // Serialize into a PSRAM buffer first, then send in small chunks.
    // Writing the full ~56KB base64 string directly to the TLS socket in one
    // call can hang on ESP32 — chunked writes let the TCP stack flow-control.
    char *buf = (char *)ps_malloc(payloadSize + 1);
    if (!buf)
    {
        Serial.printf("ERROR: ps_malloc(%d) failed for streaming publish\n", payloadSize + 1);
        return false;
    }

    size_t serialized = serializeJson(data, buf, payloadSize + 1);
    if (serialized != payloadSize)
    {
        Serial.printf("WARNING: measureJson=%d but serializeJson=%d\n", payloadSize, serialized);
        payloadSize = serialized;
    }

    if (!mqttClient.beginPublish(dataTopic.c_str(), payloadSize, false))
    {
        Serial.printf("ERROR: beginPublish failed (payload: %d bytes, connected: %s)\n",
                      payloadSize, mqttClient.connected() ? "YES" : "NO");
        free(buf);
        return false;
    }

    // Send in 4KB chunks
    static const size_t CHUNK_SIZE = 4096;
    size_t sent = 0;
    bool writeOk = true;

    while (sent < payloadSize)
    {
        size_t chunkLen = payloadSize - sent;
        if (chunkLen > CHUNK_SIZE)
            chunkLen = CHUNK_SIZE;

        size_t written = mqttClient.write((const uint8_t *)(buf + sent), chunkLen);
        if (written != chunkLen)
        {
            Serial.printf("ERROR: chunk write failed at offset %d (wanted %d, wrote %d)\n",
                          sent, chunkLen, written);
            writeOk = false;
            break;
        }
        sent += written;
    }

    free(buf);

    if (!writeOk)
    {
        Serial.println("ERROR: streaming publish aborted due to write failure");
        mqttClient.endPublish();
        return false;
    }

    bool success = mqttClient.endPublish();
    if (!success)
    {
        Serial.printf("ERROR: endPublish failed after sending %d bytes\n", sent);
    }
    else
    {
        Serial.printf("MQTT streaming publish complete: %d bytes in %d chunks\n",
                      payloadSize, (payloadSize + CHUNK_SIZE - 1) / CHUNK_SIZE);
    }

    return success;
}

void MQTTManager::messageCallback(char *topic, byte *payload, unsigned int length)
{
    Serial.print("Message received on topic: ");
    Serial.println(topic);

    if (length > MQTT_MAX_INCOMING_MSG) {
        Serial.printf("MQTT message too large (%u bytes, max %u) — dropped\n",
                      length, (unsigned)MQTT_MAX_INCOMING_MSG);
        return;
    }

    char message[MQTT_MAX_INCOMING_MSG + 1];
    memcpy(message, payload, length);
    message[length] = '\0';

    Serial.print("Payload: ");
    Serial.println(message);

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
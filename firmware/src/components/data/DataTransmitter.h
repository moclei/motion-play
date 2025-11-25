#ifndef DATA_TRANSMITTER_H
#define DATA_TRANSMITTER_H

#include <Arduino.h>
#include <ArduinoJson.h>
#include "../mqtt/MQTTManager.h"
#include "../session/SessionManager.h"
#include "../sensor/SensorConfiguration.h"

class DataTransmitter
{
private:
    MQTTManager *mqttManager;
    static const size_t BATCH_SIZE = 25; // Send 25 samples (100 sensor readings) at a time

public:
    DataTransmitter(MQTTManager *mqtt);
    bool transmitSession(SessionManager &session, const SensorConfiguration *config = nullptr);
    bool transmitBatch(const String &sessionId,
                       const String &deviceId,
                       unsigned long startTime,
                       unsigned long duration,
                       std::vector<SensorReading> &readings,
                       size_t offset,
                       size_t count,
                       const std::vector<SensorMetadata> *sensorMetadata,
                       const SensorConfiguration *config = nullptr);
};

#endif
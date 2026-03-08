#pragma once

#include <ArduinoJson.h>

class NetworkManager;
struct SensorConfiguration;
struct DetectorConfig;

class CloudConfig
{
public:
    explicit CloudConfig(NetworkManager &networkManager);

    // Fetch sensor config from cloud API and apply to the given references.
    // Returns true if config was successfully fetched and parsed.
    bool fetch(SensorConfiguration &config, bool &useMLDetection,
               DetectorConfig &detectorConfig, bool &serialStudioEnabled);

    // Shared helper: parse a sensor_config JSON object into config structs.
    // Used by both fetch() and CommandHandler::handleConfigureSensors().
    // Does NOT apply side effects (serialStudioOutput, directionDetector) —
    // callers are responsible for those.
    static void applySensorConfig(JsonObject sensorConfig,
                                  SensorConfiguration &config,
                                  bool &useMLDetection,
                                  DetectorConfig &detectorConfig,
                                  bool &serialStudioEnabled);

private:
    NetworkManager &networkManager_;
};

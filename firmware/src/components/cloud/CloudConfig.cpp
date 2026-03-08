#include "CloudConfig.h"
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include "../network/NetworkManager.h"
#include "../sensor/SensorConfiguration.h"
#include "detection_types.h"

CloudConfig::CloudConfig(NetworkManager &networkManager)
    : networkManager_(networkManager) {}

bool CloudConfig::fetch(SensorConfiguration &config, bool &useMLDetection,
                        DetectorConfig &detectorConfig, bool &serialStudioEnabled)
{
    Serial.println("\n=== Fetching Config from Cloud ===");

    String deviceId = networkManager_.getDeviceId();
    String apiEndpoint = networkManager_.getApiEndpoint();

    if (apiEndpoint.isEmpty())
    {
        Serial.println("WARNING: No API endpoint configured, using defaults");
        return false;
    }

    String url = apiEndpoint + "/device/" + deviceId + "/config";
    Serial.printf("Fetching config from: %s\n", url.c_str());

    HTTPClient http;
    http.begin(url);
    http.setTimeout(5000);

    int httpCode = http.GET();

    if (httpCode != HTTP_CODE_OK)
    {
        Serial.printf("HTTP GET failed, error: %s (code: %d)\n",
                      http.errorToString(httpCode).c_str(), httpCode);
        http.end();
        return false;
    }

    String payload = http.getString();
    Serial.println("Config received:");
    Serial.println(payload);

    DynamicJsonDocument doc(2048);
    DeserializationError error = deserializeJson(doc, payload);

    if (error)
    {
        Serial.print("JSON parse error: ");
        Serial.println(error.c_str());
        http.end();
        return false;
    }

    if (!doc.containsKey("sensor_config"))
    {
        Serial.println("WARNING: No sensor_config in response");
        http.end();
        return false;
    }

    JsonObject sensorConfig = doc["sensor_config"];
    applySensorConfig(sensorConfig, config, useMLDetection, detectorConfig, serialStudioEnabled);

    Serial.println("\nConfig loaded from cloud:");
    Serial.printf("  Sensor Mode: %s\n",
                  config.sensor_mode == SensorMode::INTERRUPT_MODE ? "INTERRUPT" : "POLLING");
    Serial.printf("  Sample Rate: %d Hz\n", config.sample_rate_hz);
    Serial.printf("  LED Current: %s\n", config.led_current.c_str());
    Serial.printf("  Integration Time: %s\n", config.integration_time.c_str());
    Serial.printf("  Multi-Pulse: %s pulses\n", config.multi_pulse.c_str());
    Serial.printf("  High Resolution: %s\n", config.high_resolution ? "enabled" : "disabled");
    Serial.printf("  Read Ambient: %s\n", config.read_ambient ? "enabled" : "disabled");
    Serial.printf("  I2C Clock: %d kHz\n", config.i2c_clock_khz);
    if (config.sensor_mode == SensorMode::INTERRUPT_MODE)
    {
        Serial.printf("  INT Threshold Margin: %d\n", config.interrupt_threshold_margin);
        Serial.printf("  INT Hysteresis: %d\n", config.interrupt_hysteresis);
        Serial.printf("  INT Integration Time: %dT\n", config.interrupt_integration_time);
        Serial.printf("  INT Multi-Pulse: %d\n", config.interrupt_multi_pulse);
    }
    Serial.printf("  Detection Mode: %s\n", useMLDetection ? "ML" : "heuristic");
    Serial.printf("  Detection Config: peak=%.1fx, rise=%d, wave=%dms, smooth=%d\n",
                  detectorConfig.peakMultiplier, detectorConfig.minRise,
                  detectorConfig.minWaveDurationMs, detectorConfig.smoothingWindow);

    http.end();
    return true;
}

void CloudConfig::applySensorConfig(JsonObject config,
                                    SensorConfiguration &out,
                                    bool &useMLDetection,
                                    DetectorConfig &detectorConfig,
                                    bool &serialStudioEnabled)
{
    // Sample rate (two key names for backwards compatibility)
    if (config.containsKey("sample_rate_hz"))
        out.sample_rate_hz = config["sample_rate_hz"];
    else if (config.containsKey("sample_rate"))
        out.sample_rate_hz = config["sample_rate"];

    // Core sensor settings
    out.led_current = config["led_current"] | "200mA";
    out.integration_time = config["integration_time"] | "1T";
    out.high_resolution = config["high_resolution"] | true;
    out.read_ambient = config["read_ambient"] | true;

    if (config.containsKey("i2c_clock_khz"))
        out.i2c_clock_khz = config["i2c_clock_khz"];

    if (config.containsKey("multi_pulse"))
        out.multi_pulse = config["multi_pulse"].as<String>();
    else
        out.multi_pulse = "1";

    // Physical geometry for transit speed estimation
    if (config.containsKey("ball_diameter_mm"))
        out.ball_diameter_mm = config["ball_diameter_mm"];
    if (config.containsKey("hoop_inner_diameter_mm"))
        out.hoop_inner_diameter_mm = config["hoop_inner_diameter_mm"];

    // Sensor mode (polling vs interrupt)
    if (config.containsKey("sensor_mode"))
    {
        String modeStr = config["sensor_mode"].as<String>();
        out.sensor_mode = (modeStr == "interrupt")
                              ? SensorMode::INTERRUPT_MODE
                              : SensorMode::POLLING_MODE;
    }

    // Interrupt mode settings
    if (config.containsKey("interrupt_threshold_margin"))
        out.interrupt_threshold_margin = config["interrupt_threshold_margin"];
    if (config.containsKey("interrupt_hysteresis"))
        out.interrupt_hysteresis = config["interrupt_hysteresis"];
    if (config.containsKey("interrupt_integration_time"))
        out.interrupt_integration_time = config["interrupt_integration_time"];
    if (config.containsKey("interrupt_multi_pulse"))
        out.interrupt_multi_pulse = config["interrupt_multi_pulse"];
    if (config.containsKey("interrupt_persistence"))
        out.interrupt_persistence = config["interrupt_persistence"];
    if (config.containsKey("interrupt_smart_persistence"))
        out.interrupt_smart_persistence = config["interrupt_smart_persistence"];
    if (config.containsKey("interrupt_mode"))
        out.interrupt_mode = config["interrupt_mode"].as<String>();

    // Detection mode
    if (config.containsKey("detection_mode"))
    {
        String detMode = config["detection_mode"].as<String>();
        useMLDetection = (detMode == "ml");
    }

    // Serial Studio toggle
    if (config.containsKey("serial_studio_enabled"))
        serialStudioEnabled = config["serial_studio_enabled"].as<bool>();

    // Detection algorithm parameters
    if (config.containsKey("peak_multiplier"))
        detectorConfig.peakMultiplier = config["peak_multiplier"].as<float>();
    if (config.containsKey("min_rise"))
        detectorConfig.minRise = config["min_rise"];
    if (config.containsKey("min_wave_duration_ms"))
        detectorConfig.minWaveDurationMs = config["min_wave_duration_ms"];
    if (config.containsKey("smoothing_window"))
        detectorConfig.smoothingWindow = config["smoothing_window"];
}

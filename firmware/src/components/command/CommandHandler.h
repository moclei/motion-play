#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>

class MQTTManager;
class DisplayManager;
class SensorManager;
class SessionManager;
class DataTransmitter;
class BinarySerializer;
class DirectionDetector;
class MLDetector;
class LEDController;
class InterruptManager;
class SerialStudioOutput;
class DetectionController;
struct SensorConfiguration;
struct DetectorConfig;
struct DetectionResult;

enum class DeviceMode
{
    IDLE,
    DEBUG,
    PLAY,
    LIVE_DEBUG
};

class CommandHandler
{
public:
    CommandHandler(MQTTManager *mqttManager,
                   DisplayManager &display,
                   SensorManager &sensorManager,
                   SessionManager &sessionManager,
                   DataTransmitter *dataTransmitter,
                   BinarySerializer *binarySerializer,
                   DirectionDetector &directionDetector,
                   MLDetector &mlDetector,
                   LEDController &ledController,
                   InterruptManager &interruptManager,
                   SerialStudioOutput &serialStudioOutput,
                   DetectionController &detectionController,
                   SensorConfiguration &currentConfig,
                   DeviceMode &currentMode,
                   bool &useMLDetection,
                   DetectorConfig &detectorConfig,
                   bool &playModeActive,
                   bool &liveDebugActive,
                   unsigned long &lastDetectionTime);

    // Returns true if the command was handled, false to fall through to legacy handler
    bool handleCommand(const String &command, JsonDocument *doc = nullptr);

private:
    void handlePing();
    void handleReboot();
    void handleSetDetectionMode(JsonDocument *doc);
    void handleSetMode(JsonDocument *doc);
    void handleConfigureSensors(JsonDocument *doc);
    void handleStartCollection();
    void handleStopCollection();
    void handleCaptureMissedEvent();
    void configurePlayDetection();
    void configureLiveDebugDetection();
    void performLiveDebugCapture(const DetectionResult &result);
    void resumeAfterLiveDebugCapture();

    static constexpr unsigned long MISSED_EVENT_WINDOW_MS = 3000;
    static constexpr size_t PLAY_BUFFER_CAP = 500;
    static constexpr size_t LIVE_DEBUG_BUFFER_CAP = 18000;
    static constexpr unsigned long DETECTION_WINDOW_MS = 500;
    static constexpr unsigned long POST_DETECTION_DELAY_MS = 250;

    // Dependencies (all passed by reference/pointer from main.cpp)
    MQTTManager *mqttManager_;
    DisplayManager &display_;
    SensorManager &sensorManager_;
    SessionManager &sessionManager_;
    DataTransmitter *dataTransmitter_;
    BinarySerializer *binarySerializer_;
    DirectionDetector &directionDetector_;
    MLDetector &mlDetector_;
    LEDController &ledController_;
    InterruptManager &interruptManager_;
    SerialStudioOutput &serialStudioOutput_;
    DetectionController &detectionController_;
    SensorConfiguration &currentConfig_;

    // Shared mutable state (references to main.cpp globals until full extraction)
    DeviceMode &currentMode_;
    bool &useMLDetection_;
    DetectorConfig &detectorConfig_;
    bool &playModeActive_;
    bool &liveDebugActive_;
    unsigned long &lastDetectionTime_;
};

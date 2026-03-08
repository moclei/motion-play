#pragma once

#include <Arduino.h>

class InterruptManager;
class SessionManager;
class SensorManager;
class SerialStudioOutput;
class DisplayManager;
class DataTransmitter;
class MQTTManager;
class DetectionController;
struct SensorConfiguration;
enum class DeviceMode;

class CollectionController
{
public:
    CollectionController(
        InterruptManager &interruptManager,
        SessionManager &sessionManager,
        SensorManager &sensorManager,
        SerialStudioOutput &serialStudioOutput,
        DisplayManager &display,
        DataTransmitter *dataTransmitter,
        MQTTManager *mqttManager,
        DetectionController &detectionController,
        SensorConfiguration &currentConfig,
        DeviceMode &currentMode,
        bool &playModeActive,
        bool &liveDebugActive);

    void update();

private:
    void drainInterruptEvents();
    void handleInterruptTimeout();
    void handleDebugTimeout();

    InterruptManager &interruptManager_;
    SessionManager &sessionManager_;
    SensorManager &sensorManager_;
    SerialStudioOutput &serialStudioOutput_;
    DisplayManager &display_;
    DataTransmitter *dataTransmitter_;
    MQTTManager *mqttManager_;
    DetectionController &detectionController_;
    SensorConfiguration &currentConfig_;
    DeviceMode &currentMode_;
    bool &playModeActive_;
    bool &liveDebugActive_;

    unsigned long lastInterruptDisplayUpdate_ = 0;
    unsigned long lastSampleDisplayUpdate_ = 0;

    static constexpr unsigned long MAX_SESSION_DURATION_MS = 30000;
    static constexpr unsigned long INTERRUPT_DISPLAY_INTERVAL_MS = 500;
    static constexpr unsigned long SAMPLE_DISPLAY_INTERVAL_MS = 1000;
};

#pragma once

#include <Arduino.h>
#include <functional>
#include "detection_types.h"

class LEDController;
class DisplayManager;
class SerialStudioOutput;
class SessionManager;

class DetectionController
{
public:
    struct Config
    {
        size_t bufferOverflowCap = 500;
        bool alwaysResetOnOverflow = false;
        const char *modeLabel = "PLAY";
    };

    using OnDetectionFn = std::function<void(const DetectionResult &)>;
    using OnResetFn = std::function<void()>;

    DetectionController(IDetector &heuristicDetector,
                        IDetector &mlDetector,
                        LEDController &ledController,
                        DisplayManager &display,
                        SerialStudioOutput &serialStudio,
                        SessionManager &sessionManager,
                        bool &useMLDetection,
                        unsigned long &lastDetectionTime,
                        unsigned long cooldownMs);

    void configure(const Config &config);
    void setOnDetection(OnDetectionFn fn);
    void setOnReset(OnResetFn fn);

    void update();
    void reset();

private:
    IDetector &getActiveDetector();
    void showDetectionFeedback(const DetectionResult &result);

    IDetector &heuristicDetector_;
    IDetector &mlDetector_;
    LEDController &ledController_;
    DisplayManager &display_;
    SerialStudioOutput &serialStudio_;
    SessionManager &sessionManager_;
    bool &useMLDetection_;
    unsigned long &lastDetectionTime_;

    Config config_;
    unsigned long cooldownMs_;
    OnDetectionFn onDetectionCb_;
    OnResetFn onResetCb_;

    size_t lastProcessedIndex_ = 0;
    unsigned long lastDebugLog_ = 0;
    static constexpr unsigned long DEBUG_LOG_INTERVAL_MS = 2000;
};

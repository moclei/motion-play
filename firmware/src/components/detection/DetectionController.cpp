#include "DetectionController.h"
#include "../led/LEDController.h"
#include "../display/DisplayManager.h"
#include "../serialstudio/SerialStudioOutput.h"
#include "../session/SessionManager.h"
#include "debug_log.h"

DetectionController::DetectionController(
    IDetector &heuristicDetector,
    IDetector &mlDetector,
    LEDController &ledController,
    DisplayManager &display,
    SerialStudioOutput &serialStudio,
    SessionManager &sessionManager,
    bool &useMLDetection,
    unsigned long &lastDetectionTime,
    unsigned long cooldownMs)
    : heuristicDetector_(heuristicDetector),
      mlDetector_(mlDetector),
      ledController_(ledController),
      display_(display),
      serialStudio_(serialStudio),
      sessionManager_(sessionManager),
      useMLDetection_(useMLDetection),
      lastDetectionTime_(lastDetectionTime),
      cooldownMs_(cooldownMs)
{
}

void DetectionController::configure(const Config &config)
{
    config_ = config;
}

void DetectionController::setOnDetection(OnDetectionFn fn)
{
    onDetectionCb_ = std::move(fn);
}

void DetectionController::setOnReset(OnResetFn fn)
{
    onResetCb_ = std::move(fn);
}

IDetector &DetectionController::getActiveDetector()
{
    return useMLDetection_ ? static_cast<IDetector &>(mlDetector_)
                           : static_cast<IDetector &>(heuristicDetector_);
}

void DetectionController::reset()
{
    lastProcessedIndex_ = 0;
    lastDebugLog_ = 0;
}

void DetectionController::showDetectionFeedback(const DetectionResult &result)
{
    ledController_.showDirection(result.direction, 3000);

    if (result.direction == Direction::A_TO_B)
        display_.showMessage("A -> B", TFT_BLUE);
    else if (result.direction == Direction::B_TO_A)
        display_.showMessage("B -> A", TFT_ORANGE);
    else
        display_.showMessage("Unknown", TFT_RED);
}

void DetectionController::update()
{
    ledController_.update();

    if (debugPrintEnabled() && millis() - lastDebugLog_ > DEBUG_LOG_INTERVAL_MS)
    {
        lastDebugLog_ = millis();
        IDetector &detector = getActiveDetector();
        Serial.printf("[%s] Buffer: %d samples, Detector(%s): %s\n",
                      config_.modeLabel,
                      sessionManager_.getDataCount(),
                      useMLDetection_ ? "ML" : "heuristic",
                      detector.isReady() ? "READY" : "establishing baseline...");
    }

    unsigned long now = millis();
    bool inCooldown = (lastDetectionTime_ > 0) && (now - lastDetectionTime_ < cooldownMs_);

    if (!inCooldown)
    {
        auto &buffer = sessionManager_.getDataBuffer();
        size_t bufferSize = buffer.size();

        IDetector &detector = getActiveDetector();

        for (size_t i = lastProcessedIndex_; i < bufferSize; i++)
        {
            detector.addReading(buffer[i]);
        }
        detector.flushReading();
        lastProcessedIndex_ = bufferSize;

        if (detector.hasDetection())
        {
            DetectionResult result = detector.getResult();
            serialStudio_.cacheDetection(result);

            DEBUG_LOG("[%s] DETECTION [%s]: %s (confidence: %.2f)\n",
                      config_.modeLabel,
                      useMLDetection_ ? "ML" : "heuristic",
                      directionToString(result.direction),
                      result.confidence);

            showDetectionFeedback(result);

            if (onDetectionCb_)
                onDetectionCb_(result);

            lastDetectionTime_ = millis();
            detector.reset();
            lastProcessedIndex_ = 0;
            buffer.clear();
            serialStudio_.resetIndex();

            if (onResetCb_)
                onResetCb_();

            DEBUG_LOG("[%s] Detection complete, buffer cleared for next event\n",
                      config_.modeLabel);
        }

        if (bufferSize > config_.bufferOverflowCap)
        {
            DEBUG_LOG("[%s] Buffer overflow prevention: clearing %d samples\n",
                      config_.modeLabel, bufferSize);
            if (config_.alwaysResetOnOverflow || !useMLDetection_)
            {
                detector.reset();
            }
            lastProcessedIndex_ = 0;
            buffer.clear();
            serialStudio_.resetIndex();
        }
    }
    else if (!ledController_.isAnimating() && getActiveDetector().isReady())
    {
        ledController_.showReady();
    }
}

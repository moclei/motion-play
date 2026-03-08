#include "CollectionController.h"
#include "../interrupt/InterruptManager.h"
#include "../session/SessionManager.h"
#include "../sensor/SensorManager.h"
#include "../sensor/SensorConfiguration.h"
#include "../serialstudio/SerialStudioOutput.h"
#include "../display/DisplayManager.h"
#include "../data/DataTransmitter.h"
#include "../mqtt/MQTTManager.h"
#include "../detection/DetectionController.h"
#include "../command/CommandHandler.h"
#include "../diagnostics/MemoryMonitor.h"
#include "debug_log.h"

CollectionController::CollectionController(
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
    bool &liveDebugActive)
    : interruptManager_(interruptManager),
      sessionManager_(sessionManager),
      sensorManager_(sensorManager),
      serialStudioOutput_(serialStudioOutput),
      display_(display),
      dataTransmitter_(dataTransmitter),
      mqttManager_(mqttManager),
      detectionController_(detectionController),
      currentConfig_(currentConfig),
      currentMode_(currentMode),
      playModeActive_(playModeActive),
      liveDebugActive_(liveDebugActive)
{
}

void CollectionController::update()
{
    bool isInterruptSession = (sessionManager_.getSessionType() == SessionType::INTERRUPT_BASED);

    if (isInterruptSession)
    {
        drainInterruptEvents();

        if (millis() - lastInterruptDisplayUpdate_ > INTERRUPT_DISPLAY_INTERVAL_MS)
        {
            lastInterruptDisplayUpdate_ = millis();
            size_t eventCount = sessionManager_.getInterruptEventCount();
            Serial.printf("[INT] Events: %d\n", eventCount);
        }

        if (sessionManager_.getDuration() >= MAX_SESSION_DURATION_MS)
        {
            handleInterruptTimeout();
            return;
        }
    }
    else
    {
        sessionManager_.processQueue();
        serialStudioOutput_.update();
    }

    if ((playModeActive_ && currentMode_ == DeviceMode::PLAY) ||
        (liveDebugActive_ && currentMode_ == DeviceMode::LIVE_DEBUG))
    {
        detectionController_.update();
    }
    else
    {
        if (sessionManager_.getDuration() >= MAX_SESSION_DURATION_MS)
        {
            handleDebugTimeout();
            return;
        }

        if (millis() - lastSampleDisplayUpdate_ > SAMPLE_DISPLAY_INTERVAL_MS)
        {
            lastSampleDisplayUpdate_ = millis();
            int sampleCount = sessionManager_.getDataCount();
            display_.updateSampleCount(sampleCount);

            if (debugPrintEnabled())
            {
                Serial.printf("Samples: %d | ", sampleCount);
                MemoryMonitor::printCompactStatus();
            }

            if (!MemoryMonitor::isMemoryHealthy())
            {
                DEBUG_LOG("WARNING: Memory getting low during collection!\n");
            }
        }
    }
}

void CollectionController::drainInterruptEvents()
{
    while (interruptManager_.hasEvents())
    {
        InterruptEvent evt;
        if (interruptManager_.getNextEvent(evt))
        {
            sessionManager_.addInterruptEvent(evt);
        }
    }
}

void CollectionController::handleInterruptTimeout()
{
    Serial.println("WARNING: Maximum interrupt session duration reached (30s), auto-stopping...");
    display_.showMessage("Max duration!", TFT_ORANGE);
    delay(1000);

    interruptManager_.stopMonitoring();
    sessionManager_.stopSession();
    display_.setDisplayState(DISPLAY_UPLOADING);

    UploadContext ctx;
    ctx.successStatus = "upload_complete_auto_stopped";
    ctx.displayDelayMs = 2000;

    dataTransmitter_->beginTransmission(sessionManager_, &currentConfig_, ctx);
}

void CollectionController::handleDebugTimeout()
{
    Serial.println("WARNING: Maximum session duration reached (30s), auto-stopping...");
    display_.showMessage("Max duration reached!", TFT_ORANGE);
    delay(1000);

    sensorManager_.stopCollection();
    sessionManager_.stopSession();
    display_.setDisplayState(DISPLAY_UPLOADING);

    {
        uint8_t activeCnt = 0;
        for (const auto &m : sessionManager_.getSensorMetadata())
        {
            if (m.active)
                activeCnt++;
        }
        sessionManager_.finalizeSessionSummary(&currentConfig_, activeCnt);
        dataTransmitter_->setSessionSummary(&sessionManager_.getSessionSummary());
    }

    UploadContext ctx;
    ctx.sendSummary = true;
    ctx.successStatus = "upload_complete_auto_stopped";
    ctx.restartOnFailure = true;
    ctx.displayDelayMs = 2000;

    dataTransmitter_->beginTransmission(sessionManager_, &currentConfig_, ctx);
}

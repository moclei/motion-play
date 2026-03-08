#include "CommandHandler.h"
#include "../mqtt/MQTTManager.h"
#include "../display/DisplayManager.h"
#include "../detection/DirectionDetector.h"
#include "../detection/MLDetector.h"
#include "../detection/DetectionController.h"
#include "../led/LEDController.h"
#include "../interrupt/InterruptManager.h"
#include "../serialstudio/SerialStudioOutput.h"
#include "../calibration/CalibrationManager.h"
#include "../calibration/CalibrationData.h"
#include "../session/SessionManager.h"
#include "../sensor/SensorConfiguration.h"
#include "../sensor/SensorManager.h"
#include "../data/DataTransmitter.h"
#include "../data/BinarySerializer.h"
#include "../cloud/CloudConfig.h"
#include "../diagnostics/MemoryMonitor.h"
#include "debug_log.h"

CommandHandler::CommandHandler(
    MQTTManager *mqttManager,
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
    unsigned long &lastDetectionTime)
    : mqttManager_(mqttManager),
      display_(display),
      sensorManager_(sensorManager),
      sessionManager_(sessionManager),
      dataTransmitter_(dataTransmitter),
      binarySerializer_(binarySerializer),
      directionDetector_(directionDetector),
      mlDetector_(mlDetector),
      ledController_(ledController),
      interruptManager_(interruptManager),
      serialStudioOutput_(serialStudioOutput),
      detectionController_(detectionController),
      currentConfig_(currentConfig),
      currentMode_(currentMode),
      useMLDetection_(useMLDetection),
      detectorConfig_(detectorConfig),
      playModeActive_(playModeActive),
      liveDebugActive_(liveDebugActive),
      lastDetectionTime_(lastDetectionTime)
{
}

bool CommandHandler::handleCommand(const String &command, JsonDocument *doc)
{
    if (command == "ping")
    {
        handlePing();
        return true;
    }
    else if (command == "start_collection")
    {
        handleStartCollection();
        return true;
    }
    else if (command == "stop_collection")
    {
        handleStopCollection();
        return true;
    }
    else if (command == "set_detection_mode")
    {
        handleSetDetectionMode(doc);
        return true;
    }
    else if (command == "capture_missed_event")
    {
        handleCaptureMissedEvent();
        return true;
    }
    else if (command == "configure_sensors")
    {
        handleConfigureSensors(doc);
        return true;
    }
    else if (command == "set_mode")
    {
        handleSetMode(doc);
        return true;
    }
    else if (command == "reboot")
    {
        handleReboot();
        return true;
    }
    return false;
}

void CommandHandler::handlePing()
{
    mqttManager_->publishStatus("pong");
    display_.showMessage("Ping received", TFT_YELLOW);
    delay(1000);
    display_.setDisplayState(DISPLAY_IDLE);
}

void CommandHandler::handleReboot()
{
    display_.showMessage("Rebooting...", TFT_YELLOW);
    delay(1000);
    ESP.restart();
}

void CommandHandler::handleSetDetectionMode(JsonDocument *doc)
{
    if (doc && doc->containsKey("mode"))
    {
        String mode = (*doc)["mode"].as<String>();
        if (mode == "ml")
        {
            if (!mlDetector_.isReady() && !useMLDetection_)
            {
                Serial.println("Initializing ML detector on demand...");
                if (mlDetector_.init())
                {
                    useMLDetection_ = true;
                    Serial.println("Switched to ML detection");
                    mqttManager_->publishStatus("detection_mode_ml");
                }
                else
                {
                    Serial.println("ML detector init failed, staying on heuristic");
                    mqttManager_->publishStatus("detection_mode_ml_failed");
                }
            }
            else
            {
                useMLDetection_ = true;
                Serial.println("Switched to ML detection");
                mqttManager_->publishStatus("detection_mode_ml");
            }
        }
        else
        {
            useMLDetection_ = false;
            Serial.println("Switched to heuristic detection");
            mqttManager_->publishStatus("detection_mode_heuristic");
        }
    }
}

void CommandHandler::handleSetMode(JsonDocument *doc)
{
    Serial.printf("[Config] Current detection mode: %s (useMLDetection=%d)\n",
                  useMLDetection_ ? "ML" : "heuristic", useMLDetection_);
    if (doc != nullptr && doc->containsKey("mode"))
    {
        String modeStr = (*doc)["mode"].as<String>();

        if (modeStr == "idle")
        {
            currentMode_ = DeviceMode::IDLE;
            playModeActive_ = false;
            ledController_.off();
            serialStudioOutput_.setEmitTelemetry(false);
            if (interruptManager_.isMonitoring())
            {
                interruptManager_.stopMonitoring();
            }
            display_.setMode(MODE_IDLE);
            display_.showMessage("Mode: IDLE", TFT_DARKGREY);
            mqttManager_->publishStatus("mode_idle");
        }
        else if (modeStr == "debug")
        {
            currentMode_ = DeviceMode::DEBUG;
            playModeActive_ = false;
            ledController_.off();
            serialStudioOutput_.setEmitTelemetry(false);
            if (interruptManager_.isMonitoring())
            {
                interruptManager_.stopMonitoring();
            }
            display_.setMode(MODE_DEBUG);
            display_.showMessage("Mode: DEBUG", TFT_BLUE);
            mqttManager_->publishStatus("mode_debug");
        }
        else if (modeStr == "play")
        {
            currentMode_ = DeviceMode::PLAY;
            serialStudioOutput_.setEmitTelemetry(true);
            if (interruptManager_.isMonitoring())
            {
                interruptManager_.stopMonitoring();
            }
            display_.setMode(MODE_PLAY);
            display_.showMessage("Mode: PLAY", TFT_GREEN);
            mqttManager_->publishStatus("mode_play");
            if (useMLDetection_)
            {
                mlDetector_.fullReset();
                Serial.println("ML detector reset for new play session");
            }
            else
            {
                directionDetector_.fullReset();

                if (deviceCalibration.isValid())
                {
                    directionDetector_.setCalibration(&deviceCalibration);
                    Serial.println("Calibration data applied to DirectionDetector");
                }
                else
                {
                    directionDetector_.setCalibration(nullptr);
                    Serial.println("No calibration - using fallback thresholds");
                }
                Serial.println("Heuristic detector reset for new play session");
            }

            ledController_.off();
        }
        else if (modeStr == "live_debug")
        {
            currentMode_ = DeviceMode::LIVE_DEBUG;
            playModeActive_ = false;
            liveDebugActive_ = false;
            ledController_.off();
            serialStudioOutput_.setEmitTelemetry(true);
            if (interruptManager_.isMonitoring())
            {
                interruptManager_.stopMonitoring();
            }
            display_.setMode(MODE_LIVE_DEBUG);
            display_.showMessage("Mode: LIVE DEBUG", TFT_MAGENTA);
            mqttManager_->publishStatus("mode_live_debug");
            if (useMLDetection_)
            {
                mlDetector_.fullReset();
                Serial.println("ML detector reset for live debug session");
            }
            else
            {
                directionDetector_.fullReset();

                if (deviceCalibration.isValid())
                {
                    directionDetector_.setCalibration(&deviceCalibration);
                    Serial.println("Calibration data applied to DirectionDetector");
                }
                else
                {
                    directionDetector_.setCalibration(nullptr);
                    Serial.println("No calibration - using fallback thresholds");
                }
                Serial.println("Heuristic detector reset for live debug session");
            }
            ledController_.off();
        }
        else if (modeStr == "calibrate")
        {
            Serial.println("Starting calibration via MQTT command...");

            if (sessionManager_.getState() == IDLE)
            {
                uint8_t mp = currentConfig_.multi_pulse.toInt();
                if (mp == 0)
                    mp = 1;
                uint8_t it = currentConfig_.integration_time.substring(0, 1).toInt();
                if (it == 0)
                    it = 1;
                uint8_t led = currentConfig_.led_current.toInt();
                if (led == 0)
                    led = 200;
                calibrationManager.setSensorConfig(mp, it, led);

                if (calibrationManager.startCalibration())
                {
                    mqttManager_->publishStatus("calibration_started");
                }
                else
                {
                    display_.showMessage("Calibration failed to start", TFT_RED);
                    mqttManager_->publishStatus("calibration_failed");
                }
            }
            else
            {
                display_.showMessage("Stop collection first!", TFT_RED);
                mqttManager_->publishStatus("calibration_rejected_busy");
            }

            delay(1500);
            return;
        }
        else
        {
            display_.showMessage("Unknown mode", TFT_RED);
            mqttManager_->publishStatus("mode_invalid");
        }

        Serial.printf("Device mode set to: %s\n", modeStr.c_str());
        delay(1500);
        display_.setDisplayState(DISPLAY_IDLE);
    }
}

void CommandHandler::handleConfigureSensors(JsonDocument *doc)
{
    Serial.println("[Config] Received configure_sensors command");
    if (doc != nullptr)
    {
        Serial.print("[Config] Top-level keys: ");
        for (JsonPair kv : doc->as<JsonObject>())
        {
            Serial.printf("%s ", kv.key().c_str());
        }
        Serial.println();
        if (doc->containsKey("sensor_config"))
        {
            JsonObject sc = (*doc)["sensor_config"];
            Serial.print("[Config] sensor_config keys: ");
            for (JsonPair kv : sc)
            {
                Serial.printf("%s ", kv.key().c_str());
            }
            Serial.println();
            if (sc.containsKey("detection_mode"))
            {
                Serial.printf("[Config] detection_mode value: '%s'\n", sc["detection_mode"].as<const char *>());
            }
            else
            {
                Serial.println("[Config] detection_mode NOT found in sensor_config");
            }
        }
        else
        {
            Serial.println("[Config] sensor_config key NOT found in payload");
        }
    }
    display_.showMessage("Configuring sensors...", TFT_CYAN);

    if (doc != nullptr && doc->containsKey("sensor_config"))
    {
        JsonObject config = (*doc)["sensor_config"];

        bool wasML = useMLDetection_;

        // Shared parsing for all common sensor_config fields
        CloudConfig::applySensorConfig(config, currentConfig_, useMLDetection_,
                                       detectorConfig_, serialStudioEnabled);

        // CommandHandler-specific: duty_cycle (not present in cloud config)
        currentConfig_.duty_cycle = config["duty_cycle"] | "1/40";

        // CommandHandler-specific: init ML detector when switching modes at runtime
        if (useMLDetection_ && !wasML)
        {
            if (!mlDetector_.isReady())
            {
                Serial.println("  Initializing ML detector on config change...");
                if (!mlDetector_.init())
                {
                    Serial.println("  ML detector init failed, staying on heuristic");
                    useMLDetection_ = false;
                }
            }
        }

        // Apply side effects
        serialStudioOutput_.setEnabled(serialStudioEnabled);
        directionDetector_.setConfig(detectorConfig_);

        Serial.println("Configuration updated:");
        Serial.printf("  Sample Rate: %d Hz\n", currentConfig_.sample_rate_hz);
        Serial.printf("  LED Current: %s\n", currentConfig_.led_current.c_str());
        Serial.printf("  Integration Time: %s\n", currentConfig_.integration_time.c_str());
        Serial.printf("  Duty Cycle: %s\n", currentConfig_.duty_cycle.c_str());
        Serial.printf("  Multi-Pulse: %s pulses\n", currentConfig_.multi_pulse.c_str());
        Serial.printf("  High Resolution: %s\n", currentConfig_.high_resolution ? "enabled" : "disabled");
        Serial.printf("  Read Ambient: %s\n", currentConfig_.read_ambient ? "enabled" : "disabled");
        Serial.printf("  I2C Clock: %d kHz\n", currentConfig_.i2c_clock_khz);
        Serial.printf("  Detection Mode: %s\n", useMLDetection_ ? "ML" : "heuristic");
        Serial.printf("  Detection Config: peak=%.1fx, rise=%d, wave=%dms, smooth=%d\n",
                      detectorConfig_.peakMultiplier, detectorConfig_.minRise,
                      detectorConfig_.minWaveDurationMs, detectorConfig_.smoothingWindow);

        if (sensorManager_.reinitialize(&currentConfig_))
        {
            display_.setSensorConfig(&currentConfig_);
            display_.setDetectionConfig(detectorConfig_.peakMultiplier, detectorConfig_.minRise,
                                        detectorConfig_.minWaveDurationMs, detectorConfig_.smoothingWindow);
            display_.showMessage("Config applied successfully!", TFT_GREEN);
            mqttManager_->publishStatus("config_applied");
        }
        else
        {
            display_.showMessage("Config apply failed", TFT_RED);
            mqttManager_->publishStatus("config_failed");
        }
    }
    else
    {
        Serial.println("No sensor_config in command payload");
        display_.showMessage("Config data missing", TFT_RED);
    }

    delay(2000);
    display_.setDisplayState(DISPLAY_IDLE);
}

void CommandHandler::handleStartCollection()
{
    MemoryMonitor::printMemoryStats();
    if (!MemoryMonitor::isMemoryHealthy())
    {
        Serial.println("ERROR: Insufficient memory to start collection!");
        mqttManager_->publishStatus("collection_failed_low_memory");
        display_.showMessage("Low memory!", TFT_RED);
        delay(2000);
        display_.setDisplayState(DISPLAY_ERROR);
        return;
    }

    bool useInterruptMode = (currentConfig_.sensor_mode == SensorMode::INTERRUPT_MODE);

    const char *modeLabel = currentMode_ == DeviceMode::PLAY ? "PLAY" : currentMode_ == DeviceMode::LIVE_DEBUG ? "LIVE_DEBUG"
                                                                                                               : "DEBUG";
    Serial.printf("Starting collection - Mode: %s, Sensor: %s\n",
                  modeLabel,
                  useInterruptMode ? "INTERRUPT" : "POLLING");

    if (useInterruptMode)
    {
        if (!interruptManager_.isMonitoring())
        {
            Serial.println("Initializing InterruptManager...");
            if (!interruptManager_.begin())
            {
                Serial.println("ERROR: InterruptManager initialization failed!");
                mqttManager_->publishStatus("interrupt_init_failed");
                display_.showMessage("INT init failed!", TFT_RED);
                delay(2000);
                display_.setDisplayState(DISPLAY_ERROR);
                return;
            }

            InterruptConfig intConfig;
            intConfig.thresholdMargin = currentConfig_.interrupt_threshold_margin;
            intConfig.hysteresis = currentConfig_.interrupt_hysteresis;
            intConfig.persistence = currentConfig_.interrupt_persistence;
            intConfig.smartPersistence = currentConfig_.interrupt_smart_persistence;
            intConfig.mode = (currentConfig_.interrupt_mode == "logic")
                                 ? InterruptMode::LOGIC_OUTPUT
                                 : InterruptMode::NORMAL;
            intConfig.ledCurrent = currentConfig_.led_current.toInt();
            if (intConfig.ledCurrent == 0)
                intConfig.ledCurrent = 200;
            intConfig.integrationTime = currentConfig_.interrupt_integration_time;
            intConfig.multiPulse = currentConfig_.interrupt_multi_pulse;
            intConfig.autoCalibrate = true;

            Serial.printf("Interrupt config: margin=%d, hysteresis=%d, pers=%d, IT=%dT, mode=%s\n",
                          intConfig.thresholdMargin, intConfig.hysteresis,
                          intConfig.persistence, intConfig.integrationTime,
                          intConfig.mode == InterruptMode::LOGIC_OUTPUT ? "logic" : "normal");

            if (deviceCalibration.isValid())
            {
                interruptManager_.setCalibration(&deviceCalibration);
                Serial.println("Calibration data applied to InterruptManager");
            }
            else
            {
                interruptManager_.setCalibration(nullptr);
                Serial.println("No calibration - InterruptManager using fallback thresholds");
            }

            if (!interruptManager_.configure(intConfig))
            {
                Serial.println("WARNING: Some sensors failed to configure for interrupt mode");
            }
        }

        sessionManager_.setSessionType(SessionType::INTERRUPT_BASED);
        if (sessionManager_.startSession())
        {
            if (!interruptManager_.startMonitoring())
            {
                Serial.println("ERROR: Failed to start interrupt monitoring!");
                sessionManager_.clearBuffer();
                mqttManager_->publishStatus("interrupt_start_failed");
                display_.setDisplayState(DISPLAY_ERROR);
                return;
            }

            if (currentMode_ == DeviceMode::PLAY)
            {
                if (!ledController_.init())
                {
                    Serial.println("WARNING: LED controller init failed");
                }
                directionDetector_.reset();
                playModeActive_ = true;
                lastDetectionTime_ = 0;
                configurePlayDetection();
                ledController_.showReady();

                mqttManager_->publishStatus("play_started_interrupt");
                display_.showMessage("PLAY [INT]", TFT_GREEN);
            }
            else
            {
                mqttManager_->publishStatus("collection_started_interrupt");
                display_.showMessage("DEBUG [INT]", TFT_CYAN);
            }
            display_.setDisplayState(DISPLAY_RECORDING);
        }
        else
        {
            mqttManager_->publishStatus("collection_failed");
            display_.setDisplayState(DISPLAY_ERROR);
        }
    }
    else
    {
        sessionManager_.setSessionType(SessionType::PROXIMITY);
        if (sessionManager_.startSession())
        {
            std::vector<SensorMetadata> metadata = sensorManager_.getSensorMetadata();
            sessionManager_.setSensorMetadata(metadata);

            sensorManager_.startCollection(sessionManager_.getQueue(), &sessionManager_.getSessionSummary());

            if (currentMode_ == DeviceMode::PLAY)
            {
                if (!ledController_.init())
                {
                    Serial.println("WARNING: LED controller init failed");
                }
                directionDetector_.reset();
                playModeActive_ = true;
                lastDetectionTime_ = 0;
                configurePlayDetection();
                ledController_.showReady();

                mqttManager_->publishStatus("play_started");
                display_.showMessage("PLAY MODE", TFT_GREEN);
            }
            else if (currentMode_ == DeviceMode::LIVE_DEBUG)
            {
                if (!ledController_.init())
                {
                    Serial.println("WARNING: LED controller init failed");
                }
                directionDetector_.reset();
                liveDebugActive_ = true;
                lastDetectionTime_ = 0;
                configureLiveDebugDetection();
                ledController_.showReady();

                mqttManager_->publishStatus("live_debug_started");
                display_.showMessage("LIVE DEBUG", TFT_MAGENTA);
            }
            else
            {
                mqttManager_->publishStatus("collection_started");
                display_.showMessage("DEBUG MODE", TFT_BLUE);
            }
            display_.setDisplayState(DISPLAY_RECORDING);
        }
        else
        {
            mqttManager_->publishStatus("collection_failed");
            display_.setDisplayState(DISPLAY_ERROR);
        }
    }
}

void CommandHandler::handleStopCollection()
{
    bool wasInterruptSession = (sessionManager_.getSessionType() == SessionType::INTERRUPT_BASED);
    bool isPlayMode = (currentMode_ == DeviceMode::PLAY);
    bool isLiveDebugMode = (currentMode_ == DeviceMode::LIVE_DEBUG);

    const char *stopModeLabel = isPlayMode ? "PLAY" : isLiveDebugMode ? "LIVE_DEBUG"
                                                                      : "DEBUG";
    Serial.printf("Stopping collection - Mode: %s, Session: %s\n",
                  stopModeLabel,
                  wasInterruptSession ? "INTERRUPT" : "POLLING");

    if (wasInterruptSession)
    {
        interruptManager_.stopMonitoring();
        Serial.printf("Collected %d interrupt events\n", sessionManager_.getInterruptEventCount());
        InterruptSessionStats stats = interruptManager_.getStats();
        Serial.printf("  ISR count: %lu, dropped: %lu\n", stats.isrCount, stats.droppedEvents);
    }
    else
    {
        sensorManager_.stopCollection();
        Serial.printf("Collected %d samples\n", sessionManager_.getDataCount());
    }

    sessionManager_.stopSession();
    MemoryMonitor::printMemoryStats();

    if (isPlayMode && playModeActive_)
    {
        sessionManager_.clearBuffer();
        playModeActive_ = false;
        directionDetector_.reset();
        ledController_.off();
        detectionController_.reset();

        mqttManager_->publishStatus("play_stopped");
        display_.showMessage("Play mode stopped", TFT_YELLOW);
        delay(1500);
        display_.setDisplayState(DISPLAY_IDLE);
    }
    else if (currentMode_ == DeviceMode::LIVE_DEBUG && liveDebugActive_)
    {
        sessionManager_.clearBuffer();
        liveDebugActive_ = false;
        directionDetector_.reset();
        ledController_.off();
        detectionController_.reset();

        mqttManager_->publishStatus("live_debug_stopped");
        display_.showMessage("Live Debug stopped", TFT_YELLOW);
        delay(1500);
        display_.setDisplayState(DISPLAY_IDLE);
    }
    else
    {
        display_.setDisplayState(DISPLAY_UPLOADING);

        uint8_t activeSensorCount = 0;
        for (const auto &m : sessionManager_.getSensorMetadata())
        {
            if (m.active)
                activeSensorCount++;
        }
        sessionManager_.finalizeSessionSummary(&currentConfig_, activeSensorCount);
        dataTransmitter_->setSessionSummary(&sessionManager_.getSessionSummary());

        if (dataTransmitter_->transmitSession(sessionManager_, &currentConfig_))
        {
            dataTransmitter_->transmitSessionSummary(
                sessionManager_.getSessionSummary(),
                sessionManager_.getSessionId(),
                mqttManager_->getDeviceId());

            mqttManager_->publishStatus("upload_complete");
            display_.setDisplayState(DISPLAY_SUCCESS);
            delay(3000);
            dataTransmitter_->setSessionSummary(nullptr);
            sessionManager_.clearBuffer();
            display_.setDisplayState(DISPLAY_IDLE);
        }
        else
        {
            Serial.println("ERROR: Session transmission failed!");
            mqttManager_->publishStatus("upload_failed");
            display_.setDisplayState(DISPLAY_ERROR);
            display_.showMessage("Upload failed!", TFT_RED);
            delay(3000);
            dataTransmitter_->setSessionSummary(nullptr);
            sessionManager_.clearBuffer();
            display_.setDisplayState(DISPLAY_IDLE);
        }
    }
}

void CommandHandler::handleCaptureMissedEvent()
{
    if (currentMode_ != DeviceMode::LIVE_DEBUG || !liveDebugActive_)
    {
        Serial.println("capture_missed_event ignored — not in Live Debug mode");
        mqttManager_->publishStatus("capture_missed_ignored");
        return;
    }

    DEBUG_LOG("[LIVE_DEBUG] Missed event capture requested\n");

    sensorManager_.stopCollection();
    delay(50);
    sessionManager_.processQueue();

    display_.showMessage("Capturing missed...", TFT_MAGENTA);

    auto &buffer = sessionManager_.getDataBuffer();
    size_t actualBufferSize = buffer.size();
    size_t startIdx = 0;

    if (actualBufferSize > 0)
    {
        unsigned long latestTs = buffer[actualBufferSize - 1].timestamp_us;
        unsigned long windowUs = MISSED_EVENT_WINDOW_MS * 1000UL;
        unsigned long cutoffTs = (latestTs > windowUs) ? latestTs - windowUs : 0;

        size_t lo = 0, hi = actualBufferSize;
        while (lo < hi)
        {
            size_t mid = lo + (hi - lo) / 2;
            if (buffer[mid].timestamp_us < cutoffTs)
                lo = mid + 1;
            else
                hi = mid;
        }
        startIdx = lo;
    }

    size_t captureCount = actualBufferSize - startIdx;
    unsigned long capDurationMs = (captureCount > 0)
                                      ? (buffer[actualBufferSize - 1].timestamp_us - buffer[startIdx].timestamp_us) / 1000
                                      : 0;

    DEBUG_LOG("[LIVE_DEBUG] Missed event: capturing %d readings (%lums)\n",
             captureCount, capDurationMs);

    {
        uint8_t activeCnt = 0;
        for (const auto &m : sessionManager_.getSensorMetadata())
        {
            if (m.active)
                activeCnt++;
        }
        sessionManager_.getSessionSummary().duration_ms = capDurationMs;
        sessionManager_.finalizeSessionSummary(&currentConfig_, activeCnt);
    }

    String captureSessionId = binarySerializer_->transmitLiveDebugCaptureBinary(
        buffer, startIdx, captureCount,
        "missed_event", nullptr, 0.0,
        sessionManager_.getSessionSummary(),
        &currentConfig_);

    if (captureSessionId.length() > 0)
    {
        DEBUG_LOG("[LIVE_DEBUG] Missed event capture transmitted\n");
        mqttManager_->publishStatus("live_debug_missed_captured");
    }
    else
    {
        DEBUG_LOG("[LIVE_DEBUG] ERROR: Missed event capture failed!\n");
        mqttManager_->publishStatus("live_debug_capture_failed");
    }

    directionDetector_.reset();
    buffer.clear();
    detectionController_.reset();

    sessionManager_.getSessionSummary().reset();
    sensorManager_.startCollection(sessionManager_.getQueue(), &sessionManager_.getSessionSummary());
    display_.showMessage("Ready", TFT_MAGENTA);
    DEBUG_LOG("[LIVE_DEBUG] Resumed after missed event capture\n");
}

void CommandHandler::configurePlayDetection()
{
    DetectionController::Config playCfg;
    playCfg.bufferOverflowCap = PLAY_BUFFER_CAP;
    playCfg.alwaysResetOnOverflow = false;
    playCfg.modeLabel = "PLAY";
    detectionController_.configure(playCfg);
    detectionController_.setOnDetection([this](const DetectionResult &result)
                                        {
        String statusMsg = "detection_" + String(directionToString(result.direction));
        mqttManager_->publishStatus(statusMsg.c_str()); });
    detectionController_.setOnReset(nullptr);
    detectionController_.reset();
}

void CommandHandler::configureLiveDebugDetection()
{
    DetectionController::Config liveDbgCfg;
    liveDbgCfg.bufferOverflowCap = LIVE_DEBUG_BUFFER_CAP;
    liveDbgCfg.alwaysResetOnOverflow = true;
    liveDbgCfg.modeLabel = "LIVE_DEBUG";
    detectionController_.configure(liveDbgCfg);
    detectionController_.setOnDetection([this](const DetectionResult &result)
                                        { performLiveDebugCapture(result); });
    detectionController_.setOnReset([this]()
                                    { resumeAfterLiveDebugCapture(); });
    detectionController_.reset();
}

void CommandHandler::performLiveDebugCapture(const DetectionResult &result)
{
    DEBUG_LOG("[LIVE_DEBUG] Post-detection delay: %lums\n", POST_DETECTION_DELAY_MS);
    delay(POST_DETECTION_DELAY_MS);

    sensorManager_.stopCollection();
    delay(50);

    sessionManager_.processQueue();

    display_.showMessage("Transmitting...", TFT_MAGENTA);

    auto &buffer = sessionManager_.getDataBuffer();
    size_t actualBufferSize = buffer.size();
    size_t startIdx = 0;

    if (actualBufferSize > 0)
    {
        unsigned long latestTs = buffer[actualBufferSize - 1].timestamp_us;
        unsigned long totalWindowUs = (DETECTION_WINDOW_MS + POST_DETECTION_DELAY_MS) * 1000UL;
        unsigned long cutoffTs = (latestTs > totalWindowUs) ? latestTs - totalWindowUs : 0;

        size_t lo = 0, hi = actualBufferSize;
        while (lo < hi)
        {
            size_t mid = lo + (hi - lo) / 2;
            if (buffer[mid].timestamp_us < cutoffTs)
                lo = mid + 1;
            else
                hi = mid;
        }
        startIdx = lo;
    }

    size_t captureCount = actualBufferSize - startIdx;
    DEBUG_LOG("[LIVE_DEBUG] Capture: %d readings from idx %d (buffer has %d)\n",
             captureCount, startIdx, actualBufferSize);

    {
        uint8_t activeCnt = 0;
        for (const auto &m : sessionManager_.getSensorMetadata())
        {
            if (m.active)
                activeCnt++;
        }
        unsigned long capDur = (captureCount > 0)
                                   ? (buffer[actualBufferSize - 1].timestamp_us - buffer[startIdx].timestamp_us) / 1000
                                   : 0;
        sessionManager_.getSessionSummary().duration_ms = capDur;
        sessionManager_.finalizeSessionSummary(&currentConfig_, activeCnt);
    }

    const char *dirStr;
    if (result.direction == Direction::A_TO_B)
        dirStr = "a_to_b";
    else if (result.direction == Direction::B_TO_A)
        dirStr = "b_to_a";
    else
        dirStr = "unknown";
    String captureSessionId = binarySerializer_->transmitLiveDebugCaptureBinary(
        buffer, startIdx, captureCount,
        "detection", dirStr, result.confidence,
        sessionManager_.getSessionSummary(),
        &currentConfig_);

    if (captureSessionId.length() > 0)
    {
        DEBUG_LOG("[LIVE_DEBUG] Detection capture transmitted successfully\n");
        mqttManager_->publishStatus("live_debug_detection_captured");
    }
    else
    {
        DEBUG_LOG("[LIVE_DEBUG] ERROR: Detection capture transmission failed!\n");
        mqttManager_->publishStatus("live_debug_capture_failed");
    }
}

void CommandHandler::resumeAfterLiveDebugCapture()
{
    sessionManager_.getSessionSummary().reset();
    sensorManager_.startCollection(sessionManager_.getQueue(), &sessionManager_.getSessionSummary());
    display_.showMessage("Ready", TFT_MAGENTA);
    DEBUG_LOG("[LIVE_DEBUG] Resumed — waiting for next event\n");
}

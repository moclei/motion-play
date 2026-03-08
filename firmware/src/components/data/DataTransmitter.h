#pragma once

#include <Arduino.h>
#include <ArduinoJson.h>
#include "../session/SessionManager.h"

class MQTTManager;
#include "../sensor/SensorConfiguration.h"
#include "../memory/PSRAMAllocator.h"

enum class TransmitState : uint8_t
{
    IDLE,
    TRANSMITTING,
    SUCCEEDED,
    FAILED
};

struct UploadContext
{
    bool sendSummary = false;
    const char *successStatus = "upload_complete";
    bool restartOnFailure = false;
    unsigned long displayDelayMs = 3000;
};

class DataTransmitter
{
private:
    MQTTManager *mqttManager;
    static const size_t BATCH_SIZE = 25;
    static const size_t INT_BATCH_SIZE = 100;
    static const size_t LIVE_DEBUG_BATCH_SIZE = 200;
    static const unsigned long LIVE_DEBUG_BATCH_DELAY = 20;
    static constexpr unsigned long BATCH_DELAY_MS = 100;
    static constexpr unsigned long INT_BATCH_DELAY_MS = 50;

    SessionSummary *activeSummary = nullptr;

    // Cooperative transmission state machine
    TransmitState txState_ = TransmitState::IDLE;
    SessionType txSessionType_ = SessionType::PROXIMITY;
    String txSessionId_;
    String txDeviceId_;
    unsigned long txStartTime_ = 0;
    unsigned long txDuration_ = 0;

    std::vector<SensorReading, PSRAMAllocator<SensorReading>> *txReadings_ = nullptr;
    const std::vector<SensorMetadata> *txSensorMetadata_ = nullptr;
    const std::vector<InterruptEvent> *txEvents_ = nullptr;

    size_t txTotalItems_ = 0;
    size_t txOffset_ = 0;
    const SensorConfiguration *txConfig_ = nullptr;
    unsigned long txLastBatchTime_ = 0;
    unsigned long txBatchDelay_ = 0;
    UploadContext txContext_;

    // Single-batch transmission (internal)
    bool transmitBatch(const String &sessionId,
                       const String &deviceId,
                       unsigned long startTime,
                       unsigned long duration,
                       std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings,
                       size_t offset,
                       size_t count,
                       const std::vector<SensorMetadata> *sensorMetadata,
                       const SensorConfiguration *config = nullptr);

    bool transmitInterruptBatch(const String &sessionId,
                                const String &deviceId,
                                unsigned long startTime,
                                unsigned long duration,
                                const std::vector<InterruptEvent> &events,
                                size_t offset,
                                size_t count,
                                bool isFirstBatch,
                                const SensorConfiguration *config = nullptr);

public:
    DataTransmitter(MQTTManager *mqtt);

    void setSessionSummary(SessionSummary *summary) { activeSummary = summary; }

    // Cooperative transmission: call beginTransmission() once, then tick() from loop().
    // Sends one batch per tick() when the inter-batch delay has elapsed, allowing
    // mqttManager->loop(), display updates, and button handling to run between batches.
    bool beginTransmission(SessionManager &session, const SensorConfiguration *config = nullptr,
                           const UploadContext &context = UploadContext{});
    TransmitState tick();
    TransmitState getTransmitState() const { return txState_; }
    bool isTransmitting() const { return txState_ == TransmitState::TRANSMITTING; }
    const UploadContext &getUploadContext() const { return txContext_; }
    void resetTransmission();

    // Live Debug capture transmission (JSON batches — legacy path)
    String transmitLiveDebugCapture(
        std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings,
        size_t startIdx,
        size_t count,
        const char *captureReason,
        const char *detectionDirection,
        float detectionConfidence,
        const SensorConfiguration *config = nullptr);

    // Session Confirmation: transmit pipeline integrity summary as separate MQTT message
    bool transmitSessionSummary(const SessionSummary &summary,
                                const String &sessionId,
                                const String &deviceId);
};
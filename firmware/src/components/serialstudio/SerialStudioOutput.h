#ifndef SERIAL_STUDIO_OUTPUT_H
#define SERIAL_STUDIO_OUTPUT_H

#include <Arduino.h>
#include "../sensor/SensorManager.h"
#include "../sensor/SensorConfiguration.h"
#include "../detection/DirectionDetector.h"
#include "../memory/PSRAMAllocator.h"

class SerialStudioOutput
{
private:
    // Reference to the session data buffer (owned by SessionManager)
    std::vector<SensorReading, PSRAMAllocator<SensorReading>> *_buffer = nullptr;
    DirectionDetector *_detector = nullptr;
    SensorConfiguration *_config = nullptr;
    bool _enabled = false;
    bool _emitTelemetry = false;

    // Buffer read tracking
    size_t _lastProcessedIndex = 0;

    // Frame accumulator: one slot per sensor position (0-5)
    uint16_t _accumulator[NUM_SENSORS] = {0};
    bool _slotFilled[NUM_SENSORS] = {false};
    uint32_t _currentTimestamp = 0;
    bool _hasPendingFrame = false;

    // Detection result cache (persists until next detection or full reset)
    Direction _cachedDirection = Direction::UNKNOWN;
    float _cachedConfidence = 0.0f;

    // Frames-per-second tracking (counts all sensor cycles, not just emitted frames)
    uint32_t _frameCount = 0;
    unsigned long _fpsWindowStart = 0;
    uint16_t _currentFps = 0;

    void emitFrame();
    void resetAccumulator(uint32_t newTimestamp);

public:
    /**
     * Initialize with references to session data buffer and direction detector.
     */
    void begin(std::vector<SensorReading, PSRAMAllocator<SensorReading>> *buffer,
               DirectionDetector *detector);

    void setEnabled(bool enabled) { _enabled = enabled; }
    bool isEnabled() const { return _enabled; }

    void setConfig(SensorConfiguration *config) { _config = config; }

    /**
     * When true, frames include algorithm telemetry fields (smoothed signals,
     * thresholds, wave states, detection status). Set to true in PLAY/LIVE_DEBUG.
     */
    void setEmitTelemetry(bool emit) { _emitTelemetry = emit; }

    /**
     * Cache a detection result so it persists in the output after the detector
     * is reset. Remains until the next detection or a full reset.
     */
    void cacheDetection(const DetectionResult &result);

    /**
     * Process new readings from the buffer and emit CSV frames.
     * Call once per Core 1 loop iteration, after sessionManager.processQueue().
     */
    void update();

    /**
     * Reset read index and accumulator state.
     * Call when the buffer is cleared externally (detection events, overflow).
     */
    void resetIndex();
};

#endif

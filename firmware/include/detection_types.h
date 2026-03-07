#pragma once

#include <Arduino.h>
#include "sensor_types.h"

enum class Direction
{
    UNKNOWN,
    A_TO_B,
    B_TO_A
};

enum class DetectorState
{
    ESTABLISHING_BASELINE,
    READY,
    DETECTING
};

enum class WaveState
{
    IDLE,
    IN_WAVE,
    COMPLETE
};

struct DetectionResult
{
    Direction direction;
    float confidence;
    uint32_t centerOfMassA;
    uint32_t centerOfMassB;
    uint32_t comGapMs;
    uint16_t maxSignalA;
    uint16_t maxSignalB;
    uint32_t waveDurationA;
    uint32_t waveDurationB;
    float baselineA;
    float baselineB;
    float thresholdA;
    float thresholdB;
    uint8_t detectedModule;
    uint8_t modulesDetected;
};

struct DetectorConfig
{
    uint16_t baselineReadings = 50;
    float peakMultiplier = 1.5f;
    uint16_t minRise = 10;

    uint8_t smoothingWindow = 5;
    uint32_t minWaveDurationMs = 8;
    uint32_t maxWaveDurationMs = 200;
    uint32_t maxPeakGapMs = 150;
    float waveExitThreshold = 0.5f;

    uint32_t minGapForConfidence = 5;
    float minSignalForConfidence = 20;
};

inline const char *directionToString(Direction dir)
{
    switch (dir)
    {
    case Direction::A_TO_B:
        return "A_TO_B";
    case Direction::B_TO_A:
        return "B_TO_A";
    default:
        return "UNKNOWN";
    }
}

class IDetector
{
public:
    virtual void addReading(const SensorReading &reading) = 0;
    virtual void flushReading() = 0;
    virtual bool hasDetection() const = 0;
    virtual DetectionResult getResult() = 0;
    virtual void reset() = 0;
    virtual void fullReset() = 0;
    virtual bool isReady() const = 0;
    virtual ~IDetector() = default;
};

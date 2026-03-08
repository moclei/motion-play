#pragma once

#include <Arduino.h>
#include "ring_buffer.h"
#include "detection_types.h"
#include "sensor_types.h"
#include "../calibration/CalibrationData.h"

/**
 * Direction Detection - Version 4: Per-Sensor Adaptive Thresholds
 *
 * Each of the 6 sensors tracks independently with its own rolling baseline
 * and adaptive threshold. Detection works in three layers:
 *
 * Layer 1 - Per-Sensor: Each sensor maintains a rolling baseline (only updated
 *   during IDLE — transit waves are excluded), computes its own adaptive
 *   threshold, and runs an independent wave state machine.
 *
 * Layer 2 - Per-Module: When both sensors on a module complete waves within
 *   a valid time window, that module produces a detection with direction
 *   from center-of-mass comparison.
 *
 * Layer 3 - Consensus: Multiple modules detecting the same direction boosts
 *   confidence. Disagreement lowers it.
 */

/**
 * Independent tracker for a single sensor.
 * Maintains its own baseline, threshold, and wave state.
 */
struct SensorTracker
{
    static const size_t SMOOTH_SIZE = 10;
    static const size_t BASELINE_SIZE = 200;

    RingBuffer<float, SMOOTH_SIZE> smoothBuffer;
    RingBuffer<float, BASELINE_SIZE> baselineBuffer;
    uint32_t baselineUpdateCount = 0;
    bool baselineReady = false;

    float threshold = 0;

    WaveState waveState = WaveState::IDLE;
    uint32_t waveStartTime = 0;
    uint32_t waveEndTime = 0;
    uint32_t peakTime = 0;
    float peakValue = 0;
    float weightedSum = 0;
    float totalWeight = 0;
    uint32_t centerOfMass = 0;

    void resetWave()
    {
        waveState = WaveState::IDLE;
        waveStartTime = 0;
        waveEndTime = 0;
        peakTime = 0;
        peakValue = 0;
        weightedSum = 0;
        totalWeight = 0;
        centerOfMass = 0;
    }

    void fullReset()
    {
        smoothBuffer.clear();
        baselineBuffer.clear();
        baselineUpdateCount = 0;
        baselineReady = false;
        threshold = 0;
        resetWave();
    }
};

class DirectionDetector : public IDetector
{
private:
    DetectorConfig config;
    SensorTracker sensors[NUM_SENSORS];

    const DeviceCalibration *_calibration = nullptr;
    bool _useCalibration = false;

    // Tracks which module last produced a detection (for telemetry)
    int _detectedModule = -1;

    void updateSensorWave(SensorTracker &sensor, float smoothed, uint32_t timestamp);
    void recalculateThreshold(SensorTracker &sensor, uint8_t position);
    bool isModuleDetected(int module) const;

public:
    DirectionDetector();
    DirectionDetector(const DetectorConfig &cfg);

    void addReading(const SensorReading &reading) override;
    void flushReading() override;

    bool hasDetection() const override;
    DetectionResult getResult() override;

    void reset() override;
    void fullReset() override;

    bool isReady() const override;
    DetectorState getState() const;

    void setConfig(const DetectorConfig &cfg);
    void setCalibration(const DeviceCalibration *cal);
    bool isUsingCalibration() const { return _useCalibration; }

    // Per-sensor telemetry accessors
    float getSensorThreshold(uint8_t position) const;
    float getSensorSmoothed(uint8_t position) const;
    WaveState getSensorWaveState(uint8_t position) const;

    // Legacy telemetry (returns data from most recently detected module, or module 0)
    float getSmoothedA() const;
    float getSmoothedB() const;
    float getThresholdA() const;
    float getThresholdB() const;
    WaveState getWaveStateA() const;
    WaveState getWaveStateB() const;

    void debugPrint() const;
};

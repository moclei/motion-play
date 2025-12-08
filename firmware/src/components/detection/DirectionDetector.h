#ifndef DIRECTION_DETECTOR_H
#define DIRECTION_DETECTOR_H

#include <Arduino.h>
#include <vector>
#include "../sensor/SensorManager.h"

/**
 * Direction Detection - Version 3: Adaptive Threshold + Wave Envelope (Real-Time)
 *
 * Ported from TypeScript directionDetector.ts to work in real-time streaming mode.
 *
 * Algorithm Overview:
 * 1. Establish baseline from first N readings (noise floor)
 * 2. Calculate adaptive threshold: baseline + max(baseline × (mult-1), minRise)
 * 3. Detect wave entry when signal exceeds threshold
 * 4. Track wave envelope, calculate center of mass
 * 5. Detect wave exit when signal drops below threshold
 * 6. Compare centers of mass between sides → direction
 *
 * Key improvement over V1: Adaptive thresholding prevents false detections
 * in low-noise sessions while still catching events in high-noise sessions.
 */

enum class Direction
{
    UNKNOWN,
    A_TO_B,
    B_TO_A
};

enum class DetectorState
{
    ESTABLISHING_BASELINE, // Collecting initial readings for baseline
    READY,                 // Baseline established, waiting for event
    DETECTING              // Wave detected, tracking for direction
};

enum class WaveState
{
    IDLE,    // Below threshold, waiting
    IN_WAVE, // Above threshold, tracking
    COMPLETE // Wave finished, data ready
};

struct DetectionResult
{
    Direction direction;
    float confidence;
    uint32_t centerOfMassA; // Center of mass timestamp for side A
    uint32_t centerOfMassB; // Center of mass timestamp for side B
    uint32_t comGapMs;      // Time gap between centers of mass
    uint16_t maxSignalA;
    uint16_t maxSignalB;
    // Debug info
    float baselineA;
    float baselineB;
    float thresholdA;
    float thresholdB;
};

struct DetectorConfig
{
    // Baseline parameters
    uint16_t baselineReadings = 50; // Number of readings to establish baseline
    float peakMultiplier = 1.5f;    // Threshold = baseline + max(baseline*(mult-1), minRise)
    uint16_t minRise = 10;          // Minimum absolute rise required

    // Wave detection parameters
    uint8_t smoothingWindow = 3;      // Moving average window size
    uint32_t maxWaveDurationMs = 200; // Maximum wave duration before timeout
    uint32_t maxPeakGapMs = 150;      // Maximum time between side A and B waves
    float waveExitThreshold = 0.5f;   // Exit wave when signal drops to this fraction of peak

    // Confidence parameters
    uint32_t minGapForConfidence = 5;  // Minimum gap (ms) for high confidence
    float minSignalForConfidence = 20; // Minimum signal for high confidence
};

/**
 * Wave tracking state for one side
 */
struct WaveTracker
{
    WaveState state = WaveState::IDLE;

    // Wave envelope data
    uint32_t waveStartTime = 0;
    uint32_t waveEndTime = 0;
    uint32_t peakTime = 0;
    float peakValue = 0;

    // Center of mass calculation (running accumulation)
    float weightedSum = 0;     // Sum of (value * timestamp)
    float totalWeight = 0;     // Sum of values
    uint32_t centerOfMass = 0; // Calculated when wave completes

    // Threshold for this side
    float threshold = 0;

    void reset()
    {
        state = WaveState::IDLE;
        waveStartTime = 0;
        waveEndTime = 0;
        peakTime = 0;
        peakValue = 0;
        weightedSum = 0;
        totalWeight = 0;
        centerOfMass = 0;
    }
};

/**
 * Baseline statistics for one side
 */
struct BaselineStats
{
    float sum = 0;
    float max = 0;
    uint32_t count = 0;

    float getMean() const { return count > 0 ? sum / count : 0; }
    void reset()
    {
        sum = 0;
        max = 0;
        count = 0;
    }
};

/**
 * Ring buffer for smoothing
 */
template <typename T, size_t SIZE>
class RingBuffer
{
private:
    T buffer[SIZE];
    size_t head = 0;
    size_t count = 0;

public:
    void push(const T &item)
    {
        buffer[head] = item;
        head = (head + 1) % SIZE;
        if (count < SIZE)
            count++;
    }

    T &operator[](size_t idx)
    {
        size_t actualIdx = (head - count + idx + SIZE) % SIZE;
        return buffer[actualIdx];
    }

    const T &operator[](size_t idx) const
    {
        size_t actualIdx = (head - count + idx + SIZE) % SIZE;
        return buffer[actualIdx];
    }

    size_t size() const { return count; }
    void clear()
    {
        count = 0;
        head = 0;
    }
    bool isFull() const { return count == SIZE; }

    // Get smoothed average of last N items
    float getSmoothedAverage(size_t windowSize) const
    {
        if (count == 0)
            return 0;
        size_t n = min(windowSize, count);
        float sum = 0;
        for (size_t i = count - n; i < count; i++)
        {
            sum += buffer[(head - count + i + SIZE) % SIZE];
        }
        return sum / n;
    }
};

/**
 * Aggregated sensor reading by side
 */
struct AggregatedReading
{
    uint32_t timestamp;
    uint16_t sideA; // Sum of all side 2 sensors (A-facing)
    uint16_t sideB; // Sum of all side 1 sensors (B-facing)
};

class DirectionDetector
{
private:
    DetectorConfig config;
    DetectorState state = DetectorState::ESTABLISHING_BASELINE;

    // Baseline tracking
    BaselineStats baselineA;
    BaselineStats baselineB;
    uint32_t baselineReadingCount = 0;

    // Wave tracking for each side
    WaveTracker waveA;
    WaveTracker waveB;

    // Smoothing buffers
    static const size_t SMOOTH_BUFFER_SIZE = 10;
    RingBuffer<float, SMOOTH_BUFFER_SIZE> smoothBufferA;
    RingBuffer<float, SMOOTH_BUFFER_SIZE> smoothBufferB;

    // Current aggregated reading
    uint32_t currentTimestamp = 0;
    uint16_t currentSideA = 0;
    uint16_t currentSideB = 0;
    bool hasCurrentReading = false;

    // Detection state
    uint32_t detectionStartTime = 0;

    // Helper methods
    void updateBaseline(float valueA, float valueB);
    void calculateThresholds();
    void processReading(uint32_t timestamp, float smoothedA, float smoothedB);
    void updateWaveTracker(WaveTracker &tracker, float value, uint32_t timestamp);
    DetectionResult checkForDetection();

public:
    DirectionDetector();
    DirectionDetector(const DetectorConfig &cfg);

    /**
     * Add a new sensor reading
     */
    void addReading(const SensorReading &reading);

    /**
     * Flush current aggregated reading and process it
     */
    void flushReading();

    /**
     * Check if a detection is ready
     */
    bool hasDetection() const;

    /**
     * Get the detection result (call after hasDetection returns true)
     */
    DetectionResult getResult();

    /**
     * Reset detector state (keeps baseline if established)
     */
    void reset();

    /**
     * Full reset including baseline
     */
    void fullReset();

    /**
     * Check if baseline is established
     */
    bool isReady() const { return state != DetectorState::ESTABLISHING_BASELINE; }

    /**
     * Get current state for debugging
     */
    DetectorState getState() const { return state; }

    /**
     * Update configuration
     */
    void setConfig(const DetectorConfig &cfg);

    /**
     * Get string representation of direction
     */
    static const char *directionToString(Direction dir);

    /**
     * Debug: Print current state
     */
    void debugPrint() const;
};

#endif

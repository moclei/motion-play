#ifndef DIRECTION_DETECTOR_H
#define DIRECTION_DETECTOR_H

#include <Arduino.h>
#include <vector>
#include "../sensor/SensorManager.h"

/**
 * Direction Detection - Attempt 1: Rise-Start Algorithm
 * 
 * Detects which direction an object passed through the sensor hoop
 * by comparing when each side's aggregate signal starts rising.
 * 
 * See: docs/initiatives/direction-detection/attempt1/IMPLEMENTATION.md
 */

enum class Direction {
    UNKNOWN,
    A_TO_B,
    B_TO_A
};

struct DetectionResult {
    Direction direction;
    float confidence;
    uint32_t riseTimeA;
    uint32_t riseTimeB;
    uint32_t gapMs;
    uint16_t maxSignalA;
    uint16_t maxSignalB;
};

struct DetectorConfig {
    uint8_t smoothingWindow = 3;     // Moving average window size
    uint16_t minRise = 10;           // Minimum signal increase to consider a peak
    uint32_t maxPeakGapMs = 100;     // Maximum time between paired peaks
    float derivativeThreshold = 2.0; // Minimum derivative to count as "rising"
};

/**
 * Ring buffer for efficient sliding window analysis
 */
template<typename T, size_t SIZE>
class RingBuffer {
private:
    T buffer[SIZE];
    size_t head = 0;
    size_t count = 0;
    
public:
    void push(const T& item) {
        buffer[head] = item;
        head = (head + 1) % SIZE;
        if (count < SIZE) count++;
    }
    
    T& operator[](size_t idx) {
        // idx 0 = oldest, idx count-1 = newest
        size_t actualIdx = (head - count + idx + SIZE) % SIZE;
        return buffer[actualIdx];
    }
    
    const T& operator[](size_t idx) const {
        size_t actualIdx = (head - count + idx + SIZE) % SIZE;
        return buffer[actualIdx];
    }
    
    size_t size() const { return count; }
    void clear() { count = 0; head = 0; }
    bool isFull() const { return count == SIZE; }
};

/**
 * Aggregated sensor reading by side
 */
struct AggregatedReading {
    uint32_t timestamp;
    uint16_t sideA;  // Sum of all side 2 sensors (A-facing)
    uint16_t sideB;  // Sum of all side 1 sensors (B-facing)
};

class DirectionDetector {
private:
    DetectorConfig config;
    
    // Analysis window (stores aggregated readings)
    // 200ms window at ~400Hz = 80 samples, use 100 for safety
    static const size_t WINDOW_SIZE = 100;
    RingBuffer<AggregatedReading, WINDOW_SIZE> window;
    
    // Smoothed signals
    float smoothedA[WINDOW_SIZE];
    float smoothedB[WINDOW_SIZE];
    
    // Derivatives
    float derivA[WINDOW_SIZE];
    float derivB[WINDOW_SIZE];
    
    // Rise detection state
    struct RiseInfo {
        uint32_t startTime;
        uint32_t peakTime;
        float riseAmount;
        bool valid;
    };
    
    // Helper methods
    void computeSmoothedSignals();
    void computeDerivatives();
    RiseInfo findMainRise(const float* signal, const float* deriv, size_t count);
    float calculateCenterOfMass(const float* signal, size_t count, uint32_t startTs);
    
public:
    DirectionDetector();
    DirectionDetector(const DetectorConfig& cfg);
    
    /**
     * Add a new sensor reading to the analysis window
     */
    void addReading(const SensorReading& reading);
    
    /**
     * Add a batch of readings (more efficient)
     */
    void addReadings(const SensorReading* readings, size_t count);
    
    /**
     * Analyze current window and detect direction
     */
    DetectionResult analyze();
    
    /**
     * Clear the analysis window
     */
    void reset();
    
    /**
     * Check if window has enough data for analysis
     */
    bool hasEnoughData() const;
    
    /**
     * Update configuration
     */
    void setConfig(const DetectorConfig& cfg);
    
    /**
     * Get string representation of direction
     */
    static const char* directionToString(Direction dir);
};

#endif


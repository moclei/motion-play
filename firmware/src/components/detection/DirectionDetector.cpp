#include "DirectionDetector.h"

DirectionDetector::DirectionDetector() : config() {}

DirectionDetector::DirectionDetector(const DetectorConfig& cfg) : config(cfg) {}

void DirectionDetector::addReading(const SensorReading& reading) {
    // Find or create aggregated reading for this timestamp
    size_t windowSize = window.size();
    
    // Check if we already have an entry for this timestamp
    if (windowSize > 0 && window[windowSize - 1].timestamp == reading.timestamp_ms) {
        // Add to existing entry
        AggregatedReading& agg = window[windowSize - 1];
        if (reading.side == 2) {
            agg.sideA += reading.proximity;
        } else {
            agg.sideB += reading.proximity;
        }
    } else {
        // Create new entry
        AggregatedReading agg;
        agg.timestamp = reading.timestamp_ms;
        agg.sideA = (reading.side == 2) ? reading.proximity : 0;
        agg.sideB = (reading.side == 1) ? reading.proximity : 0;
        window.push(agg);
    }
}

void DirectionDetector::addReadings(const SensorReading* readings, size_t count) {
    for (size_t i = 0; i < count; i++) {
        addReading(readings[i]);
    }
}

void DirectionDetector::computeSmoothedSignals() {
    size_t count = window.size();
    
    for (size_t i = 0; i < count; i++) {
        // Simple moving average
        float sumA = 0, sumB = 0;
        int samples = 0;
        
        int start = max(0, (int)i - (int)config.smoothingWindow + 1);
        for (int j = start; j <= (int)i; j++) {
            sumA += window[j].sideA;
            sumB += window[j].sideB;
            samples++;
        }
        
        smoothedA[i] = sumA / samples;
        smoothedB[i] = sumB / samples;
    }
}

void DirectionDetector::computeDerivatives() {
    size_t count = window.size();
    
    derivA[0] = 0;
    derivB[0] = 0;
    
    for (size_t i = 1; i < count; i++) {
        derivA[i] = smoothedA[i] - smoothedA[i - 1];
        derivB[i] = smoothedB[i] - smoothedB[i - 1];
    }
}

DirectionDetector::RiseInfo DirectionDetector::findMainRise(
    const float* signal, const float* deriv, size_t count) {
    
    RiseInfo bestRise = {0, 0, 0, false};
    RiseInfo currentRise = {0, 0, 0, false};
    
    bool inRise = false;
    float riseStartValue = 0;
    int consecutivePositive = 0;
    
    for (size_t i = 1; i < count; i++) {
        float prevDeriv = deriv[i - 1];
        float currDeriv = deriv[i];
        
        // Count consecutive positive derivatives
        if (currDeriv > config.derivativeThreshold) {
            consecutivePositive++;
            if (consecutivePositive >= 2 && !inRise) {
                // Start of significant rise
                size_t startIdx = i - consecutivePositive;
                currentRise.startTime = window[startIdx].timestamp;
                riseStartValue = signal[startIdx];
                inRise = true;
            }
        } else {
            consecutivePositive = 0;
        }
        
        // Detect peak (end of rise)
        if (prevDeriv > 0 && currDeriv <= 0 && inRise) {
            currentRise.peakTime = window[i - 1].timestamp;
            currentRise.riseAmount = signal[i - 1] - riseStartValue;
            
            if (currentRise.riseAmount >= config.minRise) {
                currentRise.valid = true;
                
                // Keep the rise with the largest amount
                if (currentRise.riseAmount > bestRise.riseAmount) {
                    bestRise = currentRise;
                }
            }
            
            inRise = false;
        }
    }
    
    return bestRise;
}

DetectionResult DirectionDetector::analyze() {
    DetectionResult result;
    result.direction = Direction::UNKNOWN;
    result.confidence = 0;
    result.riseTimeA = 0;
    result.riseTimeB = 0;
    result.gapMs = 0;
    result.maxSignalA = 0;
    result.maxSignalB = 0;
    
    size_t count = window.size();
    if (count < 10) {
        return result;  // Not enough data
    }
    
    // Step 1: Compute smoothed signals
    computeSmoothedSignals();
    
    // Step 2: Compute derivatives
    computeDerivatives();
    
    // Step 3: Find max signals
    for (size_t i = 0; i < count; i++) {
        if (window[i].sideA > result.maxSignalA) result.maxSignalA = window[i].sideA;
        if (window[i].sideB > result.maxSignalB) result.maxSignalB = window[i].sideB;
    }
    
    // Step 4: Find main rises on each side
    RiseInfo riseA = findMainRise(smoothedA, derivA, count);
    RiseInfo riseB = findMainRise(smoothedB, derivB, count);
    
    // Step 5: Check if we have valid rises on both sides
    if (!riseA.valid || !riseB.valid) {
        return result;  // No valid event detected
    }
    
    // Step 6: Check if peaks are close enough (same event)
    uint32_t peakGap = abs((int32_t)riseA.peakTime - (int32_t)riseB.peakTime);
    if (peakGap > config.maxPeakGapMs) {
        return result;  // Not the same event
    }
    
    // Step 7: Determine direction based on rise start time
    result.riseTimeA = riseA.startTime;
    result.riseTimeB = riseB.startTime;
    result.gapMs = abs((int32_t)riseA.startTime - (int32_t)riseB.startTime);
    
    if (riseA.startTime < riseB.startTime) {
        result.direction = Direction::A_TO_B;
    } else if (riseB.startTime < riseA.startTime) {
        result.direction = Direction::B_TO_A;
    } else {
        // Tie - use peak timing as fallback
        if (riseA.peakTime < riseB.peakTime) {
            result.direction = Direction::A_TO_B;
        } else {
            result.direction = Direction::B_TO_A;
        }
    }
    
    // Step 8: Calculate confidence
    float gapConfidence = min(1.0f, result.gapMs / 50.0f);
    float signalConfidence = min(1.0f, (riseA.riseAmount + riseB.riseAmount) / 100.0f);
    result.confidence = (gapConfidence + signalConfidence) / 2.0f;
    
    return result;
}

void DirectionDetector::reset() {
    window.clear();
}

bool DirectionDetector::hasEnoughData() const {
    return window.size() >= 20;  // At least 20 aggregated readings
}

void DirectionDetector::setConfig(const DetectorConfig& cfg) {
    config = cfg;
}

const char* DirectionDetector::directionToString(Direction dir) {
    switch (dir) {
        case Direction::A_TO_B: return "A_TO_B";
        case Direction::B_TO_A: return "B_TO_A";
        default: return "UNKNOWN";
    }
}


#include "DirectionDetector.h"

DirectionDetector::DirectionDetector() : config() {}

DirectionDetector::DirectionDetector(const DetectorConfig &cfg) : config(cfg) {}

void DirectionDetector::addReading(const SensorReading &reading)
{
    // Check if this is a new timestamp (need to flush previous)
    if (hasCurrentReading && reading.timestamp_ms != currentTimestamp)
    {
        flushReading();
    }

    // Aggregate by side
    currentTimestamp = reading.timestamp_ms;
    if (reading.side == 2)
    {
        currentSideA += reading.proximity;
    }
    else
    {
        currentSideB += reading.proximity;
    }
    hasCurrentReading = true;
}

void DirectionDetector::flushReading()
{
    if (!hasCurrentReading)
        return;

    // Add to smoothing buffers
    smoothBufferA.push((float)currentSideA);
    smoothBufferB.push((float)currentSideB);

    // Get smoothed values
    float smoothedA = smoothBufferA.getSmoothedAverage(config.smoothingWindow);
    float smoothedB = smoothBufferB.getSmoothedAverage(config.smoothingWindow);

    // Process based on current state
    switch (state)
    {
    case DetectorState::ESTABLISHING_BASELINE:
        updateBaseline(smoothedA, smoothedB);
        break;

    case DetectorState::READY:
    case DetectorState::DETECTING:
        processReading(currentTimestamp, smoothedA, smoothedB);
        break;
    }

    // Reset current reading
    currentSideA = 0;
    currentSideB = 0;
    hasCurrentReading = false;
}

void DirectionDetector::updateBaseline(float valueA, float valueB)
{
    // Accumulate statistics
    baselineA.sum += valueA;
    baselineA.count++;
    if (valueA > baselineA.max)
        baselineA.max = valueA;

    baselineB.sum += valueB;
    baselineB.count++;
    if (valueB > baselineB.max)
        baselineB.max = valueB;

    baselineReadingCount++;

    // Check if we have enough readings
    if (baselineReadingCount >= config.baselineReadings)
    {
        calculateThresholds();
        state = DetectorState::READY;

        Serial.println("=== BASELINE ESTABLISHED ===");
        Serial.printf("  Side A: mean=%.1f, max=%.1f, threshold=%.1f\n",
                      baselineA.getMean(), baselineA.max, waveA.threshold);
        Serial.printf("  Side B: mean=%.1f, max=%.1f, threshold=%.1f\n",
                      baselineB.getMean(), baselineB.max, waveB.threshold);
    }
}

void DirectionDetector::calculateThresholds()
{
    // Check if we should use calibration data
    if (_calibration != nullptr && _calibration->isValid())
    {
        // Use calibrated thresholds
        // DirectionDetector aggregates by side (A=S2, B=S1) across all PCBs
        // Each PCB's calibration is for both sensors combined
        // We'll take the maximum threshold across PCBs as conservative threshold
        
        uint16_t maxThreshold = 0;
        for (int i = 0; i < CALIBRATION_NUM_PCBS; i++)
        {
            if (_calibration->pcbs[i].threshold > maxThreshold)
            {
                maxThreshold = _calibration->pcbs[i].threshold;
            }
        }
        
        // Apply calibrated threshold to both sides
        // Since each PCB has one sensor per side, we use the same threshold
        waveA.threshold = (float)maxThreshold;
        waveB.threshold = (float)maxThreshold;
        _useCalibration = true;
        
        Serial.printf("[DirectionDetector] Using CALIBRATED thresholds: A=%.0f, B=%.0f\n",
                      waveA.threshold, waveB.threshold);
        return;
    }

    // Fallback: calculate from baseline (original behavior)
    _useCalibration = false;
    
    // Use max value as baseline (captures noise ceiling)
    float baseA = baselineA.max;
    float baseB = baselineB.max;

    // Threshold = baseline + max(baseline × (multiplier-1), minRise)
    // This ensures minimum absolute rise while scaling for high-noise sessions
    float riseA = max(baseA * (config.peakMultiplier - 1.0f), (float)config.minRise);
    float riseB = max(baseB * (config.peakMultiplier - 1.0f), (float)config.minRise);

    waveA.threshold = baseA + riseA;
    waveB.threshold = baseB + riseB;
    
    Serial.printf("[DirectionDetector] Using FALLBACK thresholds: A=%.0f, B=%.0f\n",
                  waveA.threshold, waveB.threshold);
}

void DirectionDetector::processReading(uint32_t timestamp, float smoothedA, float smoothedB)
{
    // Update wave trackers
    updateWaveTracker(waveA, smoothedA, timestamp);
    updateWaveTracker(waveB, smoothedB, timestamp);

    // Check for state transitions
    if (state == DetectorState::READY)
    {
        // Check if either side entered a wave
        if (waveA.state == WaveState::IN_WAVE || waveB.state == WaveState::IN_WAVE)
        {
            state = DetectorState::DETECTING;
            detectionStartTime = timestamp;
            Serial.printf("WAVE DETECTED at %lu (A=%s, B=%s)\n",
                          timestamp,
                          waveA.state == WaveState::IN_WAVE ? "IN_WAVE" : "IDLE",
                          waveB.state == WaveState::IN_WAVE ? "IN_WAVE" : "IDLE");
        }
    }

    // Check for timeout in detecting state
    if (state == DetectorState::DETECTING)
    {
        uint32_t elapsed = timestamp - detectionStartTime;
        if (elapsed > config.maxWaveDurationMs + config.maxPeakGapMs)
        {
            Serial.println("Detection timeout - resetting waves");
            waveA.reset();
            waveB.reset();
            state = DetectorState::READY;
        }
    }
}

void DirectionDetector::updateWaveTracker(WaveTracker &tracker, float value, uint32_t timestamp)
{
    switch (tracker.state)
    {
    case WaveState::IDLE:
        // Check if signal exceeds threshold
        if (value > tracker.threshold)
        {
            tracker.state = WaveState::IN_WAVE;
            tracker.waveStartTime = timestamp;
            tracker.peakValue = value;
            tracker.peakTime = timestamp;
            tracker.weightedSum = value * timestamp;
            tracker.totalWeight = value;
        }
        break;

    case WaveState::IN_WAVE:
    {
        // Update peak if this is higher
        if (value > tracker.peakValue)
        {
            tracker.peakValue = value;
            tracker.peakTime = timestamp;
        }

        // Accumulate for center of mass
        tracker.weightedSum += value * timestamp;
        tracker.totalWeight += value;

        // Check for wave exit (drops below threshold or fraction of peak)
        float exitThreshold = max(tracker.threshold,
                                  tracker.peakValue * config.waveExitThreshold);
        if (value < exitThreshold)
        {
            // Wave complete
            tracker.state = WaveState::COMPLETE;
            tracker.waveEndTime = timestamp;

            // Calculate center of mass
            if (tracker.totalWeight > 0)
            {
                tracker.centerOfMass = (uint32_t)(tracker.weightedSum / tracker.totalWeight);
            }
            else
            {
                tracker.centerOfMass = tracker.peakTime;
            }

            Serial.printf("  Wave complete: start=%lu, peak=%lu (%.1f), end=%lu, CoM=%lu\n",
                          tracker.waveStartTime, tracker.peakTime, tracker.peakValue,
                          tracker.waveEndTime, tracker.centerOfMass);
        }

        // Check for wave timeout
        if (timestamp - tracker.waveStartTime > config.maxWaveDurationMs)
        {
            // Force wave completion
            tracker.state = WaveState::COMPLETE;
            tracker.waveEndTime = timestamp;
            if (tracker.totalWeight > 0)
            {
                tracker.centerOfMass = (uint32_t)(tracker.weightedSum / tracker.totalWeight);
            }
            else
            {
                tracker.centerOfMass = tracker.peakTime;
            }
            Serial.println("  Wave timeout - forced completion");
        }
        break;
    }

    case WaveState::COMPLETE:
        // Already complete, waiting for detection check
        break;
    }
}

bool DirectionDetector::hasDetection() const
{
    if (state != DetectorState::DETECTING)
        return false;

    // Need both waves to be complete
    if (waveA.state != WaveState::COMPLETE || waveB.state != WaveState::COMPLETE)
    {
        return false;
    }

    // Check if waves are close enough in time (same event)
    uint32_t peakGap = abs((int32_t)waveA.peakTime - (int32_t)waveB.peakTime);
    return peakGap <= config.maxPeakGapMs;
}

DetectionResult DirectionDetector::getResult()
{
    DetectionResult result;
    result.direction = Direction::UNKNOWN;
    result.confidence = 0;
    result.centerOfMassA = 0;
    result.centerOfMassB = 0;
    result.comGapMs = 0;
    result.maxSignalA = 0;
    result.maxSignalB = 0;
    result.baselineA = baselineA.max;
    result.baselineB = baselineB.max;
    result.thresholdA = waveA.threshold;
    result.thresholdB = waveB.threshold;

    if (!hasDetection())
    {
        return result;
    }

    // Fill in result
    result.centerOfMassA = waveA.centerOfMass;
    result.centerOfMassB = waveB.centerOfMass;
    result.comGapMs = abs((int32_t)waveA.centerOfMass - (int32_t)waveB.centerOfMass);
    result.maxSignalA = (uint16_t)waveA.peakValue;
    result.maxSignalB = (uint16_t)waveB.peakValue;

    // Determine direction from center of mass comparison
    if (waveA.centerOfMass < waveB.centerOfMass)
    {
        result.direction = Direction::A_TO_B;
    }
    else if (waveB.centerOfMass < waveA.centerOfMass)
    {
        result.direction = Direction::B_TO_A;
    }
    else
    {
        // Tie - use peak time as fallback
        if (waveA.peakTime < waveB.peakTime)
        {
            result.direction = Direction::A_TO_B;
        }
        else
        {
            result.direction = Direction::B_TO_A;
        }
    }

    // Calculate confidence
    // Higher gap = more confident (up to a point)
    float gapConfidence = min(1.0f, (float)result.comGapMs / 50.0f);

    // Stronger signals = more confident
    float signalStrength = (waveA.peakValue + waveB.peakValue) / 2.0f;
    float signalConfidence = min(1.0f, signalStrength / 100.0f);

    result.confidence = (gapConfidence * 0.6f) + (signalConfidence * 0.4f);

    return result;
}

void DirectionDetector::reset()
{
    // Reset wave trackers but keep baseline
    waveA.reset();
    waveB.reset();
    smoothBufferA.clear();
    smoothBufferB.clear();
    currentSideA = 0;
    currentSideB = 0;
    hasCurrentReading = false;
    detectionStartTime = 0;

    if (state != DetectorState::ESTABLISHING_BASELINE)
    {
        state = DetectorState::READY;
    }
}

void DirectionDetector::fullReset()
{
    reset();
    baselineA.reset();
    baselineB.reset();
    baselineReadingCount = 0;
    waveA.threshold = 0;
    waveB.threshold = 0;
    state = DetectorState::ESTABLISHING_BASELINE;
}

void DirectionDetector::setConfig(const DetectorConfig &cfg)
{
    config = cfg;
    // Recalculate thresholds if baseline is established
    if (state != DetectorState::ESTABLISHING_BASELINE)
    {
        calculateThresholds();
    }
}

void DirectionDetector::setCalibration(const DeviceCalibration *cal)
{
    _calibration = cal;
    
    if (cal != nullptr && cal->isValid())
    {
        Serial.println("[DirectionDetector] Calibration data set");
        cal->debugPrint();
        
        // If we already have baseline, recalculate thresholds with calibration
        if (state != DetectorState::ESTABLISHING_BASELINE)
        {
            calculateThresholds();
        }
    }
    else
    {
        _useCalibration = false;
        Serial.println("[DirectionDetector] Calibration cleared (invalid or null)");
    }
}

const char *DirectionDetector::directionToString(Direction dir)
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

void DirectionDetector::debugPrint() const
{
    Serial.println("=== DirectionDetector State ===");
    Serial.printf("State: %s\n",
                  state == DetectorState::ESTABLISHING_BASELINE ? "ESTABLISHING_BASELINE" : state == DetectorState::READY ? "READY"
                                                                                                                          : "DETECTING");
    Serial.printf("Threshold source: %s\n", _useCalibration ? "CALIBRATED" : "FALLBACK");
    Serial.printf("Baseline readings: %lu / %u\n", baselineReadingCount, config.baselineReadings);
    Serial.printf("Baseline A: mean=%.1f, max=%.1f\n", baselineA.getMean(), baselineA.max);
    Serial.printf("Baseline B: mean=%.1f, max=%.1f\n", baselineB.getMean(), baselineB.max);
    Serial.printf("Threshold A: %.1f, B: %.1f\n", waveA.threshold, waveB.threshold);
    Serial.printf("Wave A state: %s\n",
                  waveA.state == WaveState::IDLE ? "IDLE" : waveA.state == WaveState::IN_WAVE ? "IN_WAVE"
                                                                                              : "COMPLETE");
    Serial.printf("Wave B state: %s\n",
                  waveB.state == WaveState::IDLE ? "IDLE" : waveB.state == WaveState::IN_WAVE ? "IN_WAVE"
                                                                                              : "COMPLETE");
}

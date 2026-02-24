#include "DirectionDetector.h"

extern bool serialStudioEnabled;

DirectionDetector::DirectionDetector() : config() {}

DirectionDetector::DirectionDetector(const DetectorConfig &cfg) : config(cfg) {}

void DirectionDetector::addReading(const SensorReading &reading)
{
    uint32_t timestampMs = reading.timestamp_us / 1000;
    uint8_t pos = reading.position;
    if (pos >= NUM_SENSORS)
        return;

    SensorTracker &sensor = sensors[pos];
    float value = (float)reading.proximity;

    sensor.smoothBuffer.push(value);
    float smoothed = sensor.smoothBuffer.getSmoothedAverage(config.smoothingWindow);

    // Only update baseline when sensor is idle (excludes transit waves)
    if (sensor.waveState == WaveState::IDLE)
    {
        sensor.baselineBuffer.push(smoothed);
        sensor.baselineUpdateCount++;

        if (!sensor.baselineReady &&
            sensor.baselineBuffer.size() >= config.baselineReadings)
        {
            sensor.baselineReady = true;
            recalculateThreshold(sensor, pos);

            if (!serialStudioEnabled)
                Serial.printf("[Detector] Sensor %d baseline ready (threshold=%.1f)\n",
                              pos, sensor.threshold);
        }
        else if (sensor.baselineReady &&
                 sensor.baselineUpdateCount % 50 == 0)
        {
            recalculateThreshold(sensor, pos);
        }
    }

    if (sensor.baselineReady)
    {
        updateSensorWave(sensor, smoothed, timestampMs);
    }
}

void DirectionDetector::flushReading()
{
    // Per-sensor tracking processes each reading immediately in addReading().
    // Kept for interface compatibility with callers.
}

void DirectionDetector::recalculateThreshold(SensorTracker &sensor, uint8_t position)
{
    if (_calibration != nullptr && _calibration->isValid())
    {
        uint8_t pcbIdx = position / 2;
        if (pcbIdx < CALIBRATION_NUM_PCBS)
        {
            sensor.threshold = (float)_calibration->pcbs[pcbIdx].threshold;
            _useCalibration = true;
            return;
        }
    }

    _useCalibration = false;
    float baseMax = sensor.baselineBuffer.getMax();
    float rise = max(baseMax * (config.peakMultiplier - 1.0f), (float)config.minRise);
    sensor.threshold = baseMax + rise;
}

void DirectionDetector::updateSensorWave(SensorTracker &sensor, float smoothed, uint32_t timestamp)
{
    switch (sensor.waveState)
    {
    case WaveState::IDLE:
        if (smoothed > sensor.threshold)
        {
            sensor.waveState = WaveState::IN_WAVE;
            sensor.waveStartTime = timestamp;
            sensor.peakValue = smoothed;
            sensor.peakTime = timestamp;
            sensor.weightedSum = smoothed * timestamp;
            sensor.totalWeight = smoothed;
        }
        break;

    case WaveState::IN_WAVE:
    {
        if (smoothed > sensor.peakValue)
        {
            sensor.peakValue = smoothed;
            sensor.peakTime = timestamp;
        }

        sensor.weightedSum += smoothed * timestamp;
        sensor.totalWeight += smoothed;

        float exitThreshold = max(sensor.threshold,
                                  sensor.peakValue * config.waveExitThreshold);
        bool exited = smoothed < exitThreshold;
        bool timedOut = (timestamp - sensor.waveStartTime) > config.maxWaveDurationMs;

        if (exited || timedOut)
        {
            sensor.waveState = WaveState::COMPLETE;
            sensor.waveEndTime = timestamp;
            sensor.centerOfMass = (sensor.totalWeight > 0)
                                      ? (uint32_t)(sensor.weightedSum / sensor.totalWeight)
                                      : sensor.peakTime;
        }
        break;
    }

    case WaveState::COMPLETE:
        // Expire stale completed waves that didn't pair into a module detection
        if (timestamp - sensor.waveEndTime > config.maxPeakGapMs)
        {
            sensor.resetWave();
        }
        break;
    }
}

bool DirectionDetector::isModuleDetected(int module) const
{
    int posA = module * 2;
    int posB = module * 2 + 1;

    if (sensors[posA].waveState != WaveState::COMPLETE ||
        sensors[posB].waveState != WaveState::COMPLETE)
        return false;

    uint32_t durA = sensors[posA].waveEndTime - sensors[posA].waveStartTime;
    uint32_t durB = sensors[posB].waveEndTime - sensors[posB].waveStartTime;
    if (durA < config.minWaveDurationMs || durB < config.minWaveDurationMs)
        return false;

    uint32_t peakGap = abs((int32_t)sensors[posA].peakTime - (int32_t)sensors[posB].peakTime);
    if (peakGap > config.maxPeakGapMs)
        return false;

    return true;
}

bool DirectionDetector::hasDetection() const
{
    if (!isReady())
        return false;

    for (int m = 0; m < 3; m++)
    {
        if (isModuleDetected(m))
            return true;
    }
    return false;
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
    result.waveDurationA = 0;
    result.waveDurationB = 0;
    result.baselineA = 0;
    result.baselineB = 0;
    result.thresholdA = 0;
    result.thresholdB = 0;
    result.detectedModule = 0;
    result.modulesDetected = 0;

    if (!hasDetection())
        return result;

    // Find all modules with valid detections
    int bestModule = -1;
    float bestSignal = 0;
    uint8_t modulesDetected = 0;
    Direction consensusDir = Direction::UNKNOWN;
    bool directionConsistent = true;

    for (int m = 0; m < 3; m++)
    {
        if (!isModuleDetected(m))
            continue;

        int posA = m * 2;
        int posB = m * 2 + 1;

        modulesDetected++;

        // Direction for this module: Side A (S1) saw it first → A_TO_B
        Direction dir;
        if (sensors[posA].centerOfMass < sensors[posB].centerOfMass)
            dir = Direction::A_TO_B;
        else if (sensors[posB].centerOfMass < sensors[posA].centerOfMass)
            dir = Direction::B_TO_A;
        else
            dir = (sensors[posA].peakTime < sensors[posB].peakTime)
                      ? Direction::A_TO_B
                      : Direction::B_TO_A;

        if (consensusDir == Direction::UNKNOWN)
            consensusDir = dir;
        else if (consensusDir != dir)
            directionConsistent = false;

        // Best module = strongest combined signal
        float signal = sensors[posA].peakValue + sensors[posB].peakValue;
        if (signal > bestSignal)
        {
            bestSignal = signal;
            bestModule = m;
        }
    }

    if (bestModule < 0)
        return result;

    int posA = bestModule * 2;
    int posB = bestModule * 2 + 1;

    result.direction = directionConsistent ? consensusDir : Direction::UNKNOWN;
    result.centerOfMassA = sensors[posA].centerOfMass;
    result.centerOfMassB = sensors[posB].centerOfMass;
    result.comGapMs = abs((int32_t)sensors[posA].centerOfMass -
                          (int32_t)sensors[posB].centerOfMass);
    result.maxSignalA = (uint16_t)sensors[posA].peakValue;
    result.maxSignalB = (uint16_t)sensors[posB].peakValue;
    result.waveDurationA = sensors[posA].waveEndTime - sensors[posA].waveStartTime;
    result.waveDurationB = sensors[posB].waveEndTime - sensors[posB].waveStartTime;
    result.thresholdA = sensors[posA].threshold;
    result.thresholdB = sensors[posB].threshold;
    result.detectedModule = bestModule + 1; // 1-indexed
    result.modulesDetected = modulesDetected;

    // Baseline from rolling buffer mean
    float sumA = 0, sumB = 0;
    for (size_t i = 0; i < sensors[posA].baselineBuffer.size(); i++)
        sumA += sensors[posA].baselineBuffer[i];
    for (size_t i = 0; i < sensors[posB].baselineBuffer.size(); i++)
        sumB += sensors[posB].baselineBuffer[i];
    result.baselineA = sensors[posA].baselineBuffer.size() > 0
                           ? sumA / sensors[posA].baselineBuffer.size()
                           : 0;
    result.baselineB = sensors[posB].baselineBuffer.size() > 0
                           ? sumB / sensors[posB].baselineBuffer.size()
                           : 0;

    // Confidence scoring
    float gapConfidence = min(1.0f, (float)result.comGapMs / 50.0f);
    float signalStrength = (sensors[posA].peakValue + sensors[posB].peakValue) / 2.0f;
    float signalConfidence = min(1.0f, signalStrength / 100.0f);
    float baseConfidence = (gapConfidence * 0.6f) + (signalConfidence * 0.4f);

    // Multi-module consensus boost
    if (modulesDetected >= 2 && directionConsistent)
        baseConfidence = min(1.0f, baseConfidence + 0.15f);
    if (modulesDetected >= 3 && directionConsistent)
        baseConfidence = min(1.0f, baseConfidence + 0.15f);

    result.confidence = baseConfidence;
    _detectedModule = bestModule;

    if (!serialStudioEnabled)
        Serial.printf("[Detector] Detection on M%d (%d modules agree): %s conf=%.2f\n",
                      bestModule + 1, modulesDetected,
                      directionToString(result.direction), result.confidence);

    return result;
}

void DirectionDetector::reset()
{
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        sensors[i].resetWave();
        sensors[i].smoothBuffer.clear();
    }
    _detectedModule = -1;
}

void DirectionDetector::fullReset()
{
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        sensors[i].fullReset();
    }
    _detectedModule = -1;
    _useCalibration = false;
}

bool DirectionDetector::isReady() const
{
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        if (!sensors[i].baselineReady)
            return false;
    }
    return true;
}

DetectorState DirectionDetector::getState() const
{
    if (!isReady())
        return DetectorState::ESTABLISHING_BASELINE;
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        if (sensors[i].waveState == WaveState::IN_WAVE)
            return DetectorState::DETECTING;
    }
    return DetectorState::READY;
}

void DirectionDetector::setConfig(const DetectorConfig &cfg)
{
    config = cfg;
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        if (sensors[i].baselineReady)
            recalculateThreshold(sensors[i], i);
    }
}

void DirectionDetector::setCalibration(const DeviceCalibration *cal)
{
    _calibration = cal;

    if (cal != nullptr && cal->isValid())
    {
        Serial.println("[DirectionDetector] Calibration data set");
        cal->debugPrint();
        for (int i = 0; i < NUM_SENSORS; i++)
        {
            if (sensors[i].baselineReady)
                recalculateThreshold(sensors[i], i);
        }
    }
    else
    {
        _useCalibration = false;
        Serial.println("[DirectionDetector] Calibration cleared");
    }
}

// Per-sensor telemetry accessors
float DirectionDetector::getSensorThreshold(uint8_t position) const
{
    if (position >= NUM_SENSORS)
        return 0;
    return sensors[position].threshold;
}

float DirectionDetector::getSensorSmoothed(uint8_t position) const
{
    if (position >= NUM_SENSORS)
        return 0;
    return sensors[position].smoothBuffer.getSmoothedAverage(config.smoothingWindow);
}

WaveState DirectionDetector::getSensorWaveState(uint8_t position) const
{
    if (position >= NUM_SENSORS)
        return WaveState::IDLE;
    return sensors[position].waveState;
}

// Legacy telemetry — returns data from best detected module, falling back to module 0
float DirectionDetector::getSmoothedA() const
{
    int m = (_detectedModule >= 0) ? _detectedModule : 0;
    return sensors[m * 2].smoothBuffer.getSmoothedAverage(config.smoothingWindow);
}

float DirectionDetector::getSmoothedB() const
{
    int m = (_detectedModule >= 0) ? _detectedModule : 0;
    return sensors[m * 2 + 1].smoothBuffer.getSmoothedAverage(config.smoothingWindow);
}

float DirectionDetector::getThresholdA() const
{
    int m = (_detectedModule >= 0) ? _detectedModule : 0;
    return sensors[m * 2].threshold;
}

float DirectionDetector::getThresholdB() const
{
    int m = (_detectedModule >= 0) ? _detectedModule : 0;
    return sensors[m * 2 + 1].threshold;
}

WaveState DirectionDetector::getWaveStateA() const
{
    int m = (_detectedModule >= 0) ? _detectedModule : 0;
    return sensors[m * 2].waveState;
}

WaveState DirectionDetector::getWaveStateB() const
{
    int m = (_detectedModule >= 0) ? _detectedModule : 0;
    return sensors[m * 2 + 1].waveState;
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
    Serial.println("=== DirectionDetector State (Per-Sensor) ===");
    Serial.printf("Overall state: %s\n",
                  getState() == DetectorState::ESTABLISHING_BASELINE ? "ESTABLISHING_BASELINE"
                  : getState() == DetectorState::READY               ? "READY"
                                                                     : "DETECTING");
    Serial.printf("Calibration: %s\n", _useCalibration ? "ACTIVE" : "FALLBACK");

    for (int i = 0; i < NUM_SENSORS; i++)
    {
        const SensorTracker &s = sensors[i];
        int module = i / 2 + 1;
        const char *side = (i % 2 == 0) ? "A(S1)" : "B(S2)";

        Serial.printf("  M%d-%s [pos %d]: baseline=%s thresh=%.1f wave=%s\n",
                      module, side, i,
                      s.baselineReady ? "OK" : "building",
                      s.threshold,
                      s.waveState == WaveState::IDLE     ? "IDLE"
                      : s.waveState == WaveState::IN_WAVE ? "IN_WAVE"
                                                          : "COMPLETE");
    }
}

#include "SerialStudioOutput.h"

void SerialStudioOutput::begin(
    std::vector<SensorReading, PSRAMAllocator<SensorReading>> *buffer,
    DirectionDetector *detector)
{
    _buffer = buffer;
    _detector = detector;
    resetIndex();
}

void SerialStudioOutput::cacheDetection(const DetectionResult &result)
{
    _cachedDirection = result.direction;
    _cachedConfidence = result.confidence;
    _cacheTime = millis();
}

void SerialStudioOutput::update()
{
    if (!_enabled || !_buffer)
        return;

    size_t bufferSize = _buffer->size();

    // Buffer index safety: detect external buffer clears
    if (bufferSize < _lastProcessedIndex)
    {
        resetIndex();
        bufferSize = _buffer->size();
    }

    if (bufferSize == 0 || _lastProcessedIndex >= bufferSize)
        return;

    // Expire cached detection result
    if (_cachedDirection != Direction::UNKNOWN &&
        millis() - _cacheTime > CACHE_TIMEOUT_MS)
    {
        _cachedDirection = Direction::UNKNOWN;
        _cachedConfidence = 0.0f;
    }

    for (size_t i = _lastProcessedIndex; i < bufferSize; i++)
    {
        const SensorReading &reading = (*_buffer)[i];

        if (!_hasPendingFrame)
        {
            resetAccumulator(reading.timestamp_us);
        }
        else if (reading.timestamp_us != _currentTimestamp)
        {
            emitFrame();
            resetAccumulator(reading.timestamp_us);
        }

        if (reading.position < NUM_SENSORS)
        {
            _accumulator[reading.position] = reading.proximity;
            _slotFilled[reading.position] = true;
        }
    }

    _lastProcessedIndex = bufferSize;
}

void SerialStudioOutput::emitFrame()
{
    if (!_hasPendingFrame)
        return;

    if (_emitTelemetry && _detector)
    {
        // Full frame: 7 sensor fields + 9 telemetry fields = 16 total
        int detState = 0;
        DetectorState ds = _detector->getState();
        if (ds == DetectorState::READY)
            detState = 1;
        else if (ds == DetectorState::DETECTING)
            detState = 2;

        Serial.printf("/*%lu,%u,%u,%u,%u,%u,%u,%.1f,%.1f,%.1f,%.1f,%d,%d,%d,%d,%.1f*/\n",
                      _currentTimestamp,
                      _accumulator[0], _accumulator[1],
                      _accumulator[2], _accumulator[3],
                      _accumulator[4], _accumulator[5],
                      _detector->getSmoothedA(),
                      _detector->getSmoothedB(),
                      _detector->getThresholdA(),
                      _detector->getThresholdB(),
                      (int)_detector->getWaveStateA(),
                      (int)_detector->getWaveStateB(),
                      detState,
                      (int)_cachedDirection,
                      _cachedConfidence);
    }
    else
    {
        // Basic frame: sensor data only
        Serial.printf("/*%lu,%u,%u,%u,%u,%u,%u*/\n",
                      _currentTimestamp,
                      _accumulator[0], _accumulator[1],
                      _accumulator[2], _accumulator[3],
                      _accumulator[4], _accumulator[5]);
    }
}

void SerialStudioOutput::resetAccumulator(uint32_t newTimestamp)
{
    _currentTimestamp = newTimestamp;
    memset(_accumulator, 0, sizeof(_accumulator));
    memset(_slotFilled, 0, sizeof(_slotFilled));
    _hasPendingFrame = true;
}

void SerialStudioOutput::resetIndex()
{
    _lastProcessedIndex = 0;
    _hasPendingFrame = false;
    memset(_accumulator, 0, sizeof(_accumulator));
    memset(_slotFilled, 0, sizeof(_slotFilled));
    _currentTimestamp = 0;
}

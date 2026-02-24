#include "SerialStudioOutput.h"

void SerialStudioOutput::begin(
    std::vector<SensorReading, PSRAMAllocator<SensorReading>> *buffer,
    DirectionDetector *detector)
{
    _buffer = buffer;
    _detector = detector;
    _rateWindowStart = millis();
    _pollCount = 0;
    _pollRate = 0;
    _sensorRate = 0;
    resetIndex();
}

void SerialStudioOutput::cacheDetection(const DetectionResult &result)
{
    _cachedDirection = result.direction;
    _cachedConfidence = result.confidence;

    // Estimate transit speed from wave duration and configured ball diameter
    uint32_t avgDurationMs = 0;
    if (result.waveDurationA > 0 && result.waveDurationB > 0)
        avgDurationMs = (result.waveDurationA + result.waveDurationB) / 2;
    else if (result.waveDurationA > 0)
        avgDurationMs = result.waveDurationA;
    else if (result.waveDurationB > 0)
        avgDurationMs = result.waveDurationB;

    if (avgDurationMs > 0 && _config)
    {
        float zoneMm = (float)_config->ball_diameter_mm;
        _cachedSpeedMs = zoneMm / (float)avgDurationMs; // mm/ms = m/s
    }
    else
    {
        _cachedSpeedMs = 0.0f;
    }

    _cachedPeakA = result.maxSignalA;
    _cachedPeakB = result.maxSignalB;
    _cachedWaveDurA = result.waveDurationA;
    _cachedWaveDurB = result.waveDurationB;
    _cachedComGap = result.comGapMs;
    _cachedDetModule = result.detectedModule;
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

    // Update rates every second
    unsigned long now = millis();
    if (now - _rateWindowStart >= 1000)
    {
        _pollRate = _pollCount;
        _pollCount = 0;
        _sensorRate = calculateSensorRate();
        _rateWindowStart = now;
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

    _pollCount++;

    uint16_t intTimeNum = _config ? _config->integration_time.toInt() : 0;
    uint16_t ledCurNum = _config ? _config->led_current.toInt() : 0;
    uint16_t dutyCycNum = 0;
    if (_config)
    {
        int slash = _config->duty_cycle.indexOf('/');
        dutyCycNum = (slash >= 0) ? _config->duty_cycle.substring(slash + 1).toInt() : _config->duty_cycle.toInt();
    }
    uint16_t multiPulseNum = _config ? _config->multi_pulse.toInt() : 0;

    if (_emitTelemetry && _detector)
    {
        Serial.printf("/*%lu,%u,%u,%u,%u,%u,%u,%.1f,%.1f,%.1f,%.1f,%.1f,%.1f,%d,%d,%.1f,%.1f,%u,%u,%u,%u,%u,%u,%u,%u,%lu,%lu,%lu*/\n",
                      _currentTimestamp,
                      _accumulator[0], _accumulator[1],
                      _accumulator[2], _accumulator[3],
                      _accumulator[4], _accumulator[5],
                      _detector->getSensorThreshold(0),
                      _detector->getSensorThreshold(1),
                      _detector->getSensorThreshold(2),
                      _detector->getSensorThreshold(3),
                      _detector->getSensorThreshold(4),
                      _detector->getSensorThreshold(5),
                      (int)_cachedDetModule,
                      (int)_cachedDirection,
                      _cachedConfidence,
                      _cachedSpeedMs,
                      _sensorRate,
                      _pollRate,
                      intTimeNum, ledCurNum, dutyCycNum, multiPulseNum,
                      _cachedPeakA, _cachedPeakB,
                      _cachedWaveDurA, _cachedWaveDurB,
                      _cachedComGap);
    }
    else
    {
        Serial.printf("/*%lu,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u,%u*/\n",
                      _currentTimestamp,
                      _accumulator[0], _accumulator[1],
                      _accumulator[2], _accumulator[3],
                      _accumulator[4], _accumulator[5],
                      _sensorRate,
                      _pollRate,
                      intTimeNum, ledCurNum, dutyCycNum, multiPulseNum);
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

uint16_t SerialStudioOutput::calculateSensorRate()
{
    if (!_config)
        return 0;

    // VCNL4040 integration time → pulse width in μs (T = 125 μs base unit)
    // Source: Vishay design guide oscilloscope measurement (designingvcnl4040.txt line 461)
    float it_us = 125.0f;
    String it = _config->integration_time;
    if (it == "1.5T") it_us = 187.5f;
    else if (it == "2T") it_us = 250.0f;
    else if (it == "2.5T") it_us = 312.5f;
    else if (it == "3T") it_us = 375.0f;
    else if (it == "3.5T") it_us = 437.5f;
    else if (it == "4T") it_us = 500.0f;
    else if (it == "8T") it_us = 1000.0f;

    // Duty cycle denominator (default 1/40)
    uint16_t duty_denom = 40;
    String dc = _config->duty_cycle;
    int slash = dc.indexOf('/');
    if (slash >= 0)
        duty_denom = dc.substring(slash + 1).toInt();
    if (duty_denom == 0)
        duty_denom = 40;

    float period_us = it_us * (float)duty_denom;
    return (uint16_t)(1000000.0f / period_us);
}

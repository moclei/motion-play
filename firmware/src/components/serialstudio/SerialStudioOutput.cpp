#include "SerialStudioOutput.h"

void SerialStudioOutput::begin(std::vector<SensorReading, PSRAMAllocator<SensorReading>> *buffer)
{
    _buffer = buffer;
    resetIndex();
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

    for (size_t i = _lastProcessedIndex; i < bufferSize; i++)
    {
        const SensorReading &reading = (*_buffer)[i];

        if (!_hasPendingFrame)
        {
            // First reading of a new cycle
            resetAccumulator(reading.timestamp_us);
        }
        else if (reading.timestamp_us != _currentTimestamp)
        {
            // Timestamp changed — emit the completed cycle, start a new one
            emitFrame();
            resetAccumulator(reading.timestamp_us);
        }

        // Store this reading's proximity in the appropriate slot
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

    // Serial Studio frame: /*timestamp_us,p1s1,p1s2,p2s1,p2s2,p3s1,p3s2*/
    Serial.printf("/*%lu,%u,%u,%u,%u,%u,%u*/\n",
                  _currentTimestamp,
                  _accumulator[0], _accumulator[1],
                  _accumulator[2], _accumulator[3],
                  _accumulator[4], _accumulator[5]);
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

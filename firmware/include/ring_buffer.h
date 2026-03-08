#pragma once

#include <Arduino.h>

/**
 * Generic fixed-size ring buffer for smoothing, baseline tracking, etc.
 * Stores up to SIZE elements; oldest elements are overwritten on overflow.
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

    float getMean() const
    {
        if (count == 0)
            return 0;
        float sum = 0;
        for (size_t i = 0; i < count; i++)
        {
            sum += buffer[(head - count + i + SIZE) % SIZE];
        }
        return sum / count;
    }

    float getMax() const
    {
        if (count == 0)
            return 0;
        float maxVal = buffer[(head - count + SIZE) % SIZE];
        for (size_t i = 1; i < count; i++)
        {
            float val = buffer[(head - count + i + SIZE) % SIZE];
            if (val > maxVal)
                maxVal = val;
        }
        return maxVal;
    }
};

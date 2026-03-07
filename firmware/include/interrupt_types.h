#pragma once

#include <Arduino.h>

#define INT_DEFAULT_THRESHOLD_MARGIN 10
#define INT_DEFAULT_HYSTERESIS 5

enum class InterruptEventType : uint8_t
{
    CLOSE,
    AWAY,
    UNKNOWN
};

struct InterruptEvent
{
    uint32_t timestamp_us;
    uint8_t boardId;
    uint8_t sensorId;
    InterruptEventType type;
    uint8_t rawFlags;

    String getSensorName() const
    {
        if (sensorId < 6)
        {
            uint8_t pcb = (sensorId / 2) + 1;
            uint8_t side = (sensorId % 2) + 1;
            return "P" + String(pcb) + "S" + String(side);
        }
        return "B" + String(boardId) + "?";
    }
};

enum class InterruptMode : uint8_t
{
    NORMAL,
    LOGIC_OUTPUT
};

struct InterruptConfig
{
    uint16_t thresholdMargin;
    uint16_t hysteresis;
    uint8_t persistence;
    bool smartPersistence;
    InterruptMode mode;
    uint16_t ledCurrent;
    uint8_t integrationTime;
    uint8_t multiPulse;
    bool autoCalibrate;

    static InterruptConfig defaults()
    {
        return {
            INT_DEFAULT_THRESHOLD_MARGIN,
            INT_DEFAULT_HYSTERESIS,
            1,
            true,
            InterruptMode::NORMAL,
            200,
            8,
            8,
            true};
    }
};

struct InterruptSessionStats
{
    uint32_t totalEvents;
    uint32_t closeEvents;
    uint32_t awayEvents;
    uint32_t unknownEvents;
    uint32_t droppedEvents;
    uint32_t isrCount;
    uint32_t sessionStartTime;
};

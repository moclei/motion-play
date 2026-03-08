#pragma once

#include <Arduino.h>

#define NUM_SENSORS 6
#define SAMPLE_RATE_HZ 1000
#define SAMPLE_INTERVAL_US (1000000 / SAMPLE_RATE_HZ)

struct SensorReading
{
    uint32_t timestamp_us;
    uint8_t position;
    uint8_t pcb_id;
    uint8_t side;
    uint16_t proximity;
    uint16_t ambient;
};

struct SensorMetadata
{
    uint8_t position;
    uint8_t pcb_id;
    uint8_t side;
    bool active;
    String name;
};

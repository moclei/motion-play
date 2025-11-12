/**
 * Diagnostic Tools for Motion Play Sensor Analysis
 *
 * This file contains tools to capture and analyze sensor behavior
 * to diagnose false trigger issues and transient noise.
 */

#include <Arduino.h>
#include "diagnostics.h"

// Circular buffer for sensor readings
#define BUFFER_SIZE 200 // At 15ms intervals = 3 seconds of data
#define NUM_SENSORS 6

struct SensorReading
{
    uint32_t timestamp;
    uint16_t ambient[NUM_SENSORS];
    int16_t variation[NUM_SENSORS];
    bool triggered[NUM_SENSORS];
};

SensorReading reading_buffer[BUFFER_SIZE];
int buffer_index = 0;
bool buffer_full = false;
bool capture_active = false;
uint32_t capture_start_time = 0;

// Statistics tracking
struct SensorStats
{
    uint32_t drop_count;         // Number of times sensor dropped below threshold
    uint32_t spike_count;        // Number of times sensor spiked above threshold
    uint32_t simultaneous_drops; // Drops happening across multiple sensors at once
    int16_t max_drop;            // Largest negative variation seen
    int16_t max_spike;           // Largest positive variation seen
    uint32_t last_drop_time;     // When last drop occurred
} sensor_stats[NUM_SENSORS];

struct SystemStats
{
    uint32_t all_sensor_drop_count;   // All sensors dropped at same time
    uint32_t rapid_fluctuation_count; // Rapid back-and-forth variations
} system_stats;

void initDiagnostics()
{
    // Clear buffer
    for (int i = 0; i < BUFFER_SIZE; i++)
    {
        reading_buffer[i].timestamp = 0;
        for (int s = 0; s < NUM_SENSORS; s++)
        {
            reading_buffer[i].ambient[s] = 0;
            reading_buffer[i].variation[s] = 0;
            reading_buffer[i].triggered[s] = false;
        }
    }

    // Clear statistics
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        sensor_stats[i].drop_count = 0;
        sensor_stats[i].spike_count = 0;
        sensor_stats[i].simultaneous_drops = 0;
        sensor_stats[i].max_drop = 0;
        sensor_stats[i].max_spike = 0;
        sensor_stats[i].last_drop_time = 0;
    }

    system_stats.all_sensor_drop_count = 0;
    system_stats.rapid_fluctuation_count = 0;

    buffer_index = 0;
    buffer_full = false;

    Serial.println("✅ Diagnostics initialized");
}

void startCapture(uint32_t duration_ms)
{
    capture_active = true;
    capture_start_time = millis();
    buffer_index = 0;
    buffer_full = false;

    Serial.println("📊 STARTING CAPTURE");
    Serial.println("Duration: " + String(duration_ms) + "ms");
    Serial.println("Buffer size: " + String(BUFFER_SIZE) + " readings");
    Serial.println("Capturing sensor behavior...\n");
}

void recordReading(uint16_t ambient[], int16_t variation[], bool triggered[], uint16_t thresholds[])
{
    if (!capture_active)
        return;

    uint32_t now = millis();

    // Store in circular buffer
    reading_buffer[buffer_index].timestamp = now;
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        reading_buffer[buffer_index].ambient[i] = ambient[i];
        reading_buffer[buffer_index].variation[i] = variation[i];
        reading_buffer[buffer_index].triggered[i] = triggered[i];
    }

    // Update statistics
    int simultaneous_trigger_count = 0;
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        if (triggered[i])
        {
            simultaneous_trigger_count++;

            // Track drops vs spikes
            if (variation[i] < -thresholds[i])
            {
                sensor_stats[i].drop_count++;
                if (variation[i] < sensor_stats[i].max_drop)
                {
                    sensor_stats[i].max_drop = variation[i];
                }
                sensor_stats[i].last_drop_time = now;
            }
            else if (variation[i] > thresholds[i])
            {
                sensor_stats[i].spike_count++;
                if (variation[i] > sensor_stats[i].max_spike)
                {
                    sensor_stats[i].max_spike = variation[i];
                }
            }
        }
    }

    // Check for simultaneous drops (all sensors triggering at once)
    if (simultaneous_trigger_count >= 4)
    { // At least 4 sensors
        system_stats.all_sensor_drop_count++;
        Serial.println("⚠️  SIMULTANEOUS DROP DETECTED at " + String(now) + "ms - " +
                       String(simultaneous_trigger_count) + " sensors triggered");
    }

    // Advance buffer
    buffer_index++;
    if (buffer_index >= BUFFER_SIZE)
    {
        buffer_index = 0;
        buffer_full = true;
    }
}

void analyzeCapture()
{
    if (!capture_active)
        return;

    capture_active = false;

    Serial.println("\n" + String("=").substring(0, 70));
    Serial.println("📊 DIAGNOSTIC ANALYSIS RESULTS");
    Serial.println(String("=").substring(0, 70));

    // Calculate how many readings we captured
    int total_readings = buffer_full ? BUFFER_SIZE : buffer_index;
    Serial.println("Total readings captured: " + String(total_readings));
    Serial.println("Time span: ~" + String((total_readings * 15) / 1000.0, 1) + " seconds\n");

    // Per-sensor analysis
    Serial.println("--- PER-SENSOR STATISTICS ---");
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        String side = (i % 2 == 0) ? "A" : "B";
        Serial.println("\nSensor " + String(i) + " (Side " + side + "):");
        Serial.println("  Drops: " + String(sensor_stats[i].drop_count) +
                       " | Spikes: " + String(sensor_stats[i].spike_count));
        Serial.println("  Max drop: " + String(sensor_stats[i].max_drop) +
                       " | Max spike: " + String(sensor_stats[i].max_spike));

        // Calculate trigger rate
        float trigger_rate = (sensor_stats[i].drop_count + sensor_stats[i].spike_count) * 100.0 / total_readings;
        Serial.println("  Trigger rate: " + String(trigger_rate, 1) + "%");

        if (trigger_rate > 20)
        {
            Serial.println("  ⚠️  HIGH NOISE - Consider increasing threshold");
        }
        else if (trigger_rate > 10)
        {
            Serial.println("  ⚠️  MODERATE NOISE - May need filtering");
        }
    }

    // System-wide analysis
    Serial.println("\n--- SYSTEM-WIDE STATISTICS ---");
    Serial.println("Simultaneous drops (4+ sensors): " + String(system_stats.all_sensor_drop_count));

    if (system_stats.all_sensor_drop_count > 0)
    {
        Serial.println("⚠️  SYSTEM ISSUE DETECTED!");
        Serial.println("Multiple sensors dropping together suggests:");
        Serial.println("  • Power supply noise/glitches");
        Serial.println("  • I2C communication issues");
        Serial.println("  • Environmental lighting changes");
        Serial.println("  • Need for temporal filtering");
    }

    // Look for correlation patterns
    Serial.println("\n--- CORRELATION ANALYSIS ---");
    int side_a_triggers = sensor_stats[0].drop_count + sensor_stats[2].drop_count + sensor_stats[4].drop_count;
    int side_b_triggers = sensor_stats[1].drop_count + sensor_stats[3].drop_count + sensor_stats[5].drop_count;

    Serial.println("Side A total triggers: " + String(side_a_triggers));
    Serial.println("Side B total triggers: " + String(side_b_triggers));

    float ratio = (side_a_triggers + side_b_triggers) > 0 ? (float)abs(side_a_triggers - side_b_triggers) / (side_a_triggers + side_b_triggers) : 0;

    if (ratio < 0.1)
    {
        Serial.println("⚠️  BALANCED TRIGGERS - Likely noise, not directional motion");
    }
    else
    {
        Serial.println("✅ UNBALANCED TRIGGERS - May indicate actual detection or sensor bias");
    }

    // Recommendations
    Serial.println("\n--- RECOMMENDATIONS ---");
    if (system_stats.all_sensor_drop_count > total_readings * 0.05)
    {
        Serial.println("1. ADD TEMPORAL FILTERING - Require sustained variation (2-3 consecutive readings)");
        Serial.println("2. CHECK POWER SUPPLY - Measure for voltage fluctuations");
        Serial.println("3. INCREASE THRESHOLDS - Current values may be too sensitive");
    }

    if (side_a_triggers > 0 && side_b_triggers > 0 &&
        abs(side_a_triggers - side_b_triggers) < 3)
    {
        Serial.println("4. STRICTER DIRECTIONAL LOGIC - Too many simultaneous side triggers");
    }

    Serial.println(String("=").substring(0, 70) + "\n");
}

void dumpBufferToSerial()
{
    if (!buffer_full && buffer_index == 0)
    {
        Serial.println("⚠️  No data in buffer");
        return;
    }

    Serial.println("\n" + String("=").substring(0, 70));
    Serial.println("📋 RAW BUFFER DUMP");
    Serial.println(String("=").substring(0, 70));
    Serial.println("Format: Time(ms), S0_Amb, S0_Var, S1_Amb, S1_Var, ..., S5_Amb, S5_Var");
    Serial.println("Triggered sensors marked with *\n");

    int total_readings = buffer_full ? BUFFER_SIZE : buffer_index;
    int start_index = buffer_full ? buffer_index : 0;

    for (int i = 0; i < total_readings; i++)
    {
        int idx = (start_index + i) % BUFFER_SIZE;
        SensorReading &r = reading_buffer[idx];

        Serial.print(String(r.timestamp) + ",");

        for (int s = 0; s < NUM_SENSORS; s++)
        {
            Serial.print(String(r.ambient[s]) + ",");
            Serial.print(String(r.variation[s]));
            if (r.triggered[s])
                Serial.print("*");
            if (s < NUM_SENSORS - 1)
                Serial.print(",");
        }
        Serial.println();
    }

    Serial.println(String("=").substring(0, 70) + "\n");
    Serial.println("💡 TIP: Copy this data to Excel/spreadsheet for graphing");
}

void printQuickStatus()
{
    Serial.println("\n--- QUICK DIAGNOSTIC STATUS ---");

    int total_triggers = 0;
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        total_triggers += sensor_stats[i].drop_count + sensor_stats[i].spike_count;
    }

    Serial.println("Total triggers: " + String(total_triggers));
    Serial.println("Simultaneous drops: " + String(system_stats.all_sensor_drop_count));

    if (system_stats.all_sensor_drop_count > 5)
    {
        Serial.println("⚠️  WARNING: Multiple simultaneous drops detected - likely noise");
    }
}

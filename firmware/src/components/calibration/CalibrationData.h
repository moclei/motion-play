/**
 * CalibrationData - Data structures for sensor calibration
 * 
 * Stores baseline (noise floor) and signal (object present) characteristics
 * for each PCB, enabling accurate threshold calculation.
 * 
 * Usage:
 *   DeviceCalibration cal;
 *   if (cal.isValid()) {
 *       uint16_t threshold = cal.pcbs[0].threshold;
 *   }
 */

#pragma once

#include <Arduino.h>

// Magic number for calibration validity check
#define CALIBRATION_MAGIC 0xCA11B123

// Current calibration data version
#define CALIBRATION_VERSION 1

// Number of PCBs to calibrate
#define CALIBRATION_NUM_PCBS 3

/**
 * Calibration data for a single PCB
 * Aggregates both sensors on the PCB
 */
struct PCBCalibration
{
    uint8_t pcb_id; // 1-3 (human-readable PCB number)

    // Baseline stats (noise floor - captured with nothing present)
    uint16_t baseline_min;    // Minimum reading during baseline period
    uint16_t baseline_max;    // Maximum reading (noise ceiling)
    uint16_t baseline_mean;   // Average reading
    uint16_t baseline_stddev; // Standard deviation (noise variability)

    // Signal stats (captured during approach/hold)
    uint16_t signal_min;  // Minimum reading during elevated period
    uint16_t signal_max;  // Maximum reading (peak)
    uint16_t signal_mean; // Average during elevated period

    // Derived threshold
    // Calculated as: baseline_max + ((signal_min - baseline_max) / 2)
    // This is halfway between noise ceiling and weakest real signal
    uint16_t threshold;

    // Validity flag
    bool valid;

    /**
     * Calculate threshold from captured data
     * Call this after baseline and signal stats are populated
     */
    void calculateThreshold()
    {
        if (signal_min > baseline_max)
        {
            // Halfway between noise ceiling and weakest signal
            threshold = baseline_max + ((signal_min - baseline_max) / 2);
        }
        else
        {
            // Signal overlaps with noise - use signal_min with small margin
            threshold = signal_min > 5 ? signal_min - 5 : 1;
        }
    }

    /**
     * Reset all values
     */
    void reset()
    {
        pcb_id = 0;
        baseline_min = 0;
        baseline_max = 0;
        baseline_mean = 0;
        baseline_stddev = 0;
        signal_min = 0;
        signal_max = 0;
        signal_mean = 0;
        threshold = 0;
        valid = false;
    }

    /**
     * Debug print
     */
    void debugPrint() const
    {
        Serial.printf("PCB%d: baseline=%d-%d (mean=%d, std=%d), signal=%d-%d (mean=%d), threshold=%d, valid=%s\n",
                      pcb_id,
                      baseline_min, baseline_max, baseline_mean, baseline_stddev,
                      signal_min, signal_max, signal_mean,
                      threshold,
                      valid ? "yes" : "no");
    }
};

/**
 * Complete device calibration data
 * Contains calibration for all PCBs plus metadata
 */
struct DeviceCalibration
{
    uint32_t magic;     // Validity marker (CALIBRATION_MAGIC)
    uint32_t version;   // Schema version
    uint32_t timestamp; // millis() when calibration was performed

    // Sensor configuration at calibration time
    // If these change, calibration may be invalid
    uint8_t multi_pulse;      // 1, 2, 4, or 8
    uint8_t integration_time; // 1, 2, 4, or 8 (for 1T, 2T, 4T, 8T)
    uint8_t led_current;      // LED current in mA (50-200)

    // Per-PCB calibration data
    PCBCalibration pcbs[CALIBRATION_NUM_PCBS];

    /**
     * Check if calibration data is valid
     */
    bool isValid() const
    {
        if (magic != CALIBRATION_MAGIC)
            return false;
        if (version != CALIBRATION_VERSION)
            return false;

        // All PCBs must be valid
        for (int i = 0; i < CALIBRATION_NUM_PCBS; i++)
        {
            if (!pcbs[i].valid)
                return false;
        }
        return true;
    }

    /**
     * Initialize with default/invalid values
     */
    void reset()
    {
        magic = 0;
        version = CALIBRATION_VERSION;
        timestamp = 0;
        multi_pulse = 1;
        integration_time = 1;
        led_current = 200;

        for (int i = 0; i < CALIBRATION_NUM_PCBS; i++)
        {
            pcbs[i].reset();
            pcbs[i].pcb_id = i + 1; // PCB IDs are 1-based
        }
    }

    /**
     * Mark calibration as complete and valid
     */
    void finalize()
    {
        magic = CALIBRATION_MAGIC;
        version = CALIBRATION_VERSION;
        timestamp = millis();
    }

    /**
     * Get threshold for a specific PCB
     * @param pcbIndex 0-based index (0-2)
     * @return threshold value, or 0 if invalid
     */
    uint16_t getThreshold(uint8_t pcbIndex) const
    {
        if (pcbIndex >= CALIBRATION_NUM_PCBS || !pcbs[pcbIndex].valid)
            return 0;
        return pcbs[pcbIndex].threshold;
    }

    /**
     * Debug print all calibration data
     */
    void debugPrint() const
    {
        Serial.println("=== Device Calibration ===");
        Serial.printf("Magic: 0x%08X (valid: %s)\n", magic, magic == CALIBRATION_MAGIC ? "yes" : "no");
        Serial.printf("Version: %d, Timestamp: %lu ms\n", version, timestamp);
        Serial.printf("Config at calibration: multi_pulse=%d, IT=%dT, LED=%dmA\n",
                      multi_pulse, integration_time, led_current);
        Serial.println("Per-PCB data:");
        for (int i = 0; i < CALIBRATION_NUM_PCBS; i++)
        {
            Serial.print("  ");
            pcbs[i].debugPrint();
        }
        Serial.printf("Overall valid: %s\n", isValid() ? "YES" : "NO");
    }
};

/**
 * Global calibration data instance
 * Stored in RAM for MVP, can be persisted to LittleFS later
 */
extern DeviceCalibration deviceCalibration;


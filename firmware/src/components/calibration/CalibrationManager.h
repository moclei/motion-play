/**
 * CalibrationManager - Guided Sensor Calibration Wizard
 *
 * Provides a step-by-step calibration process that:
 * 1. Captures baseline (noise floor) for each PCB
 * 2. Captures signal range (object present) for each PCB
 * 3. Calculates optimal thresholds for detection
 *
 * Calibration Flow:
 *   IDLE → INTRO → BASELINE_PCB1 → APPROACH_PCB1 →
 *                  BASELINE_PCB2 → APPROACH_PCB2 →
 *                  BASELINE_PCB3 → APPROACH_PCB3 → SUMMARY → COMPLETE
 *
 * Triggers:
 *   - Frontend: SET_MODE command with CALIBRATE mode
 *   - Physical: Hold Button 1 for 3 seconds
 *
 * Usage:
 *   CalibrationManager calMgr;
 *   calMgr.begin(&muxController);
 *
 *   // In main loop:
 *   calMgr.update();
 *
 *   // To start calibration:
 *   calMgr.startCalibration();
 */

#pragma once

#include <Arduino.h>
#include "CalibrationData.h"
#include "../mux/MuxController.h"
#include "../vcnl4040/VCNL4040.h"
#include "../display/DisplayManager.h"

// ============================================================================
// Configuration Constants
// ============================================================================

// Timing (milliseconds)
#define CAL_INTRO_DURATION_MS 3000        // Intro screen duration
#define CAL_BASELINE_DURATION_MS 600      // Baseline capture per PCB
#define CAL_APPROACH_TIMEOUT_MS 10000     // Max wait for user to approach
#define CAL_APPROACH_SUSTAIN_MS 500       // Sustained elevated readings needed
#define CAL_SUCCESS_DISPLAY_MS 1500       // Show success before next step
#define CAL_SUMMARY_MIN_DISPLAY_MS 2000   // Minimum summary display time

// Detection thresholds
#define CAL_ELEVATED_MULTIPLIER 2.0f      // Reading must be 2× baseline to count as elevated
#define CAL_MIN_ELEVATED_READING 10       // Minimum absolute reading to count as elevated

// Button configuration
#define CAL_BUTTON_HOLD_MS 3000           // Hold time to trigger calibration
#define CAL_BUTTON_1 14                   // T-Display Button 1 GPIO
#define CAL_BUTTON_2 0                    // T-Display Button 2 GPIO (BOOT)

// ============================================================================
// State Machine
// ============================================================================

enum class CalibrationState : uint8_t
{
    IDLE,             // Not calibrating
    INTRO,            // Showing intro screen
    BASELINE_PCB1,    // Capturing baseline for PCB 1
    APPROACH_PCB1,    // Waiting for approach on PCB 1
    BASELINE_PCB2,    // Capturing baseline for PCB 2
    APPROACH_PCB2,    // Waiting for approach on PCB 2
    BASELINE_PCB3,    // Capturing baseline for PCB 3
    APPROACH_PCB3,    // Waiting for approach on PCB 3
    SUMMARY,          // Showing summary
    COMPLETE,         // Calibration complete
    FAILED,           // Calibration failed
    CANCELLED         // User cancelled
};

// ============================================================================
// Statistics Accumulator
// ============================================================================

/**
 * Helper class to accumulate statistics during calibration
 */
class StatsAccumulator
{
public:
    void reset()
    {
        count = 0;
        sum = 0;
        sumSq = 0;
        minVal = UINT16_MAX;
        maxVal = 0;
    }

    void addSample(uint16_t value)
    {
        count++;
        sum += value;
        sumSq += (uint32_t)value * value;
        if (value < minVal)
            minVal = value;
        if (value > maxVal)
            maxVal = value;
    }

    uint16_t getMin() const { return count > 0 ? minVal : 0; }
    uint16_t getMax() const { return count > 0 ? maxVal : 0; }
    uint16_t getMean() const { return count > 0 ? (uint16_t)(sum / count) : 0; }

    uint16_t getStdDev() const
    {
        if (count < 2)
            return 0;
        uint32_t variance = (sumSq - (sum * sum / count)) / (count - 1);
        return (uint16_t)sqrt(variance);
    }

    uint32_t getCount() const { return count; }

private:
    uint32_t count = 0;
    uint32_t sum = 0;
    uint32_t sumSq = 0;
    uint16_t minVal = UINT16_MAX;
    uint16_t maxVal = 0;
};

// ============================================================================
// Calibration Manager Class
// ============================================================================

class CalibrationManager
{
public:
    CalibrationManager();

    /**
     * Initialize the calibration manager
     * @param mux Pointer to MuxController for sensor access
     * @param display Pointer to DisplayManager for UI rendering (optional)
     * @return true if successful
     */
    bool begin(MuxController *mux, DisplayManager *display = nullptr);

    /**
     * Update function - call every loop iteration
     * Handles state machine transitions and timing
     */
    void update();

    /**
     * Start the calibration wizard
     * @return true if calibration started
     */
    bool startCalibration();

    /**
     * Cancel ongoing calibration
     */
    void cancelCalibration();

    /**
     * Check if calibration is active
     */
    bool isActive() const { return _state != CalibrationState::IDLE; }

    /**
     * Check if calibration is in progress (not just showing results)
     */
    bool isInProgress() const
    {
        return _state != CalibrationState::IDLE &&
               _state != CalibrationState::COMPLETE &&
               _state != CalibrationState::FAILED &&
               _state != CalibrationState::CANCELLED;
    }

    /**
     * Get current calibration state
     */
    CalibrationState getState() const { return _state; }

    /**
     * Get state name for debugging
     */
    const char *getStateName() const;

    /**
     * Get current PCB being calibrated (1-3, or 0 if not calibrating a PCB)
     */
    uint8_t getCurrentPCB() const { return _currentPCB; }

    /**
     * Get progress percentage for current phase (0-100)
     */
    uint8_t getPhaseProgress() const;

    /**
     * Get current live reading (for display during approach phase)
     */
    uint16_t getCurrentReading() const { return _currentReading; }

    /**
     * Get time remaining in current phase (ms)
     */
    uint32_t getTimeRemaining() const;

    /**
     * Get the calibration result (valid after COMPLETE state)
     */
    DeviceCalibration &getCalibration() { return _calibration; }

    /**
     * Check for button hold to trigger calibration
     * Call this from main loop if you want button-triggered calibration
     * @return true if calibration was triggered
     */
    bool checkButtonTrigger();

    /**
     * Set sensor configuration for reading
     * Should be called before startCalibration with current sensor config
     */
    void setSensorConfig(uint8_t multiPulse, uint8_t integrationTime, uint8_t ledCurrent);

private:
    MuxController *_mux;
    DisplayManager *_display;
    VCNL4040 _sensor; // Temporary sensor instance for readings

    CalibrationState _state;
    uint8_t _currentPCB;        // 1-3 during calibration
    uint32_t _stateStartTime;   // When current state started
    uint32_t _elevatedStartTime; // When elevated readings started
    uint16_t _currentReading;   // Latest sensor reading
    bool _elevatedDetected;     // Have we seen elevated readings?

    // Button tracking
    uint32_t _buttonPressStart;
    bool _buttonWasPressed;

    // Statistics accumulators
    StatsAccumulator _baselineStats;
    StatsAccumulator _signalStats;

    // Working calibration data
    DeviceCalibration _calibration;

    // Sensor configuration
    uint8_t _multiPulse;
    uint8_t _integrationTime;
    uint8_t _ledCurrent;

    // State handlers
    void handleIntro();
    void handleBaseline();
    void handleApproach();
    void handleSummary();
    void handleComplete();
    void handleFailed();
    void handleCancelled();

    // Helpers
    void transitionTo(CalibrationState newState);
    bool readPCB(uint8_t pcbId, uint16_t &reading);
    void saveBaselineStats();
    void saveSignalStats();
    bool configureSensorForCalibration(uint8_t position);
    uint8_t getPCBForState(CalibrationState state) const;
    CalibrationState getNextState() const;
};

// Global instance (optional - can also be instantiated locally)
extern CalibrationManager calibrationManager;


/**
 * CalibrationManager - Guided Sensor Calibration Wizard
 *
 * Provides a step-by-step calibration process that:
 * 1. Captures baseline (noise floor) for each PCB
 * 2. Captures signal range (object present) for each PCB
 * 3. Calculates optimal thresholds for detection
 *
 * Calibration Flow:
 *   IDLE → INTRO → [BASELINE → APPROACH] × 3 PCBs → SUMMARY → COMPLETE
 *
 * The active PCB is tracked by _currentPCB (1-3), not encoded in the state.
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
#include "../sensor/SensorManager.h"
#include "../display/CalibrationScreen.h"
#include "pin_config.h"

// ============================================================================
// Configuration Constants
// ============================================================================

// Timing
static constexpr uint32_t CAL_INTRO_DURATION_MS      = 3000;
static constexpr uint32_t CAL_BASELINE_DURATION_MS    = 600;
static constexpr uint32_t CAL_APPROACH_TIMEOUT_MS     = 10000;
static constexpr uint32_t CAL_APPROACH_SUSTAIN_MS     = 500;
static constexpr uint32_t CAL_SUCCESS_DISPLAY_MS      = 1500;
static constexpr uint32_t CAL_SUMMARY_MIN_DISPLAY_MS  = 2000;

// Detection thresholds
static constexpr float    CAL_ELEVATED_MULTIPLIER     = 2.0f;
static constexpr uint16_t CAL_MIN_ELEVATED_READING    = 10;

// Button configuration (GPIOs from pin_config.h)
static constexpr uint32_t CAL_BUTTON_HOLD_MS          = 3000;
static constexpr uint8_t  CAL_BUTTON_TRIGGER          = PIN_BUTTON_2;  // BOOT button
static constexpr uint8_t  CAL_BUTTON_CANCEL           = PIN_BUTTON_1;  // Right button

// ============================================================================
// State Machine
// ============================================================================

enum class CalibrationState : uint8_t
{
    IDLE,       // Not calibrating
    INTRO,      // Showing intro screen
    BASELINE,   // Capturing baseline for _currentPCB
    APPROACH,   // Waiting for approach on _currentPCB
    SUMMARY,    // Showing summary
    COMPLETE,   // Calibration complete
    FAILED,     // Calibration failed
    CANCELLED   // User cancelled
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
        uint64_t variance = (sumSq - ((uint64_t)sum * sum / count)) / (count - 1);
        return (uint16_t)sqrt(variance);
    }

    uint32_t getCount() const { return count; }

private:
    uint32_t count = 0;
    uint32_t sum = 0;
    uint64_t sumSq = 0;
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
     * @param sensorMgr Pointer to SensorManager for sensor reading
     * @param calScreen Pointer to CalibrationScreen for UI rendering (optional)
     * @return true if successful
     */
    bool begin(SensorManager *sensorMgr, CalibrationScreen *calScreen = nullptr);

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
    SensorManager *_sensorMgr;
    CalibrationScreen *_calScreen;

    CalibrationState _state;
    uint8_t _currentPCB;        // 1-3 during calibration
    uint32_t _stateStartTime;   // When current state started
    uint32_t _elevatedStartTime; // When elevated readings started
    uint16_t _currentReading;   // Latest sensor reading
    bool _elevatedDetected;     // Have we seen elevated readings?

    // Button tracking
    uint32_t _buttonPressStart;
    bool _buttonWasPressed;

    // Render-once and rate-limit state (reset on each state transition)
    bool _phaseRendered;
    uint32_t _lastDisplayUpdate;
    uint32_t _lastReadFailLog;
    uint32_t _lastReadingLog;

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
    CalibrationState getNextState() const;
};

// Global instance (optional - can also be instantiated locally)
extern CalibrationManager calibrationManager;


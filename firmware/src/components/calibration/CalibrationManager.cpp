#include "CalibrationManager.h"

// Global instances
DeviceCalibration deviceCalibration;
CalibrationManager calibrationManager;

// ============================================================================
// Constructor and Initialization
// ============================================================================

CalibrationManager::CalibrationManager()
    : _sensorMgr(nullptr),
      _display(nullptr),
      _state(CalibrationState::IDLE),
      _currentPCB(0),
      _stateStartTime(0),
      _elevatedStartTime(0),
      _currentReading(0),
      _elevatedDetected(false),
      _buttonPressStart(0),
      _buttonWasPressed(false),
      _multiPulse(1),
      _integrationTime(1),
      _ledCurrent(200)
{
    _calibration.reset();
}

bool CalibrationManager::begin(SensorManager *sensorMgr, DisplayManager *display)
{
    if (sensorMgr == nullptr)
    {
        Serial.println("[CalibrationManager] ERROR: SensorManager is null");
        return false;
    }

    _sensorMgr = sensorMgr;
    _display = display;

    // Initialize button pins
    pinMode(CAL_BUTTON_TRIGGER, INPUT_PULLUP);
    pinMode(CAL_BUTTON_CANCEL, INPUT_PULLUP);

    Serial.println("[CalibrationManager] Initialized (using SensorManager for readings)");
    return true;
}

void CalibrationManager::setSensorConfig(uint8_t multiPulse, uint8_t integrationTime, uint8_t ledCurrent)
{
    _multiPulse = multiPulse;
    _integrationTime = integrationTime;
    _ledCurrent = ledCurrent;
}

// ============================================================================
// Main Update Loop
// ============================================================================

void CalibrationManager::update()
{
    switch (_state)
    {
    case CalibrationState::IDLE:
        // Nothing to do
        break;

    case CalibrationState::INTRO:
        handleIntro();
        break;

    case CalibrationState::BASELINE_PCB1:
    case CalibrationState::BASELINE_PCB2:
    case CalibrationState::BASELINE_PCB3:
        handleBaseline();
        break;

    case CalibrationState::APPROACH_PCB1:
    case CalibrationState::APPROACH_PCB2:
    case CalibrationState::APPROACH_PCB3:
        handleApproach();
        break;

    case CalibrationState::SUMMARY:
        handleSummary();
        break;

    case CalibrationState::COMPLETE:
        handleComplete();
        break;

    case CalibrationState::FAILED:
        handleFailed();
        break;

    case CalibrationState::CANCELLED:
        handleCancelled();
        break;
    }

    // Check for cancel button during calibration (RIGHT button = GPIO 14)
    if (isInProgress() && digitalRead(CAL_BUTTON_CANCEL) == LOW)
    {
        Serial.println("[CalibrationManager] Cancel button pressed (GPIO 14)");
        cancelCalibration();
    }
}

// ============================================================================
// State Handlers
// ============================================================================

void CalibrationManager::handleIntro()
{
    uint32_t elapsed = millis() - _stateStartTime;

    // Only render once at the start of the state
    static bool introRendered = false;
    if (elapsed < 100 && !introRendered)
    {
        introRendered = true;
        if (_display)
        {
            _display->showCalibrationIntro();
        }
    }

    if (elapsed >= CAL_INTRO_DURATION_MS)
    {
        introRendered = false; // Reset for next time
        transitionTo(CalibrationState::BASELINE_PCB1);
    }
}

void CalibrationManager::handleBaseline()
{
    uint32_t elapsed = millis() - _stateStartTime;

    // Read sensors and accumulate stats
    uint16_t reading;
    if (readPCB(_currentPCB, reading))
    {
        _currentReading = reading;
        _baselineStats.addSample(reading);
    }

    // Update display every 50ms
    static uint32_t lastDisplayUpdate = 0;
    if (millis() - lastDisplayUpdate >= 50)
    {
        lastDisplayUpdate = millis();
        if (_display)
        {
            _display->showCalibrationBaseline(_currentPCB, getPhaseProgress());
        }
    }

    // Check if baseline capture is complete
    if (elapsed >= CAL_BASELINE_DURATION_MS)
    {
        saveBaselineStats();

        Serial.printf("[CalibrationManager] PCB%d baseline: min=%d, max=%d, mean=%d, stddev=%d (n=%lu)\n",
                      _currentPCB,
                      _baselineStats.getMin(),
                      _baselineStats.getMax(),
                      _baselineStats.getMean(),
                      _baselineStats.getStdDev(),
                      _baselineStats.getCount());

        transitionTo(getNextState());
    }
}

void CalibrationManager::handleApproach()
{
    uint32_t elapsed = millis() - _stateStartTime;

    // Read sensors
    uint16_t reading;
    if (!readPCB(_currentPCB, reading))
    {
        // Read failed - log periodically
        static uint32_t lastReadFailLog = 0;
        if (millis() - lastReadFailLog > 1000)
        {
            lastReadFailLog = millis();
            Serial.printf("[CalibrationManager] PCB%d: Read failed!\n", _currentPCB);
        }
        return;
    }
    _currentReading = reading;

    // Get the baseline max for this PCB
    uint8_t pcbIndex = _currentPCB - 1;
    uint16_t baselineMax = _calibration.pcbs[pcbIndex].baseline_max;

    // Check if reading is elevated (above threshold)
    float threshold = max((float)baselineMax * CAL_ELEVATED_MULTIPLIER,
                          (float)CAL_MIN_ELEVATED_READING);

    // Log readings periodically for debugging
    static uint32_t lastReadingLog = 0;
    if (millis() - lastReadingLog > 500)
    {
        lastReadingLog = millis();
        Serial.printf("[CalibrationManager] PCB%d: reading=%d, baseline_max=%d, threshold=%.0f\n",
                      _currentPCB, reading, baselineMax, threshold);
    }

    bool isElevated = (reading > threshold);

    if (isElevated)
    {
        if (!_elevatedDetected)
        {
            // First elevated reading
            _elevatedDetected = true;
            _elevatedStartTime = millis();
            _signalStats.reset();
            Serial.printf("[CalibrationManager] PCB%d: Elevated readings detected (reading=%d, threshold=%.0f)\n",
                          _currentPCB, reading, threshold);
        }

        // Accumulate signal stats
        _signalStats.addSample(reading);

        // Check if we have enough sustained elevated readings
        uint32_t elevatedDuration = millis() - _elevatedStartTime;
        if (elevatedDuration >= CAL_APPROACH_SUSTAIN_MS)
        {
            // Success! We have enough data
            saveSignalStats();

            Serial.printf("[CalibrationManager] PCB%d signal captured: min=%d, max=%d, mean=%d (n=%lu)\n",
                          _currentPCB,
                          _signalStats.getMin(),
                          _signalStats.getMax(),
                          _signalStats.getMean(),
                          _signalStats.getCount());

            // Calculate threshold for this PCB
            _calibration.pcbs[pcbIndex].calculateThreshold();
            _calibration.pcbs[pcbIndex].valid = true;

            Serial.printf("[CalibrationManager] PCB%d threshold calculated: %d\n",
                          _currentPCB,
                          _calibration.pcbs[pcbIndex].threshold);

            // Show success screen briefly
            if (_display)
            {
                _display->showCalibrationSuccess(_currentPCB);
            }
            delay(CAL_SUCCESS_DISPLAY_MS);

            transitionTo(getNextState());
            return;
        }
    }
    else
    {
        // Not elevated - reset if we were tracking
        if (_elevatedDetected)
        {
            // Lost elevation - but don't reset stats, might come back
            // Only reset if we drop significantly
            if (reading < baselineMax + 5)
            {
                _elevatedDetected = false;
                Serial.printf("[CalibrationManager] PCB%d: Elevation lost, resetting\n", _currentPCB);
            }
        }
    }

    // Update display every 100ms (more stable visually)
    static uint32_t lastDisplayUpdate = 0;
    if (millis() - lastDisplayUpdate >= 100)
    {
        lastDisplayUpdate = millis();
        if (_display)
        {
            // Show the threshold the user needs to exceed
            uint16_t displayThreshold = (uint16_t)threshold;
            _display->showCalibrationApproach(_currentPCB, _currentReading, displayThreshold, getPhaseProgress(), getTimeRemaining());
        }
    }

    // Check for timeout
    if (elapsed >= CAL_APPROACH_TIMEOUT_MS)
    {
        Serial.printf("[CalibrationManager] PCB%d: Approach timeout - SKIPPING (continuing to next)\n", _currentPCB);
        
        // Mark this PCB as invalid but continue
        _calibration.pcbs[pcbIndex].valid = false;
        
        // Show brief failure message
        if (_display)
        {
            _display->showCalibrationFailed(_currentPCB, "Timeout - skipping");
        }
        delay(1500); // Brief pause to show failure
        
        // Continue to next state instead of aborting
        transitionTo(getNextState());
    }
}

void CalibrationManager::handleSummary()
{
    uint32_t elapsed = millis() - _stateStartTime;

    // Render summary once
    static bool summaryRendered = false;
    if (!summaryRendered)
    {
        summaryRendered = true;
        if (_display)
        {
            _display->showCalibrationSummary(
                _calibration.pcbs[0].threshold,
                _calibration.pcbs[1].threshold,
                _calibration.pcbs[2].threshold,
                _calibration.pcbs[0].valid,
                _calibration.pcbs[1].valid,
                _calibration.pcbs[2].valid);
        }
    }

    // Wait for minimum display time, then wait for button press
    if (elapsed >= CAL_SUMMARY_MIN_DISPLAY_MS)
    {
        // Check for any button press to continue
        if (digitalRead(CAL_BUTTON_TRIGGER) == LOW || digitalRead(CAL_BUTTON_CANCEL) == LOW)
        {
            summaryRendered = false; // Reset for next calibration
            transitionTo(CalibrationState::COMPLETE);
        }
    }
}

void CalibrationManager::handleComplete()
{
    // Finalize calibration data
    _calibration.finalize();

    // Copy to global instance
    deviceCalibration = _calibration;

    Serial.println("[CalibrationManager] Calibration complete!");
    _calibration.debugPrint();

    // Show complete message
    if (_display)
    {
        _display->showCalibrationComplete();
    }

    // Return to idle
    _state = CalibrationState::IDLE;
}

void CalibrationManager::handleFailed()
{
    uint32_t elapsed = millis() - _stateStartTime;

    // Render failure screen once
    static bool failedRendered = false;
    if (!failedRendered)
    {
        failedRendered = true;
        if (_display)
        {
            _display->showCalibrationFailed(_currentPCB, "Timeout - no approach detected");
        }
    }

    // Wait for button press to acknowledge
    if (elapsed >= 1000) // Minimum display time
    {
        if (digitalRead(CAL_BUTTON_TRIGGER) == LOW || digitalRead(CAL_BUTTON_CANCEL) == LOW)
        {
            failedRendered = false; // Reset for next calibration
            _state = CalibrationState::IDLE;
        }
    }
}

void CalibrationManager::handleCancelled()
{
    // Show cancelled screen
    if (_display)
    {
        _display->showCalibrationCancelled();
    }
    
    delay(1500); // Brief display
    
    // Return to idle
    _state = CalibrationState::IDLE;
}

// ============================================================================
// Public Interface
// ============================================================================

bool CalibrationManager::startCalibration()
{
    if (_sensorMgr == nullptr)
    {
        Serial.println("[CalibrationManager] Cannot start: not initialized");
        return false;
    }

    if (isActive())
    {
        Serial.println("[CalibrationManager] Cannot start: already active");
        return false;
    }

    Serial.println("[CalibrationManager] Starting calibration wizard");

    // Reset calibration data
    _calibration.reset();
    _calibration.multi_pulse = _multiPulse;
    _calibration.integration_time = _integrationTime;
    _calibration.led_current = _ledCurrent;

    transitionTo(CalibrationState::INTRO);
    return true;
}

void CalibrationManager::cancelCalibration()
{
    if (isActive())
    {
        Serial.println("[CalibrationManager] Calibration cancelled");
        transitionTo(CalibrationState::CANCELLED);
    }
}

const char *CalibrationManager::getStateName() const
{
    switch (_state)
    {
    case CalibrationState::IDLE:
        return "IDLE";
    case CalibrationState::INTRO:
        return "INTRO";
    case CalibrationState::BASELINE_PCB1:
        return "BASELINE_PCB1";
    case CalibrationState::APPROACH_PCB1:
        return "APPROACH_PCB1";
    case CalibrationState::BASELINE_PCB2:
        return "BASELINE_PCB2";
    case CalibrationState::APPROACH_PCB2:
        return "APPROACH_PCB2";
    case CalibrationState::BASELINE_PCB3:
        return "BASELINE_PCB3";
    case CalibrationState::APPROACH_PCB3:
        return "APPROACH_PCB3";
    case CalibrationState::SUMMARY:
        return "SUMMARY";
    case CalibrationState::COMPLETE:
        return "COMPLETE";
    case CalibrationState::FAILED:
        return "FAILED";
    case CalibrationState::CANCELLED:
        return "CANCELLED";
    default:
        return "UNKNOWN";
    }
}

uint8_t CalibrationManager::getPhaseProgress() const
{
    uint32_t elapsed = millis() - _stateStartTime;
    uint32_t duration = 0;

    switch (_state)
    {
    case CalibrationState::INTRO:
        duration = CAL_INTRO_DURATION_MS;
        break;

    case CalibrationState::BASELINE_PCB1:
    case CalibrationState::BASELINE_PCB2:
    case CalibrationState::BASELINE_PCB3:
        duration = CAL_BASELINE_DURATION_MS;
        break;

    case CalibrationState::APPROACH_PCB1:
    case CalibrationState::APPROACH_PCB2:
    case CalibrationState::APPROACH_PCB3:
        // For approach, show progress of sustained reading if elevated
        if (_elevatedDetected)
        {
            uint32_t sustainedTime = millis() - _elevatedStartTime;
            return min(100, (int)(sustainedTime * 100 / CAL_APPROACH_SUSTAIN_MS));
        }
        return 0;

    default:
        return 100;
    }

    if (duration == 0)
        return 100;
    return min(100, (int)(elapsed * 100 / duration));
}

uint32_t CalibrationManager::getTimeRemaining() const
{
    uint32_t elapsed = millis() - _stateStartTime;

    switch (_state)
    {
    case CalibrationState::APPROACH_PCB1:
    case CalibrationState::APPROACH_PCB2:
    case CalibrationState::APPROACH_PCB3:
        if (elapsed >= CAL_APPROACH_TIMEOUT_MS)
            return 0;
        return CAL_APPROACH_TIMEOUT_MS - elapsed;

    default:
        return 0;
    }
}

bool CalibrationManager::checkButtonTrigger()
{
    bool buttonPressed = (digitalRead(CAL_BUTTON_TRIGGER) == LOW);

    if (buttonPressed && !_buttonWasPressed)
    {
        // Button just pressed
        _buttonPressStart = millis();
    }
    else if (buttonPressed && _buttonWasPressed)
    {
        // Button held
        if (millis() - _buttonPressStart >= CAL_BUTTON_HOLD_MS)
        {
            // Trigger calibration
            _buttonWasPressed = false; // Reset to prevent re-trigger
            return startCalibration();
        }
    }
    else if (!buttonPressed && _buttonWasPressed)
    {
        // Button released before trigger
        _buttonPressStart = 0;
    }

    _buttonWasPressed = buttonPressed;
    return false;
}

// ============================================================================
// Private Helpers
// ============================================================================

void CalibrationManager::transitionTo(CalibrationState newState)
{
    Serial.printf("[CalibrationManager] State: %s -> %s\n",
                  getStateName(), 
                  // Temporarily set state to get new name
                  [&]() { 
                      CalibrationState old = _state;
                      _state = newState;
                      const char* name = getStateName();
                      _state = old;
                      return name;
                  }());

    _state = newState;
    _stateStartTime = millis();
    _elevatedDetected = false;
    _elevatedStartTime = 0;
    _currentReading = 0;

    // Reset stats at start of baseline phases
    switch (newState)
    {
    case CalibrationState::BASELINE_PCB1:
        _currentPCB = 1;
        _baselineStats.reset();
        break;
    case CalibrationState::BASELINE_PCB2:
        _currentPCB = 2;
        _baselineStats.reset();
        break;
    case CalibrationState::BASELINE_PCB3:
        _currentPCB = 3;
        _baselineStats.reset();
        break;
    case CalibrationState::APPROACH_PCB1:
        _currentPCB = 1;
        _signalStats.reset();
        break;
    case CalibrationState::APPROACH_PCB2:
        _currentPCB = 2;
        _signalStats.reset();
        break;
    case CalibrationState::APPROACH_PCB3:
        _currentPCB = 3;
        _signalStats.reset();
        break;
    default:
        break;
    }
}

bool CalibrationManager::readPCB(uint8_t pcbId, uint16_t &reading)
{
    if (pcbId < 1 || pcbId > 3 || _sensorMgr == nullptr)
        return false;

    // PCB ID is 1-based, but sensor positions are 0-based
    // Each PCB has 2 sensors: positions (pcbId-1)*2 and (pcbId-1)*2+1
    uint8_t pos1 = (pcbId - 1) * 2;     // S1
    uint8_t pos2 = (pcbId - 1) * 2 + 1; // S2

    uint16_t reading1 = 0, reading2 = 0;
    bool success1 = false, success2 = false;

    // Use SensorManager to read sensors (already initialized and configured)
    SensorReading sr1, sr2;
    
    if (_sensorMgr->readSensor(pos1, sr1))
    {
        reading1 = sr1.proximity;
        success1 = true;
    }

    if (_sensorMgr->readSensor(pos2, sr2))
    {
        reading2 = sr2.proximity;
        success2 = true;
    }

    if (!success1 && !success2)
    {
        Serial.printf("[CalibrationManager] Failed to read PCB%d sensors (S1=%s, S2=%s)\n", 
                      pcbId, success1 ? "ok" : "fail", success2 ? "ok" : "fail");
        return false;
    }

    // Aggregate readings (sum of both sensors)
    reading = reading1 + reading2;
    return true;
}

void CalibrationManager::saveBaselineStats()
{
    uint8_t pcbIndex = _currentPCB - 1;
    if (pcbIndex >= CALIBRATION_NUM_PCBS)
        return;

    _calibration.pcbs[pcbIndex].baseline_min = _baselineStats.getMin();
    _calibration.pcbs[pcbIndex].baseline_max = _baselineStats.getMax();
    _calibration.pcbs[pcbIndex].baseline_mean = _baselineStats.getMean();
    _calibration.pcbs[pcbIndex].baseline_stddev = _baselineStats.getStdDev();
}

void CalibrationManager::saveSignalStats()
{
    uint8_t pcbIndex = _currentPCB - 1;
    if (pcbIndex >= CALIBRATION_NUM_PCBS)
        return;

    _calibration.pcbs[pcbIndex].signal_min = _signalStats.getMin();
    _calibration.pcbs[pcbIndex].signal_max = _signalStats.getMax();
    _calibration.pcbs[pcbIndex].signal_mean = _signalStats.getMean();
}

bool CalibrationManager::configureSensorForCalibration(uint8_t position)
{
    // No configuration needed - SensorManager already has sensors configured
    // This function is kept for compatibility but does nothing
    return true;
}

uint8_t CalibrationManager::getPCBForState(CalibrationState state) const
{
    switch (state)
    {
    case CalibrationState::BASELINE_PCB1:
    case CalibrationState::APPROACH_PCB1:
        return 1;
    case CalibrationState::BASELINE_PCB2:
    case CalibrationState::APPROACH_PCB2:
        return 2;
    case CalibrationState::BASELINE_PCB3:
    case CalibrationState::APPROACH_PCB3:
        return 3;
    default:
        return 0;
    }
}

CalibrationState CalibrationManager::getNextState() const
{
    switch (_state)
    {
    case CalibrationState::INTRO:
        return CalibrationState::BASELINE_PCB1;
    case CalibrationState::BASELINE_PCB1:
        return CalibrationState::APPROACH_PCB1;
    case CalibrationState::APPROACH_PCB1:
        return CalibrationState::BASELINE_PCB2;
    case CalibrationState::BASELINE_PCB2:
        return CalibrationState::APPROACH_PCB2;
    case CalibrationState::APPROACH_PCB2:
        return CalibrationState::BASELINE_PCB3;
    case CalibrationState::BASELINE_PCB3:
        return CalibrationState::APPROACH_PCB3;
    case CalibrationState::APPROACH_PCB3:
        return CalibrationState::SUMMARY;
    case CalibrationState::SUMMARY:
        return CalibrationState::COMPLETE;
    default:
        return CalibrationState::IDLE;
    }
}


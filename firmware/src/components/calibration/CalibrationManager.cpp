#include "CalibrationManager.h"

// Per-module constants (CalibrationManager)
static constexpr uint32_t CAL_DISPLAY_UPDATE_INTERVAL_MS   = 50;
static constexpr uint32_t CAL_APPROACH_DISPLAY_INTERVAL_MS = 100;
static constexpr uint32_t CAL_READING_LOG_INTERVAL_MS      = 500;
static constexpr uint32_t CAL_READ_FAIL_LOG_INTERVAL_MS    = 1000;
static constexpr uint32_t CAL_FAILED_MIN_DISPLAY_MS        = 1000;
static constexpr uint32_t CAL_TIMEOUT_SKIP_DISPLAY_MS      = 1500;
static constexpr uint32_t CAL_CANCELLED_DISPLAY_MS         = 1500;

// Global instances
DeviceCalibration deviceCalibration;
CalibrationManager calibrationManager;

static const char *stateToName(CalibrationState state)
{
    switch (state)
    {
    case CalibrationState::IDLE:      return "IDLE";
    case CalibrationState::INTRO:     return "INTRO";
    case CalibrationState::BASELINE:  return "BASELINE";
    case CalibrationState::APPROACH:  return "APPROACH";
    case CalibrationState::SUMMARY:   return "SUMMARY";
    case CalibrationState::COMPLETE:  return "COMPLETE";
    case CalibrationState::FAILED:    return "FAILED";
    case CalibrationState::CANCELLED: return "CANCELLED";
    default:                          return "UNKNOWN";
    }
}

// ============================================================================
// Constructor and Initialization
// ============================================================================

CalibrationManager::CalibrationManager()
    : _sensorMgr(nullptr),
      _calScreen(nullptr),
      _state(CalibrationState::IDLE),
      _currentPCB(0),
      _stateStartTime(0),
      _elevatedStartTime(0),
      _currentReading(0),
      _elevatedDetected(false),
      _buttonPressStart(0),
      _buttonWasPressed(false),
      _phaseRendered(false),
      _lastDisplayUpdate(0),
      _lastReadFailLog(0),
      _lastReadingLog(0),
      _multiPulse(1),
      _integrationTime(1),
      _ledCurrent(CAL_DEFAULT_LED_CURRENT)
{
    _calibration.reset();
}

bool CalibrationManager::begin(SensorManager *sensorMgr, CalibrationScreen *calScreen)
{
    if (sensorMgr == nullptr)
    {
        Serial.println("[CalibrationManager] ERROR: SensorManager is null");
        return false;
    }

    _sensorMgr = sensorMgr;
    _calScreen = calScreen;

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
        break;

    case CalibrationState::INTRO:
        handleIntro();
        break;

    case CalibrationState::BASELINE:
        handleBaseline();
        break;

    case CalibrationState::APPROACH:
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

    if (!_phaseRendered)
    {
        _phaseRendered = true;
        if (_calScreen)
        {
            _calScreen->showIntro();
        }
    }

    if (elapsed >= CAL_INTRO_DURATION_MS)
    {
        transitionTo(getNextState());
    }
}

void CalibrationManager::handleBaseline()
{
    uint32_t elapsed = millis() - _stateStartTime;

    uint16_t reading;
    if (readPCB(_currentPCB, reading))
    {
        _currentReading = reading;
        _baselineStats.addSample(reading);
    }

    if (millis() - _lastDisplayUpdate >= CAL_DISPLAY_UPDATE_INTERVAL_MS)
    {
        _lastDisplayUpdate = millis();
        if (_calScreen)
        {
            _calScreen->showBaseline(_currentPCB, getPhaseProgress());
        }
    }

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

    uint16_t reading;
    if (!readPCB(_currentPCB, reading))
    {
        if (millis() - _lastReadFailLog > CAL_READ_FAIL_LOG_INTERVAL_MS)
        {
            _lastReadFailLog = millis();
            Serial.printf("[CalibrationManager] PCB%d: Read failed!\n", _currentPCB);
        }
        return;
    }
    _currentReading = reading;

    uint8_t pcbIndex = _currentPCB - 1;
    uint16_t baselineMax = _calibration.pcbs[pcbIndex].baseline_max;

    float threshold = max((float)baselineMax * CAL_ELEVATED_MULTIPLIER,
                          (float)CAL_MIN_ELEVATED_READING);

    if (millis() - _lastReadingLog > CAL_READING_LOG_INTERVAL_MS)
    {
        _lastReadingLog = millis();
        Serial.printf("[CalibrationManager] PCB%d: reading=%d, baseline_max=%d, threshold=%.0f\n",
                      _currentPCB, reading, baselineMax, threshold);
    }

    bool isElevated = (reading > threshold);

    if (isElevated)
    {
        if (!_elevatedDetected)
        {
            _elevatedDetected = true;
            _elevatedStartTime = millis();
            _signalStats.reset();
            Serial.printf("[CalibrationManager] PCB%d: Elevated readings detected (reading=%d, threshold=%.0f)\n",
                          _currentPCB, reading, threshold);
        }

        _signalStats.addSample(reading);

        uint32_t elevatedDuration = millis() - _elevatedStartTime;
        if (elevatedDuration >= CAL_APPROACH_SUSTAIN_MS)
        {
            saveSignalStats();

            Serial.printf("[CalibrationManager] PCB%d signal captured: min=%d, max=%d, mean=%d (n=%lu)\n",
                          _currentPCB,
                          _signalStats.getMin(),
                          _signalStats.getMax(),
                          _signalStats.getMean(),
                          _signalStats.getCount());

            _calibration.pcbs[pcbIndex].calculateThreshold();
            _calibration.pcbs[pcbIndex].valid = true;

            Serial.printf("[CalibrationManager] PCB%d threshold calculated: %d\n",
                          _currentPCB,
                          _calibration.pcbs[pcbIndex].threshold);

            if (_calScreen)
            {
                _calScreen->showSuccess(_currentPCB);
            }
            delay(CAL_SUCCESS_DISPLAY_MS);

            transitionTo(getNextState());
            return;
        }
    }
    else
    {
        if (_elevatedDetected)
        {
            if (reading < baselineMax + CAL_OVERLAP_MARGIN)
            {
                _elevatedDetected = false;
                Serial.printf("[CalibrationManager] PCB%d: Elevation lost, resetting\n", _currentPCB);
            }
        }
    }

    if (millis() - _lastDisplayUpdate >= CAL_APPROACH_DISPLAY_INTERVAL_MS)
    {
        _lastDisplayUpdate = millis();
        if (_calScreen)
        {
            uint16_t displayThreshold = (uint16_t)threshold;
            _calScreen->showApproach(_currentPCB, _currentReading, displayThreshold, getPhaseProgress(), getTimeRemaining());
        }
    }

    if (elapsed >= CAL_APPROACH_TIMEOUT_MS)
    {
        Serial.printf("[CalibrationManager] PCB%d: Approach timeout - SKIPPING (continuing to next)\n", _currentPCB);
        
        _calibration.pcbs[pcbIndex].valid = false;
        
        if (_calScreen)
        {
            _calScreen->showFailed(_currentPCB, "Timeout - skipping");
        }
        delay(CAL_TIMEOUT_SKIP_DISPLAY_MS);
        
        transitionTo(getNextState());
    }
}

void CalibrationManager::handleSummary()
{
    uint32_t elapsed = millis() - _stateStartTime;

    if (!_phaseRendered)
    {
        _phaseRendered = true;
        if (_calScreen)
        {
            _calScreen->showSummary(
                _calibration.pcbs[0].threshold,
                _calibration.pcbs[1].threshold,
                _calibration.pcbs[2].threshold,
                _calibration.pcbs[0].valid,
                _calibration.pcbs[1].valid,
                _calibration.pcbs[2].valid);
        }
    }

    if (elapsed >= CAL_SUMMARY_MIN_DISPLAY_MS)
    {
        if (digitalRead(CAL_BUTTON_TRIGGER) == LOW || digitalRead(CAL_BUTTON_CANCEL) == LOW)
        {
            transitionTo(CalibrationState::COMPLETE);
        }
    }
}

void CalibrationManager::handleComplete()
{
    _calibration.finalize();

    deviceCalibration = _calibration;

    Serial.println("[CalibrationManager] Calibration complete!");
    _calibration.debugPrint();

    if (_calScreen)
    {
        _calScreen->showComplete();
    }

    _state = CalibrationState::IDLE;
}

void CalibrationManager::handleFailed()
{
    uint32_t elapsed = millis() - _stateStartTime;

    if (!_phaseRendered)
    {
        _phaseRendered = true;
        if (_calScreen)
        {
            _calScreen->showFailed(_currentPCB, "Timeout - no approach detected");
        }
    }

    if (elapsed >= CAL_FAILED_MIN_DISPLAY_MS)
    {
        if (digitalRead(CAL_BUTTON_TRIGGER) == LOW || digitalRead(CAL_BUTTON_CANCEL) == LOW)
        {
            _state = CalibrationState::IDLE;
        }
    }
}

void CalibrationManager::handleCancelled()
{
    if (_calScreen)
    {
        _calScreen->showCancelled();
    }
    
    delay(CAL_CANCELLED_DISPLAY_MS);
    
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

    _calibration.reset();
    _calibration.multi_pulse = _multiPulse;
    _calibration.integration_time = _integrationTime;
    _calibration.led_current = _ledCurrent;
    _currentPCB = 0;

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
    return stateToName(_state);
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

    case CalibrationState::BASELINE:
        duration = CAL_BASELINE_DURATION_MS;
        break;

    case CalibrationState::APPROACH:
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
    if (_state != CalibrationState::APPROACH)
        return 0;

    uint32_t elapsed = millis() - _stateStartTime;
    if (elapsed >= CAL_APPROACH_TIMEOUT_MS)
        return 0;
    return CAL_APPROACH_TIMEOUT_MS - elapsed;
}

bool CalibrationManager::checkButtonTrigger()
{
    bool buttonPressed = (digitalRead(CAL_BUTTON_TRIGGER) == LOW);

    if (buttonPressed && !_buttonWasPressed)
    {
        _buttonPressStart = millis();
    }
    else if (buttonPressed && _buttonWasPressed)
    {
        if (millis() - _buttonPressStart >= CAL_BUTTON_HOLD_MS)
        {
            _buttonWasPressed = false;
            return startCalibration();
        }
    }
    else if (!buttonPressed && _buttonWasPressed)
    {
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
    Serial.printf("[CalibrationManager] %s -> %s\n",
                  stateToName(_state), stateToName(newState));

    _state = newState;
    _stateStartTime = millis();
    _elevatedDetected = false;
    _elevatedStartTime = 0;
    _currentReading = 0;
    _phaseRendered = false;
    _lastDisplayUpdate = 0;
    _lastReadFailLog = 0;
    _lastReadingLog = 0;

    switch (newState)
    {
    case CalibrationState::BASELINE:
        _currentPCB++;
        _baselineStats.reset();
        break;
    case CalibrationState::APPROACH:
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

    uint8_t pos1 = (pcbId - 1) * 2;
    uint8_t pos2 = (pcbId - 1) * 2 + 1;

    uint16_t reading1 = 0, reading2 = 0;
    bool success1 = false, success2 = false;

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

CalibrationState CalibrationManager::getNextState() const
{
    switch (_state)
    {
    case CalibrationState::INTRO:
        return CalibrationState::BASELINE;
    case CalibrationState::BASELINE:
        return CalibrationState::APPROACH;
    case CalibrationState::APPROACH:
        return (_currentPCB < CALIBRATION_NUM_PCBS)
                   ? CalibrationState::BASELINE
                   : CalibrationState::SUMMARY;
    case CalibrationState::SUMMARY:
        return CalibrationState::COMPLETE;
    default:
        return CalibrationState::IDLE;
    }
}

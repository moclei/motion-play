/**
 * InterruptManager - Implementation
 *
 * See InterruptManager.h for documentation.
 */

#include "InterruptManager.h"

// Singleton instance for ISR access
InterruptManager *InterruptManager::_instance = nullptr;

// ============================================================================
// Constructor / Destructor
// ============================================================================

InterruptManager::InterruptManager()
    : _mux(), _config(InterruptConfig::defaults()), _monitoring(false), _eventQueue(nullptr), _processingTask(nullptr), _sessionStartUs(0), _calibrated(false)
{
    // Initialize stats
    memset(&_stats, 0, sizeof(_stats));

    // Initialize baselines
    memset(_baselines, 0, sizeof(_baselines));

    // Initialize ISR tracking
    for (int i = 0; i < MUX_NUM_BOARDS; i++)
    {
        _lastIsrTime[i] = 0;
        _isrPending[i] = false;
    }

    // Set singleton instance
    _instance = this;
}

InterruptManager::~InterruptManager()
{
    stopMonitoring();

    if (_eventQueue != nullptr)
    {
        vQueueDelete(_eventQueue);
        _eventQueue = nullptr;
    }

    if (_instance == this)
    {
        _instance = nullptr;
    }
}

// ============================================================================
// Initialization
// ============================================================================

bool InterruptManager::begin()
{
    Serial.println("InterruptManager: Initializing...");

    // Initialize MuxController
    if (!_mux.begin(PIN_IIC_SDA, PIN_IIC_SCL, 400000))
    {
        Serial.println("  ERROR: MuxController initialization failed");
        return false;
    }

    Serial.printf("  Found %d sensors\n", _mux.getActiveSensorCount());

    // Create event queue
    if (_eventQueue == nullptr)
    {
        _eventQueue = xQueueCreate(INT_EVENT_BUFFER_SIZE, sizeof(InterruptEvent));
        if (_eventQueue == nullptr)
        {
            Serial.println("  ERROR: Failed to create event queue");
            return false;
        }
    }

    // Configure GPIO pins as inputs with pull-up
    // The INT lines are active-low, open-drain with external pull-up
    pinMode(PIN_SENSOR_INT_1, INPUT_PULLUP);
    pinMode(PIN_SENSOR_INT_2, INPUT_PULLUP);
    pinMode(PIN_SENSOR_INT_3, INPUT_PULLUP);

    Serial.println("  GPIO pins configured");
    Serial.println("InterruptManager: Initialization complete");

    return true;
}

// ============================================================================
// Calibration
// ============================================================================

int InterruptManager::calibrateSensors()
{
    Serial.println("\n╔══════════════════════════════════════════════════════════════════════════════╗");
    Serial.println("║              INTERRUPT MODE CALIBRATION (MAX Baseline Detection)             ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ Measuring MAX noise level per sensor. Ensure NO objects near sensors!        ║");
    Serial.println("╚══════════════════════════════════════════════════════════════════════════════╝\n");

    int calibratedCount = 0;

    for (uint8_t pos = 0; pos < MUX_TOTAL_SENSORS; pos++)
    {
        if (!_mux.isSensorAvailable(pos))
        {
            _baselines[pos] = 0;
            continue;
        }

        if (!_mux.selectSensor(pos))
        {
            Serial.printf("  Sensor %d: Failed to select via MUX\n", pos);
            _baselines[pos] = 0;
            continue;
        }

        delay(5); // Allow MUX to settle

        VCNL4040 &sensor = _sensors[pos];

        // Initialize sensor with current settings (need it running to read baseline)
        if (!sensor.begin())
        {
            Serial.printf("  Sensor %d: begin() failed\n", pos);
            _baselines[pos] = 0;
            continue;
        }

        // Configure for baseline measurement (same settings as detection)
        sensor.setLEDCurrent(_config.ledCurrent);
        sensor.setProxIntegrationTime(_config.integrationTime);
        sensor.setIRDutyCycle(40);
        sensor.setProxResolution(16);
        sensor.setMultiPulse(_config.multiPulse);
        sensor.setProxCancellation(0); // No hardware cancellation - we'll use thresholds
        sensor.powerOnProximity(true);

        delay(50); // Allow sensor to stabilize

        // Take samples for 1 second, track MAX value
        uint16_t maxReading = 0;
        uint16_t minReading = 65535;
        uint32_t sum = 0;
        int sampleCount = 0;

        uint32_t startTime = millis();
        while (millis() - startTime < INT_CALIBRATION_DURATION_MS)
        {
            uint16_t reading = sensor.readProximity();
            if (reading > maxReading)
                maxReading = reading;
            if (reading < minReading)
                minReading = reading;
            sum += reading;
            sampleCount++;
            delay(INT_CALIBRATION_SAMPLE_INTERVAL_MS);
        }

        if (sampleCount == 0)
        {
            Serial.printf("  Sensor %d: No valid samples\n", pos);
            _baselines[pos] = 0;
            continue;
        }

        uint16_t avgReading = sum / sampleCount;
        uint16_t noiseRange = maxReading - minReading;

        // Use MAX as baseline - this ensures no noise triggers
        _baselines[pos] = maxReading;

        Serial.printf("  Sensor %d: samples=%d, min=%d, avg=%d, MAX=%d (noise range: %d) ✓\n",
                      pos, sampleCount, minReading, avgReading, maxReading, noiseRange);
        calibratedCount++;
    }

    _mux.disableAll();
    _calibrated = (calibratedCount > 0);

    Serial.printf("\nCalibration complete: %d sensors calibrated\n", calibratedCount);
    Serial.println("Thresholds will be set to MAX + margin (no false triggers from noise)\n");

    return calibratedCount;
}

uint16_t InterruptManager::getBaseline(uint8_t position) const
{
    if (position >= MUX_TOTAL_SENSORS)
        return 0;
    return _baselines[position];
}

// ============================================================================
// Configuration
// ============================================================================

bool InterruptManager::configure(const InterruptConfig &config)
{
    Serial.println("InterruptManager: Configuring sensors for interrupt mode...");

    _config = config;

    Serial.printf("  Threshold margin: %d (above baseline)\n", config.thresholdMargin);
    Serial.printf("  Hysteresis: %d\n", config.hysteresis);
    Serial.printf("  Persistence: %d\n", config.persistence);
    Serial.printf("  Smart persistence: %s\n", config.smartPersistence ? "enabled" : "disabled");
    Serial.printf("  Mode: %s\n", config.mode == InterruptMode::LOGIC_OUTPUT ? "logic output" : "normal");
    Serial.printf("  LED current: %dmA\n", config.ledCurrent);
    Serial.printf("  Integration time: %dT\n", config.integrationTime);
    Serial.printf("  Auto-calibrate: %s\n", config.autoCalibrate ? "yes" : "no");

    // Run calibration first if enabled
    if (config.autoCalibrate)
    {
        int calibrated = calibrateSensors();
        if (calibrated == 0)
        {
            Serial.println("WARNING: No sensors calibrated - detection may not work correctly");
        }
    }

    // Now configure each sensor with dynamic thresholds
    int configuredCount = 0;

    for (uint8_t pos = 0; pos < MUX_TOTAL_SENSORS; pos++)
    {
        if (!_mux.isSensorAvailable(pos))
        {
            continue;
        }

        if (configureSensor(pos))
        {
            configuredCount++;
            Serial.printf("  Sensor %d configured ✓\n", pos);
        }
        else
        {
            Serial.printf("  Sensor %d FAILED ✗\n", pos);
        }
    }

    // Clean up MUX state
    _mux.disableAll();

    Serial.printf("InterruptManager: %d sensors configured\n", configuredCount);
    return configuredCount > 0;
}

bool InterruptManager::configureSensor(uint8_t position)
{
    if (!_mux.selectSensor(position))
    {
        return false;
    }

    delay(5); // Allow MUX to settle

    // Initialize sensor using our enhanced library
    VCNL4040 &sensor = _sensors[position];
    if (!sensor.begin())
    {
        Serial.printf("    Sensor %d: begin() failed\n", position);
        return false;
    }

    // Configure proximity sensor settings for maximum range
    sensor.setLEDCurrent(_config.ledCurrent);
    sensor.setProxIntegrationTime(_config.integrationTime);
    sensor.setIRDutyCycle(40);                // 1/40 duty for fast response
    sensor.setProxResolution(16);             // 16-bit resolution
    sensor.setMultiPulse(_config.multiPulse); // Multi-pulse for stronger signal
    sensor.setProxCancellation(0);            // No hardware cancellation

    // NEW: Per-sensor threshold based on calibrated MAX baseline
    // High threshold = baseline_max + margin (ensures no noise triggers)
    // Low threshold = baseline_max + margin - hysteresis (for state reset)
    uint16_t baseline = _baselines[position];
    uint16_t highThresh = baseline + _config.thresholdMargin;
    uint16_t lowThresh = baseline + _config.thresholdMargin - _config.hysteresis;

    // Ensure low threshold is reasonable
    if (lowThresh < baseline)
        lowThresh = baseline;

    sensor.setProxHighThreshold(highThresh);
    sensor.setProxLowThreshold(lowThresh);

    Serial.printf("    Sensor %d: baseline=%d, HIGH=%d, LOW=%d\n",
                  position, baseline, highThresh, lowThresh);

    // Configure interrupt behavior
    sensor.setProxPersistence(_config.persistence);
    sensor.enableSmartPersistence(_config.smartPersistence);

    // Set interrupt type based on mode
    // Only trigger on CLOSE (object approaching) - simplifies detection
    // AWAY events are not needed for direction detection
    if (_config.mode == InterruptMode::LOGIC_OUTPUT)
    {
        // Logic output mode: INT stays low while object present
        sensor.enableProxLogicMode(true);
        sensor.setProxInterruptType(VCNL4040_PSInterrupt::CLOSE);
    }
    else
    {
        // Normal mode: interrupt fires on threshold crossing
        sensor.enableProxLogicMode(false);
        sensor.setProxInterruptType(VCNL4040_PSInterrupt::CLOSE);
    }

    // Clear any pending interrupts by reading the flag register
    sensor.readInterruptFlags();

    // Power on proximity sensor
    sensor.powerOnProximity(true);

    // Debug: verify configuration was written
    delay(5); // Allow registers to settle

    // Read back PS_CONF1_2 to verify interrupt enable
    uint16_t conf12 = sensor.readRegister(0x03); // PS_CONF1_2
    uint8_t psConf1 = conf12 & 0xFF;             // Low byte = PS_CONF1
    uint8_t psConf2 = (conf12 >> 8) & 0xFF;      // High byte = PS_CONF2
    uint8_t psIntBits = psConf2 & 0x03;          // Bits 1:0 = PS_INT
    uint8_t psItBits = (psConf1 >> 1) & 0x07;    // Bits 3:1 = PS_IT

    Serial.printf("    Sensor %d: PS_CONF1_2=0x%04X, PS_IT=%d, PS_INT=%d (%s) ✓\n",
                  position, conf12, psItBits,
                  psIntBits,
                  psIntBits == 1 ? "CLOSE only" : psIntBits == 2 ? "AWAY only"
                                              : psIntBits == 3   ? "BOTH"
                                                                 : "DISABLED");

    // Read thresholds back to verify
    uint16_t threshH = sensor.readRegister(0x07); // PS_THDH
    uint16_t threshL = sensor.readRegister(0x06); // PS_THDL
    Serial.printf("    Sensor %d: Verified thresholds: HIGH=%d, LOW=%d\n",
                  position, threshH, threshL);

    // Read current proximity value (should be below threshold if no object)
    uint16_t proxValue = sensor.readProximity();
    uint16_t margin = (proxValue < threshH) ? (threshH - proxValue) : 0;
    Serial.printf("    Sensor %d: Current proximity=%d (margin to threshold: %d)\n",
                  position, proxValue, margin);

    return true;
}

// ============================================================================
// Monitoring Control
// ============================================================================

bool InterruptManager::startMonitoring()
{
    if (_monitoring)
    {
        Serial.println("InterruptManager: Already monitoring");
        return true;
    }

    Serial.println("InterruptManager: Starting monitoring...");

    // Reset stats
    resetStats();
    _stats.sessionStartTime = millis();
    _sessionStartUs = micros();

    // Clear ISR pending flags
    for (int i = 0; i < MUX_NUM_BOARDS; i++)
    {
        _isrPending[i] = false;
        _lastIsrTime[i] = 0;
    }

    // Clear event queue
    clearEvents();

    // Create processing task
    BaseType_t result = xTaskCreatePinnedToCore(
        processingTaskFunc,
        "IntProcTask",
        4096, // Stack size
        this, // Parameter
        1,    // Priority (lower than sensor polling)
        &_processingTask,
        1 // Run on Core 1 (not the sensor core)
    );

    if (result != pdPASS)
    {
        Serial.println("  ERROR: Failed to create processing task");
        return false;
    }

    // Set monitoring flag BEFORE attaching interrupts
    _monitoring = true;

    // Print GPIO pin states before attaching (for debug)
    Serial.printf("  GPIO states before attach: INT1(GPIO%d)=%d, INT2(GPIO%d)=%d, INT3(GPIO%d)=%d\n",
                  PIN_SENSOR_INT_1, digitalRead(PIN_SENSOR_INT_1),
                  PIN_SENSOR_INT_2, digitalRead(PIN_SENSOR_INT_2),
                  PIN_SENSOR_INT_3, digitalRead(PIN_SENSOR_INT_3));

    // Attach GPIO interrupts
    // Using FALLING edge because INT is active-low
    //
    // HARDWARE MAPPING (from user's PCB design):
    //   GPIO 11 (PIN_SENSOR_INT_1) ← J6 ← TCA Channel 2 (Board 2)
    //   GPIO 12 (PIN_SENSOR_INT_2) ← J5 ← TCA Channel 1 (Board 1)
    //   GPIO 13 (PIN_SENSOR_INT_3) ← J4 ← TCA Channel 0 (Board 0)
    //
    attachInterrupt(digitalPinToInterrupt(PIN_SENSOR_INT_1), isrBoard3, FALLING); // GPIO11 → Board2
    attachInterrupt(digitalPinToInterrupt(PIN_SENSOR_INT_2), isrBoard2, FALLING); // GPIO12 → Board1
    attachInterrupt(digitalPinToInterrupt(PIN_SENSOR_INT_3), isrBoard1, FALLING); // GPIO13 → Board0

    Serial.println("InterruptManager: Monitoring started");
    return true;
}

void InterruptManager::stopMonitoring()
{
    if (!_monitoring)
    {
        return;
    }

    Serial.println("InterruptManager: Stopping monitoring...");

    // Clear monitoring flag first - this tells the task to exit
    _monitoring = false;

    // Detach GPIO interrupts
    detachInterrupt(digitalPinToInterrupt(PIN_SENSOR_INT_1));
    detachInterrupt(digitalPinToInterrupt(PIN_SENSOR_INT_2));
    detachInterrupt(digitalPinToInterrupt(PIN_SENSOR_INT_3));

    // Wait for the processing task to exit on its own
    // The task will self-delete when it sees _monitoring = false
    if (_processingTask != nullptr)
    {
        // Give task time to notice the flag and clean up
        int timeout = 50; // 500ms max wait
        while (_processingTask != nullptr && timeout > 0)
        {
            delay(10);
            timeout--;
        }

        // If task didn't exit gracefully, force delete (shouldn't happen)
        if (_processingTask != nullptr)
        {
            Serial.println("  WARNING: Task didn't exit gracefully, force deleting");
            vTaskDelete(_processingTask);
            _processingTask = nullptr;
        }
    }

    // Disable all sensors' interrupts
    for (uint8_t pos = 0; pos < MUX_TOTAL_SENSORS; pos++)
    {
        if (_mux.isSensorAvailable(pos))
        {
            if (_mux.selectSensor(pos))
            {
                delay(2);
                _sensors[pos].setProxInterruptType(VCNL4040_PSInterrupt::DISABLE);
                _sensors[pos].readInterruptFlags(); // Clear any pending
            }
        }
    }

    _mux.disableAll();

    Serial.println("InterruptManager: Monitoring stopped");
    Serial.printf("  Session stats: %lu events, %lu ISRs, %lu dropped\n",
                  _stats.totalEvents, _stats.isrCount, _stats.droppedEvents);
}

// ============================================================================
// Event Queue Management
// ============================================================================

bool InterruptManager::hasEvents() const
{
    if (_eventQueue == nullptr)
        return false;
    return uxQueueMessagesWaiting(_eventQueue) > 0;
}

bool InterruptManager::getNextEvent(InterruptEvent &event, uint32_t timeout_ms)
{
    if (_eventQueue == nullptr)
        return false;

    TickType_t ticks = (timeout_ms == 0) ? 0 : pdMS_TO_TICKS(timeout_ms);
    return xQueueReceive(_eventQueue, &event, ticks) == pdTRUE;
}

uint32_t InterruptManager::getEventCount() const
{
    if (_eventQueue == nullptr)
        return 0;
    return uxQueueMessagesWaiting(_eventQueue);
}

void InterruptManager::clearEvents()
{
    if (_eventQueue != nullptr)
    {
        xQueueReset(_eventQueue);
    }
}

void InterruptManager::resetStats()
{
    memset(&_stats, 0, sizeof(_stats));
}

bool InterruptManager::queueEvent(const InterruptEvent &event)
{
    if (_eventQueue == nullptr)
        return false;

    // Non-blocking send
    if (xQueueSend(_eventQueue, &event, 0) == pdTRUE)
    {
        return true;
    }

    _stats.droppedEvents++;
    return false;
}

// ============================================================================
// Interrupt Handling
// ============================================================================

void IRAM_ATTR InterruptManager::isrBoard1()
{
    handleIsr(0);
}

void IRAM_ATTR InterruptManager::isrBoard2()
{
    handleIsr(1);
}

void IRAM_ATTR InterruptManager::isrBoard3()
{
    handleIsr(2);
}

void IRAM_ATTR InterruptManager::handleIsr(uint8_t board)
{
    if (_instance == nullptr || !_instance->_monitoring)
    {
        return;
    }

    // Record timestamp and set pending flag
    // Keep ISR minimal - just record that something happened
    _instance->_lastIsrTime[board] = micros();
    _instance->_isrPending[board] = true;
    _instance->_stats.isrCount++;
}

// ============================================================================
// Processing Task
// ============================================================================

void InterruptManager::processingTaskFunc(void *param)
{
    InterruptManager *mgr = static_cast<InterruptManager *>(param);

    Serial.println("InterruptManager: Processing task started");

    uint32_t lastDebugPoll = 0;
    const uint32_t DEBUG_POLL_INTERVAL = 2000; // Poll every 2 seconds for debug

    while (mgr->_monitoring)
    {
        bool anyPending = false;

        // Check each board for pending interrupts
        for (uint8_t board = 0; board < MUX_NUM_BOARDS; board++)
        {
            if (mgr->_isrPending[board])
            {
                anyPending = true;

                // Clear pending flag (atomic on ESP32)
                mgr->_isrPending[board] = false;

                // Process this board's interrupt
                mgr->processBoard(board);
            }
        }

        // DEBUG: Periodically poll sensors to check if they're detecting anything
        uint32_t now = millis();
        if (now - lastDebugPoll > DEBUG_POLL_INTERVAL)
        {
            lastDebugPoll = now;

            // Read GPIO states
            Serial.printf("[DEBUG] GPIO: INT1=%d, INT2=%d, INT3=%d | ",
                          digitalRead(PIN_SENSOR_INT_1),
                          digitalRead(PIN_SENSOR_INT_2),
                          digitalRead(PIN_SENSOR_INT_3));

            // Find the first available sensor to poll
            // NOTE: We only read proximity, NOT interrupt flags (reading flags clears them!)
            bool polledSensor = false;
            for (uint8_t pos = 0; pos < MUX_TOTAL_SENSORS && !polledSensor; pos++)
            {
                if (mgr->_mux.isSensorAvailable(pos) && mgr->_mux.selectSensor(pos))
                {
                    delayMicroseconds(200);
                    uint16_t prox = mgr->_sensors[pos].readProximity();
                    Serial.printf("S%d: prox=%d\n", pos, prox);
                    polledSensor = true;
                }
            }
            if (!polledSensor)
            {
                Serial.println("No sensors available to poll");
            }
        }

        // If nothing pending, yield briefly
        // Use minimal delay to maximize responsiveness for direction detection
        if (!anyPending)
        {
            // Yield without delay - just let other tasks run briefly
            taskYIELD();
        }
    }

    Serial.println("InterruptManager: Processing task exiting");

    // Clear the task handle BEFORE deleting ourselves
    // This signals to stopMonitoring() that we're done
    mgr->_processingTask = nullptr;

    // Self-delete - this function never returns
    vTaskDelete(NULL);
}

void InterruptManager::processBoard(uint8_t board)
{
    // Calculate timestamp relative to session start
    uint32_t timestamp_us = _lastIsrTime[board] - _sessionStartUs;

    // Get positions of sensors on this board
    uint8_t sensor1 = board * 2;     // S1
    uint8_t sensor2 = board * 2 + 1; // S2

    // OPTIMIZED APPROACH for direction detection:
    // Check S1 first. If it has a flag, process it and RETURN IMMEDIATELY.
    // This clears the flag and allows GPIO to go HIGH, so if S2 triggers
    // shortly after, we'll get a NEW interrupt with a NEW timestamp.
    // This maximizes our chance of distinguishing S1 vs S2 timing.

    // Check sensor 1 first
    if (_mux.isSensorAvailable(sensor1))
    {
        if (_mux.selectSensor(sensor1))
        {
            delayMicroseconds(50); // Minimal settle time
            if (processSensor(sensor1, timestamp_us))
            {
                // S1 had a flag - we've cleared it
                // Return immediately to allow GPIO to reset for S2
                _mux.disableCurrentPCA();
                return;
            }
        }
    }

    // S1 didn't have a flag, check sensor 2
    if (_mux.isSensorAvailable(sensor2))
    {
        if (_mux.selectSensor(sensor2))
        {
            delayMicroseconds(50); // Minimal settle time
            if (processSensor(sensor2, timestamp_us))
            {
                // S2 had a flag - we've cleared it
                _mux.disableCurrentPCA();
                return;
            }
        }
    }

    // Neither sensor had flags set - create an "unknown" event
    // This can happen if the interrupt was very brief or already cleared
    InterruptEvent evt;
    evt.timestamp_us = timestamp_us;
    evt.boardId = board + 1;
    evt.sensorId = 255; // Unknown which sensor
    evt.type = InterruptEventType::UNKNOWN;
    evt.rawFlags = 0;

    queueEvent(evt);
    _stats.unknownEvents++;
    _stats.totalEvents++;

    // Clean up MUX state
    _mux.disableCurrentPCA();
}

bool InterruptManager::processSensor(uint8_t position, uint32_t timestamp_us)
{
    VCNL4040 &sensor = _sensors[position];

    // Read and clear interrupt flags
    VCNL4040_InterruptFlags flags = sensor.readInterruptFlags();

    // Check if any PS interrupt occurred
    if (!flags.psClose && !flags.psAway)
    {
        return false; // No interrupt from this sensor
    }

    // Create event
    InterruptEvent evt;
    evt.timestamp_us = timestamp_us;
    evt.boardId = (position / 2) + 1;
    evt.sensorId = position;
    evt.rawFlags = flags.raw;

    // Determine event type
    if (flags.psClose)
    {
        evt.type = InterruptEventType::CLOSE;
        _stats.closeEvents++;
    }
    else
    {
        evt.type = InterruptEventType::AWAY;
        _stats.awayEvents++;
    }

    // Queue the event
    queueEvent(evt);
    _stats.totalEvents++;

    return true;
}

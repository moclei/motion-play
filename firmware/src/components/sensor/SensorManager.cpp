#include "SensorManager.h"
#include "../session/SessionManager.h" // For SessionSummary full definition
#include "constants.h"
#include "debug_log.h"

SensorManager::SensorManager()
    : diagnostics(muxController, vcnl)
{
}


// ============================================================================
// PS_CANC Baseline Calibration
// The VCNL4040 has a built-in cancellation register (PS_CANC at 0x05) that
// automatically subtracts an offset from all proximity readings. This is
// designed to compensate for cover window reflections and other constant
// sources of IR reflection that would otherwise cause elevated baselines.
//
// See: Vishay Application Note "Designing the VCNL4040 Into an Application"
// and SENSOR_SPACING_AND_COVERS.md in docs/references/vcnl4040/
// ============================================================================

bool SensorManager::calibrateSensorBaseline(uint8_t sensorIndex)
{
    if (sensorIndex >= NUM_SENSORS || !muxController.isSensorAvailable(sensorIndex))
        return false;

    if (!muxController.selectSensor(sensorIndex))
    {
        Serial.printf("  Calibration: Failed to select sensor %d\n", sensorIndex);
        return false;
    }
    delay(5);

    const int NUM_SAMPLES = 50;
    const int SAMPLE_DELAY_MS = 10;
    uint32_t sum = 0;
    int validSamples = 0;

    for (int i = 0; i < NUM_SAMPLES; i++)
    {
        uint16_t proximity;
        if (vcnl.readRegister(VCNL4040_PS_DATA, proximity))
        {
            sum += proximity;
            validSamples++;
        }
        delay(SAMPLE_DELAY_MS);
    }

    if (validSamples < NUM_SAMPLES / 2)
    {
        Serial.printf("  Calibration: Too few valid samples (%d/%d)\n", validSamples, NUM_SAMPLES);
        return false;
    }

    uint16_t baseline = sum / validSamples;
    baselineValues[sensorIndex] = baseline;

    if (!vcnl.writeRegister(VCNL4040_PS_CANC, baseline))
    {
        Serial.println("  Calibration: Failed to write PS_CANC");
        return false;
    }

    delay(5);
    uint16_t verify_value = vcnl.readRegister(VCNL4040_PS_CANC);

    if (verify_value != baseline)
    {
        Serial.printf("  Calibration: PS_CANC verify failed (wrote %d, read %d)\n", baseline, verify_value);
        return false;
    }

    return true;
}

bool SensorManager::calibrateProximityCancellation()
{
    Serial.println("\n");
    Serial.println("╔══════════════════════════════════════════════════════════════════════════════╗");
    Serial.println("║              PS_CANC BASELINE CALIBRATION (Cover Offset Removal)             ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ This calibrates each sensor to cancel the constant offset caused by the      ║");
    Serial.println("║ acrylic cover windows. Ensure NO objects are near the sensors during this!   ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    int calibratedCount = 0;
    int failedCount = 0;

    for (int i = 0; i < NUM_SENSORS; i++)
    {
        SensorPosition pos = muxController.getSensorPosition(i);

        if (!muxController.isSensorAvailable(i))
        {
            Serial.printf("║ Sensor %d (P%dS%d): SKIPPED (not active)                                       ║\n",
                          i, pos.pcbId, pos.side);
            continue;
        }

        char sensorName[8];
        snprintf(sensorName, sizeof(sensorName), "P%dS%d", pos.pcbId, pos.side);

        Serial.printf("║ Sensor %d (%-4s): Calibrating...                                              ║\n", i, sensorName);

        if (calibrateSensorBaseline(i))
        {
            Serial.printf("║ Sensor %d (%-4s): ✓ Baseline = %5d (written to PS_CANC)                     ║\n",
                          i, sensorName, baselineValues[i]);
            calibratedCount++;
        }
        else
        {
            Serial.printf("║ Sensor %d (%-4s): ✗ CALIBRATION FAILED                                        ║\n",
                          i, sensorName);
            failedCount++;
        }

        // Feed watchdog between sensors
        taskYIELD();
    }

    muxController.disableAll();

    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.printf("║ RESULT: %d sensors calibrated, %d failed                                       ║\n",
                  calibratedCount, failedCount);
    Serial.println("║ Proximity readings will now have cover reflection offset subtracted.         ║");
    Serial.println("╚══════════════════════════════════════════════════════════════════════════════╝");
    Serial.println();

    return (failedCount == 0 && calibratedCount > 0);
}

uint16_t SensorManager::getBaselineValue(uint8_t sensorIndex)
{
    if (sensorIndex >= NUM_SENSORS)
        return 0;
    return baselineValues[sensorIndex];
}

uint16_t SensorManager::parseLEDCurrentMA(const String &current)
{
    if (current == "50mA")  return 50;
    if (current == "75mA")  return 75;
    if (current == "100mA") return 100;
    if (current == "120mA") return 120;
    if (current == "140mA") return 140;
    if (current == "160mA") return 160;
    if (current == "180mA") return 180;
    return 200;
}

uint8_t SensorManager::parseIntegrationTimeValue(const String &time)
{
    // Returns whole-T values directly, half-T values as ×10 encoding
    // (matches VCNL4040::setProxIntegrationTime encoding)
    if (time == "1T")   return 1;
    if (time == "1.5T") return 15;
    if (time == "2T")   return 2;
    if (time == "2.5T") return 25;
    if (time == "3T")   return 3;
    if (time == "3.5T") return 35;
    if (time == "4T")   return 4;
    if (time == "8T")   return 8;
    return 1;
}

uint16_t SensorManager::parseDutyCycleValue(const String &duty)
{
    if (duty == "1/40")  return 40;
    if (duty == "1/80")  return 80;
    if (duty == "1/160") return 160;
    if (duty == "1/320") return 320;
    return 40;
}

uint8_t SensorManager::parseMultiPulseCount(const String &mp)
{
    if (mp == "2") return 2;
    if (mp == "4") return 4;
    if (mp == "8") return 8;
    return 1;
}

bool SensorManager::applySensorConfig(uint8_t sensorIndex)
{
    if (sensorIndex >= NUM_SENSORS || activeConfig == nullptr)
        return false;

    uint16_t ledMA = parseLEDCurrentMA(activeConfig->led_current);
    uint8_t itValue = parseIntegrationTimeValue(activeConfig->integration_time);
    uint16_t dutyValue = parseDutyCycleValue(activeConfig->duty_cycle);
    uint8_t pulses = parseMultiPulseCount(activeConfig->multi_pulse);
    bool highRes = activeConfig->high_resolution;

    Serial.printf("  Config request: LED=%dmA, IT=%s, Duty=1/%d, MultiPulse=%d, HighRes=%d\n",
                  ledMA, activeConfig->integration_time.c_str(), dutyValue, pulses, highRes);

    // Zero-initialize both config registers before applying settings.
    // This clears any stale interrupt-mode bits (thresholds, persistence,
    // interrupt type) left by InterruptManager, since the driver's per-field
    // methods use read-modify-write and would preserve those bits.
    bool ok1 = vcnl.writeRegister(VCNL4040_PS_CONF1_2, 0x0000);
    bool ok2 = vcnl.writeRegister(VCNL4040_PS_CONF3_MS, 0x0000);

    delayMicroseconds(500);

    // Apply config via driver methods (each does read-modify-write on
    // the now-zeroed registers, so only our intended bits get set)
    vcnl.setIRDutyCycle(dutyValue);
    vcnl.setProxIntegrationTime(itValue);
    vcnl.setProxResolution(highRes ? 16 : 12);
    vcnl.powerOnProximity(true);
    vcnl.setMultiPulse(pulses);
    vcnl.setLEDCurrent(ledMA);

    uint16_t conf12 = vcnl.readRegister(VCNL4040_PS_CONF1_2);
    uint16_t conf3ms = vcnl.readRegister(VCNL4040_PS_CONF3_MS);
    Serial.printf("  Write: PS_CONF1/2=0x%04X (ok:%d), PS_CONF3/MS=0x%04X (ok:%d)\n",
                  conf12, ok1, conf3ms, ok2);

    // Verify LED current — hardware bug workaround: read back and retry if mismatch
    delay(10);

    const char *led_ma[] = {"50mA", "75mA", "100mA", "120mA", "140mA", "160mA", "180mA", "200mA"};
    uint8_t verify_high = vcnl.readRegisterHigh(VCNL4040_PS_CONF3_MS);
    uint8_t actual_led = verify_high & 0x07;

    // Compute expected LED_I bits from the mA value
    uint8_t expected_led;
    switch (ledMA) {
        case 50:  expected_led = VCNL4040_LED_I_50MA; break;
        case 75:  expected_led = VCNL4040_LED_I_75MA; break;
        case 100: expected_led = VCNL4040_LED_I_100MA; break;
        case 120: expected_led = VCNL4040_LED_I_120MA; break;
        case 140: expected_led = VCNL4040_LED_I_140MA; break;
        case 160: expected_led = VCNL4040_LED_I_160MA; break;
        case 180: expected_led = VCNL4040_LED_I_180MA; break;
        default:  expected_led = VCNL4040_LED_I_200MA; break;
    }

    Serial.printf("  Verify read: PS_MS high=0x%02X, LED_I bits=%d (%s)\n",
                  verify_high, actual_led, led_ma[actual_led]);

    if (actual_led != expected_led)
    {
        Serial.printf("  ⚠️ LED VERIFY FAILED: expected %d, read %d (%s)\n",
                      expected_led, actual_led, led_ma[actual_led]);

        Serial.println("  Retrying LED current write...");
        delay(50);

        vcnl.setLEDCurrent(ledMA);

        delay(20);

        verify_high = vcnl.readRegisterHigh(VCNL4040_PS_CONF3_MS);
        actual_led = verify_high & 0x07;

        Serial.printf("  Retry result: LED_I=%d (%s)\n",
                      actual_led, led_ma[actual_led]);
    }
    else
    {
        Serial.printf("  ✓ LED verified: %s\n", led_ma[actual_led]);
    }

    return (ok1 && ok2);
}

bool SensorManager::init(SensorConfiguration *config)
{
    Serial.println("Initializing Sensor Manager...");

    activeConfig = config;

    if (activeConfig != nullptr)
    {
        Serial.println("Configuration:");
        Serial.printf("  Sample Rate: %d Hz\n", activeConfig->sample_rate_hz);
        Serial.printf("  LED Current: %s\n", activeConfig->led_current.c_str());
        Serial.printf("  Integration Time: %s\n", activeConfig->integration_time.c_str());
        Serial.printf("  High Resolution: %s\n", activeConfig->high_resolution ? "enabled" : "disabled");
        Serial.printf("  Read Ambient: %s\n", activeConfig->read_ambient ? "enabled" : "disabled");
    }

    if (!muxController.begin(43, 44, I2C_CLOCK_HZ))
    {
        Serial.println("ERROR: MuxController initialization failed (no sensors found)");
        return false;
    }

#if STARTUP_I2C_SCAN
    diagnostics.i2cBusScan();
#endif

    delay(50);

    // Initialize VCNL4040 driver's Wire reference using the first available sensor.
    // begin() verifies ID and sets defaults on that one sensor; applySensorConfig()
    // will overwrite those defaults immediately. For subsequent sensors the driver
    // methods work because _i2cPort is already set.
    bool driverInitialized = false;
    int sensors_initialized = 0;

    for (int i = 0; i < NUM_SENSORS; i++)
    {
        SensorPosition pos = muxController.getSensorPosition(i);

        Serial.printf("Initializing sensor %d (%s)...\n", i, pos.getName().c_str());

        if (!muxController.isSensorAvailable(i))
        {
            Serial.println("  No sensor detected at this position");
            continue;
        }

        if (!muxController.selectSensor(i))
        {
            Serial.println("  ERROR: Failed to select sensor via mux");
            continue;
        }

        delay(5);

        if (!driverInitialized)
        {
            if (!vcnl.begin(Wire))
            {
                Serial.println("  ERROR: VCNL4040 driver begin() failed");
                continue;
            }
            driverInitialized = true;
        }

        if (activeConfig != nullptr)
        {
            applySensorConfig(i);
        }
        else
        {
            // Zero-init then apply polling defaults via driver
            vcnl.writeRegister(VCNL4040_PS_CONF1_2, 0x0000);
            vcnl.writeRegister(VCNL4040_PS_CONF3_MS, 0x0000);
            vcnl.setIRDutyCycle(40);
            vcnl.setProxIntegrationTime(1);
            vcnl.setProxResolution(16);
            vcnl.powerOnProximity(true);
            vcnl.setLEDCurrent(200);
            Serial.println("  Applied default config (200mA, 1T, 1/40, HighRes)");
        }

        Serial.println("  Sensor initialized successfully!");
        sensors_initialized++;
    }

    muxController.disableAll();

    Serial.printf("Initialized %d / %d sensors\n", sensors_initialized, NUM_SENSORS);

    if (sensors_initialized == 0)
    {
        Serial.println("ERROR: No sensors initialized!");
        return false;
    }

    initialized = true;
    Serial.println("Sensor Manager initialization complete!");

    dumpSensorConfiguration();

    return true;
}

bool SensorManager::readSensor(uint8_t sensorIndex, SensorReading &reading)
{
    if (sensorIndex >= NUM_SENSORS)
        return false;

    if (!muxController.isSensorAvailable(sensorIndex))
        return false;

    if (!muxController.selectSensor(sensorIndex))
        return false;

    reading.timestamp_us = micros();
    reading.position = sensorIndex;

    SensorPosition pos = muxController.getSensorPosition(sensorIndex);
    reading.pcb_id = pos.pcbId;
    reading.side = pos.side;

    uint16_t proxValue;
    if (!vcnl.readRegister(VCNL4040_PS_DATA, proxValue))
        return false;
    reading.proximity = proxValue;

    if (activeConfig != nullptr && !activeConfig->read_ambient)
    {
        reading.ambient = 0;
    }
    else
    {
        uint16_t alsValue;
        if (!vcnl.readRegister(VCNL4040_ALS_DATA, alsValue))
            return false;
        reading.ambient = alsValue;
    }

    return true;
}

void SensorManager::sensorTaskFunction(void *parameter)
{
    SensorManager *manager = (SensorManager *)parameter;

    DEBUG_LOG("Sensor task started on Core 0\n");

    unsigned long lastSampleTime = micros();
    unsigned long lastErrorLog = 0;
    int consecutiveFailures = 0;
    SensorReading reading;
    unsigned long lastYield = micros();

    while (!manager->stopRequested) // Check stop flag instead of infinite loop
    {
        unsigned long currentTime = micros();

        // Check if it's time for next sample
        if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_US)
        {
            lastSampleTime = currentTime;

            // Capture timestamp ONCE for all sensors in this cycle
            // This ensures all sensors from the same sample have the same timestamp
            // ⚠️ IMPORTANT: This synchronized timestamping requires the backend to use
            // a composite key. See: infrastructure/DATABASE_SCHEMA.md for details.
            unsigned long cycleTimestamp = micros();

            int successfulReads = 0;
            int failedReads = 0;

            // Session Confirmation: count this cycle
            if (manager->activeSummary)
            {
                manager->activeSummary->total_cycles++;
            }

            // Read all active sensors (REVERSED for timing test - normally 0 to NUM_SENSORS)
            for (int i = NUM_SENSORS - 1; i >= 0; i--)
            {
                // Check stop flag between sensor reads for faster response
                if (manager->stopRequested)
                    break;

                if (!manager->muxController.isSensorAvailable(i))
                    continue;

                if (manager->readSensor(i, reading))
                {
                    // Override timestamp with cycle timestamp for synchronization
                    reading.timestamp_us = cycleTimestamp;

                    // Send to queue (non-blocking); skip if queue was torn down
                    if (manager->dataQueue != NULL &&
                        xQueueSend(manager->dataQueue, &reading, 0) == pdTRUE)
                    {
                        successfulReads++;
                        // Session Confirmation: count successful read + queue
                        if (manager->activeSummary)
                        {
                            manager->activeSummary->readings_collected[i]++;
                        }
                    }
                    else
                    {
                        // Queue full - data lost
                        if (manager->activeSummary)
                        {
                            manager->activeSummary->queue_drops++;
                        }
                    }
                }
                else
                {
                    failedReads++;
                    // Session Confirmation: count I2C error
                    if (manager->activeSummary)
                    {
                        manager->activeSummary->i2c_errors[i]++;
                    }
                }
            }

            // Track consecutive failures and log errors
            if (failedReads > 0)
            {
                consecutiveFailures++;
                // Log every 100 failures or first 3 failures
                if (consecutiveFailures <= 3 || (millis() - lastErrorLog > 5000))
                {
                    DEBUG_LOG("WARNING: Sensor read failures: %d failed, %d succeeded\n",
                              failedReads, successfulReads);
                    lastErrorLog = millis();
                }
            }
            else
            {
                consecutiveFailures = 0;
            }

            manager->muxController.disableAll();
        }

        // CRITICAL: Yield periodically to prevent watchdog timer reset
        // Yield every 100ms to keep watchdog happy without impacting sample rate
        unsigned long currentYieldTime = micros();
        if (currentYieldTime - lastYield >= 100000) // 100ms
        {
            taskYIELD();
            lastYield = currentYieldTime;
        }
    }

    // ===== GRACEFUL CLEANUP BEFORE EXIT =====
    // This ensures the I2C bus is in a clean state before task ends
    Serial.println("Sensor task stopping gracefully...");

    manager->muxController.disableAll();

    // Clear summary pointer (collection is over)
    manager->activeSummary = nullptr;

    Serial.println("Sensor task cleanup complete, exiting.");

    // Notify the task that requested the stop, completing the exit handshake
    TaskHandle_t requestor = manager->stopRequestorTask;
    if (requestor != NULL)
    {
        xTaskNotifyGive(requestor);
    }

    // Self-delete — the requestor is responsible for NULLing sensorTask
    vTaskDelete(NULL);
}

bool SensorManager::startCollection(QueueHandle_t queue, SessionSummary *summary)
{
    if (!initialized)
    {
        Serial.println("ERROR: Sensors not initialized");
        return false;
    }

    if (queue == NULL)
    {
        Serial.println("ERROR: Cannot start collection with NULL queue");
        return false;
    }

    if (sensorTask != NULL)
    {
        Serial.println("Collection already running");
        return false;
    }

    dataQueue = queue;
    activeSummary = summary;

    // Reset stop flag before starting new task
    stopRequested = false;

    // Create sensor task on Core 0
    // Stack size increased to 8192 to handle I2C operations and error logging
    xTaskCreatePinnedToCore(
        sensorTaskFunction,
        "SensorTask",
        8192, // Stack size (increased from 4096)
        this, // Parameter
        2,    // Priority (higher = more important)
        &sensorTask,
        0 // Core 0 (protocol CPU)
    );

    DEBUG_LOG("Sensor collection started\n");
    return true;
}

void SensorManager::stopCollection()
{
    if (sensorTask == NULL)
    {
        Serial.println("No sensor task running");
        return;
    }

    Serial.println("Requesting sensor task to stop...");

    // Register ourselves so the sensor task can notify us on exit
    stopRequestorTask = xTaskGetCurrentTaskHandle();

    // Signal the task to stop gracefully
    stopRequested = true;

    // Block until the sensor task notifies us, or timeout
    static constexpr uint32_t STOP_TIMEOUT_MS = 500;
    uint32_t notified = ulTaskNotifyTake(pdTRUE, pdMS_TO_TICKS(STOP_TIMEOUT_MS));

    if (notified)
    {
        Serial.println("Sensor task stopped gracefully");
    }
    else
    {
        Serial.println("WARNING: Sensor task did not stop in time, forcing deletion");
        vTaskDelete(sensorTask);
        muxController.disableAll();
        Serial.println("I2C bus cleaned up after forced stop");
    }

    sensorTask = NULL;
    stopRequestorTask = NULL;

    Serial.println("Sensor collection stopped");
}

bool SensorManager::isCollecting()
{
    return sensorTask != NULL;
}

std::vector<SensorMetadata> SensorManager::getSensorMetadata()
{
    std::vector<SensorMetadata> metadata;

    for (int i = 0; i < NUM_SENSORS; i++)
    {
        SensorPosition pos = muxController.getSensorPosition(i);

        SensorMetadata meta;
        meta.position = i;
        meta.pcb_id = pos.pcbId;
        meta.side = pos.side;
        meta.active = muxController.isSensorAvailable(i);
        meta.name = pos.getName();

        metadata.push_back(meta);
    }

    return metadata;
}

bool SensorManager::reinitialize(SensorConfiguration *config)
{
    Serial.println("Reinitializing sensors with new configuration...");

    // Stop collection if running
    bool wasCollecting = isCollecting();
    if (wasCollecting)
    {
        Serial.println("  Stopping sensor collection task...");
        stopCollection();
        taskYIELD(); // Give scheduler time to clean up
        delay(100);  // Small extra delay for safety
        Serial.println("  Collection stopped.");
    }

    Serial.println("  Ensuring I2C bus is clean...");
    muxController.disableAll();
    delay(50);

    // Update configuration
    activeConfig = config;
    Serial.println("  Applying new configuration to sensors...");

    for (int i = 0; i < NUM_SENSORS; i++)
    {
        if (muxController.isSensorAvailable(i) && activeConfig != nullptr)
        {
            Serial.printf("  Reconfiguring sensor %d...\n", i);

            if (!muxController.selectSensor(i))
            {
                Serial.printf("    WARNING: Failed to select sensor %d\n", i);
                continue;
            }
            delay(10);

            applySensorConfig(i);
            Serial.printf("    Sensor %d reconfigured.\n", i);

            taskYIELD();
        }
    }

    Serial.println("  Cleaning up multiplexer channels...");
    muxController.disableAll();

    // Final yield to ensure watchdog is fed
    taskYIELD();

    Serial.println("  Sensors reconfigured successfully!");

    // Dump configuration to verify all sensors got the new settings
    dumpSensorConfiguration();

    // PS_CANC recalibration removed — adaptive baseline in DirectionDetector
    // handles offset changes from config updates dynamically.

    return true;
}

void SensorManager::dumpSensorConfiguration()
{
    diagnostics.dumpConfiguration(activeConfig);
}
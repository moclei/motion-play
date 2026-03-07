#include "SensorManager.h"
#include "../session/SessionManager.h" // For SessionSummary full definition
#include "constants.h"
#include "debug_log.h"

SensorManager::SensorManager()
{
    // Constructor — MuxController default-constructs with TCA address 0x70
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

    // Take multiple readings to calculate average baseline
    const int NUM_SAMPLES = 50;
    const int SAMPLE_DELAY_MS = 10; // 10ms between samples
    uint32_t sum = 0;
    int validSamples = 0;

    for (int i = 0; i < NUM_SAMPLES; i++)
    {
        // Read proximity directly via I2C
        Wire.beginTransmission(VCNL4040_ADDR);
        Wire.write(0x08); // PS_DATA register
        if (Wire.endTransmission(false) != 0)
            continue;

        Wire.requestFrom((uint8_t)VCNL4040_ADDR, (uint8_t)2);
        if (Wire.available() >= 2)
        {
            uint8_t prox_low = Wire.read();
            uint8_t prox_high = Wire.read();
            uint16_t proximity = (prox_high << 8) | prox_low;
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

    // Calculate average baseline
    uint16_t baseline = sum / validSamples;
    baselineValues[sensorIndex] = baseline;

    Wire.beginTransmission(VCNL4040_ADDR);
    Wire.write(0x05);                   // PS_CANC register
    Wire.write(baseline & 0xFF);        // Low byte
    Wire.write((baseline >> 8) & 0xFF); // High byte
    uint8_t err = Wire.endTransmission();

    if (err != 0)
    {
        Serial.printf("  Calibration: Failed to write PS_CANC (I2C error %d)\n", err);
        return false;
    }

    delay(5);
    Wire.beginTransmission(VCNL4040_ADDR);
    Wire.write(0x05);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)VCNL4040_ADDR, (uint8_t)2);
    uint8_t verify_low = Wire.available() ? Wire.read() : 0xFF;
    uint8_t verify_high = Wire.available() ? Wire.read() : 0xFF;
    uint16_t verify_value = (verify_high << 8) | verify_low;

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

VCNL4040_LEDCurrent SensorManager::parseLEDCurrent(const String &current)
{
    if (current == "50mA")
        return VCNL4040_LED_CURRENT_50MA;
    if (current == "75mA")
        return VCNL4040_LED_CURRENT_75MA;
    if (current == "100mA")
        return VCNL4040_LED_CURRENT_100MA;
    if (current == "120mA")
        return VCNL4040_LED_CURRENT_120MA;
    if (current == "140mA")
        return VCNL4040_LED_CURRENT_140MA;
    if (current == "160mA")
        return VCNL4040_LED_CURRENT_160MA;
    if (current == "180mA")
        return VCNL4040_LED_CURRENT_180MA;
    // Default to 200mA
    return VCNL4040_LED_CURRENT_200MA;
}

VCNL4040_ProximityIntegration SensorManager::parseIntegrationTime(const String &time)
{
    if (time == "1T")
        return VCNL4040_PROXIMITY_INTEGRATION_TIME_1T;
    if (time == "1.5T")
        return VCNL4040_PROXIMITY_INTEGRATION_TIME_1_5T;
    if (time == "2T")
        return VCNL4040_PROXIMITY_INTEGRATION_TIME_2T;
    if (time == "2.5T")
        return VCNL4040_PROXIMITY_INTEGRATION_TIME_2_5T;
    if (time == "3T")
        return VCNL4040_PROXIMITY_INTEGRATION_TIME_3T;
    if (time == "3.5T")
        return VCNL4040_PROXIMITY_INTEGRATION_TIME_3_5T;
    if (time == "4T")
        return VCNL4040_PROXIMITY_INTEGRATION_TIME_4T;
    if (time == "8T")
        return VCNL4040_PROXIMITY_INTEGRATION_TIME_8T;
    // Default to 1T (fastest)
    return VCNL4040_PROXIMITY_INTEGRATION_TIME_1T;
}

VCNL4040_LEDDutyCycle SensorManager::parseDutyCycle(const String &duty)
{
    if (duty == "1/40")
        return VCNL4040_LED_DUTY_1_40; // ~200 Hz - Fastest
    if (duty == "1/80")
        return VCNL4040_LED_DUTY_1_80; // ~100 Hz
    if (duty == "1/160")
        return VCNL4040_LED_DUTY_1_160; // ~50 Hz
    if (duty == "1/320")
        return VCNL4040_LED_DUTY_1_320; // ~25 Hz - Slowest, best battery
    // Default to 1/40 (fastest)
    return VCNL4040_LED_DUTY_1_40;
}

// Parse multi-pulse setting string to register value
// PS_MPS bits 6:5 of PS_CONF3: 00=1, 01=2, 10=4, 11=8 pulses
uint8_t SensorManager::parseMultiPulse(const String &mp)
{
    if (mp == "2")
        return 0x01; // 01 = 2 pulses
    if (mp == "4")
        return 0x02; // 10 = 4 pulses
    if (mp == "8")
        return 0x03; // 11 = 8 pulses
    // Default to 1 pulse (00)
    return 0x00;
}

bool SensorManager::applySensorConfig(uint8_t sensorIndex)
{
    if (sensorIndex >= NUM_SENSORS || activeConfig == nullptr)
        return false;

    // Parse configuration values
    VCNL4040_LEDCurrent led = parseLEDCurrent(activeConfig->led_current);
    VCNL4040_ProximityIntegration integration = parseIntegrationTime(activeConfig->integration_time);
    VCNL4040_LEDDutyCycle duty = parseDutyCycle(activeConfig->duty_cycle);
    uint8_t multiPulse = parseMultiPulse(activeConfig->multi_pulse);
    bool highRes = activeConfig->high_resolution;

    // Debug: Print what we're trying to set
    Serial.printf("  Config request: LED=%d (want %s), IT=%d, Duty=%d, MultiPulse=%d, HighRes=%d\n",
                  (int)led, activeConfig->led_current.c_str(), (int)integration, (int)duty, multiPulse, highRes);

    // ========================================================================
    // DIRECT REGISTER WRITES - Bypass Adafruit library for reliable config
    // Using SparkFun-style approach: write full register values directly
    // ========================================================================

    // Step 1: Configure PS_CONF1/2 register (0x03)
    // PS_CONF1 (low byte): bits 7:6 = PS_Duty, bits 3:1 = PS_IT, bit 0 = PS_SD
    // PS_CONF2 (high byte): bit 3 = PS_HD
    uint8_t ps_conf1 = ((duty & 0x03) << 6) |        // PS_Duty in bits 7:6
                       ((integration & 0x07) << 1) | // PS_IT in bits 3:1
                       0x00;                         // PS_SD = 0 (proximity enabled)
    uint8_t ps_conf2 = (highRes ? 0x08 : 0x00);      // PS_HD in bit 3

    Wire.beginTransmission(VCNL4040_ADDR);
    Wire.write(0x03);
    Wire.write(ps_conf1);
    Wire.write(ps_conf2);
    uint8_t err1 = Wire.endTransmission();

    delayMicroseconds(500);

    uint8_t ps_conf3 = (multiPulse & 0x03) << 5;
    uint8_t ps_ms = (led & 0x07);

    Wire.beginTransmission(VCNL4040_ADDR);
    Wire.write(0x04);
    Wire.write(ps_conf3);
    Wire.write(ps_ms);
    uint8_t err2 = Wire.endTransmission();

    Serial.printf("  Write: PS_CONF1/2=0x%02X%02X (err:%d), PS_CONF3/MS=0x%02X%02X (err:%d)\n",
                  ps_conf2, ps_conf1, err1, ps_ms, ps_conf3, err2);

    // Step 3: Verify by reading back - add longer delay for register to fully settle
    delay(10);

    Wire.beginTransmission(VCNL4040_ADDR);
    Wire.write(0x04);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)VCNL4040_ADDR, (uint8_t)2);
    uint8_t verify_low = Wire.available() ? Wire.read() : 0xFF;
    uint8_t verify_high = Wire.available() ? Wire.read() : 0xFF;

    uint8_t actual_led = verify_high & 0x07;
    const char *led_ma[] = {"50mA", "75mA", "100mA", "120mA", "140mA", "160mA", "180mA", "200mA"};

    Serial.printf("  Verify read: PS_CONF3/MS=0x%02X%02X, LED_I bits=%d (%s)\n",
                  verify_high, verify_low, actual_led, led_ma[actual_led]);

    if (actual_led != (led & 0x07))
    {
        Serial.printf("  ⚠️ LED VERIFY FAILED: wrote %d, read %d (%s)\n",
                      (int)(led & 0x07), actual_led, led_ma[actual_led]);

        // Try writing AGAIN with extra delay
        Serial.println("  Retrying LED current write...");
        delay(50);

        Wire.beginTransmission(VCNL4040_ADDR);
        Wire.write(0x04);
        Wire.write(ps_conf3);
        Wire.write(ps_ms);
        uint8_t err_retry = Wire.endTransmission();

        delay(20);

        Wire.beginTransmission(VCNL4040_ADDR);
        Wire.write(0x04);
        Wire.endTransmission(false);
        Wire.requestFrom((uint8_t)VCNL4040_ADDR, (uint8_t)2);
        verify_low = Wire.available() ? Wire.read() : 0xFF;
        verify_high = Wire.available() ? Wire.read() : 0xFF;
        actual_led = verify_high & 0x07;

        Serial.printf("  Retry result: err=%d, LED_I=%d (%s)\n",
                      err_retry, actual_led, led_ma[actual_led]);
    }
    else
    {
        Serial.printf("  ✓ LED verified: %s\n", led_ma[actual_led]);
    }

    return (err1 == 0 && err2 == 0);
}

void SensorManager::debugI2CScan()
{
    Serial.println("\n");
    Serial.println("╔══════════════════════════════════════════════════════════════════════════════╗");
    Serial.println("║                        I2C DEBUG SCAN - TROUBLESHOOTING                      ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    Serial.println("║ STEP 1: Scanning main I2C bus (no TCA channel selected)                      ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    muxController.disableAll();
    delay(10);

    int mainBusDevices = 0;
    for (uint8_t addr = 0x08; addr <= 0x77; addr++)
    {
        Wire.beginTransmission(addr);
        uint8_t error = Wire.endTransmission();

        if (error == 0)
        {
            mainBusDevices++;
            const char *deviceName = "Unknown";
            if (addr == 0x70)
                deviceName = "TCA9548A (main mux)";
            else if (addr >= 0x71 && addr <= 0x77)
                deviceName = "Possible PCA9546A";
            else if (addr == VCNL4040_ADDR)
                deviceName = "VCNL4040";

            Serial.printf("║   Found device at 0x%02X - %s                            \n", addr, deviceName);
        }
    }

    if (mainBusDevices == 0)
    {
        Serial.println("║   ⚠️ No devices found on main I2C bus!                                      ║");
    }
    else
    {
        Serial.printf("║   Total: %d device(s) on main bus                                            \n", mainBusDevices);
    }

    // Now scan each TCA channel
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ STEP 2: Scanning each TCA9548A channel for connected devices                 ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    for (int tca_ch = 0; tca_ch < 8; tca_ch++)
    {
        Serial.printf("║ TCA Channel %d:                                                              \n", tca_ch);

        if (!muxController.selectTCAChannel(tca_ch))
        {
            Serial.println("║   ⚠️ Failed to select this channel!                                         ║");
            continue;
        }

        delay(20);

        // Scan for devices on this channel
        int channelDevices = 0;
        for (uint8_t addr = 0x08; addr <= 0x77; addr++)
        {
            // Skip TCA address (it will always respond)
            if (addr == 0x70)
                continue;

            Wire.beginTransmission(addr);
            uint8_t error = Wire.endTransmission();

            if (error == 0)
            {
                channelDevices++;
                const char *deviceName = "Unknown";
                if (addr >= 0x71 && addr <= 0x77)
                    deviceName = "PCA9546A?";
                else if (addr == 0x74)
                    deviceName = "PCA9546A (expected addr)";
                else if (addr == VCNL4040_ADDR)
                    deviceName = "VCNL4040";

                Serial.printf("║   ✓ Found: 0x%02X (%s)                                  \n", addr, deviceName);
            }
        }

        if (channelDevices == 0)
        {
            Serial.println("║   (no devices found)                                                        ║");
        }
    }

    muxController.disableAll();

    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ STEP 3: Direct PCA9546A address probe at 0x74 on TCA channel 0               ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    if (muxController.selectTCAChannel(0))
    {
        Serial.println("║   TCA channel 0 selected successfully                                       ║");
        delay(50); // Extra long delay

        // Try multiple times with different delays
        for (int attempt = 1; attempt <= 3; attempt++)
        {
            Wire.beginTransmission(0x74);
            uint8_t error = Wire.endTransmission();

            const char *errorStr = "Unknown";
            switch (error)
            {
            case 0:
                errorStr = "SUCCESS";
                break;
            case 1:
                errorStr = "Data too long";
                break;
            case 2:
                errorStr = "NACK on address";
                break;
            case 3:
                errorStr = "NACK on data";
                break;
            case 4:
                errorStr = "Other error";
                break;
            case 5:
                errorStr = "Timeout";
                break;
            }

            Serial.printf("║   Attempt %d: Address 0x74 -> Error %d (%s)                    \n",
                          attempt, error, errorStr);

            if (error == 0)
                break;
            delay(50);
        }

        // Also try reading from 0x74 to see if it responds
        Serial.println("║   Attempting to read control register from 0x74...                          ║");
        Wire.beginTransmission(0x74);
        uint8_t writeErr = Wire.endTransmission(false); // Don't release bus

        if (writeErr == 0)
        {
            uint8_t bytesRead = Wire.requestFrom((uint8_t)0x74, (uint8_t)1);
            if (bytesRead > 0)
            {
                uint8_t controlReg = Wire.read();
                Serial.printf("║   ✓ Read success! Control register value: 0x%02X                          \n", controlReg);
            }
            else
            {
                Serial.println("║   ⚠️ Write OK but read returned 0 bytes                                    ║");
            }
        }
        else
        {
            Serial.printf("║   ⚠️ Write failed with error %d, skipping read                               \n", writeErr);
        }
    }
    else
    {
        Serial.println("║   ⚠️ Failed to select TCA channel 0!                                         ║");
    }

    muxController.disableAll();

    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ DEBUG SCAN COMPLETE - Check results above for clues                          ║");
    Serial.println("╚══════════════════════════════════════════════════════════════════════════════╝");
    Serial.println();
}


bool SensorManager::init(SensorConfiguration *config)
{
    Serial.println("Initializing Sensor Manager...");

    // Store configuration reference
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

    // Initialize MuxController (handles I2C init, TCA9548A, PCA9546A scanning, sensor detection)
    if (!muxController.begin(43, 44, I2C_CLOCK_HZ))
    {
        Serial.println("ERROR: MuxController initialization failed (no sensors found)");
        return false;
    }

#if STARTUP_I2C_SCAN
    debugI2CScan();
#endif

    delay(50);

    // Configure all detected VCNL4040 sensors
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

        // Apply configuration using DIRECT I2C only (no Adafruit library!)
        if (activeConfig != nullptr)
        {
            applySensorConfig(i);
        }
        else
        {
            // Default configuration - direct I2C write
            // PS_CONF1/2: Enable proximity, 1T integration, 1/40 duty, high res
            Wire.beginTransmission(VCNL4040_ADDR);
            Wire.write(0x03);
            Wire.write(0x00); // PS_CONF1: PS_IT=0 (1T), PS_Duty=0 (1/40), PS_SD=0 (enabled)
            Wire.write(0x08); // PS_CONF2: PS_HD=1 (high res)
            Wire.endTransmission();

            // PS_MS: 200mA LED current
            Wire.beginTransmission(VCNL4040_ADDR);
            Wire.write(0x04);
            Wire.write(0x00); // PS_MS low
            Wire.write(0x07); // PS_MS high: LED_I=7 (200mA)
            Wire.endTransmission();

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

    Wire.beginTransmission(VCNL4040_ADDR);
    Wire.write(0x08); // PS_DATA register
    if (Wire.endTransmission(false) != 0)
        return false;

    Wire.requestFrom(VCNL4040_ADDR, 2);
    if (Wire.available() < 2)
        return false;

    uint8_t prox_low = Wire.read();
    uint8_t prox_high = Wire.read();
    reading.proximity = (prox_high << 8) | prox_low;

    // Conditionally read ambient light (skip if disabled for speed)
    if (activeConfig != nullptr && !activeConfig->read_ambient)
    {
        reading.ambient = 0;
    }
    else
    {
        Wire.beginTransmission(VCNL4040_ADDR);
        Wire.write(0x09); // ALS_DATA register
        if (Wire.endTransmission(false) != 0)
            return false;

        Wire.requestFrom(VCNL4040_ADDR, 2);
        if (Wire.available() < 2)
            return false;

        uint8_t als_low = Wire.read();
        uint8_t als_high = Wire.read();
        reading.ambient = (als_high << 8) | als_low;
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
    Serial.println("\n");
    Serial.println("╔══════════════════════════════════════════════════════════════════════════════╗");
    Serial.println("║                    SENSOR CONFIGURATION DIAGNOSTIC DUMP                      ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ Sensor │ TCA │ PCA │ Active │ LED Current │ Integration │ Duty  │ HighRes  ║");
    Serial.println("╠════════╪═════╪═════╪════════╪═════════════╪═════════════╪═══════╪══════════╣");

    const char *led_current_names[] = {"50mA", "75mA", "100mA", "120mA", "140mA", "160mA", "180mA", "200mA"};
    const char *integration_names[] = {"1T", "1.5T", "2T", "2.5T", "3T", "3.5T", "4T", "8T"};
    const char *duty_names[] = {"1/40", "1/80", "1/160", "1/320"};

    int mismatches = 0;

    for (int i = 0; i < NUM_SENSORS; i++)
    {
        SensorPosition pos = muxController.getSensorPosition(i);
        uint8_t tca_ch = pos.tcaChannel;
        uint8_t pca_ch = pos.pcaChannel;

        char sensorName[8];
        snprintf(sensorName, sizeof(sensorName), "P%dS%d", pos.pcbId, pos.side);

        if (!muxController.isSensorAvailable(i))
        {
            Serial.printf("║ %-6s │  %d  │  %d  │   NO   │     N/A     │     N/A     │  N/A  │   N/A    ║\n",
                          sensorName, tca_ch, pca_ch);
            continue;
        }

        if (!muxController.selectSensor(i))
        {
            Serial.printf("║ %-6s │  %d  │  %d  │  YES   │  MUX ERR    │   MUX ERR   │ ERR   │   ERR    ║\n",
                          sensorName, tca_ch, pca_ch);
            continue;
        }
        delay(10);

        Wire.beginTransmission(VCNL4040_ADDR);
        Wire.write(0x0C);
        if (Wire.endTransmission(false) != 0)
        {
            Serial.printf("║ %-6s │  %d  │  %d  │  YES   │  I2C ERR    │   I2C ERR   │ ERR   │   ERR    ║\n",
                          sensorName, tca_ch, pca_ch);
            continue;
        }
        Wire.requestFrom((uint8_t)VCNL4040_ADDR, (uint8_t)2);
        uint8_t id_low = Wire.available() ? Wire.read() : 0;
        uint8_t id_high = Wire.available() ? Wire.read() : 0;
        uint16_t device_id = (id_high << 8) | id_low;

        if (device_id != 0x0186)
        {
            Serial.printf("║ %-6s │  %d  │  %d  │  YES   │ BAD ID 0x%04X                              ║\n",
                          sensorName, tca_ch, pca_ch, device_id);
            continue;
        }

        uint8_t ps_conf1_low = 0, ps_conf1_high = 0;
        Wire.beginTransmission(VCNL4040_ADDR);
        Wire.write(0x03);
        if (Wire.endTransmission(false) == 0)
        {
            Wire.requestFrom((uint8_t)VCNL4040_ADDR, (uint8_t)2);
            if (Wire.available() >= 2)
            {
                ps_conf1_low = Wire.read();
                ps_conf1_high = Wire.read();
            }
        }

        uint8_t ps_ms_low = 0, ps_ms_high = 0;
        Wire.beginTransmission(VCNL4040_ADDR);
        Wire.write(0x04);
        if (Wire.endTransmission(false) == 0)
        {
            Wire.requestFrom((uint8_t)VCNL4040_ADDR, (uint8_t)2);
            if (Wire.available() >= 2)
            {
                ps_ms_low = Wire.read();
                ps_ms_high = Wire.read();
            }
        }

        // Parse register values
        // PS_CONF1 low byte: bits 7:6 = PS_Duty, bits 3:1 = PS_IT
        // PS_CONF2 (high byte of reg 0x03): bit 3 = PS_HD (high resolution)
        uint8_t duty_bits = (ps_conf1_low >> 6) & 0x03;
        uint8_t integration_bits = (ps_conf1_low >> 1) & 0x07;
        bool high_res = (ps_conf1_high >> 3) & 0x01;

        // PS_MS (high byte of reg 0x04): bits 2:0 = LED_I (LED current)
        uint8_t led_current_bits = ps_ms_high & 0x07;

        // Get string representations (with bounds checking)
        const char *led_str = (led_current_bits < 8) ? led_current_names[led_current_bits] : "???";
        const char *int_str = (integration_bits < 8) ? integration_names[integration_bits] : "???";
        const char *duty_str = (duty_bits < 4) ? duty_names[duty_bits] : "???";

        // Check for mismatches with expected config
        bool led_match = true;
        if (activeConfig != nullptr)
        {
            VCNL4040_LEDCurrent expected_led = parseLEDCurrent(activeConfig->led_current);
            if (led_current_bits != (expected_led & 0x07))
            {
                led_match = false;
                mismatches++;
            }
        }

        Serial.printf("║ %-6s │  %d  │  %d  │  YES   │ %s %-7s %s │    %-6s   │ %-5s │   %-5s  ║\n",
                      sensorName, tca_ch, pca_ch,
                      led_match ? " " : "⚠",
                      led_str,
                      led_match ? " " : "⚠",
                      int_str, duty_str,
                      high_res ? "YES" : "NO");

        // Debug: print raw register values if there's a mismatch
        if (!led_match)
        {
            Serial.printf("║        │ RAW: PS_CONF1/2=0x%02X%02X PS_CONF3/MS=0x%02X%02X                       ║\n",
                          ps_conf1_high, ps_conf1_low, ps_ms_high, ps_ms_low);
        }
    }

    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    // Show expected configuration
    if (activeConfig != nullptr)
    {
        Serial.printf("║ EXPECTED: LED=%-7s IT=%-5s Duty=%-5s MultiP=%sP HighRes=%-3s        ║\n",
                      activeConfig->led_current.c_str(),
                      activeConfig->integration_time.c_str(),
                      activeConfig->duty_cycle.c_str(),
                      activeConfig->multi_pulse.c_str(),
                      activeConfig->high_resolution ? "YES" : "NO");
    }
    else
    {
        Serial.println("║ EXPECTED: (no configuration provided - using defaults)                       ║");
    }

    if (mismatches > 0)
    {
        Serial.printf("║ ⚠️ WARNING: %d sensor(s) have configuration mismatches!                       ║\n", mismatches);
    }

    Serial.println("╚══════════════════════════════════════════════════════════════════════════════╝");
    Serial.println();

    muxController.disableAll();
}
#include "SensorManager.h"

SensorManager::SensorManager() : mux(0x70)
{
    // Constructor
}

void SensorManager::cleanupI2CBus()
{
    // Disable all multiplexer channels to release the I2C bus
    // IMPORTANT: Must select each TCA channel before disabling its PCA!
    for (int i = 0; i < 3; i++)
    {
        mux.selectChannel(i);
        delay(2);
        pca_instances[i].disableAllChannels();
    }
    mux.disableAllChannels();

    // Small delay to ensure bus is stable
    delayMicroseconds(100);
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
    if (sensorIndex >= NUM_SENSORS || !sensorsActive[sensorIndex])
        return false;

    uint8_t tca_ch = sensorMapping[sensorIndex].tca_channel;
    uint8_t pca_ch = sensorMapping[sensorIndex].pca_channel;

    // Select TCA channel for this sensor board
    if (!mux.selectChannel(tca_ch))
    {
        Serial.printf("  Calibration: Failed to select TCA channel %d\n", tca_ch);
        return false;
    }
    delay(5);

    // Select PCA channel on the sensor board
    if (!pca_instances[tca_ch].selectChannel(pca_ch))
    {
        Serial.printf("  Calibration: Failed to select PCA channel %d\n", pca_ch);
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
        Wire.beginTransmission(0x60);
        Wire.write(0x08); // PS_DATA register
        if (Wire.endTransmission(false) != 0)
            continue;

        Wire.requestFrom((uint8_t)0x60, (uint8_t)2);
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

    // Write to PS_CANC register (0x05) - this value is subtracted from all readings
    Wire.beginTransmission(0x60);
    Wire.write(0x05);                   // PS_CANC register
    Wire.write(baseline & 0xFF);        // Low byte
    Wire.write((baseline >> 8) & 0xFF); // High byte
    uint8_t err = Wire.endTransmission();

    if (err != 0)
    {
        Serial.printf("  Calibration: Failed to write PS_CANC (I2C error %d)\n", err);
        return false;
    }

    // Verify by reading back
    delay(5);
    Wire.beginTransmission(0x60);
    Wire.write(0x05);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)0x60, (uint8_t)2);
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
        if (!sensorsActive[i])
        {
            Serial.printf("║ Sensor %d (P%dS%d): SKIPPED (not active)                                       ║\n",
                          i, sensorMapping[i].tca_channel + 1, sensorMapping[i].pca_channel + 1);
            continue;
        }

        char sensorName[8];
        snprintf(sensorName, sizeof(sensorName), "P%dS%d",
                 sensorMapping[i].tca_channel + 1, sensorMapping[i].pca_channel + 1);

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

    // Clean up multiplexer channels
    for (int i = 0; i < 3; i++)
    {
        mux.selectChannel(i);
        delay(2);
        pca_instances[i].disableAllChannels();
    }
    mux.disableAllChannels();

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

    Wire.beginTransmission(0x60);
    Wire.write(0x03);
    Wire.write(ps_conf1);
    Wire.write(ps_conf2);
    uint8_t err1 = Wire.endTransmission();

    delayMicroseconds(500); // Allow register to settle

    // Step 2: Configure PS_CONF3/PS_MS register (0x04)
    // PS_CONF3 (low byte): bits 6:5 = PS_MPS (multi-pulse), other bits default off
    // PS_MS (high byte): bits 2:0 = LED_I
    uint8_t ps_conf3 = (multiPulse & 0x03) << 5; // PS_MPS in bits 6:5 (1, 2, 4, or 8 pulses)
    uint8_t ps_ms = (led & 0x07);                // LED_I in bits 2:0, White channel enabled (bit 7 = 0)

    Wire.beginTransmission(0x60);
    Wire.write(0x04);
    Wire.write(ps_conf3);
    Wire.write(ps_ms);
    uint8_t err2 = Wire.endTransmission();

    Serial.printf("  Write: PS_CONF1/2=0x%02X%02X (err:%d), PS_CONF3/MS=0x%02X%02X (err:%d)\n",
                  ps_conf2, ps_conf1, err1, ps_ms, ps_conf3, err2);

    // Step 3: Verify by reading back - add longer delay for register to fully settle
    delay(10);

    // Read PS_CONF3/PS_MS (0x04)
    Wire.beginTransmission(0x60);
    Wire.write(0x04);
    Wire.endTransmission(false);
    Wire.requestFrom((uint8_t)0x60, (uint8_t)2);
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

        Wire.beginTransmission(0x60);
        Wire.write(0x04);
        Wire.write(ps_conf3);
        Wire.write(ps_ms);
        uint8_t err_retry = Wire.endTransmission();

        delay(20);

        // Verify again
        Wire.beginTransmission(0x60);
        Wire.write(0x04);
        Wire.endTransmission(false);
        Wire.requestFrom((uint8_t)0x60, (uint8_t)2);
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

    // First, scan the main I2C bus BEFORE any TCA channel selection
    Serial.println("║ STEP 1: Scanning main I2C bus (no TCA channel selected)                      ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    mux.disableAllChannels();
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
            else if (addr == 0x60)
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

        // Select TCA channel
        if (!mux.selectChannel(tca_ch))
        {
            Serial.println("║   ⚠️ Failed to select this channel!                                         ║");
            continue;
        }

        delay(20); // Longer delay for channel settling

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
                else if (addr == 0x60)
                    deviceName = "VCNL4040";

                Serial.printf("║   ✓ Found: 0x%02X (%s)                                  \n", addr, deviceName);
            }
        }

        if (channelDevices == 0)
        {
            Serial.println("║   (no devices found)                                                        ║");
        }
    }

    mux.disableAllChannels();

    // Additional diagnostics
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ STEP 3: Direct PCA9546A address probe at 0x74 on TCA channel 0               ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    // Try to select TCA channel 0 and probe 0x74 specifically with detailed error codes
    if (mux.selectChannel(0))
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

    mux.disableAllChannels();

    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ DEBUG SCAN COMPLETE - Check results above for clues                          ║");
    Serial.println("╚══════════════════════════════════════════════════════════════════════════════╝");
    Serial.println();
}

bool SensorManager::initializePCA()
{
    Serial.println("Scanning for PCA9546A multiplexers on TCA channels...");

    int pca_found_count = 0;

    // Scan all 3 TCA channels for sensor boards
    for (int tca_ch = 0; tca_ch < 3; tca_ch++)
    {
        Serial.print("  Scanning TCA channel ");
        Serial.println(tca_ch);

        // Select TCA channel
        if (!mux.selectChannel(tca_ch))
        {
            Serial.println("    ERROR: Failed to select TCA channel");
            continue;
        }

        delay(10);

        // Try common PCA9546A addresses
        uint8_t test_addresses[] = {0x74, 0x75, 0x76, 0x72, 0x71, 0x73, 0x77};
        bool pca_found = false;
        uint8_t working_address = 0;

        for (int i = 0; i < 7; i++)
        {
            uint8_t test_addr = test_addresses[i];

            PCA9546A test_pca(test_addr);
            if (test_pca.begin())
            {
                Serial.print("    PCA9546A found at 0x");
                Serial.println(test_addr, HEX);
                working_address = test_addr;
                pca_found = true;
                test_pca.disableAllChannels();
                break;
            }
        }

        if (pca_found)
        {
            // Update PCA instance for this TCA channel
            pca_addresses[tca_ch] = working_address;
            pca_instances[tca_ch] = PCA9546A(working_address);
            pca_instances[tca_ch].disableAllChannels();
            pca_found_count++;
        }
        else
        {
            Serial.println("    No PCA found on this channel");
        }
    }

    mux.disableAllChannels();

    Serial.print("Found ");
    Serial.print(pca_found_count);
    Serial.println(" sensor board(s)");

    if (pca_found_count == 0)
    {
        Serial.println("ERROR: No PCA9546A multiplexers found!");
        return false;
    }

    return true;
}

bool SensorManager::init(SensorConfiguration *config)
{
    Serial.println("Initializing Sensor Manager...");

    // Store configuration reference
    activeConfig = config;

    // Initialize I2C
    Wire.begin(43, 44);    // SDA=43, SCL=44 for T-Display S3
    Wire.setClock(400000); // 400 kHz (Fast Mode) - set BEFORE sensor initialization
    Serial.println("I2C clock set to 400 kHz");

    if (activeConfig != nullptr)
    {
        Serial.println("Configuration:");
        Serial.printf("  Sample Rate: %d Hz\n", activeConfig->sample_rate_hz);
        Serial.printf("  LED Current: %s\n", activeConfig->led_current.c_str());
        Serial.printf("  Integration Time: %s\n", activeConfig->integration_time.c_str());
        Serial.printf("  High Resolution: %s\n", activeConfig->high_resolution ? "enabled" : "disabled");
        Serial.printf("  Read Ambient: %s\n", activeConfig->read_ambient ? "enabled" : "disabled");
    }

    // Initialize TCA9548A multiplexer
    if (!mux.begin())
    {
        Serial.println("ERROR: Failed to initialize TCA9548A");
        return false;
    }
    Serial.println("TCA9548A initialized");

    // Run I2C debug scan to help troubleshoot sensor board detection
    debugI2CScan();

    // Initialize PCA9546A multiplexers
    if (!initializePCA())
    {
        Serial.println("ERROR: PCA initialization failed!");
        return false;
    }

    delay(500); // Give hardware time to settle

    // Initialize all VCNL4040 sensors
    int sensors_initialized = 0;

    for (int i = 0; i < NUM_SENSORS; i++)
    {
        uint8_t tca_ch = sensorMapping[i].tca_channel;
        uint8_t pca_ch = sensorMapping[i].pca_channel;

        Serial.print("Initializing sensor ");
        Serial.print(i);
        Serial.print(" (P");
        Serial.print(tca_ch + 1);
        Serial.print("S");
        Serial.print(pca_ch + 1);
        Serial.println(")...");

        // Skip if no PCA was found on this TCA channel
        if (pca_addresses[tca_ch] == 0)
        {
            Serial.println("  No sensor board on this channel");
            sensorsActive[i] = false;
            continue;
        }

        // Select TCA channel for this sensor board
        if (!mux.selectChannel(tca_ch))
        {
            Serial.println("  ERROR: Failed to select TCA channel");
            sensorsActive[i] = false;
            continue;
        }

        delay(50);

        // Select PCA channel on the sensor board
        if (!pca_instances[tca_ch].selectChannel(pca_ch))
        {
            Serial.println("  ERROR: Failed to select PCA channel");
            sensorsActive[i] = false;
            continue;
        }

        delay(50);

        // Check if VCNL4040 responds at standard address 0x60
        Wire.beginTransmission(0x60);
        byte error = Wire.endTransmission();
        if (error != 0)
        {
            Serial.print("  ERROR: No VCNL4040 at 0x60 (I2C error: ");
            Serial.print(error);
            Serial.println(")");
            sensorsActive[i] = false;
            continue;
        }

        // Initialize VCNL4040 - just verify device ID, don't use Adafruit library's begin()
        // The Adafruit library's begin() and subsequent calls were resetting our config!

        // Read device ID to verify sensor is present
        Wire.beginTransmission(0x60);
        Wire.write(0x0C); // Device ID register
        Wire.endTransmission(false);
        Wire.requestFrom(0x60, 2);

        if (Wire.available() >= 2)
        {
            uint8_t id_low = Wire.read();
            uint8_t id_high = Wire.read();
            uint16_t device_id = (id_high << 8) | id_low;

            if (device_id != 0x0186)
            {
                Serial.printf("  ERROR: Wrong device ID 0x%04X (expected 0x0186)\n", device_id);
                sensorsActive[i] = false;
                continue;
            }
            Serial.printf("  Device ID: 0x%04X ✓\n", device_id);
        }
        else
        {
            Serial.println("  ERROR: Failed to read device ID");
            sensorsActive[i] = false;
            continue;
        }

        // Apply configuration using DIRECT I2C only (no Adafruit library!)
        if (activeConfig != nullptr)
        {
            applySensorConfig(i);
        }
        else
        {
            // Default configuration - direct I2C write
            // PS_CONF1/2: Enable proximity, 1T integration, 1/40 duty, high res
            Wire.beginTransmission(0x60);
            Wire.write(0x03);
            Wire.write(0x00); // PS_CONF1: PS_IT=0 (1T), PS_Duty=0 (1/40), PS_SD=0 (enabled)
            Wire.write(0x08); // PS_CONF2: PS_HD=1 (high res)
            Wire.endTransmission();

            // PS_MS: 200mA LED current
            Wire.beginTransmission(0x60);
            Wire.write(0x04);
            Wire.write(0x00); // PS_MS low
            Wire.write(0x07); // PS_MS high: LED_I=7 (200mA)
            Wire.endTransmission();

            Serial.println("  Applied default config (200mA, 1T, 1/40, HighRes)");
        }

        Serial.println("  Sensor initialized successfully!");
        sensorsActive[i] = true;
        sensors_initialized++;
    }

    // Clean up - disable all channels
    // IMPORTANT: Must select each TCA channel before disabling its PCA!
    for (int i = 0; i < 3; i++)
    {
        mux.selectChannel(i);
        delay(2);
        pca_instances[i].disableAllChannels();
    }
    mux.disableAllChannels();

    Serial.print("Initialized ");
    Serial.print(sensors_initialized);
    Serial.print(" / ");
    Serial.print(NUM_SENSORS);
    Serial.println(" sensors");

    if (sensors_initialized == 0)
    {
        Serial.println("ERROR: No sensors initialized!");
        return false;
    }

    initialized = true;
    Serial.println("Sensor Manager initialization complete!");

    // Dump configuration for all sensors to verify they were configured correctly
    dumpSensorConfiguration();

    // Calibrate PS_CANC for all sensors to remove cover window reflection offset
    // This should be done with covers installed but NO objects near the sensors
    Serial.println("Starting baseline calibration for cover offset compensation...");
    delay(500); // Brief delay to ensure stable readings
    calibrateProximityCancellation();

    return true;
}

bool SensorManager::readSensor(uint8_t sensorIndex, SensorReading &reading)
{
    if (sensorIndex >= NUM_SENSORS)
        return false;

    // Skip if sensor not active
    if (!sensorsActive[sensorIndex])
        return false;

    uint8_t tca_ch = sensorMapping[sensorIndex].tca_channel;
    uint8_t pca_ch = sensorMapping[sensorIndex].pca_channel;

    // Select TCA channel for this sensor board
    if (!mux.selectChannel(tca_ch))
        return false;

    // Select PCA channel on the sensor board
    if (!pca_instances[tca_ch].selectChannel(pca_ch))
        return false;

    reading.timestamp_ms = millis();
    reading.position = sensorIndex;

    // Calculate PCB ID and side from position
    // Position 0,1 -> PCB 1; Position 2,3 -> PCB 2; Position 4,5 -> PCB 3
    reading.pcb_id = (sensorIndex / 2) + 1; // 0,1->1  2,3->2  4,5->3

    // Position 0,2,4 -> Side 1 (S1); Position 1,3,5 -> Side 2 (S2)
    reading.side = (sensorIndex % 2) + 1; // 0,2,4->1  1,3,5->2

    // Read proximity directly via I2C (bypass Adafruit library to avoid config conflicts)
    Wire.beginTransmission(0x60);
    Wire.write(0x08); // PS_DATA register
    Wire.endTransmission(false);
    Wire.requestFrom(0x60, 2);

    if (Wire.available() >= 2)
    {
        uint8_t prox_low = Wire.read();
        uint8_t prox_high = Wire.read();
        reading.proximity = (prox_high << 8) | prox_low;
    }
    else
    {
        reading.proximity = 0;
    }

    // Conditionally read ambient light (skip if disabled for speed)
    if (activeConfig != nullptr && !activeConfig->read_ambient)
    {
        reading.ambient = 0; // Mark as not read
    }
    else
    {
        // Read ambient light directly via I2C
        Wire.beginTransmission(0x60);
        Wire.write(0x09); // ALS_DATA register
        Wire.endTransmission(false);
        Wire.requestFrom(0x60, 2);

        if (Wire.available() >= 2)
        {
            uint8_t als_low = Wire.read();
            uint8_t als_high = Wire.read();
            reading.ambient = (als_high << 8) | als_low;
        }
        else
        {
            reading.ambient = 0;
        }
    }

    return true;
}

void SensorManager::sensorTaskFunction(void *parameter)
{
    SensorManager *manager = (SensorManager *)parameter;

    Serial.println("Sensor task started on Core 0");

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
            unsigned long cycleTimestamp = millis();

            int successfulReads = 0;
            int failedReads = 0;

            // Read all active sensors (REVERSED for timing test - normally 0 to NUM_SENSORS)
            for (int i = NUM_SENSORS - 1; i >= 0; i--)
            {
                // Check stop flag between sensor reads for faster response
                if (manager->stopRequested)
                    break;

                // Skip inactive sensors
                if (!manager->sensorsActive[i])
                    continue;

                if (manager->readSensor(i, reading))
                {
                    // Override timestamp with cycle timestamp for synchronization
                    reading.timestamp_ms = cycleTimestamp;

                    successfulReads++;
                    // Send to queue (non-blocking)
                    if (xQueueSend(manager->dataQueue, &reading, 0) != pdTRUE)
                    {
                        // Queue full - data lost
                        // Could increment a dropped sample counter here
                    }
                }
                else
                {
                    failedReads++;
                }
            }

            // Track consecutive failures and log errors
            if (failedReads > 0)
            {
                consecutiveFailures++;
                // Log every 100 failures or first 3 failures
                if (consecutiveFailures <= 3 || (millis() - lastErrorLog > 5000))
                {
                    Serial.print("WARNING: Sensor read failures: ");
                    Serial.print(failedReads);
                    Serial.print(" failed, ");
                    Serial.print(successfulReads);
                    Serial.println(" succeeded");
                    lastErrorLog = millis();
                }
            }
            else
            {
                consecutiveFailures = 0;
            }

            // Clean up - disable all channels after reading cycle
            // IMPORTANT: Must select each TCA channel before disabling its PCA!
            for (int j = 0; j < 3; j++)
            {
                manager->mux.selectChannel(j);
                delayMicroseconds(100);
                manager->pca_instances[j].disableAllChannels();
            }
            manager->mux.disableAllChannels();
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

    // Clean up I2C bus state
    manager->cleanupI2CBus();

    Serial.println("Sensor task cleanup complete, exiting.");

    // Mark task as NULL before deleting (atomic-ish on ESP32)
    manager->sensorTask = NULL;

    // Delete ourselves - this is the proper way to end a FreeRTOS task
    vTaskDelete(NULL);
}

bool SensorManager::startCollection(QueueHandle_t queue)
{
    if (!initialized)
    {
        Serial.println("ERROR: Sensors not initialized");
        return false;
    }

    if (sensorTask != NULL)
    {
        Serial.println("Collection already running");
        return false;
    }

    dataQueue = queue;

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

    Serial.println("Sensor collection started");
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

    // Signal the task to stop gracefully
    stopRequested = true;

    // Wait for task to finish with timeout (max 500ms)
    // The task checks stopRequested frequently and will exit cleanly
    unsigned long startWait = millis();
    const unsigned long STOP_TIMEOUT_MS = 500;

    while (sensorTask != NULL && (millis() - startWait) < STOP_TIMEOUT_MS)
    {
        // Feed watchdog while waiting
        taskYIELD();
        delay(10);
    }

    // Check if task stopped gracefully
    if (sensorTask == NULL)
    {
        Serial.println("Sensor task stopped gracefully");
    }
    else
    {
        // Task didn't stop in time - force delete as fallback
        // This shouldn't happen normally, but provides safety
        Serial.println("WARNING: Sensor task did not stop in time, forcing deletion");
        vTaskDelete(sensorTask);
        sensorTask = NULL;

        // Clean up I2C bus since task couldn't do it
        cleanupI2CBus();
        Serial.println("I2C bus cleaned up after forced stop");
    }

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
        SensorMetadata meta;
        meta.position = i;
        meta.pcb_id = (i / 2) + 1;      // PCB 1, 2, or 3
        meta.side = (i % 2) + 1;        // Side 1 or 2
        meta.active = sensorsActive[i]; // Actual sensor status

        // Generate name: P1S1, P2S2, etc.
        meta.name = "P" + String(meta.pcb_id) + "S" + String(meta.side);

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

    // CRITICAL: Ensure I2C bus is in a clean state before reconfiguration
    // This prevents hangs if the bus was left in an inconsistent state
    Serial.println("  Ensuring I2C bus is clean...");
    cleanupI2CBus();
    delay(50); // Give hardware time to settle

    // Update configuration
    activeConfig = config;
    Serial.println("  Applying new configuration to sensors...");

    // Reapply configuration to all active sensors
    // Track the last TCA channel to properly clean up when switching
    int8_t lastTcaChannel = -1;

    for (int i = 0; i < NUM_SENSORS; i++)
    {
        if (sensorsActive[i] && activeConfig != nullptr)
        {
            Serial.printf("  Reconfiguring sensor %d...\n", i);

            uint8_t tca_ch = sensorMapping[i].tca_channel;
            uint8_t pca_ch = sensorMapping[i].pca_channel;

            // CRITICAL FIX: If switching TCA channels, disable the PCA on the previous channel first
            // This prevents I2C bus contention when moving between sensor boards
            if (lastTcaChannel != -1 && lastTcaChannel != tca_ch)
            {
                Serial.printf("    Switching TCA channel %d -> %d, cleaning up...\n", lastTcaChannel, tca_ch);
                // Select the old TCA channel and disable its PCA
                mux.selectChannel(lastTcaChannel);
                delay(5);
                pca_instances[lastTcaChannel].disableAllChannels();
                delay(5);
            }

            // Select TCA channel for this sensor board
            if (!mux.selectChannel(tca_ch))
            {
                Serial.printf("    WARNING: Failed to select TCA channel %d\n", tca_ch);
                continue;
            }
            delay(10); // Increased delay for TCA settling

            if (!pca_instances[tca_ch].selectChannel(pca_ch))
            {
                Serial.printf("    WARNING: Failed to select PCA channel %d\n", pca_ch);
                continue;
            }
            delay(10); // Increased delay for PCA settling

            // Reapply configuration
            applySensorConfig(i);
            Serial.printf("    Sensor %d reconfigured.\n", i);

            // Remember this TCA channel for cleanup on next iteration
            lastTcaChannel = tca_ch;

            // CRITICAL: Feed watchdog timer during lengthy reconfiguration
            // This prevents Core 1 watchdog reset during sensor reconfiguration
            taskYIELD();
        }
    }

    // Clean up
    Serial.println("  Cleaning up multiplexer channels...");
    // IMPORTANT: Must select each TCA channel before disabling its PCA!
    for (int i = 0; i < 3; i++)
    {
        mux.selectChannel(i);
        delay(2);
        pca_instances[i].disableAllChannels();
    }
    mux.disableAllChannels();

    // Final yield to ensure watchdog is fed
    taskYIELD();

    Serial.println("  Sensors reconfigured successfully!");

    // Dump configuration to verify all sensors got the new settings
    dumpSensorConfiguration();

    // Re-calibrate PS_CANC after configuration change
    // Configuration changes (especially LED current, integration time) can affect baseline
    Serial.println("  Re-calibrating baseline after configuration change...");
    delay(200);
    calibrateProximityCancellation();

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
        uint8_t tca_ch = sensorMapping[i].tca_channel;
        uint8_t pca_ch = sensorMapping[i].pca_channel;

        // Build sensor name
        char sensorName[8];
        snprintf(sensorName, sizeof(sensorName), "P%dS%d", tca_ch + 1, pca_ch + 1);

        if (!sensorsActive[i])
        {
            Serial.printf("║ %-6s │  %d  │  %d  │   NO   │     N/A     │     N/A     │  N/A  │   N/A    ║\n",
                          sensorName, tca_ch, pca_ch);
            continue;
        }

        // Select the sensor's channel with proper delays
        if (!mux.selectChannel(tca_ch))
        {
            Serial.printf("║ %-6s │  %d  │  %d  │  YES   │  TCA ERR    │   TCA ERR   │ ERR   │   ERR    ║\n",
                          sensorName, tca_ch, pca_ch);
            continue;
        }
        delay(10); // Increased delay for multiplexer settling

        if (!pca_instances[tca_ch].selectChannel(pca_ch))
        {
            Serial.printf("║ %-6s │  %d  │  %d  │  YES   │  PCA ERR    │   PCA ERR   │ ERR   │   ERR    ║\n",
                          sensorName, tca_ch, pca_ch);
            continue;
        }
        delay(10); // Increased delay for multiplexer settling

        // Verify we can communicate with the sensor by checking device ID first
        Wire.beginTransmission(0x60);
        Wire.write(0x0C); // Device ID register
        if (Wire.endTransmission(false) != 0)
        {
            Serial.printf("║ %-6s │  %d  │  %d  │  YES   │  I2C ERR    │   I2C ERR   │ ERR   │   ERR    ║\n",
                          sensorName, tca_ch, pca_ch);
            continue;
        }
        Wire.requestFrom((uint8_t)0x60, (uint8_t)2);
        uint8_t id_low = Wire.available() ? Wire.read() : 0;
        uint8_t id_high = Wire.available() ? Wire.read() : 0;
        uint16_t device_id = (id_high << 8) | id_low;

        if (device_id != 0x0186)
        {
            Serial.printf("║ %-6s │  %d  │  %d  │  YES   │ BAD ID 0x%04X                              ║\n",
                          sensorName, tca_ch, pca_ch, device_id);
            continue;
        }

        // Read PS_CONF1/2 register (0x03) - contains integration time, duty cycle, high-res
        uint8_t ps_conf1_low = 0, ps_conf1_high = 0;
        Wire.beginTransmission(0x60);
        Wire.write(0x03);
        if (Wire.endTransmission(false) == 0)
        {
            Wire.requestFrom((uint8_t)0x60, (uint8_t)2);
            if (Wire.available() >= 2)
            {
                ps_conf1_low = Wire.read();
                ps_conf1_high = Wire.read();
            }
        }

        // Read PS_CONF3/PS_MS register (0x04) - contains LED current
        uint8_t ps_ms_low = 0, ps_ms_high = 0;
        Wire.beginTransmission(0x60);
        Wire.write(0x04);
        if (Wire.endTransmission(false) == 0)
        {
            Wire.requestFrom((uint8_t)0x60, (uint8_t)2);
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

    // Clean up
    // IMPORTANT: Must select each TCA channel before disabling its PCA!
    for (int i = 0; i < 3; i++)
    {
        mux.selectChannel(i);
        delay(2);
        pca_instances[i].disableAllChannels();
    }
    mux.disableAllChannels();
}
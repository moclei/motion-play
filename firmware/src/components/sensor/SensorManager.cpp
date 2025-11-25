#include "SensorManager.h"

SensorManager::SensorManager() : mux(0x70)
{
    // Constructor
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

bool SensorManager::applySensorConfig(uint8_t sensorIndex)
{
    if (sensorIndex >= NUM_SENSORS || activeConfig == nullptr)
        return false;

    // Apply LED current
    VCNL4040_LEDCurrent led = parseLEDCurrent(activeConfig->led_current);
    sensors[sensorIndex].setProximityLEDCurrent(led);

    // Apply integration time
    VCNL4040_ProximityIntegration integration = parseIntegrationTime(activeConfig->integration_time);
    sensors[sensorIndex].setProximityIntegrationTime(integration);

    // Apply high resolution setting
    sensors[sensorIndex].setProximityHighResolution(activeConfig->high_resolution);

    Serial.printf("  Applied config: LED=%s, Integration=%s, HighRes=%s, ReadAmbient=%s\n",
                  activeConfig->led_current.c_str(),
                  activeConfig->integration_time.c_str(),
                  activeConfig->high_resolution ? "true" : "false",
                  activeConfig->read_ambient ? "true" : "false");

    return true;
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

        // Try to initialize VCNL4040
        if (!sensors[i].begin())
        {
            Serial.println("  ERROR: VCNL4040 initialization failed");
            sensorsActive[i] = false;
            continue;
        }

        // Configure sensor (using Adafruit VCNL4040 API)
        sensors[i].enableProximity(true);

        // Apply configuration if provided, otherwise use defaults
        if (activeConfig != nullptr)
        {
            applySensorConfig(i);
        }
        else
        {
            // Default configuration
            sensors[i].setProximityLEDCurrent(VCNL4040_LED_CURRENT_200MA);
            sensors[i].setProximityIntegrationTime(VCNL4040_PROXIMITY_INTEGRATION_TIME_1T);
            sensors[i].setProximityHighResolution(true);
        }

        // Query and log actual integration time (WARNING: has 50ms delay!)
        VCNL4040_ProximityIntegration pit = sensors[i].getProximityIntegrationTime();
        Serial.printf("  Proximity Integration Time: %d (", pit);
        switch (pit)
        {
        case VCNL4040_PROXIMITY_INTEGRATION_TIME_1T:
            Serial.print("1T");
            break;
        case VCNL4040_PROXIMITY_INTEGRATION_TIME_1_5T:
            Serial.print("1.5T");
            break;
        case VCNL4040_PROXIMITY_INTEGRATION_TIME_2T:
            Serial.print("2T");
            break;
        case VCNL4040_PROXIMITY_INTEGRATION_TIME_2_5T:
            Serial.print("2.5T");
            break;
        case VCNL4040_PROXIMITY_INTEGRATION_TIME_3T:
            Serial.print("3T");
            break;
        case VCNL4040_PROXIMITY_INTEGRATION_TIME_3_5T:
            Serial.print("3.5T");
            break;
        case VCNL4040_PROXIMITY_INTEGRATION_TIME_4T:
            Serial.print("4T");
            break;
        case VCNL4040_PROXIMITY_INTEGRATION_TIME_8T:
            Serial.print("8T");
            break;
        default:
            Serial.print("UNKNOWN");
        }
        Serial.println(")");

        // Read PS_CONF1 register directly to check PS_Duty setting
        // PS_Duty is in bits 7:6 of PS_CONF1 low byte (register 0x03)
        Wire.beginTransmission(0x60);
        Wire.write(0x03); // PS_CONF1 register
        Wire.endTransmission();
        Wire.requestFrom(0x60, 2);

        if (Wire.available() >= 2)
        {
            uint8_t ps_conf1_low = Wire.read();
            uint8_t ps_conf1_high = Wire.read();

            uint8_t ps_duty = (ps_conf1_low >> 6) & 0x03; // Extract bits 7:6
            Serial.printf("  PS_Duty setting: %d (", ps_duty);

            switch (ps_duty)
            {
            case 0:
                Serial.println("1/40 -> ~200 Hz max) FAST");
                break;
            case 1:
                Serial.println("1/80 -> ~100 Hz max)");
                break;
            case 2:
                Serial.println("1/160 -> ~50 Hz max)");
                break;
            case 3:
                Serial.println("1/320 -> ~25 Hz max) SLOW - THIS IS YOUR BOTTLENECK!");
                break;
            }

            Serial.printf("  PS_CONF1 register: 0x%02X%02X\n", ps_conf1_high, ps_conf1_low);
        }
        else
        {
            Serial.println("  WARNING: Failed to read PS_CONF1 register!");
        }

        Serial.println("  Sensor initialized successfully!");
        sensorsActive[i] = true;
        sensors_initialized++;
    }

    // Clean up - disable all channels
    for (int i = 0; i < 3; i++)
    {
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

    // Always read proximity
    reading.proximity = sensors[sensorIndex].getProximity();

    // Conditionally read ambient light (skip if disabled for speed)
    if (activeConfig != nullptr && !activeConfig->read_ambient)
    {
        reading.ambient = 0; // Mark as not read
    }
    else
    {
        reading.ambient = sensors[sensorIndex].getAmbientLight();
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

    while (true)
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

            // Read all active sensors
            for (int i = 0; i < NUM_SENSORS; i++)
            {
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
            for (int j = 0; j < 3; j++)
            {
                manager->pca_instances[j].disableAllChannels();
            }
            manager->mux.disableAllChannels();
        }

        // Note: Removed vTaskDelay(1) to maximize sample rate
        // I2C operations provide enough yield time for other tasks
    }
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

    // Create sensor task on Core 0
    xTaskCreatePinnedToCore(
        sensorTaskFunction,
        "SensorTask",
        4096, // Stack size
        this, // Parameter
        2,    // Priority
        &sensorTask,
        0 // Core 0
    );

    Serial.println("Sensor collection started");
    return true;
}

void SensorManager::stopCollection()
{
    if (sensorTask != NULL)
    {
        vTaskDelete(sensorTask);
        sensorTask = NULL;
        Serial.println("Sensor collection stopped");
    }
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
        delay(250);  // Allow task to fully stop and release I2C bus
        Serial.println("  Collection stopped.");
    }

    // Update configuration
    activeConfig = config;
    Serial.println("  Applying new configuration to sensors...");

    // Reapply configuration to all active sensors
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        if (sensorsActive[i] && activeConfig != nullptr)
        {
            Serial.printf("  Reconfiguring sensor %d...\n", i);

            uint8_t tca_ch = sensorMapping[i].tca_channel;
            uint8_t pca_ch = sensorMapping[i].pca_channel;

            // Select channels
            if (!mux.selectChannel(tca_ch))
            {
                Serial.printf("    WARNING: Failed to select TCA channel %d\n", tca_ch);
                continue;
            }
            delay(10);

            if (!pca_instances[tca_ch].selectChannel(pca_ch))
            {
                Serial.printf("    WARNING: Failed to select PCA channel %d\n", pca_ch);
                continue;
            }
            delay(10);

            // Reapply configuration (Note: has 50ms delay in setProximityIntegrationTime)
            applySensorConfig(i);
            Serial.printf("    Sensor %d reconfigured.\n", i);
        }
    }

    // Clean up
    Serial.println("  Cleaning up multiplexer channels...");
    for (int i = 0; i < 3; i++)
    {
        pca_instances[i].disableAllChannels();
    }
    mux.disableAllChannels();

    Serial.println("  Sensors reconfigured successfully!");
    return true;
}
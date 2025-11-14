#include "SensorManager.h"

SensorManager::SensorManager() : mux(0x70)
{
    // Constructor
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

bool SensorManager::init()
{
    Serial.println("Initializing Sensor Manager...");

    // Initialize I2C
    Wire.begin(43, 44);    // SDA=43, SCL=44 for T-Display S3
    Wire.setClock(400000); // 400kHz I2C

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
        sensors[i].setProximityLEDCurrent(VCNL4040_LED_CURRENT_200MA);
        sensors[i].setProximityIntegrationTime(VCNL4040_PROXIMITY_INTEGRATION_TIME_1T);
        sensors[i].setProximityHighResolution(true);

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

    reading.proximity = sensors[sensorIndex].getProximity();
    reading.ambient = sensors[sensorIndex].getAmbientLight();

    return true;
}

void SensorManager::sensorTaskFunction(void *parameter)
{
    SensorManager *manager = (SensorManager *)parameter;

    Serial.println("Sensor task started on Core 0");

    unsigned long lastSampleTime = micros();
    SensorReading reading;

    while (true)
    {
        unsigned long currentTime = micros();

        // Check if it's time for next sample
        if (currentTime - lastSampleTime >= SAMPLE_INTERVAL_US)
        {
            lastSampleTime = currentTime;

            // Read all active sensors
            for (int i = 0; i < NUM_SENSORS; i++)
            {
                // Skip inactive sensors
                if (!manager->sensorsActive[i])
                    continue;

                if (manager->readSensor(i, reading))
                {
                    // Send to queue (non-blocking)
                    if (xQueueSend(manager->dataQueue, &reading, 0) != pdTRUE)
                    {
                        // Queue full - data lost
                        // Could increment a dropped sample counter here
                    }
                }
            }

            // Clean up - disable all channels after reading cycle
            for (int j = 0; j < 3; j++)
            {
                manager->pca_instances[j].disableAllChannels();
            }
            manager->mux.disableAllChannels();
        }

        // Small yield to prevent watchdog
        vTaskDelay(1);
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
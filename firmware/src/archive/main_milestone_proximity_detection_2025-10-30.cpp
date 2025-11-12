/**
 * Motion Play v2.2 - Direct Register Configuration - October 28, 2025
 *
 * APPROACH: Adafruit library + Direct VCNL4040 register configuration
 * - Reverted from SparkFun library (broke ambient readings)
 * - Using Adafruit library for basic communication (working ambient)
 * - Direct register writes to configure proximity sensor properly
 * - Based on Vishay VCNL4040 datasheet register specifications
 *
 * Key Configuration:
 * - PS_CONF1: 8T integration time, proximity sensor enabled
 * - PS_CONF2: 200mA LED current, 16-bit resolution, interrupts disabled
 * - PS_CONF3: Smart persistence enabled for stable readings
 * - Expected: Proximity values 0-65535 (not 0-1 logic mode)
 *
 * Hardware: T-Display-S3 (ESP32-S3) with sensor PCB on TCA channel 0
 */

#include <Arduino.h>
#include <TFT_eSPI.h>
#include <Wire.h>
#include <TCA9548.h>           // robtillaart TCA9548 library
#include <Adafruit_VCNL4040.h> // Adafruit VCNL4040 library (back to working version)
#include "pin_config.h"

// ==================================================================================
// HARDWARE CONFIGURATION
// ==================================================================================

// TCA9548A I2C Multiplexer
#define TCA9548A_ADDRESS 0x70
TCA9548 tca(TCA9548A_ADDRESS);

// PCA9546A I2C Multiplexer (on sensor boards)
#define PCA9546A_ADDRESS 0x72

// Simple PCA9546A wrapper class
class PCA9546A
{
private:
    uint8_t address;

public:
    PCA9546A(uint8_t addr) : address(addr) {}

    bool begin()
    {
        Wire.beginTransmission(address);
        return (Wire.endTransmission() == 0);
    }

    bool selectChannel(uint8_t channel)
    {
        if (channel > 3)
            return false;
        Wire.beginTransmission(address);
        Wire.write(1 << channel);
        return (Wire.endTransmission() == 0);
    }

    bool disableAllChannels()
    {
        Wire.beginTransmission(address);
        Wire.write(0x00);
        return (Wire.endTransmission() == 0);
    }
};

PCA9546A pca(PCA9546A_ADDRESS);

// VCNL4040 Proximity Sensors
Adafruit_VCNL4040 vcnl_sensors[4]; // One for each possible PCA channel (back to Adafruit)

// ==================================================================================
// SENSOR DATA STRUCTURE
// ==================================================================================

struct SensorData
{
    bool initialized = false;
    bool active = false;
    uint16_t proximity = 0;
    uint16_t ambient = 0;
    bool object_detected = false;
    uint32_t last_reading_time = 0;
    uint32_t last_detection_time = 0;
    uint32_t error_count = 0;
    uint16_t max_proximity = 0; // Track maximum proximity seen
    String status = "Unknown";
};

SensorData sensors[4]; // One for each PCA channel
uint32_t last_display_update = 0;
uint32_t system_start_time = 0;
bool sensors_initialized_on_boot = false; // Track if we've tried initialization

// ==================================================================================
// DISPLAY CONFIGURATION
// ==================================================================================

#define VERSION_MAJOR 2
#define VERSION_MINOR 1
#define VERSION_PATCH 0

// Display configuration (Landscape mode: 320x170)
#define SCREEN_WIDTH 320
#define SCREEN_HEIGHT 170

// Colors (RGB565)
#define COLOR_BLACK 0x0000
#define COLOR_WHITE 0xFFFF
#define COLOR_GREEN 0x07E0
#define COLOR_RED 0xF800
#define COLOR_BLUE 0x001F
#define COLOR_YELLOW 0xFFE0
#define COLOR_CYAN 0x07FF
#define COLOR_MAGENTA 0xF81F
#define COLOR_GRAY 0x8410
#define COLOR_DARK_GRAY 0x4208
#define COLOR_ORANGE 0xFD20

// Detection threshold - lowered for better sensitivity
#define PROXIMITY_THRESHOLD 50      // Much lower threshold for better detection
#define SENSOR_UPDATE_INTERVAL 200  // ms between sensor readings
#define DISPLAY_UPDATE_INTERVAL 500 // ms between display updates

// Detection history
#define MAX_DETECTION_HISTORY 5
struct DetectionEvent
{
    uint32_t timestamp;
    int channel;
    uint16_t proximity_value;
    bool active;
};
DetectionEvent detection_history[MAX_DETECTION_HISTORY];
int detection_history_count = 0;

TFT_eSPI tft = TFT_eSPI();

// ==================================================================================
// SYSTEM INITIALIZATION
// ==================================================================================

bool initializeDisplay()
{
    Serial.println("Initializing T-Display-S3...");

    // Power on display and backlight
    pinMode(PIN_POWER_ON, OUTPUT);
    digitalWrite(PIN_POWER_ON, HIGH);

    pinMode(PIN_LCD_BL, OUTPUT);
    digitalWrite(PIN_LCD_BL, HIGH);

    delay(100);

    // Initialize TFT
    tft.init();
    tft.setRotation(1); // Landscape mode
    tft.fillScreen(COLOR_BLACK);

    // Welcome message
    tft.setTextColor(COLOR_GREEN, COLOR_BLACK);
    tft.setTextSize(2);
    tft.setCursor(10, 10);
    tft.println("Motion Play v2.1");
    tft.setTextSize(1);
    tft.setCursor(10, 35);
    tft.setTextColor(COLOR_CYAN, COLOR_BLACK);
    tft.println("Sensor Display Mode");

    delay(2000);
    return true;
}

bool initializeI2C()
{
    Serial.println("Initializing I2C...");

    // Initialize I2C with custom pins
    Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);
    Wire.setClock(100000); // 100kHz for reliability

    // Initialize TCA reset pin
    pinMode(PIN_TCA_RESET, OUTPUT);
    digitalWrite(PIN_TCA_RESET, HIGH);

    Serial.println("I2C initialized - SDA: GPIO" + String(PIN_IIC_SDA) + ", SCL: GPIO" + String(PIN_IIC_SCL));
    return true;
}

bool initializeTCA()
{
    Serial.println("Initializing TCA9548A...");

    if (!tca.begin())
    {
        Serial.println("TCA9548A initialization FAILED!");
        return false;
    }

    if (!tca.isConnected())
    {
        Serial.println("TCA9548A not responding!");
        return false;
    }

    tca.disableAllChannels();
    Serial.println("TCA9548A initialized successfully");
    return true;
}

bool initializePCA()
{
    Serial.println("Initializing PCA9546A...");

    // Select TCA channel 0 (sensor board)
    if (!tca.selectChannel(0))
    {
        Serial.println("Failed to select TCA channel 0");
        return false;
    }

    delay(10);

    if (!pca.begin())
    {
        Serial.println("PCA9546A initialization FAILED!");
        Serial.println("Scanning for PCA9546A on TCA channel 0...");

        // I2C scan to find the actual PCA address
        bool found_pca = false;
        for (byte addr = 0x70; addr <= 0x77; addr++) // PCA9546A address range
        {
            Wire.beginTransmission(addr);
            byte error = Wire.endTransmission();
            if (error == 0)
            {
                Serial.println("  Found device at 0x" + String(addr, HEX) + " - This might be your PCA9546A!");
                found_pca = true;
            }
            delay(1); // Small delay between scans
        }

        if (!found_pca)
        {
            Serial.println("  No devices found in PCA9546A address range (0x70-0x77)");
            Serial.println("  Scanning full I2C range on TCA channel 0...");

            for (byte addr = 0x08; addr <= 0x77; addr++)
            {
                Wire.beginTransmission(addr);
                byte error = Wire.endTransmission();
                if (error == 0)
                {
                    Serial.println("    Found device at 0x" + String(addr, HEX));
                }
                delay(1);
            }
        }

        tca.disableAllChannels();
        return false;
    }

    pca.disableAllChannels();
    Serial.println("PCA9546A initialized successfully");
    return true;
}

// ==================================================================================
// SENSOR MANAGEMENT
// ==================================================================================

// Add detection to history
void addDetectionEvent(int channel, uint16_t proximity_value)
{
    // Shift history array
    for (int i = MAX_DETECTION_HISTORY - 1; i > 0; i--)
    {
        detection_history[i] = detection_history[i - 1];
    }

    // Add new event
    detection_history[0].timestamp = millis();
    detection_history[0].channel = channel;
    detection_history[0].proximity_value = proximity_value;
    detection_history[0].active = true;

    if (detection_history_count < MAX_DETECTION_HISTORY)
    {
        detection_history_count++;
    }

    Serial.println("🔴 DETECTION! Channel " + String(channel) + " - Proximity: " + String(proximity_value));
}

void initializeSensors()
{
    Serial.println("Initializing VCNL4040 sensors...");

    // Add longer delays for hardware settling
    delay(500); // Give hardware time to settle

    // Select TCA channel 0 (sensor board)
    if (!tca.selectChannel(0))
    {
        Serial.println("Failed to select TCA channel 0 for sensor init");
        return;
    }

    delay(100); // Extra delay after TCA selection

    // Test each PCA channel for VCNL4040 sensors
    // Start with channel 0 (known working), then test others
    int test_order[] = {0, 1, 2, 3}; // Test in this order
    for (int i = 0; i < 4; i++)
    {
        int pca_channel = test_order[i];
        Serial.println("Testing PCA channel " + String(pca_channel) + "...");

        // Reset sensor data
        sensors[pca_channel].initialized = false;
        sensors[pca_channel].active = false;
        sensors[pca_channel].status = "Testing...";

        // Select PCA channel
        if (!pca.selectChannel(pca_channel))
        {
            sensors[pca_channel].status = "PCA Select Failed";
            Serial.println("  PCA channel " + String(pca_channel) + " select failed");
            continue;
        }

        delay(50); // Longer delay for channel switching

        // Check if device responds at 0x60 (standard VCNL4040 address)
        Wire.beginTransmission(0x60);
        byte error = Wire.endTransmission();
        if (error != 0)
        {
            sensors[pca_channel].status = "No Device (0x60)";
            Serial.println("  No device at 0x60 on PCA channel " + String(pca_channel) + " (I2C error: " + String(error) + ")");

            // For any channel, also check if there's a device at 0x70 (unusual but possible)
            Wire.beginTransmission(0x70);
            byte error_70 = Wire.endTransmission();
            if (error_70 == 0)
            {
                Serial.println("  ⚠️  Found device at 0x70 on PCA channel " + String(pca_channel));
                if (pca_channel == 1)
                {
                    Serial.println("      This could be IC2 with wrong address, or PCA bleed-through");
                }
                else
                {
                    Serial.println("      This is likely PCA9546A bleed-through (channel isolation issue)");
                    Serial.println("      The PCA's own address (0x70) is visible on this channel");
                }
            }

            // For channel 1, do extra debugging since hardware looks good
            if (pca_channel == 1)
            {
                Serial.println("  🔍 Extra debugging for Channel 1 (IC2):");

                // Try multiple times
                for (int retry = 0; retry < 3; retry++)
                {
                    delay(100);
                    Wire.beginTransmission(0x60);
                    byte retry_error = Wire.endTransmission();
                    Serial.println("    Retry " + String(retry + 1) + ": I2C error " + String(retry_error));
                }

                // Try scanning all addresses on this channel
                Serial.println("    Scanning all I2C addresses on PCA channel 1:");
                bool found_any = false;
                for (byte addr = 0x08; addr <= 0x77; addr++)
                {
                    Wire.beginTransmission(addr);
                    if (Wire.endTransmission() == 0)
                    {
                        Serial.println("      Found device at 0x" + String(addr, HEX));
                        found_any = true;
                    }
                    delay(1); // Small delay between scans
                }
                if (!found_any)
                {
                    Serial.println("      No devices found on PCA channel 1");
                    Serial.println("      This suggests either:");
                    Serial.println("        1. PCA channel 1 routing issue");
                    Serial.println("        2. IC2 power supply problem");
                    Serial.println("        3. IC2 not properly soldered");
                    Serial.println("        4. PCA9546A channel 1 malfunction");
                }
                else
                {
                    Serial.println("      🔍 IMPORTANT: Found devices on PCA channel 1!");
                    Serial.println("      If device is at 0x70, this could be:");
                    Serial.println("        1. IC2 has wrong I2C address (should be 0x60)");
                    Serial.println("        2. Another PCA9546A on sensor board");
                    Serial.println("        3. I2C routing/addressing issue");
                    Serial.println("      Let's test if IC2 is actually at 0x70...");

                    // Test if there's a VCNL4040 at 0x70 instead of 0x60
                    Wire.beginTransmission(0x70);
                    if (Wire.endTransmission() == 0)
                    {
                        Serial.println("      Trying to initialize VCNL4040 at 0x70...");
                        // Note: This is experimental - VCNL4040 should be at 0x60
                    }
                }
            }
            continue;
        }

        // Try to initialize VCNL4040
        if (!vcnl_sensors[pca_channel].begin())
        {
            sensors[pca_channel].status = "Init Failed";
            Serial.println("  VCNL4040 init failed on PCA channel " + String(pca_channel));
            continue;
        }

        Serial.println("  ✅ VCNL4040 initialized on PCA channel " + String(pca_channel));

        Serial.println("    🔧 Using Adafruit library configuration");

        // Configure VCNL4040 using Adafruit library functions
        Serial.println("    📋 Configuring VCNL4040 with library functions...");

        // Enable proximity sensor
        vcnl_sensors[pca_channel].enableProximity(true);
        Serial.println("      ✅ Proximity sensor enabled");

        // Set LED current to 50mA to reduce power consumption
        vcnl_sensors[pca_channel].setProximityLEDCurrent(VCNL4040_LED_CURRENT_50MA);
        Serial.println("      ✅ LED current set to 50mA");

        // Set integration time to 8T for best sensitivity
        vcnl_sensors[pca_channel].setProximityIntegrationTime(VCNL4040_PROXIMITY_INTEGRATION_TIME_8T);
        Serial.println("      ✅ Integration time set to 8T");

        // CRITICAL: Enable high resolution mode for 16-bit proximity values (0-65535)
        vcnl_sensors[pca_channel].setProximityHighResolution(true);
        Serial.println("      ✅ High resolution mode enabled (16-bit)");

        // Set duty cycle for good balance of power and performance
        vcnl_sensors[pca_channel].setProximityLEDDutyCycle(VCNL4040_LED_DUTY_1_160);
        Serial.println("      ✅ LED duty cycle set to 1/160");

        delay(100); // Allow settings to take effect
        Serial.println("    ✅ VCNL4040 configured: 8T, 200mA LED, 16-bit mode, 1/160 duty");

        // Success!
        sensors[pca_channel].initialized = true;
        sensors[pca_channel].active = true;
        sensors[pca_channel].status = "Active";
        sensors[pca_channel].error_count = 0;

        // Test multiple readings to see if we get varied proximity values
        Serial.println("    🧪 COMPREHENSIVE PROXIMITY TEST - Place hand at different distances!");
        Serial.println("    Expected: Values should be 100+ when hand is close (1-5cm)");

        for (int test = 0; test < 10; test++) // More tests for better debugging
        {
            delay(200); // Longer delay to give you time to move hand
            uint16_t prox = vcnl_sensors[pca_channel].getProximity();
            uint16_t amb = vcnl_sensors[pca_channel].getAmbientLight();

            // More detailed output with analysis
            String detection_status = "CLEAR";
            if (prox > 100)
                detection_status = "🔴 STRONG DETECTION";
            else if (prox > 20)
                detection_status = "🟡 WEAK DETECTION";
            else if (prox > 5)
                detection_status = "🟢 POSSIBLE DETECTION";

            Serial.println("      Test " + String(test + 1) + " - Prox: " + String(prox) +
                           ", Amb: " + String(amb) + " - " + detection_status);
        }

        Serial.println("    📊 Analysis:");
        Serial.println("      - If all proximity values are 0-5: LED current or power issue");
        Serial.println("      - If values vary but stay low: Integration time or resolution issue");
        Serial.println("      - If values jump to 100+ with hand close: SENSOR WORKING!");

        // Wait a few seconds before allowing detections (prevents false startup detections)
        sensors[pca_channel].last_reading_time = millis() + 3000; // 3 second delay
        Serial.println("    Detection disabled for 3 seconds to prevent false startup detections");
    }

    // Clean up
    pca.disableAllChannels();
    tca.disableAllChannels();

    // Count active sensors
    int active_count = 0;
    for (int i = 0; i < 4; i++)
    {
        if (sensors[i].active)
            active_count++;
    }

    Serial.println("Sensor initialization complete. Active sensors: " + String(active_count));
}

void readSensors()
{
    uint32_t current_time = millis();

    // Check if it's time to read sensors
    static uint32_t last_sensor_read = 0;
    if (current_time - last_sensor_read < SENSOR_UPDATE_INTERVAL)
    {
        return;
    }
    last_sensor_read = current_time;

    // Select TCA channel 0 (sensor board)
    if (!tca.selectChannel(0))
    {
        return;
    }

    // Read all active sensors
    for (int pca_channel = 0; pca_channel < 4; pca_channel++)
    {
        if (!sensors[pca_channel].active)
        {
            continue;
        }

        // Select PCA channel
        if (!pca.selectChannel(pca_channel))
        {
            sensors[pca_channel].error_count++;
            if (sensors[pca_channel].error_count > 10)
            {
                sensors[pca_channel].status = "PCA Error";
                sensors[pca_channel].active = false;
            }
            continue;
        }

        delay(5); // Small delay for I2C settling

        // Read sensor values
        try
        {
            uint16_t new_proximity = vcnl_sensors[pca_channel].getProximity();
            uint16_t new_ambient = vcnl_sensors[pca_channel].getAmbientLight();

            // Update readings
            sensors[pca_channel].proximity = new_proximity;
            sensors[pca_channel].ambient = new_ambient;
            sensors[pca_channel].last_reading_time = current_time;
            sensors[pca_channel].status = "Active";
            sensors[pca_channel].error_count = 0; // Reset error count on successful read

            // Track maximum proximity seen for calibration
            if (new_proximity > sensors[pca_channel].max_proximity)
            {
                sensors[pca_channel].max_proximity = new_proximity;
            }

            // Check for object detection (but only after startup delay)
            bool was_detected = sensors[pca_channel].object_detected;
            bool is_detected = (new_proximity > PROXIMITY_THRESHOLD);

            // Only update detection status if we're past the startup delay
            if (current_time > sensors[pca_channel].last_reading_time)
            {
                sensors[pca_channel].object_detected = is_detected;

                // If we just detected an object (transition from not detected to detected)
                if (is_detected && !was_detected)
                {
                    sensors[pca_channel].last_detection_time = current_time;
                    addDetectionEvent(pca_channel, new_proximity);
                }
            }
            else
            {
                // Still in startup delay period
                sensors[pca_channel].object_detected = false;
                uint32_t remaining_delay = (sensors[pca_channel].last_reading_time - current_time) / 1000;
                if (remaining_delay != sensors[pca_channel].error_count) // Use error_count as temp storage to avoid spam
                {
                    sensors[pca_channel].error_count = remaining_delay;
                    Serial.println("    Ch" + String(pca_channel) + " startup delay: " + String(remaining_delay) + "s remaining");
                }
            }
        }
        catch (...)
        {
            sensors[pca_channel].error_count++;
            if (sensors[pca_channel].error_count > 10)
            {
                sensors[pca_channel].status = "Read Error";
                sensors[pca_channel].active = false;
            }
        }
    }

    // Clean up
    pca.disableAllChannels();
    tca.disableAllChannels();
}

// ==================================================================================
// DISPLAY FUNCTIONS
// ==================================================================================

void drawHeader()
{
    // Clear header area
    tft.fillRect(0, 0, SCREEN_WIDTH, 25, COLOR_DARK_GRAY);

    // Title
    tft.setTextColor(COLOR_WHITE, COLOR_DARK_GRAY);
    tft.setTextSize(1);
    tft.setCursor(5, 5);
    tft.println("Motion Play v2.1 - Sensor Monitor");

    // Uptime
    uint32_t uptime_seconds = (millis() - system_start_time) / 1000;
    String uptime = "Up: " + String(uptime_seconds) + "s";
    tft.setTextColor(COLOR_CYAN, COLOR_DARK_GRAY);
    tft.setCursor(SCREEN_WIDTH - (uptime.length() * 6) - 5, 5);
    tft.println(uptime);

    // Active sensor count
    int active_count = 0;
    for (int i = 0; i < 4; i++)
    {
        if (sensors[i].active)
            active_count++;
    }
    tft.setTextColor(COLOR_YELLOW, COLOR_DARK_GRAY);
    tft.setCursor(5, 15);
    tft.println("Active Sensors: " + String(active_count));
}

void drawDetectionHistory()
{
    int history_y = 160;
    tft.fillRect(0, history_y, SCREEN_WIDTH, 10, COLOR_BLACK);

    if (detection_history_count > 0)
    {
        tft.setTextColor(COLOR_MAGENTA, COLOR_BLACK);
        tft.setTextSize(1);
        tft.setCursor(5, history_y);

        uint32_t last_detection_age = (millis() - detection_history[0].timestamp) / 1000;
        tft.println("Last Detection: Ch" + String(detection_history[0].channel) +
                    " (" + String(detection_history[0].proximity_value) + ") " +
                    String(last_detection_age) + "s ago");
    }
    else
    {
        tft.setTextColor(COLOR_GRAY, COLOR_BLACK);
        tft.setTextSize(1);
        tft.setCursor(5, history_y);
        tft.println("No detections yet - try placing object near sensor");
    }
}

void drawSensorDisplay()
{
    int start_y = 30;
    int sensor_height = 32;

    for (int i = 0; i < 4; i++)
    {
        int y_pos = start_y + (i * sensor_height);

        // Clear sensor area
        tft.fillRect(0, y_pos, SCREEN_WIDTH, sensor_height - 2, COLOR_BLACK);

        // Sensor header
        tft.setTextColor(COLOR_WHITE, COLOR_BLACK);
        tft.setTextSize(1);
        tft.setCursor(5, y_pos + 2);
        tft.println("Ch" + String(i) + ":");

        // Status indicator
        uint16_t status_color = COLOR_RED;
        if (sensors[i].active)
        {
            status_color = sensors[i].object_detected ? COLOR_ORANGE : COLOR_GREEN;
        }
        else if (sensors[i].initialized)
        {
            status_color = COLOR_YELLOW;
        }

        tft.fillCircle(35, y_pos + 8, 5, status_color);

        // Status text
        tft.setTextColor(COLOR_CYAN, COLOR_BLACK);
        tft.setCursor(45, y_pos + 2);
        tft.println(sensors[i].status);

        if (sensors[i].active)
        {
            // Proximity reading with better formatting
            tft.setTextColor(sensors[i].object_detected ? COLOR_RED : COLOR_WHITE, COLOR_BLACK);
            tft.setCursor(5, y_pos + 12);
            tft.println("P:" + String(sensors[i].proximity) + " A:" + String(sensors[i].ambient));

            // Max proximity seen (for calibration)
            tft.setTextColor(COLOR_GRAY, COLOR_BLACK);
            tft.setCursor(5, y_pos + 22);
            tft.println("Max:" + String(sensors[i].max_proximity));

            // Detection status and last detection
            if (sensors[i].object_detected)
            {
                tft.setTextColor(COLOR_RED, COLOR_BLACK);
                tft.setCursor(120, y_pos + 12);
                tft.println("🔴 DETECTED!");
            }
            else
            {
                tft.setTextColor(COLOR_GREEN, COLOR_BLACK);
                tft.setCursor(120, y_pos + 12);
                tft.println("✓ Clear");
            }

            // Last detection time or startup delay
            if (millis() < sensors[i].last_reading_time)
            {
                // Still in startup delay
                uint32_t remaining = (sensors[i].last_reading_time - millis()) / 1000;
                tft.setTextColor(COLOR_GRAY, COLOR_BLACK);
                tft.setCursor(120, y_pos + 22);
                tft.println("Delay:" + String(remaining) + "s");
            }
            else if (sensors[i].last_detection_time > 0)
            {
                uint32_t since_detection = (millis() - sensors[i].last_detection_time) / 1000;
                tft.setTextColor(COLOR_YELLOW, COLOR_BLACK);
                tft.setCursor(120, y_pos + 22);
                tft.println("Last:" + String(since_detection) + "s ago");
            }
        }
        else
        {
            // Show why sensor is not active
            tft.setTextColor(COLOR_GRAY, COLOR_BLACK);
            tft.setCursor(5, y_pos + 12);
            if (sensors[i].error_count > 0)
            {
                tft.println("Errors: " + String(sensors[i].error_count));
            }
            else
            {
                tft.println("Not detected");
            }
        }

        // Separator line
        tft.drawLine(0, y_pos + sensor_height - 2, SCREEN_WIDTH, y_pos + sensor_height - 2, COLOR_DARK_GRAY);
    }

    // Detection history at bottom
    drawDetectionHistory();
}

void updateDisplay()
{
    uint32_t current_time = millis();

    if (current_time - last_display_update < DISPLAY_UPDATE_INTERVAL)
    {
        return;
    }
    last_display_update = current_time;

    drawHeader();
    drawSensorDisplay();
}

// ==================================================================================
// BUTTON HANDLING
// ==================================================================================

void initializeButtons()
{
    pinMode(PIN_BUTTON_1, INPUT_PULLUP);
    pinMode(PIN_BUTTON_2, INPUT_PULLUP);
}

void handleButtons()
{
    static uint32_t last_button_check = 0;
    static bool button1_last_state = true;
    static bool button2_last_state = true;

    uint32_t current_time = millis();
    if (current_time - last_button_check < 50)
        return; // Debounce
    last_button_check = current_time;

    bool button1_current = digitalRead(PIN_BUTTON_1);
    bool button2_current = digitalRead(PIN_BUTTON_2);

    // Button 1 pressed (reinitialize sensors)
    if (!button1_current && button1_last_state)
    {
        Serial.println("Button 1 pressed - Reinitializing sensors...");
        tft.fillScreen(COLOR_BLACK);
        tft.setTextColor(COLOR_YELLOW, COLOR_BLACK);
        tft.setTextSize(1);
        tft.setCursor(10, 50);
        tft.println("Reinitializing sensors...");
        initializeSensors();
    }

    // Button 2 pressed (toggle proximity sensors)
    if (!button2_current && button2_last_state)
    {
        Serial.println("Button 2 pressed - Toggling proximity sensors...");
        static bool proximity_enabled = true;
        proximity_enabled = !proximity_enabled;

        // Select TCA channel 0 (sensor board)
        if (tca.selectChannel(0))
        {
            for (int i = 0; i < 4; i++)
            {
                if (sensors[i].initialized)
                {
                    // Select PCA channel
                    if (pca.selectChannel(i))
                    {
                        vcnl_sensors[i].enableProximity(proximity_enabled);
                        delay(10);
                    }
                }
            }
            pca.disableAllChannels();
        }
        tca.disableAllChannels();

        Serial.println("Proximity sensors " + String(proximity_enabled ? "ENABLED" : "DISABLED"));
    }

    button1_last_state = button1_current;
    button2_last_state = button2_current;
}

// ==================================================================================
// MAIN FUNCTIONS
// ==================================================================================

void setup()
{
    Serial.begin(115200);
    delay(1000);

    system_start_time = millis();

    Serial.println("\n" + String("=").substring(0, 50));
    Serial.println("MOTION PLAY v2.1 - SENSOR DISPLAY MODE");
    Serial.println("Build: " + String(__DATE__) + " " + String(__TIME__));
    Serial.println("Chip: " + String(ESP.getChipModel()));
    Serial.println("Free heap: " + String(ESP.getFreeHeap()) + " bytes");
    Serial.println(String("=").substring(0, 50));

    // Initialize hardware
    if (!initializeDisplay())
    {
        Serial.println("FATAL: Display initialization failed!");
        while (1)
            delay(1000);
    }

    initializeButtons();

    if (!initializeI2C())
    {
        Serial.println("FATAL: I2C initialization failed!");
        while (1)
            delay(1000);
    }

    if (!initializeTCA())
    {
        Serial.println("FATAL: TCA9548A initialization failed!");
        while (1)
            delay(1000);
    }

    if (!initializePCA())
    {
        Serial.println("FATAL: PCA9546A initialization failed!");
        while (1)
            delay(1000);
    }

    // Don't initialize sensors on boot - wait for button press
    // This fixes the timing issue where sensors aren't ready immediately

    // Clear screen for main display
    tft.fillScreen(COLOR_BLACK);

    // Show instructions
    tft.setTextColor(COLOR_YELLOW, COLOR_BLACK);
    tft.setTextSize(1);
    tft.setCursor(10, 60);
    tft.println("Press Button 1 to initialize sensors");
    tft.setCursor(10, 80);
    tft.println("(Fixes timing issues on first boot)");

    Serial.println("Setup complete. System ready.");
    Serial.println("Button 1: Initialize sensors (recommended on first boot)");
    Serial.println("Button 2: Reset error counts");
    Serial.println("Threshold: " + String(PROXIMITY_THRESHOLD) + " (lowered for better sensitivity)");
}

void loop()
{
    handleButtons();
    readSensors();
    updateDisplay();

    delay(10); // Small delay to prevent excessive CPU usage
}

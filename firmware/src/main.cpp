/**
 * Motion Play v2.0 - Phase 1: Foundation & Display Test
 *
 * This is the initial phase of the complete system rebuild using vetted libraries.
 *
 * Phase 1 Objectives:
 * - Verify T-Display-S3 initialization and functionality
 * - Display system information and build details
 * - Implement basic terminal/logging system
 * - Test button navigation
 * - Prepare placeholders for upcoming phases
 *
 * Hardware: T-Display-S3 (ESP32-S3) with built-in display and buttons
 * Libraries:
 * - TFT_eSPI for display control
 * - robtillaart/TCA9548 for I2C multiplexer (Phase 2+)
 * - Adafruit VCNL4040 for proximity sensors (Phase 4+)
 */

#include <Arduino.h>
#include <TFT_eSPI.h>
#include <Wire.h>
#include <TCA9548.h>           // robtillaart TCA9548 library
#include <Adafruit_VCNL4040.h> // Adafruit VCNL4040 library
#include "pin_config.h"

// TCA9548A I2C Multiplexer
#define TCA9548A_ADDRESS 0x70
TCA9548 tca(TCA9548A_ADDRESS);

// PCA9546A I2C Multiplexer (on sensor boards)
#define PCA9546A_ADDRESS 0x70

// Simple PCA9546A wrapper class
class PCA9546A
{
private:
    uint8_t address;

public:
    PCA9546A(uint8_t addr) : address(addr) {}

    bool begin()
    {
        // Test communication
        Wire.beginTransmission(address);
        return (Wire.endTransmission() == 0);
    }

    bool isConnected()
    {
        Wire.beginTransmission(address);
        return (Wire.endTransmission() == 0);
    }

    bool selectChannel(uint8_t channel)
    {
        if (channel > 3)
            return false;
        Wire.beginTransmission(address);
        Wire.write(1 << channel); // Set bit for channel
        return (Wire.endTransmission() == 0);
    }

    bool disableAllChannels()
    {
        Wire.beginTransmission(address);
        Wire.write(0x00); // All channels off
        return (Wire.endTransmission() == 0);
    }

    uint8_t getChannelMask()
    {
        Wire.beginTransmission(address);
        if (Wire.endTransmission() != 0)
            return 0xFF; // Error

        Wire.requestFrom(address, (uint8_t)1);
        if (Wire.available())
        {
            return Wire.read();
        }
        return 0xFF; // Error
    }
};

PCA9546A pca(PCA9546A_ADDRESS);

// VCNL4040 Proximity Sensors (test all PCA channels)
Adafruit_VCNL4040 vcnl_sensors[4]; // One for each possible PCA channel

// Sensor readings structure
struct SensorReadings
{
    uint16_t proximity[4] = {0, 0, 0, 0}; // One for each PCA channel
    uint16_t ambient[4] = {0, 0, 0, 0};   // One for each PCA channel
    bool object_detected[4] = {false, false, false, false};
    bool sensor_active[4] = {false, false, false, false}; // Which sensors are working
    uint32_t last_reading_time = 0;
    int active_sensor_count = 0;
} sensor_readings;

// Detection thresholds
#define PROXIMITY_THRESHOLD 1000   // Default threshold - adjust based on testing
#define SENSOR_UPDATE_INTERVAL 100 // ms between sensor readings

// ==================================================================================
// CONSTANTS & CONFIGURATION
// ==================================================================================

#define VERSION_MAJOR 2
#define VERSION_MINOR 0
#define VERSION_PATCH 0
#define PHASE_NUMBER 4

// Display configuration (Landscape mode: 320x170)
#define SCREEN_WIDTH 320
#define SCREEN_HEIGHT 170
#define LINE_HEIGHT 12
#define MAX_LOG_LINES 10
#define HEADER_HEIGHT 25

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

// Button debounce
#define BUTTON_DEBOUNCE_MS 50

// ==================================================================================
// GLOBAL VARIABLES
// ==================================================================================

TFT_eSPI tft = TFT_eSPI();

// System state
struct SystemStatus
{
    bool display_initialized = false;
    bool i2c_initialized = false;
    bool tca_detected = false;
    bool pca_detected = false;
    bool sensors_detected = false;
    uint32_t boot_time = 0;
    uint32_t last_update = 0;
} system_status;

// Button state
struct ButtonState
{
    bool button1_pressed = false;
    bool button2_pressed = false;
    uint32_t button1_last_press = 0;
    uint32_t button2_last_press = 0;
} button_state;

// Terminal/logging system
String log_buffer[MAX_LOG_LINES];
int log_line_count = 0;
int log_scroll_offset = 0;
bool auto_scroll = true;

// ==================================================================================
// FUNCTION DECLARATIONS
// ==================================================================================

void runPhase4Tests();
void initializeI2C();
void scanI2CBus();
void testTCA9548A();
void testPCA9546A();
void testVCNL4040Sensors();
void readSensors();
void updateSensorDisplay();

// ==================================================================================
// UTILITY FUNCTIONS
// ==================================================================================

/**
 * Get formatted build timestamp
 */
String getBuildTimestamp()
{
    return String(__DATE__) + " " + String(__TIME__);
}

/**
 * Get version string
 */
String getVersionString()
{
    return "v" + String(VERSION_MAJOR) + "." + String(VERSION_MINOR) + "." + String(VERSION_PATCH);
}

/**
 * Get uptime in human readable format
 */
String getUptimeString()
{
    uint32_t uptime_ms = millis() - system_status.boot_time;
    uint32_t seconds = uptime_ms / 1000;
    uint32_t minutes = seconds / 60;
    uint32_t hours = minutes / 60;

    seconds %= 60;
    minutes %= 60;

    return String(hours) + "h " + String(minutes) + "m " + String(seconds) + "s";
}

/**
 * Add message to terminal log
 */
void logMessage(String message, uint16_t color = COLOR_WHITE)
{
    // Add timestamp prefix
    uint32_t timestamp = millis() - system_status.boot_time;
    String timestamped_msg = "[" + String(timestamp / 1000) + "s] " + message;

    // Add to buffer
    if (log_line_count < MAX_LOG_LINES)
    {
        log_buffer[log_line_count] = timestamped_msg;
        log_line_count++;
    }
    else
    {
        // Shift buffer up
        for (int i = 0; i < MAX_LOG_LINES - 1; i++)
        {
            log_buffer[i] = log_buffer[i + 1];
        }
        log_buffer[MAX_LOG_LINES - 1] = timestamped_msg;
    }

    // ALWAYS print to serial first (for debugging)
    Serial.println(timestamped_msg);
    Serial.flush(); // Ensure immediate output

    // Auto-scroll to bottom if enabled
    if (auto_scroll)
    {
        log_scroll_offset = max(0, log_line_count - MAX_LOG_LINES);
    }
}

// ==================================================================================
// DISPLAY FUNCTIONS
// ==================================================================================

/**
 * Initialize display
 */
bool initializeDisplay()
{
    logMessage("Initializing T-Display-S3...", COLOR_CYAN);

    // Power on display
    pinMode(PIN_POWER_ON, OUTPUT);
    digitalWrite(PIN_POWER_ON, HIGH);
    delay(100);

    // Initialize TFT
    tft.init();
    tft.setRotation(1); // Landscape mode (320x170)
    tft.fillScreen(COLOR_BLACK);

    // Test display with welcome message
    tft.setTextColor(COLOR_GREEN, COLOR_BLACK);
    tft.setTextSize(1);
    tft.setCursor(10, 10);
    tft.println("Motion Play " + getVersionString());
    tft.setCursor(10, 25);
    tft.setTextColor(COLOR_YELLOW, COLOR_BLACK);
    tft.println("Phase " + String(PHASE_NUMBER) + ": Display Test");

    delay(1000); // Show welcome message briefly

    system_status.display_initialized = true;
    logMessage("Display initialized successfully", COLOR_GREEN);
    return true;
}

/**
 * Draw system header
 */
void drawHeader()
{
    // Clear header area
    tft.fillRect(0, 0, SCREEN_WIDTH, HEADER_HEIGHT, COLOR_DARK_GRAY);

    // Left side - Title and Phase
    tft.setTextColor(COLOR_WHITE, COLOR_DARK_GRAY);
    tft.setTextSize(1);
    tft.setCursor(5, 5);
    tft.println("Motion Play " + getVersionString());
    tft.setCursor(5, 15);
    tft.setTextColor(COLOR_YELLOW, COLOR_DARK_GRAY);
    tft.println("Phase " + String(PHASE_NUMBER) + " - Sensors");

    // Right side - Uptime
    tft.setTextColor(COLOR_CYAN, COLOR_DARK_GRAY);
    String uptime = "Up: " + getUptimeString();
    tft.setCursor(SCREEN_WIDTH - (uptime.length() * 6) - 5, 10);
    tft.println(uptime);
}

/**
 * Draw system status indicators
 */
void drawStatusIndicators()
{
    int y_pos = HEADER_HEIGHT + 5;
    int indicator_height = 12;

    // Status indicators
    struct StatusIndicator
    {
        String label;
        bool status;
        String description;
    };

    StatusIndicator indicators[] = {
        {"DISP", system_status.display_initialized, "Display"},
        {"I2C ", system_status.i2c_initialized, "I2C Bus"},
        {"TCA ", system_status.tca_detected, "TCA9548A Mux"},
        {"PCA ", system_status.pca_detected, "PCA9546A Mux"},
        {"SENS", system_status.sensors_detected, "VCNL4040 Sensors"}};

    for (int i = 0; i < 5; i++)
    {
        uint16_t bg_color = indicators[i].status ? COLOR_GREEN : COLOR_RED;
        uint16_t text_color = COLOR_WHITE;

        // Draw indicator box - spread across width
        int indicator_width = 50;
        int x_pos = 5 + (i * (indicator_width + 5));
        tft.fillRect(x_pos, y_pos, indicator_width, indicator_height, bg_color);
        tft.drawRect(x_pos, y_pos, indicator_width, indicator_height, COLOR_WHITE);

        // Draw label
        tft.setTextColor(text_color, bg_color);
        tft.setTextSize(1);
        tft.setCursor(x_pos + 2, y_pos + 2);
        tft.println(indicators[i].label);
    }
}

/**
 * Draw terminal log
 */
void drawTerminalLog()
{
    int terminal_start_y = HEADER_HEIGHT + 20;
    int terminal_height = SCREEN_HEIGHT - terminal_start_y - 5;

    // Clear terminal area
    tft.fillRect(0, terminal_start_y, SCREEN_WIDTH, terminal_height, COLOR_BLACK);

    // Draw terminal border
    tft.drawRect(2, terminal_start_y, SCREEN_WIDTH - 4, terminal_height, COLOR_GRAY);

    // Draw log messages
    tft.setTextColor(COLOR_WHITE, COLOR_BLACK);
    tft.setTextSize(1);

    int visible_lines = min(MAX_LOG_LINES, (terminal_height - 4) / LINE_HEIGHT);
    int start_line = max(0, log_line_count - visible_lines + log_scroll_offset);

    for (int i = 0; i < visible_lines && (start_line + i) < log_line_count; i++)
    {
        int y_pos = terminal_start_y + 4 + (i * LINE_HEIGHT);
        tft.setCursor(6, y_pos);

        String line = log_buffer[start_line + i];
        // Truncate line if too long (landscape mode = more characters)
        if (line.length() > 50)
        {
            line = line.substring(0, 47) + "...";
        }
        tft.println(line);
    }

    // Draw scroll indicator if needed
    if (log_line_count > visible_lines)
    {
        int scroll_bar_height = max(10, (visible_lines * terminal_height) / log_line_count);
        int scroll_bar_pos = (log_scroll_offset * (terminal_height - scroll_bar_height)) / max(1, log_line_count - visible_lines);

        tft.fillRect(SCREEN_WIDTH - 8, terminal_start_y + scroll_bar_pos, 4, scroll_bar_height, COLOR_CYAN);
    }
}

/**
 * Update display
 */
void updateDisplay()
{
    drawHeader();
    drawStatusIndicators();
    drawTerminalLog();
}

// ==================================================================================
// BUTTON HANDLING
// ==================================================================================

/**
 * Initialize buttons
 */
void initializeButtons()
{
    pinMode(PIN_BUTTON_1, INPUT_PULLUP);
    pinMode(PIN_BUTTON_2, INPUT_PULLUP);
    logMessage("Buttons initialized", COLOR_GREEN);
}

/**
 * Handle button presses
 */
void handleButtons()
{
    uint32_t current_time = millis();

    // Button 1 (scroll up / toggle auto-scroll)
    bool button1_current = !digitalRead(PIN_BUTTON_1);
    if (button1_current && !button_state.button1_pressed &&
        (current_time - button_state.button1_last_press) > BUTTON_DEBOUNCE_MS)
    {

        button_state.button1_pressed = true;
        button_state.button1_last_press = current_time;

        // Toggle auto-scroll or scroll up
        if (auto_scroll)
        {
            auto_scroll = false;
            logMessage("Auto-scroll OFF", COLOR_YELLOW);
        }
        else
        {
            log_scroll_offset = max(log_scroll_offset - 1, -(log_line_count - MAX_LOG_LINES));
            logMessage("Scroll up", COLOR_GRAY);
        }
    }
    else if (!button1_current)
    {
        button_state.button1_pressed = false;
    }

    // Button 2 (scroll down / enable auto-scroll)
    bool button2_current = !digitalRead(PIN_BUTTON_2);
    if (button2_current && !button_state.button2_pressed &&
        (current_time - button_state.button2_last_press) > BUTTON_DEBOUNCE_MS)
    {

        button_state.button2_pressed = true;
        button_state.button2_last_press = current_time;

        // Enable auto-scroll or scroll down
        if (!auto_scroll)
        {
            log_scroll_offset = min(log_scroll_offset + 1, 0);
            if (log_scroll_offset == 0)
            {
                auto_scroll = true;
                logMessage("Auto-scroll ON", COLOR_YELLOW);
            }
            else
            {
                logMessage("Scroll down", COLOR_GRAY);
            }
        }
        else
        {
            // Run test sequence
            Serial.println("\n>>> USER PRESSED BUTTON 2 - STARTING PHASE 4 TESTS <<<");
            Serial.flush();
            logMessage("Running Phase 4 tests...", COLOR_MAGENTA);
            runPhase4Tests();
        }
    }
    else if (!button2_current)
    {
        button_state.button2_pressed = false;
    }
}

// ==================================================================================
// TEST FUNCTIONS
// ==================================================================================

/**
 * Run Phase 4 specific tests
 */
void runPhase4Tests()
{
    logMessage("=== PHASE 4 TEST SEQUENCE ===", COLOR_MAGENTA);

    // I2C Bus Scan
    scanI2CBus();
    delay(1000);

    // TCA9548A Testing (prerequisite)
    testTCA9548A();
    delay(1000);

    // PCA9546A Testing (prerequisite)
    if (system_status.tca_detected)
    {
        testPCA9546A();
        delay(1000);
    }
    else
    {
        logMessage("Skipping PCA test - TCA failed", COLOR_YELLOW);
        system_status.pca_detected = false;
    }

    // VCNL4040 Sensor Testing (main focus)
    if (system_status.tca_detected && system_status.pca_detected)
    {
        testVCNL4040Sensors();
        delay(1000);
    }
    else
    {
        logMessage("Skipping sensor test - prerequisites failed", COLOR_YELLOW);
        system_status.sensors_detected = false;
    }

    // System status
    logMessage("--- SYSTEM STATUS ---", COLOR_CYAN);
    logMessage("Display: " + String(system_status.display_initialized ? "OK" : "FAIL"),
               system_status.display_initialized ? COLOR_GREEN : COLOR_RED);
    logMessage("I2C Bus: " + String(system_status.i2c_initialized ? "OK" : "FAIL"),
               system_status.i2c_initialized ? COLOR_GREEN : COLOR_RED);
    logMessage("TCA9548A: " + String(system_status.tca_detected ? "OK" : "FAIL"),
               system_status.tca_detected ? COLOR_GREEN : COLOR_RED);
    logMessage("PCA9546A: " + String(system_status.pca_detected ? "OK" : "FAIL"),
               system_status.pca_detected ? COLOR_GREEN : COLOR_RED);
    logMessage("VCNL4040: " + String(system_status.sensors_detected ? "OK" : "FAIL"),
               system_status.sensors_detected ? COLOR_GREEN : COLOR_RED);

    // Communication path status
    if (system_status.tca_detected && system_status.pca_detected && system_status.sensors_detected)
    {
        logMessage("Full sensor chain ready!", COLOR_GREEN);
        logMessage("Live sensor readings enabled", COLOR_GREEN);
    }
    else
    {
        logMessage("Sensor chain incomplete", COLOR_YELLOW);
    }

    // Memory status
    logMessage("Free heap: " + String(ESP.getFreeHeap()) + " bytes", COLOR_CYAN);

    // Next phase
    logMessage("--- NEXT PHASE ---", COLOR_GRAY);
    logMessage("Phase 5: Integration & LED", COLOR_GRAY);

    if (system_status.tca_detected && system_status.pca_detected && system_status.sensors_detected)
    {
        logMessage("=== PHASE 4 COMPLETE ===", COLOR_GREEN);
    }
    else
    {
        logMessage("=== PHASE 4 INCOMPLETE ===", COLOR_YELLOW);
        if (!system_status.tca_detected)
            logMessage("Check TCA9548A connection", COLOR_YELLOW);
        if (!system_status.pca_detected)
            logMessage("Check sensor board connection", COLOR_YELLOW);
        if (!system_status.sensors_detected)
            logMessage("Check VCNL4040 sensor", COLOR_YELLOW);
    }
}

// ==================================================================================
// MAIN FUNCTIONS
// ==================================================================================

/**
 * Initialize I2C bus
 */
void initializeI2C()
{
    // Initialize I2C with custom pins (GPIO 43=SDA, 44=SCL)
    Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);
    Wire.setClock(400000); // 400kHz fast mode

    // Initialize TCA reset pin
    pinMode(PIN_TCA_RESET, OUTPUT);
    digitalWrite(PIN_TCA_RESET, HIGH); // TCA9548A active (reset is active low)

    logMessage("I2C initialized", COLOR_GREEN);
    logMessage("SDA: GPIO" + String(PIN_IIC_SDA) + ", SCL: GPIO" + String(PIN_IIC_SCL), COLOR_CYAN);
    logMessage("Clock: 400kHz", COLOR_CYAN);
    system_status.i2c_initialized = true;
}

/**
 * Scan I2C bus for devices
 */
void scanI2CBus()
{
    logMessage("=== I2C BUS SCAN ===", COLOR_CYAN);
    int device_count = 0;

    for (byte address = 1; address < 127; address++)
    {
        Wire.beginTransmission(address);
        byte error = Wire.endTransmission();

        if (error == 0)
        {
            device_count++;
            String addr_str = "0x" + String(address, HEX);
            if (address < 16)
                addr_str = "0x0" + String(address, HEX);

            String device_name = "Unknown";
            if (address == 0x70)
                device_name = "TCA9548A Mux";
            else if (address == 0x60)
                device_name = "VCNL4040 Sensor";

            logMessage("Found: " + addr_str + " (" + device_name + ")", COLOR_GREEN);
        }
        else if (error == 4)
        {
            String addr_str = "0x" + String(address, HEX);
            if (address < 16)
                addr_str = "0x0" + String(address, HEX);
            logMessage("Error at: " + addr_str, COLOR_RED);
        }
    }

    if (device_count == 0)
    {
        logMessage("No I2C devices found!", COLOR_RED);
    }
    else
    {
        logMessage("Scan complete: " + String(device_count) + " devices", COLOR_CYAN);
    }
}

/**
 * Test TCA9548A communication and channel switching
 */
void testTCA9548A()
{
    logMessage("=== TCA9548A TEST ===", COLOR_CYAN);

    // Initialize TCA9548A
    if (!tca.begin())
    {
        logMessage("TCA9548A init FAILED!", COLOR_RED);
        system_status.tca_detected = false;
        return;
    }

    logMessage("TCA9548A initialized", COLOR_GREEN);

    // Test basic communication
    if (!tca.isConnected())
    {
        logMessage("TCA9548A not responding!", COLOR_RED);
        system_status.tca_detected = false;
        return;
    }

    logMessage("TCA9548A responding", COLOR_GREEN);

    // Disable all channels first
    tca.disableAllChannels();
    logMessage("All channels disabled", COLOR_YELLOW);

    // Test channel 0 (sensor board 1)
    logMessage("Testing channel 0...", COLOR_CYAN);

    if (tca.selectChannel(0))
    {
        logMessage("Channel 0 selected", COLOR_GREEN);

        // Verify channel selection by reading back
        uint8_t channels = tca.getChannelMask();
        if (channels & 0x01) // Check if bit 0 is set (channel 0)
        {
            logMessage("Channel 0 confirmed active", COLOR_GREEN);
        }
        else
        {
            logMessage("Channel 0 selection failed", COLOR_RED);
        }

        // Disable channel 0
        tca.disableChannel(0);
        logMessage("Channel 0 disabled", COLOR_YELLOW);
    }
    else
    {
        logMessage("Channel 0 select FAILED!", COLOR_RED);
        system_status.tca_detected = false;
        return;
    }

    // Mark TCA as working
    system_status.tca_detected = true;
    logMessage("TCA9548A test PASSED", COLOR_GREEN);
}

/**
 * Test PCA9546A communication through TCA9548A
 */
void testPCA9546A()
{
    logMessage("=== PCA9546A TEST ===", COLOR_CYAN);

    // First, select TCA channel 0 (sensor board 1)
    if (!tca.selectChannel(0))
    {
        logMessage("TCA channel 0 select FAILED!", COLOR_RED);
        system_status.pca_detected = false;
        return;
    }
    logMessage("TCA channel 0 selected", COLOR_GREEN);

    // Small delay for I2C settling
    delay(10);

    // Try to communicate with PCA9546A
    if (!pca.begin())
    {
        logMessage("PCA9546A init FAILED!", COLOR_RED);
        logMessage("Check sensor board connection", COLOR_YELLOW);
        system_status.pca_detected = false;
        tca.disableAllChannels();
        return;
    }

    logMessage("PCA9546A initialized", COLOR_GREEN);

    // Test basic communication
    if (!pca.isConnected())
    {
        logMessage("PCA9546A not responding!", COLOR_RED);
        system_status.pca_detected = false;
        tca.disableAllChannels();
        return;
    }

    logMessage("PCA9546A responding", COLOR_GREEN);

    // Disable all PCA channels first
    pca.disableAllChannels();
    logMessage("All PCA channels disabled", COLOR_YELLOW);

    // Test PCA channel 0 (sensor A)
    logMessage("Testing PCA channel 0...", COLOR_CYAN);
    if (pca.selectChannel(0))
    {
        logMessage("PCA channel 0 selected", COLOR_GREEN);

        // Verify channel selection
        uint8_t channels = pca.getChannelMask();
        if (channels != 0xFF && (channels & 0x01))
        {
            logMessage("PCA channel 0 confirmed", COLOR_GREEN);
        }
        else
        {
            logMessage("PCA channel 0 verify failed", COLOR_RED);
        }

        pca.disableAllChannels();
        logMessage("PCA channel 0 disabled", COLOR_YELLOW);
    }
    else
    {
        logMessage("PCA channel 0 select FAILED!", COLOR_RED);
        system_status.pca_detected = false;
        tca.disableAllChannels();
        return;
    }

    // Test PCA channel 1 (sensor B)
    logMessage("Testing PCA channel 1...", COLOR_CYAN);
    if (pca.selectChannel(1))
    {
        logMessage("PCA channel 1 selected", COLOR_GREEN);

        // Verify channel selection
        uint8_t channels = pca.getChannelMask();
        if (channels != 0xFF && (channels & 0x02))
        {
            logMessage("PCA channel 1 confirmed", COLOR_GREEN);
        }
        else
        {
            logMessage("PCA channel 1 verify failed", COLOR_RED);
        }

        pca.disableAllChannels();
        logMessage("PCA channel 1 disabled", COLOR_YELLOW);
    }
    else
    {
        logMessage("PCA channel 1 select FAILED!", COLOR_RED);
        system_status.pca_detected = false;
        tca.disableAllChannels();
        return;
    }

    // Clean up - disable all channels
    tca.disableAllChannels();
    logMessage("TCA channels disabled", COLOR_YELLOW);

    // Mark PCA as working
    system_status.pca_detected = true;
    logMessage("PCA9546A test PASSED", COLOR_GREEN);
}

/**
 * Test VCNL4040 sensors on ALL PCA channels (comprehensive scan)
 */
void testVCNL4040Sensors()
{
    logMessage("=== VCNL4040 COMPREHENSIVE TEST ===", COLOR_CYAN);

    // First, select TCA channel 0 (sensor board 1)
    if (!tca.selectChannel(0))
    {
        logMessage("TCA channel 0 select FAILED!", COLOR_RED);
        system_status.sensors_detected = false;
        return;
    }
    logMessage("TCA channel 0 selected", COLOR_GREEN);
    delay(10);

    // Reset sensor count
    sensor_readings.active_sensor_count = 0;

    // Test all 4 PCA channels for VCNL4040 sensors
    for (int pca_channel = 0; pca_channel < 4; pca_channel++)
    {
        logMessage("=== Testing PCA Channel " + String(pca_channel) + " ===", COLOR_CYAN);

        // Select PCA channel
        if (!pca.selectChannel(pca_channel))
        {
            logMessage("PCA ch" + String(pca_channel) + " select FAILED!", COLOR_RED);
            sensor_readings.sensor_active[pca_channel] = false;
            continue;
        }
        logMessage("PCA ch" + String(pca_channel) + " selected", COLOR_GREEN);
        delay(10);

        // Check if VCNL4040 is visible on I2C bus
        Wire.beginTransmission(0x60);
        byte error = Wire.endTransmission();
        if (error != 0)
        {
            logMessage("PCA ch" + String(pca_channel) + ": No device at 0x60", COLOR_YELLOW);
            logMessage("I2C error code: " + String(error), COLOR_GRAY);
            sensor_readings.sensor_active[pca_channel] = false;
            continue;
        }
        logMessage("PCA ch" + String(pca_channel) + ": Device found at 0x60!", COLOR_GREEN);

        // Try to initialize VCNL4040 sensor
        if (!vcnl_sensors[pca_channel].begin())
        {
            logMessage("PCA ch" + String(pca_channel) + ": VCNL4040 init FAILED!", COLOR_RED);
            sensor_readings.sensor_active[pca_channel] = false;
            continue;
        }
        logMessage("PCA ch" + String(pca_channel) + ": VCNL4040 initialized!", COLOR_GREEN);

        // Read test values
        uint16_t prox = vcnl_sensors[pca_channel].getProximity();
        uint16_t amb = vcnl_sensors[pca_channel].getAmbientLight();
        logMessage("PCA ch" + String(pca_channel) + " - Prox:" + String(prox) + " Amb:" + String(amb), COLOR_WHITE);

        // Test detection threshold
        bool detected = (prox > PROXIMITY_THRESHOLD);
        logMessage("PCA ch" + String(pca_channel) + " Detection: " + String(detected ? "OBJECT" : "CLEAR"),
                   detected ? COLOR_RED : COLOR_GREEN);

        // Mark this sensor as active
        sensor_readings.sensor_active[pca_channel] = true;
        sensor_readings.active_sensor_count++;

        logMessage("PCA ch" + String(pca_channel) + ": SENSOR WORKING!", COLOR_GREEN);
    }

    // Clean up - disable all channels
    pca.disableAllChannels();
    tca.disableAllChannels();
    logMessage("All channels disabled", COLOR_YELLOW);

    // Summary of findings
    logMessage("=== SENSOR DISCOVERY SUMMARY ===", COLOR_MAGENTA);
    logMessage("Active sensors found: " + String(sensor_readings.active_sensor_count), COLOR_CYAN);

    for (int i = 0; i < 4; i++)
    {
        if (sensor_readings.sensor_active[i])
        {
            logMessage("✓ PCA Channel " + String(i) + ": VCNL4040 ACTIVE", COLOR_GREEN);
        }
        else
        {
            logMessage("✗ PCA Channel " + String(i) + ": No sensor", COLOR_GRAY);
        }
    }

    // Set detection thresholds
    logMessage("Proximity threshold: " + String(PROXIMITY_THRESHOLD), COLOR_CYAN);

    // Mark sensors as working if any found
    if (sensor_readings.active_sensor_count > 0)
    {
        system_status.sensors_detected = true;
        logMessage("VCNL4040 sensor test PASSED - " + String(sensor_readings.active_sensor_count) + " sensors", COLOR_GREEN);
    }
    else
    {
        system_status.sensors_detected = false;
        logMessage("VCNL4040 sensor test FAILED - No sensors found", COLOR_RED);
    }
}

/**
 * Read all active sensors continuously for live display
 */
void readSensors()
{
    uint32_t current_time = millis();
    if (current_time - sensor_readings.last_reading_time < SENSOR_UPDATE_INTERVAL)
    {
        return; // Not time to update yet
    }

    if (!system_status.sensors_detected || sensor_readings.active_sensor_count == 0)
    {
        return; // No sensors initialized
    }

    // Select TCA channel 0
    if (!tca.selectChannel(0))
    {
        return; // TCA communication failed
    }

    // Read all active sensors
    for (int pca_channel = 0; pca_channel < 4; pca_channel++)
    {
        if (!sensor_readings.sensor_active[pca_channel])
        {
            continue; // Skip inactive sensors
        }

        // Select PCA channel
        if (!pca.selectChannel(pca_channel))
        {
            continue; // Skip if channel selection fails
        }

        delay(5); // Small delay for I2C settling

        // Read sensor values
        sensor_readings.proximity[pca_channel] = vcnl_sensors[pca_channel].getProximity();
        sensor_readings.ambient[pca_channel] = vcnl_sensors[pca_channel].getAmbientLight();
        sensor_readings.object_detected[pca_channel] = (sensor_readings.proximity[pca_channel] > PROXIMITY_THRESHOLD);
    }

    // Clean up
    pca.disableAllChannels();
    tca.disableAllChannels();

    sensor_readings.last_reading_time = current_time;
}

/**
 * Update sensor display area with live readings from all active sensors
 */
void updateSensorDisplay()
{
    if (!system_status.sensors_detected || sensor_readings.active_sensor_count == 0)
    {
        return; // No sensors to display
    }

    // Display sensor readings in bottom right area
    int sensor_x = SCREEN_WIDTH - 120;
    int sensor_y = SCREEN_HEIGHT - 50;

    // Clear sensor area
    tft.fillRect(sensor_x, sensor_y, 115, 45, COLOR_BLACK);

    // Show active sensor count
    tft.setTextSize(1);
    tft.setTextColor(COLOR_CYAN, COLOR_BLACK);
    tft.setCursor(sensor_x, sensor_y);
    tft.println("Sensors: " + String(sensor_readings.active_sensor_count));

    int line = 1;
    // Display readings for each active sensor
    for (int pca_channel = 0; pca_channel < 4 && line < 4; pca_channel++)
    {
        if (!sensor_readings.sensor_active[pca_channel])
        {
            continue; // Skip inactive sensors
        }

        // Sensor reading line
        tft.setTextColor(sensor_readings.object_detected[pca_channel] ? COLOR_RED : COLOR_GREEN, COLOR_BLACK);
        tft.setCursor(sensor_x, sensor_y + (line * 10));
        tft.println("Ch" + String(pca_channel) + ":" + String(sensor_readings.proximity[pca_channel]));
        line++;
    }

    // Detection summary
    if (line < 4)
    {
        tft.setTextColor(COLOR_YELLOW, COLOR_BLACK);
        tft.setCursor(sensor_x, sensor_y + (line * 10));
        String det_status = "Det:";
        bool any_detected = false;
        for (int i = 0; i < 4; i++)
        {
            if (sensor_readings.sensor_active[i] && sensor_readings.object_detected[i])
            {
                det_status += String(i);
                any_detected = true;
            }
        }
        if (!any_detected)
            det_status += "-";
        tft.println(det_status);
    }
}

// ==================================================================================
// MAIN FUNCTIONS
// ==================================================================================

void setup()
{
    // Initialize serial communication
    Serial.begin(115200);
    delay(1000);

    system_status.boot_time = millis();

    Serial.println("\n" + String("=").substring(0, 60));
    Serial.println("MOTION PLAY DEBUG SESSION");
    Serial.println("Motion Play " + getVersionString() + " - Phase " + String(PHASE_NUMBER));
    Serial.println("Build: " + getBuildTimestamp());
    Serial.println("Chip: " + String(ESP.getChipModel()) + " @ " + String(ESP.getCpuFreqMHz()) + "MHz");
    Serial.println("Free heap: " + String(ESP.getFreeHeap()) + " bytes");
    Serial.println("PSRAM free: " + String(ESP.getFreePsram()) + " bytes");
    Serial.println("Serial logging: ENABLED (parallel to display)");
    Serial.println(String("=").substring(0, 60));
    Serial.flush();

    // Initialize display first
    if (!initializeDisplay())
    {
        Serial.println("FATAL: Display initialization failed!");
        while (1)
            delay(1000);
    }

    // Initialize buttons
    initializeButtons();

    // Initialize placeholders for future phases
    initializeI2C();
    testTCA9548A();
    testPCA9546A();
    testVCNL4040Sensors();

    // Initial log messages
    logMessage("=== MOTION PLAY v" + getVersionString() + " ===", COLOR_GREEN);
    logMessage("Phase " + String(PHASE_NUMBER) + ": VCNL4040 Sensors", COLOR_CYAN);
    logMessage("Build: " + getBuildTimestamp(), COLOR_YELLOW);
    logMessage("Ready! Press BTN2 for tests", COLOR_WHITE);
    logMessage("BTN1: Toggle scroll mode", COLOR_GRAY);
    logMessage("BTN2: Run Phase 4 tests", COLOR_GRAY);

    // Initial display update
    updateDisplay();

    Serial.println("Setup complete. System ready.");
}

void loop()
{
    uint32_t current_time = millis();

    // Handle button presses
    handleButtons();

    // Read sensors continuously (if initialized)
    readSensors();

    // Update display periodically
    if (current_time - system_status.last_update > 1000)
    {
        updateDisplay();
        updateSensorDisplay(); // Show live sensor readings
        system_status.last_update = current_time;
    }

    // Small delay to prevent excessive CPU usage
    delay(10);
}

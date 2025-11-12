/**
 * Motion Play v4.0 - Proximity Detection System - November 6, 2025
 *
 * APPROACH: Baseline-relative proximity detection for directional motion sensing
 * - Using VCNL4040 proximity sensors (IR LED + photodiode)
 * - BASELINE-RELATIVE detection: detects ANY deviation from baseline (like ambient light!)
 * - Supporting up to 3 sensor boards with 2 sensors each (6 total sensors)
 * - S1 (PCA channel 0) vs S2 (PCA channel 1) for directional detection
 *
 * Hardware Configuration:
 * - T-Display-S3 (ESP32-S3) main controller
 * - TCA9548A I2C multiplexer (3 channels for 3 sensor boards)
 * - Each sensor board: PCA9546A + 2x VCNL4040 sensors
 * - Total: 6 sensors arranged as 3 pairs around circular hoop
 * - Sensor positions: 6 o'clock, 9 o'clock, 3 o'clock
 *
 * Detection Logic (BASELINE-RELATIVE):
 * - Establish proximity baseline for each sensor (when nothing present)
 * - Detect ANY variation > threshold from baseline (typically 8 counts)
 * - Works for FAST and SLOW motion (unlike absolute thresholds!)
 * - S1 → S2 within 150ms = Player 1 (Green LEDs)
 * - S2 → S1 within 150ms = Player 2 (Blue LEDs)
 * - Fast sampling: 66 readings/sec (15ms interval)
 *
 * LED Feedback:
 * - 🟢 Green: Player 1 scored (S1 → S2)
 * - 🔵 Blue: Player 2 scored (S2 → S1)
 * - 72 WS2812B LEDs, 3-second display duration
 */

#include <Arduino.h>
#include <TFT_eSPI.h>
#include <Wire.h>
#include <FastLED.h>           // FastLED library for WS2812B LED strip
#include <TCA9548.h>           // robtillaart TCA9548 library
#include <Adafruit_VCNL4040.h> // Adafruit VCNL4040 library
#include "pin_config.h"

// ==================================================================================
// HARDWARE CONFIGURATION
// ==================================================================================

// TCA9548A I2C Multiplexer
#define TCA9548A_ADDRESS 0x70
TCA9548 tca(TCA9548A_ADDRESS);

// PCA9546A I2C Multiplexer addresses (different for each sensor board)
// Will be auto-detected during initialization (0 = not found)
uint8_t pca_addresses[3] = {0, 0, 0}; // PCA0, PCA1, PCA2 addresses

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

// PCA instances - will be initialized when found
PCA9546A pca_instances[3] = {PCA9546A(0x74), PCA9546A(0x75), PCA9546A(0x76)};

// VCNL4040 Proximity Sensors (6 total: 3 boards × 2 sensors each)
Adafruit_VCNL4040 vcnl_sensors[6];

// ==================================================================================
// SENSOR DATA STRUCTURE
// ==================================================================================

struct SensorData
{
    bool initialized = false;
    bool active = false;

    // Sensor readings
    uint16_t proximity = 0;     // Current proximity reading (0-65535)
    uint16_t ambient = 0;       // Current ambient light reading
    uint16_t max_proximity = 0; // Maximum proximity seen (for calibration)

    // Baseline-relative detection (like ambient light!)
    uint16_t proximity_baseline = 0;   // Baseline proximity when nothing there
    uint16_t proximity_threshold = 10; // Change from baseline needed to trigger
    int16_t proximity_variation = 0;   // Current variation from baseline
    uint32_t baseline_update_time = 0; // When baseline was last updated

    // Detection state
    bool object_detected = false;
    uint32_t last_reading_time = 0;
    uint32_t last_detection_time = 0;
    uint32_t error_count = 0;

    // Sensor identification
    uint8_t tca_channel = 0;      // Which TCA channel (0-2 for 3 boards)
    uint8_t pca_channel = 0;      // Which PCA channel (0=S1, 1=S2)
    String side_name = "Unknown"; // "S1" or "S2"
    String status = "Unknown";
};

SensorData sensors[6]; // 6 sensors total: 3 boards × 2 sensors each

// Sensor mapping (P1S1/P2S2 naming):
// sensors[0] = TCA0/PCA0 (P1S1 - PCB 1, Sensor 1)
// sensors[1] = TCA0/PCA1 (P1S2 - PCB 1, Sensor 2)
// sensors[2] = TCA1/PCA0 (P2S1 - PCB 2, Sensor 1)
// sensors[3] = TCA1/PCA1 (P2S2 - PCB 2, Sensor 2)
// sensors[4] = TCA2/PCA0 (P3S1 - PCB 3, Sensor 1)
// sensors[5] = TCA2/PCA1 (P3S2 - PCB 3, Sensor 2)

uint32_t last_display_update = 0;
uint32_t system_start_time = 0;

// ==================================================================================
// DISPLAY CONFIGURATION
// ==================================================================================

#define VERSION_MAJOR 4
#define VERSION_MINOR 0
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

// Proximity detection thresholds (BASELINE-RELATIVE, like ambient light!)
#define PROXIMITY_VARIATION_THRESHOLD 8 // Change from baseline needed (any deviation triggers!)
#define BASELINE_UPDATE_INTERVAL 1000   // ms between baseline updates
#define SENSOR_UPDATE_INTERVAL 15       // ms between sensor readings (optimized for fast ball/hand detection)
#define DISPLAY_UPDATE_INTERVAL 200     // ms between display updates

// Ball detection timing
#define SIDE_CORRELATION_WINDOW 150   // ms window to correlate S1→S2 or S2→S1
#define DETECTION_PAUSE_DURATION 3000 // ms to pause detection after trigger (LED display time)

// Debug mode
#define DEBUG_MODE_SENSORS_ONLY false // Set true to disable ball detection
#define VERBOSE_SENSOR_LOGGING false  // Set true for detailed logging (helps tune threshold)
#define TEST_MODE_ANY_DETECTION false // Set true to trigger green LEDs on ANY detection (for testing - DISABLED, using directional now!)

// LED control (WS2812B/WS2818B strip)
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB
#define LED_DISPLAY_DURATION 3000 // ms to show LED feedback
#define NUM_LEDS 72               // Number of LEDs in strip
#define LED_BRIGHTNESS 128        // 0-255, 50% brightness

// Detection history
#define MAX_DETECTION_HISTORY 5
struct DetectionEvent
{
    uint32_t timestamp;
    int sensor_id;            // 0-5 for the 6 sensors
    uint16_t proximity_value; // Proximity reading that triggered
    String side_name;         // "S1" or "S2"
    String event_type;        // "Player 1", "Player 2", "Detection"
    bool active;
};
DetectionEvent detection_history[MAX_DETECTION_HISTORY];
int detection_history_count = 0;

// Ball detection state
enum BallTriggerType
{
    NO_TRIGGER,
    PLAYER_1_TRIGGER, // S1 → S2 (Green)
    PLAYER_2_TRIGGER, // S2 → S1 (Blue)
    UNKNOWN_TRIGGER   // Detected but direction unclear
};

struct BallDetectionState
{
    BallTriggerType last_trigger = NO_TRIGGER;
    uint32_t last_trigger_time = 0;
    uint32_t detection_pause_until = 0;
    bool detection_paused = false;

    // Rolling detection windows
    uint32_t side_a_last_trigger = 0;
    uint32_t side_b_last_trigger = 0;
    int side_a_trigger_sensor = -1;
    int side_b_trigger_sensor = -1;

    // LED state
    bool led_active = false;
    uint32_t led_start_time = 0;
} ball_state;

// FastLED array for WS2812B strip
CRGB leds[NUM_LEDS];

TFT_eSPI tft = TFT_eSPI();

// ==================================================================================
// LED CONTROL FUNCTIONS
// ==================================================================================

void initializeLEDs()
{
    Serial.println("*** INITIALIZING LED STRIP ***");
    Serial.println("Make sure DWEII power module is connected for 72 LEDs!");

    // Initialize FastLED with WS2812B strip on GPIO 16
    FastLED.addLeds<LED_TYPE, PIN_LED_STRIP_DATA, COLOR_ORDER>(leds, NUM_LEDS);
    FastLED.setBrightness(LED_BRIGHTNESS);

    // Clear all LEDs to start
    FastLED.clear();
    FastLED.show();

    Serial.println("FastLED strip initialized successfully");
    Serial.printf("  Type: WS2812B/WS2818B\n");
    Serial.printf("  Count: %d LEDs\n", NUM_LEDS);
    Serial.printf("  Data Pin: GPIO %d\n", PIN_LED_STRIP_DATA);
    Serial.printf("  Brightness: %d/255\n", LED_BRIGHTNESS);
}

// Helper function to format sensor name in P1S1/P2S2 format
String getSensorName(int sensor_id)
{
    int pcb_num = (sensor_id / 2) + 1;    // 0,1 → P1; 2,3 → P2; 4,5 → P3
    int sensor_num = (sensor_id % 2) + 1; // 0,2,4 → S1; 1,3,5 → S2
    return "P" + String(pcb_num) + "S" + String(sensor_num);
}

void setLEDColor(BallTriggerType trigger_type)
{
    CRGB color;
    String trigger_name;

    switch (trigger_type)
    {
    case PLAYER_1_TRIGGER:
        color = CRGB::Green;
        trigger_name = "Player 1 (Green)";
        break;
    case PLAYER_2_TRIGGER:
        color = CRGB::Blue;
        trigger_name = "Player 2 (Blue)";
        break;
    case UNKNOWN_TRIGGER:
        color = CRGB::Red;
        trigger_name = "Unknown (Red)";
        break;
    default:
        color = CRGB::Black;
        trigger_name = "Off";
        break;
    }

    ball_state.led_active = (trigger_type != NO_TRIGGER);
    ball_state.led_start_time = millis();

    // Set all LEDs to the specified color
    if (ball_state.led_active)
    {
        fill_solid(leds, NUM_LEDS, color);
        FastLED.show();
        Serial.println("🎯 BALL DETECTED! " + trigger_name);
    }
    else
    {
        FastLED.clear();
        FastLED.show();
    }
}

void updateLEDs()
{
    if (ball_state.led_active)
    {
        uint32_t elapsed = millis() - ball_state.led_start_time;
        if (elapsed >= LED_DISPLAY_DURATION)
        {
            setLEDColor(NO_TRIGGER); // Turn off LEDs
        }
    }
}

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
    tft.println("Motion Play v4.0");
    tft.setTextSize(1);
    tft.setCursor(10, 35);
    tft.setTextColor(COLOR_CYAN, COLOR_BLACK);
    tft.println("Proximity Detection Test");

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
    Serial.println("Initializing PCA9546A multiplexers on all TCA channels...");

    int pca_found_count = 0;

    // Scan all 3 TCA channels for sensor boards
    for (int tca_ch = 0; tca_ch < 3; tca_ch++)
    {
        Serial.println("\n=== Scanning TCA Channel " + String(tca_ch) + " ===");

        // Select TCA channel
        if (!tca.selectChannel(tca_ch))
        {
            Serial.println("  ❌ Failed to select TCA channel " + String(tca_ch));
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
                Serial.println("  ✅ PCA9546A found at 0x" + String(test_addr, HEX));
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

            Serial.println("  ✅ Initialized PCA" + String(tca_ch) + " at address 0x" + String(working_address, HEX));
        }
        else
        {
            Serial.println("  ℹ️  No PCA9546A found on TCA channel " + String(tca_ch));
        }
    }

    tca.disableAllChannels();

    Serial.println("\n=== PCA Initialization Summary ===");
    Serial.println("Found " + String(pca_found_count) + " sensor board(s)");

    if (pca_found_count == 0)
    {
        Serial.println("❌ No PCA9546A multiplexers found!");
        return false;
    }

    for (int i = 0; i < 3; i++)
    {
        if (pca_addresses[i] != 0)
        {
            Serial.println("  Board " + String(i + 1) + ": TCA" + String(i) + " → PCA at 0x" + String(pca_addresses[i], HEX));
        }
    }

    Serial.println("✅ PCA9546A initialization complete");
    return true;
}

// ==================================================================================
// SENSOR MANAGEMENT
// ==================================================================================

// Add detection to history
void addDetectionEvent(int sensor_id, uint16_t proximity_value, String event_type)
{
    // Shift history array
    for (int i = MAX_DETECTION_HISTORY - 1; i > 0; i--)
    {
        detection_history[i] = detection_history[i - 1];
    }

    // Add new event
    detection_history[0].timestamp = millis();
    detection_history[0].sensor_id = sensor_id;
    detection_history[0].proximity_value = proximity_value;
    detection_history[0].side_name = sensors[sensor_id].side_name;
    detection_history[0].event_type = event_type;
    detection_history[0].active = true;

    if (detection_history_count < MAX_DETECTION_HISTORY)
    {
        detection_history_count++;
    }

    Serial.println("🔴 DETECTION! " + getSensorName(sensor_id) +
                   " - " + event_type + ": Proximity=" + String(proximity_value));
}

// Initialize sensor mapping (which TCA/PCA channels each sensor uses)
void initializeSensorMapping()
{
    for (int i = 0; i < 6; i++)
    {
        sensors[i].tca_channel = i / 2; // 0,1→0  2,3→1  4,5→2
        sensors[i].pca_channel = i % 2; // 0,2,4→0  1,3,5→1
        sensors[i].side_name = (sensors[i].pca_channel == 0) ? "S1" : "S2";

        Serial.println(getSensorName(i) + ": TCA" + String(sensors[i].tca_channel) +
                       "/PCA" + String(sensors[i].pca_channel) + " (" + sensors[i].side_name + ")");
    }

    Serial.println("\n✅ Full dual-sensor support (S1 and S2 per board)");
    Serial.println("   S1 sensors (P1S1, P2S1, P3S1) + S2 sensors (P1S2, P2S2, P3S2) = Directional detection");
}

void initializeSensors()
{
    Serial.println("Initializing VCNL4040 proximity sensors for 6-sensor system...");
    Serial.println("Target: 3 sensor boards × 2 sensors each = 6 total sensors");

    // Initialize sensor mapping first
    initializeSensorMapping();

    delay(500); // Give hardware time to settle

    int active_count = 0;

    // Test all 6 sensors across 3 TCA channels
    for (int sensor_id = 0; sensor_id < 6; sensor_id++)
    {
        uint8_t tca_ch = sensors[sensor_id].tca_channel;
        uint8_t pca_ch = sensors[sensor_id].pca_channel;

        Serial.println("\n=== Initializing Sensor " + String(sensor_id) + " ===");
        Serial.println("    TCA Channel: " + String(tca_ch) + ", PCA Channel: " + String(pca_ch));
        Serial.println("    Side: " + sensors[sensor_id].side_name);

        // Update display with overall progress
        tft.fillRect(0, 50, SCREEN_WIDTH, 25, COLOR_DARK_GRAY);
        tft.setTextColor(COLOR_WHITE, COLOR_DARK_GRAY);
        tft.setTextSize(1);
        tft.setCursor(10, 55);
        tft.println("Initializing Sensor " + String(sensor_id + 1) + " of 6");
        tft.setCursor(10, 65);
        tft.println("TCA" + String(tca_ch) + "/PCA" + String(pca_ch) + " (" + sensors[sensor_id].side_name + ")");

        // Reset sensor data
        sensors[sensor_id].initialized = false;
        sensors[sensor_id].active = false;
        sensors[sensor_id].status = "Testing...";

        // Skip if no PCA was found on this TCA channel
        if (pca_addresses[tca_ch] == 0)
        {
            sensors[sensor_id].status = "No Board";
            Serial.println("    ⚠️  No sensor board on TCA channel " + String(tca_ch));
            continue;
        }

        // Select TCA channel for this sensor board
        if (!tca.selectChannel(tca_ch))
        {
            sensors[sensor_id].status = "TCA Select Failed";
            Serial.println("    ❌ Failed to select TCA channel " + String(tca_ch));
            continue;
        }

        delay(50); // TCA switching delay

        // Select PCA channel on the sensor board
        if (!pca_instances[tca_ch].selectChannel(pca_ch))
        {
            sensors[sensor_id].status = "PCA Select Failed";
            Serial.println("    ❌ Failed to select PCA channel " + String(pca_ch));
            continue;
        }

        delay(50); // PCA switching delay

        // Check if VCNL4040 responds at standard address 0x60
        Wire.beginTransmission(0x60);
        byte error = Wire.endTransmission();
        if (error != 0)
        {
            sensors[sensor_id].status = "No Device (0x60)";
            Serial.println("    ❌ No VCNL4040 found at 0x60 (I2C error: " + String(error) + ")");
            Serial.println("       Check: Sensor soldering, VDDIO power (3.3V to pin 3), I2C connections");
            continue;
        }

        // Try to initialize VCNL4040
        if (!vcnl_sensors[sensor_id].begin())
        {
            sensors[sensor_id].status = "Init Failed";
            Serial.println("    ❌ VCNL4040 initialization failed");
            continue;
        }

        Serial.println("    ✅ VCNL4040 found and initialized!");

        // Configure for proximity detection
        Serial.println("    🔧 Configuring for proximity detection...");

        // Enable proximity sensor
        vcnl_sensors[sensor_id].enableProximity(true);
        Serial.println("      ✅ Proximity sensor enabled");

        // Set LED current to 200mA for maximum range
        vcnl_sensors[sensor_id].setProximityLEDCurrent(VCNL4040_LED_CURRENT_200MA);
        Serial.println("      ✅ LED current set to 200mA (maximum)");

        // Set integration time to 8T for best sensitivity
        vcnl_sensors[sensor_id].setProximityIntegrationTime(VCNL4040_PROXIMITY_INTEGRATION_TIME_8T);
        Serial.println("      ✅ Integration time set to 8T (highest sensitivity)");

        // Enable high resolution mode for 16-bit proximity values (0-65535)
        vcnl_sensors[sensor_id].setProximityHighResolution(true);
        Serial.println("      ✅ High resolution mode enabled (16-bit)");

        // Set duty cycle for good balance
        vcnl_sensors[sensor_id].setProximityLEDDutyCycle(VCNL4040_LED_DUTY_1_160);
        Serial.println("      ✅ LED duty cycle set to 1/160");

        delay(100); // Allow settings to take effect

        // Test readings
        Serial.println("    🧪 PROXIMITY TEST - Place hand at different distances!");
        Serial.println("    Expected: Values 100+ when hand close (1-10cm)");

        for (int test = 0; test < 10; test++)
        {
            delay(200);
            uint16_t prox = vcnl_sensors[sensor_id].getProximity();
            uint16_t amb = vcnl_sensors[sensor_id].getAmbientLight();

            String detection_status = "CLEAR";
            if (prox > 500)
                detection_status = "🔴 VERY CLOSE";
            else if (prox > 200)
                detection_status = "🟡 CLOSE";
            else if (prox > 100)
                detection_status = "🟢 DETECTED";

            Serial.println("      Test " + String(test + 1) + " - Prox: " + String(prox) +
                           ", Amb: " + String(amb) + " - " + detection_status);
        }

        // Take baseline proximity readings (like ambient light calibration!)
        Serial.println("    📊 Establishing proximity baseline...");
        uint32_t baseline_sum = 0;
        const int baseline_samples = 10;

        for (int sample = 0; sample < baseline_samples; sample++)
        {
            delay(50);
            uint16_t prox = vcnl_sensors[sensor_id].getProximity();
            baseline_sum += prox;
            if (sample % 3 == 0)
            {
                Serial.println("      Sample " + String(sample + 1) + ": " + String(prox));
            }
        }

        uint16_t baseline = baseline_sum / baseline_samples;
        Serial.println("    ✅ Baseline proximity: " + String(baseline) + " (will detect ANY change > " +
                       String(PROXIMITY_VARIATION_THRESHOLD) + ")");

        // Initialize sensor data
        sensors[sensor_id].initialized = true;
        sensors[sensor_id].active = true;
        sensors[sensor_id].status = "Active";
        sensors[sensor_id].error_count = 0;
        sensors[sensor_id].max_proximity = 0;
        sensors[sensor_id].proximity_baseline = baseline;
        sensors[sensor_id].proximity_threshold = PROXIMITY_VARIATION_THRESHOLD;
        sensors[sensor_id].baseline_update_time = millis();

        // Set startup delay (2 seconds to prevent false triggers)
        sensors[sensor_id].last_reading_time = millis() + 2000;
        Serial.println("    ⏱️  Detection disabled for 2 seconds to prevent false startup detections");

        active_count++;
    }

    // Clean up - disable all PCA instances
    for (int i = 0; i < 3; i++)
    {
        pca_instances[i].disableAllChannels();
    }
    tca.disableAllChannels();

    // Show completion screen
    tft.fillScreen(COLOR_BLACK);
    tft.setTextColor(COLOR_GREEN, COLOR_BLACK);
    tft.setTextSize(2);
    tft.setCursor(10, 20);
    tft.println("Initialization Complete!");

    tft.setTextColor(COLOR_WHITE, COLOR_BLACK);
    tft.setTextSize(1);
    tft.setCursor(10, 50);
    tft.println("Active sensors: " + String(active_count) + " / 6");

    if (active_count >= 4)
    {
        tft.setTextColor(COLOR_GREEN, COLOR_BLACK);
        tft.setCursor(10, 70);
        tft.println("Working sensors: " + String(active_count));
        tft.setCursor(10, 85);
        tft.println("Directional detection active!");
        tft.setCursor(10, 100);
        tft.setTextColor(COLOR_CYAN, COLOR_BLACK);
        tft.println("Green=A->B  Blue=B->A  150ms window");
    }
    else if (active_count > 0)
    {
        tft.setTextColor(COLOR_YELLOW, COLOR_BLACK);
        tft.setCursor(10, 70);
        tft.println("Partial system - " + String(active_count) + " sensor(s)");
        tft.setCursor(10, 85);
        tft.println("Limited directional detection");
    }
    else
    {
        tft.setTextColor(COLOR_RED, COLOR_BLACK);
        tft.setCursor(10, 70);
        tft.println("No sensors detected!");
        tft.setCursor(10, 85);
        tft.println("Check hardware connections");
    }

    delay(3000); // Show completion screen

    Serial.println("\n" + String("=").substring(0, 60));
    Serial.println("SENSOR INITIALIZATION COMPLETE");
    Serial.println("Active sensors: " + String(active_count) + " / 6");

    if (active_count == 0)
    {
        Serial.println("❌ NO SENSORS ACTIVE - Check hardware connections!");
    }
    else if (active_count < 4)
    {
        Serial.println("⚠️  Partial system - " + String(active_count) + " sensors active");
        Serial.println("   Directional detection possible but limited");
        Serial.println("   Need at least 2 boards with both sensors for best results");
    }
    else
    {
        Serial.println("✅ DIRECTIONAL DETECTION READY!");
        Serial.println("   🟢 Green LEDs: Player 1 (S1 → S2)");
        Serial.println("   🔵 Blue LEDs: Player 2 (S2 → S1)");
        Serial.println("   ⏱️  Detection window: 20-" + String(SIDE_CORRELATION_WINDOW) + "ms");
        Serial.println("   🎯 Using baseline-relative detection for all speeds!");
    }
    Serial.println(String("=").substring(0, 60));
}

// Ball detection with directional sensing
void detectBallPassage(uint32_t current_time)
{
    // Check if we're in detection pause period
    if (ball_state.detection_paused)
    {
        if (current_time >= ball_state.detection_pause_until)
        {
            ball_state.detection_paused = false;
            Serial.println("🔄 Ball detection resumed");
        }
        else
        {
            return; // Skip detection during pause
        }
    }

    // Look for NEW proximity detections (rising edge only, not continuous detection)
    bool side_a_triggered = false;
    bool side_b_triggered = false;
    int strongest_side_a_sensor = -1;
    int strongest_side_b_sensor = -1;
    int max_side_a_proximity = 0;
    int max_side_b_proximity = 0;

    // Check S1 sensors (0, 2, 4: P1S1, P2S1, P3S1) - only VERY NEW detections (rising edge)
    for (int i = 0; i < 6; i += 2)
    {
        if (sensors[i].active && sensors[i].object_detected)
        {
            // Only count if this is a VERY NEW detection (within last 20ms = ~1 reading)
            // This ensures we only capture the rising edge, not continuous detection
            if ((current_time - sensors[i].last_detection_time) < 20)
            {
                if (sensors[i].proximity > max_side_a_proximity)
                {
                    max_side_a_proximity = sensors[i].proximity;
                    strongest_side_a_sensor = i;
                }
            }
        }
    }
    side_a_triggered = (strongest_side_a_sensor >= 0);

    // Check S2 sensors (1, 3, 5: P1S2, P2S2, P3S2) - only VERY NEW detections (rising edge)
    for (int i = 1; i < 6; i += 2)
    {
        if (sensors[i].active && sensors[i].object_detected)
        {
            // Only count if this is a VERY NEW detection (within last 20ms = ~1 reading)
            // This ensures we only capture the rising edge, not continuous detection
            if ((current_time - sensors[i].last_detection_time) < 20)
            {
                if (sensors[i].proximity > max_side_b_proximity)
                {
                    max_side_b_proximity = sensors[i].proximity;
                    strongest_side_b_sensor = i;
                }
            }
        }
    }
    side_b_triggered = (strongest_side_b_sensor >= 0);

    // Update side trigger timestamps (only on NEW detections, don't overwrite recent triggers)
    if (side_a_triggered)
    {
        // Only update if we don't have a recent trigger (prevent timestamp overwriting)
        if (ball_state.side_a_last_trigger == 0 ||
            (current_time - ball_state.side_a_last_trigger) > SIDE_CORRELATION_WINDOW)
        {
            ball_state.side_a_last_trigger = current_time;
            ball_state.side_a_trigger_sensor = strongest_side_a_sensor;
            Serial.println("1️⃣  S1 trigger: " + getSensorName(strongest_side_a_sensor) + " (Prox: " + String(max_side_a_proximity) + ")");
        }
        else
        {
            // Timestamp locked - waiting for correlation or expiry
            Serial.println("⏸️  S1 re-detection blocked (timestamp locked, waiting for S2 or timeout)");
        }
    }

    if (side_b_triggered)
    {
        // Only update if we don't have a recent trigger (prevent timestamp overwriting)
        if (ball_state.side_b_last_trigger == 0 ||
            (current_time - ball_state.side_b_last_trigger) > SIDE_CORRELATION_WINDOW)
        {
            ball_state.side_b_last_trigger = current_time;
            ball_state.side_b_trigger_sensor = strongest_side_b_sensor;
            Serial.println("2️⃣  S2 trigger: " + getSensorName(strongest_side_b_sensor) + " (Prox: " + String(max_side_b_proximity) + ")");
        }
        else
        {
            // Timestamp locked - waiting for correlation or expiry
            Serial.println("⏸️  S2 re-detection blocked (timestamp locked, waiting for S1 or timeout)");
        }
    }

    // Analyze directional patterns
    BallTriggerType detected_trigger = NO_TRIGGER;

    // Check for S1 → S2 pattern (Player 1)
    if (ball_state.side_a_last_trigger > 0 && ball_state.side_b_last_trigger > ball_state.side_a_last_trigger)
    {
        uint32_t time_diff = ball_state.side_b_last_trigger - ball_state.side_a_last_trigger;

        if (time_diff >= 20 && time_diff <= SIDE_CORRELATION_WINDOW)
        {
            detected_trigger = PLAYER_1_TRIGGER;
            Serial.println("🏀 PLAYER 1 DETECTED! S1→S2 in " + String(time_diff) + "ms");
            Serial.println("    Sensors: " + getSensorName(ball_state.side_a_trigger_sensor) +
                           " → " + getSensorName(ball_state.side_b_trigger_sensor));
        }
        else if (time_diff < 20)
        {
            Serial.println("⏱️  S1→S2 sequence TOO FAST: " + String(time_diff) + "ms (min 20ms) - " +
                           getSensorName(ball_state.side_a_trigger_sensor) + " → " + getSensorName(ball_state.side_b_trigger_sensor));
        }
        else if (time_diff > SIDE_CORRELATION_WINDOW)
        {
            Serial.println("⏱️  S1→S2 sequence TOO SLOW: " + String(time_diff) + "ms (max " + String(SIDE_CORRELATION_WINDOW) + "ms) - " +
                           getSensorName(ball_state.side_a_trigger_sensor) + " → " + getSensorName(ball_state.side_b_trigger_sensor));
        }
    }

    // Check for S2 → S1 pattern (Player 2)
    else if (ball_state.side_b_last_trigger > 0 && ball_state.side_a_last_trigger > ball_state.side_b_last_trigger)
    {
        uint32_t time_diff = ball_state.side_a_last_trigger - ball_state.side_b_last_trigger;

        if (time_diff >= 20 && time_diff <= SIDE_CORRELATION_WINDOW)
        {
            detected_trigger = PLAYER_2_TRIGGER;
            Serial.println("🏀 PLAYER 2 DETECTED! S2→S1 in " + String(time_diff) + "ms");
            Serial.println("    Sensors: " + getSensorName(ball_state.side_b_trigger_sensor) +
                           " → " + getSensorName(ball_state.side_a_trigger_sensor));
        }
        else if (time_diff < 20)
        {
            Serial.println("⏱️  S2→S1 sequence TOO FAST: " + String(time_diff) + "ms (min 20ms) - " +
                           getSensorName(ball_state.side_b_trigger_sensor) + " → " + getSensorName(ball_state.side_a_trigger_sensor));
        }
        else if (time_diff > SIDE_CORRELATION_WINDOW)
        {
            Serial.println("⏱️  S2→S1 sequence TOO SLOW: " + String(time_diff) + "ms (max " + String(SIDE_CORRELATION_WINDOW) + "ms) - " +
                           getSensorName(ball_state.side_b_trigger_sensor) + " → " + getSensorName(ball_state.side_a_trigger_sensor));
        }
    }

    // Trigger LED response
    if (detected_trigger != NO_TRIGGER)
    {
        // Prevent rapid-fire triggers
        static uint32_t last_ball_detection = 0;
        if (current_time - last_ball_detection < 1000)
        {
            return;
        }
        last_ball_detection = current_time;

        ball_state.last_trigger = detected_trigger;
        ball_state.last_trigger_time = current_time;
        ball_state.detection_paused = true;
        ball_state.detection_pause_until = current_time + DETECTION_PAUSE_DURATION;

        // Set LED color
        setLEDColor(detected_trigger);

        String trigger_name = (detected_trigger == PLAYER_1_TRIGGER) ? "Player 1" : "Player 2";

        int primary_sensor = (detected_trigger == PLAYER_1_TRIGGER) ? ball_state.side_b_trigger_sensor
                                                                    : ball_state.side_a_trigger_sensor;

        if (primary_sensor >= 0)
        {
            addDetectionEvent(primary_sensor, sensors[primary_sensor].proximity, trigger_name);
        }

        // Reset trigger timestamps
        ball_state.side_a_last_trigger = 0;
        ball_state.side_b_last_trigger = 0;

        Serial.println("🔄 Detection paused for " + String(DETECTION_PAUSE_DURATION) + "ms");
    }

    // Clean up old single-side triggers
    if (ball_state.side_a_last_trigger > 0 &&
        (current_time - ball_state.side_a_last_trigger) > SIDE_CORRELATION_WINDOW)
    {
        ball_state.side_a_last_trigger = 0;
    }
    if (ball_state.side_b_last_trigger > 0 &&
        (current_time - ball_state.side_b_last_trigger) > SIDE_CORRELATION_WINDOW)
    {
        ball_state.side_b_last_trigger = 0;
    }
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

    // Read all 6 sensors across 3 TCA channels
    for (int sensor_id = 0; sensor_id < 6; sensor_id++)
    {
        if (!sensors[sensor_id].active)
        {
            continue;
        }

        uint8_t tca_ch = sensors[sensor_id].tca_channel;
        uint8_t pca_ch = sensors[sensor_id].pca_channel;

        // Select TCA channel for this sensor board
        if (!tca.selectChannel(tca_ch))
        {
            sensors[sensor_id].error_count++;
            if (sensors[sensor_id].error_count > 10)
            {
                sensors[sensor_id].status = "TCA Error";
                sensors[sensor_id].active = false;
            }
            continue;
        }

        // Select PCA channel on the sensor board
        if (!pca_instances[tca_ch].selectChannel(pca_ch))
        {
            sensors[sensor_id].error_count++;
            if (sensors[sensor_id].error_count > 10)
            {
                sensors[sensor_id].status = "PCA Error";
                sensors[sensor_id].active = false;
            }
            continue;
        }

        // Read sensor values (no delay needed - I2C is fast enough)
        try
        {
            uint16_t new_proximity = vcnl_sensors[sensor_id].getProximity();
            uint16_t new_ambient = vcnl_sensors[sensor_id].getAmbientLight();

            // Update readings
            sensors[sensor_id].proximity = new_proximity;
            sensors[sensor_id].ambient = new_ambient;
            sensors[sensor_id].status = "Active";
            sensors[sensor_id].error_count = 0;

            // Calculate variation from baseline (like ambient light!)
            int16_t variation = (int16_t)new_proximity - (int16_t)sensors[sensor_id].proximity_baseline;
            sensors[sensor_id].proximity_variation = variation;
            uint16_t abs_variation = abs(variation);

            // Update baseline slowly when stable
            if (current_time - sensors[sensor_id].baseline_update_time > BASELINE_UPDATE_INTERVAL)
            {
                if (abs_variation <= 2) // Very stable
                {
                    // Fast update (1/4 weight)
                    sensors[sensor_id].proximity_baseline = (sensors[sensor_id].proximity_baseline * 3 + new_proximity) / 4;
                }
                else if (abs_variation <= sensors[sensor_id].proximity_threshold)
                {
                    // Slow update (1/16 weight)
                    sensors[sensor_id].proximity_baseline = (sensors[sensor_id].proximity_baseline * 15 + new_proximity) / 16;
                }
                sensors[sensor_id].baseline_update_time = current_time;
            }

            // Track maximum proximity
            if (new_proximity > sensors[sensor_id].max_proximity)
            {
                sensors[sensor_id].max_proximity = new_proximity;
            }

            // Log proximity values for tuning
            if (VERBOSE_SENSOR_LOGGING && abs_variation > 2)
            {
                static uint32_t last_log = 0;
                if (current_time - last_log > 100) // Every 100ms
                {
                    Serial.println("📊 S" + String(sensor_id) +
                                   " Prox: " + String(new_proximity) +
                                   ", Baseline: " + String(sensors[sensor_id].proximity_baseline) +
                                   ", Variation: " + String(variation) +
                                   " (Thresh: " + String(sensors[sensor_id].proximity_threshold) + ")");
                    last_log = current_time;
                }
            }

            // BASELINE-RELATIVE DETECTION (like ambient light!)
            bool was_detected = sensors[sensor_id].object_detected;
            bool is_detected = false;

            // Check if past startup delay
            if (current_time > sensors[sensor_id].last_reading_time)
            {
                // Detect ANY significant deviation from baseline!
                is_detected = (abs_variation > sensors[sensor_id].proximity_threshold);
                sensors[sensor_id].object_detected = is_detected;

                // If we just detected an object
                if (is_detected && !was_detected)
                {
                    sensors[sensor_id].last_detection_time = current_time;

                    if (VERBOSE_SENSOR_LOGGING)
                    {
                        Serial.println("🔍 SENSOR " + String(sensor_id) + " TRIGGER:");
                        Serial.println("    Prox: " + String(new_proximity) +
                                       " (Baseline: " + String(sensors[sensor_id].proximity_baseline) +
                                       ", Variation: " + String(variation) + ")");
                    }

                    addDetectionEvent(sensor_id, new_proximity, "Detection");
                }
            }
            else
            {
                // Still in startup delay
                sensors[sensor_id].object_detected = false;
            }
        }
        catch (...)
        {
            sensors[sensor_id].error_count++;
            if (sensors[sensor_id].error_count > 10)
            {
                sensors[sensor_id].status = "Read Error";
                sensors[sensor_id].active = false;
            }
        }
    }

    // Clean up - disable all channels after reading
    for (int i = 0; i < 3; i++)
    {
        pca_instances[i].disableAllChannels();
    }
    tca.disableAllChannels();

    // TEST MODE: Trigger green LEDs on ANY detection (for testing with single sensors)
    if (TEST_MODE_ANY_DETECTION)
    {
        // Check if any sensor is currently detecting and find max proximity
        bool any_detection = false;
        int max_proximity = 0;
        int detecting_sensor = -1;

        for (int i = 0; i < 6; i++)
        {
            if (sensors[i].active && sensors[i].object_detected)
            {
                any_detection = true;
                if (sensors[i].proximity > max_proximity)
                {
                    max_proximity = sensors[i].proximity;
                    detecting_sensor = i;
                }
            }
        }

        // Trigger green LEDs on detection (reduced cooldown from 1000ms to 300ms)
        static uint32_t last_test_trigger = 0;
        if (any_detection && (current_time - last_test_trigger > 300))
        {
            last_test_trigger = current_time;
            setLEDColor(PLAYER_1_TRIGGER); // Green LEDs
            Serial.println("🟢 TEST MODE: Detection on S" + String(detecting_sensor) +
                           " - Proximity: " + String(max_proximity) + " - GREEN LEDs ON");
        }
    }
    // Check for ball passage detection (unless in debug mode or test mode)
    else if (!DEBUG_MODE_SENSORS_ONLY)
    {
        detectBallPassage(current_time);
    }
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
    tft.println("Motion Play v4.0 - Proximity");

    // Uptime
    uint32_t uptime_seconds = (millis() - system_start_time) / 1000;
    String uptime = "Up: " + String(uptime_seconds) + "s";
    tft.setTextColor(COLOR_CYAN, COLOR_DARK_GRAY);
    tft.setCursor(SCREEN_WIDTH - (uptime.length() * 6) - 5, 5);
    tft.println(uptime);

    // Active sensor count
    int active_count = 0;
    for (int i = 0; i < 6; i++)
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
        tft.println("Last: " + getSensorName(detection_history[0].sensor_id) + " " +
                    detection_history[0].event_type + " (" + String(detection_history[0].proximity_value) + ") " +
                    String(last_detection_age) + "s ago");
    }
    else
    {
        tft.setTextColor(COLOR_GRAY, COLOR_BLACK);
        tft.setTextSize(1);
        tft.setCursor(5, history_y);
        tft.println("No detections yet - place hand near sensors");
    }
}

void drawSensorDisplay()
{
    int start_y = 30;
    int sensor_height = 22;

    for (int i = 0; i < 6; i++)
    {
        int y_pos = start_y + (i * sensor_height);

        // Clear sensor area
        tft.fillRect(0, y_pos, SCREEN_WIDTH, sensor_height - 1, COLOR_BLACK);

        // Sensor header with new P1S1/P2S2 naming
        tft.setTextColor(COLOR_WHITE, COLOR_BLACK);
        tft.setTextSize(1);
        tft.setCursor(5, y_pos + 2);
        tft.println(getSensorName(i) + ":");

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

        tft.fillCircle(30, y_pos + 6, 3, status_color);

        // Status text
        tft.setTextColor(COLOR_CYAN, COLOR_BLACK);
        tft.setCursor(38, y_pos + 2);
        String short_status = sensors[i].status;
        if (short_status.length() > 8)
            short_status = short_status.substring(0, 8);
        tft.println(short_status);

        if (sensors[i].active)
        {
            // Proximity reading
            tft.setTextColor(sensors[i].object_detected ? COLOR_RED : COLOR_WHITE, COLOR_BLACK);
            tft.setCursor(5, y_pos + 12);
            tft.println("P:" + String(sensors[i].proximity) + " Max:" + String(sensors[i].max_proximity));

            // Detection status
            if (sensors[i].object_detected)
            {
                tft.setTextColor(COLOR_RED, COLOR_BLACK);
                tft.setCursor(200, y_pos + 2);
                tft.println("DETECT!");
            }
            else
            {
                tft.setTextColor(COLOR_GREEN, COLOR_BLACK);
                tft.setCursor(200, y_pos + 2);
                tft.println("Clear");
            }

            // Last detection time
            if (millis() < sensors[i].last_reading_time)
            {
                // Still in startup delay
                uint32_t remaining = (sensors[i].last_reading_time - millis()) / 1000;
                tft.setTextColor(COLOR_GRAY, COLOR_BLACK);
                tft.setCursor(200, y_pos + 12);
                tft.println("Delay:" + String(remaining));
            }
            else if (sensors[i].last_detection_time > 0)
            {
                uint32_t since_detection = (millis() - sensors[i].last_detection_time) / 1000;
                tft.setTextColor(COLOR_YELLOW, COLOR_BLACK);
                tft.setCursor(200, y_pos + 12);
                if (since_detection < 60)
                    tft.println(String(since_detection) + "s ago");
                else
                    tft.println(">1m ago");
            }
        }
        else
        {
            // Show why sensor is not active
            tft.setTextColor(COLOR_GRAY, COLOR_BLACK);
            tft.setCursor(5, y_pos + 12);
            if (sensors[i].error_count > 0)
            {
                tft.println("Err:" + String(sensors[i].error_count));
            }
            else
            {
                tft.println("Not found");
            }
        }

        // Separator line
        tft.drawLine(0, y_pos + sensor_height - 1, SCREEN_WIDTH, y_pos + sensor_height - 1, COLOR_DARK_GRAY);
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

        // Show initialization screen
        tft.fillScreen(COLOR_BLACK);
        tft.setTextColor(COLOR_YELLOW, COLOR_BLACK);
        tft.setTextSize(2);
        tft.setCursor(10, 20);
        tft.println("Initializing...");

        tft.setTextSize(1);
        tft.setTextColor(COLOR_CYAN, COLOR_BLACK);
        tft.setCursor(10, 45);
        tft.println("6-sensor proximity system");

        // Initialize sensors with progress display
        initializeSensors();
    }

    // Button 2 pressed (test LED feedback)
    if (!button2_current && button2_last_state)
    {
        Serial.println("Button 2 pressed - Testing LED feedback...");

        static int test_mode = 0;

        switch (test_mode)
        {
        case 0:
            Serial.println("Testing Green (Player A)");
            setLEDColor(PLAYER_1_TRIGGER);
            break;
        case 1:
            Serial.println("Testing Blue (Player B)");
            setLEDColor(PLAYER_2_TRIGGER);
            break;
        case 2:
            Serial.println("Testing Red (Unknown)");
            setLEDColor(UNKNOWN_TRIGGER);
            break;
        case 3:
            Serial.println("LEDs Off");
            setLEDColor(NO_TRIGGER);
            break;
        }

        test_mode = (test_mode + 1) % 4;
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

    Serial.println("\n" + String("=").substring(0, 60));
    Serial.println("MOTION PLAY v4.0 - PROXIMITY DETECTION SYSTEM");
    Serial.println("Build: " + String(__DATE__) + " " + String(__TIME__));
    Serial.println("Chip: " + String(ESP.getChipModel()));
    Serial.println("Free heap: " + String(ESP.getFreeHeap()) + " bytes");
    Serial.println("Target: 6 sensors (3 boards × 2 sensors each)");
    Serial.println("Detection: Proximity (IR reflection)");
    Serial.println(String("=").substring(0, 60));

    // Initialize hardware
    if (!initializeDisplay())
    {
        Serial.println("FATAL: Display initialization failed!");
        while (1)
            delay(1000);
    }

    initializeButtons();
    initializeLEDs();

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

    // Clear screen for main display
    tft.fillScreen(COLOR_BLACK);

    // Show instructions
    tft.setTextColor(COLOR_YELLOW, COLOR_BLACK);
    tft.setTextSize(1);
    tft.setCursor(10, 60);
    tft.println("Press Button 1 to initialize 6 sensors");
    tft.setCursor(10, 80);
    tft.println("(Testing proximity on new fixed PCBs!)");

    Serial.println("Setup complete. System ready.");
    Serial.println("\n📋 BUTTON CONTROLS:");
    Serial.println("  Button 1: Initialize 6-sensor proximity system");
    Serial.println("  Button 2: Test LED feedback (cycles colors)");
    Serial.println("\n⚙️  DETECTION PARAMETERS (BASELINE-RELATIVE!):");
    Serial.println("  Detection: ANY variation > " + String(PROXIMITY_VARIATION_THRESHOLD) + " from baseline");
    Serial.println("  Side correlation window: " + String(SIDE_CORRELATION_WINDOW) + "ms");
    Serial.println("  Sensor update interval: " + String(SENSOR_UPDATE_INTERVAL) + "ms (~66 readings/sec)");
    Serial.println("  Baseline updates: Every " + String(BASELINE_UPDATE_INTERVAL) + "ms (adaptive tracking)");
    Serial.println("\n🔧 SENSOR CONFIG:");
    Serial.println("  LED current: 200mA (maximum)");
    Serial.println("  Integration time: 8T (highest sensitivity)");
    Serial.println("  Resolution: 16-bit (0-65535)");

    if (TEST_MODE_ANY_DETECTION)
    {
        Serial.println("\n🟢 TEST MODE ACTIVE:");
        Serial.println("  Green LEDs will trigger on ANY proximity detection");
        Serial.println("  This is for testing with single-sensor boards");
        Serial.println("  Full directional detection needs both S1+S2 working per board");
    }
}

void loop()
{
    handleButtons();
    readSensors();
    updateDisplay();
    updateLEDs(); // Update LED state

    delay(1); // Minimal delay for fast response
}

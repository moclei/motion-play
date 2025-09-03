#include <Arduino.h>
#include <TFT_eSPI.h>
#include <Wire.h>
#include <Adafruit_VCNL4040.h>
#include "pin_config.h"
#include "components/tca9548a/TCA9548A.h"

// Display setup
TFT_eSPI tdisplay = TFT_eSPI();
TFT_eSprite sprite = TFT_eSprite(&tdisplay);

// I2C components
TCA9548A tca;
Adafruit_VCNL4040 vcnl4040_sensors[8]; // Array for up to 8 sensors
bool sensor_found[8] = {false};        // Track which channels have sensors
int active_sensors = 0;

// Build information
const char *BUILD_INFO = __DATE__ " " __TIME__;

// Terminal display system
#define MAX_DISPLAY_LINES 12
#define TERMINAL_FONT 2
#define LINE_HEIGHT 14
#include <vector>
std::vector<String> allLogLines;
bool terminalMode = true;
int displayStartLine = 0;
bool initComplete = false;

// Sensor data structure
struct SensorData
{
    uint16_t proximity;
    uint16_t ambient;
    uint16_t white;
    bool valid;
};

SensorData sensorReadings[8];

// Function declarations
void terminalPrint(String message);
void updateTerminalDisplay();
void updateSensorDisplay();
void handleButtons();
bool initializeSensors();
bool testSensorOnChannel(uint8_t channel);
void readAllSensors();
void showError(String message);

void terminalPrint(String message)
{
    Serial.println(message);
    allLogLines.push_back(message);

    if (terminalMode && !initComplete)
    {
        updateTerminalDisplay();
    }
}

void updateTerminalDisplay()
{
    sprite.fillSprite(TFT_BLACK);
    sprite.setTextColor(TFT_WHITE);
    sprite.setTextDatum(TL_DATUM);

    // Show build info at top
    sprite.setTextColor(TFT_DARKGREY);
    String buildDate = String(__DATE__).substring(0, 6) + " " + String(__TIME__).substring(0, 5);
    sprite.drawString(buildDate, 2, 2, 1);

    sprite.setTextColor(TFT_WHITE);

    // Display the most recent lines
    int totalLines = allLogLines.size();
    int startLine = max(0, totalLines - (MAX_DISPLAY_LINES - 1)); // Reserve space for build info

    for (int i = 0; i < (MAX_DISPLAY_LINES - 1) && (startLine + i) < totalLines; i++)
    {
        int lineNumber = startLine + i + 1;
        String displayText = String(lineNumber) + ": " + allLogLines[startLine + i];
        sprite.drawString(displayText, 2, (i + 1) * LINE_HEIGHT + 2, TERMINAL_FONT);
    }

    sprite.pushSprite(0, 0);
}

void updateSensorDisplay()
{
    sprite.fillSprite(TFT_BLACK);
    sprite.setTextColor(TFT_WHITE);
    sprite.setTextDatum(TL_DATUM);

    // Title
    sprite.drawString("Motion Play Sensors", 10, 5, 2);
    sprite.setTextColor(TFT_DARKGREY);
    sprite.drawString("Build: " + String(__DATE__).substring(0, 6), 200, 5, 1);

    sprite.setTextColor(TFT_WHITE);

    // Show active sensors count
    sprite.drawString("Active Sensors: " + String(active_sensors), 10, 25, 2);

    // Display sensor data
    int yPos = 45;
    for (int ch = 0; ch < 8; ch++)
    {
        if (sensor_found[ch])
        {
            sprite.setTextColor(TFT_GREEN);
            sprite.drawString("Ch" + String(ch) + ":", 10, yPos, 2);

            if (sensorReadings[ch].valid)
            {
                sprite.setTextColor(TFT_WHITE);
                sprite.drawString("P:" + String(sensorReadings[ch].proximity), 60, yPos, 2);
                sprite.drawString("A:" + String(sensorReadings[ch].ambient), 130, yPos, 2);
                sprite.drawString("W:" + String(sensorReadings[ch].white), 200, yPos, 2);
            }
            else
            {
                sprite.setTextColor(TFT_RED);
                sprite.drawString("ERROR", 60, yPos, 2);
            }
            yPos += 20;
        }
    }

    // Instructions at bottom
    sprite.setTextColor(TFT_DARKGREY);
    sprite.drawString("BTN1+BTN2: Reset | P=Prox A=Amb W=White", 5, 155, 1);

    sprite.pushSprite(0, 0);
}

void handleButtons()
{
    static bool bothPressed = false;
    static unsigned long bothPressedStart = 0;
    static bool lastBtn1State = HIGH;
    static bool lastBtn2State = HIGH;

    unsigned long now = millis();
    bool btn1Down = digitalRead(PIN_BUTTON_1) == LOW;
    bool btn2Down = digitalRead(PIN_BUTTON_2) == LOW;

    const unsigned long RESET_HOLD_TIME = 2000;

    // Check for simultaneous press and hold for reset
    if (btn1Down && btn2Down)
    {
        if (!bothPressed)
        {
            bothPressed = true;
            bothPressedStart = now;

            sprite.fillSprite(TFT_BLACK);
            sprite.setTextColor(TFT_RED);
            sprite.setTextDatum(MC_DATUM);
            sprite.drawString("Hold for Reset...", 160, 85, 4);
            sprite.pushSprite(0, 0);
        }
        else if (now - bothPressedStart >= RESET_HOLD_TIME)
        {
            sprite.fillSprite(TFT_BLACK);
            sprite.setTextColor(TFT_RED);
            sprite.setTextDatum(MC_DATUM);
            sprite.drawString("Resetting...", 160, 85, 4);
            sprite.pushSprite(0, 0);
            delay(500);
            ESP.restart();
        }
    }
    else if (bothPressed)
    {
        bothPressed = false;
        if (initComplete)
        {
            updateSensorDisplay();
        }
        else
        {
            updateTerminalDisplay();
        }
    }

    lastBtn1State = btn1Down;
    lastBtn2State = btn2Down;
}

bool testSensorOnChannel(uint8_t channel)
{
    terminalPrint("Testing channel " + String(channel) + "...");

    // Disable all channels first
    tca.disableAllChannels();
    delay(50);

    // Select the channel
    if (!tca.selectChannel(channel))
    {
        terminalPrint("  Failed to select channel " + String(channel));
        return false;
    }

    delay(100); // Let channel stabilize

    // Try to initialize the VCNL4040 sensor
    if (vcnl4040_sensors[channel].begin())
    {
        terminalPrint("  VCNL4040 found on channel " + String(channel) + "!");

        // Configure the sensor with optimal settings
        vcnl4040_sensors[channel].setProximityLEDCurrent(VCNL4040_LED_CURRENT_200MA);
        vcnl4040_sensors[channel].setProximityIntegrationTime(VCNL4040_PROXIMITY_INTEGRATION_TIME_8T);
        vcnl4040_sensors[channel].setAmbientIntegrationTime(VCNL4040_AMBIENT_INTEGRATION_TIME_160MS);

        // Test a reading
        uint16_t proximity = vcnl4040_sensors[channel].getProximity();
        uint16_t ambient = vcnl4040_sensors[channel].getLux();

        terminalPrint("  Test reading - P:" + String(proximity) + " A:" + String(ambient));

        return true;
    }
    else
    {
        terminalPrint("  No VCNL4040 on channel " + String(channel));
        return false;
    }
}

bool initializeSensors()
{
    terminalPrint("=== SENSOR INITIALIZATION ===");

    // Reset sensor tracking
    active_sensors = 0;
    for (int i = 0; i < 8; i++)
    {
        sensor_found[i] = false;
        sensorReadings[i].valid = false;
    }

    // Test channels where you expect sensors (3, 4, 5)
    int channels_to_test[] = {3, 4, 5, 0, 1, 2, 6, 7}; // Test expected channels first

    for (int i = 0; i < 8; i++)
    {
        int channel = channels_to_test[i];

        if (testSensorOnChannel(channel))
        {
            sensor_found[channel] = true;
            active_sensors++;
            terminalPrint("✓ Channel " + String(channel) + " active");
        }

        delay(100); // Small delay between tests
    }

    terminalPrint("Found " + String(active_sensors) + " active sensors");

    if (active_sensors > 0)
    {
        terminalPrint("=== INITIALIZATION COMPLETE ===");
        return true;
    }
    else
    {
        terminalPrint("=== NO SENSORS FOUND ===");
        terminalPrint("Check connections and power");
        return false;
    }
}

void readAllSensors()
{
    for (int ch = 0; ch < 8; ch++)
    {
        if (sensor_found[ch])
        {
            // Select the channel
            tca.disableAllChannels();
            delay(10);

            if (tca.selectChannel(ch))
            {
                delay(20); // Small delay for channel switching

                try
                {
                    sensorReadings[ch].proximity = vcnl4040_sensors[ch].getProximity();
                    sensorReadings[ch].ambient = vcnl4040_sensors[ch].getLux();
                    sensorReadings[ch].white = vcnl4040_sensors[ch].getWhiteLight();
                    sensorReadings[ch].valid = true;

                    // Print to serial for debugging
                    Serial.printf("Ch%d: P=%d A=%d W=%d\n", ch,
                                  sensorReadings[ch].proximity,
                                  sensorReadings[ch].ambient,
                                  sensorReadings[ch].white);
                }
                catch (...)
                {
                    sensorReadings[ch].valid = false;
                    Serial.printf("Ch%d: Read error\n", ch);
                }
            }
            else
            {
                sensorReadings[ch].valid = false;
            }
        }
    }
}

void showError(String message)
{
    terminalPrint("ERROR: " + message);
}

void setup()
{
    // Start serial early
    Serial.begin(115200);
    delay(2000); // Give time for serial monitor

    Serial.println("\n=== Motion Play - Multi-Sensor Setup ===");
    Serial.println("Build: " + String(BUILD_INFO));

    // Initialize power and pins
    pinMode(PIN_POWER_ON, OUTPUT);
    pinMode(PIN_LCD_BL, OUTPUT);
    pinMode(PIN_BUTTON_1, INPUT_PULLUP);
    pinMode(PIN_BUTTON_2, INPUT_PULLUP);
    digitalWrite(PIN_POWER_ON, HIGH);
    digitalWrite(PIN_LCD_BL, HIGH);

    delay(100);

    // Initialize display
    tdisplay.init();
    tdisplay.setRotation(1);
    tdisplay.fillScreen(TFT_BLACK);
    sprite.createSprite(320, 170);

    // Start terminal mode
    allLogLines.clear();
    terminalMode = true;

    terminalPrint("=== Motion Play Multi-Sensor ===");
    terminalPrint("Build: " + String(BUILD_INFO));
    terminalPrint("Initializing...");

    // Initialize I2C
    terminalPrint("I2C: SDA=" + String(PIN_IIC_SDA) + " SCL=" + String(PIN_IIC_SCL));
    Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);
    Wire.setClock(400000); // Use 400kHz for better performance
    delay(100);

    // Initialize TCA9548A
    terminalPrint("Initializing TCA9548A...");
    if (!tca.begin())
    {
        showError("TCA9548A not found!");
        terminalPrint("Check I2C connections");
        while (1)
        {
            handleButtons();
            delay(100);
        }
    }
    terminalPrint("TCA9548A OK");

    // Initialize sensors
    bool sensorsOK = initializeSensors();

    if (sensorsOK)
    {
        terminalPrint("Switching to sensor display...");
        delay(2000);
        terminalMode = false;
        initComplete = true;
    }
    else
    {
        terminalPrint("No sensors found. Check connections.");
        terminalPrint("Use BTN1+BTN2 to reset");
        // Stay in terminal mode for debugging
    }
}

void loop()
{
    static unsigned long lastUpdate = 0;
    static unsigned long lastSensorRead = 0;

    // Always handle buttons
    handleButtons();

    if (initComplete && !terminalMode)
    {
        // Read sensors every 100ms
        if (millis() - lastSensorRead >= 100)
        {
            readAllSensors();
            lastSensorRead = millis();
        }

        // Update display every 200ms
        if (millis() - lastUpdate >= 200)
        {
            updateSensorDisplay();
            lastUpdate = millis();
        }
    }
    else
    {
        // In terminal mode, just handle buttons and small delay
        delay(50);
    }
}

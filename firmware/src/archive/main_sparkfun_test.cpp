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
Adafruit_VCNL4040 vcnl4040;

// Build information
const char *BUILD_INFO = __DATE__ " " __TIME__;

// Terminal display system
#define MAX_DISPLAY_LINES 12
#define TERMINAL_FONT 2
#define LINE_HEIGHT 14
#include <vector>
std::vector<String> allLogLines;

void updateTerminalDisplay(); // Forward declaration

void terminalPrint(String message)
{
    Serial.println(message);
    allLogLines.push_back(message);
    updateTerminalDisplay();
}

void updateTerminalDisplay()
{
    sprite.fillSprite(TFT_BLACK);
    sprite.setTextColor(TFT_WHITE);
    sprite.setTextDatum(TL_DATUM);

    // Show build info at top
    sprite.setTextColor(TFT_DARKGREY);
    String buildDate = String(__DATE__).substring(0, 6) + " " + String(__TIME__).substring(0, 5);
    sprite.drawString("SparkFun VCNL4040 Test", 5, 2, 1);
    sprite.drawString(buildDate, 5, 12, 1);

    // Show terminal output
    sprite.setTextColor(TFT_WHITE);
    int maxLines = min((int)allLogLines.size(), MAX_DISPLAY_LINES);
    int startLine = max(0, (int)allLogLines.size() - MAX_DISPLAY_LINES);

    for (int i = 0; i < maxLines; i++)
    {
        String line = allLogLines[startLine + i];
        if (line.length() > 38)
        {
            line = line.substring(0, 35) + "...";
        }
        sprite.drawString(line, 5, 25 + (i * LINE_HEIGHT), TERMINAL_FONT);
    }

    sprite.pushSprite(0, 0);
}

void setup()
{
    Serial.begin(115200);
    delay(1000);

    // Initialize display
    tdisplay.init();
    tdisplay.setRotation(1);
    sprite.createSprite(320, 170);
    sprite.fillSprite(TFT_BLACK);
    sprite.setTextColor(TFT_WHITE);
    sprite.pushSprite(0, 0);

    terminalPrint("=== SparkFun VCNL4040 Test ===");
    terminalPrint("Build: " + String(BUILD_INFO));
    terminalPrint("Testing Channel 5 only");
    delay(2000);

    // Initialize I2C
    terminalPrint("Initializing I2C...");
    terminalPrint("SDA=" + String(SDA) + " SCL=" + String(SCL));
    Wire.begin(SDA, SCL, 100000); // 100kHz
    delay(100);

    // Test TCA9548A
    terminalPrint("=== TCA9548A Test ===");
    if (tca.begin())
    {
        terminalPrint("TCA9548A: OK");

        // Disable all channels first
        tca.disableAllChannels();
        delay(100);

        // Test channel 5
        terminalPrint("=== Channel 5 Test ===");
        if (tca.selectChannel(5))
        {
            terminalPrint("Ch5 selected: OK");
            delay(100); // Let channel stabilize

            // Scan for devices on channel 5
            terminalPrint("Scanning Ch5...");
            bool deviceFound = false;

            for (uint8_t addr = 0x08; addr <= 0x77; addr++)
            {
                Wire.beginTransmission(addr);
                uint8_t error = Wire.endTransmission();

                if (error == 0)
                {
                    terminalPrint("Found: 0x" + String(addr, HEX));
                    deviceFound = true;
                }
            }

            if (!deviceFound)
            {
                terminalPrint("No devices found on Ch5");
            }

            // Test VCNL4040 specifically
            terminalPrint("=== VCNL4040 Test ===");
            terminalPrint("Testing 0x60 (VCNL4040)...");

            Wire.beginTransmission(0x60);
            uint8_t vcnl_ping = Wire.endTransmission();
            terminalPrint("0x60 ping result: " + String(vcnl_ping));

            if (vcnl_ping == 0)
            {
                terminalPrint("VCNL4040 detected!");

                // Try Adafruit library initialization
                terminalPrint("Adafruit lib init...");
                if (vcnl4040.begin())
                {
                    terminalPrint("Adafruit VCNL4040: OK!");

                    // Configure sensor
                    vcnl4040.setProximityLEDCurrent(VCNL4040_LED_CURRENT_200MA);
                    vcnl4040.setProximityLEDDutyCycle(VCNL4040_LED_DUTY_1_40);
                    vcnl4040.setAmbientIntegrationTime(VCNL4040_AMBIENT_INTEGRATION_TIME_80MS);

                    terminalPrint("Sensor configured");
                    terminalPrint("Starting readings...");
                }
                else
                {
                    terminalPrint("Adafruit init: FAILED");
                }
            }
            else
            {
                terminalPrint("VCNL4040 not responding");
            }
        }
        else
        {
            terminalPrint("Ch5 select: FAILED");
        }
    }
    else
    {
        terminalPrint("TCA9548A: FAILED");
    }

    terminalPrint("=== Setup Complete ===");
}

void loop()
{
    // If sensor is initialized, take readings
    if (tca.selectChannel(5))
    {
        delay(10);

        // Check if we have a working sensor
        Wire.beginTransmission(0x60);
        if (Wire.endTransmission() == 0)
        {
            // Try to get readings
            uint16_t proximity = vcnl4040.getProximity();
            uint16_t ambient = vcnl4040.getAmbientLight();
            uint16_t white = vcnl4040.getWhiteLight();

            // Update display with readings
            sprite.fillSprite(TFT_BLACK);
            sprite.setTextColor(TFT_WHITE);
            sprite.setTextDatum(TL_DATUM);

            sprite.drawString("SparkFun VCNL4040 - Ch5", 5, 5, 2);
            sprite.drawString("Proximity: " + String(proximity), 5, 30, 2);
            sprite.drawString("Ambient: " + String(ambient), 5, 50, 2);
            sprite.drawString("White: " + String(white), 5, 70, 2);

            // Show status
            sprite.setTextColor(TFT_GREEN);
            sprite.drawString("SENSOR WORKING!", 5, 100, 2);

            sprite.pushSprite(0, 0);

            // Also print to serial
            Serial.println("Prox:" + String(proximity) + " Amb:" + String(ambient) + " White:" + String(white));
        }
        else
        {
            // Sensor not responding
            sprite.fillSprite(TFT_BLACK);
            sprite.setTextColor(TFT_RED);
            sprite.drawString("No sensor detected", 5, 50, 2);
            sprite.pushSprite(0, 0);
        }

        tca.disableAllChannels();
    }

    delay(500); // Update every 500ms
}

#include <Arduino.h>
#include <TFT_eSPI.h>
#include <Wire.h>
#include <vector>
#include "pin_config.h"

// Display setup
TFT_eSPI tdisplay = TFT_eSPI();
TFT_eSprite sprite = TFT_eSprite(&tdisplay);

// Build information
const char *BUILD_INFO = __DATE__ " " __TIME__;

// Terminal display system
#define MAX_DISPLAY_LINES 12
#define TERMINAL_FONT 2
#define LINE_HEIGHT 14
std::vector<String> allLogLines;

// TCA9548A and VCNL4040 addresses
#define MUX_ADDR 0x70
#define VCNL4040_ADDR 0x60
#define VCNL4040_CHANNEL 5

void terminalPrint(String message)
{
    Serial.println(message);
    allLogLines.push_back(message);

    sprite.fillSprite(TFT_BLACK);
    sprite.setTextColor(TFT_WHITE);
    sprite.setTextDatum(TL_DATUM);

    int totalLines = allLogLines.size();
    int startLine = max(0, totalLines - MAX_DISPLAY_LINES);

    for (int i = 0; i < MAX_DISPLAY_LINES && (startLine + i) < totalLines; i++)
    {
        int lineNumber = startLine + i + 1;
        String displayText = String(lineNumber) + ": " + allLogLines[startLine + i];
        if (displayText.length() > 38)
        {
            displayText = displayText.substring(0, 35) + "...";
        }
        sprite.drawString(displayText, 2, i * LINE_HEIGHT + 2, TERMINAL_FONT);
    }

    sprite.pushSprite(0, 0);
    delay(100); // Allow reading
}

// Test raw I2C communication
bool testI2CDevice(uint8_t addr, String deviceName)
{
    Wire.beginTransmission(addr);
    uint8_t error = Wire.endTransmission();

    String result = deviceName + " (0x" + String(addr, HEX) + "): ";
    if (error == 0)
    {
        result += "RESPONDS";
        terminalPrint(result);
        return true;
    }
    else
    {
        result += "NO RESPONSE (err=" + String(error) + ")";
        terminalPrint(result);
        return false;
    }
}

// Test TCA9548A channel selection
bool testTCAChannel(uint8_t channel)
{
    terminalPrint("Testing TCA channel " + String(channel) + "...");

    // Select channel
    Wire.beginTransmission(MUX_ADDR);
    Wire.write(1 << channel);
    uint8_t selectError = Wire.endTransmission();

    if (selectError != 0)
    {
        terminalPrint("Channel select FAILED (err=" + String(selectError) + ")");
        return false;
    }

    terminalPrint("Channel " + String(channel) + " selected");

    // Test if VCNL4040 responds on this channel
    bool vcnlFound = testI2CDevice(VCNL4040_ADDR, "VCNL4040 on Ch" + String(channel));

    // Disable channel
    Wire.beginTransmission(MUX_ADDR);
    Wire.write(0x00);
    Wire.endTransmission();

    return vcnlFound;
}

// Read VCNL4040 device ID register
uint16_t readVCNL4040ID()
{
    // Select channel 5
    Wire.beginTransmission(MUX_ADDR);
    Wire.write(1 << VCNL4040_CHANNEL);
    if (Wire.endTransmission() != 0)
    {
        terminalPrint("Failed to select channel for ID read");
        return 0xFFFF;
    }

    delay(10);

    // Read device ID register (0x0C)
    Wire.beginTransmission(VCNL4040_ADDR);
    Wire.write(0x0C); // ID register
    if (Wire.endTransmission() != 0)
    {
        terminalPrint("Failed to write ID register address");
        Wire.beginTransmission(MUX_ADDR);
        Wire.write(0x00); // Disable channel
        Wire.endTransmission();
        return 0xFFFF;
    }

    Wire.requestFrom(VCNL4040_ADDR, (uint8_t)2);
    if (Wire.available() < 2)
    {
        terminalPrint("Failed to read ID register data");
        Wire.beginTransmission(MUX_ADDR);
        Wire.write(0x00); // Disable channel
        Wire.endTransmission();
        return 0xFFFF;
    }

    uint8_t lowByte = Wire.read();
    uint8_t highByte = Wire.read();
    uint16_t deviceID = (highByte << 8) | lowByte;

    // Disable channel
    Wire.beginTransmission(MUX_ADDR);
    Wire.write(0x00);
    Wire.endTransmission();

    return deviceID;
}

void setup()
{
    Serial.begin(115200);
    delay(1000);

    // Initialize display power
    pinMode(PIN_POWER_ON, OUTPUT);
    digitalWrite(PIN_POWER_ON, HIGH);

    // Initialize display
    tdisplay.init();
    tdisplay.setRotation(1);
    sprite.createSprite(320, 170);
    sprite.fillSprite(TFT_BLACK);
    sprite.pushSprite(0, 0);

    terminalPrint("=== POWER & I2C DEBUG ===");
    terminalPrint("Build: " + String(BUILD_INFO));
    delay(1000);

    // Initialize I2C
    terminalPrint("Initializing I2C...");
    Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);
    Wire.setClock(100000); // 100kHz
    delay(100);

    terminalPrint("=== DEVICE SCAN (No MUX) ===");

    // First, scan without using the multiplexer
    int deviceCount = 0;
    for (uint8_t addr = 0x08; addr < 0x78; addr++)
    {
        Wire.beginTransmission(addr);
        uint8_t error = Wire.endTransmission();

        if (error == 0)
        {
            deviceCount++;
            String device = "Direct: 0x" + String(addr, HEX);
            if (addr == 0x70)
                device += " (TCA9548A)";
            if (addr == 0x60)
                device += " (VCNL4040?)";
            terminalPrint(device);
        }

        if (addr % 16 == 0)
        {
            delay(10);
            yield();
        }
    }

    terminalPrint("Direct devices found: " + String(deviceCount));
    delay(2000);

    // Test TCA9548A specifically
    terminalPrint("=== TCA9548A TESTS ===");
    bool tcaFound = testI2CDevice(MUX_ADDR, "TCA9548A");

    if (tcaFound)
    {
        // Test all channels
        terminalPrint("=== CHANNEL TESTS ===");
        for (uint8_t ch = 0; ch < 8; ch++)
        {
            bool vcnlOnChannel = testTCAChannel(ch);
            if (vcnlOnChannel)
            {
                terminalPrint("*** VCNL4040 found on channel " + String(ch) + " ***");
            }
            delay(500);
        }

        // Test device ID read on channel 5
        terminalPrint("=== DEVICE ID TEST ===");
        uint16_t deviceID = readVCNL4040ID();
        if (deviceID != 0xFFFF)
        {
            terminalPrint("Device ID: 0x" + String(deviceID, HEX));
            if (deviceID == 0x0186)
            {
                terminalPrint("*** CORRECT VCNL4040 ID! ***");
            }
            else
            {
                terminalPrint("*** WRONG ID (expected 0x0186) ***");
            }
        }
        else
        {
            terminalPrint("*** FAILED TO READ DEVICE ID ***");
        }
    }

    terminalPrint("=== DIAGNOSIS COMPLETE ===");
    terminalPrint("Check sensor power now!");
    terminalPrint("Expected: 3.3V, LED on");
}

void loop()
{
    delay(1000);

    // Continuously test basic communication
    static unsigned long lastTest = 0;
    if (millis() - lastTest > 5000)
    {
        lastTest = millis();

        // Quick TCA test
        Wire.beginTransmission(MUX_ADDR);
        uint8_t tcaError = Wire.endTransmission();

        Serial.println("Loop test - TCA: " + String(tcaError == 0 ? "OK" : "FAIL"));

        // Quick channel 5 + VCNL test
        Wire.beginTransmission(MUX_ADDR);
        Wire.write(1 << VCNL4040_CHANNEL);
        Wire.endTransmission();

        delay(10);

        Wire.beginTransmission(VCNL4040_ADDR);
        uint8_t vcnlError = Wire.endTransmission();

        Wire.beginTransmission(MUX_ADDR);
        Wire.write(0x00);
        Wire.endTransmission();

        Serial.println("Loop test - VCNL on Ch5: " + String(vcnlError == 0 ? "OK" : "FAIL"));
    }
}

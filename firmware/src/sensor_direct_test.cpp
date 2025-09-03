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
std::vector<String> allLogLines; // Store all log lines
bool terminalMode = true;
int displayStartLine = 0;
bool testComplete = false;

// VCNL4040 Register definitions
#define VCNL4040_ADDRESS 0x60
#define VCNL4040_ALS_CONF 0x00
#define VCNL4040_ALS_THDH 0x01
#define VCNL4040_ALS_THDL 0x02
#define VCNL4040_PS_CONF1 0x03
#define VCNL4040_PS_CONF2 0x04
#define VCNL4040_PS_CONF3 0x05
#define VCNL4040_PS_MS 0x06
#define VCNL4040_PS_THDL 0x07
#define VCNL4040_PS_THDH 0x08
#define VCNL4040_PS_DATA 0x08
#define VCNL4040_ALS_DATA 0x09
#define VCNL4040_WHITE_DATA 0x0A
#define VCNL4040_INT_FLAG 0x0B
#define VCNL4040_ID 0x0C

// Sensor state
bool sensorInitialized = false;
unsigned long lastSensorRead = 0;

// Function declarations
void terminalPrint(String message);
void updateTerminalDisplay();
void updateTerminalDisplayWithOffset();
void handleButtons();
void testI2CBus();
bool testVCNL4040();
uint16_t readVCNL4040Register(uint8_t reg);
bool writeVCNL4040Register(uint8_t reg, uint16_t value);
void runSensorTests();
void showSensorReadings();

void terminalPrint(String message)
{
    // Print to serial as well
    Serial.println(message);

    // Add to unlimited log storage
    allLogLines.push_back(message);

    if (terminalMode)
    {
        updateTerminalDisplay();
    }
}

void updateTerminalDisplay()
{
    if (testComplete)
    {
        updateTerminalDisplayWithOffset();
    }
    else
    {
        sprite.fillSprite(TFT_BLACK);
        sprite.setTextColor(TFT_WHITE);
        sprite.setTextDatum(TL_DATUM); // Top-left alignment

        // During diagnostic, auto-scroll to show latest lines
        int totalLines = allLogLines.size();
        int startLine = max(0, totalLines - MAX_DISPLAY_LINES);

        // Display the most recent lines with line numbers
        for (int i = 0; i < MAX_DISPLAY_LINES && (startLine + i) < totalLines; i++)
        {
            int lineNumber = startLine + i + 1; // 1-based line numbers
            String displayText = String(lineNumber) + ": " + allLogLines[startLine + i];
            sprite.drawString(displayText, 2, i * LINE_HEIGHT + 2, TERMINAL_FONT);
        }

        sprite.pushSprite(0, 0);
    }
}

void updateTerminalDisplayWithOffset()
{
    sprite.fillSprite(TFT_BLACK);
    sprite.setTextColor(TFT_WHITE);
    sprite.setTextDatum(TL_DATUM);

    // Add build date in top-right corner
    sprite.setTextDatum(TR_DATUM);
    sprite.setTextColor(TFT_DARKGREY);
    String buildDate = String(__DATE__).substring(0, 6) + " " + String(__TIME__).substring(0, 5);
    buildDate.replace("  ", " ");
    sprite.drawString(buildDate, 318, 2, 1);

    // Add total log line counter in bottom-right corner
    sprite.setTextDatum(BR_DATUM);
    sprite.setTextColor(TFT_DARKGREY);
    String logInfo = String(allLogLines.size()) + " Lines";
    sprite.drawString(logInfo, 318, 168, 1);

    sprite.setTextDatum(TL_DATUM);
    sprite.setTextColor(TFT_WHITE);

    // Display lines starting from displayStartLine with line numbers
    int totalLines = allLogLines.size();
    for (int i = 0; i < MAX_DISPLAY_LINES; i++)
    {
        int lineIndex = displayStartLine + i;
        if (lineIndex < totalLines)
        {
            int lineNumber = lineIndex + 1; // 1-based line numbers
            String displayText = String(lineNumber) + ": " + allLogLines[lineIndex];
            sprite.drawString(displayText, 2, i * LINE_HEIGHT + 2, TERMINAL_FONT);
        }
    }

    sprite.pushSprite(0, 0);
}

void handleButtons()
{
    static bool bothPressed = false;
    static unsigned long bothPressedStart = 0;
    static bool lastBtn1State = HIGH;
    static bool lastBtn2State = HIGH;
    static unsigned long btn1PressStart = 0;
    static unsigned long btn2PressStart = 0;
    static bool btn1LongPressHandled = false;
    static bool btn2LongPressHandled = false;

    unsigned long now = millis();
    bool btn1Down = digitalRead(PIN_BUTTON_1) == LOW;
    bool btn2Down = digitalRead(PIN_BUTTON_2) == LOW;

    const unsigned long PRESS_DEBOUNCE = 50;    // 50ms debounce
    const unsigned long LONG_PRESS_TIME = 500;  // 500ms for long press
    const unsigned long RESET_HOLD_TIME = 2000; // 2 seconds for reset
    int totalLines = allLogLines.size();

    // Check for simultaneous press and hold for reset
    if (btn1Down && btn2Down)
    {
        if (!bothPressed)
        {
            bothPressed = true;
            bothPressedStart = now;
            // Show reset message
            sprite.fillSprite(TFT_BLACK);
            sprite.setTextColor(TFT_RED);
            sprite.setTextDatum(MC_DATUM);
            sprite.drawString("Hold for Reset...", 160, 85, 4);
            sprite.pushSprite(0, 0);
        }
        else if (now - bothPressedStart >= RESET_HOLD_TIME)
        {
            // Show resetting message
            sprite.fillSprite(TFT_BLACK);
            sprite.setTextColor(TFT_RED);
            sprite.setTextDatum(MC_DATUM);
            sprite.drawString("Resetting...", 160, 85, 4);
            sprite.pushSprite(0, 0);
            delay(500);
            ESP.restart(); // Software reset
        }
        return; // Don't process other button actions while both pressed
    }
    else if (bothPressed)
    {
        // Both buttons released before reset time
        bothPressed = false;
        updateTerminalDisplayWithOffset(); // Restore display
    }

    // Button 1 (UP) handling
    if (btn1Down && !lastBtn1State)
    {
        // Button just pressed
        btn1PressStart = now;
        btn1LongPressHandled = false;
    }
    else if (btn1Down && lastBtn1State)
    {
        // Button held down
        if (!btn1LongPressHandled && (now - btn1PressStart >= LONG_PRESS_TIME))
        {
            // Long press - jump to very top
            displayStartLine = 0;
            updateTerminalDisplayWithOffset();

            // Flash screen briefly for feedback
            sprite.fillSprite(TFT_BLUE);
            sprite.pushSprite(0, 0);
            delay(100);
            updateTerminalDisplayWithOffset();

            btn1LongPressHandled = true;
        }
    }
    else if (!btn1Down && lastBtn1State)
    {
        // Button just released
        if (!btn1LongPressHandled && (now - btn1PressStart >= PRESS_DEBOUNCE))
        {
            // Short press - scroll up one line
            if (displayStartLine > 0)
            {
                displayStartLine--;
                updateTerminalDisplayWithOffset();
            }
        }
    }

    // Button 2 (DOWN) handling
    if (btn2Down && !lastBtn2State)
    {
        // Button just pressed
        btn2PressStart = now;
        btn2LongPressHandled = false;
    }
    else if (btn2Down && lastBtn2State)
    {
        // Button held down
        if (!btn2LongPressHandled && (now - btn2PressStart >= LONG_PRESS_TIME))
        {
            // Long press - jump to very bottom
            displayStartLine = max(0, totalLines - MAX_DISPLAY_LINES);
            updateTerminalDisplayWithOffset();

            // Flash screen briefly for feedback
            sprite.fillSprite(TFT_GREEN);
            sprite.pushSprite(0, 0);
            delay(100);
            updateTerminalDisplayWithOffset();

            btn2LongPressHandled = true;
        }
    }
    else if (!btn2Down && lastBtn2State)
    {
        // Button just released
        if (!btn2LongPressHandled && (now - btn2PressStart >= PRESS_DEBOUNCE))
        {
            // Short press - scroll down one line
            int maxStartLine = max(0, totalLines - MAX_DISPLAY_LINES);
            if (displayStartLine < maxStartLine)
            {
                displayStartLine++;
                updateTerminalDisplayWithOffset();
            }
        }
    }

    // Update previous button states
    lastBtn1State = btn1Down;
    lastBtn2State = btn2Down;
}

void testI2CBus()
{
    terminalPrint("=== I2C BUS TEST ===");

    // Test different I2C speeds
    uint32_t speeds[] = {100000, 400000}; // 100kHz, 400kHz
    String speedNames[] = {"100kHz", "400kHz"};

    for (int s = 0; s < 2; s++)
    {
        terminalPrint("Testing at " + speedNames[s] + "...");
        Wire.setClock(speeds[s]);
        delay(100);

        // Scan for devices
        int deviceCount = 0;
        String foundDevices = "";

        for (uint8_t addr = 0x08; addr < 0x78; addr++)
        {
            Wire.beginTransmission(addr);
            Wire.setTimeout(100);
            uint8_t error = Wire.endTransmission();

            if (error == 0)
            {
                deviceCount++;
                if (foundDevices.length() > 0)
                    foundDevices += ", ";
                foundDevices += "0x" + String(addr, HEX);

                if (addr == 0x60)
                {
                    terminalPrint("Found device at 0x60 (VCNL4040?)");
                }
            }

            if (addr % 16 == 0)
            {
                delay(5);
                yield();
            }
        }

        terminalPrint(speedNames[s] + ": " + String(deviceCount) + " device(s)");
        if (deviceCount > 0)
        {
            terminalPrint("Addresses: " + foundDevices);
        }
    }

    // Set back to 100kHz for testing
    Wire.setClock(100000);
    terminalPrint("=== END I2C BUS TEST ===");
}

uint16_t readVCNL4040Register(uint8_t reg)
{
    Wire.beginTransmission(VCNL4040_ADDRESS);
    Wire.write(reg);
    uint8_t error = Wire.endTransmission(false);

    if (error != 0)
    {
        return 0xFFFF; // Error indicator
    }

    Wire.requestFrom((uint8_t)VCNL4040_ADDRESS, (uint8_t)2);
    delay(10); // Give time for response

    if (Wire.available() >= 2)
    {
        uint8_t lsb = Wire.read();
        uint8_t msb = Wire.read();
        return (msb << 8) | lsb;
    }

    return 0xFFFF; // No data available
}

bool writeVCNL4040Register(uint8_t reg, uint16_t value)
{
    Wire.beginTransmission(VCNL4040_ADDRESS);
    Wire.write(reg);
    Wire.write(value & 0xFF);        // LSB first
    Wire.write((value >> 8) & 0xFF); // MSB second
    return Wire.endTransmission() == 0;
}

bool testVCNL4040()
{
    terminalPrint("=== VCNL4040 DIRECT TEST ===");

    // Test basic communication
    terminalPrint("Testing communication at 0x60...");
    Wire.beginTransmission(VCNL4040_ADDRESS);
    Wire.setTimeout(200);
    uint8_t error = Wire.endTransmission();

    terminalPrint("Communication test: " + String(error == 0 ? "OK" : "FAILED"));

    if (error != 0)
    {
        terminalPrint("Error code: " + String(error));
        terminalPrint("1=Data too long, 2=NACK addr, 3=NACK data, 4=Other");
        return false;
    }

    // Read device ID
    terminalPrint("Reading device ID register...");
    uint16_t deviceID = readVCNL4040Register(VCNL4040_ID);

    terminalPrint("Device ID: 0x" + String(deviceID, HEX));

    if (deviceID == 0xFFFF)
    {
        terminalPrint("Failed to read device ID");
        return false;
    }
    else if (deviceID == 0x0000)
    {
        terminalPrint("Device ID is 0x0000 (possible power issue)");
        return false;
    }
    else if (deviceID == 0x0186)
    {
        terminalPrint("VCNL4040 CONFIRMED! ID matches expected value");
    }
    else
    {
        terminalPrint("Unexpected device ID (expected 0x0186)");
        terminalPrint("Device may still work, continuing tests...");
    }

    return true;
}

void runSensorTests()
{
    terminalPrint("=== SENSOR CONFIGURATION TEST ===");

    // Configure proximity sensor
    terminalPrint("Configuring proximity sensor...");
    bool psConf1 = writeVCNL4040Register(VCNL4040_PS_CONF1, 0x0000); // Default settings
    bool psConf2 = writeVCNL4040Register(VCNL4040_PS_CONF2, 0x0000);
    bool psConf3 = writeVCNL4040Register(VCNL4040_PS_CONF3, 0x0000);

    terminalPrint("PS_CONF1: " + String(psConf1 ? "OK" : "FAILED"));
    terminalPrint("PS_CONF2: " + String(psConf2 ? "OK" : "FAILED"));
    terminalPrint("PS_CONF3: " + String(psConf3 ? "OK" : "FAILED"));

    // Configure ambient light sensor
    terminalPrint("Configuring ALS...");
    bool alsConf = writeVCNL4040Register(VCNL4040_ALS_CONF, 0x0000); // Default settings
    terminalPrint("ALS_CONF: " + String(alsConf ? "OK" : "FAILED"));

    // Wait for sensors to stabilize
    terminalPrint("Waiting for sensors to stabilize...");
    delay(1000);

    // Test reading all registers
    terminalPrint("=== REGISTER DUMP ===");
    String regNames[] = {"ALS_CONF", "ALS_THDH", "ALS_THDL", "PS_CONF1",
                         "PS_CONF2", "PS_CONF3", "PS_MS", "PS_THDL",
                         "PS_THDH", "PS_DATA", "ALS_DATA", "WHITE_DATA",
                         "INT_FLAG", "ID"};

    for (int i = 0; i < 14; i++)
    {
        uint16_t value = readVCNL4040Register(i);
        terminalPrint(regNames[i] + " (0x" + String(i, HEX) + "): 0x" + String(value, HEX));
    }

    terminalPrint("=== LIVE SENSOR READINGS ===");
    terminalPrint("Starting continuous readings...");
    terminalPrint("Use buttons to scroll through logs");

    sensorInitialized = true;
}

void showSensorReadings()
{
    if (!sensorInitialized)
        return;

    // Clear screen and show live readings
    sprite.fillSprite(TFT_BLACK);
    sprite.setTextColor(TFT_WHITE);
    sprite.setTextDatum(MC_DATUM);

    // Title
    sprite.drawString("VCNL4040 Direct Test", 160, 20, 2);

    // Build info
    sprite.setTextColor(TFT_DARKGREY);
    sprite.drawString("Build: " + String(__DATE__).substring(0, 6), 160, 40, 1);

    sprite.setTextColor(TFT_WHITE);

    // Read sensor values
    uint16_t proximity = readVCNL4040Register(VCNL4040_PS_DATA);
    uint16_t ambient = readVCNL4040Register(VCNL4040_ALS_DATA);
    uint16_t white = readVCNL4040Register(VCNL4040_WHITE_DATA);
    uint16_t intFlag = readVCNL4040Register(VCNL4040_INT_FLAG);

    // Display readings
    sprite.drawString("Proximity:", 160, 70, 2);
    sprite.setTextColor(TFT_CYAN);
    sprite.drawString(String(proximity), 160, 90, 4);

    sprite.setTextColor(TFT_WHITE);
    sprite.drawString("Ambient Light:", 160, 120, 2);
    sprite.setTextColor(TFT_YELLOW);
    sprite.drawString(String(ambient), 160, 140, 4);

    // Show additional info at bottom
    sprite.setTextColor(TFT_DARKGREY);
    sprite.setTextDatum(BL_DATUM);
    sprite.drawString("White: " + String(white), 10, 165, 1);
    sprite.setTextDatum(BR_DATUM);
    sprite.drawString("Int: 0x" + String(intFlag, HEX), 310, 165, 1);

    sprite.pushSprite(0, 0);

    // Print to serial for logging
    Serial.printf("Prox: %d, ALS: %d, White: %d, Int: 0x%X\n", proximity, ambient, white, intFlag);
}

void setup()
{
    // Start with a delay to ensure serial monitor is ready
    delay(2000);

    // Initialize serial
    Serial.begin(115200);
    Serial.flush();
    delay(100);

    // Send startup message to serial
    Serial.println("\n\n=== VCNL4040 Direct Test ===");
    Serial.println("Build: " + String(BUILD_INFO));
    Serial.println("Testing sensor PCB directly");
    Serial.println("============================\n");

    // Initialize power and display
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

    // Clear terminal logs and start terminal mode
    allLogLines.clear();
    displayStartLine = 0;
    terminalMode = true;

    // Show initial messages
    terminalPrint("=== VCNL4040 Direct Test ===");
    terminalPrint("Build: " + String(BUILD_INFO));
    terminalPrint("Testing sensor PCB directly");
    terminalPrint("");

    // Wiring instructions
    terminalPrint("WIRING INSTRUCTIONS:");
    terminalPrint("T-Display-S3 -> Sensor PCB");
    terminalPrint("Pin 43 (SDA) -> J3 Pin 2 (SDA)");
    terminalPrint("Pin 44 (SCL) -> J3 Pin 1 (SCL)");
    terminalPrint("3.3V -> J1 Pin 1 (3.3V)");
    terminalPrint("GND -> J1 Pin 2 (GND)");
    terminalPrint("INT not connected for this test");
    terminalPrint("");

    // Power stabilization delay
    terminalPrint("Power stabilizing...");
    delay(500);

    // Initialize I2C
    terminalPrint("I2C: SDA=43, SCL=44");
    Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);
    Wire.setClock(100000); // Start with 100kHz
    delay(100);

    // Run I2C bus test
    testI2CBus();

    // Test VCNL4040 specifically
    bool vcnlFound = testVCNL4040();

    if (vcnlFound)
    {
        // Run comprehensive sensor tests
        runSensorTests();

        // Switch to live readings mode after a delay
        delay(3000);
        terminalMode = false;
    }
    else
    {
        terminalPrint("");
        terminalPrint("VCNL4040 not detected!");
        terminalPrint("Check wiring and power connections");
        terminalPrint("Use BTN1/BTN2 to scroll logs");
        terminalPrint("Both buttons = reset device");
        testComplete = true;
        displayStartLine = max(0, (int)allLogLines.size() - MAX_DISPLAY_LINES);
        updateTerminalDisplayWithOffset();
    }
}

void loop()
{
    // Handle button input for log navigation
    handleButtons();

    if (terminalMode && testComplete)
    {
        // Just handle buttons for log scrolling
        delay(50);
        return;
    }

    if (!terminalMode && sensorInitialized)
    {
        // Show live sensor readings
        if (millis() - lastSensorRead >= 100) // Update every 100ms
        {
            showSensorReadings();
            lastSensorRead = millis();
        }
    }

    delay(10);
}

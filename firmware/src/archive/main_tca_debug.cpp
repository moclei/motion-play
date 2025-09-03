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

// Build information
const char *BUILD_INFO = __DATE__ " " __TIME__;

// Terminal display system
#define MAX_DISPLAY_LINES 12
#define TERMINAL_FONT 2
#define LINE_HEIGHT 14
#include <vector>
std::vector<String> allLogLines;

void updateTerminalDisplay(); // Forward declaration

void terminalPrint(String message) {
    Serial.println(message);
    allLogLines.push_back(message);
    updateTerminalDisplay();
}

void updateTerminalDisplay() {
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
    int startLine = max(0, totalLines - (MAX_DISPLAY_LINES - 1));

    for (int i = 0; i < (MAX_DISPLAY_LINES - 1) && (startLine + i) < totalLines; i++) {
        int lineNumber = startLine + i + 1;
        String displayText = String(lineNumber) + ": " + allLogLines[startLine + i];
        sprite.drawString(displayText, 2, (i + 1) * LINE_HEIGHT + 2, TERMINAL_FONT);
    }

    sprite.pushSprite(0, 0);
}

void scanI2CDevices(String context) {
    terminalPrint(context + " I2C scan:");
    
    int deviceCount = 0;
    for (uint8_t addr = 0x08; addr < 0x78; addr++) {
        Wire.beginTransmission(addr);
        Wire.setTimeout(100);
        uint8_t error = Wire.endTransmission();
        
        if (error == 0) {
            deviceCount++;
            String deviceInfo = "  0x" + String(addr, HEX);
            if (addr == 0x70) deviceInfo += " (TCA9548A)";
            if (addr == 0x60) deviceInfo += " (VCNL4040?)";
            terminalPrint(deviceInfo);
        }
        
        if (addr % 16 == 0) {
            delay(5);
            yield();
        }
    }
    
    if (deviceCount == 0) {
        terminalPrint("  No devices found");
    } else {
        terminalPrint("  Total: " + String(deviceCount) + " devices");
    }
}

// Direct TCA9548A control functions
void tcaSelect(uint8_t channel) {
    if (channel > 7) return;
    
    Wire.beginTransmission(0x70);
    Wire.write(1 << channel);
    uint8_t error = Wire.endTransmission();
    terminalPrint("TCA select ch" + String(channel) + " result: " + String(error));
    delay(50); // Give time for channel to stabilize
}

void tcaDisable() {
    Wire.beginTransmission(0x70);
    Wire.write(0x00);
    uint8_t error = Wire.endTransmission();
    terminalPrint("TCA disable result: " + String(error));
    delay(50);
}

uint8_t tcaRead() {
    Wire.requestFrom((uint8_t)0x70, (uint8_t)1);
    if (Wire.available()) {
        uint8_t value = Wire.read();
        terminalPrint("TCA current state: 0x" + String(value, HEX));
        return value;
    } else {
        terminalPrint("TCA read failed - no data");
        return 0xFF;
    }
}

void testTCAChannelSwitching() {
    terminalPrint("=== TCA9548A CHANNEL SWITCHING TEST ===");
    
    // First disable all channels
    terminalPrint("Disabling all channels...");
    tcaDisable();
    tcaRead();
    scanI2CDevices("Main bus (all disabled)");
    
    // Test each channel individually
    for (uint8_t ch = 0; ch < 8; ch++) {
        terminalPrint("--- Testing Channel " + String(ch) + " ---");
        
        // Select the channel
        tcaSelect(ch);
        tcaRead();
        
        // Scan for devices on this channel
        scanI2CDevices("Ch" + String(ch));
        
        // Disable channel again
        tcaDisable();
        delay(100);
    }
    
    terminalPrint("=== TCA SWITCHING TEST COMPLETE ===");
}

void testPowerConnections() {
    terminalPrint("=== POWER CONNECTION TEST ===");
    
    // Test if we can see any activity when channels are enabled
    for (uint8_t ch = 3; ch <= 5; ch++) {  // Focus on channels 3, 4, 5
        terminalPrint("Testing power on channel " + String(ch));
        
        tcaSelect(ch);
        delay(100);
        
        // Try different common I2C addresses
        uint8_t test_addresses[] = {0x60, 0x61, 0x62, 0x63, 0x48, 0x49, 0x4A, 0x4B};
        bool found_device = false;
        
        for (uint8_t addr : test_addresses) {
            Wire.beginTransmission(addr);
            Wire.setTimeout(200);
            uint8_t error = Wire.endTransmission();
            
            if (error == 0) {
                terminalPrint("  Device responds at 0x" + String(addr, HEX));
                found_device = true;
            }
        }
        
        if (!found_device) {
            terminalPrint("  No devices respond on ch" + String(ch));
            terminalPrint("  Check power and connections");
        }
        
        tcaDisable();
    }
}

void testVCNL4040Direct() {
    terminalPrint("=== DIRECT VCNL4040 TEST ===");
    
    for (uint8_t ch = 3; ch <= 5; ch++) {
        terminalPrint("Testing VCNL4040 on channel " + String(ch));
        
        tcaSelect(ch);
        delay(100);
        
        // Test basic communication at 0x60
        Wire.beginTransmission(0x60);
        Wire.setTimeout(200);
        uint8_t error = Wire.endTransmission();
        
        terminalPrint("  0x60 ping: " + String(error));
        
        if (error == 0) {
            // Try to read device ID
            Wire.beginTransmission(0x60);
            Wire.write(0x0C); // ID register
            error = Wire.endTransmission(false);
            
            if (error == 0) {
                Wire.requestFrom((uint8_t)0x60, (uint8_t)2);
                delay(50);
                
                if (Wire.available() >= 2) {
                    uint8_t lsb = Wire.read();
                    uint8_t msb = Wire.read();
                    uint16_t id = (msb << 8) | lsb;
                    
                    terminalPrint("  Device ID: 0x" + String(id, HEX));
                    
                    if (id == 0x0186) {
                        terminalPrint("  *** VCNL4040 FOUND! ***");
                    }
                } else {
                    terminalPrint("  No ID data available");
                }
            } else {
                terminalPrint("  ID register write failed");
            }
        }
        
        tcaDisable();
    }
}

void setup() {
    Serial.begin(115200);
    delay(2000);
    
    Serial.println("\n=== Motion Play - TCA9548A Debug ===");
    
    // Initialize hardware
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
    
    allLogLines.clear();
    
    terminalPrint("=== TCA9548A DEBUG MODE ===");
    terminalPrint("Build: " + String(BUILD_INFO));
    
    // Initialize I2C
    terminalPrint("Initializing I2C...");
    terminalPrint("SDA=" + String(PIN_IIC_SDA) + " SCL=" + String(PIN_IIC_SCL));
    Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);
    Wire.setClock(100000); // Slow speed for debugging
    delay(100);
    
    // Test basic TCA9548A communication
    terminalPrint("=== BASIC TCA9548A TEST ===");
    Wire.beginTransmission(0x70);
    uint8_t error = Wire.endTransmission();
    terminalPrint("TCA9548A ping: " + String(error));
    
    if (error != 0) {
        terminalPrint("TCA9548A not found! Check connections.");
        while(1) delay(1000);
    }
    
    // Read initial state
    tcaRead();
    
    // Test channel switching
    testTCAChannelSwitching();
    
    // Test power connections
    testPowerConnections();
    
    // Test VCNL4040 directly
    testVCNL4040Direct();
    
    terminalPrint("=== ALL TESTS COMPLETE ===");
    terminalPrint("Check results above");
}

void loop() {
    // Check buttons for reset
    static bool bothPressed = false;
    static unsigned long bothPressedStart = 0;
    
    bool btn1 = digitalRead(PIN_BUTTON_1) == LOW;
    bool btn2 = digitalRead(PIN_BUTTON_2) == LOW;
    
    if (btn1 && btn2) {
        if (!bothPressed) {
            bothPressed = true;
            bothPressedStart = millis();
            terminalPrint("Hold to reset...");
        } else if (millis() - bothPressedStart > 2000) {
            terminalPrint("Resetting...");
            delay(500);
            ESP.restart();
        }
    } else {
        bothPressed = false;
    }
    
    delay(100);
}

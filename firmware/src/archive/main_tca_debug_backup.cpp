#include <Arduino.h>
#include <TFT_eSPI.h>
#include <Wire.h>
#include <Adafruit_VCNL4040.h>
#include "pin_config.h"
#include "components/tca9548a/TCA9548A.h"

// Display setup
TFT_eSPI tdisplay = TFT_eSPI();
TFT_eSprite sprite = TFT_eSprite(&tdisplay);

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

void tcaSelect(uint8_t channel) {
    Wire.beginTransmission(0x70);
    Wire.write(1 << channel);
    Wire.endTransmission();
    delay(50);
}

void tcaDisable() {
    Wire.beginTransmission(0x70);
    Wire.write(0x00);
    Wire.endTransmission();
    delay(50);
}

bool testVCNL4040OnChannel(uint8_t channel) {
    tcaSelect(channel);
    
    // Test VCNL4040 at all possible addresses
    uint8_t vcnl_addresses[] = {0x60, 0x61, 0x62, 0x63};
    
    for (uint8_t addr : vcnl_addresses) {
        Wire.beginTransmission(addr);
        Wire.setTimeout(200);
        uint8_t error = Wire.endTransmission();
        
        if (error == 0) {
            terminalPrint("Ch" + String(channel) + ": Device at 0x" + String(addr, HEX));
            
            // Try to read device ID
            Wire.beginTransmission(addr);
            Wire.write(0x0C); // ID register
            error = Wire.endTransmission(false);
            
            if (error == 0) {
                Wire.requestFrom(addr, (uint8_t)2);
                delay(50);
                
                if (Wire.available() >= 2) {
                    uint8_t lsb = Wire.read();
                    uint8_t msb = Wire.read();
                    uint16_t id = (msb << 8) | lsb;
                    
                    terminalPrint("Ch" + String(channel) + ": ID=0x" + String(id, HEX));
                    
                    if (id == 0x0186) {
                        terminalPrint("*** VCNL4040 FOUND ON CHANNEL " + String(channel) + "! ***");
                        tcaDisable();
                        return true;
                    }
                }
            }
        }
    }
    
    tcaDisable();
    return false;
}

void fullChannelScan() {
    terminalPrint("=== FULL CHANNEL SCAN FOR VCNL4040 ===");
    
    bool foundAny = false;
    
    for (uint8_t ch = 0; ch < 8; ch++) {
        terminalPrint("Scanning channel " + String(ch) + "...");
        
        if (testVCNL4040OnChannel(ch)) {
            foundAny = true;
        } else {
            terminalPrint("Ch" + String(ch) + ": No VCNL4040 found");
        }
        
        delay(100);
    }
    
    if (!foundAny) {
        terminalPrint("=== NO VCNL4040 SENSORS FOUND ===");
        terminalPrint("This indicates a hardware issue:");
        terminalPrint("1. Check sensor PCB power (3.3V)");
        terminalPrint("2. Check I2C connections (SDA/SCL)");
        terminalPrint("3. Check JST connector wiring");
        terminalPrint("4. Verify sensor PCB assembly");
    }
}

void testAdafruitLibraryOnAllChannels() {
    terminalPrint("=== TESTING ADAFRUIT LIBRARY ===");
    
    for (uint8_t ch = 0; ch < 8; ch++) {
        terminalPrint("Testing Adafruit lib on ch" + String(ch));
        
        tcaSelect(ch);
        
        Adafruit_VCNL4040 vcnl;
        if (vcnl.begin()) {
            terminalPrint("*** ADAFRUIT SUCCESS ON CH" + String(ch) + "! ***");
            
            // Test reading
            uint16_t proximity = vcnl.getProximity();
            uint16_t ambient = vcnl.getLux();
            terminalPrint("Ch" + String(ch) + " readings: P=" + String(proximity) + " A=" + String(ambient));
        }
        
        tcaDisable();
        delay(100);
    }
}

void setup() {
    Serial.begin(115200);
    delay(2000);
    
    Serial.println("\n=== Motion Play - Full Sensor Scan ===");
    
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
    
    terminalPrint("=== FULL SENSOR SCAN ===");
    terminalPrint("Build: " + String(BUILD_INFO));
    
    // Initialize I2C
    terminalPrint("Initializing I2C...");
    Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);
    Wire.setClock(100000);
    delay(100);
    
    // Test TCA9548A
    Wire.beginTransmission(0x70);
    if (Wire.endTransmission() != 0) {
        terminalPrint("TCA9548A not found!");
        while(1) delay(1000);
    }
    terminalPrint("TCA9548A OK");
    
    // Scan all channels for VCNL4040
    fullChannelScan();
    
    // Test Adafruit library on all channels
    testAdafruitLibraryOnAllChannels();
    
    terminalPrint("=== SCAN COMPLETE ===");
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

#include <Arduino.h>
#include <Wire.h>

// ============================================================================
// PIN CONFIGURATION for ESP32-S3-DevKitC-1
// ============================================================================
#define PIN_SDA 21 // I2C SDA for ESP32-S3-DevKitC-1
#define PIN_SCL 20 // I2C SCL for ESP32-S3-DevKitC-1

// VCNL4040 I2C ADDRESS
#define VCNL4040_ADDR 0x60
#define VCNL4040_ID_REG 0x0C

// ============================================================================
// ENHANCED I2C DIAGNOSTIC FUNCTIONS
// ============================================================================

void printI2CError(uint8_t error)
{
    Serial.printf("I2C Error %d: ", error);
    switch (error)
    {
    case 0:
        Serial.println("Success");
        break;
    case 1:
        Serial.println("Data too long for buffer");
        break;
    case 2:
        Serial.println("NACK on transmit of address");
        break;
    case 3:
        Serial.println("NACK on transmit of data");
        break;
    case 4:
        Serial.println("Other error");
        break;
    case 5:
        Serial.println("Timeout");
        break;
    default:
        Serial.println("Unknown error");
        break;
    }
}

void testI2CPins()
{
    Serial.println("\n=== I2C Pin Test ===");

    // Test if pins can be set as outputs and read back
    pinMode(PIN_SDA, OUTPUT);
    digitalWrite(PIN_SDA, HIGH);
    delay(1);
    pinMode(PIN_SDA, INPUT_PULLUP);
    bool sda_high = digitalRead(PIN_SDA);

    pinMode(PIN_SCL, OUTPUT);
    digitalWrite(PIN_SCL, HIGH);
    delay(1);
    pinMode(PIN_SCL, INPUT_PULLUP);
    bool scl_high = digitalRead(PIN_SCL);

    Serial.printf("SDA (GPIO %d) reads: %s\n", PIN_SDA, sda_high ? "HIGH" : "LOW");
    Serial.printf("SCL (GPIO %d) reads: %s\n", PIN_SCL, scl_high ? "HIGH" : "LOW");

    if (!sda_high || !scl_high)
    {
        Serial.println("⚠️  WARNING: One or both I2C lines are pulled LOW!");
        Serial.println("   This suggests missing pull-up resistors or a short circuit");
    }
    else
    {
        Serial.println("✅ Both I2C lines are pulled HIGH (good)");
    }
}

void comprehensiveI2CScan()
{
    Serial.println("\n=== Comprehensive I2C Scan ===");
    int deviceCount = 0;

    // Test different I2C speeds
    uint32_t speeds[] = {10000, 50000, 100000, 400000};
    const char *speedNames[] = {"10kHz", "50kHz", "100kHz", "400kHz"};

    for (int s = 0; s < 4; s++)
    {
        Serial.printf("\n--- Testing at %s ---\n", speedNames[s]);
        Wire.setClock(speeds[s]);

        for (uint8_t addr = 1; addr < 127; addr++)
        {
            Wire.beginTransmission(addr);
            Wire.setTimeout(500); // Longer timeout for slow speeds
            uint8_t error = Wire.endTransmission();

            if (error == 0)
            {
                Serial.printf("0x%02X: FOUND", addr);
                if (addr == 0x60)
                    Serial.print(" (VCNL4040)");
                Serial.println();
                deviceCount++;
            }
            else if (addr == 0x60)
            {
                // Special attention to VCNL4040 address
                Serial.printf("0x%02X: ", addr);
                printI2CError(error);
            }
        }
    }

    // Reset to 100kHz
    Wire.setClock(100000);
    Serial.printf("\nTotal devices found: %d\n", deviceCount);
}

bool testVCNL4040Communication()
{
    Serial.println("\n=== VCNL4040 Communication Test ===");

    // Test 1: Simple presence check
    Serial.println("Test 1: Basic presence check");
    Wire.beginTransmission(VCNL4040_ADDR);
    uint8_t error = Wire.endTransmission();
    Serial.printf("Basic transmission result: ");
    printI2CError(error);

    if (error != 0)
    {
        return false;
    }

    // Test 2: Try to read ID register
    Serial.println("Test 2: Reading ID register");
    Wire.beginTransmission(VCNL4040_ADDR);
    Wire.write(VCNL4040_ID_REG);
    error = Wire.endTransmission(false); // Don't release bus

    if (error != 0)
    {
        Serial.printf("Failed to write register address: ");
        printI2CError(error);
        return false;
    }

    // Request 2 bytes
    uint8_t bytesReceived = Wire.requestFrom((uint8_t)VCNL4040_ADDR, (uint8_t)2);
    Serial.printf("Requested 2 bytes, received: %d\n", bytesReceived);

    if (bytesReceived >= 2)
    {
        uint8_t lsb = Wire.read();
        uint8_t msb = Wire.read();
        uint16_t id = (msb << 8) | lsb;
        Serial.printf("Device ID: 0x%04X (expected: 0x0186)\n", id);
        return (id == 0x0186);
    }
    else
    {
        Serial.println("❌ Failed to read ID register");
        return false;
    }
}

void testAlternativePins()
{
    Serial.println("\n=== Testing Alternative I2C Pins ===");

    // ESP32-S3 alternative I2C pins
    uint8_t altPins[][2] = {
        {8, 9},   // Alternative set 1
        {17, 18}, // Alternative set 2
        {35, 36}, // Alternative set 3 (if available)
    };

    for (int i = 0; i < 3; i++)
    {
        Serial.printf("Testing SDA=%d, SCL=%d\n", altPins[i][0], altPins[i][1]);

        Wire.end(); // End current I2C
        Wire.setPins(altPins[i][0], altPins[i][1]);
        Wire.begin();
        Wire.setClock(100000);

        Wire.beginTransmission(VCNL4040_ADDR);
        uint8_t error = Wire.endTransmission();
        Serial.printf("  Result: ");
        printI2CError(error);

        if (error == 0)
        {
            Serial.printf("✅ VCNL4040 responds on SDA=%d, SCL=%d!\n", altPins[i][0], altPins[i][1]);
            return;
        }
    }

    // Restore original pins
    Wire.end();
    Wire.setPins(PIN_SDA, PIN_SCL);
    Wire.begin();
    Wire.setClock(100000);
}

// ============================================================================
// SETUP AND MAIN FUNCTIONS
// ============================================================================

void setup()
{
    Serial.begin(115200);
    delay(2000);

    Serial.println("\n\n=== I2C DIAGNOSTIC TOOL ===");
    Serial.printf("Target device: VCNL4040 at address 0x%02X\n", VCNL4040_ADDR);
    Serial.printf("Using pins: SDA=%d, SCL=%d\n", PIN_SDA, PIN_SCL);

    // Step 1: Test pin functionality
    testI2CPins();

    // Step 2: Initialize I2C
    Serial.println("\n--- Initializing I2C ---");
    Wire.setPins(PIN_SDA, PIN_SCL);
    Wire.begin();
    Wire.setClock(100000);
    Serial.println("I2C initialized at 100kHz");

    // Step 3: Comprehensive scan
    comprehensiveI2CScan();

    // Step 4: Specific VCNL4040 tests
    bool vcnlFound = testVCNL4040Communication();

    // Step 5: If not found, test alternative pins
    if (!vcnlFound)
    {
        testAlternativePins();
    }

    Serial.println("\n=== DIAGNOSTIC COMPLETE ===");
    Serial.println("Type 'help' for available commands");
}

void loop()
{
    if (Serial.available())
    {
        String command = Serial.readStringUntil('\n');
        command.trim();
        command.toLowerCase();

        if (command == "scan")
        {
            comprehensiveI2CScan();
        }
        else if (command == "pins")
        {
            testI2CPins();
        }
        else if (command == "vcnl")
        {
            testVCNL4040Communication();
        }
        else if (command == "alt")
        {
            testAlternativePins();
        }
        else if (command == "help")
        {
            Serial.println("\nAvailable commands:");
            Serial.println("  scan - Comprehensive I2C device scan");
            Serial.println("  pins - Test I2C pin functionality");
            Serial.println("  vcnl - Test VCNL4040 specific communication");
            Serial.println("  alt  - Test alternative pin configurations");
            Serial.println("  help - Show this help");
        }
        else
        {
            Serial.println("Unknown command. Type 'help' for available commands.");
        }
    }

    delay(100);
}

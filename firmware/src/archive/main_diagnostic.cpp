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
  sprite.drawString(buildDate, 2, 2, 1);

  sprite.setTextColor(TFT_WHITE);

  // Display the most recent lines
  int totalLines = allLogLines.size();
  int startLine = max(0, totalLines - (MAX_DISPLAY_LINES - 1));

  for (int i = 0; i < (MAX_DISPLAY_LINES - 1) && (startLine + i) < totalLines; i++)
  {
    int lineNumber = startLine + i + 1;
    String displayText = String(lineNumber) + ": " + allLogLines[startLine + i];
    sprite.drawString(displayText, 2, (i + 1) * LINE_HEIGHT + 2, TERMINAL_FONT);
  }

  sprite.pushSprite(0, 0);
}

void scanI2CDevices(uint8_t channel = 255)
{
  String prefix = (channel == 255) ? "Main" : "Ch" + String(channel);
  terminalPrint(prefix + " I2C scan:");

  int deviceCount = 0;
  for (uint8_t addr = 0x08; addr < 0x78; addr++)
  {
    Wire.beginTransmission(addr);
    Wire.setTimeout(100);
    uint8_t error = Wire.endTransmission();

    if (error == 0)
    {
      deviceCount++;
      String deviceInfo = "  0x" + String(addr, HEX);
      if (addr == 0x70)
        deviceInfo += " (TCA9548A)";
      if (addr == 0x60)
        deviceInfo += " (VCNL4040?)";
      terminalPrint(deviceInfo);
    }

    if (addr % 16 == 0)
    {
      delay(10);
      yield();
    }
  }

  if (deviceCount == 0)
  {
    terminalPrint("  No devices found");
  }
  else
  {
    terminalPrint("  Total: " + String(deviceCount) + " devices");
  }
}

bool testVCNL4040Direct(uint8_t address = 0x60)
{
  terminalPrint("Direct VCNL4040 test at 0x" + String(address, HEX));

  // Test basic communication
  Wire.beginTransmission(address);
  Wire.setTimeout(200);
  uint8_t error = Wire.endTransmission();

  terminalPrint("  Ping result: " + String(error));

  if (error != 0)
  {
    return false;
  }

  // Try to read device ID register (0x0C)
  Wire.beginTransmission(address);
  Wire.write(0x0C);                    // Device ID register
  error = Wire.endTransmission(false); // Keep connection alive

  if (error != 0)
  {
    terminalPrint("  ID register write failed: " + String(error));
    return false;
  }

  // Request 2 bytes
  uint8_t bytesReceived = Wire.requestFrom(address, (uint8_t)2);
  delay(50); // Give time for response

  terminalPrint("  Bytes available: " + String(Wire.available()));

  if (Wire.available() >= 2)
  {
    uint8_t lsb = Wire.read();
    uint8_t msb = Wire.read();
    uint16_t id = (msb << 8) | lsb;

    terminalPrint("  Device ID: 0x" + String(id, HEX) + " (LSB:0x" + String(lsb, HEX) + ", MSB:0x" + String(msb, HEX) + ")");

    if (id == 0x0186)
    {
      terminalPrint("  ✓ VCNL4040 CONFIRMED!");
      return true;
    }
    else if (id == 0x0000 || id == 0xFFFF)
    {
      terminalPrint("  ✗ Invalid ID (bus issue)");
    }
    else
    {
      terminalPrint("  ✗ Wrong ID (expected 0x0186)");
    }
  }
  else
  {
    terminalPrint("  ✗ No response data");
  }

  return false;
}

bool testAdafruitLibrary(uint8_t channel)
{
  terminalPrint("Testing Adafruit lib on Ch" + String(channel));

  // Create a new instance for each test to avoid Wire.begin() issues
  Adafruit_VCNL4040 vcnl;

  // Try to initialize without calling Wire.begin() again
  // We need to check if the sensor responds manually first
  if (testVCNL4040Direct())
  {
    terminalPrint("  Direct test passed, trying Adafruit init...");

    // The begin() function might still fail due to Wire.begin() conflicts
    // Let's try it anyway
    bool result = vcnl.begin();
    terminalPrint("  Adafruit begin(): " + String(result ? "SUCCESS" : "FAILED"));

    if (result)
    {
      // Try to get a reading
      uint16_t proximity = vcnl.getProximity();
      uint16_t ambient = vcnl.getLux();
      terminalPrint("  Test reading - P:" + String(proximity) + " A:" + String(ambient));
      return true;
    }
  }

  return false;
}

void testChannelDetailed(uint8_t channel)
{
  terminalPrint("=== DETAILED TEST CHANNEL " + String(channel) + " ===");

  // Disable all channels first
  tca.disableAllChannels();
  delay(50);

  // Select channel
  if (!tca.selectChannel(channel))
  {
    terminalPrint("Failed to select channel " + String(channel));
    return;
  }

  delay(100); // Channel stabilization

  // Scan for devices on this channel
  scanI2CDevices(channel);

  // Test VCNL4040 directly
  bool directTest = testVCNL4040Direct();

  // Test with Adafruit library
  if (directTest)
  {
    testAdafruitLibrary(channel);
  }

  terminalPrint("=== END CHANNEL " + String(channel) + " TEST ===");
}

void setup()
{
  Serial.begin(115200);
  delay(2000);

  Serial.println("\n=== Motion Play - Diagnostic Mode ===");

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

  terminalPrint("=== DIAGNOSTIC MODE ===");
  terminalPrint("Build: " + String(BUILD_INFO));

  // Initialize I2C
  terminalPrint("Initializing I2C...");
  terminalPrint("SDA=" + String(PIN_IIC_SDA) + " SCL=" + String(PIN_IIC_SCL));
  Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);
  Wire.setClock(100000); // Start slow for debugging
  delay(100);

  // Scan main I2C bus
  terminalPrint("=== MAIN BUS SCAN ===");
  scanI2CDevices();

  // Test TCA9548A
  terminalPrint("=== TCA9548A TEST ===");
  if (!tca.begin())
  {
    terminalPrint("TCA9548A initialization FAILED");
    terminalPrint("Check power and I2C connections");
    while (1)
      delay(1000);
  }
  else
  {
    terminalPrint("TCA9548A OK");
  }

  // Test your specific channels (3, 4, 5)
  terminalPrint("=== TESTING CHANNELS 3, 4, 5 ===");
  testChannelDetailed(3);
  delay(500);
  testChannelDetailed(4);
  delay(500);
  testChannelDetailed(5);

  terminalPrint("=== DIAGNOSTIC COMPLETE ===");
  terminalPrint("Check serial output for details");
}

void loop()
{
  // Check buttons for reset
  static bool bothPressed = false;
  static unsigned long bothPressedStart = 0;

  bool btn1 = digitalRead(PIN_BUTTON_1) == LOW;
  bool btn2 = digitalRead(PIN_BUTTON_2) == LOW;

  if (btn1 && btn2)
  {
    if (!bothPressed)
    {
      bothPressed = true;
      bothPressedStart = millis();
      terminalPrint("Hold to reset...");
    }
    else if (millis() - bothPressedStart > 2000)
    {
      terminalPrint("Resetting...");
      delay(500);
      ESP.restart();
    }
  }
  else
  {
    bothPressed = false;
  }

  delay(100);
}

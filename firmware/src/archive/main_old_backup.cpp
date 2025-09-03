#include <Arduino.h>
#include <TFT_eSPI.h>
#include <Wire.h>
#include <algorithm>
#include "pin_config.h"
#include "components/tca9548a/TCA9548A.h"
#include "components/vcnl4040/VCNL4040.h"

// Display setup
TFT_eSPI tdisplay = TFT_eSPI();
TFT_eSprite sprite = TFT_eSprite(&tdisplay);

// I2C components
TCA9548A tca;
VCNL4040 sensor;

// Build information
const char *BUILD_INFO = __DATE__ " " __TIME__;

// Terminal display system
#define MAX_DISPLAY_LINES 12
#define TERMINAL_FONT 2
#define LINE_HEIGHT 14
#include <vector>
std::vector<String> allLogLines; // Store all log lines (unlimited)
bool terminalMode = false;
int displayStartLine = 0; // Which line to start displaying from (0-based)
bool diagnosticComplete = false;

// Function declarations (prototypes)
void terminalPrint(String message);
void updateTerminalDisplay();
void updateTerminalDisplayWithOffset();
void handleButtons();
void scanI2C();
bool scanChannelForVCNL4040(uint8_t channel);
void testTCA9548AChannels();
int scanAllChannelsForVCNL4040();
void showError(String message);
void testChannel5Specifically();
void diagnoseI2CBus();

void diagnoseI2CBus()
{
  terminalPrint("=== I2C BUS DIAGNOSTICS ===");

  // Test I2C bus integrity
  terminalPrint("Testing I2C bus at 100kHz...");
  Wire.setClock(100000);
  delay(100);

  // Scan for all devices
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

      // Special identification for known devices
      if (addr == 0x70)
      {
        terminalPrint("Found TCA9548A at 0x70");
      }
      else if (addr == 0x60)
      {
        terminalPrint("Found device at 0x60 (possible VCNL4040)");
      }
    }

    if (addr % 16 == 0)
    {
      delay(10);
      yield();
    }
  }

  terminalPrint("Total devices found: " + String(deviceCount));
  if (deviceCount > 0)
  {
    terminalPrint("Addresses: " + foundDevices);
  }
  else
  {
    terminalPrint("No I2C devices detected!");
    terminalPrint("Check SDA/SCL connections and pull-ups");
  }

  // Test TCA9548A specifically
  if (deviceCount > 0)
  {
    terminalPrint("Testing TCA9548A communication...");
    Wire.beginTransmission(0x70);
    uint8_t tcaError = Wire.endTransmission();
    terminalPrint("TCA9548A response: " + String(tcaError == 0 ? "OK" : "FAILED"));

    if (tcaError == 0)
    {
      // Test channel selection
      terminalPrint("Testing channel selection...");
      Wire.beginTransmission(0x70);
      Wire.write(0x20); // Select channel 5 (bit 5 = 0x20)
      uint8_t selectError = Wire.endTransmission();
      terminalPrint("Channel 5 select: " + String(selectError == 0 ? "OK" : "FAILED"));

      // Disable all channels
      Wire.beginTransmission(0x70);
      Wire.write(0x00);
      Wire.endTransmission();
    }
  }

  terminalPrint("=== END I2C DIAGNOSTICS ===");
}

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
  if (diagnosticComplete)
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
    int startLine = std::max(0, totalLines - MAX_DISPLAY_LINES);

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

  // Add total log line counter in bottom-right corner (removed viewing window)
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
  if (!diagnosticComplete)
    return;

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
      displayStartLine = std::max(0, totalLines - MAX_DISPLAY_LINES);
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
      int maxStartLine = std::max(0, totalLines - MAX_DISPLAY_LINES);
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

void scanI2C()
{
  terminalPrint("Scanning I2C addresses...");
  byte error, address;
  int deviceCount = 0;

  for (address = 1; address < 127; address++)
  {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0)
    {
      terminalPrint("I2C: 0x" + String(address, HEX));
      deviceCount++;
    }
  }

  if (deviceCount == 0)
  {
    terminalPrint("No I2C devices found!");
  }
  else
  {
    terminalPrint("Found " + String(deviceCount) + " device(s)");
  }
}

bool scanChannelForVCNL4040(uint8_t channel)
{
  // First disable all channels to ensure clean slate
  tca.disableAllChannels();
  delay(50); // Give time for channels to disable

  if (!tca.selectChannel(channel))
  {
    terminalPrint("Ch" + String(channel) + ": Failed to select");
    return false;
  }

  // Give time for channel to stabilize
  delay(100);

  terminalPrint("Ch" + String(channel) + ": Scanning...");

  // First, do a general scan to see what's there
  int deviceCount = 0;
  String foundAddresses = "";
  for (uint8_t addr = 1; addr < 127; addr++)
  {
    // Skip TCA9548A address - it should not be visible through channels
    if (addr == 0x70)
      continue;

    Wire.beginTransmission(addr);
    Wire.setTimeout(100); // Increased timeout
    if (Wire.endTransmission() == 0)
    {
      deviceCount++;
      if (foundAddresses.length() > 0)
        foundAddresses += ",";
      foundAddresses += "0x" + String(addr, HEX);

      // Add extra debugging for any found device
      terminalPrint("Ch" + String(channel) + ": Device found at 0x" + String(addr, HEX));
    }

    // Add timeout protection
    if (addr % 20 == 0)
    {
      delay(10);
      yield();
    }
  }

  if (deviceCount > 0)
  {
    terminalPrint("Ch" + String(channel) + ": Found " + String(deviceCount) + " device(s): " + foundAddresses);
  }
  else
  {
    terminalPrint("Ch" + String(channel) + ": No devices found");
    // Don't return false yet - still try VCNL4040 specific addresses
  }

  // Now specifically check VCNL4040 at 0x60 (default address)
  terminalPrint("Ch" + String(channel) + ": Testing VCNL4040 at 0x60...");

  Wire.beginTransmission(0x60);
  Wire.setTimeout(200); // Increased timeout
  byte error = Wire.endTransmission();

  terminalPrint("Ch" + String(channel) + ": 0x60 ping result: " + String(error));

  bool vcnlFound = false;
  if (error == 0)
  {
    terminalPrint("Ch" + String(channel) + ": Device responds at 0x60");

    // Try to read the device ID register (0x0C)
    Wire.beginTransmission(0x60);
    Wire.write(0x0C);                    // ID register
    Wire.setTimeout(200);                // Increased timeout
    error = Wire.endTransmission(false); // Keep connection alive

    terminalPrint("Ch" + String(channel) + ": ID register write result: " + String(error));

    if (error == 0)
    {
      Wire.requestFrom((uint8_t)0x60, (uint8_t)2);
      delay(50); // More time for response

      if (Wire.available() >= 2)
      {
        uint8_t lsb = Wire.read();
        uint8_t msb = Wire.read();
        uint16_t id = (msb << 8) | lsb;

        terminalPrint("Ch" + String(channel) + ": Read ID=0x" + String(id, HEX) + " (LSB:0x" + String(lsb, HEX) + ", MSB:0x" + String(msb, HEX) + ")");

        if (id == 0x0186)
        { // VCNL4040 device ID
          terminalPrint("Ch" + String(channel) + ": VCNL4040 CONFIRMED!");
          vcnlFound = true;
        }
        else if (id == 0x0000 || id == 0xFFFF)
        {
          terminalPrint("Ch" + String(channel) + ": Invalid ID (bus issue or no power)");
        }
        else
        {
          terminalPrint("Ch" + String(channel) + ": Wrong ID (expected 0x0186)");
        }
      }
      else
      {
        terminalPrint("Ch" + String(channel) + ": No ID response (available: " + String(Wire.available()) + ")");
        terminalPrint("Ch" + String(channel) + ": Possible power or timing issue");
      }
    }
    else
    {
      terminalPrint("Ch" + String(channel) + ": ID register write failed");
    }
  }
  else
  {
    terminalPrint("Ch" + String(channel) + ": No response at 0x60 (error: " + String(error) + ")");
  }

  if (!vcnlFound)
  {
    terminalPrint("Ch" + String(channel) + ": No VCNL4040 detected");
  }

  return vcnlFound;
}

void testTCA9548AChannels()
{
  terminalPrint("Testing TCA9548A channels...");

  for (uint8_t channel = 0; channel < 8; channel++)
  {
    if (tca.selectChannel(channel))
    {
      terminalPrint("Ch" + String(channel) + ": Selectable");

      // Quick I2C scan with timeout protection
      int deviceCount = 0;
      String foundAddresses = "";

      for (uint8_t addr = 1; addr < 127; addr++)
      {
        Wire.beginTransmission(addr);
        Wire.setTimeout(100); // 100ms timeout
        uint8_t error = Wire.endTransmission();

        if (error == 0)
        {
          deviceCount++;
          if (foundAddresses.length() > 0)
            foundAddresses += ",";
          foundAddresses += "0x" + String(addr, HEX);
        }

        // Add small delay and watchdog reset
        if (addr % 20 == 0)
        {
          delay(10);
          yield(); // Allow other tasks to run
        }
      }

      if (deviceCount > 0)
      {
        terminalPrint("Ch" + String(channel) + ": " + String(deviceCount) + " device(s) at " + foundAddresses);
      }
      else
      {
        terminalPrint("Ch" + String(channel) + ": No devices");
      }
    }
    else
    {
      terminalPrint("Ch" + String(channel) + ": Failed to select");
    }
    delay(100); // Longer delay between channels
  }
}

int scanAllChannelsForVCNL4040()
{
  terminalPrint("Scanning all channels...");

  for (uint8_t channel = 0; channel < 8; channel++)
  {
    if (scanChannelForVCNL4040(channel))
    {
      return channel; // Return first channel with VCNL4040
    }
    delay(100); // Brief delay between channels
  }

  return -1; // No VCNL4040 found on any channel
}

void showError(String message)
{
  terminalPrint("ERROR: " + message);
}

void testChannel5Specifically()
{
  terminalPrint("=== DETAILED CHANNEL 5 TEST ===");

  // Test TCA9548A basic communication first
  terminalPrint("Testing TCA9548A communication...");
  Wire.beginTransmission(0x70);
  uint8_t error = Wire.endTransmission();
  terminalPrint("TCA9548A ping result: " + String(error));

  if (error != 0)
  {
    terminalPrint("ERROR: TCA9548A not responding!");
    terminalPrint("Check power connections and I2C wiring");
    return;
  }

  // Disable all channels first
  terminalPrint("Disabling all channels...");
  tca.disableAllChannels();
  delay(100);

  // Test what's on main bus (should see TCA9548A)
  terminalPrint("Scanning main I2C bus...");
  Wire.beginTransmission(0x70);
  error = Wire.endTransmission();
  terminalPrint("Main bus - TCA9548A at 0x70: " + String(error == 0 ? "Found" : "Not found"));

  // Now test channel 5 selection
  terminalPrint("Selecting channel 5...");
  bool selected = tca.selectChannel(5);
  terminalPrint("Channel 5 selection: " + String(selected ? "SUCCESS" : "FAILED"));

  if (selected)
  {
    delay(100); // Let channel stabilize

    // Test if TCA9548A is still visible (it shouldn't be through channels)
    Wire.beginTransmission(0x70);
    error = Wire.endTransmission();
    terminalPrint("Ch5 - TCA9548A visibility: " + String(error == 0 ? "VISIBLE (BAD)" : "HIDDEN (GOOD)"));

    // Specifically test VCNL4040 addresses on channel 5
    terminalPrint("Testing VCNL4040 addresses on Ch5...");
    const uint8_t vcnlAddresses[] = {0x60, 0x61, 0x62, 0x63};

    for (uint8_t addr : vcnlAddresses)
    {
      Wire.beginTransmission(addr);
      Wire.setTimeout(200); // Longer timeout for this test
      error = Wire.endTransmission();
      terminalPrint("Ch5 - VCNL4040 at 0x" + String(addr, HEX) + ": " + String(error == 0 ? "RESPONDS" : "No response (" + String(error) + ")"));

      if (error == 0)
      {
        // Try to read device ID
        Wire.beginTransmission(addr);
        Wire.write(0x0C); // Device ID register
        error = Wire.endTransmission(false);

        if (error == 0)
        {
          Wire.requestFrom((uint8_t)addr, (uint8_t)2);
          delay(50); // More time for response

          if (Wire.available() >= 2)
          {
            uint8_t lsb = Wire.read();
            uint8_t msb = Wire.read();
            uint16_t id = (msb << 8) | lsb;

            terminalPrint("Ch5 - 0x" + String(addr, HEX) + " Device ID: 0x" + String(id, HEX));

            if (id == 0x0186)
            {
              terminalPrint("*** VCNL4040 FOUND ON CHANNEL 5! ***");
            }
          }
          else
          {
            terminalPrint("Ch5 - 0x" + String(addr, HEX) + " No ID data available");
          }
        }
        else
        {
          terminalPrint("Ch5 - 0x" + String(addr, HEX) + " ID register write failed: " + String(error));
        }
      }
    }
  }

  terminalPrint("=== END CHANNEL 5 TEST ===");
}

void setup()
{
  // Start with a delay to ensure serial monitor is ready
  delay(2000);

  // Initialize serial with explicit flush
  Serial.begin(115200);
  Serial.flush();
  delay(100);

  // Send a clear startup message to serial
  Serial.println("\n\n=== Motion Play Startup ===");
  Serial.println("Build: " + String(BUILD_INFO));
  Serial.println("===========================\n");

  // Initialize power and display BEFORE starting terminal mode
  pinMode(PIN_POWER_ON, OUTPUT);
  pinMode(PIN_LCD_BL, OUTPUT);
  pinMode(PIN_BUTTON_1, INPUT_PULLUP);
  pinMode(PIN_BUTTON_2, INPUT_PULLUP);
  digitalWrite(PIN_POWER_ON, HIGH);
  digitalWrite(PIN_LCD_BL, HIGH);

  delay(100); // Brief delay for power

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
  terminalPrint("=== Motion Play ===");
  terminalPrint("Build: " + String(BUILD_INFO));
  terminalPrint("Starting initialization...");

  // Power stabilization delay
  terminalPrint("Power stabilizing...");
  delay(500);

  // Initialize I2C
  terminalPrint("I2C: SDA=" + String(PIN_IIC_SDA) + " SCL=" + String(PIN_IIC_SCL));
  Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);
  Wire.setClock(100000); // Start with slower 100kHz for debugging
  delay(100);            // Allow I2C to stabilize

  // Run comprehensive I2C diagnostics first
  diagnoseI2CBus();

  // Initialize I2C multiplexer
  terminalPrint("Initializing TCA9548A...");
  if (!tca.begin())
  {
    showError("TCA9548A not found!");
    while (1)
      delay(1000);
  }

  terminalPrint("TCA9548A OK");

  // Test all TCA9548A channels
  // testTCA9548AChannels();  // Commented out to reduce logs

  // Specific test for channel 5 (where sensor should be)
  testChannel5Specifically(); // Temporarily commented out to see only init logs

  // Comprehensive scan for VCNL4040 on all channels
  // int vcnlChannel = scanAllChannelsForVCNL4040();  // Commented out to reduce logs

  // For now, just try to use channel 5 directly
  terminalPrint("Attempting to use Channel 5...");
  bool channel5HasVCNL = scanChannelForVCNL4040(5); // Temporarily commented out
  /// bool channel5HasVCNL = false; // Assume no sensor for now to see init sequence

  if (channel5HasVCNL)
  {
    terminalPrint("VCNL4040 confirmed on Ch5!");

    // Select the channel with VCNL4040 and initialize
    if (tca.selectChannel(5))
    {
      terminalPrint("Initializing VCNL4040...");
      if (sensor.begin())
      {
        terminalPrint("Setup complete!");
        delay(2000);
        terminalMode = false; // Switch to sensor mode
      }
      else
      {
        showError("VCNL4040 init failed!");
        while (1)
          delay(1000);
      }
    }
    else
    {
      showError("Failed to select Ch5");
      terminalPrint("Check connections...");
      terminalPrint("Use BTN1/BTN2 to scroll logs");
      diagnosticComplete = true;
      // Start viewing from the bottom of the logs
      displayStartLine = std::max(0, (int)allLogLines.size() - MAX_DISPLAY_LINES);
      updateTerminalDisplayWithOffset();
    }
  }
  else
  {
    terminalPrint("No VCNL4040 detected (detailed scan disabled)");
    terminalPrint("Initialization sequence complete");
    terminalPrint("Use BTN1/BTN2 to scroll logs");
    terminalPrint("Both buttons = reset device");
    diagnosticComplete = true;
    // Start viewing from the bottom of the logs
    displayStartLine = max(0, (int)allLogLines.size() - MAX_DISPLAY_LINES);
    updateTerminalDisplayWithOffset();
  }
}

void loop()
{
  static unsigned long lastUpdate = 0;

  // Handle button input for log navigation
  handleButtons();

  // If diagnostic is complete, don't run sensor loop
  if (diagnosticComplete)
  {
    delay(100);
    return;
  }

  // Update display every 100ms (only if sensor mode)
  if (millis() - lastUpdate >= 100)
  {
    // Read sensor data
    uint16_t proximity = sensor.readProximity();
    uint16_t ambient = sensor.readAmbientLight();

    // Update display
    sprite.fillSprite(TFT_BLACK);
    sprite.setTextColor(TFT_WHITE);

    // Display build info at top
    sprite.drawString("Build: " + String(BUILD_INFO), 160, 10, 2);

    // Display proximity
    sprite.drawString("Proximity:", 160, 50, 4);
    sprite.drawString(String(proximity), 160, 80, 4);

    // Display ambient light
    sprite.drawString("Ambient Light:", 160, 120, 4);
    sprite.drawString(String(ambient), 160, 150, 4);

    sprite.pushSprite(0, 0);

    // Print to serial for debugging
    Serial.printf("Proximity: %d, Ambient: %d\n", proximity, ambient);

    lastUpdate = millis();
  }
}

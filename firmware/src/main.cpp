#include <Arduino.h>
#include <TFT_eSPI.h>
#include <Wire.h>
#include <vector>
#include "pin_config.h"

// Include SparkFun VCNL4040 Library
#include "components/vcnl4040/VCNL4040.h"

// Display setup
TFT_eSPI tdisplay = TFT_eSPI();
TFT_eSprite sprite = TFT_eSprite(&tdisplay);

// I2C components
VCNL4040 proximitySensor;

// Build information
const char *BUILD_INFO = __DATE__ " " __TIME__;

// Terminal display system
#define MAX_DISPLAY_LINES 12
#define TERMINAL_FONT 2
#define LINE_HEIGHT 14
std::vector<String> allLogLines;
bool terminalMode = true;
int displayStartLine = 0;
bool diagnosticComplete = false;
bool sensorInitialized = false;

// TCA9548A Multiplexer
#define MUX_ADDR 0x70
#define VCNL4040_CHANNEL 5

// Sensor state
long startingProxValue = 0;
long deltaNeeded = 0;
bool calibrated = false;

// Function declarations
void terminalPrint(String message);
void updateTerminalDisplay();
void updateTerminalDisplayWithOffset();
void handleButtons();
boolean enableMuxPort(byte portNumber);
boolean disableMuxPort(byte portNumber);
void scanI2C();
void initializeSensor();
void takeSensorReadings();

// Enable power to external components
void enableExternalPower()
{
  pinMode(PIN_POWER_ON, OUTPUT);
  digitalWrite(PIN_POWER_ON, HIGH);
  terminalPrint("External power enabled");
  delay(100); // Allow power to stabilize
}

// TCA9548A control functions (based on SparkFun examples)
boolean enableMuxPort(byte portNumber)
{
  if (portNumber > 7)
    portNumber = 7;

  // Select only the specified channel (disable others)
  Wire.beginTransmission(MUX_ADDR);
  Wire.write(1 << portNumber);
  return (Wire.endTransmission() == 0);
}

boolean disableMuxPort(byte portNumber)
{
  // Disable all channels
  Wire.beginTransmission(MUX_ADDR);
  Wire.write(0);
  return (Wire.endTransmission() == 0);
}

void terminalPrint(String message)
{
  Serial.println(message);
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
    sprite.setTextDatum(TL_DATUM);

    // Auto-scroll to show latest lines during diagnostic
    int totalLines = allLogLines.size();
    int startLine = max(0, totalLines - MAX_DISPLAY_LINES);

    for (int i = 0; i < MAX_DISPLAY_LINES && (startLine + i) < totalLines; i++)
    {
      int lineNumber = startLine + i + 1;
      String displayText = String(lineNumber) + ": " + allLogLines[startLine + i];
      // Truncate long lines
      if (displayText.length() > 38)
      {
        displayText = displayText.substring(0, 35) + "...";
      }
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

  // Add log counter in bottom-right corner
  sprite.setTextDatum(BR_DATUM);
  sprite.setTextColor(TFT_DARKGREY);
  String logInfo = String(allLogLines.size()) + " Lines";
  sprite.drawString(logInfo, 318, 168, 1);

  sprite.setTextDatum(TL_DATUM);
  sprite.setTextColor(TFT_WHITE);

  // Display lines with navigation
  int totalLines = allLogLines.size();
  for (int i = 0; i < MAX_DISPLAY_LINES; i++)
  {
    int lineIndex = displayStartLine + i;
    if (lineIndex < totalLines)
    {
      int lineNumber = lineIndex + 1;
      String displayText = String(lineNumber) + ": " + allLogLines[lineIndex];
      if (displayText.length() > 38)
      {
        displayText = displayText.substring(0, 35) + "...";
      }
      sprite.drawString(displayText, 2, i * LINE_HEIGHT + 2, TERMINAL_FONT);
    }
  }

  sprite.pushSprite(0, 0);
}

void handleButtons()
{
  static unsigned long lastButtonPress = 0;
  unsigned long now = millis();

  if (now - lastButtonPress < 200)
    return; // Debounce

  if (digitalRead(PIN_BUTTON_1) == LOW)
  {
    // Scroll up
    if (displayStartLine > 0)
    {
      displayStartLine--;
      updateTerminalDisplayWithOffset();
    }
    lastButtonPress = now;
  }

  if (digitalRead(PIN_BUTTON_2) == LOW)
  {
    // Scroll down
    int maxStartLine = max(0, (int)allLogLines.size() - MAX_DISPLAY_LINES);
    if (displayStartLine < maxStartLine)
    {
      displayStartLine++;
      updateTerminalDisplayWithOffset();
    }
    lastButtonPress = now;
  }
}

void scanI2C()
{
  terminalPrint("=== I2C Device Scan ===");

  int deviceCount = 0;
  for (uint8_t addr = 0x08; addr < 0x78; addr++)
  {
    Wire.beginTransmission(addr);
    uint8_t error = Wire.endTransmission();

    if (error == 0)
    {
      deviceCount++;
      String device = "Found: 0x" + String(addr, HEX);
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

  terminalPrint("Total devices: " + String(deviceCount));
}

void initializeSensor()
{
  terminalPrint("=== Sensor Initialization ===");

  // Enable channel 5 on TCA9548A
  terminalPrint("Enabling TCA9548A channel 5...");
  if (enableMuxPort(VCNL4040_CHANNEL))
  {
    terminalPrint("Channel 5 enabled");
    delay(100); // Let channel stabilize

    // Try to initialize VCNL4040
    terminalPrint("Initializing VCNL4040...");
    if (proximitySensor.begin())
    {
      terminalPrint("VCNL4040 initialized successfully!");
      sensorInitialized = true;

      // Sensor is configured internally by the library
      terminalPrint("Sensor ready for readings...");

      // Calibrate baseline (like Example2)
      terminalPrint("Calibrating baseline...");
      startingProxValue = 0;
      for (byte x = 0; x < 8; x++)
      {
        startingProxValue += proximitySensor.readProximity();
        delay(10);
      }
      startingProxValue /= 8;

      deltaNeeded = (float)startingProxValue * 0.05; // 5% change threshold
      if (deltaNeeded < 5)
        deltaNeeded = 5; // Minimum threshold

      terminalPrint("Baseline: " + String(startingProxValue));
      terminalPrint("Threshold: " + String(deltaNeeded));
      calibrated = true;
    }
    else
    {
      terminalPrint("VCNL4040 init failed!");
      sensorInitialized = false;
    }
  }
  else
  {
    terminalPrint("Failed to enable channel 5");
  }

  disableMuxPort(VCNL4040_CHANNEL);
}

void takeSensorReadings()
{
  if (!sensorInitialized)
    return;

  // Enable sensor channel
  if (enableMuxPort(VCNL4040_CHANNEL))
  {
    delay(10); // Channel stabilization

    // Get readings
    unsigned int proxValue = proximitySensor.readProximity();
    unsigned int ambientValue = proximitySensor.readAmbientLight();

    // Update display with sensor readings
    sprite.fillSprite(TFT_BLACK);
    sprite.setTextColor(TFT_WHITE);
    sprite.setTextDatum(TL_DATUM);

    // Title
    sprite.drawString("VCNL4040 - Channel 5", 5, 5, 2);

    // Sensor values
    sprite.drawString("Proximity: " + String(proxValue), 5, 30, 2);
    sprite.drawString("Ambient: " + String(ambientValue), 5, 50, 2);
    sprite.drawString("Baseline: " + String(startingProxValue), 5, 70, 2);

    // Detection status (like SparkFun Example2)
    if (calibrated)
    {
      sprite.setTextColor(TFT_YELLOW);
      sprite.drawString("Detection Status:", 5, 100, 2);

      if (proxValue > (startingProxValue + deltaNeeded))
      {
        sprite.setTextColor(TFT_GREEN);
        sprite.drawString("SOMETHING IS THERE!", 5, 120, 2);
      }
      else
      {
        sprite.setTextColor(TFT_CYAN);
        sprite.drawString("Nothing detected", 5, 120, 2);
      }
    }

    // Status indicator
    sprite.setTextColor(TFT_GREEN);
    sprite.drawString("SENSOR ACTIVE", 5, 150, 1);

    sprite.pushSprite(0, 0);

    // Also print to serial
    Serial.println("Prox:" + String(proxValue) + " Amb:" + String(ambientValue) +
                   " Delta:" + String(proxValue - startingProxValue));
  }

  disableMuxPort(VCNL4040_CHANNEL);
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
  sprite.pushSprite(0, 0);

  // Initialize buttons
  pinMode(PIN_BUTTON_1, INPUT_PULLUP);
  pinMode(PIN_BUTTON_2, INPUT_PULLUP);

  terminalPrint("=== Motion Play VCNL4040 Test ===");
  terminalPrint("Build: " + String(BUILD_INFO));
  terminalPrint("Channel 5 Detection System");
  delay(1000);

  // CRITICAL: Enable external power first!
  enableExternalPower();
  delay(500); // Allow power to fully stabilize

  // Initialize I2C
  terminalPrint("Initializing I2C...");
  terminalPrint("SDA=" + String(PIN_IIC_SDA) + " SCL=" + String(PIN_IIC_SCL));
  Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);
  Wire.setClock(100000); // 100kHz for reliability
  delay(100);

  // Scan for devices
  scanI2C();
  delay(1000);

  // Initialize sensor
  initializeSensor();
  delay(1000);

  terminalPrint("=== Setup Complete ===");
  terminalPrint("Press BTN1/BTN2 to scroll logs");
  terminalPrint("Starting sensor readings...");

  diagnosticComplete = true;
  delay(2000);
}

void loop()
{
  static unsigned long lastReading = 0;
  static bool showingSensorData = false;
  unsigned long now = millis();

  // Handle button navigation
  handleButtons();

  // Toggle between terminal view and sensor data every 5 seconds
  if (now - lastReading > 5000)
  {
    lastReading = now;
    showingSensorData = !showingSensorData;

    if (showingSensorData && sensorInitialized)
    {
      terminalMode = false;
      takeSensorReadings();
    }
    else
    {
      terminalMode = true;
      updateTerminalDisplayWithOffset();
    }
  }

  delay(100);
}
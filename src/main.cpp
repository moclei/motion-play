#include <Arduino.h>
#include <TFT_eSPI.h>
#include <Wire.h>
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

void scanI2C()
{
  Serial.println("Scanning I2C addresses...");
  byte error, address;
  int deviceCount = 0;

  for (address = 1; address < 127; address++)
  {
    Wire.beginTransmission(address);
    error = Wire.endTransmission();

    if (error == 0)
    {
      Serial.printf("I2C device found at address 0x%02X\n", address);
      deviceCount++;
    }
  }

  if (deviceCount == 0)
  {
    Serial.println("No I2C devices found!");
  }
  else
  {
    Serial.printf("Found %d device(s)\n", deviceCount);
  }
}

void scanVCNL4040()
{
  Serial.println("Scanning for VCNL4040 at all possible addresses...");
  const uint8_t possibleAddresses[] = {0x60, 0x61, 0x62, 0x63};
  bool found = false;

  for (uint8_t addr : possibleAddresses)
  {
    Wire.beginTransmission(addr);
    byte error = Wire.endTransmission();

    if (error == 0)
    {
      Serial.printf("Found device at address 0x%02X - checking if it's a VCNL4040...\n", addr);

      // Try to read the device ID register
      Wire.beginTransmission(addr);
      Wire.write(0x0C); // ID register
      Wire.endTransmission(false);

      Wire.requestFrom(addr, (uint8_t)2);
      if (Wire.available() >= 2)
      {
        uint8_t lsb = Wire.read();
        uint8_t msb = Wire.read();
        uint16_t id = (msb << 8) | lsb;

        if (id == 0x0186)
        { // VCNL4040 device ID
          Serial.printf("Confirmed VCNL4040 at address 0x%02X!\n", addr);
          found = true;
          break;
        }
      }
    }
  }

  if (!found)
  {
    Serial.println("No VCNL4040 found at any address!");
  }
}

void showError(const char *message)
{
  sprite.fillSprite(TFT_BLACK);
  sprite.setTextColor(TFT_RED);
  sprite.drawString(message, 160, 85, 4);
  sprite.setTextColor(TFT_WHITE);
  sprite.drawString("Build: " + String(BUILD_INFO), 160, 120, 2);
  sprite.pushSprite(0, 0);
}

void setup()
{
  // Start with a delay to ensure serial monitor is ready
  delay(2000);

  // Initialize serial with explicit flush
  Serial.begin(115200);
  Serial.flush();
  delay(100);

  // Send a clear startup message
  Serial.println("\n\n=== Motion Play Startup ===");
  Serial.println("Build: " + String(BUILD_INFO));
  Serial.println("Serial connection test...");
  Serial.println("If you can see this, serial is working!");
  Serial.println("===========================\n");

  // Initialize power and display
  pinMode(PIN_POWER_ON, OUTPUT);
  pinMode(PIN_LCD_BL, OUTPUT);
  digitalWrite(PIN_POWER_ON, HIGH);
  digitalWrite(PIN_LCD_BL, HIGH);

  // Initialize display
  tdisplay.init();
  tdisplay.setRotation(1);
  tdisplay.fillScreen(TFT_BLACK);
  sprite.createSprite(320, 170);
  sprite.setTextDatum(MC_DATUM);

  // Show initial setup screen
  sprite.fillSprite(TFT_BLACK);
  sprite.setTextColor(TFT_WHITE);
  sprite.drawString("Motion Play", 160, 30, 4);
  sprite.drawString("Initializing...", 160, 70, 2);
  sprite.drawString("Build: " + String(BUILD_INFO), 160, 100, 2);
  sprite.pushSprite(0, 0);

  // Initialize I2C
  Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);
  Wire.setClock(400000); // Set to 400kHz

  Serial.println("Starting I2C scan...");
  // Scan I2C bus before initializing components
  scanI2C();

  // Initialize I2C multiplexer
  Serial.println("Initializing TCA9548A...");
  if (!tca.begin())
  {
    Serial.println("Failed to initialize TCA9548A!");
    showError("TCA9548A not found!");
    while (1)
      ;
  }

  Serial.println("TCA9548A initialized successfully");

  // Select channel 0 and initialize first sensor
  Serial.println("Selecting channel 0...");
  if (!tca.selectChannel(0))
  {
    Serial.println("Failed to select channel 0!");
    showError("Failed to select channel!");
    while (1)
      ;
  }

  Serial.println("Channel 0 selected, scanning for VCNL4040...");
  scanVCNL4040(); // Use our new thorough scanning function

  Serial.println("Initializing VCNL4040...");
  if (!sensor.begin())
  {
    Serial.println("Failed to initialize VCNL4040!");
    showError("VCNL4040 not found!");
    while (1)
      ;
  }

  Serial.println("Setup complete!");
}

void loop()
{
  static unsigned long lastUpdate = 0;

  // Update display every 100ms
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

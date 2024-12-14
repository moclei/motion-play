#include <Arduino.h>
#include <TFT_eSPI.h>
#include <Wire.h>
#include <Adafruit_ADS1X15.h>
#include "pin_config.h"

TFT_eSPI tft = TFT_eSPI();
TFT_eSprite sprite = TFT_eSprite(&tft);
Adafruit_ADS1015 ads;

// Constants
const int NUM_SENSORS = 3;
const int CALIBRATION_SAMPLES = 100;
const float TRIGGER_THRESHOLD = 2.0;        // Number of standard deviations for trigger
const unsigned long TRIGGER_TIMEOUT = 1000; // Time window for sequence detection (ms)
const unsigned long COOLDOWN_PERIOD = 500;  // Time to wait after a detection before allowing new ones (ms)
const int HISTORY_SIZE = 5;                 // Number of recent triggers to display

// Global cooldown tracking
unsigned long lastDetectionTime = 0;

// Sensor data structure
struct SensorData
{
  float baseline;
  float stdDev;
  float currentValue;
  bool isTriggered;
  unsigned long lastTriggerTime;
};

// Trigger sequence structure
struct TriggerEvent
{
  String sequence;
  unsigned long timestamp;
};

// Global variables
SensorData sensors[NUM_SENSORS];
TriggerEvent triggerHistory[HISTORY_SIZE];
int historyIndex = 0;
bool isCalibrating = true;
unsigned long calibrationStart = 0;
const unsigned long CALIBRATION_DURATION = 5000; // 5 seconds

void updateDisplay();
void checkTriggers();
void recordTriggerSequence(const String &sequence);
void calibrateSensors();

void setup()
{
  Serial.begin(115200);
  Serial.println("Starting Calibrated Detector");

  // Initialize power and display
  pinMode(PIN_POWER_ON, OUTPUT);
  pinMode(PIN_LCD_BL, OUTPUT);
  digitalWrite(PIN_POWER_ON, HIGH);
  digitalWrite(PIN_LCD_BL, HIGH);

  // Initialize display
  tft.init();
  tft.setRotation(1);
  tft.fillScreen(TFT_BLACK);

  sprite.createSprite(320, 170);
  sprite.setTextDatum(MC_DATUM);

  // Initialize I2C and ADS1015
  Wire.begin(PIN_IIC_SDA, PIN_IIC_SCL);

  if (!ads.begin())
  {
    Serial.println("Failed to initialize ADS.");
    sprite.fillSprite(TFT_BLACK);
    sprite.setTextColor(TFT_RED);
    sprite.drawString("ADS1015 not found!", 160, 85, 4);
    sprite.pushSprite(0, 0);
    while (1)
      ; // Halt if ADS not found
  }

  // Configure ADS
  ads.setGain(GAIN_ONE);
  ads.setDataRate(RATE_ADS1015_1600SPS);

  // Initialize sensor data
  for (int i = 0; i < NUM_SENSORS; i++)
  {
    sensors[i] = {0, 0, 0, false, 0};
  }

  // Initialize trigger history
  for (int i = 0; i < HISTORY_SIZE; i++)
  {
    triggerHistory[i] = {"", 0};
  }

  calibrationStart = millis();
  Serial.println("Starting calibration...");
}

void loop()
{
  static unsigned long lastUpdate = 0;

  // Read current values
  for (int i = 0; i < NUM_SENSORS; i++)
  {
    sensors[i].currentValue = ads.readADC_SingleEnded(i);
  }

  if (isCalibrating)
  {
    // Display calibration progress
    sprite.fillSprite(TFT_BLACK);
    sprite.setTextColor(TFT_YELLOW);
    int progress = ((millis() - calibrationStart) * 100) / CALIBRATION_DURATION;
    sprite.drawString("Calibrating: " + String(progress) + "%", 160, 85, 4);
    sprite.pushSprite(0, 0);

    // Check if calibration period is complete
    if (millis() - calibrationStart >= CALIBRATION_DURATION)
    {
      calibrateSensors();
      isCalibrating = false;
      Serial.println("Calibration complete!");
    }
  }
  else
  {
    // Normal operation
    if (millis() - lastUpdate >= 100)
    { // Update 10 times per second
      checkTriggers();
      updateDisplay();
      lastUpdate = millis();
    }
  }
}

void calibrateSensors()
{
  // Arrays to store calibration samples
  float samples[NUM_SENSORS][CALIBRATION_SAMPLES];

  // Collect samples
  for (int i = 0; i < CALIBRATION_SAMPLES; i++)
  {
    for (int j = 0; j < NUM_SENSORS; j++)
    {
      samples[j][i] = ads.readADC_SingleEnded(j);
    }
    delay(10);
  }

  // Calculate baseline and standard deviation for each sensor
  for (int i = 0; i < NUM_SENSORS; i++)
  {
    // Calculate mean
    float sum = 0;
    for (int j = 0; j < CALIBRATION_SAMPLES; j++)
    {
      sum += samples[i][j];
    }
    sensors[i].baseline = sum / CALIBRATION_SAMPLES;

    // Calculate standard deviation
    float sumSquares = 0;
    for (int j = 0; j < CALIBRATION_SAMPLES; j++)
    {
      float diff = samples[i][j] - sensors[i].baseline;
      sumSquares += diff * diff;
    }
    sensors[i].stdDev = sqrt(sumSquares / CALIBRATION_SAMPLES);

    Serial.printf("Sensor %d - Baseline: %.2f, StdDev: %.2f\n",
                  i, sensors[i].baseline, sensors[i].stdDev);
  }
}

void checkTriggers()
{
  // Check if we're still in cooldown period
  if (millis() - lastDetectionTime < COOLDOWN_PERIOD)
  {
    return;
  }

  // Check each sensor for triggers
  for (int i = 0; i < NUM_SENSORS; i++)
  {
    float deviation = abs(sensors[i].currentValue - sensors[i].baseline);
    bool newTrigger = deviation > (sensors[i].stdDev * TRIGGER_THRESHOLD);

    // Detect rising edge of trigger
    if (newTrigger && !sensors[i].isTriggered)
    {
      sensors[i].isTriggered = true;
      sensors[i].lastTriggerTime = millis();

      // Check for sequences
      if (i == 0 || i == 2)
      { // Edge sensors
        unsigned long now = millis();
        // Check other sensors for recent triggers
        for (int j = 0; j < NUM_SENSORS; j++)
        {
          if (j != i && (now - sensors[j].lastTriggerTime) < TRIGGER_TIMEOUT)
          {
            String sequence = "";
            if (i == 0 && j == 2)
              sequence = "Left to Right";
            if (i == 2 && j == 0)
              sequence = "Right to Left";
            if (!sequence.isEmpty())
            {
              recordTriggerSequence(sequence);
            }
          }
        }
      }
    }
    else if (!newTrigger && sensors[i].isTriggered)
    {
      sensors[i].isTriggered = false;
    }
  }
}

void recordTriggerSequence(const String &sequence)
{
  lastDetectionTime = millis(); // Update cooldown timer
  triggerHistory[historyIndex] = {sequence, millis()};
  historyIndex = (historyIndex + 1) % HISTORY_SIZE;
  Serial.println("Detected: " + sequence);
}

void updateDisplay()
{
  sprite.fillSprite(TFT_BLACK);
  sprite.setTextDatum(TL_DATUM); // Top-left alignment

  // Display current readings and status
  for (int i = 0; i < NUM_SENSORS; i++)
  {
    int yPos = 10 + (i * 30);
    sprite.setTextColor(sensors[i].isTriggered ? TFT_RED : TFT_GREEN);

    String sensorText = "S" + String(i) + ": " +
                        String(sensors[i].currentValue, 1) +
                        " (B: " + String(sensors[i].baseline, 1) +
                        " ±" + String(sensors[i].stdDev * TRIGGER_THRESHOLD, 1) + ")";
    sprite.drawString(sensorText, 10, yPos, 2);
  }

  // Display recent trigger history
  sprite.setTextColor(TFT_YELLOW);
  sprite.drawString("Recent Triggers:", 10, 100, 2);

  for (int i = 0; i < HISTORY_SIZE; i++)
  {
    if (triggerHistory[i].timestamp > 0)
    {
      int idx = (historyIndex - i - 1 + HISTORY_SIZE) % HISTORY_SIZE;
      String timeAgo = String((millis() - triggerHistory[idx].timestamp) / 1000) + "s ago";
      sprite.drawString(triggerHistory[idx].sequence + " (" + timeAgo + ")",
                        10, 120 + (i * 20), 2);
    }
  }

  sprite.pushSprite(0, 0);
}
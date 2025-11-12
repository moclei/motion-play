/**
 * Motion Play - LED Strip Test
 *
 * Simple test program to verify WS2812B/WS2818B LED strip functionality
 *
 * Hardware:
 * - T-Display-S3 (ESP32-S3)
 * - WS2818B addressable LED strip (72 LEDs)
 * - Signal on GPIO 16 through SN74AHCT125 logic level shifter
 *
 * This test program will:
 * - Initialize the LED strip
 * - Display a nice red color on all LEDs
 * - Show status on the built-in display
 */

#include <Arduino.h>
#include <FastLED.h>
#include <TFT_eSPI.h>
#include "pin_config.h"

// LED Strip Configuration
#define NUM_LEDS 72
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB
#define BRIGHTNESS 128 // 0-255, starting at 50% brightness for safety

// Create LED array
CRGB leds[NUM_LEDS];

// Display
TFT_eSPI tft = TFT_eSPI();

// Colors for testing
const CRGB COLOR_RED = CRGB::Red;
const CRGB COLOR_GREEN = CRGB::Green;
const CRGB COLOR_BLUE = CRGB::Blue;
const CRGB COLOR_YELLOW = CRGB::Yellow;
const CRGB COLOR_PURPLE = CRGB::Purple;
const CRGB COLOR_CYAN = CRGB::Cyan;
const CRGB COLOR_WHITE = CRGB::White;
const CRGB COLOR_OFF = CRGB::Black;

void initDisplay()
{
    // Power on display
    pinMode(PIN_POWER_ON, OUTPUT);
    digitalWrite(PIN_POWER_ON, HIGH);

    // Initialize TFT
    tft.init();
    tft.setRotation(1); // Landscape
    tft.fillScreen(TFT_BLACK);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.setTextSize(2);

    // Draw header
    tft.setCursor(10, 10);
    tft.println("Motion Play");
    tft.setCursor(10, 30);
    tft.println("LED Strip Test");
    tft.drawLine(0, 50, tft.width(), 50, TFT_CYAN);
}

void displayStatus(const char *message, uint16_t color = TFT_WHITE)
{
    static int lineNum = 0;
    int yPos = 60 + (lineNum * 20);

    if (yPos > tft.height() - 30)
    {
        // Clear status area when full
        tft.fillRect(0, 60, tft.width(), tft.height() - 60, TFT_BLACK);
        lineNum = 0;
        yPos = 60;
    }

    tft.setTextColor(color, TFT_BLACK);
    tft.setCursor(10, yPos);
    tft.println(message);
    lineNum++;
}

void initLEDStrip()
{
    // Add LED strip configuration
    FastLED.addLeds<LED_TYPE, PIN_LED_STRIP_DATA, COLOR_ORDER>(leds, NUM_LEDS);

    // Set master brightness control
    FastLED.setBrightness(BRIGHTNESS);

    // Clear all LEDs to start
    FastLED.clear();
    FastLED.show();

    Serial.println("LED strip initialized");
    Serial.printf("  Type: WS2818B/WS2812B\n");
    Serial.printf("  Count: %d LEDs\n", NUM_LEDS);
    Serial.printf("  Data Pin: GPIO %d\n", PIN_LED_STRIP_DATA);
    Serial.printf("  Brightness: %d/255\n", BRIGHTNESS);
}

void setAllLEDs(CRGB color)
{
    fill_solid(leds, NUM_LEDS, color);
    FastLED.show();
}

void testPattern()
{
    Serial.println("\n=== Running LED Test Pattern ===");
    displayStatus("Running test...", TFT_YELLOW);

    // Test 1: All Red
    Serial.println("Test 1: All LEDs RED");
    displayStatus("All LEDs: RED", TFT_RED);
    setAllLEDs(COLOR_RED);
    delay(2000);

    // Test 2: All Green
    Serial.println("Test 2: All LEDs GREEN");
    displayStatus("All LEDs: GREEN", TFT_GREEN);
    setAllLEDs(COLOR_GREEN);
    delay(2000);

    // Test 3: All Blue
    Serial.println("Test 3: All LEDs BLUE");
    displayStatus("All LEDs: BLUE", TFT_BLUE);
    setAllLEDs(COLOR_BLUE);
    delay(2000);

    // Test 4: Rainbow sweep
    Serial.println("Test 4: Rainbow sweep");
    displayStatus("Rainbow sweep", TFT_MAGENTA);
    for (int hue = 0; hue < 255; hue++)
    {
        fill_solid(leds, NUM_LEDS, CHSV(hue, 255, 255));
        FastLED.show();
        delay(10);
    }
    delay(1000);

    // Test 5: Individual LED test
    Serial.println("Test 5: Individual LED test");
    displayStatus("LED by LED", TFT_CYAN);
    FastLED.clear();
    for (int i = 0; i < NUM_LEDS; i++)
    {
        leds[i] = COLOR_WHITE;
        FastLED.show();
        delay(20);
    }
    delay(1000);

    Serial.println("=== Test Pattern Complete ===\n");
    displayStatus("Test complete!", TFT_GREEN);
    delay(2000);
}

void setup()
{
    // Initialize Serial
    Serial.begin(115200);
    delay(1000);

    Serial.println("\n\n=================================");
    Serial.println("Motion Play - LED Strip Test");
    Serial.println("=================================\n");

    // Initialize display
    Serial.println("Initializing display...");
    initDisplay();
    displayStatus("Display: OK", TFT_GREEN);

    // IMPORTANT: Wait before initializing LEDs to allow time to switch power sources
    Serial.println("\n*** POWER SAFETY CHECK ***");
    Serial.println("Make sure DWEII power module is connected!");
    Serial.println("LEDs will initialize in 5 seconds...");
    displayStatus("SAFETY WAIT", TFT_YELLOW);
    displayStatus("Check DWEII power!", TFT_RED);
    displayStatus("Starting in 5s...", TFT_ORANGE);

    for (int i = 5; i > 0; i--)
    {
        Serial.printf("  %d...\n", i);
        delay(1000);
    }

    Serial.println("*** Initializing LED strip ***\n");

    // Initialize LED strip
    Serial.println("Initializing LED strip...");
    displayStatus("Init LED strip...", TFT_YELLOW);
    delay(500);
    initLEDStrip();
    displayStatus("LED strip: OK", TFT_GREEN);
    delay(1000);

    // Run test pattern
    testPattern();

    // Final state: Nice red color as requested
    Serial.println("Setting all LEDs to RED (final state)");
    displayStatus("Final: ALL RED!", TFT_RED);
    setAllLEDs(COLOR_RED);

    Serial.println("\n=== Setup Complete ===");
    Serial.println("LED strip is now displaying RED");
    Serial.println("Use buttons to change colors:");
    Serial.println("  Button 1 (GPIO 14): Cycle colors");
    Serial.println("  Button 2 (GPIO 0):  Toggle brightness");
}

void loop()
{
    static int colorIndex = 0;
    static bool brightnessHigh = true;
    static unsigned long lastButtonCheck = 0;

    // Check buttons every 100ms
    if (millis() - lastButtonCheck > 100)
    {
        lastButtonCheck = millis();

        // Button 1: Cycle through colors
        if (digitalRead(PIN_BUTTON_1) == LOW)
        {
            delay(50); // Debounce
            if (digitalRead(PIN_BUTTON_1) == LOW)
            {
                colorIndex = (colorIndex + 1) % 7;

                CRGB newColor;
                String colorName;
                uint16_t displayColor;

                switch (colorIndex)
                {
                case 0:
                    newColor = COLOR_RED;
                    colorName = "RED";
                    displayColor = TFT_RED;
                    break;
                case 1:
                    newColor = COLOR_GREEN;
                    colorName = "GREEN";
                    displayColor = TFT_GREEN;
                    break;
                case 2:
                    newColor = COLOR_BLUE;
                    colorName = "BLUE";
                    displayColor = TFT_BLUE;
                    break;
                case 3:
                    newColor = COLOR_YELLOW;
                    colorName = "YELLOW";
                    displayColor = TFT_YELLOW;
                    break;
                case 4:
                    newColor = COLOR_PURPLE;
                    colorName = "PURPLE";
                    displayColor = TFT_MAGENTA;
                    break;
                case 5:
                    newColor = COLOR_CYAN;
                    colorName = "CYAN";
                    displayColor = TFT_CYAN;
                    break;
                case 6:
                    newColor = COLOR_WHITE;
                    colorName = "WHITE";
                    displayColor = TFT_WHITE;
                    break;
                }

                Serial.printf("Color changed to: %s\n", colorName.c_str());
                displayStatus(("Color: " + colorName).c_str(), displayColor);
                setAllLEDs(newColor);

                // Wait for button release
                while (digitalRead(PIN_BUTTON_1) == LOW)
                {
                    delay(10);
                }
                delay(200); // Additional debounce
            }
        }

        // Button 2: Toggle brightness
        if (digitalRead(PIN_BUTTON_2) == LOW)
        {
            delay(50); // Debounce
            if (digitalRead(PIN_BUTTON_2) == LOW)
            {
                brightnessHigh = !brightnessHigh;
                uint8_t newBrightness = brightnessHigh ? 128 : 32;
                FastLED.setBrightness(newBrightness);
                FastLED.show();

                Serial.printf("Brightness: %s (%d/255)\n",
                              brightnessHigh ? "HIGH" : "LOW", newBrightness);
                displayStatus(brightnessHigh ? "Bright: HIGH" : "Bright: LOW", TFT_YELLOW);

                // Wait for button release
                while (digitalRead(PIN_BUTTON_2) == LOW)
                {
                    delay(10);
                }
                delay(200); // Additional debounce
            }
        }
    }

    // Keep the loop responsive
    delay(10);
}

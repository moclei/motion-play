/**
 * Simple T-Display-S3 Test
 *
 * This is a minimal test to verify display functionality
 * without any I2C or sensor complexity that might interfere.
 */

#include <Arduino.h>
#include <TFT_eSPI.h>
#include "pin_config.h"

TFT_eSPI tft = TFT_eSPI();

void setup()
{
    // Initialize serial
    Serial.begin(115200);
    delay(1000);

    Serial.println("=== T-Display-S3 Simple Test ===");
    Serial.println("Initializing display...");

    // Power on display and backlight (CRITICAL)
    pinMode(PIN_POWER_ON, OUTPUT);
    digitalWrite(PIN_POWER_ON, HIGH);

    // Enable backlight (CRITICAL for visibility)
    pinMode(PIN_LCD_BL, OUTPUT);
    digitalWrite(PIN_LCD_BL, HIGH);

    Serial.println("Power and backlight enabled");
    delay(200);

    // Initialize TFT
    tft.init();
    Serial.println("TFT initialized");

    // Set rotation to landscape
    tft.setRotation(1); // 0=portrait, 1=landscape, 2=portrait flipped, 3=landscape flipped
    Serial.println("Rotation set to landscape");

    // Fill screen with color to test
    tft.fillScreen(TFT_RED);
    Serial.println("Screen filled RED");
    delay(1000);

    tft.fillScreen(TFT_GREEN);
    Serial.println("Screen filled GREEN");
    delay(1000);

    tft.fillScreen(TFT_BLUE);
    Serial.println("Screen filled BLUE");
    delay(1000);

    tft.fillScreen(TFT_BLACK);
    Serial.println("Screen filled BLACK");

    // Draw some text
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.setTextSize(2);
    tft.setCursor(10, 10);
    tft.println("T-Display-S3");
    tft.setCursor(10, 40);
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.println("DISPLAY TEST");
    tft.setCursor(10, 70);
    tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    tft.println("SUCCESS!");

    Serial.println("Text drawn - if you can see this on screen, display is working!");
    Serial.println("If screen is still blank, check hardware connections.");
}

void loop()
{
    static unsigned long lastBlink = 0;
    static bool textVisible = true;

    if (millis() - lastBlink > 1000)
    {
        lastBlink = millis();
        textVisible = !textVisible;

        tft.setTextColor(textVisible ? TFT_CYAN : TFT_BLACK, TFT_BLACK);
        tft.setCursor(10, 100);
        tft.setTextSize(1);
        tft.println("Blinking text - system alive");

        Serial.println(textVisible ? "Text ON" : "Text OFF");
    }

    delay(10);
}

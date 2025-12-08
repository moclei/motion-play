#include "LEDController.h"

// Define static colors
const CRGB LEDController::COLOR_A_TO_B = CRGB(0, 100, 255); // Blue
const CRGB LEDController::COLOR_B_TO_A = CRGB(255, 100, 0); // Orange
const CRGB LEDController::COLOR_READY = CRGB(0, 50, 0);     // Dim green
const CRGB LEDController::COLOR_OFF = CRGB::Black;

LEDController::LEDController() : initialized(false), animationActive(false) {}

bool LEDController::init()
{
    if (initialized)
        return true;

    Serial.println("Initializing LED strip...");

    // Initialize FastLED
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
    FastLED.setBrightness(DEFAULT_BRIGHTNESS);

    // Clear all LEDs
    FastLED.clear();
    FastLED.show();

    initialized = true;
    Serial.printf("LED strip initialized: %d LEDs on GPIO %d\n", NUM_LEDS, LED_PIN);

    return true;
}

void LEDController::showDirection(Direction direction, uint32_t duration)
{
    if (!initialized)
        return;

    CRGB color;
    const char *dirName;

    switch (direction)
    {
    case Direction::A_TO_B:
        color = COLOR_A_TO_B;
        dirName = "A→B (Blue)";
        break;
    case Direction::B_TO_A:
        color = COLOR_B_TO_A;
        dirName = "B→A (Orange)";
        break;
    default:
        // Unknown - quick white flash
        color = CRGB::White;
        dirName = "Unknown (White)";
        duration = 500; // Short flash for unknown
        break;
    }

    Serial.printf("LED: Showing %s for %dms\n", dirName, duration);

    // Reset brightness to full (may have been dimmed by previous fade)
    FastLED.setBrightness(DEFAULT_BRIGHTNESS);

    // Set all LEDs to the color
    fill_solid(leds, NUM_LEDS, color);
    FastLED.show();

    // Start animation timer
    animationStartTime = millis();
    animationDuration = duration;
    animationActive = true;
    currentColor = color;
}

void LEDController::showReady()
{
    if (!initialized)
        return;

    // Subtle pulsing green to indicate ready state
    static uint8_t pulseValue = 0;
    static bool increasing = true;

    if (increasing)
    {
        pulseValue += 2;
        if (pulseValue >= 50)
            increasing = false;
    }
    else
    {
        pulseValue -= 2;
        if (pulseValue <= 10)
            increasing = true;
    }

    CRGB color = CRGB(0, pulseValue, 0);
    fill_solid(leds, NUM_LEDS, color);
    FastLED.show();
}

void LEDController::off()
{
    if (!initialized)
        return;

    FastLED.clear();
    FastLED.show();
    animationActive = false;
}

void LEDController::setColor(CRGB color)
{
    if (!initialized)
        return;

    fill_solid(leds, NUM_LEDS, color);
    FastLED.show();
}

void LEDController::setBrightness(uint8_t brightness)
{
    FastLED.setBrightness(brightness);
    if (initialized)
    {
        FastLED.show();
    }
}

bool LEDController::update()
{
    if (!initialized || !animationActive)
        return false;

    unsigned long elapsed = millis() - animationStartTime;

    if (elapsed >= animationDuration)
    {
        // Animation complete - turn off
        off();
        return false;
    }

    // Optional: Add fade-out effect in last 500ms
    if (elapsed > animationDuration - 500)
    {
        float fadeProgress = (animationDuration - elapsed) / 500.0f;
        uint8_t brightness = (uint8_t)(DEFAULT_BRIGHTNESS * fadeProgress);
        FastLED.setBrightness(brightness);
        FastLED.show();
    }

    return true;
}

bool LEDController::isAnimating() const
{
    return animationActive;
}

#include "LEDController.h"
#include "debug_log.h"

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

    DEBUG_LOG("Initializing LED strip...\n");

    FastLED.addLeds<WS2812B, PIN_LED_STRIP_DATA, GRB>(leds, LED_COUNT);
    FastLED.setBrightness(LED_DEFAULT_BRIGHTNESS);

    // Clear all LEDs
    FastLED.clear();
    FastLED.show();

    initialized = true;
    DEBUG_LOG("LED strip initialized: %d LEDs on GPIO %d\n", LED_COUNT, PIN_LED_STRIP_DATA);

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
        color = CRGB::Red;
        dirName = "Unknown (Red)";
        break;
    }

    DEBUG_LOG("LED: Showing %s for %dms\n", dirName, duration);

    FastLED.setBrightness(LED_DEFAULT_BRIGHTNESS);

    fill_solid(leds, LED_COUNT, color);
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
        pulseValue += LED_PULSE_STEP;
        if (pulseValue >= LED_PULSE_MAX)
            increasing = false;
    }
    else
    {
        pulseValue -= LED_PULSE_STEP;
        if (pulseValue <= LED_PULSE_MIN)
            increasing = true;
    }

    CRGB color = CRGB(0, pulseValue, 0);
    fill_solid(leds, LED_COUNT, color);
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

    fill_solid(leds, LED_COUNT, color);
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

    if (elapsed > animationDuration - LED_FADE_DURATION_MS)
    {
        float fadeProgress = (float)(animationDuration - elapsed) / LED_FADE_DURATION_MS;
        uint8_t brightness = (uint8_t)(LED_DEFAULT_BRIGHTNESS * fadeProgress);
        FastLED.setBrightness(brightness);
        FastLED.show();
    }

    return true;
}

bool LEDController::isAnimating() const
{
    return animationActive;
}

#include "LEDController.h"

extern bool serialStudioEnabled;

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

    if (!serialStudioEnabled)
        Serial.println("Initializing LED strip...");

    // Initialize FastLED
    FastLED.addLeds<LED_TYPE, LED_PIN, COLOR_ORDER>(leds, NUM_LEDS);
    FastLED.setBrightness(DEFAULT_BRIGHTNESS);

    // Soft power limit: keep LED strip draw under ~1A at 5V so the BQ24195
    // (IINLIM=2A on VSYS) has headroom for ESP32 + display (~300mA at 5V).
    FastLED.setMaxPowerInVoltsAndMilliamps(5, 1000);

    // Clear all LEDs
    FastLED.clear();
    FastLED.show();

    initialized = true;
    if (!serialStudioEnabled)
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
        color = CRGB::Red;
        dirName = "Unknown (Red)";
        break;
    }

    if (!serialStudioEnabled)
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

void LEDController::runStripTest(uint16_t count)
{
    if (!initialized)
    {
        if (!init())
            return;
    }

    if (count < 1)
        count = 1;
    if (count > NUM_LEDS)
        count = NUM_LEDS;

    Serial.printf("[LEDTest] Starting strip test on %u LEDs\n", count);

    // Cancel any in-progress direction animation and start from full brightness.
    animationActive = false;
    FastLED.setBrightness(255);
    FastLED.clear(true);

    // Brightness levels — conservative to stay within BQ24195 IINLIM budget.
    // FastLED soft power limit (1A) provides a backstop, but keep test values
    // modest so the readout on screen shows realistic current draw.
    const uint8_t LEVEL_20 = 51;  // ~20% of 255 (used for white / combined RGB)
    const uint8_t LEVEL_30 = 77;  // ~30% of 255 (used for single-channel phases)

    auto fillRange = [&](CRGB color)
    {
        for (uint16_t i = 0; i < count; ++i)
            leds[i] = color;
        for (uint16_t i = count; i < NUM_LEDS; ++i)
            leds[i] = CRGB::Black;
    };

    // ---- Phase 1: solid colors (single channels at 30%, white at 20%) ----
    Serial.println("[LEDTest] Phase 1: solid R/G/B @ 30%, W @ 20%");
    const CRGB phase1Colors[4] = {
        CRGB(LEVEL_30, 0, 0),
        CRGB(0, LEVEL_30, 0),
        CRGB(0, 0, LEVEL_30),
        CRGB(LEVEL_20, LEVEL_20, LEVEL_20),
    };
    for (int c = 0; c < 4; ++c)
    {
        fillRange(phase1Colors[c]);
        FastLED.show();
        delay(500);
    }
    fillRange(CRGB::Black);
    FastLED.show();
    delay(100);

    // ---- Phase 2: per-channel ramp 0 -> 30% over ~1s each ----
    Serial.println("[LEDTest] Phase 2: per-channel ramp R/G/B (capped 30%)");
    const uint8_t channels[3][3] = {
        {1, 0, 0}, // red
        {0, 1, 0}, // green
        {0, 0, 1}, // blue
    };
    for (int ch = 0; ch < 3; ++ch)
    {
        for (int v = 0; v <= LEVEL_30; v += 4)
        {
            CRGB color((uint8_t)(channels[ch][0] * v),
                       (uint8_t)(channels[ch][1] * v),
                       (uint8_t)(channels[ch][2] * v));
            fillRange(color);
            FastLED.show();
            delay(30);
        }
        fillRange(CRGB::Black);
        FastLED.show();
        delay(80);
    }

    // ---- Phase 3: combined RGB ramp to ~20% (peak current draw) ----
    Serial.println("[LEDTest] Phase 3: combined white ramp to ~20%");
    for (int v = 0; v <= LEVEL_20; v += 2)
    {
        fillRange(CRGB((uint8_t)v, (uint8_t)v, (uint8_t)v));
        FastLED.show();
        delay(30);
    }
    delay(600); // hold at peak — watch INA219 readout on display
    fillRange(CRGB::Black);
    FastLED.show();
    delay(150);

    // ---- Phase 4: sequential per-pixel sweep ----
    Serial.println("[LEDTest] Phase 4: sequential per-pixel sweep");
    for (uint16_t i = 0; i < count; ++i)
    {
        fillRange(CRGB::Black);
        leds[i] = CRGB(LEVEL_20, LEVEL_20, LEVEL_20);
        FastLED.show();
        delay(20);
    }

    // ---- Phase 5: cleanup ----
    Serial.println("[LEDTest] Phase 5: cleanup");
    FastLED.clear(true);
    FastLED.setBrightness(DEFAULT_BRIGHTNESS);
    Serial.println("[LEDTest] Strip test complete");
}

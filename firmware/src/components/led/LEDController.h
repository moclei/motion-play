#pragma once

#include <Arduino.h>
#include <FastLED.h>
#include "detection_types.h"
#include "pin_config.h"

/**
 * LED Controller for Motion Play
 * 
 * Controls the WS2812B LED strip to show direction detection results.
 * - Blue: A→B direction
 * - Orange: B→A direction  
 * - Green: Detection active/ready
 * - Off: Idle
 */

// LED Configuration
static constexpr uint8_t  LED_COUNT              = 72;
static constexpr uint8_t  LED_DEFAULT_BRIGHTNESS  = 128;
static constexpr uint32_t LED_FADE_DURATION_MS     = 500;
static constexpr uint32_t LED_DEFAULT_DISPLAY_DURATION_MS = 3000;
static constexpr uint8_t  LED_PULSE_MAX            = 50;
static constexpr uint8_t  LED_PULSE_MIN            = 10;
static constexpr uint8_t  LED_PULSE_STEP           = 2;

class LEDController {
private:
    CRGB leds[LED_COUNT];
    bool initialized = false;
    
    // Animation state
    unsigned long animationStartTime = 0;
    unsigned long animationDuration = 0;
    bool animationActive = false;
    CRGB currentColor;
    
    // Colors for directions
    static const CRGB COLOR_A_TO_B;  // Blue
    static const CRGB COLOR_B_TO_A;  // Orange
    static const CRGB COLOR_READY;   // Green pulse
    static const CRGB COLOR_OFF;     // Black
    
public:
    LEDController();
    
    /**
     * Initialize the LED strip
     */
    bool init();
    
    /**
     * Show direction result on LEDs
     * @param direction The detected direction
     * @param duration How long to show the result in ms (default 3000)
     */
    void showDirection(Direction direction, uint32_t duration = LED_DEFAULT_DISPLAY_DURATION_MS);
    
    /**
     * Show ready/waiting state (subtle green pulse)
     */
    void showReady();
    
    /**
     * Turn off all LEDs
     */
    void off();
    
    /**
     * Set all LEDs to a color
     */
    void setColor(CRGB color);
    
    /**
     * Set brightness (0-255)
     */
    void setBrightness(uint8_t brightness);
    
    /**
     * Update animation state (call in loop)
     * Returns true if animation is still active
     */
    bool update();
    
    /**
     * Check if currently animating
     */
    bool isAnimating() const;
};


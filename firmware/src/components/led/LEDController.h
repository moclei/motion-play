#ifndef LED_CONTROLLER_H
#define LED_CONTROLLER_H

#include <Arduino.h>
#include <FastLED.h>
#include "../detection/DirectionDetector.h"

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
#define NUM_LEDS 72
#define LED_PIN 16
#define LED_TYPE WS2812B
#define COLOR_ORDER GRB
#define DEFAULT_BRIGHTNESS 128

class LEDController {
private:
    CRGB leds[NUM_LEDS];
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
    void showDirection(Direction direction, uint32_t duration = 3000);
    
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

#endif


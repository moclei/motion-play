#include "ButtonHandler.h"
#include <Arduino.h>

ButtonHandler::ButtonHandler(uint8_t leftPin, uint8_t rightPin,
                             unsigned long longPressMs)
    : leftPin_(leftPin), rightPin_(rightPin), longPressMs_(longPressMs) {}

void ButtonHandler::init()
{
    pinMode(leftPin_, INPUT_PULLUP);
    pinMode(rightPin_, INPUT_PULLUP);
}

ButtonEvent ButtonHandler::update()
{
    int currentLeft = digitalRead(leftPin_);
    int currentRight = digitalRead(rightPin_);

    // Left button: detect hold >= longPressMs_ then fire once
    if (currentLeft == LOW)
    {
        if (!leftWasPressed_)
        {
            leftWasPressed_ = true;
            leftHoldStart_ = millis();
        }
        else if (millis() - leftHoldStart_ >= longPressMs_)
        {
            leftWasPressed_ = false;
            leftHoldStart_ = 0;
            return ButtonEvent::LEFT_LONG_PRESS;
        }
    }
    else
    {
        leftWasPressed_ = false;
        leftHoldStart_ = 0;
    }

    // Right button: falling-edge detection (HIGH → LOW)
    if (currentRight == LOW && rightPrevState_ == HIGH)
    {
        rightPrevState_ = currentRight;
        return ButtonEvent::RIGHT_PRESS;
    }
    rightPrevState_ = currentRight;

    return ButtonEvent::NONE;
}

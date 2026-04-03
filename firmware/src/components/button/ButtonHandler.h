#pragma once

#include <cstdint>

enum class ButtonEvent
{
    NONE,
    LEFT_LONG_PRESS,
    RIGHT_PRESS
};

class ButtonHandler
{
public:
    ButtonHandler(uint8_t leftPin, uint8_t rightPin,
                  unsigned long longPressMs = DEFAULT_LONG_PRESS_MS);

    void init();
    ButtonEvent update();

private:
    static constexpr unsigned long DEFAULT_LONG_PRESS_MS = 3000;

    uint8_t leftPin_;
    uint8_t rightPin_;
    unsigned long longPressMs_;

    int rightPrevState_ = 1; // HIGH
    unsigned long leftHoldStart_ = 0;
    bool leftWasPressed_ = false;
};

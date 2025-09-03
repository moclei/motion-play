#pragma once

#include <Arduino.h>
#include <Wire.h>

class TCA9548A
{
public:
    TCA9548A(uint8_t address = 0x70);
    bool begin();
    bool selectChannel(uint8_t channel);
    void disableAllChannels();
    uint8_t getCurrentChannel();
    bool isChannelSelected(uint8_t channel);

private:
    uint8_t _address;
    uint8_t _currentChannel;
};
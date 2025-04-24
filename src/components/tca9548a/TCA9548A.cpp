#include "TCA9548A.h"

TCA9548A::TCA9548A(uint8_t address) : _address(address), _currentChannel(0xFF) {}

bool TCA9548A::begin()
{
    Wire.beginTransmission(_address);
    return Wire.endTransmission() == 0;
}

bool TCA9548A::selectChannel(uint8_t channel)
{
    if (channel > 7)
        return false;

    Wire.beginTransmission(_address);
    Wire.write(1 << channel);
    if (Wire.endTransmission() == 0)
    {
        _currentChannel = channel;
        return true;
    }
    return false;
}

void TCA9548A::disableAllChannels()
{
    Wire.beginTransmission(_address);
    Wire.write(0);
    Wire.endTransmission();
    _currentChannel = 0xFF;
}
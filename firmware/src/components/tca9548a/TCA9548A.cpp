#include "TCA9548A.h"

TCA9548A::TCA9548A(uint8_t address) : _address(address), _currentChannel(0xFF) {}

bool TCA9548A::begin()
{
    // Test basic communication with TCA9548A
    Wire.beginTransmission(_address);
    Wire.setTimeout(100); // Set timeout
    uint8_t error = Wire.endTransmission();

    if (error == 0)
    {
        // Successfully communicated, now disable all channels to start clean
        disableAllChannels();
        return true;
    }
    return false;
}

bool TCA9548A::selectChannel(uint8_t channel)
{
    if (channel > 7)
        return false;

    // Skip if already on this channel
    if (_currentChannel == channel)
        return true;

    Wire.beginTransmission(_address);
    Wire.setTimeout(100);
    Wire.write(1 << channel);
    uint8_t error = Wire.endTransmission();

    if (error == 0)
    {
        _currentChannel = channel;
        return true;
    }
    return false;
}

void TCA9548A::disableAllChannels()
{
    Wire.beginTransmission(_address);
    Wire.setTimeout(100);
    Wire.write(0x00); // Disable all channels
    uint8_t error = Wire.endTransmission();

    if (error == 0)
    {
        _currentChannel = 0xFF; // Mark as no channel selected
    }
}

uint8_t TCA9548A::getCurrentChannel()
{
    return _currentChannel;
}

bool TCA9548A::isChannelSelected(uint8_t channel)
{
    return (_currentChannel == channel);
}
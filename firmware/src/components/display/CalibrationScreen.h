#pragma once

#include <TFT_eSPI.h>

class CalibrationScreen
{
private:
    TFT_eSPI &tft;

    static const int SCREEN_WIDTH = 320;
    static const int SCREEN_HEIGHT = 170;

public:
    explicit CalibrationScreen(TFT_eSPI &tft);

    void showIntro();
    void showBaseline(uint8_t pcbId, uint8_t progress);
    void showApproach(uint8_t pcbId, uint16_t currentReading, uint16_t threshold, uint8_t progress, uint32_t timeRemaining);
    void showSuccess(uint8_t pcbId);
    void showFailed(uint8_t pcbId, const String &reason = "Timeout");
    void showSummary(uint16_t threshold1, uint16_t threshold2, uint16_t threshold3, bool valid1 = true, bool valid2 = true, bool valid3 = true);
    void showComplete();
    void showCancelled();
};

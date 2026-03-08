#include "CalibrationScreen.h"

CalibrationScreen::CalibrationScreen(TFT_eSPI &tft) : tft(tft) {}

void CalibrationScreen::showIntro()
{
    tft.fillScreen(TFT_BLACK);

    // Title - centered, large
    tft.setTextSize(2);
    tft.setTextColor(TFT_MAGENTA, TFT_BLACK);
    tft.drawString("CALIBRATION", SCREEN_WIDTH / 2 - 66, 20);

    // Subtitle
    tft.setTextSize(1);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString("Sensor calibration wizard", SCREEN_WIDTH / 2 - 72, 50);

    // Instructions
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("This will calibrate all 3 sensor boards.", SCREEN_WIDTH / 2 - 114, 80);
    tft.drawString("For each PCB you will:", SCREEN_WIDTH / 2 - 63, 100);

    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.drawString("1. Wait for baseline (keep clear)", SCREEN_WIDTH / 2 - 99, 118);
    tft.drawString("2. Approach & hold near sensors", SCREEN_WIDTH / 2 - 93, 132);

    // Starting message
    tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    tft.drawString("Starting in 3 seconds...", SCREEN_WIDTH / 2 - 72, 155);
}

void CalibrationScreen::showBaseline(uint8_t pcbId, uint8_t progress)
{
    tft.fillScreen(TFT_BLACK);

    // PCB indicator
    tft.setTextSize(2);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    String pcbText = "PCB " + String(pcbId);
    tft.drawString(pcbText, SCREEN_WIDTH / 2 - 30, 10);

    // Step indicator
    tft.setTextSize(1);
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Step 1/2: Baseline", SCREEN_WIDTH / 2 - 54, 35);

    // Icon area - hand with "away" gesture
    tft.setTextSize(3);
    tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    tft.drawString("[ ]", SCREEN_WIDTH / 2 - 27, 55);

    // Instruction
    tft.setTextSize(1);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString("Keep area clear of objects", SCREEN_WIDTH / 2 - 78, 95);

    // Progress bar
    const int barX = 40;
    const int barY = 120;
    const int barW = SCREEN_WIDTH - 80;
    const int barH = 20;

    // Background
    tft.drawRoundRect(barX, barY, barW, barH, 4, TFT_DARKGREY);

    // Fill based on progress
    int fillW = (barW - 4) * progress / 100;
    if (fillW > 0)
    {
        tft.fillRoundRect(barX + 2, barY + 2, fillW, barH - 4, 2, TFT_GREEN);
    }

    // Percentage
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString(String(progress) + "%", SCREEN_WIDTH / 2 - 12, barY + 5);

    // Footer
    tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
    tft.drawString("Capturing noise floor...", SCREEN_WIDTH / 2 - 69, 150);
}

void CalibrationScreen::showApproach(uint8_t pcbId, uint16_t currentReading, uint16_t threshold, uint8_t progress, uint32_t timeRemaining)
{
    tft.fillScreen(TFT_BLACK);

    // PCB indicator
    tft.setTextSize(2);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    String pcbText = "PCB " + String(pcbId);
    tft.drawString(pcbText, SCREEN_WIDTH / 2 - 30, 5);

    // Step indicator
    tft.setTextSize(1);
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Step 2/2: Approach & Hold", SCREEN_WIDTH / 2 - 66, 28);

    // Large reading display - main focus
    tft.setTextSize(1);
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Reading:", 20, 50);
    tft.drawString("Need:", 20, 70);

    // Current reading - LARGE
    uint16_t readingColor = TFT_LIGHTGREY;
    if (currentReading >= threshold)
        readingColor = TFT_GREEN;
    else if (currentReading > threshold / 2)
        readingColor = TFT_YELLOW;
    else if (currentReading > 0)
        readingColor = TFT_ORANGE;

    tft.setTextSize(3);
    tft.setTextColor(readingColor, TFT_BLACK);
    tft.drawString(String(currentReading), 80, 42);

    // Threshold needed
    tft.setTextSize(2);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.drawString("> " + String(threshold), 80, 65);

    // Status indicator
    tft.setTextSize(1);
    if (currentReading >= threshold)
    {
        tft.setTextColor(TFT_GREEN, TFT_BLACK);
        tft.drawString("DETECTED! Hold steady...", SCREEN_WIDTH / 2 - 66, 92);
    }
    else if (currentReading > 0)
    {
        tft.setTextColor(TFT_YELLOW, TFT_BLACK);
        tft.drawString("Move CLOSER to sensors", SCREEN_WIDTH / 2 - 63, 92);
    }
    else
    {
        tft.setTextColor(TFT_RED, TFT_BLACK);
        tft.drawString("No reading - check sensor connection", SCREEN_WIDTH / 2 - 102, 92);
    }

    // Progress bar (fill when holding)
    const int barX = 20;
    const int barY = 108;
    const int barW = SCREEN_WIDTH - 40;
    const int barH = 16;

    tft.drawRoundRect(barX, barY, barW, barH, 4, TFT_DARKGREY);

    if (progress > 0)
    {
        int fillW = (barW - 4) * progress / 100;
        if (fillW > 0)
        {
            tft.fillRoundRect(barX + 2, barY + 2, fillW, barH - 4, 2, TFT_GREEN);
        }
        tft.setTextSize(1);
        tft.setTextColor(TFT_WHITE, TFT_BLACK);
        tft.drawString("Hold: " + String(progress) + "%", barX + barW / 2 - 24, barY + 3);
    }
    else
    {
        tft.setTextSize(1);
        tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
        tft.drawString("Waiting for detection...", barX + barW / 2 - 60, barY + 3);
    }

    // Time remaining
    uint32_t secs = timeRemaining / 1000;
    tft.setTextColor(secs < 3 ? TFT_RED : TFT_YELLOW, TFT_BLACK);
    tft.drawString("Timeout: " + String(secs) + "s", 20, 130);

    // Footer - cancel hint
    tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
    tft.drawString("Press RIGHT button to cancel", 20, 155);
}

void CalibrationScreen::showSuccess(uint8_t pcbId)
{
    tft.fillScreen(TFT_BLACK);

    // Large checkmark
    tft.setTextSize(4);
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString("OK", SCREEN_WIDTH / 2 - 24, 40);

    // Draw actual checkmark
    int cx = SCREEN_WIDTH / 2;
    int cy = 65;
    for (int i = 0; i < 4; i++)
    {
        tft.drawLine(cx - 30 + i, cy + 10, cx - 10, cy + 30 + i, TFT_GREEN);
        tft.drawLine(cx - 10, cy + 30 + i, cx + 30 - i, cy - 10, TFT_GREEN);
    }

    // Text
    tft.setTextSize(2);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    String msg = "PCB " + String(pcbId) + " complete!";
    tft.drawString(msg, SCREEN_WIDTH / 2 - 84, 100);

    // Next PCB hint (if not last)
    if (pcbId < 3)
    {
        tft.setTextSize(1);
        tft.setTextColor(TFT_CYAN, TFT_BLACK);
        tft.drawString("Next: PCB " + String(pcbId + 1), SCREEN_WIDTH / 2 - 36, 135);
    }
}

void CalibrationScreen::showFailed(uint8_t pcbId, const String &reason)
{
    tft.fillScreen(TFT_BLACK);

    // Large X
    tft.setTextSize(4);
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.drawString("X", SCREEN_WIDTH / 2 - 12, 30);

    // Error message
    tft.setTextSize(2);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    String msg = "PCB " + String(pcbId) + " failed";
    tft.drawString(msg, SCREEN_WIDTH / 2 - 72, 80);

    tft.setTextSize(1);
    tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    tft.drawString(reason, SCREEN_WIDTH / 2 - (reason.length() * 3), 110);

    // Instructions
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Calibration aborted.", SCREEN_WIDTH / 2 - 60, 135);
    tft.drawString("Press any button to exit", SCREEN_WIDTH / 2 - 72, 150);
}

void CalibrationScreen::showSummary(uint16_t threshold1, uint16_t threshold2, uint16_t threshold3, bool valid1, bool valid2, bool valid3)
{
    tft.fillScreen(TFT_BLACK);

    // Count valid PCBs
    int validCount = (valid1 ? 1 : 0) + (valid2 ? 1 : 0) + (valid3 ? 1 : 0);

    // Title - color based on success
    tft.setTextSize(2);
    if (validCount == 3)
    {
        tft.setTextColor(TFT_GREEN, TFT_BLACK);
        tft.drawString("CALIBRATION", SCREEN_WIDTH / 2 - 66, 10);
        tft.drawString("COMPLETE", SCREEN_WIDTH / 2 - 48, 30);
    }
    else if (validCount > 0)
    {
        tft.setTextColor(TFT_YELLOW, TFT_BLACK);
        tft.drawString("PARTIAL", SCREEN_WIDTH / 2 - 42, 10);
        tft.drawString("CALIBRATION", SCREEN_WIDTH / 2 - 66, 30);
    }
    else
    {
        tft.setTextColor(TFT_RED, TFT_BLACK);
        tft.drawString("CALIBRATION", SCREEN_WIDTH / 2 - 66, 10);
        tft.drawString("FAILED", SCREEN_WIDTH / 2 - 36, 30);
    }

    // Subtitle
    tft.setTextSize(1);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString("Results (" + String(validCount) + "/3 PCBs):", SCREEN_WIDTH / 2 - 54, 55);

    // Thresholds in a nice grid
    const int colX = 30;
    const int col2X = 100;

    // PCB 1
    tft.setTextColor(valid1 ? TFT_CYAN : TFT_DARKGREY, TFT_BLACK);
    tft.drawString("PCB 1:", colX, 75);
    tft.setTextSize(2);
    tft.setTextColor(valid1 ? TFT_GREEN : TFT_RED, TFT_BLACK);
    tft.drawString(valid1 ? String(threshold1) : "FAIL", col2X, 70);

    // PCB 2
    tft.setTextSize(1);
    tft.setTextColor(valid2 ? TFT_CYAN : TFT_DARKGREY, TFT_BLACK);
    tft.drawString("PCB 2:", colX, 95);
    tft.setTextSize(2);
    tft.setTextColor(valid2 ? TFT_GREEN : TFT_RED, TFT_BLACK);
    tft.drawString(valid2 ? String(threshold2) : "FAIL", col2X, 90);

    // PCB 3
    tft.setTextSize(1);
    tft.setTextColor(valid3 ? TFT_CYAN : TFT_DARKGREY, TFT_BLACK);
    tft.drawString("PCB 3:", colX, 115);
    tft.setTextSize(2);
    tft.setTextColor(valid3 ? TFT_GREEN : TFT_RED, TFT_BLACK);
    tft.drawString(valid3 ? String(threshold3) : "FAIL", col2X, 110);

    // Footer
    tft.setTextSize(1);
    tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    tft.drawString("Press any button to continue", SCREEN_WIDTH / 2 - 84, 145);
}

void CalibrationScreen::showComplete()
{
    tft.fillScreen(TFT_BLACK);

    tft.setTextSize(2);
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString("CALIBRATION", SCREEN_WIDTH / 2 - 66, 50);
    tft.drawString("SAVED", SCREEN_WIDTH / 2 - 30, 75);

    tft.setTextSize(1);
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Returning to session...", SCREEN_WIDTH / 2 - 66, 110);
}

void CalibrationScreen::showCancelled()
{
    tft.fillScreen(TFT_BLACK);

    tft.setTextSize(2);
    tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    tft.drawString("CANCELLED", SCREEN_WIDTH / 2 - 54, 60);

    tft.setTextSize(1);
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Calibration was cancelled", SCREEN_WIDTH / 2 - 75, 100);
    tft.drawString("Previous settings unchanged", SCREEN_WIDTH / 2 - 81, 120);
}

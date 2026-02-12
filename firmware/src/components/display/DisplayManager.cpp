#include "DisplayManager.h"
#include "pin_config.h"
#include "components/sensor/SensorConfiguration.h"

void DisplayManager::init()
{
    // Power on display and backlight (CRITICAL for T-Display-S3)
    pinMode(PIN_POWER_ON, OUTPUT);
    digitalWrite(PIN_POWER_ON, HIGH);

    pinMode(PIN_LCD_BL, OUTPUT);
    digitalWrite(PIN_LCD_BL, HIGH);

    delay(100); // Give display time to power up

    tft.init();
    tft.setRotation(1); // Landscape (320x170)
    tft.fillScreen(TFT_BLACK);
    tft.setTextDatum(TL_DATUM); // Top-left alignment
}

// ============================================================================
// INITIALIZATION SCREEN
// ============================================================================

void DisplayManager::showInitScreen()
{
    clear();
    currentInitStage = INIT_BOOT;

    // Title
    tft.setTextSize(2);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.drawString("MOTION PLAY", 10, 5);

    drawProgressBar();
}

void DisplayManager::updateInitStage(InitStage stage, const String &message)
{
    currentInitStage = stage;
    drawProgressBar();

    // Show message below progress bar
    if (message.length() > 0)
    {
        tft.fillRect(0, 65, SCREEN_WIDTH, 20, TFT_BLACK);
        tft.setTextSize(1);
        tft.setTextColor(TFT_WHITE, TFT_BLACK);
        tft.drawString(message, 10, 65);
    }
}

void DisplayManager::setInitError(const String &error)
{
    errorMessage = error;
    tft.fillRect(0, 90, SCREEN_WIDTH, 80, TFT_BLACK);
    tft.setTextSize(2);
    tft.setTextColor(TFT_RED, TFT_BLACK);
    tft.drawString("ERROR", 10, 95);
    tft.setTextSize(1);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString(error, 10, 120);
}

void DisplayManager::drawProgressBar()
{
    const int barX = 10;
    const int barY = PROGRESS_BAR_Y;
    const int barWidth = SCREEN_WIDTH - 20;
    const int barHeight = PROGRESS_BAR_HEIGHT;
    const int numStages = 6; // Boot, WiFi, MQTT, Sensors, Complete (skip connecting states)
    const int segmentWidth = barWidth / numStages;

    // Clear progress bar area
    tft.fillRect(barX, barY, barWidth, barHeight, TFT_BLACK);

    // Draw progress segments
    for (int i = 0; i < numStages; i++)
    {
        int x = barX + (i * segmentWidth);
        bool completed = false;
        bool active = false;
        String label = "";

        // Determine completion status and label
        switch (i)
        {
        case 0: // Boot
            label = "BOOT";
            completed = (currentInitStage >= INIT_BOOT);
            active = (currentInitStage == INIT_BOOT);
            break;
        case 1: // WiFi
            label = "WIFI";
            completed = (currentInitStage >= INIT_WIFI_CONNECTED);
            active = (currentInitStage == INIT_WIFI_CONNECTING);
            break;
        case 2: // MQTT
            label = "MQTT";
            completed = (currentInitStage >= INIT_MQTT_CONNECTED);
            active = (currentInitStage == INIT_MQTT_CONNECTING);
            break;
        case 3: // Sensors
            label = "SENS";
            completed = (currentInitStage >= INIT_SENSORS);
            active = (currentInitStage == INIT_SENSORS);
            break;
        case 4: // Complete
            label = "DONE";
            completed = (currentInitStage >= INIT_COMPLETE);
            active = false;
            break;
        }

        // Draw segment box
        uint16_t boxColor;
        if (completed)
        {
            boxColor = TFT_GREEN;
        }
        else if (active)
        {
            boxColor = TFT_YELLOW;
        }
        else
        {
            boxColor = TFT_DARKGREY;
        }

        // Fill segment
        tft.fillRect(x + 2, barY + 2, segmentWidth - 4, barHeight - 4, boxColor);

        // Draw segment border
        tft.drawRect(x, barY, segmentWidth, barHeight, TFT_WHITE);

        // Draw checkmark if completed
        if (completed)
        {
            drawCheckmark(x + segmentWidth / 2 - 5, barY + 5, TFT_WHITE);
        }

        // Draw label
        tft.setTextSize(1);
        tft.setTextColor(completed ? TFT_BLACK : TFT_WHITE, boxColor);
        int textX = x + (segmentWidth - (label.length() * 6)) / 2;
        tft.drawString(label, textX, barY + barHeight - 12);
    }
}

void DisplayManager::drawCheckmark(int x, int y, uint16_t color)
{
    // Draw a simple checkmark
    tft.drawLine(x, y + 5, x + 3, y + 8, color);
    tft.drawLine(x + 3, y + 8, x + 8, y, color);
    tft.drawLine(x, y + 6, x + 3, y + 9, color);
    tft.drawLine(x + 3, y + 9, x + 8, y + 1, color);
}

void DisplayManager::drawModeBadge()
{
    // Draw mode badge in top-right corner
    const int badgeX = SCREEN_WIDTH - 60;
    const int badgeY = 4;
    const int badgeW = 55;
    const int badgeH = 20;
    
    // Get mode text and color
    String modeText;
    uint16_t bgColor;
    uint16_t textColor = TFT_WHITE;
    
    switch (currentMode)
    {
    case MODE_IDLE:
        modeText = "IDLE";
        bgColor = TFT_DARKGREY;
        break;
    case MODE_DEBUG:
        modeText = "DEBUG";
        bgColor = TFT_BLUE;
        break;
    case MODE_PLAY:
        modeText = "PLAY";
        bgColor = TFT_GREEN;
        textColor = TFT_BLACK;
        break;
    default:
        modeText = "???";
        bgColor = TFT_DARKGREY;
        break;
    }
    
    // Draw badge background with rounded corners effect
    tft.fillRoundRect(badgeX, badgeY, badgeW, badgeH, 4, bgColor);
    
    // Draw badge text centered
    tft.setTextSize(1);
    tft.setTextColor(textColor, bgColor);
    int textWidth = modeText.length() * 6;
    tft.drawString(modeText, badgeX + (badgeW - textWidth) / 2, badgeY + 6);
}

void DisplayManager::drawStatusBadge()
{
    // Draw compact status badge in header (next to title)
    String statusText;
    uint16_t bgColor;
    uint16_t textColor = TFT_WHITE;
    
    switch (currentDisplayState)
    {
    case DISPLAY_IDLE:
        statusText = "IDLE";
        bgColor = TFT_DARKGREY;
        break;
    case DISPLAY_RECORDING:
        statusText = "REC";
        bgColor = TFT_RED;
        break;
    case DISPLAY_UPLOADING:
        statusText = "UP";
        bgColor = TFT_YELLOW;
        textColor = TFT_BLACK;
        break;
    case DISPLAY_SUCCESS:
        statusText = "OK";
        bgColor = TFT_GREEN;
        textColor = TFT_BLACK;
        break;
    case DISPLAY_ERROR:
        statusText = "ERR";
        bgColor = TFT_RED;
        break;
    default:
        statusText = "?";
        bgColor = TFT_DARKGREY;
        break;
    }
    
    // Draw badge background
    tft.fillRoundRect(STATUS_BADGE_X, STATUS_BADGE_Y, STATUS_BADGE_W, STATUS_BADGE_H, 4, bgColor);
    
    // Draw badge text centered
    tft.setTextSize(1);
    tft.setTextColor(textColor, bgColor);
    int textWidth = statusText.length() * 6;
    tft.drawString(statusText, STATUS_BADGE_X + (STATUS_BADGE_W - textWidth) / 2, STATUS_BADGE_Y + 6);
    
    // Add pulsing dot for recording
    if (currentDisplayState == DISPLAY_RECORDING)
    {
        tft.fillCircle(STATUS_BADGE_X + 8, STATUS_BADGE_Y + STATUS_BADGE_H / 2, 4, TFT_WHITE);
    }
}

void DisplayManager::drawConfigPanel()
{
    // Draw sensor configuration in center area
    const int panelX = 8;
    const int panelY = CONFIG_AREA_Y;
    const int panelW = SCREEN_WIDTH - 16;
    const int panelH = CONFIG_AREA_HEIGHT;
    
    // Clear config area
    tft.fillRect(panelX, panelY, panelW, panelH, TFT_BLACK);
    
    // Draw subtle border
    tft.drawRoundRect(panelX, panelY, panelW, panelH, 4, 0x3186);  // Dark gray border
    
    // Config title
    tft.setTextSize(1);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.drawString("SENSOR CONFIG", panelX + 6, panelY + 4);
    
    // Horizontal line under title
    tft.drawFastHLine(panelX + 4, panelY + 15, panelW - 8, 0x3186);
    
    // Layout: 3 columns for main settings
    const int col1X = panelX + 8;
    const int col2X = panelX + 110;
    const int col3X = panelX + 210;
    const int row1Y = panelY + 22;
    const int row2Y = panelY + 42;
    const int row3Y = panelY + 62;
    const int row4Y = panelY + 82;
    
    // Row 1: Rate, LED Current, Integration Time
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Rate:", col1X, row1Y);
    tft.drawString("LED:", col2X, row1Y);
    tft.drawString("IT:", col3X, row1Y);
    
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString(String(cachedSampleRate) + "Hz", col1X + 35, row1Y);
    tft.drawString(cachedLedCurrent, col2X + 30, row1Y);
    tft.drawString(cachedIntegrationTime, col3X + 20, row1Y);
    
    // Row 2: Duty Cycle, I2C Clock
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Duty:", col1X, row2Y);
    tft.drawString("I2C:", col2X, row2Y);
    
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString(cachedDutyCycle, col1X + 35, row2Y);
    tft.drawString(String(cachedI2cClock) + "kHz", col2X + 30, row2Y);
    
    // Row 3: Boolean flags with colored indicators
    // Hi-Res indicator
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Hi-Res:", col1X, row3Y);
    if (cachedHighRes)
    {
        tft.fillCircle(col1X + 50, row3Y + 3, 4, TFT_GREEN);
        tft.setTextColor(TFT_GREEN, TFT_BLACK);
        tft.drawString("ON", col1X + 58, row3Y);
    }
    else
    {
        tft.fillCircle(col1X + 50, row3Y + 3, 4, TFT_DARKGREY);
        tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
        tft.drawString("OFF", col1X + 58, row3Y);
    }
    
    // Ambient indicator
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Ambient:", col2X, row3Y);
    if (cachedReadAmbient)
    {
        tft.fillCircle(col2X + 55, row3Y + 3, 4, TFT_GREEN);
        tft.setTextColor(TFT_GREEN, TFT_BLACK);
        tft.drawString("ON", col2X + 63, row3Y);
    }
    else
    {
        tft.fillCircle(col2X + 55, row3Y + 3, 4, TFT_DARKGREY);
        tft.setTextColor(TFT_DARKGREY, TFT_BLACK);
        tft.drawString("OFF", col2X + 63, row3Y);
    }
    
    // Row 4: Sample count during recording
    if (currentDisplayState == DISPLAY_RECORDING)
    {
        tft.setTextColor(TFT_CYAN, TFT_BLACK);
        tft.drawString("Samples:", col1X, row4Y);
        tft.setTextColor(TFT_WHITE, TFT_BLACK);
        tft.drawString(String(sampleCount), col1X + 55, row4Y);
    }
}

void DisplayManager::setMode(DisplayMode mode)
{
    currentMode = mode;
    // Redraw the badge immediately
    drawModeBadge();
}

void DisplayManager::setSensorConfig(const SensorConfiguration* config)
{
    if (config == nullptr) return;
    
    // Cache config values
    cachedSampleRate = config->sample_rate_hz;
    cachedLedCurrent = config->led_current;
    cachedIntegrationTime = config->integration_time;
    cachedDutyCycle = config->duty_cycle;
    cachedHighRes = config->high_resolution;
    cachedReadAmbient = config->read_ambient;
    cachedI2cClock = config->i2c_clock_khz;
    
    // Redraw config panel if on session screen
    if (currentDisplayState != DISPLAY_ERROR)
    {
        drawConfigPanel();
    }
}

// ============================================================================
// SESSION SCREEN
// ============================================================================

void DisplayManager::showSessionScreen()
{
    clear();
    currentDisplayState = DISPLAY_IDLE;
    drawSessionStatus();
}

void DisplayManager::setDisplayState(DisplayState state)
{
    currentDisplayState = state;
    drawSessionStatus();
}

void DisplayManager::updateSampleCount(int count)
{
    sampleCount = count;

    // Update sample counter in config panel (only in recording state)
    if (currentDisplayState == DISPLAY_RECORDING)
    {
        // Clear and redraw just the sample count area in config panel
        const int panelX = 8;
        const int row4Y = CONFIG_AREA_Y + 82;
        
        tft.fillRect(panelX + 8 + 55, row4Y, 80, 12, TFT_BLACK);
        tft.setTextSize(1);
        tft.setTextColor(TFT_WHITE, TFT_BLACK);
        tft.drawString(String(count), panelX + 8 + 55, row4Y);
    }
}

void DisplayManager::showMessage(const String &message, uint16_t color)
{
    // Clear message area
    tft.fillRect(0, MESSAGE_Y, SCREEN_WIDTH, 25, TFT_BLACK);

    // Draw message centered
    tft.setTextSize(1);
    tft.setTextColor(color, TFT_BLACK);
    int textWidth = message.length() * 6;
    tft.drawString(message, SCREEN_WIDTH / 2 - textWidth / 2, MESSAGE_Y);
}

void DisplayManager::drawSessionStatus()
{
    // Clear header area
    tft.fillRect(0, 0, SCREEN_WIDTH, HEADER_HEIGHT, TFT_BLACK);

    // Title
    tft.setTextSize(2);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.drawString("MOTION", 8, 5);
    
    // Status badge (next to title)
    drawStatusBadge();
    
    // Mode badge (top-right corner)
    drawModeBadge();
    
    // Draw config panel in center area
    drawConfigPanel();

    // Show appropriate message based on state
    switch (currentDisplayState)
    {
    case DISPLAY_IDLE:
        showMessage("Ready to record", TFT_LIGHTGREY);
        break;

    case DISPLAY_RECORDING:
        showMessage("Recording in progress...", TFT_RED);
        break;

    case DISPLAY_UPLOADING:
        showMessage("Uploading to cloud...", TFT_YELLOW);
        break;

    case DISPLAY_SUCCESS:
        showMessage("Upload complete!", TFT_GREEN);
        break;

    case DISPLAY_ERROR:
        showMessage(errorMessage.isEmpty() ? "Error occurred" : errorMessage, TFT_RED);
        break;
    }
}

// ============================================================================
// LEGACY COMPATIBILITY METHODS
// ============================================================================

void DisplayManager::showBootScreen()
{
    showInitScreen();
}

void DisplayManager::updateStatus(const String &status, uint16_t color)
{
    showMessage(status, color);
}

void DisplayManager::setConfigString(const String &config)
{
    configString = config;
    
    // Refresh display if we're currently recording
    if (currentDisplayState == DISPLAY_RECORDING)
    {
        drawSessionStatus();
    }
}

void DisplayManager::showNetworkInfo(const String &ip, int rssi)
{
    showMessage("WiFi: " + ip + " (" + String(rssi) + " dBm)", TFT_GREEN);
}

void DisplayManager::showMQTTStatus(bool connected)
{
    if (connected)
    {
        updateInitStage(INIT_MQTT_CONNECTED, "MQTT connected");
    }
    else
    {
        showMessage("MQTT disconnected", TFT_RED);
    }
}

void DisplayManager::clear()
{
    tft.fillScreen(TFT_BLACK);
}

// ============================================================================
// CALIBRATION SCREENS
// ============================================================================

void DisplayManager::showCalibrationIntro()
{
    clear();
    
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

void DisplayManager::showCalibrationBaseline(uint8_t pcbId, uint8_t progress)
{
    clear();
    
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
    tft.drawString("[ ]", SCREEN_WIDTH / 2 - 27, 55);  // Simple "empty" icon
    
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

void DisplayManager::showCalibrationApproach(uint8_t pcbId, uint16_t currentReading, uint16_t threshold, uint8_t progress, uint32_t timeRemaining)
{
    clear();
    
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

void DisplayManager::showCalibrationSuccess(uint8_t pcbId)
{
    clear();
    
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

void DisplayManager::showCalibrationFailed(uint8_t pcbId, const String &reason)
{
    clear();
    
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

void DisplayManager::showCalibrationSummary(uint16_t threshold1, uint16_t threshold2, uint16_t threshold3, bool valid1, bool valid2, bool valid3)
{
    clear();
    
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
    const int col3X = 180;
    
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

void DisplayManager::showCalibrationComplete()
{
    // This transitions back to normal display
    // The caller should switch display mode
    showSessionScreen();
    showMessage("Calibration saved!", TFT_GREEN);
}

void DisplayManager::showCalibrationCancelled()
{
    clear();
    
    tft.setTextSize(2);
    tft.setTextColor(TFT_YELLOW, TFT_BLACK);
    tft.drawString("CANCELLED", SCREEN_WIDTH / 2 - 54, 60);
    
    tft.setTextSize(1);
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Calibration was cancelled", SCREEN_WIDTH / 2 - 75, 100);
    tft.drawString("Previous settings unchanged", SCREEN_WIDTH / 2 - 81, 120);
}
#include "DisplayManager.h"
#include "pin_config.h"

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

    // Update sample counter (only in recording state)
    if (currentDisplayState == DISPLAY_RECORDING)
    {
        tft.fillRect(SCREEN_WIDTH / 2 - 60, STATUS_INDICATOR_Y + STATUS_INDICATOR_SIZE + 10, 120, 20, TFT_BLACK);
        tft.setTextSize(2);
        tft.setTextColor(TFT_WHITE, TFT_BLACK);
        String countStr = String(count) + " samples";
        int textWidth = countStr.length() * 12;
        tft.drawString(countStr, SCREEN_WIDTH / 2 - textWidth / 2, STATUS_INDICATOR_Y + STATUS_INDICATOR_SIZE + 10);
    }
}

void DisplayManager::showMessage(const String &message, uint16_t color)
{
    // Clear message area
    tft.fillRect(0, MESSAGE_Y, SCREEN_WIDTH, 20, TFT_BLACK);

    // Draw message centered
    tft.setTextSize(1);
    tft.setTextColor(color, TFT_BLACK);
    int textWidth = message.length() * 6;
    tft.drawString(message, SCREEN_WIDTH / 2 - textWidth / 2, MESSAGE_Y);
}

void DisplayManager::drawSessionStatus()
{
    // Clear screen
    tft.fillRect(0, 0, SCREEN_WIDTH, STATUS_INDICATOR_Y + STATUS_INDICATOR_SIZE + 30, TFT_BLACK);

    // Title
    tft.setTextSize(2);
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.drawString("MOTION PLAY", 10, 5);

    // Status display
    tft.setTextSize(1);
    tft.setTextColor(TFT_LIGHTGREY, TFT_BLACK);
    tft.drawString("Status:", 10, 30);

    // Center status indicator
    int centerX = SCREEN_WIDTH / 2;
    int indicatorX = centerX - STATUS_INDICATOR_SIZE / 2;

    switch (currentDisplayState)
    {
    case DISPLAY_IDLE:
        drawStatusIndicator(indicatorX, STATUS_INDICATOR_Y, TFT_DARKGREY, "IDLE");
        showMessage("Ready to record", TFT_LIGHTGREY);
        break;

    case DISPLAY_RECORDING:
        drawStatusIndicator(indicatorX, STATUS_INDICATOR_Y, TFT_RED, "REC");
        // Draw pulsing effect (filled circle)
        tft.fillCircle(centerX, STATUS_INDICATOR_Y + STATUS_INDICATOR_SIZE / 2, STATUS_INDICATOR_SIZE / 2 - 5, TFT_RED);
        showMessage("Recording in progress...", TFT_RED);
        
        // Show config on second line if available
        if (!configString.isEmpty())
        {
            tft.setTextSize(1);
            tft.setTextColor(TFT_CYAN, TFT_BLACK);
            int configY = MESSAGE_Y + 15; // Below the main message
            tft.drawString(configString, SCREEN_WIDTH / 2, configY);
        }
        break;

    case DISPLAY_UPLOADING:
        drawStatusIndicator(indicatorX, STATUS_INDICATOR_Y, TFT_YELLOW, "UP");
        showMessage("Uploading to cloud...", TFT_YELLOW);
        break;

    case DISPLAY_SUCCESS:
        drawStatusIndicator(indicatorX, STATUS_INDICATOR_Y, TFT_GREEN, "OK");
        drawCheckmark(centerX - 10, STATUS_INDICATOR_Y + STATUS_INDICATOR_SIZE / 2 - 10, TFT_WHITE);
        showMessage("Upload complete!", TFT_GREEN);
        break;

    case DISPLAY_ERROR:
        drawStatusIndicator(indicatorX, STATUS_INDICATOR_Y, TFT_RED, "ERR");
        showMessage(errorMessage, TFT_RED);
        break;
    }
}

void DisplayManager::drawStatusIndicator(int x, int y, uint16_t color, const String &label)
{
    // Draw circle
    int centerX = x + STATUS_INDICATOR_SIZE / 2;
    int centerY = y + STATUS_INDICATOR_SIZE / 2;

    tft.drawCircle(centerX, centerY, STATUS_INDICATOR_SIZE / 2, color);
    tft.drawCircle(centerX, centerY, STATUS_INDICATOR_SIZE / 2 - 1, color);
    tft.drawCircle(centerX, centerY, STATUS_INDICATOR_SIZE / 2 - 2, color);

    // Draw label inside circle
    tft.setTextSize(2);
    tft.setTextColor(color, TFT_BLACK);
    int textWidth = label.length() * 12;
    tft.drawString(label, centerX - textWidth / 2, centerY - 8);
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
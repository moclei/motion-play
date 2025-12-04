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
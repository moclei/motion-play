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
    tft.setRotation(1); // Landscape
    tft.fillScreen(TFT_BLACK);
    tft.setTextSize(2);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
}

void DisplayManager::showBootScreen()
{
    clear();
    tft.setTextColor(TFT_CYAN, TFT_BLACK);
    tft.drawString("Motion Play", 10, 10);
    tft.setTextColor(TFT_WHITE, TFT_BLACK);
    tft.drawString("Initializing...", 10, 40);
    statusY = 70;
}

void DisplayManager::updateStatus(const String &status, uint16_t color)
{
    tft.setTextColor(color, TFT_BLACK);
    tft.fillRect(10, statusY, 220, 20, TFT_BLACK);
    tft.drawString(status, 10, statusY);
    statusY += 25;
    if (statusY > 160)
        statusY = 70; // Wrap around
}

void DisplayManager::showNetworkInfo(const String &ip, int rssi)
{
    tft.setTextColor(TFT_GREEN, TFT_BLACK);
    tft.drawString("WiFi: " + ip, 10, 100);
    tft.drawString("RSSI: " + String(rssi) + " dBm", 10, 125);
}

void DisplayManager::showMQTTStatus(bool connected)
{
    tft.setTextColor(connected ? TFT_GREEN : TFT_RED, TFT_BLACK);
    tft.fillRect(10, 150, 220, 20, TFT_BLACK);
    tft.drawString("MQTT: " + String(connected ? "Connected" : "Disconnected"), 10, 150);
}

void DisplayManager::clear()
{
    tft.fillScreen(TFT_BLACK);
}
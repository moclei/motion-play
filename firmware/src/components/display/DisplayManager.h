#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include <TFT_eSPI.h>

class DisplayManager {
private:
    TFT_eSPI tft = TFT_eSPI();
    int statusY = 0;

public:
    void init();
    void showBootScreen();
    void updateStatus(const String& status, uint16_t color = TFT_WHITE);
    void showNetworkInfo(const String& ip, int rssi);
    void showMQTTStatus(bool connected);
    void clear();
};

#endif
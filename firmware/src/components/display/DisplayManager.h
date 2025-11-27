#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include <TFT_eSPI.h>

// Initialization stages
enum InitStage
{
    INIT_BOOT = 0,
    INIT_WIFI_CONNECTING,
    INIT_WIFI_CONNECTED,
    INIT_MQTT_CONNECTING,
    INIT_MQTT_CONNECTED,
    INIT_SENSORS,
    INIT_COMPLETE
};

// Display states (visual representation)
enum DisplayState
{
    DISPLAY_IDLE,
    DISPLAY_RECORDING,
    DISPLAY_UPLOADING,
    DISPLAY_SUCCESS,
    DISPLAY_ERROR
};

class DisplayManager
{
private:
    TFT_eSPI tft = TFT_eSPI();
    InitStage currentInitStage = INIT_BOOT;
    DisplayState currentDisplayState = DISPLAY_IDLE;
    String errorMessage = "";
    int sampleCount = 0;
    String configString = ""; // For displaying config during recording

    // Layout constants
    static const int SCREEN_WIDTH = 320;
    static const int SCREEN_HEIGHT = 170;
    static const int PROGRESS_BAR_Y = 20;
    static const int PROGRESS_BAR_HEIGHT = 40;
    static const int STATUS_INDICATOR_Y = 80;
    static const int STATUS_INDICATOR_SIZE = 60;
    static const int MESSAGE_Y = 150;

    // Drawing helpers
    void drawProgressBar();
    void drawSessionStatus();
    void drawStatusIndicator(int x, int y, uint16_t color, const String &label);
    void drawCheckmark(int x, int y, uint16_t color);

public:
    void init();

    // Initialization flow
    void showInitScreen();
    void updateInitStage(InitStage stage, const String &message = "");
    void setInitError(const String &error);

    // Session display
    void showSessionScreen();
    void setDisplayState(DisplayState state);
    void updateSampleCount(int count);
    void showMessage(const String &message, uint16_t color = TFT_WHITE);
    void setConfigString(const String &config); // Set config for display during recording

    // Legacy compatibility (for gradual migration)
    void showBootScreen();
    void updateStatus(const String &status, uint16_t color = TFT_WHITE);
    void showNetworkInfo(const String &ip, int rssi);
    void showMQTTStatus(bool connected);
    void clear();
};

#endif
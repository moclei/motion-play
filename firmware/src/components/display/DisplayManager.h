#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include <TFT_eSPI.h>

// Forward declarations
struct SensorConfiguration;
enum class CalibrationState : uint8_t;

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

// Device operating modes
enum DisplayMode
{
    MODE_IDLE,
    MODE_DEBUG,
    MODE_PLAY,
    MODE_LIVE_DEBUG
};

class DisplayManager
{
private:
    TFT_eSPI tft = TFT_eSPI();
    InitStage currentInitStage = INIT_BOOT;
    DisplayState currentDisplayState = DISPLAY_IDLE;
    DisplayMode currentMode = MODE_DEBUG; // Default to debug mode
    String errorMessage = "";
    int sampleCount = 0;
    String configString = ""; // For displaying config during recording

    // Cached config values for display
    uint16_t cachedSampleRate = 1000;
    String cachedLedCurrent = "200mA";
    String cachedIntegrationTime = "1T";
    String cachedDutyCycle = "1/40";
    bool cachedHighRes = true;
    bool cachedReadAmbient = true;
    uint32_t cachedI2cClock = 400;

    // Layout constants
    static const int SCREEN_WIDTH = 320;
    static const int SCREEN_HEIGHT = 170;
    static const int PROGRESS_BAR_Y = 20;
    static const int PROGRESS_BAR_HEIGHT = 40;

    // New layout: Header with status badge
    static const int HEADER_HEIGHT = 28;
    static const int STATUS_BADGE_X = 130; // After title
    static const int STATUS_BADGE_Y = 4;
    static const int STATUS_BADGE_W = 50;
    static const int STATUS_BADGE_H = 20;

    // Config area (center of screen)
    static const int CONFIG_AREA_Y = 35;
    static const int CONFIG_AREA_HEIGHT = 100;

    // Message area at bottom
    static const int MESSAGE_Y = 145;

    // Drawing helpers
    void drawProgressBar();
    void drawSessionStatus();
    void drawStatusBadge(); // New: compact status in header
    void drawConfigPanel(); // New: config display in center
    void drawCheckmark(int x, int y, uint16_t color);
    void drawModeBadge();

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
    void setConfigString(const String &config);              // Legacy: Set config string for display
    void setSensorConfig(const SensorConfiguration *config); // New: Set full config for display
    void setMode(DisplayMode mode);                          // Set current device mode (idle/debug/play)

    // Legacy compatibility (for gradual migration)
    void showBootScreen();
    void updateStatus(const String &status, uint16_t color = TFT_WHITE);
    void showNetworkInfo(const String &ip, int rssi);
    void showMQTTStatus(bool connected);
    void clear();

    // Calibration display
    void showCalibrationIntro();
    void showCalibrationBaseline(uint8_t pcbId, uint8_t progress);
    void showCalibrationApproach(uint8_t pcbId, uint16_t currentReading, uint16_t threshold, uint8_t progress, uint32_t timeRemaining);
    void showCalibrationSuccess(uint8_t pcbId);
    void showCalibrationFailed(uint8_t pcbId, const String &reason = "Timeout");
    void showCalibrationSummary(uint16_t threshold1, uint16_t threshold2, uint16_t threshold3, bool valid1 = true, bool valid2 = true, bool valid3 = true);
    void showCalibrationComplete();
    void showCalibrationCancelled();
};

#endif
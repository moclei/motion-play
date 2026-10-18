#ifndef DISPLAY_MANAGER_H
#define DISPLAY_MANAGER_H

#include <Arduino.h>

// Forward declarations
struct SensorConfiguration;
enum class CalibrationState : uint8_t;

// Initialization stages - always available (used by main.cpp logic)
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

#ifdef HAS_DISPLAY

#include <TFT_eSPI.h>

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

    // Cached detection config values
    float cachedPeakMultiplier = 1.5f;
    uint16_t cachedMinRise = 10;
    uint32_t cachedMinWaveDurationMs = 8;
    uint8_t cachedSmoothingWindow = 5;

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

    // Power monitoring cached values
    float cachedPowerVoltage = 0.0f;
    float cachedPowerCurrentMA = 0.0f;
    bool powerMonitorActive = false;

    // Drawing helpers
    void drawProgressBar();
    void drawSessionStatus();
    void drawStatusBadge(); // New: compact status in header
    void drawConfigPanel(); // New: config display in center
    void drawPowerStatus(); // Power monitor readout
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
    void setSensorConfig(const SensorConfiguration *config);
    void setDetectionConfig(float peakMult, uint16_t minRise, uint32_t minWaveDurMs, uint8_t smoothWin);
    void setMode(DisplayMode mode);

    // Power monitoring display
    void updatePowerStatus(float vsysVoltage, float currentMA);

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

#else // !HAS_DISPLAY

// Color constant stubs so call sites compile without TFT_eSPI
#ifndef TFT_WHITE
#define TFT_WHITE      0xFFFF
#define TFT_BLACK      0x0000
#define TFT_RED        0xF800
#define TFT_GREEN      0x07E0
#define TFT_BLUE       0x001F
#define TFT_YELLOW     0xFFE0
#define TFT_ORANGE     0xFDA0
#define TFT_CYAN       0x07FF
#define TFT_MAGENTA    0xF81F
#define TFT_DARKGREY   0x7BEF
#endif

// No-op stub — all methods compile away to nothing
class DisplayManager
{
public:
    void init() {}
    void showInitScreen() {}
    void updateInitStage(InitStage stage, const String &message = "") {}
    void setInitError(const String &error) {}
    void showSessionScreen() {}
    void setDisplayState(DisplayState state) {}
    void updateSampleCount(int count) {}
    void showMessage(const String &message, uint16_t color = 0xFFFF) {}
    void setConfigString(const String &config) {}
    void setSensorConfig(const SensorConfiguration *config) {}
    void setDetectionConfig(float peakMult, uint16_t minRise, uint32_t minWaveDurMs, uint8_t smoothWin) {}
    void setMode(DisplayMode mode) {}
    void updatePowerStatus(float vsysVoltage, float currentMA) {}
    void showBootScreen() {}
    void updateStatus(const String &status, uint16_t color = 0xFFFF) {}
    void showNetworkInfo(const String &ip, int rssi) {}
    void showMQTTStatus(bool connected) {}
    void clear() {}
    void showCalibrationIntro() {}
    void showCalibrationBaseline(uint8_t pcbId, uint8_t progress) {}
    void showCalibrationApproach(uint8_t pcbId, uint16_t currentReading, uint16_t threshold, uint8_t progress, uint32_t timeRemaining) {}
    void showCalibrationSuccess(uint8_t pcbId) {}
    void showCalibrationFailed(uint8_t pcbId, const String &reason = "Timeout") {}
    void showCalibrationSummary(uint16_t threshold1, uint16_t threshold2, uint16_t threshold3, bool valid1 = true, bool valid2 = true, bool valid3 = true) {}
    void showCalibrationComplete() {}
    void showCalibrationCancelled() {}
};

#endif // HAS_DISPLAY

#endif // DISPLAY_MANAGER_H

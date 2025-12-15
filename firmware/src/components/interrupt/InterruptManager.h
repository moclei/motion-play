/**
 * InterruptManager - Hardware Interrupt-Based Sensor Detection
 *
 * This component manages interrupt-driven object detection using the VCNL4040
 * sensors' hardware interrupt feature. Unlike the polling-based SensorManager,
 * this waits for the sensor to signal detection via GPIO interrupts.
 *
 * Hardware Configuration:
 *   - GPIO 11 (PIN_SENSOR_INT_1): Sensor board 1 (TCA channel 0) - P1S1 & P1S2
 *   - GPIO 12 (PIN_SENSOR_INT_2): Sensor board 2 (TCA channel 1) - P2S1 & P2S2
 *   - GPIO 13 (PIN_SENSOR_INT_3): Sensor board 3 (TCA channel 2) - P3S1 & P3S2
 *
 * Note: Each GPIO receives combined interrupts from 2 sensors on the same board
 * (via Schottky diode OR-ing on the sensor PCB). When an interrupt fires, we
 * must scan both sensors on that board to determine which one(s) triggered.
 *
 * Operation Modes:
 *   1. Normal Interrupt Mode: INT fires on threshold crossing, must read flag to clear
 *   2. Logic Output Mode: INT stays LOW while object present, goes HIGH when away
 *
 * Usage:
 *   InterruptManager intMgr;
 *   intMgr.begin();
 *   intMgr.configureForDetection(threshold, mode);
 *   intMgr.startMonitoring();
 *
 *   // In main loop:
 *   while (intMgr.hasEvents()) {
 *       InterruptEvent evt = intMgr.getNextEvent();
 *       // Process event...
 *   }
 */

#pragma once

#include <Arduino.h>
#include <freertos/FreeRTOS.h>
#include <freertos/queue.h>
#include <freertos/task.h>
#include "../mux/MuxController.h"
#include "../vcnl4040/VCNL4040.h"
#include "pin_config.h"

// ============================================================================
// Configuration
// ============================================================================

// Event buffer size (number of events that can be queued)
#define INT_EVENT_BUFFER_SIZE 256

// Maximum time to wait for event processing (ms)
#define INT_PROCESSING_TIMEOUT_MS 10

// Default detection threshold (margin above/below calibrated baseline)
// Based on actual measurements: objects at 250mm produce only 8-25 counts above baseline
#define INT_DEFAULT_THRESHOLD_MARGIN 10 // Trigger when proximity increases by 10+ (very sensitive)
#define INT_DEFAULT_HYSTERESIS 5        // Small gap to allow re-triggering

// Calibration settings
#define INT_CALIBRATION_DURATION_MS 1000      // Calibration duration per sensor (1 second)
#define INT_CALIBRATION_SAMPLE_INTERVAL_MS 20 // Sample every 20ms (~50 samples per sensor)

// ============================================================================
// Data Types
// ============================================================================

/**
 * Type of interrupt event
 */
enum class InterruptEventType : uint8_t
{
    CLOSE,  // Object approached (PS > high threshold)
    AWAY,   // Object moved away (PS < low threshold)
    UNKNOWN // Couldn't determine (e.g., flag already cleared)
};

/**
 * Interrupt event data
 * This is what gets stored when an interrupt fires
 */
struct InterruptEvent
{
    uint32_t timestamp_us;   // Microseconds since start of session
    uint8_t boardId;         // Which board triggered (1-3)
    uint8_t sensorId;        // Which sensor triggered (0-5 position, or 255 if unknown)
    InterruptEventType type; // CLOSE or AWAY
    uint8_t rawFlags;        // Raw INT_FLAG register value for debugging

    // Helper to get sensor name
    String getSensorName() const
    {
        if (sensorId < 6)
        {
            uint8_t pcb = (sensorId / 2) + 1;
            uint8_t side = (sensorId % 2) + 1;
            return "P" + String(pcb) + "S" + String(side);
        }
        return "B" + String(boardId) + "?";
    }
};

/**
 * Interrupt detection mode
 */
enum class InterruptMode : uint8_t
{
    NORMAL,      // Standard interrupt mode - fires once per threshold crossing
    LOGIC_OUTPUT // Logic mode - INT stays LOW while object present
};

/**
 * Interrupt configuration
 */
struct InterruptConfig
{
    uint16_t thresholdMargin; // Detection margin above calibrated baseline
    uint16_t hysteresis;      // Gap between high and low thresholds
    uint8_t persistence;      // Consecutive hits before interrupt (1-4)
    bool smartPersistence;    // Enable fast response mode
    InterruptMode mode;       // NORMAL or LOGIC_OUTPUT
    uint16_t ledCurrent;      // LED current in mA (50-200)
    uint8_t integrationTime;  // Integration time (1, 2, 3, 4, or 8 for 1T-8T)
    uint8_t multiPulse;       // Multi-pulse count (1, 2, 4, or 8) - more pulses = stronger signal
    bool autoCalibrate;       // Whether to auto-calibrate on configure()

    // Default configuration - optimized for maximum detection range
    static InterruptConfig defaults()
    {
        return {
            INT_DEFAULT_THRESHOLD_MARGIN,
            INT_DEFAULT_HYSTERESIS,
            1,    // 1 hit persistence
            true, // Smart persistence enabled
            InterruptMode::NORMAL,
            200, // 200mA LED current (max)
            8,   // 8T integration (max sensitivity)
            8,   // 8 pulses (max signal strength)
            true // Auto-calibrate enabled
        };
    }
};

/**
 * Session statistics
 */
struct InterruptSessionStats
{
    uint32_t totalEvents;
    uint32_t closeEvents;
    uint32_t awayEvents;
    uint32_t unknownEvents;
    uint32_t droppedEvents;    // Events lost due to full buffer
    uint32_t isrCount;         // Total ISR invocations
    uint32_t sessionStartTime; // millis() when session started
};

// ============================================================================
// InterruptManager Class
// ============================================================================

class InterruptManager
{
public:
    /**
     * Constructor
     */
    InterruptManager();

    /**
     * Destructor - cleans up resources
     */
    ~InterruptManager();

    /**
     * Initialize the interrupt manager
     * @return true if successful
     */
    bool begin();

    /**
     * Configure sensors for interrupt-based detection
     * @param config Configuration parameters
     * @return true if all sensors configured successfully
     */
    bool configure(const InterruptConfig &config);

    /**
     * Start monitoring for interrupts
     * This enables GPIO interrupts and starts the processing task
     * @return true if successful
     */
    bool startMonitoring();

    /**
     * Stop monitoring
     * Disables GPIO interrupts and stops the processing task
     */
    void stopMonitoring();

    /**
     * Check if currently monitoring
     * @return true if monitoring is active
     */
    bool isMonitoring() const { return _monitoring; }

    /**
     * Check if there are events waiting
     * @return true if events available
     */
    bool hasEvents() const;

    /**
     * Get the next event from the queue
     * @param event Output parameter for the event
     * @param timeout_ms Maximum time to wait (0 = no wait)
     * @return true if event retrieved
     */
    bool getNextEvent(InterruptEvent &event, uint32_t timeout_ms = 0);

    /**
     * Get number of events in queue
     * @return Number of pending events
     */
    uint32_t getEventCount() const;

    /**
     * Clear all pending events
     */
    void clearEvents();

    /**
     * Get session statistics
     * @return Current session stats
     */
    InterruptSessionStats getStats() const { return _stats; }

    /**
     * Reset session statistics
     */
    void resetStats();

    /**
     * Get reference to MuxController (for advanced use)
     */
    MuxController &getMux() { return _mux; }

    /**
     * Get current configuration
     */
    InterruptConfig getConfig() const { return _config; }

    /**
     * Calibrate all sensors and set dynamic thresholds
     * This measures baseline proximity (with cover, no objects) and:
     *   1. Writes baseline to PS_CANC register (hardware subtraction)
     *   2. Sets high threshold = margin above zero (since PS_CANC subtracts baseline)
     *   3. Sets low threshold = high - hysteresis
     *
     * @return Number of sensors successfully calibrated
     */
    int calibrateSensors();

    /**
     * Get the calibrated baseline value for a sensor
     * @param position Sensor position (0-5)
     * @return Baseline value, or 0 if not calibrated
     */
    uint16_t getBaseline(uint8_t position) const;

private:
    MuxController _mux;
    VCNL4040 _sensors[MUX_TOTAL_SENSORS];
    InterruptConfig _config;
    InterruptSessionStats _stats;

    // Calibrated baseline values per sensor
    uint16_t _baselines[MUX_TOTAL_SENSORS];
    bool _calibrated;

    volatile bool _monitoring;
    QueueHandle_t _eventQueue;
    TaskHandle_t _processingTask;

    // ISR tracking - volatile because accessed from ISR
    volatile uint32_t _lastIsrTime[MUX_NUM_BOARDS];
    volatile bool _isrPending[MUX_NUM_BOARDS];

    // Session timing
    uint32_t _sessionStartUs;

    /**
     * Configure a single sensor for interrupt mode
     * @param position Sensor position (0-5)
     * @return true if successful
     */
    bool configureSensor(uint8_t position);

    /**
     * Process pending interrupts from a specific board
     * Called from processing task, not ISR
     * @param board Board index (0-2)
     */
    void processBoard(uint8_t board);

    /**
     * Read and process interrupt flags from a sensor
     * @param position Sensor position (0-5)
     * @param timestamp_us Event timestamp
     * @return true if event was generated
     */
    bool processSensor(uint8_t position, uint32_t timestamp_us);

    /**
     * Add event to queue
     * @param event Event to add
     * @return true if added, false if queue full
     */
    bool queueEvent(const InterruptEvent &event);

    /**
     * Processing task function (static for FreeRTOS)
     */
    static void processingTaskFunc(void *param);

    /**
     * GPIO interrupt service routines (static for ESP-IDF)
     */
    static void IRAM_ATTR isrBoard1();
    static void IRAM_ATTR isrBoard2();
    static void IRAM_ATTR isrBoard3();

    /**
     * Common ISR handler
     * @param board Board index (0-2)
     */
    static void IRAM_ATTR handleIsr(uint8_t board);

    // Singleton instance pointer for ISR access
    static InterruptManager *_instance;
};

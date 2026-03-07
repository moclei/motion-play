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
#include "../calibration/CalibrationData.h"
#include "pin_config.h"
#include "interrupt_types.h"

// ============================================================================
// Configuration
// ============================================================================

#define INT_EVENT_BUFFER_SIZE 256
#define INT_PROCESSING_TIMEOUT_MS 10
#define INT_CALIBRATION_DURATION_MS 1000
#define INT_CALIBRATION_SAMPLE_INTERVAL_MS 20

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

    /**
     * Set external calibration data
     * When set, thresholds will be derived from the calibration data
     * instead of using margin + hysteresis on measured baseline.
     * @param cal Pointer to calibration data (can be nullptr to clear)
     */
    void setCalibration(const DeviceCalibration *cal);

    /**
     * Check if using external calibration
     */
    bool isUsingCalibration() const { return _externalCalibration != nullptr && _externalCalibration->isValid(); }

private:
    MuxController _mux;
    VCNL4040 _sensors[MUX_TOTAL_SENSORS];
    InterruptConfig _config;
    InterruptSessionStats _stats;

    // Calibrated baseline values per sensor
    uint16_t _baselines[MUX_TOTAL_SENSORS];
    bool _calibrated;
    
    // External calibration data (from CalibrationManager)
    const DeviceCalibration *_externalCalibration = nullptr;

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

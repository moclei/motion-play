/**
 * MuxController - Shared TCA9548A + PCA9546A Multiplexer Handling
 * 
 * This component manages the dual-multiplexer architecture used in Motion Play:
 *   - TCA9548A on main board: Selects which sensor board (0, 1, 2)
 *   - PCA9546A on each sensor board: Selects which sensor (0 = S1, 1 = S2)
 * 
 * Architecture:
 *   MCU I2C → TCA9548A → [Sensor Board 0] → PCA9546A → VCNL4040 S1/S2
 *                      → [Sensor Board 1] → PCA9546A → VCNL4040 S1/S2
 *                      → [Sensor Board 2] → PCA9546A → VCNL4040 S1/S2
 * 
 * Usage:
 *   MuxController mux;
 *   mux.begin();
 *   mux.selectSensor(2);  // Select P2S1 (sensor position 2)
 *   // ... communicate with sensor at 0x60 ...
 *   mux.disableAll();
 */

#pragma once

#include <Arduino.h>
#include <Wire.h>

// Number of sensor boards and sensors per board
#define MUX_NUM_BOARDS 3
#define MUX_SENSORS_PER_BOARD 2
#define MUX_TOTAL_SENSORS (MUX_NUM_BOARDS * MUX_SENSORS_PER_BOARD)

// Default I2C addresses
#define TCA9548A_DEFAULT_ADDR 0x70
#define VCNL4040_ADDR 0x60

/**
 * Sensor position mapping
 * Position 0-5 maps to specific TCA channel (board) and PCA channel (sensor)
 */
struct SensorPosition {
    uint8_t position;     // 0-5 (overall sensor index)
    uint8_t tcaChannel;   // 0-2 (which sensor board)
    uint8_t pcaChannel;   // 0-1 (which sensor on board: S1=0, S2=1)
    uint8_t pcbId;        // 1-3 (human-readable board number)
    uint8_t side;         // 1-2 (human-readable sensor side)
    
    String getName() const {
        return "P" + String(pcbId) + "S" + String(side);
    }
};

/**
 * Board discovery result
 */
struct BoardInfo {
    uint8_t tcaChannel;   // TCA channel this board is on
    uint8_t pcaAddress;   // Detected PCA9546A address (0 if not found)
    bool sensor1Present;  // Is S1 present?
    bool sensor2Present;  // Is S2 present?
};

class MuxController {
public:
    /**
     * Constructor
     * @param tcaAddress I2C address of TCA9548A (default 0x70)
     */
    MuxController(uint8_t tcaAddress = TCA9548A_DEFAULT_ADDR);
    
    /**
     * Initialize I2C and scan for sensor boards
     * @param sda SDA pin (default -1 = don't reinitialize I2C)
     * @param scl SCL pin (default -1 = don't reinitialize I2C)
     * @param clockHz I2C clock speed (default 400000 = 400kHz)
     * @return true if at least one sensor board found
     */
    bool begin(int sda = -1, int scl = -1, uint32_t clockHz = 400000);
    
    /**
     * Select a specific sensor by position (0-5)
     * This sets up both TCA and PCA channels so the sensor at 0x60 is accessible
     * @param position Sensor position (0=P1S1, 1=P1S2, 2=P2S1, 3=P2S2, 4=P3S1, 5=P3S2)
     * @return true if successful
     */
    bool selectSensor(uint8_t position);
    
    /**
     * Select a specific sensor by board and sensor index
     * @param board Board index (0-2)
     * @param sensor Sensor index (0-1)
     * @return true if successful
     */
    bool selectSensor(uint8_t board, uint8_t sensor);
    
    /**
     * Select TCA channel only (doesn't touch PCA)
     * @param channel TCA channel (0-7)
     * @return true if successful
     */
    bool selectTCAChannel(uint8_t channel);
    
    /**
     * Select PCA channel on currently selected board
     * @param channel PCA channel (0-3)
     * @return true if successful
     */
    bool selectPCAChannel(uint8_t channel);
    
    /**
     * Disable all channels on both TCA and all PCAs
     * This releases the I2C bus
     */
    void disableAll();
    
    /**
     * Disable all PCA channels on currently selected TCA channel
     */
    void disableCurrentPCA();
    
    /**
     * Get sensor position info
     * @param position Sensor position (0-5)
     * @return SensorPosition struct with mapping info
     */
    SensorPosition getSensorPosition(uint8_t position) const;
    
    /**
     * Check if a sensor is available
     * @param position Sensor position (0-5)
     * @return true if sensor was found during initialization
     */
    bool isSensorAvailable(uint8_t position) const;
    
    /**
     * Get board info
     * @param board Board index (0-2)
     * @return BoardInfo struct
     */
    BoardInfo getBoardInfo(uint8_t board) const;
    
    /**
     * Get number of active sensors
     * @return Count of sensors that responded during initialization
     */
    uint8_t getActiveSensorCount() const;
    
    /**
     * Get the currently selected TCA channel
     * @return Current TCA channel (0-7) or 255 if none selected
     */
    uint8_t getCurrentTCAChannel() const { return _currentTCAChannel; }
    
    /**
     * Get the currently selected PCA channel
     * @return Current PCA channel (0-3) or 255 if none selected
     */
    uint8_t getCurrentPCAChannel() const { return _currentPCAChannel; }

private:
    uint8_t _tcaAddress;
    uint8_t _currentTCAChannel;
    uint8_t _currentPCAChannel;
    
    // Board discovery results
    BoardInfo _boards[MUX_NUM_BOARDS];
    bool _sensorsActive[MUX_TOTAL_SENSORS];
    uint8_t _activeSensorCount;
    
    // Sensor position mapping (constant)
    static const SensorPosition _sensorMap[MUX_TOTAL_SENSORS];
    
    /**
     * Scan for PCA9546A on a specific TCA channel
     * @param tcaChannel TCA channel to scan
     * @return Detected PCA address (0 if not found)
     */
    uint8_t scanForPCA(uint8_t tcaChannel);
    
    /**
     * Check if a VCNL4040 is present at 0x60
     * @return true if sensor responds
     */
    bool checkVCNL4040Present();
    
    /**
     * Send channel selection to TCA9548A
     * @param channelMask Bitmask of channels to enable
     * @return true if successful
     */
    bool writeTCA(uint8_t channelMask);
    
    /**
     * Send channel selection to PCA9546A
     * @param address PCA9546A address
     * @param channelMask Bitmask of channels to enable
     * @return true if successful
     */
    bool writePCA(uint8_t address, uint8_t channelMask);
};


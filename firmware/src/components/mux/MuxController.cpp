/**
 * MuxController - Implementation
 * 
 * See MuxController.h for documentation.
 */

#include "MuxController.h"

// Static sensor position mapping
// Position -> (tcaChannel, pcaChannel, pcbId, side)
const SensorPosition MuxController::_sensorMap[MUX_TOTAL_SENSORS] = {
    {0, 0, 0, 1, 1},  // Position 0: P1S1 (TCA0, PCA0)
    {1, 0, 1, 1, 2},  // Position 1: P1S2 (TCA0, PCA1)
    {2, 1, 0, 2, 1},  // Position 2: P2S1 (TCA1, PCA0)
    {3, 1, 1, 2, 2},  // Position 3: P2S2 (TCA1, PCA1)
    {4, 2, 0, 3, 1},  // Position 4: P3S1 (TCA2, PCA0)
    {5, 2, 1, 3, 2}   // Position 5: P3S2 (TCA2, PCA1)
};

MuxController::MuxController(uint8_t tcaAddress) 
    : _tcaAddress(tcaAddress)
    , _currentTCAChannel(255)
    , _currentPCAChannel(255)
    , _activeSensorCount(0)
{
    // Initialize boards array
    for (int i = 0; i < MUX_NUM_BOARDS; i++) {
        _boards[i].tcaChannel = i;
        _boards[i].pcaAddress = 0;
        _boards[i].sensor1Present = false;
        _boards[i].sensor2Present = false;
    }
    
    // Initialize sensors as inactive
    for (int i = 0; i < MUX_TOTAL_SENSORS; i++) {
        _sensorsActive[i] = false;
    }
}

bool MuxController::begin(int sda, int scl, uint32_t clockHz)
{
    Serial.println("MuxController: Initializing...");
    
    // Initialize I2C if pins provided
    if (sda >= 0 && scl >= 0) {
        Wire.begin(sda, scl);
        Wire.setClock(clockHz);
        Serial.printf("  I2C initialized: SDA=%d, SCL=%d, Clock=%luHz\n", sda, scl, clockHz);
    }
    
    // Check if TCA9548A is present
    Wire.beginTransmission(_tcaAddress);
    if (Wire.endTransmission() != 0) {
        Serial.printf("  ERROR: TCA9548A not found at 0x%02X\n", _tcaAddress);
        return false;
    }
    Serial.printf("  TCA9548A found at 0x%02X\n", _tcaAddress);
    
    // Disable all TCA channels initially
    writeTCA(0x00);
    delay(10);
    
    // Scan each TCA channel for PCA9546A and sensors
    _activeSensorCount = 0;
    
    for (uint8_t board = 0; board < MUX_NUM_BOARDS; board++) {
        Serial.printf("  Scanning TCA channel %d...\n", board);
        
        // Select TCA channel
        if (!selectTCAChannel(board)) {
            Serial.printf("    Failed to select TCA channel %d\n", board);
            continue;
        }
        delay(10);
        
        // Scan for PCA9546A
        uint8_t pcaAddr = scanForPCA(board);
        _boards[board].pcaAddress = pcaAddr;
        
        if (pcaAddr == 0) {
            Serial.println("    No PCA9546A found");
            continue;
        }
        
        Serial.printf("    PCA9546A found at 0x%02X\n", pcaAddr);
        
        // Check each sensor on this board
        for (uint8_t sensor = 0; sensor < MUX_SENSORS_PER_BOARD; sensor++) {
            // Select PCA channel
            if (!writePCA(pcaAddr, 1 << sensor)) {
                continue;
            }
            delay(10);
            
            // Check for VCNL4040
            bool present = checkVCNL4040Present();
            uint8_t position = board * MUX_SENSORS_PER_BOARD + sensor;
            
            _sensorsActive[position] = present;
            if (sensor == 0) {
                _boards[board].sensor1Present = present;
            } else {
                _boards[board].sensor2Present = present;
            }
            
            if (present) {
                _activeSensorCount++;
                Serial.printf("    Sensor S%d (pos %d): FOUND\n", sensor + 1, position);
            } else {
                Serial.printf("    Sensor S%d (pos %d): not present\n", sensor + 1, position);
            }
        }
        
        // Disable PCA channels on this board
        writePCA(pcaAddr, 0x00);
    }
    
    // Disable all channels
    disableAll();
    
    Serial.printf("MuxController: Found %d sensors\n", _activeSensorCount);
    return _activeSensorCount > 0;
}

bool MuxController::selectSensor(uint8_t position)
{
    if (position >= MUX_TOTAL_SENSORS) {
        return false;
    }
    
    const SensorPosition& pos = _sensorMap[position];
    return selectSensor(pos.tcaChannel, pos.pcaChannel);
}

bool MuxController::selectSensor(uint8_t board, uint8_t sensor)
{
    if (board >= MUX_NUM_BOARDS || sensor >= MUX_SENSORS_PER_BOARD) {
        return false;
    }
    
    // Check if board has a PCA
    if (_boards[board].pcaAddress == 0) {
        return false;
    }
    
    // If switching TCA channels, disable current PCA first
    if (_currentTCAChannel != 255 && _currentTCAChannel != board) {
        if (_boards[_currentTCAChannel].pcaAddress != 0) {
            // Need to select old TCA channel to disable its PCA
            writeTCA(1 << _currentTCAChannel);
            delayMicroseconds(100);
            writePCA(_boards[_currentTCAChannel].pcaAddress, 0x00);
        }
    }
    
    // Select TCA channel
    if (!selectTCAChannel(board)) {
        return false;
    }
    
    // Select PCA channel
    if (!selectPCAChannel(sensor)) {
        return false;
    }
    
    return true;
}

bool MuxController::selectTCAChannel(uint8_t channel)
{
    if (channel > 7) {
        return false;
    }
    
    if (!writeTCA(1 << channel)) {
        return false;
    }
    
    _currentTCAChannel = channel;
    _currentPCAChannel = 255; // Reset PCA selection when TCA changes
    return true;
}

bool MuxController::selectPCAChannel(uint8_t channel)
{
    if (channel > 3) {
        return false;
    }
    
    // Make sure we have a valid TCA channel selected
    if (_currentTCAChannel >= MUX_NUM_BOARDS) {
        return false;
    }
    
    uint8_t pcaAddr = _boards[_currentTCAChannel].pcaAddress;
    if (pcaAddr == 0) {
        return false;
    }
    
    if (!writePCA(pcaAddr, 1 << channel)) {
        return false;
    }
    
    _currentPCAChannel = channel;
    return true;
}

void MuxController::disableAll()
{
    // IMPORTANT: Must select each TCA channel before disabling its PCA
    // This is required because PCA is only accessible through its TCA channel
    for (uint8_t board = 0; board < MUX_NUM_BOARDS; board++) {
        if (_boards[board].pcaAddress != 0) {
            writeTCA(1 << board);
            delayMicroseconds(100);
            writePCA(_boards[board].pcaAddress, 0x00);
        }
    }
    
    // Disable all TCA channels
    writeTCA(0x00);
    _currentTCAChannel = 255;
    _currentPCAChannel = 255;
}

void MuxController::disableCurrentPCA()
{
    if (_currentTCAChannel < MUX_NUM_BOARDS) {
        uint8_t pcaAddr = _boards[_currentTCAChannel].pcaAddress;
        if (pcaAddr != 0) {
            writePCA(pcaAddr, 0x00);
        }
    }
    _currentPCAChannel = 255;
}

SensorPosition MuxController::getSensorPosition(uint8_t position) const
{
    if (position >= MUX_TOTAL_SENSORS) {
        // Return invalid position
        return {255, 255, 255, 255, 255};
    }
    return _sensorMap[position];
}

bool MuxController::isSensorAvailable(uint8_t position) const
{
    if (position >= MUX_TOTAL_SENSORS) {
        return false;
    }
    return _sensorsActive[position];
}

BoardInfo MuxController::getBoardInfo(uint8_t board) const
{
    if (board >= MUX_NUM_BOARDS) {
        return {255, 0, false, false};
    }
    return _boards[board];
}

uint8_t MuxController::getActiveSensorCount() const
{
    return _activeSensorCount;
}

// ============================================================================
// Private Methods
// ============================================================================

uint8_t MuxController::scanForPCA(uint8_t tcaChannel)
{
    // Common PCA9546A addresses to try
    const uint8_t addresses[] = {0x70, 0x71, 0x72, 0x73, 0x74, 0x75, 0x76, 0x77};
    
    for (int i = 0; i < 8; i++) {
        // Skip TCA address
        if (addresses[i] == _tcaAddress) {
            continue;
        }
        
        Wire.beginTransmission(addresses[i]);
        if (Wire.endTransmission() == 0) {
            return addresses[i];
        }
    }
    
    return 0; // Not found
}

bool MuxController::checkVCNL4040Present()
{
    // Try to read device ID register (0x0C)
    Wire.beginTransmission(VCNL4040_ADDR);
    Wire.write(0x0C);
    if (Wire.endTransmission(false) != 0) {
        return false;
    }
    
    Wire.requestFrom((uint8_t)VCNL4040_ADDR, (uint8_t)2);
    if (Wire.available() < 2) {
        return false;
    }
    
    uint8_t idLow = Wire.read();
    uint8_t idHigh = Wire.read();
    uint16_t deviceId = ((uint16_t)idHigh << 8) | idLow;
    
    return (deviceId == 0x0186);
}

bool MuxController::writeTCA(uint8_t channelMask)
{
    Wire.beginTransmission(_tcaAddress);
    Wire.write(channelMask);
    return (Wire.endTransmission() == 0);
}

bool MuxController::writePCA(uint8_t address, uint8_t channelMask)
{
    Wire.beginTransmission(address);
    Wire.write(channelMask);
    return (Wire.endTransmission() == 0);
}


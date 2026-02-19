#ifndef SERIAL_STUDIO_OUTPUT_H
#define SERIAL_STUDIO_OUTPUT_H

#include <Arduino.h>
#include "../sensor/SensorManager.h"
#include "../memory/PSRAMAllocator.h"

class SerialStudioOutput
{
private:
    // Reference to the session data buffer (owned by SessionManager)
    std::vector<SensorReading, PSRAMAllocator<SensorReading>> *_buffer = nullptr;
    bool _enabled = false;

    // Buffer read tracking
    size_t _lastProcessedIndex = 0;

    // Frame accumulator: one slot per sensor position (0-5)
    uint16_t _accumulator[NUM_SENSORS] = {0};
    bool _slotFilled[NUM_SENSORS] = {false};
    uint32_t _currentTimestamp = 0;
    bool _hasPendingFrame = false;

    void emitFrame();
    void resetAccumulator(uint32_t newTimestamp);

public:
    /**
     * Initialize with a reference to the session data buffer.
     * Call once after SessionManager is ready.
     */
    void begin(std::vector<SensorReading, PSRAMAllocator<SensorReading>> *buffer);

    /**
     * Enable or disable serial studio output at runtime.
     */
    void setEnabled(bool enabled) { _enabled = enabled; }
    bool isEnabled() const { return _enabled; }

    /**
     * Process new readings from the buffer and emit CSV frames.
     * Call once per Core 1 loop iteration, after sessionManager.processQueue().
     */
    void update();

    /**
     * Reset read index and accumulator state.
     * Call when the buffer is cleared externally (detection events, overflow).
     */
    void resetIndex();
};

#endif

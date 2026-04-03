#pragma once

#include "../mux/MuxController.h"
#include "../vcnl4040/VCNL4040.h"

struct SensorConfiguration;

class SensorDiagnostics {
public:
    SensorDiagnostics(MuxController& mux, VCNL4040& vcnl);

    void i2cBusScan();
    void dumpConfiguration(SensorConfiguration* config);

private:
    MuxController& _mux;
    VCNL4040& _vcnl;

    static uint8_t ledCurrentStringToRegBits(const String& current);
};

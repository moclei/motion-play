#ifndef POWER_MONITOR_H
#define POWER_MONITOR_H

#include <Arduino.h>
#include <Wire.h>

// INA219 I2C address (A0=GND, A1=GND on v6 main PCB)
#define INA219_ADDR 0x40

// INA219 register addresses
#define INA219_REG_CONFIG      0x00
#define INA219_REG_SHUNT_V     0x01
#define INA219_REG_BUS_V       0x02
#define INA219_REG_POWER       0x03
#define INA219_REG_CURRENT     0x04
#define INA219_REG_CALIBRATION 0x05

/**
 * Lightweight INA219 driver for VSYS rail monitoring.
 *
 * Hardware: INA219 (U7) with 10mΩ shunt (R44) between VSYS and VSYS_SENSE.
 * Configured for PGA /2 (+/-80mV range) → max ~8A measurable.
 * Bus voltage range set to 16V (BRNG=0) since VSYS is 3.0–4.5V.
 *
 * Calibration: with 10mΩ shunt and Current_LSB = 1mA,
 *   Cal = trunc(0.04096 / (1e-3 * 0.01)) = 4096
 */
class PowerMonitor
{
private:
    bool available = false;
    float busVoltage = 0.0f;   // VSYS voltage in V
    float currentMA = 0.0f;    // VSYS current in mA
    float shuntVoltage = 0.0f; // Shunt voltage in mV (for diagnostics)

    int16_t readRegister(uint8_t reg);
    void writeRegister(uint8_t reg, uint16_t value);

public:
    /**
     * Probe for INA219 and configure it.
     * Call after Wire.begin().
     * Returns true if INA219 was found and configured.
     */
    bool init();

    /**
     * Read latest voltage and current from INA219.
     * Updates cached values. Call periodically (e.g., every 500ms).
     */
    void update();

    /** VSYS bus voltage in volts */
    float getVoltage() const { return busVoltage; }

    /** VSYS current in milliamps */
    float getCurrentMA() const { return currentMA; }

    /** Whether INA219 was detected on the bus */
    bool isAvailable() const { return available; }
};

#endif

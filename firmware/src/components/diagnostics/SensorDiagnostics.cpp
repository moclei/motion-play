#include "SensorDiagnostics.h"
#include "../sensor/SensorConfiguration.h"
#include "sensor_types.h"

SensorDiagnostics::SensorDiagnostics(MuxController& mux, VCNL4040& vcnl)
    : _mux(mux), _vcnl(vcnl)
{
}

uint8_t SensorDiagnostics::ledCurrentStringToRegBits(const String& current)
{
    if (current == "50mA")  return VCNL4040_LED_I_50MA;
    if (current == "75mA")  return VCNL4040_LED_I_75MA;
    if (current == "100mA") return VCNL4040_LED_I_100MA;
    if (current == "120mA") return VCNL4040_LED_I_120MA;
    if (current == "140mA") return VCNL4040_LED_I_140MA;
    if (current == "160mA") return VCNL4040_LED_I_160MA;
    if (current == "180mA") return VCNL4040_LED_I_180MA;
    return VCNL4040_LED_I_200MA;
}

void SensorDiagnostics::i2cBusScan()
{
    Serial.println("\n");
    Serial.println("╔══════════════════════════════════════════════════════════════════════════════╗");
    Serial.println("║                        I2C DEBUG SCAN - TROUBLESHOOTING                      ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    Serial.println("║ STEP 1: Scanning main I2C bus (no TCA channel selected)                      ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    _mux.disableAll();
    delay(10);

    int mainBusDevices = 0;
    for (uint8_t addr = 0x08; addr <= 0x77; addr++)
    {
        Wire.beginTransmission(addr);
        uint8_t error = Wire.endTransmission();

        if (error == 0)
        {
            mainBusDevices++;
            const char *deviceName = "Unknown";
            if (addr == 0x70)
                deviceName = "TCA9548A (main mux)";
            else if (addr >= 0x71 && addr <= 0x77)
                deviceName = "Possible PCA9546A";
            else if (addr == VCNL4040_ADDR)
                deviceName = "VCNL4040";

            Serial.printf("║   Found device at 0x%02X - %s                            \n", addr, deviceName);
        }
    }

    if (mainBusDevices == 0)
    {
        Serial.println("║   ⚠️ No devices found on main I2C bus!                                      ║");
    }
    else
    {
        Serial.printf("║   Total: %d device(s) on main bus                                            \n", mainBusDevices);
    }

    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ STEP 2: Scanning each TCA9548A channel for connected devices                 ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    for (int tca_ch = 0; tca_ch < 8; tca_ch++)
    {
        Serial.printf("║ TCA Channel %d:                                                              \n", tca_ch);

        if (!_mux.selectTCAChannel(tca_ch))
        {
            Serial.println("║   ⚠️ Failed to select this channel!                                         ║");
            continue;
        }

        delay(20);

        int channelDevices = 0;
        for (uint8_t addr = 0x08; addr <= 0x77; addr++)
        {
            if (addr == 0x70)
                continue;

            Wire.beginTransmission(addr);
            uint8_t error = Wire.endTransmission();

            if (error == 0)
            {
                channelDevices++;
                const char *deviceName = "Unknown";
                if (addr >= 0x71 && addr <= 0x77)
                    deviceName = "PCA9546A?";
                else if (addr == 0x74)
                    deviceName = "PCA9546A (expected addr)";
                else if (addr == VCNL4040_ADDR)
                    deviceName = "VCNL4040";

                Serial.printf("║   ✓ Found: 0x%02X (%s)                                  \n", addr, deviceName);
            }
        }

        if (channelDevices == 0)
        {
            Serial.println("║   (no devices found)                                                        ║");
        }
    }

    _mux.disableAll();

    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ STEP 3: Direct PCA9546A address probe at 0x74 on TCA channel 0               ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    if (_mux.selectTCAChannel(0))
    {
        Serial.println("║   TCA channel 0 selected successfully                                       ║");
        delay(50);

        for (int attempt = 1; attempt <= 3; attempt++)
        {
            Wire.beginTransmission(0x74);
            uint8_t error = Wire.endTransmission();

            const char *errorStr = "Unknown";
            switch (error)
            {
            case 0:
                errorStr = "SUCCESS";
                break;
            case 1:
                errorStr = "Data too long";
                break;
            case 2:
                errorStr = "NACK on address";
                break;
            case 3:
                errorStr = "NACK on data";
                break;
            case 4:
                errorStr = "Other error";
                break;
            case 5:
                errorStr = "Timeout";
                break;
            }

            Serial.printf("║   Attempt %d: Address 0x74 -> Error %d (%s)                    \n",
                          attempt, error, errorStr);

            if (error == 0)
                break;
            delay(50);
        }

        Serial.println("║   Attempting to read control register from 0x74...                          ║");
        Wire.beginTransmission(0x74);
        uint8_t writeErr = Wire.endTransmission(false);

        if (writeErr == 0)
        {
            uint8_t bytesRead = Wire.requestFrom((uint8_t)0x74, (uint8_t)1);
            if (bytesRead > 0)
            {
                uint8_t controlReg = Wire.read();
                Serial.printf("║   ✓ Read success! Control register value: 0x%02X                          \n", controlReg);
            }
            else
            {
                Serial.println("║   ⚠️ Write OK but read returned 0 bytes                                    ║");
            }
        }
        else
        {
            Serial.printf("║   ⚠️ Write failed with error %d, skipping read                               \n", writeErr);
        }
    }
    else
    {
        Serial.println("║   ⚠️ Failed to select TCA channel 0!                                         ║");
    }

    _mux.disableAll();

    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ DEBUG SCAN COMPLETE - Check results above for clues                          ║");
    Serial.println("╚══════════════════════════════════════════════════════════════════════════════╝");
    Serial.println();
}

void SensorDiagnostics::dumpConfiguration(SensorConfiguration* config)
{
    Serial.println("\n");
    Serial.println("╔══════════════════════════════════════════════════════════════════════════════╗");
    Serial.println("║                    SENSOR CONFIGURATION DIAGNOSTIC DUMP                      ║");
    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");
    Serial.println("║ Sensor │ TCA │ PCA │ Active │ LED Current │ Integration │ Duty  │ HighRes  ║");
    Serial.println("╠════════╪═════╪═════╪════════╪═════════════╪═════════════╪═══════╪══════════╣");

    const char *led_current_names[] = {"50mA", "75mA", "100mA", "120mA", "140mA", "160mA", "180mA", "200mA"};
    const char *integration_names[] = {"1T", "1.5T", "2T", "2.5T", "3T", "3.5T", "4T", "8T"};
    const char *duty_names[] = {"1/40", "1/80", "1/160", "1/320"};

    int mismatches = 0;

    uint8_t expected_led_bits = VCNL4040_LED_I_200MA;
    if (config != nullptr)
    {
        expected_led_bits = ledCurrentStringToRegBits(config->led_current);
    }

    for (int i = 0; i < NUM_SENSORS; i++)
    {
        SensorPosition pos = _mux.getSensorPosition(i);
        uint8_t tca_ch = pos.tcaChannel;
        uint8_t pca_ch = pos.pcaChannel;

        char sensorName[8];
        snprintf(sensorName, sizeof(sensorName), "P%dS%d", pos.pcbId, pos.side);

        if (!_mux.isSensorAvailable(i))
        {
            Serial.printf("║ %-6s │  %d  │  %d  │   NO   │     N/A     │     N/A     │  N/A  │   N/A    ║\n",
                          sensorName, tca_ch, pca_ch);
            continue;
        }

        if (!_mux.selectSensor(i))
        {
            Serial.printf("║ %-6s │  %d  │  %d  │  YES   │  MUX ERR    │   MUX ERR   │ ERR   │   ERR    ║\n",
                          sensorName, tca_ch, pca_ch);
            continue;
        }
        delay(10);

        uint16_t device_id = _vcnl.getID();
        if (device_id != VCNL4040_ID_VALUE)
        {
            if (device_id == 0)
            {
                Serial.printf("║ %-6s │  %d  │  %d  │  YES   │  I2C ERR    │   I2C ERR   │ ERR   │   ERR    ║\n",
                              sensorName, tca_ch, pca_ch);
            }
            else
            {
                Serial.printf("║ %-6s │  %d  │  %d  │  YES   │ BAD ID 0x%04X                              ║\n",
                              sensorName, tca_ch, pca_ch, device_id);
            }
            continue;
        }

        uint16_t conf12_raw = _vcnl.readRegister(VCNL4040_PS_CONF1_2);
        uint16_t conf3ms_raw = _vcnl.readRegister(VCNL4040_PS_CONF3_MS);

        uint8_t ps_conf1_low = conf12_raw & 0xFF;
        uint8_t ps_conf1_high = (conf12_raw >> 8) & 0xFF;
        uint8_t ps_ms_high = (conf3ms_raw >> 8) & 0xFF;

        uint8_t duty_bits = (ps_conf1_low >> 6) & 0x03;
        uint8_t integration_bits = (ps_conf1_low >> 1) & 0x07;
        bool high_res = (ps_conf1_high >> 3) & 0x01;
        uint8_t led_current_bits = ps_ms_high & 0x07;

        const char *led_str = (led_current_bits < 8) ? led_current_names[led_current_bits] : "???";
        const char *int_str = (integration_bits < 8) ? integration_names[integration_bits] : "???";
        const char *duty_str = (duty_bits < 4) ? duty_names[duty_bits] : "???";

        bool led_match = true;
        if (config != nullptr)
        {
            if (led_current_bits != expected_led_bits)
            {
                led_match = false;
                mismatches++;
            }
        }

        Serial.printf("║ %-6s │  %d  │  %d  │  YES   │ %s %-7s %s │    %-6s   │ %-5s │   %-5s  ║\n",
                      sensorName, tca_ch, pca_ch,
                      led_match ? " " : "⚠",
                      led_str,
                      led_match ? " " : "⚠",
                      int_str, duty_str,
                      high_res ? "YES" : "NO");

        if (!led_match)
        {
            Serial.printf("║        │ RAW: PS_CONF1/2=0x%04X PS_CONF3/MS=0x%04X                            ║\n",
                          conf12_raw, conf3ms_raw);
        }
    }

    Serial.println("╠══════════════════════════════════════════════════════════════════════════════╣");

    if (config != nullptr)
    {
        Serial.printf("║ EXPECTED: LED=%-7s IT=%-5s Duty=%-5s MultiP=%sP HighRes=%-3s        ║\n",
                      config->led_current.c_str(),
                      config->integration_time.c_str(),
                      config->duty_cycle.c_str(),
                      config->multi_pulse.c_str(),
                      config->high_resolution ? "YES" : "NO");
    }
    else
    {
        Serial.println("║ EXPECTED: (no configuration provided - using defaults)                       ║");
    }

    if (mismatches > 0)
    {
        Serial.printf("║ ⚠️ WARNING: %d sensor(s) have configuration mismatches!                       ║\n", mismatches);
    }

    Serial.println("╚══════════════════════════════════════════════════════════════════════════════╝");
    Serial.println();

    _mux.disableAll();
}

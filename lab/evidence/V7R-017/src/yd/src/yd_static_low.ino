// V7R-017 dev-board static low build (card delta): holds GPIO43 or GPIO4 low
// as a plain open-drain GPIO output on a YD-ESP32-23 (ESP32-S3-WROOM-1-N16R8),
// so each pad's static low can be read with a DMM at the header pins.
// Derived from V7R-014 v7_static_low with Wire and the TCA step removed.
//
// Modes, chosen by one character on native USB serial (boot mode: r):
//   r  released: GPIO43 and GPIO4 as open-drain outputs, both high
//   3  GPIO43 low (GPIO4 high)
//   c  GPIO4 low (GPIO43 high), the control pad
// Every mode change prints [static] mode=<m> and a [regs] dump of both pads
// (as V7R-011/-014); the dump repeats every 2 s.
// Register writes: only through pinMode() and digitalWrite().

#include <Arduino.h>
#include <stdarg.h>
#include <stdio.h>
#include "soc/gpio_reg.h"
#include "soc/gpio_sig_map.h"
#include "soc/io_mux_reg.h"

#define STATIC_VERSION "1.0-yd"

static const int TEST_GPIO = 43;
static const int CTRL_GPIO = 4;

static char mode = 0;
static uint32_t lastDump = 0;

static void serialPrintf(const char *fmt, ...)
{
    char buf[160];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    Serial.print(buf);
}

static void dumpPad(int gpio, uint32_t ioMuxReg, uint32_t pinReg, uint32_t outSelReg)
{
    uint32_t mux = REG_READ(ioMuxReg);
    uint32_t pin = REG_READ(pinReg);
    uint32_t sel = REG_READ(outSelReg);
    bool hi = gpio >= 32;
    uint32_t bit = 1UL << (hi ? gpio - 32 : gpio);
    uint32_t en = REG_READ(hi ? GPIO_ENABLE1_REG : GPIO_ENABLE_REG);
    uint32_t out = REG_READ(hi ? GPIO_OUT1_REG : GPIO_OUT_REG);
    uint32_t in = REG_READ(hi ? GPIO_IN1_REG : GPIO_IN_REG);
    serialPrintf("[regs] gpio=%d mcu_sel=%lu fun_drv=%lu wpu=%lu wpd=%lu ie=%lu od=%lu out_sig=%lu oen_sel=%lu ",
                 gpio, (unsigned long)((mux >> MCU_SEL_S) & MCU_SEL_V), (unsigned long)((mux >> FUN_DRV_S) & FUN_DRV_V),
                 (unsigned long)((mux >> FUN_PU_S) & 1), (unsigned long)((mux >> FUN_PD_S) & 1),
                 (unsigned long)((mux >> FUN_IE_S) & 1), (unsigned long)((pin >> GPIO_PIN0_PAD_DRIVER_S) & 1),
                 (unsigned long)((sel >> GPIO_FUNC0_OUT_SEL_S) & GPIO_FUNC0_OUT_SEL_V),
                 (unsigned long)((sel >> GPIO_FUNC0_OEN_SEL_S) & 1));
    serialPrintf("oe=%d out=%d in=%d\n", (en & bit) ? 1 : 0, (out & bit) ? 1 : 0, (in & bit) ? 1 : 0);
}

static void dumpRegs()
{
    dumpPad(TEST_GPIO, IO_MUX_GPIO43_REG, GPIO_PIN43_REG, GPIO_FUNC43_OUT_SEL_CFG_REG);
    dumpPad(CTRL_GPIO, IO_MUX_GPIO4_REG, GPIO_PIN4_REG, GPIO_FUNC4_OUT_SEL_CFG_REG);
}

static void enterMode(char m)
{
    pinMode(TEST_GPIO, OUTPUT_OPEN_DRAIN);
    pinMode(CTRL_GPIO, OUTPUT_OPEN_DRAIN);
    digitalWrite(TEST_GPIO, m == '3' ? LOW : HIGH);
    digitalWrite(CTRL_GPIO, m == 'c' ? LOW : HIGH);
    mode = m;
    serialPrintf("[static] mode=%c low=%s\n", m, m == '3' ? "GPIO43" : (m == 'c' ? "GPIO4" : "none"));
    dumpRegs();
    lastDump = millis();
}

void setup()
{
    Serial.begin(115200);
    while (!Serial && millis() < 3000) { /* wait up to 3s for USB serial */ }
    delay(500);
    Serial.println();
    serialPrintf("[static] sketch=yd_static_low version=%s; modes r/3/c by serial; boot mode r\n", STATIC_VERSION);
    enterMode('r');
}

void loop()
{
    while (Serial.available())
    {
        char c = (char)Serial.read();
        if (c == 'r' || c == '3' || c == 'c') enterMode(c);
    }
    if (millis() - lastDump >= 2000)
    {
        serialPrintf("[static] t=%lu mode=%c\n", millis(), mode);
        dumpRegs();
        lastDump = millis();
    }
}

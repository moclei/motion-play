// V7R-014 static low-drive build (card delta): holds GPIO43 (SDA) or GPIO44
// (SCL) low as a plain open-drain GPIO output, with the I2C controller
// detached, while TCA channel 2 stays open (rigid #1 on J6), so each pad's
// static low can be read at TPIO43 / TPIO44.
//
// Modes, chosen by one character on USB serial (boot mode: r):
//   f  frames: the V7R-009 scope cycle (TCA<-0x04, INA, BQ, TCA<-0x00 every
//      100 ms, 400 kHz, default drive), for V8 and the reference low
//   r  released: Wire opens TCA channel 2 and reads it back, Wire.end(), then
//      GPIO43 and GPIO44 as open-drain outputs, both high (bus idle)
//   3  as r, then GPIO43 low (GPIO44 high)
//   4  as r, then GPIO44 low (GPIO43 high)
// Every mode change prints [static] mode=<m> tca_reg=<hex> and a [regs] dump
// of both pads (as V7R-011); static modes repeat the dump every 2 s.
// Register writes: only through Wire, pinMode() and digitalWrite().

#include <Arduino.h>
#include <Wire.h>
#include <stdarg.h>
#include <stdio.h>
#include "soc/gpio_reg.h"
#include "soc/gpio_sig_map.h"
#include "soc/io_mux_reg.h"

#define STATIC_VERSION "1.0"
#define I2C_CLOCK_HZ 400000

static const uint8_t TCA_ADDR = 0x70;
static const uint8_t INA_ADDR = 0x40;
static const uint8_t BQ_ADDR = 0x6B;
static const uint8_t TCA_CH2 = 1 << 2;

static char mode = 0;
static bool wireOn = false;
static uint32_t nCycles = 0, nTcaOk = 0, nInaAck = 0, nBqAck = 0;
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

static uint8_t tcaWrite(uint8_t value)
{
    Wire.beginTransmission(TCA_ADDR);
    Wire.write(value);
    return Wire.endTransmission();
}

static uint8_t probe(uint8_t addr)
{
    Wire.beginTransmission(addr);
    return Wire.endTransmission();
}

static void dumpPad(int gpio, uint32_t ioMuxReg, uint32_t pinReg, uint32_t outSelReg)
{
    uint32_t mux = REG_READ(ioMuxReg);
    uint32_t pin = REG_READ(pinReg);
    uint32_t sel = REG_READ(outSelReg);
    uint32_t bit = 1UL << (gpio - 32);
    serialPrintf("[regs] gpio=%d mcu_sel=%lu fun_drv=%lu wpu=%lu wpd=%lu ie=%lu od=%lu out_sig=%lu oen_sel=%lu ",
                 gpio, (unsigned long)((mux >> MCU_SEL_S) & MCU_SEL_V), (unsigned long)((mux >> FUN_DRV_S) & FUN_DRV_V),
                 (unsigned long)((mux >> FUN_PU_S) & 1), (unsigned long)((mux >> FUN_PD_S) & 1),
                 (unsigned long)((mux >> FUN_IE_S) & 1), (unsigned long)((pin >> GPIO_PIN0_PAD_DRIVER_S) & 1),
                 (unsigned long)((sel >> GPIO_FUNC0_OUT_SEL_S) & GPIO_FUNC0_OUT_SEL_V),
                 (unsigned long)((sel >> GPIO_FUNC0_OEN_SEL_S) & 1));
    serialPrintf("oe=%d out=%d in=%d\n", (REG_READ(GPIO_ENABLE1_REG) & bit) ? 1 : 0,
                 (REG_READ(GPIO_OUT1_REG) & bit) ? 1 : 0, (REG_READ(GPIO_IN1_REG) & bit) ? 1 : 0);
}

static void dumpRegs()
{
    dumpPad(43, IO_MUX_GPIO43_REG, GPIO_PIN43_REG, GPIO_FUNC43_OUT_SEL_CFG_REG);
    dumpPad(44, IO_MUX_GPIO44_REG, GPIO_PIN44_REG, GPIO_FUNC44_OUT_SEL_CFG_REG);
}

static void startWire()
{
    if (!wireOn)
    {
        Wire.begin(43, 44);
        Wire.setClock(I2C_CLOCK_HZ);
        wireOn = true;
    }
}

static void enterMode(char m)
{
    if (m == 'f')
    {
        startWire();
        tcaWrite(0x00);
        mode = m;
        serialPrintf("[static] mode=f (frames: TCA<-0x04, INA 0x40, BQ 0x6B, TCA<-0x00; every 100 ms)\n");
        dumpRegs();
        return;
    }
    // r, 3, 4: open TCA channel 2 through Wire and read it back, then hand both pads to plain GPIO
    startWire();
    uint8_t err = tcaWrite(TCA_CH2);
    int reg = -1;
    if (Wire.requestFrom(TCA_ADDR, (uint8_t)1) == 1) reg = Wire.read();
    Wire.end();
    wireOn = false;
    pinMode(43, OUTPUT_OPEN_DRAIN);
    pinMode(44, OUTPUT_OPEN_DRAIN);
    digitalWrite(43, m == '3' ? LOW : HIGH);
    digitalWrite(44, m == '4' ? LOW : HIGH);
    mode = m;
    serialPrintf("[static] mode=%c tca_write_err=%u tca_reg=0x%02x low=%s\n", m, err, reg & 0xff,
                 m == '3' ? "GPIO43" : (m == '4' ? "GPIO44" : "none"));
    dumpRegs();
    lastDump = millis();
}

void setup()
{
    Serial.begin(115200);
    while (!Serial && millis() < 3000) { /* wait up to 3s for USB serial */ }
    delay(500);
    Serial.println();
    serialPrintf("[static] sketch=v7_static_low version=%s; modes f/r/3/4 by serial; boot mode r\n", STATIC_VERSION);
    enterMode('r');
}

void loop()
{
    while (Serial.available())
    {
        char c = (char)Serial.read();
        if (c == 'f' || c == 'r' || c == '3' || c == '4') enterMode(c);
    }
    if (mode == 'f')
    {
        uint8_t tcaErr = tcaWrite(TCA_CH2);
        uint8_t inaErr = probe(INA_ADDR);
        uint8_t bqErr = probe(BQ_ADDR);
        tcaWrite(0x00);
        nCycles++;
        if (tcaErr == 0) nTcaOk++;
        if (inaErr == 0) nInaAck++;
        if (bqErr == 0) nBqAck++;
        if (nCycles % 10 == 0)
            serialPrintf("[scope] t=%lu n=%lu tca=%lu ina=%lu bq=%lu\n", millis(), (unsigned long)nCycles,
                         (unsigned long)nTcaOk, (unsigned long)nInaAck, (unsigned long)nBqAck);
        delay(100);
    }
    else if (millis() - lastDump >= 2000)
    {
        serialPrintf("[static] t=%lu mode=%c\n", millis(), mode);
        dumpRegs();
        lastDump = millis();
    }
}

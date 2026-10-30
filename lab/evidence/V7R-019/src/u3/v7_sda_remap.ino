// V7R-019 remap build (card delta): drives the SDA net from GPIO43 (pad 37,
// as v7-clean) or from GPIO16 (TPIO16, joined to the SDA net by one wire),
// with the other pad an input, in one boot; SCL stays on GPIO44.
//
// Modes, chosen by one character on USB serial (boot mode: r):
//   r  released: Wire.end(); GPIO43, GPIO16, GPIO44 inputs, no pulls (bus idle)
//   a  SDA on GPIO43: GPIO16 input (no pulls), then Wire.begin(43, 44)
//   b  SDA on GPIO16: GPIO43 input (no pulls), then Wire.begin(16, 44)
// Every mode change first releases all three pads (as r), so the two SDA pads
// are never outputs at the same time.
// In a and b, every 100 ms at 400 kHz:
//   TCA 0x70 <- 0x04 (channel 2 open; rigid #1 on J6), probe INA 0x40,
//   probe BQ 0x6B, probe PCA 0x76, PCA <- 0x01, probe VCNL 0x60,
//   PCA <- 0x02, probe VCNL 0x60, PCA <- 0x00, TCA 0x70 <- 0x00.
// Every 10 cycles one [remap] line with counts since the last mode change;
// every mode change and every 50 cycles a [regs] dump of GPIO43, GPIO16 and
// GPIO44 (as V7R-014) plus the I2C SDA input-select register.
// Register writes: only through Wire and pinMode().

#include <Arduino.h>
#include <Wire.h>
#include <stdarg.h>
#include <stdio.h>
#include "soc/gpio_reg.h"
#include "soc/gpio_sig_map.h"
#include "soc/io_mux_reg.h"

#define REMAP_VERSION "1.0"
#define I2C_CLOCK_HZ 400000

static const uint8_t TCA_ADDR = 0x70;
static const uint8_t INA_ADDR = 0x40;
static const uint8_t BQ_ADDR = 0x6B;
static const uint8_t PCA_ADDR = 0x76;
static const uint8_t VCNL_ADDR = 0x60;
static const uint8_t TCA_CH2 = 1 << 2;

static char mode = 0;
static bool wireOn = false;
static uint32_t nCycles, nTcaOk, nInaAck, nBqAck, nPcaAck, nV0Ack, nV1Ack;
static uint32_t lastDump = 0;

static void serialPrintf(const char *fmt, ...)
{
    char buf[200];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    Serial.print(buf);
}

static uint8_t probe(uint8_t addr)
{
    Wire.beginTransmission(addr);
    return Wire.endTransmission();
}

static uint8_t muxWrite(uint8_t addr, uint8_t value)
{
    Wire.beginTransmission(addr);
    Wire.write(value);
    return Wire.endTransmission();
}

static void dumpPad(int gpio, uint32_t ioMuxReg, uint32_t pinReg, uint32_t outSelReg)
{
    uint32_t mux = REG_READ(ioMuxReg);
    uint32_t pin = REG_READ(pinReg);
    uint32_t sel = REG_READ(outSelReg);
    bool hi = gpio >= 32;
    uint32_t bit = 1UL << (hi ? gpio - 32 : gpio);
    uint32_t oe = REG_READ(hi ? GPIO_ENABLE1_REG : GPIO_ENABLE_REG);
    uint32_t out = REG_READ(hi ? GPIO_OUT1_REG : GPIO_OUT_REG);
    uint32_t in = REG_READ(hi ? GPIO_IN1_REG : GPIO_IN_REG);
    serialPrintf("[regs] gpio=%d mcu_sel=%lu fun_drv=%lu wpu=%lu wpd=%lu ie=%lu od=%lu out_sig=%lu oen_sel=%lu ",
                 gpio, (unsigned long)((mux >> MCU_SEL_S) & MCU_SEL_V), (unsigned long)((mux >> FUN_DRV_S) & FUN_DRV_V),
                 (unsigned long)((mux >> FUN_PU_S) & 1), (unsigned long)((mux >> FUN_PD_S) & 1),
                 (unsigned long)((mux >> FUN_IE_S) & 1), (unsigned long)((pin >> GPIO_PIN0_PAD_DRIVER_S) & 1),
                 (unsigned long)((sel >> GPIO_FUNC0_OUT_SEL_S) & GPIO_FUNC0_OUT_SEL_V),
                 (unsigned long)((sel >> GPIO_FUNC0_OEN_SEL_S) & 1));
    serialPrintf("oe=%d out=%d in=%d\n", (oe & bit) ? 1 : 0, (out & bit) ? 1 : 0, (in & bit) ? 1 : 0);
}

static void dumpRegs()
{
    dumpPad(43, IO_MUX_GPIO43_REG, GPIO_PIN43_REG, GPIO_FUNC43_OUT_SEL_CFG_REG);
    dumpPad(16, IO_MUX_GPIO16_REG, GPIO_PIN16_REG, GPIO_FUNC16_OUT_SEL_CFG_REG);
    dumpPad(44, IO_MUX_GPIO44_REG, GPIO_PIN44_REG, GPIO_FUNC44_OUT_SEL_CFG_REG);
    uint32_t inSel = REG_READ(GPIO_FUNC0_IN_SEL_CFG_REG + 4 * I2CEXT0_SDA_IN_IDX);
    serialPrintf("[regs] sda_in_sel=%lu sda_in_via_matrix=%lu\n",
                 (unsigned long)(inSel & GPIO_FUNC0_IN_SEL_V), (unsigned long)((inSel >> GPIO_SIG0_IN_SEL_S) & 1));
}

static void releaseAll()
{
    if (wireOn)
    {
        Wire.end();
        wireOn = false;
    }
    pinMode(43, INPUT);
    pinMode(16, INPUT);
    pinMode(44, INPUT);
}

static void enterMode(char m)
{
    releaseAll();
    if (m == 'a' || m == 'b')
    {
        int sda = (m == 'a') ? 43 : 16;
        Wire.begin(sda, 44);
        Wire.setClock(I2C_CLOCK_HZ);
        wireOn = true;
        muxWrite(TCA_ADDR, 0x00);
    }
    mode = m;
    nCycles = nTcaOk = nInaAck = nBqAck = nPcaAck = nV0Ack = nV1Ack = 0;
    serialPrintf("[remap] mode=%c sda=%s\n", m, m == 'a' ? "GPIO43" : (m == 'b' ? "GPIO16" : "none (released)"));
    dumpRegs();
    lastDump = millis();
}

void setup()
{
    Serial.begin(115200);
    while (!Serial && millis() < 3000) { /* wait up to 3s for USB serial */ }
    delay(500);
    Serial.println();
    serialPrintf("[remap] sketch=v7_sda_remap version=%s; modes r/a/b by serial; boot mode r\n", REMAP_VERSION);
    serialPrintf("[remap] cycle: TCA<-0x04, INA 0x40, BQ 0x6B, PCA 0x76, PCA<-0x01, VCNL 0x60, PCA<-0x02, VCNL 0x60, PCA<-0x00, TCA<-0x00; every 100 ms\n");
    enterMode('r');
}

void loop()
{
    while (Serial.available())
    {
        char c = (char)Serial.read();
        if (c == 'r' || c == 'a' || c == 'b') enterMode(c);
    }
    if (mode == 'a' || mode == 'b')
    {
        uint8_t tcaErr = muxWrite(TCA_ADDR, TCA_CH2);
        uint8_t inaErr = probe(INA_ADDR);
        uint8_t bqErr = probe(BQ_ADDR);
        uint8_t pcaErr = probe(PCA_ADDR);
        muxWrite(PCA_ADDR, 0x01);
        uint8_t v0Err = probe(VCNL_ADDR);
        muxWrite(PCA_ADDR, 0x02);
        uint8_t v1Err = probe(VCNL_ADDR);
        muxWrite(PCA_ADDR, 0x00);
        muxWrite(TCA_ADDR, 0x00);
        nCycles++;
        if (tcaErr == 0) nTcaOk++;
        if (inaErr == 0) nInaAck++;
        if (bqErr == 0) nBqAck++;
        if (pcaErr == 0) nPcaAck++;
        if (v0Err == 0) nV0Ack++;
        if (v1Err == 0) nV1Ack++;
        if (nCycles % 10 == 0)
            serialPrintf("[remap] t=%lu mode=%c n=%lu tca=%lu ina=%lu bq=%lu pca=%lu v0=%lu v1=%lu last=%u%u%u%u%u\n",
                         millis(), mode, (unsigned long)nCycles, (unsigned long)nTcaOk, (unsigned long)nInaAck,
                         (unsigned long)nBqAck, (unsigned long)nPcaAck, (unsigned long)nV0Ack, (unsigned long)nV1Ack,
                         inaErr, bqErr, pcaErr, v0Err, v1Err);
        if (nCycles % 50 == 0) dumpRegs();
        delay(100);
    }
    else if (millis() - lastDump >= 2000)
    {
        serialPrintf("[remap] t=%lu mode=%c\n", millis(), mode);
        dumpRegs();
        lastDump = millis();
    }
}

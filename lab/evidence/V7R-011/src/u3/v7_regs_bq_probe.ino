// V7R-011 register build (card delta): the V7R-009 scope build plus a
// read-only dump of the SDA (GPIO43) and SCL (GPIO44) pad configuration.
// Nothing is written to any IO_MUX or GPIO register.
//
// Dump: once after Wire.begin(), then every 50 cycles right after the BQ
// probe (TCA channel 2 still open). One [regs] line per pin plus one line
// for the I2C input selects:
//   [regs] gpio=<n> iomux=<raw> mcu_sel=<f> fun_drv=<0-3> wpu=<b> wpd=<b>
//          ie=<b> filt=<b> pin=<raw> od=<b> outsel=<raw> out_sig=<idx>
//          out_inv=<b> oen_sel=<b> oen_inv=<b> oe=<b> out=<b> in=<b>
//   [regs] in_sel sda=<pin> sda_mx=<b> scl=<pin> scl_mx=<b> u0rxd=<pin>
//
// V7R-009 scope build (card delta, user-approved): holds the v7 bus in the
// failing state so a 0x6B address trigger catches only failing-state frames.
//
// Derived from tools/arduino-sketches v7_pca_master_probe @ ee10efd (same
// TCA writes, same probe call, same clock). Per cycle, every 100 ms:
//   TCA 0x70 <- 0x04 (channel 2 open; rigid #1 on J6), probe INA 0x40
//   (control), probe BQ 0x6B, TCA 0x70 <- 0x00.
// Every 10 cycles one line: [scope] n=<cycles> tca=<sel ok> ina=<ACK> bq=<ACK>
// bq_codes=<last 10 BQ codes>.
// The only line that differs between the U3 and Nano copies is Wire.begin().

#include <Arduino.h>
#include <Wire.h>
#include <stdarg.h>
#include <stdio.h>
#include "soc/gpio_reg.h"
#include "soc/gpio_sig_map.h"
#include "soc/io_mux_reg.h"

#define SCOPE_VERSION "1.0"

#ifndef I2C_CLOCK_HZ
#define I2C_CLOCK_HZ 400000
#endif

#if defined(ARDUINO_BOARD)
static const char SCOPE_BOARD[] = ARDUINO_BOARD;
#elif defined(ARDUINO_ARCH_ESP32)
static const char SCOPE_BOARD[] = "ESP32";
#else
static const char SCOPE_BOARD[] = "unknown";
#endif

static const uint8_t TCA_ADDR = 0x70;
static const uint8_t INA_ADDR = 0x40;
static const uint8_t BQ_ADDR = 0x6B;
static const uint8_t TCA_CH2 = 1 << 2;

static void serialPrintf(const char *fmt, ...)
{
    char buf[128];
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
    serialPrintf("[regs] gpio=%d iomux=0x%08lx mcu_sel=%lu fun_drv=%lu wpu=%lu wpd=%lu ie=%lu filt=%lu ",
                 gpio, (unsigned long)mux, (unsigned long)((mux >> MCU_SEL_S) & MCU_SEL_V),
                 (unsigned long)((mux >> FUN_DRV_S) & FUN_DRV_V), (unsigned long)((mux >> FUN_PU_S) & 1),
                 (unsigned long)((mux >> FUN_PD_S) & 1), (unsigned long)((mux >> FUN_IE_S) & 1),
                 (unsigned long)((mux >> 15) & 1));
    serialPrintf("pin=0x%08lx od=%lu outsel=0x%08lx out_sig=%lu out_inv=%lu oen_sel=%lu oen_inv=%lu ",
                 (unsigned long)pin, (unsigned long)((pin >> GPIO_PIN0_PAD_DRIVER_S) & 1),
                 (unsigned long)sel, (unsigned long)((sel >> GPIO_FUNC0_OUT_SEL_S) & GPIO_FUNC0_OUT_SEL_V),
                 (unsigned long)((sel >> GPIO_FUNC0_OUT_INV_SEL_S) & 1),
                 (unsigned long)((sel >> GPIO_FUNC0_OEN_SEL_S) & 1),
                 (unsigned long)((sel >> GPIO_FUNC0_OEN_INV_SEL_S) & 1));
    serialPrintf("oe=%d out=%d in=%d\n", (REG_READ(GPIO_ENABLE1_REG) & bit) ? 1 : 0,
                 (REG_READ(GPIO_OUT1_REG) & bit) ? 1 : 0, (REG_READ(GPIO_IN1_REG) & bit) ? 1 : 0);
}

static void dumpRegs()
{
    dumpPad(43, IO_MUX_GPIO43_REG, GPIO_PIN43_REG, GPIO_FUNC43_OUT_SEL_CFG_REG);
    dumpPad(44, IO_MUX_GPIO44_REG, GPIO_PIN44_REG, GPIO_FUNC44_OUT_SEL_CFG_REG);
    uint32_t sda = REG_READ(GPIO_FUNC0_IN_SEL_CFG_REG + 4 * I2CEXT0_SDA_IN_IDX);
    uint32_t scl = REG_READ(GPIO_FUNC0_IN_SEL_CFG_REG + 4 * I2CEXT0_SCL_IN_IDX);
    uint32_t rxd = REG_READ(GPIO_FUNC0_IN_SEL_CFG_REG + 4 * U0RXD_IN_IDX);
    serialPrintf("[regs] in_sel sda=%lu sda_mx=%lu scl=%lu scl_mx=%lu u0rxd=%lu u0rxd_mx=%lu\n",
                 (unsigned long)(sda & GPIO_FUNC0_IN_SEL_V), (unsigned long)((sda >> GPIO_SIG0_IN_SEL_S) & 1),
                 (unsigned long)(scl & GPIO_FUNC0_IN_SEL_V), (unsigned long)((scl >> GPIO_SIG0_IN_SEL_S) & 1),
                 (unsigned long)(rxd & GPIO_FUNC0_IN_SEL_V), (unsigned long)((rxd >> GPIO_SIG0_IN_SEL_S) & 1));
}

static uint32_t nCycles = 0, nTcaOk = 0, nInaAck = 0, nBqAck = 0;
static char bqCodes[11];

void setup()
{
    Serial.begin(115200);
    while (!Serial && millis() < 3000) { /* wait up to 3s for USB serial */ }
    delay(500);

    Wire.begin(43, 44);
    Wire.setClock(I2C_CLOCK_HZ);

    Serial.println();
    serialPrintf("[scope] sketch=v7_scope_bq_probe version=%s board=%s i2c_clock=%lu Hz\n",
                 SCOPE_VERSION, SCOPE_BOARD, (unsigned long)I2C_CLOCK_HZ);
    serialPrintf("[scope] cycle: TCA<-0x04, INA 0x40, BQ 0x6B, TCA<-0x00; every 100 ms\n");
    tcaWrite(0x00);
    dumpRegs();
}

void loop()
{
    uint8_t tcaErr = tcaWrite(TCA_CH2);
    uint8_t inaErr = probe(INA_ADDR);
    uint8_t bqErr = probe(BQ_ADDR);
    if (nCycles % 50 == 0) dumpRegs();
    tcaWrite(0x00);

    bqCodes[nCycles % 10] = (char)('0' + (bqErr > 9 ? 9 : bqErr));
    nCycles++;
    if (tcaErr == 0) nTcaOk++;
    if (inaErr == 0) nInaAck++;
    if (bqErr == 0) nBqAck++;

    if (nCycles % 10 == 0)
    {
        bqCodes[10] = '\0';
        serialPrintf("[scope] t=%lu n=%lu tca=%lu ina=%lu bq=%lu bq_codes=%s\n",
                     millis(), (unsigned long)nCycles, (unsigned long)nTcaOk,
                     (unsigned long)nInaAck, (unsigned long)nBqAck, bqCodes);
    }
    delay(100);
}

// V7R-012 drive build (card delta, user-approved): the V7R-009 scope build
// plus GPIO43 (SDA) drive strength set after Wire init from SDA_DRIVE_CAP
// (u3-drv2 / u3-drv3), read back on the banner and every [scope] line.
//
// V7R-009 scope build: holds the v7 bus in the
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
#include <driver/gpio.h>
#include <stdarg.h>
#include <stdio.h>

#define SCOPE_VERSION "1.0-drv"

#ifndef SDA_DRIVE_CAP
#error "SDA_DRIVE_CAP must be set (GPIO_DRIVE_CAP_2 or GPIO_DRIVE_CAP_3)"
#endif

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

static int driveCap(gpio_num_t pin)
{
    gpio_drive_cap_t cap;
    if (gpio_get_drive_capability(pin, &cap) != ESP_OK) return -1;
    return (int)cap;
}

static uint8_t probe(uint8_t addr)
{
    Wire.beginTransmission(addr);
    return Wire.endTransmission();
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
    gpio_set_drive_capability(GPIO_NUM_43, SDA_DRIVE_CAP);

    Serial.println();
    serialPrintf("[scope] sketch=v7_scope_bq_probe version=%s board=%s i2c_clock=%lu Hz\n",
                 SCOPE_VERSION, SCOPE_BOARD, (unsigned long)I2C_CLOCK_HZ);
    serialPrintf("[scope] cycle: TCA<-0x04, INA 0x40, BQ 0x6B, TCA<-0x00; every 100 ms\n");
    serialPrintf("[scope] drive: set sda=%d; read sda_drv=%d scl_drv=%d\n",
                 (int)SDA_DRIVE_CAP, driveCap(GPIO_NUM_43), driveCap(GPIO_NUM_44));
    tcaWrite(0x00);
}

void loop()
{
    uint8_t tcaErr = tcaWrite(TCA_CH2);
    uint8_t inaErr = probe(INA_ADDR);
    uint8_t bqErr = probe(BQ_ADDR);
    tcaWrite(0x00);

    bqCodes[nCycles % 10] = (char)('0' + (bqErr > 9 ? 9 : bqErr));
    nCycles++;
    if (tcaErr == 0) nTcaOk++;
    if (inaErr == 0) nInaAck++;
    if (bqErr == 0) nBqAck++;

    if (nCycles % 10 == 0)
    {
        bqCodes[10] = '\0';
        serialPrintf("[scope] t=%lu n=%lu tca=%lu ina=%lu bq=%lu bq_codes=%s sda_drv=%d scl_drv=%d\n",
                     millis(), (unsigned long)nCycles, (unsigned long)nTcaOk,
                     (unsigned long)nInaAck, (unsigned long)nBqAck, bqCodes,
                     driveCap(GPIO_NUM_43), driveCap(GPIO_NUM_44));
    }
    delay(100);
}

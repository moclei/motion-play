// v7 PCA-aware external-master probe (Arduino-as-master, card 3)
//
// Sibling of `v7_bq_master_probe` (left unchanged: it is the artefact behind
// L-Ph24a). This sketch reproduces the v7 diag loop,
// `SensorManager::runBusDiagnosticLoop()` at tag `v7-clean`, from an external
// Arduino master. Its rows are character-compatible with the v7 readout
// (`t=…  TCA2        INA:.    BQ:X(2) …`), so per-row counts compare
// directly with V7R-003.
//
// WHAT IT DOES
// ------------
//   setup():
//     - Wire.begin() on the board-default pins, Wire.setClock(I2C_CLOCK_HZ).
//     - Self-identifying banner: sketch, PROBE_VERSION, board, clock.
//     - TCA9548A begin (probe 0x70, write 0x00), same as v7 `mux.begin()`.
//     - PCA9546A scan behind TCA ch 0..2, same addresses, order, delays and
//       prints as v7 `SensorManager::initializePCA()`.
//   loop():
//     - The v7 diag loop body, verbatim in strings, probe order, delays and
//       cadence: banner, PCA detection summary, legend, then
//       `--- Iteration N ---` blocks of BASE / TCA<n> / TCA<n>+PCA0 /
//       TCA<n>+PCA1 rows, 2 s apart, until reset. PCA rows appear only for
//       TCA channels where a PCA was found at setup. The PCA column always
//       probes 0x76, whatever address was detected.
//
//   The v7 `TCA9548A` / `PCA9546A` classes are replaced with raw `Wire`
//   writes that issue the same bus transactions. That includes the TCA
//   class's channel cache: v7 `selectChannel(ch)` sends nothing if `ch` is
//   already the cached channel, and the cache clears only when a write of
//   0x00 succeeds. The diag loop hits this: `resetAllMuxes()` right after a
//   round on a channel with a PCA skips the TCA select. This sketch emulates
//   that cache exactly. (v7 also calls `Wire.setTimeout(100)` before each TCA
//   write. On ESP32 Arduino core 2.0.x that is `Stream::setTimeout`, not the
//   I2C timeout (`setTimeOut`), so it does not affect the bus. It is left
//   out here.)
//
// WIRING (Arduino Nano 33 IoT or Arduino Nano ESP32)
// --------------------------------------------------
//   Arduino A4 (SDA) <-> main PCB TPIO43 (SDA test pad)
//   Arduino A5 (SCL) <-> main PCB TPIO44 (SCL test pad)
//   Arduino GND      <-> main PCB GND test pad
//
// Power: leave the main PCB powered as-is (USB-C or VBAT). Power the
// Arduino separately over its own USB. They share GND only. DO NOT tie the
// 3.3V or 5V rails together. Both Nanos are 3.3 V I/O boards.
//
// PROCEDURE
// ---------
//   1. Flash `motion-play-v7-relbus` to the v7 main PCB:
//        pio run -e motion-play-v7-relbus -t upload
//      Open its serial monitor at 115200 and wait for "BUS RELEASED". The
//      ESP32 then has all TCA channels closed and SDA/SCL as high-Z inputs.
//   2. Plug the sensor rigid into J6 (TCA channel 2) BEFORE resetting the
//      Arduino. The PCA scan runs once at setup, so a rigid added later
//      gets no PCA rows until the next reset.
//   3. Flash this sketch to the Arduino (or press its RESET). Open ITS
//      serial monitor at 115200 in a separate window.
//   4. Read the "PCA detection summary" block, then count rows per
//      iteration, as for the v7 readout.
//
// I2C CLOCK
// ---------
//   Default 400 kHz, the same as `v7-clean`. For 100 kHz, build with
//   -DI2C_CLOCK_HZ=100000 (PlatformIO: build_flags) or edit the define below.
//   The banner prints the clock that was requested.
//
// ERROR CODES / SAMD21 CAVEAT
// ---------------------------
//   Wire.endTransmission(): 0 = ACK, 1 = data too long, 2 = NACK on address,
//   3 = NACK on data, 4 = other, 5 = timeout (ESP32 core only).
//   The SAMD21 (Nano 33 IoT) core has NO I2C timeout. It returns 0/2/3/4 and
//   never 5. A stuck bus can hang the sketch (output stops) rather than
//   print X(5). A card using the Nano 33 IoT should list this under
//   "setup void": "no output" there is the equivalent of X(5) on ESP32.
//
// OUTPUT FORMATTING
// -----------------
//   The atmelsam core's Print has no printf(), so all formatted output goes
//   through serialPrintf() (vsnprintf into a buffer, then Serial.print). The
//   format strings are the v7 ones unchanged, so the bytes match
//   Serial.printf on ESP32.

#include <Arduino.h>
#include <Wire.h>
#include <stdarg.h>
#include <stdio.h>

#define PROBE_VERSION "1.0"

#ifndef I2C_CLOCK_HZ
#define I2C_CLOCK_HZ 400000
#endif

// A const array, not a #define per branch: PlatformIO's .ino pre-pass
// (-fpreprocessed -dD) does not evaluate #if and warns on redefinition.
#if defined(ARDUINO_BOARD)
static const char PROBE_BOARD[] = ARDUINO_BOARD;
#elif defined(ARDUINO_ARCH_SAMD)
static const char PROBE_BOARD[] = "SAMD (Nano 33 IoT)";
#elif defined(ARDUINO_ARCH_ESP32)
static const char PROBE_BOARD[] = "ESP32 (Nano ESP32)";
#else
static const char PROBE_BOARD[] = "unknown";
#endif

static const uint8_t TCA_ADDR = 0x70;

// Per TCA channel: detected PCA address, 0 if none (v7 `pca_addresses[]`).
static uint8_t pca_addresses[3] = {0, 0, 0};

// ---------------------------------------------------------------------------
// printf helper: same bytes as Serial.printf on ESP32
// ---------------------------------------------------------------------------
static void serialPrintf(const char *fmt, ...)
{
    char buf[128];
    va_list ap;
    va_start(ap, fmt);
    vsnprintf(buf, sizeof(buf), fmt, ap);
    va_end(ap);
    Serial.print(buf);
}

// ---------------------------------------------------------------------------
// TCA9548A: raw-Wire equivalent of v7 `TCA9548A`, channel cache included
// ---------------------------------------------------------------------------
static uint8_t tca_currentChannel = 0xFF;

static void tcaDisableAllChannels()
{
    Wire.beginTransmission(TCA_ADDR);
    Wire.write(0x00);
    uint8_t error = Wire.endTransmission();
    if (error == 0)
        tca_currentChannel = 0xFF;
}

static bool tcaSelectChannel(uint8_t channel)
{
    if (channel > 7)
        return false;
    if (tca_currentChannel == channel)
        return true; // v7: skip if already on this channel
    Wire.beginTransmission(TCA_ADDR);
    Wire.write(1 << channel);
    uint8_t error = Wire.endTransmission();
    if (error == 0)
    {
        tca_currentChannel = channel;
        return true;
    }
    return false;
}

static bool tcaBegin()
{
    Wire.beginTransmission(TCA_ADDR);
    uint8_t error = Wire.endTransmission();
    if (error == 0)
    {
        tcaDisableAllChannels();
        return true;
    }
    return false;
}

// ---------------------------------------------------------------------------
// PCA9546A: raw-Wire equivalent of v7 `PCA9546A` (no cache)
// ---------------------------------------------------------------------------
static bool pcaBegin(uint8_t addr)
{
    Wire.beginTransmission(addr);
    return (Wire.endTransmission() == 0);
}

static bool pcaSelectChannel(uint8_t addr, uint8_t channel)
{
    if (channel > 3)
        return false;
    Wire.beginTransmission(addr);
    Wire.write(1 << channel);
    return (Wire.endTransmission() == 0);
}

static bool pcaDisableAllChannels(uint8_t addr)
{
    Wire.beginTransmission(addr);
    Wire.write(0x00);
    return (Wire.endTransmission() == 0);
}

// ---------------------------------------------------------------------------
// Setup-time PCA scan: port of v7 `SensorManager::initializePCA()`
// ---------------------------------------------------------------------------
static bool initializePCA()
{
    Serial.println("Scanning for PCA9546A multiplexers on TCA channels...");

    int pca_found_count = 0;

    for (int tca_ch = 0; tca_ch < 3; tca_ch++)
    {
        Serial.print("  Scanning TCA channel ");
        Serial.println(tca_ch);

        if (!tcaSelectChannel(tca_ch))
        {
            Serial.println("    ERROR: Failed to select TCA channel");
            continue;
        }

        delay(10);

        uint8_t test_addresses[] = {0x74, 0x75, 0x76, 0x72, 0x71, 0x73, 0x77};
        bool pca_found = false;
        uint8_t working_address = 0;

        for (int i = 0; i < 7; i++)
        {
            uint8_t test_addr = test_addresses[i];
            if (pcaBegin(test_addr))
            {
                Serial.print("    PCA9546A found at 0x");
                Serial.println(test_addr, HEX);
                working_address = test_addr;
                pca_found = true;
                pcaDisableAllChannels(test_addr);
                break;
            }
        }

        if (pca_found)
        {
            pca_addresses[tca_ch] = working_address;
            pcaDisableAllChannels(working_address);
            pca_found_count++;
        }
        else
        {
            Serial.println("    No PCA found on this channel");
        }
    }

    tcaDisableAllChannels();

    Serial.print("Found ");
    Serial.print(pca_found_count);
    Serial.println(" sensor board(s)");

    if (pca_found_count == 0)
    {
        Serial.println("ERROR: No PCA9546A multiplexers found!");
        return false;
    }

    return true;
}

// ---------------------------------------------------------------------------
// Diag loop: port of v7 `SensorManager::runBusDiagnosticLoop()`
// ---------------------------------------------------------------------------
struct Probe
{
    uint8_t addr;
    const char *name;
};
static const Probe probes[] = {
    {0x40, "INA"},
    {0x6B, "BQ"},
    {0x70, "TCA"},
    {0x76, "PCA"},
    {0x60, "VCNL"},
};
static const int nProbes = sizeof(probes) / sizeof(probes[0]);

static void probeAndPrint(const char *stateLabel)
{
    serialPrintf("t=%7lu  %-10s  ", millis(), stateLabel);
    for (int i = 0; i < nProbes; i++)
    {
        Wire.beginTransmission(probes[i].addr);
        uint8_t err = Wire.endTransmission();
        if (err == 0)
            serialPrintf("%s:.    ", probes[i].name);
        else
            serialPrintf("%s:X(%u) ", probes[i].name, err);
    }
    Serial.println();
}

static void resetAllMuxes()
{
    for (int ch = 0; ch < 3; ch++)
    {
        if (pca_addresses[ch] != 0)
        {
            tcaSelectChannel(ch);
            delay(1);
            pcaDisableAllChannels(pca_addresses[ch]);
        }
    }
    tcaDisableAllChannels();
    delay(2);
}

static void runBusDiagnosticLoop()
{
    Serial.println();
    Serial.println("==============================================================");
    Serial.println("I2C BUS DIAGNOSTIC LOOP (continuous — press RESET to stop)");
    Serial.println("==============================================================");

    Serial.println("PCA detection summary (from init):");
    for (int ch = 0; ch < 3; ch++)
    {
        if (pca_addresses[ch] != 0)
            serialPrintf("  TCA ch %d: PCA9546A at 0x%02X\n", ch, pca_addresses[ch]);
        else
            serialPrintf("  TCA ch %d: (nothing detected)\n", ch);
    }

    Serial.println();
    Serial.println("Probing: INA(0x40)  BQ(0x6B)  TCA(0x70)  PCA(0x76)  VCNL(0x60)");
    Serial.println("Legend:  '.' = ACK,  'X(n)' = error n");
    Serial.println("         1=data_too_long 2=NACK_addr 3=NACK_data 4=other 5=timeout/bus_hang");
    Serial.println();
    Serial.println("Expected when working correctly:");
    Serial.println("  BASE           -> INA, BQ, TCA present; PCA, VCNL absent");
    Serial.println("  TCA{0,1,2}     -> INA, BQ, TCA present; PCA present only on");
    Serial.println("                    channels that have a rigid; VCNL absent");
    Serial.println("  TCA+PCA0/1     -> INA, BQ, TCA, PCA, VCNL all present");
    Serial.println();

    unsigned long iter = 0;
    while (true)
    {
        iter++;
        serialPrintf("--- Iteration %lu ---\n", iter);

        // State: BASE: everything closed.
        resetAllMuxes();
        probeAndPrint("BASE");

        for (int tca_ch = 0; tca_ch < 3; tca_ch++)
        {
            resetAllMuxes();

            // State: TCA{ch}: TCA channel open, PCA channels (if any) closed.
            tcaSelectChannel(tca_ch);
            delay(2);
            if (pca_addresses[tca_ch] != 0)
            {
                pcaDisableAllChannels(pca_addresses[tca_ch]);
                delay(2);
            }
            char label[16];
            snprintf(label, sizeof(label), "TCA%d", tca_ch);
            probeAndPrint(label);

            if (pca_addresses[tca_ch] != 0)
            {
                // State: TCA{ch}+PCA0
                pcaSelectChannel(pca_addresses[tca_ch], 0);
                delay(2);
                snprintf(label, sizeof(label), "TCA%d+PCA0", tca_ch);
                probeAndPrint(label);

                // State: TCA{ch}+PCA1
                pcaDisableAllChannels(pca_addresses[tca_ch]);
                delay(1);
                pcaSelectChannel(pca_addresses[tca_ch], 1);
                delay(2);
                snprintf(label, sizeof(label), "TCA%d+PCA1", tca_ch);
                probeAndPrint(label);
            }
        }

        Serial.println();

        // ~2 second cadence between iterations (v7-clean).
        delay(2000);
    }
}

// ---------------------------------------------------------------------------

void setup()
{
    Serial.begin(115200);
    while (!Serial && millis() < 3000) { /* wait up to 3s for USB serial */ }
    delay(500);

    Wire.begin();
    Wire.setClock(I2C_CLOCK_HZ);

    Serial.println();
    serialPrintf("[probe] sketch=v7_pca_master_probe version=%s board=%s i2c_clock=%lu Hz\n",
                 PROBE_VERSION, PROBE_BOARD, (unsigned long)I2C_CLOCK_HZ);

    // v7 `mux.begin()`, then `initializePCA()`.
    if (!tcaBegin())
    {
        Serial.println("ERROR: Failed to initialize TCA9548A");
        return; // loop() runs the diag loop with no PCAs, as v7 does on init failure
    }
    Serial.println("TCA9548A initialized");

    initializePCA();
}

void loop()
{
    runBusDiagnosticLoop(); // never returns
}

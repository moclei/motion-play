// v7 BQ24195 master-probe sketch (Arduino-as-master discrimination test)
//
// Companion to the `motion-play-v7-relbus` PlatformIO build. See
// `docs/debugging/v7-i2c-investigation.md` "Immediate next steps" item 1
// for the test rationale.
//
// PURPOSE
// -------
// Decide between two surviving hypotheses for the v7 I2C failure:
//
//   Story D-revised: SDA input-stage noise-margin failure at the BQ24195.
//     The combined parasitic loading + SCL-coupled crosstalk introduced by
//     the failing-config cable on TCA2 pushes the SDA line below the BQ's
//     V_IH (~1.3 V at V_PULL-UP = 1.8 V; somewhat higher at 3.3 V) during
//     the 9th-clock ACK window, so the BQ misclassifies its own address
//     and refuses to ACK. This mechanism is independent of which master
//     is driving the bus -- it depends only on bus capacitance, pull-up
//     strength, and SCL/SDA edges.
//
//   Story F: ESP32-S3 I2C peripheral interaction. Some ESP32-S3-specific
//     timing/clock-stretching/edge-rate behavior interacts badly with the
//     bus topology to produce the NACK; a different, simpler I2C master
//     (Arduino Nano ESP32, AVR Nano, etc.) would not see the failure.
//
// HOW THIS SKETCH DECIDES
// -----------------------
// The ESP32 firmware (motion-play-v7-relbus build) ends in a "BUS
// RELEASED" state with all TCA channels closed and SDA/SCL set to high-Z
// inputs. The on-board 2.2 kΩ pull-ups (R28/R29) keep both lines at +3.3V
// idle. The failing-config sensor cable should remain plugged into J6
// (TCA channel 2) for the duration of this test.
//
// This sketch then:
//   1. Confirms the bus is sane from Arduino's master: probes INA(0x40),
//      BQ(0x6B), TCA(0x70). All three should ACK because no sensor
//      channel is open yet (this is the same "BASE row" baseline the
//      ESP32 firmware probes on each iteration).
//   2. For each TCA channel 0/1/2: open the channel from Arduino's
//      master (write (1 << ch) to 0x70), probe the bus, then close all
//      channels again.
//
// EXPECTED OUTCOMES
// -----------------
//   - BASE row: BQ ACKs (sanity check).
//   - TCA0 / TCA1 rows (no sensor cable plugged in): BQ ACKs.
//   - TCA2 row (failing-config cable plugged into J6):
//       * BQ NACKs Arduino  -> Story D-revised confirmed. The failure is
//         a property of the bus electrical environment, not of which
//         master is driving. v8 fix: I2C buffer between BQ and the rest
//         of the bus (or relocate BQ pull-ups, or add hysteresis).
//       * BQ ACKs Arduino   -> Story F confirmed. ESP32-S3 specifically
//         is provoking the failure. v8 fix: investigate ESP32-S3 I2C
//         peripheral configuration (clock stretching, glitch filter,
//         edge timings); possibly use a different I2C master IC.
//
// WIRING (Arduino Nano ESP32)
// ---------------------------
//   Arduino A4 (SDA) <-> main PCB TPIO43 (SDA test pad)
//   Arduino A5 (SCL) <-> main PCB TPIO44 (SCL test pad)
//   Arduino GND      <-> main PCB GND test pad
//
// Power: leave the main PCB powered as-is (USB-C or VBAT). The Arduino is
// powered separately over its own USB. They share GND only -- DO NOT tie
// 3.3V or 5V rails together.
//
// PROCEDURE
// ---------
//   1. Flash motion-play-v7-relbus to the main PCB:
//        pio run -e motion-play-v7-relbus -t upload
//      Open its serial monitor at 115200 and wait for "BUS RELEASED".
//   2. Flash this sketch to the Arduino. Open ITS serial monitor at
//      115200 in a separate window.
//   3. Confirm the failing-config sensor cable is plugged into J6 (TCA
//      channel 2) and that the ESP32 reproduced the BQ:X(2) NACK on its
//      TCA2 row in step 1's diagnostic burst.
//   4. Read this sketch's output. Compare BQ's behavior on the TCA2 row
//      between ESP32 and Arduino.
//
// I2C clock: 100 kHz (Standard Mode), matches the ESP32 firmware default.

#include <Wire.h>

static const uint32_t I2C_CLOCK_HZ = 100000;

static const uint8_t TCA_ADDR = 0x70;

struct Probe { uint8_t addr; const char *name; };
static const Probe PROBES[] = {
    {0x40, "INA"},
    {0x60, "VCNL"},
    {0x6B, "BQ "},
    {0x70, "TCA"},
};
static const int N_PROBES = sizeof(PROBES) / sizeof(PROBES[0]);

static uint8_t tcaWrite(uint8_t mask)
{
    Wire.beginTransmission(TCA_ADDR);
    Wire.write(mask);
    return Wire.endTransmission();
}

static void probeRow(const char *label)
{
    Serial.print("t=");
    Serial.print(millis());
    Serial.print("  ");
    Serial.print(label);
    Serial.print("    ");
    for (int i = 0; i < N_PROBES; i++)
    {
        Wire.beginTransmission(PROBES[i].addr);
        uint8_t err = Wire.endTransmission();
        Serial.print(PROBES[i].name);
        if (err == 0)
        {
            Serial.print(":.    ");
        }
        else
        {
            Serial.print(":X(");
            Serial.print(err);
            Serial.print(") ");
        }
    }
    Serial.println();
}

static void runIteration(int iter)
{
    Serial.print("--- Iteration ");
    Serial.print(iter);
    Serial.println(" (Arduino as master) ---");

    tcaWrite(0x00);
    delay(2);
    probeRow("BASE  ");

    for (int ch = 0; ch < 3; ch++)
    {
        tcaWrite(0x00);
        delay(1);
        uint8_t err = tcaWrite((uint8_t)(1 << ch));
        if (err != 0)
        {
            Serial.print("WARN: TCA select ch ");
            Serial.print(ch);
            Serial.print(" returned err=");
            Serial.println(err);
        }
        delay(2);

        char label[12];
        snprintf(label, sizeof(label), "TCA%d  ", ch);
        probeRow(label);
    }

    tcaWrite(0x00);
    delay(2);
    Serial.println();
}

void setup()
{
    Serial.begin(115200);
    while (!Serial && millis() < 3000) { /* wait up to 3s for USB serial */ }
    delay(500);

    Serial.println();
    Serial.println("==============================================================");
    Serial.println("v7 BQ24195 master-probe (Arduino-as-master test)");
    Serial.println("==============================================================");
    Serial.println("Companion to motion-play-v7-relbus. Confirm the main PCB");
    Serial.println("printed 'BUS RELEASED' and the failing-config cable is in J6");
    Serial.println("before reading these results.");
    Serial.println();
    Serial.print("I2C clock: ");
    Serial.print(I2C_CLOCK_HZ);
    Serial.println(" Hz");
    Serial.println();
    Serial.println("Probing each row: INA(0x40)  VCNL(0x60)  BQ(0x6B)  TCA(0x70)");
    Serial.println("Legend:  '.' = ACK,  'X(n)' = error code n (2 = NACK on address)");
    Serial.println();
    Serial.println("Decision matrix on TCA2 row (failing cable in J6):");
    Serial.println("  BQ:X(2)  -> Story D-revised confirmed (bus-electrical fault)");
    Serial.println("  BQ:.     -> Story F confirmed (ESP32-S3-specific behavior)");
    Serial.println("==============================================================");
    Serial.println();

    Wire.begin();
    Wire.setClock(I2C_CLOCK_HZ);
    delay(50);

    for (int iter = 1; iter <= 5; iter++)
    {
        runIteration(iter);
        delay(1500);
    }

    Serial.println("==============================================================");
    Serial.println("Burst complete. Re-running indefinitely so you can hot-swap");
    Serial.println("cables (J6 plugged/unplugged) and watch live behavior.");
    Serial.println("==============================================================");
    Serial.println();
}

void loop()
{
    static int iter = 6;
    runIteration(iter++);
    delay(2000);
}

// VCNL4040 I2C diagnostic sketch
//
// Use this on an Arduino Nano ESP32 (or any 3.3V Arduino with Wire.h) to
// sanity-check the Motion Play sensor-flex / sensor-rigid assembly when the
// main PCB firmware can't find the VCNL4040 sensors.
//
// Two supported wiring variants:
//
//   A) Arduino -> rigid J1 (JST-SH 4-pin upstream).
//      Tests flex + rigid + PCA9546A as a unit. Expects to find the PCA at
//      0x74/0x75/0x76 and the VCNL4040 (0x60) on PCA channels 0 and 1.
//
//   B) Arduino -> flex FPC tail directly (bypassing the rigid).
//      Tests only the VCNL4040 and the flex PCB. Expects to find 0x60
//      directly on the main bus with no PCA. Requires external 4.7kΩ
//      pull-ups on SDA and SCL to 3.3V.
//
// Open the Serial Monitor at 115200 baud after flashing.

#include <Wire.h>

// --- I2C speed -------------------------------------------------------------
// Start at 100 kHz (Standard Mode) for best signal integrity. Bump to
// 400000 later if everything works.
static const uint32_t I2C_CLOCK_HZ = 100000;

// --- PCA9546A control ------------------------------------------------------
// Writing (1 << ch) to the PCA selects a single downstream channel.
// Writing 0x00 disables all channels.
static bool pcaSelectChannel(uint8_t pcaAddr, uint8_t channel)
{
  Wire.beginTransmission(pcaAddr);
  Wire.write(1 << channel);
  return (Wire.endTransmission() == 0);
}

static bool pcaDisableAll(uint8_t pcaAddr)
{
  Wire.beginTransmission(pcaAddr);
  Wire.write(0x00);
  return (Wire.endTransmission() == 0);
}

static uint8_t pcaReadControl(uint8_t pcaAddr)
{
  Wire.requestFrom(pcaAddr, (uint8_t)1);
  if (!Wire.available()) return 0xFF;
  return Wire.read();
}

// --- I2C bus scan ----------------------------------------------------------
// Sweeps 0x08..0x77 and reports every device that acknowledges. Returns
// a rough description for addresses we recognize in the Motion Play system.
static const char* describeAddress(uint8_t addr)
{
  if (addr == 0x60) return "VCNL4040";
  if (addr == 0x70) return "TCA9548A";
  if (addr == 0x74 || addr == 0x75 || addr == 0x76) return "PCA9546A";
  if (addr == 0x6B) return "BQ24195";
  if (addr == 0x40) return "INA219";
  return "unknown";
}

static int scanBus(const char* label)
{
  Serial.print("[scan] ");
  Serial.println(label);

  int found = 0;
  for (uint8_t addr = 0x08; addr <= 0x77; addr++) {
    Wire.beginTransmission(addr);
    uint8_t err = Wire.endTransmission();
    if (err == 0) {
      Serial.print("  0x");
      if (addr < 0x10) Serial.print('0');
      Serial.print(addr, HEX);
      Serial.print("  ");
      Serial.println(describeAddress(addr));
      found++;
    }
  }

  if (found == 0) {
    Serial.println("  (no devices responded)");
  }
  return found;
}

// --- Setup / main ----------------------------------------------------------
void setup()
{
  Serial.begin(115200);
  while (!Serial && millis() < 3000) { /* wait up to 3s for USB serial */ }
  delay(500);

  Serial.println();
  Serial.println("=== VCNL4040 I2C diagnostic ===");
  Serial.print("I2C clock: ");
  Serial.print(I2C_CLOCK_HZ);
  Serial.println(" Hz");

  Wire.begin();
  Wire.setClock(I2C_CLOCK_HZ);

  delay(50);

  // -------- Pass 1: scan the bus as-is. --------
  // In Approach A this finds the PCA9546A (0x74/0x75/0x76).
  // In Approach B this should find the VCNL4040 (0x60) directly.
  int initial = scanBus("Pass 1: bare bus");

  if (initial == 0) {
    Serial.println();
    Serial.println("No devices on the bus at all. Check:");
    Serial.println("  - 3.3V and GND connections (the rigid LED should be lit)");
    Serial.println("  - SDA/SCL are on A4/A5 of the Nano ESP32");
    Serial.println("  - Pull-ups present on SDA and SCL (if using Approach B)");
    return;
  }

  // -------- Pass 2: if a PCA9546A was found, open each of its channels
  // and scan through, looking for the VCNL4040 at 0x60. --------
  Serial.println();
  for (uint8_t pcaAddr : {0x74, 0x75, 0x76}) {
    Wire.beginTransmission(pcaAddr);
    if (Wire.endTransmission() != 0) continue;

    Serial.print("Found PCA9546A at 0x");
    Serial.println(pcaAddr, HEX);

    for (uint8_t ch = 0; ch < 2; ch++) {
      Serial.println();
      Serial.print("--- Opening PCA ch ");
      Serial.print(ch);
      Serial.println(" ---");

      if (!pcaSelectChannel(pcaAddr, ch)) {
        Serial.println("  ERROR: PCA channel write failed");
        continue;
      }
      delay(2);

      // Verify the channel bit actually latched (same trick as the firmware).
      uint8_t ctrl = pcaReadControl(pcaAddr);
      Serial.print("  Control register reads back 0x");
      Serial.println(ctrl, HEX);
      if (ctrl != (1 << ch)) {
        Serial.println("  WARNING: control register mismatch");
      }

      char label[48];
      snprintf(label, sizeof(label), "Pass 2.%d: PCA ch %d downstream", ch, ch);
      scanBus(label);
    }

    pcaDisableAll(pcaAddr);
    break; // only work with the first PCA we find
  }

  Serial.println();
  Serial.println("=== Done ===");
}

void loop()
{
  // One-shot — nothing to do.
  delay(1000);
}

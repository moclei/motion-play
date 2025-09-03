#include <Arduino.h>
#include <TFT_eSPI.h>
#include "pin_config.h"

// Display setup
TFT_eSPI tdisplay = TFT_eSPI();

void setup()
{
    Serial.begin(115200);
    delay(1000);

    // Initialize display power
    pinMode(PIN_POWER_ON, OUTPUT);
    digitalWrite(PIN_POWER_ON, HIGH);

    // Initialize display
    tdisplay.init();
    tdisplay.setRotation(1);
    tdisplay.fillScreen(TFT_BLACK);
    tdisplay.setTextColor(TFT_WHITE);
    tdisplay.setTextDatum(TL_DATUM);

    Serial.println("=== POWER TEST ===");
    Serial.println("Check voltage on VCNL4040 now");

    tdisplay.drawString("POWER TEST", 10, 10, 2);
    tdisplay.drawString("Check VCNL4040 voltage", 10, 40, 2);
    tdisplay.drawString("Should be 3.3V", 10, 70, 2);

    // Do NOT initialize I2C at all
    Serial.println("I2C NOT initialized");
    Serial.println("GPIO43/44 left in default state");

    tdisplay.drawString("I2C NOT initialized", 10, 100, 2);
    tdisplay.drawString("GPIO43/44 default state", 10, 130, 2);
}

void loop()
{
    // Do absolutely nothing that could affect power
    delay(1000);
    Serial.println("Voltage should be stable at 3.3V");
}

#include <Arduino.h>

void setup()
{
    // Initialize Serial with a longer delay to ensure connection
    Serial.begin(115200);
    delay(3000); // Give more time for serial monitor to connect

    Serial.println("\n\n=== ESP32-S3 SERIAL TEST ===");
    Serial.println("If you can see this message, serial communication is working!");
    Serial.printf("Chip model: %s\n", ESP.getChipModel());
    Serial.printf("Chip revision: %d\n", ESP.getChipRevision());
    Serial.printf("CPU frequency: %d MHz\n", ESP.getCpuFreqMHz());
    Serial.printf("Free heap: %d bytes\n", ESP.getFreeHeap());
    Serial.println("===========================");
    Serial.println("This message will repeat every 2 seconds...");
}

void loop()
{
    static int counter = 0;

    Serial.printf("[%d] Hello from ESP32-S3! Uptime: %lu ms\n",
                  counter++, millis());

    // Also try different Serial methods to test compatibility
    Serial.print("Using Serial.print: ");
    Serial.println("SUCCESS");

    Serial.flush(); // Ensure all data is sent
    delay(2000);
}

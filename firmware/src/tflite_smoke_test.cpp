/**
 * TFLite Micro Smoke Test
 *
 * Minimal file to verify TensorFlow Lite Micro compiles with our
 * Arduino + PlatformIO + ESP32-S3 setup.
 *
 * This file is excluded from the normal build via build_src_filter.
 * To test: temporarily swap this into the build filter instead of main.cpp.
 */

#include <Arduino.h>
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

// Minimal tensor arena
constexpr int kTensorArenaSize = 2048;
uint8_t tensor_arena[kTensorArenaSize];

void setup()
{
    Serial.begin(115200);
    delay(1000);

    Serial.println("TFLite Micro smoke test");
    Serial.println("Headers included successfully.");
    Serial.printf("Tensor arena allocated: %d bytes\n", kTensorArenaSize);
    Serial.println("PASS: TFLite Micro compiles with Arduino framework.");
}

void loop()
{
    delay(5000);
}

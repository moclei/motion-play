#pragma once

#include <cstdint>
#include <cstddef>

// --- I2C Bus ---
static constexpr uint32_t I2C_CLOCK_HZ = 400000; // Fast Mode

// --- MUX Timing ---
static constexpr uint8_t MUX_SETTLE_MS = 5; // delay after channel switch

// --- Sensor Defaults ---
static constexpr uint16_t DEFAULT_IR_DUTY_DENOMINATOR = 40; // 1/40 duty cycle

// --- Device Configuration ---
static constexpr size_t CONFIG_JSON_CAPACITY = 1024;
static constexpr const char *CONFIG_FILE_PATH = "/config.json";

// --- Memory Health ---
static constexpr size_t LOW_HEAP_WARNING_BYTES  = 50000;   // 50 KB
static constexpr size_t LOW_PSRAM_WARNING_BYTES = 1000000;  // 1 MB

// --- MQTT ---
static constexpr const char *MQTT_TOPIC_PREFIX = "motionplay/";
static constexpr size_t MQTT_MAX_INCOMING_MSG = 512;

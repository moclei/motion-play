#pragma once

#include <Arduino.h>

extern bool serialStudioEnabled;

inline bool debugPrintEnabled() { return !serialStudioEnabled; }

// Gate Serial.printf behind the Serial Studio flag.
// When Serial Studio is active, debug output is suppressed to keep
// the serial line clean for the structured binary protocol.
#define DEBUG_LOG(fmt, ...) \
    do { if (!serialStudioEnabled) Serial.printf(fmt, ##__VA_ARGS__); } while (0)

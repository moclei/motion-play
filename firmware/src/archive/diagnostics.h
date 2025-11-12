/**
 * Diagnostic Tools Header
 * For analyzing sensor behavior and false triggers
 */

#ifndef DIAGNOSTICS_H
#define DIAGNOSTICS_H

#include <Arduino.h>

// Initialize diagnostic system
void initDiagnostics();

// Start capturing sensor data for analysis
void startCapture(uint32_t duration_ms = 3000);

// Record a sensor reading (called from main sensor loop)
void recordReading(uint16_t ambient[], int16_t variation[], bool triggered[], uint16_t thresholds[]);

// Analyze captured data and print report
void analyzeCapture();

// Dump raw buffer data to serial (for spreadsheet analysis)
void dumpBufferToSerial();

// Print quick status
void printQuickStatus();

#endif // DIAGNOSTICS_H

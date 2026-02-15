# Microsecond Timestamps — Brief

## Problem

The DynamoDB composite sort key for sensor data is `timestamp_offset = (timestamp_ms * 10) + position`. At sensor cycle rates above 1000Hz, `millis()` returns the same value for consecutive cycles (1ms resolution), producing duplicate composite keys. DynamoDB silently overwrites duplicate keys, causing ~28% data loss observed at 1,132Hz actual cycle rate.

## Goal

Eliminate composite key collisions by switching the firmware sensor loop from `millis()` (1ms resolution) to `micros()` (1us resolution). At 1,132Hz, consecutive cycles are ~883us apart — well within microsecond resolution to guarantee unique timestamps.

## Scope

- Firmware: Change `cycleTimestamp` from `millis()` to `micros()`, rename `timestamp_ms` to `timestamp_us` in `SensorReading`, update all references
- Lambda encoding: Update composite key calculation to use microsecond-based relative timestamps
- Lambda decoding: Convert microseconds back to milliseconds for frontend, with backwards compatibility for old sessions
- Frontend: No changes needed (Lambda handles the conversion)
- Documentation: Update DATABASE_SCHEMA.md

## Non-goals

- Data migration of existing sessions (handled via backwards-compatible decoding)
- Changing the composite key pattern itself (the `* 10 + position` scheme is fine)
- Changing session-level timing (start_timestamp, duration_ms stay in milliseconds)

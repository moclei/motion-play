# Microsecond Timestamps — Plan

## Approach

Replace `millis()` with `micros()` in the firmware sensor read cycle. Update the MQTT payload to transmit microsecond timestamps. Update Lambda composite key encoding/decoding. Maintain backwards compatibility for old sessions stored with millisecond timestamps.

## Technical Details

### Firmware

**SensorReading struct** (`SensorManager.h`): Rename `timestamp_ms` to `timestamp_us` (uint32_t — wraps at ~70 minutes, well beyond 35s session max).

**Sensor loop** (`SensorManager.cpp`): Change `cycleTimestamp = millis()` to `cycleTimestamp = micros()`. The per-sensor `readSensor()` also sets `reading.timestamp_ms = millis()` which gets overridden by `cycleTimestamp` — update both.

**Ripple effects**: Every reference to `reading.timestamp_ms` or `buffer[i].timestamp_ms` needs updating:
- `SessionManager.cpp` — buffer access, queue processing
- `DataTransmitter.cpp` — MQTT batch payload (`"ts"` field), duration calculations
- `main.cpp` — Live Debug capture window binary search (cutoff timestamps), duration calculations

**MQTT payload**: The `"ts"` field in batch payloads changes from milliseconds to microseconds. `start_timestamp` stays in milliseconds (session-level timing). The Lambda computes relative timestamps as `(ts_us - start_timestamp_us)`.

**Capture window math**: Constants like `DETECTION_WINDOW_MS` and `MISSED_EVENT_WINDOW_MS` are in milliseconds. Convert to microseconds when comparing against buffer timestamps: `cutoffTs = latestTs - (DETECTION_WINDOW_MS * 1000)`.

### Lambda Encoding (processData)

Current: `compositeKey = (relativeTimestamp_ms * 10) + position`
New: `compositeKey = (relativeTimestamp_us * 10) + position`

The firmware sends `start_timestamp` (millis) and readings with `ts` (micros). The Lambda computes: `relativeTimestamp_us = reading.ts - (start_timestamp * 1000)`. Store derived `timestamp_ms = Math.floor(relativeTimestamp_us / 1000)` for query convenience.

DynamoDB Number type supports up to 38 digits. A 35-second session in microseconds: 35,000,000 × 10 + 5 = 350,000,005. Well within range.

### Lambda Decoding (getSessionData)

Old sessions: `timestamp_offset` values are small (e.g., 1000 = 100ms pos 0).
New sessions: `timestamp_offset` values are large (e.g., 1000000 = 100ms pos 0).

Detection: if any `timestamp_offset` in the session exceeds 1,000,000, it's microsecond-based.

Decoding:
- Old: `timestamp_ms = Math.floor(timestamp_offset / 10)`
- New: `timestamp_ms = Math.floor(timestamp_offset / 10 / 1000)`

The frontend receives millisecond values in both cases — no frontend changes needed.

### Backwards Compatibility

No data migration. The Lambda detects old vs new sessions by magnitude of `timestamp_offset` values and applies the correct decoding. Old sessions continue to work exactly as before.

## Resolved Decisions

- **Field rename**: Rename `timestamp_ms` to `timestamp_us` in firmware for clarity
- **Session-level timing**: Keep `start_timestamp` and `duration_ms` in milliseconds
- **Detection threshold**: Use `timestamp_offset > 1_000_000` to distinguish old/new sessions

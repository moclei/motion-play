# Microsecond Timestamps — Tasks

## Phase 1: Documentation
- [x] Create BRIEF.md
- [x] Create PLAN.md
- [x] Create TASKS.md

## Phase 2: Firmware — SensorReading struct and SensorManager
- [x] Rename `timestamp_ms` to `timestamp_us` in `SensorReading` struct (`SensorManager.h`)
- [x] Change `readSensor()` from `millis()` to `micros()` (`SensorManager.cpp`)
- [x] Change `cycleTimestamp = millis()` to `cycleTimestamp = micros()` in sensor loop (`SensorManager.cpp`)
- [x] Update `DirectionDetector.cpp` — convert `timestamp_us` to ms at entry point (detector algorithm works in ms)

## Phase 3: Firmware — Ripple updates
- [x] Update `DataTransmitter.cpp` — batch payload `"ts"` field uses `timestamp_us`
- [x] Update `DataTransmitter.cpp` — Live Debug duration calculation (us to ms conversion)
- [x] Update `DataTransmitter.cpp` — `start_timestamp` converted to microseconds for consistency
- [x] Update `DataTransmitter.cpp` — `timestamp_unit: "us"` signal field added to all batch payloads
- [x] Update `main.cpp` — missed event capture window (MISSED_EVENT_WINDOW_MS × 1000 for us comparison)
- [x] Update `main.cpp` — detection capture window (DETECTION_WINDOW_MS × 1000 for us comparison)
- [x] Update `main.cpp` — capture duration calculations (us to ms conversion)

## Phase 4: Lambda encoding
- [x] Update `processData/index.js` — composite key uses microsecond relative timestamps when `timestamp_unit === "us"`
- [x] Store derived `timestamp_ms` field (ms) for query convenience

## Phase 5: Lambda decoding
- [x] Update `getSessionData/index.js` — detect old vs new sessions by magnitude (> 1,000,000)
- [x] Apply correct decoding (ms or us) and always return ms to frontend

## Phase 6: Documentation
- [x] Update `DATABASE_SCHEMA.md` composite key section with new scheme and backwards compat

## Phase 7: Deploy and verify
- [x] Deploy updated Lambda
- [x] Flash firmware
- [x] Test: verify 0% composite key collisions (confirmed via `tools/download-session.sh --check-keys` — 772/772 unique keys)
- [ ] Test: verify old sessions still load correctly

## Phase 8: Follow-on fixes (discovered during testing)
- [x] Fix ArduinoJson buffer overflow — `DynamicJsonDocument` 16KB→32KB in `transmitLiveDebugCapture` (200 readings exceeded 16KB, silently truncated to ~143)
- [x] Increase MQTT PubSubClient buffer 16KB→32KB to match (`MQTTManager.cpp`)
- [x] Add `doc.overflowed()` safety check with warning log
- [x] Fix `total_readings_transmitted` counter to use `readingsArray.size()` (actual) instead of `batchCount` (intended)
- [x] Fix cycle rate calculation — use actual collection time (`millis() - sessionStartTime`) instead of capture window duration
- [x] Fix `theoretical_max_readings` — use measured cycle rate × capture window (not configured rate)
- [x] Fix `sample_count` race condition in Lambda — add 5s delay before DynamoDB count query to let batch writes settle

# Session Confirmation — Tasks

## Phase 1: Documentation
- [x] Create BRIEF.md
- [x] Create PLAN.md
- [x] Create TASKS.md

## Phase 2: Firmware — SessionSummary struct and counters
- [x] Define `SessionSummary` struct in SessionManager.h with reset() method
- [x] Add `SessionSummary` instance to `SessionManager`, with reset on session start
- [x] Expose summary via `getSessionSummary()` and `finalizeSessionSummary()`
- [x] Instrument `SensorManager::sensorTaskFunction()`:
  - [x] Check `xQueueSend` return value; increment `readings_collected[pos]` on success, `queue_drops` on failure
  - [x] Increment `i2c_errors[pos]` when `readSensor()` returns false
  - [x] Increment `total_cycles` each loop iteration
- [x] Instrument `SessionManager::processQueue()`: increment `buffer_drops` when buffer full
- [x] Instrument `DataTransmitter`: increment `total_readings_transmitted` and `total_batches_transmitted` after successful MQTT publish (both proximity and Live Debug paths)
- [x] Compute `measured_cycle_rate_hz` and `theoretical_max_readings` at session end via `finalizeSessionSummary()`
- [x] Populate `actual_sample_rate_hz` on `SensorConfiguration` at session end

## Phase 3: Firmware — Summary transmission
- [x] Add `DataTransmitter::transmitSessionSummary()` method — serializes summary as JSON with `type: "session_summary"`, publishes to MQTT data topic, retries up to 3 times
- [x] Call `transmitSessionSummary()` from main.cpp after `transmitProximitySession()` completes (Debug mode)
- [x] Wire up summary for Live Debug detection and missed event captures (finalize before transmit, reset after)
- [x] Resolve merge conflicts from live_debug branch (DataTransmitter.cpp, main.cpp)
- [x] Verify firmware compiles cleanly

## Phase 4: Backend — Lambda changes
- [x] Add `type === "session_summary"` code path in `processData` Lambda: store summary on session item, compute and set `pipeline_status`
- [x] Add `batches_received` atomic counter increment on each data batch in `processData`
- [x] Add Live Debug fields (`capture_reason`, `detection_direction`, `detection_confidence`) to first-batch create/update paths
- [x] Verify `getSessionData` returns new fields without code changes (DynamoDB schemaless)
- [x] Deploy updated Lambda

## Phase 5: Frontend — Time display and API types
- [x] Extend `Session` interface in `api.ts` with `session_summary`, `batches_received`, `pipeline_status`
- [x] Add `SessionSummary` TypeScript interface in `api.ts`
- [x] Add Live Debug fields to `Session` interface (`capture_reason`, `detection_direction`, `detection_confidence`)
- [x] Add "Time Window" stat card to `SessionChart.tsx` showing duration in seconds
- [x] Show selected time range when Brush is active ("Viewing: 0.32s of 0.75s")

## Phase 6: Frontend — Session Confirmation panel
- [x] Build collapsible Session Confirmation panel component
- [x] Pipeline chain display: Firmware Collected -> Queue Drops -> Buffer Drops -> Transmitted -> Lambda Stored -> Frontend Loaded, with green/red indicators
- [x] Per-sensor breakdown table: sensor name, collected, I2C errors, status
- [x] Theoretical vs Actual summary: measured rate × sensors × duration, actual collected, percentage
- [x] Graceful handling when `session_summary` is absent (older sessions)
- [x] Pass `session` prop from App.tsx to `SessionChart`

## Phase 7: Testing and polish
- [x] End-to-end test: Debug mode session — verify summary arrives, pipeline shows complete
- [x] End-to-end test: Live Debug capture — verify summary per mini-session
- [ ] Test graceful degradation: what happens if summary message fails (kill WiFi mid-upload)
- [ ] Test with older sessions that lack summary data — confirm frontend handles absence
- [x] Update DATABASE_SCHEMA.md with new optional session fields

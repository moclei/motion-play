# Session Confirmation — Tasks

## Phase 1: Documentation
- [x] Create BRIEF.md
- [x] Create PLAN.md
- [x] Create TASKS.md

## Phase 2: Firmware — SessionSummary struct and counters
- [ ] Define `SessionSummary` struct (in SessionManager.h or a new header)
- [ ] Add `SessionSummary` instance to `SessionManager`, with reset on session start
- [ ] Expose summary pointer/reference so `SensorManager` and `DataTransmitter` can increment counters
- [ ] Instrument `SensorManager::sensorTaskFunction()`:
  - [ ] Check `xQueueSend` return value; increment `readings_collected[pos]` on success, `queue_drops` on failure
  - [ ] Increment `i2c_errors[pos]` when `readSensor()` returns false
  - [ ] Increment `total_cycles` each loop iteration
- [ ] Instrument `SessionManager::processQueue()`: increment `buffer_drops` when buffer full
- [ ] Instrument `DataTransmitter`: increment `total_readings_transmitted` and `total_batches_transmitted` after successful MQTT publish
- [ ] Compute `measured_cycle_rate_hz` and `theoretical_max_readings` at session end
- [ ] Populate `actual_sample_rate_hz` on `SensorConfiguration` at session end

## Phase 3: Firmware — Summary transmission
- [ ] Add `DataTransmitter::transmitSessionSummary()` method — serializes summary as JSON with `type: "session_summary"`, publishes to MQTT data topic, retries up to 3 times
- [ ] Call `transmitSessionSummary()` from main.cpp after `transmitProximitySession()` completes (Debug mode)
- [ ] Call `transmitSessionSummary()` from main.cpp after `transmitLiveDebugCapture()` completes (Live Debug mode)
- [ ] Verify firmware compiles cleanly

## Phase 4: Backend — Lambda changes
- [ ] Add `type === "session_summary"` code path in `processData` Lambda: store summary on session item, compute and set `pipeline_status`
- [ ] Add `batches_received` atomic counter increment on each data batch in `processData`
- [ ] Verify `getSessionData` returns new fields without code changes (DynamoDB schemaless)
- [ ] Deploy updated Lambda

## Phase 5: Frontend — Time display and API types
- [ ] Extend `Session` interface in `api.ts` with `session_summary`, `batches_received`, `pipeline_status`
- [ ] Add `SessionSummary` TypeScript interface in `api.ts`
- [ ] Add "Time Window" stat card to `SessionChart.tsx` showing duration in seconds
- [ ] Show selected time range when Brush is active ("Viewing: 0.32s of 0.75s")

## Phase 6: Frontend — Session Confirmation panel
- [ ] Build collapsible Session Confirmation panel component
- [ ] Pipeline chain display: Firmware Collected -> Queue Drops -> Buffer Drops -> Transmitted -> Lambda Stored -> Frontend Loaded, with green/yellow/red indicators
- [ ] Per-sensor breakdown table: sensor name, collected, I2C errors, expected
- [ ] Theoretical vs Actual summary: config estimate, actual collected, percentage
- [ ] Graceful handling when `session_summary` is absent (older sessions)

## Phase 7: Testing and polish
- [ ] End-to-end test: Debug mode session — verify summary arrives, pipeline shows complete
- [ ] End-to-end test: Live Debug capture — verify summary per mini-session
- [ ] Test graceful degradation: what happens if summary message fails (kill WiFi mid-upload)
- [ ] Test with older sessions that lack summary data — confirm frontend handles absence
- [ ] Update DATABASE_SCHEMA.md with new optional session fields

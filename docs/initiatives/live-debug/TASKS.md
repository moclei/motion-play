# Live Debug — Tasks

## Phase 1: Documentation and design
- [x] Create BRIEF.md
- [x] Create PLAN.md
- [x] Create TASKS.md
- [x] Add Live Debug reference to PROJECT.md
- [x] Resolve Open Questions in PLAN.md — 0.5s detection window, 3s missed-event window, use existing labels array, no post-capture delay

## Phase 2: Firmware — Live Debug mode and detection capture
- [x] Add `DeviceMode::LIVE_DEBUG` and `set_mode` handler for `live_debug`
- [x] Add `MODE_LIVE_DEBUG` to DisplayManager (enum + rendering)
- [x] Wire Live Debug into `start_collection` (polling branch, mirrors Play setup)
- [x] Wire Live Debug into `stop_collection` (clean stop, no bulk upload)
- [x] Implement Live Debug loop: same as Play (DirectionDetector, LEDs) with higher buffer overflow cap (18,000 samples)
- [x] Implement detection capture flow:
  - [x] On detection: stop sensor polling
  - [x] Extract last N readings (~0.5s window) from buffer
  - [x] Generate session_id, transmit mini-session with `mode: "live_debug"` + detection metadata
  - [x] Show "Transmitting..." on T-Display during pause
  - [x] Clear buffer, reset DirectionDetector, resume polling
- [x] Add `transmitLiveDebugCapture` method to DataTransmitter with larger batch size (200) and shorter delay (20ms)
- [x] Add `capture_missed_event` command handler: same pause-transmit-resume flow, extract full buffer (~3s), `capture_reason: "missed_event"`
- [ ] Test: verify detection capture round-trip (detect → pause → transmit → resume → detect again)
- [ ] Test: verify missed-event capture round-trip

## Phase 3: Backend
- [x] Extend processData Lambda to accept and store optional `capture_reason`, `detection_direction`, `detection_confidence` on session — both update and create paths
- [x] Extend sendCommand Lambda to forward `capture_missed_event` command
- [x] Update DATABASE_SCHEMA.md to document `live_debug` mode and new optional session fields

## Phase 4: Frontend — Mode and event feed
- [x] Add `live_debug` to Header mode selector (mode button + color + label)
- [x] Add "Missed Event" button in Header (visible when Live Debug active and collecting, calls `capture_missed_event`)
- [x] Extend `Session` type in api.ts with optional `capture_reason`, `detection_direction`, `detection_confidence`
- [x] SessionList: add `live_debug` filter option, show LIVE/MISSED badge on live_debug sessions
- [x] Event detail: existing SessionChart + LabelEditor already work for live_debug sessions (proximity data with labels)

## Phase 5: Polish and validation
- [x] Verify firmware compiles (15.2% RAM, 17.7% Flash — no new errors)
- [x] Verify frontend type-checks cleanly
- [x] Clean up PLAN.md — moved resolved questions to "Resolved Design Decisions"
- [ ] Deploy updated Lambdas (processData, sendCommand) — commands prepared, awaiting manual deploy
- [ ] End-to-end test: detection capture round-trip (detect → pause → transmit → resume → detect again)
- [ ] End-to-end test: missed-event capture round-trip
- [ ] End-to-end test: labeling and data retrieval in frontend

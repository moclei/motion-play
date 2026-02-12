# Live Debug — Tasks

## Phase 1: Documentation and design
- [x] Create BRIEF.md
- [x] Create PLAN.md
- [x] Create TASKS.md
- [x] Add Live Debug reference to PROJECT.md
- [ ] Resolve Open Questions in PLAN.md (padding, missed-event window, labels)

## Phase 2: Firmware — Live Debug mode and detection capture
- [ ] Add `DeviceMode::LIVE_DEBUG` and `set_mode` handler for `live_debug`
- [ ] Implement Live Debug loop: same as Play (DirectionDetector, LEDs) with higher buffer overflow cap (~18,000 samples / 3s)
- [ ] Implement detection capture flow:
  - [ ] On detection: stop sensor polling
  - [ ] Extract last N readings (~0.5s window) from buffer
  - [ ] Generate session_id, transmit mini-session with `mode: "live_debug"` + detection metadata (`capture_reason`, `detection_direction`, `detection_confidence`)
  - [ ] Show "Transmitting..." on T-Display during pause
  - [ ] Clear buffer, reset DirectionDetector, resume polling
- [ ] Add Live Debug batch constants (`LIVE_DEBUG_BATCH_SIZE = 200`, `LIVE_DEBUG_BATCH_DELAY = 20`)
- [ ] Add `capture_missed_event` command handler: same pause-transmit-resume flow, extract full buffer (~3s), `capture_reason: "missed_event"`
- [ ] Test: verify detection capture round-trip (detect → pause → transmit → resume → detect again)
- [ ] Test: verify missed-event capture round-trip

## Phase 3: Backend
- [ ] Extend processData Lambda to accept and store optional `capture_reason`, `detection_direction`, `detection_confidence` on session
- [ ] Extend sendCommand Lambda to forward `capture_missed_event` command
- [ ] Update DATABASE_SCHEMA.md to document `live_debug` mode and new optional session fields

## Phase 4: Frontend — Mode and event feed
- [ ] Add `live_debug` to ModeSelector (mode option + description)
- [ ] Add "Missed event" button (visible when Live Debug active and collecting)
- [ ] API: `sendCommand('capture_missed_event')`
- [ ] Extend `Session` type in api.ts with optional `capture_reason`, `detection_direction`, `detection_confidence`
- [ ] Session list: filter or highlight `live_debug` sessions
- [ ] Event detail view: show session data with chart + detection overlay; labeling controls (correct / false positive / wrong direction / missed)

## Phase 5: Polish and validation
- [ ] End-to-end test: detection capture, missed-event capture, labeling, data retrieval
- [ ] Remove resolved Open Questions from PLAN.md

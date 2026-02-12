# Live Debug — Plan

## Approach

Live Debug runs like Play mode (live detection, LEDs, DirectionDetector) but on each detection it pauses sensor polling, captures a short window of sensor data, transmits it as a mini-session, then resumes. A "missed event" command from the frontend triggers capture of a pre-button-press window using the same pause-transmit-resume flow. The same MQTT and Lambda pipeline is used; sessions are smaller and tagged with `mode: "live_debug"`. The frontend shows an event feed and allows labeling.

**High-level flow:**
1. User selects Live Debug in ModeSelector, presses Start → firmware enters Live Debug (same `start_collection` / `stop_collection` flow as Play, but with capture logic).
2. On detection: pause sensor polling → show "Transmitting..." on T-Display → extract data window from buffer → generate session_id → transmit as mini-session via DataTransmitter → clear buffer → resume polling + detector.
3. On "missed event" button (frontend): firmware receives `capture_missed_event` command → same pause-transmit-resume flow, but extracts the full buffer (up to ~3s).
4. Frontend fetches sessions, filters by `mode: "live_debug"`, displays event list with graph + labeling.

## Technical Notes

### Firmware

**New mode**: Add `DeviceMode::LIVE_DEBUG` in `firmware/src/main.cpp`. Reuse Play flow: `DirectionDetector`, `LEDController`, `SensorManager` polling. The Live Debug loop mirrors the existing Play mode loop (lines 1032-1125 of main.cpp) with capture logic added.

**Buffer management**: No new data structure needed. The existing `std::vector<SensorReading, PSRAMAllocator<SensorReading>>` in SessionManager works. Key numbers:
- `SensorReading` is ~12 bytes
- 6 sensors × 1000 Hz = 6,000 readings/sec
- 0.5s window = 3,000 readings = 36 KB
- 3s window = 18,000 readings = 216 KB
- PSRAM has 8 MB — even 3s is only 2.6%

For Live Debug, raise the Play mode's buffer overflow cap (currently 500 samples / ~83ms) to ~18,000 samples (3 seconds). This gives enough history for missed-event captures. On detection, extract the last N readings for the desired window. After capture, clear the buffer.

**Detection capture flow** (when `directionDetector.hasDetection()`):
1. Get `DetectionResult` (direction, confidence, CoM timestamps, peak signals, baselines, thresholds)
2. Stop sensor polling: `sensorManager.stopCollection()`
3. Show "Transmitting..." on T-Display
4. Extract last ~3,000 readings (~0.5s) from `sessionManager.getDataBuffer()`
5. Generate session_id via `SessionManager::generateSessionId()`
6. Transmit window as mini-session with `mode: "live_debug"`, `capture_reason: "detection"`, and detection metadata
7. Clear buffer, reset DirectionDetector
8. Resume polling: `sensorManager.startCollection(queue)`
9. Show "Ready" on T-Display, LED feedback for detection

**Missed-event capture flow** (on `capture_missed_event` MQTT command):
1. Stop sensor polling
2. Show "Capturing missed event..." on T-Display
3. Extract full buffer (up to ~18,000 readings / 3s) from SessionManager
4. Generate session_id, transmit with `mode: "live_debug"`, `capture_reason: "missed_event"`
5. Clear buffer, reset DirectionDetector
6. Resume polling

**Transmission speed**: Current `BATCH_SIZE` is 25 readings with 100ms delay (too slow for this use case). For Live Debug captures, use a larger batch size (~200 readings) and shorter delay (~20ms):
- 0.5s detection window (3,000 readings): ~15 batches × 20ms = **~0.3s pause**
- 3s missed-event window (18,000 readings): ~90 batches × 20ms = **~1.8s pause**

These could be separate constants (`LIVE_DEBUG_BATCH_SIZE`, `LIVE_DEBUG_BATCH_DELAY`) to avoid affecting normal Debug session uploads.

**Post-detection padding**: At the moment of detection, the buffer already contains data through the detection point. The algorithm fires slightly after the physical event, so the buffer naturally includes some post-event data. For v1, just capture what's in the buffer up to the detection moment. If we need explicit post-detection padding later, we can add a short delay before extracting.

**Start/stop flow**: Same as Play mode. Frontend sends `set_mode: "live_debug"`, then `start_collection` to begin, `stop_collection` to end. Individual event captures happen automatically within the session. `start_collection` / `stop_collection` control the overall "listening" period.

**Configurable windows**: Store capture durations as constants initially (`DETECTION_WINDOW_MS = 500`, `MISSED_EVENT_WINDOW_MS = 3000`). Design should make it straightforward to promote these to cloud-configurable settings later (like existing `SensorConfiguration` fields).

### Data Model

Sessions use existing schema. Key fields:
- `mode`: `"live_debug"`
- `session_type`: `"proximity"` (polling data)
- `capture_reason`: `"detection"` or `"missed_event"` — new optional field on session
- `detection_direction`: `"a_to_b"` or `"b_to_a"` — from `DetectionResult` (only for detection captures)
- `detection_confidence`: float — from `DetectionResult`

Detection metadata (direction, confidence, thresholds, peaks) can be included in the first batch payload, following the same pattern as `vcnl4040_config` and `calibration` in `DataTransmitter::transmitBatch()`.

### Backend

- **processData Lambda** (`lambda/processData/index.js`): Already accepts `data.mode` and stores it. Add handling for optional `capture_reason`, `detection_direction`, `detection_confidence` if present — store in session item. No schema migration; DynamoDB is schemaless for optional top-level attributes.
- **sendCommand Lambda** (`lambda/sendCommand/index.js`): Add a case for `capture_missed_event` to forward the command to the device via MQTT.
- **DATABASE_SCHEMA.md** (`infrastructure/DATABASE_SCHEMA.md`): Document `live_debug` as a valid `mode` value and the new optional session attributes.

### Frontend

- **ModeSelector** (`frontend/motion-play-ui/src/components/ModeSelector.tsx`): Add `live_debug` to mode options with label "Live Debug" and description "Live detection with event capture".
- **Missed event button**: Visible when Live Debug is active and collection is running. Calls `api.sendCommand('capture_missed_event')`.
- **Event feed**: New component or view listing recent `live_debug` sessions, each expandable to show SessionChart + detection overlay. Labeling controls: correct / false positive / wrong direction / missed.
- **API types**: Extend `Session` interface in `api.ts` for optional `capture_reason`, `detection_direction`, `detection_confidence`.

### Session ID Strategy

Firmware generates all session IDs, as it already does today. `SessionManager::generateSessionId()` produces `"device-001_" + String(millis())`. The sendCommand Lambda generates a UUID for `start_collection` commands, but the firmware ignores it. No change needed for Live Debug — each capture gets a firmware-generated ID. The frontend discovers sessions by polling `getSessions` filtered by `mode: "live_debug"`.

## Open Questions

- Padding duration: 0.5s total (using buffer data up to detection moment) is the starting plan. Adjust if captures feel too short or long.
- Missed-event window: 3s fixed initially. Make configurable later via cloud settings.
- Labels: Use existing `labels` array on session (e.g. `["correct"]`, `["false_positive"]`) via existing `updateSession` API. No new field needed.
- Post-detection data: The buffer at detection time already contains some post-event data since the algorithm fires late. If we need more, add a configurable post-capture delay. Not needed for v1.

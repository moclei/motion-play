# Serial Studio Integration — Tasks

## Phase 1: Structured Serial Output + Quick Plot

- [x] ~~Increase `monitor_speed` to 921600~~ — Reverted: `Serial.begin(921600)` causes T-Display-S3 black screen. Kept at 115200; USB CDC throughput is unaffected.
- [x] ~~Update `Serial.begin` to 921600~~ — Reverted (see above)
- [x] Add `#define SERIAL_STUDIO_DEFAULT false` build flag; add cloud config override for `serial_studio_enabled`
- [x] Create `SerialStudioOutput.h/.cpp` in `firmware/src/components/serialstudio/`
- [x] Implement frame accumulator: group individual `SensorReading` entries by `timestamp_us` into 6-slot array, emit one CSV frame per completed cycle
- [x] Implement buffer index safety: detect buffer clears (buffer size < last index) and reset
- [x] Use `/*` `*/` frame delimiters, emit `timestamp_us` (microseconds) + 6 proximity values
- [x] Hook `SerialStudioOutput` into main loop (Core 1, after `sessionManager.processQueue()`)
- [x] Suppress verbose periodic debug prints when `serial_studio_enabled` is true
- [ ] Verify serial output does not cause Core 1 loop blocking (latency test, not bandwidth test)
- [ ] Test with Serial Studio Quick Plot mode — confirm 6 sensor traces appear

## Phase 2: Custom Dashboard + Detection Telemetry

- [ ] Add public getters to `DirectionDetector`: `getSmoothedA/B()`, `getThresholdA/B()`, `getWaveStateA/B()`
- [ ] Add detection result caching to `SerialStudioOutput` (cache last direction + confidence independently of detector reset, clear on timeout)
- [ ] Extend frame format with 9 algorithm telemetry fields (1 decimal place for floats)
- [ ] Only emit detection telemetry fields in PLAY and LIVE_DEBUG modes; emit basic sensor-only frames in DEBUG mode
- [ ] Verify extended `Serial.printf()` does not introduce Core 1 loop blocking
- [ ] Create Serial Studio project file `tools/serial-studio/motion-play.json`
- [ ] Design dashboard layout: per-module sensor plots, all-sensors overlay, algorithm plot, detection status grid
- [ ] Test dashboard with live detection events — verify algorithm visualization is useful for tuning

## Phase 3: Local CSV Data Collection

- [ ] Test Serial Studio's built-in CSV export with Phase 2 output — verify all fields captured
- [ ] Create `tools/serial-studio/convert_csv.py` to transform Serial Studio CSV into ML training format
- [ ] Use device-side `timestamp_us` from frame data (not Serial Studio's host-side timestamp)
- [ ] Implement session segmentation in converter (time-gap based)
- [ ] Test end-to-end: collect via Serial Studio CSV → convert → feed to `tools/ml-training/train.py`
- [ ] Document local collection workflow in PLAN.md or as inline notes in converter script

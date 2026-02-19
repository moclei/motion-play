# Serial Studio Integration — Tasks

## Phase 1: Structured Serial Output + Quick Plot ✅

- [x] ~~Increase `monitor_speed` to 921600~~ — Reverted: `Serial.begin(921600)` causes T-Display-S3 black screen. Kept at 115200; USB CDC throughput is unaffected.
- [x] ~~Update `Serial.begin` to 921600~~ — Reverted (see above)
- [x] Add `#define SERIAL_STUDIO_DEFAULT false` build flag; add cloud config override for `serial_studio_enabled`
- [x] Create `SerialStudioOutput.h/.cpp` in `firmware/src/components/serialstudio/`
- [x] Implement frame accumulator: group individual `SensorReading` entries by `timestamp_us` into 6-slot array, emit one CSV frame per completed cycle
- [x] Implement buffer index safety: detect buffer clears (buffer size < last index) and reset
- [x] Use `/*` `*/` frame delimiters, emit `timestamp_us` (microseconds) + 6 proximity values
- [x] Hook `SerialStudioOutput` into main loop (Core 1, after `sessionManager.processQueue()`)
- [x] Suppress verbose periodic debug prints when `serial_studio_enabled` is true
- [x] Verify serial output does not cause Core 1 loop blocking — confirmed: live_debug detection and LED feedback work normally with serial output active
- [x] Test with Serial Studio Quick Plot mode — confirmed: 6 sensor traces visible, spikes on transit events

## Phase 2: Custom Dashboard + Detection Telemetry ✅

- [x] Add public getters to `DirectionDetector`: `getSmoothedA/B()`, `getThresholdA/B()`, `getWaveStateA/B()`
- [x] Add detection result caching to `SerialStudioOutput` (cache last direction + confidence independently of detector reset, clear on timeout)
- [x] Extend frame format with 9 algorithm telemetry fields (1 decimal place for floats)
- [x] Only emit detection telemetry fields in PLAY and LIVE_DEBUG modes; emit basic sensor-only frames in DEBUG mode
- [x] Create Serial Studio project file `tools/serial-studio/motion-play.json`
- [x] Design dashboard layout: per-module sensor plots, all-sensors overlay, algorithm plot, detection status grid
- [x] Verify extended `Serial.printf()` does not introduce Core 1 loop blocking — confirmed: custom dashboard tested with live data
- [x] Test dashboard with live detection events — confirmed: dashboard displays live samples

## Phase 3: Local CSV Data Collection — Deferred

Phase 3 is deferred. The existing frontend-based ML data collection workflow (live_debug mode → labeled event capture → download script → training pipeline) provides better tooling for ML training than Serial Studio CSV export would, because it includes event segmentation and labeling. Serial Studio's value is as a real-time visualization and algorithm debugging tool, not as a data collection pipeline.

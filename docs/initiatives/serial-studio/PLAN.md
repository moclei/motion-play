# Serial Studio Integration — Plan

## Approach

Three phases: (1) basic serial streaming with Quick Plot validation, (2) custom dashboard with detection algorithm telemetry, (3) local CSV collection workflow for ML training. Each phase builds on the previous and is independently useful.

Serial Studio is a standalone desktop application (not a library). It connects to the ESP32's serial port and consumes structured CSV frames emitted by the firmware. The firmware's only responsibility is formatting and printing data; Serial Studio handles visualization and CSV export. A JSON project file configures the dashboard layout and widget mapping.

## Phase 1: Structured Serial Output

### Frame Format

CSV frames with Serial Studio delimiters, one frame per sensor cycle:

```
/*timestamp_us,p1s1,p1s2,p2s1,p2s2,p3s1,p3s2*/
```

- `timestamp_us`: microseconds since boot, matching the `SensorReading.timestamp_us` field directly. Microsecond precision is important at 1000Hz where multiple readings would share the same millisecond value, and is needed for ML training data fidelity.
- `p1s1` through `p3s2`: raw proximity readings from all 6 sensors, ordered by position (0–5)
- `/*` and `*/` delimiters: Serial Studio recognizes these as frame boundaries and ignores all other serial text (debug messages, error logs, etc.)

### USB CDC Throughput

The ESP32-S3 uses USB CDC (`ARDUINO_USB_CDC_ON_BOOT=1`), which is a virtual serial port over USB Full Speed (~12 Mbps). The baud rate passed to `Serial.begin()` is cosmetic — actual throughput is orders of magnitude higher than any frame size concern. There is no bandwidth constraint on frame size or field count.

The real performance concern is whether `Serial.printf()` at 1000Hz causes Core 1 loop blocking due to USB transmit buffer pressure. Phase 1 testing should verify that serial output does not introduce latency in the Core 1 main loop (sensor processing, MQTT, display updates).

### Frame Aggregation Logic

The sensor task on Core 0 produces up to 6 individual `SensorReading` entries per cycle, all sharing the same `timestamp_us` but with different `position` values (0–5). These arrive individually in the session buffer via the FreeRTOS queue.

`SerialStudioOutput` must group these into a single CSV frame:

1. Maintain a 6-slot accumulator array indexed by `position` (0–5)
2. Track the current cycle's `timestamp_us`
3. As each new reading is consumed from the buffer:
   - If `timestamp_us` matches the current cycle: store the proximity value in the appropriate slot
   - If `timestamp_us` changes (new cycle): emit a frame for the completed cycle, then start a new accumulator
4. Handle missing sensors gracefully (emit 0 or a sentinel value for any unfilled slot)

This ensures one frame per cycle regardless of sensor read order or occasional read failures.

### Buffer Index Safety

In PLAY and LIVE_DEBUG modes, `main.cpp` clears the session buffer in two places (after detection and on overflow prevention). This invalidates any tracking index held by `SerialStudioOutput`. The component must detect when the buffer has been cleared (buffer size < last processed index) and reset its index to 0.

### Firmware Architecture

Create a `SerialStudioOutput` component (`firmware/src/components/serialstudio/`):

- Frame accumulator + formatter as described above
- Called in the Core 1 main loop after `sessionManager.processQueue()`
- Tracks its own read position in the buffer, with index-reset safety for buffer clears
- Controlled by `serial_studio_enabled` flag (see Config Flag section below)

### Baud Rate

Keep `Serial.begin(115200)` and `monitor_speed = 115200` as-is. Although USB CDC documentation says the baud rate is cosmetic, testing revealed that `Serial.begin(921600)` causes the T-Display-S3 screen to go black (backlight on, no display output) — likely a side effect in the Arduino-ESP32 framework's USB CDC initialization. Since USB CDC throughput is governed by the USB bus speed (not the baud rate parameter), 115200 does not limit Serial Studio data rates. Set Serial Studio's connection baud rate to 115200 to match.

### Device Mode Behavior

Serial Studio output is emitted in modes where sensor data is being collected:

| Mode | Serial Studio Output | Notes |
|------|---------------------|-------|
| IDLE | No output | Sensor task not running |
| DEBUG | Sensor frames (Phase 1 format) | Raw data collection, no detection |
| PLAY | Full frames with detection telemetry (Phase 2) | Detection active |
| LIVE_DEBUG | Full frames with detection telemetry (Phase 2) | Detection + event capture |

In Phase 1, all active modes emit the basic 7-field frame. Phase 2 extends PLAY/LIVE_DEBUG frames with detection telemetry fields.

### Validation

Open Serial Studio, select the serial port at 921600 baud, enable Quick Plot mode. All 6 proximity channels should plot as separate traces immediately with no project file needed.

## Phase 2: Custom Dashboard + Detection Telemetry

### Extended Frame Format (v10)

Telemetry mode (PLAY/LIVE_DEBUG) emits 28 fields per frame:

```
/*ts,p1s1,p1s2,p2s1,p2s2,p3s1,p3s2,thresh_p1s1,thresh_p1s2,thresh_p2s1,thresh_p2s2,thresh_p3s1,thresh_p3s2,detModule,detDir,detConf,estSpeed,sensorRate,pollRate,intTime,ledCur,dutyCyc,multiPulse,peakA,peakB,waveDurA,waveDurB,comGap*/
```

| Index | Field | Type | Description |
|-------|-------|------|-------------|
| 1 | `ts` | uint32 | Microsecond timestamp |
| 2–7 | `p1s1`–`p3s2` | uint16 | Raw proximity per sensor |
| 8–13 | `thresh_p1s1`–`thresh_p3s2` | float (1dp) | Per-sensor adaptive threshold |
| 14 | `detModule` | int | Which module triggered detection: 0=none, 1–3=module |
| 15 | `detDir` | int | Last detection direction: 0=unknown, 1=a_to_b, 2=b_to_a |
| 16 | `detConf` | float (1dp) | Last detection confidence (0.0–1.0) |
| 17 | `estSpeed` | float (1dp) | Estimated transit speed (m/s), cached from last detection |
| 18 | `sensorRate` | uint16 | Calculated sensor measurement rate (Hz) from IT × duty |
| 19 | `pollRate` | uint16 | Measured I2C polling rate (cycles/sec) |
| 20 | `intTime` | uint16 | Integration time multiplier (e.g. 4 for "4T") |
| 21 | `ledCur` | uint16 | LED current in mA (e.g. 200 for "200mA") |
| 22 | `dutyCyc` | uint16 | Duty cycle denominator (e.g. 40 for "1/40") |
| 23 | `multiPulse` | uint16 | Multi-pulse count (e.g. 1, 2, 4, 8) |
| 24 | `peakA` | uint16 | Peak signal strength for side A of detected module |
| 25 | `peakB` | uint16 | Peak signal strength for side B of detected module |
| 26 | `waveDurA` | uint32 | Wave duration side A (ms), from detected module |
| 27 | `waveDurB` | uint32 | Wave duration side B (ms), from detected module |
| 28 | `comGap` | uint32 | Center-of-mass gap (ms), from detected module |

All 28 fields are numeric. Fields 14–17 and 24–28 are "persistent post-detection metadata": they cache the last detection result and persist in every subsequent frame until a new detection overwrites them.

The v10 frame replaces the v9 smoothedA/B, thresholdA/B, waveA/B, and detState fields (indices 8–14) with 6 per-sensor adaptive thresholds and a detected-module indicator. This reflects the per-sensor detection architecture introduced in DirectionDetector v4.

Config values are emitted as integers to avoid string characters (especially `/` in duty cycle) that conflict with the `*/` frame delimiter and cause serial frame corruption at high data rates.

Basic mode (DEBUG) emits 13 fields: ts, 6 sensors, sensorRate, pollRate, and 4 numeric config values.

### Detection Result Caching

After a detection, the detector is immediately reset (`directionDetector.reset()` or `mlDetector.reset()`), which clears its internal state. `SerialStudioOutput` independently caches the last detection result (direction, confidence, module, peaks, durations, CoM gap) and continues outputting those cached values in each frame until a new detection occurs. There is no timeout — the cached result persists until overwritten, giving the user time to read the dashboard.

### DirectionDetector v4: Per-Sensor Adaptive Thresholds

The detection algorithm was rewritten from side-level aggregation to per-sensor tracking:

- **Per-sensor tracking**: Each of the 6 sensors maintains its own rolling baseline (circular buffer, 200 readings, updated only when IDLE — transit waves excluded), adaptive threshold, and wave state machine.
- **Per-module detection**: When both sensors on a module complete waves within `maxPeakGapMs`, that module produces a direction from center-of-mass comparison.
- **Multi-module consensus**: Multiple modules detecting the same direction boosts confidence. Disagreement lowers it.
- **A/B swap fix**: Sensor positions (0–5) map directly to modules and sides, eliminating the previous side-2-as-A naming inversion.

Public telemetry accessors: `getSensorThreshold(pos)`, `getSensorSmoothed(pos)`, `getSensorWaveState(pos)` for per-sensor data. Legacy `getSmoothedA/B()`, `getThresholdA/B()`, `getWaveStateA/B()` return data from the most recently detected module.

### Serial Studio Project File

Create `tools/serial-studio/motion-play.json` with these widget groups:

- **Module 1** (`multiplot`): P1S1 + P1S2 proximity overlaid
- **Module 2** (`multiplot`): P2S1 + P2S2 proximity overlaid
- **Module 3** (`multiplot`): P3S1 + P3S2 proximity overlaid
- **All Sensors** (`multiplot`): All 6 proximity values overlaid for cross-module comparison
- **All Side A** (`multiplot`): P1S1 + P2S1 + P3S1 — all back-facing sensors overlaid for cross-module comparison
- **All Side B** (`multiplot`): P1S2 + P2S2 + P3S2 — all front-facing sensors overlaid for cross-module comparison
- **Algorithm** (`multiplot`): smoothedA, smoothedB, thresholdA, thresholdB overlaid — shows signal vs threshold in real time
- **Detection Status** (`datagrid`): detector state, wave states, last direction, confidence
- **Sample Rate & Config** (`datagrid`): frames per second (gauge), integration time, LED current, duty cycle, multi-pulse

The project file uses `frameDetection: 0` (end delimiter only) with `\n` as the frame end. The `/*` and `*/` markers remain in the frame data and are validated by a custom JavaScript parser that strips them before splitting on commas. This approach is more robust against USB CDC packetization artifacts than start+end delimiter mode (see Frame Corruption Fix below).

## Phase 3: Local CSV Collection — Deferred

Phase 3 is deferred. The existing frontend-based ML data collection workflow (live_debug mode with labeled event capture, missed event button, download script, training pipeline) is better suited for ML training data than Serial Studio CSV export. The frontend workflow provides event segmentation and labeling, which Serial Studio's continuous CSV stream does not.

Serial Studio's role in this project is real-time visualization and algorithm debugging — Phases 1 and 2 deliver that value. If a local/offline CSV collection workflow becomes needed in the future, this phase can be revisited.

## Technical Notes

### Frame Corruption Fix (v4)

The original Serial Studio integration (v1–v3) suffered from ~10–12% frame corruption in CSV exports. Corrupted rows appeared in pairs: a truncated frame followed by a malformed frame containing data from both.

**Root cause**: The ESP32-S3 uses USB CDC (Hardware CDC, `ARDUINO_USB_MODE=1`), which packetizes serial data into USB transfers. When multiple frames accumulate in the HWCDC TX FIFO between USB host polls, they arrive as a single chunk. Serial Studio's `/*...*/` start+end delimiter parser occasionally misaligned when frame boundaries fell mid-chunk, merging adjacent frames.

**Additional bug found**: The `char buf[64]` used by the snprintf approach was too small for 21-field telemetry frames (~76+ chars). The safety check `(len < sizeof(buf))` silently dropped oversized frames, meaning telemetry mode frames were never actually emitted in v3.

**Fix (v4)**:
1. **Switched to newline-only frame detection** (`frameDetection: 0` / EndDelimiterOnly with `\n` end delimiter). Newline is a single byte — no risk of delimiter splitting across USB packets. Line-oriented parsing trivially handles multiple frames per USB read.
2. **JS parser validates `/*...*/` markers**: The frame parser strips and validates the markers, rejecting any non-frame lines (debug output, partial frames) by returning an empty array.
3. **Reverted to `Serial.printf()`**: Removed the snprintf/Serial.write workaround (and its undersized 64-byte buffer). `Serial.printf()` handles buffer management internally with no frame size limit.
4. **Restored full precision**: Timestamp back to microseconds (`_currentTimestamp` directly), float precision back to `%.1f`.
5. **Removed the 50 FPS output throttle**: With newline framing eliminating corruption, the full sensor rate (~370 Hz) flows to Serial Studio for maximum temporal resolution.
6. **Kept debug print suppression**: The `serialStudioEnabled` guards prevent non-frame serial output from interfering.

**Fixes retained from earlier iterations**:
- Config strings → numeric values (fix #1): prevents `/` in duty cycle from conflicting with `*/`.
- Debug print suppression (fix #2): `extern bool serialStudioEnabled` guards across 6 files.

### Coexistence with Debug Output

When `serial_studio_enabled` is true, debug prints are suppressed by `if (!serialStudioEnabled)` guards across all firmware components. The few that might slip through (e.g., during initialization before the flag is set) are rejected by the Serial Studio JS parser since they lack `/*...*/` markers.

### Config Flag

`serial_studio_enabled` must be usable without cloud access, since Serial Studio's primary value is local/offline development. The enablement strategy:

1. **Compile-time default**: A `#define SERIAL_STUDIO_DEFAULT false` in the build flags. Set to `true` when doing Serial Studio work (via `platformio.ini` build flags or a local override).
2. **Cloud config override**: If WiFi connects and cloud config is fetched, the cloud value overrides the compile-time default. This follows the existing config pattern used by `detection_mode`, `sensor_mode`, etc.

This ensures Serial Studio works immediately on boot without WiFi, while still being remotely controllable via the cloud config when connectivity is available.

### What Serial Studio Is

Serial Studio is a standalone cross-platform desktop app (macOS/Windows/Linux). Install on Mac via `brew install --cask serial-studio`. It connects to a serial port and renders incoming data as configurable dashboards. It is not a library, SDK, or embeddable component — it's a development tool that sits alongside the IDE.

## Open Questions

(none currently)

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

### Extended Frame Format

Add 9 algorithm telemetry fields to the frame (16 fields total):

```
/*ts,p1s1,p1s2,p2s1,p2s2,p3s1,p3s2,smoothA,smoothB,threshA,threshB,waveA,waveB,detState,detDir,detConf*/
```

| Field | Type | Description |
|-------|------|-------------|
| `smoothA`, `smoothB` | float (1dp) | Current smoothed aggregated signal per side |
| `threshA`, `threshB` | float (1dp) | Current adaptive detection threshold per side |
| `waveA`, `waveB` | int | Wave state: 0=idle, 1=in_wave, 2=complete |
| `detState` | int | Detector state: 0=establishing baseline, 1=ready, 2=detecting |
| `detDir` | int | Last detection direction: 0=unknown, 1=a_to_b, 2=b_to_a |
| `detConf` | float (1dp) | Last detection confidence (0.0–1.0) |

USB CDC throughput is not a concern (see Phase 1). The Phase 2 test should verify that the extended `Serial.printf()` call does not introduce Core 1 loop blocking.

### Detection Result Caching

After a detection, the detector is immediately reset (`directionDetector.reset()` or `mlDetector.reset()`), which clears its internal state. `SerialStudioOutput` must independently cache the last detection result (direction, confidence) and continue outputting those cached values in each frame until either:
- A new detection occurs (cache is updated), or
- A timeout elapses (cache is cleared to 0/unknown)

This ensures the detection is visible in the Serial Studio dashboard for a meaningful duration rather than disappearing after a single frame.

### DirectionDetector Changes

Add public getter methods to `DirectionDetector` for:
- `getSmoothedA()` / `getSmoothedB()` — current smoothed values from ring buffers
- `getThresholdA()` / `getThresholdB()` — current adaptive thresholds
- `getWaveStateA()` / `getWaveStateB()` — current wave tracker states

These are read-only accessors to existing internal state. No algorithmic changes.

### Serial Studio Project File

Create `tools/serial-studio/motion-play.json` with these widget groups:

- **Module 1** (`multipleplots`): P1S1 + P1S2 proximity overlaid
- **Module 2** (`multipleplots`): P2S1 + P2S2 proximity overlaid
- **Module 3** (`multipleplots`): P3S1 + P3S2 proximity overlaid
- **All Sensors** (`multipleplots`): All 6 proximity values overlaid for cross-module comparison
- **Algorithm** (`multipleplots`): smoothedA, smoothedB, thresholdA, thresholdB overlaid — shows signal vs threshold in real time
- **Detection Status** (`datagrid`): detector state, wave states, last direction, confidence

The project file uses `frameDetection: 2` (start + end delimiters) with `/*` and `*/`, and a default comma-separated parser.

## Phase 3: Local CSV Collection

### Workflow

1. Launch Serial Studio, load `motion-play.json` project file
2. Click CSV logging button in Serial Studio toolbar
3. Put device in PLAY or LIVE_DEBUG mode
4. Pass objects through hoop — all frames (sensor data + algorithm state) are captured to CSV
5. Stop CSV logging
6. Run conversion script to transform into ML training pipeline format

### Conversion Tooling

Create `tools/serial-studio/convert_csv.py`:

- Reads Serial Studio's timestamped CSV output
- Uses the **device-side timestamp** (`timestamp_us` from the frame data), not Serial Studio's host-side timestamp column, since the device timestamp is synchronized across sensors and has microsecond precision
- Segments into sessions using time gaps or detection events
- Maps columns to the `SensorReading` structure expected by `tools/ml-training/train.py`
- Outputs session files in the format the training pipeline expects (or directly compatible JSON)

### Session Boundaries

Serial Studio captures a continuous stream. Sessions can be segmented by:
- Time gaps (>1 second gap between frames indicates a session boundary)
- Detection events (detDir transitions from 0 to non-zero)
- Explicit markers (firmware could emit a special frame on session start/stop)

The conversion script should support at least the time-gap approach, with detection-event segmentation as an enhancement.

## Technical Notes

### Coexistence with Debug Output

When `serial_studio_enabled` is true, the firmware emits both:
- Structured CSV frames with `/*` ... `*/` delimiters (consumed by Serial Studio)
- Normal `Serial.print` debug messages (ignored by Serial Studio)

Serial Studio only parses lines matching its frame delimiters. Debug text passes through harmlessly. However, when `serial_studio_enabled` is true, verbose periodic debug prints (e.g., the 2-second `[PLAY] Buffer: %d samples` messages) should be suppressed or reduced to keep the serial path clean and avoid unnecessary USB buffer contention.

### Config Flag

`serial_studio_enabled` must be usable without cloud access, since Serial Studio's primary value is local/offline development. The enablement strategy:

1. **Compile-time default**: A `#define SERIAL_STUDIO_DEFAULT false` in the build flags. Set to `true` when doing Serial Studio work (via `platformio.ini` build flags or a local override).
2. **Cloud config override**: If WiFi connects and cloud config is fetched, the cloud value overrides the compile-time default. This follows the existing config pattern used by `detection_mode`, `sensor_mode`, etc.

This ensures Serial Studio works immediately on boot without WiFi, while still being remotely controllable via the cloud config when connectivity is available.

### What Serial Studio Is

Serial Studio is a standalone cross-platform desktop app (macOS/Windows/Linux). Install on Mac via `brew install --cask serial-studio`. It connects to a serial port and renders incoming data as configurable dashboards. It is not a library, SDK, or embeddable component — it's a development tool that sits alongside the IDE.

## Open Questions

(none currently)

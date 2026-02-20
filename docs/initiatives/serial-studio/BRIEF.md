# Serial Studio Integration

**Status:** ✅ Complete (Phases 1-2 delivered, Phase 3 deferred)

## Intent

Integrate Serial Studio as a local development tool for real-time sensor visualization and detection algorithm debugging. This provides a faster feedback loop for firmware development by eliminating the need for the full MQTT/AWS pipeline during iterative work.

## Goals

- Stream all 6 sensor proximity readings to Serial Studio in real time at 1000Hz via structured serial output.
- Visualize detection algorithm internals (smoothed signals, adaptive thresholds, wave states) for algorithm tuning.
- Enable local CSV data collection via Serial Studio's built-in export, replacing the cloud pipeline for ML training data workflows.
- Create a custom Serial Studio dashboard tailored to the 3-module, 6-sensor hoop layout.
- Make Serial Studio output togglable via config flag so it doesn't interfere with normal serial debugging.

## Scope

What's in:
- Structured CSV serial output at 1000Hz (one frame per sensor cycle)
- Baud rate increase to 921600
- `SerialStudioOutput` firmware component
- Detection algorithm telemetry exposure (smoothed values, thresholds, wave states)
- Serial Studio project file (custom dashboard with per-module plots, algorithm visualization, detection status)
- Local CSV collection workflow and conversion tooling for ML training pipeline
- Initiative documentation

What's out:
- BLE connectivity (separate future initiative)
- Serial Studio Pro features (MQTT, FFT, XY plots, 3D)
- Frontend redesign using Serial Studio as a backend
- Replacing the AWS cloud infrastructure
- Bi-directional communication (commands from Serial Studio to device)
- Ambient light data in Serial Studio output (proximity only for now)

## Constraints

- Core 0 sensor collection (1000Hz) must not be affected; all serial output on Core 1.
- USB CDC virtual serial (not hardware UART) — baud rate is cosmetic, but `Serial.printf()` at 1000Hz must not block Core 1 from USB transmit buffer pressure.
- Free/GPL Serial Studio version only — no Pro features.
- Must coexist with existing serial debug output (frame delimiters isolate structured data).
- Must be usable offline — cannot require cloud/WiFi access just to enable a local debug tool.

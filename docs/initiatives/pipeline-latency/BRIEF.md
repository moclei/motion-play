# Pipeline Latency Reduction

## Intent

Reduce the live debug pipeline end-to-end latency from ~20 seconds to under 6 seconds so the detection-to-chart feedback loop is fast enough for iterative algorithm tuning.

## Goals

- End-to-end latency (transit event → chart rendered) under 6 seconds on average
- Eliminate concurrent Lambda invocations for live debug captures
- Remove the fixed 5-second settle delay from the summary Lambda
- Maintain backward compatibility — existing session data and non-live-debug flows unaffected

## Scope

What's in:
- Frontend polling interval reduction
- Lambda smart settle (replace fixed sleep with polling loop)
- Binary payload packing on firmware (9-byte struct per reading, base64-encoded)
- Lambda decoder for the binary format
- Streaming MQTT publish via PSRAM buffer to support single-message transmission
- Merging data + summary into a single MQTT message for live debug captures

What's out:
- WebSocket push or MQTT-to-browser (future initiative if needed)
- Progressive/partial chart rendering
- Time-series database migration
- Changes to non-live-debug data flows (debug mode collection, normal sessions)
- Post-detection delay tuning (negligible impact on total latency)

## Constraints

- PubSubClient v2.8 uses `uint16_t bufferSize` — hard ceiling of 65,535 bytes per MQTT message
- AWS IoT Core MQTT limit is 128 KB per message
- Binary payload must use little-endian byte order (ESP32 native) — Lambda must decode accordingly
- Existing IoT Rule (`SELECT * FROM 'motionplay/+/data'`) expects JSON — binary readings are base64-encoded inside a JSON wrapper, not a raw binary payload
- ESP32 internal heap cannot allocate 60+ KB contiguously — large payloads must use PSRAM buffers and PubSubClient streaming API
- Origin exploration: `docs/explorations/pipeline-latency.md`

## Status

**Complete.** Both phases implemented and tested. See PLAN.md for implementation notes.

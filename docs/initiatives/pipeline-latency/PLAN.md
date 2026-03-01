# Pipeline Latency Reduction — Plan

## Approach

Two phases targeting the three biggest latency contributors: the 5s settle delay, the 2.5s average polling delay, and the concurrent Lambda overhead from ~23 separate MQTT messages.

Phase 1 addresses polling and settle with trivial code changes. Phase 2 eliminates the root cause by packing all readings into a single MQTT message using binary encoding.

## Phase 1: Quick Wins

### Frontend Polling (SessionList.tsx)

Change the `setInterval` in `SessionList.tsx` from `5000` to `2000`. The `GET /sessions` call is lightweight (DynamoDB scan, limited to 50 items), and this is a single-user debug tool.

**File:** `frontend/motion-play-ui/src/components/SessionList.tsx` (line 124)

### Lambda Smart Settle (processData/index.js)

Replace the fixed `BATCH_SETTLE_DELAY_MS = 5000` sleep in `processSessionSummary` with a polling loop:

1. Poll DynamoDB every 200ms, querying the actual reading count for the session (`SELECT COUNT` on `MotionPlaySensorData`)
2. Compare against `summary.total_readings_transmitted`
3. Exit as soon as count matches (or >= 95% delivery rate, matching existing logic)
4. Timeout fallback at 8s to handle failed batch Lambdas

This reuses the existing `countResult` query that already runs after the sleep. The only change is running it in a loop instead of once after a fixed delay.

**File:** `lambda/processData/index.js` (lines 419–451, `processSessionSummary` function)

## Phase 2: Binary Payload Packing

### Binary Reading Format ("bin9")

Each `SensorReading` is packed as 9 bytes in little-endian order:

| Offset | Field | Type | Bytes |
|--------|-------|------|-------|
| 0 | `timestamp_us` | uint32_t | 4 |
| 4 | `position` | uint8_t | 1 |
| 5 | `proximity` | uint16_t | 2 |
| 7 | `ambient` | uint16_t | 2 |

`pcb_id` and `side` are omitted — they're derived from `position` on the Lambda side:
- `pcb_id = Math.floor(position / 2) + 1`
- `side = (position % 2) + 1`

### Size Budget

| | Per reading | 4,500 readings (6 sensors, 750ms) |
|---|---|---|
| Raw binary | 9 bytes | 40,500 bytes |
| Base64 | 12 bytes | ~54,000 bytes |
| + JSON wrapper | | ~56,000 bytes |

Well within both the 128 KB MQTT limit and the 65,535-byte PubSubClient buffer ceiling.

### Firmware Changes (DataTransmitter)

1. **Increase PubSubClient buffer** in `MQTTManager.cpp`: `setBufferSize(61440)` (60 KB).
2. **New method** in `DataTransmitter`: `transmitLiveDebugCaptureBinary()`.
   - Allocate binary buffer in PSRAM: `ps_malloc(captureCount * 9)`.
   - Pack each reading as 9 bytes (direct `memcpy` of struct fields).
   - Base64-encode using `mbedtls_base64_encode` (available on ESP32 via mbedTLS).
   - Build a single JSON document containing:
     - Session metadata (session_id, device_id, mode, config, capture_reason, detection results)
     - `"reading_format": "bin9"`, `"reading_count": N`, `"readings_b64": "<base64>"`
     - Session summary fields (total_cycles, drops, etc.) — merged into the same message
   - ArduinoJson `DynamicJsonDocument` size: ~60 KB (the base64 string dominates).
   - Publish to the existing data topic as a single MQTT message.
3. **Keep existing JSON path** as a fallback — the binary path is gated on `mode == "live_debug"`. Normal debug/collection sessions continue using the existing batch approach.

### Lambda Changes (processData/index.js)

1. **Detect binary format**: check for `data.reading_format === 'bin9'` and `data.readings_b64`.
2. **Decode**: `Buffer.from(data.readings_b64, 'base64')`, then read fields at 9-byte intervals using `readUInt32LE`, `readUInt16LE`, and direct byte access.
3. **Derive** `pcb_id` and `side` from `position`.
4. **Write to DynamoDB**: reuse existing `BatchWriteCommand` logic with the unpacked readings array.
5. **Skip settle delay**: when a message contains both readings and a summary (detected by presence of `type: "session_summary"` fields alongside `readings_b64`), process the summary inline — no concurrent Lambda race, no polling needed.

### Message Flow (Before vs After)

**Before (current):**
```
Firmware → 23 MQTT messages (20ms apart) → 23 Lambda invocations → concurrent DynamoDB writes
Firmware → 1 summary MQTT message → 1 Lambda invocation → 5s sleep → query count → set status
Frontend → poll every 5s → detect completion → fetch data → render
```

**After (Phase 2):**
```
Firmware → 1 MQTT message (data + summary) → 1 Lambda invocation → DynamoDB write → set status
Frontend → poll every 2s → detect completion → fetch data → render
```

## Open Questions

- ArduinoJson `DynamicJsonDocument` at 60 KB: verify this allocates from PSRAM on ESP32-S3 with the current platformio memory config. If it uses heap, may need to use `SpiRamJsonDocument` or allocate the buffer manually.
- Should the smart settle (Phase 1) be left in place after Phase 2, as a fallback for non-binary sessions? Likely yes — it's harmless and handles edge cases.

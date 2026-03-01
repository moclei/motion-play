# Pipeline Latency Reduction — Tasks

## Phase 1: Quick Wins

- [x] Reduce frontend polling interval from 5s to 2s in `SessionList.tsx`
- [x] Replace fixed 5s `BATCH_SETTLE_DELAY_MS` in `processData/index.js` with a polling loop (200ms interval, 8s timeout, exit on count match)
- [x] Deploy updated Lambda
- [x] Test Phase 1 end-to-end — verify latency improvement and that session completion still detects reliably

## Phase 2: Binary Payload Packing

- [x] Implement `transmitLiveDebugCaptureBinary()` in `DataTransmitter` — binary packing, base64 encoding, merged data+summary message
- [x] Add streaming MQTT publish in `MQTTManager` — serialize to PSRAM, send in 4KB chunks (replaces the planned buffer increase, which failed due to heap constraints)
- [x] Add binary format detection in `processData/index.js` — decode base64, unpack bin9, derive pcb_id/side
- [x] Handle combined data+summary messages in Lambda — skip settle delay when both are present
- [x] Deploy updated Lambda
- [x] Flash firmware and test end-to-end with 6 sensors — verify all readings arrive and pipeline_status is set correctly

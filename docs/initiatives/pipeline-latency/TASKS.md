# Pipeline Latency Reduction — Tasks

## Phase 1: Quick Wins

- [ ] Reduce frontend polling interval from 5s to 2s in `SessionList.tsx`
- [ ] Replace fixed 5s `BATCH_SETTLE_DELAY_MS` in `processData/index.js` with a polling loop (200ms interval, 8s timeout, exit on count match)
- [ ] Deploy updated Lambda
- [ ] Test Phase 1 end-to-end — verify latency improvement and that session completion still detects reliably

## Phase 2: Binary Payload Packing

- [ ] Increase PubSubClient buffer to 60 KB in `MQTTManager.cpp`
- [ ] Implement `transmitLiveDebugCaptureBinary()` in `DataTransmitter` — binary packing, base64 encoding, merged data+summary message
- [ ] Verify ArduinoJson large document allocation works with PSRAM (test with 4,500+ readings)
- [ ] Add binary format detection in `processData/index.js` — decode base64, unpack bin9, derive pcb_id/side
- [ ] Handle combined data+summary messages in Lambda — skip settle delay when both are present
- [ ] Deploy updated Lambda
- [ ] Flash firmware and test end-to-end with 6 sensors — verify all readings arrive and pipeline_status is set correctly
- [ ] Measure final end-to-end latency and compare against baseline

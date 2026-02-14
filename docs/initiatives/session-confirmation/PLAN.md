# Session Confirmation — Plan

## Approach

The core idea is **measure, don't just predict**. The firmware tracks exactly what happened during a session (reads, errors, drops at each stage) and reports a summary after all data batches are transmitted. The Lambda stores this summary alongside the session and computes a pipeline status. The frontend displays a confirmation panel comparing counts at every stage of the pipeline, plus a theoretical maximum derived from config settings.

The summary is sent as a separate MQTT message (not embedded in the last data batch) so that data batch transmission is not affected if the summary fails. The summary message gets up to 3 retries. If it never arrives, the frontend shows "Summary not received" — graceful degradation rather than failure.

**High-level flow:**

1. Firmware collects sensor readings on Core 0. Counters track successful reads, I2C errors, queue drops per sensor.
2. SessionManager drains the queue into the PSRAM buffer. A counter tracks buffer-full drops.
3. DataTransmitter sends readings in batches via MQTT. Counters track readings transmitted and batches sent.
4. After all batches complete, DataTransmitter sends a separate `session_summary` message with all counters, the measured cycle rate, theoretical max, and duration.
5. Lambda's `processData` function handles the summary message: stores it on the session item, compares `total_readings_transmitted` vs `sample_count`, sets `pipeline_status`.
6. Frontend fetches the session and displays the confirmation panel: pipeline chain, per-sensor breakdown, theoretical vs actual, time in seconds.

## Technical Notes

### Firmware

**New struct** — `SessionSummary` (in a new header, or in `SessionManager.h`):

```cpp
struct SessionSummary {
    uint32_t total_cycles;              // Sensor loop iterations
    uint32_t readings_collected[6];     // Successful reads per sensor position
    uint32_t i2c_errors[6];            // Failed reads per sensor position
    uint32_t queue_drops;              // Readings lost due to full queue
    uint32_t buffer_drops;             // Readings lost due to full buffer
    uint32_t total_readings_transmitted; // Sum of readings across all MQTT batches
    uint32_t total_batches_transmitted;  // Number of MQTT batches sent
    uint16_t measured_cycle_rate_hz;    // total_cycles / (duration_ms / 1000)
    uint32_t duration_ms;              // Actual session duration
    uint32_t theoretical_max_readings;  // sample_rate_hz * (duration_ms / 1000) * active_sensors
    uint8_t  num_active_sensors;        // How many sensors were active
};
```

**Counter instrumentation points:**

- `readings_collected[pos]` — `SensorManager::sensorTaskFunction()`, after successful `readSensor()` AND successful `xQueueSend` (line ~943 of SensorManager.cpp). Currently the queue send result is not checked.
- `i2c_errors[pos]` — `SensorManager::sensorTaskFunction()`, when `readSensor()` returns false (line ~960 area, where errors are already logged).
- `queue_drops` — `SensorManager::sensorTaskFunction()`, when `xQueueSend` returns `errQUEUE_FULL` (same location, currently not tracked).
- `buffer_drops` — `SessionManager::processQueue()`, at line ~132 where "Buffer full, dropping samples" is logged.
- `total_readings_transmitted` / `total_batches_transmitted` — `DataTransmitter::transmitBatch()` / `transmitProximitySession()` / `transmitLiveDebugCapture()`, after successful MQTT publish.
- `measured_cycle_rate_hz` — computed at session end in SessionManager or main.cpp.
- `theoretical_max_readings` — computed at session end: `config->sample_rate_hz * (duration_ms / 1000.0f) * num_active_sensors`.

**Summary ownership:** The `SessionSummary` struct lives in `SessionManager` (it already owns the buffer and session state). `SensorManager` increments `readings_collected`, `i2c_errors`, and `queue_drops` via a pointer or reference to the summary. `DataTransmitter` increments `total_readings_transmitted` and `total_batches_transmitted`.

**Summary transmission** — new method `DataTransmitter::transmitSessionSummary(const SessionSummary& summary, const String& sessionId)`:

- Serializes the summary as JSON with `type: "session_summary"` and the same `session_id`.
- Publishes to the same MQTT data topic.
- Retries up to 3 times with 500ms delay on failure.
- Called from `main.cpp` after `transmitProximitySession()` or `transmitLiveDebugCapture()` completes.

**MQTT message format:**

```json
{
  "type": "session_summary",
  "session_id": "device-001_123456",
  "device_id": "motionplay-device-001",
  "summary": {
    "total_cycles": 750,
    "readings_collected": [750, 748, 750, 750, 749, 750],
    "i2c_errors": [0, 2, 0, 0, 1, 0],
    "queue_drops": 0,
    "buffer_drops": 0,
    "total_readings_transmitted": 4497,
    "total_batches_transmitted": 180,
    "measured_cycle_rate_hz": 1000,
    "duration_ms": 750,
    "theoretical_max_readings": 4500,
    "num_active_sensors": 6
  }
}
```

**actual_sample_rate_hz:** Populated on the `SensorConfiguration` struct at session end: `config->actual_sample_rate_hz = summary.measured_cycle_rate_hz`. This means existing code paths in `DataTransmitter` that already serialize this field will pick up the real value instead of 0.

**Applies to Debug and Live Debug.** For Live Debug, each mini-capture gets its own summary (the buffer is small, so the summary is computed quickly). In Debug mode, the summary is computed after the 30-second collection period ends.

### Backend (Lambda)

**processData Lambda** (`lambda/processData/index.js`):

Add a third code path for `data.type === "session_summary"`:

```javascript
if (data.type === 'session_summary') {
    // Update existing session with summary and pipeline_status
    const session = await getSession(data.session_id);
    const sampleCount = session?.sample_count || 0;
    const transmitted = data.summary.total_readings_transmitted;
    const pipelineStatus = sampleCount === transmitted ? 'complete'
                         : sampleCount < transmitted ? 'partial'
                         : 'pending';
    await updateSession(data.session_id, {
        session_summary: data.summary,
        pipeline_status: pipelineStatus
    });
    return;
}
```

Also add `batches_received` counter — increment atomically (DynamoDB `ADD`) on each data batch, same pattern as `sample_count`.

**getSessionData Lambda** (`lambda/getSessionData/index.js`):

No code changes needed. DynamoDB returns all attributes on the session item, so `session_summary`, `batches_received`, and `pipeline_status` will be included automatically once they exist.

### Frontend

**Time display** — changes to `SessionChart.tsx`:

- Compute `durationSeconds = (maxTimestamp - minTimestamp) / 1000` from the readings array.
- Add a "Time Window" stat card alongside existing Total Readings / Avg / Max / Min cards: "Time Window: 0.75s".
- When Brush is active and a range is selected, show "Viewing: 0.32s of 0.75s" in the stats area.
- Consider converting x-axis labels to seconds for sessions longer than ~2 seconds.

**Session Confirmation panel** — new collapsible section in the session detail view:

Pipeline chain (vertical steps with counts and status indicators):
- Firmware Collected: `sum(summary.readings_collected)` — green if > 0
- I2C Errors: `sum(summary.i2c_errors)` — green if 0, yellow/red otherwise
- Queue Drops: `summary.queue_drops` — green if 0, red otherwise
- Buffer Drops: `summary.buffer_drops` — green if 0, red otherwise
- Firmware Transmitted: `summary.total_readings_transmitted`
- Lambda Stored: `session.sample_count` — green if matches transmitted, red otherwise
- Frontend Loaded: `readings.length` — green if matches stored, red otherwise

Per-sensor breakdown table:
- Columns: Sensor (P1S1..P3S2), Collected, I2C Errors, Expected (theoretical per sensor)
- Highlight sensors with errors or below-expected counts

Theoretical vs Actual summary:
- "Config estimate: {sample_rate} Hz x {active_sensors} sensors x {duration}s = {theoretical_max} readings"
- "Actual collected: {total_collected} ({percentage}% of theoretical)"
- "Frontend displaying: {readings.length} ({percentage}% of collected)"

If `session_summary` is not present (older sessions or summary message failed), show "Session summary not available" with a muted style.

**API types** — extend `Session` interface in `api.ts`:

```typescript
interface SessionSummary {
  total_cycles: number;
  readings_collected: number[];   // per sensor position [0-5]
  i2c_errors: number[];           // per sensor position [0-5]
  queue_drops: number;
  buffer_drops: number;
  total_readings_transmitted: number;
  total_batches_transmitted: number;
  measured_cycle_rate_hz: number;
  duration_ms: number;
  theoretical_max_readings: number;
  num_active_sensors: number;
}

// Add to Session interface:
session_summary?: SessionSummary;
batches_received?: number;
pipeline_status?: 'complete' | 'partial' | 'pending';
```

## Resolved Decisions

- **Summary transmission:** Separate MQTT message after all data batches, with 3 retries. Not embedded in last batch.
- **Checksum:** Deferred to future iteration. Counts at each stage are sufficient for v1.
- **Theoretical max:** Included. Computed by firmware, sent in summary, displayed on frontend.
- **actual_sample_rate_hz:** Populated as part of this initiative from measured cycle rate.

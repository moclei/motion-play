# Pipeline Latency — Exploration

## Problem

The live debug pipeline — from a transit event through the hoop to the chart rendering on the frontend — takes up to 30 seconds on average. For iterative development and algorithm tuning, this feedback loop is too slow. The goal is to understand where time is spent and evaluate options for reducing end-to-end latency.

## Current State

### The Pipeline

A transit event triggers this sequence:

| Stage | What Happens | Latency |
|-------|-------------|---------|
| 1. Detection | Algorithm fires on-device | ~0ms |
| 2. Post-detection capture | Firmware collects 250ms of trailing data | **250ms** fixed |
| 3. Queue drain | Waits for sensor queue to flush | **50ms** fixed |
| 4. Data extraction | Extracts 750ms window (500ms pre + 250ms post) from circular buffer | ~10ms |
| 5. MQTT batch transmission | ~8 batches × 20ms inter-batch delay | **~160ms** |
| 6. IoT Core routing | IoT Rule matches topic, invokes Lambda | ~50–100ms |
| 7. Lambda processing | Each batch triggers a concurrent Lambda; DynamoDB BatchWrite | **1–3s** per batch |
| 8. Session summary Lambda | Receives summary, sleeps 5s waiting for batch Lambdas | **5,000ms** fixed |
| 9. Pipeline status update | Summary Lambda queries DynamoDB, sets `pipeline_status` | ~200ms |
| 10. Frontend polling | Polls session list every 5s, waits for status change | **0–5,000ms** avg 2,500ms |
| 11. Auto-select + data fetch | Fetches full session data from API | **200ms–2s** |
| 12. Chart render | Client-side processing + Recharts | **50–500ms** |

**Estimated totals:** best case ~8s, average ~15–20s, worst case ~30s.

### Key Code Locations

- **Firmware capture & batching**: `firmware/src/main.cpp` (live debug handling), `firmware/src/components/data/DataTransmitter.cpp` (batch transmission)
- **Firmware constants**: `LIVE_DEBUG_BATCH_SIZE = 200`, `LIVE_DEBUG_BATCH_DELAY = 20ms`, `POST_DETECTION_DELAY_MS = 250ms`, `DETECTION_WINDOW_MS = 500ms`
- **Lambda ingestion**: `lambda/processData/index.js` (batch processing, `BATCH_SETTLE_DELAY_MS = 5000`)
- **Lambda retrieval**: `lambda/getSessionData/index.js` (DynamoDB query with pagination)
- **Frontend polling**: `frontend/motion-play-ui/src/components/SessionList.tsx` (5s `setInterval`)
- **Frontend chart**: `frontend/motion-play-ui/src/components/SessionChart.tsx` (Recharts rendering)

### Three Biggest Bottlenecks

1. **`BATCH_SETTLE_DELAY` (5s)** — The session summary Lambda sleeps 5 seconds to wait for concurrent batch-processing Lambdas to finish their DynamoDB writes. This exists because the firmware sends all batches in ~160ms, then immediately sends the summary. Each batch Lambda takes 1–3s to complete, so without the delay the summary would query DynamoDB before all data is written, producing an inaccurate pipeline count.

2. **Frontend polling interval (5s)** — HTTP polling every 5 seconds means an average of 2.5 seconds wasted waiting for the next poll cycle to detect the session status change.

3. **Concurrent Lambda processing (1–3s + cold starts)** — Each of ~8 MQTT batches triggers its own Lambda invocation. These run concurrently but each takes 1–3s. Cold starts can add another 1–2s on top.

## Options

### Option A: Consolidate MQTT Batches

**What:** Increase the firmware batch size so the entire live debug capture (~1,500 readings) fits in 1–2 MQTT messages instead of ~8.

**Effort:** Low — firmware constant change + minor Lambda adjustment.

**Impact:** High. A single MQTT message means a single Lambda invocation, which eliminates the need for `BATCH_SETTLE_DELAY` entirely (no concurrent write race). Also removes ~160ms of inter-batch delay on the firmware side. The 128 KB AWS IoT Core message limit accommodates ~1,500 readings at ~40–50 bytes each (~60–75 KB).

**Trade-offs:**
- Larger single messages increase risk of MQTT publish failure (one retry = full retransmit)
- ESP32 needs enough contiguous memory to build the JSON document (~64–96 KB)
- PubSubClient's default buffer is 32 KB and would need increasing — or a streaming JSON approach

### Option B: Smart Settle Instead of Fixed 5s Sleep

**What:** Replace the 5-second `BATCH_SETTLE_DELAY` in the summary Lambda with a polling loop that checks `batches_received` against the expected count from the firmware summary (which includes `total_batches_transmitted`). Poll every 100–200ms, complete as soon as counts match.

**Effort:** Low — Lambda code change only.

**Impact:** Medium. Batch Lambdas typically finish in 1–3s, so this would reduce the settle wait from 5s to ~2–3s. Saves 2–3 seconds.

**Trade-offs:**
- Adds DynamoDB read cost (polling the session record every 100–200ms)
- Need a timeout fallback in case a batch Lambda fails silently
- Doesn't eliminate the root cause (concurrent Lambdas), just responds faster

### Option C: Reduce Frontend Polling Interval

**What:** Change the frontend polling interval from 5 seconds to 1–2 seconds.

**Effort:** Trivial — one constant change.

**Impact:** Medium. Reduces average polling delay from 2.5s to 0.5–1s. The `GET /sessions` call is lightweight.

**Trade-offs:**
- Slightly higher API Gateway / Lambda invocation cost
- Marginal — this is a debug tool, not a production service with many users

### Option D: WebSocket Push from Backend to Frontend

**What:** Replace HTTP polling with a real-time push channel. When `pipeline_status` is set to `complete`, the Lambda publishes a notification that reaches the frontend immediately.

Options within this option:
- MQTT-over-WebSocket via AWS IoT Core (frontend subscribes to a notification topic)
- API Gateway WebSocket API
- Server-Sent Events (SSE) via a lightweight endpoint

**Effort:** Medium — new frontend connection management, auth for WebSocket, backend publish step.

**Impact:** High. Eliminates the entire 0–5s polling delay. The frontend knows a session is ready within milliseconds of the status update.

**Trade-offs:**
- Adds connection management complexity (reconnection, auth refresh)
- AWS IoT Core WebSocket requires SigV4 signing or a custom authorizer
- API Gateway WebSocket API has its own operational overhead
- Overkill if Option C (faster polling) is "good enough"

### Option E: Optimistic / Progressive Rendering

**What:** Instead of waiting for `pipeline_status === 'complete'`, the frontend detects a new session appearing (still `pending`) and immediately begins fetching whatever data is available. Renders a partial chart that fills in as more data arrives.

**Effort:** Medium — frontend changes to support incremental data loading and chart updates.

**Impact:** Medium-high. The user sees *something* within a few seconds of the event, even if the final data isn't all there yet. Perception of latency improves significantly even if total pipeline time doesn't change.

**Trade-offs:**
- More complex frontend state management
- Chart may visually "jump" as late-arriving data fills in
- Need to handle the case where batches arrive out of order
- `getSessionData` currently returns the full session — would need to work with partial data

### Option F: Direct MQTT-to-Browser for Live Debug

**What:** For live debug sessions specifically, bypass the entire cloud storage pipeline. Firmware publishes to a dedicated topic (e.g., `motionplay/{device_id}/live_data`). The frontend subscribes to this topic via MQTT-over-WebSocket and renders data as it arrives. DynamoDB storage happens asynchronously in the background if persistence is needed.

**Effort:** High — new frontend MQTT client, auth setup, new firmware topic, optional background persistence Lambda.

**Impact:** Very high. Eliminates Lambda, DynamoDB, polling, and the entire backend from the critical path. Latency becomes: 250ms post-detection + network transit ≈ **< 1 second**.

**Trade-offs:**
- Requires AWS IoT Core WebSocket auth (SigV4 or custom authorizer)
- Dual data paths (live view vs. persistent storage) add complexity
- If the browser isn't connected when the event happens, data could be missed (mitigated by background persistence)
- Bigger architectural change than the other options

### Option G: Reduce Post-Detection Delay

**What:** Reduce `POST_DETECTION_DELAY_MS` from 250ms to 100–150ms if the trailing edge data captured in the last 100–150ms isn't analytically valuable.

**Effort:** Trivial — one firmware constant.

**Impact:** Low. Saves 100–150ms. Minor but free.

**Trade-offs:**
- May cut off useful trailing-edge data for some transit profiles
- Worth testing empirically with a few captures at different values

### Option H: Time-Series Database Instead of DynamoDB

**What:** Replace DynamoDB with a purpose-built time-series store (Amazon Timestream, InfluxDB, or S3+Parquet) for sensor data storage.

**Effort:** High — new infrastructure, Lambda rewrites, frontend API changes.

**Impact:** Medium. Faster bulk writes and range queries, but the latency bottleneck isn't really DynamoDB write speed — it's the architectural pattern around it (concurrent Lambdas, settle delay, polling).

**Trade-offs:**
- Significant migration effort
- Timestream has its own pricing model and query patterns
- Doesn't address the core latency bottleneck unless combined with other options
- Better motivated by query/analysis needs than by latency alone

## Recommendation

*To be decided.* Three tiers emerge naturally from the analysis:

**Quick wins (Options A + B + C + G):** These are largely independent and complementary. Combined, they could reduce average latency from ~20s to ~5–8s with modest code changes across firmware, Lambda, and frontend. Option A (batch consolidation) is the highest-leverage single change because it eliminates the root cause of the settle delay.

**Medium-term (Option D or E):** Either WebSocket push or progressive rendering would shave off another few seconds and improve perceived responsiveness. These are worth pursuing if the quick wins aren't sufficient.

**Long-term (Option F):** Direct MQTT-to-browser is the "right" architecture for sub-second live debug feedback. Worth building toward but represents a bigger investment.

Option H (time-series DB) is not well-motivated by latency alone — worth revisiting if query patterns or data volume become pain points.

## Decision

**Status: Open**

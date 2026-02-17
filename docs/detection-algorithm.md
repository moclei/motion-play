# Detection Algorithm

Reference documentation for the direction detection algorithm: how it works, the physical scenarios it must handle, and architectural decisions.

For terminology (wave, detection, transit, etc.), see [PROJECT.md](../.context/PROJECT.md#terminology).

## Algorithm Overview (V3: Adaptive Threshold + Wave Envelope)

The algorithm determines which direction an object passed through the hoop by comparing the timing of proximity signal "waves" on the A-side (back-facing) and B-side (front-facing) sensors.

### Pipeline

1. **Aggregate by side** — All three modules' side-A readings are summed into one signal; same for side B. The algorithm operates on these two aggregated signals, not per-module.
2. **Smooth** — A moving average (default window: 3) reduces noise.
3. **Establish baseline** — The first N readings (default: 50) establish a noise floor. The max value observed during baseline becomes the reference.
4. **Calculate threshold** — `threshold = baseline_max + max(baseline_max × (multiplier - 1), minRise)`. This adapts to ambient conditions while enforcing a minimum absolute rise.
5. **Detect wave entry** — When the smoothed signal exceeds the threshold, a wave begins. Peak value, peak time, and a running center-of-mass (CoM) are tracked.
6. **Detect wave exit** — When the signal drops below the threshold (or a fraction of peak), the wave completes and CoM is finalized.
7. **Match waves** — When both sides have completed waves within `maxPeakGapMs` of each other, a detection is produced.
8. **Determine direction** — The side whose CoM came first is the entry side. CoM-A < CoM-B → A_TO_B, and vice versa.
9. **Calculate confidence** — Weighted combination of CoM gap magnitude (60%) and signal strength (40%).

### Key Parameters

| Parameter | Default | Role |
|-----------|---------|------|
| `baselineReadings` | 50 | Readings used to establish noise floor |
| `peakMultiplier` | 1.5 | Threshold scaling above baseline |
| `minRise` | 10 | Minimum absolute rise required (prevents false triggers in low-noise) |
| `smoothingWindow` | 3 | Moving average window |
| `maxWaveDurationMs` | 200 | Timeout: force-completes a wave if it doesn't exit naturally |
| `maxPeakGapMs` | 150 | Maximum time between side A and B waves to be considered the same event |
| `waveExitThreshold` | 0.5 | Exit wave when signal drops to this fraction of peak |

### Architectural Note: Aggregated Detection

The current algorithm aggregates all three modules into one signal per side. It does **not** run per-module detection. This means:

- It cannot determine *where* on the hoop the transit occurred.
- It relies on the temporal ordering being preserved in the aggregate (all A-side activity before all B-side activity, or vice versa).
- Module alignment variations can blur the aggregate timing.

This is a deliberate simplicity trade-off. The scenario catalog below helps evaluate whether this approach is sufficient or whether per-module detection is needed.

## Transit Scenario Catalog

Each scenario describes a physical transit type, the expected signal pattern, and which algorithm parameters are most stressed. This catalog should be used when evaluating algorithm changes — walk through each scenario and consider how a change would affect it.

### 1. Straight-through, close to one module

**Physical description:** Object passes perpendicular to the hoop plane, close to one module (e.g., M1).

**Expected signals:**
- M1-A: Strong, sharp wave
- M1-B: Strong, sharp wave, delayed by a few milliseconds
- M2, M3: Minimal or no response

**Aggregate behavior:** Clean wave on side A followed by clean wave on side B. High signal-to-noise. Clear CoM separation.

**Parameters stressed:** None particularly — this is the easy case.

**Expected outcome:** Correct detection with high confidence.

### 2. Straight-through, center of hoop

**Physical description:** Object passes through the geometric center, roughly equidistant from all three modules.

**Expected signals:**
- All modules: Weak, roughly equal waves on both sides
- Individual signals may be near or below threshold

**Aggregate behavior:** Aggregation helps — summing three weak signals produces a stronger combined signal. But timing blur is a risk if modules aren't perfectly aligned.

**Parameters stressed:**
- `peakMultiplier` / `minRise` — threshold must be low enough to catch weak aggregate signals
- Module alignment — misalignment means different modules' A-side waves arrive at slightly different times, broadening the aggregate wave and reducing CoM precision

**Expected outcome:** Detection likely if aggregate crosses threshold, but lower confidence due to smaller CoM gap and weaker signals.

### 3. Angled transit (cross-module)

**Physical description:** Object enters the hoop plane near one module's A-side but exits near a different module's B-side. For example, enters near M1-A, angles across, exits near M2-B.

**Expected signals:**
- M1-A: Strong wave
- M1-B: Weak or absent (object moved away)
- M2-A: Weak or absent
- M2-B: Strong wave
- M3: Minimal

**Aggregate behavior:** Aggregated side-A is dominated by M1-A; aggregated side-B is dominated by M2-B. Temporal ordering is preserved (A before B) because the object is still moving from back to front. CoM gap is actually *larger* than straight-through because the object traveled further between triggering A and B.

**Parameters stressed:**
- Threshold — needs to catch signals from single-module contributions in the aggregate (noise from non-active modules is also summed)

**Expected outcome:** Correct detection, potentially with higher confidence than straight-through due to larger CoM gap.

### 4. Grazing transit (very close to tube)

**Physical description:** Object passes through near the edge of the hoop, almost touching the tube near one module. Very high proximity values.

**Expected signals:**
- One module: Very strong, sharp waves on both A and B
- The A→B temporal gap is tiny because the object crosses the ~4° sensor offset almost instantly
- Other modules: Minimal

**Aggregate behavior:** Dominated by one module. Wave shapes are clean but the CoM gap between A and B may be extremely small (sub-millisecond).

**Parameters stressed:**
- CoM resolution — direction determination depends on distinguishing which CoM came first, but the gap may be near zero
- Timestamp precision — at 1ms resolution (1 kHz sampling), a sub-millisecond gap is a coin flip

**Expected outcome:** Detection occurs (strong signal), but direction confidence is low. May produce wrong direction if gap is within noise.

### 5. Slow transit

**Physical description:** Object moves slowly through the hoop (e.g., a hand reaching through casually). Wave duration is long.

**Expected signals:**
- One or more modules: Broad, sustained waves on both sides
- Wave duration may approach or exceed `maxWaveDurationMs`

**Aggregate behavior:** Long waves with clear A-before-B ordering if the object moves at consistent speed.

**Parameters stressed:**
- `maxWaveDurationMs` (200ms) — if the wave is still active at timeout, it is force-completed. CoM is calculated from a truncated wave, which may shift it
- `maxPeakGapMs` (150ms) — if the object is slow enough, side B's wave may start after side A's wave has already timed out and been force-completed

**Expected outcome:** May work if transit fits within timing windows. Slow enough transits will either produce inaccurate CoM (truncated wave) or fail to match waves (gap exceeds `maxPeakGapMs`).

### 6. Partial / aborted transit

**Physical description:** Object enters from one side but doesn't pass through — e.g., a hand reaches in and pulls back.

**Expected signals:**
- One or more modules' A-side: Wave observed
- B-side: No wave (object never reached the B plane)

**Aggregate behavior:** Side-A wave completes, side-B never triggers. The algorithm waits in DETECTING state.

**Parameters stressed:**
- Detection timeout (`maxWaveDurationMs + maxPeakGapMs`) — the algorithm must eventually reset to READY without producing a false detection

**Expected outcome:** No detection (correct). The timeout resets the detector. This is a true-negative case.

### 7. Near-parallel transit

**Physical description:** Object moves nearly parallel to the hoop plane, crossing through from one side of the ring to the other. Could pass one module's B sensor before another module's A sensor.

**Expected signals:**
- Unpredictable ordering: a B sensor on one module may fire before an A sensor on a different module
- The aggregated side signals may have overlapping or reversed timing

**Aggregate behavior:** The aggregate temporal ordering (all-A before all-B) may break. CoM comparison could give the wrong direction.

**Parameters stressed:**
- The fundamental assumption of the aggregated architecture: that A-side activity precedes B-side activity (or vice versa) across all modules simultaneously

**Expected outcome:** May produce wrong direction. However, this scenario is physically unlikely in most game contexts (objects typically pass *through* the hoop, not across it).

### 8. Quick succession (double-tap)

**Physical description:** Two transits in rapid succession — e.g., two objects, or the same object passing through and then back.

**Expected signals:**
- Two separate wave events on each side, close together in time

**Aggregate behavior:** If within the 500ms cooldown, the second event is missed entirely. If between cooldown and buffer overflow (500 samples), the second event may be detected normally.

**Parameters stressed:**
- Cooldown duration (500ms) — trade-off between preventing double-triggers on a single event and catching genuinely rapid successive events
- Buffer management — the 500-sample overflow prevention clears the buffer and resets the detector

**Expected outcome:** First event detected normally. Second event missed if within cooldown window.

### 9. Ambient interference / slow drift

**Physical description:** Gradual proximity change from a person walking past the hoop, or ambient light shift. No sharp wave.

**Expected signals:**
- Slow, broad change across multiple or all modules
- May cross threshold but lacks the sharp wave envelope of a real transit

**Aggregate behavior:** Gradual rise and fall. May enter wave state but the wave shape is broad and flat compared to a real transit.

**Parameters stressed:**
- `maxWaveDurationMs` — a slow drift that crosses threshold will eventually timeout, which is correct behavior
- Baseline — if the drift is persistent, future baseline calculations may be elevated

**Expected outcome:** Should not produce a detection in most cases. The wave timeout and the requirement for both sides to complete within `maxPeakGapMs` provide natural filtering. Worth verifying empirically.

### 10. Large object / multi-module simultaneous trigger

**Physical description:** A large object (or a fast object moving along the hoop plane) triggers multiple modules' A-sides at slightly different times, followed by B-sides at slightly different times.

**Expected signals:**
- Multiple modules: Waves on both sides, with slight timing offsets between modules
- Stronger aggregate signal than single-module cases

**Aggregate behavior:** Broader wave shape due to staggered module triggers. CoM is a weighted average across modules, which should still preserve A-before-B ordering.

**Parameters stressed:**
- Smoothing window — broader aggregate waves may benefit from wider smoothing
- CoM precision — staggered triggers widen the effective wave, potentially reducing the CoM gap between sides

**Expected outcome:** Detection likely. Direction accuracy depends on whether module staggering is symmetric (shouldn't bias one direction).

## Open Questions

- Is per-module detection needed, or is aggregation sufficient? Collecting labeled data for each scenario type would answer this empirically.
- Should `maxWaveDurationMs` and `maxPeakGapMs` be increased to handle slow transits (scenario 5), or are slow transits out of scope?
- How much does real-world module misalignment affect aggregate CoM precision (scenario 2)?
- Is the 500ms cooldown appropriate, or should it be configurable?

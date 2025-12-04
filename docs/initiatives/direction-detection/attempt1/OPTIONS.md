# Direction Detection - Attempt 1: Algorithm Options

This document outlines the algorithm approaches considered for detecting the direction of an object passing through the sensor hoop.

## Context

- **Hardware**: 3 PCBs, each with 2 proximity sensors (6 total sensors)
- **Sensor Orientation**: 
  - Side 1 sensors face "Side B" (far side)
  - Side 2 sensors face "Side A" (near side / developer side)
- **Sample Rate**: ~400-500Hz (~2-3ms between readings)
- **Event Duration**: ~100-200ms for a medium-speed pass
- **Goal**: Detect whether object passed A→B or B→A

## Approaches Considered

---

### Option 1: Threshold-Based First Trigger

**Description**: Set a static threshold. The first side to exceed the threshold determines entry direction.

**How it works**:
1. Define threshold (e.g., proximity > 20)
2. Monitor all sensors
3. When any sensor exceeds threshold, note which side (1 or 2)
4. That side is the "entry" side

**Pros**:
- Simple to implement
- Low computational cost
- Real-time capable

**Cons**:
- ❌ Different PCBs have vastly different sensitivity (PCB 3 reaches 268, others peak at ~40)
- ❌ Static threshold would need per-sensor calibration
- ❌ Random noise spikes could trigger false positives
- ❌ Edge passes may trigger both sides nearly simultaneously

**Verdict**: Not suitable due to sensor-to-sensor variation and calibration complexity.

---

### Option 2: Baseline + Relative Threshold

**Description**: Maintain a rolling baseline per sensor, trigger when reading exceeds N× baseline.

**How it works**:
1. Track rolling average of each sensor's "quiet" readings
2. Trigger when any sensor exceeds 3× its baseline
3. First side to trigger = entry direction

**Pros**:
- Adapts to sensor-to-sensor variation
- Self-calibrating over time

**Cons**:
- ❌ Baseline tracking has been problematic historically (per user feedback)
- ❌ Random unexplained peaks corrupt the baseline
- ❌ Still susceptible to noise triggering false positives
- ❌ Requires tuning the multiplier (3×, 5×, etc.)

**Verdict**: Not suitable due to baseline tracking difficulties and unexplained random peaks.

---

### Option 3: Signal Ratio Over Time

**Description**: Compare the ratio of Side A total vs Side B total over the event window.

**How it works**:
1. Sum all Side 1 sensors → `total_B`
2. Sum all Side 2 sensors → `total_A`
3. Track ratio `total_A / total_B` over time
4. If ratio starts high and decreases → A→B
5. If ratio starts low and increases → B→A

**Pros**:
- Relative comparison, no absolute thresholds
- Uses aggregate signal (more robust than single sensor)

**Cons**:
- ⚠️ Still needs to define "event start" somehow
- ⚠️ Ratio can be noisy if denominators are small
- ⚠️ Doesn't leverage the peak timing insight

**Verdict**: Partially suitable, but peak timing approach is more direct.

---

### Option 4: Derivative-Based Peak Detection (CHOSEN)

**Description**: Aggregate signals by side, detect peaks using derivative zero-crossings, compare peak timing.

**How it works**:
1. Aggregate: `side_A[t] = Σ sensor2 readings`, `side_B[t] = Σ sensor1 readings`
2. Compute derivatives: `d_A[t] = side_A[t] - side_A[t-1]`
3. Find peaks: where derivative crosses from positive to negative
4. Compare timing: which side peaked first?
5. Require paired peaks within ~50ms (filters noise)

**Pros**:
- ✅ No absolute thresholds required
- ✅ No baseline tracking required
- ✅ PCB-agnostic (aggregates by side, not by PCB)
- ✅ Naturally filters noise (requires paired peaks)
- ✅ Works for both edge and center passes
- ✅ Matches the visual pattern observed in data

**Cons**:
- ⚠️ Slightly more complex than threshold approaches
- ⚠️ Needs smoothing to handle derivative noise
- ⚠️ Batch processing required (not single-sample)

**Verdict**: ✅ SELECTED - Best balance of robustness and threshold-free operation.

---

### Option 5: Machine Learning Classifier

**Description**: Train a model on labeled session data to classify direction.

**How it works**:
1. Extract features from sensor windows (peaks, timing, ratios)
2. Train classifier (SVM, Random Forest, or small neural net)
3. Deploy trained model on device

**Pros**:
- Could capture complex patterns
- Potentially higher accuracy with enough data

**Cons**:
- ❌ Overkill for first attempt (try heuristics first)
- ❌ Requires more training data
- ❌ Model deployment complexity on embedded device
- ❌ Harder to debug/understand failures

**Verdict**: Reserved for future attempts if heuristic approach doesn't achieve target accuracy.

---

## Decision

**Selected Approach**: Option 4 - Derivative-Based Peak Detection

**Rationale**:
1. Directly matches the visual pattern observed in the sensor data
2. Avoids the threshold and baseline problems that have been historically difficult
3. Aggregating by side (not PCB) handles sensor sensitivity variation
4. Paired peak requirement provides natural noise filtering
5. Batch processing fits well with dual-core architecture (Core 0 samples, Core 1 analyzes)

See [IMPLEMENTATION.md](./IMPLEMENTATION.md) for detailed algorithm specification.


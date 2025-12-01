# Direction Detection Initiative

**Status**: Planning  
**Created**: November 27, 2024  
**Last Updated**: November 27, 2024

## Executive Summary

This initiative aims to develop a real-time detection system that can:
1. **Detect** when an object passes through the sensor plane
2. **Classify** the direction of travel (Side A → Side B, or Side B → Side A)
3. **Reject** false triggers (noise, fluctuations, ambient light changes)

The output will control an LED strip: green for one direction, blue for the other, no light for non-events.

## Current State

### What We Have
- **Hardware**: 6 VCNL4040 proximity sensors arranged radially on a 14" hoop
- **Sample Rate**: ~456 Hz (2.2ms per cycle) - sufficient for 72+ mph detection
- **Data Collection**: Working pipeline (firmware → MQTT → AWS → Web UI)
- **Session Data**: CSV export capability with labeled sessions

### What We Need
- A detection algorithm or model that runs efficiently on ESP32-S3
- Labeled training/validation data
- Integration with LED control

---

## Approach Options

We've identified three main approaches, each with different trade-offs:

### Option 1: Heuristic/Threshold-Based Algorithm

**How it works**: Traditional signal processing using rules and thresholds.

```
Example Algorithm:
1. Detect signal rise above threshold (object entering)
2. Track which sensor(s) trigger first
3. Track which sensor(s) trigger last  
4. Direction = first_trigger_side → last_trigger_side
5. Validate with timing/magnitude constraints
```

**Pros**:
- ✅ Simple to implement and debug
- ✅ No training data required
- ✅ Minimal memory footprint (~1KB)
- ✅ Deterministic behavior
- ✅ Fast inference (<100μs)
- ✅ Easy to tune on-device

**Cons**:
- ❌ May struggle with edge cases
- ❌ Requires manual parameter tuning
- ❌ Less adaptable to varying conditions
- ❌ May need per-device calibration

**Best for**: Well-defined, consistent scenarios with predictable signal patterns.

**Estimated effort**: 1-2 weeks

---

### Option 2: Classical Machine Learning (Random Forest, SVM, etc.)

**How it works**: Train a traditional ML model on extracted features from sensor data.

```
Pipeline:
1. Extract features from time windows (peaks, derivatives, timing)
2. Train classifier on labeled data (scikit-learn)
3. Export model as lookup tables or simple math
4. Run inference on ESP32
```

**Pros**:
- ✅ Better generalization than heuristics
- ✅ Can learn complex patterns
- ✅ Moderate memory footprint (~10-50KB)
- ✅ Fast inference (~1ms)
- ✅ Interpretable features

**Cons**:
- ❌ Requires labeled training data
- ❌ Feature engineering is manual
- ❌ May not handle novel scenarios well
- ❌ Custom inference code needed

**Best for**: Moderate complexity with good training data coverage.

**Estimated effort**: 2-3 weeks

---

### Option 3: TinyML / Neural Network

**How it works**: Train a small neural network, deploy with TensorFlow Lite Micro or Edge Impulse.

```
Pipeline:
1. Collect labeled session data
2. Upload to Edge Impulse (or train locally)
3. Design/train neural network
4. Quantize to int8
5. Export as C++ library
6. Integrate into firmware
```

**Pros**:
- ✅ Best generalization capability
- ✅ Automatic feature learning
- ✅ Handles noise/edge cases well
- ✅ End-to-end tooling (Edge Impulse)
- ✅ Can improve with more data

**Cons**:
- ❌ Requires substantial labeled data (100s of samples)
- ❌ Larger memory footprint (~50-200KB)
- ❌ Slower inference (~5-20ms)
- ❌ "Black box" - harder to debug
- ❌ Learning curve for tooling

**Best for**: Complex, variable scenarios where heuristics fail.

**Estimated effort**: 3-4 weeks

---

## Recommended Approach: Phased Implementation

Given our situation, I recommend a **phased approach**:

### Phase 1: Heuristic Baseline (1 week)
Build a simple threshold + timing algorithm to:
- Establish a working baseline
- Understand signal characteristics better
- Identify edge cases that fail
- Generate labeled data for later phases

### Phase 2: Evaluate and Decide (1 week)
- Test heuristic against diverse scenarios
- If accuracy >90%: Stop here, refine heuristics
- If accuracy <90%: Proceed to ML approach

### Phase 3: ML Enhancement (if needed) (2-3 weeks)
- Use Edge Impulse for rapid prototyping
- Train on labeled data from Phase 1 failures
- Deploy neural network alongside heuristic fallback

---

## Data Collection Plan

### Required Session Types

To train any model (or validate heuristics), we need labeled data:

| Category | Label | Description | Min Samples |
|----------|-------|-------------|-------------|
| **Direction A→B** | `direction_a_to_b` | Object passes front to back | 50 |
| **Direction B→A** | `direction_b_to_a` | Object passes back to front | 50 |
| **No Event** | `no_event` | Baseline, no object | 20 |
| **False Positive** | `false_positive` | Hand wave, shadow, etc. | 30 |

### Variation Dimensions

For robust detection, vary:
- **Speed**: Slow (5mph), Medium (15mph), Fast (30mph)
- **Trajectory**: Center, off-center, edge
- **Object size**: Small (3"), Medium (4"), Large (6")
- **Ambient light**: Indoor, outdoor, changing
- **Object color**: Light, dark (affects reflectivity)

### Session Labeling Workflow

1. Start session from web UI
2. Perform known action (e.g., "throw ball A→B at medium speed")
3. Stop session
4. Label session with metadata in web UI
5. Export for analysis

---

## Technical Specifications

### ESP32-S3 Resources (T-Display S3)

| Resource | Available | Notes |
|----------|-----------|-------|
| RAM | 512KB | For runtime data |
| PSRAM | 8MB | For model weights if needed |
| Flash | 16MB | For code + model storage |
| CPU | 240MHz dual-core | Plenty for inference |

### Inference Requirements

| Metric | Target | Notes |
|--------|--------|-------|
| Latency | <10ms | From detection to LED response |
| Memory | <200KB | Model + buffers |
| Accuracy | >95% | Correct classification rate |
| False Positive Rate | <1% | No spurious triggers |

---

## Edge Impulse Integration (Option 3 Details)

If we pursue TinyML, Edge Impulse provides the best workflow:

### Why Edge Impulse?
- Free tier supports our use case
- Direct ESP32 deployment
- Handles time-series data well
- Built-in signal processing blocks
- Automatic quantization

### Workflow
1. **Data Upload**: CSV → Edge Impulse Data Forwarder or direct upload
2. **Impulse Design**: Configure input window, processing, classifier
3. **Training**: Neural network or classical ML in cloud
4. **Testing**: Validate on held-out data
5. **Deployment**: Export as Arduino/PlatformIO library
6. **Integration**: Include library, call `run_classifier()`

### Data Format for Edge Impulse

Edge Impulse expects time-series data with:
- Consistent sample rate (we have 456 Hz)
- Channel labels (sensor_1_prox, sensor_2_prox, etc.)
- Labeled segments with start/end times

---

## Implementation Plan

### Phase 1: Heuristic Baseline

#### Week 1: Algorithm Development

**Day 1-2: Signal Analysis**
- [ ] Analyze existing session data
- [ ] Characterize typical A→B and B→A patterns
- [ ] Identify key discriminating features (timing, peaks, order)

**Day 3-4: Algorithm Implementation**
- [ ] Implement threshold detection
- [ ] Implement direction classification
- [ ] Add noise rejection logic
- [ ] Create `DirectionDetector` class in firmware

**Day 5: Integration**
- [ ] Integrate with sensor reading loop
- [ ] Connect to LED control
- [ ] Add real-time feedback (display, serial)

**Day 6-7: Testing**
- [ ] Collect labeled test sessions
- [ ] Measure accuracy
- [ ] Document failure modes

### Phase 2: Evaluation

- [ ] Review Phase 1 accuracy
- [ ] Decide: heuristic sufficient or ML needed?
- [ ] If ML needed, begin data collection sprint

### Phase 3: ML Enhancement (if needed)

- [ ] Set up Edge Impulse project
- [ ] Upload and label session data
- [ ] Design and train model
- [ ] Export and integrate
- [ ] Validate on device

---

## Success Metrics

| Metric | Phase 1 Target | Final Target |
|--------|----------------|--------------|
| Detection Rate | 80% | 98% |
| Direction Accuracy | 75% | 95% |
| False Positive Rate | 10% | 1% |
| Latency | 20ms | 10ms |

---

## Open Questions

1. **How many sensors are needed for direction?** 
   - All 6, or subset of 2-4?

2. **What signal window is optimal?**
   - 50ms? 100ms? Adaptive?

3. **Should we detect speed/velocity?**
   - Useful for UX feedback

4. **Multi-object scenarios?**
   - Handle two objects in quick succession?

---

## References

- [TensorFlow Lite for Microcontrollers](https://www.tensorflow.org/lite/microcontrollers)
- [Edge Impulse Documentation](https://docs.edgeimpulse.com/)
- [MCUNet: Tiny Deep Learning on IoT Devices](https://arxiv.org/abs/2007.10319)
- [TinyML Community Resources](https://www.tinyml.org/)
- [VCNL4040 Application Note](https://www.vishay.com/docs/84307/designingvcnl4040.pdf)

---

## Next Steps

1. **Review this plan** and decide on approach
2. **Begin Phase 1** heuristic implementation
3. **Collect labeled sessions** for validation
4. **Evaluate** and iterate

---

*Last Updated: November 27, 2024*


# Direction Detection - Attempt 1: Results

## Summary

**Best Accuracy Achieved: 75%** (9/12 samples)

This is below the 99% target but provides valuable insights for future iterations.

## Test Dataset

| File | Type | Expected |
|------|------|----------|
| a_to_b_medium_center_1-4 | Center passes A→B | a_to_b |
| a_to_b_medium_edge_1,5 | Edge passes A→B | a_to_b |
| b_to_a_medium_center_1-2 | Center passes B→A | b_to_a |
| b_to_a_medium_edge_1 | Edge passes B→A | b_to_a |
| baseline_1-3 | No object pass | unknown |

## Results by Approach

### Rise-Start Detection (Best Overall)
```
Config: smoothing=3, min_rise=10, max_gap=100ms
Accuracy: 75.0% (9/12)

By category:
  a_to_b: 4/6 (66.7%)
  b_to_a: 2/3 (66.7%)  
  unknown: 3/3 (100.0%) ✓ Perfect baseline detection
```

### Hybrid (Rise-Start + Center-of-Mass)
```
Config: smoothing=3, min_rise=10, max_gap=100ms
Accuracy: 75.0% (9/12)

By category:
  a_to_b: 5/6 (83.3%) ← Better at A→B
  b_to_a: 1/3 (33.3%) ← Worse at B→A
  unknown: 3/3 (100.0%) ✓ Perfect baseline detection
```

## Consistent Failures

These samples failed across ALL algorithm variations:

| Sample | Expected | Always Detected As | Notes |
|--------|----------|-------------------|-------|
| b_to_a_medium_edge_1 | B→A | A→B | High confidence (0.74-0.76) |

These samples failed with some configurations:

| Sample | Expected | Issue |
|--------|----------|-------|
| a_to_b_medium_center_1 | A→B | Fails with Hybrid (1ms gap - ambiguous) |
| a_to_b_medium_center_2 | A→B | Fails with Rise-Start (B rises 11ms before A) |
| a_to_b_medium_center_4 | A→B | Fails with Rise-Start (B rises 8ms before A) |
| b_to_a_medium_center_2 | B→A | Fails with Hybrid (A centroid 4ms before B) |

## Key Observations

### 1. Temporal Gaps Are Very Small
The time difference between Side A and Side B activity is typically **1-15ms**. This is at the edge of reliable detection given:
- Sample rate: ~2-3ms
- Ball transit time through hoop: ~100-200ms
- Sensors on both sides fire nearly simultaneously when ball is in the middle

### 2. Baseline Detection Works Well
Both approaches achieve **100% accuracy on baselines** by requiring:
- Significant rise on BOTH sides (min_rise threshold)
- Peaks occurring within a time window (max_peak_gap)

### 3. Edge Passes Are Challenging
The edge passes show more variability. The `b_to_a_medium_edge_1` sample is consistently misclassified, which could indicate:
- Mislabeled data
- Unusual ball trajectory
- Edge effects where the ball grazes one side differently

### 4. Algorithm Trade-offs
| Aspect | Rise-Start | Hybrid (with CoM) |
|--------|------------|-------------------|
| A→B accuracy | 66.7% | 83.3% |
| B→A accuracy | 66.7% | 33.3% |
| Baseline detection | 100% | 100% |
| Overall | 75% | 75% |

## Recommendations for Attempt 2

1. **More Training Data**: Current dataset (12 samples) is too small
   - Need 50+ samples per direction
   - Include different throw speeds and angles
   - Verify labels are correct

2. **Investigate Problematic Samples**
   - `b_to_a_medium_edge_1`: Visually inspect raw data
   - May need to re-record or confirm labeling

3. **Consider Alternative Approaches**
   - Per-PCB analysis (instead of aggregating all PCBs)
   - Machine learning with more features
   - Combine multiple heuristics with voting

4. **Hardware Considerations**
   - Are all PCBs mounted consistently?
   - Could sensor positioning affect edge pass detection?

## Code Artifacts

- Python prototype: `scripts/direction_detection/attempt1.py`
- Algorithm documentation: `docs/initiatives/direction-detection/attempt1/IMPLEMENTATION.md`

## Conclusion

The derivative-based approach successfully detects **whether** an event occurred (100% on baselines) but struggles to reliably determine **direction** (66-83% depending on configuration).

The fundamental challenge is that the temporal gap between sides is very small (1-15ms) relative to the sample rate (2-3ms), making direction detection inherently noisy.

**Next Steps**: 
- Collect more labeled data
- Verify existing labels are correct
- Try Attempt 2 with enhanced algorithms or ML approach


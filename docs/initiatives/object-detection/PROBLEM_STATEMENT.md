# Object Detection Initiative - Problem Statement

**Status**: Active  
**Created**: November 21, 2024  
**Last Updated**: November 21, 2024

## Executive Summary

Detect a spherical object (ball) passing through a circular detection plane (hula hoop) using VCNL4040 proximity sensors arranged radially around the perimeter. The system must reliably detect object passage, determine direction of travel, and handle a range of object sizes and velocities.

## Physical System Configuration

### Hardware Setup
- **Detection Plane**: Circular hoop (hula hoop)
- **Sensor PCBs**: 3 boards positioned at 120° intervals around the perimeter
- **Sensors per PCB**: 2 VCNL4040 sensors (facing inward toward center)
- **Total Sensors**: 6 sensors
- **Sensor Type**: VCNL4040 (IR proximity + ambient light)
- **Detection Method**: IR reflection from passing object

### Current Test Configuration
- **Hoop Diameter**: 14 inches (355.6 mm)
- **Hoop Radius**: 7 inches (177.8 mm)
- **Object Diameter**: 4 inches (101.6 mm) - standard ball
- **Object Type**: Spherical (ball)

### Sensor Placement
```
         [PCB1 - S1/S2]
              |
       120°   |   120°
    /         |         \
[PCB3]    Center    [PCB2]
  S1/S2      ●      S1/S2
    \        |        /
       120°  |  120°
             |
```

Each PCB has two sensors facing the centerpoint of the hoop.

## Problem Definition

### Core Requirements
1. **Detection**: Reliably detect when an object passes through the plane
2. **Direction**: Determine which direction the object traveled
3. **Timing**: Capture passage event with sufficient temporal resolution
4. **Robustness**: Handle varying object sizes, speeds, and trajectories

### Physical Constraints

#### Object Size Range
- **Minimum**: 3 inches (76.2 mm) diameter - small ball
- **Default**: 4 inches (101.6 mm) diameter - standard test ball
- **Maximum**: 6 inches (152.4 mm) diameter - large ball

#### Object Speed Range

**Slow (Gentle Toss)**
- Velocity: ~5 mph (2.2 m/s, 8 km/h)
- Transit time through 14" hoop: ~160 ms
- Use case: Training, gentle play

**Medium (Normal Throw)**
- Velocity: ~15 mph (6.7 m/s, 24 km/h)
- Transit time through 14" hoop: ~53 ms
- Use case: Casual gameplay

**Fast (Kick/Hard Throw)**
- Velocity: ~30 mph (13.4 m/s, 48 km/h)
- Transit time through 14" hoop: ~27 ms
- Use case: Sports performance, competitive play

**Default Test Speed**: 15 mph (medium) for consistent testing

#### Detection Distance
- **Sensor-to-Center Distance**: ~7 inches (177.8 mm)
- **Effective Detection Range**: Depends on sensor configuration
  - Current: ~2-4 inches based on session data analysis
  - Target: 6-8 inches for reliable center detection
- **Detection Threshold**: Proximity value > 10 (needs tuning)

## Current Performance Analysis

### Observed Sample Rate
**Problem**: Actual sample rate is ~24 Hz (41ms between samples)
- Target sample rate: 1000 Hz (1ms between samples)
- Achieved rate: ~24 Hz (41ms between samples)
- **Performance gap**: 42x slower than target

### Sample Rate Analysis

#### Current Bottleneck
Sequential I2C operations for 4 active sensors:
1. Select TCA9548A channel (I2C write)
2. Select PCA9546A channel (I2C write)
3. Read proximity from VCNL4040 (I2C read)
4. Read ambient light from VCNL4040 (I2C read)
5. Repeat for remaining 3 sensors

**Total cycle time**: ~41ms per complete sensor sweep

#### Impact on Direction Detection
At 24 Hz with medium speed (15 mph):
- Object transits hoop in ~53ms
- Only **1-2 samples** captured during transit
- Insufficient temporal resolution for accurate direction detection

## Required Sampling Rate Calculations

### Minimum Sampling Rate (Nyquist Criterion)

For reliable direction detection, we need to capture the **sequence** of sensor activations.

**Worst Case: Fast Object (30 mph)**
- Transit time: 27ms
- Require minimum 3 samples during transit (entry, middle, exit)
- Required sample rate: 3 samples / 27ms = **111 Hz minimum**

**Target Case: Medium Object (15 mph)**
- Transit time: 53ms
- Desire 5-10 samples during transit for good direction resolution
- Required sample rate: 10 samples / 53ms = **189 Hz target**

**Comfortable Case: Slow Object (5 mph)**
- Transit time: 160ms
- Abundant samples at any reasonable rate
- 50 Hz provides 8 samples (adequate)

### Recommended Sampling Rates

| Use Case | Minimum | Target | Comfortable |
|----------|---------|--------|-------------|
| Fast (30 mph) | 111 Hz | 200 Hz | 400 Hz |
| Medium (15 mph) | 95 Hz | 189 Hz | 400 Hz |
| Slow (5 mph) | 32 Hz | 63 Hz | 125 Hz |
| **System Target** | **125 Hz** | **200 Hz** | **400 Hz** |

**Conclusion**: System should target **200 Hz** (5ms between samples) for reliable direction detection across all expected velocities.

## Current Issues

### Issue 1: Inadequate Sample Rate
- **Status**: Critical
- **Current**: 24 Hz
- **Required**: 200 Hz minimum
- **Gap**: 8.3x too slow
- **Root Cause**: Sequential I2C reads with high overhead
- **See**: Session `device-001_43363110` - simultaneous triggers on all sensors

### Issue 2: Limited Detection Range
- **Status**: High Priority
- **Current**: ~2-4 inches effective range
- **Required**: 6-8 inches for center detection
- **Gap**: 2x insufficient range
- **Root Cause**: 
  - LED current already at maximum (200mA)
  - Integration time at minimum (1T) for speed
  - Possible sensor configuration suboptimal
- **Trade-off**: Range vs. sample rate (integration time)

### Issue 3: Baseline Noise (Partially Resolved)
- **Status**: Improved
- **Previous**: Proximity spikes to 10-15 at rest (IR crosstalk)
- **Current**: Proximity 0-2 baseline with occasional 3-5 spikes
- **Resolution**: Physical repositioning of sensor PCBs to avoid mutual interference
- **Remaining**: Some ambient light sensitivity

## Optimization Approaches

### Short-term (Immediate)
1. **Increase I2C Clock Speed**: 400kHz → 1MHz (2.5x faster)
2. **Skip Ambient Light Readings**: Save 1 I2C read per sensor (2x faster)
3. **Remove Unnecessary Delays**: Eliminate `delay()` calls in read loop
4. **Expected Result**: ~100 Hz sample rate

### Medium-term (Configuration)
1. **Test Integration Time Trade-offs**:
   - 1T (current): Fastest, noisiest, shortest range
   - 2T: 2x integration, better SNR, slightly longer range
   - 4T: 4x integration, good SNR, better range
   - 8T: 8x integration, best SNR, maximum range
2. **Multi-pulse Configuration**: If supported, increase pulses per reading
3. **Optimize Detection Algorithm**: Use derivative/pattern matching vs. absolute thresholds

### Long-term (Architecture)
1. **Parallel I2C**: Use separate I2C buses for sensor groups
2. **Interrupt-driven Reading**: Use VCNL4040 interrupt pins for event-driven sampling
3. **Hardware Redesign**: Consider dedicated sensor readout ICs
4. **ML/Pattern Recognition**: Train detection model on successful vs. failed captures

## Test Protocols

### Standard Test Cases

#### Test 1: Baseline Stability
- **Setup**: No object, sensors idle
- **Duration**: 10 seconds
- **Success Criteria**: 
  - Proximity ≤ 3 for 95% of samples
  - No sustained spikes > 5
  - Stable ambient light readings

#### Test 2: Direction Detection - Slow
- **Setup**: 4" ball, 5 mph throw
- **Repetitions**: 10 passes each direction
- **Success Criteria**: 
  - 100% detection of passage
  - 90% correct direction determination

#### Test 3: Direction Detection - Medium
- **Setup**: 4" ball, 15 mph throw
- **Repetitions**: 10 passes each direction
- **Success Criteria**: 
  - 100% detection of passage
  - 90% correct direction determination

#### Test 4: Direction Detection - Fast
- **Setup**: 4" ball, 30 mph throw/kick
- **Repetitions**: 10 passes each direction
- **Success Criteria**: 
  - 95% detection of passage
  - 80% correct direction determination

#### Test 5: Size Variation
- **Setup**: 3", 4", 6" balls at 15 mph
- **Repetitions**: 5 passes each size
- **Success Criteria**: 
  - Detection across all sizes
  - Consistent direction determination

### Measurement Methodology

#### Speed Verification
Use high-speed camera (120+ fps) to verify actual ball velocities during testing.

#### Distance Calibration
1. Position sensors at known distance from center
2. Move ball incrementally closer to center
3. Record proximity values at each distance
4. Build distance-to-proximity calibration curve

#### Direction Ground Truth
1. Mark clear entry/exit directions
2. Record video of each test
3. Compare sensor direction determination with video ground truth

## Success Metrics

### Phase 1: Foundation (Current)
- [ ] Achieve 200 Hz sample rate
- [ ] Baseline proximity noise < 5
- [ ] Detect 4" ball at 7" distance

### Phase 2: Basic Detection
- [ ] 95% detection rate at 15 mph
- [ ] 80% direction accuracy at 15 mph
- [ ] Test protocol documentation complete

### Phase 3: Performance
- [ ] 90% direction accuracy at 30 mph
- [ ] Detection across 3"-6" ball sizes
- [ ] Real-time processing < 10ms latency

### Phase 4: Production
- [ ] 95% direction accuracy all speeds
- [ ] Robust to varying ambient light
- [ ] False positive rate < 1%

## Open Questions

1. **What is the optimal sensor integration time for our use case?**
   - Trade-off between range, speed, and noise

2. **Should we use all 6 sensors or subset for critical path?**
   - Using 2-3 sensors might improve sample rate

3. **What detection algorithm provides best direction accuracy?**
   - Threshold crossing vs. derivative vs. pattern matching

4. **Can we achieve 400 Hz with current hardware?**
   - May require architectural changes

5. **What is the actual detection range at different LED currents?**
   - Need systematic distance calibration

6. **Should we use sensor interrupts vs. polling?**
   - Interrupt-driven might improve efficiency

## References

### Related Documents
- [Current Sensor Configuration](../../firmware/src/components/sensor/SensorManager.cpp)
- [Sensor Performance Analysis](../data-collection/PROJECT_STATUS.md)
- [Hardware Documentation](../../../hardware/)

### Test Data
- `session_data/device-001_18686413_baseline.csv` - Baseline with noise
- `session_data/device-001_19219727_waved_through_once.csv` - First detection test
- `session_data/device-001_19331032_waved_over_sensors.csv` - Close-range test
- `session_data/device-001_43363110.csv` - Improved baseline, direction test

### Datasheets
- VCNL4040 Proximity Sensor
- TCA9548A I2C Multiplexer
- PCA9546A I2C Multiplexer

---

**Next Steps**:
1. Implement I2C optimization (target 100-200 Hz)
2. Run calibrated distance tests
3. Develop direction detection algorithm
4. Execute standard test protocol
5. Iterate on configuration based on results


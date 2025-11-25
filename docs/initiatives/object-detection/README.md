# Object Detection Initiative

**Goal**: Reliably detect spherical objects passing through a circular detection plane with direction determination.

## Overview

This initiative focuses on optimizing the Motion Play system to detect balls passing through a hula hoop using VCNL4040 IR proximity sensors. The system must handle varying object sizes (3-6 inches), velocities (5-30+ mph), and determine passage direction for gameplay and performance tracking.

## Quick Links

- **[Problem Statement](./PROBLEM_STATEMENT.md)** - Complete problem definition, requirements, and success criteria
- **[Calculations](./CALCULATIONS.md)** - Mathematical analysis, formulas, and performance modeling
- **[Phase 1 Implementation Plan](./PHASE1_IMPLEMENTATION_PLAN.md)** - Detailed implementation guide for sample rate optimization
- **[Implementation Summary](./IMPLEMENTATION_SUMMARY.md)** - What was implemented and testing protocol
- **[Deployment & Testing Guide](./DEPLOYMENT_TESTING_GUIDE.md)** - Step-by-step testing instructions ⭐ START HERE
- **[Test Data](../../../session_data/)** - Collected sensor data from experiments

## Current Status

**Sample Rate**: 24 Hz → Target 150-200 Hz (Phase 1 implementation complete ✅, testing pending)  
**Detection Range**: 2-4 inches (needs 5-7 inches) ⚠️  
**Direction Accuracy**: Unable to determine (simultaneous triggers) ❌  
**Baseline Noise**: 0-3 proximity units ✓

## Key Parameters

### Default Test Configuration
- **Hoop Diameter**: 14 inches (355.6 mm)
- **Ball Diameter**: 4 inches (101.6 mm)
- **Test Speed**: 15 mph (6.7 m/s) - medium throw
- **Transit Time**: 53 ms at test speed
- **Sensor Count**: 4 active (2 PCBs × 2 sensors)

### Target Performance
- **Sample Rate**: 200 Hz (5ms intervals)
- **Detection Range**: 7 inches (sensor-to-center)
- **Direction Accuracy**: >90% at 15 mph
- **Latency**: <10ms from detection to classification

## The Challenge

### Transit Time vs. Sample Rate

| Ball Speed | Transit Time | Current Samples | Required Samples | Status |
|------------|--------------|-----------------|------------------|--------|
| 5 mph (slow) | 159 ms | 4 samples | 10 samples | ⚠️ Marginal |
| 15 mph (medium) | 53 ms | 1-2 samples | 10 samples | ❌ Insufficient |
| 30 mph (fast) | 27 ms | 0-1 samples | 5 samples | ❌ Insufficient |

**Problem**: At 24 Hz, the system captures only 1-2 samples as a ball passes through at normal speed, making direction determination impossible.

## Immediate Action Items

### Phase 1: Optimize Sample Rate ✅ IMPLEMENTED
- [x] Add configurable `read_ambient` flag (can disable for 2x speedup)
- [x] Implement configuration parser functions for all sensor settings
- [x] Create Settings UI for configuration changes
- [x] Apply configuration without device restart
- [ ] Deploy and test actual sample rate improvements
- [ ] Increase I2C clock speed from 400kHz to 1MHz (future enhancement)
- **Status**: Implementation complete, device testing pending
- **Expected**: 50-100 Hz with ambient disabled, 150-200 Hz with I2C optimization

### Phase 2: Algorithm Development (Week 2)
- [ ] Implement peak detection algorithm
- [ ] Add derivative-based direction detection
- [ ] Create confidence scoring system
- [ ] Test with recorded session data

### Phase 3: Calibration & Testing (Week 3)
- [ ] Distance calibration (proximity vs. distance curve)
- [ ] Speed verification with high-speed camera
- [ ] Execute standard test protocol (10 passes each direction)
- [ ] Document detection accuracy per speed/size combination

### Phase 4: Configuration Optimization (Week 4)
- [ ] Test integration time trade-offs (1T, 2T, 4T, 8T)
- [ ] Evaluate sensor subset configurations
- [ ] Optimize detection thresholds
- [ ] Implement adaptive algorithms

## Technical Bottleneck Analysis

### Why Only 24 Hz?

**Expected**: 4 sensors × 120μs = 480μs → 2,000 Hz possible  
**Observed**: 41ms per cycle → 24 Hz achieved  
**Gap**: **85x slower** than theoretical

**Hypothesis**:
1. Hidden delays in Adafruit library
2. VCNL4040 measurement completion time
3. PCA9546A channel switching overhead
4. Software delays not yet identified

**Investigation Required**: 
- Profile exact timing of each I2C operation
- Check for blocking delays in VCNL4040 measurement
- Review multiplexer datasheet for switching time requirements

## Key Insights from Test Data

### Session: device-001_43363110 (Latest)

**Positive Findings**:
- ✅ Baseline noise improved (0-3 vs. previous 10-15)
- ✅ Clear detection events visible in proximity data
- ✅ Sensors respond to close-range objects

**Issues Identified**:
- ❌ Sample rate too low for direction (41ms spacing)
- ❌ All sensors trigger simultaneously (no temporal separation)
- ❌ Detection limited to very close range

**Example Detection Event** (4083-4206ms):
```
Time    P1-S1  P1-S2  P2-S1  P2-S2
4083ms    9     12     7      7     ← Initial trigger
4124ms   18     16    19     18     ← Peak
4165ms   16     13    25     23     ← Peak continued
4206ms   14      9    22     22     ← Decay
```

Both PCBs show similar timing → **Cannot determine direction**

## Design Trade-offs

### Range vs. Speed

| Integration Time | Range | Max Sample Rate | SNR |
|-----------------|-------|-----------------|-----|
| 1T (current) | Short | ~2000 Hz | Low |
| 2T | Medium | ~1000 Hz | Medium |
| 4T | Good | ~500 Hz | Good |
| 8T | Best | ~250 Hz | Best |

**Recommendation**: Start with 1T, optimize code first. If 400+ Hz achieved with 1T, test 2T for range improvement.

### Sensor Count vs. Speed

| Active Sensors | Cycle Time | Max Rate | Coverage |
|----------------|------------|----------|----------|
| 2 sensors | 240 μs | 4,000 Hz | Minimal |
| 4 sensors (current) | 480 μs | 2,000 Hz | Good |
| 6 sensors | 720 μs | 1,400 Hz | Complete |

**Recommendation**: Use 4 sensors (2 PCBs) for direction detection, validate before adding more.

### Accuracy vs. Latency

| Method | Latency | Accuracy | Complexity |
|--------|---------|----------|------------|
| First Trigger | 5-10ms | Medium | Low |
| Peak Detection | 20-50ms | High | Medium |
| ML Pattern | 10-30ms | Very High | High |

**Recommendation**: Start with peak detection (good balance), consider ML later.

## Success Criteria

### Milestone 1: Functional Detection (2 weeks)
- ✓ 200 Hz sample rate achieved
- ✓ Detect 4" ball at 15 mph with 95% reliability
- ✓ Determine direction with >80% accuracy

### Milestone 2: Robust Detection (1 month)
- ✓ Detect across 3-6" ball sizes
- ✓ Handle 5-30 mph velocity range
- ✓ Direction accuracy >90% at all speeds
- ✓ False positive rate <5%

### Milestone 3: Production Ready (2 months)
- ✓ Real-time processing <10ms latency
- ✓ Robust to varying ambient light
- ✓ Confidence scoring implemented
- ✓ Documented test protocol and results

## Related Documentation

### Hardware
- [Sensor Manager Implementation](../../../firmware/src/components/sensor/SensorManager.cpp)
- [Pin Configuration](../../../firmware/include/pin_config.h)
- [VCNL4040 Datasheet](../../../docs/context_files/vcnl4040_datasheet_text.txt)

### Testing
- [Session Data Directory](../../../session_data/)
- [Data Collection Status](../../data%20collection/PROJECT_STATUS.md)

### Background
- [Project README](../../../README.md)
- [Quick Start Guide](../../../QUICK_START_GUIDE.md)

## Questions & Answers

### Why not just increase LED current?
Already at maximum (200mA). Next step is integration time or multi-pulse.

### Why not sample even faster than 400 Hz?
Diminishing returns beyond 400 Hz for our speed range. Better to optimize other aspects.

### Can we use all 6 sensors?
Yes, but start with 4 to validate approach first. Adding more sensors reduces max sample rate proportionally.

### What about using interrupts?
Promising long-term approach. Requires additional wiring and firmware changes. Consider after achieving 200+ Hz with current architecture.

### Should we do ML now?
No. Get basic direction detection working first with simple algorithms. ML is valuable for edge cases and optimization later.

## Contact & Updates

**Initiative Lead**: [Your Name]  
**Created**: November 21, 2024  
**Last Updated**: November 21, 2024  
**Status**: Active - Phase 1 (Optimization)

---

## Quick Start Testing

To reproduce current results:

```bash
# 1. Flash firmware to device
cd firmware
pio run -t upload

# 2. Start data collection session via web interface
# Label: "direction_test_15mph"

# 3. Pass 4" ball through hoop at ~15 mph
# - 5 passes left-to-right
# - 5 passes right-to-left

# 4. Download session CSV
# Save to: session_data/

# 5. Analyze with Python/Excel
# - Plot proximity vs. time for all sensors
# - Identify peak times for each PCB
# - Calculate time difference between peaks
```

## Version History

- **v1.0** (2024-11-21): Initial problem statement and calculations
- Focus on sample rate optimization and basic direction detection

---

**Next Update**: After Phase 1 completion (target: 1 week)


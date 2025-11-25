# Object Detection - Mathematical Calculations

**Purpose**: Detailed calculations for sampling requirements, detection ranges, and performance metrics.

## Transit Time Calculations

### Basic Formula

For an object traveling through a circular hoop:

```
Transit Time (t) = Diameter / Velocity
t = d / v
```

### Reference Values

**Hoop Diameter**: 14 inches = 0.3556 meters = 355.6 mm

| Velocity | mph | m/s | km/h | Transit Time (ms) |
|----------|-----|-----|------|-------------------|
| Slow | 5 | 2.24 | 8.05 | 159 |
| Medium | 15 | 6.71 | 24.14 | 53 |
| Fast | 30 | 13.41 | 48.28 | 27 |
| Very Fast | 50 | 22.35 | 80.47 | 16 |

### Calculation Examples

**Example 1: Medium Speed Ball**
```
Velocity: 15 mph = 6.71 m/s
Hoop diameter: 0.3556 m
Transit time = 0.3556 / 6.71 = 0.053 seconds = 53 ms
```

**Example 2: Fast Kicked Ball**
```
Velocity: 30 mph = 13.41 m/s
Transit time = 0.3556 / 13.41 = 0.0265 seconds = 26.5 ms
```

## Sampling Rate Requirements

### Nyquist-Based Minimum

To capture a discrete event, we need minimum 2 samples per event duration. For direction detection, we need to capture the **sequence** of sensor activations.

**Minimum Samples for Direction Detection**: 3
- Sample 1: First sensor triggers (entry side)
- Sample 2: Object at center
- Sample 3: Second sensor triggers (exit side)

```
Minimum Sample Rate = 3 samples / Transit Time
```

**Calculations**:

| Speed | Transit Time | Min Sample Rate | Recommended (5x) | Comfortable (10x) |
|-------|--------------|-----------------|------------------|-------------------|
| Slow (5 mph) | 159 ms | 19 Hz | 95 Hz | 189 Hz |
| Medium (15 mph) | 53 ms | 57 Hz | 283 Hz | 566 Hz |
| Fast (30 mph) | 27 ms | 111 Hz | 556 Hz | 1111 Hz |

### Practical Sample Rate Targets

Considering real-world factors:
- I2C communication overhead
- Multiple sensor reads per cycle
- Processing time
- Signal-to-noise requirements

**Recommended Targets**:
- **Minimum viable**: 100 Hz (10ms per cycle)
- **Good performance**: 200 Hz (5ms per cycle)
- **Excellent performance**: 400 Hz (2.5ms per cycle)
- **Theoretical maximum**: 1000 Hz (1ms per cycle)

At **200 Hz** (5ms per sample):
- Slow (159ms transit): 32 samples ✓ Excellent
- Medium (53ms transit): 11 samples ✓ Good
- Fast (27ms transit): 5 samples ✓ Minimal but workable

## Detection Range Calculations

### VCNL4040 Sensor Characteristics

**Key Parameters**:
- IR LED Wavelength: 940nm
- LED Current: Configurable (50mA to 200mA)
- Integration Time: Configurable (1T to 8T)
- Detection Method: IR reflection

### Inverse Square Law

IR intensity follows inverse square law:

```
Intensity ∝ 1 / distance²
```

If sensor detects at distance `d₁` with signal `S₁`, then at distance `d₂`:

```
S₂ = S₁ × (d₁ / d₂)²
```

### Empirical Observations from Test Data

**Session: device-001_19331032** (close-range test)
- At ~1-2 inches: Proximity = 200-350 (strong detection)
- At ~4-6 inches: Proximity = 20-30 (weak detection)
- At ~7+ inches: Proximity = 1-5 (baseline/no detection)

### Signal-to-Noise Ratio

**Current Baseline Noise**: 0-3 proximity units
**Detection Threshold**: Should be > 10 for reliability (3σ above noise)

**Effective Ranges**:
- **Strong Detection** (Proximity > 100): < 2 inches
- **Good Detection** (Proximity > 50): 2-4 inches
- **Marginal Detection** (Proximity > 10): 4-6 inches
- **Unreliable** (Proximity < 10): > 6 inches

### Required Range

For a 14" diameter hoop with sensors at perimeter:
- **Sensor-to-Center Distance**: 7 inches (177.8mm)
- **Ball radius**: 2 inches (50.8mm)
- **Minimum Detection Distance**: 7 - 2 = **5 inches** (127mm)

**Current Gap**: We need reliable detection at 5-7 inches, but currently only achieve 2-4 inches.

### Range Improvement Factors

**Integration Time Multiplier**:
- 1T (current): 1.0x signal
- 2T: ~1.4x signal (√2)
- 4T: ~2.0x signal
- 8T: ~2.8x signal

**LED Current**:
- Currently at maximum (200mA)
- No room for improvement here

**Multi-pulse**:
- If configurable, could average multiple pulses
- Improves SNR by √N for N pulses

## I2C Timing Analysis

### Current I2C Configuration

**Clock Speed**: 400 kHz (Fast Mode)
**Bus Configuration**: Shared I2C bus with multiplexers

### I2C Transaction Times

**Single I2C Write** (e.g., select channel):
```
Time = (Setup + Address + Data + ACK) / Clock Speed
≈ 20-30 microseconds at 400 kHz
```

**Single I2C Read** (e.g., read proximity):
```
Time = (Setup + Address + Read + Data + ACK) / Clock Speed
≈ 30-40 microseconds at 400 kHz
```

### Current Read Cycle Breakdown

For **4 active sensors** (2 PCBs × 2 sensors/PCB):

**Per Sensor** (worst case):
1. Select TCA9548A channel: ~25 μs
2. Select PCA9546A channel: ~25 μs
3. Read proximity value: ~35 μs
4. Read ambient light: ~35 μs
**Subtotal per sensor**: ~120 μs

**Total for 4 sensors**: 4 × 120 μs = **480 μs = 0.48 ms**

**Observed time**: **41 ms** per cycle

**Discrepancy**: 41ms / 0.48ms = **85x slower than expected!**

### Where Is the Time Going?

1. **Software delays**: `delay(50)` calls in initialization may still exist in read path
2. **Library overhead**: Adafruit library may have internal delays
3. **Multiplexer switching time**: PCA9546A may need settling time
4. **VCNL4040 measurement time**: Sensor may take time to complete reading

### Optimization Potential

**Remove ambient light reads**: 2x faster
- From: 480 μs → 240 μs

**Increase I2C speed to 1 MHz**: 2.5x faster
- From: 240 μs → 96 μs

**Optimize library/remove delays**: 2-10x faster
- From: 96 μs → 10-50 μs

**Theoretical best case**: 10 μs × 4 sensors = **40 μs per cycle**
- Maximum sample rate: **25,000 Hz** (limited by other factors)

**Practical target**: 200 μs per cycle = **5,000 Hz**
- More than sufficient for our needs

## Direction Detection Algorithms

### Method 1: First Trigger

Detect which sensor/PCB shows first significant increase:

```
if PCB1_proximity > threshold before PCB2_proximity:
    direction = "PCB1 → PCB2"
else:
    direction = "PCB2 → PCB1"
```

**Requires**: Sufficient temporal resolution (>200 Hz)

### Method 2: Peak Detection

Track which sensor reaches maximum value first:

```
t_peak_PCB1 = timestamp when PCB1_proximity is maximum
t_peak_PCB2 = timestamp when PCB2_proximity is maximum

if t_peak_PCB1 < t_peak_PCB2:
    direction = "PCB1 → PCB2"
```

**More robust** to noise, requires fewer samples.

### Method 3: Derivative (Rate of Change)

Track which sensor shows steeper rise:

```
dP1/dt = rate of change of PCB1 proximity
dP2/dt = rate of change of PCB2 proximity

if dP1/dt peaks before dP2/dt:
    direction = "PCB1 → PCB2"
```

**Most sophisticated**, best for noisy data.

### Method 4: Pattern Matching

Train ML model on labeled data:
- Input: Time series of all sensor readings
- Output: Direction classification

**Advantages**: Handles complex scenarios, learns optimal features
**Disadvantages**: Requires training data, more computational overhead

## Confidence Metrics

### Signal Strength

```
Confidence = (Peak_Signal - Baseline) / Baseline_Noise
```

Strong detection: Confidence > 10
Weak detection: Confidence < 5

### Temporal Consistency

```
Expected_Transit_Time = Hoop_Diameter / Estimated_Velocity
Observed_Transit_Time = Last_Trigger - First_Trigger

Consistency_Score = 1 - |Expected - Observed| / Expected
```

High confidence: Score > 0.8
Low confidence: Score < 0.5

### Multi-Sensor Agreement

With 6 sensors, check how many sensors triggered:

```
Trigger_Count = number of sensors with proximity > threshold
Confidence = Trigger_Count / Total_Sensors
```

Strong event: > 4 sensors triggered
Weak event: < 3 sensors triggered

## Performance Envelope

### Current System (24 Hz)
✓ Detects: Slow objects (5 mph)
✗ Direction: Unreliable for medium/fast
✗ Latency: 40ms minimum

### Target System (200 Hz)
✓ Detects: All speeds (5-30 mph)
✓ Direction: Reliable for medium (15 mph)
⚠ Direction: Marginal for fast (30 mph)
✓ Latency: 5ms

### Aspirational System (400+ Hz)
✓ Detects: All speeds including very fast (50+ mph)
✓ Direction: Reliable for all speeds
✓ Latency: <3ms
✓ Multiple objects: Could track multiple simultaneous objects

## Scalability Considerations

### Increasing Sensor Count

Current: 6 sensors (3 PCBs × 2 sensors)
If increased to 6 PCBs (12 sensors):

**Sample time**: 12 sensors × 120 μs = 1.44 ms (optimized)
**Max sample rate**: ~700 Hz (still excellent)

### Alternative Configurations

**Option A: Critical Path Only**
- Use 2 sensors (one per PCB) for direction
- Use remaining 4 for supplementary data
- Sample time: 240 μs → 4,000 Hz possible

**Option B: Parallel I2C**
- Use 2 separate I2C buses
- Read sensor groups in parallel
- Sample time: 240 μs (2 sensors per bus) → 4,000 Hz

**Option C: Interrupt-Driven**
- Configure VCNL4040 to trigger interrupt on threshold
- Only read when object present
- Reduces idle polling, improves latency

## Summary Table

| Parameter | Current | Target | Stretch Goal |
|-----------|---------|--------|--------------|
| Sample Rate | 24 Hz | 200 Hz | 400 Hz |
| Detection Range | 2-4 in | 5-7 in | 8+ in |
| Speed Support | < 10 mph | < 30 mph | < 50 mph |
| Direction Accuracy | < 50% | > 90% | > 95% |
| Latency | 41 ms | 5 ms | 2.5 ms |

---

**Formulas for Quick Reference**:

```python
# Transit time
transit_time_ms = (hoop_diameter_m / velocity_m_s) * 1000

# Minimum sample rate (3 samples minimum)
min_sample_rate_hz = 3000 / transit_time_ms

# Recommended sample rate (10 samples)
recommended_sample_rate_hz = 10000 / transit_time_ms

# Maximum sample rate from I2C timing
max_sample_rate_hz = 1_000_000 / (num_sensors * us_per_sensor)

# Detection confidence
confidence = (peak_signal - baseline_mean) / baseline_std_dev

# Direction from peak timing
direction = "A→B" if t_peak_A < t_peak_B else "B→A"
```


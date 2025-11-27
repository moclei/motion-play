# VCNL4040 Configuration Guide
## Understanding the Settings for Optimal Performance

Based on analysis of the Vishay VCNL4040 design guide and testing with Motion Play hardware.

---

## TL;DR - Quick Reference

**For your goals (fast sample rate + good detection):**
```cpp
Integration Time: 2T or 4T    // Better range/SNR than 1T, still fast
Duty Cycle: 1/40              // Maximum sample rate (~200 Hz)
LED Current: 200mA            // Maximum detection range
High Resolution: true         // 16-bit for better precision
```

---

## The Key Insight: Two Independent Controls

### 1. **Duty Cycle (PS_Duty)** - Controls SAMPLE RATE
- **1/40** → ~5ms between measurements → **~200 Hz** (FASTEST)
- **1/80** → ~10ms between measurements → **~100 Hz**
- **1/160** → ~20ms between measurements → **~50 Hz**
- **1/320** → ~40ms between measurements → **~25 Hz** (SLOWEST)

This is the PRIMARY control for how often measurements happen.

### 2. **Integration Time (PS_IT)** - Controls PULSE LENGTH & SENSITIVITY
- **1T** → 125 μs pulse → Lower signal, shorter range
- **2T** → 250 μs pulse → Better signal
- **4T** → 500 μs pulse → Even better signal
- **8T** → 1000 μs pulse → Best signal, longest range

This controls how STRONG each measurement is, NOT how often they happen.

---

## Common Misconception (From Your Frontend)

❌ **WRONG**: "Longer integration time = slower sample rate"
✅ **RIGHT**: "Longer integration time = stronger signal per measurement"

The duty cycle setting determines sample rate. Integration time only affects it indirectly through the relationship:

```
Measurement Period = Pulse Length × Duty Cycle Denominator

Example 1: 1T with 1/40 duty
  Period = 125μs × 40 = 5ms → 200 Hz

Example 2: 8T with 1/40 duty  
  Period = 1000μs × 40 = 40ms → 25 Hz

Example 3: 1T with 1/320 duty
  Period = 125μs × 320 = 40ms → 25 Hz
```

---

## From the Vishay Design Guide

### Integration Time (Lines 537-543)
> "If higher detection distances and / or objects with very low reflectivity should be detected, there is the option to extend these proximity pulses up to about 1000 μs for 8T. This results in higher counts"

**Key Points:**
- 8T can achieve 10,000+ counts vs 1,000 counts with 1T (see Fig 14 vs Fig 15)
- Better SNR because more photons are collected
- Reduces saturation risk at very close range (higher counts before hitting max)

### Duty Cycle (Lines 515-520, 564-569)
> "With defining the duty time (PS_Duty), the repetition rate = the number of proximity measurements per second (speed of proximity measurements) is defined. This is possible between 5 ms (about 200 measurements/s) by programming PS_Duty with 1/40 and 40 ms (about 25 measurements/s) with programming PS_Duty with 1/320."

**Key Points:**
- This is the PRIMARY control for measurement frequency
- 1/40 = fastest response time
- 1/320 = longest battery life

---

## Configuration Strategy for Motion Play

### Your Goals
1. **Fast sample rate** - Need to catch fast-moving objects
2. **Good detection** - Strong signal when something passes through
3. **Less concerned about** - Exact distance measurement accuracy

### Recommended Configuration

```cpp
// BEST for Motion Play
Duty Cycle: 1/40           // ~200 Hz maximum - catch fast objects
Integration Time: 2T or 4T  // 2-4× stronger signal than 1T
LED Current: 200mA         // Maximum range
High Resolution: true      // 16-bit for better differentiation

// Result: ~200 Hz actual sample rate with strong detection
```

### Why Not 8T Integration Time?
- 8T with 1/40 duty → ~25 Hz effective rate (too slow for fast objects)
- 2T or 4T gives good signal strength while maintaining high sample rate

### Alternative: If Objects Are Very Fast
```cpp
Duty Cycle: 1/40           // Still fastest
Integration Time: 1T       // Shortest pulse for maximum speed
LED Current: 200mA         // Compensate with high power
```

---

## Power Consumption Considerations

### Integration Time Impact
- **Minimal** - pulse is longer but still very short (125μs to 1000μs)
- At 1/40 duty, LED is only ON 2.5% of the time anyway

### Duty Cycle Impact (Critical for Battery Life)
- **1/40**: Avg current = 200mA / 40 = **5.0 mA**
- **1/80**: Avg current = 200mA / 80 = **2.5 mA**
- **1/160**: Avg current = 200mA / 160 = **1.25 mA**
- **1/320**: Avg current = 200mA / 320 = **0.625 mA**

For Motion Play (powered by USB), this isn't a concern. Use 1/40.

---

## I2C Timing Impact

From your modified Adafruit library:
```cpp
delayMicroseconds(500); // Your optimization: 0.5ms vs 10ms delay
```

**I2C Read Time** (at 400 kHz):
- Reading proximity value: ~500 μs
- This is SMALL compared to duty cycle periods (5ms+)
- Your optimization is good!

**Bottleneck Analysis:**
```
Duty Cycle 1/40 → 5ms period
├─ IR Pulse: 125μs (1T) to 1000μs (8T)
├─ I2C Read: ~500μs
└─ Remaining time: ~3.5ms (plenty of buffer)

Even with 6 sensors sequentially:
6 × 500μs = 3ms < 5ms period
```

You can read all 6 sensors within one duty cycle period!

---

## Implementation Notes

### Current Status
- ✅ Integration Time: Exposed in config
- ✅ LED Current: Exposed in config
- ✅ High Resolution: Exposed in config
- ❌ **Duty Cycle: NOT exposed** (likely defaulting to 1/160)

### What's Happening Now
The Adafruit library initializes sensors but doesn't set duty cycle explicitly, so it uses the chip default (1/160 based on datasheet).

Your "sample_rate_hz" config is probably controlling your reading loop in firmware, but the SENSOR is only taking measurements at 1/160 duty rate (~50 Hz), so reading faster doesn't help!

---

## Recommended Next Steps

1. **Add duty cycle to SensorConfiguration.h**
2. **Expose duty cycle in frontend configuration**
3. **Set to 1/40 for maximum speed**
4. **Test with 2T or 4T integration time**
5. **Measure actual detection performance**

This will give you:
- Real ~200 Hz sensor measurements (not just reads)
- Strong detection signal
- Fast response to objects passing through

---

## Testing Strategy

### Baseline Test (Current Config)
```
Integration: 1T
Duty: 1/160 (default)
LED: 200mA
Expected: ~50 Hz effective, moderate signal
```

### Speed Optimized Test
```
Integration: 1T
Duty: 1/40
LED: 200mA
Expected: ~200 Hz, moderate signal
```

### Balanced Test (RECOMMENDED)
```
Integration: 2T
Duty: 1/40
LED: 200mA
Expected: ~200 Hz, strong signal
```

### Range Optimized Test
```
Integration: 4T
Duty: 1/40
LED: 200mA
Expected: ~200 Hz, very strong signal
```

---

## References

- Vishay VCNL4040 Design Guide (designingvcnl4040.txt)
- Adafruit VCNL4040 Library
- Motion Play PROJECT.md

---

*Last Updated: November 26, 2025*


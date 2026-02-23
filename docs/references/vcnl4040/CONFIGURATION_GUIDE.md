# VCNL4040 Configuration Guide
## Understanding the Settings for Optimal Performance

Based on analysis of the Vishay VCNL4040 design guide, datasheet, and testing with Motion Play hardware.

---

## TL;DR - Quick Reference

**For Motion Play (fast sample rate + good detection):**
```cpp
Integration Time: 2T           // Good signal, 100 Hz at 1/40 duty
Duty Cycle: 1/40               // Maximum measurement rate
Multi-Pulse: x4                // 4× signal boost, no rate penalty
LED Current: 200mA             // Maximum detection range
High Resolution: true          // 16-bit for better precision
```

---

## The Three Controls That Matter

### 1. Integration Time (PS_IT) — Controls PULSE LENGTH, SENSITIVITY, AND RATE

Each measurement fires an IR pulse of this duration. Longer pulses collect more photons (stronger signal) but take longer, directly reducing the measurement rate.

| Setting | Pulse Width | Rate @ 1/40 duty | Signal Strength |
|---------|------------|-------------------|-----------------|
| 1T | 125 μs | **200 Hz** | Baseline |
| 1.5T | 187.5 μs | **133 Hz** | 1.5× |
| 2T | 250 μs | **100 Hz** | 2× |
| 2.5T | 312.5 μs | **80 Hz** | 2.5× |
| 3T | 375 μs | **67 Hz** | 3× |
| 3.5T | 437.5 μs | **57 Hz** | 3.5× |
| 4T | 500 μs | **50 Hz** | 4× |
| 8T | 1000 μs | **25 Hz** | 8× |

> **Note on pulse width:** Some Vishay documentation says "about 100 μs" for 1T. The actual value measured on oscilloscope is 125 μs (see designingvcnl4040.txt lines 438, 461). All calculations use 125 μs.

### 2. Duty Cycle (PS_Duty) — Controls MEASUREMENT PERIOD

The duty cycle denominator multiplies the pulse width to set the total measurement period:

```
Measurement Period ≈ Pulse Width × Duty Denominator
Measurement Rate ≈ 1 / Period
```

| Duty Cycle | Multiplier | Period @ 1T | Rate @ 1T | Period @ 2T | Rate @ 2T |
|-----------|-----------|-----------|---------|-----------|---------|
| 1/40 | ×40 | ~5 ms | ~200 Hz | ~10 ms | ~100 Hz |
| 1/80 | ×80 | ~10 ms | ~100 Hz | ~20 ms | ~50 Hz |
| 1/160 | ×160 | ~20 ms | ~50 Hz | ~40 ms | ~25 Hz |
| 1/320 | ×320 | ~40 ms | ~25 Hz | ~80 ms | ~12.5 Hz |

> **Confidence: Medium.** This formula is derived from the Vishay design guide, not explicitly stated. The design guide says 1T/1/40 yields measurements "every 4.85 ms" (line 430), while our formula gives 5.0 ms. It also confirms proportionality: "These pulse lengths are always doubled... but the repetition time is also doubled" (lines 439-441). The formula is a close approximation (~3% error at 1T/1/40) but may not be exact.

**Both IT and duty cycle directly determine the measurement rate.** There is no way around this — longer integration time = slower rate at the same duty cycle.

### 3. Multi-Pulse (PS_MPS) — SIGNAL BOOST (LIKELY NO RATE PENALTY)

Multi-pulse fires 1/2/4/8 consecutive IR pulses per measurement and accumulates the result. This boosts signal strength and is believed to not affect the measurement rate because all pulses fit within the measurement period.

| Setting | Pulses | Signal Boost | Rate Impact |
|---------|--------|-------------|-------------|
| x1 | 1 | 1× | None (believed) |
| x2 | 2 | ~2× | None (believed) |
| x4 | 4 | ~4× | None (believed) |
| x8 | 8 | ~8× | None (believed) |

> **Confidence: Medium.** The Vishay datasheet and design guide say nothing about how PS_MPS affects measurement timing. The best evidence comes from the Linux kernel IIO driver (Astrid Rost, Axis Communications, 2023): *"Instead of one single pulse per every defined time frame, one can program 2, 4, or even 8 pulses."* The phrase "per every defined time frame" implies the period is fixed and multi-pulse fires within it. However, this is a third-party interpretation, not a Vishay specification. Empirical testing on our hardware is recommended to confirm.

---

## Full Rate Table (at 1/40 duty)

| IT | x1 Rate | x1 Signal | x4 Rate | x4 Signal | x8 Rate | x8 Signal |
|----|---------|-----------|---------|-----------|---------|-----------|
| 1T | 200 Hz | 1× | 200 Hz | ~4× | 200 Hz | ~8× |
| 2T | 100 Hz | 2× | 100 Hz | ~8× | 100 Hz | ~16× |
| 4T | 50 Hz | 4× | 50 Hz | ~16× | 50 Hz | ~32× |
| 8T | 25 Hz | 8× | 25 Hz | ~32× | 25 Hz | ~64× |

**Key insight (if multi-pulse is rate-free as believed):** Multi-pulse gives you the signal boost of a higher IT without the rate penalty. `1T/x8` would give ~8× signal at 200 Hz, while `8T/x1` also gives ~8× signal but at only 25 Hz.

---

## From the Vishay Design Guide

### Integration Time (Lines 537-543)
> "If higher detection distances and / or objects with very low reflectivity should be detected, there is the option to extend these proximity pulses up to about 1000 μs for 8T. This results in higher counts"

- 8T can achieve 10,000+ counts vs 1,000 counts with 1T (see Fig 14 vs Fig 15)
- Better SNR because more photons are collected per pulse

### Duty Cycle (Lines 515-520, 564-569)
> "With defining the duty time (PS_Duty), the repetition rate = the number of proximity measurements per second (speed of proximity measurements) is defined. This is possible between 5 ms (about 200 measurements/s) by programming PS_Duty with 1/40 and 40 ms (about 25 measurements/s) with programming PS_Duty with 1/320."

Note: The "5 ms → 200 Hz" figure is for 1T integration time. With longer IT, the period increases proportionally. Also note the design guide says "4.85 ms" for 1T/1/40 (line 430), not exactly 5 ms.

---

## Configuration Strategy for Motion Play

### The Trade-off

You need **enough samples per transit** to form a clear detection wave. For a ball traveling at up to 13.4 m/s (30 mph) through a 450mm hoop with a size 3 ball (190mm), the transit takes ~14 ms. At that speed:

| Config | Rate | Samples per transit | Verdict |
|--------|------|-------------------|---------|
| 1T/x4 @ 1/40 | 200 Hz | 2.8 | Marginal |
| 2T/x4 @ 1/40 | 100 Hz | 1.4 | Likely missed |
| 1T/x8 @ 1/40 | 200 Hz | 2.8 | Marginal (best signal) |

For typical throws (5-8 m/s), transit takes ~24-38 ms:

| Config | Rate | Samples @ 8 m/s | Samples @ 5 m/s |
|--------|------|-----------------|-----------------|
| 1T/x4 @ 1/40 | 200 Hz | 4.8 | 7.6 |
| 2T/x4 @ 1/40 | 100 Hz | 2.4 | 3.8 |
| 1T/x8 @ 1/40 | 200 Hz | 4.8 | 7.6 |

### Recommended Configurations

**Best for fast objects (speed priority):**
```
Integration Time: 1T
Multi-Pulse: x8            // Compensate with multi-pulse for signal
Duty Cycle: 1/40
LED Current: 200mA
→ 200 Hz, ~8× signal
```

**Best balance (recommended starting point):**
```
Integration Time: 2T
Multi-Pulse: x4
Duty Cycle: 1/40
LED Current: 200mA
→ 100 Hz, ~8× signal
```

**Best for slow/weak objects (sensitivity priority):**
```
Integration Time: 4T
Multi-Pulse: x4
Duty Cycle: 1/40
LED Current: 200mA
→ 50 Hz, ~16× signal
```

Use `python3 tools/transit-calculator.py` to model samples-per-transit for your specific setup.

---

## Power Consumption

For Motion Play (USB-powered), power is not a concern. Use 1/40 duty cycle.

For reference, at 200mA LED current:
- **1/40 duty**: Avg LED current = 200mA / 40 = **5.0 mA**
- **1/320 duty**: Avg LED current = 200mA / 320 = **0.625 mA**

---

## I2C Pipeline

The firmware reads all 6 sensors sequentially through a TCA9548A → PCA9546A mux chain at 400 kHz I2C. A complete read cycle takes ~1.8 ms (~549 polls/sec), which is faster than the sensor's measurement rate at all practical settings.

**The sensor's internal measurement rate is always the bottleneck, not the I2C pipeline.**

See `SENSOR_READING_PIPELINE.md` for the complete timing analysis with sequence diagrams.

---

## Current Configuration Status

- ✅ Integration Time: Exposed in cloud config
- ✅ LED Current: Exposed in cloud config
- ✅ Duty Cycle: Exposed in cloud config (default: 1/40)
- ✅ Multi-Pulse: Exposed in cloud config
- ✅ High Resolution: Exposed in cloud config

---

## Evidence & References

### Primary Sources (Vishay)
- **Design Guide** (`designingvcnl4040.txt`) — Contains oscilloscope measurements (1T = 125 μs), duty cycle timing data (1T/1/40 = 4.85 ms), and the proportionality statement for IT vs repetition time. Does NOT mention PS_MPS at all.
- **Datasheet** (`vcnl4040_datasheet_text.txt`) — Register definitions only. PS_MPS described as "Proximity multi pulse numbers: 1, 2, 4, 8 multi pulses" with no timing information.

### Third-Party Sources
- **Linux kernel IIO driver** — [Patch series by Astrid Rost (Axis Communications, May 2023)](https://patchew.org/linux/20230517151406.368219-1-astrid.rost@axis.com/). Treats PS_MPS as "oversampling_ratio" and describes it as firing multiple pulses "per every defined time frame." Treats IT, duty cycle, and multi-pulse as independent parameters.

### Project Tools
- Sensor Reading Pipeline (`SENSOR_READING_PIPELINE.md`)
- Transit Calculator (`tools/transit-calculator.py`)

---

*Last Updated: February 2026*

# VCNL4040 Configuration Experiments

**Purpose**: Systematically test different sensor configurations to find optimal settings for direction detection.

## Experiment Log Template

Copy this template for each experiment:

```
### Experiment [NUMBER]
**Date**: [YYYY-MM-DD HH:MM]
**Session ID**: [from web UI]

#### Configuration
- LED Current: [50/75/100/120/140/160/180/200] mA
- Integration Time: [1T/1.5T/2T/2.5T/3T/3.5T/4T/8T]
- Duty Cycle: [1/40 / 1/80 / 1/160 / 1/320]
- High Resolution: [On/Off]
- Ambient Light: [On/Off]

#### Test Conditions
- Object: [description - e.g., "tennis ball, yellow"]
- Speed: [slow/medium/fast]
- Direction: [A→B / B→A]
- Trajectory: [center/edge]

#### Results
- Calculated Sample Rate: [X] Hz
- Peak Proximity Value: [X] counts
- Baseline Proximity: [X] counts
- Signal-to-Noise Ratio: [peak / baseline]
- Direction Detection: [clear/marginal/failed]
- Notes: [any observations]
```

---

## Baseline Experiment (Current Settings)

### Experiment 1 - Baseline
**Date**: [Your date]
**Session ID**: device-001_49191 (from short_sample_4T.csv)

#### Configuration
- LED Current: 200mA
- Integration Time: 4T
- Duty Cycle: 1/40
- High Resolution: On
- Ambient Light: Off

#### Calculated Metrics
- Time span: 829ms
- Complete cycles: 381
- **Firmware read rate: ~460 Hz**
- **Actual sensor update rate: ~50 Hz** (4T × 1/40 = 20ms period)
- You're reading the same value ~9 times before it changes

#### Observations
- Direction detection works but is "very close"
- Multiple redundant readings between actual sensor updates

---

## Recommended Experiments

### Experiment 2 - Speed Priority (1T)
**Goal**: Maximize sample rate

#### Configuration
- LED Current: 200mA (keep max power to compensate)
- Integration Time: **1T** (fastest)
- Duty Cycle: 1/40
- High Resolution: On
- Ambient Light: Off

#### Expected
- Actual sensor rate: ~200 Hz (4× improvement!)
- Trade-off: Lower signal per reading

---

### Experiment 3 - Balanced (2T)
**Goal**: Good speed + decent signal

#### Configuration
- LED Current: 200mA
- Integration Time: **2T**
- Duty Cycle: 1/40
- High Resolution: On
- Ambient Light: Off

#### Expected
- Actual sensor rate: ~100 Hz (2× improvement)
- Better signal than 1T

---

### Experiment 4 - Resolution Impact
**Goal**: Check if 12-bit vs 16-bit affects timing

#### Configuration A (12-bit)
- High Resolution: **Off**
- Other settings: same as Experiment 2

#### Configuration B (16-bit)
- High Resolution: **On**
- Other settings: same as Experiment 2

**Note**: Resolution shouldn't affect sample rate (it's just a mode bit), but worth verifying.

---

### Experiment 5 - Ambient Light Impact
**Goal**: Check if reading ambient slows things down

#### Configuration
- Ambient Light: **On**
- Other settings: same as Experiment 2

**Expected**: Each I2C cycle takes slightly longer (extra register read), but shouldn't significantly impact rate since I2C isn't your bottleneck.

---

## Analysis Script

Save this Python script to analyze your exported CSV files:

```python
#!/usr/bin/env python3
"""Analyze Motion Play session data for configuration comparison."""

import pandas as pd
import sys
from pathlib import Path

def analyze_session(csv_path: str):
    """Analyze a session CSV file."""
    df = pd.read_csv(csv_path)
    
    # Calculate metrics
    timestamps = df['timestamp_offset'].unique()
    time_span_ms = timestamps[-1] - timestamps[0]
    num_cycles = len(timestamps)
    firmware_rate = (num_cycles / time_span_ms) * 1000
    
    # Per-sensor stats
    print(f"\n=== Session Analysis: {Path(csv_path).name} ===")
    print(f"Time span: {time_span_ms} ms")
    print(f"Complete cycles: {num_cycles}")
    print(f"Firmware read rate: {firmware_rate:.1f} Hz")
    
    # Calculate gaps between timestamps
    gaps = pd.Series(timestamps).diff().dropna()
    print(f"Average gap between reads: {gaps.mean():.2f} ms")
    print(f"Min/Max gap: {gaps.min():.0f} / {gaps.max():.0f} ms")
    
    # Per-sensor proximity stats
    print(f"\n--- Proximity Statistics ---")
    for (pcb, side), group in df.groupby(['pcb_id', 'side']):
        prox = group['proximity']
        print(f"P{pcb}S{side}: baseline={prox.median():.0f}, peak={prox.max()}, range={prox.max()-prox.min()}")
    
    # Calculate effective sensor update rate
    # Look for actual value changes in proximity readings
    print(f"\n--- Effective Sensor Update Analysis ---")
    for (pcb, side), group in df.groupby(['pcb_id', 'side']):
        values = group['proximity'].values
        changes = sum(1 for i in range(1, len(values)) if values[i] != values[i-1])
        effective_rate = (changes / time_span_ms) * 1000
        redundancy = len(values) / max(changes, 1)
        print(f"P{pcb}S{side}: {changes} unique values in {len(values)} reads ({redundancy:.1f}x redundancy)")
    
    return df

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python analyze_session.py <session.csv>")
        sys.exit(1)
    
    analyze_session(sys.argv[1])
```

---

## Quick Reference: Expected Sensor Rates

| Integration Time | Duty 1/40 | Duty 1/80 | Duty 1/160 | Duty 1/320 |
|------------------|-----------|-----------|------------|------------|
| 1T (125μs)       | **200 Hz**| 100 Hz    | 50 Hz      | 25 Hz      |
| 2T (250μs)       | 100 Hz    | 50 Hz     | 25 Hz      | 12.5 Hz    |
| 4T (500μs)       | 50 Hz     | 25 Hz     | 12.5 Hz    | 6.25 Hz    |
| 8T (1000μs)      | 25 Hz     | 12.5 Hz   | 6.25 Hz    | 3.125 Hz   |

Formula: `Rate = 1000 / (pulse_μs × duty_denominator / 1000)`

---

*Last Updated: [Date]*


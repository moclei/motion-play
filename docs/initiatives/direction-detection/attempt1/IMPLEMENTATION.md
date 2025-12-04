# Direction Detection - Attempt 1: Implementation

## Algorithm: Derivative-Based Peak Detection

This document specifies the chosen algorithm for detecting object direction through the sensor hoop.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         ALGORITHM PIPELINE                               │
│                                                                          │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│  │ Aggregate │ -> │  Smooth  │ -> │  Find    │ -> │ Compare  │ -> Result│
│  │  by Side  │    │ (optional)│   │  Peaks   │    │  Timing  │          │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Sensor Orientation Reference

| PCB | Side 1 | Side 2 |
|-----|--------|--------|
| 1   | B-facing | A-facing |
| 2   | B-facing | A-facing |
| 3   | B-facing | A-facing |

- **Side A**: Near side (developer-facing)
- **Side B**: Far side
- **A→B pass**: Object enters from Side A, exits toward Side B (triggers sensor 2 first, then sensor 1)
- **B→A pass**: Object enters from Side B, exits toward Side A (triggers sensor 1 first, then sensor 2)

## Algorithm Steps

### Step 1: Aggregate by Side

Combine all sensors facing the same direction into a single signal per side.

```
For each timestamp t:
    side_A[t] = proximity(pcb1, side2) + proximity(pcb2, side2) + proximity(pcb3, side2)
    side_B[t] = proximity(pcb1, side1) + proximity(pcb2, side1) + proximity(pcb3, side1)
```

**Why aggregate?**
- Handles sensor-to-sensor sensitivity variation (one PCB might peak at 268, another at 40)
- Edge passes activate fewer PCBs, but still contribute to the aggregate
- Center passes activate all PCBs, aggregate naturally captures this

### Step 2: Smooth the Signal (Optional)

Apply a simple moving average to reduce noise in the derivative.

```
window_size = 3  # tunable

side_A_smooth[t] = mean(side_A[t-window_size+1 : t+1])
side_B_smooth[t] = mean(side_B[t-window_size+1 : t+1])
```

**Note**: May not be necessary - test with and without smoothing.

### Step 3: Compute Derivatives

Calculate the rate of change for each side's aggregate signal.

```
For each timestamp t (where t > 0):
    d_A[t] = side_A[t] - side_A[t-1]
    d_B[t] = side_B[t] - side_B[t-1]
```

### Step 4: Detect Peaks

A peak occurs when the derivative crosses from positive to negative.

```
peaks_A = []
peaks_B = []

For each timestamp t (where t > 1):
    if d_A[t-1] > 0 and d_A[t] <= 0:
        peaks_A.append(t)
    if d_B[t-1] > 0 and d_B[t] <= 0:
        peaks_B.append(t)
```

**Refinement**: To filter minor fluctuations, require a minimum "rise" before considering a peak:

```
min_rise = 10  # tunable - minimum increase from trough to peak

# Track the value at the start of the current rise
rise_start_A = side_A[0]

For each timestamp t:
    if d_A[t] > 0 and d_A[t-1] <= 0:
        # Start of a new rise
        rise_start_A = side_A[t-1]
    
    if d_A[t-1] > 0 and d_A[t] <= 0:
        # End of rise (peak)
        rise_amount = side_A[t] - rise_start_A
        if rise_amount >= min_rise:
            peaks_A.append(t)
```

### Step 5: Find Paired Peaks

A valid pass event has peaks on **both** sides within a short time window.

```
max_peak_gap = 50  # milliseconds - tunable

For each peak_A in peaks_A:
    For each peak_B in peaks_B:
        gap = abs(peak_A - peak_B)
        if gap <= max_peak_gap:
            # Found a paired peak - this is likely a valid pass
            if peak_A < peak_B:
                return Direction.A_TO_B
            else:
                return Direction.B_TO_A
```

### Step 6: Handle Edge Cases

```
if no paired peaks found:
    return Direction.UNKNOWN  # No valid pass detected

if multiple paired peaks found:
    # Use the pair with the highest combined signal strength
    # Or use the most recent pair
```

## Parameters (Tunable)

| Parameter | Initial Value | Description |
|-----------|---------------|-------------|
| `smoothing_window` | 3 | Moving average window size (samples) |
| `min_rise` | 10 | Minimum signal increase to consider a peak valid |
| `max_peak_gap` | 50ms | Maximum time between paired peaks |
| `analysis_window` | 200ms | Size of sliding window for analysis |

## Architecture: Dual-Core Processing

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            ESP32                                         │
│                                                                          │
│  ┌────────────────────────┐       ┌────────────────────────────────┐   │
│  │       CORE 0           │       │           CORE 1               │   │
│  │                        │       │                                │   │
│  │  ┌──────────────────┐  │       │  ┌──────────────────────────┐  │   │
│  │  │ Sensor Polling   │  │       │  │ Direction Detector       │  │   │
│  │  │ Loop (2-3ms)     │  │       │  │                          │  │   │
│  │  └────────┬─────────┘  │       │  │ analyzeWindow(buffer)    │  │   │
│  │           │            │       │  │   -> aggregate           │  │   │
│  │           ▼            │       │  │   -> derivatives         │  │   │
│  │  ┌──────────────────┐  │       │  │   -> find peaks          │  │   │
│  │  │ Ring Buffer      │──────────│──│   -> compare timing      │  │   │
│  │  │ (shared memory)  │  │       │  │   -> return direction    │  │   │
│  │  └──────────────────┘  │       │  └──────────────────────────┘  │   │
│  │                        │       │              │                 │   │
│  └────────────────────────┘       │              ▼                 │   │
│                                   │  ┌──────────────────────────┐  │   │
│                                   │  │ LED Controller           │  │   │
│                                   │  │ (react to direction)     │  │   │
│                                   │  └──────────────────────────┘  │   │
│                                   └────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
```

**Data Flow**:
1. Core 0 polls sensors continuously, writes to ring buffer
2. Core 1 periodically (every ~100ms) takes a snapshot of recent data
3. Core 1 runs `analyzeWindow()` on the snapshot
4. If direction detected, Core 1 triggers LED response

## Interface Design (Modular)

```cpp
// Abstract interface - allows swapping algorithms
class DirectionDetector {
public:
    virtual ~DirectionDetector() = default;
    
    struct Result {
        enum class Direction { UNKNOWN, A_TO_B, B_TO_A };
        Direction direction;
        float confidence;  // 0.0 - 1.0
        uint32_t peakTimeDelta;  // ms between peaks
    };
    
    virtual Result analyze(const SensorReading* buffer, size_t count) = 0;
};

// Concrete implementation
class DerivativePeakDetector : public DirectionDetector {
public:
    DerivativePeakDetector(const Config& config);
    Result analyze(const SensorReading* buffer, size_t count) override;
    
private:
    Config config_;
    // ... implementation details
};
```

## Validation Plan

1. **Python Prototype**: Implement algorithm in Python, run against all labeled CSV files
2. **Accuracy Metrics**: Track true positives, false positives, direction accuracy
3. **Parameter Tuning**: Adjust `min_rise`, `max_peak_gap`, etc. based on results
4. **C++ Port**: Once Python achieves acceptable accuracy, port to firmware

## Expected Behavior by Pass Type

| Pass Type | Expected Pattern |
|-----------|------------------|
| A→B Center | All PCBs activate, Side A peaks ~10-30ms before Side B |
| A→B Edge | 1-2 PCBs activate strongly, same timing pattern |
| B→A Center | All PCBs activate, Side B peaks ~10-30ms before Side A |
| B→A Edge | 1-2 PCBs activate strongly, same timing pattern |
| No Pass (baseline) | No paired peaks detected |
| Random Spike | Single peak on one side only, no pair → filtered out |

## Completed Steps

1. [x] Build Python prototype (`scripts/direction_detection/attempt1.py`)
2. [x] Run against all labeled data in `session_data/labeled-data/group1/`
3. [x] Calculate accuracy and tune parameters
4. [x] Document results in `RESULTS.md`
5. [x] Proceed to C++ implementation (firmware)

---

## C++ Firmware Implementation

### Files Created

| File | Description |
|------|-------------|
| `firmware/src/components/detection/DirectionDetector.h` | Header file with detector interface and configuration |
| `firmware/src/components/detection/DirectionDetector.cpp` | Rise-start algorithm implementation |
| `firmware/src/components/led/LEDController.h` | LED strip control interface |
| `firmware/src/components/led/LEDController.cpp` | LED animation for direction feedback |

### Device Modes

The firmware now supports three modes, controlled via MQTT `set_mode` command:

| Mode | Behavior |
|------|----------|
| `idle` | Standby mode, no sensor activity |
| `debug` | Data collection mode (existing behavior) - collects sensor data and uploads to cloud |
| `play` | Active game mode - runs direction detection algorithm and lights LEDs |

### LED Feedback

| Direction | LED Color | Duration |
|-----------|-----------|----------|
| A→B | Blue (#0064FF) | 3 seconds |
| B→A | Orange (#FF6400) | 3 seconds |
| Unknown | White flash | 0.5 seconds |
| Ready | Pulsing dim green | Continuous while waiting |

### How to Use

1. **Set mode to PLAY**:
   ```json
   {"command": "set_mode", "mode": "play"}
   ```

2. **Start detection**:
   ```json
   {"command": "start_collection"}
   ```
   In play mode, this starts the direction detection loop instead of data collection.

3. **Stop detection**:
   ```json
   {"command": "stop_collection"}
   ```

### Algorithm Configuration

The `DetectorConfig` struct in `DirectionDetector.h` allows tuning:

```cpp
struct DetectorConfig {
    uint8_t smoothingWindow = 3;     // Moving average window
    uint16_t minRise = 10;           // Minimum signal increase for valid peak
    uint32_t maxPeakGapMs = 100;     // Max time between paired peaks
    float derivativeThreshold = 2.0; // Min derivative to count as "rising"
};
```

### Detection Flow in Play Mode

1. Sensors continuously poll readings into session buffer
2. New readings are fed to `DirectionDetector`
3. Every detection cycle, the detector:
   - Aggregates readings by side (A: sensor 2s, B: sensor 1s)
   - Computes smoothed signals and derivatives
   - Finds significant rises on each side
   - Compares rise timing to determine direction
4. On successful detection:
   - LEDs light up with direction color for 3 seconds
   - Display shows direction
   - MQTT status published
   - 3-second cooldown before next detection
5. Buffer is cleared after each detection to prepare for next event

### Notes

- Detection has a 3-second cooldown between events
- Buffer is limited to 500 readings to prevent memory issues
- LED animations include a fade-out effect in the last 500ms


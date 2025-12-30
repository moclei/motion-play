# Calibration System Initiative

> **Status:** Phase 1 & 2 Complete ✅  
> **Created:** 2025-12-29  
> **Last Updated:** 2025-12-30

## Implementation Status

| Phase | Status | Notes |
|-------|--------|-------|
| Phase 1: Core Infrastructure | ✅ Complete | Firmware compiles and works |
| Phase 2: Frontend Integration | ✅ Complete | Calibration button added to ModeSelector |
| Phase 3: Detection Integration | 🔲 Not Started | Thresholds not yet used by DirectionDetector |
| Phase 4: Persistence | 🔲 Not Started | Data only in RAM currently |

## Overview

The calibration system provides a guided wizard for characterizing sensor behavior in their installed environment. It captures both the noise floor (baseline) and expected signal range (from user-initiated waves), enabling more accurate and reliable detection thresholds.

## Problem Statement

Current detection issues with multi-pulse mode:
- Baseline calibration (50 readings, ~150ms) doesn't capture full noise variation
- No reference for what a "real" detection looks like for this specific sensor/environment
- Per-sensor noise characteristics vary significantly but thresholds are calculated uniformly
- False triggers occur when noise spikes exceed calculated thresholds

## Goals

1. **Capture both noise floor AND signal ceiling** per sensor/PCB
2. **Per-sensor characterization** to account for hardware variance
3. **Environment-specific tuning** at installation time
4. **Data persistence** for consistent behavior across sessions
5. **Future ML pipeline** - calibration sessions become labeled training data

---

## Original Intent

The original discussion identified that:

1. Multi-pulse mode (2x pulses) increases noise amplitude variability
2. The baseline calibration period was too short to capture full noise range
3. Each sensor has different noise profiles that need individual thresholds
4. Real detections show peaks of 44-101 while false triggers max at ~20
5. There's no mechanism to know what a "real" signal looks like for validation

The calibration wizard addresses all of these by having the user perform known actions (waving through the hoop) while the system measures the expected signal ranges.

---

## Possible Directions

### Direction A: Per-PCB Calibration with Approach Motion (Recommended for MVP)
- Calibrate 3 PCBs sequentially
- User moves hand TOWARD sensor and HOLDS (not wave-through)
- Captures sustained "object present" readings
- Simpler detection: just need elevated readings, not wave pattern
- Aggregate both sensors on each PCB

### Direction B: Per-Sensor Calibration
- Calibrate all 6 sensors individually
- Most granular, best accuracy
- More complex UI, longer process
- Better for debugging sensor issues

### Direction C: Single-Pass Calibration
- User waves through entire hoop once
- System detects which sensors fired and captures all data
- Fastest UX, but less controlled
- May miss sensors if wave path isn't optimal

### Direction D: Automatic Calibration (Future)
- Device learns from first N real detections
- No user interaction required
- Requires initial rough thresholds to work
- Best UX but needs ML/heuristics

**Decision:** Start with **Direction A (Per-PCB with Approach)** for MVP. This separates "baseline" (nothing present) from "signal" (object close) without requiring direction detection to work.

### Why "Approach and Hold" Instead of "Wave Through"

A wave-through motion:
- Object enters → peaks briefly → exits
- Gives transient signal with brief peak
- Good for direction detection timing calibration

An approach-and-hold motion:
- Object approaches → stays close → retreats
- Gives sustained high readings
- Captures full range of "object present" values
- Better for simple proximity threshold calibration

**For establishing proximity thresholds, we need to know:**
1. What readings look like with NOTHING present (baseline)
2. What readings look like with SOMETHING present (signal)

The approach-and-hold motion cleanly separates these two states.

---

## Current Plan: MVP Specification

### What Gets Calibrated

For each PCB (1-3), capture:

| Metric | How Captured | Purpose |
|--------|--------------|---------|
| `baseline_min` | Min reading during quiet period | Noise floor |
| `baseline_max` | Max reading during quiet period | Noise ceiling |
| `baseline_mean` | Average during quiet period | Central tendency |
| `baseline_stddev` | Std deviation during quiet | Noise variability |
| `signal_min` | Min peak during wave | Weakest valid detection |
| `signal_max` | Max peak during wave | Strongest detection |
| `signal_mean` | Average peak across waves | Expected detection level |

Derived thresholds:
```
threshold = baseline_max + ((signal_min - baseline_max) / 2)
// Halfway between noise ceiling and weakest real signal
```

### Calibration Triggers

**MVP triggers (in priority order):**

1. **Frontend Mode Selection**
   - Add `CALIBRATE` to device modes (alongside IDLE/DEBUG/PLAY)
   - User clicks mode selector → device enters calibration wizard
   - On completion, device returns to IDLE mode

2. **Physical Button Hold**
   - Hold Button 1 on T-Display for 3 seconds
   - Device enters calibration mode
   - Works offline (no WiFi needed)

**Future triggers (post-MVP):**

3. **Auto-prompt on first session**
   - When entering DEBUG/PLAY mode with no calibration data
   - Prompt: "Device not calibrated. Calibrate now? [Yes] [Skip]"
   - Skip uses fallback thresholds

4. **Session config option**
   - Checkbox: "Recalibrate before session"
   - Useful when environment has changed

### Calibration Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    CALIBRATION WIZARD                        │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  State Machine:                                              │
│                                                              │
│  IDLE ──(trigger)──► INTRO ──(2s)──► BASELINE_PCB1          │
│                                              │               │
│                                              ▼               │
│                                        APPROACH_PCB1         │
│                                              │               │
│                                              ▼               │
│                                        BASELINE_PCB2         │
│                                              │               │
│                                              ▼               │
│                                        APPROACH_PCB2         │
│                                              │               │
│                                              ▼               │
│                                        BASELINE_PCB3         │
│                                              │               │
│                                              ▼               │
│                                        APPROACH_PCB3         │
│                                              │               │
│                                              ▼               │
│                                        SUMMARY               │
│                                              │               │
│                                              ▼               │
│                                          COMPLETE ──► IDLE   │
│                                                              │
│  Any state can transition to:                                │
│    - CANCELLED (button press)                                │
│    - FAILED (timeout or hardware issue) ──► abort all        │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### Timing

| Phase | Duration | Completion |
|-------|----------|------------|
| INTRO | 2 seconds | Fixed |
| BASELINE_PCBx | 600ms | Fixed (need consistent data) |
| APPROACH_PCBx | Up to 10s | **Early complete** if 500ms of sustained elevated readings |
| Per-PCB total | ~3-5 seconds typical | |
| **Full calibration** | **~15-25 seconds** | Depending on user speed |

### UI Screens (T-Display)

```
INTRO (2 seconds):
┌─────────────────────────────────────────┐
│         CALIBRATION MODE                │
│                                         │
│   This wizard will calibrate your       │
│   sensors for optimal detection.        │
│                                         │
│   For each PCB, you'll:                 │
│   1. Keep area clear (baseline)         │
│   2. Move hand close and HOLD           │
│                                         │
│   Starting in 3...                      │
└─────────────────────────────────────────┘

BASELINE_PCBx (600ms):
┌─────────────────────────────────────────┐
│         CALIBRATION MODE                │
│                                         │
│   Step x of 3: PCB x                    │
│                                         │
│   ⏳ Measuring baseline...              │
│   [████████░░] 80%                      │
│                                         │
│   🚫 Keep area CLEAR!                   │
│                                         │
│   [Press BTN2 to cancel]                │
└─────────────────────────────────────────┘

APPROACH_PCBx:
┌─────────────────────────────────────────┐
│         CALIBRATION MODE                │
│                                         │
│   Step x of 3: PCB x                    │
│                                         │
│   ✓ Baseline: 12                        │
│                                         │
│   🖐️ Move hand CLOSE to PCB x          │
│      and HOLD for a moment              │
│                                         │
│   Waiting... (10s timeout)              │
└─────────────────────────────────────────┘

APPROACH_PCBx (detecting):
┌─────────────────────────────────────────┐
│         CALIBRATION MODE                │
│                                         │
│   Step x of 3: PCB x                    │
│                                         │
│   ✓ Baseline: 12                        │
│                                         │
│   📡 Detecting! Hold steady...          │
│   Current: 78                           │
│   [██████░░░░] 60%                      │
│                                         │
└─────────────────────────────────────────┘

APPROACH_PCBx (success):
┌─────────────────────────────────────────┐
│         CALIBRATION MODE                │
│                                         │
│   Step x of 3: PCB x                    │
│                                         │
│   ✅ Captured!                          │
│                                         │
│   Baseline: 12                          │
│   Signal:   65 - 92 (peak)              │
│   Threshold: 38                         │
│                                         │
│   [Continuing in 1s...]                 │
└─────────────────────────────────────────┘

FAILED:
┌─────────────────────────────────────────┐
│       CALIBRATION FAILED ❌             │
│                                         │
│   PCB x did not respond.                │
│                                         │
│   Possible causes:                      │
│   - Sensor not connected                │
│   - I2C communication error             │
│   - Hand not close enough               │
│                                         │
│   Calibration aborted.                  │
│   [Press any button to exit]            │
└─────────────────────────────────────────┘

SUMMARY:
┌─────────────────────────────────────────┐
│       CALIBRATION COMPLETE! ✅          │
│                                         │
│   PCB1: Base=8,  Signal=92,  T=50      │
│   PCB2: Base=12, Signal=105, T=58      │
│   PCB3: Base=15, Signal=88,  T=51      │
│                                         │
│   Calibration saved to memory.          │
│                                         │
│   [Press any button to continue]        │
└─────────────────────────────────────────┘
```

### Data Structures

```cpp
// Single PCB calibration data
struct PCBCalibration {
    uint8_t pcb_id;               // 1-3
    
    // Baseline stats (noise floor)
    uint16_t baseline_min;
    uint16_t baseline_max;
    uint16_t baseline_mean;
    uint16_t baseline_stddev;
    
    // Signal stats (during wave detection)
    uint16_t signal_peak;         // Maximum reading during wave
    uint16_t signal_min_peak;     // For multi-wave: minimum of peaks
    
    // Derived threshold
    uint16_t threshold;           // Calculated optimal threshold
    
    // Validity
    bool valid;
};

// Complete device calibration
struct DeviceCalibration {
    uint32_t magic;               // 0xCA11B123 - validity marker
    uint32_t version;             // Schema version
    uint32_t timestamp;           // When calibration was performed
    
    // Sensor config at calibration time (for reference)
    uint8_t multi_pulse;
    uint8_t integration_time;
    uint8_t led_current;
    
    // Per-PCB data
    PCBCalibration pcbs[3];
    
    // Overall validity
    bool isValid() const { 
        return magic == 0xCA11B123 && 
               pcbs[0].valid && pcbs[1].valid && pcbs[2].valid; 
    }
};
```

### Storage Strategy

| Phase | Storage | Behavior |
|-------|---------|----------|
| MVP | RAM only | Lost on reboot, must recalibrate |
| v1.1 | + LittleFS | Persists across reboots |
| v1.2 | + Cloud sync | Upload to DynamoDB, downloadable for analysis |

### Integration with Detection

```cpp
// In DirectionDetector or InterruptManager:
void calculateThresholds() {
    if (calibration.isValid()) {
        // Use calibrated thresholds
        for (int i = 0; i < 3; i++) {
            pcbThreshold[i] = calibration.pcbs[i].threshold;
        }
    } else {
        // Fallback to current behavior
        threshold = baseline_max + minRise;
    }
}
```

---

## Implementation Plan

### Phase 1: Core Infrastructure (MVP) ✅ COMPLETE

- [x] **1.1** Create `CalibrationManager` component
  - [x] 1.1.1 Define `CalibrationState` enum (IDLE, INTRO, BASELINE_PCB1, APPROACH_PCB1, etc.)
  - [x] 1.1.2 Create `CalibrationManager` class with state machine
  - [x] 1.1.3 Implement `begin()`, `update()`, `isActive()` methods
  - [x] 1.1.4 Timer management for phase transitions
  - [x] 1.1.5 Sensor reading aggregation per PCB

- [x] **1.2** Create `CalibrationData` structures
  - [x] 1.2.1 Define `PCBCalibration` struct
  - [x] 1.2.2 Define `DeviceCalibration` struct with validity checking
  - [x] 1.2.3 Create global/singleton storage instance (`deviceCalibration`)
  - [x] 1.2.4 Implement threshold calculation method

- [x] **1.3** Implement approach detection for calibration
  - [x] 1.3.1 Detect when readings exceed 2× baseline (elevated)
  - [x] 1.3.2 Track sustained elevated readings (target: 500ms)
  - [x] 1.3.3 Early completion when sufficient data captured
  - [x] 1.3.4 Timeout handling (10 seconds max)
  - [x] 1.3.5 Calculate min/max/mean of signal readings (via `StatsAccumulator`)

- [x] **1.4** Add T-Display UI screens
  - [x] 1.4.1 Intro screen (3 second countdown)
  - [x] 1.4.2 Baseline measurement screen (with progress bar)
  - [x] 1.4.3 Approach prompt screen
  - [x] 1.4.4 "Detecting" screen (shows live readings + hold progress)
  - [x] 1.4.5 Success screen (shows green checkmark)
  - [x] 1.4.6 Failure screen (abort message with reason)
  - [x] 1.4.7 Summary screen (all PCB thresholds)

- [x] **1.5** Add physical button trigger
  - [x] 1.5.1 Detect Button 1 (GPIO 14) hold for 3 seconds
  - [x] 1.5.2 Enter calibration mode on trigger
  - [x] 1.5.3 Button 2 (BOOT) to cancel during calibration
  - [x] 1.5.4 Any button to dismiss summary screen

**Files created:**
- `firmware/src/components/calibration/CalibrationData.h`
- `firmware/src/components/calibration/CalibrationManager.h`
- `firmware/src/components/calibration/CalibrationManager.cpp`

**Files modified:**
- `firmware/src/components/display/DisplayManager.h` - Added 8 calibration UI methods
- `firmware/src/components/display/DisplayManager.cpp` - Implemented calibration screens
- `firmware/src/main.cpp` - Integrated CalibrationManager, button trigger, MQTT handler

### Phase 2: Frontend Integration ✅ COMPLETE

- [x] **2.1** Add CALIBRATE mode to device modes
  - [x] 2.1.1 Calibration handled as action (not persistent mode like IDLE/DEBUG/PLAY)
  - [x] 2.1.2 Handle `SET_MODE` command with `mode: "calibrate"`
  - [x] 2.1.3 Device returns to previous display after calibration completes

- [x] **2.2** Update frontend mode selector
  - [x] 2.2.1 Add "Start Calibration" button below mode selector
  - [x] 2.2.2 Show calibration-in-progress indicator (purple theme)
  - [x] 2.2.3 Disable calibration when not in IDLE mode (must stop collection first)

- [~] **2.3** Display calibration status in frontend (DEFERRED)
  - [ ] 2.3.1 Show "Calibrated" / "Not Calibrated" badge
  - [ ] 2.3.2 Show calibration timestamp if available
  - [ ] 2.3.3 Show per-PCB threshold values
  - *Note: Deferred to Phase 3 - requires MQTT status publishing from device*

**Files modified:**
- `frontend/motion-play-ui/src/components/ModeSelector.tsx` - Added calibration section with button

### Phase 3: Detection Integration

- [ ] **3.1** Integrate calibration data into DirectionDetector
  - [ ] 3.1.1 Add `setCalibration(DeviceCalibration&)` method
  - [ ] 3.1.2 Use calibrated thresholds in `calculateThresholds()`
  - [ ] 3.1.3 Fallback to current behavior when uncalibrated

- [ ] **3.2** Update InterruptManager thresholds
  - [ ] 3.2.1 Apply per-PCB thresholds from calibration
  - [ ] 3.2.2 Reconfigure sensor registers after calibration
  - [ ] 3.2.3 Log threshold source (calibrated vs fallback)

- [ ] **3.3** Add calibration metadata to sessions
  - [ ] 3.3.1 Include `calibration_valid` flag in session data
  - [ ] 3.3.2 Include threshold values in session metadata
  - [ ] 3.3.3 Include calibration timestamp if available

### Phase 4: Persistence (Post-MVP)

- [ ] **4.1** Implement LittleFS storage
  - [ ] 4.1.1 Save calibration to `/calibration.bin` on completion
  - [ ] 4.1.2 Load calibration on boot if file exists
  - [ ] 4.1.3 Validate loaded data (magic number, version)
  - [ ] 4.1.4 Handle corruption gracefully (delete and recalibrate)

- [ ] **4.2** Cloud sync (optional)
  - [ ] 4.2.1 Add "Upload Calibration" MQTT command
  - [ ] 4.2.2 Create Lambda to store calibration in DynamoDB
  - [ ] 4.2.3 Add "Download Calibration" option in frontend
  - [ ] 4.2.4 API endpoint for calibration data retrieval

---

## Success Criteria

### MVP Complete When:
1. ✅ User can trigger calibration from device button
2. ✅ Wizard guides through all 3 PCBs
3. ✅ Approach detection works reliably (sustained elevated readings)
4. ✅ Thresholds are calculated and stored in RAM (`deviceCalibration`)
5. 🔲 DirectionDetector uses calibrated thresholds (Phase 3)

### Full Feature Complete When:
1. ✅ Frontend can trigger calibration
2. 🔲 Calibration survives reboot (LittleFS)
3. 🔲 Calibration data viewable in frontend
4. 🔲 Cloud sync operational
5. 🔲 False trigger rate reduced by >80%

---

## Decisions Made

| Question | Decision | Rationale |
|----------|----------|-----------|
| Wave vs approach | **Approach and hold** | Simpler, separates baseline from signal cleanly |
| Timeout | **10 seconds** | But complete early if 500ms sustained readings |
| Failure handling | **Abort entire calibration** | Treat as hardware issue to investigate |
| PCB naming | **PCB1, PCB2, PCB3** | No position assumptions (hardware varies) |
| Multiple samples | **Single approach per PCB** | 500ms of sustained data is sufficient |

## Open Questions (Future)

1. **Should calibration expire?** (e.g., re-prompt after 30 days or sensor config change)
2. **Should we detect sensor config changes?** (If multi-pulse changes from 2x to 4x, old calibration may be invalid)
3. **Cloud sync priority?** (v1.2 or defer further?)

---

## References

- Original discussion: Analysis of false triggers with 2-pulse mode
- Related: `docs/initiatives/interrupt-detection/` - interrupt-based detection
- Sensor config: `docs/references/vcnl4040/CONFIGURATION_GUIDE.md`

---

## Changelog

| Date | Change |
|------|--------|
| 2025-12-30 | Phase 1 & 2 implemented - firmware and frontend complete |
| 2025-12-29 | Initial planning document created |


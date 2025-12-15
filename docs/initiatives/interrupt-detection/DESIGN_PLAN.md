# VCNL4040 Interrupt-Based Direction Detection

> **Goal**: Develop an alternative detection algorithm using the VCNL4040's hardware interrupt feature instead of continuous polling, enabling comparison with our current approach and potential power savings.

---

## Executive Summary

The VCNL4040 sensors have a **hardware interrupt feature** (INT pin) that can signal threshold crossing events without continuous I2C polling. This document explores using these interrupts for direction detection as an alternative to our current polling-based approach.

**Current Approach (Polling)**:
- Sample all sensors at high rate (~1kHz aggregate)
- Collect continuous proximity values
- Use adaptive threshold + wave envelope algorithm
- Calculate center of mass timing to determine direction

**Proposed Approach (Interrupt)**:
- Configure hardware thresholds on each sensor
- Use interrupt events (close/away) as detection triggers
- Determine direction from the *timing sequence* of which sensor triggers first
- Lower power, event-driven, but less granular data

---

## VCNL4040 Interrupt Feature Deep Dive

### What the Hardware Provides

The VCNL4040 has a dedicated INT pin (pin 6) that provides hardware-level signaling:

| Feature | Description |
|---------|-------------|
| **INT Pin** | Open-drain, active LOW, requires pull-up resistor (8.2kΩ-22kΩ) |
| **Sources** | Both Proximity (PS) and Ambient Light (ALS) can generate interrupts |
| **Threshold Triggers** | High threshold (close/bright) and Low threshold (away/dark) |
| **Persistence** | 1-4 consecutive readings required before triggering (avoids false alarms) |
| **Smart Persistence** | Accelerated mode: 4 quick measurements in ~40ms instead of ~115ms |
| **Logic Output Mode** | Alternative mode where INT stays LOW while object is close |

### Proximity Interrupt Modes (PS_INT bits in PS_CONF2)

| Mode | Bits | Behavior |
|------|------|----------|
| `PS_INT_DISABLE` | 0b00 | No interrupt |
| `PS_INT_CLOSE` | 0b01 | Trigger when PS > PS_THDH (object approaches) |
| `PS_INT_AWAY` | 0b10 | Trigger when PS < PS_THDL (object leaves) |
| `PS_INT_BOTH` | 0b11 | Trigger on both close AND away |

### Key Registers for Interrupt Configuration

| Register | Address | Function |
|----------|---------|----------|
| `PS_THDL` | 0x06 | Low threshold (16-bit, triggers "away") |
| `PS_THDH` | 0x07 | High threshold (16-bit, triggers "close") |
| `PS_CONF2` | 0x03 (high byte) | PS_INT mode selection, PS resolution |
| `PS_CONF1` | 0x03 (low byte) | PS_PERS (persistence: 1-4 hits) |
| `PS_CONF3` | 0x04 (low byte) | PS_SMART_PERS enable |
| `PS_MS` | 0x04 (high byte) | PS_MS (logic output mode), LED_I |
| `INT_Flag` | 0x0B (high byte) | Status flags (read to clear) |

### Interrupt Flag Register (0x0B high byte)

| Bit | Flag | Meaning |
|-----|------|---------|
| 6 | `PS_SPFLAG` | PS entering protection mode |
| 5 | `ALS_IF_L` | ALS crossed LOW threshold |
| 4 | `ALS_IF_H` | ALS crossed HIGH threshold |
| 1 | `PS_IF_CLOSE` | PS exceeded PS_THDH |
| 0 | `PS_IF_AWAY` | PS fell below PS_THDL |

**Important**: Reading INT_Flag clears ALL flags and resets INT pin to HIGH.

### Proximity Detection Logic Output Mode

A special mode where the INT pin behaves as a simple "object present" signal:
- INT goes LOW when object exceeds high threshold
- INT stays LOW while object is present
- INT returns HIGH when object falls below low threshold
- No need to read INT_Flag to clear—it's automatic

This is useful for simple presence detection but may be less useful for direction detection since we need timing information.

---

## Direction Detection with Interrupts

### The Challenge

Our current algorithm relies on **continuous waveform analysis**:
- Track the entire "wave" as an object passes through
- Calculate center of mass (weighted timing)
- Compare centers of mass between Side A and Side B

With interrupts, we only get **discrete events**:
- "Object crossed high threshold at time T"
- "Object crossed low threshold at time T"

### Proposed Algorithm: First-Hit Direction Detection

**Core Insight**: When an object moves through the hoop, one side's sensors will trigger BEFORE the other side. The side that sees the object first indicates the entry direction.

```
Object moving A → B:

      Side A sensors          Side B sensors
           ▼                       ▼
           │                       │
     T1 ───┼──── CLOSE ────────────│───
           │                       │
     T2 ───│───────────────────────┼──── CLOSE
           │                       │
     T3 ───┼──── AWAY ─────────────│───
           │                       │
     T4 ───│───────────────────────┼──── AWAY
           │                       │
           ▼                       ▼

Direction = A→B because T1 < T2 (Side A triggered CLOSE first)
```

**Algorithm Steps**:
1. Configure all sensors with same threshold (or calibrated per-sensor)
2. Enable `PS_INT_BOTH` mode on all sensors
3. On first CLOSE event, record sensor and timestamp → start detection window
4. Collect all CLOSE events within detection window (~50-100ms)
5. Compare first CLOSE timestamps between sides
6. Direction = Side with earlier first CLOSE

**Confidence Factors**:
- Time gap between sides (larger gap = more confident)
- Number of sensors triggered on each side
- Signal strength at threshold crossing (optional: read PS data on event)

### Alternative: Hybrid Wake-on-Interrupt

Use interrupt as a "wake up" trigger, then briefly poll for detailed data:

1. Configure low threshold that detects any approach
2. On first interrupt → immediately start fast polling (~100Hz)
3. Collect ~50ms of detailed proximity data
4. Run existing direction algorithm on this short burst
5. Return to interrupt-based idle monitoring

**Pros**: Gets the best of both worlds (power savings + detailed data)
**Cons**: More complex, introduces latency, may miss fast passes

---

## Hardware Considerations

### Current Hardware Status

From the flex sensor PCB design (`DESIGN_PLAN.md`):

| Component | Description |
|-----------|-------------|
| INT lines | ✅ Routed through FPC connector (pins 2, 6) |
| INT pull-up (R5) | ✅ 8.2kΩ on rigid base board |
| Interrupt combining | ✅ BAT54S Schottky diodes (D2, D3) |

**Question**: Are the combined INT signals routed to ESP32 GPIO pins?

### What We Need to Verify

1. **INT routing to MCU**: Check if INT signals from sensor boards reach ESP32
2. **GPIO availability**: Which ESP32 pins can be used for interrupts?
3. **Multiplexer behavior**: Does TCA9548A pass through INT, or only I2C?
4. **Per-sensor INT access**: Can we read individual sensor INTs or only combined?

### Potential Hardware Modifications

If INT signals aren't currently routed to MCU:
- Could use spare GPIO on main board
- May need to modify sensor board design
- Alternatively: Use "polled interrupt" approach (read INT_Flag via I2C)

---

## Firmware Implementation Plan

### New Library: Enhanced VCNL4040 Driver

Extend our existing `VCNL4040.h/cpp` to support full configuration:

```cpp
class VCNL4040 {
public:
    // Existing
    bool begin();
    uint16_t readProximity();
    uint16_t readAmbientLight();
    
    // NEW: Interrupt Configuration
    void setProxHighThreshold(uint16_t threshold);
    void setProxLowThreshold(uint16_t threshold);
    void setProxInterruptType(uint8_t type);  // DISABLE, CLOSE, AWAY, BOTH
    void setProxPersistence(uint8_t hits);    // 1-4 hits required
    void enableSmartPersistence(bool enable);
    void enableProxLogicMode(bool enable);
    
    // NEW: Interrupt Status
    uint8_t readInterruptFlags();  // Also clears flags
    bool isClose();    // PS above high threshold
    bool isAway();     // PS below low threshold
    
    // NEW: ALS Interrupt (if needed)
    void setALSHighThreshold(uint16_t threshold);
    void setALSLowThreshold(uint16_t threshold);
    void enableALSInterrupt(bool enable);
};
```

### New Component: InterruptDetector

```cpp
struct InterruptEvent {
    uint32_t timestamp_ms;
    uint8_t sensor_index;      // 0-7 for our 8 sensors
    uint8_t side;              // 1 = Side A, 2 = Side B
    bool is_close;             // true = CLOSE, false = AWAY
};

class InterruptDetector {
public:
    InterruptDetector();
    
    // Configuration
    void setThreshold(uint16_t high, uint16_t low);
    void setPersistence(uint8_t hits);
    void calibrate();  // Auto-detect per-sensor offsets
    
    // Event handling
    void addEvent(const InterruptEvent& event);
    
    // Detection results
    bool hasDetection() const;
    DetectionResult getResult();
    
private:
    std::vector<InterruptEvent> closeEventsA;
    std::vector<InterruptEvent> closeEventsB;
    uint32_t detectionWindowStart;
    // ...
};
```

### Operating Modes

Modify `SessionManager` or create new mode handling:

| Mode | Detection Method | Data Collected |
|------|------------------|----------------|
| `debug` | Polling (current) | Full proximity waveforms |
| `play` | Polling (current) | Detections only |
| `interrupt_debug` | **NEW** Interrupt-based | Event timestamps |
| `interrupt_play` | **NEW** Interrupt-based | Detections only |

---

## Frontend Implementation Plan

### Settings Modal Additions

Add to the existing settings modal:

```tsx
// New section: Detection Mode
<div className="space-y-4">
    <h3 className="font-semibold">Detection Mode</h3>
    <div className="grid grid-cols-2 gap-2">
        <ModeButton 
            mode="proximity" 
            label="Proximity Polling"
            description="High-resolution waveforms"
            selected={detectionMode === 'proximity'}
        />
        <ModeButton 
            mode="interrupt" 
            label="Interrupt Mode"
            description="Event-based detection"
            selected={detectionMode === 'interrupt'}
        />
    </div>
    
    {/* Interrupt-specific settings */}
    {detectionMode === 'interrupt' && (
        <InterruptSettings
            highThreshold={config.int_high_threshold}
            lowThreshold={config.int_low_threshold}
            persistence={config.int_persistence}
            onChange={handleInterruptConfigChange}
        />
    )}
</div>
```

### Session List: New Card Type

Sessions collected in interrupt mode need different visualization:

```tsx
// Detect session type from data
const isInterruptSession = session.metadata?.detection_mode === 'interrupt';

// Render appropriate card
{isInterruptSession ? (
    <InterruptSessionCard session={session} onClick={onSelect} />
) : (
    <SessionCard session={session} onClick={onSelect} />
)}
```

### Interrupt Session Visualization

Instead of waveform chart, show:

1. **Event Timeline**: Horizontal timeline showing CLOSE/AWAY events
2. **Side Comparison**: Visual showing which side triggered first
3. **Detection Result**: Direction arrow with confidence and timing gap

```
┌────────────────────────────────────────────────┐
│  Interrupt Session: 2025-01-15 14:32           │
├────────────────────────────────────────────────┤
│                                                │
│  Side A: ────●━━━━━━━●────────────            │
│              ↑close  ↑away                     │
│              0ms     45ms                      │
│                                                │
│  Side B: ──────────●━━━━━━━●──────            │
│                    ↑close  ↑away               │
│                    12ms    58ms                │
│                                                │
│  ───────────────────────────────              │
│                                                │
│    Direction: A → B                           │
│    Confidence: 92%                            │
│    Time Gap: 12ms                             │
│                                                │
└────────────────────────────────────────────────┘
```

### Data Model Changes

```typescript
// New session data type for interrupt mode
interface InterruptSessionData {
    type: 'interrupt';
    events: InterruptEvent[];
    detections: InterruptDetection[];
}

interface InterruptEvent {
    timestamp_ms: number;
    sensor_index: number;
    side: 1 | 2;
    event_type: 'close' | 'away';
}

interface InterruptDetection {
    timestamp_ms: number;
    direction: 'A_TO_B' | 'B_TO_A' | 'UNKNOWN';
    confidence: number;
    side_a_first_close_ms: number;
    side_b_first_close_ms: number;
    time_gap_ms: number;
}
```

---

## Implementation Phases

### Phase 1: Library Enhancement (1 week)
- [ ] Extend `VCNL4040` class with interrupt configuration methods
- [ ] Add register constants for all interrupt-related registers
- [ ] Implement `readInterruptFlags()` and flag-checking methods
- [ ] Test basic interrupt triggering with single sensor
- [ ] Document register bit mappings

### Phase 2: Hardware Verification (3 days)
- [ ] Trace INT signals from sensor board to MCU
- [ ] Verify GPIO pin availability on ESP32
- [ ] Test hardware interrupt triggering with oscilloscope
- [ ] Determine if polled-INT approach is needed

### Phase 3: Interrupt Detection Algorithm (1 week)
- [ ] Implement `InterruptDetector` class
- [ ] Create event collection and windowing logic
- [ ] Implement first-hit direction algorithm
- [ ] Add confidence calculation
- [ ] Test with controlled object passes

### Phase 4: Firmware Integration (3 days)
- [ ] Add `interrupt_debug` and `interrupt_play` modes
- [ ] Create MQTT message format for interrupt events
- [ ] Integrate with session management
- [ ] Add configuration command for threshold/persistence

### Phase 5: Frontend Updates (1 week)
- [ ] Add detection mode toggle to settings modal
- [ ] Add interrupt-specific configuration UI
- [ ] Create `InterruptSessionCard` component
- [ ] Create `InterruptTimeline` visualization component
- [ ] Update API service for new data types

### Phase 6: Testing & Comparison (1 week)
- [ ] Collect parallel sessions (same passes, both modes)
- [ ] Compare detection accuracy
- [ ] Measure power consumption differences
- [ ] Document trade-offs and recommendations

---

## Key Questions for Discussion

### 1. Hardware INT Routing
**Question**: Are INT lines currently routed to ESP32 GPIOs, or only combined/unused?

**Impact**: Determines if we need hardware mods or can use polled approach.

### 2. Per-Sensor vs Combined INT
**Question**: Should we try to get individual sensor INTs, or use combined?

**Options**:
- **Combined**: Simpler wiring, but can't tell which sensor without I2C read
- **Individual**: More GPIOs needed, but instant sensor identification

**Recommendation**: Start with polled approach (read INT_Flag via I2C) which works regardless.

### 3. Threshold Calibration Strategy
**Question**: How do we set thresholds given sensor-to-sensor variation?

**Options**:
- **Fixed threshold**: Same value for all sensors (simple, may miss low-signal sensors)
- **Per-sensor calibrated**: Individual thresholds based on baseline (better accuracy)
- **Dynamic**: Auto-adjust based on recent readings (most complex)

**Recommendation**: Start with per-sensor calibration during init.

### 4. Hybrid Mode Interest
**Question**: Do we want a wake-on-interrupt + burst-poll hybrid mode?

**Trade-off**: More complex, but gives detailed waveforms with lower idle power.

### 5. Session Data Storage
**Question**: How to store interrupt events in existing session infrastructure?

**Options**:
- **Same table, different format**: Add `session_type` column, different JSON structure
- **Separate table**: New `interrupt_sessions` table with event records
- **Unified events**: Convert to same format as polling (synthesized waveforms)

---

## Reference Materials

### From Datasheet
- Interrupt section: Lines 923-982 of `vcnl4040_datasheet_text.txt`
- Register definitions: Tables 6-13
- Application example with thresholds: Lines 873-1064

### From SparkFun Library
Key functions for reference:
- `setProxInterruptType()` - Enable/disable interrupt modes
- `setProxHighThreshold()` / `setProxLowThreshold()` - Threshold configuration
- `enableSmartPersistance()` - Fast response mode
- `enableProxLogicMode()` - Alternative binary output mode
- `isClose()` / `isAway()` - Flag checking

### From Toit Library
Alternative reference implementation:
- `set-ps-interrupt-trigger` - Trigger mode configuration
- `read-ps-interrupt-trigger` - Read current mode
- `reset-interrupt` - Clear flags
- `last-interrupt-was-ps-close` / `last-interrupt-was-ps-away` - Event checking

---

## Next Steps

1. **Verify hardware INT routing** - Check schematics/PCB for INT trace to ESP32
2. **Decide on approach** - Polled INT vs hardware interrupt
3. **Implement Phase 1** - Library enhancement (no UI changes yet)
4. **Test basic operation** - Verify interrupt triggering with single sensor
5. **Proceed to detection algorithm** - Only after basics work

---

*Created: December 13, 2025*
*Status: Research & Planning Complete, Ready for Implementation*



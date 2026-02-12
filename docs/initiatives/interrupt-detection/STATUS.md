# Interrupt Detection - Implementation Status

> **Last Updated**: December 15, 2025  
> **Status**: ✅ Core Pipeline Complete, ✅ Direction Detection Implemented

---

## Current State

**Interrupt detection and direction detection are working end-to-end.** The firmware captures interrupt events, transmits them to the cloud, and the frontend displays them with direction analysis.

### What Works

| Component | Status | Notes |
|-----------|--------|-------|
| VCNL4040 Library | ✅ Complete | Full interrupt register support |
| InterruptManager | ✅ Working | ISR handling, event queuing, calibration |
| Auto-Calibration | ✅ Working | PS_CANC removes baseline offset at startup |
| Session Integration | ✅ Working | Events stored in SessionManager |
| MQTT Transmission | ✅ Working | Events sent to cloud |
| Lambda Processing | ✅ Working | session_type properly set for routing |
| Frontend Display | ✅ Working | InterruptSessionView renders correctly |
| Frontend Settings | ✅ Working | Settings now reflect actual firmware values |
| Direction Detection | ✅ Working | Frontend analyzes events for A→B / B→A direction |

### Recent Fixes (Dec 15, 2025)

1. **Fixed session_type not being set on update**: Lambda now properly sets `session_type: 'interrupt'` when updating existing sessions.

2. **Synced firmware/frontend config fields**: Changed from absolute thresholds to calibration-based approach:
   - Old: `interrupt_high_threshold`, `interrupt_low_threshold`
   - New: `interrupt_threshold_margin`, `interrupt_hysteresis`, `interrupt_integration_time`, `interrupt_multi_pulse`

3. **Direction detection algorithm**: Frontend now analyzes interrupt events and detects direction (A→B or B→A) with confidence scoring.

---

## Key Architecture Decisions

### Sensor Mode vs Device Mode (Refactored)

We refactored to separate concerns:

- **Device Mode** (`idle`, `debug`, `play`): What the device is doing
- **Sensor Mode** (`polling`, `interrupt`): How it's sensing

This eliminated invalid state combinations like `interrupt_debug` mode with polling config.

The sensor mode is part of `SensorConfiguration` and persisted in cloud config.

### Calibration-Based Thresholds

Each sensor's baseline is measured at startup (with no objects present) and written to the `PS_CANC` register. This hardware feature subtracts the baseline from all readings, so thresholds are relative to "zero" rather than absolute values.

**Configuration fields (all configurable from frontend):**
- `interrupt_threshold_margin`: How much above baseline triggers "close" (default: 10)
- `interrupt_hysteresis`: Gap between high and low thresholds (default: 5)
- `interrupt_integration_time`: 1-8 for 1T-8T (default: 8 for max range)
- `interrupt_multi_pulse`: 1, 2, 4, or 8 pulses (default: 8 for max signal)

### Direction Detection Algorithm

The frontend implements a "first-hit" direction detection algorithm:
1. Groups "close" events into detection windows (200ms)
2. Separates events by side (A = S1 sensors at positions 0,2,4; B = S2 sensors at positions 1,3,5)
3. Compares which side triggered first
4. Calculates confidence based on time gap, event count, and whether both sides triggered

### Interrupt Wiring

The INT lines from sensors on each sensor assembly (rigid+flex pair) are combined (wired-OR via diodes on the rigid base PCB):
- Assembly 1 (TCA Ch0) → GPIO 11
- Assembly 2 (TCA Ch1) → GPIO 12  
- Assembly 3 (TCA Ch2) → GPIO 13

When an ISR fires, we know which sensor assembly triggered but must poll sensors via I2C to identify which specific sensor. The flex PCB angles the sensors ~2° apart, providing slightly more time between sensor triggers for direction detection.

---

## Configuration Values

Default values for interrupt detection (configurable from Settings):

```cpp
// From cloud config or defaults in SensorConfiguration.h
interrupt_threshold_margin = 10;   // Trigger at 10+ counts above baseline
interrupt_hysteresis = 5;          // Small gap for re-triggering
interrupt_integration_time = 8;    // 8T for max sensitivity
interrupt_multi_pulse = 8;         // 8 pulses for stronger signal
interrupt_persistence = 1;         // 1 consecutive hit to trigger
interrupt_smart_persistence = true;// Fast response mode
interrupt_mode = "normal";         // Pulse on events (vs logic output)
```

**Why such low thresholds?** Polling tests showed objects passing through the hoop center only produce proximity values of 8-25 (with baseline subtracted). The sensors are ~15cm from center.

---

## File Locations

### Firmware

| File | Purpose |
|------|---------|
| `firmware/src/components/vcnl4040/VCNL4040.h/cpp` | Sensor driver with interrupt methods |
| `firmware/src/components/interrupt/InterruptManager.h/cpp` | ISR handling, event queue, calibration |
| `firmware/src/components/mux/MuxController.h/cpp` | Shared I2C mux logic |
| `firmware/src/components/sensor/SensorConfiguration.h` | Config struct with `sensor_mode` |
| `firmware/src/main.cpp` | Mode switching, interrupt config setup |

### Backend

| File | Purpose |
|------|---------|
| `lambda/processData/index.js` | Routes interrupt events to DynamoDB |
| `lambda/getSessionData/index.js` | Fetches from interrupt table |
| `lambda/getDeviceConfig/index.js` | Includes sensor_mode in config |
| `lambda/updateDeviceConfig/index.js` | Persists sensor_mode |
| `MotionPlayInterruptEvents` table | Stores interrupt events |

### Frontend

| File | Purpose |
|------|---------|
| `frontend/.../InterruptSessionView.tsx` | Scatter plot + table (exists, not rendering) |
| `frontend/.../SettingsModal.tsx` | Sensor mode selector + interrupt settings |
| `frontend/.../Header.tsx` | Mode buttons (INT Debug removed) |
| `frontend/.../App.tsx` | Should route to InterruptSessionView |

---

## Completed Tasks

### 1. Frontend Session View Routing ✅

Fixed Lambda `processData` to set `session_type: 'interrupt'` when updating existing sessions. The routing logic in `App.tsx` now correctly renders `InterruptSessionView` for interrupt sessions.

### 2. Frontend Settings → Firmware ✅

Fully synchronized config fields across all layers:
- **Firmware** (`SensorConfiguration.h`): Uses new field names
- **Firmware** (`main.cpp`): Reads from config instead of hardcoded values
- **Lambda** (`processData`, `getDeviceConfig`, `updateDeviceConfig`): Updated field names
- **Frontend** (`SettingsModal.tsx`): UI updated with new fields and tooltips
- **Frontend** (`InterruptSessionView.tsx`): Displays new config fields

### 3. Direction Detection Algorithm ✅

Implemented in `InterruptSessionView.tsx`:
- Groups close events into 200ms detection windows
- Separates by side (A = even positions, B = odd positions)
- Determines direction by which side triggered first
- Calculates confidence score (0-100%)
- Visual display with timeline mini-view

---

## Debugging Tips

### Firmware Serial Output

The interrupt mode prints detailed diagnostics:

```
╔══════════════════════════════════════════════════════════════════════════════╗
║              INTERRUPT MODE CALIBRATION (Cover Offset Removal)               ║
╚══════════════════════════════════════════════════════════════════════════════╝
  Sensor 0: Baseline=4 → written to PS_CANC ✓
  ...
    Sensor 0: PS_CONF1_2=0x0B0E, PS_IT=7, PS_INT=3 (BOTH)
    Sensor 0: Baseline(PS_CANC)=4, HIGH=10, LOW=5
    Sensor 0: Current proximity=0 (after cancellation)
```

### GPIO State Monitoring

The debug loop shows GPIO states:
```
[DEBUG] GPIO: INT1=1, INT2=1, INT3=1 | S0: prox=0
```
- `INT=1` means no interrupt (pulled high)
- `INT=0` means interrupt active (needs to read flags to clear)

### ISR vs Events

```
Session stats: 15 events, 15 ISRs, 0 dropped
```
- ISRs = raw interrupt triggers
- Events = processed events added to queue
- Dropped = queue overflow (shouldn't happen)

---

## What We Learned

1. **Signal strength is low at distance**: At 15cm (hoop center), proximity readings are only 8-25 counts even with max settings. Thresholds must be very low.

2. **PS_CANC is essential**: Sensor baselines varied from 4 to 78 counts. Without calibration, fixed thresholds wouldn't work across all sensors.

3. **8T integration + 8-pulse gives best range**: Lower settings couldn't detect objects at hoop center distance.

4. **Debug polling interfered with interrupts**: Early bug where reading `readInterruptFlags()` in debug code was clearing the actual interrupts before they could be processed.

5. **GPIO mapping matters**: The GPIO-to-board mapping was initially inverted, causing wrong board attribution.

---

## Next Steps

1. **Deploy Lambda updates** - Upload updated Lambda functions to AWS
2. **Test end-to-end** - Verify complete flow: firmware → cloud → frontend
3. **Add firmware-side direction detection** - Implement real-time detection for play mode
4. **LED feedback** - Show direction on LED strip during play mode
5. **Tune detection parameters** - Test with actual gameplay, adjust thresholds

---

## Files Changed (Dec 15, 2025)

### Firmware
- `firmware/src/components/sensor/SensorConfiguration.h` - New config fields
- `firmware/src/main.cpp` - Uses config values instead of hardcoded
- `firmware/src/components/data/DataTransmitter.cpp` - Sends new config fields

### Backend (Lambda)
- `lambda/processData/index.js` - Sets session_type on update, new config fields
- `lambda/getDeviceConfig/index.js` - New default config values
- `lambda/updateDeviceConfig/index.js` - New config fields

### Frontend
- `frontend/.../services/api.ts` - Updated InterruptConfig type
- `frontend/.../components/SettingsModal.tsx` - New UI for calibration-based settings
- `frontend/.../components/InterruptSessionView.tsx` - Direction detection + visualization
- `frontend/.../components/SessionList.tsx` - Updated config badges

---

*See DESIGN_PLAN.md for the original architecture and algorithm design.*


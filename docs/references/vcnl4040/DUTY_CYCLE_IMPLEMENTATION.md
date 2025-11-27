# Duty Cycle Implementation Summary
## Adding Sample Rate Control to Motion Play

**Date:** November 26, 2025  
**Status:** ✅ Implementation Complete

---

## Problem Statement

The Motion Play system was not achieving the expected sample rates despite optimizations in the firmware reading loop. Investigation revealed:

1. **Integration Time** was conflated with **Sample Rate** in the UI
2. **Duty Cycle** setting (which controls actual sensor measurement frequency) was not exposed
3. Sensors were likely defaulting to 1/160 duty cycle (~50 Hz) regardless of firmware loop speed

---

## Key Insight: Two Independent Controls

### What We Learned

The VCNL4040 has TWO separate settings that control different aspects:

| Setting | What It Controls | Effect |
|---------|-----------------|--------|
| **Integration Time (PS_IT)** | IR pulse length | Signal strength, range, SNR |
| **Duty Cycle (PS_Duty)** | Measurement frequency | Sample rate, battery life |

**They are independent!** You can have:
- 8T integration with 1/40 duty for strong signal at ~200 Hz
- 1T integration with 1/320 duty for weak signal at ~25 Hz
- Any combination

---

## Changes Made

### 1. Firmware Updates

**File:** `firmware/src/components/sensor/SensorConfiguration.h`
- Added `duty_cycle` field with default "1/40"

**File:** `firmware/src/components/sensor/SensorManager.h`
- Added `parseDutyCycle()` function declaration

**File:** `firmware/src/components/sensor/SensorManager.cpp`
- Implemented `parseDutyCycle()` to parse duty cycle strings
- Updated `applySensorConfig()` to apply duty cycle setting
- Added duty cycle to configuration logging

### 2. Frontend Updates

**File:** `frontend/motion-play-ui/src/services/api.ts`
- Added `duty_cycle: string` to `VCNL4040Config` interface
- Updated `configureSensors()` method signature

**File:** `frontend/motion-play-ui/src/components/SettingsModal.tsx`
- Added `duty_cycle` to `SensorConfig` interface
- Updated `DEFAULT_CONFIG` with `duty_cycle: '1/40'` and `integration_time: '2T'`
- Added duty cycle dropdown with options: 1/40, 1/80, 1/160, 1/320
- Fixed integration time description: "Longer pulse = stronger signal, better range & SNR"
- Added duty cycle description: "Controls measurement frequency"

**File:** `frontend/motion-play-ui/src/components/SensorConfig.tsx`
- Added duty cycle state and dropdown
- Updated integration time description
- Changed default integration time to `2T` (recommended)

**File:** `frontend/motion-play-ui/src/components/SessionConfig.tsx`
- Added duty cycle display in session configuration view
- Updated integration time label to clarify it's pulse length

### 3. Documentation

**New File:** `docs/references/vcnl4040/CONFIGURATION_GUIDE.md`
- Comprehensive guide to VCNL4040 settings
- Explains integration time vs duty cycle
- Provides configuration strategies
- Includes testing recommendations

---

## Recommended Configuration for Motion Play

Based on your goals (fast sample rate + good detection):

```
Integration Time: 2T or 4T
  └─ 2-4× stronger signal than 1T
  └─ Still fast pulse (250-500 μs)

Duty Cycle: 1/40
  └─ ~200 Hz measurement frequency
  └─ Fastest possible sample rate

LED Current: 200mA
  └─ Maximum detection range

High Resolution: true
  └─ 16-bit for better signal quality
```

**Expected Result:** ~200 Hz actual sensor measurements with strong detection signal

---

## Why This Matters

### Before (Your Current State)
```
Firmware loop: Reading as fast as possible (~1000 Hz loop)
Sensor duty: Unknown, likely 1/160 default (~50 Hz actual measurements)
Result: Reading the SAME value multiple times!
```

### After (With Duty Cycle = 1/40)
```
Firmware loop: Reading as fast as possible (~1000 Hz loop)
Sensor duty: 1/40 configured (~200 Hz NEW measurements)
Result: Each read gets a fresh measurement!
```

### Your Modified Library
You reduced the I2C delay from 10ms to 0.5ms:
```cpp
delayMicroseconds(500); // vs delay(10)
```

This was GOOD but only helped I2C speed. Now with duty cycle control:
- I2C read: ~0.5ms (your optimization)
- Sensor measurement: Every 5ms (duty cycle 1/40)
- You can read all 6 sensors (3ms total) within one duty cycle period!

---

## Testing Strategy

### Phase 1: Baseline Test (Current Config)
```
Integration: 1T
Duty: 1/160 (likely current default)
LED: 200mA
Expected: ~50 Hz effective, moderate signal
```

### Phase 2: Speed Test
```
Integration: 1T
Duty: 1/40
LED: 200mA
Expected: ~200 Hz, moderate signal
```

### Phase 3: Balanced Test (RECOMMENDED)
```
Integration: 2T
Duty: 1/40
LED: 200mA
Expected: ~200 Hz, strong signal ⭐
```

### Phase 4: Power Test
```
Integration: 4T
Duty: 1/40
LED: 200mA
Expected: ~200 Hz, very strong signal
```

### Measurements to Track
1. **Actual Sample Rate** - readings per second in firmware
2. **Detection Strength** - proximity counts for passing object
3. **Detection Consistency** - how reliably objects are detected
4. **False Positives** - detections when nothing passes

---

## How to Deploy

### 1. Update Cloud Configuration
1. Open frontend (http://localhost:5173)
2. Click Settings modal
3. Set:
   - Integration Time: 2T
   - Duty Cycle: 1/40
   - LED Current: 200mA
   - High Resolution: Enabled
4. Click "Apply Configuration"
5. Configuration saved to cloud and sent to device via MQTT

### 2. Verify on Device
1. Check serial monitor for:
   ```
   Applied config: LED=200mA, Integration=2T, Duty=1/40, HighRes=true
   PS_Duty setting: 0 (1/40 -> ~200 Hz max) FAST
   ```

### 3. Test Data Collection
1. Start a data collection session
2. Monitor actual sample rate in firmware
3. Pass object through hoop
4. Check detection strength in frontend charts

---

## Additional Notes

### Why 2T is Recommended (Not 1T)
- 1T gives moderate signal strength
- 2T doubles the signal strength
- Still maintains ~200 Hz with 1/40 duty
- Better SNR for reliable detection
- 4T or 8T may be overkill for your use case

### Power Consumption
With 200mA LED at 1/40 duty:
```
Average current = 200mA / 40 = 5.0 mA per sensor
For 6 sensors = 30 mA total
```
This is fine for USB-powered operation.

### I2C Timing
At 400 kHz I2C with your 0.5ms delay:
```
Read 6 sensors: 6 × 0.5ms = 3ms
Duty cycle period: 5ms (1/40)
Margin: 2ms (plenty of headroom!)
```

---

## Troubleshooting

### If Sample Rate Doesn't Improve
1. Check that duty cycle is actually being applied (serial monitor)
2. Verify sensor is reinitialized after config change
3. Check that firmware is using the new configuration structure

### If Detection Gets Worse
1. Increase integration time (2T → 4T)
2. Verify LED current is still 200mA
3. Check that high resolution mode is enabled

### If You See I2C Errors
1. Reduce duty cycle (1/40 → 1/80)
2. Increase I2C delay slightly if needed
3. Check I2C clock speed (should be 400 kHz)

---

## Backend Changes Required

The backend Lambda functions that store/retrieve configuration will automatically handle the new `duty_cycle` field since DynamoDB is schemaless. However, you should:

1. **Check Lambda function** `processData` to ensure it stores `duty_cycle` in session metadata
2. **Check Lambda function** `getSessionData` to ensure it returns `duty_cycle` in config
3. **Update database schema docs** to document the new field

The field is optional for backward compatibility - old sessions without `duty_cycle` will still work.

---

## Summary

✅ Firmware now supports duty cycle configuration  
✅ Frontend exposes duty cycle in settings  
✅ Integration time descriptions corrected  
✅ Recommended configuration: 2T + 1/40 duty + 200mA  
✅ Documentation created  
🔄 Ready for testing!

**Next Steps:**
1. Deploy updated firmware to device
2. Update configuration via frontend
3. Run test collection sessions
4. Compare before/after detection performance
5. Iterate on integration time if needed

---

*See also: `CONFIGURATION_GUIDE.md` for detailed technical explanation*


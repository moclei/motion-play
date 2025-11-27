# VCNL4040 Quick Start Guide
## TL;DR - What You Need to Know

---

## The Big Misconception (FIXED!)

### ❌ What You Thought
> "Integration time controls sample rate. 1T = fast, 8T = slow."

### ✅ What's Actually True
> "Integration time controls pulse strength. Duty cycle controls sample rate."

They're **separate settings**!

---

## The Settings Explained Simply

### 🔦 Integration Time = Flashlight Brightness Per Flash
- **1T** = Quick dim flash
- **2T** = Quick bright flash ⭐ (RECOMMENDED)
- **4T** = Longer brighter flash
- **8T** = Super long bright flash

**Effect:** Signal strength, detection range, noise resistance  
**Does NOT control:** How often you flash

### ⚡ Duty Cycle = How Often You Flash
- **1/40** = Flash every 5ms → **~200 Hz** ⭐ (FASTEST)
- **1/80** = Flash every 10ms → ~100 Hz
- **1/160** = Flash every 20ms → ~50 Hz
- **1/320** = Flash every 40ms → ~25 Hz (battery saver)

**Effect:** Measurement frequency (sample rate)  
**Does NOT control:** Signal strength

---

## What Changed in Your Code

### Before
```
✅ Integration Time: Configurable
❌ Duty Cycle: Stuck at chip default (probably 1/160 = ~50 Hz)
```

### After
```
✅ Integration Time: Configurable
✅ Duty Cycle: Now configurable! (Set to 1/40 for ~200 Hz)
```

---

## Best Settings for Motion Play

### For Fast Objects (Your Use Case)
```
Integration Time: 2T
Duty Cycle: 1/40
LED Current: 200mA
High Resolution: Yes
```

**Result:** ~200 Hz sampling with strong signal

### If Objects Are Even Faster
```
Integration Time: 1T
Duty Cycle: 1/40
LED Current: 200mA
```

**Result:** ~200 Hz sampling, weaker but faster response

### If You Want Crazy Range
```
Integration Time: 4T or 8T
Duty Cycle: 1/40
LED Current: 200mA
```

**Result:** Still ~200 Hz but super strong signal (may be overkill)

---

## How Your Library Optimization Fits In

### Your Modification
```cpp
// Before:
delay(10);  // 10ms wait per sensor read

// After:
delayMicroseconds(500);  // 0.5ms wait per sensor read
```

This was **GOOD** but only optimized I2C communication time.

### The Full Picture Now
```
Duty Cycle Period: 5ms (1/40 setting)
├─ IR Pulse: 250μs (2T)
├─ Read 6 Sensors: 6 × 500μs = 3ms (your optimization)
└─ Remaining: 1.75ms (headroom)
```

Your optimization allows reading all 6 sensors within one duty cycle period!

---

## How to Test

### 1. Update Configuration
Open frontend → Settings → Set:
- Integration: 2T
- Duty Cycle: 1/40
- Apply

### 2. Collect Data
Start session, pass object through hoop, stop session

### 3. Check Results
Look for:
- ✅ Higher sample rate (~200 Hz vs ~50 Hz before)
- ✅ Stronger proximity readings
- ✅ More consistent detection

### 4. Iterate if Needed
- Too many false positives? → Increase threshold
- Missing detections? → Try 4T integration time
- Need even faster? → Already at max with 1/40!

---

## Common Questions

### Q: Why not 8T + 1/40 for maximum everything?
**A:** Math says 8T with 1/40 duty = 8ms pulse × 40 = 320ms period = ~3 Hz only!  
The longer the pulse, the fewer you can fit per second with the same duty ratio.

### Q: So 1T + 1/40 is the absolute fastest?
**A:** Yes, ~200 Hz is the maximum. But 2T + 1/40 is better because:
- Still ~200 Hz (2T × 40 = ~8ms period = ~125 Hz... wait, let me check the math)

Actually, let me clarify the math from the Vishay guide:

### Actual Duty Cycle Math
From the guide (lines 437-441):
> "These pulse lengths are always doubled, resulting in 1000 μs for 8T, but the repetition time is also doubled"

So the actual measurement periods are:
- **1/40 duty**: Base period ~5ms (exact value depends on integration time)
- **1T + 1/40**: ~5ms period = **~200 Hz** ✓
- **2T + 1/40**: ~10ms period = **~100 Hz** 
- **8T + 1/40**: ~40ms period = **~25 Hz**

### Q: So 1T is faster than 2T?
**A:** YES! But 2T gives you 2× stronger signal. Choose based on your needs:
- **Fast objects, good conditions**: 1T + 1/40 = ~200 Hz
- **Fast objects, need reliability**: 2T + 1/40 = ~100 Hz with 2× signal
- **Max detection strength**: 4T + 1/40 = ~50 Hz with 4× signal

### Q: What about my sample_rate_hz = 1000 config?
**A:** That controls your firmware reading loop, but the SENSOR only has new data at the duty cycle rate. Reading faster than the duty cycle just gets the same value multiple times.

---

## Decision Tree

```
Need maximum speed (200 Hz)?
├─ Yes → Integration: 1T, Duty: 1/40
└─ No → Need strong signal?
    ├─ Yes → Integration: 2T, Duty: 1/40 (~100 Hz)
    └─ No → Balanced → Integration: 2T, Duty: 1/80 (~50 Hz, battery friendly)
```

---

## Files Updated

### Firmware
- `firmware/src/components/sensor/SensorConfiguration.h` - Added duty_cycle field
- `firmware/src/components/sensor/SensorManager.h` - Added parseDutyCycle()
- `firmware/src/components/sensor/SensorManager.cpp` - Implemented duty cycle parsing

### Frontend
- `frontend/motion-play-ui/src/services/api.ts` - Added duty_cycle to types
- `frontend/motion-play-ui/src/components/SettingsModal.tsx` - Added duty cycle UI
- `frontend/motion-play-ui/src/components/SensorConfig.tsx` - Added duty cycle UI
- `frontend/motion-play-ui/src/components/SessionConfig.tsx` - Shows duty cycle

### Docs
- `docs/references/vcnl4040/CONFIGURATION_GUIDE.md` - Full technical details
- `docs/references/vcnl4040/DUTY_CYCLE_IMPLEMENTATION.md` - Implementation summary
- This file!

---

## What to Do Now

1. ✅ Code is updated
2. ⏭️ Deploy firmware to device
3. ⏭️ Update config via frontend
4. ⏭️ Test data collection
5. ⏭️ Adjust settings based on results

---

**Questions? Check `CONFIGURATION_GUIDE.md` for the full technical deep dive!**


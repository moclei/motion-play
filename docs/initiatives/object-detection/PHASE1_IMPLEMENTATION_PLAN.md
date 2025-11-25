# Phase 1 Implementation Plan - Sample Rate Optimization

**Goal**: Increase sample rate from 24 Hz to 150-200 Hz through firmware optimizations and configurable settings.

**Status**: In Progress  
**Target Completion**: Week 1  
**Dependencies**: None

## Problem Summary

Current system achieves only 24 Hz (41ms per cycle) vs. target 1000 Hz (1ms per cycle). Analysis reveals:
- Expected theoretical cycle time: 480μs (4 sensors × 120μs)
- Observed cycle time: 41ms
- **Performance gap**: 85x slower than theoretical maximum

## Root Causes

1. **Ambient light reads**: Doubling I2C transaction count (proximity + ambient per sensor)
2. **High resolution mode**: 16-bit reads slower than necessary for detection
3. **Conservative I2C clock**: 400kHz vs. possible 1MHz
4. **Configuration not applied**: Settings stored but never used

## Optimization Strategy

### Optimization 1: Remove Ambient Light Reads
**Expected Gain**: 2x faster (50% time reduction)  
**Impact**: 41ms → ~20ms per cycle (24 Hz → ~50 Hz)

**Rationale**: Ambient light not needed for object detection, only proximity matters.

### Optimization 2: Disable High Resolution Mode
**Expected Gain**: 20-30% faster  
**Impact**: ~20ms → ~15ms per cycle (~50 Hz → ~67 Hz)

**Rationale**: 12-bit resolution sufficient for threshold-based detection (>10 vs <10).

### Optimization 3: Increase I2C Clock Speed
**Expected Gain**: 2.5x faster  
**Impact**: ~15ms → ~6ms per cycle (~67 Hz → ~167 Hz)

**Rationale**: Hardware supports Fast Mode Plus (1MHz) vs. current Fast Mode (400kHz).

### Combined Expected Result
**Target**: 150-200 Hz (5-7ms per cycle)  
**Sufficient for**: 10+ samples during medium speed (15 mph, 53ms transit)

## Implementation Components

### 1. Firmware Changes

#### A. Configuration Structure Enhancement
**File**: `firmware/src/components/sensor/SensorConfiguration.h`

Add new field:
```cpp
struct SensorConfiguration {
    int sample_rate_hz = 1000;
    String led_current = "200mA";
    String integration_time = "1T";
    bool high_resolution = true;
    bool read_ambient = true;  // NEW
};
```

#### B. Configuration Parser
**File**: `firmware/src/components/sensor/SensorManager.h` and `.cpp`

New helper functions:
- `VCNL4040_LEDCurrent parseLEDCurrent(String current)`
- `VCNL4040_ProximityIntegration parseIntegrationTime(String time)`
- `bool applySensorConfiguration(const SensorConfiguration& config)`

#### C. Apply Configuration to Sensors
**File**: `firmware/src/components/sensor/SensorManager.cpp`

Modify `init()` to:
- Accept configuration parameter
- Apply settings during sensor initialization
- Use configuration values instead of hardcoded constants

#### D. Conditional Ambient Reading
**File**: `firmware/src/components/sensor/SensorManager.cpp`

Modify `readSensor()` to:
- Check `config.read_ambient` flag
- Skip `getAmbientLight()` call when disabled
- Store 0 or -1 for ambient when not read

#### E. I2C Clock Configuration
**File**: `firmware/src/components/sensor/SensorManager.cpp`

Modify `init()` to:
- Accept I2C clock speed parameter
- Apply during `Wire.begin()` setup
- Default to 400kHz for safety

#### F. Configuration Application Command
**File**: `firmware/src/main.cpp`

Enhance `configure_sensors` handler to:
- Apply configuration immediately
- Reinitialize sensors with new settings
- Provide feedback on success/failure

### 2. Data Pipeline Changes

#### A. Session Metadata Enhancement
**File**: `firmware/src/components/data/DataTransmitter.cpp`

Add to transmitted metadata:
- `read_ambient` (boolean)
- `i2c_clock_khz` (integer)
- `actual_sample_rate_hz` (measured, integer)

#### B. Lambda Processing
**File**: `lambda/processData/index.js`

Ensure all configuration fields stored in DynamoDB session metadata.

### 3. Frontend Changes

#### A. Settings Modal Component
**File**: `frontend/motion-play-ui/src/components/SettingsModal.tsx`

Create new modal with form controls:
- LED Current dropdown (50mA-200mA)
- Integration Time dropdown (1T-8T)
- High Resolution checkbox
- Read Ambient Light checkbox
- I2C Clock Speed dropdown (400kHz, 1MHz)
- Apply button
- Reset to defaults button

#### B. Configuration Display
**File**: `frontend/motion-play-ui/src/App.tsx` or `Header.tsx`

Show current device configuration:
- Settings icon/button to open modal
- Indicator showing if custom configuration active

#### C. Session Details Enhancement
**File**: `frontend/motion-play-ui/src/components/SessionList.tsx`

Display configuration for each session:
- Show configuration badge/tooltip
- Allow filtering by configuration
- Highlight sessions with non-standard configs

#### D. API Client Updates
**File**: `frontend/motion-play-ui/src/services/api.ts`

Add function:
```typescript
configureSensors(deviceId: string, config: SensorConfig): Promise<void>
```

### 4. Testing & Validation

#### Test Cases

**TC1: No Ambient Light**
- Configuration: `read_ambient = false`
- Expected: ~50 Hz, ambient values = 0
- Validate: Detection quality unchanged

**TC2: Low Resolution**
- Configuration: `high_resolution = false`
- Expected: ~67 Hz
- Validate: Proximity values still distinguish >10 threshold

**TC3: Fast I2C**
- Configuration: `i2c_clock_khz = 1000`
- Expected: ~167 Hz
- Risk: May have stability issues
- Validate: No I2C errors, consistent readings

**TC4: All Optimizations**
- Configuration: All optimizations enabled
- Expected: 150-200 Hz
- Validate: Full detection test with ball passes

**TC5: Configuration Persistence**
- Apply config → restart device → verify config retained
- Apply config → start session → verify config in metadata

## Implementation Sequence

### Week 1, Day 1-2: Core Firmware
- [ ] Add `read_ambient` to SensorConfiguration
- [ ] Create configuration parser functions
- [ ] Modify SensorManager to accept and apply configuration
- [ ] Test: Verify configuration applied at initialization

### Week 1, Day 3: Conditional Reading
- [ ] Implement conditional ambient reading
- [ ] Test: Verify ambient = 0 when disabled
- [ ] Measure: Sample rate improvement

### Week 1, Day 4: I2C Optimization
- [ ] Add I2C clock configuration
- [ ] Test: Stability at 1MHz
- [ ] Measure: Sample rate improvement

### Week 1, Day 5-6: Frontend UI
- [ ] Create SettingsModal component
- [ ] Integrate with App
- [ ] Add API client function
- [ ] Test: Configuration roundtrip

### Week 1, Day 7: Integration Testing
- [ ] End-to-end configuration test
- [ ] Performance measurement
- [ ] Detection quality validation
- [ ] Documentation update

## Success Criteria

### Minimum Success (Must Have)
- ✓ Sample rate ≥ 100 Hz
- ✓ Configuration applied without errors
- ✓ UI allows configuration changes
- ✓ Configuration saved in session metadata

### Target Success (Should Have)
- ✓ Sample rate ≥ 150 Hz
- ✓ Detection quality maintained
- ✓ No I2C stability issues
- ✓ Configuration UI intuitive

### Stretch Success (Nice to Have)
- ✓ Sample rate ≥ 200 Hz
- ✓ Real-time sample rate display
- ✓ Configuration presets (fast/balanced/accurate)
- ✓ Automatic optimal configuration detection

## Risk Register

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| I2C instability at 1MHz | High | Medium | Make configurable, default to 400kHz |
| Detection quality loss | High | Low | Test each optimization independently |
| Configuration not persistent | Medium | Low | Save to EEPROM/preferences |
| UI complexity | Low | Medium | Start with simple form, iterate |

## File Change Summary

### New Files
- `frontend/motion-play-ui/src/components/SettingsModal.tsx`

### Modified Files
- `firmware/src/components/sensor/SensorConfiguration.h`
- `firmware/src/components/sensor/SensorManager.h`
- `firmware/src/components/sensor/SensorManager.cpp`
- `firmware/src/components/data/DataTransmitter.cpp`
- `firmware/src/main.cpp`
- `frontend/motion-play-ui/src/App.tsx`
- `frontend/motion-play-ui/src/components/Header.tsx` (or wherever settings button lives)
- `frontend/motion-play-ui/src/components/SessionList.tsx`
- `frontend/motion-play-ui/src/services/api.ts`
- `lambda/processData/index.js` (if needed)

## Configuration Options Reference

### LED Current Options
- `VCNL4040_LED_CURRENT_50MA` → "50mA"
- `VCNL4040_LED_CURRENT_75MA` → "75mA"
- `VCNL4040_LED_CURRENT_100MA` → "100mA"
- `VCNL4040_LED_CURRENT_120MA` → "120mA"
- `VCNL4040_LED_CURRENT_140MA` → "140mA"
- `VCNL4040_LED_CURRENT_160MA` → "160mA"
- `VCNL4040_LED_CURRENT_180MA` → "180mA"
- `VCNL4040_LED_CURRENT_200MA` → "200mA" (default/max)

### Integration Time Options
- `VCNL4040_PROXIMITY_INTEGRATION_TIME_1T` → "1T" (fastest)
- `VCNL4040_PROXIMITY_INTEGRATION_TIME_1_5T` → "1.5T"
- `VCNL4040_PROXIMITY_INTEGRATION_TIME_2T` → "2T"
- `VCNL4040_PROXIMITY_INTEGRATION_TIME_2_5T` → "2.5T"
- `VCNL4040_PROXIMITY_INTEGRATION_TIME_3T` → "3T"
- `VCNL4040_PROXIMITY_INTEGRATION_TIME_3_5T` → "3.5T"
- `VCNL4040_PROXIMITY_INTEGRATION_TIME_4T` → "4T"
- `VCNL4040_PROXIMITY_INTEGRATION_TIME_8T` → "8T" (slowest, best range/SNR)

### I2C Clock Options
- `400000` → 400kHz (Fast Mode - safe default)
- `1000000` → 1MHz (Fast Mode Plus - may not work on all hardware)

### Resolution Options
- `true` → 16-bit high resolution
- `false` → 12-bit low resolution (faster)

### Ambient Reading Options
- `true` → Read both proximity and ambient light
- `false` → Read only proximity (faster)

## Expected Performance Matrix

| Configuration | Sample Rate | Detection Range | Use Case |
|--------------|-------------|-----------------|----------|
| All Defaults | 24 Hz | 2-4" | Current baseline |
| No Ambient | ~50 Hz | 2-4" | Simple speed boost |
| + Low Res | ~67 Hz | 2-4" | Additional speed |
| + Fast I2C | **167 Hz** | 2-4" | **Target** |
| + 2T Integration | ~100 Hz | 4-6" | Balanced |
| + 4T Integration | ~50 Hz | 6-8" | Maximum range |

## Measurement Protocol

### Sample Rate Measurement
1. Start data collection session
2. Collect 10 seconds of data
3. Download CSV
4. Calculate average time between samples
5. Sample Rate = 1000ms / avg_interval_ms

### Detection Quality Measurement
1. Pass 4" ball through hoop at 15 mph
2. Repeat 10 times each direction
3. Count: Detected, Missed, Direction Correct, Direction Wrong
4. Detection Rate = Detected / Total
5. Direction Accuracy = Direction Correct / Detected

## Documentation Updates

After implementation:
- [ ] Update PROBLEM_STATEMENT.md with achieved sample rate
- [ ] Update CALCULATIONS.md with actual measurements
- [ ] Add configuration guide to README.md
- [ ] Document optimal configurations for different scenarios
- [ ] Update PROJECT_STATUS.md milestone

## Future Enhancements (Phase 2+)

1. **Configuration Presets**: One-click "Fast", "Balanced", "Accurate" modes
2. **Auto-Tune**: Device tests configurations and recommends optimal
3. **Live Sample Rate**: Display on device screen or frontend
4. **Configuration History**: Track which configs were tested
5. **A/B Testing**: Compare detection quality across configurations
6. **Interrupt Mode**: Use VCNL4040 interrupt pins for event-driven sampling

---

**Version**: 1.0  
**Created**: November 21, 2024  
**Author**: Marco + AI Assistant  
**Status**: Ready for Implementation


# Testing Checklist - Crash Fixes

## Pre-Upload

- [ ] Review changes in `SensorManager.cpp`
- [ ] Review changes in `SessionManager.h`
- [ ] Review changes in `main.cpp`
- [ ] Verify new files exist:
  - [ ] `PSRAMAllocator.h`
  - [ ] `MemoryMonitor.h`

## Upload & Boot

```bash
cd /Users/marcocleirigh/Workspace/motion-play
pio run --target upload
pio device monitor
```

- [ ] Device boots successfully
- [ ] See "Core 0 watchdog disabled for sensor task"
- [ ] See memory statistics after boot
- [ ] Memory health shows "✓ Heap memory OK"
- [ ] Memory health shows "✓ PSRAM OK"
- [ ] NOT seeing "❌ ERROR: PSRAM not detected!"

## Test 1: Quick Collection (5 seconds)

1. [ ] Start collection from web UI
2. [ ] Watch serial monitor for:
   - [ ] "PSRAM allocated: 360000 bytes (30000 items)"
   - [ ] "Samples: 1000 | Memory: Heap=XXX, PSRAM=XXX"
   - [ ] Heap stays above 150KB
3. [ ] Stop collection after 5 seconds
4. [ ] Check results:
   - [ ] ~5000-6000 samples collected
   - [ ] "PSRAM freed" message appears
   - [ ] Memory stats printed
   - [ ] No crash or hang

## Test 2: Medium Collection (15 seconds)

1. [ ] Start collection
2. [ ] Let run for 15 seconds
3. [ ] Stop collection
4. [ ] Check results:
   - [ ] ~15000-18000 samples collected
   - [ ] No memory warnings
   - [ ] Device responsive

## Test 3: Maximum Duration (30 seconds)

1. [ ] Start collection
2. [ ] Wait for auto-stop
3. [ ] Check results:
   - [ ] ~30000 samples collected
   - [ ] "Max duration reached!" message
   - [ ] Upload completes successfully
   - [ ] No crash

## Test 4: Back-to-Back Collections

1. [ ] Run 3 collections in a row
2. [ ] Check after each:
   - [ ] Memory stats stable
   - [ ] Heap not decreasing
   - [ ] PSRAM allocated and freed each time
3. [ ] No memory leaks detected

## Success Criteria

✅ **All tests pass if**:
- No unexpected device resets
- All collections complete successfully
- Memory stats show PSRAM usage
- Heap stays above 150KB throughout
- Sample counts match expected values

## If Tests Fail

### Device still crashes/resets:
- Check if PSRAM is actually detected on boot
- Verify watchdog disable message appears
- Check for other error messages in serial

### Memory issues persist:
- Verify "PSRAM allocated" message appears
- Check heap usage - should NOT show 360KB allocation
- Look for "PSRAM not detected!" error

### Hangs during collection:
- Check if taskYIELD() is being called
- Verify stack size is 8192 (not 4096)
- Look for I2C errors in serial

## Troubleshooting Commands

```bash
# View linter errors
pio check

# Clean and rebuild
pio run --target clean
pio run

# Upload with verbose output
pio run --target upload -v

# Monitor with timestamp
pio device monitor --timestamp
```

## Next Steps After Successful Testing

1. [ ] Monitor CloudWatch logs for any backend issues
2. [ ] Test with different sensor configurations
3. [ ] Test with varying numbers of active sensors
4. [ ] Verify data integrity in DynamoDB
5. [ ] Check session visualization in web UI

---

**Date**: November 26, 2025  
**Status**: Ready for Testing


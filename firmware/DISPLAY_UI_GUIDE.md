# T-Display S3 UI Guide

## Overview

The Motion Play device now features a professional, two-stage UI with clear visual feedback for initialization and session recording.

## Display Modes

### 1. Initialization Screen

**Layout:**
```
┌──────────────────────────────────────────────────┐
│ MOTION PLAY                                      │
│                                                  │
│ ┌────┬────┬────┬────┬────┐                     │
│ │BOOT│WIFI│MQTT│SENS│DONE│  ← Progress Bar     │
│ │ ✓  │ ✓  │ ✓  │ ✓  │ ✓  │                     │
│ └────┴────┴────┴────┴────┘                     │
│                                                  │
│ Connecting to AWS IoT...   ← Status Message     │
│                                                  │
└──────────────────────────────────────────────────┘
```

**Progress Stages:**
1. **BOOT** (Green) - System booting up
2. **WIFI** (Yellow → Green) - Connecting to WiFi → Connected
3. **MQTT** (Yellow → Green) - Connecting to AWS IoT → Connected  
4. **SENS** (Yellow → Green) - Initializing sensors
5. **DONE** (Green) - Ready!

**Colors:**
- Gray: Not started
- Yellow: In progress
- Green: Complete with checkmark ✓
- Red: Error state

**Duration:** ~5-10 seconds (auto-progresses)

---

### 2. Session Screen

**Layout:**
```
┌──────────────────────────────────────────────────┐
│ MOTION PLAY                                      │
│ Status:                                          │
│                                                  │
│              ┌───────┐                           │
│              │       │                           │
│              │  REC  │  ← Status Indicator       │
│              │       │                           │
│              └───────┘                           │
│                                                  │
│            2500 samples  ← Sample Counter        │
│                                                  │
│ Recording in progress...  ← Message Area         │
└──────────────────────────────────────────────────┘
```

**Session States:**

#### STATE_IDLE (Gray Circle)
- **Display:** "IDLE" in gray circle
- **Message:** "Ready to record"
- **Meaning:** Device ready, waiting for start command

#### STATE_RECORDING (Red Circle, Filled)
- **Display:** "REC" in red filled circle
- **Message:** "Recording in progress..."
- **Live Counter:** Shows sample count (updates every second)
- **Meaning:** Actively collecting sensor data

#### STATE_UPLOADING (Yellow Circle)
- **Display:** "UP" in yellow circle  
- **Message:** "Uploading to cloud..."
- **Meaning:** Transmitting data to AWS

#### STATE_SUCCESS (Green Circle with Checkmark)
- **Display:** "OK" in green circle with ✓
- **Message:** "Upload complete!"
- **Duration:** Shows for 3 seconds, then returns to IDLE
- **Meaning:** Data successfully uploaded

#### STATE_ERROR (Red Circle)
- **Display:** "ERR" in red circle
- **Message:** Error description
- **Duration:** Shows for 3 seconds, then returns to IDLE
- **Meaning:** Operation failed

---

## Auto-Initialization

**Boot Sequence:**
1. Power on device
2. Serial + display initialize
3. WiFi → MQTT → cloud config fetch
4. Sensors initialize (once, with cloud config)
5. Progress bar fills as each stage completes
6. Switches to Session Screen when complete

**No More Button Press Required!**
- System automatically initializes on boot
- Right button (GPIO 14) can restart device anytime
- Left button (GPIO 0 / BOOT) is unused in normal operation

---

## User Experience Flow

### Recording a Session

**From Web UI:**
1. Click "Start Collection" → Device shows `STATE_RECORDING`
2. Red filled circle appears with "REC"
3. Sample count updates every second
4. Click "Stop Collection" → Device shows `STATE_UPLOADING`
5. Yellow "UP" indicator while transmitting
6. Green "OK" with checkmark → `STATE_SUCCESS`
7. After 3 seconds → Returns to `STATE_IDLE`

**Visual Timeline:**
```
IDLE (gray) 
   ↓ start_collection
RECORDING (red, filled) → [live sample count]
   ↓ stop_collection
UPLOADING (yellow) → [transmitting batches]
   ↓ success
SUCCESS (green, ✓) → [3 second pause]
   ↓
IDLE (gray)
```

---

## Benefits

### For Users
- **Clear status** - Always know what the device is doing
- **No confusion** - Visual states match system behavior
- **Professional look** - Progress bars, indicators, clean layout
- **No button hassle** - Auto-starts on power-up

### For Development
- **No text overlap** - Proper screen clearing and layout management
- **State-driven** - DisplayManager tracks current state
- **Easy updates** - Call `setSessionState()` to change display
- **Consistent** - All status changes go through display methods

---

## Implementation Details

### Display Manager Methods

**Initialization:**
```cpp
display.showInitScreen();                     // Show progress bar
display.updateInitStage(INIT_WIFI_CONNECTING, "Connecting..."); 
display.updateInitStage(INIT_WIFI_CONNECTED, "WiFi OK");
display.setInitError("Connection failed!");   // Show error
```

**Session:**
```cpp
display.showSessionScreen();           // Switch to session mode
display.setSessionState(STATE_IDLE);   // Ready
display.setSessionState(STATE_RECORDING); // Start recording
display.updateSampleCount(1500);       // Update counter
display.setSessionState(STATE_UPLOADING); // Uploading
display.setSessionState(STATE_SUCCESS);   // Done!
display.showMessage("Custom message", TFT_YELLOW); // Temp message
```

### Screen Layout Constants

```cpp
SCREEN_WIDTH = 320
SCREEN_HEIGHT = 170
PROGRESS_BAR_Y = 20
PROGRESS_BAR_HEIGHT = 40
STATUS_INDICATOR_Y = 80
STATUS_INDICATOR_SIZE = 60
MESSAGE_Y = 150
```

---

## Testing the New UI

### 1. Upload Firmware
```bash
cd firmware
pio run --target upload
pio device monitor
```

### 2. Observe Boot Sequence
- Device powers on
- "MOTION PLAY" appears
- Progress bar segments fill: BOOT → WIFI → MQTT → SENS → DONE
- Each segment turns green with checkmark as it completes
- Status messages appear below progress bar
- After DONE, switches to Session Screen

### 3. Test Recording
From web UI:
- Start collection → Watch red "REC" appear
- Sample count updates every second
- Stop collection → "UP" (yellow) → "OK" (green with ✓)
- Returns to gray "IDLE" after 3 seconds

### 4. Test Error Handling
- Disconnect WiFi during initialization → See error screen
- Start collection twice → See STATE_ERROR

---

## Troubleshooting

**Display stays black:**
- Check PIN_POWER_ON and PIN_LCD_BL are HIGH
- Verify TFT_eSPI library is installed
- Check User_Setup.h in `include/` directory

**Text overlaps:**
- Should be fixed! Each state clears its area before drawing
- If persists, check `tft.fillRect()` calls in DisplayManager.cpp

**Wrong colors:**
- Check TFT_eSPI color constants (TFT_RED, TFT_GREEN, etc.)
- Verify color definitions in DisplayManager.cpp

**Progress bar doesn't update:**
- Check `display.updateInitStage()` is called in sequence
- Verify stages are in order (BOOT → WIFI → MQTT → SENS → COMPLETE)

---

## Future Enhancements

### Possible Additions:
1. **WiFi signal strength indicator** - Show bars in corner
2. **Battery level indicator** - If using battery power
3. **Sensor status indicators** - Show which sensors are active
4. **QR code for web UI** - Display URL to connect
5. **Touchscreen support** - If upgrading to touch display
6. **Animated transitions** - Smooth state changes
7. **Color themes** - Dark/light mode toggle

### Display Upgrade Path:
Current: T-Display S3 (320x170 LCD)
→ T-Display S3 Touch (same size, capacitive touch)
→ T-Display AMOLED (240x536, vibrant colors)

---

## Technical Notes

- **Frame rate:** Updates as needed (event-driven)
- **Memory:** ~2KB for display buffer
- **Processor:** Runs on Core 1 (same as networking)
- **Render time:** <10ms per full screen update
- **Text rendering:** TFT_eSPI built-in fonts
- **Graphics:** Lines, circles, rectangles (no complex shapes)

---

## Change Summary

### Before (Old UI)
- ❌ Text overlapped and scrolled off screen
- ❌ No clear initialization feedback
- ❌ Required button press to start
- ❌ Unclear session state
- ❌ Status messages got buried

### After (New UI)
- ✅ Clean, segmented progress bar
- ✅ Clear visual state indicators
- ✅ Auto-initialization on boot
- ✅ Professional status displays
- ✅ No text overlap
- ✅ Live sample counter during recording
- ✅ Color-coded states (red=recording, yellow=uploading, green=success)

---

*Last Updated: November 14, 2025*


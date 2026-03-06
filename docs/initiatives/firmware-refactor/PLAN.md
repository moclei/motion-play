# Firmware Architecture Refactor — Plan

## Approach

The firmware is ~12,000 lines of active C++ across 30+ source files. Six files exceed 600 lines, with `main.cpp` at 1,845 being the worst offender. Rather than a big-bang rewrite, we audit the codebase in structured batches, document findings, then execute incremental refactoring steps.

### File Size Tiers

**Over 600 lines (must split):**
| File | Lines |
|------|-------|
| `main.cpp` | 1,845 |
| `SensorManager.cpp` | 1,429 |
| `DisplayManager.cpp` | 874 |
| `InterruptManager.cpp` | 795 |
| `DataTransmitter.cpp` | 769 |
| `CalibrationManager.cpp` | 725 |

**300-600 lines (review for splitting):**
| File | Lines |
|------|-------|
| `MLDetector.cpp` | 578 |
| `VCNL4040.h` | 539 |
| `DirectionDetector.cpp` | 451 |
| `VCNL4040.cpp` | 423 |
| `InterruptManager.h` | 357 |
| `MuxController.cpp` | 325 |
| `MQTTManager.cpp` | 300 |

### Review Lens

Each batch is evaluated against these criteria:

1. **Single Responsibility** — Does each file/class do one thing?
2. **File size** — Decomposition recommendations for files over 300 lines
3. **Header hygiene** — Include guards, forward declarations, minimal includes
4. **Memory safety** — Buffer overruns, uninitialized variables, PSRAM patterns
5. **Concurrency** — Dual-core safety (mutexes, volatile, atomic), ISR safety
6. **API design** — Clean interfaces, hidden coupling between modules
7. **Naming and conventions** — Consistent style, const/static usage
8. **Error handling** — Silent failures, cascading crashes
9. **Magic numbers** — Hardcoded values that should be constants or configurable
10. **Dead code** — Unused functions, commented-out blocks, debug leftovers

## Module Analysis

Findings are documented here batch-by-batch as the audit progresses.

### Batch 1: main.cpp

**1,845 lines. The worst offender in the codebase.**

main.cpp is simultaneously the initialization orchestrator, cloud config client, command dispatcher, button handler, detection engine, data capture pipeline, and heartbeat manager. It owns ~30 mutable globals and has no class to encapsulate state. Nearly every component in the system is touched directly from this file.

#### 1. Single Responsibility Violations

main.cpp performs at least 9 distinct jobs:

| Responsibility | Lines | Size | Should live in |
|---|---|---|---|
| System initialization orchestration | 87–451 | ~365 | Acceptable in main, but `initializeSystem()` could be leaner |
| Cloud config fetching & JSON parsing | 110–301 | ~190 | **`CloudConfig`** module |
| Command dispatch + all handler logic | 453–1256 | **~800** | **`CommandHandler`** module |
| Button input (reads, long-press detect) | 1260–1351 | ~90 | **`ButtonHandler`** or fold into `InterruptManager` |
| Sensor queue drain (interrupt + polling) | 1360–1426 | ~65 | Part of a `CollectionController` |
| Play-mode detection loop | 1428–1535 | ~110 | **`DetectionController`** (shared with Live Debug) |
| Live-debug detection + capture loop | 1536–1733 | ~200 | **`DetectionController`** (80% duplicated from Play) |
| Debug-mode auto-stop + upload | 1734–1813 | ~80 | Part of a `CollectionController` |
| Periodic MQTT heartbeat | 1816–1843 | ~28 | Trivial, can stay or move to `MQTTManager` |

The `handleCommand()` function alone (800+ lines) is larger than 4 of the 6 "must-split" files listed in this plan.

#### 2. Code Duplication (Critical)

This is the most damaging structural problem:

**a) Config parsing — duplicated in two places (~90% identical):**
- `fetchConfigFromCloud()` (lines 153–283): parses JSON `sensor_config` from HTTP response
- `configure_sensors` command handler (lines 780–923): parses JSON `sensor_config` from MQTT payload

Both walk the same fields (`sample_rate_hz`, `led_current`, `integration_time`, `multi_pulse`, `ball_diameter_mm`, interrupt settings, detection params, serial studio, etc.) with near-identical code. Any new config field must be added in both places — a guaranteed source of drift bugs.

**b) Play mode vs Live Debug detection loops (~80% identical):**
- Play: lines 1428–1535
- Live Debug: lines 1536–1733

Both loops: feed readings to detector → check for detection → LED/display feedback → handle cooldown → buffer overflow prevention. Live Debug adds a capture/transmit step after detection. This is classic "copy-paste-modify" that should be a single parameterized flow.

**c) Calibration sensor config extraction — triplicated:**
The pattern `mp = multi_pulse.toInt(); it = integration_time.toInt(); led = led_current.toInt(); calibrationManager.setSensorConfig(mp, it, led)` with identical null-guard logic appears at lines 1075–1084, 1279–1289, and 1312–1322.

**d) Active sensor counting — triplicated:**
`for (const auto &m : sessionManager.getSensorMetadata()) { if (m.active) activeCnt++; }` appears at lines 704–709, 1172–1177, and 1652–1657.

**e) Mode-switching boilerplate:**
Each case in `set_mode` (idle, debug, play, live_debug) repeats: stop interrupt monitoring → set display mode → show message → publish status → reset detector → apply calibration. The calibration-apply block alone (check `isValid()`, call `setCalibration()`, else `setCalibration(nullptr)`) is duplicated between play and live_debug.

#### 3. Concurrency Concerns (Dual-Core)

**a) `currentConfig` shared across cores without protection:**
`currentConfig` is written by Core 1 (in `handleCommand(configure_sensors)` and `fetchConfigFromCloud()`) and read by Core 0's sensor task via the pointer passed to `sensorManager.init(&currentConfig)`. If a `configure_sensors` command arrives mid-read on Core 0, the config struct could be half-updated — torn reads on multi-field structs are not atomic. This needs a mutex or double-buffering.

**b) MQTT callback → `handleCommand()` re-entrancy:**
The MQTT callback (line 363) calls `handleCommand()` directly from within `mqttManager->loop()`, which is called from `loop()`. If `handleCommand()` triggers any operation that calls back into MQTT (e.g., `publishStatus`), this is a re-entrant call into PubSubClient, which is not re-entrant safe. Currently works because PubSubClient processes one message at a time, but it's fragile.

**c) `sensorManager.stopCollection()` / `startCollection()` cross-core coordination:**
`handleCommand()` on Core 1 calls `sensorManager.stopCollection()` and `startCollection()`, which must synchronize with Core 0's sensor reading task. The safety of this depends on SensorManager's internal implementation (to be verified in Batch 2), but main.cpp assumes these calls are synchronous and immediately effective — there's no handshake or confirmation.

**d) `sessionManager.getDataBuffer()` producer-consumer access:**
Core 0 writes sensor readings; Core 1 reads them for detection processing (lines 1452–1468, 1564–1578). The buffer is accessed via direct indexing (`buffer[i]`). This likely works as a lock-free producer-consumer pattern (Core 0 only appends, Core 1 only reads up to the current size), but there's no documentation or assertion enforcing this invariant. A stale `buffer.size()` read could cause Core 1 to read uninitialized memory. To be verified in Batch 4.

**e) `static` local variables in `loop()`:**
`lastProcessedIndex` (line 1453) and `lastLiveDebugIndex` (line 1563) are `static` locals that track detection processing progress. They're reset to 0 in multiple places (buffer clears) but their lifecycle is implicit and fragile. These should be explicit member state of whatever class owns detection processing.

#### 4. Error Handling

**a) Fatal `while(1) delay(1000)` hangs (4 occurrences):**
- WiFi config load failure (line 317–318)
- WiFi connect failure (line 328–329)
- MQTT config load failure (line 339–340)
- Sensor init failure (line 402–403)

These are permanent hangs with no watchdog recovery. The device becomes a brick until manually power-cycled. At minimum, these should `ESP.restart()` after a timeout, or use the hardware watchdog.

**b) Inconsistent failure strategy:**
- WiFi/sensor init failure → hang forever (bad)
- MQTT connect failure → warning + continue (good, graceful degradation)
- CalibrationManager failure → warning + continue (good)
- ML detector failure → fallback to heuristic (good)
- Upload failure in auto-stop → `ESP.restart()` (line 1789, aggressive)
- Upload failure in manual stop → clear buffer + continue (data lost silently)

There's no unified error handling philosophy. Some failures are fatal, some are recoverable, some lose data silently.

**c) No null checks on heap allocations:**
`mqttManager = new MQTTManager(...)` (line 334) and `dataTransmitter = new DataTransmitter(...)` (line 360) are never null-checked. On ESP32 with constrained heap, allocation failure returns `nullptr`. Calling methods on `nullptr` → hard crash.

**d) Data loss on upload failure:**
When `dataTransmitter->transmitSession()` fails in the manual stop path (lines 730–738), the buffer is cleared and the session data is gone. No retry, no local persistence, no notification beyond a status MQTT message.

#### 5. Magic Numbers

| Value | Location(s) | Should be |
|---|---|---|
| `500` | line 62 | Already `DETECTION_COOLDOWN` — good |
| `500` | line 1517 | **Needs constant**: `PLAY_BUFFER_OVERFLOW_LIMIT` |
| `30000` | lines 1389, 1739 | **Needs constant**: `MAX_SESSION_DURATION_MS` (duplicated) |
| `2048` | line 141 | **Needs constant**: `CONFIG_JSON_DOC_SIZE` |
| `1024` | line 368 | **Needs constant**: `COMMAND_JSON_DOC_SIZE` |
| `5000` | line 130 | **Needs constant**: `HTTP_TIMEOUT_MS` |
| `3000` | lines 1486, 1594 | **Needs constant**: `LED_DETECTION_DISPLAY_MS` |
| `200` | lines 517, 1082, 1283, 1320 | **Needs constant**: `DEFAULT_LED_CURRENT_MA` (repeated 4×) |
| `1000` | line 793 | **Needs constant**: `DEFAULT_SAMPLE_RATE_HZ` |
| `10` | line 1845 | **Needs constant**: `MAIN_LOOP_DELAY_MS` |
| Various delays | `1000`, `1500`, `2000`, `3000` throughout | Should be named constants for display message durations |

#### 6. Dead Code & Unnecessary Includes

- **`#include <Adafruit_VCNL4040.h>`** (line 2): main.cpp never uses the VCNL4040 API directly. This include leaks sensor driver internals into the top-level orchestrator. Remove it.
- **Unused return value** (line 1431): `bool animating = ledController.update();` captures a return value that is never read. Should be `ledController.update();`.

#### 7. Global State

main.cpp declares ~30 global variables (lines 35–81). All mutable, all file-scope, no encapsulation:

- 10 component instances (managers, controllers, output)
- `useMLDetection`, `serialStudioEnabled` (feature flags)
- `detectorConfig` (algorithm parameters)
- `currentMode`, `playModeActive`, `liveDebugActive` (mode state)
- `lastDetectionTime` (cooldown tracking)
- `currentConfig` (sensor configuration)
- `systemInitialized` (never actually read after being set)
- Various timing variables

This global state makes testing impossible, reasoning about data flow difficult, and any future multi-device or multi-instance scenario unworkable. The globals should migrate into a top-level `Application` or `DeviceController` class, or at minimum into the modules that own each responsibility.

Note: `systemInitialized` (line 77) is set to `true` at line 450 but never read anywhere in main.cpp — potential dead state.

#### 8. Decomposition Recommendations

Listed in priority order (highest impact first):

| # | Extraction | What moves out | Est. lines saved | Effort | Notes |
|---|---|---|---|---|---|
| 1 | **`CommandHandler`** | All of `handleCommand()`: command parsing, dispatch, per-command logic | ~800 | Large | Highest impact. Class with methods per command. Receives references to managers. |
| 2 | **`CloudConfig`** | `fetchConfigFromCloud()` + shared config-parsing helper (eliminates duplication with `configure_sensors`) | ~250 | Medium | Extract a `applySensorConfig(JsonObject&)` helper used by both fetch and command. |
| 3 | **`DetectionController`** | Play-mode and Live-debug detection loops, unified into one parameterized flow | ~250 | Medium | Eliminates the worst duplication. Parameterize: "capture on detection?" yes/no. |
| 4 | **`CollectionController`** | start/stop collection orchestration (interrupt + polling branches), auto-stop logic, queue drain | ~200 | Medium | Simplifies `handleCommand` further. Owns the interrupt/polling branching. |
| 5 | **`ButtonHandler`** | Button reading, debounce, long-press detection | ~90 | Small | Clean, self-contained. Could be a simple class with an `update()` method. |
| 6 | **Constants header** | All magic numbers → `firmware/include/constants.h` or per-module constants | ~0 (readability) | Small | Quick win. Do this first as a standalone PR. |
| 7 | **Error handling policy** | Replace `while(1)` hangs with timeout + restart; add null checks on `new` | ~0 (safety) | Small | Quick win. High reliability impact. |

**Recommended execution order:** #6 (constants) → #7 (error handling) → #2 (CloudConfig, eliminates duplication) → #1 (CommandHandler) → #3 (DetectionController) → #4 (CollectionController) → #5 (ButtonHandler).

After these extractions, main.cpp should be ~150–200 lines: `setup()`, `loop()` (delegation only), global object wiring, and forward declarations.

### Batch 2: Sensor Pipeline

*Not yet analyzed.*

### Batch 3: Detection & ML

*Not yet analyzed.*

### Batch 4: Session & Data

*Not yet analyzed.*

### Batch 5: I/O & Peripherals

*Not yet analyzed.*

### Batch 6: Networking & Infrastructure

*Not yet analyzed.*

## Refactoring Strategy

Will be populated after the audit phase is complete, based on consolidated findings. Expected to include:

- Decomposition plan for main.cpp (likely the highest-impact change)
- Module boundary cleanup
- Shared types / common definitions extraction
- Header restructuring
- Specific per-module recommendations

## Open Questions

- How tightly coupled is main.cpp to component internals? (Determines difficulty of decomposition)
- Are there circular dependencies between components?
- What shared state exists between Core 0 and Core 1, and how is it protected?
- Is there a consistent error handling pattern, or does each component do its own thing?

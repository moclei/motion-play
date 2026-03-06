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

**Files reviewed:** `SensorManager.cpp` (1,429 lines), `SensorManager.h` (142 lines), `MuxController.cpp` (325 lines), `MuxController.h` (199 lines), `VCNL4040.cpp` (423 lines), `VCNL4040.h` (539 lines), `SensorConfiguration.h` (49 lines), `TCA9548A.h/cpp` (19+64 lines), inline `PCA9546A` class (48 lines).

**The defining problem in this batch:** the codebase contains two parallel implementations of both the mux layer and the VCNL4040 driver. SensorManager uses old code (TCA9548A class + inline PCA9546A + raw `Wire` I2C calls), while InterruptManager uses the newer, cleaner abstractions (MuxController + custom VCNL4040 driver). SensorManager — the Core 0 hot path — is the one stuck on the legacy approach.

#### 1. Single Responsibility Violations

SensorManager performs at least 8 distinct jobs:

| Responsibility | Lines (approx) | Should live in |
|---|---|---|
| MUX orchestration (TCA + PCA channel selection, cleanup) | ~120 scattered | **MuxController** (already exists) |
| Raw I2C register reads/writes to VCNL4040 | ~200 scattered | **VCNL4040** driver (already exists) |
| Sensor config parsing (string→enum→register bits) | 201–269 | **VCNL4040** or a config helper |
| Sensor config application (register writes + verify/retry) | 271–375 | **VCNL4040** driver |
| PS_CANC baseline calibration | 38–192 | **CalibrationManager** or standalone |
| Diagnostic I2C scan + config dump | 377–555, 1256–1429 | Debug/diagnostic module |
| FreeRTOS task lifecycle (create, stop, graceful shutdown) | 898–1129 | **CollectionController** or kept, but simplified |
| Sensor metadata generation | 1132–1151 | Could stay, but allocs heap on every call |

The PCA9546A class (48 lines) is defined inline inside `SensorManager.h`. This is a hardware abstraction that belongs in its own file — or better, replaced by MuxController which already handles both TCA and PCA.

#### 2. Parallel / Duplicated Implementations (Critical)

This is the most impactful structural problem in this batch.

**a) MUX management — two implementations:**
- `SensorManager` uses `TCA9548A` class + inline `PCA9546A` class + manual channel management
- `MuxController` (325+199 lines) is a cleaner, unified abstraction that handles both TCA→PCA selection in a single `selectSensor(position)` call, tracks current channel state, and properly handles board-switching cleanup

SensorManager should adopt MuxController, eliminating TCA9548A, inline PCA9546A, and ~120 lines of scattered channel management.

**b) VCNL4040 communication — two implementations:**
- `SensorManager` uses raw `Wire.beginTransmission(0x60)` / `Wire.write()` / `Wire.endTransmission()` calls for every register operation (~200 lines)
- `VCNL4040` (423+539 lines) is a complete, clean driver with register abstraction, named constants, `readProximity()`, `setLEDCurrent()`, etc.

SensorManager does not use the VCNL4040 driver at all. It doesn't even use the Adafruit library that it includes — the `Adafruit_VCNL4040 sensors[NUM_SENSORS]` array (line 75 of the header) is declared but **never initialized or used**. The Adafruit `#include` exists solely for its enum types (`VCNL4040_LEDCurrent`, etc.) used in the config parsing functions.

**c) MUX cleanup pattern — repeated 7 times:**
The pattern "select each TCA channel → disable its PCA → disable all TCA channels" appears in: `cleanupI2CBus()`, `calibrateProximityCancellation()` (exit), `init()` (exit), `reinitialize()` (exit), `dumpSensorConfiguration()` (exit), and `sensorTaskFunction()` (every cycle + exit). This is exactly what `MuxController::disableAll()` does in one call.

**d) Sensor iteration with TCA/PCA selection — repeated 4 times:**
The pattern "for each sensor: select TCA, select PCA, do I2C work" appears in `init()`, `reinitialize()`, `dumpSensorConfiguration()`, and `calibrateProximityCancellation()`. Each reimplements the same channel-switching logic with slightly different delay values.

#### 3. Concurrency Safety (Core 0 Hot Path)

**a) `stopRequested` is `volatile bool`, not `std::atomic<bool>`:**
Written by Core 1 (`stopCollection()`), read by Core 0 (`sensorTaskFunction()`). On ESP32 (Xtensa LX7), single-word reads/writes are naturally atomic, so this works in practice. But `volatile` does not guarantee memory ordering — the compiler and CPU could reorder surrounding operations. The correct tool is `std::atomic<bool>` with `memory_order_relaxed` (sufficient here since there's no dependent data to synchronize).

**b) `sensorTask = NULL` race in task self-deletion:**
At line 1038, the task sets `sensorTask = NULL` then immediately calls `vTaskDelete(NULL)`. Between setting NULL and actual deletion, the task is still running. If Core 1 calls `startCollection()` at exactly this moment, it sees `sensorTask == NULL`, proceeds to create a new task, and now there are briefly two tasks. Extremely unlikely but architecturally unsound. The proper pattern is to use a task notification or event group for the handshake, or have `stopCollection()` call `vTaskDelete()` from Core 1 after confirming the task has reached its exit point.

**c) `activeSummary` pointer cross-core access:**
Set by `startCollection()` on Core 1 (line 1059), read by the sensor task on Core 0 throughout `sensorTaskFunction()`. There's no memory barrier between the write and the read. In practice, the `xTaskCreatePinnedToCore()` call likely provides an implicit barrier, but this should be documented or made explicit.

**d) `activeConfig` pointer replacement during reinitialize:**
`reinitialize()` calls `stopCollection()` first (line 1159), then updates `activeConfig` (line 1175). This is safe because the task is stopped before the pointer changes. Good pattern — but the safety depends on `stopCollection()` fully completing before the pointer update, which is handled correctly by the timeout/poll loop.

**e) `isCollecting()` reads `sensorTask` without synchronization:**
Called from Core 1, but `sensorTask` is written from Core 0 (line 1038). On ESP32 this is safe for a pointer-sized read, but it should be documented or use `std::atomic`.

**f) No protection on `dataQueue` during `startCollection()`:**
If `startCollection()` is called while a previous task is in its shutdown path (after `stopRequested` is set but before `sensorTask = NULL`), `dataQueue` gets reassigned. The old task could still be writing to the old queue. The stop-then-start sequence in `stopCollection()` mitigates this, but the forced-delete fallback path (line 1116) could leave the queue in an inconsistent state.

#### 4. I2C Error Handling

**a) `readSensor()` returns `proximity = 0` on I2C failure (line 867):**
The caller cannot distinguish "sensor legitimately reads 0 proximity" from "I2C bus error." The return value is `true` (success) even when `Wire.available() < 2` — because `proximity` is set to 0 and the function only returns `false` for inactive sensors or mux selection failures. Same issue for ambient light reads (line 892). This silently injects bad data into the pipeline at 1000 Hz.

**b) No retry logic in the hot path:**
A single I2C NACK in `readSensor()` causes immediate data loss for that sensor for that cycle. At 1000 Hz with 6 sensors, transient I2C glitches are expected. There's no bus recovery mechanism (clock toggling, bus reset) — a hung bus stays hung.

**c) MUX selection failures are silently swallowed:**
In `readSensor()` (lines 837, 841), if `mux.selectChannel()` or `pca_instances[].selectChannel()` fail, the function returns `false`. But there's no attempt to recover the bus state. The next sensor read assumes the bus is still functional.

**d) Inconsistent error handling across methods:**
- `applySensorConfig()`: verify-then-retry with extra delays — good pattern
- `calibrateSensorBaseline()`: `continue` on failed samples, threshold check at end — OK
- `init()`: individual sensor failures logged and skipped — OK, graceful
- `readSensor()` hot path: no retry, no recovery — problematic at 1000 Hz
- `sensorTaskFunction()`: consecutive failure counting with throttled logging — good telemetry, but no corrective action

**e) `Wire.endTransmission()` return value sometimes ignored:**
Line 115 in `calibrateSensorBaseline()` (`Wire.endTransmission(false)` during verify readback) — return value not checked. Line 770 in `init()` (default config write) — return value not checked. These are non-critical paths but inconsistent with the error-checking discipline elsewhere.

#### 5. Memory Safety

**a) `Adafruit_VCNL4040 sensors[NUM_SENSORS]` — dead allocation (line 75 of header):**
Six `Adafruit_VCNL4040` objects are constructed on the heap (inside SensorManager) but never initialized (`begin()` never called) and never used for any reads. This wastes memory and is misleading. The Adafruit library is used only for its enum type definitions. Remove the array; if the enums are needed, define local equivalents or switch to the custom VCNL4040 driver's approach.

**b) `getSensorMetadata()` heap-allocates on every call (line 1132–1151):**
Returns `std::vector<SensorMetadata>` where each element contains a `String name`. Called from main.cpp in multiple places (counting active sensors, building JSON). On an embedded target, this is wasteful — 6 heap allocations for String objects plus the vector itself. Should be a pre-computed array accessible by const reference.

**c) Config string parsing uses Arduino `String` throughout:**
`SensorConfiguration` stores `led_current`, `integration_time`, `duty_cycle`, `multi_pulse` as `String` objects. These are compared character-by-character in `parseLEDCurrent()`, `parseIntegrationTime()`, etc. on every config application. Using `const char*` or enum values directly would avoid heap allocation and be faster.

#### 6. Magic Numbers

| Value | Location(s) | Should be |
|---|---|---|
| `0x60` | ~15 occurrences across SensorManager.cpp | `VCNL4040_ADDR` (already defined in MuxController.h and VCNL4040.h) |
| `0x0186` | lines 742, 1318 | `VCNL4040_ID_VALUE` (already defined in VCNL4040.h) |
| `0x03`, `0x04`, `0x05`, `0x08`, `0x09`, `0x0C` | throughout | Register constants (already defined in VCNL4040.h: `VCNL4040_PS_CONF1_2`, etc.) |
| `43, 44` | line 636 | **`I2C_SDA_PIN`, `I2C_SCL_PIN`** in pin_config.h |
| `400000` | line 637 | **`I2C_CLOCK_HZ`** constant (or use `activeConfig->i2c_clock_khz * 1000`) |
| `50` | line 63 | **`BASELINE_NUM_SAMPLES`** |
| `10` | line 64 | **`BASELINE_SAMPLE_DELAY_MS`** |
| `8192` | line 1069 | **`SENSOR_TASK_STACK_SIZE`** |
| `2` | line 1071 | **`SENSOR_TASK_PRIORITY`** |
| `0` | line 1073 | **`SENSOR_TASK_CORE`** |
| `500` | line 1097 | Already named `STOP_TIMEOUT_MS` — good |
| `100000` | line 1018 | **`WATCHDOG_YIELD_INTERVAL_US`** |
| `0x74, 0x75, 0x76` | header line 78 | **`PCA_DEFAULT_ADDR_BOARD_0/1/2`** |
| Various delays | `2, 5, 10, 20, 50, 100` ms | Named constants for settling times: `MUX_SETTLE_MS`, `PCA_SETTLE_MS`, `CONFIG_SETTLE_MS` |

#### 7. Dead Code & Unnecessary Includes

- **`Adafruit_VCNL4040 sensors[NUM_SENSORS]`** (header line 75): 6 objects constructed, never used. Dead weight.
- **`#include <Adafruit_VCNL4040.h>`** (header line 7): Pulls in the entire Adafruit library. Only used for enum type aliases in `parseLEDCurrent()`, `parseIntegrationTime()`, `parseDutyCycle()`. These enums are just integer constants that could be replaced by the values from the custom VCNL4040.h or plain integers.
- **`extern bool serialStudioEnabled`** (cpp line 4): Global dependency leaking Serial Studio concerns into the sensor pipeline. Should be injected via config or a logging abstraction.
- **`debugI2CScan()`** (lines 377–555, ~180 lines): Diagnostic function gated by `STARTUP_I2C_SCAN`. Useful but inflates the file. Should be in a debug/diagnostic module.
- **`dumpSensorConfiguration()`** (lines 1256–1429, ~175 lines): Similarly diagnostic. Same recommendation.

#### 8. API Design

**a) Raw pointer ownership ambiguity:**
`init(SensorConfiguration *config)` stores the pointer but doesn't own the memory. If the caller frees or modifies the config struct, the sensor task (on Core 0) reads stale/freed memory. The pointer relationship is documented nowhere. Same issue with `startCollection(QueueHandle_t queue, SessionSummary *summary)`.

**b) `readSensor()` is public but only safe within the sensor task:**
The method performs raw I2C operations that assume the correct MUX channels are selected. If called from Core 1 or any context other than the sensor task loop, it will interfere with whatever the sensor task is doing on the I2C bus. Should be private.

**c) Tight FreeRTOS coupling:**
`startCollection()` takes a `QueueHandle_t` directly, binding the public API to FreeRTOS internals. A callback or abstract interface would be more testable and portable.

**d) Configuration parsing returns Adafruit enum types:**
`parseLEDCurrent()` returns `VCNL4040_LEDCurrent` (Adafruit enum), which is then cast to integer bits for direct register writes. The Adafruit types serve no purpose here — they're just named integers being used as intermediate values.

#### 9. Naming & Style

- `sensorMapping` vs `_sensorMap` (in MuxController) — inconsistent naming convention between the two mux implementations.
- `pca_instances` / `pca_addresses` use snake_case; `activeConfig` / `sensorsActive` use camelCase — mixed conventions within the same class.
- `NUM_SENSORS` (macro) vs `MUX_TOTAL_SENSORS` (macro in MuxController) — same concept, different names.
- TCA/PCA cleanup blocks appear inline rather than as helper functions, reducing readability.

#### 10. Decomposition Recommendations

Listed in priority order (highest impact first):

| # | Extraction | What it achieves | Est. lines saved | Effort | Notes |
|---|---|---|---|---|---|
| 1 | **Adopt MuxController** in SensorManager | Eliminates TCA9548A class, inline PCA9546A, all manual channel management. Replace `mux.selectChannel()` + `pca_instances[].selectChannel()` with `muxController.selectSensor(position)`. Replace 7 cleanup blocks with `muxController.disableAll()`. | ~200 | Medium | MuxController already exists and is tested (used by InterruptManager). |
| 2 | **Adopt VCNL4040 driver** in SensorManager | Replace all raw `Wire.beginTransmission(0x60)` / `Wire.write(register)` patterns with `vcnl.readProximity()`, `vcnl.setLEDCurrent()`, etc. Eliminates all magic register addresses and bit manipulation. | ~250 | Medium | VCNL4040 driver already exists. Need one instance per sensor or a shared instance with mux selection before each call. |
| 3 | **Extract diagnostic functions** | Move `debugI2CScan()` (~180 lines) and `dumpSensorConfiguration()` (~175 lines) to a `SensorDiagnostics` module. | ~355 | Small | Pure extraction. These are called only during init or on demand. |
| 4 | **Extract calibration** | Move `calibrateSensorBaseline()` and `calibrateProximityCancellation()` to CalibrationManager or a standalone `BaselineCalibrator`. | ~160 | Small | Already partially overlaps with CalibrationManager (Batch 3). |
| 5 | **Remove dead Adafruit dependency** | Delete `sensors[NUM_SENSORS]` array, remove `#include <Adafruit_VCNL4040.h>`, replace enum types with custom VCNL4040.h constants or plain integers. | ~0 (clarity) | Small | Quick win. Removes a misleading dependency. |
| 6 | **Fix `readSensor()` silent failure** | Return a distinct error indicator when I2C read fails (e.g., `reading.proximity = UINT16_MAX` as sentinel, or change return semantics). | ~0 (correctness) | Small | High data-integrity impact. |
| 7 | **Constants extraction** | Move magic numbers to named constants. Use existing definitions from VCNL4040.h and MuxController.h where they exist. Pin numbers to `pin_config.h`. | ~0 (readability) | Small | Quick win. Do alongside #1 and #2. |
| 8 | **Concurrency hardening** | Replace `volatile bool stopRequested` with `std::atomic<bool>`. Fix `sensorTask = NULL` race. Document cross-core pointer sharing contract. | ~0 (safety) | Small | High reliability impact. |
| 9 | **Pre-compute sensor metadata** | Replace `getSensorMetadata()` vector+String construction with a pre-computed `const` array populated at init time. | ~20 | Small | Eliminates heap allocation per call. |

**Recommended execution order:** #5 (remove dead Adafruit) → #7 (constants) → #1 (adopt MuxController) → #2 (adopt VCNL4040 driver) → #6 (fix readSensor) → #8 (concurrency) → #3 (extract diagnostics) → #4 (extract calibration) → #9 (metadata).

After these changes, SensorManager.cpp should drop from ~1,429 lines to ~300–400 lines: FreeRTOS task lifecycle, collection orchestration, and delegation to MuxController + VCNL4040 driver.

**Key dependency:** Extractions #1 and #2 are high-impact because the clean replacements already exist. This is not speculative refactoring — it's unifying two parallel implementations that drifted apart.

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

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

**⚠ Unification risk — VCNL4040 driver adoption (extraction #2):**

SensorManager's raw I2C and the custom VCNL4040 driver serve two different sensor modes (polling vs interrupt) that never run simultaneously. The driver is a functional superset — it can do everything SensorManager does. However, three behavioral differences must be handled during migration:

1. **Full-register-write vs read-modify-write:** SensorManager's `applySensorConfig()` builds entire register values from scratch (all bits explicitly set). The VCNL4040 driver's per-field methods (`setLEDCurrent()`, `setProxIntegrationTime()`, etc.) use `bitMask()` which does read-modify-write, preserving bits the caller didn't touch. During migration, we need either: (a) a `configureForPolling()` method that sets ALL fields explicitly, or (b) a `writeRegister()` call to zero-initialize registers before applying per-field settings. Without this, stale bits from a previous interrupt-mode configuration could persist.

2. **Verify-then-retry on LED current:** SensorManager has custom logic that reads back the LED current register after writing and retries with extra delays if it doesn't match. This was added to address a real hardware issue. The VCNL4040 driver has no verify/retry. This pattern must be preserved — either as a wrapper around the driver's `setLEDCurrent()`, or as a new `setLEDCurrentVerified()` method on the driver.

3. **Mode transition cleanup:** When switching from interrupt mode (InterruptManager) to polling mode (SensorManager), the full-register-write approach implicitly clears interrupt-related bits (thresholds, persistence, interrupt type). The driver's per-field approach would NOT clear those unless we explicitly disable them. The migration must include an explicit "reset to polling defaults" step when entering polling mode.

### Batch 3: Detection & ML

**Files reviewed:** `DirectionDetector.cpp` (451 lines), `DirectionDetector.h` (252 lines), `MLDetector.cpp` (578 lines), `MLDetector.h` (191 lines), `CalibrationManager.cpp` (725 lines), `CalibrationManager.h` (275 lines), `CalibrationData.h` (207 lines).

**The defining problems in this batch:** (1) DirectionDetector and MLDetector implement parallel detection pipelines with no shared interface, forcing main.cpp to duplicate all detection logic behind `if (useMLDetection)` branches. (2) CalibrationManager blocks the main loop with `delay()` calls despite being designed as a non-blocking state machine. (3) A silent integer overflow bug in `StatsAccumulator` corrupts calibration stddev calculations.

#### 1. Single Responsibility Violations

**DirectionDetector** (703 total lines across .h/.cpp) performs 5 distinct jobs:

| Responsibility | Lines (approx) | Should live in |
|---|---|---|
| Per-sensor baseline management (rolling buffer, adaptive threshold) | ~60 | Could stay, but threshold logic is tangled with calibration |
| Per-sensor wave state machine (IDLE → IN_WAVE → COMPLETE) | ~50 | Core detection logic — good |
| Module-level detection (pair both sides, validate timing) | ~60 | Good |
| Cross-module consensus + confidence scoring | ~60 | Could be a separate scoring strategy |
| Legacy telemetry accessors (6 methods duplicating per-sensor accessors) | ~40 | Should be removed when Serial Studio output is updated |

The header is the bigger problem. `DirectionDetector.h` defines 6 types: `Direction`, `DetectorState`, `WaveState`, `DetectionResult`, `DetectorConfig`, `RingBuffer<T,SIZE>`, and `SensorTracker` — all in one header. Any file that includes `DirectionDetector.h` (including `MLDetector.h`) pulls in everything. `RingBuffer` is a generic utility that should be in its own header. The detection types (`Direction`, `DetectionResult`, `DetectorConfig`) should be in a shared `DetectionTypes.h` that both detectors include.

**MLDetector** (769 total lines) performs 6 distinct jobs:

| Responsibility | Lines (approx) | Should live in |
|---|---|---|
| TFLite lifecycle (init, deinit, op registration, arena allocation) | ~130 | **`TFLiteRuntime`** — reusable for any future models |
| Ring buffer for sensor frames | ~30 | Generic utility (or reuse `RingBuffer` from DirectionDetector) |
| Reading aggregation (per-timestamp frame assembly) | ~50 | Frame builder / preprocessor |
| Smoothing + baseline + trigger logic | ~100 | Duplicates DirectionDetector's job |
| Input preparation (resampling to 1ms grid, normalization) | ~70 | **`MLPreprocessor`** — model-specific preprocessing |
| Inference execution + result interpretation | ~70 | Could stay |

**CalibrationManager** (1,000 total lines across .h/.cpp) performs 5 distinct jobs:

| Responsibility | Lines (approx) | Should live in |
|---|---|---|
| Calibration state machine (transitions, PCB sequencing) | ~200 | Core logic — good |
| Sensor reading via SensorManager | ~40 | OK as delegation |
| Display/UI rendering coordination | ~150 scattered | **Should be event-driven**: emit state changes, let a listener handle display |
| Button input handling (debounce, long-press) | ~30 | **`ButtonHandler`** (same extraction recommended in Batch 1) |
| Statistics accumulation | ~50 | `StatsAccumulator` is already a separate class — good, but has a bug (see §5) |

#### 2. No Shared Detector Interface (Critical Duplication Driver)

DirectionDetector and MLDetector implement the same public API pattern — `addReading()`, `flushReading()`, `hasDetection()`, `getResult()`, `reset()`, `fullReset()`, `isReady()` — but share no common base class or interface. This forces main.cpp (documented in Batch 1) to duplicate all detection loop logic behind `if (useMLDetection)` checks.

An abstract `IDetector` interface would allow:
```cpp
class IDetector {
public:
    virtual void addReading(const SensorReading &reading) = 0;
    virtual void flushReading() = 0;
    virtual bool hasDetection() const = 0;
    virtual DetectionResult getResult() = 0;
    virtual void reset() = 0;
    virtual void fullReset() = 0;
    virtual bool isReady() const = 0;
    virtual ~IDetector() = default;
};
```

main.cpp would hold `IDetector *detector` and the play/live-debug detection loops would collapse into a single parameterized flow — reinforcing the Batch 1 recommendation for `DetectionController`.

#### 3. Concurrency Safety

**a) `extern bool serialStudioEnabled` in DirectionDetector.cpp (line 3):**
Written by Core 1 (command handler), read by Core 1 (detection processing). Currently safe because both are on the same core, but this is a hidden coupling — if detection processing ever moves to Core 0 (plausible optimization), it becomes a data race. Should be injected via config or a logging abstraction rather than a global extern.

**b) CalibrationManager `readPCB()` calls `_sensorMgr->readSensor()` — potential I2C bus collision:**
CalibrationManager runs in `loop()` on Core 1. `readSensor()` performs raw I2C transactions. If Core 0's sensor task is also running, both cores access the I2C bus simultaneously. The safety depends entirely on main.cpp stopping the sensor task before starting calibration — but CalibrationManager doesn't enforce this. A precondition assertion (`assert(!_sensorMgr->isCollecting())` in `startCalibration()`) would catch violations.

**c) `static` local variables in CalibrationManager state handlers (7 occurrences):**
`handleIntro()` has `static bool introRendered`, `handleBaseline()` has `static uint32_t lastDisplayUpdate`, `handleApproach()` has `static uint32_t lastReadFailLog`, `static uint32_t lastReadingLog`, `static uint32_t lastDisplayUpdate`, `handleSummary()` has `static bool summaryRendered`, `handleFailed()` has `static bool failedRendered`.

These persist across calibration sessions and across CalibrationManager instances. The render flags (`introRendered`, `summaryRendered`, `failedRendered`) are reset only on the normal exit path. If the state machine is interrupted (e.g., cancel during intro), `introRendered` remains `true` and the next calibration silently skips the intro render. These should be instance members reset in `transitionTo()`.

#### 4. Signal Processing Correctness

**a) DirectionDetector baseline uses `getMax()`, not mean or robust statistic:**
`recalculateThreshold()` calls `baselineBuffer.getMax()` as the base for threshold calculation. A single noise spike during the baseline window permanently elevates the threshold until that sample rotates out of the 200-sample ring buffer (~200ms at 1kHz). A trimmed mean or median would be more resilient to transient spikes while still capturing the noise ceiling.

**b) DirectionDetector confidence scoring has hardcoded, un-tunable constants:**
The confidence formula (lines 261–271) uses: `50.0f` (gap normalization), `100.0f` (signal normalization), `0.6f`/`0.4f` (gap vs signal weights), `0.15f` (multi-module consensus boost). These are tuning parameters that cannot be adjusted without recompiling. They should live in `DetectorConfig` alongside the other tuning knobs.

**c) MLDetector baseline is one-shot, not adaptive:**
`updateBaseline()` accumulates exactly `ML_BASELINE_READINGS` (50) samples, then transitions to READY permanently. DirectionDetector continuously updates its baseline during IDLE, adapting to environmental drift (ambient light changes, temperature). MLDetector never recalibrates — if conditions change mid-session, the trigger threshold becomes stale.

**d) MLDetector forward-fill treats `0.0f` as "no data" (semantic bug):**
In `prepareInput()` (line 421): `if (input[curIdx] == 0.0f)` → propagate from previous timestep. A legitimate zero-proximity reading is indistinguishable from an unfilled grid cell. VCNL4040 proximity values are typically non-zero when the sensor is active, so this works in practice, but it's semantically wrong and fragile. A sentinel value (`-1.0f`) or a separate validity array would be correct.

**e) MLDetector side aggregation naming is inverted from DirectionDetector:**
MLDetector maps "Side A" → positions 1,3,5 (S2 sensors) and "Side B" → positions 0,2,4 (S1 sensors). DirectionDetector maps posA → even positions (S1) and posB → odd positions (S2). The ML model was trained with whatever convention was used, so detection works, but the naming inconsistency between the two detectors is a maintenance hazard. If someone "fixes" the naming to match DirectionDetector, they'll break the ML pipeline.

**f) DirectionDetector center-of-mass precision loss:**
`weightedSum += smoothed * timestamp` accumulates `float(proximity) × uint32_t(ms)`. For a 30-second session (timestamp ~30,000) with proximity ~500, each term is ~15,000,000. Over a wave of ~100 samples, `weightedSum` reaches ~1.5e9. Single-precision float has ~7 significant digits, so the center-of-mass calculation loses ~1ms of precision at this range. Not a practical problem at current session lengths, but `double` would eliminate it.

#### 5. Memory Safety

**a) `StatsAccumulator::sumSq` overflow — silent calibration data corruption:**
`sumSq` is `uint32_t`. It accumulates `(uint32_t)value * value` where `value` is `uint16_t` (max 65,535). A single `value²` is up to ~4.29e9, which fits in `uint32_t`. But `sumSq` accumulates across samples. At 600ms baseline capture with reads arriving continuously (~100+ samples), `sumSq` can reach ~4.3e11 — overflowing `uint32_t` at ~4.29e9. The overflow wraps silently, producing garbage in `getStdDev()`. **Fix: change `sumSq` to `uint64_t`.**

Similarly, `sum * sum` in `getStdDev()` (`sum * sum / count`) overflows `uint32_t` if `sum > 65,535` — which happens at ~4 samples of maximum signal. **Fix: cast to `uint64_t` before multiplication.**

**b) MLDetector `prepareInput()` writes to input tensor without bounds check:**
`memset(input, 0, totalElements * sizeof(float))` writes `ML_WINDOW_MS × ML_NUM_POSITIONS × 4 = 7,200 bytes` to `inputTensor_->data.f`. If the model's input tensor shape doesn't match these constants (model updated but constants not), this is a buffer overflow into the tensor arena. Add a check: `assert(inputTensor_->bytes >= totalElements * sizeof(float))`.

**c) MLDetector `lastResult_` is uninitialized until first detection:**
`DetectionResult lastResult_` in the header has no constructor and no default member initializers. If `getResult()` is called before any detection (perhaps due to a logic error in the caller), it returns an uninitialized struct. `DetectionResult` should have a default constructor or aggregate initializers.

**d) MLDetector ring buffer is 8KB in static storage:**
`MLSensorFrame ringBuffer_[512]` — each frame is 16 bytes (4 + 6×2 = 16), total 8,192 bytes. This lives in the MLDetector object (global instance), so it's in BSS. Acceptable for ESP32-S3, but worth noting if memory pressure increases. PSRAM allocation would be an option.

**e) CalibrationManager `readPCB()` suppresses partial failures:**
If one of the two sensors on a PCB fails (`success1 = false, success2 = true`), the function returns only the reading from the working sensor. The caller treats this as a valid PCB reading, but it's half the expected signal magnitude. This silently skews calibration thresholds downward for the affected PCB. At minimum, log a warning; ideally, require both sensors to succeed.

#### 6. Magic Numbers

**DirectionDetector:**

| Value | Location | Should be |
|---|---|---|
| `50` | cpp line 39 | **`BASELINE_RECALC_INTERVAL`** — how often to recompute threshold during baseline updates |
| `50.0f` | cpp line 261 | **`CONFIDENCE_GAP_NORMALIZATION`** — or move to `DetectorConfig` |
| `100.0f` | cpp line 263 | **`CONFIDENCE_SIGNAL_NORMALIZATION`** — or move to `DetectorConfig` |
| `0.6f` / `0.4f` | cpp line 264 | **`CONFIDENCE_GAP_WEIGHT`** / **`CONFIDENCE_SIGNAL_WEIGHT`** |
| `0.15f` | cpp lines 268, 270 | **`CONFIDENCE_CONSENSUS_BOOST`** |
| `3` | cpp line 155 | **`NUM_MODULES`** (derived from `NUM_SENSORS / 2`) |
| `SMOOTH_SIZE = 10` | header line 157 | Named but not configurable — consider making it a `DetectorConfig` field |
| `BASELINE_SIZE = 200` | header line 158 | Named but not configurable |

**MLDetector:**

| Value | Location | Should be |
|---|---|---|
| `100` | cpp line 271 | **`ML_MIN_FRAMES_FOR_INFERENCE`** — minimum ring buffer frames |
| `3` | cpp lines 172, 186 | **`ML_SMOOTH_WINDOW`** — smoothing window size (hardcoded, unlike DirectionDetector) |
| `8` | header line 91, resolver template | **`ML_MAX_OPS`** — maximum TFLite op count |

**CalibrationManager:**

| Value | Location | Should be |
|---|---|---|
| `50` | cpp line 148 | **`CAL_DISPLAY_UPDATE_INTERVAL_MS`** |
| `100` | cpp line 276 | **`CAL_APPROACH_DISPLAY_INTERVAL_MS`** |
| `500` | cpp line 204 | **`CAL_READING_LOG_INTERVAL_MS`** |
| `1000` | cpp lines 185, 378 | **`CAL_READ_FAIL_LOG_INTERVAL_MS`** / **`CAL_FAILED_MIN_DISPLAY_MS`** |
| `1500` | cpp lines 301, 396 | Already `CAL_SUCCESS_DISPLAY_MS` for one occurrence, but `1500` is hardcoded in two other places |
| `5` | CalibrationData.h line 68 | **`CAL_OVERLAP_MARGIN`** — threshold margin for signal/noise overlap case |
| `200` | CalibrationData.h line 151 | **`CAL_DEFAULT_LED_CURRENT`** (duplicated from main.cpp's default) |

**CalibrationManager button GPIOs** (`CAL_BUTTON_TRIGGER = 0`, `CAL_BUTTON_CANCEL = 14`) should come from `pin_config.h` for consistency with other GPIO assignments.

#### 7. API Design

**a) No shared detector interface (see §2):**
The most impactful API problem. Both detectors have identical public method signatures but no formal interface, preventing polymorphic use.

**b) `getResult()` has non-obvious side effects in both detectors:**
DirectionDetector's `getResult()` sets `_detectedModule` (line 273), which changes the return values of the legacy telemetry accessors (`getSmoothedA()` etc.). MLDetector's `getResult()` clears `detectionReady_`, making the result consume-once. Neither behavior is documented or obvious from the method signature.

**c) `hasDetection()` + `getResult()` is a TOCTOU pattern:**
If readings arrive between `hasDetection()` returning true and `getResult()` being called, DirectionDetector's wave states could change (stale waves expire in `updateSensorWave()`). Currently safe because both calls happen sequentially in the same loop iteration, but the API doesn't enforce this. A single `tryGetResult(DetectionResult &out) → bool` would be safer.

**d) CalibrationManager `delay()` calls violate non-blocking contract:**
`update()` is designed as a cooperative state machine called from `loop()`, but three code paths call `delay()` for 1,500ms each: `handleApproach()` success (line 254), `handleApproach()` timeout (line 301), and `handleCancelled()` (line 396). During these delays, the entire main loop stalls — no MQTT, no display refresh, no button checks. These should be timer-based transitions (add `SUCCESS_DISPLAY` / `FAILURE_DISPLAY` sub-states with timestamp checks).

**e) CalibrationManager `getCalibration()` returns mutable reference:**
Returns `DeviceCalibration &` (non-const), allowing external code to mutate calibration data while a calibration is in progress. Should return `const DeviceCalibration &` for read-only access, with mutation only through CalibrationManager's own methods.

**f) CalibrationManager `transitionTo()` uses a lambda for logging (lines 567–573):**
Temporarily swaps `_state` to get the new state's name via `getStateName()`. Unnecessarily clever. A `static stateToString(CalibrationState)` method would be straightforward.

**g) Global instances (`deviceCalibration`, `calibrationManager`) declared in .cpp:**
Classic singleton-via-globals pattern. Prevents unit testing, couples all consumers to a single instance, and makes lifetime management implicit. The `deviceCalibration` global is written by CalibrationManager at completion (line 347: `deviceCalibration = _calibration`) and read by DirectionDetector via pointer — the data flow is hidden.

#### 8. Dead Code & Unnecessary Includes

- **`DirectionDetector.h` line 6: `#include <vector>`** — `std::vector` is never used in DirectionDetector. Remove.
- **`DirectionDetector.h` line 6: `#include "../sensor/SensorManager.h"`** — Only needed for `SensorReading` and `NUM_SENSORS`. This pulls the entire SensorManager definition (including its Adafruit dependencies) into every file that includes the detector. Extract `SensorReading` and `NUM_SENSORS` into a lightweight `SensorTypes.h`.
- **`DirectionDetector::flushReading()`** — Empty method kept "for interface compatibility." If both detectors share `IDetector`, this can be properly documented as optional.
- **`DetectorConfig::minGapForConfidence` and `DetectorConfig::minSignalForConfidence`** (header lines 79–80) — Declared but never referenced anywhere in the codebase. Dead config fields.
- **`MLDetector::getFrameCount()`** (header line 137) — Defined inline in the header, never called externally or internally.
- **`CalibrationManager::configureSensorForCalibration()`** (cpp lines 676–681) — Empty method with a comment saying it does nothing. Remove.

#### 9. State Machine Design (CalibrationManager)

The `CalibrationState` enum encodes the PCB number in each state name (`BASELINE_PCB1`, `BASELINE_PCB2`, `BASELINE_PCB3`, `APPROACH_PCB1`, `APPROACH_PCB2`, `APPROACH_PCB3`), resulting in 12 enum values where 8 would suffice. `_currentPCB` already tracks which PCB is active, making the per-PCB states redundant. This causes:

- `transitionTo()` has a 6-case switch just to set `_currentPCB` and reset stats — the PCB index could be computed from the generic state + `_currentPCB`.
- `getNextState()` is a 8-case switch that encodes a linear sequence. With generic states, next-state logic would be: if `_currentPCB < 3`, increment PCB and go to BASELINE; else go to SUMMARY.
- `getPCBForState()` exists solely to reverse the encoding.

A cleaner design: `{IDLE, INTRO, BASELINE, APPROACH, SUCCESS_DISPLAY, SUMMARY, COMPLETE, FAILED, CANCELLED}` + `_currentPCB`. This also creates a natural place for the `SUCCESS_DISPLAY` sub-state that eliminates the `delay()` call.

#### 10. Naming & Style

**a) Private member naming — two conventions in the same layer:**
DirectionDetector and CalibrationManager use `_prefix` (`_calibration`, `_useCalibration`, `_sensorMgr`, `_state`). MLDetector uses `suffix_` (`modelReady_`, `inputTensor_`, `ringBuffer_`, `state_`). Pick one convention and apply it consistently. `suffix_` is Google C++ style and avoids potential conflicts with reserved identifiers (leading underscore + capital letter is reserved in C++).

**b) Struct member naming — camelCase vs snake_case:**
`DetectionResult` uses camelCase (`centerOfMassA`, `waveDurationA`, `comGapMs`). `PCBCalibration` and `DeviceCalibration` use snake_case (`baseline_min`, `signal_max`, `multi_pulse`). `MLSensorFrame` uses snake_case (`timestamp_ms`). `DetectorConfig` uses camelCase (`baselineReadings`, `peakMultiplier`). Detection-layer types should use a single convention.

**c) Constants — three different patterns:**
- `DetectorConfig` stores tuning parameters as struct fields with defaults — configurable at runtime.
- MLDetector uses `static constexpr` with `ML_` prefix (`ML_WINDOW_MS`, `ML_BASELINE_READINGS`) — compile-time only.
- CalibrationManager uses `#define` with `CAL_` prefix (`CAL_INTRO_DURATION_MS`, `CAL_BASELINE_DURATION_MS`) — preprocessor macros, no type safety.

`static constexpr` is preferred over `#define` in C++. Runtime-configurable parameters should be in config structs (like `DetectorConfig`). Compile-time constants should use `static constexpr` with a consistent prefix per module.

#### 11. Decomposition Recommendations

Listed in priority order (highest impact first):

| # | Extraction | What it achieves | Est. lines saved | Effort | Notes |
|---|---|---|---|---|---|
| 1 | **`IDetector` interface** | Shared base for DirectionDetector and MLDetector. Enables polymorphic use in main.cpp, eliminates `if (useMLDetection)` duplication. | ~0 (enables savings in main.cpp) | Small | Define in `DetectionTypes.h`. Both detectors inherit from it. |
| 2 | **`DetectionTypes.h`** | Extract `Direction`, `DetectionResult`, `DetectorConfig`, `WaveState`, `DetectorState` out of `DirectionDetector.h`. Both detectors and main.cpp include only the types they need. | ~0 (decoupling) | Small | Quick win. Breaks the transitive include chain through SensorManager. |
| 3 | **`RingBuffer.h`** | Extract the generic `RingBuffer<T, SIZE>` template into a standalone utility header. Reusable by MLDetector (replace its manual ring buffer) and any future component. | ~60 from DirectionDetector.h | Small | Quick win. Add `getMean()` method to eliminate the manual sum loop in `getResult()`. |
| 4 | **Fix `StatsAccumulator` overflow** | Change `sumSq` to `uint64_t`, cast `sum * sum` to `uint64_t` in `getStdDev()`. | ~0 (correctness) | Trivial | **High priority** — currently produces corrupt calibration data. |
| 5 | **Eliminate `delay()` in CalibrationManager** | Replace 3 blocking `delay(1500)` calls with timer-based sub-states (`SUCCESS_DISPLAY`, `FAILURE_DISPLAY`, `CANCELLED_DISPLAY`). | ~0 (responsiveness) | Small | Fixes the non-blocking contract violation. Prerequisite for simplifying the state enum. |
| 6 | **Simplify CalibrationState enum** | Reduce from 12 to ~9 states by removing per-PCB variants. Use `_currentPCB` for sequencing. Eliminate `getPCBForState()`, simplify `getNextState()` and `transitionTo()`. | ~60 | Medium | Do after #5. Cleaner state machine, fewer switch cases. |
| 7 | **Replace `static` locals in CalibrationManager** | Move 7 `static` local variables to instance members. Reset them in `transitionTo()`. | ~0 (correctness) | Trivial | Fixes the stale-flag bug on interrupted calibrations. |
| 8 | **Extract TFLite lifecycle from MLDetector** | Move `init()`, `deinit()`, model loading, op registration, arena allocation into `TFLiteRuntime`. MLDetector delegates to it. | ~130 | Medium | Makes TFLite management reusable for future models. |
| 9 | **Unify trigger/baseline logic** | MLDetector's baseline + trigger duplicates DirectionDetector's approach. If MLDetector used DirectionDetector's trigger as its trigger source (or shared a common threshold tracker), ~100 lines of duplicated logic disappears. | ~100 | Medium | Requires careful alignment of the side A/B naming convention (see §4e). |
| 10 | **Move confidence constants to `DetectorConfig`** | Make the 5 hardcoded confidence-scoring parameters configurable. | ~0 (tunability) | Trivial | Quick win for detection tuning. |
| 11 | **Add `SensorTypes.h`** | Extract `SensorReading`, `NUM_SENSORS`, and sensor position constants out of `SensorManager.h` into a lightweight header. Breaks the heavy include chain. | ~0 (compile-time) | Small | Reduces coupling across the entire codebase. |

**Recommended execution order:** #4 (StatsAccumulator fix) → #2 (DetectionTypes.h) → #11 (SensorTypes.h) → #3 (RingBuffer.h) → #1 (IDetector) → #7 (static locals) → #5 (eliminate delay) → #6 (simplify state enum) → #10 (confidence constants) → #8 (TFLite extraction) → #9 (unify trigger).

**Key dependency:** Extraction #1 (IDetector) is the enabler for the main.cpp `DetectionController` extraction recommended in Batch 1. These should be scheduled together.

### Batch 4: Session & Data

**Files reviewed:** `SessionManager.cpp` (302 lines), `SessionManager.h` (132 lines), `DataTransmitter.cpp` (769 lines), `DataTransmitter.h` (85 lines), `PSRAMAllocator.h` (98 lines).

**The defining problems in this batch:** (1) DataTransmitter contains ~160 lines of identical calibration and config JSON serialization duplicated across 4 transmission paths, plus ~30 lines of device-ID-suffix extraction duplicated from SessionManager. (2) Proximity batch transmission with `BATCH_SIZE=25` and `delay(100)` between batches means a 30-second session (30,000 readings) blocks the main loop for **~120 seconds** while transmitting. (3) `SessionManager::finalizeSessionSummary()` uses `const_cast` to mutate a `const` parameter — undefined behavior if the pointed-to object is genuinely const. (4) `PSRAMAllocator` logs via `Serial.printf()` on every allocation/deallocation, injecting latency into the data pipeline whenever `std::vector` resizes.

#### 1. Single Responsibility Violations

**SessionManager** (434 total lines across .h/.cpp) performs 5 distinct jobs:

| Responsibility | Lines (approx) | Should live in |
|---|---|---|
| Session lifecycle (start, stop, state transitions) | ~50 | Core logic — good |
| Session ID generation (device-ID parsing + timestamp) | ~30 | Utility function or SessionIdGenerator |
| Dual-mode data buffering (proximity queue→buffer + interrupt events) | ~100 | Two distinct buffer strategies behind if/else |
| FreeRTOS queue management (create, drain, overflow counting) | ~50 | Tightly coupled with buffering — acceptable |
| Session summary finalization (statistics computation + logging) | ~50 | Partly belongs in the summary itself; the `const_cast` mutation belongs elsewhere |

The dual-mode pattern (proximity vs interrupt) permeates every method with `if (sessionType == SessionType::INTERRUPT_BASED)` branches. This is a textbook case for a strategy pattern — two buffer implementations behind a common interface — but at 302 lines it's not urgent to extract.

**DataTransmitter** (854 total lines across .h/.cpp) performs 6 distinct jobs:

| Responsibility | Lines (approx) | Should live in |
|---|---|---|
| Proximity batch JSON serialization + MQTT publish | ~150 | **`ProximitySerializer`** or shared helper |
| Interrupt batch JSON serialization + MQTT publish | ~120 | **`InterruptSerializer`** or shared helper |
| Live Debug JSON batch serialization + MQTT publish | ~160 | Shares ~90% of proximity serializer |
| Live Debug binary packing + base64 encoding + MQTT publish | ~180 | **`BinarySerializer`** — distinct enough to justify extraction |
| Session summary serialization + retry publish | ~45 | Could stay, but retry logic is unique here |
| Config/calibration/metadata JSON construction (duplicated across all paths) | ~160 (4×~40) | **Extract to shared helpers** |

DataTransmitter is the file that must be split in this batch. Its size (769 lines) exceeds the 600-line "must split" threshold, and the duplication drives most of the bloat.

#### 2. Code Duplication (Critical)

**a) Calibration JSON serialization — duplicated 4 times (~20 lines each):**
The pattern `if (deviceCalibration.isValid()) { build JSON with timestamp, multi_pulse, integration_time, thresholds array }` appears identically in:
- `transmitBatch()` (lines 86–109)
- `transmitInterruptBatch()` (lines 245–268)
- `transmitLiveDebugCapture()` (lines 460–478)
- `transmitLiveDebugCaptureBinary()` (lines 659–677)

~80 lines of identical code. A single `serializeCalibration(JsonDocument &doc)` helper eliminates all four instances.

**b) Sensor config JSON serialization — duplicated 3 times (~15 lines each):**
The `vcnl4040_config` JSON object with 9 fields (`sample_rate_hz`, `led_current`, `integration_time`, `duty_cycle`, `multi_pulse`, `high_resolution`, `read_ambient`, `i2c_clock_khz`, `actual_sample_rate_hz`) appears identically in:
- `transmitBatch()` (lines 73–83)
- `transmitLiveDebugCapture()` (lines 447–456)
- `transmitLiveDebugCaptureBinary()` (lines 646–655)

~45 lines of identical code. A single `serializeConfig(JsonDocument &doc, const SensorConfiguration *config)` helper eliminates all three.

**c) Reading JSON serialization — duplicated 2 times:**
The per-reading JSON object construction (`ts`, `pos`, `pcb`, `side`, `prox`, `amb`) appears in `transmitBatch()` (lines 115–126) and `transmitLiveDebugCapture()` (lines 483–494). A shared `serializeReading()` helper or a single `serializeReadingsArray()` function eliminates both.

**d) Device ID suffix extraction — tripled across the codebase:**
The `lastIndexOf('-')` / `secondLastDash` / `substring()` pattern appears in:
- `SessionManager::setDeviceId()` (lines 19–24)
- `DataTransmitter::transmitLiveDebugCapture()` (lines 393–398)
- `DataTransmitter::transmitLiveDebugCaptureBinary()` (lines 560–565)

A single utility function `extractDeviceSuffix(const String &fullId)` eliminates all three. Better yet, DataTransmitter should get the short device ID from SessionManager rather than recomputing it.

**e) Session summary JSON serialization — duplicated 2 times:**
The full summary JSON construction (total_cycles, queue_drops, buffer_drops, per-sensor arrays, etc.) appears in `transmitLiveDebugCaptureBinary()` (lines 681–698) and `transmitSessionSummary()` (lines 737–754). A shared `serializeSummary()` helper eliminates the duplication.

#### 3. Concurrency Safety

**a) `dataBuffer` is safely single-core, but the invariant is undocumented and unenforced:**
The data flow is: Core 0 → `xQueueSend(dataQueue)` → Core 1's `processQueue()` → `dataBuffer.push_back()`. The FreeRTOS queue provides the cross-core synchronization. All `dataBuffer` reads (detection loops, transmission, clear) happen on Core 1. This is correct — but the safety depends entirely on no one calling `getDataBuffer()` from Core 0. `getDataBuffer()` returns a mutable reference with no documentation of this constraint. A comment or, better, making `processQueue()` the only writer via a private accessor would enforce it.

**b) `activeSummary` pointer in DataTransmitter — unprotected shared state:**
`setSessionSummary(SessionSummary*)` stores a raw pointer to SessionManager's `sessionSummary`. During transmission, `transmitBatch()` increments `activeSummary->total_readings_transmitted` and `total_batches_transmitted`. If `SessionManager::startSession()` calls `sessionSummary.reset()` during an ongoing transmission (e.g., a rapid stop-then-start sequence), the counters are zeroed mid-transmission. Currently safe because stop-transmit-start is sequential on Core 1, but the pointer-sharing pattern is fragile and undocumented.

**c) `extern DeviceCalibration deviceCalibration` — global accessed without protection:**
DataTransmitter reads `deviceCalibration` (4 occurrences) during JSON serialization. CalibrationManager writes to it at calibration completion. Both are on Core 1, so this is safe today. But the coupling is hidden — DataTransmitter has no explicit dependency on calibration data in its constructor or API. It silently reaches for a global. This should be injected via a const pointer/reference in the constructor or per-call.

**d) `extern bool serialStudioEnabled` in SessionManager.cpp (line 3):**
Same hidden global coupling pattern documented in Batches 2 and 3. Written by Core 1 (command handler), read by Core 1 (`clearBuffer()`). Safe but fragile. Should be injected via config.

**e) `SessionSummary` is written by multiple components without coordination:**
The `SessionSummary` struct has fields written by:
- SensorManager (Core 0): `total_cycles`, `readings_collected[]`, `i2c_errors[]`, `queue_drops`
- SessionManager (Core 1): `buffer_drops`, `duration_ms`, `measured_cycle_rate_hz`, etc.
- DataTransmitter (Core 1): `total_readings_transmitted`, `total_batches_transmitted`

The Core 0 writes to `total_cycles`, `readings_collected[]`, `i2c_errors[]`, and `queue_drops` happen concurrently with Core 1 reading them for finalization and transmission. Individual uint32_t writes are atomic on ESP32 (Xtensa LX7), so torn reads won't occur. But there's no memory barrier ensuring Core 1 sees Core 0's latest values when `finalizeSessionSummary()` is called. In practice, calling `stopCollection()` before finalization provides an implicit barrier (the task stop handshake flushes the write buffer), but this ordering requirement is undocumented.

#### 4. Memory Safety

**a) `const_cast` in `finalizeSessionSummary()` — undefined behavior risk (line 280):**
```cpp
const_cast<SensorConfiguration *>(config)->actual_sample_rate_hz = sessionSummary.measured_cycle_rate_hz;
```
The function signature promises `const SensorConfiguration *config`, then mutates through it. If the caller ever passes a genuinely `const` object, this is undefined behavior per the C++ standard. Even when it works, it violates the API contract. The measured rate should be communicated back through the return value, an out-parameter, or by making the parameter non-const.

**b) `DynamicJsonDocument` without overflow check in proximity and interrupt paths:**
`transmitBatch()` allocates `DynamicJsonDocument doc(8192)`. The first batch includes sensor metadata (6 sensors × ~80 bytes), config (~200 bytes), calibration (~300 bytes), plus 25 readings × ~100 bytes. Total could approach 5–6KB — within the 8KB budget, but with no safety margin if more sensors or config fields are added. The live debug path (line 498) correctly checks `doc.overflowed()`. The proximity and interrupt paths don't.

**c) No bounds validation on `startIdx + count` in live debug transmission:**
`transmitLiveDebugCapture()` and `transmitLiveDebugCaptureBinary()` access `readings[startIdx + offset + i]` without verifying `startIdx + count <= readings.size()`. The caller is responsible for bounds-checking, but neither the API documentation nor assertions enforce this. An out-of-bounds access on the PSRAM-backed vector would read garbage memory silently (no bounds checking in release builds).

**d) `base64Buf` lifetime depends on synchronous publish (lines 641–709):**
`transmitLiveDebugCaptureBinary()` stores a pointer to `base64Buf` in the JSON doc (`doc["readings_b64"] = (const char *)base64Buf`), then calls `publishDataStreaming(doc)`, then `free(base64Buf)`. ArduinoJson stores `const char*` by reference (zero-copy), so the doc holds a dangling pointer after `free()`. Currently safe because `publishDataStreaming()` serializes synchronously before returning. But the safety is an undocumented assumption about PubSubClient's internals — any refactoring that defers serialization would introduce use-after-free.

**e) `PSRAMAllocator::allocate()` logs on every allocation — latency injection:**
`Serial.printf()` in `allocate()` (line 56) and `deallocate()` (line 67) can take 1–10ms depending on serial buffer state. `std::vector::reserve()` calls `allocate()` once (acceptable), but if a `push_back()` triggers reallocation (reserve wasn't large enough, or `clear()` + `reserve()` sequence), the serial print fires during the hot data path. For `interruptBuffer` (no PSRAM allocator, moot) and `dataBuffer` (PSRAM allocator), the `reserve(MAX_BUFFER_SIZE)` in `startSession()` should prevent reallocation. But `clearBuffer()` calls `clear()` which does NOT release capacity — fine, but if the vector was never reserved (e.g., session started in interrupt mode, then switched to proximity without restart), the first `push_back()` allocates with a log. This logging should be compile-time conditional (`#ifdef DEBUG_PSRAM`).

**f) `xQueueCreate(1000, sizeof(SensorReading))` — undersized for peak rate:**
At 6 sensors × 1000 Hz = 6,000 readings/sec, the queue holds ~167ms of data. If `processQueue()` is delayed (e.g., during a slow MQTT publish with `delay(100)` between batches), the queue overflows and `queue_drops` increment. The queue size should be a named constant and tuned to cover the worst-case processing gap.

#### 5. Error Handling

**a) Transmission failure = data loss (no retry, no persistence):**
`transmitProximitySession()` (line 192) and `transmitInterruptSession()` (line 356) return `false` immediately on the first failed batch. No retry of the failed batch, no indication of how many batches succeeded, and the caller (main.cpp) clears the buffer — all remaining data is lost. The session summary has already been partially updated with transmission counts. Contrast with `transmitSessionSummary()` which has 3-attempt retry logic — inconsistent.

**b) `delay()` between batches blocks the entire system:**
- Proximity: `delay(100)` × 1,200 batches (30,000 readings ÷ 25) = **120 seconds** of blocking
- Interrupt: `delay(50)` × batches
- Live Debug JSON: `delay(20)` × batches
- Summary retry: `delay(500)` × 3 attempts

During these blocking delays, no MQTT keepalive processing occurs. If the MQTT broker has a keepalive timeout shorter than the total transmission time, the connection drops mid-transmission. The `delay()` calls should be replaced with cooperative yielding (return to `loop()`, resume next batch on next iteration) or at minimum use `mqttManager->loop()` between batches to maintain the connection.

**c) `processQueue()` gated on `COLLECTING` state (line 117):**
If `processQueue()` is called after `stopSession()` (which transitions to `UPLOADING`), the state check returns early and queue contents are lost. The call in `stopSession()` (line 94) processes the queue *before* the state transition — correct. But the guard in `processQueue()` is misleading: it suggests the method can be safely called at any time, when in fact it silently drops data unless state is `COLLECTING`.

**d) Queue creation failure logged but not recovered:**
`SessionManager()` constructor (line 10–13) logs if `xQueueCreate()` fails but stores `NULL` in `dataQueue`. Later, `processQueue()` calls `xQueueReceive(dataQueue, ...)` with a `NULL` handle — undefined behavior on FreeRTOS (likely crash). Should either retry allocation or prevent session start when the queue is `NULL`.

#### 6. API Design

**a) `transmitBatch()` parameter explosion — 8 parameters:**
```cpp
bool transmitBatch(const String &sessionId, const String &deviceId,
                   unsigned long startTime, unsigned long duration,
                   std::vector<...> &readings, size_t offset, size_t count,
                   const std::vector<SensorMetadata> *sensorMetadata,
                   const SensorConfiguration *config);
```
Six of these 8 parameters are properties of the session. The method should take `const SessionManager &session` and extract what it needs, or use a lightweight `TransmissionContext` struct.

**b) `transmitLiveDebugCapture()` — 7 parameters, distinct from the session-based API:**
Takes raw buffer references, indices, strings, and a float. This is a different interface shape from `transmitSession()` despite doing the same fundamental job (serialize readings + publish). A unified `TransmissionRequest` struct would normalize both paths.

**c) Public API exposes batch-level methods:**
`transmitBatch()` and `transmitInterruptBatch()` are `public` but are implementation details of session-level transmission. External callers should only use `transmitSession()`, `transmitLiveDebugCapture()`, `transmitLiveDebugCaptureBinary()`, and `transmitSessionSummary()`. The batch methods should be `private`.

**d) Two live debug transmission paths with different APIs:**
`transmitLiveDebugCapture()` doesn't take a `SessionSummary` and requires a separate `transmitSessionSummary()` call. `transmitLiveDebugCaptureBinary()` takes `const SessionSummary &` and inlines it. The caller must know which path to use and what follow-up calls to make. A unified interface would hide this.

**e) `getDataBuffer()` returns mutable reference to internal PSRAM vector:**
Allows external callers to mutate the buffer contents without SessionManager's knowledge. The detection loops, Serial Studio output, and DataTransmitter all hold mutable references. For read-only consumers (detection, Serial Studio), a `const` overload should be the default. For DataTransmitter (which shouldn't need mutation), `const` is sufficient.

**f) `SAMPLE_RATE_HZ` macro used as transmission metadata (DataTransmitter line 49):**
`doc["sample_rate"] = SAMPLE_RATE_HZ;` uses the compile-time constant `1000`, but the actual sample rate is configurable via `config->sample_rate_hz`. The same batch also includes `configObj["sample_rate_hz"] = config->sample_rate_hz` in the config metadata. If the configured rate differs from 1000, the consumer gets conflicting values. The batch-level `sample_rate` field should use `config->actual_sample_rate_hz` (the measured rate) or `config->sample_rate_hz` (the configured rate), not the compile-time constant.

#### 7. Magic Numbers

**DataTransmitter:**

| Value | Location(s) | Should be |
|---|---|---|
| `8192` | lines 42, 220 | **`JSON_DOC_SIZE_BATCH`** |
| `32768` | line 420 | **`JSON_DOC_SIZE_LIVE_DEBUG`** |
| `8192` | line 618 | **`JSON_DOC_SIZE_BINARY`** (different from batch — both are 8192 but for different reasons) |
| `4096` | line 730 | **`JSON_DOC_SIZE_SUMMARY`** |
| `9` | lines 578, 589 | **`BINARY_READING_SIZE`** — the packed struct size per reading |
| `100` | line 198 | **`PROXIMITY_BATCH_DELAY_MS`** |
| `50` | line 363 | **`INTERRUPT_BATCH_DELAY_MS`** |
| `500` | line 765 | **`SUMMARY_RETRY_DELAY_MS`** |
| `3` | line 757 | **`SUMMARY_MAX_RETRIES`** |
| `200` | line 142 | Minor — debug substring length |
| `1000` | SAMPLE_RATE_HZ macro used at line 49, 429, 628 | Should use config value, not compile-time constant |

**SessionManager:**

| Value | Location(s) | Should be |
|---|---|---|
| `1000` | line 8 | **`DATA_QUEUE_SIZE`** — critical tuning parameter |
| `1000` | line 153 | **`BUFFER_LOG_INTERVAL`** — "every 1000 samples" status print |

#### 8. Dead Code & Unnecessary Includes

- **`SessionManager.h` line 5: `#include <ArduinoJson.h>`** — SessionManager never uses ArduinoJson. No JSON parsing or serialization in either the header or the implementation. Remove.
- **`SessionManager.h` line 7: `#include "../sensor/SensorManager.h"`** — Only needed for `SensorReading`, `SensorMetadata`, `NUM_SENSORS`, and `SAMPLE_RATE_HZ`. Pulls the entire SensorManager class definition (including its Adafruit dependencies) into every file that includes SessionManager.h. This creates a transitive include chain: `DataTransmitter.h` → `SessionManager.h` → `SensorManager.h` → `Adafruit_VCNL4040.h`. Should be replaced with a lightweight `SensorTypes.h` (recommended in Batch 3, extraction #11).
- **`SessionManager.h` line 8: `#include "../interrupt/InterruptManager.h"`** — Only needed for `InterruptEvent` type. Pulls the entire InterruptManager class (357-line header with FreeRTOS internals, mux controller, VCNL4040 driver). Should forward-declare or extract `InterruptEvent` into a lightweight types header.
- **`DataTransmitter.h` line 8: `#include "../sensor/SensorConfiguration.h"`** — Needed, but comes transitively through `SessionManager.h` → `SensorManager.h` already. The explicit include is harmless but the transitive chain should be broken.

#### 9. PSRAMAllocator Design

**a) Logging in allocator is a latency hazard (lines 56–58, 67–68):**
`Serial.printf()` fires on every `allocate()` and `deallocate()`. `std::vector::reserve()` triggers one `allocate()` — acceptable. But `clear()` followed by `reserve()` triggers `deallocate()` + `allocate()` — two serial prints. More critically, if the vector was never reserved and `push_back()` triggers geometric growth (1 → 2 → 4 → 8 → ... → 30,000), each reallocation logs twice (deallocate old + allocate new). That's ~30 serial prints during what should be a hot-path operation. This should be `#ifdef DEBUG_PSRAM` conditional.

**b) Missing `max_size()` implementation:**
The C++11 allocator concept includes `max_size()`. Some STL implementations call it during `reserve()` to validate the requested size. Should return `heap_caps_get_largest_free_block(MALLOC_CAP_SPIRAM) / sizeof(T)`. Not currently causing issues, but technically incomplete.

**c) Deprecated C++17 members present (acceptable for now):**
`construct()` and `destroy()` are deprecated in C++17 (handled by `std::allocator_traits`). ESP32 Arduino uses C++11/14, so these are still needed. No action required unless the toolchain upgrades.

**d) Equality operators are correct:**
Always returning `true` is correct for a stateless allocator — containers with `PSRAMAllocator` can freely swap and move-assign. Good.

#### 10. Decomposition Recommendations

Listed in priority order (highest impact first):

| # | Extraction | What it achieves | Est. lines saved | Effort | Notes |
|---|---|---|---|---|---|
| 1 | **Extract JSON serialization helpers** | `serializeCalibration()`, `serializeConfig()`, `serializeReadingsArray()`, `serializeSummary()` as private methods or free functions. Eliminates 4× calibration duplication, 3× config duplication, 2× readings duplication, 2× summary duplication. | ~200 | Small | Highest impact per effort. No structural change, just DRY. |
| 2 | **Make batch methods private** | Move `transmitBatch()` and `transmitInterruptBatch()` from `public` to `private`. | ~0 (API clarity) | Trivial | Quick win. Clarifies the public interface. |
| 3 | **Extract `BinarySerializer`** | Move `transmitLiveDebugCaptureBinary()` (180 lines) into a dedicated class or at minimum a separate file. The binary packing + base64 encoding is a distinct concern from JSON serialization. | ~180 | Small | Reduces DataTransmitter to ~550 lines. The binary path could also be a strategy class. |
| 4 | **Fix `const_cast` in `finalizeSessionSummary()`** | Either make the config parameter non-const, or return the measured rate as part of the summary and let the caller update the config. | ~0 (correctness) | Trivial | Eliminates undefined behavior risk. |
| 5 | **Replace `delay()` with cooperative batching** | Instead of blocking `delay(100)` between batches, return to `loop()` and resume transmission on the next iteration. Track batch offset as member state. Alternatively, call `mqttManager->loop()` between batches to maintain keepalive. | ~0 (responsiveness) | Medium | Fixes the 120-second blocking issue. Major reliability improvement. |
| 6 | **Guard `dataQueue == NULL`** | Add null check before `xQueueReceive()` in `processQueue()`, and prevent `startSession()` if queue is NULL. | ~5 | Trivial | Prevents crash on allocation failure. |
| 7 | **Add `doc.overflowed()` checks** | Add overflow detection to `transmitBatch()` and `transmitInterruptBatch()` matching the pattern already used in `transmitLiveDebugCapture()`. | ~10 | Trivial | Prevents silent data truncation. |
| 8 | **Extract `SensorTypes.h`** | Move `SensorReading`, `SensorMetadata`, `NUM_SENSORS` out of `SensorManager.h` into a lightweight header. Break the transitive include chain `DataTransmitter → SessionManager → SensorManager → Adafruit`. | ~0 (compile-time, decoupling) | Small | Reinforces Batch 3 recommendation #11. Unblocks cleaner headers across the codebase. |
| 9 | **Extract device-ID suffix utility** | Single `extractDeviceSuffix(const String &fullId)` function shared by SessionManager and DataTransmitter. | ~20 | Trivial | Eliminates triple duplication. |
| 10 | **Conditional PSRAM logging** | Wrap `Serial.printf()` in `PSRAMAllocator::allocate()` and `deallocate()` with `#ifdef DEBUG_PSRAM`. | ~0 (performance) | Trivial | Quick win. Eliminates latency risk. |
| 11 | **Add batch retry logic** | Add per-batch retry (1–2 attempts) in `transmitProximitySession()` and `transmitInterruptSession()` before failing the entire session. | ~20 | Small | Reduces data loss from transient MQTT failures. |
| 12 | **Use config sample rate instead of `SAMPLE_RATE_HZ` macro** | Replace `doc["sample_rate"] = SAMPLE_RATE_HZ` with `doc["sample_rate"] = config->actual_sample_rate_hz` (or `config->sample_rate_hz` as fallback). | ~0 (correctness) | Trivial | Prevents conflicting sample rate values in transmitted data. |

**Recommended execution order:** #4 (fix const_cast) → #10 (conditional PSRAM logging) → #6 (null guard) → #7 (overflow checks) → #12 (sample rate fix) → #2 (make batch methods private) → #9 (device-ID utility) → #1 (JSON serialization helpers) → #8 (SensorTypes.h, coordinate with Batch 3 #11) → #3 (BinarySerializer extraction) → #11 (batch retry) → #5 (cooperative batching).

**Key dependencies:**
- Extraction #8 (`SensorTypes.h`) is shared with Batch 3 recommendation #11 and Batch 2 recommendation #5. This should be a single coordinated extraction.
- Extraction #5 (cooperative batching) is the highest-impact reliability fix but requires the most careful implementation — the batch loop must become stateful, and main.cpp's stop-transmit-clear sequence needs to accommodate multi-iteration transmission.
- Extraction #1 (JSON helpers) is the highest-impact structural fix and enables #3 — do it first, then the binary serializer extraction becomes straightforward.

After these changes, DataTransmitter.cpp should drop from ~769 lines to ~350–400 lines: session-level orchestration, batch loop control, and delegation to serialization helpers. SessionManager stays roughly the same size (302 lines is within budget) but with cleaner interfaces and fixed safety issues.

### Batch 5: I/O & Peripherals

**Files reviewed:** `DisplayManager.cpp` (874 lines), `DisplayManager.h` (130 lines), `InterruptManager.cpp` (795 lines), `InterruptManager.h` (357 lines), `LEDController.cpp` (161 lines), `LEDController.h` (90 lines), `SerialStudioOutput.cpp` (198 lines), `SerialStudioOutput.h` (87 lines).

**The defining problems in this batch:** (1) DisplayManager is a 1,004-line monolithic renderer that knows about every screen in the system — init, session, calibration (8 methods, ~320 lines) — with no separation between rendering concerns. (2) InterruptManager's processing task busy-loops via `taskYIELD()` instead of sleeping on `xTaskNotifyFromISR()`, consuming all spare Core 1 CPU during interrupt monitoring. (3) `volatile bool` is used instead of `std::atomic<bool>` for ISR-to-task communication in InterruptManager (same pattern flagged in Batch 2). (4) LEDController redefines `LED_PIN 16` as a local macro instead of using `PIN_LED_STRIP_DATA` from `pin_config.h`, and includes `DirectionDetector.h` (pulling the entire sensor chain) just for the `Direction` enum.

#### 1. Single Responsibility Violations

**DisplayManager** (1,004 total lines across .h/.cpp) performs 5 distinct jobs:

| Responsibility | Lines (approx) | Should live in |
|---|---|---|
| Hardware initialization (power pins, TFT driver) | ~20 | Acceptable in DisplayManager |
| Init/boot screen rendering (progress bar, checkmarks, error display) | ~150 | **`InitScreen`** or kept inline |
| Session screen rendering (header, status/mode badges, config panel, messages) | ~250 | Core display logic — good |
| Calibration screen rendering (intro, baseline, approach, success, failed, summary, complete, cancelled) | **~320** | **`CalibrationScreen`** — called only by CalibrationManager |
| Legacy compatibility wrappers (`showBootScreen`, `updateStatus`, `showNetworkInfo`) | ~30 | Remove when callers are migrated |

The calibration screens are the dominant extraction target. Eight methods totaling ~320 lines are called exclusively by CalibrationManager. They handle their own layout arithmetic (per-method ad-hoc pixel positions), their own progress bars, and their own text centering — none of which shares layout constants with the session screen. Extracting these into a `CalibrationScreen` class (or a separate file that DisplayManager delegates to) would bring DisplayManager.cpp down to ~550 lines.

**InterruptManager** (1,152 total lines across .h/.cpp) performs 6 distinct jobs:

| Responsibility | Lines (approx) | Should live in |
|---|---|---|
| Hardware initialization (MuxController, GPIO pins, event queue) | ~35 | Acceptable in InterruptManager |
| Sensor calibration (baseline measurement via polling loop) | ~95 | Overlaps with CalibrationManager (Batch 3) — could share or delegate |
| Per-sensor configuration (threshold calculation from calibration, register programming, verify-readback) | ~125 | Core logic — good, but verbose due to serial debug output |
| ISR handling (3 trampolines + common handler) | ~30 | Core logic — good, properly minimal |
| FreeRTOS processing task (ISR flag polling, sensor debug polling) | ~80 | Core logic, but debug polling should be conditional |
| Event queue management (queue/dequeue/clear/stats) | ~50 | Could be a thin wrapper but not worth extracting at this size |

The header is the bigger concern at 357 lines. It defines 5 data types (`InterruptEventType`, `InterruptEvent`, `InterruptMode`, `InterruptConfig`, `InterruptSessionStats`) plus the full class. `InterruptEvent` is already needed by `SessionManager.h` (noted in Batch 4), so extracting these types into `InterruptTypes.h` would break the transitive include chain and shrink the header to ~100 lines.

**LEDController** (251 total lines) — well-scoped. Single responsibility (LED strip control + animation state). No splitting needed.

**SerialStudioOutput** (285 total lines) — well-scoped. Frame accumulation, CSV emission, rate tracking. No splitting needed.

#### 2. Concurrency Safety

**a) InterruptManager: `_monitoring` is `volatile bool`, not `std::atomic<bool>`:**
Written by Core 1 (`stopMonitoring()`), read by ISR context (`handleIsr()`) and the processing task (`processingTaskFunc()`). Same pattern as SensorManager's `stopRequested` (Batch 2). `volatile` does not guarantee memory ordering — `std::atomic<bool>` with `memory_order_relaxed` is the correct tool.

**b) InterruptManager: `_stats.isrCount++` in ISR context without synchronization:**
`isrCount` is a plain `uint32_t` incremented in `handleIsr()` (ISR context) and read by `getStats()` and `stopMonitoring()` on Core 1. On Xtensa LX7, a single-word read-modify-write is typically atomic in practice, but it's not guaranteed by C++. Should be `volatile uint32_t` at minimum, or `std::atomic<uint32_t>`.

**c) InterruptManager: `_processingTask = nullptr` race in task self-deletion (line 689):**
Same pattern flagged in SensorManager (Batch 2). The task sets `_processingTask = nullptr` then calls `vTaskDelete(NULL)`. Between those two instructions, `stopMonitoring()` could see `nullptr` and proceed while the task is still executing. The `stopMonitoring()` implementation polls with a 500ms timeout and force-deletes as fallback — functional but architecturally fragile. The proper pattern is a task notification or event group for the exit handshake.

**d) InterruptManager: `_isrPending[]` timestamp loss on rapid re-trigger:**
The ISR writes `_lastIsrTime[board]` unconditionally. If two ISRs fire on the same board before the processing task reads the flag, the first timestamp is overwritten. The processing task processes one event with the second timestamp — the first event's timing is lost. For direction detection where microsecond-level timing between sensors matters, this could degrade accuracy. A small ring buffer per board (e.g., 4 entries) would preserve rapid consecutive events.

**e) InterruptManager: processing task accesses I2C bus without coordination with SensorManager:**
The processing task (Core 1) reads sensors via `_mux.selectSensor()` + `_sensors[pos].readInterruptFlags()`. SensorManager's task (Core 0) also uses the I2C bus. The two cannot run simultaneously. Safety relies entirely on main.cpp never running both — neither class enforces the invariant. A shared I2C bus mutex or at minimum `assert(!sensorManager.isCollecting())` in `startMonitoring()` would catch violations.

**f) InterruptManager: debug polling changes MUX state during active monitoring:**
Lines 657-668 in `processingTaskFunc()` select a sensor via MUX and read proximity every 2 seconds. This changes the MUX state while the processing task may also need to handle an ISR event. The subsequent `processBoard()` call re-selects via `_mux.selectSensor()`, so the stale MUX state is overwritten — ultimately safe, but the debug poll adds I2C latency to the interrupt processing path.

**g) DisplayManager: all rendering is Core 1 only — correct but unenforced:**
`TFT_eSPI` is not thread-safe. All display calls originate from Core 1's `loop()` or MQTT callbacks (also Core 1). Safe in practice, but if any future code calls a display method from Core 0, it would corrupt the SPI bus. No compile-time or runtime enforcement exists.

**h) LEDController: `FastLED.show()` not thread-safe:**
FastLED accesses GPIO 16 via the RMT peripheral. All LED calls are from Core 1 currently — safe. Same unenforced invariant as DisplayManager.

**i) LEDController: `showReady()` uses `static` local variables (lines 83-84):**
`pulseValue` and `increasing` persist across calls with no reset mechanism. If `off()` is called between `showReady()` invocations, the pulse state is stale — it resumes from wherever it left off rather than restarting. These should be instance members reset in `off()`.

**j) `extern bool serialStudioEnabled` — now in 5 files across the codebase:**
LEDController.cpp (line 3) and SerialStudioOutput (via `_enabled` member — clean). Including Batches 2-4, this global appears in SensorManager, DirectionDetector, SessionManager, LEDController. A configuration/logging abstraction would eliminate all occurrences.

#### 3. Interrupt Handling Patterns (InterruptManager)

**a) ISR design is properly minimal — correct:**
The ISRs only record a timestamp (`micros()`) and set a pending flag. No I2C, no queue operations, no serial output. This is the right pattern for ESP32 ISRs.

**b) ISR-to-task communication via `volatile` polling instead of FreeRTOS notification — inefficient:**
The processing task (lines 626-683) busy-loops with `taskYIELD()` when no ISR is pending. On a dual-core system, this means the task consumes all remaining Core 1 CPU time even when idle. The standard ESP32 pattern is `xTaskNotifyFromISR()` in the ISR + `xTaskNotifyWait()` in the task — the task sleeps at zero CPU cost until notified. This would also eliminate the latency introduced by `taskYIELD()` (which yields to equal-priority tasks, adding up to one tick period of delay before the task runs again).

**c) No software debounce on GPIO interrupts:**
The VCNL4040's hardware persistence setting provides some filtering, but there's no software-level debounce. If electrical noise causes rapid GPIO edges (especially during MUX switching — crosstalk between adjacent GPIO traces 11-13), every edge triggers an ISR and eventually generates an event. A minimum inter-interrupt interval check in `handleIsr()` (e.g., ignore if `micros() - _lastIsrTime[board] < 100`) would filter electrical noise without losing real events (VCNL4040's fastest measurement cycle is ~250µs at 1T/40 duty).

**d) Three ISR trampolines are necessary:**
`isrBoard1()`, `isrBoard2()`, `isrBoard3()` each forward to `handleIsr(N)` with a hardcoded board index. This is required because `attachInterrupt()` on ESP32 Arduino doesn't accept a user parameter. Correct and unavoidable pattern.

**e) GPIO-to-board mapping is inverted and documented only in comments:**
Lines 453-460: GPIO 11 maps to Board 2 (TCA channel 2), GPIO 12 to Board 1 (TCA channel 1), GPIO 13 to Board 0 (TCA channel 0) — the physical wiring inverts the numbering. This mapping is documented in comments but hardcoded in `attachInterrupt()` calls. A `const uint8_t GPIO_TO_BOARD_MAP[]` array would make this explicit and verifiable.

#### 4. Error Handling

**a) DisplayManager `init()` has no return value:**
If `tft.init()` fails (wrong SPI configuration, hardware fault), there's no way for the caller to detect it. `init()` should return `bool` so the initialization orchestrator can report the failure. Currently, a display failure results in a black screen with no diagnostic output.

**b) InterruptManager `calibrateSensors()` and `configure()` callable during active monitoring:**
Neither method checks `_monitoring` before accessing the I2C bus. If called while the processing task is running, they'd compete for the MUX and I2C bus. `calibrateSensors()` uses blocking `delay()` calls that would stall whatever core it's called from while the processing task is selecting different sensors on the same bus. Both should refuse (return error) when `_monitoring` is true.

**c) InterruptManager `begin()` silently succeeds if event queue already exists:**
Lines 70-71: `if (_eventQueue == nullptr)` skips queue creation if it already exists. This means `begin()` can be called multiple times — but the second call skips GPIO configuration (already done) and MuxController reinitialization. The method should be idempotent or guard against double-init.

**d) InterruptManager verbose serial output in `configureSensor()` (~30 lines of serial debug per sensor):**
Lines 366-390 verify register values by reading back PS_CONF1_2, thresholds, and current proximity. This is useful during development but adds ~6ms of serial I/O per sensor (6 sensors = ~36ms) during every `configure()` call. Should be gated with `#ifdef DEBUG_INTERRUPTS` or a runtime flag.

#### 5. Magic Numbers

**DisplayManager:**

| Value | Location(s) | Should be |
|---|---|---|
| `0x3186` | cpp lines 273, 281 | **`COLOR_DARK_BORDER`** — unnamed 16-bit RGB565 color |
| `100` | init() line 14 | **`DISPLAY_POWER_UP_DELAY_MS`** |
| `6` | lines 146, 204, 251, 460 | **`CHAR_WIDTH_PX`** — TFT_eSPI font width at text size 1 |
| Various pixel offsets | calibration methods throughout | Ad-hoc layout: `SCREEN_WIDTH / 2 - 66`, `- 72`, `- 114`, `- 84`, `- 99`, `- 93`, `- 78`, `- 69`, `- 102`, `- 75`, `- 81`, `- 60`, `- 63`, `- 54`, `- 42`, `- 36`, `- 30`, `- 24`, `- 12` | These are manual text-centering calculations. A helper `drawCenteredString(text, y)` would eliminate all of them. |
| Progress bar dimensions | calibration methods | Two different progress bar layouts: baseline (barX=40, barW=SCREEN_WIDTH-80, barH=20) vs approach (barX=20, barW=SCREEN_WIDTH-40, barH=16). Should be named or parameterized. |

**InterruptManager:**

| Value | Location(s) | Should be |
|---|---|---|
| `400000` | begin() line 61 | **`I2C_CLOCK_HZ`** (shared with SensorManager, Batch 2) |
| `5` | calibrateSensors() line 121, configureSensor() line 278 | **`MUX_SETTLE_MS`** (same value in Batch 2) |
| `50` | calibrateSensors() line 142 | **`SENSOR_STABILIZE_MS`** |
| `40` | calibrateSensors() line 136, configureSensor() line 291 | **`DEFAULT_IR_DUTY_DENOMINATOR`** |
| `16` | calibrateSensors() line 137, configureSensor() line 292 | **`PROX_RESOLUTION_BITS`** |
| `4096` | startMonitoring() line 428 | **`INT_TASK_STACK_SIZE`** |
| `1` | startMonitoring() line 430 | **`INT_TASK_PRIORITY`** |
| `1` | startMonitoring() line 432 | **`INT_TASK_CORE`** |
| `50` | processBoard() lines 715, 732 | **`MUX_MIN_SETTLE_US`** |
| `200` | processingTaskFunc() line 664 | **`MUX_DEBUG_SETTLE_US`** |
| `10` | stopMonitoring() line 491 | **`TASK_POLL_INTERVAL_MS`** |
| `255` | processBoard() line 746 | **`SENSOR_ID_UNKNOWN`** |
| `0x03`, `0x06`, `0x07` | configureSensor() lines 367, 381, 382 | Register constants already defined in VCNL4040.h — should use named constants |

**LEDController:**

| Value | Location(s) | Should be |
|---|---|---|
| `500` | update() line 147 | **`LED_FADE_DURATION_MS`** |
| `50` | showReady() line 89 | **`LED_PULSE_MAX`** |
| `10` | showReady() line 92 | **`LED_PULSE_MIN`** |
| `2` | showReady() lines 88, 93 | **`LED_PULSE_STEP`** |
| `3000` | showDirection() default parameter | **`LED_DEFAULT_DISPLAY_DURATION_MS`** |

**SerialStudioOutput:**

| Value | Location(s) | Should be |
|---|---|---|
| `1000` | update() line 67 | **`RATE_UPDATE_INTERVAL_MS`** |
| `125.0f` | calculateSensorRate() line 177 | **`VCNL4040_BASE_IT_US`** |
| `40` | calculateSensorRate() lines 188, 194 | **`DEFAULT_DUTY_DENOMINATOR`** (shared with InterruptManager) |

#### 6. Dead Code & Unnecessary Includes

**DisplayManager:**
- **`configString` member** (header line 50): Set by `setConfigString()` but never read during rendering. It was replaced by the `cached*` config members. `setConfigString()` conditionally calls `drawSessionStatus()`, but `drawSessionStatus()` never uses `configString`. Dead state — remove both the member and the method.
- **`CalibrationState` forward declaration** (header line 8): Never referenced in the header or implementation. Remove.
- **`showBootScreen()`** (cpp line 512): Legacy wrapper that just calls `showInitScreen()`. Mark for removal when callers migrate.
- **`updateStatus()`** (cpp line 517): Legacy wrapper that just calls `showMessage()`. Same.
- **`showNetworkInfo()`** (cpp line 533): Called once during init. Could be inlined or kept as convenience.

**InterruptManager:**
- **`INT_PROCESSING_TIMEOUT_MS`** (header line 53): Defined as `10` but never used anywhere. Dead constant — remove.
- **Debug polling block** (cpp lines 646-674): Development-time diagnostic code that reads sensor proximity every 2 seconds during active monitoring. Adds I2C latency and serial output to the interrupt processing path. Should be gated with `#ifdef DEBUG_INTERRUPTS`.

**LEDController:**
- **`#include "../detection/DirectionDetector.h"`** (header line 6): Only needs the `Direction` enum. Pulls the entire DirectionDetector → SensorManager → Adafruit_VCNL4040 transitive include chain. Should include `DetectionTypes.h` (recommended in Batch 3) once that extraction is done.

**SerialStudioOutput:**
- **`#include "../sensor/SensorManager.h"`** (header line 5): Only needs `SensorReading` and `NUM_SENSORS`. Same transitive include chain flagged in Batches 2, 3, and 4. Should use `SensorTypes.h` (recommended in Batch 3).

#### 7. API Design

**a) DisplayManager as a "god renderer" — every screen type is a method:**
DisplayManager knows about init stages, session states, operating modes, calibration stages, sensor configuration, and detection configuration. Any new screen requires modifying DisplayManager. A screen/view abstraction (e.g., `IScreen` with `render()` / `update()`) would make display extensible, but at the cost of indirection. The pragmatic step is extracting the calibration screens (~320 lines) since they form a self-contained group with no shared state with the session screen.

**b) DisplayManager `showCalibrationApproach()` — 5 parameters:**
```cpp
void showCalibrationApproach(uint8_t pcbId, uint16_t currentReading,
    uint16_t threshold, uint8_t progress, uint32_t timeRemaining);
```
This method is called on every CalibrationManager update loop iteration. Each call does `clear()` + full screen redraw (874 lines, ~25 TFT draw calls), causing visible flicker. A partial-update approach (only redraw changed fields — reading, progress bar, time remaining) would eliminate flicker and reduce I/O.

**c) DisplayManager `showCalibrationSummary()` — 6 parameters, boolean explosion:**
```cpp
void showCalibrationSummary(uint16_t threshold1, uint16_t threshold2,
    uint16_t threshold3, bool valid1, bool valid2, bool valid3);
```
Should take a `const DeviceCalibration &` or a small struct instead of 6 positional parameters. The caller (CalibrationManager) already has this data in structured form.

**d) InterruptManager `getMux()` exposes internal MuxController:**
Returns a mutable reference to the MuxController. External code could change MUX state while the processing task is using the I2C bus. Should be removed or return `const MuxController &`.

**e) InterruptManager singleton pattern via `_instance`:**
The static `_instance` pointer (required for ISR access) is set unconditionally in the constructor — if a second InterruptManager is ever created, the first's ISRs break silently. The constructor should assert `_instance == nullptr` or use a proper singleton pattern.

**f) SerialStudioOutput `setConfig()` takes non-const pointer:**
`void setConfig(SensorConfiguration *config)` stores a mutable pointer but only reads from it. Should be `const SensorConfiguration *config`.

**g) SerialStudioOutput `emitFrame()` format string is 30+ fields:**
Lines 118-138: A single `Serial.printf()` call with 30 positional format arguments. Adding, removing, or reordering fields requires counting `%` specifiers manually. This is the most maintenance-hazardous line in the entire codebase. A field-by-field emission approach (multiple `Serial.print()` calls with delimiters) or a builder pattern would be safer, at the cost of more function calls.

**h) LEDController redefines GPIO pin as local macro:**
`LED_PIN 16` in `LEDController.h` duplicates `PIN_LED_STRIP_DATA 16` from `pin_config.h`. If the pin assignment changes, only one of the two would be updated. `LED_PIN` should be replaced with `PIN_LED_STRIP_DATA` (with an `#include "pin_config.h"`), or the macro should reference it: `#define LED_PIN PIN_LED_STRIP_DATA`.

#### 8. Naming & Style

**a) `_cachedSpeedMs` in SerialStudioOutput (header line 32):**
Ambiguous — "Ms" reads as "milliseconds" but the value is meters per second. Should be `_cachedSpeedMps` or `_cachedTransitSpeed_mps`.

**b) InterruptManager uses consistent `_prefix` naming — good.**
All private members use `_prefix` (`_mux`, `_config`, `_monitoring`, `_stats`, etc.). Consistent with DirectionDetector and CalibrationManager conventions (Batch 3).

**c) LEDController uses no-prefix naming:**
Private members: `initialized`, `animationActive`, `animationStartTime`, `animationDuration`, `currentColor`, `leds`. No prefix at all — inconsistent with InterruptManager's `_prefix` and MLDetector's `suffix_`. Minor but contributes to cross-module inconsistency.

**d) `#define` macros for LEDController constants:**
`NUM_LEDS`, `LED_PIN`, `LED_TYPE`, `COLOR_ORDER`, `DEFAULT_BRIGHTNESS` are preprocessor macros. These pollute the global namespace and have no type safety. Should be `static constexpr` members of LEDController or namespace-scoped constants. `NUM_LEDS` in particular could collide with other libraries.

**e) InterruptManager config constants use `#define` with `INT_` prefix:**
`INT_EVENT_BUFFER_SIZE`, `INT_CALIBRATION_DURATION_MS`, etc. Same issue — should be `static constexpr` for type safety. The `INT_` prefix is also potentially confusing (reads as "integer" in some contexts).

#### 9. Decomposition Recommendations

Listed in priority order (highest impact first):

| # | Extraction | What it achieves | Est. lines saved | Effort | Notes |
|---|---|---|---|---|---|
| 1 | **Replace `taskYIELD()` with `xTaskNotifyFromISR()`** | Eliminates CPU waste during interrupt monitoring. Processing task sleeps at zero cost until an ISR fires. Improves latency (notification is immediate vs next scheduler tick). | ~0 (behavior) | Small | High impact. Change `handleIsr()` to call `xTaskNotifyFromISR()`, change `processingTaskFunc()` loop to `xTaskNotifyWait()`. |
| 2 | **Extract calibration screens from DisplayManager** | Move 8 `showCalibration*()` methods (~320 lines) into `CalibrationScreen` (new file or class). DisplayManager delegates to it. | ~320 | Small | Largest single extraction in this batch. Clean separation — calibration screens share no layout state with session screen. |
| 3 | **Extract `InterruptTypes.h`** | Move `InterruptEventType`, `InterruptEvent`, `InterruptMode`, `InterruptConfig`, `InterruptSessionStats` out of `InterruptManager.h`. Breaks transitive include: `SessionManager.h` → `InterruptManager.h` → `MuxController.h` → `VCNL4040.h`. | ~100 from header | Small | SessionManager.h only needs `InterruptEvent`. DataTransmitter only needs `InterruptEvent`. Neither needs MuxController or VCNL4040. |
| 4 | **Replace `volatile` with `std::atomic` in InterruptManager** | Fix `_monitoring` (ISR + task), add `volatile` to `_stats.isrCount`. Fix `_processingTask = nullptr` race (use task notification for exit handshake). | ~0 (correctness) | Small | Same pattern as Batch 2 recommendation #8 for SensorManager. Should be done in one pass across both components. |
| 5 | **Gate debug polling with `#ifdef DEBUG_INTERRUPTS`** | Remove ~25 lines of debug polling from the hot path. Eliminates unnecessary I2C traffic and serial output during monitoring. | ~25 (conditional) | Trivial | Quick win. Also removes `INT_PROCESSING_TIMEOUT_MS` dead constant. |
| 6 | **Add software debounce in `handleIsr()`** | Ignore ISRs within 100µs of the previous ISR on the same board. Filters electrical noise without losing real events. | ~5 | Trivial | `if (now - _lastIsrTime[board] < MIN_ISR_INTERVAL_US) return;` before writing the flag. |
| 7 | **Fix LEDController pin/include issues** | Replace `#define LED_PIN 16` with `PIN_LED_STRIP_DATA` from `pin_config.h`. Replace `#include "DirectionDetector.h"` with `DetectionTypes.h` (after Batch 3 #2 is done). Convert remaining `#define` macros to `static constexpr`. | ~0 (correctness) | Trivial | Quick win. Eliminates pin duplication and heavy transitive include. |
| 8 | **Fix LEDController `showReady()` static locals** | Move `pulseValue` and `increasing` to instance members. Reset in `off()`. | ~0 (correctness) | Trivial | Eliminates stale pulse state on mode transitions. |
| 9 | **Add `drawCenteredString()` helper to DisplayManager** | Replace ~20 manual `SCREEN_WIDTH / 2 - (text.length() * 6 / 2)` calculations with a single helper. | ~0 (readability) | Trivial | Quick win. Reduces errors when changing text content. |
| 10 | **Make `DisplayManager::init()` return `bool`** | Allow initialization orchestrator to detect display failure. | ~0 (safety) | Trivial | Currently a black screen is undiagnosable. |
| 11 | **Remove dead `configString` from DisplayManager** | Delete `configString` member, `setConfigString()` method. | ~15 | Trivial | Dead state that's never rendered. |
| 12 | **Replace `showCalibrationApproach()` full redraw with partial update** | Only redraw changed fields (reading value, progress bar fill, time remaining) instead of `clear()` + 25 draw calls per iteration. | ~0 (performance/UX) | Medium | Eliminates visible screen flicker during calibration approach phase. |
| 13 | **Fix SerialStudioOutput `setConfig()` const-correctness** | Change parameter to `const SensorConfiguration *`. | ~0 (correctness) | Trivial | Matches read-only usage. |
| 14 | **Guard InterruptManager `calibrateSensors()`/`configure()` during monitoring** | Add `if (_monitoring) return false;` at the top of both methods. | ~5 | Trivial | Prevents I2C bus collision if called at the wrong time. |

**Recommended execution order:** #5 (gate debug polling) → #11 (remove dead configString) → #7 (fix LED pin/includes) → #8 (fix LED static locals) → #13 (SerialStudioOutput const) → #14 (guard calibrate/configure) → #10 (init return bool) → #6 (software debounce) → #4 (volatile→atomic, coordinate with Batch 2 #8) → #3 (InterruptTypes.h, coordinate with Batch 4 #8) → #9 (drawCenteredString) → #1 (xTaskNotify, highest-impact behavioral change) → #2 (extract calibration screens) → #12 (partial display update).

**Key dependencies:**
- Extraction #3 (`InterruptTypes.h`) enables Batch 4 #8 (`SensorTypes.h`) — both break heavy transitive include chains. Should be coordinated.
- Extraction #7 (LED `DetectionTypes.h` include) depends on Batch 3 #2 (`DetectionTypes.h` extraction).
- Extraction #4 (`volatile` → `std::atomic`) should be done in one pass with Batch 2 #8 (SensorManager's `stopRequested`) for consistency.
- Extraction #1 (`xTaskNotify`) is the highest-impact behavioral fix. It's independent of other extractions and can be done at any time.

After these changes, DisplayManager.cpp drops from ~874 to ~550 lines (calibration screens extracted). InterruptManager stays roughly the same line count but with cleaner header separation, correct concurrency primitives, and efficient task scheduling. LEDController and SerialStudioOutput need only minor fixes.

### Batch 6: Networking & Infrastructure

**MQTTManager (300 + 45 lines), NetworkManager (122 + 29 lines), MemoryMonitor (144 lines, header-only), pin_config.h (44 lines). Plus cross-cutting review: header hygiene, include chains, shared constants, `extern bool serialStudioEnabled`.**

#### 1. Single Responsibility Violations

**a) MQTTManager owns config loading, certificate I/O, connection management, serialization, and a vestigial command handler:**

`loadConfig()` reads `/config.json` from LittleFS, parses JSON, extracts MQTT fields, builds topic strings, and calls `loadCertificates()`. `loadCertificates()` reads three PEM files and configures the TLS client. `publishStatus()` constructs a JSON document and publishes it. The static `messageCallback()` (line 267) parses incoming JSON and handles a "ping" command — but this handler is dead code because main.cpp immediately installs its own callback via `setCallback()`. The class is simultaneously a config loader, a certificate manager, a connection state machine, a message serializer, and a (dead) command dispatcher.

**b) NetworkManager manages WiFi, TLS, filesystem initialization, config parsing, and stores unrelated application state:**

`loadConfig()` mounts LittleFS (`LittleFS.begin(true)`), enumerates all files in root (debug listing, lines 16-29), opens and parses `/config.json`, and stores WiFi credentials, `deviceId`, and `apiEndpoint`. The `deviceId` and `apiEndpoint` fields have nothing to do with network connectivity — they are application configuration data that happens to live in the same config file. `getDeviceId()` and `getApiEndpoint()` turn NetworkManager into a config bag.

**c) Both managers parse `/config.json` independently:**

`NetworkManager::loadConfig()` and `MQTTManager::loadConfig()` each open `/config.json`, create a `DynamicJsonDocument(1024)`, deserialize the same JSON file, and extract their respective fields. `device_id` is parsed and stored by both classes (`NetworkManager::deviceId` and `MQTTManager::deviceId`). If the config file format changes, two methods need updating. This is a textbook violation of DRY that also doubles filesystem I/O at boot.

**d) MemoryMonitor is a static utility class with a hidden dependency on Serial Studio state:**

All methods are `static`. The class depends on `extern bool serialStudioEnabled` (line 8 of the header) to gate serial output — a presentation concern embedded in a diagnostic utility. The class should report data unconditionally; callers (or a logging layer) decide whether to print.

#### 2. Error Handling

**a) MQTTManager `connect()` blocks Core 1 for up to 25 seconds:**

Lines 101-128: 5 attempts × `delay(5000)` = up to 25 seconds of blocking. During this time, display updates, heartbeat publishing, and command processing are stalled. On an ESP32 dual-core system, blocking Core 1's loop for 25 seconds is severe — the device appears unresponsive.

**b) MQTTManager `loop()` reconnects on every iteration with no backoff:**

Lines 142-149: If disconnected, `loop()` calls `connect()` unconditionally. If the broker is unreachable (e.g., internet outage), every `loop()` iteration blocks for 25 seconds, retries, fails, then the next `loop()` call immediately tries again. No exponential backoff, no cooldown, no maximum-attempts-per-hour limit. The device enters an infinite block-retry cycle.

**c) NetworkManager `connectWiFi()` blocks for up to 30 seconds:**

Lines 78-94: 30 attempts × `delay(1000)`. Same pattern — Core 1 is completely blocked. If WiFi credentials are wrong (e.g., wrong network at a remote test location), boot takes 30+ seconds before the device becomes usable.

**d) NetworkManager `checkConnection()` triggers the full 30-second blocking reconnect:**

Lines 110-114: If WiFi drops, `checkConnection()` calls `connectWiFi()` which blocks for up to 30 seconds. If called from `loop()`, this stalls the entire Core 1 event loop.

**e) `connected` flag is stale — two sources of truth:**

NetworkManager has a `bool connected` member (set in `connectWiFi()` and `disconnect()`) but `isConnected()` checks `WiFi.status()` directly, ignoring the flag. The flag is only used in `checkConnection()` to detect "was connected but now isn't." If WiFi drops, `connected` remains `true` until `checkConnection()` runs — a split-brain state. The flag should either track `WiFi.status()` or be removed in favor of the hardware check.

**f) MQTTManager `publishDataStreaming()` — partial write leaves connection in undefined state:**

Lines 228-243: If a chunk write fails, the method frees the buffer and returns `false`. But `beginPublish()` has already been called, and `endPublish()` is skipped. The PubSubClient state after a failed streaming write is undefined — subsequent `publish()` calls may fail silently. The method should attempt `endPublish()` (or disconnect/reconnect) even after a partial failure.

**g) MQTTManager `publishStatus()` reaches past NetworkManager to call `WiFi.RSSI()` directly:**

Line 157: `doc["wifi_rssi"] = WiFi.RSSI();`. This bypasses the NetworkManager abstraction entirely. If NetworkManager ever wraps WiFi behind a different transport (or for testing), this call would break. RSSI should be exposed via NetworkManager.

#### 3. Header Hygiene & Transitive Include Chains

**a) `MQTTManager.h` includes `<LittleFS.h>` — only needed in the .cpp:**

LittleFS is used in `loadConfig()` and `loadCertificates()` — both implementation methods. The header doesn't reference any LittleFS types. Moving `#include <LittleFS.h>` to `MQTTManager.cpp` eliminates this transitive dependency from all includers.

**b) `NetworkManager.h` includes `<LittleFS.h>` and `<ArduinoJson.h>` — both only needed in .cpp:**

The header's public interface uses `String`, `WiFiClientSecure`, and `bool` — none of which require LittleFS or ArduinoJson. Both includes should move to `NetworkManager.cpp`.

**c) Transitive chain: `DataTransmitter.h` → `MQTTManager.h` → `NetworkManager.h`:**

Including `DataTransmitter.h` pulls in:
- `NetworkManager.h` → `<WiFi.h>`, `<WiFiClientSecure.h>`, `<ArduinoJson.h>`, `<LittleFS.h>`
- `MQTTManager.h` → `<PubSubClient.h>`, `<LittleFS.h>` (again)

DataTransmitter only needs `MQTTManager*`. A forward declaration (`class MQTTManager;`) in `DataTransmitter.h` with the include moved to `DataTransmitter.cpp` would break this chain. Similarly, `MQTTManager.h` only needs `NetworkManager*` — a forward declaration would break the chain further, reducing `DataTransmitter.h` to near-zero transitive cost.

**d) `MemoryMonitor.h` exports `extern bool serialStudioEnabled` to all includers:**

Line 8: `extern bool serialStudioEnabled;` in a header means every file that includes `MemoryMonitor.h` gets an implicit dependency on a global defined in main.cpp. Currently only main.cpp includes it, but this is a maintenance trap — any future includer inherits the dependency silently.

**e) Mixed include guard styles across the codebase:**

| Style | Files |
|---|---|
| `#ifndef X_H` / `#define X_H` / `#endif` | MQTTManager.h, NetworkManager.h, DataTransmitter.h, DisplayManager.h, SensorManager.h, SessionManager.h, DirectionDetector.h, MLDetector.h, LEDController.h, PSRAMAllocator.h, SensorConfiguration.h, SerialStudioOutput.h, MemoryMonitor.h |
| `#pragma once` | pin_config.h, InterruptManager.h, CalibrationManager.h, CalibrationData.h, VCNL4040.h, MuxController.h, TCA9548A.h |

Neither style is wrong, but mixing both in the same project means contributors must check which convention each file uses. The codebase should pick one. `#pragma once` is simpler and supported by all modern compilers targeting ESP32.

#### 4. Concurrency

**a) MQTTManager `loop()` is called from Core 1 only — safe but unenforced:**

All MQTT operations (connect, publish, loop) run on Core 1. PubSubClient is not thread-safe. Same unenforced invariant pattern noted in Batches 3 and 5 for DisplayManager and LEDController.

**b) NetworkManager `checkConnection()` + MQTTManager `connect()` race:**

If `checkConnection()` triggers `connectWiFi()` while `MQTTManager::loop()` is calling `connect()`, both attempt WiFi/MQTT operations simultaneously. In practice both run on Core 1 so they are serialized by the single-threaded event loop. But if either is ever moved to a task or ISR, the lack of synchronization becomes a data race.

#### 5. Magic Numbers

**MQTTManager:**

| Value | Location(s) | Should be |
|---|---|---|
| `32768` | cpp line 44 | **`MQTT_BUFFER_SIZE`** |
| `24576` | cpp line 173 | **`MQTT_LARGE_PAYLOAD_WARN_BYTES`** |
| `4096` | cpp line 224 | **`MQTT_STREAM_CHUNK_SIZE`** |
| `5000` | cpp line 126 | **`MQTT_RECONNECT_DELAY_MS`** |
| `5` | cpp line 102 | **`MQTT_MAX_CONNECT_ATTEMPTS`** |
| `1024` | cpp lines 14, 280 | **`CONFIG_JSON_CAPACITY`** (shared with NetworkManager) |
| `256` | cpp line 153 | **`STATUS_JSON_CAPACITY`** |
| `"motionplay/"` | cpp lines 27-29 | **`MQTT_TOPIC_PREFIX`** — hardcoded topic prefix |

**NetworkManager:**

| Value | Location(s) | Should be |
|---|---|---|
| `1024` | cpp line 45 | **`CONFIG_JSON_CAPACITY`** (same as MQTTManager — shared constant) |
| `30` | cpp line 79 | **`WIFI_MAX_CONNECT_ATTEMPTS`** |
| `1000` | cpp line 80 | **`WIFI_ATTEMPT_DELAY_MS`** |
| `100` | cpp line 75 | **`WIFI_MODE_SETTLE_MS`** |

**MemoryMonitor:**

| Value | Location(s) | Should be |
|---|---|---|
| `50000` | lines 62, 103 | **`LOW_HEAP_WARNING_BYTES`** (duplicated between `printMemoryStats()` and `isMemoryHealthy()`) |
| `100000` | line 66 | **`LOW_HEAP_CAUTION_BYTES`** |
| `1000000` | lines 77, 103 | **`LOW_PSRAM_WARNING_BYTES`** (also duplicated) |

**pin_config.h:**

No magic numbers — all values are named. But see item 6d below for dead definitions.

#### 6. Dead Code & Issues

**a) MQTTManager `messageCallback()` is dead code:**

The static callback is installed in `loadConfig()` (line 39: `mqttClient.setCallback(messageCallback)`), but main.cpp immediately calls `setCallback()` with its own handler, overwriting it. The static method's "ping" handling is never reached. Remove it.

**b) MQTTManager VLA in `messageCallback()`:**

Line 272: `char message[length + 1]` is a variable-length array — a C99 feature, not standard C++. GCC allows it as an extension, but if a large MQTT payload arrives (the buffer is 32KB), this overflows the stack. Should use a fixed-size buffer with length check, or `std::vector<char>`.

**c) NetworkManager debug file listing in `loadConfig()`:**

Lines 16-29: Enumerates all files in LittleFS root and prints their names/sizes. This was useful during initial development but is pure noise in production. Should be gated behind `#ifdef DEBUG_FILESYSTEM` or removed.

**d) pin_config.h SD card definitions are dead:**

Lines 37-41: `PIN_SD_CS`, `PIN_SD_MISO`, `PIN_SD_MOSI`, `PIN_SD_SCLK` — all marked as conflicting with Motion Play hardware. SD card is not used in the project. These dead definitions add confusion. Comment them out or remove.

**e) pin_config.h `PIN_IIC_SDA` / `PIN_IIC_SCL` naming:**

Uses the older `IIC` notation. The rest of the codebase (comments, CONTEXT.md, hardware docs) uses `I2C`. Rename to `PIN_I2C_SDA` / `PIN_I2C_SCL` for consistency.

**f) NetworkManager return-by-value for string accessors:**

`getDeviceId()` and `getApiEndpoint()` return `String` by value — copying the string on every call. Should return `const String&` to avoid unnecessary allocations. (MQTTManager's `getDeviceId()` already does this correctly.)

#### 7. API Design

**a) `MQTTManager` exposes raw `PubSubClient` callback signature to callers:**

`setCallback(std::function<void(char*, byte*, unsigned int)>)` leaks the PubSubClient callback signature into the public API. Callers must know about `byte*` payloads and manual length handling. A higher-level interface (e.g., accepting a `const char* topic, const JsonDocument& doc` callback) would decouple callers from the transport library.

**b) NetworkManager `getClient()` returns a mutable reference to `WiFiClientSecure`:**

This allows any caller to reconfigure TLS settings, change certificates, or close the connection. The SSL client should be encapsulated — MQTTManager should receive it during construction rather than reaching into NetworkManager at will.

**c) LittleFS initialization is an implicit ordering dependency:**

NetworkManager initializes LittleFS in `loadConfig()`. MQTTManager uses LittleFS in `loadConfig()` and `loadCertificates()` without initializing it. If MQTTManager is initialized before NetworkManager, the cert reads fail silently. This dependency is not documented or enforced by the API.

#### 8. Cross-Cutting: `extern bool serialStudioEnabled`

**Final tally across the active codebase (6 files):**

| File | Type | Usage |
|---|---|---|
| `main.cpp` line 53 | **Definition** | `bool serialStudioEnabled = SERIAL_STUDIO_DEFAULT;` |
| `SensorManager.cpp` line 4 | `extern` | Guards debug serial output |
| `DirectionDetector.cpp` line 3 | `extern` | Guards debug serial output |
| `SessionManager.cpp` line 3 | `extern` | Guards debug serial output |
| `LEDController.cpp` line 3 | `extern` | Guards debug serial output |
| `MemoryMonitor.h` line 8 | `extern` **in a header** | Guards `printMemoryStats()` and `printCompactStatus()` |

Every occurrence follows the same pattern: `if (serialStudioEnabled) return;` or `if (!serialStudioEnabled) { Serial.print(...); }`. The global is purely a debug-output gate.

**Recommended fix:** Create `firmware/include/debug_log.h` with:
- `extern bool serialStudioEnabled;` declared once
- Inline helper: `inline bool debugPrintEnabled() { return !serialStudioEnabled; }` or a `DEBUG_LOG(...)` macro that checks the flag and calls `Serial.printf()`

All 5 `extern` declarations are replaced by `#include "debug_log.h"`. The flag definition stays in main.cpp (or moves to a globals.cpp). This eliminates the scattered `extern` declarations, centralizes the Serial Studio concern, and prevents the `extern` from appearing in component headers.

#### 9. Cross-Cutting: Shared Constants Across All Batches

Constants that were identified in multiple batches as needing unification:

| Constant | Value | Files | Recommended name |
|---|---|---|---|
| I2C clock speed | `400000` | SensorManager (Batch 2), InterruptManager (Batch 5) | `I2C_CLOCK_HZ` |
| IR duty denominator | `40` | InterruptManager ×2 (Batch 5), SerialStudioOutput ×2 (Batch 5) | `DEFAULT_IR_DUTY_DENOMINATOR` |
| MUX settle time | `5` ms | SensorManager (Batch 2), InterruptManager (Batch 5) | `MUX_SETTLE_MS` |
| Config JSON capacity | `1024` | NetworkManager (Batch 6), MQTTManager (Batch 6) | `CONFIG_JSON_CAPACITY` |
| Config file path | `"/config.json"` | NetworkManager, MQTTManager | `CONFIG_FILE_PATH` |
| Heap warning threshold | `50000` | MemoryMonitor ×2 | `LOW_HEAP_WARNING_BYTES` |
| PSRAM warning threshold | `1000000` | MemoryMonitor ×2 | `LOW_PSRAM_WARNING_BYTES` |
| MQTT topic prefix | `"motionplay/"` | MQTTManager | `MQTT_TOPIC_PREFIX` |

These should live in a shared `firmware/include/constants.h` (compile-time, `static constexpr`) or per-module constant blocks as appropriate. Pin-related constants already have a home in `pin_config.h`. I2C-related constants (clock speed, settle times) could live in a `firmware/include/i2c_config.h` alongside pin definitions.

#### 10. Decomposition Recommendations

Listed in priority order (highest impact first):

| # | Extraction | What it achieves | Est. lines saved | Effort | Notes |
|---|---|---|---|---|---|
| 1 | **Extract `ConfigLoader`** | Single class/function that mounts LittleFS, parses `/config.json` once, and exposes typed fields (WiFi credentials, MQTT settings, device ID, API endpoint). Both NetworkManager and MQTTManager receive config rather than loading it. Eliminates duplicate file I/O, duplicate `device_id`, and the implicit LittleFS initialization ordering. | ~80 (net: new file but removes duplication) | Small | Highest-impact structural fix in this batch. Also a natural home for cert paths and topic prefix constants. |
| 2 | **Non-blocking reconnection for MQTT and WiFi** | Replace `delay()`-based blocking loops in `MQTTManager::connect()` and `NetworkManager::connectWiFi()` with a state machine: track `lastAttemptMs`, `attemptCount`, return immediately if cooldown hasn't elapsed. `loop()` drives the state machine incrementally. Adds exponential backoff. | ~0 (behavioral) | Medium | Eliminates the 25-30 second blocking stalls that freeze Core 1. Most important behavioral fix. |
| 3 | **Create `debug_log.h`** | Centralizes `extern bool serialStudioEnabled` and provides `DEBUG_LOG(...)` macro. Replaces 5 scattered `extern` declarations and ad-hoc guard patterns across the codebase. | ~0 (hygiene) | Trivial | Quick win. Can be done independently. Eliminates the `extern` in MemoryMonitor.h. |
| 4 | **Move LittleFS/ArduinoJson includes from headers to .cpp files** | Break transitive include chains. `MQTTManager.h` drops `<LittleFS.h>`. `NetworkManager.h` drops `<LittleFS.h>` and `<ArduinoJson.h>`. Forward-declare `class NetworkManager;` in `MQTTManager.h`. Forward-declare `class MQTTManager;` in `DataTransmitter.h`. | ~0 (compile time) | Trivial | Dramatically reduces transitive include cost for DataTransmitter and anything that includes it. |
| 5 | **Split MemoryMonitor into .h + .cpp** | Move `printMemoryStats()` and `printCompactStatus()` implementations to .cpp. Header retains only declarations and trivial inline getters. Follows project convention. | ~0 (convention) | Trivial | Also the place to remove the `extern bool serialStudioEnabled` once #3 is done. |
| 6 | **Remove dead `messageCallback()`** | Delete the static callback and the "ping" handler in MQTTManager. It's immediately overwritten by main.cpp's `setCallback()`. | ~30 | Trivial | Dead code removal. |
| 7 | **Fix `publishDataStreaming()` partial-write cleanup** | Call `endPublish()` (or disconnect + reconnect) even after a chunk write failure, to avoid leaving PubSubClient in an undefined state. | ~5 | Trivial | Correctness fix for edge case during data transmission. |
| 8 | **Clean up pin_config.h** | Remove dead SD card pin definitions. Rename `PIN_IIC_*` to `PIN_I2C_*`. Add comment for GPIO 0 = BOOT button. | ~5 | Trivial | Quick housekeeping. |
| 9 | **Constants extraction** | Create `firmware/include/constants.h` for cross-module constants (`I2C_CLOCK_HZ`, `MUX_SETTLE_MS`, `DEFAULT_IR_DUTY_DENOMINATOR`, `CONFIG_JSON_CAPACITY`, `CONFIG_FILE_PATH`). Per-module magic numbers become `static constexpr` members (see Batch 6 §5 tables). | ~0 (readability) | Small | Coordinate with Batch 2 #7 and Batch 5 magic number fixes. |
| 10 | **Unify include guard style** | Pick `#pragma once` project-wide (simpler, universal ESP32 support). Convert all `#ifndef`/`#define`/`#endif` headers. | ~0 (consistency) | Trivial | Mechanical change. Can be done in one pass. |
| 11 | **Fix NetworkManager string accessor return types** | Change `getDeviceId()` and `getApiEndpoint()` to return `const String&`. | ~0 (performance) | Trivial | Avoids unnecessary string copies. |
| 12 | **Expose WiFi RSSI through NetworkManager** | Add `int getRSSI() const` to NetworkManager. Replace `WiFi.RSSI()` in MQTTManager::publishStatus(). | ~0 (encapsulation) | Trivial | Fixes the abstraction leak. |

**Recommended execution order:** #3 (debug_log.h) → #6 (remove dead callback) → #8 (pin_config cleanup) → #11 (string refs) → #12 (RSSI accessor) → #4 (move includes to .cpp) → #5 (MemoryMonitor .h/.cpp split) → #10 (unify guards) → #9 (constants extraction, coordinate with Batches 2+5) → #7 (streaming cleanup) → #1 (ConfigLoader extraction) → #2 (non-blocking reconnection).

**Key dependencies:**
- #3 (`debug_log.h`) should be done before #5 (MemoryMonitor split) — the split removes the `extern` and replaces it with `#include "debug_log.h"`.
- #4 (header include moves) should be done before #10 (guard unification) to avoid rework.
- #1 (ConfigLoader) can be done independently but is the largest structural change. Should be done after #4 so the new class follows the clean include patterns.
- #2 (non-blocking reconnection) is the most complex change. It's behavioral and should be thoroughly tested. Independent of all other extractions.
- #9 (constants) spans Batches 2, 5, and 6 — should be done in one coordinated pass.

After these changes, MQTTManager.cpp drops from ~300 to ~270 lines (dead callback removed, config loading delegated). NetworkManager.cpp drops from ~122 to ~70 lines (config loading delegated, debug listing removed). MemoryMonitor gains a proper .h/.cpp split. The transitive include chain `DataTransmitter.h` → `WiFi.h` is broken. The `extern bool serialStudioEnabled` global is centralized. Boot no longer blocks for 25-55 seconds on network failures.

## Audit Complete

All six batches analyzed. See REPORT.md for synthesized findings and follow-on initiative recommendations. The open questions that were listed here at the start of the audit have been answered by the batch analyses above:

- **How tightly coupled is main.cpp to component internals?** Very. 30+ mutable globals, 9 distinct responsibilities, direct member access across components. (Batch 1)
- **Are there circular dependencies between components?** No true circular includes, but heavy transitive chains: `DataTransmitter.h` → `SessionManager.h` → `SensorManager.h` → `Adafruit_VCNL4040.h`. (Batches 4, 6)
- **What shared state exists between Core 0 and Core 1, and how is it protected?** `stopRequested` (volatile, should be atomic), `sensorTask` handle (unprotected), `activeSummary` pointer (no barrier), `activeConfig` pointer (safe via shutdown ordering). (Batch 2)
- **Is there a consistent error handling pattern?** No. Each component does its own thing: some use return codes, some print and continue, some block with `delay()` loops, some silently fail. (Batches 1, 4, 6)

# Firmware Architecture Audit — Report

## Executive Summary

We audited all active firmware source (~12,000 lines of C++ across 30+ files) in six structured batches, evaluating against ten criteria: single responsibility, file size, header hygiene, memory safety, concurrency, API design, naming, error handling, magic numbers, and dead code.

**The firmware works.** It collects sensor data at 1kHz, transmits reliably over MQTT/TLS, runs ML inference on-device, and has never exhibited data corruption in the field. The issues below are structural, not functional — they affect maintainability, resilience to edge cases, and the ability to evolve the system.

**The three most impactful problems are:**

1. **main.cpp is a 1,845-line monolith** containing 9 distinct responsibilities and ~30 mutable globals. It is the orchestrator, command handler, config client, button handler, detection engine, data capture pipeline, and heartbeat manager all at once. Every component in the system is touched directly from this file.

2. **The sensor pipeline has two parallel implementations** of both the MUX layer and the VCNL4040 driver. SensorManager (the Core 0 hot path, 1,429 lines) uses legacy raw I2C code, while InterruptManager uses the cleaner MuxController + VCNL4040 driver abstractions that already exist. Unifying these would cut SensorManager by ~450 lines and eliminate an entire class of consistency bugs.

3. **Network reconnection blocks the main loop for up to 55 seconds.** WiFi reconnection blocks for up to 30 seconds; MQTT reconnection adds another 25 seconds. During this time, display, buttons, heartbeats, and command processing are frozen. Data transmission (proximity mode) can block for an additional 120 seconds. These are the most likely causes of the device appearing "hung" in the field.

Below are the consolidated findings organized by theme, followed by a prioritized recommendation plan and a proposal for the follow-on refactoring initiative.

---

## 1. Oversized Files

Six files exceed the 600-line "must split" threshold. Three more are in the 300-600 review zone.

| File | Lines | Primary Issue | Target After Refactor |
|------|-------|---------------|----------------------|
| `main.cpp` | 1,845 | 9 responsibilities, ~30 globals | ~150-200 (delegation only) |
| `SensorManager.cpp` | 1,429 | Parallel MUX/driver implementations, inline diagnostics | ~300-400 |
| `DisplayManager.cpp` | 874 | Calibration screens (~320 lines) belong in dedicated module | ~550 |
| `InterruptManager.cpp` | 795 | Processing task architecture, verbose debug output | ~750 (modest reduction) |
| `DataTransmitter.cpp` | 769 | 4× duplicated JSON serialization across transmission paths | ~350-400 |
| `CalibrationManager.cpp` | 725 | Overly granular state enum, blocking delay() calls | ~600 (modest reduction) |
| `InterruptManager.h` | 357 | 5 data types that should be in a separate types header | ~100 |
| `DirectionDetector.h` | 252 | 6 types including generic RingBuffer utility | ~80 |

## 2. Code Duplication

**a) Parallel MUX + VCNL4040 implementations (Batch 2 — critical):**
SensorManager uses `TCA9548A` class + inline `PCA9546A` + raw `Wire` I2C calls. InterruptManager uses the newer `MuxController` + custom `VCNL4040` driver. Both access the same hardware. The clean implementations already exist and are tested — SensorManager just never adopted them. MUX cleanup code (select-each-channel → disable-PCA → disable-TCA) is repeated 7 times in SensorManager; `MuxController::disableAll()` does it in one call.

**b) No shared detector interface (Batch 3):**
DirectionDetector and MLDetector implement identical public APIs (`addReading`, `hasDetection`, `getResult`, `reset`, etc.) with no common base class. This forces main.cpp to duplicate all detection loop logic behind `if (useMLDetection)` branches (~250 lines of near-identical code in two detection loops). An `IDetector` interface would collapse this into one polymorphic flow.

**c) JSON serialization in DataTransmitter (Batch 4):**
Calibration JSON (~20 lines) is duplicated 4 times across transmission paths. Config JSON (~15 lines) is duplicated 3 times. Readings-array serialization is duplicated twice. Device-ID suffix extraction is duplicated 3 times (2 in DataTransmitter, 1 in SessionManager). Total: ~200 lines of copy-paste code.

**d) Config file parsing (Batch 6):**
Both `NetworkManager::loadConfig()` and `MQTTManager::loadConfig()` independently open `/config.json`, parse the same JSON, and extract their fields. `device_id` is stored in both classes.

## 3. Error Handling & Resilience

**a) Blocking network reconnection (Batch 6):**
`NetworkManager::connectWiFi()` blocks for up to 30 seconds (30 × `delay(1000)`). `MQTTManager::connect()` blocks for up to 25 seconds (5 × `delay(5000)`). `MQTTManager::loop()` calls `connect()` on every iteration when disconnected — no backoff, no cooldown, no attempt limit. Combined worst case: Core 1 frozen for 55 seconds every `loop()` cycle during an outage.

**b) Blocking data transmission (Batch 4):**
Proximity session transmission with `BATCH_SIZE=25` and `delay(100)` between batches: a 30-second session (30,000 readings) blocks the main loop for ~120 seconds. MQTT keepalive isn't called between batches, risking disconnect mid-transmission.

**c) Blocking calibration display (Batch 3):**
CalibrationManager calls `delay(1500)` in three code paths despite being designed as a cooperative (non-blocking) state machine. The main loop stalls for 1.5 seconds each time.

**d) Silent failures:**
- `SensorManager::readSensor()` returns a zeroed reading on I2C failure — indistinguishable from a legitimate zero (Batch 2).
- `MQTTManager::publishDataStreaming()` aborts on chunk-write failure without calling `endPublish()`, leaving PubSubClient in undefined state (Batch 6).
- `CalibrationManager::readPCB()` suppresses partial sensor failures, producing half-magnitude readings that silently skew thresholds (Batch 3).
- `PSRAMAllocator` logs via `Serial.printf()` on every allocation — if `push_back()` triggers geometric growth, ~30 serial prints fire during what should be a hot-path operation (Batch 4).

**e) Missing safety checks:**
- No null guard on `dataQueue` before `xQueueReceive()` (Batch 4).
- `doc.overflowed()` not checked in two of four transmission paths (Batch 4).
- `DisplayManager::init()` returns void — no way to detect display failure (Batch 5).
- InterruptManager's `calibrateSensors()` and `configure()` can be called during active monitoring, competing for the I2C bus (Batch 5).

## 4. Concurrency Hazards

All issues are currently "safe in practice" due to the single-threaded Core 1 event loop and careful ordering in main.cpp. But the safety is implicit and unenforced — any future change that moves work to a different core or task would silently introduce races.

**a) `volatile` used instead of `std::atomic` (Batches 2, 5):**
`SensorManager::stopRequested` and `InterruptManager::_monitoring` are `volatile bool` shared between cores/ISRs. `volatile` does not guarantee memory ordering on Xtensa LX7. `std::atomic<bool>` with `memory_order_relaxed` is the correct tool.

**b) Task self-deletion race (Batches 2, 5):**
Both SensorManager and InterruptManager have the pattern: `taskHandle = NULL; vTaskDelete(NULL);`. Between setting NULL and actual deletion, the task is still executing. If Core 1 checks the handle at exactly this moment, it creates a new task while the old one still exists. Proper pattern: task notification or event group for exit handshake.

**c) Cross-core pointer sharing without barriers (Batch 2):**
`activeSummary` and `activeConfig` pointers are set by Core 1 and read by Core 0. Safety depends on `xTaskCreatePinnedToCore()` providing an implicit barrier. Undocumented.

**d) I2C bus contention (Batches 3, 5):**
CalibrationManager and InterruptManager's processing task both access the I2C bus from Core 1. SensorManager accesses it from Core 0. Safety relies entirely on main.cpp never running conflicting operations simultaneously — neither class enforces the invariant.

**e) `InterruptManager::_stats.isrCount++` in ISR context (Batch 5):**
Plain `uint32_t` incremented in ISR, read from Core 1. Likely safe on Xtensa but not guaranteed by C++.

## 5. Header Hygiene & Include Chains

**a) Heavy transitive chains:**

The worst chain: `DataTransmitter.h` → `SessionManager.h` → `SensorManager.h` → `Adafruit_VCNL4040.h`. Including DataTransmitter pulls in the Adafruit sensor library, the I2C wire library, and the full SensorManager class definition. SessionManager only needs `SensorReading` and `InterruptEvent` from those headers.

Another chain: `DataTransmitter.h` → `MQTTManager.h` → `NetworkManager.h` → `<WiFi.h>`, `<WiFiClientSecure.h>`, `<LittleFS.h>`, `<ArduinoJson.h>`. DataTransmitter only needs `MQTTManager*`.

**b) Includes that belong in .cpp, not .h:**
- `MQTTManager.h`: `<LittleFS.h>` (only used in .cpp)
- `NetworkManager.h`: `<LittleFS.h>`, `<ArduinoJson.h>` (only used in .cpp)
- `SessionManager.h`: `<ArduinoJson.h>` (never used at all)

**c) Type headers needed:**
Three "lightweight types" headers would break the major transitive chains:
- `SensorTypes.h`: `SensorReading`, `SensorMetadata`, `NUM_SENSORS`, `SAMPLE_RATE_HZ`
- `DetectionTypes.h`: `Direction`, `DetectionResult`, `DetectorConfig`, `WaveState`, `DetectorState`, `IDetector`
- `InterruptTypes.h`: `InterruptEventType`, `InterruptEvent`, `InterruptMode`, `InterruptConfig`, `InterruptSessionStats`

**d) Mixed include guard styles:**
13 headers use `#ifndef`/`#define`/`#endif`, 7 use `#pragma once`. Should pick one (recommend `#pragma once`).

## 6. Global State & Cross-Cutting Concerns

**a) `extern bool serialStudioEnabled` in 6 files:**

| File | Type |
|------|------|
| `main.cpp` | Definition (`bool serialStudioEnabled = SERIAL_STUDIO_DEFAULT;`) |
| `SensorManager.cpp` | `extern` declaration |
| `DirectionDetector.cpp` | `extern` declaration |
| `SessionManager.cpp` | `extern` declaration |
| `LEDController.cpp` | `extern` declaration |
| `MemoryMonitor.h` | `extern` declaration **in a header** |

Every occurrence follows the same pattern: gate Serial.print output. A `debug_log.h` header with the `extern` declared once (plus a logging macro or inline helper) eliminates all scattered declarations.

**b) ~30 mutable globals in main.cpp (Batch 1):**
Component instances, session state, timing variables, detection flags, configuration pointers — all as file-scope globals. Makes testing impossible and reasoning about data flow difficult. These should migrate into an `Application` class or at minimum into the modules that own each responsibility.

**c) Duplicate config loading (Batch 6):**
Both NetworkManager and MQTTManager parse `/config.json` independently. LittleFS is initialized by NetworkManager but used by MQTTManager — creating an implicit ordering dependency.

## 7. Magic Numbers & Shared Constants

Constants that appear in multiple files without unification:

| Constant | Value | Files |
|----------|-------|-------|
| I2C clock speed | `400000` | SensorManager, InterruptManager |
| IR duty denominator | `40` | InterruptManager ×2, SerialStudioOutput ×2 |
| MUX settle time | `5` ms | SensorManager, InterruptManager |
| Config JSON capacity | `1024` | NetworkManager, MQTTManager |
| Config file path | `"/config.json"` | NetworkManager, MQTTManager |
| Heap warning threshold | `50000` | MemoryMonitor ×2 |
| PSRAM warning threshold | `1000000` | MemoryMonitor ×2 |
| Default LED current | `200` | CalibrationData, main.cpp |

Additionally, every batch identified per-module magic numbers (pixel offsets, timing constants, buffer sizes, JSON capacities) that should be named constants. The total count across all batches is ~80 individual values.

The codebase mixes three constant styles: `#define` macros (InterruptManager, CalibrationManager, LEDController), `static constexpr` (MLDetector), and struct fields with defaults (DetectorConfig). `static constexpr` is preferred for compile-time constants in C++; runtime-configurable parameters should be in config structs.

## 8. Correctness Bugs

These are not theoretical — they produce wrong results under specific (reproducible) conditions.

**a) `StatsAccumulator::sumSq` overflow (Batch 3 — high priority):**
`sumSq` is `uint32_t` accumulating `value²` where value is `uint16_t`. At ~100 samples (normal for a 600ms baseline), `sumSq` overflows `uint32_t`, producing garbage in `getStdDev()`. Similarly, `sum * sum` overflows if `sum > 65,535` (~4 samples at max signal). **Fix:** change `sumSq` to `uint64_t`, cast `sum * sum` to `uint64_t`.

**b) `SessionManager::finalizeSessionSummary()` `const_cast` (Batch 4):**
Uses `const_cast` to mutate a `const SensorConfiguration*` parameter — undefined behavior if the pointed-to object is genuinely const.

**c) VLA in `MQTTManager::messageCallback()` (Batch 6):**
`char message[length + 1]` is a variable-length array on the stack. Not standard C++, and if a large payload arrives (buffer is 32KB), this overflows the stack.

**d) `MLDetector::lastResult_` uninitialized (Batch 3):**
`DetectionResult lastResult_` has no default constructor or member initializers. If `getResult()` is called before any detection occurs, it returns uninitialized memory.

**e) `SAMPLE_RATE_HZ` macro used as transmission metadata (Batch 4):**
`doc["sample_rate"] = SAMPLE_RATE_HZ` hardcodes 1000, but the actual sample rate is configurable via cloud config. If the configured rate differs, transmitted data contains conflicting values.

## 9. Dead Code

Confirmed dead code across the codebase:

| Item | Location | Lines |
|------|----------|-------|
| `Adafruit_VCNL4040 sensors[NUM_SENSORS]` array | SensorManager.h | Declared, never used |
| `#include <Adafruit_VCNL4040.h>` | SensorManager.h | Only for enum types (replaceable) |
| `debugI2CScan()` | SensorManager.cpp | ~180 lines, gated behind unused flag |
| `dumpSensorConfiguration()` | SensorManager.cpp | ~175 lines, diagnostic only |
| `systemInitialized` global | main.cpp | Set but never read |
| `configString` member + `setConfigString()` | DisplayManager | Set but never rendered |
| `CalibrationState` forward declaration | DisplayManager.h | Never referenced |
| `showBootScreen()` / `updateStatus()` | DisplayManager.cpp | Legacy wrappers |
| Static `messageCallback()` | MQTTManager.cpp | Immediately overwritten by `setCallback()` |
| `DetectorConfig::minGapForConfidence`, `minSignalForConfidence` | DirectionDetector.h | Declared, never referenced |
| `MLDetector::getFrameCount()` | MLDetector.h | Never called |
| `CalibrationManager::configureSensorForCalibration()` | CalibrationManager.cpp | Empty method |
| `#include <vector>` | DirectionDetector.h | std::vector never used |
| `#include <ArduinoJson.h>` | SessionManager.h | ArduinoJson never used |
| SD card pin definitions | pin_config.h | SD card not used, pins conflict |

---

## Prioritized Recommendation Plan

Recommendations are organized into four phases. Each phase is a natural stopping point — the codebase is better after any completed phase, and later phases build on earlier ones.

### Phase 1: Foundation (creates shared infrastructure, enables later phases)

Low risk, high leverage. Primarily new files and include changes — minimal modification of existing logic.

| # | Task | What It Does | Effort |
|---|------|-------------|--------|
| 1.1 | Create `SensorTypes.h` | Extract `SensorReading`, `SensorMetadata`, `NUM_SENSORS`, `SAMPLE_RATE_HZ` from `SensorManager.h`. Breaks the heaviest transitive include chain. | Small |
| 1.2 | Create `DetectionTypes.h` | Extract `Direction`, `DetectionResult`, `DetectorConfig`, `WaveState`, `DetectorState` from `DirectionDetector.h`. Add `IDetector` interface. | Small |
| 1.3 | Create `InterruptTypes.h` | Extract `InterruptEventType`, `InterruptEvent`, `InterruptMode`, `InterruptConfig`, `InterruptSessionStats` from `InterruptManager.h`. | Small |
| 1.4 | Create `RingBuffer.h` | Extract generic `RingBuffer<T,SIZE>` from `DirectionDetector.h` into standalone utility. | Trivial |
| 1.5 | Create `debug_log.h` | Centralize `extern bool serialStudioEnabled` + `DEBUG_LOG(...)` macro. Replace 5 scattered `extern` declarations. | Trivial |
| 1.6 | Create `constants.h` | Unify shared constants: `I2C_CLOCK_HZ`, `MUX_SETTLE_MS`, `DEFAULT_IR_DUTY_DENOMINATOR`, `CONFIG_JSON_CAPACITY`, `CONFIG_FILE_PATH`, memory thresholds. | Small |
| 1.7 | Header cleanup | Move `<LittleFS.h>`, `<ArduinoJson.h>` from headers to .cpp files. Add forward declarations. Remove unused includes. | Small |
| 1.8 | Pin config cleanup | Rename `PIN_IIC_*` → `PIN_I2C_*`. Remove dead SD card definitions. | Trivial |
| 1.9 | Unify include guards | Convert all headers to `#pragma once`. | Trivial |
| 1.10 | Per-module magic numbers | Convert remaining `#define` constants to `static constexpr`. Name per-module magic numbers per the tables in PLAN.md. | Small |

### Phase 2: Correctness & Safety (fix bugs and hazards, targeted changes)

Each task is a focused fix that can be compiled and tested independently. No structural changes.

| # | Task | What It Does | Effort |
|---|------|-------------|--------|
| 2.1 | Fix `StatsAccumulator` overflow | Change `sumSq` to `uint64_t`, cast `sum*sum` to `uint64_t` in `getStdDev()`. | Trivial |
| 2.2 | Replace `volatile` with `std::atomic` | `SensorManager::stopRequested`, `InterruptManager::_monitoring`, `_stats.isrCount`. Coordinate in one pass. | Small |
| 2.3 | Fix task self-deletion races | Use task notification for exit handshake in both SensorManager and InterruptManager. | Small |
| 2.4 | Fix `const_cast` in SessionManager | Change parameter to non-const or restructure return flow. | Trivial |
| 2.5 | Fix streaming publish cleanup | Call `endPublish()` or disconnect after partial chunk-write failure in MQTTManager. | Trivial |
| 2.6 | Fix `readSensor()` silent failure | Return distinct error indicator (sentinel value or error code) on I2C failure. | Small |
| 2.7 | Add null/overflow guards | Guard `dataQueue` before `xQueueReceive()`. Add `doc.overflowed()` checks in remaining transmission paths. Make `DisplayManager::init()` return `bool`. | Trivial |
| 2.8 | Fix VLA in messageCallback | Replace `char message[length+1]` with fixed buffer + length check. | Trivial |
| 2.9 | Fix sample rate metadata | Use `config->actual_sample_rate_hz` instead of `SAMPLE_RATE_HZ` macro in transmission. | Trivial |
| 2.10 | Initialize `MLDetector::lastResult_` | Add default member initializers to `DetectionResult`. | Trivial |
| 2.11 | Remove dead code | Delete all items listed in §9 above. | Small |
| 2.12 | Fix string accessor return types | Change `NetworkManager::getDeviceId()`, `getApiEndpoint()` to return `const String&`. | Trivial |
| 2.13 | Guard calibrate/configure during monitoring | Add `if (_monitoring) return false;` to InterruptManager's `calibrateSensors()` and `configure()`. | Trivial |
| 2.14 | Conditional debug logging | Gate PSRAMAllocator logging with `#ifdef`, InterruptManager sensor debug with `#ifdef`, NetworkManager file listing with `#ifdef`. | Trivial |

### Phase 3: Structural Decomposition (the big refactoring)

These tasks change file boundaries and module structure. Each should be compiled and tested independently. Ordered so that earlier tasks create infrastructure that later tasks depend on.

| # | Task | What It Does | Lines Impact | Effort |
|---|------|-------------|-------------|--------|
| 3.1 | Extract `ConfigLoader` | Single class parses `/config.json` once. Both NetworkManager and MQTTManager receive config. Eliminates duplicate parsing and implicit LittleFS ordering. | -80 (net) | Small |
| 3.2 | Adopt MuxController in SensorManager | Replace TCA9548A + inline PCA9546A + manual channel management with existing MuxController. Eliminate 7 cleanup blocks. | -200 | Medium |
| 3.3 | Adopt VCNL4040 driver in SensorManager | Replace all raw `Wire` I2C patterns with driver methods. Three behavioral differences must be handled (see PLAN.md Batch 2 §10 risk notes). | -250 | Medium |
| 3.4 | Extract JSON serialization helpers | `serializeCalibration()`, `serializeConfig()`, `serializeReadingsArray()`, `serializeSummary()` in DataTransmitter. Eliminates 4× / 3× / 2× / 2× duplication. | -200 | Small |
| 3.5 | Extract `BinarySerializer` | Move `transmitLiveDebugCaptureBinary()` (~180 lines) out of DataTransmitter. | -180 | Small |
| 3.6 | Extract `CalibrationScreen` | Move 8 calibration rendering methods (~320 lines) from DisplayManager. | -320 | Small |
| 3.7 | Extract `CommandHandler` from main.cpp | All command parsing and dispatch (~800 lines). Receives references to managers. | -800 | Large |
| 3.8 | Extract `CloudConfig` from main.cpp | `fetchConfigFromCloud()` + shared config-parsing helper. | -250 | Medium |
| 3.9 | Create `IDetector` interface + `DetectionController` | Shared detector interface. Unify play-mode and live-debug detection loops into one parameterized flow. | -250 from main.cpp | Medium |
| 3.10 | Extract `CollectionController` from main.cpp | Start/stop orchestration for both interrupt and polling modes. | -200 | Medium |
| 3.11 | Extract `ButtonHandler` from main.cpp | Button reading, debounce, long-press. | -90 | Small |
| 3.12 | Simplify CalibrationManager state enum | Reduce 12 states to ~9 generic states + `_currentPCB`. Replace `static` locals with instance members. | -60 | Medium |
| 3.13 | Extract SensorManager diagnostics | Move `debugI2CScan()` and `dumpSensorConfiguration()` to diagnostic module. | -355 | Small |
| 3.14 | Extract TFLite runtime from MLDetector | Move init, model loading, arena allocation into `TFLiteRuntime`. | -130 | Medium |

### Phase 4: Behavioral Improvements (change how things work)

These tasks modify runtime behavior. Higher risk, requiring more thorough testing.

| # | Task | What It Does | Effort |
|---|------|-------------|--------|
| 4.1 | Non-blocking WiFi/MQTT reconnection | Replace `delay()`-based blocking loops with state machines. Track `lastAttemptMs`, `attemptCount`. Add exponential backoff. `loop()` drives reconnection incrementally. | Medium |
| 4.2 | Non-blocking data transmission | Replace `delay()` between batches with cooperative batching. Return to `loop()` between batches. Track batch offset as member state. Call `mqttClient.loop()` between batches. | Medium |
| 4.3 | Replace `taskYIELD()` with `xTaskNotifyFromISR()` | InterruptManager processing task sleeps at zero CPU cost until ISR fires. Eliminates busy-loop waste and reduces latency. | Small |
| 4.4 | Eliminate `delay()` in CalibrationManager | Replace 3× `delay(1500)` with timer-based sub-states (`SUCCESS_DISPLAY`, `FAILURE_DISPLAY`). Prerequisite: Phase 3 state enum simplification. | Small |
| 4.5 | Add batch retry logic | Per-batch retry (1-2 attempts) in DataTransmitter before failing the entire session. | Small |

### Expected Outcome

After all four phases:
- **main.cpp:** 1,845 → ~150-200 lines (delegation only)
- **SensorManager.cpp:** 1,429 → ~300-400 lines (orchestration + delegation)
- **DataTransmitter.cpp:** 769 → ~350-400 lines (orchestration + delegation)
- **DisplayManager.cpp:** 874 → ~550 lines (calibration screens extracted)
- No file exceeds 600 lines
- Network failures no longer freeze the device
- Concurrency patterns are correct, not just accidentally safe
- Include chains are minimal — type headers break all heavy transitive dependencies
- Magic numbers are named constants
- Dead code is removed

---

## Follow-On Initiative Recommendation

### Structure

A single initiative: **"Firmware Architecture Refactor — Implementation"** (or similar). The four phases above map naturally to the TASKS.md structure. Each phase is a checkpoint — the codebase is strictly better after each completed phase, and later phases can be deferred without harm.

### Approach

**BRIEF.md** should scope the initiative to the specific refactoring work defined in this report. The "what's in" list is the four phases; "what's out" includes feature additions, algorithm changes, and hardware driver rewrites. The key constraint is the same as this audit: zero functional regressions after each step. Compile, flash, verify behavior matches before moving on.

**PLAN.md** can be lightweight — the detailed technical analysis lives in this audit's PLAN.md (which should be referenced, not duplicated). The new PLAN.md covers execution strategy: how to verify each change, what to test, and any dependencies between tasks.

**TASKS.md** is the four phases from §Prioritized Recommendation Plan above, broken into checkable items. Each item is a single compilable change.

### How to Use This Report

The new initiative's BRIEF should reference this report: `See docs/initiatives/firmware-refactor/REPORT.md for the audit findings.` Sessions working on the refactoring can read this report's relevant section for context on *why* a change is recommended, then consult PLAN.md's batch analysis for the specific line numbers and code patterns involved.

### Phasing Considerations

- **Phase 1 is prerequisite** for Phase 3 (type headers must exist before files that use them can be decomposed).
- **Phase 2 is independent** — can be done before, after, or interleaved with Phase 1.
- **Phase 3 tasks are mostly independent of each other** — e.g., DataTransmitter decomposition doesn't depend on main.cpp decomposition. But main.cpp's `DetectionController` extraction (3.9) depends on `IDetector` from Phase 1 (1.2).
- **Phase 4 depends on Phase 3** for CalibrationManager (4.4 requires 3.12), but networking changes (4.1, 4.2) are independent.
- **Phases 1-2 are low risk** and can move quickly (1-2 sessions each).
- **Phase 3 is the core work** and will take the most sessions. main.cpp decomposition (3.7-3.11) is the largest single effort.
- **Phase 4 is optional but high-value** for field reliability.

The initiative could reasonably stop after Phase 2 (bugs fixed, foundation in place) or Phase 3 (structure clean) and still represent a significant improvement. Phase 4 adds resilience that matters most for untethered field testing.

---

*Audit conducted across 6 sessions, March 2026. Detailed per-file analysis in PLAN.md (~1,300 lines). Source files reviewed: main.cpp, SensorManager, MuxController, VCNL4040, SensorConfiguration, TCA9548A, DirectionDetector, MLDetector, CalibrationManager, CalibrationData, SessionManager, DataTransmitter, PSRAMAllocator, DisplayManager, InterruptManager, LEDController, SerialStudioOutput, MQTTManager, NetworkManager, MemoryMonitor, pin_config.h.*

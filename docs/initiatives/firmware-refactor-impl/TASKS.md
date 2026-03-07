# Firmware Architecture Refactor — Implementation Tasks

Each task is one compilable, flashable step. Tasks within a phase are ordered by dependency — do them in sequence unless noted otherwise. See REPORT.md for rationale and PLAN.md (audit) for line-level details.

## Phase 1: Foundation

Creates shared infrastructure. Mostly new files and include changes — low risk.

- [x] **1.1** Create `firmware/include/sensor_types.h` — extract `SensorReading`, `SensorMetadata`, `NUM_SENSORS`, `SAMPLE_RATE_HZ` from `SensorManager.h`. Update all includers.
- [x] **1.2** Create `firmware/include/detection_types.h` — extract `Direction`, `DetectionResult`, `DetectorConfig`, `WaveState`, `DetectorState` from `DirectionDetector.h`. Define `IDetector` interface.
- [x] **1.3** Create `firmware/include/interrupt_types.h` — extract `InterruptEventType`, `InterruptEvent`, `InterruptMode`, `InterruptConfig`, `InterruptSessionStats` from `InterruptManager.h`.
- [x] **1.4** Create `firmware/include/ring_buffer.h` — extract generic `RingBuffer<T,SIZE>` from `DirectionDetector.h`.
- [x] **1.5** Create `firmware/include/debug_log.h` — centralize `extern bool serialStudioEnabled` + `DEBUG_LOG(...)` macro. Replace 5 scattered `extern` declarations.
- [x] **1.6** Create `firmware/include/constants.h` — shared constants: `I2C_CLOCK_HZ`, `MUX_SETTLE_MS`, `DEFAULT_IR_DUTY_DENOMINATOR`, `CONFIG_JSON_CAPACITY`, `CONFIG_FILE_PATH`, memory thresholds.
- [x] **1.7** Header cleanup — move `<LittleFS.h>`, `<ArduinoJson.h>` from headers to .cpp files. Add forward declarations. Remove unused includes (`<vector>` from DirectionDetector.h, `<ArduinoJson.h>` from SessionManager.h).
- [x] **1.8** Pin config cleanup — rename `PIN_IIC_*` → `PIN_I2C_*`. Remove dead SD card definitions. Replace `LED_PIN` macro in LEDController with `PIN_LED_STRIP_DATA`.
- [x] **1.9** Unify include guards — convert all headers to `#pragma once`.
- [x] **1.10** Per-module magic numbers — convert `#define` constants to `static constexpr` across InterruptManager, CalibrationManager, LEDController. Name per-module magic numbers per audit PLAN.md tables.

## Phase 2: Correctness & Safety

Targeted fixes — a few lines each. No structural changes.

- [x] **2.1** Fix `StatsAccumulator` overflow — change `sumSq` to `uint64_t`, cast `sum*sum` to `uint64_t` in `getStdDev()`. *(Highest priority — produces corrupt calibration data today.)*
- [x] **2.2** Replace `volatile` with `std::atomic` — `SensorManager::stopRequested`, `InterruptManager::_monitoring`, `_stats.isrCount`. Do in one pass.
- [x] **2.3** Fix task self-deletion races — use task notification for exit handshake in SensorManager and InterruptManager.
- [x] **2.4** Fix `const_cast` in `SessionManager::finalizeSessionSummary()`.
- [x] **2.5** Fix streaming publish cleanup — call `endPublish()` after partial chunk-write failure in MQTTManager.
- [x] **2.6** Fix `readSensor()` silent failure — return distinct error indicator on I2C failure.
- [x] **2.7** Add null/overflow guards — guard `dataQueue`, add `doc.overflowed()` checks, make `DisplayManager::init()` return `bool`.
- [x] **2.8** Fix VLA in `MQTTManager::messageCallback()` — replace `char message[length+1]` with fixed buffer + length check.
- [x] **2.9** Fix sample rate metadata — use `config->actual_sample_rate_hz` instead of `SAMPLE_RATE_HZ` macro.
- [ ] **2.10** Initialize `MLDetector::lastResult_` — add default member initializers to `DetectionResult`.
- [ ] **2.11** Remove dead code — all items listed in REPORT.md §9.
- [ ] **2.12** Fix string accessor return types — `NetworkManager::getDeviceId()`, `getApiEndpoint()` return `const String&`.
- [ ] **2.13** Guard calibrate/configure during monitoring — add `if (_monitoring) return false;` to InterruptManager.
- [ ] **2.14** Conditional debug logging — gate PSRAMAllocator, InterruptManager debug, NetworkManager file listing with `#ifdef`. *(Also: adopt `DEBUG_LOG()` / `debugPrintEnabled()` from `debug_log.h` (created in 1.5) to replace ad-hoc `if (!serialStudioEnabled)` patterns in main.cpp, DirectionDetector, SessionManager, SensorManager, LEDController, MemoryMonitor.)*

## Phase 3: Structural Decomposition

File splits and class extractions. Each task is independent unless noted. Largest effort in the initiative.

- [ ] **3.1** Extract `ConfigLoader` — single class parses `/config.json` once. NetworkManager and MQTTManager receive config. *(Depends on 1.6 for `CONFIG_FILE_PATH` constant.)*
- [ ] **3.2** Adopt MuxController in SensorManager — replace TCA9548A + inline PCA9546A with MuxController. *(High risk — read audit PLAN.md Batch 2 §10 risk notes before starting.)*
- [ ] **3.3** Adopt VCNL4040 driver in SensorManager — replace raw I2C with driver methods. Preserve verify-retry on LED current. *(High risk — depends on 3.2. Read audit PLAN.md Batch 2 §10.)*
- [ ] **3.4** Extract JSON serialization helpers in DataTransmitter — `serializeCalibration()`, `serializeConfig()`, `serializeReadingsArray()`, `serializeSummary()`.
- [ ] **3.5** Extract `BinarySerializer` from DataTransmitter — move `transmitLiveDebugCaptureBinary()` to own file.
- [ ] **3.6** Extract `CalibrationScreen` from DisplayManager — move 8 calibration rendering methods (~320 lines).
- [ ] **3.7** Extract `CommandHandler` from main.cpp — all command parsing and dispatch. Do incrementally: one command group at a time. *(Largest single task — ~800 lines.)*
- [ ] **3.8** Extract `CloudConfig` from main.cpp — `fetchConfigFromCloud()` + shared config-parsing helper.
- [ ] **3.9** Create `DetectionController` — unify play-mode and live-debug detection loops using `IDetector` interface. *(Depends on 1.2 for IDetector.)*
- [ ] **3.10** Extract `CollectionController` from main.cpp — start/stop orchestration for interrupt + polling modes.
- [ ] **3.11** Extract `ButtonHandler` from main.cpp — button reading, debounce, long-press.
- [ ] **3.12** Simplify CalibrationManager state enum — reduce 12 states to ~9 generic + `_currentPCB`. Replace `static` locals with instance members.
- [ ] **3.13** Extract SensorManager diagnostics — move `debugI2CScan()` and `dumpSensorConfiguration()` to diagnostic module.
- [ ] **3.14** Extract TFLite runtime from MLDetector — move init, model loading, arena allocation into `TFLiteRuntime`.

## Phase 4: Behavioral Improvements

Runtime behavior changes. Require testing beyond compilation.

- [ ] **4.1** Non-blocking WiFi/MQTT reconnection — replace `delay()` loops with state machines. Add exponential backoff.
- [ ] **4.2** Non-blocking data transmission — cooperative batching with `loop()` re-entry between batches.
- [ ] **4.3** Replace `taskYIELD()` with `xTaskNotifyFromISR()` in InterruptManager.
- [ ] **4.4** Eliminate `delay()` in CalibrationManager — timer-based sub-states. *(Depends on 3.12.)*
- [ ] **4.5** Add batch retry logic in DataTransmitter — per-batch retry (1-2 attempts) before failing session.

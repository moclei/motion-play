# ML Direction Detection — Tasks

## Phase 1: Documentation and setup
- [x] Create BRIEF.md
- [x] Create PLAN.md
- [x] Create TASKS.md
- [x] Verify TFLite Micro PlatformIO library compatibility with arduino-esp32 2.0.14 — `spaziochirale/Chirale_TensorFLowLite@^2.0.0` compiles cleanly. Smoke test with TFLite headers passes. Note: does not include ESP-NN (PIE vector acceleration); generic CMSIS-NN kernels only. Acceptable for initial work, ESP-NN optimization is a future enhancement.
- [x] Set up `tools/ml-training/` Python project structure (requirements.txt, README)

## Phase 2: Data collection
- [x] Confirm Live Debug mode is working end-to-end (detection capture + labeling)
- [x] Define collection protocol: VCNL4040 at 2T integration, 1 pulse. Live Debug for A_TO_B/B_TO_A, regular Debug for NO_TRANSIT (short sessions, one event each)
- [x] Collect 15 A_TO_B events (labeled "a->b", "successful-shot")
- [x] Collect 19 B_TO_A events (labeled "b->a", "successful-shot" or "missed-shot")
- [x] Collect 12 NO_TRANSIT events (labeled "no-transit") — partial/aborted hand waves
- [ ] Collect angled / cross-module transits (both directions) — deferred to Phase 5
- [x] Label all collected sessions via frontend
- [x] Verify data is downloadable via API — `download_sessions.py` fetches all 46 sessions

## Phase 3: Python training pipeline
- [x] Write data download script (`tools/ml-training/download_sessions.py`) — filters by label/date, organizes into class subdirectories
- [x] Write preprocessing: extract (300, 6) matrices from session readings, forward-fill sparse data to 1ms grid, normalize by actual max proximity value (490)
- [x] Implement train/validation/test split (80/20 stratified)
- [x] Define and train initial 1D CNN model — Conv1D(16,5) -> MaxPool -> Conv1D(32,3) -> MaxPool -> Dense(32) -> Dropout(0.3) -> Dense(3, softmax). 78,995 params.
- [x] Evaluate: **90% validation accuracy** (9/10). Confusion: 1 a_to_b misclassified as b_to_a. no_transit perfect (3/3).
- [x] Export TFLite — initially tried dynamic range quantization (86KB) but hybrid models (int8 weights, float32 activations) are not supported by TFLite Micro's Conv2D kernel. Re-exported as fully float32 (321KB). Full int8 blocked by Keras 3 / TF 2.16 MLIR bug.
- [x] Export as C header file (`output/model_data.h`)
- [x] Results documented below

### Phase 3 Results
- **Model**: 1D CNN, (300, 6) input, 3-class softmax output
- **Data**: 46 sessions (15 A_TO_B, 19 B_TO_A, 12 NO_TRANSIT). 36 train / 10 test.
- **Val accuracy**: 90% after 30 epochs (batch size 8)
- **TFLite size**: 321,132 bytes (float32, no quantization). Dynamic range quantization produces hybrid models incompatible with TFLite Micro.
- **Known issues**: Small dataset means likely overfitting. Need more data for production. int8 quantization requires TF/Keras version fix.

## Phase 4: Firmware integration
- [x] Add TFLite Micro library to platformio.ini lib_deps — `spaziochirale/Chirale_TensorFLowLite@^2.0.0`
- [x] Create MLDetector component (`firmware/src/components/detection/MLDetector.h`, `MLDetector.cpp`)
- [x] Implement model loading from flash — `model_data.h` (321KB float32) embedded in `firmware/include/`, loaded via `tflite::GetModel()`. Tensor arena 150KB in PSRAM (40KB actually used).
- [x] Implement input tensor preparation: ring buffer of `MLSensorFrame` (512 frames), extracts 300ms window, forward-fills to 1ms grid, normalizes by 490.0
- [x] Implement inference and output parsing: softmax [A_TO_B, B_TO_A, NO_TRANSIT], confidence threshold 0.6
- [x] Wire trigger mechanism: simplified baseline/threshold (same logic as heuristic), 150ms post-trigger delay to capture full wave
- [x] Add `detection_mode` config option — parsed from cloud config JSON, default "heuristic". Also switchable via `set_detection_mode` MQTT command at runtime. Frontend UI toggle in SettingsModal.
- [x] Wire MLDetector into main loop — conditional in both PLAY and LIVE_DEBUG mode loops. Same LED/display/MQTT feedback path.
- [x] Compiles successfully: RAM 17.9%, Flash 24.0% (with float32 model)
- [x] Fix: Add `EXPAND_DIMS` op to resolver (model uses it for Conv2D reshape). Fix `init()` re-initialization crash by switching from static to heap-allocated resolver/interpreter with proper `deinit()` cleanup.
- [x] Fix: Re-export model as float32 (dynamic range quantization produces hybrid models rejected by TFLite Micro Conv2D kernel with "Hybrid models are not supported" error).
- [x] Deploy updated Lambda functions (`getDeviceConfig`, `updateDeviceConfig`) to support `detection_mode` in cloud config.
- [x] Test: verify inference runs and produces output on device
- [x] Test: verify LED feedback works with ML detection path

### Phase 4 Results — First On-Device Test
- **Inference time**: ~140ms per invocation (float32 on Core 1, no ESP-NN acceleration)
- **Sensor rate impact**: Poll rate drops from ~1000Hz to 20-365Hz during inference (Core 1 blocked)
- **Trigger-to-detection**: 14 triggers in test session, 8 resulted in detections (57%)
- **Confidence range**: 0.569–0.877 on transit events. 5 near-misses just below 0.600 threshold.
- **Direction accuracy**: Correct on all high-confidence detections (A-side triggers → A_TO_B, B-side → B_TO_A)
- **Re-trigger pattern**: Some events trigger 2-3 times before exceeding confidence threshold, which works but isn't ideal
- **Missed events**: 2 user-reported "missed" button presses where model was below threshold
- **Memory**: Heap 92% free, PSRAM 93% free — healthy throughout
- **Comparison to heuristic**: Heuristic has near-instant detection, higher trigger rate, and better coverage of edge cases. ML model is more selective but misses events the heuristic catches. Expected given small training set (46 sessions).

## Phase 5: Evaluation and iteration
- [ ] Compare ML vs heuristic accuracy on the same test events
- [ ] Identify failure cases and weak scenarios
- [ ] Collect additional targeted data for weak scenarios if needed
- [ ] Retrain model with expanded dataset
- [ ] Document findings and next steps

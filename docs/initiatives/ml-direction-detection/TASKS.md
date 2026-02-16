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
- [x] Export TFLite with dynamic range quantization — 86,608 bytes (~85KB). Full int8 blocked by Keras 3 / TF 2.16 MLIR bug.
- [x] Export as C header file (`output/model_data.h`)
- [x] Results documented below

### Phase 3 Results
- **Model**: 1D CNN, (300, 6) input, 3-class softmax output
- **Data**: 46 sessions (15 A_TO_B, 19 B_TO_A, 12 NO_TRANSIT). 36 train / 10 test.
- **Val accuracy**: 90% after 50 epochs (batch size 8)
- **TFLite size**: 86,608 bytes (dynamic range quantization)
- **Known issues**: Small dataset means likely overfitting. Need more data for production. int8 quantization requires TF/Keras version fix.

## Phase 4: Firmware integration
- [x] Add TFLite Micro library to platformio.ini lib_deps — `spaziochirale/Chirale_TensorFLowLite@^2.0.0`
- [x] Create MLDetector component (`firmware/src/components/detection/MLDetector.h`, `MLDetector.cpp`)
- [x] Implement model loading from flash — `model_data.h` (86KB) embedded in `firmware/include/`, loaded via `tflite::GetModel()`. Tensor arena 150KB in PSRAM.
- [x] Implement input tensor preparation: ring buffer of `MLSensorFrame` (512 frames), extracts 300ms window, forward-fills to 1ms grid, normalizes by 490.0
- [x] Implement inference and output parsing: softmax [A_TO_B, B_TO_A, NO_TRANSIT], confidence threshold 0.6
- [x] Wire trigger mechanism: simplified baseline/threshold (same logic as heuristic), 150ms post-trigger delay to capture full wave
- [x] Add `detection_mode` config option — parsed from cloud config JSON, default "heuristic". Also switchable via `set_detection_mode` MQTT command at runtime.
- [x] Wire MLDetector into main loop — conditional in both PLAY and LIVE_DEBUG mode loops. Same LED/display/MQTT feedback path.
- [x] Compiles successfully: RAM 18.0%, Flash 20.5%
- [ ] Test: verify inference runs and produces output on device
- [ ] Test: verify LED feedback works with ML detection path

## Phase 5: Evaluation and iteration
- [ ] Compare ML vs heuristic accuracy on the same test events
- [ ] Identify failure cases and weak scenarios
- [ ] Collect additional targeted data for weak scenarios if needed
- [ ] Retrain model with expanded dataset
- [ ] Document findings and next steps

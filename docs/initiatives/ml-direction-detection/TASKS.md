# ML Direction Detection — Tasks

## Phase 1: Documentation and setup
- [x] Create BRIEF.md
- [x] Create PLAN.md
- [x] Create TASKS.md
- [x] Verify TFLite Micro PlatformIO library compatibility with arduino-esp32 2.0.14 — `spaziochirale/Chirale_TensorFLowLite@^2.0.0` compiles cleanly. Smoke test with TFLite headers passes. Note: does not include ESP-NN (PIE vector acceleration); generic CMSIS-NN kernels only. Acceptable for initial work, ESP-NN optimization is a future enhancement.
- [x] Set up `tools/ml-training/` Python project structure (requirements.txt, README)

## Phase 2: Data collection
- [ ] Confirm Live Debug mode is working end-to-end (detection capture + labeling)
- [ ] Define collection protocol checklist (scenarios to cover, repetitions per direction)
- [ ] Collect ~50+ A_TO_B straight-through events (close to modules + center)
- [ ] Collect ~50+ B_TO_A straight-through events (close to modules + center)
- [ ] Collect angled / cross-module transits (both directions)
- [ ] Collect negative examples: partial transits, ambient interference, no-transit
- [ ] Label all collected sessions via frontend
- [ ] Verify data is downloadable via API and inspect a few sessions for quality

## Phase 3: Python training pipeline
- [ ] Write data download script (fetch labeled live_debug sessions via REST API)
- [ ] Write preprocessing: extract (300, 6) matrices from session readings, normalize, assign labels
- [ ] Implement train/validation/test split
- [ ] Define and train initial 1D CNN model in TensorFlow/Keras
- [ ] Evaluate: accuracy, confusion matrix, per-scenario breakdown
- [ ] Quantize model to int8 TFLite format
- [ ] Export as C header file (model_data.h)
- [ ] Document results and any model architecture adjustments

## Phase 4: Firmware integration
- [x] Add TFLite Micro library to platformio.ini lib_deps — `spaziochirale/Chirale_TensorFLowLite@^2.0.0`
- [ ] Create MLDetector component (firmware/src/components/detection/MLDetector.h, MLDetector.cpp)
- [ ] Implement model loading from flash (embedded header file)
- [ ] Implement input tensor preparation: extract 300ms window from buffer, reshape to (300, 6)
- [ ] Implement inference and output parsing (direction + confidence from softmax)
- [ ] Wire trigger mechanism: threshold crossing triggers ML inference
- [ ] Add `detection_mode` config option to config.json ("heuristic" | "ml")
- [ ] Wire MLDetector into main loop as alternative to DirectionDetector
- [ ] Test: verify inference runs and produces output on device
- [ ] Test: verify LED feedback works with ML detection path

## Phase 5: Evaluation and iteration
- [ ] Compare ML vs heuristic accuracy on the same test events
- [ ] Identify failure cases and weak scenarios
- [ ] Collect additional targeted data for weak scenarios if needed
- [ ] Retrain model with expanded dataset
- [ ] Document findings and next steps

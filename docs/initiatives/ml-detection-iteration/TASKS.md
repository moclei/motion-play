# ML Detection Iteration — Tasks

## Phase 1: Pipeline fixes, versioning, and cleanup

### Pipeline correctness (do before mass data collection)
- [ ] Fix normalization mismatch: update `train.py` `normalize()` to use fixed constant (match firmware's `ML_NORMALIZATION_MAX`) instead of per-sample max
- [ ] Determine optimal normalization constant: analyze dataset for practical max proximity, or use current 490.0 and document rationale
- [ ] Fix window alignment: update `preprocess_session()` to extract windows aligned to trigger-end (matching firmware behavior) instead of centering on peak
- [ ] Retrain with fixes applied, compare accuracy to Phase 3 baseline — expect improvement from fixes alone

### Model versioning
- [ ] Add `MODEL_VERSION` string constant to generated C header (e.g., `"v2.0-float32-46sess"`)
- [ ] Log model version on firmware boot (serial output)
- [ ] Include model version in detection event MQTT messages
- [ ] Create `tools/ml-training/MODEL_CHANGELOG.md` to track training parameters, dataset size, and metrics per version

### Cleanup
- [ ] Clean up verbose `[Config]` debug logging added during Phase 4 troubleshooting
- [ ] Verify lowered confidence threshold (0.55) improves detection rate without excessive false positives
- [ ] Experiment with post-trigger delay (try 200ms instead of 150ms) to see if first-trigger accuracy improves

## Phase 2: Expanded data collection and augmentation

### Data collection
- [ ] Collect 100+ A_TO_B sessions (Live Debug, 2T/1-pulse, labeled "a->b")
- [ ] Collect 100+ B_TO_A sessions (Live Debug, 2T/1-pulse, labeled "b->a")
- [ ] Collect 100+ NO_TRANSIT sessions (regular Debug, short sessions, labeled "no-transit")
- [ ] Include edge cases: center-of-hoop, angled passes, grazing transits, slow hand waves

### Data augmentation (implement in `train.py`)
- [ ] Channel-swap augmentation: swap side-A and side-B channels within each module, flip direction label (A_TO_B ↔ B_TO_A). Doubles directional data.
- [ ] Time-shift augmentation: randomly offset extraction window by ±20-50ms. Improves robustness to trigger timing.
- [ ] Gaussian noise injection: add noise calibrated to actual sensor baseline noise levels
- [ ] Amplitude scaling: multiply proximity values by random factor (0.8-1.2) to simulate distance variation

### Retraining
- [ ] Retrain model with expanded dataset + augmentation, compare metrics to Phase 1 baseline
- [ ] Update model version and changelog

## Phase 3: Frontend-settable ML parameters
- [ ] Add `ml_confidence_threshold` and `ml_post_trigger_delay_ms` to Lambda `sanitizeConfig()` and MQTT payload
- [ ] Parse new config fields in firmware `configure_sensors` handler, apply to MLDetector
- [ ] Add slider/input controls to SettingsModal for ML parameters (visible when detection mode is ML)
- [ ] Test end-to-end: change threshold in frontend → device applies it → verify in serial logs

## Phase 4: Int8 quantization and ESP-NN

### Quantization export
- [ ] Try `experimental_new_converter=False` (TOCO fallback) for full int8 quantization — quickest path, one-line change
- [ ] Try Quantization-Aware Training (QAT) via `tensorflow_model_optimization` — trains with fake quantization nodes
- [ ] Try TF 2.15 / Keras 2 for post-training int8 quantization (avoids MLIR bug)
- [ ] Check if TF 2.17+ fixes the MLIR assertion error
- [ ] Validate int8 model correctness: run inference in Python and compare outputs to float32 model

### ESP-NN integration
- [ ] Research: can `esp-tflite-micro` or community ports (e.g., `tflite-micro-esp-examples`) work with PlatformIO + Arduino? Document findings.
- [ ] If int8 works: integrate ESP-NN optimized kernels and benchmark inference time
- [ ] If int8 blocked: reduce model complexity to speed up float32 inference as fallback

### Quick win: tensor arena placement
- [ ] Experiment: reduce `ML_TENSOR_ARENA_SIZE` to ~48KB, use `malloc()` instead of `ps_malloc()` to place arena in internal SRAM
- [ ] Benchmark inference time with SRAM arena vs PSRAM arena — could provide speedup without any quantization work

## Phase 5: Async inference
- [ ] Create FreeRTOS inference task on Core 1 (waits for trigger, runs inference, posts result)
- [ ] Implement ring buffer snapshot: on trigger, copy relevant 300ms of data into separate buffer for inference task (avoids shared-state contention with main loop)
- [ ] Decouple trigger detection from inference execution in main loop
- [ ] Verify sensor poll rate stays at ~1000Hz during inference
- [ ] Test detection latency and accuracy are not degraded

## Phase 6: Side-by-side comparison mode
- [ ] Add `"comparison"` option to `detection_mode`
- [ ] In comparison mode, feed readings to both DirectionDetector and MLDetector
- [ ] Primary detector drives LEDs/MQTT, secondary logs to serial
- [ ] Add structured comparison fields to detection event MQTT messages (both detector results side by side)
- [ ] Collect comparison data on real events, document accuracy differences

## Phase 7: Validation improvements (ongoing, applies across phases)
- [ ] Implement k-fold cross-validation (5-fold) in training pipeline for more reliable accuracy estimates
- [ ] Track per-module accuracy (M1/M2/M3) to detect module-specific biases in the dataset
- [ ] Implement temporal validation split (train on earlier sessions, test on later) once dataset is large enough
- [ ] Separate validation set from test set for hyperparameter tuning (once dataset supports 3-way split)

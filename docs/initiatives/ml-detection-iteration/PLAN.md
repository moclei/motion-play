# ML Detection Iteration — Plan

## Approach

Build on the working ML detection foundation from `ml-direction-detection` across five tracks: (0) fix pipeline correctness issues, (1) more and better training data, (2) hardware-accelerated inference, (3) frontend tunability, and (4) objective evaluation. Track 0 should be completed before mass data collection (Track 1), since pipeline mismatches make current training data less effective. The remaining tracks are mostly independent and can be worked in parallel.

## Track 0: Pipeline Correctness Fixes

These are training/inference mismatches that likely explain much of the weak confidence (0.57-0.60 range) seen in Phase 4. They should be fixed before collecting more data, since data collected under a broken pipeline may need to be reprocessed.

### Normalization Mismatch (Critical)

The training pipeline and firmware use different normalization schemes:

- **Training (`train.py`):** Per-sample normalization — `X / max(X)`. Each sample is divided by its own maximum, scaling everything to [0, 1] regardless of absolute magnitude.
- **Firmware (`MLDetector.cpp`):** Fixed constant — `proximity / 490.0` (`ML_NORMALIZATION_MAX`).

These are fundamentally different. A training sample with max proximity 100 gets stretched to [0, 1.0], while the same data on-device would be compressed to [0, 0.204]. The model sees different input distributions at training vs inference time.

**Fix:** Use the same fixed normalization constant in both training and firmware. Divide by a well-chosen global constant (e.g., 490.0, or recalculated from dataset statistics). Update `normalize()` in `train.py` to divide by this constant instead of per-sample max.

### Window Alignment Mismatch (Critical)

The training pipeline centers the transit event in the 300ms window (via `find_event_center()`). The firmware captures a 300ms window ending at the current time, after a 150ms post-trigger delay. This means:

- **Training:** Event is in the middle of the window.
- **Inference:** Event is predominantly in the latter portion of the window.

The CNN's convolutional layers are position-sensitive — a model trained on centered events won't generalize well to events shifted to the end.

**Fix options (use one or both):**
1. Align training extraction to match inference: extract windows that end at the trigger point + post-trigger delay, not centered on peak.
2. Use time-shifting augmentation during training to make the model robust to event position within the window.

### Model Versioning

Introduce model versioning from the start so every training run is tracked:

- Add a `MODEL_VERSION` string constant to the generated C header (e.g., `"v2.0-float32-46sess"`)
- Log model version on firmware boot and include in detection event MQTT messages
- Maintain a changelog in `tools/ml-training/` tracking training parameters, dataset size, and metrics per version
- This is low-effort and invaluable for debugging — knowing which model was running when a result was observed

## Track 1: Data Collection and Retraining

### Strategy
The initial model was trained on 46 sessions (15 A_TO_B, 19 B_TO_A, 12 NO_TRANSIT). Many real events produced confidence in the 0.57-0.60 range — just barely below threshold. More data is the highest-impact improvement, but only after Track 0 pipeline fixes are in place.

### Target
- 100+ sessions per class (A_TO_B, B_TO_A, NO_TRANSIT)
- Include edge cases: center-of-hoop passes, angled/cross-module transits, grazing passes, slow hand waves
- Use the same collection protocol: 2T integration, 1 pulse, Live Debug for transit events, regular Debug for NO_TRANSIT

### Data Augmentation Strategy

Data augmentation is high-value with a small dataset. The following augmentations are physically valid for this system:

- **Channel-swap for direction flipping:** Swap side-A and side-B sensor channels within each module and flip the label (A_TO_B ↔ B_TO_A). The sensor geometry is symmetric, so this is physically equivalent. Immediately doubles the directional dataset.
- **Time-shifting (±20-50ms random offset):** Slide the extraction window slightly. Makes the model robust to trigger timing variation and directly addresses the window alignment concern.
- **Gaussian noise injection:** Add noise calibrated to actual sensor noise levels (measurable from baseline readings). Improves robustness to sensor variability.
- **Amplitude scaling (±10-20%):** Multiply proximity values by a random factor. Simulates different object distances and sizes.

Implement augmentation in `train.py` during preprocessing, applied on-the-fly during training or as a dataset expansion step.

### Retraining
- Same pipeline (`tools/ml-training/train.py`) with Track 0 fixes applied
- May experiment with model architecture if accuracy plateaus (deeper network, depthwise separable convolutions, etc.)
- Track metrics across training runs using model versioning (Track 0)

## Track 2: Int8 Quantization and ESP-NN Acceleration

### Why This Matters
The ESP32-S3 has SIMD vector instructions specifically designed for int8 neural network operations. ESP-NN provides optimized TFLite Micro kernels that leverage these. Benchmarks show **~43x speedup** (e.g., person detection: 2300ms → 54ms). For our model, this could mean ~140ms → ~3-5ms.

### Current Blockers
1. **Dynamic range quantization** produces hybrid models (int8 weights, float32 activations) that TFLite Micro rejects.
2. **Full int8 post-training quantization** crashes with a Keras 3 / TF 2.16 MLIR assertion error.
3. **ESP-NN** is bundled with Espressif's `esp-tflite-micro` component (ESP-IDF), not with the Arduino-compatible `Chirale_TensorFLowLite` library we currently use.

### Approach
1. **Resolve int8 export — multiple paths to try:**
   - TensorFlow 2.15 (Keras 2) — avoids the Keras 3 MLIR bug entirely
   - TF 2.17+ — the MLIR bug may be fixed in newer releases
   - `experimental_new_converter=False` — bypasses the MLIR-based converter, falls back to TOCO. One-line change, worth trying first.
   - ONNX → TFLite conversion as an alternative export path
   - **Quantization-Aware Training (QAT):** Train with fake quantization nodes via `tf.quantization` or `tensorflow_model_optimization`. Since we're retraining anyway (Track 1), QAT is natural and often produces better int8 models than post-training quantization. This avoids the PTQ converter entirely.
2. **Integrate ESP-NN:** Investigate whether `esp-tflite-micro` can be used as a PlatformIO library with Arduino framework. Community ports like `tflite-micro-esp-examples` may provide Arduino-compatible builds. If not, explore extracting the ESP-NN optimized kernels and linking them manually.
3. **Validate:** Ensure int8 model produces correct outputs on-device before switching over. Run inference in Python on the int8 model and compare outputs to float32.

### Quick Win: Tensor Arena in Internal SRAM

The tensor arena is currently allocated in PSRAM (150KB via `ps_malloc()`). PSRAM is accessed via SPI/OSPI, which is significantly slower than internal SRAM for the thousands of read/write operations during inference. The actual arena usage is ~40KB — the ESP32-S3 has 512KB internal SRAM, so this may fit.

**Experiment:** Reduce `ML_TENSOR_ARENA_SIZE` to ~48KB, use `malloc()` instead of `ps_malloc()`, and benchmark inference time. This could provide a meaningful speedup even without int8 quantization, and it's a trivial code change.

### Fallback
If int8 + ESP-NN proves too difficult within Arduino constraints:
- Reduce model size (fewer filters, smaller dense layer) to speed up float32 inference
- Move tensor arena to internal SRAM (see above)
- Move inference to async FreeRTOS task (Track 3) to at least unblock the main loop

## Track 3: Async Inference and Frontend Tunability

### Async Inference
Currently, `runInference()` blocks the main loop on Core 1 for ~140ms. This degrades sensor poll rate and delays LED/MQTT responses.

Option: Create a FreeRTOS task on Core 1 that waits for a trigger signal, runs inference in the background, and posts the result back. The main loop continues processing sensor data while inference runs.

**Ring buffer synchronization:** With async inference, the ring buffer becomes a shared resource — the main loop writes new frames while the inference task reads from it. This requires thread-safe handling. Recommended approach: when the trigger fires, snapshot the relevant 300ms of ring buffer data into a separate buffer (owned by the inference task), then pass that snapshot to `prepareInput()`. This avoids mutex contention on the ring buffer during inference and keeps the main loop lock-free.

### Frontend-Settable Parameters
Add the following to the config flow (cloud config → MQTT → firmware → frontend):
- **`ml_confidence_threshold`** (float, default 0.55): Minimum softmax confidence to report a detection
- **`ml_post_trigger_delay_ms`** (uint16, default 150): How long to wait after trigger before running inference, to capture more of the wave

These would appear in the SettingsModal alongside the existing ML toggle, as sliders or numeric inputs. The firmware would parse them from `sensor_config` in the same way as `detection_mode`.

## Track 4: Side-by-Side Comparison

### Concept
Run both `DirectionDetector` (heuristic) and `MLDetector` simultaneously. Only one drives LED output (configurable), but both log their results. This provides:
- Direct accuracy comparison on identical events
- Data for identifying ML failure modes
- Confidence calibration (what heuristic confidence corresponds to what ML confidence)

### Implementation
- Add a `"comparison"` option to `detection_mode` (in addition to `"heuristic"` and `"ml"`)
- In comparison mode, both detectors receive every reading
- Primary detector (configurable) drives LEDs and MQTT events
- Secondary detector logs to serial only

### Structured Cloud Logging (Recommended)
Log both detector results to the cloud for systematic analysis, not just serial. Add fields to the detection event MQTT message:

```json
{
  "primary_detector": "heuristic",
  "primary_result": { "direction": "A_TO_B", "confidence": 0.82 },
  "secondary_detector": "ml",
  "secondary_result": { "direction": "A_TO_B", "confidence": 0.61 }
}
```

This enables analysis in DynamoDB without needing to be physically watching serial output during every test session.

## Cross-Cutting: Validation Strategy

The current evaluation uses a single 80/20 stratified split, with the test set also used as validation data during training. This should improve as the dataset grows:

- **K-fold cross-validation (5-fold):** Gives more reliable accuracy estimates than a single split, especially important with <300 samples.
- **Per-module evaluation:** Track accuracy separately for events on M1 (6 o'clock), M2 (9 o'clock), and M3 (3 o'clock). If most training data comes from one module, the model may not generalize to others.
- **Temporal split:** Train on earlier sessions, test on later ones. Catches temporal biases (sensor drift, environmental changes between collection batches).
- **Proper train/val/test split:** As the dataset grows, use a separate validation set for hyperparameter tuning rather than reusing the test set.

## Future Investigation: Per-Module Architecture

The current model takes `(300, 6)` input — all 6 sensors. An alternative worth investigating: a `(300, 2)` model that only takes the triggering module's A and B channels. Benefits: ~3x smaller/faster, invariant to which module triggered, data from all 3 modules usable interchangeably (3x effective dataset).

**Concern:** Cross-module transits are a real scenario. An object passing at an angle could trigger side A of module 1 and then side B of module 2 (not module 1). A per-module model would miss this entirely. The 6-channel model handles cross-module events naturally. Investigation needed: analyze existing data to determine how common cross-module transit patterns actually are. If rare, per-module could work for a fast-path with the 6-channel model as fallback. If common, the 6-channel architecture is the right choice.

## Open Questions

- Can `esp-tflite-micro` be used as a PlatformIO lib with Arduino framework, or does it strictly require ESP-IDF? Are there community Arduino-compatible ports?
- Is the Keras 3 / TF 2.16 int8 quantization bug fixed in newer TF releases (2.17+)?
- Does `experimental_new_converter=False` (TOCO fallback) support full int8 quantization for our model?
- For async inference, what's the best synchronization pattern? Ring buffer snapshot approach (recommended) vs mutex-protected shared buffer?
- What is the optimal fixed normalization constant? Should it be dataset-derived (e.g., 99th percentile of all proximity values) or hardware-derived (practical max for VCNL4040 at operating distance)?
- How common are cross-module transit patterns in real usage? (Determines viability of per-module architecture.)

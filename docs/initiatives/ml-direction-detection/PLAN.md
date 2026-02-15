# ML Direction Detection — Plan

## Approach

Replace the hand-tuned heuristic detection algorithm with (or supplement it by) a small neural network that classifies transit direction from raw proximity data. The pipeline has three stages: collect labeled data via the existing Live Debug mode, train and quantize a model in Python, and deploy it on the ESP32-S3 using TensorFlow Lite Micro with hardware-accelerated inference via ESP-NN.

The existing `DirectionDetector` (heuristic) remains as a selectable alternative. A config flag chooses which detection path drives LED feedback and events.

## Framework Choice: TFLite Micro

**Decision:** TensorFlow Lite Micro, not ESP-DL.

Rationale:
- The project uses Arduino framework on PlatformIO. ESP-DL requires ESP-IDF — adopting it would mean migrating the entire build system.
- TFLite Micro has Arduino-compatible libraries available on PlatformIO (`TensorFlowLite_ESP32`, `ArduTFLite`, `pio-tflite-lib`).
- ESP-NN (Espressif's optimized int8 neural network kernels) is automatically compiled as part of TFLite Micro on ESP32-S3, providing PIE vector instruction acceleration (4-10x speedups on quantized ops).
- TensorFlow/Keras ecosystem for model training is widely documented.
- Switching model architectures within TFLite Micro is trivial; switching to ESP-DL later would require an ESP-IDF migration.

## Technical Notes

### 1. Data Collection Strategy

Leverage the existing Live Debug mode to collect labeled transit windows. Each captured event is already a short sensor data window with a label — exactly what ML training needs.

**Collection protocol:**
- Use Live Debug mode with current hardware setup
- Systematic passes covering the key transit scenarios from `docs/detection-algorithm.md`:
  - Straight-through close to each module (easy case, high signal)
  - Center-of-hoop passes (weak signal, tests sensitivity)
  - Angled / cross-module transits
  - Grazing transits (very close to tube, tiny CoM gap)
  - Slow hand passes
- Each direction (A_TO_B, B_TO_A) for each scenario type
- Label each event via frontend: correct direction, wrong direction, missed
- Also capture negative examples: partial/aborted transits, ambient interference, no-transit periods
- **Initial target:** ~50+ labeled events per direction to train a first model. More for refinement.

**Data format:** Sessions are already in DynamoDB with readings containing `timestamp_us`, `position` (0-5), `proximity`, and `ambient`. The existing REST API + CSV export provides the download path.

### 2. Python Training Pipeline

A standalone Python project in `tools/ml-training/`:

**Data download and preprocessing:**
- Download labeled `live_debug` sessions via REST API
- For each session, extract readings into a matrix: one row per millisecond, one column per sensor position (0-5), cell value = proximity reading
- Pad/trim to fixed window size: 300 timesteps (300ms at 1kHz)
- Normalize values to 0-1 range (VCNL4040 proximity is 16-bit, 0-65535)
- Assign label from session metadata: A_TO_B, B_TO_A, or NO_TRANSIT
- Train/validation/test split

**Model architecture (initial — small 1D CNN):**
```
Input: (300, 6)  — 300 timesteps, 6 proximity channels
  → Conv1D(16 filters, kernel_size=5, ReLU)
  → MaxPool1D(pool_size=2)
  → Conv1D(32 filters, kernel_size=3, ReLU)
  → MaxPool1D(pool_size=2)
  → Flatten
  → Dense(32, ReLU)
  → Dense(3, Softmax)   # A_TO_B, B_TO_A, NO_TRANSIT
```

- Estimated ~5-10KB of parameters
- ~300K multiply-accumulate operations per inference
- With ESP-NN int8 acceleration: ~0.3-1ms inference on ESP32-S3

**Training and export:**
- Train with TensorFlow/Keras
- Evaluate accuracy, confusion matrix, per-scenario breakdown
- Quantize to int8 using TFLite post-training quantization (required for ESP-NN acceleration)
- Convert: `xxd -i model.tflite > model_data.h` for embedding in firmware

### 3. Window Size Rationale

**Transit speed analysis:**

| Scenario | Speed | Detection zone transit | Full A+B wave |
|----------|-------|----------------------|---------------|
| Fast throw | 5-15 m/s | 7-40ms | 10-60ms |
| Medium toss | 2-5 m/s | 20-100ms | 40-150ms |
| Slow hand pass | 0.5-2 m/s | 50-400ms | 100-500ms |

The current heuristic uses `maxWaveDurationMs` (200ms) + `maxPeakGapMs` (150ms) = 350ms total window. The Live Debug capture window is 500ms.

**Chosen initial window: 300ms.** This captures fast and medium transits fully with baseline padding on both sides. Slow transits may clip, but they're the easiest to classify (large CoM gap, strong signal). The window size is easy to adjust once we have real data — only the input dimension and preprocessing change; the model architecture stays the same.

### 4. On-Device Inference Integration

**New component:** `MLDetector` in `firmware/src/components/detection/`

**Library:** Add TFLite Micro to PlatformIO `lib_deps`. The `pio-tflite-lib` package or `TensorFlowLite_ESP32` are candidates; need to verify compatibility with arduino-esp32 2.0.14 during setup.

**Trigger-first architecture:**
- Reuse existing threshold/baseline logic (from `DirectionDetector`) to detect "something crossed above the noise floor"
- On trigger: extract the most recent 300ms of sensor data from the buffer
- Reshape into `(300, 6)` input tensor (proximity values only, position-indexed)
- Run TFLite Micro inference
- Output: classification (A_TO_B / B_TO_A / NO_TRANSIT) + softmax confidence
- Drive LED feedback and detection events from ML result

**Core allocation:** Inference runs on Core 1 (networking/display core). Core 0 continues uninterrupted sensor collection at 1kHz. The inference is fast enough (~1ms) that it won't meaningfully block Core 1's other responsibilities.

**Memory budget:**
- Model weights: ~5-10KB in flash (int8 quantized)
- TFLite Micro tensor arena: ~10-30KB in SRAM
- Input buffer: ~3.6KB (300 × 6 × 2 bytes)
- PSRAM available: 8MB — plenty of headroom

**Config:** Add `"detection_mode": "heuristic" | "ml"` to `config.json`. The main loop checks this to decide which detector processes sensor data and drives output.

### 5. Relationship to Current Algorithm

The existing `DirectionDetector` (heuristic) and the new `MLDetector` coexist:
- Both consume `SensorReading` data from the same sensor pipeline
- A config flag selects which one is active
- Could optionally run both simultaneously and log comparisons for validation
- The heuristic remains the default and fallback

## Open Questions

- Which TFLite Micro PlatformIO library is best for arduino-esp32 2.0.14? Need to verify during setup phase.
- What is the minimum number of training samples needed for acceptable accuracy? Start with ~50 per class and evaluate.
- Should the trigger threshold be shared with the heuristic's baseline logic, or independent? Start shared, separate if needed.

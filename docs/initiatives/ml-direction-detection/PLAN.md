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

- 78,995 parameters (~309KB float32, ~321KB TFLite)
- ~300K multiply-accumulate operations per inference
- **Actual inference time: ~140ms** (float32, no ESP-NN acceleration). Original estimate of ~0.3-1ms assumed int8 quantization with ESP-NN — hybrid quantization is not supported by TFLite Micro, so the model runs as float32 on generic CMSIS-NN kernels. True int8 quantization (which would enable ESP-NN) is blocked by a Keras 3 / TF 2.16 MLIR bug.

**Training and export:**
- Train with TensorFlow/Keras
- Evaluate accuracy, confusion matrix, per-scenario breakdown
- Export as float32 TFLite (no quantization). Dynamic range quantization creates hybrid models (int8 weights, float32 activations) that TFLite Micro's Conv2D kernel rejects. Full int8 post-training quantization is blocked by a Keras 3 / TF 2.16 MLIR assertion crash. Future: resolve int8 export to enable ESP-NN acceleration.
- Convert to C header via `export_c_header()` in `train.py` for embedding in firmware

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

**Library:** `spaziochirale/Chirale_TensorFLowLite@^2.0.0` — verified compatible with arduino-esp32 2.0.14 on PlatformIO. Includes CMSIS-NN generic kernels but not ESP-NN (PIE vector acceleration). Performance is sufficient for the small model (~300K MACs); ESP-NN optimization can be explored later if needed.

**Trigger-first architecture:**
- Reuse existing threshold/baseline logic (from `DirectionDetector`) to detect "something crossed above the noise floor"
- On trigger: extract the most recent 300ms of sensor data from the buffer
- Reshape into `(300, 6)` input tensor (proximity values only, position-indexed)
- Run TFLite Micro inference
- Output: classification (A_TO_B / B_TO_A / NO_TRANSIT) + softmax confidence
- Drive LED feedback and detection events from ML result

**Core allocation:** Inference runs on Core 1 (networking/display core). Core 0 continues sensor collection, but the sensor poll rate drops significantly during the ~140ms inference window (from ~1000Hz to 20-365Hz) because the main loop on Core 1 is blocked. This is acceptable for initial testing but would benefit from optimization (async inference, or moving inference to a separate FreeRTOS task).

**Memory budget (actual):**
- Model weights: 321KB in flash (float32 TFLite)
- TFLite Micro tensor arena: 150KB allocated in PSRAM, ~40KB actually used
- Ring buffer: 512 × `MLSensorFrame` (16 bytes each) = ~8KB
- Total flash: 24.0% used (1.57MB / 6.5MB)
- PSRAM: 97.4% free after init — plenty of headroom

**Config:** Add `"detection_mode": "heuristic" | "ml"` to `config.json`. The main loop checks this to decide which detector processes sensor data and drives output.

### 5. Relationship to Current Algorithm

The existing `DirectionDetector` (heuristic) and the new `MLDetector` coexist:
- Both consume `SensorReading` data from the same sensor pipeline
- A config flag selects which one is active
- Could optionally run both simultaneously and log comparisons for validation
- The heuristic remains the default and fallback

## Open Questions (Resolved)

- **Minimum training samples?** 46 sessions (15/19/12 per class) yielded 90% validation accuracy. On-device, ~57% of triggers result in detections. More data would improve reliability, especially for edge cases near the confidence threshold.
- **Shared trigger threshold?** Yes — the ML detector reuses the heuristic's baseline/threshold logic for triggering. This works well: the trigger fires on real activity, and the ML model classifies direction. The main issue is that some triggers fire too early (before the full wave), producing low-confidence results that miss the threshold.

## Learnings from Phase 4

1. **Dynamic range quantization is incompatible with TFLite Micro.** The converter produces hybrid models (int8 weights, float32 activations) that the Conv2D kernel rejects. Must use either fully float32 or fully int8.
2. **TFLite op resolver must include all ops the model uses.** The Keras Conv1D → TFLite Conv2D conversion introduces `EXPAND_DIMS` ops not in the original architecture.
3. **Static TFLite objects prevent re-initialization.** Resolver and interpreter must be heap-allocated (not `static` locals) if `init()` may be called more than once.
4. **140ms inference is usable but slow.** The heuristic is near-instant. The ~140ms float32 inference blocks the main loop and degrades sensor poll rate. True int8 quantization with ESP-NN could bring this to ~1-5ms.
5. **Confidence threshold of 0.6 is borderline.** Many real events produce confidence in the 0.57-0.60 range. Lowering to 0.55 would catch more events but may increase false positives. More training data is the better path.
6. **Re-trigger behavior is a feature, not a bug.** When the first trigger misses the threshold, subsequent triggers on the same event often succeed with higher confidence as more of the wave is captured.

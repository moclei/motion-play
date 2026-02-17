# ML Detection Iteration — Plan

## Approach

Build on the working ML detection foundation from `ml-direction-detection` across four tracks: (1) more and better training data, (2) hardware-accelerated inference, (3) frontend tunability, and (4) objective evaluation. These tracks are mostly independent and can be worked in parallel.

## Track 1: Data Collection and Retraining

### Strategy
The initial model was trained on 46 sessions (15 A_TO_B, 19 B_TO_A, 12 NO_TRANSIT). Many real events produced confidence in the 0.57-0.60 range — just barely below threshold. More data is the highest-impact improvement.

### Target
- 100+ sessions per class (A_TO_B, B_TO_A, NO_TRANSIT)
- Include edge cases: center-of-hoop passes, angled/cross-module transits, grazing passes, slow hand waves
- Use the same collection protocol: 2T integration, 1 pulse, Live Debug for transit events, regular Debug for NO_TRANSIT
- Consider data augmentation (time-shifting, noise injection) to stretch the dataset further

### Retraining
- Same pipeline (`tools/ml-training/train.py`)
- May experiment with model architecture if accuracy plateaus (deeper network, attention, etc.)
- Track metrics across training runs for comparison

## Track 2: Int8 Quantization and ESP-NN Acceleration

### Why This Matters
The ESP32-S3 has SIMD vector instructions specifically designed for int8 neural network operations. ESP-NN provides optimized TFLite Micro kernels that leverage these. Benchmarks show **~43x speedup** (e.g., person detection: 2300ms → 54ms). For our model, this could mean ~140ms → ~3-5ms.

### Current Blockers
1. **Dynamic range quantization** produces hybrid models (int8 weights, float32 activations) that TFLite Micro rejects.
2. **Full int8 post-training quantization** crashes with a Keras 3 / TF 2.16 MLIR assertion error.
3. **ESP-NN** is bundled with Espressif's `esp-tflite-micro` component (ESP-IDF), not with the Arduino-compatible `Chirale_TensorFLowLite` library we currently use.

### Approach
1. **Resolve int8 export:** Try TensorFlow 2.15 (Keras 2), or export via ONNX→TFLite, or use `tf.lite.TFLiteConverter` with a representative dataset for full integer quantization.
2. **Integrate ESP-NN:** Investigate whether `esp-tflite-micro` can be used as a PlatformIO library with Arduino framework. If not, explore extracting the ESP-NN optimized kernels and linking them manually.
3. **Validate:** Ensure int8 model produces correct outputs on-device before switching over.

### Fallback
If int8 + ESP-NN proves too difficult within Arduino constraints:
- Reduce model size (fewer filters, smaller dense layer) to speed up float32 inference
- Move inference to async FreeRTOS task (Track 3) to at least unblock the main loop

## Track 3: Async Inference and Frontend Tunability

### Async Inference
Currently, `runInference()` blocks the main loop on Core 1 for ~140ms. This degrades sensor poll rate and delays LED/MQTT responses.

Option: Create a FreeRTOS task on Core 1 that waits for a trigger signal, runs inference in the background, and posts the result back. The main loop continues processing sensor data while inference runs.

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
- Consider logging both results to a session metadata field for later analysis

## Open Questions

- Can `esp-tflite-micro` be used as a PlatformIO lib with Arduino framework, or does it strictly require ESP-IDF?
- Is the Keras 3 / TF 2.16 int8 quantization bug fixed in newer TF releases (2.17+)?
- For async inference, what's the best synchronization pattern? Semaphore + shared result struct, or FreeRTOS queue?
- Should the comparison mode log results to the cloud (session metadata) or just serial?

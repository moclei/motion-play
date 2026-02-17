# ML Direction Detection

## Intent

Add a machine-learning-based direction detection path that classifies transit direction from raw proximity sensor data, running inference on-device via TensorFlow Lite Micro on the ESP32-S3. This is an alternative to the current heuristic algorithm (DirectionDetector), not a replacement. The goal is a working end-to-end ML detection pipeline — data collection, model training, on-device inference — even if the model isn't production-grade yet.

## Goals

- Establish a repeatable data collection protocol for gathering labeled training data using Live Debug mode.
- Build a Python training pipeline that downloads session data, trains a small 1D CNN, and exports a quantized TFLite model.
- Integrate TFLite Micro into the firmware with a new MLDetector component that runs inference on the ESP32-S3. (ESP-NN PIE acceleration deferred — requires int8 quantization, currently blocked.)
- Make detection method selectable via config (heuristic vs ML) so both approaches coexist.

## Scope

What's in:
- Data collection protocol using existing Live Debug mode and frontend labeling
- Python training pipeline (download, preprocess, train, quantize, export)
- Firmware MLDetector component with TFLite Micro inference
- Config-selectable detection method (`"detection_mode": "heuristic" | "ml"`)
- Trigger-first architecture: simple threshold triggers ML inference on a buffered window

What's out:
- Replacing the heuristic algorithm entirely (it remains as fallback)
- Cloud-based or automated retraining pipeline
- On-device training or fine-tuning
- Production-grade model accuracy (this initiative establishes the foundation)
- Always-watching sliding window inference (defer to future iteration)
- Using ambient light sensor values (proximity only for now)

## Constraints

- Must use Arduino framework on PlatformIO (rules out ESP-DL, which requires ESP-IDF).
- TFLite Micro library must be compatible with the existing build setup (espressif32 platform, arduino-esp32 2.0.14).
- Model must be small enough to fit in flash. Current float32 inference takes ~140ms (acceptable for PoC; int8 would reduce to ~1-5ms).
- Core 0 remains dedicated to sensor collection; ML inference runs on Core 1.
- Training data must be collected fresh with this purpose in mind (prior sessions were for pipeline testing).

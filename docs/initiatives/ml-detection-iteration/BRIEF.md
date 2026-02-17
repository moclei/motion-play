# ML Detection Iteration

## Intent

Improve the ML-based direction detection from its initial proof-of-concept state to a more reliable, performant system. The foundation (training pipeline, on-device inference, config-selectable detection mode) was established in `ml-direction-detection`. This initiative focuses on making it genuinely useful: better accuracy through more data, dramatically faster inference via int8 quantization and ESP32-S3 hardware acceleration, and tunability from the frontend.

## Goals

- **Fix training/inference pipeline mismatches** that undermine current model accuracy (normalization, window alignment).
- Achieve ML detection accuracy comparable to the heuristic algorithm on standard transit events.
- Reduce inference time from ~140ms (float32) to <10ms via int8 quantization and ESP-NN hardware acceleration.
- Make ML parameters (confidence threshold, post-trigger delay) tunable from the frontend without reflashing.
- Collect a substantially larger labeled dataset (100+ sessions per class), supplemented by data augmentation.
- Establish a side-by-side comparison capability to objectively evaluate ML vs heuristic.
- Introduce model versioning from the start so every trained model is tracked and reproducible.

## Scope

What's in:
- Fix training/inference pipeline mismatches (normalization scheme, window alignment)
- Model versioning (version constant in C header, logged on boot and in detection events)
- Expanded data collection (more sessions per class, edge cases)
- Data augmentation (channel-swap direction flipping, time-shifting, noise injection, amplitude scaling)
- Int8 quantization and ESP-NN integration for hardware-accelerated inference
- Frontend-settable ML parameters (confidence threshold, post-trigger delay)
- Async inference (FreeRTOS task) to avoid blocking the main loop
- Side-by-side comparison mode (run both detectors, log both results)
- Model architecture experimentation if needed
- Validation strategy improvements (k-fold cross-validation, per-module evaluation)
- Clean up debug logging from Phase 4

What's out:
- Replacing the heuristic entirely (it remains the default and fallback)
- Cloud-based or automated retraining pipeline
- On-device training or fine-tuning
- Always-on sliding window inference (continuous inference without trigger)
- Ambient light sensor features (proximity only for now)

## Constraints

- Must remain on Arduino framework / PlatformIO (no ESP-IDF migration).
- ESP-NN integration must work within the Arduino build system, or via a compatible shim. If this proves impossible, focus on other optimizations (smaller model, reduced float ops).
- Int8 quantization must produce a fully int8 model (not hybrid). The Keras 3 / TF 2.16 MLIR bug that blocked this previously must be worked around (e.g., older TF version, alternative export path).
- Core 0 remains dedicated to sensor collection; ML inference stays on Core 1 (or a Core 1 task).

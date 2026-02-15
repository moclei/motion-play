# ML Training Pipeline

Training pipeline for the Motion Play ML-based direction detection model.

## Overview

This pipeline downloads labeled sensor data from the Motion Play cloud, preprocesses it into training tensors, trains a small 1D CNN, quantizes it to int8, and exports it as a C header file for embedding in the ESP32-S3 firmware.

## Setup

```bash
cd tools/ml-training
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Pipeline Steps

1. **Download data** — Fetch labeled `live_debug` sessions from the REST API
2. **Preprocess** — Extract fixed-size `(300, 6)` matrices (300ms window, 6 proximity channels), normalize, assign labels
3. **Train** — Train a 1D CNN model using TensorFlow/Keras
4. **Evaluate** — Accuracy, confusion matrix, per-scenario analysis
5. **Export** — Quantize to int8 TFLite, convert to C header for firmware

## Model Architecture

```
Input: (300, 6) — 300 timesteps at 1kHz, 6 sensor channels (proximity only)
  → Conv1D(16, kernel_size=5, ReLU)
  → MaxPool1D(2)
  → Conv1D(32, kernel_size=3, ReLU)
  → MaxPool1D(2)
  → Flatten
  → Dense(32, ReLU)
  → Dense(3, Softmax)   # A_TO_B, B_TO_A, NO_TRANSIT
```

## Output Classes

| Class | Label | Description |
|-------|-------|-------------|
| 0 | A_TO_B | Object passed from back to front of hoop |
| 1 | B_TO_A | Object passed from front to back of hoop |
| 2 | NO_TRANSIT | No valid transit (noise, partial, ambient) |

## Data Format

Each training sample is derived from a Live Debug session:
- **Input**: 300×6 matrix of uint16 proximity values, normalized to [0, 1]
- **Label**: Direction from session metadata + user labeling
- **Source**: DynamoDB via REST API (`GET /sessions/{id}/data`)

## Exporting for Firmware

After training and quantization:

```bash
# Convert .tflite to C header
xxd -i model.tflite > model_data.h
```

The header file goes into `firmware/src/components/detection/` and is included by `MLDetector`.

## See Also

- Initiative docs: `docs/initiatives/ml-direction-detection/`
- Current heuristic: `firmware/src/components/detection/DirectionDetector.cpp`
- Sensor data format: `SensorReading` struct in `firmware/src/components/sensor/SensorManager.h`

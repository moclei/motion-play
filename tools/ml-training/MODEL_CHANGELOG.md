# Model Changelog

Tracks each trained model version with its parameters, dataset, and metrics.

## Versions

### v1.0 (initial, pre-versioning)

- **Date:** ~2026-02-15
- **Dataset:** 46 sessions (15 a_to_b, 19 b_to_a, 12 no_transit)
- **Architecture:** 1D CNN — Conv1D(16,5) → MaxPool → Conv1D(32,3) → MaxPool → Dense(32) → Dropout(0.3) → Dense(3)
- **Window:** 300ms, centered on peak
- **Normalization:** Per-dataset max (~490.0)
- **Quantization:** Float32 (no quantization)
- **Model size:** 321,132 bytes
- **Validation accuracy:** ~90%
- **On-device detection rate:** ~57% of triggers produce detections
- **Inference time:** ~140ms (float32, PSRAM arena)
- **Notes:** First working model. Normalization used per-dataset max (mismatched with firmware's fixed 490.0 constant). Window centered on peak (mismatched with firmware's trigger-end-aligned extraction). These pipeline mismatches likely explain the gap between 90% validation accuracy and ~57% on-device detection rate.

---

*Template for new versions:*

```
### vYYYYMMDD-Nsess-alignment-normN

- **Date:** YYYY-MM-DD
- **Dataset:** N sessions (X a_to_b, Y b_to_a, Z no_transit)
- **Architecture:** (describe any changes)
- **Window:** 300ms, trigger-aligned (or centered)
- **Normalization:** Fixed constant = N (matching firmware)
- **Quantization:** Float32 / Int8
- **Model size:** N bytes
- **Validation accuracy:** N%
- **On-device detection rate:** N%
- **Inference time:** Nms
- **Notes:** What changed and why
```

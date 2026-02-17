# ML Detection Iteration — Tasks

## Phase 1: Quick wins and cleanup
- [ ] Clean up verbose `[Config]` debug logging added during Phase 4 troubleshooting
- [ ] Verify lowered confidence threshold (0.55) improves detection rate without excessive false positives
- [ ] Experiment with post-trigger delay (try 200ms instead of 150ms) to see if first-trigger accuracy improves

## Phase 2: Expanded data collection
- [ ] Collect 100+ A_TO_B sessions (Live Debug, 2T/1-pulse, labeled "a->b")
- [ ] Collect 100+ B_TO_A sessions (Live Debug, 2T/1-pulse, labeled "b->a")
- [ ] Collect 100+ NO_TRANSIT sessions (regular Debug, short sessions, labeled "no-transit")
- [ ] Include edge cases: center-of-hoop, angled passes, grazing transits, slow hand waves
- [ ] Retrain model with expanded dataset, compare metrics to Phase 3 baseline (90% val accuracy)

## Phase 3: Frontend-settable ML parameters
- [ ] Add `ml_confidence_threshold` and `ml_post_trigger_delay_ms` to Lambda `sanitizeConfig()` and MQTT payload
- [ ] Parse new config fields in firmware `configure_sensors` handler, apply to MLDetector
- [ ] Add slider/input controls to SettingsModal for ML parameters (visible when detection mode is ML)
- [ ] Test end-to-end: change threshold in frontend → device applies it → verify in serial logs

## Phase 4: Int8 quantization and ESP-NN
- [ ] Research: can `esp-tflite-micro` work with PlatformIO + Arduino? Document findings.
- [ ] Attempt int8 full-integer quantization (try TF 2.15 / Keras 2 or alternative export path)
- [ ] Validate int8 model correctness: run inference in Python and compare outputs to float32 model
- [ ] If int8 works: integrate ESP-NN optimized kernels and benchmark inference time
- [ ] If int8 blocked: reduce model complexity to speed up float32 inference as fallback

## Phase 5: Async inference
- [ ] Create FreeRTOS inference task on Core 1 (waits for trigger, runs inference, posts result)
- [ ] Decouple trigger detection from inference execution in main loop
- [ ] Verify sensor poll rate stays at ~1000Hz during inference
- [ ] Test detection latency and accuracy are not degraded

## Phase 6: Side-by-side comparison mode
- [ ] Add `"comparison"` option to `detection_mode`
- [ ] In comparison mode, feed readings to both DirectionDetector and MLDetector
- [ ] Primary detector drives LEDs/MQTT, secondary logs to serial
- [ ] Collect comparison data on real events, document accuracy differences

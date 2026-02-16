#include "MLDetector.h"
#include "model_data.h"

// ============================================================================
// Construction / Destruction
// ============================================================================

MLDetector::MLDetector() {}

MLDetector::~MLDetector()
{
    if (interpreter_)
    {
        delete interpreter_;
        interpreter_ = nullptr;
    }
    if (tensorArena_)
    {
        free(tensorArena_);
        tensorArena_ = nullptr;
    }
}

// ============================================================================
// Initialization
// ============================================================================

bool MLDetector::init()
{
    Serial.println("[MLDetector] Initializing TFLite Micro...");

    // Load model from flash
    model_ = tflite::GetModel(direction_model_tflite);
    if (model_ == nullptr)
    {
        Serial.println("[MLDetector] ERROR: Failed to load model");
        return false;
    }

    if (model_->version() != TFLITE_SCHEMA_VERSION)
    {
        Serial.printf("[MLDetector] ERROR: Model schema version %lu != expected %d\n",
                      model_->version(), TFLITE_SCHEMA_VERSION);
        return false;
    }
    Serial.printf("[MLDetector] Model loaded (%u bytes, schema v%lu)\n",
                  direction_model_tflite_len, model_->version());

    // Allocate tensor arena in PSRAM
    tensorArena_ = (uint8_t *)ps_malloc(ML_TENSOR_ARENA_SIZE);
    if (tensorArena_ == nullptr)
    {
        Serial.println("[MLDetector] ERROR: Failed to allocate tensor arena in PSRAM");
        // Fallback to regular malloc
        tensorArena_ = (uint8_t *)malloc(ML_TENSOR_ARENA_SIZE);
        if (tensorArena_ == nullptr)
        {
            Serial.println("[MLDetector] ERROR: Failed to allocate tensor arena");
            return false;
        }
        Serial.println("[MLDetector] WARNING: Tensor arena allocated in SRAM (PSRAM unavailable)");
    }
    else
    {
        Serial.printf("[MLDetector] Tensor arena: %u bytes in PSRAM\n", ML_TENSOR_ARENA_SIZE);
    }

    // Register required ops
    static tflite::MicroMutableOpResolver<6> resolver;
    resolver.AddConv2D();
    resolver.AddMaxPool2D();
    resolver.AddReshape();
    resolver.AddFullyConnected();
    resolver.AddSoftmax();
    resolver.AddQuantize();

    // Create interpreter
    static tflite::MicroInterpreter static_interpreter(
        model_, resolver, tensorArena_, ML_TENSOR_ARENA_SIZE);
    interpreter_ = &static_interpreter;

    // Allocate tensors
    TfLiteStatus status = interpreter_->AllocateTensors();
    if (status != kTfLiteOk)
    {
        Serial.println("[MLDetector] ERROR: AllocateTensors() failed");
        return false;
    }

    // Get input/output tensor pointers
    inputTensor_ = interpreter_->input(0);
    outputTensor_ = interpreter_->output(0);

    Serial.printf("[MLDetector] Input tensor: dims=(%d",
                  inputTensor_->dims->data[0]);
    for (int i = 1; i < inputTensor_->dims->size; i++)
    {
        Serial.printf(", %d", inputTensor_->dims->data[i]);
    }
    Serial.printf("), type=%d\n", inputTensor_->type);

    Serial.printf("[MLDetector] Output tensor: dims=(%d",
                  outputTensor_->dims->data[0]);
    for (int i = 1; i < outputTensor_->dims->size; i++)
    {
        Serial.printf(", %d", outputTensor_->dims->data[i]);
    }
    Serial.printf("), type=%d\n", outputTensor_->type);

    Serial.printf("[MLDetector] Arena used: %u / %u bytes\n",
                  interpreter_->arena_used_bytes(), ML_TENSOR_ARENA_SIZE);

    modelReady_ = true;
    Serial.println("[MLDetector] Initialization complete");
    return true;
}

// ============================================================================
// Ring buffer
// ============================================================================

void MLDetector::pushFrame(const MLSensorFrame &frame)
{
    ringBuffer_[ringHead_] = frame;
    ringHead_ = (ringHead_ + 1) % RING_BUFFER_SIZE;
    if (ringCount_ < RING_BUFFER_SIZE)
        ringCount_++;
}

// ============================================================================
// Smoothing
// ============================================================================

void MLDetector::pushSmooth(float a, float b)
{
    smoothBufferA_[smoothHead_] = a;
    smoothBufferB_[smoothHead_] = b;
    smoothHead_ = (smoothHead_ + 1) % SMOOTH_BUFFER_SIZE;
    if (smoothCount_ < SMOOTH_BUFFER_SIZE)
        smoothCount_++;
}

float MLDetector::getSmoothedA() const
{
    if (smoothCount_ == 0)
        return 0;
    size_t n = min((size_t)3, smoothCount_); // window of 3
    float sum = 0;
    for (size_t i = 0; i < n; i++)
    {
        size_t idx = (smoothHead_ - 1 - i + SMOOTH_BUFFER_SIZE) % SMOOTH_BUFFER_SIZE;
        sum += smoothBufferA_[idx];
    }
    return sum / n;
}

float MLDetector::getSmoothedB() const
{
    if (smoothCount_ == 0)
        return 0;
    size_t n = min((size_t)3, smoothCount_);
    float sum = 0;
    for (size_t i = 0; i < n; i++)
    {
        size_t idx = (smoothHead_ - 1 - i + SMOOTH_BUFFER_SIZE) % SMOOTH_BUFFER_SIZE;
        sum += smoothBufferB_[idx];
    }
    return sum / n;
}

// ============================================================================
// Sensor reading ingestion (same pattern as DirectionDetector)
// ============================================================================

void MLDetector::addReading(const SensorReading &reading)
{
    uint32_t timestampMs = reading.timestamp_us / 1000;

    // New timestamp? Flush the previous aggregated reading.
    if (hasCurrentReading_ && timestampMs != currentTimestamp_)
    {
        flushReading();
    }

    currentTimestamp_ = timestampMs;

    // Store per-position proximity
    if (reading.position < ML_NUM_POSITIONS)
    {
        currentProximity_[reading.position] = reading.proximity;
    }

    hasCurrentReading_ = true;
}

void MLDetector::flushReading()
{
    if (!hasCurrentReading_)
        return;

    // Build frame
    MLSensorFrame frame;
    frame.timestamp_ms = currentTimestamp_;
    for (uint8_t i = 0; i < ML_NUM_POSITIONS; i++)
    {
        frame.proximity[i] = currentProximity_[i];
    }
    pushFrame(frame);

    // Compute side aggregates for baseline/threshold (same convention as DirectionDetector)
    // Side A (side==2): positions 1, 3, 5 (S2 sensors)
    // Side B (side==1): positions 0, 2, 4 (S1 sensors)
    float sideA = (float)(currentProximity_[1] + currentProximity_[3] + currentProximity_[5]);
    float sideB = (float)(currentProximity_[0] + currentProximity_[2] + currentProximity_[4]);

    pushSmooth(sideA, sideB);
    float smoothedA = getSmoothedA();
    float smoothedB = getSmoothedB();

    // State machine
    switch (state_)
    {
    case State::ESTABLISHING_BASELINE:
        updateBaseline(smoothedA, smoothedB);
        break;

    case State::READY:
        if (checkTrigger(smoothedA, smoothedB))
        {
            state_ = State::TRIGGERED;
            triggerTimestamp_ = currentTimestamp_;
            waitingPostTrigger_ = true;
            Serial.printf("[MLDetector] Trigger at %lu ms (A=%.1f, B=%.1f)\n",
                          currentTimestamp_, smoothedA, smoothedB);
        }
        break;

    case State::TRIGGERED:
        // Wait for post-trigger delay so the full wave is captured
        if (waitingPostTrigger_)
        {
            if (currentTimestamp_ - triggerTimestamp_ >= ML_POST_TRIGGER_DELAY_MS)
            {
                waitingPostTrigger_ = false;
                // Run inference
                if (modelReady_ && ringCount_ >= 100) // need at least ~100 frames
                {
                    unsigned long t0 = micros();
                    bool detected = runInference();
                    unsigned long elapsed = micros() - t0;
                    Serial.printf("[MLDetector] Inference took %lu us\n", elapsed);

                    if (detected)
                    {
                        lastDetectionTime_ = currentTimestamp_;
                    }
                }
                else
                {
                    Serial.printf("[MLDetector] Skipping inference: modelReady=%d, frames=%u\n",
                                  modelReady_, ringCount_);
                }
                // Return to READY (cooldown enforced in checkTrigger)
                state_ = State::READY;
            }
        }
        break;
    }

    // Reset current reading accumulators
    for (uint8_t i = 0; i < ML_NUM_POSITIONS; i++)
    {
        currentProximity_[i] = 0;
    }
    hasCurrentReading_ = false;
}

// ============================================================================
// Baseline / threshold
// ============================================================================

void MLDetector::updateBaseline(float sideA, float sideB)
{
    baselineSumA_ += sideA;
    baselineSumB_ += sideB;
    if (sideA > baselineMaxA_)
        baselineMaxA_ = sideA;
    if (sideB > baselineMaxB_)
        baselineMaxB_ = sideB;
    baselineCount_++;

    if (baselineCount_ >= ML_BASELINE_READINGS)
    {
        calculateThresholds();
        state_ = State::READY;
        Serial.println("[MLDetector] Baseline established");
        Serial.printf("  Side A: mean=%.1f, max=%.1f, threshold=%.1f\n",
                      baselineSumA_ / baselineCount_, baselineMaxA_, thresholdA_);
        Serial.printf("  Side B: mean=%.1f, max=%.1f, threshold=%.1f\n",
                      baselineSumB_ / baselineCount_, baselineMaxB_, thresholdB_);
    }
}

void MLDetector::calculateThresholds()
{
    float baseA = baselineMaxA_;
    float baseB = baselineMaxB_;

    float riseA = max(baseA * (ML_PEAK_MULTIPLIER - 1.0f), (float)ML_MIN_RISE);
    float riseB = max(baseB * (ML_PEAK_MULTIPLIER - 1.0f), (float)ML_MIN_RISE);

    thresholdA_ = baseA + riseA;
    thresholdB_ = baseB + riseB;
}

bool MLDetector::checkTrigger(float sideA, float sideB)
{
    // Enforce cooldown
    if (lastDetectionTime_ > 0 &&
        (currentTimestamp_ - lastDetectionTime_) < ML_DETECTION_COOLDOWN_MS)
    {
        return false;
    }

    return (sideA > thresholdA_ || sideB > thresholdB_);
}

// ============================================================================
// Inference
// ============================================================================

void MLDetector::prepareInput()
{
    // Build a (ML_WINDOW_MS, ML_NUM_POSITIONS) matrix from the ring buffer.
    // Strategy: take the most recent ML_WINDOW_MS worth of data,
    // resample to 1ms grid with forward-fill (matching training preprocessing).

    float *input = inputTensor_->data.f;
    const size_t totalElements = ML_WINDOW_MS * ML_NUM_POSITIONS;
    memset(input, 0, totalElements * sizeof(float));

    if (ringCount_ == 0)
        return;

    // Find the start frame: we want up to ML_WINDOW_MS of data ending at the latest frame.
    // Walk backwards from the newest frame to find the time range.
    size_t newest = (ringHead_ - 1 + RING_BUFFER_SIZE) % RING_BUFFER_SIZE;
    uint32_t endTime = ringBuffer_[newest].timestamp_ms;
    uint32_t startTime = (endTime >= ML_WINDOW_MS) ? endTime - ML_WINDOW_MS + 1 : 0;

    // Forward-fill: iterate through ring buffer frames in order, place into the 1ms grid.
    // We need to iterate from oldest to newest.
    size_t oldest = (ringCount_ < RING_BUFFER_SIZE)
                        ? 0
                        : ringHead_;

    float lastVal[ML_NUM_POSITIONS] = {0};

    for (size_t i = 0; i < ringCount_; i++)
    {
        size_t idx = (oldest + i) % RING_BUFFER_SIZE;
        const MLSensorFrame &frame = ringBuffer_[idx];

        if (frame.timestamp_ms < startTime)
        {
            // Before our window, but update lastVal for forward-fill
            for (uint8_t p = 0; p < ML_NUM_POSITIONS; p++)
            {
                if (frame.proximity[p] > 0)
                    lastVal[p] = (float)frame.proximity[p];
            }
            continue;
        }
        if (frame.timestamp_ms > endTime)
            break;

        uint32_t t = frame.timestamp_ms - startTime;
        if (t < ML_WINDOW_MS)
        {
            for (uint8_t p = 0; p < ML_NUM_POSITIONS; p++)
            {
                float val = (float)frame.proximity[p];
                if (val > 0)
                    lastVal[p] = val;
                input[t * ML_NUM_POSITIONS + p] = lastVal[p] / ML_NORMALIZATION_MAX;
            }
        }
    }

    // Forward-fill gaps: for each ms without a frame, propagate from previous ms.
    for (uint32_t t = 1; t < ML_WINDOW_MS; t++)
    {
        for (uint8_t p = 0; p < ML_NUM_POSITIONS; p++)
        {
            size_t curIdx = t * ML_NUM_POSITIONS + p;
            if (input[curIdx] == 0.0f)
            {
                size_t prevIdx = (t - 1) * ML_NUM_POSITIONS + p;
                input[curIdx] = input[prevIdx];
            }
        }
    }
}

bool MLDetector::runInference()
{
    if (!modelReady_ || interpreter_ == nullptr)
        return false;

    // Prepare input tensor
    prepareInput();

    // Run inference
    TfLiteStatus status = interpreter_->Invoke();
    if (status != kTfLiteOk)
    {
        Serial.println("[MLDetector] ERROR: Inference failed");
        return false;
    }

    // Parse output: softmax [a_to_b, b_to_a, no_transit]
    float *output = outputTensor_->data.f;
    float confA2B = output[0];
    float confB2A = output[1];
    float confNoTransit = output[2];

    Serial.printf("[MLDetector] Output: A_TO_B=%.3f, B_TO_A=%.3f, NO_TRANSIT=%.3f\n",
                  confA2B, confB2A, confNoTransit);

    // Find the winning class
    float maxConf = confNoTransit;
    MLClass bestClass = MLClass::NO_TRANSIT;

    if (confA2B > maxConf)
    {
        maxConf = confA2B;
        bestClass = MLClass::A_TO_B;
    }
    if (confB2A > maxConf)
    {
        maxConf = confB2A;
        bestClass = MLClass::B_TO_A;
    }

    // Only report transit detections above confidence threshold
    if (bestClass == MLClass::NO_TRANSIT)
    {
        Serial.println("[MLDetector] Classification: NO_TRANSIT");
        return false;
    }

    if (maxConf < ML_CONFIDENCE_THRESHOLD)
    {
        Serial.printf("[MLDetector] Confidence %.3f below threshold %.3f\n",
                      maxConf, ML_CONFIDENCE_THRESHOLD);
        return false;
    }

    // Build DetectionResult
    lastResult_ = DetectionResult();
    lastResult_.direction = (bestClass == MLClass::A_TO_B) ? Direction::A_TO_B : Direction::B_TO_A;
    lastResult_.confidence = maxConf;
    lastResult_.baselineA = baselineMaxA_;
    lastResult_.baselineB = baselineMaxB_;
    lastResult_.thresholdA = thresholdA_;
    lastResult_.thresholdB = thresholdB_;

    detectionReady_ = true;

    Serial.printf("[MLDetector] DETECTION: %s (confidence=%.3f)\n",
                  DirectionDetector::directionToString(lastResult_.direction),
                  lastResult_.confidence);

    return true;
}

// ============================================================================
// Public API
// ============================================================================

bool MLDetector::hasDetection() const
{
    return detectionReady_;
}

DetectionResult MLDetector::getResult()
{
    detectionReady_ = false;
    return lastResult_;
}

void MLDetector::reset()
{
    // Clear ring buffer and detection state, keep baseline and model
    ringHead_ = 0;
    ringCount_ = 0;
    smoothHead_ = 0;
    smoothCount_ = 0;
    memset(smoothBufferA_, 0, sizeof(smoothBufferA_));
    memset(smoothBufferB_, 0, sizeof(smoothBufferB_));

    for (uint8_t i = 0; i < ML_NUM_POSITIONS; i++)
        currentProximity_[i] = 0;
    hasCurrentReading_ = false;
    currentTimestamp_ = 0;

    detectionReady_ = false;
    waitingPostTrigger_ = false;
    triggerTimestamp_ = 0;

    if (state_ != State::ESTABLISHING_BASELINE)
    {
        state_ = State::READY;
    }
}

void MLDetector::fullReset()
{
    reset();
    baselineSumA_ = 0;
    baselineSumB_ = 0;
    baselineMaxA_ = 0;
    baselineMaxB_ = 0;
    baselineCount_ = 0;
    thresholdA_ = 0;
    thresholdB_ = 0;
    lastDetectionTime_ = 0;
    state_ = State::ESTABLISHING_BASELINE;
}

bool MLDetector::isReady() const
{
    return modelReady_ && state_ != State::ESTABLISHING_BASELINE;
}

void MLDetector::debugPrint() const
{
    Serial.println("=== MLDetector State ===");
    Serial.printf("Model ready: %s\n", modelReady_ ? "YES" : "NO");
    Serial.printf("State: %s\n",
                  state_ == State::ESTABLISHING_BASELINE ? "ESTABLISHING_BASELINE"
                  : state_ == State::READY               ? "READY"
                                                         : "TRIGGERED");
    Serial.printf("Baseline count: %lu / %u\n", baselineCount_, ML_BASELINE_READINGS);
    Serial.printf("Threshold A: %.1f, B: %.1f\n", thresholdA_, thresholdB_);
    Serial.printf("Ring buffer: %u / %u frames\n", ringCount_, RING_BUFFER_SIZE);
    Serial.printf("Detection ready: %s\n", detectionReady_ ? "YES" : "NO");
    if (interpreter_)
    {
        Serial.printf("Arena used: %u / %u bytes\n",
                      interpreter_->arena_used_bytes(), ML_TENSOR_ARENA_SIZE);
    }
}

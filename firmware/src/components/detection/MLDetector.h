#ifndef ML_DETECTOR_H
#define ML_DETECTOR_H

#include <Arduino.h>
#include "DirectionDetector.h" // Reuse Direction, DetectionResult, SensorReading
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

/**
 * ML-based Direction Detection using TensorFlow Lite Micro.
 *
 * Replaces the heuristic wave-envelope approach with a small 1D CNN
 * that classifies transit direction from raw proximity sensor data.
 *
 * Architecture:
 *   - Maintains a sliding ring buffer of per-position proximity readings
 *   - Uses simplified threshold logic to detect "something happened"
 *   - On trigger: extracts 300ms window, runs TFLite inference
 *   - Output: A_TO_B, B_TO_A, or NO_TRANSIT with confidence
 *
 * The model expects input shape (1, 300, 6) — 300ms at 1ms resolution,
 * 6 sensor positions. Values normalized by dividing by NORMALIZATION_MAX.
 */

// Model input parameters (must match training pipeline)
static constexpr uint16_t ML_WINDOW_MS = 300;
static constexpr uint8_t ML_NUM_POSITIONS = 6;
static constexpr float ML_NORMALIZATION_MAX = 490.0f;
static constexpr float ML_CONFIDENCE_THRESHOLD = 0.55f;

// Tensor arena size — allocated in PSRAM for the dynamic-range quantized model
static constexpr size_t ML_TENSOR_ARENA_SIZE = 150 * 1024; // 150KB

// Baseline parameters
static constexpr uint16_t ML_BASELINE_READINGS = 50;
static constexpr float ML_PEAK_MULTIPLIER = 1.5f;
static constexpr uint16_t ML_MIN_RISE = 10;

// Cooldown between detections
static constexpr uint32_t ML_DETECTION_COOLDOWN_MS = 500;

// Post-trigger delay to capture the full wave
static constexpr uint32_t ML_POST_TRIGGER_DELAY_MS = 150;

/**
 * One timestep of sensor data: proximity values for all 6 positions.
 */
struct MLSensorFrame
{
    uint32_t timestamp_ms;
    uint16_t proximity[ML_NUM_POSITIONS]; // position 0-5
};

/**
 * ML model output classes (must match training CLASSES order)
 */
enum class MLClass : uint8_t
{
    A_TO_B = 0,
    B_TO_A = 1,
    NO_TRANSIT = 2
};

class MLDetector
{
public:
    MLDetector();
    ~MLDetector();

    /**
     * Initialize TFLite interpreter and load model.
     * Must be called before use. Returns true on success.
     */
    bool init();

    /**
     * Add a new sensor reading (same interface as DirectionDetector).
     */
    void addReading(const SensorReading &reading);

    /**
     * Flush current aggregated reading and process it.
     */
    void flushReading();

    /**
     * Check if a detection result is ready.
     */
    bool hasDetection() const;

    /**
     * Get the detection result (call after hasDetection returns true).
     */
    DetectionResult getResult();

    /**
     * Reset detection state (keep baseline and model).
     */
    void reset();

    /**
     * Full reset including baseline.
     */
    void fullReset();

    /**
     * Check if baseline is established and model is ready.
     */
    bool isReady() const;

    /**
     * Debug print current state.
     */
    void debugPrint() const;

private:
    // --- TFLite members ---
    const tflite::Model *model_ = nullptr;
    tflite::MicroMutableOpResolver<8> *resolver_ = nullptr;
    tflite::MicroInterpreter *interpreter_ = nullptr;
    uint8_t *tensorArena_ = nullptr;
    TfLiteTensor *inputTensor_ = nullptr;
    TfLiteTensor *outputTensor_ = nullptr;
    bool modelReady_ = false;

    /** Clean up all TFLite resources (safe to call multiple times). */
    void deinit();

    // --- Ring buffer for sensor frames ---
    static constexpr size_t RING_BUFFER_SIZE = 512; // ~1.3s at ~2.7ms per frame
    MLSensorFrame ringBuffer_[RING_BUFFER_SIZE];
    size_t ringHead_ = 0;
    size_t ringCount_ = 0;

    void pushFrame(const MLSensorFrame &frame);
    size_t getFrameCount() const { return ringCount_; }

    // --- Current reading aggregation ---
    uint32_t currentTimestamp_ = 0;
    uint16_t currentProximity_[ML_NUM_POSITIONS] = {0};
    bool hasCurrentReading_ = false;

    // --- Baseline / threshold tracking ---
    enum class State
    {
        ESTABLISHING_BASELINE,
        READY,
        TRIGGERED,
    };
    State state_ = State::ESTABLISHING_BASELINE;

    float baselineSumA_ = 0;
    float baselineSumB_ = 0;
    float baselineMaxA_ = 0;
    float baselineMaxB_ = 0;
    uint32_t baselineCount_ = 0;
    float thresholdA_ = 0;
    float thresholdB_ = 0;

    void updateBaseline(float sideA, float sideB);
    void calculateThresholds();

    // --- Trigger logic ---
    uint32_t triggerTimestamp_ = 0;
    bool waitingPostTrigger_ = false;

    bool checkTrigger(float sideA, float sideB);

    // --- Inference ---
    bool runInference();
    void prepareInput();

    // --- Detection result ---
    bool detectionReady_ = false;
    DetectionResult lastResult_;
    uint32_t lastDetectionTime_ = 0;

    // --- Smoothing ---
    static constexpr size_t SMOOTH_BUFFER_SIZE = 10;
    float smoothBufferA_[SMOOTH_BUFFER_SIZE] = {0};
    float smoothBufferB_[SMOOTH_BUFFER_SIZE] = {0};
    size_t smoothHead_ = 0;
    size_t smoothCount_ = 0;

    void pushSmooth(float a, float b);
    float getSmoothedA() const;
    float getSmoothedB() const;
};

#endif // ML_DETECTOR_H

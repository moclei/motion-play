#pragma once

#include <Arduino.h>
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/schema/schema_generated.h"

/**
 * Manages the TensorFlow Lite Micro lifecycle: model loading, tensor arena
 * allocation, op registration, and interpreter creation.
 *
 * Separated from MLDetector so the runtime can be reused for future models.
 * The caller provides model data and arena size; TFLiteRuntime owns all
 * TFLite objects and exposes accessors for inference.
 */
class TFLiteRuntime
{
public:
    TFLiteRuntime() = default;
    ~TFLiteRuntime();

    TFLiteRuntime(const TFLiteRuntime &) = delete;
    TFLiteRuntime &operator=(const TFLiteRuntime &) = delete;

    /**
     * Load model, allocate arena (PSRAM preferred, SRAM fallback),
     * register ops, create interpreter, and allocate tensors.
     * Safe to call multiple times — cleans up previous state first.
     */
    bool init(const unsigned char *modelData, size_t arenaSize);

    /** Release all TFLite resources. Safe to call multiple times. */
    void deinit();

    bool isReady() const { return modelReady_; }
    TfLiteTensor *inputTensor() { return inputTensor_; }
    TfLiteTensor *outputTensor() { return outputTensor_; }
    tflite::MicroInterpreter *interpreter() { return interpreter_; }
    size_t arenaUsedBytes() const;

private:
    const tflite::Model *model_ = nullptr;
    tflite::MicroMutableOpResolver<8> *resolver_ = nullptr;
    tflite::MicroInterpreter *interpreter_ = nullptr;
    uint8_t *tensorArena_ = nullptr;
    TfLiteTensor *inputTensor_ = nullptr;
    TfLiteTensor *outputTensor_ = nullptr;
    bool modelReady_ = false;
};

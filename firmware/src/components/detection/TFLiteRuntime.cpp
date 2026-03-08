#include "TFLiteRuntime.h"

TFLiteRuntime::~TFLiteRuntime()
{
    deinit();
}

void TFLiteRuntime::deinit()
{
    modelReady_ = false;
    inputTensor_ = nullptr;
    outputTensor_ = nullptr;

    if (interpreter_)
    {
        delete interpreter_;
        interpreter_ = nullptr;
    }
    if (resolver_)
    {
        delete resolver_;
        resolver_ = nullptr;
    }
    if (tensorArena_)
    {
        free(tensorArena_);
        tensorArena_ = nullptr;
    }
    model_ = nullptr;
}

bool TFLiteRuntime::init(const unsigned char *modelData, size_t arenaSize)
{
    deinit();

    Serial.println("[TFLiteRuntime] Initializing...");

    model_ = tflite::GetModel(modelData);
    if (model_ == nullptr)
    {
        Serial.println("[TFLiteRuntime] ERROR: Failed to load model");
        return false;
    }

    if (model_->version() != TFLITE_SCHEMA_VERSION)
    {
        Serial.printf("[TFLiteRuntime] ERROR: Model schema version %lu != expected %d\n",
                      model_->version(), TFLITE_SCHEMA_VERSION);
        return false;
    }
    Serial.printf("[TFLiteRuntime] Model loaded (schema v%lu)\n", model_->version());

    // Allocate tensor arena in PSRAM, fall back to SRAM
    tensorArena_ = (uint8_t *)ps_malloc(arenaSize);
    if (tensorArena_ == nullptr)
    {
        Serial.println("[TFLiteRuntime] WARNING: PSRAM unavailable, trying SRAM");
        tensorArena_ = (uint8_t *)malloc(arenaSize);
        if (tensorArena_ == nullptr)
        {
            Serial.println("[TFLiteRuntime] ERROR: Failed to allocate tensor arena");
            return false;
        }
        Serial.printf("[TFLiteRuntime] Tensor arena: %u bytes in SRAM\n", arenaSize);
    }
    else
    {
        Serial.printf("[TFLiteRuntime] Tensor arena: %u bytes in PSRAM\n", arenaSize);
    }

    resolver_ = new tflite::MicroMutableOpResolver<8>();
    resolver_->AddConv2D();
    resolver_->AddMaxPool2D();
    resolver_->AddReshape();
    resolver_->AddFullyConnected();
    resolver_->AddSoftmax();
    resolver_->AddExpandDims();

    interpreter_ = new tflite::MicroInterpreter(
        model_, *resolver_, tensorArena_, arenaSize);

    TfLiteStatus status = interpreter_->AllocateTensors();
    if (status != kTfLiteOk)
    {
        Serial.println("[TFLiteRuntime] ERROR: AllocateTensors() failed");
        deinit();
        return false;
    }

    inputTensor_ = interpreter_->input(0);
    outputTensor_ = interpreter_->output(0);

    Serial.printf("[TFLiteRuntime] Input tensor: dims=(%d",
                  inputTensor_->dims->data[0]);
    for (int i = 1; i < inputTensor_->dims->size; i++)
    {
        Serial.printf(", %d", inputTensor_->dims->data[i]);
    }
    Serial.printf("), type=%d\n", inputTensor_->type);

    Serial.printf("[TFLiteRuntime] Output tensor: dims=(%d",
                  outputTensor_->dims->data[0]);
    for (int i = 1; i < outputTensor_->dims->size; i++)
    {
        Serial.printf(", %d", outputTensor_->dims->data[i]);
    }
    Serial.printf("), type=%d\n", outputTensor_->type);

    Serial.printf("[TFLiteRuntime] Arena used: %u / %u bytes\n",
                  interpreter_->arena_used_bytes(), arenaSize);

    modelReady_ = true;
    Serial.println("[TFLiteRuntime] Initialization complete");
    return true;
}

size_t TFLiteRuntime::arenaUsedBytes() const
{
    if (interpreter_)
        return interpreter_->arena_used_bytes();
    return 0;
}

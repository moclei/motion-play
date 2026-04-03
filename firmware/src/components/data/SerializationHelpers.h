#pragma once

#include <ArduinoJson.h>
#include <vector>
#include "sensor_types.h"
#include "../sensor/SensorConfiguration.h"
#include "../session/SessionManager.h"
#include "../memory/PSRAMAllocator.h"

class SensorConfiguration;
struct SessionSummary;

namespace serialization {

void serializeCalibration(JsonDocument &doc);

void serializeConfig(JsonDocument &doc, const SensorConfiguration *config);

void serializeReadingsArray(JsonArray &arr,
                            std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings,
                            size_t startIdx, size_t count);

void serializeSummary(JsonObject &summaryObj, const SessionSummary &summary);

} // namespace serialization

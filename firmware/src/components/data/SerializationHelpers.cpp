#include "SerializationHelpers.h"
#include "../calibration/CalibrationData.h"

namespace serialization {

void serializeCalibration(JsonDocument &doc)
{
    if (deviceCalibration.isValid())
    {
        JsonObject calObj = doc.createNestedObject("calibration");
        calObj["valid"] = true;
        calObj["timestamp"] = deviceCalibration.timestamp;
        calObj["multi_pulse"] = deviceCalibration.multi_pulse;
        calObj["integration_time"] = deviceCalibration.integration_time;

        JsonArray thresholds = calObj.createNestedArray("thresholds");
        for (int i = 0; i < CALIBRATION_NUM_PCBS; i++)
        {
            JsonObject pcbCal = thresholds.createNestedObject();
            pcbCal["pcb"] = i + 1;
            pcbCal["baseline_max"] = deviceCalibration.pcbs[i].baseline_max;
            pcbCal["signal_min"] = deviceCalibration.pcbs[i].signal_min;
            pcbCal["signal_max"] = deviceCalibration.pcbs[i].signal_max;
            pcbCal["threshold"] = deviceCalibration.pcbs[i].threshold;
        }
    }
    else
    {
        JsonObject calObj = doc.createNestedObject("calibration");
        calObj["valid"] = false;
    }
}

void serializeConfig(JsonDocument &doc, const SensorConfiguration *config)
{
    if (config == nullptr)
        return;

    JsonObject configObj = doc.createNestedObject("vcnl4040_config");
    configObj["sample_rate_hz"] = config->sample_rate_hz;
    configObj["led_current"] = config->led_current;
    configObj["integration_time"] = config->integration_time;
    configObj["duty_cycle"] = config->duty_cycle;
    configObj["multi_pulse"] = config->multi_pulse;
    configObj["high_resolution"] = config->high_resolution;
    configObj["read_ambient"] = config->read_ambient;
    configObj["i2c_clock_khz"] = config->i2c_clock_khz;
    configObj["actual_sample_rate_hz"] = config->actual_sample_rate_hz;
}

void serializeReadingsArray(
    JsonArray &arr,
    std::vector<SensorReading, PSRAMAllocator<SensorReading>> &readings,
    size_t startIdx, size_t count)
{
    for (size_t i = 0; i < count; i++)
    {
        SensorReading &reading = readings[startIdx + i];

        JsonObject readingObj = arr.createNestedObject();
        readingObj["ts"] = reading.timestamp_us;
        readingObj["pos"] = reading.position;
        readingObj["pcb"] = reading.pcb_id;
        readingObj["side"] = reading.side;
        readingObj["prox"] = reading.proximity;
        readingObj["amb"] = reading.ambient;
    }
}

void serializeSummary(JsonObject &summaryObj, const SessionSummary &summary)
{
    summaryObj["total_cycles"] = summary.total_cycles;
    summaryObj["queue_drops"] = summary.queue_drops;
    summaryObj["buffer_drops"] = summary.buffer_drops;
    summaryObj["total_readings_transmitted"] = summary.total_readings_transmitted;
    summaryObj["total_batches_transmitted"] = summary.total_batches_transmitted;
    summaryObj["measured_cycle_rate_hz"] = summary.measured_cycle_rate_hz;
    summaryObj["duration_ms"] = summary.duration_ms;
    summaryObj["theoretical_max_readings"] = summary.theoretical_max_readings;
    summaryObj["num_active_sensors"] = summary.num_active_sensors;

    JsonArray collectedArr = summaryObj.createNestedArray("readings_collected");
    JsonArray errorsArr = summaryObj.createNestedArray("i2c_errors");
    for (int i = 0; i < NUM_SENSORS; i++)
    {
        collectedArr.add(summary.readings_collected[i]);
        errorsArr.add(summary.i2c_errors[i]);
    }
}

} // namespace serialization

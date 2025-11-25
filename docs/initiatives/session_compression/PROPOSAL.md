# Session Data Compression Proposal

**Date:** November 22, 2025  
**Status:** Proposed - Not Yet Implemented  
**Context:** After achieving ~222 Hz sample rate (15,134 readings in 17s), transmission time has become a bottleneck

## Problem Statement

### Current State
- **Sample Rate:** ~222 Hz per sensor (4 sensors active)
- **Readings per Session:** 15,134 readings in ~17 seconds
- **Data Format:** JSON via MQTT to AWS IoT Core
- **Estimated Size:** ~1.36 MB per session (90 bytes × 15,134 readings)
- **Issue:** Long transmission times affecting user experience

### Current JSON Format
```json
{
  "timestamp": 1000,
  "position": 0,
  "sensor_id": "P1S1",
  "proximity": 551,
  "ambient": 23,
  "white": 15
}
```

## Compression Options

### Option 1: Binary Encoding + Delta Compression ⭐ RECOMMENDED

**Size Reduction:** 90-95%  
**Complexity:** Medium  
**Performance Impact:** Low

#### Implementation
Pack data as binary struct:
```cpp
struct CompactReading {
    uint16_t timestamp_delta;  // 2 bytes (delta from previous)
    uint8_t sensor_id;         // 1 byte (0-5)
    uint16_t proximity;        // 2 bytes
    uint16_t ambient;          // 2 bytes (optional)
} __attribute__((packed));
// Total: 7 bytes per reading (vs ~90 bytes JSON)
```

#### Expected Results
- **Binary only:** 7 bytes × 15,134 = **106 KB** (~92% reduction)
- **Binary + gzip:** **30-50 KB** (~96% reduction)
- **Benefit:** Single MQTT message vs multiple batches

#### Pros
- Massive size reduction (13x smaller)
- ESP32 can handle easily
- Fits in single MQTT message (128 KB limit)
- Timestamps compress well due to sequential patterns

#### Cons
- Need decoder on backend/frontend
- More complex implementation
- Schema version management required

#### Implementation Steps
1. Create binary packing functions in DataTransmitter
2. Base64 encode for MQTT transmission
3. Update Lambda to decode binary format
4. Convert to DynamoDB format in Lambda
5. Update frontend to handle binary/decoded format

---

### Option 2: MessagePack

**Size Reduction:** 60-70%  
**Complexity:** Low (libraries available)  
**Performance Impact:** Low

#### Implementation
MessagePack is binary JSON - maintains structure, much smaller size:
```cpp
// ESP32: https://github.com/hideakitai/MsgPack
MsgPack::Packer packer;
packer.serialize(readings);
```

#### Expected Results
- **Size:** ~400-500 KB (vs 1.36 MB JSON)
- **Reduction:** 60-70%

#### Pros
- Drop-in replacement for JSON
- Libraries exist for ESP32, Node.js (Lambda), JavaScript (frontend)
- Self-describing format (easier debugging)
- Less prone to version mismatch issues

#### Cons
- Not as small as custom binary format
- Still requires multiple MQTT batches
- Additional library dependency

---

### Option 3: gzip Compression on JSON

**Size Reduction:** 70-80%  
**Complexity:** Low  
**Performance Impact:** Medium-High (CPU/memory intensive on ESP32)

#### Implementation
```cpp
#include <esp_gzip.h>
size_t compressed_size = compressBuffer(json_string, compressed_buffer);
```

#### Expected Results
- **Size:** ~270-400 KB (vs 1.36 MB JSON)
- **Reduction:** 70-80%

#### Pros
- Simple to implement
- AWS Lambda can auto-decompress
- No format changes needed
- Standard compression

#### Cons
- CPU/memory intensive on ESP32 (PSRAM usage)
- Still ~270-400 KB (multiple MQTT batches)
- Compression time adds to transmission delay
- May impact sensor collection if memory constrained

---

## Recommended Approach

### Phase 1: Binary + Delta Encoding (Immediate Win)
**Target:** 90-95% size reduction

1. Implement binary packing in `DataTransmitter`
2. Use delta encoding for timestamps
3. Base64 encode for MQTT
4. Update Lambda decoder
5. Test with real sessions

**Expected Result:** 15,134 readings = **~106 KB** (single MQTT message)

### Phase 2: Optional Lightweight Compression
**Target:** Additional 30-50% on top of binary

If 106 KB is still problematic:
- Run-length encoding for unchanged values
- Further optimize delta encoding
- Skip ambient/white if always 0
- Consider zlib on binary data

**Expected Result:** ~50-70 KB

## Questions to Answer

### Measurement & Constraints
1. **Current transmission time?** - Add timing logs to quantify problem
2. **AWS IoT Core MQTT message size limit?** - Typically 128 KB, verify actual
3. **Real-time requirement?** - Can sessions buffer or must stream?
4. **ESP32 memory constraints?** - PSRAM usage during compression

### Design Decisions
1. **Compression on device or cloud?** - Where is bottleneck?
2. **Binary schema versioning?** - How to handle format changes?
3. **Backward compatibility?** - Support old sessions?
4. **Error handling?** - What if decompression fails?

### Performance Testing Needed
1. Measure current upload duration
2. Profile ESP32 memory during large sessions
3. Test Lambda cold-start with decompression
4. Benchmark frontend decode performance

## Technical Considerations

### ESP32 Constraints
- **PSRAM:** 8 MB available for buffering
- **Heap:** Limited for compression algorithms
- **CPU:** Single core available (Core 1) during upload
- **Network:** WiFi may be bottleneck, not data size

### AWS Lambda
- **Timeout:** 30 seconds max
- **Memory:** Configure based on decompression needs
- **Cold Start:** Binary libs may slow cold starts

### Frontend
- **Binary Decoding:** Use JavaScript TypedArrays
- **Performance:** 15K+ readings to render
- **Caching:** Decoded sessions for visualization

## Related Files

- `firmware/src/components/data/DataTransmitter.cpp` - Current JSON transmission
- `lambda/processData/index.js` - Data ingestion Lambda
- `frontend/motion-play-ui/src/services/api.ts` - Frontend API client

## Success Metrics

### Phase 1 Goals
- [ ] Transmission time reduced by 80%+
- [ ] Single MQTT message for typical sessions
- [ ] No impact on sensor collection rate
- [ ] Lambda processing time < 5 seconds

### Phase 2 Goals (if needed)
- [ ] Further 50% size reduction from Phase 1
- [ ] Support sessions up to 60 seconds (30K+ readings)
- [ ] Memory usage stays under 50% PSRAM

## Next Steps

1. **Add timing instrumentation** to quantify current transmission duration
2. **Verify AWS MQTT limits** and current batch sizes
3. **Choose approach** based on measurements and constraints
4. **Prototype binary encoding** in isolated test
5. **Deploy and validate** with real hardware

---

**Note:** This proposal was created after successfully increasing sample rate from 25 Hz to 222 Hz by removing delays in the Adafruit VCNL4040 library. The bottleneck has shifted from data collection to data transmission.

**Related Initiatives:**
- [Object Detection](../object-detection/) - Requires high sample rates
- [Data Collection](../data-collection/) - Full data pipeline documentation


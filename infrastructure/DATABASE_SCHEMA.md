# Motion Play Database Schema

This document describes the DynamoDB table schemas and important implementation details.

---

## Tables Overview

1. **MotionPlaySessions** - Session metadata (both proximity and interrupt sessions)
2. **MotionPlaySensorData** - Individual sensor readings (proximity mode)
3. **MotionPlayInterruptEvents** - Interrupt detection events (interrupt mode)
4. **MotionPlayDevices** - Device status and configuration

---

## 1. MotionPlaySessions Table

**Purpose**: Store metadata about each data collection session.

### Schema

```
Partition Key: session_id (String)
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| session_id | String | Unique session identifier (e.g., "device-001_123456") |
| device_id | String | Device that recorded the session |
| **session_type** | **String** | **"proximity" or "interrupt" (added Dec 2025)** |
| start_timestamp | String | Session start time (ISO 8601 or epoch ms) |
| end_timestamp | String | Session end time (ISO 8601) |
| duration_ms | Number | Session duration in milliseconds |
| mode | String | Recording mode (debug, play, idle, interrupt_debug, **live_debug**) |
| sample_count | Number | Total number of sensor readings (proximity sessions) |
| **event_count** | **Number** | **Total number of interrupt events (interrupt sessions)** |
| sample_rate | Number | Sampling rate in Hz |
| labels | List[String] | User-added labels for categorization |
| notes | String | User notes about the session |
| created_at | Number | Timestamp when session was created (epoch ms) |
| active_sensors | List[Object] | Which sensors were active during recording |
| vcnl4040_config | Object | Sensor hardware configuration (proximity mode) |
| **interrupt_config** | **Object** | **Interrupt detection configuration (interrupt mode)** |
| capture_reason | String | (Optional) Live Debug: `"detection"` or `"missed_event"` (added Feb 2026) |
| detection_direction | String | (Optional) Live Debug: `"a_to_b"` or `"b_to_a"` (added Feb 2026) |
| detection_confidence | Number | (Optional) Live Debug: algorithm confidence score 0.0–1.0 (added Feb 2026) |

### Session Type Field

The `session_type` field determines which data table to query:
- `"proximity"` (default) → Query `MotionPlaySensorData` for continuous readings
- `"interrupt"` → Query `MotionPlayInterruptEvents` for discrete events

### Interrupt Configuration Object

For interrupt sessions, the `interrupt_config` field stores detection settings:

```json
{
  "high_threshold": 500,
  "low_threshold": 100,
  "persistence": 1,
  "smart_persistence": true,
  "mode": "normal",
  "led_current": "200mA",
  "integration_time": "1T"
}
```

### Live Debug Sessions

Sessions with `mode: "live_debug"` are short event captures from the Live Debug feature (added Feb 2026). They use `session_type: "proximity"` and store readings in `MotionPlaySensorData` like normal proximity sessions, but are much smaller (~0.5s detection windows or ~3s missed-event windows).

Optional fields present on live_debug sessions:
- `capture_reason`: `"detection"` (algorithm triggered) or `"missed_event"` (user pressed button)
- `detection_direction`: `"a_to_b"` or `"b_to_a"` (only for detection captures)
- `detection_confidence`: Float 0.0–1.0 (only for detection captures)

Labels can be added via `updateSession` to categorize captures: `["correct"]`, `["false_positive"]`, `["wrong_direction"]`, `["missed"]`.

### Global Secondary Index (GSI)

**DeviceTimeIndex**:
- Partition Key: `device_id` (String)
- Sort Key: `start_timestamp` (String)
- Purpose: Query sessions by device, sorted by time

---

## 2. MotionPlaySensorData Table

**Purpose**: Store individual sensor readings from each session.

### Schema

```
Partition Key: session_id (String)
Sort Key: timestamp_offset (Number) - ⚠️ COMPOSITE KEY
```

### ⚠️ CRITICAL: Composite Timestamp Key

**Why It Exists**: Multiple sensors reading simultaneously would create duplicate keys.

**Problem Without Composite Key**:
```
P1S1 at 100ms: (session_id="abc", timestamp_offset=100) ✓
P1S2 at 100ms: (session_id="abc", timestamp_offset=100) ❌ DUPLICATE KEY!
```

**Solution**: Encode both timestamp AND sensor position into a single number:

```javascript
timestamp_offset = (timestamp_ms * 10) + position
```

**Example**:
| Sensor | Time | Position | Calculation | timestamp_offset |
|--------|------|----------|-------------|------------------|
| P1S1   | 100ms | 0 | 100 × 10 + 0 | 1000 |
| P1S2   | 100ms | 1 | 100 × 10 + 1 | 1001 |
| P2S1   | 100ms | 2 | 100 × 10 + 2 | 1002 |
| P2S2   | 100ms | 3 | 100 × 10 + 3 | 1003 |

**Decoding**:
```javascript
actual_timestamp = Math.floor(timestamp_offset / 10)
sensor_position = timestamp_offset % 10
```

**Why This Works**:
1. ✅ Each reading gets a unique key (no duplicates)
2. ✅ Sort order is preserved (earlier timestamps appear first)
3. ✅ Position values 0-5 fit cleanly in the ones digit
4. ✅ All sensors can share synchronized timestamps

**Where Implemented**:
- Encoding: `lambda/processData/index.js`
- Decoding: `lambda/getSessionData/index.js`
- Frontend: Receives decoded `timestamp_ms` values

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| session_id | String | FK to MotionPlaySessions |
| timestamp_offset | Number | **COMPOSITE KEY** (see above) |
| timestamp_ms | Number | Actual timestamp relative to session start (ms) |
| position | Number | Sensor array index (0-5) |
| pcb_id | Number | PCB board number (1-3) |
| side | Number | Sensor side (1=S1, 2=S2) |
| proximity | Number | Proximity sensor reading |
| ambient | Number | Ambient light sensor reading |

### Sensor Position Mapping

| Position | PCB | Side | Label |
|----------|-----|------|-------|
| 0 | 1 | 1 | P1S1 |
| 1 | 1 | 2 | P1S2 |
| 2 | 2 | 1 | P2S1 |
| 3 | 2 | 2 | P2S2 |
| 4 | 3 | 1 | P3S1 |
| 5 | 3 | 2 | P3S2 |

### Query Patterns

**Get all readings for a session**:
```javascript
query({
  TableName: 'MotionPlaySensorData',
  KeyConditionExpression: 'session_id = :sid',
  ExpressionAttributeValues: { ':sid': 'device-001_123456' }
})
// Returns readings sorted by timestamp_offset (chronological order)
```

**⚠️ IMPORTANT**: 
- To query by actual timestamp, use the `timestamp_ms` attribute in FilterExpression
- DO NOT use `timestamp_offset` for timestamp-based queries (it includes position)

---

## 3. MotionPlayInterruptEvents Table

**Purpose**: Store interrupt detection events for interrupt-mode sessions.

### Schema

```
Partition Key: session_id (String)
Sort Key: event_index (Number) - Sequential index within session
```

### Table Settings

```
Table Name: MotionPlayInterruptEvents
Billing Mode: PAY_PER_REQUEST (On-Demand)
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| session_id | String | Session this event belongs to |
| event_index | Number | Sequential event index (sort key) |
| timestamp_us | Number | Timestamp in microseconds since boot |
| board_id | Number | Which sensor board (1-3) |
| sensor_position | Number | Global sensor position (0-5) |
| event_type | String | "close" or "away" |
| raw_flags | Number | Raw INT_FLAG register value |

### Event Types

- `"close"`: Object detected (proximity value exceeded high threshold)
- `"away"`: Object removed (proximity value dropped below low threshold)

### Example Event

```json
{
  "session_id": "device-001_1702500000",
  "event_index": 0,
  "timestamp_us": 150000,
  "board_id": 1,
  "sensor_position": 0,
  "event_type": "close",
  "raw_flags": 2
}
```

### Usage Notes

1. **Event index** is a simple incrementing counter for uniqueness
2. **Timestamp is in microseconds** (not milliseconds like proximity data)
3. **Typical session size**: <1000 events (much smaller than proximity sessions)
4. **Use sort key** to retrieve events in chronological order

### Query Patterns

**Get all events for a session**:
```javascript
query({
  TableName: 'MotionPlayInterruptEvents',
  KeyConditionExpression: 'session_id = :sid',
  ExpressionAttributeValues: { ':sid': 'device-001_123456' }
})
// Returns events sorted by event_index (chronological order)
```

---

## 4. MotionPlayDevices Table

**Purpose**: Track device status and configuration.

### Schema

```
Partition Key: device_id (String)
```

### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| device_id | String | Unique device identifier |
| status | String | Current status (online, offline, collecting) |
| last_seen | Number | Last communication timestamp (epoch ms) |
| current_mode | String | Current operating mode |
| wifi_rssi | Number | WiFi signal strength |
| free_heap | Number | Free memory (bytes) |
| uptime_ms | Number | Device uptime (milliseconds) |
| **sensor_config** | **Object** | **Persistent sensor configuration (added Nov 2025)** |
| **config_updated_at** | **Number** | **Timestamp when config was last updated (epoch ms)** |

### Sensor Configuration Object

The `sensor_config` field stores the active sensor configuration for the device. This is the **single source of truth** for device settings and persists across firmware reboots.

```json
{
  "sample_rate_hz": 1000,
  "led_current": "200mA",
  "integration_time": "1T",
  "high_resolution": true,
  "read_ambient": true,
  "i2c_clock_khz": 400
}
```

**Configuration Flow**:
1. Frontend → `PUT /device/{id}/config` → Updates DynamoDB
2. Lambda sends MQTT command to firmware
3. Firmware applies config immediately
4. On firmware reboot → `GET /device/{id}/config` → Restores from cloud

**Default Values** (if config doesn't exist):
- `sample_rate_hz`: 1000
- `led_current`: "200mA"
- `integration_time`: "1T"
- `high_resolution`: true
- `read_ambient`: true
- `i2c_clock_khz`: 400

---

## Data Flow

```
Device → MQTT → IoT Rule → processData Lambda → DynamoDB
                                ↓
                         Composite Key Encoding
                                ↓
                    MotionPlaySensorData Table
                                ↓
                    getSessionData Lambda
                                ↓
                         Composite Key Decoding
                                ↓
                            Frontend
```

---

## Migration Notes

If you ever need to change the composite key scheme:

1. **DO NOT** modify the existing table
2. Create a new table with the new schema
3. Write a migration script to transform data
4. Update Lambda functions to write to both tables during transition
5. Switch frontend to read from new table
6. Archive old table

**Estimated effort**: 2-3 days for careful migration

---

## Cost Considerations

**Storage**:
- Each sensor reading: ~100 bytes
- 1000 readings/second × 6 sensors × 10 seconds = 60,000 items
- 60,000 × 100 bytes = 6 MB per session
- DynamoDB: First 25GB free, then $0.25/GB/month

**Read/Write Capacity**:
- On-demand mode (current): Pay per request
- Typical cost: $0.01-$0.05 per session

---

## Troubleshooting

### "Provided list of item keys contains duplicates"
- **Cause**: Multiple readings with same `(session_id, timestamp_offset)`
- **Fix**: Ensure composite key encoding is working
- **Check**: `timestamp_offset = (timestamp_ms * 10) + position`

### "The provided key element does not match the schema"
- **Cause**: Trying to use String for `timestamp_offset` (must be Number)
- **Fix**: Ensure composite key is calculated as a Number

### "No readings returned for session"
- **Cause**: Readings exist but decoding is broken
- **Fix**: Check `getSessionData` Lambda decoding logic

---

**Last Updated**: February 12, 2026  
**Author**: Marc  
**Version**: 1.4 (Added live_debug mode, capture_reason, detection_direction, detection_confidence fields)


# Infrastructure Context

AWS-based cloud platform for device connectivity, data collection, storage, and visualization. Provides remote control of the ESP32 device and a data pipeline for ML training.

> See `infrastructure/aws-setup-guide.md` for setup instructions. See `infrastructure/lambda-deployment-guide.md` for Lambda deployment. See `infrastructure/DATABASE_SCHEMA.md` for full DynamoDB schema details.

## AWS Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        AWS Cloud                                 │
│                                                                  │
│  ┌──────────────┐      ┌──────────────┐      ┌──────────────┐ │
│  │  IoT Core    │      │   Lambda     │      │  DynamoDB    │ │
│  │   (MQTT)     │─────▶│  Functions   │─────▶│   Tables     │ │
│  └──────┬───────┘      └──────────────┘      └──────────────┘ │
│         │                      ▲                                │
│         │                      │                                │
│         ▼                      │                                │
│  ┌──────────────┐      ┌──────┴───────┐                       │
│  │ IoT Rules    │      │ API Gateway  │                       │
│  │   Engine     │      │   (REST)     │                       │
│  └──────────────┘      └──────┬───────┘                       │
│                                │                                │
└────────────────────────────────┼────────────────────────────────┘
                                 │ HTTPS
                                 ▼
                    ┌────────────────────────┐
                    │   React Web Frontend   │
                    └────────────────────────┘
```

## AWS IoT Core

- **Authentication**: X.509 certificates (per device), stored in `firmware/data/certs/`
- **Protocol**: MQTT over TLS 1.2
- **Topics**:
  - `motionplay/{device_id}/commands` — Commands from cloud to device
  - `motionplay/{device_id}/data` — Sensor data from device to cloud
  - `motionplay/{device_id}/status` — Device status updates

## Lambda Functions

| Function | Trigger | Purpose |
|----------|---------|---------|
| **processData** | IoT Rule (data topic) | Process and store sensor data in DynamoDB |
| **getSessionData** | API Gateway GET | Retrieve session metadata and readings |
| **getSessions** | API Gateway GET | List all sessions with filtering |
| **sendCommand** | API Gateway POST | Send commands to device via IoT Core |
| **updateSession** | API Gateway PATCH | Update session labels/notes |
| **deleteSession** | API Gateway DELETE | Delete session and associated data |
| **processStatus** | IoT Rule (status topic) | Process device status updates |

Lambda source code lives in `lambda/` (separate from `infrastructure/`).

## DynamoDB Tables

**MotionPlaySessions** — Session metadata
- Partition Key: `session_id` (String)
- GSI: `DeviceTimeIndex` (device_id, start_timestamp)

**MotionPlaySensorData** — Sensor readings
- Partition Key: `session_id` (String)
- Sort Key: `timestamp_offset` (Number) — **Composite timestamp**

**MotionPlayDevices** — Device registry
- Partition Key: `device_id` (String)

### Composite Timestamp Key (Critical)

Multiple sensors reading simultaneously need unique sort keys:
```javascript
timestamp_offset = (timestamp_ms * 10) + sensor_position

// Example: P1S1 at 100ms → (100 * 10) + 0 = 1000
// Example: P1S2 at 100ms → (100 * 10) + 1 = 1001

// Decoding:
actual_timestamp = Math.floor(timestamp_offset / 10)
sensor_position = timestamp_offset % 10
```

## API Gateway

REST API with CORS enabled for local development.

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/sessions` | List sessions |
| GET | `/sessions/{session_id}` | Get session details |
| GET | `/sessions/{session_id}/data` | Get sensor readings |
| POST | `/command` | Send device command |
| PATCH | `/sessions/{session_id}` | Update session |
| DELETE | `/sessions/{session_id}` | Delete session |

## MQTT Message Formats

**Command Message** (Cloud → Device):
```json
{
  "command": "START_COLLECTION|STOP_COLLECTION|SET_MODE|CONFIGURE_SENSORS",
  "session_id": "device-001_123456",
  "parameters": {
    "mode": "debug|play|idle",
    "sample_rate": 1000,
    "vcnl4040_config": {
      "led_current": 200,
      "integration_time": 80
    }
  }
}
```

**Data Message** (Device → Cloud):
```json
{
  "device_id": "motionplay-device-001",
  "session_id": "device-001_123456",
  "start_timestamp": 1234567890,
  "sample_rate": 1000,
  "mode": "debug",
  "readings": [
    {
      "timestamp": 0,
      "position": 0,
      "sensor_id": "P1S1",
      "proximity": 551,
      "ambient": 23,
      "white": 15
    }
  ],
  "active_sensors": [
    {"position": 0, "sensor_id": "P1S1", "enabled": true}
  ],
  "vcnl4040_config": {
    "led_current": 200,
    "integration_time": 80
  }
}
```

**Status Message** (Device → Cloud):
```json
{
  "device_id": "motionplay-device-001",
  "status": "idle|collecting|uploading|error",
  "wifi_rssi": -45,
  "free_heap": 123456,
  "uptime_ms": 3600000
}
```

## Data Flow

**Starting a Collection Session:**
1. User clicks "Start Collection" in web interface
2. Frontend → API Gateway → `sendCommand` Lambda → IoT Core MQTT
3. ESP32 receives command, begins 1000 Hz data collection
4. Data buffered in PSRAM (30,000+ samples)

**Stopping and Uploading:**
1. User clicks "Stop Collection" → same flow as above
2. ESP32 stops collection, publishes batched data via MQTT
3. IoT Rule triggers `processData` Lambda → DynamoDB
4. Frontend polls for new session

**Viewing Data:**
1. Frontend → API Gateway → `getSessionData` Lambda → DynamoDB query
2. Data returned as JSON, rendered with Recharts

## Deployment

- **Device certificates**: Generated from AWS IoT Core, stored in `firmware/data/certs/`
- **WiFi credentials**: `firmware/data/config.json`
- **Cloud config is source of truth**: Device fetches sensor config from cloud on boot; frontend is authoritative for config changes
- **Frontend**: Local dev via `npm run dev`, API endpoint in `.env`

---

*Last Updated: March 4, 2026*

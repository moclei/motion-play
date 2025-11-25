# Motion Play Lambda Functions

AWS Lambda functions for the Motion Play data collection system.

## Functions Overview

1. **processData** - Process sensor data from ESP32 and store in DynamoDB
2. **processStatus** - Update device status information
3. **sendCommand** - Send commands to devices via IoT Core
4. **getSessions** - Retrieve list of sessions
5. **getSessionData** - Get detailed session data
6. **updateSession** - Update session metadata (labels, notes)
7. **deleteSession** - Delete sessions and associated data

## Deployment

Each function should be deployed as a separate Lambda function with appropriate IAM permissions.

### Required IAM Permissions

- DynamoDB: PutItem, GetItem, Query, UpdateItem, DeleteItem
- IoT Core: Publish (for sendCommand function)
- CloudWatch Logs: CreateLogGroup, CreateLogStream, PutLogEvents

### Environment Variables

Each function may require:
- `SESSIONS_TABLE` - MotionPlaySessions table name
- `SENSOR_DATA_TABLE` - MotionPlaySensorData table name
- `DEVICES_TABLE` - MotionPlayDevices table name
- `REGION` - AWS region (e.g., us-west-2)

## Data Storage Architecture

### Composite Timestamp Key ⚠️ CRITICAL

**Problem Solved**: Multiple sensors reading simultaneously create duplicate DynamoDB keys.

**Solution**: Composite numeric key encoding both timestamp and sensor position.

#### Key Schema (MotionPlaySensorData table)
- **Partition Key**: `session_id` (String)
- **Sort Key**: `timestamp_offset` (Number) - **COMPOSITE KEY**

#### Composite Key Formula
```javascript
timestamp_offset = (timestamp_ms * 10) + position
```

**Example**:
- Sensor P1S1 (position=0) at 100ms: `1000` (100 × 10 + 0)
- Sensor P1S2 (position=1) at 100ms: `1001` (100 × 10 + 1)
- Sensor P2S1 (position=2) at 100ms: `1002` (100 × 10 + 2)

#### Decoding
```javascript
timestamp_ms = Math.floor(timestamp_offset / 10)
position = timestamp_offset % 10
```

**Why This Works**:
- All sensors can share the same timestamp (synchronized readings)
- Each reading still has a unique DynamoDB key
- Sort order is preserved (lower timestamps appear first)
- Position values 0-5 fit in the ones digit

**Where Implemented**:
- Encoding: `lambda/processData/index.js` (lines ~107-117)
- Decoding: `lambda/getSessionData/index.js` (lines ~63-78)

**⚠️ IMPORTANT**: If you ever need to query by timestamp, use the `timestamp_ms` attribute, NOT `timestamp_offset`!

## Development

Each function directory contains:
- `index.ts` or `index.js` - Main handler
- `package.json` - Dependencies
- `README.md` - Function-specific documentation

## Deployment Options

1. **Manual** - Zip and upload via AWS Console
2. **AWS CLI** - Use `aws lambda update-function-code`
3. **AWS CDK** - Infrastructure as code (recommended for Phase 2)
4. **Serverless Framework** - Alternative deployment tool


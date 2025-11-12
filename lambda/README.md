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


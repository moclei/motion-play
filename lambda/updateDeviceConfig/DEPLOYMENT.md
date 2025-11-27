# updateDeviceConfig Lambda - Deployment Guide

## Function Details

**Function Name**: `motionplay-updateDeviceConfig`  
**Runtime**: Node.js 18.x or later  
**Handler**: `index.handler`  
**Timeout**: 15 seconds  
**Memory**: 256 MB  

## Environment Variables

```
DEVICES_TABLE=MotionPlayDevices
AWS_REGION=us-west-2
```

## IAM Permissions Required

The Lambda execution role needs the following permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:UpdateItem"
      ],
      "Resource": "arn:aws:dynamodb:us-west-2:*:table/MotionPlayDevices"
    },
    {
      "Effect": "Allow",
      "Action": [
        "iot:Publish"
      ],
      "Resource": "arn:aws:iot:us-west-2:*:topic/motionplay/*/commands"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

## Deployment Steps

### 1. Install Dependencies

```bash
cd lambda/updateDeviceConfig
npm install
```

### 2. Create Deployment Package

```bash
zip -r function.zip index.js node_modules/
```

### 3. Create Lambda Function (first time only)

```bash
aws lambda create-function \
  --function-name motionplay-updateDeviceConfig \
  --runtime nodejs18.x \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/motionplay-lambda-role \
  --handler index.handler \
  --zip-file fileb://function.zip \
  --timeout 15 \
  --memory-size 256 \
  --environment Variables="{DEVICES_TABLE=MotionPlayDevices,AWS_REGION=us-west-2}"
```

### 4. Update Existing Function

```bash
aws lambda update-function-code \
  --function-name motionplay-updateDeviceConfig \
  --zip-file fileb://function.zip
```

## API Gateway Integration

**Method**: PUT  
**Path**: `/device/{device_id}/config`  
**Integration Type**: Lambda Proxy  

### Integration Request

- Lambda Function: `motionplay-updateDeviceConfig`
- Use Lambda Proxy integration: Yes

### Method Response

**Status Code**: 200

**Response Headers**:
- `Access-Control-Allow-Origin`: `*`
- `Content-Type`: `application/json`

**Request Body**:
```json
{
  "sensor_config": {
    "sample_rate_hz": 500,
    "led_current": "100mA",
    "integration_time": "2T",
    "high_resolution": true,
    "read_ambient": false,
    "i2c_clock_khz": 400
  }
}
```

**Response Body**:
```json
{
  "device_id": "motionplay-device-001",
  "sensor_config": {
    "sample_rate_hz": 500,
    "led_current": "100mA",
    "integration_time": "2T",
    "high_resolution": true,
    "read_ambient": false,
    "i2c_clock_khz": 400
  },
  "config_updated_at": 1732579200000,
  "message": "Config updated and command sent to device"
}
```

## Testing

### Test with AWS CLI

```bash
aws lambda invoke \
  --function-name motionplay-updateDeviceConfig \
  --payload '{
    "pathParameters": {"device_id": "motionplay-device-001"},
    "body": "{\"sensor_config\":{\"sample_rate_hz\":500,\"led_current\":\"100mA\",\"integration_time\":\"2T\",\"high_resolution\":true,\"read_ambient\":false,\"i2c_clock_khz\":400}}"
  }' \
  response.json

cat response.json
```

### Test via API Gateway

```bash
curl -X PUT \
  https://YOUR_API_GATEWAY_ID.execute-api.us-west-2.amazonaws.com/prod/device/motionplay-device-001/config \
  -H "Content-Type: application/json" \
  -d '{
    "sensor_config": {
      "sample_rate_hz": 500,
      "led_current": "100mA",
      "integration_time": "2T",
      "high_resolution": true,
      "read_ambient": false,
      "i2c_clock_khz": 400
    }
  }'
```

### Verify MQTT Command Sent

Check device serial output or AWS IoT Core MQTT test client:
- Subscribe to: `motionplay/+/commands`
- Should see `configure_sensors` command with config payload

## Troubleshooting

### "Table not found"
- Verify `DEVICES_TABLE` environment variable is set correctly
- Verify the table exists: `aws dynamodb describe-table --table-name MotionPlayDevices`

### "Access denied to iot:Publish"
- Check Lambda execution role has IoT Publish permission
- Verify resource ARN pattern: `arn:aws:iot:REGION:ACCOUNT:topic/motionplay/*/commands`

### Config saved but device not responding
- Check device is connected to MQTT
- Verify device is subscribed to correct topic: `motionplay/{device_id}/commands`
- Check IoT Core MQTT test client to confirm message was published

### "sensor_config is required" error
- Verify request body includes `sensor_config` object
- Check JSON is properly formatted


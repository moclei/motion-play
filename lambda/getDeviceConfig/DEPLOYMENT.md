# getDeviceConfig Lambda - Deployment Guide

## Function Details

**Function Name**: `motionplay-getDeviceConfig`  
**Runtime**: Node.js 18.x or later  
**Handler**: `index.handler`  
**Timeout**: 10 seconds  
**Memory**: 128 MB  

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
        "dynamodb:GetItem"
      ],
      "Resource": "arn:aws:dynamodb:us-west-2:*:table/MotionPlayDevices"
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
cd lambda/getDeviceConfig
npm install
```

### 2. Create Deployment Package

```bash
zip -r function.zip index.js node_modules/
```

### 3. Create Lambda Function (first time only)

```bash
aws lambda create-function \
  --function-name motionplay-getDeviceConfig \
  --runtime nodejs18.x \
  --role arn:aws:iam::YOUR_ACCOUNT_ID:role/motionplay-lambda-role \
  --handler index.handler \
  --zip-file fileb://function.zip \
  --timeout 10 \
  --memory-size 128 \
  --environment Variables="{DEVICES_TABLE=MotionPlayDevices,AWS_REGION=us-west-2}"
```

### 4. Update Existing Function

```bash
aws lambda update-function-code \
  --function-name motionplay-getDeviceConfig \
  --zip-file fileb://function.zip
```

## API Gateway Integration

**Method**: GET  
**Path**: `/device/{device_id}/config`  
**Integration Type**: Lambda Proxy  

### Integration Request

- Lambda Function: `motionplay-getDeviceConfig`
- Use Lambda Proxy integration: Yes

### Method Response

**Status Code**: 200

**Response Headers**:
- `Access-Control-Allow-Origin`: `*`
- `Content-Type`: `application/json`

**Response Body**:
```json
{
  "device_id": "motionplay-device-001",
  "sensor_config": {
    "sample_rate_hz": 1000,
    "led_current": "200mA",
    "integration_time": "1T",
    "high_resolution": true,
    "read_ambient": true,
    "i2c_clock_khz": 400
  },
  "config_updated_at": 1732579200000
}
```

## Testing

### Test with AWS CLI

```bash
aws lambda invoke \
  --function-name motionplay-getDeviceConfig \
  --payload '{"pathParameters":{"device_id":"motionplay-device-001"}}' \
  response.json

cat response.json
```

### Test via API Gateway

```bash
curl https://YOUR_API_GATEWAY_ID.execute-api.us-west-2.amazonaws.com/prod/device/motionplay-device-001/config
```

## Troubleshooting

### "Table not found"
- Verify `DEVICES_TABLE` environment variable is set correctly
- Verify the table exists: `aws dynamodb describe-table --table-name MotionPlayDevices`

### "Access denied"
- Check Lambda execution role has DynamoDB GetItem permission
- Verify resource ARN in IAM policy matches your table

### Returns defaults every time
- No device record exists yet - this is expected on first run
- Update config via `updateDeviceConfig` Lambda to create the record


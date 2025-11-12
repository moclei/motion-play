# Lambda Deployment Guide for Motion Play

This guide walks you through deploying the Lambda functions and connecting them to IoT Core.

## Prerequisites

- ✅ AWS CLI configured
- ✅ DynamoDB tables created
- ✅ IoT Thing and certificates created
- ✅ IoT Policy attached

## Working Directory

**IMPORTANT:** Run all commands from the project root directory:

```bash
cd /Users/marcocleirigh/Workspace/motion-play
```

This ensures:

- Lambda function paths are correct (`lambda/functionName`)
- Temporary files (policies, zips) are created in the root and cleaned up
- Relative paths work correctly

## Overview

We'll deploy 7 Lambda functions:

1. **processData** - Stores sensor data from MQTT to DynamoDB
2. **processStatus** - Updates device status in DynamoDB
3. **sendCommand** - Sends commands to devices via MQTT
4. **getSessions** - Lists recording sessions
5. **getSessionData** - Retrieves session details and sensor data
6. **updateSession** - Updates session metadata
7. **deleteSession** - Deletes sessions and associated data

## Step 1: Create IAM Role for Lambda

First, create a trust policy file:

```bash
cat > lambda-trust-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
```

Create the IAM role:

```bash
aws iam create-role \
    --role-name MotionPlayLambdaRole \
    --assume-role-policy-document file://lambda-trust-policy.json
```

Create the permissions policy:

```bash
cat > lambda-permissions-policy.json << 'EOF'
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:us-west-2:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:PutItem",
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:Scan",
        "dynamodb:BatchWriteItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:us-west-2:*:table/MotionPlaySessions",
        "arn:aws:dynamodb:us-west-2:*:table/MotionPlaySessions/*",
        "arn:aws:dynamodb:us-west-2:*:table/MotionPlaySensorData",
        "arn:aws:dynamodb:us-west-2:*:table/MotionPlayDevices"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "iot:Publish"
      ],
      "Resource": "arn:aws:iot:us-west-2:*:topic/motionplay/*/commands"
    }
  ]
}
EOF
```

Attach the policy to the role:

```bash
aws iam put-role-policy \
    --role-name MotionPlayLambdaRole \
    --policy-name MotionPlayLambdaPolicy \
    --policy-document file://lambda-permissions-policy.json
```

Get the role ARN (save this for next steps):

```bash
aws iam get-role --role-name MotionPlayLambdaRole --query 'Role.Arn' --output text
```

Clean up policy files:

```bash
rm lambda-trust-policy.json lambda-permissions-policy.json
```

## Step 2: Deploy Lambda Functions

Deploy each function one by one:

### 2.1 Deploy processData Function

```bash
cd lambda/processData
npm install
zip -r function.zip .

aws lambda create-function \
    --function-name motionplay-processData \
    --runtime nodejs20.x \
    --role arn:aws:iam::861647825061:role/MotionPlayLambdaRole \
    --handler index.handler \
    --zip-file fileb://function.zip \
    --timeout 30 \
    --memory-size 256

rm function.zip
cd ../..
```

### 2.2 Deploy processStatus Function

```bash
cd lambda/processStatus
npm install
zip -r function.zip .

aws lambda create-function \
    --function-name motionplay-processStatus \
    --runtime nodejs20.x \
    --role arn:aws:iam::861647825061:role/MotionPlayLambdaRole \
    --handler index.handler \
    --zip-file fileb://function.zip \
    --timeout 15 \
    --memory-size 128

rm function.zip
cd ../..
```

### 2.3 Deploy sendCommand Function

```bash
cd lambda/sendCommand
npm install
zip -r function.zip .

aws lambda create-function \
    --function-name motionplay-sendCommand \
    --runtime nodejs20.x \
    --role arn:aws:iam::861647825061:role/MotionPlayLambdaRole \
    --handler index.handler \
    --zip-file fileb://function.zip \
    --timeout 15 \
    --memory-size 128

rm function.zip
cd ../..
```

### 2.4 Deploy getSessions Function

```bash
cd lambda/getSessions
npm install
zip -r function.zip .

aws lambda create-function \
    --function-name motionplay-getSessions \
    --runtime nodejs20.x \
    --role arn:aws:iam::861647825061:role/MotionPlayLambdaRole \
    --handler index.handler \
    --zip-file fileb://function.zip \
    --timeout 15 \
    --memory-size 128

rm function.zip
cd ../..
```

### 2.5 Deploy getSessionData Function

```bash
cd lambda/getSessionData
npm install
zip -r function.zip .

aws lambda create-function \
    --function-name motionplay-getSessionData \
    --runtime nodejs20.x \
    --role arn:aws:iam::861647825061:role/MotionPlayLambdaRole \
    --handler index.handler \
    --zip-file fileb://function.zip \
    --timeout 30 \
    --memory-size 256

rm function.zip
cd ../..
```

### 2.6 Deploy updateSession Function

```bash
cd lambda/updateSession
npm install
zip -r function.zip .

aws lambda create-function \
    --function-name motionplay-updateSession \
    --runtime nodejs20.x \
    --role arn:aws:iam::861647825061:role/MotionPlayLambdaRole \
    --handler index.handler \
    --zip-file fileb://function.zip \
    --timeout 15 \
    --memory-size 128

rm function.zip
cd ../..
```

### 2.7 Deploy deleteSession Function

```bash
cd lambda/deleteSession
npm install
zip -r function.zip .

aws lambda create-function \
    --function-name motionplay-deleteSession \
    --runtime nodejs20.x \
    --role arn:aws:iam::861647825061:role/MotionPlayLambdaRole \
    --handler index.handler \
    --zip-file fileb://function.zip \
    --timeout 30 \
    --memory-size 128

rm function.zip
cd ../..
```

## Step 3: Create IoT Rules for MQTT Integration

### 3.1 Create Rule for Sensor Data

Create the rule to process sensor data:

```bash
aws iot create-topic-rule --rule-name ProcessMotionPlayData --topic-rule-payload '{
  "sql": "SELECT * FROM '\''motionplay/+/data'\''",
  "description": "Route sensor data to Lambda for processing",
  "actions": [
    {
      "lambda": {
        "functionArn": "arn:aws:lambda:us-west-2:861647825061:function:motionplay-processData"
      }
    }
  ]
}'
```

Grant IoT permission to invoke the Lambda:

```bash
aws lambda add-permission \
    --function-name motionplay-processData \
    --statement-id IoTInvokeProcessData \
    --action lambda:InvokeFunction \
    --principal iot.amazonaws.com \
    --source-arn arn:aws:iot:us-west-2:861647825061:rule/ProcessMotionPlayData
```

### 3.2 Create Rule for Status Updates

Create the rule to process status updates:

```bash
aws iot create-topic-rule --rule-name ProcessMotionPlayStatus --topic-rule-payload '{
  "sql": "SELECT * FROM '\''motionplay/+/status'\''",
  "description": "Route device status to Lambda for processing",
  "actions": [
    {
      "lambda": {
        "functionArn": "arn:aws:lambda:us-west-2:861647825061:function:motionplay-processStatus"
      }
    }
  ]
}'
```

Grant IoT permission to invoke the Lambda:

```bash
aws lambda add-permission \
    --function-name motionplay-processStatus \
    --statement-id IoTInvokeProcessStatus \
    --action lambda:InvokeFunction \
    --principal iot.amazonaws.com \
    --source-arn arn:aws:iot:us-west-2:861647825061:rule/ProcessMotionPlayStatus
```

## Step 4: Test the Functions

### 4.1 Test processData Function

First create a test payload file:

```bash
cat > test-processData.json << 'EOF'
{
  "topic": "motionplay/device-001/data",
  "device_id": "device-001",
  "session_id": "test-session-001",
  "start_timestamp": "2024-01-01T00:00:00.000Z",
  "mode": "test",
  "sample_rate": 1000,
  "readings": [
    {"t": 0, "p": 1, "s": 0, "prox": 100, "amb": 50},
    {"t": 100, "p": 2, "s": 0, "prox": 110, "amb": 55}
  ]
}
EOF
```

Invoke the function:

```bash
aws lambda invoke \
    --function-name motionplay-processData \
    --cli-binary-format raw-in-base64-out \
    --payload file://test-processData.json \
    response.json

cat response.json
rm test-processData.json
```

### 4.2 Test processStatus Function

Create test payload:

```bash
cat > test-processStatus.json << 'EOF'
{
  "topic": "motionplay/device-001/status",
  "device_id": "device-001",
  "status": "online",
  "current_mode": "test",
  "wifi_rssi": -45,
  "free_heap": 120000,
  "uptime_ms": 60000
}
EOF
```

Invoke the function:

```bash
aws lambda invoke \
    --function-name motionplay-processStatus \
    --cli-binary-format raw-in-base64-out \
    --payload file://test-processStatus.json \
    response.json

cat response.json
rm test-processStatus.json
```

### 4.3 Test getSessions Function

```bash
# Test without filters (gets all sessions)
aws lambda invoke \
    --function-name motionplay-getSessions \
    --cli-binary-format raw-in-base64-out \
    --payload '{}' \
    response.json

cat response.json

# Test with device filter (simulating API Gateway query params)
aws lambda invoke \
    --function-name motionplay-getSessions \
    --cli-binary-format raw-in-base64-out \
    --payload '{"queryStringParameters": {"device_id": "device-001", "limit": "10"}}' \
    response.json

cat response.json
```

### 4.4 Test other Lambda Functions

The remaining functions (getSessionData, updateSession, deleteSession, sendCommand) are designed for API Gateway integration. For now, you can skip testing these individually as they require specific path parameters and request formats that will be set up with API Gateway.

To verify all functions are deployed:

```bash
aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'motionplay')].[FunctionName, Runtime, State]" --output table
```

## Step 5: Verify Deployment

### Check Lambda Functions

```bash
aws lambda list-functions --query "Functions[?starts_with(FunctionName, 'motionplay')].[FunctionName, Runtime, State]" --output table
```

### Check IoT Rules

```bash
aws iot list-topic-rules | grep motionplay
```

### Check DynamoDB for Test Data

```bash
aws dynamodb scan --table-name MotionPlaySessions --max-items 5
```

## Troubleshooting

**Function creation fails:**

- Verify IAM role was created successfully
- Check account ID in ARN is correct
- Ensure you're in the correct region

**IoT Rules don't trigger:**

- Check rule SQL syntax
- Verify Lambda permissions
- Test with IoT Core test client

**Lambda execution fails:**

- Check CloudWatch logs: `aws logs tail /aws/lambda/motionplay-processData`
- Verify DynamoDB table names
- Check IAM permissions

## Next Steps

1. **API Gateway Setup** (for web interface)

   - Create REST API
   - Connect to Lambda functions
   - Enable CORS

2. **CloudWatch Monitoring**

   - Set up log groups
   - Create alarms for errors
   - Monitor Lambda costs

3. **Begin Phase 1**
   - Implement ESP32 firmware
   - Test MQTT publishing
   - Verify data flow

## Clean Up Commands (if needed)

To remove all Lambda functions:

```bash
for func in processData processStatus sendCommand getSessions getSessionData updateSession deleteSession; do
    aws lambda delete-function --function-name motionplay-$func
done
```

To remove IoT Rules:

```bash
aws iot delete-topic-rule --rule-name ProcessMotionPlayData
aws iot delete-topic-rule --rule-name ProcessMotionPlayStatus
```

## Cost Considerations

- Lambda: First 1M requests/month free
- DynamoDB: 25GB storage + 25 RCU/WCU free
- IoT Core: 250k messages/month free
- Estimated monthly cost for development: < $1

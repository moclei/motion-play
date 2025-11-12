# AWS Setup Guide for Motion Play

This guide walks you through setting up the AWS infrastructure manually.

## Prerequisites

- AWS Account
- AWS CLI configured (`aws configure`)
- Appropriate IAM permissions

## Step 1: Configure AWS CLI

```bash
aws configure
# Enter AWS Access Key ID
# Enter AWS Secret Access Key
# Enter region: us-west-2
# Enter output format: json
```

Test configuration:
```bash
aws sts get-caller-identity
```

## Step 2: Set Up Billing Alert

1. Go to AWS Console → Billing → Budgets
2. Click "Create budget"
3. Choose "Cost budget"
4. Set amount: $20
5. Configure email alert
6. Create budget

## Step 3: Create DynamoDB Tables

### MotionPlaySessions Table

```bash
aws dynamodb create-table \
    --table-name MotionPlaySessions \
    --attribute-definitions \
        AttributeName=session_id,AttributeType=S \
        AttributeName=device_id,AttributeType=S \
        AttributeName=start_timestamp,AttributeType=S \
    --key-schema \
        AttributeName=session_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST \
    --global-secondary-indexes \
        "IndexName=DeviceTimeIndex,KeySchema=[{AttributeName=device_id,KeyType=HASH},{AttributeName=start_timestamp,KeyType=RANGE}],Projection={ProjectionType=ALL}"
```

### MotionPlaySensorData Table

```bash
aws dynamodb create-table \
    --table-name MotionPlaySensorData \
    --attribute-definitions \
        AttributeName=session_id,AttributeType=S \
        AttributeName=timestamp_offset,AttributeType=N \
    --key-schema \
        AttributeName=session_id,KeyType=HASH \
        AttributeName=timestamp_offset,KeyType=RANGE \
    --billing-mode PAY_PER_REQUEST
```

### MotionPlayDevices Table

```bash
aws dynamodb create-table \
    --table-name MotionPlayDevices \
    --attribute-definitions \
        AttributeName=device_id,AttributeType=S \
    --key-schema \
        AttributeName=device_id,KeyType=HASH \
    --billing-mode PAY_PER_REQUEST
```

## Step 4: Create IoT Thing

```bash
# Create thing
aws iot create-thing --thing-name motionplay-device-001

# Create certificates
aws iot create-keys-and-certificate \
    --set-as-active \
    --certificate-pem-outfile device-cert.pem \
    --public-key-outfile public-key.pem \
    --private-key-outfile private-key.pem \
    > certificate-output.json

# Extract certificate ARN
CERT_ARN=$(cat certificate-output.json | jq -r '.certificateArn')

# Attach certificate to thing
aws iot attach-thing-principal \
    --thing-name motionplay-device-001 \
    --principal $CERT_ARN
```

## Step 5: Create IoT Policy

Save this as `iot-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "iot:Connect",
      "Resource": "arn:aws:iot:REGION:ACCOUNT:client/motionplay-*"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Publish",
      "Resource": [
        "arn:aws:iot:REGION:ACCOUNT:topic/motionplay/*/data",
        "arn:aws:iot:REGION:ACCOUNT:topic/motionplay/*/status"
      ]
    },
    {
      "Effect": "Allow",
      "Action": "iot:Subscribe",
      "Resource": "arn:aws:iot:REGION:ACCOUNT:topicfilter/motionplay/*/commands"
    },
    {
      "Effect": "Allow",
      "Action": "iot:Receive",
      "Resource": "arn:aws:iot:REGION:ACCOUNT:topic/motionplay/*/commands"
    }
  ]
}
```

Replace REGION and ACCOUNT with your values, then:

```bash
# Get your account ID
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION="us-west-2"

# Update policy file with account ID and region
sed -i '' "s/REGION/$REGION/g" iot-policy.json
sed -i '' "s/ACCOUNT/$ACCOUNT_ID/g" iot-policy.json

# Create policy
aws iot create-policy \
    --policy-name MotionPlayDevicePolicy \
    --policy-document file://iot-policy.json

# Attach policy to certificate
aws iot attach-policy \
    --policy-name MotionPlayDevicePolicy \
    --target $CERT_ARN
```

## Step 6: Get IoT Endpoint

```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS
```

Save this endpoint URL - you'll need it for the ESP32 configuration.

## Step 7: Download Root CA Certificate

```bash
curl -o root-ca.pem https://www.amazontrust.com/repository/AmazonRootCA1.pem
```

## Step 8: Move Certificates to ESP32 Project

```bash
# Copy certificates to firmware data directory
cp device-cert.pem ../firmware/data/certs/
cp private-key.pem ../firmware/data/certs/
cp root-ca.pem ../firmware/data/certs/

# Remove from current directory for security
rm device-cert.pem private-key.pem public-key.pem root-ca.pem certificate-output.json
```

## Step 9: Create config.json for ESP32

In `firmware/data/config.json`:

```json
{
  "device_id": "motionplay-device-001",
  "wifi": {
    "ssid": "YOUR_WIFI_SSID",
    "password": "YOUR_WIFI_PASSWORD"
  },
  "mqtt": {
    "broker": "YOUR_IOT_ENDPOINT.iot.us-west-2.amazonaws.com",
    "port": 8883,
    "client_id": "motionplay-device-001"
  },
  "sampling": {
    "rate_hz": 1000,
    "max_duration_seconds": 30
  }
}
```

## Verification

### Test DynamoDB Tables

```bash
aws dynamodb list-tables
```

You should see:
- MotionPlaySessions
- MotionPlaySensorData
- MotionPlayDevices

### Test IoT Thing

```bash
aws iot describe-thing --thing-name motionplay-device-001
```

### Test MQTT Connection (from AWS Console)

1. Go to AWS IoT Core → Test
2. Subscribe to topic: `motionplay/+/status`
3. You'll test publishing from ESP32 later

## Next Steps

1. Complete Phase 1: ESP32 WiFi and MQTT implementation
2. Create Lambda functions for data processing
3. Set up API Gateway for web interface

## Troubleshooting

**Certificate Issues:**
- Ensure certificate is activated
- Verify policy is attached
- Check policy permissions match topic structure

**DynamoDB Issues:**
- Verify tables are created in correct region
- Check billing mode is set correctly

**IoT Core Issues:**
- Ensure endpoint is correct (use iot:Data-ATS type)
- Verify thing name matches exactly


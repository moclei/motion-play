# API Gateway Setup for Device Config Endpoints

This guide shows how to add the new config endpoints to your existing API Gateway.

## Prerequisites

- Existing API Gateway: `MotionPlayAPI`
- Both Lambda functions deployed:
  - `motionplay-getDeviceConfig`
  - `motionplay-updateDeviceConfig`

## Option 1: AWS Console (Recommended for Testing)

### Step 1: Navigate to API Gateway

1. Open AWS Console → API Gateway
2. Select your API: `MotionPlayAPI`
3. Select the `/prod` stage (or your deployment stage)

### Step 2: Create `/device/{device_id}/config` Resource

1. Click **Resources** in left sidebar
2. Select the root `/` or existing `/device` resource
3. Click **Actions** → **Create Resource**

**If `/device` doesn't exist:**
- Resource Name: `device`
- Resource Path: `/device`
- Enable CORS: ✅ Yes
- Click **Create Resource**

**Then create the `{device_id}` resource:**
- Select `/device` resource
- Click **Actions** → **Create Resource**
- Resource Name: `device_id`
- Resource Path: `{device_id}` (include the curly braces)
- Enable CORS: ✅ Yes
- Click **Create Resource**

**Then create the `/config` resource:**
- Select `/device/{device_id}` resource
- Click **Actions** → **Create Resource**
- Resource Name: `config`
- Resource Path: `/config`
- Enable CORS: ✅ Yes
- Click **Create Resource**

### Step 3: Add GET Method

1. Select `/device/{device_id}/config` resource
2. Click **Actions** → **Create Method**
3. Choose **GET** from dropdown
4. Click the checkmark ✓

**Configure GET Method:**
- Integration type: **Lambda Function**
- Use Lambda Proxy integration: ✅ **Yes**
- Lambda Region: `us-west-2` (or your region)
- Lambda Function: `motionplay-getDeviceConfig`
- Click **Save**
- Click **OK** to grant permission

### Step 4: Add PUT Method

1. Select `/device/{device_id}/config` resource
2. Click **Actions** → **Create Method**
3. Choose **PUT** from dropdown
4. Click the checkmark ✓

**Configure PUT Method:**
- Integration type: **Lambda Function**
- Use Lambda Proxy integration: ✅ **Yes**
- Lambda Region: `us-west-2` (or your region)
- Lambda Function: `motionplay-updateDeviceConfig`
- Click **Save**
- Click **OK** to grant permission

### Step 5: Enable CORS

For **both** GET and PUT methods:

1. Select the method
2. Click **Actions** → **Enable CORS**
3. Leave defaults:
   - Access-Control-Allow-Origin: `*`
   - Access-Control-Allow-Headers: `Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token`
   - Access-Control-Allow-Methods: `GET,PUT,OPTIONS`
4. Click **Enable CORS and replace existing CORS headers**
5. Click **Yes, replace existing values**

### Step 6: Deploy API

1. Click **Actions** → **Deploy API**
2. Deployment stage: `prod` (or your stage)
3. Click **Deploy**

### Step 7: Test Endpoints

Get your API Gateway URL:
```
https://{api-id}.execute-api.us-west-2.amazonaws.com/prod
```

Test GET:
```bash
curl https://{api-id}.execute-api.us-west-2.amazonaws.com/prod/device/motionplay-device-001/config
```

Test PUT:
```bash
curl -X PUT \
  https://{api-id}.execute-api.us-west-2.amazonaws.com/prod/device/motionplay-device-001/config \
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

## Option 2: AWS CLI

### Create Resources

```bash
# Get API ID
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='MotionPlayAPI'].id" --output text)
echo "API ID: $API_ID"

# Get root resource ID
ROOT_ID=$(aws apigateway get-resources --rest-api-id $API_ID --query "items[?path=='/'].id" --output text)
echo "Root ID: $ROOT_ID"

# Create /device resource (if doesn't exist)
DEVICE_RESOURCE=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $ROOT_ID \
  --path-part device \
  --query 'id' --output text)
echo "Device Resource ID: $DEVICE_RESOURCE"

# Create /device/{device_id} resource
DEVICE_ID_RESOURCE=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $DEVICE_RESOURCE \
  --path-part '{device_id}' \
  --query 'id' --output text)
echo "Device ID Resource ID: $DEVICE_ID_RESOURCE"

# Create /device/{device_id}/config resource
CONFIG_RESOURCE=$(aws apigateway create-resource \
  --rest-api-id $API_ID \
  --parent-id $DEVICE_ID_RESOURCE \
  --path-part config \
  --query 'id' --output text)
echo "Config Resource ID: $CONFIG_RESOURCE"
```

### Add GET Method

```bash
# Get Lambda ARN
GET_LAMBDA_ARN=$(aws lambda get-function --function-name motionplay-getDeviceConfig --query 'Configuration.FunctionArn' --output text)

# Get AWS Account ID and Region
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
REGION=us-west-2

# Create GET method
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $CONFIG_RESOURCE \
  --http-method GET \
  --authorization-type NONE

# Set Lambda integration
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $CONFIG_RESOURCE \
  --http-method GET \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${GET_LAMBDA_ARN}/invocations"

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name motionplay-getDeviceConfig \
  --statement-id apigateway-get-config \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/GET/device/{device_id}/config"
```

### Add PUT Method

```bash
# Get Lambda ARN
PUT_LAMBDA_ARN=$(aws lambda get-function --function-name motionplay-updateDeviceConfig --query 'Configuration.FunctionArn' --output text)

# Create PUT method
aws apigateway put-method \
  --rest-api-id $API_ID \
  --resource-id $CONFIG_RESOURCE \
  --http-method PUT \
  --authorization-type NONE

# Set Lambda integration
aws apigateway put-integration \
  --rest-api-id $API_ID \
  --resource-id $CONFIG_RESOURCE \
  --http-method PUT \
  --type AWS_PROXY \
  --integration-http-method POST \
  --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${PUT_LAMBDA_ARN}/invocations"

# Grant API Gateway permission to invoke Lambda
aws lambda add-permission \
  --function-name motionplay-updateDeviceConfig \
  --statement-id apigateway-update-config \
  --action lambda:InvokeFunction \
  --principal apigateway.amazonaws.com \
  --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/PUT/device/{device_id}/config"
```

### Deploy API

```bash
aws apigateway create-deployment \
  --rest-api-id $API_ID \
  --stage-name prod \
  --description "Added device config endpoints"
```

## Verification

### Check Resources Were Created

```bash
aws apigateway get-resources --rest-api-id $API_ID
```

Look for:
- `/device/{device_id}/config` resource
- GET and PUT methods on that resource

### Test Endpoints

```bash
# Get your API endpoint URL
echo "https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod"

# Test GET
curl https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/device/motionplay-device-001/config

# Test PUT
curl -X PUT \
  https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod/device/motionplay-device-001/config \
  -H "Content-Type: application/json" \
  -d '{"sensor_config":{"sample_rate_hz":500,"led_current":"100mA","integration_time":"2T","high_resolution":true,"read_ambient":false,"i2c_clock_khz":400}}'
```

## Troubleshooting

### "Missing Authentication Token"
- Verify the URL path is correct
- Ensure the API was deployed after creating methods

### "Internal Server Error"
- Check Lambda function logs in CloudWatch
- Verify Lambda has correct IAM permissions
- Test Lambda function directly first

### CORS Errors in Browser
- Enable CORS for GET, PUT, and OPTIONS methods
- Redeploy API after enabling CORS
- Check response headers include `Access-Control-Allow-Origin: *`

### "Execution failed due to configuration error: Invalid permissions"
- Run the `aws lambda add-permission` commands
- This grants API Gateway permission to invoke the Lambda functions


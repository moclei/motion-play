# Lambda Deployment Instructions
## Deploying Duty Cycle Updates

**Date:** November 26, 2025  
**Changes:** Added `duty_cycle` field support to all Lambda functions

---

## What Changed

### Lambda Functions Updated
1. **getDeviceConfig** - Returns duty_cycle in default config
2. **updateDeviceConfig** - Validates and stores duty_cycle, sends to device via MQTT
3. **processData** - Stores duty_cycle in session metadata

---

## Prerequisites

Before deploying, ensure you have:
- ✅ AWS CLI configured with appropriate credentials
- ✅ Permissions to update Lambda functions in your AWS account
- ✅ Node.js installed (for dependency bundling)

Check your AWS configuration:
```bash
aws sts get-caller-identity
```

---

## Deployment Steps

### Option 1: Use Deployment Script (Recommended)

The deployment script handles both Lambda functions and API Gateway routes:

```bash
cd lambda
chmod +x deploy-config-endpoints.sh
./deploy-config-endpoints.sh
```

This script will:
1. Package the Lambda functions with dependencies
2. Create/update Lambda functions in AWS
3. Configure API Gateway routes
4. Set up environment variables
5. Display test endpoints

### Option 2: Manual Deployment

If you prefer manual control:

#### 1. Package Lambda Functions

For each Lambda function:

```bash
# getDeviceConfig
cd lambda/getDeviceConfig
npm install
zip -r ../getDeviceConfig.zip index.js node_modules/

# updateDeviceConfig
cd ../updateDeviceConfig
npm install
zip -r ../updateDeviceConfig.zip index.js node_modules/

# processData
cd ../processData
npm install
zip -r ../processData.zip index.js node_modules/

cd ..
```

#### 2. Update Lambda Functions

```bash
# Update getDeviceConfig
aws lambda update-function-code \
  --function-name getDeviceConfig \
  --zip-file fileb://getDeviceConfig.zip \
  --region us-west-2

# Update updateDeviceConfig
aws lambda update-function-code \
  --function-name updateDeviceConfig \
  --zip-file fileb://updateDeviceConfig.zip \
  --region us-west-2

# Update processData
aws lambda update-function-code \
  --function-name processData \
  --zip-file fileb://processData.zip \
  --region us-west-2
```

#### 3. Wait for Deployment

Lambda updates take a few seconds:

```bash
aws lambda wait function-updated \
  --function-name getDeviceConfig \
  --region us-west-2

aws lambda wait function-updated \
  --function-name updateDeviceConfig \
  --region us-west-2

aws lambda wait function-updated \
  --function-name processData \
  --region us-west-2
```

---

## Verify Deployment

### 1. Check Lambda Function Status

```bash
aws lambda get-function \
  --function-name updateDeviceConfig \
  --region us-west-2 \
  --query 'Configuration.[FunctionName,LastModified,State]'
```

Expected output shows recent `LastModified` timestamp and `State: Active`

### 2. Test getDeviceConfig

Get your API Gateway endpoint:
```bash
export API_ENDPOINT=$(aws apigatewayv2 get-apis \
  --region us-west-2 \
  --query 'Items[?Name==`MotionPlayAPI`].ApiEndpoint' \
  --output text)

echo $API_ENDPOINT
```

Test getting config:
```bash
curl ${API_ENDPOINT}/device/motionplay-device-001/config | jq
```

Expected response should include `duty_cycle`:
```json
{
  "device_id": "motionplay-device-001",
  "sensor_config": {
    "sample_rate_hz": 1000,
    "led_current": "200mA",
    "integration_time": "2T",
    "duty_cycle": "1/40",
    "high_resolution": true,
    "read_ambient": true,
    "i2c_clock_khz": 400
  },
  "config_updated_at": null
}
```

### 3. Test updateDeviceConfig

```bash
curl -X PUT \
  ${API_ENDPOINT}/device/motionplay-device-001/config \
  -H 'Content-Type: application/json' \
  -d '{
    "sensor_config": {
      "sample_rate_hz": 1000,
      "led_current": "200mA",
      "integration_time": "2T",
      "duty_cycle": "1/40",
      "high_resolution": true,
      "read_ambient": true,
      "i2c_clock_khz": 400
    }
  }' | jq
```

Expected response:
```json
{
  "device_id": "motionplay-device-001",
  "sensor_config": {
    "sample_rate_hz": 1000,
    "led_current": "200mA",
    "integration_time": "2T",
    "duty_cycle": "1/40",
    "high_resolution": true,
    "read_ambient": true,
    "i2c_clock_khz": 400
  },
  "config_updated_at": 1732635600000,
  "message": "Config updated and command sent to device"
}
```

### 4. Check CloudWatch Logs

View recent Lambda executions:

```bash
# updateDeviceConfig logs
aws logs tail /aws/lambda/updateDeviceConfig \
  --region us-west-2 \
  --follow

# Look for: "New config:" with duty_cycle included
```

---

## Test MQTT Command Delivery

If you have a device connected:

1. **Deploy the Lambda updates** (above)
2. **Monitor device serial output**
3. **Send config update from frontend** (or curl command above)
4. **Check device logs** for:
   ```
   Received MQTT command: configure_sensors
   sensor_config: { ..., "duty_cycle": "1/40" }
   Applying duty cycle: 1/40
   ```

---

## Rollback (If Needed)

If something goes wrong, you can rollback to a previous version:

```bash
# List function versions
aws lambda list-versions-by-function \
  --function-name updateDeviceConfig \
  --region us-west-2

# Rollback to specific version (replace VERSION_NUMBER)
aws lambda update-function-configuration \
  --function-name updateDeviceConfig \
  --region us-west-2 \
  --publish \
  --revision-id VERSION_NUMBER
```

Or redeploy from a previous commit:
```bash
git checkout <previous-commit>
cd lambda
./deploy-config-endpoints.sh
```

---

## Common Issues

### Issue: "Function not found"
**Solution:** Ensure Lambda functions exist. Run deployment script with `--create` flag if needed.

### Issue: "Permission denied"
**Solution:** Check IAM permissions. Your user needs:
- `lambda:UpdateFunctionCode`
- `lambda:UpdateFunctionConfiguration`
- `lambda:GetFunction`

### Issue: "Package size too large"
**Solution:** Ensure you're only including necessary node_modules:
```bash
npm install --production
```

### Issue: Config update doesn't reach device
**Solution:** 
1. Check device is connected to MQTT (check CloudWatch IoT logs)
2. Verify MQTT topic is correct: `motionplay/{device_id}/commands`
3. Check device subscription in firmware

---

## Post-Deployment Testing

After deploying, test the full flow:

1. **Frontend → Lambda → DynamoDB:**
   - Open frontend settings
   - Change duty cycle to "1/40"
   - Click "Apply Configuration"
   - Verify no errors

2. **Lambda → MQTT → Device:**
   - Monitor device serial output
   - Should see: "Received MQTT command"
   - Should see: "Applied config: ... Duty=1/40"

3. **Device → Data Collection → Lambda → DynamoDB:**
   - Start a data collection session
   - Stop collection
   - Check frontend session list
   - View session details
   - Verify `duty_cycle` appears in configuration

4. **DynamoDB → Frontend:**
   - Load session data
   - Check SessionConfig component shows duty cycle

---

## Monitoring

After deployment, monitor for issues:

```bash
# Watch Lambda errors
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Errors \
  --dimensions Name=FunctionName,Value=updateDeviceConfig \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Sum \
  --region us-west-2

# Watch Lambda duration
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=updateDeviceConfig \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --region us-west-2
```

---

## Summary

✅ Updated 3 Lambda functions to support duty_cycle  
✅ Deployment script ready  
✅ Testing procedures documented  
✅ Rollback procedure available  

**Next:** Deploy and test!

---

*See also: `docs/references/vcnl4040/DUTY_CYCLE_IMPLEMENTATION.md` for the full implementation details*


# Config Endpoints - Automated Deployment

This directory contains the automated deployment script for the device configuration endpoints.

## Quick Start

### Prerequisites

1. **AWS CLI** configured with credentials
   ```bash
   aws configure
   # Enter your credentials and set region to us-west-2
   ```

2. **Verify AWS access**
   ```bash
   aws sts get-caller-identity
   ```

3. **Node.js and npm** installed
   ```bash
   node --version  # Should be v16 or later
   npm --version
   ```

4. **Existing resources**:
   - API Gateway named `MotionPlayAPI`
   - DynamoDB table `MotionPlayDevices`

5. **Lambda execution role** (if you don't have one, see below)

### First-Time Setup: Create Lambda Execution Role

If you don't have a Lambda execution role yet, run this **once**:

```bash
./setup-lambda-role.sh
```

This creates a role named `motionplay-lambda-execution-role` with all necessary permissions:
- ✅ DynamoDB access (GetItem, UpdateItem, PutItem)
- ✅ IoT Core access (Publish to device topics)
- ✅ CloudWatch Logs access

**Then proceed with deployment below.**

### Deploy Everything

From the `lambda` directory, run:

```bash
./deploy-config-endpoints.sh
```

The script will:
- ✅ Install dependencies for both Lambda functions
- ✅ Create deployment packages
- ✅ Deploy/update Lambda functions
- ✅ Configure API Gateway routes
- ✅ Enable CORS
- ✅ Deploy API to prod stage
- ✅ Test both endpoints

**Expected output**: Colored status messages showing progress, ending with test results and the API endpoint URL.

### What Gets Created/Updated

**Lambda Functions**:
- `motionplay-getDeviceConfig` - GET endpoint handler
- `motionplay-updateDeviceConfig` - PUT endpoint handler

**API Gateway Routes**:
- `GET /device/{device_id}/config` → getDeviceConfig
- `PUT /device/{device_id}/config` → updateDeviceConfig
- `OPTIONS /device/{device_id}/config` → CORS preflight

**API Endpoints** (after deployment):
```
https://{api-id}.execute-api.us-west-2.amazonaws.com/prod/device/{device_id}/config
```

## Troubleshooting

### "AWS CLI not found"
Install AWS CLI: https://aws.amazon.com/cli/

### "Failed to get AWS account ID"
Configure AWS credentials:
```bash
aws configure
```

### "No Lambda execution role found"
Create a Lambda execution role with the necessary permissions. See `DEPLOYMENT.md` files for details.

### "API Gateway 'MotionPlayAPI' not found"
Verify your API name:
```bash
aws apigateway get-rest-apis --query "items[*].[name,id]" --output table
```

If your API has a different name, edit `deploy-config-endpoints.sh` and change:
```bash
API_NAME="YourAPIName"
```

### Deployment succeeds but tests fail

**Wait a moment**: API Gateway deployment can take 5-10 seconds to propagate.

**Check CloudWatch Logs**:
```bash
# For getDeviceConfig
aws logs tail /aws/lambda/motionplay-getDeviceConfig --follow

# For updateDeviceConfig
aws logs tail /aws/lambda/motionplay-updateDeviceConfig --follow
```

**Test manually**:
```bash
# Get your API endpoint
API_ID=$(aws apigateway get-rest-apis --query "items[?name=='MotionPlayAPI'].id" --output text)
echo "https://${API_ID}.execute-api.us-west-2.amazonaws.com/prod"

# Test GET
curl https://${API_ID}.execute-api.us-west-2.amazonaws.com/prod/device/motionplay-device-001/config

# Test PUT
curl -X PUT \
  https://${API_ID}.execute-api.us-west-2.amazonaws.com/prod/device/motionplay-device-001/config \
  -H "Content-Type: application/json" \
  -d '{"sensor_config":{"sample_rate_hz":500,"led_current":"100mA","integration_time":"2T","high_resolution":true,"read_ambient":false,"i2c_clock_khz":400}}'
```

## Redeploying After Changes

If you modify the Lambda function code:

```bash
# Quick redeploy (just updates function code)
./deploy-config-endpoints.sh
```

The script is idempotent - safe to run multiple times.

## Manual Deployment

If you prefer manual deployment, see:
- `getDeviceConfig/DEPLOYMENT.md`
- `updateDeviceConfig/DEPLOYMENT.md`
- `../docs/initiatives/config-sync/API_GATEWAY_SETUP.md`

## Next Steps After Deployment

Once deployed successfully:

1. **Update your frontend `.env`**:
   ```
   VITE_API_ENDPOINT=https://{api-id}.execute-api.us-west-2.amazonaws.com/prod
   VITE_DEVICE_ID=motionplay-device-001
   ```

2. **Update frontend code** (Phase 2):
   - Modify `api.ts` to add new methods
   - Update `SettingsModal` to fetch/save config
   - Update `SessionList` to display config

3. **Update firmware** (Phase 3):
   - Add HTTP config fetch on boot
   - Update display to show config

4. **Test end-to-end**:
   - Change config in frontend
   - Verify firmware receives update
   - Reboot firmware
   - Verify config persists

## Support

If deployment fails:
1. Check the error message (errors are in red)
2. Review the prerequisites above
3. Check CloudWatch Logs for Lambda errors
4. See individual `DEPLOYMENT.md` files for detailed troubleshooting


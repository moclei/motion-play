# Infrastructure Directory

AWS infrastructure configuration and setup files.

> **Project Context:** See [.context/PROJECT.md](../.context/PROJECT.md) for architecture overview.

## Files

- `aws-setup-guide.md` - Step-by-step AWS setup instructions
- `lambda-deployment-guide.md` - Lambda function deployment guide
- `aws-config.json` - Non-sensitive AWS configuration (endpoints, resource names)
- `certificate-output.json` - Certificate metadata (gitignored)
- `iot-policy.json` - IoT policy document (gitignored)

## Important Notes

1. **Update aws-config.json** with your actual IoT endpoint from:

   ```bash
   aws iot describe-endpoint --endpoint-type iot:Data-ATS
   ```

2. **Security**: Files containing certificates or sensitive data are gitignored

3. **Policy Management**: To view/edit your IoT policy in the future:
   - AWS Console: IoT Core → Security → Policies → MotionPlayDevicePolicy
   - AWS CLI: `aws iot get-policy --policy-name MotionPlayDevicePolicy`

## Viewing Resources in AWS Console

### DynamoDB Tables

1. Go to AWS Console → DynamoDB
2. Click "Tables" in the left sidebar
3. You'll see: MotionPlaySessions, MotionPlaySensorData, MotionPlayDevices

### IoT Core Resources

1. Go to AWS Console → IoT Core
2. **Things**: Manage → All devices → Things
3. **Certificates**: Security → Certificates
4. **Policies**: Security → Policies

### Lambda Functions (when created)

1. Go to AWS Console → Lambda
2. Functions will be listed with prefix "motionplay-"

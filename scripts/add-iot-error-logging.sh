#!/bin/bash

# Add error logging to IoT Rule
# This will help identify if messages are being dropped

echo "Adding CloudWatch error action to IoT Rule..."

# Create updated rule with error action
cat > /tmp/iot-rule-update.json << 'EOF'
{
  "sql": "SELECT * FROM 'motionplay/+/data'",
  "description": "Route sensor data to Lambda for processing",
  "actions": [
    {
      "lambda": {
        "functionArn": "arn:aws:lambda:us-west-2:861647825061:function:motionplay-processData"
      }
    }
  ],
  "errorAction": {
    "cloudwatchLogs": {
      "logGroupName": "/aws/iot/rules/ProcessMotionPlayData/errors",
      "roleArn": "arn:aws:iam::861647825061:role/MotionPlayIoTRole"
    }
  },
  "ruleDisabled": false,
  "awsIotSqlVersion": "2015-10-08"
}
EOF

# Update the rule
aws iot replace-topic-rule \
    --rule-name ProcessMotionPlayData \
    --topic-rule-payload file:///tmp/iot-rule-update.json

if [ $? -eq 0 ]; then
    echo "✅ Error logging enabled!"
    echo ""
    echo "Errors will be logged to: /aws/iot/rules/ProcessMotionPlayData/errors"
    echo ""
    echo "To view errors:"
    echo "  aws logs tail /aws/iot/rules/ProcessMotionPlayData/errors --follow"
else
    echo "❌ Failed to update rule"
    echo "You may need to create the IAM role first"
fi

rm /tmp/iot-rule-update.json


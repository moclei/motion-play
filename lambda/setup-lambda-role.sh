#!/bin/bash

###############################################################################
# Motion Play - Lambda Execution Role Setup
# 
# This script creates an IAM role for Lambda functions with permissions for:
# - DynamoDB (GetItem, UpdateItem)
# - IoT Core (Publish)
# - CloudWatch Logs
###############################################################################

set -e  # Exit on error

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_status() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_header "Setting Up Lambda Execution Role"

# Configuration
ROLE_NAME="motionplay-lambda-execution-role"
REGION="us-west-2"
DEVICES_TABLE="MotionPlayDevices"

# Get AWS account ID
print_status "Getting AWS account details..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$ACCOUNT_ID" ]; then
    print_error "Failed to get AWS account ID. Check your AWS credentials."
    exit 1
fi
print_success "AWS Account ID: $ACCOUNT_ID"

# Check if role already exists
print_status "Checking if role already exists..."
if aws iam get-role --role-name $ROLE_NAME &> /dev/null; then
    print_success "Role $ROLE_NAME already exists"
    ROLE_ARN=$(aws iam get-role --role-name $ROLE_NAME --query 'Role.Arn' --output text)
    print_success "Role ARN: $ROLE_ARN"
    echo ""
    echo -e "${GREEN}Role is ready to use!${NC}"
    echo ""
    echo "You can now run: ./deploy-config-endpoints.sh"
    exit 0
fi

# Create trust policy document
print_status "Creating trust policy..."
cat > /tmp/lambda-trust-policy.json << EOF
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
print_success "Trust policy created"

# Create the role
print_status "Creating IAM role..."
aws iam create-role \
    --role-name $ROLE_NAME \
    --assume-role-policy-document file:///tmp/lambda-trust-policy.json \
    --description "Execution role for Motion Play Lambda functions" > /dev/null

ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${ROLE_NAME}"
print_success "Role created: $ROLE_NAME"

# Create and attach DynamoDB policy
print_status "Creating DynamoDB permissions policy..."
cat > /tmp/lambda-dynamodb-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:UpdateItem",
        "dynamodb:PutItem"
      ],
      "Resource": [
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/${DEVICES_TABLE}",
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/MotionPlaySessions",
        "arn:aws:dynamodb:${REGION}:${ACCOUNT_ID}:table/MotionPlaySensorData"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name motionplay-dynamodb-access \
    --policy-document file:///tmp/lambda-dynamodb-policy.json > /dev/null

print_success "DynamoDB permissions attached"

# Create and attach IoT policy
print_status "Creating IoT permissions policy..."
cat > /tmp/lambda-iot-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iot:Publish"
      ],
      "Resource": [
        "arn:aws:iot:${REGION}:${ACCOUNT_ID}:topic/motionplay/*/commands",
        "arn:aws:iot:${REGION}:${ACCOUNT_ID}:topic/motionplay/*/config"
      ]
    }
  ]
}
EOF

aws iam put-role-policy \
    --role-name $ROLE_NAME \
    --policy-name motionplay-iot-access \
    --policy-document file:///tmp/lambda-iot-policy.json > /dev/null

print_success "IoT permissions attached"

# Attach AWS managed policy for CloudWatch Logs
print_status "Attaching CloudWatch Logs permissions..."
aws iam attach-role-policy \
    --role-name $ROLE_NAME \
    --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole > /dev/null

print_success "CloudWatch Logs permissions attached"

# Clean up temp files
rm -f /tmp/lambda-trust-policy.json
rm -f /tmp/lambda-dynamodb-policy.json
rm -f /tmp/lambda-iot-policy.json

# Wait for role to propagate
print_status "Waiting 10 seconds for IAM role to propagate..."
sleep 10

print_header "Setup Complete!"

echo ""
echo -e "${GREEN}✓ IAM Role Created Successfully${NC}"
echo ""
echo -e "${BLUE}Role Name:${NC} $ROLE_NAME"
echo -e "${BLUE}Role ARN:${NC}  $ROLE_ARN"
echo ""
echo -e "${BLUE}Permissions Granted:${NC}"
echo "  • DynamoDB: GetItem, UpdateItem, PutItem"
echo "    - MotionPlayDevices"
echo "    - MotionPlaySessions"
echo "    - MotionPlaySensorData"
echo "  • IoT Core: Publish"
echo "    - motionplay/*/commands"
echo "    - motionplay/*/config"
echo "  • CloudWatch Logs: Full access"
echo ""
echo -e "${GREEN}Next Step:${NC}"
echo "  Run the deployment script:"
echo "  ./deploy-config-endpoints.sh"
echo ""


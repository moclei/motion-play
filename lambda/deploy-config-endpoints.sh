#!/bin/bash

###############################################################################
# Motion Play - Config Endpoints Deployment Script
# 
# This script deploys the getDeviceConfig and updateDeviceConfig Lambda 
# functions and configures API Gateway routes.
#
# Prerequisites:
# - AWS CLI configured with appropriate credentials
# - Node.js and npm installed
# - Existing API Gateway (MotionPlayAPI)
# - Existing Lambda execution role with appropriate permissions
###############################################################################

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REGION="us-west-2"
DEVICES_TABLE="MotionPlayDevices"
API_NAME="MotionPlayAPI"

# Function to print colored output
print_status() {
    echo -e "${BLUE}==>${NC} $1"
}

print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

###############################################################################
# Step 0: Prerequisites Check
###############################################################################

print_header "Step 0: Checking Prerequisites"

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    print_error "AWS CLI not found. Please install it first."
    exit 1
fi
print_success "AWS CLI found"

# Check Node.js
if ! command -v node &> /dev/null; then
    print_error "Node.js not found. Please install it first."
    exit 1
fi
print_success "Node.js found: $(node --version)"

# Check npm
if ! command -v npm &> /dev/null; then
    print_error "npm not found. Please install it first."
    exit 1
fi
print_success "npm found: $(npm --version)"

# Get AWS account details
print_status "Getting AWS account details..."
ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text)
if [ -z "$ACCOUNT_ID" ]; then
    print_error "Failed to get AWS account ID. Check your AWS credentials."
    exit 1
fi
print_success "AWS Account ID: $ACCOUNT_ID"
print_success "AWS Region: $REGION"

# Check if DynamoDB table exists
print_status "Checking if $DEVICES_TABLE table exists..."
if aws dynamodb describe-table --table-name $DEVICES_TABLE --region $REGION &> /dev/null; then
    print_success "DynamoDB table $DEVICES_TABLE found"
else
    print_warning "DynamoDB table $DEVICES_TABLE not found. It will be created when needed."
fi

# Get Lambda execution role
print_status "Looking for Lambda execution role..."
LAMBDA_ROLE=$(aws iam list-roles --query "Roles[?contains(RoleName, 'motionplay') && contains(RoleName, 'lambda')].RoleName" --output text | head -1)
if [ -z "$LAMBDA_ROLE" ]; then
    print_error "No Lambda execution role found. Please create a role with:"
    print_error "  - DynamoDB: GetItem, UpdateItem permissions"
    print_error "  - IoT: Publish permissions"
    print_error "  - CloudWatch Logs permissions"
    exit 1
fi
LAMBDA_ROLE_ARN="arn:aws:iam::${ACCOUNT_ID}:role/${LAMBDA_ROLE}"
print_success "Lambda role found: $LAMBDA_ROLE"

###############################################################################
# Step 1: Deploy getDeviceConfig Lambda
###############################################################################

print_header "Step 1: Deploying getDeviceConfig Lambda"

cd getDeviceConfig

print_status "Installing dependencies..."
npm install --silent
print_success "Dependencies installed"

print_status "Creating deployment package..."
if [ -f function.zip ]; then
    rm function.zip
fi
zip -q -r function.zip index.js node_modules/
print_success "Deployment package created: $(du -h function.zip | cut -f1)"

# Check if Lambda function exists
print_status "Checking if Lambda function exists..."
if aws lambda get-function --function-name motionplay-getDeviceConfig --region $REGION &> /dev/null; then
    print_status "Function exists. Updating code..."
    aws lambda update-function-code \
        --function-name motionplay-getDeviceConfig \
        --zip-file fileb://function.zip \
        --region $REGION \
        > /dev/null
    print_success "Function code updated"
else
    print_status "Function doesn't exist. Creating..."
    aws lambda create-function \
        --function-name motionplay-getDeviceConfig \
        --runtime nodejs18.x \
        --role $LAMBDA_ROLE_ARN \
        --handler index.handler \
        --zip-file fileb://function.zip \
        --timeout 10 \
        --memory-size 128 \
        --environment Variables="{DEVICES_TABLE=$DEVICES_TABLE}" \
        --region $REGION \
        > /dev/null
    print_success "Function created"
fi

GET_LAMBDA_ARN=$(aws lambda get-function --function-name motionplay-getDeviceConfig --region $REGION --query 'Configuration.FunctionArn' --output text)
print_success "Lambda ARN: $GET_LAMBDA_ARN"

cd ..

###############################################################################
# Step 2: Deploy updateDeviceConfig Lambda
###############################################################################

print_header "Step 2: Deploying updateDeviceConfig Lambda"

cd updateDeviceConfig

print_status "Installing dependencies..."
npm install --silent
print_success "Dependencies installed"

print_status "Creating deployment package..."
if [ -f function.zip ]; then
    rm function.zip
fi
zip -q -r function.zip index.js node_modules/
print_success "Deployment package created: $(du -h function.zip | cut -f1)"

# Check if Lambda function exists
print_status "Checking if Lambda function exists..."
if aws lambda get-function --function-name motionplay-updateDeviceConfig --region $REGION &> /dev/null; then
    print_status "Function exists. Updating code..."
    aws lambda update-function-code \
        --function-name motionplay-updateDeviceConfig \
        --zip-file fileb://function.zip \
        --region $REGION \
        > /dev/null
    print_success "Function code updated"
else
    print_status "Function doesn't exist. Creating..."
    aws lambda create-function \
        --function-name motionplay-updateDeviceConfig \
        --runtime nodejs18.x \
        --role $LAMBDA_ROLE_ARN \
        --handler index.handler \
        --zip-file fileb://function.zip \
        --timeout 15 \
        --memory-size 256 \
        --environment Variables="{DEVICES_TABLE=$DEVICES_TABLE}" \
        --region $REGION \
        > /dev/null
    print_success "Function created"
fi

PUT_LAMBDA_ARN=$(aws lambda get-function --function-name motionplay-updateDeviceConfig --region $REGION --query 'Configuration.FunctionArn' --output text)
print_success "Lambda ARN: $PUT_LAMBDA_ARN"

cd ..

###############################################################################
# Step 3: Configure API Gateway
###############################################################################

print_header "Step 3: Configuring API Gateway"

# Get API ID
print_status "Finding API Gateway..."
API_ID=$(aws apigateway get-rest-apis --region $REGION --query "items[?name=='$API_NAME'].id" --output text)
if [ -z "$API_ID" ]; then
    print_error "API Gateway '$API_NAME' not found."
    exit 1
fi
print_success "API ID: $API_ID"

# Get root resource
ROOT_ID=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query "items[?path=='/'].id" --output text)
print_success "Root resource ID: $ROOT_ID"

# Check if /device resource exists, create if not
print_status "Checking for /device resource..."
DEVICE_RESOURCE=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query "items[?pathPart=='device'].id" --output text)
if [ -z "$DEVICE_RESOURCE" ]; then
    print_status "Creating /device resource..."
    DEVICE_RESOURCE=$(aws apigateway create-resource \
        --rest-api-id $API_ID \
        --parent-id $ROOT_ID \
        --path-part device \
        --region $REGION \
        --query 'id' --output text)
    print_success "Created /device resource"
else
    print_success "Found existing /device resource"
fi

# Check if /device/{device_id} resource exists, create if not
print_status "Checking for /device/{device_id} resource..."
DEVICE_ID_RESOURCE=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query "items[?pathPart=='{device_id}' && parentId=='$DEVICE_RESOURCE'].id" --output text)
if [ -z "$DEVICE_ID_RESOURCE" ]; then
    print_status "Creating /device/{device_id} resource..."
    DEVICE_ID_RESOURCE=$(aws apigateway create-resource \
        --rest-api-id $API_ID \
        --parent-id $DEVICE_RESOURCE \
        --path-part '{device_id}' \
        --region $REGION \
        --query 'id' --output text)
    print_success "Created /device/{device_id} resource"
else
    print_success "Found existing /device/{device_id} resource"
fi

# Check if /device/{device_id}/config resource exists, create if not
print_status "Checking for /device/{device_id}/config resource..."
CONFIG_RESOURCE=$(aws apigateway get-resources --rest-api-id $API_ID --region $REGION --query "items[?pathPart=='config' && parentId=='$DEVICE_ID_RESOURCE'].id" --output text)
if [ -z "$CONFIG_RESOURCE" ]; then
    print_status "Creating /device/{device_id}/config resource..."
    CONFIG_RESOURCE=$(aws apigateway create-resource \
        --rest-api-id $API_ID \
        --parent-id $DEVICE_ID_RESOURCE \
        --path-part config \
        --region $REGION \
        --query 'id' --output text)
    print_success "Created /device/{device_id}/config resource"
else
    print_success "Found existing /device/{device_id}/config resource"
fi

###############################################################################
# Step 4: Configure GET Method
###############################################################################

print_header "Step 4: Configuring GET Method"

# Check if GET method exists
if aws apigateway get-method --rest-api-id $API_ID --resource-id $CONFIG_RESOURCE --http-method GET --region $REGION &> /dev/null; then
    print_warning "GET method already exists. Deleting and recreating..."
    aws apigateway delete-method --rest-api-id $API_ID --resource-id $CONFIG_RESOURCE --http-method GET --region $REGION &> /dev/null
fi

print_status "Creating GET method..."
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $CONFIG_RESOURCE \
    --http-method GET \
    --authorization-type NONE \
    --region $REGION \
    > /dev/null
print_success "GET method created"

print_status "Configuring Lambda integration..."
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $CONFIG_RESOURCE \
    --http-method GET \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${GET_LAMBDA_ARN}/invocations" \
    --region $REGION \
    > /dev/null
print_success "Lambda integration configured"

print_status "Granting API Gateway permission to invoke Lambda..."
aws lambda add-permission \
    --function-name motionplay-getDeviceConfig \
    --statement-id apigateway-get-config-$(date +%s) \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/GET/device/{device_id}/config" \
    --region $REGION \
    > /dev/null 2>&1 || print_warning "Permission may already exist"
print_success "Permission granted"

###############################################################################
# Step 5: Configure PUT Method
###############################################################################

print_header "Step 5: Configuring PUT Method"

# Check if PUT method exists
if aws apigateway get-method --rest-api-id $API_ID --resource-id $CONFIG_RESOURCE --http-method PUT --region $REGION &> /dev/null; then
    print_warning "PUT method already exists. Deleting and recreating..."
    aws apigateway delete-method --rest-api-id $API_ID --resource-id $CONFIG_RESOURCE --http-method PUT --region $REGION &> /dev/null
fi

print_status "Creating PUT method..."
aws apigateway put-method \
    --rest-api-id $API_ID \
    --resource-id $CONFIG_RESOURCE \
    --http-method PUT \
    --authorization-type NONE \
    --region $REGION \
    > /dev/null
print_success "PUT method created"

print_status "Configuring Lambda integration..."
aws apigateway put-integration \
    --rest-api-id $API_ID \
    --resource-id $CONFIG_RESOURCE \
    --http-method PUT \
    --type AWS_PROXY \
    --integration-http-method POST \
    --uri "arn:aws:apigateway:${REGION}:lambda:path/2015-03-31/functions/${PUT_LAMBDA_ARN}/invocations" \
    --region $REGION \
    > /dev/null
print_success "Lambda integration configured"

print_status "Granting API Gateway permission to invoke Lambda..."
aws lambda add-permission \
    --function-name motionplay-updateDeviceConfig \
    --statement-id apigateway-update-config-$(date +%s) \
    --action lambda:InvokeFunction \
    --principal apigateway.amazonaws.com \
    --source-arn "arn:aws:execute-api:${REGION}:${ACCOUNT_ID}:${API_ID}/*/PUT/device/{device_id}/config" \
    --region $REGION \
    > /dev/null 2>&1 || print_warning "Permission may already exist"
print_success "Permission granted"

###############################################################################
# Step 6: Enable CORS
###############################################################################

print_header "Step 6: Enabling CORS"

# Configure OPTIONS method for CORS (if doesn't exist)
if ! aws apigateway get-method --rest-api-id $API_ID --resource-id $CONFIG_RESOURCE --http-method OPTIONS --region $REGION &> /dev/null; then
    print_status "Creating OPTIONS method for CORS..."
    
    aws apigateway put-method \
        --rest-api-id $API_ID \
        --resource-id $CONFIG_RESOURCE \
        --http-method OPTIONS \
        --authorization-type NONE \
        --region $REGION \
        > /dev/null
    
    aws apigateway put-integration \
        --rest-api-id $API_ID \
        --resource-id $CONFIG_RESOURCE \
        --http-method OPTIONS \
        --type MOCK \
        --request-templates '{"application/json": "{\"statusCode\": 200}"}' \
        --region $REGION \
        > /dev/null
    
    aws apigateway put-method-response \
        --rest-api-id $API_ID \
        --resource-id $CONFIG_RESOURCE \
        --http-method OPTIONS \
        --status-code 200 \
        --response-parameters '{"method.response.header.Access-Control-Allow-Headers":false,"method.response.header.Access-Control-Allow-Methods":false,"method.response.header.Access-Control-Allow-Origin":false}' \
        --region $REGION \
        > /dev/null
    
    aws apigateway put-integration-response \
        --rest-api-id $API_ID \
        --resource-id $CONFIG_RESOURCE \
        --http-method OPTIONS \
        --status-code 200 \
        --response-parameters '{"method.response.header.Access-Control-Allow-Headers":"'"'"'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token'"'"'","method.response.header.Access-Control-Allow-Methods":"'"'"'GET,PUT,OPTIONS'"'"'","method.response.header.Access-Control-Allow-Origin":"'"'"'*'"'"'"}' \
        --region $REGION \
        > /dev/null
    
    print_success "CORS configured"
else
    print_success "CORS already configured"
fi

###############################################################################
# Step 7: Deploy API
###############################################################################

print_header "Step 7: Deploying API"

print_status "Creating deployment..."
aws apigateway create-deployment \
    --rest-api-id $API_ID \
    --stage-name prod \
    --description "Added device config endpoints" \
    --region $REGION \
    > /dev/null
print_success "API deployed to prod stage"

API_ENDPOINT="https://${API_ID}.execute-api.${REGION}.amazonaws.com/prod"
print_success "API Endpoint: $API_ENDPOINT"

###############################################################################
# Step 8: Test Endpoints
###############################################################################

print_header "Step 8: Testing Endpoints"

print_status "Waiting 3 seconds for deployment to propagate..."
sleep 3

# Test GET endpoint
print_status "Testing GET /device/motionplay-device-001/config..."
GET_RESPONSE=$(curl -s -w "\n%{http_code}" "${API_ENDPOINT}/device/motionplay-device-001/config")
GET_STATUS=$(echo "$GET_RESPONSE" | tail -n 1)
GET_BODY=$(echo "$GET_RESPONSE" | sed '$d')

if [ "$GET_STATUS" = "200" ]; then
    print_success "GET endpoint working! Response:"
    echo "$GET_BODY" | python3 -m json.tool 2>/dev/null || echo "$GET_BODY"
else
    print_error "GET endpoint returned status $GET_STATUS"
    echo "$GET_BODY"
fi

echo ""

# Test PUT endpoint
print_status "Testing PUT /device/motionplay-device-001/config..."
PUT_PAYLOAD='{"sensor_config":{"sample_rate_hz":500,"led_current":"100mA","integration_time":"2T","high_resolution":true,"read_ambient":false,"i2c_clock_khz":400}}'
PUT_RESPONSE=$(curl -s -w "\n%{http_code}" -X PUT \
    -H "Content-Type: application/json" \
    -d "$PUT_PAYLOAD" \
    "${API_ENDPOINT}/device/motionplay-device-001/config")
PUT_STATUS=$(echo "$PUT_RESPONSE" | tail -n 1)
PUT_BODY=$(echo "$PUT_RESPONSE" | sed '$d')

if [ "$PUT_STATUS" = "200" ]; then
    print_success "PUT endpoint working! Response:"
    echo "$PUT_BODY" | python3 -m json.tool 2>/dev/null || echo "$PUT_BODY"
else
    print_error "PUT endpoint returned status $PUT_STATUS"
    echo "$PUT_BODY"
fi

###############################################################################
# Summary
###############################################################################

print_header "Deployment Complete!"

echo ""
echo -e "${GREEN}✓ Lambda Functions Deployed${NC}"
echo "  • motionplay-getDeviceConfig"
echo "  • motionplay-updateDeviceConfig"
echo ""
echo -e "${GREEN}✓ API Gateway Configured${NC}"
echo "  • GET  /device/{device_id}/config"
echo "  • PUT  /device/{device_id}/config"
echo ""
echo -e "${BLUE}API Endpoint:${NC}"
echo "  $API_ENDPOINT"
echo ""
echo -e "${BLUE}Test Commands:${NC}"
echo ""
echo "# Get device config:"
echo "curl ${API_ENDPOINT}/device/motionplay-device-001/config"
echo ""
echo "# Update device config:"
echo "curl -X PUT \\"
echo "  ${API_ENDPOINT}/device/motionplay-device-001/config \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"sensor_config\":{\"sample_rate_hz\":1000,\"led_current\":\"200mA\",\"integration_time\":\"2T\",\"duty_cycle\":\"1/40\",\"high_resolution\":true,\"read_ambient\":true,\"i2c_clock_khz\":400}}'"
echo ""
echo -e "${BLUE}Next Steps:${NC}"
echo "  1. Update frontend to use these endpoints"
echo "  2. Update firmware to fetch config on boot"
echo "  3. Test end-to-end config sync"
echo ""


#!/bin/bash
#
# Motion Play — New Device Provisioning
#
# Automates the full setup for a new ESP32-S3 device:
#   1. Creates an AWS IoT Thing
#   2. Generates and attaches certificates
#   3. Attaches the IoT policy
#   4. Downloads the Root CA (if needed)
#   5. Generates config.json with WiFi + MQTT settings
#   6. Backs up secrets to AWS Secrets Manager
#   7. Uploads filesystem (LittleFS) and firmware to the device
#
# Usage:
#   ./scripts/provision-device.sh
#
# Prerequisites:
#   - AWS CLI configured (aws configure)
#   - PlatformIO CLI installed (pio)
#   - Device connected via USB (for the flash step)

set -e

# ──────────────────────────────────────────────
# Configuration
# ──────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
DATA_DIR="${PROJECT_ROOT}/firmware/data"
CERTS_DIR="${DATA_DIR}/certs"
IOT_POLICY_NAME="MotionPlayDevicePolicy"
AWS_REGION="${AWS_REGION:-us-west-2}"

# ──────────────────────────────────────────────
# Helper functions
# ──────────────────────────────────────────────

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

step() {
    echo ""
    echo -e "${CYAN}${BOLD}[$1/$TOTAL_STEPS]${NC} $2"
}

success() {
    echo -e "    ${GREEN}✓${NC} $1"
}

warn() {
    echo -e "    ${YELLOW}⚠${NC} $1"
}

fail() {
    echo -e "    ${RED}✗${NC} $1"
    exit 1
}

prompt() {
    local var_name="$1"
    local prompt_text="$2"
    local default="$3"
    local is_secret="$4"

    if [ -n "$default" ]; then
        prompt_text="${prompt_text} [${default}]"
    fi

    if [ "$is_secret" = "true" ]; then
        echo -n -e "${BOLD}${prompt_text}: ${NC}"
        read -s "$var_name"
        echo "" # newline after hidden input
    else
        echo -n -e "${BOLD}${prompt_text}: ${NC}"
        read "$var_name"
    fi

    # Apply default if empty
    if [ -z "${!var_name}" ] && [ -n "$default" ]; then
        eval "$var_name='$default'"
    fi
}

# ──────────────────────────────────────────────
# Pre-flight checks
# ──────────────────────────────────────────────

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════${NC}"
echo -e "${BOLD}   Motion Play — Device Provisioning${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════${NC}"
echo ""

# Check AWS CLI
if ! command -v aws &> /dev/null; then
    fail "AWS CLI not found. Install it: https://aws.amazon.com/cli/"
fi

# Check PlatformIO
if ! command -v pio &> /dev/null; then
    fail "PlatformIO CLI not found. Install it: https://platformio.org/install/cli"
fi

# Verify AWS credentials
echo -e "${CYAN}Checking AWS credentials...${NC}"
AWS_ACCOUNT_ID=$(aws sts get-caller-identity --query Account --output text 2>/dev/null) || \
    fail "AWS credentials not configured. Run: aws configure"
success "AWS account: ${AWS_ACCOUNT_ID} (region: ${AWS_REGION})"

# ──────────────────────────────────────────────
# Gather input
# ──────────────────────────────────────────────

echo ""
echo -e "${BOLD}Device Configuration${NC}"
echo -e "─────────────────────────────────────────────"

prompt DEVICE_NUM "Device number (e.g. 002)"
if [ -z "$DEVICE_NUM" ]; then
    fail "Device number is required"
fi

DEVICE_ID="motionplay-device-${DEVICE_NUM}"
THING_NAME="${DEVICE_ID}"

echo ""
echo -e "  Device ID:   ${BOLD}${DEVICE_ID}${NC}"
echo -e "  Thing name:  ${BOLD}${THING_NAME}${NC}"
echo ""

prompt WIFI_SSID "WiFi SSID"
if [ -z "$WIFI_SSID" ]; then
    fail "WiFi SSID is required"
fi

prompt WIFI_PASSWORD "WiFi Password" "" "true"
if [ -z "$WIFI_PASSWORD" ]; then
    fail "WiFi Password is required"
fi

# Optional: API endpoint
prompt API_ENDPOINT "API Gateway endpoint (leave blank to skip)"

echo ""
echo -e "${BOLD}Ready to provision ${DEVICE_ID}${NC}"
echo -e "─────────────────────────────────────────────"
prompt CONFIRM "Continue? (y/N)" "N"
if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
    echo "Aborted."
    exit 0
fi

TOTAL_STEPS=7

# ──────────────────────────────────────────────
# Step 1: Create IoT Thing
# ──────────────────────────────────────────────

step 1 "Creating IoT Thing: ${THING_NAME}"

# Check if thing already exists
if aws iot describe-thing --thing-name "${THING_NAME}" --region "${AWS_REGION}" &> /dev/null; then
    warn "Thing '${THING_NAME}' already exists — skipping creation"
else
    aws iot create-thing \
        --thing-name "${THING_NAME}" \
        --region "${AWS_REGION}" > /dev/null
    success "Created IoT Thing: ${THING_NAME}"
fi

# ──────────────────────────────────────────────
# Step 2: Generate certificates
# ──────────────────────────────────────────────

step 2 "Generating device certificates"

mkdir -p "${CERTS_DIR}"

CERT_OUTPUT=$(aws iot create-keys-and-certificate \
    --set-as-active \
    --certificate-pem-outfile "${CERTS_DIR}/device-cert.pem" \
    --public-key-outfile "/tmp/motionplay-${DEVICE_NUM}-public-key.pem" \
    --private-key-outfile "${CERTS_DIR}/private-key.pem" \
    --region "${AWS_REGION}")

CERT_ARN=$(echo "$CERT_OUTPUT" | python3 -c "import sys,json; print(json.load(sys.stdin)['certificateArn'])")

success "Certificate ARN: ${CERT_ARN}"
success "Certs written to ${CERTS_DIR}/"

# Clean up public key (not needed on device)
rm -f "/tmp/motionplay-${DEVICE_NUM}-public-key.pem"

# ──────────────────────────────────────────────
# Step 3: Attach certificate to thing + policy
# ──────────────────────────────────────────────

step 3 "Attaching certificate to Thing and IoT Policy"

aws iot attach-thing-principal \
    --thing-name "${THING_NAME}" \
    --principal "${CERT_ARN}" \
    --region "${AWS_REGION}"
success "Certificate attached to thing: ${THING_NAME}"

# Check that the policy exists
if ! aws iot get-policy --policy-name "${IOT_POLICY_NAME}" --region "${AWS_REGION}" &> /dev/null; then
    fail "IoT policy '${IOT_POLICY_NAME}' not found. Create it first (see infrastructure/aws-setup-guide.md Step 5)"
fi

aws iot attach-policy \
    --policy-name "${IOT_POLICY_NAME}" \
    --target "${CERT_ARN}" \
    --region "${AWS_REGION}"
success "Policy '${IOT_POLICY_NAME}' attached to certificate"

# ──────────────────────────────────────────────
# Step 4: Download Root CA (if not present)
# ──────────────────────────────────────────────

step 4 "Ensuring Root CA certificate is present"

if [ -f "${CERTS_DIR}/root-ca.pem" ]; then
    warn "root-ca.pem already exists — keeping existing file"
else
    curl -s -o "${CERTS_DIR}/root-ca.pem" \
        https://www.amazontrust.com/repository/AmazonRootCA1.pem
    success "Downloaded Amazon Root CA to ${CERTS_DIR}/root-ca.pem"
fi

# ──────────────────────────────────────────────
# Step 5: Generate config.json
# ──────────────────────────────────────────────

step 5 "Generating config.json"

IOT_ENDPOINT=$(aws iot describe-endpoint \
    --endpoint-type iot:Data-ATS \
    --region "${AWS_REGION}" \
    --query "endpointAddress" \
    --output text)

success "IoT endpoint: ${IOT_ENDPOINT}"

# Build config JSON
API_BLOCK=""
if [ -n "$API_ENDPOINT" ]; then
    API_BLOCK=$(cat <<APIEOF
,
  "api": {
    "endpoint": "${API_ENDPOINT}"
  }
APIEOF
)
fi

cat > "${DATA_DIR}/config.json" <<CONFIGEOF
{
  "device_id": "${DEVICE_ID}",
  "wifi": {
    "ssid": "${WIFI_SSID}",
    "password": "${WIFI_PASSWORD}"
  },
  "mqtt": {
    "broker": "${IOT_ENDPOINT}",
    "port": 8883,
    "client_id": "${DEVICE_ID}"
  }${API_BLOCK},
  "sampling": {
    "rate_hz": 1000,
    "max_duration_seconds": 30
  }
}
CONFIGEOF

success "Config written to ${DATA_DIR}/config.json"

# ──────────────────────────────────────────────
# Step 6: Back up secrets to AWS Secrets Manager
# ──────────────────────────────────────────────

step 6 "Backing up secrets to AWS Secrets Manager"

"${SCRIPT_DIR}/sync-secrets.sh" up "${DEVICE_NUM}"
success "Secrets backed up under prefix: motion-play/device-${DEVICE_NUM}"

# ──────────────────────────────────────────────
# Step 7: Flash device
# ──────────────────────────────────────────────

step 7 "Flashing device"

echo ""
echo -e "    ${YELLOW}Connect the device via USB now.${NC}"
echo -e "    Make sure DWEII power (Cable A) is ${BOLD}disconnected${NC}."
echo -e "    Connect Cable B (MacBook) ${BOLD}directly${NC} to T-Display USB-C."
echo ""
prompt FLASH_CONFIRM "Ready to flash? (y/N)" "N"

if [[ ! "$FLASH_CONFIRM" =~ ^[Yy]$ ]]; then
    echo ""
    echo -e "${YELLOW}Skipping flash. You can flash manually later:${NC}"
    echo "  cd ${PROJECT_ROOT}"
    echo "  pio run --target uploadfs    # Upload filesystem (config + certs)"
    echo "  pio run --target upload       # Upload firmware"
    echo ""
else
    echo ""
    echo -e "    Uploading filesystem (LittleFS)..."
    (cd "${PROJECT_ROOT}" && pio run --target uploadfs) || fail "Filesystem upload failed"
    success "Filesystem uploaded"

    echo ""
    echo -e "    Uploading firmware..."
    (cd "${PROJECT_ROOT}" && pio run --target upload) || fail "Firmware upload failed"
    success "Firmware uploaded"
fi

# ──────────────────────────────────────────────
# Done
# ──────────────────────────────────────────────

echo ""
echo -e "${BOLD}═══════════════════════════════════════════════${NC}"
echo -e "${GREEN}${BOLD}   Device ${DEVICE_ID} provisioned!${NC}"
echo -e "${BOLD}═══════════════════════════════════════════════${NC}"
echo ""
echo -e "  Thing:    ${THING_NAME}"
echo -e "  Cert:     ${CERT_ARN}"
echo -e "  Secrets:  motion-play/device-${DEVICE_NUM}/*"
echo ""
echo -e "  ${BOLD}Next steps:${NC}"
echo -e "  1. Power on with DWEII module (Cable A)"
echo -e "  2. Attach Cable B with data-only adapter for serial monitoring"
echo -e "  3. Verify in AWS IoT Core console that device connects"
echo ""
echo -e "  To re-download this device's secrets later:"
echo -e "    ./scripts/sync-secrets.sh down ${DEVICE_NUM}"
echo ""

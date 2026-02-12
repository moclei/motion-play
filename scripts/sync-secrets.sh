#!/bin/bash
# Sync secrets from AWS Secrets Manager to the local environment
#
# Usage:
#   ./scripts/sync-secrets.sh up [device-number]
#   ./scripts/sync-secrets.sh down [device-number]
#
# Examples:
#   ./scripts/sync-secrets.sh up          # Syncs device-001 (default)
#   ./scripts/sync-secrets.sh up 002      # Syncs device-002
#   ./scripts/sync-secrets.sh down 003    # Downloads device-003 secrets

set -e

DEVICE_NUM="${2:-001}"
DEVICE_ID="device-${DEVICE_NUM}"
SECRETS_PREFIX="motion-play/${DEVICE_ID}"
DATA_DIR="firmware/data"

echo "Device: motionplay-${DEVICE_ID} (secrets prefix: ${SECRETS_PREFIX})"

sync_up() {
    echo "Syncing secrets up to AWS Secrets Manager..."

    # Upload config.json to AWS Secrets Manager
    aws secretsmanager create-secret \
        --name "${SECRETS_PREFIX}/config" \
        --secret-string file://${DATA_DIR}/config.json 2>/dev/null || \
    aws secretsmanager update-secret \
        --secret-id "${SECRETS_PREFIX}/config" \
        --secret-string file://${DATA_DIR}/config.json

    # Upload certificates to AWS Secrets Manager
    for cert in device-cert.pem private-key.pem root-ca.pem; do
        aws secretsmanager create-secret \
            --name "${SECRETS_PREFIX}/certs/${cert}" \
            --secret-binary fileb://${DATA_DIR}/certs/${cert} 2>/dev/null || \
        aws secretsmanager update-secret \
            --secret-id "${SECRETS_PREFIX}/certs/${cert}" \
            --secret-binary fileb://${DATA_DIR}/certs/${cert}
    done

    echo "Secrets uploaded successfully."
}

sync_down() {
    echo "Syncing secrets down from AWS Secrets Manager..."

    mkdir -p "${DATA_DIR}/certs"

    # Download config.json from AWS Secrets Manager
    aws secretsmanager get-secret-value \
        --secret-id "${SECRETS_PREFIX}/config" \
        --query SecretString \
        --output text > "${DATA_DIR}/config.json"

    # Download certificates from AWS Secrets Manager
    for cert in device-cert.pem private-key.pem root-ca.pem; do
        aws secretsmanager get-secret-value \
            --secret-id "${SECRETS_PREFIX}/certs/${cert}" \
            --query SecretBinary \
            --output text | base64 -d > "${DATA_DIR}/certs/${cert}"
    done

    echo "Secrets downloaded successfully."
}

case "$1" in
    up|push)
        sync_up
        ;;
    down|pull)
        sync_down
        ;;
    *)
        echo "Usage: $0 {up|push|down|pull} [device-number]"
        echo ""
        echo "  up/push:   Upload secrets to AWS Secrets Manager"
        echo "  down/pull: Download secrets from AWS Secrets Manager"
        echo ""
        echo "  device-number: e.g. 001, 002, 003 (default: 001)"
        echo ""
        echo "Examples:"
        echo "  $0 up          # Sync device-001 secrets up"
        echo "  $0 down 002    # Download device-002 secrets"
        exit 1
esac

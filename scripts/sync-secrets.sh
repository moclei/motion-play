#!/bin/bash
# Sync secrets from AWS Secrets Manager to the local environment

set -e

SECRETS_PREFIX="motion-play/device-001"
DATA_DIR="firmware/data"

sync_up() {
    echo "Syncing secrets up to AWS Secrets Manager..."

    #upload config.json to AWS Secrets Manager
    aws secretsmanager create-secret \
        --name ${SECRETS_PREFIX}/config \
        --secret-string file://$DATA_DIR/config.json 2>/dev/null || \
    aws secretsmanager update-secret \
        --secret-id ${SECRETS_PREFIX}/config \
        --secret-string file://$DATA_DIR/config.json

    # Upload certificates to AWS Secrets Manager
    for cert in device-cert.pem private-key.pem root-ca.pem; do
        aws secretsmanager create-secret \
            --name ${SECRETS_PREFIX}/certs/${cert} \
            --secret-binary fileb://${DATA_DIR}/certs/${cert} 2>/dev/null || \
        aws secretsmanager update-secret \
            --secret-id ${SECRETS_PREFIX}/certs/${cert} \
            --secret-binary fileb://${DATA_DIR}/certs/${cert}
    done

    echo "Secrets uploaded successfully."
}

sync_down() {
    echo "Syncing secrets down from AWS Secrets Manager..."

    mkdir -p ${DATA_DIR}/certs

    # Download config.json from AWS Secrets Manager
    aws secretsmanager get-secret-value \
        --secret-id ${SECRETS_PREFIX}/config \
        --query SecretString \
        --output text > ${DATA_DIR}/config.json

    # Download certificates from AWS Secrets Manager
    for cert in device-cert.pem private-key.pem root-ca.pem; do
        aws secretsmanager get-secret-value \
            --secret-id ${SECRETS_PREFIX}/certs/${cert} \
            --query SecretBinary \
            --output text | base64 -d > ${DATA_DIR}/certs/${cert}
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
        echo "Usage: $0 {up|push|down|pull}"
        echo "  up/push: Upload secrets to AWS Secrets Manager"
        echo "  down/pull: Download secrets from AWS Secrets Manager"
        exit 1
esac
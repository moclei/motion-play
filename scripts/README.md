# Scripts

Utility scripts for the Motion Play project. Run all scripts from the project root.

## Device Provisioning

### `provision-device.sh`

Automates the full setup process for a new ESP32-S3 device. Walks you through each step interactively.

```bash
./scripts/provision-device.sh
```

**What it does:**
1. Creates an AWS IoT Thing for the device
2. Generates and activates X.509 certificates
3. Attaches the certificate to the Thing and the `MotionPlayDevicePolicy`
4. Downloads the Amazon Root CA (if not already present)
5. Fetches the IoT endpoint and generates `config.json` with your WiFi credentials
6. Backs up all secrets to AWS Secrets Manager
7. Uploads the filesystem (LittleFS) and firmware to the device

**Prerequisites:**
- AWS CLI configured (`aws configure`)
- PlatformIO CLI installed (`pio`)
- Device connected via USB for the flash step (DWEII power disconnected)

### `sync-secrets.sh`

Syncs device config and certificates to/from AWS Secrets Manager. Useful for backing up a new device's secrets or restoring them on a different machine.

```bash
./scripts/sync-secrets.sh up [device-number]     # Upload to Secrets Manager
./scripts/sync-secrets.sh down [device-number]    # Download from Secrets Manager
```

**Examples:**
```bash
./scripts/sync-secrets.sh up           # Back up device-001 (default)
./scripts/sync-secrets.sh up 002       # Back up device-002
./scripts/sync-secrets.sh down 002     # Restore device-002 secrets locally
```

Secrets are stored under the prefix `motion-play/device-{number}/` in AWS Secrets Manager.

## Monitoring & Debugging

### `monitor-mqtt.sh` / `monitor-mqtt.py`

Monitor MQTT messages to/from a device in real time. Useful for verifying device connectivity and inspecting data payloads.

### `add-iot-error-logging.sh`

Adds error logging rules to AWS IoT Core for debugging connection or message delivery issues.

## Data Analysis

### `analyze_session.py` / `analyze-session-data.sh`

Tools for analyzing sensor data from completed collection sessions. Used during development to inspect data quality and sensor behavior.

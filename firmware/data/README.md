# Firmware Data Directory

This directory contains configuration files and certificates for the ESP32-S3 device. These files are uploaded to the device's LittleFS filesystem partition and read by the firmware at runtime.

## Files

### Certificates (Not Committed)

AWS IoT Core certificates for TLS authentication:
- `certs/device-cert.pem` - Device certificate
- `certs/private-key.pem` - Private key
- `certs/root-ca.pem` - Amazon Root CA

### Configuration

- `config.json` - Device configuration (not committed, copy from `config.json.example`)
- `config.json.example` - Template showing the expected structure

## Setup — New Device

**Recommended:** Use the provisioning script, which handles everything automatically (AWS IoT Thing creation, certificates, config, filesystem upload, and firmware upload):

```bash
./scripts/provision-device.sh
```

See [`scripts/README.md`](../../scripts/README.md) for details.

### Manual Setup

If you prefer to set things up manually:

1. Copy `config.json.example` to `config.json`
2. Update `config.json` with your WiFi credentials, device ID, and AWS IoT endpoint
3. Place your AWS IoT certificates in the `certs/` directory
4. Upload filesystem to ESP32 using PlatformIO:
   ```bash
   pio run --target uploadfs
   ```
5. Upload firmware:
   ```bash
   pio run --target upload
   ```

## Restoring Secrets

If you need to restore a device's config and certs from AWS Secrets Manager:

```bash
./scripts/sync-secrets.sh down 002   # Downloads device-002's secrets
```

## Security Note

**NEVER commit certificate files or actual config.json to git!**
These files contain sensitive credentials and are automatically ignored by `.gitignore`.


# Firmware Data Directory

This directory contains configuration files and certificates for the ESP32-S3 device.

## Files

### Certificates (Not Committed)

Place your AWS IoT Core certificates here:
- `certs/device-cert.pem` - Device certificate
- `certs/private-key.pem` - Private key
- `certs/root-ca.pem` - Amazon Root CA

### Configuration

- `config.json` - Device configuration (not committed, copy from `config.json.example`)
- `config.json.example` - Template configuration file

## Setup Instructions

1. Copy `config.json.example` to `config.json`
2. Update `config.json` with your WiFi credentials and AWS IoT endpoint
3. Place your AWS IoT certificates in the `certs/` directory
4. Upload filesystem to ESP32 using PlatformIO:
   ```bash
   pio run --target uploadfs
   ```

## Security Note

**NEVER commit certificate files or actual config.json to git!**
These files contain sensitive credentials and are automatically ignored by `.gitignore`.


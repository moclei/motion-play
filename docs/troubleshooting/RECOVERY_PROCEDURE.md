# Device Recovery Procedure

## When Device is Hung/Stuck

### Symptoms:
- Display stuck on a message (e.g., "Configuring sensors...")
- Not responding to web UI commands
- Upload fails with "chip stopped responding"

### Recovery Steps:

#### 1. Power Cycle the Device
```bash
# Disconnect power completely:
# - Unplug DWEII USB-C power cable
# - Unplug programming cable from T-Display
# - Wait 5 seconds
# - Reconnect DWEII power first
# - Then reconnect programming cable (with data-only adapter for monitoring)
```

#### 2. For Upload (if needed):
```bash
# Remove data-only adapter from programming cable
# Connect programming cable directly to T-Display
# Disconnect DWEII power cable
# Upload new firmware:
cd /Users/marcocleirigh/Workspace/motion-play
pio run --target upload

# After upload completes, device will reboot automatically
```

#### 3. Monitor Serial Output:
```bash
pio device monitor
```

#### 4. Check for Success Indicators:
- Device boots normally
- Memory statistics displayed
- "PSRAM OK" message
- No error messages

### If Device Won't Enter Upload Mode:

1. **Hold BOOT button** (GPIO 0) on T-Display
2. **Press and release RESET** button while holding BOOT
3. **Release BOOT button** after ~1 second
4. **Run upload command**:
   ```bash
   pio run --target upload
   ```

### Emergency: Complete Reset

If the device is completely unresponsive:

```bash
# Erase flash completely
esptool.py --port /dev/cu.usbmodem* erase_flash

# Then upload firmware again
pio run --target upload
```

**Warning**: This will erase all certificates and configuration!

---

## Prevention Tips

1. **Always monitor serial output** during configuration changes
2. **Don't send multiple configuration commands** rapidly
3. **Wait for "successfully" messages** before next command
4. **Keep backup of certificates** in `firmware/data/certs/`

---

*Last Updated: November 26, 2025*


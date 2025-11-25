# Power Management Quick Reference

## Cable Setup
- **Cable A**: USB-C to wall power → DWEII module (Main power)
- **Cable B**: USB-C to MacBook → T-Display (Programming/Serial monitor)
- **Adapter**: USB-C data-only (power pins disabled)

## Quick Workflows

### Upload Code
```
1. DWEII: Disconnected
2. Cable B: Direct to T-Display (no adapter)
3. Upload via PlatformIO
4. Device reboots automatically
```

### Test/Monitor
```
1. Cable B: Remove from T-Display
2. Cable B: Add data-only adapter
3. Cable B: Reconnect to T-Display
4. DWEII: Connect to wall power
5. Open serial monitor
```

### Re-upload
```
1. DWEII: Disconnect
2. Cable B: Remove adapter
3. Cable B: Reconnect directly
4. Upload new code
5. Repeat test steps
```

## Safety Checklist for LED Testing

- [ ] DWEII module connected before LED initialization
- [ ] Code includes startup delay (5+ seconds recommended)
- [ ] Data-only adapter installed for monitoring
- [ ] Verify LED strip connector is properly seated
- [ ] Check that power indicator on main PCB is lit

## Power Source Identification

| Scenario | T-Display Powered | Main PCB Components | LED Strip | Power Source |
|----------|------------------|-------------------|-----------|--------------|
| Upload | ✅ Yes | 🟡 Partially* | ❌ No | USB via T-Display |
| Testing | ✅ Yes | ✅ Yes | ✅ Yes | DWEII module |
| Ideal** | ✅ Yes | ✅ Yes | ✅ Yes | Both (isolated) |

*Via 5V back-feed through T-Display pin 12 - insufficient for proper operation  
**Not yet reliable - investigating

## Troubleshooting

### LEDs not lighting
- Check DWEII power connected
- Verify LED strip connector orientation (Data pin correct)
- Check for brown-out messages in serial monitor
- Ensure brightness not set to 0

### Upload fails
- Remove data-only adapter from Cable B
- Disconnect DWEII power
- Try different USB port on MacBook
- Check T-Display USB-C connection

### Components behaving erratically
- Likely powered by USB back-feed only
- Connect DWEII power immediately
- Avoid running sensor/LED code without proper power

### Serial monitor not connecting
- Verify data-only adapter installed
- Check monitor_speed matches code (115200)
- Try unplugging/replugging Cable B
- Ensure T-Display hasn't crashed (check display)

## Technical Details

**Why components power up with only USB:**
- T-Display 5V pin (pin 12) back-feeds to main PCB +5V rail
- This activates AP2112K voltage regulator
- Creates 3.3V for sensors and logic
- BUT: Current insufficient for LED strip or sustained operation

**Why data-only adapter needed:**
- Without it: MacBook and DWEII both provide 5V
- Potential for voltage differences causing current flow
- Could damage MacBook USB port or DWEII module
- Adapter isolates power while allowing serial communication

**Future improvement options:**
1. Add Schottky diode in 5V path from T-Display (prevents back-feed)
2. Add MOSFET switch controlled by GPIO (software power control)
3. Redesign PCB with isolated programming header
4. Move to bare ESP32-S3 with isolated USB programming circuit


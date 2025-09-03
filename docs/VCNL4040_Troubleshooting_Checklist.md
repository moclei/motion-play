# VCNL4040 Sensor Troubleshooting Checklist

**Project:** Motion Play v3  
**Issue:** No I2C devices detected on any TCA9548A channel  
**Date:** _______________  
**Technician:** _______________

---

## 📋 Diagnostic Summary
- ✅ TCA9548A responds at 0x70 (multiplexer working)
- ✅ All 8 channels selectable
- ❌ **Zero devices found on any channel**
- ❌ No VCNL4040 sensors responding

---

## 🔧 Phase 1: Power Supply Verification
**Priority: HIGH** - Most likely cause

### 1.1 Main PCB Power Input
- [ ] **USB-C Power Module Status**
  - [ ] LED indicators ON? ____________
  - [ ] Output voltage: _____ V (expect ~5V)
  - [ ] Current draw: _____ mA

- [ ] **DWEII Power Module Check**
  - [ ] Module LED status: ____________
  - [ ] Input voltage stable: _____ V
  - [ ] Output current capability verified

### 1.2 Voltage Regulator (AMS1117-3.3V)
- [ ] **Input measurements:**
  - [ ] VIN: _____ V (should be ~5V)
  - [ ] GND continuity verified
  
- [ ] **Output measurements:**
  - [ ] VOUT: _____ V (should be 3.3V ±0.1V)
  - [ ] Load test with 100Ω resistor: _____ V
  - [ ] Ripple/noise acceptable

### 1.3 Main PCB 3.3V Distribution
- [ ] **TCA9548A Power:**
  - [ ] VCC pin: _____ V
  - [ ] GND connection verified
  - [ ] Decoupling capacitors present

- [ ] **Sensor PCB connectors (measure all 6):**
  - [ ] Ch0 VCC: _____ V
  - [ ] Ch1 VCC: _____ V  
  - [ ] Ch2 VCC: _____ V
  - [ ] Ch3 VCC: _____ V
  - [ ] Ch4 VCC: _____ V
  - [ ] Ch5 VCC: _____ V

**✋ STOP: If any voltage is wrong, fix power before continuing**

---

## 🔌 Phase 2: I2C Bus Integrity
**Complete only if Phase 1 passes**

### 2.1 Main I2C Bus (T-Display ↔ TCA9548A)
- [ ] **T-Display connections:**
  - [ ] Pin 43 (SDA) to TCA9548A SDA: _____ Ω
  - [ ] Pin 44 (SCL) to TCA9548A SCL: _____ Ω
  - [ ] No shorts to GND or VCC

- [ ] **Pull-up Resistors:**
  - [ ] SDA pull-up resistance: _____ kΩ (expect ~4.7kΩ)
  - [ ] SCL pull-up resistance: _____ kΩ (expect ~4.7kΩ)
  - [ ] Pull-ups to correct voltage (3.3V)

### 2.2 TCA9548A Channel Outputs
**Test each channel that should have sensors**

- [ ] **Channel 0 (if used):**
  - [ ] SDA continuity to connector: _____ Ω
  - [ ] SCL continuity to connector: _____ Ω
  - [ ] No cross-channel shorts

- [ ] **Channel 1 (if used):**
  - [ ] SDA continuity to connector: _____ Ω
  - [ ] SCL continuity to connector: _____ Ω
  - [ ] No cross-channel shorts

- [ ] **Channels 2-5 (if used):**
  - [ ] Ch2: SDA _____ Ω, SCL _____ Ω
  - [ ] Ch3: SDA _____ Ω, SCL _____ Ω  
  - [ ] Ch4: SDA _____ Ω, SCL _____ Ω
  - [ ] Ch5: SDA _____ Ω, SCL _____ Ω

---

## 🔗 Phase 3: Cable & Connector Verification
**Complete only if Phase 2 passes**

### 3.1 Cable Continuity Tests
**Test each sensor cable (main PCB to sensor PCB)**

- [ ] **Sensor Cable 1:**
  - [ ] VCC: _____ Ω (should be <1Ω)
  - [ ] GND: _____ Ω (should be <1Ω)
  - [ ] SDA: _____ Ω (should be <1Ω)
  - [ ] SCL: _____ Ω (should be <1Ω)

- [ ] **Sensor Cable 2:**
  - [ ] VCC: _____ Ω, GND: _____ Ω
  - [ ] SDA: _____ Ω, SCL: _____ Ω

- [ ] **Sensor Cables 3-6 (if connected):**
  - [ ] Cable 3: All connections <1Ω? ______
  - [ ] Cable 4: All connections <1Ω? ______
  - [ ] Cable 5: All connections <1Ω? ______
  - [ ] Cable 6: All connections <1Ω? ______

### 3.2 Connector Integrity
- [ ] **Main PCB connectors:**
  - [ ] All pins making contact
  - [ ] No bent or damaged pins
  - [ ] Proper insertion depth

- [ ] **Sensor PCB connectors:**
  - [ ] Proper seating verified
  - [ ] No mechanical damage
  - [ ] Retention clips engaged

---

## 🔬 Phase 4: Sensor PCB Analysis
**Complete only if Phase 3 passes**

### 4.1 Power Reaching VCNL4040 Chips
**Measure at each sensor PCB**

- [ ] **Sensor PCB 1:**
  - [ ] VCNL4040 VDD pin: _____ V (expect 3.3V)
  - [ ] VCNL4040 GND connection verified
  - [ ] No shorts between power rails

- [ ] **Sensor PCB 2:**
  - [ ] VCNL4040 VDD: _____ V
  - [ ] GND verified: ______

- [ ] **Additional sensor PCBs:**
  - [ ] PCB 3 power: _____ V
  - [ ] PCB 4 power: _____ V
  - [ ] PCB 5 power: _____ V
  - [ ] PCB 6 power: _____ V

### 4.2 VCNL4040 I2C Connections
- [ ] **Sensor PCB 1:**
  - [ ] SDA to VCNL4040 pin: _____ Ω
  - [ ] SCL to VCNL4040 pin: _____ Ω
  - [ ] No shorts to power/ground

- [ ] **Check for cold solder joints:**
  - [ ] VCNL4040 pin soldering looks good
  - [ ] Connector soldering verified
  - [ ] No obvious bridging

### 4.3 Daisy-Chain Power Distribution
**If using daisy-chain power connections**

- [ ] **Power forwarding connections:**
  - [ ] PCB 1 → PCB 2: _____ V
  - [ ] PCB 2 → PCB 3: _____ V
  - [ ] Each link <0.1V drop

---

## 🧪 Phase 5: Isolation Testing
**If systematic issues found**

### 5.1 Single Sensor Test
- [ ] **Disconnect all but one sensor PCB**
  - [ ] Selected sensor PCB: ______
  - [ ] Connected to channel: ______

- [ ] **Test with shortest possible cable**
  - [ ] Cable length: _____ cm
  - [ ] Direct connection (no daisy-chain)

- [ ] **Re-run diagnostic code:**
  - [ ] Device detected? ______
  - [ ] I2C address found: ______
  - [ ] Device ID response: ______

### 5.2 Known Good Component Test
- [ ] **If available, test with:**
  - [ ] VCNL4040 breakout board
  - [ ] Simple I2C device (e.g., EEPROM)
  - [ ] Different sensor PCB

---

## 📊 Results Summary

### Measurements Record
| Component | Expected | Measured | Status |
|-----------|----------|----------|---------|
| DWEII Power Module | ~5V | 5.2V | ✅ GOOD |
| J3 LED Power Strip | ~5V | 5.2V | ✅ GOOD |
| After Schottky Diode | ~5V | ~5V | ✅ GOOD |
| After 0.1μF Capacitor | ~5V | <5V | ⚠️ SLIGHT DROP |
| **After 10μF Capacitor** | **~5V** | **0.1-0.3V** | **❌ CRITICAL FAILURE** |
| AMS1117 Input | ~5V | _____ V | _____ |
| AMS1117 Output | 3.3V | _____ V | _____ |
| TCA9548A VCC | 3.3V | _____ V | _____ |

### Likely Root Cause
Based on test results:
- [ ] Power supply issue
- [ ] I2C pull-up problem  
- [ ] Cable/connector failure
- [ ] VCNL4040 chip failure
- [ ] PCB manufacturing defect

### Notes & Observations
```
_________________________________________________
_________________________________________________
_________________________________________________
_________________________________________________
_________________________________________________
```

---

## 🛠️ Required Tools
- [ ] Digital multimeter
- [ ] Oscilloscope (optional, for signal integrity)
- [ ] Magnifying glass/microscope
- [ ] Fine-tip probes
- [ ] Jumper wires for testing
- [ ] Known good VCNL4040 breakout (if available)

---

## ⚠️ Safety Notes
- [ ] Power off before making connections
- [ ] Check polarity before applying power
- [ ] Use ESD protection when handling PCBs
- [ ] Double-check measurements before concluding

---

**Completion Date:** _______________  
**Final Status:** _______________  
**Next Steps:** _______________

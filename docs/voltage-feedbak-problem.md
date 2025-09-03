Problem & Solution Summary
The Problem

Symptoms: Inconsistent VCNL4040 sensor detection, random voltage readings (1.4V, 3.3V, high voltages), "things change all the time"
Root Cause: Dual 3.3V regulators connected to same output rail

Technical Details
T-Display-S3 Architecture:

Pin 1 ("3v"): OUTPUT from internal AP2112K-3.3V regulator
Pin 12 ("5V"): INPUT power to T-Display

The Conflict:

Your main PCB connected T-Display Pin 1 → Main board 3.3V net
Your main PCB connected AMS1117 output → Same main board 3.3V net
Result: Two active 3.3V regulators fighting each other on same rail

Power Flow Problems:
T-Display USB Scenario:
USB 5V → T-Display → 3.3V out Pin 1 → Main 3.3V net ← AMS1117 ← T-Display Pin 12 ← USB 5V

DWEII Scenario:  
DWEII 5V → AMS1117 → 3.3V AND DWEII 5V → T-Display Pin 12 → T-Display 3.3V → Same net
The Solution
Immediate Fix (What You Did):

Disconnected T-Display 3.3V pins (Pin 1 + other 3V pins) from main board
Kept 5V pin connected so T-Display can still run code and control TCA
Result: Eliminated regulator conflict, stabilized power supply

Why This Works:

T-Display gets power via 5V pin (can run code)
T-Display 3.3V outputs isolated (no regulator fighting)
AMS1117 has sole control of main board 3.3V rail
GPIO signals (SDA/SCL) still work at compatible 3.3V levels

Long-term PCB Redesign Solution

MCU gets power from AMS1117, not the other way around
MCU USB isolated for programming only
Single clean power domain eliminates conflicts
Add comprehensive debugging features (test points, LEDs, etc.)

Key Lesson
The problem wasn't simultaneous power sources - it was architectural: connecting two voltage regulator outputs to the same net, causing them to fight each other regardless of timing.
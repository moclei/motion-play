# Schematic Context System — Verification Test Questions

These questions should be answerable by an AI given only `circuit-context.json` and `hardware/CONTEXT.md`. Defined during Phase 3a, tested during Phase 3c.

## Signal Tracing

1. **Trace the I2C path from the ESP32 to a sensor connector.** What components and nets are involved between the MCU's I2C pins and the JST-SH connector for sensor module 1 (J4)?

2. **How does the LED data signal get from the MCU to the LED strip connector (J3)?** What level-shifting or buffering occurs along the way?

## Component Roles

3. **What is the purpose of D1 (Schottky diode) in the power path?** What nets does it sit between, and why is it there?

4. **What do R28 and R29 do, and why are they 2.2kΩ?** What bus are they associated with?

## Power Architecture

5. **How is the 3.3V rail generated?** Trace the power path from USB-C input to the +3.3V rail, identifying every component in the chain.

6. **How is the LED strip power protected?** What components sit between the +5V rail and the actual LED strip power pin on J3?

## Functional Grouping

7. **Which components belong to the TCA9548A I2C mux subsystem?** List them and describe each one's role.

8. **How many GPIO pins on the T-Display-S3 are broken out to test points but not connected to any functional circuit?** Which pins are they?

## Design Modification

9. **If you wanted to add a fourth sensor module, what changes would be needed on the main PCB?** Consider connectors, I2C mux channels, and interrupt lines.

10. **What would need to change if the DWEII power module were replaced with a direct USB-C connector and buck regulator?** Which components in the power path would be affected?

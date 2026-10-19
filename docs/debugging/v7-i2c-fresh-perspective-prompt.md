> **RETIRED, superseded by `lab/STATE.md`; do not load.** A future outside-review prompt is generated from `lab/STATE.md` (context-strategy §7.3), not maintained by hand.

# Fresh-Perspective Handoff — v7 Main PCB I2C Fault

I designed a PCB and had it manufactured and components assembled by JLCPCB. It arrived and I uploaded my custom firmware, and it doesn't work. I've been trying to find the fault for several days and I'm worried about confirmation bias —  I'm worried that my framing of the problem is causing blind spots in my troubleshooting. **Your job is to look at this with fresh eyes and challenge the framing where it makes sense.** You are not obligated to accept the existing interpretation.

Some documents are provided alongside this prompt:
- `v7-i2c-investigation.md` — the full investigation history, facts, ruled-out theories, tests run, firmware modifications, and board status. Read this for depth of what I've theorized and tried so far.
- `PROJECT.md` - The high level description of what my project is

Below is more detail. I refer to myself as "the user" in this document.

## Observable symptom 

The project is a custom PCB (main PCB v7) with an ESP32-S3 microcontroller that talks to an I2C bus. On that bus:

- An INA219 power monitor at address **0x40**
- A BQ24195 battery charger at address **0x6B**
- A TCA9548A 8-channel I2C multiplexer at address **0x70**
- Three sensor modules attach to the TCA via three JST-SH connectors (J4 → TCA channel 0, J5 → TCA channel 1, J6 → TCA channel 2). Each sensor module carries a PCA9546A local mux at address **0x76** and two VCNL4040 proximity sensors at address **0x60** behind that mux.

The reported failure:

> When the firmware opens a TCA9548A channel that has a sensor module connected, the BQ24195 at 0x6B stops acknowledging its I2C address. This is reproducible on any assembly-healthy v7 board, on any of the three TCA channels, deterministically — never flaky. The failure clears the instant the TCA channel is closed again.

Every VCNL4040 I2C probe fails with NACK-on-address. The BQ failure is the canary; the VCNL4040 failure is the downstream consequence. The board's firmware keeps running throughout — the BQ's power-path function (charging, VSYS regulation) is unaffected; only its I2C interface misbehaves.

---

## The empirical matrix (what we observed)

All tests were run with the same diagnostic loop that probes 5 addresses (INA, BQ, TCA, PCA, VCNL) in several multiplexer states. The matrix reduces cleanly to:

| Setup at a TCA output connector | Bus behavior when that TCA channel opens |
|---------------------------------|-----|
| Nothing plugged in | All devices ACK normally |
| A JST-SH cable plugged in, bare wires dangling at far end | All devices ACK normally |
| A JST-SH cable with **any resistor (4.7 kΩ–47 kΩ) from SDA and/or SCL to +3.3 V** at far end | **BQ at 0x6B NACKs every iteration** |
| A full sensor module plugged in | **BQ NACKs every iteration** (sensor module has 4.7 kΩ pullups on its upstream side) |

Key empirical numbers:
- **I2C error code is always 2 (NACK on address)**, never 5 (bus timeout / stuck low). The bus is electrically alive; BQ is just not responding.
- Pullup resistance swept over a **10× range** (4.7 k, 10 k, 47 k) with **no change in behavior**. Resistance magnitude does not matter.
- Identical behavior at **100 kHz and 400 kHz** I2C clock.
- Identical behavior with **WiFi and Bluetooth radios off** (via a dedicated build flag `-DDIAG_NO_WIFI`).
- Identical behavior on TCA channels 0, 1, and 2 (the three routes between the TCA and connectors J4/J5/J6).
- VSYS voltage monitored by the INA219 stays at **~4.21 V** throughout; no power sag, no brownout.
- On a separate Arduino wired directly to the sensor module (bypassing the main PCB entirely), **everything works perfectly** — sensor modules are not at fault.

**The minimum reproducer is two 10 kΩ resistors, a JST-SH cable, and a breadboard.** No sensor module required.

---

## What the user has already ruled out

These are ruled out with evidence, not assumption. Unless you think the evidence is weak, you can treat these as settled:

- Sensor module, flex PCB, VCNL4040 chips, and PCA9546A all working (Arduino test).
- Power supply quality — no brownout, VSYS steady.
- I2C bus speed — same fault at 100 kHz and 400 kHz.
- Upstream pullup *strength* — swept 4.7 k to 47 k, no variation in behavior.
- Cable stub capacitance / antenna — a cable with floating wires (no DC path to any rail at the far end) does **not** trigger the fault.
- RF coupling from ESP32 radios — tested with both radios off via a build flag.
- Per-channel trace differences — fault follows the cable, not the channel; all three channels behave identically.
- Solder-joint or per-board assembly defects — tested on three separate boards; two of them reproduce the fault identically (the third is an unrelated assembly defect with BQ silent from boot, and is not part of this investigation).
- Basic firmware logic errors — channel selection is verified by reading back the TCA and PCA control registers.

---

## What's *not* been determined

- **Mechanism.** Nobody knows yet *why* adding a DC-terminated cable stub to a TCA channel downstream causes the BQ (sitting on the main upstream bus) to stop acknowledging.
- **Whether the fault is specific to the BQ24195.** The INA219 (also on the upstream bus, closer to the ESP32) never fails. Is this because it's electrically further from the disturbance, or because it has a more tolerant input stage, or because the fault is about the BQ specifically?
- **Why a completed DC path matters.** A 47 kΩ pullup is ~70 µA maximum. That's a tiny current. Why is the *presence* of any DC return sufficient, while the *value* of that current is irrelevant?

---

## Tests the user hasn't run yet

Listed without endorsement — just so you know the option space.

- **Isolate which line matters.** Pullup on SDA only (SCL dangling), vs pullup on SCL only (SDA dangling), vs both. Could reveal asymmetry.
- **Pullup polarity.** DC path to GND instead of to +3.3 V. Could reveal whether the direction of the DC return current matters.
- **Oscilloscope capture** at the BQ24195's I2C pins during a failing transaction. User has a Hantek DSO5202P that's currently broken (stuck at boot splash, possibly firmware corrupted). Recovery pending.
- **Isolate BQ from the main bus.** Put an I2C buffer IC (P82B96, PCA9517) between the main bus and BQ so the BQ sees a shorter, locally-terminated bus. Hardware modification.
- **Power the board from the battery pads with a bench PSU** instead of USB-C, using a data-only USB-C adapter for the serial monitor. Would isolate the BQ24195 from USB-C input state.
- **Re-extract PCB routing** and look at traces directly (the user has tooling — `tools/pcb-context/` — that extracts placement to JSON; has not yet run the equivalent for routing/tracks).

---

## Explicit invitation: what we might be missing

The user is specifically worried that they've been tunneled in. A few examples of what "fresh perspective" might look like:

- **Datasheet / errata / application-note review for the BQ24195.** Is there a known quirk about I2C input thresholds when nearby signals switch? Does the chip enter some state based on VBUS, battery, or VSYS conditions that gates I2C response? Are there registers that change the I2C behavior depending on mode?
- **TI E2E forum posts about the BQ24195.** Other people may have reported unusual I2C behavior on this chip.
- **Bus-topology reconsideration.** Is the "main upstream I2C bus with a TCA mux hanging off it" topology itself sound for this combination of slaves? Is there a well-known design pattern that v7 departs from?
- **Firmware stack issue.** Is `Wire.h` / the ESP32 Arduino I2C driver / the TCA9548 library doing something that could be mistaken for a hardware fault? Is there a protocol-level interaction between addressing 0x70 (TCA) and 0x6B (BQ) that has timing sensitivity?
- **"Bypass BQ entirely" experiments.** If BQ's I2C is electrically removed from the bus, does the VCNL4040 then work? That'd tell us whether the downstream VCNL failure is actually caused by the BQ's misbehavior (e.g., BQ glitching something while it's not ACKing) or is independent.
- **Completely unrelated angle.** Maybe the "BQ NACK" symptom is a *side effect* and we should focus on something else entirely. What other anomalies exist in the diagnostic output that we might be overlooking because they don't match our frame?

---

## What the user is hoping for

Not a guaranteed answer. They'd be happy with:

1. A new test to run that they haven't thought of, or
2. A reason to look at existing evidence differently, or
3. A pointer to a datasheet section / forum post / known design pattern that fits the symptoms, or
4. A reframing of the problem statement that changes what "resolved" would look like.

**You do not need to re-verify everything in the investigation doc.** Trust the ruled-out list unless something catches your attention. The user has run a lot of tests; the question is whether any of the remaining options (or an option they haven't considered) is the right next move.

---

## Logistical context

- The physical hardware and user are available to run experiments.
- Three boards exist: Board 1 damaged from a rework attempt, Board 2 has unrelated assembly defect, **Board 3 is healthy and reproduces the fault. Use Board 3.**
- An Arduino Nano ESP32 is available as an external I2C master.
- Bench DMM available. Oscilloscope broken, recovery in progress.
- Sensor modules (rigid + flex + VCNL4040) are available and confirmed healthy via the Arduino test.

When you respond, feel free to ask the user for additional clarifying information before committing to a direction. They'll be patient.

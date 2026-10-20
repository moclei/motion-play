> **RETIRED, superseded by `lab/procedures/` (`dho804-setup-validation.md`, `known-good-reference.md`); do not follow.** Kept in place because other documents cite this path.

# Debugging v7 I2C Communication with an Oscilloscope

Step-by-step guide for using an oscilloscope to diagnose the v7 main-PCB I2C fault chain. Originally written for a Hantek DSO5202P; the **Rigol DHO804** that arrived 2026-04-28 is now the working scope, so DHO804-specific notes have been added at the top of each major section. The button-name walkthroughs below sometimes still reflect Hantek conventions — when in doubt, follow the DHO804 notes. Written assuming no prior oscilloscope experience.

---

## Rigol DHO804 — what's different from the Hantek the original guide assumed

The DHO804 is a 4-channel, 70 MHz, 12-bit, 1.25 GSa/s scope with a 7" capacitive touchscreen. Most front-panel buttons have a touchscreen equivalent, and many menus are easier to reach by tapping than by knob-hunting. Keep these in mind as you read the rest of the guide:

- **12-bit ADC vs the Hantek's 8-bit ADC** is the single most useful difference for *this* investigation. We are looking for sub-100 mV wobbles on SDA at BQ's pad — features that an 8-bit / 5 V-range scope would round into the LSB. The DHO804 resolves them comfortably.
- **Memory depth: up to 25 Mpts** standard. Set it generously — deep memory at a fine timebase lets you scroll horizontally through a whole transaction after the trigger fires, which matters for I2C decoding.
- **Touchscreen is the fast path for most settings.** Tap the channel label at the bottom of the screen to open the channel menu. Tap a measured value to change its source. Tap the trigger label to open the trigger menu. The physical knobs still work and are sometimes faster (especially the multi-purpose knob for fine adjustments).
- **Probes that ship with the DHO804** are typically Rigol's PVP3150 or similar 1×/10× passive probes. Use the **10× position on the probe switch** for everything in this guide. Confirm the scope agrees by tapping the channel label and setting Probe Ratio to 10×.
- **Probe-comp terminal** is on the front, labelled "Cal". Two pins (signal + ground), 1 kHz square wave. Worth doing once.
- **I2C decode is built in.** Press `MATH` → `Decode` → `Decode 1` (or tap the `Decode` button on the touchscreen menu bar). The DHO804 decodes I2C, SPI, UART, CAN, and LIN; for our purposes only I2C matters.
- **Trigger has dedicated I2C trigger types.** You can trigger on a START condition specifically, on a particular address byte, or on a NACK — much more useful than the generic falling-edge trigger this guide originally described. We'll use the I2C-specific trigger for the BQ-pad capture below.
- **Saving screenshots / waveform data** — there's a USB-A port on the front for a thumb drive. Press the dedicated `Save` button or use `Storage` from the menu. Image (.png) and waveform (.csv / .wfm) both work.
- **No loud fan**, runs cool, no external PSU brick. Powered from a normal mains cord on the back.

The rest of the original guide is portable to the DHO804 with one substitution: where the original says "press CH1 button → menu appears on the right" you can also tap the CH1 label at the bottom of the screen and the same menu opens. Where it says "press Decode" → use the `MATH → Decode` path described above.

---

## Scope targets in the post-Phase-17 v7 I2C investigation (read this first)

The investigation in `docs/debugging/v7-i2c-investigation.md` has progressed beyond the VCNL-NACK framing this guide was originally written for. There are now **two distinct scope-target setups**, and the primary one is no longer the VCNL pads — it's the BQ24195's I2C pads. Use the BQ-pad capture first; the VCNL-pad capture is a secondary discriminator if the BQ-pad capture leaves anything ambiguous.

### Primary capture (post-Phase-17): BQ24195 SDA/SCL pads in the failing config

- **What we're looking for**: two waveform features in a single capture session.
  1. **SCL-correlated wobble on SDA at BQ's pad during the 9th-clock ACK window.** Story D-revised (the dominant surviving hypothesis as of Phase 17) predicts that with the failing-config cable attached, capacitive crosstalk from SCL transitions plus added cable parasitic C drag SDA at BQ's pad below V_IH = 1.3 V momentarily during the ACK window. If this is observed, Story D-revised is confirmed.
  2. **Rising-edge overshoot on SDA at BQ's pad above ~3.9 V (VDD + ~0.6 V).** Legacy target from the original ESD-diode framing of Story D, retained as a sanity check. Phase 17's datasheet drill ruled out a conventional upper ESD clamp at +3.3 V (BQ's SDA is rated abs max +7 V, characterised at V_PULL-UP = 1.8 V), so this feature is no longer expected to be diagnostically meaningful — but if it shows large overshoot it's still worth knowing about.
- **Probe points (preferred)**: BQ24195 (U5) SDA pad (pin 6) and SCL pad (pin 5) directly. Reference: pin descriptions are in the cleaned BQ datasheet at `hardware/components/BQ24195/bq24195_datasheet_clean.html` line 277–289. Probe ground: any nearby GND test pad.
- **Probe points (alternate, easier)**: TPIO43 (SDA) and TPIO44 (SCL) on the main PCB. These are upstream of BQ but on the same upstream net (~34 mm of trace away). Less ideal because the wobble is predicted to be largest *at BQ's pad specifically*, not at the upstream end of the bus, but easier to physically probe and useful as a fallback if the BQ pads can't be hit reliably.
- **Test setup**: failing-config cable in J6 (JST-SH cable, far end → 10 kΩ resistor → either main PCB +3.3 V via cable's pin 1 wire OR a clean external +3.3 V source with shared GND), SCL wire at the far end dangling unconnected, SDA wire at the far end through the 10 kΩ resistor. Firmware in `motion-play-v7-busrec` env (so the diagnostic loop runs and BQ is being probed every ~2 s). The fault should be active and steady-state — TCA2 row should report `BQ:X(2)` every iteration.
- **Trigger setup**: trigger on **SCL falling edge** at the BQ's SCL pad (this catches each clock pulse during a transaction). For the wobble target, pan to the 9th-clock ACK window (8 data bits + 1 ACK = 9 SCL pulses after the START); SDA at BQ's pad during the ACK window is the waveform of interest. For the overshoot target, look at any SDA rising edge during the same capture.
- **Decode setup**: enable I2C decode with SCL = scope channel for SCL pad, SDA = scope channel for SDA pad, 7-bit address, threshold 1.6 V. Decoded annotation should show `S 0xD6 N` (write to 0x6B = 0xD6 on the wire, with NACK on the address byte) repeating every diagnostic iteration. If decode shows `S 0xD6 A` while firmware logs `BQ:X(2)`, that's a divergence between scope and ESP32 perception of the bus and is itself diagnostic — capture and report.
- **Discrimination outcomes**:
  - Wobble below V_IH = 1.3 V observed during ACK window → **Story D-revised confirmed**. Story F (ESP32-S3 I2C peripheral interaction) is also still possible if Arduino-as-master test (run separately, see investigation doc § "Immediate next steps") shows Arduino also fails. v8 buffer fix is correct.
  - No wobble below V_IH, no rising-edge overshoot above ~3.9 V, but BQ still NACKs → **Story D-revised refuted, Story E becomes the only remaining candidate**. v8 buffer fix is still correct (Story E by definition lives at BQ's pad too).
  - Large rising-edge overshoot above ~3.9 V observed → unexpected given the Phase 17 datasheet drill; capture and re-evaluate the ESD topology assumption from first principles.

### Secondary capture (legacy, this guide's original target): VCNL4040 SDA/SCL at the ZIF or chip pads

Used only if the BQ-pad capture is inconclusive and we need to confirm the downstream consequence. The original Step 1–8 walkthrough below was written for this target. The probe points and interpretations in Steps 2 and 7 are specific to this use case.

---

## Why We're Doing This (legacy framing — VCNL capture target)

> Note: this section reflects the original purpose of this guide before the BQ24195 was identified as the upstream cause of the VCNL-side symptom. Kept for reference; the primary scope target is now the BQ-pad capture above.

Firmware-side debugging has confirmed:

- The I2C bus works end-to-end from the ESP32 through the TCA9548A, through the PCA9546A (at 0x76 on the rigid), all the way to where the downstream I2C signals exit the rigid through the ZIF connector.
- The PCA9546A's channel selection is verified — the control register reads back the channel we wrote.
- 3.3 V power and GND are present at the VCNL4040 pins.
- Continuity from the ZIF pins to the VCNL4040 SDA/SCL pins is good, with no crossover.
- Downstream I2C pull-ups on the rigid are populated and at the correct value.
- VSYS is stable at ~4.2 V and current draw is well under the BQ24195's 2 A input current limit — no brown-out.
- The behavior is identical at both 400 kHz and 100 kHz bus speeds.

Despite all of that, the VCNL4040s never respond at their I2C address (0x60). At this point we have to look directly at the electrical signal on the bus. The oscilloscope is the tool that tells us what is actually happening on the wire.

**What we're hoping to learn:** Is the VCNL4040 *receiving* valid I2C traffic and *choosing not to acknowledge* (which would mean the chip is at fault), or is the signal arriving at the chip *degraded or missing* (which would mean there is still something wrong in the signal path)?

---

## Equipment You Need

- Hantek DSO5202P oscilloscope
- The two passive probes that came with the scope (they are labelled something like "PP-80" or similar — standard 1×/10× passive probes)
- Motion Play main PCB v7 with the rigid and flex connected, ready to flash and run
- A USB cable to power the main PCB
- Tweezers or a fine-tip probe hook (useful for hitting ZIF pins, though the probe clip usually works)
- A well-lit work surface

You do **not** need: a signal generator, a power supply for the scope (it's mains-powered), active probes, or any special adapters.

---

## Safety Notes (Quick)

- This is all low-voltage (3.3 V logic). No shock risk.
- The only damage risk: shorting two pins with the probe tip while the board is powered. Go slowly, especially at the ZIF which has 1.0 mm pin pitch.
- Never attach the probe ground clip to anything that isn't ground. Probe grounds are connected directly to the scope's chassis ground (earth through the mains plug). Clipping to 3.3 V or a signal line would cause a large current through the probe's ground wire.

---

## Step 1: Set Up the Oscilloscope

### 1.1 Power On

1. Plug the scope into a mains outlet.
2. Press the power button on the front. It takes 15–30 seconds to boot.
3. When it reaches the default display, you should see a grid ("graticule"), two channel labels (CH1 and CH2) at the bottom, and some default settings. Don't worry about them — we'll set them all explicitly.

### 1.2 Understand What a Probe Is

Each probe has four parts you need to identify:

- **BNC connector** — the metal coaxial plug at the end. This goes into the scope's CH1 or CH2 input.
- **Probe tip** — the sharp spring-loaded pin at the other end. Press it against a pin or pad on the board.
- **Retractable hook clip** — slides over the probe tip. Lets you clip onto a pin or wire without holding the probe. **Use this.** Holding a probe tip steady with your hand for minutes at a time is miserable.
- **Ground clip** — a short wire coming off the probe body with an alligator clip on the end. This must connect to ground on the board under test.

On the probe body there is usually a **1×/10× switch**. Set it to **10×**. This is the default mode for almost all measurements and is what the scope will expect.

### 1.3 Plug In the Probes

1. Take **Probe A** (pick either one — they're identical) and screw its BNC connector onto the **CH1** input on the front of the scope. Turn it clockwise until it locks.
2. Take **Probe B** and plug it into the **CH2** input the same way.

### 1.4 Tell the Scope the Probes Are 10×

Because you set the physical switch to 10×, the scope needs to know so it can display correct voltages.

1. Press the **CH1** button on the front panel. A menu appears on the right side of the screen.
2. Find the menu item labelled **Probe** or **Attenuation**. Press the soft-key next to it (the buttons along the right edge of the screen).
3. Select **10×**. The number next to "Probe" on the screen should now read `10X`.
4. Repeat for **CH2**.

If you skip this step, every voltage measurement will be 10× too small (a 3.3 V signal will look like 0.33 V). Very easy mistake — double-check it.

### 1.5 One-Time: Probe Compensation

Each probe has a small adjustment screw (usually on the BNC end or halfway along the probe body) that needs to be tuned once. This step is optional for this debugging — we're looking at slow 100 kHz signals and slight miscompensation won't matter — but if you want to do it properly:

1. Find the small metal terminal on the front of the scope labelled **PROBE COMP** or **CAL** (near the bottom, with a ~1 kHz square-wave output).
2. Clip the probe hook to the **signal** terminal and the ground clip to the **ground** terminal next to it.
3. Set CH1 to show a reasonable view (press **AUTO** if you're unsure; the scope will auto-range).
4. Look at the square wave on screen. The top and bottom should be flat, with sharp corners.
5. If the corners are rounded or peaked, turn the trimmer screw on the probe with a small flathead screwdriver until the corners are square.

Skip this if you want; do it later when you have time.

---

## Step 2: Identify the Probe Points on the Board

We want to probe **SDA** and **SCL** as close to the VCNL4040 as possible — but the easiest physical probe points are the ZIF connector pins on the rigid (they're larger and more exposed than the tiny VCNL4040 pins on the flex).

### Recommended probe points (ZIF on the rigid)

Use this as your first probe position. If the ZIF signals look clean, you can move the probes closer to the IC later if needed.

| Signal | Location | Notes |
|--------|----------|-------|
| **SDA1** | ZIF pin 4 | I2C data, sensor 1 channel |
| **SCL1** | ZIF pin 3 | I2C clock, sensor 1 channel |
| **GND** | **TP2** on the rigid | Labelled "GND" — a dedicated test pad. Use this for both probe ground clips. |

The ZIF pin numbering on the rigid starts at pin 1 nearest the board edge and counts inward. Consult `hardware/sensor-rigid/circuit-context.json` if you need to double-check, or look at the silkscreen.

### Alternative (probes directly at the chip)

If the ZIF capture shows clean signals but we want to rule out a contact or trace issue between the ZIF and the IC, move the probes to:

| Signal | Location |
|--------|----------|
| **SDA1** | IC1 pin 7 (SDAT) on the flex |
| **SCL1** | IC1 pin 8 (SCLK) on the flex |
| **GND** | TP2 on the rigid (same as before) |

These pads are smaller — a fine probe hook or a tweezer-tip is helpful.

---

## Step 3: Power the Board and Connect the Probes

1. Connect the main PCB's USB cable to power it — but **don't open the serial monitor yet.** We want the firmware to run and hammer the bus in a failing loop, but we need to arm the scope first.
2. Attach the ground clip of **both probes** to TP2 (GND) on the rigid. Both scope channels must share the same ground.
3. Attach the CH1 probe hook to **ZIF pin 4 (SDA1)**.
4. Attach the CH2 probe hook to **ZIF pin 3 (SCL1)**.

Be careful not to let the two probe tips touch each other or adjacent ZIF pins — 1.0 mm pitch is tight.

---

## Step 4: Configure the Scope

All of these settings are on the front panel or in menus that appear when you press the corresponding button.

### 4.1 Vertical (voltage) settings

Press **CH1**, then set:

| Setting | Value | Notes |
|---------|-------|-------|
| Coupling | **DC** | We want to see absolute voltage, including the 3.3 V idle level |
| Probe | **10×** | Set earlier, just confirm |
| Volts/div | **1 V/div** | Click the large knob above the CH1 button — each click changes V/div |

Repeat for **CH2**.

### 4.2 Vertical position

Each channel has a small **POSITION** knob above its channel button. Use these to put the zero-volt line of each channel near the bottom of the screen, so the 0 → 3.3 V swing fills most of the display upward. A typical setup:

- Move CH1's zero line to about one division up from the bottom
- Move CH2's zero line to about one division up from the bottom (same place)

Some people prefer to offset the two channels vertically so they don't overlap. Up to you.

### 4.3 Horizontal (timebase)

Look for the **Horizontal** section (usually a large knob labelled "SEC/DIV" or similar).

Set timebase to **20 µs/div**. At 100 kHz, one I2C clock cycle is 10 µs, so 20 µs/div shows half a clock per division — ten divisions across the screen = five clocks = about half an I2C address byte. We will actually want to see more than that, so if the memory depth allows:

- If the scope lets you set **memory depth** (Acquire menu), set it to the deepest available (typically **40K** or **80K** on the DSO5202P). Deep memory lets you capture a full transaction even at a detailed time base.

### 4.4 Trigger

The trigger tells the scope when to "freeze" the waveform. Without a trigger, you just see a fast-scrolling mess.

Find the **Trigger** button/menu (usually a dedicated section on the right side of the front panel).

| Setting | Value |
|---------|-------|
| Source | **CH1 (SDA)** |
| Slope | **Falling edge** |
| Mode | **Normal** (not Auto) |
| Level | **~1.6 V** (middle of the 0–3.3 V swing) |

**Why falling edge on SDA?** An I2C START condition is defined as SDA going low while SCL is high. SDA's first falling edge in each transaction is therefore the beginning of a new I2C message. Triggering on this catches every new I2C ping the firmware issues.

**Why Normal mode and not Auto?** Auto triggers regardless of whether the condition is met — you'd see free-running noise. Normal waits for a real trigger event. If the trigger never fires, the screen stays blank, which is useful information (means no SDA edges are happening at your probe point).

### 4.5 Acquisition

Find the **Acquire** menu. Set:

| Setting | Value |
|---------|-------|
| Mode | **Normal** or **Sample** (not Average or Peak Detect) |

---

## Step 5: Enable I2C Protocol Decoding

This is the killer feature. The scope will watch the waveforms on CH1 and CH2 and overlay decoded bytes directly onto the display, showing you Start conditions, address bytes, ACK/NACK bits, and data.

1. Press the **Decode** or **Math** button (on the DSO5202P it may be under **Utility → Decode** or a dedicated button — check the panel).
2. Select **Bus Decoding** or **Serial Decoding**.
3. Choose protocol: **I2C**.
4. Configure the sources:
   - **SCL source: CH2**
   - **SDA source: CH1**
5. Threshold: **~1.6 V** for both (halfway between 0 and 3.3 V).
6. Address format: **7-bit**.
7. Turn decoding **ON**.

After this, any I2C traffic you capture will show annotations like `S 0xC0 N` below the waveform — where `S` is the start condition, `0xC0` is the write address (0x60 << 1), and `N` means NACK (no acknowledge).

---

## Step 6: Capture the Failing Transaction

Now the capture sequence:

1. Verify the scope trigger is **armed** (usually shown as "Ready" or "Armed" at the top of the screen) and in **Normal** mode.
2. Press **Single** (not Run/Stop) — this arms the scope for one capture, then it holds the display.
3. Press the **reset button** on the main PCB (or unplug/replug USB) to reboot the firmware.
4. The firmware will go through boot, then reach the sensor init phase where it tries to ping 0x60 on each PCA channel. The scope should trigger on the first SDA falling edge and hold the capture.

Look at the screen.

If nothing triggers within 30 seconds:
- Try switching the trigger source to **CH2 (SCL)**, falling edge. Some I2C masters hold SDA low first; triggering on SCL might catch it more reliably.
- Or switch to **Auto** trigger mode temporarily to confirm you're seeing *any* activity on the lines. If in Auto mode you see a flat line at 3.3 V with no wiggles at all, the firmware isn't actually pinging that channel — the PCA hasn't opened the channel or something is wrong upstream.

---

## Step 7: Interpret What You See

Use the scope's cursors or just read the decoded annotations.

### Scenario A: Decoded annotation shows `S 0xC0 N`

This is the expected outcome of our ongoing investigation.

- **S** = Start condition (SDA falls while SCL is high). Seen — good.
- **0xC0** = Address byte. In 7-bit I2C, the write to address 0x60 appears as `0xC0` on the wire (the 7-bit address shifted left by one with the R/W bit = 0 appended). So the master is correctly addressing the VCNL4040. Good.
- **N** = NACK. **The 9th clock pulse shows SDA floating high instead of being pulled low by the addressed device.** This means the chip is receiving the address but is not responding.

**Conclusion:** The VCNL4040 either isn't there, is dead, or is the wrong part. Your earlier checks confirmed it's physically present and visually correct, so the next step is to test the chip directly with another I2C master (Option B from our earlier discussion: wire the flex to a spare Arduino or similar). If that also fails to find 0x60, the chips themselves are not working.

### Scenario B: Decoded annotation shows `S 0xC0 A`

The VCNL4040 **is** acknowledging. But the ESP32 firmware is still logging a NACK (I2C error: 2).

- **A** = ACK. SDA is pulled low on the 9th clock. The sensor is alive and responding.

**Conclusion:** This is very unusual and would indicate a timing or sampling issue on the ESP32 side — perhaps the ACK arrives slightly later than the ESP32 expects, or the bus has enough capacitance that the ACK window closes before the ESP32 can read it. Unlikely but diagnostically important. Share this capture and we'll dig in.

### Scenario C: Waveforms are present but decode fails, or shows garbled bytes

You see both SCL and SDA wiggling, but the decoder shows odd bytes or can't lock on.

Look closely at:

- **Idle voltage.** Between transactions, SDA and SCL should sit solidly at 3.3 V. If they're sitting at 2.0–2.8 V, the pull-ups are weak or there's excessive bus capacitance.
- **Rise time.** Watch the transition from 0 V to 3.3 V on either line. At 100 kHz the rise should be well under 1 µs. If it looks like a slow curve taking 3–5 µs to reach 3.3 V, the bus is capacitively loaded and the pull-ups can't keep up — the VCNL4040 may be seeing an ambiguous high/low state and refusing to decode its address.
- **High and low levels.** Highs should reach ~3.3 V; lows should go to ~0.1 V or less. If highs are at 2.5 V or lows are at 0.8 V, signal integrity is degraded.

**Conclusion:** Signal integrity issue. Capture what you see, then we investigate bus capacitance / pull-up strength together.

### Scenario D: No transitions on SDA or SCL

The scope triggers (or in Auto mode, both channels just show flat lines at 3.3 V or 0 V).

**Conclusion:** The I2C clock and data aren't reaching this probe point. Possibilities:

- The PCA isn't actually opening the channel (despite what the firmware readback said — but we already verified this, so unlikely).
- The probe isn't making electrical contact with the pin (easy to miss on 1.0 mm pitch — check the hook is really on the metal pad, not next to it).
- Something is shorting the line to ground or 3.3 V between the PCA and the ZIF.

Move the probes to the PCA9546A output pins on the rigid (U1 pins 4 and 5 for SDA1 and SCL1) and repeat. If you see signals there but not at the ZIF, the fault is in the rigid's layout between U1 and the ZIF.

---

## Step 8: Save the Capture (Optional but Useful)

If the DSO5202P has a USB port on the front, you can insert a USB stick and save the waveform as an image or as raw data. To do this:

1. Insert the USB stick.
2. Press **Save** or **Utility → Save/Recall**.
3. Select **Save Image** (BMP/PNG) or **Save Waveform** (CSV).
4. Share the saved file when you report back.

---

## Troubleshooting Your Scope Setup

| Symptom | Likely Cause | Fix |
|---------|--------------|-----|
| Both traces are flat, regardless of what's happening on the board | No channel enabled, or channel off-screen | Press CH1 and CH2 buttons to enable; use POSITION knobs to bring traces on-screen |
| Voltages look 10× too low (3.3 V signal shows as 0.33 V) | Scope probe attenuation set to 1× but probe is physically 10× | Go to CH1 menu → Probe → 10× |
| Voltages look 10× too high | Opposite of above | CH1 menu → Probe → 10× (if probe switch is actually 10×) |
| Trigger never fires in Normal mode | Trigger level is outside the signal range, or wrong source, or wrong edge | Set trigger level to ~1.6 V; confirm source = CH1; slope = falling |
| Waveform is "floating" and shifting around | AC coupling is on instead of DC | CH1 menu → Coupling → DC |
| Decoder shows nonsense even though waveforms look clean | Wrong threshold or wrong channels assigned | Decode menu → Threshold 1.6 V, SCL = CH2, SDA = CH1 |
| Ringing / spikes on signal edges | Probe ground lead is too long, picking up EMI | Use the short ground spring instead of the long alligator clip lead |

---

## After the Capture — What to Send Back

When you report your result, include:

1. Which scenario (A/B/C/D) matches what you saw.
2. The decoded annotation on the address byte, if any.
3. Idle voltage level on SDA and SCL between transactions.
4. Rough rise time from 0 V to 3.3 V (your scope's cursors or just eyeballed from the time base).
5. A screenshot of the waveform if you can save one.

With that information we can pick the next move cleanly.

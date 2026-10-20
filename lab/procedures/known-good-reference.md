# Known-good reference (V9)

Purpose: prove that the probe, ground and scope chain reads a healthy I²C bus as healthy, using the **same** probes, ground method and settings planned for the board under test. This is `test-workflow-audit.md` §4.3, made concrete for our boards. It is step V9 of `dho804-setup-validation.md`.

**Outcome rule.** If the v6 reference fails these numbers with a validated setup, either the setup or the expectation is wrong. Resolve that before any v7 measurement is recorded. Never widen a pass limit to make the reference pass.

- Same conventions as `dho804-setup-validation.md`: steps are relayed as §4.8 blocks, commands run in Cursor's terminal at the repo root with the `q` helper (§0.3 there), every setting is set and read back, and every measured item goes on the Result panel while the scope is running (§0.4 there; the panel rule rests on an untested hypothesis).
- Scope facts are cited as *[facts: row]*, meaning `docs/initiatives/test-workflow-setup/PLAN.md` → "Verified instrument facts". **[own]** marks our own figures and heuristics.

## Prerequisites

1. `dho804-setup-validation.md` V1–V8 passed **in this session**, with the probes, ground method and channel settings used below. Change any of them and V2–V8 have to be redone.
2. **Reference DUT:** the surviving **v6** main board, flashed with the **`v6-ref`** tag (`4da1c67`, env `lilygo-t-display-s3`; its I²C init is in the tag message: `Wire.begin(43, 44)`, 400 kHz, default drive, no filters, default pulls). Flashing it is the card's step, not this procedure's.
3. The card names the arms, the probes and the channels. This procedure gives the points and the pass table.

## Points (from the board files, not from memory)

Names come from the Phase 5 extraction of the KiCad PCB files, v6 `motion-play-main.kicad_pcb@fd632ef` and v7 `@c2acffc` *[facts: PCB probe points]*.

| Signal | Master end (v6 and v7) | BQ24195 end (v6 and v7) |
|---|---|---|
| SDA | **TPIO43** (`/I2C_SDA`) | **U5 pin 6** (`/I2C_SDA`) |
| SCL | **TPIO44** (`/I2C_SCL`) | **U5 pin 5** (`/I2C_SCL`) |

- The master is U2 (T-Display-S3, pins 15/16) on v6. U5 is the BQ24195 on both boards. On v6 its package is rotated, but the pin numbers are the same.
- U5 is a 0.5 mm-pitch QFN. Its own GND pins (U5.2, U5.3) sit beside the signal pins and the exposed pad is under the package, so they are **not** ground points.
- Other v6 pads, for context: TP4 (`PGND`), TP_GND1 (GND, about 36 mm from U5), TP_3V1 (+3.3 V), TP_5V1 (+5 V).

## Ground: the same-ground-length rule

Use the **same ground type and length on every board you compare**, not "whatever pad is closest". Otherwise the comparison is uneven.

| Probing at | Ground point | Ground on v6 | Ground on v7 | Use |
|---|---|---|---|---|
| U5 pins 5/6 | **C21.2** | 2.64 mm | 2.64 mm | **Yes.** Identical on both boards, so a ground spring on C21.2 is the same ground on both |
| TPIO43/44 | v6 **U2.14** (header pin, through-hole); v7 **C9.1** (100 nF) | 8.26 mm | 3.05 mm | The pads differ, so use the **same wire, ≤ 10 mm [own]**, on both boards and record its length |
| either | TP4 | 6.85 mm from U5 | 12.09 mm from U5 | **No.** "TP4 on both boards" is not the same ground length |

All distances are copper edge to copper edge, and run slightly low (roundrect corners ignored) *[facts: PCB probe points]*.

> **Bridging warning (C21).** C21.1, the other end of C21, is **`Protected_VBUS`**, and so is C20.1 next to it. A ground spring or wire that touches both ends of C21 shorts the charger input to ground. Land the ground on the **outer end of C21.2, away from C21.1**, with the board powered off, and look at it before powering on.

Whether a spring stays put on the 0603-size C21.2 pad has not been tried. If it won't, use a ≤ 10 mm wire to C21.2 and record the length. Ground springs fit both the Rigol stock probe and the SQ500 *[facts: Ground springs]*.

## Arms

| Arm | CH1 | CH2 | Ground |
|---|---|---|---|
| **S1**, master end | SDA at TPIO43 | SCL at TPIO44 | the master-end wire (table above) |
| **S2**, BQ end | SDA at U5.6 | SCL at U5.5 | spring (or wire) on C21.2 |

Use the Rigol stock probe at 10× or the SQ500 (fixed 10:1), with the channel ratio set to 10 and read back (V2). Not the SQ10 (1:1) *[facts: SQ10 attenuation]*.

## Which transaction to capture

On `v6-ref` the BQ24195 is addressed **only at boot**. `configureBQ24195()` in `firmware/src/main.cpp` @ `4da1c67` first sends an address-only probe to 0x6B, then writes REG00 and REG05. After that, bus traffic is to the TCA9548A (0x70) and the VCNL4040s (0x60). So the reference frame is caught by arming a single trigger and then restarting the board. The firmware restarts when the board's **RIGHT button (GPIO 14)** is pressed (boot banner in the same file), or power-cycle it.

The expected address byte on the wire is **`D6`** (0x6B, write), followed by ACK.

## Steps, per arm

1. **Probes on.** Board powered off: land the grounds first (bridging warning above), then the tips, per the arm table. Power on. Confirm the ground method matches V6 for this arm.
2. **Channels and timebase:**
   ```
   q ':CHANnel1:DISPlay ON'; q ':CHANnel2:DISPlay ON'
   q ':CHANnel1:PROBe 10'; q ':CHANnel2:PROBe 10'
   q ':CHANnel1:SCALe 0.5'; q ':CHANnel2:SCALe 0.5'; q ':CHANnel1:OFFSet -1.65'; q ':CHANnel2:OFFSet -1.65'
   q ':CHANnel1:BWLimit OFF'; q ':CHANnel2:BWLimit OFF'
   q ':TIMebase:MAIN:SCALe 1e-5'
   q ':CHANnel1:PROBe?'; q ':CHANnel2:PROBe?'; q ':CHANnel1:SCALe?'; q ':CHANnel1:OFFSet?'; q ':TIMebase:MAIN:SCALe?'; q ':ACQuire:MDEPth?'; q ':SYSTem:ERRor?'
   ```
   **CHECK:** `10`, `10`, `5.000000E-01`, about `-1.65`, `1.000000E-5`, `1.0000E+04`, `0,"No error"`.
   - These are the reference's settings. Whatever they are, they must be the same as the settings planned for the board under test (the card states them), and V5 must have been run at them.
   - Memory depth must read **10 kpts**: `capture.py` refuses deeper memory, because a single read is verified only at 10 kpts *[facts: Waveform range]*. If it reads more, set the memory depth to 10k in the scope's acquire menu and write the button path in REPORT.
   - At 10 µs/div the 10 kpt record covers 100 µs at 10 ns per sample. That holds the whole address frame (about 25 µs at 400 kHz) with room to resolve a 300 ns edge.
3. **Decode and trigger** (as in V8), then thresholds for the rise time:
   ```
   q ':BUS1:MODE IIC'; q ':BUS1:IIC:SCLK:SOURce CHANnel2'; q ':BUS1:IIC:SDA:SOURce CHANnel1'
   q ':TRIGger:MODE IIC'; q ':TRIGger:IIC:SCL CHANnel2'; q ':TRIGger:IIC:SDA CHANnel1'; q ':TRIGger:IIC:WHEN STAR'
   q ':MEASure:SETup:MAX 70'; q ':MEASure:SETup:MIN 30'
   q ':BUS1:MODE?'; q ':TRIGger:MODE?'; q ':TRIGger:IIC:WHEN?'; q ':MEASure:SETup:MAX?'; q ':MEASure:SETup:MIN?'; q ':SYSTem:ERRor?'
   ```
   **CHECK:** `IIC`, `IIC`, `STAR`, `7.000000E+01`, `3.000000E+01`, `0,"No error"`. The thresholds default to 90/50/10 %, so the 30 → 70 % rise time is wrong unless they read back 70 and 30 *[facts: Measurement thresholds]*. Setting them has not been tried yet. If the read-back is wrong, set them in the measure menu and write the button path in REPORT.
4. **Result panel, scope running.** Put **Vtop, Vbase and Rise time** for CH1 and CH2 on the panel:
   ```
   for c in 1 2; do for i in VTOP VBASe RTIMe; do q ":MEASure:ITEM $i,CHANnel$c"; done; done
   ```
   **CHECK:** the Result panel shows the six items, each with a number. If one is missing, add it by hand and note the path. (`RTIMe` has not been queried on this scope yet. If it reads `9.9E37`, the CSV check in step 7 still gives the rise time.)
5. **Arm one frame:** `q ':TRIGger:SWEep SING'`, then `q ':TRIGger:SWEep?'`. **CHECK:** `SING`, and the screen waits for a trigger. Press the board's **RIGHT button** (or power-cycle it). **CHECK:** the scope triggers once and stops, and the decode row reads **`D6`** then ACK. If it shows another address, arm again and restart again.
6. **Capture:**
   ```
   python3 tools/lab/capture.py --test <V7R-NNN> --arm <S1|S2> --items VTOP,VBASe,RTIMe --session lab/log/<YYYY-MM-DD_sNN>.yaml
   ```
   **CHECK:** the output ends `The scope is left STOPPED.` and lists the `.png`, `.csv` and `.setup.bin`. Note any `NOTE: … invalid` line in REPORT.
7. **Session work (no operator action):** open the PNG and write the `ai_read` entry. Then, from the CSV:
   - **V_OL:** the mean of SDA over the flat middle of a **master-driven 0-bit**. In `D6` = `1101 0110`, those are address bits 5 and 3 and the R/W bit (bit 0). The 9th-clock **ACK low is driven by the BQ24195, so exclude it**. Record the bit and the sample range as the value's `gate`. Vbase alone is only a cross-check, because it also includes the ACK low.
   - **Rise time:** 30 → 70 % on each SDA and SCL rising edge in the frame, from the samples. Record the RTIMe panel value next to it. The scope's percentages are of its own Vbase–Vtop span, while UM10204 uses 0.3–0.7 V_DD. With Vbase near 0 V and Vtop near 3.3 V the two agree within a few per cent **[own]**.
   - **Idle high:** Vtop, or the mean of the samples before the START.
   - **Decode:** the address byte and ACK, as read from the PNG.
   This CSV reading stands in for the audit's cursor confirmation; the cursor menus have not been recorded.
8. Press **RUN/STOP** once, set the sweep back with `q ':TRIGger:SWEep AUTO'`, and move to the next arm.

## Pass table (UM10204, V_DD = 3.3 V)

| Quantity | Pass | Note |
|---|---|---|
| V_OL, master-driven 0-bit | **≤ 0.4 V** (UM10204, at 3 mA sink) | **Estimate [own], not a pass band:** tens of mV, ≈ 35 mV at drive CAP_3, from the ESP32-S3 datasheet's typical I_OL (28 mA at 0.495 V). `v6-ref` runs the default drive, for which the datasheet gives no figure. **> 0.2 V on a working bus = investigate the setup [own heuristic].** |
| V_IL threshold | 0.3 V_DD = 0.99 V | reference only, not measured |
| V_IH threshold | 0.7 V_DD = 2.31 V | reference only, not measured |
| Idle high | **3.135 V to 3.465 V** (3.3 V ± 5 %) | same limit as V7 |
| Rise time, 30 → 70 % | **≤ 300 ns** at 400 kHz (`v6-ref` runs 400 kHz); ≤ 1000 ns at 100 kHz | from the CSV; the RTIMe panel value is a cross-check |
| Decode | **`D6`** then ACK | the BQ24195 probe at boot |

The V_OL estimate and its limits are in *[facts: ESP32-S3 V_OL]*. The datasheet's V_OL max (0.33 V) is a no-load figure, so it is not a bound at our ≈ 2 mA. Don't quote 30–80 mV as an expectation; only the order of magnitude follows from the datasheet.

## Secondary reference (optional)

A bench I²C bus, such as the Arduino Nano 33 IoT with any breakout, at 100 kHz. Same probes, same ground method, same settings. The rise-time limit there is ≤ 1000 ns.

## Recording

- One log entry per arm, from `capture.py`. Fill `feature` (for example "SDA, master-driven 0-bit, address bit 3, flat region"), `raw_observation` (operator, verbatim), `channels.CH<n>.{probe, signal, point}` (for example `point: U5.6`), and the CSV-derived values with their `gate`.
- In the card: pass or fail per row of the pass table, citing the evidence files.
- Set `validation.notes` in the session log to "V9 <card ID> pass" or "fail".

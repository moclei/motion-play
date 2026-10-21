# Known-good reference (V9)

Purpose: prove that the probe, ground and scope chain reads a healthy I²C bus as healthy, using the **same** probes, ground method and settings planned for the board under test. This is `test-workflow-audit.md` §4.3, made concrete for our boards. It is step V9 of `dho804-setup-validation.md`.

**Outcome rule.** If the v6 reference fails these numbers with a validated setup, either the setup or the expectation is wrong. Resolve that before any v7 measurement is recorded. Never widen a pass limit to make the reference pass.

- Same conventions as `dho804-setup-validation.md`: steps are relayed as §4.8 blocks (one numbered step = one block, its CHECK read after all of its DO), every step names the screen it means (scope screen, board display or terminal), commands run in Cursor's terminal at the repo root with the `q` helper (§0.3 there), every setting is set and read back, and every measured item goes on the Result panel while the scope is running (§0.4 there; the panel rule rests on an untested hypothesis).
- Scope facts are cited as *[facts: row]*, meaning `docs/initiatives/test-workflow-setup/PLAN.md` → "Verified instrument facts". **[own]** marks our own figures and heuristics.

## Words used here

- **I²C bus.** The two-wire bus the ESP32 uses to talk to the other chips. **SDA** is the data line, **SCL** the clock line. Both idle high (about 3.3 V), and a chip talks by pulling a line low.
- **Master end.** The end of the bus at the ESP32, which drives the clock and sends the address ("master-driven" bits are the ones the ESP32 pulls low). On v6 the ESP32 is on the T-Display board plugged into header U2; on v7 it is the ESP32-S3 module on the board. Probe points **A/B**, ground **C**.
- **BQ end.** The end of the bus at the battery-charger chip **U5** (a BQ24195). Probe points **D/E**, ground **F**.
- **Arm (S1, S2).** One measurement setup: where the two probes and the ground sit. **S1** = master end, **S2** = BQ end. It is also the `--arm` name in capture file names. It has nothing to do with the PCBite arms that hold the probes.
- **Pad and pin numbers.** `C21.1` and `C21.2` are the two ends (pads) of capacitor C21. `U5.6` is pin 6 of chip U5. You don't need to know which is which by eye: the pictures below mark every point with a letter.
- **V1–V9 vs v6/v7.** Capital V1–V9 are the steps of `dho804-setup-validation.md` (this procedure is V9). Lower-case v6 and v7 are the two main-board versions.
- **Ground spring.** The short spring that replaces the probe's ground lead. It touches a ground pad next to the probe tip.
- **Soldered wire (v6).** A ~10 mm solid-core wire soldered to pad C on v6. It is the v6 ground at the master end (S1). The springs touch the wire, not the pad.
- **Unequal ground.** At the master end, v6 uses the soldered wire and v7 a spring straight on pad C. The two grounds are not the same, so a v6–v7 comparison there carries this label.
- **Unplug the board.** The **main-board USB-C cable out**, and **no battery** connected. On v6, the data-only cable to the T-Display may stay in (see Prerequisites); write in `validation.notes` whether it was in.
- **Replug.** Unplug the main-board USB-C and plug it back in, with the probes left where they are. This restarts the board.
- **V_OL.** The low level: the voltage on a line while a chip holds it low.
- **Frame, START, STOP, ACK.** A frame is one I²C message. It begins with a **START** (SDA falls while SCL is high) and ends with a **STOP** (SDA rises while SCL is high). After each byte, the chip that receives it pulls SDA low for the 9th clock: that is the **ACK**.
- **The three screens.** The **scope screen** (the DHO804's display), the **board display** (the T-Display on v6) and the **terminal** (Cursor's terminal on the Mac). Every step names one.
- **Decode band.** The row labelled **B1** / **I2C** at the left edge of the scope screen. Byte labels such as `Write:d6` appear in that row, but only when the frame's START is inside the record.
- **Record.** The 10 000 samples the scope keeps for one capture. At 10 µs/div: −80 µs to +80 µs around the trigger, 16 ns per sample.
- **Address trigger, SINGLE.** The address trigger fires only when the chosen address (here 0x6B, write) is sent. **SINGLE** sweep keeps the first record that triggers and stops the scope.
- **Gate.** The stretch of samples a value is averaged over, given as a time range with the number of samples (n). `i2c_frame.py` prints it.
- **Rise time, 30 → 70 %.** How long a line takes to rise from 0.99 V to 2.31 V (0.3 and 0.7 of the 3.3 V supply).
- **Zero offset.** How far a channel reads from 0 V with its tip on ground. Step V5 of the setup validation measures it (`validation.V5.offset_mV`).

## Pictures: where the probe points are

Every board point in this procedure has a letter on these pictures. **A/B/C** are the master end (S1); **D/E/F** are the BQ end (S2). The two **X** pads carry USB power: never touch them, and never let a spring or wire bridge them to F. Each picture is rendered from the board's KiCad layout, so check each point under the microscope before probing.

| Board | Picture |
|---|---|
| v6 (layout `fd632ef`) | [`img/v6-probe-points.png`](img/v6-probe-points.png) |
| v7 (layout `c2acffc`) | [`img/v7-probe-points.png`](img/v7-probe-points.png) |

![v6 probe points A–F and X](img/v6-probe-points.png)

![v7 probe points A–F and X](img/v7-probe-points.png)

On both boards D is U5 pin 6, E is U5 pin 5, F is the end of C21 farther from U5, and the X pads are the other end of C21 and one end of C20. U5 is turned 90° between the two layouts, so its pins point a different way in the two pictures; the pin numbers are the same. A and B are the round test pads TPIO43 and TPIO44 on both boards. C differs: on v6 it is a ground hole of header U2, on v7 one end of capacitor C9.

## Prerequisites

1. `dho804-setup-validation.md` V1–V8 and its decode setup passed **in this session**, with the probes, ground method and channel settings used below. Change any of them and V2–V8 have to be redone.
2. **Reference DUT:** the surviving **v6** main board, flashed with the **`v6-ref`** tag (`4da1c67`, env `lilygo-t-display-s3`; its I²C init is in the tag message: `Wire.begin(43, 44)`, default drive, no filters, default pulls). The tag message says 400 kHz. That clock is set later, in sensor init. The 0x6B frames this procedure measures run at **100 kHz**, the Arduino default, because `Wire.begin(43, 44)` sets no clock (PLAN "After V7R-002 S1" §2). Flashing it is the card's step, not this procedure's.
   - **Re-flash `v6-ref` at the start of every card.** Without a sensor PCB the boot screen ("Sensor init failed") looks the same under any firmware, so it can't tell you which build is on the board.
   - **No sensor PCB.** The reference runs with no sensor PCB plugged in. With no sensor PCB, `v6-ref` halts early in start-up ("Sensor init failed!" on the board display, `firmware/src/main.cpp` @ `4da1c67`, l.463–464). Before it halts, it sends the 0x6B frames once (l.123) and then tries sensor init at 400 kHz. After the halt the bus stays idle. With a sensor PCB fitted, the firmware keeps running and the bus carries traffic all the time (TCA9548A, VCNL4040).
   - **The soldered wire stays on pad C.** It is the v6 S1 ground. The card lists it in `hardware_config` as a board change.
3. **v6 power and flash path.**
   - **Power:** a mains USB-C charger into the **main-board USB-C**.
   - **Flash and serial:** a **data-only cable** from the Mac to the **T-Display's USB-C**. It passes no power. The ESP32's port (`/dev/cu.usbmodem…`) shows up on the Mac only once the main board is powered.
   - "Unplug the board" means the main-board USB-C out and no battery. The data-only cable may stay in, but it may still join the Mac's ground to the board (not checked for this cable), so write in `validation.notes` whether it was in.
4. The card names the arms, the probes and the channels. This procedure gives the points and the pass table.
5. **Probes stay off the board until a step puts them there.** V1–V4 and V5a use only the scope and its Cal terminals; V5b of the setup validation is the first step on the board, and step 1 below is where each arm's probes are placed. Every time probes or grounds go on or move, the board is unplugged first and checked under the microscope before it is powered on.

## Points (from the board files, not from memory)

Names come from the Phase 5 extraction of the KiCad PCB files, v6 `motion-play-main.kicad_pcb@fd632ef` and v7 `@c2acffc` *[facts: PCB probe points]*.

| Signal | Master end (v6 and v7) | BQ end, U5 (v6 and v7) |
|---|---|---|
| SDA | **A**: test pad **TPIO43** (`/I2C_SDA`) | **D**: **U5 pin 6** (`/I2C_SDA`) |
| SCL | **B**: test pad **TPIO44** (`/I2C_SCL`) | **E**: **U5 pin 5** (`/I2C_SCL`) |

- On v6 the master is U2 (the T-Display-S3 plugged into the board, pins 15/16). U5 is the BQ24195 on both boards. Its package sits at 0° on v6 and is turned 90° on v7, but the pin numbers are the same.
- U5 is a 0.5 mm-pitch QFN (a tiny square chip with pins on all four sides). Its own GND pins (U5.2, U5.3) sit beside the signal pins and the exposed pad is under the package, so they are **not** ground points.
- Other v6 pads, for context (not marked in the pictures): TP4 (`PGND`), TP_GND1 (GND, about 36 mm from U5), TP_3V1 (+3.3 V), TP_5V1 (+5 V).

## Ground: the same-ground-length rule

Use the **same ground type and length on every board you compare**, not "whatever pad is closest". Otherwise the comparison is uneven.

The one exception is the master end (S1): v6 uses the soldered wire and v7 a spring straight on pad C, because pad C on v6 is a header hole filled by the T-Display's soldered pin, where no short probe ground was practical (V7R-001), and v7 gets no soldering. That comparison is labelled **unequal ground**, and it counts only when V5 passed at S1 on both boards.

| Probing at | Ground point | Ground on v6 | Ground on v7 | Use |
|---|---|---|---|---|
| D/E (U5 pins 6/5) | **F** (C21.2) | 2.64 mm | 2.64 mm | **Yes.** Identical on both boards, so a ground spring on pad F is the same ground on both |
| A/B (TPIO43/44) | **C**: v6 **U2.14** (header hole, through-hole); v7 **C9.1** (one end of the 100 nF capacitor C9) | pad C is 8.26 mm from A/B. The ground is the **soldered wire** on pad C; the springs touch it about 8–9 mm from C | 3.05 mm. The ground is a **spring straight on pad C**. No soldering on v7 | **Unequal ground.** Record each board's ground (V6). A v6–v7 comparison at S1 is labelled "unequal ground" and counts only when V5 passed at S1 on **both** boards |
| either | TP4 | 6.85 mm from U5 | 12.09 mm from U5 | **No.** "TP4 on both boards" is not the same ground length |

All distances are copper edge to copper edge, and run slightly low (roundrect corners ignored) *[facts: PCB probe points]*.

> **Bridging warning (C21).** Pad F (C21.2) is ground, but the other end of the same capacitor (C21.1, an **X** pad in the pictures) is **`Protected_VBUS`**, USB power. So is one end of C20 next to it (C20.1, the other **X** pad). A ground spring or wire that touches both ends of C21 shorts the charger input to ground. Land the ground on **pad F, on the side of the pad away from the X pad**, with the board **unplugged**, and look at it under the microscope before powering on.

Whether a spring stays put on pad F (C21.2, a small 0603-size pad) has not been tried. If it won't, use a ≤ 10 mm wire to pad F and record the length. Ground springs fit both the Rigol stock probe and the SQ500 *[facts: Ground springs]*.

## Arms

| Arm | CH1 (SDA) | CH2 (SCL) | Ground |
|---|---|---|---|
| **S1**, master end | pad **A** (TPIO43) | pad **B** (TPIO44) | v6: springs on the **soldered wire** on pad **C** (U2.14). v7: spring straight on pad **C** (C9.1). Unequal ground (table above) |
| **S2**, BQ end | pad **D** (U5 pin 6) | pad **E** (U5 pin 5) | spring (or wire) on pad **F** (C21.2, the end of C21 farther from U5) |

Either probe type works on either channel: the SQ500 (fixed 10:1, the usual bench setup is two SQ500s in PCBite arms) or the Rigol stock probe at 10×. Either way, set the channel ratio to 10 and read it back (V2). Not the SQ10 (1:1) *[facts: SQ10 attenuation]*.

## Which transaction to capture

On `v6-ref` the BQ24195 is addressed **only at start-up**. `configureBQ24195()` (`firmware/src/main.cpp` @ `4da1c67`, l.123) first sends an address-only probe to 0x6B, then writes REG00 and REG05. These 0x6B frames run at **100 kHz**: one SCL clock every 10 µs, so the address byte and its ACK take about 90 µs.

The bus is **not** quiet around them (PLAN "After V7R-002 S1" §1):
- **Before them**, SDA toggles while SCL stays high, in steps of about 8.68 µs. That is one bit of serial at 115 200 baud. It fits the ESP32-S3's start-up code (boot ROM) sending serial text on GPIO43, the same pin as SDA. *This fits the data; it is not proven.* A START trigger fires on it, and the scope decodes nothing (V7R-002 S1).
- **After them**, sensor init runs at 400 kHz (the TCA9548A at 0x70, then a scan of 0x71–0x77) before the firmware halts.

So the scope uses the **address trigger** on 0x6B write with **SINGLE** sweep. It fires only on a 0x6B write frame, at its R/W bit, and stops, so later frames can't replace the record. The board is restarted by a **replug** of the main-board USB-C, with the probes left in place. Don't press the board's RIGHT button: the firmware reads it only after start-up, which it never reaches without a sensor PCB.

The expected address byte on the wire is **`D6`** (0x6B, write), followed by ACK.

## Steps, per arm

1. **Probes on.**
   - If V5–V8 left the probes on this arm's pads, leave the board as it is and only look (the CHECK below).
   - Otherwise **unplug the board** (main-board USB-C out, no battery; the data-only cable may stay in). Land the ground first, per the arm table: for S1 the springs on the soldered wire at pad **C** (v6), or a spring on pad **C** (v7); for S2 the spring on pad **F** (C21.2, the end of C21 farther from U5), away from the X pad (bridging warning above). Then the tips: CH1 (SDA) on pad **A** or **D**, CH2 (SCL) on pad **B** or **E**.

   **CHECK:** under the microscope, each tip sits on its lettered pad, the ground is as in the arm table and as recorded at step V6 for this arm, and nothing touches an **X** pad.
2. **Power.** If you unplugged the board in step 1, plug in the main-board USB-C now.
   **CHECK:** the board display shows "Sensor init failed!".
3. **Channels and timebase:**
   ```
   q ':CHANnel1:DISPlay ON'; q ':CHANnel2:DISPlay ON'
   q ':CHANnel1:PROBe 10'; q ':CHANnel2:PROBe 10'
   q ':CHANnel1:SCALe 0.5'; q ':CHANnel2:SCALe 0.5'; q ':CHANnel1:OFFSet -1.65'; q ':CHANnel2:OFFSet -1.65'
   q ':CHANnel1:BWLimit OFF'; q ':CHANnel2:BWLimit OFF'
   q ':TIMebase:MAIN:SCALe 1e-5'
   q ':CHANnel1:PROBe?'; q ':CHANnel2:PROBe?'; q ':CHANnel1:SCALe?'; q ':CHANnel1:OFFSet?'; q ':TIMebase:MAIN:SCALe?'; q ':ACQuire:MDEPth?'; q ':SYSTem:ERRor?'
   ```
   **CHECK:** in the terminal, `10`, `10`, `5.000000E-01`, about `-1.65`, `1.000000E-5`, `1.0000E+04`, `0,"No error"`.
   - These are the reference's settings. Whatever they are, they must be the same as the settings planned for the board under test (the card states them), and V5 must have been run at them.
   - Memory depth must read **10 kpts**: `capture.py` refuses deeper memory, because a single read is verified only at 10 kpts *[facts: Waveform range]*. If it reads more, set the memory depth to 10k in the scope's acquire menu and write the button path in REPORT.
   - At 10 µs/div the record runs from **−80 µs to +80 µs** around the trigger, at **16 ns per sample** *[facts: Timebase]*. The trigger fires at the R/W bit, about 80 µs after the START, so the START falls just before the record. Every rising edge, every master-driven 0-bit, the ACK and the idle level after the STOP are inside it. 16 ns per sample resolves the ≈ 95 ns edges seen in V7R-002.
4. **Address trigger and rise-time thresholds** (the trigger as in V8):
   ```
   q ':TRIGger:MODE IIC'; q ':TRIGger:IIC:SCL CHANnel2'; q ':TRIGger:IIC:SDA CHANnel1'
   q ':TRIGger:IIC:WHEN ADDR'; q ':TRIGger:IIC:AWIDth 7'; q ':TRIGger:IIC:ADDRess 107'; q ':TRIGger:IIC:DIRection WRITe'
   q ':MEASure:SETup:MAX 70'; q ':MEASure:SETup:MIN 30'
   q ':TRIGger:MODE?'; q ':TRIGger:IIC:WHEN?'; q ':TRIGger:IIC:AWIDth?'; q ':TRIGger:IIC:ADDRess?'; q ':TRIGger:IIC:DIRection?'; q ':MEASure:SETup:MAX?'; q ':MEASure:SETup:MIN?'; q ':SYSTem:ERRor?'
   ```
   **CHECK:** in the terminal, `IIC`, `ADDR`, `7`, `107`, `WRIT`, `7.000000E+01`, `3.000000E+01`, `0,"No error"` *[facts: Trigger (I²C), Measurement thresholds]*. The thresholds default to 90/50/10 %, so the panel rise time is 10 → 90 % unless they read back 70 and 30.
5. **Result panel, scope running.** Put **Vtop, Vbase and Rise time** for CH1 and CH2 on the panel:
   ```
   for c in 1 2; do for i in VTOP VBASe RTIMe; do q ":MEASure:ITEM $i,CHANnel$c"; done; done
   ```
   **CHECK:** the Result panel on the scope screen shows the six items, each with a number. If one is missing, add it by hand and note the path. These panel values are recorded only; the pass rows come from the CSV in step 9.
6. **Arm the single trigger:**
   ```
   q ':TRIGger:SWEep SING'; q ':TRIGger:SWEep?'
   ```
   **CHECK:** in the terminal, `SING`.
7. **Replug** the main-board USB-C: unplug it, wait a second, plug it back in. Leave the probes where they are. Then run `q ':TRIGger:STATus?'`.
   **CHECK:**
   - In the terminal: `STOP` (the scope triggered once and stopped).
   - On the scope screen, the decode band shows **no byte labels**. That is expected at 10 µs/div, because the START is outside the record. The decode is read from the CSV in step 9; V8 showed it on the scope screen.

   If the status is not `STOP`: run step 6 again and replug again. **Stop rule:** no trigger after **3 replugs** → stop and report what the status and the board display showed.
8. **Capture:**
   ```
   python3 tools/lab/capture.py --test <V7R-NNN> --arm <S1|S2> --items VTOP,VBASe,RTIMe --session lab/log/<YYYY-MM-DD_sNN>.yaml
   ```
   **CHECK:** in the terminal, the output ends `The scope is left STOPPED.` and lists the `.png`, `.csv` and `.setup.bin`. Note any `NOTE: … invalid` line in REPORT.
9. **Session work (no operator action):** open the PNG and write the `ai_read` entry. Then run the frame tool on the CSV:
   ```
   python3 tools/lab/i2c_frame.py lab/captures/<V7R-NNN>/<YYYY-MM-DD>_<V7R-NNN>_<S1|S2>_<nn>.csv --expect D6
   ```
   It prints each value with its gate and a PASS or FAIL per row of the pass table below (exit 0 all pass, 1 a fail, 2 bad input or no frame in the record). On exit 2, report it; don't read the CSV by hand. What it measures (PLAN "After V7R-002 S1" §4, §6):
   - **Decode:** SDA read at each SCL rising edge gives the address byte and the 9th bit (ACK when low). It must read `D6` then ACK. This replaces reading the decode band.
   - **V_OL:** on each **master-driven 0-bit** of the address byte. In `D6` = `1101 0110`, those are address bits 5 and 3 and the R/W bit (bit 0). The 9th-clock **ACK low is driven by the BQ24195, so it is left out**. The gate is the time **SCL is high** in that bit, **shrunk by 10 % at each end**. SCL high is when the receiver reads SDA, and the shrink keeps the SCL edges out. Record V_OL **as measured**, and write that channel's zero offset from V5 (`validation.V5.offset_mV`) beside it, in place of the tool's `offset_mV: TODO`. Don't subtract it. The 0.4 V limit is far away, but the ≈ 35 mV estimate is about the same size as the offset (V7R-001: −10.4 / −14.1 mV), so the reader needs both numbers.
   - **Rise time:** every SDA and SCL rising edge in the record, from 0.99 V to 2.31 V (0.3 and 0.7 of V_DD = 3.3 V, as UM10204 defines them), with linear interpolation between samples. The tool gives each edge and the largest per channel. Write the panel RTIMe value (from the capture's log entry) beside it. The panel value has **no pass role**: in V7R-002 it read up to about 3× the CSV value.
   - **Idle high:** the mean of each channel from **5 µs after the last edge** to the end of the record (the tool needs at least 5 µs of samples left). 5 µs is UM10204's bus-free time after a STOP (4.7 µs), rounded up: just after the STOP the line is still settling.
   - **SCL period:** about 10 µs (100 kHz). For the record only.

   Paste the tool's `values_csv` block under the capture's log entry. This CSV reading stands in for the audit's cursor confirmation; the cursor menus have not been recorded.
10. Press **RUN/STOP** once, set the sweep back with `q ':TRIGger:SWEep AUTO'`, and move to the next arm. To move the probes: **unplug the board first**, then lift the tips and the ground, then go back to step 1.

## Pass table (UM10204, V_DD = 3.3 V)

All rows come from the CSV, through `i2c_frame.py` (step 9). No limit here changed after V7R-002 S1.

| Quantity | Pass | Note |
|---|---|---|
| V_OL, master-driven 0-bit | **≤ 0.4 V** (UM10204, at 3 mA sink) | Gate: the SCL-high part of the bit, shrunk by 10 % at each end. **Estimate [own], not a pass band:** tens of mV, ≈ 35 mV at drive CAP_3, from the ESP32-S3 datasheet's typical I_OL (28 mA at 0.495 V). `v6-ref` runs the default drive, for which the datasheet gives no figure. **> 0.2 V on a working bus = investigate the setup [own heuristic].** |
| V_IL threshold | 0.3 V_DD = 0.99 V | reference only, not measured |
| V_IH threshold | 0.7 V_DD = 2.31 V | reference only, not measured |
| Idle high | **3.135 V to 3.465 V** (3.3 V ± 5 %) | from 5 µs after the last edge; same limit as step V7 |
| Rise time, 30 → 70 % | **≤ 300 ns** | Every SDA and SCL rising edge, 0.99 → 2.31 V. The reference frame runs at 100 kHz, but the Fast-mode (400 kHz) limit is kept: rise time is set by the pull-ups and the bus capacitance, not by the clock rate; the bus runs at 400 kHz once the firmware is running; and the v7 comparison is at 400 kHz. So the stricter limit is the one that matters. The panel RTIMe is recorded beside it, with no pass role |
| Decode | **`D6`** then ACK | from the CSV bits (SDA at each SCL rising edge); the BQ24195 probe at start-up |

The V_OL estimate and its limits are in *[facts: ESP32-S3 V_OL]*. The datasheet's V_OL max (0.33 V) is a no-load figure, so it is not a bound at our ≈ 2 mA. Don't quote 30–80 mV as an expectation; only the order of magnitude follows from the datasheet.

## Secondary reference (optional)

A bench I²C bus, such as the Arduino Nano 33 IoT with any breakout, at 100 kHz. Same probes, same ground method, same settings. The rise-time limit there is ≤ 1000 ns (UM10204 Standard mode). That limit is for this secondary reference only, not for the v6 reference.

## Recording

- **One session log per arm**: S1 in `_s01`, S2 in `_s02`, each with its own `validation` block (`dho804-setup-validation.md`, "Closing the validation"). Pass the arm's log to `capture.py` with `--session`.
- One log entry per arm, from `capture.py`. Fill `feature` (for example "S2 reference frame, address trigger 0x6B write"), `raw_observation` (operator, verbatim), `channels.CH<n>.{probe, signal, point}` (for example `point: U5.6`), and paste the `values_csv` block from `i2c_frame.py` (each value carries its `gate`).
- In the card: pass or fail per row of the pass table, citing the evidence files.
- Set `validation.notes` in each arm's log to "V9 <card ID> pass" or "fail".

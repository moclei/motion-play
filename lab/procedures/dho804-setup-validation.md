# DHO804 setup validation (V1–V9)

Run this at the start of every scope session, before any number from that session is trusted. It is `test-workflow-audit.md` §4.2, made concrete for our Rigol DHO804 (firmware 00.01.05) and our probes.

**If any step fails, stop and investigate the setup. Never adjust an interpretation, a threshold or an "effective" parameter to make a reading fit.**

- **Who does what.** The debugger session relays each step to the operator as a §4.8 block (`lab/templates/instruction.md`), one step at a time, and fills the log. The operator does the physical steps and types the commands.
- **One numbered item = one block.** You read its CHECK after you have done all of its DO. So when something has to be checked before the next action, the check ends the item and the action is the next item.
- **Where the numbers come from.** Every scope fact used here is a row of `docs/initiatives/test-workflow-setup/PLAN.md` → "Verified instrument facts", cited as *[facts: row]*. Tolerances marked **[own]** are ours, not a vendor's.
- **Recording.** Results go into the session log `lab/log/YYYY-MM-DD_sNN.yaml`, block `validation` (`lab/templates/log.yaml`). **One log per arm**: S1 writes `_s01`, S2 writes `_s02` (see "Closing the validation"). Validation captures use the arm `val_V<n>` (§4.4), for example `2026-11-04_V7R-012_val_V3_01.png`.
- **Terminal.** Every command runs in Cursor's integrated terminal, at the repo root.
- **When probes touch the board.** V1–V4 and V5a need no board: the probes are plugged into the scope, and V3, V4 and V5a put them on the Cal terminals. V5b is the first step with probes on the board. Every time probes or grounds go on or move on the board, **unplug the board first** and **look before powering on**.

## Words used here

Points on the board are named by the letters **A–F** (and **X**, keep clear) in the pictures `lab/procedures/img/v6-probe-points.png` and `v7-probe-points.png`. The pictures and more words (I²C, SDA, SCL, START, STOP, ACK, "master end", "BQ end", "arm", pad numbers such as C21.2) are at the top of `known-good-reference.md`.

- **The three screens.** The bench has three, and every step names the one it means:
  - the **scope screen**: the DHO804's own display;
  - the **board display**: the small screen on the board (the T-Display on v6), which shows "Sensor init failed!" with `v6-ref` and no sensor PCB;
  - the **terminal**: Cursor's terminal on the Mac, where you type the commands.
- **Result panel.** The list of measurements on the scope screen, such as `Vamp(C1)` with its value.
- **Status badge.** The word on the scope screen that says what the scope is doing, for example `STOP` when it has stopped. `q ':TRIGger:STATus?'` prints the same state in the terminal.
- **Decode band.** The row labelled **B1** / **I2C** at the left edge of the scope screen. When the decode works, byte labels such as `Write:d6` and `A:0` appear in that row, towards the middle of the scope screen. It shows labels only when the start of the I²C frame is inside the record.
- **Record.** The 10 000 samples the scope keeps for one capture. At 10 µs/div it runs from −80 µs to +80 µs around the trigger, at 16 ns per sample; at 20 µs/div from −160 µs to +160 µs, at 32 ns *[facts: Timebase]*.
- **Sweep.** How the scope triggers. **AUTO** keeps the trace updating even with nothing to trigger on. **SINGLE** (`SING`) waits for one trigger, keeps that record and stops.
- **Address trigger.** An I²C trigger that fires only when a chosen address is sent. Here it is the BQ24195's address 0x6B (107 in decimal), write. See V8.
- **Replug.** Unplug the main-board USB-C and plug it back in, with the probes left where they are. This restarts the board, and every start-up sends the 0x6B frames once.
- **DUT** (device under test). The board being measured.
- **Cal.** The probe-calibration output on the scope's front panel: a signal terminal and a ground terminal next to it.
- **V1–V9 vs v6/v7.** Capital V1–V9 are the steps below; lower-case v6/v7 are the board versions. So "the V6 ground" is step V6's ground, not the v6 board.
- **Unplug the board.** The **main-board USB-C cable out**, and **no battery** connected. On v6, the data-only cable from the Mac to the T-Display may stay in. It passes no power, but it may still join the Mac's ground to the board, so write in `validation.notes` whether it was in.
- **Data-only cable.** On v6, the cable from the Mac to the T-Display's USB-C, used for flashing and the serial port. It does not power the board.
- **Noise.** The fuzz on a flat trace. **sd** (standard deviation) is a number for how big that fuzz is, worked out from the CSV samples by `noise_floor.py`. For noise, "mV rms" means the same as the sd in mV.
- **Control (V5a).** The noise the scope and probes show on their own, with both probes on the Cal ground and no board.
- **Excess noise.** The noise the board and its ground add on top of the control. `noise_floor.py` works it out per channel.
- **Zero offset (`offset_mV`).** The average the control reads with the tips on ground. That is how far this channel reads from 0 V. It is not the channel's OFFSet setting (−1.65 V).
- **Soldered wire (v6).** A ~10 mm solid-core wire soldered to pad C on v6. It is the v6 ground at the master end (S1). The probe springs touch the wire, not the pad.
- **Unequal ground.** A comparison at the master end between v6 (wire) and v7 (spring straight on pad C). The two grounds are not the same, so the comparison carries this label.
- **`not_run`.** What you write for a step that was not done, with the reason (see "Closing the validation").

---

## 0. One-time and per-session preparation

### 0.1 One-time Mac setup (once per Mac or terminal app)

1. On the Mac open **System Settings → Privacy & Security → Local Network**.
2. Find **Cursor** in the list and switch it **on**. If it is already on but Python can't reach the scope, switch it off and on again (that fixed it in W6) *[facts: Inputs for Phase 8, Local Network]*.
3. `nc` reaching the scope does **not** prove Python can: `nc` is an Apple binary and is exempt from this setting. Only `capture.py` running cleanly proves it.

Without this, `capture.py` stops with `[Errno 65] No route to host` and prints this hint.

### 0.2 Network link

The scope sits on a direct Ethernet link to the Mac: scope `192.168.50.2/24`, Mac adapter `en7` at `192.168.50.1` *[facts: LAN]*. Plug the USB-C Ethernet adapter into the Mac before you start. The scope's IO page is **Utility → IO**. It should show Network status CONNECTED.

### 0.3 The SCPI helper (paste once per terminal window)

```
SCOPE=192.168.50.2
q(){ (printf '%s\n' "$1"; sleep "${2:-1}") | nc -G 3 "$SCOPE" 5555; }
```

`q '<command>'` sends one SCPI command on port 5555 and prints the reply. The `sleep` keeps the socket open until the scope answers. Plain `printf … | nc` drops the reply *[facts: LAN]*. A command without `?` prints nothing. After a group of settings, run `q ':SYSTem:ERRor?'`. It must print `0,"No error"`.

Every setting below is **set, then read back**. The read-back is the check, because most set commands have not been tried on our firmware yet (only the queries are verified). If a read-back shows the wrong value, set it on the scope by hand and write the menu path you used in REPORT, so this procedure can be updated.

### 0.4 Rules that apply to every step

- **Name the screen.** Never "the screen" on its own: say the scope screen, the board display or the terminal ("Words used here"). The decode band is always "the decode band on the scope screen".
- **Probe ratio by hand.** The DHO804 does **not** detect the Sensepeek SQ500. It left CH2 at `1` with the SQ500 attached, and the Cal signal read about 10× low *[facts: SQ500 attenuation]*. Set every channel's ratio yourself and read it back (V2).
- **Channel on, and the trigger on that channel, before measuring.** A measurement on a channel that is off, or that isn't the trigger source, returned `9.9E37` (invalid) *[facts: Measurement (one value)]*.
- **Every measured item goes on the Result panel while the scope is running, before any capture.** `capture.py` stops the scope and then asks for each value. In W6, the one item that was not already on the panel came back `9.9E37`, while the items on the panel were valid. **This is a hypothesis, not tested**: an item that isn't already being measured may have no value on a stopped trace *[facts: Capture-tool comparison, VPP observation]*. Following the rule costs nothing.
- **`capture.py` leaves the scope STOPPED.** After each capture, press **RUN/STOP** once so the scope runs again (the status badge on the scope screen leaves STOP). The exception is V8 and V9, where the sweep is SINGLE: those steps say what to do instead.
- **Never trust `:SAVE:STATus?`.** It returns `1` even when no file was written. `:SAVE:SETup` and `:SAVE:MEMory:WAVeform` fail silently on 00.01.05 *[facts: Save waveform to stick; Setup save / load]*. `capture.py` refuses to send them. Check that a file exists by listing it.
- **Clock.** The scope has no front-panel date/time setting. `capture.py` sets the clock from the Mac on every run and reads it back *[facts: Scope clock]*. Don't assume a time held across a power cycle. Don't assume any fixed offset between the USB stick's file times and the Mac either. `ingest_usb.py` tries both +0 and +60 min *[facts: Saved-file timestamps; Inputs for Phase 8]*.

### 0.5 Probes

| Probe | Ratio | Use | Source |
|---|---|---|---|
| Rigol stock probe | Switch on the probe body: set it to **10×** | Cal checks, references, all edge and V_OL work | *[facts: DHO804 Cal output]* |
| Sensepeek SQ500 | **Fixed 10:1**, no switch. Scope must be set to 10 by hand | Hands-free at fine pitch; edge and V_OL work | *[facts: SQ500 attenuation, bandwidth, tip capacitance]* |
| Sensepeek SQ10 | 1:1 | **Not for edge or V_OL work** | *[facts: SQ10 attenuation]* |

Ground springs are on hand for both the Rigol stock probe and the SQ500 *[facts: Ground springs]*. Use one wherever it reaches.

The usual bench is **two SQ500s in PCBite arms, CH1 = SDA, CH2 = SCL**. Nothing in V1–V9 needs the Rigol stock probe; it remains allowed on either channel.

---

## V1 — Clock and starting settings

1. Power the scope on. Wait until the scope screen shows the waveform view.
2. Press **AUTO** on the front panel. Do this before anything else in the session, so the scope starts from a known, triggered state.
3. Don't load a saved setup file. Loading (`:LOAD:SETup` or the menu) has not been tested on 00.01.05 *[facts: Setup save / load]*. The settings are set explicitly in V2–V8, and `capture.py` records every one of them in the log entry's `scope_settings` block.
4. The clock is set by the first `capture.py` run of the session (V3).

**Pass:** the V3 capture output has **no** `WARNING: scope clock read-back` line. The entry's `scope_clock` block shows `ok: true` (read-back within 10 s of the Mac), inside the audit's 1 min limit.
**Record:** `validation.notes`: "V1 clock ok (Δ <n> s); no setup loaded".

## V2 — Probe ratio, per channel in use

For each channel `<n>` that will be used (CH1 and CH2 in most cards):

1. Rigol stock probe: slide the switch on the probe body to **10×**. SQ500: nothing to switch, it is fixed 10:1.
2. Run:
   ```
   q ':CHANnel<n>:DISPlay ON'; q ':CHANnel<n>:PROBe 10'; q ':CHANnel<n>:PROBe?'; q ':CHANnel<n>:DISPlay?'; q ':SYSTem:ERRor?'
   ```
   (`<n>` is the channel number, for example `:CHANnel2:PROBe 10`.)
   **CHECK:** in the terminal, `:CHANnel<n>:PROBe?` prints `10`, and `:CHANnel<n>:DISPlay?` prints `1`.

**Pass:** the probe and the scope channel both say 10×, for every channel in use.
**Record:** `validation.V2_probe_ratio`, for example `{CH1: 10x/10x, CH2: "fixed 10:1/10x"}`. The scope setting comes first, then the probe (switch position, or "fixed 10:1" for the SQ500).

## V3 — Probe compensation, on the channel it will be used on

Do it once for each probe, **on the channel that probe will use**. Move the probe to the next channel only after its capture.

1. Clip the probe tip onto the **Cal** terminal on the front of the scope, and its ground (clip or spring) onto the Cal ground terminal.
2. Set the channel, the timebase and an edge trigger on that channel:
   ```
   q ':CHANnel<n>:SCALe 1'; q ':CHANnel<n>:BWLimit OFF'; q ':CHANnel<n>:COUPling DC'
   q ':TIMebase:MAIN:SCALe 2e-4'
   q ':TRIGger:MODE EDGE'; q ':TRIGger:EDGE:SOURce CHANnel<n>'; q ':TRIGger:EDGE:SLOPe POSitive'; q ':TRIGger:EDGE:LEVel 1.5'; q ':TRIGger:SWEep AUTO'
   q ':CHANnel<n>:SCALe?'; q ':TIMebase:MAIN:SCALe?'; q ':TRIGger:EDGE:SOURce?'; q ':TRIGger:SWEep?'; q ':SYSTem:ERRor?'
   ```
   **CHECK:** in the terminal, `1.000000E+00`, `2.000000E-4`, `CHAN<n>`, `AUTO`, `0,"No error"` *[facts: V/div, Timebase, Trigger (edge), Trigger (common)]*. If the trace is off the scope screen, press **AUTO** once, then check the four read-backs again.
3. Put **Vamp, Vtop and Vbase** for this channel on the Result panel (these are also V4's items), with the scope running:
   ```
   q ':MEASure:ITEM VAMP,CHANnel<n>'; q ':MEASure:ITEM VTOP,CHANnel<n>'; q ':MEASure:ITEM VBASe,CHANnel<n>'
   ```
   This is the set form of the verified query. Whether it adds the item to the panel has not been tested. **CHECK:** the Result panel on the scope screen shows `Vamp(C<n>)`, `Vtop(C<n>)` and `Vbase(C<n>)`, each with a number. If one is missing, add it from the scope's measure menu by hand and write the button path in REPORT.
4. On the scope screen, look at the square wave's top and corners. On a probe with a compensation trimmer, turn the trimmer with the plastic tool until the top is flat and the corners square, with no overshoot or rounding.
5. Capture, then press **RUN/STOP** once to run the scope again:
   ```
   python3 tools/lab/capture.py --test <V7R-NNN> --arm val_V3 --items VAMP,VTOP,VBASe --session lab/log/<YYYY-MM-DD_sNN>.yaml
   ```
   **CHECK:** in the terminal, the output ends `The scope is left STOPPED.`, it has no `NOTE: … invalid` line and no clock `WARNING` line, and it lists a `.png`.

**Pass:** flat top, square corners, no visible overshoot or rounding at 1 V/div in the PNG.
**Record:** `validation.V3_comp_png`: the PNG name (one per probe or channel; list them if more than one).

## V4 — Cal amplitude, per channel in use

The Cal output is a **1 kHz, 3 Vpp** square wave, about 0 → 3 V *[facts: DHO804 Cal output]*. Rigol gives no tolerance. ±3 % is ours **[own]**.

1. Use the V3 capture. Its log entry already holds `VAMP`, `VTOP` and `VBASe` for the channel. Don't re-capture.
2. **Read Vamp**, not Vtop: the Phase 6 check read Vamp 3.0037 V, Vtop 2.9774 V, Vbase −26.3 mV on this scope.
3. Vbase may jump between two values tens of mV apart from one refresh to the next. Phase 6 saw −26.3 mV and +43.3 mV alternating. That was recorded as observed, not explained. Note it if you see it; it is not a fail on its own.
4. CH1 and CH2 may show the same Vamp, Vtop and Vbase on the Result panel to every digit, even though their CSVs differ. V7R-002 saw this. It is not a fail (PLAN "After V7R-002 S1" §4).

**Pass:** **Vamp = 2.91 V to 3.09 V** (3 Vpp ± 3 % **[own]**) on every channel in use.
**Record:** `validation.notes`: "V4 Vamp CH<n> = <value> V".

## V5 — Noise check: what the board and its ground add

**Why.** A long or looping ground picks up noise from the switching charger. It rides on every level as a fuzzy band. The scope and probes show some noise even with no board (about 5 mV sd on our scope at the reference settings). So V5 measures in two parts, and `noise_floor.py` works out the difference:

- **V5a, control:** both probes on the scope's Cal ground, no board.
- **V5b, DUT:** both probes on this arm's ground point, board powered.

**Run V5 once per arm** (S1 and S2 each), because the ground point is different for each arm. Do V5a and then V5b in the same session, with the same scope settings. **Don't change any scope setting between V5a and V5b**, or the tool refuses to compare them.

1. **Settings.** Set both channels to the card's channel settings. For the reference settings (`known-good-reference.md` step 3):
   ```
   q ':CHANnel1:DISPlay ON'; q ':CHANnel2:DISPlay ON'
   q ':CHANnel1:SCALe 0.5'; q ':CHANnel2:SCALe 0.5'; q ':CHANnel1:OFFSet -1.65'; q ':CHANnel2:OFFSet -1.65'
   q ':CHANnel1:BWLimit OFF'; q ':CHANnel2:BWLimit OFF'
   q ':TIMebase:MAIN:SCALe 1e-5'
   q ':TRIGger:MODE EDGE'; q ':TRIGger:EDGE:SOURce CHANnel1'; q ':TRIGger:SWEep AUTO'
   q ':CHANnel1:SCALe?'; q ':CHANnel2:SCALe?'; q ':CHANnel1:OFFSet?'; q ':CHANnel2:OFFSet?'; q ':CHANnel1:BWLimit?'; q ':CHANnel2:BWLimit?'; q ':TIMebase:MAIN:SCALe?'; q ':ACQuire:MDEPth?'; q ':TRIGger:SWEep?'; q ':SYSTem:ERRor?'
   ```
   **CHECK:** in the terminal, `5.000000E-01` twice, about `-1.65` twice, `OFF` twice, `1.000000E-5`, `1.0000E+04`, `AUTO`, `0,"No error"` *[facts: V/div, Offset, BW limit, Timebase, Acquisition]*. Sweep has to be **AUTO**: a tip on ground gives nothing to trigger on, and AUTO keeps the trace updating.
2. **Vpp on the panel** (for the record only): `q ':MEASure:ITEM VPP,CHANnel1'; q ':MEASure:ITEM VPP,CHANnel2'`. Vpp is not the pass test: it swings too much from one capture to the next.
   **CHECK:** the Result panel on the scope screen shows `Vpp(C1)` and `Vpp(C2)`, each with a number. If one is missing, add it from the scope's measure menu by hand and write the button path in REPORT.

### V5a — control, no board

3. Put **both probe tips and both ground springs on the Cal ground terminal** on the scope's front panel (not the Cal signal terminal). No probe touches the board. A tip or spring may go on an alligator clip on the Cal ground terminal instead of touching it directly.
4. Capture, then press **RUN/STOP** once:
   ```
   python3 tools/lab/capture.py --test <V7R-NNN> --arm val_V5ctl --items VPP --session lab/log/<YYYY-MM-DD_sNN>.yaml
   ```
   **CHECK:** in the terminal, the output ends `The scope is left STOPPED.` and lists a `.csv`. Note the `.csv` name.

### V5b — on this arm's ground point, board powered

5. **Unplug the board.** Put each probe's **tip and its spring on the same ground point**: the one this arm uses in V6. Land the ground first, then the tip.
   - **S1 (master end), v6:** the soldered wire on pad **C**. The tips and springs touch the wire, as the springs will in the reference.
   - **S1 (master end), v7:** pad **C** (C9.1, one end of capacitor C9).
   - **S2 (BQ end), v6 or v7:** pad **F** (C21.2, the end of C21 farther from U5). See the bridging warning in V6. If a tip and a spring can't both sit on that small pad, put the spring on pad F and the tip on the nearest other ground pad, **R32.2** (one end of resistor R32, 3.44 mm from U5.6). It is not marked in the pictures, so find it in the layout first. Write down which pads you used. That fallback is our suggestion **[own]**.

   **CHECK:** under the microscope, each tip and spring sits on the ground point above, and nothing touches an **X** pad. The board is still unplugged.
6. Power the board: plug in the main-board USB-C.
   **CHECK:** on v6 with `v6-ref` and no sensor PCB, the board display shows "Sensor init failed!". That is expected.
7. Capture, then press **RUN/STOP** once:
   ```
   python3 tools/lab/capture.py --test <V7R-NNN> --arm val_V5 --items VPP --session lab/log/<YYYY-MM-DD_sNN>.yaml
   ```
   **CHECK:** in the terminal, the output ends `The scope is left STOPPED.` and lists a `.csv`. Note the `.csv` name.

### V5 result

8. Run the tool on the two CSVs (both are in `lab/captures/<V7R-NNN>/`):
   ```
   python3 tools/lab/noise_floor.py --ctl lab/captures/<V7R-NNN>/<YYYY-MM-DD>_<V7R-NNN>_val_V5ctl_<nn>.csv --dut lab/captures/<V7R-NNN>/<YYYY-MM-DD>_<V7R-NNN>_val_V5_<nn>.csv
   ```
   It prints, per channel, the average, the sd, the spread (max − min) and the excess noise, all in mV. Then PASS or FAIL, and a `validation.V5` block to paste into the log. If it refuses because the sample interval or the point count differ (the time between samples, or the number of samples), a setting changed between V5a and V5b: redo both. If it warns that the smallest level step differs (the size of one step in the sample values), the V/div probably changed: check the settings and redo both.

**Pass:** **excess noise ≤ 5 mV rms on each channel** **[own]**. Why 5 mV: noise of 5 mV rms is about 14 mV from peak to peak, which is below the 20 mV difference in the low level (V_OL) that our measurements need to tell apart (`test-workflow-audit.md` §4.7). If it fails, the ground is too long or loops near the charger. Fix it before measuring anything tens of mV in size. Never raise the limit.

**Scope sanity check [own]:** at the reference settings above, the control sd should be between **2.5 and 10 mV** on each channel (half to double the ≈ 5 mV seen in V7R-001). Outside that band, recapture V5a with the flagged channel on an alligator clip on the Cal ground terminal, and keep the flagged capture in the record. If the clip control is flagged too, stop. The tool prints a flag when it is outside the band; at other settings the flag does not apply, and the control sd is just recorded.

**Record:** paste the tool's block as `validation.V5`. It holds four per-channel values: `ctl_sd_mV` (control sd), `dut_sd_mV` (board sd), `excess_rms_mV` (excess noise) and `offset_mV` (the zero offset: the control's average). Optionally add `vpp_panel_mV`, the panel Vpp of the V5b capture. Put both PNG names in `validation.notes`. The zero offset is used again in `known-good-reference.md` step 9.

## V6 — Ground method

Use the shortest ground the probe can land: a **ground spring**, or a wire of **≤ 10 mm** **[own]**.

| Probing at | Ground point | Distance (edge to edge) | Source |
|---|---|---|---|
| BQ end: pads **D/E** (U5 pins 6/5), v6 **and** v7 | pad **F** (C21.2; C21 is 4.7 µF, 0603-size pad) | **2.64 mm** on both boards | *[facts: PCB probe points]* |
| Master end: pads **A/B** (test pads TPIO43/44), v6 | the **soldered wire** on pad **C** (U2.14, a ground hole of the T-Display header). The springs touch the wire about 8–9 mm from C | pad C is 8.26 mm from A/B | *[facts: PCB probe points]*; PLAN "After V7R-001" §2 |
| Master end: pads **A/B** (test pads TPIO43/44), v7 | a **spring straight on pad C** (C9.1, one end of the 100 nF capacitor C9). No soldering on v7 | 3.05 mm | *[facts: PCB probe points]*; user decision, 2026-10-20 |

> **Bridging warning (C21).** Pad F (C21.2) is ground, but the other end of the same capacitor (C21.1, an **X** pad in the pictures) is **`Protected_VBUS`**, USB power. One end of C20 next to it (C20.1, the other **X** pad) is `Protected_VBUS` too. A spring or wire touching both ends of C21 shorts the charger input to ground. Land the ground on **pad F, on the side of the pad away from the X pad**, with the board **unplugged**. Look at it under the microscope before you power on.

- Don't use TP4 as a "same ground" on both boards. It is 6.85 mm from U5 on v6 but 12.09 mm on v7 *[facts: PCB probe points, v6 names]*.
- Whether a spring stays on a 0603 pad has not been tried yet. If it won't stay, use a ≤ 10 mm wire to the same pad and record the length.
- Use the **same ground type and length** on every board you will compare (the same-ground-length rule, `known-good-reference.md`). The one exception is the master end: v6 uses the wire and v7 a spring. A v6–v7 comparison there is labelled **"unequal ground"**, and it counts only when V5 passed at S1 on **both** boards.
- On v6 the soldered wire is a board change. The card lists it in `hardware_config`.

**Pass:** recorded.
**Record:** `validation.V6_ground: {method: spring | wire, point: <pad>, length_mm: <n>}`, per probe if they differ. Examples: v6 S1 `{method: wire, point: U2.14, length_mm: <distance from where the springs touch the wire to pad C>}`; S2 `{method: spring, point: C21.2, length_mm: <n>}`.

## V7 — Idle-high level on the DUT

The bus is idle here: on v6 with `v6-ref` and no sensor PCB, the firmware halts at start-up ("Sensor init failed!") and sends nothing more. V7 reads the level the pull-ups hold.

1. **Unplug the board.** Move the probe tips onto the measurement points for this arm: CH1 (SDA) on pad **A** (S1) or **D** (S2), CH2 (SCL) on pad **B** (S1) or **E** (S2). The grounds stay as in V6.
   **CHECK:** under the microscope, each tip sits on its lettered pad, the grounds are as in V6, and nothing touches an **X** pad. The board is still unplugged.
2. Power the board: plug in the main-board USB-C.
   **CHECK:** the board display shows "Sensor init failed!".
3. Edge trigger on CH1, sweep AUTO:
   ```
   q ':TRIGger:MODE EDGE'; q ':TRIGger:EDGE:SOURce CHANnel1'; q ':TRIGger:SWEep AUTO'
   q ':TRIGger:MODE?'; q ':TRIGger:EDGE:SOURce?'; q ':TRIGger:SWEep?'; q ':SYSTem:ERRor?'
   ```
   **CHECK:** in the terminal, `EDGE`, `CHAN1`, `AUTO`, `0,"No error"` *[facts: Trigger (edge), Trigger (common)]*. The channel settings are still V5's (0.5 V/div, offset −1.65 V, 10 µs/div).
4. **Vpp on the panel**, for each channel in use:
   ```
   q ':MEASure:ITEM VPP,CHANnel1'; q ':MEASure:ITEM VPP,CHANnel2'
   ```
   Vpp, not Vtop: on a flat trace Vtop and Vbase come back `9.9E37` (invalid) *[facts: Measurement (one value)]*. Vpp works on a flat trace, so it is a check that the trace is flat. It has no pass role.
   **CHECK:** the Result panel on the scope screen shows `Vpp(C1)` and `Vpp(C2)`, each with a number. If one is missing, add it from the scope's measure menu by hand and write the button path in REPORT.
5. Capture, then press **RUN/STOP** once:
   ```
   python3 tools/lab/capture.py --test <V7R-NNN> --arm val_V7 --items VPP --session lab/log/<YYYY-MM-DD_sNN>.yaml
   ```
   **CHECK:** in the terminal, the output ends `The scope is left STOPPED.` and lists a `.csv`.
6. **Session work (no operator action):** run the frame tool on the CSV:
   ```
   python3 tools/lab/i2c_frame.py lab/captures/<V7R-NNN>/<YYYY-MM-DD>_<V7R-NNN>_val_V7_<nn>.csv
   ```
   **CHECK:** it prints `mode: idle` (no edge in the record). If it prints `mode: frame`, the bus was not idle during the capture: redo steps 5 and 6, and write in REPORT what the board display showed.

**Pass:** the tool's **mean of all samples is 3.135 V to 3.465 V** (3.3 V ± 5 %) on every channel in use. This catches a ×10 ratio error. It is the check Phase 23 lacked.
**Record:** paste the tool's `validation.V7_idle_high_V` line, for example `{CH1: 3.303, CH2: 3.290}`, and its `values_csv` block under the capture's log entry. The panel Vpp values are already in that entry, from `capture.py`.

## Decode setup (before V8, every scope session)

The scope's decode does not come up ready. In V7R-002 the bus status was Off and both thresholds were 0.00 V, and `:BUS1:MODE IIC` did not switch it on *[facts: I²C decode]*. So set it in the menu, by hand, in every scope session. There are no SCPI commands here for Bus status, the thresholds or R/W: they have not been tried on this scope.

1. On the scope screen, open the **function navigation icon** at the lower left → **Decode** → the **Decode 1** tab. Set these fields:

   | Field | Set to |
   |---|---|
   | Bus type | I2C |
   | Bus status | **On** |
   | Clock | CH2 |
   | SDA | CH1 |
   | Format | Hex |
   | SCL Thre | **1.65 V** |
   | SDA Thre | **1.65 V** |
   | R/W | **With** (so the byte shows as `d6`; Without shows the 7-bit address, `6b`) |

   Leave the other fields as they are (at V7R-002 they were Label On, Exchange SCL/SDA, Event table Off).
   **CHECK:** on the scope screen, before you close the menu, the Decode 1 tab shows every field as in the table. Bus status **On** and R/W **With** matter most, because no command can read them back: `:BUS1:MODE?` reads `IIC` even with Bus status Off.
2. Close the menu and run:
   ```
   q ':BUS1:MODE?'; q ':BUS1:IIC:SCLK:SOURce?'; q ':BUS1:IIC:SDA:SOURce?'; q ':BUS1:THReshold? SDA'; q ':BUS1:THReshold? SCL'; q ':SYSTem:ERRor?'
   ```
   **CHECK:**
   - In the terminal: `IIC`, `CHAN2`, `CHAN1`, `1.650000E0`, `1.650000E0`, `0,"No error"` *[facts: I²C decode]*.
   - On the scope screen, the decode band (the row labelled **B1** / **I2C** at the left edge) is there.

**Pass:** both CHECKs.
**Record:** in `validation.notes`: "Decode setup by menu: Bus status On, SCL/SDA Thre 1.65 V, R/W With", plus any field that was not as listed before you changed it.

## V8 — Contact check: I²C decode

Needle probes can sit on a pad without making contact. Decode proves they do.

Why this trigger: a trigger on an I²C START fires at power-up on something that is not I²C (V7R-002: the ESP32's start-up serial output on the SDA pin), and the bus carries other frames after the 0x6B frames. So V8 triggers on the BQ24195's address, 0x6B write, and uses SINGLE, which keeps the first such frame and stops *[facts: Trigger (I²C)]*.

1. **Address trigger:**
   ```
   q ':TRIGger:MODE IIC'; q ':TRIGger:IIC:SCL CHANnel2'; q ':TRIGger:IIC:SDA CHANnel1'
   q ':TRIGger:IIC:WHEN ADDR'; q ':TRIGger:IIC:AWIDth 7'; q ':TRIGger:IIC:ADDRess 107'; q ':TRIGger:IIC:DIRection WRITe'
   q ':TRIGger:MODE?'; q ':TRIGger:IIC:SCL?'; q ':TRIGger:IIC:SDA?'; q ':TRIGger:IIC:WHEN?'; q ':TRIGger:IIC:AWIDth?'; q ':TRIGger:IIC:ADDRess?'; q ':TRIGger:IIC:DIRection?'; q ':SYSTem:ERRor?'
   ```
   107 is 0x6B in decimal. **CHECK:** in the terminal, `IIC`, `CHAN2`, `CHAN1`, `ADDR`, `7`, `107`, `WRIT`, `0,"No error"`.
2. **20 µs/div and SINGLE:**
   ```
   q ':TIMebase:MAIN:SCALe 2e-5'; q ':TRIGger:SWEep SING'
   q ':TIMebase:MAIN:SCALe?'; q ':TRIGger:SWEep?'
   ```
   Why 20 µs/div: the trigger fires at the R/W bit, about 80 µs after the frame's START. At 10 µs/div the START falls just before the record, and the decode band then shows no labels. At 20 µs/div it is inside *[facts: Timebase]*. **CHECK:** in the terminal, `2.000000E-5`, `SING`.
3. **Replug** the main-board USB-C: unplug it, wait a second, plug it back in. Leave the probes where they are. Then run `q ':TRIGger:STATus?'`.
   **CHECK:**
   - In the terminal: `STOP` (the scope triggered once and stopped).
   - On the scope screen, in the decode band: **`Write:d6`** then **`A:0`**. `Write:d6` is the address byte D6 (0x6B with the write bit); `A:0` is the ACK, the 9th bit, low.

   If the status is not `STOP`, or the labels are not there: run step 2 again and replug again. **Stop rule:** no `d6` after **3 replugs** → stop, V8 fails, and report what the decode band and the status showed.
4. Capture (don't press RUN/STOP after it: the scope stays stopped until V9 arms the trigger again):
   ```
   python3 tools/lab/capture.py --test <V7R-NNN> --arm val_V8 --items VPP --session lab/log/<YYYY-MM-DD_sNN>.yaml
   ```
   **CHECK:** in the terminal, the output ends `The scope is left STOPPED.` and lists a `.png`. The PNG shows the decode band with `Write:d6` and `A:0`. After a fired SINGLE the logged sweep can read `NORM` or `AUTO`; the check is the `STOP` status. An SCPI error recorded `after: connect` was queued by an earlier terminal command: note it in REPORT and go on.
5. **Back to 10 µs/div** for V9:
   ```
   q ':TIMebase:MAIN:SCALe 1e-5'; q ':TIMebase:MAIN:SCALe?'
   ```
   **CHECK:** in the terminal, `1.000000E-5`.

**Pass:** the decode band on the scope screen showed `Write:d6` then `A:0` (for the BQ24195, 7-bit address 0x6B, write). Repeat V8 after any bump or reseat, and at the start of every day.
**Record:** `validation.V8_decode_ok: true`, and in `validation.notes`: "V8 decode Write:d6 then A:0 (<PNG name>, 20 µs/div, address trigger 0x6B write)".

## V9 — Reference measurement

Run `known-good-reference.md` at the start of a campaign, and again whenever the probes, the ground method or the scope settings change.

**Pass:** within the spec in that procedure.
**Record:** `validation.notes`: "V9 <card ID>, <date>"; or "V9 not due, last run <card ID>".

---

## Closing the validation

- Set `validation.passed: true` only when V1–V8 and the decode setup pass (and V9 when it is due). Any fail: `passed: false`, stop, and fix the setup.
- **Steps not done.** When a fail stops the validation, write each step you did not run as `{not_run: "<reason>"}` in place of its value, for example `V7_idle_high_V: {not_run: "V5 failed"}`. This is allowed **only** with `passed: false`. With `passed: true`, the validator reports an error.
- **One log per arm.** A card that runs S1 and S2 writes two session logs: `_s01` for S1 and `_s02` for S2. Each has its own `validation` block.
  - V1–V4 run once, at the start of the session, and are recorded in the first log.
  - The second log records a fresh V2 read-back, and `validation.notes` says "V1, V3, V4: see `<first log>`".
  - V5–V9 run again for the second arm and go in the second log.
  - Give `capture.py` the right log every time with `--session lab/log/<YYYY-MM-DD_sNN>.yaml`. Without it, the tool writes to today's latest log.
- Run `python3 tools/lab/validate_log.py lab/log/<YYYY-MM-DD_sNN>.yaml` on each log. TODOs are reported as pending (exit 3), and the pre-commit hook only warns about them. Errors block.

## Fallback: saving to the USB stick

Use this only if the LAN capture can't run. `capture.py` is the normal path.

- **Memory CSV** (matches the LAN capture sample for sample): **Storage** (the lower-left function navigation icon, or the toolbar **Storage** button) → **Save** tab → **Choose** → "Save wave" → **DATA SOURCE** = MEMORY → **FORMAT** = \*.csv → **File Name** → **Save** *[facts: CSV save path (menu)]*. Its layout differs from the tool's CSV (header `CH1V,t0 =…, tInc =…,`, no time column).
- **Setup file:** **Storage** → **Save** → **Choose** → "Save setup" → **File Name** → **Save**. It writes an XML `.stp` file *[facts: Setup-file extension]*.
- **Screenshot:** **Choose** also lists "Save image". The rest of that path has not been recorded, so write down the labels you see. Over SCPI, `q ':SAVE:IMAGe:FORMat PNG'; q ':SAVE:IMAGe D:/<name>.png'` works *[facts: Save image to stick]*.
- The scope adds an index digit to every name (`name` → `name0`) *[facts: Scope-side filename limit]*. Keep names short; the 16-character limit for SCPI names has not been tested.
- Then move the stick to the Mac and ingest it, giving the Mac time of the save:
  ```
  python3 tools/lab/ingest_usb.py --src /Volumes/HANTEK --test <V7R-NNN> --arm <arm> --at <YYYY-MM-DDTHH:MM:SS> --files <names the scope showed>
  ```

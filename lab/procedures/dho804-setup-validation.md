# DHO804 setup validation (V1–V9)

Run this at the start of every scope session, before any number from that session is trusted. It is `test-workflow-audit.md` §4.2, made concrete for our Rigol DHO804 (firmware 00.01.05) and our probes.

**If any step fails, stop and investigate the setup. Never adjust an interpretation, a threshold or an "effective" parameter to make a reading fit.**

- **Who does what.** The debugger session relays each step to the operator as a §4.8 block (`lab/templates/instruction.md`), one step at a time, and fills the log. The operator does the physical steps and types the commands.
- **Where the numbers come from.** Every scope fact used here is a row of `docs/initiatives/test-workflow-setup/PLAN.md` → "Verified instrument facts", cited as *[facts: row]*. Tolerances marked **[own]** are ours, not a vendor's.
- **Recording.** Results go into the session log `lab/log/YYYY-MM-DD_sNN.yaml`, block `validation` (`lab/templates/log.yaml`). Validation captures use the arm `val_V<n>` (§4.4), for example `2026-11-04_V7R-012_val_V3_01.png`.
- **Terminal.** Every command runs in Cursor's integrated terminal, at the repo root.

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

- **Probe ratio by hand.** The DHO804 does **not** detect the Sensepeek SQ500. It left CH2 at `1` with the SQ500 attached, and the Cal signal read about 10× low *[facts: SQ500 attenuation]*. Set every channel's ratio yourself and read it back (V2).
- **Channel on, and the trigger on that channel, before measuring.** A measurement on a channel that is off, or that isn't the trigger source, returned `9.9E37` (invalid) *[facts: Measurement (one value)]*.
- **Every measured item goes on the Result panel while the scope is running, before any capture.** `capture.py` stops the scope and then asks for each value. In W6, the one item that was not already on the panel came back `9.9E37`, while the items on the panel were valid. **This is a hypothesis, not tested**: an item that isn't already being measured may have no value on a stopped trace *[facts: Capture-tool comparison, VPP observation]*. Following the rule costs nothing.
- **`capture.py` leaves the scope STOPPED.** After each capture, press **RUN/STOP** once so the scope runs again (the screen's status badge leaves STOP).
- **Never trust `:SAVE:STATus?`.** It returns `1` even when no file was written. `:SAVE:SETup` and `:SAVE:MEMory:WAVeform` fail silently on 00.01.05 *[facts: Save waveform to stick; Setup save / load]*. `capture.py` refuses to send them. Check that a file exists by listing it.
- **Clock.** The scope has no front-panel date/time setting. `capture.py` sets the clock from the Mac on every run and reads it back *[facts: Scope clock]*. Don't assume a time held across a power cycle. Don't assume any fixed offset between the USB stick's file times and the Mac either. `ingest_usb.py` tries both +0 and +60 min *[facts: Saved-file timestamps; Inputs for Phase 8]*.

### 0.5 Probes

| Probe | Ratio | Use | Source |
|---|---|---|---|
| Rigol stock probe | Switch on the probe body: set it to **10×** | Cal checks, references, all edge and V_OL work | *[facts: DHO804 Cal output]* |
| Sensepeek SQ500 | **Fixed 10:1**, no switch. Scope must be set to 10 by hand | Hands-free at fine pitch; edge and V_OL work | *[facts: SQ500 attenuation, bandwidth, tip capacitance]* |
| Sensepeek SQ10 | 1:1 | **Not for edge or V_OL work** | *[facts: SQ10 attenuation]* |

Ground springs are on hand for both the Rigol stock probe and the SQ500 *[facts: Ground springs]*. Use one wherever it reaches.

---

## V1 — Clock and starting settings

1. Power the scope on. Wait for the waveform screen.
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
3. **CHECK:** `:CHANnel<n>:PROBe?` prints `10`, and `:CHANnel<n>:DISPlay?` prints `1`.

**Pass:** the probe and the scope channel both say 10×, for every channel in use.
**Record:** `validation.V2_probe_ratio`, for example `{CH1: 10x/10x, CH2: "fixed 10:1/10x"}`. The scope setting comes first, then the probe (switch position, or "fixed 10:1" for the SQ500).

## V3 — Probe compensation, on the channel it will be used on

Do it once for each probe, **on the channel that probe will use**. Move the probe to the next channel only after its capture.

1. Clip the probe tip onto the **Cal** terminal on the front of the scope, and its ground clip onto the Cal ground terminal.
2. Set the channel, the timebase and an edge trigger on that channel:
   ```
   q ':CHANnel<n>:SCALe 1'; q ':CHANnel<n>:BWLimit OFF'; q ':CHANnel<n>:COUPling DC'
   q ':TIMebase:MAIN:SCALe 2e-4'
   q ':TRIGger:MODE EDGE'; q ':TRIGger:EDGE:SOURce CHANnel<n>'; q ':TRIGger:EDGE:SLOPe POSitive'; q ':TRIGger:EDGE:LEVel 1.5'; q ':TRIGger:SWEep AUTO'
   q ':CHANnel<n>:SCALe?'; q ':TIMebase:MAIN:SCALe?'; q ':TRIGger:EDGE:SOURce?'; q ':TRIGger:SWEep?'; q ':SYSTem:ERRor?'
   ```
   **CHECK:** `1.000000E+00`, `2.000000E-4`, `CHAN<n>`, `AUTO`, `0,"No error"` *[facts: V/div, Timebase, Trigger (edge), Trigger (common)]*. If the trace is off screen, press **AUTO** once, then check the four read-backs again.
3. Put **Vamp, Vtop and Vbase** for this channel on the Result panel (these are also V4's items), with the scope running:
   ```
   q ':MEASure:ITEM VAMP,CHANnel<n>'; q ':MEASure:ITEM VTOP,CHANnel<n>'; q ':MEASure:ITEM VBASe,CHANnel<n>'
   ```
   This is the set form of the verified query. Whether it adds the item to the panel has not been tested. **CHECK:** the Result panel on the screen shows `Vamp(C<n>)`, `Vtop(C<n>)` and `Vbase(C<n>)`, each with a number. If one is missing, add it from the scope's measure menu by hand and write the button path in REPORT.
4. Look at the square wave's top and corners. On a probe with a compensation trimmer, turn the trimmer with the plastic tool until the top is flat and the corners square, with no overshoot or rounding.
5. Capture:
   ```
   python3 tools/lab/capture.py --test <V7R-NNN> --arm val_V3 --items VAMP,VTOP,VBASe --session lab/log/<YYYY-MM-DD_sNN>.yaml
   ```
   **CHECK:** the output ends `The scope is left STOPPED.`, it has no `NOTE: … invalid` line and no clock `WARNING` line, and it lists a `.png`. Then press **RUN/STOP** once to run again.

**Pass:** flat top, square corners, no visible overshoot or rounding at 1 V/div in the PNG.
**Record:** `validation.V3_comp_png`: the PNG name (one per probe or channel; list them if more than one).

## V4 — Cal amplitude, per channel in use

The Cal output is a **1 kHz, 3 Vpp** square wave, about 0 → 3 V *[facts: DHO804 Cal output]*. Rigol gives no tolerance. ±3 % is ours **[own]**.

1. Use the V3 capture. Its log entry already holds `VAMP`, `VTOP` and `VBASe` for the channel. Don't re-capture.
2. **Read Vamp**, not Vtop: the Phase 6 check read Vamp 3.0037 V, Vtop 2.9774 V, Vbase −26.3 mV on this scope.
3. Vbase may jump between two values tens of mV apart from one refresh to the next. Phase 6 saw −26.3 mV and +43.3 mV alternating. That was recorded as observed, not explained. Note it if you see it; it is not a fail on its own.

**Pass:** **Vamp = 2.91 V to 3.09 V** (3 Vpp ± 3 % **[own]**) on every channel in use.
**Record:** `validation.notes`: "V4 Vamp CH<n> = <value> V".

## V5 — Shorted-tip noise floor, on the powered DUT

Do this with the board powered and running, at the V/div and BW-limit settings the measurement will use (the card's channel settings).

1. Set the channel to the measurement's V/div and BW limit, for example:
   ```
   q ':CHANnel<n>:SCALe 0.5'; q ':CHANnel<n>:BWLimit OFF'; q ':TRIGger:EDGE:SOURce CHANnel<n>'; q ':TRIGger:SWEep AUTO'
   q ':CHANnel<n>:SCALe?'; q ':CHANnel<n>:BWLimit?'; q ':TRIGger:EDGE:SOURce?'; q ':TRIGger:SWEep?'
   ```
   Sweep has to be **AUTO**: a shorted tip gives nothing to trigger on, and AUTO keeps the trace updating.
2. Put the probe **tip and its ground on the same ground point**, the one the V6 ground method uses. Land the ground first, with the board's power off, then power on.
   - At the BQ24195 (U5) end on v6 or v7, that point is **C21.2**. See the bridging warning in V6.
   - If the tip and the spring can't both sit on that one 0603 pad, put the spring on C21.2 and the tip on the nearest other GND pad, **R32.2** (GND net, 3.44 mm from U5.6). Write down which pads you used. That fallback is our suggestion **[own]**.
3. Add **Vpp** for this channel with the scope running: `q ':MEASure:ITEM VPP,CHANnel<n>'`. **CHECK:** `Vpp(C<n>)` is on the Result panel with a number.
4. Capture:
   ```
   python3 tools/lab/capture.py --test <V7R-NNN> --arm val_V5 --items VPP --session lab/log/<YYYY-MM-DD_sNN>.yaml
   ```
   Then press **RUN/STOP** once.

**Pass:** **Vpp ≤ 20 mV** **[own]**. If it is larger, the ground method is too long or loops near the charger. Fix it before measuring any tens-of-mV feature.
**Record:** `validation.V5_noise_floor_mVpp` (from the entry's `VPP` value, in mV), and the PNG name in `validation.notes`.

## V6 — Ground method

Use the shortest ground the probe can land: a **ground spring**, or a wire of **≤ 10 mm** **[own]**.

| Probing at | Ground point | Distance (edge to edge) | Source |
|---|---|---|---|
| U5 (BQ24195) pins 5/6, v6 **and** v7 | **C21.2** (4.7 µF, 0603-size pad) | **2.64 mm** on both boards | *[facts: PCB probe points]* |
| Master test points TPIO43/44, v6 | U2.14 (T-Display header pin, through-hole) | 8.26 mm | same |
| Master test points TPIO43/44, v7 | C9.1 (100 nF) | 3.05 mm | same |

> **Bridging warning (C21).** C21.1, the other end of the same capacitor, is **`Protected_VBUS`**. C20.1 next to it is `Protected_VBUS` too. A spring or wire touching both ends of C21 shorts the charger input to ground. Land the ground on the **outer end of C21.2, away from C21.1**, with the board powered off. Look at it before you power on.

- Don't use TP4 as a "same ground" on both boards. It is 6.85 mm from U5 on v6 but 12.09 mm on v7 *[facts: PCB probe points, v6 names]*.
- Whether a spring stays on a 0603 pad has not been tried yet. If it won't stay, use a ≤ 10 mm wire to the same pad and record the length.
- Use the **same ground type and length** on every board you will compare (the same-ground-length rule, `known-good-reference.md`).

**Pass:** recorded.
**Record:** `validation.V6_ground: {method: spring | wire, point: C21.2, length_mm: <n>}`, per probe if they differ.

## V7 — Idle-high level on the DUT

1. Probes on the measurement points (for example SDA on CH1, SCL on CH2), with the V6 ground. Board powered and running.
2. Set an edge trigger on the channel, sweep AUTO, and put **Vtop** on the panel, for each channel in use:
   ```
   q ':TRIGger:EDGE:SOURce CHANnel<n>'; q ':TRIGger:SWEep AUTO'; q ':MEASure:ITEM VTOP,CHANnel<n>'
   ```
   **CHECK:** `Vtop(C<n>)` shows on the Result panel for every channel in use.
3. Capture:
   ```
   python3 tools/lab/capture.py --test <V7R-NNN> --arm val_V7 --items VTOP,VBASe --session lab/log/<YYYY-MM-DD_sNN>.yaml
   ```
   Then press **RUN/STOP** once.

**Pass:** **3.135 V to 3.465 V** (3.3 V ± 5 %) on every channel in use. This catches a ×10 ratio error. It is the check Phase 23 lacked.
**Record:** `validation.V7_idle_high_V`, for example `{CH1: 3.29, CH2: 3.30}`.

## V8 — Contact check: I²C decode

Needle probes can sit on a pad without making contact. Decode proves they do.

1. Turn on bus 1 decode for I²C, with SCL and SDA on the channels you are using, and check it:
   ```
   q ':BUS1:MODE IIC'; q ':BUS1:IIC:SCLK:SOURce CHANnel2'; q ':BUS1:IIC:SDA:SOURce CHANnel1'
   q ':BUS1:MODE?'; q ':BUS1:IIC:SCLK:SOURce?'; q ':BUS1:IIC:SDA:SOURce?'; q ':BUS1:THReshold? SDA'; q ':BUS1:THReshold? SCL'; q ':SYSTem:ERRor?'
   ```
   **CHECK:** mode `IIC`; sources CH2 (SCL) and CH1 (SDA); both thresholds about **1.65 V** (V_DD/2, §4.1). Only `:BUS1:MODE?` has been verified on this scope (it read `PAR` with decode off) *[facts: I²C decode]*. If a value is wrong, set it in the scope's decode menu and write the button path in REPORT.
2. Trigger on an I²C START so each frame starts at the trigger:
   ```
   q ':TRIGger:MODE IIC'; q ':TRIGger:IIC:SCL CHANnel2'; q ':TRIGger:IIC:SDA CHANnel1'; q ':TRIGger:IIC:WHEN STAR'; q ':TRIGger:SWEep NORM'
   q ':TRIGger:MODE?'; q ':TRIGger:IIC:WHEN?'; q ':TRIGger:SWEep?'
   ```
   **CHECK:** `IIC`, `STAR`, `NORM` *[facts: Trigger (I²C)]*.
3. Look at the decode row on the screen.

**Pass:** the decoded address byte is the one the card expects. For the BQ24195 (7-bit address 0x6B), a write shows **`D6`**. Repeat this check after any bump or reseat, and at the start of every day.
**Record:** `validation.V8_decode_ok: true`, and the address byte seen, in `validation.notes`.

## V9 — Reference measurement

Run `known-good-reference.md` at the start of a campaign, and again whenever the probes, the ground method or the scope settings change.

**Pass:** within the spec in that procedure.
**Record:** `validation.notes`: "V9 <card ID>, <date>"; or "V9 not due, last run <card ID>".

---

## Closing the validation

- Set `validation.passed: true` only when V1–V8 pass (and V9 when it is due). Any fail: `passed: false`, stop, and fix the setup.
- Run `python3 tools/lab/validate_log.py lab/log/<YYYY-MM-DD_sNN>.yaml`. TODOs are reported as pending (exit 3), and the pre-commit hook only warns about them. Errors block.

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

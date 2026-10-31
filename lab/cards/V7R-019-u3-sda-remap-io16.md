---
test_id: V7R-019
title: "U3 drives SDA from GPIO43 / GPIO16 / GPIO43 (TPIO16 wired to the SDA net, the idle pad an input), rigid #1 on J6, 400 kHz: SDA low at TPIO43 and BQ / VCNL ACK"
status: pre-registered
created: 2026-10-29
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "self"      # run image u3-remap, built from lab/evidence/V7R-019/src/u3/ at the prereg commit (firmware.bin sha256 bd97d883…; binary committed beside it); env copied verbatim from V7R-014 u3-static (core 2.0.14, devkitc-1, qio_opi, 16 MB). Card delta, needs the user's approval before S6. End: revert to motion-play-v7-diag 166f5f40 (lab/evidence/V7R-018/diag-166f5f40.bin)
  firmware_env: "u3-remap"
  board_id: v7-B3              # v7 #0003 (STATE §6 naming); U3 die rev v0.2
  hardware_config: "As V7R-018 end (STATE §6), changed before any arm: new ~68 mm 26 AWG wire soldered on TPIO16 (/LED_DATA = U3 IO16, D5 WS2812B-MINI DIN, IC1 SN74AHCT125 1A; J3 strip unplugged), tinned far end → female-to-male Dupont → Nano A4 column (with green / TPIO43), so the SDA net gains IO16 and the LED_DATA loads in every arm. Rigid #1 moved J5 → J6 (SW1 ON = PCA 0x76, SW2 OFF; as V7R-013); J6 pigtail moved J6 → J5 (channel never opened by the image; red keeps the Nano GND link; blue row 15 / 10 kΩ, black 'V' rail). TPIO43 green / TPIO44 yellow → ~175 mm Dupont → Nano A4 / A5; Nano blank sketch, powered before and whenever the v7 is (V7R-008). No battery. USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano."
variable_changed: "Which U3 pad drives the SDA net: GPIO43 (pad 37, the v7 SDA pin) with GPIO16 an input, vs GPIO16 (via TPIO16 and the new wire) with GPIO43 an input. Set by serial command to the running image; same boot, same wiring, same far-end path (rigid #1 on J6), SCL on GPIO44 throughout."
structure: "A/B/A — a (GPIO43) / b (GPIO16) / a (GPIO43) in one boot by serial command, at S1 with no probe move between arms"
revert_on_null: "yes — on every outcome: unplug v7 and Nano, pull the TPIO16 Dupont out of the A4 column (wire stays soldered, free end insulated), re-power, flash diag 166f5f40. Removing the soldered wire: user's call, recorded"
---

# V7R-019 — U3 SDA from GPIO43 / GPIO16 / GPIO43

Map regions cut: **master: module/path** and **master: pin role** (is the elevated low specific to GPIO43's path, or present whenever U3 drives this net?), **master supply** (same U3, same rail, different pad), **slave: BQ × master** (moves the level with the far-end path present: the V7R-016 B3 confound), and **symptom identity** for the fix (VCNL must clear, decisioning §4.2). Card F in STATE §8; fix route (i) of the checkpoint @ V7R-017. User approved the TPIO16 wire (2026-10-29: "I'm ok with soldering a wire onto TPIO16, yes").

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | The ~0.54 kΩ low-side resistance belongs to GPIO43's own path (die driver, module path or pad-37 joint): with another U3 pad driving the SDA net, the low is normal (≤ ~0.1 V) | map: master: module/path; V7R-014 (GPIO44 49 mV), V7R-016, desk (d), V7R-017 |
| H2 | The elevated low appears whenever U3 drives this net (U3's supply/ground return relative to the bus, U3's controller/clock/core, or a net-side load only U3's context brings): GPIO16 also gives ~0.9 V | map: master supply, master: identity; V7R-014 left "pad vs SDA-net load" unseparated |
| H3 | BQ's and VCNL's NACK follows the low level: with the far-end path present and the low ≤ 0.25 V, both ACK | map: slave: BQ × master; F-14; V7R-013, V7R-016 |
| H4 | The NACK needs more than the level (e.g. U3's timing, or GPIO43 itself on the net): with a normal low from GPIO16, BQ or VCNL still NACK | map: master: timing; mux |
| M  | Measurement artefact: CH1 contact at pad A, trigger on the wrong frame, image or pad routing not as declared (read-back), the TPIO16 joint open (B would then not drive the net), or scope/log disagreement | always listed; §4.2 |

**Magnitude (argued).** Desk (d): U3's SDA low ≈ 545 Ω × I_total; with rigid #1 on J6 (R1 4.7 kΩ far end) the model gives ~892 mV (V7R-013 measured 898 mV). H1: GPIO16 is an ordinary pad (U3's GPIO44 ≈ 32 Ω, V7R-014; dev-board GPIO43 29.5 Ω and GPIO4 31.5 Ω, V7R-017), so V_OL(B) ≈ 1.6 mA × ~30–50 Ω ≈ 50–80 mV, plus wire, Dupont and breadboard (≲ 1 Ω, ≲ 2 mV). H2: V_OL(B) ≈ 0.85–0.95 V. The two are ~800 mV apart, so the thresholds below are wide.

## Confounds (declared; not separated by this card)
- **Path to the net differs.** In a, the driver is ~5.9 mm of copper from pad A. In b, it is IO16's own copper to TPIO16, ~68 mm wire, a Dupont joint, the A4 breadboard column, ~175 mm Dupont and the ~68 mm green wire back to pad A. The DC drop is small (above); edge shape and ringing differ. A b result is a property of "IO16 through this fixture", which is also the fix as it would be bodged.
- **Pulls follow the driver.** `Wire.begin()` enables the internal pull-up on its SDA pad (V7R-011); the idle pad is `INPUT` with no pulls. So the ~45 kΩ internal pull-up moves from GPIO43 to GPIO16 with the variable (≈ 73 µA, ≈ +40 mV on the H2 side at 545 Ω, ≈ 2 mV on the H1 side). Declared; it can't move a ~800 mV split.
- **LED_DATA loads.** D5 DIN and IC1 1A (CMOS inputs) sit on the SDA net through the new wire in all three arms. D5 may light in random colours during bus traffic (desk e). No firmware drives IO16 except this image (argued: `git grep` of v7-clean 90053af `firmware/` finds no pin-16 use; firmware/CONTEXT.md lists 16 as LED strip data). The wire is joined to the net only while u3-remap is on U3 (S6 before S7; End before the revert).
- **Hardware change before A1.** The new wire, the LED_DATA loads and the rigid move (J5 → J6) happen together before any arm. A1 is compared with A2, not with V7R-013. If A1 is not in the failing state (anchor), the card stops: that would itself be a result about the wire/loads, recorded as void with values.
- **Arms by serial command:** no reflash, no power cycle, no physical touch between A1, B and A2. Each mode change releases all three pads before routing the new SDA pad, so GPIO43 and GPIO16 are never outputs together.
- **Probe re-seat.** Probes come off for the soldering and go back on at S1: one full move, full validation V1–V8 (V9 not due: same probes and settings, V7R-002). CH2 at pad B (SCL) is recorded, not counted.
- **Timing:** captured in the CSVs, not evaluated (Planner relay 2026-10-24).

## Predictions and exclusions (written before the run)
Counted per arm (A1 = a, B = b, A2 = a): 3 SINGLE captures on the 0x6B write address trigger, 10 µs/div. Per capture: decoded byte and 9th bit; SDA V_OL on bits 5, 3 and R/W of D6 (`tools/lab/i2c_frame.py --expect D6`, cropped −30…+40 µs, as V7R-013). Arm value: V_OL = mean of the 9 bit-means. A = mean(A1, A2); Δ = V_OL(B) − A. ACK rates per arm from the `[remap]` lines spanning the arm's captures (≥ 50 cycles, counts reset at each mode change): BQ = bq/n, VCNL = min(v0, v1)/n.
Controls in every counted arm: V8 band shows `Write:d6`; `[regs]` at the mode change and every 50 cycles show the declared routing (a: GPIO43 out_sig 90, oe 1, od 1; GPIO16 out_sig 256, oe 0, wpu 0; sda_in_sel 43. b: GPIO16 out_sig 90, oe 1, od 1; GPIO43 out_sig 256, oe 0, wpu 0; sda_in_sel 16. GPIO44 out_sig 89 in both); tca = ina = pca = n (≥ 95 %); no reboot within the arm; each capture decodes `D6` and its 9th bit agrees with the log's BQ result for that arm; SCL period 2.50 ± 0.01 µs; CH1 between frames ≥ 3.135 V in each counted CSV (or in the arm's V8 capture if a counted CSV has no idle stretch).
Anchor: |A1 − A2| ≤ 20 mV; A1 and A2 ≥ 0.80 V; BQ ≤ 5 % and VCNL ≤ 5 % in A1 and A2.

| Outcome (numeric; anchor and controls pass) | Excludes | Supports (weakly) |
|---|---|---|
| Row 1: V_OL(B) ≤ 0.25 V; BQ ≥ 95 % and VCNL ≥ 95 % in B | H2; H4 | H1; H3. Fix route (i) measured-supported on this unit (one board, one rigid) |
| Row 2: V_OL(B) ≤ 0.25 V; BQ ≤ 5 % or VCNL ≤ 5 % in B | H2; H3 for the device(s) that NACK, down to V_OL(B) | H1; H4 |
| Row 3: V_OL(B) ≥ 0.80 V; BQ ≤ 5 % and VCNL ≤ 5 % in B | H1 | H2; H3 not tested (level not moved) |
| Row 4: 0.25 V < V_OL(B) < 0.80 V | H1 and H2 as the whole of the low (each predicts the other end) | values to the map with the ACK rates; no exclusion of H3/H4 |
| Row 5: V_OL(B) ≤ 0.25 V or ≥ 0.80 V with BQ or VCNL between 5 % and 95 % in B, or BQ and VCNL split (one ≥ 95 %, the other ≤ 5 %) where Rows 1–3 don't place it | — | recorded as measured; values to the map |
| Anchor fails: \|A1 − A2\| > 20 mV, or A1 or A2 < 0.80 V, or BQ or VCNL > 5 % in A1 or A2 | — (result void) | M, or the wire / LED_DATA loads / rigid move changed the a state: stop and investigate before B is read |
| A control fails (decode not D6, 9th bit disagrees with the log, routing read-back not as declared, tca/ina/pca < 95 %, reboot, SCL period off, CH1 idle < 3.135 V) | — (that arm void; result void if any arm is void) | M |

## Setup
- Measurement log: `lab/log/2026-10-29_s01.yaml` (new session). Full validation at S1 per `lab/procedures/dho804-setup-validation.md` (V1–V8): V7 with u3-remap in boot mode `r` (all three pads released; replaces the relbus image), V8 in mode `a`. Validation must read `passed: true` before A1. Scope left in roll/PEAK by V7R-018: reset to the validation settings (timebase, acquisition normal, 10 kpts, decode display on).
- Scope (counted arms): as V7R-013 (0.5 V/div, −1.65 V, BW OFF, DC, 10 kpts; V8 at 20 µs/div, counted at 10 µs/div; trigger I²C ADDR 107 WRITE, SINGLE; decode set by hand this session). Captures `val_V8_<arm>`, counted `A1`, `B`, `A2` (`2026-10-29_V7R-019_*`).
- **Probe moves (user rule, 2026-10-25), in run order:** S1 → lifted (soldering, S2) → S1 re-seated (S9): **one full move**, flagged to the user; none between arms. Physical actions after S9: Mac-end USB plugs only.
- **Amendment (2026-10-30, before S3; user's proposal, accepted):** the TPIO16 wire is a grey male-to-female Dupont jumper (~180 mm before cutting), female end cut off, stripped, strands twisted and tinned, soldered to TPIO16; its male pin goes straight into the Nano A4 column at S7. Replaces "~68 mm 26 AWG + tinned end into a female-to-male Dupont": one contact fewer. Path TPIO16 → SDA is then ~180 mm jumper + A4 column + green's ~175 mm Dupont + ~68 mm green to pad A. Wire dressed (taped) so its weight doesn't pull on the pad. S3, S7 and End read with this wire.
- Picture for the solder pad: `lab/evidence/V7R-019/img/v7-tpio16.png` (G = TPIO16; A, B, C = S1), from tools/lab/probe_points at c2acffc. TPIO16: 2.0 mm round pad, front, 19.2 mm from TPIO43 at the same x (desk e).
- Readout: v7 and Nano serial logged by the session to `lab/captures/V7R-019/2026-10-29_V7R-019_{v7,nano}_01.txt`, `=== <arm>` markers. Mode commands `a` / `b` / `a` sent by the session on the v7 port.
- Image: u3-remap flashed by esptool at 0x10000 with `--flash_mode keep` (as V7R-014) from the committed binary (`shasum -c` first), with the TPIO16 wire not yet joined to the net. Banner `[remap] sketch=v7_sda_remap version=1.0` and boot mode r checked before S7.

## Procedure (physical steps for the operator)
The session runs every flash, SCPI command, capture and mode command; one instruction block per step.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S1 | Unplug the v7 at the Mac end, then the Nano at the Mac end | v7 PWR LED off; Nano LED off | LEDs |
| S2 | Lift both probes and their springs off the board; park them clear | no probe or spring touches the board | done |
| S3 | Solder ~68 mm 26 AWG wire on TPIO16 (G in the picture); tin the far end; far end touching nothing | pad silk-labelled "LED" (not "TCA_RESET", the pad above it); joint shiny, no bridge to neighbouring copper (look under the microscope) | wire colour, length, what you saw |
| S4 | DMM, board unpowered: TPIO16 ↔ TPIO43 resistance; TPIO16 ↔ pad C (GND) resistance | — | both readings |
| S5 | Rigid #1 out of J5, into J6; pigtail out of J6, into J5; check pigtail blue in row 15 and black in the 'V' rail | both connectors fully seated; rigid SW1 ON, SW2 OFF | positions |
| S6 | Plug in the Nano, then the v7 (TPIO16 wire still free). Session approves the delta with the user, flashes u3-remap, checks the banner | PWR LED; free end touches nothing | LEDs |
| S7 | Unplug the v7, then the Nano. Push the TPIO16 wire's tinned end into a female-to-male Dupont; male end into the Nano A4 column (with green) | joint firm; no pin in a rail | which hole, what is next to it |
| S8 | Plug in the Nano, then the v7 | PWR LED; D5 state | LEDs |
| S9 | Re-seat the probes at S1 (CH1 tip A, CH2 tip B, springs C); session runs V1–V8 | per the validation procedure | per the validation procedure |
| A1, B, A2 | Nothing (session: mode command, V8, 3 captures, ≥ 60 s per arm) | — | D5 state if it changes |
| End | Session sends `r`. Unplug the v7, then the Nano; pull the TPIO16 Dupont out of the A4 column, insulate its end; plug in the Nano, then the v7; session flashes diag 166f5f40 | TPIO16 wire touches nothing | bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- Pre-run decisions (2026-10-30), user: "1. approve 2. yes 3. about 3 hours" — u3-remap firmware delta approved; rigid J5→J6 and pigtail J6→J5 approved; bench time ~3 h. Session date rolled to 2026-10-30: log `lab/log/2026-10-30_s01.yaml` and file prefix `2026-10-30_V7R-019_*` (card text says 2026-10-29; deviation).
- S1–S2, operator: "1. both off 2. yes" — v7 and Nano unplugged at the Mac end, LEDs off; probes and springs lifted off S1 and parked clear.
- Fixture, operator (before S3): proposed soldering a cut Dupont jumper instead of 26 AWG + Dupont; "I have one, it's gray male-to-female, it is about 180mm". Amendment in Setup.
- S3–S4, operator: "1. Like, 170mm maybe 2. Lookks good 3. Nothing 4. about 2.1 M 5. same as the other one" — grey jumper ~170 mm after cutting, soldered on TPIO16; joint looks good; DMM TPIO16↔TPIO43 "Nothing" (wire not yet joined to the net); TPIO16↔C9.1 ~2.1 MΩ; item 5 wording recorded as given (meaning asked at S5).
- S4 correction, operator: "\"Nothing\" was a mistake - forget that response. \"2.1M\" and \"Same as the other one\" both were meant to refer to report items 3 and 4. So both the resistence measurements I took were around \"2.1 M\".\" — corrected: TPIO16↔TPIO43 ≈ 2.1 MΩ, TPIO16↔C9.1 ≈ 2.1 MΩ (DMM display 'M' = megohms).
- S5, operator: "1. Rigid is in J6, pigtail is in J5. SW1 is on, SW2 is off 2. all as it should be".
- S6, operator: "1. good 2. good" — Nano and v7 plugged in (Nano first); LEDs reported good (D5 state not separately described).
- S6 flash (session): `shasum -c` OK; esptool write_flash --flash_mode keep 0x10000 u3-remap/firmware.bin to /dev/cu.usbmodem14301 — Chip ESP32-S3 (revision v0.2), MAC 44:1b:f6:c5:58:c4, 272960 bytes, hash verified, 22:15:52. RTS reset 22:16:08: banner `[remap] sketch=v7_sda_remap version=1.0 … boot mode r`; mode r regs: GPIO43, GPIO16, GPIO44 all mcu_sel=1 out_sig=256 oe=0 wpu=0 wpd=0 ie=1; in: 43=1, 16=0, 44=1; sda_in_sel=56 (`lab/captures/V7R-019/2026-10-30_V7R-019_v7_01.txt`). Grey jumper not joined.
- S7–S8, operator (after asking to confirm A4 holds both green and grey): "1. next to green in A4 2. good, D5 off 3. good" — v7 and Nano unplugged, grey male pin into the Nano A4 column beside green, Nano then v7 plugged in; v7 PWR good, D5 off; Nano LEDs good.
- Validation (log `lab/log/2026-10-30_s01.yaml`): V1 AUTO pressed (left V7R-018 roll); MDEPth read 1 M, set 10 k. V2 CH1/CH2 probe 10, display 1. V3 CH1 operator: "flat, square corners"; Vamp 3.0037 V (val_V3_01). V3 CH2 operator: "flat, square corners"; Vamp 3.0208 V (val_V3_02). Clock Δ 0 s. V5a operator: "direct on Cal ground". V5b placement: operator: "All four things won't fit on C. We could use the capacitor above C9?" — springs on C (C9.1), tips on C10.1 (GND, as V7R-018's N); operator: "Looks good", "On, all good". V5 PASS: excess CH1 1.60, CH2 1.43 mV rms; ctl sd 5.42 / 4.98 mV.
- Deviation (session error, 22:48:14): the session wrote an arm marker through the logger's command file, so its text went to U3; the image read b, r, a, … from it and switched b→r→a→r→r→b→a within ~25 ms (each switch releases all pads first), ending in mode a with bus traffic. V5b (val_V5_01) was captured in mode a, not with an idle bus. Mode r restored 22:48:38. Markers are written to the log file directly from here on.
- V6–V7 placement, operator: "1. All looked good 2. Looks good" — tips moved C10.1 → A (CH1), B (CH2), springs on C; v7 replugged 22:54:24, boot mode r. V7 PASS: idle CH1 3.273 V, CH2 3.260 V (val_V7_01, bus idle).
- Decode setup by menu, operator: "1. none 2. Yes" (no field differed). `:BUS1:DISPlay ON` sent first (reads 1).
- V8 (mode a sent 22:56:02 instead of a replug; address trigger 0x6B write, 20 µs/div, SINGLE → STOP): val_V8_A1_01.png decode band `Write:80`, `Write:d6` with a red mark after it, `Write:ec` (session read). V8 passes on `Write:d6` (V7R-013 adaptation); 9th bit recorded from A1 captures.
- A1 (mode a, 22:56:02; regs: GPIO43 out_sig 90 oe 1 od 1 wpu 1; GPIO16 out_sig 256 oe 0 wpu 0 in 1; GPIO44 out_sig 89; sda_in_sel 43): `[remap]` n=580 at 22:57:01: tca=ina=pca=580, bq=0, v0=0, v1=0, last=02022; no reboot. Captures A1_01..03 (10 µs/div): D6, 9th high ×3, period 2.500 µs; bit V_OL [901.3 892.9 896.6] [900.6 892.3 894.4] [900.9 892.9 896.0] mV → A1 = 896.43 mV; idle CH1 −45..−25 µs 3.2744 / 3.2739 / 3.2740 V.
- B (mode b, 22:57:15; regs: GPIO16 out_sig 90 oe 1 od 1 wpu 1; GPIO43 out_sig 256 oe 0 wpu 0 in 1; GPIO44 out_sig 89; sda_in_sel 16): `[remap]` n=10 at 22:57:15.855 already tca=ina=bq=pca=v0=v1=10, last=00000; n=710 at 22:58:26: all six counts 710, no line with a non-zero code; no reboot; dwell 22:57:15–22:58:28 (73 s). Captures B_01..03: D6, 9th low ×3, period 2.500 / 2.501 / 2.500 µs; bit V_OL [115.3 104.0 108.2] [116.5 104.1 108.6] [114.8 104.1 109.0] mV → B = 109.40 mV; idle CH1 3.2743 / 3.2750 / 3.2746 V. capture.py NOTE on B_01: panel VPP CH1 invalid (panel item only; not counted).
- A2 (mode a, 22:58:28; regs as A1): n=630 at 22:59:31: tca=ina=pca=630, bq=0, v0=0, v1=0, last=02022; no reboot (two banners in the v7 log: S6 check 22:16 and V7 replug 22:54). Captures A2_01..03: D6, 9th high ×3, period 2.500 µs; bit V_OL [902.0 893.0 896.5] [900.4 892.8 896.9] [900.5 891.9 897.1] mV → A2 = 896.79 mV; idle CH1 3.2749 / 3.2740 / 3.2737 V.
### Measured values (from log; cite `lab/evidence/V7R-019/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** ...
- Revert-on-null done: ...
- Result commit: self

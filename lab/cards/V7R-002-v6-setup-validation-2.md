---
test_id: V7R-002
title: "Setup validation + known-good reference on v6 (`v6-ref`), second attempt"
status: run
created: 2026-10-21
prereg_commit: self
baseline:
  name: v6-ref
  firmware_commit: "4da1c67"
  firmware_env: lilygo-t-display-s3
  board_id: v6                # no physical label; the only v6 main board on the bench
  hardware_config: "v6 main board with T-Display-S3 in U2; mains USB-C charger into the main-board USB-C; data-only cable Mac ↔ T-Display USB-C; no battery; no sensor PCB. Board change: ~10 mm solid-core wire soldered to pad C (U2.14, top-side mound), GND net only (fitted during V7R-001)."
variable_changed: "none — instrument validation"
structure: single             # justified: no DUT variable is changed; the run validates the probe/ground/scope chain against a board expected to be healthy (known-good-reference.md, outcome rule). V7R-001 was void at V5; this card re-runs V1–V9 under the revised V5 rule (dho804-setup-validation.md @ 7ad3a4f) and the revised reference procedure (known-good-reference.md @ 598fb5b)
revert_on_null: n/a           # flashing v6-ref is the baseline, not a delta
---

# V7R-002 — Setup validation + known-good reference on v6 (`v6-ref`), second attempt

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H0 | The validated setup (two SQ500, CH1 SDA / CH2 SCL, per-arm ground, settings below) reads a healthy I²C bus inside the UM10204 pass table | `lab/procedures/known-good-reference.md` |
| E  | The pass-table expectation is wrong for v6 on `v6-ref` (the setup is fine but the expected numbers are not) | known-good-reference.md, outcome rule |
| M  | Measurement artefact: probe ratio, compensation, ground, contact or scope settings distort the readings (always listed) | §4.2 |

## Predictions and exclusions (written before the run)
Pass table per `known-good-reference.md` (V_DD = 3.3 V). Evaluated per arm (S1, S2). V1–V4 are run once and count for both arms.

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| V1–V8 all pass for the arm, and V9: V_OL (master-driven 0-bit, ACK excluded, as measured) ≤ 0.2 V, idle high 3.135–3.465 V on CH1 and CH2, 30→70 % rise time ≤ 300 ns on every SDA and SCL rising edge in the frame, decode `D6` then ACK | M (for this arm, these settings) | H0 |
| As row 1, but V_OL in 0.2 V < V_OL ≤ 0.4 V | — (passes UM10204; > 0.2 V on a working bus = investigate the setup [own heuristic]) | M |
| V1–V8 pass, and any V9 row out of its pass limit (V_OL > 0.4 V, or idle high outside 3.135–3.465 V, or any rise time > 300 ns, or decode ≠ `D6`+ACK) | H0 | M or E: stop; resolve before any v7 measurement (outcome rule). No limit is widened |
| Any of V1–V8 fails: V1 clock Δ > 10 s; V2 ratio ≠ 10; V3 not flat/square; V4 Vamp outside 2.91–3.09 V; V5 excess noise > 5 mV rms on either channel, or V5a control sd outside 2.5–10 mV on either channel; V7 outside 3.135–3.465 V; V8 decode not `D6` | — (result void for that arm: setup not validated) | M |
| No `D6` frame caught after 3 replugs, or capture.py returns `9.9E37` for an item with no CSV fallback, or noise_floor.py refuses the V5a/V5b pair twice | — (void: investigate) | M |

## Setup
- Measurement logs, one per arm: S1 `lab/log/2026-10-21_s01.yaml`, S2 `lab/log/2026-10-21_s02.yaml` (created by the first `capture.py --session` run for each). V1–V4 recorded in `_s01`; `_s02` records a fresh V2 read-back and "V1, V3, V4: see 2026-10-21_s01". Validation must read `passed: true` in the arm's log before any V9 number counts.
- Scope: Rigol DHO804, firmware 00.01.05, direct LAN 192.168.50.2.
- Probes: SQ500 #1 on CH1 (SDA), SQ500 #2 on CH2 (SCL), fixed 10:1, scope ratio 10, ground springs fitted, in PCBite arms.
- V5 and V9 channel settings: 0.5 V/div, offset −1.65 V, BW limit OFF, DC, 10 µs/div, 10 kpts, measure thresholds 30/70 % (V9).
- Arms (v6 picture `lab/procedures/img/v6-probe-points.png`):
  - S1, master end: CH1 on pad A, CH2 on pad B; springs on the soldered wire at pad C (U2.14); spring-to-C distance recorded (V6). Unequal ground vs v7.
  - S2, BQ end: CH1 on pad D, CH2 on pad E; spring (or ≤ 10 mm wire) on pad F (C21.2), on the side away from the X pad; length recorded (V6).
- V5 (V5a control on Cal ground, V5b on the arm's ground point, board powered) through V9 run per arm.

## Procedure (physical steps for the operator)
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| F | Session flashes `v6-ref` (4da1c67, lilygo-t-display-s3) from a scratch worktree via the data-only cable, main board powered | Board is v6; upload port is the T-Display | Upload result; display state |
| V1–V4 | Scope only, probes on Cal: AUTO, ratio, compensation (per channel), Cal amplitude | Read-backs as in the procedure | Read-backs, capture output, Vamp per channel, any hand-set button path |
| S1: V5–V8 | V5a on Cal ground → unplug → tips + springs on the wire at C → look → power → V5b; noise_floor.py; ground record; tips to A/B (unplugged) → look → power; idle high; decode | Read-backs; panel items present | capture output, ground length, Vtop per channel, decode byte |
| S1: V9 | Reference settings, SINGLE trigger, replug main-board USB-C, capture | `D6` then ACK on decode | capture output, decode as seen |
| S2: V2, V5–V8 | V2 read-back; V5a on Cal ground → unplug → tips + spring on F (away from X) → look → power → V5b; then tips to D/E (unplugged) → look → power; as S1 | as S1 | as S1 |
| S2: V9 | as S1 | as S1 | as S1 |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- Step F (main-board USB-C power in, before flashing), 2026-10-21: display: "It says: \"Motion play\", \"Initializing sensors\" \"error\" \"Sensor init failed!\"". Data-only cable Mac ↔ T-Display in: "Yes". Bench time: "2 hours".
- Step F, session: `/dev/cu.usbmodem14401` enumerated; `pio run -e lilygo-t-display-s3 -t upload` from a scratch worktree at `v6-ref` (4da1c67): "Wrote 1842416 bytes ... Hash of data verified." "Hard resetting via RTS pin..." [SUCCESS].
- V1: `*IDN?` → "RIGOL TECHNOLOGIES,DHO804,DHO8A282M00872,00.01.05"; `:SYSTem:ERRor?` → "0,\"No error\""; AUTO pressed: "yes". No setup loaded.

- V2: read-backs "10 1 10 1 0,\"No error\"" (CH1 PROBe?, DISPlay?, CH2 PROBe?, DISPlay?, ERRor?). Probe identity, operator: "I don't tell them apart.. why would I need to? One is plugged in to Ch1, the other plugged in to Ch2". Session: probes are identified by scope socket (CH1/CH2) for this card; neither is unplugged from its socket during the card.

- V3a (CH1 on Cal, CH2 parked on Cal ground): read-backs "1.000000E+00 / 2.000000E-4 / CHAN1 / AUTO / 0,\"No error\"". Panel: "For c1 I see Vamp, Vtop, Vbase, Vpp. For C2 the same ones." capture.py: wrote `2026-10-21_V7R-002_val_V3_01.{png,csv,setup.bin}`; "NOTE: 3 measurement(s) invalid (9.9E37 or no reply): VAMP CH2, VTOP CH2, VBASe CH2"; "The scope is left STOPPED."; no clock WARNING line. Shape: "Tops look flat, corners looks square". Log: VAMP CH1 3.0208 V, VTOP CH1 2.9757 V, VBASe CH1 −45.067 mV; scope_clock delta 0.0 s ok.

- V3b (CH2 on Cal, CH1 parked on Cal ground): read-backs "1.000000E+00 / 2.000000E-4 / CHAN2 / AUTO / 0,\"No error\"". Panel: "Same as before: Vamp, Vtop, Vbase, Vpp -- for both Ch1 and Ch2". capture.py: wrote `2026-10-21_V7R-002_val_V3_02.{png,csv,setup.bin}`; "NOTE: 3 measurement(s) invalid (9.9E37 or no reply): VAMP CH1, VTOP CH1, VBASe CH1"; "NOTE: channel settings differ from the last val_V3 entry: CH2.v_div_V: earlier val_V3 entry 0.5, scope 1.0; CH2.offset_V: earlier val_V3 entry -1.65, scope -3.3"; "The scope is left STOPPED." Shape: "tops flat and corners square". Log: VAMP CH2 3.0208 V, VTOP CH2 2.9757 V, VBASe CH2 −45.067 mV.
- Session observation (ai_read, val_V3_02): CH2 panel Vamp/Vtop/Vbase equal CH1's (val_V3_01) to every digit shown; Vpp differs (3.1361 V vs 3.1772 V); CSV level modes differ by channel (top 2.98853 / 2.98827 V; base −23.2 / −29.1 mV; sample step ≈ 2.5 mV). Recorded, not explained.

- S1 V5a (both tips + springs on Cal ground, no board contact; board powered): read-backs "5.000000E-01 / 5.000000E-01 / -1.650000E+00 / -1.650000E+00 / OFF / OFF / 1.000000E-5 / 1.0000E+04 / AUTO / 0,\"No error\"". capture.py: wrote `2026-10-21_V7R-002_val_V5ctl_01.{png,csv,setup.bin}`; "The scope is left STOPPED." (no NOTE lines). Board: "Still powered, showing the \"Sensor init failed!\" screen". Log: VPP CH1 22.667 mV, CH2 24.067 mV.

- S1 V5b (board unplugged → both tips + springs on the soldered wire at C → microscope → main-board USB-C in): spring position: "Like 4mm or 5mm I guess, hard to tell exactly. Maybe less." Display: "The \"Sensor init failed!\" screen". Data-only cable in: "Yes". capture.py: wrote `2026-10-21_V7R-002_val_V5_01.{png,csv,setup.bin}`; "The scope is left STOPPED." (no NOTE lines). Log: VPP CH1 24.067 mV, CH2 21.867 mV.
- S1 V5 result, session (`noise_floor.py` on val_V5ctl_01 / val_V5_01): CH1 ctl sd 5.04, dut sd 5.16, excess 1.11 mV rms; CH2 ctl sd 4.81, dut sd 4.71, excess 0.00 mV rms; offset CH1 −9.08, CH2 −13.02 mV; tool verdict "V5 PASS".

- S1 V6/V7 (board unplugged → tips to A (CH1) and B (CH2), springs on the wire → microscope → main-board USB-C in): spring position: "I estimate about 4mm". Display: "\"Sensor init failed!\" screen". Panel Vtop before capture: "Oh, I didn't look at the panel for Vtop after step 6. That instruction was in the \"Check\" section which I only read after following the \"Do:\" steps." capture.py: wrote `2026-10-21_V7R-002_val_V7_01.{png,csv,setup.bin}`; "NOTE: 4 measurement(s) invalid (9.9E37 or no reply): VTOP CH1, VBASe CH1, VTOP CH2, VBASe CH2"; "The scope is left STOPPED."
- S1 V7, session (CSV `val_V7_01`, all 10000 samples, bus idle): CH1 mean 3.3029 V (sd 3.18 mV, 3.2894–3.3197 V); CH2 mean 3.2902 V (sd 8.73 mV, 3.2441–3.3650 V). PNG: both traces flat, no edges; panel Vpp C1 26.866 mV, C2 74.000 mV.
- Deviation: V7 says "put Vtop on the panel" and passes on Vtop; panel VTOP is 9.9E37 on a flat (idle) trace, as CH2's Vtop/Vbase were on the flat parked trace in V3a. V7 value taken as the CSV mean (known-good-reference.md step 7 "Idle high: Vtop, or the mean of the samples before the START"). Limit unchanged. → procedure question for the Planner.
- Operator note on the instruction block: CHECK lines that fall between DO sub-steps were read only after the DO steps were done.

- S1 V8 attempt 1: decode read-backs "IIC / CHAN2 / CHAN1 / 0.000000 / 0.000000 / 0,\"No error\"" (MODE?, SCLK:SOURce?, SDA:SOURce?, THReshold? SDA, THReshold? SCL, ERRor?). Trigger read-backs "IIC, STAR, NORM". After replug: "I don't see a decode row. Where would I see it? You say screen, but there are three screens to look at: The scope screen, the v6 main board screen, the terminal where I ran the commands... I don't see anything about \"decode\" on any of them though." Display: "the usual \"Sensor init failed!\" screen". Session: thresholds read 0.000000, not ≈ 1.65 V (CHECK not met); no decode row shown on the scope. V8 not passed; redo via the scope's decode menu.

- S1 V8b (decode menu by hand): fields before: "Bus type: I2C, Bus status: off, Clock: Ch2, SDA: Ch1, Format: Hex, SCL Thre: 0.00v (1), SDA Thre: 0.00v (2), Label: On, Exchange: SCL/SDA (other option is SDA/SCL), R/W: Without (other option is \"with\"), Event table: off, Copy trig (a button)". Path/changes: "Changed Bus status to on, set both \"SCL Thre\" and \"SDA Thre\" to 1.65V. The other ones were already correct." (menu reached via the lower-left function navigation icon → Decode → Decode 1, per instruction). Read-backs "1.650000E0 / 1.650000E0 / IIC / NORM". After replug (sweep NORM): "I see the decode band, and one label from it is \"in frame\" on the scope display. It says \"write 74\"". Session: with sweep NORM the screen holds the last START of the boot burst, not the first; R/W "Without" shows the 7-bit address, so the BQ write would read `6B`, not `D6`. Not yet a V8 pass/fail.

- S1 V8c: "I went into the Decode screen, Decode 1 tab, and I set \"R/W\" to \"with\"". `:TRIGger:SWEep?` → "SING". After replug: "I don't think I see any decode band labels. There are tags over on the left of the scope screen saying \"B1\" and \"I2C\" but I'm not sure if they are the \"decode band\" per se." Display: "The usual \"Sensor init failed!\"". Then RUN/STOP pressed (per step). Whether the scope triggered: not reported.

- S1 V8d: `:TRIGger:SWEep?` → "SING"; status after replug: "STOP". capture.py: wrote `2026-10-21_V7R-002_val_V8_01.{png,csv,setup.bin}`; "The scope is left STOPPED". Session (CSV/PNG): SDA (CH1) edges at 0.24 F, 8.91 R, 17.58 F, 26.26 R, 34.94 F, 60.99 R, 69.66 F, 78.37 R µs (intervals multiples of ≈ 8.68 µs); SCL (CH2) has no crossing of 1.65 V (min 3.021 V); decode band shows no bytes.
- Interpretation (V7R-002): the single START trigger fires on a non-I²C waveform on SDA with SCL idle; the ≈ 8.68 µs unit interval equals one bit at 115 200 baud, consistent with ESP32-S3 boot-ROM UART0 TX on GPIO43. Not an I²C frame; V8/V9 single-START-after-replug recipe does not catch the BQ frame on this setup. → procedure question for the Planner.

- Decision (user, 2026-10-21): continue with an I²C address trigger (0x6B, write, SINGLE, replug) for V8 and V9 at S1 and S2, in place of the procedure's START trigger. Deviation from dho804-setup-validation.md V8 step 2 and known-good-reference.md steps 3/5; pass limits unchanged. Planner follow-up.

- S1 V8e (address trigger): read-backs "IIC / ADDR / 7 / 107 / WRIT / 0,\"No error\""; menu labels: "None"; status: "STOP"; decode: "Still just \"B1\" and \"I2C\" at the left edge of the scope display". capture.py: wrote `2026-10-21_V7R-002_val_V8_02.{png,csv,setup.bin}`; "The scope is left STOPPED."
- Session (CSV val_V8_02): SCL period ≈ 10 µs (rising edges −69.98 … +10.02 µs, 10.00 µs apart). SDA sampled at the 9 SCL rising edges −69.98 … +10.02 µs: 1 1 0 1 0 1 1 0 | 0 (= byte D6, then 9th-clock low). No START in the record (first SCL edge is falling, at −75.04 µs; record −80 … +80 µs). Scope decode band shows no labels.

- S1 V8f (20 µs/div, V8 only): replies "2.000000E-5, SING". Decode: "Decode band shows \"B1\" and \"I2C\" on the left side of the display, and \"Write:d6\" followed by \"A:0\" towards the center of the display". capture.py: wrote `2026-10-21_V7R-002_val_V8_03.{png,csv,setup.bin}`; "The scope is left STOPPED." Timebase back: "1.000000E-5". PNG agrees (Write:d6 | A:0).

- S1 V9 step 2 read-backs: "10 / 10 / 5.000000E-01 / -1.650000E+00 / 1.000000E-5 / 1.0000E+04 / IIC / IIC / ADDR / 7.000000E+01 / 3.000000E+01 / 0,\"No error\"". Operator: "I'm not sure if the response shows the 70/30 or not." No menu change.

- S1 V9 step 5 (panel before the replug): "Vtop(ch1): 3.2969V, Vbase(ch1): 62.800mV, Rise time (c1): Cur = 300.00ns, Avg = 300.00ns, Max = 300.00ns, Min = 300.00ns, Dev = 0.0000s, Cnt = 1." / "Vtop(ch2): 3.2628V, Vbase(ch2): 62.800mV, Rise time (c2): Cur = 100.00ns, Avg = 100.00ns, Max = 100.00ns, Min = 100.00ns, Dev = 0.0000s, Cnt = 1". Session: Vtop(C1) and Vbase(C1) equal the val_V8_03 panel values; Cnt = 1. Pre-capture panel state, not a V9 value.

- S1 V9 (address trigger 0x6B write, SINGLE, replug): status "STOP"; decode: "Only decode band labels are \"B1\" and \"I2C\" at the left edge of the display". capture.py: wrote `2026-10-21_V7R-002_S1_01.{png,csv,setup.bin}`; "The scope is left STOPPED." Log panel: VTOP CH1 3.2969 V, VBASe CH1 54.267 mV, RTIMe CH1 285.71 ns; VTOP CH2 3.2884 V, VBASe CH2 62.8 mV, RTIMe CH2 114.29 ns. Bench time left: "30 mins".
- S1 V9, session (CSV S1_01; values in log `2026-10-21_s01` entry S1): SDA at SCL rising edges 1 1 0 1 0 1 1 0 | 0. V_OL as measured, CH1 offset −9.08 mV beside it: bit 5 72.4 mV, bit 3 70.2 mV, bit 0 75.4 mV (sd 11–12 mV). Idle high after the frame: SDA 3.3025 V, SCL 3.2929 V. Rise 30→70 % (0.99→2.31 V): SDA 97.7–98.4 ns (5 edges), SCL 91.1–94.2 ns (10 edges). SCL period 10.0 µs. Panel RiseTime differs from CSV (C1 285.71 vs ≈ 98 ns; C2 114.28 vs ≈ 92 ns), Cnt = 1.

- Session stop after S1 (bench time): operator: "powered off, data cable in, probes on Cal ground"; "scope still on". S2 not started; continues in the next session with fresh V1–V4 (new scope session).

- S2 method note (session, 2026-10-21, before any S2 bench step): S2 runs on `lab/procedures/dho804-setup-validation.md` and `lab/procedures/known-good-reference.md` at 16c1ed1 (Phase 14: 27fb0ff, 1f1bd5d, 16c1ed1), which write the S1 deviations in as the method: (a) V7 from the CSV mean (`i2c_frame.py`, idle mode); (b) V8 and V9 on the I²C address trigger 0x6B write, SINGLE, replug. known-good-reference.md steps are cited by their numbers at 16c1ed1 (1–10). Why they changed: `docs/initiatives/test-workflow-setup/PLAN.md`, "After V7R-002 S1" §1–§8. Predictions and limits unchanged. S2 is a new scope session: V1–V4 run again and are recorded in the S2 log. S2 log is named by its session date, `lab/log/<date>_sNN.yaml` (sNN = next free number for that date); S2 runs on 2026-10-21, so the next free name is `lab/log/2026-10-21_s02.yaml`, the same as in the Setup line. Every S2 `capture.py` run gets `--session lab/log/2026-10-21_s02.yaml`. Bench time: "About 2 hours"; boards: "just the v6 board".

- S2 step F (main-board USB-C power in, before flashing): board is v6: "yes"; display: "\"Sensor init failed!\""; data-only cable in: "yes"; other: "nothing".
- S2 step F, session: `/dev/cu.usbmodem14401` enumerated; `pio run -e lilygo-t-display-s3 -t upload` from a scratch worktree at `v6-ref` (4da1c67): "Wrote 1842416 bytes (1182730 compressed) at 0x00010000 ... Hash of data verified." "Hard resetting via RTS pin..." [SUCCESS].
- S2 V1: `*IDN?` → "RIGOL TECHNOLOGIES,DHO804,DHO8A282M00872,00.01.05"; `:SYSTem:ERRor?` → "0,\"No error\""; AUTO pressed: "yes". No setup loaded. Display: "the usual \"Sensor init failed!\" screeb".
- S2 V2: read-backs "10 1 10 1 0,\"No error\"" (CH1 PROBe?, DISPlay?, CH2 PROBe?, DISPlay?, ERRor?). Other: "nothing".
- S2 V3a (CH1 on Cal, CH2 parked on Cal ground): read-backs "1.000000E+00 / 2.000000E-4 / CHAN1 / AUTO / 0,\"No error\"". Panel: "Vamp, Vtop, Vbase, Vpp, and RiseTime for both C1 and C2".
- S2 V3a: shape: "flat tops and square corners". capture.py: wrote `2026-10-21_V7R-002_val_V3_03.{png,csv,setup.bin}`; log `2026-10-21_s02.yaml` created; "NOTE: 3 measurement(s) invalid (9.9E37 or no reply): VAMP CH2, VTOP CH2, VBASe CH2"; "The scope is left STOPPED."; no clock WARNING line. Status after RUN/STOP: "TD". Log: VAMP CH1 3.0208 V, VTOP CH1 2.9757 V, VBASe CH1 −45.067 mV; scope_clock delta 0.0 s ok.
- S2 V3b (CH2 on Cal, CH1 parked on Cal ground): read-backs "1.000000E+00 / 2.000000E-4 / CHAN2 / AUTO / 0,\"No error\"". Panel: "What you described, all good". Hand-set: "All good".
- S2 V3b: shape: "flat tops and square corners,". capture.py: wrote `2026-10-21_V7R-002_val_V3_04.{png,csv,setup.bin}`; "NOTE: 3 measurement(s) invalid (9.9E37 or no reply): VAMP CH1, VTOP CH1, VBASe CH1"; "NOTE: channel settings differ from the last val_V3 entry: CH2.v_div_V: earlier val_V3 entry 0.5, scope 1.0; CH2.offset_V: earlier val_V3 entry -1.65, scope -3.3"; "The scope is left STOPPED."; no clock WARNING line. Status after RUN/STOP: "TD". Log: VAMP CH2 3.0037 V, VTOP CH2 2.9757 V, VBASe CH2 −28.0 mV.
- S2 V4 (from the V3 entries): Vamp CH1 3.0208 V (val_V3_03), CH2 3.0037 V (val_V3_04).
- S2 decode setup, menu (function navigation icon → Decode → Decode 1), fields as found: "Bus type: I2C, Bus status: on, CLK: Ch2, SDA: Ch1, Format: Hex, Scl Thre: 1.65V, Sda Thre: 1.65V, label: on, exchange: SCL/SDA, R/W: With, Event table: Off". Changes: "They were already set to the correct settings, I didn't have to change anything".
- S2 hand read-back (1), Decode 1 fields left as found, operator's own reading: Label "on", Exchange "SCL/SDA", Event table "Off".
- Session note: the session crossed midnight; captures from here on carry the date 2026-10-22 in their file names; the S2 log stays `lab/log/2026-10-21_s02.yaml` (session date of S2's start).
- S2 decode setup, terminal: "IIC / CHAN2 / CHAN1 / 1.650000E0 / 1.650000E0 / 0,\"No error\""; decode band present: "Yes". Scope or main-board USB-C off since V3b (2026-10-21 23:20 → 2026-10-22 ~13:50): "I don't think so".
- Session: decode 1 was found as set at S1 (a power cycle leaves Bus status Off and thresholds 0.00 V, dho804-setup-validation.md "Decode setup"), consistent with no scope power cycle in the gap; V1–V4 of S2 are kept. Interpretation, not checked.
- S2 V5a setup (both tips + springs on Cal ground, no board contact; board powered): read-backs "5.000000E-01 / 5.000000E-01 / -1.650000E+00 / -1.650000E+00 / OFF / OFF / 1.000000E-5 / 1.0000E+04 / AUTO / 0,\"No error\"". Panel Vpp(C1)/Vpp(C2): "Both are showing, yes". Display: "the \"Sensor init failed!\" screen".
- S2 V5a: capture.py: wrote `2026-10-22_V7R-002_val_V5ctl_01.{png,csv,setup.bin}`; "The scope is left STOPPED." (no NOTE lines). Log: VPP CH1 129.33 mV, CH2 23.867 mV; scope_clock delta 0.0 s ok.
- S2 V5a, session (`noise_floor.py --ctl val_V5ctl_01 --dut val_V5ctl_01`, control stats only; no DUT capture taken): CH1 mean −11.15, sd 11.17, max−min 138.73 mV; CH2 mean −13.56, sd 5.01, max−min 28.80 mV. Tool: "FLAG CH1 control sd 11.17 mV is outside the sanity band 2.5-10 mV". Settings are the reference settings (read-backs above). S1 control for comparison: CH1 sd 5.04, CH2 4.81 mV (log 2026-10-21_s01).
- Stop (relay §4, "control's noise outside the scope sanity band"; dho804-setup-validation.md V5 "Outside that band, stop and look at the scope and probes"). S2 V5b–V9 not run; probes never on the board in S2. Log `2026-10-21_s02` closed with `passed: false`, remaining items `not_run`.
- Operator, after the flag: "My concern is that the probes might not have been fully seated on the Cal ground, as it's a little challenging to seat them all in there and be sure that they are all touching the metal of it." Alligator clip on the Cal ground tab proposed by the operator; not used (changes the control fixture; method question for the Planner).
- Decision (user, 2026-10-22): "re-seat and redo V5a as a recorded deviation". Deviation from relay §4 (stop at once on the sanity flag); dho804-setup-validation.md V5 ("stop and look at the scope and probes before going on") is followed. Limits and band unchanged; val_V5ctl_01 stays in the record; V5 for S2 uses the redone control only if it is inside the band. Log `2026-10-21_s02` validation reopened (pending).
- S2 V5a re-seat (no clip, no scope setting changed): "Both Ch1 and Ch2 tips and springs seem properly seated now". Status badge: not reported.
- S2 V5a redo: capture.py: wrote `2026-10-22_V7R-002_val_V5ctl_02.{png,csv,setup.bin}`; "The scope is left STOPPED." (no NOTE lines). Status badge before the capture: not reported (log `trigger_status.before: AUTO`). Log: VPP CH1 195.27 mV, CH2 28.067 mV; settings as val_V5ctl_01.
- S2 V5a redo, session (`noise_floor.py`, control stats only): CH1 mean −9.76, sd 12.05, max−min 227.27 mV; CH2 mean −12.48, sd 4.93, max−min 35.67 mV. Tool: "FLAG CH1 control sd 12.05 mV is outside the sanity band 2.5-10 mV".
- Session (scratch script on the CH1 column; not a tool value): samples more than 40 mV from the median — val_V5ctl_02: 81 events, sd of the rest 9.89 mV; val_V5ctl_01: 51 events, sd of the rest 10.14 mV; S1 `2026-10-21_V7R-002_val_V5ctl_01`: 0 events, sd 5.04 mV. Event spacing irregular (≈ 0.3–10 µs).
- Stop: CH1 control outside the sanity band on both V5a captures, the second after re-seating. S2 V5b–V9 not run; probes never on the board in S2. Log `2026-10-21_s02` closed `passed: false`.
- S2 V5a used for S2 (user decision): `2026-10-22_V7R-002_dbg_ch1_01` — CH1 on an alligator clip to Cal ground, CH2 direct.
- S2 V5b (unplugged → both springs then both tips on the left half of pad F → main-board USB-C in): operator: "It's an incredibly tight space for all four probe points to be touching. I think I got them all on" / "All four are touching the pad I think." Clearance: "whatever the distance from the F pad to the X pads is, that's the clearance I suppose, because these probes are coming in from above." Data-only cable: "plugged in". Display: "the usual \"Sensor init failed!\"". capture.py: wrote `2026-10-22_V7R-002_val_V5_01.{png,csv,setup.bin}`; "The scope is left STOPPED." Log: VPP CH1 37.2 mV, CH2 47.133 mV.
- S2 V5 result, session (`noise_floor.py --ctl dbg_ch1_01 --dut val_V5_01`): CH1 ctl sd 5.25, dut sd 5.62, excess 2.00 mV rms; CH2 ctl sd 4.85, dut sd 5.43, excess 2.44 mV rms; offset CH1 −10.53, CH2 −11.69 mV; tool verdict "V5 PASS".
- S2 V6: springs directly on pad F (C21.2), left half; recorded as spring, length 0 mm.

### Measured values (from log; cite `lab/evidence/V7R-002/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** ...
- Revert-on-null done: n/a
- Result commit: self

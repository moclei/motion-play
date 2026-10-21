---
test_id: V7R-002
title: "Setup validation + known-good reference on v6 (`v6-ref`), second attempt"
status: pre-registered
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

### Measured values (from log; cite `lab/evidence/V7R-002/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** ...
- Revert-on-null done: n/a
- Result commit: self

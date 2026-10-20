---
test_id: V7R-001
title: "Setup validation + known-good reference on v6 (`v6-ref`)"
status: pre-registered
created: 2026-10-20
prereg_commit: self
baseline:
  name: v6-ref
  firmware_commit: "4da1c67"
  firmware_env: lilygo-t-display-s3
  board_id: v6                # no physical label; the only v6 main board on the bench
  hardware_config: "v6 main board with T-Display-S3 in U2, USB-C to the Mac, no battery, nothing on the sensor connectors unless already fitted (operator records at S1). No mods."
variable_changed: "none — instrument validation"
structure: single             # justified: no DUT variable is changed; the run validates the probe/ground/scope chain against a board expected to be healthy (known-good-reference.md, outcome rule)
revert_on_null: n/a           # flashing v6-ref is the baseline, not a delta
---

# V7R-001 — Setup validation + known-good reference on v6 (`v6-ref`)

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H0 | The validated setup (two SQ500, CH1 SDA / CH2 SCL, per-arm ground, settings below) reads a healthy I²C bus inside the UM10204 pass table | `lab/procedures/known-good-reference.md` |
| E  | The pass-table expectation is wrong for v6 on `v6-ref` (the setup is fine but the expected numbers are not) | known-good-reference.md, outcome rule |
| M  | Measurement artefact: probe ratio, compensation, ground, contact or scope settings distort the readings (always listed) | §4.2 |

## Predictions and exclusions (written before the run)
Pass table per `known-good-reference.md` (V_DD = 3.3 V). Evaluated per arm (S1, S2).

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| V1–V8 all pass for the arm, and V9: V_OL (master-driven 0-bit, ACK excluded) ≤ 0.2 V, idle high 3.135–3.465 V on CH1 and CH2, 30→70 % rise time ≤ 300 ns on every SDA and SCL rising edge in the frame, decode `D6` then ACK | M (for this arm, these settings) | H0 |
| As row 1, but V_OL in 0.2 V < V_OL ≤ 0.4 V | — (passes UM10204; > 0.2 V on a working bus = investigate the setup [own heuristic]) | M |
| V1–V8 pass, and any V9 row out of its pass limit (V_OL > 0.4 V, or idle high outside 3.135–3.465 V, or any rise time > 300 ns, or decode ≠ `D6`+ACK) | H0 | M or E: stop; resolve before any v7 measurement (outcome rule). No limit is widened |
| Any of V1–V8 fails (V2 ratio ≠ 10, V3 not flat/square, V4 Vamp outside 2.91–3.09 V, V5 Vpp > 20 mV, V7 outside 3.135–3.465 V, V8 decode not `D6`) | — (result void for that arm: setup not validated) | M |
| No `D6` frame caught after 3 restarts, or capture.py returns `9.9E37` for an item with no CSV fallback | — (void: investigate) | M |

## Setup
- Measurement log: `lab/log/2026-10-20_s01.yaml` (created by the first `capture.py` run). Validation must read `passed: true` before any V9 number counts.
- Scope: Rigol DHO804, firmware 00.01.05, direct LAN 192.168.50.2.
- Probes: SQ500 #1 on CH1 (SDA), SQ500 #2 on CH2 (SCL), fixed 10:1, scope ratio 10. Ground springs fitted.
- V9 channel settings (V5 runs at these): 0.5 V/div, offset −1.65 V, BW limit OFF, DC, 10 µs/div, 10 kpts, measure thresholds 30/70 %.
- Arms (v6 picture `lab/procedures/img/v6-probe-points.png`):
  - S1, master end: CH1 on pad A, CH2 on pad B, ground wire ≤ 10 mm to pad C (U2.14); length recorded.
  - S2, BQ end: CH1 on pad D, CH2 on pad E, ground spring (or ≤ 10 mm wire) on pad F (C21.2), clear of both X pads.
- V5–V8 are run per arm, because the ground point differs between arms (V5 uses the arm's ground point; V6 recorded per arm).

## Procedure (physical steps for the operator)
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| F | Plug v6 (only) into the Mac; session flashes `v6-ref` (4da1c67, lilygo-t-display-s3) from a scratch worktree | Board is v6; upload port is the T-Display | Upload result; boot banner on the display/serial |
| V1–V4 | Scope only, probes on Cal: AUTO, ratio, compensation (per channel), Cal amplitude | Read-backs as in the procedure | Read-backs, capture output, Vamp per channel, any hand-set button path |
| S1: V5–V8 | Board unplugged → ground wire on C, tips on A/B → look → power; noise floor, ground record, idle high, decode | Read-backs; panel items present | Vpp, ground length, Vtop per channel, decode byte |
| S1: V9 | Reference settings, SINGLE trigger, RIGHT button, capture | `D6` then ACK on decode | capture output, decode as seen |
| S2: V5–V8 | Board unplugged → spring on F (away from X), tips on D/E → look → power; as S1 | as S1 | as S1 |
| S2: V9 | as S1 | as S1 | as S1 |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- Step F (before flashing; firmware on the board unknown), 2026-10-20: "v6 confirmed". Display: "Motion play" title; boxes labelled "Boot", "Wifi", "MQTT", "Sens", "Done"; "Initializing sensors..."; "Error"; "Sensor init failed". "The display started and worked through each of the boxes until it got to \"Sens\", when it stopped and showed the error message." Operator note: no sensor PCB connected.
- Step F, session: after plug-in, no ESP32 serial port enumerated on the Mac (`ls /dev/cu.*` shows only Bluetooth ports; `system_profiler SPUSBDataType` lists no Espressif device).
- Step F power config (operator): "Main board is plugged in to a usb-c cable plugged into a standard plug socket (I don't know the ratings)". "The T-display USB-c is plugged into my mac via a cable with a \"data only\" function, so no power can pass through". Session: `/dev/cu.usbmodem14401` enumerated; `pio run -e lilygo-t-display-s3 -t upload` from a worktree at `v6-ref` (4da1c67): "Wrote 1842416 bytes ... Hash of data verified." Serial read for 12 s after reset: no output.
- S1 (post-flash + V1): display "on the previously mentioned screen, stopped at the \"Sensor init failed\" step". `*IDN?` → `RIGOL TECHNOLOGIES,DHO804,DHO8A282M00872,00.01.05`; `:SYSTem:ERRor?` → `0,"No error"`.

- S2 (V2): ":CHANnel1:PROBe?/DISPlay? and :CHANnel2:PROBe?/DISPlay?": "The first two both printed \"10\" and \"1\". The error one showed `0,\"No error\"`". Probes unmarked; "I tell them apart just by looking at them and seeing which sockets they are plugged into on the scope (CH1 or CH2)."

- S3 (V3/V4 CH1, CH1 on Cal): read-backs "`1.000000E+00`, `2.000000E-4`, `CHAN1`, `AUTO`, `0,"No error"`". "Result panel shows Vamp(C1), Vtop(C1), VBase(C1), Vamp(C2), Vpp(C2), Vpp(C1), Vtop(C2), Vbase(C2) -- some of them might have been there before we did this? Not sure". capture.py: wrote `2026-10-20_V7R-001_val_V3_01.{png,csv,setup.bin}`; "NOTE: 1 measurement(s) invalid (9.9E37 or no reply): VTOP CH2"; "The scope is left STOPPED."; no clock WARNING line. "The Ch1 square wave's top and corners.. look like squares I guess. There's a \"T\" tag on the top left of one of the waves, and on the right of the screen about halfway up a square wave"

- S4 (V3/V4 CH2, CH2 on Cal): read-backs "`1.000000E+00`, `2.000000E-4`, `CHAN2`, `AUTO`, `0,"No error"`". "CH1 is parked". capture.py: wrote `2026-10-20_V7R-001_val_V3_02.{png,csv,setup.bin}`; "NOTE: 3 measurement(s) invalid (9.9E37 or no reply): VAMP CH1, VTOP CH1, VBASe CH1"; "NOTE: channel settings differ from the session block: CH2.v_div_V: session 0.05, scope 1.0"; "The scope is left STOPPED." CH2 shape: "They look pretty much the same as CH1 had -- square"

### Measured values (from log; cite `lab/evidence/V7R-001/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: n/a
- Result commit: self

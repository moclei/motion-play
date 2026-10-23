---
test_id: V7R-003
title: "Fault re-established on v7 at `v7-clean`, L-Ph12 minimal repro, A/B/A"
status: pre-registered
created: 2026-10-22
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: motion-play-v7-diag
  board_id: v7-B3             # believed B3; user not certain of the B1/B2/B3 identity (2026-10-22). Recorded at S1 as "v7, believed B3"
  hardware_config: "v7 main board, no battery, nothing on J4/J5; J6: JST-SH 4-pin pigtail (loose wires at the far end; wires identified at S1 by continuity of GND to pad C, then position), far end 10 kΩ with one lead on pin 1 (+3.3 V), SDA (pin 3) and SCL (pin 4) wires dangling; USB-C Mac ↔ v7 J7 (data + power). No mods known."
variable_changed: "far-end DC path SDA → +3.3 V (10 kΩ) connected vs not connected; cable stays in J6"
structure: A/B/A
revert_on_null: n/a           # flashing v7-clean is the baseline, not a delta; firmware on the board before S2 is unknown and is recorded from its boot output at S2
---

# V7R-003 — Fault re-established on v7 at `v7-clean`, L-Ph12 minimal repro, A/B/A

Map region cut: **firmware: drift** (the stacked Ph23–25 init changes are reverted in `v7-clean`). Not cut: **firmware: env** (env and variant unchanged from the legacy runs). Also sets the v7 baseline that later cards cite.

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | The BQ NACK needs the stacked Ph23–25 init changes; on `v7-clean` the far-end SDA path gives no NACK | map: firmware: drift; F-6 (argued) |
| H2 | The symptom (STATE §1) holds at `v7-clean`: far-end SDA path → BQ X(2) on the TCA2 row; no path → '.' | STATE §1; L-Ph12 |
| M  | Readout artefact: wrong board or port, diag loop not entered, J6 not on TCA2, fixture contact | always listed |

## Predictions and exclusions (written before the run)
Counts are over the TCA2-row `BQ:` field in the first 10 complete iterations of each arm, after the iteration in progress at the change is dropped. Controls in every arm: BASE row `BQ:.`, and TCA2 row `INA:.` and `TCA:.`.

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| A1 and A2: BQ non-'.' in ≤ 1/10 each; B: `BQ:X(2)` in ≥ 9/10; controls pass | H1 (measured-refuted for firmware: drift) | H2 |
| A1 and A2: ≤ 1/10 non-'.'; B: `BQ:.` in ≥ 9/10; controls pass | H2 on this board at `v7-clean` | H1; M (board identity) stays open. No map change until board identity is checked. |
| A1 and A2: ≤ 1/10 non-'.'; B: `BQ:X(2)` in 2–8/10 | — (intermittent; contradicts STATE §2 Extent) | — ; extend B to 30 iterations, decide with the user |
| Any control fails in any arm; or A1 or A2 > 1/10 non-'.'; or any BQ code other than 2; or A2 differs from A1 by > 1/10 | — (result void) | M; stop and investigate |
| No `I2C BUS DIAGNOSTIC LOOP` banner after flashing, or no serial | — (setup void; no arm counts) | M |

## Setup
- Readout: serial at 115200 baud, logged continuously by the session to `lab/captures/V7R-003/2026-10-22_V7R-003_serial_01.txt` with the host time on each line (scratch logger on pyserial). Arm boundaries are the iteration numbers at which the operator reports each change done.
- Flash: `pio run -e motion-play-v7-diag -t upload` from a detached worktree at `v7-clean` (90053af), by the session.
- The diag loop runs because sensor init fails with nothing on J4/J5 and a cable-only J6 (main.cpp at v7-clean, `runBusDiagnosticLoop`).
- No scope. Probes stay on the scope's Cal ground.

## Procedure (physical steps for the operator)
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S1 | Unpowered: v6 off the bench (data-only cable out). v7 on the bench, no battery, J4/J5 empty. Pigtail into J6; find the GND wire by continuity to pad C (C9.1), then pin 1 / pin 3 / pin 4 by position. At the far end: 10 kΩ, one lead on pin 1 (+3.3 V); SDA and SCL wires dangling, touching nothing | Nothing conductive under the board; the free 10 kΩ lead touches nothing | Board markings; how the 10 kΩ joins pin 1; anything noticed |
| S2 | USB-C Mac ↔ v7 J7. Session logs the old firmware's boot output, then flashes | Session confirms the port, the flash and the diag banner | Anything seen on the board (LEDs) |
| A1 | Nothing; session logs ≥ 10 iterations | — | — |
| B  | Connect the free 10 kΩ lead to the SDA wire (cable pin 3); reply "done" at once | SCL wire still dangling | Anything noticed |
| A2 | Disconnect that lead from the SDA wire; reply "done" at once | Lead touches nothing | Anything noticed |
| S3 | Unplug USB-C from J7 | — | Bench state read-back |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- S1 (2026-10-23), operator: "1. Pin 1 is black, Pin 2 is red, Pin 3 is blue, Pin 4 is yellow 2. Yes, the red wire, Pin 2 3. The 10kohm resistor is a "through hole" type. It has both legs plugged in to a breadboard -- one leg is in the rail labelled for ground, one leg is in the rail labelled for voltage. I plan to insert pin 1 and pin 3 into the rails so that they are connected through the resistor. 4. [...] on that extra PCB material there is a QR code and the text "0003", indicating this was the 3rd board (of 5) from the order. That is how I can identify it, as #3."
- Board identity: panel marking "0003" on the breakaway rails (rails still attached). Link between "0003" and legacy "B3": not confirmed.
- S2, operator: "Black wire and resistor leg are on the same half of the rail. The others are hanging unconnected". Breadboard rail labelled "voltage" = +3.3 V (pin 1, black); rail labelled "ground" = SDA side of the 10 kΩ (blue goes there at B).
- S3, operator: PWR LED lit "Yes"; other LEDs "No".
- S3, firmware found on the board before flashing (session log `lab/captures/V7R-003/2026-10-23_V7R-003_serial_00_oldfw.txt`): banner line `I2C: 100 kHz, drive CAP_3, filter(7), pad-filter, internal pulls dis [Phase 24 null + Phase 25 bundle]`, DIAG_NO_WIFI, diag loop running; 15 iterations logged with the pigtail in J6 and no far-end path: TCA2 row `BQ:.` in all 15.
- S3 flash (session): `pio run -e motion-play-v7-diag -t upload` from worktree at 90053af, SUCCESS, hash verified, 2026-10-23 ~11:12. Log `..._serial_01.txt` from 11:12:32: banner `I2C: 400 kHz, default drive, no filters, default pulls [v7-clean]`, `I2C BUS DIAGNOSTIC LOOP` present, PCA summary ch 0/1/2 "(nothing detected)". Boot lines before `BQ24195 configured` not captured (port opened after them). A1 begins at Iteration 1 (11:12:32.757).- A1 (session log): iterations 1–236 (11:12:32 → 11:20:26), every row BASE `BQ:.`, TCA0/1/2 `BQ:.`, TCA2 `INA:.` `TCA:.`. Counted window (first 10 complete): iterations 1–10, TCA2 `BQ:.` 10/10.
- B, operator: "done, 30 seconds ago, 11:20am (don't know the seconds)". Session received the reply at ~11:21:00 (shell clock 11:21:10 on the next command).
- B (session log), TCA2 `BQ:`: it 237 (11:20:28) X(2); it 238 (11:20:30) `.`; it 239–266 (11:20:32 → 11:21:27) X(2) every iteration. Controls in 237–266: BASE `BQ:.`, TCA0/1 `BQ:.`, TCA2 `INA:.` `TCA:.`. No code other than 2 anywhere in the log.
- B counted window by the pre-registered boundary rule (report time, in-progress iteration 253 dropped): iterations 254–263, TCA2 `BQ:X(2)` 10/10. Deviation: the operator's report came ~30 s after the action, so the boundary rule places the window ~25 iterations after the first X(2).

### Measured values (from log; cite `lab/evidence/V7R-003/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: n/a
- Result commit: self

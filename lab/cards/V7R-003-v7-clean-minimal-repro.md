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
  hardware_config: "v7 main board, no battery, nothing on J4/J5; J6: JST-SH 4-pin cable, far end 10 kΩ with one lead on pin 1 (+3.3 V), SDA (pin 3) and SCL (pin 4) wires dangling; USB-C Mac ↔ v7 J7 (data + power). No mods known."
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
| S1 | Unpowered: v6 off the bench (data-only cable out). v7 on the bench, no battery, J4/J5 empty. Cable into J6. At the far end: 10 kΩ, one lead on pin 1 (+3.3 V); SDA and SCL wires dangling, touching nothing | Nothing conductive under the board; the free 10 kΩ lead touches nothing | Board markings; how the 10 kΩ joins pin 1; anything noticed |
| S2 | USB-C Mac ↔ v7 J7. Session logs the old firmware's boot output, then flashes | Session confirms the port, the flash and the diag banner | Anything seen on the board (LEDs) |
| A1 | Nothing; session logs ≥ 10 iterations | — | — |
| B  | Connect the free 10 kΩ lead to the SDA wire (cable pin 3); reply "done" at once | SCL wire still dangling | Anything noticed |
| A2 | Disconnect that lead from the SDA wire; reply "done" at once | Lead touches nothing | Anything noticed |
| S3 | Unplug USB-C from J7 | — | Bench state read-back |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
### Measured values (from log; cite `lab/evidence/V7R-003/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: n/a
- Result commit: self

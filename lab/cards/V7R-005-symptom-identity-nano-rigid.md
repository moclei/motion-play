---
test_id: V7R-005
title: "Symptom identity: sensor rigid on J6, Nano ESP32 vs U3 as master — does VCNL 0x60 ACK? A/B/A"
status: pre-registered
created: 2026-10-23
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: motion-play-v7-diag   # A arms (U3 master, diag loop). B arm: motion-play-v7-relbus (U3 released), same commit. Declared, user-approved pattern from V7R-004
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2
  hardware_config: "v7 #0003, no battery, nothing on J4. J6: sensor rigid (+ flex + 2× VCNL4040), connection described at S1. J5: pigtail moved from J6 (black in breadboard 'V' rail with the 10 kΩ, blue dangling — no far-end path, stub only; red → Nano GND column; yellow dangling). TPIO43 green / TPIO44 yellow pad wires → ~175 mm F-M Dupont → Nano ESP32 A4 / A5. USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Scope probes on Cal ground."
variable_changed: "I²C master: U3 (v7-clean diag loop) vs Arduino Nano ESP32 (v7_pca_master_probe) at TPIO43/44, U3 released; rigid on J6 throughout"
structure: A/B/A
revert_on_null: yes           # end of card: v7 on v7-clean motion-play-v7-diag (A2 leaves it there); Nano on the blank sketch
---

# V7R-005 — Symptom identity with a rigid: Nano ESP32 vs U3

Map region cut: **symptom identity** (VCNL NACK = same fault as the BQ marker?). Decisioning §2.7 card 3, run with the Nano ESP32 instead of the SAMD21: what the card needs is a master that clears the BQ marker on this board, and V7R-004 measured that for the Nano (at 100 kHz).

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | Symptom identity holds: the VCNL NACK behind the rigid follows the master the same way the BQ marker does — U3 gets VCNL X(2), the Nano gets VCNL ACK | map: symptom identity (A-2, argued) |
| H2 | The symptoms separate: under a master that gets BQ ACK, VCNL still NACKs (or the reverse) | map: symptom identity; symptom identity: causal |
| M  | Readout or setup artefact: rigid not seated or not detected (PCA scan), wrong channel, U3 not released, Nano contact, wrong port | always listed |

## Confounds (declared; not separated by this card)
- Everything V7R-004 listed for the Nano vs U3 (module, supply, die rev v0.1 vs v0.2, core 2.0.18-arduino.5 vs 2.0.14, injection at TPIO, ~243 mm wire).
- Image: U3 runs `runBusDiagnosticLoop()` at `v7-clean`; the Nano runs `tools/arduino-sketches/v7_pca_master_probe` @ ee10efd (PROBE_VERSION 1.0), which emulates that loop's transactions, delays and TCA channel cache with raw `Wire` (per its header). Built for `arduino:esp32:nano_nora:USBMode=hwcdc`, flashed with esptool (as V7R-004).
- Clock: both 400 kHz (diag loop: `v7-clean` init; probe: `I2C_CLOCK_HZ` default 400000). The Nano's BQ ACK was measured at 100 kHz (V7R-004), not 400 kHz; this card reads it.
- J5 carries a stub-only pigtail (no far-end path) in all arms; it only appears on TCA1 rows.

## Predictions and exclusions (written before the run)
Counted: the `VCNL:` field on the `TCA2+PCA0` and `TCA2+PCA1` rows, 10 complete iterations per arm → 20 fields per arm. A arms: diag-loop iterations 1–10 after the banner. B: probe iterations 1–10. Secondary (counted, not deciding alone): `BQ:` on the TCA2 row, 10 per arm.
Controls in every counted iteration: PCA detection summary shows `TCA ch 2: PCA9546A at 0x76` (each boot/reset); BASE `INA:. BQ:. TCA:.`; TCA2 row `INA:. TCA:. PCA:.`; TCA2+PCA rows `PCA:.`; TCA0 row `BQ:.`. During B: v7 heartbeat, no reboot.

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| A1, A2: VCNL X(2) ≥ 18/20 each; B: VCNL '.' ≥ 18/20 and TCA2 BQ '.' ≥ 9/10; controls pass | H2 (measured-refuted on this board/rigid) | H1 |
| A1, A2: VCNL X(2) ≥ 18/20 each; B: VCNL X(2) ≥ 18/20 and TCA2 BQ '.' ≥ 9/10 | H1 (measured-refuted: symptoms separate) | H2 |
| A1, A2: VCNL X(2) ≥ 18/20; B: TCA2 BQ X(2) ≥ 9/10 and VCNL '.' ≥ 18/20 | H1 (separate, reverse direction) | H2 |
| A1, A2: VCNL X(2) ≥ 18/20; B: TCA2 BQ X(2) ≥ 9/10 and VCNL X(2) ≥ 18/20 | — (Nano fails both at 400 kHz; identity not tested) | — ; note as an observation, decide with the user (B at 100 kHz is a new card) |
| B: VCNL non-'.' in 3–17/20, or BQ non-'.' in 2–8/10 | — (intermittent) | — ; extend B to 30 iterations, decide with the user |
| A1 or A2: VCNL X(2) < 18/20; or A2 vs A1 differ by > 2/20; or any control fails; or a counted code other than 2; or no heartbeat / v7 reboot during B | — (result void) | M; stop and investigate |
| No diag-loop banner (A) / no `BUS RELEASED` (B) / no probe output (B) | — (setup void) | M |

## Setup
- Readout: v7 and Nano serial at 115200, logged by the session with host time (same scratch logger as V7R-004): `lab/captures/V7R-005/2026-10-23_V7R-005_v7_01.txt`, `..._nano_01.txt`.
- All flashing by the session from a detached worktree at `v7-clean` (v7) and esptool (Nano). Order per arm avoids two masters at once: A1 (U3 diag; Nano blank) → B (U3 relbus → `BUS RELEASED`, then Nano probe) → A2 (Nano blank first, then U3 diag).
- No scope.

## Procedure (physical steps for the operator)
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S1 | Both unpowered. Pigtail J6 → J5; blue out of the rail, dangling; rigid into J6 | Black still in 'V' rail; blue and yellow touch nothing; red still in Nano GND | How the rigid connects (cable, length), which rigid, seated |
| S2 | Plug both Mac ends | LED on each | LEDs |
| A1, B, A2 | Nothing (session) | — | — |
| S3 | Unplug both Mac ends | — | Bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
### Measured values (from log; cite `lab/evidence/V7R-005/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** ...
- Revert-on-null done: ...
- Result commit: self

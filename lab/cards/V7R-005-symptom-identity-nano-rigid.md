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
- S1 (2026-10-23), operator: "1, The rigid connects to J6 through a cable - similar to the pigtail one but it has a connector on both ends. One end is in the rigid board, the other is in the main board. It's about 400mm long 2. The rigid doesn't have any identifying mark on it, so I wrote "#1" in black marker. Hopefully it survives handling. A flex PCB is plugged into the rigid, the flex has both sensors on it. The rigid has it's jumper switches thing set so that "1" is "on" and "2" is off (that's what sets it's I2C address)"
- S1 (session): SW1 ON / SW2 OFF = PCA9546A 0x76 per hardware/CONTEXT.md §sensor rigid ("Board 3 (SW1 ON): 0x76"). Rigid marked "#1" by the operator (not a module number). Pigtail moved J6 → J5 per the card (operator did steps 2–3 without remark).
- S2, operator: "1. yes 2. green/yellow power one is on 3. green one (power) is on 4. Yes a green one on the rigid, it's on. No LEDs on the flex."
- S2/A1 (session, `..._v7_01.txt`): loggers opened 21:39:20. v7 boot 1 (the operator's power-on, ~2.5 min before): the whole boot arrived in one burst at 21:39:20.77 when the port was opened; its millis() at STEP 3 `requestFrom()` was 152218, i.e. output had been held since power-on until the host opened the port. Boot 1: init scan finds PCA 0x76 on TCA ch 2; `P3S1`/`P3S2` `ERROR: No VCNL4040 at 0x60 (I2C error: 2)`; `Initialized 0 / 6 sensors`; diag banner; summary `TCA ch 2: PCA9546A at 0x76`; iterations 1–5 logged (21:39:21 → 21:39:29).
- A1 (session): esptool hard reset at 21:39:31 (not needed — boot 1 already had the banner; done by session habit from V7R-004). Boot 2 output from 21:39:31.5 stops at 21:39:32.554 after `[  1283][E][Wire.cpp:499] requestFrom(): i2cWriteReadNonStop returned Error -1` (STEP 3, 0x74 read on TCA ch 0). No further line by 21:42; reopening the port at 21:42:09 gave nothing. Boot 1 printed the same error line and continued (`⚠️ Write OK but read returned 0 bytes`). Stop: unplanned state, reported to the operator.
- Operator approved one more session reset ("yes, go ahead with the reset"). 21:47:37 esptool `chip_id`: chip seen (rev v0.2), then `A fatal error occurred: Unable to verify flash chip connection (No serial data received.)`, no hard reset sent (board left in download mode, no output). 21:48:53 esptool `--no-stub read_mac`: MAC 44:1b:f6:c5:58:c4, hard reset sent.
- A1 (session, boot 3 from 21:48:54): banner `I2C: 400 kHz, default drive, no filters, default pulls [v7-clean]`; same `requestFrom()` error line at STEP 3, followed by `⚠️ Write OK but read returned 0 bytes` (continued, as boot 1); `Initialized 0 / 6 sensors`; diag banner; `TCA ch 2: PCA9546A at 0x76`. Counted iterations 1–10 (boot 3): TCA2+PCA0 `VCNL:X(2)` 10/10, TCA2+PCA1 `VCNL:X(2)` 10/10 → 20/20; TCA2 `BQ:X(2)` 10/10. Controls 10/10 each: BASE INA/BQ/TCA '.', TCA2 INA/TCA/PCA '.', TCA2+PCA0/1 PCA '.', TCA0 BQ '.'. Codes: '.' and X(2) only. Boot 1 iterations 1–5 (uncounted): TCA2, TCA2+PCA0/1 rows `BQ:X(2) … VCNL:X(2)` 5/5.
- B (session): `motion-play-v7-relbus` flashed to v7 from worktree at 90053af, SUCCESS, 4 hashes verified, 21:50:14. Relbus burst (100 kHz, rigid on J6, uncounted): TCA2 `INA:. BQ:X(2) TCA:.` 5/5; `BUS RELEASED` 21:50:22; heartbeat thereafter. Nano: `v7_pca_master_probe` (hwcdc build) written 21:50:31–35, 4 hashes verified. Nano log from 21:50:36: `[probe] sketch=v7_pca_master_probe version=1.0 board=NANO_ESP32 i2c_clock=400000 Hz`; PCA scan `PCA9546A found at 0x76` on TCA channel 2; summary `TCA ch 2: PCA9546A at 0x76`.
- B (session log `..._nano_01.txt`), iterations 1–10: TCA2+PCA0 `VCNL:.` 10/10, TCA2+PCA1 `VCNL:.` 10/10 → 20/20; TCA2 `BQ:.` 10/10. Controls 10/10 each: BASE INA/BQ/TCA '.', TCA2 INA/TCA/PCA '.', TCA2+PCA0/1 PCA '.', TCA0 BQ '.'. No WARN line. X(2) only in uncounted columns (PCA/VCNL on BASE/TCA0/TCA1, VCNL on TCA2). Iteration 1 verbatim: `TCA2        INA:.    BQ:.    TCA:.    PCA:.    VCNL:X(2)` / `TCA2+PCA0   INA:.    BQ:.    TCA:.    PCA:.    VCNL:.` / `TCA2+PCA1   INA:.    BQ:.    TCA:.    PCA:.    VCNL:.`. v7 during B: 7 heartbeat lines, no reboot or new banner.
- A2 (session): blank sketch written to the Nano 21:51:19–23, 4 hashes verified (Nano log silent after). `motion-play-v7-diag` flashed to v7 from worktree at 90053af, SUCCESS, 4 hashes verified, 21:51:57. Boot: banner `[v7-clean]`; STEP 3 `requestFrom()` error line then `⚠️ Write OK but read returned 0 bytes` (continued); `Initialized 0 / 6 sensors`; diag banner; `TCA ch 2: PCA9546A at 0x76`.
- A2 (session log `..._v7_01.txt`), iterations 1–10: TCA2+PCA0 `VCNL:X(2)` 10/10, TCA2+PCA1 `VCNL:X(2)` 10/10 → 20/20; TCA2 `BQ:X(2)` 10/10. Controls 10/10 each (as A1). Codes: '.' and X(2) only.
### Measured values (from log; cite `lab/evidence/V7R-005/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** ...
- Revert-on-null done: ...
- Result commit: self

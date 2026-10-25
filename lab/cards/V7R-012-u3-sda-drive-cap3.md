---
test_id: V7R-012
title: "U3 SDA drive strength CAP_2 / CAP_3 / CAP_2: SDA low at TPIO43 and BQ ACK, failing state"
status: pre-registered
created: 2026-10-25
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: motion-play-v7-relbus   # validation steps (idle bus). Counted arms: V7R-012 drive builds u3-drv2 / u3-drv3 (V7R-009 scope build + drive set and read back on GPIO43), user-approved delta ("1. approved.")
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2. Nano ESP32 powered on the blank sketch throughout (power order, V7R-008)
  hardware_config: "As V7R-011 end (notebook 2026-10-25 s07): v7 #0003, no battery, J4 empty. J6: sensor rigid #1 (SW1 ON = PCA 0x76, SW2 OFF) via ~400 mm cable. J5: pigtail, black in breadboard 'V' rail with the 10 kΩ, blue + yellow dangling, red → Nano GND. TPIO43 green / TPIO44 yellow pad wires → ~175 mm Dupont → Nano A4 / A5. USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Two SQ500 in PCBite arms at S1 (A/B, ground C) for every counted arm."
variable_changed: "GPIO43 (SDA) pad drive strength on U3: GPIO_DRIVE_CAP_2 (default, set explicitly) vs GPIO_DRIVE_CAP_3, set after Wire.begin(43, 44). GPIO44 (SCL) left at its default; clock, image, bus, trigger and probe position held."
structure: "A/B/A — u3-drv2 / u3-drv3 / u3-drv2, all at S1 with no probe move between arms"
revert_on_null: yes           # end: U3 on v7-clean motion-play-v7-diag, Nano on the blank sketch (unchanged), probes off the board
---

# V7R-012 — U3 SDA drive CAP_2 / CAP_3 / CAP_2, SDA low and BQ ACK

Map regions cut: **master: peripheral config** (drive as a lever on the SDA low), **slave: BQ × master** (does BQ's ACK follow the low?), and **measurement** (re-measures legacy L-Ph23, STATE §7: "validated V_OL at CAP_3 vs CAP_2 under U3"). User chose STATE §8 option (d) (session prompt 2026-10-25), the 8th card in the master bundle region.

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | U3's ~0.90 V SDA low is set by the GPIO43 pad's output drive against the bus pull-ups; a stronger drive lowers it | map: master: peripheral config, master: module/path; F-13 |
| H2 | The low is set by something the drive setting does not change (a current into the SDA net, a series element in the pad/module path, a ground offset of U3's supply) | map: master: module/path, master supply; V7R-011 H3 |
| H3 | BQ NACKs because the SDA low is above its input-low threshold; a low that falls far enough gets ACK | map: slave: BQ × master |
| H4 | BQ NACKs whatever the SDA low (the cause is not the level) | legacy L-Ph23 (unvalidated); map: master: timing, mux |
| M  | Measurement artefact: setup (ratio, compensation, ground, contact), trigger catching the wrong frame, the drive setting not in effect, or scope and log disagreeing | always listed; §4.2 |

**Magnitude (argued, for H1).** With combined pull-ups 1.5–2.1 kΩ (legacy, unmeasured on this config), a 0.90 V low is an effective pull-down of ~560–790 Ω. If that is the pad's drive and CAP_3 roughly halves it [verify: ESP32-S3 datasheet drive-strength table], the low falls to ~0.5 V. A fall to ≤ 0.4 V needs ≥ 2.6× more drive; legacy L-Ph23's ~50 mV would need ~18×. A pure CAP_2 → CAP_3 change with no H2 component therefore predicts B ≈ 0.45–0.6 V.

**Threshold used for "a valid low":** 0.4 V, the I²C master V_OL limit (NXP UM10204, 3 mA sink). BQ24195's own V_IL is not in the repo's datasheet notes (STATE §8 desk card (c), not done) [verify]; rows that reach ≤ 0.4 V do not depend on it.

## Confounds (declared; not separated by this card)
- **Not a replica of L-Ph23.** L-Ph23: 100 kHz, CAP_3 on both GPIO43 and GPIO44, reading at U5.6 (BQ pin) by cursor. This card: 400 kHz (scope build), CAP_3 on GPIO43 only, reading at TPIO43. V7R-010 showed TPIO43 and U5.6 within 2 mV at CAP_2; at CAP_3 the copper is not re-checked. L-Ph22 found clock not a lever on the NACK (log-based); its effect on the low is not tested.
- CH2 (SCL) on B (TPIO44) for trigger and decode only; SCL drive is not changed. Its low is recorded from the panel, not counted (CH2 V5 invalid at ground C in V7R-010, accepted).
- CH1 tip shares pad A with the soldered green wire to the Nano (blank, powered), as V7R-010.
- Frames at 400 kHz. Analysis crops each counted CSV to −30…+40 µs around the trigger before `i2c_frame.py` (`lab/evidence/V7R-009/i2c_frame/crop.py`), as V7R-009/-010.
- **V8 adaptation (as V7R-009, approved):** V8 passes on the decoded `Write:d6`; the 9th bit is recorded, not judged.
- V5 at the master end: springs on C, tips on N (C10.1), as V7R-010.
- The Nano stays powered whenever the v7 is; "unplug the v7" means the v7's USB-C only. Reflashing U3 between arms is done over USB with no unplug and no probe move.

## Predictions and exclusions (written before the run)
Counted per arm (A1 = CAP_2, B = CAP_3, A2 = CAP_2): 3 SINGLE captures on the 0x6B write address trigger, read by `i2c_frame.py --expect D6` on the cropped CSV. Per capture: decoded byte and 9th bit; SDA V_OL on the three master-driven 0-bits of D6 (bits 5, 3, R/W). Arm value: V_OL = mean of the arm's 9 bit-means. A = mean(A1, A2); Δ = V_OL(B) − A. BQ ACK rate per arm from the `[scope]` lines spanning the arm's captures (≥ 50 cycles per arm).
Controls in every counted arm: S1 validation passed (V5, V7, and V8 per arm); `[scope]` lines show `sda_drv` = the arm's setting and `scl_drv=2` on every line; `tca` = `ina` = n; no U3 reboot within the arm; every capture decodes `D6` and its 9th bit agrees with the log's BQ result for that arm (NACK arms: high; ACK arms: low); SCL period 2.50 ± 0.01 µs.
Anchor: |A1 − A2| ≤ 20 mV and A1, A2 > 0.4 V with BQ ACK ≤ 5 % (V7R-009/-010 state reproduced).

| Outcome (numeric; anchor and controls pass) | Excludes | Supports (weakly) |
|---|---|---|
| Row 1: \|Δ\| < 50 mV; BQ ACK ≤ 5 % in B | H1 (measured-refuted: drive is not a lever on the low) | H2 |
| Row 2: Δ ≤ −150 mV, V_OL(B) > 0.4 V; BQ ACK ≤ 5 % in B | H2 as the whole of the low | H1; H3 untested below V_OL(B) |
| Row 3: V_OL(B) ≤ 0.4 V; BQ ACK ≤ 5 % in B | H3 (measured-refuted for BQ down to V_OL(B)); L-Ph23 direction replicated | H1, H4 |
| Row 4: V_OL(B) ≤ 0.4 V; BQ ACK ≥ 95 % in B | H4, H2 | H1, H3 (and a firmware lever, one board) |
| Row 5: V_OL(B) > 0.4 V; BQ ACK ≥ 95 % in B | H4 | H3 (BQ threshold above V_OL(B)); H1 if Δ ≤ −50 mV |
| Row 6: any other pattern (−150 < Δ ≤ −50 mV with BQ ≤ 5 %, Δ ≥ +50 mV, or BQ ACK between 5 % and 95 % in B) | — | recorded as measured, no exclusion; values go to the map |
| Anchor fails: \|A1 − A2\| > 20 mV, or A1 or A2 ≤ 0.4 V, or BQ ACK > 5 % in A1 or A2 | — (result void) | M or a changed board state; stop and investigate |
| A control fails (drive read-back not as set, decode not D6, 9th bit disagrees with the log, `tca`/`ina` < n, reboot, SCL period off) or S1 validation fails | — (that arm void; result void if any arm is void) | M |

**Timing:** captured in the CSVs, not evaluated (Planner relay 2026-10-24).

## Setup
- Measurement log: `lab/log/2026-10-25_s01.yaml` (S1, ground C). Validation must read `passed: true` before A1. Validation captures `val_V3`, `val_V5ctl`, `val_V5`, `val_V7`, `val_V8_A1`, `val_V8_B`, `val_V8_A2`; counted captures `A1`, `B`, `A2`.
- Scope, probes, channel settings, trigger, decode: as V7R-010 (DHO804 fw 00.01.05 at 192.168.50.2; two SQ500, scope ratio 10; 0.5 V/div, −1.65 V, BW OFF, DC, 10 µs/div, 10 kpts, 30/70 %; V8 at 20 µs/div; trigger I²C ADDR 107 WRITE, SINGLE).
- Position **S1** (picture `lab/evidence/V7R-010/img/v7-s1-points.png`): CH1 tip A (TPIO43, beside the green wire's solder), CH2 tip B (TPIO44), both springs on C (C9.1), away from C9's +3.3 V end. V5: tips on N (C10.1).
- **Probe moves (user rule, 2026-10-25), in run order:**
  1. Off board → S1-V5 (springs on C, tips on N): **full placement** (springs + both tips), the only one in the card.
  2. S1-V5 → S1 (tips N → A and B, springs stay on C): both tips, springs untouched.
  3. A1, B, A2: **no moves** (only U3's image changes).
  4. End: lift both arms off the board.
  Total on the board: 1 full placement, 1 two-tip move, 0 moves between arms. Cards (a) and (e) in STATE §8 use the same S1 placement; see the session note in the notebook for whether they run in this session.
- Readout: v7 and Nano serial logged by the session (`lab/captures/V7R-012/2026-10-25_V7R-012_{v7,nano}_01.txt`, `=== <arm>` markers); ports by USB serial (v7 44:1B:F6:C5:58:C4, Nano 34:85:18:7B:EB:38).
- Images: U3 relbus / diag from the v7-clean worktree at 90053af. Drive builds `u3-drv2` / `u3-drv3`: the V7R-009 scope sketch (`lab/evidence/V7R-009/src/u3/`) plus, after `Wire.setClock()`, `gpio_set_drive_capability(GPIO_NUM_43, SDA_DRIVE_CAP)` with `-DSDA_DRIVE_CAP=GPIO_DRIVE_CAP_2|3`, and `sda_drv=<n> scl_drv=<n>` (read back with `gpio_get_drive_capability`) on the banner and every `[scope]` line. Same source, one flag differs; sources and firmware.bin hashes to `lab/evidence/V7R-012/src/`. Nano blank (2.0.18 hwcdc), not reflashed.
- Image sequence: relbus for V5/V7 → u3-drv2 (V8_A1, A1) → u3-drv3 (V8_B, B) → u3-drv2 (V8_A2, A2) → diag.
- V9 not due (V7R-002, same probes and settings).

## Procedure (physical steps for the operator)
The session runs every SCPI command, flash and capture; one instruction block per step.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| P0 | Bench: scope on, Ethernet adapter in; Nano plugged in first, then the v7 | scope waveform view; v7 PWR LED | done |
| V1–V4, V5a | Scope only; probes on Cal (V3 per channel), then tips + springs on Cal ground | per procedure | per procedure |
| S1 V5b–V7 | Session puts U3 on relbus. Unplug the v7; springs to C, tips to N; look; plug in (V5b). Unplug; CH1 tip to A, CH2 tip to B; look; plug in (V7) | nothing on an X pad; springs on C | positions |
| Decode | Scope menu: Decode 1 fields per procedure | fields as listed | any field that differed |
| V8, A1 | Nothing (session: u3-drv2, V8 at 20 µs/div, 3 captures at 10 µs/div) | decode band shows `Write:d6` | what the band shows |
| V8, B | Nothing (session: u3-drv3, V8, 3 captures) | decode band shows `Write:d6` | what the band shows |
| V8, A2 | Nothing (session: u3-drv2, V8, 3 captures) | decode band shows `Write:d6` | what the band shows |
| End | Session reverts U3 to diag; then unplug the v7, lift the probes off the board, unplug the Nano | no LEDs; probes clear | bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
### Measured values (from log; cite `lab/evidence/V7R-012/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: yes/no (commit)
- Result commit: self

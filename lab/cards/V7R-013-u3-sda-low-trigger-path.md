---
test_id: V7R-013
title: "U3 SDA low with the far-end path in / out / in (rigid #1 on the J6 cable vs cable stub only), at TPIO43"
status: pre-registered
created: 2026-10-25
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: "u3-drv2"     # run image throughout: V7R-012 drive build u3-drv2 (firmware.bin f8ebf3fc; V7R-009 scope build + GPIO43 CAP_2 set and read back = default drive), user-approved in V7R-012 ("1. approved."); already on U3. End: revert to motion-play-v7-diag
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2. Nano ESP32 powered on the blank sketch throughout (power order, V7R-008)
  hardware_config: "As V7R-012 end (same session, 2026-10-25 s08): v7 #0003, no battery, J4 empty. J6: ~400 mm cable to sensor rigid #1 (SW1 ON = PCA 0x76, SW2 OFF). J5: pigtail, black in breadboard 'V' rail with the 10 kΩ, blue + yellow dangling, red → Nano GND. TPIO43 green / TPIO44 yellow pad wires → ~175 mm Dupont → Nano A4 / A5. Probes seated and validated at S1 (CH1 A, CH2 B, springs C) in V7R-012; not moved in this card."
variable_changed: "Far-end path on the TCA channel-2 cable: rigid #1 plugged into the far end of the J6 cable (A) vs unplugged, leaving the ~400 mm cable as a stub (B). Changed at the rigid's end only; the cable stays in J6."
structure: "A/B/A — rigid in / rigid out (stub) / rigid in, all at S1 with no probe move"
revert_on_null: yes           # end: U3 on v7-clean motion-play-v7-diag, Nano blank (unchanged), probes off the board
---

# V7R-013 — U3 SDA low, far-end path in / out / in

Map regions cut: **master: module/path / master supply** vs **the trigger path** (does the far-end path set any of U3's ~0.90 V low?), **slave: BQ × master** (if BQ ACKs with the path out, at what low?), and **measurement** (re-measures legacy L-Ph21, STATE §7: "validated V_OL with the trigger path out"). User chose STATE §8 option (a) after V7R-012 ("1, record it and continue with (a)"), the 9th card in the master bundle region. V7R-012 found the low is not set by GPIO43's drive setting.

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | The far-end DC path (rigid on the channel-2 cable) sets all or part of U3's elevated SDA low; without it the low falls | F-2, A-1; map: mux, cable / far end; L-Ph21 (~650 mV no cable, unvalidated) |
| H2 | U3's SDA low is independent of the far-end path (it stays ~0.90 V with the path out) | map: master: module/path, master supply; V7R-012 |
| H3 | BQ NACKs because the SDA low is above its input-low threshold | map: slave: BQ × master |
| H4 | BQ's NACK does not follow the low level (BQ can ACK at a ~0.9 V low, or NACK at a valid low) | map: master: timing, mux |
| M  | Measurement artefact: probe contact lost (the last arm's bump history), trigger catching the wrong frame, image not as declared, or scope and log disagreeing | always listed; §4.2 |

**Magnitude (argued, for H1).** With the bus pull-ups at 1.5–2.1 kΩ (legacy, unmeasured) the sink current at a 0.90 V low is ~1.1–1.6 mA; a 4.7–47 kΩ far-end path to +3.3 V adds ~0.05–0.5 mA (the rigid's own pull-up value is not in the repo notes [verify]). If the low were proportional to sink current (a resistive pull-down at U3), removing the path would lower it by ~3–30 %, to ~0.63–0.87 V; the low reaching ≤ 0.4 V would need something other than a resistive load share. V7R-012 already argues against a simple resistive pad, so this estimate is weak. L-Ph21's ~650 mV (no cable, unvalidated) sits inside it.

## Confounds (declared; not separated by this card)
- **Not a replica of L-Ph21.** L-Ph21: no cable at all, 100 kHz, reading at U5.6 by cursor. This card: cable stub left in J6, 400 kHz, reading at TPIO43. F-2 records stub-only as passing; whether the stub alone changes the low is not separated.
- "Rigid out" removes, together: the rigid's SDA/SCL pull-ups (the far-end DC path), the PCA9546A and VCNL loads, the rigid's +3.3 V draw on the cable, and (A-1) the TCA pass gate's downstream idle level. The card tests the bundle; F-2 (10 kΩ far-end resistor alone triggers) is the existing evidence that the DC path is the active part.
- The J5 pigtail's 10 kΩ sits on a TCA channel the build never opens (the cycle writes 0x04 = channel 2 only); left as is.
- The v7 is power-cycled at every change (unplug at the Mac end); U3 boots u3-drv2 each time. V7R-012 showed the low steady across a ~4 h unplugged gap and two power cycles.
- Probes: S1 placement validated in V7R-012 (V5, V7, re-check `val_V7_03`). No V5/V7 here; V8 before every arm (contact via decode), and CH1's idle-high between frames in each counted CSV is read as a contact check (≥ 3.135 V). CH2 at B carries spike bursts at idle (V7R-010, V7R-012); CH2 is not counted.
- Frames at 400 kHz; cropped CSV −30…+40 µs, `i2c_frame.py --expect D6`, as V7R-009/-010/-012. V8 adaptation as V7R-009: V8 passes on the decoded `Write:d6`; the 9th bit is recorded.

## Predictions and exclusions (written before the run)
Counted per arm (A1 = rigid in, B = rigid out, A2 = rigid in): 3 SINGLE captures on the 0x6B write address trigger. Per capture: decoded byte and 9th bit; SDA V_OL on bits 5, 3 and R/W of D6. Arm value: V_OL = mean of the 9 bit-means. A = mean(A1, A2); Δ = V_OL(B) − A. BQ ACK rate per arm from the `[scope]` lines spanning the arm's captures (≥ 50 cycles).
Controls in every counted arm: V8 shows `Write:d6`; `[scope]` lines show `sda_drv=2 scl_drv=2`, `tca` = `ina` = n; no reboot within the arm; each capture decodes `D6` and its 9th bit agrees with the log's BQ result for that arm; SCL period 2.50 ± 0.01 µs; CH1 between frames ≥ 3.135 V in each counted CSV (or in the arm's V8 capture if a counted CSV has no idle stretch).
Anchor: |A1 − A2| ≤ 20 mV, A1 and A2 > 0.4 V, BQ ACK ≤ 5 % in A1 and A2 (V7R-012's state reproduced).

| Outcome (numeric; anchor and controls pass) | Excludes | Supports (weakly) |
|---|---|---|
| Row 1: V_OL(B) ≤ 0.4 V; BQ ACK ≥ 95 % in B | H2 | H1, H3 (low and ACK move together) |
| Row 2: \|Δ\| < 50 mV; BQ ACK ≥ 95 % in B | H1; H3 (measured-refuted: BQ ACKs U3's ~0.9 V low) | H2, H4 |
| Row 3: Δ ≤ −100 mV, V_OL(B) > 0.4 V; BQ ACK ≥ 95 % in B | H2 as the whole of the low | H1 (part of the low from the path); H3 only if BQ's V_IL lies between V_OL(B) and A — not decided here |
| Row 4: V_OL(B) ≤ 0.4 V; BQ ACK ≤ 5 % in B | H2; H3 (measured-refuted for BQ down to V_OL(B)) | H1, H4; F-2 not reproduced (stub-only should pass) — flag |
| Row 5: V_OL(B) > 0.4 V; BQ ACK ≤ 5 % in B | — | F-2 not reproduced at this config — recorded, stop and investigate before the next card |
| Row 6: any other pattern (−100 < Δ ≤ −50 mV or Δ ≥ +50 mV with BQ ≥ 95 %, or BQ ACK between 5 % and 95 % in B) | — | recorded as measured, no exclusion; values go to the map |
| Anchor fails: \|A1 − A2\| > 20 mV, or A1 or A2 ≤ 0.4 V, or BQ ACK > 5 % in A1 or A2 | — (result void) | M or a changed board state (rigid not re-seated); stop and investigate |
| A control fails (decode not D6, 9th bit disagrees with the log, drive read-back ≠ 2, `tca`/`ina` < n, reboot, SCL period off, CH1 idle < 3.135 V) | — (that arm void; result void if any arm is void) | M |

**Timing:** captured in the CSVs, not evaluated (Planner relay 2026-10-24).

## Setup
- Measurement log: `lab/log/2026-10-25_s01.yaml`, shared with V7R-012 (validation `passed: true` for the S1 placement). Captures `val_V8_A1`, `val_V8_B`, `val_V8_A2`; counted `A1`, `B`, `A2` (files named `2026-10-25_V7R-013_*`).
- Scope: as V7R-012 (0.5 V/div, −1.65 V, BW OFF, DC, 10 kpts; V8 at 20 µs/div, counted at 10 µs/div; trigger I²C ADDR 107 WRITE, SINGLE; decode set this session).
- **Probe moves (user rule, 2026-10-25), in run order:** none. Probes stay at S1 (CH1 A, CH2 B, springs C) from V7R-012 through all three arms; the end lift is the only touch. Physical actions are at the cable's far end (rigid connector, ~400 mm from the board) and the Mac end of the v7's USB-C only.
- Readout: v7 and Nano serial logged by the session to new files `lab/captures/V7R-013/2026-10-25_V7R-013_{v7,nano}_01.txt`, `=== <arm>` markers.
- Image: u3-drv2 throughout (already on U3, `drive:` banner line checked at each boot). End: diag from the v7-clean worktree at 90053af.

## Procedure (physical steps for the operator)
The session runs every SCPI command and capture; one instruction block per step.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| A1 | Plug the v7 in at the Mac end (rigid on the cable, as now) | PWR LED; probes untouched | LED |
| V8, A1 | Nothing (session: V8, 3 captures) | band shows `Write:d6` | what the band shows |
| B-1 | Unplug the v7 at the Mac end; unplug the cable from rigid #1 (rigid end only); lay the free cable end on the bench, contacts touching nothing | cable still in J6; free end touches nothing; probes untouched | positions |
| B-2 | Plug the v7 in | PWR LED | LED |
| V8, B | Nothing (session: V8, 3 captures) | band shows `Write:d6` | what the band shows |
| A2-1 | Unplug the v7; plug the cable back into rigid #1 | connector fully seated; probes untouched | done |
| A2-2 | Plug the v7 in | PWR LED | LED |
| V8, A2 | Nothing (session: V8, 3 captures) | band shows `Write:d6` | what the band shows |
| End | Session reverts U3 to diag; then unplug the v7, lift the probes off the board, unplug the Nano | no LEDs; probes clear | bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
### Measured values (from log; cite `lab/evidence/V7R-013/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: yes/no (commit)
- Result commit: self

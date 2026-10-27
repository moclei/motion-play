---
test_id: V7R-015
title: "U3 SDA low and BQ ACK vs added far-end pull-up current on the J6 pigtail (stub / 47 kΩ / 10 kΩ / 4.7 kΩ / stub), at TPIO43"
status: pre-registered
created: 2026-10-26
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: "u3-drv2"     # counted arms: V7R-012 drive build u3-drv2 (sources lab/evidence/V7R-012/src/u3/, firmware.sha256 f8ebf3fc…; GPIO43 CAP_2 = default drive, read back), as V7R-012 A and all of V7R-013. Validation on motion-play-v7-relbus. End: revert to motion-play-v7-diag. User-approved for this card ("1. approved")
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2. Nano ESP32 powered on the blank sketch throughout (power order, V7R-008)
  hardware_config: "From s01 end (notebook 2026-10-26 s01), changed at S0 before any probe touches the board: J6 rigid cable unplugged at the board end, rigid #1 set aside; JST-SH pigtail moved J5 → J6 (black = pin 1 +3.3 V in the breadboard 'V' rail; red = pin 2 GND → Nano GND column; blue = pin 3 SDA in the 'G'-labelled rail, which is the SDA side of the resistor, not GND; yellow = pin 4 SCL dangling). J4, J5 empty. No battery. TPIO43 green / TPIO44 yellow pad wires → ~175 mm Dupont → Nano A4 / A5. USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Two SQ500 in PCBite arms at S1 (A/B, ground C)."
variable_changed: "Far-end pull-up on SDA: the resistor between the breadboard 'V' rail (+3.3 V) and the SDA rail at the J6 pigtail's far end — none (stub) / 47 kΩ / 10 kΩ / 4.7 kΩ / none. Changed at the breadboard only."
structure: "A/B/C/D/A dose series — S0a (stub) / R47 / R10 / R4.7 / S0b (stub), at S1 with no probe move between arms; the S0 anchor brackets the series"
revert_on_null: yes           # end: U3 on v7-clean motion-play-v7-diag; Nano blank (unchanged); probes off the board; pigtail and rigid positions as left (recorded in the notebook)
---

# V7R-015 — U3 SDA low and BQ ACK vs added far-end pull-up current

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | U3's GPIO43 low behaves as a resistive sink: V_OL rises about linearly with the added far-end current, slope 0.3–1.5 kΩ | checkpoint @ V7R-014 (argued ~0.5–0.7 kΩ); V7R-013, V7R-014; map: master: module/path |
| H2 | U3's SDA low does not depend on the added far-end current (V7R-013's −219 mV came from the rigid's other loads, not its pull-up) | V7R-013 confounds; map: mux |
| H3 | BQ's ACK is set by the SDA low level: one switching level sorts every arm (ACK below it, NACK above it) | map: slave: BQ × master; F-14 |
| H4 | BQ's ACK follows the presence of a far-end path, not the low level (an ACK arm sits above a NACK arm in V_OL) | map: mux, master: timing; F-2 |
| M  | Measurement artefact: probe contact lost, trigger catching the wrong frame, image not as declared, resistor or rail value wrong, scope and log disagreeing | always listed; §4.2 |

**Magnitude (argued, for H1; checkpoint @ V7R-014).** At ~0.6 kΩ in series, the added current I_far = (V_rail − V_OL)/R gives ≈ 55 µA / 0.25 mA / 0.55 mA for 47 / 10 / 4.7 kΩ, so V_OL ≈ S0 + ~33 / ~150 / ~330 mV. V7R-013's stub low was 678 mV (400 mm cable, not this pigtail). L-Ph5 (log-based) has 47 kΩ triggering the NACK; under H1 + H3 that puts BQ's switching level within ~33 mV above S0.

## Confounds (declared; not separated by this card)
- **Pigtail, not the 400 mm cable.** S0 here is the pigtail stub, so V7R-013's 678 mV is not the anchor; S0a/S0b are.
- **No rigid.** No PCA/VCNL load, no rigid pull-ups, no VCNL readout: BQ is the only marker.
- **I_far is computed, not measured.** I_far = (V_rail − V_OL(arm))/R_meas. V_rail is read once by DMM ('V' rail to Nano GND column, powered, S0a). R_meas is read by DMM before each resistor goes in. The TCA pass-gate drop at ≤ 0.6 mA is ignored (argued, a few mV).
- **Power cycle at every change** (unplug the v7 at the Mac end), as V7R-013; U3 reboots u3-drv2 each time.
- **Timing:** captured in the CSVs, not evaluated (Planner relay 2026-10-24).
- **Image:** u3-drv2 is rebuilt, since no binary is kept. Before flashing, the session compares the rebuild to `firmware.sha256`. If the whole-file hash differs, it checks that the loadable segments are identical (V7R-014 method; Planner relay 2026-10-26) and tells the user before flashing.

## Predictions and exclusions (written before the run)
Counted per arm: 3 SINGLE captures on the 0x6B write address trigger. Per capture: decoded byte and 9th bit; SDA V_OL on bits 5, 3 and R/W of D6. Arm value: V_OL = mean of the 9 bit-means. BQ ACK rate per arm from the `[scope]` lines spanning the arm's captures (≥ 50 cycles).
Fit: least-squares line V_OL vs I_far over all five arms (I_far = 0 for S0a, S0b). R_fit = slope; residual = max |V_OL − fit|. Range = max − min V_OL over the five arms.
Controls in every counted arm (as V7R-013): V8 shows `Write:d6`; `[scope]` lines show `sda_drv=2 scl_drv=2`, `tca` = `ina` = n; no reboot within the arm; each capture decodes `D6` and its 9th bit agrees with the log's BQ result for that arm; SCL period 2.50 ± 0.01 µs; CH1 between frames ≥ 3.135 V.
Anchor: |S0a − S0b| ≤ 20 mV and S0a, S0b in the same BQ class (both ≥ 95 % or both ≤ 5 %).
BQ class per arm: ACK (≥ 95 %), NACK (≤ 5 %), mixed (between).

| Outcome (numeric; anchor and controls pass) | Excludes | Supports (weakly) |
|---|---|---|
| Row 1: 0.3 ≤ R_fit ≤ 1.5 kΩ, residual ≤ 25 mV; every ACK arm's V_OL below every NACK arm's, no mixed arm | H2, H4 | H1, H3; BQ's switching level bracketed between the highest ACK and lowest NACK V_OL |
| Row 2: 0.3 ≤ R_fit ≤ 1.5 kΩ, residual ≤ 25 mV; an ACK arm's V_OL ≥ 20 mV above a NACK arm's | H2; H3 as the sole cause | H1, H4 |
| Row 3: range < 40 mV | H1 | H2; if BQ changes class across arms: H3 excluded, H4 supported; if not: no exclusion for H3/H4 |
| Row 4: range ≥ 40 mV and (R_fit outside 0.3–1.5 kΩ or residual > 25 mV) | H1 in the stated resistive form | V_OL vs I_far shape recorded as measured; H3/H4 judged by ordering as rows 1/2 |
| Row 5: one or more mixed arms, otherwise row 1 or 2 | as row 1 or 2 for the class arms | mixed arm's V_OL marks BQ's switching region |
| All arms ACK, or all arms NACK | — for H3/H4 | H1/H2 judged by the fit rows; BQ's switching level is outside the measured V_OL span (recorded) |
| 47 kΩ sub-result (reported with any row) | — | R47 NACK: L-Ph5 reproduced in this config. R47 ACK: L-Ph5's 47 kΩ entry not reproduced; F-2 updated |
| Anchor fails: \|S0a − S0b\| > 20 mV, or S0a and S0b in different BQ classes | — (result void) | M or a changed board state; stop and investigate |
| A control fails (decode not D6, 9th bit disagrees with the log, drive read-back ≠ 2, `tca`/`ina` < n, reboot, SCL period off, CH1 idle < 3.135 V) | — (that arm void; result void if any arm is void) | M |

## Setup
- Measurement log: new, `lab/log/<run date>_sNN.yaml`. A new scope session: full validation per `lab/procedures/dho804-setup-validation.md` must read `passed: true` before S0a. V9 not due unless the procedure says so.
- Scope: as V7R-012/-013 (DHO804 at 192.168.50.2; two SQ500, scope ratio 10; 0.5 V/div, −1.65 V, BW OFF, DC; V8 at 20 µs/div, counted at 10 µs/div, 10 kpts; trigger I²C ADDR 107 WRITE, SINGLE; decode set).
- Position **S1** (picture `lab/evidence/V7R-010/img/v7-s1-points.png`): CH1 tip A (TPIO43), CH2 tip B (TPIO44), both springs on C (C9.1). V5: tips on N (C10.1).
- **Probe moves (user rule, 2026-10-25), in run order:**
  1. Off board → S1-V5 (springs on C, tips on N): **full placement**, the only one in the card. It comes after S0's connector swap, so no board-end connector is touched with probes on.
  2. S1-V5 → S1 (tips N → A and B, springs stay): both tips.
  3. S0a … S0b: **no moves**. Every change is at the breadboard, away from the board.
  4. End: lift both arms off the board.
- Readout: v7 and Nano serial logged by the session (`lab/captures/V7R-015/<date>_V7R-015_{v7,nano}_01.txt`, `=== <arm>` markers).
- Images: relbus for validation → u3-drv2 (all five arms) → diag, from the v7-clean worktree at 90053af / V7R-012 sources.
- Resistors: one each of 47 kΩ, 10 kΩ (the one on the bench) and 4.7 kΩ, read by DMM before use (user: "yes, I have both").

## Procedure (physical steps for the operator)
The session runs every SCPI command, flash and capture; one instruction block per step.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S0 | Both boards unpowered, probes off. Unplug the J6 cable at the board end and set rigid #1 aside. Move the pigtail from J5 to J6. At the breadboard: take the 10 kΩ out; blue stays in the 'G'-labelled rail on its own; black in 'V'; red in the Nano GND column; yellow dangling | J4, J5 empty; blue alone in its rail; yellow touches nothing; nothing under the board | what is where |
| R | DMM the 47 kΩ, 10 kΩ and 4.7 kΩ resistors (out of circuit) | leads on the resistor only | three readings |
| V | Power up (Nano first, then v7); session runs validation; operator places probes per the procedure | per procedure | per procedure |
| S0a | Session flashes u3-drv2 (after the image check). DMM 'V' rail to Nano GND column | PWR LED; probes untouched | V_rail reading; LED |
| V8, S0a | Nothing (session: V8, 3 captures) | band shows `Write:d6` | what the band shows |
| R47-1 | Unplug the v7 at the Mac end; put the 47 kΩ between the 'V' rail and blue's rail | resistor legs in those two rails only; probes untouched | holes used |
| R47-2 | Plug the v7 in | PWR LED | LED |
| V8, R47 | Nothing (session) | band shows `Write:d6` | what the band shows |
| R10 | As R47-1/-2 with the 10 kΩ in place of the 47 kΩ; then nothing (session) | as R47 | as R47 |
| R4.7 | As R47-1/-2 with the 4.7 kΩ; then nothing (session) | as R47 | as R47 |
| S0b | Unplug the v7; take the 4.7 kΩ out (blue alone in its rail); plug in; then nothing (session) | blue alone; probes untouched | LED; band |
| End | Session reverts U3 to diag; unplug the v7 at the Mac end, lift the probes off the board, unplug the Nano | no LEDs; probes clear | bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
**Session 2026-10-26 s02** (log `lab/log/2026-10-26_s02.yaml`).
- Image check (session, before S0): rebuild of `lab/evidence/V7R-012/src/u3/` → `ca2ba6af…` ≠ `f8ebf3fc…`. Original V7R-012 binary found at an earlier session's scratchpad (`…/31eb2470…/scratchpad/u3drv/.pio/build/u3-drv2/firmware.bin`), sha256 = `f8ebf3fc…` (matches `firmware.sha256`). Original vs rebuild: 271712 B both, 5 segments; 4 identical; segment 0x3c030020 differs in 32 bytes at file 0xb0 (embedded ELF SHA256); remaining differences in the trailing checksum/hash. Plan: flash the original f8ebf3fc binary (user told before flashing).
- S0: "1. J6 has the pigtail, other two are empty / All else as it should be"
- R: "All read their proper values"; asked for digits: "Same. they're good". Digits not reported — R_meas taken as nominal 47 k / 10 k / 4.7 kΩ (deviation).
### Measured values (from log; cite `lab/evidence/V7R-015/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: yes/no (commit)
- Result commit: self

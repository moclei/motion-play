---
test_id: V7R-010
title: "SDA low along U3's path: U3 pin (K) vs test pad (A) vs BQ pin (D), U3 master, failing state"
status: recorded
created: 2026-10-24
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: motion-play-v7-relbus   # validation steps (idle bus after BUS RELEASED). Counted captures: U3 runs the V7R-009 scope build (u3-scope, firmware.bin 84c930db), user-approved delta ("Approve")
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2. Nano ESP32 powered on the blank sketch throughout (power order, V7R-008)
  hardware_config: "As V7R-009 end (notebook 2026-10-24 s05): v7 #0003, no battery, J4 empty. J6: sensor rigid #1 (SW1 ON = PCA 0x76, SW2 OFF) via ~400 mm cable. J5: pigtail, black in breadboard 'V' rail with the 10 kΩ, blue + yellow dangling, red → Nano GND. TPIO43 green / TPIO44 yellow pad wires → ~175 mm Dupont → Nano A4 / A5. USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Two SQ500 in PCBite arms, moved between the positions below."
variable_changed: "Where CH1 (SDA) touches U3's SDA net: U3 pad 37 (K, U3's own pin) vs TPIO43 (A, test pad) vs U5.6 (D, BQ pin). Master, image, bus and trigger held."
structure: "A/B/C/A — S2 (D) / S1 (A) / S0 (K) / S2 (D)"
revert_on_null: yes           # end: U3 on v7-clean motion-play-v7-diag, Nano on the blank sketch (unchanged), probes off the board
---

# V7R-010 — SDA low along U3's path (K / A / D), U3 master

Map regions cut: **master: module/path, master supply, master: pin role** vs **bus copper** (location part: is U3's ~0.90 V SDA low already there at U3's own pin, or does it appear along the copper U3 → TPIO43 (5.9 mm) or TPIO43 → U5.6?) and **measurement** (first validated v7 scope view at the master end). Follows V7R-009 (F-13); user chose STATE §8 option (a), extended with U3's own pin K ("Yes, with K").

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | The elevated SDA low is already present at U3's own pin (K): it comes from U3 or what drives/loads its pad (module, pin role, driver config, supply), not from the copper after it | map: master: module/path, pin role, master supply; F-13 |
| H2 | SDA is low (≤ 0.4 V) at K and the low is lost along U3 → TPIO43 copper (A higher than K) | map: master: module/path (copper U3→TPIO) |
| H3 | SDA is low at K and A, and the low is lost along TPIO43 → U5.6 copper (D higher than A) | map: bus copper |
| M  | Measurement artefact: setup (ratio, compensation, ground, contact), trigger catching the wrong frame, or scope and log disagreeing | always listed; §4.2 |

## Confounds (declared; not separated by this card)
- S1 and S0 share one ground (both springs on pad C, C9.1), so K vs A is like-for-like; S2 uses pad F (C21.2). The master-end vs BQ-end comparison is across two grounds, each validated by V5 at its own position. A low of ~0.1 V vs ~0.9 V is far beyond any V5-level offset, so this does not limit the outcome rows.
- CH2 (SCL) sits on B (TPIO44) at both S1 and S0, and on E at S2. SCL is only for the trigger and decode; its level is recorded from the panel, not counted.
- At S1 the CH1 tip shares pad A with the soldered green wire to the Nano (blank, powered).
- Every probe move needs a v7 power cycle (unplug at the Mac end). Validation steps run on relbus; U3 is reflashed to the scope build before each V8 and counted arm, and back to relbus before each move.
- Frames at 400 kHz (scope build). Analysis crops each counted CSV to −30…+40 µs around the trigger before `i2c_frame.py` (`lab/evidence/V7R-009/i2c_frame/crop.py`, the method the user chose in V7R-009) until the Planner relay's window option exists.
- **V8 adaptation (as V7R-009, approved):** V8 passes on the decoded `Write:d6`; the 9th bit is recorded, not judged.
- V5 at the master end: springs on C, tips on pad N (C10.1, ground), because spring and tip do not both fit on one 0603 pad (V7R-009). The +3.3 V end of C10 (X) sits between N and C.
- The Nano stays powered whenever the v7 is; "unplug the v7" means the v7's USB-C only.

## Predictions and exclusions (written before the run)
Counted per arm (A1 = S2, S1, S0, A2 = S2): 3 SINGLE captures on the 0x6B write address trigger, read by `i2c_frame.py --expect D6` on the cropped CSV. Per capture: decoded byte and 9th bit; SDA V_OL on the three master-driven 0-bits of D6 (bits 5, 3, R/W); rise times. Arm value: V_OL = mean of the arm's 9 bit-means. Written V_OL(K), V_OL(A), V_OL(D) with V_OL(D) = mean of A1 and A2.
Controls in every counted arm: the position's validation passed (V5 per ground, V7 idle high and V8 decode per placement); `[scope]` log lines spanning the captures show `tca` = `ina` = n and `bq` ACK ≤ 5 % of n; every capture decodes `D6` with the 9th bit high (NACK), agreeing with the log; SCL period 2.50 ± 0.01 µs (stands in for the banner, which the logger misses).

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| V_OL(K) > 0.4 V and \|V_OL(K) − V_OL(D)\| < 100 mV and \|V_OL(A) − V_OL(D)\| < 100 mV; anchor and controls pass | H2, H3 (measured-refuted: the low is not lost along the copper) | H1 |
| V_OL(K) ≤ 0.4 V and V_OL(A) − V_OL(K) ≥ 300 mV; anchor and controls pass | H1, H3 | H2 |
| V_OL(K) ≤ 0.4 V, V_OL(A) ≤ 0.4 V and V_OL(D) − V_OL(A) ≥ 300 mV; anchor and controls pass | H1, H2 | H3 |
| Any other pattern (e.g. a rise along the path with no single step ≥ 300 mV, or K > 0.4 V with D more than 100 mV away); anchor and controls pass | — | recorded as measured, no exclusion; the values go to the map as a gradient |
| Anchor fails: \|A1 − A2\| > 20 mV, or A1 or A2 ≤ 0.4 V (V7R-009's state not reproduced) | — (result void) | M or a changed board state; stop and investigate |
| A control fails (decode not D6, 9th bit low in a capture, log `bq` ACK > 5 %, `tca`/`ina` < n, U3 reboot, SCL period off) or a position's validation fails | — (that arm void; result void if any arm is void) | M |

**Timing:** captured in the CSVs, not evaluated (Planner relay 2026-10-24).

## Setup
- Measurement logs: `lab/log/2026-10-24_s02.yaml` (S2: A1 and A2; arm position S2) and `lab/log/2026-10-24_s03.yaml` (master end: S1 and S0; one ground, C). Each log's validation must read `passed: true` before its first counted capture. Validation captures `val_V3`, `val_V5ctl`, `val_V5`, `val_V7`, `val_V8` (with a position suffix where needed, e.g. `val_V7_S0`); counted captures `A1`, `S1`, `S0`, `A2`.
- Scope, probes, channel settings, trigger, decode setup: as V7R-009 (DHO804 fw 00.01.05 at 192.168.50.2; two SQ500, scope ratio 10; 0.5 V/div, −1.65 V, BW OFF, DC, 10 µs/div, 10 kpts, 30/70 %; V8 at 20 µs/div; trigger I²C ADDR 107 WRITE, SINGLE).
- Positions (pictures `lab/evidence/V7R-010/img/v7-s1-points.png`, `v7-s2-grounds.png`; pad nets from the layout via `probe_points pads`):
  - **S2:** CH1 tip D (U5.6), CH2 tip E (U5.5), both springs on F (C21.2) away from its X pad. V5: tips on G (C20.2), as V7R-009.
  - **S1:** CH1 tip A (TPIO43, beside the green wire's solder), CH2 tip B (TPIO44), both springs on C (C9.1), away from C9's +3.3 V end. V5: tips on N (C10.1).
  - **S0:** as S1 with only the CH1 tip moved from A to K (U3 pad 37, on the exposed part of the module edge pad, right of the metal can; the pads either side are U3 pad 38 (unconnected) and pad 36 (SCL)).
- Readout: v7 and Nano serial logged by the session (`lab/captures/V7R-010/2026-10-24_V7R-010_{v7,nano}_01.txt`, `=== <arm>` markers); ports by USB serial (v7 44:1B:F6:C5:58:C4, Nano 34:85:18:7B:EB:38).
- Images: U3 relbus / diag from the v7-clean worktree at 90053af; U3 scope build `u3-scope` (firmware.bin 84c930db, uploaded with `-t nobuild`); Nano blank (2.0.18 hwcdc), not reflashed.
- Image sequence: U3 relbus for validation at each position → scope build for V8 and the arm → relbus before each probe move → … → revert U3 to diag.
- V9 not due (V7R-002, same probes and settings).

## Procedure (physical steps for the operator)
The session runs every SCPI command, flash and capture; one instruction block per step.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| P0 | Bench: scope on, Ethernet adapter in; Nano plugged in first, then the v7 | scope waveform view; v7 PWR LED | done |
| V1–V4, V5a | Scope only; probes on Cal (V3 per channel), then tips + springs on Cal ground | per procedure | per procedure |
| S2 V5b–V7 | Unplug the v7; springs on F, tips on G; look; plug in (V5b). Unplug; tips to D/E; look; plug in (V7) | nothing on an X pad; tips on D/E | positions |
| Decode | Scope menu: Decode 1 fields per procedure | fields as listed | any field that differed |
| S2 V8, A1 | Nothing (session: scope build, V8 at 20 µs/div, 3 captures at 10 µs/div) | decode band shows `Write:d6` | what the band shows |
| S1 V5b–V7 | Session puts U3 on relbus. Unplug the v7; springs to C, tips to N; look; plug in (V5b). Unplug; CH1 tip to A, CH2 tip to B; look; plug in (V7) | nothing on an X pad; springs on C | positions |
| S1 V8, S1 | Nothing (session: scope build, V8, 3 captures) | band shows `Write:d6` | what the band shows |
| S0 V7 | Session puts U3 on relbus. Unplug the v7; CH1 tip from A to K only; look; plug in | CH1 on K, not on pad 36 or 38; springs on C | position |
| S0 V8, S0 | Nothing (session: scope build, V8, 3 captures) | band shows `Write:d6` | what the band shows |
| S2 V7 | Session puts U3 on relbus. Unplug the v7; springs to F, tips to D/E; look; plug in | nothing on an X pad; tips on D/E | positions |
| S2 V8, A2 | Nothing (session: scope build, V8, 3 captures) | band shows `Write:d6` | what the band shows |
| End | Session reverts U3 to diag; then unplug the v7, lift the probes off the board, unplug the Nano | no LEDs; probes clear | bench state |

### Amendment 2026-10-25 (after the S0 arm, before any anchor data; user-approved "a")
- **Change:** the anchor arm A2 is taken at **A (TPIO43), S1 placement**, not at D (S2). After S0, only the CH1 tip moves from K back to A; springs stay on C and CH2 stays on B. Steps "S2 V7" and "S2 V8, A2" are replaced by: V7 at A (`val_V7_A2`), then V8 (`val_V8_A2`) and 3 counted captures `A2`, all in `lab/log/2026-10-24_s03.yaml`, same image sequence (relbus for V7, scope build for V8 and A2).
- **Reason:** probe moves are a risk to the board (shorts, pad scraping, repeated seating); a return to S2 is a full move (springs + both tips) at the most cramped position. The design did not weigh this. The change was made for the physical reason only; no anchor data existed when it was made.
- **Anchor rule, amended:** anchor fails if |V_OL(S1) − V_OL(A2)| > 20 mV, or S1 or A2 ≤ 0.4 V. V_OL(A) = mean of S1 and A2. V_OL(D) = A1 alone (no second D reading). Outcome rows otherwise unchanged.
- **Cost:** drift at D itself is not checked; the D value rests on one arm.

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- P0 (operator): "1. yes 2. yes". Nano plugged in first, then the v7. Session: U3 on relbus, `BUS RELEASED` 21:45:09; V2 probe ratio read back 10 / 10 by direct socket after the one-shot query returned blanks and `-110` errors (error queue drained).
- V1–V4 (operator): "1. done 2. I accidentally pressed auto a second time after placing probe 1 in it's position"; CH1 flat top, square corners "yes"; CH2 "yes". Vamp 3020.8 mV per channel (`val_V3_01`, `val_V3_03`). Session: `val_V3_02` (CH2) captured at 0.5 V/div, 0 V offset (set commands had not taken); re-set, read back, recaptured as `_03`.
- V5a (operator): both tips and springs on Cal ground "done". Session: `val_V5ctl_01` CH2 flat at 2.971–2.998 V (the Cal high level), CH1 mean −6.7 mV.
- S2 V5b (operator): springs on F, tips on G, "1. confirmed 2. yes". S2 V7: "1. confirmed 2. yes"; `val_V7_01` passes first seat. Decode menu: "1. none 2. confirmed 3. yes".
- S2 V8, A1 (session): U3 scope build (firmware.bin 84c930db, hash verified); V8 decode band `Write:80`, `Write:d6` (red NACK mark), `Write:e0`. A1 captures 22:33:50 / :55 / 22:34:01; v7 log `[scope]` 22:33:43 → 22:34:21, n 120 → 490, `tca` = `ina` = n, `bq=0 bq_codes=2222222222`, no reboot.
- S1 V5b (operator): "1. confirmed. Small space so hard to be 100% about it, but I'm ok enough to try turning on the power, which i just did 2. yes". S1 V7: "1. confirmed 2. yes"; `val_V7_02` CH2 −0.0157 V; operator: "ok checked and fixed (I think). plugged in power on". The session's command checker then gave no verdict on several calls; the operator ran `capture.py` for `val_V7_03` in another terminal and pasted the output; `val_V7_03` passes, CH2 sd 29.56 mV with spikes 2.79–3.64 V.
- S1 V8, S1 (session): V8 decode band `Write:d6` with NACK mark; panel Vpp(C2) and Vbase(C2) `*****`. Captures 23:12:56 / 23:13:02 / :08; log 23:12:51 → 23:13:26, n 110 → 460, `tca` = `ina` = n, `bq=0`, no reboot.
- S0 V7 (operator): CH1 on K only "1. confirmed 2. yes"; `val_V7_S0_01` CH1 −0.0127 V. Operator: "The ESP32-s3 pins/pads seem to have some kind of substance in them, semi-transparent, which scrapes away a bit when touched by the probe needles. I reseated CH1"; `val_V7_S0_02` CH1 −0.0118 V. Operator (third seat): "I think everything is in place now"; `2026-10-25_…_val_V7_S0_01` passes, 2 s after `BUS RELEASED` 09:35:48.
- S0 V8, S0 (session): V8 `Write:d6` with NACK mark. Captures 09:37:02 / :08 / :14; log 09:36:51 → 09:37:34, n 70 → 500, `tca` = `ina` = n, `bq=0`, no reboot.
- Anchor (operator, after the amendment 598369c): "a — move CH1 tip from K back to A"; "1. confirmed 2. plugged in, PWR LED on". `val_V7_A2_01` passes, 2 s after `BUS RELEASED` 09:46:11. V8 `Write:d6` with NACK mark. A2 captures 09:47:08 / :14 / :20; log 09:46:57 → 09:47:37, n 30 → 430, `tca` = `ina` = n, `bq=0`, no reboot.
- Revert (session): U3 `motion-play-v7-diag` from the worktree at 90053af, SUCCESS. Nano not reflashed (blank throughout).
- End (operator): "v7 off, probes clear, nano off, pads look fine".
- Observed, not asked for: every relbus boot scan this session found 0x6B; captures after midnight carry the date 2026-10-25.

### Measured values (from log; cite `lab/evidence/V7R-010/...`)
Sources: `lab/log/2026-10-24_s02.yaml` (S2), `lab/log/2026-10-24_s03.yaml` (S1, S0, A2); `lab/evidence/V7R-010/i2c_frame/*.i2c_frame.txt` (i2c_frame.py `--expect D6` on CSVs cropped to −30…+40 µs by `lab/evidence/V7R-010/i2c_frame/crop.py`, identical to V7R-009's; originals in `lab/captures/V7R-010/`, iCloud backup); `lab/evidence/V7R-010/png/`; v7 log `lab/evidence/V7R-010/2026-10-24_V7R-010_v7_01.txt` (trimmed: blank lines and the relbus help text removed).

Validation (both logs `passed: true`): V5 excess S2 1.04 / 2.66 mV rms, master end 2.29 / 3.11 mV rms (limit 5), CH1 control sd 4.95 mV, offset −6.73 mV; CH2 control invalid (see Deviations). V6 springs on F (S2) / C (master end), 0 mm. V7 idle high 3.261–3.274 V at every placement used (D/E, A/B, K/B, A/B). V8 `Write:d6` + NACK at S2, S1, S0, A2.

| Arm | Point (CH1) | Captures: byte, 9th bit | SDA V_OL, 9 bit-means (mV) | Arm V_OL mean (mV) | Rise max CH1 / CH2 (ns) | SCL period (µs) | Log `bq` ACK | Controls |
|---|---|---|---|---|---|---|---|---|
| A1 | D (U5.6) | D6 NACK ×3 | 893.9–903.1 | 898.50 | 133.0 / 128.0 | 2.500 | 0 % (0/490) | pass |
| S1 | A (TPIO43) | D6 NACK ×3 | 894.2–903.2 | 898.61 | 134.6 / 130.3 | 2.500–2.501 | 0 % (0/460) | pass |
| S0 | K (U3 pad 37) | D6 NACK ×3 | 895.9–905.6 | 900.48 | 133.3 / 127.2 | 2.500 | 0 % (0/500) | pass |
| A2 | A (TPIO43) | D6 NACK ×3 | 895.3–904.6 | 899.94 | 133.8 / 127.7 | 2.500 | 0 % (0/430) | pass |

Card quantities: V_OL(K) = 900.48 mV; V_OL(A) = mean(S1, A2) = 899.28 mV; V_OL(D) = A1 = 898.50 mV. |V_OL(K) − V_OL(D)| = 1.98 mV; |V_OL(A) − V_OL(D)| = 0.78 mV; V_OL(K) − V_OL(A) = 1.20 mV. Anchor (amended): |S1 − A2| = 1.33 mV (limit 20), both > 0.4 V. Zero offset beside V_OL (not subtracted): CH1 −6.73 mV (Cal ground); on-board CH1 means at ground (V5b) −12.1 mV (C/N), and the failed K seats read −11.8 / −12.7 mV. Timing (t_SU;DAT, t_HD;DAT): captured in the CSVs, not evaluated.

### Interpretation (session; labelled as such)
Interpretation: U3's ~0.90 V SDA low is already there at U3's own edge pad (K) and is the same, within 2 mV, at TPIO43 and at the BQ's pin. Nothing along the copper adds to it; the low comes from U3 or from what loads its pad, not from the path after it. The test had limited power against H2/H3 as stated: at a few mA, board copper drops microvolts, so only a break or a series fault (e.g. a cracked joint) could have produced a step; none is seen. The same wire is pulled to ~0.1 V by the INA/TCA ACKs (V8 screens, V7R-009), so the bus can be pulled low; the weak low is specific to U3 driving SDA, while U3's SCL lows sit near 0.1 V. Exploratory, argued only: GPIO43 is U0TXD; if the UART0 TX output (idle high) were still routed to that pad while the I²C controller pulls it low, the two drivers would fight and settle at an intermediate level. SCL's pad (GPIO44 = U0RXD, an input) would not fight. This is not measured; it sits under master: pin role. The semi-transparent coating on U3's pads is unidentified [verify]; it delayed contact at K but V7 there passed once contact was made.

## Conclusion
- Outcome row matched: row 1 — V_OL(K) = 900.48 mV > 0.4 V, |V_OL(K) − V_OL(D)| = 1.98 mV < 100 mV, |V_OL(A) − V_OL(D)| = 0.78 mV < 100 mV; anchor (amended, at A) 1.33 mV ≤ 20 mV; all controls pass in all four arms.
- Hypotheses excluded: H2 (low lost along U3 → TPIO43 copper) and H3 (lost along TPIO43 → U5.6) — measured-refuted. H1 weakly supported (the elevated low is present at U3's pin). M not supported: four placements, two grounds, each validated; every capture's NACK agrees with its log; values agree across points to 2 mV.
- **Strength:** measured-refuted (H2, H3; one board, one rigid, A/B/C/A with the anchor amended to A, 3 captures per arm); H1 measured-supported only in the weak sense of the row (location, not mechanism); `lab/evidence/V7R-010/`
- Deviations: (1) Anchor amended before any anchor data (598369c, user "a"): A2 at A by a single-tip move instead of a full move back to S2, to limit probe moves; V_OL(D) rests on A1 alone and drift at D is not checked. (2) V5a control CH2 on the Cal signal, not ground: CH2 V5 invalid at both grounds; accepted (user "b"; CH2 = SCL carries no counted number). (3) `val_V3_02` captured at the wrong scale/offset; recaptured as `_03`. (4) AUTO pressed twice before V3 (V3 then sets every setting). (5) Re-seats: S1 CH2 off pad B once (`val_V7_02`); K needed three seats (coating on U3's pads, operator report). (6) `val_V7_03` captured by the operator in another terminal while the session's command checker gave no verdict; output pasted. (7) Analysis on cropped CSVs (user choice a, as V7R-009; Planner relay open). (8) Banner control not observed; SCL period 2.500 µs in all 12 captures stands in. (9) CH2 at B showed spike bursts at `val_V7_03` (sd 29.56 mV); not at later V7 captures at B (sd 4.7–5.1 mV).
- Revert-on-null done: yes (not a null; revert per card) — U3 on v7-clean motion-play-v7-diag (90053af), Nano on the blank sketch, probes off the board, both boards unplugged
- Result commit: self

---
test_id: V7R-016
title: "U3 SDA low and BQ ACK vs far-end pull-up on the J6 pigtail, each level set up three times in mixed order, with stub power-up repeats (USB replug, RTS reset), at TPIO43"
status: pre-registered
created: 2026-10-27
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: "u3-drv2"     # V7R-012 drive build, original binary f8ebf3fc (lab/evidence/V7R-015/u3-drv2-f8ebf3fc.bin; GPIO43 CAP_2 = default drive, read back), flashed 2026-10-26 23:42 for V7R-015 and still on U3. Not reflashed for this card. End: revert to motion-play-v7-diag (also closes V7R-015's deferred revert). User-approved for this card ("1. approved"); RTS arms "2. ok"; 2 captures per arm "3. ok"; photos + DMM digits "4. yes"
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2. Nano ESP32 powered on the blank sketch throughout (power order, V7R-008)
  hardware_config: "As V7R-015 end (notebook 2026-10-27 s02): J6 JST-SH pigtail (black = pin 1 +3.3 V in the breadboard 'V' rail; red = pin 2 GND → Nano GND column; blue = pin 3 SDA alone in the 'G'-labelled rail; yellow = pin 4 SCL dangling). J4, J5 empty. Rigid #1 off the bench. No battery. TPIO43 green / TPIO44 yellow pad wires → ~175 mm Dupont → Nano A4 / A5. USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Two SQ500 in PCBite arms seated at S1 (CH1 tip A, CH2 tip B, springs C), validated in log 2026-10-26_s02, not moved since V7. v7 powered since the V7R-015 S0b power-up (~00:25)."
variable_changed: "Far-end pull-up on SDA at the J6 pigtail's far end, selected by which breadboard row blue's Dupont pin is in (each resistor fixed between the 'V' rail and its own row; one empty row): none (stub) / 47 kΩ / 10 kΩ / 4.7 kΩ, each set up three times in mixed order, one power-up per set-up. Stub power-up repeats with nothing touched (USB replug, RTS reset) are replicates of the stub level, not a second variable: they separate the boot from the breadboard touch (declared, M-boot / M-touch / M-rts)."
structure: "Replicated blocks: C0 (V7R-015 S0b boot read before anything is touched); step R (resistor placement); pre-block stub arms S-0 (after placement) / U1 (USB replug) / T1 (RTS reset); three blocks, each holding every level once in a different order; post-block T2 (RTS reset). 17 arms, at S1 with no probe move. Not A/B/A: replication across set-ups replaces the bracketing anchor (V7R-015's anchor failed at the set-up level)"
revert_on_null: yes           # end: U3 on v7-clean motion-play-v7-diag; Nano blank (unchanged); probes per the user's call at the end (recorded in the notebook)
---

# V7R-016 — U3 SDA low vs far-end pull-up, replicated set-ups

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | U3's GPIO43 low behaves as a resistive sink: V_OL rises about linearly with the added far-end current, slope 0.3–1.5 kΩ | checkpoint @ V7R-014; V7R-015 (void); map: master: module/path |
| H2 | U3's SDA low does not depend on the added far-end current | V7R-013 confounds; map: mux |
| H3 | BQ's ACK is set by the SDA low level: one switching level sorts every arm | map: slave: BQ × master; F-14 |
| H4 | BQ's ACK follows the presence of a far-end path, not the low level | map: mux, master: timing; F-2 |
| M-boot | U3's low differs between power-ups with nothing on the bench touched (board or boot state) | V7R-015 anchor fail; map: measurement |
| M-touch | U3's low differs with breadboard insertions (contact, lead position), not with power-ups alone | V7R-015 anchor fail; map: measurement |
| M-rts | The boot type (esptool RTS reset vs USB replug) shifts U3's low | V7R-015 deviation (4): S0a after an RTS reset |
| M  | Measurement artefact: probe contact lost, trigger catching the wrong frame, image not as declared, resistor or rail value wrong, scope and log disagreeing | always listed; §4.2 |

**Magnitude (argued, for H1; checkpoint @ V7R-014).** At ~0.6 kΩ in series, I_far ≈ 55 µA / 0.25 mA / 0.55 mA for 47 / 10 / 4.7 kΩ, so V_OL ≈ stub + ~33 / ~150 / ~330 mV. V7R-015's between-power-up difference at the stub (107 mV) is larger than the 47 kΩ step and comparable to the 10 kΩ step, so a single set-up per level cannot resolve them; three set-ups per level can if the set-up spread is ≲ 40 mV.

## Confounds (declared; not separated by this card)
- **Pigtail, no rigid**, as V7R-015: BQ is the only marker.
- **I_far computed, not measured:** I_far = (V_rail − V_OL)/R_meas. V_rail by DMM once ('V' rail to Nano GND column, powered, at S-0). R_meas by DMM, digits reported, before the first insertion.
- **Power-up at every set-up** (unplug the v7 at the Mac end, change, plug in), as V7R-013/-015. A set-up therefore changes both the breadboard and the boot; the no-touch stub arms (U1, T1, T2) give the boot alone; C0 is no power-up at all.
- **RTS reset:** the session runs `esptool.py --port <v7> read_mac` (default reset into the ROM loader, then hard reset via RTS), the same sequence that ended the V7R-015 flash before S0a, without a write. The serial logger is stopped for it and restarted.
- **Move-blue layout (amendment 2026-10-27, before any counted arm; user: "yes, amend it for the move-blue layout"):** the three resistors are placed once at step R and not touched again: one leg each in the 'V' rail (with black), the other leg in its own 5-hole terminal row, three rows that connect to nothing else; one further empty row is the stub row. Each set-up moves only blue's Dupont pin into the arm's row. Differences from V7R-015: the stub node is a 5-hole row, not the 'G' rail (a few pF; stub capacitance tombstoned, L-Ph5/6d); idle resistors hang from the 'V' rail with open far ends (no current). M-touch now means blue's pin contact, the same action for every level. The operator photographs the breadboard after each change.
- **C0 is not a new power-up:** it is the V7R-015 S0b boot (~00:25), read hours later; compared with S0b (676.72 mV) for within-boot drift.
- **Timing:** captured in the CSVs, not evaluated (Planner relay 2026-10-24).

## Predictions and exclusions (written before the run)
Counted per arm: V8 PNG, then 2 SINGLE captures on the 0x6B write address trigger (V7R-015 within-arm spread ≤ 2.2 mV over 15 captures). Per capture: decoded byte, 9th bit, SDA V_OL on bits 5, 3 and R/W of D6. Arm value V = mean of the 6 bit-means. BQ class per arm from the `[scope]` lines spanning the arm's captures (≥ 50 cycles): ACK (≥ 95 %), NACK (≤ 5 %), mixed.
Controls in every counted arm (as V7R-015): V8 shows `Write:d6`; `[scope]` lines show `sda_drv=2 scl_drv=2`, `tca` = `ina` = n; no reboot within the arm; each capture decodes `D6` and its 9th bit agrees with the log's BQ result; SCL period 2.50 ± 0.01 µs; CH1 idle before the frame ≥ 3.135 V.
Definitions: R_boot = max − min of V over the no-touch stub arms U1, T1, T2 (power-up only). R_set(L) = max − min of V over level L's three block arms. Level mean m(L) over its block arms. Fit: least-squares line of the four m(L) vs mean I_far(L) (I_far = 0 for stub); R_fit = slope; residual = max |m(L) − fit|. Needs ≥ 2 complete blocks; with 2, R_set is over 2 arms.

**Part 1: set-up and boot repeatability** (rows exclusive; read first)
| Outcome (numeric; controls pass) | Excludes | Supports (weakly) |
|---|---|---|
| P1: R_boot ≤ 20 mV and every R_set ≤ 20 mV | M-boot, M-touch, M-rts at 20 mV (this session) | V7R-015's anchor fail not reproduced; §7 single-boot row re-measured for this config |
| P2: R_boot ≤ 20 mV and some R_set > 20 mV | M-boot (power-up alone) | M-touch |
| P3: R_boot > 20 mV, and T1 and T2 both ≥ 20 mV from U1 on the same side | — | M-rts, M-boot |
| P4: R_boot > 20 mV, otherwise | — | M-boot; M-rts not separated |
| Sub-result: \|C0 − 676.72 mV\| ≤ 20 mV / > 20 mV | — | within-boot stable over hours / within-boot drift (recorded) |

**Part 2: dose** (evaluated with any Part 1 row)
| Outcome (numeric; ≥ 2 complete blocks) | Excludes | Supports (weakly) |
|---|---|---|
| D1: level ranges do not overlap and order stub < 47k < 10k < 4.7k; 0.3 ≤ R_fit ≤ 1.5 kΩ; residual ≤ 25 mV | H2 | H1 |
| D2: m(4.7k) − m(stub) < 40 mV, or the stub and 4.7k ranges overlap | H1 in the stated form, at this resolution | H2 |
| D3: neither D1 nor D2 | — | dose not resolved at the set-up level; V vs I_far recorded as measured |
| B1: every ACK arm's V below every NACK arm's V (no mixed arm), with at least one stub arm NACK or one resistor arm ACK | H4 | H3; BQ's switching level bracketed between the highest ACK and lowest NACK V |
| B2: an ACK arm's V ≥ 20 mV above a NACK arm's | H3 as the sole cause | H4 |
| B3: all arms one class, or B1 holds with every stub arm ACK and every resistor arm NACK | — for H3/H4 (level and path presence not separated) | recorded |
| B-mixed: any mixed arm | — | its V marks BQ's switching region (reported with B1/B2) |
| 47 kΩ sub-result | — | R47 class per set-up: NACK ×3 reproduces L-Ph5 in this config; ACK ×3 does not; split recorded with V |
| Void: fewer than 2 complete blocks, or a control fails in an arm (that arm void; Part 2 void if any block arm is void and fewer than 2 complete blocks remain) | — | M |

## Setup
- Measurement log: new, `lab/log/2026-10-27_s03.yaml`. Validation carried from `lab/log/2026-10-26_s02.yaml` (V1–V7 and decode passed; probes seated, not moved since V7; user, notebook 2026-10-27 s02): values copied with that note; V8 per arm. No re-validation unless a probe moves.
- Scope: as V7R-015 (DHO804 at 192.168.50.2; CH1 1 V/div −3.3 V, CH2 0.5 V/div −1.65 V, BW OFF, DC; V8 at 20 µs/div, counted at 10 µs/div, 10 kpts; trigger I²C ADDR 107 WRITE, SINGLE; decode set). Session helper: V7R-015 `runarm_frames.sh` with 2 counted captures.
- Position **S1**. **Probe moves: none.** If a probe moves or is bumped: stop; V7 + V8 again before the next counted arm (procedure).
- Readout: v7 serial logged by the session (`lab/captures/V7R-016/2026-10-27_V7R-016_v7_01.txt`, `=== <arm>` markers).
- Resistors: the 47 kΩ, 10 kΩ and 4.7 kΩ from V7R-015, DMM digits (or "within 1 % of nominal") reported out of circuit; legs trimmed to ~8–10 mm and placed once at step R (move-blue layout). A 1 % R error moves I_far by ≤ 1 % (≤ ~3 mV under H1), below every threshold.
- Photos: one phone photo of the breadboard after each change (`<arm>.jpg`), handed over at the end into `lab/captures/V7R-016/photos/`; the session writes what it reads from each into the log.
- Time: ~2 h bench. If 105 min have passed, finish the current block and go to End (T2 dropped first).

## Arm order (fixed before the run)
Note (amendment): C0 is read before step R, with nothing touched, so it stays the V7R-015 S0b boot. Step R (resistor placement, blue from the 'G' rail into the stub row) is done with the v7 unplugged; S-0 is the stub after it (a touch stub, outside R_boot and the blocks; recorded).
| # | Arm | Bench action before it | Power |
|---|---|---|---|
| 1 | C0 | none | none (V7R-015 S0b boot) |
| — | step R | resistor placement; blue to the stub row | v7 unplugged, plugged in at the end of R |
| 1b | S-0 | none after R | (the R power-up) |
| 2 | U1 | none | USB replug |
| 3 | T1 | none | RTS reset (session) |
| 4–7 | Block 1: R10-1, S-1, R4.7-1, R47-1 | change to the arm's level | USB replug each |
| 8–11 | Block 2: R4.7-2, R47-2, S-2, R10-2 | change to the arm's level | USB replug each |
| 12–15 | Block 3: R47-3, R4.7-3, R10-3, S-3 | change to the arm's level | USB replug each |
| 16 | T2 | none | RTS reset (session) |

## Procedure (physical steps for the operator)
The session runs every SCPI command, esptool call, marker and capture; one instruction block per step.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| C0 | Nothing (session: V8, 2 captures), before step R | probes untouched | what the decode band shows |
| R | DMM the 47 kΩ, 10 kΩ and 4.7 kΩ (out of circuit); v7 unplugged at the Mac end; trim legs, place each between the 'V' rail and its own row; move blue from the 'G' rail into an empty row (the stub row); photo; plug the v7 back in | each resistor's far leg alone in its row; blue alone in the stub row | three readings; which row is which; photo name |
| S-0 | DMM 'V' rail to Nano GND column; then nothing (session: V8, 2 captures) | PWR LED on; probes untouched | V_rail digits; decode band |
| U1 | Unplug the v7 at the Mac end; plug it back in; nothing else touched | PWR LED; probes untouched | LED; decode band |
| T1 | Nothing (session resets U3 by RTS) | PWR LED | decode band |
| set-up (arms 4–15) | Unplug the v7 at the Mac end; move blue's pin to the arm's row (resistor row, or the empty row for S); photo; plug in | blue alone in the arm's row; resistors untouched; probes untouched | row used; photo name; LED; decode band |
| T2 | Nothing (session resets U3 by RTS) | PWR LED | decode band |
| End | Session reverts U3 to diag; then per the user's call on the probes; unplug the v7 at the Mac end, unplug the Nano | as stated | bench state; photos handed over |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
### Measured values (from log; cite `lab/evidence/V7R-016/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: yes/no (commit)
- Result commit: self

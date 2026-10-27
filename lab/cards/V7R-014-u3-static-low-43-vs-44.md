---
test_id: V7R-014
title: "U3 static low as plain GPIO, I²C controller detached: GPIO43 (SDA) vs GPIO44 (SCL) held low, TCA channel 2 open"
status: pre-registered
created: 2026-10-25
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: "u3-static"   # run image throughout: V7R-014 static build u3-static (firmware.bin 493a0235; modes f/r/3/4 by serial), user-approved delta ("approve the firmware changes"). End: revert to motion-play-v7-diag
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2. Nano ESP32 powered on the blank sketch throughout (power order, V7R-008)
  hardware_config: "As V7R-013 end (notebook 2026-10-25 s08): v7 #0003, no battery, J4 empty. J6: sensor rigid #1 (SW1 ON = PCA 0x76, SW2 OFF) via ~400 mm cable. J5: pigtail, black in breadboard 'V' rail with the 10 kΩ, blue + yellow dangling, red → Nano GND. TPIO43 green / TPIO44 yellow pad wires → ~175 mm Dupont → Nano A4 / A5. USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Two SQ500 in PCBite arms at S1 (A/B, ground C)."
variable_changed: "Which U3 pad is held low as a plain open-drain GPIO output with the I²C controller detached: GPIO43 (SDA, TPIO43) vs GPIO44 (SCL, TPIO44). The other pad is held released (high). TCA channel 2 open (rigid #1 on the bus) in both."
structure: "A/B/A — GPIO43 low / GPIO44 low / GPIO43 low, all in one boot by serial command, at S1 with no probe move; preceded by a reference arm F (I²C frames, same build) that is recorded, not compared as an arm"
revert_on_null: yes           # end: U3 on v7-clean motion-play-v7-diag, Nano blank (unchanged), probes off the board
---

# V7R-014 — U3 static low as plain GPIO, GPIO43 vs GPIO44

Map regions cut: **master: module/path** (U3's GPIO43 pad, its driver and the module path to TPIO43) vs **master: peripheral config / pin role** (the I²C controller's output through the GPIO matrix), and **master supply** (a U3-wide sink problem would show on both pads). STATE §8 option (e); user: "ok, draft V7R-014 for (e)". 10th card in the master bundle region.

Question: V7R-009 to -013 show U3's SDA low at ~0.90 V (≈0.68 V with the far-end path out), set neither by the drive setting nor by the copper, while U3's SCL lows and every other device's lows reach ~0.1 V. Does GPIO43 sink to a valid low when it is a plain GPIO output, with the I²C controller out of the path?

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | U3's GPIO43 pad or its module path cannot sink to a valid low at this load, whoever drives it: as a plain GPIO its static low is about the same as the I²C low | map: master: module/path; V7R-010, V7R-012, V7R-013 |
| H2 | GPIO43 sinks normally as a plain GPIO; the elevated low appears only when the I²C controller drives the pad (matrix output path, open-drain emulation, controller output) | map: master: peripheral config, master: pin role; V7R-011 |
| H3 | Neither of U3's pads sinks well statically (a U3-wide cause: supply or ground return), although SCL frames reach ~0.1 V | map: master supply |
| M  | Measurement artefact: probe contact, a pad not in the mode the firmware claims (read-back), the TCA channel not open, or a trace that is not static | always listed; §4.2 |

**Magnitude (argued, for H1).** In a frame the SDA low settles within ~0.2 µs of a 1.25 µs bit (V7R-009 rise times ~130 ns), so the frame low is close to the DC low at the same load. If the pad (or its path) is the limiting element, a static GPIO43 low with the same load should sit within ~100 mV of the reference I²C low (~0.90 V). If the pad is healthy, the S3's GPIO output-low spec (V_OL ≤ 0.1 × VDD = 0.33 V at its rated sink current [verify: ESP32-S3 datasheet DC characteristics]) gives ≤ 0.2 V at the ~1–2 mA this bus sinks.

**Load (declared).** SDA and SCL carry similar pull-up networks (main pull-ups, rigid #1's pull-ups through TCA channel 2), not equal ones. GPIO44 is a within-chip control for "a plain GPIO low on this module reaches a valid low at this kind of load", not a matched-current comparison.

## Confounds (declared; not separated by this card)
- Static vs frame: the reference arm F measures SDA lows inside frames (cropped CSV, `i2c_frame.py`), arms A1/B/A2 measure a DC level (mean over a 10 kpt record). Same probe, same placement, same load.
- In A1/A2 SDA is held low while SCL is high (a START with no clock); in B SCL is held low (INA219 resets its interface after 28 ms of a low line, SBOS448G note 6). Slaves see no completed transaction; the TCA register is read back at every mode change.
- Mode changes are serial commands to the running build: no reflash, no power cycle and no probe move between F, A1, B and A2.
- CH2 at B shows spike bursts at idle (V7R-010, V7R-012); in arm B CH2 carries the counted number, so its V5 must pass at this placement (V7R-012 showed it can after a re-seat).

## Predictions and exclusions (written before the run)
Counted per arm (A1 = GPIO43 low, B = GPIO44 low, A2 = GPIO43 low): 3 captures, EDGE trigger on CH1, sweep AUTO, 10 µs/div, 10 kpts; per capture the mean and sd of CH1 and CH2 over the whole record (`i2c_frame.py`, idle mode). V43 = mean of the A1 and A2 CH1 means; V44 = mean of the B CH2 means.
Reference arm F (frames, before A1): V8 then 3 captures on the 0x6B address trigger, SDA V_OL as V7R-013 (bits 5, 3, R/W; cropped CSV). Vref = mean of the 9 bit-means.
Controls: (c1) in each arm the released pad's channel reads ≥ 3.135 V (contact and release); (c2) each arm's `[regs]` lines show both pads `mcu_sel=1`, `out_sig=256` (simple GPIO output), `od=1`, `oe=1`, and `out=0` on the driven pad only, `out=1` on the other; (c3) `[static]` line at each mode change shows `tca_write_err=0 tca_reg=0x04`; (c4) no reboot from F to A2; (c5) the driven channel's sd ≤ 10 mV (static trace); (c6) F: every capture decodes `D6` with the 9th bit high, the `[scope]` lines show `ina` = n and `bq` ACK ≤ 5 %, and |Vref − 898 mV| ≤ 30 mV (V7R-012/-013 A-arm state reproduced).
Anchor: |V43(A1) − V43(A2)| ≤ 20 mV.

| Outcome (numeric; anchor and controls pass) | Excludes | Supports (weakly) |
|---|---|---|
| Row 1: V43 ≥ 0.6 V and \|V43 − Vref\| < 100 mV; V44 ≤ 0.2 V | H2, H3 (measured-refuted: the elevated low does not need the I²C controller, and is not U3-wide) | H1 |
| Row 2: V43 ≤ 0.2 V; V44 ≤ 0.2 V | H1, H3 (measured-refuted: GPIO43 sinks to a valid low as a plain GPIO) | H2 |
| Row 3: V43 ≥ 0.6 V; V44 ≥ 0.6 V | H2 | H3; recorded, stop and investigate (SCL frames reach ~0.1 V) |
| Row 4: any other pattern (V43 or V44 between 0.2 and 0.6 V, or V43 ≥ 0.6 V with \|V43 − Vref\| ≥ 100 mV, or V43 ≤ 0.2 V with V44 > 0.2 V) | — | recorded as measured, no exclusion; values go to the map |
| Anchor fails: \|A1 − A2\| > 20 mV | — (result void) | M or a changed state; stop and investigate |
| A control fails (c1–c6) or the session's validation fails | — (that arm void; result void if any arm is void) | M |

## Setup
- Measurement log: `lab/log/<date>_s01.yaml` (new session). Full validation at S1 per `lab/procedures/dho804-setup-validation.md` (V1–V8); V7 with the build in boot mode `r` (bus idle, both pads released; replaces the relbus image), V8 in mode `f`. V9 not due (V7R-002, same probes and settings). Validation must read `passed: true` before arm F.
- Captures: `val_V3`, `val_V5ctl`, `val_V5`, `val_V7`, `val_V8`; reference `F`; counted `A1`, `B`, `A2`.
- Scope: 0.5 V/div, −1.65 V, BW OFF, DC, 10 µs/div, 10 kpts on both channels. F and V8: I²C ADDR 107 WRITE trigger, SINGLE (V8 at 20 µs/div). A1/B/A2: EDGE on CH1, AUTO.
- Position **S1** (picture `lab/evidence/V7R-010/img/v7-s1-points.png`): CH1 tip A (TPIO43), CH2 tip B (TPIO44), both springs on C (C9.1), away from C9's +3.3 V end. V5: tips on N (C10.1).
- **Probe moves (user rule, 2026-10-25), in run order:**
  1. Off board → S1-V5 (springs on C, tips on N): **full placement** (springs + both tips), the only one in the card.
  2. S1-V5 → S1 (tips N → A and B, springs stay on C): both tips, springs untouched.
  3. F, A1, B, A2: **no moves** (mode changes by serial command).
  4. End: lift both arms off the board.
  Total on the board: 1 full placement, 1 two-tip move, 0 moves between arms.
- Readout: v7 and Nano serial logged by the session (`lab/captures/V7R-014/<date>_V7R-014_{v7,nano}_01.txt`, `=== <arm>` markers). Mode commands are sent by the session through the logger's command file (`lab/evidence/V7R-014/src/session/serlog.py`) and appear in the log as `>>> <cmd>` beside the `[static]` reply.
- Image: `u3-static` (`lab/evidence/V7R-014/src/u3/`, firmware.bin 493a0235), flashed once after P0; boot mode `r`. End: diag from a v7-clean worktree at 90053af.

## Procedure (physical steps for the operator)
The session runs every SCPI command, flash, serial command and capture; one instruction block per step.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| P0 | Bench: scope on, Ethernet adapter in; Nano plugged in first, then the v7 | scope waveform view; v7 PWR LED | done |
| V1–V4, V5a | Scope only; probes on Cal (V3 per channel), then tips + springs on Cal ground | per procedure | per procedure |
| S1 V5b–V7 | Unplug the v7; springs to C, tips to N; look; plug in (V5b). Unplug; CH1 tip to A, CH2 tip to B; look; plug in (V7, mode r) | nothing on an X pad; springs on C | positions |
| Decode | Scope menu: Decode 1 fields per procedure | fields as listed | any field that differed |
| V8, F | Nothing (session: mode f, V8, 3 captures) | band shows `Write:d6` | what the band shows |
| A1, B, A2 | Nothing (session: modes 3, 4, 3; 3 captures each) | none | anything that changed on the bench |
| End | Session reverts U3 to diag; then unplug the v7, lift the probes off the board, unplug the Nano | no LEDs; probes clear | bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
Session 2026-10-26 s01 (log `lab/log/2026-10-26_s01.yaml`).
- Image check (session, before P0): rebuild of `src/u3/` gave `b3205a0b…` ≠ `493a0235…`; a second rebuild in the original layout (`u3static/src/main.ino`) gave `0a31c4a6…`. Diff vs the original 493a0235 binary: all loadable segments identical; image differs only at 0xb0–0xcf (embedded ELF SHA256) and the last 33 bytes (checksum + appended SHA256); ELF differs only in `.debug_line`/`.debug_str` (absolute build folder, sketch file name). User: "I wouldn't rebuild". Flashed the original 493a0235 binary (`shasum -c` OK) at 0x10000 with esptool `--flash_mode keep`, 13:35. Planner relay `lab/relays/2026-10-26_RELAY-planner-card-build-reproducibility.md`.
- P0: "1. yes 2. on 3. no 4. nothing". Logger started after the flash: the first boot banner is not in the v7 log.
- V1/V3 CH1: "Kind of, but it's too 'zoomed in' and the scope is 'running'" (after AUTO, before V3 settings). V3 CH1: "Square wave, top flat, square corners -- yes"; panel "Vamp: 3.0037V, Vtop: 2.9677V, -36mV". V3 CH2: "yes"; panel "vamp(c2): approx 3.003V, vtop(c2): 2.9677V, vbase(c2): -36mV" (capture: 3.0208 V).
- First V2 batch: one `-110,"Command header err"` queued; source not identified; every read-back correct, queue clear after.
- V5a: "Both are showing between 21 and 26 mV". V5b: "both around 22-26mV".
- V7 first capture (`val_V7_01`): CH1 at ~0.85 V with short returns to ~3.29 V every ~8.5 µs; CH2 flat ~3.26 V; U3 `[regs]` GPIO43/44 `out=1 in=1`. Operator Vpp: "both are moving around so I couldn't say". Then operator, before the redo step: "I unplugged the v7 usb from the mac and reseated both probes (tips and ground springs)" — **one extra full placement**. Operator pressed AUTO; session re-set and read back every V5/V7 setting.
- V7 second capture (`val_V7_02`): CH1 mean −11.3 mV, sd 5.37 mV (ground level); CH2 3.261 V; U3 GPIO43 `in=1`. Board unplugged, CH1 tip re-seated on A — **one extra single-tip move**; where the tip was before: "didn't see".
- U3 resets in the v7 log (uptime back to a few ms) at ~15:12:50, 16:52:33, 16:54:47, 16:55:54, 16:57:30, 17:05:19, 17:06:07, 17:07:00, 17:07:46; the card's steps account for two plug-ins (V5b, V7). Not explained; none from F onward to be checked (c4).
- Decode setup: "1. no 2. yes" (no field differed; band present).
### Measured values (from log; cite `lab/evidence/V7R-014/...`)
- Validation: V3/V4 Vamp CH1 3.0037 V, CH2 3.0208 V. V5 (`val_V5ctl_01` / `val_V5_01`): excess CH1 0.00, CH2 1.72 mV rms, PASS (springs' first seat). V5 on the re-seated springs, `noise_floor.py` with `val_V7_03` as DUT: excess CH1 4.33, CH2 2.21 mV rms (≤ 5; idle-high pad, not a ground point). V7 (`val_V7_03`): CH1 3.273 V, CH2 3.262 V, idle, PASS. V8 (`val_V8_01`, 20 µs/div, 0x6B write trigger): band `Write:80`, `Write:d6` (red mark), `Write:e0`.
- F (U3 mode f, 400 kHz; `i2c_frame/F_0n_frame.txt`): F_01 D6, 9th high, 2.500 µs, V_OL 901.1/892.2/896.6 mV; F_02 D6, high, 2.500, 900.7/891.7/896.4; F_03 D6, high, 2.500, 900.7/892.2/896.0. **Vref = 896.40 mV** (n = 9). `[scope]` at 17:33:09: n=930 tca=930 ina=930 bq=0. CH1 idle −45…−25 µs: 3.2752 / 3.2748 / 3.2750 V. c6 pass.
- A1/B/A2 (EDGE CH1, AUTO, 10 µs/div, 10 kpts; mean / sd over the whole record, CSV; not offset-corrected — V5a offsets CH1 −11.83, CH2 −14.27 mV):
  | Capture | CH1 mean mV | CH1 sd | CH2 mean mV | CH2 sd |
  |---|---|---|---|---|
  | A1_01 / _02 / _03 | 845.69 / 845.72 / 845.89 | 8.04 / 8.06 / 7.88 | 3260.46 / 3260.79 / 3260.45 | 5.42 / 5.36 / 5.41 |
  | B_01 / _02 / _03 | 3272.84 / 3273.63 / 3272.98 | 5.45 / 5.71 / 5.59 | 48.61 / 49.28 / 48.41 | 5.78 / 5.88 / 6.09 |
  | A2_01 / _02 / _03 | 845.52 / 845.32 / 846.14 | 8.00 / 8.23 / 7.89 | 3260.39 / 3260.36 / 3261.08 | 5.46 / 5.61 / 5.37 |
- V43(A1) = 845.77, V43(A2) = 845.66, anchor |A1 − A2| = 0.10 mV; **V43 = 845.71 mV**; **V44 = 48.77 mV**; V43 − Vref = −50.69 mV.
- Controls: c1 released pad 3.260 V (A1, A2 CH2), 3.273 V (B CH1). c2 `[regs]` at each mode change: both pads `mcu_sel=1 out_sig=256 od=1 oe=1`; driven pad `out=0 in=0`, other `out=1 in=1` (A1 17:34:11, B 17:34:37, A2 17:35:02). c3 `tca_write_err=0 tca_reg=0x04` at each. c4 no banner and uptime monotonic from `>>> f` (17:31:36) to the end of A2. c5 driven-channel sd 7.88–8.23 (A), 5.78–6.09 mV (B). Operator: no bench action during A1–A2.
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: yes/no (commit)
- Result commit: self

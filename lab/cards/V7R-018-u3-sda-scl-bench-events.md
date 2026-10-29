---
test_id: V7R-018
title: "U3 SDA (TPIO43) and SCL (TPIO44) through bench events on #0003 — power-up, SW2 reset, reflash of the same image, rigid #1 hot-plugged into J5 — excursions outside the rails, and the ROM's TX low on GPIO43 at power-up"
status: recorded
created: 2026-10-27
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: motion-play-v7-diag   # on U3 since V7R-016 End (upload 15:39:47 2026-10-27). V7 uses motion-play-v7-relbus from the same tag (validation only); diag flashed back before arm R0. E3 reflashes the same diag build. No firmware delta.
  board_id: v7-B3             # v7 #0003 (STATE §6 naming); U3 die rev v0.2
  hardware_config: "As V7R-016 end (STATE §6): J6 JST-SH pigtail (black = pin 1 +3.3 V in the 'V' rail; red = pin 2 GND → Nano GND column; blue = pin 3 SDA in row 15 with the 10 kΩ; yellow = pin 4 SCL dangling); 47 k row 10, 4.7 k row 20 (far legs alone), stub row 25. J4, J5 empty. Rigid #1 off the bench until E4 (SW1 ON = PCA 0x76, SW2 OFF, as V7R-013). No battery (user decision, card C entry). TPIO43 green / TPIO44 yellow pad wires → ~175 mm Dupont → Nano A4 / A5; Nano on its blank sketch, powered before the v7 and whenever the v7 is (power order, V7R-008). USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano."
variable_changed: "The bench event applied to the powered v7: none (idle anchors R0, R1) / USB power-up (E1a, E1b) / SW2 (EN) press (E2) / reflash of the same diag build over USB (E3) / sensor rigid #1 hot-plugged into the empty J5 (E4, last). SCL on the same U3 is the within-chip control for every event."
structure: "single (justify): characterisation across events, not a contrast of two levels; each event once, bracketed by idle anchors R0 (before E1a) and R1 (after E3, before E4) at the same scope settings. E4 is last because it changes the hardware state (rigid stays in J5); R2 after it is recorded, not an anchor"
revert_on_null: n/a           # no firmware or hardware delta; at End rigid #1 is unplugged from J5 with the v7 unplugged (or left, user's call; recorded)
---

# V7R-018 — U3 SDA/SCL through bench events: excursions and the ROM TX low

Map regions cut: **master: identity (c)** (a v7-caused stress route on GPIO43: an over/under-voltage excursion at a routine event, untested) and **master: pin role** (ROM/boot-time state of GPIO43, which V7R-011 did not cover); the ROM TX low also bears on **master: module/path** (whether the ~0.54 kΩ low-side path shows when the ROM drives GPIO43 as U0TXD through IO_MUX function 0, not the GPIO matrix of V7R-014). STATE §8 "card C"; design decisions in the notebook entry "card C design decisions" (2026-10-27).

Questions: (1) Does SDA, unlike SCL, leave the 0–3.3 V range during power-up, reset, flashing or a cable hot-plug? (2) Does the ROM drive its boot output onto SDA, and does its low sit at the elevated level the I²C and plain-GPIO lows show?

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | SDA-specific excursion: at ≥ 1 event, CH1 goes above V_hi or below V_lo (limits below) and CH2 does not in the same event | map: master: identity (c); desk (e) "transients at cable plug-in not covered" |
| H2 | Common excursion: at an event where CH1 crosses a limit, CH2 also crosses one (rail, ground return or probe-common) | map: master supply / measurement |
| H3 | No excursion on either line at any event | — |
| H4 | The ROM's U0TXD lows on GPIO43 at power-up sit at the pad-resistance level (|V_TX − 677 mV| ≤ 100 mV): the low-side path shows with the IO_MUX UART path too | map: master: module/path; V7R-014, V7R-016, desk (d) |
| H5 | The ROM's U0TXD lows reach a normal low (V_TX ≤ 0.20 V): the elevated low needs something present only after boot (matrix routing, app pad setup, time/heating) | map: master: pin role (boot-time state); V7R-011 |
| M  | Measurement artefact: probe pickup on fast edges or at hand movement near the arms (spring grounds, PCBite), peak-detect behaviour at 5 ms/point not as assumed, roll-mode memory depth, a probe moved by the event | always listed; §4.2 |

**Limits (declared).** V_hi = V7 idle-high (CH1, this session) + 0.30 V; V_lo = −0.30 V. Source: ESP32-S3 I/O absolute maximum taken as −0.3 V to VDD + 0.3 V **[verify: ESP32-S3 / WROOM-1 datasheet absolute maximum ratings; not in the repo]**. An event crosses a limit only if it also lies beyond that channel's R0 envelope (R0 Vmax + 50 mV, or R0 Vmin − 50 mV). If R0 itself crosses a limit on a channel, that limit is void for that channel (M) and the card reports the values only.

**Magnitude (argued).** SDA's only sources are U3, R28 (2.2 kΩ to the shared +3.3 V), the 10 kΩ far end (same rail), the Nano's input and open-drain slaves (desk (e)). A 1 V excursion beyond a clamp through ≥ 2.2 kΩ injects ≤ ~0.5 mA. So a counted excursion is a credible damage route only if it is several volts or brief and capacitive (connector contact). The card records the peak and its width (points beyond the limit × 5 ms); any damage inference stays argued.

**ROM TX low model (argued, for H4).** At power-up the TCA's channels are closed (power-on reset state), so SDA carries R28 ∥ the internal pull-up (2.098 kΩ) only. With ~545 Ω to ground: 3.276 V × 545 / (2098 + 545) ≈ 676 mV, the V7R-016 stub level (677.1 mV). A normal pad (~30 Ω, V7R-014 GPIO44, V7R-017) gives ≈ 45 mV.

## Confounds (declared; not separated by this card)
- One event of each kind, one board, one seat. A null (H3) is for these events as done here, not for every power-up or plug-in.
- E2 hand near the board: the press can move a probe or couple into the arms (M). R1 after E3 checks the seat; the CH2 control shows common pickup.
- E3 resets U3 twice (into download mode, then the hard reset after writing), plus USB re-enumeration. Reported as one event.
- E4 at J5: whether J5's TCA channel is open at the moment of contact depends on the diag loop's phase (not controlled). Through a closed pass gate the rigid sees the TCA's pins, not U3's; the +3.3 V inrush into the rigid reaches every node on the rail.
- E1a/E1b power-up ramps from 0 V; V_lo is the only limit there below the idle level.

## Predictions and exclusions (written before the run)
Counted: per roll arm (R0, E1a, E2, E3, R1, E4, R2): one capture, CH1 and CH2 **Vmax** and **Vmin** over the whole record (scope `VMAX`/`VMIN` items, and min/max of the CSV; they must agree within 30 mV, control c3).
E1b: one SINGLE capture; V_TX = median of CH1 samples below 1.65 V that are ≥ 2 samples (4 µs) from any 1.65 V crossing and ≥ 1 ms after the trigger. Burst = ≥ 20 falling crossings of 1.65 V on CH1 after the trigger with CH2 > 1.65 V at every one of them.
Controls: (c1) R0 is in peak detect and catches the µs-wide frame lows: CH1 Vmin ≤ 0.50 V and CH2 Vmin ≤ 0.50 V (slave ACK and SCL lows ≈ 0.1 V, V7R-009); (c2) memory depth reads 10 k and acquisition type reads PEAK on every roll arm (NORMAL on E1b); (c3) VMAX/VMIN vs CSV agree within 30 mV; (c4) diag rows after each event show the pre-event pattern (`TCA2 … BQ:X(2)`, BASE/TCA0/TCA1 `BQ:.`); E4 may add TCA1 PCA/VCNL results (recorded); (c5) V8 passes before R0 and again before R1 (decode `Write:d6`).
Anchor: R1 vs R0, each of CH1 Vmax, CH1 Vmin, CH2 Vmax, CH2 Vmin within 50 mV.

| Outcome (numeric; anchor and controls pass) | Excludes | Supports (weakly) |
|---|---|---|
| X1: CH1 crosses V_hi or V_lo at ≥ 1 event; CH2 crosses neither at that event | H3, and H2 for that event | H1 (event named; peak and width recorded) |
| X2: at every event where CH1 crosses a limit, CH2 crosses one too | H1 for those events, H3 | H2 or M (not separated) |
| X3: neither channel crosses a limit at any event | H1, H2 (for these events, measured-refuted at the limits and 5 ms resolution) | H3 |
| X4: only CH2 crosses a limit | H3 | recorded as measured, no SDA conclusion |
| T1: burst present and \|V_TX − 677 mV\| ≤ 100 mV | H5 | H4 |
| T2: burst present and V_TX ≤ 0.20 V | H4 | H5 |
| T3: burst present, V_TX in 0.20–0.577 V or > 0.777 V | — | recorded as measured; map gets the value |
| T4: no burst (< 20 falling crossings in the 20 ms window) | — (ROM output not seen in this window; H4/H5 not tested) | recorded; ROM log disabled or later than 18 ms (not separated) |
| Anchor fails (any R1 − R0 > 50 mV) | — (X rows void; T rows stand on their own) | M or a moved seat; stop and investigate |
| c1, c2 or c3 fails, or validation fails | — (that arm void; c1 fail voids every roll arm: stop before E1a) | M |

## Setup
- Measurement log: new, `lab/log/2026-10-27_s04.yaml` (pass `--session` explicitly; capture.py's default would pick s03). Full validation per `lab/procedures/dho804-setup-validation.md` V1–V8 at S1; V7 on `motion-play-v7-relbus` (bus released), V8 on diag. V9 not due. `passed: true` before R0.
- Builds: from a fresh v7-clean worktree at 90053af in this session's scratchpad (`motion-play-v7-relbus`, `motion-play-v7-diag`); sha1 of each firmware.bin recorded; diag must match V7R-016 End's 166f5f40 or the difference is recorded before R0.
- Scope (roll arms): CH1 SDA tip A (TPIO43), CH2 SCL tip B (TPIO44), **1 V/div, offset −2 V** on both (screen −2 V … +6 V, so overshoot to ~6 V and undershoot to −2 V stay on screen), BW OFF, DC; **5 s/div** (50 s), AUTO sweep (roll), acquisition **PEAK**, 10 kpts. Captured with `capture.py --items VMAX,VMIN,VTOP,VBASe` (VMAX/VMIN not yet verified on 00.01.05: c3 checks them against the CSV).
- Scope (E1b): same channels; **2 ms/div**, trigger EDGE rising CH1 at 1.65 V, SINGLE, trigger point at 10 % of the screen, acquisition NORMAL, 10 kpts (2 µs/sample, ~4 per 115200-baud bit).
- Decode and V8 settings per procedure, restored for c5.
- Position **S1** (CH1 tip A, CH2 tip B, both springs on C = C9.1). **Probe moves (user rule, 2026-10-25), in run order:**
  1. S1 → off board (v7 unplugged): lift both arms, for V3/V4/V5a on Cal. **Removal.**
  2. Off → S1-V5 (springs on C, tips on N = C10.1): **full placement** (springs + both tips), the only one in the card.
  3. S1-V5 → S1 (tips N → A and B; springs stay): two-tip move.
  4. R0 to R2: **no moves.**
  5. End: user's call (leave seated, or lift).
  Total on the board: 1 removal, 1 full placement, 1 two-tip move. Flagged to the user before this commit.
- Readout: v7 serial logged by the session (`lab/captures/V7R-018/2026-10-27_V7R-018_v7_01.txt`, `=== <arm>` markers); esptool output for E3 kept verbatim in `lab/captures/V7R-018/`.
- Time: ~2 h bench. Validation first (~40 min). If 105 min have passed, finish the current arm and go to End; E4 and R2 are dropped first, then E2.

## Arm order (fixed before the run)
| # | Arm | Event (one physical action) | Scope |
|---|---|---|---|
| 1 | R0 | none; diag running ≥ 50 s | roll, PEAK |
| 2 | E1a | unplug the v7 at the Mac end, wait 5 s, plug it back in | roll, PEAK |
| 3 | E1b | unplug the v7 at the Mac end; session arms SINGLE; plug it back in | 2 ms/div SINGLE, NORMAL |
| 4 | E2 | press and hold SW2 (RESET, EN) ~1 s, release | roll, PEAK |
| 5 | E3 | nothing (session reflashes the same diag build) | roll, PEAK |
| 6 | V8 + R1 | none | V8 decode; then roll, PEAK |
| 7 | E4 | plug rigid #1's cable into J5 (rigid end already fitted) | roll, PEAK |
| 8 | R2 | none | roll, PEAK |

Roll arms: the session sets roll and RUN, the user waits ≥ 10 s before the action, does it, then waits ≥ 10 s (E3: until esptool exits and 10 s more); then the session captures (STOP). The event's time in the record comes from the serial log and the trace.

**SW2 pivot (declared, user decision).** If SW2 can't be pressed without touching a probe arm, a Dupont or the pigtail, E2 becomes **E2r**: the session resets U3 by RTS over USB (a chip reset through USB-Serial-JTAG, not the EN pin; labelled as such). If that is declined too, E2 is abandoned (recorded as not tested).

## Procedure (physical steps for the operator)
The session runs every SCPI command, build, flash, marker and capture; one instruction block per step.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| P0 | Nano plugged in first, then the v7 (Mac end); scope on, Ethernet adapter in | PWR LED; scope waveform view | done |
| V1–V5a | Unplug the v7 at the Mac end; lift both arms off the board; scope steps per procedure (Cal) | per procedure | per procedure |
| V5b–V7 | Springs to C, tips to N; look; plug in (V5b). Unplug; tips to A and B; look; session flashes relbus; V7 | nothing on an X pad; springs on C | positions |
| Decode, V8 | Decode fields per procedure; session flashes diag; V8 | band shows `Write:d6` | any field that differed |
| R0–R2 | One action per arm, as the arm table | PWR LED; probes untouched | what you did and when (the terminal's clock); anything seen on the board or the scope screen |
| End | Session stops loggers; unplug the v7 at the Mac end; rigid #1 out of J5 or left (user's call); probes per the user's call; unplug the Nano | no LEDs | bench state |

**Amendment (2026-10-28, before R0; user chose option A).** Roll mode forces memory depth 1 M at 20 kSa/s (50 µs/point), and `:ACQuire:MDEPth 10k` is ignored. c2 for roll arms becomes "memory depth reads 1 M (roll) and type PEAK". Roll captures use `capture.py --chunked` (not bench-verified). R0 is the trial: if the CSV min/max and VMAX/VMIN disagree by more than 30 mV (c3), or a capture takes more than 5 min, roll arms fall back to the scope's VMAX/VMIN plus the PNG (option B), and c3 is recorded as not checked. Nothing else changes.

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- Session 2026-10-28 (log `lab/log/2026-10-28_s01.yaml`; card named `2026-10-27_s04`, the date rolled over). Ports: v7 `/dev/cu.usbmodem14301` (MAC 44:1b:f6:c5:58:c4), Nano `/dev/cu.usbmodem14101`. P0: "v7 pwr on"; scope "showing results from prior card, status = STOP".
- V1: AUTO → status "T'D". After AUTO the Cal wave was not visible on CH1 ("I don't see the wave"); V3 settings by SCPI (plus CH1/CH2 offset −1.5 V, not in the procedure) → "square wave, flat tops". V2: first `:PROBe?` reads empty with three stale `-110 Command header err` in the queue; after draining, 10/10, display 1/1.
- V5a: "both tips and springs direct on the [Cal ground] terminal". V5b/V7 placement: "Ch1 tip on A, Ch2 tip on B, springs on C"; nothing near an X pad.
- Flashes: relbus (fresh build f8572de2; diag rebuild 5c156423 differs from V7R-016 End's 166f5f40, builds not byte-reproducible) 16:18:20–16:18:31; diag 166f5f40 (`lab/evidence/V7R-018/diag-166f5f40.bin`, copied from the V7R-016 session's build dir) by esptool write_flash 0x10000 16:19:14–16:19:26, hash verified. Decode menu: no field differed.
- Logger start 16:22:56: every TCA2 row `INA:. BQ:. TCA:. PCA:X(2) VCNL:X(2)` (8/8). X1 (user, look only): "The J6 black wire was out, so was the blue wire. The 10kohm resistor is in place, the black and blue wires were just out hanging". When they came out: not known. X2 (v7 unplugged): black back in the 'V' rail, blue in row 15: "both are good"; probes unmoved: "yes".
- R0 (no action; diag running): `capture.py --chunked` stopped "CH1 PREamble points 10000 != memory depth 1000000. Nothing was written." In roll after STOP, RAW preamble = 10000 points at 50 µs (last 0.5 s); NORMal = 1000 points at 50 ms (50 s window). Fallback B (amendment): `screen_minmax.py` → CH1 screen min −0.2157 / max 3.3993 V, VMAX 3.3993 / VMIN −0.21573; CH2 min −0.0995 / max 3.3927 V, VMAX 3.3927 / VMIN −0.099467 (identical: VMAX/VMIN come from the screen data; c3 not independent). PNG `R0_01.png`: ROLL, PEAK, 20 kSa/s, 1.00 Mpts, 5 s/div; traffic bursts every ~2 s on both channels.
- Session: roll arms stopped by `stopwatch.py` (serial-log reboot detection + delay → :STOP), because the 50 s window is shorter than the operator's report round trip.
- E1a attempt 1 (not captured): armed 18:38:20 (roll RUN, stopwatch reboot 15 s, 600 s timeout); stopwatch timed out 18:48:20 with no STOP sent. Operator: "I waited more than 10 seconds as I had walked away"; "Power is now on as it should, no D5"; "The scope did not seem to stop on it's own. It is still running." Serial: last pre-unplug line 20:32:10.988 (t=7617467), boot output from 20:32:19.845 (logger reconnect). Checked 20:33:36: the event was outside the 50 s roll window. Cause: the session's 600 s stopwatch timeout. One extra USB power-up on #0003, not captured. Repeat as E1a attempt 2 with a 4 h timeout.
- E1a attempt 2: armed 20:3x (roll RUN, stopwatch 4 h). Operator: "power on"; "scope is STOP". Stopwatch hit 20:36:14.000 on `t=   1395  BASE …`; STOP sent 20:36:29. Screen (option B): CH1 min −0.2107 (t −9.30 s) / max 3.4248 V (t −15.75 s); CH2 min −0.1145 (t −19.50 s) / max 3.4583 V (t −16.65 s); VMAX/VMIN identical. PNG `E1a_01.png`: ROLL, PEAK, 1.00 Mpts; both lines fall to ~0 V at ~−25 s, back up at ~−16 s with a dense burst on both, then the ~2 s traffic bursts.
- E1b: E1b-1 operator "pwr off"; armed (2 ms/div, offset 8 ms, NORM, 10 kpts, 500 kSa/s, EDGE CH1 rising 1.65 V, SINGLE; status WAIT); E1b-2 operator "power on"; status STOP. `capture.py` → `E1b_01` (png/csv/setup). `e1b_tx.py`: 151 falling 1.65 V crossings after the trigger (146 with CH2 > 1.65 V); by 1 ms bin: 0 ms 8, 10 ms 6, 11 ms 38, 12 ms 34, 13 ms 4, 16 ms 29, 17 ms 32 (window ends 18 ms). V_TX (card rule): n = 452, median 588.8 mV, min 540.4, max 626.9, sd 16.2 mV; low samples 10.886–17.994 ms. CH2 first ≥ 1.00 V at −1.454 ms, ≥ 1.65 V at 0.082 ms, ≥ 3.00 V at 5.810 ms; CH2 min after 1 ms 1.842 V. CH1 max 3.320, CH2 max 3.408 V. PNG: both lines ramp together with a plateau near 1.9 V and a step to ~3.3 V at ~5.8 ms; activity on CH1 only, ~10.9–13 ms and from ~16 ms to the end; CH2 flat high there.
- E2 (SW2, not pivoted): operator "power lit, scope is STOP, didn't touch anything else I don't think". Stopwatch hit 20:54:08.000 on `t=   1322  BASE …`; STOP 20:54:23. Screen: CH1 min −0.2056 (t −33.20 s) / max 3.4324 V (t −15.75 s); CH2 min −0.0893 (t −15.25 s) / max 3.4608 V (t −16.65 s); VMAX/VMIN identical. PNG `E2_01.png`: ~2 s traffic bursts throughout; at ~−16.5 s a yellow-only (CH1) block with lows near ~0.6–0.7 V by eye, then a dense burst on both; no gap at 0 V (the rail stayed up).
- E3 (session; operator hands off, "go"): roll RUN ~21:02:33; logger stopped; esptool write_flash 0x10000 diag-166f5f40.bin 21:02:48–21:03:00, rc 0, "Hash of data verified", "Hard resetting via RTS pin" (`E3_esptool.txt`); logger restarted; boot output 21:03:01.5; STOP 21:03:13. Diag after: TCA2 `BQ:X(2)` (c4). Screen: 811 points (roll had ~40 s, not 50 s); CH1 min −0.2157 (t −43.85 s) / max 3.4273 V (t −20.30 s); CH2 min −0.1120 (t −45.85 s) / max 3.4583 V (t −33.60 s). PNG `E3_01.png`: traffic bursts to ~−26 s; from ~−25 s to ~−14.5 s dense CH1-only (yellow) activity with lows near ~0.6–0.7 V by eye and CH2 flat high; then a short gap and the boot burst on both at ~−11 s.
- V8 re-check before R1 (no replug; diag frames): first capture at 100 µs/div (timebase set dropped after roll; `val_V8_02`); reset to 20 µs/div, no decode band (`val_V8_03`; `:BUS1:DISPlay?` 0 after roll); `:BUS1:DISPlay ON` → 1, thresholds 1.65/1.65 V; `val_V8_04`: decode band `Write:d6` (c5).
- R1 (session, no operator action): roll RUN ~21:05:5x, 55 s, STOP. Screen: CH1 min −0.2004 / max 3.3993 V; CH2 min −0.0919 / max 3.3599 V; VMAX/VMIN identical. Diag TCA2 `BQ:X(2)` at 21:07:02.
- E4: armed 21:07:23 (roll RUN, stopwatch pca 15 s). Operator: "power LED lit, D5 not lit"; "Scope status STOP"; rigid switches "1 is on, 2 is off"; "It's possible. I didn't see anything out of place but plugging in J5 took a bit of pushing and I think the light on the rigid came on, then off again, then on finally, perhaps indicating that it connected and disconnected briefly before finally connecting". Stopwatch hit 21:29:43.000 on `t=1603262  TCA1  INA:. BQ:X(2) TCA:. PCA:. VCNL:X(2)`; STOP 21:29:59. Diag after: TCA1 `BQ:X(2) PCA:. VCNL:X(2)`; TCA0 `BQ:.`; TCA2 `BQ:X(2)`. Screen: CH1 min −0.4092 (t −0.95 s) / max 3.6947 V (t −25.50 s); CH2 min −0.0995 (t −15.10 s) / max 3.5669 V (t −17.60 s); VMAX/VMIN identical. Points beyond R0 envelope ± 50 mV: CH1 > 3.449 V at −25.50 (3.695), −23.20 (3.483), −21.20 (3.483), −19.20 (3.476), −17.55 (3.550), −17.20 (3.468), −17.10 (3.471), −16.90 (3.555); CH1 < −0.25 V at −15.10 (−0.386), −13.10 (−0.399), −11.05 (−0.381), −9.05 (−0.404), −7.10 (−0.374), −4.95 (−0.379), −2.95 (−0.399), −0.95 (−0.409); CH2 > 3.449 V at −25.50 (3.527), −17.60 (3.567), −16.90 (3.567); CH2 < −0.25 V none. PNG `E4_01.png`: ~2 s bursts throughout; small upward spikes above the 3.3 V line at ~−25.5 s and ~−17 s.
- R2 (operator "go", hands off; rigid #1 on J5): roll 56 s, STOP. Screen: CH1 min −0.4296 / max 3.3892 V; CH2 min −0.1044 / max 3.3573 V. CH1 < −0.25 V at 25 of 25 ~2 s iterations (−0.356 to −0.430 V); CH1 > 3.449 V none; CH2 beyond envelope none. Diag TCA1 `BQ:X(2) PCA:. VCNL:X(2)` at 21:35:45.
### Measured values (from log; cite `lab/evidence/V7R-018/...`)
Limits: V_hi = 3.272 + 0.30 = 3.572 V (V7 CH1); V_lo = −0.30 V. R0 envelope ± 50 mV: CH1 3.449 / −0.266 V; CH2 3.443 / −0.149 V. Roll arms: screen data, 1000 × 50 ms, PEAK (`captures/<arm>_01_screen.csv`, `<arm>_01.png`).
| Arm | CH1 max | CH1 min | CH2 max | CH2 min | Crosses a limit (and the R0 envelope) |
|---|---|---|---|---|---|
| R0 | 3.399 | −0.216 | 3.393 | −0.099 | — (reference) |
| E1a power-up | 3.425 | −0.211 | 3.458 | −0.115 | none |
| E2 SW2 | 3.432 | −0.206 | 3.461 | −0.089 | none |
| E3 reflash (811 pts) | 3.427 | −0.216 | 3.458 | −0.112 | none |
| R1 | 3.399 | −0.200 | 3.360 | −0.092 | — (anchor) |
| E4 hot-plug J5 | **3.695** (−25.50 s, 1 bin) | **−0.409** (8 bins, every ~2 s from −15.1 s) | 3.567 | −0.099 | CH1 both; CH2 none |
| R2 (rigid on J5) | 3.389 | **−0.430** (25/25 iterations, −0.356 to −0.430) | 3.357 | −0.104 | CH1 low; CH2 none (recorded, not an anchor) |
Anchor R1 − R0: CH1 max 0.0, CH1 min 15.3, CH2 max 32.8, CH2 min 7.6 mV (all ≤ 50): pass.
Controls: c1 pass (R0 CH1 −0.216, CH2 −0.099 V ≤ 0.50); c2 pass as amended (roll PEAK, 1 M; E1b NORM, 10 k); c3 not independent (VMAX/VMIN = screen data to the digit; option B); c4 pass (TCA2 `BQ:X(2)` after E1a, E2, E3, E4; E4 adds TCA1 `PCA:.`); c5 pass (`captures/…val_V8_01.png` before R0, `…val_V8_04.png` before R1).
E1b (`captures/2026-10-28_V7R-018_E1b_01.csv`, `e1b_tx.py`): burst present (CH1-only activity 10.9–13 ms and 16–18 ms; 143 falls after the ramp bin, CH2 > 1.65 V at each); V_TX median **588.8 mV** (n 452, 540.4–626.9, sd 16.2); model 676 mV; normal-pad model ≈ 45 mV.
E3 (`captures/…E3_01.png`): CH1-only activity for ~10.5 s during the flash, lows near the same level by eye (not counted).

### Interpretation (session; labelled as such)
- (Interpretation, V7R-018) The ROM drives GPIO43 at power-up, at an SW2 reset and through a USB flash, and its lows sit at ~0.59 V, not ~0.05 V: the elevated low is present before any application code configures the pad, through the IO_MUX UART path. V_TX is 88 mV below the R28-only model; this card doesn't separate why (ROM pull-up state, drive setting, or the model's R28 nominal).
- (Interpretation, V7R-018) The SDA low-side crossing (−0.36 to −0.43 V) is a steady-state feature of every diag iteration while rigid #1 is on J5 (R2), not a plug-in transient; SCL's lows stay at −0.1 V in the same frames. Probe ringing on SDA's fall edges with the extra J5 load (M) is not separated from a real undershoot. Magnitude (argued): ~0.1 V past the limit, µs-scale ringing, no low-impedance source; as a damage route this is weak.
- (Interpretation, V7R-018) The single +3.695 V bin at E4 −25.5 s coincides with the operator's "light came on, then off, then on" during a firm push; CH2 reached 3.527 V in the same bin. Partial contact, hand coupling and probe pickup are not separated. ≤ 50 ms wide by resolution; peak only.
- Power-up, reset and reflash produce no crossing on either line at this resolution (5 ms/point peak).

## Conclusion
- Outcome row matched: **X1** (E4 only: CH1 crosses V_hi and V_lo, CH2 neither; E1a, E2, E3 cross nothing) and **T1** (burst present, V_TX 588.8 mV, 11.8 mV inside the 577 mV edge).
- Hypotheses excluded: H3 (no excursion anywhere), H2 for E4 (common excursion), H5 (the elevated low needs something present only after boot). H1 supported (weakly) for E4 only; the low-side part persists with the rigid connected (R2), so it is not specific to the plug-in event. H4 supported (weakly). M not excluded for the E4/R2 SDA undershoot.
- **Strength:** measured-refuted for H5 (one board, one power-up, 452 samples) and for H1/H2 at power-up, SW2 reset and USB reflash (one event each, 5 ms peak resolution, limits ±0.3 V); measured-supported (weak) for H1 at a rigid hot-plug into J5 (one event; low side steady-state with the rigid; high side one 50 ms bin); `lab/evidence/V7R-018/`
- Deviations: (1) session log `2026-10-28_s01` (date rolled over), not `2026-10-27_s04`. (2) J6 black and blue found out of the breadboard after V7 (X1), restored before V8 (X2); V7 ran with them out. (3) Roll forces 1 M points; amendment (option A) tried, `--chunked` failed; option B (screen data, VMAX/VMIN) used; c3 not independent. (4) E1a attempt 1 not captured (session stopwatch 600 s timeout); one extra uncaptured USB power-up. (5) V8 before R1 without a replug (diag frames); two recaptures (timebase dropped after roll; decode display off after roll, `:BUS1:DISPlay ON`). (6) E3's roll held ~40 s, not 50 s. (7) E2 not pivoted (SW2 pressed). (8) End: v7 and Nano left powered, rigid #1 left in J5, probes seated at S1 (user).
- Revert-on-null done: n/a (no delta); U3 on v7-clean diag 166f5f40 (reflashed at E3, 21:03:00)
- Result commit: self

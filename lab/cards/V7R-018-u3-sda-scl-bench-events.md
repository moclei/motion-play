---
test_id: V7R-018
title: "U3 SDA (TPIO43) and SCL (TPIO44) through bench events on #0003 — power-up, SW2 reset, reflash of the same image, rigid #1 hot-plugged into J5 — excursions outside the rails, and the ROM's TX low on GPIO43 at power-up"
status: pre-registered
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
### Measured values (from log; cite `lab/evidence/V7R-018/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** ...
- Revert-on-null done: ...
- Result commit: self

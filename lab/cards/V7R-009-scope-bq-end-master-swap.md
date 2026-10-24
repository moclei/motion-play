---
test_id: V7R-009
title: "Scope at the BQ end (U5.6/U5.5): 0x6B address frame in the failing state, U3 vs Nano ESP32 as master, A/B/A"
status: pre-registered
created: 2026-10-24
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: motion-play-v7-relbus   # U3 released in B; validation steps run on relbus (idle bus after BUS RELEASED). Masters run the V7R-009 scope build (source in lab/evidence/V7R-009/src/), user-approved delta ("yes to both")
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2. Second master: Arduino Nano ESP32 (S3 rev v0.1, MAC 34:85:18:7b:eb:38)
  hardware_config: "As V7R-008 end (notebook 2026-10-24 s04): v7 #0003, no battery, J4 empty. J6: sensor rigid #1 (SW1 ON = PCA 0x76, SW2 OFF) via ~400 mm cable. J5: pigtail, black in breadboard 'V' rail with the 10 kΩ, blue + yellow dangling, red → Nano GND. TPIO43 green / TPIO44 yellow pad wires → ~175 mm Dupont → Nano A4 / A5. USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Added: two SQ500 in PCBite arms at S2 (CH1 → pad D = U5.6 SDA, CH2 → pad E = U5.5 SCL), ground spring (or ≤ 10 mm wire) on pad F (C21.2)."
variable_changed: "I²C master: U3 (scope build, Wire.begin(43, 44), PIO arduino-esp32 2.0.14) vs Nano ESP32 (scope build, Wire.begin() = A4/A5 = GPIO11/12, core 2.0.18-arduino.5; U3 released by relbus) — the scope build's source is identical apart from the Wire.begin line"
structure: A/B/A
revert_on_null: yes           # end: U3 on v7-clean motion-play-v7-diag, Nano on the blank sketch, probes off the board
---

# V7R-009 — Scope at the BQ end: U3 vs Nano as master, failing state

Map regions cut: **master: module/path, master supply, bus copper** (level and edge part: does the 0x6B address byte arrive at U5's pins with a different low level, edge or byte value under U3 than under the Nano?) and **measurement** (first v7 scope session under a validated setup; re-measures SDA V_OL at the BQ end, §7 rows L-Ph21/L-Ph23). **master: timing** is captured (CSV) but not evaluated on this card: no validated tool measures SDA setup/hold against SCL yet (Planner relay); its numbers are registered below so a later evaluation is not post hoc. First card after the master-bundle review (checkpoint @ V7R-008); user chose it ("yes, go with the scope session").

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | Under U3 the 0x6B address frame arrives at U5.6/U5.5 different in level, edge or byte value from the Nano's frame (V_OL, rise time, or decoded byte), so what distinguishes U3 is visible at the BQ pins in these quantities | map: master: module/path, master supply, bus copper |
| H2 | The frames match in these quantities (same byte, V_OL within 20 mV, rise within 30 ns) and only the 9th bit differs; the distinguishing factor lies outside level/edge/byte (e.g. timing, not evaluated here) | map: master: timing, slave: BQ × master |
| M  | Measurement artefact: setup (ratio, compensation, ground, contact), trigger catching the wrong frame, or scope and log disagreeing | always listed; §4.2 |

## Confounds (declared; not separated by this card)
- The two masters differ in everything in the U3 bundle (module/path, die rev, supply, copper U3→TPIO, pin role, variant, core); this card compares their frames at the BQ pins, it does not separate those items.
- The Nano drives the bus through ~175 mm Dupont + pad wires to TPIO43/44; U3 drives from its own pads. That length is in the B arm only (and was in V7R-004/-007, which got ACK).
- U3 is reflashed between arms (upload reset, no power cycle); the scope build writes TCA 0x00 at setup. Relbus closes all TCA channels before release.
- Captures are 10 kpts at 10 µs/div (16 ns/sample), the V7R-002 reference settings, so V9 is not due. Frames run at 400 kHz (the scope build's clock, as in V7R-006/-007), not the 100 kHz of the V9 reference frame.
- **V8 adaptation (user-approved, "yes to both"):** V8 passes on the decoded address byte `Write:d6` alone; the 9th bit (`A:0` / `A:1`) is recorded, not judged, because under U3 on v7 the BQ does not ACK (the symptom).
- The Nano stays powered whenever the v7 is (V7R-008: power order). "Unplug the board" in this card means the v7's USB-C only; the Nano stays plugged in, on the blank sketch whenever the v7 is unplugged.

## Predictions and exclusions (written before the run)
Counted per arm (A1, B, A2): 3 SINGLE captures on the 0x6B write address trigger, read by `i2c_frame.py --expect D6`. Per capture: decoded address byte and 9th bit; V_OL on the three master-driven 0-bits of D6 (bits 5, 3, R/W); 30→70 % rise time of every SDA and SCL rising edge; idle high if reported. Arm values: V_OL = mean over the arm's 9 bit-means; rise = max per channel over the arm. Log controls per arm (`[scope]` lines spanning the captures): `tca` and `ina` ACK counts, `bq` ACK count.
Controls in every counted arm: validation passed (V1–V8, decode setup); scope banner/settings read back; `[scope] … i2c_clock=400000 Hz`; log `tca` = `ina` = n (all ACK); U3 heartbeat in B; A arms log `bq` ACK ≤ 5 % of n, B arm log `bq` ACK ≥ 95 % of n (the failing state holds under U3 and not under the Nano); the 9th bit in each capture agrees with the arm's log (A:1 in A arms, A:0 in B).

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| All 9 captures decode `D6`; \|V_OL(B) − V_OL(A)\| < 20 mV for A1 and A2; \|rise_max(B) − rise_max(A)\| < 30 ns per channel for A1 and A2; A1 vs A2 within 10 mV (V_OL) and 15 ns (rise); controls pass | H1 (measured-refuted for byte, V_OL and rise at U5's pins) | H2 |
| All decode `D6`; A1 vs A2 within 10 mV / 15 ns; \|V_OL(B) − V_OL(A)\| ≥ 20 mV, or \|rise_max(B) − rise_max(A)\| ≥ 30 ns on a channel, for both A1 and A2 in the same direction; controls pass | H2 | H1 (the quantity that differs) |
| Any A-arm capture decodes a byte other than `D6` (B decodes `D6`); controls pass | H2 | H1 (byte at the BQ pin differs) |
| Any pass-table limit broken in any arm (V_OL > 0.4 V, rise > 300 ns, idle high outside 3.135–3.465 V when reported) | — | recorded with the row above it; an out-of-limit quantity in A only supports H1 |
| A1 vs A2 differ by > 10 mV (V_OL) or > 15 ns (rise) or in decoded byte; or a 9th bit disagrees with its arm's log; or a log control fails (`tca`/`ina` < n, U3 reboots, no heartbeat in B); or A-arm `bq` ACK > 5 % / B-arm `bq` ACK < 95 % | — (result void) | M; stop and investigate |
| Validation fails (any of V1–V8 or decode setup) | — (setup void; no v7 number counts) | M |

**Timing (registered now, evaluated only once a validated tool exists; not counted on this card):** per master-driven address bit, t_SU;DAT (last SDA 0.3/0.7 V_DD crossing before SCL's rising 0.3 V_DD crossing) and t_HD;DAT (SCL's falling 0.3 V_DD crossing to the next SDA transition's first threshold crossing). Outcome: min t_SU;DAT or min t_HD;DAT differs between B and both A arms by ≥ 50 ns in the same direction, with A1 vs A2 within 20 ns → supports master: timing; < 50 ns for both → measured-refuted for a setup/hold difference at U5's pins on these bits.

## Setup
- Measurement log: `lab/log/2026-10-24_s01.yaml` (one arm position, S2, for the whole card). Validation must read `passed: true` before any counted capture. Validation and V8 captures use arm names `val_V3`, `val_V5ctl`, `val_V5`, `val_V7`, `val_V8`; counted captures `A1`, `B`, `A2`.
- Scope: Rigol DHO804, firmware 00.01.05, LAN 192.168.50.2 (Mac `en7` 192.168.50.1). SCPI and `capture.py` run by the session from the repo root; the Mac's Local Network permission must cover the terminal app this session runs in (checked by the first `capture.py` run, V3).
- Probes: two Sensepeek SQ500 (fixed 10:1), scope ratio 10, CH1 = SDA, CH2 = SCL, ground springs, PCBite arms, as V7R-002.
- Channel settings (V5, V7, captures): 0.5 V/div, offset −1.65 V, BW limit OFF, DC, 10 µs/div, 10 kpts, measure thresholds 30/70 %. V8: 20 µs/div. Trigger for V8 and captures: I²C, WHEN ADDR, 7-bit, address 107 (0x6B), WRITE, sweep SINGLE.
- Arm position: S2 per `lab/procedures/known-good-reference.md`: CH1 on pad D (U5.6), CH2 on pad E (U5.5), ground spring on pad F (C21.2), on the side away from the X pad (bridging warning). v7 picture `lab/procedures/img/v7-probe-points.png`.
- Readout: Nano and v7 serial logged by the session (PlatformIO's python logger, host time, `=== <arm>` markers): `lab/captures/V7R-009/2026-10-24_V7R-009_v7_01.txt`, `..._nano_01.txt`. Ports by USB serial (`ioreg`): v7 44:1B:F6:C5:58:C4, Nano 34:85:18:7B:EB:38.
- Images (built clean before pre-registration; source `lab/evidence/V7R-009/src/`):
  - U3 scope build: `v7_scope_bq_probe` U3 copy (Wire.begin(43, 44)), PIO env `u3-scope` (board/core/flags of v7-clean [env:motion-play-v7], core 2.0.14, as V7R-006); sketch sha256 e081e790…, firmware.bin 84c930db….
  - Nano scope build: Nano copy (Wire.begin()), arduino-cli `arduino:esp32:nano_nora:USBMode=hwcdc`, core 2.0.18-arduino.5; sketch sha256 0299c9c4…, bin 881bc806…; written with esptool v4.5.1 (0x0 / 0x8000 / 0xe000 boot_app0 / 0x10000).
  - U3 relbus / diag: v7-clean 90053af from the detached worktree. Nano blank: 2.0.18 hwcdc blank sketch.
- Image sequence (all flashing by the session; the Nano stays powered whenever the v7 is): validation on U3 relbus + Nano blank (idle bus) → U3 scope build for V8 and A1 (Nano blank) → B: U3 relbus, then Nano scope build (its flash resets it after `BUS RELEASED`) → A2: Nano blank, then U3 scope build → revert: U3 diag, Nano blank.
- V9 not due: last run V7R-002 (S1 and S2 pass) with the same probes, ground method and settings.

## Procedure (physical steps for the operator)
Validation steps follow `lab/procedures/dho804-setup-validation.md` V1–V8 and the decode setup, one block per numbered item; the session runs every SCPI command and capture.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| P0 | Bench: scope on, USB-C Ethernet adapter in the Mac; Nano plugged in first, then the v7 | scope waveform view; v7 PWR LED | done |
| V1–V4 | Scope only: AUTO; probes on Cal (V3 per channel: compensation look); session reads back ratio, settings, Vamp | per procedure | per procedure |
| V5a | Both tips + springs on Cal ground | per procedure | done |
| V5b | Unplug the v7; tips + spring on pad F (away from X); microscope look; plug the v7 in | nothing on an X pad; v7 PWR LED | spring/tip positions |
| V6 | (record) ground method and length | — | length |
| V7 | Unplug the v7; tips to D (CH1) and E (CH2), spring on F; microscope look; plug the v7 in | nothing on an X pad; tips on D/E | positions |
| Decode | Scope menu: Decode 1 fields per procedure | fields as listed | any field that differed |
| V8 | Nothing (session flashes U3 scope build, arms SINGLE at 20 µs/div) | decode band shows `Write:d6` | what the decode band shows |
| A1 | Nothing (session: 3 SINGLE captures at 10 µs/div) | — | — |
| B | Nothing (session: U3 relbus, Nano scope build, 3 captures) | — | — |
| A2 | Nothing (session: Nano blank, U3 scope build, 3 captures) | — | — |
| End | Session reverts U3 to diag and the Nano to blank; then unplug the v7, lift the probes off the board, unplug the Nano | no LEDs; probes clear | bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
### Measured values (from log; cite `lab/evidence/V7R-009/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** ...
- Revert-on-null done: ...
- Result commit: self

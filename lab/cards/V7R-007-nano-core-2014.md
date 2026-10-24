---
test_id: V7R-007
title: "Core swap on the Nano ESP32 master: v7_pca_master_probe on arduino-esp32 2.0.18-arduino.5 vs 2.0.14, U3 released, rigid on J6, A/B/A"
status: recorded
created: 2026-10-23
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: motion-play-v7-relbus   # U3 released in all arms (as V7R-005 B). Nano: probe sketch @ ee10efd, unchanged source, built two ways (see Setup). Deltas approved by the user for this card, 2026-10-23 ("yes")
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2. Master under test: Arduino Nano ESP32 (S3 rev v0.1, MAC 34:85:18:7b:eb:38)
  hardware_config: "As V7R-006 (notebook 2026-10-23 s03 bench state), unchanged: v7 #0003, no battery, J4 empty. J6: sensor rigid #1 (SW1 ON = PCA 0x76, SW2 OFF; flex + 2× VCNL4040) via ~400 mm double-ended cable. J5: pigtail, black in breadboard 'V' rail with the 10 kΩ, blue + yellow dangling (stub only), red → Nano GND column. TPIO43 green / TPIO44 yellow pad wires → ~175 mm F-M Dupont → Nano ESP32 A4 / A5. USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Scope probes on Cal ground."
variable_changed: "Arduino core for the Nano's probe image: arduino:esp32 2.0.18-arduino.5 (nano_nora, hwcdc; the V7R-005 B image) vs espressif arduino-esp32 2.0.14 (U3's core; arduino_nano_nora variant, hwcdc)"
structure: A/B/A
revert_on_null: yes           # end of card: Nano on the blank sketch (2.0.18 hwcdc), U3 on v7-clean motion-play-v7-diag — the V7R-006 end state
---

# V7R-007 — Core swap on the Nano: 2.0.18-arduino.5 vs 2.0.14

Map region cut: **firmware: core**, which V7R-006 left bundled with U3's hardware context (module/path, supply, copper, pin role, die rev). Same master hardware, same sketch source, same bus; only the core the sketch is built with changes. Checkpoint @ V7R-006 queue item (a), chosen by the user.

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | Core 2.0.14 (espressif) is necessary for the NACK given an S3 master on this bus: the Nano on 2.0.14 gets VCNL and BQ X(2) | map: firmware: core |
| H2 | The core is not the distinguishing factor: the Nano on 2.0.14 gets VCNL and BQ ACK, as on 2.0.18-arduino.5; what's left of the U3 bundle is hardware context (module/path, supply, copper, pin role, die rev) | map: master: module/path, master supply, pin role |
| M  | Readout or setup artefact: wrong image or port (banner), rigid not detected (PCA scan), U3 not released, Nano contact moved, 2.0.14 build mis-set for the Nano (pins, USB, PSRAM) | always listed |

## Confounds (declared; not separated by this card)
- The two cores differ as packages, not just by version: 2.0.18-arduino.5 is Arduino's fork of a later 2.0.x; 2.0.14 is espressif's release. Their bundled ESP-IDF versions were not checked. Either version or fork patches would show up as "core".
- Build settings mirror `nano_nora:USBMode=hwcdc` (pin remap on, `ARDUINO_USB_MODE=1`, CDC on boot, OPI PSRAM, 16MB app3M_fat9M_fact512k) through PlatformIO's `arduino_nano_esp32` board; differences: `ARDUINO_USB_DFU_ON_BOOT=0` and flash mode qio (PlatformIO board) vs dio/boot qio (boards.txt). Both variants map A4 → GPIO11, A5 → GPIO12 (checked in both `pins_arduino.h`).
- v6 ran the same 2.0.14 core on a T-Display S3 without the fault (F-1), so H1 would need a v7-side condition too.
- U3 relbus: boots, runs a 5-iteration burst, then releases the bus (as V7R-004/005).

## Predictions and exclusions (written before the run)
Counted (Nano log): the `VCNL:` field on the `TCA2+PCA0` and `TCA2+PCA1` rows, probe iterations 1–10 per arm → 20 per arm. Secondary: `BQ:` on the TCA2 row, 10 per arm.
Controls in every counted iteration: Nano banner `sketch=v7_pca_master_probe version=1.0 … i2c_clock=400000 Hz`; PCA detection summary `TCA ch 2: PCA9546A at 0x76`; BASE `INA:. BQ:. TCA:.`; TCA2 row `INA:. TCA:. PCA:.`; TCA2+PCA rows `PCA:.`; TCA0 row `BQ:.`. Throughout: U3 printed `BUS RELEASED` and keeps its heartbeat, no reboot.

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| A1, A2 (2.0.18): VCNL '.' ≥ 18/20 each; B (2.0.14): VCNL '.' ≥ 18/20 and TCA2 BQ '.' ≥ 9/10; controls pass | H1 (measured-refuted: core 2.0.14 not sufficient with an S3 master on this bus) | H2 |
| A1, A2: VCNL '.' ≥ 18/20 each; B: VCNL X(2) ≥ 18/20 and TCA2 BQ X(2) ≥ 9/10; controls pass | H2 (measured-refuted: the core moves the symptom) | H1 |
| A1, A2: VCNL '.' ≥ 18/20; B: VCNL and BQ separate (one '.' at threshold, the other X(2) at threshold) | — (symptoms separate) | — ; record, decide with the user |
| B: VCNL non-'.' in 3–17/20, or BQ non-'.' in 2–8/10 | — (intermittent) | — ; extend B to 30 iterations, decide with the user |
| A1 or A2: VCNL '.' < 18/20 (does not reproduce V7R-005 B); or A2 vs A1 differ by > 2/20; or any control fails; or a counted code other than 2; or U3 reboots / no heartbeat | — (result void) | M; stop and investigate |
| No `BUS RELEASED` (U3) / no Nano banner, or wrong version/clock | — (setup void) | M |

## Setup
- Readout: both ports at 115200, logged by the session with host time (scratch pyserial logger under PlatformIO's python): `lab/captures/V7R-007/2026-10-23_V7R-007_v7_01.txt`, `..._nano_01.txt`. Ports by USB serial number (`ioreg`): v7 44:1B:F6:C5:58:C4, Nano 34:85:18:7B:EB:38.
- U3 image: `motion-play-v7-relbus` from a detached worktree at `v7-clean` (90053af), uploaded once at the start; `motion-play-v7-diag` uploaded at the end.
- Nano A image (A1, A2): probe @ ee10efd (sha256 0218ffa2…0d48201, unchanged) compiled with Arduino IDE's bundled arduino-cli, `arduino:esp32:nano_nora:USBMode=hwcdc`, core 2.0.18-arduino.5 — the V7R-005 B build recipe; written with esptool v4.5.1 (bootloader 0x0, partitions 0x8000, boot_app0 0xe000, app 0x10000).
- Nano B image: same source file, PlatformIO `[env:nano-2014]`: board `arduino_nano_esp32`, framework-arduinoespressif32 2.0.14 (built `2.0.14+sha.44da992`), build_flags `-DARDUINO_USB_MODE=1 -DARDUINO_USB_DFU_ON_BOOT=0 -DARDUINO_USB_MSC_ON_BOOT=0`, build_unflags `-DARDUINO_USB_DFU_ON_BOOT=1`; uploaded with `pio run -t upload` (esptool v4.5.1). Built clean 2026-10-23 before pre-registration.
- End: Nano blank sketch (2.0.18 hwcdc, rebuilt from `void setup(){}` / `loop(){delay(1000);}`), U3 diag.
- Order: power on (Nano blank) → U3 relbus → `BUS RELEASED` → Nano A1 → B → A2 → Nano blank → U3 diag. All flashing by the session; no resets beyond those the uploads issue. No scope.

## Procedure (physical steps for the operator)
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S1 | Nothing moved since V7R-006. Plug both Mac ends (Nano first, then v7) | LED on each | LEDs |
| A1, B, A2 | Nothing (session) | — | — |
| S2 | Unplug both Mac ends | No LEDs | Bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- S1 (operator): "both on" (Nano first, then v7).
- S1 (session): ports by USB serial (`ioreg`, no port opened): Nano 34:85:18:7B:EB:38 → `/dev/cu.usbmodem14201`; v7 44:1B:F6:C5:58:C4 → `/dev/cu.usbmodem14401`. Nano logger started 23:40:15 (blank sketch: no output).
- U3 (session): `motion-play-v7-relbus` uploaded from worktree at 90053af, 23:40:15–23:40:45: `Chip is ESP32-S3 (revision v0.2)`, `MAC: 44:1b:f6:c5:58:c4`, 4× `Hash of data verified.`, hard reset, SUCCESS. v7 log from 23:40:45.335: relbus burst (100 kHz, uncounted) TCA2 `INA:. BQ:X(2) TCA:.` 5/5; `BUS RELEASED` 23:40:52.848; heartbeat `[heartbeat] t=… ms — ESP32 alive, bus released` every 5 s thereafter.
- A1 (session): Nano logger stopped; probe built with 2.0.18-arduino.5 (`nano_nora:USBMode=hwcdc`) written with esptool v4.5.1 23:41:07–23:41:11: `Chip is ESP32-S3 (revision v0.1)`, `MAC: 34:85:18:7b:eb:38`, 4× `Hash of data verified.`, hard reset. Nano log (`=== A1` marker): `[probe] sketch=v7_pca_master_probe version=1.0 board=NANO_ESP32 i2c_clock=400000 Hz`; `TCA9548A initialized`; PCA scan ch 0/1 nothing, ch 2 `PCA9546A found at 0x76`; summary `TCA ch 2: PCA9546A at 0x76`. Iterations 1–10 (t = 1516 … 19816 ms; host 23:41:12.653 … 23:41:30.967), every iteration identical: BASE, TCA0, TCA1 `INA:. BQ:. TCA:. PCA:X(2) VCNL:X(2)`; TCA2 `INA:. BQ:. TCA:. PCA:. VCNL:X(2)`; TCA2+PCA0 and TCA2+PCA1 `INA:. BQ:. TCA:. PCA:. VCNL:.`. Counted: VCNL '.' 20/20; TCA2 BQ '.' 10/10. Controls pass. v7 heartbeat continued (last seen 23:41:37.801, t=53599 ms), one `BUS RELEASED`, no reboot.
- B (session), first attempt: `pio run -e nano-2014 -t upload` at 23:42:01 failed — `*** [upload] Error 74`, `[FAILED] Took 2.43 seconds`: PlatformIO's `arduino_nano_esp32` board defaults to upload protocol `dfu`, not esptool as the card's Setup states. Nano not reset: its log continued the A1 image without a break (iteration 27, t = 54401 ms at 23:42:05.476). Amended to the declared method by adding `upload_protocol = esptool` to `[env:nano-2014]`; no other change to the build.
- B (session): retry 23:42:45–23:42:55, esptool v4.5.1: `Chip is ESP32-S3 (revision v0.1)`, `MAC: 34:85:18:7b:eb:38`, 4× `Hash of data verified.`, hard reset, SUCCESS. Nano log (`=== B 23:42:55` marker): `[probe] sketch=v7_pca_master_probe version=1.0 board=Arduino Nano ESP32 i2c_clock=400000 Hz` (board string differs from A1's `NANO_ESP32`); `TCA9548A initialized`; PCA scan ch 0/1 nothing, ch 2 `PCA9546A found at 0x76`; summary `TCA ch 2: PCA9546A at 0x76`. Iterations 1–10 (t = 1517 … 19816 ms; host 23:42:57.240 … 23:43:15.570), every iteration identical: BASE, TCA0, TCA1 `INA:. BQ:. TCA:. PCA:X(2) VCNL:X(2)`; TCA2 `INA:. BQ:. TCA:. PCA:. VCNL:X(2)`; TCA2+PCA0 and TCA2+PCA1 `INA:. BQ:. TCA:. PCA:. VCNL:.`. Counted: VCNL '.' 20/20; TCA2 BQ '.' 10/10. Controls pass. v7 heartbeat continued (23:43:02.915, t=138599 ms), no reboot.
- A2 (session): 2.0.18 probe image (same files as A1) written with esptool 23:43:40–23:43:43: `Chip is ESP32-S3 (revision v0.1)`, `MAC: 34:85:18:7b:eb:38`, 4× `Hash of data verified.`, hard reset. Nano log (`=== A2 23:43:43` marker): `[probe] sketch=v7_pca_master_probe version=1.0 board=NANO_ESP32 i2c_clock=400000 Hz`; summary `TCA ch 2: PCA9546A at 0x76`. Iterations 1–10 (t = 1516 … 19815 ms; host 23:43:45.169 … 23:44:03.475), every iteration identical to A1 and B: BASE, TCA0, TCA1 `INA:. BQ:. TCA:. PCA:X(2) VCNL:X(2)`; TCA2 `INA:. BQ:. TCA:. PCA:. VCNL:X(2)`; TCA2+PCA0/1 `INA:. BQ:. TCA:. PCA:. VCNL:.`. Counted: VCNL '.' 20/20; TCA2 BQ '.' 10/10. Controls pass. v7 heartbeat continued (23:44:02.968, t=198599 ms), one `BUS RELEASED` in the v7 log, no reboot.
- Revert (session): loggers stopped. Nano blank sketch (2.0.18 hwcdc) written 23:44:14–23:44:17, 4 hashes verified, hard reset. U3 `motion-play-v7-diag` from worktree at 90053af (rebuilt: worktree recreated) uploaded 23:44:17–23:46:55, `Chip is ESP32-S3 (revision v0.2)`, `MAC: 44:1b:f6:c5:58:c4`, 4 hashes verified, hard reset, SUCCESS. Not logged after the revert.
- S2 (operator): "both off".
### Measured values (from log; cite `lab/evidence/V7R-007/...`)
Sources: `lab/evidence/V7R-007/2026-10-23_V7R-007_nano_01.txt` (Nano: A1, failed B upload note, B, A2; arm markers `=== …`), `lab/evidence/V7R-007/2026-10-23_V7R-007_v7_01.txt` (U3 relbus: burst, `BUS RELEASED`, heartbeat through all arms).

| Arm | Nano probe image (core) | Counted | VCNL '.' (TCA2+PCA0/1) | VCNL X(2) | TCA2 BQ '.' | TCA2 BQ X(2) | Controls | Other codes |
|---|---|---|---|---|---|---|---|---|
| A1 | 2.0.18-arduino.5, nano_nora hwcdc | it 1–10 | 20/20 | 0/20 | 10/10 | 0/10 | pass; U3 heartbeat | none |
| B  | espressif 2.0.14, arduino_nano_nora hwcdc | it 1–10 | 20/20 | 0/20 | 10/10 | 0/10 | pass; U3 heartbeat | none |
| A2 | 2.0.18-arduino.5, nano_nora hwcdc | it 1–10 | 20/20 | 0/20 | 10/10 | 0/10 | pass; U3 heartbeat | none |

Uncounted: U3 relbus burst before A1 (100 kHz) TCA2 BQ X(2) 5/5; A1 iterations 11–27 same per-row results.
### Interpretation (session; labelled as such)
Interpretation: with the Nano ESP32 as master on this bus (U3 released, rigid #1 on J6), the probe sketch gets VCNL and BQ ACK whether built on Arduino's 2.0.18-arduino.5 or on espressif's 2.0.14, the core U3 runs. Core 2.0.14 is not sufficient for the NACK with an S3 master here, so it drops out of the U3 bundle left by V7R-006. Left in the bundle, unseparated: U3's module/path (WROOM-1 vs NORA-W106), die rev (v0.2 vs v0.1), master supply (v7 +3.3 V rail vs the Nano's own), U3→TPIO copper, pin role (U3 drives from GPIO43/44, the UART0 pins; the Nano from GPIO11/12), and the board variant/flags (devkitc build on U3 vs Nano variant).

## Conclusion
- Outcome row matched: row 1 — A1 VCNL '.' 20/20 / BQ '.' 10/10; B VCNL '.' 20/20 / BQ '.' 10/10; A2 VCNL '.' 20/20 / BQ '.' 10/10; controls pass in every arm; no counted code other than 2 (`lab/evidence/V7R-007/2026-10-23_V7R-007_nano_01.txt`, `lab/evidence/V7R-007/2026-10-23_V7R-007_v7_01.txt`).
- Hypotheses excluded: H1 (core 2.0.14 necessary for the NACK given an S3 master on this bus) — measured-refuted. H2 measured-supported (core is not the distinguishing factor; remaining U3 bundle listed above). M not supported (banners per arm differ as the builds should; PCA detected; controls pass; U3 released throughout).
- **Strength:** measured-refuted (H1; one board, one rigid, one Nano, A/B/A, 20/20 and 10/10 per arm; fork vs version not separated, but neither moves the symptom); measured-supported (H2); `lab/evidence/V7R-007/`
- Deviations: first B upload used PlatformIO's default `dfu` protocol and failed (Error 74) before touching the Nano; retried with `upload_protocol = esptool`, the method the card declared. No other deviation; no session resets beyond uploads.
- Revert-on-null done: yes — Nano on the blank sketch (23:44:14–23:44:17), U3 on v7-clean motion-play-v7-diag (23:44:17–23:46:55)
- Result commit: self

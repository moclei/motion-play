---
test_id: V7R-006
title: "Image swap on U3: v7-clean diag loop vs v7_pca_master_probe (+ Wire.begin(43, 44)), same core, rigid on J6, A/B/A"
status: pre-registered
created: 2026-10-23
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: motion-play-v7-diag   # A arms. B arm: scratch PlatformIO build of v7_pca_master_probe @ ee10efd + one-line pin delta, same board/core/flags as motion-play-v7 (see Setup). Delta approved by the user for this card, 2026-10-23 ("yes, of course")
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2
  hardware_config: "As at the end of V7R-005 (notebook 2026-10-23 s02 cont.), unchanged: v7 #0003, no battery, J4 empty. J6: sensor rigid #1 (SW1 ON = PCA 0x76, SW2 OFF; flex + 2× VCNL4040) via ~400 mm double-ended cable. J5: pigtail, black in breadboard 'V' rail with the 10 kΩ, blue + yellow dangling (stub only), red → Nano GND column. TPIO43 green / TPIO44 yellow pad wires → ~175 mm F-M Dupont → Nano ESP32 A4 / A5; Nano on the blank sketch in all arms (powered, passive). USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Scope probes on Cal ground."
variable_changed: "U3 firmware image: v7-clean motion-play-v7-diag (runBusDiagnosticLoop) vs v7_pca_master_probe 1.0 with Wire.begin(43, 44); core 2.0.14, board config, master hardware and bus unchanged"
structure: A/B/A
revert_on_null: yes           # A2 re-flashes v7-clean motion-play-v7-diag (90053af) and leaves U3 there whatever the outcome; Nano stays on the blank sketch
---

# V7R-006 — Image swap on U3: v7-clean diag loop vs the PCA probe sketch

Map region cut: **firmware: env** (v7 image/boot context) against the **U3 hardware** bundle (master: module/path, master supply, pin role, U3→TPIO copper, die rev). STATE §8 option (b). V7R-004/005 changed master hardware *and* image *and* core at once; this card changes the image only, on U3, with the core held at 2.0.14.

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | Something in the v7-clean image (boot order, BQ/INA config, other GPIO/peripheral init, the diag loop's code path) is necessary for the NACK on U3: with the probe image, U3 gets VCNL and BQ ACK | map: firmware: env; firmware: drift (rest, argued) |
| H2 | The NACK needs U3's hardware context (module/path, supply, pin role, copper, die rev) and/or core 2.0.14, not the v7 image: with the probe image, U3 still gets VCNL and BQ X(2) | map: master: module/path, master supply, pin role; firmware: core |
| M  | Readout or setup artefact: wrong port or image (banner), rigid not detected (PCA scan), Nano not passive, contact moved, U3 not booted into the image | always listed |

## Confounds (declared; not separated by this card)
- Core held at 2.0.14 on U3 in all arms, so H2 bundles U3 hardware with core 2.0.14 (Nano ran 2.0.18-arduino.5). Option (a) in STATE §8 cuts the core.
- B image differs from A in everything the v7 image does besides the bus loop: `configureBQ24195()`, INA219 init, PIN_SENSOR_INT_1–3 INPUT_PULLUP, CAL buttons, startup I²C scan, task layout. H1 does not name which. The probe sketch emulates the diag loop's bus transactions, delays and TCA cache (per its header; not verified on a scope).
- BQ register state in B: B is entered by a flash + reset with no power cycle, so whatever A1's `configureBQ24195()` wrote (watchdog etc.) persists into B. Not read back.
- Nano ESP32 on the bus in all arms, blank sketch, powered (same passive load as V7R-005 A arms).

## Predictions and exclusions (written before the run)
Counted: the `VCNL:` field on the `TCA2+PCA0` and `TCA2+PCA1` rows, 10 complete iterations per arm → 20 fields per arm. A arms: diag-loop iterations 1–10 after the banner (A1 on boot 1 after power-on, no session reset). B: probe iterations 1–10 after the PCA detection summary. Secondary (counted, not deciding alone): `BQ:` on the TCA2 row, 10 per arm.
Controls in every counted iteration: PCA detection summary shows `TCA ch 2: PCA9546A at 0x76` (each boot); BASE `INA:. BQ:. TCA:.`; TCA2 row `INA:. TCA:. PCA:.`; TCA2+PCA rows `PCA:.`; TCA0 row `BQ:.`. B banner shows `sketch=v7_pca_master_probe version=1.0` and `i2c_clock=400000 Hz`.

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| A1, A2: VCNL X(2) ≥ 18/20 each; B: VCNL '.' ≥ 18/20 and TCA2 BQ '.' ≥ 9/10; controls pass | H2 (measured-refuted: U3 hardware + core 2.0.14 not sufficient) | H1 |
| A1, A2: VCNL X(2) ≥ 18/20 each; B: VCNL X(2) ≥ 18/20 and TCA2 BQ X(2) ≥ 9/10; controls pass | H1 (measured-refuted: v7 image not necessary) | H2 |
| A1, A2: VCNL X(2) ≥ 18/20; B: VCNL and BQ separate (one '.' ≥ 18/20 or ≥ 9/10, the other X(2) at the same thresholds) | — (symptoms separate under this image; contradicts V7R-005 pattern) | — ; record, decide with the user |
| B: VCNL non-'.' in 3–17/20, or BQ non-'.' in 2–8/10 | — (intermittent) | — ; extend B to 30 iterations, decide with the user |
| A1 or A2: VCNL X(2) < 18/20; or A2 vs A1 differ by > 2/20; or any control fails; or a counted code other than 2; or U3 reboots mid-arm | — (result void) | M; stop and investigate |
| No diag-loop banner (A) / no probe banner or wrong version/clock (B) | — (setup void) | M |

## Setup
- Readout: v7 serial (USB HW CDC, J7) at 115200, logged by the session with host time (scratch pyserial logger): `lab/captures/V7R-006/2026-10-23_V7R-006_v7_01.txt`. Nano port opened only to confirm it is silent.
- B image: scratch PlatformIO project; `src/v7_pca_master_probe.ino` = `git show ee10efd:tools/arduino-sketches/v7_pca_master_probe/v7_pca_master_probe.ino` with line 393 `Wire.begin();` → `Wire.begin(43, 44);` (only diff; sha256 df3acaea…5c41f78). `platformio.ini` `[env:u3-probe]`: platform espressif32, board esp32-s3-devkitc-1, framework-arduinoespressif32 2.0.14 (built: `2.0.14+sha.44da992`), build_flags `-DBOARD_HAS_PSRAM -DARDUINO_USB_MODE=1 -DARDUINO_USB_CDC_ON_BOOT=1 -DCORE_DEBUG_LEVEL=3`, build_unflags `-DARDUINO_USB_CDC_ON_BOOT=0`, build_type debug, 16MB / default_16MB.csv / qio / 240 MHz / 80 MHz flash / qio_opi — copied from v7-clean `[env:motion-play-v7]`, minus lib_deps, `-Ifirmware/include`, `SERIAL_STUDIO_DEFAULT`, `STARTUP_I2C_SCAN` (not used by the sketch). Built clean 2026-10-23 before pre-registration.
- A2 image: `motion-play-v7-diag` from a detached worktree at `v7-clean` (90053af), as V7R-005.
- All flashing by the session over J7 (`pio run -t upload`). Order: A1 (already flashed; boot 1 after power-on) → flash B image → B → flash v7-clean diag → A2. No session resets other than the resets the uploads issue. No scope.

## Procedure (physical steps for the operator)
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S1 | Nothing moved. Look over the bench | Bench matches hardware_config (rigid on J6, pigtail on J5 stub-only, pad wires to Nano A4/A5, Nano GND via red) | Anything different |
| S2 | Plug both Mac ends (Nano first, then v7, so the Nano is powered before U3 boots) | LED on each | LEDs |
| A1, B, A2 | Nothing (session) | — | — |
| S3 | Unplug both Mac ends | — | Bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
### Measured values (from log; cite `lab/evidence/V7R-006/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** ...
- Revert-on-null done: ...
- Result commit: self

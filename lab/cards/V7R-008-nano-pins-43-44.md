---
test_id: V7R-008
title: "Pin role on the Nano ESP32 master: I²C on GPIO11/12 (A4/A5) vs GPIO43/44 (D1/D0, UART0 pins), U3 released, rigid on J6, A/B/A"
status: run
created: 2026-10-24
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: motion-play-v7-relbus   # U3 released in all arms (as V7R-007). Nano: probe @ ee10efd built twice (A: unchanged; B: Wire.begin(D1, D0)), both with core debug level 3. Deltas approved by the user for this card ("sure")
  board_id: v7-B3             # v7 #0003; U3 die rev v0.2. Master under test: Arduino Nano ESP32 (S3 rev v0.1, MAC 34:85:18:7b:eb:38)
  hardware_config: "As V7R-007 (notebook 2026-10-23 s03 cont. bench state): v7 #0003, no battery, J4 empty. J6: sensor rigid #1 (SW1 ON = PCA 0x76, SW2 OFF) via ~400 mm cable. J5: pigtail, black in breadboard 'V' rail with the 10 kΩ, blue + yellow dangling, red → Nano GND column. TPIO43 green / TPIO44 yellow pad wires → ~175 mm F-M Dupont → Nano: A arms A4 (green) / A5 (yellow); B arm D1/TX (green) / D0/RX (yellow). USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Scope probes on Cal ground."
variable_changed: "Nano I²C pins: GPIO11/12 (A4/A5; Wire.begin() default) vs GPIO43/44 (D1/D0; Wire.begin(D1, D0)) — image pin argument and jumper position move together"
structure: A/B/A
revert_on_null: yes           # end: jumpers on A4/A5, Nano on the blank sketch, U3 on v7-clean motion-play-v7-diag — the V7R-007 end state
---

# V7R-008 — Pin role on the Nano: GPIO11/12 vs GPIO43/44

Map region cut: **master: pin role** — the U3 bundle item "U3 drives SDA/SCL from GPIO43/44, the UART0 TX/RX pins". After V7R-006 (image) and V7R-007 (core), the bundle is module/path, die rev, supply, U3→TPIO copper, pin role, board variant/flags. This card moves the Nano onto the same GPIO numbers as U3; nothing else about the master changes. Fourth card on the master bundle: its region review falls due after this card is recorded (decisioning §4.2).

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | Driving I²C from GPIO43/44 (UART0 pins: IO_MUX/matrix state, ROM boot output on GPIO43, pad characteristics) is necessary for the NACK with an S3 master: the Nano on GPIO43/44 gets VCNL and BQ X(2) | map: master: pin role |
| H2 | Pin role is not the distinguishing factor: the Nano on GPIO43/44 gets VCNL and BQ ACK; what's left of the U3 bundle is module/path, die rev, supply, U3→TPIO copper, board variant | map: master: module/path, master supply |
| M  | Readout or setup artefact: jumper on the wrong Nano pin or poor contact, wrong image (banner, i2cInit pin line), U3 not released, rigid not detected | always listed |

## Confounds (declared; not separated by this card)
- The jumper move is part of the variable: different Nano header pins, same Dupont jumpers. A contact or wrong-pin error shows as M (controls fail: INA/TCA/PCA NACK or no PCA found).
- Both Nano images built with `build.code_debug=3` (V7R-007's were 0) so the `i2cInit(): … sda=… scl=…` line reads back the pins. A and B differ only by the `Wire.begin` line.
- The Nano ESP32 board may route its D0/D1 header pins through components (series resistors, other loads) that its A4/A5 pins don't have — not checked against the Nano schematic.
- B arm boots the Nano with GPIO43 connected to the v7 SDA, so the S3 ROM's boot output on UART0 TX (if enabled on this Nano) reaches SDA before the sketch starts — part of the pin role, as on U3.
- Between arms the Nano is reflashed with jumpers still on the previous pins (that run is uncounted), then unplugged, rewired and replugged; the counted run is the boot after replugging. U3 stays powered and released throughout.

## Predictions and exclusions (written before the run)
Counted (Nano log, the boot after replug for B and A2; A1 the boot after flashing): `VCNL:` on `TCA2+PCA0` and `TCA2+PCA1`, probe iterations 1–10 → 20 per arm. Secondary: `BQ:` on the TCA2 row, 10 per arm.
Controls in every counted arm: banner `sketch=v7_pca_master_probe version=1.0 … i2c_clock=400000 Hz`; `i2cInit()` line shows sda=11 scl=12 (A) or sda=43 scl=44 (B); PCA detection summary `TCA ch 2: PCA9546A at 0x76`; BASE `INA:. BQ:. TCA:.`; TCA2 row `INA:. TCA:. PCA:.`; TCA2+PCA rows `PCA:.`; TCA0 row `BQ:.`. U3: one `BUS RELEASED`, heartbeat throughout, no reboot.

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| A1, A2: VCNL '.' ≥ 18/20 each; B: VCNL '.' ≥ 18/20 and TCA2 BQ '.' ≥ 9/10; controls pass | H1 (measured-refuted: GPIO43/44 not sufficient on an S3 master with its own module/supply) | H2 |
| A1, A2: VCNL '.' ≥ 18/20 each; B: VCNL X(2) ≥ 18/20 and TCA2 BQ X(2) ≥ 9/10; controls pass | H2 (measured-refuted: pin role moves the symptom) | H1 |
| A1, A2: VCNL '.' ≥ 18/20; B: VCNL and BQ separate (one '.' at threshold, the other X(2) at threshold) | — (symptoms separate) | — ; record, decide with the user |
| B: VCNL non-'.' in 3–17/20, or BQ non-'.' in 2–8/10 | — (intermittent) | — ; extend B to 30 iterations, decide with the user |
| A1 or A2: VCNL '.' < 18/20; or A2 vs A1 differ by > 2/20; or any control fails; or a counted code other than 2; or U3 reboots / no heartbeat | — (result void) | M; stop and investigate |
| No `BUS RELEASED` / no Nano banner / wrong i2cInit pins | — (setup void) | M |

## Setup
- Readout: both ports at 115200, session logger (PlatformIO's python) with host time and `=== <arm>` markers: `lab/captures/V7R-008/2026-10-24_V7R-008_v7_01.txt`, `..._nano_01.txt`. Ports by USB serial number (`ioreg`): v7 44:1B:F6:C5:58:C4, Nano 34:85:18:7B:EB:38.
- U3: `motion-play-v7-relbus` from a detached worktree at `v7-clean` (90053af) at the start; `motion-play-v7-diag` at the end.
- Nano A image: probe @ ee10efd unchanged (sha256 0218ffa2…0d48201); Nano B image: same with line 393 `Wire.begin();` → `Wire.begin(D1, D0);` (sha256 01d9ea5a…0ef64542; with pin remap, D1/D0 → GPIO43/44 via `digitalPinToGPIONumber` in `i2cInit`, io_pin_remap.h). Both compiled with Arduino IDE's arduino-cli, `arduino:esp32:nano_nora:USBMode=hwcdc`, `--build-property build.code_debug=3`, core 2.0.18-arduino.5; written with esptool v4.5.1 (0x0 / 0x8000 / 0xe000 boot_app0 / 0x10000). Built clean before pre-registration.
- End: Nano blank sketch (2.0.18 hwcdc), U3 diag. All flashing by the session; no resets beyond uploads and the operator's Nano power cycles in the procedure. No scope.

## Procedure (physical steps for the operator)
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S1 | Plug both Mac ends (Nano first, then v7) | LED on each | LEDs |
| A1 | Nothing (session: U3 relbus, Nano A image, count) | — | — |
| S2 | (session has flashed the B image) Unplug the Nano's Mac end; move green jumper A4 → D1/TX, yellow A5 → D0/RX; plug the Nano's Mac end | Jumpers on the pins labelled D1/TX and D0/RX; nothing else moved; Nano LED on | Pin labels as printed on the Nano |
| B | Nothing (session counts) | — | — |
| S3 | (session has flashed the A image) Unplug the Nano's Mac end; move green back to A4, yellow back to A5; plug the Nano's Mac end | Jumpers on A4/A5; Nano LED on | Done |
| A2 | Nothing (session counts, then reverts both boards) | — | — |
| S4 | Unplug both Mac ends | No LEDs | Bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- S1 (operator): "both on" (Nano first, then v7). Ports by USB serial (`ioreg`): Nano → `/dev/cu.usbmodem14201`, v7 → `/dev/cu.usbmodem14401`.
- U3 (session): `motion-play-v7-relbus` uploaded 00:26:12–00:26:42 (`Chip is ESP32-S3 (revision v0.2)`, `MAC: 44:1b:f6:c5:58:c4`, 4 hashes verified, SUCCESS). Relbus burst (uncounted) TCA2 `INA:. BQ:X(2) TCA:.` 5/5; `BUS RELEASED` 00:26:50.675.
- A1 (session): Nano A image written 00:26:52–00:26:55 (`Chip is ESP32-S3 (revision v0.1)`, `MAC: 34:85:18:7b:eb:38`, 4 hashes verified, hard reset). Log (`=== A1 00:26:55`): `[probe] sketch=v7_pca_master_probe version=1.0 board=NANO_ESP32 i2c_clock=400000 Hz`; `TCA9548A initialized`; summary `TCA ch 2: PCA9546A at 0x76`. **No `i2cInit()` line**: the string `Initialising I2C Master` is absent from the A image ELF — `--build-property build.code_debug=3` did not take effect (same for the B image, same flags). Iterations 1–10 (t = 1517 … 19816 ms; host 00:26:57.077 … 00:27:15.418), every iteration identical: BASE, TCA0, TCA1 `INA:. BQ:. TCA:. PCA:X(2) VCNL:X(2)`; TCA2 `INA:. BQ:. TCA:. PCA:. VCNL:X(2)`; TCA2+PCA0/1 `INA:. BQ:. TCA:. PCA:. VCNL:.`. Counted: VCNL '.' 20/20; TCA2 BQ '.' 10/10. Controls pass except the i2cInit pin readback (absent). U3 heartbeat 00:27:15.690 (t=33574 ms).
- Stop and decision (session → user): pin-readback control unavailable in both images. User: "carry on" — continue without it; the INA/TCA/PCA ACK controls stand in (a Nano on unconnected pins gets no ACK from any device). Recorded as a deviation.
### Measured values (from log; cite `lab/evidence/V7R-008/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** ...
- Revert-on-null done: ...
- Result commit: self

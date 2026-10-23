---
test_id: V7R-004
title: "Same-family master swap: Arduino Nano ESP32 as master on the v7 bus (U3 released), L-Ph12 minimal repro, A/B/A"
status: pre-registered
created: 2026-10-23
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "90053af"
  firmware_env: motion-play-v7-relbus   # same commit as V7R-003; env differs (bus-release build, -DDIAG_RELEASE_I2C on motion-play-v7). Declared delta, user-approved 2026-10-23
  board_id: v7-B3             # v7 #0003 (panel marking); link to legacy B3 not confirmed (V7R-003)
  hardware_config: "v7 #0003, no battery, nothing on J4/J5. J6: pigtail (black = pin 1 +3.3 V, red = pin 2 GND, blue = pin 3 SDA, yellow = pin 4 SCL); breadboard: 10 kΩ between the rail labelled 'voltage' (black) and the rail labelled 'ground' (blue goes there; that rail is the SDA side of the 10 kΩ, not GND); pigtail yellow dangling. Wires soldered to v7 pads (fitted before this card): green ~68 mm 26 AWG on TPIO43 (pad A, SDA), yellow ~68 mm on TPIO44 (pad B, SCL). Arduino Nano ESP32 in the breadboard (headers push-fit): green → Nano A4 column, yellow → Nano A5 column, pigtail red → Nano GND column. USB-C Mac ↔ v7 J7; USB-C Mac ↔ Nano. Scope probes on Cal ground."
variable_changed: "I²C master: U3 (ESP32-S3-WROOM-1 on v7, relbus burst) vs Arduino Nano ESP32 (probe sketch) at TPIO43/44, U3 released"
structure: A/B/A
revert_on_null: yes           # end of card: v7 re-flashed to v7-clean motion-play-v7-diag (the V7R-003 bench state); Nano left on the blank sketch
---

# V7R-004 — Same-family master swap: Nano ESP32 as master on the v7 bus

Map region cut: **master: module/path** and **master supply** (U3's WROOM module, its pad path and the shared +3.3 V rail at the master) against **master: identity → die / Arduino-core driver class**, and against the bus side (**bus copper**, **mux**) with an S3 master. Decisioning §2.7 card 4.

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | The NACK needs U3's context on v7 (WROOM-1 module, its pad path, its supply from the board's +3.3 V, or its firmware env/core 2.0.14); an ESP32-S3 master with its own module and supply, driving TPIO43/44, gets BQ ACK in the failing config | map: master: module/path, master supply; F-5 (SAMD21 ACK) |
| H2 | Any ESP32-S3 master on arduino-esp32 2.0.x (die, legacy I²C driver class), or the bus side of v7 with an S3 master, gives the NACK; the Nano ESP32 at TPIO43/44 also gets BQ X(2) | map: master: identity, bus copper, mux; F-1 (v6 passes with an S3) |
| M  | Readout or setup artefact: wrong board or port; U3 not released (contention); Nano wired to the wrong pad or column, or poor contact; J6 not on TCA2; 10 kΩ not on SDA | always listed |

## Confounds (declared; not separated by this card)
- Nano core is arduino:esp32 **2.0.18-arduino.5** (IDF 4.4.x); U3 runs arduino-esp32 **2.0.14**. Different module (Nano ESP32 = u-blox NORA-W106, ESP32-S3), its own 3.3 V regulator from its USB.
- Sketch: `tools/arduino-sketches/v7_bq_master_probe/v7_bq_master_probe.ino` @ 6400df9, unchanged, built for `arduino:esp32:nano_nora`. Each Nano row also probes 0x60 (VCNL, absent: expected NACK, not counted) before BQ; the U3 relbus burst probes INA, BQ, TCA only. Delays the same (1 ms close, 2 ms open).
- Both at 100 kHz: neither sets a clock before the probes; both cores default to 100 kHz (`esp32-hal-i2c.c:71`). Both drivers enable internal pull-ups on their pins.
- Injection point: TPIO43/44 (5.9 mm from U3) via ~68 mm wire + breadboard; U3's pads stay on the net as inputs (`pinMode(INPUT)`) during B. During A arms the Nano's A4/A5 are on the net, running an empty sketch (pins at reset default).

## Predictions and exclusions (written before the run)
Counted field: TCA2-row `BQ:` in 10 complete iterations per arm. A1 and A2: the 5-iteration relbus burst from each of two consecutive v7 boots (2 × 5). B: Nano iterations 1–10 after the probe sketch starts. Controls in every counted iteration: BASE row `BQ:.` `INA:.` `TCA:.`; TCA0/TCA1 rows `BQ:.`; TCA2 row `INA:.` `TCA:.`; no `WARN: TCA select` line (B); during B, the v7 log shows `[heartbeat]` lines and no reboot.

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| A1 and A2: `BQ:X(2)` in ≥ 9/10 each; B: `BQ:.` in ≥ 9/10; controls pass | H2 (measured-refuted: an S3 master on core 2.0.x on this bus does not by itself give the NACK) | H1 |
| A1 and A2: `BQ:X(2)` ≥ 9/10 each; B: `BQ:X(2)` ≥ 9/10; controls pass | H1 (measured-refuted: U3's module/supply context is not needed) | H2 |
| A1 and A2: ≥ 9/10 X(2); B: non-'.' in 2–8/10 | — (intermittent under the Nano) | — ; extend B to 30 iterations, decide with the user |
| A1 or A2: `BQ:X(2)` < 9/10; or A2 differs from A1 by > 1/10; or any control fails; or a counted code other than 2; or no heartbeat / a v7 reboot during B | — (result void) | M; stop and investigate |
| No `BUS RELEASED` banner on v7, or no Nano output after flashing | — (setup void; no arm counts) | M |

## Setup
- Readout: two serial ports at 115200, logged by the session with host time on each line (scratch pyserial logger, reconnects on re-enumeration): v7 → `lab/captures/V7R-004/2026-10-23_V7R-004_v7_01.txt`, Nano → `lab/captures/V7R-004/2026-10-23_V7R-004_nano_01.txt`.
- v7 flash: `pio run -e motion-play-v7-relbus -t upload` from a detached worktree at `v7-clean` (90053af), by the session. v7 resets between bursts by the session (esptool hard reset over USB); no physical step.
- Nano flashes by the session. *Amended at S1, before any arm:* the Nano enumerates as Espressif USB-JTAG/serial (303A:1001), not Arduino DFU, so both sketches are built with `arduino:esp32:nano_nora:USBMode=hwcdc` (Hardware CDC, as v7's `ARDUINO_USB_MODE=1`) and written with esptool v4.5.1 (bootloader 0x0, partitions 0x8000, boot_app0 0xe000, app 0x10000). Sketches: blank sketch (`void setup(){}` / `loop(){delay(1000);}`, scratch, built with the same core) for A arms; probe sketch for B.
- Arms run with no operator action; the 10 kΩ SDA → +3.3 V path stays connected throughout.
- No scope.

## Procedure (physical steps for the operator)
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S1 | Both boards unpowered. Nano USB-C into the Mac; nothing else to the Nano. Session flashes the blank sketch, then asks for the Nano Mac end to be unplugged | Session confirms port + flash | Nano LEDs |
| S2 | Both unpowered. Green (pad A) → Nano A4 column; yellow (pad B) → Nano A5 column; pigtail red → Nano GND column; pigtail blue → the 'ground'-labelled rail (10 kΩ SDA side) | No Nano pin in a rail; pigtail yellow touches nothing | Which holes, what is next to what |
| S3 | Plug the Nano Mac end; plug the v7 Mac end. Session flashes relbus to v7 | Session confirms both ports, flash, `BUS RELEASED` | v7 LEDs |
| A1 | Nothing; session resets v7 once more (2 bursts logged) | — | — |
| B  | Nothing; session flashes the probe sketch to the Nano, logs ≥ 10 iterations | — | — |
| A2 | Nothing; session flashes the blank sketch to the Nano, resets v7 twice | — | — |
| S4 | Session re-flashes v7-clean motion-play-v7-diag to v7 (revert). Unplug both Mac ends | — | Bench state read-back |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- S1 (2026-10-23), operator: "One LED is on I think, it's green-ish (or  maybe yellow)"
- S1 (session): Nano on `/dev/cu.usbmodem14201`, USB "USB JTAG_serial debug unit" 303A:1001; esptool: ESP32-S3 (revision v0.1), MAC 34:85:18:7b:eb:38. Old firmware printed nothing in 4 s at 115200 (not identified). Blank sketch (hwcdc build) written, all four hashes verified, hard reset; port back, silent.
- S2 fixture amendment (before any arm), operator: "Option 1, I tinned the ends and use dupont jumpers". Pad wires too short to reach the breadboard from the PCBite; green and yellow ends tinned, each pushed into the female end of a female-to-male Dupont jumper, male end in the Nano column. Extension in place for all arms (A1, B, A2). Jumper length: asked at S3.
- S2, operator: "1. The green wire is next to A4 on the nano, connected. The yellow wire is next to A5, connected. The pigtail's black wire is in the "V" rail of the breadboard, same side as one leg of the 10kohm resistor, connected. The pigtail's red wire is next to the GND pin of the nano, connected. The pigtail's blue wire is connected to the GND rail of the breadboard, beside the 10kohm resistor's other leg, connected. The pigtail's yellow wire is hanging unconnected 2. I think I listed everything above 3. Yes, it has 2. I connected our pigtail wire next to the GND that is between the nano's pins "D2" and "RST". The other one is between pins "VIN" and "B1""
### Measured values (from log; cite `lab/evidence/V7R-004/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** ...
- Revert-on-null done: ...
- Result commit: self

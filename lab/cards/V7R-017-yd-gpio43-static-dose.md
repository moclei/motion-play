---
test_id: V7R-017
title: "GPIO43 vs GPIO4 static low on a YD-ESP32-23 dev board (ESP32-S3-WROOM-1-N16R8, never in a v7): DMM dose with none / 10 kΩ / 4.7 kΩ to 3.3 V"
status: pre-registered
created: 2026-10-27
prereg_commit: self
baseline:
  name: other                 # YD-ESP32-23 "2022-V1.3" dev board (VCC-GND Studio design, DevKitC-1 clone), ESP32-S3-WROOM-1 N16R8 in a metal can; history unknown, never fitted to a v7
  firmware_commit: "self"     # yd-static built from lab/evidence/V7R-017/src/yd/ at the prereg commit (firmware.bin sha256 56a0ef90…); env copied verbatim from V7R-014 u3-static (core 2.0.14, devkitc-1, qio_opi, 16 MB)
  firmware_env: "yd-static"   # user-approved for this card ("1. approve"); parts to hand ("2. I have the parts"); card unchanged ("3. no")
  board_id: yd-1              # the user's YD-ESP32-23; chip revision read by esptool at the flash and recorded
  hardware_config: "Dev board alone on the bench, powered and talking only through its native USB port (GPIO19/20, labelled USB/OTG); the CH343P 'COM' port unplugged. Nothing on any header pin except the arm's resistor between the 3V3 header pin and the pin under test. v7, Nano, scope probes and the V7R-016 breadboard untouched."
variable_changed: "Which ESP32-S3-WROOM-1 module's GPIO43 is held low: U3 on v7 (V7R-014/-016, the reference values) vs a module on a dev board that was never in a v7. Within the card, the external pull-up (none / 10 kΩ / 4.7 kΩ to 3.3 V) is the dose that turns each pin's low into a resistance, and GPIO4 is the within-module control."
structure: "Per pin, A/B/C/A (none / 10 kΩ / 4.7 kΩ / none) in one boot: GPIO43 first, then GPIO4. The comparison with U3 is across cards and instruments (DMM here, scope there): decided against fixed numeric thresholds, not against V7R-016's values directly"
revert_on_null: "n/a for the v7 (not touched). Dev board: not a project board; left on yd-static or erased at the user's call (recorded)"
---

# V7R-017 — GPIO43 vs GPIO4 static low, YD-ESP32-23 dev board, DMM dose

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | The ~0.5 kΩ low-side resistance is a property of GPIO43 on this module type (WROOM-1 N16R8): another module shows it with no v7 history | map: master: module/path; desk (d) 2026-10-27; notebook s04 (family 1) |
| H2 | It is specific to v7's U3 (this unit, or something v7 does to the pin: boot, damage, a setting not yet found): a module never in a v7 has a normal GPIO43 | map: master: module/path, master: pin role; notebook s04 (family 2) |
| M  | Measurement artefact: DMM lead on the wrong pin or poor contact, the pad not in the mode the firmware claims (read-back), the dev board's own parts on GPIO43 loading the reading, rail not 3.3 V, resistor value wrong | always listed; §4.2 |

**Magnitude (argued; desk (d) 2026-10-27).** On U3, V/I_total = 544–546 Ω for GPIO43, ≈ 32 Ω for GPIO44 (V7R-014 + R29). Datasheet (WROOM-1 v1.8, Table 6-3): I_OL 28 mA at 0.495 V, PAD_DRIVER 3 (≈ 18 Ω). Under H1 at drive 2: 4.7 kΩ adds ~0.6 mA → ~+0.2 V at GPIO43 (after the LED path below). Under H2: ~+20 mV. The two differ by ~10×.

## Confounds (declared; not separated by this card)
- **TX LED on GPIO43 (schematic V1.4, VCC-GND Studio, 2022-09-23: 3V3 → R1 1 kΩ → TX LED → U0TXD = module pin 37 = GPIO43; also CH343P RXD, pin 5, and header J2).** When GPIO43 is low the LED conducts ~1.3 mA into the pin. A fixed extra current shifts V_A but not the slope; the LED's current falls as V rises, so the measured slope is the pin's resistance in parallel with the LED path (~1.1 kΩ): 545 Ω would read ~360 Ω, 32 Ω would read ~31 Ω. Thresholds below allow for this. The user's board is marked V1.3; the LED arrangement is checked by eye at S0 (TX LED near the USB-UART chip, lights when GPIO43 is held low).
- **CH343P half-powered:** its VIO is on 3V3, its core on the COM port's VBUS (unplugged). Its RXD input on GPIO43 is in an undefined state; it is a fixed load during the card.
- **GPIO44 not used:** on this board it is driven by CH343P TXD (push-pull) and has the RX LED, so holding it low would fight a driver. **GPIO4** is the control: header J1 pin only (schematic: GPIO4 net = J1.4 + module pin 4, nothing else).
- **Instrument:** DMM DC volts at the header pins, not the scope at TPIO; static DC level only (as V7R-014's static arms).
- **Module:** same part number as U3 (WROOM-1-N16R8); die revision may differ (recorded from esptool); different board, supply (dev board LDO), and no I²C bus.

## Predictions and exclusions (written before the run)
Per arm: 3 DMM readings ~5 s apart, arm value V = mean. I_ext = (V_rail − V)/R_meas (0 for none). Per pin: R_slope = least-squares slope of V vs I_ext over A1, B, C (A1 as the none level). Anchor: |A1 − A2| per pin.
Controls: (c1) `[regs]` at each mode change: pin under test `mcu_sel=1 out_sig=256 od=1 oe=1 out=0 in=0`, other pin `out=1`; (c2) no reboot line in the serial log during a pin's four arms; (c3) V_rail 3.20–3.40 V; (c4) anchor ≤ 5 mV per pin; (c5) R_meas within 2 % of nominal.

| Outcome (numeric; controls pass) | Excludes | Supports (weakly) |
|---|---|---|
| R1: R_slope(43) ≤ 60 Ω and R_slope(4) ≤ 60 Ω | H1 (on this module) | H2 |
| R2: R_slope(43) ≥ 250 Ω and R_slope(4) ≤ 60 Ω | H2 as necessary (a module never in a v7 shows it) | H1 |
| R3: 60 Ω < R_slope(43) < 250 Ω, R_slope(4) ≤ 60 Ω | — | not resolved; value recorded |
| R4: R_slope(4) > 60 Ω | — for H1/H2 (control fails) | M, or a board/module-wide sink problem |
| Sub-result: V_A(43) and V_A(4) (no external resistor) | — | recorded with the LED/CH343 load |
| Void: any control c1–c5 fails for a pin (that pin's result void) | — | M |

## Setup
- No scope. DMM (the bench DMM used for V7R-016's R_meas and V_rail), DC V, auto range; black lead on a dev board GND header pin, red on the pin under test.
- Resistors: a 10 kΩ and a 4.7 kΩ **not** taken from the V7R-016 breadboard (it stays as left), DMM digits reported out of circuit before S1. Held between the 3V3 header pin and the pin under test in a way that touches only those two pins (female–female Dupont jumpers with the resistor legs in their ends, or the board on a breadboard); operator says which.
- Firmware: yd-static from `lab/evidence/V7R-017/src/yd/` (user approval required), flashed over the native USB port by the session; esptool chip revision and MAC recorded. Modes by serial, sent by the session: `3` = GPIO43 low, `c` = GPIO4 low, `r` = both released.
- Serial log by the session: `lab/captures/V7R-017/2026-MM-DD_V7R-017_yd_01.txt`, `=== <arm>` markers. Measurement log `lab/log/<date>_sNN.yaml` (kind: dmm).
- Time: ~30–40 min bench.

## Arm order (fixed before the run)
| # | Arm | Mode | External resistor (3V3 → pin) |
|---|---|---|---|
| — | S0 | r | none: board ID, LEDs, plug in, flash |
| — | S1 | r | none: V_rail (3V3 pin to GND) |
| 1 | 43-A1 | 3 | none |
| 2 | 43-B | 3 | 10 kΩ → GPIO43 |
| 3 | 43-C | 3 | 4.7 kΩ → GPIO43 |
| 4 | 43-A2 | 3 | none |
| 5 | 4-A1 | c | none |
| 6 | 4-B | c | 10 kΩ → GPIO4 |
| 7 | 4-C | c | 4.7 kΩ → GPIO4 |
| 8 | 4-A2 | c | none |
| — | End | r | none; unplug |

## Procedure (physical steps for the operator)
The session sends every mode command and records every serial line; one instruction block per step.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S0 | Read the board's markings; look for TX/RX LEDs near the USB-UART chip; plug only the native USB port into the Mac (session flashes) | nothing on any header pin; COM port unplugged | markings; LEDs present and their labels; which port; LEDs lit |
| S1 | DMM: 3V3 header pin to GND | DMM on DC V | digits |
| arm (1–8) | Fit / change / remove the arm's resistor; then DMM the pin under test to GND, 3 readings ~5 s apart | resistor only between 3V3 and the arm's pin; DMM leads on GND and that pin | 3 readings; TX LED lit or not (GPIO43 arms) |
| End | Unplug the dev board | — | as left |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
### Measured values (from log; cite `lab/evidence/V7R-017/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: yes/no (commit)
- Result commit: self

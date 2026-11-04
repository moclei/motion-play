---
test_id: PWR-002
title: "SW1 throw on USB power (A/B/A per board): rails, boost pins and USB enumeration in download mode, #0005 (reference) then #0004"
status: run
created: 2026-11-03
prereg_commit: self
baseline:
  name: ref-0005
  firmware_commit: "n/a"
  firmware_env: "#0005 u3-static 3c23d99a (V7R-020); #0004 as found (unknown). Enumeration is judged in ROM download mode, which doesn't depend on the app."
  board_id: "v7-0005 (reference), v7-0004"
  hardware_config: "Each board alone: USB-C J7 to the Mac (same port and cable as V7R-020), no cell, nothing in J3-J6. Power toggled at the Mac end of the cable."
variable_changed: "SW1 throw: as found vs flipped. #0005: ON (VSYS_SENSE) / GND / ON. #0004: GND / ON / GND (PWR-001)."
structure: A/B/A   # per board
revert_on_null: yes  # A2 returns SW1 to its as-found throw on both boards, whatever the outcome
---

# PWR-002 — SW1 throw on USB power, #0005 then #0004

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| Ka | #0004's boost doesn't run because SW1 is at the GND throw (PWR-001: BOOST_EN 0.4 Ω to GND) | STATE §3 Ka |
| Kb | SW1 at ON but BOOST_EN < 1.2 V (contact or joint) | STATE §3 Kb |
| Kc | U6 not alive: BOOST_EN high, VCC ≈ 0 | STATE §3 Kc |
| Kd | FB divider holds FB high: U6 alive but not switching, +5V < VSYS | STATE §3 Kd |
| Ke | U6 switches but is starved (BQ 100 mA default): VSYS < +5V < 4.9 V | STATE §3 Ke |
| B8 | On USB with SW1 at the GND throw, a healthy v7 gives the same symptom as "burnt out" #0001/#0002: no ESP32 on the Mac | STATE §3 B8 |
| M | Measurement artefact: DMM on the wrong pad, not settled, rail read under a loading probe; Mac port or cable; BOOT not held during plug-in | always listed |

**Magnitude (argued).** The v7 feeds U8 (and U3) only from +5V, the boost output. With U6 off, +5V ≈ VSYS minus one diode drop (V7R-020: #0004 +5V 3.754 V, +3.3V 2.69 V). U3's minimum supply is 3.0 V, so 2.69 V is ~10 % under. With U6 on, +5V ≈ 5.1 V (#0003 5.096–5.098 V, V7R-020 E3) and +3.3V ≈ 3.28–3.30 V. The two states are > 1 V apart on +5V and > 0.5 V apart on +3.3V, far outside DMM error.

## Predictions and exclusions (written before the run)
Readings with DMM DC V, black on G (TP4), points as PWR-001 (`lab/procedures/img/v7-power-points.png`): K VSYS, L VSYS_SENSE, M BOOST_EN, Q boost VCC, R FB, N +5V, P +3.3V. "Enumerates" = a VID 0x303A device appears on the Mac (session checks ioreg) after a plug-in with BOOT held.
"Boost on" = N 5.00–5.20 V and P 3.20–3.35 V. "Boost off" = N < K and N < 4.50 V.

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| Void (method): #0005 A1 (SW1 ON) not "boost on", or #0005 A1 doesn't enumerate | — (reference not normal: stop, investigate) | M |
| Void (drift): any rail in A2 differs from A1 by > 0.10 V, or enumeration differs A1 vs A2, on either board | — | M |
| **#0005 GND arm: "boost off", P < 3.00 V, no enumeration** | B8 against | B8 |
| #0005 GND arm: P ≥ 3.00 V, or it enumerates | B8 (as stated) | — |
| **#0004 ON arm: "boost on" and it enumerates; GND arms "boost off"** | Kb, Kc, Kd, Ke as #0004's fault | Ka (cause) |
| #0004 ON arm: M < 1.20 V | Ka as the whole story | Kb |
| #0004 ON arm: M ≥ 1.20 V, Q < 1.0 V | Ka, Kb | Kc |
| #0004 ON arm: M ≥ 1.20 V, Q ≥ 1.0 V, N < K | Ka, Kb | Kd (R reading recorded), Kc (die) |
| #0004 ON arm: K < N < 4.90 V | Ka, Kb, Kd | Ke |
| #0004 ON arm: "boost on" but no enumeration | Ka as the whole story | a fault downstream of +5V/+3.3V (U3, USB path); not on the map |
| Any part too hot to keep a finger on, at any arm | — (stop: unplug the Mac end) | — |

## Setup
- DMM: the one from PWR-001 (S0b: 0.4 Ω leads). DC V, auto-range. Black on G throughout; red moves.
- Power on/off: plug / unplug the **Mac end** of the USB-C cable; the cable stays in the board.
- SW1 is moved only with the Mac end unplugged.
- Download mode: hold BOOT, plug the Mac end in, release BOOT after ~2 s.
- Session checks the Mac: `ls /dev/cu.usbmodem*` and `ioreg -p IOUSB -l -w0 | grep -i -E 'idVendor|USB Product Name'` (VID 0x303A = 12346).
- No scope, no log yaml (DMM + session terminal output, copied into the raw block).

## Procedure (physical steps for the operator)
Per board: arm A1 (SW1 as found), B (flipped), A2 (as found again). Per arm:
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| a | Mac end unplugged; set SW1 for the arm | board alone, nothing in J3–J6 | SW1 slider left/right |
| b | Plug the Mac end in normally; wait 10 s | — | LEDs lit; warm parts (finger: U5, U6, U8, Q2) |
| c | DMM: K, L, M, Q, R, N, P | black on G | each value |
| d | Unplug the Mac end; hold BOOT; plug in; release BOOT | — | done (session reads the Mac) |
| e | Unplug the Mac end | — | done |

Order: #0005 A1 (ON), B (GND), A2 (ON); then #0004 A1 (GND), B (ON), A2 (GND).

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- Pre-run (session, 2026-11-03): Mac shows no /dev/cu.usbmodem* and no VID 12346 (0x303A) device; only Apple internal devices and the AX88179B adapter.
- S1 #0005 A1: SW1 slider "to the left"; LEDs "power led only"; warm "no". Session (normal plug-in, no BOOT): /dev/cu.usbmodem14101; ioreg "USB JTAG_serial debug unit", idVendor 12346.
- S2 #0005 A1 DC V, black G: K "4.283V, going up and down a little, like from 4.260 to 4.300 approximately"; L "4.280V, varying a little just like K"; M "4.280V, same story as the previous two"; Q "5.078V"; R "1.238V"; N "5.100V"; P "3.300V".
- S3 #0005 A1 download mode: "done". Session: /dev/cu.usbmodem14101; ioreg "USB JTAG_serial debug unit", idVendor 12346.
- S4 #0005 B: SW1 slider "right"; LEDs "power led only"; warm "no". Session (normal plug-in): no /dev/cu.usbmodem*, no idVendor 12346.
- S5 #0005 B DC V, black G: K "4.300V with a little variance up and down"; L "4.300V same variance as K"; M "0V"; Q "3.931V with a tiny bit of variance up and down"; R "0.900V with tiny bit of variance"; N "3.799V with tiny bit variance"; P "2.710 with a little bit of variance".
- S6 #0005 B download mode: "done". Session: no /dev/cu.usbmodem*, no idVendor 12346.
- S7 #0005 A2: SW1 slider "left"; LEDs "power"; warm "no". Session (normal plug-in): /dev/cu.usbmodem14101
- Before S8 (user): "if absolutely necessary I'll take these readings, but are they really necessary? I've taken these readings so many times I feel like I'm going crazy. How valuable is this?" Deviation (session): #0005 A2 reads N and P only (the rails the outcome rows use), and A2's download-mode check is dropped (A2 enumerated on the normal plug-in, S7). #0004 arms read M, N, P + the Mac check; Q and R only if the ON arm isn't "boost on".
- S8 #0005 A2 DC V, black G: N "5.100V", P "3.300V".
- S9 #0004 A1: SW1 slider "right"; LEDs "power led only"; warm "no". Session (normal plug-in): no /dev/cu.usbmodem*, no idVendor 12346.
- S10 #0004 A1 DC V, black G: M "0.000V"; N "3.780V with some slight variance up and down"; P "2.700V with small variance up and down". Deviation (session): no download-mode check at #0004 A1 (V7R-020 S4b found none in download mode in this same state); download mode is used at #0004 only if a normal plug-in doesn't enumerate in the ON arm.
- S11 #0004 B: SW1 slider "left"; LEDs "power led only"; warm "no". Session (normal plug-in): /dev/cu.usbmodem14101
- S12 #0004 B DC V, black G: M "0.000V", N "5.118V", P "3.270V". Session: M 0 V with N at 5.118 V is not self-consistent (U6 runs only with EN high); SW1 pin 2 sits ~1.5 mm from pin 3 (GND). M re-read with L as a cross-check (S12b, extra).
- S12b #0004 B re-read: M "4.290V with variance up and down a bit"; L "4.300V with variance up and down a bit". (Item 2, which pin at S12: not answered.) Session: S12 M 0.000 V taken as a tip on the wrong pin (M); S12b M is the reading used.
- S13 #0004 A2 (SW1 back to the right): N "3.775V with some variance"; P "2.700V with some variance". Items 1–3 (slider, LEDs, warm) not answered. Session (normal plug-in): no /dev/cu.usbmodem*, no idVendor 12346.
 | "USB Product Name" = "USB JTAG_serial debug unit"  | "idVendor" = 12346.
 | "USB Product Name" = "USB JTAG_serial debug unit"  | "idVendor" = 12346.
### Measured values (from log; cite `lab/evidence/PWR-002/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: yes/no (commit)
- Result commit: self

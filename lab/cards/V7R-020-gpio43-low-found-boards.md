---
test_id: V7R-020
title: "GPIO43 vs GPIO44 static low (plain open-drain GPIO, I²C detached) on v7 #0004 and #0005, with #0003 as the same-instrument reference: DMM at TPIO43 / TPIO44 against the on-board 2.2 kΩ pull-ups"
status: run
created: 2026-10-31
prereg_commit: self
baseline:
  name: v7-clean
  firmware_commit: "self"      # run image u3-static rebuilt unchanged from lab/evidence/V7R-014/src/u3/ (v7_static_low 1.0) at the prereg commit; app sha256 3c23d99a… (lab/evidence/V7R-020/fw/, SHA256SUMS). Differs from V7R-014's approved 493a0235… by build path only (Planner relay 2026-10-26, open). Card delta: needs the user's approval before S4.
  firmware_env: "u3-static"
  board_id: "v7-0003 (reference), v7-0004 ('Board X'), v7-0005 ('Board #3')"
  hardware_config: "#0003 as V7R-019 End (STATE §6) except rigid #1 out of J6 for the card (J4, J6 empty; pigtail stays in J5, channel never opened by u3-static; Nano wired at TPIO43/44, powered before and whenever the v7 is, V7R-008); scope probes stay seated at S1, scope not used. #0004 and #0005: alone on the bench, USB-C J7 to the Mac only, nothing in J3–J6, no battery, no wires added."
variable_changed: "Which v7 board's U3 GPIO43 is held low: #0003 (reference, ~545 Ω known) vs #0004 vs #0005. Within each board, GPIO44 held low the same way is the within-chip control (A/B/A: 43 / 44 / 43)."
structure: "Per board A/B/A (GPIO43 low / GPIO44 low / GPIO43 low) in one boot by serial command, after an idle arm r; across boards single (justify: no board can be swapped back to another's U3; #0003 first as the method anchor on a board whose value is known)"
revert_on_null: "yes for #0003 on every outcome: rigid #1 back into J6 (v7 and Nano unplugged), flash diag 166f5f40. #0004 / #0005: left on u3-static or erased, user's call (recorded)"
---

# V7R-020 — GPIO43 vs GPIO44 static low on #0004 and #0005, #0003 as reference

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | #0003's GPIO43 low-side resistance is #0003's own (unit): other v7 boards from the same order have a normal GPIO43 (≲ 100 Ω, like GPIO44) | map: master: identity (a); checkpoint @ V7R-019 challenge 1 |
| H2 | It is shared across the v7 boards (module batch / JLC assembly, or something the v7 design does to the pin; (b) and (c) not separated by this card): #0004 and #0005 show GPIO43 ≳ 300 Ω with GPIO44 normal | map: master: identity (b)/(c); user prior (notebook 2026-10-31, argued) |
| M  | Measurement artefact: DMM lead off the pad or on the wrong pad, pad not in the mode the firmware claims (read-back), leakage on SDA from another damaged part on the board (idle level), rail not 3.3 V, DMM vs scope disagreement on #0003 | always listed; §4.2 |

**Magnitude (argued; desk (d) 2026-10-27).** Static low V_L = V_idle × R_pin / (R_pin + R_pu), R_pu = R28 (2.2 kΩ, schematic, not measured; ∥ 45 kΩ internal pull-up if `wpu=1` in the read-back, −5 %). #0003 (~545 Ω): V_L ≈ 3.3 × 545 / 2745 ≈ 0.65 V (V7R-016 stub frame low 677 mV, scope). Normal pad (~32 Ω, V7R-014 GPIO44; 29.5 Ω, V7R-017): ≈ 0.05 V. ~13× apart. Back-calculated R = V_L × R_pu / (V_idle − V_L).

## Confounds (declared; not separated by this card)
- **History of #0004 / #0005 unknown.** User suspects both are dead (2026-10-31); #0005 is likely legacy B3 (marker; argued), which NACKed at its first diag run (L-Ph9). A damaged board can show an elevated GPIO43 for a reason unrelated to #0003's. A board that doesn't boot gives only the unpowered branch (weak).
- **(b) batch vs (c) design-caused** are not separated: all v7 boards are from one JLC order with one design.
- **Instrument:** DMM DC volts, static; #0003's known values are scope (V7R-014/-016). The #0003 arms are the same-instrument anchor.
- **TCA channel 2 opened by u3-static** at every mode change (V7R-014 behaviour); J6 is empty on all three boards in this card, so no far-end path. `tca_write_err` is recorded, not a control (a damaged TCA must not void the GPIO reading).
- **Other parts on the SDA net** (TCA U4, BQ U5, INA U7) on a damaged board may leak; the idle arm r catches leakage to GND (V_idle low) but not a part that sinks only when SDA is low.
- **Firmware rebuild:** same source as V7R-014; hash differs by build path only (relay 2026-10-26). Loadable segments not compared (V7R-014's original binary was not kept).

## Predictions and exclusions (written before the run)
Per arm: 3 DMM readings ~5 s apart at the pad under test, arm value = mean; one reading at the other pad. Arms in order: r (idle: V_idle43, V_idle44), 3a (V_L43; V44 high), 4 (V_L44; V43 high), 3b (V_L43).
Controls per board: (c1) `[static]` banner `sketch=v7_static_low version=1.0`, and at each mode change `[regs]` shows the pin under test `oe=1 out=0`, the other `oe=1 out=1`, both `od=1 out_sig=256`; (c2) no reboot line in the board's serial log between r and 3b; (c3) V_idle43 and V_idle44 3.20–3.40 V; (c4) |3a − 3b| ≤ 10 mV; (c5) chip revision and MAC from esptool recorded.
**Method anchor (#0003, rigid out):** V_L43 0.55–0.80 V and V_L44 ≤ 0.15 V with c1–c5 passing. If it fails, the card stops before any found board is powered: void for the method, M.

Per found board (#0004, #0005), anchor and controls passing:
| Outcome | Reading | Excludes | Supports (weakly) |
|---|---|---|---|
| N | V_L43 ≤ 0.15 V and V_L44 ≤ 0.15 V | H2 for that board | H1 |
| E | V_L43 ≥ 0.40 V and V_L44 ≤ 0.15 V | H1 as "#0003 only" | H2 |
| U | 0.15 V < V_L43 < 0.40 V, V_L44 ≤ 0.15 V | — | value and R recorded |
| C | V_L44 > 0.15 V | — (control fails for that board) | M, or a board-wide sink / leakage |
| Void | c1–c4 fail for the board | — | M |

Across both found boards (written before): both E → H1 excluded as the whole account; H2 supported on three boards. Both N → H1 supported (#0003 differs from two siblings); H2 excluded as "every board from this order". One E, one N → recorded; no exclusion of H1 or H2 as a class.

**Unpowered branch (a found board fails the S2 rail check, or doesn't enumerate in download mode at S4):** DMM diode test, red on U8 pin 1 (GND), black on TPIO43, then TPIO44, 3 readings each. Recorded only; no row above applies to that board; |Δ| > 50 mV recorded as an asymmetry (argued meaning only).

## Setup
- No scope. Bench DMM (V7R-016/-017), DC V auto range; diode range for the unpowered branch.
- Measurement log: `lab/log/2026-10-31_s01.yaml` (kind: dmm, as V7R-017). Serial logs: `lab/captures/V7R-020/2026-10-31_V7R-020_<board>_01.txt` (serlog.py from `lab/evidence/V7R-014/src/session/`), `=== <arm>` markers.
- Points (picture `lab/procedures/img/v7-probe-points.png`): A = TPIO43 ("SDA"), B = TPIO44 ("SCL"); GND = U8 pin 1 (the SOT-223 regulator near PWR LED, the narrow leg farthest from the USB-C edge; U8.1 GND, U8.2 +3.3 V, U8.3 +5 V nearest the USB-C edge; the wide tab is +3.3 V). On #0003: A and B via the Nano breadboard columns A4 / A5 (green / yellow), GND via the Nano GND column; the seated scope probes are not touched.
- Firmware: `lab/evidence/V7R-020/fw/` (`shasum -c SHA256SUMS` first). App at 0x10000 with `--flash_mode keep` (as V7R-014/-019). Fallback for a found board whose app doesn't start: full write (bootloader 0x0, partitions 0x8000, boot_app0 0xe000, app 0x10000) from the same folder, recorded as a deviation. Download mode if needed: hold the IO0 button (below the module, labelled "IO") while plugging in.
- **Probe moves:** none (scope probes stay on #0003 at S1; DMM only).
- Time: ~1.5–2 h.

## Procedure (physical steps for the operator)
The session runs every flash, mode command and serial log; one instruction block per step.
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S1 | #0003: unplug the v7, then the Nano (Mac end). Rigid #1 out of J6; park it. Plug in the Nano, then the v7 | J6 and J4 empty; pigtail still in J5; scope probes untouched | done; LEDs |
| S1f | Session approves the delta with the user, flashes u3-static on #0003, checks the banner | — | — |
| R (#0003) | Arms r, 3a, 4, 3b: DMM red in the A4 column (A4 for GPIO43 arms, A5 for the 44 arm and idle 44), black in the Nano GND column; readings as the session asks | leads only in those holes | readings |
| S2 | #0004 then #0005, each unpowered: look over both sides; DMM ohms, U8.1 (GND) to the U8 tab (+3.3 V), and U8.1 to U8.3 (+5 V) | board unpowered; nothing in any connector | what you see (burn marks, cracked or missing parts); both readings per board |
| S3 | Unplug #0003's v7, then the Nano (Mac end); they stay as wired | — | done |
| S4 | First found board that passed S2 (> 10 Ω on both rails): USB-C J7 to the Mac. Session looks for the port; if none, unplug, hold IO, plug in | PWR LED; nothing touches the board | PWR LED; any other LEDs; board warm anywhere (finger near U8, U5, U3) |
| arms | Session flashes u3-static, then arms r, 3a, 4, 3b: DMM red on A (or B), black on U8.1; 3 readings ~5 s apart | probe tip on the pad centre, not the ring | readings |
| S5 | Unplug that board; repeat S4 + arms for the other board | — | as above |
| End | All found boards unplugged. #0003: rigid #1 back into J6 (unplugged), plug in the Nano, then the v7; session flashes diag 166f5f40 | rigid fully seated, SW1 ON, SW2 OFF | bench state |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- Session date 2026-11-01 (card says 2026-10-31).
- Approvals (user): "1. approve 2. yes 3. yes" (u3-static delta; rigid out of J6; power #0004/#0005 from the Mac if no short).
- S1: "LEDs off"; "J4, J5 and J6 are empty" then "Oh sorry, pigtail is in J5"; probes as left: "yes".
- S1b: "both plugged in". Session: only `/dev/cu.usbmodem14101` enumerated (one Espressif VID 0x303A device; #0003 previously 14301).
- S1c: "OK the v7 is on now, but the RGB LED (D5) is on and colored blue. One of the probes had slipped and had move it's ground spring from C9.1 to C9.2, so that probe was bridging C9.2 and the SCL testpad I guess"
- S1d (incident, make safe): spring "was already moved, both probes are off the board and parked"; time plugged in with the spring on C9.2 "maybe one minute"; "Nothing warm"; C9 pads / spring tip marked: "No".
- S1e (#0003 unpowered, DMM ohms, black U8.1): U8.1 → tab (+3.3 V) "306.1, not climbing"; U8.1 → pin 3 (+5 V) "This one seems to start at about 600k but then keep getting lower. After 5 seconds it was still rapidly lowering and after a minute or two it seemed to settle at around 260k.." No pre-incident reference for #0003.
- S1f: "Powered on, LED's back to being good now"; warm: "No". Session: both ports enumerated (Nano 14101, #0003 14301). Pre-flash diag (v7-clean diag 166f5f40) 5 s: TCA1 row BQ X(2) ×2, all other rows INA/BQ/TCA '.' (`lab/captures/V7R-020/2026-11-01_V7R-020_0003_prediag.txt`).
- #0003 flash: esptool "Chip is ESP32-S3 (revision v0.2)", "MAC: 44:1b:f6:c5:58:c4", app 0x10000 hash verified. Banner printed before the logger opened (not captured; deviation); `[static] mode=r tca_write_err=0 tca_reg=0x04`, both pads `od=1 out_sig=256 oe=1 out=1`, `wpu=0`.
- R-r (#0003, DMM at Nano A4 / A5, black Nano GND column): "Both A4 and A5 read 3.279 V"
- R-3a (#0003, GPIO43 low): A4 "0.64V all three times"; A5 "3.28V"
- R-4 (#0003, GPIO44 low): A5 "0.050V all three times (would flicker between 0.049V and 0.050V, but mostly be 0.050V)"; A4 "3.280V"
- R-3b (#0003, GPIO43 low, repeat): A4 "0.641V all three times". Session: no reset/boot line in `2026-11-01_V7R-020_0003_01.txt` from r to 3b.
- S2 #0004: markings: "It had no markings so I took a black sharpie and wrote \"#0004\" on it"; look-over: "No burn marks or discoloring. Pristine really"; U8.1 → tab "304.9 (settled)"; U8.1 → pin 3 "It started around 3m and kept dropping. After 15s it was about 1.5m and was still dropping"
- S2 #0005: markings: "This one had \"Board #3\" written on it. I wrote \"#0005\" on it in sharpie"; look-over: "Don't see any burn marks or anything at all really"; U8.1 → tab "304.4"; U8.1 → pin 3 "Same as the last one, started at around 3m and started dropping, was around 1.5m after 15s or so."
- S3: #0003 and Nano unplugged, "All off"; same Mac port reused for found boards (user knows which).
- S4 #0004 (USB-C J7 to the Mac, same port, same cable): PWR LED "On"; other LEDs "No"; warm "No". Session: no /dev/cu.usbmodem*, no VID 0x303A device in ioreg.
- S4b #0004 download mode: silk labels are "RESET" and "BOOT" (card said IO / RE: render truncation); BOOT held while plugging in: "Done". Session: still no /dev/cu.usbmodem*, no VID 0x303A device (only the Mac's own devices and a USB Ethernet adapter).
- S4c #0004 powered, DMM DC V, black U8.1 (extra observation, not in the card): U8 tab (+3.3 V) "Around 2.680, but kind of hovering there up to 2.701"; U8 pin 3 (+5 V) "Around 3.754, but going up and down a bit in the 3.7XX range". (+5V net = TPS61088 U6 VOUT → U8 VIN, D5 VDD, F1; circuit-context @ c2acffc, no provenance.)
- S4d #0004 unplugged; diode mode, red U8.1, black on pad: SDA (TPIO43) "1.162, all 3"; SCL (TPIO44) "1.160, all 3"
- S5 #0005 (USB-C J7, same port and cable): PWR LED "on"; D5 "yes D5 is blue"; warm "No". Session: enumerates as /dev/cu.usbmodem14301 (VID 0x303A); port drops repeatedly. 20 s log (`2026-11-01_V7R-020_0005_preflash.txt`): an old Motion Play image (deviceId 'motionplay-device-002') reboots ~1 s apart, 20 "Motion Play Device - BOOT" banners, each after "Connecting to WiFi"; "[DBG] B: reset_reason=9"; "[I2C SCAN] Found device at 0x40", "Found device at 0x70", "BQ24195 not found at 0x6B"; "[PWR after BQ config] VSYS=4.30 V". esptool app flash failed: "Device not configured" (port dropped mid-connect).
- S5b #0005 download mode (BOOT held while plugging in): "OK done". esptool: "Chip is ESP32-S3 (revision v0.2)", "MAC: 44:1b:f6:c5:58:a4", app 0x10000 hash verified; `run` did not start the app (no reply to `r`).
- S5c RESET pressed: "PWR is on, D5 is still blue". Banner `[static] sketch=v7_static_low version=1.0`, `mode=r tca_write_err=0 tca_reg=0x04`, both pads `od=1 out_sig=256 oe=1 out=1`, `wpu=0`; one banner (no boot loop on u3-static).
- #0005 r (DMM on pads, black U8.1): "Both read 3.300V"
- #0005 3a (GPIO43 low): SDA "0.644V" (one value reported for the three readings); SCL "3.300V"
- #0005 3a confirmed: "All three showed 0.644". #0005 4 (GPIO44 low): SCL "0.046V all three times"; SDA "3.300V"
- #0005 3b (GPIO43 low, repeat): SDA "0.644V all three times". Session: one banner, no reset line in `2026-11-01_V7R-020_0005_01.txt` from r to 3b.
- Deviation: both scope probes lifted off #0003 and parked (not in the card; card uses no scope). Scope probes need a full re-seat + V1–V8 before any later scope card.
### Measured values (from log; cite `lab/evidence/V7R-020/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched:
- Hypotheses excluded:
- **Strength:**
- Revert-on-null done:
- Result commit: self

---
as_of: PWR-000            # highest card ID with status recorded|abandoned that this file reflects (PWR-000 = sentinel, nothing recorded)
updated: 2026-11-02       # date of the last edit
last_checkpoint: PWR-000  # card ID at which the last step-back checkpoint ran (context-strategy §4.3)
open_cards: [PWR-001]            # cards with status pre-registered|run; must match lab/cards/ (checked)
prefix: PWR               # card ID prefix of this investigation (lab/cards/PWR-NNN-<slug>.md); unique across lab/investigations/
title: "v7 power path: battery damage and #0004 boost"
status: open              # open | closed
---

# v7 power path: battery damage and #0004 boost — current state
> Debugger sessions: this is L0. Other sessions: read sections 1–4 and stop. Never restate a result here. Cite its card. Max ~150 lines; the check warns beyond that.
> New investigation (`tools/lab/new_investigation.py`): sections are empty. The first debugger session fills sections 1–8 from the intake relay in one commit (context-strategy §4.4). Boards, fixtures and what's flashed live in `lab/BENCH.md`, shared by every investigation.

## 1. Symptom                                   (≤ 6 lines)
- v7 #0001 and #0002: after a Samsung 30Q 18650 (3000 mAh, 15 A) went into BT1 (SW1 OFF, no USB, no LED strip; orientation "pretty sure" correct), USB was plugged in to talk to the ESP32 and the Mac didn't find it; "after some fiddling around it seemed like the thing was burnt out". Nothing seen or smelled (user, 2026-11-02). Both boards since binned (user, 2026-11-02).
- v7 #0004 on USB-C, no battery: PWR LED on, no USB device in normal or download mode, +5V ≈ 3.75 V, +3.3V ≈ 2.69 V (V7R-020 S4/S4c).
- Repro: none. #0001/#0002 no longer exist; board-level evidence of their event is gone.

## 2. IS / IS NOT                               (KT table, ≤ 12 rows)
| Dimension | IS | IS NOT | Distinction | Evidence |
|---|---|---|---|---|
| Boards (battery) | #0001, #0002 (user) | v7 run from a 3.7 V / 500 mA PSU on BAT_RAW, VBUS absent (legacy Ph18) | real cell (stiff source) vs current-limited PSU; polarity unknown | legacy Ph18; user |
| Boards (boost) | #0004 (+5V 3.75 V) | #0003 (+5V 5.096–5.098 V), #0005 (boost and LDO up) | none known yet; SW1 position on #0004 not recorded | V7R-020 S4c, E3, S5 |
| Unpowered rails | — | #0004 +3.3V–GND 304.9 Ω (≈ #0003 306.1, #0005 304.4); +5V–GND falling MΩ drift on all three | no shorted rail on #0004 | V7R-020 S1e, S2 |
| When | seen at the next USB plug-in after the cell went in (#0001/#0002) | no smoke, smell or visible mark at insertion | — | user 2026-11-02 |
| Symptom after | Mac doesn't find the ESP32 (#0001/#0002; #0004) | — | same operator symptom on #0004, whose battery history is unknown | user; V7R-020 S4 |
| Conditions | one 30Q cell, SW1 OFF at insertion, no USB, no LED strip | 2S pack; LED strip load | — | user 2026-11-02 |

## 3. Hypothesis map                            (one row per region, ≤ 25 rows)
Mechanism numbers as in the intake relay. All desk analysis: SESSION Worker #2 Notes (feat/v8-debug-board).
| Region | Hypothesis (one line) | Status | Strength | Evidence | Last touched |
|---|---|---|---|---|---|
| B1 reversed cell | cell reversed in BT1; Q2 body diode + U5 BAT substrate carry cell current; C30 reversed | untested | argued | relay | intake |
| B2 Q2 under-driven | Vgs ≈ −Vcell/2 (below the −2.5 V Rds(on) spec); Q2 overheats under real load, no battery-side fuse | untested | argued | relay | intake |
| B3a BATFET latch | hot-plug inrush > 9 A trips BQ BATFET OCP; board dead on battery until VBUS, not damaged | untested | argued; against as the whole story (USB was plugged in afterwards, which clears the latch; user) | relay; user 2026-11-02 | intake |
| B3b overshoot | LC ringing at plug-in takes BAT/SYS > 6 V | untested | argued (unlikely: electrolytic ESR) | relay | intake |
| B4 boost into load | SW1 ON with heavy +5V load (LED strip) → U6 at ILIM through Q2 | untested | argued against for the event (SW1 OFF, no strip; user); live as a design risk | relay; user 2026-11-02 | intake |
| B5 BT1 + pad bridge | solder/tab bridges BT1 + (BAT_RAW) to J7 rear shell legs (0.78 mm) or USB_DN via (0.38 mm) | untested | argued; untestable (only #0001/#0002 had a holder soldered; both binned) | relay (kiutils + B.Mask @ c2acffc) | intake |
| B6 wrong source | source > 6 V (not one Li-ion cell) | untested | argued against (one 30Q cell, ≤ 4.2 V; user) | relay; user 2026-11-02 | intake |
| B7 TS network | cannot cook a board | untested | argued | relay | intake |
| B8 not damaged | #0001/#0002 not damaged: on USB with SW1 OFF, U6 doesn't switch, U8 in dropout, U3 below 3.0 V → no USB device (as #0004 Ka) | untested | argued (fits SW1 OFF at insertion; SW1 position at the USB plug-in not recalled) | user 2026-11-02; V7R-020 S4c | intake |
| Ka SW1 OFF | #0004 boost off because SW1 OFF (BOOST_EN held low by R2) | untested | argued | V7R-020; relay | intake |
| Kb SW1 contact | SW1 ON but BOOST_EN < 1.2 V | untested | argued | relay | intake |
| Kc U6 not alive | BOOST_EN high, U6 VCC ≈ 0 (joint or die) | untested | argued | relay | intake |
| Kd FB divider | R39/R40 fault holds FB > 1.204 V | untested | argued | relay | intake |
| Ke input starved | BQ 100 mA default limit can't start the boost | untested | argued (against: #0005 runs on the same limit) | relay | intake |
| M | measurement artefact (DMM lead/pad, settle time, in-circuit parallel paths, PSU limit) | untested | not tested | — | intake |

## 4. Facts in use                              (≤ 15 rows)
| Fact | Strength | Source |
|---|---|---|
| Path: BT1+ → BAT_RAW → Q2 (AO3401A; S BAT_RAW, D VBAT, G = VBAT/2 via R33/R34 100 k) → VBAT → U5 BAT; U5 SYS → VSYS → R44 → VSYS_SENSE → U6 VIN (EN = BOOST_EN, SW1, R2 pull-down) → +5V → U8 → +3.3V | argued (schematic) | circuit-context.json @ c2acffc; SESSION Worker #1 |
| Test pads: TP1 VSYS, TP2 VBAT, TP3 Protected_VBUS, TP4 GND | argued (schematic) | same |
| A v7 ran from 3.7 V / 500 mA PSU on BAT_RAW, VBUS absent, no damage; Q2 channel conducts BAT_RAW → VBAT | measured (legacy) | v7-i2c-investigation.md Phase 18 |
| #0004 powered on USB: +5V 3.754 V (3.7x), +3.3V 2.680–2.701 V | measured (one DMM pass) | V7R-020 S4c |
| #0003 powered: +5V 5.096–5.098 V, +3.3V 3.276 V | measured | V7R-020 E3 |
| #0005: boots on USB; VSYS 4.30 V (old image, INA219); BQ absent at 0x6B; brownout loop on the old image | measured (firmware-reported) | V7R-020 S5 |
| BT1 is not fitted by JLC: bare pads on every v7; the user hand-soldered separately bought holders on #0001 and #0002 only | measured (user) | user 2026-11-02 (PWR-001 raw) |
| No battery-side fuse; VBAT has no capacitor; BQ BATFET OCP 9 A latches until VBUS | argued (schematic + SLUSB97A) | SESSION Worker #2 |

## 5. Tombstones                                (one line each, never deleted)

## 6. Baselines and bench state                 (≤ 15 lines)
- No firmware baseline: no firmware change is part of this investigation.
- `ref-0005`: v7 #0005 as found at V7R-020 end (u3-static 3c23d99a; no mods). Power reference: every suspect reading is compared with the same reading on #0005, not with a datasheet number.
- `0004-as-found`: v7 #0004 as found (never flashed this track; SW1 position not yet recorded).
Boards and bench: see `lab/BENCH.md` (boards, fixtures, flashed now, bench at last stop; shared by every investigation).

## 7. Measurement trust                         (≤ 10 rows; rows leave when re-measured)
| Earlier result | Verdict | Load-bearing for | Pending |
|---|---|---|---|
| V7R-020 S4c #0004 +5V / +3.3V (DMM, one pass) | unknown | Ka–Ke | re-read at 4a |
| V7R-020 S5 #0005 VSYS 4.30 V (old image's INA219 print) | suspect (firmware-reported, uncalibrated) | ref-0005, Ke | DMM at TP1 at 4a |
| Legacy Phase 18 (3.7 V PSU on BAT_RAW, no damage) | unknown (legacy, board identity uncertain) | B2, B6 | 4b |
| User recollection of the #0001/#0002 event (2026-11-02) | unknown (months later; orientation "pretty sure") | B1, B3a, B4, B6, B8 | — (boards binned; can't be re-measured) |

## 8. Next                                      (≤ 6 lines)
- Open cards: PWR-001 (passive survey #0004 vs #0005), pre-registered.
- Proposed next: PWR-001 passive on #0004 and #0005 (SW1 as found, look-over, holder keying, rail ohms + diode mode to GND; no power). Then PWR-002: SW1 OFF/ON/OFF on USB (#0005, then #0004): cuts B8 and Ka–Ke.
- Blocked on: #0001/#0002 binned (B1, B5 can only be tested as design questions on other boards); Phase 7 of v8-debug-board waits on these cards (W1).

## 9. Lookups (L1 routing)                      (≤ 15 rows)
| When you need… | Load | Section/query |
|---|---|---|
| the intake request | docs/initiatives/v8-debug-board/debugger/RELAY-power.md (feat/v8-debug-board) | whole (steps 0–5, result table) |
| mechanism table with datasheet values | docs/initiatives/v8-debug-board/SESSION.md (feat/v8-debug-board) | Worker #2 Notes, Task 1 / Task 2 |
| v7 power-path pin → net trace | same SESSION.md | Worker #1 Notes |
| v8 battery section, design deviations | hardware/pcb-main-v8/CONTEXT.md | Inherited v7 faults |
| pin → net | hardware/pcb-main/kicad/circuit-context.json @ c2acffc | jq by ref (check `--fresh` first) |
| datasheet values | docs/references/{bq24195,tps61088,ina219}/DATASHEET_REFERENCE.md | by parameter |
| legacy 3.7 V PSU run | docs/debugging/v7-i2c-investigation.md | grep "Phase 18" |
| #0004 / #0005 found-board readings | lab/cards/V7R-020-gpio43-low-found-boards.md | raw S2, S4–S5, E3–E4 |
| boards, fixtures, what's flashed | lab/BENCH.md | per board ID |

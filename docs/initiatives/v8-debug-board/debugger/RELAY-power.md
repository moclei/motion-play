# Relay-initiative (v8-debug-board, Phase 2 Worker) — Debugger — 2026-11-02

role:debugger

## Context
The v8 debug board's power path has to be designed after a methodical look at why connecting a battery cooked v7 boards #0001 and #0002, and why #0004's boost doesn't run (v8 BRIEF goal; PLAN wait W1). The initiative traced the v7 battery → charger → boost → LDO path from the schematic and datasheets and ranked the ways a battery could damage a v7 board. The desk can't pick between them: that needs the boards. This relay asks for that bench evidence. It is a request, not an instruction (PROTOCOL Relays, Initiative → Debugger): you and the user decide where it goes in the bench queue.

**In plain words:** the likeliest causes are (1) a cell put in the holder backwards, which this circuit doesn't block; (2) the battery MOSFET Q2 being driven with only half the cell voltage on its gate, so it runs hot under a real load and has no fuse in front of it; and (3) a hand-soldering bridge at the holder's + pad, which sits under a millimetre from the USB-C shell legs and a USB D− via. Passive checks on the cooked boards (look, ohms, diode mode, no cell) separate these. #0004 most likely has a boost converter that isn't switching, and the first check is simply which way its power switch SW1 is set.

## Load these files
- .context/PROTOCOL.md (Relays; Escalation Paths, Debugger row)
- docs/initiatives/v8-debug-board/SESSION.md — Worker #1 Notes (v7 power-path trace, pin → net; Q2 and BT1 checks) and Worker #2 Notes (the ranked mechanisms table; #0004 / #0005 analysis). This relay is the bench side of those notes; the tables there carry the datasheet values.
- hardware/pcb-main-v8/CONTEXT.md — Inherited v7 faults (BQ root cause; battery section)
- hardware/pcb-main/kicad/circuit-context.json (v7 @ `c2acffc`) for any pin → net lookup
- lab/BENCH.md; lab/cards/V7R-020-gpio43-low-found-boards.md (the #0004 / #0005 readings this relay starts from)
- docs/debugging/v7-i2c-investigation.md Phase 18 (a v7 run from a 3.7 V / 500 mA bench PSU on BAT_RAW, VBUS absent, no damage)
- docs/references/{bq24195,tps61088,ina219}/DATASHEET_REFERENCE.md

## State
Branch: feat/v8-debug-board (initiative work only; the Debugger works in `lab/` on its own branch as usual)
Build: n/a (no firmware change requested)
TASKS.md current: yes (Phase 2)

`lab-multi-investigation` is merged (PR #89, commit `36ab0ad`), so this relay doesn't wait on it. Per TASKS Deferred: run it as its own investigation with `PWR` cards, scaffolded at intake with
`python3 tools/lab/new_investigation.py --name power --prefix PWR --title "<title>"`.
You decide whether #0004 also belongs to `power` in `lab/BENCH.md` (it is listed under v7-i2c today).

**No change to the debug track's order unless the user says so.** The v7-i2c queue keeps its order; this investigation runs beside it, or after it, as the user chooses. #0003 (the only good unit, set up for v7-i2c) is not used here unless the user says so.

## What was done
- v7 power path traced at `c2acffc` (Phase 1): BT1 + → BAT_RAW → Q2 (AO3401A, S on BAT_RAW, D on VBAT, gate = VBAT/2 via R33/R34 100 k each) → VBAT → U5 BQ24195 BAT; U5 SYS → VSYS → R44 10 mΩ → VSYS_SENSE → U6 TPS61088 VIN (EN = BOOST_EN from SW1, R2 100 k pull-down) → +5V → U8 AMS1117 → +3.3V. Test pads: TP1 VSYS, TP2 VBAT, TP3 Protected_VBUS, TP4 GND.
- BQ "needs an I²C command" root-caused on the desk: D+/D− on GND and OTG pulled to a rail that only exists after start-up give a 100 mA input limit on every USB plug-in (hardware/pcb-main-v8/CONTEXT.md).
- Q2 is in load-switch orientation: its body diode doesn't block a reversed cell. Its gate drive is about −Vcell/2 (−1.5 to −2.1 V), below the −2.5 V where its on-resistance is specified.
- Phase 18 (legacy, measured): a v7 ran from 3.7 V / 500 mA on BAT_RAW without damage. A soft, current-limited source in the right polarity doesn't cook a board, and Q2's channel does conduct BAT_RAW → VBAT.
- Board geometry (kiutils + B.Mask gerber, `c2acffc`): BT1's + pad (B side) is 0.78 mm edge-to-edge from J7's two rear USB-C shell legs (through-hole, exposed, no net) and 0.38 mm from a tented USB_DN via. BT1 is hand-fitted (no LCSC part).
- Ranked mechanisms (SESSION Worker #2 Notes): 1 reversed cell; 2 Q2 under-driven under load; 3 hot-plug inrush (incl. the BQ's 9 A BATFET over-current latch, which makes a board look dead on battery until USB is plugged in); 4 boost enabled into a load; 5 bridge at BT1's + pad; 6 DC abs-max (refuted for one Li-ion cell; live only if the source was > 6 V); 7 TS network (can't cook).
- #0004 (argued from V7R-020): no rail shorted; U6 not switching, so +5V is VSYS passed through U6's body diode and U8 is in dropout. #0005 (argued): its brownout loop is the 100 mA default limit because its BQ is absent from I²C; its BQ's buck still runs (VSYS 4.30 V). Neither shows battery damage.

## Your task
Bench evidence that separates the mechanisms above, on **#0001, #0002 and #0004**. The user supplies #0001 and #0002 (not on the bench yet) and any cell or pack that was used in the original events. Reference board for "what normal reads": **#0005** (its power path runs: boots on USB, VSYS 4.30 V, boost and LDO up), unless the user prefers otherwise. Every reading on a suspect board is compared with the same reading on the reference, never with a datasheet number (in-circuit readings include every part on the net).

Non-destructive first. Nothing powered on a board until its passive readings say the input being powered isn't shorted. **No real cell goes into any holder** at any step except the optional last one.

**0. Recollection (user, before the bench).** For #0001 and #0002: which battery (an 18650 in the holder, or a pack/cell on leads; its voltage), which way round it went in, whether a USB cable was plugged in at the time, SW1 position, whether the LED strip was connected, what was seen or smelled and where, what stopped working afterwards. Each answer narrows the table below; "don't remember" is a fine answer.

**1. Visual (unpowered, all three + reference).** Both sides, under a loupe; photos of each. Look at: Q2 (SOT-23, top side, near the BQ), U5 (BQ24195 QFN), U6 (TPS61088), C29 (220 µF can) and C30 (47 µF can, by the holder's + end) for bulging, venting or residue; scorch or discolouration anywhere. Bottom side at BT1's + end (pad 1, the end with the "+" silk and the locating hole): solder on or near J7's two rear shell legs and around the via just beside the pad; mask scratches. The holder: part marking (Keystone 1042 vs 1042P), and whether the two contacts differ in shape so that a reversed cell can't touch both (look only; no cell). Record SW1's position on #0004 as found.

**2. Per-rail resistance to GND (unpowered, DMM ohms, black on GND = U8 pin 1 or TP4, settle ~15 s, note any drift).** BAT_RAW (BT1 pad 1 or C30 +), VBAT (TP2), PMOS_GATE (Q2 pin 1), VSYS (TP1), VSYS_SENSE (C41 or U6 VIN side of R44), BOOST_EN (SW1 centre pin), +5V (U8 pin 3), +3.3V (U8 tab), Protected_VBUS (TP3), BQ_PMID, BQ_REGN. Known values from V7R-020: +3.3V 304–306 Ω on #0003/#0004/#0005; +5V a falling MΩ drift on all three. Plus continuity, unpowered: BAT_RAW ↔ J7 shell, BAT_RAW ↔ USB_DN (U9 pin 3 or 4).

**3. Diode mode on the power parts (unpowered; both lead orders, as V7R-020 E4).** Q2: all three pin pairs. The body diode should show from pad 3 (D, VBAT) to pad 2 (S, BAT_RAW) and not the other way; this also confirms the G/S/D mapping on that board. U5: VBUS, PMID, SW, SYS, BAT, REGN, TS, ILIM, OTG, SDA, SCL to GND. U6: VIN, SW, VOUT, EN, VCC, FB to GND. U8: VIN, VOUT to GND.

**4. Powered, current-limited bench supply, one input at a time.** Only on inputs whose step 2 readings match the reference. Start at a 50 mA limit, raise in steps, stop at any surprise. Finger or thermal camera on Q2, U5, U6, U8 at each step (thermal check here).
- 4a. **VBUS input** (USB power meter in the cable, or the PSU at 5.0 V / 500 mA on TP3 with USB data unplugged). Read VSYS (TP1), VSYS_SENSE, BOOST_EN, U6 VCC (pin 1), U6 FB (pin 17), +5V, +3.3V. #0004 first, as found, then with SW1 ON if it was OFF.
- 4b. **Battery input from the PSU, not a cell** (clip leads on BT1's pads or soldered leads on BAT_RAW and TP4, as Phase 18). VBUS absent. 3.7 V. SW1 OFF, then ON. Read Q2 Vds (BAT_RAW − VBAT), VSYS, +5V, +3.3V and the supply current.
- 4c. **Q2 under load (on the reference board, or a board whose power path passes 4b).** Set a known battery-side current with a dummy load on +5V (power resistor or electronic load), 0.5 A then 1 A from the PSU. Record Q2 Vds and its temperature at each. 2 A only with the user's agreement and a Q2 limit of 60 °C. This measures Q2's on-resistance at the gate drive the circuit really gives it.

**5. Optional, user-gated, not reversible: real-cell hot-plug.** On a board the user agrees to sacrifice (not #0003): scope BAT_RAW, VBAT and VSYS while a charged 18650 goes into BT1, SW1 OFF, no USB. Then: does the board run on battery, and if not, does it come back after a USB plug-in (BATFET latch)? Only if steps 1–4 leave 3 open.

**What each result discriminates** (mechanism numbers as in the summary above):
| Result | Points to | Against |
|---|---|---|
| Holder accepts a reversed cell; VBAT or U5 BAT low Ω / abnormal diode; Q2 D–S short or open; C30 bulged | 1 reversed cell | 2, 5 as the first cause |
| Holder keyed; VBAT and U5 normal; Q2 discoloured, D–S short/open or G–S leaky | 2 Q2 overload (4 if the user recalls SW1 ON with the LED strip on) | 1 |
| Bridge or burn at BT1 + pad / J7 rear legs; continuity BAT_RAW ↔ J7 shell or ↔ USB_DN | 5 | — (can coexist with others) |
| Everything passive reads like the reference; board dead on battery (4b) but alive after VBUS (4a) | 3(a) BATFET latch, not damage | "cooked" for that board |
| U5 BAT/SYS abnormal with Q2 and holder normal; recollection says the source was > 6 V | 6 (wrong source) | 1, 2 |
| 4c: Q2 Vds well above 85 mΩ × I, temperature scaling to > 1 W at 3–4 A | 2 is live in the design, whatever cooked #0001/#0002 | 2 refuted if Vds < 0.2 V at 2 A and Q2 stays cool |
| #0004 4a: SW1 found OFF and +5V 5.1 V once ON | #0004's boost is fine (switch position) | U6 fault |
| #0004 4a: SW1 ON, BOOST_EN < 1.2 V | SW1 contact or joint | U6 fault |
| #0004 4a: BOOST_EN high, U6 VCC ≈ 0 | U6 not alive (joint or die) | — |
| #0004 4a: BOOST_EN high, VCC up, FB > 1.204 V, +5V < VSYS | FB divider (R39/R40) | — |
| #0004 4a: +5V > VSYS but < 5 V | U6 switches but is input-starved or current-limited (BQ 100 mA default) | a–d |

Results come back as cards. The initiative's Phase 7 waits on a user gate (W1) that cites those card IDs. If the results change what v8 needs beyond the power path, the Debugger → Planner row applies.

## Open questions
- Which holder is fitted on each board (1042 or 1042P), and does the plain 1042 accept a cell either way? (Phase 1 left this open; distributor listings call 1042P the polarised one.)
- Whether #0005 is legacy B2 or B3 doesn't matter for its use as the power reference, but its BQ I²C is absent, so no BQ register reads on it. An optional BQ register readback (REG00 / REG08 to confirm the 100 mA SDP default) needs a board whose BQ answers on I²C; #0003 is the only one known, so only if the user wants it.
- U6's behaviour when disabled (VIN → VOUT through the high-side body diode) is argued from the topology, not read from the TPS61088 datasheet (SLVSCM7). Step 4a with SW1 OFF on the reference settles it by measurement.

# Session Log — v8-debug-board

## 2026-11-02 — orchestration run 1

Entry conditions: started from `RELAY-orchestrator.md`. `lab-multi-investigation` is merged (PR #89, `36ab0ad`). Branch `feat/v8-debug-board` was cut from `main` at `5acec69`. PLAN Open Questions OQ-1 to OQ-5 are still open, and each is assigned to a later phase (OQ-2/4/5 to Phase 3, OQ-3 to Phase 13, OQ-1 to Phase 16), so none gates Phase 1. Gate rule from the relay: Phases 1–6 run without a user gate except W2 (end of Phases 3–4). Phase 7 stops on W1 if the bench findings haven't landed.

---

### Worker #1 — Phase 1: Power path — v7 trace and BQ root cause (desk)

**Dispatch:** standard spawn prompt, plus:
- Additional reading: `tools/CONTEXT.md` (Critical Rule, Source-Hash Rule); PLAN Technical Notes "Sources to load per task" (the subset relevant to the power path: CL-IDs in `docs/research/v7-retry/v6-v7-changelist.md`, `docs/references/{bq24195,tps61088}/DATASHEET_REFERENCE.md`, `hardware/CONTEXT.md`, `firmware/src/main.cpp` `configureBQ24195()`).
- Scratch extraction output stays outside the repo. `lab/` is read-only.

#### Notes

**Task 1: v7 power-path trace (`c2acffc`).** I re-extracted with `tools/schematic-context/extract.py` from a `git archive c2acffc hardware/pcb-main/kicad` copy into the session scratchpad, both with and without `--previous`. Both outputs equal the committed `hardware/pcb-main/kicad/circuit-context.json` key for key, except `source.extracted_at`. `source_hash` is `455cad3e5704` in all three, and the four `.kicad_sch` files are unchanged between `c2acffc` and HEAD. 93 components, 53 nets. The committed copy has no `_provenance` (tools/CONTEXT.md Source-Hash Rule: freshness judged from git; it is fresh).

Components on battery → charger → boost → LDO (pin:name → net; `PM/` = `/Power Management/`):

| Ref | Part (LCSC) | Pins |
|---|---|---|
| BT1 | Keystone 1042 18650 holder (no LCSC; bottom side, CL-10) | 1:+ → BAT_RAW, 2:− → GND |
| C30 | 47 µF 10 V elec (schematic C7469958; as built C72522 47 µF 35 V, CL-14) | 1 → BAT_RAW, 2 → GND |
| Q2 | `Q_PMOS_GSD`, SOT-23, C15127 (AO3401A) | 1:G → PMOS_GATE, 2:S → BAT_RAW, 3:D → VBAT (CL-09) |
| R33 | 100 k | VBAT – PMOS_GATE |
| R34 | 100 k | PMOS_GATE – GND (v6: PMOS_GATE – BAT_RAW, CL-09) |
| U5 | BQ24195RGER C90862 | 1,24:VBUS → Protected_VBUS; 2:D+ → GND; 3:D− → GND; 4:STAT not in netlist (unconnected); 5:SCL → /I2C_SCL; 6:SDA → /I2C_SDA; 7:INT → /CHRG_INT; 8:OTG → OTG_BIAS; 9:CE → GND; 10:ILIM → BQ_ILIM; 11:TS1, 12:TS2 → BQ_TS; 13,14:BAT → VBAT; 15,16:SYS → VSYS; 17,18:PGND, 25:EP → GND; 19,20:SW → BQ_SW; 21:BTST → BQ_BTST; 22:REGN → BQ_REGN; 23:PMID → BQ_PMID |
| R32 | 330 Ω | BQ_ILIM – GND (ILIM) |
| R35 | 10 k | OTG_BIAS – +3.3V (OTG is pulled to a rail that is downstream of U5) |
| R36 / R37 / TH1 | 5.6 k / 30 k / 10 k NTC 0603 (on PCB, not on the cell) | REGN – TS; TS – GND; TS – GND |
| C24 | 4.7 µF | REGN |
| C25, C26 | 10 µF ×2 | PMID (20 µF total; datasheet reference asks ≥ 60 µF for bq24195, 20 µF for L) |
| C23, L1 | 47 nF; 2.2 µH C266426 | BTST–SW; SW → VSYS |
| C27, C28, C29 | 10 µF ×2, 220 µF 10 V | VSYS |
| J7 → F2 → C20/C21/C22, U9.5, TP3 | USB-C, 3 A fuse | VBUS_RAW → Protected_VBUS |
| R44 | 10 mΩ 2512 | VSYS – VSYS_SENSE (INA219 U7 shunt: IN+ VSYS, IN− VSYS_SENSE) |
| C31, C41 | 0.1 µF, 10 µF | VSYS_SENSE |
| SW1 | MSK-12C02 SPDT C431540 | A → VSYS_SENSE, B (common) → BOOST_EN, C → GND (CL-11) |
| R2 | 100 k | BOOST_EN – GND |
| U6 | TPS61088RHLR C87357 | 1:VCC → BOOST_VCC; 2:EN → BOOST_EN; 3:FSW → BOOST_FSW; 4–7:SW → BOOST_SW; 8:BOOT → BOOST_BOOT; 9:VIN → VSYS_SENSE; 10:SS → BOOST_SS; 11,12:NC → GND; 13:MODE not in netlist (floating = PFM); 14–16:VOUT → +5V; 17:FB; 18:COMP; 19:ILIM; 20:AGND, 21:PGND → GND |
| L2 | 2.2 µH 10 A C167218 | BOOST_SW – VSYS_SENSE |
| R39/R40, R41, R42, R43/C38/C39, C37, C32, C33 | FB 180 k/56 k, FSW 100 k, ILIM 100 k, comp, SS 47 nF, BOOT 0.1 µF, VCC 2.2 µF | boost support |
| C34, C35, C36, C42 | 22 µF 0805 (schematic C109314; as built C45783 25 V, CL-14) | +5V |
| U8 | AMS1117-3.3 C6186 | 3:VIN → +5V; 2,4:VOUT → +3.3V; 1:GND |
| C40, C43 | 0.1 µF; 22 µF tant | +3.3V |
| TP1 / TP2 / TP3 / TP4 | test pads | VSYS / VBAT / Protected_VBUS / GND |

Net membership:
- BAT_RAW: BT1.1, C30.1, Q2.2(S). VBAT: Q2.3(D), R33.1, TP2, U5.13/14. PMOS_GATE: Q2.1, R33.2, R34.1.
- BQ_PMID: U5.23, C25, C26. VSYS: U5.15/16, L1.2, C27–C29, R44.1, U7.1, TP1. VSYS_SENSE: R44.2, L2.2, U6.9, SW1.1(A), U7.2, C31, C41.
- BOOST_EN: SW1.2(B), R2, U6.2. BQ_TS: U5.11/12, R36, R37, TH1. BQ_ILIM: U5.10, R32. OTG_BIAS: U5.8, R35. /CHRG_INT: U5.7, R38 (10 k to +3.3V), U3.23 (IO21), TPIO21.
- +5V (11): U6.14–16, C34–36, C42, R39, U8.3, F1, D5.2 (VDD). +3.3V (25): U8.2/4 plus U3, U4, U7 and the sensor connectors J4–J6.
- D+/D−: U5.2 and U5.3 are on GND. The USB pair (/USB_DP, /USB_DN) runs J7 → U9 → U3 and does not touch U5.

CL references: CL-09 (Q2 symbol GSD, R34 to GND, `fae477e`), CL-11 (SW1 on BOOST_EN, R2 pull-down), CL-14 (C22/C30/C34–36/C42 as built differ from the schematic BOM).

**Task 2: Q2 and BT1 pin mapping.** I read the pads with a read-only kiutils probe (session scratchpad `probe_q2_bt1.py`) on `git archive c2acffc` `motion-play-main.kicad_pcb`. It printed pad number, position, net and the footprint's silk/fab text. No KiCad text was read into context.
- **Q2 symbol → footprint → part.** The symbol is `Q_PMOS_GSD` (pin 1 G, 2 S, 3 D, per the extracted pin names). The footprint is `Package_TO_SOT_SMD:SOT-23` on F.Cu at (88.908, 125.612), rotated 90°. Pad 1 (−0.94, −0.95) → PMOS_GATE, pad 2 (−0.94, +0.95) → BAT_RAW, pad 3 (+0.94, 0), alone on its side → VBAT. The part is C15127, AO3401A (AOS datasheet Rev 3.1, Dec 2023; LCSC's page for C15127 calls the pinout G-S-D). The datasheet's SOT-23 drawing has D alone on one side and G and S on the other. So pad 3 = D is confirmed. Pin 1 = G and pin 2 = S follow AOS's SOT-23 convention and LCSC's G-S-D, but the G/S left-right order is only in the page-1 drawing, which I couldn't render (no poppler). **Mapping: consistent. The G/S order needs one visual check of the AO3401A page 1 drawing.** CL-09's fix of the v6 SPICE symbol holds at symbol/pad level.
- **Q2's orientation, a finding for Phase 2.** With S on BAT_RAW and D on VBAT, the body diode (anode D, cathode S) points from VBAT to BAT_RAW. That is load-switch orientation. Classic reverse-polarity protection is the other way round: D at the cell, S at the load, so the body diode points from the cell to the load. Argued consequences: (1) **The circuit does not block a reversed cell.** With BAT_RAW at −Vcell, the gate sits at about VBAT/2 and Vgs > 0, so Q2 is off. But the body diode is forward-biased from VBAT to BAT_RAW, which pulls VBAT about 0.7 V above −Vcell, far beyond BQ BAT abs-min −0.3 V (bq24195 reference, Absolute Maximum Ratings). Current then flows through U5's BAT-pin internal diodes from GND. (2) **Gate drive is marginal when the cell is the right way round.** Once Q2 is on, R33/R34 set the gate to VBAT/2, so Vgs ≈ −Vcell/2: −1.5 V at 3.0 V and −2.1 V at 4.2 V. AO3401A Vgs(th) is −0.5 / −0.9 / −1.3 V, and Rds(on) is only specified down to −2.5 V (≤ 85 mΩ). The BQ's default ICHG is 2048 mA (bq24195 reference, REG02), and firmware leaves it alone. So Q2 carries up to 2 A with Rds(on) unspecified. Both points go to Phase 2's mechanism ranking; neither is ranked here. The archived `integrated-power` COMPONENT_SELECTION lists Q2's role as "Battery reverse polarity protection", which the v7 topology doesn't provide.
- **BT1 polarity.** The footprint is `Battery:BatteryHolder_Keystone_1042_1x18650` on B.Cu at (119.63, 128.6). Pad 1 (−39.69, 0) → BAT_RAW and pad 2 (+39.69, 0) → GND. Both "+" markings sit at the pad 1 end: B.SilkS "+" at (−40, 5) and B.Fab "+" at (−35, 0.15). There is one NPTH locating hole at (−36.13, 8), also at the pad 1 end. **The footprint is internally consistent: + marking = pad 1 = BAT_RAW = Q2 source.** Open: (a) Distributor listings (element14, Novapart) list **1042P** as the "polarized" SMT variant and 1042 as plain leaf springs, so the plain 1042 the footprint names may accept a cell either way round. The Keystone drawing (M65p27.pdf) text doesn't settle this. (b) BT1 has no LCSC number (hand-fit), so which holder is actually on #0001/#0002/#0004 is a bench question. (c) Whether the holder body covers the bottom-silk "+" is also unknown. Phase 2 and the relay should carry (a)–(c).

**Task 3: BQ "needs an I²C command", root cause.** Sources: `docs/references/bq24195/DATASHEET_REFERENCE.md`, checked against the full TI datasheet SLUSB97A (Dec 2014; text extracted in the session scratchpad). The reference doesn't cover the HIZ rule, the D± thresholds or the start-up order, so those are cited to SLUSB97A sections.
- **Mechanism (datasheet).** The BQ sets its input current limit (IINLIM) by BC1.2 detection each time a source is plugged in (§8.3.1.3.3–8.3.1.3.4). It runs DCD first, then primary detection; Table 2 lists the outcomes. D+ and D− tied to GND read as a USB host (SDP): D+ is already below VD+_LOW 0.7 V, so DCD passes, and D− is low in primary detection. For an SDP, the OTG pin picks 100 mA (OTG low) or 500 mA (OTG high). The IINLIM that results applies until a host writes REG00[2:0] (§8.3.1.3.3). The ILIM pin is only a ceiling: "The actual input current limit is the lower value between ILIM setting and register setting" (§8.3.5.1). With R32 = 330 Ω, KILIM 435/485/530 gives 1.32/1.47/1.61 A, so ILIM never sets the limit at power-up.
- **Why OTG is low (argued from the schematic and the datasheet's start-up order).** OTG is pulled up by R35 10 k to +3.3V. +3.3V comes from U8, which runs from +5V (U6), which runs from VSYS, which comes from the BQ's own buck. Detection runs before "Converter Power-Up" (§8.3.1.4: "After the input current limit is set, the converter is enabled"), and IIN_START = 100 mA while VSYS < 2.2 V. So on USB power alone, OTG is low at detection and **IINLIM = 100 mA** (REG00 = 0x30). That is 0.5 W at 5 V, which can't carry U3, the boost/LDO losses or the LEDs, so the board browns out and boot-loops. The `main.cpp` comment says the default is "~500 mA". Per Table 2 it is 100 mA unless OTG is high.
- **With a good battery (datasheet §8.3.1.3.5, §8.4.1.1).** If detection gives a 100 mA SDP and VBAT > VBATGD (3.55 V), the BQ enters HIZ. VBUS is then ignored, it doesn't charge, and the cell carries the system. In default mode it leaves HIZ only when the source is removed. OTG is high at plug-in only if +3.3V is already up, i.e. battery fitted and SW1 on. Otherwise USB won't charge a good cell. Also, in default mode a 100 mA SDP source gets a 45-min charging timer, then the converter stops and the BQ goes to HIZ (§8.4.1.2, tSDP_DEFAULT).
- **Why the firmware fix needs two writes (§8.4.1).** Any I²C write puts the BQ in host mode, where the watchdog (default 40 s, REG05[5:4]) must be reset or disabled. When it expires, the BQ resets its registers (Fig. 22). REG00's reset value has IINLIM = 000 (100 mA), and the datasheet doesn't say whether a watchdog reset re-applies the detection result. So `configureBQ24195()` writes REG00 = 0x36 (IINLIM 2 A, which R32 caps at about 1.47 A) and REG05 = 0x8A (watchdog off). Its comment and log line say "2 A". The effective limit is the ILIM ceiling, 1.32–1.61 A.
- **Ruled out.** EN_HIZ (REG00[7]) resets to 0, so it isn't the cause; HIZ comes from the 100 mA-SDP rule above. VINDPM resets to 4.36 V, which gives margin on a 5 V source, but under load it is a sag limit, not the cause. CE is on GND (charge enabled). TS: R36 5.6 k / (R37 30 k ∥ TH1 10 k) = 57 % of REGN at 25 °C, inside the 73 % cold / 47.7 % hot window, so it isn't the cause. TH1 is on the PCB, so it senses board temperature, not the cell.
- **Root cause.** D+ and D− are tied to GND, and OTG is pulled to a rail that only exists after the BQ starts. Together they make every USB plug-in a 100 mA SDP: brownout with no battery, HIZ with a good battery. ILIM can't raise a limit, only lower it. The firmware workaround then has to disable the watchdog to keep its write.
- **Hardware fix options (each needs a Phase 7 decision; stock not checked here):**
  1. *Keep BQ24195; short D+ to D− instead of tying them to GND.* Argued from Table 2 and the thresholds: in DCD, ID+_SRC 7–14 µA into RD−_DWN 14.25–24.8 k gives 0.10–0.35 V, below 0.7 V, so contact is detected. In primary detection, VD+_SRC 0.5–0.7 V appears on D−, above VD−_LOW 0.25–0.40 V, so D− is high: charging port, IINLIM 1.5 A (101), no HIZ, no 45-min timer. No I²C needed, and R32 sets the real ceiling. *Trade-offs:* the limit is capped at 1.5 A (IADPT_DPM 1.35–1.65 A) unless a host writes more. Every source looks like a charger, so a PC port gets asked for up to 1.5 A, against USB 2.0's 500 mA. That is fine on the bench with a wall adapter or powered hub, but a PC port may trip. One 2- or 3-way solder jumper gives the v7 position (GND) and the v8 position (shorted). Costs nothing in parts.
  2. *Keep BQ24195; pull OTG up from a rail that exists at detection* (REGN through a resistor; OTG abs-max 7 V; REGN ≈ 4.8 V from 5 V VBUS). *Trade-offs:* only gets SDP 500 mA, which also avoids the HIZ rule, but 500 mA is likely too little for WiFi peaks plus LEDs. The boost only enables when CHG_CONFIG = 10 is also set, which takes I²C, so OTG high is safe in default mode. Partial fix, and it can sit beside option 1.
  3. *Keep BQ24195; wire D+/D− to the real USB pair.* *Trade-offs:* you get the true source class (PC 100/500 mA, wall charger 1.5 A). But the BQ drives 0.6 V and current sinks onto the same pair as U3's native USB during enumeration, adds load to the pair, and still gives 100 mA from a PC with OTG low. Not recommended.
  4. *Swap to a part that needs no I²C to run at the target current.* Phase 7 candidates, to check against datasheets and stock (none verified here): standalone NVDC buck chargers with a resistor-set input limit (e.g. TI BQ25616 class), or a linear power-path charger (BQ24074/5 class, ≤ 1.5 A input, more heat). *Trade-offs:* a new footprint and support network, losing I²C telemetry/control (STAT/PG pins instead), and different boost/OTG behaviour. It may get away from the chronic C90862 stock problem (hardware/CONTEXT.md). Some standalone chargers also run D+/D− detection, so the same pin trap has to be checked for each one.
  Options 1–3 keep U5 on the I²C bus (jumper (f) still applies). Firmware can keep `configureBQ24195()` as an optional raise above 1.5 A, but boot no longer depends on it.

**Task 4.** Created `hardware/pcb-main-v8/CONTEXT.md` with all eight sections. Purpose and "Inherited v7 faults → BQ24195" are filled; the BQ section is the durable version of Task 3. The others say which phase fills them. There is also an empty "Battery connection damaged boards" subsection for Phase 2.

**Handoff, for Phase 2:**
- Carry these into the mechanism ranking (Task 2 above). **Q2 is in load-switch orientation** (S on BAT_RAW, D on VBAT). Its body diode does not block a reversed cell, which would drive VBAT/U5 BAT to about −Vcell + 0.7 V (abs-min −0.3 V). Also, **R33/R34 give only about −Vcell/2 of gate drive**, below the −2.5 V where AO3401A Rds(on) is specified, while carrying up to 2048 mA default ICHG.
- The plain Keystone 1042 may be unpolarized (1042P is the "polarized" variant per distributor listings). BT1 is hand-fit with no LCSC number, so which holder is on each board is a bench question for the relay.
- AO3401A G/S pin order: one visual check of datasheet page 1 is still open. D = pin 3 is confirmed.
- The relay could add one cheap discriminator on the BQ path: REG08[7:6] / REG00 readback on a v7 board with the firmware write disabled, to confirm SDP / 100 mA. This is optional.

**Not actioned, for the Orchestrator** (refinements to existing docs, so GARDEN-type, not initiative Deferred):
- `docs/references/bq24195/DATASHEET_REFERENCE.md` says "Minimum ILIM current: 500 mA" and that 2.7 kΩ clamps at 500 mA. SLUSB97A §8.3.5.1 doesn't support that. The reference also omits the 100 mA-SDP → HIZ rule (§8.3.1.3.5) and the 45-min SDP timer.
- `firmware/src/main.cpp`: the comment above the BQ defines says the default is "~500 mA". It is 100 mA with OTG low. The "IINLIM=2A" log line is capped by R32 at about 1.47 A. Phase 12 touches this function anyway.

PLAN Approach and Technical Notes still describe the work, and no approach changed. Commits: `6a5d793` (task 1), `3ca8380` (task 2), `0e37837` (task 3), `cff9d35` (task 4), plus this handoff.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 1 | Phase 1: Power path — v7 trace and BQ root cause | DONE | No — clean completion | 37627b5 | 4 tasks + handoff; commits 6a5d793, 3ca8380, 0e37837, cff9d35, 37627b5 |

#### Verification
- TASKS.md Phase 1: all five items `[x]`. Working tree clean. PLAN.md unchanged; no date-stamped headings.
- `hardware/pcb-main-v8/CONTEXT.md` exists with the eight sections Task 4 named. Only Purpose and Inherited v7 faults → BQ are filled; the battery subsection is a Phase 2 placeholder. The BQ root cause cites SLUSB97A section numbers, and the four fix options each carry trade-offs, as the task asked.
- Nothing outside the plan was done: `.kicad_*` files were only read through kiutils/extract.py in scratch, and nothing under `lab/` was touched.
- Carried forward to Phase 2: the Q2 orientation and gate-drive findings, the BT1 1042 vs 1042P polarisation question, and the open AO3401A G/S visual check (Handoff notes above).
- Two doc corrections the Worker flagged (`docs/references/bq24195/DATASHEET_REFERENCE.md` ILIM "500 mA" minimum; `firmware/src/main.cpp` "~500 mA" comment) are GARDEN-type. Raised with the user, not actioned by this initiative. Phase 12 touches the `main.cpp` comment anyway.

---

### Worker #2 — Phase 2: Power path — battery failure mechanisms and bench relay (desk)

**Dispatch:** standard spawn prompt, plus:
- Additional reading: SESSION.md Worker #1 `#### Notes` (the Phase 1 trace, Q2/BT1 findings, Handoff items); `hardware/pcb-main-v8/CONTEXT.md`; card V7R-020 and `lab/BENCH.md` (read-only); `.context/PROTOCOL.md` Relays (template, Initiative → Debugger row); TASKS Deferred `[from: lab-multi-investigation]` note (PWR prefix, scaffold command).
- `lab-multi-investigation` merged at `36ab0ad` (PR #89); state that in the relay.

#### Notes

**Task 1: battery-damage mechanisms, ranked.** Sources: the Phase 1 trace above (`circuit-context.json` @ `c2acffc`); `docs/references/{bq24195,tps61088,ina219}/DATASHEET_REFERENCE.md`; TI SLUSB97A (full text, session scratchpad) for BATFET behaviour; AOS AO3401A Rev 3.1 (text, session scratchpad); a read-only kiutils probe and a kicad-cli B.Mask gerber export of `c2acffc` `motion-play-main.kicad_pcb` in the session scratchpad (`probe_bt1_area.py`, `probe_bt1_edge.py`); `docs/debugging/v7-i2c-investigation.md` Phase 18. Everything below is **argued** unless it cites a measurement.

What we know about the events (NOTEBOOK 2026-10-27, user recollection): "adding the battery" cooked #0001 and #0002 in original testing; not done methodically; "I remember it being clear that they were 'cooked'"; details not recorded. Unknown: which battery (an 18650 in BT1, or a pack on leads), cell orientation, whether USB, SW1 ON or the LED strip were connected, what failed afterwards.

One measured anchor: in legacy Phase 18 (2026-04-26) a v7 board ran from a bench PSU at 3.7 V, 500 mA limit, on BAT_RAW with VBUS absent, and was not damaged. So "any forward-polarity source on BAT_RAW cooks a v7" is refuted for a soft, current-limited source. It also shows Q2's channel conducts BAT_RAW → VBAT (its body diode points the other way, so the board could not have booted through it). That settles Worker #1's open AO3401A G/S question functionally for that board (argued: same design and BOM on all five).

Ranking (most to least likely to cook a board at or soon after connection):

| # | Mechanism | Datasheet values | Confirms | Refutes | Test reversible? |
|---|---|---|---|---|---|
| 1 | **Cell inserted reversed in BT1.** Q2 is in load-switch orientation (S on BAT_RAW, D on VBAT), so its body diode is forward-biased from VBAT to BAT_RAW when BAT_RAW is negative. Q2 itself is off (gate ≈ VBAT/2, Vgs > 0). VBAT is pulled to about −Vcell + VSD = −2.0 to −3.5 V, and current flows from GND through U5's BAT-pin substrate/ESD structure, Q2's body diode and the cell, limited only by the cell, contacts and diodes. C30 (polarised electrolytic) sits reversed at −Vcell | BQ BAT abs-min −0.3 V; AO3401A VSD −0.7 typ / −1.0 max at −1 A, body-diode IS −2 A continuous max; aluminium electrolytic: no reverse rating (argued, typical ≤ 1 V) | The holder accepts a cell either way (plain 1042 leaf springs; 1042P is the polarised variant, Phase 1); VBAT (TP2)–GND low Ω or U5 BAT diode reading unlike the reference board; Q2 D–S short or open; C30 bulged or vented; scorch at U5 / Q2 | Holder physically keyed **and** VBAT, U5 BAT, Q2 and C30 read as the reference | Yes: visual, ohms, diode mode, holder inspection (no cell) |
| 2 | **Overload on battery: Q2 under-driven.** R33/R34 hold the gate at VBAT/2, so Vgs = −(Vcell + Vds)/2 ≈ −1.5 to −2.1 V, below the −2.5 V where Rds(on) is specified. On battery the only overcurrent limits are the BQ's BATFET OCP (9 A) and the boost's cycle-by-cycle ILIM (10.6–13 A peak, R42 100 k). No fuse on the battery path (F2 is on VBUS; F1 3 A only feeds the LED strip). The 72-LED strip behind F1 can draw up to 15 W at +5 V, ≈ 4.5 A from a 3.7 V cell (argued, 90 % boost). At an extrapolated 0.1–0.2 Ω (argued; no curve below −2.5 V) that is 2–4 W in a SOT-23. The default ICHG 2048 mA (REG02) also runs through Q2 when charging: ≈ 0.4–0.8 W for the whole charge | AO3401A Vgs(th) −0.5/−0.9/−1.3 V; Rds(on) ≤ 85 mΩ at −2.5 V/−2.5 A; ID −4.0 A (25 °C) / −3.2 A (70 °C) at Vgs −10 V; PD 1.4 W (≤ 10 s, 25 °C), 0.9 W (70 °C); RθJA 125 °C/W max steady state on 1 in² 2 oz; BQ IBATFET_OCP 9 A (SLUSB97A EC table) | Q2 discoloured or cracked; Q2 D–S short/open, G–S leaky; on a reference board, Q2 Vds at a set battery-side current (from a current-limited PSU) gives Rds well above 85 mΩ and a temperature rise that scales to > 1 W at 3–4 A | Q2 intact on #0001/#0002; measured Vds small (< 0.2 V at 2 A) and Q2 stays cool | Yes, if the PSU current limit stays ≤ 1 A (step to 2 A only with the user, Q2 ≤ 60 °C) |
| 3 | **Hot-plug inrush and ringing on BAT.** At contact VBAT = 0, so the gate is at 0 and Q2 is fully on (Vgs = −Vcell) for the edge. The cell then charges C30 47 µF, SYS (C27/C28 2 × 10 µF + C29 220 µF through the BATFET), VSYS_SENSE (C31, C41 via R44) and, through L2 and U6's high-side body diode (argued: no load disconnect in a synchronous boost; check SLVSCM7), +5V (C34–36, C42 4 × 22 µF) and U8's output. **VBAT has no capacitor** (BQ asks for 10 µF at BAT). Two outcomes: (a) peak current above 9 A trips BATFET OCP, which **latches off until VBUS is plugged in** (§8.3.5.5.3): the board looks dead on battery but isn't damaged; (b) LC ringing on the ceramic-only nodes overshoots BAT/SYS past 6 V (needs ≈ 1.43 × 4.2 V; C29/C30 electrolytic ESR damps it, so argued unlikely) | BQ BAT, SYS abs-max 6 V; RON_BATFET 12/20 mΩ; IBATFET_OCP 9 A; TPS61088 VIN abs-max 14.5 V | (a) a board dead on battery that recovers after a USB plug-in; (b) scope on BAT_RAW / VBAT / VSYS at a real-cell plug-in shows > 6 V; U5 BAT/SYS diode reading abnormal | (a) no latch seen; (b) overshoot < 5 V on the scope | (a) yes; (b) **no**: plugging a real cell into a board risks the board. Only on a sacrificial board, user-gated |
| 4 | **Boost enabled into a load at plug-in.** With SW1 ON, U6 starts once VIN > 2.7 V with an 11.3 ms soft-start (SS 47 nF). +5V is already precharged to ≈ Vcell − Vf through the body diode with no control. Into a normal load this is benign. Into a heavy or shorted +5V load (LED strip, a +5V fault) U6 pulls up to its ILIM from the cell through Q2, which is mechanism 2 at its worst | TPS61088 ILIM 10.6/11.9/13.0 A (PFM, R42 100 k); UVLO 2.7 V rising; tSS ≈ 11.3 ms; EN, VCC abs-max 7 V; thermal shutdown 150 °C | User recalls SW1 ON and the LED strip attached; +5V–GND low Ω or U6 SW/VOUT diode readings unlike the reference | +5V shows the same MΩ drift as #0003/#0004/#0005 (V7R-020) and U6 pins read as the reference | Yes (passive); powered on a current-limited PSU with SW1 OFF then ON |
| 5 | **BT1 body over B.Cu copper (CL-10, CL-20).** BT1 is hand-fit (no LCSC). Its + pad (pad 1, BAT_RAW, 7.5 × 6.5 mm, B.Cu) is **0.78 mm edge-to-edge from J7's two rear shell legs** (THT, mask open, net unassigned, protruding on B side) and 0.38 mm from a **USB_DN via** (tented: the B.Mask gerber has no via openings). Under the body: B.Cu runs of USB_DP/DN, SDA/SCL, CHRG_INT, LED_DATA, TCA_RESET, VBAT, BAT_RAW, and 79 GND, 9 +3.3V and 6 +5V vias (all tented). A solder bridge or the contact tab reaching a J7 leg puts BAT_RAW on the USB shell (a dead short of the cell through the cable shield and GND whenever a USB cable is attached). A bridge to the USB_DN via (needs mask damage from the iron) puts up to 4.2 V on U3's D− and, through U9's clamp, onto Protected_VBUS | ESP32-S3 GPIO abs-max VDD + 0.3 V (argued, check the S3 datasheet); USBLC6 clamp to VBUS (U9.5 on Protected_VBUS) | Solder on or near J7's rear legs at the BT1 + end, scratched mask by the USB_DN via, continuity BAT_RAW ↔ J7 shell or BAT_RAW ↔ USB_DN (U9.3/4) on #0001/#0002 | No bridge, mask intact, no continuity | Yes: loupe and ohms, no cell |
| 6 | **Abs-max on BAT_RAW / VBAT / VSYS members, DC, forward polarity.** A single Li-ion cell is ≤ 4.2 V (4.35 V for HV cells). Every member is rated above it: BQ BAT/SYS 6 V; TPS61088 VIN 14.5 V, EN 7 V; INA219 IN± common mode 26 V; AO3401A VDS −30 V, VGS ±12 V (gate sees at most −Vcell); C29 220 µF 10 V; C30 10 V (schematic) / 35 V (as built, CL-14). **Refuted on the desk for one cell.** Live only if the "battery" was not one Li-ion cell (e.g. a 2S pack at 8.4 V exceeds BQ BAT/SYS 6 V) | as listed | The source was > 6 V (user recollection; measure any pack used); U5 BAT/SYS abnormal | One cell used | Yes |
| 7 | **TS network.** TS is biased from REGN, which exists only with VBUS; TH1 is on the PCB, not on the cell; the cell never touches TS. At 25 °C TS = 57 % of REGN (window 73 % cold / 47.7 % hot, Phase 1). It can stop charging but cannot cook a board. Side finding for v8: there is no cell-temperature sensing while charging at 2048 mA default | TS abs-max 7 V; REGN ≈ 4.8 V at 5 V VBUS | — (cannot cook) | TS/REGN ≈ 0.57 on USB power | Yes |

Notes on the ranking:
- 1 and 5 need a specific event (a reversed cell, a bridge). 2 needs only normal use on battery with a load. Which of them happened depends on facts only the boards and the user hold, so the relay asks the user's recollection first, and orders the bench to separate 1 / 2 / 5 with passive measurements before anything powered.
- 3(a) is a "false cooked": a board that seems dead on battery after a hot-plug, but is fine once USB is plugged in. Worth ruling out before calling #0001/#0002 damaged.
- Design deviations found on the way (for Phase 7, not ranked as causes): no 10 µF on VBAT (BQ pin table); PMID 20 µF vs the ≥ 60 µF the bq24195 asks for (Phase 1); J7's shell legs have no net (floating shield).

**Task 2: #0004 and #0005 against the same path.** Measurements are from V7R-020 (raw block and Extras); everything else is **argued**.

*#0004* (measured: USB-C to the Mac, no battery, nothing in J3–J6; PWR LED on; no USB device in normal or download mode; nothing warm; "pristine" both sides; +5V ≈ 3.75 V moving in the 3.7x range; +3.3V 2.680–2.701 V; unpowered +3.3V–GND 304.9 Ω, the same as #0003 306.1 Ω and #0005 304.4 Ω; +5V–GND a falling MΩ drift like the other two).
- No rail is shorted (the unpowered readings match the two boards that run). So #0004's problem is a stage that isn't running, not a load that drags a rail down.
- +3.3V ≈ +5V − 1.06 V: U8 (AMS1117) in dropout. U3 at 2.69 V is below its 3.0 V minimum, which accounts for no USB device in either mode; PWR LED (D1 via R1 1 k from +3.3V) still lights.
- +5V at 3.75 V is neither 5.1 V (U6 regulating, as #0003 5.096–5.098 V) nor 0 V. #0005, with the same design on USB and no battery, reported VSYS 4.30 V (INA219, old image). If #0004's VSYS is also ≈ 4.3 V, then +5V = VSYS − ≈ 0.55 V, which is VIN passing through L2 and U6's high-side body diode with U6 **not switching** (argued: synchronous boost without load disconnect). That fits every reading.
- Why U6 isn't switching, candidates in order of cost to check: (a) **SW1 is OFF** (BOOST_EN held low by R2). SW1's position on #0004 was not recorded in V7R-020; (b) SW1 contact or joint fault, BOOST_EN < 1.2 V with SW1 ON; (c) U6 not alive (VCC pin ≈ 0 with EN high: joint or die fault); (d) FB divider fault (R39/R40) holding FB above 1.204 V so U6 never switches; (e) input starved: the BQ's 100 mA default IINLIM (Phase 1) can't start the boost. (e) is argued against: #0005 boots on the same default limit and no extra load shows on #0004's rails.
- Discriminators (powered on USB): VSYS (TP1) vs +5V. +5V < VSYS − 0.3 V → U6 not switching (a–d); +5V > VSYS → U6 switches but doesn't regulate (input starved or current limit). Then BOOST_EN (SW1 B), U6 VCC (pin 1), FB (pin 17), and the SW node (scope, or DMM average ≈ VIN if idle).
- Battery relevance: none shown. #0004 has no known battery history (user named only #0001/#0002). It is a "boost doesn't run" case on the same path; if (c) U6 is dead, how it died is open.

*#0005* (measured: boots on USB; old image `motionplay-device-002` resets ~1 s apart after "Connecting to WiFi", `reset_reason=9`; scan finds 0x40 and 0x70 only, "BQ24195 not found at 0x6B"; VSYS 4.30 V; no battery; on u3-static it stays up, one banner).
- `reset_reason=9` is ESP_RST_BROWNOUT in ESP-IDF's `esp_reset_reason_t` (argued from the enum, not checked against this image's core version).
- The old image's `configureBQ24195()` write can't land with no BQ on the bus. So IINLIM stays at the BC1.2 default: SDP, OTG low at detection, **100 mA** (Phase 1 root cause). That is ≈ 0.5 W in: enough for the boot (and for u3-static, which never starts WiFi), not for WiFi TX peaks. With no battery there's no supplement, so the rails sag and U3 resets on brownout. This needs no damage at all, only the BQ missing from I²C.
- BQ missing from I²C, but VSYS = 4.30 V on USB means the BQ's buck is running. So the BQ's power stage is alive and only its I²C is absent: consistent with an open SDA/SCL/joint on U5 (legacy B2's "BQ I²C open", Phase 8) rather than a dead BQ. This fits the BENCH.md note that #0005 may be legacy B2 rather than B3.
- VSYS 4.30 V rather than VSYS_MIN + 150 mV (3.65 V): with charge enabled and no cell, the BQ charges the BAT node, which is only Q2's body diode into C30 47 µF and R33/R34. BAT sits near VREG 4.208 V and SYS follows it. The BQ datasheet asks for BATFET_DIS when no battery is fitted (§8.3.1.2.1); v7 can't do that without I²C.
- Battery relevance: none. #0005 is the Phase 1 BQ fault seen on a board whose BQ I²C is missing.

**Task 3.** Wrote `debugger/RELAY-power.md` (PROTOCOL template, role: debugger). It carries: a plain-words summary first; boards #0001, #0002 (user supplies), #0004, with #0005 as the power reference and #0003 untouched unless the user says so; steps 0 recollection → 1 visual → 2 per-rail ohms + two continuity checks (BAT_RAW ↔ J7 shell, BAT_RAW ↔ USB_DN) → 3 diode mode on Q2/U5/U6/U8 → 4 current-limited PSU per input (VBUS, battery-side PSU, Q2 under a set load) → 5 optional real-cell hot-plug (user-gated, not reversible); a result → mechanism table; the explicit "no change to the debug track's order unless the user says so"; PWR prefix and scaffold command.

**Task 4.** Filled `hardware/pcb-main-v8/CONTEXT.md` "Battery connection damaged boards…" with the ranked list (short form), #0004/#0005, a pointer to the relay, and the design deviations Phase 7 should fix whatever the bench finds.

**Task 5.** `lab-multi-investigation` is merged: `36ab0ad` (PR #89) is an ancestor of `main` and of this branch; `tools/lab/new_investigation.py` exists. The relay doesn't wait. Message for the user is in the return report (W1 opens).

**Handoff, for Phase 3 and Phase 7:**
- W1 is open: Phase 7 stops until the Debugger's `PWR` cards land and the user cites them.
- Phase 7 inputs, beyond the bench: the "Design deviations" list in the v8 CONTEXT battery section (blocking reverse protection, full gate drive, battery-side fuse, 10 µF on BAT, PMID ≥ 60 µF, + pad clearance, J7 shell net, cell-temperature sensing).
- Phase 3 (test points): VBAT, BAT_RAW, BOOST_EN, U6 VCC/FB and the Q2 pins were the hard-to-reach points in this relay; worth test points on v8.
- Open, argued only: TPS61088 VIN → VOUT body-diode path when disabled (not read from SLVSCM7; the relay's step 4a measures it); `reset_reason=9` = brownout read from the ESP-IDF enum, not checked against the old image's core.
- Not actioned, for the Orchestrator (GARDEN-type): `circuit-context.json` gives R2's `function` as "PMOS gate bias resistor to BAT_RAW (turns Q2 off if reverse…)", but R2 is the BOOST_EN pull-down (stale annotation from v6).

PLAN Approach and Technical Notes still describe the work; no approach changed, nothing rejected. Commits: `f21ce81` (task 1), `6bc68fd` (task 2), `5b25500` (task 3), `84058b4` (task 4), plus task 5 and this handoff.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 2 | Phase 2: Power path — battery failure mechanisms and bench relay | DONE | No — clean completion | 351383b | 5 tasks + handoff; commits f21ce81, 6bc68fd, 5b25500, 84058b4, bd3e2e3, 351383b |

#### Verification
- TASKS.md Phase 2: all six items `[x]`. Working tree clean. PLAN.md unchanged; no date-stamped headings. Nothing under `lab/` touched.
- `debugger/RELAY-power.md` follows the PROTOCOL relay template (role line, Context, Load, State, What was done, Your task, Open questions). It names #0001/#0002/#0004 as the suspect boards and #0005 as the reference, orders the sequence non-destructive first (the real-cell hot-plug is step 5, optional and user-gated), and carries the "no change to the debug track's order" line. #0003 is excluded unless the user says otherwise.
- `hardware/pcb-main-v8/CONTEXT.md` battery subsection filled (ranked mechanisms, relay pointer, design deviations for Phase 7).
- W1 is open. It closes when the Debugger's PWR cards land; Phase 7 checks for them.
- Worker #1's open AO3401A G/S question is answered in practice by the legacy Phase 18 run (argued from one board, per the Worker). Not re-verified here.
- GARDEN-type item raised with the user, not actioned: `hardware/pcb-main/kicad/circuit-context.json` annotation for R2 is stale v6 text ("PMOS gate bias to BAT_RAW"; R2 is the BOOST_EN pull-down).

---

### Worker #3 — Phase 3: Design intent — GPIO, jumpers, test points (desk)

**Dispatch:** standard spawn prompt, plus:
- Additional reading: SESSION.md Worker #1 and #2 `#### Notes`; `hardware/pcb-main-v8/CONTEXT.md`; PLAN Technical Notes jumper matrix and Open Questions OQ-2, OQ-4, OQ-5; `docs/research/v7-retry/v6-v7-changelist.md` §3; `lab/investigations/v7-i2c/STATE.md` §8, its NOTEBOOK (grep the dates) and card V7R-019 (read-only).
- The Worker can't talk to the user. For OQ-2/OQ-4 and W2 (part 1) it prepares the options and the approval summary, and returns them in its report; the Orchestrator puts them to the user.

#### Notes

**Task 1: debug-track inputs since the plan (read-only: card V7R-019 Conclusion, NOTEBOOK 2026-10-31 checkpoint + decision, 2026-11-01/02 V7R-020, 2026-11-02 decision @ 20/20, STATE §8 as of V7R-020; `git log --all -- lab/` and `lab/cards/` on main, this branch and `debug/v7-track-4`).**
- Landed, already in the plan's sources: V7R-019 Row 1 (SDA from GPIO16 → 109 mV, BQ + both VCNL 100 % ACK; GPIO43 → 896 mV, 0 %; one board, one rigid on J6, bodge wire; fix route (i) measured-supported on #0003 only). V7R-020 (#0005 GPIO43 533 Ω vs #0003 534 Ω: "not #0003 alone"; batch vs design not separated). Decision @ 20/20 (2026-11-02): continue the bench track + v8; design work assumes (c) v7-caused, not (b) batch, **argued (user prior), not tested**.
- Design reading of those entries (notebook 2026-11-02, Interpretation, argued): moving SDA off GPIO43 acts under (b) and the TX-role form of (c); connector protection on the channel SDA lines acts under the net-stress form of (c). So jumpers (a) and (b) are both needed, and neither is evidence about the mechanism.
- **Not landed:** card (j) (static dose at module castellation 37 vs board pad: joint vs inside the module), card (k) (V7R-019 extended: J4/J5, power cycles, dwell), and no `PWR` cards (no `lab/investigations/power/` yet; W1 still open). Highest card is V7R-020; STATE `open_cards: []`.
- **OQ-5 stays open.** Consequence for Phase 3: the GPIO allocation and jumper (a) are written so they don't depend on (j). If (j) says "joint", the v8 footprint/pad-37 land and solder-paste check matter (Phase 4/8 footprint review); if "inside the module", only the remap matters. Either way, jumper (a) keeps GPIO43 able to drive the bus (v7 position), so the v8 board can repeat (j)'s A/B/A without rework.

**Task 2: GPIO allocation.** Written to `hardware/pcb-main-v8/CONTEXT.md` § GPIO allocation, marked pending W2. Source for module facts: Espressif WROOM-1/1U datasheet v1.8 (downloaded, text extracted with PyMuPDF in the session scratchpad; not committed). Key choices: v8 bus pair SDA = GPIO16 (the pad V7R-019 measured), SCL = GPIO15 (adjacent pin 8); v7 pair 43/44 by jumper (a), one jumper per line; LED_DATA moves to GPIO18 (jumper g); UART0 (43/44) to a header in v8; DBG LEDs on GPIO47/48 (3.3 V on N16R8, note c); 15 spares to a header; straps 3/45/46 to bare test pads only; IO35–37 unconnected (PSRAM). Interlock to know: (a) SDA = v8 with (g) = v7 puts the LED_DATA loads on SDA, which is exactly V7R-019's fixture state (allowed, not a v7 or v8 state).

**Task 3: jumper matrix (left `[ ]`: OQ-2/OQ-4 answers await the user).** Written to CONTEXT § Jumper matrix, pending W2. Rows a–h from PLAN plus i (boost EN, CL-11; v6 = EN tied to VIN), j (BQ D+/D−, Phase 1 option 1), k (BQ OTG pull-up source, option 2); j and k are conditional on Phase 7 keeping the BQ24195. Rows where the default equals v7 because no fix is claimed: d (2.2 k upstream), f (BQ on bus), h (links closed), i (SW1). Row e is realised by the (a) SJ3s both open plus a header behind SJ2s. Rows considered and not added are listed in CONTEXT. OQ-2 recommended: option 1 (header only). OQ-4 recommended: A (≤ 100 × 100 mm, battery on a keyed cable connector). PLAN Open Questions not edited (answers pending).

**Task 4: test points, ground points, debug LEDs.** Written to CONTEXT § Test points, pending W2. 12 channel-side I²C points (TCA side and connector side, because row b's series R splits each line), 8 upstream (bus side, U3 pin side for both pairs, BQ side), the pull-up rail, every v7 rail plus the Phase 2 hard-to-reach nodes, MCU control pins, and three headers (UART0, external master, 2 × 15 spare GPIO). Ground rule: own GND pad per test point, ≤ 5 mm centre-to-centre as a working value until Phase 4 measures the spring (argued), pads sized for two springs. Seven LEDs: D1 kept (green, +3.3V_MCU), BUS green, +5V yellow, VBUS red, STAT orange (conditional), DBG1 blue / DBG2 white on GPIO47/48; D5 kept. Rail LEDs each behind a closed SJ2 for v7-load A/B.

**Task 5 (left `[ ]`: W2 part 1 awaits the user).** The GPIO allocation, Jumper matrix (with the OQ-2/OQ-4 option tables) and Test points sections of `hardware/pcb-main-v8/CONTEXT.md` are filled and each is headed "pending user approval". Nothing else in CONTEXT changed.

**For the Orchestrator to put to the user (W2 part 1 + OQ-2 + OQ-4):**
1. GPIO: bus moves to SDA = GPIO16 / SCL = GPIO15 by default (GPIO16 is the pad V7R-019 measured good); 43/44 become a UART0 boot-log header; LED_DATA moves to GPIO18; debug LEDs on GPIO47/48; 15 spares on a header; straps 3/45/46 as bare pads. Approve, or name a different default pair.
2. Jumpers a–k (CONTEXT table). Four rows default to the v7 value because no fix is claimed: d (2.2 k upstream), f (BQ on bus), h (current links closed), i (SW1 drives boost EN). Approve those defaults? Rows j and k only exist if Phase 7 keeps the BQ24195.
3. OQ-2: recommended option 1, external-master header only (no DevKitC footprint).
4. OQ-4: recommended A, ≤ 100 × 100 mm with the battery on a keyed cable connector (removes holder-over-copper and blocks a reversed cell at the connector).
5. Test points: every I²C net both sides of the TCA (with the protection split, 12 channel-side points), every rail, the Phase 2 hard-to-reach power nodes, own GND pad per point (≤ 5 mm working rule). Seven debug LEDs (colours in CONTEXT).
After the answers: record them in CONTEXT (drop "pending"), strike OQ-2/OQ-4 in PLAN, tick tasks 3 and 5, then the Handoff.

**Handoff notes (for whoever finishes Phase 3 and for Phase 4):**
- Phase 4 inputs: TVS array (low C) + series R for 6 channel lines; SJ2/SJ3 footprints; the ground-spring reach (replace the 5 mm working rule with a measured value); three upstream pull-up values per line and the downstream option value; LED parts (red, yellow, green ×2, orange, blue, white) and resistors; 1 × 4 and 2 × 15 headers.
- Phase 7 inputs: row c (two regulators; v7 position should use an AMS1117-type for fidelity, CL-08; check back-powering through pull-ups), row h rail list, rows i/j/k conditional on the charger choice, OQ-4 battery connector.
- Phase 12: firmware must support SDA and SCL pins independently (four combinations).
- OQ-5 still open (card (j) not run). PLAN Approach and Technical Notes still describe the work; nothing rejected; PLAN not edited.
- Commits: `d945387` (task 1), `93590ae` (task 2), `54413de` (task 3, WIP), `ea75703` (task 4), plus this notes commit.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 3 | Phase 3: Design intent — GPIO, jumpers, test points | PARTIAL | Yes — resolvable without replanning: the stop is the planned user gate (OQ-2, OQ-4, W2 part 1) | 2a5cb13 | Tasks 1, 2, 4 done; tasks 3, 5 and Handoff await the user |

#### Verification
- TASKS.md Phase 3: tasks 1, 2, 4 `[x]`; tasks 3, 5 and Handoff `[ ]`. Working tree clean. PLAN.md unchanged; no date-stamped headings. Nothing under `lab/` touched.
- `hardware/pcb-main-v8/CONTEXT.md` GPIO allocation, Jumper matrix (rows a–k, OQ-2/OQ-4 option tables) and Test points sections are filled and marked "pending user approval".
- OQ-5 stays open: no new debug-track cards since the plan (V7R-020 is the latest). Jumper (a) is designed not to depend on card (j).
- Jumper rows i, j, k were added beyond PLAN rows a–h. That is inside task 3's remit ("add any others the changelist §3 supports"), not a scope change.
- Loop paused for the user: OQ-2, OQ-4, the four v7-valued jumper defaults (d, f, h, i), and W2 part 1 approval.

**User decisions (2026-11-02), relayed by the Orchestrator:** OQ-4 = A (board ≤ 100 × 100 mm, 18650 on a keyed, polarised cable connector). OQ-2 = option 1 (external-master header only, no dev-board footprint). W2 part 1 = approved as written (GPIO allocation, jumper matrix a–k with the d/f/h/i v7 defaults, test-point list). GARDEN: the three doc errors from Workers #1–#2 added to `docs/initiatives/GARDEN.md` (new file; the protocol's prescribed location).

Re-dispatch: Worker #3 resumed with its context to record the answers, finish tasks 3 and 5, and do the Handoff. It continues its own block (Notes addendum).

**Addendum (Worker #3, after the user's answers).** Recorded in `hardware/pcb-main-v8/CONTEXT.md`: the three sections now read "approved by the user 2026-11-02 (W2 part 1)"; the OQ-2/OQ-4 option tables are replaced by a short Decisions subsection (decision + reason + what was not chosen); row (e) now says "no second master footprint". PLAN: OQ-2 and OQ-4 struck as resolved 2026-11-02; OQ-5 left open (card (j) not run). TASKS: tasks 3 and 5 and the Phase 3 Handoff ticked. Carried to later phases, unchanged from the Handoff notes above: Phase 4 parts list (TVS + series R, SJ2/SJ3 footprints, measured spring reach replacing the 5 mm working rule, pull-up and LED parts, headers); Phase 7 (row c regulators with an AMS1117-type v7 position, row h rails, conditional rows i/j/k, the OQ-4 battery connector); Phase 12 (SDA and SCL pins set independently).

#### Result (re-dispatch)
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 3 | Phase 3: Design intent — GPIO, jumpers, test points | DONE | Yes (earlier PARTIAL) — resolved by the user's answers | a10b44c | Tasks 3, 5 + Handoff closed |

#### Verification (re-dispatch)
- TASKS.md Phase 3: all six items `[x]`. Working tree clean. PLAN.md: OQ-2 and OQ-4 struck in the existing style; OQ-5 open; no date-stamped headings.
- CONTEXT.md: the only remaining "pending" wording is the OQ-5 note (card (j) hasn't run), which is correct.
- W2 part 1 closed. W2 part 2 (parts) is due at the end of Phase 4.

---

### Worker #4 — Phase 4: Design intent — parts (non-power)

**Dispatch:** standard spawn prompt, plus:
- Additional reading: SESSION.md Worker #3 `#### Notes` (including the addendum; its Phase 4 carry-forward list); `hardware/pcb-main-v8/CONTEXT.md` (GPIO allocation, Jumper matrix, Test points, Decisions); `hardware/CONTEXT.md`; `docs/research/v7-retry/v6-v7-changelist.md`.
- OQ-2 = header only, so task 3's header question is settled: the external-master header plus UART0 header (and the spare-GPIO header from Phase 3).
- Power parts belong to Phase 7, not here. Stock checks use the JLC MCP if it's available in the Worker's tools; otherwise record "stock not checked" and the reason per part.
- W2 part 2: the Worker prepares the approval summary and returns it; the Orchestrator puts it to the user.

#### Notes

**Stock source.** The JLC MCP was not in the Worker's tools. Stock came from JLCPCB's public parts API (`POST jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList`, keyword = LCSC code), the same data as the JLC parts page, checked 2026-11-02. LCSC's own `wmsc.lcsc.com/ftps/wm/product/detail?productCode=Cxxxx` also answers. Both work from curl without a key; the scratch script isn't committed (a one-file helper could go in `tools/` if Phase 7/19 want it: Worker's suggestion, not done).

**Task 1: cable-facing protection.** TPD2E2U06DRLR (C1972959, 4 078, SOT-553) per connector; alternate TPD4E05U06DQAR (C138714, 121 301, USON-10). 47 Ω series R (C23182, basic). V_RWM 5.5 V rather than a 3.3 V part, for nA leakage at 3.3 V. Rise-time table from datasheet values (TCA9548A SCPS207H downloaded to scratch, PCA9546A from `docs/references/`), with Cb ≈ 200 pF estimated (no measured value exists). Outcome: TVS and series R cost ≤ 5 ns; the real cost of the series R is ≈ 62 mV on the low level, which is why 47 Ω, not 100 Ω. The table also shows 10 k upstream alone exceeds 300 ns at 200 pF, and 2.2 k upstream + downstream exceeds 3 mA.

**Task 2: footprints.** KiCad stock names in CONTEXT → Parts → Footprints. Default-closed jumpers use the factory-bridged SJ footprints (JLC can't place a solder blob). SJ3 pad rule: pad 2 = common, pad 1 = default position, pad 3 = other (row i's default is SW1 = v7). Ground-spring rule replaced: signal-to-ground gap 1.0–3.0 mm edge to edge, from bench-demonstrated SQ500 placements (2.64 mm pad F, 3.05 mm pad C on v7; `lab/procedures/known-good-reference.md`, read-only). Maximum spring reach not measured; optional user caliper check offered. Rail current-measure 0 Ω 1206: current rating unknown, Phase 7 checks per rail (+5V_TO_LEDS 3 A likely needs 2512).

**Task 3: LEDs, pull-ups, headers.** LEDs 0603 KT series (green = v7 D1 part), resistors for ≈ 1 mA; STAT LED anode on VSYS (conditional on Phase 7 keeping the BQ). Upstream pull-ups 2.2 k / 4.7 k / 10 k basic; downstream 4.7 k. Headers hand-fit, LCSC numbers recorded. "pull-up rail chosen in Phase 4" and other forward pointers in the approved sections were resolved to point at Parts (pointer text only; no approved decision changed).

**Task 4: v7 parts review.** One swap: IC1 SN74AHCT125PWR (0 stock; three unused gates with floating inputs) → SN74AHCT1G125DBVR C7484 (41 125). Thin stock: D5 WS2812B-MINI-X2 152 (fallback V3J C22371519). Flagged to Phase 7: R44 10 mΩ shunt C1322424 has **2** in stock. Considered, not changed: D5 DIN at 3.3 V vs VIH ≈ 3.5 V at 5 V VDD (moving it would break row g's v7 membership).

**Task 5 (left `[ ]`: W2 part 2 awaits the user).** Parts section filled, headed "pending user approval (W2 part 2)".

**For the Orchestrator to put to the user (W2 part 2):**
1. Protection (row b): TI TPD2E2U06 dual TVS (1.5 pF, 5.5 V standoff) at each sensor connector, plus a 47 Ω series resistor per line. Cost on the bus: ~3–5 ns rise time and ~60 mV on the low level, both removable by the row b jumpers.
2. Pull-up options (row d): upstream 2.2 k (default) / 4.7 k / 10 k; downstream 4.7 k per channel line (open). Allowed: one upstream value at a time; downstream only with 4.7 k or 10 k upstream.
3. Jumpers: factory-bridged solder jumpers where the default is closed (cut to open); SJ3 pad 1 = default. Test points: 1.5 mm round signal pads, 2.5 mm square ground pads, 1–3 mm apart (the 3 mm is what the SQ500 springs have already reached on v7). Optional: measure the springs' reach with calipers to relax it.
4. LEDs: green ×2, yellow, red, orange (STAT, on VSYS), blue, white, ≈ 1 mA each. Headers hand-fit.
5. One swap: the LED level shifter becomes the single-gate SN74AHCT1G125 (the quad is out of stock and v7 left three gates floating). Everything else from v7 is kept. Watch items: WS2812B-MINI stock 152; R44 shunt stock 2 (Phase 7).
After approval: change the Parts status line to "approved by the user <date> (W2 part 2)", tick task 5, then the Handoff.

**Handoff notes.** PLAN Approach/Technical Notes still describe the work; no approach change, nothing rejected, PLAN not edited. No Deferred items. OQ-5 still open. Commits: `b4cecb0` (task 1), `281e7ae` (task 2), `ce7d66b` (task 3), `4452d09` (task 4), `761d29b` (task 5 WIP), plus this notes commit.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 4 | Phase 4: Design intent — parts (non-power) | PARTIAL | Yes — resolvable without replanning: the stop is the planned user gate (W2 part 2) | 9fec430 | Tasks 1–4 done; task 5 and Handoff await the user |

#### Verification
- TASKS.md Phase 4: tasks 1–4 `[x]`; task 5 and Handoff `[ ]`. Working tree clean. PLAN.md unchanged. Nothing under `lab/` edited (`lab/procedures/known-good-reference.md` read only).
- Edits to the W2-part-1-approved sections were checked line by line: rows b and d, the Ground points rule and the STAT LED row only fill in what Phase 3 had deferred to Phase 4 (implementation detail, the measured 1.0–3.0 mm spacing rule, the STAT pull-up rail). No approved decision changed.
- Stock checked through JLCPCB's public parts API (the JLC MCP isn't in the Worker's tools), dated 2026-11-02. Watch items carried forward: WS2812B-MINI-X2 has 152 in stock; R44 shunt has 2 (Phase 7).
- Loop paused for the user: W2 part 2.

**User decisions (2026-11-02), relayed by the Orchestrator:** W2 part 2 is approved, with one change to how the jumpers are built (what each jumper does is unchanged). Jumpers that are switched often become 2.54 mm pin headers with push-on shunts:
- row a (both SJ3s and the two UART0 SJ2s)
- row b (all 9: the series-R bypasses and the TVS GND legs)
- row c
- row d upstream (one select-one-of-three header per line, so a single shunt can't connect two values)
- row f

These stay as solder pads: row d downstream, row e links, rows g, i, j, k, and the LED load jumpers. Row h is unchanged (0 Ω + unfitted header). The user also asked for the TVS (TPD2E2U06) unit price. Points 3–6 of the walkthrough (rail links, test-point spacing, IC1 swap, kept v7 parts including D5 at 3.3 V drive) were accepted as written.

Re-dispatch: Worker #4 resumed with its context to apply the jumper change, close task 5 and do the Handoff.

**Addendum (Worker #4, after the user's W2 part 2 decision).** Applied to `hardware/pcb-main-v8/CONTEXT.md`:
- Jumper matrix: rows a, b, c, d (upstream), e (usage text) and f now describe pin headers with shunts. A status line says the implementation changed per W2 part 2, not the positions.
- New Parts → Jumper headers subsection. Row a is one 1 × 4 per line (U3_IO16 / bus / U3_IO43 / UART0). The v7 shunt on 2–3 physically excludes both v8 shunts. Row d upstream is a 2 × 3 per line: the bus line is on the odd row and the three resistors are on the even row, so one shunt picks exactly one value. Row c is a 1 × 3. Rows b and f are 1 × 2.
- Counts: 16 headers (11 × 1×2, 1 × 1×3, 2 × 1×4, 2 × 2×3). Shunts: 12 fitted in v8, 13 in all-v7, supply 15 per board. 13 SJ2 and 4 SJ3 remain.
- Shunt: C5305, open-top, 3 A, 920 428 in stock. Row c's argued worst-case peak is about 1.2 A (six VCNL4040 IR LEDs at the 200 mA LED_I maximum, all lined up).
- TVS price: US$0.3254 each (1–49 tier): about $0.98 for 3 and $4.88 for 15. JLC minimum buy is 5. Extended-part loading fee is about $3 per unique part per order.
- Parts status: "approved by the user 2026-11-02 (W2 part 2), with the header/pad jumper split". Footprints table updated: default-closed SJ2 now covers the LED loads only, and SJ3 covers rows g, i, j, k.
- One cost recorded in row b: the header in the TVS GND leg adds a few nH to the clamp path (argued). The layout rule is to put it beside TVS pin 4.

Task 5 and the Phase 4 Handoff are ticked. PLAN is unchanged: the approach still holds, nothing was rejected. Phase 7 carry-forward: row c's regulators, the row h 0 Ω current rating per rail, R44 shunt stock (2), and the STAT LED rail.

#### Result (re-dispatch)
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 4 | Phase 4: Design intent — parts (non-power) | DONE | Yes (earlier PARTIAL) — resolved by the user's W2 part 2 answer | abfaf2e | Header/pad split applied; task 5 + Handoff closed |

#### Verification (re-dispatch)
- TASKS.md Phase 4: all six items `[x]`. Working tree clean. PLAN.md unchanged; OQ-5 open.
- CONTEXT.md: Parts status reads approved (W2 part 2, header/pad split). The Jumper matrix status says only the implementation changed, not the positions. 16 headers (rows a, b, c, d-upstream, f) as the user decided; the rest stay pads.
- Row a's 1×4 arrangement is a Worker design choice inside the decision: v7 uses a single shunt on 2–3, which physically prevents GPIO43 being on the bus and on UART0 at once. It keeps the approved positions.
- W2 is now closed except for the power path, which Phase 7 closes.
- Stock watch carried to Phase 19: the 2×3 header C56153599 has 1,000 in stock (10 needed for 5 boards); WS2812B-MINI has 152; R44 has 2 (Phase 7).

---

### Worker #5 — Phase 5: Board model — parse and validate (audit phase 1)

**Dispatch:** standard spawn prompt, plus:
- Additional reading: `docs/research/v7-retry/kicad-extraction-audit.md` §3–§6.1 (the spec and fixture table); `tools/CONTEXT.md` (Critical Rule, Source-Hash Rule, pcb-context section); `tools/pcb-context/README.md` and the existing scripts there (`extract.py`, `routing_extract.py`, `routing_audit.py`, `place_power.py`, `audit-specs/`) to reuse rather than duplicate.
- This phase is independent of the hardware design phases; it validates on v7 `c2acffc` only.

#### Notes

**Validation on v7 `c2acffc` (task 4).** The source was `git archive c2acffc hardware/pcb-main/kicad` into scratch. Its sha256 `ff6857d0…` is the same as the working-tree file, so `c2acffc` = HEAD for this PCB. Run: `python3 tools/pcb-context/board_model.py <scratch>/motion-play-main.kicad_pcb -o <scratch>/v7-model.json --source-ref c2acffc` (9 s with DRC; the config was auto-picked from `board-config/motion-play-main.json`). Fixture values were computed from the model through the `BoardModel` API (scratch scripts, not committed).

| Audit §6.1 check | Expected | Model | Δ | Note |
|---|---|---|---|---|
| SDA length | 72.9 (F 35.9 / B 37.0), 3 vias | 72.90 (F 35.92 / B 36.98), 3 vias | 0.0 / +0.02 / −0.02 | |
| SDA branches from U3.37 | 19.4 / 5.9 / 31.7 / 47.7 | R28.1 19.36 / TPIO43.1 5.87 / U7.6 31.67 / U5.6 47.69 | −0.04 / −0.03 / −0.03 / −0.01 | Also U4.23 9.42 (the audit's 19.4 is the end of that branch, R28.1). Vias on path: 0/0/2/3. Driver from config. |
| SCL to BOOST_SW gap | 0.94 edge to edge | track to track **0.937** (S547 0.25 mm ↔ S723 1.5 mm, F.Cu) | −0.003 | All copper: **0.662**, from SCL via V200 to the 1.5 mm BOOST_SW track. The audit's method left vias out, so the real minimum is 0.28 mm smaller than the fixture. Next: SCL track to R41.2 (BOOST_SW pad) 1.21. |
| SDA to R44 pad 2 | 0.85 | SDA tracks to R44.2 **0.845** | −0.005 | All SDA copper (pads and vias too): 0.570 (an SDA pad or via is closer than any SDA track). |
| SDA to SCL gap | 0.20 | F.Cu 0.200 / B.Cu 0.210 | 0.0 | Centreline 0.451 / 0.460 (audit 0.45). Within 1 mm of SCL copper: F 30.7 / B 20.0 (audit, not a fixture: 27.8 / 19.5; the model counts SCL pads and vias as well). |
| SDA over In2 +3.3V / over nothing | ~28.9 / ~6.8 | +3.3V **28.94**; nothing: raw **8.04**, **6.46** without the 0.6 / 0.6 / 0.38 mm crossings of SDA's own via antipads at V196/V198 | +0.04 / −0.34 | The void run is S541 6.01 + S542 0.43 + S539 0.02 (V197 → x 111.8, y 122.17). With every own-via antipad disc removed it is 5.49. The audit's "~6.8" was approximate. The 6.46 figure is the same quantity measured exactly. +5V under SDA: 0. |
| SDA B.Cu inside BT1 body | 29.7 | **29.74** (body from B.CrtYd: x 75.69–163.57, y 117.77–139.43) | +0.04 | 0.0 inside BT1's pad bbox (audit: "outside its pad bbox"). |
| Zones | 8 per audit §4 | 8: In1 GND (81 holes); In2 +5V p7 (70 holes) / +3.3V p8 (36 holes); F.Cu BOOST_SW p4, +5V p5, GND p3, +3.3V p6; keepout on all four layers (tracks, vias, pads, pour not allowed) | 0 | All 7 copper zones filled, no unfilled warning. De-fracture kept the area exactly. |

**KiCad spot checks** (the audit asks for these. kicad-cli stands in for the GUI, because the Worker can't open KiCad):
- **Pads:** `kicad-cli pcb export ipcd356` gives KiCad's own pad centre, size and rotation. All 359 copper pads match: worst centre Δ 0.0017 mm and worst rotated-extent Δ 0.0013 mm, both under the format's 0.0001 in (0.00254 mm) grid. That covers rotated R44 (−90°) and the (0, 180) / (90, 270) pads that are rotated relative to their footprint.
- **Zones:** `kicad-cli pcb export gerbers --layers In1.Cu,In2.Cu`, region area per `TO.N` net: In1 GND 2991.13, In2 +5V 1582.19, In2 +3.3V 1177.91 mm². The model gives 2991.13 / 1582.19 / 1177.91.
- **Connectivity:** DRC reports 0 unconnected items, and the model has no net split into islands.

**What changed while building (task 2).**
- **Connectivity rule.** The first version joined a track to a pad only if the track's endpoint lay inside the pad. That split 6 nets that KiCad treats as connected (e.g. U5.20: the 0.75 mm track ends 0.076 mm outside the pad, but the pad centre is under the track). Now: an anchor of one item inside the copper of the other connects them, as in KiCad's connectivity (track anchors are its endpoints; pad and via anchors are their centres). Track endpoints inside another track's copper merge. Overlapping same-net pads join (U6's custom exposed pad holds 8 more pads numbered 21). Result: 0 islands, matching DRC.
- **Pad angle** in the file is absolute (it already includes the footprint's rotation). Confirmed by the IPC-D-356 check.
- **De-fracture:** `Polygon(fill).buffer(0)` gives back the holes (81/70/36). `make_valid(method="structure")` doesn't exist in shapely 2.0.7.
- One zero-length GND track (S297) is ignored for splitting.

**Environment (task 1).** pip 20.0.2 builds only `macosx_26_*` wheel tags on this macOS 26 (x86_64 Python), so it saw no wheels for any version of matplotlib. Fix: `python3 -m pip install --upgrade "pip<24.1"` (24.0 is the last pip for 3.7), then `pip install matplotlib`. Result: matplotlib 3.5.3 (Agg render tested), numpy 1.21.6. shapely 2.0.7, kiutils 1.4.8 and kicad-cli 9.0.4 at the app path were all confirmed. `tools/pcb-context/requirements.txt` now lists matplotlib. This is a hazard (old pip on macOS ≥ 11 says "no matching distribution"). `.context/HAZARDS.md` doesn't exist and creating it is outside a Worker's remit, so it is noted here for the Orchestrator or Gardener.

**Model facts for Phase 6.**
- Output is about 950 KB of JSON (In1 fill 5.8k points).
- `BoardModel` gives shapely geometry: `net_copper(net, layers, include_zones)`, `pad_geom`, `segment_geom` / `segment_line`, `via_geom`, `body`, `zone_fill`, `layer_fill(layer, net)`, `outline`.
- Topology per net: `root` (config `drivers`, else a heuristic: a pad on the largest footprint), `chains` (key node to key node, with layer, length and segment ids), `branches` (Dijkstra from the root: length, by layer, via count, node path), `stubs` (dangling tracks, one-sided vias), `islands`.
- Through vias carry annular rings on In1/In2 in `net_copper` (KiCad's via `removeUnusedLayers` is False on v7). So same-layer gaps on inner layers are via-to-via.
- The plan-view gap between SDA and SCL is 0 because they cross on opposite layers. Phase 6 must report plan-view proximity alongside the layer separation, not as a bare minimum.
- DRC with `--severity-all` gives 25 (18 errors: 16 clearance, 2 hole_clearance; 7 warnings) and 0 unconnected. Topic 2's "6 minor" was presumably at default severity, excluding the warnings and footprint-library checks; it was not re-derived here.
- The sensor-rigid and sensor-flex boards also parse (0 unconnected, no islands). They are not validated (still Deferred).

**Handoff.**
- All six Phase 5 items are done.
- Commits: `40b7cdc` (task 1, environment), `04999e5` (task 2, `board_model.py`), `893876b` (task 3, config), `8a2bfc4` (task 4, validation), `812e49b` (task 5, README historical), plus this handoff commit.
- PLAN: Technical Notes now name the config path and the connectivity rule. One line was appended to Rejected Approaches (endpoint-only pad joins). The approach is unchanged.
- No Deferred items added: the sensor-board run is already Deferred. Both sensor boards parse; they are not validated.
- Nothing under `lab/` was touched. No `.kicad_pcb` or `.kicad_sch` text was read or edited: kiutils and kicad-cli only, on a scratch `git archive` copy.

**For Phase 6:**
- `board_model.py` writes no v7 output into the repo (validation ran in scratch). Phase 6 decides where the generated model and reports for v7 and v8 get committed.
- Two fixture rows depend on method:
  - SCL–BOOST_SW: the fixture's 0.94 is track to track. The all-copper minimum is 0.66, through SCL via V200.
  - SDA unreferenced: the fixture's "~6.8" is 6.46 measured exactly with own-via antipad crossings excluded, or 8.04 raw.
- The Phase 6 acceptance test should state which method each number uses.
- `routing_audit.py` still has the centreline-distance bug. Phase 6 makes it a thin consumer of the model, or retires it (audit §6.1).

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 5 | Phase 5: Board model — parse and validate | DONE | Yes (step 11) — pip upgrade outside the plan; resolvable, no replan | e7c24f3 | 5 tasks + handoff; commits 40b7cdc, 04999e5, 893876b, 8a2bfc4, 812e49b, e7c24f3 |

#### Verification
- TASKS.md Phase 5: all six items `[x]`. Working tree clean. PLAN.md: one Rejected Approaches line (append-only, allowed) and a Technical Notes clarification (config path by PCB stem; KiCad's anchor-inside-copper connectivity rule). The approach is unchanged; no date-stamped headings.
- Re-derived independently: ran `board_model.py --no-drc` on a fresh `git archive c2acffc` copy in the Orchestrator's scratch. Result: 93 footprints, 362 pads, 102 nets, 8 zones, `/I2C_SDA` 72.898 mm with 3 vias, matching the audit fixture and the Worker's table. Runs in about 6 s.
- Outside the plan: the Worker upgraded pip (20.0.2 → 24.0) in the user's pyenv Python 3.7.3 to get a matplotlib wheel. It's a small, reversible environment change made in service of task 1; raised with the user. The trap is recorded in `.context/HAZARDS.md` (created by the Orchestrator; PROTOCOL lets any session add a hazard).
- Carried to Phase 6: where committed model/report outputs live (none committed yet); acceptance must name the measuring method for each number (track-to-track vs all copper; raw vs antipads excluded). SCL–BOOST_SW real minimum is 0.662 mm (via to track), not the audit's 0.94.

---

### Worker #6 — Phase 6: Board model — reports and images (audit phase 2)

**Dispatch:** standard spawn prompt, plus:
- Additional reading: SESSION.md Worker #5 `#### Notes` (validation table, method notes, Phase 6 carry-forward); `docs/research/v7-retry/kicad-extraction-audit.md` §3 (the SDA acid test), §5–§6.1; `tools/pcb-context/board_model.py` (`BoardModel` loader), `README.md`, `board-config/motion-play-main.json`; `tools/CONTEXT.md`.
- The Worker decides where committed outputs go, consistent with the Source-Hash Rule, and records it in the README.

#### Notes

**Where outputs go.** `hardware/pcb-main/kicad/board-model/` (beside the PCB): `board-model.json`, `net-report.md/.json`, `plane-report.md/.json`, `img/net-*.png`, `img/plane-*.png`, each PNG with `.png.meta.json`. Generated from the repo path (`--source-ref c2acffc`), so `_provenance.source` is repo-relative and `check_state.py --fresh` re-hashes it: all 16 files FRESH. The repo file's sha256 `ff6857d0…` equals the `git archive c2acffc` copy (checked again in scratch). Regenerated after the last code commit, so `generator_commit` is clean (`aa34a87`). Recorded in `tools/pcb-context/README.md` ("Where committed outputs go") and PLAN Technical Notes.

**What was built.** `report_lib.py` (shared geometry and the measuring methods), `net_report.py`, `plane_report.py`, `render.py`, all reading only `board-model.json`. Runtimes on v7: model 9 s, net report 8 s, plane report 3 s, render 23 s.

**Acceptance: audit §3 acid test, from the outputs alone** (`net-report.json`/`.md` block `/I2C_SDA`, `plane-report.*`, `img/net-I2C_SDA.png`, `img/plane-In2_Cu.png`).

*Where SDA routes* (net-report route tree): U3.37 → F 3.9 → junction (143.41, 111.60) → F 2.0 → TPIO43.1; junction → F 5.5 → U4.23 → F 9.9 → R28.1; U3.37 → F 1.5 → V196 (138.40, 112.65) → B 26.3 (9.2 diagonal, then 17.1 along y = 119.17) → V198 (114.77, 119.17), the branch point → F 3.8 → U7.6; V198 → B 10.6 (6.0 along y = 122.19, x 105.4 → 111.4) → V197 (105.37, 122.19) → F 9.2 → U5.6.

| Check | Audit | Output | Method / where |
|---|---|---|---|
| SDA length | 72.9 (F 35.9 / B 37.0), 3 vias | 72.90 (F 35.92 / B 36.98), 3 vias | track centreline sum; net report header |
| Branches from U3.37 | 19.4 / 5.9 / 31.7 / 47.7 | R28.1 19.4 / TPIO43.1 5.9 / U7.6 31.7 / U5.6 47.7 (+ U4.23 9.4) | along copper from the config driver; endpoints table |
| SDA to SCL | 0.20 | F 0.20 / B 0.21 | track to track, per layer (`by_layer_track_to_track_mm`) |
| SDA within 1 mm of SCL | F 27.8 / B 19.5 (not a fixture) | F 32.1 / B 20.3 | coupled: SDA centreline within 1 mm of all SCL copper incl. pads and vias (the audit used tracks) |
| SDA to CHRG_INT | 0.23 F (sketch) / "0.84 B" | F 0.23 / B 0.59 track to track; all copper F 0.20, B 0.31 | the audit's B figure was approximate; B 0.59 is S539 (V197's 0.02 mm stub) to S174 |
| SDA to R44.2 | 0.85 | 0.85 | track to copper (SDA tracks to the pad); all copper 0.57 (V197 to R44.2) |
| SCL to BOOST_SW | 0.94 | 0.94 track to track; 0.66 all copper (V200 to S723) | SCL block, neighbours |
| SDA B.Cu over In2 +3.3V / nothing | ~28.9 / ~6.8 | +3.3V 28.94 raw; nothing 8.04 raw / **6.19 antipads excl.** | reference planes table. Worker #5's 6.46 kept S542's 0.27 mm crossing of V198's antipad; the report's rule closes every fill hole that contains a drill. The 6.19 is S541 6.01 + S542 0.16 + S539 0.02 |
| Where that void is | "mostly the 6.0 mm run from 105.4 to 111.4 along y = 122.17" | S541 6.01 mm (105.38, 122.17) → (111.40, 122.17) | unreferenced stretches; **plane report: S541 lies in the In2 +3.3V / +5V split gap (6.01 mm in the gap, min gap 0.90 mm)**, as do SCL S570/S576 |
| SDA F.Cu over In1 GND | — | 30.71 raw, 5.21 raw void = V196/V197/V198 antipads; 0.00 antipads excl. | reference planes |
| SCL unreferenced | ~7.4 | B 6.78 antipads excl. (9.79 raw) | SCL reference planes |
| SDA B.Cu inside BT1 body | 29.7 | 29.74 (and F 13.04) | bodies, plan view |
| Under C53 | "passes directly under" | C53 B 2.96 mm; plan-view 0.00 to C53.1/C53.2 | bodies; neighbours GND/+3.3V plan view |
| U3 GND / LED_DATA within 0.75 mm plan view | yes | LED_DATA F.Cu track S12 crosses SDA B.Cu (plan view 0.00, 1.44 mm apart); GND 0.00 (C53.2) | plan view across layers |
| Zones | 8 | 8 | model |

Also found unprompted (not in the audit): SDA's three vias are each 3.2–4.0 mm (centre to centre) from the nearest GND via, and each sits where the reference changes from In1 GND (F side) to In2 +3.3V (B side), V197 also beside +5V. The plane report lists 16 signal tracks crossing the In2 split, including CHRG_INT, TCA_RESET, LED_DATA and both USB lines.

*PNG check.* Looked at all 11 PNGs (8 nets, F.Cu/In1/In2). Every pad and via label's leader ends on a dot at the pad or via centre, and every dot sits on its pad (U3.37, U4.23, R28.1, TPIO43.1, U7.6, U5.6, V196–V198 on SDA; the same on SCL and the six channel nets). Fixed during the check: the legend was clipped; footnote collided with the x label; 12 `unconnected-(…)` labels cluttered SCL (now highlighted but not labelled, with a count in the footnote); the view now stops 1 mm outside the outline; the F.Cu image hatched the whole board as a void (voids are now drawn only on plane layers, ≥ 25 % fill, as in the plane report).

**Other notes.**
- DRC in the model differs with the PCB's location: 25 from the scratch archive, 20 from the repo path. The 5 extra are `lib_footprint_issues` (library tables resolve differently in scratch). Clearance 16, hole_clearance 2, padstack 2 in both.
- No-connect pads (`unconnected-(…)` nets) are real neighbours and stay in the reports; only the PNG labels drop them.
- `routing_audit.py` / `routing_extract.py` are marked superseded in the README, not changed or retired (the debug track cites their outputs). Added to Deferred.
- tools/CONTEXT.md: pcb-context section rewritten around the board model; the Source-Hash scope line no longer refers to a "board-model initiative" (the `circuit-context.json` retrofit is unscheduled and outside the board model).

**Handoff.** All six Phase 6 items done. PLAN: one Technical Notes clause (where outputs go) and one Rejected Approaches line (split-channel subtraction for voids). Deferred: one line (routing_audit). Nothing under `lab/` touched; no `.kicad_pcb`/`.kicad_sch` text read or edited. Commits: `f25d7fe` (task 1), `2611fdf` (task 2), `18d60a5` (task 3), `aa34a87` (per-layer track gaps), plus the handoff commit.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 6 | Phase 6: Board model — reports and images | DONE | No — clean completion | 38ff6bb | 5 tasks + handoff; commits f25d7fe, 2611fdf, 18d60a5, aa34a87, 38ff6bb |

#### Verification
- TASKS.md Phase 6: all six items `[x]`. Working tree clean. PLAN.md: one Technical Notes clause (where outputs go) and one Rejected Approaches line; approach unchanged; no date-stamped headings. New Deferred line: `routing_audit.py` as a model consumer, or retired.
- Outputs are committed under `hardware/pcb-main/kicad/board-model/` (27 new files). No existing v7 file was modified, so the debug track's `c2acffc` citations still hold. `board_model.py --check` on the committed model reports the source matches.
- Looked at `img/net-I2C_SDA.png`: readable, the legend fits, pad/via leaders end on their pads, and the 6.2 mm unreferenced run is drawn dashed.
- Carried to Phase 7 / layout: on v7, the SDA/SCL unreferenced runs lie in the In2 +3.3V/+5V split gap, which 16 signal tracks cross (USB pair included). This is an input for the v8 stackup/plane plan, not a v7 action.
- Known variance: the DRC count differs by 5 `lib_footprint_issues` between the scratch and repo paths (library-table resolution). Clearance, hole and padstack counts are identical.

---

### Phase 7 — W1 check (no Worker dispatched)

Phase 7 task 1 is the W1 gate. Before dispatching, the Orchestrator checked every local and remote branch for `lab/cards/PWR-*` and `lab/investigations/power/`. There are none; `lab/investigations/` holds only `v7-i2c`. W1 hasn't closed, so no Worker was dispatched (the relay says to stop at Phase 7, not skip ahead). Phase 7 task 1 stays `[ ]`.

**Outcome:** Paused — awaiting user decision (W1: the Debugger's power bench findings, `debugger/RELAY-power.md`). Phases 1–6 are complete. Phases 8+ depend on Phase 7.

---

## 2026-11-03 — orchestration run 1, resumed

Entry conditions: the Debugger's `power` investigation merged to `main` (PR #90, `76ba42b`), with cards PWR-001 and PWR-002. `main` was merged into `feat/v8-debug-board` (`b55eafb`); no conflicts, and only `lab/` files came in. `lab/investigations/power/STATE.md` §8 leaves the W1 call to the user.

**User decision (2026-11-03), relayed by the Orchestrator:** W1 is closed on PWR-001 and PWR-002. B1 (reversed cell) and B2 (Q2 under load) are untested; they are to be treated as design risks that v8 designs out, not as open bench questions.

---

### Worker #7 — Phase 7: Power path design

**Dispatch:** standard spawn prompt, plus:
- W1 answer (task 1): closed by the user 2026-11-03 on PWR-001, PWR-002. The Worker records it and ticks task 1.
- Additional reading: `lab/investigations/power/STATE.md` §1–§4 and §8; `lab/cards/PWR-001-passive-0004-0005.md` and `lab/cards/PWR-002-sw1-throw-on-usb.md` Conclusions (read-only); SESSION.md Worker #1, #2 and #4 Notes (BQ fix options, ranked mechanisms, design deviations, Phase 7 carry-forwards); `hardware/pcb-main-v8/CONTEXT.md` (all sections; OQ-4 decision = ≤ 100 × 100 mm with a keyed, polarised battery cable connector); `docs/references/{bq24195,tps61088,ina219}/DATASHEET_REFERENCE.md`; `tools/schematic-gen/` (spec format).
- Design input from PWR-002: with SW1 at its OFF (GND) throw, v7 doesn't run on USB at all. Jumper row (i)'s default needs reconsidering.
- The user's power-path approval (task 5) is a user gate: the Worker prepares the summary and returns PARTIAL.

#### Notes

**Task 1 (W1).** Recorded: W1 closed by the user 2026-11-03 on **PWR-001** and **PWR-002**; B1/B2 are design risks to design out. The CONTEXT battery section's status line now says what the cards settled (Ka SW1 at the GND throw on #0004; B8 measured-supported on healthy boards; #0001/#0002 argued). `95cf961`.

**Tasks 2–4.** All decisions are in `hardware/pcb-main-v8/CONTEXT.md` → Power path (headed "pending user approval"). Commits `b5c8378` (task 2), `b8e91df` (task 3), `b9da8be` (task 4), plus this notes commit.
- Charger: BQ24195 kept, fixed with rows j (D+–D− short, v8) and k (OTG from REGN, v8). Swap rejected (PLAN Rejected Approaches): it breaks row f's v7 bus membership. C90862 has 14 in stock; fallback BQ24195LRGER C417486 (3 196), same pins, decided at Phase 19.
- Battery: XT30 (board male C428721, cell lead female), F3 7 A Nano2 first, then back-to-back CSD25402Q3A (C111356) with a slow gate (R60 1 M, C60 220 nF, C61 22 nF, R61 47 k) driven by a new SW4 "BATT". Blocks a reversed cell (B1), Vgs −0.955·Vcell with RDS(on) specified at −2.5 V (B2), ≈ 2.6 V/ms ramp → ≈ 1 A inrush (B3a). Values are hand-calculated (argued); Phase 10 should sanity-check. Pinout checked: TI SLPS454B top view (D 1–3, G 4, S 5–8 + pad) matches the KiCad stock symbol/footprint. No v7 position for battery protection (stated as a question for the user).
- Row i: default changed to EN tied to VSYS_SENSE (PWR-002); SW1 kept wired as v7 behind pad 3. This changes a W2-part-1-approved default.
- New row l: cell NTC via J9 (default) vs TH1 (v7). Default suspends charging until an NTC is fitted (STAT blinks). Offered the alternative default in the summary.
- Row c: AMS1117 (MCU, also the v7 shared position) + AP2112K-3.3 (bus, v6 part) with EN on +3.3V_MCU to stop back-powering U3 through the pull-ups. Dropout margin from measured +5V 5.10 V: 0.6 V (AMS1117), 1.45 V (AP2112K).
- Row h: h1/h2 0 Ω 1206, h3 0 Ω 2512, h4 = 10 mΩ 3 W shunt (C2903468) for the 3 A LED rail. 0 Ω ratings are derived (√(P/50 mΩ)), marked argued. VSYS uses R44 + INA219; no link on the battery path.
- Fixed deviations: PMID 4 × 22 µF 1206; VBAT 10 µF + C30 moved to VBAT; F3; J7 shell on GND (v7's schematic already had SH on GND, the PCB legs had no net: Phase 8 checks the footprint's pad numbers); R44 → C2903468 (same 10 mΩ 1 %); STAT LED on VSYS confirmed. Plane-planning input (In2 split crossed by 16 tracks on v7) recorded for layout.
- Spec: `tools/schematic-gen/power_v8_spec.json` (135 parts, 54 nets, no single-pin nets except interface nets), generated by a scratch script (not committed). Same shape as `spec.json`, plus `v7_ref`, `dnp`, `pair_of` and per-net members. Row f's headers, the rail LEDs other than STAT, and the bus/LED-sheet parts are not in it. One row added to `tools/CONTEXT.md`.

**For Phase 10:** confirm from datasheets the items marked argued: AMS1117 max dropout, AP2112K EN threshold, 0 Ω jumper ratings, 22 µF 1206 DC-bias derating (PMID), Nano2 breaking capacity at low voltage, BQ24195 low-VBAT behaviour in battery-only mode (over-discharge isn't designed here). Check J8's + pad against the XT30 chamfer, INA219 symbol pin numbering vs the v7 order, and copy SW1/L1/U5/U6/J7 symbols and footprints from the v7 project. Phase 12: cap LED brightness on battery (≈ 1.8 A at a low cell, budget in CONTEXT).

**Approval summary for the user (task 5, closes W2). The Orchestrator puts this to the user.**
1. **Charger: keep the BQ24195**, fixed with two solder jumpers so it runs at 1.5 A from USB with no I²C (D+ shorted to D−; OTG pulled from REGN). Each has a v7 position. A swap would take the charger off the I²C bus, so v7's bus couldn't be rebuilt. Stock is 14; if it runs short, the pin-identical BQ24195L (3 196 in stock) goes in at order time (its system current is 2.5 A instead of 4.5 A).
2. **Battery on an XT30** (keyed; female on the cell lead), **7 A fuse first**, then **two P-MOSFETs back to back** with a slow gate. This blocks a reversed cell, drives the FETs fully (unlike v7's Q2), and ramps the battery in over ≈ 1.5 ms so plug-in current stays ≈ 1 A. There is **no v7 position** for the battery protection, because v7's arrangement is the damage risk. OK?
3. **New switch SW4 "BATT"** connects or isolates the cell. Trade-off: no charging with SW4 off.
4. **Row i default changes:** the boost always runs whenever there is power, so the board always works on USB (PWR-002 showed v7 looks dead on USB with SW1 off). SW1 stays, wired as v7, as row i's v7 position. This changes a default you approved on 2026-11-02.
5. **New row l, cell temperature:** a 2-pin socket for an NTC taped to the cell. Default = cell NTC: **charging stops (STAT blinks) until an NTC is fitted**. Alternative: default to the board thermistor (v7 behaviour). Which one?
6. **Regulators:** AMS1117 for the ESP32 (v7 part), AP2112K for the sensor bus (v6 part), and the bus one only switches on after the ESP32 rail, so the pull-ups can't back-power the ESP32. Margin from the measured 5.10 V is 0.6 V and 1.45 V.
7. **Current links on four rails** (MCU 3.3 V, bus 3.3 V, 5 V core, LED 5 V). The LED one is a 10 mΩ shunt rather than 0 Ω (rated well past 3 A, and it reads 10 mV/A without lifting anything).
8. Datasheet fixes: PMID 88 µF, 10 µF + 47 µF on VBAT, USB shell on GND, a new R44 part (same 10 mΩ). The STAT LED runs from VSYS.
After approval: change the Power path status to "approved by the user <date> (W2)" and drop the "pending" notes on rows i, k and l and in the Footprints SJ3 row. Then tick task 5 and the Handoff.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 7 | Phase 7: Power path design | PARTIAL | Yes — resolvable without replanning: the stop is the planned user gate (task 5, closes W2) | 349c7cd | Tasks 1–4 done; task 5 and Handoff await the user |

#### Verification
- TASKS.md Phase 7: tasks 1–4 `[x]`; task 5 and Handoff `[ ]`. Working tree clean. PLAN.md: one Rejected Approaches line (charger swap); no date-stamped headings. `lab/` untouched.
- Two items touch earlier approvals or the BRIEF, so they go to the user explicitly rather than being accepted by the Orchestrator: (1) row i's default reverses a W2-part-1 decision; (2) the battery protection has no v7 position, while BRIEF Constraints say "every suspected v7 → v8 difference has a v7 position". The Orchestrator's reading is that the constraint concerns differences suspected in the v7 I²C fault, and the battery path isn't one, but that's the user's call.
- Stock: BQ24195RGER has 14 in stock (5 needed). The pin-identical BQ24195L fallback is recorded. Phase 19 preflight re-checks.
- Loop paused for the user: task 5 (power path approval: row i default, no v7 battery-protection position, row l default, SW4 trade-off).

**User decisions (2026-11-03), relayed by the Orchestrator:** power path approved (task 5, closes W2), with these answers:
- Battery protection (XT30 → 7 A fuse → back-to-back P-MOSFETs) has **no v7 position**. The user accepts this as an exception to the BRIEF's v7-position rule, because the battery path isn't an I²C-fault suspect.
- Row i default = **boost always on**; SW1 as v7 is the v7 position. This supersedes the 2026-11-02 W2-part-1 default for row i.
- Row l default = **board thermistor (v7 behaviour)**; the cell NTC socket is the alternate position. This is the opposite of the Worker's proposed default.
- **SW4 "BATT" kept**, with its trade-off (no charging with SW4 off) accepted.
- Points 1, 6, 7, 8 (keep the BQ24195 with rows j/k, two regulators, four current links, datasheet fixes) accepted as written.

Re-dispatch: Worker #7 resumed with its context to apply the row l default, close task 5 and do the Handoff.

**Addendum (Worker #7, after the user's W2 decision).** Applied to `hardware/pcb-main-v8/CONTEXT.md`:
- Power path status: "approved by the user 2026-11-03 (W2), with row l defaulting to the board thermistor".
- Battery protection: the "no v7 position" bullet now records the user's acceptance as an exception to the BRIEF's v7-position rule (the battery path isn't an I²C-fault suspect).
- Row i (matrix, Power path, SJ3 footprint row): approved; says it supersedes the 2026-11-02 default.
- Row l: pad 1 (default) = TH1 (v8 = v7), pad 3 = J9 cell NTC (alternate). The "charging suspended / STAT blinks with no NTC" text, the STAT LED row and the Changes list now describe the alternate position. The all-v7 line notes the v8 default differs in rows a, b, c, g, i, j, k only.
- Row k: "pending" dropped. No "pending user approval" text is left in CONTEXT; the only "pending" left is OQ-5's card (j).
- `tools/schematic-gen/power_v8_spec.json`: JP35 pins swapped (pad 1 TS_BOARD, pad 3 TS_CELL), so the factory bridge (pads 1–2) gives the TH1 default. Regenerated: 135 parts, 54 nets.
Task 5 and the Phase 7 Handoff are ticked. PLAN is unchanged beyond the Rejected Approaches line already committed. Phase 8 carry-forward: the Phase 10 checks listed in the Notes above.

#### Result (re-dispatch)
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 7 | Phase 7: Power path design | DONE | Yes (earlier PARTIAL) — resolved by the user's power-path answers | e773838 | Row l flipped to TH1; task 5 + Handoff closed |

#### Verification (re-dispatch)
- TASKS.md Phase 7: all six items `[x]`. Working tree clean. CONTEXT.md: the only "pending" wording left is OQ-5 (card (j)), which is correct. `power_v8_spec.json` parses, and JP35 pad 1 = TS_BOARD, so the factory bridge gives the TH1 default the user chose.
- W1 and W2 are closed. Carried to Phase 10: the "argued" values in Worker #7's Notes (gate network, AMS1117 dropout, AP2112K EN threshold, 0 Ω ratings, PMID derating, fuse breaking capacity), over-discharge protection, J8 XT30 polarity and J7 shell pad numbering.

---

### Worker #8 — Phase 8: Schematic — project setup and MCU sheet

**Dispatch:** standard spawn prompt, plus:
- Additional reading: `tools/CONTEXT.md` (Critical Rule; schematic-modify, schematic-context sections) and `tools/schematic-modify/CONTEXT.md` + `modify.py`; `hardware/pcb-main-v8/CONTEXT.md` GPIO allocation, Jumper matrix rows a, e, g (with the W2 header implementations), Parts (header footprints, Kept v7 parts, IC1 swap, D5 note); SESSION.md Worker #3 and #4 Notes.
- The **(user)** steps (task 3) are a user gate: the Worker writes numbered KiCad instructions, commits, and returns PARTIAL; the Orchestrator relays them.

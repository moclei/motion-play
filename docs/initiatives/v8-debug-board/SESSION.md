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

#### Notes

**Task 1: project setup** (`tools/schematic-modify/v8_project_setup.py`). It copied the v7 project from git `c2acffc` into `hardware/pcb-main-v8/kicad/` as `motion-play-main-v8`. Copied: `.kicad_pro`, the 5 sheets, `.kicad_dru`, the lib tables and `libraries/`. Not copied: the v7 board, reports, production, netlists, context JSON, STEP. The lib tables now point `${KIPRJMOD}/../../pcb-main/resources/`, so v7's resources stay the only copy. Pinned libs `../../libraries/...` resolve unchanged. kiutils renamed each instance's project and set the title blocks to v8 / rev 8.0. The board is a fresh `.kicad_pcb` with v7's setup only: 4-layer stackup F/In1/In2/B, 0.1/1.24/0.1 mm, 1.6 mm. It has no footprints, nets, tracks, zones, graphics or outline. Checks:
- ERC: 59 warnings and 0 errors, the same as v7 at `c2acffc` (the before/after diff is empty once the lib paths are fixed).
- Netlist: identical to v7 (93 components, 102 nets, same membership).
- kicad-cli DRC loads the board. Its only violation is "no Edge.Cuts outline", which is expected; Phase 14 adds the outline.
- kiutils round-trip on these KiCad 9 sheets: no netlist change.

**Task 2: MCU sheet** (`tools/schematic-modify/v8_mcu_sheet.py`, with new helpers in `modify.py`: `set_pin_net`, `pin_position`, `remove_no_connect_at`, and `add_component(project_name=)`). Every edit is label-style, so nothing needs wiring in the GUI.
- U3 pins: 37 → U3_IO43, 36 → U3_IO44, 9 → U3_IO16 (the stub labels were renamed). 8 → U3_IO15 and 11 → U3_IO18 (each no-connect replaced by a label).
- Row a: JP1 and JP2 are `Conn_01x04` headers (C2691448). Pins: 1 U3_IO16/15, 2 I2C_SDA/SCL, 3 U3_IO43/44, 4 UART0_TX/RX.
- Row e: J10 is a 1×4 header (GND, EXT_SDA, EXT_SCL, +3.3V_BUS). JP3 and JP4 are open SJ2s from EXT_x to I2C_x. +3.3V_BUS comes in as a new hierarchical label. At the root it has a sheet pin on the left edge of the ESP32_S3 sheet with a `+3.3V_BUS` label (net `/+3.3V_BUS`). The Phase 10 power sheet joins it by the same label.
- Row g: JP5 is an SJ3 Bridged12. Pad 1 = U3_IO18 (default), pad 2 = LED_DATA, pad 3 = U3_IO16 (v7).
- IC1 swap (Parts): on `led_controller.kicad_sch`, SN74AHCT125PWR becomes SN74AHCT1G125DBVR (`74xGxx:74AHCT1G125`, flattened from 74LVC1G125; SOT-23-5; C7484). Labels were put at the old pin positions so the existing wires stay on their nets. Pin map v7 → v8: 1→1 (OE, GND), 2→2 (A), 3→4 (Y), 7→3 (GND), 14→5 (VCC).
- D5 is unchanged (CONTEXT: kept as v7). The fallback pinout check only applies if the part is substituted.
- New refs: JP1–JP5 and J10. They don't collide with the power spec's provisional JP30–35, J30–33 or TP10–75.

**Task 3: no (user) wiring steps.** The tools did all the wiring. Re-extracted with `tools/schematic-context/extract.py` (to scratch; not committed, since Phase 11 commits the context with provenance). U3 pin → net matches the GPIO allocation table for every connected pin: 37, 36, 9, 8, 11, 18, 23, 21/20/19, 27, 3, 13, 14, plus power pins 1/2/40/41. The 23 unused pins have no net. `v8_mcu_sheet.py --check` passes:
- Every JP/J10/JP5/D5/IC1 pin is on its expected net.
- With the all-v7 positions applied to the netlist (JP1/JP2 on 2–3, JP5 pads 2–3, JP3/JP4 open), every net's membership equals v7 at `c2acffc`, with 0 differences, once the jumper pins are removed and IC1's pins are mapped.
- v8 default: I2C_SDA = {R28, TPIO43, U3.9, U4.23, U5.6, U7.6}, I2C_SCL = {R29, TPIO44, U3.8, U4.22, U5.5, U7.5}, LED_DATA = {D5.1, IC1.2, TPIO16, U3.11}.

**ERC after task 2:** 68 violations against v7's 59. The new items are all expected until a later phase:
- 4 `label_dangling` errors: UART0_TX and UART0_RX until Phase 11's UART0 header; +3.3V_BUS (the hierarchical label and the root label) until Phase 10's power sheet drives it.
- 1 `power_pin_not_driven` error: the new IC1 VCC is power_in on +5V_TO_LEDS, which only F1 (passive) feeds. The v7 symbol didn't flag this. Phase 10 should drive or flag the rail when F1/+5V_TO_LEDS move to the power sheet.
- Some `pin_to_pin` warnings moved: they follow U3 pins onto the jumper headers.

**Left for later phases (not done here):**
- UART0 header (Phase 11).
- Test points on U3_IO43/44/16/15 and on LED_DATA (Phase 11). Root TPIO43/44 now sit on the bus side, and TPIO16 sits on LED_DATA (the row g centre), so their names are now misleading. Phase 11 should rename or keep them deliberately.
- `annotate.py` for the new parts (Phase 11).
- Renaming +3.3V to +3.3V_MCU (Phase 10).
- OQ-5 (card (j)) is still open, so the U3 pad 37 footprint was not reviewed.

**Cosmetic, optional, not a gate.** The new parts sit to the right of U3 (x 205–260 mm) on the ESP32 sheet. Header Reference/Value text overlaps the pin names. The +3.3V_BUS hierarchical label text runs past the sheet's left frame (at 15.24, 104.14). On the LED sheet, the labels at the old IC1 pin spot overlap the old footprint text. The user can tidy these in the GUI at W3 (Phase 11). After any move, re-run `python3 tools/schematic-modify/v8_mcu_sheet.py --check`; it confirms the wiring is unchanged.

**PLAN:** unchanged; the approach held and nothing was rejected. No Deferred items. Commits: `1213d24` (task 1), `282259b` (task 2), plus this notes/handoff commit.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 8 | Phase 8: Schematic — project setup and MCU sheet | DONE | Yes (step 11) — the IC1 swap was done here although no phase named it; accepted, no replan | 25ab020 | No user steps needed (all wiring by net label); commits 1213d24, 282259b, 25ab020 |

#### Verification
- TASKS.md Phase 8: all four items `[x]`. Working tree clean. Nothing under `hardware/pcb-main/` (v7) changed. PLAN.md unchanged.
- Re-ran `v8_mcu_sheet.py --check`: passes. The all-v7 jumper positions give 0 net differences against v7 `c2acffc`. In the v8 default, `/I2C_SDA` is on U3.9 (IO16), `/I2C_SCL` on U3.8 (IO15) and `/LED_DATA` on U3.11 (IO18), matching the GPIO allocation.
- Re-ran ERC at error severity: v8 has 7 errors, v7 has 0. All are the expected kinds: 6 dangling labels (+3.3V_BUS ×4, UART0_TX/RX), which Phases 10 and 11 connect, and 1 undriven power pin (IC1 VCC on +5V_TO_LEDS), which Phase 10 resolves. The Worker counted +3.3V_BUS as two labels; there are four, all the same cause.
- The IC1 swap (approved in W2 part 2) was applied in Phase 8 because it sits on row g's LED_DATA path and no later phase names it. Accepted as in-scope.
- Carried to Phase 11: rename or keep the root test points TPIO43/44/16 (they now sit on bus/LED nets); test points on U3_IO43/44/16/15; `annotate.py`. Optional label tidy at W3.

---

### Worker #9 — Phase 9: Schematic — TCA, bus and channels

**Dispatch:** standard spawn prompt, plus:
- Additional reading: SESSION.md Worker #8 Notes (the new `modify.py` helpers, `v8_mcu_sheet.py` as the pattern, references JP1–JP5/J10 taken, power spec references JP30–35/J30–33/TP10–75 reserved); `hardware/pcb-main-v8/CONTEXT.md` Jumper matrix rows b, d, f (W2 header implementations), Test points (channel), Parts (cable-facing protection, pull-up options, jumper headers); `tools/CONTEXT.md`; `tools/schematic-modify/CONTEXT.md`.
- Same rule as Phase 8: do whatever the tools can; if any user steps remain, write them as numbered KiCad instructions and return PARTIAL.

#### Notes

**Task 1: rows b, d, f and channel test points** (`tools/schematic-modify/v8_bus_sheet.py`, commit `c5241b9`). Everything is label-style; no GUI wiring was needed. The TCA sheet was wire-wired, so the script frees a pin by removing its wire (and junction) first, then labels it. New `modify.py` helpers: `remove_junction_at`, `add_local_label`, `add_wire`, `rename_hlabel`, `rename_sheet_pin`.
- **Bug fixed in `modify._compute_pin_position`:** symbols at 90/270 degrees had their pins computed at the wrong end. The X term had the wrong sign on `py*sin`. Found on J4–J6, which sit at 270. Symbols at 0/180 are unaffected, so Phase 8's output is unchanged and its check still passes. **The same bug is in `tools/schematic-gen/generate_power_sheet.py`, `generate_esp32_sheet.py` and `poc_generate.py`.** I added a Deferred item: Phase 10 must fix it before it generates the power sheet.
- **TCA sheet paper is now A3.** The v7 drawing is unchanged in place. The new parts sit in a grid below it (y 157–234) and the channel test points sit to the right (x 241–366, y 45–107).
- **Channel split (row b):** U4 SD0–SC2 now carry local labels CHn_SDA/CHn_SCL (the TCA side). The six channel hierarchical labels and the root sheet pins were renamed CHn_x_CONN and moved to x 215.9. J4–J6 stay wired to those sheet pins, so J4–J6 pins 3/4 are now on CHn_x_CONN.
- **Row b parts:** 47 Ω R80–R85 (C23182), one per line. Bypass headers JP10–JP15 sit across them (1×2, C492401). TVS U11–U13 are `Power_Protection:TPD2E2U06DRL` (the stock symbol pin map matches CONTEXT: IO1 = 3, IO2 = 5, GND = 4), with no-connects on pins 1/2; footprint SOT-553, C1972959. TVS GND-leg headers JP16–JP18 run from CHn_TVS_GND to GND.
- **Row d upstream:** R28/R29 are kept. Their bus stub and junction were removed, and pin 1 now goes to PU_SDA_2K2/PU_SCL_2K2. Their LCSC was changed C114662 → C4190 (Parts: same value, basic). JP19/JP20 are 2×3 selectors (C56153599): odd pins = bus, 2/4/6 = 2.2 k/4.7 k/10 k. The new 4.7 k R86/R88 (C23162) and 10 k R87/R89 (C25804) go to I2C_PU_RAIL. Labels I2C_SDA_IN/I2C_SCL_IN sit on the old junction points, which are on the bus wires.
- **Row d downstream:** each line has an open SJ2 (JP21–JP26, CHn_x → CHn_x_PU) and a 4.7 k (R90–R95) to I2C_PU_RAIL.
- **I2C_PU_RAIL is temporarily +3.3V.** It is a local label at R28 pin 2's +3.3V power-symbol point (139.7, 60.96). That makes the one new ERC warning: `multiple_net_names` (#PWR014 vs I2C_PU_RAIL). **Phase 10:** when the bus loads move to +3.3V_BUS (CONTEXT Power path: "+3.3V_BUS (I2C_PU_RAIL, TCA, INA219, J4–J6, BUS LED)"), retarget this one point and #PWR029/#PWR030 (R29.2/R28.2). U4.24, C9, C10 (VCC_3V3 hlabel), R6 and J4–J6 pin 1 are still on +3.3V too.
- **Row f:** JP27/JP28 (1×2) join the bus to BQ_SDA/BQ_SCL; the shunt is on in both v8 and v7. U5 pins 6/5 on the power sheet were relabelled BQ_SDA/BQ_SCL. New hierarchical labels BQ_SDA/BQ_SCL are on the TCA sheet (119.38, 83.82/88.9) and the power sheet (195.58/208.28, 189.23). Root sheet pins on both sheet symbols are joined by root labels. This matches `power_v8_spec.json`, which already has BQ_SDA/BQ_SCL as power-sheet interface pins whose row f headers are "on the bus sheet".
- **Channel test points:** TP80–TP91 (D1.5) on CHn_x and CHn_x_CONN. Each has its own ground point, TP92–TP103 (2.5×2.5, GND). Refs used: R80–R95, U11–U13, JP10–JP28, TP80–TP103. They don't collide with the power spec's reserved refs.

**Task 2: (user) steps.** None were needed. Re-extracted with `extract.py` to scratch (not committed; Phase 11 commits it with provenance). It agrees with the netlist: U5.5/6 on /BQ_SCL and /BQ_SDA, J4.3 on CH0_SDA_CONN, U4.4 on CH0_SDA, R28.1 on PU_SDA_2K2. `v8_bus_sheet.py --check` passes. It runs:
- `v8_mcu_sheet.py --check`, which now imports `v8_bus_sheet` and applies its jumper positions too. **All-v7 positions (rows a, e, g + b bypass on / TVS leg off, d 1–2, f on) vs v7 @ c2acffc: 0 nets differ.**
- 133 pin → net checks.
- Each row in both positions, with the others at the v8 default:
  - Row b v8: CH0_SDA = {U4.4, R80.1, JP10.1, JP21.1, TP80}, CH0_SDA_CONN = {J4.3, R80.2, JP10.2, U11.3, TP82}, and U11.4 on GND.
  - Row b v7: the two nets merge, and U11.4 floats with only JP16.1.
  - Row d and row f: v8 = v7 by design. The check also confirms the 4.7 k (JP19 3–4) and 10 k (JP20 5–6) selections, no shunt = no pull-up, downstream JP21 closed puts R90 on CH0_SDA, and row f open takes U5 off the bus.
- v8 default I2C_SDA: U3.9, U4.23, U5.6, U7.6, R28.1, TPIO43 plus jumper pins.

**ERC:** 69 violations vs Phase 8's 68. The I2C_PU_RAIL `multiple_net_names` warning above is the only new item. Two pin_to_pin warnings changed partners: U7 now pairs with U4 instead of U5, because U5 left the net.

**Cosmetic, for the user at W3 (not a gate):** in the new grid, label text overlaps some part reference/value text, and the CHn_x and CHn_x_CONN labels by U4 crowd each other. After any GUI move, re-run `python3 tools/schematic-modify/v8_bus_sheet.py --check`.

**Left for later:** test points for I2C_SDA/SCL, BQ_SDA/SCL and I2C_PU_RAIL, plus `annotate.py` for the new parts (Phase 11). +3.3V_BUS moves and row c (Phase 10). PLAN is unchanged, with no rejected approaches.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 9 | Phase 9: Schematic — TCA, bus and channels | DONE | Yes (step 11) — `modify.py` rotation fix and a Deferred line outside the plan; accepted, no replan | 8bebde5 | No user steps; commits c5241b9, 8bebde5 |

#### Verification
- TASKS.md Phase 9: all three items `[x]`. Working tree clean. v7 (`hardware/pcb-main/`) untouched.
- Re-ran `v8_bus_sheet.py --check`: PHASE 9 CHECK PASSED. The all-v7 jumper set (a, b, d, e, f, g) gives 0 net differences against v7 `c2acffc`, and the alternate row b/d/f settings give the expected memberships.
- ERC at error severity: still 7, the same set as Phase 8. The new I2C_PU_RAIL `multiple_net_names` item is a warning.
- The rotation fix in `modify._compute_pin_position` is a tool bug fix. Phase 8's output is unchanged: its check still passes, and it now also runs inside Phase 9's check. The same bug in the `schematic-gen` generators was logged in Deferred, but Phase 10 needs `generate_power_sheet.py`, so Phase 10 fixes it before generating. That brings it into scope, and the Deferred line is removed once it's fixed.
- Carried to Phase 10: retarget I2C_PU_RAIL and R28.2/R29.2 to +3.3V_BUS; drive +5V_TO_LEDS (IC1 VCC); connect +3.3V_BUS labels; Worker #7's "argued" checks list.

---

### Worker #10 — Phase 10: Schematic — power sheet

**Dispatch:** standard spawn prompt, plus:
- Additional reading: SESSION.md Worker #7 Notes (the power spec and the "for Phase 10" checks list), Worker #8 and #9 Notes (helpers, reserved references, BQ_SDA/BQ_SCL interface, I2C_PU_RAIL, +5V_TO_LEDS, the generator rotation bug); `hardware/pcb-main-v8/CONTEXT.md` Power path and Jumper matrix rows c, h, i, j, k, l; `tools/schematic-gen/power_v8_spec.json`, `generate_power_sheet.py`; `tools/CONTEXT.md`; `docs/references/{bq24195,tps61088,ina219}/DATASHEET_REFERENCE.md`.
- Fix the rotation bug in the `schematic-gen` generators first, and remove its TASKS Deferred line once fixed.
- Same rule as Phases 8–9 for user steps.

#### Notes

**Generator rotation bug (before anything else).** Fixed the X-term sign in `tools/schematic-gen/generate_power_sheet.py`, `generate_esp32_sheet.py` and `poc_generate.py` (same fix as `modify._compute_pin_position`; all three now agree with modify.py at 0/90/180/270). Deferred line removed from TASKS. `7c0c1ad`.

**Task 1: power sheet** (`tools/schematic-modify/v8_power_sheet.py`, `dae1935`). Modified in place, not regenerated (PLAN Rejected Approaches: the spec leaves out v7 parts such as U9, D1/R1, TP1–TP4, C7/R27). All label-style, no GUI wiring.
- Power sheet now A3; new parts gridded right of (x 305–381) and below (TPs, y 211–262) the v7 drawing. BT1/Q2/R33/R34 removed with their stubs (`modify.remove_component_with_stubs`). Battery block, rows c, h1–h3, i, j, k, l, STAT LED, U10, PMID caps, rail TPs added from `power_v8_spec.json`. v7 part values/LCSC/footprints updated per Power path "Other v7 deviations" (C22, C25, C26, C29, C30, R44, C34–C36, C42).
- **Rails, all sheets.** A power symbol's Value names its global net in KiCad 9 (tested on a scratch copy). Global +3.3V → **+3.3V_MCU** (power symbols, labels, hlabels, sheet pins). Bus loads → global **+3.3V_BUS**: TCA #PWR014 (R6), #PWR029/#PWR030 (R29/R28), root #PWR013/#PWR015/#PWR016/#PWR031 (J6, TCA VCC_3V3, J5, J4), new #PWR103 on the root J10 label, new #PWR101 on the power sheet (U7 VS, h2 side). The 11 I2C_PU_RAIL labels on the TCA sheet are renamed +3.3V_BUS (clears Phase 9's multiple_net_names). Root #PWR02 → **+5V_CORE** (ESP32 sheet +5V = D5 only); #PWR102 joins the power sheet's +5V_CORE. R6 (TCA_RESET pull-up) on +3.3V_BUS is my call (argued: TCA's own rail), recorded in CONTEXT.
- **Link h4 on the LED sheet.** v7 already has **R27 0.1 Ω 2512 (LED current sense) and C7** after F1, which the Phase 7 spec missed. Built literally: F1 → +5V_LED_F → R66 (10 mΩ, J33 DNP) → +5V_LED_H4 (C7, R27) → R27 → +5V_TO_LEDS. With h4 closed the rail = v7. **Question for the user at W3:** keep R66, or drop it and put J33 across R27 (which already reads 100 mV/A)? Not a gate.
- PWR_FLAGs added: #FLG101 (+5V_TO_LEDS; clears the IC1 power_pin_not_driven from Phase 8), #FLG102 (+5V), #FLG103 (+3.3V_MCU). Those two had lost root FLG01/FLG03 to +5V_CORE/+3.3V_BUS.
- J7: new v8 footprint `motion-play-v8:USB-C_SMD-TYPE-C-31-M-12_ShellGND` (`hardware/pcb-main-v8/kicad/libraries/footprints/motion-play-v8.pretty`, row added to the v8 `fp-lib-table`), the v7 footprint with shell legs 1–4 renumbered "0" = the symbol's SH pin on GND. Explains v7's netless shell legs.
- Refs used: J8, J9, F3, Q20, Q21, R60–R66, C60–C70, SW4, U10, D10, JP30–JP35, J30–J33, TP10, TP12, TP13, TP15, TP17–TP36, TP50–TP76, #PWR101–103, #FLG101–103. Spec updated (`_note_phase10`): 138 parts.

**Argued checks** (CONTEXT Power path → "Phase 10 checks"; none changes an approved decision):
- Confirmed: gate network (SLPS454B: VGS(th) −0.65 min, kick Vgs ≈ −0.42 V at 4.2 V, ramp 1.6–2.8 V/ms → 0.65–1.1 A); AP2112K EN (VIH 1.5 V min, VIL 0.4 V); F3 (listing 300 A DC breaking); over-discharge (SLUSB97A VBAT_DPL 2.4–2.6 V falling; not designed further).
- Value changed: AMS1117 margin 0.4 V (1.3 V max dropout); 0 Ω links rated 2 A (UNI-ROYAL table) → h3 margin 1.2× on the sum of ratings; PMID 6 × 22 µF (C69, C70 added; DC-bias curve not readable, ≈ 50 % retention argued).
- Pin map changed: **J8 pin 2 = BAT_CONN (+), pin 1 = GND.** The stock XT30UPB-M footprint's silk marks pad 2 "+"; the Phase 7 spec had it reversed.
- New residual (argued): SW4 OFF under load drives the pair slowly through the linear region (τ ≈ 0.24 s). For the bring-up relay.
- CSD25402Q3A pinout re-checked from the datasheet text (label counts 3 D / 1 G / 5 S): D 1–3, G 4, S 5–8 + pad, as the KiCad symbol.

**Task 2: no (user) steps.** Re-extracted with `extract.py` to scratch (not committed; Phase 11 commits with provenance): 324 power pins match. `python3 tools/schematic-modify/v8_power_sheet.py --check` passes: Phase 8 + 9 checks, 324 pin → net checks, and 18 row facts (c v8/v7/no shunt, h1 and h4 lifted, h3, i, j, k, l both positions, battery, U10 EN). **All-v7 positions vs v7 @ c2acffc: 0 nets differ**, with the battery exception explicit: `v8_mcu_sheet.later_phases()` now returns a v7-side drop/short pair; BT1/Q2/R33/R34 are dropped from the v7 netlist with Q2 conducting, and F3/Q20/Q21 are shorted (SW4 ON) and dropped on v8. It prints the dropped v7 parts. Also updated: `v8_bus_sheet.py` and `v8_mcu_sheet.py` expectations now say +3.3V_BUS where they said +3.3V / /+3.3V_BUS. The check prints every power net's v8-default membership.

**ERC:** 66 violations (Phase 9: 69). Errors: 2, both `label_dangling` UART0_TX/RX (Phase 11's UART0 header). Warnings: 58 pin_to_pin (as before), 2 lib_symbol_issues (as before), 1 unconnected_wire_endpoint (a 0.1 mm wire on SW1 pin 1 at (222.25, 24.13), already in the v7-derived sheet), and 3 new **lib_symbol_mismatch** on Q20, Q21, U10 (the cached stock symbol differs from the library copy; "Update symbols from library" at W3 clears it, then re-run `--check`).

**Cosmetic, for W3 (not a gate):** the new parts sit in grids; labels on TP stubs run downward. After any GUI move, re-run `python3 tools/schematic-modify/v8_power_sheet.py --check`.

**Left for later:** I2C_PU_RAIL has no separate test point any more (it is +3.3V_BUS; TP28 covers it) — Phase 11's I²C test-point list should read it that way. Rail LEDs for +3.3V_BUS, +5V, Protected_VBUS and their SJ2s; `annotate.py`; committed `circuit-context.json` (Phase 11). Phase 12: LED brightness cap on battery (unchanged). PLAN: one Rejected Approaches line (regenerating the power sheet). No Deferred items.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 10 | Phase 10: Schematic — power sheet | DONE | No — clean completion; the argued checks changed values only, no approved decision | 7170088 | No user steps; commits 7c0c1ad, dae1935, 7170088 |

#### Verification
- TASKS.md Phase 10: all three items `[x]`; the rotation-bug Deferred line is removed (fixed in `7c0c1ad`). Working tree clean. v7 untouched.
- Re-ran `v8_power_sheet.py --check`: PHASE 10 CHECK PASSED (it chains the Phase 8 and 9 checks). With every jumper in its v7 position, 0 nets differ against v7; the battery-protection exception is modelled explicitly (dropped parts printed).
- ERC at error severity: 2 (UART0_TX/RX dangling, for Phase 11), down from 7.
- PLAN: one Rejected Approaches line (regenerating the power sheet from the spec, which would drop v7 parts); approach unchanged.
- The J7 shell-to-GND footprint is a v8-local library copy. The v7 library and footprint are untouched. This implements the approved "USB shell on GND" (Phase 7 point 8).
- Changed values (AMS1117 margin 0.4 V, 0 Ω links rated 2 A, PMID 6 × 22 µF, J8 pin 2 = +) are recorded in CONTEXT "Phase 10 checks". Each is a value inside an approved decision.
- For the user at W3 (end of Phase 11): keep R66 (10 mΩ, link h4) or drop it and read the LED-rail current across v7's existing R27 (0.1 Ω). The SW4-off-under-load linear-region risk goes into the Phase 19 bring-up relay.

---

### Worker #11 — Phase 11: Schematic — debug features, ERC, freeze

**Dispatch:** standard spawn prompt, plus:
- Additional reading: SESSION.md Worker #8, #9 and #10 Notes (Phase 11 carry-forwards: UART0 header; rail LEDs and their SJ2s; TPIO43/44/16 naming; test points on U3_IO43/44/16/15; `annotate.py`; `circuit-context.json` with `_provenance`; the label tidy); `hardware/pcb-main-v8/CONTEXT.md` (Test points, Debug LEDs, Parts, Jumper matrix); `tools/CONTEXT.md` (Source-Hash Rule; schematic-context `extract.py`/`annotate.py`).
- W3 (task 4) is a user gate. The Worker prepares the review guide (what to look at in KiCad, open choices including R66 vs R27, the optional cosmetic tidy), commits, and returns PARTIAL. The Orchestrator relays it. The freeze tag comes after the user's fixes.

#### Notes

**Task 1: debug features** (`tools/schematic-modify/v8_debug_sheet.py`, `80036ff`). Every edit is label-style, so there was no GUI wiring.
- **Test-point naming (carry-forward from Worker #8): renamed.** On v8, `TPIO<n>` always means GPIO n's own pad. v7's root TPIO43/44/16 sat on I2C_SDA, I2C_SCL and LED_DATA, which on v8 are no longer those pins' nets. They are now **TP110 (I2C_SDA), TP111 (I2C_SCL) and TP112 (LED_DATA)**, with the value set to the net name.
  - The new TPIO43/44/16/15 sit on U3_IO43/44/16/15, the U3 side of row a. In row a's v7 position (shunt 2–3), TPIO43 and TP110 are on one net, as v7's TPIO43 was.
  - The v7 comparison maps v7 TPIO43/44/16 to TP110/111/112 (`v8_debug_sheet.V7_REF_RENAME`, applied in `v8_mcu_sheet.check`).
  - TPIO10 and TPIO21 keep their names: they are still on GPIO10 and GPIO21's nets.
- **New signal points:** TPIO0 (GPIO0_BOOT), TP113 (EN), TPIO13/12/11 (INT1–3), TPIO3/45/46 (strap pads, D1.0 mm, value "STRAP …"), and TP114/TP115 (BQ_SDA/BQ_SCL, on the TCA sheet). Each has its own GND point, TP130–TP148. TP144–TP148 are on the root sheet and serve TP110–112, TPIO10 and TPIO21.
- I2C_PU_RAIL is +3.3V_BUS, so TP28 covers it (as Worker #10 noted). No separate point.
- **Headers:**
  - J11 is the UART0 header: GND, UART0_TX, UART0_RX, and NC (no-connect flag). It clears the last 2 ERC errors.
  - J12 is the 2 × 15 spare-GPIO header (C22465939). Odd pins = GPIO1, 2, 4–9, 14, 17, 38–42 (U3 pins checked against the symbol's pin names); even pins = GND.
- **LEDs:**
  - D11 green BUS on +3.3V_BUS (R100 1 k C21190), D12 yellow on +5V (R101 3.3 k C22978) and D13 red on Protected_VBUS (R102 3.3 k). Each chain is rail → factory-bridged SJ2 (JP41–43) → R → LED → GND.
  - D1 kept: R1 pin 2 now goes through JP40 (bridged SJ2) to +3.3V_MCU.
  - D14 blue DBG1 on GPIO47 and D15 white DBG2 on GPIO48, each with a 470 Ω resistor (C23179).
  - The LED part numbers follow CONTEXT Parts.
- **Jumper positions:** JP40–43 are closed by default. In the v7 position JP40 stays closed (v7 had D1) and JP41–43 are cut (v7 had none of those LEDs).
- **Placement:** the ESP32 sheet paper is now A3. The new parts sit in a grid below the v7 drawing (y 172–255). On the power sheet the LEDs are at x 289–356, y 233–270. On the TCA sheet, TP114/115 are at y 259; on the root sheet the GND points are at y 145.
- **Check-chain changes:**
  - `v8_mcu_sheet.later_phases()` now imports `v8_debug_sheet`.
  - A new `later_extras()` gives the U3 pins used by later phases (its unused-pin list skips them) and the ref renames.
  - `v8_power_sheet.expected()` no longer expects R1.2 on +3.3V_MCU. Phase 11 checks R1.2 = LED_D1_SJ, and that closing JP40 joins it to +3.3V_MCU.
- `hardware/pcb-main-v8/CONTEXT.md` has a new paragraph, Test points → "As built (Phase 11)".

**Task 2: ERC, annotation, context** (`ccc726c`, `dbad731`).
- **ERC: 0 errors, 87 warnings.** Waivers, each with its reason:
  - 81 `pin_to_pin`: every one is "Pins of type **Unspecified** and …". The JLC-MCP library symbols (U3, U5, U6, U8 …) declare their pins Unspecified, so every connection to them warns. v7 had the same class (58). Phase 11 adds 23, from the new J12, test point and LED connections to U3 pins. No electrical meaning.
  - 3 `lib_symbol_mismatch` (Q20, Q21, U10): the cached symbol differs from the library copy. "Update symbols from library" at W3 clears them.
  - 2 `lib_symbol_issues` (J7, U5): v7 project symbol libraries aren't in the lib table. Carried from v7, and the symbols are cached.
  - 1 `unconnected_wire_endpoint`: a 0.1 mm wire on SW1 pin 1 at (222.25, 24.13), carried from the v7 sheet. Cosmetic; it can be deleted at W3.
- **BOM audit (in `--check`):** all 293 parts have a footprint. Every part has an LCSC number except the copper-only ones (test points, solder jumpers). The headers carry LCSC numbers but are hand-fit (CONTEXT Parts → Headers).
- **Annotation:** `v8_debug_sheet.py --annotate` writes `ai_function/block/role/critical_specs` on 225 parts through `annotate.write_ai_properties`. That covers every part Phases 8–11 added, plus the v7 parts Phase 10 changed (C22, C25, C26, C29, C30, R44, C34–36, C42, SW1, J7, R28/R29); their stale v7 text is replaced.
  - Coverage is 274/293. The 19 unannotated parts are v7 parts that were never annotated on v7 either (U3, U8, U9, MCU passives, SW2/3, D1, D5, R1, C43).
  - Block names follow `power_v8_spec.json` (charger, battery, boost, regulators, links, test_points …) and new ones (i2c_channels, i2c_pullups, i2c_bus, i2c_master_select, led_data_select, debug_leds, debug_headers). The 48 older v7 annotations still use v7's vocabulary (battery_mgmt, boost_5v, usb_c_input), so Phase 13's group rules should map the two vocabularies.
- **`circuit-context.json`** is committed at `hardware/pcb-main-v8/kicad/` with `_provenance`. `extract.py` now writes `source` (the root sheet) plus `sources` (each child sheet → sha256). `tools/lab/check_state.py --fresh` now also checks `sources`, so an edit to any sheet marks the file stale. It reports FRESH and the generator commit is clean. Re-extract after the W3 edits. The `tools/CONTEXT.md` Source-Hash scope line is updated.

**Task 3: audit against `hardware/pcb-main-v8/CONTEXT.md`.** Source: the committed `circuit-context.json` and `v8_debug_sheet.py --check` (which chains the Phase 8–10 checks).
- **Jumper rows a–l:** all present.
  - a: JP1, JP2. b: JP10–18, R80–85, U11–13. c: JP30, U10. d: JP19/20, R28/29/86–89, JP21–26, R90–95. e: J10, JP3/4. f: JP27/28. g: JP5. h: R63–R66 with J30–J33. i: JP31. j: JP32/33. k: JP34. l: JP35, J9.
- **Test points:** every net in CONTEXT Test points has one.
  - I²C master side: TP110/111, TPIO43/44/16/15, TP114/115, +3.3V_BUS (TP28).
  - Channels: all 12 (TP80–91).
  - Rails: VBUS_RAW, Protected_VBUS, PMID, REGN, VSYS, VSYS_SENSE, VBAT, BAT_FUSED, BAT_COMMON, +5V, +5V_CORE, +5V_LED_F/H4, +5V_TO_LEDS, +3.3V_MCU(_REG), +3.3V_BUS_REG/HDR. Each row h link has a point on both sides.
  - Control nodes: BOOST_EN/VCC/FB, BAT_GATE, OTG_BIAS, BQ_TS, BQ_ILIM, BQ_STAT.
  - MCU: EN, GPIO0, TCA_RESET, CHRG_INT, LED_DATA, INT1–3, straps 3/45/46.
  - **58 signal points, 58 GND points**: one each, with TP4 being v7's own GND pad. The headers have a GND pin beside their signal pins.
  - BAT_RAW is now split into BAT_CONN / BAT_FUSED / BAT_COMMON. BAT_CONN (at J8, before F3) has no point, per the Phase 10 spec. W3 can add one if wanted.
- **LEDs:** all 8 in the CONTEXT table are present: D1, BUS (D11), +5V (D12), VBUS (D13), STAT (D10), DBG1 (D14), DBG2 (D15), D5. The 4 rail LEDs have their default-closed SJ2s (JP40–43).
- **v7 positions:** with every jumper in its v7 position, the netlist matches v7 @ `c2acffc`: **0 nets differ**. The battery-protection exception is modelled as before: BT1/Q2/R33/R34 are dropped with Q2 conducting, and F3/Q20/Q21 are shorted. The row checks pass for each row's v8 and v7 positions (Phase 9: b, d, f; Phase 10: c, h, i, j, k, l; Phase 11: LED SJs, row a with J11).
- **Not checked here:** physical spacing between each test point and its GND point is a layout item (Phase 13 rules).

**W3 review guide (task 4, user gate).** Open `hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_pro` in KiCad 9. KiCad must be closed whenever a script runs.
1. **Root sheet:** check that TP110/TP111/TP112 (renamed from TPIO43/44/16) read as you want. The alternative is to keep the v7 names, with the cost that "TPIO43" would then not be GPIO43's pad. The GND points TP144–148 sit below the drawing.
2. **ESP32_S3 sheet (now A3):**
   - Row a headers JP1/JP2 and the UART0 header J11 (pin order GND/TX/RX/NC; TX = ESP output, so it goes to an adapter's RX).
   - J12 spare-GPIO pin order.
   - DBG LEDs D14/D15.
   - The test-point grid below the drawing, including the strap pads TPIO3/45/46 with GND points. These are strap pins: confirm a GND pad beside them is wanted; it is harmless.
3. **TCA9548A sheet:** row b/d/f grid (Worker #9), TP114/115 at the bottom.
4. **Power sheet:** the battery block, rows c/h/i/j/k/l, and the rail LEDs D11–D13 with JP41–43, plus JP40 for D1 (lower right).
5. **LED controller sheet:** IC1 (SOT-23-5), and link h4 with R66/J33 and R27.

Open choices:
- **R66 vs R27 (Worker #10):** keep R66 (10 mΩ, link h4, reads 10 mV/A across J33), or drop R66 and put J33 across v7's existing R27 (0.1 Ω, reads 100 mV/A, already in v7's path). Dropping R66 removes a part, and the v7 rail stays exactly v7 (no added 10 mΩ). The cost: J33 then can't be lifted to insert an ammeter without lifting R27.
- Optional: a test point on BAT_CONN (before F3).
- Optional: the LED currents (≈ 1 mA targets, resistors swappable).

**Required, not optional:** run "Tools → Update Symbols from Library" for Q20, Q21 and U10. It clears the 3 lib_symbol_mismatch warnings.

Cosmetic tidy (optional, not a gate):
- Text overlaps in the new grids on all sheets (labels against reference/value text; the CHn_x labels by U4).
- The +3.3V_BUS hierarchical label past the ESP32 sheet's left frame.
- The old IC1-position labels on the LED sheet.
- The 0.1 mm stray wire on SW1 pin 1 (power sheet).

After any edit, close KiCad and run `python3 tools/schematic-modify/v8_debug_sheet.py --check`. It runs the Phase 8–11 checks, the BOM audit and ERC, and must end PHASE 11 CHECK PASSED. Then re-extract: `python3 tools/schematic-context/extract.py hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_sch` and `python3 tools/lab/check_state.py --fresh hardware/pcb-main-v8/kicad/circuit-context.json`. After that comes the freeze tag (the Orchestrator's next Worker).

**PLAN:** unchanged, no rejected approaches. No Deferred items. Tasks 1–3 are `[x]`; task 4 (W3) and the Handoff are left open. Commits: `80036ff`, `ccc726c`, `dbad731`, plus this notes commit.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 11 | Phase 11: Schematic — debug features, ERC, freeze | PARTIAL | Yes — resolvable without replanning: the stop is the planned user gate (W3) | 2fb7e21 | Tasks 1–3 done; task 4 (W3, freeze tag) and Handoff await the user |

#### Verification
- TASKS.md Phase 11: tasks 1–3 `[x]`; task 4 and Handoff `[ ]`. Working tree clean. Nothing in `lab/` or v7 `hardware/pcb-main/` changed.
- Re-ran `v8_debug_sheet.py --check` (it chains Phases 8–10): PHASE 11 CHECK PASSED. With every jumper in its v7 position, 0 nets differ against v7.
- ERC at error severity: 0. `check_state.py --fresh` on the v8 `circuit-context.json`: FRESH (root plus 4 child sheets).
- Tooling changed outside the schematic scripts, both needed for task 2's provenance: `extract.py` now writes per-sheet hashes; `tools/lab/check_state.py --fresh` checks them (this is the tool, not `lab/`). Accepted.
- The worker ran about 2 h 50 min, against the usual 10–20 min. It ended normally and committed throughout. The Orchestrator's check-in arrived after it had finished.
- Loop paused for the user: W3 schematic review in KiCad (guide in Worker #11 Notes).

---

### Replan — schematic readability (2026-11-04)

The user opened the schematic for W3 and found it unreadable. The Orchestrator sent two read-only researchers (reports: `docs/research/kicad-ai-tooling-2026-11/`). Cause: kiutils 1.4.8 drops KiCad 9 `(hide yes)` on any load/save, which left 536 extra visible fields and 1,616 overlapping text pairs. User decisions: fix the tooling and tidy, then look before any re-layout (OQ-10 at W3a); keep R66; add the BAT_CONN test point (Orchestrator's call); LED currents unchanged. Planner inserted Phases 11a–11f (`d041e70`); W3 moved to 11f. Planner flag for the user: the 11e tour goes in `hardware/pcb-main-v8/REVIEW-GUIDE.md` (a new file, outside the prescribed documents).

---

### Worker #12 — Phase 11a: Schematic tooling — kiutils KiCad 9 shim and field tidy

**Dispatch:**
```
Initiative: v8-debug-board
Phase: 11a — Schematic tooling — kiutils KiCad 9 shim and field tidy
Initiative path: docs/initiatives/v8-debug-board/
Additional reading: docs/research/kicad-ai-tooling-2026-11/schematic-readability.md (and its prototypes/ folder); PLAN.md Technical Notes "Schematic readability"; SESSION.md "Replan — schematic readability (2026-11-04)" and Worker #11 Notes; .context/HAZARDS.md kiutils entry.

Tasks assigned (from TASKS.md Phase 11a):
## Phase 11a: Schematic tooling — kiutils KiCad 9 shim and field tidy

- [~] KiCad 8/9 shim for kiutils 1.4.8 (readability §3.1 step 1; prototype `prototypes/kiutils_k9_shim.py`): a module in `tools/schematic-modify/` that reads `(hide yes)` on effects and properties, and on `pin_numbers`/`pin_names`. Import it on every schematic load path: `modify.load_project`/`SheetDoc`, `tools/schematic-context/{annotate,extract,show}.py`, `v8_project_setup.py`, `v8_mcu_sheet.py`, and the `tools/schematic-gen/` generators (grep for `from_file`). `SheetDoc.save_all` (and any other schematic save, including annotate's) refuses while a `~*.kicad_sch.lck` exists in the project folder. Test in scratch: a load/save round trip of v7's three `c2acffc` sheets keeps every field's visibility and every pin_numbers/pin_names hide (readability §1.2: 496/99/49 flags). Report whether `fields_autoplaced` and `exclude_from_sim` are still dropped (readability §1.2, "Other things"); preserve `fields_autoplaced` if it is cheap. **Nothing else touches the v8 schematic before this lands.**
- [ ] `annotate.write_ai_properties` (`annotate.py:134`): a new `ai_*` property takes its symbol's position and is hidden. Updating an existing `ai_*` also hides it and moves it to the symbol (readability §3.4)
- [ ] `tools/schematic-modify/tidy_fields.py --check | --apply` (readability §3.1 steps 2–4; prototype `prototypes/hide_fields.py`): hide every placed-symbol field except Reference and Value; restore `pin_numbers`/`pin_names` hiding on embedded library symbols (from v7 `c2acffc` for the same `lib_id`, else from the source library); move every `ai_*` field to its symbol's position. `--check` prints per-sheet counts and writes nothing
- [ ] Apply to v8. Gate, before vs after: `kicad-cli sch export netlist` identical (apart from library `uri` paths); `v8_debug_sheet.py --check` ends PHASE 11 CHECK PASSED; ERC 0 errors. Log per-sheet counts (fields hidden, pin flags restored, `ai_*` moved, off-sheet text left) in SESSION.md. Re-extract `circuit-context.json` (`extract.py --previous`) and confirm `check_state.py --fresh`
- [ ] Check, don't fix: does a kiutils `Board` round trip of a KiCad 9 `.kicad_pcb` (scratch copies of v7 and v8) drop `(hide yes)` or other flags the same way? Record the answer under OQ-11 in PLAN (Phase 13's `place.py` writes boards with kiutils)
- [ ] Write the rule in `tools/schematic-modify/CONTEXT.md` and `tools/CONTEXT.md`: every kiutils schematic load goes through the shim, and no write while KiCad has the project open. Point the `.context/HAZARDS.md` kiutils entry at the shim
- [ ] 🔄 Handoff

The first task is marked `[~]` because it was dispatched to you — it is not someone else's work in progress.

Phase-specific notes: KiCad is closed (no ~*.lck when checked). Check again before any schematic write. The shim must land before any script writes a v8 sheet.

You are not the Orchestrator. Do not create documents, work across phases, or replan.
Return DONE, PARTIAL, or BLOCKED with specifics.
```

#### Notes

**Task 1: shim and save guard** (`6a5325b`). `tools/schematic-modify/kiutils_k9.py` patches kiutils on import: `Effects`, `Property` (property-level `(hide yes)`), `Symbol` (`pin_numbers`/`pin_names`) and `SymbolPin`. It also gives `save_schematic` / `assert_not_open`, which raise `KiCadOpenError` while a `~*.kicad_sch.lck` is in the project folder.
- Imported on every load path: `modify.py` (so every `v8_*.py` and `esp32_integration*.py`), explicitly in `v8_mcu_sheet.py` and `v8_project_setup.py`, `tools/schematic-context/{annotate,extract,show}.py`, and `tools/schematic-gen/{generate_esp32_sheet,generate_power_sheet,poc_generate}.py`. Every schematic `to_file` in those now goes through `save_schematic`; `ProjectDocs.save_all` checks the lock once up front. Board saves in `v8_project_setup.py` are untouched.
- **Round trip, v7 `c2acffc`, all five sheets** (scratch): hidden items kept item by item (power 496, MCU 99, TCA 49, LED 77, root 194; 0 lost, 0 gained); a second round trip is stable. Without the shim, all are lost. Netlist identical (only the scratch path differs); plotted strings per sheet identical (389/102/624/248/165).
- **`fields_autoplaced`: preserved** (9 → 9 across v7; kiutils reads `(fields_autoplaced yes)` and writes the bare form). Readability §1.2's "3 → 0" counted the `yes` form only. **`exclude_from_sim`: still dropped** (211 → 0), harmless: every one in v7 is `(exclude_from_sim no)`, the default. Not shimmed.
- Lock guard tested on a scratch copy: refuses with a lock file, saves without one. v8 shim load + save in scratch left the flags unchanged.

**Task 2: annotate** (`c53d152`). `write_ai_properties` creates new `ai_*` at the symbol's position, hidden. When it touches an existing `ai_*` it also hides it and moves it to the symbol (logged as "re-homed"). It only touches the keys it writes; `tidy_fields.py` handles the rest.

**Task 3: `tidy_fields.py`** (`8001cc8`). `--check` / `--apply` (mutually exclusive, one required), `--root` (default v8), `--ref-commit c2acffc`, `--ref-dir`, `-v` lists each pin-flag restore. Library fallback: project `sym-lib-table`, then KiCad's stock symbol folder. It only sets hide flags and moves fields, so it can't change a net.

**Task 4: tidy applied to v8** (`tidy_fields.py --apply`; KiCad closed, no `~*.lck`, no KiCad process). Per-sheet counts:

| Sheet | Fields hidden | pin_numbers restored | pin_names restored | `ai_*` moved to symbol | Off-sheet text left | Overlap pairs (probe) before → after | Plotted strings before → after |
|---|---|---|---|---|---|---|---|
| Root `motion-play-main-v8` | 125 | 16 | 18 | 56 | 0 | 170 → 4 | 568 → 270 |
| MCU `esp32_s3` | 84 | 3 | 11 | 172 | 0 | 109 → 3 | 923 → 496 |
| LED `led_controller` | 51 | 5 | 9 | 52 | 0 | 158 → 4 | 256 → 133 |
| Power `power_management` | 429 | 8 | 19 | 562 | 0 | 724 → 60 | 2448 → 1117 |
| TCA `tca9548A_subsystem` | 74 | 2 | 5 | 288 | 0 | 455 → 40 | 814 → 510 |
| **Total** | **763** | **34** | **62** | **1130** | **0** | **1,616 → 111** | |

- "Fields hidden" includes empty and `~` fields, so it is above readability's 536 "extra visible" count. After the tidy the probe finds no visible field other than Reference/Value on any sheet, and no field at the origin.
- Pin flags came from v7 `c2acffc` for the same `lib_id` where v7 had it, else from the source library (`Jumper:SolderJumper_*`, `Connector_Generic:Conn_01x02`/`Conn_02x03`/`Conn_02x15`, `Transistor_FET:CSD25402Q3A`). Every embedded symbol found a source. `tidy_fields.py --check -v` lists each one.
- "Moved" counts every `ai_*` not already at its symbol's origin, hidden or not.
- A second `--check` after the apply reports 0 everywhere (idempotent).
- **Gate:** `kicad-cli sch export netlist` before vs after differs only in the `(date …)` line (not even `uri`, since it is the same folder). `v8_debug_sheet.py --check`: PHASE 11 CHECK PASSED. ERC 0 errors (warnings unchanged: 81 pin_to_pin, 3 lib_symbol_mismatch, 2 lib_symbol_issues, 1 unconnected_wire_endpoint).
- `circuit-context.json` re-extracted with `--previous` ("No structural changes"; only the sheet hashes, generator commit and timestamps changed). `check_state.py --fresh`: FRESH.
- Overlap and plotted-string counts are from `prototypes/probe.py` (pass a mode word first: `probe.py x <sheets>`; its first argument is a mode, not a file) and `kicad-cli sch export svg`. They match readability's 111 after-hide estimate, which is the starting point for 11b's baseline.

**Task 5: kiutils `Board` round trip (OQ-11, check only)** (`96843bf`). Scratch copies of v7 (`c2acffc`) and v8. v7: footprint properties come back in KiCad 7 form (key + value only), so 793 `(hide yes)` and every footprint field's position/layer/effects are lost; also `(locked yes)` on 18 footprints, `(free yes)` on 19 vias, all `uuid`s (as `tstamp`), `sheetname`/`sheetfile`, plot settings. **kicad-cli 9.0.4 can't load the result** ("Failed to load board"; DRC exit 3). v8's board (outline only) is unchanged by a round trip. Recorded under OQ-11 in PLAN (struck as answered; the write-path choice for `place.py` stays with Phase 13 / OQ-3).

**Task 6: rules** (`efcb6ca`). `tools/schematic-modify/CONTEXT.md` has a new "Rule" section and lists `kiutils_k9.py` and `tidy_fields.py`. `tools/CONTEXT.md` has a "kiutils Rule" section after the Critical Rule, two table rows, and the Dependencies line. The `.context/HAZARDS.md` kiutils entry names `kiutils_k9` and `save_schematic`, and warns that boards have no shim.

**For 11b onwards:**
- New scripts: import `modify` (or `kiutils_k9`) before any kiutils load, and save through `save_all` / `save_schematic`.
- Scratch test scripts (not committed): `scratchpad/tests/roundtrip.py` (per-item hide comparison) and `scratchpad/tests/board_rt.py`.
- Readability's `fields_autoplaced` "dropped" finding was wrong for symbols (see Task 1), so 11b's `(fields_autoplaced yes)` from `add_component` will survive later loads.

**PLAN:** OQ-11 answered. Approach unchanged; no rejected approaches. No Deferred items. Commits: `6a5325b`, `c53d152`, `8001cc8`, `dec1e37`, `96843bf`, `efcb6ca`, plus this handoff commit.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 12 | Phase 11a: kiutils KiCad 9 shim and field tidy | DONE | No — clean completion | 79af3de | 6 tasks + handoff; overlap pairs 1,616 → 111 |

#### Verification
- Re-derived: 7/7 Phase 11a boxes checked; working tree clean; no `~*.lck`. `v8_debug_sheet.py --check`: PHASE 11 CHECK PASSED. `tidy_fields.py --check`: all zeros, so the tidy is idempotent. ERC at error severity: 0 violations. `check_state.py --fresh`: FRESH (root plus 4 sheets). PLAN has no date-stamped headings.
- Carry forward to Phase 13: OQ-11 is answered "yes, and worse". A kiutils save of a KiCad 9 board drops footprint field state and kicad-cli 9.0.4 can't load the result. `place.py` (Phase 13, task 2) can't write boards via kiutils as planned. Send a Planner request (with OQ-3) before dispatching Phase 13.

---

### Worker #13 — Phase 11b: Schematic tooling — layout check and placement rules

**Dispatch:**
```
Initiative: v8-debug-board
Phase: 11b — Schematic tooling — layout check and placement rules
Initiative path: docs/initiatives/v8-debug-board/
Additional reading: docs/research/kicad-ai-tooling-2026-11/schematic-readability.md (§1.1 method, §3.4) and prototypes/probe.py; SESSION.md Worker #12 Notes (probe.py argument quirk; per-sheet counts after the tidy).

Tasks assigned (from TASKS.md Phase 11b):
## Phase 11b: Schematic tooling — layout check and placement rules

- [~] `tools/schematic-modify/layout_check.py` (readability §1.1 method and §3.4; prototype `prototypes/probe.py`). Per sheet, it fails on: (1) a visible field other than Reference/Value on a non-power symbol; (2) any text or symbol outside the paper; (3) text-overlap pairs above a committed per-sheet baseline; (4) identical labels stacked on one point, above the baseline. The baseline only ratchets down: a lower count is reported, and `--update-baseline` records it. It prints the worst spots by sheet grid zone (e.g. "C3"). Record the baseline from the tidied v8 (readability expects about 111 overlap pairs by the prototype's count, 6 stacked labels on power)
- [ ] Wire it into the end of `v8_debug_sheet.py --check`, so the whole v8 check chain (Phases 8–11) runs it. The chain passes
- [ ] Placement rules in `modify.py` (readability §3.4 rows 2–3). `add_component` places Reference/Value at the library symbol's own field offsets, rotated with the symbol, and writes `(fields_autoplaced yes)`. `_make_local_label`/`_label_angle`: on a vertical stub, prefer a horizontal label justified away from the part. `WIRE_STUB_LEN` default 5.08 mm, with a per-call `stub_len`. Existing parts are not moved. Test on a scratch copy: a vertical two-pin part and a test point, each with labels, add 0 overlaps by `layout_check.py`
- [ ] Record in `tools/schematic-modify/CONTEXT.md`: the placement rules, `layout_check.py` as part of every `--check`, and the grid rule for future generator scripts (row pitch from the longest label or value, about 0.75 × 1.27 mm per character + 2.54 mm; 1.27 mm grid snap; inside the frame with a margin from the title block). The already-run v8 phase scripts are not re-run
- [ ] 🔄 Handoff

The first task is marked `[~]` because it was dispatched to you — it is not someone else's work in progress.

Phase-specific notes: every schematic load/save goes through tools/schematic-modify/kiutils_k9.py (Phase 11a). KiCad must be closed during any write.

You are not the Orchestrator. Do not create documents, work across phases, or replan.
Return DONE, PARTIAL, or BLOCKED with specifics.
```

#### Notes

**Task 1: `layout_check.py`** (`ebca71c`). Read-only; parses raw s-expressions (no kiutils model, so no shim needed). `run(root)` returns the failure count; CLI `--root`, `--update-baseline`, `--worst N`, `-v` (every pair and stack). Baseline in `tools/schematic-modify/layout_baseline.json`, keyed by repo-relative sheet path. `--update-baseline` lowers counts and records a sheet's first baseline. It never raises one (tested with a doctored baseline: above → BAD and "not raised"; below → reported, then lowered). Rules 1 and 2 were exercised on v7 `c2acffc` (scratch): it flags IC1's Mouser fields, R52/R53's visible `ai_*`, and the off-paper `ai_*` anchors.
- **Geometry differs from the prototype, on purpose.** I compared every modelled text box with the strings kicad-cli 9.0.4 actually plots (stroked-text paths in the SVG). Three corrections came out of it: (a) a symbol field's angle and justification are in the symbol's frame and turn with the symbol; (b) characters are about 0.85 × the text height wide (median of 1,149 plotted strings), not 0.72; (c) **a label written without a `justify` is drawn centred on its anchor, across the wire end.** Every label `modify.py` wrote before this phase is like that. Sheet pins and sheet name/file text on the root are now counted too. Result: 141 modelled pairs vs 143 from the plotted boxes, and every field box matches its plotted string.
- **v8 baseline** (recorded from the tidied v8): root 13, MCU 22, LED 5, power 51, TCA 50 overlap pairs (141 in all; the prototype counted 111). Stacked labels: power 6 (2 stacks of 3: `BAT_FUSED` and `VBAT` at x 307.34, zone B6), 0 elsewhere. Readability's "6" counted labels, so the check counts labels in stacks, not extra copies. Visible extra fields 0 and off-paper 0 on every sheet. The worst zones are mostly GND test points' Value sitting on their own GND label (MCU D3–D5, power E1, root C2) and the TCA 47 Ω values on the `CHn_*_CONN` labels.

**Task 2** (`4cd4a66`). `v8_debug_sheet.check()` calls `layout_check.run(ROOT)` after the ERC summary. The full chain passes: CHECK PASSED (Phase 8), PHASE 9/10 CHECK PASSED, LAYOUT CHECK PASSED, PHASE 11 CHECK PASSED.

**Task 3: placement rules** (`ac45077`). `add_component` places Reference/Value at the library field offsets (position turned with the symbol; library angle, justify and font kept) and sets `fieldsAutoplaced`. Labels are always horizontal. On a vertical stub the label runs right of the wire (left if the pin is left of the symbol origin). Every label now carries KiCad's justify (0/90 left bottom, 180/270 right bottom). `WIRE_STUB_LEN` is 5.08, with `stub_len=` on `add_component` and `set_pin_net`. `v8_mcu_sheet`/`v8_bus_sheet` use `modify.WIRE_STUB_LEN` only in their one-shot `apply()` paths, which are not re-run.
- Scratch test (`scratchpad/tests/place_test.py`, v8 copy, LED sheet at (30.48, 177.8)): vertical Device:R with a label on each pin, Connector:TestPoint with a label, and a horizontal R at 90°. **0 overlap pairs added** (5 → 5, by the model and by the plotted SVG boxes), 0 stacked, 0 visible extra, 0 off paper. The same placement with the pre-11b `modify.py` adds 1 (R900's Value on its `TEST_NET_A` label). The rendered PNG reads cleanly.

**Task 4** (`64f0d3b`). `tools/schematic-modify/CONTEXT.md` has a new "Rule: readable placement, checked by `layout_check.py`" section and file entries for `layout_check.py`, `layout_baseline.json` and `v8_debug_sheet.py` (that row was missing). `tools/CONTEXT.md` has a table row. In the grid rule I wrote "about 0.75–0.85 × 1.27 mm per character (0.85 measured)". The task said 0.75; the plotted text is wider.

**For 11c onwards:**
- **Adding the BAT_CONN test point (11c):** use `add_component` with the new rules, then `v8_debug_sheet.py --check`. The power baseline is 51 and must not go up. After the GUI autoplace, run `layout_check.py --update-baseline` to ratchet the lower counts down, and commit the JSON.
- **Deferred (added):** about 660 local labels and 26 hierarchical labels on v8 have no `justify`, so they're drawn centred across their wire ends. You can see it in the LED sheet plot (`+5V_LED_H4` drawn over F1's pin). GUI autoplace doesn't touch labels. A netlist-neutral justify pass would fix them. That fits 11c/W3a if the Orchestrator wants it; I didn't do it, because it's out of 11b's scope.
- Scratch tools (not committed): `scratchpad/tests/svgcmp.py` (model vs plotted box per text), `svgpairs.py` (pair count from the plotted boxes), `place_test.py`.

**PLAN:** one Rejected Approaches line (the prototype's geometry). Approach unchanged; no open questions. Commits: `ebca71c`, `4cd4a66`, `ac45077`, `64f0d3b`, plus this handoff commit.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 13 | Phase 11b: layout check and placement rules | DONE | No — clean completion; one Deferred item routed to the Planner | b667390 | 4 tasks + handoff; baseline 141 overlap pairs (calibrated against the plotted SVG) |

#### Verification
- Re-derived: 5/5 Phase 11b boxes checked; working tree clean. `v8_debug_sheet.py --check` runs Phases 8–10, ERC 0 errors, LAYOUT CHECK PASSED, PHASE 11 CHECK PASSED. `check_state.py --fresh`: FRESH. PLAN has no date-stamped headings.
- The 141 versus 111 baseline is a measurement correction (the geometry was calibrated against the kicad-cli plot), not a regression.
- Out of plan: about 660 local and 26 hierarchical labels with no justify are drawn across their wire ends, and GUI autoplace won't fix them. The user approved "tidy, then look", so a netlist-neutral justify pass belongs before W3a. That adds a task, so it goes to the Planner before 11c is dispatched.

---

### Replan — label justify into 11c (2026-11-04)

Planner `c548964`: a label-justify pass and the stacked-label dedupe go into 11c before the GUI pass, and `layout_check` fails on a label with no justify.

---

### Worker #14 — Phase 11c: BAT_CONN test point, label justify, GUI autoplace, readability look

**Dispatch:**
```
Initiative: v8-debug-board
Phase: 11c — BAT_CONN test point, label justify, GUI autoplace, readability look
Initiative path: docs/initiatives/v8-debug-board/
Additional reading: SESSION.md Worker #12 and #13 Notes; docs/research/kicad-ai-tooling-2026-11/schematic-readability.md §3.3 (W3a options).

Tasks assigned (from TASKS.md Phase 11c):
## Phase 11c: BAT_CONN test point, label justify, GUI autoplace, readability look

- [~] Add a test point on BAT_CONN (J8 pin 2, before F3) and its own GND point, per `hardware/pcb-main-v8/CONTEXT.md` Test points → Ground points and Parts → Footprints. Next free TP numbers. Placed with the 11b rules, in `v8_debug_sheet.py` (idempotent; its `--check` expects both; the v7-position comparison still gives 0 nets differ). `annotate` both parts. `layout_check.py` at or below baseline
- [ ] Label justify pass on the existing v8 labels (SESSION.md Worker #13 Notes: about 660 local and 26 hierarchical labels have no `justify`, so KiCad draws them centred across their wire ends; GUI autoplace moves fields, not labels). A `--labels` mode on `tools/schematic-modify/tidy_fields.py` or a sibling `tidy_labels.py` (Worker's choice), with `--check` (per-sheet counts, writes nothing) and `--apply`, through the kiutils shim, refusing while a `~*.lck` exists. For each local, hierarchical or global label with no justify: apply the 11b rule from `modify.py` (`_label_angle`, `_make_local_label`): horizontal, with KiCad's justify (0/90 left bottom, 180/270 right bottom), the text running away from its wire. Find the wire from the wires that end at the label's anchor. If a label sits on a vertical wire end, make it horizontal (0 or 180, away from the part per `_label_angle`). If wires leave the anchor on both sides, or none ends there, keep the angle and only add the justify. Positions, text and kind don't change. Also dedupe the power sheet's 2 stacks (`BAT_FUSED` ×3, `VBAT` ×3 at x 307.34, zone B6): delete the extra copies only where kind, text and position are identical, leaving one of each. If they differ in any of these, leave them for W3a and say so. Add a rule to `layout_check.py`: a label with no justify fails (the baseline is 0 after this pass). Gate, before vs after: `kicad-cli sch export netlist` identical (apart from library `uri` paths); `v8_debug_sheet.py --check` passes, including `layout_check.py`. If a sheet's overlap count would go up, list the new pairs and flip those labels to the other side. If it still goes up, stop and report: don't raise the baseline. Then `layout_check.py --update-baseline` to record the lower counts (stacked labels on power 6 → 0). Render the LED sheet and check that `+5V_LED_H4` no longer sits over F1's pin. Log per-sheet counts (justified, turned horizontal, deduped, overlap pairs before → after) in SESSION.md. Add the pass to `tools/schematic-modify/CONTEXT.md`. Commit
- [ ] Update `hardware/pcb-main-v8/CONTEXT.md`: Test points (BAT_CONN added to the list and the "As built" paragraph), and the user's 2026-11-04 W3 decisions: keep R66 (10 mΩ, link h4), which answers the "Question for W3" under Power path; LED currents stay as designed. Re-extract `circuit-context.json`; `--fresh`
- [ ] Write the GUI steps for the user in SESSION.md, with checks inline in each step. Per sheet: Cmd+A, then `O` (Autoplace Fields); look before saving, and Undo on any hand-tuned v7 area that got worse. Then: Tools → Update Symbols from Library for Q20, Q21 and U10 only (clears the 3 `lib_symbol_mismatch` waivers); delete the 0.1 mm stray wire on SW1 pin 1 (power sheet, (222.25, 24.13)); optionally Preferences → Schematic Editor → Editing Options → automatically place fields; save; quit KiCad and confirm no `~*.lck` remains. Export the pre-GUI netlist to scratch first. Stop and report
- [ ] **(user)** Do the GUI pass (about 2 minutes per sheet)
- [ ] Verify the GUI pass: netlist identical to the pre-GUI export (pin → net checked for Q20, Q21, U10); `v8_debug_sheet.py --check` passes; ERC 0 errors with the 3 `lib_symbol_mismatch` gone; `layout_check.py` counts lowered and recorded with `--update-baseline`. Render each sheet to PNG (`kicad-cli sch export svg`, then convert) for the look, and list each sheet's remaining overlap spots by grid zone. Re-extract `circuit-context.json`; commit
- [ ] **W3a (user):** the readability look. The user reads each sheet (PNGs, then KiCad) and decides on the power/TCA re-layout (OQ-10), with the options in readability §3.3: none; hand layout in the GUI; scripted regroup; the battery block on its own sheet. Record the decision in SESSION.md. If any re-layout is chosen, stop: the Orchestrator sends a replan request to the Planner before Phase 11d
- [ ] 🔄 Handoff

The first task is marked `[~]` because it was dispatched to you — it is not someone else's work in progress.

Phase-specific notes: this phase has a user step. Do tasks 1–4, then return PARTIAL at the "(user) Do the GUI pass" task with the steps ready. The Orchestrator gives them to the user and resumes you afterwards. User decisions already given: keep R66; LED currents unchanged; add the BAT_CONN TP.

You are not the Orchestrator. Do not create documents, work across phases, or replan.
Return DONE, PARTIAL, or BLOCKED with specifics.
```

#### Notes

**Task 1: BAT_CONN test point** (`8047357`). **TP37** (BAT_CONN, D1.5 mm) and its ground point **TP77** (2.5 × 2.5 mm), power sheet, at the end of the rail test-point rows (88.9 / 101.6, 261.62). Numbers: the power sheet's rail convention, rail point TPn and its ground point TP(n+40) (TP10–TP36 / TP50–TP76), so TP37/TP77 are the next free pair. `v8_debug_sheet.py --apply` now adds the missing Phase 11c parts when Phase 11 is already applied (J11 present), and does nothing on a second run. `--check` expects both pins and a new fact (TP37 on J8 pin 2's net, the cell side of F3, not F3 pin 2). The v7-position comparison: 0 nets differ (the new refs are dropped as Phase 11 new parts). Annotated (`--annotate`: `ai_*` hidden at the symbol). Power overlaps 51 = baseline.

**Task 2: label justify pass** (`tools/schematic-modify/tidy_labels.py`, a sibling of `tidy_fields.py`). Per sheet:

| Sheet | Labels justified | Turned horizontal | Flipped 0↔180 | Kept angle (wires on > 1 side) | No wire | Deduped | Gate flips | Overlap pairs before → after |
|---|---|---|---|---|---|---|---|---|
| Root | 10 | 5 | 0 | 0 | 0 | 0 | 0 | 13 → 4 |
| LED | 22 | 11 | 0 | 1 | 0 | 0 | 0 | 5 → 5 |
| MCU | 177 | 39 | 24 | 0 | 0 | 0 | 0 | 22 → 19 |
| Power | 333 | 101 | 43 | 1 | 0 | 4 | 0 | 51 → 39 |
| TCA | 137 | 65 | 0 | 3 | 0 | 0 | 0 | 50 → 30 |
| **Total** | **679** (653 local, 26 hierarchical) | **221** | **67** | **5** | **0** | **4** | **0** | **141 → 97** |

- "Flipped" = a horizontal label whose text ran back over its own wire, now reading away from it. Every label with no justify had a wire end at its anchor, so none were "no wire".
- **Dedupe:** both power stacks were identical in kind, text, position and angle (`BAT_FUSED` ×3 and `VBAT` ×3 at x 307.34, 270°), so 2 extra copies of each were deleted. Stacked labels on power 6 → 0. Nothing left for W3a.
- No sheet's overlap count went up, so the gate flipped nothing.
- **Gate:** `kicad-cli sch export netlist` before vs after differs only in the `(date …)` line. `v8_debug_sheet.py --check`: CHECK PASSED (Phase 8, 0 nets differ), PHASE 9/10 CHECK PASSED, ERC 0 errors, LAYOUT CHECK PASSED, PHASE 11 CHECK PASSED. A second `tidy_labels.py --check` reports 0 everywhere.
- `layout_check.py` rule 5: a local, global or hierarchical label with no justify fails (no baseline; none allowed). Tested on the pre-pass copy: it flags all 683 (10/22/177/337/137).
- `--update-baseline`: root 13 → 4, MCU 22 → 19, power 51 → 39 (stacked 6 → 0), TCA 50 → 30, LED 5 unchanged.
- **LED sheet render** (kicad-cli PDF, cropped): `+5V_LED_H4` no longer sits over F1's pin. It now reads right from the C7 junction (147.32, 102.87), above the R27 wire. **Still crowded:** `+5V_LED_F` at F1 pin 2's stub end (143.51) reads right across the 3.8 mm gap and into `+5V_LED_H4` (the one LED-sheet pair in zone B3). Either side overlaps something (flipped, it would sit over F1), so the fix is a wire move, not a justify. Left for the user's GUI pass / W3a (GUI steps, LED sheet).
- Renders: PNGs via `kicad-cli sch export pdf` and PyMuPDF (`fitz`, installed). No SVG-to-PNG converter is on the machine (no rsvg-convert, ImageMagick or cairosvg).

**Task 3: design-intent CONTEXT** (`hardware/pcb-main-v8/CONTEXT.md`). BAT_CONN added to the Rails test-point list; a Phase 11c bullet in "As built (Phase 11)" (TP37/TP77 and the numbering); the Power path "Question for W3" now reads "Decided by the user 2026-11-04: keep R66"; Debug LEDs: currents kept as designed (user, 2026-11-04). `circuit-context.json` re-extracted with `--previous` (new components TP37, TP77; 295 components, 131 nets); `check_state.py --fresh`: FRESH.

**Task 4: the user's GUI steps.** Pre-GUI reference: commit `5ec6302` (all five sheets), plus the netlist exported to scratch (`scratchpad/pregui/pregui.net` and `pregui.xml`, with copies of the sheets). The verify task can regenerate it from `5ec6302` if the scratch folder is gone.
- **Correction to the task wording: the "0.1 mm stray wire on SW1 pin 1" isn't a stray to delete.** ERC's "length 0.1016 mm" uses the same ×100 scale as its positions: it is the 10.16 mm wire from SW1 pin 1 (222.25, 24.13) to (232.41, 24.13). That wire carries SW1 pin 1's net: the `VSYS_SENSE` label sits on it at 231.14. Only the last 1.27 mm past the label dangles. Deleting the wire would take SW1 pin 1 (row i, v7 position) off VSYS_SENSE. Step 3 shortens it instead.

##### GUI steps for the user (Phase 11c)

In short: the scripts have done everything that can be scripted (fields hidden, labels justified, duplicates removed). What's left needs KiCad's own autoplace, which only the GUI has. About 15 minutes. Nothing here should change a connection; the verify step checks the netlist afterwards.

Before you start: the working tree is clean at `5ec6302`. If anything goes wrong, quit KiCad without saving, or run `git checkout -- hardware/pcb-main-v8/kicad/` to get back to this point.

1. **Open the project.**
   DO: open `hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_pro` in KiCad 9, then open the Schematic Editor.
   CHECK: the title bar says `motion-play-main-v8`, and the Schematic Hierarchy panel on the left lists the root and four sheets (ESP32_S3, LED Controller, Power Management, TCA9548A_Subsystem).

2. **Update three symbols from the library** (clears the 3 `lib_symbol_mismatch` warnings). Run it once per reference: Q20, then Q21, then U10 (all on Power Management).
   DO:
   a. Tools → Update Symbols from Library…
   b. Choose "Update symbols matching reference designator" and type `Q20`.
   c. **Untick every box under the update/reset options** (remove fields, reset empty fields, field text, visibility, sizes and styles, positions, alternate pin functions, attributes). The fields, including the hidden `ai_*` and `LCSC Part` fields, must stay as they are. The symbol body and pins are updated anyway.
   d. Click Update. Read the message panel at the bottom of the dialog, then close it.
   e. Repeat b–d for `Q21`, then for `U10`.
   CHECK: each run's message panel names the one symbol you typed and reports it updated, with no error. On Power Management, Q20/Q21 (battery FETs, top right) and U10 (AP2112K) still have every pin on a wire; nothing is left dangling at a pin end.

3. **Shorten the wire past the VSYS_SENSE label at SW1** (Power Management, top centre, zone A5; clears the `unconnected_wire_endpoint` warning).
   DO:
   a. Go to Power Management. Find SW1 (the slide switch at about x 217, y 27 mm). From its pin 1 (right side, upper pin), a wire runs right to a `VSYS_SENSE` label and goes one grid step (1.27 mm) past it.
   b. Click that wire to select it. Drag the small square handle at its right end left, one grid step, onto the `VSYS_SENSE` label's anchor (the point where the label meets the wire). **Don't delete the wire**: it is what connects SW1 pin 1 to VSYS_SENSE.
   CHECK: the wire now ends exactly at the label: no stub sticks out to the right of the label's anchor, and the wire end shows no small open square (KiCad's mark for an unconnected end). The wire still reaches SW1 pin 1.

4. **Autoplace the fields, one sheet at a time** (root, ESP32_S3, LED Controller, Power Management, TCA9548A_Subsystem).
   DO, on each sheet:
   a. Click an empty spot on the sheet, then Cmd+A (select all).
   b. Press `O` (Autoplace Fields). Then Esc to deselect.
   c. Look over the sheet before you move on, especially the hand-placed v7 areas: on Power Management the BQ24195 (U5) and boost (U6) blocks, on TCA the TCA9548A (U4), on ESP32_S3 the module (U3). If one of those areas got worse, press Cmd+Z (this undoes the whole sheet's autoplace), then drag-select only the regions you want autoplaced (leave the hand-tuned area out) and press `O` again.
   CHECK: on each sheet, Reference and Value text no longer sits on top of labels or other text in the rows of test points (power sheet rows at the bottom left: TP10–TP77, including the new TP37 `BAT_CONN` / TP77; MCU sheet rows: TPIO*/TP13x), and no part's Reference/Value sits on its own pin's wire.

5. **(Optional) LED Controller: move `+5V_LED_F` off `+5V_LED_H4`** (zone B3, between F1 and R27).
   DO: on LED Controller, find F1 (3 A fuse) and R27 (0.1 Ω) at the top. The `+5V_LED_F` label at F1's right pin reads right, into the `+5V_LED_H4` label at the C7 junction. Select the `+5V_LED_F` label and press `R` until its text hangs down below the wire (3 presses, from reading right to reading down). Don't move it.
   CHECK: `+5V_LED_F` reads downward from F1's right-hand wire end, clear of `+5V_LED_H4`, and its anchor is still on that wire end (it hasn't moved).

6. **(Optional) Turn on field autoplace for future edits.**
   DO: Preferences → Preferences… → Schematic Editor → Editing Options → tick the option to automatically place symbol fields. OK.
   CHECK: the box stays ticked when you reopen the dialog.

7. **ERC.**
   DO: Inspect → Electrical Rules Checker → Run ERC.
   CHECK: 0 errors. Warnings: no `lib_symbol_mismatch` and no `unconnected_wire_endpoint` left. What remains is 81 `pin_to_pin` and 2 `lib_symbol_issues` (J7 and U5 library names, expected). If there's an error, or the warning counts are different, don't save: note what ERC says and tell the Orchestrator.

8. **Save and quit.**
   DO: File → Save (Cmd+S). Quit KiCad completely (Cmd+Q; close the project manager too). Then in Terminal, from the repo: `ls -a hardware/pcb-main-v8/kicad | grep lck`
   CHECK: the `ls` command prints nothing (no `~*.lck` lock file left). Don't commit. The verify task checks the netlist and commits.

Tell the Orchestrator when you're done, and mention anything you undid in step 4 or skipped in 5–6.

**Status at the user step (PARTIAL by design).** Tasks 1–4 done; stopped at "(user) Do the GUI pass". For the resumed verify task: compare against `5ec6302` / `scratchpad/pregui/pregui.net`; check pin → net for Q20, Q21, U10 and SW1 pin 1 (still VSYS_SENSE after step 3); expect ERC warnings 81 pin_to_pin + 2 lib_symbol_issues only; then `layout_check.py --update-baseline` (current baseline: root 4, MCU 19, LED 5, power 39, TCA 30), PNG renders via `kicad-cli sch export pdf` + PyMuPDF, re-extract `circuit-context.json`. `tidy_labels.py --check` should still report 0; GUI autoplace doesn't touch labels, but step 5's rotation keeps a justify, so rule 5 holds. PLAN unchanged; no Rejected Approaches or Deferred items this phase so far.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 14 | Phase 11c: BAT_CONN TP, label justify, GUI pass | PARTIAL | Yes — planned user gate (GUI pass) | ef81cf8 | Tasks 1–4 done; overlap pairs 141 → 97; stopped at the user's GUI pass |

#### Verification
- Re-derived: tasks 1–4 checked; working tree clean. `v8_debug_sheet.py --check` (Phases 8–11, ERC 0 errors, LAYOUT CHECK PASSED): PHASE 11 CHECK PASSED. `--fresh`: FRESH.
- Worker caught an error in the plan: the "0.1 mm stray wire on SW1" is a 10.16 mm wire that carries SW1 pin 1 to VSYS_SENSE. ERC's position scale misled Worker #11's guide and the Orchestrator's relay of it. Deleting it would have opened the net. The user step now shortens it instead, and the verify task must confirm SW1 pin 1 is still on VSYS_SENSE.
- GUI steps relayed to the user. On resume, the verify task compares the result against `5ec6302` / the pre-GUI netlist in the scratchpad.

#### User GUI pass (2026-11-04): aborted, not saved
- The user shortened the SW1 wire (its `unconnected_wire_endpoint` cleared) and updated Q20/Q21; U10's update didn't take. Cmd+A then `O` appeared to do nothing.
- The user's GUI ERC (85 warnings) had a **new `multiple_net_names` on TCA: `I2C_SCL_IN` + `PU_SCL_2K2`**. That warning isn't in kicad-cli ERC of the committed files. Cause, from the file: the vertical wire (128.27, 69.85)–(128.27, 72.39) passes through the shared end (128.27, 71.12) of the two `I2C_SCL_IN` wires, with no junction. kicad-cli reads them as separate; the editor joins them. Saving would have baked in an SCL ↔ pull-up short. Latent scripted geometry; the v8 checks missed it.
- The user quit without saving. The tree is clean at f583fbb. The user's ERC report was moved to the scratchpad (`user_gui_ERC.rpt`).
- Evaluated: resolvable without replanning. Worker #14 was resumed to fix the geometry, add a check, trim the SW1 wire by script and confirm the KiCad 9 autoplace command.

#### Notes (resumed after the aborted GUI pass)

**T-touch fix (TCA)** (`e365da3`, `v8_debug_sheet.py --fix-11c`). Which side was intended: R29 pin 1 on **PU_SCL_2K2** only, separate from I2C_SCL_IN. Sources: the CONTEXT jumper matrix row d (upstream 2.2 k reaches the bus only through the JP19/JP20 selector, 1–2), the Phase 9 check (`PU_SCL_2K2 = JP20.2, R29.1`), and the v7-position comparison (0 nets differ with row d's v7 shorts applied). kicad-cli's reading was therefore the intended one, and the netlist didn't change. The SDA twin (R28) was already clean: its stub at x 139.7 crosses the SCL wire's interior, and a plain crossing joins in neither tool. Fix: the stub (128.27, 69.85)–(128.27, 72.39) is deleted; the `PU_SCL_2K2` label moves onto R29 pin 1 (128.27, 69.85), at 180° (reads left, right-bottom justify).

**Scan of every v8 sheet** (wire ends, pin ends and label anchors on a wire's interior, with no junction):

| Sheet | Item | Where | Both tools connect? | Fix |
|---|---|---|---|---|
| TCA | two `I2C_SCL_IN` wire ends | (128.27, 71.12), on R29's stub | No: the editor joins, kicad-cli doesn't | Stub deleted, label on R29 pin 1 (above) |
| TCA | `I2C_SCL_IN` label anchor | (128.27, 71.12), on R29's stub | Same point | Same fix |
| Power | `VSYS_SENSE` label anchor | (231.14, 24.13), 1.27 mm before the end of SW1 pin 1's wire | Yes (SW1.1 was on VSYS_SENSE in kicad-cli) | Wire now ends at the label (also clears `unconnected_wire_endpoint`) |

No other sheet had one. No pin end sits on a wire's interior anywhere. For information: v7 `c2acffc` has only the SW1/VSYS_SENSE one (inherited); the TCA one came from the Phase 9 script.

**`layout_check.py` rule 6** (`e365da3`): a T-touch with no junction fails, no baseline. It found exactly the 4 items above before the fix (2 wire ends and 1 label on TCA, 1 label on power) and 0 after.

**U10 "Update Symbols from Library" didn't take: why.** The embedded `Regulator_Linear:AP2112K-3.3` had lost the NC pin's `(hide yes)` (and the library copy's hidden property flags) in a kiutils round trip before the 11a shim. AP2112K-3.3 is a derived symbol in KiCad 9's library (`extends "AP2204K-1.5"`). I didn't establish why the GUI update failed on it; Q20/Q21 (not derived) updated fine. Fix by script: Q20/Q21's `CSD25402Q3A` and U10's `AP2112K-3.3` embedded symbols are re-copied from the stock library (`mcu.stock_symbol`, which flattens `extends`). kicad-cli ERC then has no `lib_symbol_mismatch`. **The GUI symbol-update step is removed.** Finding for later: `tidy_fields.py` restored pin_numbers/pin_names flags but not per-pin or library-property hides. ERC flagged only these three, so no other embedded copy differs from its library.

**Gate.** `kicad-cli sch export netlist` vs the pre-GUI export (`5ec6302`): only the `(date …)` line differs. `v8_debug_sheet.py --check`: CHECK PASSED (0 nets differ), PHASE 9/10/11 CHECK PASSED, LAYOUT CHECK PASSED, with expected pins added for R28.1/R29.1/SW1.1. kicad-cli ERC: 81 `pin_to_pin` + 2 `lib_symbol_issues` (J7 and U5 library names), nothing else. Overlap counts unchanged (power 39, TCA 30). `tidy_fields`/`tidy_labels --check`: 0. `circuit-context.json` re-extracted ("No structural changes"); `--fresh`: FRESH. A second `--fix-11c` does nothing.

**Autoplace command, KiCad 9 (sources checked, not guessed).**
- KiCad 9 English manual, shipped in the app (`SharedSupport/help/en/eeschema.html`): "Autoplace Fields action (select a symbol and press O)"; hotkey table: "Autoplace Fields | O".
- KiCad 9.0 source, `eeschema/tools/sch_edit_tool.cpp`: the action is in the right-click menus (`selToolMenu`, `drawMenu`) whenever the selection holds a symbol or sheet. It acts on every selected symbol or sheet (or a selected field's parent), forces manual mode, and moves visible fields only.
- `eeschema/menubar.cpp` puts it in **no main menu**, so there is no menu-bar path. The primary instruction is the right-click menu entry. Select All is Edit → Select All.
- The autoplacer puts a symbol's fields on the side with no pins (right first), so a test point's Reference/Value should move from above the circle to its right. That gives the step a visible check. Why the user's Cmd+A then `O` showed nothing isn't known (perhaps keyboard focus). The new steps try one symbol first.

##### GUI steps for the user (Phase 11c, rework; replaces the steps above)

In short: the scripts have now fixed what the last attempt found (the SCL pull-up short the editor saw, the SW1 wire, the three symbols that didn't match the library). What's left is KiCad's field autoplace, which only the GUI has. About 15 minutes. You run ERC twice: once as soon as the project opens, before you change anything, and again before saving. That way any disagreement between the editor and the scripts' checks shows up before anything is saved.

Before you start: the working tree is clean at the commit that logs these steps. If anything looks wrong, quit KiCad without saving; `git checkout -- hardware/pcb-main-v8/kicad/` also restores this point.

**Expected ERC list** (both ERC runs): 0 errors; 83 warnings, which are 81 `pin_to_pin` and 2 `lib_symbol_issues` ("The current configuration does not include the symbol library 'USB-C_SMD-TYPE-C-31-M-12'" for J7 and the same for 'BQ24195RGET' for U5). Nothing else: no `multiple_net_names`, no `lib_symbol_mismatch`, no `unconnected_wire_endpoint`.

1. **Open the project.**
   DO: open `hardware/pcb-main-v8/kicad/motion-play-main-v8.kicad_pro` in KiCad 9, then open the Schematic Editor.
   CHECK: the title bar says `motion-play-main-v8`, and the Schematic Hierarchy panel on the left lists the root and four sheets (ESP32_S3, LED Controller, Power Management, TCA9548A_Subsystem).

2. **ERC before changing anything.**
   DO: Inspect → Electrical Rules Checker → Run ERC. Compare the result with the expected list above.
   CHECK: it matches the expected list exactly. **If it doesn't (in particular any `multiple_net_names`), stop: close the dialog, quit KiCad without saving, and send the Orchestrator the ERC report** (in the ERC dialog: Save… to a file). The editor and the scripts then disagree about a connection.

3. **Try autoplace on one symbol first** (Power Management, bottom left, the test-point rows).
   DO:
   a. Go to Power Management. Find TP37 (value `BAT_CONN`, the last-but-one test point in the bottom row, about x 89, y 262 mm). Click its circle to select it.
   b. Right-click on it and choose **Autoplace Fields** from the menu (the keyboard shortcut is `O`).
   CHECK: TP37's "TP37" and "BAT_CONN" text jumps from above the circle to its right. If nothing moves, press Esc, click empty canvas once (so the drawing has keyboard focus), select TP37 again and retry. If it still doesn't move, stop and tell the Orchestrator what the right-click menu shows.

4. **Autoplace each sheet** (root, ESP32_S3, LED Controller, Power Management, TCA9548A_Subsystem).
   DO, on each sheet:
   a. Click empty canvas, then Edit → Select All (Cmd+A).
   b. Right-click on any selected symbol and choose **Autoplace Fields** (or press `O`). Press Esc to deselect.
   c. Look over the sheet before you move on, especially the hand-placed v7 areas: on Power Management the BQ24195 (U5) and boost (U6) blocks, on TCA the TCA9548A (U4), on ESP32_S3 the module (U3). If one of those got worse, press Cmd+Z (this undoes that sheet's whole autoplace), drag-select only the regions you want autoplaced (leave the hand-tuned area out), and run Autoplace Fields again.
   CHECK: on each sheet the test points' Reference/Value now sit to the right of their circles, not over the labels below them (Power Management bottom-left rows TP10–TP77; ESP32_S3 rows of TPIO*/TP13x; TCA test points TP80–TP103). No part's Reference/Value sits on its own pin's wire.

5. **(Optional) LED Controller: move `+5V_LED_F` off `+5V_LED_H4`** (zone B3, between F1 and R27).
   DO: on LED Controller, find F1 (3 A fuse) and R27 (0.1 Ω) at the top. The `+5V_LED_F` label at F1's right-hand wire end reads right, into the `+5V_LED_H4` label at the C7 junction. Select the `+5V_LED_F` label and press `R` until its text hangs down below the wire (3 presses, from reading right to reading down). Don't move it.
   CHECK: `+5V_LED_F` reads downward from F1's right-hand wire end, clear of `+5V_LED_H4`, and its anchor is still on that wire end.

6. **(Optional) Turn on field autoplace for future edits.**
   DO: KiCad → Settings… (Preferences) → Schematic Editor → Editing Options → tick the option to automatically place symbol fields. OK.
   CHECK: the box stays ticked when you reopen the dialog.

7. **ERC again, before saving.**
   DO: Inspect → Electrical Rules Checker → Run ERC.
   CHECK: it still matches the expected list exactly (autoplace and label rotation don't change connections). If not, don't save: quit without saving and send the Orchestrator the ERC report.

8. **Save and quit.**
   DO: File → Save (Cmd+S). Quit KiCad completely (Cmd+Q; close the project manager too). Then in Terminal, from the repo: `ls -a hardware/pcb-main-v8/kicad | grep lck`
   CHECK: the `ls` prints nothing (no `~*.lck` lock file). Don't commit. The verify task checks the netlist and commits.

Tell the Orchestrator when you're done, and mention anything you undid in step 4 or skipped in 5–6.

**Status: PARTIAL again, at "(user) Do the GUI pass".** Verify-task reference: `e365da3` (netlist = the pre-GUI export apart from the date line). Expect pin → net R29.1 = PU_SCL_2K2, R28.1 = PU_SDA_2K2, SW1.1 = VSYS_SENSE, Q20/Q21/U10 unchanged; ERC = the expected list; `layout_check.py` including rule 6 (T-touch) passes.

#### Result (resume)
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 14 | Phase 11c (resume) | PARTIAL | Yes — planned user gate (GUI pass, reworked steps) | d86fa78 | SCL T-touch fixed (R29.1 on PU_SCL_2K2 only); T-touch rule in layout_check; SW1 trimmed; Q20/Q21/U10 library copies refreshed |

#### Verification (resume)
- Re-derived: tree clean. `--check` chain passes (ERC 0 errors, LAYOUT CHECK PASSED, PHASE 11 CHECK PASSED). kicad-cli ERC = 81 `pin_to_pin` + 2 `lib_symbol_issues`, matching the expected list in the new steps. `--fresh`: FRESH.
- The new steps run ERC in the editor before any change, so editor/cli disagreement shows up before a save. Relayed to the user.

#### Notes (verify the GUI pass, 2026-11-05)

The user did the reworked steps 1–4 and 7–8, skipped the optional steps 5 (`+5V_LED_F`) and 6 (preference), and undid nothing.

**Verify against `e365da3`.**
- **Netlist identical** (kicad-cli, apart from date, source path and library `uri` paths). Pin → net: R29.1 PU_SCL_2K2, R28.1 PU_SDA_2K2, SW1.1 VSYS_SENSE, Q20.4/Q21.4 BAT_GATE, U10 pins 1/3/5 = +5V_CORE / +3.3V_MCU / +3.3V_BUS_REG, TP37 BAT_CONN.
- `v8_debug_sheet.py --check`: CHECK PASSED (0 nets differ), PHASE 9/10/11 CHECK PASSED, LAYOUT CHECK PASSED. kicad-cli ERC = the expected list: 81 `pin_to_pin` + 2 `lib_symbol_issues` (J7, U5), 0 errors.
- **Did KiCad's save undo the 11a/11c work?** No. A structural comparison of every sheet (`scratchpad/tests/cmp.py`) found the same labels (text, position, angle, justify), the same symbols (none moved, rotated, added or lost), all 1,138 `ai_*` fields still hidden, 0 visible extra fields, and no change in the embedded symbols' pin, pin-number or pin-name hiding. `tidy_labels.py --check`: 0. What KiCad did change on save:
  - **TCA:** it merged the collinear wire pairs `I2C_SCL_IN` (119.38→128.27→146.05, y 71.12) and `I2C_SDA_IN` (119.38→139.7→146.05, y 73.66) into single wires. Their local labels now sit on a wire's interior. **This failed layout_check rule 6 as I first wrote it** (2 "T-touches"). Both tools connect a label on a wire's interior (kicad-cli joined SW1 pin 1 to VSYS_SENSE through just such a label before the trim, and the netlist is unchanged here). So the rule was too broad, and the GUI wasn't at fault. **Rule 6 is narrowed** to wire ends and pin ends on a wire's interior (fail); a label on a wire's interior is listed with `-v` only. Re-run on `5ec6302` (before the fix), the narrowed rule still catches the real SCL case.
  - **LED:** it removed the junction at the C7 node (147.32, 102.87). Only two wire ends meet there (with the `+5V_LED_H4` label), so the junction was redundant; the netlist is unchanged.
  - **All sheets:** it added an empty, unhidden `Description` field to 213 placed symbols and rewrote the files in KiCad's own multi-line format, hence the large diffs. An empty field draws nothing, but `tidy_fields.py --check` counted it. `tidy_fields.py` now leaves empty fields alone; `--check` is 0.
- `layout_check.py --update-baseline`: root 4 (unchanged), MCU 19→13, LED 5→3, power 39→19, TCA 30→6. That is 45 pairs in all, down from 141 at 11b and 1,616 before 11a.
- `circuit-context.json` re-extracted ("No structural changes"); `--fresh`: FRESH.

**Remaining overlap spots by zone** (`layout_check.py -v`):
- **Root (4):** C2 TP145 Value on its `GND` label; C4 TP110 and TP111 Values touch; B1 TP112 Reference on its Value; A5 TPIO10 Value ("TestPoint") on the TCA sheet name. Root counts didn't change, so autoplace probably didn't move these four.
- **LED (3):** C3 R66 Reference / `+5V_LED_F` and R66 Value / `+5V_LED_H4`; B3 `+5V_LED_H4` / `+5V_LED_F` (the optional step 5 spot).
- **MCU (13):** D6/D7 strap-pad Values (`STRAP U3_IO3/45/46`) on their GND points' Values (3); A2/A3 four `+3.3V_MCU` labels touching each other (v7 area); C3/C4 neighbouring labels in the U3 label column (`U3_IO9/U3_IO46`, `U3_IO3/U3_IO46`, `INT1/INT2`, `U3_IO45/DBG2`, `DBG1/DBG2`, `DBG1/U3_IO14`).
- **Power (19):** D3 three hierarchical labels touching (+5V, +3.3V_MCU, GND); C2 `PWR_FLAG` value on R38/TH1 values; C5 C37/C39 fields; C8 C65 fields on `+3.3V_BUS_HDR`/`+3.3V_BUS` labels; single label-on-label touches in A5, B7, B8, D1, D2, D4, E1, E2, E3, E7.
- **TCA (6):** A7/A8/B7/B8: each channel's `CHn_*_CONN` label touches the TVS's `GND` label.

**W3a: readability look, ready for the user.**

PNGs (rendered from the committed sheets by kicad-cli PDF, 150 dpi):
- Root: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/4463d79b-1453-4083-8508-d40852c5e639/scratchpad/w3a/1-root.png`
- LED Controller: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/4463d79b-1453-4083-8508-d40852c5e639/scratchpad/w3a/2-led_controller.png`
- Power Management: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/4463d79b-1453-4083-8508-d40852c5e639/scratchpad/w3a/3-power_management.png`
- TCA9548A_Subsystem: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/4463d79b-1453-4083-8508-d40852c5e639/scratchpad/w3a/4-tca9548A_subsystem.png`
- ESP32_S3: `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/4463d79b-1453-4083-8508-d40852c5e639/scratchpad/w3a/5-esp32_s3.png`
- All five in one PDF (zoomable): `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/4463d79b-1453-4083-8508-d40852c5e639/scratchpad/w3a/v8-schematic.pdf`

What you'll see, sheet by sheet:
- **Root:** the five sheet boxes and the root test points. Clean apart from four small touches among the TP110–TP112/TPIO10 texts.
- **LED Controller:** small and readable. One spot: between F1 and R27 the labels `+5V_LED_F` and `+5V_LED_H4` run into each other (the optional step you skipped).
- **ESP32_S3:** the v7 module drawing at the top, and below it (new in v8) a grid of test points, the debug LEDs, the UART0 header and the spare-GPIO header, all wired by labels. The few touches are neighbouring net names in U3's label column and the strap pads' value text.
- **Power Management:** the busiest sheet (154 parts on A3; v7 had 59). The v7 circuit (USB-C, BQ24195, boost, regulators) is still drawn as a circuit across the top. Everything v8 added sits below and to the right as **rows of parts joined by net labels**: the passives row in the middle, the rail test points and their ground points in three rows at the bottom left, the debug LEDs bottom right, and the battery block (J8, F3, Q20/Q21, J30–J35 and the row c/h/i/j/k/l jumpers) as a column on the right. Nothing overlaps much any more (19 small touches), but the added parts read as a parts list: to follow the battery path J8 → F3 → Q20 → Q21 → BQ you trace net names, not lines.
- **TCA9548A_Subsystem:** the TCA (U4) top left with its upstream pull-ups; the 24 channel test points as a grid top right; then one row of parts per channel (series R, row b bypass, TVS, its GND header, the downstream pull-up option) and the row d/f selectors at the bottom. A regular, label-wired layout. The only touches are each channel's connector-side label against the TVS's GND label.

**OQ-10: should the power and TCA sheets be re-laid out?** The options (readability §3.3), in plain terms:
1. **None.** Keep the sheets as they are. The circuit is complete and checked; the remaining roughness is cosmetic. The 11e plain-language tour explains the label-wired blocks, so a reader doesn't have to trace them unaided.
2. **Hand layout in the GUI.** You move parts in KiCad (for example the test points into one labelled box, the jumper rows next to the circuitry they break). About 2–4 h. Every move risks a connection change, but the netlist check and the editor ERC run before saving catch that, as they did this time.
3. **Scripted regroup.** I write a script that moves the generated parts into tidier groups and wires the battery chain with lines. Repeatable and checked by the same gates, but it is new script work on a sheet where the last scripted geometry hid a short. It needs a replan.
4. **The battery block on its own sheet.** Move J8, F3, Q20/Q21 and their gate network onto a new "Battery protection" sheet, drawn as a left-to-right chain. That means a new hierarchical sheet, script work and an update to the `--check` chain, so it also needs a replan.

**My recommendation: option 1 (none) for both sheets.** TCA is regular and nearly clean (6 touches). The power sheet's added parts are complete, checked against v7 and readable by net name. Re-laying them out costs hours and new geometry risk, and buys nothing the W3 review needs, because the tour (11e) can walk the battery path and the jumper rows. If, when you read the power sheet, you find you can't follow the battery path from the labels, take **option 4** for that block alone: it's the one part of the board whose drawing matters most for the review (it's what protects against the cooked-board faults).

Record the decision here as "W3a decision: …". If you choose any re-layout (2–4), the Orchestrator sends a replan to the Planner before Phase 11d.

**Status: PARTIAL at "W3a (user)".** Verify task done and committed. PLAN unchanged; no Rejected Approaches (the rule narrowing is a tool fix, logged here). No Deferred items.

#### Result (GUI-pass verify)
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 14 | Phase 11c (verify) | PARTIAL | Yes — planned user gate (W3a) | cf61cb2 | GUI pass verified; overlap pairs 141 → 45; W3a renders ready |

#### Verification (GUI-pass verify)
- Re-derived: tree clean; `--check` chain passes (ERC 0 errors, LAYOUT CHECK PASSED, PHASE 11 CHECK PASSED); `--fresh` FRESH; W3a PNGs/PDF exist in the scratchpad.
- Accepted: rule 6 narrowed to wire and pin ends (labels partway along a wire connect in both tools). The worker reports the narrowed rule still catches the original SCL case at `5ec6302`. tidy_fields now ignores empty fields, after KiCad added empty Description fields on save.

#### Notes (close-out, 2026-11-05)

**W3a decision: none (option 1), both sheets.** The user's words: "Leave them as they are, no need to relay." The power and TCA sheets stay as they are; no replan before Phase 11d. OQ-10 is struck as resolved in PLAN.md. W3a and the Handoff are ticked in TASKS.md.

**Phase 11c summary for the next phases.**
- TP37/TP77 on BAT_CONN.
- `tidy_labels.py` justify pass.
- `layout_check.py` rules 5 (labels with no justify) and 6 (wire/pin-end T-touches).
- Two fixes, `v8_debug_sheet.py --fix-11c`:
  - the TCA SCL T-touch, which only the editor joined;
  - the SW1 wire tail.
- Q20/Q21/U10 embedded symbols re-copied from the library.
- The user's GUI autoplace.
- Overlaps: 45 pairs (baseline). ERC: 81 `pin_to_pin` and 2 `lib_symbol_issues`, 0 errors.
- The schematic is as of `cf61cb2`.
- For 11d onwards:
  - KiCad's own save merges collinear wires and adds empty `Description` fields. Both tools allow for it now.
  - Any future GUI save should be followed by the netlist and `--check` gate.

#### Result (close-out)
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 14 | Phase 11c | DONE | No — clean completion | b314d8c | W3a: no re-layout (OQ-10 resolved) |

#### Verification (close-out)
- Re-derived: tree clean; 0 open boxes in 11c; PLAN has no date-stamped headings; OQ-10 struck. Carry forward: after any GUI save, run the netlist comparison and `--check`.

---

### Worker #15 — Phase 11d: Second-opinion review — kicad-happy (read-only)

**Dispatch:**
```
Initiative: v8-debug-board
Phase: 11d — Second-opinion review — kicad-happy (read-only)
Initiative path: docs/initiatives/v8-debug-board/
Additional reading: docs/research/kicad-ai-tooling-2026-11/landscape.md (kicad-happy section); SESSION.md Worker #11 audit and Notes; hardware/pcb-main-v8/CONTEXT.md.

Tasks assigned (from TASKS.md Phase 11d):
## Phase 11d: Second-opinion review — kicad-happy (read-only)

- [~] Clone kicad-happy at tag v3.0.0 (github.com/aklofas/kicad-happy, MIT; landscape §2 and §5 item 1) into its own scratchpad directory. Run its schematic analyzers on a scratch copy of `hardware/pcb-main-v8/kicad/` at HEAD, with output to the scratchpad. Run any of its Python with `-I` from outside its folder. Don't install it as a Claude Code plugin (that is a config change): if its analyzers can't run standalone, or need a Python we don't have, write the install as a **(user)** step and stop. Nothing it produces is written into the repo
- [ ] Classify each finding against the Phase 11 audit (SESSION.md, Worker #11) and `hardware/pcb-main-v8/CONTEXT.md`: new true issue; known or by design (cite the CONTEXT decision); or false positive. Spot-check its datasheet extraction for TCA9548A, BQ24195 and TPS61088 against `docs/references/*/DATASHEET_REFERENCE.md`
- [ ] Log the findings in SESSION.md as a table: finding, sheet/ref, class, evidence, proposed fix. **Nothing is applied**; each true issue goes to the user at W3 as a proposal. Give a recommendation for OQ-9 with the score (true new issues, false positives)
- [ ] 🔄 Handoff

The first task is marked `[~]` because it was dispatched to you — it is not someone else's work in progress.

Phase-specific notes: treat the cloned repo as untrusted downloaded code. Use its own scratchpad dir, run its Python with -I from outside its folder, and don't install anything globally. Work on a scratch copy of the kicad folder. The user is not an EE: write each proposed true issue so it can be explained in plain terms at W3.

You are not the Orchestrator. Do not create documents, work across phases, or replan.
Return DONE, PARTIAL, or BLOCKED with specifics.
```

**Not spawned:** the Claude Code permission check blocked the dispatch, because the phase runs downloaded third-party code (kicad-happy). `[~]` reverted. Awaiting the user's decision.

**User decision (2026-11-05):** "Allow kicad-happy". The user approved running kicad-happy v3.0.0 from its own scratch folder on a copy of the schematic, with nothing installed. Re-dispatching.

#### Notes

**Run (task 1).** kicad-happy v3.0.0 (commit `c451943`), shallow-cloned into the session scratchpad (`kh-src/`). The schematic analyzer is pure Python but needs 3.10+. The project Python (3.7.3) and `/usr/bin/python3` (3.9.6) can't run it, so it ran with `/usr/local/bin/python3.13` (3.13.3, already on the machine). Nothing was installed. Command (from the scratchpad, not the clone): `python3.13 -I <clone>/skills/kicad/scripts/analyze_schematic.py <scratch copy>/motion-play-main-v8.kicad_sch --output <scratch>/schematic.json`. The input was a `git archive` copy of `hardware/pcb-main-v8/kicad/` at `8cd2681`. The analyzer has no network code (`lifecycle_audit.py` has some, and wasn't run). It wrote only `schematic.json` and `capability_mode.json` to the scratchpad. The repo stayed clean. The PCB analyzer wasn't run: the task asks for the schematic, and the v8 board is an outline only.

**Output.** 141 findings: 4 error, 14 warning, 123 info. 91 of the info items are detections with no claim attached ("LED D11 is resistor-limited", "RC filter R43/C38"). Each item below is classed against Worker #11's audit and `hardware/pcb-main-v8/CONTEXT.md`. Where a class depended on connectivity, it was checked against `circuit-context.json`, and against a `kicad-cli sch export netlist` of the scratch copy for the ground point.

**Datasheet spot-check.** Datasheet extraction **didn't run**: `capability_mode.json` reports `datasheet_extraction: unavailable`, coverage 0 %. It needs an MPN field on each part (ours carry LCSC numbers, so 0/172), PDFs downloaded into `./datasheets/` by its distributor skills (network), and its LLM extraction flow (the Claude Code skills). So there is nothing extracted to compare for TCA9548A, BQ24195 or TPS61088. The only datasheet-type value it used was a guess:
- **TPS61088 (U6):** it guessed the feedback reference at 0.6 V (`missing_info.heuristic_vref: ["U6"]`), so it estimated +5V at 2.529 V. `docs/references/tps61088/DATASHEET_REFERENCE.md` gives 1.204 V typ (PWM), so 1.204 × (1 + 180k/56k) = 5.07 V. That matches CONTEXT (5.07 V nominal; 5.096–5.12 V measured, V7R-020, PWR-002). The wrong voltage then fed its capacitor-derating and inrush figures.
- **BQ24195 (U5):** no values extracted. Its "SCL/SDA needs a pull-up" premise agrees with the reference ("Pull up via 10 kΩ"). It missed that the pull-up reaches U5 through row f's header.
- **TCA9548A (U4):** no values extracted. It classed U4 as a "bidirectional level shifter", which is loosely true. There is no `docs/references/*/DATASHEET_REFERENCE.md` for the TCA9548A, only two library READMEs in `docs/references/i2c-multiplexer/`, so there was nothing to spot-check against.

**Findings (task 3).** Classes: **new** = a true issue not in Worker #11's audit or CONTEXT; **known** = known or by design; **FP** = false positive. Most of the FPs come from one blind spot: the analyzer treats a pin header as a connector, not a jumper, and doesn't trace a rail through a fuse or a current-shunt resistor. This board uses headers, fuses and shunts on purpose, on most rows.

| # | Finding (kicad-happy rule, severity) | Sheet / ref | Class | Evidence | Proposed fix |
|---|---|---|---|---|---|
| 1 | SDA and SCL have no pull-up (PR-001, 2 × error) | TCA / I2C_SDA, I2C_SCL; U4, U7 | FP | The pull-ups R28/R29 (2.2 k, plus 4.7 k/10 k) reach the bus through the row d headers JP19/JP20, and the 1–2 shunt ships fitted (CONTEXT Jumper matrix row d). The tool can't see a shunt | none |
| 2 | BQ SDA/SCL have no pull-up (PU-001, 2 × warning) | TCA / BQ_SDA, BQ_SCL; U5 | FP | U5 reaches I2C_SDA/SCL, and their pull-ups, through the row f headers JP27/JP28 (shunt on by default) | none |
| 3 | BQ STAT has no pull-up (PU-001, warning) | Power / BQ_STAT; U5 | FP | STAT is open-drain and drives D10 (orange) through R62 2.2 k: the LED and resistor are the pull-up | none |
| 4 | TPS61088 EN has no pull-up (PU-001, warning) | Power / BOOST_EN; U6 | FP | JP31 (row i, closed by default) ties EN to VSYS_SENSE; R2 100 k pulls it down when the jumper is cut (CONTEXT row i) | none |
| 5 | Rails with no declared source: +3.3V_BUS_HDR, +5V_LED_F, +5V_LED_H4, BOOST_VCC, VSYS_SENSE (RS-001, 5 × warning) | Power, LED | FP | +3.3V_BUS_HDR is fed from U10 through the row c header JP30. +5V_LED_F comes from +5V through F1. +5V_LED_H4 comes through R66 (link h4). VSYS_SENSE comes from VSYS through R44 (the 10 mΩ INA219 shunt). BOOST_VCC is U6's own internal regulator output (VCC pin; reference: "VCC regulation 5.8 V") | none |
| 6 | JP19/JP20 have no ground pins (CG-AUD, 2 × warning) | TCA / JP19, JP20 | FP | These are the row d pull-up selector headers, not cable connectors | none |
| 7 | No capacitor on USB VBUS at J7 (UC-001, warning) | Power / J7, VBUS_RAW | FP | C20 1 µF, C21 4.7 µF and C22 47 µF sit on Protected_VBUS just after F2. The tool only checks the net before the fuse | none |
| 8 | No ESD/TVS on USB VBUS at J7 (UC-002, warning) | Power / J7, VBUS_RAW | FP | U9 USBLC6-2SC6 pin 5 (its VBUS clamp) is on Protected_VBUS, after F2 (CONTEXT Kept v7 parts: U9) | none |
| 9 | JP33 is open by default, so the board needs a solder step (SJ-DET, warning) | Power / JP33 | known | Row j: the D+ to GND SJ2 is open in v8 and closed in v7 (CONTEXT Power path → rows j and k as built) | none |
| 10 | No datasheets, no MPNs, so the review is a consistency check only (DS-001, error) | all | known | A limit of the tool's setup, not a design finding. Our datasheet facts live in `docs/references/` | none |
| 11 | Sourcing gate: 0/116 BOM lines have an MPN (SS-001, error) | all | known | The BOM is keyed on LCSC numbers. Worker #11's BOM audit has every part with one except the copper-only parts. kicad-happy's own missing-LCSC list is exactly the 18 solder jumpers | none |
| 12 | Same net, two names: CHRG_INT, TCA_RESET, USB_DP, USB_DN, BQ_SDA, BQ_SCL (LB-001, 6 × info) | root ↔ child sheets | FP | Each is the same name on two sheets, joined by a hierarchical label. The tool counts the sheet path as part of the name | none |
| 13 | Same net, two names: I2C_SDA / I2C_SDA_IN, I2C_SCL / I2C_SCL_IN, LED_DATA / DATA_IN (LB-001, 3 × info) | TCA, LED sheet pins | known | v7's sheet-pin names (present at `c2acffc`). Kept, and the v7-position netlist check matches v7 | none (a rename is cosmetic and touches the v7 comparison) |
| 14 | C34, C35, C36, C42 (22 µF 25 V) over-rated for a "2.5 V" +5V rail (VD-004, 4 × info) | Power / boost output | FP | Based on the wrong 2.529 V estimate (datasheet spot-check above). The 25 V part is v7's as-built part, kept for v7 +5V behaviour (CONTEXT "Boost parts unchanged from v7", CL-14) | none |
| 15 | C22 (47 µF 35 V) over-rated for Protected_VBUS (VD-004, info) | Power / C22 | known | v7 as built (CONTEXT Power parts: C22, C30, CL-14) | none |
| 16 | Solder-jumper notes: JP3/4, JP5, JP21–26, JP31, JP32, JP34, JP35, JP40–43, "open = needs a solder step" or "closed = treat as connected" (SJ-DET, 17 × info) | all | known | They match the CONTEXT Jumper matrix defaults (rows d downstream, e, g, i, j, k, l; LED load SJs) | none |
| 17 | Lifecycle audit not run (LC-007, info) | — | n/a | A process note: it needs `--lifecycle` plus network and API keys. Not run | none |
| 18 | "Isolation barrier: 5 ground domains, 0 isolation parts" (info) | root / TP144–TP148; TCA / CH0–2_TVS_GND | FP | kicad-happy puts the root-sheet ground points TP144–148 on a separate `/GND` net, because it doesn't merge a root-sheet local label with the GND power net. KiCad does: `kicad-cli sch export netlist` puts TP144 on `GND` (net code 130). The three CHn_TVS_GND nets are row b's TVS ground legs, switched by JP16–18 (CONTEXT row b) | none |
| 19 | U6 output estimated at 2.529 V (info) | Power / U6, R39/R40 | FP | Datasheet spot-check above: the true figure is 5.07 V | none |
| 20 | Sensor channels CH0–2_*_CONN have no pull-ups (protocol compliance, info) | TCA / J4–J6 side | known | The downstream pull-ups are on each sensor board (4.7 k, `hardware/CONTEXT.md`). The on-board downstream option is row d, open by default (CONTEXT row d) | none |
| 21 | Key nets with no test point: UART0_TX/RX, EXT_SDA/SCL, PU_* / CHn_*_PU (test coverage, info) | MCU, TCA | known | UART0 is probed at J11, EXT at J10. The PU nodes are resistor ends behind the jumpers. CONTEXT Test points lists neither | none |
| 22 | No ESD on J8 (battery), J9 (cell NTC), J10–J12 and the jumper headers (ESD audit, info) | various | known | Bench headers on a debug board. Row b protects only the cable-facing sensor lines J4–J6 (CONTEXT Parts → Cable-facing protection) | none |
| 23 | **J3 (LED strip) has no ESD protection** (ESD audit, info: "none coverage") | LED sheet / J3 pin 2, IC1 pin 4 (DATA_TO_LEDS) | **new** (minor) | IC1 (SN74AHCT1G125) output pin 4 goes straight to J3 pin 2, an off-board cable: no series resistor and no ESD part (`circuit-context.json`). Neither CONTEXT nor Worker #11 mentions it. v7 had the same circuit. kicad-happy reported only "none coverage", with no recommendation; the series resistor is our observation | Proposal for W3, below |

**Proposal for W3 (item 23), in plain terms.** The wire that carries the colour commands to the LED strip leaves the board straight from a small chip pin (IC1). Nothing sits in line: no resistor, no static-protection part. The strip's cable is plugged and touched by hand, and a long cable makes the signal "ring". Either a static zap or the ringing lands on that pin. Common practice is a small resistor (33–100 Ω) in series at the chip, and sometimes a tiny protection diode at the connector. Cost: one or two small parts on the LED sheet. Because v7 had neither, fit the resistor as 0 Ω (or a footprint with a solder bridge) for v7 comparisons, so the v7-position netlist check still holds. The v7 debug track doesn't suspect the LED strip, so this is optional; the user decides at W3.

**Score (OQ-9).** Across the 50 findings that carry a recommendation or a severity above info, plus the 5 descriptive claims checked (items 18–22): **1 true new issue** (item 23, minor, and only weakly signalled), **27 false positives** (items 1–8, 12, 14, 18, 19: 25 + 2), 34 known or by design, 1 not applicable.

**Recommendation for OQ-9: don't adopt kicad-happy as a standing step in the pre-order review in this form.** The one real hit was minor and came as an info line with no recommendation. 27 false positives came from blind spots this board triggers everywhere: headers used as jumpers, rails through fuses and shunts, a root-sheet GND label, and a guessed reference voltage. Its main selling point, datasheet-aware review, didn't run. It needs MPN fields, PDF downloads (network) and the Claude Code plugin skills: that is a config change and data egress, which this run excluded. If the user wants a second look later, a single PCB-analyzer run at Phase 18 (thermal vias, trace width vs current, DFM) is the cheapest next test. Same limits (scratch copy, Python 3.13, no install), about 15 minutes. Re-decide on that score.

**For the next session.** Phase 11e's review checklist should carry item 23 as the only open kicad-happy finding. A scratch-copy schematic.json and the clone are in this session's scratchpad (not the repo; they disappear with the session). PLAN unchanged. No Deferred items.

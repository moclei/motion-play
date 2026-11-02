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

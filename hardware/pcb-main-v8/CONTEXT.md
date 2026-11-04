# Main PCB v8 (Debug Board): Design Intent

This file records every v8 design decision. The schematic and layout are built from it. Initiative: `docs/initiatives/v8-debug-board/` (BRIEF, PLAN, TASKS). The v7 design it starts from is at `hardware/pcb-main/kicad/`, commit `c2acffc`, and stays untouched.

## Purpose

v8 is a large, probe-friendly main board. It is built for debugging, not for the product form factor. It:

- fixes the known v7 design faults (below), in hardware rather than firmware;
- can be switched back to v7's configuration with jumpers. Jumpers default to the v8 (fixed) position, and every suspected v7 → v8 difference has a v7 position, so any v8 result can be A/B/A'd against v7;
- puts test points on every I²C net (both sides of the TCA), every rail and the spare U3 GPIOs, each with a ground point beside it within ground-spring reach, and adds debug LEDs;
- carries a v8 power path designed after the battery-damage investigation (Phase 2 → Debugger bench → Phase 7).

Out of scope: enclosure fit, compactness, and the v7 I²C debug track (owned by `lab/`).

## Inherited v7 faults

### BQ24195 needs an I²C command to run

**Symptom.** On USB power, v6 and v7 brown out and boot-loop unless firmware writes the BQ24195 at boot. The firmware workaround is `configureBQ24195()` in `firmware/src/main.cpp`: REG00 = 0x36 (IINLIM 2 A) and REG05 = 0x8A (watchdog off). The fault was found on v6 on 2026-04-10, three days after v7 was ordered, so v7 inherited it (`docs/research/v7-retry/v6-v7-changelist.md` §1a and the CL table "BQ24195 support" line).

**v7 circuit (`c2acffc`, `hardware/pcb-main/kicad/circuit-context.json`).**
- U5.2 D+ and U5.3 D− are on GND.
- U5.8 OTG goes through R35 (10 kΩ) to +3.3V. +3.3V comes from U8, which runs from +5V (U6), which runs from VSYS (the BQ's own buck output).
- U5.10 ILIM goes through R32 (330 Ω) to GND.
- U5.9 CE is on GND.
- TS: R36 5.6 kΩ from REGN, with R37 30 kΩ and TH1 10 kΩ NTC (on the PCB) to GND.

**Root cause.** Sources: TI SLUSB97A; section numbers below are the datasheet's. `docs/references/bq24195/DATASHEET_REFERENCE.md` covers the register map and ILIM.
1. Every time a source is plugged in, the BQ sets IINLIM by BC1.2 detection (§8.3.1.3.3–8.3.1.3.4, Table 2).
   - With D+ and D− on GND, it detects a USB host (SDP).
   - For an SDP, the limit is **100 mA if OTG is low** and 500 mA if OTG is high.
2. Detection runs before the buck starts (§8.3.1.4). So +3.3V, and with it OTG, is still low on USB power alone, and the limit is 100 mA (0.5 W at 5 V). That can't run U3 and the boost/LDO chain, so the board browns out.
3. ILIM can only lower the limit: the actual limit is the lower of the ILIM setting and the register (§8.3.5.1). R32 (≈ 1.47 A) never applies until firmware raises the register.
4. With a good cell (VBAT > 3.55 V), a 100 mA SDP sends the BQ into HIZ (§8.3.1.3.5, §8.4.1.1): VBUS is ignored and the cell isn't charged.
   - OTG is only high at plug-in if a battery is fitted and SW1 is on.
   - Also, in default mode a 100 mA SDP source gets a 45-minute timer, after which the BQ goes to HIZ (§8.4.1.2).
5. Any I²C write puts the BQ in host mode. There, watchdog expiry (40 s by default) resets the registers, and REG00 resets with IINLIM = 100 mA (§8.4.1, Fig. 22). So the workaround must also disable the watchdog.
6. EN_HIZ, VINDPM (4.36 V), CE and the TS network were checked and are not causes.

The firmware's "2 A" setting is really capped by R32 at 1.32–1.61 A (KILIM 435–530). The `main.cpp` comment's "~500 mA" default is 100 mA in practice (OTG low).

**Hardware fix options** (chosen in Phase 7 with the bench findings; stock not yet checked).
| # | Option | Gains | Costs / risks |
|---|---|---|---|
| 1 | Keep BQ24195; **short D+ to D−** instead of grounding them | Detects a charging port, so 1.5 A with no I²C, no HIZ and no 45-min timer. R32 sets the real ceiling. The argument: in DCD, 7–14 µA × 14.25–24.8 kΩ = 0.10–0.35 V, below 0.7 V, so contact is detected; in primary detection, D+'s 0.5–0.7 V source shows up on D−, above the 0.25–0.40 V threshold, so D− reads high. Zero part cost. A solder jumper gives a v7 position (GND) and a v8 position (shorted) | Capped at 1.5 A (1.35–1.65 A) unless I²C raises it. Asks a PC port for 1.5 A, against USB 2.0's 500 mA; fine from a wall adapter or powered hub |
| 2 | Keep BQ24195; **pull OTG up from a rail that exists at detection** (e.g. REGN through a resistor) | SDP 500 mA, which also escapes the HIZ rule | 500 mA is likely short for WiFi peaks plus LEDs. A partial fix that can sit beside option 1. The boost still needs CHG_CONFIG = 10 over I²C, so OTG high is safe |
| 3 | Keep BQ24195; wire D+/D− to the USB pair | Detects the true source class | Shares the pair with U3's native USB during enumeration and loads the pair. A PC port still gives 100 mA. Not recommended |
| 4 | **Swap** to a charger that needs no I²C to run at the target current (standalone NVDC buck with a resistor-set input limit, e.g. the BQ25616 class; or a linear power-path charger like the BQ24074/5 class, ≤ 1.5 A) | No I²C dependency at all. May avoid the chronic C90862 stock problem (`hardware/CONTEXT.md`) | New footprint and support network. Loses I²C telemetry and control. Some standalone parts also run D+/D− detection, so each must be checked for the same pin trap. Candidates are not verified yet |

With options 1–3, U5 stays on the I²C bus (jumper (f) still applies). `configureBQ24195()` can stay as an optional raise above 1.5 A, but boot no longer depends on it (Phase 12).

### Battery connection damaged boards (#0001, #0002) and #0004's boost doesn't run

**Status.** Desk-ranked in Phase 2; bench findings landed as `lab/cards/PWR-001-passive-0004-0005.md` and `lab/cards/PWR-002-sw1-throw-on-usb.md` (investigation `lab/investigations/power/`). W1 closed by the user 2026-11-03 on those two cards. What they settled: #0004's boost is off because SW1 sits at its GND throw (measured-supported, A/B/A; Kb–Ke refuted on #0004), and a healthy v7 on USB with SW1 at the GND throw shows exactly the "Mac doesn't find the ESP32" symptom (B8, measured-supported on #0004 and #0005). So #0001/#0002's "damage" may have been that (argued: both boards were binned). B1 (reversed cell) and B2 (Q2 under load) are untested; by the user's direction they are design risks that v8 designs out (Power path), not open bench questions. The full mechanism table is in the initiative SESSION.md (Phase 2 Worker Notes); the request was `docs/initiatives/v8-debug-board/debugger/RELAY-power.md`.

**What is known.** The user recalls that adding the battery cooked #0001 and #0002 in early testing, but not how (lab notebook 2026-10-27). One measured anchor: a v7 ran from a bench PSU at 3.7 V / 500 mA on BAT_RAW, with VBUS absent, without damage (`docs/debugging/v7-i2c-investigation.md` Phase 18). So a soft, current-limited source in the right polarity doesn't cook the board, and Q2's channel does conduct BAT_RAW → VBAT.

**v7 battery path (`c2acffc`).** BT1 + → BAT_RAW (C30 47 µF) → Q2 AO3401A (S on BAT_RAW, D on VBAT, gate = VBAT/2 via R33/R34) → VBAT (no capacitor) → U5 BAT → BATFET → VSYS → R44 → VSYS_SENSE → U6 boost (EN from SW1) → +5V → U8 → +3.3V. No fuse on the battery side.

**Ranked mechanisms (all argued).**
1. **Reversed cell.** Q2 is in load-switch orientation, so its body diode conducts from VBAT to BAT_RAW when the cell is backwards. VBAT is pulled to about −Vcell + 0.7–1.0 V, against U5 BAT's −0.3 V abs-min, with current limited only by the cell. C30 is reverse-biased. Live only if the holder accepts a reversed cell: the plain Keystone 1042 may not be polarised (1042P is).
2. **Q2 under-driven under load.** Vgs ≈ −Vcell/2 (−1.5 to −2.1 V), below the −2.5 V where Rds(on) is specified (≤ 85 mΩ). Battery-side limits are only the BQ's 9 A BATFET over-current and the boost's 10.6–13 A peak limit, so a 3–4 A load (the LED strip through F1 3 A, ≈ 4.5 A from the cell) can put watts into a SOT-23 rated 1.4 W for ≤ 10 s. The default 2048 mA charge current also flows through Q2.
3. **Hot-plug inrush and ringing.** At contact Q2 is fully on, and the cell charges C30, SYS (C29 220 µF + ceramics) and, through L2 and U6's body diode, +5V. Peaks over 9 A latch the BQ's BATFET off until USB is plugged in: the board looks dead but isn't. Overshoot past BAT/SYS 6 V abs-max is argued unlikely (electrolytic damping).
4. **Boost enabled into a load at plug-in.** Benign into a normal load (11.3 ms soft-start). Into a heavy or shorted +5V it becomes mechanism 2 at its worst.
5. **BT1 over B.Cu (CL-10, CL-20).** BT1 is hand-fit. Its + pad is 0.78 mm from J7's exposed rear shell legs (no net) and 0.38 mm from a tented USB_DN via. A bridge puts BAT_RAW on the USB shell, or on U3's D− and (via U9) Protected_VBUS.
6. **DC abs-max on BAT_RAW / VBAT / VSYS members.** Refuted for one Li-ion cell: every member is rated ≥ 6 V (BQ BAT/SYS 6 V, TPS61088 VIN 14.5 V, INA219 26 V, AO3401A 30 V). Live only if the source was > 6 V (e.g. a 2S pack).
7. **TS network.** It can't cook the board: TS is biased from REGN (VBUS only), and TH1 is on the PCB, not the cell. Side finding: nothing senses cell temperature while charging.

**#0004 and #0005 (argued from card V7R-020).** #0004: no rail is shorted, U6 isn't switching, so +5V (≈ 3.75 V) is VSYS through U6's body diode and U8 is in dropout (+3.3V ≈ 2.69 V, U3 can't run). First check: SW1's position. #0005: brownout loop at WiFi start because its BQ is absent from I²C, so the input limit stays at the 100 mA default (BQ section above). Its BQ buck runs (VSYS 4.30 V). Neither shows battery damage.

**Design deviations to fix in v8 whatever the bench finds (Phase 7).** Reverse-polarity protection that blocks (Q2 the other way round, or an ideal-diode / polarised holder); full gate drive for any series FET; a fuse or current limit on the battery side; 10 µF on BAT; PMID ≥ 60 µF (bq24195); clearance between the battery + pad and other exposed copper; J7 shell on a net; cell-temperature sensing if the cell is charged at > 1 A.

## Power path

**Status: pending user approval (Phase 7 task 5; closes W2).** Inputs: the Phase 1 BQ root cause and fix options and the Phase 2 mechanisms (Inherited v7 faults, above); cards PWR-001 and PWR-002 (W1, closed 2026-11-03); the user's direction that B1 (reversed cell) and B2 (Q2 under load) are designed out, not waited on; OQ-4 (battery on a keyed, polarised cable connector). Datasheets: TI SLUSB97A and `docs/references/bq24195/DATASHEET_REFERENCE.md` (BQ24195), `docs/references/tps61088/DATASHEET_REFERENCE.md` (TPS61088, SLVSCM8D), TI SLPS454B (CSD25402Q3A, rev. Jan 2016). Stock: JLCPCB parts API, 2026-11-03 (Power parts table, below). "Argued" marks anything not taken from a datasheet or a measurement.

**v8 power tree.**
```
XT30 (J8, cell) ─ F3 7 A ─ BAT_FUSED ─ Q20 ┐ BAT_COMMON ┌ Q21 ─ VBAT ─ U5 BAT        (SW4 "BATT" drives the Q20/Q21 gate)
USB-C J7 ─ F2 ─ Protected_VBUS ─ U5 VBUS        U5 SYS ─ VSYS ─ R44 ─ VSYS_SENSE ─ U6 boost (EN: row i) ─ +5V
+5V ─ link h3 ─ +5V_CORE ─┬ U8 AMS1117 ─ +3.3V_MCU_REG ─ link h1 ─ +3.3V_MCU (U3, R38, row k pad 3, D1)
                          ├ U10 AP2112K ─ +3.3V_BUS_REG ─ row c pin 1
                          └ D5, IC1, +5V LED
row c pin 2 = +3.3V_BUS_HDR ─ link h2 ─ +3.3V_BUS (I2C_PU_RAIL, TCA, INA219, J4–J6, BUS LED)
+5V ─ F1 3 A ─ link h4 (10 mΩ) ─ +5V_TO_LEDS (J3)
```
Row c's pin 3 is +3.3V_MCU_REG (before h1): in the v7 position U8 feeds everything, and h1 and h2 still split U3's current from the bus current (their sum is v7's U8 load).

### Charger: keep the BQ24195, fix it with pins (rows j, k)

**Decision.** U5 stays a BQ24195 (BQ24195RGER, C90862, the v7 part). The "needs I²C" fault is fixed by Phase 1 options 1 and 2 together, both on solder jumpers with a v7 position:
- **Row j, v8 = D+ shorted to D−.** Detection reads a charging port: IINLIM 1.5 A from the first plug-in, no HIZ, no 45-minute SDP timer, no I²C needed (SLUSB97A §8.3.1.3, Table 2; argued from the thresholds, Phase 1). R32 (330 Ω) stays, so the real ceiling is the ILIM pin's 1.32–1.61 A (KILIM 435–530). v7 = both pins on GND.
- **Row k, v8 = OTG pull-up (R35 10 kΩ) from REGN.** REGN exists at detection time (it comes from VBUS), so if detection ever reads an SDP (row j at v7, or a source that defeats the D+/D− short) the limit is 500 mA, not 100 mA, and the HIZ rule doesn't fire. OTG abs-max 7 V; REGN ≈ 4.8 V at 5 V VBUS, up to ≈ 6 V from a higher source (SLUSB97A). The boost (OTG) mode still needs CHG_CONFIG = 10 over I²C, so OTG high in default mode is safe (Phase 1). v7 = R35 to the MCU 3.3 V rail.
- **Addresses:** the BQ root cause (Inherited v7 faults → BQ24195, items 1–4). Boot no longer depends on `configureBQ24195()`; Phase 12 keeps it as an optional raise above 1.5 A (watchdog note stays).

**Why not a swap (Phase 1 option 4).** A standalone charger takes the BQ off the I²C bus. The BQ is one of the devices on v7's bus: it ACKs in V7R-019, its pins are probed (test points BQ_SDA/BQ_SCL), and row f's v7 position is "BQ on the bus". With a swap, no jumper position could rebuild v7's bus membership, which breaks the brief's A/B/A constraint. It would also lose charge telemetry. Option 3 (D+/D− on the USB pair) stays rejected (Phase 1).

**Stock and the fallback.** C90862 has **14** in stock (chronically low, `hardware/CONTEXT.md`); five boards need 5 plus attrition. Fallback with the same footprint, pinout, address and register map: **BQ24195LRGER (C417486, 3 196)**. Differences that matter here (from `docs/references/bq24195/DATASHEET_REFERENCE.md`): system current 2.5 A instead of 4.5 A, and a lower PMID minimum (20 µF, which the v8 PMID bank exceeds anyway). The schematic carries the v7 part; Phase 19 preflight switches the LCSC number if C90862 is short, and records it as built (CL-14 lesson). If the L part is fitted, the battery-side budget below drops to 2.5 A.

**Rows j and k as built.** Row j: SJ3 centre = D−, pad 1 (default) = D+, pad 3 = GND; plus an SJ2 from D+ to GND (open in v8, closed in v7). Row k: SJ3 centre = R35's top end, pad 1 (default) = BQ_REGN, pad 3 = +3.3V_MCU (v7's +3.3V). Footprints as Parts → Footprints (SJ3 pad rule: pad 2 common, pad 1 default).

### Battery connection and protection

**Connector (OQ-4): XT30, board side male (J8, XT30UPB-M, C428721, through-hole), cell lead female (XT30U-F, C99102, user-supplied cable).** Keyed and polarised by its housing shape, so a cell can't go in backwards through the connector (B1). 15 A rated (listing), well above the 7 A fuse. The source side carries the female so its live contacts are shrouded (common practice, argued). Why not JST-PH (v6, CL-10): 2 A per contact (listing for C173752), below the battery-side current (budget below). Mechanism 5 (holder body over B.Cu copper) disappears: no holder on the board.

**Reverse polarity, gate drive and inrush: back-to-back P-MOSFETs with a slow gate (Q20, Q21, CSD25402Q3A, C111356).** Replaces v7's Q2/R33/R34.
- Wiring: Q20 drain on BAT_FUSED (cell side), Q20 source and Q21 source joined (BAT_COMMON), Q21 drain on VBAT. Gates joined (BAT_GATE). R60 1 MΩ BAT_GATE–BAT_COMMON (holds off). C60 220 nF BAT_GATE–BAT_COMMON. C61 22 nF BAT_GATE–VBAT (Miller cap, sets the ramp). R61 47 kΩ from BAT_GATE to SW4's common; SW4's ON throw to GND, OFF throw unconnected.
- **B1, reversed cell (mechanism 1): blocked.** With the cell side negative, Q20's body diode (anode at its drain) is reverse-biased, and the gate sits at about BAT_COMMON (≈ 0 V), so Vgs ≈ 0 and both FETs are off. Nothing on the board sees the negative voltage except F3, J8 and Q20's drain (VDS −20 V rating, SLPS454B). There is no polarised capacitor on the cell side (v7's C30 moves to VBAT).
- **B2, under-driven series FET (mechanism 2): fixed.** On, Vgs = −Vcell × 1 M / (1 M + 47 k) = −0.955 × Vcell: −2.87 V at a 3.0 V cell, −4.0 V at 4.2 V. SLPS454B specifies RDS(on) at −2.5 V: 13.3 mΩ typ / 15.9 mΩ max (−4.5 V: 7.7 / 8.9 mΩ). Two in series ≤ 32 mΩ. At the 4.5 A budget that is ≤ 0.65 W total, ≈ 0.32 W per FET, ≈ +18 °C at RθJA 55 °C/W (1 in² 2 oz, SLPS454B; argued for our copper). v7's AO3401A at −1.5 to −2.1 V had no specified RDS(on) at all. VGS abs-max ±12 V vs at most −4.35 V here.
- **B3a/B3b, hot-plug inrush (mechanism 3): slew-limited.** At plug-in (SW4 already ON), BAT_COMMON jumps to Vcell − VSD through Q20's body diode; C60 (10 × C61) drags the gate up with it, so Vgs ≈ −Vcell × 22/242 ≈ −0.3 V, below VGS(th) −0.65 V min: Q21 stays off. The gate then falls through R61 and Q21 turns on along the Miller plateau with dV/dt ≈ I_R61 / C61 ≈ (2.7 V / 47 kΩ) / 22 nF ≈ 2.6 V/ms. Into the ≈ 400 µF downstream (VBAT 10 µF + 47 µF, SYS 2 × 10 µF + 220 µF through the BATFET, VSYS_SENSE, and +5V via L2 and U6's body path) that is ≈ 1 A, against the BATFET's 9 A latching OCP and F3's 7 A. Switching SW4 ON gives the same ramp. All values **argued** (first-order hand calculation; no simulation); Phase 10 sanity-checks them and the bring-up relay measures VBAT's ramp.
- **Charging.** The pair conducts both ways when on, so the BQ charges the cell through it (ICHG default 2048 mA: ≈ 0.13 W in the pair). With SW4 OFF both body diodes face each other: the cell is isolated in both directions, so **no charging with SW4 OFF** (trade-off, below).
- **Fuse: F3, Littelfuse 0451007.MRL (C99548, 7 A, 2410), between J8 + and Q20.** First part after the connector, so a short anywhere on the board (including a failed FET) opens it. Rating: the battery-side continuous current is bounded by the BQ's 4.5 A system rating (budget below); 7 A × 0.75 derating (argued, usual fuse practice) = 5.25 A ≥ 4.5 A. Its breaking capacity is listed as 50 A at 125 V; at 4.2 V against a 30Q's short-circuit current that is argued adequate, not datasheet-confirmed at low voltage. v7 had no battery-side fuse (Phase 2 deviation).
- **No v7 position for the battery protection.** v7's arrangement is itself the damage risk (B1/B2), the cell is on a connector instead of a holder, and the v7 boards still exist for that comparison. Not a suspected I²C variable, so the brief's A/B/A rule doesn't call for one (argued; the approval summary asks the user).

**SW4 "BATT" (new, MSK12C02, C431540, same switch as SW1).** ON connects the cell (through the slow gate), OFF isolates it. Why: with row i at v8 the boost runs whenever VSYS exists (next subsection), so the battery needs its own off switch; the 30Q is an unprotected cell, and SW4 OFF stops the BQ's quiescent drain (32 µA BATFET on, SLUSB97A) in storage. Gate current only (µA), well inside the switch's 50 mA. Cost: the board can't charge with SW4 OFF; charge with SW4 ON (the board then runs too).

**Cell temperature (new row l).** v7's TH1 is on the PCB and senses the board, not the cell (Phase 2 mechanism 7), while the default charge current is 2048 mA. v8 adds J9 (JST-PH 2-pin, S2B-PH-K-S, C173752) for a 10 kΩ 103AT NTC taped to the cell, and **row l**, an SJ3: centre = the TS network's NTC leg (R37 ∥ NTC to GND), pad 1 (default) = J9, pad 3 = TH1 (v7). R36/R37 stay (5.6 k / 30 k, the TI divider for a 103AT). With the default and nothing on J9, TS sits at R37's share of REGN ≈ 84 %, above the 73 % cold threshold, so the BQ **suspends charging and the STAT LED blinks** (fault) until an NTC is fitted: a safe-fail default (argued from the Phase 1 TS percentages). Alternative if the user prefers: default pad 1 = TH1 (v7 behaviour, charges without a cell sensor).

### Boost and enable (row i): the boost runs whenever VSYS exists

**What PWR-002 showed.** On v7, SW1 is the boost's only enable (CL-11). At its GND throw the boost doesn't run even on USB: +5V sits at ≈ 3.78–3.80 V (VSYS through U6's body path), U8 drops out (+3.3V 2.70–2.71 V), and the Mac finds no ESP32 (#0004, #0005, A/B/A). At the other throw the same boards regulate (+5V 5.10–5.12 V) and enumerate. So on v7 "SW1 off + USB" looks exactly like a dead board, and #0001/#0002's "burnt out" may have been just that (B8, argued for those two boards).

**Decision: row i default changes to v8 = BOOST_EN tied to VSYS_SENSE (always on; v6's arrangement).** The board runs on USB whatever any switch says, and on battery whenever SW4 is ON. The off switch for the battery is SW4 (above), which is where an off switch is needed. SW1 stays fitted and wired exactly as v7 (A → VSYS_SENSE, common → its own net, C → GND, R2 100 k pull-down on BOOST_EN), so the **v7 position (row i pad 3 = SW1's common on BOOST_EN) rebuilds v7's net membership**, including the "SW1 off = dead on USB" behaviour for A/B. Silk: SW1 "BOOST (row i v7)", SW4 "BATT".
- **This changes an approved default.** Phase 3 (W2 part 1) approved row i with v8 = v7 (SW1). The new default comes from PWR-002, which landed after that approval; it goes to the user in the Phase 7 approval (task 5). The SJ3 pad rule from Parts still holds, with pad 1 (default) now = VSYS_SENSE and pad 3 = SW1 common.
- EN abs-max 7 V vs VSYS_SENSE ≤ 4.35 V; EN high threshold 1.2 V; R2 then draws ≈ 40 µA from VSYS_SENSE (TPS61088 reference).
- B4 (boost enabled into a load at plug-in): with EN always on, the boost starts as soon as VIN passes its 2.7 V UVLO, with the 11.3 ms soft-start (SS 47 nF), after the battery pair's ≈ 1.5 ms ramp. A heavy +5V load at start-up draws from the cell through the fully driven pair and F3, not an under-driven SOT-23 (argued).

**Boost parts unchanged from v7.** U6 TPS61088RHLR; L2 2.2 µH 10 A; FB 180 k / 56 k (5.07 V nominal; measured 5.096–5.12 V on #0003/#0004/#0005, V7R-020, PWR-002); FSW 100 k; ILIM R42 100 k (10.6–13.0 A peak, PFM); SS 47 nF; MODE floating (PFM); output 4 × 22 µF 25 V (C45783, the v7 as-built part, CL-14). The boost isn't suspected of anything, so keeping it keeps v7's +5V behaviour for A/B.

### Regulators (row c): AMS1117 for the MCU, AP2112K for the bus

**Decision.**
- **U8 AMS1117-3.3 (C6186, basic) feeds +3.3V_MCU**, as on v7. In row c's v7 position it feeds everything, so the v7 position uses v7's regulator type (CL-08), not a substitute.
- **U10 AP2112K-3.3TRG1 (C51118, SOT-25) feeds +3.3V_BUS** in the v8 position. It is v6's bus regulator (CL-03), so v8's split repeats v6. 600 mA rating vs the bus rail's load (pull-ups, TCA, INA219, three sensor modules: tens of mA average; the VCNL IR pulses come from the flex boards' anode capacitors, Parts → row c note).
- **U10 EN tied to +3.3V_MCU** (after link h1). The bus rail can then only be up while U3 is powered: it comes up after +3.3V_MCU and drops with it.

**Dropout margin from the actual +5V.** Measured +5V: 5.096–5.098 V (#0003, V7R-020), 5.10–5.12 V (#0004/#0005, PWR-002). Less link h3 (≤ 50 mΩ × ≈ 1.7 A ≈ 0.09 V, argued) → ≈ 5.0 V at the regulators.
- AMS1117: 1.1 V at 800 mA (JLC listing). 5.0 − 3.3 − 1.1 = **0.6 V margin** at 800 mA. The maker's maximum dropout is higher than the listing's figure (argued; Phase 10 reads the AMS1117 datasheet). Dissipation ≈ 1.7 V × 0.5 A ≈ 0.85 W at a WiFi peak, SOT-223 (as v7).
- AP2112K: 250 mV at 600 mA (listing). **≈ 1.45 V margin.** Dissipation at a 50 mA bus load ≈ 0.09 W; at its full 600 mA it would be ≈ 1 W, too much for SOT-25 (argued), but the bus load is nowhere near that.
- Neither regulator is fed from VSYS, so neither depends on the cell voltage; both depend on the boost running, which row i now guarantees in v8.

**Back-powering U3 through the pull-ups (Phase 3 check).**
- *Bus rail up, MCU rail down:* the 2.2 k upstream pull-ups would push ≈ (3.3 − 0.6) / 2.2 k ≈ 1.2 mA per line into U3's GPIO16/15 (or 43/44) clamp diodes, ≈ 2.5 mA into an unpowered VDD3P3 (argued from the S3's ESD structure, not a datasheet value). U10's EN on +3.3V_MCU prevents that state in the v8 position. Residual: in row i's v7 position with SW1 off, +5V ≈ 3.8 V puts U8 in dropout (+3.3V_MCU ≈ 2.7 V) while U10 may still regulate (EN is high above ≈ 1.5 V, argued from the AP2112 class): bus rail 3.3 V vs U3 at 2.7 V, ≈ 0.6 V across a clamp diode, so microamps (argued). Phase 10 confirms U10's EN threshold.
- *MCU rail up, bus rail down* (row c shunt off): the pull-ups hang from a dead rail; U3's pins are open drain, so nothing is driven into the bus rail (argued). The bus devices are unpowered and the bus reads low.
- *v7 position (shared):* one rail, no back-power path (as v7).

### Current-measure links (row h): four rails

Per link: the part below, plus an unfitted 1 × 2 2.54 mm header beside it (Parts → Headers) and a test point on each side (Test points). Lift the part to insert an ammeter. Rated current for a 0 Ω part is not in the JLC listing; it is derived as I = √(P / R_max) with R_max = 50 mΩ, the usual jumper-resistance limit for thick-film 0 Ω parts (**argued**; Phase 10 confirms from each maker's sheet).
| Link | Rail | Max current (source of the bound) | Part | LCSC | Rating | Margin |
|---|---|---|---|---|---|---|
| h1 | +3.3V_MCU_REG → +3.3V_MCU | 1 A (AMS1117 rating) | 0 Ω 1206, 250 mW | C17888 (basic) | ≈ 2.2 A (argued) | 2.2× |
| h2 | +3.3V_BUS_HDR → +3.3V_BUS | 1 A in v7 position (AMS1117); 0.6 A in v8 (AP2112K) | 0 Ω 1206, 250 mW | C17888 (basic) | ≈ 2.2 A (argued) | 2.2× |
| h3 | +5V → +5V_CORE | ≈ 1.7 A (U8 1 A + U10 0.6 A + D5/IC1/LED; argued sum of ratings) | 0 Ω 2512, 1 W | C25469 | ≈ 4.5 A (argued) | 2.6× |
| h4 | F1 out → +5V_TO_LEDS | 3 A (F1) | **10 mΩ 1 % 2512, 3 W** shunt | C2903468 | 17 A by power (listing: 3 W at 10 mΩ) | 5.7× |

- **h4 is a 10 mΩ shunt, not 0 Ω.** The 3 A LED rail is the one where a 0 Ω part's derived rating (≈ 2.2 A for 1206, ≈ 4.5 A for 2512) is either too low or argued. A 3 W shunt's rating follows from its listed power. It also reads 10 mV/A across the unfitted header pins without lifting anything. Cost: up to 30 mV less on the LED strip at 3 A, which is not a v7 variable anyone suspects (v7 position "closed" is then 10 mΩ, not 0 Ω).
- **No link on VSYS.** R44 (10 mΩ) with the INA219 already measures VSYS → VSYS_SENSE, which carries up to 4.5 A.
- **No link on the battery path.** It carries up to 4.5 A, and an ammeter there is better put in the battery cable.

### Other v7 deviations fixed

| Item (Phase 2 deviation) | v7 | v8 | Reason / source |
|---|---|---|---|
| PMID capacitance | C25, C26: 2 × 10 µF 0603 = 20 µF nominal | **4 × 22 µF 25 V X5R 1206** (C12891, basic) = 88 µF nominal | bq24195 asks ≥ 60 µF on PMID (20 µF for the L part; reference, PMID row). 22 µF 25 V in 1206 at 5 V bias is argued to keep ≈ 60–70 % (≈ 55–60 µF effective); Phase 10 checks the Samsung DC-bias curve and adds a fifth if needed |
| VBAT capacitor | none | **10 µF 25 V 0805** (C15850, basic) at U5 pins 13/14, plus v7's C30 47 µF 35 V electrolytic (C72522, as built) moved from BAT_RAW onto VBAT | BQ pin table: BAT decoupled with 10 µF. C30 on VBAT is behind the reverse blocking, so it can never see a reversed cell, and it damps BAT ringing (B3b) |
| Battery-side fuse | none | F3 7 A (above) | Phase 2 deviation; B2/B4 worst cases |
| J7 shell | Schematic: J7 pin "SH" on GND (v7 `circuit-context.json`). PCB: the rear shell legs have no net (Phase 2 probe) | Shell on **GND**, as v7's schematic intended. Phase 8 checks that every shell pad of the J7 footprint carries the SH pin number, so the PCB matches | Argued: the v7 footprint's rear-leg pads don't carry the SH number. With the battery on a cable, the BAT_RAW-to-shell bridge (B5) is gone anyway |
| Cell temperature | TH1 on the PCB | Row l, J9 cell NTC (above) | Phase 2 mechanism 7 side finding |
| R44 shunt | MFJ12HR010FT 10 mΩ 1 W (C1322424, **2 in stock**) | **HoJLR2512-3W-10mR-1 %** (C2903468, 86 331): same 10 mΩ 1 %, 2512 | Same value, so INA219 calibration in firmware is unchanged |
| STAT LED rail | STAT unconnected | Orange LED + 2.2 k from **VSYS** to U5 STAT (confirmed: the BQ is kept) | VSYS exists whenever USB is in or SW4 is ON, so it shows charging and faults (including row l's "no NTC" blink); off with SW4 OFF and no USB, so no storage drain |

### Power budget (argued, from ratings)

- **Battery side:** ≤ 4.5 A, the BQ24195's system-current rating (2.5 A with the L part). At a 3.0 V cell and 90 % boost efficiency that is ≈ 12 W, so +5V can deliver ≈ 2.4 A in total; after the core load (≈ 0.6 A at a WiFi peak, through U8), the LED strip on battery should stay under ≈ 1.8 A at a low cell. F1 (3 A) allows more than the BQ is rated for, as it did on v7. Phase 12 note: cap LED brightness in firmware for battery use.
- **USB side:** 1.5 A at 5 V (row j) less the buck's loss ≈ 7 W, so +5V ≈ 1.3 A without a cell (argued); the BQ supplements from the cell when one is connected.
- **Over-discharge:** not designed here. The boost stops at its 2.4–2.5 V UVLO; whether the BQ's BATFET disconnects a deeply discharged cell in battery-only mode isn't in `docs/references/bq24195/` (Phase 10 reads SLUSB97A). SW4 OFF is the storage answer.

### Plane-planning input (layout, not designed here)

On v7, In2 is split between +3.3V and +5V, and 16 signal tracks cross the split gap, the USB pair and SDA/SCL included (board model, Phase 6; SESSION Worker #5/#6). v8 has more power nets on that layer's candidates (+3.3V_MCU, +3.3V_BUS, +5V_CORE, +5V_TO_LEDS, VSYS). The layout phases should plan the inner-layer split so that no I²C, USB or test-point signal crosses a gap (or route those over solid GND), and keep the battery high-current path (J8 → F3 → Q20/Q21 → VBAT → U5) and the two switching loops on the outer layers with GND under them.

## GPIO allocation

**Status: approved by the user 2026-11-02 (W2 part 1).** Sources: Espressif *ESP32-S3-WROOM-1 & WROOM-1U Datasheet* v1.8, Table 3-1 (pin definitions) and Chapter 4 (boot configurations); v7 `hardware/pcb-main/kicad/circuit-context.json` @ `c2acffc` (U3 pin → net); `firmware/include/pin_config.h`; changelist CL-02, CL-04, CL-05, CL-07; card V7R-019; NOTEBOOK desk (e) (2026-10-27).

**Module constraints (datasheet v1.8).**
- N16R8 has Octal SPI PSRAM: module pins 28–30 (IO35, IO36, IO37) "are connected to the Octal SPI PSRAM and are not available for other uses" (Table 3-1 note b). Leave them unconnected.
- GPIO47/48 run at 1.8 V only on R16V modules (note c). On N16R8 they are ordinary 3.3 V GPIOs.
- Strapping pins (Table 4-1): GPIO0 weak pull-up (1 = SPI boot); GPIO45 weak pull-down (0 = VDD_SPI 3.3 V with the default eFuse; 1 would select 1.8 V, Table 4-4); GPIO46 weak pull-down (boot mode with GPIO0, and ROM print control); GPIO3 floating, read as JTAG source only with JTAG eFuses burnt (Table 4-5; defaults 0). Nothing on the board may pull GPIO45 or GPIO46 high at reset.
- ROM messages go to UART0 **and** USB Serial/JTAG by default (§4.3). So on v7 the ROM drives its boot log push-pull onto SDA through GPIO43 = U0TXD at every boot (CL-02, V7R-018). With the bus off GPIO43/44, the same log is readable on a UART0 header.
- USB: GPIO19 = USB_D−, GPIO20 = USB_D+ (native USB / CDC, CL-07). Unchanged.

**Allocation.** "v8" is the default jumper position; "v7" is the jumper position that rebuilds v7's net membership.
| Module pin | GPIO | v7 net (`c2acffc`) | v8 use | Jumper | Notes |
|---|---|---|---|---|---|
| 37 | 43 (U0TXD) | /I2C_SDA | v7: SDA. v8: UART0 TX to the UART0 header | (a) SDA | Pad-37 joint is in V7R-010's measured path; card (j) pending (OQ-5) |
| 36 | 44 (U0RXD) | /I2C_SCL | v7: SCL. v8: UART0 RX to the UART0 header | (a) SCL | |
| 9 | 16 | /LED_DATA | v8: **SDA** (default pair). v7: LED_DATA | (a) SDA, (g) | The pad V7R-019 measured on #0003: SDA low 109 mV, BQ + both VCNL 100 % ACK (one board, bodge wire) |
| 8 | 15 | — (no copper) | v8: **SCL** (default pair) | (a) SCL | Adjacent to pin 9; XTAL_32K_P function unused |
| 11 | 18 | — | v8: LED_DATA (D5 DIN, IC1 1A) | (g) | Frees GPIO16 for the bus |
| 18 | 10 | /TCA_RESET | TCA_RESET (R6 10 k pull-up), unchanged | — | Test point kept |
| 23 | 21 | /CHRG_INT | CHRG_INT (BQ INT, R38 10 k pull-up), unchanged | — | Phase 7 may change the charger; then this is its INT/STAT input |
| 21, 20, 19 | 13, 12, 11 | INT1, INT2, INT3 (U3 only, no-connect) | INT1–3 to test points (as v6 TPIO11–13, CL-05). Not wired to J4–J6 (4-pin, CL-16) | — | Reserved for a future second bus or sensor INT (dual-bus-i2c idea used 11/12) |
| 24 | 47 | — | Debug LED DBG1 (blue), firmware-driven | — | |
| 25 | 48 | — | Debug LED DBG2 (white), firmware-driven | — | |
| 27 | 0 | GPIO0_BOOT (R51 10 k, SW3) | unchanged + test point | — | Strapping |
| 3 | EN | EN (R50 10 k, C50 1 µF, SW2) | unchanged + test point | — | |
| 13, 14 | 19, 20 | USB_DN_MCU / USB_DP_MCU | unchanged | — | No test pads on the USB pair (stubs on a 90 Ω pair) |
| 39, 38, 4–7, 12, 17, 22, 10, 31, 32–35 | 1, 2, 4, 5, 6, 7, 8, 9, 14, 17, 38, 39, 40, 41, 42 | — | Spare: to the spare-GPIO header (15 signals) | — | 39–42 are the pad-JTAG pins (MTCK/MTDO/MTDI/MTMS); usable as GPIO with default eFuses |
| 15, 26, 16 | 3, 45, 46 | — (module defaults) | Strapping spares: test pad only, nothing else on the net, silk "STRAP" | — | Never pull 45/46 up; see constraints |
| 28–30 | 35–37 | — | Not connected (PSRAM) | — | |

**Bus master pairs.** Default (v8) pair: SDA = GPIO16, SCL = GPIO15. Alternate (v7) pair: SDA = GPIO43, SCL = GPIO44. SDA and SCL each have their own jumper, so firmware must allow the four combinations (Phase 12 env/pin flags; the common ones are both-v8 and both-v7, and SDA-only matches V7R-019). Why GPIO16 for SDA: it is the only pad measured on a v7 to give a normal low on this bus with BQ and VCNL ACKing (V7R-019 Row 1), so the v8 default repeats a measured configuration. Argued, not measured: any ordinary pad would do (GPIO44 ≈ 32 Ω, V7R-014; dev-board GPIO43/GPIO4 ≈ 30 Ω, V7R-017).

**Debug-track input still pending (OQ-5).** Card (j) (castellation 37 vs board pad) hasn't run. The allocation doesn't depend on it: jumper (a) keeps GPIO43 able to drive the bus, so v8 can repeat (j) and V7R-019 A/B/A without rework. If (j) points at the joint, Phase 4/8 review the U3 footprint pad and paste for pin 37.

## Jumper matrix

**Status: approved by the user 2026-11-02 (W2 part 1), including the v7-valued defaults of rows d, f, h and i.** Rows a–h are the PLAN candidates; i–k come from changelist §3 and Phases 1–2. Every row has a v7 position that rebuilds v7's net membership for the nets it touches (Phase 9/11 check this against `c2acffc`). Defaults are the v8 position (BRIEF), except where the row says v8 = v7 because no fix is claimed. "SJ2" = 2-pad solder jumper, "SJ3" = 3-pad solder jumper (centre common); footprints and the SJ3 pad rule are in Parts.

**Implementation changed by the W2 part 2 decision (user, 2026-11-02):** rows a, b, c, d (upstream) and f are now 2.54 mm pin headers with push-on shunts instead of solder jumpers. The positions (v7, v8, defaults) did not change; only the implementation column did. For a header row, "default" means where the shunt ships fitted. Details and footprints: Parts → Jumper headers.

| # | Toggles | v7 position | v8 position (default) | v6 (where it differs) | Map row / CL-ID | Implementation |
|---|---|---|---|---|---|---|
| a | Bus master pins, SDA and SCL separately | SDA = GPIO43, SCL = GPIO44; UART0 header disconnected | SDA = GPIO16, SCL = GPIO15; GPIO43/44 to the UART0 header | T-Display pins "43"/"44" (other die path) | master: module/path, pin role; V7R-019; CL-02 | Per line: one 1 × 4 header, pins 1–4 = U3_IO16 / I2C_SDA / U3_IO43 / UART0_TX (SCL line: U3_IO15 / I2C_SCL / U3_IO44 / UART0_RX). v8: shunts on 1–2 and 3–4. v7: one shunt on 2–3, which physically blocks both other positions, so GPIO43 can't be on the bus and the UART0 header at once. No bus shunt (1–2 and 2–3 empty) = U3 off the bus (row e) |
| b | Cable-facing protection on CH0–CH2 SDA/SCL | Bypassed: series R shorted, TVS ground leg open | Fitted: series R in line, TVS to GND | as v7 (none) | notebook 2026-10-31 candidate (1); net-stress form of (c) | Per line: series R with a 1 × 2 header across it (shunt off = v8; shunt on = v7). Per connector: TVS with a 1 × 2 header in its GND leg (shunt on = v8; off = v7). 9 headers. The header in the TVS return adds a few nH (argued), which raises the clamp during the ns ESD edge; the header sits beside TVS pin 4 with its GND pin on a via at the pad, and the 47 Ω series R takes more of the burden. Residual in v7 position: the floating TVS's capacitance stays on the lines (argued, small: TPD2E2U06, 1.9 pF max, Parts) |
| c | MCU 3.3 V vs bus/pull-up 3.3 V | Shared: one regulator feeds U3 and the pull-ups, TCA, INA219, J4–J6 | Separate: +3.3V_MCU and +3.3V_BUS from two regulators | Separate (AP2112K for the bus, T-Display LDO for the MCU) | master supply; CL-03, CL-08 | 1 × 3 header on the +3.3V_BUS feed: pin 2 = +3.3V_BUS, pin 1 = bus regulator output (v8, shunt fitted), pin 3 = MCU regulator output (v7). No shunt = bus rail unpowered (neither position). Phase 7 picks the parts; for a faithful v7 position the shared regulator should be the v7 type (AMS1117, CL-08) or the difference recorded. Back-powering U3 through the pull-ups when only the bus rail is up: Phase 7 checks |
| d | On-board pull-up values | Upstream 2.2 kΩ (R28/R29); no on-board pull-ups downstream | Upstream 2.2 kΩ (**v8 = v7**: no pull-up fix is claimed; notebook fix (ii) "not pursued"); downstream none fitted | as v7 | master: pull-up current; desk (d) | Upstream per line: one 2 × 3 selector header; odd pins 1/3/5 = the bus line, even pins 2/4/6 = 2.2 k / 4.7 k / 10 k, each resistor's other end on I2C_PU_RAIL. A shunt across a column (1–2, 3–4 or 5–6) picks one value; 1–2 (2.2 k) ships fitted. One shunt can't connect two values. No shunt = no upstream pull-up. Downstream per channel line: one footprint (4.7 kΩ, Parts) in series with an SJ2, open. Values and rise time: Parts |
| e | External master on the bus | Header disconnected | Header disconnected | — | master: identity; V7R-004 / F-12 method | 4-pin header (SDA, SCL, GND, +3.3V_BUS sense) on the bus side, joined by SJ2 per line (open). To use: take the (a) bus shunts off (leave 1–2 and 2–3 empty), close these. No second master footprint (OQ-2) |
| f | BQ on the I²C bus | Connected | Connected (**v8 = v7**; firmware still talks to it) | — | symptom identity: causal; STATE §3; L-Ph8 | 1 × 2 header on U5 SDA and on U5 SCL (shunt fitted). Applies only if Phase 7 keeps the BQ24195 or another I²C charger |
| g | LED_DATA source | GPIO16 drives D5 + IC1 | GPIO18 drives D5 + IC1; GPIO16 free for the bus | — | desk (e); CL-06 | SJ3: centre = LED_DATA (D5 DIN, IC1 1A, test point), side 1 = GPIO16, side 2 = GPIO18. Interlock: (a) SDA = v8 with (g) = v7 puts the LED loads on SDA, which is V7R-019's fixture state (allowed, a deliberate third state) |
| h | Rail current-measure links | Closed | Closed (**v8 = v7**) | — | debug goal | Per rail: 0 Ω (1206) with an unpopulated 2-pin 2.54 mm header beside it; lift the 0 Ω to insert an ammeter. Rails chosen in Phase 7 (candidates: +3.3V_MCU, +3.3V_BUS, +5V core loads, +5V_TO_LEDS, VSYS) |
| i | Boost enable | SW1 → BOOST_EN (R2 pull-down) | SW1 (**v8 = v7**) | EN tied to VIN (VSYS_SENSE): always on | CL-11; #0004 boost not running (Phase 2, V7R-020) | SJ3: centre = BOOST_EN (or its Phase 7 equivalent), side 1 = SW1 common, side 2 = boost VIN. Lets the bench take SW1 out of the path |
| j | BQ D+/D− (input source detection) | Both to GND: SDP, IINLIM 100 mA without I²C | D+ shorted to D−: DCP, 1.5 A without I²C | as v7 | BQ fault (Phase 1, SLUSB97A §8.3.1.3); "verified unchanged" BQ support | SJ3: centre = D−; side 1 = GND, side 2 = D+, with D+ also to GND through an SJ2 (closed in v7, open in v8). Conditional: only if Phase 7 keeps the BQ24195 (fix option 1) |
| k | BQ OTG pull-up source | R35 10 k to +3.3V | Phase 7 decides (option 2: REGN through a resistor) | as v7 | BQ fault (Phase 1, option 2) | SJ3: centre = OTG pull-up resistor, side 1 = +3.3V, side 2 = REGN. Conditional on Phase 7 keeping the BQ24195 |

Rows considered and not added: D5 on-board pixel isolation (CL-06; row g already takes the LED loads off GPIO16); USBLC6 fitted vs bypassed (CL-12; jumpers on the USB pair cost more than they test); LDO type alone (CL-08; folded into c); B.Cu GND pour and I²C route (CL-20, CL-21; copper, not jumperable: the board model and partner review cover them); J7 shell net, battery holder, reverse protection (power path, Phase 7).

**All-v7 configuration** (for A/B/A): a = v7 both lines, b = bypassed, c = shared, d = 2.2 k upstream only, e = open, f = closed, g = GPIO16, h = closed, i = SW1, j = GND, k = +3.3V. The bring-up relay (Phase 19) carries this list.

### Decisions (user, 2026-11-02)

- **OQ-2: no second master footprint.** Row (e) is a 4-pin external-master header behind open SJ2s only. Reason: it is the method the bench already uses (Nano ESP32 as external master, V7R-004) and adds no bus copper by default. Not chosen: a DevKitC-1 socket or a fixed dev-board footprint (board area, more nets near the bus, a new 3.3 V rail question).
- **OQ-4: board ≤ 100 × 100 mm; the 18650 is on a cable through a keyed, polarised connector.** Reason: the cheapest JLC tier (PLAN), no holder body over copper (Phase 2 mechanism 5), and a reversed cell is blocked at the connector (mechanism 1). Cost: v7's battery-in-holder arrangement can't be A/B'd on v8 (the v7 boards still can). Phase 7 picks the connector (v6 used a JST-PH 2-pin, CL-10).

## Test points

**Status: approved by the user 2026-11-02 (W2 part 1), including the seven debug LEDs.** Net names are v7's (`c2acffc`) where the net exists; new names come from the jumper matrix. Power-net names change if Phase 7 changes the power path; the rule "every rail gets a test point" stays. v7 had TP1 VSYS, TP2 VBAT, TP3 PVBUS, TP4 GND and TPIO10/16/21/43/44, and no +3.3V or +5V pad (CL-26).

**Ground points.** Every signal or rail test point has its own GND pad beside it (not shared with a neighbour), within ground-spring reach. Spacing rule (Phase 4, from bench-demonstrated SQ500 spring placements): signal-to-ground gap 1.0–3.0 mm copper edge to copper edge (Parts → Footprints). GND pads are big enough for two springs at once (V7R-019 V5b: "All four things won't fit on C"). Headers count as test points when a GND pin sits next to each signal pin.

**I²C, master side of the TCA** (upstream).
| Net | What it is | Why |
|---|---|---|
| I2C_SDA, I2C_SCL | Bus side of the (a) jumpers: pull-ups, TCA, INA219, BQ (via f), external header | Probe point S1-equivalent (v7 TPIO43/44 sat on U3's pin net; here the bus and the pin are separate nets) |
| U3_IO43, U3_IO44 | U3 pins 37/36, between the module and the (a) jumper | Measures the pad itself (V7R-010 K point, card (j)); doubles as the UART0 TX/RX probe |
| U3_IO16, U3_IO15 | U3 pins 9/8, between the module and the (a) jumper | Same for the v8 pair |
| BQ_SDA, BQ_SCL | U5 side of jumper (f) | Isolates BQ's own pin level from the bus |
| I2C_PU_RAIL | the rail feeding the upstream pull-ups (row c, d) | Pull-up current and rail droop at the pull-ups |

**I²C, channel side of the TCA** (CH0–CH2 → J4–J6). With row (b) the series R splits each line into a TCA-side net and a connector-side net; both get a test point.
| Net | Count |
|---|---|
| CHn_SDA, CHn_SCL (TCA side), n = 0..2 | 6 |
| CHn_SDA_CONN, CHn_SCL_CONN (connector side, at J4–J6 pins 3/4) | 6 |

**Rails** (v7 names; Phase 7 may rename). VBUS_RAW (before F2), Protected_VBUS (TP3), BQ_PMID, BQ_REGN, VSYS (TP1), VSYS_SENSE, VBAT (TP2), BAT_RAW, +5V, +5V_TO_LEDS, +3.3V_MCU, +3.3V_BUS (one point per 3.3 V regulator output; two if row c is separate). Each 0 Ω current link (row h) also gets a point on each side.

**Power control nodes** (Phase 2 hand-off: hard to reach on v7): BOOST_EN, BOOST_VCC (U6 pin 1), BOOST_FB (U6 pin 17), PMOS_GATE (or Phase 7's equivalent series-FET gate), OTG_BIAS, BQ_TS, BQ_ILIM. Switch nodes (BQ_SW, BOOST_SW) get no pad (dv/dt; scope at the inductor pad instead).

**MCU and control.** EN, GPIO0_BOOT, TCA_RESET, CHRG_INT, LED_DATA (the (g) centre), INT1–INT3 (GPIO13/12/11), GPIO3/45/46 (bare strap pads, see GPIO allocation). No pads on the USB pair.

**Headers** (signal pin beside a GND pin):
- UART0: 1 × 4, 2.54 mm: GND, TX (GPIO43), RX (GPIO44), NC. 3.3 V logic. Joined through the (a) selector headers (pins 3–4).
- External master (row e): 1 × 4, 2.54 mm: GND, SDA, SCL, +3.3V_BUS (sense/reference only).
- Spare GPIO: 2 × 15, 2.54 mm, signal row + GND row: GPIO1, 2, 4, 5, 6, 7, 8, 9, 14, 17, 38, 39, 40, 41, 42.

**Debug LEDs.** Each rail LED draws ≈ 1 mA and has an SJ2 in series (closed), so its load can be removed for an A/B against v7 (v7 had only D1 on +3.3V).
| LED | Signal | Colour | Notes |
|---|---|---|---|
| D1 (kept) | +3.3V_MCU | green | As v7 (R1 1 k) |
| new | +3.3V_BUS | green, silk "BUS" | Lit only when the bus rail is up (row c) |
| new | +5V | yellow | Shows the boost running (#0004 case) |
| new | Protected_VBUS | red | USB input present |
| new | charger STAT | orange | U5 STAT (pin 4, unconnected on v7) if Phase 7 keeps the BQ24195; open drain, LED anode on VSYS (Parts) |
| new | GPIO47 | blue, "DBG1" | Firmware-driven |
| new | GPIO48 | white, "DBG2" | Firmware-driven |
| D5 (kept) | LED_DATA | RGB (WS2812B-MINI) | As v7, on the (g) centre |

## Parts

Phase 4 filled the non-power parts below. Phase 7 adds the power parts (charger, boost, LDOs, battery connector, fuses, shunt).

**Status (non-power, Phase 4): approved by the user 2026-11-02 (W2 part 2), with the header/pad jumper split.** Stock: JLCPCB parts API (`selectSmtComponentList`, the same data as the JLC parts page), checked 2026-11-02. The JLC MCP was not available to the Worker. "basic" / "extended" is JLC's library type (extended parts carry a per-part assembly fee). Stock moves: Phase 19 preflight re-checks every number.

### Cable-facing protection (jumper row b)

Per connector J4–J6: one dual TVS on CHn_SDA_CONN / CHn_SCL_CONN, and one series resistor per line between the TCA pin and the connector. 3 TVS, 6 resistors.

| Item | Part | LCSC | Stock | Footprint |
|---|---|---|---|---|
| TVS, 2-line, per connector | TI **TPD2E2U06DRLR** (SOT-553-5): IO1 = pin 3, IO2 = pin 5, GND = pin 4, pins 1–2 NC | C1972959 (extended) | 4 078 | `Package_TO_SOT_SMD:SOT-553` (Phase 8 checks the symbol pin map against TI's DRL pinout) |
| Alternate TVS | TI TPD4E05U06DQAR (4-line, 0.5 pF, USON-10 0.5 mm pitch; two channels unused) | C138714 (extended) | 121 301 | `Package_SON:USON-10_2.5x1.0mm_P0.5mm` |
| Series R, per line | **47 Ω** 1 % 0603 | C23182 (basic) | 1 557 821 | `Resistor_SMD:R_0603_1608Metric` |
| Bypass (v7 position) | 1 × 2 header across each series R (shunt on = v7); 1 × 2 header in each TVS GND leg (shunt off = v7) | — | — | see Jumper headers |

**TPD2E2U06 price (JLC parts API, 2026-11-02).** US$0.3254 each in the 1–49 tier, so ≈ $0.98 for 3 (one board) and ≈ $4.88 for 15 (five boards). JLC's minimum buy for this part is 5 (API `leastPatchNumber`), with 1 attrition part. It is an extended part, so JLC adds a one-off loading fee per unique extended part per order: about US$3 (JLC assembly FAQ; their Oct 2026 blog gives $3.07 for Economic PCBA, with Preferred Extended parts exempt). Confirm in the live quote at Phase 19.

**TPD2E2U06 (TI SLLSEG9C, rev. Dec 2019, §6.5).** V_RWM 5.5 V. Line capacitance 1.5 pF typ, 1.9 pF max (1 MHz, 2.5 V bias). Leakage 10 nA max at 2.5 V. Clamp IO→GND 9.7 V at 1 A and 12.4 V at 5 A (TLP); R_DYN 0.5 Ω (DRL). Unidirectional to GND: there is no rail pin, so with its GND leg open (v7 position) the only thing left on the line is its capacitance.

**Why V_RWM 5.5 V and not 3.3 V.** The task asked for "3.3 V working voltage": the bus runs at 3.3 V, so any V_RWM ≥ 3.6 V (3.3 V + 10 %) works. A 5–5.5 V part leaks nA at 3.3 V; 3.3 V-rated parts are typically specified only at their V_RWM, in µA (argued from the class, not one part), which shows up as a DC load on a bus whose fault is a low-level question. The clamp still sits above the TCA9548A's 7 V abs-max (SCPS207H §6.1: SDx/SCx −0.5 to 7 V, ±20 mA input current). That is why the series R is there: during a strike the TVS takes the bulk of the current and the 47 Ω limits what reaches the TCA's own ESD structure, to roughly (12.4 − 7) V / 47 Ω ≈ 115 mA for the ns-scale pulse (argued; 100 Ω would halve it, at the VOL cost below).

**Rise time (argued, from datasheet values; no measured channel capacitance exists).** tr (30→70 %) = 0.8473 · Rp · Cb (PCA9546A datasheet §9.2.2, Eq. 2; UM10204 limit 300 ns at 400 kHz, which the firmware runs). When a channel is in use, the TCA and the rigid board's PCA are both switches, so the line sees the main board's upstream pull-up, the rigid board's R1/R2 (4.7 k, `hardware/CONTEXT.md`) and the selected sensor's 4.7 k (R6–R9) in parallel.
- Cb estimate ≈ 200 pF worst: TCA upstream Cio(off) 28 pF max + channel 7.5 pF (SCPS207H) + ESP32/BQ/INA219/test-point stubs ≈ 40 pF + an 825 mm cable (module 3, `docs/explorations/sensor-alternatives.md`) at ≈ 70–100 pF/m + rigid PCA + flex + VCNL ≈ 30 pF.

| Upstream (row d) | Downstream on-board (row d) | Rp effective | tr at 200 pF | Sink at VOL 0.4 V |
|---|---|---|---|---|
| 2.2 k (v7, v8 default) | none | 1.14 k | 193 ns | 2.5 mA |
| 4.7 k | none | 1.57 k | 266 ns | 1.8 mA |
| 10 k | none | 1.90 k | 322 ns (over 300 ns; 242 ns at 150 pF) | 1.5 mA |
| 10 k | 4.7 k | 1.35 k | 229 ns | 2.1 mA |
| 2.2 k | 4.7 k | 0.92 k | 155 ns | 3.2 mA (over the 3 mA I²C IOL at 0.4 V: don't use) |

- **TVS cost:** 1.9 pF max adds 0.8473 × 1.90 k × 1.9 pF ≈ 3 ns in the slowest row. Negligible.
- **Series R cost on rise time:** 47 Ω × the connector-side capacitance (≈ 100 pF) ≈ 5 ns. Negligible.
- **Series R cost on the low level** (the one that matters on this bus). When a far-end device pulls low, the main board's pull-up current crosses the series R: 2.9 V / 2.2 k ≈ 1.3 mA × 47 Ω ≈ 62 mV added at the master. Worst-case sum at U3: VCNL VOL 0.4 V + PCA Ron 20 Ω max × 2.5 mA (50 mV) + 62 mV + TCA Ron 30 Ω max × 1.3 mA (40 mV) ≈ 0.55 V, against VIL = 0.3 · VDD = 0.99 V. 100 Ω would make it ≈ 0.62 V. 47 Ω was chosen to keep the added offset to ≈ 60 mV on a board that is built to study low levels; the row (b) SJ2 removes it entirely for A/B.

### Footprints: jumpers, links, test points, ground points

All are KiCad 9 stock libraries (checked present in `/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/`). No LCSC part: solder jumpers and pads are copper only.

| Use | Footprint | Notes |
|---|---|---|
| SJ2, default **open** | `Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm` | Close with a solder blob. Rows d (downstream, 6), e (2), j (the D+ to GND SJ2; closed only in v7) |
| SJ2, default **closed** | `Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm` | Copper bridge from the factory: cut it to open, then it behaves as an open SJ2 (blob to re-close). JLC can't place a solder blob, so this is how "closed by default" ships. LED load jumpers only (D1, BUS, +5V, VBUS: 4) |
| SJ3 | `Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm_NumberLabels` | Pads 1–2 bridged from the factory. **Pad rule: pad 2 = common (the matrix's "centre"), pad 1 = the default position, pad 3 = the other position.** Rows g, i, j, k (j and k only if Phase 7 keeps the BQ24195). For row i the default (pad 1) is SW1, which is also the v7 position. The matrix's "side 1 / side 2" wording names positions, not pad numbers |
| 0 Ω link, signal | `Resistor_SMD:R_0603_1608Metric`, 0 Ω C21189 (basic, 20.45 M) | Where a jumper must be removable more than a few times, a 0603 0 Ω is the alternative to a bridged SJ2 |
| 0 Ω link, rail current-measure (row h) | `Resistor_SMD:R_1206_3216Metric`, 0 Ω C17888 (basic, 1.72 M) + `Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical` beside it, not fitted | C17888 is listed at 250 mW; its current rating isn't in the JLC listing. **Phase 7 checks the rating per rail**: +5V_TO_LEDS (behind F1, 3 A) probably needs a 2512 0 Ω or a pair |
| Signal test point | `TestPoint:TestPoint_Pad_D1.5mm` | Round, SMD. v7's TP1–TP4 used this; TPIO used D2.0 mm |
| Ground point | `TestPoint:TestPoint_Pad_2.5x2.5mm` | Square, so it reads as GND at a glance. Big enough for two springs (V7R-019 V5b: two tips and two springs "won't fit" on a 0603 pad) |
| Strap pads (GPIO3/45/46) | `TestPoint:TestPoint_Pad_D1.0mm` | Bare pad only (GPIO allocation) |

**Ground-spring reach (replaces the 5 mm working rule).** Measured on the bench, with SQ500 springs, edge to edge (copper), `lab/procedures/known-good-reference.md` ground table: pad F → U5 pins 5/6 at **2.64 mm** (V7R-009, V7R-010: "springs on F, 0 mm") and pad C → TPIO43/44 at **3.05 mm** on v7 (V7R-010 master end). The spring's maximum reach has not been measured, so the rule stays inside what has been done:
- **Gap between a signal test point and its ground point: 1.0–3.0 mm, copper edge to copper edge.** With a D1.5 signal pad and a 2.5 mm square ground pad that is 3.0–5.0 mm centre to centre, which matches the old working value.
- The 1.0 mm minimum keeps a slipping spring off the signal pad (a spring on the signal pad shorts it to GND).
- Not demonstrated on a board: the Rigol stock-probe spring (springs for it are on hand, `lab/procedures/known-good-reference.md`). Optional user check, not blocking: measure each probe's tip-to-spring reach with calipers; if it's well over 3 mm, the Phase 13 placement rules can relax the maximum.

### Jumper headers (W2 part 2 decision)

The jumpers that get switched often are 2.54 mm pin headers with push-on shunts (user, 2026-11-02): rows a, b, c, d upstream and f. Row d downstream, row e, rows g, i, j, k and the LED load jumpers stay as solder pads (Footprints above); row h is unchanged. Headers are hand-fit, or JLC through-hole if Phase 19 chooses it, as in the Headers table below. "Default" = where the shunt ships fitted.

| Row | Per board | Footprint | Pins | v8 (default) | v7 |
|---|---|---|---|---|---|
| a | 2 (SDA, SCL) | `Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical` | 1 U3_IO16/15, 2 I2C_SDA/SCL, 3 U3_IO43/44, 4 UART0_TX/RX | shunts 1–2 + 3–4 | shunt 2–3 only |
| b | 9 (6 bypass, 3 TVS GND) | `Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical` | bypass: CHn_x / CHn_x_CONN; GND leg: TVS pin 4 / GND | bypass off, GND leg on | bypass on, GND leg off |
| c | 1 | `Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical` | 1 bus regulator out, 2 +3.3V_BUS, 3 MCU regulator out | shunt 1–2 | shunt 2–3 |
| d upstream | 2 (SDA, SCL) | `Connector_PinHeader_2.54mm:PinHeader_2x03_P2.54mm_Vertical` | odd 1/3/5 = bus line; even 2/4/6 = 2.2 k / 4.7 k / 10 k to I2C_PU_RAIL | shunt 1–2 (2.2 k) | shunt 1–2 (2.2 k) |
| f | 2 (SDA, SCL) | `PinHeader_1x02_P2.54mm_Vertical` | bus line / BQ_SDA or BQ_SCL | shunt on | shunt on |

**Counts.** 16 jumper headers per board: 11 × 1×2, 1 × 1×3, 2 × 1×4, 2 × 2×3. Shunts fitted: 12 in the v8 default, 13 in the all-v7 configuration; supply 15 per board (75 for 5 boards). Solder pads left: 13 SJ2 (9 default-open: d downstream 6, e 2, j 1; 4 factory-bridged: LED loads) and 4 SJ3 (g, i, j, k; j and k only if Phase 7 keeps the BQ24195). The old count of 9 row-b jumpers is now 9 headers.

**v7 positions stay reproducible.** Each v7 position joins exactly the nets v7 had joined: a (2–3) puts U3_IO43/44 on the bus and leaves UART0_TX/RX open; b (bypass on, GND leg off) shorts the 47 Ω and leaves the TVS on its capacitance only; c (2–3) feeds the bus rail from the MCU regulator; d (1–2) is R28/R29's 2.2 k; f (on) keeps the BQ on the bus. The headers add their own pins to those nets (≈ 1 pF each, argued), as the solder jumpers' pads did. Phase 9/11 check the v7 positions against `c2acffc` as before.

**Arrangements chosen.**
- Row a as one 1 × 4 per line instead of a 1 × 3 plus a 1 × 2: the v7 shunt (2–3) shares a pin with both v8 shunts, so the hardware can't be left with GPIO43 on the bus and the UART0 header at once.
- Row d as a 2 × 3 with the bus line on the odd row: a 2-pin shunt bridges one column (one value) or two pins in the same row (no effect), so one shunt can never put two values in parallel. Unselected resistors hang only from I2C_PU_RAIL with an open end, so they add no stub to the bus beyond the header pin. Two values at once (deliberate stress) needs a second shunt.

**Parts** (stock from the JLC parts API, 2026-11-02; all extended).
| Item | Part | LCSC | Stock | Rating |
|---|---|---|---|---|
| Shunt | 2.54 mm, open-top, 1 × 2 | C5305 | 920 428 | 3 A. Open-top, so a probe tip can touch the shunt's metal from above |
| 1 × 2 header | PZ254V-11-02P | C492401 | 878 135 | 3 A |
| 1 × 3 header | PZ254V-11-03P | C2937625 | 728 380 | 3 A |
| 1 × 4 header | PZ254V-11-04P | C2691448 | 427 246 | 3 A |
| 2 × 3 header | PZ254V-12-06P-T | C56153599 | 1 000 | (no rating listed) |

**Row c current vs the 3 A shunt (argued).** Only the bus rail's load passes the shunt, not U3's. That load is the pull-ups, TCA, INA219 (each mA or less) and three sensor modules on J4–J6: the rigid board's PCA and LED (≈ 1–3 mA each), and six VCNL4040s whose IR LEDs pulse at up to 200 mA each (VCNL4040 LED_I maximum; the firmware setting wasn't checked), from the flex boards' 2.2 µF anode capacitors. Even if all six pulses lined up, the peak is ≈ 1.2 A + a few tens of mA, below 3 A; the average is far lower. The shunt's contact resistance (tens of mΩ, typical for the class, argued) drops a few mV at that peak.

### Debug LEDs, pull-up options, headers

**Debug LEDs** (the seven in Test points, plus D5 kept). All 0603, footprint `LED_SMD:LED_0603_1608Metric`; series resistors 0603, `Resistor_SMD:R_0603_1608Metric`. Target ≈ 1 mA (Test points). Vf at 1 mA is argued from the listed Vf at 5–20 mA, so currents are approximate; the resistor can be swapped on the bench. Phase 8 checks each LED's cathode mark against the footprint.
| LED | Rail / signal | Part | LCSC | Stock | Resistor | LCSC (stock) | ≈ I |
|---|---|---|---|---|---|---|---|
| D1 (kept) | +3.3V_MCU | Emerald green, A-SP192DGHC-C01-4T (v7 part) | C19171301 (extended) | 69 023 | 1 kΩ (v7 R1) | C22548 (extended, 14.5 M) | 0.5–0.9 mA |
| BUS | +3.3V_BUS | same green | C19171301 (extended) | 69 023 | 1 kΩ | C21190 (basic, 30.1 M) | 0.5–0.9 mA |
| +5V | +5V | Yellow, KT-0603Y | C2287 (extended) | 110 877 | 3.3 kΩ | C22978 (basic, 5.1 M) | ≈ 0.95 mA |
| VBUS | Protected_VBUS | Red, KT-0603R | C2286 (basic) | 6 977 221 | 3.3 kΩ | C22978 (basic) | ≈ 0.95 mA |
| STAT | charger STAT (open drain) | Orange, KT-0603O | C111340 (extended) | 18 999 | 2.2 kΩ to **VSYS** | C4190 (basic, 5.3 M) | ≈ 0.85 mA |
| DBG1 | GPIO47 (high = on) | Blue, KT-0603B | C2288 (extended) | 139 571 | 470 Ω | C23179 (basic, 4.4 M) | ≈ 1.3 mA |
| DBG2 | GPIO48 (high = on) | White, KT-0603W | C2290 (basic) | 1 220 705 | 470 Ω | C23179 (basic) | ≈ 1.3 mA |
| D5 (kept) | LED_DATA | WS2812B-MINI (v7) | C4154873 | see v7 review below | — | — | — |

- STAT anode on VSYS: VSYS exists whenever the charger runs, whether or not SW1 has the boost on, so the LED shows charging with the board "off". Conditional, like the STAT LED itself, on Phase 7 keeping the BQ24195 (the BQ's STAT is open drain, SLUSB97A; `docs/references/bq24195/DATASHEET_REFERENCE.md` pin table). Phase 7 confirms the rail.
- Rail LEDs (BUS, +5V, VBUS, and D1) each have a default-closed SJ2 in series (Test points), so their ≈ 1 mA can be removed for a v7-load A/B.
- The extended LEDs could be swapped for basic ones only by changing colour (JLC basic 0603 LEDs found: red C2286, white C2290). Not worth a colour change for a few cents of fee.

**Pull-up option resistors (jumper row d).** All 1 % 0603, `Resistor_SMD:R_0603_1608Metric`, each in series with its SJ2.
| Position | Per line | Value | LCSC | Stock | SJ2 default |
|---|---|---|---|---|---|
| Upstream (I2C_SDA, I2C_SCL) | 3 | 2.2 kΩ | C4190 (basic) | 5 302 703 | closed |
| | | 4.7 kΩ | C23162 (basic) | 14 856 287 | open |
| | | 10 kΩ | C25804 (basic) | 47 170 710 | open |
| Downstream (CH0–CH2 SDA/SCL, TCA side) | 1 | 4.7 kΩ | C23162 (basic) | 14 856 287 | open |
- v7 used Yageo 2.2 kΩ C114662 (extended) for R28/R29. C4190 is the same value and tolerance as a basic part; the A/B depends on the value, not the maker.
- Allowed combinations (from the rise-time table above): one upstream value at a time; downstream only with upstream 4.7 k or 10 k. 2.2 k upstream + downstream sinks ≈ 3.2 mA, over the 3 mA I²C limit. Two upstream values together (2.2 k ∥ 4.7 k = 1.5 k) also exceed it with a rigid board attached: a deliberate stress setting only.
- Downstream value 4.7 kΩ matches the rigid board's own pull-ups (`hardware/CONTEXT.md`). Its use is to recover rise time when the upstream is raised to 10 k (322 → 229 ns at 200 pF).

**Headers.** Footprints are KiCad stock. Hand-fit by the user (JLC through-hole assembly is not needed for break-away headers); the LCSC numbers are there if Phase 19 decides to have JLC fit them.
| Header | Pins | Footprint | LCSC (if assembled) | Stock |
|---|---|---|---|---|
| UART0 | 1 × 4: GND, TX (GPIO43), RX (GPIO44), NC | `Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical` | C2691448 (PZ254V-11-04P, extended) | 427 246 |
| External master (row e) | 1 × 4: GND, SDA, SCL, +3.3V_BUS (sense) | same | C2691448 | 427 246 |
| Spare GPIO | 2 × 15: signal row + GND row (GPIO1, 2, 4–9, 14, 17, 38–42) | `Connector_PinHeader_2.54mm:PinHeader_2x15_P2.54mm_Vertical` | C22465939 (PZ254V-12-30P, extended) | 498 |
| Rail current-measure (row h) | 1 × 2 per rail, **not fitted** | `Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical` | C492401 (PZ254V-11-02P, extended) | 878 135 |

### Kept v7 parts (non-power) and swap review

Footprints carry over from the v7 project (`c2acffc`) unless a row says otherwise. Every v7 part on the I²C path is kept, so each jumper's v7 position reproduces v7's parts as well as its nets.

**Swaps (each with a reason).**
| v7 | Swap to | Reason | LCSC | Stock |
|---|---|---|---|---|
| IC1 SN74AHCT125PWR (TSSOP-14), C36365 | **SN74AHCT1G125DBVR** (TI, SOT-23-5), `Package_TO_SOT_SMD:SOT-23-5` | (1) C36365 is at **0 stock** (also the G4/E4 variants). (2) v7 uses one gate (1A = LED_DATA, 1Y = DATA_TO_LEDS, 1OE = GND); the other three gates' inputs have no net, i.e. float (v7 `circuit-context.json`). The single gate is the same AHCT family (TTL input thresholds, 5 V output), so LED_DATA sees the same kind of load. IC1 has no I²C role, so no jumper is needed for v7 fidelity | C7484 (extended) | 41 125 |

**Kept, with stock.**
| Ref (v7) | Part | LCSC | Stock | Note |
|---|---|---|---|---|
| U4 | TCA9548APWR | C130026 (extended) | 23 309 | Same part as v6/v7 (changelist: I²C circuitry unchanged). SCPS207H values used above |
| U7 | INA219AIDCNR | C87469 (extended) | 8 920 | On the bus as in v7. Its shunt (R44, 10 mΩ, C1322424) has **2 in stock**: power part, flagged to Phase 7 |
| U9 | USBLC6-2SC6 | C7519 (extended) | 40 183 | Jumpering it was rejected in Phase 3 |
| D5 | WS2812B-MINI-X2 | C4154873 (extended) | **152** | Enough for 5 boards, but thin. Fallback if it runs out: WS2812B-MINI-V3J C22371519 (43 048); Phase 8 checks its pinout against the v7 footprint first |
| U3 | ESP32-S3-WROOM-1-N16R8 | C2913202 (extended) | 34 388 | Footprint pad 37 is reviewed in Phase 8 if card (j) points at the joint (OQ-5) |
| J4–J6 | SM04B-SRSS-TB | C160404 (extended) | 61 118 | |
| J7 | TYPE-C-31-M-12 | C165948 (extended) | 176 891 | Its shell net is a Phase 7 item |
| J3 | S3B-PH-SM4-TB (LED strip) | C265101 (extended) | 57 430 | |
| SW2, SW3 | HX 3x4x2-2P tactile (RESET, BOOT) | C49234124 (extended) | 235 344 | |
| R30, R31 | 5.1 kΩ (USB CC) | C23186 (basic) | 21 038 674 | |
| R52, R53 | 22 Ω (USB series) | C23345 (basic) | 6 536 942 | |
| MCU passives | 100 nF C14663, 10 µF C19702 / C96446, 1 µF C15849, 10 kΩ C25804 | basic | ≥ 7.6 M each | |

**Considered, not changed.**
- D5's DIN is driven at 3.3 V while its VDD is +5 V (WS2812B VIH = 0.7 · VDD ≈ 3.5 V, argued from the WS2812B family, not from this part's sheet). Moving D5 to the 5 V side (DATA_TO_LEDS) would fix that, but it changes LED_DATA's membership and row (g)'s v7 position (V7R-019's fixture had D5 DIN on the line). Kept as v7.
- TCA9548A footprint: v7 uses a project-library `SOP65P640X120-24N`. Kept for continuity; the stock `Package_SO:TSSOP-24_4.4x7.8mm_P0.65mm` is the fallback if Phase 8 finds the project library awkward.

## Layout rules pointer

Phases 13–15 fill this in. The rules will live in `tools/pcb-context/` (rules config and CONTEXT).

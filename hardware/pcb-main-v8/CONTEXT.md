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

**Status.** Desk-ranked, not yet measured. The bench request is `docs/initiatives/v8-debug-board/debugger/RELAY-power.md` (Debugger, `PWR` cards). Phase 7 waits on its findings (W1). The full table, with the datasheet values and what confirms or refutes each mechanism, is in the initiative SESSION.md (Phase 2 Worker Notes).

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

Phase 7 fills this in.

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

**Status: approved by the user 2026-11-02 (W2 part 1), including the v7-valued defaults of rows d, f, h and i.** Rows a–h are the PLAN candidates; i–k come from changelist §3 and Phases 1–2. Every row has a v7 position that rebuilds v7's net membership for the nets it touches (Phase 9/11 check this against `c2acffc`). Defaults are the v8 position (BRIEF), except where the row says v8 = v7 because no fix is claimed. "SJ2" = 2-pad solder jumper, "SJ3" = 3-pad solder jumper (centre common); footprints are chosen in Phase 4.

| # | Toggles | v7 position | v8 position (default) | v6 (where it differs) | Map row / CL-ID | Implementation |
|---|---|---|---|---|---|---|
| a | Bus master pins, SDA and SCL separately | SDA = GPIO43, SCL = GPIO44; UART0 header disconnected | SDA = GPIO16, SCL = GPIO15; GPIO43/44 to the UART0 header | T-Display pins "43"/"44" (other die path) | master: module/path, pin role; V7R-019; CL-02 | Per line: SJ3 (centre = bus SDA or SCL; side 1 = GPIO43/44; side 2 = GPIO16/15) + SJ2 GPIO43/44 → UART0 header (open in v7). Both SJ3 open = U3 off the bus (row e) |
| b | Cable-facing protection on CH0–CH2 SDA/SCL | Bypassed: series R shorted, TVS ground leg open | Fitted: series R in line, TVS to GND | as v7 (none) | notebook 2026-10-31 candidate (1); net-stress form of (c) | Per line: series R with an SJ2 across it (closed = v7). Per connector: TVS array with an SJ2 in its GND leg (open = v7). 9 jumpers. Residual in v7 position: the floating TVS's capacitance stays on the lines (argued, small; Phase 4 picks a low-C part) |
| c | MCU 3.3 V vs bus/pull-up 3.3 V | Shared: one regulator feeds U3 and the pull-ups, TCA, INA219, J4–J6 | Separate: +3.3V_MCU and +3.3V_BUS from two regulators | Separate (AP2112K for the bus, T-Display LDO for the MCU) | master supply; CL-03, CL-08 | SJ3 on the +3.3V_BUS feed (side 1 = MCU regulator output, side 2 = bus regulator output). Phase 7 picks the parts; for a faithful v7 position the shared regulator should be the v7 type (AMS1117, CL-08) or the difference recorded. Back-powering U3 through the pull-ups when only the bus rail is up: Phase 7 checks |
| d | On-board pull-up values | Upstream 2.2 kΩ (R28/R29); no on-board pull-ups downstream | Upstream 2.2 kΩ (**v8 = v7**: no pull-up fix is claimed; notebook fix (ii) "not pursued"); downstream none fitted | as v7 | master: pull-up current; desk (d) | Upstream per line: three resistors (2.2 k, 4.7 k, 10 k) each in series with an SJ2 (2.2 k closed). Downstream per channel line: one footprint (value Phase 4) in series with an SJ2, open. Values and rise time: Phase 4 |
| e | External master on the bus | Header disconnected | Header disconnected | — | master: identity; V7R-004 / F-12 method | 4-pin header (SDA, SCL, GND, +3.3V_BUS sense) on the bus side, joined by SJ2 per line (open). To use: open both (a) SJ3s, close these. No second master footprint (OQ-2) |
| f | BQ on the I²C bus | Connected | Connected (**v8 = v7**; firmware still talks to it) | — | symptom identity: causal; STATE §3; L-Ph8 | SJ2 on U5 SDA and SCL (closed). Applies only if Phase 7 keeps the BQ24195 or another I²C charger |
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

**Ground points.** Every signal or rail test point has its own GND pad beside it (not shared with a neighbour), within ground-spring reach. Working rule until Phase 4 measures the Sensepeek/Rigol spring: centre-to-centre ≤ 5 mm (argued). GND pads are big enough for two springs at once (V7R-019 V5b: "All four things won't fit on C"). Headers count as test points when a GND pin sits next to each signal pin.

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
- UART0: 1 × 4, 2.54 mm: GND, TX (GPIO43), RX (GPIO44), NC. 3.3 V logic. Joined through the (a) SJ2s.
- External master (row e): 1 × 4, 2.54 mm: GND, SDA, SCL, +3.3V_BUS (sense/reference only).
- Spare GPIO: 2 × 15, 2.54 mm, signal row + GND row: GPIO1, 2, 4, 5, 6, 7, 8, 9, 14, 17, 38, 39, 40, 41, 42.

**Debug LEDs.** Each rail LED draws ≈ 1 mA and has an SJ2 in series (closed), so its load can be removed for an A/B against v7 (v7 had only D1 on +3.3V).
| LED | Signal | Colour | Notes |
|---|---|---|---|
| D1 (kept) | +3.3V_MCU | green | As v7 (R1 1 k) |
| new | +3.3V_BUS | green, silk "BUS" | Lit only when the bus rail is up (row c) |
| new | +5V | yellow | Shows the boost running (#0004 case) |
| new | Protected_VBUS | red | USB input present |
| new | charger STAT | orange | U5 STAT (pin 4, unconnected on v7) if Phase 7 keeps the BQ24195; open drain, pull-up rail chosen in Phase 4 |
| new | GPIO47 | blue, "DBG1" | Firmware-driven |
| new | GPIO48 | white, "DBG2" | Firmware-driven |
| D5 (kept) | LED_DATA | RGB (WS2812B-MINI) | As v7, on the (g) centre |

## Parts

Phase 4 (non-power) and Phase 7 (power) fill this in.

**Status (non-power, Phase 4): pending user approval (W2 part 2).** Stock: JLCPCB parts API (`selectSmtComponentList`, the same data as the JLC parts page), checked 2026-11-02. The JLC MCP was not available to the Worker. "basic" / "extended" is JLC's library type (extended parts carry a per-part assembly fee). Stock moves: Phase 19 preflight re-checks every number.

### Cable-facing protection (jumper row b)

Per connector J4–J6: one dual TVS on CHn_SDA_CONN / CHn_SCL_CONN, and one series resistor per line between the TCA pin and the connector. 3 TVS, 6 resistors.

| Item | Part | LCSC | Stock | Footprint |
|---|---|---|---|---|
| TVS, 2-line, per connector | TI **TPD2E2U06DRLR** (SOT-553-5): IO1 = pin 3, IO2 = pin 5, GND = pin 4, pins 1–2 NC | C1972959 (extended) | 4 078 | `Package_TO_SOT_SMD:SOT-553` (Phase 8 checks the symbol pin map against TI's DRL pinout) |
| Alternate TVS | TI TPD4E05U06DQAR (4-line, 0.5 pF, USON-10 0.5 mm pitch; two channels unused) | C138714 (extended) | 121 301 | `Package_SON:USON-10_2.5x1.0mm_P0.5mm` |
| Series R, per line | **47 Ω** 1 % 0603 | C23182 (basic) | 1 557 821 | `Resistor_SMD:R_0603_1608Metric` |
| Bypass (v7 position) | SJ2 across each series R (closed = v7); SJ2 in each TVS GND leg (open = v7) | — | — | see Footprints |

**TPD2E2U06 (TI SLLSEG9C, rev. Dec 2019, §6.5).** V_RWM 5.5 V. Line capacitance 1.5 pF typ, 1.9 pF max (1 MHz, 2.5 V bias). Leakage 10 nA max at 2.5 V. Clamp IO→GND 9.7 V at 1 A and 12.4 V at 5 A (TLP); R_DYN 0.5 Ω (DRL). Unidirectional to GND: there is no rail pin, so with its GND leg open (v7 position) the only thing left on the line is its capacitance.

**Why V_RWM 5.5 V and not 3.3 V.** The task asked for "3.3 V working voltage": the bus runs at 3.3 V, so any V_RWM ≥ 3.6 V (3.3 V + 10 %) works. A 5–5.5 V part leaks nA at 3.3 V; a 3.3 V-rated part is specified only at its V_RWM and leaks µA there, which shows up as a DC load on a bus whose fault is a low-level question. The clamp still sits above the TCA9548A's 7 V abs-max (SCPS207H §6.1: SDx/SCx −0.5 to 7 V, ±20 mA input current). That is why the series R is there: during a strike the TVS takes the bulk of the current and the 47 Ω limits what reaches the TCA's own ESD structure, to roughly (12.4 − 7) V / 47 Ω ≈ 115 mA for the ns-scale pulse (argued; 100 Ω would halve it, at the VOL cost below).

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
- **Series R cost on the low level** (the one that matters on this bus). When a far-end device pulls low, the main board's pull-up current crosses the series R: 2.9 V / 2.2 k ≈ 1.3 mA × 47 Ω ≈ 62 mV added at the master. Worst-case sum at U3: VCNL VOL 0.4 V + PCA Ron 20 Ω max × 2.5 mA (50 mV) + 62 mV + TCA Ron 30 Ω max × 1.3 mA (40 mV) ≈ 0.55 V, against VIL = 0.3 · VDD = 0.99 V. 100 Ω would make it ≈ 0.62 V. 47 Ω was chosen to keep the added offset under ≈ 60 mV on a board that is built to study low levels; the row (b) SJ2 removes it entirely for A/B.

### Footprints: jumpers, links, test points, ground points

All are KiCad 9 stock libraries (checked present in `/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/`). No LCSC part: solder jumpers and pads are copper only.

| Use | Footprint | Notes |
|---|---|---|
| SJ2, default **open** | `Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm` | Close with a solder blob. Rows a (UART0 side in v7), b (series-R bypass), d (4.7 k, 10 k, downstream), e, j (the D+ to GND SJ2; closed only in v7) |
| SJ2, default **closed** | `Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm` | Copper bridge from the factory: cut it to open, then it behaves as an open SJ2 (blob to re-close). JLC can't place a solder blob, so this is how "closed by default" ships. Rows a (UART0 SJ2 in v8), b (TVS GND leg), d (2.2 k), f, LED series jumpers |
| SJ3 | `Jumper:SolderJumper-3_P1.3mm_Bridged12_RoundedPad1.0x1.5mm_NumberLabels` | Pads 1–2 bridged from the factory. **Pad rule: pad 2 = common (the matrix's "centre"), pad 1 = the default position, pad 3 = the other position.** Rows a ×2, c, g, i, j, k. For row i the default (pad 1) is SW1, which is also the v7 position. The matrix's "side 1 / side 2" wording names positions, not pad numbers |
| 0 Ω link, signal | `Resistor_SMD:R_0603_1608Metric`, 0 Ω C21189 (basic, 20.45 M) | Where a jumper must be removable more than a few times, a 0603 0 Ω is the alternative to a bridged SJ2 |
| 0 Ω link, rail current-measure (row h) | `Resistor_SMD:R_1206_3216Metric`, 0 Ω C17888 (basic, 1.72 M) + `Connector_PinHeader_2.54mm:PinHeader_1x02_P2.54mm_Vertical` beside it, not fitted | C17888 is listed at 250 mW; its current rating isn't in the JLC listing. **Phase 7 checks the rating per rail**: +5V_TO_LEDS (behind F1, 3 A) probably needs a 2512 0 Ω or a pair |
| Signal test point | `TestPoint:TestPoint_Pad_D1.5mm` | Round, SMD. v7's TP1–TP4 used this; TPIO used D2.0 mm |
| Ground point | `TestPoint:TestPoint_Pad_2.5x2.5mm` | Square, so it reads as GND at a glance. Big enough for two springs (V7R-019 V5b: two tips and two springs "won't fit" on a 0603 pad) |
| Strap pads (GPIO3/45/46) | `TestPoint:TestPoint_Pad_D1.0mm` | Bare pad only (GPIO allocation) |

**Ground-spring reach (replaces the 5 mm working rule).** Measured on the bench, with SQ500 springs, edge to edge (copper), `lab/procedures/known-good-reference.md` ground table: pad F → U5 pins 5/6 at **2.64 mm** (V7R-009, V7R-010: "springs on F, 0 mm") and pad C → TPIO43/44 at **3.05 mm** on v7 (V7R-010 master end). The spring's maximum reach has not been measured, so the rule stays inside what has been done:
- **Gap between a signal test point and its ground point: 1.0–3.0 mm, copper edge to copper edge.** With a D1.5 signal pad and a 2.5 mm square ground pad that is 3.0–5.0 mm centre to centre, which matches the old working value.
- The 1.0 mm minimum keeps a slipping spring off the signal pad (a spring on the signal pad shorts it to GND).
- Not demonstrated on a board: the Rigol stock-probe spring (springs for it are on hand, `lab/procedures/known-good-reference.md`). Optional user check, not blocking: measure each probe's tip-to-spring reach with calipers; if it's well over 3 mm, the Phase 13 placement rules can relax the maximum.

## Layout rules pointer

Phases 13–15 fill this in. The rules will live in `tools/pcb-context/` (rules config and CONTEXT).

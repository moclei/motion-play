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

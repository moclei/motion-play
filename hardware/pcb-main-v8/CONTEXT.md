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

Phase 2 fills this in: ranked mechanisms and a pointer to `docs/initiatives/v8-debug-board/debugger/RELAY-power.md`.

## Power path

Phase 7 fills this in.

## GPIO allocation

Phase 3 fills this in.

## Jumper matrix

Phase 3 fills this in. The candidate rows a–h are in the initiative PLAN.

## Test points

Phase 3 fills this in.

## Parts

Phase 4 (non-power) and Phase 7 (power) fill this in.

## Layout rules pointer

Phases 13–15 fill this in. The rules will live in `tools/pcb-context/` (rules config and CONTEXT).

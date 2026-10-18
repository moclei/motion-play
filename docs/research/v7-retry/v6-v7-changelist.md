# v6 → v7 Changelist — Main PCB

> Stage A, topic 2. A list of every discrete difference between the main PCB that worked (v6) and the one that doesn't (v7). **This is a list of suspects, not a diagnosis.** Risk ratings are gut calls to help order the walk-down; they are not conclusions.

## 1. Version anchors

| | v6 | v7 |
|---|---|---|
| **Design ref (git)** | `fd632ef` — "Update LCSC part numbers… Order placed on JLCPCB 2026-03-16" | `c2acffc` — "Main PCB v7 finalization" (2026-04-13) |
| **Fabricated gerbers** | `hardware/pcb-main/kicad/production/motion-play-main-v6.zip` (2026-03-16 13:19, gitignored — local only) | `hardware/pcb-main/kicad/production/motion-play-main-v7.zip` (2026-04-07 15:28, gitignored — local only) |
| **Gerber ↔ git check** | F/In1/In2/B.Cu + Edge.Cuts regenerated from `fd632ef` with kicad-cli 9.0.4 match the zip's coordinate streams exactly | Same check against `c2acffc`: exact match on all 5 layers |
| **HEAD vs ref** | — | `.kicad_sch` / `.kicad_pcb` at HEAD are identical to `c2acffc` (later commits only add JSON context exports and 3D models) |
| **MCU** | LilyGO T-Display-S3 dev board (U2), on header | ESP32-S3-WROOM-1-N16R8 module (U3), soldered on |
| **Firmware that ran on it** | `4da1c67` (2026-04-13), env `lilygo-t-display-s3` — the user's chosen baseline ("last confirmed working"; trusted over later debug edits) | `HEAD` (`6400df9`), env `motion-play-v7` (+ diag variants) |

The user confirmed these anchors on 2026-10-18. Every later session should diff against **`fd632ef` ↔ `c2acffc`**.

### 1a. Timeline — was v6 actually brought up?

The user isn't sure whether v6 was tested. This is what the repo and memory record:

| Date | Event | Source |
|---|---|---|
| 2026-03-16 | **v6 ordered** from JLCPCB (PCBA) | `fd632ef` commit message; v6 gerber timestamps |
| 2026-03-17 | ESP32 integration initiative opened. Its BRIEF says v7 fabrication is "gated on v6 validation". | `docs/initiatives/esp32-integration/BRIEF.md:39` |
| 2026-03-26 | Main + sensor-rigid boards revised to 4-pin connectors (design only) | `cc5e603` |
| 2026-04-03 | Q2 polarity-protection fix committed (v7 design) | `fae477e` (message gives no reason) |
| 2026-04-07 | **v7 ordered.** The "Confirm v6 board validation is complete (gate for ordering)" checkbox was never ticked. | memory note; v7 gerber timestamps; `docs/initiatives/esp32-integration/TASKS.md:102` |
| 2026-04-10 | **BQ24195 IINLIM brownout found on a v6 board and fixed in firmware.** "VSYS held steady, display booted normally." | memory `project_bq24195_iinlim_fix` |
| 2026-04-13 | Firmware committed with `configureBQ24195()`, a new INA219 `PowerMonitor`, and LED-strip current-draw test modes with a display UI | `4da1c67` |
| 2026-04-21 | v7 debugging Phase 6 under way; boards 1–3 in hand by 04-22 | `docs/debugging/v7-i2c-investigation.md:277-319` |

**Conclusion: a v6 board was definitely powered up and running firmware.** The INA219 and the BQ24195 exist only on the main PCB, not on a bare T-Display. So the 04-10/04-13 work proves that on v6 the T-Display master talked over I²C to the BQ (at 0x6B on the same upstream bus) and to the INA219, while running from J7 USB power.

**This also explains the user's question "if v6 found the IINLIM bug, why didn't v7 fix it?".** The bug was found on 04-10, three days *after* v7 was ordered on 04-07. v7 was ordered before v6 validation was finished.

**Not proven: v6 with sensors on the TCA channels** (the v7 failure condition). Nothing in the repo records it. Local `session_data/` has nothing after Dec 2025. Sessions live in DynamoDB, so querying for sessions created between 2026-04-10 and ~04-20 would settle it. The user recalls that any v6 testing was done with sensors attached and worked.

**Correction to prior assumptions.** The memory note `project_pcb_revision_apr2026` lists "custom power circuit: BQ24195, TPS61088, INA219" as a v7 change. It is not one. All three were already on v6 (`fd632ef` BOM: U5 BQ24195RGER, U6 TPS61088RHLR, U7 INA219AIDCNR). That fits the IINLIM note, which records the BQ24195 being configured over I²C on a v6 board on 2026-04-10. The memory note is also wrong on two smaller points (see CL-06 and CL-17).

## 2. Scope of comparison

**Covered:**
- Schematic, all sheets (root, `power_management`, `tca9548A_subsystem`, `led_controller`, plus `esp32_s3` which is v7-only). Compared through kicad-cli XML netlist exports: components, values, footprints, LCSC numbers, the net on every pin, and the members of every net.
- Layout at component and net level: footprint placement and side, board outline, stackup, copper zones and keepouts, and per-net totals (segment count, length, widths, layers, via count).
- Fabricated output: gerber equivalence to git (above), plus the LCSC substitutions made at JLCPCB checkout that the schematic doesn't record.
- Master-side firmware: `platformio.ini` envs, `pin_config.h`, I²C init code.
- KiCad ERC and DRC run fresh on both refs.

**Not covered:**
- Trace geometry, coupling, return paths, via placement. Flagged for **topic 3** wherever relevant.
- Sensor PCBs (rigid/flex) and the cables. Only the main-PCB connector side is covered.
- The inside of the T-Display-S3 board. We have no schematic for it in the repo, so the v6 master's on-module circuitry is a black box (see §4).
- Exact resolved library versions in each firmware build (`^` ranges, no lockfile).

Working files (netlists, BOMs, position files, diff scripts) were left in this session's scratchpad. They are not committed, and all of them can be regenerated from the two refs with kicad-cli.

## 3. Changes table

Evidence paths are relative to `hardware/pcb-main/kicad/` unless stated otherwise. "Net" means the KiCad net name. Pin numbers are symbol/footprint pins.

### 3a. MCU and master side

| ID | Category | Subsystem | What changed | v6 → v7 | Risk | Evidence |
|---|---|---|---|---|---|---|
| CL-01 | component | MCU | MCU replaced | U2 **T-Display-S3** (bare ESP32-S3R8 die, own 3.3 V LDO, LCD, buttons, own USB-C; plugs into a header footprint) → U3 **ESP32-S3-WROOM-1-N16R8** (C2913202), soldered directly | **High.** This is the I²C master. The Phase-24 Arduino-as-master result points at the master side. Nearly every master-side difference comes from this one swap. | `fd632ef` BOM `U2,T-Display-S3`; `c2acffc` BOM `U3,…C2913202`; `esp32_s3.kicad_sch` |
| CL-02 | pin assignment | I²C | I²C master pins: **same GPIO numbers**, different physical path | SDA = GPIO43, SCL = GPIO44 in both. v6: T-Display header pins labelled "43"/"44" (U2.15/U2.16). v7: WROOM pins U3.37 `TXD0` / U3.36 `RXD0`, connected straight to the die through the module. Both are UART0's default pins. | **Medium.** Same pad function on the same die family, but on v6 the path from die to bus passed through T-Display PCB copper and connector (unknown; §4). The ROM bootloader drives TXD0 (SDA) at cold boot on both. | netlist `/I2C_SDA`, `/I2C_SCL`; `firmware/include/pin_config.h` |
| CL-03 | power | MCU / 3.3 V | **The 3.3 V domains were merged** | v6: the MCU ran from the T-Display's internal LDO (fed from +5V on U2.12). U2's "3v" pins (1, 24) were unconnected. The board's +3.3V net (AP2112K) fed only the I²C pull-ups, TCA, INA219 and sensor connectors. v7: a single +3.3V net (AMS1117) feeds the ESP32 **and** the pull-ups, TCA, INA219 and sensors. | **Medium.** This is the only change that alters how the master's I/O supply relates to the bus pull-up rail and the sensor-board supplies. v6 had two separate regulators, v7 has one shared rail. The ESP32's load (WiFi TX, ~500 mA peaks) now sits on the pull-up rail. | netlist `+3.3V` membership; `unconnected-(U2-3v-Pad1/24)`; `docs/explorations/esp32-integration.md:70-72` |
| CL-04 | component | MCU | ESP32 support circuitry added | (inside T-Display) → EN RC: R50 10 kΩ / C50 1 µF, SW2 RESET. GPIO0 strap: R51 10 kΩ pull-up, SW3 BOOT. Decoupling: C51 10 µF, C52–C54 100 nF, C55 1 µF on +3.3V. GPIO3/45/46 straps left floating (module defaults). | Low. Standard reference circuit. An EN RC problem would show up as a reset fault, not a per-address NACK. | `esp32_s3.kicad_sch`; nets `/ESP32_S3/EN`, `/ESP32_S3/GPIO0_BOOT` |
| CL-05 | pin assignment | MCU | Other GPIOs | Same numbers in both: TCA_RESET = IO10, INT1/2/3 = IO13/12/11, CHRG_INT = IO21, LED_DATA = IO16. **INT1–3 now dangle**: on v7 each is a single-node net (U3 only). On v6 they went to TPIO11–13. Neither version wires INT to the sensor connectors. | Low | U2/U3 pin maps; nets `/ESP32_S3/INT1..3` |
| CL-06 | component | MCU | Onboard WS2812B added | — → D5 WS2812B-MINI on `/LED_DATA` (shared with IC1 input and TPIO16), VDD = +5V, DOUT unconnected | Low. 3.3 V data into a 5 V-powered pixel is marginal on V_IH, but this circuit is not on the I²C path. | net `/LED_DATA`, `+5V` |
| CL-07 | net | USB | USB data path moved onto the board | v6: J7 D+/D− unconnected (USB data went through the T-Display's own USB-C). v7: J7 A6/B6, A7/B7 → U9 USBLC6-2SC6 → R52/R53 22 Ω → U3 IO19/IO20 (native USB / CDC) | Low for I²C. The route is long (~70 mm per line, 2–5 vias): **flagged for topic 3**. | nets `/USB_DP`, `/USB_DN`, `/ESP32_S3/USB_D?_MCU` |

### 3b. Power

| ID | Category | Subsystem | What changed | v6 → v7 | Risk | Evidence |
|---|---|---|---|---|---|---|
| CL-08 | component | 3.3 V LDO | LDO replaced | U1 AP2112K-3.3 (C51118, 600 mA, SOT-23-5) with C1 1 µF in / C2 2.2 µF out → U8 AMS1117-3.3 (C6186, 1 A, SOT-223) with C42 22 µF (0805) in / C43 22 µF 6.3 V tantalum out | **Medium.** Different regulator: ~1.1 V dropout vs ~0.25 V, an ESR-dependent stability window, and now carrying the MCU load (CL-03). Rail droop or noise reaches the pull-ups, TCA and sensors together. | netlist; v6 BOM `U1`; v7 BOM `U8` |
| CL-09 | component / net | battery | **Q2 pin mapping fixed, so the battery path now works** | v6 used the `Simulation_SPICE:PMOS` symbol, so physical SOT-23 pins were G = BAT_RAW, S = PMOS_GATE net, D = VBAT. The battery-to-VBAT path was non-functional; the only connection was through 100 kΩ. v7 uses `Q_PMOS_GSD`: G = PMOS_GATE, S = BAT_RAW, D = VBAT. R34 also changed from PMOS_GATE–BAT_RAW (v6) to PMOS_GATE–GND (v7). | Low–medium. No direct I²C mechanism, but it changes the board's **operating regime**. As far as the design goes, v6 could only run with VBUS present; v7 can also run from battery. The v7 fault reproduces in both regimes (USB-powered runs, and Phase 18 battery-pad-only with VBUS absent; `docs/debugging/v7-i2c-investigation.md:162`), which weakens this as a cause. It still matters as a control in any A/B test. | netlist `Q2.1/Q2.2` swap, `R34.2: BAT_RAW → GND`; commit `fae477e`; memory note bug #2 |
| CL-10 | component | battery | Battery connector | J8 JST-PH 2-pin (top side, C18221575) → BT1 Keystone 1042 18650 holder (**bottom side**, centred at (119.6, 128.6), covering roughly x 81–158, y 118–139) | Low electrically. Mechanically it now covers a large part of the bottom copper; see CL-20. | pos files; `BT1` |
| CL-11 | component / net | boost | Boost enable now switched | v6: TPS61088 EN (U6.2) tied straight to VIN (`VSYS_SENSE`), so the boost was always on and **there was no power switch**. v7: SW1 SPDT MSK-12C02 (C431540) between VSYS_SENSE and `BOOST_EN`, with R2 100 kΩ pull-down giving hard-off. | Low. +5V (and so +3.3V) startup now depends on switch contact. The memory note says v6 had a through-hole SS-12D10L5 switch in VSYS; the v6 netlist has no SW1. That switch only existed in a draft. | nets `/Power Management/BOOST_EN`, `VSYS_SENSE` |
| CL-12 | component | USB / VBUS | USB ESD added | — → U9 USBLC6-2SC6 (C7519): D+/D− through pins 1/6 and 3/4, pin 5 to `Protected_VBUS`, pin 2 to GND | Low. Puts one more load on Protected_VBUS. The pre-order fix of pin 5 is visible in the netlist. | net `Protected_VBUS` adds `U9.5` |
| CL-13 | net | +5V | +5V rail loads | v6: AP2112K VIN/EN, T-Display 5V (U2.12), C1, TP_5V1. v7: AMS1117 VIN, C42, D5 VDD. Feeding the T-Display's 5V pin meant v6 +5V may have been back-fed from the T-Display's own USB (§4). | Low | netlist `+5V` |
| CL-14 | passive value (as-built) | power | **LCSC substitutions at JLCPCB checkout that the schematic doesn't record** | v7 as built: C22, C30 → C72522 (47 µF 35 V, 6.3×5.4); C34, C35, C36, C42 → C45783 (22 µF 25 V 0805 Samsung). v6 as built used the schematic parts: C7469958 (C22/C30), C109314 (C34–36). | Low–medium. Same nominal values, different dielectric/ESR. C34–36 are the +5V boost output caps and C42 is the AMS1117 input. **The v7 schematic BOM is not the as-built BOM.** | memory note `project_pcb_revision_apr2026` (substitutions); `fd632ef` commit message |
| CL-15 | component | power | Power LED added | — → D1 + R1 1 kΩ from +3.3V to GND (~1.3 mA) | Low | net `Net-(D1-A)` |

### 3c. I²C / sensor connectors

| ID | Category | Subsystem | What changed | v6 → v7 | Risk | Evidence |
|---|---|---|---|---|---|---|
| CL-16 | footprint | sensor connectors | J4–J6 changed from 5-pin to 4-pin | SM05B-SRSS-TB (C136657) → SM04B-SRSS-TB (C160404). Pins 1–4 keep the same order: 1 = +3.3V, 2 = GND, 3 = CHn_SDA, 4 = CHn_SCL. | **Medium.** The fault shows up specifically when a TCA channel is open and has a cable attached. The user says v6 used the same sensor cables as v7. **Open contradiction:** the fabricated v6 has 5-pin SM05B sockets and v7 has 4-pin SM04B. One cable can only serve both if a 4-pin plug sat offset in a 5-pin socket, or if "same" means the same cable type. In the same 03-26 commit the sensor-rigid boards also went 5→4-pin, so the **sensor-board revision** on the far end may differ between v6 and v7 testing as well. | netlist J4–J6 |
| CL-17 | net | sensor connectors | (Correction) INT lines | Pin 5 was already **unconnected** on v6 (`unconnected-(J4-Pin_5-Pad5)`). The memory note's "INT lines removed" changed the footprint only, not the circuit. | Low | v6 netlist |
| CL-18 | net (rename) | hierarchy | Labels promoted to the root sheet | `/TCA9548A_Subsystem/TCA_RESET` → `/TCA_RESET`, `/Power Management/CHRG_INT` → `/CHRG_INT`, `/LED Controller/DATA_IN` → `/LED_DATA`. Membership is unchanged apart from the MCU pin. | Low. Names only. | netlist |

### 3d. Layout

| ID | Category | Subsystem | What changed | v6 → v7 | Risk | Evidence |
|---|---|---|---|---|---|---|
| CL-19 | mechanical / copper | whole board | **Complete re-placement** | Every component common to both boards moved; none of the 67 kept the same position and rotation. Outline went from 88.0 × 40.0 mm to 88.2 × 38.5 mm. The boost group (U6, L2, C31–C39, R39–R43) moved as a rigid block (+19.3 mm in x). TCA U4, pull-ups R28/R29 and J4–J6 moved from the bottom edge (y ≈ 138) to the right edge (x ≈ 146–161, connectors rotated 90°). USB J7 moved from the top edge to the left edge. | **Medium.** No row-by-row placement diff is useful here: the layout is new. Coupling and return paths: **topic 3**. | `kicad-cli pcb export pos` on both refs |
| CL-20 | copper | planes | Zone changes | **The B.Cu GND pour was removed** (v6 had GND on B.Cu at priority 6; v7 has no pour on B.Cu; B_Cu gerber has ~494 coordinate lines vs ~4350). Added: an F.Cu +3.3V pour (`U8_3.3V_POUR`) and an antenna keepout on all copper layers (x 121–140.5, y 100.9–107.6; no tracks, vias or pours). In2 still has the +5V/+3.3V split, with priorities reordered. In1 GND plane unchanged. | **Medium.** Less bottom-side ground stitching, and part of the I²C route now runs on B.Cu under the battery holder (CL-21). **Topic 3.** | `zone` blocks in both `.kicad_pcb`; gerber line counts |
| CL-21 | copper | I²C routing | I²C master-side route | SDA 82.0 mm / 3 vias → 72.9 mm / 3 vias. SCL 86.6 mm / 3 vias → 73.3 mm / 5 vias. Both 0.25 mm on F.Cu and B.Cu. On v7, ~37 mm (SDA) and ~40 mm (SCL) are on B.Cu at y ≈ 110–123, which overlaps the BT1 footprint area (y ≈ 118–139). | Medium. **Flagged for topic 3.** I have not assessed coupling. | per-net segment stats |
| CL-22 | copper | whole board | Routing totals | 650 → 855 segments, 156 → 224 vias | Low (context) | as above |
| CL-23 | other | DRC | DRC state | v6 file: 1 unconnected item, 1 dangling 0.275 mm SCL stub at (110.73, 131.58), 1 dangling via, about 30 clearance and annular-ring violations. v7: 0 unconnected, 6 minor clearance violations. Library-path warnings appear in both (an artefact of running from a scratch copy). | Low. v6 worked despite its DRC debt. | fresh `kicad-cli pcb drc` on both refs |

### 3e. Firmware (master side)

| ID | Category | Subsystem | What changed | v6 → v7 | Risk | Evidence |
|---|---|---|---|---|---|---|
| CL-24 | other (build env) | firmware | PlatformIO env | `env:lilygo-t-display-s3` → `env:motion-play-v7`. Board JSON `lilygo-t-display-s3` → `esp32-s3-devkitc-1` (different variant `pins_arduino.h`). `HAS_DISPLAY` / `HAS_BUTTONS` and TFT_eSPI dropped. `STARTUP_I2C_SCAN` false → true. Flash size set explicitly. **Unchanged:** Arduino core pinned at `#2.0.14`, USB_MODE=1 / CDC_ON_BOOT=1, `qio_opi`, 240 MHz, the same `^`-range lib_deps. | Medium. The variant affects defaults only, and I²C pins are passed explicitly. Without the display, boot timing between the I²C, BQ configuration and sensor init steps changes. | `platformio.ini` |
| CL-25 | other (code) | firmware | I²C init code has drifted since v6 ran | `4da1c67` (v6 era): `Wire.begin(43,44)`, 400 kHz, default drive and filters. HEAD: 100 kHz, `GPIO_DRIVE_CAP_3` on 43/44, `i2c_filter_enable(I2C_NUM_0, 7)`, pad filter, internal pulls disabled, plus diag/busrec/relbus paths. These sit in **shared** code (`SensorManager.cpp:641-685`), so a v6 build made today would differ from the one that worked. | Medium, as a confounder. Any v6 baseline re-run needs `4da1c67` firmware, or a clean revert of these debug changes. | `git diff 4da1c67 HEAD -- firmware/src` (+595/−28 lines) |

### 3f. Debug access

| ID | Category | Subsystem | What changed | v6 → v7 | Risk | Evidence |
|---|---|---|---|---|---|---|
| CL-26 | component | test points | Test points removed | Removed: TP_3V1 (+3.3V), TP_5V1 (+5V), TP_GND1 (a second GND pad), TPIO1/2/3/17/18 (spare T-Display GPIOs), TPIO11–13 (INT). Kept on v7: **TP1 VSYS, TP2 VBAT, TP3 PVBUS, TP4 PGND (= GND net)**, TPIO43/44 (SDA/SCL), TPIO10, TPIO16, TPIO21. | Low for the fault. **Relevant to topic 4**: v7 has a GND pad (TP4), but no +3.3V or +5V pad. (Corrected 2026-10-18; the first draft missed that TP4 is GND.) | netlist |

### Verified unchanged (useful invariants)

These are identical in both netlists:
- I²C bus members other than the master: R28/R29 2.2 kΩ to +3.3V, U4 TCA9548A, U5 BQ24195 (addr 0x6B), U7 INA219, TPIO43/44.
- BQ24195 support: R32 330 Ω ILIM, the TS network, D+/D− both tied to GND (IINLIM firmware dependency on both boards), CE to GND.
- TCA downstream nets CHn_SDA/SCL, R6 10 kΩ TCA_RESET pull-up, C9/C10/C40 decoupling.
- IC1 SN74AHCT125 LED buffer (with unused gates floating in both).
- 4-layer stackup: 35 µm Cu, 0.1 mm prepreg / 1.24 mm core / 0.1 mm prepreg. In1 = GND plane.
- Every passive value present on both boards. The only differences are the as-built substitutions in CL-14.

## 4. Changes we could not determine

1. **T-Display-S3 internals around GPIO43/44.** There's no T-Display schematic in the repo. Unknown: any series resistors, ESD or onboard pull-ups on the header's 43/44 pins; how the T-Display's LDO output voltage compares with the AP2112K's; the ESP32-S3R8 chip revision vs the WROOM-1's. *Next step: get the LilyGO T-Display-S3 schematic and read the die revision of each part from the boot log.*
2. ~~v6 power source~~ — **answered by the user:** v6 ran from J7 USB-C, with the T-Display's own USB-C disconnected. So the BQ always had VBUS on v6, and the back-feed path in CL-13 was never used.
3. **Whether v6 ran with sensors attached, BQ on the bus, and a TCA channel open** — the exact v7 failure condition. Partly resolved (§1a): v6 was brought up, and BQ + INA219 I²C worked on it. The user recalls sensors were attached and working but isn't certain. *Settle it by querying DynamoDB for sessions between 2026-04-10 and ~04-20.* Still the most important unknown in this artifact.
4. ~~Whether the v7 fault depends on power regime~~ — **resolved during this session:** it reproduces both with USB-C power and with VBUS absent (Phase 18, bench PSU on BAT_RAW; `docs/debugging/v7-i2c-investigation.md:162`, `:690`). Not yet tested on v7: a VBUS-present, no-battery run that also isolates the T-Display-style back-feed path, which can't exist on v7 anyway.
5. **Sensor cables and boards used with v6 vs v7** (CL-16). The user says the cables were the same, but the v6 socket is 5-pin and the v7 socket is 4-pin. Which sensor-rigid revision (5-pin, pre-03-26, or 4-pin) was on the far end in each case is unknown.
6. **Exact firmware build that ran on v6.** The user chose `4da1c67` as the baseline: the last confirmed-working firmware, trusted over the later debug edits. Any uncommitted local changes at the time, and the resolved library versions (no lockfile), are unknown.
7. **The v6 as-built BOM.** I assume it matches `fd632ef` `production/bom.csv`. No record of checkout substitutions exists for v6.
8. **v5 → v6 delta.** Out of scope by agreement. The v5 (2025-09-18) gerbers exist locally if needed.

## 5. Observations

- **The I²C circuitry itself did not change.** Pull-ups, TCA, BQ, INA219 and connector pinout are identical. Electrically, the only I²C-path changes are **who drives the bus** (CL-01/02), **what powers the driver relative to the pull-ups** (CL-03, CL-08), **the copper between them** (CL-19–21), and **the cable at the far end** (CL-16). That is a short list, and it lines up with the Phase-24 "master side" result.
- **The swap from separate to shared 3.3 V rails (CL-03) is easy to overlook.** The exploration doc framed the LDO change as "same function, just higher current". In fact v6 had the MCU on its own regulator, separate from the bus/sensor rail.
- **The power regime is a control variable, probably not the cause** (CL-09, CL-11, §4.2–4.4). v6 couldn't run from battery. v7 can, has a switch on the boost, and has a different LDO. Phase 18 shows the v7 fault doesn't depend on VBUS, but any A/B test between boards should still pin down the power source.
- **The firmware has drifted** (CL-25). The "known-good" v6 cannot be re-run with today's firmware without reverting the debug changes. That matters for the post-mortem's call for a known-good reference measurement.
- **Memory note `project_pcb_revision_apr2026` is inaccurate** on three points (the power circuit isn't new, there was no v6 switch, and the v6 INT pins were already unconnected). Updating it is outside this topic's scope, but the user should know.

## Observations for other topics

- **Topic 3 (KiCad extraction audit):** CL-07 USB route length; CL-20 B.Cu GND pour removal and the reordered In2 split-plane priorities; CL-21 I²C on B.Cu under the BT1 footprint; what kind of plane each I²C trace segment references. A single-sheet XML netlist export (`kicad-cli sch export netlist --format kicadxml`) plus position export reproduced everything at component and net level here in a few seconds. The audit could use it as an independent cross-check on `circuit-context.json` and `pcb-layout-context.json`.
- **Topic 4 (test workflow):** v7 has TP4 (PGND = GND) for scope ground, but no +3.3V or +5V test pad (CL-26). A v6 reference measurement needs `4da1c67` firmware (CL-25). A surviving v6 board plus `4da1c67` firmware is the natural known-good reference the post-mortem asked for.

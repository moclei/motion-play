# Integrated Power Management — Plan

## Approach

Integrate power management onto the main PCB by adding a new hierarchical schematic sheet containing USB-C input, BQ24195 battery management, a high-current boost converter, and INA219 power monitoring. The existing AP2112K stays as the 3.3V regulator fed from the +5V post-boost rail. The DWEII module footprint and its Schottky diode are removed from the root sheet.

The existing power supply PCB schematic (`hardware/pcb-power-supply/kicad/circuit-context.json`) serves as reference for the BQ24195 battery management circuitry. Key modifications from that reference: STUSB4500 and USBLC6-2SC6 are removed, the MT3608 boost converter is replaced with a higher-current part, and the LR1801 3.3V LDO is dropped (AP2112K on the main board handles 3.3V).

### Power Architecture

```
USB-C (5V) ──→ 3A Fuse ──→ Protected_VBUS
                                  │
                                  ▼
                            ┌──────────┐
          Battery ──→ PMOS ──→│ BQ24195  │──→ VSYS (3.0-4.5V)
          (JST PH)    Q1    │ Charger/ │      │
                            │ Power    │      ├──→ Boost Converter ──→ +5V
                            │ Path Mgr │      │    (8-10A switch)      │
                            └──────────┘      │                        ├──→ LED Strip
                                              │                        ├──→ T-Display-S3
                                              │                        ├──→ Level Shifter VCC
                                              │                        └──→ AP2112K ──→ +3.3V
                                              │                                         │
                                              │                                         ├──→ Sensors
                                              │                                         ├──→ TCA9548A
                                              │                                         └──→ PCA9546As
                                              │
                                              └──→ INA219 (monitors VSYS V/I via I2C)
```

### Why AP2112K from +5V (Not LDO from VSYS)

On battery only, VSYS tracks battery voltage. At a depleted cell (~3.0V), VSYS could be as low as 3.0-3.2V (BQ24195 BATFET drop). An LDO needs VIN >= VOUT + dropout: for 3.3V output with ~200mV dropout, that's 3.5V minimum input — out of spec at low battery.

Feeding the 3.3V LDO from +5V (post-boost) eliminates this: the boost converter maintains 5V regardless of battery state. The existing AP2112K on the main board already does this (VIN = +5V, VOUT = +3.3V). No new 3.3V regulator needed.

## Technical Notes

### Component Blocks

**USB-C Input** — USB-C connector (TYPE-C-31-M-12 or equivalent), 3A fuse on VBUS, 5.1k CC pull-downs for sink role, bulk + ceramic decoupling on Protected_VBUS. No STUSB4500 (PD removed for V1 simplicity). No USBLC6-2SC6 (data-line ESD protector is inapplicable without data lines; VBUS fuse handles overcurrent).

**Battery Management** — BQ24195RGER (C90862) with support circuitry adapted from the reference power supply design: PMOS reverse polarity protection (Q1 + R7/R8 bias), NTC thermistor, bootstrap cap (47nF per datasheet), REGN cap, PMID cap (2× 10µF for ≥20µF per datasheet), VSYS bulk capacitors, switching inductor (2.2µH), ILIM resistor. The ILIM resistor is **330Ω** (not 2.7kΩ from reference design) to set a ~1.5A hardware input current ceiling. OTG pin is tied HIGH via 10kΩ pull-up to give 500mA boot-time current (D+/D- grounded detects as SDP). Firmware configures actual input current limit via I2C after boot. See `COMPONENT_SELECTION.md` for the full analysis of the boot-time current issue.

**5V Boost Converter** — TPS61088RHLR (C87357). Replaces the MT3608 from the reference design. 10A synchronous boost, 2.7-12V input, 4.5-12.6V output, VQFN-20-EP (3.6×4.6mm). Feedback divider: 180kΩ/56kΩ for 5.07V output. Inductor: 2.2µH, 10A Isat (FXL0630-2R2-M, C167218). Output caps: 3× 22µF ceramic. Synchronous topology eliminates the Schottky rectifier needed by MT3608. See `COMPONENT_SELECTION.md` for full passive BOM.

**Power Monitoring** — INA219AIDCNR (C87469) on the VSYS rail with a 10mΩ 2512 shunt resistor (C1322424). PGA /2 mode (±80mV) gives 1 mA/LSB resolution, 8A max measurable current. Provides MCU-readable voltage and current via I2C. Address 0x40 (A0=GND, A1=GND — no conflicts with TCA9548A at 0x70 or BQ24195 at 0x6B). VS powered from 3.3V rail.

**BQ24195 GPIO** — INT (active-low interrupt on status change) wired to **GPIO 21** on the T-Display-S3 (pin 19 on header, net currently `Net-(U2-21)`, test point TPIO21). 10kΩ pull-up to 3.3V. GPIO 21 was selected to preserve GPIO 1-3 as a contiguous group and GPIO 17-18 as a pair for future use. STAT and PG are readable via BQ24195 I2C registers and do not need dedicated GPIOs.

### I2C Bus

The main I2C bus (GPIO43 SDA, GPIO44 SCL) carries three devices after this change:
- TCA9548A at 0x70 (existing)
- BQ24195 at 0x6B (new)
- INA219 at 0x40 (new)

Pull-ups: existing 2.2k to +3.3V (R28, R29 on the TCA9548A subsystem sheet). The reference power PCB's 10k pull-ups to Protected_VBUS (5V) are NOT used — the ESP32's GPIO is 3.3V and cannot tolerate 5V pull-ups.

### Boot-Time Power Sequence

1. BQ24195 sees VBUS, applies ILIM-resistor-programmed input current limit (~1-1.5A)
2. BQ24195 provides VSYS from VBUS power path (battery not required for boot)
3. Boost converter starts, producing +5V from VSYS
4. AP2112K produces +3.3V from +5V
5. ESP32 boots, firmware configures BQ24195 via I2C (sets actual input current limit, charge parameters)
6. System enters normal operation

The ~1-1.5A boot-time limit is adequate — system draws well under 1A before LEDs and WiFi activate.

### Schematic Editing Workflow

The `.kicad_sch` files are 7000+ lines. Reading them into AI context degrades session quality. Instead:

1. **AI produces a schematic change specification** — structured document listing every component (ref, part, value, footprint, LCSC#), every net, and pin-by-pin connections, organized by functional block.
2. **User implements in KiCad GUI** — new power management circuitry as a hierarchical sheet.
3. **User re-extracts `circuit-context.json`** — via `tools/schematic-context/extract.py --previous`.
4. **AI reviews extracted context** — verifies changes match spec.
5. **Annotation session** — AI proposes `ai_function`, `ai_block`, `ai_role`, `ai_critical_specs` for new components, written via `annotate.py`.

### Tooling

**JLCPCB MCP Server** (`@jlcpcb/mcp`, configured in `.cursor/mcp.json`): Use for Phase 1 component selection and beyond. Provides:
- Component search with LCSC part numbers, stock levels, pricing, package info, and category
- Datasheet PDF URLs in search results (`datasheetPdf` field) -- fetch these to produce text-only extracts for `docs/references/`
- KiCad symbol/footprint library installation (`library_install`) -- use after selecting components to get KiCad-compatible symbols and footprints automatically, streamlining Phase 3

If the server is not connected, restart Cursor or re-enable it. The server name is `jlcpcb`.

### Reference Materials

- Main PCB current design: `hardware/pcb-main/kicad/circuit-context.json`
- Power supply PCB (reference): `hardware/pcb-power-supply/kicad/circuit-context.json`
- Power budget analysis: `docs/explorations/power-budget.md`
- Schematic context tooling: `tools/schematic-context/` (extract.py, annotate.py, show.py)

## Resolved Questions (Phase 1)

- **Boost converter IC:** TPS61088RHLR (C87357). 4,972 in stock, $1.08. Thermally validated: ~1.5W dissipation at 5V/3A, RθJA 29.7°C/W with good layout → Tj ~85°C at 40°C ambient.
- **Board area:** Power block estimated at ~830mm². Fits on current 85mm × 45mm board but will be tight. May need to grow to 90mm × 50mm — flag during Phase 3 layout.
- **GPIO for BQ24195 INT:** GPIO 21 (preserves GPIO 1-3 and 17-18 for future use).
- **Battery-absent operation:** Confirmed viable. BQ24195 regulates VSYS at ~3.65V from VBUS. With revised ILIM (330Ω) and OTG HIGH, system boots at 500mA and operates at 1.5A. Firmware limits LEDs on USB-only.
- **ILIM resistor issue (NEW):** Reference design 2.7kΩ gives only 100mA boot current with D+/D- grounded — too low. Changed to 330Ω (~1.5A) with OTG HIGH for 500mA boot. See `COMPONENT_SELECTION.md`.

## Open Questions

All Phase 2 questions resolved — see `SCHEMATIC_SPEC.md` for full details.

- ~~Compensation network values for TPS61088 at 5V output~~ **Resolved:** R_COMP=22kΩ, C_COMP1=4.7nF, C_COMP2=100pF. Derived from TPS61088 EVM (SLVUAF2) and scaled for 5V/2.2MHz. Bench-tunable during Phase 5.
- ~~PMID capacitance~~ **Resolved:** 2× 10µF (C25+C26 = 20µF total), meeting datasheet minimum.
- ~~CE pin connection~~ **Resolved:** Tied to GND (always LOW = charging hardware-enabled). Firmware controls charging via I2C REG01. Simpler and more reliable than reference design's CE→PG connection.

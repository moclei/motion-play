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

**Battery Management** — BQ24195RGET with support circuitry carried from the reference power supply design: PMOS reverse polarity protection (Q1 + R7/R8 bias), NTC thermistor, bootstrap cap, REGN cap, PMID cap, VSYS bulk capacitors, switching inductor (2.2uH), ILIM resistor. The ILIM resistor (2.7k) programs ~1-1.5A boot-time input current limit (D+/D- grounded = non-standard adapter detection). Firmware configures actual input current limit via I2C after boot.

**5V Boost Converter** — Replaces the MT3608 from the reference design. Must deliver 3A+ at 5V from VSYS input (3.0-4.5V). Requires 8-10A switch class (e.g., TPS61088). Specific component selected in Phase 1 based on LCSC availability, thermal specs, and application circuit complexity. The feedback divider, inductor, Schottky diode, and capacitor values all depend on the selected part's datasheet.

**Power Monitoring** — INA219 (or INA226) on the VSYS rail with a shunt resistor. Provides MCU-readable voltage and current via I2C. Address 0x40 (no conflicts with TCA9548A at 0x70 or BQ24195 at 0x6B).

**BQ24195 GPIO** — INT (active-low interrupt on status change) wired to one unused T-Display-S3 GPIO. Candidates: GPIO 1, 2, 3, 17, 18, or 21 (all currently unused breakout test points on the main PCB). STAT and PG are readable via BQ24195 I2C registers and do not need dedicated GPIOs.

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

**JLCPCB MCP Server** (`jlc-mcp@latest`, configured in `.cursor/mcp.json`): Use for Phase 1 component selection and beyond. Provides:
- Component search with LCSC part numbers, stock levels, pricing, package info, and category
- Datasheet PDF URLs in search results (`datasheetPdf` field) -- fetch these to produce text-only extracts for `docs/references/`
- KiCad symbol/footprint library installation (`library_install`) -- use after selecting components to get KiCad-compatible symbols and footprints automatically, streamlining Phase 3

If the server is not connected, restart Cursor or re-enable it. The server name is `jlcpcb`.

### Reference Materials

- Main PCB current design: `hardware/pcb-main/kicad/circuit-context.json`
- Power supply PCB (reference): `hardware/pcb-power-supply/kicad/circuit-context.json`
- Power budget analysis: `docs/explorations/power-budget.md`
- Schematic context tooling: `tools/schematic-context/` (extract.py, annotate.py, show.py)

## Open Questions

- Which specific boost converter IC? Depends on Phase 1 LCSC search. TPS61088 is the leading candidate but must be confirmed for stock, pricing, and thermal viability.
- Will the board need to grow beyond 85mm x 45mm? Depends on Phase 1 area estimate after component selection.
- Which GPIO for BQ24195 INT? Any of GPIO 1, 2, 3, 17, 18, 21. Pick during schematic spec.
- Battery-absent VSYS behavior under full load? BQ24195 datasheet confirms support but needs validation against expected load profile during Phase 1 datasheet review.

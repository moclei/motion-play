# Power Supply PCB Schematic Context — Plan

## Approach

This follows the same workflow established in the `schematic-context` initiative. The tooling already exists — this initiative is about running it on the power supply board and annotating the results.

### Schematic Hierarchy

```
motion-play-power.kicad_sch (root — page 1, top-level interconnect only)
├── usb_pd.kicad_sch         — "USB-C & PD Control" (page 2)
├── battery_mgmt.kicad_sch   — "Battery Management" (page 3)
├── power_dist.kicad_sch     — "Power Distribution" (page 4)
└── connectors.kicad_sch     — "Connectors" (page 5)
```

The root sheet contains no components — only hierarchical sheet instances and wiring between them. All components live on child sheets.

### Cross-Sheet Signals (from root sheet wiring)

| Signal | From | To | Purpose |
|--------|------|----|---------|
| USB_ATTACH | usb_pd → | connectors | USB connection status |
| USB_ALERT | usb_pd → | connectors | PD alert signal |
| VSYS | battery_mgmt ↔ | power_dist | Main system voltage rail |
| CHRG_STAT | battery_mgmt → | connectors | Charge status indicator |
| CHRG_INT | battery_mgmt → | connectors | Charger interrupt |
| CHRG_PG | battery_mgmt → | connectors | Power good signal |

### Key Components (from BOM)

| Ref | Part | Function | Expected Block |
|-----|------|----------|----------------|
| U1 | STUSB4500LQTR | USB PD controller (negotiates voltage/current) | usb_pd |
| U2 | USBLC6-2SC6 | USB ESD protection | usb_pd |
| U3 | BQ24195RGET | Battery charger/power path management IC | battery_mgmt |
| U4 | MT3608 | Boost converter (battery → 5V) | power_dist |
| U5 | LR1801G-33-SH2-R | 3.3V LDO regulator | power_dist |
| USBC1 | TYPE-C-31-M-12 | USB-C connector | usb_pd |
| CN1 | Molex MicroFit 3-pin | Main power output connector | connectors |
| J1 | JST PH 2-pin | Battery connector | battery_mgmt |
| J3 | JST SH 2-pin | Small signal connector | connectors |
| J4 | JST SH 5-pin | Main board interface connector | connectors |
| D1 | SS54 Schottky | Reverse polarity / flyback protection | power_dist or battery_mgmt |
| F1 | Fuse 1206 | Overcurrent protection | usb_pd or battery_mgmt |
| Q1 | PMOS | Power switching / load disconnect | power_dist |
| TH1 | 10kΩ NTC | Battery temperature monitoring | battery_mgmt |

### Expected Functional Blocks

1. **usb_pd** — USB-C connector, STUSB4500 PD controller, ESD protection, CC resistors
2. **battery_mgmt** — BQ24195 charger IC, battery connector, NTC thermistor, charge status signals
3. **power_dist** — MT3608 boost converter, LR1801 3.3V LDO, Schottky diode, PMOS switch, output filtering
4. **connectors** — Output connectors (MicroFit, JST), status signal pass-through to main board

## Workflow

1. Run `extract.py` on root schematic → baseline `circuit-context.json`
2. Run `show.py --unannotated` to see all components needing annotation
3. Annotate in batches by functional block (usb_pd → battery_mgmt → power_dist → connectors)
4. Write component annotations via `annotate.py`
5. Add net annotations and block definitions directly to `circuit-context.json`
6. Re-extract with `--previous` to merge everything
7. Verify with test questions

## Open Questions

- None currently — tooling is proven, just applying it to a new board.

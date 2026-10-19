> **RETIRED for numbers.** Clearances here are centreline to centreline and overstate the real copper gap by roughly half the combined trace widths (`docs/research/v7-retry/kicad-extraction-audit.md`). Don't quote them. Use edge-to-edge figures from a read-only probe (tools/CONTEXT.md Critical Rule) until the board model lands.

## Routing audit — hardware/pcb-main/kicad/motion-play-main.kicad_pcb

_Generated_: 2026-04-25T17:30:53.066907+00:00
_Spec_: `v7-main-i2c.json`
_Routing context_: `/Users/marcocleirigh/Workspace/motion-play/hardware/pcb-main/kicad/pcb-routing-context.json`

### Net `/I2C_SDA`

- Total length: **72.9 mm** (B.Cu 37.0, F.Cu 35.9)
- Segments: 25, vias: 3
- Min clearance to component `L1`: **6.1 mm** (F.Cu)
- Min clearance to component `L2`: **7.0 mm** (F.Cu)
- Min clearance to component `U5`: **0.0 mm** (F.Cu)
- Min clearance to component `U6`: **5.4 mm** (F.Cu)
- Min clearance to BQ24195 SW pin (pad 19): **4.3 mm** (F.Cu)
- Min clearance to BQ24195 SW pin (pad 20): **3.9 mm** (F.Cu)
- Min clearance to net `/Power Management/Protected_VBUS`: **2.2 mm** (F.Cu)
- Min clearance to net `/Power Management/VSYS`: **2.8 mm** (F.Cu)
- Min clearance to net `/Power Management/VBAT`: **4.0 mm** (F.Cu)
- Min clearance to net `/Power Management/BQ_SW`: **4.5 mm** (F.Cu)
- Min clearance to net `/Power Management/BOOST_SW`: **2.7 mm** (F.Cu)

### Net `/I2C_SCL`

- Total length: **73.3 mm** (B.Cu 39.6, F.Cu 33.7)
- Segments: 33, vias: 5
- Min clearance to component `L1`: **5.6 mm** (F.Cu)
- Min clearance to component `L2`: **6.5 mm** (F.Cu)
- Min clearance to component `U5`: **0.0 mm** (F.Cu)
- Min clearance to component `U6`: **5.0 mm** (F.Cu)
- Min clearance to BQ24195 SW pin (pad 19): **3.9 mm** (F.Cu)
- Min clearance to BQ24195 SW pin (pad 20): **3.6 mm** (F.Cu)
- Min clearance to net `/Power Management/Protected_VBUS`: **1.7 mm** (F.Cu)
- Min clearance to net `/Power Management/VSYS`: **3.1 mm** (F.Cu)
- Min clearance to net `/Power Management/VBAT`: **4.0 mm** (F.Cu)
- Min clearance to net `/Power Management/BQ_SW`: **4.1 mm** (F.Cu)
- Min clearance to net `/Power Management/BOOST_SW`: **1.8 mm** (F.Cu)

### Asymmetry (`/I2C_SDA` vs `/I2C_SCL`)

| Metric | /I2C_SDA | /I2C_SCL | Δ (a − b) |
|---|---:|---:|---:|
| Total length (mm) | 72.9 | 73.3 | -0.4 |
| Min dist to /Power Management/BOOST_SW (mm) | 2.7 (F.Cu) | 1.8 (F.Cu) | +0.9 |
| Min dist to /Power Management/BQ_SW (mm) | 4.5 (F.Cu) | 4.1 (F.Cu) | +0.4 |
| Min dist to /Power Management/Protected_VBUS (mm) | 2.2 (F.Cu) | 1.7 (F.Cu) | +0.5 |
| Min dist to /Power Management/VBAT (mm) | 4.0 (F.Cu) | 4.0 (F.Cu) | -0.0 |
| Min dist to /Power Management/VSYS (mm) | 2.8 (F.Cu) | 3.1 (F.Cu) | -0.4 |
| Min dist to L1 (mm) | 6.1 (F.Cu) | 5.6 (F.Cu) | +0.5 |
| Min dist to L2 (mm) | 7.0 (F.Cu) | 6.5 (F.Cu) | +0.5 |
| Min dist to U5 (mm) | 0.0 (F.Cu) | 0.0 (F.Cu) | 0.0 |
| Min dist to BQ24195 SW pin (pad 19) (mm) | 4.3 (F.Cu) | 3.9 (F.Cu) | +0.3 |
| Min dist to BQ24195 SW pin (pad 20) (mm) | 3.9 (F.Cu) | 3.6 (F.Cu) | +0.4 |
| Min dist to U6 (mm) | 5.4 (F.Cu) | 5.0 (F.Cu) | +0.5 |


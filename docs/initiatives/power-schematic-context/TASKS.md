# Power Supply PCB Schematic Context — Tasks

## Phase 1: Initial Extraction

- [x] Run `extract.py` on `hardware/pcb-power-supply/kicad/motion-play-power.kicad_sch` — 50 components, 29 nets, 5 sheets (root + 4 children)
- [x] Review extraction output — all 4 child sheets discovered (usb_pd, battery_mgmt, power_dist, connectors), component count matches BOM
- [x] Run `show.py --unannotated` — 0/50 annotated, breakdown: battery_mgmt 21, power_dist 14, usb_pd 12, connectors 3

## Phase 2: Annotation Pass

- [x] Annotate USB-C & PD Control block (usb_pd sheet — 12 components: USBC1, F1, U1 STUSB4500, U2 ESD, R1-R5, C1, C2, C14)
- [x] Annotate Battery Management block (battery_mgmt sheet — 21 components: U3 BQ24195, J1, Q1 PMOS, L1, TH1, R6-R8, C3-C8, C13, TP1-TP6)
- [x] Annotate Power Distribution block (power_dist sheet — 14 components: U4 MT3608, U5 LR1801, D1, L2, R9-R11, C9-C12, TP7-TP9)
- [x] Annotate Connectors block (connectors sheet — 3 components: CN1 MicroFit, J3, J4)
- [x] Add net annotations (type, protocol, direction, description) to all 29 nets in circuit-context.json
- [x] Define 4 functional blocks (usb_pd, battery_mgmt, power_dist, connectors) with descriptions and design intent notes
- [x] Add sheet interface descriptions and top-level circuit description
- [x] Re-extract with `--previous` — 50/50 components annotated, clean merge, 48,965 bytes output

## Phase 3: Verification

- [ ] Define 5-8 test questions about the power supply circuit
- [ ] Run verification: fresh session with only circuit-context.json answers the test questions
- [ ] Address any gaps found during verification

## Phase 4: Documentation Update

- [ ] Update `hardware/CONTEXT.md` — add power supply PCB to the schematic context file locations table

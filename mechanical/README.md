# Mechanical Design — Motion Play

Physical enclosures and mounting hardware for the Motion Play sensor system. These are the 3D-printed parts that house the PCBs, attach to the hoop, protect electronics from impact, and route cables.

## Status

**v0.1** — Problem definition and dimensional constraints captured. No CAD models yet.

## Structure

```
mechanical/
├── specs/                  # Dimensional specs, constraints, design requirements
│   └── assembly-v0.1.yaml  # Problem definition: dimensions, current prototype, requirements
├── enclosures/             # CAD files (organized as the design takes shape)
```

## Context

The sensor assemblies must mount to a 25.25mm × 4mm steel flat bar hoop, with the rigid sensor PCB on the outside face and the flex PCB's optical sensors facing inward. Three assemblies are spaced equally (120°) around the hoop.

The number of pieces per assembly, how they fasten, and the overall form factor are open design questions. See `specs/assembly-v0.1.yaml` for the current prototype description and the requirements the next design must meet.

## Manufacturing

Primary method is FDM 3D printing. Design is open to:
- External fasteners (screws, zip ties)
- Hybrid materials (TPU for compliance, foam for padding)
- Drilling into the hoop if needed

## Related

- PCB dimensions and connector details: `hardware/sensor-rigid/`, `hardware/sensor-flex/`
- Flex PCB design rationale: `docs/initiatives/flex-sensor-pcb/DESIGN_PLAN.md`
- Physical architecture overview: `.context/PROJECT.md` (Physical Architecture section)

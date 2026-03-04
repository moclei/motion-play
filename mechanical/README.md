# Mechanical Design — Motion Play

Physical enclosures and mounting hardware for the Motion Play sensor system. These are the 3D-printed parts that house the PCBs, attach to the hoop, protect electronics from impact, and route cables.

## Status

Actively iterating on enclosure designs. The `specs/` folder defines the problem and constraints. The `enclosures/` folder contains parametric CAD models (Python/build123d) organized by design option, with each option exploring a different approach to the same problem.

## Structure

```
mechanical/
├── specs/                     # Dimensional specs, constraints, requirements
│   └── assembly-v0.1.yaml    # Core reference: all dimensions, current issues, requirements
├── enclosures/                # Parametric CAD models, one folder per design option
│   └── option-a/             # Clamshell with zip-tie retention
├── view.sh                   # Interactive launcher — view any model in OCP CAD Viewer
└── .venv/                    # Python venv (build123d, ocp_vscode)
```

Each option folder contains build123d Python scripts that generate STL/STEP files. The scripts are self-documenting — read the docstring at the top of each `.py` file for what the part is, how it prints, and its coordinate conventions.

## Problem Summary

Each sensor assembly mounts to a 25.25mm × 4mm steel flat bar hoop:
- **Outer face:** Rigid PCB (28.5 × 22.6 × 1.6mm) with connectors facing outward
- **Thin edge:** Flex PCB wraps 180° around the 4mm edge
- **Inner face:** Flex PCB lies flat, two VCNL4040 optical sensors face into the hoop interior, angled ±3° toward opposite hoop entrances

Three assemblies are spaced 120° around the hoop. Each connects to the main PCB via a JST-SH cable running along the hoop. The enclosure must protect electronics on both faces and across the thin edge, while leaving a window for the optical sensors.

See `specs/assembly-v0.1.yaml` for full dimensional constraints and requirements.

## Tooling

- **CAD:** build123d (Python, B-rep via OpenCASCADE)
- **Viewer:** OCP CAD Viewer standalone server on port 3939
- **Viewing models:** `./mechanical/view.sh` from project root — prompts to select an option and model
- **Environment:** Python venv at `mechanical/.venv` (created with python3.13)
- **Printing:** FDM, PLA for test-fitting, PETG for final. Prusa Core One with PrusaSlicer.

## Design Exploration

See `docs/explorations/sensor-enclosure.md` for the exploration of enclosure approaches.

## Related

- PCB dimensions and connector details: `hardware/sensor-rigid/`, `hardware/sensor-flex/`
- Flex PCB design rationale: `docs/initiatives/flex-sensor-pcb/DESIGN_PLAN.md`
- Physical architecture overview: `.context/PROJECT.md` (Physical Architecture section)

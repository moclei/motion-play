# Mechanical — Motion Play

Context for the `mechanical/` directory: 3D-printed enclosures and mounting hardware for the sensor system.

## What This Is

This folder contains the physical enclosure designs for the Motion Play sensor assemblies. Each sensor assembly mounts to a steel flat bar hoop and houses a rigid PCB (outer face), a flex PCB that wraps 180° around the bar's thin edge, and optical sensors (inner face). The enclosures protect electronics from ball impact, hold everything in position, and leave a window for the optical sensors.

The enclosures are designed in Python using build123d (parametric B-rep CAD on OpenCASCADE) and viewed in OCP CAD Viewer.

## Structure

```
mechanical/
├── CONTEXT.md                 # This file
├── FDM_DESIGN_RULES.md        # 3D printing design standards and tolerances
├── specs/                     # Problem definition and constraints
│   └── assembly-v0.1.yaml    # Dimensions, requirements, current prototype issues
├── enclosures/                # CAD models, one folder per design approach
│   └── option-X/             # Each option explores a different solution
│       ├── *.py              # build123d scripts (self-documenting)
│       ├── *.step            # Exported STEP files
│       └── *.stl             # Exported STL files (for slicing/printing)
├── view.sh                    # Interactive launcher for OCP CAD Viewer
└── .venv/                     # Python venv (build123d, ocp_vscode)
```

## Design Process

1. **Spec first**: `specs/assembly-v0.1.yaml` defines the physical constraints, measurements, and requirements. All designs reference this.
2. **Explore options**: `docs/explorations/sensor-enclosure.md` evaluates design approaches before committing to CAD work.
3. **Parametric CAD**: Each option folder contains build123d Python scripts. Dimensions trace back to the spec file or to `FDM_DESIGN_RULES.md`. Scripts are self-documenting — the docstring at the top of each `.py` file explains what the part is, how it prints, and its coordinate system.
4. **Visual evaluation**: Run scripts through `view.sh` to see parts in OCP CAD Viewer (standalone server on port 3939).
5. **Print and test**: Export STL, slice in PrusaSlicer, print on Prusa Core One. PLA for test-fitting, PETG for final parts.

## Coordinate Conventions

All enclosure scripts use the same axis definitions:

- **X** = across bar width (25.25mm)
- **Y** = along hoop circumference
- **Z** = radial — meaning depends on which face:
  - Outer shell: +Z = away from bar (outward from hoop)
  - Inner shell: +Z = into hoop interior (away from bar)
- **Origin** = center of the part's bar-contact surface

The outer and inner shells have opposite Z directions because they sit on opposite faces of the bar. Assembly scripts handle the 180° rotation around X.

## Tooling

- **CAD**: build123d — Python parametric B-rep modeling on OpenCASCADE
- **Viewer**: OCP CAD Viewer standalone server, port 3939
- **Launcher**: `./mechanical/view.sh` from project root
- **Environment**: Python 3.13 venv at `mechanical/.venv`
- **Printer**: Prusa Core One, PrusaSlicer
- **Materials**: PLA (test fitting), PETG (final parts)

## Related

- **PCB dimensions**: `hardware/sensor-rigid/`, `hardware/sensor-flex/`
- **Flex PCB rationale**: `docs/initiatives/flex-sensor-pcb/DESIGN_PLAN.md`
- **Design exploration**: `docs/explorations/sensor-enclosure.md`
- **Project overview**: `.context/PROJECT.md`

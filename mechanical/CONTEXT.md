# Mechanical — Motion Play

Context for the `mechanical/` directory: 3D-printed parts designed with build123d and viewed in OCP CAD Viewer.

## What This Is

This folder contains parametric 3D models for the Motion Play project and related experiments. The primary focus is sensor enclosures for the hoop assembly, but the same tooling supports any 3D-printable part — replacement components, fixtures, test jigs, etc.

All parts are designed in Python using build123d (parametric B-rep CAD on OpenCASCADE) and viewed in OCP CAD Viewer.

## Structure

```
mechanical/
├── CONTEXT.md                 # This file
├── FDM_DESIGN_RULES.md        # 3D printing design standards and tolerances
├── specs/                     # Problem definition and constraints
│   └── assembly-v0.1.yaml    # Hoop assembly dimensions and requirements
├── models/                    # CAD models, one folder per project
│   ├── enclosures/            # Sensor enclosure designs (option-a, interior-channel, etc.)
│   │   └── option-X/          # Each option explores a different solution
│   │       ├── *.py           # build123d scripts (self-documenting)
│   │       ├── *.step         # Exported STEP files
│   │       └── *.stl          # Exported STL files (for slicing/printing)
│   └── door-latch-spring/     # Replacement spring for a mortise latch (experiment)
├── view.sh                    # Interactive launcher: model selector + OCP viewer auto-start
└── .venv/                     # Python venv (build123d, ocp_vscode)
```

## Design Process

1. **Spec first**: For project-related parts, `specs/assembly-v0.1.yaml` defines the physical constraints. For standalone p1s, the script docstring describes the problem and measurements.
2. **Explore options**: `docs/explorations/sensor-enclosure.md` evaluates design approaches before committing to CAD work (for enclosures specifically).
3. **Parametric CAD**: Each project folder contains build123d Python scripts. Dimensions trace back to the spec file or to `FDM_DESIGN_RULES.md`. Scripts are self-documenting — the docstring at the top of each `.py` file explains what the part is, how it prints, and its coordinate system.
4. **Visual evaluation**: Run `./mechanical/view.sh` to select a project and model, then view in OCP CAD Viewer. The launcher auto-starts the viewer if it isn't running.
5. **Print and test**: Export STL, slice in PrusaSlicer, print on Prusa Core One. PLA for test-fitting, PETG for final parts.

## Coordinate Conventions

Enclosure scripts use consistent axis definitions (see individual script docstrings for project-specific conventions):

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
- **Launcher**: `./mechanical/view.sh` from project root (auto-starts viewer if needed)
- **Environment**: Python 3.13 venv at `mechanical/.venv`
- **Printer**: Prusa Core One, PrusaSlicer
- **Materials**: PLA (test fitting), PETG (final parts)

## Related

- **PCB dimensions**: `hardware/sensor-rigid/`, `hardware/sensor-flex/`
- **Flex PCB rationale**: `docs/initiatives/flex-sensor-pcb/DESIGN_PLAN.md`
- **Design exploration**: `docs/explorations/sensor-enclosure.md`
- **Project overview**: `.context/PROJECT.md`

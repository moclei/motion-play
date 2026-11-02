# PCB Layout Context Extraction

## Intent

Build a tool that extracts structured spatial data from KiCad `.kicad_pcb` files into a compact JSON format, enabling AI agents to reason about component placement, available board space, and layout constraints without visual access to KiCad. This is the PCB-layout counterpart to `circuit-context.json` (which captures schematic connectivity).

## Goals

- Extract board outline, component placements (position, rotation, bounding box), and unplaced components from any `.kicad_pcb` file
- Output a JSON file compact enough to fit in AI context (~200-400 lines) while capturing all spatially relevant information
- Enable AI-guided PCB layout sessions where the agent can give precise coordinate-based placement suggestions and verify available space

## Scope

What's in:
- Python extraction script using kiutils to parse `.kicad_pcb`
- Board outline extraction (rectangle or polygon)
- Placed component data: ref, value, footprint name, position (x, y), rotation, bounding box (width × height)
- Unplaced component list (footprints present but not yet positioned)
- Output to JSON file alongside the PCB

What's out:
- Trace/routing extraction (not needed for placement-phase layout guidance)
- Copper zone/pour extraction (too verbose, not needed for placement)
- Annotation or write-back to PCB files (read-only tool)
- Net/ratsnest data (circuit-context.json already covers connectivity)
- 3D model or rendering

## Constraints

- Must use kiutils (already installed in the project, v1.4.8)
- Output JSON must be self-contained and useful without reading the PCB file
- Bounding boxes should come from courtyard layer if available, falling back to fab layer or pad extents
- Script should work on all three PCB projects (pcb-main, sensor-rigid, sensor-flex) even though the immediate need is pcb-main

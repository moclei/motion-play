# PCB Routing Audit Tool

## Intent

A programmatic PCB routing audit tool that extracts trace geometry from KiCad `.kicad_pcb` files and reports proximity + length asymmetries between named nets. Built to fill the gap that has made the v7 I2C investigation hand-wavy about routing — the existing `pcb-layout-context.json` has component placement only, no traces.

## Goals

- v7 first deliverable: hard numbers on `/I2C_SDA` vs `/I2C_SCL` routing geometry near `{U5 (BQ24195), L1, L2, U5's SW pin, /VBUS, /VSYS, /BAT}`, suitable for pasting into `docs/debugging/v7-i2c-investigation.md` as a new phase. Either reinforces or weakens the routing-asymmetry-explains-SDA-only-fault hypothesis with measured values rather than placement-based handwaving.
- Reusable across the project's other PCBs (v8 main, sensor-rigid, sensor-flex).
- Output both machine-readable JSON and human-readable Markdown.

## Scope

What's in:
- Per-net trace segment extraction (start/end, width, layer, net name) and via extraction.
- Per-net total length and per-layer length.
- Footprint pad world-space positions (rotation- and offset-corrected) and per-layer footprint bounding boxes.
- Min-distance computation: target net → component bbox, target net → named pad, target net → another net.
- Asymmetry diff between a named pair of nets (length, per-layer length, proximities).
- JSON + Markdown reports.
- Audit spec format (small JSON file naming target nets, noisy components/pads/nets) so audits are declarative and reusable.

What's out:
- Pad-to-pad path-distance via segment graph traversal — defer to v2. Total net length plus proximity is enough for the v7 question.
- Trace impedance, signal-integrity math, EM-coupling modeling, current density, via thermal analysis. This is a focused diagnostic helper, not a full SI tool.
- Cross-PCB comparison (e.g., automated v7-vs-v8 routing diff) — defer to v2.
- Editing the `.kicad_pcb` — this tool is read-only.

## Constraints

- Use `kiutils` for parsing (already a project dependency in `tools/`). No `pcbnew` Python API — would force KiCad's bundled Python and break CLI/CI use on macOS.
- Use `Shapely` for 2D geometry (LineString, Polygon, distance, buffer). New dependency, well-maintained.
- Honor the project rule in `.context/PROJECT.md` and `tools/CONTEXT.md`: do not read `.kicad_pcb` directly elsewhere. This tool is the read-from-pcb mechanism.
- Live alongside the existing `tools/pcb-context/extract.py`; complement it, don't replace it.
- v1 must be tight enough to ship in one focused session (~3.5–5 hours of work).

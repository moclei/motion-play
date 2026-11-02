# PCB Layout Context Extraction — Plan

## Approach

Single Python script at `tools/pcb-context/extract.py` that reads a `.kicad_pcb` file via kiutils and produces a `pcb-layout-context.json` in the same directory as the input PCB. The script mirrors the pattern of `tools/schematic-context/extract.py` but for spatial/placement data rather than connectivity.

### Output Schema

```json
{
  "meta": {
    "source_file": "hardware/pcb-main/kicad/motion-play-main.kicad_pcb",
    "extracted_at": "2026-03-11T...",
    "board_area_mm2": 3024.0
  },
  "board_outline": {
    "type": "rectangle",
    "min_x": 77.6, "min_y": 101.0,
    "max_x": 164.0, "max_y": 136.0,
    "width": 86.4, "height": 35.0
  },
  "placed_components": [
    {
      "ref": "U1",
      "value": "TCA9548APWR",
      "footprint": "TSSOP-24_4.4x7.8mm_P0.65mm",
      "x": 110.5,
      "y": 125.2,
      "rotation": 0,
      "side": "front",
      "bbox": { "width": 7.8, "height": 4.4 }
    }
  ],
  "unplaced_components": [
    {
      "ref": "U5",
      "value": "BQ24195RGER",
      "footprint": "VQFN-24_L4.0-W4.0-P0.50-TL-EP2.8"
    }
  ],
  "summary": {
    "total_components": 86,
    "placed": 35,
    "unplaced": 51,
    "board_utilization_pct": 45.2
  }
}
```

### Bounding Box Strategy

Component bounding boxes (width × height at rotation=0) are needed to understand how much space each footprint occupies. Extraction priority:

1. **Courtyard layer** (`F.CrtYd` / `B.CrtYd`) — preferred, includes manufacturer-recommended clearance
2. **Fab layer** (`F.Fab` / `B.Fab`) — physical component outline
3. **Pad extents** — fallback: compute bounding box from pad positions + pad sizes

For rotated components, the reported `bbox` is the axis-aligned bounding box at the placed rotation (what actually matters for space planning).

### File Location

- Script: `tools/pcb-context/extract.py`
- Output: co-located with input PCB, e.g., `hardware/pcb-main/kicad/pcb-layout-context.json`
- Dependencies: kiutils (already in project), no new packages needed

### Reference: Existing Schematic Context Tool

`tools/schematic-context/extract.py` provides a working pattern for:
- CLI argument handling (input file path)
- kiutils parsing patterns
- JSON output formatting
- `--previous` flag for diffing against prior extractions

We may add a `--previous` diff mode later, but it's not needed for V1.

## Open Questions

- Should the output include mounting holes and fiducials, or filter to electrical components only? (Leaning toward including everything with a ref designator)
- Is pad-level data useful (e.g., for understanding pin positions of QFN thermal pads)? (Leaning no — too verbose for V1, can add later)

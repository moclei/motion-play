# PCB Routing Audit Tool — Plan

## Approach

Two-stage pipeline that mirrors the existing `tools/schematic-context/` and `tools/pcb-context/extract.py` pattern:

1. **`routing_extract.py`** — reads `.kicad_pcb` via `kiutils`, writes `pcb-routing-context.json` (per-net segments + vias, per-footprint pads in world-space, per-layer bboxes). One-shot extraction, separate file from the existing `pcb-layout-context.json` (combining them would double the size of a file that's already verbose).

2. **`routing_audit.py`** — reads that JSON plus a small audit spec (target nets, noisy components, noisy pads, noisy nets, compare pair) and writes a JSON report plus a Markdown report.

The intermediate JSON becomes a reusable artifact: future audits don't re-parse the `.kicad_pcb`. This matches the existing convention where `circuit-context.json` and `pcb-layout-context.json` are extracted once and consumed many times.

### Library choices

- **`kiutils ≥ 1.4.8`** — already a project dependency. For *reading* tracks/vias/pads it's straightforward; the surgical-edit edge cases that sometimes lag KiCad releases don't apply to a read-only tool.
- **`Shapely ≥ 2.0`** — 2D geometry (`LineString` for tracks, `Polygon` for footprint bboxes, `Point.buffer()` for pads with effective radius, `.distance()` for proximity). Add to `requirements.txt`.
- **No `pcbnew` Python API** — would force the user into KiCad's bundled Python interpreter, messy on macOS.
- **No custom S-expression parser** — reinventing the wheel, no benefit over `kiutils` for this scope.

### File structure

```
tools/pcb-context/
├── extract.py             (existing — placement only, untouched)
├── place_power.py         (existing, untouched)
├── routing_extract.py     (NEW)
├── routing_audit.py       (NEW)
├── audit-specs/           (NEW)
│   └── v7-main-i2c.json   (audit spec for v7 first deliverable)
├── requirements.txt       (NEW or UPDATE — add shapely)
└── README.md              (UPDATE — add routing extractor + auditor sections)
```

`pcb-routing-context.json` lives next to `pcb-layout-context.json` in each PCB's `kicad/` folder.

## Technical Notes

### Segment extraction

`kiutils.board.Board.traceItems` yields `Segment`, `Via`, and `Arc` objects. Each segment has `start`, `end`, `width`, `layer`, `net` (an integer index into `Board.nets`). Build a net-name → list-of-segments map. Arcs are rare on this board but should be handled (either approximated as a chord for v1 or sampled into a polyline; sampling is safer for length).

### Pad world-space resolution

Footprint pads are stored with offsets relative to the footprint's reference position. World-space pad position requires rotating the pad offset by the footprint's rotation angle and adding the footprint position. Pad shape (rect / oval / circle) and size matter for proximity — represent each pad as a `Point.buffer(effective_radius)` for v1 (treat ovals/rects conservatively as their bounding circle).

### Layer awareness

Tracks live on `F.Cu`, `B.Cu`, `In1.Cu`, `In2.Cu`. Proximity must be layer-aware: an SDA trace on `F.Cu` near an inductor pad on `F.Cu` is meaningfully closer than one on `B.Cu`. Compute proximity per (net, target) per layer; the report surfaces the minimum across layers and notes which layer it occurred on. For inner-layer routing that crosses layers via vias, report per-layer proximity separately.

### Net naming

KiCad nets typically have a leading slash (`/I2C_SDA`, `/I2C_SCL`). Audit spec strings must match exactly. Provide a `--list-nets` helper on the extractor for discoverability.

### Output schema sketches

`pcb-routing-context.json` (rough):

```json
{
  "meta": {
    "source_file": "hardware/pcb-main/kicad/motion-play-main.kicad_pcb",
    "extracted_at": "2026-04-25T...",
    "kicad_format_version": "20240108"
  },
  "nets": {
    "/I2C_SDA": {
      "name": "/I2C_SDA",
      "segments": [
        {"start": [x, y], "end": [x, y], "width": 0.2, "layer": "F.Cu"}
      ],
      "vias": [
        {"position": [x, y], "drill": 0.3, "size": 0.6, "layers": ["F.Cu", "B.Cu"]}
      ],
      "total_length_mm": 12.4,
      "length_by_layer": {"F.Cu": 9.8, "B.Cu": 2.6}
    }
  },
  "footprints": [
    {
      "ref": "U5",
      "value": "BQ24195RGER",
      "position": [96.885, 117.564],
      "rotation": 90,
      "side": "front",
      "bbox_by_layer": {"F.Cu": {"min_x": ..., "max_x": ..., "min_y": ..., "max_y": ...}},
      "pads": [
        {"number": "1", "net": "/VBUS", "position": [x, y], "layer": "F.Cu",
         "size": [0.3, 0.5], "shape": "rect"}
      ]
    }
  ]
}
```

Audit spec (`audit-specs/v7-main-i2c.json`):

```json
{
  "pcb": "hardware/pcb-main/kicad/motion-play-main.kicad_pcb",
  "routing_context": "hardware/pcb-main/kicad/pcb-routing-context.json",
  "target_nets": ["/I2C_SDA", "/I2C_SCL"],
  "noisy_components": ["L1", "L2", "U5", "U6"],
  "noisy_pads": [
    {"ref": "U5", "pad": "19", "label": "BQ24195 SW pin (pad 19)"},
    {"ref": "U5", "pad": "20", "label": "BQ24195 SW pin (pad 20)"}
  ],
  "noisy_nets": [
    "/Power Management/Protected_VBUS",
    "/Power Management/VSYS",
    "/Power Management/VBAT",
    "/Power Management/BQ_SW",
    "/Power Management/BOOST_SW"
  ],
  "compare_pair": ["/I2C_SDA", "/I2C_SCL"]
}
```

Note: hierarchical-sheet net names on this board are prefixed (e.g. `/Power Management/VSYS`, not `/VSYS`). Use `routing_extract.py --list-nets` for exact strings. The BQ24195RGER's SW pin is split across pads 19 and 20, not pad 7.

Audit report JSON (rough):

```json
{
  "meta": {"spec": "v7-main-i2c.json", "pcb": "...", "generated_at": "..."},
  "nets": {
    "/I2C_SDA": {
      "total_length_mm": 12.4,
      "length_by_layer": {"F.Cu": 9.8, "B.Cu": 2.6},
      "proximities": {
        "L1": {"min_distance_mm": 4.2, "layer": "F.Cu", "closest_point": [x, y]},
        "U5.pad.7": {"min_distance_mm": 6.1, "layer": "F.Cu", "label": "BQ24195 SW pin"},
        "/VBUS": {"min_distance_mm": 3.8, "layer": "F.Cu"}
      }
    }
  },
  "asymmetry": {
    "pair": ["/I2C_SDA", "/I2C_SCL"],
    "diffs": [
      {"metric": "total_length_mm", "sda": 12.4, "scl": 11.9, "delta": 0.5},
      {"metric": "min_distance_to_L1_mm", "sda": 4.2, "scl": 8.7, "delta": -4.5}
    ]
  }
}
```

Audit report Markdown structure:

```markdown
## Routing audit — <pcb name>

### Net /I2C_SDA
- Total length: 12.4 mm  (F.Cu 9.8, B.Cu 2.6)
- Min clearance to L1: 4.2 mm (F.Cu)
- Min clearance to L2: 11.7 mm (F.Cu)
- Min clearance to U5 SW pin: 6.1 mm (F.Cu)
- Min clearance to /VBUS: 3.8 mm (F.Cu)

### Net /I2C_SCL
... same ...

### Asymmetry (SDA vs SCL)
| Metric              | SDA  | SCL  | Δ     |
|---------------------|------|------|-------|
| Total length (mm)   | 12.4 | 11.9 | +0.5  |
| Min dist to L1 (mm) | 4.2  | 8.7  | −4.5  |
```

Numbers rounded to 0.1 mm in Markdown; raw values preserved in JSON.

### Verification approach

Trust nothing until verified against KiCad's built-in tools:
- 3 net lengths checked against KiCad's Net Inspector / Properties → Track Length.
- 2–3 pad coordinates checked against KiCad's measure-from-origin.
- 1 proximity pair (e.g., `/I2C_SDA` → `L1`) measured manually in KiCad and compared.
- Tolerance ±0.05 mm on all three.

## Open Questions

- KiCad format version of `motion-play-main.kicad_pcb` — confirm `kiutils 1.4.8` reads it cleanly. If it doesn't, fallback is either pin to a working `kiutils` version or write a tiny custom parser for just `(segment ...)` / `(via ...)` blocks. Treat as contingency, not v1 risk.
- Audit spec location: tool-side (`tools/pcb-context/audit-specs/`) vs board-side (`hardware/pcb-main/audit-specs/`). Tentatively tool-side for v1 since there's only one spec and it's tightly coupled to the auditor's schema.
- Arc handling: sample into polylines for length accuracy, or skip in v1 (this board may not use any arcs)? Decide after looking at the actual `.kicad_pcb`.

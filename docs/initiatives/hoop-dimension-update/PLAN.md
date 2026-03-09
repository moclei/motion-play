# Hoop Dimension Update — Plan

## Approach

### Phase 1: Audit

Run a project-wide search for known old values and any hoop-dimension references. Target patterns:

- `445` (old diameter) — will have false positives, review each hit
- `222.5` (old radius) — more specific, fewer false positives
- `1398` or `1,398` (old circumference)
- `466` (old arc spacing)
- `430` (old clear-arc between assemblies)
- `inner_diameter`, `inner_radius`, `hoop_radius`, `HOOP_RADIUS`, etc. — any named references to hoop dimensions in code or docs

Produce a checklist of every file and line that needs updating.

### Phase 2: Canonical source

Create `mechanical/specs/hoop.yaml` (or extend `assembly-v0.1.yaml` with a clearly marked canonical section) containing all hoop physical properties:

```yaml
hoop:
  inner_diameter_mm: 505
  inner_radius_mm: 252.5
  inner_circumference_mm: 1586.4  # π × 505
  bar_width_mm: 25.25
  bar_thickness_mm: 4.0
  material: steel_flat_bar
  sensor_count: 3
  sensor_spacing_deg: 120
  arc_between_sensors_mm: 528.8   # circumference / 3
```

Decide whether this lives as a standalone file or as a section within `assembly-v0.1.yaml`. The key requirement is that it's clearly the single source of truth and easy for both humans and scripts to reference.

### Phase 3: Update references

Work through the audit checklist, updating each reference. For documentation files, update the values directly. For CAD scripts (build123d `.py` files), evaluate whether to:

- Import/parse the YAML at the top of the script (adds a `pyyaml` dependency but creates a true single source)
- Or define constants at the top with a comment pointing to the canonical file (simpler, no dependency, but requires manual sync)

The pragmatic choice for now is probably the comment-and-constant approach, with a future option to switch to YAML parsing if the project grows more scripts.

### Phase 4: Verify

Spot-check that updated CAD scripts still run and produce expected geometry. Ensure no documentation contradictions remain.

## Open Questions

- Should the canonical hoop file be standalone (`hoop.yaml`) or a section within the existing `assembly-v0.1.yaml`? Leaning toward standalone since the hoop properties are referenced beyond just the sensor assembly context.
- Are there firmware constants (e.g., circumference used for LED count calculations, transit distance assumptions) that also need updating? Need to check `firmware/` during the audit.
- Does `tools/transit-calculator.py` use hoop dimensions? Likely yes — include in audit.

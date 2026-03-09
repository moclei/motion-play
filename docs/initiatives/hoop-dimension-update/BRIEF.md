# Hoop Dimension Update

## Intent

The hoop inner diameter has changed from 445mm to 505mm. References to the old diameter and derived values (radius, circumference, arc spacing) are scattered across documentation, CAD scripts, and potentially firmware/tools. This initiative updates all stale references and centralizes hoop dimensions into a single source of truth so future changes only require editing one file.

## Goals

- Every reference to hoop dimensions across the project reflects the current 505mm inner diameter
- A single canonical file defines hoop physical properties (dimensions, bar cross-section, screw hole spacing, etc.)
- Documentation and CAD scripts reference or import from that canonical source rather than hard-coding values
- No regression — CAD scripts that use hoop dimensions still produce correct geometry after the update

## Scope

What's in:
- Audit all project files for references to old hoop dimensions (445mm diameter, 222.5mm radius, ~1398mm circumference, ~466mm arc spacing, and any other derived values)
- Create or designate a canonical hoop dimensions file (likely a YAML in `mechanical/specs/`)
- Update all stale references
- Where practical, refactor CAD scripts to import from the canonical source instead of defining hoop constants locally

What's out:
- Redesigning the sensor enclosures for the new hoop size (separate concern — the enclosure geometry is parametric but a resize is a distinct task)
- Updating the LED strip lengths or channel design (that's the interior-channel initiative)
- Any firmware or calibration changes that might be needed for the larger hoop (separate if needed)

## Constraints

- The audit must cover the full project tree, but context window limitations mean it should be done methodically (e.g., subagent search, then manual review of hits)
- The canonical dimensions file should be human-readable (YAML preferred) and straightforward for build123d scripts to parse
- `assembly-v0.1.yaml` has already been updated with the new diameter — this initiative covers everything else

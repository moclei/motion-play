# Hoop Dimension Update — Tasks

## Phase 1: Audit
- [ ] Search project-wide for old diameter (445), radius (222.5), circumference (1398), arc spacing (466, 430)
- [ ] Search for named hoop dimension references in code (`inner_diameter`, `hoop_radius`, `HOOP_RADIUS`, etc.)
- [ ] Search firmware/ for any hoop-derived constants (circumference, LED count, transit distance)
- [ ] Search tools/ (especially transit-calculator.py) for hoop references
- [ ] Compile a complete list of files and lines that need updating

## Phase 2: Canonical source
- [ ] Decide: standalone `hoop.yaml` vs. section in `assembly-v0.1.yaml`
- [ ] Create the canonical hoop dimensions file
- [ ] Document the convention in `mechanical/CONTEXT.md` (point to the file as the single source of truth)

## Phase 3: Update references
- [ ] Update all documentation files from audit list
- [ ] Update all CAD scripts from audit list (constants + comment pointing to canonical source)
- [ ] Update any firmware or tools files from audit list
- [ ] Update `assembly-v0.1.yaml` to reference the canonical source if it's a separate file

## Phase 4: Verify
- [ ] Run updated CAD scripts and confirm they execute without errors
- [ ] Spot-check one or two scripts produce geometry consistent with 505mm diameter
- [ ] Grep once more for old values to confirm nothing was missed

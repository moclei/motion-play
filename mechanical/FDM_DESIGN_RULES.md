# FDM 3D Printing Design Rules

Standard minimums and tolerances for FDM-printed parts in this project. Referenced by build123d scripts when setting wall thicknesses, clearances, boss sizes, and other print-sensitive dimensions.

**Printer:** Prusa Core One (0.4mm nozzle)
**Slicer:** PrusaSlicer
**Materials:** PLA (prototyping), PETG (final)

## Wall Thickness

| Rule | Minimum | Preferred |
|------|---------|-----------|
| Perimeter wall | 1.2mm (3 perimeters) | 1.6mm (4 perimeters) |
| Structural wall (load-bearing) | 1.6mm | 2.0mm |
| Thin feature / rib | 0.8mm (2 perimeters) | 1.2mm |

## Hole and Boss Design

| Rule | Value | Notes |
|------|-------|-------|
| Hole-to-edge minimum | 2.0mm | Material between hole wall and nearest edge |
| Screw boss OD | ≥ 2× insert hole diameter | e.g., M2.5 insert (3.6mm hole) → boss ≥ 7.2mm |
| Heat-set insert hole depth | insert length + 0.5mm | Extra depth for melt overflow |
| Vertical holes | print 0.1–0.2mm undersized | Drill or ream to final size if needed |

## Clearances and Tolerances

| Fit Type | Clearance per side | Use case |
|----------|-------------------|----------|
| Press fit | 0.05–0.10mm | Inserts, pins |
| Snug / sliding fit | 0.15–0.25mm | Lids, mating shells |
| Loose / assembly fit | 0.30–0.50mm | Parts that need to slide freely |

## Overhangs and Bridging

| Rule | Limit | Notes |
|------|-------|-------|
| Unsupported overhang angle | ≤ 45° from vertical | Beyond 45° needs support |
| Unsupported bridge span | ≤ 10mm | Beyond 10mm may sag |
| Bridging for screw holes | Support or print vertically | Horizontal holes > 3mm need support |

## Layer and Feature Limits

| Rule | Value |
|------|-------|
| Minimum Z-axis feature | 0.2mm (1 layer at standard height) |
| Minimum XY feature | 0.4mm (nozzle diameter) |
| Minimum slot width | 0.5mm |
| Minimum emboss/deboss depth | 0.4mm |

## Fastener Reference

| Screw | Clearance Hole | Heat-Set Insert Hole | Boss OD (min) |
|-------|---------------|---------------------|---------------|
| M2 | 2.4mm | 3.2mm | 6.4mm |
| M2.5 | 2.9mm | 3.6mm | 7.2mm |
| M3 | 3.4mm | 4.0mm | 8.0mm |

## General Principles

- **Weakest axis is Z**: Layer adhesion is the weakest direction. Orient parts so critical loads are in-plane (XY), not across layers.
- **Fillets at stress points**: ≥ 0.5mm radius at inside corners to reduce delamination risk.
- **Round external corners**: Reduces stress concentration and improves print quality.
- **Hole compensation**: FDM holes print ~0.1–0.2mm undersized. Add compensation in the model or plan to drill.
- **Test fit with PLA first**: Cheap and fast iteration before committing to PETG.

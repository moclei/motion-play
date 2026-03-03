# Sensor Enclosure Design — Exploration

## Problem

The current 3D-printed prototype enclosures are fragile, difficult to install, and offer no impact protection. This blocks the near-term milestone of portable, battery-powered playtesting where balls will be kicked at the hoop at up to 20 mph.

Specific failure modes of the current design:
- Easily knocked loose by a stray hand, let alone a ball
- Flex PCB bend zone and sensor face are fully exposed
- Friction-fit lid is not secure
- Interior clip piece requires excessive force to install
- No impact absorption — a direct hit could damage PCBs or unseat the assembly

See `mechanical/specs/assembly-v0.1.yaml` for full dimensional constraints, current prototype description, and requirements.

## Current State

Each sensor assembly mounts to a 25.25mm × 4mm steel flat bar hoop:
- **Outer face:** Rigid PCB (28.5 × 22.6 × 1.6mm) with components facing outward, tallest component 3mm (JST-SH connector)
- **Thin edge:** Flex PCB wraps 180° around the 4mm edge (bend arc ~14–15mm diameter)
- **Inner face:** Flex PCB lies flat, optical sensors (VCNL4040, 1.4mm tall) face into the hoop interior

Three assemblies are spaced 120° around the hoop (~466mm apart along the arc). Each connects to the main PCB via a JST-SH 5-pin cable that runs along the hoop.

The fundamental awkwardness is that the enclosure must protect electronics on *both* faces of the bar *and* the transition around the thin edge, while leaving a window for the optical sensors on the inner face.

The current prototype uses a two-piece design (outer box + inner clip) where the same parts serve as both the mount and the housing. This conflation is the root cause of most problems — the clips that grip the bar also form the enclosure walls, so any compromise in one function (e.g., making clips easier to install) weakens the other (structural integrity under impact).

## Options

### Option A: Clamshell with Zip-Tie Retention

**Concept:** A two-piece clamshell that wraps entirely around the flat bar, secured to the bar with zip ties through printed slots. The two halves fasten to *each other* with a separate reusable mechanism (snap latches or M2 screws with heat-set inserts).

**Piece breakdown:**
1. **Outer shell** — houses the rigid PCB. Has a cavity shaped to the PCB footprint with clearance for the JST-SH connector. The JST-SH cable exits through a slot with a printed strain relief. Zip-tie slots on both sides for bar retention.
2. **Inner shell** — flat base for the flex PCB sensor area. Sensor window is an open cutout with smooth convex ramps on all sides (ball rolls over, doesn't catch). The flex PCB attaches with double-sided tape as before. Zip-tie slots align with the outer shell.
3. **Bend channel** — either integrated into the shells or a separate C/U-shaped piece that guides and protects the flex PCB's 180° bend around the thin edge. Keeps the bend radius controlled and shields it from impact.

**How it fastens:**
- **To the bar:** 1–2 zip ties thread through slots in both shells, wrapping around the entire assembly + bar. Zip ties provide clamping force; the printed shells provide shape and protection. This is rarely undone.
- **Shells to each other:** Snap latches (like a GoPro housing) or 2× M2 screws with heat-set inserts. This is opened frequently during development for PCB access, so it must be reusable and tool-minimal.

**Sensor window design:**
- Open cutout in the inner shell (no lens for now)
- Smooth convex ramps on all four sides — a ball approaching from any direction along the hoop surface rides up and over the window
- Ramp height ~2–3mm above sensor face, enough to prevent direct contact but not occlude the sensor's ~40° detection cone
- Geometry could accept a polycarbonate or acrylic window later (both are IR-transparent at the VCNL4040's 940nm wavelength)

**Cable/connector access:**
- JST-SH cable exits through a slot in the outer shell, with a printed strain relief channel to survive accidental tugs
- FPC connector remains accessible when the outer shell is opened (unscrew/unlatch)

**Material:**
- PETG preferred over PLA for impact toughness (slight flex before failure vs. brittle shattering)
- TPU bumper pads on impact-likely outer surfaces (optional, press-fit)
- Zip ties: standard nylon, 2.5mm or 3.6mm width

**Precedents:**
- Bike light/computer mounts (Garmin, Cateye) — separate mount from housing, zip-tie or strap retention to the bar
- GoPro housings — hinged clamshell with latching lid, impact-rated
- Parking sensors — recessed sensor face with bumper surface above
- Cable management C-channels — simple guide for the flex PCB bend zone
- Strain relief boots — printed channel at cable exit to prevent sharp bending

**Pros:**
- Fully encloses all electronics including the vulnerable bend zone
- Zip ties are extremely strong, cheap, and available everywhere
- Separation of bar-retention (zip ties) from shell-closure (latches/screws) means each can be optimized independently
- PETG + zip ties should easily survive 10 mph ball impacts
- Simple to iterate — reprinting one shell doesn't require reprinting the other
- Smooth ramp geometry is forgiving for off-angle impacts

**Cons:**
- Zip ties are single-use (need to cut to reposition on hoop) — acceptable since repositioning is rare
- More complex print geometry than the current prototype (two shells + bend channel vs. box + clip)
- Heat-set inserts add a step (need a soldering iron to install) — could use snap latches instead to avoid this
- Ramp geometry around sensor window needs careful tuning to avoid occluding the sensor's detection cone

**Open questions:**
- Exact zip-tie size and slot dimensions — need to test fit with real zip ties
- Snap latches vs. screws for shell closure — may need to prototype both
- Whether the bend channel should be integrated into one of the shells or be a separate piece
- Minimum ramp angle that deflects a ball without reducing sensor range
- Whether the outer shell needs venting (unlikely but worth considering for humidity)

### Option B: *(reserved for future variation)*

### Option C: *(reserved for future variation)*

## Recommendation

*(Empty — exploring options. Option A is the current leading candidate based on analysis of bicycle mount, action camera, and parking sensor design patterns.)*

## Decision

**Status: Open**

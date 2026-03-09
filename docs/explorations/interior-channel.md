# Interior Hoop Channel — Exploration

## Problem

The interior circumference of the hoop contains two sensitive component systems — the VCNL4040 sensor assemblies and the WS2812B LED strip — both of which are currently exposed. A ball making direct impact at speed could damage the LED strip, unseat solder joints, or strike the sensors. Beyond impact risk, exposed wiring and bare flex PCBs look unfinished, which matters now that the project is moving from workstation prototype toward a playable game.

Specific issues:

- **Impact vulnerability:** The LED strip sits on the interior hoop surface with no protection. A ball hitting the strip directly could crack solder joints or damage individual LEDs.
- **Exposed wiring:** The LED strip must be cut into sections and re-soldered with bridge wires that route around the sensor assemblies. Those bridge wires and solder joints are currently loose and exposed, vulnerable to snagging by passing objects.
- **Sensor exposure:** The VCNL4040 sensors face into the hoop interior (negative Z axis). The sensor assembly's inner shell has ramped edges that help deflect impacts, but the areas between assemblies offer no protection to the LED strip.
- **Aesthetics:** Exposed circuitry, tape, and wiring detract from the overall appearance. A product-like finish — even for a prototype — supports playtesting with others and motivates continued development.

## Current State

### Hoop geometry

- Steel flat bar hoop, inner diameter 505mm, inner circumference ~1,586mm
- Bar cross-section: 25.25mm wide (flat face) × 4mm thick (thin edge)
- 3 sensor assemblies at 120° spacing → ~529mm arc between assemblies
- Sensor assembly footprint along circumference: ~33–38mm (depending on design version)
- Available open arc per section: ~491–496mm
- The hoop has screw holes spaced around the circumference

### LED strip

- WS2812B individually-addressable RGB LED strip
- ~16mm LED-to-LED spacing (center-to-center)
- Comes in a flexible PCB strip with a clear silicone/rubber coating
- Copper cut-pads between every pair of LEDs (labeled GND, DIN, 5V) allow cutting to arbitrary lengths and re-soldering
- The strip needs to span approximately the full interior circumference to provide visual feedback
- Currently attached to the interior hoop surface (double-sided tape or similar)
- JST-PH 3-wire cable connects the strip to the main controller box

### LED strip routing around sensors

The LED strip and sensor assemblies cannot co-exist in the same physical space — the sensors occupy the interior face and must have an unobstructed view into the hoop center. The current approach (proven on the previous prototype):

1. Cut the LED strip into sections that fit between sensor assemblies
2. Solder 3-wire bridge cables (GND, DIN, 5V) at each cut point
3. Route the bridge wires around the sensor assembly so they don't block the sensors
4. The entire strip remains electrically "one strip" — the microcontroller addresses it as a continuous chain

This works but the bridge wires are loose and exposed. They need to be re-done for the new 505mm hoop and the new sensor assembly geometry.

### What exists today

The sensor assemblies (Option A clamshell design) provide impact protection for the sensors themselves via ramped inner shells. But nothing protects the LED strip between them, and nothing manages the bridge wires. The hoop interior between sensor assemblies is bare steel bar with components taped on.

## Options

### Option A: Off-the-shelf rubber U-channel

**What it is:** Purchase pre-made EPDM rubber U-channel (e.g., Metro Moulded Parts LP 102-U: 15/16" wide × 3/4" deep × 13/16" inside width) and cut sections to fit between sensor assemblies. Glue or tape them to the interior hoop surface. The LED strip sits inside the channel.

**Effort:** Low (purchase + cut + glue)

**Pros:**
- Minimal fabrication — buy and attach
- Rubber absorbs impact well
- Proven product designed for edge protection

**Cons:**
- Standard sizes don't match the hoop geometry precisely
- Attachment is glue/tape only — shear forces from ball impact could dislodge sections
- Sections simply abut the sensor assemblies with no designed interface
- Not cheap, and shipping adds lead time
- Cutting rubber cleanly to arbitrary arc lengths is fiddly
- No accommodation for LED strip bridge wires — they'd still be exposed at the transitions
- Looks "added on" rather than integrated

### Option B: 3D-printed custom channel segments

**What it is:** Design and print PLA channel segments that conform to the hoop curvature, mount securely, house the LED strip, and eventually interface with the sensor assemblies. Six identical segments (two per arc section between sensor assemblies).

**Geometry rationale:** Each arc section between sensor assemblies is ~491mm. A single piece would far exceed the Prusa Core One build plate (250 × 220mm). Two pieces per section → ~245mm arc per segment. At 252.5mm hoop radius, this subtends ~55.6°, giving a chord length of ~235mm and a sagitta of ~29mm. The bounding box of one segment is roughly 235 × (channel width + 29)mm — fits the build plate. Two segments could nest on one plate (concave-to-convex), enabling 2–3 print batches for all six.

**Attachment options:**
- Clip-over-edge feature gripping the 4mm bar edge (push-on with slight interference, hard to pull off)
- Screw through channel base into existing hoop screw holes
- Adhesive as supplementary retention
- Combination of clip + screw for maximum impact resistance

**Pros:**
- Custom fit to exact hoop curvature and bar dimensions
- Can incorporate clip, screw, and interface features
- Designed endpoint geometry can couple with sensor assemblies
- Internal features possible: LED strip shelf, wire routing channels, cosmetic covers
- Cheap (PLA filament), fast iteration, no lead time beyond print time
- Six identical parts — one design, batch printing
- Upgrade path to PETG for toughness once design is validated

**Cons:**
- Requires CAD design effort (build123d scripting)
- PLA is brittle under sharp impact (acceptable for prototype; PETG for final)
- Curved parts require careful print orientation for strength
- Six segments means twelve seams (six segment-to-segment, six segment-to-assembly) that need to look clean

**Candidate design features for the initiative:**

1. **U-channel cross-section** — Sized to house the WS2812B strip (strip PCB is ~10–12mm wide; silicone sleeve adds ~2mm). Wall height sufficient to prevent ball contact with the strip, shallow enough for LED light to remain visible.
2. **Hoop curvature conformance** — Base follows the 252.5mm interior radius so segments sit flush against the bar.
3. **Clip-over-edge retention** — Lips on each side grip the 4mm bar edges. Push-on installation with enough interference to resist casual removal, but not so much that installation is difficult.
4. **Screw mounting points** — Alignment with existing hoop screw holes for positive retention against impact shear.
5. **Segment-to-segment joint** — Tongue-and-groove or lap joint where two segments meet at the midpoint of an arc section. The hoop provides the rigid alignment backbone; the joint prevents gaps and lateral shift.
6. **Wire routing conduit at segment ends** — Where a segment meets a sensor assembly, a small covered raceway routes the LED strip bridge wires (3× conductors: GND, DIN, 5V) around the assembly. Protects wires from snagging and hides them.
7. **LED strip shelf/retainer** — Internal ledge or clips that hold the LED strip at a consistent depth, possibly with a friction fit so the strip doesn't need adhesive.
8. **Diffuser/cover window** — Optional: a slot or shelf to accept a translucent cover (e.g., thin polycarbonate or frosted acrylic strip) to diffuse LED light and hide individual LED point sources. Not essential for v1 but designing the slot in from the start costs nothing.
9. **Sensor assembly interface** — Mating geometry at the channel endpoints that couples with the sensor assembly's inner shell. Could be as simple as a matching profile that butts up cleanly, or as integrated as interlocking features. Defer detailed design until the channel cross-section is validated, but define the interface surface from the start.
10. **Parametric design** — The build123d script should pull hoop dimensions from a central spec (or at minimum, define them as named constants at the top) so the entire channel can be regenerated for a different hoop size.

### Option C: Hybrid — 3D-printed end adapters + off-the-shelf channel

**What it is:** Print short adapter pieces that mount at each sensor assembly and accept a standard rubber U-channel between them. The adapters handle the interface and wire routing; the off-the-shelf channel handles the long run.

**Effort:** Medium

**Pros:**
- Less CAD work than full custom channel
- Rubber channel provides good impact absorption for the long runs
- Adapters solve the interface problem that off-the-shelf alone doesn't

**Cons:**
- Still requires purchasing and cutting rubber channel
- Mixed materials and aesthetics (printed PLA meets rubber)
- More complex assembly (adapters + channel + glue)
- Harder to iterate — changing the adapter means re-fitting the rubber

## Recommendation

**Option B (3D-printed custom channel segments)** is the recommended direction.

The core argument: this project is fundamentally about engineering depth, and the channel is a relatively contained mechanical design problem that exercises the same build123d + Prusa Core One pipeline already established for the sensor enclosures. The result will be better-fitting, better-looking, and more integrated than anything off-the-shelf. The print cost is negligible (six PLA segments use minimal filament), and iteration is same-day.

Option A is the fastest path to "something" but results in a less polished, less secure, and less integrated outcome. Option C adds complexity without clear benefit over going fully custom.

The recommended approach should result in an initiative to design, print, and validate the channel segments, starting with the U-channel cross-section and clip attachment, then adding features (wire routing, LED retention, diffuser slot, assembly interface) iteratively.

## Decision

**Status: Open**

Pending decision to proceed with Option B. When decided, this should spawn an initiative at `docs/initiatives/interior-channel/` covering the design, printing, and validation of the 3D-printed channel segments.

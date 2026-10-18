# KiCad Extraction Audit

> Topic 3 of 6, Stage A of the v7 retry. This is an audit, not a build. No scripts were changed, and no project script was re-run. Every number below came from reading the committed output files, or from short read-only probes (kiutils + shapely in a heredoc) against the committed `motion-play-main.kicad_pcb` at `c2acffc` (v7 as fabricated, unchanged since 2026-04-13).

## TL;DR

- **Your instinct is right, and the problem is bigger than legibility.** The routing data is all on disk, but nothing turns it into a route, a neighbourhood, or a reference plane. Some of the numbers the auditor produced are also **wrong in ways that matter** (see §3).
- **Where does SDA route?** No output answers this. `pcb-routing-context.json` holds SDA as 25 unordered segments. I rebuilt the route with about 40 lines of throwaway code: four branches from U3 pin 37, including **a 26 mm B.Cu run across the middle of the board, under the battery holder, out to U7 (INA219) and U5 (BQ24195)**. A session given only the JSON will not do that rebuild reliably.
- **What's near SDA?** Only what you name in an audit spec, only on the same copper layer, and only as centreline distance. Anything you don't think to name never shows up, and neither does anything on the other side of the board.
- **Planes, cutouts, return paths:** **completely invisible.** No extractor reads `zone`. The board has 8 zones (In1 solid GND, In2 split +5V/+3.3V, four small F.Cu pours, and an antenna keepout). In under a minute I found **about 6.8 mm of SDA on B.Cu with no In2 copper under it at all**, which no tool could have reported.
- **v6 vs v7:** no diff capability exists. Topic 2 did the diff by hand with `kicad-cli`.
- **Stale and misleading files sit next to the good ones:** `pcb-layout-context.json` predates the final layout (7 parts moved, including U7 on the I²C bus). `drc-report.json` is from before routing (137 unconnected). Nothing in either file warns that it is stale.
- **Recommendation:** yes, **one** implementation initiative in three phases: fix and extend the extractor (zones, stackup, true pad geometry, topology, freshness); add net-centric and route-narrative output, with rendered images; then add diff mode. Plus one small cleanup task.

---

## 1. Script inventory

| Script | Reads | Writes | Built for | Last changed / last output |
|---|---|---|---|---|
| `tools/pcb-context/extract.py` | `.kicad_pcb` (kiutils), optional `circuit-context.json` | `pcb-layout-context.json` | AI-guided **placement** sessions (`pcb-layout-context` initiative). Routing and zones were explicitly out of scope. | Code 2026-03-15. Output extracted **2026-04-07**, committed 04-13 without re-extracting. |
| `tools/pcb-context/place_power.py` | layout context with `--pads`, `tools/schematic-gen/spec.json` | **writes `.kicad_pcb`**, `placement-report.json` | One-off auto-placement of about 44 power-section parts (`pcb-auto-placement`). | 2026-03-15 / report 03-16. Superseded: the board was re-placed by hand afterwards. |
| `tools/pcb-context/routing_extract.py` | `.kicad_pcb` (kiutils) | `pcb-routing-context.json` (253 KB) | Phase 16 of the v7 I²C debug (`pcb-routing-audit-tool`). | 2026-04-25 / output 04-25 (current with the PCB). |
| `tools/pcb-context/routing_audit.py` | routing context + audit spec | `<spec>.audit.json` / `.audit.md` | Same. Answers "min clearance from net X to named things". | 2026-04-25 / one spec ever written (`v7-main-i2c.json`). |
| `tools/schematic-context/extract.py` | `.kicad_sch` via `kicad-cli` XML netlist + kiutils | `circuit-context.json` | AI reasoning about the circuit (`schematic-context`). | 2026-03-09 / main output 2026-04-10; sensor boards 03-26. |
| `tools/schematic-context/annotate.py` | `.kicad_sch` | **writes** `ai_*` properties into `.kicad_sch` | Interactive annotation sessions. | 2026-03-09. |
| `tools/schematic-context/show.py` | `.kicad_sch` | stdout | Annotation coverage checks. | 2026-03-09. |
| `tools/schematic-modify/*.py` | `.kicad_sch` | **writes** `.kicad_sch` | One-off ESP32 integration edits (March 2026). `modify.py` is a reusable helper library; the two `esp32_integration*.py` files are single-use. | 2026-03-18. |
| `tools/schematic-gen/*.py` | spec JSON | **writes** a new `.kicad_sch` | One-off generation of the power and ESP32 sheets, plus a PoC. | 2026-03-18. |

**Scope decision:** `schematic-modify` and `schematic-gen` are authoring tools, not extractors, and they have nothing to do with making layout legible. I checked their purpose and did not audit them further. They need no action for the v7 retry. If anything, mark the `esp32_integration*`, `generate_*_sheet` and `poc_generate` scripts as historical in `tools/CONTEXT.md`.

**Surprises found on the way:**
- The `routing-verification` initiative (a pre-order check of routing against design intent, including zones and Kelvin sense) **was never executed: 0 of 16 tasks done.** v7 was ordered without it.
- `tools/pcb-context/README.md` documents `routing_audit.py` with a positional spec argument and `--output-json/--output-md`. The script actually takes `--spec`, `--out-json` and `--out-md`. The documented commands fail.
- `tools/CONTEXT.md` forbids reading `.kicad_pcb` directly, but no tool exposes zones, stackup or board shape. Following that rule means not being able to see the planes at all.

---

## 2. Output quality, per file

### `circuit-context.json` (schematic) — **good; keep**
- **Answers:** what every part is, its value, footprint and LCSC number, which net each pin is on, which sheet it lives on, and sheet interfaces. 89 of 93 components carry `function/role/block` annotations, which is real value.
- **Can't answer:** "who is on net X" without scanning every component (nets carry no member list). There's no net semantics: **0 of 53** nets are annotated and `blocks` is empty, despite the merge machinery built for both. One sheet pin resolves to an empty net (`led_controller` `DATA_IN` → `""`), which is either a resolver bug or a real dangling pin and is worth a look.
- **Signal-to-noise:** fine. About 84 KB, readable.
- **Cross-check:** topic 2 reproduced component and net data independently with `kicad-cli sch export netlist`. I saw nothing suggesting `circuit-context.json` is wrong. It's just thin on nets.

### `pcb-layout-context.json` — **stale and lossy; replace**
- **Answers:** rough placement: ref, x, y, rotation, side, and the AABB width/height of each body.
- **Wrong today:** extracted on 04-07, while the PCB changed until 04-13. **7 parts are at the wrong position**, including **U7 (INA219, on the I²C bus) off by about 4.9 mm**, R44 (the shunt) off by 4.5 mm, and TP1/TP4 off by about 8 mm. No field lets a reader detect this: there is a timestamp but no source hash.
- **Lossy even when fresh:** the bbox is width/height only, with no centre and no polygon, so a part whose origin isn't its centre is mislocated. The outline is a bbox of the first Edge.Cuts item. `board_utilization_pct: 113.3` is nonsense (it adds BT1 on the back to the front-side area). It has no pads (the `--pads` run was never committed), no nets and no copper.
- **Signal-to-noise:** compact (17 KB), but the most compact file is also the least true.
- **Prior harm:** the postmortem (§4.8) found that Phases 4–15 made routing claims from this placement-only file. Its existence invites exactly that.

### `pcb-routing-context.json` — **correct raw data, unusable as context; keep as a cache only**
- **Contents:** all 855 segments and 224 vias per net, with width, layer and length; every pad in world coordinates with its net; per-layer pad bboxes. It's current, and its lengths were spot-checked in KiCad (±0.05 mm).
- **Answers (with code):** per-net length, per-layer length, via count, which pads a net touches.
- **Can't answer, even with code:**
  - Planes and pours. **No zones at all.** The B.Cu GND pour removed in v7 (topic 2, CL-20) can't be seen in either version.
  - Stackup: which plane each signal layer references, and dielectric thickness.
  - Component bodies. The bbox is **pads only**, so BT1's "footprint" on B.Cu is two 7.5 mm pads at y 125–132 rather than the 88 × 22 mm holder. "I²C runs under the battery holder" (topic 2, CL-21) **can't be computed from this file**.
  - The real board outline, keepouts, silkscreen, and courtyards.
- **Can't answer without writing code:** route order, branches, stubs, which segment joins which pad, what's next to the route.
- **Signal-to-noise:** 253 KB (very roughly 80k tokens). Too big to read whole, and segments come in file order, not route order. A session either greps it, which gives disconnected fragments, or writes code, which is what a tool should already do.
- **Correctness bugs** (they matter as soon as anyone computes on this data):
  1. **Pad sizes are never rotated.** R44 is at −90°. Its pad is stored as 1.225 × 3.35 in footprint-local axes but used as if in world axes. That makes every per-layer bbox wrong for rotated parts, and most parts are rotated.
  2. **`effective_radius` = half the long side.** That is a bounding circle, which inflates long pads badly. Measured against SDA: R44 pad 2 reads **0.0 mm** with the circle and **0.85 mm** edge-to-edge with the real rotated rectangle. U4 pad 22 (SCL) reads 0.0 with the circle and 0.32 mm in reality. Every pad-proximity number is unreliable below about 1 mm.
  3. **`F&B.Cu` pads aren't expanded.** Only `*.Cu` is handled, so BT1's mounting pad produces a fake layer key, `"F&B.Cu"`, that never matches any trace.

### `routing_audit.py` output (`v7-main-i2c.audit.md`) — **directionally useful, numerically misleading**
- **Answers:** the minimum distance from the named target nets to things named in the spec, plus an SDA-vs-SCL asymmetry table.
- **Problems, roughly by impact:**
  1. **Net-to-net distances are centreline to centreline, and pad distances are centreline to the circle edge.** Trace widths are ignored. The real copper gap from SCL to BOOST_SW (a 1.5 mm trace) is **0.94 mm, not the reported 1.8 mm**. SDA to BOOST_SW is 1.79 mm, not 2.7. Protected_VBUS is 1.21 / 1.69, not 1.7 / 2.2. **Every clearance reported in Phase 16 is too large, by roughly half the combined trace widths.**
  2. **Zones are ignored.** BOOST_SW is partly a pour, and so are +5V and +3.3V on F.Cu. In this case the BOOST_SW pour is 6+ mm from I²C, so no conclusion flips. The tool can't know that.
  3. **Strictly same-layer.** A B.Cu trace running under a front-side switching part, or a front-side trace over a back-side BT1, reports "no shared Cu layer". For EMI questions, plan-view distance plus layer separation is what matters.
  4. **Vias and the net's own pads are excluded** from the net's geometry. So are other nets' pads, unless named one by one in the spec.
  5. **"0.0 mm to U5" is reported without context.** SDA *connects to* U5. The tool should say "connected (pin 6)" and then measure distance to U5's *other* pins.
  6. **Minimum distance is not coupling.** Coupling scales roughly with parallel run length over spacing. One 1.8 mm close point and 20 mm of parallel run at 1.8 mm look identical in this report.
  7. **Spec-driven blindness:** it only reports what you already suspected. It never says "the thing you didn't think of is 0.3 mm away".
- **On Phase 16's conclusion:** the *sign* of the asymmetry survives. SCL is closer than SDA under both the centreline and the edge-to-edge metric, so "if routing-EMI mattered, SCL should fail" still holds as an argument. The absolute clearances in the debug log are wrong and shouldn't be quoted again. (I'm not re-arguing the bug here. That belongs to topics 4–6 and Stage B.)

### `placement-report.json`, `drc-report.json` — **historical; archive or regenerate**
- `placement-report.json` (03-16) describes a placement run whose result was later re-placed by hand. It's of no use to a debug session.
- `drc-report.json` (03-12) is from before routing: 137 unconnected items and 84 violations. Topic 2's fresh DRC on v7 found 0 unconnected and 6 minor violations. **Anyone reading the committed file comes away believing the opposite of the truth.**

---

## 3. Acid test: "Where does SDA between the ESP32 and the TCA9548A route, and what's near it?"

**From the outputs alone, as designed:** a session can say SDA is 72.9 mm long, about half on F.Cu and half on B.Cu, with 3 vias, and give its distances to L1, L2, U5, U6 and five power nets. It can't say where SDA goes, what it passes, or what it references. **Fail.**

**What it took to answer** (throwaway probes; this is what a tool should hand over):

```
/I2C_SDA — 6 pads, 3 vias, 4 branches from U3.37 (ESP32 GPIO, the driver)
  ├─ F.Cu → U4.23 (TCA9548A) → R28.1 (2.2k pull-up)          19.4 mm from U3, all F.Cu
  ├─ F.Cu → TPIO43 (test pad)                                  5.9 mm from U3 (shares ~3.5 mm with the U4 branch)
  └─ F.Cu 1.5 mm → via (138.4,112.65) → B.Cu 9.2 mm diag → B.Cu 17.1 mm along y=119.17
       → via (114.77,119.17) — branch point
           ├─ F.Cu 3.8 mm → U7.6 (INA219)                       31.7 mm from U3
           └─ B.Cu 10.6 mm (incl. 6.0 mm along y=122.17) → via (105.37,122.19)
                → F.Cu 9.2 mm → U5.6 (BQ24195)                  47.7 mm from U3 (37.0 mm of it on B.Cu)
```

What's near it, unprompted and measured edge-to-edge on rotated pad rectangles:
- **Passes directly under C53 (100 nF, front side, +3.3V/GND)** on B.Cu, and within 0.75 mm of U3's GND/LED_DATA pads, in plan view.
- **Runs alongside SCL at a 0.20 mm copper gap** (0.45 mm centreline): 27.8 mm of SDA on F.Cu and 19.5 mm on B.Cu lie within 1 mm of SCL copper. That's expected for a bus, but it means "SCL as aggressor or victim" deserves a row of its own.
- **Within 0.5 mm of `/CHRG_INT`** on F.Cu and 0.84 mm on B.Cu, a signal that toggles at BQ events.
- **Reference plane:** In2 sits directly above B.Cu. SDA's B.Cu runs sit over In2 **+3.3V** for about 29 mm, and about **6.8 mm sit over no In2 copper at all**, mostly the 6.0 mm run from 105.4 to 111.4 along y = 122.17. SCL has about 7.4 mm unreferenced in the same area. Both figures exclude the ~0.6 mm via antipads. The return path for that stretch has to go up to In1 GND, across a thicker dielectric.
- **29.7 mm of SDA's B.Cu** (the runs at y = 119–122) lies inside BT1's body outline (the holder spans y ≈ 117.8–139.4) but **outside its pad bbox**. The routing context can't show this. It is exactly topic 2's CL-21.

That one question exercised almost every gap: topology, unnamed neighbours, cross-layer proximity, zones and reference planes, component bodies, and pad geometry. **The data exists in the `.kicad_pcb`. The extractors just don't keep the parts that matter for EMI and return-path reasoning.**

---

## 4. The four evaluation questions

| Question | Verdict | Why |
|---|---|---|
| Where does a trace actually route? | **No** | Raw segments are unordered, with no chaining, no pad-to-via-to-pad sequence and no branch detection. It's possible with code, but no output does it. |
| Which components does a trace pass near? | **Only if pre-named, same layer, approximate** | Spec-driven. Bodies are pad-only, pads are bounding circles, and clearances are centreline. Opposite-side parts never show up. |
| v6 vs v7 diff? | **No** | No diff mode. v6 outputs were never generated. The extractors could run on `git archive fd632ef`, but you'd be diffing 253 KB of coordinates for a board that was **completely re-placed** (CL-19), which is meaningless. The diff has to be *relational* (see §5.5). |
| Ground cutouts, star points, high-current return paths? | **No** | Zones are not extracted. There's no stackup and no via-stitching analysis. Pour fills are stored *fractured* in KiCad (holes joined to the outer edge by thin slits), so a naive reader sees the In1 GND fill as a single polygon with 0 holes even though every via antipad is a hole. Star points and return paths need net topology plus zones, and neither exists. |

---

## 5. Recommendations

### 5.1 Keep as-is
- `tools/schematic-context/` (`extract`, `annotate`, `show`). It does its job. Optionally add a `members` list per net, which is cheap.
- The **audit-spec idea**: declarative, reusable, and kept in the repo.
- `routing_extract.py`'s parsing core (segments, vias, arcs, world transform). It's spot-checked and correct for positions.

### 5.2 Augment
- **routing_extract → a full board model** (one extractor and one internal model; every report is derived from it):
  - **Zones:** net, layer, priority, outline polygon, and filled polygons. De-fracture the fills into proper shapely polygons with holes. Mark keepouts.
  - **Stackup** from the board `setup` block: layer order, dielectric thicknesses, and which plane each signal layer is adjacent to.
  - **True pad polygons:** rotated rect, roundrect and oval, with `F&B.Cu` and `*.Cu` expanded.
  - **Component bodies:** courtyard or fab polygon per side, with a fallback to the footprint-name dims logic that already exists in `extract.py`.
  - **Board outline as a polygon.**
  - **Net topology:** chain segments and vias into a graph whose nodes are pads, vias and junctions; emit branches and stubs.
  - **Freshness:** a source-file SHA-256 and git ref in `meta`, plus a `--check` mode that exits non-zero if the output doesn't match the `.kicad_pcb`.
- **routing_audit:**
  - Use edge-to-edge copper clearance, with buffered traces, and include pads, vias and zones in every net's geometry.
  - Report "connected via pin N" instead of 0.0.
  - Add plan-view (cross-layer) proximity with layer separation reported.
  - Add a **coupled-length** metric: mm of parallel run within X mm, per neighbour.
  - Add an **unprompted neighbour scan:** everything within X mm, ranked, with the spec only adding emphasis.
  - Fix the README.

### 5.3 Replace or retire
- **`pcb-layout-context.json`:** replace it with a placement view generated from the same board model, so it can't drift from routing. Delete the stale committed copy now (or regenerate it, but the replacement is better).
- **`drc-report.json`:** stop committing a hand-run snapshot. Generate it with `kicad-cli pcb drc` as part of the extraction run, stamped with the same source hash.
- **`placement-report.json` and `place_power.py`:** archive both as historical (`tools/pcb-context/archive/` or a note in `tools/CONTEXT.md`). Don't delete the script, since it's a reasonable reference for a future placer.

### 5.4 New extractors and reports
1. **Net-centric report** (see sketch below). Markdown first, JSON sidecar second. The route narrative from §3 belongs at the top of each critical net's section.
2. **Plane and region report:** per layer, which nets own which copper, their area and bbox, split lines between same-layer zones, and voids (areas inside the outline with no copper on a plane layer). For each signal segment, the plane above and below it and the **mm with no reference**. Via-stitching density per region for GND.
3. **Rendered images**, one PNG per critical net and one per plane layer: the board outline, footprints faded, the target net highlighted by layer, labelled pads and vias, and neighbours within X mm in a contrasting colour. **A multimodal session reads one picture faster and more reliably than 25 coordinate rows.** It's cheap with matplotlib from the board model. `kicad-cli pcb export svg` is an alternative for plane layers.
4. **Diff mode** (see sketch below).

#### Sketch: net-centric output

One row per net. In Markdown, critical nets get a full block and everything else gets a summary table line.

```jsonc
{
  "net": "/I2C_SDA",
  "class": "signal",              // inferred: signal | power | ground | switching (from width, zones, schematic role)
  "endpoints": [                  // from pads; the driver is marked if inferable from schematic pin type
    {"ref": "U3", "pin": "37", "part": "ESP32-S3-WROOM-1", "role": "driver"},
    {"ref": "U4", "pin": "23", "part": "TCA9548APWR"},
    {"ref": "U7", "pin": "6",  "part": "INA219AIDCNR"},
    {"ref": "U5", "pin": "6",  "part": "BQ24195RGER"},
    {"ref": "R28","pin": "1",  "part": "2.2k pull-up"},
    {"ref": "TPIO43","pin":"1","part": "TestPoint"}
  ],
  "length_mm": 72.9, "length_by_layer": {"F.Cu": 35.9, "B.Cu": 37.0},
  "width_mm": [0.25],
  "vias": 3,
  "topology": "U3.37 ─┬─F 19.4─ U4.23 ─ R28.1 │ ├─F 5.9─ TPIO43 │ └─F 1.5 ▸via B 26.3 ▸via(branch) ─┬─F 3.8─ U7.6 └─B 10.6 ▸via F 9.2─ U5.6",
  "longest_branch_from_driver_mm": 47.7,
  "reference_planes": [           // per signal-layer run, from stackup + zone fills
    {"layer": "B.Cu", "adjacent": "In2.Cu", "over": {"+3.3V": 28.9, "<none>": 6.8}},
    {"layer": "F.Cu", "adjacent": "In1.Cu", "over": {"GND": 35.9}}
  ],
  "passes_under_or_over": [       // opposite-side bodies in plan view
    {"ref": "BT1", "side": "back", "overlap_mm": 29.7},
    {"ref": "C53", "side": "front", "overlap_mm": "…"}
  ],
  "neighbours": [                 // unprompted, ranked by coupled length / spacing
    {"net": "/I2C_SCL",  "class": "signal",   "min_gap_mm": 0.20, "parallel_mm_within_1mm": 47.3, "layers": ["F.Cu","B.Cu"]},
    {"net": "/CHRG_INT", "class": "signal",   "min_gap_mm": 0.23, "parallel_mm_within_1mm": "…"},
    {"net": "/Power Management/Protected_VBUS", "class": "power", "min_gap_mm": 1.69, "parallel_mm_within_2mm": "…"}
  ],
  "nearby_high_current": [...],   // nets classed power/ground with width ≥ 0.5 mm or a zone, within 3 mm (any layer, plan view)
  "nearby_high_dvdt":    [...]    // switching nodes (BQ_SW, BOOST_SW, LED_DATA, USB, SW pads), within 5 mm plan view
}
```

The SDA values are the ones measured in §3. `…` marks values I didn't compute, which the tool would fill in.

#### Sketch: diff mode

`board_diff.py <refA> <refB> [--pcb path]`. It `git archive`s each ref, runs the extractor on both, then compares **relations, not coordinates**, because v6 → v7 moved every part:

- **Per component** (matched by ref, with a fallback on footprint + pin-net signature): added, removed, value/footprint/LCSC changed, side flipped, rotation changed. Position change is reported **relative to its connected neighbours** (for example "U7 is now N mm from U5, was M mm"), not in absolute coordinates.
- **Per net** (matched by name, with a fallback on pin-set): endpoint set Δ; length Δ; layer-mix Δ; via count Δ; topology Δ (branch added, stub length change); **reference-plane Δ** ("SDA B.Cu over In2 +3.3V 0 → 29 mm; unreferenced 0 → 6.6 mm"); **neighbour Δ** (new or removed aggressors in the top N, and passes under/over BT1 new); width Δ.
- **Per copper region:** zones added or removed (net, layer, priority); per layer, the fill area per net; the XOR of each plane layer's fill, reported as changed regions with bbox, area and which nets moved in or out ("B.Cu GND fill <area> mm² → 0"; "In2 +3.3V/+5V split moved: new boundary crosses I²C at …").
- **Board-level:** outline, stackup, DRC counts (from `kicad-cli`) and keepouts.
- **Output:** Markdown summary ordered by likely relevance to signal integrity (reference-plane and aggressor changes on critical nets first), plus JSON, plus side-by-side PNGs for each critical net.

Topic 2 did most of the component and net half of this by hand with `kicad-cli` netlist and pos exports. Diff mode should reuse that path for connectivity and add the copper and relational half that topic 2 couldn't do automatically.

---

## 6. Does this spawn an implementation initiative?

**Yes: one initiative, three phases.** Each phase is usable on its own for the v7 retry.

1. **Board model + correctness** (about 1–2 sessions): zones with de-fractured fills, stackup, true pad polygons, body polygons, outline, net topology graph, freshness hash and `--check`, `kicad-cli` DRC in the run. Re-validate against KiCad for 3–5 spot-checks, including one zone and one rotated pad. Fix the auditor's clearance math, or fold the auditor into phase 2.
2. **Net-centric + plane reports + images** (about 1–2 sessions): the net-centric Markdown/JSON from the sketch, the route narrative, the plane/region report, and per-net PNGs. Acceptance test: the §3 SDA question answered from the output alone, matching the numbers in this document.
3. **Diff mode** (about 1–2 sessions): `board_diff.py` over git refs; acceptance test: reproduces topic 2's CL-19/20/21 findings automatically, plus the reference-plane change for I²C.

**Plus a small cleanup**, which can be phase 0 or a gardener task: delete or regenerate the stale `pcb-layout-context.json` and `drc-report.json`, archive `placement-report.json`, fix the `routing_audit` README, mark the schematic-gen/modify one-offs as historical in `tools/CONTEXT.md`, and update `tools/CONTEXT.md` so it points at the board model.

**Constraint worth revisiting in planning:** the `pcb-routing-audit-tool` brief ruled out pcbnew's Python API. That stays sensible for parsing, but `kicad-cli` is already a dependency and should be used freely: DRC, gerber/SVG export for images, and refilling zones if fills are ever stale. Note too that kiutils reads whatever zone fills were last saved. If KiCad didn't refill before saving, the fills are stale. The extractor should warn when a zone has no fill.

**One initiative, not several,** because all three phases share one board model, and splitting them recreates the drift between `layout-context` and `routing-context` that this audit found. Your call on whether to launch it before Stage B synthesis or let topic 6 / decisioning sequence it.

### 6.1 Input for the Planner

This section is not a PLAN. It lists what the Planner needs to settle when writing BRIEF, PLAN and TASKS.

**Goals and non-goals.**
- In: everything in §5.2–5.4.
- Out: impedance and SI simulation, EM field modelling, current density and thermal analysis, any write-back to `.kicad_pcb`, auto-fixing.
- The extractor must run on all three boards (main, sensor-rigid, sensor-flex). Validation is required on main only.

**Suggested module layout** (all in `tools/pcb-context/`):

| Module | Job |
|---|---|
| `board_model.py` | Parse once into one internal model; JSON cache with source hash |
| `net_report.py` | Net-centric and route-narrative output |
| `plane_report.py` | Planes, splits, voids, per-segment reference plane, stitching density |
| `render.py` | Per-net and per-plane PNGs |
| `board_diff.py` | Diff mode over git refs |

`routing_audit.py` becomes a thin consumer of the model. `routing_extract.py` stays only as a compatibility shim, or is retired.

**Definitions to fix in the PLAN** (as a per-board config file, not hard-coded):
- *High-current:* the net has a zone, any segment ≥ 0.5 mm wide, or schematic role power/ground.
- *High dv/dt:* an explicit list per board. Seed for main: `BQ_SW`, `BOOST_SW`, the U5 SW pads 19/20, `LED_DATA`, `USB_DP`/`USB_DN`, `CHRG_INT`.
- *Neighbour radii:* 1 mm for signals, 3 mm for high-current, 5 mm for high dv/dt, all measured in plan view across layers.
- *Clearance:* always copper edge to copper edge.

**Validation fixtures.** The phase 1–2 output must reproduce these values from this audit, each also spot-checked in KiCad:

| Check | Expected value |
|---|---|
| SDA length | 72.9 mm (F 35.9 / B 37.0), 3 vias |
| SDA branch lengths from U3 | 19.4 / 5.9 / 31.7 / 47.7 mm |
| SCL to BOOST_SW gap | 0.94 mm, edge to edge |
| SDA to R44 pad 2 gap | 0.85 mm |
| SDA to SCL gap | 0.20 mm |
| SDA over In2 +3.3V / over nothing | ~28.9 mm / ~6.8 mm |
| SDA B.Cu inside BT1 body | 29.7 mm |
| Zones on the board | 8, per the §4 inventory |

For phase 3, the diff must surface topic 2's CL-19, CL-20 and CL-21 between `fd632ef` (v6) and `c2acffc` (v7).

**Dependencies.**
- Python 3.7 is the current pyenv constraint. Check that shapely 2.0.x and matplotlib wheels still install on it, or bump Python as an explicit task.
- `kicad-cli` 9.0.4 is already required by `schematic-context`.

**Decisions for you (the user)**, to answer at Planner kickoff:
1. Commit generated outputs, stamped with a source hash, or gitignore them and generate on demand?
2. Delete `pcb-layout-context.json` and `drc-report.json` now, or regenerate them until phase 1 lands?
3. Is the pcbnew Python API allowed as a fallback (for example, for zone refill), or kiutils + `kicad-cli` only?
4. Launch now, or wait for the Stage B decisioning?

**Rough size:** 3–6 sessions in total, plus the cleanup task.

---

## Observations for other topics

- **Topic 4 / Stage B:** Phase 16's absolute clearances are overstated (centreline). The SDA/SCL asymmetry direction holds. Don't quote the 1.7–2.7 mm figures again; the edge-to-edge values are 0.94–1.79 mm.
- **Topic 4 / Stage B:** SDA (~6.8 mm) and SCL (~7.4 mm) each have B.Cu runs with no In2 copper beneath, near x 105–111, y 122–123, and the rest of their B.Cu runs reference In2 **+3.3V**, not GND. That's raw geometry, not a hypothesis. Whether it matters is Stage B's question.
- **Topic 6 (context strategy):** route narratives and per-net images are the right unit of layout context for a session. Raw coordinate JSON isn't. Every generated context file needs a source hash, because this audit found two stale committed outputs that nothing flagged.
- **Topic 6:** the `tools/CONTEXT.md` "never read `.kicad_pcb`" rule is currently a blindfold for zones and stackup. Until phase 1 lands, allow targeted read-only kiutils probes (as used here) and say so explicitly.
- `circuit-context.json`: `led_controller` sheet pin `DATA_IN` resolves to an empty net. Check whether this is a resolver bug or a real dangling hierarchical pin.

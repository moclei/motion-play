---
title: Making the v8 schematic readable, and keeping scripted edits readable
date: 2026-11-04
source: hardware/pcb-main-v8/kicad/*.kicad_sch @ f1eaa2e (v7 comparison: hardware/pcb-main/kicad @ f1eaa2e and c2acffc)
tools: KiCad / kicad-cli 9.0.4, Python 3.7.3, kiutils 1.4.8
status: research only; no project file changed
---

# Making the v8 schematic readable

## Summary

**What went wrong.** Most of the clutter is a bug, not a layout problem. Our scripts edit
schematics with kiutils 1.4.8, the last release (February 2024, written for KiCad 7). KiCad 8 and 9
mark a hidden field with `(hide yes)`. kiutils does not recognise that, so when a script loads a
sheet KiCad saved and writes it back, **every hidden field becomes visible**: Footprint, Datasheet,
Description, LCSC Part, the `ai_*` notes and a dozen vendor fields. A round trip of the v7 sheets
from `c2acffc` reproduces it exactly: 496 of 496 `(hide yes)` flags are lost on the power sheet,
99 of 99 on the MCU sheet and 49 of 49 on the TCA sheet. Every one of the 536 extra visible fields
on v8 belongs to a part that came from v7. 505 were hidden in v7 and the round trip unhid them. The
other 31 were already visible in v7, including 24 `ai_*` fields piled at the sheet origin on the TCA
sheet. None of the fields Phases 8–11 added are affected, because our helpers write the older
`hide` form that kiutils keeps.

**The quick fix works.** In a scratch copy, hiding every symbol field except Reference and Value
(one kiutils pass, about 760 fields) gave a **byte-identical netlist** and brought the sheets close
to v7 levels:

- No visible text is left off the sheet. Before the fix there were 216 items, all `ai_*` fields.
- Text overlaps fall from 1,616 pairs to 111.
- The amount of plotted text roughly halves.

You can do the same in KiCad in about two minutes per project (exact clicks below).

**What is left needs layout work.** After hiding, 111 pairs of overlapping text remain. Nearly all
are on the power sheet (60) and the TCA sheet (40), where generated parts sit in tight rows: value
text collides with net labels, and vertical labels cross test-point references. KiCad's Autoplace
Fields (`O`) tidies reference and value text. Nothing in KiCad moves net labels, and no reliable
tool does it for us, so the rows need either a better placement rule in our scripts or a pass by
hand.

**Keep it from coming back.** Two changes matter:

1. Teach our kiutils loader to read `(hide yes)`. A 40-line shim, tested here, preserves visibility
   exactly on a round trip. Without it, the next script run after anyone saves in KiCad unhides
   everything again.
2. Add a readability check to every `--check`: no visible fields other than Reference and Value,
   no text off the sheet, and no new overlapping text.

**Not available yet.** KiCad 9 and 10 cannot be scripted through the official API for schematics;
that arrives in KiCad 11. kicad-cli has no autoplace or cleanup command. So the work splits into a
safe script pass, a few GUI clicks, and some judgment calls.

**Note:** `hardware/pcb-main-v8/kicad/~motion-play-main-v8.kicad_sch.lck` exists, so KiCad has (or
had) the project open. Close it before any script edits the files, or KiCad will overwrite the
script's changes when it saves.

---

## 1. Diagnosis

### 1.1 Method

- `scratchpad/probe.py` parses each sheet as raw s-expressions, independently of kiutils. It
  classifies every placed-symbol field as hidden or visible. A field counts as hidden if it has
  `hide` or `(hide yes)` in its effects, has `(hide yes)` on the property itself, or is empty or
  `~`. The probe also computes approximate text boxes (0.72 × height per character) and counts
  pairs of boxes overlapping by more than 25 % of the smaller box. Treat the overlap counts as
  indicators, not exact figures.
- `kicad-cli sch export svg` was run on v8, on v7 and on the fixed scratch copy. "Plotted strings"
  means the number of `<desc>` text items in each SVG, which counts what KiCad actually draws.
- Check that KiCad honours our form of hiding: the LCSC field `C7484` on IC1 is written with
  kiutils' bare `hide` and does not appear in the v8 LED SVG. So KiCad 9 honours the bare form, and
  the visible fields are exactly the ones that have no hide marker at all.
- All scratch files are in
  `/private/tmp/claude-501/-Users-marcocleirigh-Workspace-motion-play/4463d79b-1453-4083-8508-d40852c5e639/scratchpad/`.
  Subfolders: `svg7/`, `svg8/`, `svgfix/`, `png/`, `pngfix/`. Scripts: `probe.py`,
  `hide_fields.py`, `kiutils_k9_shim.py`. The scratchpad is temporary; the three scripts are
  committed beside this report in `prototypes/` (the SVG/PNG folders are not).

### 1.2 Per-sheet numbers (v8 @ f1eaa2e)

Column notes:

- **Extra visible fields** counts visible fields other than Reference and Value.
- **Overlap pairs** counts pairs of overlapping text boxes, over all visible text.
- **After hide** is the same count once only Reference, Value and labels remain.
- **v7** is the same sheet in v7.

| Sheet | Paper | Parts | Labels | Extra visible fields (by field) | Off-sheet text | Overlap pairs | After hide | Plotted strings v8 → after hide (v7) |
|---|---|---|---|---|---|---|---|---|
| Root `motion-play-main-v8` | A4 | 14 | 28 | 76 (Description 29, ai_* 31, Footprint 9, LCSC 7) | 19 | 170 | 4 | 568 → 343 (165) |
| MCU `esp32_s3` | A3 | 50 | 177 | 56 (ai_* 28, Footprint 14, LCSC 14) | 24 | 109 | 3 | 923 → 603 (389) |
| LED `led_controller` | A4 | 13 | 27 | 37 (ai_* 16, Description 9, LCSC 8, Footprint 4) | 16 | 158 | 4 | 256 → 151 (102) |
| Power `power_management` | A3 | 144 | 344 | 306 (ai_* 197, Footprint 55, LCSC 51, Description 2, Sim.Pins 1) | 157 | 724 | **60** | 2448 → 1312 (624) |
| TCA `tca9548A_subsystem` | A3 | 72 | 149 | 61 (ai_* 24 at sheet origin, Description 8, LCSC 10, Footprint 6, 13 SnapEDA/vendor fields on U4) | 0 | 455 | **40** | 814 → 624 (248) |

v7 for comparison (hand-drawn, KiCad-saved): extra visible fields are 0–5 per sheet, apart from the
TCA sheet's 24 origin `ai_*` fields and five Mouser and manufacturer fields on the LED sheet. Overlap
pairs are 0–3 per sheet, apart from the TCA origin pile. No sheet has a symbol off the page or two
symbol bodies overlapping, in v7 or v8.

**Where the extra fields came from** (each v8 part compared with the same reference in v7
`c2acffc`):

| Sheet | Hidden in v7, visible in v8 | Already visible in v7 | On new v8 parts |
|---|---|---|---|
| Power | 305 (ai_* 197, other 108) | 1 | 0 |
| MCU | 51 | 5 | 0 |
| LED | 37 | 0 | 0 |
| TCA | 36 | 25 (24 origin ai_* + PARTREV) | 0 |
| Root | 61, plus 15 on TP110–112 (renamed v7 TPIO43/44/16) | 0 | 0 |
| **Total** | **505** | **31** | **0** |

So the only cause of the visible fields is the kiutils round trip. `modify.add_component`,
`set_property` and `annotate.py` all write hidden fields correctly.

**Off-sheet text.** All 216 off-sheet items are `ai_*` fields. They sit 25 mm or more from their
symbol, mostly at negative coordinates left of the power, MCU and LED frames: the purple text bleeding
off the left edge of the power sheet. The cause is that `annotate.write_ai_properties`
(`tools/schematic-context/annotate.py:134`) creates the property with no position, so it lands at
(0, 0). After that it moves around with sheet edits. Hidden fields still have a position, and KiCad
uses it for the bounding box and for "zoom to fit".

**Overlaps that remain after hiding** (the layout work):

- **Power, 60 pairs.**
  - 18 in the upper right (around U8/C42/C43 and the new battery block F3/Q20/Q21), where value and
    reference text sit on the `BAT_FUSED` and `GND` labels.
  - The test-point rows (TP10–TP75), where vertical labels cross the references.
  - The PWR_FLAG row (#FLG05–08), where values sit on labels.
  - 6 identical labels stacked on the same spot.
  - The passive rows at 5–8 mm pitch, where text like "22uF 25V" runs into the next part.
- **TCA, 40 pairs.** The same pattern repeated per channel: 47 Ω (R80–R95) and 4.7 kΩ values
  sitting on the `CHn_xxx_CONN` and `+3.3V_BUS` labels at the end of the stub. The stub is 2.54 mm
  long and the value is placed 2.54 mm below the symbol origin, so they meet.
- **MCU, LED and root: 3–4 pairs each.** For example, R103/R104 values on the DBG labels, JP5 on
  LED_DATA, and two power-symbol values touching on the root sheet.

**Other things the round trip dropped** (`c2acffc` power sheet, kiutils load and save):

- `(exclude_from_sim yes)`: 91 → 0. Harmless here.
- `(fields_autoplaced yes)`: 3 → 0. KiCad then no longer re-autoplaces those fields when a part
  moves.
- `(pin_numbers (hide yes))` on 6 library symbols. Pin numbers "1"/"2" now show on those passives.
- `(pin_names (hide yes))` on 12 library symbols.
- `embedded_fonts`, `generator_version`, and 7 `uuid`s. All harmless.

---

## 2. Options, with evidence

### 2.1 KiCad 9.0.4 GUI (installed; KiCad 9 manual, docs.kicad.org/9.0, fetched 2026-11-04)

- **Bulk hide: Edit → Edit Text and Graphic Properties…** The manual says:

  > "Properties of text and graphics, including symbol fields, can be edited in bulk … (Edit → Edit
  > Text and Graphic Properties…)"

  It can set "visibility of fields and field names". Filters include "Filter fields by name"
  (wildcards allowed), parent reference, library ID, symbol type (power or non-power), net, and
  "Only include selected items". The checkboxes have a third "leave unchanged" state.

  This dialog is the GUI equivalent of our hide pass and works across the whole hierarchy. Tick the
  "Other symbol fields" scope, untick the others, and set Visible to unchecked. (The scope names are
  from the 9.0 dialog; check them on screen.)
- **Autoplace Fields: select the symbols, then press `O`** (also on the right-click menu). The
  manual says:

  > "Symbol fields can be automatically moved to an appropriate location with the Autoplace Fields
  > action … Field autoplacement is configurable in the Schematic Editor's Editing Options,
  > including a setting to always autoplace fields."

  It moves only fields (reference and value), never labels or wires. Run it on one sheet first and
  check with Undo ready.
- **Tools → Update Symbols from Library…** has "Update/reset field visibilities" and
  "Update/reset field positions". It would also restore the hidden pin numbers and names. **But**
  the manual says "the symbol's shape and pins are always updated to match the library version",
  and several of our symbols are embedded copies from JLC/SnapEDA downloads. Use it only on generic
  parts (`Device:R*`, `Device:C*`, `Connector:TestPoint`) using its library-ID filter, and only with
  a netlist comparison afterwards.
- **Symbol Fields Table (Tools → Edit Symbol Fields…).** Its show/hide controls choose the table's
  columns, not what is drawn on the sheet. It is useful for checking values, not for fixing
  clutter.
- **Align Elements to Grid** (right-click on a selection) and **Cleanup Sheet Pins**. Neither does
  anything for label overlap. There is no general "cleanup schematic" command, and nothing places
  labels automatically.

### 2.2 kicad-cli (9.0.4, checked locally)

`kicad-cli sch` offers only `erc` and `export`. There is no upgrade, autoplace or format command for
schematics, so autoplace cannot be run headless.

### 2.3 IPC API and kicad-python

The KiCad developer docs ("For Add-on Developers", fetched 2026-11-04) say: "KiCad 9 and 10 only
support IPC API plugins in the PCB Editor", "KiCad 11 adds support for plugins in the Schematic
Editor", and headless use through kicad-cli also came with KiCad 11. kicad-python 0.7.0's KiCad 10
additions are all board-related. KiCad 10.0.0 was released on 2026-03-20 (kicad.org blog). KiCad 11
is not out.

So we have no official programmatic access to the schematic editor on 9.0.4 or 10.x. Live, scripted
"autoplace and tidy" is not an option until KiCad 11.

### 2.4 Third-party libraries and MCP servers

- **kiutils 1.4.8** (PyPI): the last release was 2024-02-02. It does not parse `(hide yes)`
  (verified: `Effects.from_sexpr` only checks a bare `hide` atom). It is what caused the clutter.
- **kicad-sch-api 0.5.6** (circuit-synth, PyPI 2025-11-19): needs Python 3.10 or later, and its
  README claims KiCad 7/8 output. It has a field `visible` option and bounding boxes, but no
  autoplace or overlap tools. Switching to it would mean a Python upgrade and a port; that is not
  worth doing just for readability.
- **kicad-skip 0.2.5** (2024-02): KiCad 7+ and Python 3.8 or later. It is stale.
- **KiCAD-MCP-Server (Avinash1286), v2.7.1, first seen 2026-08-12** (Glama listing). It has
  `autoplace_schematic_fields` (moves reference and value clear of bodies and pin labels),
  `lint_schematic_cosmetic` (hides pin names, reorients labels; "netlist-safe raw-text edits"),
  `find_overlapping_elements`, `lint_offgrid`, `suggest_schematic_declutter` and
  `move_schematic_net_label`. It is the closest thing to the "tidy" tooling we want. But it is
  unvetted: I could not see its source repository from the listing, and its edits write the file
  directly. If we try it, run it on a scratch copy and gate it on our own netlist and ERC
  comparison. Its `find_overlapping_elements` is worth comparing against our probe.
- I found no maintained general-purpose library for schematic label placement. Published
  approaches, our probe and the MCP server all use the same simple method: compute text boxes, then
  move or orient text away from the pin and from neighbours.

---

## 3. Recommended plan

### 3.1 What a script can safely do (about 1–2 h of agent time; netlist-neutral, verifiable)

1. **Add the kiutils KiCad 8/9 shim** to `tools/schematic-modify/modify.py`. Import it before any
   `Schematic.from_file`, and do the same in `tools/schematic-context/annotate.py` and
   `extract.py`, which load with kiutils. The prototype is `scratchpad/kiutils_k9_shim.py`. It
   patches `Effects.from_sexpr`, `Property.from_sexpr` and `Symbol.from_sexpr` (for
   `pin_numbers`/`pin_names`). Tested on the three v7 `c2acffc` sheets: field visibility after a
   round trip matches the original exactly.

   Also give `SheetDoc` a guard that refuses to save while a `~*.kicad_sch.lck` file exists.
2. **Hide pass** (`scratchpad/hide_fields.py`): set `effects.hide = True` on every placed-symbol
   field except Reference and Value. Tested on a scratch copy of all five sheets:
   - The netlist is identical (only the `uri` paths to symbol libraries differ, which is the copy
     location).
   - 0 text left off the sheet.
   - Visible fields are Reference and Value only.
   - Overlaps go from 1,616 pairs to 111.
3. **Restore `pin_numbers`/`pin_names` hiding** on embedded library symbols. Copy the flags from
   v7 `c2acffc` for the same `lib_id`, or from the source library.
4. **Re-home the `ai_*` fields** to their symbol's position, so hidden text no longer stretches the
   sheet's bounding box or "zoom to fit".
5. **Verify** with what the v8 scripts already use: `v8_debug_sheet.py --check` (pin → net and
   jumper positions), ERC 0 errors, and a netlist compared with the pre-pass netlist. Then
   regenerate `circuit-context.json` (`extract.py --previous`), because the sheet hashes change.

Steps 2–4 are one new script, for example `tools/schematic-modify/tidy_fields.py --check/--apply`.
It should not be an edit to a v8 phase script.

**GUI alternative to steps 2–3** (about 2 minutes; do this instead if the owner wants to start
reviewing today):

1. In KiCad, open the root sheet.
2. Go to Edit → Edit Text and Graphic Properties….
3. Under Scope, tick only "Other symbol fields". Leave the filters off, or set "Filter items by
   parent symbol type" to non-power.
4. Set Visible to unchecked. Click Apply, then OK.
5. Save, then rerun ERC.

This covers every sheet in the hierarchy. Pin numbers stay as they are.

### 3.2 What KiCad's GUI does in a few clicks (about 10–15 min, by the owner)

On each sheet:

1. Press Cmd+A to select all, then press `O` (Autoplace Fields). Check the result before saving.
   Expect improvement on passives and test points; on hand-tuned v7 areas it may need an Undo.
2. In the same Edit Text and Graphic Properties dialog, optionally reset reference and value text
   to 1.27 mm. (They already are 1.27 mm everywhere.)
3. Optionally, set Preferences → Preferences… → Schematic Editor → Editing Options → automatically
   place symbol fields, so fields follow parts when they are moved.

### 3.3 What needs judgment (about 2–4 h in the GUI for power and TCA; the other sheets need minutes)

- **Power sheet** (144 parts on A3; v7 had 59 on A4). The generated parts are laid out in rows: the
  battery block, rows c/h/i/j/k/l, 40-odd rail and ground test points, and the PWR_FLAG row. They
  are readable as a parts bin, not as a circuit. Choices for a person:
  - Move the test points into one labelled "Test points" box, and the jumper rows next to the
    circuitry they break.
  - Decide whether the battery-protection block gets its own sheet. That would be a new
    hierarchical sheet, which means script work and a `--check` update.
  - Fix the 6 identical stacked labels: are they intentional duplicates or leftovers?
- **TCA sheet.** The 40 value-on-label overlaps repeat per channel. Either nudge one channel and
  copy the pattern to the others by hand, or fix the rule (3.4) and regenerate those parts' field
  positions with a script.
- **Root, MCU and LED.** Three or four nudges each, after autoplace.

### 3.4 Changes to our tools so new scripted parts come out readable (about half a day)

| Where | Change |
|---|---|
| `tools/schematic-modify/modify.py`, loader (`load_project`) | Import the KiCad 8/9 shim. Refuse to write while a KiCad lock file exists. |
| `modify.add_component` (lines 248–300) | Place Reference and Value at the library symbol's own field offsets, rotated with the symbol, the way KiCad does on placement. The hard-coded `(x+2.54, y-1.27)` and `(x, y+2.54)` put the value exactly where a 2.54 mm stub's label sits on vertical two-pin parts. Write `(fields_autoplaced yes)` so KiCad re-autoplaces them when the part moves. Keep Footprint, Datasheet and LCSC hidden (already done). |
| `modify._make_local_label` / `_label_angle` / `WIRE_STUB_LEN` (line 38) | For vertical stubs, prefer a horizontal label, justified away from the part, on a stub of at least 5.08 mm. Allow a per-call `stub_len`. Vertical labels in test-point rows are where most of the remaining power-sheet overlaps come from. |
| Row and grid placement in `v8_power_sheet.py`, `v8_bus_sheet.py` and `v8_debug_sheet.py` | Work out row pitch from the longest label or value in the row: about 0.75 × 1.27 mm per character, plus 2.54 mm. Do not use a fixed 5–8 mm. Snap every coordinate to the 1.27 mm grid. Keep new parts inside the frame, with a margin from the title block. |
| `tools/schematic-context/annotate.py:134` | Give new `ai_*` properties the symbol's position, and keep them hidden. When updating an existing `ai_*`, also set `hide`, so old visible ones are repaired on the next annotate run. |
| New `tools/schematic-modify/layout_check.py` (from `scratchpad/probe.py`) | Run it from every `v8_*.py --check`. Fail on: a visible field other than Reference/Value on a non-power symbol; any text or symbol outside the paper; new text-box overlaps above a baseline (stored per sheet, so the check ratchets down as overlaps are fixed); two identical labels at the same point. Print the worst areas by sheet grid zone, for example "C3", so a person can find them. |
| `tools/schematic-modify/CONTEXT.md` and `tools/CONTEXT.md` | Record the kiutils `(hide yes)` limitation and the rule: every kiutils write goes through the shim, and `layout_check.py` is part of `--check`. |

### 3.5 Effort and order

1. Shim and lock guard: 0.5 h. Do this first, because otherwise any KiCad save followed by a script
   run brings the clutter back.
2. `tidy_fields.py` and verification: 1–1.5 h. Alternatively, the GUI dialog: 2 min.
3. Autoplace in the GUI: 15 min.
4. `layout_check.py` and the `--check` hooks: 1.5 h.
5. Field and label placement rules in `modify.py`: 2 h, plus a re-run check on one sheet.
6. Hand layout of the power and TCA sheets: 2–4 h. This needs the owner's judgment on grouping.

Steps 1–3 make the schematic reviewable today (overlaps from 1,616 to about 111 by the probe's
count, and lower after autoplace). Steps 4–5 stop it regressing. Step 6 makes the power sheet read
like a circuit.

## Sources (fetched 2026-11-04)

- KiCad 9.0 Schematic Editor manual: https://docs.kicad.org/9.0/en/eeschema/eeschema.html. Covers
  bulk editing, Autoplace Fields, Update Symbols from Library and Align Elements to Grid.
- KiCad IPC API, For Add-on Developers: https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/for-addon-developers/
- kicad-python 0.7.0: https://pypi.org/project/kicad-python/0.7.0/
- KiCad 10.0.0 release (2026-03-20): https://www.kicad.org/blog/2026/03/Version-10.0.0-Released/
- kiutils release history (PyPI JSON API): https://pypi.org/pypi/kiutils/json
- kicad-sch-api: https://github.com/circuit-synth/kicad-sch-api and https://pypi.org/pypi/kicad-sch-api/json
- kicad-skip: https://pypi.org/pypi/kicad-skip/json
- KiCAD-MCP-Server (Avinash1286) tool listing: https://glama.ai/mcp/servers/Avinash1286/KiCAD-MCP-Server-THEAVI/tools/lint_schematic_cosmetic
- Local evidence: kicad-cli 9.0.4 SVG and netlist exports; a kiutils round trip of v7 `c2acffc`
  sheets; the scratch prototypes listed in 1.1.

# RELAY — research session — KiCad extraction audit (DRAFT)

> Informal research session, no agent role. Launch with default `claude`. See `docs/research/v7-retry/RESEARCHER.md` for conventions.

## Context

During prior v7 debugging, we built scripts to extract structured data from the KiCad schematic and PCB files so AI sessions could reason about layout without parsing KiCad formats. The user's instinct is these scripts worked well for understanding components but **failed to make trace routing, components-along-routes, and v6-to-v7 differences legible** to a session ingesting the output.

This session is topic 3 of 6 in Stage A. The job is **audit, not build**. The output is a recommendation document that may spawn an implementation initiative to improve or replace the scripts.

## Load these files

- `docs/research/v7-retry/RESEARCHER.md` — conventions
- Extraction scripts:
  - `tools/pcb-context/extract.py`
  - `tools/pcb-context/routing_extract.py`
  - `tools/pcb-context/routing_audit.py`
  - `tools/pcb-context/place_power.py`
  - `tools/schematic-context/extract.py`
  - `tools/schematic-context/show.py`
  - `tools/schematic-context/annotate.py`
  - `tools/schematic-modify/*.py` — review purpose; may be out of scope
  - `tools/schematic-gen/*.py` — review purpose; may be out of scope
- Recent outputs they produced:
  - `hardware/pcb-main/kicad/pcb-layout-context.json`
  - `hardware/pcb-main/kicad/pcb-routing-context.json`
  - `hardware/pcb-main/kicad/placement-report.json`
  - `hardware/pcb-main/kicad/drc-report.json`
- `docs/explorations/kicad-ai-annotation-proposal.md` — related prior thinking
- Any pcb-routing-audit or pcb-layout-context initiatives under `docs/initiatives/` — context for why these scripts exist

## Produces

**Artifact path:** `docs/research/v7-retry/kicad-extraction-audit.md`

Suggested structure:

1. **Script inventory** — one short section per script: what it reads, what it outputs, what it was built for, when it was last used.
2. **Output quality assessment** per script and per output file:
   - What questions can an AI session answer from this output?
   - What questions **can't** it answer that it should be able to?
   - Signal-to-noise: is the output readable, or does it bury useful info in noise?
3. **Specifically evaluate**:
   - Can a session understand **where a trace actually routes** from the output? (User's main concern.)
   - Can a session see **which components a trace passes near** (potential aggressors/victims)?
   - Can a session diff **v6 vs v7** using any of these outputs?
   - Can a session identify **ground plane cutouts, star-ground points, high-current return paths**?
4. **Recommendations**:
   - What to keep as-is
   - What to augment (and roughly how)
   - What to replace
   - New extractors needed (and what they'd produce)
   - **Explicitly include**: a sketch of a "net-centric" output — one row per net with endpoints, length, layers, vias, nearby high-current nets, nearby high-dv/dt aggressors
   - **Explicitly include**: a sketch of a "diff mode" — given two KiCad projects, output what changed per net, per component, per copper region
5. **Does this spawn an implementation initiative?** Give a direct answer: yes/no, and if yes, roughly scoped (one initiative or several?). The user decides whether to launch it.

## Scope

**In:**
- Reading each script's source and understanding what it does
- Running scripts if their current output isn't on disk and understanding needs it (confirm with user before running)
- Reviewing output JSON files
- Writing recommendations

**Out:**
- Writing new scripts (that's the follow-on initiative, if any)
- Modifying any existing scripts
- Running the scripts against modified schematics
- Analyzing what the data says about the v7 bug (not here)

## What was done before this relay

- `adopt-protocol` initiative merged
- Topic 2 (v6-v7 changelist) may be in progress or complete — if complete, read it; the changelist may flag specific extraction gaps
- Framework for v7 retry agreed; this is topic 3 of 6

## Your task

Produce `docs/research/v7-retry/kicad-extraction-audit.md` per the structure above.

**Expected first move:** quick skim of all the scripts to understand the inventory before deep-reading any one. Many may turn out to be lightly-used or superseded.

**Expected second move:** take one real v7 debugging question (e.g., "where does the SDA trace between the ESP32 and TCA9548A actually route and what's near it?") and try to answer it from the current output files. This is the acid test. If you can't answer it from the output, that's the gap.

Flag anything surprising. Don't try to be diplomatic about script quality — honesty here saves debug sessions later.

## Context-pressure behavior

At ~60% context: finish the current section, commit `WIP:`, write `docs/research/v7-retry/RELAY-kicad-extraction-audit-continue.md`, and stop.

## Open questions to surface

- Running scripts to generate fresh output — confirm with user before executing anything.
- If recommendations suggest a large new script set, confirm with the user whether to scope one initiative or multiple.
- The schematic-modify and schematic-gen tools may be artifacts from prior one-off work, not part of the ongoing toolkit. Confirm scope with the user before auditing them deeply.

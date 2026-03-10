# Schematic Context System

## Intent

Build tooling that produces an AI-optimized context file from KiCad schematics, so AI assistants can reason about circuit design, suggest changes, troubleshoot issues, and guide modifications — without reading the raw `.kicad_sch` files. This replaces the existing JSON netlist + YAML annotation system, which failed to gain adoption.

## Goals

- A Python extraction pipeline that combines `kicad-cli` netlist export with `kiutils` schematic parsing to produce a single `circuit-context.json` per PCB project
- The context file contains everything an AI needs: component inventory with pin-level detail, net connectivity with semantic annotations, functional block groupings, cross-sheet relationships, and design intent notes
- An interactive annotation workflow where the AI proposes context (functional roles, block groupings, signal types) and the human confirms or corrects
- Component-level annotations persist in the `.kicad_sch` file as `ai_` custom properties (survive schematic edits); net/block annotations persist in the context file and merge forward on re-extraction
- Updated `hardware/CONTEXT.md` and related docs to point AI sessions at the new context files instead of raw netlists or schematics

## Scope

What's in:
- Python scripts for extraction (kicad-cli + kiutils → circuit-context.json)
- Python script for writing `ai_` properties to schematic components via kiutils
- Context file schema design and implementation
- Merge logic for preserving net/block annotations across re-extractions
- Hierarchical schematic support (recursive sheet discovery, cross-sheet net resolution)
- First full annotation pass on the main PCB (`hardware/pcb-main/kicad/`)
- Documentation updates (hardware/CONTEXT.md, PROJECT.md references)
- Deprecation of existing netlist JSON + annotation YAML files

What's out:
- Annotation of sensor-rigid or sensor-flex schematics (future — same tools, separate pass)
- KiCad plugin development (we use CLI scripts, not KiCad plugins)
- Automated design rule checking or schematic modification
- Any changes to the schematics themselves (annotations are additive metadata only)

## Constraints

- Python 3.7+ (current system runs 3.7.3)
- `kiutils` 1.4.8 (validated via spike — parses KiCad 9 format v20250114)
- `kicad-cli` from KiCad 9.0.4 at `/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli`
- kiutils cannot resolve net connectivity — kicad-cli netlist export is required for pin names, pin types, and net assignments
- kiutils labels (net labels, global labels) do not support custom properties — net annotations must live in the context file, not the schematic
- `3v3_Power_Supply.kicad_sch` is an orphaned sub-sheet (not referenced from root) — excluded from this initiative

## Reference

- **Exploration:** `docs/explorations/kicad-ai-annotation-proposal.md` — original proposal and design principles
- **Spike results:** Validated in conversation — kiutils parses/writes KiCad 9, kicad-cli exports full netlists with pin data, hierarchy discovery works via sheet objects and hierarchical labels

## Session Handoff

Each session should:
1. Read BRIEF.md, PLAN.md, and TASKS.md to orient.
2. Pick up from the first unchecked task in TASKS.md.
3. Complete one phase (or sub-phase) — don't push past a phase boundary.
4. After completing work: commit, update TASKS.md, and produce a handoff prompt.

**Handoff prompt format:**

```
I'm working on the schematic context system for the Motion Play project.

Read these files to get oriented:
- .context/PROJECT.md
- hardware/CONTEXT.md
- docs/initiatives/schematic-context/BRIEF.md
- docs/initiatives/schematic-context/PLAN.md
- docs/initiatives/schematic-context/TASKS.md

We're on the `schematic-context` branch. The next task is:
  <task description from TASKS.md>

The files you'll need to read for this task:
  <list the specific source files>

<any additional context about unexpected issues, implementation decisions, or deviations from the plan>
```

# Session Handoff — PCB Placement Recovery

**STATUS: RECOVERED.** Git checkout restored the correct placements. User needs to redo: net classes, design rules, pre-defined sizes, thermal vias. Delete this file after use.

## What Happened

The pcb-auto-placement initiative's Phase 3 is complete (committed on `integrated-power-phase5`, commit `a11d124`). The placement script successfully placed 46 components and the L1 anchor was shifted up 2mm. All of this is correctly saved in git.

**However**, the current `.kicad_pcb` file on disk has been overwritten by KiCad. When KiCad PCB Editor was opened for visual review, it had the pre-placement file in memory from a previous session. When the user subsequently saved (after adding thermal vias and GND zones), KiCad wrote its old in-memory state back, reverting all 45 component placements and the L1 shift.

**Result:** The committed git version has correct placements. The current file on disk has the user's manual additions (thermal vias under U5/U6, attempted GND zones) but all component positions are wrong (reverted to pre-placement state).

## What Needs to Happen

### Option A: Re-apply placements to the current file
1. Close KiCad completely
2. Re-apply the L1 shift: change L1's `(at ...)` from current position back to `(at 83.1 114.35 90)` in the .kicad_pcb file
3. Re-extract: `python3 tools/pcb-context/extract.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb --pads`
4. Re-run placement: `python3 tools/pcb-context/place_power.py hardware/pcb-main/kicad/motion-play-main.kicad_pcb`
5. Open KiCad fresh, verify placements loaded correctly
6. Re-add thermal vias (the user's manual via additions will likely be lost)

### Option B: Restore committed version, redo manual work
1. Close KiCad completely
2. `git checkout HEAD -- hardware/pcb-main/kicad/motion-play-main.kicad_pcb`
3. Open KiCad fresh — placements will be correct
4. Re-add thermal vias under U5 and U6 (user had placed 6 vias under U5 and 4 under U6)

Option B is simpler since the manual work was just thermal vias (minutes to redo).

### After recovery, before any further work:
- Verify by re-extracting and spot-checking a few component positions match the placement report
- The U6 rotation should show +90° (SW pins facing RIGHT toward L2, +5V pins facing LEFT)
- L1 should be at (83.1, 114.35) — 2mm above original position

## Critical Lesson for Future Workflow

**Always close KiCad before running the placement script, AND verify KiCad is not still running from a previous session.** The `open -a` command may not reload the file if KiCad already has it open. After running the script, open KiCad fresh and confirm positions look correct before doing any manual work.

## Files to Read

- `docs/initiatives/pcb-auto-placement/BRIEF.md` — initiative scope
- `docs/initiatives/pcb-auto-placement/PLAN.md` — technical approach, U6 rotation logic, resolved issues
- `docs/initiatives/pcb-auto-placement/TASKS.md` — Phase 3 complete, all tasks checked
- `docs/initiatives/integrated-power/TASKS.md` — Phase 5 layout tasks, visual review + routing next
- `hardware/pcb-main/kicad/placement-report.json` — expected positions for all 46 components
- `tools/pcb-context/place_power.py` — the placement script
- `tools/pcb-context/extract.py` — PCB context extraction with --pads flag
- `hardware/pcb-main/ROUTING_GUIDE.md` — step-by-step routing instructions (ephemeral, delete after use)

## Routing Guide Status

A detailed routing guide was created at `hardware/pcb-main/ROUTING_GUIDE.md` with step-by-step instructions for all traces. **Important caveat:** the routing guide was written based on the placement script's output positions, which assumed U6 at +90° with SW pins on the RIGHT side. Once placements are restored, the guide should be accurate. But the next session should verify the U6 pin orientations match what the guide describes before proceeding with routing.

## Board Setup Already Done by User (in current KiCad file)

The user manually configured these in KiCad's Board Setup — these may or may not survive a git checkout:

**Net Classes:**
- Default: 0.25mm track, 0.2mm clearance
- Power_5V: 1.5mm track, 0.3mm clearance (nets: +5V, BOOST_SW)
- Power_3V3: 0.5mm track, 0.2mm clearance (net: +3.3V)
- Power_Med: 1.0mm track, 0.3mm clearance (nets: VSYS, VSYS_SENSE, Protected_VBUS, VBUS_RAW, BQ_SW, BQ_PMID, +5V_TO_LEDS, Net-(C7-Pad2))
- Power_Low: 0.75mm track, 0.25mm clearance (nets: VBAT, BAT_RAW, BQ_REGN)
- Sensitive: 0.2mm track, 0.25mm clearance (nets: BOOST_FB, BOOST_COMP, COMP_MID)

**Design Rules:** min track 0.15mm, min drill 0.2mm, min clearance 0.2mm, min annular 0.13mm, edge clearance 0.3mm

**Pre-defined sizes:** Tracks 0.15-2.0mm, Vias 0.45/0.2, 0.6/0.3, 0.8/0.4

If git checkout loses these, they need to be re-entered. The net class assignments (which nets belong to which class) are stored in the .kicad_pcb file, so they WILL be lost on checkout. The net class definitions themselves may also be in the PCB file.

## Prompt for Next Session

```
Read docs/initiatives/pcb-auto-placement/SESSION_HANDOFF.md for context on what happened and what needs to be recovered. Then read the BRIEF.md, PLAN.md, and TASKS.md in the same folder. The placement script worked correctly but KiCad overwrote the file. We need to restore placements (Option B is simplest: git checkout + redo thermal vias), verify everything matches, then proceed with routing using hardware/pcb-main/ROUTING_GUIDE.md. The board setup (net classes, design rules) may also need to be re-entered if lost in the checkout.
```

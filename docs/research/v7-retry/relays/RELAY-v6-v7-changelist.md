# RELAY — research session — v6 → v7 changelist (DRAFT)

> Informal research session, no agent role. Launch with default `claude`. See `docs/research/v7-retry/RESEARCHER.md` for conventions.

## Context

The prior main PCB (T-Display-based, call it "v6" for shorthand) worked. The current main PCB (v7, ESP32-S3-on-board) does not. The hardware fault lives somewhere inside the delta. This session enumerates that delta.

This is topic 2 of 6 in Stage A, and arguably the single highest-leverage research artifact in the whole track. Every future debugging test will reference it — any row in the change table is a candidate suspect.

The user has flagged honestly that they can't remember what changed beyond the MCU swap. The whole value of this artifact is removing that uncertainty.

## Load these files

- `docs/research/v7-retry/RESEARCHER.md` — conventions
- `hardware/pcb-main/kicad/` — current v7 state:
  - `motion-play-main.kicad_sch` (top-level schematic)
  - `motion-play-main.kicad_pcb` (layout)
  - `esp32_s3.kicad_sch`
  - `power_management.kicad_sch`
  - `tca9548A_subsystem.kicad_sch`
  - `pcb-layout-context.json`
  - `pcb-routing-context.json`
  - `placement-report.json`
- **Prior-working version location: unknown.** Use `git log --all --follow hardware/pcb-main/kicad/motion-play-main.kicad_sch` and `git log --all -- hardware/archive/` to locate the T-Display-era commits. The user should confirm the exact ref to compare against — do not assume.
- `docs/explorations/esp32-integration.md` — likely has notes from the MCU-swap transition
- Memory file `project_pcb_revision_apr2026.md` (via `/Users/marcocleirigh/.claude/projects/.../memory/`) — mentions "3 critical bugs fixed" in v7; those changes matter here.

## Produces

**Artifact path:** `docs/research/v7-retry/v6-v7-changelist.md`

A change inventory. Suggested structure:

1. **Version anchors** — exact git refs or file paths that define "v6" and "v7". Make this unambiguous so later sessions reference the same points.
2. **Scope of comparison** — what you did and didn't look at (e.g., only `pcb-main`, not sensor PCB).
3. **Changes table** — one row per discrete change. Columns:
   - ID (CL-01, CL-02, ...)
   - Category (component / net / power / footprint / passive value / pin assignment / copper / mechanical / other)
   - Subsystem (power / MCU / I²C / display / sensor / charging / ...)
   - What changed (brief, concrete)
   - v6 state → v7 state
   - Suspected risk (low/medium/high + one line why — this is your gut, not conclusion)
   - Evidence (file/line references so a reader can verify)
4. **Changes we could not determine** — things where v6 state wasn't recoverable or ambiguity remained. Explicitly list; don't hide.
5. **Observations** — patterns across the change set (e.g., "the pin reassignments all cluster around GPIOs 8–12 — worth flagging").

## Scope

**In:**
- Schematic-level diff
- Layout-level diff (components placed, nets routed, major copper areas)
- Firmware pin assignments if they moved (brief — reference `firmware/include/pin_config.h`)
- Changes to supporting components (passives, charge circuit, protection, etc.)

**Out:**
- Analyzing which change caused the bug (that's debugging; not here)
- Running any tests
- Modifying any files (this is read-only research)
- Comparing the sensor PCBs (different track)
- Deep trace routing analysis — that belongs in topic 3 (kicad extraction audit). Note trace-level observations as "flagged for topic 3" and move on.

## What was done before this relay

- `adopt-protocol` initiative merged
- Framework for v7 retry agreed; this is topic 2 of 6
- No prior work on this artifact

## Your task

Produce `docs/research/v7-retry/v6-v7-changelist.md` per the structure above.

**Expected first move:** figure out the v6 anchor. Use git log to find the last commit of the T-Display-based main PCB before the ESP32-S3 integration landed. Confirm the ref with the user before diffing against it. Do not guess.

**Expected second move:** compare schematic trees. KiCad schematics are text files (`.kicad_sch`) — diffable, with some signal-to-noise work needed. Start with top-level then expand into subsheets.

**Expected third move:** compare layout. `.kicad_pcb` diffs are noisier; use the JSON context exports if they help, but be careful — they may themselves be v7-only.

Be thorough but conservative in "suspected risk" ratings. The point of the artifact isn't to pick the culprit — it's to produce a list the retry team can walk down methodically.

## Context-pressure behavior

At ~60% context: finish the current section (likely a subsystem's worth of rows), commit `WIP:`, write `docs/research/v7-retry/RELAY-v6-v7-changelist-continue.md` naming which subsystems are done and which remain, and stop. This topic may well take two sessions.

## Open questions to surface

- **v6 anchor** — ask the user to confirm the ref/branch/tag before diffing.
- **Scope boundary** — confirm whether to include firmware pin changes or treat as out-of-scope reference-only.
- **Depth of layout comparison** — layout diffs are expensive. Confirm with user how deep to go: component-level, net-level, or copper-and-via-level.

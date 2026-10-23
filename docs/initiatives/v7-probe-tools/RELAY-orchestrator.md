# Relay-Planner — Orchestrator — 2026-10-23

role:orchestrator

## Context
Debug cards 2 and 3 (v7 I²C fault track, `lab/`) are blocked on two missing log-only probe tools. Card 2 needs a v6 build that prints the v7 diag loop's rows. Card 3 needs an external-master sketch that reaches VCNL 0x60 behind a rigid's PCA 0x76. The Planner wrote this initiative to build both.

## Load these files
- .context/PROTOCOL.md
- docs/initiatives/v7-probe-tools/BRIEF.md, PLAN.md, TASKS.md
- Workers also need `git show v7-clean:firmware/src/components/sensor/SensorManager.cpp`, function `runBusDiagnosticLoop` (~line 1285). This is the reference readout both tools copy exactly. PLAN "Reference readout" summarises it, but the source is the spec.

## State
Branch: `feat/v7-probe-tools`, cut from `main` (601c367), docs commit 582b407, not pushed. Phase 2 also uses a side branch `feat/v7-probe-tools-v6diag` from `v6-ref` (4da1c67), in a scratchpad worktree, never merged.
Build: n/a (no code yet)
TASKS.md current: yes

## What was done
- Decided on a sibling sketch `tools/arduino-sketches/v7_pca_master_probe/` for card 3. `v7_bq_master_probe` stays untouched: L-Ph24a cites it and card 4 runs on it.
- Decided on an env `lilygo-t-display-s3-diag` on top of 4da1c67, tagged `v6-diag`, for card 2, not a standalone sketch. All new code sits behind `DIAG_NO_WIFI`. The base env must build the `v6-ref` path unchanged.
- Settled that v6 TCA ch 2 is on J6, pins 1–4 (v6 netlist fd632ef).
- Probe sketch default clock is 400 kHz (matches `v7-clean`), overridable at build time.
- Two phases: Phase 1 is the card 3 probe (higher priority), Phase 2 is the v6 diag readout. Both are small. One session may finish both.

## Your task
Run the initiative: dispatch Phase 1, then Phase 2, to Workers per TASKS.md.
Verification is build-only. No bench and no flashing:
- Phase 1: `pio ci` builds clean for `nano_33_iot` and `arduino_nano_esp32` at both clocks. The row/printf strings match `v7-clean` `runBusDiagnosticLoop()`.
- Phase 2: both v6 envs build. `git diff v6-ref v6-diag` shows only the new env, the new function, and `#ifdef DIAG_NO_WIFI` code. The `v6-diag` tag and the branch are pushed.

Hard limits: no edits to `lab/`, `v7-clean`, `v6-ref`, `v7_bq_master_probe`, or product firmware on `main`. At the end, push `feat/v7-probe-tools`, open the PR, and give the user the handoff items for the debugger (STATE §6/§8): the tag, the commit, the env, the sketch path, the core versions, and that cards 2 and 3 are unblocked.

## Open questions
- Whether card 4 should switch to the new sketch at 400 kHz is the debugger's call. Out of scope here.
- The SAMD21 core has no I²C timeout code, so a stuck bus may hang rather than print `X(5)`. Record this in the sketch header. Don't engineer around it.

# Relay-Debugger — Planner — 2026-10-23

role:planner

## Context
The v7 debug track is running on `lab/` (first map card V7R-003 recorded: the fault reproduces on v7 at `v7-clean`). Two cards in the queue can't run because a probe tool they need doesn't exist. Card 2 is v6 under the minimal repro. Card 3 is SAMD21 as master with a rigid: does the VCNL answer? The debugger role doesn't build tools, so this relay asks for a small initiative that builds both. A suggested name is `v7-probe-tools`; the user may choose another. Card 4 doesn't depend on this and may run in parallel.

## Load these files
- .context/PROTOCOL.md
- lab/STATE.md, sections 1, 6 and 8 only: the symptom, the baselines and bench, and the queue
- lab/cards/V7R-003-v7-clean-minimal-repro.md: the readout format and arm counting these tools must support
- docs/research/v7-retry/decisioning.md §2.7: cards 2 and 3 as queued, and why
- tools/arduino-sketches/v7_bq_master_probe/v7_bq_master_probe.ino: the external-master probe sketch used in L-Ph24a
- `git show v7-clean:firmware/src/components/sensor/SensorManager.cpp`, function `runBusDiagnosticLoop` (`grep -n runBusDiagnosticLoop`): the v7 diag loop whose output the cards compare against
- `git tag -n20 v7-clean` and `git tag -n20 v6-ref`
- firmware/CONTEXT.md "Development Cable Workflow" (v6 T-Display flashing)
- docs/research/v7-retry/v6-v7-changelist.md CL-16 and CL-24

## State
Branch: n/a. Start `feat/<initiative-slug>` from `main` once PR "debug/v7-track" is merged, or from `debug/v7-track` if it isn't merged yet.
Build: n/a
TASKS.md current: n/a (new initiative)

## What was done
- V7R-003 (`v7-clean`, `motion-play-v7-diag`, v7 #0003): the TCA2-row BQ result went from `.` to `X(2)` to `.` across A/B/A, 10/10 in each arm. Readout: the v7 diag loop's per-iteration rows (BASE / TCA0 / TCA1 / TCA2 [/ TCA+PCA0/1]), logged by the session over serial.
- Card 2 is blocked: `v6-ref` (4da1c67, env `lilygo-t-display-s3`) has no diag loop. Nothing in it re-probes BQ with a TCA channel held open, so it can't produce the TCA2-row marker. Flashing the v7 diag env onto v6 would change board and firmware at once.
- Card 3 is blocked: `v7_bq_master_probe` opens TCA channels and probes INA/VCNL/BQ/TCA, but it never opens a PCA9546A (0x76) channel. VCNL 0x60 sits behind the PCA on a rigid, so the sketch can't see it. As written it also doesn't probe PCA 0x76.
- Checkpoint @ V7R-003 (notebook 2026-10-23) ranks card 3 above card 4 on what it decides: whether the VCNL product failure and the BQ marker are the same fault.

## Your task
Write BRIEF, PLAN and TASKS for an initiative that delivers two probe tools:
1. **v6 diag readout (card 2).** It runs on the v6 T-Display master and prints the same rows and codes as the v7 diag loop (`t=… <state> INA:. BQ:X(2) …`), looping until reset. It must keep the I²C init identical to `v6-ref` (Wire.begin(43, 44), 400 kHz, default drive, no filters, default pulls) so it can be declared as one firmware delta against `v6-ref`. Tag or name the build so a card can cite it. Decide, and justify, whether it is a new env on top of 4da1c67 or a standalone sketch, and say what else differs from `v6-ref` (BQ config, display, boot order).
2. **PCA-aware external-master probe (card 3).** Extend `v7_bq_master_probe` or add a sibling so it also opens PCA 0x76 channels 0 and 1 behind an open TCA channel and probes VCNL 0x60 there. Keep the existing rows and the BQ column. Output must match the v7 diag loop's row labels (`TCA2+PCA0`, `TCA2+PCA1`) so counts compare directly. It must still build for the Nano 33 IoT (SAMD21; L-Ph24a) and the Nano ESP32.
Both are log-only tools. They make no change to `v7-clean`, `v6-ref` or the lab procedures. Keep it light: the user has asked for less ceremony.

## Open questions
- Which v6 connector maps to TCA channel 2? On v6, J4–J6 are 5-pin SM05B taking a 4-pin plug (CL-16). Card 2 needs the connector, pin order and the row it prints to. Not checked this session.
- Clock: `v7_bq_master_probe` runs at 100 kHz; `v7-clean` runs at 400 kHz. A clock option (default unchanged) would let cards 3 and 4 remove that confound. Card 4 will run with the sketch as is and declare the clock difference.
- Serial capture: the debugger logged serial with a throwaway pyserial script in its scratchpad. A lab tool for that is a methodology item (`docs/initiatives/test-workflow-setup/RELAY-methodology-planner.md`), not part of this initiative unless the user wants it here.

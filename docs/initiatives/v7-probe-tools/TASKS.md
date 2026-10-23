# v7 Probe Tools — Tasks

## Phase 1: PCA-aware external-master probe (card 3)

Branch `feat/v7-probe-tools`. Spec: PLAN "Reference readout" and "Tool 1".

- [x] Create `tools/arduino-sketches/v7_pca_master_probe/v7_pca_master_probe.ino`. Port `runBusDiagnosticLoop()` from `v7-clean` with raw `Wire` writes: same banner, the PCA detection summary (setup-time scan from `initializePCA()`), the same probe order and row format, the same delays and cadence. Add a header comment covering wiring, procedure (`motion-play-v7-relbus` on v7; rigid on J6 before reset) and the SAMD21 no-timeout note. Add a self-identifying banner line: sketch, `PROBE_VERSION`, board, clock. Default `I2C_CLOCK_HZ` 400000, overridable with `#ifndef`.
- [x] Diff the sketch's printf strings and delays against `v7-clean` `runBusDiagnosticLoop()` line by line. Fix any mismatch. Do not touch `v7_bq_master_probe`.
- [x] Build check: `pio ci --board nano_33_iot --board arduino_nano_esp32 <sketch>`, plus one build with `-DI2C_CLOCK_HZ=100000` (`--project-option="build_flags=-DI2C_CLOCK_HZ=100000"`). Both boards must build clean. Record the resolved platform/core versions in SESSION.md.
- [ ] Add one row for the new sketch to `tools/CONTEXT.md`, wherever the Arduino sketches are listed. If they aren't listed, skip this.
- [ ] 🔄 Handoff: commit. In SESSION.md, record the sketch path, the commit hash and the core versions for the card.

# --- handoff point ---

## Phase 2: v6 diag readout (card 2)

Worktree at `v6-ref` (4da1c67), branch `feat/v7-probe-tools-v6diag`. Spec: PLAN "Tool 2". The worktree goes in the session scratchpad. Remove it at the end.

- [ ] Add `[env:lilygo-t-display-s3-diag]` to `platformio.ini` (extends the base env, plus `-DDIAG_NO_WIFI`). Leave the base env untouched.
- [ ] `SensorManager.{h,cpp}`: add `runBusDiagnosticLoop()`, copied verbatim from `v7-clean`.
- [ ] `main.cpp`: port the `DIAG_NO_WIFI` network skip from `v7-clean`. After `sensorManager.init()`, under `#ifdef DIAG_NO_WIFI`: print the init result and the `[v6-diag]` line, then call `runBusDiagnosticLoop()` whatever the result. Guard any later use of `mqttManager` / `dataTransmitter` the diag path could reach.
- [ ] Build both `lilygo-t-display-s3-diag` and `lilygo-t-display-s3`. Then run `git diff v6-ref` and confirm: the only changes are the new env, the new function, and code inside `#ifdef DIAG_NO_WIFI`. I²C init lines are byte-identical.
- [ ] Commit. Create annotated tag `v6-diag`; its message follows PLAN "Declared differences from `v6-ref`", in `v6-ref` tag style, build-only. Push the branch and the tag. Remove the worktree.
- [ ] 🔄 Handoff: on `feat/v7-probe-tools`, record in SESSION.md the tag, the commit, the env and the build result. Report to the user what the debugger needs for STATE §6 and §8: `v6-diag` → commit + env, the probe sketch path + commit, and that cards 2 and 3 are unblocked. Do not edit `lab/` (the debugger owns it). Commit.

## Deferred

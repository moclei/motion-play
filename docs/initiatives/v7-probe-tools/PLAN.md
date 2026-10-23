# v7 Probe Tools — Plan

## Approach

Two independent tools, one phase each. The probe sketch goes first because card 3 outranks card 4, and card 4 is runnable already.

**Reference readout.** Both tools reproduce `SensorManager::runBusDiagnosticLoop()` at `v7-clean` (`git show v7-clean:firmware/src/components/sensor/SensorManager.cpp`, line ~1285). Treat that function as the spec. Copy its strings and sequencing; don't paraphrase them.
- Banner `I2C BUS DIAGNOSTIC LOOP (continuous — press RESET to stop)`, then the "PCA detection summary (from init)" block, the probe/legend/expected lines, then `--- Iteration N ---` blocks.
- Row: `Serial.printf("t=%7lu  %-10s  ", millis(), label)`, then for each probe in order INA 0x40, BQ 0x6B, TCA 0x70, PCA 0x76, VCNL 0x60: `"%s:.    "` on ACK, `"%s:X(%u) "` otherwise.
- Per iteration: `resetAllMuxes()` → `BASE`; then for TCA ch 0..2: reset, open TCA ch (delay 2), close that ch's PCA if one was detected (delay 2), print `TCA<ch>`. If a PCA was detected on that ch: PCA ch0 (delay 2) → `TCA<ch>+PCA0`; PCA all off (delay 1), PCA ch1 (delay 2) → `TCA<ch>+PCA1`. Blank line, `delay(2000)`.
- `resetAllMuxes()`: for each ch with a PCA, select TCA ch, delay 1, write 0x00 to that PCA; then TCA 0x00, delay 2.
- PCA rows appear only for channels where a PCA was found at init. Detection scans `{0x74, 0x75, 0x76, 0x72, 0x71, 0x73, 0x77}` behind each TCA channel (`initializePCA()`, identical in `v6-ref` and `v7-clean`). The PCA column always probes 0x76, whatever address was detected.

### Tool 1: PCA-aware external-master probe (card 3)

A **new sibling sketch**, `tools/arduino-sketches/v7_pca_master_probe/v7_pca_master_probe.ino`. `v7_bq_master_probe` stays as it is.

Why a sibling and not an in-place edit: `v7_bq_master_probe` is the artefact behind L-Ph24a, and card 4 is about to run on it "as is". Its column order (INA VCNL BQ TCA) and spacing also differ from the v7 loop. Making it v7-compatible would change a cited tool under a running card.

Content:
- `setup()`: `Wire.begin()` (board default pins: A4/A5 on both Nanos), `Wire.setClock(I2C_CLOCK_HZ)`. Then a self-identifying banner: sketch name, `PROBE_VERSION` string, board (`ARDUINO_BOARD` if the core defines it, else a `#if` on `ARDUINO_ARCH_SAMD` / `ARDUINO_ARCH_ESP32`), and clock. Keep the wiring/procedure header comment from the old sketch, updated: the v7 runs `motion-play-v7-relbus`; the rigid sits on J6 before the Nano is reset.
- PCA detection, run once at setup (same scan as `initializePCA()`, same summary lines), then the v7 loop body verbatim, using raw `Wire` writes in place of the `TCA9548A` / `PCA9546A` classes. The bus transactions are the same: the v7 `TCA9548A::disableAllChannels()` clears its channel cache, so every select in the loop is a real write.
- No 5-iteration burst and no decision-matrix text from the old sketch. Iterations run back to back from 1 at the v7 cadence, so the arm-counting rules in V7R-003 carry over unchanged.
- Clock: `#ifndef I2C_CLOCK_HZ` / `#define I2C_CLOCK_HZ 400000`. The default matches `v7-clean`, the readout it is compared against, which removes the 100 vs 400 kHz confound for card 3. To get 100 kHz, set `-DI2C_CLOCK_HZ=100000` at build time or edit the define; the banner shows which clock ran.

### Tool 2: v6 diag readout (card 2)

A **new env on top of 4da1c67**, not a standalone sketch. Reasons:
- A standalone sketch would replace the whole v6 boot: no BQ24195 IINLIM write, which v6 needs to avoid brownout under display load; no display init; different boot timing; possibly a different core. The card would then change "firmware" wholesale, not by one delta.
- An env on `v6-ref` mirrors exactly what `motion-play-v7-diag` is to `motion-play-v7`: same boot order, same SensorManager init, network skipped, diag loop at the end. So card 2's v6 rows and V7R-003's v7 rows come from the same firmware shape.

Mechanics:
- Git worktree at `v6-ref` (4da1c67). Branch `feat/v7-probe-tools-v6diag`. One commit, annotated tag **`v6-diag`**, with a message in the style of the `v7-clean` / `v6-ref` tags: I²C init line, env, delta list, "build-only". Push branch and tag. The branch is never merged to `main`; the tag is what cards cite.
- `platformio.ini`: add `[env:lilygo-t-display-s3-diag]`, `extends = env:lilygo-t-display-s3`, build_flags `${env:lilygo-t-display-s3.build_flags}` plus `-DDIAG_NO_WIFI`. The base env stays untouched.
- `main.cpp` `initializeSystem()`: port the `#ifdef DIAG_NO_WIFI` block from `v7-clean` main.cpp (~line 539: `WiFi.mode(WIFI_OFF); btStop();`, skip config/WiFi/MQTT/cloud fetch, `cloudConfigLoaded = false`). Port any `#ifndef DIAG_NO_WIFI` guard the v6 `loop()` or later init needs to avoid null `mqttManager` / `dataTransmitter` use (v7-clean guards `loop()` ~line 1639). Right after `sensorManager.init()`, under `#ifdef DIAG_NO_WIFI`: print the init result, then call `runBusDiagnosticLoop()` **whether init succeeded or failed**.
- `SensorManager.{h,cpp}`: add `runBusDiagnosticLoop()` copied verbatim from `v7-clean`, `BUS_RECOVERY_TEST` blocks included (inert). It needs only `mux`, `pca_instances` and `pca_addresses`, all already in v6.
- One print-only line at loop start: `[v6-diag] v6-ref 4da1c67 + diag readout; I2C init unchanged`.
- All new code paths sit behind `DIAG_NO_WIFI`, so `lilygo-t-display-s3` built at `v6-diag` takes the `v6-ref` path. The Worker confirms this with `git diff v6-ref v6-diag` (only additions inside `#ifdef DIAG_NO_WIFI`, plus the new env and the new function).

**Declared differences from `v6-ref`** (go in the tag message; card 2 copies them):
1. Network skipped, radio off (`DIAG_NO_WIFI`). `v6-ref` would halt on WiFi failure before sensor init anyway; with WiFi it would init with cloud config. Neither affects I²C init.
2. Diag loop entered after sensor init instead of halting on failure or entering the main loop.
3. Print-only banner line.
Unchanged: BQ24195 config (REG00 0x36, REG05 0x8A, via `Wire.begin(43, 44)` before display init), display init, boot order up to sensor init, `STARTUP_I2C_SCAN=false`, core `#2.0.14`, lib_deps.

**Declared differences from `motion-play-v7-diag` at `v7-clean`** (for comparing card 2 with V7R-003; not v6-ref deltas):
- v7 enters the loop only on init failure. v6-diag always enters it. With no rigid, both fail init, so it makes no difference to card 2.
- v7 has `STARTUP_I2C_SCAN=true` (an extra boot-time scan) and INA power prints around sensor init. Both are boot-only and happen before the loop.
- v7 prints an `I2C: 400 kHz, default drive, no filters, default pulls [v7-clean]` line from init. v6 has no such line, and the `[v6-diag]` line stands in for it.
- The v6 board env and variant are `lilygo-t-display-s3` with display/buttons, per CL-24.

## Technical Notes

- **v6 connector for TCA ch 2: J6.** v6 netlist (`fd632ef:hardware/pcb-main/kicad/circuit-context.json`): J6 pin 1 +3.3V, pin 2 GND, pin 3 `CH2_SDA`, pin 4 `CH2_SCL`. These go to U4 (TCA9548A) SD2/SC2, pins 8/9. J6 is a 5-pin SM05B. The 4-pin plug sits on pins 1–4 (CL-16), and pin 5 is the empty end. Card 2's trigger goes on J6 and shows on the `TCA2` row, the same as v7.
- **Error codes differ by core.** ESP32 core: 0 ACK, 2 NACK addr, 3 NACK data, 5 timeout. The SAMD21 core's `endTransmission` returns 0/2/3 (and 4) but has no timeout code. A stuck bus can hang the sketch rather than print `X(5)`. Note this in the sketch header so a card lists it under "setup void".
- **Build checks:** the probe sketch builds with `pio ci --board nano_33_iot --board arduino_nano_esp32 tools/arduino-sketches/v7_pca_master_probe/v7_pca_master_probe.ino`. First use installs the `atmelsam` platform. Record the resolved core versions from the build output in SESSION.md, so a card can declare them. `v6-diag` builds with `pio run -e lilygo-t-display-s3-diag` and `-e lilygo-t-display-s3` in the worktree.
- v6 flashing and bench use follow `firmware/CONTEXT.md` "Development Cable Workflow". That belongs to the card, not this initiative.

## Rejected Approaches

- Standalone T-Display sketch for card 2: it replaces the whole v6 boot (no BQ IINLIM write, no display, different core), so it isn't a single delta against `v6-ref`.
- Flashing `motion-play-v7-diag` onto v6: it changes board env and firmware at once (relay).
- Editing `v7_bq_master_probe` in place: it is cited by L-Ph24a and in use for card 4, and its column order differs from the v7 loop.
- Probing PCA rows on every TCA channel regardless of detection: it changes the iteration shape and timing relative to the v7 loop.

## Open Questions

- ~~Which v6 connector is TCA ch 2?~~ J6, pins 1–4 (Technical Notes).
- ~~Env vs standalone for v6~~: env (Approach).
- Probe-sketch default clock is 400 kHz, to match `v7-clean`. Card 4 runs the old sketch at 100 kHz as declared. If the debugger wants card 4 at 400 kHz, the new sketch's BASE/TCA rows serve that too. That is the debugger's call, not this initiative's.
- Serial capture tool: out of scope, belongs to `test-workflow-setup`.

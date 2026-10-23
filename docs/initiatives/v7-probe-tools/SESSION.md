# Session Log — v7 Probe Tools

## 2026-10-23 — orchestration run 1

Entry: branch `feat/v7-probe-tools` at 480c744 (docs + relay), clean tree, not pushed. No blocking Open Questions in PLAN.md. Verification is build-only per RELAY-orchestrator.md.

---

### Worker #1 — Phase 1: PCA-aware external-master probe (card 3)

**Dispatch:**
```
Initiative: v7-probe-tools
Phase: 1 — PCA-aware external-master probe (card 3)
Initiative path: docs/initiatives/v7-probe-tools/
Additional reading: `git show v7-clean:firmware/src/components/sensor/SensorManager.cpp` — `runBusDiagnosticLoop()` (~line 1285) and `initializePCA()`; this source is the spec, PLAN "Reference readout" only summarises it. `tools/arduino-sketches/v7_bq_master_probe/` for the header-comment/wiring baseline (read only, do not modify).

Tasks assigned (from TASKS.md Phase 1):
<Phase 1 task list as in TASKS.md>

The first task is marked `[~]` because it was dispatched to you — it is not someone else's work in progress.

You are not the Orchestrator. Do not create documents, work across phases, or replan.
Return DONE, PARTIAL, or BLOCKED with specifics.
```
Hard limits restated: no edits to `lab/`, `v7-clean`, `v6-ref`, `v7_bq_master_probe`, product firmware. Do not push.

#### Notes

**Result: DONE.** Sketch: `tools/arduino-sketches/v7_pca_master_probe/v7_pca_master_probe.ino`, last changed in **ee10efd** (cite this for card 3). `PROBE_VERSION` "1.0". Banner line: `[probe] sketch=v7_pca_master_probe version=1.0 board=<…> i2c_clock=<Hz> Hz`. Default clock 400000. Override with `-DI2C_CLOCK_HZ=100000`. `v7_bq_master_probe` untouched.

**Build (pio ci, build-only, both clean with no warnings, at 400k and at `-DI2C_CLOCK_HZ=100000`; the flag was confirmed on the compile line):**
- `nano_33_iot`: platform Atmel SAM 9.0.0, `framework-arduino-samd` 1.8.14, CMSIS 1.40500.0 (4.5.0), cmsis-atmel 1.2.2, `toolchain-gccarmnoneeabi` 1.70201.0 (7.2.1).
- `arduino_nano_esp32`: platform Espressif 32 6.4.0, `framework-arduinoespressif32` 3.20011.230801 (**arduino-esp32 2.0.11**), `toolchain-xtensa-esp32s3` 8.4.0+2021r2-patch5. Note: this is NOT the 2.0.14 core that `v7-clean` / `v6-ref` pin. A card comparing Nano ESP32 rows with V7R-003 should declare it.

**Fidelity points (for the card / next session):**
- printf: the atmelsam `Print` has no `printf`. All formatted output goes through `serialPrintf()` (vsnprintf into a 128 B buffer, then `Serial.print`) on both boards. The v7 format strings are unchanged, so the output is byte-identical to `Serial.printf`.
- String/delay diff vs `v7-clean` (`initializePCA()` and `runBusDiagnosticLoop()`, excluding `BUS_RECOVERY_TEST`): extracted mechanically, identical in content and order.
- TCA channel cache emulated (PLAN corrected): v7 skips a TCA select when the channel is already cached. With a PCA on ch2 (card 3), the first `resetAllMuxes()` of each iteration skips the TCA write. At iteration 1, the sketch's cache is 0xFF after the setup scan. On v7, the cache at loop entry depends on how far sensor init got, so iteration 1's first transaction may differ. Iterations 2+ match.
- Setup also replicates `mux.begin()` (probe 0x70, write 0x00, print "TCA9548A initialized" / "ERROR: Failed to initialize TCA9548A"). If begin fails, the PCA scan is skipped and the loop runs with no PCAs, as v7 does on init failure. Not reproduced: v7's `STARTUP_I2C_SCAN` debug scan and the other `init()` prints (boot-only).
- `Wire.setTimeout(100)` from the v7 TCA class is omitted. On ESP32 core 2.0.x it is `Stream::setTimeout`; the I2C timeout is `setTimeOut` (default 50 ms). It has no bus effect.
- Board name: `ARDUINO_BOARD` is not defined under PlatformIO, so the banner shows the fallback `SAMD (Nano 33 IoT)` / `ESP32 (Nano ESP32)`. It is a `static const char[]`, not a macro, because PlatformIO's `.ino` pre-pass (`-fpreprocessed -dD -E`) doesn't evaluate `#if` and warned on the per-branch `#define`s.
- `tools/CONTEXT.md` doesn't list the Arduino sketches, so no row was added.

**Environment side effect:** the first `pio ci` installed the `atmelsam` platform and replaced the global default `~/.platformio/packages/framework-arduinoespressif32` (was 2.0.15, now 3.20011.230801 / 2.0.11, the default for espressif32 6.4.0). Project envs pin 2.0.14 through git (`@src-` dirs), so they are unaffected. Phase 2 builds should still show `#2.0.14` in their output.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 1 | Phase 1: PCA-aware external-master probe | DONE | No — clean completion | e91eedd (sketch: ee10efd) | 5 tasks; CONTEXT row skipped per task (sketches not listed) |

#### Verification
- All 5 Phase 1 tasks `[x]`; 4 commits ab5ed59..e91eedd; tree clean; no paths under `lab/`, `firmware/`, or `v7_bq_master_probe` touched.
- Re-ran `pio ci --board nano_33_iot --board arduino_nano_esp32` on the sketch: both SUCCESS (400 kHz default). 100 kHz build taken on the Worker's word (flag confirmed on compile line per notes).
- Spot-checked row/banner/iteration format strings against `v7-clean` SensorManager.cpp 1289–1397: identical.
- Worker edited one PLAN line (Tool 1 → Content) to correct the TCA cache claim. Confirmed against `v7-clean:firmware/src/components/tca9548a/TCA9548A.cpp` (`selectChannel` skips when `_currentChannel == channel`; only a successful 0x00 write clears it). Accepted as a factual correction; no scope change. PLAN has no date-stamped headings.
- Carry forward to Phase 2: global `framework-arduinoespressif32` default is now 2.0.11. Phase 2 must confirm its builds resolve the pinned `#2.0.14`.

---

### Worker #2 — Phase 2: v6 diag readout (card 2)

**Dispatch:**
```
Initiative: v7-probe-tools
Phase: 2 — v6 diag readout (card 2)
Initiative path: docs/initiatives/v7-probe-tools/
Additional reading: v7-clean sources for the port — `firmware/src/components/sensor/SensorManager.{h,cpp}` `runBusDiagnosticLoop()` (~1285), `firmware/src/main.cpp` DIAG_NO_WIFI blocks (~539, ~1639), `platformio.ini` motion-play-v7-diag env; `git show v6-ref` tag message for tag style. SESSION.md Worker #1 Verification (2.0.14 core check).

Tasks assigned (from TASKS.md Phase 2):
<Phase 2 task list as in TASKS.md>

The first task is marked `[~]` ...
You are not the Orchestrator. ...
```
Phase notes: worktree in session scratchpad; build output must show core #2.0.14; push only `feat/v7-probe-tools-v6diag` + tag `v6-diag` (not `feat/v7-probe-tools`); SESSION/TASKS writes go on `feat/v7-probe-tools` in the main checkout.

#### Notes

**Result: DONE.** Tag **`v6-diag`** (annotated, tag object fa42ba8) → commit **189cc03** on branch `feat/v7-probe-tools-v6diag` (parent `v6-ref` 4da1c67). Env **`lilygo-t-display-s3-diag`**. Branch and tag pushed to origin; the worktree was removed. Cite the tag for card 2.

**Build (build-only, 2026-10-23, both SUCCESS, no warnings from `firmware/src`):**
- Both envs resolved `framework-arduinoespressif32 @ 2.0.14+sha.44da992` (the `#2.0.14` git pin), platform Espressif 32 6.4.0. The 2.0.11 global default that Phase 1 left behind is not used.
- `lilygo-t-display-s3-diag`: Flash 1,315,357 B (20.1%), RAM 69,452 B (21.2%). `lilygo-t-display-s3`: Flash 1,842,085 B, RAM 70,356 B. The diag image is smaller because the network/cloud path is compiled out.
- Libraries resolved from today's cache (the same for both envs): TFT_eSPI 2.5.43, Adafruit BusIO 1.17.4, Adafruit VCNL4040 1.2.0, TCA9548 0.3.2, FastLED 3.10.8, PubSubClient 2.8.0, ArduinoJson 6.21.6, Chirale_TensorFLowLite 2.0.0. The `^` ranges are unchanged from `v6-ref`. The `v6-ref` tag build on 2026-10-19 also resolved from the live cache.

**`git diff v6-ref` audit:**
- 4 files, +216/−1. The single "−" line is `platformio.ini`'s last line (`-DARDUINO_USB_CDC_ON_BOOT=0`). `v6-ref` had no newline at end of file, and appending the env added one. The diff is empty under `--ignore-space-at-eol`, so the base env is unchanged in content.
- `SensorManager.cpp`: only `runBusDiagnosticLoop()` was added, placed before `dumpSensorConfiguration()` as in v7. It was checked mechanically with awk extraction + diff against `v7-clean`: identical, `BUS_RECOVERY_TEST` blocks included. `SensorManager.h`: the declaration and its comment were copied verbatim. `selectChannelVerify` / `readControlRegister` were not ported, because the loop doesn't use them.
- `main.cpp`: two `#ifdef DIAG_NO_WIFI … #else … #endif` wraps. (1) The network block: the v7 `#ifdef` header was copied verbatim, and the v6 network code sits untouched in `#else`. (2) The sensor init: the diag branch runs the same `sensorManager.init(&currentConfig)` call, prints `ERROR: Sensor initialization failed!` (and the display error) or `Sensors initialized successfully`, then `[v6-diag] v6-ref 4da1c67 + diag readout; I2C init unchanged`, then the loop, then `while(1)`. The original v6 `if (!init) {halt}` sits byte-identical in `#else`.
- No added or removed line touches `Wire.begin`, `setClock`, pulls, filters or drive. `TCA9548A` / `PCA9546A` are unchanged between `v6-ref` and `v7-clean` (empty diff on `components/tca9548a`). So the TCA channel cache noted in Phase 1 behaves the same on v6-diag as on v7.
- No `loop()` guard was ported. The diag path never returns from `runBusDiagnosticLoop()` (plus `while(1)`), so `loop()`, `handleCommand()` and every other `mqttManager` / `dataTransmitter` use is unreachable. No task that touches them is started before that point: the `xTaskCreate` calls in `SensorManager` / `InterruptManager` are only reached from collection commands.

**For the card:** the v6-diag boot prints `[DIAG_NO_WIFI] Skipping WiFi/MQTT init, forcing radio off` and `WARNING: Cloud config unavailable, sensors will use defaults`, then `[Config] Detection mode…`, the sensor init output, the init result, the `[v6-diag]` line, and then the v7 banner/rows. Flashing follows `firmware/CONTEXT.md` "Development Cable Workflow": `pio run -e lilygo-t-display-s3-diag -t upload` from a checkout of `v6-diag`.

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 2 | Phase 2: v6 diag readout | DONE | No — clean completion | handoff on this branch; `v6-diag` → 189cc03 | 6 tasks; branch + tag pushed; worktree removed; `lab/` untouched |

#### Result
| # | Phase | Result | Escalation evaluated? | Commit | Notes |
|---|-------|--------|-----------------------|--------|-------|
| 2 | Phase 2: v6 diag readout | DONE | No — clean completion | 0bb87e9 (v6-diag: 189cc03) | 6 tasks; tag + branch pushed |

#### Verification
- All tasks in TASKS.md `[x]`; tree clean; scratchpad worktree removed.
- `v6-diag^{commit}` = 189cc03, parent = `v6-ref` 4da1c67. `git ls-remote origin` shows tag object fa42ba8 and branch `feat/v7-probe-tools-v6diag` at 189cc03.
- `git diff v6-ref v6-diag`: 4 files, +216/−1. Read main.cpp and platformio.ini hunks in full: all main.cpp changes sit inside `#ifdef DIAG_NO_WIFI` with the original code unchanged in `#else`; the only `-` line is the EOF-newline on platformio.ini; no `Wire.`/`setClock` lines touched.
- `runBusDiagnosticLoop()` extracted from `v7-clean` and `v6-diag` and diffed: identical.
- Builds taken on the Worker's word (both envs SUCCESS, core 2.0.14+sha.44da992); not re-run.
- No `loop()` guard ported: diag path ends in the loop then `while(1)`, so no later `mqttManager`/`dataTransmitter` use is reachable. Accepted.
- PLAN has no date-stamped headings.

---

**Outcome:** Loop complete — 2 workers dispatched, 1 session, 0 unresolved blockers. `feat/v7-probe-tools` pushed and PR opened by the Orchestrator. Debugger handoff items relayed to the user (no `lab/` edits).

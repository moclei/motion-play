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

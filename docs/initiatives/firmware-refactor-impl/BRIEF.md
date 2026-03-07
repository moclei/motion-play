# Firmware Architecture Refactor — Implementation

## Intent

Implement the refactoring recommendations from the firmware architecture audit. The audit (see `docs/initiatives/firmware-refactor/REPORT.md`) identified structural issues across all active firmware source: oversized files, code duplication, concurrency hazards, fragile error handling, tangled include chains, and scattered global state. This initiative executes the fixes in four prioritized phases.

## Goals

- No source file exceeds ~300 lines (soft limit: 600 max)
- Each file/class has a single, clear responsibility
- Clean module boundaries with minimal coupling (transitive include chains broken)
- All concurrency patterns are correct, not just accidentally safe (`std::atomic`, proper task exit handshakes)
- Network failures no longer freeze the device (non-blocking reconnection)
- Zero functional regressions — refactoring only, no feature changes

## Scope

What's in:
- Phase 1: Foundation — shared type headers, `debug_log.h`, `constants.h`, header cleanup, include guard unification
- Phase 2: Correctness & Safety — bug fixes (`StatsAccumulator` overflow, `const_cast` UB, `volatile` → `atomic`, task races, silent failures), dead code removal
- Phase 3: Structural Decomposition — main.cpp extraction (CommandHandler, CloudConfig, DetectionController, CollectionController, ButtonHandler), SensorManager unification (adopt MuxController + VCNL4040 driver), DataTransmitter DRY-up, DisplayManager split, ConfigLoader extraction, IDetector interface
- Phase 4: Behavioral Improvements — non-blocking WiFi/MQTT reconnection, cooperative data transmission, `xTaskNotifyFromISR`, CalibrationManager `delay()` elimination

What's out:
- Feature additions or algorithm changes
- Hardware driver rewrites (VCNL4040 driver is vendor-derived — light touch only)
- Archive files (`firmware/src/archive/`)
- Auto-generated files (`model_data.h`)
- Build system or dependency changes (unless required by file moves)

## Constraints

- Must compile and run identically after each refactoring step — no behavior changes (except Phase 4 which intentionally changes blocking behavior to non-blocking)
- ESP32-S3 / Arduino / PlatformIO toolchain
- Dual-core architecture must be preserved (Core 0 = sensors, Core 1 = networking)
- PSRAM usage patterns must remain compatible
- Changes should be incremental and testable — each task in TASKS.md is one compilable, flashable step

## Reference

- **Audit findings:** `docs/initiatives/firmware-refactor/REPORT.md` — synthesized themes, prioritized plan, expected outcomes
- **Detailed per-file analysis:** `docs/initiatives/firmware-refactor/PLAN.md` — line numbers, code patterns, risk notes for each recommendation

## Session Handoff

This initiative is designed for incremental progress across many chat sessions. Each session should:

1. Read BRIEF.md, PLAN.md, and TASKS.md to orient.
2. Pick up from the first unchecked task in TASKS.md.
3. Complete one task (or a few small ones) — don't try to push through an entire phase.
4. After completing work: commit, update TASKS.md, and produce a **handover prompt** (see below).

**Handover prompt format** — write this at the end of each session so the next session can start clean:

```
I'm working on the firmware refactor implementation for the Motion Play project.

Read these files to get oriented:
- .context/PROJECT.md
- firmware/CONTEXT.md
- docs/initiatives/firmware-refactor-impl/BRIEF.md
- docs/initiatives/firmware-refactor-impl/PLAN.md
- docs/initiatives/firmware-refactor-impl/TASKS.md

We're on the `firmware-refactor-impl` branch. The next task is:
  <task ID and description from TASKS.md>

The files you'll need to read for this task:
  <list the specific source files>

<any additional context about the current state, gotchas, or decisions made>
```

**Why small chunks:** Context compression degrades quality. A fresh session that reads the initiative docs picks up exactly where the last one left off. Trying to push through too much in one session risks errors in the later work. If a task is small (trivial effort), do several in one session. If a task touches many files or requires careful reasoning, do just that one.

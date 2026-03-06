# Firmware Architecture Refactor

## Intent

Review and refactor the Motion Play firmware codebase from the perspective of a senior C/C++ engineer. The firmware grew organically during feature development and needs structural improvements: decomposing oversized files, applying C best practices, improving header hygiene, and ensuring dual-core safety patterns are sound.

## Goals

- No source file exceeds ~300 lines (soft limit: 600 max)
- Each file/class has a single, clear responsibility
- Clean module boundaries with minimal coupling
- Consistent naming, error handling, and memory safety patterns
- Dual-core (Core 0 sensor loop / Core 1 networking) concurrency is provably safe
- Zero functional regressions — refactoring only, no feature changes

## Scope

What's in:
- All active firmware source under `firmware/src/` and `firmware/include/`
- Structural decomposition of oversized files (main.cpp, SensorManager, DisplayManager, etc.)
- Header hygiene (include guards, forward declarations, minimal header includes)
- Naming, const-correctness, error handling improvements
- Identification of concurrency hazards

What's out:
- Feature additions or algorithm changes
- Hardware driver rewrites (VCNL4040 driver is a vendor-derived file — light touch only)
- Archive files (`firmware/src/archive/`)
- Auto-generated files (`model_data.h`)
- Build system or dependency changes (unless required by file moves)

## Constraints

- Must compile and run identically after each refactoring step — no behavior changes
- ESP32-S3 / Arduino / PlatformIO toolchain
- Dual-core architecture must be preserved (Core 0 = sensors, Core 1 = networking)
- PSRAM usage patterns must remain compatible
- Changes should be incremental and testable, not a big-bang rewrite

## Session Handoff

When starting a new chat session for this initiative, use this prompt:

```
I'm working on the firmware refactor initiative for the Motion Play project.

Please read these files to get oriented:
- .context/PROJECT.md
- firmware/CONTEXT.md
- docs/initiatives/firmware-refactor/BRIEF.md
- docs/initiatives/firmware-refactor/PLAN.md
- docs/initiatives/firmware-refactor/TASKS.md

Pick up from where TASKS.md left off. Read the next unfinished batch of files
listed in TASKS.md, analyze them from the perspective of a senior C/C++ lead
engineer, and document your findings in PLAN.md under the appropriate Module
Analysis section. Check off the batch in TASKS.md when done.
```

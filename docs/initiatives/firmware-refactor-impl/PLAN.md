# Firmware Architecture Refactor — Implementation Plan

## Approach

This initiative implements the recommendations from the firmware architecture audit (`docs/initiatives/firmware-refactor/REPORT.md`). Work is organized into four phases, each a natural stopping point. The codebase is strictly better after each completed phase — later phases can be deferred without harm.

The detailed analysis for every recommendation (line numbers, code patterns, risk notes, dependencies) lives in the audit's PLAN.md (`docs/initiatives/firmware-refactor/PLAN.md`). This document covers execution strategy only — consult the audit docs for the "why" behind each task.

### Execution Principles

- **One compilable step at a time.** Every task in TASKS.md should leave the firmware in a compilable, flashable state. If a task can't be done atomically, break it into sub-tasks.
- **Verify after each step.** Compile. If the change touches runtime behavior, flash and test. Don't batch untested changes.
- **Small sessions, clean handoffs.** A chat session handles one task (or a few trivial ones). Session ends with a commit and a handover prompt. See BRIEF.md for the handover format.

### Phase Strategy

**Phase 1: Foundation** creates shared infrastructure (type headers, constants, logging). These are mostly new files and include-statement changes — minimal modification of existing logic. Low risk, high leverage. Everything in later phases is easier once these exist.

**Phase 2: Correctness & Safety** fixes actual bugs and hazards. Each task is a targeted fix — a few lines changed in one or two files. The `StatsAccumulator` overflow (2.1) is the highest-priority item in the entire initiative because it produces corrupt calibration data today.

**Phase 3: Structural Decomposition** is the core work. Files get split, classes get extracted, responsibilities get redistributed. Each extraction is independent unless noted — e.g., DataTransmitter decomposition doesn't depend on main.cpp decomposition. But some tasks have prerequisites:
- 3.9 (IDetector + DetectionController) depends on 1.2 (DetectionTypes.h)
- 3.2 + 3.3 (SensorManager MuxController/VCNL4040 adoption) are the riskiest tasks — they replace the Core 0 hot path's I2C implementation. The audit's PLAN.md Batch 2 §10 documents three specific behavioral differences that must be preserved.
- 3.7 (CommandHandler) is the single largest extraction (~800 lines). It should be done in sub-steps: extract one command group at a time rather than all at once.

**Phase 4: Behavioral Improvements** changes how things work at runtime. These require testing beyond "does it compile" — network failure scenarios, timing verification, etc.

### Verification

For Phase 1-2 tasks: compile is sufficient (no behavioral change).

For Phase 3 tasks: compile + flash + verify the affected feature works (e.g., after extracting CommandHandler, verify that cloud commands still function; after adopting MuxController in SensorManager, verify sensor readings match pre-refactor values).

For Phase 4 tasks: compile + flash + test the specific scenario (e.g., after non-blocking reconnection, verify that WiFi drop doesn't freeze the display; after cooperative batching, verify that full sessions transmit correctly).

## Technical Notes

### Creating Type Headers (Phase 1)

When extracting types into new headers (SensorTypes.h, DetectionTypes.h, InterruptTypes.h):
1. Move the type definitions to the new header
2. Add `#include "NewTypes.h"` to the original header
3. Update all files that used the types via the original header — most won't need changes because they still get the types transitively
4. Then, in files that only needed the types (not the full class), replace the heavy include with the lightweight one
5. Compile after each step

### SensorManager Unification (Phase 3, tasks 3.2-3.3)

This is the highest-risk refactoring. The audit identified three behavioral differences between SensorManager's raw I2C code and the VCNL4040 driver:

1. **Full-register-write vs read-modify-write:** SensorManager builds entire register values from scratch. The driver uses `bitMask()` (read-modify-write). During migration, either zero-initialize registers first or add a `configureForPolling()` method.
2. **Verify-then-retry on LED current:** SensorManager has custom retry logic for LED current that the driver lacks. Must be preserved.
3. **Mode transition cleanup:** Switching from interrupt mode to polling must explicitly clear interrupt-related register bits.

Read audit PLAN.md Batch 2 §10 for full details before starting these tasks.

### main.cpp Decomposition (Phase 3, tasks 3.7-3.11)

The recommended approach for CommandHandler extraction (3.7) is to do it incrementally:
1. Create the CommandHandler class with a reference to each manager it needs
2. Move one command group at a time (e.g., all session commands first, then config commands, then detection commands)
3. Compile and test after each group
4. main.cpp's `handleCommand()` shrinks incrementally — it's never in a half-broken state

## Open Questions

- None currently. All technical questions were resolved during the audit phase. New questions will be added here as they arise during implementation.

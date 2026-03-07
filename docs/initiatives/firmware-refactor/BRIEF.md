# Firmware Architecture Audit

> **Note:** This initiative was originally scoped as "Firmware Architecture Refactor" covering both audit (Phase A) and implementation (Phase B). During Phase A we recognized that the audit is a self-contained deliverable — its findings should inform a properly scoped follow-on initiative rather than an open-ended "Phase B." The scope was revised to audit-only. See REPORT.md for the synthesized findings and recommendations for the follow-on initiative.

## Intent

Audit the Motion Play firmware codebase from the perspective of a senior C/C++ engineer. The firmware grew organically during feature development. This initiative systematically reviews every active source file, documents structural issues, and produces a prioritized report of findings to inform future refactoring work.

## Goals

- Review all active firmware source files (~12,000 lines across 30+ files)
- Document single-responsibility violations, code duplication, error handling gaps, concurrency hazards, header hygiene issues, magic numbers, dead code, and API design problems
- Produce a synthesized report (REPORT.md) with prioritized, actionable recommendations
- Recommend how to structure a follow-on refactoring initiative

## Scope

What's in:
- All active firmware source under `firmware/src/` and `firmware/include/`
- Batch-by-batch detailed analysis (documented in PLAN.md)
- Cross-cutting review: header hygiene, include chains, shared constants, global state
- Synthesized findings and recommendations (REPORT.md)

What's out:
- Implementation of any refactoring (that's the follow-on initiative)
- Feature additions or algorithm changes
- Hardware driver rewrites (VCNL4040 driver is a vendor-derived file — light touch only)
- Archive files (`firmware/src/archive/`)
- Auto-generated files (`model_data.h`)

## Constraints

- Analysis only — no code changes
- Findings must be specific and actionable, not vague observations
- Recommendations must preserve: ESP32-S3 / Arduino / PlatformIO toolchain, dual-core architecture (Core 0 = sensors, Core 1 = networking), PSRAM usage patterns

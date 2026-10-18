# RELAY — research session — testing workflow audit (DRAFT)

> Informal research session, no agent role. Launch with default `claude`. See `docs/research/v7-retry/RESEARCHER.md` for conventions.

## Context

During prior v7 debugging, the user did significant oscilloscope work — soldering probe wires onto traces, capturing waveforms, logging measurements. The retry will do more of this. The current workflow has friction: unclear filename conventions, scattered image placement, no standard measurement log format, no test-card template, and no documented procedure for the user's specific scope model.

This session is topic 4 of 6 in Stage A. The goal is to produce a workflow proposal that reduces friction and makes test results easy for future AI sessions to ingest.

## Load these files

- `docs/research/v7-retry/RESEARCHER.md` — conventions
- `docs/debugging/i2c-oscilloscope-debugging.md` — current scope workflow doc
- `docs/debugging/v7-i2c-investigation.md` — how test results have been logged in practice
- Any image/capture files already in `docs/debugging/` (or elsewhere) — check `find docs -name "*.png" -o -name "*.jpg" -o -name "*.bmp"`
- The user is the primary source for parts of this — scope model, workflow preferences, physical setup. Ask early.

## Produces

**Artifact path:** `docs/research/v7-retry/test-workflow-audit.md`

Suggested structure:

1. **Current state** — document what the workflow looks like today based on the inputs, warts and all. Short.
2. **Friction points observed** — concrete, specific. Each with evidence (file reference or prior-session anecdote).
3. **Proposals** — one section per element below. For each: recommendation, rationale, and a snippet/template if applicable.
   - **Scope model + its quirks.** Document the user's specific oscilloscope, including: model, probe configuration, trigger quirks, screenshot export mechanism, any SCPI/network control support. If the scope supports programmatic control, flag it as a tooling opportunity (feeds into topic 3 or 6).
   - **Filename convention** for scope captures. Suggested starting point: `YYYY-MM-DD_<test-id>_<probe-channel>_<signal-name>.png`. Refine with user.
   - **Capture location** — one directory per test, or one flat directory with disciplined names? Needs to be easy for an AI session to reference without ambiguity.
   - **Measurement log format** — structured (YAML/TOML/JSON) so sessions can parse without heuristics. Include minimal required fields and optional ones.
   - **Test card template** — the single most important element. Hypothesis → Prediction (what the scope should show if the hypothesis is true) → Setup → Procedure → Expected pass/fail → Actual → Interpretation. The Prediction is filled in *before* the test runs.
   - **How the user receives instructions** from an AI session. Right now: ad-hoc chat. Proposal: structured step-by-step with explicit "do this physically / expect this result / report back". Reduces the user's cognitive load during the test itself.
   - **Image handoff** — how does an AI session read a capture the user just took? Confirm file-path handoff flow with the user; propose a standard if ad-hoc today.
4. **Tooling opportunities** — things that would reduce friction further but need their own work (SCPI integration, measurement-logger CLI, test-card scaffolder). Flag; do not build.
5. **Does this spawn an implementation initiative?** Direct answer. Probably yes — "test-workflow setup" is a natural follow-on initiative.

## Scope

**In:**
- Documenting current workflow
- Identifying friction points
- Proposing conventions, templates, and formats
- Writing the artifact

**Out:**
- Building any tools
- Modifying any scripts
- Changing anything in `docs/debugging/` (except as a flagged recommendation)
- Running any oscilloscope test
- Any physical hardware work

## What was done before this relay

- `adopt-protocol` initiative merged
- Framework for v7 retry agreed; this is topic 4 of 6
- Topics 1 and 2 may be complete and have context on what friction specifically bit us last time — read them if available

## Your task

Produce `docs/research/v7-retry/test-workflow-audit.md` per the structure above.

**Expected first move:** before doing anything else, ask the user about their scope. Specifically: make/model, how they export captures today, whether it has USB/LAN SCPI support, what probe set they have, and any specific pain points they remember. Scope model and quirks drive several of the subsequent recommendations.

**Expected second move:** read the prior debugging docs and look at how test results were actually recorded. Spot the inconsistencies — those are the friction points.

Keep the proposals specific enough to adopt without further design. Don't produce vague "we should have a template" — produce a concrete starting template with real field names.

## Context-pressure behavior

At ~60% context: finish the current section, commit `WIP:`, write `docs/research/v7-retry/RELAY-test-workflow-audit-continue.md`, and stop.

## Open questions to surface

- **Scope model + capabilities** — must come from the user.
- **Where captures should live** — in the repo (committed), in a sibling folder (gitignored), on cloud storage? Confirm with user.
- **How much programmatic scope control to recommend** — depends on scope support and user's appetite for building tooling.
- **Who owns the test-workflow docs after this** — if it spawns an implementation initiative, confirm expected scope with the user before writing recommendations that pre-commit it.

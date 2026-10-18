# RELAY — research session — v7 debug post-mortem (DRAFT)

> Informal research session, no agent role. Launch with default `claude`. See `docs/research/v7-retry/RESEARCHER.md` for conventions.

## Context

Months ago we hit a wall debugging the v7 main PCB (ESP32-S3-on-board redesign of a working T-Display-based board). After many sessions we couldn't repeatably isolate a fault and set the project aside. We are now kicking off a retry. This session is topic 1 of 6 in Stage A — a methodological post-mortem of the prior debugging work, before any new debugging begins.

The intent is **not to re-debug**. The intent is to understand *how* we went about it so we can do it better this time. If this session is tempted to form new hypotheses or test ideas, stop — that is out of scope.

## Load these files

- `docs/research/v7-retry/RESEARCHER.md` — conventions
- `docs/debugging/v7-i2c-investigation.md` — main investigation record
- `docs/debugging/v7-i2c-session-resume.md`
- `docs/debugging/v7-i2c-fresh-perspective-prompt.md`
- `docs/debugging/i2c-oscilloscope-debugging.md`
- `docs/explorations/esp32-s3-i2c-master-deep-dive.md`
- `docs/explorations/bq_solder_sda-catmull.md`
- `git log --all --oneline | grep "v7-i2c-debug"` — look at commits in the Phase 1–18 range for a sense of sweep and sequencing

## Produces

**Artifact path:** `docs/research/v7-retry/postmortem.md`

A methodological audit. Structure suggestion (adjust if you find a better frame):

1. **Session timeline summary** — one paragraph, how many sessions, what phases, roughly what happened.
2. **Hypotheses chased** — for each distinct hypothesis the prior work pursued, a scored assessment:
   - Was it falsifiable before testing?
   - Did we commit to the pass/fail criterion *before* the test?
   - Did we change one variable per test, or several?
   - Was the conclusion "no evidence for X" (weak) or "positive evidence against X" (strong)?
3. **What we did well** — explicit list. The retry should keep these. Don't skip this section; a post-mortem that only names mistakes causes overcorrection.
4. **What went wrong, methodologically** — specifically about *process*, not about the hardware. Candidates to look for: hypothesis sprawl without falsification criteria, reasoning from absence of evidence, session discontinuity (relitigating prior context), confirmation bias, multi-variable changes between tests, no clean separation of signal/power/firmware failure modes.
5. **Patterns that recurred across sessions** — things that happened in session N, then again in session N+3, etc.
6. **Recommendations for the retry** — concrete process rules we should adopt. These feed into topic 6 (context strategy) and the eventual synthesis session.

## Scope

**In:**
- Reading the prior debugging docs and commit history
- Characterizing methodology, decision quality, and process patterns
- Writing the artifact

**Out:**
- Forming new hypotheses about the actual hardware fault
- Running any tests
- Changing any code, scripts, schematics, or firmware
- Analyzing structured data outputs (that's topic 3)
- Comparing v6 vs v7 designs (that's topic 2)

## What was done before this relay

- `adopt-protocol` initiative merged — new protocol installed
- Research/ideation session agreed on Stage A structure (six topics, this is topic 1)
- This relay is a pre-launch draft; the user may have edited it before you see it

## Your task

Produce `docs/research/v7-retry/postmortem.md` per the structure above. Work through the inputs in a sensible order (probably investigation doc → session resume → explorations → commit log). Be honest and specific — a vague post-mortem is useless.

Before you finalize the artifact, briefly surface the top 3–5 process findings to the user for a sanity check. They lived through these sessions and will catch mischaracterizations faster than you can self-audit.

## Context-pressure behavior

At ~60% context, if the artifact isn't complete: finish the current section, commit `WIP:`, write `docs/research/v7-retry/RELAY-postmortem-continue.md` describing what's done, what's partial, what to load next, and stop.

## Open questions to surface, if relevant

- The prior debugging appears to span 18+ phases. If the input docs are long enough to pressure context, which sections to prioritize?
- The user's memory system (see `/Users/marcocleirigh/.claude/projects/-Users-marcocleirigh-Workspace-motion-play/memory/MEMORY.md`) carries some v7 debug context — load if useful.
- Is there a specific hypothesis you want to call out that the user is skeptical of in retrospect? Ask them when sanity-checking.

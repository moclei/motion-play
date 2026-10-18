# RELAY — research session — expert approaches to PCB bring-up debug (DRAFT)

> Informal research session, no agent role. Launch with default `claude`. See `docs/research/v7-retry/RESEARCHER.md` for conventions.

## Context

Prior v7 debugging drifted — many hypotheses chased, nothing conclusively isolated. Before resuming, we want a concise set of principles for how experienced hardware engineers approach the specific class of problem we face: *a design that was working, was redesigned, and now doesn't work, with intermittent/ambiguous symptoms on a digital bus*.

This session is topic 5 of 6 in Stage A. It is primarily a **web research session**. The deliverable is a distilled principles doc that will inform topic 6 (context strategy) and the eventual debug sessions.

## Load these files

- `docs/research/v7-retry/RESEARCHER.md` — conventions
- `docs/research/v7-retry/postmortem.md` — **if complete**; the methodological gaps named there should guide what principles to prioritize.

Minimal local reading. The main inputs come from the web.

## Produces

**Artifact path:** `docs/research/v7-retry/expert-approaches.md`

Suggested structure:

1. **Scope statement** — a sentence or two restating the problem class we are researching for. Keeps the artifact focused.
2. **Principles** — 6–12 of them, each with:
   - Name (short, memorable)
   - What it says (two to four sentences)
   - Why it works
   - How to apply it to our specific situation
   - Source(s) — real citations, not vague
3. **Techniques** — more concrete than principles. Candidates to investigate; adopt only those with real backing:
   - Golden-board A/B comparison (we have a working v6)
   - Signal-chain partitioning (power → reset → clock → bus activity → protocol → firmware)
   - Minimum reproducing subset (depopulate until it works, repopulate one at a time)
   - Shotgunning (what it means and when it's actually appropriate)
   - "Half-splitting" and binary isolation
   - Written falsification criteria before each test
   - Pre-registered predictions (the test-card discipline)
4. **Anti-patterns** — things experts specifically warn against. Candidates: reasoning from absence of evidence, confirmation bias, changing multiple variables per test, "I bet it's X" without a test, chasing intermittents without environmental control.
5. **Decision frameworks** — when to stop debugging and redesign; when to escalate to a consultant; when to post to a forum. Explicit heuristics with sources.
6. **Reading list** — short, curated. 3–8 references. Not every blog post that mentions the topic; the ones a thoughtful engineer should actually read.

## Scope

**In:**
- Web research (EEVblog, Horowitz & Hill *Art of Electronics*, hardware engineering blogs, textbook methodology, forum conventions)
- Distilling into principles directly applicable to our problem class
- Writing the artifact

**Out:**
- Applying any principle to the actual v7 bug
- Running any tests
- Modifying any code or scripts
- Over-generalizing — if a principle doesn't apply to "working-then-broken redesign with ambiguous bus symptoms", leave it out

## What was done before this relay

- `adopt-protocol` initiative merged
- Topic 1 (post-mortem) may or may not be complete — if it is, use its findings to prioritize which principles matter most for *our* failure modes
- Framework for v7 retry agreed; this is topic 5 of 6

## Your task

Produce `docs/research/v7-retry/expert-approaches.md` per the structure above.

**Expected first move:** narrow the search. "How to debug PCBs" is too broad; "how to debug a working-then-broken redesign with ambiguous I²C symptoms" is the real question. Draft a few concrete search queries aimed at this class of problem.

**Expected second move:** triangulate. One source saying something isn't enough. Prefer principles backed by multiple reputable sources, or by one highly credible source (textbook, well-known engineer).

**Keep the artifact tight.** 6–12 principles is a working ceiling. If you have 25, you're copy-pasting; distill.

## Context-pressure behavior

At ~60% context: finish the current section, commit `WIP:`, write `docs/research/v7-retry/RELAY-expert-approaches-continue.md`, and stop.

Note: web-heavy sessions can burn context fast on fetches. Be deliberate about which pages you load in full vs. skim.

## Open questions to surface

- **Narrowing the scope** — surface the specific problem-class framing to the user before deep research. If they want to broaden ("I also want to learn about general bring-up discipline"), the artifact scope grows.
- **Source quality bar** — confirm with the user how strict to be about citations. If they want this to be adoptable with confidence, bar is high.
- **Overlap with topic 1** — the post-mortem may already have named "what we should have done." This artifact should complement, not duplicate.

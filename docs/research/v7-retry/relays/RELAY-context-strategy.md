# RELAY — research session — context strategy for v7-retry sessions (DRAFT)

> Informal research session, no agent role. Launch with default `claude`. See `docs/research/v7-retry/RESEARCHER.md` for conventions.

## Context

The eventual v7 retry debugging will span many sessions. In the prior round, each new session had to re-derive context from scratch — reading long investigation docs, relitigating ruled-out hypotheses, re-anchoring to the user's physical setup. That drag was a significant cost. This session designs a context strategy that avoids it.

This session is topic 6 of 6 in Stage A — the **last** research session, intentionally. It should run after the other five are complete because it synthesizes patterns from them: what information the postmortem says we lose across sessions, what the changelist says the "always-load" suspect list looks like, what the extraction audit says we have vs. need, what the workflow audit says a test record looks like, what expert approaches say about session discipline.

## Load these files

Preferably **after** topics 1–5 are complete:

- `docs/research/v7-retry/RESEARCHER.md` — conventions
- `docs/research/v7-retry/postmortem.md`
- `docs/research/v7-retry/v6-v7-changelist.md`
- `docs/research/v7-retry/kicad-extraction-audit.md`
- `docs/research/v7-retry/test-workflow-audit.md`
- `docs/research/v7-retry/expert-approaches.md`
- `.context/PROTOCOL.md` — protocol context mechanisms (SESSION.md, TASKS.md, Relay)
- `.context/PROJECT.md`
- `CLAUDE.md`

## Produces

**Artifact path:** `docs/research/v7-retry/context-strategy.md`

This artifact is a **design**. It describes how debug sessions should be structured so that any new session can productively engage with ~2 pages of reading plus on-demand lookups.

Suggested structure:

1. **Problem statement** — what we are solving for. Short.
2. **The context pyramid** — three tiers:
   - **L0 — always loaded** (via CLAUDE.md or equivalent): what every debug session needs on first message. Target: < 500 lines total. Candidates: PROTOCOL/PROJECT; a `V7-DEBUG-BRIEF.md`; current `STATE.md`.
   - **L1 — loaded on relevance**: the full changelist, latest test card(s), extraction output for the current subsystem. Named explicitly so a session knows to request them.
   - **L2 — fetched on demand**: all historical investigation docs, old captures, prior session logs. Keyed by index.
3. **Entry doc design** — specify the structure of the one doc every new debug session reads. "If you only read one file" — routing + current state, not content dump. Mock up its exact sections.
4. **State document** — the one-page live snapshot updated at the end of every debug session (current working theory, last test outcome, next test). Mock it up with field definitions.
5. **Session log** — append-only, one short paragraph per session. Specifies what each entry looks like.
6. **Test cards** — reference the format defined in `test-workflow-audit.md`; specify how they integrate into the context pyramid (e.g., "the two most recent test cards live at L1").
7. **Compaction/handoff rule for debug sessions** — context-pressure behavior analogous to the Worker rule but adapted for debug sessions (which are interactive, not autonomous).
8. **Does this fit under existing protocol or need a new mechanism?** Direct answer. Options: (a) each debug session is an informal session like this track's research sessions; (b) debug becomes a formal role (`debugger` or similar); (c) each debug phase is a tiny initiative. Make a recommendation and name the tradeoffs.
9. **Does this spawn an implementation initiative?** Direct answer. Likely yes — a "v7-debug-prep" initiative that creates the entry doc, state doc, templates, and any directory scaffolding.

## Scope

**In:**
- Reading the other five Stage A artifacts
- Designing the context layout, templates, and session discipline for the retry debug sessions
- Making a recommendation about debug-session role formalization

**Out:**
- Starting any debugging
- Implementing templates, scripts, or scaffolding
- Modifying `.context/PROTOCOL.md` (that would be a protocol-level change — surface, don't do)

## What was done before this relay

- `adopt-protocol` initiative merged
- Topics 1–5 ideally complete; if some aren't, flag which are missing and either wait or proceed with reduced input (surface to user)

## Your task

Produce `docs/research/v7-retry/context-strategy.md` per the structure above.

**Expected first move:** check which prior artifacts exist. If any are missing, surface to the user; don't proceed as if you have the input you don't.

**Expected second move:** draft the entry doc structure (section 3) first — it anchors everything else. Then work outward: L0 content → L1 → L2 → state → log → cards → handoff.

**Expected third move:** sanity-check against the postmortem. If the postmortem said "we kept relitigating X across sessions", the strategy must demonstrably solve for X.

## Context-pressure behavior

At ~60% context: finish the current section, commit `WIP:`, write `docs/research/v7-retry/RELAY-context-strategy-continue.md`, and stop.

## Open questions to surface

- **Should debug sessions become a formal role?** This is a design decision the user needs to make. Present options with tradeoffs.
- **Where does the entry doc live?** `.context/V7-DEBUG-BRIEF.md`? Inside an initiative folder? Confirm with user.
- **Is the retry a single long debug track, or several bounded initiatives in sequence?** Changes how continuity should be structured. Surface for user decision.

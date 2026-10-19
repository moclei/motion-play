# RELAY — research session — context strategy for v7-retry sessions (DRAFT)

> Informal research session, no agent role. Launch with default `claude`. See `docs/research/v7-retry/RESEARCHER.md` for conventions.
>
> Revised 2026-10-18 after topics 1–5 completed. The load list is now targeted by section, and the specific questions that topics 1–5 handed to this topic are listed under "Inputs handed to this topic".

## Context

The v7 retry debugging will span many sessions. In the prior round, a fresh session following the resume prompt loaded ~70–80k tokens of history before doing anything. Most of it was superseded reasoning, and the investigation doc (~56k tokens) tried to be both lab notebook and briefing (post-mortem §4.10). Handoff artefacts drifted apart and encoded bias (§4.6). This session designs a context strategy that avoids both.

This session is topic 6 of 6 in Stage A, the last. Topics 1–5 are **complete**:
- Topic 1 diagnosed the context failures.
- Topic 4 defined the test record formats.
- Topics 2, 3 and 5 each produced content that some tier of the context must carry.

**This session designs containers, not their contents.** Writing the hypothesis map, ranking hypotheses or sequencing initiatives is the Stage B synthesis session's job (`decisioning.md`). Don't do it here.

## Load these files

Load targeted sections, not whole documents. Loading everything would repeat the anti-pattern this session exists to fix (post-mortem §4.10). Use `grep -n "^#"` to find headings and read by offset.

**Read in full:**
- `docs/research/v7-retry/RESEARCHER.md`: conventions.
- `.context/PROTOCOL.md`: Relays, SESSION.md, TASKS.md, and the escalation/context-pressure rules you'd be adapting.
- `CLAUDE.md` and `.context/PROJECT.md`: what is auto-loaded today.
- `~/.claude/projects/-Users-marcocleirigh-Workspace-motion-play/memory/MEMORY.md` and the two v7 notes it indexes (`project_v7_i2c_bq_debug.md`, `project_pcb_revision_apr2026.md`). Memory is auto-loaded into every session, so it is part of L0 whether we design it or not.

**Read only the named sections:**
- `postmortem.md`:
  - §4.6 (handoff decay), §4.9 (no synthesis), §4.10 (context budget);
  - §5 (recurring patterns: the "summary sections not updated" row);
  - §6 recommendations 13–14 and 16–20 (the **→6** set);
  - "Observations for other topics".
- `test-workflow-audit.md`:
  - §2.6 (audit summary table) and §2.5 (firmware baseline table): candidates for always-loaded state;
  - §4.4–§4.9 (filenames, capture layout, log, test card, instruction block, image handoff);
  - "Observations for other topics".
- `expert-approaches.md`:
  - P1 (IS / IS NOT table), P7 (logbook), P10 (symptoms, not theories);
  - §4 Anti-patterns;
  - "Observations for other topics".
- `kicad-extraction-audit.md`: TL;DR, §6.1 (only to see what the board-model initiative will output), and "Observations for other topics".
- `v6-v7-changelist.md`: §5 Observations (the short suspect list). Scan the §3 table's shape (how many CLs, columns) without reading every row. It is a candidate L1 document.
- `docs/debugging/`: **headings only** of `v7-i2c-investigation.md`, `v7-i2c-session-resume.md` and `v7-i2c-fresh-perspective-prompt.md`. These are the existing handoff artefacts the strategy must place in a tier or retire. Do not read their bodies.

## Inputs handed to this topic

Each item needs an explicit answer in the artifact.

**From topic 1 (post-mortem):**
1. Split the briefing from the notebook. The current-state file is ≤ ~3–5k tokens; the notebook is append-only and loaded only for lookups (rec 16).
2. One handoff artefact, retired when superseded (rec 17). Decide the fate of the investigation doc, the resume prompt, the fresh-perspective prompt and the scope guide.
3. Handoffs carry state, not interpretation (rec 18).
4. Refuted hypotheses get one-line tombstones (rec 19).
5. Commit after every test result, with stable IDs (rec 20).
6. The hypothesis map and the periodic "step back" checkpoint (recs 13–14) need a home and an update trigger.
7. The ~56k-token investigation doc is the concrete anti-pattern to design against.
8. Summary sections went stale because nothing forced an update when a phase landed (§5). The design needs a mechanism, not a good intention.

**From topic 4 (test workflow):**
9. Topic 4 owns the formats of the test card (§4.7), the measurement log (§4.6) and the capture split (§4.5). **Topic 6 decides:**
   - where `lab/` lives in the repo;
   - where cards and logs are stored;
   - which cards a session loads by default;
   - where the single `V7R-NNN` test-ID counter lives.
10. Whether the audit summary (§2.6) and the declared baselines (`v7-clean` / `v6-ref`, §2.5) belong in the current-state file.
11. How a session gets a capture image into context (§4.9). Which tier do captures sit in, and what does the session write down after reading one?

**From topic 3 (KiCad audit):**
12. Route narratives and per-net images are the right unit of layout context; raw coordinate JSON isn't.
13. Every generated context file needs a source hash. Two stale committed outputs went unflagged.
14. The `tools/CONTEXT.md` rule "never read `.kicad_pcb`" blinds sessions to zones and stackup. Until the board-model initiative lands, should targeted read-only kiutils probes be explicitly allowed?

**From topic 5 (expert approaches):**
15. Raymond's "symptoms, not guesses" as a rule for handoff prompts.
16. The IS / IS NOT table (P1) as a candidate standing section of the current-state file.

**Housekeeping found along the way** (decide the mechanism; don't edit the files in this session):
17. Memory notes are auto-loaded and stale:
    - `project_v7_i2c_bq_debug.md` names a refuted top hypothesis (topic 1).
    - `project_pcb_revision_apr2026.md` is wrong on three points (topic 2).

    What role, if any, should auto-memory play for v7 debug state, and how is it kept from drifting?

## Produces

**Artifact path:** `docs/research/v7-retry/context-strategy.md`

A **design** for how debug sessions are structured, so that a new session can engage productively from ~2 pages of reading plus named on-demand lookups.

Suggested structure:

1. **Problem statement.** Short, citing post-mortem §4.6 and §4.10.
2. **The context pyramid:**
   - **L0, always loaded** (CLAUDE.md, auto-memory, or a named entry doc), target < ~500 lines in total;
   - **L1, loaded on relevance**, each document named so a session knows to ask for it;
   - **L2, fetched on demand by index**.

   Place every existing artefact in a tier or mark it retired, including the `docs/debugging/` files, the topic 1–5 research docs, test cards, captures, extraction outputs and memory notes.
3. **Entry doc design.** The one file every debug session reads first, covering routing and current state, not a content dump. Mock up its exact sections.
4. **Current-state document.** A one-page live snapshot. Mock it up with field definitions. Address inputs 1, 4, 6, 10 and 16. Define the **update trigger**: what event forces an update, and how a stale state file is detected (input 8).
5. **Session log / lab notebook.** Append-only, with the entry format defined. Say how it relates to test cards so results aren't written twice.
6. **Test cards, log and captures in the pyramid.** Answer inputs 9 and 11: locations, the default-load rule (e.g. "the open card plus the last two recorded cards at L1"), and where the counter lives.
7. **Handoff and compaction rule for debug sessions.** Context-pressure behaviour adapted for interactive, user-at-the-bench sessions, plus what a handoff may and may not contain (inputs 3 and 15).
8. **Generated context.** The source-hash rule and the kiutils-probe question (inputs 12–14).
9. **Protocol fit.** A direct answer with tradeoffs:
   - (a) debug sessions stay informal, like this research track;
   - (b) a formal `debugger` role in `.claude/agents/`;
   - (c) each test or test batch is a tiny initiative.

   Recommend one.
10. **Does this spawn an implementation initiative?** A direct answer. If yes, follow the topic 3/4 pattern: a §"Input for the Planner" (goal, in/out of scope, acceptance criteria, dependencies, decisions for the user), plus a draft `RELAY-planner.md`. **Do not write phases; phasing is the Planner's job.**
    - Flag overlap with `test-workflow-setup` (topic 4 §6), which already creates the card, log and capture templates. Say whether this work merges into that initiative or stays separate, as a recommendation.
    - Sequencing between initiatives is decided in `decisioning.md`, not here.

## Scope

**In:**
- Reading the named sections of topics 1–5 and the protocol/auto-load files
- Designing the context layout, templates, update triggers and session discipline for retry debug sessions
- Recommending a protocol fit and a fate for each existing handoff artefact and memory note
- Writing the artifact, including Planner input and a draft relay if an initiative is recommended

**Out:**
- Starting any debugging; writing the hypothesis map's content or ranking hypotheses (Stage B)
- Implementing templates, scripts, scaffolding or directories
- Editing `.context/PROTOCOL.md`, `CLAUDE.md`, memory files or anything in `docs/debugging/`. Surface these as recommendations.
- Phasing any initiative, or sequencing initiatives against each other

## What was done before this relay

- `adopt-protocol` initiative merged.
- **Topic 1 (post-mortem): complete.** Diagnosed handoff decay and orientation cost; gave recommendations 16–20 (→6).
- **Topic 2 (changelist): complete.** Produced a short suspect list (§5) and a ~26-row changes table, a natural L1 document.
- **Topic 3 (KiCad audit): complete.** Recommends a board-model initiative whose outputs are route narratives, per-net images and diffs, with source hashes. A draft Planner relay is in its §6.2.
- **Topic 4 (test workflow): complete.**
  - Defined the test card, YAML log, filenames, capture split, instruction block and image handoff.
  - Recommends a `test-workflow-setup` initiative, with Planner input and a draft relay in §6. Its sequencing is left to `decisioning.md` by user decision; its open decisions are left for its Planner.
- **Topic 5 (expert approaches): complete.** Gave the logbook, symptoms-not-theories and IS/IS NOT sources.

## Your task

Produce `docs/research/v7-retry/context-strategy.md` per the structure above. Answer every numbered input, or explicitly defer it to Stage B with a reason.

**Expected first move:** after loading, ask the user the open questions below that change the design (role formalisation, entry-doc location, single track vs a sequence of initiatives, and the role of auto-memory). Ask them early; they decide the shape of §3 and §9.

**Expected second move:** draft the entry doc (§3) and the current-state doc (§4) first, since they anchor everything else. Then work outward: L0 → L1 → L2 → log → cards/captures → handoff → generated context.

**Expected third move:** check the design against post-mortem §4.6, §4.10 and the §5 "summary sections not updated" row. For each failure named there, show which element of the design prevents it. Then do a budget check: estimate the token cost of L0 as designed and confirm it is under the target.

## Context-pressure behavior

At ~60% context: finish the current section, commit `WIP:`, write `docs/research/v7-retry/RELAY-context-strategy-continue.md`, and stop.

## Open questions to surface

- **Should debug sessions become a formal role?** A design decision for the user. Present the options with tradeoffs.
- **Where does the entry doc live?** `.context/V7-DEBUG-BRIEF.md`, inside an initiative folder, or elsewhere? Confirm with the user.
- **Is the retry a single long debug track, or several bounded initiatives in sequence?** This changes how continuity is structured. Surface it for user decision; final sequencing is still `decisioning.md`'s.
- **Auto-memory for v7 state: use it, restrict it to pointers, or keep v7 state out of it?** The current notes show the drift risk.
- **Where `lab/` lives** (topic 4 handed this over). Confirm with the user.

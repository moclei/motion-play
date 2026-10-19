# RELAY — research session — Stage B synthesis (DRAFT)

> Informal research session, no agent role. Launch with default `claude`. See `docs/research/v7-retry/RESEARCHER.md` for conventions.
>
> Drafted 2026-10-18, after all six Stage A topics completed.

## Context

Stage A of the v7 retry is complete. Six topics each produced one artifact in `docs/research/v7-retry/`:
1. post-mortem (method);
2. v6→v7 changelist;
3. KiCad extraction audit;
4. test-workflow audit;
5. expert approaches;
6. context strategy.

Each one deliberately avoided forming or ranking fault hypotheses, and each one deferred certain decisions to this session.

This session is the **one place where the whole picture is synthesised**. It produces `decisioning.md`. That document:
- holds the first hypothesis map, IS / IS NOT table, tombstones and measurement-trust table, in the shapes topic 6 defined so they can be transcribed into `lab/STATE.md` unchanged;
- sequences the recommended initiatives;
- ends with a `RELAY-planner.md` for the first one.

The prior investigation failed through frame lock: one lead story at a time, tested from five angles, while the master side stayed unexplored (post-mortem §4.1, §4.9). **The map you write must cover the whole fault space, not argue for a favourite.**

## Load these files

Load targeted sections, not whole documents (topic 6 §2; post-mortem §4.10). Use `grep -n "^#"` to find headings and read by offset. The section lists below are the minimum. Go deeper by section when a specific decision needs it, and say so in the artifact.

**Read in full:**
- `docs/research/v7-retry/RESEARCHER.md`: conventions, including the Stage A → B transition.
- `docs/research/v7-retry/README.md`.
- `.context/PROTOCOL.md`: Relays (the `RELAY-planner.md` template), Initiatives.

**Read the named sections:**
- `postmortem.md`:
  - §1 (timeline);
  - §2 (hypotheses chased, scored): the main input for tombstones and the map's tested regions;
  - §4.1–§4.5, §4.9;
  - §5;
  - §6 (all recommendations);
  - Observations.
- `v6-v7-changelist.md`:
  - §1a (was v6 brought up?);
  - §3 (the full changes table; this is the search space, so read every row here);
  - §4 (undetermined changes);
  - §5;
  - Observations.
- `test-workflow-audit.md`:
  - §0 (what the user said);
  - §2.1 (physics sanity);
  - §2.3–§2.6 (per-result verdicts, Phase 25, baselines, summary);
  - §6 (initiative input);
  - Observations.
- `expert-approaches.md`:
  - §2 (P1–P11; skim the "What it says" and "Apply to us" paragraphs);
  - §4;
  - §5 (decision frameworks);
  - Observations, especially the ESP-IDF #8543 reference fact.
- `kicad-extraction-audit.md`:
  - TL;DR;
  - §3 (SDA acid test);
  - §6 (initiative input, including decision 4: "launch now or wait for decisioning");
  - Observations, especially the raw geometry facts.
- `context-strategy.md`:
  - user decisions at the top;
  - §4.1 (STATE.md section shapes: **write your map in these shapes**);
  - §4.4 (first fill);
  - §10 (merge recommendation and draft relay);
  - §12 (deferred to Stage B);
  - Observations.

**Legacy record, lookup only:** `docs/debugging/v7-i2c-investigation.md` and the two `docs/explorations/` I²C docs.
- Never load them whole, and never read their summary sections (Fastest read, TL;DR, Current working theory, Candidate fixes) as current.
- Grep for a specific phase heading when a map row needs its raw result.
- Cite legacy phases as `L-PhNN`, with `L-Ph24a` (Arduino-as-master) and `L-Ph24b` (Exp 1 glitch filter).

**Do not load:** `v7-i2c-session-resume.md`, `v7-i2c-fresh-perspective-prompt.md`, the auto-memory v7 notes. They are retired (topic 6 §2.4–§2.5) and encode interpretation.

## Inputs handed to this session

Each item needs an explicit answer in `decisioning.md`, or an explicit deferral with a reason.

**Content for `lab/STATE.md`** (topic 6 §4.4, §12), written in the §4.1 table shapes:
1. **Symptom** (STATE section 1): observable behaviour only, minimal repro. No mechanism words.
2. **IS / IS NOT** (section 2), built against the changelist (topic 5 P1). Every map row must explain both columns, or be marked as failing to.
3. **Hypothesis map** (section 3):
   - regions at least master / bus / mux / slave / power / firmware / measurement;
   - each row carries status (untested / argued / tested) and strength (measured-refuted / measured-supported / argued / not tested), with evidence IDs;
   - a region with no hypothesis is listed as such;
   - include the CL short list (changelist §5) as candidate distinctions.
4. **Facts in use** (section 4), with strength labels. Include the topic 3 raw geometry facts and the ESP-IDF #8543 reference fact *as facts*, with relevance "unassessed". Decide where the assumptions register (PM rec 12) goes: STATE section 4 rows, or its own file (topic 6 §12).
5. **Tombstones** (section 5): one line per refuted story from post-mortem §2, with strength. Apply topic 4's corrections:
   - G-revised is "measured-refuted, pending R1";
   - "BQ effective V_IL ~800–900 mV" is withdrawn;
   - Phase 25 is "not tested".
6. **Measurement trust** (section 7), seeded from topic 4 §2.6.
7. **Next** (section 8): the first tests, as card *titles*, each naming the map region it cuts. Don't write the cards themselves; that is the debug track's job once `lab/` exists. Topic 4 recommends R1 re-measurement first; confirm or override it with a reason.

**Decisions handed to this session:**

8. **Initiative sequencing.** The user decided on 2026-10-18 that `decisioning.md` sequences. Candidates:
   - `test-workflow-setup`, merged with topic 6's context scaffolding (topic 6 §10 recommends the merge: accept or reject);
   - the board-model initiative (topic 3, whose decision 4 asks "now or after decisioning");
   - the start of the debug track itself;
   - any swap test that needs no new tooling (PM rec 4: master swap, v6 known-good).

   For each: what it unblocks, what blocks it, and whether it can run in parallel. **Don't phase any initiative; that's the Planner's job.**
9. **Is any bench test worth running before `test-workflow-setup` lands?** For example a log-only swap test that needs no scope numbers. Answer with the measurement-validity reasoning from topic 4.
10. **Fix-recommendation stance** (PM rec 15): state what the current evidence supports about v8, and that it is re-derived at each checkpoint. Never "regardless".
11. **Stop / redesign / outside-help triggers** (topic 5 §5): adopt them, adapt them, or reject them as standing criteria for the debug track. Say where they live (STATE section 8, or a checkpoint rule in the debugger role).

## Produces

**Artifacts:**
- `docs/research/v7-retry/decisioning.md`
- `docs/research/v7-retry/RELAY-planner.md` for the first initiative, following the PROTOCOL relay template. Build it from topic 4 §6.2 / topic 6 §10.2 / topic 3 §6.2, whichever applies, and update its Context to say why this one runs first.

Suggested structure for `decisioning.md`:

1. **Summary**: half a page. Where the fault stands, what runs first, and why.
2. **STATE.md seed**: inputs 1–7, in topic 6 §4.1 shapes, ready to transcribe.
3. **Initiative sequence**: input 8, with dependencies and parallelism, as a table. Plus input 9.
4. **Standing criteria**: inputs 10–11.
5. **Disagreements with Stage A**: anywhere you override a topic's recommendation, with the reason.
6. **Open questions for the user**.

## Scope

**In:**
- Reading the named sections of topics 1–6, plus targeted legacy lookups
- Forming, structuring and labelling hypotheses
- Sequencing initiatives
- Writing `decisioning.md` and `RELAY-planner.md`

**Out:**
- Bench work or firmware changes
- Creating `lab/`, cards, templates, the role file or the hook (implementation)
- Editing `.context/`, `CLAUDE.md`, memory, `docs/debugging/`, `.claude/agents/`, or any Stage A artifact (record disagreements in §5 instead)
- Phasing any initiative

## What was done before this relay

- Topics 1–6 complete. See `README.md`.
- User decisions to date:
  - **2026-10-18 (topic 4):** `decisioning.md` sequences `test-workflow-setup`.
  - **2026-10-18 (topic 6):** a formal `debugger` role, drafted in `context-strategy.md` Appendix A; the user will edit it before first launch and may pivot.
  - **2026-10-18 (topic 6):** `lab/` at the repo root.
  - **2026-10-18 (topic 6):** one continuous debug track that spawns build initiatives.
  - **2026-10-18 (topic 6):** no v7 state in auto-memory.

## Your task

Produce `decisioning.md` and `RELAY-planner.md` per the above.

**Expected first move:** after loading, give the user a short draft of the hypothesis map's *regions*, without rows filled, plus the initiative candidates. Ask:
- whether any region is missing;
- whether the user has bench facts since May that Stage A didn't capture (boards, parts, scope or firmware changes);
- their constraints on bench time and parts spend, since these change sequencing.

**Expected second move:** fill the map by region. For each row, cite evidence IDs and apply the magnitude gate (PM rec 5) before anything is called a lead. Then the IS / IS NOT check: drop or flag any row that fails to explain the v6 IS NOT column.

**Expected third move:** sequence the initiatives and write the relay. Then do a frame-lock self-check, and report it to the user in the artifact's §1:
- Does the first proposed test cut the map's largest untested region?
- Or does it probe whatever the last investigation ended on?

## Context-pressure behavior

At ~60% context: finish the current section, commit `WIP:`, write `docs/research/v7-retry/RELAY-synthesis-continue.md`, and stop.

## Open questions to surface

- **Merge `test-workflow-setup` and the context scaffolding** (topic 6 §10)? It's a recommendation; the user confirms.
- **Board-model timing:** before the first v7 card, in parallel with it, or only when a layout question becomes load-bearing?
- **Bench tests before the tooling lands:** any at all (input 9)?
- **PR strategy for `research/v7-retry`:** one bundled PR now that Stage A is complete, or after Stage B (RESEARCHER.md: user's call)?

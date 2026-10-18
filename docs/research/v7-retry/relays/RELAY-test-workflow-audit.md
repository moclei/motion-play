# RELAY — research session — testing workflow audit (DRAFT)

> Informal research session, no agent role. Launch with default `claude`. See `docs/research/v7-retry/RESEARCHER.md` for conventions.
>
> Revised 2026-10-18 after topics 1, 2, 3 and 5 completed. Their findings added a **measurement-validity** job to this topic on top of the original logistics job.

## Context

During prior v7 debugging, the user did significant oscilloscope work: soldering probe wires onto traces, capturing waveforms, logging measurements. The retry will do more of this. This topic has **two jobs**:

1. **Measurement validity.** The post-mortem (§4.7) found that no step anywhere validated the measurement setup before a number was trusted, and several refutations rest on scope readings that may be artefacts. The user is new to the oscilloscope and has doubts about how past tests were performed and interpreted. This job comes first: there is no point standardising how captures are filed if we can't trust what's in them.
2. **Workflow logistics.** The current workflow has friction: unclear filename conventions, scattered image placement, no standard measurement log format, no test-card template, no documented procedure for the user's scope. The goal is a workflow that reduces friction and makes results easy for future AI sessions to ingest.

This session is topic 4 of 6 in Stage A. Topics 1, 2, 3 and 5 are **complete**; topic 6 (context strategy) runs after this one.

## Load these files

Load targeted sections, not whole documents. The investigation doc alone is ~56k tokens, and loading it whole is the anti-pattern described in post-mortem §4.10.

**Read in full:**
- `docs/research/v7-retry/RESEARCHER.md`: conventions.
- `docs/research/v7-retry/postmortem.md`: §4.5, §4.6, §4.7, §6 (recommendations 1–3, 7–10, 20) and "Observations for other topics". This is the main input for job 1.
- `docs/debugging/i2c-oscilloscope-debugging.md` (~360 lines): the current scope workflow doc.

**Read only the named sections:**
- `docs/research/v7-retry/expert-approaches.md`:
  - P3 (test the tool), P5 (control conditions), P6–P8 (test-card discipline);
  - §3 Techniques, the "scope before logic analyser" row;
  - "Observations for other topics".
- `docs/research/v7-retry/v6-v7-changelist.md`: CL-25 (firmware drift; v6 reference needs `4da1c67`), CL-26 (test points: TP4 = GND, no +3.3 V / +5 V pad), and §"Observations for other topics".
- `docs/research/v7-retry/kicad-extraction-audit.md`: the "Topic 4 / Stage B" bullets under observations. In particular, Phase 16 clearances were centreline, so don't reuse the 1.7–2.7 mm figures.
- `docs/debugging/v7-i2c-investigation.md`, **by heading only**:
  - Phases 20, 21, 22 and 23 (lines ~823–928): the scope measurements under audit;
  - Phase 25 (~962): unrecorded result;
  - "Firmware state" and "Revert list" (~1009–1069): baseline question;
  - one or two earlier phases (e.g. 12, 14) as examples of how results were logged in practice.

  Use `grep -n "^#"` to find the headings and read by offset.
- Image/capture files: `find docs -name "*.png" -o -name "*.jpg" -o -name "*.bmp" -o -name "*.csv"`. List them; open only the ones referenced by Phases 20–23.

The user is the primary source for scope model, probe kit, physical setup and what they remember of how Phases 20–23 were measured. Ask early.

## Produces

**Artifact path:** `docs/research/v7-retry/test-workflow-audit.md`

Suggested structure:

1. **Current state.** What the workflow looks like today, warts and all. Short.
2. **Measurement-validity audit** (job 1). For each scope result that a conclusion rests on (at minimum Phase 20, Phase 21's ~650 mV baseline V_OL on a working bus, and Phase 23's ~50 mV):
   - What was measured, and the recorded setup (or "not recorded").
   - Plausible artefact sources:
     - ground-lead length and method;
     - probe compensation;
     - 1×/10× setting vs. scope channel setting;
     - bandwidth limit;
     - probe loading (tip capacitance added to the bus);
     - Sensepeek/soldered-wire effects;
     - cursor vs. automatic measurement, and which waveform feature was measured.
   - A verdict per result: **trustworthy / suspect / unknown**, with reasoning.
   - Which post-mortem conclusions inherit that verdict.
   - What it would take to re-establish each one (a re-measurement procedure, not a run).

   Also resolve or explicitly mark unknown: **whether Phase 25 ran**, and **what the current firmware baseline is** (accumulated debug changes vs. the revert list).
3. **Friction points observed.** Concrete and specific, each with evidence (file reference or prior-session anecdote).
4. **Proposals.** One section per element below. For each: recommendation, rationale, and a snippet/template where it applies.
   - **Scope model and its quirks.** Model, probe configuration, trigger quirks, screenshot/CSV export mechanism, SCPI/network control support. If the scope supports programmatic control, flag it as a tooling opportunity.
   - **Setup-validation procedure** (new). A short checklist run at the start of every scope session, before any measurement on v7 is trusted:
     - Compensate the probe on the cal output.
     - Confirm the attenuation setting matches on probe and scope.
     - Use the shortest ground method available (note that v7's only GND test pad is TP4).
     - Measure a known-good reference and check it against datasheet/UM10204 expectations.
     - Define what a failed check means: stop and investigate, never fit parameters.
   - **Known-good reference procedure** (new). How to take reference measurements on a surviving v6 board running `4da1c67` firmware (CL-25), and/or another known-good I²C bus. Which signals, which probe points, and what "matches spec" means numerically (V_OL, rise time 30%→70%, V_IL/V_IH per UM10204). Note the ground-access difference: v7 has TP4 but no +3.3 V / +5 V pad (CL-26).
   - **Filename convention** for captures. Starting point: `YYYY-MM-DD_<test-id>_<probe-channel>_<signal-name>.png`. Refine with the user. `<test-id>` must be the stable, never-reused test ID from the test card.
   - **Capture location.** One directory per test, or one flat directory with disciplined names? It must be easy for an AI session to reference without ambiguity. Decide committed vs. gitignored vs. external with the user.
   - **Measurement log format.** Structured (YAML/TOML/JSON) so sessions can parse it without heuristics.
     - Minimal required fields include the **setup metadata** from post-mortem §6.9: probe, attenuation, ground method and length, bandwidth limit, trigger, timebase, cursor positions or measurement function, and capture filenames.
     - Include a field for whether the setup-validation checklist passed in this session.
   - **Test card template.** The single most important element. **Topic 4 owns the card's format**; topic 6 decides how cards and the log are stored and loaded into session context. Start from Zeller's five-column logbook row (Hypothesis | Prediction | Experiment | Observation | Conclusion; see `expert-approaches.md` P7) and include at least:
     - a stable, never-reused **test ID**;
     - the **declared baseline**: firmware commit/env, hardware config, board ID;
     - **hypotheses in play**, and **for each possible outcome, which hypotheses it excludes** (Platt; P6);
     - **variable changed**: exactly one (P8);
     - **A/B/A structure** where possible (post-mortem §3.1);
     - **prediction(s)**, written before the run with numeric thresholds;
     - **setup**, referencing the setup-validation result and log entry;
     - **procedure**: physical steps for the user;
     - **actual result** (raw symptoms first, then interpretation);
     - **conclusion strength**: measured-refuted / measured-supported / argued / not tested (post-mortem §6.6);
     - **revert-on-null**: was the change backed out?
     - **commit hash of the result** (post-mortem §6.20).

     The prediction and exclusion fields are filled in *before* the test runs.
   - **How the user receives instructions** from an AI session. Today this is ad-hoc chat. Proposal: structured, step-by-step, with an explicit "do this physically / expect this / report back exactly this". The user reports **raw observations, not interpretations** (Raymond, "symptoms, not guesses"; `expert-approaches.md` P10). This reduces the user's cognitive load during the test and keeps the session's bias out of the data.
   - **Image handoff.** How does an AI session read a capture the user just took? Confirm the file-path handoff flow with the user; propose a standard if it is ad-hoc today.
5. **Tooling opportunities.** Things that would reduce friction further but need their own work, such as SCPI capture with setup metadata auto-recorded, a measurement-logger CLI, and a test-card scaffolder. Flag them; do not build them.
6. **Does this spawn an implementation initiative?** Give a direct answer. Probably yes: "test-workflow setup", possibly including a re-measurement campaign for any results judged suspect in §2.

## Scope

**In:**
- Auditing the validity of past scope measurements, from the record and the user's recollection
- Documenting the current workflow
- Identifying friction points
- Proposing conventions, templates, formats and validation/reference procedures
- Writing the artifact

**Out:**
- Building any tools
- Modifying any scripts or firmware
- Changing anything in `docs/debugging/`, except as a flagged recommendation
- Running any oscilloscope test, including the re-measurements this audit proposes
- Any physical hardware work
- Forming new hypotheses about the v7 fault. Judging whether a past *measurement* is trustworthy is in scope. Proposing what the fault *is* is not.

## What was done before this relay

- `adopt-protocol` initiative merged.
- **Topic 1 (post-mortem): complete.** It names measurement validity (§4.7) as an open process gap, with the Phase 21 baseline anomaly and the Phase 21→23 swing as the first things to scrutinise.
- **Topic 2 (changelist): complete.**
  - The firmware has drifted (CL-25), so a v6 reference needs `4da1c67`.
  - v7 test points are reduced (CL-26).
- **Topic 3 (KiCad extraction audit): complete.** Phase 16 clearance figures are centreline and overstated.
- **Topic 5 (expert approaches): complete.**
  - Sources for instrument validation: Tektronix *ABCs of Probes*, Pease.
  - Test-card discipline: Zeller, Platt.
  - Instruction format: Raymond.

## Your task

Produce `docs/research/v7-retry/test-workflow-audit.md` per the structure above.

**Expected first move:** before doing anything else, ask the user about their setup and memory:
- Scope make/model, firmware, how they export captures today, USB/LAN SCPI support.
- Probe set: model, 1×/10×, ground-spring availability, Sensepeek SQ-500 details.
- **How Phases 20–23 were physically measured**: probe point, ground point and lead length, whether the probe was compensated, attenuation, bandwidth limit, how V_OL was read (cursor or auto measurement, on which feature).
- Whether Phase 25 ran (expected answer: unknown).
- Which boards survive: a working v6? Which v7 boards?
- Specific pain points they remember.

**Expected second move:** read Phases 20–23 and the scope doc, and do the measurement-validity audit (§2). Then look at how test results were recorded across phases; the inconsistencies are the friction points.

Keep the proposals specific enough to adopt without further design. Don't write "we should have a template"; write a concrete starting template with real field names.

## Context-pressure behavior

At ~60% context: finish the current section, commit `WIP:`, write `docs/research/v7-retry/RELAY-test-workflow-audit-continue.md`, and stop.

## Open questions to surface

- **Scope model and capabilities**: must come from the user.
- **How confident the user is in their recollection of the Phase 20–23 setups.** If it is low, the audit verdicts default to "unknown" rather than "suspect", and the re-measurement plan carries the weight.
- **Where captures should live**: in the repo (committed), in a sibling folder (gitignored), or on cloud storage. Confirm with the user.
- **How much programmatic scope control to recommend**: depends on scope support and the user's appetite for building tooling.
- **Who owns the test-workflow docs after this.** If it spawns an implementation initiative (or a re-measurement initiative), confirm the expected scope with the user before writing recommendations that pre-commit it.

# Relay — research → planner — 2026-10-18

role:planner

> To launch: copy this file to `docs/initiatives/test-workflow-setup/RELAY-planner.md`, then run `claude --agent planner`. Built from `context-strategy.md` §10.2, which supersedes `test-workflow-audit.md` §6.2 (the merge was accepted in `decisioning.md` §3.1).

## Context
Stage A of the v7 retry recommended a `test-workflow-setup` initiative (topic 4) and context scaffolding for debug sessions (topic 6). Topic 6 recommended merging them because both build `lab/`. Stage B (`docs/research/v7-retry/decisioning.md`) accepted the merge.

**Why this runs first:** it is the only initiative that blocks bench work. No v7 card can run until there is a declared firmware baseline and a place to pre-register and commit the result. HEAD is the stacked Phase 23–25 build, and Phase 25's result was lost for want of exactly that. The board-model initiative waits until a layout question becomes load-bearing.

## Load these files
- .context/PROTOCOL.md
- docs/research/v7-retry/test-workflow-audit.md — §2.5 (baselines), §4.4–§4.9, §5, §6.1 (skip §2–§3 unless a decision needs them)
- docs/research/v7-retry/context-strategy.md — §2.4, §4, §6, §8.2, §10 (§10.1 is an addendum to topic 4 §6.1)
- docs/research/v7-retry/decisioning.md — §1, §3 (sequence, dependency of the log-only cards), §4.2 (criteria the debugger role should carry)
- .claude/agents/debugger.md if the user has already finalised it; else docs/research/v7-retry/debugger-role-draft.md
- docs/research/v7-retry/v6-v7-changelist.md — CL-25 (`v6-ref` = `4da1c67`), CL-26 (v7 test points)

## State
Branch: n/a (the Orchestrator cuts `feat/test-workflow-setup` from main at run time)
Build: n/a at kickoff; the firmware builds at HEAD
TASKS.md current: n/a — not yet written
Initiative folder `docs/initiatives/test-workflow-setup/` holds only this relay.

## What was done
- Topic 4 audited past scope work: Phase 20 trustworthy (by margin), Phase 21 suspect, Phase 23 unknown, Phase 25 not tested, HEAD a stacked debug build. It defined the card, log, filenames, capture split, instruction block and image handoff; §6.1 is Planner input.
- Topic 6 placed `lab/` at the repo root, designed STATE.md / NOTEBOOK.md / hook / checker, and drafted a debugger role; §10.1 is an addendum to topic 4 §6.1.
- Stage B wrote the first STATE.md content (hypothesis map, IS / IS NOT, tombstones, measurement trust, next cards) in `decisioning.md` §2. The first debugger session transcribes it; this initiative creates the containers empty.
- **Stage B dependency finding:** the first four debug cards are log-only (serial ACK/NACK, no scope). They need only `v7-clean`, `v6-ref`, the `lab/` containers with the card template, and the debugger role. They do not need the LAN capture tool or the scope procedures. `decisioning.md` §3.3 gives the reasoning.
- User decisions (2026-10-18): formal debugger role (draft; the user will edit it); root `lab/`; one debug track that spawns build initiatives; no v7 state in auto-memory; `decisioning.md` sequences initiatives.
- User constraints (2026-10-18): 5–10 bench hours/week, flexible; parts budget ~$500/month.

## Your task
Write BRIEF.md, PLAN.md and TASKS.md in `docs/initiatives/test-workflow-setup/` for one initiative covering topic 4 §6.1 plus topic 6 §10.1.

- Carry both acceptance tables into the PLAN.
- Phasing is yours. Weigh the Stage B dependency above: the debug track can start log-only cards as soon as the baselines, containers and role exist, in parallel with the scope-tooling work.
- Instrument facts marked [verify] in topic 4 must be confirmed on the scope before anything is built on them.
- Bench steps for the user use the topic 4 §4.8 instruction format. The PLAN shows where the Orchestrator waits for the user.
- Keep each phase Worker-session-sized; split with a `🔄 Handoff` if not.
- Raise the decisions listed in both sections with the user at kickoff.

This initiative builds workflow, tooling and empty containers only. It must not:
- take v7 measurements;
- fill STATE.md with content (that is the first debugger session's transcription of `decisioning.md` §2);
- write test code for specific debug cards (the Nano ESP32 / SAMD21 probe sketches belong to the debug track).

## Open questions
- Whether the debugger role and containers land before the scope tooling (phasing; see the Stage B dependency above).
- Topic 4 decisions:
  1. cloud backup for gitignored captures;
  2. build our own capture tool, or adopt the third-party DHO800 project;
  3. delete or archive the old scope guide.
- Topic 6 decisions:
  1. hook mechanism;
  2. hard or soft section caps;
  3. banner legacy artefacts in place, or move them to an archive;
  4. card filename form.
- Whether the debugger role's checkpoint section carries the `decisioning.md` §4.2 criteria table. The user decides during the role edit pass.

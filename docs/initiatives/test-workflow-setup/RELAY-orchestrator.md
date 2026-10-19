# Relay — planner → orchestrator — 2026-10-18

role:orchestrator

## Context
The v7-retry research recommended one merged initiative (topic 4 test workflow plus topic 6 context scaffolding). Stage B (`decisioning.md` §3) put it first because it is the only thing blocking bench work. The Planner wrote BRIEF, PLAN and TASKS, and the user answered every kickoff decision.

## Load these files
- .context/PROTOCOL.md
- docs/initiatives/test-workflow-setup/BRIEF.md
- docs/initiatives/test-workflow-setup/PLAN.md
- docs/initiatives/test-workflow-setup/TASKS.md

Workers load source sections as each task names them, mainly `docs/research/v7-retry/test-workflow-audit.md` §2.5, §4.2–§4.9, §5 and `context-strategy.md` §2.4, §2.5, §4, §5, §6, §8.2, §8.3, §9. Don't preload them here.

## State
Branch: n/a. Cut `feat/test-workflow-setup` from main once the planning PR is merged.
Build: firmware builds at HEAD (stacked Phase 23–25 debug build; Phase 1 creates `v7-clean`).
TASKS.md current: yes

## What was done
- Nine phases in two tracks:
  - Track 1 (Phases 1–4) ends at a milestone PR that unblocks log-only debug cards.
  - Track 2 (Phases 5–9) is scope tooling, ending in a v6 dry run.
- PLAN.md lists seven user waits, W1–W7, with what the user does and the resume condition for each. The Orchestrator stops at each one.
- User decisions (2026-10-18):
  - log-only path first, with a milestone merge;
  - evaluate the third-party DHO800 tool before build-vs-adopt (gate W5);
  - Google Drive backup;
  - scope guide gets a banner and pointer;
  - git-only hook;
  - soft caps except `as_of`;
  - legacy docs bannered in place;
  - card files named `V7R-NNN-<slug>.md`.
- Both acceptance tables (topic 4 and topic 6) are in PLAN.md. Phase 9 ticks them.

## Your task
Run the initiative from Phase 1.

Watch for these:
- **Merges.** Every PR (the milestone and the final one) must be merged with a merge commit, never squashed. The baseline tags must stay reachable.
- **Phase 1 is build-only.** Don't flash `v7-clean` onto v7; that is debug card 1.
- **Phase 4 starts at W1.** Before dispatching it, ask the user whether `docs/research/v7-retry/debugger-role-draft.md` is final.
- **After the Phase 4 merge,** tell the user the debug track can start. Re-cut the branch from main, and rebase at the start of each Track 2 phase.
- **Bench steps** go to the user one at a time in the `test-workflow-audit.md` §4.8 format, with each REPORT recorded in SESSION.md. Workers never talk to the bench.
- **[verify] items.** No [verify] instrument fact feeds a tool or procedure until PLAN.md marks it verified, with its source.
- **Scope limits.** No v7 measurements and no STATE.md content.

## Open questions
- Does the debugger role's checkpoint section carry the `decisioning.md` §4.2 criteria table? The user decides at W1.
- Does `4da1c67` still build with today's toolchain? Found in Phase 1.
- Is the ESP32-S3 V_OL "≈ 30–80 mV" expectation supported by the datasheet? Found in Phase 5.
- The Google Drive for desktop folder path. Asked in Phase 7.
- Ground springs: the user buys them at any point before Phase 9.

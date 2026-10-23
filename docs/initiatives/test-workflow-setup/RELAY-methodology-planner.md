# Relay-Orchestrator — Planner — 2026-10-22

role:planner

## Context
`test-workflow-setup` built the lab method for the v7 I²C debugging: firmware baselines, `lab/` (cards, logs, STATE, notebook), checks, a debugger role draft, scope tooling and procedures. It was proven by a dry run on v6 (cards V7R-001 void, V7R-002 pass). That run was also the first real test of the AI method itself: roles, relays and bench sessions. This relay starts a methodology pass, a new initiative that improves the method before the first v7 card. The user has their own notes from the run, and those are the primary input.

## Load these files
- .context/PROTOCOL.md
- docs/research/v7-retry/debugger-role-draft.md: the debugger role. It is the user's file; changes go through the user.
- docs/research/v7-retry/decisioning.md §1, §2.7 and §3: the overall v7 plan and the first-card queue.
- lab/templates/ (card, log, instruction)
- lab/procedures/dho804-setup-validation.md and lab/procedures/known-good-reference.md
- The four debugger return relays in docs/initiatives/test-workflow-setup/ are the real record of how bench sessions went:
  - `RELAY-v6-dry-run.md`, the first dispatch. Its return is recorded in SESSION.md "### W7".
  - `RELAY-v6-dry-run-2-return.md`
  - `RELAY-v6-dry-run-2-s2-return.md`
- docs/initiatives/test-workflow-setup/TASKS.md "Deferred": the role install and the role-draft suggestions already queued.

Do **not** load `docs/initiatives/test-workflow-setup/SESSION.md` in full. It is over 2 000 lines of bookkeeping. If you need a detail, grep its section headings.

## State
Branch: n/a (start a new branch for the new initiative)
Build: n/a
TASKS.md current: n/a (new initiative)

## What was done
Lessons from the first run, as seen by the Orchestrator. The user's notes come first; these add to them.
1. **Readability.** Jargon reached the user unfiltered: "BQ end arm", "outer end of C21.1", probe points with no picture. What fixed it: a "Words used here" glossary per procedure, labelled probe-point pictures (pads A–F), and naming which screen is meant (scope screen, board display or terminal). Nothing checks readability before user-facing text ships.
2. **Pictures work.** Labelled board pictures were the most useful handoff aid (user: "perfect and super helpful"). The tool that makes them is in `tools/lab/probe_points/`; see `tools/CONTEXT.md`. New probe points should get a picture by default.
3. **Procedures written before any bench contact got four facts wrong:**
   - the V5 noise limit sat below the scope's own floor;
   - the RIGHT button can't restart the firmware;
   - a START trigger catches boot UART noise on SDA;
   - the BQ frame runs at 100 kHz, not 400.

   Each cost a bench session plus a replan. A short smoke run of a new procedure, before any card registers on it, would catch these sooner.
4. **Process weight.** There was a raw-data commit after every report, even for confirm-only steps (S2: 27 commits). Suggestion: a confirm-only report rides with the next data commit.
5. **Instruction delivery.** An instruction block posted under a results table got missed. A rule now in `lab/templates/instruction.md` says each instruction block goes in a message of its own. The role draft doesn't carry it yet.
6. **Bench-state handoff.** The user's idea: at session close, read the bench state back to the user for confirmation before the notebook commit. A fresh session already restores state from the notebook (the L0 test passed), so no separate check is needed after that.
7. **Card ordering ignores setup cost.** Board swaps and probe moves are slow, delicate manual work. The queue in decisioning §2.7 orders cards by information value only. The role should weigh setup-change cost, batch cards that share a setup, and prefer the board already on the bench. For example, card 2 (v6 under the minimal repro) doesn't depend on card 1, and v6 is on the bench now.
8. **Relay routing.** Debugger sessions wrote their returns as "paste into a fresh Orchestrator session" while an Orchestrator was already running. Returns should go to the running Orchestrator. When a Planner is needed, it should be spawned by that Orchestrator.
9. **Initiative log length.** SESSION.md grew past 2 000 lines because each replan and dispatch appended in full. It needs per-phase summaries or an archive rule.
10. **Replans after bench returns worked well.** The Planner fixed procedures from raw facts without widening limits, and the user decided only when a pass rule changed. Keep this.

## Your task
Write the initiative docs (BRIEF, PLAN, TASKS) for a methodology pass. A suggested name is `debug-method-v2`; the user may choose another.
- Start by asking the user for their notes, and treat them as the primary input. Fold in the lessons above where they agree, and flag where they conflict.
- Expected outputs:
  - the user's edits to the role draft, then the role install (already Deferred in test-workflow-setup TASKS);
  - template and procedure changes;
  - PROTOCOL changes, with the user's approval.
- Keep it light. The user has asked for less ceremony more than once.
- Finish before the first v7 card, so the friction isn't repeated on v7.

## Open questions
- Where cross-initiative work is tracked. The user hasn't named a document for it yet.
- The parts listed in decisioning §3.2 (a spare T-Display-S3 and an ESP32-S3-DevKitC-1 N16R8): the user hasn't confirmed they're on hand.
- Open technical items carried over:
  - the S2 fallback ground R32.2 isn't pictured;
  - there is no v7 S1 fallback if C9.1 won't take a tip and a spring;
  - the capture.py sweep label shows NORM or AUTO after SINGLE.

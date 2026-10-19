# Test Workflow Setup

## Intent
Make v7 bench work recordable and trustworthy before any new v7 result is taken. That means named firmware baselines, a `lab/` that holds pre-registered test cards, logs and evidence, checks that stop that state going stale, a formal debugger role, and a validated scope-capture path that an AI session can read without anyone transcribing by hand. Phase 25's result was lost because none of this existed.

## Goals
- Two declared firmware baselines, `v7-clean` and `v6-ref`, as tagged commits. Every future card cites one of them.
- A `lab/` tree (STATE, NOTEBOOK, cards, log, evidence, captures, inbox, procedures, templates) plus a pre-commit hook and session-start checker, so a recorded result can't be committed without updating STATE.
- A `debugger` agent role, installed after the user's edit pass. A fresh session engages from about 13k tokens.
- **Milestone (log-only ready):** the four items above merged to main, so the debug track can start log-only cards while the scope work continues.
- Scope on the LAN, every [verify] instrument fact confirmed, and a one-command capture that writes files named per convention plus a fully filled log entry.
- DHO804 setup-validation and known-good-reference procedures, proven by an end-to-end dry run on v6 with `v6-ref` firmware, run as a debugger session.

## Scope
In: the baselines; the `lab/` containers and templates; the checker and hook; installing the debugger role; protocol, context and memory touch points (with user approval); retirement banners; SCPI verification; evaluating the third-party DHO800 tool vs building our own; the capture tool, USB ingest and log validation; Google Drive backup for gitignored captures; the procedures; finding the closest GND pad to U5; the v6 dry run.
Out: any v7 measurement (R1/R2 included); any hypothesis work on the v7 fault; STATE.md content (the first debugger session transcribes `decisioning.md` §2); probe sketches for specific debug cards; firmware changes beyond defining the two baselines; source-hash retrofits to extractor outputs (board-model initiative); editing the bodies of `docs/debugging/` files.

## Constraints
- User bench time is 5–10 h/week, and parts are about $500/month. Bench steps wait on the user.
- Instrument facts marked [verify] are confirmed on the actual scope before anything is built on them.
- Never flash `v7-clean` onto v7 within this initiative. Doing so would be debug card 1.
- Merge PRs with merge commits, never squash, so the baseline tags stay reachable.
- The debugger role file is the user's. It is installed only after their edit pass.

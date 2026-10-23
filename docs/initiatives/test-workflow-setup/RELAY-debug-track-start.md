# Relay — Orchestrator — Debugger (first v7 debug session) — 2026-10-22

For the user. This starts the **debug track**: ad-hoc debugger sessions that run test cards on the v7 I²C fault. `test-workflow-setup` is closed and merged (PR #80). It runs on the role draft as it stands now, before the methodology pass.

## 1. Before you start

- **Terminal:** a new Cursor terminal at the repo root.
  - `git status` must show a clean tree. Use a fresh branch, for example `git switch -c debug/v7-track main`.
  - `git config core.hooksPath` must print `.githooks`.
- **Bench:** nothing needs to be set up in advance. The session asks what you have and how long you've got. v6 is still on the bench from the dry run:
  - unpowered;
  - data-only cable in the T-Display;
  - wire on pad C;
  - probes on the scope's Cal ground.

  Tell the session if anything has changed since then.
- **Time:** the first part needs no bench time: filling in STATE.md, then choosing and pre-registering the first card. You can stop after that and run the card another day.

## 2. Open the session

Run plain `claude`, then paste this as your first message:

```
Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session.
This is the first debug-track session on the v7 I²C fault. `test-workflow-setup` is closed (PR #80), and `v7-clean` may now be flashed onto v7 as a card's declared baseline.
First, with no bench time: transcribe `docs/research/v7-retry/decisioning.md` §2 into `lab/STATE.md` sections 1–8, as STATE.md's header says. Leave out the material marked *(decisioning only)* and keep the section caps. Commit that on its own.
Then propose the first card from the queue in STATE §8 (decisioning §2.7, cards 1–4, all log-only). Weigh the cost of changing the bench as well as what each card cuts: board swaps and probe moves are slow, delicate manual work for me. Say which cards share a setup and could run back to back, and whether card 2 (v6 under the minimal repro) should come first, since v6 is already on the bench. I choose; then pre-register and commit before any bench step.
Working rules for me at the bench:
- Plain short language. Name the screen (scope screen, board display, terminal). Refer to pads with a labelled picture; `tools/lab/probe_points/` can make one (see `tools/CONTEXT.md`).
- Send each instruction block in a message of its own, never under results.
- Steps that only confirm something can ride with the next data commit; they don't need a raw commit of their own.
- At the end, read the bench state back to me to confirm before the notebook commit.
If a tool, procedure or design change is needed, stop and write a Planner relay; don't build it here.
```

When it asks how long you have and which boards are available, tell it.

## 3. What should happen, in order

1. **Start-up check and a five-line orientation.** It should be clean, with no open cards.
2. **STATE.md filled in from decisioning §2,** in one commit, with no bench time.
3. **A proposed first card,** with the setup cost weighed. You choose.
4. **The card pre-registered and committed** before any bench step.
5. **Bench steps one at a time,** with raw data committed as it comes in.
6. **Recording:** the card, STATE and the notebook entry. You confirm the bench state before that last commit.

## 4. Stop at once

- Anything gets hot or smells, or you see a short.
- The start-up check reports STALE or CHECKPOINT DUE, and it can't be resolved.
- The session wants to change firmware beyond the card's declared change, or to rework the only good unit of a board.

## 5. Afterwards

There's no Orchestrator for the debug track. Each session carries on from `lab/STATE.md` and the notebook. Bring something back to the methodology Planner (`RELAY-methodology-planner.md`) only if it's about the method itself.

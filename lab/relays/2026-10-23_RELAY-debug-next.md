# Relay — Debugger — Debugger (next v7 debug session) — 2026-10-23

For the user. A kickstart for the next debug-track session. It holds pointers, not state. Per the role, the handoff is `lab/STATE.md`, the last notebook entry and the cards. Nothing here restates a result.

## 1. Before you start

- **Terminal:** a new terminal at the repo root.
  - `git status` must show `On branch main`, up to date, with a clean tree. The previous session's branch (`debug/v7-track-2`) is merged.
  - `git config core.hooksPath` must print `.githooks`.
- **Bench:** as left at the end of the last session. The bench-state line is in the notebook entry `2026-10-23 · s02 (cont.)`. Tell the session if anything has changed since then.
- **Optional, any time before:** read the text on the YD-ESP32-23's metal can (for example `ESP32-S3-WROOM-1 N16R8`). STATE §8 option (c) depends on it.

## 2. Open the session

Run plain `claude`, then paste this as your first message:

```
Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session.
Continue the v7 debug track. Cut a branch `debug/v7-track-3` from an up-to-date `main` and work on it.
Start from lab/STATE.md and the last notebook entry (2026-10-23 · s02 (cont.)).
Next is option (b) in STATE §8 (U3 runs `v7_pca_master_probe` with `Wire.begin(43, 44)`, a one-line card delta; ask me to approve it before pre-registering), unless I say otherwise or the start-up check says a checkpoint is due. The step-back checkpoint falls due once the next card is recorded: do it before pre-registering any further card.
Working rules for me at the bench: the same as before (notebook 2026-10-23 s01 and s02 "decisions"). Also:
- Don't run a session-side action that isn't in the card's procedure (an extra reset, an extra flash) without asking me first.
- If a STATE line says something is blocked, check `git log` on main before taking it at its word.
```

## 3. What should happen, in order

1. **Start-up check and a five-line orientation.** No open cards. Then the branch.
2. **Card (b) pre-registered and committed** before any bench step, with the delta stated: which file, which line, built on which core, reverted at the end.
3. **Bench steps one at a time.** Raw data is committed as it comes in.
4. **Recording:** the card, STATE and the notebook entry in one commit.
5. **Checkpoint entry** (now due) before anything else is pre-registered.

## 4. Stop at once

- Anything gets hot or smells, or you see a short.
- The start-up check reports STALE and it can't be resolved.
- The session wants to change firmware beyond the card's declared delta, or rework v7 #0003 (the only good unit).

## 5. Afterwards

Each session carries on from `lab/STATE.md` and the notebook. Tool or design work goes to the Planner via a relay.

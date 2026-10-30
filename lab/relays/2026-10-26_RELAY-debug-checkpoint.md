# Relay — Debugger — Debugger (step-back checkpoint session) — 2026-10-26

For the user. A kickstart for the next debug-track session, which is the step-back checkpoint. It holds pointers, not state. Per the role, the handoff is `lab/STATE.md` and the last notebook entry (`2026-10-26 · s01`). There is no open card. Nothing here restates a result.

## 1. Before you start

- **Terminal:** a new terminal at the repo root.
  - `git status` must show `On branch debug/v7-track-3` with a clean tree (or `main`, if you merge the branch first; then tell the session to cut `debug/v7-track-4`).
  - `git config core.hooksPath` must print `.githooks`.
- **Bench:** not needed. A checkpoint is desk work. Bench as left at the end of s01 (notebook bench-state line).

## 2. Open the session

Run plain `claude`, then paste this as your first message:

```
Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session, on branch debug/v7-track-3.
This session is the step-back checkpoint only; no bench, no new card.
```

## 3. What should happen, in order

1. **Start-up check and orientation.** `check_state.py` reports CHECKPOINT DUE; per the role, that is resolved first.
2. **Checkpoint** per the role's Step-back checkpoint section: re-read STATE §2–3, challenge the lead, re-derive the fix, check `expert-approaches.md` §5.1–5.3.
3. **Timebox:** STATE §8 shows 15/15 cards overall and 10 cards in the master bundle region. The rule is in `docs/research/v7-retry/decisioning.md` §4.2 (`grep -n "Timebox" …`): at the overall limit, the checkpoint explicitly decides continue / parallel respin / outside help, and the numbers change only at a checkpoint, with a notebook entry. That decision is yours.
4. **Write** the `checkpoint` notebook entry and set `last_checkpoint: V7R-014` in STATE; commit.
5. **Next card (optional, after the commit):** only if you want one drafted in the same session.

## 4. Inputs worth having open

- Cards recorded since the last checkpoint: V7R-012, V7R-013, V7R-014 (`lab/cards/`).
- Previous checkpoint: notebook `2026-10-25 · checkpoint @ V7R-011`.
- Planner relays still open: `2026-10-24_RELAY-planner-i2c_frame-window.md`, `2026-10-26_RELAY-planner-card-build-reproducibility.md`. They don't block the checkpoint.

## 5. Known quirks (from s01; not results)

- STATE.md is at 152 lines (cap ~150); the checkpoint edit is a chance to trim.
- The Read tool cannot render PDFs on this Mac (no poppler); use pypdf in a scratch venv for datasheets.

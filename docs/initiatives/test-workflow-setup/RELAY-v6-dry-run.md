# Relay — v6 dry run (W7)

For the user. This starts the v6 dry run as an ad-hoc debugger session (Phase 9, W7). Bring the results back to the Orchestrator session at the end.

## 1. Before you start

- **Board:** v6, under the microscope. USB-C cable attached to the board, **not yet** plugged into the Mac. Never v7.
- **Probes:** two Sensepeek SQ500s in PCBite arms. **CH1 = SDA, CH2 = SCL.** Ground springs fitted. Plugged into the scope, **not on the board**. The session tells you when and where to place them.
- **Picture:** keep `lab/procedures/img/v6-probe-points.png` open. Pads **A–F** on it are the probe points; the two **X** pads are USB power, so keep clear of them.
- **Scope:** on the direct Ethernet link (adapter in the Mac).
- **Terminal:** a new Cursor terminal at the repo root.
  - Local Network permission for Cursor must be on. If Python can't reach the scope later, switch it off and on again.
  - `git config core.hooksPath` must print `.githooks`.
  - `git status` must say `On branch feat/test-workflow-setup`, with a clean tree.
- **Date:** run it **before 2026-11-02**. After that, the start-up check reports CHECKPOINT DUE. If you see it, stop and tell the Orchestrator.

## 2. Open the session

Run plain `claude`, then paste these two lines as your first message:

```
Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session.
This session is the v6 dry run of `lab/procedures/dho804-setup-validation.md` (V1–V9) and `lab/procedures/known-good-reference.md` on the v6 board with `v6-ref`, as card V7R-001 (title "Setup validation + known-good reference on v6 (`v6-ref`)", `variable_changed: none — instrument validation`, `structure: single (justified)`). It is not the first debug-track session: don't transcribe `decisioning.md` §2, and in STATE.md change only the front matter (`open_cards`, `as_of`, `updated`), with no map cells, tombstones or measurement-trust rows. Bench: v6 board, DHO804, two SQ500 probes in PCBite arms (CH1 SDA, CH2 SCL) with ground springs, probes not yet on the board. Refer to probe points by the A–F labels in `lab/procedures/img/v6-probe-points.png`.
```

When it asks how long you have, tell it.

## 3. What should happen, in order

If the session skips a step or changes the order, stop it and say so.

1. It **pre-registers card V7R-001 and commits**, before any bench step.
2. It **flashes `v6-ref` onto v6.** Plug the board into the Mac when it asks, and check that it's v6 before the upload starts.
3. **Scope checks V1–V9.** The probes go on the scope's Cal output first. If a setting doesn't take, set it by hand and **write down the button path**.
4. **Reference measurements:**
   - **S1** at pads **A/B/C**.
   - **S2** at pads **D/E/F**. Place F with the board **unplugged**, and look before powering on.
   - For each one: arm a SINGLE trigger, press the board's **RIGHT button** (or replug its USB), and expect the decode to read `D6` then ACK.
5. **Captures and commits:**
   - captures with `capture.py`;
   - one commit per arm;
   - a recording commit with the result;
   - a notebook entry;
   - `tools/lab/backup_captures.sh`.

## 4. Stop at once

Power off if it's safe, tell the session, then tell the Orchestrator.

- v6 reads out of spec on a validated setup.
- Anything gets hot or smells, or a spring slips toward an X pad.
- No `D6` decode after a few restarts.
- The board boot-loops.

## 5. Afterwards

1. Close the session. Open a **new** `claude` session and paste **only the first line** of the prompt. After its start-up, ask only: `what is the bench state?`
2. Return to the Orchestrator session and report:
   1. Was the answer correct, and did it ask you anything first?
   2. Was the image handoff workable? What was awkward?
   3. The final commit hash (`git log -1 --format=%h`).
   4. Every setting you set by hand, with its button path.
   5. Pass or fail per row: V_OL, idle high, rise time, decode.

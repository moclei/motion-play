# Relay — v6 dry run, second attempt (W8)

For the user. This starts the v6 re-run as an ad-hoc debugger session (Phase 12, W8). The first attempt, card V7R-001, was recorded void at V5. This run is a **new card, V7R-002**. V7R-001 is not reopened. Bring the results back to the Orchestrator session at the end.

## 1. Before you start

- **Board:** v6, under the microscope. Never v7.
  - **No sensor PCB** plugged in.
  - The **soldered wire stays on pad C**. It is the S1 ground.
  - **Power:** a mains USB-C charger, ready for the **main-board USB-C**. Not plugged in yet.
  - **Flash cable:** the data-only cable from the Mac to the **T-Display's USB-C**. It passes no power. It may stay in the whole time.
- **"Unplug the board"** means: the main-board USB-C out, and no battery. The data-only cable may stay in. Tell the session whether it was in; it goes in the log.
- **Probes:** two Sensepeek SQ500s in PCBite arms. **CH1 = SDA, CH2 = SCL.** Ground springs fitted. Plugged into the scope, **not on the board**. The session tells you when and where to place them.
- **Picture:** keep `lab/procedures/img/v6-probe-points.png` open. Pads **A–F** on it are the probe points; the two **X** pads are USB power, so keep clear of them.
- **Scope:** on the direct Ethernet link (adapter in the Mac).
- **Terminal:** a new Cursor terminal at the repo root.
  - Local Network permission for Cursor must be on. If Python can't reach the scope later, switch it off and on again.
  - `git config core.hooksPath` must print `.githooks`.
  - `git status` must say `On branch feat/test-workflow-setup`, with a clean tree.
  - `ls lab/cards/` must show only `V7R-001-…`. If a `V7R-002-…` file is already there, the debug track has used that number: use the next free number everywhere below, and tell the Orchestrator.
- **Date:** run it **before 2026-11-04**. From that day, the start-up check reports CHECKPOINT DUE. If you see it, stop and tell the Orchestrator.

## 2. Open the session

Run plain `claude`, then paste these two lines as your first message:

```
Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session.
This session is the v6 re-run of `lab/procedures/dho804-setup-validation.md` (V1–V9) and `lab/procedures/known-good-reference.md` on the v6 board with `v6-ref`, as a new card V7R-002 (title "Setup validation + known-good reference on v6 (`v6-ref`), second attempt", `variable_changed: none — instrument validation`, `structure: single (justified)`; `hardware_config` lists the board change: a ~10 mm wire soldered to pad C (U2.14), GND only; no sensor PCB). V7R-001 was recorded void at V5; don't reopen it. It is not the first debug-track session: don't transcribe `decisioning.md` §2, and in STATE.md change only the front matter (`open_cards`, `as_of`, `updated`), with no map cells, tombstones or measurement-trust rows. Bench: v6 board, DHO804, two SQ500 probes in PCBite arms (CH1 SDA, CH2 SCL) with ground springs, probes not yet on the board. Refer to probe points by the A–F labels in `lab/procedures/img/v6-probe-points.png`. Run V1–V4 once, then V5–V9 at S1 and then at S2, one session log per arm (`_s01` S1, `_s02` S2).
```

When it asks how long you have, tell it.

## 3. What should happen, in order

If the session skips a step or changes the order, stop it and say so.

1. It **pre-registers card V7R-002 and commits**, before any bench step.
2. It **re-flashes `v6-ref` onto v6**, first, even though `v6-ref` should already be on it. The boot screen ("Sensor init failed") looks the same under any firmware, so the screen can't confirm the build.
   - Plug the charger into the main-board USB-C when it asks. The board's port shows up on the Mac only once the main board has power.
   - Check that it's v6 before the upload starts.
3. **V1–V4, once.** Scope and Cal only; the probes don't touch the board. They go in the S1 log (`_s01`).
4. **Arm S1** (log `_s01`): V5–V9 at the master end.
   - **V5a:** both tips and both springs on the scope's **Cal ground** terminal. No board.
   - **V5b:** unplug the board; tips and springs on the **soldered wire at pad C**; look; power on. Then the session runs `noise_floor.py` on the two captures.
   - **V6–V8:** tips on pads **A/B**, springs on the wire at pad C. Unplug before every move, look before powering on.
   - **V9, the reference:** set a SINGLE trigger, then **replug the main-board USB-C** (out, then back in), probes left in place. Expect the decode to read `D6` then ACK. Don't press RIGHT; it does nothing on this setup.
   - One raw-data commit for the arm.
5. **Arm S2** (log `_s02`): V5–V9 at the BQ end.
   - A fresh V2 read-back. V1, V3 and V4 are not repeated; the log points to `_s01`.
   - **V5a** again on the Cal ground (unplug the board first, then take the probes off it).
   - **V5b** on pad **F**. Place F with the board **unplugged**, away from the X pad, and look before powering on.
   - **V6–V8** on pads **D/E** with the ground on F. **V9** as for S1: SINGLE, then replug.
   - One raw-data commit for the arm.
6. **Close:**
   - `validate_log.py` passes on both logs;
   - a recording commit with the result and STATE;
   - a notebook entry;
   - `tools/lab/backup_captures.sh`.

If a setting doesn't take, set it by hand and **write down the button path**.

## 4. Stop at once

Power off if it's safe (unplug the board), tell the session, then tell the Orchestrator.

- **V5 fails again** (excess noise over 5 mV rms on a channel). Don't change the limit.
- The control's noise is outside the scope sanity band (sd outside 2.5–10 mV at the reference settings). `noise_floor.py` prints a flag.
- v6 reads out of spec on a validated setup (V1–V8 passed for that arm).
- Anything gets hot or smells, or a spring slips toward an X pad.
- No `D6` decode after a few replugs.
- The board boot-loops.
- The start-up check reports CHECKPOINT DUE.

## 5. Afterwards

1. Close the session. Open a **new** `claude` session and paste **only the first line** of the prompt. After its start-up, ask only: `what is the bench state?`
2. Return to the Orchestrator session and report:
   1. The L0 answer: was it correct, and did it ask you anything first?
   2. Was the image handoff workable? What was awkward?
   3. The final commit hash (`git log -1 --format=%h`).
   4. Every setting you set by hand, with its button path.
   5. Pass or fail per row, for **each arm** (S1 and S2): V5, V6, V7, V8, V9 (and within V9: V_OL, idle high, rise time, decode).

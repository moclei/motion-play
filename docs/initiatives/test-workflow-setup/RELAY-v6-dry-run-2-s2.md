# Relay — v6 dry run 2, arm S2 (W8, continued)

For the user. This continues card **V7R-002** at arm **S2** (the BQ end) as an ad-hoc debugger session (Phase 16, W8 part 2). It is **not a new card**. The card's predictions and limits stay as registered. S1 ran on 2026-10-21 (`RELAY-v6-dry-run-2.md`, which stays as run). Since then the procedures were revised, so S2 runs on the new versions. At the end the session closes the card. Bring the results back to the Orchestrator session.

## 1. Before you start

- **Board:** v6, under the microscope. Never v7.
  - **No sensor PCB** plugged in.
  - The **soldered wire stays on pad C**. S2 doesn't use it, but leave it.
  - **Power:** the mains USB-C charger, ready for the **main-board USB-C**. Not plugged in yet.
  - **Flash cable:** the data-only cable from the Mac to the **T-Display's USB-C**. It passes no power. It may stay in the whole time.
- **"Unplug the board"** means: the main-board USB-C out, and no battery. The data-only cable may stay in. Tell the session whether it was in; it goes in the log.
- **Probes:** the two SQ500s in PCBite arms. **CH1 = SDA, CH2 = SCL.** Ground springs fitted. Plugged into the scope, **not on the board**. The session tells you when and where to place them.
- **Picture:** keep `lab/procedures/img/v6-probe-points.png` open. S2 uses pads **D, E and F**. The two **X** pads are USB power. Pad F sits right next to an X pad.
- **Scope:** on the direct Ethernet link (adapter in the Mac).
- **Terminal:** a new Cursor terminal at the repo root.
  - Local Network permission for Cursor must be on. If Python can't reach the scope later, switch it off and on again.
  - `git config core.hooksPath` must print `.githooks`.
  - `git status` must say `On branch feat/test-workflow-setup`, with a clean tree.
  - `git log -1 --format=%h -- lab/procedures` must print `16c1ed1`. If it prints anything else, the procedures changed after this relay was written: stop and tell the Orchestrator.
- **Three screens.** Every instruction names one of them:
  - the **scope screen**: the DHO804's display;
  - the **board display**: the T-Display's small screen;
  - the **terminal**: Cursor's terminal on the Mac.
- **Date:** run it **before 2026-11-05**. From that day, the start-up check reports CHECKPOINT DUE. If you see it, stop and tell the Orchestrator.
  - From 2026-10-29 the check also warns `LOST-RESULT` for V7R-002. That is expected while the card waits for S2. It is not a stop.

## 2. Open the session

Run plain `claude`, then paste this as your first message:

```
Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session.
This session continues card V7R-002 (`lab/cards/V7R-002-v6-setup-validation-2.md`) at arm S2, the BQ end, on the v6 board with `v6-ref`, then closes the card. It is not a new card: don't pre-register anything, and keep the card's predictions and limits as registered. S1 is done; its log is `lab/log/2026-10-21_s01.yaml`, and it is not edited.
Method: S2 runs on `lab/procedures/dho804-setup-validation.md` and `lab/procedures/known-good-reference.md` at commit 16c1ed1 (Phase 14: 27fb0ff, 1f1bd5d, 16c1ed1). They write the S1 deviations in as the method: (a) V7 from the CSV mean, (b) V8 and V9 on the address trigger 0x6B write, SINGLE, replug. Cite known-good-reference.md steps 1–10 by their new numbers. Why they changed: `docs/initiatives/test-workflow-setup/PLAN.md`, "After V7R-002 S1" §1–§8.
Before any bench step, add a note to the card and commit it: S2 ran on the procedures at 16c1ed1 (27fb0ff, 1f1bd5d, 16c1ed1), with (a) and (b) as the method; and the S2 log is named by its session date, `lab/log/<date>_sNN.yaml` (sNN is the next free number for that date), which differs from the `2026-10-21_s02.yaml` in the card's Setup line. Pass that log to every `capture.py` run with `--session`.
Order: re-flash `v6-ref` first. This is a new scope session, so V1–V4 run again and go in the S2 log. Then the decode setup. Then V5–V9 at S2: V5a on the Cal ground, V5b on pad F, V6, V7 with CH1 on pad D and CH2 on pad E, V8, then V9 (`known-good-reference.md` steps 1–10, arm S2). No sensor PCB. Restart the board only by replugging the main-board USB-C. Pad F is next to an X pad (bridging warning in V6): land on F with the board unplugged, on the side away from the X pad, and look under the microscope before power.
Two expected values have never been read back by hand. The first time each is used, have me read it myself, and record what I saw in the S2 log's `validation.notes` and in the card's raw observations: (1) in the decode setup, the Decode 1 fields "left as found" (Label, Exchange, Event table; expected On, SCL/SDA, Off) on the scope screen; (2) in V8 step 1, `q ':TRIGger:IIC:SCL?'` and `q ':TRIGger:IIC:SDA?'` (expected CHAN2, CHAN1) in the terminal.
Analysis: `tools/lab/noise_floor.py` for V5, `tools/lab/i2c_frame.py` for V7 (idle mode) and V9 (`--expect D6`). Logs show `sweep: NORM` after a SINGLE trigger has fired; that is how the scope reports it, not a NORM run.
Close: `tools/lab/validate_log.py` passes on both logs; a recording commit with the card filled and `status: recorded`, STATE front matter only (`as_of: V7R-002`, `open_cards: []`, `updated`; no map cells, tombstones or measurement-trust rows), and the evidence for both arms, S1's captures included, promoted from `lab/captures/V7R-002/` to `lab/evidence/` under the card ID; a notebook entry; `tools/lab/backup_captures.sh`. Measured values on the card: S1 cites its log as recorded (hand values), with the `i2c_frame.py` values for `lab/captures/V7R-002/2026-10-21_V7R-002_S1_01.csv` beside them, labelled "recomputed at the method gates (PLAN §6); differs from the hand values only by gate; verdicts unchanged" with the tool commit a427a66; S2 cites the tool values from its log; any S1-vs-S2 comparison uses the tool values for both arms.
Bench: v6 board, DHO804, two SQ500 probes in PCBite arms (CH1 SDA, CH2 SCL) with ground springs, probes not on the board. Refer to probe points by the A–F labels in `lab/procedures/img/v6-probe-points.png`.
```

When it asks how long you have, tell it.

## 3. What should happen, in order

If the session skips a step or changes the order, stop it and say so.

1. **Start-up check.** It runs the start-up check and orients you. It must **not** pre-register a new card.
2. **Card note and commit**, before any bench step. The note names the procedure commit (16c1ed1) and the S2 log name.
3. **Re-flash `v6-ref`** onto v6, as at S1. The board display ("Sensor init failed!") looks the same under any firmware, so it can't confirm the build.
   - Plug the charger into the main-board USB-C when it asks. The board's port shows up on the Mac only once the main board has power.
   - Check that it's v6 before the upload starts.
4. **V1–V4**, in the S2 log. Scope and Cal only; the probes don't touch the board.
5. **Decode setup**, on the scope screen: function navigation icon (lower left) → **Decode** → **Decode 1** tab. The field table is in the setup validation, "Decode setup".
   - Read out Label, Exchange and Event table **as you find them**. Don't change them.
   - Then the terminal read-backs.
6. **V5a:** both tips and both springs on the scope's **Cal ground** terminal. No board.
7. **V5b** on pad **F**:
   - unplug the board;
   - land the springs and tips on F, on the side **away from the X pad**;
   - look under the microscope: nothing touches an X pad;
   - power on.
   Then the session runs `noise_floor.py`.
   If a tip and a spring don't both fit on F, the procedure's fallback pad R32.2 is **not marked** in the picture. The session must find it in the layout first. If that isn't clear, stop.
8. **V6:** the session records the ground on F and its length.
9. **V7:** unplug, tips to **D** (CH1) and **E** (CH2), ground stays on F, look, power on. Then **Vpp on the panel** (its own step), then the capture.
10. **V8:**
    - address trigger, set and read back. Type the `:TRIGger:IIC:SCL?` and `SDA?` queries yourself and read out the replies.
    - 20 µs/div and SINGLE;
    - **replug** the main-board USB-C (out, then back in), probes left in place.
    - Look at the **decode band on the scope screen**: the row labelled **B1 / I2C** at the left edge. Expect `Write:d6` then `A:0`.
    - Then capture, then back to 10 µs/div.
11. **V9** (`known-good-reference.md` steps 1–10, arm S2): SINGLE, then replug.
    - Expect status `STOP` in the terminal.
    - At 10 µs/div the decode band shows **no byte labels**. That is expected: the decode is read from the CSV.
    - Don't press RIGHT; it does nothing on this setup.
12. **Raw-data commits** for S2, as the role says.
13. **Close:**
    - `validate_log.py` passes on both logs;
    - the recording commit, with the card, the evidence for both arms and STATE;
    - a notebook entry;
    - `tools/lab/backup_captures.sh`.

If a setting doesn't take, set it by hand and **write down the button path**.

## 4. Stop at once

Power off if it's safe (unplug the board), tell the session, then tell the Orchestrator.

- **V5 fails** at S2 (excess noise over 5 mV rms on a channel). Don't change the limit.
- The control's noise is outside the scope sanity band (sd outside 2.5–10 mV at the reference settings). `noise_floor.py` prints a flag.
- v6 reads out of spec on a validated setup (V1–V8 and the decode setup passed for S2).
- Anything gets hot or smells, or a spring slips toward an X pad.
- **V8: no `d6` after 3 replugs.**
- **V9: no trigger (status not `STOP`) after 3 replugs.**
- `i2c_frame.py` exits 2 (bad input, or no frame in the record). Don't read the CSV by hand instead.
- `:TRIGger:IIC:SCL?` / `SDA?` don't read `CHAN2` / `CHAN1`, even after setting them again.
- The board boot-loops.
- The start-up check reports CHECKPOINT DUE.

## 5. Afterwards

1. Close the session. Open a **new** `claude` session and paste **only the first line** of the prompt. After its start-up, ask only: `what is the bench state?`
2. Return to the Orchestrator session and report:
   1. The L0 answer: was it correct, and did it ask you anything first?
   2. Was the image handoff workable? What was awkward?
   3. The final commit hash (`git log -1 --format=%h`).
   4. Every setting you set by hand, with its button path.
   5. Pass or fail per row, for **each arm** (S1 and S2): V5, V6, V7, V8, V9 (and within V9: V_OL, idle high, rise time, decode). S1's rows are already on the card. Add V1–V4 for the S2 session.
   6. What the two hand read-backs showed: the Decode 1 Label / Exchange / Event table fields, and `:TRIGger:IIC:SCL?` / `SDA?`.

# Relay — Debugger (W8, v6 dry run 2) — Orchestrator — 2026-10-21

role:orchestrator

## Context
W8 (`RELAY-v6-dry-run-2.md`) ran card V7R-002 on v6 with `v6-ref` on 2026-10-21. S1 (master end) ran V1–V9; S2 (BQ end) was not started (bench time). The card is open (`status: run`). This is an interim return: five procedure questions came up at S1, and the procedures belong to this initiative. Debugger findings that need procedure or tool changes go to the Planner; per the relay, they come back through this session.

## Load these files
- .context/PROTOCOL.md
- docs/initiatives/test-workflow-setup/RELAY-v6-dry-run-2.md (the dispatch)
- lab/cards/V7R-002-v6-setup-validation-2.md (raw observations, deviations, decision)
- lab/log/2026-10-21_s01.yaml (S1 log; `validate_log.py`: OK)
- lab/NOTEBOOK.md, entry "2026-10-21 · s01"
- lab/procedures/dho804-setup-validation.md §V7, §V8; lab/procedures/known-good-reference.md "Which transaction to capture", steps 3, 5, 7, pass table

## State
Branch: feat/test-workflow-setup, clean, last commit `7d208ba`
Build: n/a (no firmware change; `v6-ref` 4da1c67 re-flashed at step F)
TASKS.md current: not touched by W8
Captures: `lab/captures/V7R-002/` (gitignored), backed up with `tools/lab/backup_captures.sh` on 2026-10-21. Not yet promoted to `lab/evidence/` (that happens at recording).

## What was done (relay §5 items)
1. **L0 answer:** not done yet. The fresh-session "what is the bench state?" check is due after the card closes.
2. **Image handoff:** workable. The A–F letters were used throughout. Friction:
   - the dispatch's paste text had the image name as `v6-oints.png`, and the session used `v6-probe-points.png`;
   - "look at the decode row on the screen" was ambiguous with three screens on the bench (scope, board, terminal);
   - CHECK lines that fall between DO sub-steps were read only after DO was done (V7 panel look missed).
3. **Final commit:** `7d208ba`.
4. **Settings set by hand:** Decode menu (function navigation icon → Decode → Decode 1). Before: Bus status off, SCL Thre 0.00 V, SDA Thre 0.00 V, R/W Without. Set: Bus status On, both thresholds 1.65 V, R/W With. The other fields were already right: type I2C, Clock CH2, SDA CH1, Hex.
5. **Pass/fail, S1** (S2 not run):

| Row | S1 | Value | Source |
|---|---|---|---|
| V1 | pass | clock Δ 0.0 s | log val_V3 #1 |
| V2 | pass | 10/10 | card raw V2 |
| V3 | pass | flat/square, CH1 and CH2 | val_V3_01, _02 |
| V4 | pass | Vamp 3.0208 V both channels | val_V3_01, _02 |
| V5 | pass | excess 1.11 / 0.00 mV rms; ctl sd 5.04 / 4.81 mV | val_V5ctl_01, val_V5_01, `noise_floor.py` |
| V6 | recorded | wire on pad C, springs ~4 mm from C | card raw |
| V7 | pass (deviation a) | 3.303 / 3.290 V, CSV mean | val_V7_01 |
| V8 | pass (deviation b) | decode `Write:d6`, `A:0` | val_V8_03 |
| V9 V_OL | pass | 72.4 / 70.2 / 75.4 mV (bits 5/3/0), offset −9.08 mV not subtracted | S1_01 CSV |
| V9 idle high | pass | 3.3025 / 3.2929 V | S1_01 CSV |
| V9 rise 30→70 % | pass | SDA 97.7–98.4 ns, SCL 91.1–94.2 ns | S1_01 CSV |
| V9 decode | pass (deviation b) | CSV bits 1101 0110, 9th clock low | S1_01 CSV; scope band empty |

**Relay §4 stop list:** "No `D6` decode after a few replugs" was met with the procedure's START trigger. The run did not stop: the user chose an address trigger (question Q1). Flagged here because it departs from the dispatch's stop rule.

## Your task
1. Send questions Q1–Q5 below to the Planner as a replan request for the procedures (`dho804-setup-validation.md`, `known-good-reference.md`, and `capture.py` if the Planner decides to change it).
2. Decide whether V7R-002 S2 runs on the procedure as it stands, with the S1 deviations, or waits for the revision. Tell the user, who will pass it on to the next debugger session.

## Open questions
Raw facts and evidence only. Lines starting "Interpretation:" are the session's reading, tied to V7R-002.

- **Q1: the V8/V9 trigger.** With the trigger set to SINGLE on an I²C START, a replug fires on a waveform where SDA toggles in steps of about 8.68 µs while SCL stays high. The scope decodes no bytes (val_V8_01). Triggering on I²C address 0x6B (write), with `:TRIGger:IIC:WHEN ADDR`, `AWIDth 7`, `ADDRess 107` and `DIRection WRITe`, all read back correctly, catches `D6`+ACK (val_V8_02, val_V8_03, S1_01). Interpretation: 8.68 µs is one bit at 115 200 baud, which fits the ESP32-S3 boot-ROM UART0 TX on GPIO43, the same pin as SDA.
- **Q2: the clock rate at the BQ frame.** The SCL period is 10.0 µs, about 100 kHz (S1_01). The procedure assumes 400 kHz: a frame of about 25 µs, and the ≤ 300 ns rise-time row. At 10 µs/div the frame's START falls before the start of the record, so the scope's decode band stays empty. The decode labels show at 20 µs/div (val_V8_03). The ≤ 300 ns limit was kept as registered.
- **Q3: V7 Vtop on a flat trace.** VTOP and VBASe return 9.9E37 on both channels when the bus is idle (val_V7_01). V7 used the CSV mean, as `known-good-reference.md` step 7 allows for idle high.
- **Q4: decode defaults.** The scope came up with Bus status off and both thresholds at 0.00 V. `:BUS1:THReshold? SDA/SCL` read `0.000000` with `:BUS1:MODE IIC` set. After the menu fix they read `1.650000E0`. No SCPI set command for bus status or thresholds has been tried.
- **Q5: rise time on the panel vs the CSV.** With MAX/MIN thresholds reading back 70/30, the panel gives RiseTime(C1) = 285.71 ns and RiseTime(C2) = 114.28 ns (Cnt 1). From the CSV, 30→70 % comes to ≈ 98 ns for SDA and ≈ 92 ns for SCL, and 10→90 % to 256–272 ns (S1_01). Both sets are under 300 ns.
- **Unexplained, not a question:**
  - In V3, the CH2 panel Vamp, Vtop and Vbase equal CH1's to every digit shown, while the CSV level modes differ (val_V3_01, _02).
  - With a NORM START trigger, one frame decoded as "write 74" (R/W Without; not captured).

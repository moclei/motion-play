# v7 I²C fault — lab notebook

> **L2, append-only.** New entries go at the bottom. Nothing is edited after the commit that adds it, except to fix a typo. Find entries with `grep -n "V7R-014"` or by date heading.
>
> **No result is written twice.** A test's hypotheses, predictions, raw observations, values and conclusion live in its card (`lab/cards/`). Capture numbers and setup live in the log (`lab/log/`). Current standing lives in `lab/STATE.md`. This file holds *everything between cards*: why a test was chosen, belief changes, decisions with the user, observations not covered by any card, dead ends that never became a card, checkpoints and bench incidents.

## Entry formats

One **session** entry per session:

```markdown
## YYYY-MM-DD · sNN · <one-line summary>
- session: debugger | <relay or "direct"> · operator: user · boards: <board-id> (<baseline>+Δ), …
- cards: V7R-NNN pre-registered (<hash>) → recorded (<hash>); …
- map: <region>: <old status> → <new status> (V7R-NNN); …
- belief changes: was "<old>", now "<new>", because V7R-NNN. (Interpretation, labelled.)
- decisions: <what the user decided, and why, one line each>
- observations not in a card: <verbatim operator notes; symptom terms>
- bench state at end: <board power, probes, firmware flashed>, so the next session doesn't guess
- next: <ID of the open card, or "checkpoint due">
```

One **checkpoint** entry per step-back checkpoint (context-strategy §4.3):

```markdown
## YYYY-MM-DD · checkpoint @ V7R-NNN
- untested regions: …
- lead challenged: <region> — earned / not earned (magnitude gate: …)
- fix recommendation: unchanged | re-derived: …
- redesign/outside-help check (expert §5.1–5.3): …
```

The "belief changes" line replaces overwriting a "current working theory": STATE.md says what is believed; this notebook says when and why it changed.

---

## 2026-10-19 · s00 · volume 0: legacy investigation frozen
- session: direct (test-workflow-setup Phase 2) · operator: none · boards: none touched
- volume 0 is `docs/debugging/v7-i2c-investigation.md`, frozen. It is not edited; it is cited, never transcribed.
- legacy IDs: `L-PhNN` = legacy phase NN of volume 0 (find with `grep -n "^### Phase NN"`). Phase 24 has two entries: `L-Ph24a` = Arduino-as-master, `L-Ph24b` = Exp 1 glitch filter. Legacy phases are never renumbered into V7R.
- cards: none. The V7R counter starts after `V7R-000` (the STATE.md sentinel); the next card is the highest `lab/cards/V7R-NNN-*.md` + 1.
- next: the first debugger session transcribes `docs/research/v7-retry/decisioning.md` §2 into STATE.md.

## 2026-10-20 · s01 · v6 dry run of setup validation: V1–V4 pass, V5 fails on the instrument floor
- session: debugger (W7 v6 dry run, RELAY-v6-dry-run.md) · operator: user · boards: v6 (v6-ref, + ground wire on pad C)
- cards: V7R-001 pre-registered (479270c) → recorded (this commit)
- map: none (instrument validation; no map cells by instruction)
- belief changes: none on the fault. Setup: was "V5 ≤ 20 mV at the reference settings is reachable with a short ground", now "the scope + SQ500 floor alone at 0.5 V/div, BW OFF is 21.9 mV Vpp", because V7R-001 (val_V5_03). (Interpretation, labelled.)
- decisions: flash path = data-only cable to the T-Display USB-C + mains USB-C charger on the main board USB-C (as used on v7). S1 run first (relay order) with a ≤ 10 mm ground; 80 mm hook-clip assembly rejected (V6). User soldered a ~10 mm solid-core wire to pad C's mound; springs touch it ~8–9 mm from C. Stop after V5 and hand the V5 limit / reference settings question to the Planner via the Orchestrator; continuation is a new card.
- observations not in a card: on v6-ref with no sensor PCB, setup() halts at "Sensor init failed" (`while (1)` at main.cpp:463 @ 4da1c67), so the RIGHT button (read in loop()) cannot restart it; restart = replug main-board USB-C power. The BQ probe runs before that (main.cpp:123). validate_log.py accepts no "not run" value for V7_idle_high_V (left TODO).
- bench state at end: v6 main board unpowered (main-board USB-C power out); data-only cable Mac ↔ T-Display USB-C still in; v6-ref (4da1c67, lilygo-t-display-s3) flashed by V7R-001; ~10 mm solid-core wire soldered to pad C (U2.14) top mound, still fitted; both SQ500 (CH1 SDA, CH2 SCL) off the board, tips + springs on scope Cal ground; scope at 0.5 V/div both channels, offset −1.65 V, BW OFF, 10 µs/div, edge trigger CH1 1.5 V AUTO, 10 kpts; Result panel holds Vpp C1/C2 and leftovers.
- next: none open. Planner decision on V5 limit / reference settings, then a new card for V5–V9 at S1 and S2.

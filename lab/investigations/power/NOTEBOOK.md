# v7 power path: battery damage and #0004 boost — lab notebook

> **L2, append-only.** New entries go at the bottom. Nothing is edited after the commit that adds it, except to fix a typo. Find entries with `grep -n "PWR-014"` or by date heading.
>
> **No result is written twice.** A test's hypotheses, predictions, raw observations, values and conclusion live in its card (`lab/cards/PWR-NNN-<slug>.md`). Capture numbers and setup live in the log (`lab/log/`). Current standing lives in `lab/investigations/power/STATE.md`. Boards, fixtures and what's flashed live in `lab/BENCH.md`. This file holds *everything between cards*: why a test was chosen, belief changes, decisions with the user, observations not covered by any card, dead ends that never became a card, checkpoints and bench incidents.

## Entry formats

One **session** entry per session:

```markdown
## YYYY-MM-DD · sNN · <one-line summary>
- session: debugger | <relay or "direct"> · operator: user · boards: <board-id> (<baseline>+Δ), …
- cards: PWR-NNN pre-registered (<hash>) → recorded (<hash>); …
- map: <region>: <old status> → <new status> (PWR-NNN); …
- belief changes: was "<old>", now "<new>", because PWR-NNN. (Interpretation, labelled.)
- decisions: <what the user decided, and why, one line each>
- observations not in a card: <verbatim operator notes; symptom terms>
- bench state at end: <board power, probes, firmware flashed>, so the next session doesn't guess (also update `lab/BENCH.md`)
- next: <ID of the open card, or "checkpoint due">
```

One **checkpoint** entry per step-back checkpoint (context-strategy §4.3):

```markdown
## YYYY-MM-DD · checkpoint @ PWR-NNN
- untested regions: …
- lead challenged: <region> — earned / not earned (magnitude gate: …)
- fix recommendation: unchanged | re-derived: …
- redesign/outside-help check (expert §5.1–5.3): …
```

The "belief changes" line replaces overwriting a "current working theory": STATE.md says what is believed; this notebook says when and why it changed.

---

## 2026-11-03 · s01 · intake; PWR-001 passive survey; PWR-002 SW1 throw on USB
- session: debugger · docs/initiatives/v8-debug-board/debugger/RELAY-power.md · operator: user · boards: v7 #0005 (ref-0005), v7 #0004 (0004-as-found)
- cards: PWR-001 pre-registered (c48259a) → recorded (5afb461); PWR-002 pre-registered (95649f1) → recorded (see git log)
- map: Ka: untested → measured-supported (PWR-002); Kb, Kc, Kd, Ke: untested → measured-refuted on #0004 (PWR-001 passive, PWR-002 powered); B8: new at intake → measured-supported as a symptom on healthy boards, argued for #0001/#0002 (PWR-002); B4, B6: argued against (recollection); B5: untestable (no other board ever had a holder soldered).
- belief changes: was "#0004's boost doesn't run (cause unknown)", now "#0004's SW1 was at the GND throw; its power path runs", because PWR-002. Interpretation (PWR-002): was "#0001/#0002 were cooked by the battery", now "their symptom (no ESP32 on the Mac) is also what a healthy v7 shows on USB with SW1 at the GND throw"; damage not shown either way.
- decisions: investigation named power / PWR, branch debug/power from main (user). #0004 under both investigations (session default after the question was unclear; user can change). Readings trimmed mid-PWR-002 after the user asked how valuable the full repeats were (card deviation). No photos: user describes what they see.
- observations not in a card: user recollection 2026-11-02 (STATE §1, §7): Samsung 30Q 18650 in BT1, orientation "pretty sure" correct, no USB at insertion, SW1 OFF at insertion, no LED strip, nothing seen or smelled; afterwards the Mac didn't find the ESP32; #0001/#0002 since binned. BT1 holders were bought separately (Keystone 1042, DigiKey 36-1042-ND) and hand-soldered on #0001/#0002 only. Probe picture lab/procedures/img/v7-power-points.png made for PWR-001.
- bench state at end: #0004 and #0005 unplugged, SW1 as found on both (#0004 right, #0005 left); firmware unchanged; #0003 / Nano not plugged in; scope probes as V7R-020 (also lab/BENCH.md).
- next: none open. Options for the user: Q2 under a set load from the PSU (relay 4b/4c; B2 as a design risk); spare 1042 holder keying (B1). For v8-debug-board W1: cite PWR-001, PWR-002.

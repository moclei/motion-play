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

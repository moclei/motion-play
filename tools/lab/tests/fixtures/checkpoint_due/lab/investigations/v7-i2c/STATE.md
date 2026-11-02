---
as_of: V7R-003            # highest card ID with status recorded|abandoned that this file reflects (V7R-000 = sentinel, nothing recorded)
updated: 2026-10-19       # date of the last edit
last_checkpoint: V7R-000  # card ID at which the last step-back checkpoint ran (context-strategy §4.3)
open_cards: []            # cards with status pre-registered|run; must match lab/cards/ (checked)
---

# v7 I²C fault — current state

> Debugger sessions: this is L0. Other sessions: read sections 1–4 and stop.
> Never restate a result here. Cite its card. Max ~150 lines; the check warns beyond that.
> Skeleton only. The first debugger session transcribes `docs/research/v7-retry/decisioning.md` §2 into sections 1–8 in one commit (context-strategy §4.4).

## 1. Symptom                                   (≤ 6 lines)
Observable behaviour only, in operator terms: what fails, how it is seen, the minimal repro config. No mechanism words.

## 2. IS / IS NOT                               (KT table, ≤ 12 rows)
Every candidate cause in section 3 must explain both columns; Distinction is what is true only of IS; Evidence is V7R-/L-Ph/CL- IDs.
| Dimension | IS | IS NOT | Distinction | Evidence |
|---|---|---|---|---|

## 3. Hypothesis map                            (one row per region, ≤ 25 rows)
Status (untested | tested) says whether a test has touched the region; Strength (argued | measured-supported | measured-refuted | not tested) says what the evidence is worth. A region with no rows is listed as "no hypothesis yet".
| Region | Hypothesis (one line) | Status | Strength | Evidence | Last touched |
|---|---|---|---|---|---|

## 4. Facts in use                              (≤ 15 rows)
Only facts load-bearing for section 3; inferences are labelled "argued" and never promoted silently.
| Fact | Strength | Source |
|---|---|---|

## 5. Tombstones                                (one line each, never deleted)
`<hypothesis> — refuted by <ID> — <strength> — notebook <date>`; the full narrative lives in the notebook or the legacy doc only.

## 6. Baselines and bench state                 (≤ 15 lines)
Baselines (tag → commit, I²C init in one line); boards (ID | condition | mods | role); flashed now (board → commit + env, with the card ID that set it); cables and fixtures in the failing config.

## 7. Measurement trust                         (≤ 10 rows; rows leave when re-measured)
Verdict is trustworthy | suspect | unknown | not tested; a row is deleted when a V7R card re-measures it.
| Legacy or V7R result | Verdict | Load-bearing for | Pending |
|---|---|---|---|

## 8. Next                                      (≤ 6 lines)
Open cards (ID, title, arm reached); proposed next test (which map region it cuts, and why); blocked on (initiatives, parts, decisions).

## 9. Lookups (L1 routing)                      (≤ 15 rows)
Where to go for detail that is not L0; load only the named section or query.
| When you need… | Load | Section/query |
|---|---|---|
| a v6/v7 difference | docs/research/v7-retry/v6-v7-changelist.md | §3 by CL-ID (`grep -n "CL-NN"`); §5 observations |
| a legacy phase (`L-PhNN`) | docs/debugging/v7-i2c-investigation.md | `grep -n "^### Phase NN"` |
| the STATE seed (until transcribed) | docs/research/v7-retry/decisioning.md | §2 (sections 1–8 seed); §4 standing criteria |

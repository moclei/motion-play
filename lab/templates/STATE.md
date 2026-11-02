---
as_of: <PREFIX>-000            # highest card ID with status recorded|abandoned that this file reflects (<PREFIX>-000 = sentinel, nothing recorded)
updated: <YYYY-MM-DD>       # date of the last edit
last_checkpoint: <PREFIX>-000  # card ID at which the last step-back checkpoint ran (context-strategy §4.3)
open_cards: []            # cards with status pre-registered|run; must match lab/cards/ (checked)
prefix: <PREFIX>               # card ID prefix of this investigation (lab/cards/<PREFIX>-NNN-<slug>.md); unique across lab/investigations/
title: <TITLE>
status: open              # open | closed
---

# <TITLE> — current state
> Debugger sessions: this is L0. Other sessions: read sections 1–4 and stop. Never restate a result here. Cite its card. Max ~150 lines; the check warns beyond that.
> New investigation (`tools/lab/new_investigation.py`): sections are empty. The first debugger session fills sections 1–8 from the intake relay in one commit (context-strategy §4.4). Boards, fixtures and what's flashed live in `lab/BENCH.md`, shared by every investigation.

## 1. Symptom                                   (≤ 6 lines)
Observable behaviour only, in operator terms: what fails, how it is seen, the minimal repro config. No mechanism words.

## 2. IS / IS NOT                               (KT table, ≤ 12 rows)
Every candidate cause in section 3 must explain both columns; Distinction is what is true only of IS; Evidence is <PREFIX>-NNN IDs (and any legacy IDs this investigation defines).
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
`<hypothesis> — refuted by <ID> — <strength> — notebook <date>`; the full narrative lives in the notebook only.

## 6. Baselines and bench state                 (≤ 15 lines)
Baselines this investigation's cards cite (name → tag/commit + env, one line each).
Boards and bench: see `lab/BENCH.md` (boards, fixtures, flashed now, bench at last stop; shared by every investigation).

## 7. Measurement trust                         (≤ 10 rows; rows leave when re-measured)
Verdict is trustworthy | suspect | unknown | not tested; a row is deleted when a <PREFIX> card re-measures it.
| Earlier result | Verdict | Load-bearing for | Pending |
|---|---|---|---|

## 8. Next                                      (≤ 6 lines)
Open cards (ID, title, arm reached); proposed next test (which map region it cuts, and why); blocked on (initiatives, parts, decisions).

## 9. Lookups (L1 routing)                      (≤ 15 rows)
Where to go for detail that is not L0; load only the named section or query.
| When you need… | Load | Section/query |
|---|---|---|
| the intake request | <relay or doc that opened this investigation> | — |
| boards, fixtures, what's flashed | lab/BENCH.md | per board ID |

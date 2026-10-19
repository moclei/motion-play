---
test_id: V7R-012              # allocated from a counter; never reused, never renumbered
title: SDA V_OL at U5.6, cable out/in/out, v7-clean
status: pre-registered        # pre-registered | run | recorded | abandoned
created: 2026-11-04
prereg_commit: self           # `self` = the commit that adds this file; resolved from git (check_state.py --load)
baseline:
  name: v7-clean              # v7-clean | v6-ref | other (describe)
  firmware_commit: "1a2b3c4"   # quoted: an all-digit hash would parse as an int
  firmware_env: motion-play-v7-diag
  board_id: v7-B3
  hardware_config: "J6: failing-config cable (10k SDA→3V3 far end, SCL dangling). No other mods."
variable_changed: "J6 cable present vs absent"   # exactly one
structure: A/B/A              # A/B/A | A/B | single (justify)
revert_on_null: n/a           # yes | no (justify) | n/a (no firmware/hardware change)
---

# V7R-012 — <title>

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H1 | ... | hypothesis map / card V7R-0xx |
| H2 | ... | |
| M  | Measurement artefact (always listed) | §4.2 |

## Predictions and exclusions (written before the run)
| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| V_OL(B) − V_OL(A) < 20 mV | H1 | H2 |
| V_OL(B) − V_OL(A) ≥ 20 mV and A2 ≈ A1 ± 10 mV | H2 | H1 |
| A2 ≠ A1 by > 10 mV | — (drift: result void, investigate) | M |

## Setup
- Measurement log: `lab/log/2026-11-04_session-01.yaml`. Validation must read `passed: true` before step 1.
- Channels, probes, points: per log `channels`.

## Procedure (physical steps for the operator)
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| S1 | ... | ... | ... |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
### Measured values (from log; cite `lab/evidence/V7R-012/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** measured-refuted | measured-supported | argued | not tested
- Revert-on-null done: yes/no (commit)
- Result commit: self   <!-- `self` = the commit that sets status: recorded; resolved from git -->

<!-- Card rules (test-workflow-audit §4.7):
- `test_id` uses the form `V7R-NNN`, allocated monotonically (next = highest lab/cards/ filename + 1). Abandoned tests keep their ID with `status: abandoned`.
- Exactly one `variable_changed`.
- The prediction table has numeric thresholds and covers every outcome, including "void".
- `M` (measurement artefact) is always a listed hypothesis.
- Everything above `--- RUN ---` is written and committed before the test runs.
- Filename: lab/cards/V7R-NNN-<slug>.md. A conclusion cites only files under lab/evidence/V7R-NNN/.
- Self-reference: a commit can't contain its own hash, so `prereg_commit` and `Result commit` are written as the literal `self`. `self` means "the commit that made this transition": for prereg_commit, the commit that adds this file; for Result commit, the commit that sets `status: recorded`. Resolve with `python3 tools/lab/check_state.py --load`, or by hand with `git log --diff-filter=A --format=%h -- <card>` (prereg) and `git log -1 -G'^status: recorded' --format=%h -- <card>` (result). A real hash is also accepted, e.g. when correcting a card later. The pre-commit hook rejects a recorded card whose Result commit is empty or still `<hash>`.
-->

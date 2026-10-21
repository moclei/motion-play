---
test_id: V7R-002
title: "Setup validation + known-good reference on v6 (`v6-ref`), second attempt"
status: pre-registered
created: 2026-10-21
prereg_commit: self
baseline:
  name: v6-ref
  firmware_commit: "4da1c67"
  firmware_env: lilygo-t-display-s3
  board_id: v6                # no physical label; the only v6 main board on the bench
  hardware_config: "v6 main board with T-Display-S3 in U2; mains USB-C charger into the main-board USB-C; data-only cable Mac ↔ T-Display USB-C; no battery; no sensor PCB. Board change: ~10 mm solid-core wire soldered to pad C (U2.14, top-side mound), GND net only (fitted during V7R-001)."
variable_changed: "none — instrument validation"
structure: single             # justified: no DUT variable is changed; the run validates the probe/ground/scope chain against a board expected to be healthy (known-good-reference.md, outcome rule). V7R-001 was void at V5; this card re-runs V1–V9 under the revised V5 rule (dho804-setup-validation.md @ 7ad3a4f) and the revised reference procedure (known-good-reference.md @ 598fb5b)
revert_on_null: n/a           # flashing v6-ref is the baseline, not a delta
---

# V7R-002 — Setup validation + known-good reference on v6 (`v6-ref`), second attempt

## Hypotheses in play
| ID | Hypothesis | Source |
|---|---|---|
| H0 | The validated setup (two SQ500, CH1 SDA / CH2 SCL, per-arm ground, settings below) reads a healthy I²C bus inside the UM10204 pass table | `lab/procedures/known-good-reference.md` |
| E  | The pass-table expectation is wrong for v6 on `v6-ref` (the setup is fine but the expected numbers are not) | known-good-reference.md, outcome rule |
| M  | Measurement artefact: probe ratio, compensation, ground, contact or scope settings distort the readings (always listed) | §4.2 |

## Predictions and exclusions (written before the run)
Pass table per `known-good-reference.md` (V_DD = 3.3 V). Evaluated per arm (S1, S2). V1–V4 are run once and count for both arms.

| Outcome (numeric) | Excludes | Supports (weakly) |
|---|---|---|
| V1–V8 all pass for the arm, and V9: V_OL (master-driven 0-bit, ACK excluded, as measured) ≤ 0.2 V, idle high 3.135–3.465 V on CH1 and CH2, 30→70 % rise time ≤ 300 ns on every SDA and SCL rising edge in the frame, decode `D6` then ACK | M (for this arm, these settings) | H0 |
| As row 1, but V_OL in 0.2 V < V_OL ≤ 0.4 V | — (passes UM10204; > 0.2 V on a working bus = investigate the setup [own heuristic]) | M |
| V1–V8 pass, and any V9 row out of its pass limit (V_OL > 0.4 V, or idle high outside 3.135–3.465 V, or any rise time > 300 ns, or decode ≠ `D6`+ACK) | H0 | M or E: stop; resolve before any v7 measurement (outcome rule). No limit is widened |
| Any of V1–V8 fails: V1 clock Δ > 10 s; V2 ratio ≠ 10; V3 not flat/square; V4 Vamp outside 2.91–3.09 V; V5 excess noise > 5 mV rms on either channel, or V5a control sd outside 2.5–10 mV on either channel; V7 outside 3.135–3.465 V; V8 decode not `D6` | — (result void for that arm: setup not validated) | M |
| No `D6` frame caught after 3 replugs, or capture.py returns `9.9E37` for an item with no CSV fallback, or noise_floor.py refuses the V5a/V5b pair twice | — (void: investigate) | M |

## Setup
- Measurement logs, one per arm: S1 `lab/log/2026-10-21_s01.yaml`, S2 `lab/log/2026-10-21_s02.yaml` (created by the first `capture.py --session` run for each). V1–V4 recorded in `_s01`; `_s02` records a fresh V2 read-back and "V1, V3, V4: see 2026-10-21_s01". Validation must read `passed: true` in the arm's log before any V9 number counts.
- Scope: Rigol DHO804, firmware 00.01.05, direct LAN 192.168.50.2.
- Probes: SQ500 #1 on CH1 (SDA), SQ500 #2 on CH2 (SCL), fixed 10:1, scope ratio 10, ground springs fitted, in PCBite arms.
- V5 and V9 channel settings: 0.5 V/div, offset −1.65 V, BW limit OFF, DC, 10 µs/div, 10 kpts, measure thresholds 30/70 % (V9).
- Arms (v6 picture `lab/procedures/img/v6-probe-points.png`):
  - S1, master end: CH1 on pad A, CH2 on pad B; springs on the soldered wire at pad C (U2.14); spring-to-C distance recorded (V6). Unequal ground vs v7.
  - S2, BQ end: CH1 on pad D, CH2 on pad E; spring (or ≤ 10 mm wire) on pad F (C21.2), on the side away from the X pad; length recorded (V6).
- V5 (V5a control on Cal ground, V5b on the arm's ground point, board powered) through V9 run per arm.

## Procedure (physical steps for the operator)
| Step | Do | Check before continuing | Report back |
|---|---|---|---|
| F | Session flashes `v6-ref` (4da1c67, lilygo-t-display-s3) from a scratch worktree via the data-only cable, main board powered | Board is v6; upload port is the T-Display | Upload result; display state |
| V1–V4 | Scope only, probes on Cal: AUTO, ratio, compensation (per channel), Cal amplitude | Read-backs as in the procedure | Read-backs, capture output, Vamp per channel, any hand-set button path |
| S1: V5–V8 | V5a on Cal ground → unplug → tips + springs on the wire at C → look → power → V5b; noise_floor.py; ground record; tips to A/B (unplugged) → look → power; idle high; decode | Read-backs; panel items present | capture output, ground length, Vtop per channel, decode byte |
| S1: V9 | Reference settings, SINGLE trigger, replug main-board USB-C, capture | `D6` then ACK on decode | capture output, decode as seen |
| S2: V2, V5–V8 | V2 read-back; V5a on Cal ground → unplug → tips + spring on F (away from X) → look → power → V5b; then tips to D/E (unplugged) → look → power; as S1 | as S1 | as S1 |
| S2: V9 | as S1 | as S1 | as S1 |

--- RUN ---

## Actual result
### Raw observations (operator, verbatim; symptoms not interpretations)
- Step F (main-board USB-C power in, before flashing), 2026-10-21: display: "It says: \"Motion play\", \"Initializing sensors\" \"error\" \"Sensor init failed!\"". Data-only cable Mac ↔ T-Display in: "Yes". Bench time: "2 hours".
- Step F, session: `/dev/cu.usbmodem14401` enumerated; `pio run -e lilygo-t-display-s3 -t upload` from a scratch worktree at `v6-ref` (4da1c67): "Wrote 1842416 bytes ... Hash of data verified." "Hard resetting via RTS pin..." [SUCCESS].
### Measured values (from log; cite `lab/evidence/V7R-002/...`)
### Interpretation (session; labelled as such)

## Conclusion
- Outcome row matched: ...
- Hypotheses excluded: ...
- **Strength:** ...
- Revert-on-null done: n/a
- Result commit: self

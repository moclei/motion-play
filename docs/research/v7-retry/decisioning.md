# v7 Retry — Stage B Decisioning

> Stage B synthesis. Session date: 2026-10-18. Reads the six Stage A artifacts and targeted legacy phases. Produces the first `lab/STATE.md` content (§2), the initiative sequence (§3), the standing criteria (§4) and `RELAY-planner.md` for the first initiative.
>
> **Inputs loaded:**
> - Stage A sections, as listed in `relays/RELAY-synthesis.md`.
> - Legacy lookups (raw results only; no summary sections used as current): `docs/debugging/v7-i2c-investigation.md` L-Ph1–9, L-Ph12–16, L-Ph24a/b, L-Ph25.
> - `tools/arduino-sketches/v7_bq_master_probe/v7_bq_master_probe.ino` (header and constants only).
>
> **Went deeper than the minimum** for two decisions:
> - **The symptom wording and IS / IS NOT.** These needed the raw diag-loop rows from L-Ph4/9/12–15.
> - **The master-swap cards.** These needed the probe sketch's wiring note and its clock (100 kHz).
>
> **User input this session (2026-10-18):**
> - Add a "symptom identity" region.
> - No bench changes since May.
> - Bench time: 5–10 h/week, flexible when something needs finishing.
> - Parts: ~$500/month, more for a JLCPCB PCBA run.
> - PR strategy: decide after Stage B.

---

## 1. Summary

**Where the fault stands.** On v7 the ESP32-S3 master's address byte to BQ24195 (0x6B) gets NACKed while a TCA channel is open and that channel's cable has a DC path from SDA to +3.3 V at its far end. INA219 and TCA9548A ACK in the same state. With a sensor rigid attached, PCA9546A ACKs and the VCNL4040s NACK; that is the product failure. Two measured facts bound the search:

- **It depends on the master.** A SAMD21 master on the same v7 wire gets ACKs (L-Ph24a).
- **It depends on the board.** v6 ran an ESP32-S3 master on the same GPIOs, on the same Arduino core, with the same sensor assembly, at 400 kHz, error-free (changelist §1a).

So the cause sits in what is **specific to the S3 master's context on v7**, not in the S3 as such:
- the WROOM-1 module and its pad path (CL-01/02);
- its supply, now shared with the pull-up rail (CL-03/08);
- the v7 copper (CL-19–21);
- the firmware environment (CL-24).

It could also be an **interaction** between one of those and BQ's input. **No region has a lead.** No row has passed the magnitude gate (PM rec 5), and the map is written so that none can be promoted without a card.

There is a second open question the old investigation never asked. **Is the VCNL NACK the same fault as the BQ NACK?** L-Ph4 asserted it and nothing tested it. Every legacy test from Phase 5 on watched BQ, not the sensors.

**What runs first.**
1. **`test-workflow-setup`, merged with topic 6's context scaffolding** (accepted, §3.1). It is the only initiative that blocks bench work. It gives the two firmware baselines, `lab/`, the card format and the debugger role. Without those, any result risks going the way of Phase 25.
2. **The debug track starts as soon as the baselines and `lab/` containers exist,** with **log-only cards**, while the scope-capture parts of the initiative are still landing. Serial ACK/NACK results are binary, deterministic and A/B/A-able, and topic 4's distrust applies to scope numbers, not to logs (§3.3).
3. **`pcb-board-model` waits** until a card makes a layout question load-bearing, or until `test-workflow-setup` closes, whichever comes first. Until then, targeted kiutils probes are allowed (topic 6 §8.3).

**First discriminating tests** (titles only; §2.7):
1. Re-establish the fault on `v7-clean`.
2. Confirm the v6 IS NOT under the exact minimal reproducer.
3. **Symptom identity:** does VCNL ACK under the SAMD21 master on v7?
4. **Master swap within the S3 family:** the Arduino Nano ESP32 (already on hand) as master on the v7 bus.

**Frame-lock self-check** (relay's third move):
- **Does the first test cut the largest untested region?** Yes for the discriminating cards.
  - Symptom identity has never been touched.
  - The master-context half-split (Nano ESP32 vs WROOM-on-v7) cuts the module/supply/copper block. That block holds most of the changelist's short list and has never been tested.
- **Or does it probe where the last investigation ended?** Topic 4's recommended first test, R1 (V_OL at BQ pin 6), is exactly that. It re-measures the G-revised endpoint. **Overridden** (§5, D1). R1 becomes the first *scope* card, and doubles as v7 instrument validation once a scope question is load-bearing.
- **Honest caveat:** the master region is also where the legacy investigation turned at the end. The difference is that L-Ph22–25 tuned S3 *peripheral knobs*, which the v6 IS NOT already argues against (v6 used the default knobs and worked). The proposed swap tests the master's *context*, and its outcome can move the search off the master entirely.

**Fix stance.** The evidence does not yet support any v8 change. In particular it does not support the legacy "I²C buffer in front of BQ". The only fix direction with any backing is reverting master-side deltas toward v6, and that backing comes from IS / IS NOT, not from a mechanism. It is re-derived at each checkpoint (§4.1).

---

## 2. STATE.md seed

Written in the topic 6 §4.1 shapes for transcription into `lab/STATE.md` (as_of `V7R-000`) by the first debugger session (topic 6 §4.4). Material marked *(decisioning only)* is supporting reasoning and is **not** transcribed.

Evidence ID conventions:
- `L-PhNN`: legacy phase (`L-Ph24a` = Arduino-as-master, `L-Ph24b` = Exp 1 glitch filter).
- `CL-NN`: changelist row.
- `T3`: topic 3 kicad-extraction-audit §3 probes.
- `T4`: topic 4 test-workflow-audit §2.
- `T5-ref`: expert-approaches Observations.
- `F-n`: section 4 fact row.

### 2.1 Section 1 — Symptom

```
On v7 (B1 before rework, B3), on-board ESP32-S3 master, diag loop (motion-play-v7-diag):
with a TCA channel open whose connector carries a cable with SDA tied to +3.3 V at the far end
(4.7–47 kΩ, or a sensor rigid), BQ24195 0x6B returns X(2) (NACK on address) on every probe;
INA219 0x40 and TCA 0x70 return '.'. With a rigid: PCA 0x76 '.', VCNL4040 0x60 X(2), no sensor data.
Minimal repro: cable in J6, 10 kΩ SDA→+3.3 V at far end, SCL wire dangling; TCA2 row shows BQ:X(2).
Removing the far-end path: next probe shows BQ:'.'. Empty or closed channel: BQ:'.'.
```

### 2.2 Section 2 — IS / IS NOT

| Dimension | IS | IS NOT | Distinction | Evidence |
|---|---|---|---|---|
| What: which device | BQ 0x6B NACK; VCNL 0x60 NACK (behind PCA) | INA 0x40, TCA 0x70, PCA 0x76 ACK in the same state | BQ is farthest along SDA (47.7 mm from U3); address bit pattern; per-device input timing and thresholds; VCNL is behind a second mux | L-Ph4, L-Ph9, T3 |
| What: error type | NACK on address, code 2 | timeout or bus hang (code 5); never seen | address byte completes; slave does not pull ACK | L-Ph6a, L-Ph20 decode `D6 A:1` |
| What: master | ESP32-S3-WROOM-1 (U3) on v7 | SAMD21 (Nano 33 IoT) on the same v7 wire and config; ESP32-S3R8 (T-Display) on v6 | WROOM module and pad path; master supply shared with the pull-up rail; v7 copper U3→bus; v7 firmware env/variant | L-Ph24a, F-1, CL-01/02/03/24 |
| Where: board | v7 B1 (pre-bodge), B3 | v6 | everything in changelist §3; short list §5 | L-Ph9, F-1 |
| Where: channel | any channel carrying the trigger cable (J4/J5/J6) | empty channel; closed channel | follows the cable, not the route | L-Ph6c, L-Ph4 |
| Where: line | far-end DC path on SDA | far-end DC path on SCL only | SDA is bidirectional (slave drives ACK); GPIO43 = U0TXD, GPIO44 = U0RXD; SDA neighbours (CHRG_INT) | L-Ph12, CL-02, T3 |
| Condition: polarity | far-end path to +3.3 V (main rail or clean bench PSU) | far-end path to GND; VCC–GND resistor only | ~70 µA sourced into SDA at the far end while low; downstream node held at 3.3 V | L-Ph11, L-Ph13, L-Ph14 |
| Condition: load | any R from 4.7 k to 47 k, or a rigid | cable with no far-end path (stub only) | DC path present, not R value or C | L-Ph5, L-Ph6d |
| When | every probe while channel open and path present; steady state | after channel close or path removal (next probe); never cleared by 3× START/STOP | live, not latched | L-Ph12, L-Ph14, L-Ph15 |
| Firmware knobs | 400 kHz default init (pre-debug), 100 k, 50 k, CAP_3, deglitch 7 | none found that clears it | none found | L-Ph1–4, L-Ph22, L-Ph23, L-Ph24b |
| Regime | VBUS present; battery pads only; WiFi on and off | none found | none found | L-Ph6b, L-Ph18 |
| Extent | 100% deterministic on 2 healthy-assembly v7 boards | intermittent; board-specific | design-level | L-Ph4, L-Ph9 |

Every candidate cause in section 3 must explain both columns. **The hard pair is the master row together with the line row.** A cause must:
- care about which master context drives the bus (SAMD21 and v6-S3 pass);
- care about whether SDA, not SCL, has a far-end DC path;
- respond to ~70 µA of DC current or the downstream idle level, not to R or C.

### 2.3 Section 3 — Hypothesis map

| Region | Hypothesis (one line) | Status | Strength | Evidence | Last touched |
|---|---|---|---|---|---|
| master: identity | Something about the v7 master context (not BQ alone) causes the NACK; which property is unknown | tested | measured-supported (master-dependent; property not isolated) | L-Ph24a, F-1 | L-Ph24a |
| master: module/path | WROOM-1 module vs T-Display path to GPIO43/44 (die rev, module routing, pad state) is the distinguishing factor | untested | not tested | CL-01, CL-02 | — |
| master: pin role | GPIO43's UART0-TX role (ROM boot output, IO_MUX/matrix state, any Serial0 use) leaves the SDA pad unlike SCL's | untested | not tested | CL-02, CL-24 | — |
| master: peripheral config | A controller or pad setting (clock, drive, deglitch, pad filter, internal pulls) gates it | tested (partly) | measured-refuted for clock, CAP_3, deglitch (stacked); not tested for pad filter and pulls | L-Ph22, L-Ph23, L-Ph24b, L-Ph25 | L-Ph24b |
| master: timing | S3 SDA hold/setup relative to SCL, as shaped by the far-end path, falls outside BQ's (and VCNL's) tolerance but inside INA/TCA's | untested | not tested | F-3, F-9 | — |
| master supply | Shared +3.3 V rail (MCU I/O = pull-up rail; AMS1117 + as-built caps) changes how the master's pad relates to the bus | untested | not tested | CL-03, CL-08, CL-14 | — |
| bus copper | v7 SDA route (B.Cu under BT1, ~6.8 mm with no In2 under it, In2 +3.3 V reference) degrades S3-driven SDA edges but not SAMD21's | untested | argued (geometry only) | F-8, CL-19–21, T3 | T3 |
| bus copper: neighbours | SCL (0.20 mm gap) or CHRG_INT (<0.5 mm) couples into SDA | untested | not tested | F-8, T3 | — |
| mux | TCA channel-open with a far-end pull-up changes the upstream SDA node (pass-gate state, idle level) in a way only the S3 context reacts to | untested | argued | A-1, L-Ph5, L-Ph6d, L-Ph13 | L-Ph13 |
| slave: BQ × master | BQ's input requirement is stricter than INA/TCA's, met by SAMD21, missed by S3-on-v7 | untested | not tested | F-9, L-Ph24a | — |
| slave: INA, TCA, PCA | no hypothesis yet (they ACK; used as controls) | untested | not tested | L-Ph4 | — |
| symptom identity | VCNL NACK (product failure) is the same fault as BQ NACK (diag marker) | untested | argued (asserted in L-Ph4, never tested) | A-2, L-Ph4 | — |
| symptom identity: causal | BQ's NACK state or input disturbs the bus for downstream devices (BQ causal), vs common cause | untested | not tested | L-Ph8 (B2: BQ I²C open) | — |
| cable / far end | no live hypothesis; trigger characterised (SDA, +3.3 V, DC path, R-independent) | tested | measured (as trigger) | L-Ph5, L-Ph6d, L-Ph11–15 | L-Ph15 |
| cable mating | 4-pin socket vs 4-in-5 (CL-16) | untested | argued-refuted (SAMD21 ACKs through the same mating) | CL-16, L-Ph24a | — |
| firmware: drift | Debug-stack drift since `4da1c67` causes it | tested (indirectly) | argued-refuted (fault present with v6-era init, L-Ph1–4) | CL-25, F-6 | L-Ph4 |
| firmware: env | v7 env/variant change (devkitc variant, no display init, STARTUP_I2C_SCAN, boot order) | untested | not tested | CL-24 | — |
| firmware: core | arduino-esp32 2.0.14 / legacy IDF I²C driver behaviour (#8543 class) | untested | not tested; fails v6 IS NOT on its own (same core on v6) | F-10, CL-24 | — |
| power regime | no live hypothesis; control variable (VBUS / battery / WiFi state) | tested | measured-refuted as cause | L-Ph6b, L-Ph18 | L-Ph18 |
| measurement | Any v7 scope number is an artefact until §4.2 setup validation passes on that session | untested | not tested | T4 §2.6 | T4 |
| power: other | no hypothesis yet (BQ charger switching, boost, LDO noise beyond L-Ph14's far-end test) | untested | not tested | — | — |

**Row audit against IS / IS NOT and the magnitude gate** *(decisioning only)*. ✓ = explains the column; ✗ = fails it as stated; ? = only with an extra mechanism the row doesn't name.

| Row | v6 IS NOT | SAMD21 IS NOT | SCL-only IS NOT | GND/stub IS NOT | INA/TCA ACK | Magnitude gate | Verdict |
|---|---|---|---|---|---|---|---|
| master: module/path | ✓ | ✓ | ? | ? | ? | not applicable until a property is named | keep; half-split candidate |
| master: pin role | ? (same pins on v6; needs CL-24 env difference) | ✓ | ✓ (only row with an SDA-specific master mechanism) | ? | ? | not assessed | keep; cheap to check by code reading plus one card |
| master: peripheral config | ✗ (v6 ran defaults) | ✓ | ? | ? | ? | — | flagged: fails v6 alone. Phase 25 items deprioritised. |
| master: timing | ? (same driver on v6; needs a v7 edge-shape change) | ✓ | ✓ (SDA is the data line) | ? | ✓ (per-device tolerance) | **not passed:** needs BQ24195 t_SU;DAT / t_HD;DAT spec vs S3 legacy-driver timing, and an estimate of how 70 µA shifts an SDA edge. Unassessed. | keep; not a lead |
| master supply | ✓ | ✓ | ✗ (supply touches both lines) | ✗ | ✗ | **fails on its face:** 70 µA from the far end can't move an LDO rail. Needs a mechanism tying supply to SDA-only. | flagged: fails SCL-only and GND/stub |
| bus copper | ✓ | ? (edge-rate difference) | ✗ per L-Ph16 (SCL equally or more exposed) | ? | ? | not assessed | flagged: fails SCL-only unless a SDA-only neighbour matters |
| bus copper: neighbours | ✓ | ? | ? (CHRG_INT is SDA-adjacent; SCL-adjacency to CHRG_INT unknown) | ? | ? | not assessed | keep, low |
| mux | ? | ✓ only if the S3 context reacts differently | ✗ (pass gate is symmetric) unless master reads back SDA | ✓ (explains polarity and stub) | ? | **the only row that addresses the 70 µA / idle-level distinction directly**, but argued from a datasheet behaviour (A-1) | keep |
| slave: BQ × master | ? | ✓ | ✓ | ? | ✓ | not assessed | keep |
| symptom identity | n/a | n/a | n/a | n/a | n/a | n/a | test first: decides what the other rows are explaining |
| firmware: env | ✓ | ✓ | ? | ? | ? | — | keep |
| firmware: core | ✗ | ✓ | ? | ? | ? | — | flagged: fails v6 alone |

**Reading of the audit.** No row explains every column on its own. The rows that come closest each need a second ingredient:
- **master: pin role** needs CL-24.
- **master: timing** needs a v7 edge-shape change.
- **mux** needs master read-back of SDA.

That pattern suggests an interaction of two deltas. It is a reason to half-split the master context before forming a story, not a story itself.

**Magnitude-gate note** *(own; decisioning only)*. The cleanest numeric constraint is L-Ph6d vs L-Ph5:
- Cable alone passes. Cable + 47 kΩ fails, at a combined pull-up of 2.1 k vs 2.2 k: essentially the same R and the same C.
- What differs is ≈ 3.3 V / 47 kΩ ≈ **70 µA** sourced into SDA at the far end while SDA is low, plus the far-end node's idle level (A-1).
- **Any hypothesis must be switched by ≤ 70 µA or by that idle level.** A row whose mechanism needs mA-scale or rail-scale effects fails the gate before scope time is spent.

### 2.4 Section 4 — Facts in use

| Fact | Strength | Source |
|---|---|---|
| F-1 v6 ran 6 sensors through TCA + PCA with BQ and INA on the bus, 0 I²C errors, 400 kHz, T-Display ESP32-S3 master on GPIO43/44, core 2.0.14 (2026-04-14) | measured (session data); board identity argued (strong) | changelist §1a, CL-24 |
| F-2 Trigger: TCA channel open + cable + far-end DC path SDA→+3.3 V, any R from 4.7 k to 47 k; stub-only, SCL-only, SDA→GND and VCC–GND-only pass; live A/B/A | measured-supported (strong, repeated) | L-Ph5, L-Ph6d, L-Ph11–14 |
| F-3 Failure is NACK on address (code 2), never timeout; not cleared by 3× START/STOP | measured | L-Ph6a, L-Ph15 |
| F-4 In the failing state INA 0x40 and TCA 0x70 ACK; with a rigid, PCA 0x76 ACKs and VCNL 0x60 NACKs | measured | L-Ph4, L-Ph9 |
| F-5 SAMD21 master (Nano 33 IoT, 100 kHz, via TPIO43/44, U3 released) gets BQ ACK in the failing config; single session; master, clock source, drive, library all differ | measured-supported (one run, multi-variable) | L-Ph24a; probe sketch |
| F-6 Fault present before the debug firmware stack (v6-era init, 400 kHz) | argued (chronology) | L-Ph1–4, CL-25 |
| F-7 At BQ pin 6 in the NACK window, SDA high ≥ 3.01 V; scope decode reads `Write:D6 A:1` | measured (trustworthy by margin) | L-Ph20, T4 §2.3 |
| F-8 SDA 72.9 mm (F 35.9 / B 37.0); 37 mm on B.Cu under BT1; B.Cu runs reference In2 +3.3 V, ~6.8 mm SDA / ~7.4 mm SCL over no In2 copper (x 105–111, y 122–123); SDA–SCL gap 0.20 mm; SDA < 0.5 mm from CHRG_INT. Relevance: **unassessed** | measured (read-only probes) | T3 §3 |
| F-9 BQ is the farthest SDA load from U3 (47.7 mm; INA 31.7 mm, TCA 19.4 mm) | measured | T3 §3 |
| F-10 espressif/esp-idf #8543: ESP32-S3 master clocked SCL after STOP on IDF release/v4.4, fixed 2022; original ESP32 unaffected. Relevance: **unassessed** (whether core 2.0.14's IDF includes the fix is unchecked) | reference | T5-ref |
| F-11 Sensor module (rigid + flex + VCNL) works with an Arduino Nano ESP32 master on J1 | measured (strong) | L-Ph3 |
| A-1 TCA9548A pass gate: with no downstream pull-up, the downstream side idles below VCC (pass-gate limited), so "stub only" and "stub + far-end pull-up" also differ in downstream idle level | argued (datasheet behaviour; not verified this session; not measured on v7) | TI TCA9548A datasheet [verify] |
| A-2 "BQ is first to fail because it's farthest, and VCNL fails from the same bus margin" | argued (never tested; frame-lock origin, PM §4.1) | L-Ph4 |

**Assumptions register (PM rec 12): decided as STATE section 4 rows labelled `argued`** (A-n), the topic 6 §12 default. Reasons:
- Only two assumptions are load-bearing now.
- A separate file would be one more L1 document to keep in sync, which is the PROTOCOL's "every document must earn its existence".
- Revisit at a checkpoint if A-rows push section 4 past its 15-row cap. At that point they move to a `lab/ASSUMPTIONS.md` that the debugger role names.

**Withdrawn, never to be entered:** "BQ effective V_IL ~800–900 mV" (T4 §2.3). "~5–10 pF cable capacitance" is never measured; if a row needs it, it enters as an A-row with that label.

### 2.5 Section 5 — Tombstones

```
Sensor-side defect (VCNL/PCA/flex) — refuted by L-Ph3 — measured-refuted (strong) — legacy Ph3
Pull-up strength / rise time — refuted by L-Ph2, L-Ph5 — measured-refuted (weak: combined 1.5–2.1 kΩ only) — legacy Ph5
I²C clock speed — refuted by L-Ph2, L-Ph22 — measured-refuted (moderate) — legacy Ph22
ESP32 RF coupling — refuted by L-Ph6b — measured-refuted (moderate; also skips WiFi/MQTT init) — legacy Ph6
Per-channel routing defect — refuted by L-Ph6c — measured-refuted (strong) — legacy Ph6
Cable stub capacitance/inductance alone — refuted by L-Ph5, L-Ph6d — measured-refuted (strong) — legacy Ph6
BQ in a documented I²C-suppressing mode — L-Ph10 — argued (datasheet silence); moot after L-Ph24a — legacy Ph10
Rail perturbation through cable loop — refuted by L-Ph11 — measured-refuted (moderate; ~330 µA never measured) — legacy Ph11
SCL as the trigger line — refuted by L-Ph12 — measured-refuted (strong, A/B/A) — legacy Ph12
Story A naive (phantom START) / Story B naive (edge degradation) — L-Ph13 — measured-refuted, naive forms only (moderate) — legacy Ph13
Story C: 3.3 V rail noise via the far-end source — refuted by L-Ph14 — measured-refuted (strong, A/B/A) — legacy Ph14
Story A residual: stuck slave state machine — refuted by L-Ph15 — measured-refuted (strong, narrow claim) — legacy Ph15
Routing-asymmetry EMI (SDA routed worse than SCL) — L-Ph16 — argued (geometry; centreline numbers overstated, direction holds per T3) — legacy Ph16
Story D original: ESD-diode injection at BQ — L-Ph17 — argued (datasheet inference) — legacy Ph17
Cable as EMI antenna — L-Ph17 — argued (geometry, untested) — legacy Ph17
USB-C / VBUS state — refuted by L-Ph18 — measured-refuted (moderate) — legacy Ph18
Story D-revised: V_IH violation via crosstalk — refuted by L-Ph20 — measured-refuted (strong; margin exceeds any probe artefact, T4) — legacy Ph20
Story G-revised: V_IL violation via V_OL rise — refuted by L-Ph23 — measured-refuted, pending R1 — legacy Ph21–23
Story H: BQ input fault regardless of master — refuted by L-Ph24a — measured-refuted (strong for "master-dependent") — legacy Ph24a
I²C-controller deglitcher (Exp 1) — refuted by L-Ph24b — measured-refuted (moderate; stacked on 100 kHz + CAP_3) — legacy Ph24b
```

Not tombstoned:
- **Phase 25 (pad filter + internal pulls)** is **not tested**. It stays in the map under master: peripheral config.
- **The Phase 7 bodge (1.1 kΩ upstream)** produced no data, because Board 1 was destroyed. It is neither tested nor tombstoned.

### 2.6 Section 7 — Measurement trust

| Legacy or V7R result | Verdict | Load-bearing for | Pending |
|---|---|---|---|
| L-Ph20 SDA high ≥ 3.01 V vs V_IH 1.3 V | trustworthy (by margin) | D-revised tombstone; F-7 | none |
| L-Ph20 visual "ACK/NACK identical, no kink" | unknown | nothing | R2 only if needed |
| L-Ph21 V_OL ~650/750 mV, cable +100 mV, SCL "elevated" | suspect | nothing live (G-revised "confirmed" already invalid; fitted V_IL withdrawn) | R1 |
| L-Ph22 scope remark | unknown | nothing (null result is log-based) | none |
| L-Ph23 SDA V_OL ~50 mV | unknown, leaning plausible | G-revised tombstone | R1 |
| L-Ph23 SCL V_OL ~300 mV | suspect (inconsistent with SDA, same driver) | nothing | R1 channel swap |
| L-Ph25 | not tested | nothing | re-run individually only if the map needs it |
| L-Ph24a | log-based; trustworthy as a binary result; multi-variable | master: identity; F-5 | a same-family swap (§2.7) narrows it |
| Firmware baseline | HEAD = stacked Ph23–25 changes | every future card | `v7-clean` / `v6-ref` (test-workflow-setup) |

### 2.7 Section 8 — Next

```
- Open cards: none (V7R-000 sentinel).
- Proposed first cards (titles; IDs at pre-registration), all log-only:
  1. Fault re-established on v7-clean, L-Ph12 minimal repro, A/B/A — cuts firmware: drift/env (and sets the baseline every card cites)
  2. v6 on v6-ref under the exact L-Ph12 minimal repro, A/B/A — cuts the IS NOT (v6 so far proven with rigids, not the minimal repro)
  3. Symptom identity: SAMD21 master on v7 with a rigid on J6 — does VCNL 0x60 ACK? — cuts symptom identity
  4. Same-family master swap: Arduino Nano ESP32 (S3, own module and supply) as master on the v7 bus, U3 released — cuts master: module/path + master supply + copper-near-U3 vs die/core/driver
- Then, depending on 4: WROOM-1 devkit as master (same module, own supply and copper) or board-model-backed copper cards; first scope card = R1 (instrument validation on v7 + V_OL), then S3-vs-SAMD21 side-by-side capture at BQ pin 6.
- Blocked on: test-workflow-setup (baselines + lab/ containers for 1–4; scope tooling for R1 onward).
```

**Why this order** *(decisioning only)*:
- **Card 1** is housekeeping, but every card cites its baseline. It also tests the firmware: drift row (argued-refuted) directly.
- **Card 2:** the IS NOT has so far been shown with rigids, not with the cable + 10 kΩ reproducer. The cheapest error to rule out is "v6 would fail the minimal repro too".
- **Card 3:** what we're trying to explain depends on it. If VCNL still NACKs under SAMD21, the product failure and the BQ marker have separated, and the map splits in two.
- **Card 4** uses hardware already on hand (L-Ph3 used the Nano ESP32). Each outcome excludes something:
  - *ACK* → the die, the Arduino core's driver class and the generic S3 peripheral are excluded. The cause is in U3's module, its supply or its copper on v7.
  - *NACK* → v6's pass must then come from v6's bus side, not its master, and the copper/mux rows rise.
  - Confounds to declare on the card: the Nano ESP32 runs the Arduino core it ships with (record the version), injects at TPIO43/44 (5.9 mm from U3), and brings its own supply.
- **Topic 4's R1 recommendation is overridden** for first place (§5, D1).

**Board 2 option:** a v7 board whose BQ I²C pins are open (L-Ph8). If it still exists, a "rigid on Board 2: does VCNL ACK?" card is the cheapest test of symptom identity: causal. See §6.

---

## 3. Initiative sequence

### 3.1 Merge decision

**Accept topic 6 §10's merge:** one initiative, `test-workflow-setup`, covering topic 4 §6.1 and topic 6 §10.1. Topic 6's reasons hold:
- both create `lab/`;
- one dry run validates both;
- the context part is too small to stand alone.

Topic 6 §10.2's relay supersedes topic 4 §6.2's. `RELAY-planner.md` (next to this file) is built from §10.2.

### 3.2 Table

| Candidate | What it unblocks | What blocks it | Parallel? |
|---|---|---|---|
| **`test-workflow-setup`** (merged) | Every V7R card. **Log-only cards** need only part of it: the two baselines, `lab/` containers with the card template, and the debugger role. **Scope cards** need all of it: LAN capture, §4.2/§4.3 procedures, dry run. | Nothing technical. The user's edit pass on `debugger-role-draft.md` before the dry run. The ESP32-S3 V_OL datasheet check before the §4.3 number enters a procedure. | It *is* the first. Bench time inside it is the v6 dry run only. |
| **Debug track** (`lab/`, V7R cards) | Map progress; the fix decision. | Log-only cards: baselines + containers + role. Scope cards: the whole initiative. | **Yes**, with the later parts of `test-workflow-setup`. Log-only cards use the bench; the tooling work mostly doesn't, apart from the dry run. |
| **`pcb-board-model`** | Copper rows: bus copper, neighbours, reference planes; diff mode against v6. | Nothing technical. **Trigger:** a card makes a layout question load-bearing (most likely card 4 = NACK, or a WROOM-devkit ACK), or `test-workflow-setup` closes, whichever is first. | Yes in principle (no bench time). Held back by the user's one-initiative-at-a-time preference. kiutils probes bridge the gap (topic 6 §8.3). |
| **No-tooling swap tests** (PM rec 4) | The master and IS NOT rows. | Baselines and containers (input 9 below). Parts: none for cards 1–4. | They become debug-track cards 1–4, not a separate initiative. |

**Board-model timing (open question answered):** only when a layout question becomes load-bearing, or when `test-workflow-setup` closes. Not before the first v7 card. Reason: the four first cards are log-only, and none of their outcomes needs routing data to interpret. Card 4's outcome decides whether copper even matters.

**Parts to buy now (≪ budget):**
- a **spare LilyGO T-Display-S3**, to use v6's exact master on the v7 bus without unplugging the only known-good v6's module;
- an **ESP32-S3-DevKitC-1 N16R8** (the same WROOM-1 module as U3, with its own LDO and copper);
- **ground springs** for the Sensepeek probes (topic 4).

None of these needs a decision on mechanism. They are the swap fixtures P2 asks for.

### 3.3 Input 9: any bench test before `test-workflow-setup` lands?

**Not before any of it lands. Yes, before its scope tooling lands.**

- **Why log-only is valid now.** Topic 4's validity problem is with scope *numbers*: no setup validation, no metadata, no captures, an unrecorded cursor technique. Topic 4 explicitly kept the log-based Phase 22 null as trustworthy (T4 §2.3). A serial ACK/NACK result is binary, deterministic on this fault (F-2), and A/B/A-able within one flash. It has no instrument to validate.
- **Why not before the containers exist.** The two known failures that affect log results too are:
  - an **undeclared baseline**: HEAD is the stacked build (T4 §2.5);
  - an **unrecorded result**: Phase 25.

  Both are fixed by the baselines and the card + commit discipline, not by scope tooling. A log-only card run before `v7-clean` exists would inherit the Phase 23–25 stack. A card run before `lab/` exists would be recorded ad hoc, as Phase 25 was.
- **So:** the log-only cards in §2.7 become runnable the moment `v7-clean`, `v6-ref`, the card template and the debugger role exist. That is a dependency the Planner should see. The phasing is the Planner's call (topic 6 §10 already anticipated "context scope first" as an option).

---

## 4. Standing criteria

### 4.1 Input 10: fix-recommendation stance (PM rec 15)

What current evidence supports about v8, as of V7R-000:

- **Not supported: "I²C buffer between the bus and BQ".** It was derived for stories in which BQ's local SDA conditions were the cause (L-Ph12–15). L-Ph24a refuted Story H, and nothing shows a buffer would clear the *VCNL* failure, which is the product failure. Symptom identity is untested.
- **Weakly supported, by IS / IS NOT only: reverting master-side deltas toward v6.** That means CL-01 (module), CL-03 (separate MCU rail) and the master's copper. Its backing is "v6 worked and differs from v7 here". There is no mechanism behind it, so under P11 it is not a fix until a swap card shows the symptom following the delta, ideally A/B/A.
- **Not supported: any firmware mitigation.** None found (L-Ph22–24b), and a firmware change that makes the NACK vanish without an isolated mechanism is a lead, not a fix (P11).
- **No v8 design work** until §4.2's respin criteria hold, or a checkpoint opens a deliberate parallel respin track.

This stance is **re-derived at every step-back checkpoint** (topic 6 §4.3 step 3) and whenever a card moves a map row's strength. It is never carried forward unchanged.

### 4.2 Input 11: stop / redesign / outside-help triggers

**Adopt topic 5 §5.1–§5.3, with these adaptations:**

| Trigger | Adopted as | Adaptation |
|---|---|---|
| **Respin** (§5.1) | All three conditions: mechanism isolated and reproduced on more than one board; fix verified A/B/A on the current board; remaining unknowns cheaper on the new board | Add: symptom identity must be settled first, so the fix is shown to clear the **VCNL** failure, not just the BQ marker. |
| **Parallel respin track** (§5.1) | Allowed only by a checkpoint decision, recorded in the notebook as "not evidence about the mechanism" | Concrete trigger: every remaining untested region needs an irreversible test or an instrument we lack. A JLCPCB PCBA run is within the user's stated budget, so cost alone is not a blocker. |
| **Timebox** (§5.1) | Per region: **4 recorded cards** before that region must go through a checkpoint review. Overall: **15 recorded cards, or 8 calendar weeks** (~40–80 bench hours at the user's 5–10 h/week), whichever comes first, then a checkpoint that explicitly decides continue / parallel respin / outside help | Numbers are [own]. They are set in advance on purpose (Arkes & Blumer): don't renegotiate them mid-stream; change them only at a checkpoint, with a notebook entry. |
| **Forum / outside expert** (§5.2) | (a) A single interpretation-critical measurement decides a hypothesis; (b) two checkpoints in a row leave the map unchanged | Add (c): a card localises the cause to the S3 peripheral or core with a minimal repro. Then post to espressif/arduino-esp32 or esp-idf issues using the §5.2 format. |
| **Consultant** (§5.3) | When §5.2 has been tried and the fix decision is blocked on a measurement we can't make or validate (e.g. sub-ns edges beyond the DHO804) | Within the ~$500/month budget, prefer renting or borrowing an instrument or one paid review session over an open-ended engagement. |

**Where they live:**
- **The rules** go in the **debugger role's step-back checkpoint section**. They are standing rules that a role applies every time, and the user is editing that file anyway. The current draft points at expert-approaches §5.1–§5.3; replace that pointer with the adapted table above, or a pointer to this section.
- **The live counters** go in **STATE section 8**, as one line: `Timebox: N/15 cards · week W/8`. Per-region counts come from section 3's `Evidence` cells.

Note: the debugger role file is the user's to edit (topic 6 decision), so this is a recommendation, not an edit.

---

## 5. Disagreements with Stage A

| ID | Topic | Their recommendation | This session | Reason |
|---|---|---|---|---|
| D1 | 4 (§6) | R1 (V_OL re-measurement at BQ pins 5/6) is the first debug card | **Overridden:** R1 is the first *scope* card, after log-only cards 1–4 | Frame-lock check: R1 re-measures the last investigation's endpoint (G-revised), which is already tombstoned and load-bearing for nothing live (§2.6). The largest untested regions (symptom identity, master context) are cut by log-only cards that need no instrument validation. R1 keeps its value as v7 instrument validation and runs when a scope question becomes load-bearing. |
| D2 | 4 (§6) | Phase 25 experiments follow R1 if still relevant | **Deprioritised** | They sit in master: peripheral config, a row that fails the v6 IS NOT on its own (v6 ran the default knobs). Re-run only if card 4 points back at the S3 peripheral. |
| D3 | 1 (§2 row 14) | Routing asymmetry EMI: moderate–strong | Tombstoned as **argued** | Topic 3 showed the L-Ph16 clearances are centreline-based and overstated. The direction holds, but it's a geometry argument, not a measured exclusion. |
| D4 | 5 (P2) | A USB-I²C adapter is a reasonable known-good master | **Same-family masters first** (Nano ESP32, T-Display-S3, WROOM devkit); a non-S3 adapter later if needed | The v6 IS NOT makes "which S3 context" the sharper question. A SAMD21-like master has already been run (L-Ph24a). |
| D5 | 2 (CL-02) | Risk medium: "same pad function on the same die family" | **Adds a map row** (master: pin role) | GPIO43 is U0TXD and GPIO44 is U0RXD: the only SDA-vs-SCL asymmetry on the *master* side that anyone has named. It still needs CL-24 to explain v6, so it is a row to test, not a lead. |
| D6 | Legacy record | Probe sketch header says "Arduino Nano ESP32" wiring; L-Ph24a says SAMD21 Nano 33 IoT | **Treat L-Ph24a as SAMD21** (the results paragraph), and flag the discrepancy | The results paragraph is more specific. Card 4 must record the exact board. |

Accepted without change:
- topic 6's merge (§10);
- topic 6's §12 default for the assumptions register;
- topic 4's measurement-trust verdicts and its three corrections (G-revised pending R1, V_IL withdrawn, Phase 25 not tested);
- topic 3's recommendation of one three-phase board-model initiative (timing set in §3.2).

---

## 6. Open questions for the user

1. **v7 board inventory.** Topic 4 recorded "one, possibly two" undamaged v7 boards. Which exist, and in what state?
   - **B1:** bodge-damaged.
   - **B2:** BQ I²C open; never reflowed?
   - **B3:** healthy.
   - **Any further JLCPCB spares?**

   B2 as-is is the cheapest test of symptom identity: causal. A third healthy board would let the "no irreversible actions on the only good unit" rule relax.
2. **Approve the parts list** in §3.2 (spare T-Display-S3, ESP32-S3-DevKitC-1 N16R8, ground springs)? About $50 in total.
3. **Timebox numbers** (§4.2: 4 cards per region; 15 cards or 8 weeks overall): accept, or set your own now? Setting them now is the point.
4. **PR strategy** for `research/v7-retry`: deferred by you until after Stage B. Now that Stage B is written, one bundled PR (Stage A + B) before the Planner session is the natural cut, but it's your call.
5. **Debugger role edits:** fold §4.2 into the checkpoint section of `debugger-role-draft.md` when you do your edit pass?

---

## Observations for other topics / housekeeping

- **`test-workflow-setup` Planner:**
  - Card 4 needs a Nano ESP32 probe build. The existing sketch is SAMD21/Arduino-generic; record the core version.
  - Card 3 needs the SAMD21 sketch's VCNL-through-PCA path. The sketch probes 0x60 but doesn't open PCA channels.

  Both are card-level test code for the debug track, not initiative scope. Noted so the Planner doesn't put them in scope by mistake.
- **Legacy record:** the probe sketch's header describes "Arduino Nano ESP32" wiring while L-Ph24a used a Nano 33 IoT (D6). Not edited (`docs/debugging/` is frozen).
- **F-10 follow-up:** check whether arduino-esp32 2.0.14's bundled IDF contains the #8543 fix. It's a five-minute lookup for whichever card first needs the firmware: core row.

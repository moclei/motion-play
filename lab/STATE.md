---
as_of: V7R-003            # highest card ID with status recorded|abandoned that this file reflects (V7R-000 = sentinel, nothing recorded)
updated: 2026-10-23       # date of the last edit
last_checkpoint: V7R-003  # card ID at which the last step-back checkpoint ran (context-strategy §4.3)
open_cards: [V7R-004]                 # cards with status pre-registered|run; must match lab/cards/ (checked)
---

# v7 I²C fault — current state

> Debugger sessions: this is L0. Other sessions: read sections 1–4 and stop.
> Never restate a result here. Cite its card. Max ~150 lines; the check warns beyond that.
> Sections 1–8 seeded from `docs/research/v7-retry/decisioning.md` §2 (context-strategy §4.4); section 6 from the baseline tags and notebook 2026-10-21 s02.

## 1. Symptom                                   (≤ 6 lines)
Observable behaviour only, in operator terms: what fails, how it is seen, the minimal repro config. No mechanism words.
On v7 (B1 before rework, B3), on-board ESP32-S3 master, diag loop (`motion-play-v7-diag`): with a TCA channel open whose connector carries a cable with SDA tied to +3.3 V at the far end (4.7–47 kΩ, or a sensor rigid), BQ24195 0x6B returns X(2) (NACK on address) on every probe; INA219 0x40 and TCA 0x70 return '.'.
With a rigid: PCA 0x76 '.', VCNL4040 0x60 X(2), no sensor data.
Minimal repro: cable in J6, 10 kΩ SDA→+3.3 V at far end, SCL wire dangling; TCA2 row shows BQ:X(2).
Removing the far-end path: next probe shows BQ:'.'. Empty or closed channel: BQ:'.'.

## 2. IS / IS NOT                               (KT table, ≤ 12 rows)
Every candidate cause in section 3 must explain both columns; Distinction is what is true only of IS; Evidence is V7R-/L-Ph/CL- IDs.
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
| When | every probe while channel open and path present; steady state | after channel close or path removal (next probe); never cleared by 3× START/STOP | live, not latched | L-Ph12, L-Ph14, L-Ph15, V7R-003 |
| Firmware knobs | 400 kHz default init (pre-debug; `v7-clean`), 100 k, 50 k, CAP_3, deglitch 7 | none found that clears it | none found | L-Ph1–4, L-Ph22, L-Ph23, L-Ph24b, V7R-003 |
| Regime | VBUS present; battery pads only; WiFi on and off | none found | none found | L-Ph6b, L-Ph18 |
| Extent | 100% deterministic on 2 healthy-assembly v7 boards | intermittent; board-specific | design-level | L-Ph4, L-Ph9 |

## 3. Hypothesis map                            (one row per region, ≤ 25 rows)
Status (untested | tested) says whether a test has touched the region; Strength (argued | measured-supported | measured-refuted | not tested) says what the evidence is worth. A region with no rows is listed as "no hypothesis yet".
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
| firmware: drift | Debug-stack drift since `4da1c67` causes it | tested (partly) | measured-refuted for the five stacked I²C-init changes; argued-refuted for the rest (diag code, F-6) | V7R-003, CL-25, F-6 | V7R-003 |
| firmware: env | v7 env/variant change (devkitc variant, no display init, STARTUP_I2C_SCAN, boot order) | untested | not tested | CL-24 | — |
| firmware: core | arduino-esp32 2.0.14 / legacy IDF I²C driver behaviour (#8543 class) | untested | not tested; fails v6 IS NOT on its own (same core on v6) | F-10, CL-24 | — |
| power regime | no live hypothesis; control variable (VBUS / battery / WiFi state) | tested | measured-refuted as cause | L-Ph6b, L-Ph18 | L-Ph18 |
| measurement | Any v7 scope number is an artefact until §4.2 setup validation passes on that session | untested | not tested | T4 §2.6 | T4 |
| power: other | no hypothesis yet (BQ charger switching, boost, LDO noise beyond L-Ph14's far-end test) | untested | not tested | — | — |

## 4. Facts in use                              (≤ 15 rows)
Only facts load-bearing for section 3; inferences are labelled "argued" and never promoted silently.
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

## 5. Tombstones                                (one line each, never deleted)
`<hypothesis> — refuted by <ID> — <strength> — notebook <date>`; the full narrative lives in the notebook or the legacy doc only.
- Sensor-side defect (VCNL/PCA/flex) — refuted by L-Ph3 — measured-refuted (strong) — legacy Ph3
- Pull-up strength / rise time — refuted by L-Ph2, L-Ph5 — measured-refuted (weak: combined 1.5–2.1 kΩ only) — legacy Ph5
- I²C clock speed — refuted by L-Ph2, L-Ph22 — measured-refuted (moderate) — legacy Ph22
- ESP32 RF coupling — refuted by L-Ph6b — measured-refuted (moderate; also skips WiFi/MQTT init) — legacy Ph6
- Per-channel routing defect — refuted by L-Ph6c — measured-refuted (strong) — legacy Ph6
- Cable stub capacitance/inductance alone — refuted by L-Ph5, L-Ph6d — measured-refuted (strong) — legacy Ph6
- BQ in a documented I²C-suppressing mode — L-Ph10 — argued (datasheet silence); moot after L-Ph24a — legacy Ph10
- Rail perturbation through cable loop — refuted by L-Ph11 — measured-refuted (moderate; ~330 µA never measured) — legacy Ph11
- SCL as the trigger line — refuted by L-Ph12 — measured-refuted (strong, A/B/A) — legacy Ph12
- Story A naive (phantom START) / Story B naive (edge degradation) — L-Ph13 — measured-refuted, naive forms only (moderate) — legacy Ph13
- Story C: 3.3 V rail noise via the far-end source — refuted by L-Ph14 — measured-refuted (strong, A/B/A) — legacy Ph14
- Story A residual: stuck slave state machine — refuted by L-Ph15 — measured-refuted (strong, narrow claim) — legacy Ph15
- Routing-asymmetry EMI (SDA routed worse than SCL) — L-Ph16 — argued (geometry; centreline numbers overstated, direction holds per T3) — legacy Ph16
- Story D original: ESD-diode injection at BQ — L-Ph17 — argued (datasheet inference) — legacy Ph17
- Cable as EMI antenna — L-Ph17 — argued (geometry, untested) — legacy Ph17
- USB-C / VBUS state — refuted by L-Ph18 — measured-refuted (moderate) — legacy Ph18
- Story D-revised: V_IH violation via crosstalk — refuted by L-Ph20 — measured-refuted (strong; margin exceeds any probe artefact, T4) — legacy Ph20
- Story G-revised: V_IL violation via V_OL rise — refuted by L-Ph23 — measured-refuted, pending R1 — legacy Ph21–23
- Story H: BQ input fault regardless of master — refuted by L-Ph24a — measured-refuted (strong for "master-dependent") — legacy Ph24a
- I²C-controller deglitcher (Exp 1) — refuted by L-Ph24b — measured-refuted (moderate; stacked on 100 kHz + CAP_3) — legacy Ph24b
- Five stacked I²C-init debug changes (Ph22–25) as the cause — refuted by V7R-003 — measured-refuted (one board, A/B/A, 10/10 per arm) — notebook 2026-10-23
- Not tombstoned: L-Ph25 (pad filter + internal pulls) not tested, stays under master: peripheral config; L-Ph7 bodge (1.1 kΩ upstream) no data (B1 destroyed).

## 6. Baselines and bench state                 (≤ 15 lines)
Baselines (tag → commit, I²C init in one line); boards (ID | condition | mods | role); flashed now (board → commit + env, with the card ID that set it); cables and fixtures in the failing config.
- Baselines: `v7-clean` → 90053af (Wire.begin(43, 44), 400 kHz, CAP_2, no filters, default pulls; STARTUP_I2C_SCAN true; envs motion-play-v7, -diag, -busrec, -relbus). `v6-ref` → 4da1c67 (same init; STARTUP_I2C_SCAN false; env lilygo-t-display-s3).
- Boards: v6 | healthy | ~10 mm wire on pad C (U2.14, GND), V7R-001 | known-good reference, on the bench.
- Boards: v7 #0003 (panel marking; believed B3, not confirmed) | healthy | none known | the v7 on the bench (V7R-003); treated as the only good unit.
- Legacy: v7 B1 | bodge-damaged (L-Ph7) | rework | none. v7 B2 | BQ I²C open (L-Ph8), never reflowed? | none known | symptom identity: causal, if it still exists. v7 B3 | healthy | none known | only good unit (no irreversible actions); likely #0003.
- Flashed now: v6 → v6-ref 4da1c67, lilygo-t-display-s3 (V7R-002 S2 step F). v7 #0003 → v7-clean 90053af, motion-play-v7-diag (V7R-003 S3).
- Bench at last stop (notebook 2026-10-23 s01): v7 #0003 unpowered (USB-C cable left in J7, Mac end unplugged = power toggle), pigtail in J6 (black = pin 1 +3.3 V, red = pin 2 GND, blue = pin 3 SDA, yellow = pin 4 SCL), black in breadboard with the 10 kΩ, blue out; v6 off the bench; probes on scope Cal ground.
- Failing config fixtures: cable in J6 with 10 kΩ SDA→+3.3 V at the far end, SCL wire dangling (L-Ph12); sensor rigid on J4/J5/J6.

## 7. Measurement trust                         (≤ 10 rows; rows leave when re-measured)
Verdict is trustworthy | suspect | unknown | not tested; a row is deleted when a V7R card re-measures it.
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

## 8. Next                                      (≤ 6 lines)
Open cards (ID, title, arm reached); proposed next test (which map region it cuts, and why); blocked on (initiatives, parts, decisions).
- Open cards: V7R-004 (Nano ESP32 master swap), pre-registered. V7R-003 recorded (v7 baseline set: fault reproduces at `v7-clean`).
- Queue, all log-only: (2) v6 on v6-ref under the L-Ph12 minimal repro, A/B/A — cuts the v6 IS NOT (proven with rigids only); (3) SAMD21 master on v7, rigid on J6: does VCNL 0x60 ACK? — cuts symptom identity; (4) Arduino Nano ESP32 as master on the v7 bus, U3 released — cuts master: module/path, master supply, copper near U3 vs die/core/driver.
- Runnable now: card 4 (existing probe sketch, v7 bench as is). Blocked → Planner relay: card 2 (v6-ref has no diag loop), card 3 (probe sketch never opens a PCA channel, so VCNL behind a rigid is unreachable). Card 3 outranks 4 on what it decides. Then, depending on 4: WROOM-1 devkit as master or board-model-backed copper cards; first scope card = R1 (instrument validation on v7 + V_OL), then S3-vs-SAMD21 capture at BQ pin 6.
- Timebox: 3/15 cards · week 1/8 (from V7R-001, 2026-10-20). Last checkpoint V7R-003 (notebook 2026-10-23).
- Blocked on: Planner relay for cards 2 and 3 (tools only); nothing blocks card 4.

## 9. Lookups (L1 routing)                      (≤ 15 rows)
Where to go for detail that is not L0; load only the named section or query.
| When you need… | Load | Section/query |
|---|---|---|
| a v6/v7 difference | docs/research/v7-retry/v6-v7-changelist.md | §3 by CL-ID (`grep -n "CL-NN"`); §5 observations |
| a legacy phase (`L-PhNN`) | docs/debugging/v7-i2c-investigation.md | `grep -n "^### Phase NN"` |
| row audit, card-order reasoning, standing criteria | docs/research/v7-retry/decisioning.md | §2.3 row audit; §2.7 why this order; §4 standing criteria; §6 board inventory |
| baseline build names and I²C init | `git tag -n20 v7-clean` / `v6-ref` | tag message |
| flashing and cable workflow (v6 T-Display) | firmware/CONTEXT.md | `grep -n "Development Cable Workflow"` |
| sensor connector pinout, mux chain | hardware/CONTEXT.md | `grep -n -i "JST-SH\|mux"` |
| v7 probe pads (labelled picture) | lab/procedures/img/v7-probe-points.png | whole image; make new ones with tools/lab/probe_points/ |
| scope setup (validation V1–V9, known-good reference) | lab/procedures/ | `dho804-setup-validation.md` every scope session; `known-good-reference.md` for V9 |

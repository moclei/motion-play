---
as_of: V7R-013            # highest card ID with status recorded|abandoned that this file reflects (V7R-000 = sentinel, nothing recorded)
updated: 2026-10-25       # date of the last edit
last_checkpoint: V7R-011  # card ID at which the last step-back checkpoint ran (context-strategy §4.3)
open_cards: [V7R-014]                       # cards with status pre-registered|run; must match lab/cards/ (checked)
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
| What: master | ESP32-S3-WROOM-1 (U3, die rev v0.2) on v7 | SAMD21 (Nano 33 IoT) and ESP32-S3 Nano ESP32 (rev v0.1, own module + supply, core 2.0.18 or 2.0.14) at TPIO43/44 on the same v7 bus and config; ESP32-S3R8 (T-Display) on v6 | WROOM module and pad path; master supply shared with the pull-up rail; copper U3→TPIO (5.9 mm); GPIO43/44 pin role; die rev (not the image: V7R-006; not the core: V7R-007); at U5.6 SDA low 0.90 V under U3 vs 0.11 V under the Nano (V7R-009), already at U3's own pad (V7R-010) | L-Ph24a, V7R-004, V7R-006, V7R-007, V7R-009, V7R-010, F-1, F-13, CL-01/02/03/24 |
| Where: board | v7 B1 (pre-bodge), B3 | v6 | everything in changelist §3; short list §5 | L-Ph9, F-1 |
| Where: channel | any channel carrying the trigger cable (J4/J5/J6) | empty channel; closed channel | follows the cable, not the route | L-Ph6c, L-Ph4 |
| Where: line | far-end DC path on SDA | far-end DC path on SCL only | SDA is bidirectional (slave drives ACK); GPIO43 = U0TXD, GPIO44 = U0RXD; SDA neighbours (CHRG_INT) | L-Ph12, CL-02, T3 |
| Condition: polarity | far-end path to +3.3 V (main rail or clean bench PSU) | far-end path to GND; VCC–GND resistor only | ~70 µA sourced into SDA at the far end while low; downstream node held at 3.3 V | L-Ph11, L-Ph13, L-Ph14 |
| Condition: load | any R from 4.7 k to 47 k, or a rigid | cable with no far-end path (stub only) | DC path present, not R value or C | L-Ph5, L-Ph6d |
| When | every probe while channel open and path present; steady state | after channel close or path removal (next probe); never cleared by 3× START/STOP | live, not latched | L-Ph12, L-Ph14, L-Ph15, V7R-003 |
| Firmware knobs | 400 kHz default init (pre-debug; `v7-clean`), 100 k, 50 k, CAP_3, deglitch 7; U3 running the raw-`Wire` probe sketch (no v7 init) | none found that clears it on U3 | none found | L-Ph1–4, L-Ph22, L-Ph23, L-Ph24b, V7R-003, V7R-006 |
| Regime | VBUS present; battery pads only; WiFi on and off | none found | none found | L-Ph6b, L-Ph18 |
| Extent | 100% deterministic on 2 healthy-assembly v7 boards | intermittent; board-specific | design-level | L-Ph4, L-Ph9 |

## 3. Hypothesis map                            (one row per region, ≤ 25 rows)
Status (untested | tested) says whether a test has touched the region; Strength (argued | measured-supported | measured-refuted | not tested) says what the evidence is worth. A region with no rows is listed as "no hypothesis yet".
| Region | Hypothesis (one line) | Status | Strength | Evidence | Last touched |
|---|---|---|---|---|---|
| master: identity | Something about U3's context on v7 (not BQ alone, not an S3 master as such, not the v7 image, not core 2.0.14) causes the NACK; which property is unknown | tested | measured-supported (two non-U3 masters ACK, the Nano on both cores; U3 NACKs on two images; property not isolated) | L-Ph24a, V7R-004, V7R-006, V7R-007 | V7R-007 |
| master: module/path | WROOM-1 module, its pad path, die rev (v0.2 vs Nano v0.1) or copper U3→TPIO is the distinguishing factor | tested (bundle) | measured-supported (bundle with supply, pin role, board variant; image removed by V7R-006, core by V7R-007; not separated); V7R-009: the bundle shows at U5.6 as SDA V_OL 0.90 vs 0.11 V; V7R-010: the same low at U3's pad 37, so it comes from U3 or its pad load, not the copper after it; V7R-012: not set by the pad's drive setting; V7R-013: ~0.68 V of it remains with the far-end path out | CL-01, CL-02, V7R-004, V7R-006, V7R-007, V7R-009, V7R-010, V7R-012, V7R-013 | V7R-013 |
| master: pin role | GPIO43's UART0-TX role (ROM boot output, IO_MUX/matrix state, any Serial0 use) leaves the SDA pad unlike SCL's | tested (bundle) | measured-supported (bundle; U3 NACKs with v7 image and probe sketch alike); V7R-008 void: Nano on GPIO43/44 lost every device after iteration 1, not separated. V7R-011: at run time GPIO43 and GPIO44 read back identically (GPIO matrix, I²C signals 90/89, open-drain, drive 2, pull-up, no filter; no UART routing) — measured-refuted for run-time pad configuration; ROM/boot-time state not covered | CL-02, CL-24, V7R-004, V7R-006, V7R-008, V7R-011 | V7R-011 |
| master: peripheral config | A controller or pad setting (clock, drive, deglitch, pad filter, internal pulls) gates it | tested (partly) | measured-refuted for clock, CAP_3, deglitch (stacked); SDA and SCL pads identical in drive, pulls, open-drain and filter at run time (V7R-011); GPIO43 CAP_2→CAP_3 moves U3's SDA low by −18 mV and BQ still NACKs: drive is not what sets the low (V7R-012); changing pad filter or pulls not tested | L-Ph22, L-Ph23, L-Ph24b, L-Ph25, V7R-011, V7R-012 | V7R-012 |
| master: timing | S3 SDA hold/setup relative to SCL, as shaped by the far-end path, falls outside BQ's (and VCNL's) tolerance but inside INA/TCA's | untested | argued (V7R-004: a generic S3 at TPIO got ACK; timing captured in V7R-009 CSVs, not evaluated: Planner relay 2026-10-24) | F-3, F-9, V7R-004, V7R-009 | V7R-009 |
| master supply | Shared +3.3 V rail (MCU I/O = pull-up rail; AMS1117 + as-built caps) changes how the master's pad relates to the bus | tested (bundle) | measured-supported (bundle with module/path; not separated; V7R-009 level difference is in the bundle) | CL-03, CL-08, CL-14, V7R-004, V7R-006, V7R-009 | V7R-009 |
| bus copper | v7 SDA route (B.Cu under BT1, ~6.8 mm with no In2 under it, In2 +3.3 V reference) degrades S3-driven SDA edges but not SAMD21's | tested (partly) | measured-refuted for TPIO→BQ with an S3 master at TPIO (V7R-004); measured-refuted as where U3's SDA low is lost, U3 pad → TPIO43 → U5.6 (V7R-010) | F-8, CL-19–21, T3, V7R-004, V7R-010 | V7R-010 |
| bus copper: neighbours | SCL (0.20 mm gap) or CHRG_INT (<0.5 mm) couples into SDA | untested | not tested | F-8, T3 | — |
| mux | TCA channel-open with a far-end pull-up changes the upstream SDA node (pass-gate state, idle level) in a way only U3's context reacts to | tested (bundle) | measured-supported (bundle: rigid off the far end lowers U3's SDA low by ~220 mV to ~0.68 V and BQ ACKs, A/B/A; pull-ups, PCA/VCNL load, rail draw and pass-gate level not separated, V7R-013); V7R-004: an S3 at TPIO doesn't react | A-1, L-Ph5, L-Ph6d, L-Ph13, V7R-004, V7R-013 | V7R-013 |
| slave: BQ × master | BQ's input requirement is stricter than INA/TCA's (e.g. V_IL), met by the Nano, missed by U3's ~0.90 V SDA low | untested | argued: repo datasheet text gives VCNL4040 V_IL 0.4 V (NACKs) and PCA9546A V_IL 0.3×VCC ≈ 0.99 V (ACKs), which fits a 0.90 V low; BQ/INA/TCA values unchecked. L-Ph23's ~50 mV at CAP_3 not reproduced (V7R-012: 880 mV at TPIO43, BQ NACK), so not tested by it. V7R-013: under U3, BQ ACKs at ~0.68 V (path out) and NACKs at ~0.90 V (path in), consistent with a BQ threshold between, not separated from the rigid bundle. Desk (c) 2026-10-25 (F-14): datasheet V_IL max sorts all five devices, 0.4 V class NACK and 0.3 × V_CC class ACK under U3's 0.90 V; argued, magnitude fits; lead status is the V7R-014 checkpoint's call | F-9, F-13, F-14, L-Ph21, L-Ph23, L-Ph24a, V7R-009, V7R-012, V7R-013 | desk (c) |
| slave: INA, TCA, PCA | no hypothesis yet (they ACK; used as controls) | untested | not tested | L-Ph4 | — |
| symptom identity | VCNL NACK (product failure) is the same fault as BQ NACK (diag marker) | tested | measured-supported (both follow the master, A/B/A; one board, one rigid; rigid as trigger) | A-2, L-Ph4, V7R-005 | V7R-005 |
| symptom identity: causal | BQ's NACK state or input disturbs the bus for downstream devices (BQ causal), vs common cause | untested | not tested | L-Ph8 (B2: BQ I²C open) | — |
| cable / far end | no live hypothesis; trigger characterised (SDA, +3.3 V, DC path, R-independent); V7R-013: it also raises U3's SDA low by ~220 mV | tested | measured (as trigger) | L-Ph5, L-Ph6d, L-Ph11–15, V7R-013 | V7R-013 |
| cable mating | 4-pin socket vs 4-in-5 (CL-16) | untested | argued-refuted (SAMD21 ACKs through the same mating) | CL-16, L-Ph24a | — |
| firmware: drift | Debug-stack drift since `4da1c67` causes it | tested | measured-refuted for the five stacked I²C-init changes (V7R-003) and for the v7 image as a whole incl. diag code (V7R-006) | V7R-003, V7R-006, CL-25, F-6 | V7R-006 |
| firmware: env | v7 env/variant change (devkitc variant, no display init, STARTUP_I2C_SCAN, boot order) | tested (partly) | measured-refuted for the image (boot order, STARTUP_I2C_SCAN, BQ/INA/GPIO init); devkitc variant and build flags held, not tested | CL-24, V7R-006 | V7R-006 |
| firmware: core | arduino-esp32 2.0.14 / legacy IDF I²C driver behaviour (#8543 class) | tested | measured-refuted as sufficient with an S3 master on this bus: Nano on 2.0.14 ACKs (V7R-007); also fails v6 IS NOT (same core on v6) | F-10, CL-24, V7R-004, V7R-007 | V7R-007 |
| power regime | no live hypothesis; control variable (VBUS / battery / WiFi state) | tested | measured-refuted as cause | L-Ph6b, L-Ph18 | L-Ph18 |
| measurement | Any v7 scope number is an artefact until §4.2 setup validation passes on that session | tested | validated at S2 (V7R-009, V7R-010) and at the master end, ground C9.1: TPIO43/44 and U3 pad 37 (V7R-010) | T4 §2.6, V7R-009, V7R-010 | V7R-010 |
| power: other | no hypothesis yet (BQ charger switching, boost, LDO noise beyond L-Ph14's far-end test) | untested | not tested | — | — |

## 4. Facts in use                              (≤ 15 rows)
Only facts load-bearing for section 3; inferences are labelled "argued" and never promoted silently.
| Fact | Strength | Source |
|---|---|---|
| F-1 v6 ran 6 sensors through TCA + PCA with BQ and INA on the bus, 0 I²C errors, 400 kHz, T-Display ESP32-S3 master on GPIO43/44, core 2.0.14 (2026-04-14) | measured (session data); board identity argued (strong) | changelist §1a, CL-24 |
| F-2 Trigger: TCA channel open + cable + far-end DC path SDA→+3.3 V, any R from 4.7 k to 47 k; stub-only, SCL-only, SDA→GND and VCC–GND-only pass; live A/B/A | measured-supported (strong, repeated) | L-Ph5, L-Ph6d, L-Ph11–14 |
| F-3 Failure is NACK on address (code 2), never timeout; not cleared by 3× START/STOP. F-4 In the failing state INA 0x40 and TCA 0x70 ACK; with a rigid, PCA 0x76 ACKs and VCNL 0x60 NACKs | measured | L-Ph6a, L-Ph15 (F-3); L-Ph4, L-Ph9 (F-4) |
| F-5 SAMD21 master (Nano 33 IoT, 100 kHz, via TPIO43/44, U3 released) gets BQ ACK in the failing config; single session; master, clock source, drive, library all differ | measured-supported (one run, multi-variable) | L-Ph24a; probe sketch |
| F-6 Fault present before the debug firmware stack (v6-era init, 400 kHz) | argued (chronology) | L-Ph1–4, CL-25 |
| F-7 At BQ pin 6 in the NACK window, SDA high ≥ 3.01 V; scope decode reads `Write:D6 A:1` | measured (trustworthy by margin) | L-Ph20, T4 §2.3 |
| F-8 SDA 72.9 mm (F 35.9 / B 37.0); 37 mm on B.Cu under BT1; B.Cu runs reference In2 +3.3 V, ~6.8 mm SDA / ~7.4 mm SCL over no In2 copper (x 105–111, y 122–123); SDA–SCL gap 0.20 mm; SDA < 0.5 mm from CHRG_INT. Relevance: **unassessed** | measured (read-only probes) | T3 §3 |
| F-9 BQ is the farthest SDA load from U3 (47.7 mm; INA 31.7 mm, TCA 19.4 mm) | measured | T3 §3 |
| F-10 espressif/esp-idf #8543: ESP32-S3 master clocked SCL after STOP on IDF release/v4.4, fixed 2022; original ESP32 unaffected. Relevance: **unassessed** (whether core 2.0.14's IDF includes the fix is unchecked) | reference | T5-ref |
| F-11 Sensor module (rigid + flex + VCNL) works with an Arduino Nano ESP32 master on J1 | measured (strong) | L-Ph3 |
| F-12 Nano ESP32 (S3 rev v0.1, core 2.0.18-arduino.5, own supply) at TPIO43/44, U3 released, failing config: BQ ACKs; U3 (rev v0.2) NACKs before and after; ~243 mm wire on the bus in all arms | measured-supported (one board, A/B/A; bundle) | V7R-004 |
| F-13 At U5.6/U5.5, failing config (rigid #1 on J6), 400 kHz: address byte D6, SCL period and rise times equal under U3 and Nano; SDA V_OL ~0.90 V under U3 (NACK), ~0.11 V under the Nano (ACK); SCL lows ~0.1 V under both. Under U3 the SDA low is the same at U3 pad 37, TPIO43 and U5.6 (within 2 mV); at TPIO43 898 mV at CAP_2 vs 880 mV at CAP_3 (GPIO43 only), BQ NACK at both; 898 mV with rigid #1 on the J6 cable vs 678 mV with the cable as a stub, BQ ACK 100 % at 678 mV | measured-supported (validated scope, one board, A/B/A and A/B/C/A, 3 captures per arm) | V7R-009, V7R-010, V7R-012, V7R-013 |
| F-14 SDA/SCL V_IL max from datasheets: BQ24195 0.4 V fixed (V_IH 1.3 V; spec'd at V_PULL-UP 1.8 V); VCNL4040 0.4 V (V_IH 1.55 V at VDD 3.3 V); INA219, TCA9548A, PCA9546A 0.3 × V_CC = 0.99 V at 3.3 V. The two fixed-0.4 V devices NACK under U3, the three 0.3 × V_CC devices ACK. V_IL max is a guaranteed limit, not the switching point (BQ ACKs at ~0.68 V in V7R-013) | reference (datasheet values); the split vs ACK/NACK is argued | TI SLUSB97A p9 §7.5; TI SBOS448G p5; TI SCPS207H p4 §5.3; repo vcnl4040_datasheet_text L202, pca9546a_datasheet_textonly L311 |
| A-1 TCA9548A pass gate: with no downstream pull-up, the downstream side idles below VCC (pass-gate limited), so "stub only" and "stub + far-end pull-up" also differ in downstream idle level | argued (datasheet behaviour; not verified this session; not measured on v7) | TI TCA9548A datasheet [verify] |
| A-2 "BQ is first to fail because it's farthest, and VCNL fails from the same bus margin" | argued for "farthest / bus margin" (not tested); "same fault" part measured-supported (V7R-005) | L-Ph4, V7R-005 |

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
- An S3 master as such (die family, arduino-esp32 2.0.x driver class) or the TPIO→BQ bus with an S3 master gives the NACK — refuted by V7R-004 — measured-refuted (one board, A/B/A, 10/10 per arm; die rev and core differ) — notebook 2026-10-23
- VCNL NACK and BQ marker as separate faults — refuted by V7R-005 — measured-refuted (one board, one rigid, A/B/A, VCNL 20/20, BQ 10/10 per arm) — notebook 2026-10-23
- The v7-clean image (boot order, startup scan, BQ/INA/GPIO init, diag-loop code) as necessary for the NACK on U3 — refuted by V7R-006 — measured-refuted (one board, one rigid, A/B/A, VCNL 20/20, BQ 10/10 per arm; core 2.0.14 and devkitc variant held) — notebook 2026-10-23
- Core 2.0.14 (espressif arduino-esp32) as sufficient for the NACK with an S3 master on this bus — refuted by V7R-007 — measured-refuted (one board, one rigid, one Nano, A/B/A, VCNL 20/20, BQ 10/10 per arm) — notebook 2026-10-23
- SDA low lost along the copper U3 pad → TPIO43 → U5.6 (series fault or drop on the route) — refuted by V7R-010 — measured-refuted (one board, A/B/C/A, anchor amended to TPIO43, 3 captures per arm) — notebook 2026-10-25
- GPIO43 (SDA) pad configured unlike GPIO44 (SCL) at run time (IO_MUX function incl. UART0, matrix signal, inversion, open-drain, drive, pulls, filter) — refuted by V7R-011 — measured-refuted (one board, two boots, 42 dumps; firmware-readable registers only) — notebook 2026-10-25
- GPIO43 drive strength (CAP_2 vs CAP_3) as what sets U3's ~0.90 V SDA low — refuted by V7R-012 — measured-refuted (one board, A/B/A, 3 captures per arm, 400 kHz, SDA only; Δ −18 mV) — notebook 2026-10-25
- U3's SDA low independent of the far-end path (the whole ~0.90 V present without it) — refuted by V7R-013 — measured-refuted (one board, one rigid, A/B/A, 3 captures per arm; −219 mV with the path out, ~0.68 V remains) — notebook 2026-10-25
- Note (V7R-009): G-revised's basis (L-Ph23 SDA V_OL ~50 mV) is contradicted by a validated ~0.90 V at U5.6 under U3; the low-level story is live again in §3 (slave: BQ × master; master bundle). V7R-012 did not reproduce L-Ph23's ~50 mV at CAP_3 (880 mV at TPIO43, 400 kHz, SDA only). Not tombstoned: L-Ph25 (pad filter + internal pulls) not tested, stays under master: peripheral config; L-Ph7 bodge (1.1 kΩ upstream) no data (B1 destroyed).

## 6. Baselines and bench state                 (≤ 15 lines)
Baselines (tag → commit, I²C init in one line); boards (ID | condition | mods | role); flashed now (board → commit + env, with the card ID that set it); cables and fixtures in the failing config.
- Failing config fixtures: cable in J6 with 10 kΩ SDA→+3.3 V at the far end, SCL wire dangling (L-Ph12); sensor rigid on J4/J5/J6. Baselines: `v7-clean` → 90053af (Wire.begin(43, 44), 400 kHz, CAP_2, no filters, default pulls; STARTUP_I2C_SCAN true; envs motion-play-v7, -diag, -busrec, -relbus). `v6-ref` → 4da1c67 (same init; STARTUP_I2C_SCAN false; env lilygo-t-display-s3).
- Boards: v6 | healthy | ~10 mm wire on pad C (U2.14, GND), V7R-001 | known-good reference, on the bench. v7 #0003 (panel marking; believed B3, not confirmed; U3 die rev v0.2) | healthy | ~68 mm 26 AWG wires soldered on TPIO43 (green) and TPIO44 (yellow), fitted before V7R-004 | the v7 on the bench; treated as the only good unit. Arduino Nano ESP32 (S3 rev v0.1) | healthy | none | external S3 master (V7R-004). Legacy: v7 B1 | bodge-damaged (L-Ph7) | rework | none. v7 B2 | BQ I²C open (L-Ph8), never reflowed? | none known | symptom identity: causal, if it still exists. v7 B3 | healthy | none known | only good unit (no irreversible actions); likely #0003.
- Flashed now: v6 → v6-ref 4da1c67, lilygo-t-display-s3 (V7R-002 S2 step F). v7 #0003 → v7-clean 90053af, motion-play-v7-diag (V7R-013 end revert, 22:18). Nano ESP32 → blank sketch, 2.0.18 hwcdc build (V7R-009 revert; not reflashed since).
- Bench at last stop (notebook 2026-10-25 s08, V7R-013): v7 #0003 and Nano unpowered (USB-C cables in, Mac ends unplugged). J6: rigid #1 (SW1 ON = PCA 0x76; flex + 2 VCNL) via ~400 mm cable, re-plugged at the rigid end in V7R-013. J5: pigtail, black in 'V' rail with the 10 kΩ, blue + yellow dangling, red in Nano GND column. Pad wires green/yellow → ~175 mm Dupont → Nano A4/A5. J4 empty. v6 off bench. Probes lifted off the board; operator: "pads look fine". Scope on, decode set.

## 7. Measurement trust                         (≤ 10 rows; rows leave when re-measured)
Verdict is trustworthy | suspect | unknown | not tested; a row is deleted when a V7R card re-measures it.
| Legacy or V7R result | Verdict | Load-bearing for | Pending |
|---|---|---|---|
| L-Ph20 SDA high ≥ 3.01 V vs V_IH 1.3 V | trustworthy (by margin) | D-revised tombstone; F-7 | none |
| L-Ph20 visual "ACK/NACK identical, no kink" | unknown | nothing | R2 only if needed |
| L-Ph22 scope remark | unknown | nothing (null result is log-based) | none |
| L-Ph23 SCL V_OL ~300 mV | suspect (inconsistent with SDA, same driver) | nothing | R1 channel swap |
| L-Ph25 | not tested | nothing | re-run individually only if the map needs it |
| L-Ph24a | log-based; trustworthy as a binary result; multi-variable | master: identity; F-5 | none (V7R-004 replicates master-dependence with an S3) |

## 8. Next                                      (≤ 6 lines)
- V7R-012 (row 1: GPIO43 drive not a lever on the low) and V7R-013 (row 3: far-end path out → low −219 mV to ~0.68 V, BQ ACKs) recorded. Open question: what holds U3's SDA low at ~0.68 V with no far-end path while the Nano reaches ~0.11 V, and does the low track sink current. Candidates (user's choice; all at S1): (e) static low-drive GPIO43 vs GPIO44 as plain open-drain GPIO, I²C off (needs a build); SDA low vs added sink current at TPIO43 (e.g. a known resistor to +3.3 V, design TBD). Desk (c) done 2026-10-25 (F-14).
- Open cards: V7R-014 (static low GPIO43 vs GPIO44, I²C detached; pre-registered, not run; firmware delta u3-static approved). Timebox: 14/15 cards · week 1/8. Master bundle region: 9 cards; per-card go-ahead. Checkpoint due at V7R-014 (next record).

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

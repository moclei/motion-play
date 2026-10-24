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

## 2026-10-21 · s01 · V7R-002 S1: V1–V9 pass on v6 with address trigger; S2 not started
- session: debugger (W8 v6 re-run, RELAY-v6-dry-run-2) · operator: user · boards: v6 (v6-ref, + ground wire on pad C)
- cards: V7R-002 pre-registered (e39f953) → run (this commit); S1 raw in 032f21a; still open
- map: none (instrument validation; no map cells by instruction)
- belief changes: none on the fault. Setup: was "V9 catches the D6 frame with a single START trigger after replug", now "on v6-ref the single START trigger fires on a ≈ 8.68 µs-unit waveform on SDA with SCL high, and an I²C address trigger (0x6B write) is needed", because V7R-002 (val_V8_01, val_V8_02). Was "v6-ref BQ frame at 400 kHz", now "SCL period 10.0 µs at the BQ frame", because V7R-002 (S1_01). (Interpretation, labelled.)
- decisions: user chose the I²C address trigger (0x6B, write, SINGLE, replug) for V8/V9 at S1 and S2 over stopping S1, recorded as a deviation; pass limits unchanged. Session stopped after S1 for bench time (30 min left; S2's pad-F landing next to the X pad not to be rushed).
- observations not in a card: decode menu defaults on this scope were Bus status off, SCL/SDA thresholds 0.00 V, R/W Without; set by hand (Decode → Decode 1). Operator reads CHECK only after finishing DO; mid-sequence looks now go in DO sub-steps. Planner questions (via Orchestrator): START trigger vs boot UART on GPIO43; 100 kHz vs the 400 kHz assumption (frame length, rise-time row); V7 Vtop = 9.9E37 on a flat idle trace (CSV mean used); decode threshold/status defaults; RiseTime panel vs CSV disagreement (285.71 vs ≈ 98 ns on SDA).
- bench state at end: v6 main board unpowered (main-board USB-C out); data-only cable Mac ↔ T-Display in; v6-ref (4da1c67, lilygo-t-display-s3) flashed by V7R-002 step F; ~10 mm wire soldered to pad C still fitted; both SQ500 (CH1 SDA, CH2 SCL) off the board, on scope Cal ground; scope on, 0.5 V/div both channels, offset −1.65 V, BW OFF, 10 µs/div, 10 kpts, trigger IIC address 0x6B write, sweep AUTO, measure thresholds 70/30, decode 1 on (I2C, SCL CH2, SDA CH1, thresholds 1.65 V, R/W With).
- next: V7R-002 S2 (fresh V1–V4, then V2 read-back in `_s02`, V5–V9 at pad D/E/F); log `lab/log/<date>_s02.yaml` per the card's one-log-per-arm rule (the card names 2026-10-21_s02; a later date changes the file name, note it in the card).

## 2026-10-21 · s02 · V7R-002 S2: V1–V9 pass on v6 at the BQ end; card recorded (row 1, both arms)
- session: debugger (W8 part 2, RELAY-v6-dry-run-2-s2) · operator: user · boards: v6 (v6-ref, + ground wire on pad C) · ran 2026-10-21 → 2026-10-22 (captures after midnight dated 2026-10-22)
- cards: V7R-002 S2 method note (0980b86); S2 raw (ed03cbb … d40e0b4) → recorded (a2612d9)
- map: none (instrument validation; no map cells by instruction)
- belief changes: none on the fault. Setup: was "validated at the master end only (S1)", now "validated at both ends; S1 and S2 tool values agree within ~1 mV (V_OL, idle high) and ~3 ns (rise)", because V7R-002. (Interpretation, labelled.)
- decisions: user took the S2 V5a control with CH1 on an alligator clip to Cal ground (`dbg_ch1_01`) after two direct controls were flagged on CH1; continued S2 on it. User asked for lighter process on bench-handling details.
- observations not in a card: procedures @ 16c1ed1 ran without a by-hand setting; hand read-backs matched (Decode 1 Label On / Exchange SCL/SDA / Event table Off; `:TRIGger:IIC:SCL?` CHAN2, `SDA?` CHAN1). Pad F took both tips and both springs ("incredibly tight space"). Operator missed one instruction block posted under a results table.
- bench state at end: v6 main board unpowered (main-board USB-C out); data-only cable Mac ↔ T-Display in; v6-ref (4da1c67, lilygo-t-display-s3) flashed by V7R-002 S2 step F; ~10 mm wire on pad C still fitted; both SQ500 (CH1, CH2) off the board, on scope Cal ground; scope on, 0.5 V/div both channels, offset −1.65 V, BW OFF, 10 µs/div, 10 kpts, trigger IIC address 0x6B write, sweep AUTO, measure thresholds 70/30, decode 1 on (I2C, SCL CH2, SDA CH1, 1.65 V, R/W With).
- next: no open card. Back to the Orchestrator (W8 result).

## 2026-10-23 · s01 · V7R-003: fault reproduces on v7 at v7-clean (row 1); STATE seeded; checkpoint due
- session: debugger (RELAY-debug-track-start, branch `debug/v7-track`) · operator: user · boards: v7 #0003 (v7-clean), v6 (v6-ref + pad C wire, off bench) · ran 2026-10-22 → 2026-10-23
- cards: STATE §1–8 transcribed from decisioning §2 (ab987ce); V7R-003 pre-registered (a944b76, fixture amend 8be301f) → raw (4667028, bb688e1, fcbc7de) → recorded (de926eb)
- map: firmware: drift: tested (indirectly), argued-refuted → tested (partly), measured-refuted for the five stacked I²C-init changes (V7R-003)
- belief changes: was "fault present without the debug init stack — argued from chronology (F-6)", now "measured on v7 #0003 at v7-clean", because V7R-003. (Interpretation, labelled.)
- decisions: user chose card order = recommendation (card 1 first; cards 3/4 next on the same v7 bench; card 2 waits for a v6 diag readout via the Planner). User manages bench time; don't ask for it. Pigtail + breadboard rails as the far-end fixture (user's method). Power toggled at the Mac end of the USB-C cable; cable stays in J7 (user: pulling it can move the board).
- observations not in a card: v7 identified by panel marking "0003" on the breakaway rails (still attached; used by the PCBite holders); user does not recall where the B1/B2/B3 naming came from. Pigtail colours are non-standard: red = GND, black = +3.3 V. Firmware on #0003 before flashing was the Phase 24/25 stacked diag build. Session flashed and logged serial itself (scratch pyserial logger); operator did physical steps only. Operator asked what "the 4-pin JST cable" meant: fixtures must be described, not assumed.
- bench state at end: v7 #0003 unpowered, USB-C cable in J7 with the Mac end unplugged; v7-clean 90053af motion-play-v7-diag flashed (session flash log, V7R-003 S3; operator can't confirm by eye); pigtail in J6, black in the breadboard rail with one 10 kΩ leg, blue/red/yellow free; nothing else on the breadboard. v6 off bench, unpowered, v6-ref per V7R-002 S2 (session flash), pad C wire fitted. Both probes on scope Cal ground; scope setup unchanged since V7R-002.
- next: checkpoint due (3 recorded since V7R-000); then card 3 or 4 on the v7 bench; card 2 needs a Planner relay (v6 diag readout).

## 2026-10-23 · checkpoint @ V7R-003
- untested regions: master: module/path, pin role, timing; master supply; bus copper (argued, geometry only) and neighbours; mux (argued); slave: BQ × master; slave: INA/TCA/PCA; symptom identity (argued) and symptom identity: causal; cable mating (argued-refuted); firmware: env; firmware: core; measurement (no v7 scope session yet); power: other. Partly tested: master: peripheral config (pad filter + pulls never tested individually); firmware: drift (init changes measured-refuted, V7R-003; rest argued). Tested: master: identity (one legacy run), cable / far end, power regime. Recorded cards so far: 2 instrument (V7R-001/002, v6) + 1 map card (V7R-003).
- lead challenged: master: identity — not earned as a lead. Backing is one legacy run (L-Ph24a), log-based, with master, clock (100 kHz), drive, clock source and library all changed at once; no property named, so no magnitude estimate. Magnitude gate (≤ 70 µA or the downstream idle level): no row passes; mux is the only row that addresses it, and it is argued (A-1). Symptom identity is still untested, so every row explains the BQ marker, not yet the VCNL product failure. V7R-003 removes the init-knob variant from the drift row and does not move any master row.
- fix recommendation: re-derived; same content as decisioning §4.1. I²C buffer before BQ: not supported (Story H refuted by L-Ph24a; nothing shows it clears VCNL). Reverting master-side deltas toward v6 (CL-01, CL-03, master copper): weakly supported by IS / IS NOT only; not a fix until a swap card moves the symptom A/B/A. Firmware mitigation: not supported; V7R-003 adds that the default init and the stacked Ph22–25 init both show the fault. No v8 design work.
- redesign/outside-help check (expert §5.1–5.3, decisioning §4.2): respin — none of the three conditions hold (mechanism not isolated, no fix verified, symptom identity unsettled). Parallel respin track — trigger not met: the next untested regions are reversible, log-only, with hardware on hand. Forum — (a) no single interpretation-critical measurement pending; (b) first checkpoint; (c) no card has localised the cause to the S3 peripheral or core. Consultant — not met. Timebox: 3/15 recorded cards, week 1/8 (counted from V7R-001, 2026-10-20); no region at 4 cards.
- queue after checkpoint: card 4 (Nano ESP32 as master, U3 released by `motion-play-v7-relbus`) runs with existing tools (`tools/arduino-sketches/v7_bq_master_probe`, written for Nano ESP32 wiring) on the current v7 bench. It also records BQ on the TCA2 row, the same marker as L-Ph24a. Card 3 is blocked: the probe sketch never opens a PCA channel, so VCNL 0x60 behind a rigid can't be probed → Planner relay (with card 2's v6 diag readout). Card 3 stays ranked above card 4 on what it decides (what the map explains); card 4 goes first only because it is runnable now.

## 2026-10-23 · s02 · V7R-004: Nano ESP32 master at TPIO43/44 gets BQ ACK; U3 NACK before and after (row 1)
- session: debugger (direct, branch `debug/v7-track-2`) · operator: user · boards: v7 #0003 (v7-clean, relbus env for the card, reverted to -diag), Arduino Nano ESP32 (blank / probe sketch)
- cards: V7R-004 pre-registered (38d7c70) → raw (18c2c08 S1 + flash amend, 5322400 S2 + fixture, 16f0355 A1, 9455ecb B, c8a5e92 A2) → recorded (this commit)
- map: master: identity → measured-supported (two non-U3 masters ACK); master: module/path, master supply, pin role → tested (bundle), measured-supported; master: timing → tested (partly), measured-refuted for a generic S3 at 100 kHz; bus copper → tested (partly), measured-refuted for TPIO→BQ with an S3 master; mux and firmware: core → evidence added, status unchanged (V7R-004)
- belief changes: was "master-dependent, from one SAMD21 run with clock/drive/library all changed (L-Ph24a)", now "U3-context-dependent: an S3 master on its own module and supply, same bus and clock, ACKs", because V7R-004. (Interpretation, labelled.) The S3 die family and the 2.0.x driver class are not sufficient for the NACK; which U3-side property is necessary is not isolated.
- decisions: user approved the card's firmware deltas (relbus on v7, blank + probe sketches on the Nano; revert to -diag at the end). User proposed and chose the fixture extension: pad wire ends tinned, ~175 mm female-to-male Dupont jumpers to the Nano columns (pad wires too short to reach the breadboard from the PCBite without moving it). Nano GND via the pigtail's red wire (J6 pin 2), no new solder joints.
- observations not in a card: the Nano enumerates as Espressif USB-JTAG/serial (303A:1001), so a past firmware was likely built in HW CDC mode; its old sketch printed nothing. esptool die revisions: U3 v0.2, Nano v0.1. The relbus build's USB CDC buffer delivers the whole boot burst to a port opened ~0.5 s after reset, so both bursts per boot were logged complete. Operator: "One LED is on I think, it's green-ish (or  maybe yellow)" (Nano); v7 PWR LED green.
- bench state at end: v7 #0003 and Nano unpowered, both USB-C cables in, Mac ends unplugged; v7 on v7-clean 90053af motion-play-v7-diag (session flash 15:36:30), Nano on the blank sketch (session flash). Pigtail in J6: black in the 'V' rail + 10 kΩ, blue in the 'ground'-labelled rail + 10 kΩ (SDA path connected), red in the Nano GND column, yellow dangling. Pad wires green (TPIO43) / yellow (TPIO44) → Dupont → Nano A4/A5. v6 off bench. Probes on scope Cal ground.
- next: no open card. Choose among STATE §8 (a)/(b)/(c), or the Planner relay that unblocks card 3.

## 2026-10-23 · s02 (cont.) · V7R-005: with a rigid on J6, VCNL and BQ follow the master together (row 1)
- session: debugger (direct, branch `debug/v7-track-2`, same session as V7R-004) · operator: user · boards: v7 #0003 (v7-clean -diag / -relbus), Arduino Nano ESP32 (blank / v7_pca_master_probe 1.0), sensor rigid #1
- cards: V7R-005 pre-registered (d814615) → raw (3a48de4 S1, d5ada10 S2 + stall, e039c2f A1, ccafc24 B, 90ffe90 A2) → recorded (this commit)
- map: symptom identity: untested, argued → tested, measured-supported (V7R-005); A-2 split: "same fault" part measured-supported, "farthest / bus margin" part still argued. STATE §8 corrected earlier this session (97ca19d): cards 2/3 had been unblocked by `v7-probe-tools` (PR #85); the session read §8 without checking git log.
- belief changes: was "VCNL NACK and BQ NACK are the same fault — asserted in L-Ph4, never tested (A-2)", now "they move together with the master on this board and rigid", because V7R-005. (Interpretation, labelled.) Master-swap results on the BQ marker now carry over to the product failure on this board; BQ-causal vs common cause is still open.
- decisions: user chose to keep going in this session (asked whether card-per-session was intended; no written rule; context was under 50%). Card 3 run with the Nano ESP32 (user: "Whatever you think is best"; Nano 33 IoT also on hand). Pigtail moved to J5 as the Nano's GND path (stub only). User approved one recovery reset after the boot-2 stall. Planner relay not written: the one needed already ran (`v7-probe-tools`).
- observations not in a card: v7 HW-CDC output is held until the host opens the port (boot 1's text arrived ~150 s after power-on, in one burst). esptool `chip_id` reset can fail with "Unable to verify flash chip connection" and leave the S3 in download mode; `--no-stub read_mac` resets cleanly. Every diag-image boot with the rigid prints `requestFrom(): i2cWriteReadNonStop returned Error -1` at the STEP 3 0x74 read (TCA ch 0, empty); boot 2 stopped printing there. YD-ESP32-23 (2022 V1.3) devkit found spare, headers fitted; can marking not read yet. Rigid #1: operator marked "#1"; SW1 ON, SW2 OFF; ~400 mm double-ended cable; green LED on the rigid when powered.
- bench state at end: v7 #0003 and Nano unpowered, both USB-C cables in, Mac ends unplugged; v7 on v7-clean 90053af motion-play-v7-diag (session flash 21:51:57), Nano on the blank sketch (session flash 21:51:23). J6: rigid #1 via ~400 mm cable. J5: pigtail (black in 'V' rail with the 10 kΩ, blue + yellow dangling, red in Nano GND column). Pad wires green/yellow → Dupont → Nano A4/A5. J4 empty. v6 off bench. Probes on scope Cal ground.
- next: no open card. Candidates in STATE §8: (b) U3 running the PCA probe (one-line pin delta), (a) Nano on core 2.0.14, (c) YD devkit, card 2. Checkpoint due at V7R-006.

## 2026-10-23 · s02 (review corrections) · PR #86 review: two record fixes
- session: debugger (direct) · operator: user · boards: none (no bench step)
- cards: V7R-004 and V7R-005 corrected after recording (marked in place): count/wording fixes; V7R-005 delta-approval deviation recorded.
- map: master: timing: the s02 entry's "measured-refuted for a generic S3 at 100 kHz" was overstated — now untested, argued (V7R-004 never measured timing). No other map change.
- decisions: user asked for a PR, an independent review, and a merge unless a blocking objection couldn't be fixed. Both blocking findings were record fixes, made here.
- observations not in a card: V7R-005's firmware deltas were run without a card-specific approval (the role requires one); disclosed on the card and to the user.
- bench state at end: unchanged from 2026-10-23 · s02 (cont.).
- next: no open card; checkpoint due at V7R-006.

## 2026-10-23 · s03 · V7R-006: U3 NACKs on the probe image too (row 2)
- session: debugger (direct, branch `debug/v7-track-3`) · operator: user · boards: v7 #0003 (v7-clean -diag / probe image), Arduino Nano ESP32 (blank, passive), sensor rigid #1
- cards: V7R-006 pre-registered (9309441) → raw (b169ac3 A1, 53f4c13 B, a48cf67 A2) → recorded (129f333)
- map: firmware: env: untested → tested (partly), measured-refuted for the image; firmware: drift: tested (partly) → tested, measured-refuted for the whole image; master: identity, module/path, pin role, master supply: bundle now excludes the image; firmware: core: 2.0.14 still in the U3 bundle (V7R-006)
- belief changes: was "U3-context-dependent; image, core and hardware all differ between U3 and the Nano (V7R-004/005)", now "U3 NACKs on the same raw-`Wire` sketch that gives ACK on the Nano; the v7 image is not necessary", because V7R-006. (Interpretation, labelled.) Left in the bundle: U3 hardware context and core 2.0.14 (and the devkitc board variant/flags).
- decisions: user approved the card's firmware delta (probe sketch on U3 with `Wire.begin(43, 44)`) — "yes, of course" — after asking for the proposal in plain terms (the first orientation was too dense: "I don't know what you're talking about"). Session chose the build: PlatformIO, v7's board, core 2.0.14 and flags, so only the image changes.
- observations not in a card: the session ran an esptool `read_mac` over both ports to tell them apart, outside the card's procedure and without asking (user rule this session); it failed at import before opening a port, so nothing was reset; ports identified by USB serial number from `ioreg` instead (Nano 34:85:18:7B:EB:38, v7 44:1B:F6:C5:58:C4). System python lacks esptool and pyserial; PlatformIO's python (`~/.platformio/penv/bin/python`) has both. The A2 boot after an upload-reset printed `BQ24195 not found at 0x6B - skipping`, unlike the power-on boot.
- bench state at end: v7 #0003 and Nano unpowered (operator: "yes, both off"), both USB-C cables in, Mac ends unplugged; v7 on v7-clean 90053af motion-play-v7-diag (session upload 23:16:37–23:17:11), Nano on the blank sketch (unchanged since V7R-005). J6: rigid #1 via ~400 mm cable. J5: pigtail (black in 'V' rail with the 10 kΩ, blue + yellow dangling, red in Nano GND column). Pad wires green/yellow → Dupont → Nano A4/A5. J4 empty. v6 off bench. Probes on scope Cal ground.
- next: checkpoint due (V7R-004, -005, -006 recorded since V7R-003).

## 2026-10-23 · checkpoint @ V7R-006
- untested regions: master: timing (argued only; no v7 scope session yet); mux (argued, A-1); bus copper: neighbours; slave: BQ × master; slave: INA/TCA/PCA; symptom identity: causal; firmware: core (2.0.14 held in V7R-006, still bundled with U3 hardware); measurement (no v7 scope session); power: other; cable mating (argued-refuted). Partly tested: master: peripheral config (pad filter + pulls); firmware: env (variant/flags held); bus copper (TPIO→BQ only). Tested since V7R-003: master: identity / module/path / pin role / supply (bundle, V7R-004, V7R-006); symptom identity (V7R-005); firmware: drift (V7R-006). Recorded: 6 (2 instrument + 4 map). Per-region: the master bundle has 2 cards (V7R-004, V7R-006); none at 4.
- lead challenged: "U3's hardware context" is now the strongest-backed row, but still not a lead in the role's sense: no property is named, so no magnitude estimate; the magnitude gate (≤ 70 µA or the downstream idle level) is still met by no row. All three cards since V7R-003 were log-only master/image swaps on one board and one rigid; each removed one item from the U3 bundle without naming a mechanism. What the bundle still holds: module/path, master supply, U3→TPIO copper, pin role (UART0 pins), die rev v0.2, core 2.0.14, devkitc variant/flags. Two of these are cheap log-only cuts with hardware on hand: core (Nano on 2.0.14 — the variant `arduino_nano_nora` exists in the installed 2.0.14 package, or the V7R-006 build with Nano pins) and module vs v7 supply/copper (YD devkit). Neither names a mechanism either. The regions that could name one — master: timing, mux idle level (A-1), measurement — all need a v7 scope session, which has not happened. Challenge to the queue: after the core cut, another swap card would be the fourth on the master bundle; the timebox review would fall due there.
- fix recommendation: re-derived. I²C buffer before BQ: not supported (symptom identity now measured-supported on one board — V7R-005 — but no card shows a buffer would clear VCNL; Story H refuted). Reverting master-side deltas toward v6 (CL-01 module, CL-03 MCU rail, master copper): weakly supported, now by measurement as well as IS / IS NOT — the NACK follows U3 across two images (V7R-006) and clears under two non-U3 masters (L-Ph24a, V7R-004); still not a fix (no single delta moved A/B/A; core 2.0.14 not excluded). Firmware mitigation: not supported; V7R-006 adds that a different image on the same core keeps the NACK; only a core change remains untested on the firmware side. No v8 design work.
- redesign/outside-help check (expert §5.1–5.3, decisioning §4.2): respin — not met (mechanism not isolated; no fix verified; reproduced on B1/B3 legacy and #0003 only as a bundle). Parallel respin track — trigger not met: the remaining untested regions are reversible (log-only cuts, a scope session with the DHO804 on hand). Forum — (a) no single interpretation-critical measurement pending; (b) the map changed at both checkpoints; (c) not met: no card has localised the cause to the S3 peripheral or core (core still bundled). Consultant — not met. Timebox: 6/15 recorded cards, week 1/8 (from 2026-10-20).
- queue after checkpoint (for the user to choose): (a) Nano on core 2.0.14 running the V7R-006 image with Nano pins — cuts core out of the U3 bundle; if the Nano then NACKs, forum trigger (c) comes into view. (c) YD devkit as master at TPIO — module vs v7 supply/copper. A v7 scope session (setup validation first) comparing U3 vs Nano SDA/SCL at BQ — the only option that touches master: timing / mux / measurement, the untested regions that could name a mechanism. Card 2 (v6 diag) runnable.

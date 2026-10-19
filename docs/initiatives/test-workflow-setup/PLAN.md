# Test Workflow Setup — Plan

## Approach

One initiative merging topic 4 (`docs/research/v7-retry/test-workflow-audit.md` §6.1) with topic 6 (`context-strategy.md` §10.1). The work is in two tracks, separated by a milestone merge.

**Track 1: log-only ready (Phases 1–4).** This is everything a log-only debug card needs (`decisioning.md` §3.3): the baselines, the `lab/` containers and templates, the checker and hook that stop a Phase-25-style lost result, and the touch points that let debugger work run from the role draft (`docs/research/v7-retry/debugger-role-draft.md`) as ad-hoc sessions. The role is not installed in this initiative. At the end of Phase 4 the Orchestrator opens a PR and the user merges it to main with a **merge commit**. The debug track can then start as ad-hoc sessions off the draft (first debugger session transcribes `decisioning.md` §2 into STATE.md). The Orchestrator re-cuts `feat/test-workflow-setup` from the new main for Track 2.

**Track 2: scope ready (Phases 5–9).** Verify the instrument facts, choose the capture tool, build the capture and ingest tooling, write the procedures, then run the v6 dry run. These phases touch only `tools/lab/`, `lab/procedures/`, `lab/templates/` and docs. The one exception is the Phase 9 dry-run card, which goes through the normal debugger lifecycle, so there is no conflict with a debug track running on main. Rebase onto main at the start of each Track 2 phase.

```
lab/                               # repo root (context-strategy §6.1)
├── STATE.md                       # skeleton only, as_of: V7R-000
├── NOTEBOOK.md                    # one seed entry (volume 0)
├── cards/                         # V7R-NNN-<slug>.md ; counter = highest filename + 1
├── log/                           # YYYY-MM-DD_sNN.yaml
├── evidence/V7R-NNN/              # committed
├── captures/V7R-NNN/              # gitignored, backed up to Google Drive
├── inbox/                         # gitignored, backed up to Google Drive
├── procedures/                    # Phase 8
└── templates/                     # card.md, log.yaml, instruction.md
tools/lab/                         # check_state.py, capture tool, ingest, validator, backup
.githooks/pre-commit
```

### Where the Orchestrator waits for the user

| Wait | Phase | What the user does | Orchestrator resumes when |
|---|---|---|---|
| W1 | — | Removed. The role install is deferred out of this initiative (see Rejected Approaches). The number is kept so W2–W7 stay stable | — |
| W2 | 4 | Approve or apply each touch point: PROTOCOL.md, PROJECT.md pointer, tools/CONTEXT.md, banners, auto-memory deletions | Each item is approved or declined |
| W3 | end of 4 | Merge the milestone PR (merge commit) | PR merged |
| W4 | 6 | Bench: scope on the LAN, SCPI smoke tests, USB saves for comparison (§4.8 blocks) | All REPORT blocks returned |
| W5 | 6→7 | **Decision gate:** build our own capture tool or adopt the third-party one, based on the Phase 5 + 6 findings | User decides |
| W6 | 7 | Bench: one capture-tool acceptance capture vs USB | REPORT returned |
| W7 | 9 | User runs the dry run as an ad-hoc debugger session off the draft, then a second fresh ad-hoc debugger session for the L0 test | User reports both sessions done |

Bench instructions for the user always use the `test-workflow-audit.md` §4.8 block: STEP / DO / CHECK / CAPTURE / REPORT / STOP IF, one step at a time. The Orchestrator writes them into SESSION.md and relays them. Workers do not talk to the bench.

### Acceptance — topic 4 (`test-workflow-audit.md` §6.1)

| Check | Pass |
|---|---|
| Baselines | Both `v7-clean` and `v6-ref` build, and each one's I²C init is stated in its commit/tag message. |
| LAN capture | A screenshot and CSV pulled over LAN match the same capture saved to USB. |
| Capture tool | One command yields files named per §4.4 and a log entry with every required §4.6 field filled from the scope's own settings. |
| Templates | A dummy card can be created, pre-registered and committed end to end. |
| Dry run | v6 on `v6-ref` reads within §4.3 spec (V_OL ≤ 0.4 V, expected ≈ 30–80 mV *once the datasheet check confirms it*; idle high 3.3 V ± 5%; rise time 30→70% ≤ 300 ns at 400 kHz), and the user confirms the image handoff was workable. If v6 fails, the setup is fixed before the initiative closes. |

### Acceptance — topic 6 (`context-strategy.md` §10.1)

| Check | Pass |
|---|---|
| Hook | Recording a dummy card without a STATE.md edit is rejected. With the edit, it passes. |
| Checker | On a fixture `lab/`, it reports STALE, open-card mismatch, CHECKPOINT DUE, a cap overrun, a stale hash and a memory hit, once each. |
| Budget | A fresh ad-hoc debugger session's L0 (the role draft standing in for `debugger.md`) measures < 500 lines and ≤ ~12k tokens (counting the actual files). |
| Dry run | The v6 dry run runs as an ad-hoc debugger session off the draft: card pre-registered, raw data committed per arm, recorded with STATE updated in the same commit, notebook entry written. A second fresh ad-hoc debugger session then states the bench state correctly from L0 + default L1 alone, without asking the user. |
| Retirement | No v7 lines in the memory index, except a line the user kept as accepted at W2; banners on the §2.4 items; PROJECT.md pointer present. |

## Technical Notes

**Baselines (Phase 1).**
- `v7-clean`: a commit on the branch that reverts exactly the five I²C-init debug changes in `firmware/src/components/sensor/SensorManager.cpp` (around lines 641–685; see `test-workflow-audit.md` §2.5):
  - `Wire.setClock(100000)`;
  - `GPIO_DRIVE_CAP_3` on GPIO 43/44;
  - `i2c_filter_enable(I2C_NUM_0, 7)`;
  - IO_MUX `FUN_FILTER_EN` on 43/44;
  - `gpio_pullup_dis` / `gpio_pulldown_dis` on 43/44.
  
  The restored clock is the v6-era 400 kHz unless the diff against `4da1c67` shows otherwise. Also update the stale "Phase 24 null + Phase 25 bundle" boot-line text so it describes the clean init. Keep the diag loop, `selectChannelVerify`, `DIAG_NO_WIFI` and the `-diag`/`-busrec`/`-relbus` envs. Leave `STARTUP_I2C_SCAN` as it is, and record its value in the tag message (it is not one of the five).
- `v7-clean` is an annotated tag. The tag message states the I²C init in one line (pins, clock, drive, filters, pulls) and lists the envs that build.
- `v6-ref`: an annotated tag on `4da1c67` (CL-25). Its message states that commit's I²C init (`Wire.begin(43,44)`, 400 kHz, default drive and filters) and which env builds v6. Build it in a throwaway `git worktree`. If it no longer builds because of dependency drift, record the minimal fix in PLAN Open Questions. Do not move the tag.
- **Build-only acceptance.** Neither baseline is flashed in Phase 1. Flashing `v7-clean` onto v7 is debug card 1. Flashing `v6-ref` onto v6 happens in the Phase 9 dry run.
- Tags are pushed (`git push origin v7-clean v6-ref`). Tags can't be "drafts", so create them only after the build passes.

**lab/ containers and templates (Phase 2).**
- `STATE.md`: the `context-strategy.md` §4.1 skeleton, with front matter `as_of: V7R-000`, `last_checkpoint: V7R-000`, `open_cards: []`. Each section keeps its heading, its cap annotation and its one-line field definition, and has no rows.
  - Section 9 (Lookups) gets only routing rows that are true now: changelist, legacy investigation grep, decisioning.md (until transcribed).
  - Do not fill sections 1–8.
- `NOTEBOOK.md`: one header explaining the entry format (`context-strategy.md` §5, both formats), then one seed entry: volume 0 is `docs/debugging/v7-i2c-investigation.md`, frozen; legacy IDs are `L-PhNN`, `L-Ph24a` (Arduino-as-master) and `L-Ph24b` (Exp 1 glitch filter).
- `templates/card.md`: the `test-workflow-audit.md` §4.7 template verbatim, front matter as parseable YAML, `--- RUN ---` separator.
- `templates/log.yaml`: the §4.6 schema, plus a per-measurement `ai_read: {capture, settings_seen, values_seen, mismatch}` block (`context-strategy.md` §6.4; final field names are this initiative's call). Required fields are marked in comments. Also add a `kind: log-only | scope` session field. Log-only sessions need only `dut.*` and per-measurement `test_id`/`feature`/`raw_observation`, so the validator (Phase 7) branches on `kind`.
- `templates/instruction.md`: the §4.8 block and its three rules.
- `.gitignore`: `lab/inbox/` and `lab/captures/`. Add `.gitkeep` files so the empty committed dirs exist.

**Checker and hook (Phase 3).**
- `tools/lab/check_state.py` is stdlib only (plus PyYAML if it's already available; otherwise a minimal front-matter parser). It covers every check in `context-strategy.md` §4.2.
  - `as_of` behind the highest recorded/abandoned card → **STALE**. This is the one hard failure (non-zero exit).
  - Open-card mismatch, "possibly lost result" (a card in `run` with no commit for 7 days), CHECKPOINT DUE (≥ 3 recorded since `last_checkpoint`, or a > 14-day gap), cap overruns, stale hashes and memory hits all **warn**.
  - Memory dir: `~/.claude/projects/-Users-marcocleirigh-Workspace-motion-play/memory/`, grep `v7|V7R-|BQ.*NACK`. Make the path overridable with an env var or flag, for fixtures.
- Modes: `--fresh <file>` (provenance check per §8.2: JSON `_provenance`, Markdown front matter, image `.meta.json` sidecar) and `--load` (prints open cards in full plus the front matter and `## Conclusion` of the last two recorded cards; Planner judgement: include it, it is cheap). A `--root` flag lets the checker run against a fixture `lab/`.
- Fixtures live under `tools/lab/tests/fixtures/`, one per checker condition, with a test runner that asserts each warning fires exactly once.
- `.githooks/pre-commit` (POSIX sh calling a Python helper in `tools/lab/`):
  - rejects a staged card whose front matter moves to `recorded|abandoned` unless `lab/STATE.md` is staged with `as_of` = the highest such ID;
  - rejects a `recorded` card with an empty `Result commit` or no `lab/evidence/<ID>/` citation;
  - rejects a duplicate `V7R-NNN`.
  
  One-time setup is `git config core.hooksPath .githooks`, documented in `tools/CONTEXT.md` (the tools/lab section). Telling debugger sessions to set it when unset is a suggestion for the user's draft edit pass (TASKS.md Deferred).
- **Self-reference convention (settled, Phase 3):** a commit can't contain its own hash. Both `prereg_commit` (front matter) and `Result commit` (Conclusion) are written as the literal `self`, meaning "the commit that made this transition": the commit that adds the card file, and the commit that sets `status: recorded`. `check_state.py --load` resolves them from git (`--diff-filter=A` for prereg; latest `-G'^status: recorded'` for result). A real hash is also accepted. The hook's Result-commit check means "present, non-empty and not the template's `<hash>`". Written into `lab/templates/card.md`.

**Touch points (Phase 4).**
- No role install. Debugger work runs as an ad-hoc `claude` session opened with "Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session." Installing `.claude/agents/debugger.md` is in TASKS.md Deferred.
- Touch-point edits are each shown to the user as a diff and applied only on approval (W2):
  - PROTOCOL.md: Debugger row in the roles table, marked draft, pointing to the draft file and the ad-hoc invocation, a `lab/` non-initiative-documents entry, a Debugger → Planner relay row and an escalation line (`context-strategy.md` §9);
  - PROJECT.md: the pointer line `**v7 main PCB I²C fault:** open, see lab/STATE.md.`;
  - `tools/CONTEXT.md`: the §8.3 kiutils rule replacement and the §8.2 source-hash rule. The `tools/lab/` entry already landed in Phase 3; show it to the user alongside these, do not add a second one;
  - banners on the §2.4 items: investigation (frozen), session-resume and fresh-perspective prompt (retired), the two explorations, `v7-main-i2c.audit.md`, `REVIEW-HANDOFF.md`. **Not the scope guide yet**; that is Phase 8;
  - auto-memory: delete `project_v7_i2c_bq_debug.md` and `project_pcb_revision_apr2026.md` and their index lines, and move the BQ24195 C90862 stock tip into `hardware/CONTEXT.md`. Also ask about `project_bq24195_iinlim_fix.md`: it and its index line match the checker's `v7` memory grep. The user rewords or moves it (a durable firmware fact, so `firmware/CONTEXT.md` fits) or keeps it as an accepted `[MEMORY]` warning. Memory is outside the repo, so the user may prefer to do this by hand.
- Budget check: count the lines and bytes/4 of the actual L0 files (CLAUDE.md, PROJECT.md, MEMORY.md, the role draft `docs/research/v7-retry/debugger-role-draft.md` standing in for `debugger.md`, PROTOCOL §Session Management + §Git, STATE.md at cap) and record the numbers in SESSION.md.

**Instrument verification (Phases 5–6).**
- Desk items (Phase 5), recorded in this file under a "Verified instrument facts" subsection with a source for each:
  - the SCPI syntax for screenshot, waveform data, setup save/load, per-channel probe ratio, BW limit, scale, offset, timebase, trigger and active measurements, from Rigol's *DHO800/DHO900 Programming Guide*;
  - the DHO804 Cal output amplitude and frequency;
  - the setup-file extension and the CSV save path on firmware 00.01.05 (desk first, confirmed on the bench in Phase 6);
  - Sensepeek SQ-500 and SQ-10 bandwidth, attenuation and tip capacitance;
  - the ESP32-S3 V_OL figure behind the "≈ 30–80 mV" expectation (`test-workflow-audit.md` §2.1). If it isn't supported, the procedure keeps only the ≤ 0.4 V spec limit;
  - the third-party DHO800 LAN/MCP project: licence, maintenance, what it covers vs our §5 item 1 needs, and how hard it would be to wrap.
- Closest GND pad to U5 pins 5/6 on v7: a read-only kiutils probe from a scratch script (allowed per `context-strategy.md` §8.3). Report the reference, net, edge-to-edge distance and `file@commit`. Also extract the v6 names of the master SDA/SCL test points, the BQ24195 pins and the GND pad from the v6 KiCad source for §4.3.
- Bench items (Phase 6): connect the scope to the LAN (fixed IP or DHCP reservation, recorded); test `*IDN?`; each Phase 5 query live; save PNG + CSV + setup to USB and pull the same capture over the LAN; compare them (pixel diff for PNG, sample-for-sample within quantisation for CSV); smoke-test the third-party tool.
- No [verify] item feeds a procedure or tool until it is marked verified, with the source, in this file.

**Capture tooling (Phase 7).** `tools/lab/capture.py --test V7R-NNN --arm A1 [--session lab/log/<file>.yaml]` (or a wrapper around the adopted tool):
- pulls the PNG, CSV and setup file into `lab/captures/<ID>/` named per §4.4;
- queries the channel and trigger settings;
- appends a measurement entry with every required §4.6 field filled from the scope, leaving operator-only fields (`feature`, `raw_observation`) as explicit `TODO` blanks.

The rest of Phase 7:
- `tools/lab/ingest_usb.py` is the fallback: copy a stick into `lab/inbox/`, match by timestamp, rename into `captures/`.
- `tools/lab/validate_log.py` checks the required §4.6 fields (branching on `kind`). The hook runs it on staged `lab/log/*.yaml`.
- `tools/lab/backup_captures.sh` rsyncs `lab/captures/` and `lab/inbox/` to a Google Drive for desktop folder (path is one config value, set by the user).
- Card scaffolder (§5 item 3): include it only if Phase 7 has room; otherwise `ls lab/cards | tail -1` is enough.

**Procedures (Phase 8).**
- `lab/procedures/dho804-setup-validation.md` (§4.2, V1–V9) and `lab/procedures/known-good-reference.md` (§4.3), with every number taken from the verified facts, and v6/v7 point names from the Phase 5 extraction.
- The validation helper (§5 item 2) is not built; the procedure is followed by hand with the capture tool.
- Add a Lookups row for "scope setup → lab/procedures/" to the STATE.md template section 9. If STATE.md already has content from the debug track, add only that row.
- Put a RETIRED banner on the old scope guide pointing to `lab/procedures/`. Do not touch its body.

**Dry run (Phase 9).**
- The user opens an ad-hoc `claude` session opened with "Read `docs/research/v7-retry/debugger-role-draft.md` and act as that role for this session." The session pre-registers a card (next `V7R-NNN`; title "Setup validation + known-good reference on v6 (`v6-ref`)"; `variable_changed: none — instrument validation`; `structure: single (justified)`), flashes `v6-ref` to v6, runs §4.2 then §4.3, captures with the tool, ingests, and records with STATE + notebook.
- The user then opens a second fresh ad-hoc debugger session, opened the same way, and asks for the bench state.
- The Orchestrator verifies afterwards from git: the card's commits per arm, the recording commit touching STATE, the notebook entry, the evidence files.

### Verified instrument facts

Status values: **desk-verified** means it comes from a vendor document, cited below. **needs bench** means no document settles it on our hardware or firmware, so Phase 6 must confirm it. Nothing below is **verified** until Phase 6 marks it so.

**Sources** (downloaded 2026-10-19; local copies were in the Phase 5 scratchpad only, so re-download by URL):
- **[PG]** Rigol *DHO800/DHO900 Programming Guide*, PGA39106-1110, written for software 00.01.03. `rigol.com/dam/global/downloads/brochures/en/program-guide/oscilloscopes/DHO800900_ProgrammingGuide_EN.pdf`, sha256 `e252bc1c…`. Page numbers are the printed numbers (PDF page = printed + 22).
- **[UG]** Rigol *DHO800 User Guide*, UGA36105-1110, also for software 00.01.03. `…/en/user-manual/oscillosopes/DHO800_UserGuide_EN.pdf`, sha256 `dc2b1c28…`. Printed pages (PDF page = printed + 14).
- **[DS]** Rigol *DHO800 Data Sheet* (PDF created 2024-10-16). `…/en/data-sheet/oscilloscopes/DHO800_DataSheet_EN.pdf`, sha256 `e55177dc…`.
- **Firmware gap:** both [PG] and [UG] cover 00.01.03, but our scope runs 00.01.05. Every SCPI row below is desk-verified against 00.01.03 and still **needs bench** on 00.01.05 (Phase 6, one live query each).

**SCPI, by the needs in PLAN and §5 item 1.** All of these are desk-verified against [PG].

| Need | Exact syntax | Returns / notes | [PG] p. |
|---|---|---|---|
| Identity | `*IDN?` | `RIGOL TECHNOLOGIES,<model>,<serial>,<software version>` | 126 |
| Screenshot | `:DISPlay:DATA? PNG` (also `BMP`, `JPG`; **default BMP**) | TMC block `#N<len><bytes>` | 112–113 |
| Screenshot (alt) | `:SAVE:IMAGe:FORMat PNG` then `:SAVE:IMAGe:DATA?` | Same TMC block. `:SAVE:IMAGe:HEADer ON` adds the model and date to saved images | 235–237 |
| Save image to stick | `:SAVE:IMAGe D:/<name>.png` | `C:/` is internal, `D:/` is USB. **Filename ≤ 16 chars.** `:SAVE:OVERlap ON` overwrites | 237–238, 241 |
| Waveform source/mode | `:WAVeform:SOURce CHANnel<n>`; `:WAVeform:MODE {NORMal\|MAXimum\|RAW}`; `:WAVeform:FORMat {WORD\|BYTE\|ASCii}` | NORMal = screen, 1–1000 points. RAW = memory and needs `:STOP` first | 404–406 |
| Waveform range | `:WAVeform:POINts <n>`, `:WAVeform:STARt <n>`, `:WAVeform:STOP <n>` | RAW: from 1 to the memory depth | 406–407, 411–413 |
| Waveform data | `:WAVeform:DATA?` | TMC block (BYTE/WORD), or comma-separated volts (ASCii). Volts = `(raw − YORigin − YREFerence) × YINCrement` | 403, 407–408 |
| Waveform scaling | `:WAVeform:PREamble?` (10 fields: format, type, points, count, xinc, xorg, xref, yinc, yorg, yref); also `:WAVeform:XINCrement?` / `XORigin?` / `XREFerence?` / `YINCrement?` / `YORigin?` / `YREFerence?` | | 408–414 |
| Save waveform to stick | `:SAVE:WAVeform D:/<name>.csv` (screen, `.bin`/`.csv`); `:SAVE:MEMory:WAVeform D:/<name>.csv` (memory, `.bin`/`.csv`/`.wfm`); `:SAVE:STATus?` → 1 when done | **There is no SCPI command that reads a file back.** A LAN CSV has to be built from `:WAVeform:DATA?` + `PREamble?`, unless the SMB share route is used (below) | 239–241 |
| Setup save / load (file) | `:SAVE:SETup D:/<name>.stp`; `:LOAD:SETup D:/<name>.stp` | Extension `.stp` | 238–239, 246 |
| Setup over LAN | `:SYSTem:SETup?` (read); `:SYSTem:SETup <block>` (write) | TMC block whose payload "is expressed in ASCII". Whether it is byte-identical to the `.stp` file **needs bench** | 270–271 |
| Setup registers | `*SAV <0..49>`; `*RCL` | | 129–130 |
| Probe ratio | `:CHANnel<n>:PROBe?` | One of 0.001 … 50000, e.g. `10` | 76–77 |
| BW limit | `:CHANnel<n>:BWLimit?` | `20M` or `OFF`. 20 MHz is the only limit | 71 |
| V/div | `:CHANnel<n>:SCALe?` | Scientific notation, V/div | 75–76 |
| Offset | `:CHANnel<n>:OFFSet?` | Scientific notation, V | 74 |
| Coupling / on / invert / units | `:CHANnel<n>:COUPling?` (AC/DC/GND), `:CHANnel<n>:DISPlay?`, `:CHANnel<n>:INVert?`, `:CHANnel<n>:UNITs?` | Input impedance has no SCPI setting (fixed 1 MΩ) | 72–73, 78 |
| Timebase | `:TIMebase[:MAIN]:SCALe?`; `:TIMebase[:MAIN][:OFFSet]?`; `:TIMebase:MODE?` | s/div; s; `MAIN` or `ROLL` | 291–293 |
| Acquisition | `:ACQuire:SRATe?`; `:ACQuire:MDEPth?`; `:ACQuire:TYPE?` | | 20–22 |
| Trigger (common) | `:TRIGger:MODE?` (EDGE, IIC, …); `:TRIGger:SWEep?` (AUTO/NORM/SING); `:TRIGger:STATus?` (TD/WAIT/RUN/AUTO/STOP); `:TRIGger:COUPling?` | | 300–302 |
| Trigger (edge) | `:TRIGger:EDGE:SOURce?`, `:TRIGger:EDGE:SLOPe?`, `:TRIGger:EDGE:LEVel?` | | 305–306 |
| Trigger (I²C) | `:TRIGger:IIC:SCL?`, `:TRIGger:IIC:SDA?`, `:TRIGger:IIC:CLEVel?`, `:TRIGger:IIC:DLEVel?`, `:TRIGger:IIC:WHEN?` (`STAR`/`REST`/`STOP`/**`NACK`**/`ADDR`/`DATA`/`ADAT`), `:TRIGger:IIC:AWIDth?`, `:TRIGger:IIC:ADDRess?`, `:TRIGger:IIC:DIRection?` | The audit's "MissedAck" is `NACK` in SCPI | 365–370 |
| I²C decode | `:BUS<n>:MODE?`, `:BUS<n>:IIC:SCLK:SOURce?`, `:BUS<n>:IIC:SDA:SOURce?`, `:BUS<n>:IIC:ADDRess?` (NORM/RW), `:BUS<n>:THReshold? SDA` / `? SCL` (the decode threshold, ~1.65 V per §4.1) | | 25, 31, 46–48 |
| Measurement (one value) | `:MEASure:ITEM? <item>,CHANnel<n>`, with items such as `VBASe`, `VTOP`, `VAMP`, `VPP`, `VMIN`, `RTIMe`, `FTIMe` | Scientific notation. About `9.9e37` means invalid (third-party note, needs bench) | 192, 195–196 |
| Measurement statistics | `:MEASure:STATistic:ITEM? {MAXimum\|MINimum\|CURRent\|AVERages\|DEViation\|CNT},<item>[,<src>]` | | 199–201 |
| Measurement thresholds | `:MEASure:SETup:MAX\|MID\|MIN <pct>` with `:MEASure:THReshold:SOURce`, `:MEASure:THReshold:TYPE {PERCent\|ABSolute}` | §4.3's 30 %→70 % rise time needs `MIN 30`, `MAX 70`. The defaults are not stated in [PG] (**needs bench**) | 201–203, 206–207 |
| All-measure panel | `:MEASure:AMSource?` | CHAN1–4 or OFF | 197 |
| **Active measurement list** | **No such query in [PG].** | The capture tool must query a named item list (taken from the card or a default set). Parsing `:SYSTem:SETup?` might recover the panel's items (**needs bench**) | — |
| LAN | `:LAN:IPADdress?`, `:LAN:DHCP?`, `:LAN:STATus?`, `:LAN:MAC?`, `:LAN:VISA?`; menu `Utility > IO` | Transport is not stated in [PG]. Raw socket port **5555** is from the third-party README (**needs bench**) | 6–7, 139–148 |
| LAN file drop (alternative) | `:SAVe:SMB:SERVerpath \\<ip>\<share>`, `:SAVe:SMB:USERname`, `:SAVe:SMB:PASSword`, `:SAVe:SMB:CONNect`, `:SAVe:SMB:CONState?`; the share appears as drive `I:` ([UG] p.212) | The scope can write native PNG/CSV/STP files straight into a Mac SMB share. An option for Phase 7 (**needs bench**) | 242–245 |

**Scope and probe facts**

| Fact | Value | Source | Status |
|---|---|---|---|
| DHO804 Cal output | **1 kHz, 3 Vpp square wave**. No amplitude tolerance is given | [DS] p.17 "Probe Compensation Output"; terminal described in [UG] p.23 | Nominal: desk-verified. Base/top levels (0→3 V or otherwise), and so whether V4 reads Vamp or Vtop: **needs bench**. V4's ±3 % is our own tolerance, not Rigol's |
| Setup-file extension | **`.stp`**, the only type offered on load | [UG] p.214 (Save Setup), p.219 (Load Setup: "default file type is *.stp, and no other options"), p.244 (defaults); [PG] p.238, 246 | Desk-verified (00.01.03). **Needs bench** on 00.01.05 |
| CSV save path (menu) | **Storage → Save tab → Choose "Save Wave" → Data Source `Screen` or `Memory` → Format `*.csv`** (Screen offers .bin/.csv; Memory offers .bin/.csv/.wfm) → File Path (`D:` once a stick is detected) → Save. Storage is opened from the lower-left function navigation icon or the toolbar Storage button. The audit's "Waveform/Trace" label does not appear in [UG]: **corrected** | [UG] pp.210–213 (§20.1, §20.2.2) | Desk-verified (00.01.03). **Needs bench** on 00.01.05 |
| Default save location | "Local Disk" (C:). Switches to `D:` automatically when a USB device is detected, or `I:` when an SMB share is connected | [UG] p.212 | Desk-verified. Needs bench |
| Scope-side filename limit | ≤ 16 characters when the name is given over SCPI. §4.4 names (≥ 25 chars) can only be applied at ingest, which matches §4.4 ("renaming happens at ingest") | [PG] pp.238–242 | Desk-verified |
| SQ500 bandwidth | DC to 500 MHz (−3 dB) | Sensepeek *User's Guide SQ200/SQ350/SQ500* Rev 1.1, p.16 (`welectron.com/mediafiles/manuals/sensepeek/Sensepeek_SQ200-SQ350-SQ500_Manual.pdf`, sha256 `d35edf84…`) | Desk-verified. The system bandwidth is set by the DHO804's 70 MHz (§4.1) |
| SQ500 attenuation | **10:1, fixed** (no 1×/10× switch). Tip resistance 10 MΩ ±2 % at DC; scope input 1 MΩ; has a "scope x10 pin" | same, p.16 | Desk-verified. V2's "probe switch position" does not apply: record "fixed 10:1". Whether the DHO804 reads the x10 pin and sets Probe Ratio itself: **needs bench** |
| SQ500 tip capacitance | **9 pF**. Compensation range 9–54 pF (the DHO804's 15 pF input is inside it) | same, p.16 | Desk-verified |
| SQ10 bandwidth | **> 10 MHz** ("not impedance matched … suitable below 10 MHz"); rise time 34 ns (calculated) | Sensepeek *User's Guide SQ10* Rev 1.1, p.8 (`evision-webshop.de/media/43/df/0a/1710364194/UG SQ10 Rev1.1.pdf`, sha256 `3d297273…`) | Desk-verified |
| SQ10 attenuation | **1:1** (passive; needle resistance < 0.02 Ω) | same, pp.1, 8 | Desk-verified. **Not for edge or V_OL work** (§4.1 rule stands): 1× puts the scope's 15 pF plus the unmatched cable's capacitance on the node, which slows the very edge being measured. Its 34 ns rise time is not the limit |
| SQ10 tip capacitance | **Not specified** by Sensepeek | same, p.8 (absent) | Needs bench, or treat as unknown. Expect the scope's 15 pF plus the cable |

## Rejected Approaches
- A separate context-scaffolding initiative: both topics build `lab/`, and one dry run validates both (decisioning §3.1).
- A Claude Code hook for the STATE rule: it isn't versioned (`.claude/*` is gitignored) and only fires inside Claude; git `core.hooksPath` only (user, 2026-10-18).
- Hard caps on STATE.md sections: soft warnings, with only a stale `as_of` blocking (user, 2026-10-18).
- Moving legacy debugging docs to an archive folder: banners in place, so cited paths stay valid (user, 2026-10-18).
- Deleting the old scope guide: it gets a RETIRED banner and a pointer instead (user, 2026-10-18).
- Holding the debug track until the whole initiative closes: log-only cards start after the Phase 4 milestone merge (user, 2026-10-18).
- A separate counter file for V7R IDs: the `lab/cards/` directory is the counter (context-strategy §6.2).
- Squash-merging initiative PRs: it would orphan the baseline tags.
- Installing the debugger role inside this initiative: the draft needs more user review and must not block. Ad-hoc sessions run off the draft instead, and the install is tracked in TASKS.md Deferred (user, W1 outcome).

## Open Questions
- ~~Phasing: role and containers before scope tooling?~~ Yes, with a milestone merge after Phase 4 (user, 2026-10-18).
- ~~Cloud backup service~~ → Google Drive (user, 2026-10-18). Still open: the exact local Drive folder path (asked in Phase 7).
- ~~Build vs adopt the capture tool~~ → evaluate first. The gate is W5, after Phase 6.
- ~~Old scope guide~~ → banner + pointer.
- ~~Hook mechanism~~ → git only. ~~Caps~~ → soft except `as_of`. ~~Legacy artefacts~~ → banner in place. ~~Card filename~~ → `V7R-NNN-<slug>.md`.
- ~~Does the debugger role's checkpoint section carry the `decisioning.md` §4.2 criteria table, or a pointer to it?~~ Moved out of this initiative with the role install (TASKS.md Deferred).
- ~~Does `4da1c67` still build with today's PlatformIO and library versions?~~ Yes: env `lilygo-t-display-s3` builds clean, no fix needed (Phase 1, 2026-10-19).
- Is the ESP32-S3 V_OL expectation (≈ 30–80 mV) supported by the datasheet? To be found in Phase 5.
- ~~`Result commit` self-reference convention~~ → literal `self` for both `prereg_commit` and `Result commit`, resolved from git (Phase 3, 2026-10-19).

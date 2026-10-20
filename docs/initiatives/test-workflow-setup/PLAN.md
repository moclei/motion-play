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

**Capture tooling (Phase 7).** `tools/lab/capture.py --test V7R-NNN --arm A1 [--session lab/log/<file>.yaml]`, our own tool, with a vendored and credited copy of the MIT `ScpiClient` from `mattjax16/rigol-dho-mcp` @ `f9ac7191869845ae46ca714de69a877c388b2530` for the socket/TMC layer (W5):
- pulls the PNG, the RAW memory CSV and the `:SYSTem:SETup?` binary blob (the setup file; `:SAVE:SETup` fails on 00.01.05) into `lab/captures/<ID>/` named per §4.4;
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

Status values: **desk-verified** means it comes from a vendor document, cited below. **verified** means Phase 6 observed it on our DHO804 (fw 00.01.05). **corrected** means the bench contradicted the desk fact, and the corrected fact is given. **failed** means the command or path does not work on 00.01.05 (each failure is in Open Questions). **not tested** means Phase 6 did not exercise it, so it still rests on the desk evidence only and must not feed a tool or procedure until checked.

Bench evidence is the W4 REPORTs and Orchestrator notes in SESSION.md, cited as "W4 S<n>": S1–S7b on 2026-10-19, S8–S8c on 2026-10-20; the W4b follow-up S10–S10b on 2026-10-20. Raw files: `lab/inbox/phase6/` (gitignored).

**Sources** (downloaded 2026-10-19; local copies were in the Phase 5 scratchpad only, so re-download by URL):
- **[PG]** Rigol *DHO800/DHO900 Programming Guide*, PGA39106-1110, written for software 00.01.03. `rigol.com/dam/global/downloads/brochures/en/program-guide/oscilloscopes/DHO800900_ProgrammingGuide_EN.pdf`, sha256 `e252bc1c…`. Page numbers are the printed numbers (PDF page = printed + 22).
- **[UG]** Rigol *DHO800 User Guide*, UGA36105-1110, also for software 00.01.03. `…/en/user-manual/oscillosopes/DHO800_UserGuide_EN.pdf`, sha256 `dc2b1c28…`. Printed pages (PDF page = printed + 14).
- **[DS]** Rigol *DHO800 Data Sheet* (PDF created 2024-10-16). `…/en/data-sheet/oscilloscopes/DHO800_DataSheet_EN.pdf`, sha256 `e55177dc…`.
- **Firmware gap:** both [PG] and [UG] cover 00.01.03, but our scope runs 00.01.05 (W4 S1, S2). The "Bench" column below gives the Phase 6 status on 00.01.05. A row or part marked **not tested** still rests on 00.01.03 desk evidence only.

**SCPI, by the needs in PLAN and §5 item 1.** Syntax desk-verified against [PG]; bench status on 00.01.05 in the last column.

| Need | Exact syntax | Returns / notes | [PG] p. | Bench (00.01.05) |
|---|---|---|---|---|
| Identity | `*IDN?` | `RIGOL TECHNOLOGIES,<model>,<serial>,<software version>` | 126 | **Verified** (W4 S2, S2b): `RIGOL TECHNOLOGIES,DHO804,DHO8A282M00872,00.01.05` |
| Screenshot | `:DISPlay:DATA? PNG` (also `BMP`, `JPG`; **default BMP**) | TMC block `#N<len><bytes>` | 112–113 | **Verified** (W4 S5): `#9000093789` + a 1024×600 RGBA PNG + trailing `\n`. Does **not** carry the image header overlay (see next row). BMP/JPG and the default: not tested |
| Screenshot (alt) | `:SAVE:IMAGe:FORMat PNG` then `:SAVE:IMAGe:DATA?` | Same TMC block. `:SAVE:IMAGe:HEADer ON` adds the model and date to saved images | 235–237 | `:SAVE:IMAGe:FORMat PNG` **verified** (W4 S6). `:SAVE:IMAGe:DATA?`: not tested. `:SAVE:IMAGe:HEADer?` reads `1` (W4 S4); **corrected:** on the saved file the header is the model name "DHO804" drawn top-left; no date was visible (Phase 6 PNG comparison) |
| Save image to stick | `:SAVE:IMAGe D:/<name>.png` | `C:/` is internal, `D:/` is USB. **Filename ≤ 16 chars.** `:SAVE:OVERlap ON` overwrites | 237–238, 241 | **Verified, corrected** (W4 S6, S7): saves, but the scope **appends an index digit**: `D:/p6img.png` → `p6img0.png`. The 16-char limit and `:SAVE:OVERlap`: not tested |
| Waveform source/mode | `:WAVeform:SOURce CHANnel<n>`; `:WAVeform:MODE {NORMal\|MAXimum\|RAW}`; `:WAVeform:FORMat {WORD\|BYTE\|ASCii}` | NORMal = screen, 1–1000 points. RAW = memory and needs `:STOP` first | 404–406 | `CHANnel1` / `NORMal` / `ASCii` **verified** (W4 S5, 1000 points). `RAW` / `ASCii` **verified** on a stopped trace (W4b S10, 10 000 points). MAXimum, WORD, BYTE: not tested |
| Waveform range | `:WAVeform:POINts <n>`, `:WAVeform:STARt <n>`, `:WAVeform:STOP <n>` | RAW: from 1 to the memory depth | 406–407, 411–413 | `:WAVeform:STARt 1` / `:WAVeform:STOP 10000` **verified** (W4b S10): RAW ASCii at 10 kpts reads in one go, no chunking needed. Larger depths and `:WAVeform:POINts`: not tested |
| Waveform data | `:WAVeform:DATA?` | TMC block (BYTE/WORD), or comma-separated volts (ASCii). Volts = `(raw − YORigin − YREFerence) × YINCrement` | 403, 407–408 | ASCii **verified** (W4 S5): 1000 comma-separated volts, **no TMC header**. RAW ASCii (W4b S10): 10 000 values, 140 000 B, also no TMC header; PREamble `2,2,10000,1,4.000000E-7,-2.000000E-3,0.000000,1.3333E-04,0,32768`. BYTE/WORD and the volts formula: not tested |
| Waveform scaling | `:WAVeform:PREamble?` (10 fields: format, type, points, count, xinc, xorg, xref, yinc, yorg, yref); also `:WAVeform:XINCrement?` / `XORigin?` / `XREFerence?` / `YINCrement?` / `YORigin?` / `YREFerence?` | | 408–414 | `PREamble?` **verified** (W4 S5): 10 fields, `2,0,1000,1,2.000000E-6,-1.000000E-3,0.000000,1.3333E-04,-22459,32768`. xinc/xorg reproduce the USB CSV time axis exactly (Phase 6 comparison). Single-field queries: not tested |
| Save waveform to stick | `:SAVE:WAVeform D:/<name>.csv` (screen, `.bin`/`.csv`); `:SAVE:MEMory:WAVeform D:/<name>.csv` (memory, `.bin`/`.csv`/`.wfm`); `:SAVE:STATus?` → 1 when done | **There is no SCPI command that reads a file back.** A LAN CSV has to be built from `:WAVeform:DATA?` + `PREamble?`, unless the SMB share route is used (below) | 239–241 | `:SAVE:WAVeform` **verified, corrected** (W4 S6, S7): writes `p6wav0.csv` (index digit appended), header `Time(s),CH1V`, 1000 rows for the screen. **Corrected:** `:SAVE:STATus?` returns `1` even when nothing was written (W4 S7b), so it is not proof of a save. `:SAVE:MEMory:WAVeform D:/p6mem.csv` **failed** (W4b S10): `:SAVE:STATus?` = 1 and `0,"No error"`, but no `p6mem*` file on the stick, the same silent failure as `:SAVE:SETup`. A memory CSV can only be saved from the menu (scope/probe facts, CSV save path) |
| Setup save / load (file) | `:SAVE:SETup D:/<name>.stp`; `:LOAD:SETup D:/<name>.stp` | Extension `.stp` | 238–239, 246 | `:SAVE:SETup` **failed** (W4 S7, S7b): twice it returned `:SAVE:STATus?` = 1 and `0,"No error"`, but no file appeared. Unusable on 00.01.05 (Open Questions). `:LOAD:SETup`: not tested |
| Setup over LAN | `:SYSTem:SETup?` (read); `:SYSTem:SETup <block>` (write) | TMC block whose payload "is expressed in ASCII". Whether it is byte-identical to the `.stp` file **needs bench** | 270–271 | Read **verified, corrected** (W4 S5; decoded in the Phase 6 comparison): a 2 867 B TMC payload that is **binary, not ASCII**. It is a 20 B header, then 29 records, each a short binary header plus a zlib stream (6 745 B decoded): packed little-endian integers and length-prefixed strings, with no field names. It is **not the `.stp` format** (that is XML). 214 of the 215 distinctive integer values in `p6menu0.stp` also occur in it. Write: not tested |
| Setup registers | `*SAV <0..49>`; `*RCL` | | 129–130 | Not tested |
| Probe ratio | `:CHANnel<n>:PROBe?` | One of 0.001 … 50000, e.g. `10` | 76–77 | **Verified** (W4 S4: CH1 `10`; S8: CH2 `1`). Setting it (`:CHANnel<n>:PROBe 10`): not tested |
| BW limit | `:CHANnel<n>:BWLimit?` | `20M` or `OFF`. 20 MHz is the only limit | 71 | **Verified** (W4 S4): `OFF` |
| V/div | `:CHANnel<n>:SCALe?` | Scientific notation, V/div | 75–76 | **Verified** (W4 S4 `1.000000E+00`; S8c CH2 `5.000000E-02`) |
| Offset | `:CHANnel<n>:OFFSet?` | Scientific notation, V | 74 | **Verified** (W4 S4): `-2.994604E+00` |
| Coupling / on / invert / units | `:CHANnel<n>:COUPling?` (AC/DC/GND), `:CHANnel<n>:DISPlay?`, `:CHANnel<n>:INVert?`, `:CHANnel<n>:UNITs?` | Input impedance has no SCPI setting (fixed 1 MΩ) | 72–73, 78 | **Verified** (W4 S4): `DC`, `1`, `0`, `VOLT` |
| Timebase | `:TIMebase[:MAIN]:SCALe?`; `:TIMebase[:MAIN][:OFFSet]?`; `:TIMebase:MODE?` | s/div; s; `MAIN` or `ROLL` | 291–293 | **Verified** (W4 S4, long forms `:TIMebase:MAIN:SCALe?` / `:TIMebase:MAIN:OFFSet?`): `2.000000E-4`, `0.000000`, `MAIN`. Short forms: not tested |
| Acquisition | `:ACQuire:SRATe?`; `:ACQuire:MDEPth?`; `:ACQuire:TYPE?` | | 20–22 | **Verified** (W4 S4): `2.500000E+6`, `1.0000E+04`, `NORM` |
| Trigger (common) | `:TRIGger:MODE?` (EDGE, IIC, …); `:TRIGger:SWEep?` (AUTO/NORM/SING); `:TRIGger:STATus?` (TD/WAIT/RUN/AUTO/STOP); `:TRIGger:COUPling?` | | 300–302 | MODE/SWEep/STATus **verified** (W4 S4): `EDGE`, `AUTO`, `TD`. COUPling: not tested |
| Trigger (edge) | `:TRIGger:EDGE:SOURce?`, `:TRIGger:EDGE:SLOPe?`, `:TRIGger:EDGE:LEVel?` | | 305–306 | **Verified** (W4 S4): `CHAN1`, `POS`, `1.617302E0`. S8c set CH2 as the source, but the report does not say whether by menu or SCPI, so the SCPI set is not tested |
| Trigger (I²C) | `:TRIGger:IIC:SCL?`, `:TRIGger:IIC:SDA?`, `:TRIGger:IIC:CLEVel?`, `:TRIGger:IIC:DLEVel?`, `:TRIGger:IIC:WHEN?` (`STAR`/`REST`/`STOP`/**`NACK`**/`ADDR`/`DATA`/`ADAT`), `:TRIGger:IIC:AWIDth?`, `:TRIGger:IIC:ADDRess?`, `:TRIGger:IIC:DIRection?` | The audit's "MissedAck" is `NACK` in SCPI | 365–370 | WHEN?/CLEVel? **verified** (W4 S4): `STAR`, `1.617302E0`. The other IIC queries and the `NACK` value: not tested |
| I²C decode | `:BUS<n>:MODE?`, `:BUS<n>:IIC:SCLK:SOURce?`, `:BUS<n>:IIC:SDA:SOURce?`, `:BUS<n>:IIC:ADDRess?` (NORM/RW), `:BUS<n>:THReshold? SDA` / `? SCL` (the decode threshold, ~1.65 V per §4.1) | | 25, 31, 46–48 | `:BUS1:MODE?` **verified** (W4 S4): `PAR`. `:BUS1:THReshold? SDA` answers (`0.000000`, with the bus in PAR mode, so not a decode threshold yet). IIC source/address queries: not tested |
| Measurement (one value) | `:MEASure:ITEM? <item>,CHANnel<n>`, with items such as `VBASe`, `VTOP`, `VAMP`, `VPP`, `VMIN`, `RTIMe`, `FTIMe` | Scientific notation. About `9.9e37` means invalid (third-party note, needs bench) | 192, 195–196 | **Verified** (W4 S4: VAMP/VTOP/VBASe on CH1 match the panel; S8c: VAMP/VPP on CH2). `9.9E37` = invalid **verified** (W4 S8b): CH2 returned `9.9000E+37` until CH2 was turned on, made the trigger source and AUTO was pressed (S8c). Which of the three was needed was not isolated. RTIMe/FTIMe/VMIN: not tested |
| Measurement statistics | `:MEASure:STATistic:ITEM? {MAXimum\|MINimum\|CURRent\|AVERages\|DEViation\|CNT},<item>[,<src>]` | | 199–201 | Not tested |
| Measurement thresholds | `:MEASure:SETup:MAX\|MID\|MIN <pct>` with `:MEASure:THReshold:SOURce`, `:MEASure:THReshold:TYPE {PERCent\|ABSolute}` | §4.3's 30 %→70 % rise time needs `MIN 30`, `MAX 70`. The defaults are not stated in [PG] (**needs bench**) | 201–203, 206–207 | Queries **verified** (W4 S4): `PERC`; MAX/MID/MIN = **90/50/10 %** (defaults now known). Setting 70/30: not tested |
| All-measure panel | `:MEASure:AMSource?` | CHAN1–4 or OFF | 197 | **Verified** (W4 S4): `OFF` |
| **Active measurement list** | **No such query in [PG].** | The capture tool must query a named item list (taken from the card or a default set). Parsing `:SYSTem:SETup?` might recover the panel's items (**needs bench**) | — | Not settled. The `:SYSTem:SETup?` blob has no field names (see above), so recovering the panel's items from it is not practical. The capture tool queries a named item list |
| LAN | `:LAN:IPADdress?`, `:LAN:DHCP?`, `:LAN:STATus?`, `:LAN:MAC?`, `:LAN:VISA?`; menu `Utility > IO` | Transport is not stated in [PG]. Raw socket port **5555** is from the third-party README (**needs bench**) | 6–7, 139–148 | **Verified** (W4 S1, S2, S2b, S4): menu `Utility > IO`; fixed IP `192.168.50.2/24` on a direct link to the Mac (`en7`, `192.168.50.1`); MAC `00:19:AF:A5:19:A7`. **Raw socket port 5555 answers**; VXI-11 portmapper (111) is open and the web "SCPI Panel Control" works (`TCPIP::192.168.50.2::INSTR`). `:LAN:IPADdress?`/`:LAN:VISA?` answer. **Corrected:** macOS `nc` drops the reply when stdin ends; a client must hold the socket open and read until the reply is complete, not until EOF (W4 S2, S2b). No socket-port setting on the IO page. DHCP?/STATus?/MAC? queries: not tested |
| LAN file drop (alternative) | `:SAVe:SMB:SERVerpath \\<ip>\<share>`, `:SAVe:SMB:USERname`, `:SAVe:SMB:PASSword`, `:SAVe:SMB:CONNect`, `:SAVe:SMB:CONState?`; the share appears as drive `I:` ([UG] p.212) | The scope can write native PNG/CSV/STP files straight into a Mac SMB share. An option for Phase 7 (**needs bench**) | 242–245 | Not tested. Still an untested alternative for Phase 7 |
| Scope clock | `:SYSTem:DATE?`, `:SYSTem:TIME?`; set with `:SYSTem:DATE <Y>,<M>,<D>`, `:SYSTem:TIME <H>,<M>,<S>` | Not desk-checked in [PG] (added at the bench) | — | **Verified** (W4 S4, S4b): it read `2013-01-18 09:52:08` (≈ 13.75 years slow); after the sets it read `2026-10-19` / `23:19:26`, matching the Mac. One of the three set commands raised `-109,"Missing parameter"` (likely the dashed date form; not isolated), so use the comma form and read it back. Persistence across a power cycle: not tested. There is no front-panel date/time setting (W4 S1) |
| Version / error queue | `:SYSTem:VERSion?`, `:SYSTem:ERRor?` | | — | **Verified** (W4 S4): `3.0` (not the firmware version), `0,"No error"` |

**Scope and probe facts**

| Fact | Value | Source | Status |
|---|---|---|---|
| DHO804 Cal output | **1 kHz, 3 Vpp square wave**. No amplitude tolerance is given | [DS] p.17 "Probe Compensation Output"; terminal described in [UG] p.23 | Nominal: desk-verified. **Verified** (W4 S3, S4; Rigol stock probe at 10×, ratio 10): Vamp 3.0037 V, Vtop 2.9774 V, Vbase −26.3 mV, so a ≈ 0 → 3 V square wave, and **V4 reads Vamp**. The Vbase panel value alternated between −26.266 mV and 43.333 mV (observed, not interpreted). V4's ±3 % is our own tolerance, not Rigol's |
| Setup-file extension | **`.stp`**, the only type offered on load | [UG] p.214 (Save Setup), p.219 (Load Setup: "default file type is *.stp, and no other options"), p.244 (defaults); [PG] p.238, 246 | **Verified** (W4 S7b): the menu save wrote `p6menu0.stp` (43 839 B), an **XML** file (`<?xml …?>`, a `<meta>` root with model, firmware `00.01.05.00.01` and serial, then 43 `<ServiceIDnn>` blocks of integer fields). Saving it over SCPI fails (SCPI table). Loading: not tested |
| CSV save path (menu) | **Storage → Save tab → Choose "Save Wave" → Data Source `Screen` or `Memory` → Format `*.csv`** (Screen offers .bin/.csv; Memory offers .bin/.csv/.wfm) → File Path (`D:` once a stick is detected) → Save. Storage is opened from the lower-left function navigation icon or the toolbar Storage button. The audit's "Waveform/Trace" label does not appear in [UG]: **corrected** | [UG] pp.210–213 (§20.1, §20.2.2) | **Verified** (W4 S6, S7) with Data Source `Screen`: wrote `p6menu0.csv`, byte-identical to the SCPI `p6wav0.csv` of the same frozen trace. The "Choose" control lists "Save wave", "Save image" and "Save setup" (W4 S7). The setup save is **Storage → Save → Choose "Save setup" → File Name → Save** (W4 S7b). Data Source `Memory` **verified** (W4b S10b): **Storage → Save → Choose "Save wave" → DATA SOURCE = MEMORY → FORMAT = \*.csv → File Name → Save** (the menu labels read exactly `DATA SOURCE` and `FORMAT`). It wrote `p6mem0.csv` (160 045 B, 10 001 lines). **The memory CSV has its own layout:** header `CH1V,t0 =-2.000000e-03, tInc = 4.000000e-07,`, then one value per line followed by `,,`, with no time column. The screen CSV is `Time(s),CH1V` |
| Default save location | "Local Disk" (C:). Switches to `D:` automatically when a USB device is detected, or `I:` when an SMB share is connected | [UG] p.212 | Partly verified (W4 S6, S7): `D:` is the USB stick, for SCPI and menu saves. The automatic switch to `D:` was not separately observed. `I:` (SMB): not tested |
| Scope-side filename limit | ≤ 16 characters when the name is given over SCPI. §4.4 names (≥ 25 chars) can only be applied at ingest, which matches §4.4 ("renaming happens at ingest") | [PG] pp.238–242 | Desk-verified; the limit itself was not tested. **Corrected** (W4 S6, S7): the scope **appends an index digit to every saved name**, SCPI and menu saves alike (`p6img.png` → `p6img0.png`; a second menu save of `p6menu` → `p6menu1.csv`). Ingest has to expect the digit |
| Saved-file timestamps | — | Observed in Phase 6 | Observed (Phase 6 comparison, listing `/Volumes/HANTEK`): after the S4b clock set, stick files are dated 2026-10-20 00:27–00:45, while the Mac saved and copied them at about 23:22–23:46 on 2026-10-19. The stick times read **about 1 h ahead of Mac local time** (cause not established). Files from before the set are dated 2013-01-18 |
| SQ500 bandwidth | DC to 500 MHz (−3 dB) | Sensepeek *User's Guide SQ200/SQ350/SQ500* Rev 1.1, p.16 (`welectron.com/mediafiles/manuals/sensepeek/Sensepeek_SQ200-SQ350-SQ500_Manual.pdf`, sha256 `d35edf84…`) | Desk-verified. The system bandwidth is set by the DHO804's 70 MHz (§4.1). No bench check possible |
| SQ500 attenuation | **10:1, fixed** (no 1×/10× switch). Tip resistance 10 MΩ ±2 % at DC; scope input 1 MΩ; has a "scope x10 pin" | same, p.16 | **Verified 10:1** (W4 S8c): with CH2's ratio at 1×, the 3 Vpp Cal signal read VAMP 0.298 V and VPP 0.307 V. **The DHO804 does not detect it** (W4 S8, S8c): CH2 read `1` with the SQ500 attached. Every procedure sets `:CHANnel<n>:PROBe 10` (or the menu ratio to 10×) and reads it back. V2 records "fixed 10:1" |
| SQ500 tip capacitance | **9 pF**. Compensation range 9–54 pF (the DHO804's 15 pF input is inside it) | same, p.16 | Desk-verified |
| SQ10 bandwidth | **> 10 MHz** ("not impedance matched … suitable below 10 MHz"); rise time 34 ns (calculated) | Sensepeek *User's Guide SQ10* Rev 1.1, p.8 (`evision-webshop.de/media/43/df/0a/1710364194/UG SQ10 Rev1.1.pdf`, sha256 `3d297273…`) | Desk-verified |
| SQ10 attenuation | **1:1** (passive; needle resistance < 0.02 Ω) | same, pp.1, 8 | Desk-verified. **Not for edge or V_OL work** (§4.1 rule stands): 1× puts the scope's 15 pF plus the unmatched cable's capacitance on the node, which slows the very edge being measured. Its 34 ns rise time is not the limit |
| SQ10 tip capacitance | **Not specified** by Sensepeek | same, p.8 (absent) | Not tested in Phase 6: treat as unknown. Expect the scope's 15 pF plus the cable |
| Ground springs | On hand for the Rigol stock probe and the SQ500 | Bench | **Verified** (W4 S8, S8b): springs are in the stock-probe bags and the user has one that fits each probe type (the SQ500's has the same spring-needle head). The TASKS purchase note is closed. Landing one on a 0603 pad (C21.2): not tested, see PCB probe points |

**LAN-vs-USB comparison (Phase 6; acceptance "LAN capture").** A stdlib scratch script (session scratchpad, not kept) compared the S5 LAN files with the S6/S7 USB files.
- **Same capture?** Yes, for the PNG and CSV pairs. The scope was STOPPED from the start of S5 until RUN at the start of S7 (W4 S5–S7), and both PNGs show STOP. The two screenshots match pixel for pixel over the whole graticule, trace and Result panel (0 differing pixels in that area). `p6wav0.csv` (SCPI), `p6menu0.csv` and `p6menu1.csv` (menu, about 1–2 min later by the stick times) are byte-identical. The W4 note "may not come from the same acquisition" is therefore resolved: it is one acquisition. The CSV difference comes from the readout path (below), not from a new trigger.
- **PNG: match.** Both are 1024×600 RGBA PNGs with the same chunk layout. The bytes differ (93 789 B vs 97 347 B), so compare decoded pixels, not files. 1 946 of 614 400 pixels (0.32 %) differ, all outside the waveform area: the "DHO804" header overlay that only the saved file has (`:SAVE:IMAGe:HEADer` = 1), the USB-stick icon (the stick went in after the LAN pull), and 63 pixels of ±2-level colour noise on the STOP badge.
- **CSV: does not match sample for sample.** The LAN `:WAVeform:DATA?` (NORMal, ASCii) and the USB screen CSV agree on format and scaling: 1 000 points each, the same time axis (PREamble xorg −1 ms, xinc 2 µs reproduce the CSV `Time(s)` column exactly), the same voltage steps, the same 1.5 V crossings at indices 1/251/501/751, and mean high/low levels within 1.4 mV (2.981/−0.022 V vs 2.982/−0.022 V). But only 145 of the 1 000 values are equal. Away from the edges they differ by up to 64 mV, which is about the noise on the flat top (std 18–25 mV). Within ±2 samples of each edge they differ by up to 0.82 V: the LAN set starts each transition one sample earlier. This fits the two paths taking different 1-in-5 samples from the 10 kpt memory (screen point 2 µs, sample 400 ns), but that is a hypothesis, not checked.
- **Setup:** not comparable byte for byte (binary blob vs XML; see the SCPI table). Where both expose a value it agrees: CH1 scale, CH1 offset, CH1/CH2 probe codes, the CH1 trigger level, the 200 µs timebase and the IP/gateway, plus 214 of 215 distinctive integer fields. The `.stp` was saved in S7b, after RUN, with no settings changed in between by the reports. This is "consistent where comparable", not "identical".
- **Screen data (S5 vs S6/S7): no sample-for-sample match.** The screenshot half passes. The screen CSV pulled over the LAN does not match the USB screen CSV of the same capture sample for sample (above).
- **Memory data (W4b S10 vs S10b): match.** One frozen acquisition (S10b `:TRIGger:STATus?` = STOP): the LAN `:WAVeform:MODE RAW` ASCii pull (`lan_raw_ascii.txt`) against the menu memory CSV (`usb/p6mem0.csv`). A stdlib scratch script (session scratchpad, not kept) found:
  - 10 000 vs 10 000 values; **10 000 / 10 000 equal**, as numbers and as text; max abs difference **0**; alignment offset **0** (every shift of ±1…5 samples matches only 397–645 values).
  - The memory CSV header's `t0 = -2.000000e-03` and `tInc = 4.000000e-07` equal the RAW preamble's xorg and xinc exactly.
- **Are the 1 000-point screen sets subsets of the 10 k memory?** Not shown, and not provable: S5–S7 is a different acquisition from S10. Structurally they fit a 1-in-5 decimation of the middle of memory. The screen window (xorg −1 ms, xinc 2 µs) is RAW indices 2 500–7 499 at stride 5. That window has its 1.5 V crossings at screen indices 1/251/501/751, the same as both screen sets. All three sets have the same ≈ 2.53–2.67 mV value steps. But **no** screen value occurs in the RAW value set: the value grids are offset from each other (cause not checked), so even a value-level subset test can't be made across the two acquisitions. Which memory samples each screen path takes is still a hypothesis.
- **Acceptance "LAN capture": met on memory data.** The PNG matches (S5 vs S6), and the RAW memory pulled over the LAN matches the menu memory CSV of the same capture sample for sample. The screen-data readouts don't match each other, so the capture tool does not use them. The capture tool writes RAW memory data, and W6 compares its CSV against a menu memory CSV (DATA SOURCE = MEMORY) of the same frozen capture.

**Inputs for Phase 7 (capture tool), from the bench:**
- Set the scope clock over SCPI at the start of every session (comma form, then read back with `:SYSTem:DATE?`/`:TIME?`). Persistence across a power cycle is unknown, so don't assume it held. Don't match files on scope timestamps without allowing for the ≈ 1 h offset seen on the stick (row above).
- Raw socket on port 5555. Read each reply until it is complete (TMC length, or the terminating `\n` for ASCII). Don't rely on the socket reaching EOF.
- The scope appends an index digit to every saved filename. Ingest matches on the stem plus digit, and renames to §4.4.
- `:SAVE:SETup` and `:SAVE:MEMory:WAVeform` are unusable on 00.01.05 (both fail silently). `:SAVE:STATus?` = 1 does not prove a file was written. The tool saves the `:SYSTem:SETup?` binary blob over the LAN as the setup file (not human-readable), and the log entry records the readable settings from the S4 queries. There is no per-capture menu save (user, W4b).
- The waveform the tool writes is RAW memory: `:STOP`, then `:WAVeform:SOURce CHANnel<n>`, `:WAVeform:MODE RAW`, `:WAVeform:FORMat ASCii`, `:WAVeform:STARt 1`, `:WAVeform:STOP <mdepth>`, `:WAVeform:DATA?` and `:WAVeform:PREamble?`. That matches the menu memory CSV sample for sample (LAN-vs-USB comparison, above). The NORMal screen readout is not canonical. A single read is verified only at 10 kpts; deeper memory may need chunking.
- The SMB drop (`:SAVe:SMB:*`, drive `I:`) is still an untested alternative.

**Inputs for Phase 8 (procedures), from the bench:**
- The SQ500 is 10:1 and the scope doesn't detect it. Set `:CHANnel<n>:PROBe 10` (or the menu ratio) and read it back before measuring.
- Turn the channel on and make it the trigger source before `:MEASure:ITEM?`. Otherwise the result can be `9.9E37` (invalid).
- Measure thresholds default to 90/50/10 %. The 30→70 % rise time needs `:MEASure:SETup:MAX 70` and `:MEASure:SETup:MIN 30`, set and read back.
- V4 reads Vamp on the Cal output (≈ 0 → 3 V).
- Ground springs fit both probes.
- The user needs menu steps spelled out button by button. The S6 wording ("Choose 'Save Setup'") was not followable, and the S3 step only worked as a full walk-through.

**ESP32-S3 V_OL (the check behind §2.1's "≈ 30–80 mV").**
- **Source:** *ESP32-S3 Series Datasheet* v1.7 (Espressif, 2023), Table 4-4 "DC Characteristics (3.3 V, 25 °C)", p.57, and Table 2-1 note 6, p.12. **The datasheet is not in `docs/references/`.** It was read from the user's local copy `~/Downloads/esp32-s3_datasheet_en.pdf` (sha256 `049b83bb…`). See TASKS Deferred.
- **What the datasheet says:**
  - V_OL max = 0.1 × VDD = **0.33 V**, measured "using high-impedance load" (note 2). That makes it a no-load figure, not a bound at our ~2 mA sink.
  - I_OL **typ 28 mA at V_OL = 0.495 V**, with VDD = 3.3 V and **PAD_DRIVER = 3 only**.
  - Default drive strength is 20 mA (p.12). That is the setting `v6-ref` uses. **No V_OL or I_OL figure is given for it.**
- **What follows:**
  - At CAP_3 the typical R_on is ≈ 0.495 V / 28 mA ≈ **18 Ω**, so ≈ **35 mV** at 2 mA. This assumes the low-current linear region and is a typ value at 25 °C, not a guarantee.
  - The audit's 15–40 Ω range is anchored only at the CAP_3 end. The 40 Ω end (default drive, so the upper ~80 mV) is our own extrapolation.
- **Verdict: partly supported.** The order of magnitude (tens of mV) follows from a typical datasheet figure. The 30–80 mV band is not a datasheet spec.
- **What the §4.3 procedure may claim:**
  - Pass/fail stays **V_OL ≤ 0.4 V** (UM10204, 3 mA).
  - "Expect tens of mV (≈ 35 mV at CAP_3, from the datasheet's typical I_OL; default drive not specified)" may appear only as a labelled **estimate [own]**. The "> 0.2 V = investigate the setup" line stays as our own heuristic.
  - The procedure must not present 30–80 mV as a pass band.

**Third-party DHO800 LAN/MCP project (input to W5).** The audit doesn't name the project, so Phase 5 checked the three GitHub candidates (data from `gh api`, 2026-10-19).

| Project | Licence | Activity | Notes |
|---|---|---|---|
| **`mattjax16/rigol-dho-mcp`** @ `f9ac719` | MIT | Created 2026-07-09. 26 commits, the last on 2026-07-30 (pushed 2026-10-17). 2 stars, 1 open issue ("MCP v2 migration"). | Best fit. Python ≥ 3.10, `mcp<2.0` pinned. Raw socket on port 5555. Stdlib-only `scpi.py` (~215 lines) plus a FastMCP `server.py` with 14 tools and a `rigol-dho-cli`. No tests. Doesn't say which firmware it was tested on |
| `csibug/rigol-dho824-mcp` | MIT | 1 commit (2026-03-29), inactive | Bundles Rigol's manuals converted to Markdown |
| `MasterJubei/pydho800` | BSD-3 | 27 commits, the last on 2024-05-08, stale | Library only, no MCP. Predates firmware 00.01.05 |

`mattjax16` against §5 item 1:
- **Covered:**
  - `*IDN?`.
  - Per-channel probe ratio, BW, scale, offset, coupling (`get_status`).
  - Timebase, sample rate and memory depth.
  - Trigger mode/sweep/status, but configuration is edge-only.
  - A single named measurement (`get_measurement`).
  - Screen or RAW waveform, chunked.
  - A PNG screenshot.
- **Not covered:**
  - The setup file (`:SYSTem:SETup?` and `:SAVE:SETup` are absent).
  - I²C trigger and decode settings, which would need the opt-in raw `scpi_command`.
  - A list of active measurements (no SCPI exists for it).
  - **Writing files at all.** The screenshot comes back as an MCP image and the waveform as decimated JSON, both into the session context. Only the CLI writes a `capture_NNNNN.png`.
  - Names per §4.4 and the §4.6 log entry.
- **Effort:**
  - Adopting the MCP server as it stands gives interactive control but none of the file/log contract. We would still write the capture tool, and the server needs a Python ≥ 3.10 venv (the repo's default `python3` is 3.7).
  - Reusing its `scpi.py` (MIT, keep the notice) under our own `tools/lab/capture.py` saves about 100 lines of socket/TMC-block code. Everything else is ours either way: setup, I²C queries, CSV from PREamble, naming, YAML.

**Recommendation (for the user at W5): build our own `capture.py`.** Either vendor `mattjax16`'s `ScpiClient` with its MIT notice, or write the equivalent. Don't adopt the MCP server as the capture path. Use the Phase 6 smoke test (port 5555, `*IDN?`, `:DISPlay:DATA? PNG` via `rigol-dho-cli`) to validate the transport on 00.01.05 whichever way W5 goes. Registering the MCP server for interactive debugger sessions is a separate, later choice, outside this initiative.

**W5 decision (user, 2026-10-20): "build + borrow the socket client".** We build our own `tools/lab/capture.py` and vendor `mattjax16/rigol-dho-mcp`'s MIT `ScpiClient` (`scpi.py`) @ `f9ac7191869845ae46ca714de69a877c388b2530`, keeping its licence notice and crediting it. The S9 smoke test was never run, so the vendored client is first exercised on 00.01.05 in Phase 7.

**PCB probe points (Phase 5 kiutils probe).**
- **Method:** a read-only scratch script (kiutils 1.4.8 + shapely), run on `hardware/pcb-main/kicad/motion-play-main.kicad_pcb` **@`c2acffc`** (v7; HEAD is identical) and **@`fd632ef`** (v6). Both were extracted with `git show`.
- **Distances** are copper pad edge to copper pad edge. Pads are modelled as rotated rectangles or circles, and roundrect corners are ignored, so the distances run slightly low.
- **Vias are excluded:** both boards have `(tenting front back)`, and the nearest GND vias sit under U5's exposed pad.

v7, the closest GND-net pad to U5 (BQ24195) pin 5 (`/I2C_SCL`) and pin 6 (`/I2C_SDA`), front side:

| Pad | Value | Edge-to-edge | Centre-to-centre | Note |
|---|---|---|---|---|
| **C21.2** | 4.7 µF (0603-size pads, ~0.95 × 0.9 mm) | **2.64 mm** (to U5.5) | 3.67 mm | **Closest usable GND.** C21.1 next to it is `Protected_VBUS`, so the ground contact must not bridge the two |
| R32.2 | 330 Ω (BQ_ILIM) | 3.44 mm (to U5.6) | 4.19 mm | |
| C20.2 | 1 µF | 3.66 mm (to U5.5) | 4.70 mm | Its pad 1 is also `Protected_VBUS` |
| TP4.1 | PGND test pad | 12.09 mm | 13.26 mm | Today's V6 ground (§4.2) |
| U5.2 / U5.3 (own pins on the GND net), U5.25 (EP) | — | 1.20 / 0.70 / 0.24 mm | — | Not usable: 0.5 mm-pitch QFN pins beside the signal pins, and the EP is under the package |

**v6 names** (from `fd632ef`):
- **Master SDA/SCL test points:** **TPIO43** = `/I2C_SDA`, **TPIO44** = `/I2C_SCL`. These are the same names as v7. The master is U2 (T-Display-S3, pins 15/16).
- **BQ24195:** **U5**, pin 5 = `/I2C_SCL` and pin 6 = `/I2C_SDA`, the same as v7. On v6 the package is rotated, but C21.2 is again 2.64 mm edge-to-edge (R32.2 3.44, C20.2 3.66).
- **GND pads:** **TP4** (value `PGND`, net GND), 6.85 mm from U5 pins 5/6, and **TP_GND1** (net GND), about 36 mm from U5. Note: TP4 is 6.85 mm from U5 on v6 but 12.09 mm on v7, so "TP4 on both boards" would not be the same ground length. Correction to CL-26's wording: v6 *has* TP4; TP_GND1 was the second GND pad.
- **Other v6 pads:** TP_3V1 (+3.3V) and TP_5V1 (+5V).
- **Master-side GND, for the same-ground-length rule:**
  - v6: the nearest GND to TPIO43/44 is U2.14, a T-Display header pin (through-hole), 8.26 mm away. TP_GND1 is about 38–41 mm centre-to-centre.
  - v7: U3.40, an ESP32 module pad, is 1.19 mm away (not a practical clip point), and C9.1 (100 nF) is 3.05 mm away.
- **Implication for §4.3:** C21.2 gives an identical 2.64 mm ground on both boards at the BQ end. That makes it the natural "same ground length" point for the U5 pin 5/6 arms, if the probe ground (spring or ≤ 10 mm wire) can land on a 0603 pad. Whether it can **needs bench** (not tested in Phase 6; the springs fit the probes, W4 S8b).

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
- Adopting `mattjax16/rigol-dho-mcp` as the capture tool as-is: untested on 00.01.05 (the S9 smoke test was not run), writes no files, has no setup pull and no I²C configuration; we build `capture.py` and vendor only its MIT `ScpiClient` (user, W5).

## Open Questions
- ~~Phasing: role and containers before scope tooling?~~ Yes, with a milestone merge after Phase 4 (user, 2026-10-18).
- ~~Cloud backup service~~ → Google Drive (user, 2026-10-18). Still open: the exact local Drive folder path (asked in Phase 7).
- ~~Build vs adopt the capture tool~~ → build our own `capture.py`, vendoring the MIT `ScpiClient` from `mattjax16/rigol-dho-mcp` @ `f9ac719` (user, W5, 2026-10-20: "build + borrow the socket client").
- ~~Old scope guide~~ → banner + pointer.
- ~~Hook mechanism~~ → git only. ~~Caps~~ → soft except `as_of`. ~~Legacy artefacts~~ → banner in place. ~~Card filename~~ → `V7R-NNN-<slug>.md`.
- ~~Does the debugger role's checkpoint section carry the `decisioning.md` §4.2 criteria table, or a pointer to it?~~ Moved out of this initiative with the role install (TASKS.md Deferred).
- ~~Does `4da1c67` still build with today's PlatformIO and library versions?~~ Yes: env `lilygo-t-display-s3` builds clean, no fix needed (Phase 1, 2026-10-19).
- ~~Is the ESP32-S3 V_OL expectation (≈ 30–80 mV) supported by the datasheet?~~ Partly. The CAP_3 typical figure gives ≈ 35 mV, and the band is not a spec. The pass limit stays ≤ 0.4 V and the expectation is a labelled estimate (Verified instrument facts; Phase 5, 2026-10-19).
- ~~`Result commit` self-reference convention~~ → literal `self` for both `prereg_commit` and `Result commit`, resolved from git (Phase 3, 2026-10-19).
- ~~**`:SAVE:SETup` fails silently on 00.01.05** (W4 S7, S7b): what does the capture tool save as the setup file?~~ → the `:SYSTem:SETup?` binary blob over the LAN, and the log entry records the readable settings from the S4 queries; no per-capture menu save (user, W4b, 2026-10-20: "Let's go with option a").
- ~~**LAN CSV ≠ USB CSV for the same capture** (Phase 6 comparison; screen data, 145/1 000 equal)~~ → compare memory data instead. The LAN RAW pull matches the menu memory CSV 10 000/10 000 (W4b S10/S10b). The capture tool writes RAW memory data, and W6 compares against a menu memory CSV (Verified instrument facts, LAN-vs-USB comparison). `:SAVE:MEMory:WAVeform` fails silently on 00.01.05 (W4b S10), so the memory CSV for W6 is a menu save; nothing in the tool depends on it.

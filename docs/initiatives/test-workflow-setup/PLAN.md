# Test Workflow Setup — Plan

## Approach

One initiative merging topic 4 (`docs/research/v7-retry/test-workflow-audit.md` §6.1) with topic 6 (`context-strategy.md` §10.1). The work is in two tracks, separated by a milestone merge.

**Track 1: log-only ready (Phases 1–4).** This is everything a log-only debug card needs (`decisioning.md` §3.3): the baselines, the `lab/` containers and templates, the checker and hook that stop a Phase-25-style lost result, and the installed debugger role. At the end of Phase 4 the Orchestrator opens a PR and the user merges it to main with a **merge commit**. The debug track can then start (first debugger session transcribes `decisioning.md` §2 into STATE.md). The Orchestrator re-cuts `feat/test-workflow-setup` from the new main for Track 2.

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
| W1 | before 4 | Edit pass on `docs/research/v7-retry/debugger-role-draft.md`, including whether the checkpoint section carries the `decisioning.md` §4.2 criteria table | User says the draft is final |
| W2 | 4 | Approve or apply each touch point: PROTOCOL.md, PROJECT.md pointer, tools/CONTEXT.md, banners, auto-memory deletions | Each item is approved or declined |
| W3 | end of 4 | Merge the milestone PR (merge commit) | PR merged |
| W4 | 6 | Bench: scope on the LAN, SCPI smoke tests, USB saves for comparison (§4.8 blocks) | All REPORT blocks returned |
| W5 | 6→7 | **Decision gate:** build our own capture tool or adopt the third-party one, based on the Phase 5 + 6 findings | User decides |
| W6 | 7 | Bench: one capture-tool acceptance capture vs USB | REPORT returned |
| W7 | 9 | User runs the dry run as a `claude --agent debugger` session, then a second fresh debugger session for the L0 test | User reports both sessions done |

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
| Budget | A fresh debugger session's L0 measures < 500 lines and ≤ ~12k tokens (counting the actual files). |
| Dry run | The v6 dry run runs as a debugger session: card pre-registered, raw data committed per arm, recorded with STATE updated in the same commit, notebook entry written. A second fresh debugger session then states the bench state correctly from L0 + default L1 alone, without asking the user. |
| Retirement | No v7 lines in the memory index; banners on the §2.4 items; PROJECT.md pointer present. |

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
  
  One-time setup is `git config core.hooksPath .githooks`, documented in `tools/CONTEXT.md` (the tools/lab section) and in the debugger role.
- **`Result commit` chicken-and-egg:** the commit can't contain its own hash. The hook's check means "the line is present and non-empty". Convention: the recording commit writes `Result commit: this commit (see git log -- <card>)`, and the checker resolves it from git. A Phase 3 Worker must settle this and write it into the card template.

**Role install and touch points (Phase 4).**
- Copy the user-finalised draft to `.claude/agents/debugger.md` verbatim (it is allowed in by `!.claude/agents/`).
- Touch-point edits are each shown to the user as a diff and applied only on approval (W2):
  - PROTOCOL.md: Debugger row in the roles table, a `lab/` non-initiative-documents entry, a Debugger → Planner relay row and an escalation line (`context-strategy.md` §9);
  - PROJECT.md: the pointer line `**v7 main PCB I²C fault:** open, see lab/STATE.md.`;
  - `tools/CONTEXT.md`: the §8.3 kiutils rule replacement, the §8.2 source-hash rule and a `tools/lab/` entry;
  - banners on the §2.4 items: investigation (frozen), session-resume and fresh-perspective prompt (retired), the two explorations, `v7-main-i2c.audit.md`, `REVIEW-HANDOFF.md`. **Not the scope guide yet**; that is Phase 8;
  - auto-memory: delete `project_v7_i2c_bq_debug.md` and `project_pcb_revision_apr2026.md` and their index lines, and move the BQ24195 C90862 stock tip into `hardware/CONTEXT.md`. Memory is outside the repo, so the user may prefer to do this by hand.
- Budget check: count the lines and bytes/4 of the actual L0 files (CLAUDE.md, PROJECT.md, MEMORY.md, debugger.md, PROTOCOL §Session Management + §Git, STATE.md at cap) and record the numbers in SESSION.md.

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
- The user runs `claude --agent debugger`. The session pre-registers a card (next `V7R-NNN`; title "Setup validation + known-good reference on v6 (`v6-ref`)"; `variable_changed: none — instrument validation`; `structure: single (justified)`), flashes `v6-ref` to v6, runs §4.2 then §4.3, captures with the tool, ingests, and records with STATE + notebook.
- The user then opens a second fresh debugger session and asks for the bench state.
- The Orchestrator verifies afterwards from git: the card's commits per arm, the recording commit touching STATE, the notebook entry, the evidence files.

## Rejected Approaches
- A separate context-scaffolding initiative: both topics build `lab/`, and one dry run validates both (decisioning §3.1).
- A Claude Code hook for the STATE rule: it isn't versioned (`.claude/*` is gitignored) and only fires inside Claude; git `core.hooksPath` only (user, 2026-10-18).
- Hard caps on STATE.md sections: soft warnings, with only a stale `as_of` blocking (user, 2026-10-18).
- Moving legacy debugging docs to an archive folder: banners in place, so cited paths stay valid (user, 2026-10-18).
- Deleting the old scope guide: it gets a RETIRED banner and a pointer instead (user, 2026-10-18).
- Holding the debug track until the whole initiative closes: log-only cards start after the Phase 4 milestone merge (user, 2026-10-18).
- A separate counter file for V7R IDs: the `lab/cards/` directory is the counter (context-strategy §6.2).
- Squash-merging initiative PRs: it would orphan the baseline tags.

## Open Questions
- ~~Phasing: role and containers before scope tooling?~~ Yes, with a milestone merge after Phase 4 (user, 2026-10-18).
- ~~Cloud backup service~~ → Google Drive (user, 2026-10-18). Still open: the exact local Drive folder path (asked in Phase 7).
- ~~Build vs adopt the capture tool~~ → evaluate first. The gate is W5, after Phase 6.
- ~~Old scope guide~~ → banner + pointer.
- ~~Hook mechanism~~ → git only. ~~Caps~~ → soft except `as_of`. ~~Legacy artefacts~~ → banner in place. ~~Card filename~~ → `V7R-NNN-<slug>.md`.
- Does the debugger role's checkpoint section carry the `decisioning.md` §4.2 criteria table, or a pointer to it? The user decides during the W1 edit pass.
- Does `4da1c67` still build with today's PlatformIO and library versions? To be found in Phase 1.
- Is the ESP32-S3 V_OL expectation (≈ 30–80 mV) supported by the datasheet? To be found in Phase 5.
- `Result commit` self-reference convention (see Technical Notes). Settled in Phase 3.

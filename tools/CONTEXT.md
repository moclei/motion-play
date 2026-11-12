# Tools — AI Context

## Critical Rule

**Never read `.kicad_sch` or `.kicad_pcb` text into context, and never edit them directly.** Use the tools below. Exception: targeted read-only kiutils or `kicad-cli` probes are allowed when no tool output answers the question (e.g. zones, stackup). Run them from a scratch script, print only the numbers you need, and cite the probe and file commit.

## kiutils Rule

**Every kiutils schematic load goes through the KiCad 8/9 shim, and no script writes a schematic while KiCad has the project open.** kiutils 1.4.8 doesn't read `(hide yes)`, so a bare load + save unhides every hidden field. Import `tools/schematic-modify/kiutils_k9.py` before the first `from_file`, and save with `kiutils_k9.save_schematic` (it refuses while a `~*.kicad_sch.lck` exists). Details: `tools/schematic-modify/CONTEXT.md`. Boards: a bare kiutils round trip of a KiCad 9 `.kicad_pcb` is lossy and unloadable (v8-debug-board PLAN OQ-11); don't write a KiCad-saved board with kiutils until Phase 13 settles a write path.

## Source-Hash Rule

**Every generated context file carries provenance, and every reader checks it.**

- **JSON:** a top-level `_provenance` object: `source`, `source_sha256`, `generator`, `generator_commit`, `generated`.
- **Markdown:** the same fields as a front-matter block.
- **Images:** a sidecar `<name>.meta.json`, or the provenance block of the narrative that embeds them.
- **Check:** `python3 tools/lab/check_state.py --fresh <file>` recomputes the source hash (exit 0 fresh, 1 stale, 2 no provenance). Run it before citing a generated file in a card or a design decision.
- **Scope:** all generated context, including `circuit-context.json`. `extract.py` writes `_provenance` since 2026-11-03 (v8-debug-board Phase 11): `source` is the root sheet and `sources` maps each child sheet to its sha256; `--fresh` checks both, so an edit to any sheet marks the file stale. Older `circuit-context.json` outputs (v7, sensor boards) have none, so `--fresh` reports them as having none (exit 2); judge those from git.

## KiCad Schematic Tools

These three toolkits form a pipeline: **gen** creates sheets, **modify** surgically edits existing sheets, **context** extracts/annotates for AI consumption.

### schematic-context/

Extracts circuit data from `.kicad_sch` files into compact `circuit-context.json` files optimized for AI analysis. Also writes `ai_`-prefixed annotations back into schematic symbols.

| Script | Purpose |
|--------|---------|
| `extract.py` | Combines `kicad-cli` netlist export + kiutils parsing → `circuit-context.json`. Use `--previous` to preserve net/block annotations across re-extractions. Each `sheet_interfaces` pin carries the net KiCad connects it to (probe netlist on a scratch copy), not a name guess. `--check-sheet-pins [-v]` exits 1 and lists every sheet pin on no net or on a net with no component pins; it writes nothing unless `--output` is given. |
| `annotate.py` | Writes hidden `ai_function`, `ai_block`, `ai_role`, `ai_critical_specs` properties to component symbols in `.kicad_sch`. |
| `show.py` | Displays annotation coverage; `--unannotated` shows what still needs labeling. |

See `tools/schematic-context/README.md` for full usage.

### schematic-gen/

Generates complete `.kicad_sch` sheet files from structured JSON specs. Components get symbols, footprints, LCSC part numbers, net labels, no-connect flags, and hierarchical labels — all programmatically. Uses the `@jlcpcb/mcp` MCP server to search LCSC parts, check stock, and download symbols/footprints.

| File | Purpose |
|------|---------|
| `spec.json` | Structured spec for the power management sheet (components, nets, blocks). |
| `esp32_spec.json` | Structured spec for the ESP32-S3 sheet. |
| `power_v8_spec.json` | v8 debug board power sheet spec (same shape as `spec.json`, plus `v7_ref`/`dnp` per part and generated net members). Design intent: `hardware/pcb-main-v8/CONTEXT.md` Power path. Phase 10 corrections in `_note_phase10`; parts may carry `sheet` (LED sheet) and `no_connect`. Applied in place by `schematic-modify/v8_power_sheet.py`, not generated. |
| `generate_power_sheet.py` | Generates `power_management.kicad_sch` from `spec.json`. The three generators' pin rotation for 90/270-degree symbols was fixed 2026-11-03 (same fix as `modify.py`). |
| `generate_esp32_sheet.py` | Generates `esp32_s3.kicad_sch` from `esp32_spec.json`. |
| `poc_generate.py` | Proof-of-concept: generates a minimal schematic with one resistor. |

### schematic-modify/

Surgical in-place edits on existing `.kicad_sch` files — adding/removing components, sheet references, hierarchical labels. Sits between gen (full sheet creation) and context (read-only extraction).

| File | Purpose |
|------|---------|
| `modify.py` | Reusable helpers: `add_component`, `remove_component`, `add_hierarchical_label`, `add_sheet_reference`, `annotate_components`, `set_pin_net` (move a label-wired pin to another net), `pin_position`, `remove_no_connect_at`, `remove_junction_at`, `add_local_label`, `add_wire`, `rename_hlabel`, `rename_sheet_pin`, `remove_component_with_stubs`, `set_property`, `add_power_symbol`. |
| `kiutils_k9.py` | KiCad 8/9 `(hide yes)` shim for kiutils 1.4.8 plus the lock-file save guard. Imported by every schematic load path (kiutils Rule above). |
| `layout_check.py` | Read-only readability check (visible extra fields, off-paper items, labels with no justify, wire/pin-end T-touches with no junction, text overlaps and stacked labels against a per-sheet baseline that only ratchets down, worst grid zones). Part of every `--check` (end of `v8_debug_sheet.py --check`); placement rules in `schematic-modify/CONTEXT.md`. |
| `tidy_fields.py` | `--check / --apply`: netlist-neutral field tidy (hide all but Reference/Value, restore pin-number/name hiding, re-home `ai_*` to the symbol). |
| `tidy_labels.py` | `--check / --apply`: netlist-neutral label pass (KiCad justify on every label, text away from its wire, vertical-stub labels turned horizontal, stacked duplicates removed), gated by `layout_check.py`. |
| `v8_project_setup.py` | v8-debug-board: creates `hardware/pcb-main-v8/kicad/` from the v7 project at `c2acffc` (renamed `motion-play-main-v8`, empty stackup-only board) and verifies it with kicad-cli. |
| `v8_mcu_sheet.py` | v8-debug-board: MCU sheet edits for jumper rows a, e, g and the IC1 swap; `--check` verifies pin -> net and the all-v7 positions against v7. |
| `v8_bus_sheet.py` | v8-debug-board: TCA sheet edits for jumper rows b, d, f (channel protection, pull-up options, BQ isolate) and channel test points; `--check` runs the MCU check plus each jumper's positions. |
| `v8_power_sheet.py` | v8-debug-board: power sheet edits from `power_v8_spec.json` (battery protection, rows c, h, i, j, k, l, STAT LED, rail test points, rail split +3.3V_MCU / +3.3V_BUS / +5V_CORE, J7 shell-GND footprint); `--check` runs the Phase 8 and 9 checks plus every power pin and row. |

See `tools/schematic-modify/CONTEXT.md` for relationship details and typical workflow.

## KiCad PCB Tools

### pcb-context/

The **board model** is the one source for PCB context: `board_model.py` parses a `.kicad_pcb` once (`kicad_io` raw tree through `pcb_raw.py`, + kicad-cli) into `board-model.json` (true pad polygons, bodies, outline, tracks/vias, zones with de-fractured fills, stackup, per-net topology, kicad-cli DRC, `_provenance`). Every report is derived from that model, so placement, routing and planes can't drift apart. Validated on v7 `c2acffc` against the extraction audit's fixtures (`docs/research/v7-retry/kicad-extraction-audit.md` §6.1; results in `docs/initiatives/v8-debug-board/SESSION.md`, Workers #5 and #6).

| Script | Purpose |
|--------|---------|
| `board_model.py` | `.kicad_pcb` → `board-model.json`; `--check` for freshness. Per-board definitions (net classes, neighbour radii, drivers, critical nets) in `board-config/<pcb stem>.json`. |
| `net_report.py` | `net-report.md/.json`: per critical net the route narrative (tree from the driver), endpoints, reference plane per segment, bodies passed under/over, unprompted neighbours across layers (gaps, coupled length, crossings), per-via return-path notes; one summary row per other net. |
| `plane_report.py` | `plane-report.md/.json`: per copper layer ownership, zones, splits (with tracks crossing the gap), voids, antipads; mm unreferenced per signal segment; GND stitching density. |
| `render.py` | `img/net-<net>.png` per critical net and `img/plane-<layer>.png` per layer with fills, each with `.png.meta.json` (provenance, view in mm, label anchors in mm and px). |
| `report_lib.py` | Shared geometry for the three reports (measuring methods are defined here). |
| `extract.py`, `place_power.py` | Older placement tooling (`pcb-layout-context.json`); its v7 outputs are historical. To be generalised by the v8 placement work. |
| `routing_extract.py`, `routing_audit.py` | Superseded by the board model and `net_report.py` (the auditor's distances are centreline, not edge to edge). Kept for the specs and outputs the v7 debug track cites. |

**Every number names its measuring method** (track to track, track to copper, all copper, plan view; reference raw vs antipads excluded). They differ by up to 0.3 mm on v7, so cite the method with the number. Committed outputs live beside the PCB in `<kicad folder>/board-model/` (v7: `hardware/pcb-main/kicad/board-model/`); check them with `python3 tools/lab/check_state.py --fresh <file>` before citing. Look at a PNG rather than reading coordinate rows when the question is "where".

See `tools/pcb-context/README.md` for full usage.

### verify-routing.py

Verifies PCB routing against spec constraints (trace widths, clearances, net classes). Currently hardcoded to a specific board revision — needs genericization to accept an input spec file.

## KiCad Regression Harness

### kicad-regress/

`regress.py` shows that a change to the KiCad tools (parser port, dependency upgrade, new KiCad) changes no output. `run <root>` makes fresh `git archive` copies (v8 at `v8-schematic-freeze`, v7 at `c2acffc`, each with `hardware/pcb-main/resources`) and runs the reference set: kicad-cli netlists and ERC, `extract.py --check-sheet-pins`, `layout_check`, `tidy_*` and every `v8_*.py` check with `--root`, the v7 board model and reports, probe-points `pads`. `--python`, `--kicad-cli` (default 9.0.4) and `--tools <ref>` (a temporary worktree, e.g. the oracle tag `kicad10-preport`; default the working tree) choose what runs. `hash --against reference-k9.txt` checks a run against the KiCad 9 reference; `compare <rootA> <rootB>` compares two runs (JSON leaf by leaf within 1e-9, netlists structurally). `roundtrip <outdir>` loads and saves every v8, v7 and other-board `.kicad_sch`/`.kicad_pcb` through kicad-tools (raw and typed layers) and checks each is tree-identical: run it with `compare` when kicad-tools is upgraded (pinned in `tools/requirements.txt`). `iotest <outdir>` runs the I/O module's test (`test_kicad_io.py`: `tools/kicad-io/kicad_io.py` round trips, splice-save edits on KiCad 9 files and on kicad-cli 10 conversions, the guards' refusals, number and hide-flag forms; about 4 minutes). `modtest <outdir>` runs the `modify.py` differential test (`test_modify.py`: every public operation with the working tree's `modify.py` and with `kicad10-preport`'s, seeded UUIDs; netlist, ERC, plotted strings, return values and token census on kicad-cli 9, then the property and sheet ops on kicad-cli 10 copies; about 6 minutes). Also `netlist`, `erc` (setup vs real library items), `plot`/`svg` (plotted strings), `tokens` (census) and `treeeq`. Scratch only: it refuses a run root inside the repo. Run roots are 6-character names, and two runs compare cleanly only if their full paths have the same length (`extract.py` prints the netlist's byte count). Stdlib only. Usage in the `regress.py` docstring.

## Firmware & Data Tools

| Tool | Type | Purpose |
|------|------|---------|
| `diagnose-session.sh` | Shell | Queries CloudWatch Logs for Lambda invocations related to a session. Shows invocation count, errors, durations. |
| `download-session.sh` | Shell | Downloads session data (metadata + readings) from API Gateway for offline analysis. Supports `--summary` and `--check-keys`. |
| `transit-calculator.py` | Python | Calculates sensor samples per ball transit for different hoop/ball/speed combinations. Design tool for sensor rate requirements. |

## ML Training

### ml-training/

Full pipeline: download labeled sessions → preprocess into (300, 6) tensors → train 1D CNN → quantize to int8 → export as C header for ESP32-S3 firmware. See `tools/ml-training/README.md`.

## Serial Studio

### serial-studio/

JSON dashboard definition files for Serial Studio (advanced serial monitor). Multiple versioned files exist from iterative development — the latest version is the active one. These are loaded into Serial Studio to visualize real-time sensor data from the device.

## Lab Tools

### lab/

Tooling for the bench-debug `lab/` tree at the repo root (STATE, cards, log, evidence). The rules come from `docs/research/v7-retry/context-strategy.md` §4.2 and §8.2. Stdlib Python 3.7+; PyYAML is used if it's installed, otherwise a built-in front-matter parser (`validate_log.py` and the tool tests need PyYAML).

**Investigations (the registry).** Each bench investigation is a folder `lab/investigations/<name>/` holding its `STATE.md` and `NOTEBOOK.md`. The STATE front matter declares `prefix` (card ID prefix, e.g. `V7R`), `title` and `status` (`open` | `closed`). The folders are the registry: `lablib.investigations(root)` scans `lab/investigations/*/STATE.md`; there is no registry file. Every tool takes prefixes from it, and accepts an ID only if an investigation declares its prefix.

**IDs.** `<PREFIX>-NNN`, pattern `^[A-Z][A-Z0-9]{1,5}-\d{3,}$`, numbered per prefix (next = highest `lab/cards/<PREFIX>-NNN-*.md` + 1). Cards, captures and evidence stay shared and flat: `lab/cards/<ID>-<slug>.md`, `lab/captures/<ID>/`, `lab/evidence/<ID>/`; the prefix keeps investigations apart.

**`lab/BENCH.md`** is shared by all investigations: boards (ID, condition, mods, role, which investigations use it), fixtures, what's flashed now (board → commit + env, with the card ID that set it) and the bench state at the last stop. A card that changes a board or what's flashed updates BENCH.md in the same commit (a written rule, not hook-enforced). Each STATE's §6 keeps only its own baselines and points to BENCH.md.

| Tool | Purpose |
|------|---------|
| `check_state.py` | Session-start check, run per open investigation with output grouped under `== <name>` (registry findings first). A STATE `as_of` behind its prefix's highest recorded/abandoned card is **STALE**; STALE in any investigation, a STATE with no `prefix` (`NO-PREFIX`) and two investigations sharing a prefix (`DUP-PREFIX`) are the hard failures (exit 1). A closed investigation is skipped except that it may have no open cards (`CLOSED-OPEN`, warning). Also warnings: a card whose prefix no investigation declares (`ORPHAN-CARD`) and `lab/BENCH.md` missing (`BENCH`). Per investigation these only warn: open-card mismatch, a card in `run` with no commit for 7 days, CHECKPOINT DUE (≥ 3 recorded since `last_checkpoint`, or > 14 days since the last notebook entry), section caps, stale source hashes of generated files cited in Lookups, and mentions of any investigation (prefix, title, v7 terms) in auto-memory. `--inv <name>` limits the run to one investigation. `--load` also prints the default L1 load for one investigation: open cards, the last two recorded conclusions and today's log, with `self` commits resolved; it needs `--inv` when more than one investigation is open. `--fresh <file>` checks one generated file's provenance (exit 0 fresh, 1 stale, 2 none). `--root`, `--memory-dir` (or `$LAB_MEMORY_DIR`) and `--now` exist for fixtures. |
| `precommit.py` | Called by `.githooks/pre-commit` on commits that stage anything under `lab/`. It reads the registry from the index (staged STATE front matter) and rejects three things: a card moved to `recorded`/`abandoned` unless *its* investigation's STATE (the one declaring the card's prefix) is staged with `as_of` set to that prefix's highest such ID (a prefix no investigation declares is rejected); a `recorded` card with an empty `Result commit` or no `lab/evidence/<ID>/` citation in its Conclusion; and a duplicate `<PREFIX>-NNN` (same prefix, same number). Rule 4 runs `validate_log.py` on staged `lab/log/*.yaml` against the staged prefixes: **errors block, TODOs only warn** (user-confirmed), so per-arm commits made mid-session go through. |
| `capture.py` | One-command DHO804 capture over the LAN: `python3 tools/lab/capture.py --test <PREFIX>-NNN --arm A1 [--session lab/log/<date>_sNN.yaml]`; an ID whose prefix no investigation declares is refused (exit 2) before the scope is contacted. Sets the scope clock, sends `:STOP` (the scope is left stopped), and writes `lab/captures/<ID>/YYYY-MM-DD_<ID>_<arm>_<nn>.{png,csv,setup.bin}`: the screenshot, the RAW memory CSV (`Time(s),CH1V…`, values verbatim; equal to a menu memory CSV sample for sample) and the `:SYSTem:SETup?` blob (binary, not `.stp`). Appends a measurement entry to the session log (or creates it) with every scope-sourced field filled and operator fields as `TODO`; `:MEASure:ITEM?` ≈ 9.9E37 is `valid: false`. Refuses firmware other than 00.01.05 (`--any-firmware`) and memory > 10 kpts (`--chunked`, unverified). Host `--host` or `$DHO_HOST` (default `192.168.50.2`), port 5555. Exit 0 ok, 1 transport/scope error (nothing written), 2 refused. Every command it sends is bench-verified in the test-workflow-setup PLAN. **Channel drift is per arm:** each capture's channel settings are compared with the most recent earlier entry in the session log with the same `--arm` (a NOTE plus `channel_drift` in the entry); no earlier entry for that arm means no check, so `val_V3` at Cal settings and `val_V5` at card settings don't flag each other. A new session's validation skeleton carries the `V5` block as per-channel TODOs. |
| `vendor/scpi.py` | The socket/TMC layer, vendored unmodified with its MIT notice from `https://github.com/mattjax16/rigol-dho-mcp/blob/f9ac7191869845ae46ca714de69a877c388b2530/rigol_dho_mcp/scpi.py` (commit `f9ac7191869845ae46ca714de69a877c388b2530`). Upstream sha256 `9fface904495086784322b44cdfac4edaa35ea215f1c87ccdfe5b0d4004a5066`. Never edit below its header; wrap it in `capture.py`. Recheck: `tail -n +$(( $(grep -n '^# ---- end vendor header' tools/lab/vendor/scpi.py \| cut -d: -f1) + 1 )) tools/lab/vendor/scpi.py \| shasum -a 256` |
| `validate_log.py` | Checks a session log's required §4.6 fields, branching on `kind` (`log-only`: `dut.*` and per-measurement `test_id` (`<PREFIX>-NNN` with a registered prefix; `--root <repo>` picks the registry, default this repo)/`feature`/`raw_observation`; `scope`: also scope, validation, channels, values, captures). A `TODO` is pending, not missing. Exit 0 valid, 1 errors, 3 TODOs only (0 with `--allow-todo`), 2 usage or PyYAML missing. A PNG with no `ai_read` entry is a warning. `validation.V5` is four per-channel maps (`ctl_sd_mV`, `dut_sd_mV`, `excess_rms_mV`, `offset_mV`; optional `vpp_panel_mV`); a log with only the legacy `V5_noise_floor_mVpp` (V7R-001) gets a warning, not an error. **`not_run`:** any `validation.V<n>` item may be `{not_run: "<reason>"}` when the validation stopped early. It is neither a TODO nor an error, but only with `validation.passed: false`; with `passed: true` it is an ERROR. |
| `noise_floor.py` | V5 check: `python3 tools/lab/noise_floor.py --ctl <val_V5ctl csv> --dut <val_V5 csv> [--limit-mV 5]` on two `capture.py` CSVs. Per channel it prints mean, sd, max − min and excess = √(max(0, sd_dut² − sd_ctl²)) in mV, PASS/FAIL against the limit, and a FLAG (not a fail) when the control sd is outside 2.5–10 mV; that band holds only at the V7R-001 reference settings. Refuses (exit 2) when the sample interval or point count differ; warns when the smallest level step differs (a different V/div). Ends with a `validation.V5` snippet to paste into the log. Exit 0 pass, 1 fail. Stdlib only. |
| `i2c_frame.py` | V7 and V9 numbers from one `capture.py` CSV: `python3 tools/lab/i2c_frame.py <csv> [--sda CH1] [--scl CH2] [--vdd 3.3] [--expect D6]`. Thresholds are 0.3 / 0.5 / 0.7 × V_DD (0.99 / 1.65 / 2.31 V). **Idle mode** (no channel crosses 0.5 V_DD): per channel mean, sd, min, max, and a `validation.V7_idle_high_V` snippet. **Frame mode:** SDA at each SCL rise gives the address byte and the 9th bit (ACK when low). The frame starts after a START; with no START in the record, the 9-bit groups before the first STOP are used. The SCL period. The 30→70 % rise time of every rising edge per channel (linear interpolation). V_OL on each master-driven 0-bit of the address byte (the ACK excluded), gated on its SCL-high interval shrunk by 10 % at each end. Idle high from 5 µs after the last edge (its 0.5 V_DD crossing, either channel) to the record end, with ≥ 5 µs of samples after that margin, else n/a. PASS/FAIL per `known-good-reference.md` pass-table row (V_OL ≤ 0.4 V, idle 3.135–3.465 V, rise ≤ 300 ns, decode = `--expect` + ACK), and a `values_csv` snippet with gates. Exit 0 pass, 1 any fail, 2 bad input or no frame found. Stdlib only. |
| `probe_points/` | Probe-point pictures for bench procedures (made `lab/procedures/img/v6-probe-points.png` and `v7-probe-points.png`): `python3 tools/lab/probe_points/probe_points.py render --points tools/lab/probe_points/v7.json --out <png>` [`--ref <commit> [--path <board>]` or `--board <file>`; default board from the points file]. kicad-cli 9.0.4 `pcb render` (top, high, 6400×4800, about 2.5 min; `--render-png` reuses one) → board bbox from the PNG alpha channel against the Edge.Cuts bbox (image size measured from the PNG, never assumed) → SVG overlay with #ff1744 markers at footprint pad centres (reference + pad from the points JSON, never by eye) → headless Chrome screenshot (not qlmanage: it crops). Writes `<png>.meta.json` provenance. `pads` and `near` print pad centres for writing a points file. Points files: `v6.json` (`fd632ef`), `v7.json` (`c2acffc`). Look at the output and check every marker sits on its pad. Stdlib only; macOS KiCad and Chrome paths by default. See its README. |
| `ingest_usb.py` | USB fallback: `--src /Volumes/<stick> --test <PREFIX>-NNN (registered prefix) --arm A1usb --at <Mac time of the save> [--files <names the scope showed>]`. Copies the whole stick to `lab/inbox/usb-<stamp>/` (never writes to the stick), matches files to `--at` by mtime (stick offsets 0 and +60 min, ±300 s; the scope's appended index digit is optional in `--files`), and copies the matches into `lab/captures/<ID>/` with §4.4 names plus an `INGEST.tsv` row. Ambiguous or no match: exit 1, nothing renamed. `--dry-run`. |
| `backup_captures.sh` | Copies the gitignored `lab/captures/` and `lab/inbox/` to iCloud Drive, `~/Library/Mobile Documents/com~apple~CloudDocs/motion-play-lab/` (one config value at the top; `$LAB_BACKUP_DIR` overrides). Additive rsync, never `--delete`. `--dry-run`. Exit 1 if the iCloud Drive root is missing. Run after each bench session. |
| `new_investigation.py` | Scaffold: `python3 tools/lab/new_investigation.py --name <folder> --prefix <PFX> --title "<title>"` writes `lab/investigations/<name>/STATE.md` and `NOTEBOOK.md` from `lab/templates/STATE.md` and `NOTEBOOK.md`, with the sentinel front matter (`as_of`/`last_checkpoint` `<PFX>-000`, `open_cards: []`, `status: open`). Refuses (exit 2, nothing written) an existing folder, a prefix already declared or used by card files, a malformed name/prefix, and any existing investigation whose STATE has no `prefix`. Writes files only, never commits; then `check_state.py --inv <name>` and commit. `--root` (lab dir), `--templates`, `--now` for tests. |
| `lablib.py` | Shared helpers: front matter (splits on the first two `---` lines), the generic ID/card patterns (`ID_RE`, `CARD_RE`, `parse_id`), the registry (`investigations(root)`, `prefixes`, `registered_prefixes`), `check_id(id, known)` for tools that take an ID, and per-prefix `next_id(root, prefix)`. |
| `tests/run_tests.py` | Runs everything: the checker fixtures (`tests/fixtures/<condition>/`; each condition fires exactly once and nothing else does) and `tests/tool_tests.py` (capture against `tests/fake_scope.py`, which replays the Phase 6 bench recordings in `tests/scope_fixtures/`; validator and hook rule 4 with `tests/log_fixtures/` (`pass/`, `warn/`, `fail/`); `noise_floor.py` on the V7R-001 evidence CSVs; `i2c_frame.py` on synthetic CSVs the test writes; ingest; the scaffold, in fixture copies only; backup). Tool tests seed a registry (`seed_registry`) in their temp roots and cover a second prefix (`PWR`). Run after any change under `tools/lab/`. |

**One log per arm:** a card that runs at S1 and S2 writes one session log per arm (`_s01` for S1, `_s02` for S2), each with its own `validation` block (pass `--session` to `capture.py`). V1–V4 are recorded in the first log; the second records a fresh V2 read-back and `"V1, V3, V4: see <first log>"` in `validation.notes`.

**One-time setup per clone:** `git config core.hooksPath .githooks`. Without it the STATE rule is not enforced.

**Scope on the LAN (Mac):** the DHO804 is on a direct link at `192.168.50.2` (Mac `en7` `192.168.50.1`). Allow the terminal app (Cursor) under System Settings → Privacy & Security → Local Network, or Python gets `No route to host` while `nc` still connects.

**`self` convention:** `prereg_commit: self` and `Result commit: self` mean "the commit that made this transition", since a commit can't hold its own hash. `check_state.py --load` resolves them from git.

## Dependencies

All KiCad Python tools in this folder use **kiutils ≥ 1.4.8** for KiCad file parsing, through the KiCad 8/9 shim for schematics (kiutils Rule). Install via `pip install kiutils`. Shell scripts require AWS CLI + jq.

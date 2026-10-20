# Tools — AI Context

## Critical Rule

**Never read `.kicad_sch` or `.kicad_pcb` text into context, and never edit them directly.** Use the tools below. Exception: targeted read-only kiutils or `kicad-cli` probes are allowed when no tool output answers the question (e.g. zones, stackup). Run them from a scratch script, print only the numbers you need, and cite the probe and file commit.

## Source-Hash Rule

**Every generated context file carries provenance, and every reader checks it.**

- **JSON:** a top-level `_provenance` object: `source`, `source_sha256`, `generator`, `generator_commit`, `generated`.
- **Markdown:** the same fields as a front-matter block.
- **Images:** a sidecar `<name>.meta.json`, or the provenance block of the narrative that embeds them.
- **Check:** `python3 tools/lab/check_state.py --fresh <file>` recomputes the source hash (exit 0 fresh, 1 stale, 2 no provenance). Run it before citing a generated file in a card or a design decision.
- **Scope:** all generated context, including the existing `circuit-context.json` outputs. Those have no `_provenance` yet (the retrofit belongs to the board-model initiative), so `--fresh` reports them as having none (exit 2). Until the retrofit, judge their freshness from git.

## KiCad Schematic Tools

These three toolkits form a pipeline: **gen** creates sheets, **modify** surgically edits existing sheets, **context** extracts/annotates for AI consumption.

### schematic-context/

Extracts circuit data from `.kicad_sch` files into compact `circuit-context.json` files optimized for AI analysis. Also writes `ai_`-prefixed annotations back into schematic symbols.

| Script | Purpose |
|--------|---------|
| `extract.py` | Combines `kicad-cli` netlist export + kiutils parsing → `circuit-context.json`. Use `--previous` to preserve net/block annotations across re-extractions. |
| `annotate.py` | Writes hidden `ai_function`, `ai_block`, `ai_role`, `ai_critical_specs` properties to component symbols in `.kicad_sch`. |
| `show.py` | Displays annotation coverage; `--unannotated` shows what still needs labeling. |

See `tools/schematic-context/README.md` for full usage.

### schematic-gen/

Generates complete `.kicad_sch` sheet files from structured JSON specs. Components get symbols, footprints, LCSC part numbers, net labels, no-connect flags, and hierarchical labels — all programmatically. Uses the `@jlcpcb/mcp` MCP server to search LCSC parts, check stock, and download symbols/footprints.

| File | Purpose |
|------|---------|
| `spec.json` | Structured spec for the power management sheet (components, nets, blocks). |
| `esp32_spec.json` | Structured spec for the ESP32-S3 sheet. |
| `generate_power_sheet.py` | Generates `power_management.kicad_sch` from `spec.json`. |
| `generate_esp32_sheet.py` | Generates `esp32_s3.kicad_sch` from `esp32_spec.json`. |
| `poc_generate.py` | Proof-of-concept: generates a minimal schematic with one resistor. |

### schematic-modify/

Surgical in-place edits on existing `.kicad_sch` files — adding/removing components, sheet references, hierarchical labels. Sits between gen (full sheet creation) and context (read-only extraction).

| File | Purpose |
|------|---------|
| `modify.py` | Reusable helpers: `add_component`, `remove_component`, `add_hierarchical_label`, `add_sheet_reference`, `annotate_components`. |
| `esp32_integration.py` | Initiative-specific script that used `modify.py` to integrate the ESP32-S3 into the main schematic. |

See `tools/schematic-modify/CONTEXT.md` for relationship details and typical workflow.

## KiCad PCB Tools

### pcb-context/

Extracts structured layout data from `.kicad_pcb` files into `pcb-layout-context.json`, and automates component placement.

| Script | Purpose |
|--------|---------|
| `extract.py` | Parses board outline, component positions, bounding boxes, optional pad data → `pcb-layout-context.json`. |
| `place_power.py` | Computes collision-free placements for power section components relative to anchor ICs. Supports `--dry-run`. |

See `tools/pcb-context/README.md` for full usage.

### verify-routing.py

Verifies PCB routing against spec constraints (trace widths, clearances, net classes). Currently hardcoded to a specific board revision — needs genericization to accept an input spec file.

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

| Tool | Purpose |
|------|---------|
| `check_state.py` | Session-start check. A STATE.md `as_of` behind the highest recorded/abandoned card is **STALE**, the only hard failure (exit 1). These only warn: open-card mismatch, a card in `run` with no commit for 7 days, CHECKPOINT DUE (≥ 3 recorded since `last_checkpoint`, or > 14 days since the last notebook entry), section caps, stale source hashes of generated files cited in Lookups, and v7 mentions in auto-memory. `--load` also prints the default L1 load: open cards, the last two recorded conclusions and today's log, with `self` commits resolved. `--fresh <file>` checks one generated file's provenance (exit 0 fresh, 1 stale, 2 none). `--root`, `--memory-dir` (or `$LAB_MEMORY_DIR`) and `--now` exist for fixtures. |
| `precommit.py` | Called by `.githooks/pre-commit` on commits that stage anything under `lab/`. It rejects three things: a card moved to `recorded`/`abandoned` unless `lab/STATE.md` is staged with `as_of` set to that ID; a `recorded` card with an empty `Result commit` or no `lab/evidence/<ID>/` citation in its Conclusion; and a duplicate `V7R-NNN`. Rule 4 runs `validate_log.py` on staged `lab/log/*.yaml`: **errors block, TODOs only warn** (user-confirmed), so per-arm commits made mid-session go through. |
| `capture.py` | One-command DHO804 capture over the LAN: `python3 tools/lab/capture.py --test V7R-NNN --arm A1 [--session lab/log/<date>_sNN.yaml]`. Sets the scope clock, sends `:STOP` (the scope is left stopped), and writes `lab/captures/<ID>/YYYY-MM-DD_<ID>_<arm>_<nn>.{png,csv,setup.bin}`: the screenshot, the RAW memory CSV (`Time(s),CH1V…`, values verbatim; equal to a menu memory CSV sample for sample) and the `:SYSTem:SETup?` blob (binary, not `.stp`). Appends a measurement entry to the session log (or creates it) with every scope-sourced field filled and operator fields as `TODO`; `:MEASure:ITEM?` ≈ 9.9E37 is `valid: false`. Refuses firmware other than 00.01.05 (`--any-firmware`) and memory > 10 kpts (`--chunked`, unverified). Host `--host` or `$DHO_HOST` (default `192.168.50.2`), port 5555. Exit 0 ok, 1 transport/scope error (nothing written), 2 refused. Every command it sends is bench-verified in the test-workflow-setup PLAN. |
| `vendor/scpi.py` | The socket/TMC layer, vendored unmodified with its MIT notice from `https://github.com/mattjax16/rigol-dho-mcp/blob/f9ac7191869845ae46ca714de69a877c388b2530/rigol_dho_mcp/scpi.py` (commit `f9ac7191869845ae46ca714de69a877c388b2530`). Upstream sha256 `9fface904495086784322b44cdfac4edaa35ea215f1c87ccdfe5b0d4004a5066`. Never edit below its header; wrap it in `capture.py`. Recheck: `tail -n +$(( $(grep -n '^# ---- end vendor header' tools/lab/vendor/scpi.py \| cut -d: -f1) + 1 )) tools/lab/vendor/scpi.py \| shasum -a 256` |
| `validate_log.py` | Checks a session log's required §4.6 fields, branching on `kind` (`log-only`: `dut.*` and per-measurement `test_id`/`feature`/`raw_observation`; `scope`: also scope, validation, channels, values, captures). A `TODO` is pending, not missing. Exit 0 valid, 1 errors, 3 TODOs only (0 with `--allow-todo`), 2 usage or PyYAML missing. A PNG with no `ai_read` entry is a warning. |
| `ingest_usb.py` | USB fallback: `--src /Volumes/<stick> --test V7R-NNN --arm A1usb --at <Mac time of the save> [--files <names the scope showed>]`. Copies the whole stick to `lab/inbox/usb-<stamp>/` (never writes to the stick), matches files to `--at` by mtime (stick offsets 0 and +60 min, ±300 s; the scope's appended index digit is optional in `--files`), and copies the matches into `lab/captures/<ID>/` with §4.4 names plus an `INGEST.tsv` row. Ambiguous or no match: exit 1, nothing renamed. `--dry-run`. |
| `backup_captures.sh` | Copies the gitignored `lab/captures/` and `lab/inbox/` to iCloud Drive, `~/Library/Mobile Documents/com~apple~CloudDocs/motion-play-lab/` (one config value at the top; `$LAB_BACKUP_DIR` overrides). Additive rsync, never `--delete`. `--dry-run`. Exit 1 if the iCloud Drive root is missing. Run after each bench session. |
| `lablib.py` | Shared front-matter and card helpers. Splits on the first two `---` lines, matches only `V7R-NNN-*.md`. |
| `tests/run_tests.py` | Runs everything: the checker fixtures (`tests/fixtures/<condition>/`; each condition fires exactly once and nothing else does) and `tests/tool_tests.py` (capture against `tests/fake_scope.py`, which replays the Phase 6 bench recordings in `tests/scope_fixtures/`; validator and hook rule 4 with `tests/log_fixtures/`; ingest; backup). Run after any change under `tools/lab/`. |

**One-time setup per clone:** `git config core.hooksPath .githooks`. Without it the STATE rule is not enforced.

**Scope on the LAN (Mac):** the DHO804 is on a direct link at `192.168.50.2` (Mac `en7` `192.168.50.1`). Allow the terminal app (Cursor) under System Settings → Privacy & Security → Local Network, or Python gets `No route to host` while `nc` still connects.

**`self` convention:** `prereg_commit: self` and `Result commit: self` mean "the commit that made this transition", since a commit can't hold its own hash. `check_state.py --load` resolves them from git.

## Dependencies

All KiCad Python tools in this folder use **kiutils ≥ 1.4.8** for KiCad file parsing. Install via `pip install kiutils`. Shell scripts require AWS CLI + jq.

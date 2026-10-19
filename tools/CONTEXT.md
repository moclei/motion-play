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

Tooling for the bench-debug `lab/` tree at the repo root (STATE, cards, log, evidence). The rules come from `docs/research/v7-retry/context-strategy.md` §4.2 and §8.2. Stdlib Python 3.7+; PyYAML is used if it's installed, otherwise a built-in front-matter parser.

| Tool | Purpose |
|------|---------|
| `check_state.py` | Session-start check. A STATE.md `as_of` behind the highest recorded/abandoned card is **STALE**, the only hard failure (exit 1). These only warn: open-card mismatch, a card in `run` with no commit for 7 days, CHECKPOINT DUE (≥ 3 recorded since `last_checkpoint`, or > 14 days since the last notebook entry), section caps, stale source hashes of generated files cited in Lookups, and v7 mentions in auto-memory. `--load` also prints the default L1 load: open cards, the last two recorded conclusions and today's log, with `self` commits resolved. `--fresh <file>` checks one generated file's provenance (exit 0 fresh, 1 stale, 2 none). `--root`, `--memory-dir` (or `$LAB_MEMORY_DIR`) and `--now` exist for fixtures. |
| `precommit.py` | Called by `.githooks/pre-commit` on commits that stage anything under `lab/`. It rejects three things: a card moved to `recorded`/`abandoned` unless `lab/STATE.md` is staged with `as_of` set to that ID; a `recorded` card with an empty `Result commit` or no `lab/evidence/<ID>/` citation in its Conclusion; and a duplicate `V7R-NNN`. |
| `lablib.py` | Shared front-matter and card helpers. Splits on the first two `---` lines, matches only `V7R-NNN-*.md`. |
| `tests/run_tests.py` | Fixture tests (`tests/fixtures/<condition>/`). Each checker condition fires exactly once and nothing else does. Run after any checker change. |

**One-time setup per clone:** `git config core.hooksPath .githooks`. Without it the STATE rule is not enforced.

**`self` convention:** `prereg_commit: self` and `Result commit: self` mean "the commit that made this transition", since a commit can't hold its own hash. `check_state.py --load` resolves them from git.

## Dependencies

All KiCad Python tools in this folder use **kiutils ≥ 1.4.8** for KiCad file parsing. Install via `pip install kiutils`. Shell scripts require AWS CLI + jq.
